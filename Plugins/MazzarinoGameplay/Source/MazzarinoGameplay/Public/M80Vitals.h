#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "M80Vitals.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FM80Damaged, float, Amount, FVector, Direction, AActor*, Causer);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FM80Died, AActor*, Killer);

/**
 * Health, armour and stamina of a character (the player now, pedestrians later), GTA style:
 * armour takes the damage first, health does not come back by itself, stamina runs down while
 * sprinting and comes back after a short rest. Damage from UGameplayStatics::ApplyDamage (weapons)
 * arrives here too.
 */
UCLASS(ClassGroup = (Mazzarino), meta = (BlueprintSpawnableComponent))
class MAZZARINOGAMEPLAY_API UM80VitalsComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UM80VitalsComponent();

	virtual void BeginPlay() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/** Takes Amount of damage (armour first); Direction is where the hit pushes (world, may be zero). */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void TakeHit(float Amount, FVector Direction, AActor* Causer);

	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void Heal(float Amount) { if (!bDead) { Health = FMath::Min(MaxHealth, Health + Amount); } }

	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void AddArmour(float Amount) { if (!bDead) { Armour = FMath::Min(MaxArmour, Armour + Amount); } }

	/** Sprinting allowed (not out of breath). */
	UFUNCTION(BlueprintPure, Category = "Mazzarino")
	bool CanSprint() const { return !bExhausted && !bDead; }

	UFUNCTION(BlueprintPure, Category = "Mazzarino")
	bool IsDead() const { return bDead; }

	/** Seconds since the last hit (HUD red flash). */
	float SinceHit() const { return SinceLastHit; }

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mazzarino")
	float MaxHealth = 100.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mazzarino")
	float Health = 100.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mazzarino")
	float MaxArmour = 100.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mazzarino")
	float Armour = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mazzarino|Stamina")
	float MaxStamina = 100.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mazzarino|Stamina")
	float Stamina = 100.f;

	/** Per second while sprinting (about 9 s of sprint from full). */
	UPROPERTY(EditAnywhere, Category = "Mazzarino|Stamina")
	float SprintDrain = 11.f;

	/** Per second, after RegenDelay seconds without sprinting. */
	UPROPERTY(EditAnywhere, Category = "Mazzarino|Stamina")
	float StaminaRegen = 16.f;

	UPROPERTY(EditAnywhere, Category = "Mazzarino|Stamina")
	float RegenDelay = 1.2f;

	/** Out of breath at zero: no sprint until stamina is back to this. */
	UPROPERTY(EditAnywhere, Category = "Mazzarino|Stamina")
	float RecoverAt = 30.f;

	/** Ground speed (cm/s) above which the character counts as sprinting (the sample runs at 500, sprints at 700). */
	UPROPERTY(EditAnywhere, Category = "Mazzarino|Stamina")
	float SprintSpeed = 580.f;

	UPROPERTY(BlueprintAssignable, Category = "Mazzarino")
	FM80Damaged OnDamaged;

	UPROPERTY(BlueprintAssignable, Category = "Mazzarino")
	FM80Died OnDied;

	UPROPERTY(BlueprintReadOnly, Category = "Mazzarino")
	bool bExhausted = false;

	UPROPERTY(BlueprintReadOnly, Category = "Mazzarino")
	bool bSprinting = false;

	/** Direction of the last hit (ragdoll push). */
	FVector LastHitDirection = FVector::ZeroVector;

private:
	UFUNCTION()
	void HandleAnyDamage(AActor* DamagedActor, float Damage, const UDamageType* DamageType, AController* InstigatedBy, AActor* DamageCauser);

	bool bDead = false;
	float SinceLastHit = 99.f;
	float SinceSprint = 99.f;
};
