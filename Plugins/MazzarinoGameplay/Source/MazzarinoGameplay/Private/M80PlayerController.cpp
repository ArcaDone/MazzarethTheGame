#include "M80PlayerController.h"
#include "M80Car.h"
#include "M80Vitals.h"
#include "M80Weapons.h"
#include "M80OverlayAnim.h"
#include "MazzarinoRoadSpline.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimSequenceBase.h"
#include "Components/CapsuleComponent.h"
#include "Components/InputComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SplineComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "EnhancedInputSubsystems.h"
#include "EnhancedPlayerInput.h"
#include "InputAction.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameModeBase.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
constexpr float WalkToDoorMax = 3.f;   // seconds before giving up walking and snapping to the door
constexpr float SlideInTime = 0.7f;    // door -> seat
constexpr float MaxExitKmh = 25.f;     // faster than this E jumps out

FString LireText(int32 V)
{
	FString Digits = FString::FromInt(FMath::Abs(V));
	for (int32 i = Digits.Len() - 3; i > 0; i -= 3)
	{
		Digits.InsertAt(i, TEXT("."));
	}
	return TEXT("L. ") + Digits;
}

/** A flag of the sample character's CharacterInputState struct ("WantsToSprint", "WantsToAim"), or null. */
bool* InputStateFlag(ACharacter* C, const TCHAR* Prefix)
{
	const FStructProperty* InputState = C ? FindFProperty<FStructProperty>(C->GetClass(), TEXT("CharacterInputState")) : nullptr;
	if (!InputState)
	{
		return nullptr;
	}
	for (TFieldIterator<FBoolProperty> It(InputState->Struct); It; ++It)
	{
		// Blueprint struct members carry a suffix (WantsToSprint_1_840C...).
		if (It->GetName().StartsWith(Prefix))
		{
			void* StructData = InputState->ContainerPtrToValuePtr<void>(C);
			return static_cast<bool*>(It->ContainerPtrToValuePtr<void>(StructData));
		}
	}
	return nullptr;
}

bool* WantsToSprint(ACharacter* C)
{
	return InputStateFlag(C, TEXT("WantsToSprint"));
}
}

AM80PlayerController::AM80PlayerController()
{
	static ConstructorHelpers::FObjectFinderOptional<UAnimSequenceBase> Seated(TEXT("/Game/Mazzarino80/Player/A_M80_Seduto_Guida.A_M80_Seduto_Guida"));
	SeatedAnim = Seated.Get();
}

void AM80PlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();
	InputComponent->BindKey(EKeys::E, IE_Pressed, this, &AM80PlayerController::Interact);
	InputComponent->BindKey(EKeys::Gamepad_FaceButton_Top, IE_Pressed, this, &AM80PlayerController::Interact);
	InputComponent->BindKey(EKeys::M, IE_Pressed, this, &AM80PlayerController::ToggleMap);
	InputComponent->BindKey(EKeys::Gamepad_Special_Left, IE_Pressed, this, &AM80PlayerController::ToggleMap);
	// Pause keys must work while the game is paused.
	InputComponent->BindKey(EKeys::P, IE_Pressed, this, &AM80PlayerController::TogglePauseMap).bExecuteWhenPaused = true;
	InputComponent->BindKey(EKeys::Gamepad_Special_Right, IE_Pressed, this, &AM80PlayerController::TogglePauseMap).bExecuteWhenPaused = true;
	// Weapons.
	BindKeyLambda(EKeys::LeftMouseButton, [this]() { SetFire(true); });
	BindKeyLambda(EKeys::Gamepad_RightTrigger, [this]() { SetFire(true); });
	for (const FKey& K : {EKeys::LeftMouseButton, EKeys::Gamepad_RightTrigger})
	{
		FInputKeyBinding Up{FInputChord(K), IE_Released};
		Up.bConsumeInput = false;
		Up.KeyDelegate.GetDelegateForManualSet().BindLambda([this]() { SetFire(false); });
		InputComponent->KeyBindings.Add(Up);
	}
	const FKey Numbers[] = {EKeys::One, EKeys::Two, EKeys::Three, EKeys::Four};
	for (int32 i = 0; i < 4; ++i)
	{
		BindKeyLambda(Numbers[i], [this, i]() { if (UM80WeaponInventory* Inv = GetInventory()) { Inv->SelectSlot(i); } });
	}
	BindKeyLambda(EKeys::Q, [this]() { if (UM80WeaponInventory* Inv = GetInventory()) { Inv->Cycle(1); } });
	BindKeyLambda(EKeys::Gamepad_DPad_Right, [this]() { if (UM80WeaponInventory* Inv = GetInventory()) { Inv->Cycle(1); } });
	BindKeyLambda(EKeys::Gamepad_DPad_Left, [this]() { if (UM80WeaponInventory* Inv = GetInventory()) { Inv->Cycle(-1); } });
	auto OnFootDo = [this](TFunction<void(UM80WeaponInventory*)> Fn)
	{
		return [this, Fn]() { if (UM80WeaponInventory* Inv = GetInventory(); Inv && State == EM80PlayerState::OnFoot) { Fn(Inv); } };
	};
	BindKeyLambda(EKeys::R, OnFootDo([](UM80WeaponInventory* Inv) { Inv->Reload(); }));
	BindKeyLambda(EKeys::Gamepad_FaceButton_Left, OnFootDo([](UM80WeaponInventory* Inv) { Inv->Reload(); }));
	BindKeyLambda(EKeys::G, OnFootDo([](UM80WeaponInventory* Inv) { Inv->DropCurrent(); }));
	BindKeyLambda(EKeys::Gamepad_DPad_Down, OnFootDo([](UM80WeaponInventory* Inv) { Inv->DropCurrent(); }));
}

