#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "M80StreetLight.generated.h"

class UPointLightComponent;
class UStaticMeshComponent;
class UStaticMesh;

UENUM(BlueprintType)
enum class EM80LampKind : uint8
{
	Wall UMETA(DisplayName = "A muro (braccio in ferro battuto)"),
	Pole UMETA(DisplayName = "A palo (candelabro a tre luci)")
};

/**
 * A cast-iron street lamp of Mazzarino (modelled from photos, Research/Mazzarino80/Blender/m80_lamps_blender.py):
 * a lantern on a wrought-iron bracket on the facade, or the three-light candelabra of the squares.
 * Its warm light and glowing glass are switched on at dusk and off at dawn by the "Atmosfera
 * (Mazzarino)" (no cost by day: the light is hidden). Wall lamps are placed along the streets by
 * Scripts/m80_town_streetlights.py; both kinds can be placed and moved by hand (the back of a wall
 * lamp goes against the wall).
 */
UCLASS(meta = (DisplayName = "Lampione (Mazzarino)"))
class MAZZARINOGAMEPLAY_API AM80StreetLight : public AActor
{
	GENERATED_BODY()

public:
	AM80StreetLight();

	virtual void OnConstruction(const FTransform& Transform) override;
	virtual void BeginPlay() override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Lampione")
	TObjectPtr<UStaticMeshComponent> Lantern;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Lampione")
	TObjectPtr<UPointLightComponent> Light;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Lampione", meta = (DisplayName = "Tipo"))
	EM80LampKind Kind = EM80LampKind::Wall;

	/** Empty = the Mazzarino model of the chosen kind. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Lampione", meta = (DisplayName = "Modello (vuoto = quello del tipo)"))
	TObjectPtr<UStaticMesh> MeshOverride;

	/** Brightness at full night (candela, same scale as the sun of the Atmosfera). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Lampione", meta = (DisplayName = "Intensita di notte (cd)", ClampMin = "0"))
	float NightIntensity = 40.f;

	/** Pole lamps light a whole square: this multiplies brightness and reach. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Lampione", meta = (DisplayName = "Fattore palo", ClampMin = "1"))
	float PoleScale = 2.5f;

	/** Broken or switched-off lamp (a few, for realism). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Lampione", meta = (DisplayName = "Spento (guasto)"))
	bool bBroken = false;

	/** 0 = day (off), 1 = night (full brightness). Called by the Atmosfera when the light changes. */
	UFUNCTION(BlueprintCallable, Category = "Lampione")
	void SetNight(float Night);

	/** Applies the night amount to every lamp of the world. */
	static void SetNightForAll(const UWorld* World, float Night);

private:
	/** Model of the kind and light inside its glass. */
	void PlaceLight();

	UPROPERTY()
	TObjectPtr<UStaticMesh> WallModel;

	UPROPERTY()
	TObjectPtr<UStaticMesh> PoleModel;
};
