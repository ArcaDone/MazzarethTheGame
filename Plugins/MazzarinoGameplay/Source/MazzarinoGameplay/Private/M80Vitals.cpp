#include "M80Vitals.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"

UM80VitalsComponent::UM80VitalsComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
}

void UM80VitalsComponent::BeginPlay()
{
	Super::BeginPlay();
	if (AActor* Owner = GetOwner())
	{
		Owner->OnTakeAnyDamage.AddUniqueDynamic(this, &UM80VitalsComponent::HandleAnyDamage);
	}
}

void UM80VitalsComponent::HandleAnyDamage(AActor* DamagedActor, float Damage, const UDamageType* DamageType, AController* InstigatedBy, AActor* DamageCauser)
{
	FVector Dir = FVector::ZeroVector;
	if (DamageCauser && DamagedActor)
	{
		Dir = (DamagedActor->GetActorLocation() - DamageCauser->GetActorLocation()).GetSafeNormal2D();
	}
	TakeHit(Damage, Dir, DamageCauser);
}

void UM80VitalsComponent::TakeHit(float Amount, FVector Direction, AActor* Causer)
{
	if (bDead || Amount <= 0.f)
	{
		return;
	}
	const float ToArmour = FMath::Min(Armour, Amount);
	Armour -= ToArmour;
	Health = FMath::Max(0.f, Health - (Amount - ToArmour));
	SinceLastHit = 0.f;
	LastHitDirection = Direction;
	OnDamaged.Broadcast(Amount, Direction, Causer);
	if (Health <= 0.f)
	{
		bDead = true;
		bSprinting = false;
		OnDied.Broadcast(Causer);
	}
}

void UM80VitalsComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	SinceLastHit += DeltaTime;
	if (bDead)
	{
		return;
	}
	const ACharacter* C = Cast<ACharacter>(GetOwner());
	const UCharacterMovementComponent* Move = C ? C->GetCharacterMovement() : nullptr;
	bSprinting = Move && Move->IsMovingOnGround() && C->GetVelocity().Size2D() > SprintSpeed;
	if (bSprinting)
	{
		SinceSprint = 0.f;
		Stamina = FMath::Max(0.f, Stamina - SprintDrain * DeltaTime);
		if (Stamina <= 0.f)
		{
			bExhausted = true;
		}
	}
	else
	{
		SinceSprint += DeltaTime;
		if (SinceSprint > RegenDelay)
		{
			// Faster when standing still than when walking.
			const float K = (C && C->GetVelocity().Size2D() < 50.f) ? 1.5f : 1.f;
			Stamina = FMath::Min(MaxStamina, Stamina + StaminaRegen * K * DeltaTime);
		}
	}
	if (bExhausted && Stamina >= RecoverAt)
	{
		bExhausted = false;
	}
}
