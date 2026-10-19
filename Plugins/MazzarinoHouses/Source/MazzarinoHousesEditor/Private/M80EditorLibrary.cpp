#include "M80EditorLibrary.h"
#include "Misc/FileHelper.h"
#include "Engine/Texture.h"
#include "Interfaces/ITargetPlatform.h"
#include "Interfaces/ITargetPlatformManagerModule.h"
#include "Modules/ModuleManager.h"
#include "TextureSourceDataUtils.h"
#include "M80House.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetUtils/CreateStaticMeshUtil.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMeshToMeshDescription.h"
#include "Engine/StaticMesh.h"
#include "StaticMeshAttributes.h"
#include "UObject/Package.h"
#include "Editor.h"
#include "Landscape.h"
#include "LandscapeComponent.h"
#include "LandscapeProxy.h"
#include "LandscapeSubsystem.h"
#include "LandscapeEditLayer.h"
#include "Components/SplineComponent.h"
#include "TimerManager.h"
#include "LandscapeInfo.h"
#include "Components/PrimitiveComponent.h"
#include "Misc/ScopedSlowTask.h"
#include "EngineUtils.h"
#include "Engine/SceneCaptureCube.h"
#include "Components/SceneCaptureComponentCube.h"
#include "Engine/TextureRenderTargetCube.h"
#include "Engine/TextureCube.h"
#include "Engine/TextureCubeArray.h"
#include "RenderingThread.h"
#include "LandscapeEdit.h"
#include "LandscapeLayerInfoObject.h"
#include "Engine/SkeletalMesh.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "AnimationRuntime.h"
#include "MaterialEditingLibrary.h"
#include "M80Bougainvillea.h"
#include "WorldPartition/WorldPartition.h"
#include "WorldPartition/WorldPartitionRuntimeHash.h"
#include "DNAReader.h"
#include "DNAUtils.h"
#include "MetaHumanCharacter.h"
#include "MetaHumanCharacterEditorSubsystem.h"
#include "MetaHumanCharacterIdentity.h"
#include "Dataflow/DataflowObject.h"
#include "Dataflow/DataflowNode.h"
#include "Dataflow/DataflowInputOutput.h"
#include "Dataflow/DataflowInstance.h"
#include "ChaosOutfitAsset/SizedOutfitSource.h"
#include "ChaosClothAsset/ClothAssetBase.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "RenderingThread.h"

namespace
{
/**
 * Editor glue for the houses:
 *  - after a map opens, rebuild houses whose baked mesh is missing (baked meshes are not versioned);
 *  - when a landscape is sculpted, rebuild the houses standing on the changed area.
 */
class FMazzarinoHousesEditorModule : public IModuleInterface
{
public:
	virtual void StartupModule() override
	{
		MapOpenedHandle = FEditorDelegates::OnMapOpened.AddRaw(this, &FMazzarinoHousesEditorModule::OnMapOpened);
		if (GEngine)
		{
			ActorAddedHandle = GEngine->OnLevelActorAdded().AddRaw(this, &FMazzarinoHousesEditorModule::OnActorAdded);
		}
	}

	virtual void ShutdownModule() override
	{
		FEditorDelegates::OnMapOpened.Remove(MapOpenedHandle);
		if (GEngine)
		{
			GEngine->OnLevelActorAdded().Remove(ActorAddedHandle);
		}
		for (const TWeakObjectPtr<ULandscapeSubsystem>& Subsystem : BoundSubsystems)
		{
			if (Subsystem.IsValid())
			{
				Subsystem->OnLandscapeProxyComponentDataChanged().RemoveAll(this);
			}
		}
	}

private:
	static UWorld* EditorWorld() { return GEditor ? GEditor->GetEditorWorldContext().World() : nullptr; }

	void OnMapOpened(const FString&, bool)
	{
		UWorld* World = EditorWorld();
		if (!World)
		{
			return;
		}
		for (TActorIterator<ALandscapeProxy> It(World); It; ++It)
		{
			Bind(*It);
		}
		int32 Rebuilt = 0;
		for (TActorIterator<AM80House> It(World); It; ++It)
		{
			if (It->NeedsRebuild())
			{
				It->Rebuild();
				++Rebuilt;
			}
		}
		if (Rebuilt)
		{
			UE_LOG(LogTemp, Display, TEXT("MazzarinoHouses: rebuilt %d houses without a baked mesh"), Rebuilt);
		}
	}

	void OnActorAdded(AActor* Actor)
	{
		if (ALandscapeProxy* Proxy = Cast<ALandscapeProxy>(Actor))
		{
			Bind(Proxy);
		}
	}

	void Bind(ALandscapeProxy* Proxy)
	{
		if (Proxy && !BoundProxies.Contains(Proxy))
		{
			// Since 5.7 the landscapes of a world report their changes through its landscape subsystem.
			ULandscapeSubsystem* Subsystem = Proxy->GetWorld() ? Proxy->GetWorld()->GetSubsystem<ULandscapeSubsystem>() : nullptr;
			if (Subsystem && !BoundSubsystems.Contains(Subsystem))
			{
				Subsystem->OnLandscapeProxyComponentDataChanged().AddRaw(this, &FMazzarinoHousesEditorModule::OnLandscapeChanged);
				BoundSubsystems.Add(Subsystem);
			}
			BoundProxies.Add(Proxy);
			for (ULandscapeComponent* C : Proxy->LandscapeComponents)
			{
				if (C)
				{
					HeightHashes.Add(C, HeightHash(C));
				}
			}
		}
	}

	/** Hash of the component's heights: painting layers (roads...) also fires OnComponentDataChanged. */
	static uint32 HeightHash(const ULandscapeComponent* C)
	{
		ULandscapeInfo* Info = C ? C->GetLandscapeInfo() : nullptr;
		if (!Info)
		{
			return 0;
		}
		// GetComponentExtent only widens the range it is given.
		int32 X1 = MAX_int32, Y1 = MAX_int32, X2 = MIN_int32, Y2 = MIN_int32;
		C->GetComponentExtent(X1, Y1, X2, Y2);
		if (X2 < X1 || Y2 < Y1 || (int64)(X2 - X1 + 1) * (Y2 - Y1 + 1) > 4096 * 4096)
		{
			return 0;
		}
		TArray<uint16> Data;
		Data.SetNumZeroed((X2 - X1 + 1) * (Y2 - Y1 + 1));
		FLandscapeEditDataInterface Edit(Info);
		Edit.GetHeightDataFast(X1, Y1, X2, Y2, Data.GetData(), 0);
		return FCrc::MemCrc32(Data.GetData(), Data.Num() * sizeof(uint16));
	}

	void OnLandscapeChanged(ALandscapeProxy*, const FLandscapeProxyComponentDataChangedParams& Params)
	{
		Params.ForEachComponent([this](const ULandscapeComponent* Component)
		{
			if (!Component)
			{
				return;
			}
			const uint32 Hash = HeightHash(Component);
			const uint32* Old = HeightHashes.Find(Component);
			if (Old && *Old == Hash)
			{
				return; // weights only: houses do not care
			}
			HeightHashes.Add(Component, Hash);
			DirtyArea += Component->Bounds.GetBox();
		});
		if (!DirtyArea.IsValid)
		{
			return;
		}
		// Sculpting fires many updates: wait for a short pause before rebuilding.
		if (GEditor)
		{
			GEditor->GetTimerManager()->SetTimer(RebuildTimer, FTimerDelegate::CreateRaw(this, &FMazzarinoHousesEditorModule::RebuildDirtyHouses), 0.6f, false);
		}
	}

	void RebuildDirtyHouses()
	{
		UWorld* World = EditorWorld();
		if (!World || !DirtyArea.IsValid)
		{
			return;
		}
		const FBox Area = DirtyArea.ExpandBy(FVector(500, 500, 100000));
		DirtyArea.Init();
		int32 Rebuilt = 0;
		for (TActorIterator<AM80House> It(World); It; ++It)
		{
			if (It->bLiveRebuild && It->Footprint && Area.Intersect(It->Footprint->Bounds.GetBox()))
			{
				It->Rebuild();
				++Rebuilt;
			}
		}
		if (Rebuilt)
		{
			UE_LOG(LogTemp, Display, TEXT("MazzarinoHouses: terrain changed, rebuilt %d houses"), Rebuilt);
		}
	}

