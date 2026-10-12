#include "M80Climb.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "MotionWarpingComponent.h"

namespace
{
/** What can be climbed: the world, things that move, physics props and vehicles (not people). */
FCollisionObjectQueryParams ClimbObjects()
{
	FCollisionObjectQueryParams O;
	O.AddObjectTypesToQuery(ECC_WorldStatic);
	O.AddObjectTypesToQuery(ECC_WorldDynamic);
	O.AddObjectTypesToQuery(ECC_PhysicsBody);
	O.AddObjectTypesToQuery(ECC_Vehicle);
	O.AddObjectTypesToQuery(ECC_Destructible);
	return O;
}

// Where the hands rest on a ledge: just behind its front edge, on the top.
// (the hand bone is the wrist: the fingers reach over the edge).
constexpr float HandsBehindEdge = 12.f;
constexpr float HandsAboveTop = 0.f;
// Hands above the feet while hanging (A_M80_Appeso_Laterale): ledges this high are caught from a jump or a fall.
constexpr float HangReach = 220.f;
}

UM80ClimbComponent::UM80ClimbComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PrePhysics;
}

void UM80ClimbComponent::BeginPlay()
{
	Super::BeginPlay();
	if (const ACharacter* C = Owner())
	{
		MeshRelative = C->GetMesh()->GetRelativeTransform();
	}
}

ACharacter* UM80ClimbComponent::Owner() const
{
	return Cast<ACharacter>(GetOwner());
}

bool UM80ClimbComponent::FindLedge(float MinRise, float MaxRise, FM80Ledge& Out) const
{
	const ACharacter* C = Owner();
	if (!C)
	{
		return false;
	}
	const float Half = C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	return FindLedgeFrom(C->GetActorLocation() - FVector(0, 0, Half), C->GetActorForwardVector(), MinRise, MaxRise, Out);
}

