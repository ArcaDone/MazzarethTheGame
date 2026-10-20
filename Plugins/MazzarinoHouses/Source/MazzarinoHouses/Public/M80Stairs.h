#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "M80Stairs.generated.h"

class USplineComponent;
class UDynamicMeshComponent;
class UInstancedStaticMeshComponent;
class UMaterialInterface;
struct FM80MeshBuffer;

UENUM(BlueprintType)
enum class EM80StairsKind : uint8
{
	Steps UMETA(DisplayName = "Scalinata (gradini)"),
	SteppedPath UMETA(DisplayName = "Cordonata (marciapiede a gradoni)"),
	FenceOnly UMETA(DisplayName = "Solo muretto / staccionata"),
	WallFromSpline UMETA(DisplayName = "Muro dalla spline fino a terra"),
	WallFromGround UMETA(DisplayName = "Muro dal terreno (altezza scelta)")
};

UENUM(BlueprintType)
enum class EM80StairsSide : uint8
{
	None UMETA(DisplayName = "Nessuno"),
	Left UMETA(DisplayName = "Sinistra"),
	Right UMETA(DisplayName = "Destra"),
	Both UMETA(DisplayName = "Entrambi")
};

UENUM(BlueprintType)
enum class EM80TreadFinish : uint8
{
	Setts UMETA(DisplayName = "Basolato (cubetti lavici)"),
	Lava UMETA(DisplayName = "Pietra lavica piena"),
	Cement UMETA(DisplayName = "Cemento")
};

UENUM(BlueprintType)
enum class EM80StairsWallFinish : uint8
{
	Stone UMETA(DisplayName = "Conci di pietra"),
	Concrete UMETA(DisplayName = "Cemento"),
	Lava UMETA(DisplayName = "Pietra lavica"),
	DryStone UMETA(DisplayName = "Pietra a secco (muretto di campagna)")
};

UENUM(BlueprintType)
enum class EM80FenceKind : uint8
{
	None UMETA(DisplayName = "Nessuna"),
	WroughtIron UMETA(DisplayName = "Ferro battuto"),
	IronTube UMETA(DisplayName = "Ferro tubolare"),
	Wood UMETA(DisplayName = "Legno"),
	Cane UMETA(DisplayName = "Canne (rustica)"),
	MadonnaRailing UMETA(DisplayName = "Ringhiera della Madonna (pilastrini e tubi)"),
	RedIronRails UMETA(DisplayName = "Ferro a traverse (rosso ruggine)")
};

/**
 * Steps, stepped paths ("cordonata") and stairs drawn with a spline (the walking centre line, from the
 * first point to the last; it may go up or down and turn), plus side walls and fences, in the lava stone
 * of the town's streets.
 * Each step has a lava-stone edge and riser, the rest of the tread is setts (or lava, or cement).
 * The ends sit on the ground (landscape) like the sidewalk, or at the height of the spline points; the
 * steps are spread evenly between them. "Pieno fino a terra" fills the space under the steps down to
 * the terrain; otherwise the stair is a slab (with its walls, if any, still reaching the ground).
 * "Solo muretto / staccionata" builds only walls and fences along the ground.
 * "Muro dalla spline fino a terra" builds one wall centred on the spline, its top at the height of the spline
 * (plus "Altezza muro"), down into the terrain: a retaining wall or a parapet that follows the drawn line.
 * "Muro dal terreno (altezza scelta)" builds one wall centred on the spline that stands on the ground and is
 * "Altezza muro" tall all along (the spline's own height does not matter): a field wall that follows the terrain.
 * "Pietra a secco" is the dry-stone wall of the countryside, built of real stones (8 models, Nanite) laid in
 * courses on both faces and across the top, over a dark core; "Profilo alto irregolare" makes any wall's top go up
 * and down stone by stone (no coping then; a dry-stone wall never has one).
 * The Madonna's railing (stone posts and iron rails, the model of the Madonna's villa) is a fence kind: it stands on
 * any wall, or on the ground with no wall.
 * "Destra" is the right-hand side walking along the spline from the first point.
 */
UCLASS(meta = (DisplayName = "Scalinata (Mazzarino)"))
class MAZZARINOHOUSES_API AM80Stairs : public AActor
{
	GENERATED_BODY()

public:
	AM80Stairs();

	virtual void OnConstruction(const FTransform& Transform) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Scalinata")
	TObjectPtr<USplineComponent> Path;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Scalinata")
	TObjectPtr<UDynamicMeshComponent> Mesh;

