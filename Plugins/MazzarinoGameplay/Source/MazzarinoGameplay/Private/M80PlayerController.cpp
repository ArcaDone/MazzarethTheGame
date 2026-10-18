#include "M80PlayerController.h"
#include "M80PlayerCamera.h"
#include "Kismet/GameplayStatics.h"
#include "M80Climb.h"
#include "M80TargetDummy.h"
#include "EngineUtils.h"
#include "M80Car.h"
#include "M80Vitals.h"
#include "M80Weapons.h"
#include "M80OverlayAnim.h"
#include "M80Pedone.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
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
	PlayerCameraManagerClass = AM80PlayerCameraManager::StaticClass();
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
	BindKeyLambda(EKeys::Q, [this]() { if (bWheelOpen) { WheelNext(1); } else if (UM80WeaponInventory* Inv = GetInventory()) { Inv->Cycle(1); } });
	BindKeyLambda(EKeys::MouseScrollUp, [this]() { if (bWheelOpen) { WheelNext(1); } });
	BindKeyLambda(EKeys::MouseScrollDown, [this]() { if (bWheelOpen) { WheelNext(-1); } });
	BindKeyLambda(EKeys::Gamepad_FaceButton_Left, [this]() { if (bWheelOpen) { WheelNext(1); } });
	// The weapon wheel: open while held.
	for (const FKey& K : {EKeys::Tab, EKeys::Gamepad_LeftShoulder})
	{
		BindKeyLambda(K, [this]() { OpenWheel(); });
		FInputKeyBinding Up{FInputChord(K), IE_Released};
		Up.bConsumeInput = false;
		Up.KeyDelegate.GetDelegateForManualSet().BindLambda([this]() { CloseWheel(true); });
		InputComponent->KeyBindings.Add(Up);
	}
	BindKeyLambda(EKeys::Gamepad_DPad_Right, [this]() { if (UM80WeaponInventory* Inv = GetInventory()) { Inv->Cycle(1); } });
	BindKeyLambda(EKeys::Gamepad_DPad_Left, [this]() { if (UM80WeaponInventory* Inv = GetInventory()) { Inv->Cycle(-1); } });
	auto OnFootDo = [this](TFunction<void(UM80WeaponInventory*)> Fn)
	{
		return [this, Fn]() { if (UM80WeaponInventory* Inv = GetInventory(); Inv && State == EM80PlayerState::OnFoot) { Fn(Inv); } };
	};
	BindKeyLambda(EKeys::R, OnFootDo([](UM80WeaponInventory* Inv) { Inv->Reload(); }));
	// Gamepad X reloads, but inside the open wheel it changes the weapon of the sector.
	BindKeyLambda(EKeys::Gamepad_FaceButton_Left, OnFootDo([this](UM80WeaponInventory* Inv) { if (!bWheelOpen) { Inv->Reload(); } }));
	BindKeyLambda(EKeys::G, OnFootDo([](UM80WeaponInventory* Inv) { Inv->DropCurrent(); }));
	// Climbing: jump climbs onto things, catches ledges and acts on the ledge held; C / Ctrl / B let go.
	for (const FKey& K : {EKeys::SpaceBar, EKeys::Gamepad_FaceButton_Bottom})
	{
		BindKeyLambda(K, [this]() { if (UM80ClimbComponent* Cl = GetClimb()) { if (State == EM80PlayerState::OnFoot) { Cl->JumpPressed(); } } });
	}
	for (const FKey& K : {EKeys::C, EKeys::LeftControl, EKeys::Gamepad_FaceButton_Right})
	{
		BindKeyLambda(K, [this]() { if (UM80ClimbComponent* Cl = GetClimb()) { Cl->Drop(); } });
	}
	BindKeyLambda(EKeys::Gamepad_DPad_Down, OnFootDo([](UM80WeaponInventory* Inv) { Inv->DropCurrent(); }));
}

void AM80PlayerController::BindKeyLambda(const FKey& Key, TFunction<void()> Fn)
{
	FInputKeyBinding B{FInputChord(Key), IE_Pressed};
	B.bConsumeInput = false;
	B.KeyDelegate.GetDelegateForManualSet().BindLambda(MoveTemp(Fn));
	InputComponent->KeyBindings.Add(B);
}

UM80ClimbComponent* AM80PlayerController::GetClimb() const
{
	const ACharacter* W = Walker.Get();
	return W ? W->FindComponentByClass<UM80ClimbComponent>() : nullptr;
}

UM80WeaponInventory* AM80PlayerController::GetInventory() const
{
	const ACharacter* W = Walker.Get();
	return W ? W->FindComponentByClass<UM80WeaponInventory>() : nullptr;
}