bool UM80ClimbComponent::FindLedgeFrom(const FVector& Feet, const FVector& Forward, float MinRise, float MaxRise, FM80Ledge& Out) const
{
	const ACharacter* C = Owner();
	UWorld* W = GetWorld();
	if (!C || !W)
	{
		return false;
	}
	const FVector Fwd = Forward.GetSafeNormal2D();
	const float Radius = C->GetCapsuleComponent()->GetScaledCapsuleRadius();
	const float Half = C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	// Complex collision: house walls and cars (whose simple collision may be missing) as they look.
	FCollisionQueryParams Q(SCENE_QUERY_STAT(M80Climb), true, C);
	const FCollisionObjectQueryParams O = ClimbObjects();   // overlap tests (room for hands)
	// 1) The wall in front, scanned densely (cornices, balcony slabs and sills are a few cm thick): the part that
	// stands out the most, its highest point if several do.
	FHitResult Wall;
	bool bWall = false;
	for (float Z = FMath::Max(25.f, MinRise - 60.f); Z <= MaxRise - 4.f; Z += 8.f)
	{
		const FVector A = Feet + FVector(0, 0, Z);
		FHitResult H;
		if (W->LineTraceSingleByChannel(H, A, A + Fwd * (Radius + 70.f), ECC_Visibility, Q) && !Cast<ACharacter>(H.GetActor()) && FMath::Abs(H.ImpactNormal.Z) < 0.35f
			&& (!bWall || H.Distance <= Wall.Distance + 3.f))
		{
			Wall = H;
			bWall = true;
		}
	}
	if (!bWall)
	{
		Note(TEXT("nessun muro"));
		return false;
	}	const FVector N = FVector(Wall.ImpactNormal.X, Wall.ImpactNormal.Y, 0.f).GetSafeNormal();
	// 2) Its top, from above, just inside the face.
	const FVector In = Wall.ImpactPoint - N * 8.f;
	FHitResult Top;
	if (!W->LineTraceSingleByChannel(Top, FVector(In.X, In.Y, Feet.Z + MaxRise + 40.f), FVector(In.X, In.Y, Feet.Z + MinRise - 20.f), ECC_Visibility, Q)
		|| Top.bStartPenetrating || Top.ImpactNormal.Z < 0.7f)
	{
		Note(FString::Printf(TEXT("cima non trovata (muro a %.0f cm, colpo %d)"), Wall.ImpactPoint.Z - Feet.Z, Top.bBlockingHit ? 1 : 0));
		return false;
	}
	const float Height = Top.ImpactPoint.Z - Feet.Z;
	if (Height < MinRise || Height > MaxRise)
	{
		Note(FString::Printf(TEXT("cima a %.0f cm, fuori da %.0f-%.0f"), Height, MinRise, MaxRise));
		return false;
	}
	// 3) The front edge: the face just under the top.
	FVector Edge(Wall.ImpactPoint.X, Wall.ImpactPoint.Y, Top.ImpactPoint.Z);
	FHitResult Face;
	if (W->LineTraceSingleByChannel(Face, Edge + N * 60.f - FVector(0, 0, 5.f), Edge - N * 30.f - FVector(0, 0, 5.f), ECC_Visibility, Q))
	{
		Edge.X = Face.ImpactPoint.X;
		Edge.Y = Face.ImpactPoint.Y;
	}
	// 4) Room for the hands (nothing right over the edge).
	if (W->OverlapAnyTestByObjectType(Edge - N * HandsBehindEdge + FVector(0, 0, 14.f), FQuat::Identity, O, FCollisionShape::MakeSphere(8.f), Q))
	{
		Note(TEXT("niente spazio per le mani"));
		return false;
	}
	Out.Edge = Edge;
	Out.Normal = N;
	Out.Height = Height;
	Out.Actor = Top.GetActor();
	// 5) Room to stand on the top: the floor a step in from the edge (a car roof bulges up), the body standing on it.
	const FVector Above = Top.ImpactPoint - N * (Radius + 15.f);
	FHitResult Floor;
	const bool bFloor = W->LineTraceSingleByChannel(Floor, Above + FVector(0, 0, 40.f), Above - FVector(0, 0, 30.f), ECC_Visibility, Q)
		&& !Floor.bStartPenetrating;
	const FVector Stand = (bFloor ? Floor.ImpactPoint : Above) + FVector(0, 0, Half + 3.f);
	const bool bFree = !W->OverlapAnyTestByChannel(Stand, FQuat::Identity, ECC_Pawn, FCollisionShape::MakeCapsule(Radius, Half), Q);
	Out.bRoomOnTop = bFree && bFloor && Floor.ImpactNormal.Z > 0.7f && FMath::Abs(Floor.ImpactPoint.Z - Top.ImpactPoint.Z) < 25.f;
	if (!Out.bRoomOnTop)
	{
		Note(FString::Printf(TEXT("bordo a %.0f cm senza spazio sopra (libero %d, pavimento %d, normale %.2f, dislivello %.0f)"), Height, bFree ? 1 : 0,
			bFloor ? 1 : 0, Floor.ImpactNormal.Z, Floor.ImpactPoint.Z - Top.ImpactPoint.Z));
	}
	return true;
}

FVector UM80ClimbComponent::HoldPoint(const FM80Ledge& L) const
{
	return L.Edge - L.Normal * HandsBehindEdge + FVector(0, 0, HandsAboveTop);
}

bool UM80ClimbComponent::JumpPressed()
{
	ACharacter* C = Owner();
	if (!C)
	{
		return false;
	}
	UCharacterMovementComponent* M = C->GetCharacterMovement();
	switch (State)
	{
	case EM80ClimbState::None:
	{
		if (!M->IsMovingOnGround())
		{
			return false;
		}
		FM80Ledge L;
		if (FindLedge(50.f, 260.f, L) && L.bRoomOnTop)
		{
			C->StopJumping();
			C->ResetJumpState();
			StartMantle(L);
			return true;
		}
		if (FindLedge(150.f, MaxGrabHeight, L))
		{
			// A jump just high enough for the hands to reach the edge; the grab happens near the top of the jump.
			const float Rise = FMath::Max(40.f, L.Height - HangReach + 15.f);
			const float Vz = FMath::Sqrt(2.f * FMath::Abs(M->GetGravityZ()) * Rise) * 1.05f;
			C->StopJumping();
			C->ResetJumpState();
			C->LaunchCharacter(FVector(0, 0, Vz) - L.Normal * 60.f, true, true);
			GrabCooldown = 0.f;
			Note(FString::Printf(TEXT("salto verso il bordo a %.0f cm: %.0f cm/s"), L.Height, Vz));
			return true;
		}
		return false;
	}
	case EM80ClimbState::Hanging:
	case EM80ClimbState::Shimmying:
	{
		if (FVector::DotProduct(Input(), Ledge.Normal) > 0.5f)
		{
			// Away from the wall: a jump backwards.
			Release(Ledge.Normal * 420.f + FVector(0, 0, 420.f));
			return true;
		}
		if (Ledge.bRoomOnTop)
		{
			StartClimbUp();
			return true;
		}
		// A ledge above (the next window sill, a balcony): jump up to it.
		const FVector Feet = HoldPoint(Ledge) - FVector(0, 0, HangReach);
		FM80Ledge Up;
		if (FindLedgeFrom(Feet, -Ledge.Normal, HangReach + 30.f, HangReach + 170.f, Up))
		{
			const float Rise = Up.Height - HangReach + 15.f;
			Release(FVector(0, 0, FMath::Sqrt(2.f * FMath::Abs(M->GetGravityZ()) * Rise) * 1.05f) - Ledge.Normal * 30.f);
			GrabCooldown = 0.12f;
		}
		return true;
	}
	default:
		return true;
	}
}

