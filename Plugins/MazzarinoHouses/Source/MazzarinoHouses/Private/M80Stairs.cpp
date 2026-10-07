#include "M80Stairs.h"
#include "M80MeshBuffer.h"
#include "M80Sidewalk.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/SplineComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "Materials/Material.h"
#include "Materials/MaterialInterface.h"
#include "MaterialDomain.h"

namespace M80St
{
// Material slots of the generated mesh.
enum ESlot : int32 { Lava = 0, Tread = 1, Wall = 2, Iron = 3, Wood = 4, Cane = 5 };

// Longest straight piece: treads, walls and rails are cut so they follow curves and slopes.
constexpr double Piece = 50.0;

UMaterialInterface* Kit(const TCHAR* Name)
{
	// Made by Scripts/m80_stairs_setup.py.
	return LoadObject<UMaterialInterface>(nullptr, *FString::Printf(TEXT("/Game/Mazzarino80/Kit/Stairs/%s.%s"), Name, Name), nullptr, LOAD_NoWarn);
}

UMaterialInterface* Pick(UMaterialInterface* Override, const TCHAR* Name)
{
	UMaterialInterface* M = Override ? Override : Kit(Name);
	return M ? M : UMaterial::GetDefaultMaterial(MD_Surface);
}

/** Cuts [A, B] into pieces no longer than Piece. */
TArray<double> Cuts(double A, double B)
{
	TArray<double> Out;
	const int32 N = FMath::Max(1, FMath::CeilToInt((B - A) / Piece));
	for (int32 i = 0; i <= N; ++i)
	{
		Out.Add(A + (B - A) * i / N);
	}
	return Out;
}

/** A straight bar of rectangular section between two points (rails, posts). */
void Beam(FM80MeshBuffer& B, int32 Slot, const FVector3d& P0, const FVector3d& P1, const FVector3d& Side, double W, double H)
{
	const FVector3d X = (P1 - P0).GetSafeNormal();
	if (X.IsNearlyZero())
	{
		return;
	}
	const FVector3d Y = (Side - X * FVector3d::DotProduct(Side, X)).GetSafeNormal();
	const FVector3d Z = FVector3d::CrossProduct(X, Y).GetSafeNormal() * (FVector3d::CrossProduct(X, Y).Z < 0 ? -1.0 : 1.0);
	B.Box(Slot, (P0 + P1) * 0.5, X, Y, Z.IsNearlyZero() ? FVector3d::UnitZ() : Z, FVector3d((P1 - P0).Size() * 0.5, W * 0.5, H * 0.5));
}
}


AM80Stairs::AM80Stairs()
{
	PrimaryActorTick.bCanEverTick = false;
	Path = CreateDefaultSubobject<USplineComponent>(TEXT("Path"));
	SetRootComponent(Path);
	Path->SetMobility(EComponentMobility::Static);
	Path->bInputSplinePointsToConstructionScript = true;
	Path->SetUnselectedSplineSegmentColor(FLinearColor(0.3f, 0.6f, 0.95f));
	// A new stair: 4 m along the ground.
	Path->SetSplinePoints({FVector(0, 0, 0), FVector(400, 0, 100)}, ESplineCoordinateSpace::Local);
	Mesh = CreateDefaultSubobject<UDynamicMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Path);
	Mesh->SetMobility(EComponentMobility::Static);
	Mesh->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);
	// Houses must keep finding the real ground under a stair.
	Tags.Add(TEXT("M80IgnoreGround"));
}

void AM80Stairs::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	Rebuild();
}

double AM80Stairs::GroundAt(const FVector& World) const
{
	return AM80Sidewalk::TraceGroundZ(GetWorld(), this, World, World.Z - 30.0);
}

FVector AM80Stairs::RightAt(double D) const
{
	FVector Dir = Path->GetDirectionAtDistanceAlongSpline(FMath::Clamp(D, 0.0, Length), ESplineCoordinateSpace::World);
	Dir.Z = 0;
	if (!Dir.Normalize())
	{
		Dir = FVector::ForwardVector;
	}
	return FVector(-Dir.Y, Dir.X, 0);
}