void AM80PlayerController::BindKeyLambda(const FKey& Key, TFunction<void()> Fn)
{
	FInputKeyBinding B{FInputChord(Key), IE_Pressed};
	B.bConsumeInput = false;
	B.KeyDelegate.GetDelegateForManualSet().BindLambda(MoveTemp(Fn));
	InputComponent->KeyBindings.Add(B);
}

UM80WeaponInventory* AM80PlayerController::GetInventory() const
{
	const ACharacter* W = Walker.Get();
	return W ? W->FindComponentByClass<UM80WeaponInventory>() : nullptr;
}

void AM80PlayerController::SetFire(bool bDown)
{
	bFireHeld = bDown && State == EM80PlayerState::OnFoot;
	if (UM80WeaponInventory* Inv = GetInventory())
	{
		if (bFireHeld && !Inv->CurrentSpec().bMelee)
		{
			// Firing without aiming: the character turns to the crosshair for a moment (GTA).
			ForceAimTime = 0.6f;
		}
		Inv->SetTrigger(bFireHeld, GetAimPoint());
	}
}

FVector AM80PlayerController::GetAimPoint() const
{
	FVector Eye;
	FRotator Rot;
	GetPlayerViewPoint(Eye, Rot);
	const FVector End = Eye + Rot.Vector() * 10000.f;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(M80Aim), true, GetPawn());
	if (const AActor* W = Walker.Get())
	{
		Q.AddIgnoredActor(W);
	}
	FHitResult Hit;
	return GetWorld()->LineTraceSingleByObjectType(Hit, Eye, End, M80ShotObjects(), Q) ? Hit.ImpactPoint : End;
}

bool AM80PlayerController::IsActionHeld(const TSoftObjectPtr<UInputAction>& Action) const
{
	const UInputAction* A = Action.LoadSynchronous();
	const UEnhancedInputLocalPlayerSubsystem* Sub = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer());
	return A && Sub && Sub->GetPlayerInput() && Sub->GetPlayerInput()->GetActionValue(A).Get<bool>();
}

void AM80PlayerController::UpdateWeapons(float DeltaTime)
{
	ACharacter* W = Walker.Get();
	UM80WeaponInventory* Inv = GetInventory();
	UM80OverlayAnimInstance* O = Overlay.Get();
	if (!W || !Inv)
	{
		return;
	}
	const FM80WeaponSpec& S = Inv->CurrentSpec();
	const bool bOnFoot = State == EM80PlayerState::OnFoot;
	ForceAimTime -= DeltaTime;
	// Aim: right mouse (the sample turns the character to the camera), or held for a moment after a shot.
	bool* WantsAim = InputStateFlag(W, TEXT("WantsToAim"));
	const bool bRMB = IsActionHeld(AimAction);
	const bool bForce = bOnFoot && !S.bMelee && ForceAimTime > 0.f;
	if (WantsAim)
	{
		if (bForce && !*WantsAim)
		{
			*WantsAim = true;
			bAimForced = true;
		}
		else if (bAimForced && !bForce)
		{
			*WantsAim = bRMB;
			bAimForced = false;
		}
	}
	bAimingNow = bOnFoot && !S.bMelee && (bRMB || bForce);
	// Aiming: the character faces the crosshair at once (GTA) and walks sideways (the sample's strafe).
	if (bool* Strafe = InputStateFlag(W, TEXT("WantsToStrafe")))
	{
		if (bAimingNow && !*Strafe)
		{
			*Strafe = true;
			bStrafeForced = true;
		}
		else if (!bAimingNow && bStrafeForced)
		{
			*Strafe = false;
			bStrafeForced = false;
		}
	}
	if (bAimingNow)
	{
		FRotator R = W->GetActorRotation();
		R.Yaw = FMath::FixedTurn(R.Yaw, GetControlRotation().Yaw, 1080.f * DeltaTime);
		W->SetActorRotation(R);
	}
	if (bFireHeld)
	{
		Inv->SetTrigger(bOnFoot, GetAimPoint());
	}
	if (O)
	{
		O->Pose = bOnFoot ? S.Pose : EM80WeaponPose::Unarmed;
		O->bAiming = bAimingNow;
		O->AimPoint = bAimingNow ? GetAimPoint() : FVector::ZeroVector;
		O->SinceFire = Inv->SinceFire();
		O->bEnabled = bOnFoot;
	}
}

