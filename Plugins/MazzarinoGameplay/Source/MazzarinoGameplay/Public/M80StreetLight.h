#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "M80StreetLight.generated.h"

class UPointLightComponent;
class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;

UENUM(BlueprintType)
enum class EM80LampKind : uint8
{
	Wall UMETA(DisplayName = "A muro (braccio in ferro battuto)"),
	Pole UMETA(DisplayName = "A palo (candelabro a tre luci)"),
	City UMETA(DisplayName = "Lamp_city (tre lanterne sui bracci)"),
	Garden UMETA(DisplayName = "Lampione della Madonna (lanterna su colonnina)"),
	Whip UMETA(DisplayName = "A frusta (palo stradale anni '80)")
};

/**
 * A cast-iron street lamp of Mazzarino (modelled from photos, Research/Mazzarino80/Blender/m80_lamps_blender.py):
 * a lantern on a wrought-iron bracket on the facade, or the three-light candelabra of the squares.
 * Its warm light and glowing glass are switched on at dusk and off at dawn by the "Atmosfera
 * (Mazzarino)" (no cost by day: the light is hidden). Wall lamps are placed along the streets by
 * Scripts/m80_town_streetlights.py; every kind can be placed and moved by hand (the back of a wall
 * lamp goes against the wall). Two more kinds are the recovered lamps of the old project (Lamp_city and the
 * Madonna's Lampione, copies in Kit/Lamps made by Scripts/m80_lampioni_migrati.py with the night glass); they stand
 * on the ground and collide.
 * "A frusta" is the steel road lamp of the 1970s-80s outskirts (Research/Mazzarino80/Blender/m80_lampione_frusta.py):
 * a tapered pole of the chosen height bending into an arm over the road (+X), with an aluminium luminaire and a
 * glass bowl; high-pressure sodium (orange) or mercury (bluish white) light.
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

	/** The straight pole of "A frusta", stretched to the chosen height (the arm and luminaire are the Lantern). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Lampione")
	TObjectPtr<UStaticMeshComponent> Pole;

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

	/** Height of the luminaire above the ground (the top of the arm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Lampione", meta = (DisplayName = "Altezza palo (m)", ClampMin = "4", ClampMax = "14", EditCondition = "Kind == EM80LampKind::Whip", EditConditionHides))
	float PoleHeightM = 9.f;

	/** Mercury vapour (the older bluish-white lamps) instead of high-pressure sodium (orange). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Lampione", meta = (DisplayName = "Luce al mercurio (bianca)", EditCondition = "Kind == EM80LampKind::Whip", EditConditionHides))
	bool bMercury = false;

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

	UPROPERTY()
	TObjectPtr<UStaticMesh> CityModel;

	UPROPERTY()
	TObjectPtr<UStaticMesh> GardenModel;

	UPROPERTY()
	TObjectPtr<UStaticMesh> WhipPoleModel;

	UPROPERTY()
	TObjectPtr<UStaticMesh> WhipHeadModel;

	/** Glass of the whip's luminaire: sodium or mercury colour. */
	UPROPERTY()
	TObjectPtr<UMaterialInterface> SodiumGlass;

	UPROPERTY()
	TObjectPtr<UMaterialInterface> MercuryGlass;

	/** Brightness and reach of the kind against a wall lamp. */
	float KindScale() const;
};
