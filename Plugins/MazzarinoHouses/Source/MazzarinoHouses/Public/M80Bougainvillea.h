#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "M80Bougainvillea.generated.h"

class UDynamicMeshComponent;
class UMaterialInterface;
class USplineComponent;
class UStaticMesh;
class UStaticMeshComponent;
namespace UE::Geometry { class FDynamicMesh3; }

UENUM(BlueprintType)
enum class EM80BougainvilleaColour : uint8
{
	Magenta UMETA(DisplayName = "Magenta"),
	Viola UMETA(DisplayName = "Viola"),
	Arancione UMETA(DisplayName = "Arancione"),
	Rosso UMETA(DisplayName = "Rosso"),
};

/**
 * A bougainvillea grown procedurally along a spline: the spline is the main stem (from the root up a wall, a pole
 * or a wire), branches open from it and from each other, droop under their weight and slide over whatever they
 * touch; leaves and flowers (bracts in threes around the small white flowers) are folded transparent cards cut from
 * texture atlases, so a plant stays light. One colour for the whole plant.
 * With "Rampicante" the branches hold on to the surfaces they meet and fall over the edges; without it they grow
 * free and only avoid passing through things.
 * "Passaggio libero" cuts the branches that hang free below that height (streets stay passable); "Filo di sostegno"
 * draws a thin cable under the free stretches of the stem (a plant trained across a street).
 * "Cuoci" (M80EditorLibrary.BakeBougainvillea) turns the plant into a static mesh with three levels of detail, which
 * World Partition HLODs can use; any edit returns to the live preview.
 * Materials: /Game/Mazzarino80/Vegetazione/Bouganvillea (Scripts/m80_bouganvillea_materiali.py).
 */
UCLASS(meta = (DisplayName = "Bouganvillea (Mazzarino)"))
class MAZZARINOHOUSES_API AM80Bougainvillea : public AActor
{
	GENERATED_BODY()

public:
	AM80Bougainvillea();

	virtual void OnConstruction(const FTransform& Transform) override;
	/** A plant whose baked mesh is missing (not in this checkout) and has no preview grows again. */
	virtual void BeginPlay() override;

