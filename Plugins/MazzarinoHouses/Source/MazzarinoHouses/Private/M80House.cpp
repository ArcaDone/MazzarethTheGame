#include "M80House.h"
#include "M80HouseBuilder.h"
#include "M80Polygon.h"
#include "M80ExclusionZone.h"
#include "Components/SplineComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Materials/Material.h"
#include "MaterialDomain.h"
#include "HAL/PlatformTime.h"
#include "Engine/CollisionProfile.h"
#include "Algo/Reverse.h"

AM80House::AM80House()
{
	PrimaryActorTick.bCanEverTick = false;

	Footprint = CreateDefaultSubobject<USplineComponent>(TEXT("Footprint"));
	SetRootComponent(Footprint);
	Footprint->SetClosedLoop(true, false);
	Footprint->ClearSplinePoints(false);
	const TArray<FVector> Square = {{-500, -400, 0}, {500, -400, 0}, {500, 400, 0}, {-500, 400, 0}};
	Footprint->SetSplinePoints(Square, ESplineCoordinateSpace::Local, false);
	for (int32 i = 0; i < Square.Num(); ++i)
	{
		Footprint->SetSplinePointType(i, ESplinePointType::Linear, false);
	}
	Footprint->UpdateSpline();
	Footprint->bDrawDebug = true;
	Footprint->SetMobility(EComponentMobility::Static);

	Shell = CreateDefaultSubobject<UDynamicMeshComponent>(TEXT("Shell"));
	Shell->SetupAttachment(Footprint);
	Shell->SetMobility(EComponentMobility::Static);
	Shell->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);
	Shell->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);

	Baked = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Baked"));
	Baked->SetupAttachment(Footprint);
	Baked->SetMobility(EComponentMobility::Static);
	Baked->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	Baked->SetVisibility(false);
}

bool AM80House::NeedsRebuild() const
{
	if (IsBaked())
	{
		return false;
	}
	int32 Triangles = 0;
	Shell->ProcessMesh([&Triangles](const UE::Geometry::FDynamicMesh3& Mesh) { Triangles = Mesh.TriangleCount(); });
	return Triangles == 0;
}

void AM80House::BeginPlay()
{
	Super::BeginPlay();
	if (IsExcluded())
	{
		SetExcludedVisuals(true);
		return;
	}
	if (NeedsRebuild())
	{
		Rebuild();
	}
	else if (PropComponents.IsEmpty() && SavedProps.Num())
	{
		RefreshProps();
	}
}

bool AM80House::IsBaked() const
{
	return Baked && Baked->GetStaticMesh() != nullptr;
}

void AM80House::ApplyBakedMesh(UStaticMesh* Mesh)
{
	if (!Mesh)
	{
		return;
	}
	Baked->SetStaticMesh(Mesh);
	Baked->SetVisibility(true);
	Baked->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	// The baked asset carries the vertex colours and UV1 unit data; copy the per-lot values too.
	for (int32 i = 0; i < 8; ++i)
	{
		const float* Value = Shell->GetDefaultCustomPrimitiveData().Data.IsValidIndex(i) ? &Shell->GetDefaultCustomPrimitiveData().Data[i] : nullptr;
		if (Value)
		{
			Baked->SetDefaultCustomPrimitiveDataFloat(i, *Value);
		}
	}
	// Free the preview: an empty dynamic mesh is not saved with the level.
	Shell->SetMesh(UE::Geometry::FDynamicMesh3());
	Shell->SetVisibility(false);
	Shell->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	BuildInfo += TEXT(" | cotta in ") + Mesh->GetName();
	SetExcludedVisuals(IsExcluded());
}

uint32 AM80House::ComputeInputHash() const
{
	FString Params;
	FM80HouseParams::StaticStruct()->ExportText(Params, &House, nullptr, nullptr, PPF_None, nullptr);
	uint32 Hash = GetTypeHash(Params);
	for (const FVector2D& Q : LocalFootprint())
	{
		Hash = HashCombineFast(Hash, GetTypeHash(Q));
	}
	const FTransform& T = GetActorTransform();
	Hash = HashCombineFast(Hash, GetTypeHash(T.GetLocation()));
	Hash = HashCombineFast(Hash, GetTypeHash(T.GetRotation().Rotator().Yaw));
	return Hash;
}

void AM80House::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	// The editor also runs construction when a level loads: skip if nothing changed.
	if (bLiveRebuild && !IsExcluded() && (ComputeInputHash() != LastInputHash || NeedsRebuild()))
	{
		Rebuild();
	}
	else if (PropComponents.IsEmpty() && SavedProps.Num())
	{
		RefreshProps();
	}
	SetExcludedVisuals(IsExcluded());
}

bool AM80House::IsExcluded() const
{
	if (bDisabled)
	{
		return true;
	}
	const TArray<FVector2D> P = GetFootprintWorld2D();
	if (P.IsEmpty())
	{
		return false;
	}
	FVector2D C(0, 0);
	for (const FVector2D& Q : P)
	{
		C += Q;
	}
	C /= P.Num();
	if (AM80ExclusionZone::IsPointExcluded(this, FVector(C.X, C.Y, 0)))
	{
		return true;
	}
	// Also when most of the house is inside a zone even if its centre is not (corner, L-shaped lots).
	int32 Inside = 0, Total = 0;
	for (int32 i = 0; i < P.Num(); ++i)
	{
		const FVector2D& A = P[i];
		const FVector2D& B = P[(i + 1) % P.Num()];
		for (const double F : {0.0, 0.5})
		{
			const FVector2D Q = FMath::Lerp(FMath::Lerp(A, B, F), C, 0.15);
			Inside += AM80ExclusionZone::IsPointExcluded(this, FVector(Q.X, Q.Y, 0)) ? 1 : 0;
			++Total;
		}
	}
	return Total > 0 && Inside * 2 > Total;
}

void AM80House::ApplyExclusion()
{
	const bool bExcluded = IsExcluded();
	if (!bExcluded && NeedsRebuild())
	{
		Rebuild();
		return;
	}
	if (!bExcluded && PropComponents.IsEmpty() && SavedProps.Num())
	{
		RefreshProps();
	}
	SetExcludedVisuals(bExcluded);
}