	/** Posts and bays of rails of the Madonna's railing (models from the Madonna's villa). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Staccionata")
	TObjectPtr<UInstancedStaticMeshComponent> RailingPosts;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Staccionata")
	TObjectPtr<UInstancedStaticMeshComponent> RailingBays;

	/** The stones of a dry-stone wall, one component per stone model (Kit/Stairs/SM_M80_PietraSecco_N). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Muri")
	TArray<TObjectPtr<UInstancedStaticMeshComponent>> DryStones;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (DisplayName = "Tipo"))
	EM80StairsKind Kind = EM80StairsKind::Steps;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (EditCondition = "Kind != EM80StairsKind::WallFromSpline && Kind != EM80StairsKind::WallFromGround", EditConditionHides, DisplayName = "Larghezza (cm)", ClampMin = "40", ClampMax = "2000"))
	float WidthCm = 200.f;

	/** Rise of each step. A stair spreads its steps evenly over the spline: the real rise is shown below. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (EditCondition = "Kind != EM80StairsKind::FenceOnly && Kind != EM80StairsKind::WallFromSpline && Kind != EM80StairsKind::WallFromGround", EditConditionHides, DisplayName = "Altezza gradino (cm)", ClampMin = "4", ClampMax = "40"))
	float RiserCm = 16.f;

	/** Depth of the steps of a stair. When the spline is longer than the steps need, the extra length
	 *  becomes landings spread along the flight. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (EditCondition = "Kind == EM80StairsKind::Steps", EditConditionHides, DisplayName = "Pedata scalinata (cm)", ClampMin = "22", ClampMax = "80"))
	float StepTreadCm = 33.f;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Scalinata", meta = (EditCondition = "Kind != EM80StairsKind::FenceOnly && Kind != EM80StairsKind::WallFromSpline && Kind != EM80StairsKind::WallFromGround", EditConditionHides, DisplayName = "Pianerottoli (calcolati)"))
	int32 LandingCount = 0;

	/** Depth of each step of a "cordonata"; the slope left over between the steps tilts the treads. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (EditCondition = "Kind == EM80StairsKind::SteppedPath", EditConditionHides, DisplayName = "Profondità gradino cordonata (cm)", ClampMin = "40", ClampMax = "1000"))
	float TreadCm = 150.f;

	/** Lava-stone band along the edge of each tread (the rest is the tread finish). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (EditCondition = "Kind != EM80StairsKind::FenceOnly && Kind != EM80StairsKind::WallFromSpline && Kind != EM80StairsKind::WallFromGround", EditConditionHides, DisplayName = "Bordo in pietra lavica (cm)", ClampMin = "0", ClampMax = "100"))
	float NosingCm = 30.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (EditCondition = "Kind != EM80StairsKind::FenceOnly && Kind != EM80StairsKind::WallFromSpline && Kind != EM80StairsKind::WallFromGround", EditConditionHides, DisplayName = "Finitura pedata"))
	EM80TreadFinish TreadFinish = EM80TreadFinish::Setts;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (EditCondition = "Kind != EM80StairsKind::FenceOnly && Kind != EM80StairsKind::WallFromSpline && Kind != EM80StairsKind::WallFromGround", EditConditionHides, DisplayName = "Inizio sul terreno"))
	bool bStartOnGround = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (EditCondition = "Kind != EM80StairsKind::FenceOnly && Kind != EM80StairsKind::WallFromSpline && Kind != EM80StairsKind::WallFromGround", EditConditionHides, DisplayName = "Fine sul terreno"))
	bool bEndOnGround = true;

	/** Solid steps down to the terrain; off = a slab stair (a flight on a wall or over a void). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (EditCondition = "Kind != EM80StairsKind::FenceOnly && Kind != EM80StairsKind::WallFromSpline && Kind != EM80StairsKind::WallFromGround", EditConditionHides, DisplayName = "Pieno fino a terra"))
	bool bFillToGround = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (EditCondition = "Kind != EM80StairsKind::FenceOnly && Kind != EM80StairsKind::WallFromSpline && Kind != EM80StairsKind::WallFromGround && !bFillToGround", EditConditionHides, DisplayName = "Spessore soletta (cm)", ClampMin = "8", ClampMax = "60"))
	float SlabCm = 20.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Muri", meta = (EditCondition = "Kind != EM80StairsKind::WallFromSpline && Kind != EM80StairsKind::WallFromGround", EditConditionHides, DisplayName = "Muri laterali"))
	EM80StairsSide WallSides = EM80StairsSide::None;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Muri", meta = (DisplayName = "Finitura muro"))
	EM80StairsWallFinish WallFinish = EM80StairsWallFinish::Stone;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Muri", meta = (DisplayName = "Spessore muro (cm)", ClampMin = "5", ClampMax = "600"))
	float WallThicknessCm = 40.f;

	/** Height of the wall above the steps (0 = flush with the edge of the steps, a retaining wall); for
	 *  "Muro dalla spline fino a terra", above the spline; for "Muro dal terreno", above the ground. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Muri", meta = (DisplayName = "Altezza muro sopra i gradini (cm)", ClampMin = "0", ClampMax = "400"))
	float WallHeightCm = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Muri", meta = (DisplayName = "Copertina in pietra lavica", EditCondition = "TopUnevenCm < 1 && WallFinish != EM80StairsWallFinish::DryStone", EditConditionHides))
	bool bWallCoping = true;

	/** The top of the wall goes up and down stone by stone by up to this much (0 = straight, with its coping). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Muri", meta = (DisplayName = "Profilo alto irregolare (cm)", ClampMin = "0", ClampMax = "40"))
	float TopUnevenCm = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Staccionata", meta = (DisplayName = "Tipo staccionata"))
	EM80FenceKind FenceKind = EM80FenceKind::None;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Staccionata", meta = (EditCondition = "Kind != EM80StairsKind::WallFromSpline && Kind != EM80StairsKind::WallFromGround", EditConditionHides, DisplayName = "Lato staccionata"))
	EM80StairsSide FenceSides = EM80StairsSide::Both;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Staccionata", meta = (DisplayName = "Altezza staccionata (cm)", ClampMin = "40", ClampMax = "250"))
	float FenceHeightCm = 100.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Staccionata", meta = (DisplayName = "Distanza montanti (cm)", ClampMin = "50", ClampMax = "400"))
	float PostSpacingCm = 150.f;

	/** How worn the stone, the walls and the fences are: 0 = new and square, 1 = old, hollowed and chipped. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (DisplayName = "Usura (0-1)", ClampMin = "0", ClampMax = "1"))
	float Wear = 0.7f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (DisplayName = "Collisione"))
	bool bCollision = true;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Scalinata", meta = (EditCondition = "Kind != EM80StairsKind::FenceOnly && Kind != EM80StairsKind::WallFromSpline && Kind != EM80StairsKind::WallFromGround", EditConditionHides, DisplayName = "Gradini (calcolati)"))
	int32 StepCount = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Scalinata", meta = (EditCondition = "Kind != EM80StairsKind::FenceOnly && Kind != EM80StairsKind::WallFromSpline && Kind != EM80StairsKind::WallFromGround", EditConditionHides, DisplayName = "Alzata reale (cm)"))
	float RealRiserCm = 0.f;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Scalinata", meta = (EditCondition = "Kind != EM80StairsKind::FenceOnly && Kind != EM80StairsKind::WallFromSpline && Kind != EM80StairsKind::WallFromGround", EditConditionHides, DisplayName = "Pedata reale (cm)"))
	float RealTreadCm = 0.f;

	/** Optional overrides of the kit materials. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Materiali", meta = (DisplayName = "Pietra lavica"))
	TObjectPtr<UMaterialInterface> LavaMaterial;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Materiali", meta = (DisplayName = "Pedata"))
	TObjectPtr<UMaterialInterface> TreadMaterial;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Materiali", meta = (DisplayName = "Muro"))
	TObjectPtr<UMaterialInterface> WallMaterial;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Materiali", meta = (DisplayName = "Ferro"))
	TObjectPtr<UMaterialInterface> IronMaterial;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Materiali", meta = (DisplayName = "Ferro rosso"))
	TObjectPtr<UMaterialInterface> RedIronMaterial;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Materiali", meta = (DisplayName = "Legno"))
	TObjectPtr<UMaterialInterface> WoodMaterial;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Materiali", meta = (DisplayName = "Canne"))
	TObjectPtr<UMaterialInterface> CaneMaterial;

	UFUNCTION(BlueprintCallable, CallInEditor, Category = "Scalinata", meta = (DisplayName = "Ricostruisci"))
	void Rebuild();

private:
	/** Steps already built (saved with the level). */
	bool HasGeometry() const;