void UM80ClimbComponent::Drop()
{
	if (State == EM80ClimbState::Hanging || State == EM80ClimbState::Shimmying)
	{
		Release(Ledge.Normal * 80.f);
		GrabCooldown = 0.5f;
	}
}

void UM80ClimbComponent::StartMantle(const FM80Ledge& L)
{
	ACharacter* C = Owner();
	UAnimMontage* M = (L.Height < 160.f ? MantleMontage : ClimbMontage).LoadSynchronous();
	UMotionWarpingComponent* MW = C ? C->FindComponentByClass<UMotionWarpingComponent>() : nullptr;
	UAnimInstance* AI = C ? C->GetMesh()->GetAnimInstance() : nullptr;
	if (!M || !MW || !AI)
	{
		return;
	}
	const FRotator Face(0.f, (-L.Normal).Rotation().Yaw, 0.f);
	C->SetActorRotation(Face);
	MW->AddOrUpdateWarpTargetFromLocationAndRotation(TEXT("FrontLedge"), L.Edge, Face);
	C->GetCharacterMovement()->StopMovementImmediately();
	C->GetCharacterMovement()->SetMovementMode(MOVE_Flying);
	if (AActor* A = L.Actor.Get())
	{
		C->GetCapsuleComponent()->IgnoreActorWhenMoving(A, true);
	}
	AI->Montage_Play(M, 1.f);
	Ledge = L;
	Montage = M;
	MantleTime = 0.f;
	State = EM80ClimbState::Mantling;
}

void UM80ClimbComponent::EndMantle()
{
	ACharacter* C = Owner();
	if (C)
	{
		if (AActor* A = Ledge.Actor.Get())
		{
			C->GetCapsuleComponent()->IgnoreActorWhenMoving(A, false);
		}
		C->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
	}
	State = EM80ClimbState::None;
}

void UM80ClimbComponent::PlayClip(UAnimSequence* InClip, float Time, float Rate)
{
	ACharacter* C = Owner();
	if (!C || !InClip)
	{
		return;
	}
	USkeletalMeshComponent* Mesh = C->GetMesh();
	if (Clip.Get() != InClip || Mesh->GetAnimationMode() != EAnimationMode::AnimationSingleNode)
	{
		Mesh->PlayAnimation(InClip, false);
	}
	Mesh->SetPlayRate(0.f);
	Mesh->SetPosition(Time, false);
	Mesh->TickAnimation(0.f, false);
	Mesh->RefreshBoneTransforms();
	Clip = InClip;
	ClipLength = InClip->GetPlayLength();
	ClipRate = Rate;
	ClipTime = Time;
}

FVector UM80ClimbComponent::HandsWorld() const
{
	const ACharacter* C = Owner();
	const USkeletalMeshComponent* Mesh = C ? C->GetMesh() : nullptr;
	return Mesh ? (Mesh->GetSocketLocation(TEXT("hand_l")) + Mesh->GetSocketLocation(TEXT("hand_r"))) * 0.5f : FVector::ZeroVector;
}

void UM80ClimbComponent::AlignHandsTo(const FVector& Target)
{
	if (ACharacter* C = Owner())
	{
		C->GetMesh()->AddWorldOffset(Target - HandsWorld());
	}
}