FVector AM80Stairs::PointAt(double D, double Lateral, double Z) const
{
	FVector W = Path->GetLocationAtDistanceAlongSpline(FMath::Clamp(D, 0.0, Length), ESplineCoordinateSpace::World) + RightAt(D) * Lateral;
	W.Z = Z;
	return Path->GetComponentTransform().InverseTransformPosition(W);
}

double AM80Stairs::EdgeLineZ(double D) const
{
	if (EdgeLine.Num() == 0)
	{
		return 0.0;
	}
	if (D <= EdgeLine[0].X)
	{
		return EdgeLine[0].Y;
	}
	for (int32 i = 1; i < EdgeLine.Num(); ++i)
	{
		if (D <= EdgeLine[i].X)
		{
			const double Span = FMath::Max(EdgeLine[i].X - EdgeLine[i - 1].X, 1e-3);
			return FMath::Lerp(EdgeLine[i - 1].Y, EdgeLine[i].Y, (D - EdgeLine[i - 1].X) / Span);
		}
	}
	return EdgeLine.Last().Y;
}

double AM80Stairs::SurfaceZ(double D) const
{
	for (const FTread& T : Treads)
	{
		if (D >= T.D0 - 0.01 && D <= T.D1 + 0.01)
		{
			return FMath::Lerp(T.Z0, T.Z1, FMath::Clamp((D - T.D0) / FMath::Max(T.D1 - T.D0, 1e-3), 0.0, 1.0));
		}
	}
	return EdgeLineZ(D);
}

