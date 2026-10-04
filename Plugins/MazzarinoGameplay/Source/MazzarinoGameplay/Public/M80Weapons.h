#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameFramework/Actor.h"
#include "M80Weapons.generated.h"

class UStaticMesh;
class UStaticMeshComponent;
class USphereComponent;
class UPointLightComponent;
class USoundBase;
class USkeletalMeshComponent;

/** The period weapons (GTA Vice City style, Sicily 1980s). */
UENUM(BlueprintType)
enum class EM80Weapon : uint8
{
	Pugni,
	Coltello,
	Mazza,
	Revolver,
	Beretta,
	Lupara
};

/** How the arms hold the weapon (the overlay animation picks the pose from this). */
UENUM(BlueprintType)
enum class EM80WeaponPose : uint8
{
	Unarmed,
	Melee,
	Pistol,
	Rifle
};

/** Fixed data of a weapon (like the cars' FCarSpec: the numbers live in code). */
struct MAZZARINOGAMEPLAY_API FM80WeaponSpec
{
	const TCHAR* Name = TEXT("");
	int32 Slot = 0;                 // 0 fists, 1 melee, 2 pistol, 3 shotgun
	const TCHAR* Mesh = nullptr;    // static mesh path, null for fists
	EM80WeaponPose Pose = EM80WeaponPose::Unarmed;
	bool bMelee = true;
	float Damage = 10.f;            // per hit (per pellet for the lupara)
	int32 Pellets = 1;
	float Interval = 0.5f;          // seconds between shots / blows
	int32 Clip = 0;                 // rounds per load (0 = melee)
	int32 MaxAmmo = 0;              // reserve cap
	int32 PickupAmmo = 0;           // rounds in a pickup
	float ReloadTime = 1.5f;
	float Range = 150.f;            // cm
	float SpreadDeg = 0.f;
	float Impulse = 300.f;          // push on physics objects (cars...)
	const TCHAR* FireSound = nullptr;
	FLinearColor Glow = FLinearColor(1.f, 0.8f, 0.3f);
};

MAZZARINOGAMEPLAY_API const FM80WeaponSpec& M80WeaponSpec(EM80Weapon W);

/** What shots (and the crosshair) hit: world, people, vehicles. */
MAZZARINOGAMEPLAY_API FCollisionObjectQueryParams M80ShotObjects();

/** Weapon frame in the right hand bone's space (grip in the palm, barrel along the knuckles), from the mesh's hand bones. */
MAZZARINOGAMEPLAY_API FTransform M80GripInHand(const class USkeletalMesh* Mesh, bool bBlade);

/** One inventory slot: the weapon in it and its ammo. */
USTRUCT(BlueprintType)
struct FM80WeaponSlot
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Mazzarino")
	bool bHas = false;

	UPROPERTY(BlueprintReadOnly, Category = "Mazzarino")
	EM80Weapon Weapon = EM80Weapon::Pugni;

	UPROPERTY(BlueprintReadOnly, Category = "Mazzarino")
	int32 InClip = 0;

	UPROPERTY(BlueprintReadOnly, Category = "Mazzarino")
	int32 Reserve = 0;
};

/**
 * The weapons a character carries, GTA style: four slots (fists, melee, pistol, shotgun), one weapon
 * per slot (picking up another one of the same slot swaps it), ammo adds up. Fires hitscan shots
 * (UGameplayStatics::ApplyPointDamage, impulses, impacts) and melee blows. The weapon in hand is a
 * static mesh on the right hand of the visible body.
 */
UCLASS(ClassGroup = (Mazzarino), meta = (BlueprintSpawnableComponent))
class MAZZARINOGAMEPLAY_API UM80WeaponInventory : public UActorComponent
{
	GENERATED_BODY()

public:
	UM80WeaponInventory();

	virtual void BeginPlay() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/** Adds a weapon (or its ammo); returns false if nothing could be taken (ammo full). */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	bool Give(EM80Weapon Weapon, int32 Ammo, bool bSelect = true);

	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void SelectSlot(int32 Slot);

	/** Next (+1) or previous (-1) slot that has a weapon. */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void Cycle(int32 Dir);

	/** Drops the weapon in hand on the ground (with its ammo) and goes back to the fists. */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void DropCurrent();

	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void Reload();

