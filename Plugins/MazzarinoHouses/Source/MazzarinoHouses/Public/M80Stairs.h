#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "M80Stairs.generated.h"

class USplineComponent;
class UDynamicMeshComponent;
class UMaterialInterface;
struct FM80MeshBuffer;

UENUM(BlueprintType)
enum class EM80StairsKind : uint8
{
	Steps UMETA(DisplayName = "Scalinata (gradini)"),
	SteppedPath UMETA(DisplayName = "Cordonata (marciapiede a gradoni)"),
	FenceOnly UMETA(DisplayName = "Solo muretto / staccionata")
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
	Lava UMETA(DisplayName = "Pietra lavica")
};

UENUM(BlueprintType)
enum class EM80FenceKind : uint8
{
	None UMETA(DisplayName = "Nessuna"),
	WroughtIron UMETA(DisplayName = "Ferro battuto"),
	IronTube UMETA(DisplayName = "Ferro tubolare"),
	Wood UMETA(DisplayName = "Legno"),
	Cane UMETA(DisplayName = "Canne (rustica)")
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

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (DisplayName = "Tipo"))
	EM80StairsKind Kind = EM80StairsKind::Steps;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (DisplayName = "Larghezza (cm)", ClampMin = "40", ClampMax = "2000"))
	float WidthCm = 200.f;

	/** Rise of each step. A stair spreads its steps evenly over the spline: the real rise is shown below. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (DisplayName = "Altezza gradino (cm)", ClampMin = "4", ClampMax = "40"))
	float RiserCm = 16.f;

	/** Depth of the steps of a stair. When the spline is longer than the steps need, the extra length
	 *  becomes landings spread along the flight. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (DisplayName = "Pedata scalinata (cm)", ClampMin = "22", ClampMax = "80", EditCondition = "Kind == EM80StairsKind::Steps"))
	float StepTreadCm = 33.f;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Scalinata", meta = (DisplayName = "Pianerottoli (calcolati)"))
	int32 LandingCount = 0;

	/** Depth of each step of a "cordonata"; the slope left over between the steps tilts the treads. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (DisplayName = "Profondità gradino cordonata (cm)", ClampMin = "40", ClampMax = "1000", EditCondition = "Kind == EM80StairsKind::SteppedPath"))
	float TreadCm = 150.f;

	/** Lava-stone band along the edge of each tread (the rest is the tread finish). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (DisplayName = "Bordo in pietra lavica (cm)", ClampMin = "0", ClampMax = "100"))
	float NosingCm = 30.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (DisplayName = "Finitura pedata"))
	EM80TreadFinish TreadFinish = EM80TreadFinish::Setts;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (DisplayName = "Inizio sul terreno"))
	bool bStartOnGround = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (DisplayName = "Fine sul terreno"))
	bool bEndOnGround = true;

	/** Solid steps down to the terrain; off = a slab stair (a flight on a wall or over a void). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (DisplayName = "Pieno fino a terra"))
	bool bFillToGround = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (DisplayName = "Spessore soletta (cm)", ClampMin = "8", ClampMax = "60", EditCondition = "!bFillToGround"))
	float SlabCm = 20.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Muri", meta = (DisplayName = "Muri laterali"))
	EM80StairsSide WallSides = EM80StairsSide::None;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Muri", meta = (DisplayName = "Finitura muro"))
	EM80StairsWallFinish WallFinish = EM80StairsWallFinish::Stone;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Muri", meta = (DisplayName = "Spessore muro (cm)", ClampMin = "10", ClampMax = "150"))
	float WallThicknessCm = 40.f;

	/** Height of the wall above the steps (0 = flush with the edge of the steps, a retaining wall). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Muri", meta = (DisplayName = "Altezza muro sopra i gradini (cm)", ClampMin = "0", ClampMax = "400"))
	float WallHeightCm = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Muri", meta = (DisplayName = "Copertina in pietra lavica"))
	bool bWallCoping = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Staccionata", meta = (DisplayName = "Tipo staccionata"))
	EM80FenceKind FenceKind = EM80FenceKind::None;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Staccionata", meta = (DisplayName = "Lato staccionata"))
	EM80StairsSide FenceSides = EM80StairsSide::Both;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Staccionata", meta = (DisplayName = "Altezza staccionata (cm)", ClampMin = "40", ClampMax = "250"))
	float FenceHeightCm = 100.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Staccionata", meta = (DisplayName = "Distanza montanti (cm)", ClampMin = "50", ClampMax = "400"))
	float PostSpacingCm = 150.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scalinata", meta = (DisplayName = "Collisione"))
	bool bCollision = true;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Scalinata", meta = (DisplayName = "Gradini (calcolati)"))
	int32 StepCount = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Scalinata", meta = (DisplayName = "Alzata reale (cm)"))
	float RealRiserCm = 0.f;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Scalinata", meta = (DisplayName = "Pedata reale (cm)"))
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

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Materiali", meta = (DisplayName = "Legno"))
	TObjectPtr<UMaterialInterface> WoodMaterial;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Materiali", meta = (DisplayName = "Canne"))
	TObjectPtr<UMaterialInterface> CaneMaterial;

	UFUNCTION(BlueprintCallable, CallInEditor, Category = "Scalinata", meta = (DisplayName = "Ricostruisci"))
	void Rebuild();

private:
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

	TArray<FTread> Treads;
	TArray<FVector2D> EdgeLine; // (distance, z)
	double Length = 0.0;
	double SurfaceStartZ = 0.0, SurfaceEndZ = 0.0;
};
