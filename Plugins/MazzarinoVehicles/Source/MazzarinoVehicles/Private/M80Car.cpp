#include "M80Car.h"
#include "M80WheelAnim.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/AudioComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SpotLightComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/DamageEvents.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "Sound/SoundBase.h"
#include "Components/SkeletalMeshComponent.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "Engine/LocalPlayer.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
const TCHAR* const EngineSound = TEXT("/Game/Mazzarino80/Audio/M80_Motore.M80_Motore");
const TCHAR* const HornSound = TEXT("/Game/Mazzarino80/Audio/M80_Clacson.M80_Clacson");
const TCHAR* const GlassSound = TEXT("/Game/Mazzarino80/Audio/M80_Vetro.M80_Vetro");
const TCHAR* const BoomSound = TEXT("/Game/Mazzarino80/Audio/M80_Esplosione.M80_Esplosione");
const TCHAR* const CrashSound = TEXT("/Game/Mazzarino80/Audio/M80_Colpo.M80_Colpo");
const TCHAR* const SmokeLight = TEXT("/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Smoke/P_Smoke_A.P_Smoke_A");
const TCHAR* const SmokeDark = TEXT("/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Smoke/P_Smoke_C.P_Smoke_C");
const TCHAR* const FireFx = TEXT("/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Fire/P_Fire_Small.P_Fire_Small");
const TCHAR* const BoomFx = TEXT("/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Explosion/P_Explosion_Big_A.P_Explosion_Big_A");
const TCHAR* const GlassFx = TEXT("/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Destruction/P_Destruction_Glass.P_Destruction_Glass");
const TCHAR* const BurntMat = TEXT("/Game/Mazzarino80/Vehicles/M_M80_Bruciato.M_M80_Bruciato");

template <typename T>
T* LoadPath(const TCHAR* Path)
{
	return Cast<T>(StaticLoadObject(T::StaticClass(), nullptr, Path));
}

UChaosWheeledVehicleMovementComponent* Movement(const AWheeledVehiclePawn* Car)
{
	return Cast<UChaosWheeledVehicleMovementComponent>(Car->GetVehicleMovementComponent());
}

void SetupWheel(UChaosVehicleWheel* W, EAxleType Axle, float Radius, float Width, float MaxSteer, float Brake, float Handbrake, bool bEngine,
	float Spring, float Preload, float Damping, float Raise, float Drop, float Grip = 2.2f)
{
	W->AxleType = Axle;
	W->WheelRadius = Radius;
	W->WheelWidth = Width;
	W->WheelMass = 12.f;
	W->FrictionForceMultiplier = Grip;
	W->CorneringStiffness = 1000.f;
	W->SideSlipModifier = 1.f;
	W->SlipThreshold = 20.f;
	W->SkidThreshold = 20.f;
	W->MaxSteerAngle = MaxSteer;
	W->bAffectedBySteering = MaxSteer > 0.f;
	W->bAffectedByBrake = true;
	W->bAffectedByHandbrake = Handbrake > 0.f;
	W->bAffectedByEngine = bEngine;
	W->MaxBrakeTorque = Brake;
	W->MaxHandBrakeTorque = Handbrake;
	W->SpringRate = Spring;
	W->SpringPreload = Preload;
	W->SuspensionDampingRatio = Damping;
	W->SuspensionMaxRaise = Raise;
	W->SuspensionMaxDrop = Drop;
	W->SuspensionSmoothing = 4;
	W->RollbarScaling = 0.3f;
}
}

// ---------------------------------------------------------------------------------------------
// Wheels

UM80WheelApeFront::UM80WheelApeFront()
{
	SetupWheel(this, EAxleType::Front, 27.f, 12.f, 42.f, 450.f, 0.f, false, 110.f, 40.f, 0.5f, 7.f, 9.f);
}

UM80WheelApeRear::UM80WheelApeRear()
{
	SetupWheel(this, EAxleType::Rear, 27.f, 14.f, 0.f, 450.f, 1200.f, true, 150.f, 60.f, 0.5f, 7.f, 9.f, 2.6f);
}

// Imported vehicles: radius and width measured on the meshes (Saved/Mazzarino80/Import/out/<key>.json).
// The 500: rear engine and drive, 125x12 tyres (radius 25.1, width 16 on the mesh).
UM80Wheel500Front::UM80Wheel500Front() { SetupWheel(this, EAxleType::Front, 25.1f, 16.f, 38.f, 850.f, 0.f, false, 130.f, 55.f, 0.45f, 8.f, 10.f); }
UM80Wheel500Rear::UM80Wheel500Rear() { SetupWheel(this, EAxleType::Rear, 25.1f, 16.f, 0.f, 600.f, 1700.f, true, 165.f, 65.f, 0.45f, 8.f, 10.f, 2.7f); }
// The downloaded cars (radius on the mesh; width the tyre's, the mesh's wheel group also holds the brakes).
UM80WheelMiniFront::UM80WheelMiniFront() { SetupWheel(this, EAxleType::Front, 24.5f, 14.f, 38.f, 1000.f, 0.f, true, 160.f, 60.f, 0.45f, 8.f, 10.f, 2.4f); }
UM80WheelMiniRear::UM80WheelMiniRear() { SetupWheel(this, EAxleType::Rear, 24.5f, 14.f, 0.f, 600.f, 1700.f, false, 130.f, 50.f, 0.45f, 8.f, 10.f, 2.4f); }
UM80WheelMaggiolinoFront::UM80WheelMaggiolinoFront() { SetupWheel(this, EAxleType::Front, 32.3f, 15.f, 36.f, 1000.f, 0.f, false, 150.f, 55.f, 0.45f, 8.f, 10.f); }
UM80WheelMaggiolinoRear::UM80WheelMaggiolinoRear() { SetupWheel(this, EAxleType::Rear, 33.1f, 15.f, 0.f, 700.f, 2000.f, true, 200.f, 75.f, 0.45f, 8.f, 10.f, 2.6f); }
UM80WheelGolfFront::UM80WheelGolfFront() { SetupWheel(this, EAxleType::Front, 27.9f, 18.f, 38.f, 1300.f, 0.f, true, 190.f, 70.f, 0.45f, 8.f, 10.f, 2.6f); }
UM80WheelGolfRear::UM80WheelGolfRear() { SetupWheel(this, EAxleType::Rear, 27.9f, 18.f, 0.f, 800.f, 2000.f, false, 150.f, 55.f, 0.45f, 8.f, 10.f, 2.6f); }
UM80WheelM3Front::UM80WheelM3Front() { SetupWheel(this, EAxleType::Front, 31.1f, 21.f, 36.f, 1800.f, 0.f, false, 260.f, 90.f, 0.45f, 8.f, 10.f, 2.6f); }
UM80WheelM3Rear::UM80WheelM3Rear() { SetupWheel(this, EAxleType::Rear, 30.f, 21.f, 0.f, 1200.f, 2600.f, true, 280.f, 95.f, 0.45f, 8.f, 10.f, 2.8f); }
// The 155: 195/60 R14 on the model (radius 29.5, width 21), front-wheel drive, a heavier car than the Golf.
UM80WheelAlfa155Front::UM80WheelAlfa155Front() { SetupWheel(this, EAxleType::Front, 29.5f, 21.f, 36.f, 1800.f, 0.f, true, 260.f, 90.f, 0.45f, 8.f, 10.f, 2.6f); }
UM80WheelAlfa155Rear::UM80WheelAlfa155Rear() { SetupWheel(this, EAxleType::Rear, 29.5f, 21.f, 0.f, 1100.f, 2600.f, false, 240.f, 85.f, 0.45f, 8.f, 10.f, 2.6f); }
// The Piaggio Si: 2.25x16 tyres (radius 25.1, width 7 on the mesh), drum brakes, soft telescopic fork and rear shocks.
// A two-wheeler's wheel touches the road under its centre (a sphere cast), not where a ray along the leaning frame meets it
// (that is out on the low side, and the springs there stood the moped up again like a wide foot); no anti-roll bar.
static void SetupTwoWheel(UChaosVehicleWheel* W)
{
	W->SweepShape = ESweepShape::Spherecast;
	W->RollbarScaling = 0.f;
}
UM80WheelSiFront::UM80WheelSiFront() { SetupWheel(this, EAxleType::Front, 25.1f, 7.f, 35.f, 160.f, 0.f, false, 45.f, 15.f, 0.5f, 6.f, 8.f, 2.4f); SetupTwoWheel(this); }
UM80WheelSiRear::UM80WheelSiRear() { SetupWheel(this, EAxleType::Rear, 25.1f, 7.f, 0.f, 130.f, 300.f, true, 55.f, 20.f, 0.5f, 5.f, 7.f, 2.6f); SetupTwoWheel(this); }

// ---------------------------------------------------------------------------------------------
// Base car

AM80Car::AM80Car()
{
	PrimaryActorTick.bCanEverTick = true;
#if WITH_EDITORONLY_DATA
	// World Partition: a car is driven away from where it was parked; tied to that cell it would be unloaded
	// under the player ~200 m later (the camera stops, the car rolls on without a driver).
	bIsSpatiallyLoaded = false;
#endif
	// Parked cars stay without a controller until the player gets in (no AI driver by default).
	AutoPossessAI = EAutoPossessAI::Disabled;

	USkeletalMeshComponent* Body = GetMesh();
	Body->SetCollisionProfileName(UCollisionProfile::Vehicle_ProfileName);
	Body->BodyInstance.bSimulatePhysics = true;
	Body->BodyInstance.bNotifyRigidBodyCollision = true;
	Body->BodyInstance.bUseCCD = true;
	Body->bBlendPhysics = true;
	Body->SetGenerateOverlapEvents(true);
	Body->SetCanEverAffectNavigation(false);

	SpringArm = CreateDefaultSubobject<USpringArmComponent>(TEXT("SpringArm"));
	SpringArm->SetupAttachment(Body);
	SpringArm->SetRelativeLocation(FVector(0, 0, 110));
	SpringArm->SetRelativeRotation(FRotator(-12, 0, 0));
	SpringArm->TargetArmLength = ChaseDistance;
	SpringArm->bUsePawnControlRotation = false;
	SpringArm->bInheritPitch = false;
	SpringArm->bInheritRoll = false;
	SpringArm->bEnableCameraLag = true;
	SpringArm->CameraLagSpeed = 9.f;
	SpringArm->bEnableCameraRotationLag = true;
	SpringArm->CameraRotationLagSpeed = 5.f;
	SpringArm->bDoCollisionTest = true;
	SpringArm->ProbeSize = 15.f;

	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(SpringArm, USpringArmComponent::SocketName);
	Camera->bUsePawnControlRotation = false;
	Camera->FieldOfView = 78.f;
}

