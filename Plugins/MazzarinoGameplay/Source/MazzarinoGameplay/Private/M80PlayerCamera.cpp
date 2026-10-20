#include "M80PlayerCamera.h"
#include "M80PlayerController.h"
#include "M80Atmosphere.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"

void AM80PlayerCameraManager::UpdateViewTarget(FTViewTarget& OutVT, float DeltaTime)
{
	Super::UpdateViewTarget(OutVT, DeltaTime);
	// On foot, a little closer to the character than the sample's camera (towards the head, so the framing holds).
	if (const ACharacter* Walker = Cast<ACharacter>(OutVT.Target); Walker && CloserOnFoot > 0.f)
	{
		const FVector Head = Walker->GetActorLocation() + FVector(0.f, 0.f, PivotHeight);
		OutVT.POV.Location = FMath::Lerp(OutVT.POV.Location, Head, FMath::Clamp(CloserOnFoot, 0.f, 0.6f));
	}
	// Handheld: a slow drift on every axis (the frame a little tilted) and a faint step. Running, the operator steadies
	// the camera: the drift halves and the step stays small, with almost no roll (rolling made players sick).
	if (const AM80Atmosphere* Atmo = AM80Atmosphere::Find(this); Atmo && Atmo->bHandheldCamera)
	{
		HandheldTime += DeltaTime;
		const APawn* Target = Cast<APawn>(OutVT.Target);
		const float Moving = Target ? FMath::Clamp(Target->GetVelocity().Size2D() / 450.f, 0.f, 1.f) : 0.f;
		HandheldStep += DeltaTime * 2.f * PI * FMath::Lerp(1.4f, 2.2f, Moving);   // about two steps a second
		const float T = HandheldTime;
		const float K = Atmo->HandheldAmount * FMath::Lerp(1.f, 0.5f, Moving);
		const float Step = 0.3f * Moving * (1.f - 0.5f * Moving);   // most at a walk, less at a run
		const float Pitch = FMath::PerlinNoise1D(T * 0.35f) * 0.6f + FMath::Sin(HandheldStep * 2.f) * 0.12f * Step;
		const float Yaw = FMath::PerlinNoise1D(T * 0.27f + 17.f) * 0.7f + FMath::Sin(HandheldStep) * 0.08f * Step;
		const float Roll = FMath::PerlinNoise1D(T * 0.21f + 41.f) * 0.6f * (1.f - Moving);
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
