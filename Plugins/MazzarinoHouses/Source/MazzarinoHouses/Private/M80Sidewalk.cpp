#include "M80Sidewalk.h"
#include "M80House.h"
#include "M80MeshBuffer.h"
#include "M80Polygon.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/SplineComponent.h"
#include "Components/SplineMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Algo/Reverse.h"
#include "LandscapeProxy.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "Materials/Material.h"
#include "Materials/MaterialInterface.h"
#include "MaterialDomain.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
const FName GeneratedTag(TEXT("M80SidewalkGenerated"));
}

AM80Sidewalk::AM80Sidewalk()
{
	PrimaryActorTick.bCanEverTick = false;
	Path = CreateDefaultSubobject<USplineComponent>(TEXT("Path"));
	SetRootComponent(Path);
	Path->SetMobility(EComponentMobility::Static);
	Path->bInputSplinePointsToConstructionScript = true;
	Path->SetUnselectedSplineSegmentColor(FLinearColor(0.9f, 0.8f, 0.2f));
	Fill = CreateDefaultSubobject<UDynamicMeshComponent>(TEXT("Fill"));
	Fill->SetupAttachment(Path);
	Fill->SetMobility(EComponentMobility::Static);
	Fill->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);
	// Houses must keep finding the real ground under a sidewalk.
	Tags.Add(TEXT("M80IgnoreGround"));

	// Slab: a plain box with the tiles mapped in world space (the hand-made marciaPiedeBase slab has
	// rounded edges that turn wavy once stretched along a spline). Curb: the lava-stone piece.
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Slab(TEXT("/Engine/BasicShapes/Cube.Cube"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> SlabMat(TEXT("/Game/Mazzarino80/Kit/Sidewalk/M_M80_Marciapiede.M_M80_Marciapiede"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Curb(TEXT("/Game/Migrated/Case/Door/marciaPiedeBase_001.marciaPiedeBase_001"));
	SlabMesh = Slab.Object;
	SlabMaterial = SlabMat.Object;
	CurbMesh = Curb.Object;
}

void AM80Sidewalk::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	Rebuild();
}

double AM80Sidewalk::GroundZ(const FVector& World) const
{
	return bSnapToGround ? TraceGroundZ(GetWorld(), this, World, World.Z) : World.Z;
}

double AM80Sidewalk::TraceGroundZ(const UWorld* W, const AActor* Ignore, const FVector& World, double Fallback)
{
	if (!W)
	{
		return Fallback;
	}
	FCollisionQueryParams Params(SCENE_QUERY_STAT(M80SidewalkGround), true, Ignore);
	const FCollisionObjectQueryParams Objects(ECC_WorldStatic);
	TArray<FHitResult> Hits;
	W->LineTraceMultiByObjectType(Hits, World + FVector(0, 0, 20000), World - FVector(0, 0, 20000), Objects, Params);
	// The terrain wins: the trace starts 200 m up, so roofs, hand-made buildings or HLOD shells above a
	// point under a house would otherwise lift the paving onto them like a tent.
	for (const FHitResult& Hit : Hits)
	{
		if (Cast<ALandscapeProxy>(Hit.GetActor()))
		{
			return Hit.ImpactPoint.Z;
		}
	}
	for (const FHitResult& Hit : Hits)
	{
		const AActor* A = Hit.GetActor();
		const UPrimitiveComponent* C = Hit.GetComponent();
		if ((A && (A->IsA<AM80House>() || A->ActorHasTag(TEXT("M80IgnoreGround")))) || (C && C->IsA<UInstancedStaticMeshComponent>()))
		{
			continue;
		}
		return Hit.ImpactPoint.Z;
	}
	return Fallback;
}

TArray<TArray<FVector2D>> AM80Sidewalk::NearbyHouses(double Reach) const
{
	TArray<TArray<FVector2D>> Houses;
	UWorld* World = GetWorld();
	const int32 N = Path ? Path->GetNumberOfSplinePoints() : 0;
	if (!World || N < 1)
	{
		return Houses;
	}
	FBox Area(ForceInit);
	for (int32 i = 0; i < N; ++i)
	{
		Area += Path->GetLocationAtSplinePoint(i, ESplineCoordinateSpace::World);
	}
	Area = Area.ExpandBy(FVector(Reach, Reach, 1e6));
	for (TActorIterator<AM80House> It(World); It; ++It)
	{
		if (It->IsExcluded() || !It->Footprint || !Area.Intersect(It->Footprint->Bounds.GetBox()))
		{
			continue;
		}
		TArray<FVector2D> P = It->GetFootprintWorld2D();
		if (P.Num() < 3)
		{
			continue;
		}
		if (M80Poly::SignedArea(P) < 0)
		{
			Algo::Reverse(P);
		}
		Houses.Add(MoveTemp(P));
	}
	return Houses;
}

void AM80Sidewalk::SnapToHouses(double W)
{
	SnappedPoints = 0;
	SnapStatus.Reset();
	UWorld* World = GetWorld();
	const int32 N = Path->GetNumberOfSplinePoints();
	if (!World || N < 1)
	{
		return;
	}
	const double Reach = SnapDistanceCm + W;
	const TArray<TArray<FVector2D>> Houses = NearbyHouses(Reach);
	if (Houses.IsEmpty())
	{
		SnapStatus = FString::Printf(TEXT("Nessuna casa procedurale entro %.0f cm"), Reach);
		return;
	}
	auto InsideAny = [&Houses](const FVector2D& Q)
	{
		for (const TArray<FVector2D>& P : Houses)
		{
			if (M80Poly::Contains(P, Q))
			{
				return true;
			}
		}
		return false;
	};
	const double Half = W * 0.5 + FMath::Max(0.f, WallGapCm);

	// Facade nearest to Q running along Dir (within ~30 degrees), on its line also a little past its corners;
	// out: the line of the sidewalk's centre (point and direction) and the distance from Q to the facade.
	struct FLine
	{
		FVector2D Point, Dir;
		double Dist = TNumericLimits<double>::Max();
		const TArray<FVector2D>* House = nullptr;
		int32 Edge = -1;
	};
	auto Facade = [&](const FVector2D& Q, const FVector2D& Dir, bool bInside)
	{
		FLine Best;
		for (const TArray<FVector2D>& P : Houses)
		{
			for (int32 e = 0; e < P.Num(); ++e)
			{
				const FVector2D A = P[e], B = P[(e + 1) % P.Num()];
				const FVector2D AB = B - A;
				const double L2 = AB.SizeSquared();
				if (L2 < 1.0)
				{
					continue;
				}
				const FVector2D U = AB / FMath::Sqrt(L2);
				if (!Dir.IsNearlyZero() && FMath::Abs(FVector2D::CrossProduct(Dir, U)) > 0.5)
				{
					continue;
				}
				const double Len = FMath::Sqrt(L2), Along = FVector2D::DotProduct(Q - A, U);
				if (Along < -SnapDistanceCm || Along > Len + SnapDistanceCm)
				{
					continue;
				}
				const FVector2D C = A + U * Along;
				const double D = FVector2D::Distance(Q, C);
				if (D >= Best.Dist || (!bInside && D > SnapDistanceCm))
				{
					continue;
				}
				// Centre of the sidewalk half its width out of the facade; never onto a house (party walls).
				const FVector2D T = C + M80Poly::EdgeNormal(P, e) * Half;
				if (InsideAny(T))
				{
					continue;
				}
				Best.Point = T;
				Best.Dir = U;
				Best.Dist = D;
				Best.House = &P;
				Best.Edge = e;
			}
		}
		return Best;
	};

	TArray<FVector> Orig;
	for (int32 i = 0; i < N; ++i)
	{
		Orig.Add(Path->GetLocationAtSplinePoint(i, ESplineCoordinateSpace::World));
	}
	const bool bLoop = Path->IsClosedLoop();
	TArray<int32> Left;
	int32 Moved = 0;
	for (int32 i = 0; i < N; ++i)
	{
		const FVector2D Q(Orig[i].X, Orig[i].Y);
		const bool bInside = InsideAny(Q);
		// The segments arriving at and leaving the point: at a corner of the sidewalk each one follows its own
		// facade and the point goes where the two lines meet (the corner of the house, half a width out).
		const int32 Prev = i > 0 ? i - 1 : (bLoop ? N - 1 : -1), NextI = i + 1 < N ? i + 1 : (bLoop ? 0 : -1);
		const FVector2D DirIn = Prev >= 0 ? FVector2D(Q - FVector2D(Orig[Prev].X, Orig[Prev].Y)).GetSafeNormal() : FVector2D::ZeroVector;
		const FVector2D DirOut = NextI >= 0 ? FVector2D(FVector2D(Orig[NextI].X, Orig[NextI].Y) - Q).GetSafeNormal() : FVector2D::ZeroVector;
		const FLine In = DirIn.IsNearlyZero() ? FLine() : Facade(Q, DirIn, bInside);
		const FLine Out = DirOut.IsNearlyZero() ? FLine() : Facade(Q, DirOut, bInside);
		const bool bIn = In.Edge >= 0, bOut = Out.Edge >= 0;
		if (!bIn && !bOut)
		{
			Left.Add(i);
			continue;
		}
		FVector2D Target = !bOut || (bIn && In.Dist <= Out.Dist) ? In.Point : Out.Point;
		const double Cross = FVector2D::CrossProduct(In.Dir, Out.Dir);
		if (bIn && bOut && (In.House != Out.House || In.Edge != Out.Edge) && FMath::Abs(Cross) > 0.3)
		{
			// Intersection of the two offset lines.
			const double T = FVector2D::CrossProduct(Out.Point - In.Point, Out.Dir) / Cross;
			const FVector2D Corner = In.Point + In.Dir * T;
			if (FVector2D::Distance(Corner, Q) <= SnapDistanceCm + Half && !InsideAny(Corner))
			{
				Target = Corner;
			}
		}
		++SnappedPoints;
		if (FVector2D::Distance(Q, Target) > 0.5)
		{
			Path->SetLocationAtSplinePoint(i, FVector(Target.X, Target.Y, Orig[i].Z), ESplineCoordinateSpace::World, false);
			++Moved;
		}
	}
	if (Moved)
	{
		Path->UpdateSpline();
	}
	SnapStatus = FString::Printf(TEXT("%d punti su %d agganciati"), SnappedPoints, N);
	if (Left.Num())
	{
		TArray<FString> Ids;
		for (int32 i : Left)
		{
			Ids.Add(FString::FromInt(i));
		}
		SnapStatus += FString::Printf(TEXT("; liberi i punti %s: nessuna facciata parallela entro %.0f cm"), *FString::Join(Ids, TEXT(", ")), SnapDistanceCm);
	}
}

void AM80Sidewalk::RefreshSnappedNear(UWorld* World, const FBox& Area)
{
	if (!World)
	{
		return;
	}
	for (TActorIterator<AM80Sidewalk> It(World); It; ++It)
	{
		if (!It->bSnapToHouses || !It->Path)
		{
			continue;
		}
		const double Reach = It->SnapDistanceCm + It->WidthCm;
		if (Area.Intersect(It->Path->Bounds.GetBox().ExpandBy(FVector(Reach, Reach, 1e6))))
		{
			It->Rebuild();
		}
	}
}

TArray<AM80Sidewalk::FStation> AM80Sidewalk::Sample(double Step) const
{
	TArray<FStation> Out;
	const double Length = Path->GetSplineLength();
	if (Length < 1.0)
	{
		return Out;
	}
	const int32 N = FMath::Max(1, FMath::CeilToInt(Length / FMath::Max(Step, 10.0)));
	for (int32 k = 0; k <= N; ++k)
	{
		const double D = Length * k / N;
		FStation S;
		S.Pos = Path->GetLocationAtDistanceAlongSpline(D, ESplineCoordinateSpace::World);
		FVector Dir = Path->GetDirectionAtDistanceAlongSpline(D, ESplineCoordinateSpace::World);
		Dir.Z = 0;
		if (!Dir.Normalize())
		{
			Dir = FVector::ForwardVector;
		}
		S.Right = FVector(-Dir.Y, Dir.X, 0);
		Out.Add(S);
	}
	return Out;
}

void AM80Sidewalk::AddStrip(UStaticMesh* Mesh, UMaterialInterface* Material, const TArray<FStation>& St, double Lateral, double Width, double Top, double Depth, bool bWrap)
{
	if (!Mesh || St.Num() < 2 || Width <= 1.0)
	{
		return;
	}
	const FBox Box = Mesh->GetBoundingBox();
	const double MeshW = Box.Max.Y - Box.Min.Y, MeshH = Box.Max.Z - Box.Min.Z;
	if (MeshW <= UE_SMALL_NUMBER || MeshH <= UE_SMALL_NUMBER)
	{
		return;
	}
	const double SY = Width / MeshW;
	const double SZ = (Top + Depth) / MeshH;
	const FVector2D Scale(SY, SZ);
	const FVector2D Offset(-Box.GetCenter().Y * SY, Top - Box.Max.Z * SZ);
	const FTransform& T = Path->GetComponentTransform();
	// A closed spline samples its first point again at the end: tangents wrap around.
	const bool bLoop = bWrap && Path->IsClosedLoop() && St.Num() > 2;

	TArray<FVector> P;
	P.Reserve(St.Num());
	for (const FStation& S : St)
	{
		FVector W = S.Pos + S.Right * Lateral;
		W.Z = GroundZ(W);
		P.Add(T.InverseTransformPosition(W));
	}
	const int32 Last = P.Num() - 1;
	auto Tangent = [&P, Last, bLoop](int32 j)
	{
		if (bLoop)
		{
			return (P[(j + 1) % Last] - P[(j - 1 + Last) % Last]) * 0.5;
		}
		if (j == 0)
		{
			return P[1] - P[0];
		}
		return j == Last ? P[Last] - P[Last - 1] : (P[j + 1] - P[j - 1]) * 0.5;
	};
	for (int32 i = 0; i < Last; ++i)
	{
		const FVector TA = Tangent(i);
		const FVector TB = Tangent(i + 1);
		USplineMeshComponent* Seg = NewObject<USplineMeshComponent>(this, NAME_None, RF_Transactional);
		Seg->CreationMethod = EComponentCreationMethod::UserConstructionScript;
		Seg->ComponentTags.Add(GeneratedTag);
		Seg->SetupAttachment(Path);
		Seg->SetMobility(EComponentMobility::Static);
		Seg->SetStaticMesh(Mesh);
		if (Material)
		{
			Seg->SetMaterial(0, Material);
		}
		Seg->SetForwardAxis(ESplineMeshAxis::X, false);
		Seg->SetBoundaryMin(Box.Min.X, false);
		Seg->SetBoundaryMax(Box.Max.X, false);
		Seg->SetStartAndEnd(P[i], TA, P[i + 1], TB, false);
		Seg->SetStartScale(Scale, false);
		Seg->SetEndScale(Scale, false);
		Seg->SetStartOffset(Offset, false);
		Seg->SetEndOffset(Offset, false);
		Seg->SetCollisionProfileName(bCollision ? TEXT("BlockAll") : TEXT("NoCollision"));
		Seg->RegisterComponent();
		Seg->UpdateMesh();
	}
}

double AM80Sidewalk::BuildFill(double Top)
{
	const FTransform& T = Path->GetComponentTransform();
	const double Length = Path->GetSplineLength();
	const int32 N = FMath::Clamp(FMath::CeilToInt(Length / 50.0), 3, 4000);
	TArray<FVector2D> Outline;
	for (int32 k = 0; k < N; ++k)
	{
		Outline.Add(FVector2D(Path->GetLocationAtDistanceAlongSpline(Length * k / N, ESplineCoordinateSpace::Local)));
	}
	M80Poly::Clean(Outline, 5.0);
	if (Outline.Num() < 3)
	{
		return 1.0;
	}

	// Which side of the walking direction is inside.
	const FVector Start = Path->GetLocationAtDistanceAlongSpline(0, ESplineCoordinateSpace::Local);
	const FVector Dir = Path->GetDirectionAtDistanceAlongSpline(0, ESplineCoordinateSpace::Local);
	const FVector2D Right = FVector2D(-Dir.Y, Dir.X).GetSafeNormal();
	const double Inside = M80Poly::Contains(Outline, FVector2D(Start) + Right * 10.0) ? 1.0 : -1.0;

	// With a curb the paving stops under its inner edge, so the stones show all around the piazza.
	if (CurbMesh && CurbSide != EM80CurbSide::None)
	{
		const double Inset = FMath::Clamp<double>(CurbWidthCm, 10.0, 100.0) * 0.8;
		TArray<FVector2D> Inner = Outline;
		for (int32 i = 0; i < Outline.Num(); ++i)
		{
			Inner[i] = Outline[i] - M80Poly::Miter(Outline, i) * Inset;
		}
		M80Poly::Clean(Inner, 5.0);
		if (Inner.Num() >= 3)
		{
			Outline = MoveTemp(Inner);
		}
	}

	// Ground under a local XY point, plus the paving height, back in local space (cached: cells share corners).
	TMap<FIntPoint, FVector3d> Cache;
	auto Drape = [&](const FVector2D& Q) -> FVector3d
	{
		const FIntPoint Key(FMath::RoundToInt(Q.X * 4), FMath::RoundToInt(Q.Y * 4));
		if (const FVector3d* Hit = Cache.Find(Key))
		{
			return *Hit;
		}
		FVector W = T.TransformPosition(FVector(Q.X, Q.Y, 0));
		W.Z = GroundZ(W) + Top;
		return Cache.Add(Key, T.InverseTransformPosition(W));
	};

	// The polygon is cut into 2 m cells so the paving follows the slopes of the terrain.
	FM80MeshBuffer Mesh;
	const double Cell = 200.0;
	const FBox2D Box(Outline);
	const FVector3d FacingUp(0, 0, 1);
	for (double X0 = FMath::FloorToDouble(Box.Min.X / Cell) * Cell; X0 < Box.Max.X; X0 += Cell)
	{
		const TArray<FVector2D> Column = M80Poly::ClipHalfPlane(M80Poly::ClipHalfPlane(Outline, FVector2D(1, 0), X0, true), FVector2D(1, 0), X0 + Cell, false);
		if (Column.Num() < 3)
		{
			continue;
		}
		for (double Y0 = FMath::FloorToDouble(Box.Min.Y / Cell) * Cell; Y0 < Box.Max.Y; Y0 += Cell)
		{
			TArray<FVector2D> Piece = M80Poly::ClipHalfPlane(M80Poly::ClipHalfPlane(Column, FVector2D(0, 1), Y0, true), FVector2D(0, 1), Y0 + Cell, false);
			if (Piece.Num() < 3)
			{
				continue;
			}
			M80Poly::Clean(Piece, 0.5);
			TArray<int32> Tris;
			if (Piece.Num() < 3 || !M80Poly::Triangulate(Piece, Tris))
			{
				continue;
			}
			TArray<FVector3d> V;
			for (const FVector2D& Q : Piece)
			{
				V.Add(Drape(Q));
			}
			for (int32 t = 0; t + 2 < Tris.Num(); t += 3)
			{
				const int32 A = Tris[t], B = Tris[t + 1], C = Tris[t + 2];
				Mesh.Tri(0, V[A], V[B], V[C], FVector2f(Piece[A] / 100.0), FVector2f(Piece[B] / 100.0), FVector2f(Piece[C] / 100.0), FacingUp);
			}
		}
	}
	// Side skirt down into the ground, so the raised edge never shows a gap.
	const FVector3d Down(0, 0, Top + 30.0);
	for (int32 i = 0; i < Outline.Num(); ++i)
	{
		const FVector2D Out = M80Poly::EdgeNormal(Outline, i);
		const FVector3d A = Drape(Outline[i]), B = Drape(Outline[(i + 1) % Outline.Num()]);
		Mesh.QuadProjected(0, A - Down, B - Down, B, A, FVector3d(Out.X, Out.Y, 0));
	}

	UE::Geometry::FDynamicMesh3 Dyn;
	Mesh.ToDynamicMesh(Dyn);
	Fill->SetMesh(MoveTemp(Dyn));
	Fill->ConfigureMaterialSet({SlabMaterial ? SlabMaterial.Get() : UMaterial::GetDefaultMaterial(MD_Surface)});
	Fill->SetComplexAsSimpleCollisionEnabled(bCollision, true);
	Fill->SetCollisionProfileName(bCollision ? TEXT("BlockAll") : TEXT("NoCollision"));
	return Inside;
}

void AM80Sidewalk::Rebuild()
{
	TInlineComponentArray<USplineMeshComponent*> Existing(this);
	for (USplineMeshComponent* C : Existing)
	{
		if (C && C->ComponentHasTag(GeneratedTag))
		{
			C->DestroyComponent();
		}
	}
	if (Fill)
	{
		Fill->SetMesh(UE::Geometry::FDynamicMesh3());
	}
	if (!Path || Path->GetNumberOfSplinePoints() < 2)
	{
		return;
	}
	Path->SetClosedLoop(bClosedLoop && Path->GetNumberOfSplinePoints() > 2);
	const double W = FMath::Clamp<double>(WidthCm, 40.0, 600.0);
	if (bSnapToHouses && !(Path->IsClosedLoop() && bFillInside))
	{
		SnapToHouses(W);
	}
	else
	{
		SnappedPoints = 0;
		SnapStatus = bSnapToHouses ? TEXT("Spento per le piazze (Riempi l'interno)") : TEXT("");
	}
	const int32 Curbs = CurbSide == EM80CurbSide::None ? 0 : (CurbSide == EM80CurbSide::Both ? 2 : 1);
	const double CW = Curbs ? FMath::Min<double>(CurbWidthCm, W / (Curbs + 1)) : 0.0;
	const double Top = FMath::Max(0.f, TopHeightCm);

	if (Path->IsClosedLoop() && bFillInside && Fill)
	{
		// Piazza: paving inside the outline, one curb running along it on the inside.
		const double Inside = BuildFill(Top);
		if (CurbMesh && Curbs)
		{
			const FBox CB = CurbMesh->GetBoundingBox();
			const double CurbW = FMath::Max(1.0, CB.Max.Y - CB.Min.Y);
			const double Piece = FMath::Clamp((CB.Max.X - CB.Min.X) * CW / CurbW, 60.0, 400.0);
			AddStrip(CurbMesh, CurbMaterial, Sample(Piece), Inside * CW / 2, CW, Top + 2.0, 25.0 + Top);
		}
		return;
	}

	// Magnet: no curb against a wall. Stations whose edge on a side touches a house (or lies in one) are
	// "against the house" on that side; a single curb drawn on the house side moves to the street side.
	TArray<TArray<FVector2D>> Walls;
	if (bSnapToHouses && SnappedPoints > 0)
	{
		Walls = NearbyHouses(W + 200.0);
	}
	const double Edge = W / 2 + FMath::Max(0.f, WallGapCm) + 2.0;
	auto AgainstHouse = [&Walls, Edge](const FStation& S, double Side)
	{
		const FVector P = S.Pos + S.Right * Side * Edge;
		const FVector2D Q(P.X, P.Y);
		for (const TArray<FVector2D>& H : Walls)
		{
			if (M80Poly::Contains(H, Q))
			{
				return true;
			}
			for (int32 e = 0; e < H.Num(); ++e)
			{
				if (M80Poly::SegmentDistance(Q, H[e], H[(e + 1) % H.Num()]) < 20.0)
				{
					return true;
				}
			}
		}
		return false;
	};
	bool bCurbRight = CurbSide == EM80CurbSide::Right || CurbSide == EM80CurbSide::Both;
	bool bCurbLeft = CurbSide == EM80CurbSide::Left || CurbSide == EM80CurbSide::Both;
	bool bHouseRight = false, bHouseLeft = false;
	const TArray<FStation> Slab = Sample(SlabPieceCm);
	if (Walls.Num())
	{
		int32 Right = 0, Left = 0;
		for (const FStation& S : Slab)
		{
			Right += AgainstHouse(S, 1.0);
			Left += AgainstHouse(S, -1.0);
		}
		bHouseRight = Right > 0 && Right >= Left;
		bHouseLeft = Left > 0 && Left > Right;
		if (CurbSide == EM80CurbSide::Right && bHouseRight)
		{
			bCurbRight = false;
			bCurbLeft = true;
		}
		else if (CurbSide == EM80CurbSide::Left && bHouseLeft)
		{
			bCurbLeft = false;
			bCurbRight = true;
		}
	}

	// Slab between the curbs (with a little overlap under them); up to the wall on the house side.
	double SlabMin = -W / 2, SlabMax = W / 2;
	if (bCurbRight && !bHouseRight)
	{
		SlabMax -= CW * 0.8;
	}
	if (bCurbLeft && !bHouseLeft)
	{
		SlabMin += CW * 0.8;
	}
	AddStrip(SlabMesh, SlabMaterial, Slab, (SlabMin + SlabMax) / 2, SlabMax - SlabMin, Top, 30.0);

	if (CurbMesh && Curbs)
	{
		const FBox CB = CurbMesh->GetBoundingBox();
		const double CurbW = FMath::Max(1.0, CB.Max.Y - CB.Min.Y);
		// Keep the stones' proportions: piece length = mesh length at the curb's scale.
		const double Piece = FMath::Clamp((CB.Max.X - CB.Min.X) * CW / CurbW, 60.0, 400.0);
		const TArray<FStation> St = Sample(Piece);
		for (const double Side : {1.0, -1.0})
		{
			if (!(Side > 0 ? bCurbRight : bCurbLeft))
			{
				continue;
			}
			// Only the runs of stations away from the walls.
			TArray<FStation> Run;
			for (int32 k = 0; k <= St.Num(); ++k)
			{
				const bool bFree = k < St.Num() && (Walls.IsEmpty() || !AgainstHouse(St[k], Side));
				if (bFree)
				{
					Run.Add(St[k]);
					continue;
				}
				if (Run.Num() >= 2)
				{
					// A piece of a closed ring is an open strip: no wrapping tangents.
					AddStrip(CurbMesh, CurbMaterial, Run, Side * (W / 2 - CW / 2), CW, Top + 2.0, 25.0 + Top, Run.Num() == St.Num());
				}
				Run.Reset();
			}
		}
	}
}