void AM80PlayerController::TogglePauseMap()
{
	const bool bPause = !IsPaused();
	SetPause(bPause);
	bShowMap = bPause;
}

void AM80PlayerController::OnPossess(APawn* InPawn)
{
	Super::OnPossess(InPawn);
	if (ACharacter* C = Cast<ACharacter>(InPawn))
	{
		Walker = C;
		PutOnSunglasses(C);
		UM80VitalsComponent* V = C->FindComponentByClass<UM80VitalsComponent>();
		if (!V)
		{
			V = NewObject<UM80VitalsComponent>(C, TEXT("M80Vitals"));
			V->RegisterComponent();
		}
		V->OnDied.AddUniqueDynamic(this, &AM80PlayerController::OnWalkerDied);
		V->OnDamaged.AddUniqueDynamic(this, &AM80PlayerController::OnWalkerDamaged);
		MeshRelative = C->GetMesh()->GetRelativeTransform();
		MeshProfile = C->GetMesh()->GetCollisionProfileName();
		if (!C->FindComponentByClass<UM80WeaponInventory>())
		{
			NewObject<UM80WeaponInventory>(C, TEXT("M80Armi"))->RegisterComponent();
		}
		Overlay = UM80OverlayAnimInstance::Install(C);
		C->LandedDelegate.AddUniqueDynamic(this, &AM80PlayerController::OnWalkerLanded);
	}
}

UM80VitalsComponent* AM80PlayerController::GetVitals() const
{
	const ACharacter* W = Walker.Get();
	return W ? W->FindComponentByClass<UM80VitalsComponent>() : nullptr;
}

void AM80PlayerController::OnWalkerLanded(const FHitResult& Hit)
{
	const float Peak = FallPeak;
	FallPeak = 0.f;
	if (bRollOnLanding && State == EM80PlayerState::OnFoot)
	{
		// Out of a moving car: roll forward along the way the body was flying.
		bRollOnLanding = false;
		if (ACharacter* W = Walker.Get())
		{
			const FVector V = W->GetVelocity().GetSafeNormal2D();
			if (!V.IsNearlyZero())
			{
				W->SetActorRotation(V.Rotation());
			}
			PlayOneShot(RollAnim.LoadSynchronous());
		}
	}
	if (Peak > FallDamageSpeed && State == EM80PlayerState::OnFoot)
	{
		if (UM80VitalsComponent* V = GetVitals())
		{
			V->TakeHit((Peak - FallDamageSpeed) / 8.f, FVector::ZeroVector, nullptr);
		}
	}
}

void AM80PlayerController::OnCarExploded(AM80Car* Exploded)
{
	if (Exploded != Car.Get() || (State != EM80PlayerState::Driving && State != EM80PlayerState::GettingIn))
	{
		return;
	}
	// Still inside when it blew up: thrown out, and it is hard to survive that.
	if (State == EM80PlayerState::Driving)
	{
		StartGetOut(false);
	}
	if (UM80VitalsComponent* V = GetVitals())
	{
		V->TakeHit(300.f, FVector::UpVector, Exploded);
	}
}

void AM80PlayerController::OnWalkerDamaged(float Amount, FVector Direction, AActor* Causer)
{
	// A blast close by (a car blowing up): down on the ground.
	if (Amount >= 25.f && State == EM80PlayerState::OnFoot && Causer && Causer->IsA<AM80Car>() && Cast<AM80Car>(Causer)->bWrecked)
	{
		if (const UM80VitalsComponent* V = GetVitals(); V && !V->IsDead())
		{
			KnockDown(Direction * 700.f + FVector(0, 0, 500.f));
		}
	}
}

