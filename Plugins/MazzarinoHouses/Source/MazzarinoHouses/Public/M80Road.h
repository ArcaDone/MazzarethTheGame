#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "M80Road.generated.h"

class USplineComponent;
class UDynamicMeshComponent;
class UStaticMesh;
class UMaterialInterface;

UENUM(BlueprintType)
enum class EM80RoadSurface : uint8
{
	/** The hand-made lava road piece (RoadSource/Migrated/LowPoly). */
	MainLava UMETA(DisplayName = "Lavica principale (LowPoly)"),
	/** The cambered version (RoadSource/Migrated/Lavica_curved). */
	CurvedLava UMETA(DisplayName = "Lavica bombata (Lavica_curved)"),
	/** A slab ("cube") draped on the ground, textured with a tiling material (default: secondary lava). */
	Slab UMETA(DisplayName = "Lastra (cubo) con materiale"),
	/** Any static mesh, repeated like the lava pieces. */
	Custom UMETA(DisplayName = "Mesh personalizzata")
};

/**
 * Road drawn with a spline (the centre line) that sits on the ground like the sidewalks: every point of the
 * spline is put on the terrain (landscape first), the surface tilts sideways with the slope and sinks a little
 * so its edges never float.
 * Mesh surfaces (the lava road pieces or a custom mesh) are repeated along the spline keeping their proportions,
 * so the setts are not stretched; the slab is one continuous surface draped on the ground, its material mapped
 * in metres (one UV unit = 1 m).
 * Houses, sidewalks and stairs ignore it when they look for the ground.
 */
UCLASS(meta = (DisplayName = "Strada (Mazzarino)"))
class MAZZARINOHOUSES_API AM80Road : public AActor
{
	GENERATED_BODY()

public:
	AM80Road();

	virtual void OnConstruction(const FTransform& Transform) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Strada")
	TObjectPtr<USplineComponent> Path;

	/** The slab surface. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Strada")
	TObjectPtr<UDynamicMeshComponent> Slab;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Strada", meta = (DisplayName = "Superficie"))
	EM80RoadSurface Surface = EM80RoadSurface::MainLava;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Strada", meta = (DisplayName = "Mesh personalizzata", EditCondition = "Surface == EM80RoadSurface::Custom"))
	TObjectPtr<UStaticMesh> CustomMesh;

	/** Optional: replaces the surface material (the slab uses MI_M80_Lavica_secondaria when empty). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Strada", meta = (DisplayName = "Materiale (opzionale)"))
	TObjectPtr<UMaterialInterface> Material;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Strada", meta = (DisplayName = "Larghezza (cm)", ClampMin = "100", ClampMax = "3000"))
	float WidthCm = 500.f;

	/** Length of each repeated mesh piece; 0 keeps the mesh proportions (setts not stretched). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Strada", meta = (DisplayName = "Lunghezza pezzi (cm, 0 = proporzionata)", ClampMin = "0", ClampMax = "5000", EditCondition = "Surface != EM80RoadSurface::Slab"))
	float PieceLengthCm = 0.f;

	/** Height of the mesh pieces, as a multiple of their proportional height. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Strada", meta = (DisplayName = "Scala verticale mesh", ClampMin = "0.1", ClampMax = "5", EditCondition = "Surface != EM80RoadSurface::Slab"))
	float VerticalScale = 1.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Strada", meta = (DisplayName = "Spessore lastra (cm)", ClampMin = "2", ClampMax = "200", EditCondition = "Surface == EM80RoadSurface::Slab"))
	float SlabThicknessCm = 25.f;

	/** Puts the road on the terrain; off: the spline points keep their own height. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Terreno", meta = (DisplayName = "Appoggia sul terreno"))
	bool bSnapToGround = true;

	/** Tilts the surface sideways with the terrain (otherwise it stays level across). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Terreno", meta = (DisplayName = "Inclina di lato col terreno", EditCondition = "bSnapToGround"))
	bool bBankWithGround = true;

	/** Height of the top of the surface over the terrain (negative = sunk into it). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Terreno", meta = (DisplayName = "Quota sul terreno (cm)", ClampMin = "-100", ClampMax = "200"))
	float HeightCm = 2.f;

	/** Distance between the terrain samples (the slab also follows the terrain across, every half of this). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Terreno", meta = (DisplayName = "Passo campionamento terreno (cm)", ClampMin = "25", ClampMax = "1000"))
	float SampleCm = 100.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Strada", meta = (DisplayName = "Collisione"))
	bool bCollision = true;

	/** Pieces or slab rows made by the last rebuild. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Strada", meta = (DisplayName = "Pezzi (calcolati)"))
	int32 PieceCount = 0;

	UFUNCTION(BlueprintCallable, CallInEditor, Category = "Strada", meta = (DisplayName = "Ricostruisci"))
	void Rebuild();

private:
	/** A point of the centre line on the ground. */
	struct FStation
	{
		double D;      // distance along the spline
		FVector Pos;   // world, top of the surface
		FVector Right; // world, horizontal
		double Roll;   // sideways tilt, radians (positive: right side higher)
	};

	double GroundZ(const FVector& World) const;
	FStation StationAt(double D) const;
	UStaticMesh* SurfaceMesh() const;
	void BuildPieces(UStaticMesh* Mesh);
	void BuildSlab();
};
