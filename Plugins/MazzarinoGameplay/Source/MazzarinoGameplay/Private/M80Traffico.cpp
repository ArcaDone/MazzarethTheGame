#include "M80Traffico.h"

#include "AI/NavigationModifier.h"
#include "AI/Navigation/NavigationRelevantData.h"
#include "Components/ArrowComponent.h"
#include "Components/BoxComponent.h"
#include "Components/SplineComponent.h"
#include "DrawDebugHelpers.h"
#include "EngineUtils.h"
#include "M80Car.h"
#include "MazzarinoRoadSpline.h"

namespace
{
	/** Ways that are not for cars. */
	bool IsFootway(const FString& Kind)
	{
		static const TCHAR* Foot[] = {TEXT("footway"), TEXT("steps"), TEXT("path"), TEXT("pedestrian"), TEXT("cycleway"), TEXT("corridor")};
		for (const TCHAR* F : Foot)
		{
			if (Kind.Equals(F, ESearchCase::IgnoreCase))
			{
				return true;
			}
		}
		return false;
	}

	FVector Flat(const FVector& V)
	{
		return FVector(V.X, V.Y, 0.f);
	}

	/** Point of segment AB nearest to X (2D) and its parameter. */
	float ClosestT(const FVector& A, const FVector& B, const FVector& X)
	{
		const FVector AB = Flat(B - A);
		const float L2 = AB.SizeSquared();
		return L2 < 1.f ? 0.f : FMath::Clamp(FVector::DotProduct(Flat(X - A), AB) / L2, 0.f, 1.f);
	}

	/** Distances along a polyline. */
	TArray<float> Along(const TArray<FVector>& P)
	{
		TArray<float> S;
		S.SetNumZeroed(P.Num());
		for (int32 i = 1; i < P.Num(); ++i)
		{
			S[i] = S[i - 1] + FVector::Dist2D(P[i - 1], P[i]);
		}
		return S;
	}

	FVector AtDistance(const TArray<FVector>& P, const TArray<float>& S, float D)
	{
		if (P.Num() == 0)
		{
			return FVector::ZeroVector;
		}
		if (D <= 0.f || P.Num() == 1)
		{
			return P[0];
		}
		for (int32 i = 1; i < P.Num(); ++i)
		{
			if (S[i] >= D)
			{
				const float Seg = S[i] - S[i - 1];
				return FMath::Lerp(P[i - 1], P[i], Seg > KINDA_SMALL_NUMBER ? (D - S[i - 1]) / Seg : 0.f);
			}
		}
		return P.Last();
	}

	/** 2D intersection of segments AB and CD: parameters on both. */
	bool Cross2D(const FVector& A, const FVector& B, const FVector& C, const FVector& D, float& T, float& U)
	{
		const FVector2D R(B.X - A.X, B.Y - A.Y), Q(D.X - C.X, D.Y - C.Y), W(C.X - A.X, C.Y - A.Y);
		const float Den = R.X * Q.Y - R.Y * Q.X;
		if (FMath::Abs(Den) < 1e-3f)
		{
			return false;
		}
		T = (W.X * Q.Y - W.Y * Q.X) / Den;
		U = (W.X * R.Y - W.Y * R.X) / Den;
		return T >= 0.f && T <= 1.f && U >= 0.f && U <= 1.f;
	}
}

// ---------------------------------------------------------------------------------------------
// The roadway in the people's navigation

UM80NavArea_Strada::UM80NavArea_Strada()
{
	DefaultCost = 8.f;
	DrawColor = FColor(150, 90, 40);
}

UM80StradeNavComponent::UM80StradeNavComponent()
{
	bAttachToOwnersRoot = false;
}

void UM80StradeNavComponent::Gather() const
{
	Pezzi.Reset();
	TArray<UM80Traffico::FStrada> Roads;
	UM80Traffico::GatherRoads(GetWorld(), Roads);
	for (const UM80Traffico::FStrada& R : Roads)
	{
		const float Half = R.Width * 0.5f - Margine;
		if (Half < 40.f)
		{
			continue;   // a lane so narrow nothing is left once the people's strips are off
		}
		for (int32 i = 0; i + 1 < R.P.Num(); ++i)
		{
			Pezzi.Add({R.P[i], R.P[i + 1], Half});
		}
	}
}

void UM80StradeNavComponent::OnRegister()
{
	Gather();
	Super::OnRegister();
}

