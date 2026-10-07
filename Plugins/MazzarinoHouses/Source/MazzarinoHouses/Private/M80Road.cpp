#include "M80Road.h"
#include "M80MeshBuffer.h"
#include "M80Sidewalk.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/SplineComponent.h"
#include "Components/SplineMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "Engine/StaticMesh.h"
#include "Materials/Material.h"
#include "Materials/MaterialInterface.h"
#include "MaterialDomain.h"

namespace M80Rd
{
const FName GeneratedTag(TEXT("M80RoadPiece"));
// Steepest sideways tilt: beyond this the terrain is a wall or a ditch, not a road camber.
constexpr double MaxRoll = 0.26;

UStaticMesh* LoadMesh(const TCHAR* Path)
{
	return LoadObject<UStaticMesh>(nullptr, Path, nullptr, LOAD_NoWarn);
}
}

AM80Road::AM80Road()
{
	PrimaryActorTick.bCanEverTick = false;
	Path = CreateDefaultSubobject<USplineComponent>(TEXT("Path"));
	SetRootComponent(Path);
	Path->SetMobility(EComponentMobility::Static);
	Path->bInputSplinePointsToConstructionScript = true;
	Path->SetUnselectedSplineSegmentColor(FLinearColor(0.85f, 0.35f, 0.2f));
	// A new road: 20 m straight.
	Path->SetSplinePoints({FVector(0, 0, 0), FVector(2000, 0, 0)}, ESplineCoordinateSpace::Local);
	Slab = CreateDefaultSubobject<UDynamicMeshComponent>(TEXT("Slab"));
	Slab->SetupAttachment(Path);
	Slab->SetMobility(EComponentMobility::Static);
	Slab->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);
	// Houses, sidewalks and stairs must keep finding the real ground under a road.
	Tags.Add(TEXT("M80IgnoreGround"));
}

void AM80Road::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	Rebuild();
}

double AM80Road::GroundZ(const FVector& World) const
{
	return AM80Sidewalk::TraceGroundZ(GetWorld(), this, World, World.Z);
}

AM80Road::FStation AM80Road::StationAt(double D) const
{
	FStation S;
	S.D = D;
	S.Pos = Path->GetLocationAtDistanceAlongSpline(D, ESplineCoordinateSpace::World);
	FVector Dir = Path->GetDirectionAtDistanceAlongSpline(D, ESplineCoordinateSpace::World);
	Dir.Z = 0;
	if (!Dir.Normalize())
	{
		Dir = FVector::ForwardVector;
	}
	S.Right = FVector(-Dir.Y, Dir.X, 0);
	S.Roll = 0.0;
	if (bSnapToGround)
	{
		const double Half = FMath::Max(50.0, double(WidthCm)) * 0.5;
		const double ZC = GroundZ(S.Pos);
		double Z = ZC;
		if (bBankWithGround)
		{
			const double ZL = GroundZ(S.Pos - S.Right * Half);
			const double ZR = GroundZ(S.Pos + S.Right * Half);
			S.Roll = FMath::Clamp(FMath::Atan2(ZR - ZL, 2.0 * Half), -M80Rd::MaxRoll, M80Rd::MaxRoll);
			// On a hump across, the middle wins (the edges then stand on their thickness rather than
			// the terrain poking through the middle).
			Z = FMath::Max(ZC, 0.5 * (ZL + ZR));
		}
		S.Pos.Z = Z;
	}
	S.Pos.Z += HeightCm;
	return S;
}

UStaticMesh* AM80Road::SurfaceMesh() const
{
	switch (Surface)
	{
	case EM80RoadSurface::MainLava:
		return M80Rd::LoadMesh(TEXT("/Game/Mazzarino80/RoadSource/Migrated/LowPoly.LowPoly"));
	case EM80RoadSurface::CurvedLava:
		return M80Rd::LoadMesh(TEXT("/Game/Mazzarino80/RoadSource/Migrated/Lavica_curved.Lavica_curved"));
	case EM80RoadSurface::Custom:
		return CustomMesh;
	default:
		return nullptr;
	}
}

void AM80Road::Rebuild()
{
	if (!Path || !Slab)
	{
		return;
	}
	// Collected by tag: construction-script reruns can replace component pointers.
	TInlineComponentArray<USplineMeshComponent*> Existing(this);
	for (USplineMeshComponent* C : Existing)
	{
		if (C && C->ComponentHasTag(M80Rd::GeneratedTag))
		{
			C->DestroyComponent();
		}
	}
	Slab->SetMesh(UE::Geometry::FDynamicMesh3());
	PieceCount = 0;
	if (Path->GetNumberOfSplinePoints() < 2 || Path->GetSplineLength() < 10.0)
	{
		return;
	}
	if (Surface == EM80RoadSurface::Slab)
	{
		BuildSlab();
	}
	else if (UStaticMesh* M = SurfaceMesh())
	{
		BuildPieces(M);
	}
}

