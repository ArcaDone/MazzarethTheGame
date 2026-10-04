#include "M80ExclusionZone.h"
#include "M80House.h"
#include "M80Polygon.h"
#include "Components/SplineComponent.h"
#include "EngineUtils.h"
#include "Engine/World.h"

AM80ExclusionZone::AM80ExclusionZone()
{
	PrimaryActorTick.bCanEverTick = false;
	Outline = CreateDefaultSubobject<USplineComponent>(TEXT("Outline"));
	SetRootComponent(Outline);
	Outline->SetClosedLoop(true, false);
	Outline->ClearSplinePoints(false);
	const TArray<FVector> Square = {{-1000, -1000, 0}, {1000, -1000, 0}, {1000, 1000, 0}, {-1000, 1000, 0}};
	Outline->SetSplinePoints(Square, ESplineCoordinateSpace::Local, false);
	for (int32 i = 0; i < Square.Num(); ++i)
	{
		Outline->SetSplinePointType(i, ESplinePointType::Linear, false);
	}
	Outline->UpdateSpline();
	Outline->bDrawDebug = true;
	Outline->SetUnselectedSplineSegmentColor(FLinearColor(1.f, 0.2f, 0.1f));
	Outline->SetMobility(EComponentMobility::Static);
	bIsEditorOnlyActor = false;
}

TArray<FVector2D> AM80ExclusionZone::GetOutlineWorld2D() const
{
	TArray<FVector2D> Points;
	for (int32 i = 0; i < Outline->GetNumberOfSplinePoints(); ++i)
	{
		const FVector W = Outline->GetLocationAtSplinePoint(i, ESplineCoordinateSpace::World);
		Points.Add(FVector2D(W.X, W.Y));
	}
	return Points;
}

bool AM80ExclusionZone::IsPointExcluded(const UObject* WorldContext, FVector Location)
{
	UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	if (!World)
	{
		return false;
	}
	for (TActorIterator<AM80ExclusionZone> It(World); It; ++It)
	{
		if (It->bEnabled && !It->bDying)
		{
			const TArray<FVector2D> P = It->GetOutlineWorld2D();
			if (P.Num() >= 3 && M80Poly::Contains(P, FVector2D(Location.X, Location.Y)))
			{
				return true;
			}
		}
	}
	return false;
}

void AM80ExclusionZone::RefreshHouses()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	for (TActorIterator<AM80House> It(World); It; ++It)
	{
		It->ApplyExclusion();
	}
}

void AM80ExclusionZone::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	RefreshHouses();
}

void AM80ExclusionZone::Destroyed()
{
	bDying = true;
	RefreshHouses();
	Super::Destroyed();
}