void AM80Car::BeginPlay()
{
	Super::BeginPlay();
	Health = MaxHealth;
	// Loaded by path the first time they are needed, each was a frame stalled on the disk in the packaged game (breaking
	// a window, getting on): loaded in the background now, before they are needed, and kept.
	TArray<FSoftObjectPath> Assets;
	for (const TCHAR* Path : {EngineSound, HornSound, GlassSound, BoomSound, CrashSound, SmokeLight, SmokeDark, FireFx, BoomFx, GlassFx, BurntMat})
	{
		Assets.Add(FSoftObjectPath(Path));
	}
	for (const TSoftObjectPtr<UAnimSequenceBase>* Clip : {&RidePose, &MountClip, &DismountClip, &PickUpClip})
	{
		if (!Clip->IsNull())
		{
			Assets.Add(Clip->ToSoftObjectPath());
		}
	}
	Preloaded = UAssetManager::GetStreamableManager().RequestAsyncLoad(Assets);
	USkeletalMeshComponent* Body = GetMesh();
	Body->OnComponentHit.AddUniqueDynamic(this, &AM80Car::OnBodyHit);
	// On every body of its physics asset (the component's own flag does not reach them): crashes are felt.
	Body->SetNotifyRigidBodyCollision(true);
	if (bCart)
	{
		return;   // no lights, no engine
	}
	// Parked cars: some are locked (stable per car, not random each time).
	if (!GetController() && LockedChance > 0.f)
	{
		bLocked = (FCrc::StrCrc32(*GetName()) % 100) < uint32(LockedChance * 100.f);
	}
	// Lights: spot lights forward, small red lights at the back (dim, bright when braking).
	const int32 Sides = FMath::IsNearlyZero(HeadlightOffset.Y) ? 1 : 2;
	for (int32 i = 0; i < Sides; ++i)
	{
		const float Y = i == 0 ? HeadlightOffset.Y : -HeadlightOffset.Y;
		USpotLightComponent* L = NewObject<USpotLightComponent>(this);
		L->SetupAttachment(Body);
		L->SetRelativeLocation(FVector(HeadlightOffset.X, Y, HeadlightOffset.Z));
		L->SetRelativeRotation(FRotator(-6.f, 0.f, 0.f));
		L->SetIntensity(Sides == 1 ? 9000.f : 6000.f);
		L->SetAttenuationRadius(3500.f);
		L->SetOuterConeAngle(32.f);
		L->SetInnerConeAngle(18.f);
		L->SetLightColor(FLinearColor(1.f, 0.9f, 0.7f));
		L->SetCastShadows(false);
		L->SetVisibility(false);
		L->RegisterComponent();
		Headlights.Add(L);
		UPointLightComponent* T = NewObject<UPointLightComponent>(this);
		T->SetupAttachment(Body);
		T->SetRelativeLocation(FVector(TaillightOffset.X, i == 0 ? TaillightOffset.Y : -TaillightOffset.Y, TaillightOffset.Z));
		T->SetLightColor(FLinearColor(1.f, 0.05f, 0.02f));
		T->SetAttenuationRadius(150.f);
		T->SetIntensity(0.f);
		T->SetCastShadows(false);
		T->RegisterComponent();
		Taillights.Add(T);
	}
	if (USoundBase* Snd = LoadPath<USoundBase>(EngineSound))
	{
		EngineAudio = NewObject<UAudioComponent>(this);
		EngineAudio->SetupAttachment(Body);
		EngineAudio->SetRelativeLocation(EngineOffset);
		EngineAudio->SetSound(Snd);
		EngineAudio->bAutoActivate = false;
		EngineAudio->bAllowSpatialization = true;
		EngineAudio->RegisterComponent();
	}
}

float AM80Car::TakeDamage(float DamageAmount, FDamageEvent const& DamageEvent, AController* EventInstigator, AActor* DamageCauser)
{
	const float Actual = Super::TakeDamage(DamageAmount, DamageEvent, EventInstigator, DamageCauser);
	if (!bWrecked && Actual > 0.f)
	{
		Health = FMath::Max(0.f, Health - Actual);
	}
	return Actual;
}

void AM80Car::OnBodyHit(UPrimitiveComponent* HitComp, AActor* Other, UPrimitiveComponent* OtherComp, FVector NormalImpulse, const FHitResult& Hit)
{
	if (bWrecked || HitCooldown > 0.f)
	{
		return;
	}
	// Change of speed in the crash (cm/s): nothing under ~18 km/h, a 60 km/h crash into a wall ~70.
	const float Mass = FMath::Max(100.f, GetMesh()->GetMass());
	const float DeltaV = NormalImpulse.Size() / Mass;
	if (IsTwoWheeler() && DeltaV > 200.f)
	{
		UE_LOG(LogTemp, Log, TEXT("%s: hit %s, change of speed %.0f cm/s (sideways %.0f), %.0f km/h"), *GetName(), Other ? *Other->GetName() : TEXT("?"),
			DeltaV, FVector(NormalImpulse.X, NormalImpulse.Y, 0.f).Size() / Mass, GetSpeedKmh());
	}
	if (DeltaV < 500.f)
	{
		return;
	}
	HitCooldown = 0.25f;
	if (!bCart)
	{
		Health = FMath::Max(0.f, Health - (DeltaV - 500.f) * 0.06f);
	}
	// Thrown off by what it runs into (a wall, a car), not by the road (a hard landing, the tail touching in a wheelie).
	const float SideDeltaV = FVector(NormalImpulse.X, NormalImpulse.Y, 0.f).Size() / Mass;
	if (IsTwoWheeler() && SideDeltaV > ThrowDeltaV && GetController())
	{
		// Into something hard: the rider goes on over the handlebar with the speed the moped had.
		ThrowRider(LastVelocity * 0.8f + FVector(0.f, 0.f, 250.f), 8.f + (DeltaV - ThrowDeltaV) * 0.035f,
			*FString::Printf(TEXT("urto %.0f cm/s contro %s"), SideDeltaV, Other ? *Other->GetName() : TEXT("?")));
	}
	UGameplayStatics::PlaySoundAtLocation(this, LoadPath<USoundBase>(CrashSound), Hit.ImpactPoint, FMath::Clamp(DeltaV / 1500.f, 0.3f, 1.5f), 0.6f);
}

void AM80Car::UpdateDamage(float DeltaSeconds)
{
	HitCooldown -= DeltaSeconds;
	if (bWrecked || bCart)
	{
		return;
	}
	const float F = Health / FMath::Max(1.f, MaxHealth);
	const int32 Level = F < 0.1f ? 3 : (F < 0.25f ? 2 : (F < 0.5f ? 1 : 0));
	if (Level != SmokeLevel)
	{
		SmokeLevel = Level;
		if (!Smoke)
		{
			Smoke = UGameplayStatics::SpawnEmitterAttached(LoadPath<UParticleSystem>(SmokeLight), GetMesh(), NAME_None, EngineOffset,
				FRotator::ZeroRotator, FVector(0.6f), EAttachLocation::KeepRelativeOffset, false);
		}
		if (!Smoke)
		{
			return;
		}
		Smoke->SetTemplate(LoadPath<UParticleSystem>(Level >= 2 ? SmokeDark : SmokeLight));
		Smoke->SetVisibility(Level > 0);
		if (Level > 0)
		{
			Smoke->Activate(true);
		}
		else
		{
			Smoke->Deactivate();
		}
	}
	if (Level == 3 && BurnTime < 0.f)
	{
		// On fire: it blows up in a few seconds (GTA: run!).
		BurnTime = 0.f;
		if (!Fire)
		{
			Fire = UGameplayStatics::SpawnEmitterAttached(LoadPath<UParticleSystem>(FireFx), GetMesh(), NAME_None, EngineOffset + FVector(0, 0, 10.f),
				FRotator::ZeroRotator, FVector(1.f), EAttachLocation::KeepRelativeOffset, false);
		}
		if (Fire)
		{
			Fire->Activate(true);
		}
	}
	if (BurnTime >= 0.f)
	{
		BurnTime += DeltaSeconds;
		if (BurnTime > (Health <= 0.f ? 1.5f : 5.f))
		{
			Explode();
		}
	}
}

void AM80Car::Explode()
{
	if (bWrecked || bCart)
	{
		return;
	}
	bWrecked = true;
	Health = 0.f;
	bLights = false;
	const FVector At = GetActorTransform().TransformPosition(EngineOffset);
	UGameplayStatics::SpawnEmitterAtLocation(this, LoadPath<UParticleSystem>(BoomFx), At, FRotator::ZeroRotator, FVector(1.2f));
	UGameplayStatics::PlaySoundAtLocation(this, LoadPath<USoundBase>(BoomSound), At, 2.f);
	OnExploded.Broadcast(this);
	TArray<AActor*> Ignore = {this};
	UGameplayStatics::ApplyRadialDamageWithFalloff(this, 220.f, 15.f, At, 350.f, 900.f, 1.f, nullptr, Ignore, this, nullptr, ECC_Visibility);
	// The shell jumps and turns a little.
	USkeletalMeshComponent* Body = GetMesh();
	Body->AddImpulse(FVector(FMath::FRandRange(-150.f, 150.f), FMath::FRandRange(-150.f, 150.f), 520.f), NAME_None, true);
	Body->AddAngularImpulseInDegrees(FVector(FMath::FRandRange(-60.f, 60.f), FMath::FRandRange(-90.f, 90.f), 0.f), NAME_None, true);
	if (UMaterialInterface* Burnt = LoadPath<UMaterialInterface>(BurntMat))
	{
		for (int32 i = 0; i < Body->GetNumMaterials(); ++i)
		{
			Body->SetMaterial(i, Burnt);
		}
	}
	if (Smoke)
	{
		Smoke->SetTemplate(LoadPath<UParticleSystem>(SmokeDark));
		Smoke->Activate(true);
	}
	if (EngineAudio)
	{
		EngineAudio->Stop();
	}
	if (UChaosWheeledVehicleMovementComponent* M = Movement(this))
	{
		M->SetThrottleInput(0.f);
		M->SetHandbrakeInput(true);
	}
	// The fire burns out after a while; the smoke stays a bit longer.
	FTimerHandle T;
	GetWorldTimerManager().SetTimer(T, FTimerDelegate::CreateWeakLambda(this, [this]() { if (Fire) { Fire->Deactivate(); } }), 25.f, false);
}

void AM80Car::Horn()
{
	if (!bWrecked && !bCart)
	{
		UGameplayStatics::PlaySoundAtLocation(this, LoadPath<USoundBase>(HornSound), GetActorLocation());
		// Let the town hear it (pedestrians will step aside later).
		MakeNoise(0.6f, this, GetActorLocation(), 2500.f, TEXT("Clacson"));
	}
}

void AM80Car::ToggleLights()
{
	bLights = !bLights && !bWrecked;
}

void AM80Car::BreakWindow()
{
	bLocked = false;
	const FVector At = GetActorTransform().TransformPosition(FVector(DoorOffset.X, DoorOffset.Y * 0.45f, DoorOffset.Z + 30.f));
	UGameplayStatics::SpawnEmitterAtLocation(this, LoadPath<UParticleSystem>(GlassFx), At, FRotator::ZeroRotator, FVector(0.4f));
	UGameplayStatics::PlaySoundAtLocation(this, LoadPath<USoundBase>(GlassSound), At);
	MakeNoise(0.8f, nullptr, At, 2000.f, TEXT("Vetro"));
}

void AM80Car::UpdateLightsAndSound(float DeltaSeconds)
{
	UChaosWheeledVehicleMovementComponent* M = Movement(this);
	for (USpotLightComponent* L : Headlights)
	{
		L->SetVisibility(bLights);
	}
	const bool bBraking = M && !bWrecked && GetController() && (M->GetBrakeInput() > 0.1f || bHandbrakeHeld);
	for (UPointLightComponent* T : Taillights)
	{
		T->SetIntensity(bBraking ? 2500.f : (bLights ? 500.f : 0.f));
	}
	// Engine sound while someone drives: pitch with the rpm, louder with the throttle.
	if (EngineAudio)
	{
		const bool bOn = GetController() && !bWrecked;
		if (bOn && !EngineAudio->IsPlaying())
		{
			EngineAudio->Play();
		}
		else if (!bOn && EngineAudio->IsPlaying())
		{
			EngineAudio->FadeOut(0.6f, 0.f);
		}
		if (bOn && M)
		{
			const float Rpm = FMath::Clamp(GetEngineRPM() / FMath::Max(1000.f, M->EngineSetup.MaxRPM), 0.f, 1.f);
			EngineAudio->SetPitchMultiplier(0.8f + Rpm * 2.4f);
			EngineAudio->SetVolumeMultiplier(0.45f + 0.5f * M->GetThrottleInput());
		}
	}
}

