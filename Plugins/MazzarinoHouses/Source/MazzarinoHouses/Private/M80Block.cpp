#include "M80Block.h"
#include "M80House.h"
#include "M80Polygon.h"
#include "Components/SplineComponent.h"
#include "EngineUtils.h"
#include "Engine/World.h"

namespace
{
bool SegmentsCross(const FVector2D& A, const FVector2D& B, const FVector2D& C, const FVector2D& D)
{
	auto Side = [](const FVector2D& P, const FVector2D& Q, const FVector2D& R) { return (Q.X - P.X) * (R.Y - P.Y) - (Q.Y - P.Y) * (R.X - P.X); };
	return Side(A, B, C) * Side(A, B, D) < 0 && Side(C, D, A) * Side(C, D, B) < 0;
}

/** The inset ring is usable: same winding, not collapsed, no crossing edges, inside the outline. */
bool ValidInset(const TArray<FVector2D>& Outer, const TArray<FVector2D>& Inner)
{
	if (M80Poly::SignedArea(Inner) < 0.05 * M80Poly::SignedArea(Outer))
	{
		return false;
	}
	const int32 N = Inner.Num();
	for (int32 i = 0; i < N; ++i)
	{
		if (!M80Poly::Contains(Outer, Inner[i]))
		{
			return false;
		}
		for (int32 j = i + 2; j < N; ++j)
		{
			if ((j + 1) % N != i && SegmentsCross(Inner[i], Inner[(i + 1) % N], Inner[j], Inner[(j + 1) % N]))
			{
				return false;
			}
		}
	}
	return true;
}
}

AM80Block::AM80Block()
{
	PrimaryActorTick.bCanEverTick = false;
	Outline = CreateDefaultSubobject<USplineComponent>(TEXT("Outline"));
	SetRootComponent(Outline);
	Outline->SetClosedLoop(true, false);
	Outline->ClearSplinePoints(false);
	const TArray<FVector> Square = {{-2500, -2000, 0}, {2500, -2000, 0}, {2500, 2000, 0}, {-2500, 2000, 0}};
	Outline->SetSplinePoints(Square, ESplineCoordinateSpace::Local, false);
	for (int32 i = 0; i < Square.Num(); ++i)
	{
		Outline->SetSplinePointType(i, ESplinePointType::Linear, false);
	}
	Outline->UpdateSpline();
	Outline->bDrawDebug = true;
	Outline->SetUnselectedSplineSegmentColor(FLinearColor(0.15f, 0.85f, 0.2f));
	Outline->SetMobility(EComponentMobility::Static);
}

FString AM80Block::LotPrefix() const
{
	return TEXT("isolato_") + GetName() + TEXT("_");
}

TArray<FVector2D> AM80Block::GetOutlineWorld2D() const
{
	TArray<FVector2D> Points;
	for (int32 i = 0; i < Outline->GetNumberOfSplinePoints(); ++i)
	{
		const FVector W = Outline->GetLocationAtSplinePoint(i, ESplineCoordinateSpace::World);
		Points.Add(FVector2D(W.X, W.Y));
	}
	if (Points.Num() >= 3)
	{
		M80Poly::Clean(Points, 20.0);
	}
	return Points;
}

TArray<TArray<FVector2D>> AM80Block::MakeLots(double& OutDepth) const
{
	TArray<TArray<FVector2D>> Lots;
	const TArray<FVector2D> P = GetOutlineWorld2D();
	const int32 N = P.Num();
	OutDepth = 0.0;
	if (N < 3)
	{
		return Lots;
	}
	// Inner ring: the outline moved inwards by the depth, smaller if the block is too narrow.
	TArray<FVector2D> Q;
	double D = Depth;
	for (int32 Attempt = 0; Attempt < 8 && D >= 400.0; ++Attempt, D *= 0.8)
	{
		TArray<double> Distances;
		Distances.Init(-D, N);
		Q = M80Poly::OffsetEdges(P, Distances);
		if (ValidInset(P, Q))
		{
			OutDepth = D;
			break;
		}
	}
	if (OutDepth == 0.0)
	{
		Lots.Add(P);   // too small for a courtyard: one house fills the block
		return Lots;
	}
	// One lot per side, from the longest side on, so short sides join the previous one.
	int32 Start = 0;
	for (int32 i = 1; i < N; ++i)
	{
		if (FVector2D::Distance(P[i], P[(i + 1) % N]) > FVector2D::Distance(P[Start], P[(Start + 1) % N]))
		{
			Start = i;
		}
	}
	TArray<TArray<FVector2D>> Outer, Inner;
	for (int32 k = 0; k < N; ++k)
	{
		const int32 i = (Start + k) % N, j = (i + 1) % N;
		if (k > 0 && FVector2D::Distance(P[i], P[j]) < MinSide)
		{
			Outer.Last().Add(P[j]);
			Inner.Last().Add(Q[j]);
			continue;
		}
		Outer.Add({P[i], P[j]});
		Inner.Add({Q[i], Q[j]});
	}
	for (int32 l = 0; l < Outer.Num(); ++l)
	{
		TArray<FVector2D> Lot = Outer[l];
		for (int32 m = Inner[l].Num() - 1; m >= 0; --m)
		{
			if (FVector2D::Distance(Lot.Last(), Inner[l][m]) > 1.0)
			{
				Lot.Add(Inner[l][m]);
			}
		}
		if (Lot.Num() >= 3 && M80Poly::SignedArea(Lot) > 4.0 * 10000.0)
		{
			Lots.Add(Lot);
		}
	}
	return Lots;
}

