#pragma once

#include "CoreMinimal.h"
#include "WheeledVehiclePawn.h"
#include "ChaosVehicleWheel.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "M80Car.generated.h"

class USpringArmComponent;
class UCameraComponent;
class UAudioComponent;
class USpotLightComponent;
class UPointLightComponent;
class UParticleSystemComponent;
class UAnimSequenceBase;
class AM80Car;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FM80CarExploded, AM80Car*, Car);
class UInputAction;
class UInputMappingContext;
struct FInputActionValue;

/**
 * Drivable period car (Chaos Vehicles). The subclasses carry the real data of each vehicle
 * (mass, engine, gears, steering, suspension) so that each one drives like what it is.
 * Controls are built in code (no input assets): W/S or arrows, A/D, Space handbrake, mouse to look,
 * C camera, R put back on the wheels, H horn, L lights, B look back; gamepad: triggers, left stick, A,
 * left stick click horn, D-pad up lights, right shoulder look back.
 * Damage (GTA style): crashes and shots take its health; white smoke, black smoke, fire, then it blows
 * up (radial damage around, burnt shell). Some parked cars are locked: the window gets broken.
 */
UCLASS(Abstract, meta = (DisplayName = "Auto Mazzarino (base)"))
class MAZZARINOVEHICLES_API AM80Car : public AWheeledVehiclePawn
{
	GENERATED_BODY()

public:
	AM80Car();

	virtual void Tick(float DeltaSeconds) override;
	virtual void BeginPlay() override;
	virtual float TakeDamage(float DamageAmount, struct FDamageEvent const& DamageEvent, AController* EventInstigator, AActor* DamageCauser) override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;
	virtual void NotifyControllerChanged() override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Auto")
	TObjectPtr<USpringArmComponent> SpringArm;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Auto")
	TObjectPtr<UCameraComponent> Camera;

	/** Name shown by the test HUD. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Auto", meta = (DisplayName = "Nome"))
	FText DisplayName;

	/** Driver seat, in the car's local space: where the driver's capsule centre goes when seated. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Auto|Guidatore")
	FVector SeatOffset = FVector(-20, -35, 30);

	/** Degrees the seated driver leans back (low cars: the head goes down and back, the feet up and forward). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Auto|Guidatore")
	float SeatRecline = 0.f;

	/** Where the driver stands to get in/out (left side, local space). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Auto|Guidatore")
	FVector DoorOffset = FVector(0, -150, 60);

	/** Arm length of the chase camera and of the close one (C). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Auto|Camera")
	float ChaseDistance = 520.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Auto|Camera")
	float CloseDistance = 300.f;

	/**
	 * Driving help (GTA style): the car never turns faster than its tyres can hold, a sliding rear end
	 * is caught. Off while the handbrake is held, so handbrake turns still work.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Auto|Guida")
	bool bStabilityAssist = true;

	/** Health of the car: smoke under half, fire under a tenth, then it blows up. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Auto|Danni")
	float MaxHealth = 600.f;

	UPROPERTY(BlueprintReadOnly, Category = "Auto|Danni")
	float Health = 600.f;

	/** Blown up: a burnt shell, cannot be driven. */
	UPROPERTY(BlueprintReadOnly, Category = "Auto|Danni")
	bool bWrecked = false;

	/** Where the engine is (smoke and fire come out of it), local space. */
	UPROPERTY(EditAnywhere, Category = "Auto|Danni")
	FVector EngineOffset = FVector(-120.f, 0.f, 60.f);

	/** Headlight (and its mirror at -Y; Y = 0 means a single central one) and tail light, local space. */
	UPROPERTY(EditAnywhere, Category = "Auto|Luci")
	FVector HeadlightOffset = FVector(150.f, 50.f, 65.f);

	UPROPERTY(EditAnywhere, Category = "Auto|Luci")
	FVector TaillightOffset = FVector(-150.f, 50.f, 75.f);