void AM80Car::ApplySpec(const FCarSpec& S)
{
	UChaosWheeledVehicleMovementComponent* M = Movement(this);
	if (!M)
	{
		return;
	}
	M->Mass = S.MassKg;
	M->bEnableCenterOfMassOverride = true;
	M->CenterOfMassOverride = S.CenterOfMass;
	M->DragCoefficient = S.DragCoefficient;
	M->ChassisWidth = S.ChassisWidth;
	M->ChassisHeight = S.ChassisHeight;
	M->DownforceCoefficient = 0.1f;
	M->bReverseAsBrake = true;
	M->bLegacyWheelFrictionPosition = false;

	M->EngineSetup.MaxTorque = S.MaxTorqueNm;
	M->EngineSetup.MaxRPM = S.MaxRPM;
	M->EngineSetup.EngineIdleRPM = S.IdleRPM;
	M->EngineSetup.EngineBrakeEffect = S.EngineBrake;
	M->EngineSetup.EngineRevUpMOI = S.RevUpMOI;
	M->EngineSetup.EngineRevDownRate = S.RevDownRate;
	FRichCurve* Torque = M->EngineSetup.TorqueCurve.GetRichCurve();
	Torque->Reset();
	Torque->AddKey(0.f, 0.45f);
	Torque->AddKey(S.IdleRPM, 0.6f);
	Torque->AddKey(S.PeakTorqueRPM, 1.f);
	Torque->AddKey(S.MaxRPM, 0.72f);

	M->TransmissionSetup.bUseAutomaticGears = true;
	M->TransmissionSetup.bUseAutoReverse = true;
	M->TransmissionSetup.ForwardGearRatios = S.Gears;
	M->TransmissionSetup.ReverseGearRatios = {S.ReverseGear};
	M->TransmissionSetup.FinalRatio = S.FinalRatio;
	M->TransmissionSetup.ChangeUpRPM = S.ChangeUpRPM;
	M->TransmissionSetup.ChangeDownRPM = S.ChangeDownRPM;
	M->TransmissionSetup.GearChangeTime = S.GearChangeTime;
	M->TransmissionSetup.TransmissionEfficiency = 0.9f;

	M->DifferentialSetup.DifferentialType = S.Drive;

	M->SteeringSetup.SteeringType = ESteeringType::AngleRatio;
	FRichCurve* Steer = M->SteeringSetup.SteeringCurve.GetRichCurve();
	// Less lock the faster the car goes (X in MPH): full keyboard steering stays near the grip limit.
	Steer->Reset();
	Steer->AddKey(0.f, 1.f);
	Steer->AddKey(10.f, FMath::Lerp(1.f, S.SteerAt30Mph, 0.35f));
	Steer->AddKey(20.f, FMath::Lerp(1.f, S.SteerAt30Mph, 0.75f));
	Steer->AddKey(30.f, S.SteerAt30Mph);
	Steer->AddKey(60.f, S.SteerAt60Mph);
	Steer->AddKey(100.f, S.SteerAt60Mph * 0.75f);
	WheelbaseCm = S.WheelbaseCm;
	MaxLeanDeg = S.MaxLeanDeg;
	GripG = S.GripG;

	M->ThrottleInputRate.RiseRate = S.ThrottleRise;
	M->ThrottleInputRate.FallRate = S.ThrottleFall;
	M->SteeringInputRate.RiseRate = S.SteerRise;
	M->SteeringInputRate.FallRate = S.SteerFall;
	M->BrakeInputRate.RiseRate = S.BrakeRise;
	M->BrakeInputRate.FallRate = S.BrakeFall;
	M->HandbrakeInputRate.RiseRate = 12.f;
	M->HandbrakeInputRate.FallRate = 12.f;
	if (MaxLeanDeg > 0.f)
	{
		// Two wheels: no reverse gear (S held at a standstill walks it back, UpdateFootBack), and no braking by itself
		// when stopped without throttle (it would hold against the feet).
		M->bReverseAsBrake = false;
		M->SleepThreshold = 0.f;   // nor put to sleep while the feet push it
		if (FFloatProperty* Stop = FindFProperty<FFloatProperty>(UChaosVehicleMovementComponent::StaticClass(), TEXT("StopThreshold")))
		{
			Stop->SetPropertyValue_InContainer(M, 0.f);
		}
	}
}

void AM80Car::SetupImported(const TCHAR* MeshPath, TSubclassOf<UChaosVehicleWheel> Front, TSubclassOf<UChaosVehicleWheel> Rear, bool bTwoWheels)
{
	ConstructorHelpers::FObjectFinderOptional<USkeletalMesh> MeshAsset(MeshPath);
	GetMesh()->SetSkeletalMesh(MeshAsset.Get());
	GetMesh()->SetAnimInstanceClass(UM80WheelAnimInstance::StaticClass());
	if (UChaosWheeledVehicleMovementComponent* M = Movement(this))
	{
		const TArray<FName> Bones = bTwoWheels ? TArray<FName>{TEXT("Wheel_F"), TEXT("Wheel_R")}
			: TArray<FName>{TEXT("Wheel_FL"), TEXT("Wheel_FR"), TEXT("Wheel_RL"), TEXT("Wheel_RR")};
		M->WheelSetups.SetNum(Bones.Num());
		for (int32 i = 0; i < Bones.Num(); ++i)
		{
			M->WheelSetups[i].BoneName = Bones[i];
			M->WheelSetups[i].WheelClass = (Bones[i].ToString().Contains(TEXT("_F")) ? Front : Rear);
		}
	}
}

void AM80Car::SetupCart(const TCHAR* MeshPath, const TCHAR* PosePath, const TArray<TPair<FName, TSubclassOf<UChaosVehicleWheel>>>& Wheels, float InWheelbaseCm)
{
	ConstructorHelpers::FObjectFinderOptional<USkeletalMesh> MeshAsset(MeshPath);
	GetMesh()->SetSkeletalMesh(MeshAsset.Get());
	GetMesh()->SetAnimInstanceClass(UM80WheelAnimInstance::StaticClass());
	RidePose = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(PosePath));
	if (UChaosWheeledVehicleMovementComponent* M = Movement(this))
	{
		M->WheelSetups.SetNum(Wheels.Num());
		for (int32 i = 0; i < Wheels.Num(); ++i)
		{
			M->WheelSetups[i].BoneName = Wheels[i].Key;
			M->WheelSetups[i].WheelClass = Wheels[i].Value;
		}
		// Chaos puts a vehicle to sleep when nobody presses throttle or brake: a cart has neither (it is pushed, or
		// it rolls downhill), so only the physics' own sleep (still and on the flat) is kept. Nor does it brake by
		// itself when standing still without throttle (Chaos' "auto brake"): the push could not start it.
		M->SleepThreshold = 0.f;
		if (FFloatProperty* Stop = FindFProperty<FFloatProperty>(UChaosVehicleMovementComponent::StaticClass(), TEXT("StopThreshold")))
		{
			Stop->SetPropertyValue_InContainer(M, 0.f);   // protected in Chaos, set through its property
		}
	}
	// A few kilos of wood and the rider (not simulated: the weight is in the mass). No engine: the push and the
	// slopes move it (UpdateCart); Chaos keeps the wheels, the steering and the brakes.
	FCarSpec S;
	S.MassKg = 80.f;
	S.CenterOfMass = FVector(-10.f, 0.f, 5.f);
	S.DragCoefficient = 0.f;   // air and bearings in UpdateCart
	S.ChassisWidth = 50.f;
	S.ChassisHeight = 40.f;
	S.MaxTorqueNm = 0.5f;
	S.MaxRPM = 3000.f;
	S.IdleRPM = 500.f;
	S.PeakTorqueRPM = 1500.f;
	S.EngineBrake = 0.f;
	S.Gears = {1.f};
	S.ReverseGear = 1.f;
	S.FinalRatio = 1.f;
	S.ChangeUpRPM = 2900.f;
	S.ChangeDownRPM = 100.f;
	S.SteerAt30Mph = 0.55f;   // ~48 km/h downhill: still some lock, the bearings slide anyway
	S.SteerAt60Mph = 0.4f;
	S.SteerRise = 3.f;
	S.SteerFall = 5.f;
	S.WheelbaseCm = InWheelbaseCm;
	S.GripG = 0.6f;
	ApplySpec(S);
}

void AM80Car::UpdateCart(float DeltaSeconds)
{
	UChaosWheeledVehicleMovementComponent* M = Movement(this);
	USkeletalMeshComponent* Body = GetMesh();
	if (!bCart || !M || !Body->IsSimulatingPhysics())
	{
		return;
	}
	const float Kmh = GetSpeedKmh();
	// S: the feet brake while it rolls forward; once stopped they shuffle it back.
	const bool bBack = CartBrake > 0.05f && Kmh < 1.5f;
	M->SetThrottleInput(0.f);
	M->SetBrakeInput(bBack ? 0.f : CartBrake);
	int32 OnGround = 0;
	for (int32 i = 0; i < M->Wheels.Num(); ++i)
	{
		OnGround += M->GetWheelState(i).bInContact ? 1 : 0;
	}
	if (OnGround < 2)
	{
		return;
	}
	float Push = 0.f;
	if (CartPush > 0.05f)
	{
		Push = CartPush * PushAccel * FMath::Clamp((PushTopKmh - Kmh) / 3.f, 0.f, 1.f);
	}
	else if (bBack)
	{
		Push = -CartBrake * PushAccel * 0.5f * FMath::Clamp((4.f + Kmh) / 2.f, 0.f, 1.f);
	}
	if (Push != 0.f)
	{
		M->SetSleeping(false);
	}
	// Steel bearings on stone and the rider in the wind: on the flat it slows down by itself, downhill it
	// runs up to where the slope and the drag even out (about 45 km/h on a 10% street).
	const FVector V = Body->GetPhysicsLinearVelocity();
	const float Speed = V.Size();
	FVector Resist = FVector::ZeroVector;
	if (Speed > 1.f)
	{
		const float Roll = RollingResistance * 981.f * FMath::Clamp(Speed / 50.f, 0.f, 1.f);
		const float Air = AirDrag * Speed * Speed / 100.f;
		Resist = -V / Speed * (Roll + Air);
	}
	Body->AddForce(GetActorForwardVector() * Push + Resist, NAME_None, true);
}

void AM80Car::KeepUpright(float DeltaSeconds)
{
	// Two wheels: Chaos would let it fall over. A spring-damper on the roll holds it up and leans it into the bend as a
	// real one leans: the angle that balances the turn, tan(lean) = speed x turning rate / g. Slow it stays almost upright
	// however much the handlebar is turned; fast, a gentle bend already leans it well over.
	USkeletalMeshComponent* Body = GetMesh();
	UChaosWheeledVehicleMovementComponent* M = Movement(this);
	if (MaxLeanDeg <= 0.f || !Body->IsSimulatingPhysics() || !M)
	{
		return;
	}
	const FVector Fwd = GetActorForwardVector();
	if (bFallen)
	{
		return;   // nobody holds it up: UpdateLayDown
	}
	// Knocked over on its side (a crash from the side, a kerb taken badly): the rider comes off, it lies down.
	TipTime = FMath::Abs(GetActorRightVector().Z) > 0.82f ? TipTime + DeltaSeconds : 0.f;
	if (TipTime > 0.35f)
	{
		bFallen = true;
		if (GetController())
		{
			ThrowRider(GetVelocity() * 0.7f + FVector(0.f, 0.f, 150.f), 6.f, TEXT("sul fianco"));
		}
		return;
	}
	const float Speed = M->GetForwardSpeed() / 100.f;   // m/s
	const float YawRate = Body->GetPhysicsAngularVelocityInRadians().Z;   // + turning right
	const float Balance = -FMath::RadiansToDegrees(FMath::Atan(Speed * YawRate / 9.81f));
	LeanNow = FMath::FInterpTo(LeanNow, FMath::Clamp(Balance, -MaxLeanDeg, MaxLeanDeg), DeltaSeconds, 6.f);
	const float Lean = LeanNow;
	const float Roll = FMath::RadiansToDegrees(FMath::Asin(FMath::Clamp(GetActorRightVector().Z, -1.f, 1.f)));
	const float RollRate = FMath::RadiansToDegrees(Body->GetPhysicsAngularVelocityInRadians() | Fwd);
	const float Accel = (Lean - Roll) * 40.f - RollRate * 7.f;   // deg/s^2
	Body->AddTorqueInDegrees(Fwd * Accel, NAME_None, true);
}