	/** The main stem, from the root. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Bouganvillea", meta = (DisplayName = "Fusto"))
	TObjectPtr<USplineComponent> Stem;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Bouganvillea")
	TObjectPtr<UDynamicMeshComponent> Mesh;

	/** Baked version of the plant (static mesh with LODs), shown instead of the live preview. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Bouganvillea")
	TObjectPtr<UStaticMeshComponent> Baked;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Pianta", meta = (DisplayName = "Colore"))
	EM80BougainvilleaColour Colour = EM80BougainvilleaColour::Magenta;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Pianta", meta = (DisplayName = "Variante (seed)"))
	int32 Seed = 1;

	/** Radius of the trunk at the root (cm); it thins towards the end of the spline. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rami", meta = (DisplayName = "Raggio tronco", ClampMin = "0.5", ClampMax = "20"))
	float TrunkRadius = 3.5f;

	/** Bare part of the trunk from the root (0-1 of the spline): no branches, leaves or flowers there. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rami", meta = (DisplayName = "Tronco nudo", ClampMin = "0", ClampMax = "0.9"))
	float BareTrunk = 0.25f;

	/** Side branches per metre of stem or branch. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rami", meta = (DisplayName = "Rami per metro", ClampMin = "0", ClampMax = "12"))
	float BranchesPerMetre = 6.f;

	/** Length of the branches that leave the trunk (cm); their own branches are shorter. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rami", meta = (DisplayName = "Lunghezza rami", ClampMin = "10", ClampMax = "600"))
	float BranchLength = 140.f;

	/** How many times branches split again (1 = branches only from the trunk). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rami", meta = (DisplayName = "Livelli di rami", ClampMin = "1", ClampMax = "3"))
	int32 BranchLevels = 3;

	/** Angle between a branch and the one it grows from (degrees). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rami", meta = (DisplayName = "Apertura rami", ClampMin = "5", ClampMax = "90"))
	float BranchAngle = 50.f;

	/** How much branches fall under their weight (bougainvillea cascades). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rami", meta = (DisplayName = "Ricadenza", ClampMin = "0", ClampMax = "1"))
	float Droop = 0.55f;

	/** How crooked the branches grow. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rami", meta = (DisplayName = "Irregolarita", ClampMin = "0", ClampMax = "1"))
	float Wander = 0.35f;

	/** Leaves: 1 = a full plant, 0 = none, 2 = very thick. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Foglie e fiori", meta = (DisplayName = "Quantita foglie", ClampMin = "0", ClampMax = "3"))
	float LeafAmount = 1.f;

	/** Flowers: 1 = in full bloom, 0 = none. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Foglie e fiori", meta = (DisplayName = "Quantita fiori", ClampMin = "0", ClampMax = "3"))
	float FlowerAmount = 1.f;

	/** 0 = flowers all along the branches, 1 = only towards their tips. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Foglie e fiori", meta = (DisplayName = "Fiori verso le punte", ClampMin = "0", ClampMax = "1"))
	float FlowersAtTips = 0.6f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Foglie e fiori", meta = (DisplayName = "Dimensione foglie (cm)", ClampMin = "1", ClampMax = "30"))
	float LeafSize = 7.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Foglie e fiori", meta = (DisplayName = "Dimensione brattee (cm)", ClampMin = "1", ClampMax = "20"))
	float BractSize = 4.5f;

	/** Leaves folded along the midrib (4 triangles each) instead of flat (2): rounder up close, twice the leaves' cost. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Foglie e fiori", meta = (DisplayName = "Foglie piegate"))
	bool bFoldedLeaves = false;

	/** Branches hanging free (not lying on a surface) stop at this height above the root (cm); 0 = no limit. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rami", meta = (DisplayName = "Passaggio libero (cm)", ClampMin = "0", ClampMax = "1500"))
	float ClearHeight = 0.f;

	/** Thin cable under the stretches of the stem that touch nothing (a plant trained across a street). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rami", meta = (DisplayName = "Filo di sostegno"))
	bool bSupportWire = false;

	/** Climbing plant: branches hold on to the walls, poles and roofs they meet and fall over their edges. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rampicante", meta = (DisplayName = "Rampicante"))
	bool bClimbing = true;

	/** How far a branch feels for a surface to hold on to (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rampicante", meta = (DisplayName = "Distanza di presa", ClampMin = "5", ClampMax = "300", EditCondition = "bClimbing"))
	float ClimbReach = 60.f;

	/** Gap between a branch and the surface it lies on (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rampicante", meta = (DisplayName = "Distacco dal muro", ClampMin = "0", ClampMax = "30"))
	float WallGap = 2.f;

	/** Optional overrides of the default materials. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Materiali", meta = (DisplayName = "Corteccia"))
	TObjectPtr<UMaterialInterface> BarkMaterial;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Materiali", meta = (DisplayName = "Foglie"))
	TObjectPtr<UMaterialInterface> LeafMaterial;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Materiali", meta = (DisplayName = "Brattee (sostituisce il colore)"))
	TObjectPtr<UMaterialInterface> BractMaterial;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Materiali", meta = (DisplayName = "Fiorellini"))
	TObjectPtr<UMaterialInterface> FlowerMaterial;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Pianta", meta = (DisplayName = "Stato"))
	FString BuildInfo;

	UFUNCTION(BlueprintCallable, CallInEditor, Category = "Pianta", meta = (DisplayName = "Rigenera"))
	void Rebuild();

	/** Shows Mesh (a bake of this plant) instead of the live preview, which is freed. */
	UFUNCTION(BlueprintCallable, Category = "Pianta")
	void ApplyBakedMesh(UStaticMesh* InMesh);

	UFUNCTION(BlueprintCallable, Category = "Pianta")
	bool IsBaked() const;

	/**
	 * The plant at a level of detail: 0 full, 1 fewer and larger cards and no finest twigs, 2 for far away. The
	 * plant grows the same at every level (same seed). Returns a summary.
	 */
	FString BuildLOD(int32 Lod, UE::Geometry::FDynamicMesh3& OutMesh);

	/** Materials of the four slots: bark, leaves, bracts (of the chosen colour), small flowers. */
	TArray<UMaterialInterface*> GetSlotMaterials() const;

private:
	/** Hash of everything the plant grows from (parameters, spline, placement), to keep a bake valid. */
	int32 ComputeInputHash() const;

	UPROPERTY()
	int32 BakedHash = 0;
};