void UM80StradeNavComponent::CalcAndCacheBounds() const
{
	Bounds = FBox(ForceInit);
	for (const FPezzo& Pz : Pezzi)
	{
		Bounds += Pz.A;
		Bounds += Pz.B;
	}
	if (Bounds.IsValid)
	{
		Bounds = Bounds.ExpandBy(FVector(800.f, 800.f, 600.f));
	}
	else
	{
		Bounds = FBox::BuildAABB(GetOwner() ? GetOwner()->GetActorLocation() : FVector::ZeroVector, FVector(100.f));
	}
}

void UM80StradeNavComponent::GetNavigationData(FNavigationRelevantData& Data) const
{
	for (const FPezzo& Pz : Pezzi)
	{
		const FVector Dir = Flat(Pz.B - Pz.A).GetSafeNormal();
		if (Dir.IsNearlyZero())
		{
			continue;
		}
		const FVector Right = FVector::CrossProduct(FVector::UpVector, Dir) * Pz.Half;
		// A little longer than the piece so the pieces overlap at the bends; tall enough for the road's slope.
		const FVector A = Pz.A - Dir * 20.f, B = Pz.B + Dir * 20.f;
		TArray<FVector> Pts;
		for (const float Z : {-250.f, 250.f})
		{
			Pts.Add(A + Right + FVector(0.f, 0.f, Z));
			Pts.Add(A - Right + FVector(0.f, 0.f, Z));
			Pts.Add(B - Right + FVector(0.f, 0.f, Z));
			Pts.Add(B + Right + FVector(0.f, 0.f, Z));
		}
		Data.Modifiers.Add(FAreaNavModifier(Pts, ENavigationCoordSystem::Unreal, FTransform::Identity, UM80NavArea_Strada::StaticClass()));
	}
}

AM80StradeNav::AM80StradeNav()
{
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Strade = CreateDefaultSubobject<UM80StradeNavComponent>(TEXT("Strade"));
}

// ---------------------------------------------------------------------------------------------
// Parking places

AM80Parcheggio::AM80Parcheggio()
{
	Area = CreateDefaultSubobject<UBoxComponent>(TEXT("Area"));
	Area->SetBoxExtent(FVector(230.f, 110.f, 80.f));
	Area->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Area->SetCanEverAffectNavigation(false);
	RootComponent = Area;
#if WITH_EDITORONLY_DATA
	Freccia = CreateEditorOnlyDefaultSubobject<UArrowComponent>(TEXT("Freccia"));
	if (Freccia)
	{
		Freccia->SetupAttachment(Area);
		Freccia->ArrowSize = 2.f;
	}
#endif
}

bool AM80Parcheggio::IsTaken(const AActor* Asker) const
{
	if (Prenotato.IsValid() && Prenotato.Get() != Asker)
	{
		return true;
	}
	for (TActorIterator<AM80Car> It(GetWorld()); It; ++It)
	{
		if (*It != Asker && FVector::Dist2D(It->GetActorLocation(), GetActorLocation()) < 300.f)
		{
			return true;
		}
	}
	return false;
}

// ---------------------------------------------------------------------------------------------
// Lanes

FVector FM80Corsia::At(float D, FVector* OutDir) const
{
	if (OutDir)
	{
		int32 i = 1;
		while (i < P.Num() - 1 && S[i] < D)
		{
			++i;
		}
		*OutDir = P.Num() > 1 ? Flat(P[i] - P[i - 1]).GetSafeNormal() : FVector::ForwardVector;
	}
	return AtDistance(P, S, D);
}

float FM80Corsia::Project(const FVector& Pos, float Near, float Window) const
{
	float Best = TNumericLimits<float>::Max(), BestS = 0.f;
	for (int32 i = 0; i + 1 < P.Num(); ++i)
	{
		if (Near >= 0.f && (S[i + 1] < Near - Window || S[i] > Near + Window))
		{
			continue;
		}
		const float T = ClosestT(P[i], P[i + 1], Pos);
		const float D = FVector::DistSquared2D(FMath::Lerp(P[i], P[i + 1], T), Pos);
		if (D < Best)
		{
			Best = D;
			BestS = FMath::Lerp(S[i], S[i + 1], T);
		}
	}
	return BestS;
}

UM80Traffico* UM80Traffico::Get(const UObject* Context)
{
	const UWorld* World = Context ? Context->GetWorld() : nullptr;
	return World ? World->GetSubsystem<UM80Traffico>() : nullptr;
}

