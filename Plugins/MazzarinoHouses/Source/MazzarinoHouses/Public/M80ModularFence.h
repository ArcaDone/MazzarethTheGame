#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "M80ModularFence.generated.h"

class USplineComponent;
class UInstancedStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;

/**
 * Fence drawn with a spline from two meshes of a building (a pillar and a railing panel, e.g. the hospital's):
 * every straight stretch between two spline points is cut into bays as long as one pillar plus the panels per bay,
 * stretched a little so they fill it exactly. Each bay stands on a low wall laid on the ground at its own height
 * (on a slope the wall steps down bay by bay, as the hospital's did), with a coping on top; the pillars stand on a
 * block as high as the higher of their two bays. The spline points are corners (linear): draw it along the lot.
 * Every piece is instanced (one draw per kind), so long fences stay cheap.
 */
UCLASS(meta = (DisplayName = "Recinzione modulare (Mazzarino)"))
class MAZZARINOHOUSES_API AM80ModularFence : public AActor
{
	GENERATED_BODY()

public:
	AM80ModularFence();

	virtual void OnConstruction(const FTransform& Transform) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Recinzione")
	TObjectPtr<USplineComponent> Path;

	/** Pillar between bays (pivot at the middle of its base). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Recinzione", meta = (DisplayName = "Pilastro"))
	TObjectPtr<UStaticMesh> PillarMesh;

	/** Railing panel (pivot at the middle of its base, length along X). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Recinzione", meta = (DisplayName = "Pannello"))
	TObjectPtr<UStaticMesh> PanelMesh;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Recinzione", meta = (DisplayName = "Pannelli per campata", ClampMin = "1", ClampMax = "8"))
	int32 PanelsPerBay = 2;

	/** Chiusa: the last point joins the first (a whole lot). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Recinzione", meta = (DisplayName = "Chiusa"))
	bool bClosedLoop = false;

	/** A pillar also at the first and last point of an open fence (and at every corner). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Recinzione", meta = (DisplayName = "Pilastri alle estremità"))
	bool bEndPillars = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Muretto", meta = (DisplayName = "Muretto"))
	bool bWall = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Muretto", meta = (DisplayName = "Altezza (cm)", ClampMin = "0", ClampMax = "400", EditCondition = "bWall"))
	float WallHeightCm = 90.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Muretto", meta = (DisplayName = "Spessore (cm)", ClampMin = "5", ClampMax = "150", EditCondition = "bWall"))
	float WallThicknessCm = 45.f;

	/** How far the wall goes into the ground (it never shows a gap on a slope). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Muretto", meta = (DisplayName = "Interrato (cm)", ClampMin = "0", ClampMax = "200", EditCondition = "bWall"))
	float WallBuriedCm = 40.f;

	/** Empty: the pillar's own material. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Muretto", meta = (DisplayName = "Materiale muretto", EditCondition = "bWall"))
	TObjectPtr<UMaterialInterface> WallMaterial;

	/** Empty: the wall's material. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Muretto", meta = (DisplayName = "Materiale copertina", EditCondition = "bWall"))
	TObjectPtr<UMaterialInterface> CopingMaterial;

	/** Every bay on the ground under its middle (steps on slopes); off: all at the height of the spline. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Muretto", meta = (DisplayName = "Segue il terreno"))
	bool bFollowGround = true;

	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Recinzione", meta = (DisplayName = "Rifai"))
	void Rebuild();

	UPROPERTY(VisibleAnywhere, Category = "Recinzione", meta = (DisplayName = "Campate"))
	int32 BayCount = 0;

private:
	UPROPERTY()
	TObjectPtr<UInstancedStaticMeshComponent> Pillars;
	UPROPERTY()
	TObjectPtr<UInstancedStaticMeshComponent> Panels;
	UPROPERTY()
	TObjectPtr<UInstancedStaticMeshComponent> Walls;
	UPROPERTY()
	TObjectPtr<UInstancedStaticMeshComponent> Copings;

	double GroundZ(const FVector& World) const;
};
