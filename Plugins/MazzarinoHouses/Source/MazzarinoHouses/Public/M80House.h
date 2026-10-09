#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "M80HouseTypes.h"
#include "M80House.generated.h"

class USplineComponent;
class UDynamicMeshComponent;
class UInstancedStaticMeshComponent;
class UStaticMeshComponent;
class UStaticMesh;

/** A prop or plant instance of the last build, saved with the level so baked houses keep them. */
USTRUCT()
struct FM80SavedProp
{
	GENERATED_BODY()
	UPROPERTY()
	TObjectPtr<UStaticMesh> Mesh;
	UPROPERTY()
	FTransform Transform;
	UPROPERTY()
	bool bPlant = false;
	/** Part of the building (noble balcony): collides and is not culled with distance. */
	UPROPERTY()
	bool bArchitecture = false;
};

/** One house of a row, cut from the lot footprint. */
struct FM80Unit
{
	TArray<FVector2D> Footprint;
	TArray<EM80EdgeKind> Kinds;
	int32 Front = 0;
};

/**
 * A procedural Mazzarino house. Edit the footprint spline points (closed loop) or any parameter
 * and the house rebuilds: floors, facades, roof and terrain contact are all derived live.
 */
UCLASS(meta = (DisplayName = "Casa Mazzarino (procedurale)"))
class MAZZARINOHOUSES_API AM80House : public AActor
{
	GENERATED_BODY()

public:
	AM80House();

	virtual void OnConstruction(const FTransform& Transform) override;
	virtual void BeginPlay() override;

	/** True when nothing would be drawn: no baked mesh (e.g. not in this checkout) and an empty preview. */
	UFUNCTION(BlueprintCallable, Category = "Casa")
	bool NeedsRebuild() const;

	/** Footprint: closed loop of linear points, local space. Move points to reshape the house. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Casa")
	TObjectPtr<USplineComponent> Footprint;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Casa")
	TObjectPtr<UDynamicMeshComponent> Shell;

	/** Final Nanite version of the house, shown after "Cuoci". Any edit returns to the live preview. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Casa")
	TObjectPtr<UStaticMeshComponent> Baked;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Casa", meta = (ShowOnlyInnerProperties))
	FM80HouseParams House;

	/** Switch this house off (e.g. replaced by a hand-made building). See also "Zona senza case procedurali". */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Casa", meta = (DisplayName = "Disattiva (sostituita da un edificio fatto a mano)"))
	bool bDisabled = false;

	/** True when the house is switched off or its centre lies in an enabled exclusion zone. */
	UFUNCTION(BlueprintCallable, Category = "Casa")
	bool IsExcluded() const;

	/** Hides or shows the house according to IsExcluded(); rebuilds it if it comes back without a mesh. */
	UFUNCTION(BlueprintCallable, Category = "Casa")
	void ApplyExclusion();

	/** Rebuild while dragging points and editing values. Turn off when editing many houses at once. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Casa", meta = (DisplayName = "Rigenera mentre modifico"))
	bool bLiveRebuild = true;

	/** OSM / catalogue id of the lot. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Riferimento", meta = (DisplayName = "Id lotto"))
	FString LotId;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Riferimento", meta = (DisplayName = "Stato generazione"))
	FString BuildInfo;

	/** Edge kinds actually used by the last build (after automatic detection). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Riferimento", meta = (DisplayName = "Lati rilevati"))
	TArray<EM80EdgeKind> ResolvedEdgeKinds;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Riferimento", meta = (DisplayName = "Facciata principale usata"))
	int32 ResolvedFrontEdge = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Riferimento", meta = (DisplayName = "Case nel lotto"))
	int32 UnitCount = 1;

	UFUNCTION(BlueprintCallable, CallInEditor, Category = "Casa", meta = (DisplayName = "Rigenera"))
	void Rebuild();

	/** Rebuilds this house and every house sharing a wall with it. */
	UFUNCTION(BlueprintCallable, CallInEditor, Category = "Casa", meta = (DisplayName = "Rigenera con i vicini"))
	void RebuildWithNeighbours();

	/** Places the actor at the footprint centroid and stores the points in local space. */
	UFUNCTION(BlueprintCallable, Category = "Casa")
	void SetFootprintWorld(const TArray<FVector>& WorldPoints);

	/** Footprint in world XY, cleaned and counter-clockwise. */
	UFUNCTION(BlueprintCallable, Category = "Casa")
	TArray<FVector2D> GetFootprintWorld2D() const;

	/** Shows a baked static mesh instead of the live preview and frees the preview mesh. */
	UFUNCTION(BlueprintCallable, Category = "Casa")
	void ApplyBakedMesh(UStaticMesh* Mesh);

	UFUNCTION(BlueprintCallable, Category = "Casa")
	bool IsBaked() const;

	/** Local-space eave height of the last build, used by neighbours. */
	double GetEaveZ() const { return LastEaveZ; }

private:
	UPROPERTY(Transient)
	TArray<TObjectPtr<UInstancedStaticMeshComponent>> PropComponents;

	UPROPERTY()
	TArray<FM80SavedProp> SavedProps;

	/** Recreates the instanced components from SavedProps (one per mesh). */
	void RefreshProps();

	/** Visibility and collision of preview, baked mesh and props for an excluded or active house. */
	void SetExcludedVisuals(bool bExcluded);

	UPROPERTY()
	double LastEaveZ = 0;

	/** Hash of everything the build depends on; unchanged inputs skip the rebuild (keeps baked houses baked on load). */
	UPROPERTY()
	uint32 LastInputHash = 0;

	uint32 ComputeInputHash() const;

	struct FGroundGrid
	{
		FVector2D Origin;
		double Step = 100;
		int32 NX = 0, NY = 0;
		TArray<double> Z;
		double Sample(const FVector2D& World) const;
	};

	TArray<FVector2D> LocalFootprint() const;
	FGroundGrid SampleGround(const TArray<FVector2D>& World2D) const;
	void ResolveEdges(const TArray<FVector2D>& Local, TArray<EM80EdgeKind>& OutKinds, int32& OutFront) const;
	void SplitIntoUnits(const TArray<FVector2D>& Local, const TArray<EM80EdgeKind>& Kinds, int32 Front, TArray<FM80Unit>& OutUnits) const;
	void ApplyMaterials(const UM80HouseStyle* Style);
};
