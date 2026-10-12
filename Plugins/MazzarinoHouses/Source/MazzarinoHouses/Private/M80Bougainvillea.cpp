#include "M80Bougainvillea.h"
#include "M80MeshBuffer.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/SplineComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "Engine/World.h"
#include "Materials/Material.h"
#include "MaterialDomain.h"

namespace M80Bgv
{
// Material slots of the plant's mesh.
constexpr int32 SlotBark = 0;
constexpr int32 SlotLeaf = 1;
constexpr int32 SlotBract = 2;
constexpr int32 SlotFlower = 3;

UMaterialInterface* Pick(UMaterialInterface* Override, const FString& Name)
{
	if (Override)
	{
		return Override;
	}
	UMaterialInterface* M = LoadObject<UMaterialInterface>(nullptr, *FString::Printf(TEXT("/Game/Mazzarino80/Vegetazione/Bouganvillea/%s.%s"), *Name, *Name), nullptr, LOAD_NoWarn);
	return M ? M : UMaterial::GetDefaultMaterial(MD_Surface);
}

FVector AnyPerp(const FVector& D)
{
	return FVector::CrossProduct(D, FMath::Abs(D.Z) > 0.9 ? FVector::XAxisVector : FVector::ZAxisVector).GetSafeNormal();
}

/** A grown stem or branch, in world space. Wall is the normal of the surface it lies on, zero where it hangs free. */
struct FBranch
{
	TArray<FVector> P;
	TArray<double> R;
	TArray<FVector> Wall;
	TArray<double> Dist;   // distance from the branch start
	int32 Level = 0;
	double Sway = 0;       // how much the root of the branch moves in the wind (0 at the trunk)

	void Add(const FVector& Q, double Radius, const FVector& N)
	{
		Dist.Add(P.Num() ? Dist.Last() + FVector::Dist(P.Last(), Q) : 0.0);
		P.Add(Q);
		R.Add(Radius);
		Wall.Add(N);
	}
	double Length() const { return Dist.Num() ? Dist.Last() : 0.0; }
	FVector Tangent(int32 i) const
	{
		return (P[FMath::Min(i + 1, P.Num() - 1)] - P[FMath::Max(i - 1, 0)]).GetSafeNormal();
	}
	/** Index of the point at distance D. */
	int32 At(double D) const
	{
		int32 i = 0;
		while (i + 1 < Dist.Num() && Dist[i + 1] < D)
		{
			++i;
		}
		return i;
	}
};

struct FGrower
{
	const AM80Bougainvillea& Plant;
	UWorld* World;
	FRandomStream& Rng;
	FCollisionQueryParams Params;
	TArray<FBranch> Branches;

	FGrower(const AM80Bougainvillea& InPlant, UWorld* InWorld, FRandomStream& InRng)
		: Plant(InPlant), World(InWorld), Rng(InRng), Params(SCENE_QUERY_STAT(M80Bougainvillea), false, &InPlant)
	{
	}

	bool Trace(const FVector& A, const FVector& B, FHitResult& Out) const
	{
		return World && World->LineTraceSingleByChannel(Out, A, B, ECC_Visibility, Params);
	}

	/** Nearest surface around P within Reach, looking sideways (walls, poles) and along Hint. */
	bool FindSurface(const FVector& P, const FVector& Hint, double Reach, FHitResult& Out) const
	{
		bool bAny = false;
		double Best = Reach * 2;
		TArray<FVector, TInlineAllocator<10>> Dirs;
		if (!Hint.IsNearlyZero())
		{
			Dirs.Add(Hint.GetSafeNormal());
		}
		for (int32 k = 0; k < 8; ++k)
		{
			Dirs.Add(FVector(FMath::Cos(k * PI / 4), FMath::Sin(k * PI / 4), 0));
		}
		for (const FVector& D : Dirs)
		{
			FHitResult H;
			if (Trace(P, P + D * Reach, H) && H.Distance < Best)
			{
				Best = H.Distance;
				Out = H;
				bAny = true;
			}
		}
		return bAny;
	}