void AM80House::SetExcludedVisuals(bool bExcluded)
{
	const bool bBaked = IsBaked();
	Shell->SetVisibility(!bExcluded && !bBaked);
	Shell->SetCollisionEnabled(!bExcluded && !bBaked ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
	Baked->SetVisibility(!bExcluded && bBaked);
	Baked->SetCollisionEnabled(!bExcluded && bBaked ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
	for (UInstancedStaticMeshComponent* C : PropComponents)
	{
		if (C)
		{
			C->SetVisibility(!bExcluded);
			if (bExcluded)
			{
				C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			}
		}
	}	// Details attached to the house (posters, ...) follow it.
	TArray<AActor*> Attached;
	GetAttachedActors(Attached, true, true);
	for (AActor* A : Attached)
	{
		if (A)
		{
			A->SetActorHiddenInGame(bExcluded);
			A->SetActorEnableCollision(!bExcluded);
#if WITH_EDITOR
			A->SetIsTemporarilyHiddenInEditor(bExcluded);
#endif
		}
	}
}

TArray<FVector2D> AM80House::LocalFootprint() const
{
	TArray<FVector2D> Points;
	for (int32 i = 0; i < Footprint->GetNumberOfSplinePoints(); ++i)
	{
		const FVector L = Footprint->GetLocationAtSplinePoint(i, ESplineCoordinateSpace::Local);
		Points.Add(FVector2D(L.X, L.Y));
	}
	return Points;
}

TArray<FVector2D> AM80House::GetFootprintWorld2D() const
{
	TArray<FVector2D> Local = LocalFootprint();
	M80Poly::Clean(Local);
	const FTransform& T = GetActorTransform();
	TArray<FVector2D> World;
	for (const FVector2D& Q : Local)
	{
		const FVector W = T.TransformPosition(FVector(Q.X, Q.Y, 0));
		World.Add(FVector2D(W.X, W.Y));
	}
	if (M80Poly::SignedArea(World) < 0)
	{
		Algo::Reverse(World);
	}
	return World;
}

void AM80House::SetFootprintWorld(const TArray<FVector>& WorldPoints)
{
	if (WorldPoints.Num() < 3)
	{
		return;
	}
	FVector Centroid = FVector::ZeroVector;
	for (const FVector& Q : WorldPoints)
	{
		Centroid += Q;
	}
	Centroid /= WorldPoints.Num();
	SetActorLocation(Centroid);
	TArray<FVector> Local;
	for (const FVector& Q : WorldPoints)
	{
		Local.Add(GetActorTransform().InverseTransformPosition(FVector(Q.X, Q.Y, Centroid.Z)));
	}
	Footprint->ClearSplinePoints(false);
	Footprint->SetSplinePoints(Local, ESplineCoordinateSpace::Local, false);
	for (int32 i = 0; i < Local.Num(); ++i)
	{
		Footprint->SetSplinePointType(i, ESplinePointType::Linear, false);
	}
	Footprint->SetClosedLoop(true, false);
	Footprint->UpdateSpline();
}

double AM80House::FGroundGrid::Sample(const FVector2D& World) const
{
	if (NX < 2 || NY < 2)
	{
		return Z.Num() ? Z[0] : 0.0;
	}
	const double FX = FMath::Clamp((World.X - Origin.X) / Step, 0.0, NX - 1.001);
	const double FY = FMath::Clamp((World.Y - Origin.Y) / Step, 0.0, NY - 1.001);
	const int32 IX = FMath::FloorToInt(FX), IY = FMath::FloorToInt(FY);
	const double TX = FX - IX, TY = FY - IY;
	auto At = [&](int32 X, int32 Y) { return Z[Y * NX + X]; };
	return FMath::Lerp(FMath::Lerp(At(IX, IY), At(IX + 1, IY), TX), FMath::Lerp(At(IX, IY + 1), At(IX + 1, IY + 1), TX), TY);
}

AM80House::FGroundGrid AM80House::SampleGround(const TArray<FVector2D>& World2D) const
{
	FGroundGrid Grid;
	const double ActorZ = GetActorLocation().Z;
	FBox2D Bounds(World2D);
	Bounds = Bounds.ExpandBy(400.0);
	const FVector2D Size = Bounds.GetSize();
	Grid.Step = FMath::Max(100.0, FMath::Max(Size.X, Size.Y) / 60.0);
	Grid.Origin = Bounds.Min;
	Grid.NX = FMath::CeilToInt(Size.X / Grid.Step) + 1;
	Grid.NY = FMath::CeilToInt(Size.Y / Grid.Step) + 1;
	Grid.Z.SetNumUninitialized(Grid.NX * Grid.NY);

	UWorld* World = GetWorld();
	const bool bTrace = World && House.bFollowTerrain;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(M80HouseGround), true, this);
	const FCollisionObjectQueryParams Objects(ECC_WorldStatic);
	TArray<FHitResult> Hits;
	for (int32 Y = 0; Y < Grid.NY; ++Y)
	{
		for (int32 X = 0; X < Grid.NX; ++X)
		{
			double Height = ActorZ;
			if (bTrace)
			{
				const FVector2D Q = Grid.Origin + FVector2D(X, Y) * Grid.Step;
				Hits.Reset();
				World->LineTraceMultiByObjectType(Hits, FVector(Q.X, Q.Y, ActorZ + 30000), FVector(Q.X, Q.Y, ActorZ - 30000), Objects, Params);
				for (const FHitResult& Hit : Hits)
				{
					const AActor* HitActor = Hit.GetActor();
					const UPrimitiveComponent* Comp = Hit.GetComponent();
					// Houses, scattered props and anything tagged out never count as ground.
					if ((HitActor && (HitActor->IsA<AM80House>() || HitActor->ActorHasTag(TEXT("M80IgnoreGround")))) ||
						(Comp && Comp->IsA<UInstancedStaticMeshComponent>()))
					{
						continue;
					}
					Height = Hit.ImpactPoint.Z;
					break;
				}
			}
			Grid.Z[Y * Grid.NX + X] = Height;
		}
	}
	return Grid;
}

void AM80House::ResolveEdges(const TArray<FVector2D>& Local, TArray<EM80EdgeKind>& OutKinds, int32& OutFront) const
{
	const FTransform& T = GetActorTransform();
	auto ToWorld = [&](const FVector2D& Q) { const FVector W = T.TransformPosition(FVector(Q.X, Q.Y, 0)); return FVector2D(W.X, W.Y); };

	TArray<TArray<FVector2D>> Others;
	TArray<USplineComponent*> Roads;
	if (UWorld* World = GetWorld())
	{
		const FBox Mine = Footprint->Bounds.GetBox().ExpandBy(2000);
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			if (*It == this)
			{
				continue;
			}
			if (const AM80House* Other = Cast<AM80House>(*It))
			{
				if (Other->Footprint && Mine.Intersect(Other->Footprint->Bounds.GetBox()))
				{
					Others.Add(Other->GetFootprintWorld2D());
				}
			}
			else if (It->GetClass()->GetName().Contains(TEXT("RoadSpline")))
			{
				if (USplineComponent* S = It->FindComponentByClass<USplineComponent>())
				{
					Roads.Add(S);
				}
			}
		}
	}

	const int32 N = Local.Num();
	OutKinds.SetNum(N);
	double BestLength = -1;
	OutFront = 0;
	for (int32 e = 0; e < N; ++e)
	{
		EM80EdgeKind Kind = House.EdgeKinds.IsValidIndex(e) ? House.EdgeKinds[e] : EM80EdgeKind::Auto;
		const FVector2D A = Local[e], B = Local[(e + 1) % N];
		const FVector2D Normal = M80Poly::EdgeNormal(Local, e);
		if (Kind == EM80EdgeKind::Auto)
		{
			Kind = EM80EdgeKind::Street;
			if (House.bDetectPartyWalls && Others.Num())
			{
				int32 Inside = 0;
				for (double F : {0.2, 0.5, 0.8})
				{
					const FVector2D Probe = ToWorld(FMath::Lerp(A, B, F) + Normal * 60.0);
					for (const TArray<FVector2D>& Poly : Others)
					{
						if (M80Poly::Contains(Poly, Probe))
						{
							++Inside;
							break;
						}
					}
				}
				if (Inside >= 2)
				{
					Kind = EM80EdgeKind::Party;
				}
			}
			if (Kind == EM80EdgeKind::Street && Roads.Num())
			{
				const FVector2D Mid = ToWorld((A + B) * 0.5 + Normal * 150.0);
				const FVector Probe(Mid.X, Mid.Y, GetActorLocation().Z);
				double Nearest = TNumericLimits<double>::Max();
				for (const USplineComponent* S : Roads)
				{
					const FVector C = S->FindLocationClosestToWorldLocation(Probe, ESplineCoordinateSpace::World);
					Nearest = FMath::Min(Nearest, FVector2D::Distance(FVector2D(C.X, C.Y), Mid));
				}
				if (Nearest > 900)
				{
					Kind = EM80EdgeKind::Back;
				}
			}
		}
		OutKinds[e] = Kind;
		const double Length = FVector2D::Distance(A, B) * (Kind == EM80EdgeKind::Street ? 2.0 : Kind == EM80EdgeKind::Back ? 1.0 : 0.0);
		if (Length > BestLength)
		{
			BestLength = Length;
			OutFront = e;
		}
	}
	if (House.FrontEdge >= 0 && House.FrontEdge < N)
	{
		OutFront = House.FrontEdge;
		if (OutKinds[OutFront] == EM80EdgeKind::Party)
		{
			OutKinds[OutFront] = EM80EdgeKind::Street;
		}
	}
	if (OutKinds[OutFront] == EM80EdgeKind::Back)
	{
		OutKinds[OutFront] = EM80EdgeKind::Street;
	}
}