void UM80Traffico::GatherRoads(const UWorld* World, TArray<FStrada>& Out)
{
	if (!World)
	{
		return;
	}
	auto Sample = [&Out](const USplineComponent* Sp, float Width, const FString& Kind)
	{
		// Footpaths and steps (the OSM kind is in the road's name when its kind was not kept), lanes too narrow for a car.
		if (!Sp || IsFootway(Kind) || Width < 250.f)
		{
			return;
		}
		for (const TCHAR* F : {TEXT("footway"), TEXT("steps"), TEXT("pedestrian"), TEXT("_path"), TEXT("cycleway")})
		{
			if (Kind.Contains(F))
			{
				return;
			}
		}
		const float Len = Sp->GetSplineLength();
		const int32 N = FMath::Max(1, FMath::CeilToInt(Len / 200.f));
		FStrada R;
		R.Width = Width;
		R.Kind = Kind;
		for (int32 i = 0; i <= N; ++i)
		{
			R.P.Add(Sp->GetLocationAtDistanceAlongSpline(Len * i / N, ESplineCoordinateSpace::World));
		}
		if (Len > 50.f)
		{
			Out.Add(MoveTemp(R));
		}
	};
	for (TActorIterator<AMazzarinoRoadSpline> It(World); It; ++It)
	{
		Sample(It->Spline, It->WidthMeters * 100.f, It->OsmHighway.IsEmpty() ? It->RoadName : It->OsmHighway);
	}
	// The lava roads of the houses' plugin (AM80Road), read by name: this module does not depend on that one.
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		if (It->GetClass()->GetName() != TEXT("M80Road"))
		{
			continue;
		}
		const FFloatProperty* W = FindFProperty<FFloatProperty>(It->GetClass(), TEXT("WidthCm"));
		Sample(It->FindComponentByClass<USplineComponent>(), W ? W->GetPropertyValue_InContainer(*It) : 500.f, FString());
	}
}

bool UM80Traffico::HasLanes()
{
	if (!bBuilt)
	{
		Build();
	}
	return Lanes.Num() > 0;
}