	/** Grows a branch from P along Dir and, below the last level, the branches it bears. Returns its index. */
	int32 Grow(FVector P, FVector Dir, double R0, double Length, int32 Level, FVector Wall, double Sway)
	{
		const double Step = Level <= 1 ? 6.0 : 4.5;
		const int32 N = FMath::Max(2, FMath::CeilToInt(Length / Step));
		const double REnd = FMath::Max(0.2, R0 * 0.25);
		FBranch B;
		B.Level = Level;
		B.Sway = Sway;
		B.Add(P, R0, Wall);
		Dir = Dir.GetSafeNormal();
		for (int32 i = 1; i <= N; ++i)
		{
			const double T = double(i) / N;
			const double R = FMath::Lerp(R0, REnd, T);
			// Weight bends the branch more and more along it; growth wanders a little
			// (more where nothing holds them up).
			const double Fall = Wall.IsZero() ? 1.5 : 0.6;
			Dir += FVector(0, 0, -1) * Plant.Droop * 0.16 * (0.25 + T) * Fall + Rng.GetUnitVector() * Plant.Wander * 0.2;
			if (!Wall.IsZero())
			{
				Dir -= Wall * FVector::DotProduct(Dir, Wall) * 0.7;   // keep along the surface it lies on
			}
			Dir = Dir.GetSafeNormal();
			FVector Q = P + Dir * Step;
			FHitResult H;
			if (Trace(P, Q + Dir * (R + Plant.WallGap), H))
			{
				// Something in the way: lie on it and slide along it.
				Wall = H.ImpactNormal;
				Q = H.ImpactPoint + Wall * (R + Plant.WallGap);
				Dir = FVector::VectorPlaneProject(Dir, Wall).GetSafeNormal();
				if (Dir.IsNearlyZero())
				{
					Dir = AnyPerp(Wall);
				}
			}
			else if (!Wall.IsZero() && Plant.bClimbing)
			{
				// Hold on to the surface behind; past an edge there is none and the branch falls free.
				const double Reach = FMath::Max(Step * 2.0, R * 2 + Plant.WallGap + 6.0);
				if (Trace(Q + Wall * 2.0, Q - Wall * Reach, H))
				{
					Wall = H.ImpactNormal;
					Q = H.ImpactPoint + Wall * (R + Plant.WallGap);
				}
				else
				{
					Wall = FVector::ZeroVector;
				}
			}
			else if (!Wall.IsZero())
			{
				Wall = FVector::ZeroVector;   // not climbing: it only rested on the surface
			}
			else if (Plant.bClimbing && i % 3 == 0)
			{
				// Free: reach for a support nearby.
				FHitResult S;
				if (FindSurface(Q, -FVector::ZAxisVector, Plant.ClimbReach * 0.5, S))
				{
					Dir = (Dir + (S.ImpactPoint - Q).GetSafeNormal() * 0.6).GetSafeNormal();
				}
			}
			P = Q;
			B.Add(P, R, Wall);
		}
		const int32 Index = Branches.Add(MoveTemp(B));
		if (Level < Plant.BranchLevels)
		{
			// Twigs on the branches, fewer on the twigs (they would only add weight).
			Children(Index, 0.12, 0.95, Level == 1 ? 1.5 : 0.7);
		}
		return Index;
	}

