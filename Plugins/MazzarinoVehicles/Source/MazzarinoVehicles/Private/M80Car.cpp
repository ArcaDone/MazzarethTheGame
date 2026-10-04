#include "M80Car.h"
#include "M80WheelAnim.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/AudioComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SpotLightComponent.h"
#include "Engine/DamageEvents.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
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

UM80WheelFiatFront::UM80WheelFiatFront()
{
	SetupWheel(this, EAxleType::Front, 25.f, 15.f, 38.f, 900.f, 0.f, false, 140.f, 60.f, 0.45f, 8.f, 10.f);
}

UM80WheelFiatRear::UM80WheelFiatRear()
{
	// The engine sits over the rear axle: stiffer springs, more grip at the back so the tail stays put.
	SetupWheel(this, EAxleType::Rear, 25.f, 15.f, 0.f, 650.f, 1800.f, true, 175.f, 70.f, 0.45f, 8.f, 10.f, 2.7f);
}

UM80WheelApeFront::UM80WheelApeFront()
{
	SetupWheel(this, EAxleType::Front, 27.f, 12.f, 42.f, 450.f, 0.f, false, 110.f, 40.f, 0.5f, 7.f, 9.f);
}

UM80WheelApeRear::UM80WheelApeRear()
{
	SetupWheel(this, EAxleType::Rear, 27.f, 14.f, 0.f, 450.f, 1200.f, true, 150.f, 60.f, 0.5f, 7.f, 9.f, 2.6f);
}

namespace
{
// Wheel radius and width (cm) of the imported meshes.
constexpr float WHEEL127R = 29.6f, WHEEL127W = 15.7f;
constexpr float WHEELUNOR = 28.f, WHEELUNOW = 16.f;
constexpr float WHEELVESPAR = 23.1f, WHEELVESPAW = 10.f;
}

// Imported cars: front-wheel drive, the rear axle carries the handbrake and a little more grip.
// Radius and width measured on the meshes (Saved/Mazzarino80/Import/out/<car>.json).
UM80WheelPandaFront::UM80WheelPandaFront() { SetupWheel(this, EAxleType::Front, 25.5f, 19.f, 36.f, 1000.f, 0.f, true, 150.f, 60.f, 0.45f, 8.f, 10.f); }
UM80WheelPandaRear::UM80WheelPandaRear() { SetupWheel(this, EAxleType::Rear, 25.5f, 19.f, 0.f, 700.f, 1800.f, false, 140.f, 60.f, 0.45f, 8.f, 10.f, 2.7f); }
UM80Wheel127Front::UM80Wheel127Front() { SetupWheel(this, EAxleType::Front, WHEEL127R, WHEEL127W, 36.f, 1000.f, 0.f, true, 150.f, 60.f, 0.45f, 8.f, 10.f); }
UM80Wheel127Rear::UM80Wheel127Rear() { SetupWheel(this, EAxleType::Rear, WHEEL127R, WHEEL127W, 0.f, 700.f, 1800.f, false, 140.f, 60.f, 0.45f, 8.f, 10.f, 2.7f); }
UM80WheelUnoFront::UM80WheelUnoFront() { SetupWheel(this, EAxleType::Front, WHEELUNOR, WHEELUNOW, 36.f, 1050.f, 0.f, true, 155.f, 60.f, 0.45f, 8.f, 10.f); }
UM80WheelUnoRear::UM80WheelUnoRear() { SetupWheel(this, EAxleType::Rear, WHEELUNOR, WHEELUNOW, 0.f, 700.f, 1800.f, false, 145.f, 60.f, 0.45f, 8.f, 10.f, 2.7f); }
UM80WheelGolfFront::UM80WheelGolfFront() { SetupWheel(this, EAxleType::Front, 26.6f, 20.f, 34.f, 1400.f, 0.f, true, 190.f, 70.f, 0.5f, 7.f, 9.f, 2.4f); }
UM80WheelGolfRear::UM80WheelGolfRear() { SetupWheel(this, EAxleType::Rear, 26.6f, 20.f, 0.f, 900.f, 2000.f, false, 180.f, 70.f, 0.5f, 7.f, 9.f, 2.8f); }
UM80WheelVespaFront::UM80WheelVespaFront() { SetupWheel(this, EAxleType::Front, WHEELVESPAR, WHEELVESPAW, 30.f, 250.f, 0.f, false, 60.f, 20.f, 0.5f, 6.f, 8.f, 2.4f); }
UM80WheelVespaRear::UM80WheelVespaRear() { SetupWheel(this, EAxleType::Rear, WHEELVESPAR, WHEELVESPAW, 0.f, 200.f, 500.f, true, 70.f, 25.f, 0.5f, 6.f, 8.f, 2.6f); }