void AM80Block::RemoveHouses()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	const FString Prefix = LotPrefix();
	TArray<AM80House*> Mine;
	for (TActorIterator<AM80House> It(World); It; ++It)
	{
		if (It->LotId.StartsWith(Prefix))
		{
			Mine.Add(*It);
		}
	}
	for (AM80House* House : Mine)
	{
		House->Destroy();
	}
	Info = FString::Printf(TEXT("Eliminate %d case"), Mine.Num());
}

void AM80Block::Generate()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	RemoveHouses();
	double UsedDepth = 0.0;
	const TArray<TArray<FVector2D>> Lots = MakeLots(UsedDepth);
	const TArray<FVector2D> Block = GetOutlineWorld2D();
	if (Lots.Num() == 0)
	{
		Info = TEXT("Disegna almeno 3 punti");
		return;
	}
	FVector2D Centre = FVector2D::ZeroVector;
	for (const FVector2D& Q : Block)
	{
		Centre += Q / Block.Num();
	}

	// The other houses: the nearest one gives the style, those touching the block are rebuilt after.
	const FString Prefix = LotPrefix();
	TArray<AM80House*> Others;
	AM80House* Nearest = nullptr;
	double NearestD = TNumericLimits<double>::Max();
	for (TActorIterator<AM80House> It(World); It; ++It)
	{
		if (It->LotId.StartsWith(Prefix) || It->IsExcluded())
		{
			continue;
		}
		Others.Add(*It);
		const double Dist = FVector2D::Distance(Centre, FVector2D(It->GetActorLocation()));
		if (Dist < NearestD)
		{
			NearestD = Dist;
			Nearest = *It;
		}
	}
	FBox BlockBox(ForceInit);
	for (const FVector2D& Q : Block)
	{
		BlockBox += FVector(Q, 0.0);
	}
	BlockBox = BlockBox.ExpandBy(FVector(300.0, 300.0, 1e6));
	TArray<AM80House*> Touching;
	TArray<TArray<FVector2D>> OtherFootprints;
	for (AM80House* House : Others)
	{
		if (BlockBox.IsInside(FVector(FVector2D(House->GetActorLocation()), 0.0)) || BlockBox.Intersect(House->Footprint->Bounds.GetBox()))
		{
			Touching.Add(House);
			OtherFootprints.Add(House->GetFootprintWorld2D());
		}
	}

	FRandomStream Rng(Seed);
	const double Z = GetActorLocation().Z;
	TArray<AM80House*> Made;
	int32 Skipped = 0;
	for (int32 l = 0; l < Lots.Num(); ++l)
	{
		const TArray<FVector2D>& Lot = Lots[l];
		FVector2D C = FVector2D::ZeroVector;
		for (const FVector2D& Q : Lot)
		{
			C += Q / Lot.Num();
		}
		if (bSkipExisting && OtherFootprints.ContainsByPredicate([&C](const TArray<FVector2D>& F) { return F.Num() >= 3 && M80Poly::Contains(F, C); }))
		{
			++Skipped;
			continue;
		}
		AM80House* House = World->SpawnActorDeferred<AM80House>(AM80House::StaticClass(), FTransform(FVector(C, Z)));
		if (!House)
		{
			continue;
		}
		if (Nearest)
		{
			House->House = Nearest->House;
		}
		if (Style)
		{
			House->House.Style = Style;
		}
		House->House.Floors = Rng.RandRange(FMath::Min(FloorsMin, FloorsMax), FMath::Max(FloorsMin, FloorsMax));
		House->House.Seed = Rng.RandRange(1, 99999);
		House->House.Decay = Rng.FRandRange(0.15f, 0.65f);
		House->House.FrontEdge = 0;
		House->House.EdgeKinds.Reset();
		House->House.EdgeGroundUse.Reset();
		House->LotId = FString::Printf(TEXT("%s%d"), *Prefix, l + 1);
		House->bLiveRebuild = false;   // built once below, when every house of the block exists
		TArray<FVector> Points;
		for (const FVector2D& Q : Lot)
		{
			Points.Add(FVector(Q, Z));
		}
		House->SetFootprintWorld(Points);
		House->FinishSpawning(House->GetActorTransform());
#if WITH_EDITOR
		House->SetActorLabel(FString::Printf(TEXT("Isolato_%s_%d"), *GetActorLabel(), l + 1));
		House->SetFolderPath(TEXT("Case/Isolati"));
#endif
		Made.Add(House);
	}
	for (AM80House* House : Made)
	{
		House->bLiveRebuild = true;
		House->Rebuild();
	}
	// Walls now shared with the new houses lose their windows (these neighbours leave their baked mesh).
	for (AM80House* House : Touching)
	{
		House->Rebuild();
	}
	Info = FString::Printf(TEXT("%d case su %d lati, profondita %.1f m%s%s, %d vicine ricostruite (da ricuocere)"),
		Made.Num(), Lots.Num(), UsedDepth / 100.0, UsedDepth < Depth - 1.0 ? TEXT(" (ridotta: isolato stretto)") : TEXT(""),
		Skipped ? *FString::Printf(TEXT(", %d lati saltati perche gia costruiti"), Skipped) : TEXT(""), Touching.Num());
}
