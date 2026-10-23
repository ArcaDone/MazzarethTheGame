#include "M80DynamicMeshHLODBuilder.h"
#include "M80DynamicMeshHLOD.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMeshToMeshDescription.h"
#include "Engine/StaticMesh.h"
#include "StaticMeshAttributes.h"
#include "StaticMeshOperations.h"

TArray<UActorComponent*> UM80DynamicMeshHLODBuilder::Build(const FHLODBuildContext& InHLODBuildContext, const TArray<UActorComponent*>& InSourceComponents) const
{
	// Vertices relative to the HLOD actor: world positions of the town are too large for float vertices.
	const FVector Pivot = InHLODBuildContext.WorldPosition;
	FMeshDescription Merged;
	FStaticMeshAttributes(Merged).Register();
	FStaticMeshOperations::FAppendSettings Settings;
	for (bool& bMerge : Settings.bMergeUVChannels)
	{
		bMerge = true;
	}
	// Each source section is named after its material: the merge joins the sections that share one.
	TArray<UMaterialInterface*> Materials;
	int32 Sources = 0;
	for (const UM80DynamicMeshHLODComponent* Source : FilterComponents<UM80DynamicMeshHLODComponent>(InSourceComponents))
	{
		for (UDynamicMeshComponent* Mesh : Source->GetSourceMeshes())
		{
			FMeshDescription Description;
			FStaticMeshAttributes Attributes(Description);
			Attributes.Register();
			Mesh->ProcessMesh([&Description](const UE::Geometry::FDynamicMesh3& Dynamic)
			{
				FDynamicMeshToMeshDescription Converter;
				Converter.Convert(&Dynamic, Description);
			});
			// The converter makes polygon group N from material ID N.
			TPolygonGroupAttributesRef<FName> Slots = Attributes.GetPolygonGroupMaterialSlotNames();
			for (const FPolygonGroupID Group : Description.PolygonGroups().GetElementIDs())
			{
				const int32 Index = Materials.AddUnique(Mesh->GetMaterial(Group.GetValue()));
				Slots[Group] = FName(*FString::Printf(TEXT("M80Slot%d"), Index));
			}
			FTransform Transform = Mesh->GetComponentTransform();
			Transform.AddToTranslation(-Pivot);
			Settings.MeshTransform = Transform;
			FStaticMeshOperations::AppendMeshDescription(Description, Merged, Settings);
			++Sources;
		}
	}
	const int32 Triangles = Merged.Triangles().Num();
	if (Triangles == 0)
	{
		return {};
	}

	const FName Name = MakeUniqueObjectName(InHLODBuildContext.AssetsOuter, UStaticMesh::StaticClass(), FName(InHLODBuildContext.AssetsBaseName + TEXT("_M80Dynamic")));
	UStaticMesh* StaticMesh = NewObject<UStaticMesh>(InHLODBuildContext.AssetsOuter, Name);
	StaticMesh->SetFlags(InHLODBuildContext.AssetsObjectFlags);
	FStaticMeshSourceModel& Model = StaticMesh->AddSourceModel();
	// The generators already wrote normals; the far view needs no distance field.
	Model.BuildSettings.bRecomputeNormals = false;
	Model.BuildSettings.bRecomputeTangents = true;
	Model.BuildSettings.DistanceFieldResolutionScale = 0;
	FMeshDescription* Description = StaticMesh->CreateMeshDescription(0);
	*Description = MoveTemp(Merged);
	// Material slots in polygon group order, so section N draws with slot N.
	TPolygonGroupAttributesConstRef<FName> Slots = FStaticMeshConstAttributes(*Description).GetPolygonGroupMaterialSlotNames();
	for (const FPolygonGroupID Group : Description->PolygonGroups().GetElementIDs())
	{
		const FString Slot = Slots[Group].ToString();
		const int32 Index = FCString::Atoi(*Slot.RightChop(7));
		StaticMesh->GetStaticMaterials().Add(FStaticMaterial(Materials.IsValidIndex(Index) ? Materials[Index] : nullptr, Slots[Group], Slots[Group]));
	}
	StaticMesh->CommitMeshDescription(0);
	StaticMesh->GetNaniteSettings().bEnabled = true;
	StaticMesh->SetImportVersion(EImportStaticMeshVersion::LastVersion);
	UStaticMesh::BatchBuild({StaticMesh});

	UStaticMeshComponent* Component = NewObject<UStaticMeshComponent>();
	Component->SetStaticMesh(StaticMesh);
	Component->SetWorldLocation(Pivot);
	UE_LOGF(LogHLODBuilder, Display, "M80 dynamic meshes: %d meshes, %d triangles, %d materials into %ls", Sources, Triangles, Materials.Num(), *Name.ToString());
	return {Component};
}