void AM80PlayerController::Ragdoll(ACharacter* W, const FVector& Velocity)
{
	W->GetCharacterMovement()->DisableMovement();
	W->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	USkeletalMeshComponent* M = W->GetMesh();
	M->SetCollisionProfileName(TEXT("Ragdoll"));
	M->SetAllBodiesSimulatePhysics(true);
	M->SetSimulatePhysics(true);
	M->WakeAllRigidBodies();
	M->SetAllPhysicsLinearVelocity(Velocity);
}

void AM80PlayerController::KnockDown(FVector Push)
{
	ACharacter* W = Walker.Get();
	if (!W || State != EM80PlayerState::OnFoot)
	{
		return;
	}
	State = EM80PlayerState::KnockedDown;
	KnockTime = 0.f;
	bFireHeld = false;
	SetIgnoreMoveInput(true);
	if (UM80OverlayAnimInstance* O = Overlay.Get())
	{
		O->bEnabled = false;
	}
	Ragdoll(W, Push);
}

void AM80PlayerController::PlayOneShot(UAnimSequenceBase* Anim, float BlendBack)
{
	ACharacter* W = Walker.Get();
	if (!W || !Anim)
	{
		return;
	}
	W->GetMesh()->PlayAnimation(Anim, false);
	AnimLockTime = Anim->GetPlayLength();
}

void AM80PlayerController::GetUp()
{
	ACharacter* W = Walker.Get();
	if (!W)
	{
		return;
	}
	USkeletalMeshComponent* M = W->GetMesh();
	const FVector Pelvis = M->GetSocketLocation(TEXT("pelvis"));
	const FVector Head = M->GetSocketLocation(TEXT("head"));
	// Lying on the back or on the belly (as ALS: the pelvis' right axis points down when face up).
	const bool bFaceUp = M->GetSocketRotation(TEXT("pelvis")).Quaternion().GetRightVector().Z < 0.f;
	FVector Facing = (bFaceUp ? Pelvis - Head : Head - Pelvis).GetSafeNormal2D();
	if (Facing.IsNearlyZero())
	{
		Facing = W->GetActorForwardVector();
	}
	M->SetSimulatePhysics(false);
	M->SetAllBodiesSimulatePhysics(false);
	M->SetCollisionProfileName(MeshProfile);
	// The capsule stands where the body lies, on the ground.
	const float Half = W->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	FVector Stand = Pelvis + FVector(0, 0, Half);
	FHitResult Hit;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(M80GetUp), false, W);
	if (GetWorld()->LineTraceSingleByChannel(Hit, Pelvis + FVector(0, 0, 100.f), Pelvis - FVector(0, 0, 300.f), ECC_Visibility, Q))
	{
		Stand = Hit.ImpactPoint + FVector(0, 0, Half + 2.f);
	}
	W->SetActorLocationAndRotation(Stand, Facing.Rotation(), false, nullptr, ETeleportType::TeleportPhysics);
	M->AttachToComponent(W->GetCapsuleComponent(), FAttachmentTransformRules::KeepWorldTransform);
	M->SetRelativeTransform(MeshRelative);
	W->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	W->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
	State = EM80PlayerState::OnFoot;
	PlayOneShot((bFaceUp ? GetUpBackAnim : GetUpFrontAnim).LoadSynchronous());
}

void AM80PlayerController::OnWalkerDied(AActor* Killer)
{
	ACharacter* W = Walker.Get();
	if (!W || State == EM80PlayerState::Dead)
	{
		return;
	}
	if (W->GetAttachParentActor())
	{
		W->DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
		W->GetMesh()->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	}
	State = EM80PlayerState::Dead;
	DeathTime = 0.f;
	bFireHeld = false;
	if (UM80WeaponInventory* Inv = GetInventory())
	{
		Inv->HideWeapon();
	}
	if (UM80OverlayAnimInstance* O = Overlay.Get())
	{
		O->bEnabled = false;
	}
	bShowMap = false;
	W->DisableInput(this);
	SetIgnoreMoveInput(true);
	// Ragdoll: the (hidden) animation mesh falls, the MetaHuman parts follow it.
	const UM80VitalsComponent* V = GetVitals();
	if (!W->GetMesh()->IsSimulatingPhysics())
	{
		Ragdoll(W, W->GetVelocity() + (V ? V->LastHitDirection * 250.f : FVector::ZeroVector));
	}
}

