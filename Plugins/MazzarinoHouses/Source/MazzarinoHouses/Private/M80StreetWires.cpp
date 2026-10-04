#include "M80StreetWires.h"
#include "M80House.h"
#include "M80MeshBuffer.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "EngineUtils.h"
#include "Materials/Material.h"
#include "MaterialDomain.h"

AM80StreetWires::AM80StreetWires()
{
	PrimaryActorTick.bCanEverTick = false;
	Wires = CreateDefaultSubobject<UDynamicMeshComponent>(TEXT("Wires"));
	SetRootComponent(Wires);
	Wires->SetMobility(EComponentMobility::Static);
	Wires->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

void AM80StreetWires::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	int32 Triangles = 0;
	Wires->ProcessMesh([&Triangles](const UE::Geometry::FDynamicMesh3& Mesh) { Triangles = Mesh.TriangleCount(); });
	if (Triangles == 0)
	{
		Rebuild();
	}
}

namespace
{
struct FFacade
{
	FVector2D A, B, N;
	double BaseZ = 0, MaxZ = 0;
	int32 Links = 0;
};
}

void AM80StreetWires::Rebuild()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	// Main facades of every house in range, in world space.
	TArray<FFacade> Facades;
	const FVector Center = GetActorLocation();
	for (TActorIterator<AM80House> It(World); It; ++It)
	{
		AM80House* House = *It;
		if (House->IsExcluded())
		{
			continue;
		}
		const FVector L = House->GetActorLocation();
		if (Radius > 0 && FVector::Dist2D(L, Center) > Radius)
		{
			continue;
		}
		const TArray<FVector2D> P = House->GetFootprintWorld2D();
		if (P.Num() < 3)
		{
			continue;
		}
		const int32 i = FMath::Clamp(House->ResolvedFrontEdge, 0, P.Num() - 1);
		FFacade F;
		F.A = P[i];
		F.B = P[(i + 1) % P.Num()];
		const FVector2D U = (F.B - F.A).GetSafeNormal();
		F.N = FVector2D(U.Y, -U.X);  // outward for a counter-clockwise footprint
		F.BaseZ = L.Z;
		F.MaxZ = L.Z + House->GetEaveZ() - 40;
		Facades.Add(F);
	}

	FRandomStream Rng(Seed);
	FM80MeshBuffer Mesh;
	const FTransform ToLocal = GetActorTransform().Inverse();
	int32 Count = 0;
	for (int32 a = 0; a < Facades.Num(); ++a)
	{
		for (int32 b = a + 1; b < Facades.Num(); ++b)
		{
			FFacade& FA = Facades[a];
			FFacade& FB = Facades[b];
			if (FA.Links >= 3 || FB.Links >= 3)
			{
				continue;
			}
			const FVector2D MA = (FA.A + FA.B) * 0.5, MB = (FB.A + FB.B) * 0.5;
			const FVector2D D = MB - MA;
			const double Dist = D.Size();
			if (Dist < MinSpan || Dist > MaxSpan)
			{
				continue;
			}
			const FVector2D Dir = D / Dist;
			// Roughly facing each other across the street (crooked old streets: loose test).
			if (FVector2D::DotProduct(FA.N, Dir) < 0.2 || FVector2D::DotProduct(FB.N, -Dir) < 0.2 || Rng.FRand() > Density)
			{
				continue;
			}
			const int32 Lines = Rng.FRand() < 0.35f ? 2 : 1;
			for (int32 k = 0; k < Lines; ++k)
			{
				auto Anchor = [&Rng](const FFacade& F) -> FVector
				{
					const FVector2D Q = FMath::Lerp(F.A, F.B, Rng.FRandRange(0.2f, 0.8f)) + F.N * 6;
					const double Z = FMath::Clamp(F.BaseZ + Rng.FRandRange(380.f, 650.f), F.BaseZ + 250, FMath::Max(F.BaseZ + 250, F.MaxZ));
					return FVector(Q.X, Q.Y, Z);
				};
				const FVector P0 = Anchor(FA), P1 = Anchor(FB);
				const double Sag = FVector::Dist(P0, P1) * Rng.FRandRange(0.025f, 0.05f);
				TArray<FVector3d> Points;
				for (int32 s = 0; s <= 16; ++s)
				{
					const double T = s / 16.0;
					const FVector W = FMath::Lerp(P0, P1, T) - FVector(0, 0, Sag * 4 * T * (1 - T));
					Points.Add(ToLocal.TransformPosition(W));
				}
				Mesh.ElementRandom = Rng.FRand();
				Mesh.Tube(0, Points, Rng.FRandRange(0.5f, 0.9f), 4);
				// Wall bracket at both ends.
				for (const FVector& WallEnd : {P0, P1})
				{
					const FVector3d E = ToLocal.TransformPosition(WallEnd);
					Mesh.Box(0, E, FVector3d(1, 0, 0), FVector3d(0, 1, 0), FVector3d(0, 0, 1), FVector3d(3, 3, 3));
				}
				++Count;
			}
			++FA.Links;
			++FB.Links;
		}
	}

	UE::Geometry::FDynamicMesh3 Dyn;
	Mesh.ToDynamicMesh(Dyn);
	Wires->SetMesh(MoveTemp(Dyn));
	Wires->ConfigureMaterialSet({WireMaterial ? WireMaterial.Get() : UMaterial::GetDefaultMaterial(MD_Surface)});
	BuildInfo = FString::Printf(TEXT("%d facciate, %d fili"), Facades.Num(), Count);
}