	/** Height profile of the walking surface along the spline. */
	struct FTread
	{
		double D0, D1;   // distance along the spline
		double Z0, Z1;   // top at D0 and D1 (world)
		bool bEdgeAtStart; // the lava edge is at D0 (stairs going up) or at D1 (going down)
	};

	double GroundAt(const FVector& World) const;
	FVector PointAt(double D, double Lateral, double Z) const;
	FVector RightAt(double D) const;
	/** Line through the step edges (walls and fences follow it). */
	double EdgeLineZ(double D) const;
	double SurfaceZ(double D) const;

	void BuildTreads(FM80MeshBuffer& B) const;
	void BuildWall(FM80MeshBuffer& B, double Side) const;
	void BuildFence(FM80MeshBuffer& B, double Side, bool bOnWall) const;
	/** Lateral offset of the wall's inner face from the spline (negative: the wall straddles the spline). */
	double WallGap() const;
	/** One wall centred on the spline ("dalla spline" or "dal terreno"). */
	bool IsSingleWall() const;
	/** Top of the wall at D: the edge line, "Altezza muro" and the uneven stones of the top. */
	double WallTopZ(double D) const;
	/** Lays the stones of a dry-stone wall on its two faces and across its top. */
	void PlaceDryStones(double Side);
	/** True when the dry-stone wall is built of stones over a core (else its texture is on the wall itself). */
	bool HasStoneCourses() const;
	/** Height of the lava coping on the wall's top (0 without one). */
	double CopingCm() const;
	/** The Madonna's railing: a post at each end and between the bays, the rails stretched from post to post. */
	void PlaceMadonnaRailing(double Side, bool bOnWall);

	TArray<FTread> Treads;
	TArray<FVector2D> EdgeLine; // (distance, z)
	TArray<FVector2D> TopStones; // uneven top: (start distance, height) of each stone
	double Length = 0.0;
	double SurfaceStartZ = 0.0, SurfaceEndZ = 0.0;
};
