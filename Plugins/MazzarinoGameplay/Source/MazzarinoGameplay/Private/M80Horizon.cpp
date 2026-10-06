#include "M80Horizon.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "DynamicMesh/MeshNormals.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "LandscapeProxy.h"
#include "Materials/Material.h"
#include "MaterialDomain.h"
#include "UObject/ConstructorHelpers.h"

using UE::Geometry::FDynamicMesh3;

namespace
{
constexpr double EarthRadiusCm = 6.371e8;
constexpr int32 Segments = 360;
constexpr int32 Rings = 160;   // fine enough for a smooth Etna profile at 45 km

double Fbm(const FVector2D& P, int32 Octaves)
{
	double Sum = 0.0, Amp = 1.0, Norm = 0.0;
	FVector2D Q = P;
	for (int32 i = 0; i < Octaves; ++i)
	{
		Sum += Amp * FMath::PerlinNoise2D(Q);
		Norm += Amp;
		Amp *= 0.5;
		Q = Q * 2.03 + FVector2D(17.3, 9.1);
	}
	return Sum / Norm;
}

/** Field colours of the Sicilian interior in summer (linear albedo). */
FVector3f FieldColour(double Pick, double Shade)
{
	static const FVector3f Palette[] = {
		FVector3f(0.42f, 0.32f, 0.14f),  // wheat stubble
		FVector3f(0.36f, 0.30f, 0.17f),  // dry grass
		FVector3f(0.24f, 0.17f, 0.10f),  // ploughed earth
		FVector3f(0.13f, 0.15f, 0.08f),  // olive groves
		FVector3f(0.30f, 0.27f, 0.16f),  // pasture
	};
	const int32 N = UE_ARRAY_COUNT(Palette);
	const int32 I = FMath::Clamp(int32((Pick * 0.5 + 0.5) * N), 0, N - 1);
	return Palette[I] * float(0.85 + 0.3 * Shade);
}
}

AM80Horizon::AM80Horizon()
{
	PrimaryActorTick.bCanEverTick = false;
	Land = CreateDefaultSubobject<UDynamicMeshComponent>(TEXT("Land"));
	SetRootComponent(Land);
	Land->SetMobility(EComponentMobility::Static);
	Land->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Land->SetCastShadow(false);
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> Mat(TEXT("/Game/Mazzarino80/Sky/M_M80_Horizon.M_M80_Horizon"));
	if (Mat.Succeeded())
	{
		Material = Mat.Object;
	}
}

void AM80Horizon::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	int32 Triangles = 0;
	Land->ProcessMesh([&Triangles](const FDynamicMesh3& Mesh) { Triangles = Mesh.TriangleCount(); });
	if (Triangles == 0)
	{
		Rebuild();
	}
}

