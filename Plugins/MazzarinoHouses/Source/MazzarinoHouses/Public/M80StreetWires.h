#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "M80StreetWires.generated.h"

class UDynamicMeshComponent;
class UMaterialInterface;

/**
 * Power and phone cables strung across the streets between facing houses, like the tangles of
 * wires in 1980s Mazzarino. Place one per district: it reads every Casa Mazzarino within Radius.
 */
UCLASS(meta = (DisplayName = "Fili tra le case (Mazzarino)"))
class MAZZARINOHOUSES_API AM80StreetWires : public AActor
{
	GENERATED_BODY()

public:
	AM80StreetWires();

	virtual void OnConstruction(const FTransform& Transform) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Fili")
	TObjectPtr<UDynamicMeshComponent> Wires;

	/** Only houses whose centre is within this distance of the actor (cm). 0 = whole level. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Fili", meta = (DisplayName = "Raggio", ClampMin = "0"))
	float Radius = 0.f;

	/** Chance that two facing houses are linked. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Fili", meta = (DisplayName = "Densita", ClampMin = "0", ClampMax = "1"))
	float Density = 0.6f;

	/** Street widths that get crossed (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Fili", meta = (DisplayName = "Larghezza strada minima"))
	float MinSpan = 300.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Fili", meta = (DisplayName = "Larghezza strada massima"))
	float MaxSpan = 1800.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Fili", meta = (DisplayName = "Variante (seed)"))
	int32 Seed = 1;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Fili", meta = (DisplayName = "Materiale"))
	TObjectPtr<UMaterialInterface> WireMaterial;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Fili", meta = (DisplayName = "Stato"))
	FString BuildInfo;

	UFUNCTION(BlueprintCallable, CallInEditor, Category = "Fili", meta = (DisplayName = "Rigenera"))
	void Rebuild();
};
