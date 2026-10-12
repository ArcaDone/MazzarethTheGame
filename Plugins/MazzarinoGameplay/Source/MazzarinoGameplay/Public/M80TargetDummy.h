#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "M80TargetDummy.generated.h"

class UAnimSequence;
class UM80VitalsComponent;

/**
 * A person to fight with while there are no pedestrians yet: the mannequin standing idle, with health. Shots and blows
 * hurt it (blood); a hard blow, or several in a row, throws it to the ground (ragdoll) and it gets up after a moment
 * (ALS get-up, retargeted); at zero health it stays down and comes back where it stood after a while.
 * The gamepad lock-on aims at these (and later at pedestrians).
 */
UCLASS(meta = (DisplayName = "Bersaglio umano (Mazzarino)"))
class MAZZARINOGAMEPLAY_API AM80TargetDummy : public ACharacter
{
	GENERATED_BODY()

public:
	AM80TargetDummy();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Mazzarino")
	TObjectPtr<UM80VitalsComponent> Vitals;

	/** Damage within a couple of seconds that throws it to the ground (a bat blow, three punches). */
	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	float KnockdownDamage = 22.f;

	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	float GetUpAfter = 2.5f;

	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	float RespawnAfter = 12.f;

	UFUNCTION(BlueprintPure, Category = "Mazzarino")
	bool IsDown() const { return bDown; }

	/** Where the lock-on aims (the chest). */
	FVector AimPoint() const;

private:
	UFUNCTION()
	void OnDamaged(float Amount, FVector Direction, AActor* Causer);
	UFUNCTION()
	void OnDied(AActor* Killer);
	void FallDown(const FVector& Push);
	void GetUp();
	void Stand();

	FTransform Home;
	FTransform MeshRelative;
	float RecentDamage = 0.f;
	float SinceDamage = 99.f;
	float DownTime = 0.f;
	float GetUpLeft = -1.f;
	bool bDown = false;
};
