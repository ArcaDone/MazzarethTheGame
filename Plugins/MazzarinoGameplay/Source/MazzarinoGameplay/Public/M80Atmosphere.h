#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "M80Atmosphere.generated.h"

class UDirectionalLightComponent;
class USkyAtmosphereComponent;
class UVolumetricCloudComponent;
class USkyLightComponent;
class UExponentialHeightFogComponent;
class UPostProcessComponent;
class UMaterialInterface;
class UMaterialParameterCollection;

UENUM(BlueprintType)
enum class EM80Weather : uint8
{
	Clear UMETA(DisplayName = "Sereno"),
	Hazy UMETA(DisplayName = "Afa estiva (foschia)"),
	Scirocco UMETA(DisplayName = "Scirocco (polvere)"),
	Cloudy UMETA(DisplayName = "Nuvoloso")
};

/**
 * The whole look of Mazzarino in one actor: sun placed by the real solar position at Mazzarino
 * (37.3 N) for the day of the year and the hour, moon light at night, sky with Mediterranean haze,
 * volumetric clouds, height fog with a valley haze, and a filmic warm grade (a bit RDR2, a bit GTA).
 * The clock runs in game (one game minute per second, as GTA); the HUD reads it.
 * Owns its lights: the map should not have other sun, sky, fog or cloud actors.
 */
UCLASS(meta = (DisplayName = "Atmosfera (Mazzarino)"))
class MAZZARINOGAMEPLAY_API AM80Atmosphere : public AActor
{
	GENERATED_BODY()

public:
	AM80Atmosphere();

	virtual void OnConstruction(const FTransform& Transform) override;
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	/** Hour of the day (0-24) shown in the editor and used when the game starts. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Atmosfera", meta = (DisplayName = "Ora del giorno", ClampMin = "0", ClampMax = "24", UIMin = "0", UIMax = "24"))
	float Hour = 17.5f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Atmosfera", meta = (DisplayName = "Il tempo scorre in gioco"))
	bool bAdvanceInGame = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Atmosfera", meta = (DisplayName = "Minuti di gioco al secondo", ClampMin = "0", ClampMax = "60"))
	float GameMinutesPerSecond = 1.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Atmosfera", meta = (DisplayName = "Tempo"))
	EM80Weather Weather = EM80Weather::Hazy;

	/** 1 = 1 January; 200 = mid July (long days, high sun). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Atmosfera", meta = (DisplayName = "Giorno dell'anno", ClampMin = "1", ClampMax = "365"))
	int32 DayOfYear = 200;

	/** Strength of the colour grade: 0 = plain Unreal, 1 = full Mazzarino look. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Atmosfera", meta = (DisplayName = "Intensita del look", ClampMin = "0", ClampMax = "1.5"))
	float LookStrength = 1.f;

	/** World yaw of north (degrees). Fitted on the OSM buildings: north is about -Y. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Atmosfera|Avanzate", meta = (DisplayName = "Direzione del nord (gradi)"))
	float NorthYaw = -98.5f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Atmosfera|Avanzate", meta = (DisplayName = "Latitudine"))
	float Latitude = 37.3f;

	/** Sun brightness at noon (lux, same scale as the rest of the project). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Atmosfera|Avanzate", meta = (DisplayName = "Luce del sole (lux)"))
	float SunLux = 10.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Atmosfera|Avanzate", meta = (DisplayName = "Materiale nuvole"))
	TObjectPtr<UMaterialInterface> CloudMaterial;

	/** Global values for the materials: "Finestre" = brightness of the rooms behind the windows (dim by day). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Atmosfera|Avanzate", meta = (DisplayName = "Parametri globali materiali"))
	TObjectPtr<UMaterialParameterCollection> MaterialValues;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Componenti")
	TObjectPtr<UDirectionalLightComponent> Sun;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Componenti")
	TObjectPtr<UDirectionalLightComponent> Moon;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Componenti")
	TObjectPtr<USkyAtmosphereComponent> Sky;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Componenti")
	TObjectPtr<UVolumetricCloudComponent> Clouds;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Componenti")
	TObjectPtr<USkyLightComponent> SkyLight;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Componenti")
	TObjectPtr<UExponentialHeightFogComponent> Fog;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Componenti")
	TObjectPtr<UPostProcessComponent> Look;

	/** Current hour of the game clock (advances in game). */
	UFUNCTION(BlueprintPure, Category = "Atmosfera")
	float GetHour() const { return CurrentHour; }

	UFUNCTION(BlueprintCallable, Category = "Atmosfera")
	void SetHour(float NewHour);

	/** Sun elevation above the horizon in degrees (negative at night). */
	UFUNCTION(BlueprintPure, Category = "Atmosfera")
	float GetSunElevation() const { return SunElevation; }

	/** Street lamps: 0 by day, 1 from a little after sunset to a little before sunrise. */
	UFUNCTION(BlueprintPure, Category = "Atmosfera")
	float GetStreetLights() const { return StreetLights; }

	/** The atmosphere actor of a world, if any. */
	UFUNCTION(BlueprintPure, Category = "Atmosfera", meta = (WorldContext = "WorldContextObject"))
	static AM80Atmosphere* Find(const UObject* WorldContextObject);

	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Atmosfera", meta = (DisplayName = "Applica"))
	void Apply();

private:
	void ApplyAt(float AtHour);
	/** Solar elevation and azimuth (degrees, azimuth clockwise from north) at Mazzarino. */
	void SolarPosition(float AtHour, float& OutElevation, float& OutAzimuth) const;

	float CurrentHour = 17.5f;
	float SunElevation = 20.f;
	float StreetLights = 0.f;
	float SinceApply = 0.f;
};
