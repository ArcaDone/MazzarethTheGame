#include "M80TargetDummy.h"
#include "M80Vitals.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace
{
template <typename T>
T* Load(const TCHAR* Path)
{
	return LoadObject<T>(nullptr, Path, nullptr, LOAD_NoWarn);
}
const TCHAR* const MeshPath = TEXT("/Game/Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin.SKM_UEFN_Mannequin");
const TCHAR* const DummyIdlePath = TEXT("/Game/Characters/UEFN_Mannequin/Animations/Idle/M_Neutral_Stand_Idle_Loop.M_Neutral_Stand_Idle_Loop");
const TCHAR* const UpBackPath = TEXT("/Game/Mazzarino80/Player/Anim/A_M80_Rialzati_Schiena.A_M80_Rialzati_Schiena");
const TCHAR* const UpFrontPath = TEXT("/Game/Mazzarino80/Player/Anim/A_M80_Rialzati_Pancia.A_M80_Rialzati_Pancia");
}

AM80TargetDummy::AM80TargetDummy()
{
	PrimaryActorTick.bCanEverTick = true;
	GetCapsuleComponent()->InitCapsuleSize(34.f, 90.f);
	USkeletalMeshComponent* M = GetMesh();
	M->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -90.f), FRotator(0.f, -90.f, 0.f));
	M->SetCollisionProfileName(TEXT("CharacterMesh"));
	M->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPose;
	Vitals = CreateDefaultSubobject<UM80VitalsComponent>(TEXT("Vitals"));
	AutoPossessAI = EAutoPossessAI::Disabled;
}

void AM80TargetDummy::BeginPlay()
{
	Super::BeginPlay();
	if (!GetMesh()->GetSkeletalMeshAsset())
	{
		GetMesh()->SetSkeletalMesh(Load<USkeletalMesh>(MeshPath));
	}
	Home = GetActorTransform();
	MeshRelative = GetMesh()->GetRelativeTransform();
	Vitals->OnDamaged.AddUniqueDynamic(this, &AM80TargetDummy::OnDamaged);
	Vitals->OnDied.AddUniqueDynamic(this, &AM80TargetDummy::OnDied);
	Stand();
}

void AM80TargetDummy::Stand()
{
	if (UAnimSequence* Idle = Load<UAnimSequence>(DummyIdlePath))
	{
		GetMesh()->PlayAnimation(Idle, true);
	}
}

FVector AM80TargetDummy::AimPoint() const
{
	return bDown ? GetMesh()->GetSocketLocation(TEXT("spine_03")) : GetActorLocation() + FVector(0.f, 0.f, 45.f);
}

void AM80TargetDummy::OnDamaged(float Amount, FVector Direction, AActor* Causer)
{
	RecentDamage = (SinceDamage < 2.f ? RecentDamage : 0.f) + Amount;
	SinceDamage = 0.f;
	if (!bDown && !Vitals->IsDead() && RecentDamage >= KnockdownDamage)
	{
		FallDown(Direction.GetSafeNormal() * 350.f + FVector(0.f, 0.f, 120.f));
	}
}

void AM80TargetDummy::OnDied(AActor* Killer)
{
	if (!bDown)
	{
		FallDown(FVector(0.f, 0.f, 50.f));
	}
}

void AM80TargetDummy::FallDown(const FVector& Push)
{
	USkeletalMeshComponent* M = GetMesh();
	GetCharacterMovement()->DisableMovement();
	GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	M->SetCollisionProfileName(TEXT("Ragdoll"));
	M->SetAllBodiesSimulatePhysics(true);
	M->SetSimulatePhysics(true);
	M->WakeAllRigidBodies();
	M->SetAllPhysicsLinearVelocity(Push);
	bDown = true;
	DownTime = 0.f;
}

void AM80TargetDummy::GetUp()
{
	USkeletalMeshComponent* M = GetMesh();
	const FVector Pelvis = M->GetSocketLocation(TEXT("pelvis"));
	const FVector Head = M->GetSocketLocation(TEXT("head"));
	const bool bFaceUp = M->GetSocketRotation(TEXT("pelvis")).Quaternion().GetRightVector().Z < 0.f;
	FVector Facing = (bFaceUp ? Pelvis - Head : Head - Pelvis).GetSafeNormal2D();
	if (Facing.IsNearlyZero())
	{
		Facing = GetActorForwardVector();
	}
	M->SetSimulatePhysics(false);
	M->SetAllBodiesSimulatePhysics(false);
	M->SetCollisionProfileName(TEXT("CharacterMesh"));
	M->AttachToComponent(GetCapsuleComponent(), FAttachmentTransformRules::KeepWorldTransform);
	// Stand where the body lies.
	FHitResult Floor;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(M80Dummy), false, this);
	FVector At = Pelvis + FVector(0.f, 0.f, 100.f);
	if (GetWorld()->LineTraceSingleByChannel(Floor, Pelvis + FVector(0, 0, 50.f), Pelvis - FVector(0, 0, 300.f), ECC_Visibility, Q))
	{
		At = Floor.ImpactPoint + FVector(0.f, 0.f, GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 2.f);
	}
	SetActorLocationAndRotation(At, Facing.Rotation(), false, nullptr, ETeleportType::TeleportPhysics);
	M->SetRelativeTransform(MeshRelative);
	GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	GetCharacterMovement()->SetMovementMode(MOVE_Walking);
	bDown = false;
	RecentDamage = 0.f;
	if (UAnimSequence* Up = Load<UAnimSequence>(bFaceUp ? UpBackPath : UpFrontPath))
	{
		M->PlayAnimation(Up, false);
		GetUpLeft = Up->GetPlayLength();
	}
	else
	{
		Stand();
	}
}

void AM80TargetDummy::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	SinceDamage += DeltaSeconds;
	if (GetUpLeft >= 0.f)
	{
		GetUpLeft -= DeltaSeconds;
		if (GetUpLeft < 0.f)
		{
			Stand();
		}
	}
	if (!bDown)
	{
		return;
	}
	DownTime += DeltaSeconds;
	if (Vitals->IsDead())
	{
		if (DownTime > RespawnAfter)
		{
			// Back where it stood, whole.
			Vitals->Revive();
			GetUp();
			SetActorTransform(Home, false, nullptr, ETeleportType::TeleportPhysics);
		}
	}
	else if (DownTime > GetUpAfter)
	{
		GetUp();
	}
}