	FDelegateHandle MapOpenedHandle;
	FDelegateHandle ActorAddedHandle;
	TSet<TWeakObjectPtr<ALandscapeProxy>> BoundProxies;
	TSet<TWeakObjectPtr<ULandscapeSubsystem>> BoundSubsystems;
	TMap<TWeakObjectPtr<const ULandscapeComponent>, uint32> HeightHashes;
	FBox DirtyArea = FBox(ForceInit);
	FTimerHandle RebuildTimer;
};
}

IMPLEMENT_MODULE(FMazzarinoHousesEditorModule, MazzarinoHousesEditor)

bool UM80EditorLibrary::DownsizeTextureSource(UTexture* Texture, int32 MaxSize)
{
	if (!Texture || MaxSize < 16)
	{
		return false;
	}
	const ITargetPlatform* Platform = GetTargetPlatformManagerRef().GetRunningTargetPlatform();
	if (!UE::TextureUtilitiesCommon::Experimental::DownsizeTextureSourceData(Texture, MaxSize, Platform))
	{
		return false;
	}
	Texture->LODBias = 0;
	// DownsizeTextureSourceData already called PreEditChange.
	Texture->PostEditChange();
	return true;
}

bool UM80EditorLibrary::CompressTextureSourceJPEG(UTexture* Texture, int32 Quality)
{
	if (!Texture || !Texture->Source.IsValid())
	{
		return false;
	}
	// JPEG needs 8-bit sources; downsizing can leave 16-bit or float data behind.
	const ETextureSourceFormat Format = Texture->Source.GetFormat(0);
	if (Format != TSF_BGRA8 && Format != TSF_G8)
	{
		const ETextureSourceFormat Target = (Format == TSF_G16 || Format == TSF_R16F || Format == TSF_R32F) ? TSF_G8 : TSF_BGRA8;
		if (!UE::TextureUtilitiesCommon::Experimental::ChangeTextureSourceFormat(Texture, Target))
		{
			return false;
		}
	}
	return UE::TextureUtilitiesCommon::Experimental::CompressTextureSourceWithJPEG(Texture, Quality);
}

FIntPoint UM80EditorLibrary::GetTextureSourceSize(UTexture* Texture)
{
	return Texture ? Texture->Source.GetLogicalSize() : FIntPoint::ZeroValue;
}

UStaticMesh* UM80EditorLibrary::BakeHouse(AM80House* House, const FString& Folder, bool bNanite)
{
	if (!House || !House->Shell)
	{
		return nullptr;
	}
	// The house's own file (World Partition: one per actor) must be saved with the bake, or the town keeps it live.
	House->Modify();
	House->Rebuild();
	UE::Geometry::FDynamicMesh3 Mesh;
	House->Shell->ProcessMesh([&Mesh](const UE::Geometry::FDynamicMesh3& Source) { Mesh = Source; });
	if (Mesh.TriangleCount() == 0)
	{
		return nullptr;
	}
	TArray<UMaterialInterface*> Materials;
	for (int32 i = 0; i < House->Shell->GetNumMaterials(); ++i)
	{
		Materials.Add(House->Shell->GetMaterial(i));
	}

	const FString Name = TEXT("SM_M80_") + (House->LotId.IsEmpty() ? House->GetName() : House->LotId);
	const FString PackagePath = Folder / Name;
	UStaticMesh* StaticMesh = LoadObject<UStaticMesh>(nullptr, *(PackagePath + TEXT(".") + Name), nullptr, LOAD_NoWarn | LOAD_Quiet);
	if (StaticMesh)
	{
		// Re-bake in place so references and the asset path stay stable.
		FMeshDescription Description;
		FStaticMeshAttributes(Description).Register();
		FDynamicMeshToMeshDescription Converter;
		Converter.Convert(&Mesh, Description);
		StaticMesh->Modify();
		TArray<FStaticMaterial> Slots;
		for (UMaterialInterface* Material : Materials)
		{
			Slots.Add(FStaticMaterial(Material));
		}
		StaticMesh->SetStaticMaterials(Slots);
		StaticMesh->CreateMeshDescription(0, MoveTemp(Description));
		StaticMesh->CommitMeshDescription(0);
		StaticMesh->NaniteSettings.bEnabled = bNanite;
		StaticMesh->Build();
		StaticMesh->PostEditChange();
		StaticMesh->MarkPackageDirty();
	}
	else
	{
		UE::AssetUtils::FStaticMeshAssetOptions Options;
		Options.NewAssetPath = PackagePath;
		Options.NumMaterialSlots = Materials.Num();
		Options.AssetMaterials = Materials;
		Options.bGenerateNaniteEnabledMesh = bNanite;
		Options.bAllowDistanceField = true;
		Options.bCreatePhysicsBody = true;
		Options.CollisionType = ECollisionTraceFlag::CTF_UseComplexAsSimple;
		Options.SourceMeshes.DynamicMeshes.Add(&Mesh);
		UE::AssetUtils::FStaticMeshResults Results;
		if (UE::AssetUtils::CreateStaticMeshAsset(Options, Results) != UE::AssetUtils::ECreateStaticMeshResult::Ok || !Results.StaticMesh)
		{
			return nullptr;
		}
		StaticMesh = Results.StaticMesh;
		StaticMesh->PostEditChange();
		FAssetRegistryModule::AssetCreated(StaticMesh);
	}
	House->ApplyBakedMesh(StaticMesh);
	House->MarkPackageDirty();
	return StaticMesh;
}

namespace
{
	/** A landscape of SizeX x SizeY vertices from Origin, one every QuadSizeCm; Heights row by row (Lowest = unknown: filled
	 *  from the neighbours). Two sections of 63 quads per component. */
	ALandscape* LandscapeFromHeights(UWorld* World, FVector2D Origin, double QuadSizeCm, int32 SizeX, int32 SizeY, TArray<float> Heights,
		UMaterialInterface* Material)
	{
		constexpr int32 QuadsPerSection = 63;
		constexpr int32 SectionsPerComponent = 2;
		// Fill holes (outside the mesh) by spreading valid neighbours, then clamp what is left.
		double MinZ = TNumericLimits<double>::Max(), MaxZ = TNumericLimits<double>::Lowest();
		int32 Missing = 0;
		for (float H : Heights)
		{
			if (H > TNumericLimits<float>::Lowest())
			{
				MinZ = FMath::Min<double>(MinZ, H);
				MaxZ = FMath::Max<double>(MaxZ, H);
			}
			else
			{
				++Missing;
			}
		}
		if (MinZ > MaxZ)
		{
			return nullptr;
		}
		for (int32 Pass = 0; Pass < 64 && Missing > 0; ++Pass)
		{
			TArray<float> Next = Heights;
			Missing = 0;
			for (int32 Y = 0; Y < SizeY; ++Y)
			{
				for (int32 X = 0; X < SizeX; ++X)
				{
					if (Heights[Y * SizeX + X] > TNumericLimits<float>::Lowest())
					{
						continue;
					}
					double Sum = 0;
					int32 Count = 0;
					const int32 N[4][2] = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}};
					for (const auto& D : N)
					{
						const int32 NX = X + D[0], NY = Y + D[1];
						if (NX >= 0 && NY >= 0 && NX < SizeX && NY < SizeY && Heights[NY * SizeX + NX] > TNumericLimits<float>::Lowest())
						{
							Sum += Heights[NY * SizeX + NX];
							++Count;
						}
					}
					if (Count)
					{
						Next[Y * SizeX + X] = Sum / Count;
					}
					else
					{
						++Missing;
					}
				}
			}
			Heights = MoveTemp(Next);
		}
	
		for (float& H : Heights)
		{
			if (H <= TNumericLimits<float>::Lowest())
			{
				H = MinZ; // far outside the source terrain
			}
		}
	
		// uint16 heights: Z = ActorZ + (H - 32768) / 128 * ScaleZ. Pick ScaleZ so the range fits with margin for sculpting.
		const double MidZ = (MinZ + MaxZ) * 0.5;
		const double HalfRange = FMath::Max(25600.0, (MaxZ - MinZ) * 0.5 + 20000.0); // at least +-256 m, plus 200 m headroom
		const double ScaleZ = HalfRange / 256.0;
		TArray<uint16> Data;
		Data.SetNumUninitialized(SizeX * SizeY);
		for (int32 i = 0; i < Heights.Num(); ++i)
		{
			const double Value = 32768.0 + (Heights[i] - MidZ) * 128.0 / ScaleZ;
			Data[i] = uint16(FMath::Clamp(FMath::RoundToInt(Value), 0, 65535));
		}
	
		ALandscape* Landscape = World->SpawnActor<ALandscape>(FVector(Origin.X, Origin.Y, MidZ), FRotator::ZeroRotator);
		Landscape->LandscapeMaterial = Material;
		Landscape->SetActorRelativeScale3D(FVector(QuadSizeCm, QuadSizeCm, ScaleZ));
		Landscape->StaticLightingLOD = FMath::DivideAndRoundUp(FMath::CeilLogTwo((SizeX * SizeY) / (2048 * 2048) + 1), (uint32)2);
	
		TMap<FGuid, TArray<uint16>> HeightPerLayer;
		HeightPerLayer.Add(FGuid(), MoveTemp(Data));
		TMap<FGuid, TArray<FLandscapeImportLayerInfo>> MaterialLayers;
		MaterialLayers.Add(FGuid(), TArray<FLandscapeImportLayerInfo>());
		Landscape->Import(FGuid::NewGuid(), 0, 0, SizeX - 1, SizeY - 1, SectionsPerComponent, QuadsPerSection, HeightPerLayer, TEXT(""), MaterialLayers,
			ELandscapeImportAlphamapType::Additive, TArrayView<const FLandscapeLayer>());
		Landscape->SetActorLabel(TEXT("M80_Landscape"));
		if (ULandscapeInfo* Info = Landscape->GetLandscapeInfo())
		{
			Info->UpdateLayerInfoMap(Landscape);
		}
		return Landscape;
	}
	
}

