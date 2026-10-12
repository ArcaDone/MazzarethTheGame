#include "M80PlayerCamera.h"
#include "M80PlayerController.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"

void AM80PlayerCameraManager::UpdateViewTarget(FTViewTarget& OutVT, float DeltaTime)
{
	Super::UpdateViewTarget(OutVT, DeltaTime);
	const AM80PlayerController* PC = Cast<AM80PlayerController>(GetOwningPlayerController());
	ACharacter* C = PC ? PC->GetPlayerCharacter() : nullptr;
	const bool bAim = C && PC->IsAiming() && PC->GetViewTarget() == C;
	AimAlpha = FMath::FInterpTo(AimAlpha, bAim ? 1.f : 0.f, DeltaTime, BlendSpeed);
	if (!C || AimAlpha < 0.001f)
	{
		return;
	}
	const FRotator Rot = PC->GetControlRotation();
	const FVector Pivot = C->GetActorLocation() + FVector(0.f, 0.f, PivotHeight);
	FVector Desired = Pivot + Rot.RotateVector(ShoulderOffset);
	// Out of walls: sweep from the pivot (inside the capsule) to the shoulder spot.
	FCollisionQueryParams Q(SCENE_QUERY_STAT(M80AimCamera), false, C);
	FHitResult Hit;
	if (GetWorld()->SweepSingleByChannel(Hit, Pivot, Desired, FQuat::Identity, ECC_Camera, FCollisionShape::MakeSphere(12.f), Q))
	{
		Desired = Hit.Location;
	}
	const float A = FMath::SmoothStep(0.f, 1.f, AimAlpha);
	OutVT.POV.Location = FMath::Lerp(OutVT.POV.Location, Desired, A);
	OutVT.POV.Rotation = FQuat::Slerp(OutVT.POV.Rotation.Quaternion(), Rot.Quaternion(), A).Rotator();
	OutVT.POV.FOV = FMath::Lerp(OutVT.POV.FOV, AimFOV, A);
}