void AM80PlayerController::Respawn()
{
	ACharacter* Old = Walker.Get();
	UnPossess();
	if (Old)
	{
		Old->SetLifeSpan(30.f);
	}
	Walker.Reset();
	Car.Reset();
	State = EM80PlayerState::OnFoot;
	ResetIgnoreMoveInput();
	ResetIgnoreLookInput();
	if (AGameModeBase* GM = GetWorld()->GetAuthGameMode())
	{
		GM->RestartPlayer(this);
	}
	const int32 Fee = FMath::Min(Money, HospitalFee);
	Money -= Fee;
	RespawnAge = 0.f;
	if (Fee > 0)
	{
		ShowHint(TEXT("Spese dell'ospedale: ") + LireText(Fee));
	}
}

bool AM80PlayerController::SetCharacterSprint(bool bSprint)
{
	bool* Wants = WantsToSprint(Walker.Get());
	if (Wants)
	{
		*Wants = bSprint && (!GetVitals() || GetVitals()->CanSprint());
	}
	return Wants != nullptr;
}

void AM80PlayerController::LimitSprint()
{
	ACharacter* W = Walker.Get();
	const UM80VitalsComponent* V = GetVitals();
	bool* Wants = WantsToSprint(W);
	if (!V || !Wants)
	{
		return;
	}
	if (!V->CanSprint())
	{
		if (*Wants)
		{
			*Wants = false;
			bSprintForcedOff = true;
		}
		return;
	}
	if (bSprintForcedOff)
	{
		// Breath is back: sprint again if the key is still held.
		bSprintForcedOff = false;
		const UInputAction* Action = SprintAction.LoadSynchronous();
		const UEnhancedInputLocalPlayerSubsystem* Sub = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer());
		if (Action && Sub && Sub->GetPlayerInput() && Sub->GetPlayerInput()->GetActionValue(Action).Get<bool>())
		{
			*Wants = true;
		}
	}
}

void AM80PlayerController::CheckCarHits(float DeltaTime)
{
	ACharacter* W = Walker.Get();
	UM80VitalsComponent* V = GetVitals();
	HitCooldown -= DeltaTime;
	IgnoreCarTime -= DeltaTime;
	if (!W || !V || V->IsDead() || State != EM80PlayerState::OnFoot || HitCooldown > 0.f)
	{
		return;
	}
	const FVector P = W->GetActorLocation();
	const float Margin = W->GetCapsuleComponent()->GetScaledCapsuleRadius() + 30.f;
	for (TActorIterator<AM80Car> It(GetWorld()); It; ++It)
	{
		AM80Car* C = *It;
		if ((IgnoreCarTime > 0.f && C == IgnoreCar.Get()) || FVector::DistSquared(C->GetActorLocation(), P) > FMath::Square(800.f))
		{
			continue;
		}
		// Inside the car's box grown by the capsule radius (car space)?
		const FBox Local = C->GetMesh()->CalcBounds(FTransform::Identity).GetBox().ExpandBy(FVector(Margin, Margin, 20.f));
		if (!Local.IsInside(C->GetActorTransform().InverseTransformPosition(P)))
		{
			continue;
		}
		const FVector Dir = (P - C->GetActorLocation()).GetSafeNormal2D();
		// Only the car's own speed towards the player counts (running into a parked car does not hurt).
		const float Kmh = (C->GetVelocity() | Dir) * 0.036f;
		if (Kmh < 12.f)
		{
			continue;
		}
		// Run over: thrown up and forward, the faster the car the worse; fast enough, down on the ground.
		const FVector Push = C->GetVelocity() * 0.7f + Dir * 250.f + FVector(0, 0, 250.f + Kmh * 5.f);
		V->TakeHit((Kmh - 10.f) * 1.25f, Dir, C);
		if (V->IsDead())
		{
			return;
		}
		if (Kmh > 22.f)
		{
			KnockDown(Push);
		}
		else
		{
			W->LaunchCharacter(Push, true, true);
		}
		HitCooldown = 0.8f;
		return;
	}
}