void UM80ClimbComponent::FollowBody()
{
	// The capsule goes with the body; the body (the mesh) stays where the clip has put it.
	ACharacter* C = Owner();
	if (!C)
	{
		return;
	}
	USkeletalMeshComponent* Mesh = C->GetMesh();
	const FVector MeshWorld = Mesh->GetComponentLocation();
	C->SetActorLocation(Mesh->GetSocketLocation(TEXT("pelvis")) + BodyToCapsule, false, nullptr, ETeleportType::TeleportPhysics);
	Mesh->SetWorldLocation(MeshWorld);
}

void UM80ClimbComponent::KeepOffWall(float DeltaTime, bool bCheckWall)
{
	// The braced hang clip plants the feet on a wall of its own; the wall under a real ledge may stand further out
	// (a sill, a plain wall under a thin cornice): the body swings out about the hands until legs and head are off it.
	ACharacter* C = Owner();
	UWorld* W = GetWorld();
	if (!C || !W)
	{
		return;
	}
	USkeletalMeshComponent* Mesh = C->GetMesh();
	const FVector Out = Ledge.Normal;
	const FVector Pivot = HandsWorld();
	FCollisionQueryParams Q(SCENE_QUERY_STAT(M80ClimbWall), true, C);
	float Need = -90.f;   // degrees more to swing out (negative: it may swing back in)
	bool bWall = false;
	if (bCheckWall)
	{
		for (const TCHAR* Bone : {TEXT("ball_l"), TEXT("ball_r"), TEXT("foot_l"), TEXT("foot_r"), TEXT("calf_l"), TEXT("calf_r"), TEXT("pelvis"),
				 TEXT("spine_03"), TEXT("head")})
		{
			const FVector P = Mesh->GetSocketLocation(Bone);
			const float Below = Pivot.Z - P.Z;
			FHitResult H;
			if (Below > 30.f && W->LineTraceSingleByChannel(H, P + Out * 60.f, P - Out * 40.f, ECC_Visibility, Q) && !H.bStartPenetrating)
			{
				// > 0: inside the wall (keeping 4 cm off it).
				const float Depth = FVector::DotProduct(H.ImpactPoint - P, Out) + 4.f;
				Need = FMath::Max(Need, FMath::RadiansToDegrees(FMath::Atan2(Depth, Below)));
				bWall = true;
			}
		}
	}
	const float Want = bWall ? FMath::Clamp(Lean + Need, 0.f, 35.f) : 0.f;
	// Out at once (never seen in the wall), back in slowly.
	const float NewLean = Want > Lean ? Want : FMath::FInterpTo(Lean, Want, DeltaTime, 4.f);
	if (FMath::Abs(NewLean - Lean) < 0.01f)
	{
		return;
	}
	const FVector Right = FVector::CrossProduct(FVector::UpVector, -Out);
	const float Sign = FVector::DotProduct(FQuat(Right, 0.1f).RotateVector(-FVector::UpVector), Out) > 0.f ? 1.f : -1.f;
	const FQuat Swing(Right, Sign * FMath::DegreesToRadians(NewLean - Lean));
	const FTransform T = Mesh->GetComponentTransform();
	Mesh->SetWorldLocationAndRotation(Pivot + Swing.RotateVector(T.GetLocation() - Pivot), Swing * T.GetRotation());
	Lean = NewLean;
}

bool UM80ClimbComponent::Grab(const FM80Ledge& L)
{
	ACharacter* C = Owner();
	UAnimSequence* Hang = HangAnim.LoadSynchronous();
	if (!C || !Hang)
	{
		return false;
	}
	if (State == EM80ClimbState::None)
	{
		MeshRelative = C->GetMesh()->GetRelativeTransform();
		// The animation mesh is hidden behind the visible body: make it pose every frame, seen or not.
		MeshTickOption = uint8(C->GetMesh()->VisibilityBasedAnimTickOption);
		C->GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
		bMeshURO = C->GetMesh()->bEnableUpdateRateOptimizations;
		C->GetMesh()->bEnableUpdateRateOptimizations = false;
	}
	UCharacterMovementComponent* M = C->GetCharacterMovement();
	M->StopMovementImmediately();
	M->SetMovementMode(MOVE_None);
	C->SetActorRotation(FRotator(0.f, (-L.Normal).Rotation().Yaw, 0.f));
	C->GetMesh()->SetRelativeTransform(MeshRelative);
	Lean = 0.f;
	PlayClip(Hang, 0.f, 0.f);
	Ledge = L;
	AlignHandsTo(HoldPoint(L));
	KeepOffWall(0.f, true);
	// The capsule hangs with the body, a little out from the wall so it never sits in it.
	BodyToCapsule = L.Normal * 12.f;
	FollowBody();
	State = EM80ClimbState::Hanging;
	return true;
}