void AM80House::ApplyMaterials(const UM80HouseStyle* Style)
{
	UMaterialInterface* Fallback = UMaterial::GetDefaultMaterial(MD_Surface);
	auto Pick = [&](UMaterialInterface* M, UMaterialInterface* Alt = nullptr) { return M ? M : (Alt ? Alt : Fallback); };
	TArray<UMaterialInterface*> Set;
	Set.Init(Fallback, M80Slot::Count);
	if (Style)
	{
		Set[M80Slot::WallAshlar] = Pick(Style->AshlarMaterial);
		Set[M80Slot::WallRubble] = Pick(Style->RubbleMaterial, Style->AshlarMaterial);
		Set[M80Slot::WallPlaster] = Pick(Style->PlasterMaterial, Style->AshlarMaterial);
		Set[M80Slot::WallPlasterWorn] = Pick(Style->PlasterWornMaterial, Style->PlasterMaterial);
		Set[M80Slot::Trim] = Pick(Style->TrimMaterial);
		Set[M80Slot::Roof] = Pick(Style->RoofMaterial);
		Set[M80Slot::Terrace] = Pick(Style->TerraceMaterial);
		Set[M80Slot::Wood] = Pick(Style->WoodMaterial);
		Set[M80Slot::Glass] = Pick(Style->GlassMaterial);
		Set[M80Slot::Iron] = Pick(Style->IronMaterial);
		Set[M80Slot::RawWall] = Pick(Style->RawWallMaterial, Style->RubbleMaterial);
		Set[M80Slot::Brick] = Pick(Style->BrickMaterial, Style->RawWallMaterial);
		Set[M80Slot::Majolica] = Pick(Style->MajolicaMaterial, Style->TrimMaterial);
	}
	Shell->ConfigureMaterialSet(Set);
}

