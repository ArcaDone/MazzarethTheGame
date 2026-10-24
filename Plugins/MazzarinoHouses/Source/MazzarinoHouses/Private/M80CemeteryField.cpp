#include "M80CemeteryField.h"

#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/SplineComponent.h"
#include "Engine/StaticMesh.h"
#include "M80Sidewalk.h"

AM80CemeteryField::AM80CemeteryField()
{
	PrimaryActorTick.bCanEverTick = false;
	Area = CreateDefaultSubobject<USplineComponent>(TEXT("Area"));
	SetRootComponent(Area);
	Area->SetMobility(EComponentMobility::Static);
	Area->ClearSplinePoints(false);
	for (const FVector& P : {FVector(0, 0, 0), FVector(1500, 0, 0), FVector(1500, 1000, 0), FVector(0, 1000, 0)})
	{
		Area->AddSplinePoint(P, ESplineCoordinateSpace::Local, false);
	}
	for (int32 i = 0; i < Area->GetNumberOfSplinePoints(); ++i)
	{
		Area->SetSplinePointType(i, ESplinePointType::Linear, false);
	}
	Area->SetClosedLoop(true, false);
	Area->UpdateSpline();
}

void AM80CemeteryField::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	Rebuild();
}

namespace
{
	bool CemeteryInside(const TArray<FVector2D>& Poly, const FVector2D& P)
	{
		bool bIn = false;
		for (int32 i = 0, j = Poly.Num() - 1; i < Poly.Num(); j = i++)
		{
			const FVector2D& A = Poly[i];
			const FVector2D& B = Poly[j];
			if ((A.Y > P.Y) != (B.Y > P.Y) && P.X < (B.X - A.X) * (P.Y - A.Y) / (B.Y - A.Y) + A.X)
			{
				bIn = !bIn;
			}
		}
		return bIn;
	}

	struct FCemeteryKindInfo
	{
		int32 Index;      // in Kinds and Instances
		double Width;     // along the row
		double Length;    // across the row
		double BaseYaw;   // turns the mesh's long side across the row
		FVector Center;   // of its bounds, in the mesh's space
		double Bottom;
		float Weight;
	};
}