void AM80Horizon::Rebuild()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	// The playable terrain: its box gives the centre and the inner edge of the ring.
	FBox Box(ForceInit);
	TArray<ALandscapeProxy*> Landscapes;
	for (TActorIterator<ALandscapeProxy> It(World); It; ++It)
	{
		Box += It->GetComponentsBoundingBox(true);
		Landscapes.Add(*It);
	}
	if (!Box.IsValid)
	{
		BuildInfo = TEXT("Nessun landscape nella mappa");
		return;
	}
	const FVector2D C(Box.GetCenter());
	const FVector2D Half(Box.GetExtent());
	const double Margin = 1500.0;   // the ring starts a little inside the landscape, just below it

	auto LandscapeZ = [&](const FVector2D& P, double& OutZ) -> bool
	{
		TArray<FHitResult> Hits;
		FCollisionQueryParams Params(SCENE_QUERY_STAT(M80Horizon), true);
		World->LineTraceMultiByObjectType(Hits, FVector(P, Box.Max.Z + 10000.0), FVector(P, Box.Min.Z - 10000.0), FCollisionObjectQueryParams(ECC_WorldStatic), Params);
		for (const FHitResult& Hit : Hits)
		{
			if (Hit.GetActor() && Hit.GetActor()->IsA<ALandscapeProxy>())
			{
				OutZ = Hit.ImpactPoint.Z;
				return true;
			}
		}
		return false;
	};

	// Inner edge: distance to the landscape border along each direction, and the ground height there.
	TArray<double> EdgeR, EdgeZ;
	EdgeR.SetNum(Segments);
	EdgeZ.SetNum(Segments);
	double SumZ = 0.0;
	int32 Found = 0;
	for (int32 s = 0; s < Segments; ++s)
	{
		const double A = 2.0 * PI * s / Segments;
		const FVector2D D(FMath::Cos(A), FMath::Sin(A));
		const double ToX = FMath::Abs(D.X) > 1e-6 ? Half.X / FMath::Abs(D.X) : 1e12;
		const double ToY = FMath::Abs(D.Y) > 1e-6 ? Half.Y / FMath::Abs(D.Y) : 1e12;
		EdgeR[s] = FMath::Min(ToX, ToY) - Margin;
		double Z = 0.0;
		if (LandscapeZ(C + D * EdgeR[s], Z))
		{
			EdgeZ[s] = Z - 150.0;
			SumZ += Z;
			++Found;
		}
		else
		{
			EdgeZ[s] = TNumericLimits<double>::Max();
		}
	}
	const double BaseZ = Found ? SumZ / Found : Box.GetCenter().Z;
	for (double& Z : EdgeZ)
	{
		if (Z == TNumericLimits<double>::Max())
		{
			Z = BaseZ;
		}
	}

	const double Radius = FMath::Max<double>(RadiusKm, 10.0) * 100000.0;
	const FVector2D Off(Seed * 0.731, Seed * 0.377);
	const double EtnaD = EtnaDistanceKm * 100000.0;
	const FVector2D EtnaC = C + FVector2D(FMath::Cos(FMath::DegreesToRadians(EtnaYaw)), FMath::Sin(FMath::DegreesToRadians(EtnaYaw))) * EtnaD;
	// Height that keeps the apparent size of the real volcano, plus what the curvature of the earth hides.
	const double EtnaH = FMath::Tan(FMath::DegreesToRadians(EtnaAngleDeg)) * EtnaD + EtnaD * EtnaD / (2.0 * EarthRadiusCm);
	const double EtnaR = 2000000.0 * EtnaDistanceKm / 93.0;   // base of about 40 km at the real distance

	FDynamicMesh3 Mesh(true, true, false, false);
	const FTransform& ToLocal = GetActorTransform();
	for (int32 j = 0; j <= Rings; ++j)
	{
		const double T = double(j) / Rings;
		for (int32 s = 0; s < Segments; ++s)
		{
			const double A = 2.0 * PI * s / Segments;
			const FVector2D D(FMath::Cos(A), FMath::Sin(A));
			const double R = EdgeR[s] + (Radius - EdgeR[s]) * FMath::Pow(T, 2.2);
			const FVector2D P = C + D * R;
			const double Out = R - EdgeR[s];   // distance beyond the edge of the map

			const double Blend = FMath::SmoothStep(0.0, 350000.0, Out);
			const double Amp = FMath::Lerp(double(NearHillsM), double(FarHillsM), FMath::SmoothStep(0.0, 3000000.0, Out)) * 100.0;
			const FVector2D Q = P / 600000.0 + Off;
			double Hills = Fbm(Q, 5);
			Hills += 0.35 * (1.0 - FMath::Abs(Fbm(Q * 0.35 + FVector2D(5.2, 1.3), 3))) - 0.2;   // a few ridges
			double Z = FMath::Lerp(EdgeZ[s], BaseZ + Amp * Hills, Blend);
			double EtnaShare = 0.0;
			if (bEtna)
			{
				const double E = FVector2D::Distance(P, EtnaC);
				// Rounded summit, long concave flanks (a shield volcano, not a spike).
				const double X = FMath::Clamp(E / EtnaR, 0.0, 1.0);
				EtnaShare = FMath::Pow(1.0 - FMath::Pow(X, 1.3), 1.8);
				Z += EtnaH * EtnaShare;
			}
			Z -= Out * Out / (2.0 * EarthRadiusCm);
			if (j == Rings)
			{
				Z -= 300000.0;   // the far rim dips below the horizon line
			}
			const double Pick = Fbm(P / 45000.0 + Off * 3.0, 2);
			const double Shade = Fbm(P / 9000.0 + Off * 5.0, 2);
			FVector3f Colour = FieldColour(Pick, Shade);
			// Higher hills: more scrub; Etna: dark lava.
			Colour = FMath::Lerp(Colour, FVector3f(0.17f, 0.17f, 0.12f), float(FMath::Clamp((Z - BaseZ) / 60000.0, 0.0, 0.5)));
			Colour = FMath::Lerp(Colour, FVector3f(0.09f, 0.08f, 0.075f), float(FMath::SmoothStep(0.15, 0.6, EtnaShare)));
			const FVector3d Local = ToLocal.InverseTransformPosition(FVector(P, Z));
			Mesh.AppendVertex(UE::Geometry::FVertexInfo(Local, FVector3f::UnitZ(), Colour));
		}
	}
	auto V = [](int32 Ring, int32 Seg) { return Ring * Segments + (Seg % Segments); };
	for (int32 j = 0; j < Rings; ++j)
	{
		for (int32 s = 0; s < Segments; ++s)
		{
			const int32 A = V(j, s), B = V(j, s + 1), Cc = V(j + 1, s + 1), Dd = V(j + 1, s);
			for (const UE::Geometry::FIndex3i& Tri : {UE::Geometry::FIndex3i(A, B, Cc), UE::Geometry::FIndex3i(A, Cc, Dd)})
			{
				// GeometryCore's front face is (C-A)x(B-A): keep every triangle facing up.
				const FVector3d P0 = Mesh.GetVertex(Tri.A), P1 = Mesh.GetVertex(Tri.B), P2 = Mesh.GetVertex(Tri.C);
				const bool bUp = FVector3d::CrossProduct(P2 - P0, P1 - P0).Z > 0;
				Mesh.AppendTriangle(bUp ? Tri : UE::Geometry::FIndex3i(Tri.A, Tri.C, Tri.B));
			}
		}
	}
	UE::Geometry::FMeshNormals::QuickComputeVertexNormals(Mesh);
	Mesh.EnableAttributes();
	UE::Geometry::FMeshNormals::InitializeOverlayToPerVertexNormals(Mesh.Attributes()->PrimaryNormals(), true);
	Mesh.Attributes()->EnablePrimaryColors();
	UE::Geometry::FDynamicMeshColorOverlay* Colours = Mesh.Attributes()->PrimaryColors();
	for (int32 Vid = 0; Vid < Mesh.MaxVertexID(); ++Vid)
	{
		const FVector3f Cv = Mesh.GetVertexColor(Vid);
		Colours->AppendElement(FVector4f(Cv.X, Cv.Y, Cv.Z, 1.f));
	}
	for (int32 Tid : Mesh.TriangleIndicesItr())
	{
		Colours->SetTriangle(Tid, Mesh.GetTriangle(Tid));
	}
	const int32 Tris = Mesh.TriangleCount();
	Land->SetMesh(MoveTemp(Mesh));
	Land->ConfigureMaterialSet({Material ? Material.Get() : UMaterial::GetDefaultMaterial(MD_Surface)});
	BuildInfo = FString::Printf(TEXT("%d triangoli, bordo mappa a %.0f m, Etna alto %.0f m a %.0f km"), Tris, BaseZ / 100.0, EtnaH / 100.0, EtnaDistanceKm);
}