void UM80Traffico::Build()
{
	bBuilt = true;
	Lanes.Reset();
	Tratti.Reset();
	TArray<FStrada> Roads;
	GatherRoads(GetWorld(), Roads);
	TArray<TArray<float>> Dist;
	for (const FStrada& R : Roads)
	{
		Dist.Add(Along(R.P));
		for (int32 i = 0; i + 1 < R.P.Num(); ++i)
		{
			Tratti.Add({R.P[i], R.P[i + 1], R.Width * 0.5f});
		}
	}

	// 1) Junctions: a road's end on (or near) another road, two roads crossing; nearby ones are one junction.
	struct FCut
	{
		float D;
		int32 Node;
	};
	TArray<TArray<FCut>> Cuts;
	Cuts.SetNum(Roads.Num());
	TArray<FVector> Nodes;
	TArray<int32> NodeCount;
	auto NodeAt = [&](const FVector& X)
	{
		for (int32 n = 0; n < Nodes.Num(); ++n)
		{
			if (FVector::Dist2D(Nodes[n], X) < 500.f)
			{
				Nodes[n] = (Nodes[n] * NodeCount[n] + X) / (NodeCount[n] + 1);
				++NodeCount[n];
				return n;
			}
		}
		NodeCount.Add(1);
		return Nodes.Add(X);
	};
	TArray<FBox> Box;
	for (const FStrada& R : Roads)
	{
		Box.Add(FBox(R.P).ExpandBy(FVector(R.Width + 300.f, R.Width + 300.f, 1e6f)));
	}
	for (int32 a = 0; a < Roads.Num(); ++a)
	{
		const FStrada& RA = Roads[a];
		for (int32 End = 0; End < 2; ++End)
		{
			const FVector X = End == 0 ? RA.P[0] : RA.P.Last();
			for (int32 b = 0; b < Roads.Num(); ++b)
			{
				if (b == a || !Box[b].IsInsideXY(X))
				{
					continue;
				}
				const FStrada& RB = Roads[b];
				float Best = TNumericLimits<float>::Max(), BestD = 0.f;
				for (int32 i = 0; i + 1 < RB.P.Num(); ++i)
				{
					const float T = ClosestT(RB.P[i], RB.P[i + 1], X);
					const float D = FVector::Dist2D(FMath::Lerp(RB.P[i], RB.P[i + 1], T), X);
					if (D < Best)
					{
						Best = D;
						BestD = FMath::Lerp(Dist[b][i], Dist[b][i + 1], T);
					}
				}
				if (Best < FMath::Max(RA.Width, RB.Width) * 0.5f + 150.f)
				{
					const int32 N = NodeAt(AtDistance(RB.P, Dist[b], BestD));
					Cuts[a].Add({End == 0 ? 0.f : Dist[a].Last(), N});
					Cuts[b].Add({BestD, N});
				}
			}
		}
		for (int32 b = a + 1; b < Roads.Num(); ++b)
		{
			if (!Box[a].Intersect(Box[b]))
			{
				continue;
			}
			const FStrada& RB = Roads[b];
			for (int32 i = 0; i + 1 < RA.P.Num(); ++i)
			{
				for (int32 j = 0; j + 1 < RB.P.Num(); ++j)
				{
					float T, U;
					if (Cross2D(RA.P[i], RA.P[i + 1], RB.P[j], RB.P[j + 1], T, U))
					{
						const FVector X = FMath::Lerp(RA.P[i], RA.P[i + 1], T);
						const int32 N = NodeAt(X);
						Cuts[a].Add({FMath::Lerp(Dist[a][i], Dist[a][i + 1], T), N});
						Cuts[b].Add({FMath::Lerp(Dist[b][j], Dist[b][j + 1], U), N});
					}
				}
			}
		}
	}
	NumNodes = Nodes.Num();

	// 2) Pieces of road between junctions (or a free end: the edge of the map, a blind alley).
	struct FPiece
	{
		TArray<FVector> P;
		int32 N0, N1;
		float Width;
	};
	TArray<FPiece> Pieces;
	for (int32 r = 0; r < Roads.Num(); ++r)
	{
		TArray<FCut> C = Cuts[r];
		C.Add({0.f, -1});
		C.Add({Dist[r].Last(), -1});
		C.Sort([](const FCut& X, const FCut& Y) { return X.D < Y.D; });
		// One cut per place: a junction wins over a free end.
		TArray<FCut> U;
		for (const FCut& K : C)
		{
			if (U.Num() && K.D - U.Last().D < 150.f)
			{
				if (U.Last().Node < 0)
				{
					U.Last().Node = K.Node;
				}
				continue;
			}
			U.Add(K);
		}
		for (int32 k = 0; k + 1 < U.Num(); ++k)
		{
			if (U[k + 1].D - U[k].D < 100.f || (U[k].Node >= 0 && U[k].Node == U[k + 1].Node))
			{
				continue;
			}
			FPiece Pc;
			Pc.N0 = U[k].Node;
			Pc.N1 = U[k + 1].Node;
			Pc.Width = Roads[r].Width;
			const int32 Steps = FMath::Max(1, FMath::CeilToInt((U[k + 1].D - U[k].D) / 150.f));
			for (int32 s = 0; s <= Steps; ++s)
			{
				Pc.P.Add(AtDistance(Roads[r].P, Dist[r], FMath::Lerp(U[k].D, U[k + 1].D, float(s) / Steps)));
			}
			Pieces.Add(MoveTemp(Pc));
		}
	}

	// 3) Lanes: each piece trimmed back from its junctions; two lanes (one each way, on the right) or, in a narrow street,
	// one in the middle used one way at a time.
	TArray<float> Radius;
	Radius.Init(250.f, Nodes.Num());
	for (const FPiece& Pc : Pieces)
	{
		for (const int32 N : {Pc.N0, Pc.N1})
		{
			if (N >= 0)
			{
				Radius[N] = FMath::Clamp(FMath::Max(Radius[N], Pc.Width * 0.5f + 80.f), 250.f, 700.f);
			}
		}
	}
	TArray<int32> StartNode, EndNode;
	for (int32 e = 0; e < Pieces.Num(); ++e)
	{
		const FPiece& Pc = Pieces[e];
		const TArray<float> S = Along(Pc.P);
		const float Len = S.Last();
		float S0 = Pc.N0 >= 0 ? Radius[Pc.N0] : 0.f;
		float S1 = Len - (Pc.N1 >= 0 ? Radius[Pc.N1] : 0.f);
		if (S1 - S0 < 150.f)
		{
			S0 = Len * 0.35f;
			S1 = Len * 0.65f;
		}
		TArray<FVector> Mid;
		const int32 Steps = FMath::Max(1, FMath::CeilToInt((S1 - S0) / 150.f));
		for (int32 s = 0; s <= Steps; ++s)
		{
			Mid.Add(AtDistance(Pc.P, S, FMath::Lerp(S0, S1, float(s) / Steps)));
		}
		// Most of the town's streets are 5 m: two small cars pass each other slowly; below 4.5 m one at a time.
		const bool bNarrow = Pc.Width < 450.f;
		const float Off = bNarrow ? 0.f : FMath::Min(Pc.Width * 0.25f, 175.f);
		for (int32 Way = 0; Way < 2; ++Way)
		{
			FM80Corsia L;
			L.Edge = e;
			L.bStretta = bNarrow;
			L.RoadWidth = Pc.Width;
			L.Offset = Off;
			for (int32 i = 0; i < Mid.Num(); ++i)
			{
				const int32 j = Way == 0 ? i : Mid.Num() - 1 - i;
				const FVector Dir = Flat(Mid[FMath::Min(j + 1, Mid.Num() - 1)] - Mid[FMath::Max(j - 1, 0)]).GetSafeNormal();
				const FVector Right = FVector::CrossProduct(FVector::UpVector, Dir);
				L.P.Add(Mid[j] + Right * (Way == 0 ? Off : -Off));
			}
			L.S = Along(L.P);
			Lanes.Add(MoveTemp(L));
			StartNode.Add(Way == 0 ? Pc.N0 : Pc.N1);
			EndNode.Add(Way == 0 ? Pc.N1 : Pc.N0);
		}
	}

	// 3b) Lanes fitted to the room there really is: the OSM centre lines run over kerbs, sidewalks, steps and house corners.
	// Each point moves sideways to the nearest place a car fits (no raised ground, nothing standing); a piece where there is
	// none is closed (its lanes lead nowhere).
	{
		UWorld* World = GetWorld();
		FCollisionQueryParams Q(SCENE_QUERY_STAT(M80LaneFit), false);
		FCollisionObjectQueryParams Static(ECC_WorldStatic);
		auto Fits = [&](const FVector& At)
		{
			TArray<FHitResult> Hits;
			World->LineTraceMultiByObjectType(Hits, At + FVector(0, 0, 600), At - FVector(0, 0, 1500), Static, Q);
			double Land = -1e9, Top = -1e9;
			bool bSlab = false;
			for (const FHitResult& H : Hits)
			{
				const AActor* A = H.GetActor();
				const FString Cls = A ? A->GetClass()->GetName() : FString();
				if (Cls.StartsWith(TEXT("Landscape")))
				{
					Land = FMath::Max(Land, H.ImpactPoint.Z);
				}
				else if (H.ImpactPoint.Z > Top)
				{
					Top = H.ImpactPoint.Z;
					bSlab = Cls == TEXT("M80Road");
				}
			}
			if (Land < -1e8 && Top < -1e8)
			{
				return false;
			}
			// Something raised on the ground (a kerb, a sidewalk, a step, a wall's foot), unless it is a road slab.
			if (Top > Land + 9.0 && !bSlab)
			{
				return false;
			}
			const double Z = FMath::Max(Land, Top);
			// Nothing standing where the car goes: half a car wide, from 20 cm over the ground to its roof.
			return !World->OverlapAnyTestByObjectType(FVector(At.X, At.Y, Z + 90.0), FQuat::Identity, Static,
				FCollisionShape::MakeBox(FVector(80.0, 80.0, 70.0)), Q);
		};
		int32 Moved = 0, Closed = 0;
		for (int32 l = 0; l < Lanes.Num(); ++l)
		{
			FM80Corsia& L = Lanes[l];
			if (L.Node >= 0 || L.P.Num() < 2)
			{
				continue;
			}
			int32 Bad = 0;
			for (int32 i = 0; i < L.P.Num(); ++i)
			{
				const FVector Dir = Flat(L.P[FMath::Min(i + 1, L.P.Num() - 1)] - L.P[FMath::Max(i - 1, 0)]).GetSafeNormal();
				const FVector Right = FVector::CrossProduct(FVector::UpVector, Dir);
				bool bFound = false;
				// Towards the middle of the road first (left of a right-hand lane), then the other way.
				for (const float Off : {0.f, -40.f, 40.f, -80.f, 80.f, -120.f, 120.f, -170.f, -220.f})
				{
					const FVector C = L.P[i] + Right * Off;
					if (Fits(C))
					{
						Moved += Off != 0.f;
						L.P[i] = C;
						bFound = true;
						break;
					}
				}
				Bad += bFound ? 0 : 1;
			}
			// Smoothed after moving (single points pulled sideways make a zigzag).
			TArray<FVector> Sm = L.P;
			for (int32 i = 1; i + 1 < L.P.Num(); ++i)
			{
				Sm[i] = (L.P[i - 1] + L.P[i] * 2.0 + L.P[i + 1]) * 0.25;
			}
			L.P = Sm;
			L.S = Along(L.P);
			if (Bad * 4 > L.P.Num())
			{
				L.Next.Reset();   // mostly no room: no car is sent there
				L.bCieca = true;
				++Closed;
			}
		}
		// Where the two lanes of a piece were pushed together (a 5 m street between sidewalks), two cars cannot pass: the
		// piece becomes narrow, one car at a time.
		int32 Narrowed = 0;
		for (int32 l = 0; l + 1 < Lanes.Num(); ++l)
		{
			FM80Corsia& A = Lanes[l];
			FM80Corsia& B = Lanes[l + 1];
			if (A.Node >= 0 || B.Node >= 0 || A.Edge != B.Edge || A.bStretta || A.P.Num() < 2)
			{
				continue;
			}
			int32 Close = 0;
			for (const FVector& PA : A.P)
			{
				float Best = TNumericLimits<float>::Max();
				for (const FVector& PB : B.P)
				{
					Best = FMath::Min(Best, float(FVector::Dist2D(PA, PB)));
				}
				Close += Best < 230.f ? 1 : 0;
			}
			if (Close * 3 > A.P.Num())
			{
				A.bStretta = B.bStretta = true;
				++Narrowed;
			}
		}
		UE_LOG(LogTemp, Log, TEXT("M80Traffico: lane points moved %d, lanes closed %d, pieces made narrow %d"), Moved, Closed, Narrowed);
	}

	// 4) Across each junction: a curve from every lane coming in to every lane going out of another road.
	const int32 RoadLanes = Lanes.Num();
	for (int32 In = 0; In < RoadLanes; ++In)
	{
		const int32 N = EndNode[In];
		if (N < 0 || Lanes[In].bCieca)
		{
			continue;
		}
		for (int32 Out = 0; Out < RoadLanes; ++Out)
		{
			if (StartNode[Out] != N || Lanes[Out].Edge == Lanes[In].Edge || Lanes[Out].bCieca)
			{
				continue;
			}
			const FM80Corsia& A = Lanes[In];
			const FM80Corsia& B = Lanes[Out];
			const FVector P0 = A.P.Last(), P3 = B.P[0];
			const FVector D0 = Flat(A.P.Last() - A.P[A.P.Num() - 2]).GetSafeNormal();
			const FVector D3 = Flat(B.P[1] - B.P[0]).GetSafeNormal();
			if (FVector::DotProduct(D0, D3) < -0.85f)
			{
				continue;   // a U-turn
			}
			const float K = FVector::Dist2D(P0, P3) * 0.4f;
			const FVector P1 = P0 + D0 * K, P2 = P3 - D3 * K;
			FM80Corsia C;
			C.Node = N;
			const int32 Steps = FMath::Clamp(FMath::CeilToInt(FVector::Dist2D(P0, P3) / 100.f), 4, 16);
			for (int32 s = 0; s <= Steps; ++s)
			{
				const float T = float(s) / Steps, V = 1.f - T;
				C.P.Add(P0 * V * V * V + P1 * 3.f * V * V * T + P2 * 3.f * V * T * T + P3 * T * T * T);
			}
			C.S = Along(C.P);
			C.Next.Add(Out);
			Lanes[In].Next.Add(Lanes.Add(MoveTemp(C)));
		}
	}

	// 5) Lanes that lead only into dead ends.
	for (FM80Corsia& L : Lanes)
	{
		L.bCieca = L.Next.Num() == 0;
	}
	for (bool bChanged = true; bChanged;)
	{
		bChanged = false;
		for (FM80Corsia& L : Lanes)
		{
			if (!L.bCieca && L.Next.Num() > 0 && !L.Next.ContainsByPredicate([this](int32 n) { return !Lanes[n].bCieca; }))
			{
				L.bCieca = true;
				bChanged = true;
			}
		}
	}

	// 6) Parking places on their lane.
	Spots.Reset();
	SpotLane.Reset();
	for (TActorIterator<AM80Parcheggio> It(GetWorld()); It; ++It)
	{
		float S = 0.f;
		const int32 L = NearestLane(It->GetActorLocation(), It->GetActorForwardVector(), 600.f, S, 0.5f);
		if (L >= 0)
		{
			Spots.Add(*It);
			SpotLane.Add({L, S});
		}
	}
}