	/** Side branches along branch Index between fractions From and To of its length. */
	void Children(int32 Index, double From, double To, double DensityScale)
	{
		const FBranch& Parent = Branches[Index];
		const double Length = Parent.Length();
		const int32 Level = Parent.Level + 1;
		const double ParentSway = Parent.Sway;
		const int32 Count = FMath::RoundToInt(Length / 100.0 * (To - From) * Plant.BranchesPerMetre * DensityScale * Rng.FRandRange(0.8f, 1.2f));
		struct FSeed { FVector P, Dir, Wall; double R, Length, T; };
		TArray<FSeed> Seeds;
		for (int32 c = 0; c < Count; ++c)
		{
			const double T = Rng.FRandRange(float(From), float(To));
			const int32 i = Parent.At(T * Length);
			const FVector Tan = Parent.Tangent(i);
			const FVector Wall = Parent.Wall[i];
			// On a surface the branch opens along it, a little outwards; free it opens all around.
			const FVector Side = Wall.IsZero()
				? AnyPerp(Tan).RotateAngleAxis(Rng.FRandRange(0.f, 360.f), Tan)
				: FVector::CrossProduct(Wall, Tan).GetSafeNormal() * (Rng.FRand() < 0.5f ? -1.0 : 1.0);
			const double A = FMath::DegreesToRadians(Plant.BranchAngle + Rng.FRandRange(-15.f, 15.f));
			FSeed S;
			S.Dir = (Tan * FMath::Cos(A) + Side * FMath::Sin(A) + Wall * 0.2).GetSafeNormal();
			S.P = Parent.P[i];
			S.Wall = Wall;
			S.R = FMath::Max(0.2, Parent.R[i] * 0.6);
			S.Length = (Level == 1 ? Plant.BranchLength * Rng.FRandRange(0.6f, 1.3f) : Length * Rng.FRandRange(0.3f, 0.55f)) * (1.0 - 0.35 * T);
			S.T = T;
			Seeds.Add(S);
		}
		for (const FSeed& S : Seeds)
		{
			Grow(S.P, S.Dir, S.R, S.Length, Level, S.Wall, FMath::Min(1.0, ParentSway + 0.25 + S.T * 0.2));
		}
	}
};

/** Tube with a radius per point, smooth normals and bark UVs at 20 cm per unit. */
void Wood(FM80MeshBuffer& M, const FBranch& B, const FTransform& ToLocal)
{
	const int32 N = B.P.Num();
	if (N < 2)
	{
		return;
	}
	const int32 Sides = B.Level == 0 ? 8 : (B.Level == 1 ? 6 : (B.Level == 2 ? 4 : 3));
	TArray<FVector3d> P, U, V;
	FVector3d Frame = AnyPerp(B.Tangent(0));
	for (int32 i = 0; i < N; ++i)
	{
		const FVector3d T = B.Tangent(i);
		Frame = FVector3d::VectorPlaneProject(Frame, T).GetSafeNormal();
		if (Frame.IsNearlyZero())
		{
			Frame = AnyPerp(T);
		}
		P.Add(B.P[i]);
		U.Add(Frame);
		V.Add(FVector3d::CrossProduct(T, Frame));
	}
	const double Tile = 20.0;
	for (int32 i = 0; i + 1 < N; ++i)
	{
		const float V0 = float(B.Dist[i] / Tile), V1 = float(B.Dist[i + 1] / Tile);
		const float Around0 = float(2 * PI * B.R[i] / Tile), Around1 = float(2 * PI * B.R[i + 1] / Tile);
		M.FacadeMask = float(FMath::Min(1.0, B.Sway + 0.3 * B.Dist[i] / FMath::Max(1.0, B.Length())));
		for (int32 k = 0; k < Sides; ++k)
		{
			const double A0 = 2 * PI * k / Sides, A1 = 2 * PI * (k + 1) / Sides;
			const FVector3d N00 = U[i] * FMath::Cos(A0) + V[i] * FMath::Sin(A0), N01 = U[i] * FMath::Cos(A1) + V[i] * FMath::Sin(A1);
			const FVector3d N10 = U[i + 1] * FMath::Cos(A0) + V[i + 1] * FMath::Sin(A0), N11 = U[i + 1] * FMath::Cos(A1) + V[i + 1] * FMath::Sin(A1);
			const FVector3d A = ToLocal.TransformPosition(P[i] + N00 * B.R[i]), Bv = ToLocal.TransformPosition(P[i] + N01 * B.R[i]);
			const FVector3d C = ToLocal.TransformPosition(P[i + 1] + N11 * B.R[i + 1]), D = ToLocal.TransformPosition(P[i + 1] + N10 * B.R[i + 1]);
			const FVector3f n00(ToLocal.TransformVectorNoScale(N00)), n01(ToLocal.TransformVectorNoScale(N01));
			const FVector3f n10(ToLocal.TransformVectorNoScale(N10)), n11(ToLocal.TransformVectorNoScale(N11));
			const float u0 = float(k) / Sides, u1 = float(k + 1) / Sides;
			M.TriN(SlotBark, A, Bv, C, {u0 * Around0, V0}, {u1 * Around0, V0}, {u1 * Around1, V1}, n00, n01, n11);
			M.TriN(SlotBark, A, C, D, {u0 * Around0, V0}, {u1 * Around1, V1}, {u0 * Around1, V1}, n00, n11, n10);
		}
	}
}

/**
 * A card folded along its midrib: Base is where the stalk joins, Dir points to the tip, Normal is the face. The card
 * shows the atlas cell UV0-UV1 with the stalk at the bottom (V max) and the tip at the top (V min).
 */
void Card(FM80MeshBuffer& M, int32 Slot, const FTransform& ToLocal, const FVector& Base, const FVector& Dir, const FVector& Normal,
	const FVector& Shade, double Len, double Wid, double Fold, const FVector2f& UV0, const FVector2f& UV1)
{
	const FVector X = FVector::CrossProduct(Normal, Dir).GetSafeNormal() * (Wid * 0.5);
	const FVector Up = Normal * Fold;
	const FVector Tip = Base + Dir * Len - Normal * (Len * 0.1);
	const FVector3d B = ToLocal.TransformPosition(Base), T = ToLocal.TransformPosition(Tip);
	const FVector3d BL = ToLocal.TransformPosition(Base - X + Up), BR = ToLocal.TransformPosition(Base + X + Up);
	const FVector3d TL = ToLocal.TransformPosition(Tip - X + Up), TR = ToLocal.TransformPosition(Tip + X + Up);
	const FVector3f n(ToLocal.TransformVectorNoScale(Shade));
	if (Fold <= 0.0)
	{
		// Flat: one quad.
		M.TriN(Slot, BL, TL, TR, {UV0.X, UV1.Y}, {UV0.X, UV0.Y}, {UV1.X, UV0.Y}, n, n, n);
		M.TriN(Slot, BL, TR, BR, {UV0.X, UV1.Y}, {UV1.X, UV0.Y}, {UV1.X, UV1.Y}, n, n, n);
		return;
	}
	const float UC = (UV0.X + UV1.X) * 0.5f;
	M.TriN(Slot, B, T, TL, {UC, UV1.Y}, {UC, UV0.Y}, {UV0.X, UV0.Y}, n, n, n);
	M.TriN(Slot, B, TL, BL, {UC, UV1.Y}, {UV0.X, UV0.Y}, {UV0.X, UV1.Y}, n, n, n);
	M.TriN(Slot, B, BR, TR, {UC, UV1.Y}, {UV1.X, UV1.Y}, {UV1.X, UV0.Y}, n, n, n);
	M.TriN(Slot, B, TR, T, {UC, UV1.Y}, {UV1.X, UV0.Y}, {UC, UV0.Y}, n, n, n);
}

/** One of the four cells of a 2x2 atlas, inset to its leaf or bract; the last cell (the yellowed leaf, the palest bract) is rarer. */
void Cell(FRandomStream& Rng, FVector2f& UV0, FVector2f& UV1)
{
	const float r = Rng.FRand();
	const int32 c = r < 0.32f ? 0 : (r < 0.62f ? 1 : (r < 0.9f ? 2 : 3));
	const float u = (c % 2) * 0.5f, v = (c / 2) * 0.5f;
	UV0 = FVector2f(u + 0.04f, v + 0.01f);
	UV1 = FVector2f(u + 0.46f, v + 0.49f);
}
}

