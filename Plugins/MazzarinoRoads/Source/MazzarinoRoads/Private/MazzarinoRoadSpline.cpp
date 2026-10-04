#include "MazzarinoRoadSpline.h"
#include "Components/SplineComponent.h"
#include "Components/SplineMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"

AMazzarinoRoadSpline::AMazzarinoRoadSpline()
{
    PrimaryActorTick.bCanEverTick = false;
    Spline = CreateDefaultSubobject<USplineComponent>(TEXT("Spline"));
    SetRootComponent(Spline);
    Spline->SetMobility(EComponentMobility::Static);
    Spline->bInputSplinePointsToConstructionScript = true;
}

void AMazzarinoRoadSpline::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    RebuildRoad();
}

void AMazzarinoRoadSpline::RebuildRoad()
{
    // Collect by tag as construction-script reconstruction can replace pointers.
    TInlineComponentArray<USplineMeshComponent*> Existing(this);
    for (USplineMeshComponent* Component : Existing)
    {
        if (Component && Component->ComponentHasTag(TEXT("M80RoadGenerated")))
            Component->DestroyComponent();
    }
    RoadSegments.Empty();
    if (!RoadMesh || !Spline || Spline->GetNumberOfSplinePoints() < 2) return;

    const FBox Box = RoadMesh->GetBoundingBox();
    const double MeshWidth = Box.Max.Y - Box.Min.Y;
    if (MeshWidth <= UE_SMALL_NUMBER) return;
    const double WidthScale = FMath::Clamp(WidthMeters, 0.2f, 40.0f) * 100.0 / MeshWidth;
    const double VerticalScale = FMath::Clamp(MeshVerticalScale, 0.01f, 10.0f);
    const double Length = Spline->GetSplineLength();
    const double MaxStep = FMath::Clamp(SegmentLengthMeters, 1.0f, 50.0f) * 100.0;

    // Split at every control point and limit segment length within each span.
    TArray<double> Distances;
    Distances.Add(0.0);
    const int32 PointCount = Spline->GetNumberOfSplinePoints();
    const int32 SpanCount = Spline->IsClosedLoop() ? PointCount : PointCount - 1;
    for (int32 Span = 0; Span < SpanCount; ++Span)
    {
        const double A = Spline->GetDistanceAlongSplineAtSplinePoint(Span);
        const double B = Span + 1 < PointCount ? Spline->GetDistanceAlongSplineAtSplinePoint(Span + 1) : Length;
        const int32 Pieces = FMath::Max(1, FMath::CeilToInt((B - A) / MaxStep));
        for (int32 Index = 1; Index <= Pieces; ++Index)
            Distances.Add(FMath::Lerp(A, B, double(Index) / Pieces));
    }

    for (int32 Index = 0; Index + 1 < Distances.Num(); ++Index)
    {
        const double A = Distances[Index], B = Distances[Index + 1], Span = B - A;
        if (Span < 0.1) continue;
        USplineMeshComponent* Segment = NewObject<USplineMeshComponent>(this, NAME_None, RF_Transactional);
        Segment->CreationMethod = EComponentCreationMethod::UserConstructionScript;
        Segment->ComponentTags.Add(TEXT("M80RoadGenerated"));
        Segment->SetupAttachment(Spline);
        Segment->SetMobility(EComponentMobility::Static);
        Segment->SetStaticMesh(RoadMesh);
        if (RoadMaterial) Segment->SetMaterial(0, RoadMaterial);
        Segment->SetForwardAxis(ESplineMeshAxis::X, false);
        Segment->SetBoundaryMin(Box.Min.X, false);
        Segment->SetBoundaryMax(Box.Max.X, false);
        const FVector Start = Spline->GetLocationAtDistanceAlongSpline(A, ESplineCoordinateSpace::Local);
        const FVector End = Spline->GetLocationAtDistanceAlongSpline(B, ESplineCoordinateSpace::Local);
        // CurveClamped can have a zero derivative at a control point. A spline
        // mesh needs a nonzero direction there to construct its cross section;
        // otherwise its end vertices collapse onto the centre line.
        const auto StableDirection = [&](double Distance)
        {
            FVector Direction = Spline->GetDirectionAtDistanceAlongSpline(Distance, ESplineCoordinateSpace::Local);
            if (Direction.IsNearlyZero())
            {
                const auto Sample = [&](double D)
                {
                    D = Spline->IsClosedLoop()
                        ? FMath::Fmod(D + Length, Length)
                        : FMath::Clamp(D, 0.0, Length);
                    return Spline->GetLocationAtDistanceAlongSpline(D, ESplineCoordinateSpace::Local);
                };
                Direction = (Sample(Distance + 10.0) - Sample(Distance - 10.0)).GetSafeNormal();
            }
            return Direction.IsNearlyZero() ? (End - Start).GetSafeNormal() : Direction;
        };
        const FVector TA = StableDirection(A) * Span;
        const FVector TB = StableDirection(B) * Span;
        const FVector ScaleA = Spline->GetScaleAtDistanceAlongSpline(A);
        const FVector ScaleB = Spline->GetScaleAtDistanceAlongSpline(B);
        const double WA = WidthScale * FMath::Max(0.05, ScaleA.Y);
        const double WB = WidthScale * FMath::Max(0.05, ScaleB.Y);
        Segment->SetStartAndEnd(Start, TA, End, TB, false);
        Segment->SetStartScale(FVector2D(WA, VerticalScale), false);
        Segment->SetEndScale(FVector2D(WB, VerticalScale), false);
        Segment->SetStartOffset(FVector2D(-Box.GetCenter().Y * WA, -Box.Max.Z * VerticalScale), false);
        Segment->SetEndOffset(FVector2D(-Box.GetCenter().Y * WB, -Box.Max.Z * VerticalScale), false);
        Segment->SetCollisionProfileName(bRoadCollision ? TEXT("BlockAll") : TEXT("NoCollision"));
        Segment->bCastDynamicShadow = false;
        Segment->RegisterComponent();
        Segment->UpdateMesh();
        RoadSegments.Add(Segment);
        // Optional continuous underlay, using the same paving material.
        if (RoadBackingMesh)
        {
            const FBox BackBox = RoadBackingMesh->GetBoundingBox();
            const double BackWidth = BackBox.Max.Y - BackBox.Min.Y;
            if (BackWidth > UE_SMALL_NUMBER)
            {
                USplineMeshComponent* Back = NewObject<USplineMeshComponent>(this, NAME_None, RF_Transactional);
                Back->CreationMethod = EComponentCreationMethod::UserConstructionScript;
                Back->ComponentTags.Add(TEXT("M80RoadGenerated"));
                Back->SetupAttachment(Spline);
                Back->SetMobility(EComponentMobility::Static);
                Back->SetStaticMesh(RoadBackingMesh);
                if (RoadMaterial) Back->SetMaterial(0, RoadMaterial);
                Back->SetForwardAxis(ESplineMeshAxis::X, false);
                Back->SetBoundaryMin(BackBox.Min.X, false);
                Back->SetBoundaryMax(BackBox.Max.X, false);
                Back->SetStartAndEnd(Start, TA, End, TB, false);
                const double BA = FMath::Clamp(WidthMeters, 0.2f, 40.0f) * 100.0 / BackWidth * FMath::Max(0.05, ScaleA.Y);
                const double BB = FMath::Clamp(WidthMeters, 0.2f, 40.0f) * 100.0 / BackWidth * FMath::Max(0.05, ScaleB.Y);
                Back->SetStartScale(FVector2D(BA, 1), false);
                Back->SetEndScale(FVector2D(BB, 1), false);
                const double BackZ = -BackBox.Max.Z - (Box.Max.Z - Box.Min.Z) * VerticalScale - 1.0;
                Back->SetStartOffset(FVector2D(-BackBox.GetCenter().Y * BA, BackZ), false);
                Back->SetEndOffset(FVector2D(-BackBox.GetCenter().Y * BB, BackZ), false);
                Back->SetCollisionProfileName(bRoadCollision ? TEXT("BlockAll") : TEXT("NoCollision"));
                Back->bCastDynamicShadow = false;
                Back->RegisterComponent();
                Back->UpdateMesh();
                RoadSegments.Add(Back);
            }
        }
    }
}