void AM80House::SplitIntoUnits(const TArray<FVector2D>& Local, const TArray<EM80EdgeKind>& Kinds, int32 Front, TArray<FM80Unit>& OutUnits) const
{
	OutUnits.Reset();
	const int32 N = Local.Num();
	const FVector2D Axis = (Local[(Front + 1) % N] - Local[Front]).GetSafeNormal();
	double TMin = TNumericLimits<double>::Max(), TMax = -TMin;
	for (const FVector2D& Q : Local)
	{
		TMin = FMath::Min(TMin, FVector2D::DotProduct(Q, Axis));
		TMax = FMath::Max(TMax, FVector2D::DotProduct(Q, Axis));
	}
	const double Total = TMax - TMin;
	const double MinW = House.UnitWidthMin, MaxW = FMath::Max<double>(House.UnitWidthMax, House.UnitWidthMin + 50);
	if (!House.bSplitIntoUnits || Total < MaxW * 1.25)
	{
		OutUnits.Add({Local, Kinds, Front});
		return;
	}

	// Random widths in [MinW, MaxW], rescaled so they fill the frontage exactly.
	FRandomStream Rng(House.Seed * 31 + 7);
	TArray<double> Widths;
	double Sum = 0;
	while (Sum < Total - MinW * 0.5)
	{
		Widths.Add(Rng.FRandRange(MinW, MaxW));
		Sum += Widths.Last();
	}
	const double Scale = Total / Sum;
	TArray<double> Cuts = {TMin};
	for (double W : Widths)
	{
		Cuts.Add(Cuts.Last() + W * Scale);
	}
	Cuts.Last() = TMax;

	const FVector2D FrontNormal = M80Poly::EdgeNormal(Local, Front);
	for (int32 u = 0; u + 1 < Cuts.Num(); ++u)
	{
		const double A = Cuts[u], B = Cuts[u + 1];
		TArray<FVector2D> Piece = M80Poly::ClipHalfPlane(M80Poly::ClipHalfPlane(Local, Axis, A, true), Axis, B, false);
		M80Poly::Clean(Piece);
		if (Piece.Num() < 3 || FMath::Abs(M80Poly::SignedArea(Piece)) < 6e4)
		{
			continue; // slivers under 6 m2
		}
		FM80Unit Unit;
		Unit.Footprint = Piece;
		double Best = -1;
		for (int32 e = 0; e < Piece.Num(); ++e)
		{
			const FVector2D P0 = Piece[e], P1 = Piece[(e + 1) % Piece.Num()];
			const double D0 = FVector2D::DotProduct(P0, Axis), D1 = FVector2D::DotProduct(P1, Axis);
			EM80EdgeKind Kind = EM80EdgeKind::Back;
			const bool bOnCut = (FMath::Abs(D0 - A) < 1 && FMath::Abs(D1 - A) < 1) || (FMath::Abs(D0 - B) < 1 && FMath::Abs(D1 - B) < 1);
			if (bOnCut)
			{
				Kind = EM80EdgeKind::Party;
			}
			else
			{
				const FVector2D Mid = (P0 + P1) * 0.5;
				for (int32 o = 0; o < N; ++o)
				{
					if (M80Poly::SegmentDistance(Mid, Local[o], Local[(o + 1) % N]) < 2.0)
					{
						Kind = Kinds[o];
						break;
					}
				}
			}
			Unit.Kinds.Add(Kind);
			const double Facing = FVector2D::DotProduct(M80Poly::EdgeNormal(Piece, e), FrontNormal);
			const double Score = Kind == EM80EdgeKind::Street ? FVector2D::Distance(P0, P1) * (1.0 + Facing) : -1;
			if (Score > Best)
			{
				Best = Score;
				Unit.Front = e;
			}
		}
		if (Best < 0)
		{
			// No street edge: use the longest non-shared one.
			for (int32 e = 0; e < Piece.Num(); ++e)
			{
				const double L = Unit.Kinds[e] == EM80EdgeKind::Party ? -1 : FVector2D::Distance(Piece[e], Piece[(e + 1) % Piece.Num()]);
				if (L > Best)
				{
					Best = L;
					Unit.Front = e;
				}
			}
			if (Unit.Kinds.IsValidIndex(Unit.Front))
			{
				Unit.Kinds[Unit.Front] = EM80EdgeKind::Street;
			}
		}
		OutUnits.Add(MoveTemp(Unit));
	}
	if (OutUnits.IsEmpty())
	{
		OutUnits.Add({Local, Kinds, Front});
	}
}