void AM80Car::Wheelie()
{
	if (IsTwoWheeler() && WheelieClock < 0.f && !bFallen)
	{
		WheelieClock = 0.f;
		bPulled = false;
	}
}

void AM80Car::UpdateWheelie(float DeltaSeconds)
{
	USkeletalMeshComponent* Body = GetMesh();
	UChaosWheeledVehicleMovementComponent* M = Movement(this);
	if (!IsTwoWheeler() || !M || M->Wheels.Num() < 2 || !Body->IsSimulatingPhysics() || bFallen)
	{
		RiderLean = WheelieDeg = 0.f;
		WheelieClock = -1.f;
		return;
	}
	const FVector Fwd = GetActorForwardVector();
	const FVector Up = GetActorUpVector();
	const float Pitch = FMath::RadiansToDegrees(FMath::Asin(FMath::Clamp(Fwd.Z, -1.f, 1.f)));
	const bool bFront = M->GetWheelState(0).bInContact;   // Wheel_F, then Wheel_R (SetupImported)
	const bool bRear = M->GetWheelState(1).bInContact;
	// The slope it rides on, measured with both wheels down: the wheelie is the nose's rise over it.
	if (bFront && bRear)
	{
		GroundPitch = FMath::FInterpTo(GroundPitch, Pitch, DeltaSeconds, 5.f);
	}
	WheelieDeg = bFront ? 0.f : FMath::Max(0.f, Pitch - GroundPitch);
	const FVector Axis = FVector::CrossProduct(Fwd, Up).GetSafeNormal();   // turning about it lifts the nose
	const float Throttle = M->GetThrottleInput();
	float LeanTarget = 0.f;
	if (WheelieClock >= 0.f)
	{
		WheelieClock += DeltaSeconds;
		if (WheelieClock < 0.22f)
		{
			LeanTarget = 14.f;   // over the handlebar, loading the fork
		}
		else
		{
			if (!bPulled)
			{
				// The pull: the body thrown back, the front lifts (more with the throttle open and some speed).
				bPulled = true;
				const float Kmh = FMath::Abs(GetSpeedKmh());
				if (bRear)
				{
					PitchAboutRear(WheelieKick * (0.35f + 0.65f * Throttle) * FMath::Clamp(0.4f + Kmh / 15.f, 0.4f, 1.f), true);
				}
			}
			LeanTarget = -16.f;
			if (WheelieClock > 0.7f && WheelieDeg < 1.5f)
			{
				WheelieClock = -1.f;   // back on both wheels
			}
		}
	}
	if (WheelieDeg > 1.5f)
	{
		LeanTarget = FMath::Min(LeanTarget, -6.f - WheelieDeg * 0.3f);   // leaning back against it
		// The rear wheel's drive pushes the front up, the rear brake drops it; gravity does the rest (Chaos). A little
		// damping so that a steady hand on the throttle can hold it.
		const float PitchRate = FMath::RadiansToDegrees(Body->GetPhysicsAngularVelocityInRadians() | Axis);
		// Held wide open, the engine revs up and pulls harder and harder: about a second of that and it goes over; a hand
		// that eases off keeps it.
		WheelieRev = Throttle > 0.9f ? WheelieRev + DeltaSeconds * 1.2f : FMath::Max(0.f, WheelieRev - DeltaSeconds * 2.f);
		const float Lift = bRear ? Throttle * WheelieThrottle * (1.f + WheelieRev) : 0.f;
		PitchAboutRear(Lift - M->GetBrakeInput() * 600.f - PitchRate * 1.2f, false);
		if (WheelieDeg > WheelieLoopDeg)
		{
			// Over backwards: the rider slides off the back, the moped goes over.
			bFallen = true;
			if (GetController())
			{
				ThrowRider(GetVelocity() * 0.6f - Fwd * 200.f + FVector(0.f, 0.f, 200.f), 12.f,
					*FString::Printf(TEXT("impennata oltre %.0f gradi"), WheelieDeg));
			}
		}
	}
	if (WheelieDeg <= 1.5f)
	{
		WheelieRev = 0.f;
	}
	RiderLean = FMath::FInterpTo(RiderLean, LeanTarget, DeltaSeconds, WheelieClock >= 0.f && WheelieClock < 0.4f ? 14.f : 5.f);
}

void AM80Car::PitchAboutRear(float DegreesPerSecond, bool bImpulse)
{
	USkeletalMeshComponent* Body = GetMesh();
	const FVector Up = GetActorUpVector();
	const FVector Axis = FVector::CrossProduct(GetActorForwardVector(), Up).GetSafeNormal();
	const FVector Contact = Body->GetSocketLocation(TEXT("Wheel_R")) - Up * 25.f;
	// The centre of mass goes round the contact with the body: its velocity (or acceleration) is the turn x the arm.
	const FVector Turn = Axis * FMath::DegreesToRadians(DegreesPerSecond);
	const FVector Along = FVector::CrossProduct(Turn, Body->GetCenterOfMass() - Contact);
	// Only its upward part: going on, the drive of the rear wheel (Chaos) keeps the speed; the backward part of turning
	// about the contact would brake it to a stop while the wheelie is held.
	const FVector Lift(0.f, 0.f, Along.Z);
	if (bImpulse)
	{
		Body->AddAngularImpulseInRadians(Turn, NAME_None, true);
		Body->AddImpulse(Lift, NAME_None, true);
	}
	else
	{
		Body->AddTorqueInRadians(Turn, NAME_None, true);
		Body->AddForce(Lift, NAME_None, true);
	}
}

void AM80Car::UpdateFootBack(float DeltaSeconds)
{
	UChaosWheeledVehicleMovementComponent* M = Movement(this);
	USkeletalMeshComponent* Body = GetMesh();
	if (!IsTwoWheeler() || !M || !GetController() || bFallen || !Body->IsSimulatingPhysics())
	{
		bBacking = false;
		return;
	}
	// S held at a standstill (or already going back): the rider walks it back with both feet, a step at a time, at most
	// about 3 km/h; going forward S is the brake as usual.
	const float Kmh = GetSpeedKmh();
	const bool bWas = bBacking;
	bBacking = CartBrake > 0.1f && Kmh < (bBacking ? 1.f : 0.5f) && M->GetThrottleInput() < 0.05f;
	if (bBacking != bWas)
	{
		M->SetTargetGear(bBacking ? 0 : 1, true);   // in neutral while pushed: the engine does not hold it
	}
	if (!bBacking)
	{
		return;
	}
	M->SetBrakeInput(0.f);
	M->SetHandbrakeInput(false);
	M->SetSleeping(false);
	const float Step = 0.55f + 0.45f * FMath::Sin(GetWorld()->GetTimeSeconds() * 2.f * PI * 1.2f);
	const float Push = CartBrake * 400.f * Step * FMath::Clamp((3.f + Kmh) / 1.5f, 0.f, 1.f);
	Body->AddForce(-GetActorForwardVector() * Push, NAME_None, true);
}

void AM80Car::UpdateRiderless(float DeltaSeconds)
{
	// A two-wheeler left by its rider while moving (thrown off in a crash or a wheelie, jumped off): nobody holds it any
	// more, no keeping it upright (KeepUpright), a free body. The wheels still roll it on and gravity takes it over onto its
	// side, the more it leans the harder (as gravity on a body standing on a line: with the sine of the lean); balanced
	// exactly upright nothing in the simulation would ever tip it, so it starts to the side it leant to. Down on its side
	// it lies there until it is picked up. Got off standing still, it stays up (bFallen is not set).
	USkeletalMeshComponent* Body = GetMesh();
	if (!IsTwoWheeler() || !bFallen || bPickingUp || GetController() || !Body->IsSimulatingPhysics())
	{
		return;
	}
	SinceThrown += DeltaSeconds;
	const float Rolled = FMath::RadiansToDegrees(FMath::Asin(FMath::Clamp(GetActorRightVector().Z, -1.f, 1.f)));
	if (FMath::Abs(Rolled) > 60.f)
	{
		return;   // down
	}
	Body->WakeAllRigidBodies();   // a body at rest sleeps and would not feel the pull
	// Stronger than gravity alone: the Chaos wheels (springs and tyres on traces) still hold a leaning moped up a little.
	const float Pull = 900.f + 3000.f * FMath::Sin(FMath::DegreesToRadians(FMath::Abs(Rolled)));
	Body->AddTorqueInDegrees(GetActorForwardVector() * -ToppleSide * Pull, NAME_None, true);
}

void AM80Car::GripLoose(bool bLoose)
{
	// The Chaos tyre is a trace from the moped down to the road: leaning over, the trace's foot slides sideways with the
	// moped, the tyre takes that for a skid and its grip stands the moped up again (an upturned pendulum held at its
	// foot). With nobody on it most of that grip goes: the wheels still carry it and roll on, gravity lays it down.
	UChaosWheeledVehicleMovementComponent* M = Movement(this);
	if (!M)
	{
		return;
	}
	if (WheelGrip.Num() != M->Wheels.Num())
	{
		WheelGrip.SetNum(M->Wheels.Num());
		for (int32 i = 0; i < M->Wheels.Num(); ++i)
		{
			WheelGrip[i] = M->Wheels[i] ? M->Wheels[i]->FrictionForceMultiplier : 2.f;
		}
	}
	for (int32 i = 0; i < M->Wheels.Num(); ++i)
	{
		M->SetWheelFrictionMultiplier(i, bLoose ? 0.1f : WheelGrip[i]);
	}
}

void AM80Car::ThrowRider(const FVector& Velocity, float Damage, const TCHAR* Why)
{
	bFallen = true;
	GripLoose(true);
	ThrowReason = Why;
	SinceThrown = 0.f;
	UE_LOG(LogTemp, Log, TEXT("%s: rider thrown (%s), %.0f km/h"), *GetName(), Why, GetSpeedKmh());
	// Down on the side it leans to (either, if upright).
	const float Rz = GetActorRightVector().Z;
	ToppleSide = FMath::Abs(Rz) > 0.03f ? (Rz < 0.f ? 1.f : -1.f) : (FMath::RandBool() ? 1.f : -1.f);
	// A nudge to the side it goes: from upright gravity alone would take its time.
	GetMesh()->AddAngularImpulseInDegrees(GetActorForwardVector() * -ToppleSide * 25.f, NAME_None, true);
	WheelieClock = -1.f;
	RiderLean = 0.f;
	OnRiderThrown.Broadcast(this, Velocity, Damage);
}

float AM80Car::GetSpeedKmh() const
{
	const UChaosWheeledVehicleMovementComponent* M = Movement(this);
	return M ? M->GetForwardSpeed() * 0.036f : 0.f;
}

int32 AM80Car::GetGear() const
{
	const UChaosWheeledVehicleMovementComponent* M = Movement(this);
	return M ? M->GetCurrentGear() : 0;
}

