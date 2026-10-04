#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "M80ExclusionZone.generated.h"

class USplineComponent;

/**
 * Area where the procedural houses are switched off, to make room for hand-made buildings.
 * Draw the outline with the spline points (closed loop, seen from above): every Casa Mazzarino whose
 * centre falls inside disappears (mesh, collision, plants) and comes back when the zone is moved,
 * turned off or deleted. District imports and street details skip the area too.
 */
UCLASS(meta = (DisplayName = "Zona senza case procedurali (Mazzarino)"))
class MAZZARINOHOUSES_API AM80ExclusionZone : public AActor
{
	GENERATED_BODY()

public:
	AM80ExclusionZone();

	virtual void OnConstruction(const FTransform& Transform) override;
	virtual void Destroyed() override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Zona")
	TObjectPtr<USplineComponent> Outline;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Zona", meta = (DisplayName = "Attiva"))
	bool bEnabled = true;

	/** Outline in world XY. */
	UFUNCTION(BlueprintCallable, Category = "Zona")
	TArray<FVector2D> GetOutlineWorld2D() const;

	/** True when Location (XY) is inside an enabled zone of the world. */
	UFUNCTION(BlueprintCallable, Category = "Zona", meta = (WorldContext = "WorldContext"))
	static bool IsPointExcluded(const UObject* WorldContext, FVector Location);

	/** Shows or hides every house of the world according to the zones (editor refresh). */
	UFUNCTION(BlueprintCallable, CallInEditor, Category = "Zona", meta = (DisplayName = "Aggiorna case"))
	void RefreshHouses();

private:
	bool bDying = false;
};