namespace
{
/** Kinds and uses of a piece cut from Src: edges lying on Src keep theirs, the others (cuts) get CutKind. */
void InheritEdges(const TArray<FVector2D>& Piece, const FM80BuildInput& Src, EM80EdgeKind CutKind, TArray<EM80EdgeKind>& OutKinds,
	TArray<EM80GroundUse>& OutUses, TArray<int32>& OutCuts)
{
	OutKinds.Reset();
	OutUses.Reset();
	OutCuts.Reset();
	const TArray<FVector2D>& P = Src.Footprint;
	for (int32 e = 0; e < Piece.Num(); ++e)
	{
		const FVector2D Mid = (Piece[e] + Piece[(e + 1) % Piece.Num()]) * 0.5;
		int32 On = -1;
		for (int32 o = 0; o < P.Num(); ++o)
		{
			if (M80Poly::SegmentDistance(Mid, P[o], P[(o + 1) % P.Num()]) < 2.0)
			{
				On = o;
				break;
			}
		}
		OutKinds.Add(On >= 0 && Src.Kinds.IsValidIndex(On) ? Src.Kinds[On] : CutKind);
		OutUses.Add(On >= 0 && Src.Uses.IsValidIndex(On) ? Src.Uses[On] : EM80GroundUse::Home);
		if (On < 0)
		{
			OutCuts.Add(e);
		}
	}
}

struct FM80CourtWall
{
	FVector2D A, B, Outward;
	bool bStreet = false;
};

/**
 * Splits a deep unit into a front block and a back block around a courtyard; the courtyard is
 * closed by walls along the original non-party edges crossing it.
 */
bool MakeCourtyard(const FM80BuildInput& In, double MinDepth, FRandomStream& Rng, FM80BuildInput& OutFront, FM80BuildInput& OutRear, TArray<FM80CourtWall>& OutWalls)
{
	const TArray<FVector2D>& P = In.Footprint;
	const int32 N = P.Num();
	const FVector2D Inward = -M80Poly::EdgeNormal(P, In.FrontEdge);
	const double D0 = FVector2D::DotProduct(P[In.FrontEdge], Inward);
	double DMax = -TNumericLimits<double>::Max();
	for (const FVector2D& Q : P)
	{
		DMax = FMath::Max(DMax, FVector2D::DotProduct(Q, Inward));
	}
	const double Depth = DMax - D0;
	if (Depth < MinDepth)
	{
		return false;
	}
	const double D1 = FMath::Clamp(Depth * Rng.FRandRange(0.38f, 0.48f), 550.0, 900.0);
	const double Gap = FMath::Clamp(Depth * 0.3, 400.0, 700.0);
	if (Depth - D1 - Gap < 450)
	{
		return false;
	}
	const double C0 = D0 + D1, C1 = D0 + D1 + Gap;
	TArray<FVector2D> FrontP = M80Poly::ClipHalfPlane(P, Inward, C0, false);
	TArray<FVector2D> RearP = M80Poly::ClipHalfPlane(P, Inward, C1, true);
	M80Poly::Clean(FrontP);
	M80Poly::Clean(RearP);
	if (FrontP.Num() < 3 || RearP.Num() < 3 || FMath::Abs(M80Poly::SignedArea(FrontP)) < 1.5e5 || FMath::Abs(M80Poly::SignedArea(RearP)) < 1.2e5)
	{
		return false;
	}
	TArray<int32> Cuts;
	OutFront = In;
	OutFront.Footprint = FrontP;
	InheritEdges(FrontP, In, EM80EdgeKind::Back, OutFront.Kinds, OutFront.Uses, Cuts);
	OutFront.FrontEdge = 0;
	double Best = -1;
	const FVector2D FA = P[In.FrontEdge], FB = P[(In.FrontEdge + 1) % N];
	for (int32 e = 0; e < FrontP.Num(); ++e)
	{
		const FVector2D Mid = (FrontP[e] + FrontP[(e + 1) % FrontP.Num()]) * 0.5;
		const double Len = FVector2D::Distance(FrontP[e], FrontP[(e + 1) % FrontP.Num()]);
		if (M80Poly::SegmentDistance(Mid, FA, FB) < 2.0 && Len > Best)
		{
			Best = Len;
			OutFront.FrontEdge = e;
		}
	}

	OutRear = In;
	OutRear.Footprint = RearP;
	InheritEdges(RearP, In, EM80EdgeKind::Street, OutRear.Kinds, OutRear.Uses, Cuts);
	OutRear.Uses.Reset();
	Best = -1;
	for (int32 e : Cuts)
	{
		const double Len = FVector2D::Distance(RearP[e], RearP[(e + 1) % RearP.Num()]);
		if (Len > Best)
		{
			Best = Len;
			OutRear.FrontEdge = e;
		}
	}
	if (Best < 0)
	{
		return false;
	}
	OutRear.Params.Floors = FMath::Max(1, In.Params.Floors - 1);
	OutRear.Params.Seed = In.Params.Seed + 11;

	// Courtyard walls: the parts of the original outer edges between the two blocks.
	for (int32 o = 0; o < N; ++o)
	{
		if (In.Kinds.IsValidIndex(o) && In.Kinds[o] == EM80EdgeKind::Party)
		{
			continue;
		}
		const FVector2D A = P[o], B = P[(o + 1) % N];
		const double Da = FVector2D::DotProduct(A, Inward), Db = FVector2D::DotProduct(B, Inward);
		if (FMath::Abs(Db - Da) < 1e-3)
		{
			continue;
		}
		const double T0 = FMath::Clamp((C0 - Da) / (Db - Da), 0.0, 1.0), T1 = FMath::Clamp((C1 - Da) / (Db - Da), 0.0, 1.0);
		const FVector2D WA = FMath::Lerp(A, B, FMath::Min(T0, T1)), WB = FMath::Lerp(A, B, FMath::Max(T0, T1));
		if (FVector2D::Distance(WA, WB) >= 60)
		{
			OutWalls.Add({WA, WB, M80Poly::EdgeNormal(P, o), !In.Kinds.IsValidIndex(o) || In.Kinds[o] == EM80EdgeKind::Street});
		}
	}
	return true;
}

/** Cuts the part of the unit that stays behind a terrace of the given depth along the front edge. */
bool MakeSetback(const FM80BuildInput& In, double Depth, FM80BuildInput& OutUpper)
{
	const TArray<FVector2D>& P = In.Footprint;
	const int32 N = P.Num();
	const FVector2D Inward = -M80Poly::EdgeNormal(P, In.FrontEdge);
	double DMin = TNumericLimits<double>::Max(), DMax = -DMin;
	for (const FVector2D& Q : P)
	{
		DMin = FMath::Min(DMin, FVector2D::DotProduct(Q, Inward));
		DMax = FMath::Max(DMax, FVector2D::DotProduct(Q, Inward));
	}
	const double Cut = FVector2D::DotProduct(P[In.FrontEdge], Inward) + Depth;
	if (DMax - Cut < 450)
	{
		return false; // too shallow for a room behind the terrace
	}
	TArray<FVector2D> Piece = M80Poly::ClipHalfPlane(P, Inward, Cut, true);
	M80Poly::Clean(Piece);
	if (Piece.Num() < 3 || FMath::Abs(M80Poly::SignedArea(Piece)) < 1.2e5)
	{
		return false;
	}
	OutUpper = In;
	OutUpper.Footprint = Piece;
	OutUpper.Uses.Reset();
	OutUpper.Kinds.Reset();
	double Best = -1;
	for (int32 e = 0; e < Piece.Num(); ++e)
	{
		const FVector2D A = Piece[e], B = Piece[(e + 1) % Piece.Num()];
		const bool bOnCut = FMath::Abs(FVector2D::DotProduct(A, Inward) - Cut) < 1 && FMath::Abs(FVector2D::DotProduct(B, Inward) - Cut) < 1;
		EM80EdgeKind Kind = bOnCut ? EM80EdgeKind::Street : EM80EdgeKind::Back;
		if (!bOnCut)
		{
			const FVector2D Mid = (A + B) * 0.5;
			for (int32 o = 0; o < N; ++o)
			{
				if (M80Poly::SegmentDistance(Mid, P[o], P[(o + 1) % N]) < 2.0)
				{
					Kind = In.Kinds.IsValidIndex(o) ? In.Kinds[o] : EM80EdgeKind::Back;
					break;
				}
			}
		}
		OutUpper.Kinds.Add(Kind);
		if (bOnCut && FVector2D::Distance(A, B) > Best)
		{
			Best = FVector2D::Distance(A, B);
			OutUpper.FrontEdge = e;
		}
	}
	return Best > 0;
}
}