	/** Parked and locked: getting in breaks the window. Decided at start for cars nobody drives. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Auto")
	bool bLocked = false;

	UPROPERTY(EditAnywhere, Category = "Auto")
	float LockedChance = 0.35f;

	/**
	 * Soapbox cart (carrettu): no engine. W pushes it (slowly, up to PushTopKmh on the flat), downhill it rolls
	 * by itself; S brakes with the feet and, once stopped, shuffles it back. No engine sound, lights, smoke or
	 * fire, it does not blow up. The rider takes RidePose; its mesh has the bones Sella (where the rider's mesh
	 * origin goes), Mano_L/R and Piede_L/R (wrists and ankles, under the steering when they hold it).
	 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Auto|Carretto", meta = (DisplayName = "Carretto (senza motore)"))
	bool bCart = false;

	/** Pose of the rider on this vehicle (UEFN mannequin); none: the driving pose of the cars. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Auto|Guidatore")
	TSoftObjectPtr<UAnimSequenceBase> RidePose;

	/** Cart: top speed pushing it on the flat (km/h) and how hard the push is (cm/s2). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Auto|Carretto")
	float PushTopKmh = 13.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Auto|Carretto")
	float PushAccel = 160.f;

	/** Cart: rolling resistance of steel bearings on stone (fraction of g) and air drag of the rider (1/m). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Auto|Carretto")
	float RollingResistance = 0.035f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Auto|Carretto")
	float AirDrag = 0.0035f;

	/** Cart controls from code (tests, AI): push 0..1 forward, brake / back 0..1, steering -1..1 (right +). */
	UFUNCTION(BlueprintCallable, Category = "Auto|Carretto")
	void SetCartInput(float Push, float Brake, float Steer = 0.f) { CartPush = Push; CartBrake = Brake; SteerTarget = Steer; }

	UPROPERTY(BlueprintAssignable, Category = "Auto")
	FM80CarExploded OnExploded;

	UFUNCTION(BlueprintCallable, Category = "Auto")
	void Explode();

	UFUNCTION(BlueprintCallable, Category = "Auto")
	void Horn();

	UFUNCTION(BlueprintCallable, Category = "Auto")
	void ToggleLights();

	/** Breaks the driver's window (getting into a locked car). */
	UFUNCTION(BlueprintCallable, Category = "Auto")
	void BreakWindow();

	UFUNCTION(BlueprintPure, Category = "Auto")
	bool AreLightsOn() const { return bLights; }

	UFUNCTION(BlueprintPure, Category = "Auto")
	float GetSpeedKmh() const;

	UFUNCTION(BlueprintPure, Category = "Auto")
	int32 GetGear() const;

	UFUNCTION(BlueprintPure, Category = "Auto")
	float GetEngineRPM() const;

	/** Lifts the car, puts it back on its wheels facing the same way and stops it. */
	UFUNCTION(BlueprintCallable, Category = "Auto")
	void PutBackOnWheels();

protected:
	/** Fills the Chaos setup. Called by the subclasses' constructors. */
	struct FCarSpec
	{
		float MassKg = 800.f;
		FVector CenterOfMass = FVector(0, 0, -20);
		float DragCoefficient = 0.4f;
		float ChassisWidth = 150.f;
		float ChassisHeight = 140.f;
		// Engine
		float MaxTorqueNm = 100.f;
		float MaxRPM = 6000.f;
		float IdleRPM = 900.f;
		float PeakTorqueRPM = 3500.f;
		float EngineBrake = 0.06f;
		float RevUpMOI = 5.f;
		float RevDownRate = 600.f;
		// Gearbox (automatic)
		TArray<float> Gears = {3.f, 2.f, 1.4f, 1.f};
		float ReverseGear = 3.f;
		float FinalRatio = 4.f;
		float ChangeUpRPM = 5000.f;
		float ChangeDownRPM = 2200.f;
		float GearChangeTime = 0.35f;
		EVehicleDifferential Drive = EVehicleDifferential::RearWheelDrive;
		// Steering: max fraction of the wheel angle at 0, 30 and 60+ MPH
		float SteerAt30Mph = 0.75f;
		float SteerAt60Mph = 0.5f;
		// Input smoothing (per second)
		float ThrottleRise = 2.5f, ThrottleFall = 5.f;
		float SteerRise = 2.2f, SteerFall = 4.f;
		float BrakeRise = 5.f, BrakeFall = 8.f;
		// Stability help
		float StabilizeRoll = 0.f;
		// Two-wheelers: kept upright by the game, leaning into bends up to this angle
		float MaxLeanDeg = 0.f;
		float WheelbaseCm = 220.f;
		float GripG = 0.85f;   // sideways grip of the tyres (g)
	};
	void ApplySpec(const FCarSpec& Spec);