void UM80ClimbComponent::TickHang(float DeltaTime)
{
	ACharacter* C = Owner();
	UAnimSequence* Hang = HangAnim.LoadSynchronous();
	if (!C || !Hang)
	{
		return;
	}
	USkeletalMeshComponent* Mesh = C->GetMesh();
	const FVector In = Input();
	const FVector Facing = -Ledge.Normal;
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Facing);
	const float Side = FVector::DotProduct(In, Right);
	const FString Why = Debug;
	const float Dir = Side > 0.3f ? 1.f : (Side < -0.3f ? -1.f : 0.f);
	Note(FString::Printf(TEXT("appeso: input %.2f,%.2f lato %.2f stato %d clip %.2f/%.2f fuori dal muro %.0f gradi"), In.X, In.Y, Side, int32(State),
		Mesh->GetPosition(), ClipLength, Lean));

	if (State == EM80ClimbState::Hanging)
	{
		if (Dir == 0.f)
		{
			KeepOffWall(DeltaTime, true);
			FollowBody();
			return;
		}
		// Is there ledge on that side?
		FM80Ledge Next;
		const FVector Feet = HoldPoint(Ledge) - FVector(0, 0, HangReach - HandsAboveTop) + Right * Dir * 45.f + Ledge.Normal * 40.f;
		if (!FindLedgeFrom(Feet, Facing, HangReach - 25.f, HangReach + 25.f, Next))
		{
			Note(FString::Printf(TEXT("laterale %.2f: bordo finito (%s)"), Side, *Debug));
			return;
		}
		// The clip shuffles to the right; played backwards (from its end, where the body stands further right) it
		// goes left: the body stays where it is.
		const FVector Before = HandsWorld();
		PlayClip(Hang, Dir > 0.f ? 0.f : ClipLength * 0.999f, Dir * ShimmySpeed);
		Mesh->AddWorldOffset(Before - HandsWorld());
		State = EM80ClimbState::Shimmying;
		return;
	}

	// Shimmying: at the end of each cycle the clip starts again where the hands have got to.
	ClipTime = FMath::Clamp(ClipTime + DeltaTime * ClipRate, 0.f, ClipLength);
	Mesh->SetPosition(ClipTime, false);
	const bool bEnd = ClipRate > 0.f ? ClipTime >= ClipLength - 0.02f : ClipTime <= 0.02f;
	if (bEnd)
	{
		const FVector Before = HandsWorld();
		const bool bGoOn = Dir != 0.f && FMath::Sign(Dir) == FMath::Sign(ClipRate);
		FM80Ledge Next;
		const FVector Feet = HoldPoint(Ledge) - FVector(0, 0, HangReach - HandsAboveTop) + Right * FMath::Sign(ClipRate) * 45.f + Ledge.Normal * 40.f;
		const bool bMore = bGoOn && FindLedgeFrom(Feet, Facing, HangReach - 25.f, HangReach + 25.f, Next);
		if (bMore)
		{
			PlayClip(Hang, ClipRate > 0.f ? 0.f : ClipLength * 0.999f, ClipRate);
		}
		else
		{
			PlayClip(Hang, 0.f, 0.f);
			State = EM80ClimbState::Hanging;
		}
		Mesh->AddWorldOffset(Before - HandsWorld());
		// Keep the hands on the ledge where it is now (walls are not straight).
		FM80Ledge Here;
		const FVector HereFeet = FVector(HandsWorld().X, HandsWorld().Y, HoldPoint(Ledge).Z) - FVector(0, 0, HangReach - HandsAboveTop) + Ledge.Normal * 40.f;
		if (FindLedgeFrom(HereFeet, Facing, HangReach - 25.f, HangReach + 25.f, Here))
		{
			Ledge = Here;
			C->SetActorRotation(FRotator(0.f, (-Here.Normal).Rotation().Yaw, 0.f));
			AlignHandsTo(HoldPoint(Here));
		}
	}
	KeepOffWall(DeltaTime, true);
	FollowBody();
}

void UM80ClimbComponent::StartClimbUp()
{
	UAnimSequence* Up = ClimbUpAnim.LoadSynchronous();
	if (!Up)
	{
		return;
	}
	PlayClip(Up, 0.f, 1.f);
	AlignHandsTo(HoldPoint(Ledge));
	State = EM80ClimbState::ClimbingUp;
}

