#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "Engine/StreamableManager.h"
#include "M80PlayerController.generated.h"

class ACharacter;
class AM80Car;
class UAnimSequenceBase;
class UAnimSequence;
class UInputAction;
class UM80VitalsComponent;
class UM80WeaponInventory;
class UM80ClimbComponent;
class UM80OverlayAnimInstance;
class UStaticMesh;

UENUM(BlueprintType)
enum class EM80PlayerState : uint8
{
	OnFoot,
	GettingIn,
	Driving,
	GettingOut,
	Dead,
	KnockedDown,  // on the ground after a car or a blast, gets up by itself
	Sitting       // on a chair (E near one; E again to stand up)
};

/**
 * GTA-like player: walks around as a character, E (gamepad Y) near a car walks to the driver door,
 * sits in (driving pose) and drives it; E again stops and gets out on the driver side, or jumps out
 * when the car is going fast. M shows the full map. Health, armour and stamina live in the character's
 * UM80VitalsComponent (added on possession): falls and cars hurt, sprint needs stamina, at zero health
 * the character falls as a ragdoll and the player comes back at the start, paying the hospital.
 * Weapons (UM80WeaponInventory): left mouse fires or hits, right mouse aims (the sample's aim),
 * 1-4 / Q choose, R reloads, G drops; the arms take the weapon pose through UM80OverlayAnimInstance.
 */