void AM80Stairs::BuildTreads(FM80MeshBuffer& B) const
{
	const FTransform& T = Path->GetComponentTransform();
	const double HalfW = FMath::Max(20.0, double(WidthCm)) * 0.5;
	const double Nose = FMath::Max(0.0, double(NosingCm));
	const double Rise = RealRiserCm;
	const FVector3d Up(0, 0, 1);
	auto Local = [&T](const FVector& V) { return FVector3d(T.InverseTransformVectorNoScale(V)); };
	auto Ground = [this](double D, double Lat) { return GroundAt(Path->GetComponentTransform().TransformPosition(PointAt(D, Lat, 0.0))) - 25.0; };
	auto Soffit = [&](double D) { return EdgeLineZ(D) - Rise - double(SlabCm); };
	// Side faces of the steps between D0 and D1: the ends of the lava steps, then the wall finish down
	// to the ground (or to the slab's soffit).
	auto Sides = [&](double D0, double D1, double Z0, double Z1)
	{
		for (const double S : {-1.0, 1.0})
		{
			const FVector3d Out = Local(RightAt((D0 + D1) * 0.5) * S);
			const double Band = Rise + 8.0;
			const double B0 = bFillToGround ? FMath::Min(Ground(D0, S * HalfW), Z0 - Band) : Soffit(D0);
			const double B1 = bFillToGround ? FMath::Min(Ground(D1, S * HalfW), Z1 - Band) : Soffit(D1);
			const double M0 = FMath::Max(Z0 - Band, B0), M1 = FMath::Max(Z1 - Band, B1);
			B.QuadProjected(M80St::Lava, PointAt(D0, S * HalfW, M0), PointAt(D1, S * HalfW, M1), PointAt(D1, S * HalfW, Z1), PointAt(D0, S * HalfW, Z0), Out);
			B.QuadProjected(M80St::Wall, PointAt(D0, S * HalfW, B0), PointAt(D1, S * HalfW, B1), PointAt(D1, S * HalfW, M1), PointAt(D0, S * HalfW, M0), Out);
		}
		if (!bFillToGround)
		{
			B.QuadProjected(M80St::Wall, PointAt(D0, -HalfW, Soffit(D0)), PointAt(D0, HalfW, Soffit(D0)), PointAt(D1, HalfW, Soffit(D1)), PointAt(D1, -HalfW, Soffit(D1)), -Up);
		}
	};
	// Top of a stretch of tread, cut in pieces; setts courses run across the stair.
	auto Top = [&](int32 Slot, double D0, double D1, double Z0, double Z1, double DA, double DB)
	{
		const TArray<double> C = M80St::Cuts(DA, DB);
		for (int32 i = 0; i + 1 < C.Num(); ++i)
		{
			const double ZA = FMath::Lerp(Z0, Z1, (C[i] - D0) / FMath::Max(D1 - D0, 1e-3));
			const double ZB = FMath::Lerp(Z0, Z1, (C[i + 1] - D0) / FMath::Max(D1 - D0, 1e-3));
			B.QuadProjected(Slot, PointAt(C[i], -HalfW, ZA), PointAt(C[i], HalfW, ZA), PointAt(C[i + 1], HalfW, ZB), PointAt(C[i + 1], -HalfW, ZB), Up);
			Sides(C[i], C[i + 1], ZA, ZB);
		}
	};
	// Vertical face across the stair at D, between Z0 and Z1, facing Dir (+1 forward, -1 back).
	auto Across = [&](int32 Slot, double D, double Z0, double Z1, double Dir)
	{
		if (FMath::Abs(Z1 - Z0) < 0.5)
		{
			return;
		}
		const FVector3d Facing = Local(FVector(-RightAt(D).Y, RightAt(D).X, 0) * -Dir);
		B.QuadProjected(Slot, PointAt(D, -HalfW, FMath::Min(Z0, Z1)), PointAt(D, HalfW, FMath::Min(Z0, Z1)), PointAt(D, HalfW, FMath::Max(Z0, Z1)), PointAt(D, -HalfW, FMath::Max(Z0, Z1)), Facing);
	};

	for (int32 k = 0; k < Treads.Num(); ++k)
	{
		const FTread& S = Treads[k];
		const bool bEdge = Nose > 0.5 && StepCount > 0;
		if (!bEdge)
		{
			Top(M80St::Tread, S.D0, S.D1, S.Z0, S.Z1, S.D0, S.D1);
		}
		else if (S.bEdgeAtStart)
		{
			const double E = FMath::Min(S.D0 + Nose, S.D1);
			Top(M80St::Lava, S.D0, S.D1, S.Z0, S.Z1, S.D0, E);
			if (E < S.D1 - 0.5)
			{
				Top(M80St::Tread, S.D0, S.D1, S.Z0, S.Z1, E, S.D1);
			}
		}
		else
		{
			const double E = FMath::Max(S.D1 - Nose, S.D0);
			if (E > S.D0 + 0.5)
			{
				Top(M80St::Tread, S.D0, S.D1, S.Z0, S.Z1, S.D0, E);
			}
			Top(M80St::Lava, S.D0, S.D1, S.Z0, S.Z1, E, S.D1);
		}
		// Risers: lava, facing the lower side.
		if (S.bEdgeAtStart)
		{
			const double Below = k == 0 ? SurfaceStartZ : Treads[k - 1].Z1;
			Across(M80St::Lava, S.D0, Below, S.Z0, -1.0);
		}
		else
		{
			const double Below = k + 1 == Treads.Num() ? SurfaceEndZ : Treads[k + 1].Z0;
			Across(M80St::Lava, S.D1, Below, S.Z1, 1.0);
		}
	}
	// Ends: down to the ground, or to the soffit of a slab.
	if (Treads.Num())
	{
		const double Z0 = FMath::Min(Treads[0].bEdgeAtStart ? SurfaceStartZ : Treads[0].Z0, Treads[0].Z0);
		const double Z1 = FMath::Min(Treads.Last().bEdgeAtStart ? Treads.Last().Z1 : SurfaceEndZ, Treads.Last().Z1);
		Across(M80St::Wall, 0.0, bFillToGround ? FMath::Min(Ground(0.0, 0.0), Z0 - 1.0) : Soffit(0.0), Z0, -1.0);
		Across(M80St::Wall, Length, bFillToGround ? FMath::Min(Ground(Length, 0.0), Z1 - 1.0) : Soffit(Length), Z1, 1.0);
	}
}

