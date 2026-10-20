#pragma once

#include "CoreMinimal.h"
#include "Camera/PlayerCameraManager.h"
#include "M80PlayerCamera.generated.h"

/**
 * The player's camera: the sample's camera (Gameplay Cameras) as it is, but while aiming a gun it moves over the right
 * shoulder, closer and narrower (GTA), so the crosshair at the centre of the screen is where the shot goes and the
 * character no longer hides the target. A sphere sweep keeps it out of walls. Shots aim from this view
 * (AM80PlayerController::GetAimPoint uses the view point).
 * With the Atmosfera's "Camera a mano" the view sways like a camera held by someone walking behind.
 */
UCLASS()
class MAZZARINOGAMEPLAY_API AM80PlayerCameraManager : public APlayerCameraManager
{
	GENERATED_BODY()

public:
	virtual void UpdateViewTarget(FTViewTarget& OutVT, float DeltaTime) override;

	/** Camera while aiming, from the shoulder pivot in the control frame: back (-X), right (+Y), up (+Z). */
	UPROPERTY(EditAnywhere, Category = "Mira")
	FVector ShoulderOffset = FVector(-165.f, 72.f, 22.f);

	/** Height of the shoulder pivot above the capsule centre. */
	UPROPERTY(EditAnywhere, Category = "Mira")
	float PivotHeight = 58.f;

	UPROPERTY(EditAnywhere, Category = "Mira")
	float AimFOV = 64.f;

	/** How fast the camera goes to the shoulder and back. */
	UPROPERTY(EditAnywhere, Category = "Mira")
	float BlendSpeed = 12.f;

	/** 0 = the sample's camera, 1 = over the shoulder. */
	float GetAimAlpha() const { return AimAlpha; }

private:
	float AimAlpha = 0.f;
	float HandheldTime = 0.f;
	float HandheldStep = 0.f;
};