	/** Trigger: shots go from the muzzle towards AimPoint (the point under the crosshair). */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void SetTrigger(bool bDown, FVector AimPoint);

	/** Fires once now if the weapon is ready (used by the trigger and by tests). */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	bool TryFire(FVector AimPoint);

	UFUNCTION(BlueprintPure, Category = "Mazzarino")
	EM80Weapon GetCurrentWeapon() const { return Slots[Current].Weapon; }

	UFUNCTION(BlueprintPure, Category = "Mazzarino")
	int32 GetCurrentSlot() const { return Current; }

	UFUNCTION(BlueprintPure, Category = "Mazzarino")
	FM80WeaponSlot GetSlot(int32 Slot) const { return Slots.IsValidIndex(Slot) ? Slots[Slot] : FM80WeaponSlot(); }

	UFUNCTION(BlueprintPure, Category = "Mazzarino")
	bool IsReloading() const { return ReloadLeft > 0.f; }

	const FM80WeaponSpec& CurrentSpec() const { return M80WeaponSpec(GetCurrentWeapon()); }

	/** Seconds since the last shot / blow (recoil and swing in the overlay animation). */
	float SinceFire() const { return SinceLastFire; }

	/** The visible body mesh the weapon is held by (MetaHuman body, else the character mesh). */
	USkeletalMeshComponent* HandMesh() const;

	/** World position of the muzzle (or of the hand without a gun). */
	FVector MuzzleLocation() const;

	/** Unequip everything (death). */
	void HideWeapon();

	UPROPERTY(BlueprintReadOnly, Category = "Mazzarino")
	TArray<FM80WeaponSlot> Slots;

private:
	void FireRanged(const FM80WeaponSpec& S, const FVector& AimPoint);
	void FireMelee(const FM80WeaponSpec& S);
	void Impact(const FHitResult& Hit, const FVector& Dir, const FM80WeaponSpec& S);
	void UpdateHeldMesh();

	UPROPERTY(Transient)
	TObjectPtr<UStaticMeshComponent> Held;

	int32 Current = 0;
	float Cooldown = 0.f;
	float ReloadLeft = 0.f;
	float SinceLastFire = 99.f;
	bool bTrigger = false;
	FVector TriggerAim = FVector::ZeroVector;
};

/**
 * A weapon lying on the ground, GTA style: turns, bobs and glows; walking over it picks it up.
 * Placed ones come back after RespawnTime; dropped ones disappear after a while.
 */
UCLASS()
class MAZZARINOGAMEPLAY_API AM80WeaponPickup : public AActor
{
	GENERATED_BODY()

public:
	AM80WeaponPickup();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	/** Sets the weapon shown and given (call before or right after spawning). */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void SetWeapon(EM80Weapon InWeapon, int32 InAmmo);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mazzarino")
	EM80Weapon Weapon = EM80Weapon::Beretta;

	/** Rounds given (-1 = the weapon's usual pickup amount). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mazzarino")
	int32 Ammo = -1;

	/** Placed in the world: comes back this many seconds after being taken (0 = never). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mazzarino")
	float RespawnTime = 60.f;

	/** Dropped by someone: disappears after this many seconds (0 = stays). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mazzarino")
	float LifeTime = 0.f;

	UPROPERTY(VisibleAnywhere, Category = "Mazzarino")
	TObjectPtr<USphereComponent> Trigger;

	UPROPERTY(VisibleAnywhere, Category = "Mazzarino")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, Category = "Mazzarino")
	TObjectPtr<UPointLightComponent> Glow;

	/** Glowing disc under the weapon (seen in daylight too). */
	UPROPERTY(VisibleAnywhere, Category = "Mazzarino")
	TObjectPtr<UStaticMeshComponent> Halo;

private:
	UFUNCTION()
	void OnOverlap(UPrimitiveComponent* OverlappedComp, AActor* Other, UPrimitiveComponent* OtherComp, int32 BodyIndex, bool bFromSweep, const FHitResult& Sweep);

	void SetAvailable(bool bOn);

	bool bAvailable = true;
	float Hidden = 0.f;
	float Age = 0.f;
	float Pause = 0.f;  // a dropped weapon is not picked up again at once
};