	/**
	 * Cars imported from Blender (Scripts/m80_import_blender_assets.py): skeletal mesh with bones Root +
	 * Wheel_FL/FR/RL/RR (or Wheel_F/Wheel_R for two-wheelers), wheels animated in code (UM80WheelAnimInstance).
	 */
	void SetupImported(const TCHAR* MeshPath, TSubclassOf<UChaosVehicleWheel> Front, TSubclassOf<UChaosVehicleWheel> Rear, bool bTwoWheels = false);

	/**
	 * Carts from Research/Mazzarino80/Blender/m80_carretti_gioco.py: skeletal mesh with Root, Steer, the wheels
	 * (one wheel class each), Sella, Mano_L/R, Piede_L/R; the rider's pose; slow, light, low grip.
	 */
	void SetupCart(const TCHAR* MeshPath, const TCHAR* PosePath, const TArray<TPair<FName, TSubclassOf<UChaosVehicleWheel>>>& Wheels, float InWheelbaseCm);

private:
	void OnThrottle(const FInputActionValue& Value);
	void OnBrake(const FInputActionValue& Value);
	void OnSteer(const FInputActionValue& Value);
	void OnHandbrake(const FInputActionValue& Value);
	void OnLook(const FInputActionValue& Value);
	void OnToggleCamera();
	void OnReset();
	void OnLookBack(const FInputActionValue& Value);
	void BuildInput();
	void UpdateDamage(float DeltaSeconds);
	void UpdateLightsAndSound(float DeltaSeconds);
	UFUNCTION()
	void OnBodyHit(UPrimitiveComponent* HitComp, AActor* Other, UPrimitiveComponent* OtherComp, FVector NormalImpulse, const FHitResult& Hit);

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> EngineAudio;
	UPROPERTY(Transient)
	TArray<TObjectPtr<USpotLightComponent>> Headlights;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UPointLightComponent>> Taillights;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystemComponent> Smoke;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystemComponent> Fire;
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> HornAction;
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> LightsAction;
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> LookBackAction;
	bool bLights = false;
	bool bLookBack = false;
	int32 SmokeLevel = 0;
	float BurnTime = -1.f;
	float HitCooldown = 0.f;

	UPROPERTY(Transient)
	TObjectPtr<UInputMappingContext> Mapping;
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> ThrottleAction;
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> BrakeAction;
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> SteerAction;
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> HandbrakeAction;
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> LookAction;
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> CameraAction;
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> ResetAction;

	float SteerTarget = 0.f;
	FRotator LookOffset = FRotator::ZeroRotator;
	float LookIdle = 0.f;
	bool bClose = false;
	float UpsideDownTime = 0.f;
	/** Without a driver and with no ground streamed in under it, the body is held still (not simulated). */
	void HoldWithoutGround();
	float GroundCheck = 0.f;
	bool bHeldNoGround = false;
	float WheelbaseCm = 220.f;
	float GripG = 0.85f;
	bool bHandbrakeHeld = false;
	void StabilityAssist(float DeltaSeconds);
	bool bCoasting = false;
	float MaxLeanDeg = 0.f;
	void KeepUpright(float DeltaSeconds);
	TWeakObjectPtr<APlayerController> InputOwner;
	void UpdateCart(float DeltaSeconds);
	float CartPush = 0.f;
	float CartBrake = 0.f;
};

/** Fiat 500 F (1965-72): 499.5 cc rear engine, 18 hp, about 520 kg, rear-wheel drive, top speed about 95 km/h.
 * The town's common car (Research/Mazzarino80/Blender/m80_fiat500_sorgente.py: engine under the lid dropped, not decimated). */
UCLASS(meta = (DisplayName = "Fiat 500 (guidabile)"))
class MAZZARINOVEHICLES_API AM80CarFiat500 : public AM80Car
{
	GENERATED_BODY()
public:
	AM80CarFiat500();
};

/** Mini Cooper S (1965): 1275 cc front engine, 76 hp, about 650 kg, front-wheel drive, 10 inch wheels, top speed about
 * 160 km/h. Downloaded game-ready model, not decimated (Research/Mazzarino80/Blender/m80_auto_sorgente.py). */
UCLASS(meta = (DisplayName = "Mini Cooper S (guidabile)"))
class MAZZARINOVEHICLES_API AM80CarMini : public AM80Car
{
	GENERATED_BODY()
public:
	AM80CarMini();
};

/** Volkswagen Maggiolino 1500 (1968): flat-four rear engine, 44 hp, about 840 kg, rear-wheel drive, top speed about 125 km/h. */
UCLASS(meta = (DisplayName = "Maggiolino (guidabile)"))
class MAZZARINOVEHICLES_API AM80CarMaggiolino : public AM80Car
{
	GENERATED_BODY()
public:
	AM80CarMaggiolino();
};

