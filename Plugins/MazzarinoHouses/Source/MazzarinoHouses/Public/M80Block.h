#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "M80Block.generated.h"

class USplineComponent;
class UM80HouseStyle;
class AM80House;

/**
 * A town block to fill with houses where the OSM map has none. Draw the outline with the spline
 * points (closed loop along the streets, seen from above) and press "Genera case": a ring of row
 * houses as deep as "Profondita case" is built along every side, with the corners shared, and the
 * middle is left as a courtyard. Each side becomes one Casa Mazzarino that splits itself into row
 * houses of different widths, floors and finishes. The style is copied from the nearest existing
 * house unless one is chosen here. Pressing again replaces the houses made by this block; houses
 * edited by hand afterwards are ordinary houses (change their "Id lotto" to keep them apart).
 */
UCLASS(meta = (DisplayName = "Isolato da riempire (Mazzarino)"))
class MAZZARINOHOUSES_API AM80Block : public AActor
{
	GENERATED_BODY()

public:
	AM80Block();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Isolato")
	TObjectPtr<USplineComponent> Outline;

	/** Depth of the houses from the street towards the courtyard (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Isolato", meta = (DisplayName = "Profondita case", ClampMin = "500", ClampMax = "3000"))
	float Depth = 1100.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Isolato", meta = (DisplayName = "Piani minimi", ClampMin = "1", ClampMax = "7"))
	int32 FloorsMin = 2;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Isolato", meta = (DisplayName = "Piani massimi", ClampMin = "1", ClampMax = "7"))
	int32 FloorsMax = 3;

	/** Empty = copy the style of the nearest existing house. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Isolato", meta = (DisplayName = "Stile (vuoto = come la casa piu vicina)"))
	TObjectPtr<UM80HouseStyle> Style;

	/** Sides shorter than this are joined to the side before them (cut corners, small bends). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Isolato", meta = (DisplayName = "Lato minimo per una casa", ClampMin = "100"))
	float MinSide = 400.f;

	/** Leave out the parts of the ring that fall on an existing house. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Isolato", meta = (DisplayName = "Salta dove ci sono gia case"))
	bool bSkipExisting = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Isolato", meta = (DisplayName = "Variante (seed)"))
	int32 Seed = 1;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Isolato", meta = (DisplayName = "Esito"))
	FString Info;

	/** Builds (or rebuilds) the houses of the block. */
	UFUNCTION(BlueprintCallable, CallInEditor, Category = "Isolato", meta = (DisplayName = "Genera case"))
	void Generate();

	/** Deletes the houses made by this block. */
	UFUNCTION(BlueprintCallable, CallInEditor, Category = "Isolato", meta = (DisplayName = "Elimina case generate"))
	void RemoveHouses();

	/** Outline in world XY, counter-clockwise. */
	UFUNCTION(BlueprintCallable, Category = "Isolato")
	TArray<FVector2D> GetOutlineWorld2D() const;

private:
	/** "Id lotto" prefix of the houses made by this block. */
	FString LotPrefix() const;
	/** One polygon per side; the first edge of each is on the street. */
	TArray<TArray<FVector2D>> MakeLots(double& OutDepth) const;
};