void AM80PlayerController::SetFire(bool bDown)
{
	if (bWheelOpen && bDown)
	{
		return;
	}
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
	if (bAimFrozen)
	{
		return FrozenAim;
	}
	// Locked on a person (gamepad): the shot goes to the chest.
	if (const ACharacter* T = LockTarget.Get())
	{
		const AM80TargetDummy* D = Cast<AM80TargetDummy>(T);
		return D ? D->AimPoint() : T->GetActorLocation() + FVector(0.f, 0.f, 45.f);
	}
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

int32 AM80PlayerController::WheelCategory(int32 Sector)
{
	// Clockwise from the top: pistols, machine pistols, shotguns, rifles, fists (bottom), melee, heavy, thrown.
	static const int32 Map[M80WeaponCategories] = {2, 4, 3, 5, 0, 1, 7, 6};
	return Map[((Sector % M80WeaponCategories) + M80WeaponCategories) % M80WeaponCategories];
}

void AM80PlayerController::OpenWheel()
{
	if (bWheelOpen || State != EM80PlayerState::OnFoot || !GetInventory())
	{
		return;
	}
	bWheelOpen = true;
	WheelCursor = FVector2D::ZeroVector;
	// Start on the sector of the weapon in hand.
	WheelSector = -1;
	const int32 Cat = M80WeaponSpec(GetInventory()->GetCurrentWeapon()).Slot;
	for (int32 i = 0; i < M80WeaponCategories; ++i)
	{
		if (WheelCategory(i) == Cat)
		{
			WheelSector = i;
		}
	}
	SetFire(false);
	SetIgnoreLookInput(true);
	UGameplayStatics::SetGlobalTimeDilation(this, 0.3f);
}

void AM80PlayerController::CloseWheel(bool bTake)
{
	if (!bWheelOpen)
	{
		return;
	}
	bWheelOpen = false;
	ResetIgnoreLookInput();
	UGameplayStatics::SetGlobalTimeDilation(this, 1.f);
	UM80WeaponInventory* Inv = GetInventory();
	if (bTake && Inv && WheelSector >= 0)
	{
		Inv->SelectSlot(WheelCategory(WheelSector));
	}
}

void AM80PlayerController::PointWheel(int32 Sector)
{
	WheelSector = ((Sector % M80WeaponCategories) + M80WeaponCategories) % M80WeaponCategories;
	const float A = FMath::DegreesToRadians(WheelSector * 45.f);
	WheelCursor = FVector2D(FMath::Sin(A), FMath::Cos(A));
}

void AM80PlayerController::WheelNext(int32 Dir)
{
	UM80WeaponInventory* Inv = GetInventory();
	if (!Inv || WheelSector < 0)
	{
		return;
	}
	const int32 Cat = WheelCategory(WheelSector);
	const TArray<EM80Weapon> In = Inv->WeaponsIn(Cat);
	if (In.Num() > 1)
	{
		const int32 At = In.IndexOfByKey(Inv->ChosenIn(Cat));
		Inv->ChooseIn(In[((At == INDEX_NONE ? 0 : At) + Dir + In.Num()) % In.Num()]);
	}
}

void AM80PlayerController::UpdateWheel()
{
	if (!bWheelOpen)
	{
		return;
	}
	if (State != EM80PlayerState::OnFoot)
	{
		CloseWheel(false);
		return;
	}
	// Mouse: the cursor moves with it (screen up = +Y); right stick: it points directly.
	float DX = 0.f, DY = 0.f;
	GetInputMouseDelta(DX, DY);
	WheelCursor += FVector2D(DX, DY) * 0.08f;
	float SX = 0.f, SY = 0.f;
	GetInputAnalogStickState(EControllerAnalogStick::CAS_RightStick, SX, SY);
	if (FVector2D(SX, SY).Size() > 0.4f)
	{
		WheelCursor = FVector2D(SX, SY);
	}
	if (WheelCursor.Size() > 1.f)
	{
		WheelCursor.Normalize();
	}
	if (WheelCursor.Size() > 0.35f)
	{
		// 0 at the top, clockwise.
		const float Deg = FMath::RadiansToDegrees(FMath::Atan2(WheelCursor.X, WheelCursor.Y));
		WheelSector = FMath::FloorToInt(FMath::Fmod(Deg + 360.f + 22.5f, 360.f) / 45.f) % M80WeaponCategories;
	}
}

bool AM80PlayerController::LockOn()
{
	ACharacter* W = Walker.Get();
	if (!W)
	{
		return false;
	}
	FVector Eye;
	FRotator Rot;
	GetPlayerViewPoint(Eye, Rot);
	const FVector Fwd = Rot.Vector();
	ACharacter* Best = nullptr;
	float BestScore = 0.f;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(M80LockOn), false, W);
	for (TActorIterator<ACharacter> It(GetWorld()); It; ++It)
	{
		ACharacter* C = *It;
		if (C == W)
		{
			continue;
		}
		const UM80VitalsComponent* V = C->FindComponentByClass<UM80VitalsComponent>();
		if (!V || V->IsDead())
		{
			continue;
		}
		const FVector To = C->GetActorLocation() + FVector(0.f, 0.f, 45.f) - Eye;
		const float Dist = To.Size();
		const float Cos = FVector::DotProduct(To / FMath::Max(Dist, 1.f), Fwd);
		if (Dist > 3500.f || Cos < FMath::Cos(FMath::DegreesToRadians(30.f)))
		{
			continue;
		}
		// In sight.
		FHitResult Hit;
		Q.ClearIgnoredSourceObjects();
		Q.AddIgnoredActor(W);
		if (GetWorld()->LineTraceSingleByChannel(Hit, Eye, Eye + To, ECC_Visibility, Q) && Hit.GetActor() != C)
		{
			continue;
		}
		// Nearer and more central first.
		const float Score = Cos * 2.f - Dist / 3500.f;
		if (!Best || Score > BestScore)
		{
			Best = C;
			BestScore = Score;
		}
	}
	LockTarget = Best;
	return Best != nullptr;
}