/** Volkswagen Golf GTI (1976): 1588 cc, 110 hp, about 810 kg, front-wheel drive, top speed about 182 km/h. */
UCLASS(meta = (DisplayName = "Golf GTI (guidabile)"))
class MAZZARINOVEHICLES_API AM80CarGolf : public AM80Car
{
	GENERATED_BODY()
public:
	AM80CarGolf();
};

/** BMW M3 E30 Evolution II (1988): 2.3 l four, 220 hp, about 1200 kg, rear-wheel drive, top speed about 245 km/h. */
UCLASS(meta = (DisplayName = "BMW M3 (guidabile)"))
class MAZZARINOVEHICLES_API AM80CarM3 : public AM80Car
{
	GENERATED_BODY()
public:
	AM80CarM3();
};

/** Piaggio Ape (P501 type, late 70s): 3 wheels, small engine, about 450 kg, top speed about 60 km/h. Slow, short gears, leans in fast turns. */
UCLASS(meta = (DisplayName = "Ape Piaggio (guidabile)"))
class MAZZARINOVEHICLES_API AM80CarApe : public AM80Car
{
	GENERATED_BODY()
public:
	AM80CarApe();
};

/** Vespa 125 (Primavera type): 125 cc two-stroke, 6 hp, about 80 kg, 10 inch wheels, top speed about 80 km/h. Kept upright by the game. */
UCLASS(meta = (DisplayName = "Vespa Piaggio (guidabile)"))
class MAZZARINOVEHICLES_API AM80CarVespa : public AM80Car
{
	GENERATED_BODY()
public:
	AM80CarVespa();
};

/** Wheels: one class per axle and vehicle, values set in the constructors. */
UCLASS()
class MAZZARINOVEHICLES_API UM80WheelApeFront : public UChaosVehicleWheel
{
	GENERATED_BODY()
public:
	UM80WheelApeFront();
};

UCLASS()
class MAZZARINOVEHICLES_API UM80WheelApeRear : public UChaosVehicleWheel
{
	GENERATED_BODY()
public:
	UM80WheelApeRear();
};

UCLASS()
class MAZZARINOVEHICLES_API UM80Wheel500Front : public UChaosVehicleWheel
{
	GENERATED_BODY()
public:
	UM80Wheel500Front();
};

UCLASS()
class MAZZARINOVEHICLES_API UM80Wheel500Rear : public UChaosVehicleWheel
{
	GENERATED_BODY()
public:
	UM80Wheel500Rear();
};

UCLASS()
class MAZZARINOVEHICLES_API UM80WheelMiniFront : public UChaosVehicleWheel
{
	GENERATED_BODY()
public:
	UM80WheelMiniFront();
};

UCLASS()
class MAZZARINOVEHICLES_API UM80WheelMiniRear : public UChaosVehicleWheel
{
	GENERATED_BODY()
public:
	UM80WheelMiniRear();
};

UCLASS()
class MAZZARINOVEHICLES_API UM80WheelMaggiolinoFront : public UChaosVehicleWheel
{
	GENERATED_BODY()
public:
	UM80WheelMaggiolinoFront();
};

UCLASS()
class MAZZARINOVEHICLES_API UM80WheelMaggiolinoRear : public UChaosVehicleWheel
{
	GENERATED_BODY()
public:
	UM80WheelMaggiolinoRear();
};

UCLASS()
class MAZZARINOVEHICLES_API UM80WheelGolfFront : public UChaosVehicleWheel
{
	GENERATED_BODY()
public:
	UM80WheelGolfFront();
};

UCLASS()
class MAZZARINOVEHICLES_API UM80WheelGolfRear : public UChaosVehicleWheel
{
	GENERATED_BODY()
public:
	UM80WheelGolfRear();
};

UCLASS()
class MAZZARINOVEHICLES_API UM80WheelM3Front : public UChaosVehicleWheel
{
	GENERATED_BODY()
public:
	UM80WheelM3Front();
};

UCLASS()
class MAZZARINOVEHICLES_API UM80WheelM3Rear : public UChaosVehicleWheel
{
	GENERATED_BODY()
public:
	UM80WheelM3Rear();
};