void AM80House::RefreshProps()
{
	for (UInstancedStaticMeshComponent* C : PropComponents)
	{
		if (C)
		{
			C->DestroyComponent();
		}
	}
	PropComponents.Reset();
	TMap<UStaticMesh*, UInstancedStaticMeshComponent*> ByMesh;
	for (const FM80SavedProp& Prop : SavedProps)
	{
		if (!Prop.Mesh)
		{
			continue;
		}
		UInstancedStaticMeshComponent*& C = ByMesh.FindOrAdd(Prop.Mesh);
		if (!C)
		{
			C = NewObject<UInstancedStaticMeshComponent>(this, NAME_None, RF_Transient);
			C->SetupAttachment(Footprint);
			C->SetMobility(EComponentMobility::Static);
			C->SetStaticMesh(Prop.Mesh);
			if (Prop.bPlant)
			{
				// Plants: no collision, and they fade out with distance like foliage.
				C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
				C->SetCullDistances(0, 9000);
			}
			C->RegisterComponent();
			PropComponents.Add(C);
		}
		C->AddInstance(Prop.Transform, false);
	}
}

void AM80House::Rebuild()
{
	const double Start = FPlatformTime::Seconds();
	if (IsExcluded())
	{
		// Switched off: keep whatever was built (or baked) but hidden; nothing is generated.
		SetExcludedVisuals(true);
		BuildInfo = bDisabled ? TEXT("Disattivata") : TEXT("Esclusa da una zona senza case procedurali");
		return;
	}
	if (IsBaked())
	{
		// Any change makes the baked asset stale: go back to the live preview.
		Baked->SetStaticMesh(nullptr);
		Baked->SetVisibility(false);
	}
	Shell->SetVisibility(true);
	Shell->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	TArray<FVector2D> Local = LocalFootprint();
	M80Poly::Clean(Local);
	if (Local.Num() < 3 || FMath::Abs(M80Poly::SignedArea(Local)) < 1e4)
	{
		BuildInfo = TEXT("Perimetro non valido: servono almeno 3 punti e 1 m2");
		return;
	}
	UM80HouseStyle* MainStyle = House.Style;
	TArray<EM80EdgeKind> Kinds;
	int32 Front = 0;
	ResolveEdges(Local, Kinds, Front);
	ResolvedEdgeKinds = Kinds;
	ResolvedFrontEdge = Front;

	TArray<FVector2D> World2D;
	const FTransform T = GetActorTransform();
	for (const FVector2D& Q : Local)
	{
		const FVector W = T.TransformPosition(FVector(Q.X, Q.Y, 0));
		World2D.Add(FVector2D(W.X, W.Y));
	}
	const FGroundGrid Grid = SampleGround(World2D);
	const double ActorZ = GetActorLocation().Z;
	auto Ground = [&Grid, &T, ActorZ](const FVector2D& Q)
	{
		const FVector W = T.TransformPosition(FVector(Q.X, Q.Y, 0));
		return Grid.Sample(FVector2D(W.X, W.Y)) - ActorZ;
	};

	TArray<FM80Unit> Units;
	SplitIntoUnits(Local, Kinds, Front, Units);

	FM80MeshBuffer Mesh;
	TArray<FM80PropPlacement> Props;
	int32 Openings = 0, Balconies = 0, Courtyards = 0, Stairs = 0, SplitTops = 0, Abandoned = 0;
	double Floor0Min = TNumericLimits<double>::Max(), Floor0Max = -Floor0Min;
	LastEaveZ = -TNumericLimits<double>::Max();
	const bool bMany = Units.Num() > 1;
	for (int32 u = 0; u < Units.Num(); ++u)
	{
		FRandomStream Rng(House.Seed * 13 + u * 7919);
		FM80BuildInput In;
		In.Footprint = Units[u].Footprint;
		In.Kinds = Units[u].Kinds;
		In.FrontEdge = Units[u].Front;
		In.Ground = Ground;
		In.Params = House;
		In.Params.Seed = House.Seed * 101 + u * 37;

		UM80HouseStyle* Style = MainStyle;
		if (bMany && House.AlternativeStyles.Num() && Rng.FRand() < 0.35f)
		{
			if (UM80HouseStyle* Alt = House.AlternativeStyles[Rng.RandRange(0, House.AlternativeStyles.Num() - 1)])
			{
				Style = Alt;
			}
		}
		In.Rules = Style ? Style->Rules : FM80FacadeRules();
		if (MainStyle)
		{
			In.NumProps = MainStyle->PropMeshes.Num();
			In.NumClimbers = MainStyle->ClimberMeshes.Num();
			In.NumGroundPlants = MainStyle->GroundPlantMeshes.Num();
			In.NumWallPlants = MainStyle->WallPlantMeshes.Num();
			In.ClimberYaw = MainStyle->ClimberYaw;
			In.WallPropYaw = MainStyle->WallPropYaw;
			int32 First = MainStyle->PropMeshes.Num() + MainStyle->ClimberMeshes.Num() + MainStyle->GroundPlantMeshes.Num() + MainStyle->WallPlantMeshes.Num();
			const TArray<const TArray<TObjectPtr<UStaticMesh>>*> Lists = MainStyle->SicilyLists();
			for (int32 c = 0; c < M80Cat::Count; ++c)
			{
				In.CatFirst[c] = First;
				In.CatCount[c] = Lists[c]->Num();
				First += Lists[c]->Num();
			}
		}

		EM80WallFinish Finish = (House.bUseStyleFinish && Style) ? Style->DefaultFinish : House.Finish;
		if (bMany && House.bVaryFinish && Rng.FRand() < 0.5f)
		{
			const float Roll = Rng.FRand();
			Finish = Roll < 0.35f ? EM80WallFinish::Plaster : Roll < 0.6f ? EM80WallFinish::PlasterWorn : Roll < 0.8f ? EM80WallFinish::Rubble : EM80WallFinish::Ashlar;
		}
		In.WallSlot = M80Slot::ForFinish(Finish);
		if (bMany)
		{
			In.Params.Floors = FMath::Max(1, House.Floors + Rng.RandRange(-House.FloorVariation, House.FloorVariation));
			In.Params.GroundFloorHeight = House.GroundFloorHeight + Rng.FRandRange(-25.f, 20.f);
			In.Params.FloorHeight = House.FloorHeight + Rng.FRandRange(-15.f, 15.f);
			if (House.bVaryRoofs)
			{
				const float Roll = Rng.FRand();
				In.Params.RoofType = Roll < 0.55f ? House.RoofType : Roll < 0.8f ? EM80RoofType::Terrace : EM80RoofType::Shed;
			}
		}
		In.UnitData = FVector2f(Rng.FRand(), FMath::Clamp(House.Decay + Rng.FRandRange(-0.25f, 0.25f), 0.f, 1.f));
		// Some houses of the row are abandoned: worn plaster, full decay, weeds everywhere.
		FRandomStream AbandonRng(House.Seed * 389 + u * 17);
		if (AbandonRng.FRand() < House.AbandonChance)
		{
			In.bAbandoned = true;
			++Abandoned;
			if (In.WallSlot == M80Slot::WallPlaster)
			{
				In.WallSlot = M80Slot::WallPlasterWorn;
			}
			In.UnitData.Y = 1.f;
			In.Params.Vegetation = FMath::Min(1.f, House.Vegetation * 2.5f + 0.2f);
		}
		// Ground floor use is set per lot edge: give each unit edge the use of the lot edge it lies on.
		for (int32 e = 0; e < In.Footprint.Num() && House.EdgeGroundUse.Num(); ++e)
		{
			const FVector2D Mid = (In.Footprint[e] + In.Footprint[(e + 1) % In.Footprint.Num()]) * 0.5;
			EM80GroundUse Use = EM80GroundUse::Home;
			for (int32 o = 0; o < Local.Num(); ++o)
			{
				if (House.EdgeGroundUse.IsValidIndex(o) && M80Poly::SegmentDistance(Mid, Local[o], Local[(o + 1) % Local.Num()]) < 2.0)
				{
					Use = House.EdgeGroundUse[o];
					break;
				}
			}
			In.Uses.Add(Use);
		}

		auto Emit = [&](const FM80BuildInput& Input)
		{
			FM80BuildOutput Out;
			M80BuildHouse(Input, Out);
			Mesh.Append(Out.Mesh);
			Props.Append(Out.Props);
			Openings += Out.Openings;
			Balconies += Out.Balconies;
			Stairs += Out.bStair;
			Floor0Min = FMath::Min(Floor0Min, Out.Floor0);
			Floor0Max = FMath::Max(Floor0Max, Out.Floor0);
			LastEaveZ = FMath::Max(LastEaveZ, Out.EaveZ);
			return Out;
		};

		// Deep houses: front and back block around an inner courtyard closed by walls with a gateway.
		FRandomStream CourtRng(House.Seed * 613 + u * 29);
		FM80BuildInput FrontBlock, RearBlock;
		TArray<FM80CourtWall> Walls;
		if (CourtRng.FRand() < House.CourtyardChance && MakeCourtyard(In, House.CourtyardMinDepth, CourtRng, FrontBlock, RearBlock, Walls))
		{
			In = FrontBlock;
			Emit(RearBlock);
			++Courtyards;
			int32 Gate = -1;
			double GateLen = 0;
			for (int32 w = 0; w < Walls.Num(); ++w)
			{
				const double Len = FVector2D::Distance(Walls[w].A, Walls[w].B);
				if (Walls[w].bStreet && Len > GateLen)
				{
					GateLen = Len;
					Gate = w;
				}
			}
			for (int32 w = 0; w < Walls.Num(); ++w)
			{
				FM80MeshBuffer WallMesh;
				M80BuildCourtWall(Walls[w].A, Walls[w].B, Walls[w].Outward, Ground, In.WallSlot, w == Gate, In.Params.Seed + w, In.UnitData, WallMesh);
				Mesh.Append(WallMesh);
			}
		}

		// Top floor set back behind a terrace, or left unfinished in bare bricks: a lower block with a
		// flat roof plus a one-floor block on top.
		FM80BuildInput Upper;
		FRandomStream SetbackRng(House.Seed * 977 + u * 13);
		bool bSplitTop = false;
		if (In.Params.Floors >= 2 && SetbackRng.FRand() < House.SetbackChance && MakeSetback(In, House.SetbackDepth, Upper))
		{
			bSplitTop = true;
			Upper.bUnfinished = SetbackRng.FRand() < 0.3f;
		}
		else if (In.Params.Floors >= 2 && SetbackRng.FRand() < House.UnfinishedChance)
		{
			bSplitTop = true;
			Upper = In;
			Upper.Uses.Reset();
			Upper.bUnfinished = true;
		}
		if (bSplitTop)
		{
			// The upper walls stand just inside the terrace parapet (25 cm) so the two never overlap.
			TArray<double> Inset;
			for (int32 e = 0; e < Upper.Footprint.Num(); ++e)
			{
				Inset.Add(Upper.Kinds.IsValidIndex(e) && Upper.Kinds[e] == EM80EdgeKind::Party ? 0.0 : -31.0);
			}
			Upper.Footprint = M80Poly::OffsetEdges(Upper.Footprint, Inset);
		}
		if (bSplitTop && FMath::Abs(M80Poly::SignedArea(Upper.Footprint)) > 6e4)
		{
			++SplitTops;
			In.Params.Floors -= 1;
			In.Params.RoofType = EM80RoofType::Terrace;
			In.KeepOut = Upper.Footprint;
			const FM80BuildOutput Lower = Emit(In);
			const double TerraceZ = Lower.EaveZ;
			Upper.Ground = [TerraceZ](const FVector2D&) { return TerraceZ - 12.0; };
			Upper.Params.Floors = 1;
			Upper.Params.GroundFloorHeight = House.FloorHeight;
			Upper.Params.Seed = In.Params.Seed + 5;
			Upper.Params.Vegetation *= 0.4f;
			Upper.Params.RoofType = SetbackRng.FRand() < 0.6f ? EM80RoofType::Shed : EM80RoofType::Terrace;
			if (Upper.bUnfinished)
			{
				Upper.WallSlot = M80Slot::Brick;
				Upper.Params.RoofType = EM80RoofType::Terrace;
			}
			Emit(Upper);
		}
		else
		{
			Emit(In);
		}
	}
	UnitCount = Units.Num();
	LastInputHash = ComputeInputHash();

	UE::Geometry::FDynamicMesh3 Dyn;
	Mesh.ToDynamicMesh(Dyn);
	const int32 Triangles = Dyn.TriangleCount();
	Shell->SetMesh(MoveTemp(Dyn));
	ApplyMaterials(MainStyle);
	Shell->SetComplexAsSimpleCollisionEnabled(true, true);

	// Lot-wide values for the master material (custom primitive data 0-7).
	FRandomStream Rng(House.Seed * 7919 + 13);
	FLinearColor WallTint = FLinearColor::White, WoodTint(0.32f, 0.42f, 0.30f);
	if (MainStyle && MainStyle->WallTints.Num())
	{
		WallTint = MainStyle->WallTints[Rng.RandRange(0, MainStyle->WallTints.Num() - 1)];
	}
	if (MainStyle && MainStyle->WoodTints.Num())
	{
		WoodTint = MainStyle->WoodTints[Rng.RandRange(0, MainStyle->WoodTints.Num() - 1)];
	}
	const float Values[8] = {WallTint.R, WallTint.G, WallTint.B, House.Decay, WoodTint.R, WoodTint.G, WoodTint.B, Rng.FRand()};
	for (int32 i = 0; i < 8; ++i)
	{
		Shell->SetDefaultCustomPrimitiveDataFloat(i, Values[i]);
	}

	// Props and plants are real meshes: same order as the builder's indices.
	TArray<UStaticMesh*> PropMeshes;
	int32 FirstPlant = 0;
	if (MainStyle)
	{
		PropMeshes.Append(MainStyle->PropMeshes);
		FirstPlant = PropMeshes.Num();
		PropMeshes.Append(MainStyle->ClimberMeshes);
		PropMeshes.Append(MainStyle->GroundPlantMeshes);
		PropMeshes.Append(MainStyle->WallPlantMeshes);
		for (const TArray<TObjectPtr<UStaticMesh>>* List : MainStyle->SicilyLists())
		{
			PropMeshes.Append(*List);
		}
	}
	SavedProps.Reset();
	for (const FM80PropPlacement& Prop : Props)
	{
		UStaticMesh* PropMesh = PropMeshes.IsValidIndex(Prop.Prop) ? PropMeshes[Prop.Prop] : nullptr;
		if (!PropMesh)
		{
			continue;
		}
		FTransform PropT = Prop.Transform;
		int32 Copies = 1;
		double Step = 0;
		if (Prop.TargetHeight > 0)
		{
			const FBox Box = PropMesh->GetBoundingBox();
			const double MeshHeight = FMath::Max(1.0, Box.Max.Z - Box.Min.Z);
			double Scale = Prop.TargetHeight / MeshHeight;
			if (Prop.bStack && Scale > 1.6)
			{
				// Keep leaves at a believable size: overlapping copies up the wall.
				Copies = FMath::CeilToInt(Prop.TargetHeight / (MeshHeight * 1.3 * 0.8));
				Scale = 1.3;
				Step = MeshHeight * Scale * 0.8;
			}
			PropT.SetScale3D(FVector(Scale));
		}
		for (int32 c = 0; c < Copies; ++c)
		{
			FM80SavedProp& Saved = SavedProps.AddDefaulted_GetRef();
			Saved.Mesh = PropMesh;
			Saved.Transform = PropT;
			Saved.Transform.AddToTranslation(FVector(0, 0, Step * c));
			if (c > 0)
			{
				// Mirror every other copy so the stack does not read as a repeated tile.
				Saved.Transform.SetScale3D(PropT.GetScale3D() * FVector(c % 2 ? -1 : 1, 1, 1));
			}
			Saved.bPlant = Prop.Prop >= FirstPlant;
		}
	}
	RefreshProps();

	int32 Party = 0;
	for (EM80EdgeKind K : Kinds)
	{
		Party += K == EM80EdgeKind::Party;
	}
	BuildInfo = FString::Printf(TEXT("%d case, %d triangoli, %d aperture, %d balconi, %d muri in comune col vicinato, piano terra da %.0f a %.0f cm, %.1f ms"),
		Units.Num(), Triangles, Openings, Balconies, Party, Floor0Min, Floor0Max, (FPlatformTime::Seconds() - Start) * 1000.0);
	BuildInfo += FString::Printf(TEXT(", %d cortili, %d scale esterne, %d piani arretrati o non finiti, %d abbandonate"), Courtyards, Stairs, SplitTops, Abandoned);
	SetExcludedVisuals(false);
}

void AM80House::RebuildWithNeighbours()
{
	Rebuild();
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	const FBox Mine = Footprint->Bounds.GetBox().ExpandBy(200);
	for (TActorIterator<AM80House> It(World); It; ++It)
	{
		if (*It != this && It->Footprint && Mine.Intersect(It->Footprint->Bounds.GetBox()))
		{
			It->Rebuild();
		}
	}
}