ALandscape* UM80EditorLibrary::CreateLandscapeFromTerrain(AActor* Terrain, FVector2D Center, float QuadSizeCm, int32 ComponentsX, int32 ComponentsY, UMaterialInterface* Material)
{
	if (!Terrain || !Terrain->GetWorld() || QuadSizeCm <= 0 || ComponentsX < 1 || ComponentsY < 1)
	{
		return nullptr;
	}
	constexpr int32 QuadsPerSection = 63;
	constexpr int32 SectionsPerComponent = 2;
	constexpr int32 QuadsPerComponent = QuadsPerSection * SectionsPerComponent;
	const int32 SizeX = ComponentsX * QuadsPerComponent + 1;
	const int32 SizeY = ComponentsY * QuadsPerComponent + 1;
	const FVector2D Origin = Center - FVector2D((SizeX - 1) * 0.5 * QuadSizeCm, (SizeY - 1) * 0.5 * QuadSizeCm);

	TArray<UPrimitiveComponent*> Surfaces;
	Terrain->GetComponents<UPrimitiveComponent>(Surfaces);
	const FBox Bounds = Terrain->GetComponentsBoundingBox(true);
	const double Top = Bounds.Max.Z + 1000, Bottom = Bounds.Min.Z - 1000;

	// Trace only the terrain actor, so houses, roads and landmarks never leak into the heights.
	TArray<float> Heights;
	Heights.Init(TNumericLimits<float>::Lowest(), SizeX * SizeY);
	{
		FScopedSlowTask Task(SizeY, NSLOCTEXT("M80", "SampleTerrain", "Campionamento del terreno"));
		Task.MakeDialog();
		FCollisionQueryParams Params(SCENE_QUERY_STAT(M80LandscapeSample), true);
		for (int32 Y = 0; Y < SizeY; ++Y)
		{
			Task.EnterProgressFrame();
			for (int32 X = 0; X < SizeX; ++X)
			{
				const FVector2D Q = Origin + FVector2D(X, Y) * QuadSizeCm;
				FHitResult Best;
				for (UPrimitiveComponent* C : Surfaces)
				{
					FHitResult Hit;
					if (C->IsCollisionEnabled() && C->LineTraceComponent(Hit, FVector(Q.X, Q.Y, Top), FVector(Q.X, Q.Y, Bottom), Params))
					{
						if (!Best.bBlockingHit || Hit.ImpactPoint.Z > Best.ImpactPoint.Z)
						{
							Best = Hit;
							Best.bBlockingHit = true;
						}
					}
				}
				if (Best.bBlockingHit)
				{
					Heights[Y * SizeX + X] = Best.ImpactPoint.Z;
				}
			}
		}
	}

	return LandscapeFromHeights(Terrain->GetWorld(), Origin, QuadSizeCm, SizeX, SizeY, MoveTemp(Heights), Material);
}

bool UM80EditorLibrary::SampleLandscapeHeights(FVector2D Center, float QuadSizeCm, int32 ComponentsX, int32 ComponentsY, const FString& File)
{
	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World || QuadSizeCm <= 0 || ComponentsX < 1 || ComponentsY < 1)
	{
		return false;
	}
	const int32 SizeX = ComponentsX * 126 + 1, SizeY = ComponentsY * 126 + 1;
	const FVector2D Origin = Center - FVector2D((SizeX - 1) * 0.5 * QuadSizeCm, (SizeY - 1) * 0.5 * QuadSizeCm);
	TArray<float> Heights;
	Heights.Init(TNumericLimits<float>::Lowest(), SizeX * SizeY);
	FCollisionQueryParams Params(SCENE_QUERY_STAT(M80LandscapeHeights), true);
	int32 Found = 0;
	for (int32 Y = 0; Y < SizeY; ++Y)
	{
		for (int32 X = 0; X < SizeX; ++X)
		{
			const FVector2D Q = Origin + FVector2D(X, Y) * QuadSizeCm;
			TArray<FHitResult> Hits;
			World->LineTraceMultiByObjectType(Hits, FVector(Q.X, Q.Y, 300000.0), FVector(Q.X, Q.Y, -300000.0), FCollisionObjectQueryParams(ECC_WorldStatic), Params);
			for (const FHitResult& H : Hits)
			{
				// Only the landscape: houses, roads and steps on it are not the ground.
				if (Cast<ALandscapeProxy>(H.GetActor()))
				{
					Heights[Y * SizeX + X] = H.ImpactPoint.Z;
					++Found;
					break;
				}
			}
		}
	}
	TArray<uint8> Bytes;
	Bytes.Append(reinterpret_cast<const uint8*>(&SizeX), sizeof(int32));
	Bytes.Append(reinterpret_cast<const uint8*>(&SizeY), sizeof(int32));
	Bytes.Append(reinterpret_cast<const uint8*>(Heights.GetData()), Heights.Num() * sizeof(float));
	return Found > 0 && FFileHelper::SaveArrayToFile(Bytes, *File);
}

ALandscape* UM80EditorLibrary::CreateLandscapeFromHeightsFile(FVector2D Center, float QuadSizeCm, const FString& File, UMaterialInterface* Material)
{
	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	TArray<uint8> Bytes;
	if (!World || !FFileHelper::LoadFileToArray(Bytes, *File) || Bytes.Num() < 8)
	{
		return nullptr;
	}
	int32 SizeX = 0, SizeY = 0;
	FMemory::Memcpy(&SizeX, Bytes.GetData(), 4);
	FMemory::Memcpy(&SizeY, Bytes.GetData() + 4, 4);
	if (SizeX < 2 || SizeY < 2 || Bytes.Num() != 8 + SizeX * SizeY * 4)
	{
		return nullptr;
	}
	TArray<float> Heights;
	Heights.SetNumUninitialized(SizeX * SizeY);
	FMemory::Memcpy(Heights.GetData(), Bytes.GetData() + 8, Heights.Num() * 4);
	const FVector2D Origin = Center - FVector2D((SizeX - 1) * 0.5 * QuadSizeCm, (SizeY - 1) * 0.5 * QuadSizeCm);
	return LandscapeFromHeights(World, Origin, QuadSizeCm, SizeX, SizeY, MoveTemp(Heights), Material);
}