void AM80Stairs::BuildWall(FM80MeshBuffer& B, double Side) const
{
	const FTransform& T = Path->GetComponentTransform();
	auto Local = [&T](const FVector& V) { return FVector3d(T.InverseTransformVectorNoScale(V)); };
	const double HalfW = FMath::Max(20.0, double(WidthCm)) * 0.5;
	const double Th = WallThicknessCm;
	const double In = Side * HalfW, OutL = Side * (HalfW + Th);
	const double Cop = bWallCoping ? 6.0 : 0.0, Over = 4.0;
	const TArray<double> C = M80St::Cuts(0.0, Length);
	auto TopZ = [&](double D) { return EdgeLineZ(D) + WallHeightCm; };
	auto Bottom = [&](double D)
	{
		const double G = FMath::Min(GroundAt(T.TransformPosition(PointAt(D, In, 0.0))), GroundAt(T.TransformPosition(PointAt(D, OutL, 0.0))));
		return FMath::Min(G - 30.0, TopZ(D) - 20.0);
	};
	TArray<double> Bot;
	for (const double D : C)
	{
		Bot.Add(Bottom(D));
	}
	for (int32 i = 0; i + 1 < C.Num(); ++i)
	{
		const double D0 = C[i], D1 = C[i + 1];
		const double Z0 = TopZ(D0), Z1 = TopZ(D1);
		const FVector3d Out = Local(RightAt((D0 + D1) * 0.5) * Side);
		B.QuadProjected(M80St::Wall, PointAt(D0, OutL, Bot[i]), PointAt(D1, OutL, Bot[i + 1]), PointAt(D1, OutL, Z1), PointAt(D0, OutL, Z0), Out);
		B.QuadProjected(M80St::Wall, PointAt(D0, In, Bot[i]), PointAt(D1, In, Bot[i + 1]), PointAt(D1, In, Z1), PointAt(D0, In, Z0), -Out);
		if (Cop > 0)
		{
			const double A = In - Side * Over, Bq = OutL + Side * Over;
			B.QuadProjected(M80St::Lava, PointAt(D0, A, Z0 + Cop), PointAt(D0, Bq, Z0 + Cop), PointAt(D1, Bq, Z1 + Cop), PointAt(D1, A, Z1 + Cop), FVector3d(0, 0, 1));
			B.QuadProjected(M80St::Lava, PointAt(D0, Bq, Z0), PointAt(D1, Bq, Z1), PointAt(D1, Bq, Z1 + Cop), PointAt(D0, Bq, Z0 + Cop), Out);
			B.QuadProjected(M80St::Lava, PointAt(D0, A, Z0), PointAt(D1, A, Z1), PointAt(D1, A, Z1 + Cop), PointAt(D0, A, Z0 + Cop), -Out);
			B.QuadProjected(M80St::Lava, PointAt(D0, A, Z0), PointAt(D0, Bq, Z0), PointAt(D1, Bq, Z1), PointAt(D1, A, Z1), FVector3d(0, 0, -1));
		}
		else
		{
			B.QuadProjected(M80St::Wall, PointAt(D0, In, Z0), PointAt(D0, OutL, Z0), PointAt(D1, OutL, Z1), PointAt(D1, In, Z1), FVector3d(0, 0, 1));
		}
	}
	// End faces.
	for (const int32 End : {0, 1})
	{
		const double D = End ? Length : 0.0;
		const double Z = TopZ(D);
		const FVector3d Facing = Local(FVector(-RightAt(D).Y, RightAt(D).X, 0) * (End ? -1.0 : 1.0));
		const double Bo = End ? Bot.Last() : Bot[0];
		B.QuadProjected(M80St::Wall, PointAt(D, In, Bo), PointAt(D, OutL, Bo), PointAt(D, OutL, Z), PointAt(D, In, Z), Facing);
		if (Cop > 0)
		{
			const double A = In - Side * Over, Bq = OutL + Side * Over;
			B.QuadProjected(M80St::Lava, PointAt(D, A, Z), PointAt(D, Bq, Z), PointAt(D, Bq, Z + Cop), PointAt(D, A, Z + Cop), Facing);
		}
	}
}