UCLASS()
class MAZZARINOGAMEPLAY_API AM80PlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	AM80PlayerController();

	virtual void BeginPlay() override;
	virtual void SetupInputComponent() override;
	virtual void PlayerTick(float DeltaTime) override;
	virtual void OnPossess(APawn* InPawn) override;

	/** E: get in the nearest car or get out of the current one. */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void Interact();

	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void ToggleMap() { if (!IsPaused()) { bShowMap = !bShowMap; } }

	/** P / gamepad Start: pause with the town map (GTA pause screen); again to resume. */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void TogglePauseMap();

	/** Car the player could get into right now (for the "press E" hint), or null. */
	UFUNCTION(BlueprintPure, Category = "Mazzarino")
	AM80Car* GetCarInReach() const { return CarInReach.Get(); }

	UFUNCTION(BlueprintPure, Category = "Mazzarino")
	AM80Car* GetCurrentCar() const { return Car.Get(); }

	UFUNCTION(BlueprintPure, Category = "Mazzarino")
	ACharacter* GetPlayerCharacter() const { return Walker.Get(); }

	/** Sets the sample character's "wants to sprint" (as holding Shift); false if the character has none. */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	bool SetCharacterSprint(bool bSprint);

	/** Climbing on houses, balconies and roofs (null while there is no character). */
	UFUNCTION(BlueprintPure, Category = "Mazzarino")
	UM80ClimbComponent* GetClimb() const;

	/** Weapons carried by the character on foot (null while there is none). */
	UFUNCTION(BlueprintPure, Category = "Mazzarino")
	UM80WeaponInventory* GetInventory() const;

	/** Aiming a gun now (right mouse, or for a moment after firing without aiming). */
	UFUNCTION(BlueprintPure, Category = "Mazzarino")
	bool IsAiming() const { return bAimingNow; }

	/** Point under the crosshair (what a shot fired now would aim at). */
	UFUNCTION(BlueprintPure, Category = "Mazzarino")
	FVector GetAimPoint() const;

	/** Keeps the aim point where it is now, whatever the view (tests: photos from another camera). */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void FreezeAim(bool bFreeze) { FrozenAim = GetAimPoint(); bAimFrozen = bFreeze; }

	/** Throws the character to the ground (ragdoll) with this push; it gets up after a moment. */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void KnockDown(FVector Push);

	/** Weapon wheel (GTA V): Tab / gamepad LB held opens it and slows time; the mouse or the right stick points a
	 * sector, the mouse wheel / Q changes the weapon inside it; letting go takes it. */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void OpenWheel();

	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void CloseWheel(bool bTake = true);

	UFUNCTION(BlueprintPure, Category = "Mazzarino")
	bool IsWheelOpen() const { return bWheelOpen; }

	/** Sector pointed at (0 = top, clockwise), -1 none yet. */
	UFUNCTION(BlueprintPure, Category = "Mazzarino")
	int32 GetWheelSector() const { return WheelSector; }

	/** Points the wheel at a sector (tests, the d-pad). */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void PointWheel(int32 Sector);

	/** The next weapon inside the sector pointed at (mouse wheel, Q). */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void WheelNext(int32 Dir);

	/** Weapon category of each wheel sector, clockwise from the top. */
	static int32 WheelCategory(int32 Sector);

	/** Person locked by the gamepad aim (left trigger), or null. */
	UFUNCTION(BlueprintPure, Category = "Mazzarino")
	ACharacter* GetLockTarget() const { return LockTarget.Get(); }

	/** Locks the nearest living person in front (what the gamepad aim does; tests). */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	bool LockOn();

	/** Keeps the lock while the aim is held (tests: no gamepad). */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void HoldLock(bool bHold) { bLockHeld = bHold; if (!bHold) { LockTarget.Reset(); } }

	/** Holds the aim as the right mouse button does (tests, gamepad left trigger). */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void SetAimHeld(bool bHeld) { bAimHeld = bHeld; }

	/** Trigger (left mouse / right trigger). */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void SetFire(bool bDown);

	/** Health, armour and stamina of the character on foot (null while there is none). */
	UFUNCTION(BlueprintPure, Category = "Mazzarino")
	UM80VitalsComponent* GetVitals() const;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mazzarino")
	int32 Money = 50000;

	UPROPERTY(BlueprintReadOnly, Category = "Mazzarino")
	EM80PlayerState State = EM80PlayerState::OnFoot;

	UPROPERTY(BlueprintReadOnly, Category = "Mazzarino")
	FString StreetName;

	/** Seconds since the street name / vehicle name changed (HUD fades them). */
	float StreetNameAge = 99.f;
	float VehicleNameAge = 99.f;
	FString VehicleName;
	FString Hint;
	float HintAge = 99.f;
	bool bShowMap = false;
	/** Seconds since death (HUD "SEI MORTO" and fade out) and since coming back (fade in). */
	float DeathTime = 0.f;
	float RespawnAge = 99.f;

	/** Lire paid to the hospital when coming back after death. */
	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	int32 HospitalFee = 5000;

	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	float RespawnDelay = 5.f;

	/** Falls: no damage below this landing speed (cm/s, about 4 m), deadly around 15 m. */
	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	float FallDamageSpeed = 900.f;

	/** The sample character's sprint action (held: sprint again once the breath is back). */
	/** Getting up from the back / from the belly, and the roll after jumping out of a car (ALS, retargeted). */
	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	TSoftObjectPtr<UAnimSequenceBase> GetUpBackAnim = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Mazzarino80/Player/Anim/A_M80_Rialzati_Schiena.A_M80_Rialzati_Schiena")));

	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	TSoftObjectPtr<UAnimSequenceBase> GetUpFrontAnim = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Mazzarino80/Player/Anim/A_M80_Rialzati_Pancia.A_M80_Rialzati_Pancia")));

	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	TSoftObjectPtr<UAnimSequenceBase> RollAnim = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Mazzarino80/Player/Anim/A_M80_Capriola.A_M80_Capriola")));

	/** The sample's move action (X right, Y forward), read while climbing. */
	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	TSoftObjectPtr<UInputAction> MoveAction = TSoftObjectPtr<UInputAction>(FSoftObjectPath(TEXT("/Game/Input/IA_Move.IA_Move")));

	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	TSoftObjectPtr<UInputAction> SprintAction = TSoftObjectPtr<UInputAction>(FSoftObjectPath(TEXT("/Game/Input/IA_Sprint.IA_Sprint")));

	/** Driving pose (slot montage on the character's animation mesh). */
	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	TObjectPtr<UAnimSequenceBase> SeatedAnim;

	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	float ReachDistance = 450.f;

	/** Sunglasses put on the player's face (between the eyes) when the character is first possessed. */
	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	TSoftObjectPtr<UStaticMesh> Sunglasses = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Game/Mazzarino80/Player/SM_M80_Occhiali.SM_M80_Occhiali")));

