#include "M80PlayerCamera.h"
#include "M80PlayerController.h"
#include "M80Atmosphere.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"

void AM80PlayerCameraManager::UpdateViewTarget(FTViewTarget& OutVT, float DeltaTime)
{
	Super::UpdateViewTarget(OutVT, DeltaTime);
	// Handheld: slow drift on every axis (the frame a little tilted), the steps when the target moves, a wider lens.
	if (const AM80Atmosphere* Atmo = AM80Atmosphere::Find(this); Atmo && Atmo->bHandheldCamera)
	{
		HandheldTime += DeltaTime;
		const APawn* Target = Cast<APawn>(OutVT.Target);
		const float Moving = Target ? FMath::Clamp(Target->GetVelocity().Size2D() / 450.f, 0.f, 1.f) : 0.f;
		HandheldStep += DeltaTime * 2.f * PI * FMath::Lerp(1.4f, 2.2f, Moving);   // about two steps a second
		const float T = HandheldTime;
		const float K = Atmo->HandheldAmount;
		const float Pitch = FMath::PerlinNoise1D(T * 0.35f) * 0.7f + FMath::Sin(HandheldStep * 2.f) * 0.25f * Moving;
		const float Yaw = FMath::PerlinNoise1D(T * 0.27f + 17.f) * 0.9f + FMath::Sin(HandheldStep) * 0.2f * Moving;
		const float Roll = FMath::PerlinNoise1D(T * 0.21f + 41.f) * 1.2f + FMath::Sin(HandheldStep) * 0.45f * Moving;
		OutVT.POV.Rotation += FRotator(Pitch, Yaw, Roll) * K;
		OutVT.POV.FOV += Atmo->HandheldExtraFOV;
	}
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
