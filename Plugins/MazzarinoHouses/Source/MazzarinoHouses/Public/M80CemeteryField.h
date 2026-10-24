#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "M80CemeteryField.generated.h"

class USplineComponent;
class UHierarchicalInstancedStaticMeshComponent;
class UStaticMesh;

/** One kind of tomb of a cemetery field and how often it comes up. */
USTRUCT(BlueprintType)
struct FM80TombKind
{
	GENERATED_BODY()

	/** Pivot at the middle of its base; its long side is the tomb's length, whichever axis it lies on. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tomba", meta = (DisplayName = "Mesh"))
	TObjectPtr<UStaticMesh> Mesh;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tomba", meta = (DisplayName = "Peso", ClampMin = "0"))
	float Weight = 1.f;
};

/**
 * A field of graves drawn with a closed spline (the plot of a cemetery sector): it fills itself with tombs in rows,
 * picked at random among the kinds by their weight, as close as their own widths allow. Every tomb stands on the
 * ground under it, sunk a little and barely tilted as old graves settle, turned by a few degrees and shifted a few
 * centimetres off the row; some places stay empty. The same seed gives the same field. Rows run along the actor's X
 * turned by "Direzione file"; every N rows an aisle can be left. Each kind is instanced (one draw per kind).
 */
UCLASS(meta = (DisplayName = "Campo di tombe (Mazzarino)"))
class MAZZARINOHOUSES_API AM80CemeteryField : public AActor
{
	GENERATED_BODY()

public:
	AM80CemeteryField();

	virtual void OnConstruction(const FTransform& Transform) override;

	/** The plot's outline (closed, corners). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Campo")
	TObjectPtr<USplineComponent> Area;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Campo", meta = (DisplayName = "Tombe"))
	TArray<FM80TombKind> Kinds;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Campo", meta = (DisplayName = "Seme"))
	int32 Seed = 1980;

	/** Share of the places that get a tomb (the rest stay bare earth). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Campo", meta = (DisplayName = "Densità", ClampMin = "0", ClampMax = "1"))
	float Density = 0.85f;

	/** Direction of the rows from the actor's X (degrees). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "File", meta = (DisplayName = "Direzione file"))
	float RowYawDeg = 0.f;

	/** Free ground between two tombs of a row. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "File", meta = (DisplayName = "Spazio tra tombe (cm)", ClampMin = "0", ClampMax = "300"))
	float GapCm = 35.f;

	/** Free ground between two rows (where people walk). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "File", meta = (DisplayName = "Spazio tra file (cm)", ClampMin = "0", ClampMax = "500"))
	float RowGapCm = 70.f;

	/** Every N rows a wider aisle (0: none). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "File", meta = (DisplayName = "Vialetto ogni N file", ClampMin = "0", ClampMax = "20"))
	int32 AisleEvery = 0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "File", meta = (DisplayName = "Larghezza vialetto (cm)", ClampMin = "0", ClampMax = "600"))
	float AisleCm = 180.f;

	/** Free ground kept along the outline. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "File", meta = (DisplayName = "Margine dal bordo (cm)", ClampMin = "0", ClampMax = "500"))
	float MarginCm = 40.f;

	/** Every other row faces the other way (head to head across the walk). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "File", meta = (DisplayName = "File alterne"))
	bool bAlternateRows = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Varietà", meta = (DisplayName = "Rotazione casuale (gradi)", ClampMin = "0", ClampMax = "45"))
	float YawJitterDeg = 3.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Varietà", meta = (DisplayName = "Spostamento casuale (cm)", ClampMin = "0", ClampMax = "100"))
	float OffsetJitterCm = 12.f;

	/** Share of the tombs turned round (headstone on the other end). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Varietà", meta = (DisplayName = "Girate", ClampMin = "0", ClampMax = "1"))
	float FlipChance = 0.05f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Varietà", meta = (DisplayName = "Affondamento min (cm)", ClampMin = "0", ClampMax = "100"))
	float SinkMinCm = 2.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Varietà", meta = (DisplayName = "Affondamento max (cm)", ClampMin = "0", ClampMax = "100"))
	float SinkMaxCm = 9.f;

	/** Settling: largest lean of a tomb. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Varietà", meta = (DisplayName = "Inclinazione max (gradi)", ClampMin = "0", ClampMax = "10"))
	float TiltMaxDeg = 1.2f;

	/** Off: all on the height of the spline. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Campo", meta = (DisplayName = "Segue il terreno"))
	bool bFollowGround = true;

	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Campo", meta = (DisplayName = "Rifai"))
	void Rebuild();

	UPROPERTY(VisibleAnywhere, Category = "Campo", meta = (DisplayName = "Tombe piazzate"))
	int32 TombCount = 0;

private:
	UPROPERTY()
	TArray<TObjectPtr<UHierarchicalInstancedStaticMeshComponent>> Instances;
};