float AM80Car::GetEngineRPM() const
{
	const UChaosWheeledVehicleMovementComponent* M = Movement(this);
	return M ? M->GetEngineRotationSpeed() : 0.f;
}

FTransform AM80Car::GetUprightTransform() const
{
	FVector F = GetActorForwardVector();
	F.Z = 0.f;
	return FTransform(F.IsNearlyZero() ? FRotator(0.f, GetActorRotation().Yaw, 0.f) : F.Rotation(), GetActorLocation());
}

void AM80Car::BeginPickUp()
{
	UE_LOG(LogTemp, Log, TEXT("%s: being picked up"), *GetName());
	bPickingUp = true;
	PickFrom = GetActorQuat();
	PickTo = GetUprightTransform().GetRotation();
	GetMesh()->SetSimulatePhysics(false);
}

void AM80Car::SetPickUp(float Alpha)
{
	if (bPickingUp)
	{
		SetActorRotation(FQuat::Slerp(PickFrom, PickTo, FMath::Clamp(Alpha, 0.f, 1.f)), ETeleportType::TeleportPhysics);
	}
}

void AM80Car::EndPickUp()
{
	if (!bPickingUp)
	{
		return;
	}
	bPickingUp = false;
	SetActorRotation(PickTo, ETeleportType::TeleportPhysics);
	USkeletalMeshComponent* Body = GetMesh();
	Body->SetSimulatePhysics(true);
	Body->SetPhysicsLinearVelocity(FVector::ZeroVector);
	Body->SetPhysicsAngularVelocityInDegrees(FVector::ZeroVector);
	if (UChaosWheeledVehicleMovementComponent* M = Movement(this))
	{
		M->ResetVehicle();
	}
	bFallen = false;
	TipTime = 0.f;
	LeanNow = 0.f;
	GripLoose(false);
	UE_LOG(LogTemp, Log, TEXT("%s: picked up"), *GetName());
}

void AM80Car::PutBackOnWheels()
{
	UE_LOG(LogTemp, Log, TEXT("%s: put back on its wheels"), *GetName());
	if (bFallen && IsTwoWheeler())
	{
		GripLoose(false);
	}
	bFallen = false;
	TipTime = 0.f;
	LeanNow = 0.f;
	const FRotator Upright(0.f, GetActorRotation().Yaw, 0.f);
	SetActorLocationAndRotation(GetActorLocation() + FVector(0, 0, 80), Upright, false, nullptr, ETeleportType::TeleportPhysics);
	GetMesh()->SetPhysicsLinearVelocity(FVector::ZeroVector);
	GetMesh()->SetPhysicsAngularVelocityInDegrees(FVector::ZeroVector);
	if (UChaosWheeledVehicleMovementComponent* M = Movement(this))
	{
		M->ResetVehicle();
	}
	UpsideDownTime = 0.f;
}

void AM80Car::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	// Player steering (AI and scripts set the movement component directly).
	if (IsPlayerControlled())
	{
		if (UChaosWheeledVehicleMovementComponent* M = Movement(this))
		{
			M->SetSteeringInput(SteerTarget);
		}
	}

	if (bCoasting && !GetController() && FMath::Abs(GetSpeedKmh()) < 8.f)
	{
		bCoasting = false;
		if (UChaosWheeledVehicleMovementComponent* M = Movement(this))
		{
			M->SetHandbrakeInput(true);
		}
	}

	// Cars are always loaded (see the constructor), the ground streams with the player. Chaos keeps a pointer to the body
	// each wheel stands on and does not clear it when that body is streamed out (UE 5.8): the packaged game crashed in
	// the suspension constraints after the player left the 500 and ran off. Away from the player a car rests with no
	// vehicle physics; within reach again (its ground streamed in long before) its vehicle is built again.
	DormantCheck -= DeltaSeconds;
	if (DormantCheck <= 0.f)
	{
		DormantCheck = 0.5f;
		UpdateDormant();
	}
	if (bDormant)
	{
		return;
	}

	// Parked near the player, the ground under a car may not be streamed in yet: it would fall through the world.
	GroundCheck -= DeltaSeconds;
	if (!bPickingUp && (GroundCheck <= 0.f || (bHeldNoGround && GetController())))
	{
		GroundCheck = 0.5f;
		HoldWithoutGround();
	}

	UpdateCart(DeltaSeconds);
	StabilityAssist(DeltaSeconds);
	KeepUpright(DeltaSeconds);
	UpdateWheelie(DeltaSeconds);
	UpdateFootBack(DeltaSeconds);
	UpdateRiderless(DeltaSeconds);
	LastVelocity = GetVelocity();
	UpdateDamage(DeltaSeconds);
	UpdateLightsAndSound(DeltaSeconds);

	// Camera: free look with the mouse, back behind the car after a moment; a little wider when fast.
	LookIdle += DeltaSeconds;
	if (LookIdle > 1.5f)
	{
		LookOffset = FMath::RInterpTo(LookOffset, FRotator::ZeroRotator, DeltaSeconds, 2.5f);
	}
	SpringArm->SetRelativeRotation(bLookBack ? FRotator(-10.f, 180.f, 0.f) : FRotator(-12.f + LookOffset.Pitch, LookOffset.Yaw, 0.f));
	SpringArm->TargetArmLength = FMath::FInterpTo(SpringArm->TargetArmLength, bClose ? CloseDistance : ChaseDistance, DeltaSeconds, 4.f);
	const float Speed = FMath::Abs(GetSpeedKmh());
	Camera->SetFieldOfView(FMath::FInterpTo(Camera->FieldOfView, 78.f + FMath::Min(Speed, 100.f) * 0.1f, DeltaSeconds, 2.f));

	// Stuck on its side or roof: put it back after a few seconds (not a moped: it lies there until picked up).
	if (!IsTwoWheeler() && GetActorUpVector().Z < 0.25f && Speed < 5.f)
	{
		UpsideDownTime += DeltaSeconds;
		if (UpsideDownTime > 3.f)
		{
			PutBackOnWheels();
		}
	}
	else
	{
		UpsideDownTime = 0.f;
	}
}

void AM80Car::UpdateDormant()
{
	// Well inside World Partition's loading range (192 m): ground is only streamed out further away.
	constexpr double SleepCm = 12000.0;
	constexpr double WakeCm = 10000.0;
	const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!Player || IsPlayerControlled() || bPickingUp)
	{
		SetDormant(false);
		return;
	}
	const double Distance = FVector::Dist2D(Player->GetActorLocation(), GetActorLocation());
	if (Distance > SleepCm)
	{
		SetDormant(true);
	}
	else if (Distance < WakeCm)
	{
		SetDormant(false);
	}
}

void AM80Car::SetDormant(bool bNow)
{
	if (bDormant == bNow)
	{
		return;
	}
	bDormant = bNow;
	USkeletalMeshComponent* Body = GetMesh();
	UChaosWheeledVehicleMovementComponent* M = Movement(this);
	if (bNow)
	{
		// Removes the vehicle with its suspension constraints (and rebuilds the body without them).
		if (M)
		{
			M->DestroyPhysicsState();
		}
		Body->SetSimulatePhysics(false);
		UE_LOG(LogTemp, Verbose, TEXT("%s: at rest, away from the player"), *GetName());
		return;
	}
	Body->SetSimulatePhysics(!bHeldNoGround);
	if (M)
	{
		M->CreatePhysicsState();
		if (!GetController())
		{
			M->SetHandbrakeInput(true);
		}
	}
	UE_LOG(LogTemp, Verbose, TEXT("%s: vehicle physics back, the player is near"), *GetName());
}

void AM80Car::HoldWithoutGround()
{
	USkeletalMeshComponent* Body = GetMesh();
	const FVector At = GetActorLocation();
	FHitResult Hit;
	const FCollisionQueryParams Params(SCENE_QUERY_STAT(M80CarGround), false, this);
	const bool bGround = GetController() || GetWorld()->LineTraceSingleByObjectType(Hit, At + FVector(0, 0, 200), At - FVector(0, 0, 5000),
		FCollisionObjectQueryParams(ECC_WorldStatic), Params);
	if (!bGround && !bHeldNoGround && Body->IsSimulatingPhysics())
	{
		Body->SetSimulatePhysics(false);
		bHeldNoGround = true;
	}
	else if (bGround && bHeldNoGround)
	{
		Body->SetSimulatePhysics(true);
		bHeldNoGround = false;
	}
}

void AM80Car::StabilityAssist(float DeltaSeconds)
{
	UChaosWheeledVehicleMovementComponent* M = Movement(this);
	USkeletalMeshComponent* Body = GetMesh();
	// Not on a two-wheeler its rider has left: catching its sideways slide would catch it falling over too (it rocked and
	// stood up again).
	if (!bStabilityAssist || bHandbrakeHeld || !M || !Body->IsSimulatingPhysics() || GetActorUpVector().Z < 0.8f || (IsTwoWheeler() && bFallen))
	{
		return;
	}
	int32 OnGround = 0;
	for (int32 i = 0; i < M->Wheels.Num(); ++i)
	{
		OnGround += M->GetWheelState(i).bInContact ? 1 : 0;
	}
	if (OnGround < M->Wheels.Num() - 1)
	{
		return;  // airborne or on two wheels: leave it to physics
	}
	const FVector V = Body->GetPhysicsLinearVelocity();
	const FVector Up = GetActorUpVector();
	const float Fwd = V | GetActorForwardVector();
	const float Lat = V | GetActorRightVector();
	const float Speed = FMath::Sqrt(Fwd * Fwd + Lat * Lat);
	if (Speed < 300.f)
	{
		return;  // below ~11 km/h
	}
	// Yaw rate the steering asks for (bicycle model), no more than the tyres can give at this speed.
	// (from the input and the speed curve, the same way Chaos turns the wheels)
	float MaxSteer = 0.f;
	for (const UChaosVehicleWheel* W : M->Wheels)
	{
		if (W && W->bAffectedBySteering)
		{
			MaxSteer = W->MaxSteerAngle;
			break;
		}
	}
	const float Mph = FMath::Abs(Fwd) * 0.022369f;
	const float SteerDeg = M->GetSteeringInput() * MaxSteer * M->SteeringSetup.SteeringCurve.GetRichCurveConst()->Eval(Mph);
	const float GripAccel = GripG * 981.f;
	float Wanted = Fwd * FMath::Tan(FMath::DegreesToRadians(SteerDeg)) / WheelbaseCm;
	Wanted = FMath::Clamp(Wanted, -GripAccel / Speed, GripAccel / Speed);
	const float Yaw = Body->GetPhysicsAngularVelocityInRadians() | Up;
	// Only take away the extra yaw (oversteer, spin); never add yaw.
	const float Excess = (FMath::Sign(Yaw) != FMath::Sign(Wanted) || FMath::Abs(Yaw) > FMath::Abs(Wanted)) ? Yaw - Wanted : 0.f;
	if (FMath::Abs(Excess) > 0.05f)
	{
		Body->AddTorqueInRadians(Up * (-Excess * 9.f), NAME_None, true);
	}
	// Sliding sideways more than ~7 degrees: tyres "bite" back (grip help scales with the slide).
	const float Slip = FMath::RadiansToDegrees(FMath::Atan2(FMath::Abs(Lat), FMath::Abs(Fwd)));
	if (Slip > 7.f)
	{
		const float K = FMath::Clamp((Slip - 7.f) / 20.f, 0.f, 1.f) * 3.f;
		Body->AddForce(-GetActorRightVector() * Lat * K, NAME_None, true);
	}
}

