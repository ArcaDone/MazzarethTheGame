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

/** Cuts [A, B] into pieces no longer than Step. */
TArray<double> Cuts(double A, double B, double Step = Piece)
{
	TArray<double> Out;
	const int32 N = FMath::Max(1, FMath::CeilToInt((B - A) / Step));
	for (int32 i = 0; i <= N; ++i)
	{
		Out.Add(A + (B - A) * i / N);
	}
	return Out;
}

/** Smooth deterministic noise in about [-1, 1]. */
double Noise(double X, double Y, int32 Seed)
{
	return FMath::PerlinNoise2D(FVector2D(X + Seed * 17.31, Y - Seed * 9.17)) * 1.4;
}

/**
 * Grid surface P[row][col] with smooth normals, each pointing away from the row's Inside point, so the
 * same code shades convex stones, bulging walls and uneven paving.
 */
void Loft(FM80MeshBuffer& B, int32 Slot, const TArray<TArray<FVector3d>>& P, const TArray<TArray<FVector2f>>& UV, const TArray<FVector3d>& Inside)
{
	const int32 R = P.Num();
	if (R < 2 || P[0].Num() < 2)
	{
		return;
	}
	const int32 C = P[0].Num();
	TArray<TArray<FVector3f>> N;
	N.SetNum(R);
	for (int32 i = 0; i < R; ++i)
	{
		N[i].SetNum(C);
		for (int32 j = 0; j < C; ++j)
		{
			const FVector3d Du = P[i][FMath::Min(j + 1, C - 1)] - P[i][FMath::Max(j - 1, 0)];
			const FVector3d Dv = P[FMath::Min(i + 1, R - 1)][j] - P[FMath::Max(i - 1, 0)][j];
			FVector3d Nn = FVector3d::CrossProduct(Du, Dv).GetSafeNormal();
			if (FVector3d::DotProduct(Nn, P[i][j] - Inside[i]) < 0)
			{
				Nn = -Nn;
			}
			N[i][j] = FVector3f(Nn);
		}
	}
	for (int32 i = 0; i + 1 < R; ++i)
	{
		for (int32 j = 0; j + 1 < C; ++j)
		{
			B.TriN(Slot, P[i][j], P[i][j + 1], P[i + 1][j + 1], UV[i][j], UV[i][j + 1], UV[i + 1][j + 1], N[i][j], N[i][j + 1], N[i + 1][j + 1]);
			B.TriN(Slot, P[i][j], P[i + 1][j + 1], P[i + 1][j], UV[i][j], UV[i + 1][j + 1], UV[i + 1][j], N[i][j], N[i + 1][j + 1], N[i + 1][j]);
		}
	}
}

/** Flat polygon (a cap) as a fan from its centre, facing Facing. */
void Cap(FM80MeshBuffer& B, int32 Slot, const TArray<FVector3d>& Ring, const FVector3d& Facing)
{
	if (Ring.Num() < 3)
	{
		return;
	}
	FVector3d C(0);
	for (const FVector3d& P : Ring)
	{
		C += P;
	}
	C /= Ring.Num();
	const FVector3f Nf(Facing.GetSafeNormal());
	const FVector3d U = FVector3d::CrossProduct(Facing, FMath::Abs(Facing.Z) > 0.9 ? FVector3d::UnitX() : FVector3d::UnitZ()).GetSafeNormal();
	const FVector3d V = FVector3d::CrossProduct(Facing.GetSafeNormal(), U);
	auto Uv = [&](const FVector3d& P) { return FVector2f(float(FVector3d::DotProduct(P, U) / 100.0), float(FVector3d::DotProduct(P, V) / 100.0)); };
	for (int32 k = 0; k < Ring.Num(); ++k)
	{
		const FVector3d& A = Ring[k];
		const FVector3d& Bq = Ring[(k + 1) % Ring.Num()];
		B.TriN(Slot, C, A, Bq, Uv(C), Uv(A), Uv(Bq), Nf, Nf, Nf);
	}
}

/** Closed 2D section with outward normals (counter-clockwise). */
struct FSection
{
	TArray<FVector2D> P, N;
};