UTextureCube* UM80EditorLibrary::CaptureRoomCube(FVector Location, int32 Size, const FString& PackagePath)
{
	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World || Size < 16)
	{
		return nullptr;
	}
	FActorSpawnParameters Params;
	Params.ObjectFlags = RF_Transient;
	ASceneCaptureCube* Capture = World->SpawnActor<ASceneCaptureCube>(Location, FRotator::ZeroRotator, Params);
	if (!Capture)
	{
		return nullptr;
	}
	UTextureRenderTargetCube* Target = NewObject<UTextureRenderTargetCube>(GetTransientPackage());
	Target->bHDR = true;
	Target->InitAutoFormat(Size);
	Target->UpdateResourceImmediate(true);
	USceneCaptureComponentCube* Component = Capture->GetCaptureComponentCube();
	Component->TextureTarget = Target;
	Component->bCaptureEveryFrame = false;
	Component->bCaptureOnMovement = false;
	Component->CaptureScene();
	FlushRenderingCommands();

	UPackage* Package = CreatePackage(*PackagePath);
	Package->FullyLoad();
	const FString Name = FPackageName::GetShortName(PackagePath);
	if (UObject* Old = StaticFindObject(UObject::StaticClass(), Package, *Name))
	{
		// Replace in place: move the old cube out of the package first.
		Old->Rename(nullptr, GetTransientPackage(), REN_DontCreateRedirectors | REN_NonTransactional);
		Old->ClearFlags(RF_Public | RF_Standalone);
	}
	UTextureCube* Cube = Target->ConstructTextureCube(Package, Name, RF_Public | RF_Standalone);
	Capture->Destroy();
	if (Cube)
	{
		Cube->MarkPackageDirty();
		FAssetRegistryModule::AssetCreated(Cube);
	}
	return Cube;
}

UTextureCubeArray* UM80EditorLibrary::MakeCubeArray(const TArray<UTextureCube*>& Cubes, const FString& PackagePath)
{
	UPackage* Package = CreatePackage(*PackagePath);
	Package->FullyLoad();
	const FString Name = FPackageName::GetShortName(PackagePath);
	UTextureCubeArray* Array = FindObject<UTextureCubeArray>(Package, *Name);
	const bool bNew = Array == nullptr;
	if (bNew)
	{
		Array = NewObject<UTextureCubeArray>(Package, *Name, RF_Public | RF_Standalone);
	}
	Array->Modify();
	Array->SourceTextures.Reset();
	for (UTextureCube* Cube : Cubes)
	{
		if (Cube)
		{
			Array->SourceTextures.Add(Cube);
		}
	}
	if (!Array->UpdateSourceFromSourceTextures(bNew))
	{
		return nullptr;
	}
	Array->UpdateResource();
	Array->MarkPackageDirty();
	if (bNew)
	{
		FAssetRegistryModule::AssetCreated(Array);
	}
	return Array;
}

ULandscapeLayerInfoObject* UM80EditorLibrary::EnsureLandscapeLayer(ALandscape* Landscape, FName LayerName, const FString& PackagePath, bool bNoWeightBlend)
{
	ULandscapeInfo* Info = Landscape ? Landscape->GetLandscapeInfo() : nullptr;
	if (!Info || LayerName.IsNone())
	{
		return nullptr;
	}
	// UE 5.5: the landscape keeps its paint layers in TargetLayers; allocations of layers missing there
	// are dropped when the map is loaded again.
	auto Register = [&](ULandscapeLayerInfoObject* LI)
	{
		const FLandscapeTargetLayerSettings Settings(LI);
		if (Landscape->HasTargetLayer(LayerName))
		{
			Landscape->UpdateTargetLayer(LayerName, Settings);
		}
		else
		{
			Landscape->AddTargetLayer(LayerName, Settings);
		}
	};
	if (ULandscapeLayerInfoObject* Existing = Info->GetLayerInfoByName(LayerName))
	{
		Register(Existing);
		Landscape->MarkPackageDirty();
		return Existing;
	}
	ULandscapeLayerInfoObject* LayerInfo = LoadObject<ULandscapeLayerInfoObject>(nullptr, *PackagePath, nullptr, LOAD_NoWarn | LOAD_Quiet);
	if (!LayerInfo)
	{
		UPackage* Package = CreatePackage(*PackagePath);
		LayerInfo = NewObject<ULandscapeLayerInfoObject>(Package, FName(*FPackageName::GetShortName(PackagePath)), RF_Public | RF_Standalone);
		LayerInfo->SetFlags(RF_Transactional);
		LayerInfo->SetLayerName(LayerName, false);
		LayerInfo->SetBlendMethod(bNoWeightBlend ? ELandscapeTargetLayerBlendMethod::None : ELandscapeTargetLayerBlendMethod::FinalWeightBlending, false);
		FAssetRegistryModule::AssetCreated(LayerInfo);
		Package->MarkPackageDirty();
	}
	Info->Modify();
	const int32 Index = Info->GetLayerInfoIndex(LayerName, Landscape);
	if (Index == INDEX_NONE)
	{
		Info->Layers.Add(FLandscapeInfoLayerSettings(LayerInfo, Landscape));
	}
	else
	{
		Info->Layers[Index].LayerInfoObj = LayerInfo;
	}
	Info->CreateTargetLayerSettingsFor(LayerInfo);
	Register(LayerInfo);
	Landscape->MarkPackageDirty();
	return LayerInfo;
}

int32 UM80EditorLibrary::PaintLandscapeLayerAlongSplines(ALandscape* Landscape, ULandscapeLayerInfoObject* Layer, const TArray<USplineComponent*>& Splines,
	const TArray<float>& HalfWidthsCm, float EdgeCm, bool bClear)
{
	ULandscapeInfo* Info = Landscape ? Landscape->GetLandscapeInfo() : nullptr;
	int32 MinX, MinY, MaxX, MaxY;
	if (!Info || !Layer || !Info->GetLandscapeExtent(MinX, MinY, MaxX, MaxY))
	{
		return 0;
	}
	const int32 W = MaxX - MinX + 1, H = MaxY - MinY + 1;
	const FTransform LT = Landscape->GetActorTransform();
	const double Quad = LT.GetScale3D().X;
	const double Edge = FMath::Max(1.0, (double)EdgeCm);
	const FGuid EditLayer = Landscape->GetEditLayerConst(0) ? Landscape->GetEditLayerConst(0)->GetGuid() : FGuid();

	TArray<uint8> Data;
	Data.SetNumZeroed(W * H);
	if (!bClear)
	{
		FScopedSetLandscapeEditingLayer Scope(Landscape, EditLayer);
		FLandscapeEditDataInterface Edit(Info);
		Edit.GetWeightDataFast(Layer, MinX, MinY, MaxX, MaxY, Data.GetData(), 0);
	}

	int32 Painted = 0;
	for (int32 s = 0; s < Splines.Num(); ++s)
	{
		const USplineComponent* S = Splines[s];
		if (!S || S->GetNumberOfSplinePoints() < 2)
		{
			continue;
		}
		const double Half = HalfWidthsCm.IsValidIndex(s) ? HalfWidthsCm[s] : 250.0;
		const double Reach = (Half + Edge) / Quad;
		const double Length = S->GetSplineLength();
		const int32 N = FMath::Max(1, FMath::CeilToInt(Length / 50.0));
		TArray<FVector2D> Pts;
		for (int32 k = 0; k <= N; ++k)
		{
			const FVector L = LT.InverseTransformPosition(S->GetLocationAtDistanceAlongSpline(Length * k / N, ESplineCoordinateSpace::World));
			Pts.Add(FVector2D(L.X, L.Y));
		}
		for (int32 k = 0; k + 1 < Pts.Num(); ++k)
		{
			const FVector2D A = Pts[k], B = Pts[k + 1];
			const int32 X0 = FMath::Max(MinX, FMath::FloorToInt(FMath::Min(A.X, B.X) - Reach)), X1 = FMath::Min(MaxX, FMath::CeilToInt(FMath::Max(A.X, B.X) + Reach));
			const int32 Y0 = FMath::Max(MinY, FMath::FloorToInt(FMath::Min(A.Y, B.Y) - Reach)), Y1 = FMath::Min(MaxY, FMath::CeilToInt(FMath::Max(A.Y, B.Y) + Reach));
			const FVector2D AB = B - A;
			const double Len2 = FMath::Max(AB.SizeSquared(), 1e-6);
			for (int32 y = Y0; y <= Y1; ++y)
			{
				for (int32 x = X0; x <= X1; ++x)
				{
					const FVector2D Q(x, y);
					const double t = FMath::Clamp(FVector2D::DotProduct(Q - A, AB) / Len2, 0.0, 1.0);
					const double D = FVector2D::Distance(Q, A + AB * t) * Quad;
					const double Alpha = FMath::Clamp((Half + Edge - D) / Edge, 0.0, 1.0);
					if (Alpha > 0)
					{
						uint8& V = Data[(y - MinY) * W + (x - MinX)];
						const uint8 NewV = (uint8)FMath::RoundToInt(Alpha * 255.0);
						if (NewV > V)
						{
							Painted += V == 0 ? 1 : 0;
							V = NewV;
						}
					}
				}
			}
		}
	}

	{
		FScopedSetLandscapeEditingLayer Scope(Landscape, EditLayer, [Landscape] { Landscape->RequestLayersContentUpdate(ELandscapeLayerUpdateMode::Update_Weightmap_All); });
		TAlphamapAccessor<false> Accessor(Info, Layer);
		Accessor.SetData(MinX, MinY, MaxX, MaxY, Data.GetData(), ELandscapeLayerPaintingRestriction::None);
	}
	Landscape->MarkPackageDirty();
	return Painted;
}