void AM80PlayerController::PutOnSunglasses(ACharacter* C)
{
	static const FName Tag(TEXT("M80Occhiali"));
	UStaticMesh* Mesh = Sunglasses.LoadSynchronous();
	if (!Mesh || C->FindComponentByTag<UStaticMeshComponent>(Tag))
	{
		return;
	}
	// MetaHuman face: the eye bones give the place; otherwise fall back to the head of the body mesh.
	USkeletalMeshComponent* Face = nullptr;
	TInlineComponentArray<USkeletalMeshComponent*> Meshes(C);
	for (USkeletalMeshComponent* M : Meshes)
	{
		if (M->DoesSocketExist(TEXT("FACIAL_L_Eye")) && M->DoesSocketExist(TEXT("FACIAL_R_Eye")))
		{
			Face = M;
			break;
		}
	}
	if (!Face)
	{
		return;
	}
	const FVector Eyes = (Face->GetSocketLocation(TEXT("FACIAL_L_Eye")) + Face->GetSocketLocation(TEXT("FACIAL_R_Eye"))) * 0.5f;
	const FVector Fwd = C->GetActorForwardVector();
	UStaticMeshComponent* G = NewObject<UStaticMeshComponent>(C, TEXT("Occhiali"));
	G->ComponentTags.Add(Tag);
	G->SetStaticMesh(Mesh);
	G->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	G->SetCastShadow(true);
	G->RegisterComponent();
	// The glasses face +Y in their mesh: turn them to the character's forward.
	G->SetWorldLocationAndRotation(Eyes + Fwd * 2.2f + FVector(0, 0, 0.3f), FRotator(0.f, C->GetActorRotation().Yaw - 90.f, 0.f));
	const FName Bone = Face->DoesSocketExist(TEXT("head")) ? FName(TEXT("head")) : FName(TEXT("FACIAL_C_FacialRoot"));
	G->AttachToComponent(Face, FAttachmentTransformRules::KeepWorldTransform, Bone);
}

FVector AM80PlayerController::DoorWorld(const AM80Car* C) const
{
	return C->GetActorTransform().TransformPosition(C->DoorOffset);
}

AM80Car* AM80PlayerController::FindCarInReach() const
{
	const ACharacter* W = Walker.Get();
	if (!W)
	{
		return nullptr;
	}
	AM80Car* Best = nullptr;
	float BestDist = ReachDistance;
	for (TActorIterator<AM80Car> It(GetWorld()); It; ++It)
	{
		AM80Car* C = *It;
		const APlayerController* Driver = Cast<APlayerController>(C->GetController());
		if (C->bWrecked || C->GetActorUpVector().Z < 0.5f || (Driver && Driver != this))
		{
			continue;
		}
		const float Dist = FMath::Min(FVector::Dist2D(W->GetActorLocation(), DoorWorld(C)), FVector::Dist2D(W->GetActorLocation(), C->GetActorLocation()) - 100.f);
		if (Dist < BestDist && FMath::Abs(W->GetActorLocation().Z - C->GetActorLocation().Z) < 250.f)
		{
			BestDist = Dist;
			Best = C;
		}
	}
	return Best;
}

void AM80PlayerController::Interact()
{
	if (State == EM80PlayerState::OnFoot)
	{
		if (AM80Car* Target = FindCarInReach())
		{
			StartGetIn(Target);
		}
	}
	else if (State == EM80PlayerState::Driving)
	{
		// Too fast to stop and get out: jump out, the car rolls on.
		StartGetOut(Car.IsValid() && FMath::Abs(Car->GetSpeedKmh()) > MaxExitKmh);
	}
}

void AM80PlayerController::ShowHint(const FString& Text)
{
	Hint = Text;
	HintAge = 0.f;
}

void AM80PlayerController::StartGetIn(AM80Car* Target)
{
	ACharacter* W = Walker.Get();
	if (!W || !Target)
	{
		return;
	}
	Car = Target;
	State = EM80PlayerState::GettingIn;
	PhaseTime = 0.f;
	BreakWait = 0.f;
	Target->OnExploded.AddUniqueDynamic(this, &AM80PlayerController::OnCarExploded);
	SeatStartRel = FVector::ZeroVector;
	SetIgnoreLookInput(true);
}

void AM80PlayerController::FinishGetIn()
{
	ACharacter* W = Walker.Get();
	AM80Car* C = Car.Get();
	if (!W || !C)
	{
		State = EM80PlayerState::OnFoot;
		SetIgnoreLookInput(false);
		return;
	}
	W->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	W->GetCharacterMovement()->StopMovementImmediately();
	W->GetCharacterMovement()->DisableMovement();
	W->AttachToComponent(C->GetMesh(), FAttachmentTransformRules::KeepWorldTransform);
	SeatStartRel = W->GetRootComponent()->GetRelativeLocation();
	SeatStartRot = W->GetRootComponent()->GetRelativeRotation();
	if (SeatedAnim)
	{
		// The sample's animation blueprint does not let a slot override the whole body while the
		// character has no movement: play the driving pose on the mesh directly while seated.
		W->GetMesh()->PlayAnimation(SeatedAnim, true);
	}
}