/** Rectangle W x H with rounded corners of radius R (no perfectly sharp edge on worn iron, wood or stone). */
FSection RoundRect(double W, double H, double R, int32 Seg = 2)
{
	FSection S;
	R = FMath::Clamp(R, 0.05, FMath::Min(W, H) * 0.5 - 0.01);
	const FVector2D Centre[4] = {{W / 2 - R, H / 2 - R}, {-W / 2 + R, H / 2 - R}, {-W / 2 + R, -H / 2 + R}, {W / 2 - R, -H / 2 + R}};
	for (int32 c = 0; c < 4; ++c)
	{
		for (int32 k = 0; k <= Seg; ++k)
		{
			const double A = FMath::DegreesToRadians(90.0 * c + 90.0 * k / FMath::Max(1, Seg));
			const FVector2D Nn(FMath::Cos(A), FMath::Sin(A));
			S.P.Add(Centre[c] + Nn * R);
			S.N.Add(Nn);
		}
	}
	return S;
}

FSection Round(double Radius, int32 Sides)
{
	return RoundRect(Radius * 2, Radius * 2, Radius, FMath::Max(1, Sides / 4));
}

/** Rounds the corners of a polyline with short quadratic arcs (bent tubes). */
TArray<FVector3d> RoundCorners(const TArray<FVector3d>& In, double Radius, int32 Seg = 5)
{
	if (In.Num() < 3)
	{
		return In;
	}
	TArray<FVector3d> Out = {In[0]};
	for (int32 i = 1; i + 1 < In.Num(); ++i)
	{
		const FVector3d A = In[i - 1], C = In[i], D = In[i + 1];
		const double R = FMath::Min(Radius, 0.45 * FMath::Min((C - A).Size(), (D - C).Size()));
		const FVector3d P0 = C + (A - C).GetSafeNormal() * R, P2 = C + (D - C).GetSafeNormal() * R;
		if (FVector3d::DotProduct((C - A).GetSafeNormal(), (D - C).GetSafeNormal()) > 0.995 || R < 0.5)
		{
			Out.Add(C);
			continue;
		}
		for (int32 k = 0; k <= Seg; ++k)
		{
			const double T = double(k) / Seg;
			Out.Add(P0 * FMath::Square(1 - T) + C * (2 * T * (1 - T)) + P2 * FMath::Square(T));
		}
	}
	Out.Add(In.Last());
	return Out;
}

/**
 * Sweeps a section along a path, with smooth normals and capped ends. bUpright keeps the section's Y
 * vertical (rails, copings, planks); otherwise the frame is carried along the path (tubes, posts).
 */