void AM80Road::BuildPieces(UStaticMesh* Mesh)
{
	const FBox Box = Mesh->GetBoundingBox();
	const double MeshL = Box.Max.X - Box.Min.X, MeshW = Box.Max.Y - Box.Min.Y;
	if (MeshL <= 1.0 || MeshW <= 1.0)
	{
		return;
	}
	const double Width = FMath::Max(50.0, double(WidthCm));
	const double SY = Width / MeshW;
	const double SZ = SY * FMath::Clamp(double(VerticalScale), 0.1, 5.0);
	// Proportional pieces keep the setts square; the count is rounded so the last piece is not a sliver.
	const double Wanted = PieceLengthCm > 1.f ? double(PieceLengthCm) : MeshL * SY;
	const double Length = Path->GetSplineLength();
	const int32 N = FMath::Max(1, FMath::RoundToInt(Length / FMath::Max(50.0, Wanted)));

	const FTransform& T = Path->GetComponentTransform();
	TArray<FStation> St;
	TArray<FVector> P;
	for (int32 i = 0; i <= N; ++i)
	{
		St.Add(StationAt(Length * i / N));
		P.Add(T.InverseTransformPosition(St.Last().Pos));
	}
	// Smooth tangents through the piece ends (they follow both the curve and the terrain).
	auto Tangent = [&P, N](int32 j)
	{
		if (j == 0)
		{
			return P[1] - P[0];
		}
		return j == N ? P[N] - P[N - 1] : (P[j + 1] - P[j - 1]) * 0.5;
	};
	const FVector2D Offset(-Box.GetCenter().Y * SY, -Box.Max.Z * SZ);
	for (int32 i = 0; i < N; ++i)
	{
		USplineMeshComponent* Seg = NewObject<USplineMeshComponent>(this, NAME_None, RF_Transactional);
		Seg->CreationMethod = EComponentCreationMethod::UserConstructionScript;
		Seg->ComponentTags.Add(M80Rd::GeneratedTag);
		Seg->SetupAttachment(Path);
		Seg->SetMobility(EComponentMobility::Static);
		Seg->SetStaticMesh(Mesh);
		if (Material)
		{
			for (int32 Slot = 0; Slot < Mesh->GetStaticMaterials().Num(); ++Slot)
			{
				Seg->SetMaterial(Slot, Material);
			}
		}
		Seg->SetForwardAxis(ESplineMeshAxis::X, false);
		Seg->SetBoundaryMin(Box.Min.X, false);
		Seg->SetBoundaryMax(Box.Max.X, false);
		Seg->SetStartAndEnd(P[i], Tangent(i), P[i + 1], Tangent(i + 1), false);
		Seg->SetStartScale(FVector2D(SY, SZ), false);
		Seg->SetEndScale(FVector2D(SY, SZ), false);
		Seg->SetStartOffset(Offset, false);
		Seg->SetEndOffset(Offset, false);
		// A positive spline-mesh roll lowers the right side.
		Seg->SetStartRoll(-St[i].Roll, false);
		Seg->SetEndRoll(-St[i + 1].Roll, false);
		Seg->SetCollisionProfileName(bCollision ? TEXT("BlockAll") : TEXT("NoCollision"));
		Seg->RegisterComponent();
		Seg->UpdateMesh();
	}
	PieceCount = N;
}