void AM80CemeteryField::Rebuild()
{
	for (UHierarchicalInstancedStaticMeshComponent* C : Instances)
	{
		if (IsValid(C))
		{
			C->DestroyComponent();
		}
	}
	Instances.Reset();
	TombCount = 0;
	const int32 Points = Area->GetNumberOfSplinePoints();
	for (int32 i = 0; i < Points; ++i)
	{
		Area->SetSplinePointType(i, ESplinePointType::Linear, false);
	}
	Area->SetClosedLoop(true, false);
	Area->UpdateSpline();

	TArray<FCemeteryKindInfo> Info;
	float TotalWeight = 0.f;
	for (int32 k = 0; k < Kinds.Num(); ++k)
	{
		UStaticMesh* Mesh = Kinds[k].Mesh;
		UHierarchicalInstancedStaticMeshComponent* C = nullptr;
		if (Mesh && Kinds[k].Weight > 0.f)
		{
			C = NewObject<UHierarchicalInstancedStaticMeshComponent>(this, NAME_None, RF_Transactional);
			C->CreationMethod = EComponentCreationMethod::UserConstructionScript;
			C->SetMobility(EComponentMobility::Static);
			C->SetupAttachment(Area);
			C->SetStaticMesh(Mesh);
			C->RegisterComponent();
			AddInstanceComponent(C);
			const FBox Box = Mesh->GetBoundingBox();
			const FVector Size = Box.GetSize();
			const bool bLongOnX = Size.X >= Size.Y;
			Info.Add({k, bLongOnX ? Size.Y : Size.X, bLongOnX ? Size.X : Size.Y, bLongOnX ? 90.0 : 0.0, Box.GetCenter(), Box.Min.Z,
			          Kinds[k].Weight});
			TotalWeight += Kinds[k].Weight;
		}
		Instances.Add(C);
	}
	if (Info.IsEmpty() || Points < 3)
	{
		return;
	}

	// the outline in the rows' frame: U along the rows, V across them
	const FTransform ToWorld = GetActorTransform();
	const FQuat RowRot(FVector::UpVector, FMath::DegreesToRadians(RowYawDeg));
	TArray<FVector2D> Poly;
	FBox2D Bounds(ForceInit);
	for (int32 i = 0; i < Points; ++i)
	{
		const FVector Local = ToWorld.InverseTransformPosition(Area->GetLocationAtSplinePoint(i, ESplineCoordinateSpace::World));
		const FVector R = RowRot.UnrotateVector(Local);
		Poly.Add(FVector2D(R.X, R.Y));
		Bounds += FVector2D(R.X, R.Y);
	}
	const double SplineZ = ToWorld.GetLocation().Z;
	auto Fits = [&](double U0, double U1, double V0, double V1)
	{
		const double M = MarginCm;
		for (const FVector2D& P : {FVector2D(U0 - M, V0 - M), FVector2D(U1 + M, V0 - M), FVector2D(U1 + M, V1 + M),
		                           FVector2D(U0 - M, V1 + M), FVector2D((U0 + U1) / 2, (V0 + V1) / 2)})
		{
			if (!CemeteryInside(Poly, P))
			{
				return false;
			}
		}
		return true;
	};

	FRandomStream Rand(Seed);
	double RowDepth = 0.0;
	for (const FCemeteryKindInfo& K : Info)
	{
		RowDepth = FMath::Max(RowDepth, K.Length);
	}
	int32 Row = 0;
	for (double V = Bounds.Min.Y + MarginCm; V + RowDepth <= Bounds.Max.Y - MarginCm + 1.0; ++Row)
	{
		const double Vc = V + RowDepth / 2;
		const bool bTurnedRow = bAlternateRows && (Row % 2 == 1);
		double U = Bounds.Min.X + MarginCm;
		while (U < Bounds.Max.X - MarginCm)
		{
			// a kind by weight
			float Pick = Rand.FRand() * TotalWeight;
			const FCemeteryKindInfo* K = &Info.Last();
			for (const FCemeteryKindInfo& Candidate : Info)
			{
				Pick -= Candidate.Weight;
				if (Pick <= 0.f)
				{
					K = &Candidate;
					break;
				}
			}
			const double U0 = U, U1 = U + K->Width;
			// the tombs of a row line up on its front (the walk side), shorter ones leave room behind
			const double V0 = bTurnedRow ? V + RowDepth - K->Length : V;
			const double V1 = V0 + K->Length;
			if (!Fits(U0, U1, V0, V1))
			{
				U += 20.0;
				continue;
			}
			U = U1 + GapCm;
			if (Rand.FRand() > Density)
			{
				continue;
			}
			const FVector2D Jit(Rand.FRandRange(-OffsetJitterCm, OffsetJitterCm), Rand.FRandRange(-OffsetJitterCm, OffsetJitterCm) * 0.5);
			const FVector LocalRow((U0 + U1) / 2 + Jit.X, (V0 + V1) / 2 + Jit.Y, 0.0);
			const FVector World = ToWorld.TransformPosition(RowRot.RotateVector(LocalRow));
			const bool bFlip = bTurnedRow != (Rand.FRand() < FlipChance);
			const double Yaw = ToWorld.Rotator().Yaw + RowYawDeg + K->BaseYaw + (bFlip ? 180.0 : 0.0) +
			                   Rand.FRandRange(-YawJitterDeg, YawJitterDeg);
			const FRotator Rot(Rand.FRandRange(-TiltMaxDeg, TiltMaxDeg), Yaw, Rand.FRandRange(-TiltMaxDeg, TiltMaxDeg));
			const double Ground = bFollowGround ? AM80Sidewalk::TraceGroundZ(GetWorld(), this, World, SplineZ) : SplineZ;
			const double Sink = Rand.FRandRange(FMath::Min(SinkMinCm, SinkMaxCm), FMath::Max(SinkMinCm, SinkMaxCm));
			// the mesh's bounds centre on the place, its bottom on the ground minus the sinking
			const FVector Pivot = Rot.RotateVector(FVector(K->Center.X, K->Center.Y, K->Bottom));
			const FVector Pos(World.X - Pivot.X, World.Y - Pivot.Y, Ground - Sink - Pivot.Z);
			Instances[K->Index]->AddInstance(FTransform(Rot, Pos), true);
			++TombCount;
		}
		V += RowDepth + RowGapCm;
		if (AisleEvery > 0 && (Row + 1) % AisleEvery == 0)
		{
			V += AisleCm;
		}
	}
}