void Sweep(FM80MeshBuffer& B, int32 Slot, const TArray<FVector3d>& Path, const FSection& S, bool bUpright, bool bCaps = true, float VOffset = 0.f)
{
	const int32 N = Path.Num(), M = S.P.Num();
	if (N < 2 || M < 3)
	{
		return;
	}
	TArray<FVector3d> T, U, V;
	for (int32 i = 0; i < N; ++i)
	{
		FVector3d Ti = (Path[FMath::Min(i + 1, N - 1)] - Path[FMath::Max(i - 1, 0)]).GetSafeNormal();
		if (Ti.IsNearlyZero())
		{
			Ti = i ? T.Last() : FVector3d::UnitX();
		}
		FVector3d Ui;
		if (bUpright && FMath::Abs(Ti.Z) < 0.95)
		{
			Ui = FVector3d::CrossProduct(FVector3d::UnitZ(), Ti).GetSafeNormal();
		}
		else if (i == 0)
		{
			Ui = FVector3d::CrossProduct(Ti, FMath::Abs(Ti.Z) > 0.9 ? FVector3d::UnitX() : FVector3d::UnitZ()).GetSafeNormal();
		}
		else
		{
			Ui = (U.Last() - Ti * FVector3d::DotProduct(U.Last(), Ti)).GetSafeNormal();
		}
		T.Add(Ti);
		U.Add(Ui);
		V.Add(FVector3d::CrossProduct(Ti, Ui).GetSafeNormal() * (bUpright && FVector3d::CrossProduct(Ti, Ui).Z < 0 ? -1.0 : 1.0));
	}
	TArray<double> Along = {0.0};
	for (int32 i = 1; i < N; ++i)
	{
		Along.Add(Along.Last() + (Path[i] - Path[i - 1]).Size());
	}
	TArray<double> Around = {0.0};
	for (int32 k = 1; k <= M; ++k)
	{
		Around.Add(Around.Last() + (S.P[k % M] - S.P[k - 1]).Size());
	}
	auto At = [&](int32 i, int32 k) { return Path[i] + U[i] * S.P[k % M].X + V[i] * S.P[k % M].Y; };
	auto Nrm = [&](int32 i, int32 k) { return FVector3f(U[i] * S.N[k % M].X + V[i] * S.N[k % M].Y); };
	for (int32 i = 0; i + 1 < N; ++i)
	{
		for (int32 k = 0; k < M; ++k)
		{
			const FVector2f A0(float(Around[k] / 100), float(Along[i] / 100) + VOffset), A1(float(Around[k + 1] / 100), float(Along[i] / 100) + VOffset);
			const FVector2f B0(float(Around[k] / 100), float(Along[i + 1] / 100) + VOffset), B1(float(Around[k + 1] / 100), float(Along[i + 1] / 100) + VOffset);
			B.TriN(Slot, At(i, k), At(i, k + 1), At(i + 1, k + 1), A0, A1, B1, Nrm(i, k), Nrm(i, k + 1), Nrm(i + 1, k + 1));
			B.TriN(Slot, At(i, k), At(i + 1, k + 1), At(i + 1, k), A0, B1, B0, Nrm(i, k), Nrm(i + 1, k + 1), Nrm(i + 1, k));
		}
	}
	if (bCaps)
	{
		TArray<FVector3d> R0, R1;
		for (int32 k = 0; k < M; ++k)
		{
			R0.Add(At(0, k));
			R1.Add(At(N - 1, k));
		}
		Cap(B, Slot, R0, -T[0]);
		Cap(B, Slot, R1, T[N - 1]);
	}
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
	const double Use = FMath::Clamp(double(Wear), 0.0, 1.0);
	const int32 Seed = int32(GetTypeHash(GetName()) % 9973);
	const FVector3d Up(0, 0, 1);
	auto Local = [&T](const FVector& V) { return FVector3d(T.InverseTransformVectorNoScale(V)); };
	auto Ground = [this](double D, double Lat) { return GroundAt(Path->GetComponentTransform().TransformPosition(PointAt(D, Lat, 0.0))) - 25.0; };
	auto Soffit = [&](double D) { return EdgeLineZ(D) - Rise - double(SlabCm); };
	// Feet wear the steps hollow in the middle of the flight.
	auto Dish = [&](double Lat) { const double X = Lat / HalfW; return Use * 1.6 * FMath::Max(0.0, 1.0 - X * X); };
	auto TreadZ = [](const FTread& S, double D) { return FMath::Lerp(S.Z0, S.Z1, FMath::Clamp((D - S.D0) / FMath::Max(S.D1 - S.D0, 1e-3), 0.0, 1.0)); };
	// The paving between the stone edges: a little lower and uneven.
	auto InfillZ = [&](const FTread& S, double D, double Lat)
	{
		return TreadZ(S, D) - 0.6 - Dish(Lat) * 0.6 + Use * 0.45 * M80St::Noise(D / 41.0, Lat / 41.0, Seed + 5);
	};
	// Side faces under a stretch of tread: a band of lava (the ends of the step stones), then the wall
	// finish down to the ground, or to the soffit of a slab stair. Top(D, Side) gives the upper edge.
	auto Sides = [&](double D0, double D1, TFunctionRef<double(double, double)> Top)
	{
		const TArray<double> C = M80St::Cuts(D0, D1, 25.0);
		for (const double S : {-1.0, 1.0})
		{
			for (int32 i = 0; i + 1 < C.Num(); ++i)
			{
				const FVector3d Out = Local(RightAt((C[i] + C[i + 1]) * 0.5) * S);
				const double Z0 = Top(C[i], S), Z1 = Top(C[i + 1], S);
				const double Band = 12.0;
				const double B0 = bFillToGround ? FMath::Min(Ground(C[i], S * HalfW), Z0 - Band) : FMath::Min(Soffit(C[i]), Z0 - 2.0);
				const double B1 = bFillToGround ? FMath::Min(Ground(C[i + 1], S * HalfW), Z1 - Band) : FMath::Min(Soffit(C[i + 1]), Z1 - 2.0);
				const double M0 = FMath::Max(Z0 - Band, B0), M1 = FMath::Max(Z1 - Band, B1);
				B.QuadProjected(M80St::Lava, PointAt(C[i], S * HalfW, M0), PointAt(C[i + 1], S * HalfW, M1), PointAt(C[i + 1], S * HalfW, Z1), PointAt(C[i], S * HalfW, Z0), Out);
				B.QuadProjected(M80St::Wall, PointAt(C[i], S * HalfW, B0), PointAt(C[i + 1], S * HalfW, B1), PointAt(C[i + 1], S * HalfW, M1), PointAt(C[i], S * HalfW, M0), Out);
			}
		}
		if (!bFillToGround)
		{
			for (int32 i = 0; i + 1 < C.Num(); ++i)
			{
				B.QuadProjected(M80St::Wall, PointAt(C[i], -HalfW, Soffit(C[i])), PointAt(C[i], HalfW, Soffit(C[i])), PointAt(C[i + 1], HalfW, Soffit(C[i + 1])), PointAt(C[i + 1], -HalfW, Soffit(C[i + 1])), -Up);
			}
		}
	};
	// Uneven paving between D0 and D1.
	auto Infill = [&](const FTread& S, double D0, double D1)
	{
		if (D1 - D0 < 0.5)
		{
			return;
		}
		const TArray<double> Ds = M80St::Cuts(D0, D1, 15.0), Ls = M80St::Cuts(-HalfW, HalfW, 15.0);
		TArray<TArray<FVector3d>> P;
		TArray<TArray<FVector2f>> UV;
		TArray<FVector3d> In;
		for (const double D : Ds)
		{
			TArray<FVector3d>& Row = P.AddDefaulted_GetRef();
			TArray<FVector2f>& URow = UV.AddDefaulted_GetRef();
			for (const double L : Ls)
			{
				Row.Add(PointAt(D, L, InfillZ(S, D, L)));
				URow.Add(FVector2f(float(L / 100.0), float(D / 100.0)));
			}
			In.Add(PointAt(D, 0.0, TreadZ(S, D) - 200.0));
		}
		M80St::Loft(B, M80St::Tread, P, UV, In);
		Sides(D0, D1, [&](double D, double Side) { return InfillZ(S, D, Side * HalfW); });
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

	/**
	 * The stone edge of a step: a row of lava blocks 60-120 cm long across the stair, each with its own
	 * height and tilt, a rounded nose (rounder and lower where it is walked on), chips, and hairline
	 * joints. Edge = distance of the nose, Dir = +1 when the tread lies after it (stairs going up).
	 */
	auto EdgeStones = [&](int32 k, const FTread& S, double Edge, double Dir, double Band, double ZBelow)
	{
		FRandomStream Rnd(Seed * 131 + k * 7);
		TArray<FVector2D> Blocks;
		for (double L = -HalfW; L < HalfW - 1.0;)
		{
			double Len = Rnd.FRandRange(60.0, 120.0);
			if (HalfW - (L + Len) < 30.0)
			{
				Len = HalfW - L;
			}
			Blocks.Add(FVector2D(L, L + Len));
			L += Len;
		}
		const double Gap = 0.35;
		for (int32 b = 0; b < Blocks.Num(); ++b)
		{
			const double L0 = Blocks[b].X + (b ? Gap : 0.0), L1 = Blocks[b].Y - (b + 1 < Blocks.Num() ? Gap : 0.0);
			const double Lift = Rnd.FRandRange(-0.45, 0.45) * Use, Tilt = Rnd.FRandRange(-0.35, 0.35) * Use;
			const double R0 = Rnd.FRandRange(1.0, 2.2), Lean = Rnd.FRandRange(-0.4, 0.4);
			// Each stone shows its own piece of the texture, sometimes mirrored, so no two steps look alike.
			const float ShiftU = Rnd.FRandRange(0.f, 20.f), ShiftV = Rnd.FRandRange(0.f, 20.f), FlipU = Rnd.FRand() < 0.5f ? -1.f : 1.f;
			const double Mid = (L0 + L1) * 0.5;
			const TArray<double> Ls = M80St::Cuts(L0, L1, 8.0);
			TArray<TArray<FVector3d>> P;
			TArray<TArray<FVector2f>> UV;
			TArray<FVector3d> In;
			for (const double L : Ls)
			{
				auto TopAt = [&](double Sd)
				{
					return TreadZ(S, Edge + Dir * Sd) + Lift + Tilt * (L - Mid) / FMath::Max(L1 - L0, 1.0) - Dish(L) * (1.0 - 0.5 * Sd / FMath::Max(Band, 1.0))
						+ Use * 0.25 * M80St::Noise((Edge + Dir * Sd) / 13.0, L / 13.0, Seed + 1);
				};
				// Chips along the nose: deeper, rounder edge where the noise peaks.
				const double Chip = FMath::Max(0.0, M80St::Noise(Edge / 7.0 + k * 3.1, L / 9.0, Seed + 3) - (0.55 - 0.25 * Use)) * 6.0 * Use;
				const double R = R0 + Use * 2.2 * Dish(L) / 1.6 + Chip;
				const double Top = TopAt(0.0);
				TArray<FVector2D> Prof; // (distance into the tread, height)
				Prof.Add(FVector2D(Lean * 0.5, ZBelow - 1.0));
				Prof.Add(FVector2D(Lean * 0.25 + Use * 0.3 * M80St::Noise(Edge / 5.0, L / 5.0, Seed + 7), (ZBelow + Top - R) * 0.5));
				for (int32 a = 0; a <= 5; ++a)
				{
					const double Ang = PI - (PI * 0.5) * a / 5.0;
					Prof.Add(FVector2D(R + R * FMath::Cos(Ang), Top - R + R * FMath::Sin(Ang) - Chip * 0.25 * FMath::Sin(Ang * 2.0)));
				}
				Prof.Add(FVector2D(Band * 0.5, TopAt(Band * 0.5)));
				Prof.Add(FVector2D(Band - 0.7, TopAt(Band) - 0.1));
				Prof.Add(FVector2D(Band, TopAt(Band) - 0.9));
				Prof.Add(FVector2D(Band, ZBelow - 1.0));
				TArray<FVector3d>& Row = P.AddDefaulted_GetRef();
				TArray<FVector2f>& URow = UV.AddDefaulted_GetRef();
				double Run = 0.0;
				for (int32 j = 0; j < Prof.Num(); ++j)
				{
					Run += j ? (Prof[j] - Prof[j - 1]).Size() : 0.0;
					Row.Add(PointAt(Edge + Dir * Prof[j].X, L, Prof[j].Y));
					URow.Add(FVector2f(FlipU * float(L / 100.0) + ShiftU, float(Run / 100.0) + ShiftV));
				}
				In.Add(PointAt(Edge + Dir * Band * 0.5, L, (ZBelow + Top) * 0.5));
			}
			M80St::Loft(B, M80St::Lava, P, UV, In);
			// Block ends (seen in the joints and at the sides of the stair).
			M80St::Cap(B, M80St::Lava, P[0], Local(RightAt(Edge) * -1.0));
			M80St::Cap(B, M80St::Lava, P.Last(), Local(RightAt(Edge)));
		}
		// Bedding behind the joints, so they read as dark gaps.
		const double TopE = TreadZ(S, Edge);
		Across(M80St::Lava, Edge + Dir * 1.2, ZBelow - 1.0, TopE - 1.6, -Dir);
		B.QuadProjected(M80St::Lava, PointAt(Edge, -HalfW, TopE - 1.4), PointAt(Edge, HalfW, TopE - 1.4), PointAt(Edge + Dir * Band, HalfW, TopE - 1.4), PointAt(Edge + Dir * Band, -HalfW, TopE - 1.4), Up);
		// Sides below the stones.
		const double DA = FMath::Min(Edge, Edge + Dir * Band), DB = FMath::Max(Edge, Edge + Dir * Band);
		Sides(DA, DB, [&](double, double) { return ZBelow - 1.0; });
	};

	const bool bStones = Nose > 0.5 && StepCount > 0;
	for (int32 k = 0; k < Treads.Num(); ++k)
	{
		const FTread& S = Treads[k];
		if (!bStones)
		{
			Infill(S, S.D0, S.D1);
			if (StepCount > 0)
			{
				if (S.bEdgeAtStart)
				{
					Across(M80St::Lava, S.D0, k == 0 ? SurfaceStartZ : Treads[k - 1].Z1, S.Z0, -1.0);
				}
				else
				{
					Across(M80St::Lava, S.D1, k + 1 == Treads.Num() ? SurfaceEndZ : Treads[k + 1].Z0, S.Z1, 1.0);
				}
			}
			continue;
		}
		const double Band = FMath::Min(Nose, S.D1 - S.D0);
		if (S.bEdgeAtStart)
		{
			EdgeStones(k, S, S.D0, 1.0, Band, k == 0 ? SurfaceStartZ : Treads[k - 1].Z1);
			Infill(S, S.D0 + Band, S.D1);
		}
		else
		{
			EdgeStones(k, S, S.D1, -1.0, Band, k + 1 == Treads.Num() ? SurfaceEndZ : Treads[k + 1].Z0);
			Infill(S, S.D0, S.D1 - Band);
		}
	}
	// Ends: down to the ground, or to the soffit of a slab.
	if (Treads.Num())
	{
		const double Z0 = FMath::Min(Treads[0].bEdgeAtStart ? SurfaceStartZ : Treads[0].Z0, Treads[0].Z0);
		const double Z1 = FMath::Min(Treads.Last().bEdgeAtStart ? Treads.Last().Z1 : SurfaceEndZ, Treads.Last().Z1);
		Across(M80St::Wall, 0.0, bFillToGround ? FMath::Min(Ground(0.0, 0.0), Z0 - 1.0) : Soffit(0.0), Z0 - 0.6, -1.0);
		Across(M80St::Wall, Length, bFillToGround ? FMath::Min(Ground(Length, 0.0), Z1 - 1.0) : Soffit(Length), Z1 - 0.6, 1.0);
	}
}

void AM80Stairs::BuildWall(FM80MeshBuffer& B, double Side) const
{
	const FTransform& T = Path->GetComponentTransform();
	auto Local = [&T](const FVector& V) { return FVector3d(T.InverseTransformVectorNoScale(V)); };
	const double HalfW = FMath::Max(20.0, double(WidthCm)) * 0.5;
	const double Th = WallThicknessCm;
	const double Use = FMath::Clamp(double(Wear), 0.0, 1.0);
	const int32 Seed = int32(GetTypeHash(GetName()) % 9973) + int32(Side * 31);
	const double In = Side * HalfW, OutL = Side * (HalfW + Th), Centre = Side * (HalfW + Th * 0.5);
	const double Cop = bWallCoping ? 7.0 : 0.0, Over = 4.0;
	// Old masonry bulges and sags: the faces are pushed in and out by up to ~1.5 cm.
	const double Bulge = (WallFinish == EM80StairsWallFinish::Concrete ? 0.5 : 1.5) * Use;
	const TArray<double> C = M80St::Cuts(0.0, Length, 25.0);
	auto TopZ = [&](double D) { return EdgeLineZ(D) + WallHeightCm; };
	TArray<double> Bot, Tops;
	double Tallest = 0.0;
	for (const double D : C)
	{
		const double G = FMath::Min(GroundAt(T.TransformPosition(PointAt(D, In, 0.0))), GroundAt(T.TransformPosition(PointAt(D, OutL, 0.0))));
		Tops.Add(TopZ(D));
		Bot.Add(FMath::Min(G - 30.0, Tops.Last() - 20.0));
		Tallest = FMath::Max(Tallest, Tops.Last() - Bot.Last());
	}
	const int32 Rows = FMath::Clamp(FMath::CeilToInt(Tallest / 25.0), 2, 60);
	for (const double Face : {1.0, -1.0})
	{
		const double Lat = Face > 0 ? OutL : In;
		TArray<TArray<FVector3d>> P;
		TArray<TArray<FVector2f>> UV;
		TArray<FVector3d> Inside;
		for (int32 i = 0; i < C.Num(); ++i)
		{
			TArray<FVector3d>& Row = P.AddDefaulted_GetRef();
			TArray<FVector2f>& URow = UV.AddDefaulted_GetRef();
			for (int32 j = 0; j <= Rows; ++j)
			{
				const double Z = FMath::Lerp(Bot[i], Tops[i], double(j) / Rows);
				// No bulge at the top and bottom edges, so the coping and the ground still meet the wall.
				const double Edge = FMath::Min(1.0, FMath::Min(double(j), double(Rows - j)) / 1.5);
				const double Push = Bulge * Edge * M80St::Noise(C[i] / 60.0, Z / 60.0, Seed + int32(Face * 5));
				Row.Add(PointAt(C[i], Lat + Side * Face * Push, Z));
				URow.Add(FVector2f(float(C[i] / 100.0), float(-Z / 100.0)));
			}
			Inside.Add(PointAt(C[i], Centre, (Bot[i] + Tops[i]) * 0.5));
		}
		M80St::Loft(B, M80St::Wall, P, UV, Inside);
	}
	// Wall top (the mortar bed under the coping).
	for (int32 i = 0; i + 1 < C.Num(); ++i)
	{
		B.QuadProjected(M80St::Wall, PointAt(C[i], In, Tops[i]), PointAt(C[i], OutL, Tops[i]), PointAt(C[i + 1], OutL, Tops[i + 1]), PointAt(C[i + 1], In, Tops[i + 1]), FVector3d(0, 0, 1));
	}
	// End faces.
	for (const int32 End : {0, 1})
	{
		const double D = End ? Length : 0.0;
		const double Z = TopZ(D);
		const FVector3d Facing = Local(FVector(-RightAt(D).Y, RightAt(D).X, 0) * (End ? -1.0 : 1.0));
		const double Bo = End ? Bot.Last() : Bot[0];
		B.QuadProjected(M80St::Wall, PointAt(D, In, Bo), PointAt(D, OutL, Bo), PointAt(D, OutL, Z), PointAt(D, In, Z), Facing);
	}
	// Coping: separate lava slabs 50-100 cm long with rounded edges, each a little off level.
	if (Cop > 0)
	{
		FRandomStream Rnd(Seed);
		const M80St::FSection Slab = M80St::RoundRect(Th + Over * 2, Cop, 1.2 + 1.2 * Use, 2);
		for (double D0 = 0.0; D0 < Length - 1.0;)
		{
			double Len = Rnd.FRandRange(50.0, 100.0);
			if (Length - (D0 + Len) < 25.0)
			{
				Len = Length - D0;
			}
			const double Lift = Rnd.FRandRange(-0.4, 0.5) * Use, Twist = Rnd.FRandRange(-0.6, 0.6) * Use;
			TArray<FVector3d> Pts;
			for (const double D : M80St::Cuts(D0 + 0.3, D0 + Len - 0.3, 25.0))
			{
				Pts.Add(PointAt(D, Centre + Twist * (D - D0 - Len * 0.5) / Len, TopZ(D) + Cop * 0.5 + Lift));
			}
			M80St::Sweep(B, M80St::Lava, Pts, Slab, true, true, Rnd.FRandRange(0.f, 20.f));
			D0 += Len;
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
	const double Cop = bWallCoping ? 7.0 : 0.0;
	const double Use = FMath::Clamp(double(Wear), 0.0, 1.0);
	// Feet of the fence: on the wall's top, or on the steps; the rails follow the edge line.
	auto Base = [&](double D) { return bOnWall ? EdgeLineZ(D) + WallHeightCm + Cop : SurfaceZ(D); };
	auto Line = [&](double D) { return bOnWall ? Base(D) : EdgeLineZ(D); };
	auto P = [&](double D, double Z, double Off = 0.0) { return FVector3d(PointAt(D, Lat + Side * Off, Z)); };
	auto RailPts = [&](double D0, double D1, double Offset, double Off = 0.0)
	{
		TArray<FVector3d> Pts;
		for (const double D : M80St::Cuts(D0, D1, 25.0))
		{
			Pts.Add(P(D, Line(D) + Offset, Off));
		}
		return Pts;
	};
	const int32 Posts = FMath::Max(1, FMath::CeilToInt(Length / FMath::Max(50.f, PostSpacingCm)));
	auto PostD = [&](int32 i) { return FMath::Clamp(Length * i / Posts, 3.0, Length - 3.0); };
	FRandomStream Rnd(int32(GetTypeHash(GetName()) % 9973) + int32(Side * 7));

	switch (FenceKind)
	{
	case EM80FenceKind::WroughtIron:
	{
		// Forged: a half-round handrail, a flat lower bar, square posts and bars, slightly out of true.
		M80St::Sweep(B, M80St::Iron, RailPts(0.0, Length, H), M80St::RoundRect(5.0, 3.6, 1.5, 3), true);
		M80St::Sweep(B, M80St::Iron, RailPts(0.0, Length, 10.0), M80St::RoundRect(1.4, 4.0, 0.5, 1), true);
		const M80St::FSection PostS = M80St::RoundRect(4.0, 4.0, 0.7, 2), BarS = M80St::RoundRect(1.6, 1.6, 0.35, 1);
		for (int32 i = 0; i <= Posts; ++i)
		{
			const double D = PostD(i);
			M80St::Sweep(B, M80St::Iron, {P(D, Base(D) - 3.0), P(D, Line(D) + H - 1.0)}, PostS, false, true, Rnd.FRandRange(0.f, 20.f));
			M80St::Sweep(B, M80St::Iron, {P(D, Line(D) + H + 1.0), P(D, Line(D) + H + 4.5)}, M80St::Round(2.2, 8), false);
		}
		const int32 Bars = FMath::Max(1, FMath::FloorToInt(Length / 12.0));
		for (int32 i = 1; i < Bars; ++i)
		{
			const double D = Length * i / Bars;
			const double Bend = Rnd.FRandRange(-0.5, 0.5) * Use;
			M80St::Sweep(B, M80St::Iron, {P(D, Line(D) + 9.0), P(D + Bend, Line(D) + H * 0.5, Bend * 0.5), P(D, Line(D) + H - 1.0)}, BarS, false, true, Rnd.FRandRange(0.f, 20.f));
		}
		break;
	}
	case EM80FenceKind::IronTube:
	{
		// Bent tubes: an upside-down U in each bay, one continuous pipe with rounded bends.
		for (int32 i = 0; i < Posts; ++i)
		{
			const double DA = FMath::Min(PostD(i) + 12.0, PostD(i + 1) - 10.0), DB = FMath::Max(PostD(i + 1) - 12.0, DA + 10.0);
			TArray<FVector3d> Pts = {P(DA, Base(DA) - 4.0)};
			Pts.Append(RailPts(DA, DB, H));
			Pts.Add(P(DB, Base(DB) - 4.0));
			TArray<FVector3d> Bent = M80St::RoundCorners(Pts, 9.0);
			M80St::Sweep(B, M80St::Iron, Bent, M80St::Round(2.4, 12), false, true, Rnd.FRandRange(0.f, 20.f));
		}
		break;
	}
	case EM80FenceKind::Wood:
	{
		// Rough posts, each a little different and out of plumb; rails nailed on their outer face, sagging.
		TArray<double> PostSize;
		for (int32 i = 0; i <= Posts; ++i)
		{
			const double D = PostD(i), Sz = Rnd.FRandRange(9.0, 12.0);
			PostSize.Add(Sz);
			const FVector3d Lean = Local(RightAt(D) * Rnd.FRandRange(-1.5, 1.5) * Use) + FVector3d(Rnd.FRandRange(-1.5, 1.5) * Use, 0, 0);
			M80St::Sweep(B, M80St::Wood, {P(D, Base(D) - (bOnWall ? 0.0 : 20.0)), P(D, Line(D) + H + Rnd.FRandRange(3.0, 9.0)) + Lean},
				M80St::RoundRect(Sz, Sz * Rnd.FRandRange(0.85, 1.0), 1.0 + 1.5 * Use, 2), false, true, Rnd.FRandRange(0.f, 20.f));
		}
		for (int32 i = 0; i < Posts; ++i)
		{
			for (const double Z : {H - 6.0, H * 0.45})
			{
				const double Sag = Rnd.FRandRange(0.0, 2.0) * Use, Off = (PostSize[i] + PostSize[i + 1]) * 0.25 + 2.5;
				TArray<FVector3d> Pts = RailPts(PostD(i) - 4.0, PostD(i + 1) + 4.0, Z + Rnd.FRandRange(-1.5, 1.5), Off);
				for (int32 j = 0; j < Pts.Num(); ++j)
				{
					Pts[j].Z -= Sag * FMath::Sin(PI * j / FMath::Max(1, Pts.Num() - 1));
				}
				M80St::Sweep(B, M80St::Wood, Pts, M80St::RoundRect(4.5, Rnd.FRandRange(10.0, 13.0), 0.8 + Use, 2), true, true, Rnd.FRandRange(0.f, 20.f));
			}
		}
		break;
	}
	case EM80FenceKind::Cane:
	{
		// Reed fence: canes side by side, each its own thickness, height and lean, tied to two cross canes.
		for (int32 i = 0; i <= Posts; ++i)
		{
			const double D = PostD(i);
			M80St::Sweep(B, M80St::Wood, {P(D, Base(D) - 20.0), P(D, Line(D) + H - 5.0)}, M80St::RoundRect(7.0, 7.0, 1.5, 2), false, true, Rnd.FRandRange(0.f, 20.f));
		}
		const int32 Canes = FMath::Max(1, FMath::FloorToInt(Length / 4.4));
		for (int32 i = 0; i <= Canes; ++i)
		{
			const double D = FMath::Clamp(Length * i / Canes + Rnd.FRandRange(-0.8, 0.8), 0.0, Length);
			const FVector3d Lean = Local(RightAt(D) * Rnd.FRandRange(-1.2, 1.2)) + FVector3d(Rnd.FRandRange(-1.0, 1.0), 0, 0);
			M80St::Sweep(B, M80St::Cane, {P(D, Base(D) - 3.0, 5.0), P(D, Line(D) + H + Rnd.FRandRange(-8.0, 8.0), 5.0) + Lean},
				M80St::Round(Rnd.FRandRange(1.4, 2.2), 6), false, true, float(Rnd.FRand()));
		}
		for (const double Z : {H * 0.3, H * 0.8})
		{
			M80St::Sweep(B, M80St::Cane, RailPts(0.0, Length, Z, 8.5), M80St::Round(1.2, 6), false);
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