void AM80Road::BuildSlab()
{
	const FTransform& T = Path->GetComponentTransform();
	const double Length = Path->GetSplineLength();
	const double Half = FMath::Max(50.0, double(WidthCm)) * 0.5;
	const double Step = FMath::Clamp(double(SampleCm), 25.0, 1000.0);
	const double Thick = FMath::Clamp(double(SlabThicknessCm), 2.0, 200.0);
	const int32 Rows = FMath::Max(1, FMath::CeilToInt(Length / Step));
	const int32 Cols = FMath::Max(2, FMath::CeilToInt(2.0 * Half / (Step * 0.5)));
	const bool bDrape = bSnapToGround && bBankWithGround;

	// Top grid: rows along the road, columns across (left to right), local space.
	TArray<TArray<FVector3d>> P;
	TArray<TArray<FVector2f>> UV;
	P.SetNum(Rows + 1);
	UV.SetNum(Rows + 1);
	for (int32 i = 0; i <= Rows; ++i)
	{
		const FStation S = StationAt(Length * i / Rows);
		for (int32 j = 0; j <= Cols; ++j)
		{
			const double Lat = -Half + 2.0 * Half * j / Cols;
			FVector W = S.Pos + S.Right * Lat;
			// Draped: every grid point on the terrain; otherwise level across at the centre height.
			W.Z = bDrape ? GroundZ(W) + HeightCm : S.Pos.Z;
			P[i].Add(T.InverseTransformPosition(W));
			UV[i].Add(FVector2f(float(S.D / 100.0), float(Lat / 100.0)));
		}
	}

	FM80MeshBuffer B;
	const FVector3d Down(0, 0, -Thick);
	auto Normal = [&](int32 i, int32 j)
	{
		const FVector3d Du = P[i][FMath::Min(j + 1, Cols)] - P[i][FMath::Max(j - 1, 0)];
		const FVector3d Dv = P[FMath::Min(i + 1, Rows)][j] - P[FMath::Max(i - 1, 0)][j];
		FVector3d Nn = FVector3d::CrossProduct(Du, Dv).GetSafeNormal();
		return FVector3f(Nn.Z < 0 ? -Nn : Nn);
	};
	for (int32 i = 0; i < Rows; ++i)
	{
		for (int32 j = 0; j < Cols; ++j)
		{
			B.TriN(0, P[i][j], P[i][j + 1], P[i + 1][j + 1], UV[i][j], UV[i][j + 1], UV[i + 1][j + 1], Normal(i, j), Normal(i, j + 1), Normal(i + 1, j + 1));
			B.TriN(0, P[i][j], P[i + 1][j + 1], P[i + 1][j], UV[i][j], UV[i + 1][j + 1], UV[i + 1][j], Normal(i, j), Normal(i + 1, j + 1), Normal(i + 1, j));
		}
	}
	// Edges: vertical skirts on both sides and at both ends, as deep as the slab.
	auto Skirt = [&](const FVector3d& A, const FVector3d& Bp, const FVector2f& UA, const FVector2f& UB, const FVector3d& Out)
	{
		const FVector2f Dv(0.f, float(Thick / 100.0));
		B.Quad(0, A, Bp, Bp + Down, A + Down, UA, UB, UB + Dv, UA + Dv, Out);
	};
	for (int32 i = 0; i < Rows; ++i)
	{
		const FVector3d Out = FVector3d::CrossProduct(FVector3d::UnitZ(), P[i + 1][Cols] - P[i][Cols]).GetSafeNormal(); // right side
		Skirt(P[i][Cols], P[i + 1][Cols], FVector2f(UV[i][Cols].X, 0.f), FVector2f(UV[i + 1][Cols].X, 0.f), Out);
		Skirt(P[i][0], P[i + 1][0], FVector2f(UV[i][0].X, 0.f), FVector2f(UV[i + 1][0].X, 0.f), -Out);
	}
	for (int32 j = 0; j < Cols; ++j)
	{
		const FVector3d Fwd = (P[1][j] - P[0][j]).GetSafeNormal2D();
		Skirt(P[0][j], P[0][j + 1], FVector2f(UV[0][j].Y, 0.f), FVector2f(UV[0][j + 1].Y, 0.f), -Fwd);
		const FVector3d Fwd2 = (P[Rows][j] - P[Rows - 1][j]).GetSafeNormal2D();
		Skirt(P[Rows][j], P[Rows][j + 1], FVector2f(UV[Rows][j].Y, 0.f), FVector2f(UV[Rows][j + 1].Y, 0.f), Fwd2);
	}

	UE::Geometry::FDynamicMesh3 Dyn;
	B.ToDynamicMesh(Dyn);
	Slab->SetMesh(MoveTemp(Dyn));
	UMaterialInterface* M = Material ? Material.Get()
		: LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Mazzarino80/Kit/Stairs/MI_M80_Lavica_secondaria.MI_M80_Lavica_secondaria"), nullptr, LOAD_NoWarn);
	Slab->ConfigureMaterialSet({M ? M : UMaterial::GetDefaultMaterial(MD_Surface)});
	Slab->SetComplexAsSimpleCollisionEnabled(bCollision, true);
	Slab->SetCollisionProfileName(bCollision ? TEXT("BlockAll") : TEXT("NoCollision"));
	PieceCount = Rows;
}