void AM80Stairs::BuildFence(FM80MeshBuffer& B, double Side, bool bOnWall) const
{
	const FTransform& T = Path->GetComponentTransform();
	auto Local = [&T](const FVector& V) { return FVector3d(T.InverseTransformVectorNoScale(V)); };
	const double HalfW = FMath::Max(20.0, double(WidthCm)) * 0.5;
	const double Lat = bOnWall ? Side * (HalfW + WallThicknessCm * 0.5) : Side * (HalfW - 10.0);
	const double H = FenceHeightCm;
	const double Cop = bWallCoping ? 6.0 : 0.0;
	// Feet of the fence: on the wall's top, or on the steps; the rails follow the edge line.
	auto Base = [&](double D) { return bOnWall ? EdgeLineZ(D) + WallHeightCm + Cop : SurfaceZ(D); };
	auto Line = [&](double D) { return bOnWall ? Base(D) : EdgeLineZ(D); };
	auto P = [&](double D, double Z) { return FVector3d(PointAt(D, Lat, Z)); };
	auto Rail = [&](int32 Slot, double Offset, double W, double Hh, bool bTube)
	{
		const TArray<double> C = M80St::Cuts(0.0, Length);
		TArray<FVector3d> Pts;
		for (const double D : C)
		{
			Pts.Add(P(D, Line(D) + Offset));
		}
		if (bTube)
		{
			B.Tube(Slot, Pts, W * 0.5, 8, true);
			return;
		}
		for (int32 i = 0; i + 1 < Pts.Num(); ++i)
		{
			M80St::Beam(B, Slot, Pts[i], Pts[i + 1], Local(RightAt(C[i])), W, Hh);
		}
	};
	const int32 Posts = FMath::Max(1, FMath::CeilToInt(Length / FMath::Max(50.f, PostSpacingCm)));
	auto PostD = [&](int32 i) { return Length * i / Posts; };
	FRandomStream Rnd(int32(GetTypeHash(GetName())) + int32(Side * 7));

	switch (FenceKind)
	{
	case EM80FenceKind::WroughtIron:
	{
		Rail(M80St::Iron, H, 5.0, 4.0, true);
		Rail(M80St::Iron, 10.0, 3.0, 1.5, false);
		for (int32 i = 0; i <= Posts; ++i)
		{
			const double D = PostD(i);
			M80St::Beam(B, M80St::Iron, P(D, Base(D) - 2.0), P(D, Line(D) + H), Local(RightAt(D)), 4.0, 4.0);
		}
		// Bars every 12 cm between the lower rail and the handrail.
		const int32 Bars = FMath::Max(1, FMath::FloorToInt(Length / 12.0));
		for (int32 i = 1; i < Bars; ++i)
		{
			const double D = Length * i / Bars;
			M80St::Beam(B, M80St::Iron, P(D, Line(D) + 10.0), P(D, Line(D) + H), Local(RightAt(D)), 1.6, 1.6);
		}
		break;
	}
	case EM80FenceKind::IronTube:
	{
		// Bent tubes: an upside-down U in each bay, on the edge line.
		for (int32 i = 0; i < Posts; ++i)
		{
			const double DA = FMath::Min(PostD(i) + 15.0, PostD(i + 1) - 10.0), DB = FMath::Max(PostD(i + 1) - 15.0, DA + 10.0);
			TArray<FVector3d> Pts = {P(DA, Base(DA) - 3.0), P(DA, Line(DA) + H - 6.0)};
			for (const double D : M80St::Cuts(DA, DB))
			{
				Pts.Add(P(D, Line(D) + H));
			}
			Pts.Add(P(DB, Line(DB) + H - 6.0));
			Pts.Add(P(DB, Base(DB) - 3.0));
			B.Tube(M80St::Iron, Pts, 2.4, 8, true);
		}
		break;
	}
	case EM80FenceKind::Wood:
	{
		for (int32 i = 0; i <= Posts; ++i)
		{
			const double D = PostD(i);
			M80St::Beam(B, M80St::Wood, P(D, Base(D) - (bOnWall ? 0.0 : 20.0)), P(D, Line(D) + H + 6.0), Local(RightAt(D)), 10.0, 10.0);
		}
		Rail(M80St::Wood, H - 4.0, 12.0, 5.0, false);
		Rail(M80St::Wood, H * 0.5, 10.0, 4.0, false);
		break;
	}
	case EM80FenceKind::Cane:
	{
		// Reed fence: canes side by side tied to two cross canes, on wooden posts.
		for (int32 i = 0; i <= Posts; ++i)
		{
			const double D = PostD(i);
			M80St::Beam(B, M80St::Wood, P(D, Base(D) - 20.0), P(D, Line(D) + H), Local(RightAt(D)), 7.0, 7.0);
		}
		const int32 Canes = FMath::Max(1, FMath::FloorToInt(Length / 4.6));
		const double Off = Side * 4.5;
		for (int32 i = 0; i <= Canes; ++i)
		{
			const double D = Length * i / Canes;
			const FVector3d Shift = Local(RightAt(D) * Off);
			B.Tube(M80St::Cane, {P(D, Base(D) - 3.0) + Shift, P(D, Line(D) + H + Rnd.FRandRange(-6.0, 6.0)) + Shift}, 2.0, 6, true);
		}
		for (const double Z : {H * 0.3, H * 0.8})
		{
			TArray<FVector3d> Pts;
			for (const double D : M80St::Cuts(0.0, Length))
			{
				Pts.Add(P(D, Line(D) + Z) + Local(RightAt(D) * (Off + Side * 2.5)));
			}
			B.Tube(M80St::Cane, Pts, 1.2, 5, true);
		}
		break;
	}
	default:
		break;
	}
}