FString UM80EditorLibrary::DescribeLandscapeLayer(ALandscape* Landscape, ULandscapeLayerInfoObject* Layer)
{
	ULandscapeInfo* Info = Landscape ? Landscape->GetLandscapeInfo() : nullptr;
	int32 MinX, MinY, MaxX, MaxY;
	if (!Info || !Layer || !Info->GetLandscapeExtent(MinX, MinY, MaxX, MaxY))
	{
		return TEXT("invalid");
	}
	const int32 W = MaxX - MinX + 1, H = MaxY - MinY + 1;
	auto Count = [&](bool bEditLayer)
	{
		TArray<uint8> Data;
		Data.SetNumZeroed(W * H);
		TOptional<FScopedSetLandscapeEditingLayer> Scope;
		if (bEditLayer && Landscape->GetEditLayerConst(0))
		{
			Scope.Emplace(Landscape, Landscape->GetEditLayerConst(0)->GetGuid());
		}
		FLandscapeEditDataInterface Edit(Info);
		Edit.GetWeightDataFast(Layer, MinX, MinY, MaxX, MaxY, Data.GetData(), 0);
		int32 N = 0;
		for (uint8 V : Data)
		{
			N += V > 0;
		}
		return N;
	};
	int32 Comps = 0;
	Info->ForEachLandscapeProxy([&](ALandscapeProxy* Proxy)
	{
		for (ULandscapeComponent* C : Proxy->LandscapeComponents)
		{
			for (const FWeightmapLayerAllocationInfo& A : C->GetWeightmapLayerAllocations())
			{
				Comps += A.LayerInfo == Layer;
			}
		}
		return true;
	});
	return FString::Printf(TEXT("edit=%d final=%d comps=%d layers=%d editing=%s infolayers=%d"), Count(true), Count(false), Comps,
		Landscape->GetEditLayersConst().Num(), *Landscape->GetEditingLayer().ToString(), Info->Layers.Num());
}

bool UM80EditorLibrary::MakeVehiclePhysicsAsset(USkeletalMesh* Mesh, FName RootBone, FVector BoxMin, FVector BoxMax, float BeltHeight, float CabinLengthFraction)
{
	const int32 RootIndex = Mesh ? Mesh->GetRefSkeleton().FindBoneIndex(RootBone) : INDEX_NONE;
	if (RootIndex == INDEX_NONE)
	{
		return false;
	}
	// The boxes are given in component space; bodies live in the bone's frame, which an imported rig
	// usually rotates (Blender bones point up), so the boxes are carried into it.
	const FTransform ToBone = FAnimationRuntime::GetComponentSpaceTransformRefPose(Mesh->GetRefSkeleton(), RootIndex).Inverse();
	const FVector BoneScale = ToBone.GetScale3D().GetAbs();
	auto AddBox = [&ToBone, &BoneScale](USkeletalBodySetup* Body, const FVector& Center, const FVector& Size)
	{
		FKBoxElem Box(Size.X * BoneScale.X, Size.Y * BoneScale.Y, Size.Z * BoneScale.Z);
		Box.Center = ToBone.TransformPosition(Center);
		Box.Rotation = ToBone.GetRotation().Rotator();
		Body->AggGeom.BoxElems.Add(Box);
	};
	const FString Name = Mesh->GetName() + TEXT("_PhysicsAsset");
	const FString PackageName = FPackageName::GetLongPackagePath(Mesh->GetPackage()->GetName()) / Name;
	UPackage* Package = CreatePackage(*PackageName);
	UPhysicsAsset* Asset = FindObject<UPhysicsAsset>(Package, *Name);
	if (!Asset)
	{
		Asset = NewObject<UPhysicsAsset>(Package, *Name, RF_Public | RF_Standalone | RF_Transactional);
		FAssetRegistryModule::AssetCreated(Asset);
	}
	Asset->SkeletalBodySetups.Reset();
	Asset->ConstraintSetup.Reset();
	USkeletalBodySetup* Body = NewObject<USkeletalBodySetup>(Asset, NAME_None, RF_Transactional);
	Body->BoneName = RootBone;
	Body->PhysicsType = PhysType_Default;
	Body->CollisionTraceFlag = CTF_UseSimpleAsComplex;
	// Lower body: the whole length and width, from the bottom to the belt line.
	const FVector Size = BoxMax - BoxMin;
	AddBox(Body, FVector((BoxMin.X + BoxMax.X) * 0.5f, (BoxMin.Y + BoxMax.Y) * 0.5f, (BoxMin.Z + BeltHeight) * 0.5f),
		FVector(Size.X, Size.Y, FMath::Max(10.f, BeltHeight - BoxMin.Z)));
	// Cabin: a bit narrower and shorter, from the belt line to the roof.
	if (BoxMax.Z - BeltHeight > 10.f)
	{
		AddBox(Body, FVector((BoxMin.X + BoxMax.X) * 0.5f - Size.X * 0.05f, (BoxMin.Y + BoxMax.Y) * 0.5f, (BeltHeight + BoxMax.Z) * 0.5f),
			FVector(Size.X * CabinLengthFraction, Size.Y * 0.9f, BoxMax.Z - BeltHeight));
	}
	Asset->SkeletalBodySetups.Add(Body);
	Asset->UpdateBodySetupIndexMap();
	Asset->UpdateBoundsBodiesArray();
	Asset->SetPreviewMesh(Mesh);
	Asset->MarkPackageDirty();
	Mesh->SetPhysicsAsset(Asset);
	Mesh->MarkPackageDirty();
	return true;
}

bool UM80EditorLibrary::ConnectWorldPositionOffset(UMaterialExpression* From, const FString& OutputName)
{
	return From && UMaterialEditingLibrary::ConnectMaterialProperty(From, OutputName, MP_WorldPositionOffset);
}

