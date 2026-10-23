#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "M80Sidewalk.generated.h"

class USplineComponent;
class USplineMeshComponent;
class UDynamicMeshComponent;
class UStaticMesh;
class UMaterialInterface;
struct FM80MeshBuffer;

UENUM(BlueprintType)
enum class EM80CurbSide : uint8
{
	Right UMETA(DisplayName = "Destra"),
	Left UMETA(DisplayName = "Sinistra"),
	Both UMETA(DisplayName = "Entrambi"),
	None UMETA(DisplayName = "Nessuno")
};

/**
 * Sidewalk drawn with a spline (the centre line): a paved slab (tiles of the hand-made "Marciapiede"
 * material, mapped in world space) plus a lava-stone curb on the road side, one mesh with sharp mitered corners.
 * The slab is one mesh laid on the ground every half metre, at both its edges (it follows slopes along and
 * across); its sides are lava stone mapped on their own plane (the tiles, mapped from above, streaked down them).
 * Houses ignore it when they look for the ground.
 * "Destra" is the right-hand side walking along the spline from the first point.
 * With "Spline chiusa" the path becomes a ring (e.g. around a block); with "Riempi l'interno" the whole
 * inside is paved (a piazza), draped on the ground, and the curb runs along the outline on the inside.
 * With "Attacca alle facciate" every point near a procedural house is moved so the edge of the paving
 * runs along the facade (magnet): the spline can be drawn roughly, even inside the houses.
 */
UCLASS(meta = (DisplayName = "Marciapiede (Mazzarino)"))
class MAZZARINOHOUSES_API AM80Sidewalk : public AActor
{
	GENERATED_BODY()

public:
	AM80Sidewalk();

	virtual void OnConstruction(const FTransform& Transform) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Marciapiede")
	TObjectPtr<USplineComponent> Path;

	/** The slab (or the paved inside of a closed spline). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Marciapiede")
	TObjectPtr<UDynamicMeshComponent> Fill;

	/** Joins the last point to the first one. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Marciapiede", meta = (DisplayName = "Spline chiusa"))
	bool bClosedLoop = false;

	/** Paves the whole area inside the closed spline (piazza); "Larghezza" is then ignored. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Marciapiede", meta = (DisplayName = "Riempi l'interno (piazza)", EditCondition = "bClosedLoop"))
	bool bFillInside = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Marciapiede", meta = (DisplayName = "Larghezza (cm)", ClampMin = "40", ClampMax = "600"))
	float WidthCm = 150.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Marciapiede", meta = (DisplayName = "Altezza dal suolo (cm)", ClampMin = "0", ClampMax = "60"))
	float TopHeightCm = 16.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Marciapiede", meta = (DisplayName = "Lato del cordolo"))
	EM80CurbSide CurbSide = EM80CurbSide::Right;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Marciapiede", meta = (DisplayName = "Larghezza cordolo (cm)", ClampMin = "10", ClampMax = "100"))
	float CurbWidthCm = 32.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Marciapiede", meta = (DisplayName = "Appoggia sul terreno"))
	bool bSnapToGround = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Marciapiede", meta = (DisplayName = "Collisione"))
	bool bCollision = true;

	/** Magnet: points closer than "Distanza di aggancio" to a house facade running along the sidewalk (or inside a
	 *  house) move so that the side of the sidewalk towards the house lies on the facade; past the corners the
	 *  sidewalk keeps the facade's line. Moving or reshaping a house re-attaches it. Where the sidewalk touches a
	 *  wall there is no curb on that side: a single curb drawn on the house side moves to the street side. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Case", meta = (DisplayName = "Attacca alle facciate"))
	bool bSnapToHouses = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Case", meta = (DisplayName = "Distanza di aggancio (cm)", ClampMin = "10", ClampMax = "2000", EditCondition = "bSnapToHouses"))
	float SnapDistanceCm = 300.f;

	/** Gap left between the paving and the wall (0 = touching). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Case", meta = (DisplayName = "Distanza dal muro (cm)", ClampMin = "0", ClampMax = "100", EditCondition = "bSnapToHouses"))
	float WallGapCm = 0.f;

	/** Points attached to a facade in the last build. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Case", meta = (DisplayName = "Punti agganciati"))
	int32 SnappedPoints = 0;

	/** What the magnet did in the last build, and why points were left where they are. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Case", meta = (DisplayName = "Stato aggancio"))
	FString SnapStatus;

	/** How often the slab is laid on the ground along the spline (at most every 50 cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Marciapiede", meta = (DisplayName = "Passo lastra sul terreno (cm)", ClampMin = "10", ClampMax = "2000"))
	float SlabPieceCm = 50.f;

	/** Not used any more (the slab is built as its own mesh); kept so saved sidewalks load. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mesh", meta = (DisplayName = "Mesh lastra (non usata)"))
	TObjectPtr<UStaticMesh> SlabMesh;

	/** Gives the curb its material (when "Materiale cordolo" is empty); the curb itself is built with the slab. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mesh", meta = (DisplayName = "Mesh cordolo"))
	TObjectPtr<UStaticMesh> CurbMesh;

	/** Optional: replaces the slab mesh material. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mesh", meta = (DisplayName = "Materiale lastra"))
	TObjectPtr<UMaterialInterface> SlabMaterial;

	/** Optional: replaces the curb mesh material. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mesh", meta = (DisplayName = "Materiale cordolo"))
	TObjectPtr<UMaterialInterface> CurbMaterial;

	UFUNCTION(BlueprintCallable, CallInEditor, Category = "Marciapiede", meta = (DisplayName = "Ricostruisci"))
	void Rebuild();

	/** Ground under a point: the landscape first, else the first static surface that is not a house,
	 *  a sidewalk/stair (tag M80IgnoreGround) or an instanced prop; Fallback when nothing is hit. */
	static double TraceGroundZ(const UWorld* World, const AActor* Ignore, const FVector& Point, double Fallback);

	/** Rebuilds the sidewalks with the magnet on that touch Area (after a house changed). */
	static void RefreshSnappedNear(UWorld* World, const FBox& Area);

private:
	/** Curbs, slabs or fill already built (saved with the level). */
	bool HasGeometry() const;

	struct FStation
	{
		FVector Pos;   // world, on the ground
		FVector Right; // world, horizontal; at a corner the miter (longer than 1), so offsets keep their width on both sides
	};

	/** Stations every Step along each segment, every spline point included (evenly spaced stations cut the corners). */
	TArray<FStation> Sample(double Step) const;
	/** Moves the spline points near house facades (magnet); W = sidewalk width. */
	void SnapToHouses(double W);
	/** Footprints (CCW, world) of the procedural houses within Reach of the spline points. */
	TArray<TArray<FVector2D>> NearbyHouses(double Reach) const;
	double GroundZ(const FVector& World) const;
	/** The curb: a lava-stone profile Width wide, from Depth below the ground to Top above it, swept through the
	 *  stations at Lateral with mitered corners; capped at the ends unless bLoop. */
	void AddCurb(FM80MeshBuffer& Out, const TArray<FStation>& St, double Lateral, double Width, double Top, double Depth, bool bLoop) const;
	/** Paves the inside of the closed spline; returns +1/-1, the side ("Right" sign) where the inside lies. */
	double BuildFill(double Top, FM80MeshBuffer& Out);
	/** The slab between Lateral -/+ Width/2 of the stations, on the ground at both edges, sides down Depth below. */
	void BuildSlab(const TArray<FStation>& St, double Lateral, double Width, double Top, double Depth, FM80MeshBuffer& Out);
	/** Top tiles, then the sides (the curb's lava stone). */
	void SetFillMaterials();
};
