#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/HUD.h"
#include "GameFramework/PlayerController.h"
#include "M80DriveTest.generated.h"

class AM80Car;

/** Test drive: possesses the first car of the level; Tab (gamepad right shoulder) jumps to the next one. */
UCLASS()
class MAZZARINOVEHICLES_API AM80DrivePlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	virtual void BeginPlay() override;
	virtual void SetupInputComponent() override;

	UFUNCTION(BlueprintCallable, Category = "Prova guida")
	void NextCar();

	/** Cars of the level, in placement order. */
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Prova guida")
	TArray<TObjectPtr<AM80Car>> Cars;

private:
	int32 Current = -1;
};

/** Speed, gear and rpm of the driven car, plus the controls. */
UCLASS()
class MAZZARINOVEHICLES_API AM80DriveHUD : public AHUD
{
	GENERATED_BODY()

public:
	virtual void DrawHUD() override;
};

/** Game mode of the test-drive level (set in World Settings > GameMode Override). */
UCLASS(meta = (DisplayName = "Prova guida (Mazzarino)"))
class MAZZARINOVEHICLES_API AM80DriveTestGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AM80DriveTestGameMode();
};