UCLASS()
class MAZZARINOVEHICLES_API UM80WheelVespaFront : public UChaosVehicleWheel
{
	GENERATED_BODY()
public:
	UM80WheelVespaFront();
};

UCLASS()
class MAZZARINOVEHICLES_API UM80WheelVespaRear : public UChaosVehicleWheel
{
	GENERATED_BODY()
public:
	UM80WheelVespaRear();
};

/** Soapbox carts (carretti): wooden boards on steel ball bearings, steered by a pivoting front axle. */
UCLASS(Abstract, meta = (DisplayName = "Carretto (base)"))
class MAZZARINOVEHICLES_API AM80Carretto : public AM80Car
{
	GENERATED_BODY()
public:
	AM80Carretto();
};

/** A plank on four bearings: the rider lies on it on the chest (as on a sled) and steers with the bar at the front. */
UCLASS(meta = (DisplayName = "Carretto a cuscinetti (guidabile)"))
class MAZZARINOVEHICLES_API AM80CarrettoCuscinetti : public AM80Carretto
{
	GENERATED_BODY()
public:
	AM80CarrettoCuscinetti();
};

/** Two rails in a triangle, a seat of slats: sitting as in a go-kart, heels on the front axle, the rope in the hands. */
UCLASS(meta = (DisplayName = "Carretto a triangolo (guidabile)"))
class MAZZARINOVEHICLES_API AM80CarrettoTriangolo : public AM80Carretto
{
	GENERATED_BODY()
public:
	AM80CarrettoTriangolo();
};

/** An old plank with a fruit crate for a seat and mismatched bearings: go-kart style, rope in the hands. */
UCLASS(meta = (DisplayName = "Carretto con la cassetta (guidabile)"))
class MAZZARINOVEHICLES_API AM80CarrettoCassetta : public AM80Carretto
{
	GENERATED_BODY()
public:
	AM80CarrettoCassetta();
};

/** A green shutter on three bearings, a broomstick tiller: sitting, arms up on the handle as on a chopper. */
UCLASS(meta = (DisplayName = "Carretto persiana (guidabile)"))
class MAZZARINOVEHICLES_API AM80CarrettoPersiana : public AM80Carretto
{
	GENERATED_BODY()
public:
	AM80CarrettoPersiana();
};

/** Cart wheels: ball bearings, one class per size (radius and width measured on the meshes). */
UCLASS(Abstract)
class MAZZARINOVEHICLES_API UM80WheelCuscinetto : public UChaosVehicleWheel
{
	GENERATED_BODY()
public:
	UM80WheelCuscinetto();
protected:
	void Size(float RadiusCm, float WidthCm, bool bSteer);
};

UCLASS()
class MAZZARINOVEHICLES_API UM80WheelCuscinetti36Sterzo : public UM80WheelCuscinetto
{
	GENERATED_BODY()
public:
	UM80WheelCuscinetti36Sterzo();
};

UCLASS()
class MAZZARINOVEHICLES_API UM80WheelCuscinetti36 : public UM80WheelCuscinetto
{
	GENERATED_BODY()
public:
	UM80WheelCuscinetti36();
};

UCLASS()
class MAZZARINOVEHICLES_API UM80WheelCuscinetti42Sterzo : public UM80WheelCuscinetto
{
	GENERATED_BODY()
public:
	UM80WheelCuscinetti42Sterzo();
};

UCLASS()
class MAZZARINOVEHICLES_API UM80WheelCuscinetti42 : public UM80WheelCuscinetto
{
	GENERATED_BODY()
public:
	UM80WheelCuscinetti42();
};

UCLASS()
class MAZZARINOVEHICLES_API UM80WheelCuscinetti29Sterzo : public UM80WheelCuscinetto
{
	GENERATED_BODY()
public:
	UM80WheelCuscinetti29Sterzo();
};

UCLASS()
class MAZZARINOVEHICLES_API UM80WheelCuscinetti47 : public UM80WheelCuscinetto
{
	GENERATED_BODY()
public:
	UM80WheelCuscinetti47();
};

UCLASS()
class MAZZARINOVEHICLES_API UM80WheelCuscinetti30 : public UM80WheelCuscinetto
{
	GENERATED_BODY()
public:
	UM80WheelCuscinetti30();
};

UCLASS()
class MAZZARINOVEHICLES_API UM80WheelCuscinetti41Sterzo : public UM80WheelCuscinetto
{
	GENERATED_BODY()
public:
	UM80WheelCuscinetti41Sterzo();
};