void AM80Car::BuildInput()
{
	if (Mapping)
	{
		return;
	}
	auto MakeAction = [this](EInputActionValueType Type)
	{
		UInputAction* A = NewObject<UInputAction>(this);
		A->ValueType = Type;
		return A;
	};
	ThrottleAction = MakeAction(EInputActionValueType::Axis1D);
	BrakeAction = MakeAction(EInputActionValueType::Axis1D);
	SteerAction = MakeAction(EInputActionValueType::Axis1D);
	HandbrakeAction = MakeAction(EInputActionValueType::Boolean);
	LookAction = MakeAction(EInputActionValueType::Axis2D);
	CameraAction = MakeAction(EInputActionValueType::Boolean);
	ResetAction = MakeAction(EInputActionValueType::Boolean);
	HornAction = MakeAction(EInputActionValueType::Boolean);
	LightsAction = MakeAction(EInputActionValueType::Boolean);
	LookBackAction = MakeAction(EInputActionValueType::Boolean);
	WheelieAction = MakeAction(EInputActionValueType::Boolean);

	Mapping = NewObject<UInputMappingContext>(this);
	auto Negated = [this](FEnhancedActionKeyMapping& Map) { Map.Modifiers.Add(NewObject<UInputModifierNegate>(this)); };
	auto DeadZone = [this](FEnhancedActionKeyMapping& Map) { Map.Modifiers.Add(NewObject<UInputModifierDeadZone>(this)); };
	Mapping->MapKey(ThrottleAction, EKeys::W);
	Mapping->MapKey(ThrottleAction, EKeys::Up);
	Mapping->MapKey(ThrottleAction, EKeys::Gamepad_RightTriggerAxis);
	Mapping->MapKey(BrakeAction, EKeys::S);
	Mapping->MapKey(BrakeAction, EKeys::Down);
	Mapping->MapKey(BrakeAction, EKeys::Gamepad_LeftTriggerAxis);
	Mapping->MapKey(SteerAction, EKeys::D);
	Mapping->MapKey(SteerAction, EKeys::Right);
	Negated(Mapping->MapKey(SteerAction, EKeys::A));
	Negated(Mapping->MapKey(SteerAction, EKeys::Left));
	DeadZone(Mapping->MapKey(SteerAction, EKeys::Gamepad_LeftX));
	Mapping->MapKey(HandbrakeAction, EKeys::SpaceBar);
	Mapping->MapKey(HandbrakeAction, EKeys::Gamepad_FaceButton_Bottom);
	Mapping->MapKey(LookAction, EKeys::Mouse2D);
	DeadZone(Mapping->MapKey(LookAction, EKeys::Gamepad_Right2D));
	Mapping->MapKey(CameraAction, EKeys::C);
	Mapping->MapKey(CameraAction, EKeys::Gamepad_RightThumbstick);
	Mapping->MapKey(ResetAction, EKeys::R);
	Mapping->MapKey(ResetAction, EKeys::Gamepad_Special_Left);
	Mapping->MapKey(HornAction, EKeys::H);
	Mapping->MapKey(HornAction, EKeys::Gamepad_LeftThumbstick);
	Mapping->MapKey(LightsAction, EKeys::L);
	Mapping->MapKey(LightsAction, EKeys::Gamepad_DPad_Up);
	Mapping->MapKey(LookBackAction, EKeys::B);
	Mapping->MapKey(LookBackAction, EKeys::Gamepad_RightShoulder);
	Mapping->MapKey(WheelieAction, EKeys::LeftShift);
	Mapping->MapKey(WheelieAction, EKeys::Gamepad_FaceButton_Left);
}

void AM80Car::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);
	BuildInput();
	UEnhancedInputComponent* Input = Cast<UEnhancedInputComponent>(PlayerInputComponent);
	if (!Input)
	{
		return;
	}
	Input->BindAction(ThrottleAction, ETriggerEvent::Triggered, this, &AM80Car::OnThrottle);
	Input->BindAction(ThrottleAction, ETriggerEvent::Completed, this, &AM80Car::OnThrottle);
	Input->BindAction(BrakeAction, ETriggerEvent::Triggered, this, &AM80Car::OnBrake);
	Input->BindAction(BrakeAction, ETriggerEvent::Completed, this, &AM80Car::OnBrake);
	Input->BindAction(SteerAction, ETriggerEvent::Triggered, this, &AM80Car::OnSteer);
	Input->BindAction(SteerAction, ETriggerEvent::Completed, this, &AM80Car::OnSteer);
	Input->BindAction(HandbrakeAction, ETriggerEvent::Started, this, &AM80Car::OnHandbrake);
	Input->BindAction(HandbrakeAction, ETriggerEvent::Completed, this, &AM80Car::OnHandbrake);
	Input->BindAction(LookAction, ETriggerEvent::Triggered, this, &AM80Car::OnLook);
	Input->BindAction(CameraAction, ETriggerEvent::Started, this, &AM80Car::OnToggleCamera);
	Input->BindAction(ResetAction, ETriggerEvent::Started, this, &AM80Car::OnReset);
	Input->BindAction(HornAction, ETriggerEvent::Started, this, &AM80Car::Horn);
	Input->BindAction(LightsAction, ETriggerEvent::Started, this, &AM80Car::ToggleLights);
	Input->BindAction(LookBackAction, ETriggerEvent::Started, this, &AM80Car::OnLookBack);
	Input->BindAction(LookBackAction, ETriggerEvent::Completed, this, &AM80Car::OnLookBack);
	Input->BindAction(WheelieAction, ETriggerEvent::Started, this, &AM80Car::Wheelie);
}