UStaticMesh* UM80EditorLibrary::BakeBougainvillea(AM80Bougainvillea* Plant, const FString& Folder)
{
	if (!Plant)
	{
		return nullptr;
	}
	constexpr int32 NumLods = 3;
	TArray<UE::Geometry::FDynamicMesh3> Lods;
	Lods.SetNum(NumLods);
	for (int32 k = 0; k < NumLods; ++k)
	{
		Plant->BuildLOD(k, Lods[k]);
	}
	if (Lods[0].TriangleCount() == 0)
	{
		return nullptr;
	}
	const TArray<UMaterialInterface*> Materials = Plant->GetSlotMaterials();
	FString Label = Plant->GetActorLabel();
	for (TCHAR& Ch : Label)
	{
		if (!FChar::IsAlnum(Ch))
		{
			Ch = TEXT('_');
		}
	}
	const FString Name = TEXT("SM_M80_BGV_") + Label;
	const FString PackagePath = Folder / Name;
	UStaticMesh* StaticMesh = LoadObject<UStaticMesh>(nullptr, *(PackagePath + TEXT(".") + Name), nullptr, LOAD_NoWarn | LOAD_Quiet);
	if (StaticMesh)
	{
		// Re-bake in place so references and the asset path stay stable.
		StaticMesh->Modify();
		TArray<FStaticMaterial> Slots;
		for (UMaterialInterface* Material : Materials)
		{
			Slots.Add(FStaticMaterial(Material));
		}
		StaticMesh->SetStaticMaterials(Slots);
		StaticMesh->SetNumSourceModels(NumLods);
		FMeshSectionInfoMap SectionInfoMap;
		for (int32 k = 0; k < NumLods; ++k)
		{
			FMeshDescription Description;
			FStaticMeshAttributes(Description).Register();
			FDynamicMeshToMeshDescription Converter;
			Converter.Convert(&Lods[k], Description);
			for (int32 Section = 0; Section < Description.PolygonGroups().Num(); ++Section)
			{
				SectionInfoMap.Set(k, Section, FMeshSectionInfo(Section));
			}
			StaticMesh->CreateMeshDescription(k, MoveTemp(Description));
			StaticMesh->CommitMeshDescription(k);
		}
		StaticMesh->GetSectionInfoMap().CopyFrom(SectionInfoMap);
		StaticMesh->GetOriginalSectionInfoMap().CopyFrom(SectionInfoMap);
	}
	else
	{
		UE::AssetUtils::FStaticMeshAssetOptions Options;
		Options.NewAssetPath = PackagePath;
		Options.NumSourceModels = NumLods;
		Options.NumMaterialSlots = Materials.Num();
		Options.AssetMaterials = Materials;
		Options.bGenerateNaniteEnabledMesh = false;
		Options.bAllowDistanceField = false;
		Options.bCreatePhysicsBody = false;
		for (UE::Geometry::FDynamicMesh3& L : Lods)
		{
			Options.SourceMeshes.DynamicMeshes.Add(&L);
		}
		UE::AssetUtils::FStaticMeshResults Results;
		if (UE::AssetUtils::CreateStaticMeshAsset(Options, Results) != UE::AssetUtils::ECreateStaticMeshResult::Ok || !Results.StaticMesh)
		{
			return nullptr;
		}
		StaticMesh = Results.StaticMesh;
		FAssetRegistryModule::AssetCreated(StaticMesh);
	}
	// Levels of detail by screen size: full up close, fewer and larger cards from a few metres, a sketch far away.
	StaticMesh->bAutoComputeLODScreenSize = false;
	const float Screen[NumLods] = {1.f, 0.3f, 0.1f};
	for (int32 k = 0; k < NumLods; ++k)
	{
		FStaticMeshSourceModel& Source = StaticMesh->GetSourceModel(k);
		Source.ScreenSize.Default = Screen[k];
		Source.BuildSettings.bRecomputeNormals = false;
		Source.BuildSettings.bGenerateLightmapUVs = false;
		Source.BuildSettings.DistanceFieldResolutionScale = 0.f;
	}
	StaticMesh->NaniteSettings.bEnabled = false;
	StaticMesh->bGenerateMeshDistanceField = false;
	StaticMesh->Build();
	StaticMesh->PostEditChange();
	StaticMesh->MarkPackageDirty();
	Plant->ApplyBakedMesh(StaticMesh);
	return StaticMesh;
}

namespace
{
// The runtime hash set keeps its partitions private and Python cannot see them: they are read and written through
// reflection, as the World Settings panel does. Each partition is {Name, MainLayer, HLODSetups[{Name, PartitionLayer}]}.
template <typename FFunc>
void ForEachRuntimePartitionLayer(UWorld* World, FFunc&& Func)
{
	UWorldPartition* WorldPartition = World ? World->GetWorldPartition() : nullptr;
	UObject* Hash = WorldPartition ? WorldPartition->RuntimeHash.Get() : nullptr;
	FArrayProperty* Partitions = Hash ? FindFProperty<FArrayProperty>(Hash->GetClass(), TEXT("RuntimePartitions")) : nullptr;
	FStructProperty* Desc = Partitions ? CastField<FStructProperty>(Partitions->Inner) : nullptr;
	if (!Desc)
	{
		return;
	}
	FNameProperty* NameProp = FindFProperty<FNameProperty>(Desc->Struct, TEXT("Name"));
	FObjectProperty* MainProp = FindFProperty<FObjectProperty>(Desc->Struct, TEXT("MainLayer"));
	FArrayProperty* HLODsProp = FindFProperty<FArrayProperty>(Desc->Struct, TEXT("HLODSetups"));
	FStructProperty* Setup = HLODsProp ? CastField<FStructProperty>(HLODsProp->Inner) : nullptr;
	FScriptArrayHelper Items(Partitions, Partitions->ContainerPtrToValuePtr<void>(Hash));
	for (int32 i = 0; i < Items.Num(); ++i)
	{
		const uint8* Item = Items.GetRawPtr(i);
		const FName Partition = NameProp ? NameProp->GetPropertyValue_InContainer(Item) : NAME_None;
		Func(Partition, FName(TEXT("Main")), MainProp ? MainProp->GetObjectPropertyValue_InContainer(Item) : nullptr);
		if (!Setup)
		{
			continue;
		}
		FNameProperty* SetupName = FindFProperty<FNameProperty>(Setup->Struct, TEXT("Name"));
		FObjectProperty* SetupLayer = FindFProperty<FObjectProperty>(Setup->Struct, TEXT("PartitionLayer"));
		FScriptArrayHelper HLODs(HLODsProp, HLODsProp->ContainerPtrToValuePtr<void>(Item));
		for (int32 k = 0; k < HLODs.Num(); ++k)
		{
			const uint8* HLOD = HLODs.GetRawPtr(k);
			Func(Partition, SetupName ? SetupName->GetPropertyValue_InContainer(HLOD) : NAME_None,
				SetupLayer ? SetupLayer->GetObjectPropertyValue_InContainer(HLOD) : nullptr);
		}
	}
}

FNumericProperty* RuntimePartitionNumber(UObject* Layer, const TCHAR* Name)
{
	return Layer ? FindFProperty<FNumericProperty>(Layer->GetClass(), Name) : nullptr;
}
}

FString UM80EditorLibrary::DescribeRuntimePartitions(UWorld* World)
{
	FString Out;
	ForEachRuntimePartitionLayer(World, [&Out](FName Partition, FName Layer, UObject* Object)
	{
		Out += FString::Printf(TEXT("%s %s %s"), *Partition.ToString(), *Layer.ToString(), Object ? *Object->GetClass()->GetName() : TEXT("none"));
		for (const TCHAR* Name : {TEXT("CellSize"), TEXT("LoadingRange")})
		{
			if (FNumericProperty* Prop = RuntimePartitionNumber(Object, Name))
			{
				Out += FString::Printf(TEXT(" %s=%lld"), Name, Prop->GetSignedIntPropertyValue(Prop->ContainerPtrToValuePtr<void>(Object)));
			}
		}
		if (FBoolProperty* Block = Object ? FindFProperty<FBoolProperty>(Object->GetClass(), TEXT("bBlockOnSlowStreaming")) : nullptr)
		{
			Out += FString::Printf(TEXT(" BlockOnSlowStreaming=%d"), Block->GetPropertyValue_InContainer(Object) ? 1 : 0);
		}
		Out += TEXT("\n");
	});
	return Out;
}