void AM80PlayerController::StartGetOut(bool bJump)
{
	ACharacter* W = Walker.Get();
	AM80Car* C = Car.Get();
	if (!W || !C)
	{
		return;
	}
	// Driver side first, then the other side, behind and in front (a wall, another car...).
	const UCapsuleComponent* Cap = W->GetCapsuleComponent();
	const float Half = Cap->GetScaledCapsuleHalfHeight();
	const FCollisionShape Shape = FCollisionShape::MakeCapsule(Cap->GetScaledCapsuleRadius() * 0.9f, Half * 0.8f);
	FCollisionQueryParams Params(SCENE_QUERY_STAT(M80Exit), false, C);
	Params.AddIgnoredActor(W);
	const FTransform T = C->GetActorTransform();
	const FVector D = C->DoorOffset;
	const FVector Candidates[] = {D, FVector(D.X, -D.Y, D.Z), FVector(-260.f, D.Y * 0.6f, D.Z), FVector(300.f, D.Y * 0.6f, D.Z),
		FVector(D.X, D.Y * 1.6f, D.Z), FVector(D.X, -D.Y * 1.6f, D.Z)};
	FVector Exit = T.TransformPosition(D);
	for (int32 i = 0; i < UE_ARRAY_COUNT(Candidates); ++i)
	{
		// Jumping out of a moving car: only to the sides (behind or in front the car would hit you).
		if (bJump && (i == 2 || i == 3))
		{
			continue;
		}
		const FVector& Local = Candidates[i];
		// Test a little above the ground so the capsule does not touch the road.
		const FVector P = T.TransformPosition(Local);
		const FVector Test(P.X, P.Y, C->GetActorLocation().Z + Half + 15.f);
		if (!GetWorld()->OverlapBlockingTestByChannel(Test, FQuat::Identity, ECC_Pawn, Shape, Params))
		{
			Exit = Test;
			break;
		}
	}
	const float Yaw = C->GetActorRotation().Yaw;
	State = EM80PlayerState::GettingOut;
	Possess(W);
	W->DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
	W->SetActorLocationAndRotation(Exit, FRotator(0, Yaw, 0), false, nullptr, ETeleportType::TeleportPhysics);
	W->GetMesh()->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	W->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	W->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
	SetControlRotation(FRotator(-10.f, Yaw, 0));
	SetViewTargetWithBlend(W, 0.6f, VTBlend_EaseInOut, 2.f);
	SetIgnoreLookInput(false);
	Car.Reset();
	State = EM80PlayerState::OnFoot;
	if (bJump)
	{
		const float Kmh = FMath::Abs(C->GetSpeedKmh());
		const FVector Side = (Exit - C->GetActorLocation()).GetSafeNormal2D();
		W->LaunchCharacter(C->GetVelocity() * 0.55f + Side * 350.f + FVector(0, 0, 220.f), true, true);
		IgnoreCar = C;
		IgnoreCarTime = 1.5f;
		bRollOnLanding = true;
		if (UM80VitalsComponent* V = GetVitals())
		{
			V->TakeHit(FMath::Clamp(4.f + (Kmh - MaxExitKmh) * 0.4f, 4.f, 35.f), Side, C);
		}
	}
}