void AM80Car::NotifyControllerChanged()
{
	Super::NotifyControllerChanged();
	BuildInput();
	// The driving controls only while someone drives this car.
	if (APlayerController* Old = InputOwner.Get())
	{
		if (UEnhancedInputLocalPlayerSubsystem* Sub = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(Old->GetLocalPlayer()))
		{
			Sub->RemoveMappingContext(Mapping);
		}
		InputOwner.Reset();
	}
	if (APlayerController* PC = Cast<APlayerController>(GetController()))
	{
		if (bFallen && IsTwoWheeler())
		{
			GripLoose(false);
		}
		bFallen = false;   // a rider on it again holds it up
		TipTime = 0.f;
		if (UEnhancedInputLocalPlayerSubsystem* Sub = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
		{
			Sub->AddMappingContext(Mapping, 0);
			InputOwner = PC;
		}
		if (UChaosWheeledVehicleMovementComponent* M = Movement(this))
		{
			M->SetHandbrakeInput(false);
		}
	}
	else if (UChaosWheeledVehicleMovementComponent* M = Movement(this))
	{
		// Nobody driving: engine idle; the handbrake goes on once it has stopped (a driver who jumped
		// out of a moving car leaves it rolling on).
		M->SetThrottleInput(0.f);
		M->SetBrakeInput(0.f);
		M->SetSteeringInput(0.f);
		CartPush = CartBrake = 0.f;
		bCoasting = FMath::Abs(GetSpeedKmh()) > 8.f;
		if (IsTwoWheeler() && !bFallen && FMath::Abs(GetSpeedKmh()) > 5.f)
		{
			// Jumped off it moving: nobody holds it up any more (UpdateRiderless).
			bFallen = true;
			GripLoose(true);
			SinceThrown = 0.f;
			ToppleSide = GetActorRightVector().Z < 0.f ? 1.f : -1.f;
		}
		M->SetHandbrakeInput(!bCoasting);
		SteerTarget = 0.f;
	}
}

void AM80Car::OnThrottle(const FInputActionValue& Value)
{
	if (bWrecked)
	{
		return;
	}
	if (bCart)
	{
		CartPush = FMath::Clamp(Value.Get<float>(), 0.f, 1.f);
		if (UChaosWheeledVehicleMovementComponent* M = Movement(this))
		{
			M->SetHandbrakeInput(false);
		}
		return;
	}
	if (UChaosWheeledVehicleMovementComponent* M = Movement(this))
	{
		M->SetThrottleInput(FMath::Clamp(Value.Get<float>(), 0.f, 1.f));
		M->SetHandbrakeInput(false);
	}
}

void AM80Car::OnBrake(const FInputActionValue& Value)
{
	if (bCart)
	{
		CartBrake = FMath::Clamp(Value.Get<float>(), 0.f, 1.f);
		return;
	}
	if (IsTwoWheeler())
	{
		CartBrake = FMath::Clamp(Value.Get<float>(), 0.f, 1.f);   // also walking it back once stopped (UpdateFootBack)
	}
	if (UChaosWheeledVehicleMovementComponent* M = Movement(this))
	{
		M->SetBrakeInput(FMath::Clamp(Value.Get<float>(), 0.f, 1.f));
	}
}

void AM80Car::OnSteer(const FInputActionValue& Value)
{
	SteerTarget = FMath::Clamp(Value.Get<float>(), -1.f, 1.f);
}

void AM80Car::OnHandbrake(const FInputActionValue& Value)
{
	if (UChaosWheeledVehicleMovementComponent* M = Movement(this))
	{
		bHandbrakeHeld = Value.Get<bool>();
		M->SetHandbrakeInput(bHandbrakeHeld);
	}
}

void AM80Car::OnLook(const FInputActionValue& Value)
{
	const FVector2D V = Value.Get<FVector2D>();
	LookOffset.Yaw = FMath::Clamp(LookOffset.Yaw + V.X * 2.f, -170.f, 170.f);
	LookOffset.Pitch = FMath::Clamp(LookOffset.Pitch + V.Y * 1.5f, -25.f, 30.f);
	LookIdle = 0.f;
}

void AM80Car::OnLookBack(const FInputActionValue& Value)
{
	bLookBack = Value.Get<bool>();
}

void AM80Car::OnToggleCamera()
{
	bClose = !bClose;
}

void AM80Car::OnReset()
{
	PutBackOnWheels();
}

// ---------------------------------------------------------------------------------------------
// Fiat 500 F

AM80CarFiat500::AM80CarFiat500()
{
	DisplayName = NSLOCTEXT("M80", "Fiat500", "Fiat 500");
	SetupImported(TEXT("/Game/Mazzarino80/Vehicles/Fiat500/SK_M80_Fiat500.SK_M80_Fiat500"), UM80Wheel500Front::StaticClass(), UM80Wheel500Rear::StaticClass());
	ChaseDistance = 460.f;
	SeatOffset = FVector(20.f, -22.f, 45.f);     // low roof: seated low and leaning back, the head under the highest part, elbows in
	SeatRecline = 24.f;
	DoorOffset = FVector(-5.f, -150.f, 100.f);
	MaxHealth = 550.f;
	EngineOffset = FVector(-130.f, 0.f, 60.f);      // engine at the back
	HeadlightOffset = FVector(138.f, 45.f, 62.f);
	TaillightOffset = FVector(-154.f, 48.f, 68.f);
	FCarSpec S;
	S.MassKg = 590.f;                       // 520 kg + driver
	S.CenterOfMass = FVector(-25, 0, -15);  // engine behind the rear axle
	S.DragCoefficient = 0.45f;
	S.ChassisWidth = 132.f;
	S.ChassisHeight = 132.f;
	S.MaxTorqueNm = 46.f;                   // 30 Nm real, livelier in game
	S.MaxRPM = 5400.f;
	S.IdleRPM = 850.f;
	S.PeakTorqueRPM = 3200.f;
	S.Gears = {3.70f, 2.07f, 1.30f, 0.875f};
	S.ReverseGear = 5.1f;
	S.FinalRatio = 5.9f;                    // ~100 km/h in 4th at the limiter
	S.ChangeUpRPM = 4900.f;
	S.ChangeDownRPM = 1800.f;
	S.SteerAt30Mph = 0.3f;
	S.SteerAt60Mph = 0.14f;
	S.WheelbaseCm = 184.f;
	S.GripG = 0.85f;
	ApplySpec(S);
}

// ---------------------------------------------------------------------------------------------
// Downloaded cars (Research/Mazzarino80/Blender/m80_auto_sorgente.py): sizes from Saved/Mazzarino80/Import/out/<key>.json

AM80CarMini::AM80CarMini()
{
	DisplayName = NSLOCTEXT("M80", "Mini", "Mini Cooper S");
	SetupImported(TEXT("/Game/Mazzarino80/Vehicles/Mini/SK_M80_Mini.SK_M80_Mini"), UM80WheelMiniFront::StaticClass(), UM80WheelMiniRear::StaticClass());
	ChaseDistance = 450.f;
	SeatOffset = FVector(-25.f, -28.f, 45.f);
	SeatRecline = 18.f;
	DoorOffset = FVector(-20.f, -150.f, 100.f);
	MaxHealth = 550.f;
	EngineOffset = FVector(110.f, 0.f, 60.f);
	HeadlightOffset = FVector(140.f, 50.f, 70.f);
	TaillightOffset = FVector(-152.f, 55.f, 70.f);
	FCarSpec S;
	S.MassKg = 720.f;                      // 650 kg + driver
	S.CenterOfMass = FVector(20, 0, -15);  // engine and gearbox over the front wheels
	S.DragCoefficient = 0.42f;
	S.ChassisWidth = 141.f;
	S.ChassisHeight = 135.f;
	S.MaxTorqueNm = 110.f;
	S.MaxRPM = 6500.f;
	S.IdleRPM = 850.f;
	S.PeakTorqueRPM = 3000.f;
	S.Gears = {3.2f, 1.9f, 1.35f, 1.0f};
	S.ReverseGear = 3.2f;
	S.FinalRatio = 3.44f;
	S.ChangeUpRPM = 6000.f;
	S.ChangeDownRPM = 2500.f;
	S.Drive = EVehicleDifferential::FrontWheelDrive;
	S.SteerAt30Mph = 0.5f;
	S.SteerAt60Mph = 0.3f;
	S.WheelbaseCm = 201.f;
	S.GripG = 0.95f;                       // the go-kart of the rallies
	ApplySpec(S);
}

AM80CarMaggiolino::AM80CarMaggiolino()
{
	DisplayName = NSLOCTEXT("M80", "Maggiolino", "Maggiolino");
	SetupImported(TEXT("/Game/Mazzarino80/Vehicles/Maggiolino/SK_M80_Maggiolino.SK_M80_Maggiolino"), UM80WheelMaggiolinoFront::StaticClass(), UM80WheelMaggiolinoRear::StaticClass());
	ChaseDistance = 520.f;
	SeatOffset = FVector(-10.f, -30.f, 52.f);
	SeatRecline = 10.f;
	DoorOffset = FVector(-10.f, -160.f, 100.f);
	MaxHealth = 650.f;
	EngineOffset = FVector(-180.f, 0.f, 60.f);
	HeadlightOffset = FVector(175.f, 55.f, 80.f);
	TaillightOffset = FVector(-208.f, 58.f, 75.f);
	FCarSpec S;
	S.MassKg = 920.f;
	S.CenterOfMass = FVector(-30, 0, -10);  // engine behind the rear axle
	S.DragCoefficient = 0.48f;
	S.ChassisWidth = 154.f;
	S.ChassisHeight = 150.f;
	S.MaxTorqueNm = 120.f;
	S.MaxRPM = 4800.f;
	S.IdleRPM = 800.f;
	S.PeakTorqueRPM = 2600.f;
	S.Gears = {3.8f, 2.06f, 1.26f, 0.89f};
	S.ReverseGear = 3.88f;
	S.FinalRatio = 4.125f;
	S.ChangeUpRPM = 4300.f;
	S.ChangeDownRPM = 1800.f;
	S.SteerAt30Mph = 0.45f;
	S.SteerAt60Mph = 0.25f;
	S.WheelbaseCm = 242.f;
	S.GripG = 0.85f;
	ApplySpec(S);
}

AM80CarGolf::AM80CarGolf()
{
	DisplayName = NSLOCTEXT("M80", "Golf", "Golf GTI");
	SetupImported(TEXT("/Game/Mazzarino80/Vehicles/Golf/SK_M80_Golf.SK_M80_Golf"), UM80WheelGolfFront::StaticClass(), UM80WheelGolfRear::StaticClass());
	ChaseDistance = 500.f;
	SeatOffset = FVector(-25.f, -32.f, 45.f);
	SeatRecline = 12.f;
	DoorOffset = FVector(-20.f, -165.f, 100.f);
	MaxHealth = 650.f;
	EngineOffset = FVector(150.f, 0.f, 60.f);
	HeadlightOffset = FVector(185.f, 52.f, 70.f);
	TaillightOffset = FVector(-176.f, 55.f, 80.f);
	FCarSpec S;
	S.MassKg = 890.f;
	S.CenterOfMass = FVector(25, 0, -15);
	S.DragCoefficient = 0.42f;
	S.ChassisWidth = 161.f;
	S.ChassisHeight = 139.f;
	S.MaxTorqueNm = 155.f;
	S.MaxRPM = 6800.f;
	S.IdleRPM = 900.f;
	S.PeakTorqueRPM = 5000.f;
	S.Gears = {3.45f, 2.12f, 1.44f, 1.13f, 0.91f};
	S.ReverseGear = 3.17f;
	S.FinalRatio = 3.9f;
	S.ChangeUpRPM = 6300.f;
	S.ChangeDownRPM = 2800.f;
	S.Drive = EVehicleDifferential::FrontWheelDrive;
	S.SteerAt30Mph = 0.5f;
	S.SteerAt60Mph = 0.28f;
	S.WheelbaseCm = 237.f;
	S.GripG = 0.95f;
	ApplySpec(S);
}

AM80CarAlfa155::AM80CarAlfa155()
{
	DisplayName = NSLOCTEXT("M80", "Alfa155", "Alfa 155 Carabinieri");
	SetupImported(TEXT("/Game/Mazzarino80/Vehicles/Alfa155C/SK_M80_Alfa155C.SK_M80_Alfa155C"), UM80WheelAlfa155Front::StaticClass(), UM80WheelAlfa155Rear::StaticClass());
	ChaseDistance = 560.f;
	SeatOffset = FVector(-25.f, -35.f, 45.f);
	SeatRecline = 12.f;
	DoorOffset = FVector(-20.f, -170.f, 100.f);
	MaxHealth = 800.f;
	EngineOffset = FVector(170.f, 0.f, 60.f);
	HeadlightOffset = FVector(212.f, 52.f, 60.f);
	TaillightOffset = FVector(-210.f, 60.f, 85.f);
	FCarSpec S;
	S.MassKg = 1330.f;                      // 1250 kg + two Carabinieri
	S.CenterOfMass = FVector(30, 0, -15);   // engine across over the front wheels
	S.DragCoefficient = 0.30f;
	S.ChassisWidth = 170.f;
	S.ChassisHeight = 144.f;
	S.MaxTorqueNm = 187.f;
	S.MaxRPM = 6500.f;
	S.IdleRPM = 850.f;
	S.PeakTorqueRPM = 4000.f;
	S.Gears = {3.5f, 1.96f, 1.36f, 1.03f, 0.84f};
	S.ReverseGear = 3.55f;
	S.FinalRatio = 3.73f;
	S.ChangeUpRPM = 6200.f;
	S.ChangeDownRPM = 2800.f;
	S.Drive = EVehicleDifferential::FrontWheelDrive;
	S.SteerAt30Mph = 0.5f;
	S.SteerAt60Mph = 0.28f;
	S.WheelbaseCm = 254.f;
	S.GripG = 0.95f;
	ApplySpec(S);
}

void AM80CarAlfa155::BeginPlay()
{
	Super::BeginPlay();
	USkeletalMeshComponent* Body = GetMesh();
	// The beacon's glass: its own material slot (Lampeggiante), made dynamic to flash.
	const TArray<FName> Slots = Body->GetMaterialSlotNames();
	for (int32 i = 0; i < Slots.Num(); ++i)
	{
		if (Slots[i].ToString().Contains(TEXT("Lampeggiante")))
		{
			BeaconGlass = Body->CreateDynamicMaterialInstance(i);
			break;
		}
	}
	BeaconLight = NewObject<UPointLightComponent>(this);
	BeaconLight->SetupAttachment(Body);
	BeaconLight->SetRelativeLocation(BeaconOffset);
	BeaconLight->SetLightColor(FLinearColor(0.05f, 0.2f, 1.f));
	BeaconLight->SetAttenuationRadius(1800.f);
	BeaconLight->SetIntensity(0.f);
	BeaconLight->SetCastShadows(false);
	BeaconLight->RegisterComponent();
}

void AM80CarAlfa155::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const bool bOn = bLampeggiante && GetController() != nullptr && Health > 0.f;
	float Flash = 0.f;
	if (bOn)
	{
		// The mirror turning round the bulb: a short bright sweep each turn, a faint glow between.
		BeaconPhase = FMath::Fmod(BeaconPhase + DeltaSeconds * BeaconTurns, 1.f);
		Flash = FMath::Pow(FMath::Max(0.f, FMath::Cos(BeaconPhase * 2.f * PI)), 8.f);
	}
	if (BeaconLight)
	{
		BeaconLight->SetIntensity(bOn ? 30000.f * Flash : 0.f);
	}
	if (BeaconGlass)
	{
		const float Glow = bOn ? 0.6f + 40.f * Flash : 0.05f;
		BeaconGlass->SetVectorParameterValue(TEXT("Emissivo"), FLinearColor(0.05f * Glow, 0.25f * Glow, 1.f * Glow));
	}
}

AM80CarM3::AM80CarM3()
{
	DisplayName = NSLOCTEXT("M80", "M3", "BMW M3");
	SetupImported(TEXT("/Game/Mazzarino80/Vehicles/M3/SK_M80_M3.SK_M80_M3"), UM80WheelM3Front::StaticClass(), UM80WheelM3Rear::StaticClass());
	ChaseDistance = 540.f;
	SeatOffset = FVector(-35.f, -35.f, 45.f);
	SeatRecline = 15.f;
	DoorOffset = FVector(-30.f, -170.f, 100.f);
	MaxHealth = 750.f;
	EngineOffset = FVector(150.f, 0.f, 55.f);
	HeadlightOffset = FVector(198.f, 55.f, 65.f);
	TaillightOffset = FVector(-228.f, 60.f, 85.f);
	FCarSpec S;
	S.MassKg = 1280.f;
	S.CenterOfMass = FVector(5, 0, -20);
	S.DragCoefficient = 0.38f;
	S.ChassisWidth = 168.f;
	S.ChassisHeight = 137.f;
	S.MaxTorqueNm = 260.f;
	S.MaxRPM = 7200.f;
	S.IdleRPM = 900.f;
	S.PeakTorqueRPM = 4750.f;
	S.Gears = {3.72f, 2.40f, 1.77f, 1.26f, 1.0f};
	S.ReverseGear = 4.23f;
	S.FinalRatio = 3.25f;
	S.ChangeUpRPM = 6900.f;
	S.ChangeDownRPM = 3200.f;
	S.SteerAt30Mph = 0.45f;
	S.SteerAt60Mph = 0.25f;
	S.WheelbaseCm = 253.f;
	S.GripG = 1.0f;
	ApplySpec(S);
}

// ---------------------------------------------------------------------------------------------
// Ape