bool UM80EditorLibrary::SetRuntimePartitionGrid(UWorld* World, FName PartitionName, int32 CellSize, int32 LoadingRange)
{
	bool bDone = false;
	ForEachRuntimePartitionLayer(World, [&](FName Partition, FName Layer, UObject* Object)
	{
		FNumericProperty* Cell = RuntimePartitionNumber(Object, TEXT("CellSize"));
		FNumericProperty* Range = RuntimePartitionNumber(Object, TEXT("LoadingRange"));
		if (Partition != PartitionName || Layer != FName(TEXT("Main")) || !Cell || !Range)
		{
			return;
		}
		Object->Modify();
		for (const TPair<FNumericProperty*, int32>& Change : {TPair<FNumericProperty*, int32>(Cell, CellSize), TPair<FNumericProperty*, int32>(Range, LoadingRange)})
		{
			Object->PreEditChange(Change.Key);
			Change.Key->SetIntPropertyValue(Change.Key->ContainerPtrToValuePtr<void>(Object), static_cast<int64>(Change.Value));
			FPropertyChangedEvent Event(Change.Key, EPropertyChangeType::ValueSet);
			Object->PostEditChangeProperty(Event);
		}
		bDone = true;
	});
	if (bDone)
	{
		World->GetWorldPartition()->RuntimeHash->Modify();
		World->MarkPackageDirty();
	}
	return bDone;
}

bool UM80EditorLibrary::SetRuntimePartitionBlockOnSlowStreaming(UWorld* World, FName PartitionName, bool bBlock)
{
	bool bDone = false;
	ForEachRuntimePartitionLayer(World, [&](FName Partition, FName Layer, UObject* Object)
	{
		FBoolProperty* Prop = Object ? FindFProperty<FBoolProperty>(Object->GetClass(), TEXT("bBlockOnSlowStreaming")) : nullptr;
		if (Partition != PartitionName || !Prop)
		{
			return;
		}
		Object->Modify();
		Object->PreEditChange(Prop);
		Prop->SetPropertyValue_InContainer(Object, bBlock);
		FPropertyChangedEvent Event(Prop, EPropertyChangeType::ValueSet);
		Object->PostEditChangeProperty(Event);
		bDone = true;
	});
	if (bDone)
	{
		World->GetWorldPartition()->RuntimeHash->Modify();
		World->MarkPackageDirty();
	}
	return bDone;
}

FString UM80EditorLibrary::ReadFaceDnaVertices(const FString& DnaPath, TArray<FVector>& Head, TArray<FVector>& LeftEye,
	TArray<FVector>& RightEye, TArray<FVector>& Teeth)
{
	Head.Reset();
	LeftEye.Reset();
	RightEye.Reset();
	Teeth.Reset();
	// Same reading as the Creator's own DNA import (Maya source axes, transformed), geometry of LOD0 only.
	const TSharedPtr<IDNAReader> Dna = LoadDNAFromFile(DnaPath, FDNAConfig::Source(ECoordinateSystemTransformPolicy::Transform));
	if (!Dna.IsValid())
	{
		return FString();
	}
	FString Info;
	for (uint16 Mesh = 0; Mesh < Dna->GetMeshCount(); ++Mesh)
	{
		const FString Name = Dna->GetMeshName(Mesh);
		const uint32 Count = Dna->GetVertexPositionCount(Mesh);
		Info += FString::Printf(TEXT("%d %s %u\n"), Mesh, *Name, Count);
		// Mesh names of every MetaHuman DNA: head_lod0_mesh, teeth_lod0_mesh, eyeLeft_lod0_mesh, eyeRight_lod0_mesh.
		TArray<FVector>* Target = Name.StartsWith(TEXT("head_lod0")) ? &Head : Name.StartsWith(TEXT("teeth_lod0")) ? &Teeth
			: Name.StartsWith(TEXT("eyeLeft_lod0")) ? &LeftEye : Name.StartsWith(TEXT("eyeRight_lod0")) ? &RightEye : nullptr;
		if (Target && Target->IsEmpty())
		{
			Target->Reserve(Count);
			for (uint32 Vertex = 0; Vertex < Count; ++Vertex)
			{
				Target->Add(Dna->GetVertexPosition(Mesh, Vertex));
			}
		}
	}
	return Info;
}

bool UM80EditorLibrary::ResetMetaHumanNeck(UMetaHumanCharacter* Character)
{
	UMetaHumanCharacterEditorSubsystem* Subsystem = GEditor ? GEditor->GetEditorSubsystem<UMetaHumanCharacterEditorSubsystem>() : nullptr;
	if (!Character || !Subsystem || !Subsystem->IsObjectAddedForEditing(Character))
	{
		return false;
	}
	TSharedRef<FMetaHumanCharacterIdentity::FState> State = Subsystem->CopyFaceState(Character);
	State->ResetNeckRegion();
	Subsystem->ApplyFaceState(Character, State);
	return true;
}

static UMetaHumanCharacterEditorSubsystem* EditingSubsystem(UMetaHumanCharacter* Character)
{
	UMetaHumanCharacterEditorSubsystem* Subsystem = GEditor ? GEditor->GetEditorSubsystem<UMetaHumanCharacterEditorSubsystem>() : nullptr;
	return Character && Subsystem && Subsystem->IsObjectAddedForEditing(Character) ? Subsystem : nullptr;
}

TArray<FVector> UM80EditorLibrary::GetMetaHumanFaceRegions(UMetaHumanCharacter* Character)
{
	TArray<FVector> Regions;
	if (UMetaHumanCharacterEditorSubsystem* Subsystem = EditingSubsystem(Character))
	{
		for (const FVector3f& Gizmo : Subsystem->GetFaceGizmos(Character))
		{
			Regions.Add(FVector(Gizmo));
		}
	}
	return Regions;
}

bool UM80EditorLibrary::BlendMetaHumanFaceRegion(UMetaHumanCharacter* Character, int32 Region,
	const TArray<UMetaHumanCharacter*>& Sources, const TArray<float>& Weights, bool bShapeOnly)
{
	UMetaHumanCharacterEditorSubsystem* Subsystem = EditingSubsystem(Character);
	if (!Subsystem || Sources.Num() == 0 || Sources.Num() != Weights.Num())
	{
		return false;
	}
	TArray<TSharedRef<FMetaHumanCharacterIdentity::FState>> States;
	TArray<TPair<float, const FMetaHumanCharacterIdentity::FState*>> Weighted;
	for (int32 i = 0; i < Sources.Num(); ++i)
	{
		if (!Sources[i] || !Subsystem->IsObjectAddedForEditing(Sources[i]))
		{
			return false;
		}
		States.Add(Subsystem->CopyFaceState(Sources[i]));
		Weighted.Add({ Weights[i], &States.Last().Get() });
	}
	TSharedRef<FMetaHumanCharacterIdentity::FState> State = Subsystem->CopyFaceState(Character);
	State->BlendPresets(Region, Weighted, bShapeOnly ? EBlendOptions::Proportions : EBlendOptions::Both, true);
	Subsystem->ApplyFaceState(Character, State);
	return true;
}

FVector UM80EditorLibrary::MoveMetaHumanFaceRegion(UMetaHumanCharacter* Character, int32 Region, FVector Offset, float ScaleFactor)
{
	UMetaHumanCharacterEditorSubsystem* Subsystem = EditingSubsystem(Character);
	if (!Subsystem)
	{
		return FVector::ZeroVector;
	}
	TSharedRef<FMetaHumanCharacterIdentity::FState> State = Subsystem->CopyFaceState(Character);
	if (Region < 0 || Region >= State->NumGizmos())
	{
		return FVector::ZeroVector;
	}
	FVector3f Position;
	State->GetGizmoPosition(Region, Position);
	if (!Offset.IsNearlyZero())
	{
		State->SetGizmoPosition(Region, Position + FVector3f(Offset), true, true);
	}
	if (!FMath::IsNearlyEqual(ScaleFactor, 1.0f))
	{
		float Scale = 1.0f;
		State->GetGizmoScale(Region, Scale);
		State->SetGizmoScale(Region, Scale * ScaleFactor, true, true);
	}
	State->GetGizmoPosition(Region, Position);
	Subsystem->ApplyFaceState(Character, State);
	return FVector(Position);
}

FString UM80EditorLibrary::GetMetaHumanBuildStatus(UMetaHumanCharacter* Character)
{
	UMetaHumanCharacterEditorSubsystem* Subsystem = EditingSubsystem(Character);
	if (!Subsystem)
	{
		return TEXT("Character not added for editing");
	}
	FText Error;
	return Subsystem->CanBuildMetaHuman(Character, Error) ? FString() : Error.ToString();
}