AM80Bougainvillea::AM80Bougainvillea()
{
	PrimaryActorTick.bCanEverTick = false;
	Stem = CreateDefaultSubobject<USplineComponent>(TEXT("Stem"));
	SetRootComponent(Stem);
	Stem->bInputSplinePointsToConstructionScript = true;
	Stem->SetUnselectedSplineSegmentColor(FLinearColor(0.45f, 0.8f, 0.3f));
	Stem->SetSplinePoints({FVector(0, 0, 0), FVector(10, 0, 150), FVector(30, 0, 280)}, ESplineCoordinateSpace::Local);
	Mesh = CreateDefaultSubobject<UDynamicMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Stem);
	Mesh->SetMobility(EComponentMobility::Static);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

void AM80Bougainvillea::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	Rebuild();
}

void AM80Bougainvillea::Rebuild()
{
	using namespace M80Bgv;
	FRandomStream Rng(Seed);
	FGrower G(*this, GetWorld(), Rng);
	const double StemLength = Stem->GetSplineLength();
	FM80MeshBuffer M;
	const FTransform ToLocal = Mesh->GetComponentTransform().Inverse();

	if (Stem->GetNumberOfSplinePoints() >= 2 && StemLength > 10.0)
	{
		// The main stem follows the spline as drawn; it only learns which surface it lies on.
		FBranch S;
		const int32 N = FMath::Max(2, FMath::CeilToInt(StemLength / 6.0));
		FVector Wall = FVector::ZeroVector;
		for (int32 i = 0; i <= N; ++i)
		{
			const double D = StemLength * i / N;
			const FVector P = Stem->GetLocationAtDistanceAlongSpline(D, ESplineCoordinateSpace::World);
			if (i % 4 == 0)
			{
				FHitResult H;
				Wall = G.FindSurface(P, -Wall, ClimbReach, H) ? FVector(H.ImpactNormal) : FVector::ZeroVector;
			}
			S.Add(P, FMath::Lerp(double(TrunkRadius), TrunkRadius * 0.35, FMath::Pow(double(i) / N, 0.8)), Wall);
		}
		S.Level = 0;
		const int32 Root = G.Branches.Add(MoveTemp(S));
		G.Children(Root, BareTrunk, 1.0, 1.0);
		// The stem goes on past the end of the spline as a branch.
		const FBranch& R = G.Branches[Root];
		const int32 Last = R.P.Num() - 1;
		const FVector TipP = R.P[Last], TipDir = R.Tangent(Last), TipWall = R.Wall[Last];
		const double TipR = R.R[Last];
		G.Grow(TipP, TipDir, TipR, BranchLength * 0.8, 1, TipWall, 0.3);
	}

	// Centre of the plant: free leaves and flowers face away from it.
	FVector Centre = FVector::ZeroVector;
	int32 Count = 0;
	for (const FBranch& B : G.Branches)
	{
		for (const FVector& P : B.P)
		{
			Centre += P;
			++Count;
		}
	}
	Centre = Count ? Centre / Count : GetActorLocation();

	int32 Leaves = 0, Flowers = 0;
	for (const FBranch& B : G.Branches)
	{
		Wood(M, B, ToLocal);
		const double Length = B.Length();
		const double Start = B.Level == 0 ? Length * BareTrunk : 0.0;
		const double Density = B.Level == 0 ? 0.4 : 1.0;
		auto Sway = [&B, Length](double D) { return float(FMath::Min(1.0, B.Sway + 0.3 * D / FMath::Max(1.0, Length) + 0.1)); };
		auto Outward = [&Centre](const FVector& P, const FVector& Wall)
		{
			return Wall.IsZero() ? ((P - Centre).GetSafeNormal() * 0.6 + FVector::ZAxisVector * 0.5).GetSafeNormal() : Wall;
		};

		// Leaves, alternating along the branch, held out on either side and facing the light.
		if (LeafAmount > 0)
		{
			const double Spacing = 100.0 / (36.0 * LeafAmount * Density);
			double Side = 1.0;
			for (double D = Start + Rng.FRandRange(0.f, float(Spacing)); D < Length; D += Spacing * Rng.FRandRange(0.6f, 1.4f))
			for (int32 Node = Rng.RandRange(1, 3); Node > 0; --Node)
			{
				const int32 i = B.At(D);
				const FVector Tan = B.Tangent(i);
				const FVector Out = Outward(B.P[i], B.Wall[i]);
				const FVector Face = (Out + Rng.GetUnitVector() * 0.45).GetSafeNormal();
				FVector Across = FVector::CrossProduct(Face, Tan).GetSafeNormal().RotateAngleAxis(Rng.FRandRange(-50.f, 50.f), Tan) * Side;
				if (Across.IsNearlyZero())
				{
					Across = AnyPerp(Tan);
				}
				Side = -Side;
				FVector Dir = (Tan * Rng.FRandRange(0.2f, 0.7f) + Across + Rng.GetUnitVector() * 0.2).GetSafeNormal();
				Dir = (FVector::VectorPlaneProject(Dir, Face).GetSafeNormal() - FVector::ZAxisVector * 0.25).GetSafeNormal();
				const double Len = LeafSize * Rng.FRandRange(0.7f, 1.25f) * (B.Level == 0 ? 1.1 : 1.0);
				FVector2f UV0, UV1;
				Cell(Rng, UV0, UV1);
				M.FacadeMask = Sway(D);
				M.ElementRandom = Rng.FRand();
				Card(M, SlotLeaf, ToLocal, B.P[i] + Across * B.R[i], Dir, Face, (Face + Out).GetSafeNormal(), Len, Len * 0.88, Len * 0.12, UV0, UV1);
				++Leaves;
			}
		}

		// Flowers: bunches of bract triads, more towards the tips, always one at the tip of a branch.
		if (FlowerAmount > 0 && B.Level > 0)
		{
			const double Spacing = 100.0 / (10.0 * FlowerAmount);
			auto Bunch = [&](double D, int32 Triads)
			{
				const int32 i = B.At(D);
				const FVector Out = Outward(B.P[i], B.Wall[i]);
				const FVector Axis0 = (Out + FVector::ZAxisVector * 0.3 + Rng.GetUnitVector() * 0.35).GetSafeNormal();
				for (int32 t = 0; t < Triads; ++t)
				{
					const FVector Axis = (Axis0 + Rng.GetUnitVector() * 0.45).GetSafeNormal();
					const FVector X = AnyPerp(Axis), Y = FVector::CrossProduct(Axis, X);
					const FVector C = B.P[i] + (Rng.GetUnitVector() * 0.6 + Axis * 0.5) * BractSize * 1.3;
					const double Phase = Rng.FRandRange(0.f, 2 * PI);
					const double Len = BractSize * Rng.FRandRange(0.8f, 1.2f);
					M.FacadeMask = Sway(D) + 0.1f;
					M.ElementRandom = Rng.FRand();
					for (int32 k = 0; k < 3; ++k)
					{
						const double A = Phase + k * 2 * PI / 3 + Rng.FRandRange(-0.2f, 0.2f);
						const FVector Radial = X * FMath::Cos(A) + Y * FMath::Sin(A);
						const FVector Dir = (Axis * 0.6 + Radial * 0.8).GetSafeNormal();
						FVector Face = FVector::CrossProduct(Dir, FVector::CrossProduct(Axis, Radial)).GetSafeNormal();
						if (FVector::DotProduct(Face, Axis) < 0)
						{
							Face = -Face;
						}
						FVector2f UV0, UV1;
						Cell(Rng, UV0, UV1);
						Card(M, SlotBract, ToLocal, C + Radial * 0.3, Dir, Face, (Face + Out).GetSafeNormal(), Len, Len * 0.88, 0.0, UV0, UV1);
					}
					// The small white flowers in the middle.
					Card(M, SlotFlower, ToLocal, C, Axis, Rng.FRand() < 0.5f ? X : Y, Out, Len * 0.75, Len * 0.75, 0.0, FVector2f(0.32f, 0.41f), FVector2f(0.77f, 0.86f));
					++Flowers;
				}
			};
			for (double D = Rng.FRandRange(0.f, float(Spacing)); D < Length * 0.92; D += Spacing * Rng.FRandRange(0.6f, 1.4f))
			{
				const double T = D / FMath::Max(1.0, Length);
				if (Rng.FRand() < (1.0 - FlowersAtTips) + FlowersAtTips * T * T)
				{
					Bunch(D, FMath::Max(1, FMath::RoundToInt(Rng.FRandRange(1.f, 3.f) * FMath::Min(1.0f, FlowerAmount))));
				}
			}
			Bunch(Length, FMath::RoundToInt(Rng.FRandRange(2.f, 4.f) * FMath::Min(1.5f, FlowerAmount)));
		}
	}

	UE::Geometry::FDynamicMesh3 Dyn;
	M.ToDynamicMesh(Dyn);
	Mesh->SetMesh(MoveTemp(Dyn));
	static const TCHAR* ColourNames[] = {TEXT("Magenta"), TEXT("Viola"), TEXT("Arancione"), TEXT("Rosso")};
	Mesh->ConfigureMaterialSet({Pick(BarkMaterial, TEXT("MI_M80_BGV_Corteccia")), Pick(LeafMaterial, TEXT("MI_M80_BGV_Foglie")),
		Pick(BractMaterial, FString(TEXT("MI_M80_BGV_Brattee_")) + ColourNames[uint8(Colour)]), Pick(FlowerMaterial, TEXT("MI_M80_BGV_Fiorellini"))});
	BuildInfo = FString::Printf(TEXT("%d rami, %d foglie, %d terne di brattee, %d triangoli"), G.Branches.Num(), Leaves, Flowers, M.NumTriangles());
}