void AM80PlayerController::UpdateLockOn(float DeltaTime)
{
	// The gamepad aim (left trigger) locks on as it is pulled and keeps the person while it is held.
	const bool bPad = GetInputAnalogKeyState(EKeys::Gamepad_LeftTriggerAxis) > 0.3f;
	if (bPad && !bPadAimWas)
	{
		LockOn();
	}
	bPadAimWas = bPad;
	ACharacter* T = LockTarget.Get();
	const UM80VitalsComponent* V = T ? T->FindComponentByClass<UM80VitalsComponent>() : nullptr;
	if (!T || !V || V->IsDead() || (!bPad && !bLockHeld) || !bAimingNow)
	{
		if (!bLockHeld)
		{
			LockTarget.Reset();
		}
		return;
	}
	// The camera follows the target.
	FVector Eye;
	FRotator Rot;
	GetPlayerViewPoint(Eye, Rot);
	const FRotator Want = (GetAimPoint() - Eye).Rotation();
	SetControlRotation(FMath::RInterpTo(GetControlRotation(), FRotator(Want.Pitch, Want.Yaw, 0.f), DeltaTime, 10.f));
}

void AM80PlayerController::UpdateClimbInput()
{
	// While climbing the move stick / WASD moves along the ledge: the component gets it in world space.
	UM80ClimbComponent* Cl = GetClimb();
	if (!Cl || !Cl->IsClimbing())
	{
		return;
	}
	const UInputAction* Move = MoveAction.LoadSynchronous();
	const UEnhancedInputLocalPlayerSubsystem* Sub = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer());
	FVector2D V = FVector2D::ZeroVector;
	if (Move && Sub && Sub->GetPlayerInput())
	{
		V = Sub->GetPlayerInput()->GetActionValue(Move).Get<FVector2D>();
	}
	// A / D (stick left/right) always go along the wall, W / S towards / away from it; flipped only when the
	// camera looks away from the wall, so that right stays right on screen.
	const FVector Facing = -Cl->GetWallNormal();
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Facing);
	const float Flip = FVector::DotProduct(FRotator(0.f, GetControlRotation().Yaw, 0.f).Vector(), Facing) < -0.3f ? -1.f : 1.f;
	Cl->SetMoveInput(Right * V.X * Flip + Facing * V.Y);
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
	// Climbing needs both hands: the weapon is put away (no aiming, no shots) and comes back after.
	const UM80ClimbComponent* Climb = GetClimb();
	const bool bClimbing = Climb && Climb->IsClimbing();
	Inv->SetHolstered(bClimbing);
	const bool bOnFoot = State == EM80PlayerState::OnFoot && !bClimbing;
	ForceAimTime -= DeltaTime;
	// Aim: right mouse (the sample turns the character to the camera), or held for a moment after a shot.
	bool* WantsAim = InputStateFlag(W, TEXT("WantsToAim"));
	// The sample's IA_Aim only fires on press and release: the held state comes from the keys themselves.
	const bool bRMB = IsInputKeyDown(EKeys::RightMouseButton) || GetInputAnalogKeyState(EKeys::Gamepad_LeftTriggerAxis) > 0.3f || bAimHeld;
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
	if (WantsAim && bAimHeld != bAimHeldApplied)
	{
		*WantsAim = bAimHeld;   // the sample's own aim state follows SetAimHeld
		bAimHeldApplied = bAimHeld;
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
	Inv->SetAim(bAimingNow, GetAimPoint());
	if (O)
	{
		O->Pose = bOnFoot ? S.Pose : EM80WeaponPose::Unarmed;
		O->bAiming = bAimingNow;
		O->AimPoint = bAimingNow ? GetAimPoint() : FVector::ZeroVector;
		O->SinceFire = Inv->SinceFire();
		O->ComboStep = Inv->GetComboStep();
		O->bEnabled = bOnFoot;
		O->bClimbing = bClimbing;
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
		// Walking into a chair or a table moves it; into a parked car does not (the default push, 7500 N, shoved cars).
		C->GetCharacterMovement()->bEnablePhysicsInteraction = true;
		C->GetCharacterMovement()->PushForceFactor = 60000.f;
		C->GetCharacterMovement()->InitialPushForceFactor = 100.f;
		if (!C->FindComponentByClass<UM80ClimbComponent>())
		{
			NewObject<UM80ClimbComponent>(C, TEXT("M80Arrampicata"))->RegisterComponent();
		}
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

void AM80PlayerController::OnRiderThrown(AM80Car* From, FVector Velocity, float Damage)
{
	ACharacter* W = Walker.Get();
	if (!W || From != Car.Get() || State != EM80PlayerState::Driving)
	{
		return;
	}
	// Off the saddle (into something hard, over backwards in a wheelie, down on its side): the body flies on as a ragdoll
	// and gets up again, unless the fall hurt too much.
	const FVector At = W->GetMesh()->GetSocketLocation(TEXT("pelvis"));
	Possess(W);
	W->DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
	W->SetActorLocationAndRotation(At + FVector(0.f, 0.f, 20.f), FRotator(0.f, From->GetActorRotation().Yaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
	W->GetMesh()->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	SetViewTargetWithBlend(W, 0.3f, VTBlend_EaseInOut, 2.f);
	SetIgnoreLookInput(false);
	Car.Reset();
	IgnoreCar = From;
	IgnoreCarTime = 1.5f;
	State = EM80PlayerState::OnFoot;
	if (UM80VitalsComponent* V = GetVitals())
	{
		V->TakeHit(Damage, Velocity.GetSafeNormal(), From);
		if (V->IsDead())
		{
			return;
		}
	}
	KnockDown(Velocity);
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
	// The capsule follows the body while it lies (the camera is on it): the mesh must not be dragged along with it.
	const FTransform T = M->GetComponentTransform();
	M->SetUsingAbsoluteLocation(true);
	M->SetUsingAbsoluteRotation(true);
	M->SetWorldLocationAndRotation(T.GetLocation(), T.GetRotation());
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
	M->SetUsingAbsoluteLocation(false);
	M->SetUsingAbsoluteRotation(false);
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
	// The glasses face +Y in their mesh: turn them to the character's forward. Sized and set off the eyes for Sandro's
	// face (broader, deeper-set eyes than the sample's Kellan): a little wider and further out, or the lenses sink in.
	G->SetWorldScale3D(FVector(1.1f));
	G->SetWorldLocationAndRotation(Eyes + Fwd * 3.6f + FVector(0, 0, 0.5f), FRotator(0.f, C->GetActorRotation().Yaw - 90.f, 0.f));
	const FName Bone = Face->DoesSocketExist(TEXT("head")) ? FName(TEXT("head")) : FName(TEXT("FACIAL_C_FacialRoot"));
	G->AttachToComponent(Face, FAttachmentTransformRules::KeepWorldTransform, Bone);
}

FVector AM80PlayerController::SeatFor(const AM80Car* C) const
{
	static const FName Sella(TEXT("Sella"));
	const USkeletalMeshComponent* M = C->GetMesh();
	if (M && M->DoesSocketExist(Sella))
	{
		// Attached to the vehicle's mesh, facing its front: the character's mesh origin on the Sella bone.
		return M->GetSocketTransform(Sella, RTS_Component).GetLocation() - MeshRelative.GetLocation();
	}
	return C->SeatOffset;
}

void AM80PlayerController::UpdateRide()
{
	UM80OverlayAnimInstance* O = Overlay.Get();
	if (!O)
	{
		return;
	}
	const ACharacter* W = Walker.Get();
	const AM80Car* C = Car.Get();
	const USkeletalMeshComponent* M = C ? C->GetMesh() : nullptr;
	static const FName Hand[2] = {TEXT("Mano_L"), TEXT("Mano_R")};
	static const FName Foot[2] = {TEXT("Piede_L"), TEXT("Piede_R")};
	// Fists round the grips while on a moped, getting on and off, picking it up.
	O->RideFists = FMath::FInterpTo(O->RideFists, C && W && C->IsTwoWheeler() && (W->IsAttachedTo(C) || PickingUp.Get() == C) ? 1.f : 0.f,
		GetWorld()->GetDeltaSeconds(), 8.f);
	if (C && M && W && PickingUp.Get() == C)
	{
		// Picking it up: the hands down to the grips as the body bends (0.35-0.65 s), the moped up as it stands (1.0-1.73 s;
		// Research/Mazzarino80/Blender/m80_motorino_gioco.py, mount_keys).
		O->RideWeight = FMath::SmoothStep(0.35f, 0.65f, ClipTime);
		O->bRideFeet = false;
		O->RideLean = 0.f;
		O->bRideSteadyJoints = true;
		for (int32 k = 0; k < 2; ++k)
		{
			O->RideHand[k] = M->GetSocketLocation(Hand[k]);
		}
		PickingUp->SetPickUp(FMath::SmoothStep(1.0f, 1.73f, ClipTime));
		RideLocal(O, W);
		return;
	}
	const bool bOn = W && M && (C->bCart || C->IsTwoWheeler()) && W->IsAttachedTo(C) && !ClipNow
		&& (State == EM80PlayerState::GettingIn || State == EM80PlayerState::Driving) && M->DoesSocketExist(Hand[0]);
	// Comes in with the slide onto the seat (on a moped the getting-on clip ends in the pose: at once).
	O->RideWeight = !bOn ? 0.f : (State == EM80PlayerState::Driving ? 1.f : FMath::Clamp(PhaseTime / SlideInTime, 0.f, 1.f));
	if (!bOn)
	{
		FootDown = 0.f;
		return;
	}
	O->bRideFeet = M->DoesSocketExist(Foot[0]);
	for (int32 k = 0; k < 2; ++k)
	{
		O->RideHand[k] = M->GetSocketLocation(Hand[k]);
		if (O->bRideFeet)
		{
			O->RideFoot[k] = M->GetSocketLocation(Foot[k]);
		}
	}
	O->RideLean = C->GetRiderLean();
	O->bRideSteadyJoints = C->IsTwoWheeler();
	if (C->IsTwoWheeler() && O->bRideFeet)
	{
		// Stopped or nearly: the left foot off the pedal, down on the road beside it (out to the left, a little forward).
		// Walking it back (no reverse gear): both feet down, stepping back in turn.
		const float Dt = GetWorld()->GetDeltaSeconds();
		const bool bBack = State == EM80PlayerState::Driving && C->IsBackingUp();
		const bool bStill = State == EM80PlayerState::Driving && FMath::Abs(C->GetSpeedKmh()) < 4.f;
		FootDown = FMath::FInterpTo(FootDown, bStill || bBack ? 1.f : 0.f, Dt, 6.f);
		FootDownRight = FMath::FInterpTo(FootDownRight, bBack ? 1.f : 0.f, Dt, 6.f);
		const float Downs[2] = {FootDown, FootDownRight};
		const FTransform T = C->GetActorTransform();
		for (int32 k = 0; k < 2; ++k)
		{
			if (Downs[k] <= 0.01f)
			{
				continue;
			}
			const float Stride = bBack ? 14.f * FMath::Sin(GetWorld()->GetTimeSeconds() * 2.f * PI * 1.2f + k * PI) : 0.f;
			const FVector Beside = O->RideFoot[k] + T.TransformVector(FVector(12.f + Stride, k == 0 ? -22.f : 22.f, 0.f));
			FHitResult Hit;
			FCollisionQueryParams Params(SCENE_QUERY_STAT(M80FootDown), false, C);
			Params.AddIgnoredActor(W);
			const bool bGround = GetWorld()->LineTraceSingleByChannel(Hit, Beside + FVector(0, 0, 30.f), Beside - FVector(0, 0, 120.f), ECC_Visibility, Params);
			const FVector Down = bGround ? Hit.ImpactPoint + FVector(0, 0, 9.f) : Beside - FVector(0, 0, 25.f);
			O->RideFoot[k] = FMath::Lerp(O->RideFoot[k], Down, Downs[k]);
		}
	}
	RideLocal(O, W);
}

void AM80PlayerController::RideLocal(UM80OverlayAnimInstance* O, const ACharacter* W) const
{
	// The targets in the animation mesh's space, now, with the vehicle's sockets just read (see bRideLocal).
	const FTransform& ST = W->GetMesh()->GetComponentTransform();
	for (int32 k = 0; k < 2; ++k)
	{
		O->RideHandLocal[k] = ST.InverseTransformPosition(O->RideHand[k]);
		O->RideFootLocal[k] = ST.InverseTransformPosition(O->RideFoot[k]);
	}
	O->bRideLocal = true;
}

FVector AM80PlayerController::DoorWorld(const AM80Car* C) const
{
	// A moped is got on (or picked up) from beside where it stands upright, also when it lies on its side.
	return (C->IsTwoWheeler() ? C->GetUprightTransform() : C->GetActorTransform()).TransformPosition(C->DoorOffset);
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
		if (C->bWrecked || (C->GetActorUpVector().Z < 0.5f && !C->IsTwoWheeler()) || (Driver && Driver != this))
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
		// The nearer of a car's door and a chair.
		AM80Car* Target = FindCarInReach();
		AActor* Seat = FindChairInReach();
		const ACharacter* W = Walker.Get();
		if (Seat && (!Target || (W && FVector::Dist2D(Seat->GetActorLocation(), W->GetActorLocation()) < FVector::Dist2D(DoorWorld(Target), W->GetActorLocation()))))
		{
			SitDown(Seat);
		}
		else if (Target)
		{
			StartGetIn(Target);
		}
	}
	else if (State == EM80PlayerState::Sitting)
	{
		if (!ClipNow)
		{
			StandUp();
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
	Target->OnRiderThrown.AddUniqueDynamic(this, &AM80PlayerController::OnRiderThrown);
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
	// The vehicle's own pose (carts: lying on the chest, go-kart, chopper), else the driving pose.
	UAnimSequenceBase* Pose = C->RidePose.IsNull() ? nullptr : C->RidePose.LoadSynchronous();
	if (Pose || SeatedAnim)
	{
		// The sample's animation blueprint does not let a slot override the whole body while the
		// character has no movement: play the driving pose on the mesh directly while seated.
		W->GetMesh()->PlayAnimation(Pose ? Pose : SeatedAnim.Get(), true);
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
	if (!bJump && C->IsTwoWheeler() && FMath::Abs(C->GetSpeedKmh()) < 3.f && FVector::Dist2D(Exit, T.TransformPosition(D)) < 1.f && GetOffAstride(C))
	{
		return;
	}
	UAnimSequence* OutClip = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/Mazzarino80/Personaggi/Animazioni/A_M80_Folla_Scende.A_M80_Folla_Scende"), nullptr, LOAD_NoWarn);
	if (!bJump && OutClip && ActsCar(C) && FMath::Abs(C->GetSpeedKmh()) < 3.f && FVector::Dist2D(Exit, T.TransformPosition(D)) < 1.f)
	{
		// Driver's door free: gets out acted (from the seat, to the left, the door shut), then walks.
		State = EM80PlayerState::GettingOut;
		Possess(W);
		// Possess restarts the pawn walking: it stays put (the clip moves it) until the clip ends.
		W->GetCharacterMovement()->DisableMovement();
		W->DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
		FVector Seat = C->GetMesh()->GetComponentTransform().TransformPosition(C->SeatOffset);
		Seat.Z = C->GetActorLocation().Z + Half + 2.f;
		W->SetActorLocationAndRotation(Seat, FRotator(0, Yaw, 0), false, nullptr, ETeleportType::TeleportPhysics);
		SetControlRotation(FRotator(-10.f, Yaw, 0));
		SetViewTargetWithBlend(W, 0.6f, VTBlend_EaseInOut, 2.f);
		SetIgnoreLookInput(false);
		SetIgnoreMoveInput(true);
		Car.Reset();
		// The clip's seat is 81 cm from the ground, ours lower: down at first, back up as the feet come out.
		ClipDrop = FMath::Clamp(81.f - float(C->SeatOffset.Z), 0.f, 45.f);
		PlayWithRoot(OutClip, 0.f, 3.4f, [this]()
		{
			ClipDrop = 0.f;
			BackOnFoot();
		});
		return;
	}
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

	TickClip(DeltaTime);
	// Climbing is for the character on foot: in a vehicle, getting in or out, seated or down it catches no ledge (put
	// down by the door it once caught the car itself, and the capsule pulled into the car threw it into the air).
	if (State != EM80PlayerState::OnFoot)
	{
		if (UM80ClimbComponent* Cl = GetClimb())
		{
			Cl->Suspend(0.6f);
		}
	}
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
	UpdateRide();
	UpdateClimbInput();
	UpdateWheel();
	UpdateLockOn(DeltaTime);

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
	if (ClipNow)
	{
		return;   // getting in, acted out (TickClip)
	}
	if (SeatStartRel.IsZero() && !W->IsAttachedTo(C))
	{
		// 1) Walk to the driver door (the character's own locomotion animates it); for the acted getting in, to
		// where the clip starts.
		const bool bActs = ActsCar(C);
		const bool bAstride = C->IsTwoWheeler();
		const FVector Door = bActs ? EnterStart(C) : DoorWorld(C);
		FVector To = Door - W->GetActorLocation();
		To.Z = 0.f;
		if (To.Size() > (bActs || bAstride ? 25.f : 45.f) && PhaseTime < WalkToDoorMax)
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
		if (bAstride && C->IsLyingDown() && PickUpAstride(C))
		{
			return;
		}
		if (bAstride && GetOnAstride(C))
		{
			return;
		}
		if (bActs)
		{
			// Facing the car, opens the door, ducks in and sits; then onto the seat as before.
			W->GetCharacterMovement()->StopMovementImmediately();
			W->GetCharacterMovement()->DisableMovement();
			W->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			W->SetActorRotation(FRotator(0.f, C->GetActorRotation().Yaw + 90.f, 0.f));
			if (UM80OverlayAnimInstance* O = Overlay.Get())
			{
				O->bEnabled = false;
			}
			UAnimSequence* In = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/Mazzarino80/Personaggi/Animazioni/A_M80_Folla_Sale.A_M80_Folla_Sale"), nullptr, LOAD_NoWarn);
			PlayWithRoot(In, 0.9f, 3.15f, [this]()
			{
				FinishGetIn();
				PhaseTime = 0.f;
			});
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
	Root->SetRelativeLocation(FMath::Lerp(SeatStartRel, SeatFor(C), E));
	Root->SetRelativeRotation(FQuat::Slerp(SeatStartRot.Quaternion(), FRotator(C->SeatRecline, 0.f, 0.f).Quaternion(), E));
	if (A >= 1.f)
	{
		Possess(C);
		SetViewTargetWithBlend(C, 0.8f, VTBlend_EaseInOut, 2.f);
		SetIgnoreLookInput(false);
		State = EM80PlayerState::Driving;
		VehicleName = C->DisplayName.ToString();
		if (!VehicleName.IsEmpty())
		{
			VehicleName[0] = FChar::ToUpper(VehicleName[0]);   // carts are named in lower case for the hints
		}
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

// ---------------------------------------------------------------------------------------------
// Acted moves: getting in and out of a car, sitting down and standing up (the townspeople's clips)

bool AM80PlayerController::PickUpAstride(AM80Car* C)
{
	ACharacter* W = Walker.Get();
	UAnimSequence* Clip = Cast<UAnimSequence>(C->PickUpClip.LoadSynchronous());
	if (!W || !Clip)
	{
		return false;
	}
	// Standing where getting on starts, facing its front; its body off (not pushing the moped).
	W->GetCharacterMovement()->StopMovementImmediately();
	W->GetCharacterMovement()->DisableMovement();
	W->GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	const FTransform Up = C->GetUprightTransform();
	FVector Stand = Up.TransformPosition(FVector(C->DoorOffset.X, C->DoorOffset.Y, 0.f));
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(M80PickUp), false, C);
	Params.AddIgnoredActor(W);
	if (GetWorld()->LineTraceSingleByChannel(Hit, Stand + FVector(0, 0, 100.f), Stand - FVector(0, 0, 150.f), ECC_Visibility, Params))
	{
		Stand = Hit.ImpactPoint;
	}
	W->SetActorLocationAndRotation(Stand + FVector(0.f, 0.f, W->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 2.f),
		Up.GetRotation(), false, nullptr, ETeleportType::TeleportPhysics);
	C->BeginPickUp();
	PickingUp = C;
	PlayWithRoot(Clip, 0.f, -1.f, [this]()
	{
		AM80Car* Moped = PickingUp.Get();
		PickingUp.Reset();
		if (Moped)
		{
			Moped->EndPickUp();
			// On from where picking it up ended: standing beside it, the hands on the grips (frame 16 of getting on).
			if (!GetOnAstride(Moped, 0.53f))
			{
				FinishGetIn();
			}
		}
	});
	return true;
}

bool AM80PlayerController::GetOnAstride(AM80Car* C, float From)
{
	ACharacter* W = Walker.Get();
	UAnimSequence* Clip = Cast<UAnimSequence>(C->MountClip.LoadSynchronous());
	if (!W || !Clip)
	{
		return false;
	}
	// On the moped from where the clip starts: attached to it, the mesh origin on its saddle, the clip carries the body
	// over (hands on the grips, the right leg over the saddle, sitting, the feet onto the pedals); then the riding pose.
	W->GetCharacterMovement()->StopMovementImmediately();
	W->GetCharacterMovement()->DisableMovement();
	W->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	// The body's own collision off too: the leg going over the saddle would push the moped it is attached to (and the
	// moped the body, and so on: it flew off). Back with the profile on foot (BackOnFoot) or as a ragdoll.
	W->GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	W->AttachToComponent(C->GetMesh(), FAttachmentTransformRules::KeepWorldTransform);
	W->GetRootComponent()->SetRelativeLocationAndRotation(SeatFor(C), FRotator::ZeroRotator);
	// Standing on the road beside it until the right foot is over (frame 40 of 30 fps), sitting by frame 63
	// (Research/Mazzarino80/Blender/m80_motorino_gioco.py, mount_keys).
	ClipLift = GroundBeside(C);
	ClipLiftWindow = FVector2D(1.33f, 2.1f);
	bClipLiftIn = false;
	PlayWithRoot(Clip, From, -1.f, [this]()
	{
		ClipLift = 0.f;
		if (ACharacter* Rider = Walker.Get())
		{
			Rider->GetMesh()->SetRelativeLocation(MeshRelative.GetLocation());
		}
		FinishGetIn();
		PhaseTime = SlideInTime;
	});
	return true;
}

float AM80PlayerController::GroundBeside(const AM80Car* C) const
{
	// The road where the rider stands to get on, against the moped's own ground there (its wheels' plane): a kerb, a slope.
	const FVector Plane = C->GetActorTransform().TransformPosition(FVector(C->DoorOffset.X, C->DoorOffset.Y, 0.f));
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(M80GroundBeside), false, C);
	Params.AddIgnoredActor(Walker.Get());
	if (GetWorld()->LineTraceSingleByChannel(Hit, Plane + FVector(0, 0, 60.f), Plane - FVector(0, 0, 80.f), ECC_Visibility, Params))
	{
		return FMath::Clamp(float(Hit.ImpactPoint.Z - Plane.Z), -40.f, 40.f);
	}
	return 0.f;
}

bool AM80PlayerController::GetOffAstride(AM80Car* C)
{
	ACharacter* W = Walker.Get();
	UAnimSequence* Clip = Cast<UAnimSequence>(C->DismountClip.LoadSynchronous());
	if (!W || !Clip || !W->IsAttachedTo(C))
	{
		return false;
	}
	// Still on the moped: the feet down, standing astride, the right leg back over the saddle, standing beside it on the
	// left; then walking from there.
	State = EM80PlayerState::GettingOut;
	Possess(W);
	// Possessing turns the walking back on: it would move the capsule (still on the saddle) away while the clip plays.
	W->GetCharacterMovement()->StopMovementImmediately();
	W->GetCharacterMovement()->DisableMovement();
	SetViewTargetWithBlend(W, 0.6f, VTBlend_EaseInOut, 2.f);
	SetControlRotation(FRotator(-10.f, C->GetActorRotation().Yaw, 0));
	SetIgnoreLookInput(false);
	SetIgnoreMoveInput(true);
	// The feet back on the road beside it from standing astride (frame 22) to the leg over (frame 44).
	ClipLift = GroundBeside(C);
	ClipLiftWindow = FVector2D(0.73f, 1.47f);
	bClipLiftIn = true;
	PlayWithRoot(Clip, 0.f, -1.f, [this]()
	{
		ACharacter* Rider = Walker.Get();
		const AM80Car* Moped = Car.Get();
		if (Rider && Moped)
		{
			const float Half = Rider->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
			const FVector Stand = Moped->GetActorTransform().TransformPosition(FVector(Moped->DoorOffset.X, Moped->DoorOffset.Y, 0.f))
				+ FVector(0.f, 0.f, ClipLift + Half + 2.f);
			ClipLift = 0.f;
			Rider->DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
			Rider->SetActorLocationAndRotation(Stand, FRotator(0.f, Moped->GetActorRotation().Yaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
		}
		else if (Rider)
		{
			Rider->DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
		}
		Car.Reset();
		BackOnFoot();
	});
	return true;
}

bool AM80PlayerController::ActsCar(const AM80Car* C) const
{
	return C && !C->bCart && C->RidePose.IsNull() && C->GetMesh() && C->GetMesh()->DoesSocketExist(TEXT("Wheel_FL"));
}

FVector AM80PlayerController::EnterStart(const AM80Car* C) const
{
	// The clip from the door to the seat (0.9-3.15 s) walks the body towards the car's right and turns it to its
	// front: it starts that far from the seat, facing the car.
	const ACharacter* W = Walker.Get();
	UAnimSequence* In = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/Mazzarino80/Personaggi/Animazioni/A_M80_Folla_Sale.A_M80_Folla_Sale"), nullptr, LOAD_NoWarn);
	const FVector Seat = C->GetMesh()->GetComponentTransform().TransformPosition(C->SeatOffset);
	if (!W || !In)
	{
		return DoorWorld(C);
	}
	const FTransform D = In->ExtractRootMotionFromRange(0.9f, 3.15f, FAnimExtractContext());
	FVector Travel = MeshRelative.TransformVector(D.GetTranslation());
	Travel.Z = 0.f;
	FVector Start = Seat - FRotator(0.f, C->GetActorRotation().Yaw + 90.f, 0.f).RotateVector(Travel);
	Start.Z = W->GetActorLocation().Z;
	return Start;
}

void AM80PlayerController::PlayWithRoot(UAnimSequence* Clip, float From, float To, TFunction<void()> Then)
{
	ACharacter* W = Walker.Get();
	if (!W || !Clip)
	{
		if (Then)
		{
			Then();
		}
		return;
	}
	ClipNow = Clip;
	ClipTo = To < 0.f ? Clip->GetPlayLength() - 0.01f : FMath::Min(To, Clip->GetPlayLength() - 0.01f);
	ClipTime = From;
	ClipThen = MoveTemp(Then);
	W->GetMesh()->PlayAnimation(Clip, false);
	if (UAnimSingleNodeInstance* S = W->GetMesh()->GetSingleNodeInstance())
	{
		S->SetPlayRate(0.f);
		S->SetPosition(From, false);
	}
}

void AM80PlayerController::TickClip(float DeltaTime)
{
	ACharacter* W = Walker.Get();
	if (!ClipNow || !W)
	{
		return;
	}
	const float T0 = ClipTime;
	ClipTime = FMath::Min(ClipTime + DeltaTime, ClipTo);
	if (!W->GetAttachParentActor())
	{
		// The character follows the clip's root (the clips' root is locked in the pose: the body stays on the capsule).
		const FTransform D = ClipNow->ExtractRootMotionFromRange(T0, ClipTime, FAnimExtractContext());
		FVector Move = W->GetMesh()->GetComponentTransform().TransformVector(D.GetTranslation());
		Move.Z = 0.f;
		W->AddActorWorldOffset(Move, false);
		const float Yaw = D.GetRotation().Rotator().Yaw;
		if (!FMath::IsNearlyZero(Yaw))
		{
			W->AddActorWorldRotation(FRotator(0.f, Yaw, 0.f));
		}
	}
	if (UAnimSingleNodeInstance* S = W->GetMesh()->GetSingleNodeInstance())
	{
		S->SetPosition(ClipTime, false);
	}
	if (!FMath::IsNearlyZero(ClipLift))
	{
		const float A = FMath::SmoothStep(float(ClipLiftWindow.X), float(ClipLiftWindow.Y), ClipTime);
		W->GetMesh()->SetRelativeLocation(MeshRelative.GetLocation() + FVector(0.f, 0.f, ClipLift * (bClipLiftIn ? A : 1.f - A)));
	}
	if (ClipDrop > 0.f)
	{
		const float Up = FMath::Clamp((ClipTime - 0.6f) / 1.8f, 0.f, 1.f);
		W->GetMesh()->SetRelativeLocation(MeshRelative.GetLocation() - FVector(0.f, 0.f, ClipDrop * (1.f - Up)));
	}
	if (ClipTime >= ClipTo)
	{
		ClipNow = nullptr;
		TFunction<void()> Then = MoveTemp(ClipThen);
		ClipThen = nullptr;
		if (Then)
		{
			Then();
		}
	}
}

void AM80PlayerController::BackOnFoot()
{
	ACharacter* W = Walker.Get();
	if (!W)
	{
		return;
	}
	W->GetMesh()->SetRelativeTransform(MeshRelative);
	W->GetMesh()->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	W->GetMesh()->SetCollisionProfileName(MeshProfile);
	W->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	W->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
	if (UM80OverlayAnimInstance* O = Overlay.Get())
	{
		O->bEnabled = true;
	}
	ResetIgnoreMoveInput();
	State = EM80PlayerState::OnFoot;
}

AActor* AM80PlayerController::FindChairInReach() const
{
	const ACharacter* W = Walker.Get();
	if (!W)
	{
		return nullptr;
	}
	AActor* Best = nullptr;
	float BestDist = 160.f;
	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
	{
		if (!It->ActorHasTag(TEXT("M80Sedia")))
		{
			continue;
		}
		const float Dist = FVector::Dist2D(It->GetActorLocation(), W->GetActorLocation());
		if (Dist < BestDist && AM80Pedone::SediaLibera(*It) && FMath::Abs(It->GetActorLocation().Z - W->GetActorLocation().Z) < 200.f)
		{
			Best = *It;
			BestDist = Dist;
		}
	}
	return Best;
}

void AM80PlayerController::SitDown(AActor* OnChair)
{
	ACharacter* W = Walker.Get();
	UAnimSequence* Down = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/Mazzarino80/Personaggi/Animazioni/A_M80_Folla_Siediti.A_M80_Folla_Siediti"), nullptr, LOAD_NoWarn);
	if (!W || !OnChair || !Down)
	{
		return;
	}
	Chair = OnChair;
	State = EM80PlayerState::Sitting;
	bFireHeld = false;
	SetIgnoreMoveInput(true);
	if (UM80OverlayAnimInstance* O = Overlay.Get())
	{
		O->bEnabled = false;
	}
	if (UM80WeaponInventory* Inv = GetInventory())
	{
		Inv->HideWeapon();
	}
	// In front of the chair, back to it: sitting down steps back onto the seat.
	W->GetCharacterMovement()->StopMovementImmediately();
	W->GetCharacterMovement()->DisableMovement();
	W->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	AM80Pedone::TieniSedia(OnChair, true);
	W->SetActorLocationAndRotation(AM80Pedone::DoveSedersi(OnChair, W, Down, 2.2f), FRotator(0.f, OnChair->GetActorRotation().Yaw, 0.f),
		false, nullptr, ETeleportType::TeleportPhysics);
	PlayWithRoot(Down, 0.f, 2.2f, [this]()
	{
		if (ACharacter* Me = Walker.Get())
		{
			if (UAnimSequence* Sit = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/Mazzarino80/Personaggi/Animazioni/A_M80_Folla_Seduto.A_M80_Folla_Seduto"), nullptr, LOAD_NoWarn))
			{
				Me->GetMesh()->PlayAnimation(Sit, true);
			}
		}
		ShowHint(TEXT("E: alzati"));
	});
}

void AM80PlayerController::StandUp()
{
	UAnimSequence* Up = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/Mazzarino80/Personaggi/Animazioni/A_M80_Folla_Alzati.A_M80_Folla_Alzati"), nullptr, LOAD_NoWarn);
	PlayWithRoot(Up, 0.f, 2.2f, [this]()
	{
		AM80Pedone::TieniSedia(Chair.Get(), false);
		Chair.Reset();
		BackOnFoot();
	});
}