int32 UM80Traffico::NearestLane(const FVector& Pos, const FVector& Dir, float MaxDist, float& OutS, float MinDot)
{
	if (!HasLanes())
	{
		return -1;
	}
	const FVector D = Flat(Dir).GetSafeNormal();
	int32 Best = -1;
	float BestDist = MaxDist;
	for (int32 l = 0; l < Lanes.Num(); ++l)
	{
		const FM80Corsia& L = Lanes[l];
		if (L.Node >= 0)
		{
			continue;
		}
		for (int32 i = 0; i + 1 < L.P.Num(); ++i)
		{
			const FVector Seg = Flat(L.P[i + 1] - L.P[i]);
			if (FVector::DotProduct(Seg.GetSafeNormal(), D) < MinDot)
			{
				continue;
			}
			const float T = ClosestT(L.P[i], L.P[i + 1], Pos);
			const float Dd = FVector::Dist2D(FMath::Lerp(L.P[i], L.P[i + 1], T), Pos);
			if (Dd < BestDist)
			{
				BestDist = Dd;
				Best = l;
				OutS = FMath::Lerp(L.S[i], L.S[i + 1], T);
			}
		}
	}
	return Best;
}

int32 UM80Traffico::PickNext(int32 LaneIndex, FRandomStream& R) const
{
	if (!Lanes.IsValidIndex(LaneIndex))
	{
		return -1;
	}
	const TArray<int32>& Next = Lanes[LaneIndex].Next;
	TArray<int32> Open = Next.FilterByPredicate([this](int32 n) { return !Lanes[n].bCieca; });
	const TArray<int32>& From = Open.Num() ? Open : Next;
	return From.Num() ? From[R.RandRange(0, From.Num() - 1)] : -1;
}