void UM80ClimbComponent::FinishClimbUp()
{
	ACharacter* C = Owner();
	if (!C)
	{
		return;
	}
	const float Radius = C->GetCapsuleComponent()->GetScaledCapsuleRadius();
	const float Half = C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	FVector Stand = Ledge.Edge - Ledge.Normal * (Radius + 15.f);
	Stand.Z = Ledge.Edge.Z + Half + 2.f;
	RestoreBody();
	C->SetActorLocation(Stand, false, nullptr, ETeleportType::TeleportPhysics);
	C->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
	Note(FString::Printf(TEXT("salita finita: piedi a %.0f, bordo a %.0f"), C->GetActorLocation().Z - Half, Ledge.Edge.Z));
	State = EM80ClimbState::None;
}

void UM80ClimbComponent::RestoreBody()
{
	ACharacter* C = Owner();
	if (!C)
	{
		return;
	}
	USkeletalMeshComponent* Mesh = C->GetMesh();
	Mesh->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	Mesh->SetRelativeTransform(MeshRelative);
	Lean = 0.f;
	Mesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption(MeshTickOption);
	Mesh->bEnableUpdateRateOptimizations = bMeshURO;
	Clip.Reset();
}

void UM80ClimbComponent::Release(const FVector& Push)
{
	ACharacter* C = Owner();
	if (!C)
	{
		return;
	}
	// Out from the wall before falling, so the capsule does not start inside it.
	const FVector At = C->GetActorLocation() + Ledge.Normal * 15.f;
	RestoreBody();
	C->SetActorLocation(At, false, nullptr, ETeleportType::TeleportPhysics);
	C->GetCharacterMovement()->SetMovementMode(MOVE_Falling);
	C->LaunchCharacter(Push, true, true);
	State = EM80ClimbState::None;
	GrabCooldown = FMath::Max(GrabCooldown, 0.25f);
}

void UM80ClimbComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	// A hitch (loading, a screenshot) must not throw the clips forward.
	DeltaTime = FMath::Min(DeltaTime, 0.05f);
	ACharacter* C = Owner();
	if (!C)
	{
		return;
	}
	GrabCooldown -= DeltaTime;
	ForcedTime -= DeltaTime;
	switch (State)
	{
	case EM80ClimbState::None:
	{
		// Catch a ledge when the hands come level with it in a jump or a fall.
		UCharacterMovementComponent* M = C->GetCharacterMovement();
		if (GrabCooldown > 0.f || !M->IsFalling() || M->Velocity.Z > 250.f)
		{
			return;
		}
		const float Half = C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
		const FVector Feet = C->GetActorLocation() - FVector(0, 0, Half);
		FVector Fwd = M->Velocity.GetSafeNormal2D();
		if (Fwd.IsNearlyZero() || FVector::DotProduct(Fwd, C->GetActorForwardVector()) < 0.f)
		{
			Fwd = C->GetActorForwardVector();
		}
		FM80Ledge L;
		if (FindLedgeFrom(Feet, Fwd, HangReach - 45.f, HangReach + 25.f, L))
		{
			Grab(L);
		}
		return;
	}
	case EM80ClimbState::Mantling:
	{
		MantleTime += DeltaTime;
		const UAnimInstance* AI = C->GetMesh()->GetAnimInstance();
		const UAnimMontage* M = Montage.Get();
		if (!AI || !M || !AI->Montage_IsPlaying(M) || MantleTime > M->GetPlayLength() + 0.5f)
		{
			EndMantle();
		}
		return;
	}
	case EM80ClimbState::Hanging:
	case EM80ClimbState::Shimmying:
		TickHang(DeltaTime);
		return;
	case EM80ClimbState::ClimbingUp:
		Note(FString::Printf(TEXT("salita: clip %.2f/%.2f"), C->GetMesh()->GetPosition(), ClipLength));
		ClipTime = FMath::Clamp(ClipTime + DeltaTime * ClipRate, 0.f, ClipLength);
		C->GetMesh()->SetPosition(ClipTime, false);
		KeepOffWall(DeltaTime, false);   // upright again while climbing over
		FollowBody();
		if (ClipTime >= ClipLength - 0.03f)
		{
			FinishClimbUp();
		}
		return;
	default:
		return;
	}
}
