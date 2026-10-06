#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "M80Horizon.generated.h"

class UDynamicMeshComponent;
class UMaterialInterface;

/**
 * The land around the playable terrain, out to the horizon: rolling hills of wheat, stubble and olive
 * groves, higher towards the distance, with Etna where it really stands (north-east, 93 km away, shown
 * closer at the same apparent size). The inner edge follows the border of the landscape, so there is
 * no cliff at the end of the map. Not walkable (no collision): it is scenery seen through the haze.
 */
UCLASS(meta = (DisplayName = "Orizzonte (colline ed Etna)"))
class MAZZARINOGAMEPLAY_API AM80Horizon : public AActor
{
	GENERATED_BODY()

public:
	AM80Horizon();

	virtual void OnConstruction(const FTransform& Transform) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Orizzonte")
	TObjectPtr<UDynamicMeshComponent> Land;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Orizzonte", meta = (DisplayName = "Raggio (km)", ClampMin = "10", ClampMax = "120"))
	float RadiusKm = 60.f;

	/** Height of the hills next to the map and far away (metres above the edge of the map). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Orizzonte", meta = (DisplayName = "Colline vicine (m)"))
	float NearHillsM = 90.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Orizzonte", meta = (DisplayName = "Colline lontane (m)"))
	float FarHillsM = 550.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Orizzonte", meta = (DisplayName = "Seme"))
	int32 Seed = 1980;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Orizzonte|Etna", meta = (DisplayName = "Mostra l'Etna"))
	bool bEtna = true;

	/** World yaw of Etna seen from Mazzarino (from the OSM fit: north-east, about -44 degrees). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Orizzonte|Etna", meta = (DisplayName = "Direzione (gradi)"))
	float EtnaYaw = -44.3f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Orizzonte|Etna", meta = (DisplayName = "Distanza (km)"))
	float EtnaDistanceKm = 45.f;

	/** Real Etna: 3300 m at 93 km, seen from 550 m: the height is scaled to keep that apparent size. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Orizzonte|Etna", meta = (DisplayName = "Altezza apparente (gradi)"))
	float EtnaAngleDeg = 1.25f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Orizzonte", meta = (DisplayName = "Materiale"))
	TObjectPtr<UMaterialInterface> Material;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Orizzonte", meta = (DisplayName = "Info"))
	FString BuildInfo;

	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Orizzonte", meta = (DisplayName = "Ricostruisci"))
	void Rebuild();
};