bool UM80Traffico::IsOnRoad(const FVector& P, float Margin)
{
	if (!bBuilt)
	{
		Build();
	}
	for (const FTratto& T : Tratti)
	{
		const float Half = T.Half - Margin;
		if (Half <= 0.f || P.X < FMath::Min(T.A.X, T.B.X) - Half || P.X > FMath::Max(T.A.X, T.B.X) + Half
			|| P.Y < FMath::Min(T.A.Y, T.B.Y) - Half || P.Y > FMath::Max(T.A.Y, T.B.Y) + Half)
		{
			continue;
		}
		const float U = ClosestT(T.A, T.B, P);
		if (FVector::Dist2D(FMath::Lerp(T.A, T.B, U), P) < Half)
		{
			return true;
		}
	}
	return false;
}

bool UM80Traffico::CarComing(const FVector& P, float Near, float Seconds, const AActor* Ignore) const
{
	for (TActorIterator<AM80Car> It(GetWorld()); It; ++It)
	{
		if (*It == Ignore || It->bWrecked)
		{
			continue;
		}
		const FVector Pos = It->GetActorLocation();
		const FVector V = Flat(It->GetVelocity());
		const float D = FVector::Dist2D(Pos, P);
		if (D < Near && (V.Size() > 50.f || D < 450.f))
		{
			return true;
		}
		const float V2 = V.SizeSquared();
		if (V2 > 100.f * 100.f)
		{
			const float T = FVector::DotProduct(Flat(P - Pos), V) / V2;
			if (T > 0.f && T < Seconds && FVector::Dist2D(Pos + V * T, P) < 400.f)
			{
				return true;
			}
		}
	}
	return false;
}

