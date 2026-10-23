#include "M80ModularFence.h"

#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SplineComponent.h"
#include "Engine/StaticMesh.h"
#include "M80Sidewalk.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

AM80ModularFence::AM80ModularFence()
{
	PrimaryActorTick.bCanEverTick = false;
	Path = CreateDefaultSubobject<USplineComponent>(TEXT("Path"));
	SetRootComponent(Path);
	Path->SetMobility(EComponentMobility::Static);
	Path->ClearSplinePoints(false);
	Path->AddSplinePoint(FVector(0, 0, 0), ESplineCoordinateSpace::Local, false);
	Path->AddSplinePoint(FVector(1500, 0, 0), ESplineCoordinateSpace::Local, false);
	for (int32 i = 0; i < Path->GetNumberOfSplinePoints(); ++i)
	{
		Path->SetSplinePointType(i, ESplinePointType::Linear, false);
	}
	Path->UpdateSpline();

	auto MakeIsm = [this](const TCHAR* Name)
	{
		UInstancedStaticMeshComponent* C = CreateDefaultSubobject<UInstancedStaticMeshComponent>(Name);
		C->SetupAttachment(Path);
		C->SetMobility(EComponentMobility::Static);
		return C;
	};
	Pillars = MakeIsm(TEXT("Pilastri"));
	Panels = MakeIsm(TEXT("Pannelli"));
	Walls = MakeIsm(TEXT("Muretto"));
	Copings = MakeIsm(TEXT("Copertina"));

	// The hospital's fence by default.
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Pillar(TEXT("/Game/Mazzarino80/Buildings/OspedaleModulare/SM_M80_OspedaleModulare_RecintoPilastro.SM_M80_OspedaleModulare_RecintoPilastro"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Panel(TEXT("/Game/Mazzarino80/Buildings/OspedaleModulare/SM_M80_OspedaleModulare_RecintoPannello.SM_M80_OspedaleModulare_RecintoPannello"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	PillarMesh = Pillar.Object;
	PanelMesh = Panel.Object;
	Walls->SetStaticMesh(Cube.Object);
	Copings->SetStaticMesh(Cube.Object);
}

void AM80ModularFence::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	Rebuild();
}

double AM80ModularFence::GroundZ(const FVector& World) const
{
	return bFollowGround ? AM80Sidewalk::TraceGroundZ(GetWorld(), this, World, World.Z) : World.Z;
}

void AM80ModularFence::Rebuild()
{
	for (UInstancedStaticMeshComponent* C : {Pillars.Get(), Panels.Get(), Walls.Get(), Copings.Get()})
	{
		C->ClearInstances();
	}
	BayCount = 0;
	const int32 Points = Path->GetNumberOfSplinePoints();
	Path->SetClosedLoop(bClosedLoop && Points > 2);
	for (int32 i = 0; i < Points; ++i)
	{
		Path->SetSplinePointType(i, ESplinePointType::Linear, false);
	}
	Path->UpdateSpline();
	if (!PillarMesh || !PanelMesh || Points < 2)
	{
		return;
	}
	Pillars->SetStaticMesh(PillarMesh);
	Panels->SetStaticMesh(PanelMesh);
	UMaterialInterface* WallMat = WallMaterial ? WallMaterial.Get() : PillarMesh->GetMaterial(0);
	Walls->SetMaterial(0, WallMat);
	Copings->SetMaterial(0, CopingMaterial ? CopingMaterial.Get() : WallMat);
	Walls->SetVisibility(bWall);
	Copings->SetVisibility(bWall);

	const FBox PillarBox = PillarMesh->GetBoundingBox();
	const FBox PanelBox = PanelMesh->GetBoundingBox();
	const double PillarW = FMath::Max(1.0, PillarBox.GetSize().X);
	const double PanelW = FMath::Max(1.0, PanelBox.GetSize().X);
	const double Bay = PillarW + PanelsPerBay * PanelW;
	const double WallH = bWall ? WallHeightCm : 0.0;
	const double Thick = WallThicknessCm;
	const FTransform& ToWorld = Path->GetComponentTransform();
	const FTransform ToLocal = ToWorld.Inverse();

	// One straight stretch between two spline points at a time; its bays share the stretch evenly.
	struct FBayTop { FVector Start, End; double Top; };
	TArray<FBayTop> Bays;
	TArray<int32> StretchFirstBay;
	const int32 Stretches = Path->IsClosedLoop() ? Points : Points - 1;
	for (int32 s = 0; s < Stretches; ++s)
	{
		const FVector A = Path->GetLocationAtSplinePoint(s, ESplineCoordinateSpace::World);
		const FVector B = Path->GetLocationAtSplinePoint((s + 1) % Points, ESplineCoordinateSpace::World);
		const double Len = FVector::Dist2D(A, B);
		if (Len < 10.0)
		{
			continue;
		}
		StretchFirstBay.Add(Bays.Num());
		const int32 N = FMath::Max(1, FMath::RoundToInt(Len / Bay));
		for (int32 k = 0; k < N; ++k)
		{
			const FVector P0 = FMath::Lerp(A, B, double(k) / N);
			const FVector P1 = FMath::Lerp(A, B, double(k + 1) / N);
			// the bay stands on the lower of its two ends, so the wall never floats
			const double G = FMath::Min(GroundZ(P0), GroundZ(P1));
			Bays.Add({P0, P1, G + WallH});
		}
	}
	BayCount = Bays.Num();
	if (Bays.IsEmpty())
	{
		return;
	}

	auto AddLocal = [&ToLocal](UInstancedStaticMeshComponent* C, const FTransform& World)
	{
		C->AddInstance(World * ToLocal, false);
	};
	const FVector Up(0, 0, 1);
	for (const FBayTop& Bay2 : Bays)
	{
		FVector Dir = Bay2.End - Bay2.Start;
		Dir.Z = 0;
		const double Len = Dir.Size();
		Dir /= Len;
		const FQuat Rot = FRotationMatrix::MakeFromXZ(Dir, Up).ToQuat();
		const FVector Mid = (Bay2.Start + Bay2.End) / 2;
		const double Ground = Bay2.Top - WallH;
		if (bWall && WallH > 0)
		{
			const double Bottom = Ground - WallBuriedCm;
			AddLocal(Walls, FTransform(Rot, FVector(Mid.X, Mid.Y, (Bottom + Bay2.Top - 6.0) / 2), FVector(Len / 100.0, Thick / 100.0, (Bay2.Top - 6.0 - Bottom) / 100.0)));
			AddLocal(Copings, FTransform(Rot, FVector(Mid.X, Mid.Y, Bay2.Top - 3.0), FVector(Len / 100.0, (Thick + 8.0) / 100.0, 0.06)));
		}
		// the panels fill the bay between the half pillars at its ends
		const double Free = Len - PillarW;
		const double Stretch = Free / (PanelsPerBay * PanelW);
		for (int32 p = 0; p < PanelsPerBay; ++p)
		{
			const double At = PillarW / 2 + (p + 0.5) * Free / PanelsPerBay;
			const FVector Pos = Bay2.Start + Dir * At;
			const double PanelPivotX = -(PanelBox.Min.X + PanelBox.Max.X) / 2 * Stretch;
			AddLocal(Panels, FTransform(Rot, FVector(Pos.X, Pos.Y, Bay2.Top) + Dir * PanelPivotX, FVector(Stretch, 1.0, 1.0)));
		}
	}
	// pillars at the bay joints, on a block as high as the higher of the two bays
	auto PlacePillar = [&](const FVector& At, const FVector& Dir, double TopA, double TopB)
	{
		const double Top = FMath::Max(TopA, TopB);
		const double Ground = FMath::Min(TopA, TopB) - WallH;
		const FQuat Rot = FRotationMatrix::MakeFromXZ(Dir, Up).ToQuat();
		if (bWall && WallH > 0)
		{
			const double Bottom = Ground - WallBuriedCm;
			AddLocal(Walls, FTransform(Rot, FVector(At.X, At.Y, (Bottom + Top) / 2), FVector((PillarW + 6.0) / 100.0, (Thick + 6.0) / 100.0, (Top - Bottom) / 100.0)));
		}
		AddLocal(Pillars, FTransform(Rot, FVector(At.X, At.Y, Top), FVector::OneVector));
	};
	for (int32 i = 0; i < Bays.Num(); ++i)
	{
		const FBayTop& B = Bays[i];
		FVector Dir = B.End - B.Start;
		Dir.Z = 0;
		Dir.Normalize();
		const bool bFirst = i == 0;
		if (bFirst && !Path->IsClosedLoop())
		{
			if (bEndPillars)
			{
				PlacePillar(B.Start, Dir, B.Top, B.Top);
			}
		}
		const bool bLast = i == Bays.Num() - 1;
		if (bLast && !Path->IsClosedLoop())
		{
			if (bEndPillars)
			{
				PlacePillar(B.End, Dir, B.Top, B.Top);
			}
			continue;
		}
		const FBayTop& Next = Bays[(i + 1) % Bays.Num()];
		PlacePillar(B.End, Dir, B.Top, Next.Top);
	}
	for (UInstancedStaticMeshComponent* C : {Pillars.Get(), Panels.Get(), Walls.Get(), Copings.Get()})
	{
		C->MarkRenderStateDirty();
	}
}