void AM80PlayerController::PlayerTick(float DeltaTime)
{
	Super::PlayerTick(DeltaTime);
	StreetNameAge += DeltaTime;
	VehicleNameAge += DeltaTime;
	HintAge += DeltaTime;
	RespawnAge += DeltaTime;

	if (State == EM80PlayerState::KnockedDown)
	{
		KnockTime += DeltaTime;
		if (ACharacter* W = Walker.Get())
		{
			const FVector Pelvis = W->GetMesh()->GetSocketLocation(TEXT("pelvis"));
			W->SetActorLocation(Pelvis + FVector(0, 0, 40.f));
			const float Moving = W->GetMesh()->GetPhysicsLinearVelocity(TEXT("pelvis")).Size();
			if (KnockTime > 4.f || (KnockTime > 1.8f && Moving < 40.f))
			{
				GetUp();
			}
		}
		return;
	}
	// Get-up / roll playing on the animation mesh: back to the sample's animation when it ends.
	if (AnimLockTime >= 0.f)
	{
		AnimLockTime -= DeltaTime;
		if (AnimLockTime < 0.f)
		{
			if (ACharacter* W = Walker.Get())
			{
				W->GetMesh()->SetAnimationMode(EAnimationMode::AnimationBlueprint);
			}
			ResetIgnoreMoveInput();
			if (UM80OverlayAnimInstance* O = Overlay.Get())
			{
				O->bEnabled = true;
			}
		}
	}
	if (State == EM80PlayerState::Dead)
	{
		DeathTime += DeltaTime;
		// The ragdoll left the capsule (and the camera on it) behind: keep the capsule over the body.
		if (ACharacter* W = Walker.Get())
		{
			W->SetActorLocation(W->GetMesh()->GetSocketLocation(TEXT("pelvis")) + FVector(0, 0, 40.f));
		}
		if (DeathTime > RespawnDelay)
		{
			Respawn();
		}
		return;
	}
	if (ACharacter* W = Walker.Get(); W && State == EM80PlayerState::OnFoot)
	{
		if (W->GetCharacterMovement()->IsFalling())
		{
			FallPeak = FMath::Max(FallPeak, -W->GetVelocity().Z);
		}
		LimitSprint();
		CheckCarHits(DeltaTime);
	}
	UpdateWeapons(DeltaTime);

	StreetTimer -= DeltaTime;
	if (StreetTimer <= 0.f)
	{
		StreetTimer = 0.5f;
		UpdateStreetName();
		CarInReach = State == EM80PlayerState::OnFoot ? FindCarInReach() : nullptr;
	}

	if (State != EM80PlayerState::GettingIn)
	{
		return;
	}
	ACharacter* W = Walker.Get();
	AM80Car* C = Car.Get();
	if (!W || !C)
	{
		State = EM80PlayerState::OnFoot;
		SetIgnoreLookInput(false);
		return;
	}
	PhaseTime += DeltaTime;
	if (SeatStartRel.IsZero() && !W->IsAttachedTo(C))
	{
		// 1) Walk to the driver door (the character's own locomotion animates it).
		const FVector Door = DoorWorld(C);
		FVector To = Door - W->GetActorLocation();
		To.Z = 0.f;
		if (To.Size() > 45.f && PhaseTime < WalkToDoorMax)
		{
			W->AddMovementInput(To.GetSafeNormal(), To.Size() < 150.f ? 0.5f : 1.f);
			return;
		}
		// Locked: break the window first (GTA), then get in.
		if (C->bLocked)
		{
			C->BreakWindow();
			BreakWait = 0.8f;
			ShowHint(TEXT("Era chiusa a chiave: finestrino rotto"));
		}
		if (BreakWait > 0.f)
		{
			BreakWait -= DeltaTime;
			return;
		}
		FinishGetIn();
		PhaseTime = 0.f;
		return;
	}
	// 2) Slide from the door into the seat while the driving pose blends in.
	const float A = FMath::Clamp(PhaseTime / SlideInTime, 0.f, 1.f);
	const float E = A * A * (3.f - 2.f * A);
	USceneComponent* Root = W->GetRootComponent();
	Root->SetRelativeLocation(FMath::Lerp(SeatStartRel, C->SeatOffset, E));
	Root->SetRelativeRotation(FQuat::Slerp(SeatStartRot.Quaternion(), FQuat::Identity, E));
	if (A >= 1.f)
	{
		Possess(C);
		SetViewTargetWithBlend(C, 0.8f, VTBlend_EaseInOut, 2.f);
		SetIgnoreLookInput(false);
		State = EM80PlayerState::Driving;
		VehicleName = C->DisplayName.ToString();
		VehicleNameAge = 0.f;
	}
}

void AM80PlayerController::UpdateStreetName()
{
	const APawn* P = GetPawn();
	if (!P)
	{
		return;
	}
	const FVector Loc = P->GetActorLocation();
	FString Best;
	float BestDist = 2500.f;
	for (TActorIterator<AMazzarinoRoadSpline> It(GetWorld()); It; ++It)
	{
		if (It->RoadName.IsEmpty() || It->RoadName.StartsWith(TEXT("Senza_nome")) || !It->Spline)
		{
			continue;
		}
		const FBox Box = It->Spline->Bounds.GetBox().ExpandBy(BestDist);
		if (!Box.IsInsideXY(Loc))
		{
			continue;
		}
		const FVector Q = It->Spline->FindLocationClosestToWorldLocation(Loc, ESplineCoordinateSpace::World);
		const float D = FVector::Dist2D(Q, Loc);
		if (D < BestDist)
		{
			BestDist = D;
			Best = It->RoadName;
		}
	}
	if (!Best.IsEmpty() && Best != StreetName)
	{
		StreetName = Best;
		StreetNameAge = 0.f;
	}
}