bool UM80Traffico::Reserve(int32 Key, const AActor* Who)
{
	TWeakObjectPtr<const AActor>& H = Held.FindOrAdd(Key);
	if (H.IsValid() && H.Get() != Who)
	{
		return false;
	}
	H = Who;
	return true;
}

void UM80Traffico::Release(int32 Key, const AActor* Who)
{
	if (const TWeakObjectPtr<const AActor>* H = Held.Find(Key); H && (!H->IsValid() || H->Get() == Who))
	{
		Held.Remove(Key);
	}
}

void UM80Traffico::ReleaseAll(const AActor* Who)
{
	for (auto It = Held.CreateIterator(); It; ++It)
	{
		if (!It->Value.IsValid() || It->Value.Get() == Who)
		{
			It.RemoveCurrent();
		}
	}
}

AM80Parcheggio* UM80Traffico::SpotAhead(const TArray<int32>& Route, float S, float Within, const AActor* Asker, int32& OutRouteIndex, float& OutS)
{
	float Gone = 0.f;
	for (int32 k = 0; k < Route.Num() && Gone < Within; ++k)
	{
		const int32 L = Route[k];
		const float From = k == 0 ? S + 900.f : 0.f;   // room to pull in
		for (int32 j = 0; j < Spots.Num(); ++j)
		{
			AM80Parcheggio* Spot = Spots[j].Get();
			if (Spot && SpotLane[j].Key == L && SpotLane[j].Value >= From && Gone + SpotLane[j].Value - (k == 0 ? S : 0.f) < Within && !Spot->IsTaken(Asker))
			{
				OutRouteIndex = k;
				OutS = SpotLane[j].Value;
				return Spot;
			}
		}
		Gone += Lanes[L].Length() - (k == 0 ? S : 0.f);
	}
	return nullptr;
}

