#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "GameFramework/GameModeBase.h"
#include "M80GameHUD.generated.h"

class UMaterialInterface;
class UMaterialInstanceDynamic;
class UFont;

/**
 * GTA-style HUD: round radar (fading at the rim) with the town map bottom left (rotates with the camera, player arrow,
 * north marker), health and armour bars under it (stamina too while it is not full); red flash when hit,
 * "SEI MORTO" and a fade when the player dies; weapon and ammo, crosshair while aiming; clock, money (lire) and wanted stars top right;
 * street and vehicle names bottom right; help box top left; full map with M.
 * The map texture covers the world square MapMin .. MapMin + MapSpan (Tools/Map/m80_make_map.py).
 */
UCLASS()
class MAZZARINOGAMEPLAY_API AM80GameHUD : public AHUD
{
	GENERATED_BODY()

public:
	AM80GameHUD();
	virtual void DrawHUD() override;

	/** Loaded when the game starts (a hard reference would keep the material locked in the editor). */
	UPROPERTY(EditAnywhere, Category = "Radar")
	TSoftObjectPtr<UMaterialInterface> RadarMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/Mazzarino80/UI/M_M80_Radar.M_M80_Radar")));

	UPROPERTY(EditAnywhere, Category = "Radar")
	FVector2D MapMin = FVector2D(-55289.48, -74830.065);

	UPROPERTY(EditAnywhere, Category = "Radar")
	double MapSpan = 227520.12;

	/** Half height of the radar in world cm, on foot and at speed. */
	UPROPERTY(EditAnywhere, Category = "Radar")
	float RadarRangeWalk = 9000.f;

	UPROPERTY(EditAnywhere, Category = "Radar")
	float RadarRangeDrive = 16000.f;

	/** Game clock: starts at this hour, one game minute per real second. */
	UPROPERTY(EditAnywhere, Category = "HUD")
	float StartHour = 10.f;

private:
	void DrawRadar(float X, float Y, float W, float H, float S);
	void DrawFullMap(float S);
	void DrawStatus(float S);
	void DrawNames(float S);
	void DrawHelp(float S);
	void Text(const FString& Str, float X, float Y, const FLinearColor& Color, float Scale, bool bRight = false, bool bBig = true, bool bCentre = false);
	void DrawEffects(float S);
	void DrawWeapon(float S);
	void DrawSpeed(float S);
	void Star(float X, float Y, float R, const FLinearColor& Fill, const FLinearColor& Edge);
	FVector2D WorldToMapUV(const FVector& P) const;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> RadarMID;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> MapMID;

	float RadarRange = 9000.f;
	float StaminaAlpha = 0.f;
};

/** Town game: GTA-like player controller and HUD, the player character in a tracksuit. */
UCLASS(meta = (DisplayName = "Mazzarino 80 (gioco)"))
class MAZZARINOGAMEPLAY_API AM80GameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AM80GameMode();
	virtual void InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage) override;

	/** Player character blueprint; falls back to the sample's MetaHuman (Kellan) if missing. */
	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	FSoftClassPath PlayerCharacter = FSoftClassPath(TEXT("/Game/Mazzarino80/Player/BP_M80_Giocatore.BP_M80_Giocatore_C"));

	/** Weapons lying around the player start, on the streets (GTA pickups). */
	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	bool bSpawnWeaponPickups = true;

	virtual void StartPlay() override;
};