FString UM80EditorLibrary::DescribeDataflow(UDataflow* Dataflow)
{
	TSharedPtr<UE::Dataflow::FGraph> Graph = Dataflow ? Dataflow->GetDataflow() : nullptr;
	if (!Graph)
	{
		return FString();
	}
	FString Text;
	for (const TSharedPtr<FDataflowNode>& Node : Graph->GetNodes())
	{
		if (!Node)
		{
			continue;
		}
		Text += FString::Printf(TEXT("%s [%s]\n"), *Node->GetName().ToString(), *Node->GetType().ToString());
		if (const UScriptStruct* Struct = Node->TypedScriptStruct())
		{
			for (TFieldIterator<FProperty> It(Struct); It; ++It)
			{
				if (It->HasAnyPropertyFlags(CPF_Edit))
				{
					FString Value;
					It->ExportTextItem_InContainer(Value, Node.Get(), nullptr, nullptr, PPF_None);
					Text += FString::Printf(TEXT("    %s = %s\n"), *It->GetName(), *Value.Left(300));
				}
			}
		}
		for (const FDataflowInput* Input : Node->GetInputs())
		{
			const FDataflowOutput* From = Input ? Input->GetConnection() : nullptr;
			if (From && From->GetOwningNode())
			{
				Text += FString::Printf(TEXT("    <%s> <- %s.%s\n"), *Input->GetName().ToString(),
					*From->GetOwningNode()->GetName().ToString(), *From->GetName().ToString());
			}
		}
	}
	return Text;
}

bool UM80EditorLibrary::SetDataflowNodeProperty(UDataflow* Dataflow, FName Node, const FString& Property, const FString& Value)
{
	TSharedPtr<UE::Dataflow::FGraph> Graph = Dataflow ? Dataflow->GetDataflow() : nullptr;
	TSharedPtr<FDataflowNode> Found = Graph ? Graph->FindBaseNode(Node) : nullptr;
	const UScriptStruct* Struct = Found ? Found->TypedScriptStruct() : nullptr;
	FProperty* Prop = Struct ? Struct->FindPropertyByName(FName(*Property)) : nullptr;
	if (!Prop)
	{
		return false;
	}
	Dataflow->Modify();
	if (!Prop->ImportText_InContainer(*Value, Found.Get(), Dataflow, PPF_None))
	{
		return false;
	}
	Found->Invalidate();
	Dataflow->MarkPackageDirty();
	return true;
}

// Rebuilding a cloth or outfit asset that is already loaded replaces its render data, and the 5.8 engine releases
// everything but the LODs' half-edge buffers first (fatal: "FRenderResource was deleted without being released",
// FSkeletalMeshLODRenderData.HalfEdgeBuffer). Released here before a rebuild.
static void ReleaseHalfEdgeBuffers(UObject* Asset)
{
	UChaosClothAssetBase* Cloth = Cast<UChaosClothAssetBase>(Asset);
	FSkeletalMeshRenderData* RenderData = Cloth ? Cloth->GetResourceForRendering() : nullptr;
	if (!RenderData)
	{
		return;
	}
	for (FSkeletalMeshLODRenderData& Lod : RenderData->LODRenderData)
	{
		BeginReleaseResource(&Lod.HalfEdgeBuffer);
	}
	FlushRenderingCommands();
}

UDataflow* UM80EditorLibrary::GetAssetDataflow(UObject* Asset)
{
	return Asset ? UE::Dataflow::InstanceUtils::GetDataflowAssetFromObject(Asset) : nullptr;
}

bool UM80EditorLibrary::RebuildAssetFromDataflow(UObject* Asset, UDataflow* Dataflow, FName Terminal)
{
	IDataflowInstanceInterface* Instance = Asset ? UE::Dataflow::InstanceUtils::GetDataflowInterfaceFromObject(Asset) : nullptr;
	if (!Instance)
	{
		return false;
	}
	Asset->Modify();
	ReleaseHalfEdgeBuffers(Asset);
	if (Dataflow)
	{
		Instance->GetDataflowInstance().SetDataflowAsset(Dataflow);
	}
	if (!Terminal.IsNone())
	{
		Instance->GetDataflowInstance().SetDataflowTerminal(Terminal);
	}
	const bool bUpdated = Instance->GetDataflowInstance().UpdateOwnerAsset(true);
	Asset->MarkPackageDirty();
	return bUpdated;
}

bool UM80EditorLibrary::SetObjectPropertyText(UObject* Object, FName Property, const FString& Value)
{
	FProperty* Prop = Object ? Object->GetClass()->FindPropertyByName(Property) : nullptr;
	if (!Prop)
	{
		return false;
	}
	Object->Modify();
	if (!Prop->ImportText_InContainer(*Value, Object, Object, PPF_None))
	{
		return false;
	}
	FPropertyChangedEvent Event(Prop, EPropertyChangeType::ValueSet);
	Object->PostEditChangeProperty(Event);
	Object->MarkPackageDirty();
	return true;
}

bool UM80EditorLibrary::SetOutfitSizes(UObject* Outfit, const TArray<UObject*>& ClothAssets, const TArray<FString>& SizeNames,
	const TArray<USkeletalMesh*>& Bodies)
{
	IDataflowInstanceInterface* Instance = Outfit ? UE::Dataflow::InstanceUtils::GetDataflowInterfaceFromObject(Outfit) : nullptr;
	if (!Instance || ClothAssets.Num() == 0 || ClothAssets.Num() != SizeNames.Num() || ClothAssets.Num() != Bodies.Num())
	{
		return false;
	}
	TArray<FChaosSizedOutfitSource> Sizes;
	for (int32 i = 0; i < ClothAssets.Num(); ++i)
	{
		FChaosSizedOutfitSource& Size = Sizes.AddDefaulted_GetRef();
		Size.SourceAsset = Cast<UChaosClothAssetBase>(ClothAssets[i]);
		Size.SizeName = SizeNames[i];
		Size.SourceBodyParts = { Bodies[i] };
		if (!Size.SourceAsset || !Bodies[i])
		{
			return false;
		}
	}
	Outfit->Modify();
	ReleaseHalfEdgeBuffers(Outfit);
	FDataflowInstance& Dataflow = Instance->GetDataflowInstance();
	if (!Dataflow.GetVariableOverrides().OverrideVariableStructArray(TEXT("SizedOutfitSource"), Sizes))
	{
		return false;
	}
	const bool bUpdated = Dataflow.UpdateOwnerAsset(true);
	Outfit->MarkPackageDirty();
	return bUpdated;
}

FString UM80EditorLibrary::GetObjectPropertyText(UObject* Object, FName Property)
{
	FProperty* Prop = Object ? Object->GetClass()->FindPropertyByName(Property) : nullptr;
	FString Value;
	if (Prop)
	{
		Prop->ExportTextItem_InContainer(Value, Object, nullptr, Object, PPF_None);
	}
	return Value;
}

bool UM80EditorLibrary::ConnectMaterialInput(UMaterialExpression* Expression, const FString& OutputName, const FString& Input)
{
	const int64 Value = StaticEnum<EMaterialProperty>()->GetValueByNameString(Input);
	return Expression && Value != INDEX_NONE
		&& UMaterialEditingLibrary::ConnectMaterialProperty(Expression, OutputName, static_cast<EMaterialProperty>(Value));
}

int32 UM80EditorLibrary::SetSkeletalLODScreenSizes(USkeletalMesh* Mesh, const TArray<float>& ScreenSizes)
{
	if (!Mesh)
	{
		return 0;
	}
	int32 Set = 0;
	Mesh->Modify();
	for (int32 i = 1; i < ScreenSizes.Num() && i < Mesh->GetLODNum(); ++i)
	{
		if (FSkeletalMeshLODInfo* Info = Mesh->GetLODInfo(i))
		{
			Info->ScreenSize = FPerPlatformFloat(ScreenSizes[i]);
			++Set;
		}
	}
	Mesh->PostEditChange();
	Mesh->MarkPackageDirty();
	return Set;
}