FString UM80Traffico::Descrivi()
{
	HasLanes();
	int32 Road = 0, Conn = 0, Narrow = 0, Blind = 0;
	for (const FM80Corsia& L : Lanes)
	{
		(L.Node >= 0 ? Conn : Road) += 1;
		Narrow += L.bStretta ? 1 : 0;
		Blind += L.bCieca ? 1 : 0;
	}
	return FString::Printf(TEXT("lanes %d connectors %d junctions %d narrow %d dead-end %d spots %d road pieces %d"),
		Road, Conn, NumNodes, Narrow, Blind, Spots.Num(), Tratti.Num());
}

void UM80Traffico::Disegna(float Seconds)
{
	HasLanes();
	for (const FM80Corsia& L : Lanes)
	{
		const FColor C = L.bCieca ? FColor::Red : L.Node >= 0 ? FColor::Cyan : L.bStretta ? FColor::Yellow : FColor::Green;
		for (int32 i = 0; i + 1 < L.P.Num(); ++i)
		{
			DrawDebugLine(GetWorld(), L.P[i] + FVector(0, 0, 60), L.P[i + 1] + FVector(0, 0, 60), C, false, Seconds, 0, 8.f);
		}
		if (L.P.Num() > 1)
		{
			DrawDebugDirectionalArrow(GetWorld(), L.P[L.P.Num() - 2] + FVector(0, 0, 60), L.P.Last() + FVector(0, 0, 60), 80.f, C, false, Seconds, 0, 8.f);
		}
	}
}

TArray<FTransform> UM80Traffico::PostiSuCorsie(int32 Quanti, float Distanza)
{
	TArray<FTransform> Out;
	if (!HasLanes())
	{
		return Out;
	}
	FRandomStream R(80);
	TArray<int32> Order;
	for (int32 l = 0; l < Lanes.Num(); ++l)
	{
		if (Lanes[l].Node < 0 && !Lanes[l].bStretta && !Lanes[l].bCieca && Lanes[l].Length() > 1200.f)
		{
			Order.Add(l);
		}
	}
	for (int32 i = Order.Num() - 1; i > 0; --i)
	{
		Order.Swap(i, R.RandRange(0, i));
	}
	for (int32 Pass = 0; Pass < 4 && Out.Num() < Quanti; ++Pass)
	{
		for (const int32 l : Order)
		{
			if (Out.Num() >= Quanti)
			{
				break;
			}
			FVector Dir;
			const FVector P = Lanes[l].At(Lanes[l].Length() * (0.3f + 0.13f * Pass), &Dir);
			if (!Out.ContainsByPredicate([&](const FTransform& T) { return FVector::Dist2D(T.GetLocation(), P) < Distanza; }))
			{
				Out.Add(FTransform(Dir.Rotation(), P));
			}
		}
	}
	return Out;
}

TArray<FTransform> UM80Traffico::PostiParcheggio(float LarghezzaMin)
{
	TArray<FTransform> Out;
	if (!HasLanes())
	{
		return Out;
	}
	for (const FM80Corsia& L : Lanes)
	{
		if (L.Node >= 0 || L.bStretta || L.RoadWidth < LarghezzaMin)
		{
			continue;
		}
		// From the lane to the right edge, keeping 1.3 m for half a car and the gap to the kerb; the parked car must leave the
		// lane free (2 m between the two middles), so only wide roads and squares have places.
		const float Side = L.RoadWidth * 0.5f - L.Offset - 130.f;
		if (Side < 200.f)
		{
			continue;
		}
		for (float D = 600.f; D < L.Length() - 600.f; D += 750.f)
		{
			FVector Dir;
			const FVector P = L.At(D, &Dir);
			Out.Add(FTransform(Dir.Rotation(), P + FVector::CrossProduct(FVector::UpVector, Dir) * Side));
		}
	}
	return Out;
}