private:
	/** The player's clips (getting up, rolling, getting in and out, sitting), input actions and sunglasses, loaded by
	 *  path when first needed: loaded in the background at BeginPlay and kept. */
	TSharedPtr<FStreamableHandle> Preloaded;

	void PutOnSunglasses(ACharacter* C);
	void StartGetIn(AM80Car* Target);
	void FinishGetIn();
	void StartGetOut(bool bJump = false);
	void LimitSprint();
	void UpdateWeapons(float DeltaTime);
	void UpdateClimbInput();
	/** On a cart or a moped: hands (and feet) on its grips, following the steering; on a stopped moped the left foot down. */
	void UpdateRide();
	void RideLocal(UM80OverlayAnimInstance* O, const ACharacter* W) const;
	float FootDown = 0.f;
	float FootDownRight = 0.f;
	/** Two-wheelers: on and off astride from the left, the vehicle's own clips played with the rider attached to it. */
	bool GetOnAstride(AM80Car* C, float From = 0.f);
	bool GetOffAstride(AM80Car* C);
	/** A moped lying on the road: bent down to the handlebar, it comes up with the rider standing up; then getting on. */
	bool PickUpAstride(AM80Car* C);
	TWeakObjectPtr<AM80Car> PickingUp;
	/** Where the character's root goes in the vehicle (its mesh origin on the cart's Sella bone, else SeatOffset). */
	FVector SeatFor(const AM80Car* C) const;
	void BindKeyLambda(const FKey& Key, TFunction<void()> Fn);
	void CheckCarHits(float DeltaTime);
	void Respawn();
	void Ragdoll(ACharacter* W, const FVector& Velocity);
	void GetUp();
	void PlayOneShot(UAnimSequenceBase* Anim, float BlendBack = 0.f);
	UFUNCTION()
	void OnWalkerDamaged(float Amount, FVector Direction, AActor* Causer);
	UFUNCTION()
	void OnWalkerDied(AActor* Killer);
	UFUNCTION()
	void OnWalkerLanded(const FHitResult& Hit);
	UFUNCTION()
	void OnCarExploded(AM80Car* Exploded);
	UFUNCTION()
	void OnRiderThrown(AM80Car* From, FVector Velocity, float Damage);
	AM80Car* FindCarInReach() const;
	void UpdateStreetName();
	void ShowHint(const FString& Text);
	FVector DoorWorld(const AM80Car* C) const;
	/** Four-wheeled cars: getting in and out is acted out (the townspeople's clips); carts and two-wheelers jump on. */
	bool ActsCar(const AM80Car* C) const;
	/** Where getting in starts: the clip walks the body from there into the seat. */
	FVector EnterStart(const AM80Car* C) const;
	/** A clip played on the character's mesh, its root's travel moving the character; then Then. */
	void PlayWithRoot(UAnimSequence* Clip, float From, float To, TFunction<void()> Then);
	void TickClip(float DeltaTime);
	/** Back to the sample's animation and walking, after a clip or sitting. */
	void BackOnFoot();
	AActor* FindChairInReach() const;
	void SitDown(AActor* OnChair);
	void StandUp();

	TWeakObjectPtr<ACharacter> Walker;
	TWeakObjectPtr<AM80Car> Car;
	TWeakObjectPtr<AM80Car> CarInReach;
	float PhaseTime = 0.f;
	FVector SeatStartRel = FVector::ZeroVector;
	FRotator SeatStartRot = FRotator::ZeroRotator;
	float StreetTimer = 0.f;
	float FallPeak = 0.f;
	float HitCooldown = 0.f;
	TWeakObjectPtr<AM80Car> IgnoreCar;
	float IgnoreCarTime = 0.f;
	bool bSprintForcedOff = false;
	bool bFireHeld = false;
	bool bAimingNow = false;
	bool bAimHeld = false;
	bool bWheelOpen = false;
	TWeakObjectPtr<ACharacter> LockTarget;
	bool bPadAimWas = false;
	bool bLockHeld = false;
	bool bAimFrozen = false;
	FVector FrozenAim = FVector::ZeroVector;
	void UpdateLockOn(float DeltaTime);
	int32 WheelSector = -1;
	FVector2D WheelCursor = FVector2D::ZeroVector;
	void UpdateWheel();
	bool bAimHeldApplied = false;
	bool bAimForced = false;
	bool bStrafeForced = false;
	float ForceAimTime = 0.f;
	float BreakWait = 0.f;
	float KnockTime = 0.f;
	float AnimLockTime = -1.f;
	bool bRollOnLanding = false;
	FTransform MeshRelative;
	FName MeshProfile;
	TWeakObjectPtr<UM80OverlayAnimInstance> Overlay;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> ClipNow;
	float ClipTo = 0.f;
	float ClipTime = 0.f;
	float ClipDrop = 0.f;
	/** Two-wheelers' clips: how much higher (or lower) the road beside the moped is than its wheels' ground, carried by the
	 *  feet while they stand beside it (ClipLiftWindow: seconds of the clip over which it goes; bClipLiftIn: 0 -> 1). */
	float ClipLift = 0.f;
	FVector2D ClipLiftWindow = FVector2D::ZeroVector;
	bool bClipLiftIn = false;
	float GroundBeside(const AM80Car* C) const;
	TFunction<void()> ClipThen;
	TWeakObjectPtr<AActor> Chair;
};