// ---------------------------------------------------------------------------------------------
// Base car

AM80Car::AM80Car()
{
	PrimaryActorTick.bCanEverTick = true;
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
	USkeletalMeshComponent* Body = GetMesh();
	Body->OnComponentHit.AddUniqueDynamic(this, &AM80Car::OnBodyHit);
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
	if (DeltaV < 500.f)
	{
		return;
	}
	HitCooldown = 0.25f;
	Health = FMath::Max(0.f, Health - (DeltaV - 500.f) * 0.06f);
	UGameplayStatics::PlaySoundAtLocation(this, LoadPath<USoundBase>(CrashSound), Hit.ImpactPoint, FMath::Clamp(DeltaV / 1500.f, 0.3f, 1.5f), 0.6f);
}

void AM80Car::UpdateDamage(float DeltaSeconds)
{
	HitCooldown -= DeltaSeconds;
	if (bWrecked)
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
	if (bWrecked)
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
	if (!bWrecked)
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

void AM80Car::KeepUpright(float DeltaSeconds)
{
	// Two wheels: Chaos would let it fall over. A spring-damper on the roll holds it up and leans it
	// into the bend (more lean with more speed and more steering), like a rider would.
	USkeletalMeshComponent* Body = GetMesh();
	UChaosWheeledVehicleMovementComponent* M = Movement(this);
	if (MaxLeanDeg <= 0.f || !Body->IsSimulatingPhysics() || !M)
	{
		return;
	}
	const FVector Fwd = GetActorForwardVector();
	const float Speed = FMath::Abs(GetSpeedKmh());
	const float Lean = -M->GetSteeringInput() * MaxLeanDeg * FMath::Clamp(Speed / 40.f, 0.f, 1.f);
	const float Roll = FMath::RadiansToDegrees(FMath::Asin(FMath::Clamp(GetActorRightVector().Z, -1.f, 1.f)));
	const float RollRate = FMath::RadiansToDegrees(Body->GetPhysicsAngularVelocityInRadians() | Fwd);
	const float Accel = (Lean - Roll) * 40.f - RollRate * 7.f;   // deg/s^2
	Body->AddTorqueInDegrees(Fwd * Accel, NAME_None, true);
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

void AM80Car::PutBackOnWheels()
{
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

	StabilityAssist(DeltaSeconds);
	KeepUpright(DeltaSeconds);
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

	// Stuck on its side or roof: put it back after a few seconds.
	if (GetActorUpVector().Z < 0.25f && Speed < 5.f)
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

void AM80Car::StabilityAssist(float DeltaSeconds)
{
	UChaosWheeledVehicleMovementComponent* M = Movement(this);
	USkeletalMeshComponent* Body = GetMesh();
	if (!bStabilityAssist || bHandbrakeHeld || !M || !Body->IsSimulatingPhysics() || GetActorUpVector().Z < 0.8f)
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
		bCoasting = FMath::Abs(GetSpeedKmh()) > 8.f;
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
	if (UChaosWheeledVehicleMovementComponent* M = Movement(this))
	{
		M->SetThrottleInput(FMath::Clamp(Value.Get<float>(), 0.f, 1.f));
		M->SetHandbrakeInput(false);
	}
}

void AM80Car::OnBrake(const FInputActionValue& Value)
{
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
// Fiat 126

AM80CarFiat126::AM80CarFiat126()
{
	DisplayName = NSLOCTEXT("M80", "Fiat126", "Fiat 126");
	static ConstructorHelpers::FObjectFinder<USkeletalMesh> MeshAsset(TEXT("/Game/Drive/fiat126/fiat126.fiat126"));
	static ConstructorHelpers::FClassFinder<UAnimInstance> AnimClass(TEXT("/Game/Drive/Anim/BP_Fiat126"));
	GetMesh()->SetSkeletalMesh(MeshAsset.Object);
	GetMesh()->SetAnimInstanceClass(AnimClass.Class);
	ChaseDistance = 480.f;
	SeatOffset = FVector(-30.f, -35.f, 85.f);
	DoorOffset = FVector(-5.f, -165.f, 100.f);
	MaxHealth = 600.f;
	EngineOffset = FVector(-125.f, 0.f, 70.f);      // engine at the back
	HeadlightOffset = FVector(150.f, 48.f, 62.f);
	TaillightOffset = FVector(-152.f, 52.f, 72.f);

	if (UChaosWheeledVehicleMovementComponent* M = Movement(this))
	{
		M->WheelSetups.SetNum(4);
		M->WheelSetups[0].WheelClass = UM80WheelFiatFront::StaticClass();
		M->WheelSetups[0].BoneName = TEXT("Wheel_FL");
		M->WheelSetups[1].WheelClass = UM80WheelFiatFront::StaticClass();
		M->WheelSetups[1].BoneName = TEXT("Wheel_FR");
		M->WheelSetups[2].WheelClass = UM80WheelFiatRear::StaticClass();
		M->WheelSetups[2].BoneName = TEXT("Wheel_RL");
		M->WheelSetups[3].WheelClass = UM80WheelFiatRear::StaticClass();
		M->WheelSetups[3].BoneName = TEXT("Wheel_RR");
	}
	FCarSpec S;
	S.MassKg = 650.f;                       // 580 kg + driver
	S.CenterOfMass = FVector(-25, 0, -15);  // engine behind the rear axle
	S.DragCoefficient = 0.42f;
	S.ChassisWidth = 138.f;
	S.ChassisHeight = 134.f;
	S.MaxTorqueNm = 56.f;                   // 39 Nm real, a bit more so it is not a chore in game
	S.MaxRPM = 5800.f;
	S.IdleRPM = 850.f;
	S.PeakTorqueRPM = 3400.f;
	S.Gears = {3.25f, 2.07f, 1.30f, 0.87f};
	S.ReverseGear = 3.2f;
	S.FinalRatio = 6.2f;                    // ~108 km/h in 4th at the limiter
	S.ChangeUpRPM = 5200.f;
	S.ChangeDownRPM = 1800.f;              // fewer shifts back and forth in bends
	S.SteerAt30Mph = 0.3f;                  // 38 degrees of lock -> 11 at 50 km/h, 5 at 100
	S.SteerAt60Mph = 0.14f;
	S.WheelbaseCm = 184.f;
	S.GripG = 0.85f;
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
// Cars imported from Blender (D:/Blender/AssetsMazzarethTheGame, Research/Mazzarino80/Blender/m80_prepare_vehicle.py)

AM80Car::FCarSpec AM80Car::SmallFiatSpec()
{
	FCarSpec S;
	S.MassKg = 760.f;                       // ~690 kg + driver
	S.CenterOfMass = FVector(25, 0, -10);   // engine in front
	S.DragCoefficient = 0.42f;
	S.ChassisWidth = 150.f;
	S.ChassisHeight = 140.f;
	S.MaxTorqueNm = 85.f;                   // 64 Nm real, livelier in game (as the 126)
	S.MaxRPM = 6000.f;
	S.IdleRPM = 850.f;
	S.PeakTorqueRPM = 3200.f;
	S.Gears = {3.91f, 2.06f, 1.30f, 0.89f};
	S.ReverseGear = 3.7f;
	S.FinalRatio = 4.4f;                    // ~145 km/h in 4th
	S.ChangeUpRPM = 5400.f;
	S.ChangeDownRPM = 1900.f;
	S.Drive = EVehicleDifferential::FrontWheelDrive;
	S.SteerAt30Mph = 0.32f;
	S.SteerAt60Mph = 0.15f;
	S.WheelbaseCm = 215.f;
	S.GripG = 0.85f;
	return S;
}

AM80CarPanda::AM80CarPanda()
{
	DisplayName = NSLOCTEXT("M80", "Panda", "Fiat Panda");
	SetupImported(TEXT("/Game/Mazzarino80/Vehicles/Panda/SK_M80_Panda.SK_M80_Panda"), UM80WheelPandaFront::StaticClass(), UM80WheelPandaRear::StaticClass());
	SeatOffset = FVector(-20.f, -35.f, 85.f);
	DoorOffset = FVector(-5.f, -165.f, 100.f);
	EngineOffset = FVector(130.f, 0.f, 70.f);
	HeadlightOffset = FVector(165.f, 55.f, 70.f);
	TaillightOffset = FVector(-166.f, 58.f, 75.f);
	FCarSpec S = SmallFiatSpec();
	S.WheelbaseCm = 210.f;
	ApplySpec(S);
}

AM80CarFiat127::AM80CarFiat127()
{
	DisplayName = NSLOCTEXT("M80", "Fiat127", "Fiat 127");
	SetupImported(TEXT("/Game/Mazzarino80/Vehicles/Fiat127/SK_M80_Fiat127.SK_M80_Fiat127"), UM80Wheel127Front::StaticClass(), UM80Wheel127Rear::StaticClass());
	SeatOffset = FVector(-20.f, -35.f, 80.f);
	DoorOffset = FVector(-5.f, -160.f, 100.f);
	EngineOffset = FVector(130.f, 0.f, 65.f);
	HeadlightOffset = FVector(175.f, 55.f, 65.f);
	TaillightOffset = FVector(-176.f, 55.f, 70.f);
	FCarSpec S = SmallFiatSpec();
	S.MassKg = 780.f;
	S.Gears = {3.58f, 2.24f, 1.45f, 1.04f};
	S.FinalRatio = 4.08f;
	S.WheelbaseCm = 222.f;
	ApplySpec(S);
}

AM80CarFiatUno::AM80CarFiatUno()
{
	DisplayName = NSLOCTEXT("M80", "FiatUno", "Fiat Uno");
	SetupImported(TEXT("/Game/Mazzarino80/Vehicles/FiatUno/SK_M80_FiatUno.SK_M80_FiatUno"), UM80WheelUnoFront::StaticClass(), UM80WheelUnoRear::StaticClass());
	SeatOffset = FVector(-15.f, -35.f, 82.f);
	DoorOffset = FVector(0.f, -165.f, 100.f);
	EngineOffset = FVector(135.f, 0.f, 70.f);
	HeadlightOffset = FVector(178.f, 55.f, 68.f);
	TaillightOffset = FVector(-178.f, 58.f, 78.f);
	FCarSpec S = SmallFiatSpec();
	S.MassKg = 790.f;
	S.MaxTorqueNm = 90.f;
	S.Gears = {3.91f, 2.06f, 1.34f, 0.98f};
	S.FinalRatio = 4.2f;
	S.DragCoefficient = 0.34f;              // the Uno was a slippery one
	S.WheelbaseCm = 236.f;
	ApplySpec(S);
}

AM80CarGolf::AM80CarGolf()
{
	DisplayName = NSLOCTEXT("M80", "Golf", "Volkswagen Golf GTI");
	SetupImported(TEXT("/Game/Mazzarino80/Vehicles/Golf/SK_M80_Golf.SK_M80_Golf"), UM80WheelGolfFront::StaticClass(), UM80WheelGolfRear::StaticClass());
	SeatOffset = FVector(-20.f, -35.f, 75.f);
	DoorOffset = FVector(-5.f, -165.f, 95.f);
	EngineOffset = FVector(135.f, 0.f, 65.f);
	HeadlightOffset = FVector(183.f, 50.f, 62.f);
	TaillightOffset = FVector(-178.f, 55.f, 75.f);
	FCarSpec S;
	S.MassKg = 890.f;                       // 810 kg + driver
	S.CenterOfMass = FVector(25, 0, -12);
	S.DragCoefficient = 0.40f;
	S.ChassisWidth = 162.f;
	S.ChassisHeight = 139.f;
	S.MaxTorqueNm = 175.f;                  // 140 Nm real
	S.MaxRPM = 6800.f;
	S.IdleRPM = 900.f;
	S.PeakTorqueRPM = 5000.f;
	S.Gears = {3.45f, 2.12f, 1.44f, 1.13f, 0.91f};
	S.ReverseGear = 3.4f;
	S.FinalRatio = 3.9f;                    // ~180 km/h in 5th
	S.ChangeUpRPM = 6300.f;
	S.ChangeDownRPM = 2500.f;
	S.Drive = EVehicleDifferential::FrontWheelDrive;
	S.SteerAt30Mph = 0.28f;
	S.SteerAt60Mph = 0.12f;
	S.WheelbaseCm = 231.f;
	S.GripG = 0.95f;
	ApplySpec(S);
}

AM80CarVespa::AM80CarVespa()
{
	DisplayName = NSLOCTEXT("M80", "Vespa", "Vespa Piaggio");
	SetupImported(TEXT("/Game/Mazzarino80/Vehicles/Vespa/SK_M80_Vespa.SK_M80_Vespa"), UM80WheelVespaFront::StaticClass(), UM80WheelVespaRear::StaticClass(), true);
	ChaseDistance = 380.f;
	CloseDistance = 240.f;
	SeatOffset = FVector(-25.f, 0.f, 120.f); // on the saddle
	DoorOffset = FVector(-10.f, -110.f, 95.f);
	MaxHealth = 250.f;
	EngineOffset = FVector(-50.f, 15.f, 35.f); // under the right side cowl
	HeadlightOffset = FVector(55.f, 0.f, 105.f);
	TaillightOffset = FVector(-85.f, 0.f, 70.f);
	LockedChance = 0.f;
	FCarSpec S;
	S.MassKg = 160.f;                       // ~85 kg + rider
	S.CenterOfMass = FVector(-10, 0, -15);
	S.DragCoefficient = 0.6f;
	S.ChassisWidth = 70.f;
	S.ChassisHeight = 115.f;
	S.MaxTorqueNm = 14.f;
	S.MaxRPM = 7000.f;
	S.IdleRPM = 1400.f;
	S.PeakTorqueRPM = 5000.f;
	S.RevUpMOI = 1.5f;
	S.Gears = {3.0f, 1.9f, 1.35f, 1.0f};
	S.ReverseGear = 3.0f;
	S.FinalRatio = 7.0f;                    // ~80 km/h flat out
	S.ChangeUpRPM = 6500.f;
	S.ChangeDownRPM = 2800.f;
	S.Drive = EVehicleDifferential::RearWheelDrive;
	S.SteerAt30Mph = 0.35f;
	S.SteerAt60Mph = 0.2f;
	S.WheelbaseCm = 120.f;
	S.GripG = 0.8f;
	S.MaxLeanDeg = 25.f;
	ApplySpec(S);
}