void AM80Stairs::Rebuild()
{
	if (!Mesh || !Path)
	{
		return;
	}
	Mesh->SetMesh(UE::Geometry::FDynamicMesh3());
	Treads.Reset();
	EdgeLine.Reset();
	StepCount = LandingCount = 0;
	RealRiserCm = RealTreadCm = 0.f;
	Length = Path->GetSplineLength();
	if (Path->GetNumberOfSplinePoints() < 2 || Length < 20.0)
	{
		return;
	}

	// Heights of the two ends.
	const FVector A = Path->GetLocationAtDistanceAlongSpline(0.0, ESplineCoordinateSpace::World);
	const FVector Z = Path->GetLocationAtDistanceAlongSpline(Length, ESplineCoordinateSpace::World);
	SurfaceStartZ = bStartOnGround ? GroundAt(A) : A.Z;
	SurfaceEndZ = bEndOnGround ? GroundAt(Z) : Z.Z;
	const double Dz = SurfaceEndZ - SurfaceStartZ;
	const double Rise = FMath::Abs(Dz);
	const bool bUp = Dz >= 0.0;

	if (Kind == EM80StairsKind::FenceOnly)
	{
		// Walls and fences on the ground.
		for (const double D : M80St::Cuts(0.0, Length))
		{
			EdgeLine.Add(FVector2D(D, GroundAt(Path->GetLocationAtDistanceAlongSpline(D, ESplineCoordinateSpace::World))));
		}
	}
	else
	{
		int32 N = 0;
		double R = 0.0, Slope = 0.0;
		if (Kind == EM80StairsKind::Steps)
		{
			N = Rise < 2.0 ? 0 : FMath::Max(1, FMath::RoundToInt(Rise / FMath::Max(4.f, RiserCm)));
			R = N ? Rise / N : 0.0;
		}
		else
		{
			N = FMath::Max(1, FMath::RoundToInt(Length / FMath::Max(40.f, TreadCm)));
			R = FMath::Min<double>(RiserCm, Rise / N);
			Slope = Rise / N - R;
			if (R < 1.0)
			{
				N = 0; // a gentle slope: just a ramp
			}
		}
		const double Sgn = bUp ? 1.0 : -1.0;
		if (N == 0)
		{
			Treads.Add({0.0, Length, SurfaceStartZ, SurfaceEndZ, true});
			EdgeLine = {FVector2D(0.0, SurfaceStartZ), FVector2D(Length, SurfaceEndZ)};
		}
		else
		{
			StepCount = N;
			RealRiserCm = float(R);
			// Tread lengths: even, or (a stair longer than its steps need) steps of the set depth with the
			// extra length given to a few landings spread along the flight.
			TArray<double> Lens;
			Lens.Init(Length / N, N);
			const double Want = FMath::Max(22.f, StepTreadCm);
			if (Kind == EM80StairsKind::Steps && Length / N > Want * 1.25 && N > 1)
			{
				const double Extra = Length - Want * N;
				const int32 M = FMath::Clamp(FMath::RoundToInt(Extra / 150.0), 1, N - 1);
				Lens.Init(Want, N);
				for (int32 j = 0; j < M; ++j)
				{
					Lens[FMath::Clamp(FMath::RoundToInt(double(j + 1) * N / (M + 1)) - 1, 0, N - 1)] += Extra / M;
				}
				LandingCount = M;
			}
			RealTreadCm = float(LandingCount ? Want : Length / N);
			double DAcc = 0.0;
			for (int32 k = 0; k < N; ++k)
			{
				FTread S;
				S.D0 = DAcc;
				DAcc += Lens[k];
				S.D1 = k + 1 == N ? Length : DAcc;
				S.Z0 = SurfaceStartZ + Sgn * ((bUp ? k + 1 : k) * R + k * Slope);
				S.Z1 = S.Z0 + Sgn * Slope;
				S.bEdgeAtStart = bUp;
				Treads.Add(S);
			}
			// The line through the edges of the steps.
			if (bUp)
			{
				for (const FTread& S : Treads)
				{
					EdgeLine.Add(FVector2D(S.D0, S.Z0));
				}
				EdgeLine.Add(FVector2D(Length, Treads.Last().Z1));
			}
			else
			{
				EdgeLine.Add(FVector2D(0.0, SurfaceStartZ));
				for (const FTread& S : Treads)
				{
					EdgeLine.Add(FVector2D(S.D1, S.Z1));
				}
			}
		}
	}

	FM80MeshBuffer B;
	if (Kind != EM80StairsKind::FenceOnly)
	{
		BuildTreads(B);
	}
	auto Has = [](EM80StairsSide Sides, double S)
	{
		return Sides == EM80StairsSide::Both || (S < 0 ? Sides == EM80StairsSide::Left : Sides == EM80StairsSide::Right);
	};
	for (const double S : {-1.0, 1.0})
	{
		const bool bWall = Has(WallSides, S) && (Kind != EM80StairsKind::FenceOnly || WallHeightCm > 1.f);
		if (bWall)
		{
			BuildWall(B, S);
		}
		if (FenceKind != EM80FenceKind::None && Has(FenceSides, S))
		{
			BuildFence(B, S, bWall);
		}
	}
	if (B.NumTriangles() == 0)
	{
		return;
	}

	UE::Geometry::FDynamicMesh3 Dyn;
	B.ToDynamicMesh(Dyn);
	Mesh->SetMesh(MoveTemp(Dyn));
	const TCHAR* TreadName = TreadFinish == EM80TreadFinish::Setts ? TEXT("MI_M80_Basolato") : (TreadFinish == EM80TreadFinish::Lava ? TEXT("MI_M80_PietraLavica") : TEXT("MI_M80_Cemento"));
	const TCHAR* WallName = WallFinish == EM80StairsWallFinish::Stone ? TEXT("MI_M80_MuroConci") : (WallFinish == EM80StairsWallFinish::Concrete ? TEXT("MI_M80_Cemento") : TEXT("MI_M80_PietraLavica"));
	Mesh->ConfigureMaterialSet({M80St::Pick(LavaMaterial, TEXT("MI_M80_PietraLavica")), M80St::Pick(TreadMaterial, TreadName), M80St::Pick(WallMaterial, WallName),
		M80St::Pick(IronMaterial, TEXT("MI_M80_Ferro")), M80St::Pick(WoodMaterial, TEXT("MI_M80_Legno")), M80St::Pick(CaneMaterial, TEXT("MI_M80_Canne"))});
	Mesh->SetComplexAsSimpleCollisionEnabled(bCollision, true);
	Mesh->SetCollisionProfileName(bCollision ? TEXT("BlockAll") : TEXT("NoCollision"));
}