AM80CarApe::AM80CarApe()
{
	DisplayName = NSLOCTEXT("M80", "Ape", "Ape Piaggio");
	// Dense mesh (1.7 M vertices, LODs from Scripts/m80_cars_lods.py); kept out of Git, see .gitignore.
	static ConstructorHelpers::FObjectFinderOptional<USkeletalMesh> MeshAsset(TEXT("/Game/Drive/ApeCar/ApeDrivable.ApeDrivable"));
	static ConstructorHelpers::FClassFinder<UAnimInstance> AnimClass(TEXT("/Game/Drive/Anim/ApeCar_Anim_BP"));
	GetMesh()->SetSkeletalMesh(MeshAsset.Get());
	GetMesh()->SetAnimInstanceClass(AnimClass.Class);
	ChaseDistance = 450.f;
	SeatOffset = FVector(60.f, 0.f, 125.f);  // central seat in the cab
	DoorOffset = FVector(55.f, -150.f, 100.f);
	MaxHealth = 400.f;
	EngineOffset = FVector(-20.f, 0.f, 60.f);       // under the bed, behind the cab
	HeadlightOffset = FVector(128.f, 0.f, 105.f);   // one round light on the front
	TaillightOffset = FVector(-170.f, 55.f, 70.f);

	if (UChaosWheeledVehicleMovementComponent* M = Movement(this))
	{
		M->WheelSetups.SetNum(3);
		M->WheelSetups[0].WheelClass = UM80WheelApeFront::StaticClass();
		M->WheelSetups[0].BoneName = TEXT("Circle");
		M->WheelSetups[1].WheelClass = UM80WheelApeRear::StaticClass();
		M->WheelSetups[1].BoneName = TEXT("Circle_001");
		M->WheelSetups[2].WheelClass = UM80WheelApeRear::StaticClass();
		M->WheelSetups[2].BoneName = TEXT("Circle_002");
	}
	FCarSpec S;
	S.MassKg = 480.f;
	S.CenterOfMass = FVector(-20, 0, -30);  // low, over the rear axle: three wheels tip easily
	S.DragCoefficient = 0.65f;              // a box
	S.ChassisWidth = 125.f;
	S.ChassisHeight = 160.f;
	S.MaxTorqueNm = 22.f;
	S.MaxRPM = 6000.f;
	S.IdleRPM = 1000.f;
	S.PeakTorqueRPM = 4000.f;
	S.RevUpMOI = 3.f;
	S.Gears = {3.6f, 2.2f, 1.45f, 1.f};
	S.ReverseGear = 3.6f;
	S.FinalRatio = 10.f;                    // ~60 km/h flat out
	S.ChangeUpRPM = 5600.f;
	S.ChangeDownRPM = 2000.f;
	S.GearChangeTime = 0.5f;
	S.SteerAt30Mph = 0.3f;                  // at 50 km/h on three wheels, little lock
	S.SteerAt60Mph = 0.2f;
	S.WheelbaseCm = 195.f;
	S.GripG = 0.6f;                         // tips over before it slides
	S.ThrottleRise = 1.8f;
	ApplySpec(S);
}

// ---------------------------------------------------------------------------------------------
// Two-wheelers (D:/Mazzarino80_Sorgenti/Auto/Piaggio_Si, Research/Mazzarino80/Blender/m80_motorino_gioco.py)

AM80CarPiaggioSi::AM80CarPiaggioSi()
{
	DisplayName = NSLOCTEXT("M80", "PiaggioSi", "Piaggio Si");
	SetupImported(TEXT("/Game/Mazzarino80/Vehicles/PiaggioSi/SK_M80_PiaggioSi.SK_M80_PiaggioSi"), UM80WheelSiFront::StaticClass(), UM80WheelSiRear::StaticClass(), true);
	// The rider: astride (Sella bone), the hands on the grips and the feet on the pedals (Mano_*, Piede_*), got on from the left.
	RidePose = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Mazzarino80/Player/Anim/A_M80_Motorino_Guida.A_M80_Motorino_Guida")));
	MountClip = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Mazzarino80/Player/Anim/A_M80_Motorino_Sale.A_M80_Motorino_Sale")));
	PickUpClip = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Mazzarino80/Player/Anim/A_M80_Motorino_Raccoglie.A_M80_Motorino_Raccoglie")));
	DismountClip = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Mazzarino80/Player/Anim/A_M80_Motorino_Scende.A_M80_Motorino_Scende")));
	ChaseDistance = 360.f;
	CloseDistance = 230.f;
	SpringArm->SetRelativeLocation(FVector(0.f, 0.f, 95.f));
	SeatOffset = FVector(-35.f, 0.f, 75.f);    // the saddle
	DoorOffset = FVector(-23.f, -45.f, 60.f);  // where the getting-on clip starts (PiaggioSi.json "mount_from_cm")
	MaxHealth = 200.f;
	EngineOffset = FVector(-20.f, 8.f, 30.f);  // under the frame, by the pedals
	HeadlightOffset = FVector(36.f, 0.f, 86.f);
	TaillightOffset = FVector(-84.f, 0.f, 62.f);
	LockedChance = 0.f;
	FCarSpec S;
	S.MassKg = 130.f;                          // ~55 kg + rider
	S.CenterOfMass = FVector(-10.f, 0.f, -10.f);
	S.DragCoefficient = 0.6f;
	S.ChassisWidth = 60.f;
	S.ChassisHeight = 120.f;
	S.MaxTorqueNm = 6.f;                       // with the variator's low ratios at start: 0-40 km/h in about 8 s
	S.MaxRPM = 6500.f;
	S.IdleRPM = 1500.f;
	S.PeakTorqueRPM = 5000.f;
	S.EngineBrake = 0.04f;
	S.RevUpMOI = 1.0f;
	S.Gears = {1.0f};                          // the variator: one ratio
	S.ReverseGear = 3.0f;                      // no reverse on a moped: backing it with the feet, slowly
	S.FinalRatio = 13.0f;                      // ~47 km/h flat out
	S.ChangeUpRPM = 6400.f;
	S.ChangeDownRPM = 2000.f;
	S.Drive = EVehicleDifferential::RearWheelDrive;
	S.SteerAt30Mph = 0.4f;
	S.SteerAt60Mph = 0.25f;
	S.WheelbaseCm = 108.f;
	S.GripG = 0.8f;
	S.MaxLeanDeg = 35.f;
	ApplySpec(S);
}

// ---------------------------------------------------------------------------------------------
// Soapbox carts (D:/Mazzarino80_Sorgenti/Carretti, Research/Mazzarino80/Blender/m80_carretti_gioco.py)

UM80WheelCuscinetto::UM80WheelCuscinetto()
{
	Size(3.6f, 3.2f, false);
}

void UM80WheelCuscinetto::Size(float RadiusCm, float WidthCm, bool bSteer)
{
	// Steel on stone: little grip, no suspension to speak of. The feet brake (mostly at the back), the handbrake is
	// the heels dragging behind.
	SetupWheel(this, bSteer ? EAxleType::Front : EAxleType::Rear, RadiusCm, WidthCm, bSteer ? 26.f : 0.f, bSteer ? 4.f : 8.f,
		bSteer ? 0.f : 14.f, false, 40.f, 12.f, 0.6f, 1.5f, 1.5f, 1.6f);
	WheelMass = 1.5f;
}

UM80WheelCuscinetti36Sterzo::UM80WheelCuscinetti36Sterzo() { Size(3.6f, 3.2f, true); }
UM80WheelCuscinetti36::UM80WheelCuscinetti36() { Size(3.6f, 3.2f, false); }
UM80WheelCuscinetti42Sterzo::UM80WheelCuscinetti42Sterzo() { Size(4.21f, 3.74f, true); }
UM80WheelCuscinetti42::UM80WheelCuscinetti42() { Size(4.21f, 3.74f, false); }
UM80WheelCuscinetti29Sterzo::UM80WheelCuscinetti29Sterzo() { Size(2.88f, 2.56f, true); }
UM80WheelCuscinetti47::UM80WheelCuscinetti47() { Size(4.68f, 4.16f, false); }
UM80WheelCuscinetti30::UM80WheelCuscinetti30() { Size(2.95f, 2.62f, false); }
UM80WheelCuscinetti41Sterzo::UM80WheelCuscinetti41Sterzo() { Size(4.14f, 3.68f, true); }

namespace
{
FString CartMesh(const TCHAR* Key)
{
	return FString::Printf(TEXT("/Game/Mazzarino80/Vehicles/Carretti/%s/SK_M80_%s.SK_M80_%s"), Key, Key, Key);
}

FString CartPose(const TCHAR* Key)
{
	return FString::Printf(TEXT("/Game/Mazzarino80/Player/Anim/A_M80_Carretto_%s.A_M80_Carretto_%s"), Key, Key);
}
}

AM80Carretto::AM80Carretto()
{
	bCart = true;
	LockedChance = 0.f;
	MaxHealth = 1000.f;
	ChaseDistance = 330.f;
	CloseDistance = 210.f;
	SpringArm->SetRelativeLocation(FVector(0.f, 0.f, 70.f));
}

AM80CarrettoCuscinetti::AM80CarrettoCuscinetti()
{
	DisplayName = NSLOCTEXT("M80", "CarrettoCuscinetti", "carretto a cuscinetti");
	SetupCart(*CartMesh(TEXT("CarrettoCuscinetti")), *CartPose(TEXT("Cuscinetti")),
		{{TEXT("Wheel_FL"), UM80WheelCuscinetti36Sterzo::StaticClass()}, {TEXT("Wheel_FR"), UM80WheelCuscinetti36Sterzo::StaticClass()},
		 {TEXT("Wheel_RL"), UM80WheelCuscinetti36::StaticClass()}, {TEXT("Wheel_RR"), UM80WheelCuscinetti36::StaticClass()}}, 61.f);
	DoorOffset = FVector(-20.f, -85.f, 60.f);
}

AM80CarrettoTriangolo::AM80CarrettoTriangolo()
{
	DisplayName = NSLOCTEXT("M80", "CarrettoTriangolo", "carretto a triangolo");
	SetupCart(*CartMesh(TEXT("CarrettoTriangolo")), *CartPose(TEXT("Triangolo")),
		{{TEXT("Wheel_FL"), UM80WheelCuscinetti42Sterzo::StaticClass()}, {TEXT("Wheel_FR"), UM80WheelCuscinetti42Sterzo::StaticClass()},
		 {TEXT("Wheel_RL"), UM80WheelCuscinetti42::StaticClass()}, {TEXT("Wheel_RR"), UM80WheelCuscinetti42::StaticClass()}}, 112.f);
	DoorOffset = FVector(-15.f, -90.f, 60.f);
}

AM80CarrettoCassetta::AM80CarrettoCassetta()
{
	DisplayName = NSLOCTEXT("M80", "CarrettoCassetta", "carretto con la cassetta");
	SetupCart(*CartMesh(TEXT("CarrettoCassetta")), *CartPose(TEXT("Cassetta")),
		{{TEXT("Wheel_FL"), UM80WheelCuscinetti29Sterzo::StaticClass()}, {TEXT("Wheel_FR"), UM80WheelCuscinetti29Sterzo::StaticClass()},
		 {TEXT("Wheel_RL"), UM80WheelCuscinetti47::StaticClass()}, {TEXT("Wheel_RR"), UM80WheelCuscinetti30::StaticClass()}}, 80.f);
	DoorOffset = FVector(-25.f, -85.f, 60.f);
}

AM80CarrettoPersiana::AM80CarrettoPersiana()
{
	DisplayName = NSLOCTEXT("M80", "CarrettoPersiana", "carretto persiana");
	SetupCart(*CartMesh(TEXT("CarrettoPersiana")), *CartPose(TEXT("Persiana")),
		{{TEXT("Wheel_F"), UM80WheelCuscinetti41Sterzo::StaticClass()}, {TEXT("Wheel_RL"), UM80WheelCuscinetti36::StaticClass()},
		 {TEXT("Wheel_RR"), UM80WheelCuscinetti36::StaticClass()}}, 106.f);
	DoorOffset = FVector(-25.f, -85.f, 60.f);
}
