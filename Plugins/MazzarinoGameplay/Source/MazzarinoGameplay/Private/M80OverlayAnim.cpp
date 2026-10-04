#include "M80OverlayAnim.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/Character.h"
#include "TwoBoneIK.h"

namespace
{
// Component space of the UEFN mannequin: the character looks along +Y, +X is its left, +Z up.
const FVector CSForward(0.f, 1.f, 0.f);
const FVector CSLeft(1.f, 0.f, 0.f);
const FVector CSUp(0.f, 0.f, 1.f);

float Bump(float X)
{
	return FMath::Sin(PI * FMath::Clamp(X, 0.f, 1.f));
}
}

// ---------------------------------------------------------------------------------------------
// Anim instance

UM80OverlayAnimInstance* UM80OverlayAnimInstance::Install(ACharacter* Character)
{
	USkeletalMeshComponent* Source = Character ? Character->GetMesh() : nullptr;
	if (!Source || !Source->GetSkeletalMeshAsset())
	{
		return nullptr;
	}
	static const FName Tag(TEXT("M80Overlay"));
	if (USkeletalMeshComponent* Existing = Character->FindComponentByTag<USkeletalMeshComponent>(Tag))
	{
		return Cast<UM80OverlayAnimInstance>(Existing->GetAnimInstance());
	}
	// The MetaHuman body: the leader of the clothes, retargeting from the animation mesh (its parent).
	USkeletalMeshComponent* Body = nullptr;
	TInlineComponentArray<USkeletalMeshComponent*> Meshes(Character);
	for (USkeletalMeshComponent* M : Meshes)
	{
		if (USkeletalMeshComponent* Leader = Cast<USkeletalMeshComponent>(M->LeaderPoseComponent.Get()))
		{
			Body = Leader;
			break;
		}
	}
	if (!Body || Body->GetAttachParent() != Source)
	{
		return nullptr;
	}
	USkeletalMeshComponent* Copy = NewObject<USkeletalMeshComponent>(Character, TEXT("M80Overlay"));
	Copy->ComponentTags.Add(Tag);
	Copy->SetSkeletalMesh(Source->GetSkeletalMeshAsset());
	Copy->SetAnimInstanceClass(UM80OverlayAnimInstance::StaticClass());
	Copy->SetVisibility(false);
	Copy->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Copy->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	Copy->SetupAttachment(Source);
	Copy->RegisterComponent();
	Copy->AddTickPrerequisiteComponent(Source);
	Body->AddTickPrerequisiteComponent(Copy);
	// The body retargets from its attached parent: put it under the copy.
	Body->AttachToComponent(Copy, FAttachmentTransformRules::KeepRelativeTransform);
	// The retarget node keeps the source it found first: a new anim instance looks for the parent again.
	const TSubclassOf<UAnimInstance> BodyAnim = Body->GetAnimClass();
	Body->SetAnimInstanceClass(nullptr);
	Body->SetAnimInstanceClass(BodyAnim);
	return Cast<UM80OverlayAnimInstance>(Copy->GetAnimInstance());
}

// ---------------------------------------------------------------------------------------------
// Proxy

void FM80OverlayProxy::Initialize(UAnimInstance* InAnimInstance)
{
	CopyNode.bUseAttachedParent = true;
	CopyNode.bCopyCurves = true;
	FAnimInstanceProxy::Initialize(InAnimInstance);
	if (const USkeletalMeshComponent* Comp = InAnimInstance->GetSkelMeshComponent())
	{
		Grip = M80GripInHand(Comp->GetSkeletalMeshAsset(), false);
	}
}

void FM80OverlayProxy::PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds)
{
	FAnimInstanceProxy::PreUpdate(InAnimInstance, DeltaSeconds);
	CopyNode.PreUpdate(InAnimInstance);
	UM80OverlayAnimInstance* I = Cast<UM80OverlayAnimInstance>(InAnimInstance);
	const USkeletalMeshComponent* Comp = InAnimInstance->GetSkelMeshComponent();
	if (!I || !Comp)
	{
		return;
	}
	Pose = I->Pose;
	const bool bGun = Pose == EM80WeaponPose::Pistol || Pose == EM80WeaponPose::Rifle;
	I->BlendArms = FMath::FInterpTo(I->BlendArms, (I->bEnabled && bGun) ? 1.f : 0.f, DeltaSeconds, 12.f);
	ArmsWeight = I->BlendArms;
	bAimPoint = I->bAiming;
	AimCS = Comp->GetComponentTransform().InverseTransformPosition(I->AimPoint);
	Recoil = (bGun && I->bEnabled) ? FMath::Clamp(1.f - I->SinceFire / 0.15f, 0.f, 1.f) : 0.f;
	const float Duration = Pose == EM80WeaponPose::Melee ? 0.5f : 0.35f;
	Swing = (!bGun && I->bEnabled && I->SinceFire < Duration) ? I->SinceFire / Duration : -1.f;
	bPunch = Pose == EM80WeaponPose::Unarmed;
}

void FM80OverlayProxy::CacheBones()
{
	FAnimInstanceProxy::CacheBones();
	const FBoneContainer& BC = GetRequiredBones();
	if (!BC.IsValid())
	{
		return;
	}
	const FReferenceSkeleton& Ref = BC.GetReferenceSkeleton();
	Bones.Reset();
	for (int32 i = 0; i < BC.GetCompactPoseNumBones(); ++i)
	{
		const FCompactPoseBoneIndex CI(i);
		Bones.Add(Ref.GetBoneName(BC.MakeMeshPoseIndex(CI).GetInt()), CI);
	}
}

void FM80OverlayProxy::Rotate(FPoseContext& Output, FName Bone, const FVector& CSAxis, float Degrees)
{
	const FCompactPoseBoneIndex* I = Bones.Find(Bone);
	if (!I || FMath::IsNearlyZero(Degrees))
	{
		return;
	}
	FCSPose<FCompactPose> CS;
	CS.InitPose(Output.Pose);
	const FCompactPoseBoneIndex Parent = Output.Pose.GetParentBoneIndex(*I);
	const FQuat ParentRot = Parent.IsValid() ? CS.GetComponentSpaceTransform(Parent).GetRotation() : FQuat::Identity;
	const FVector Axis = ParentRot.UnrotateVector(CSAxis).GetSafeNormal();
	FTransform& Local = Output.Pose[*I];
	Local.SetRotation((FQuat(Axis, FMath::DegreesToRadians(Degrees)) * Local.GetRotation()).GetNormalized());
}

void FM80OverlayProxy::AimArms(FPoseContext& Output)
{
	auto Find = [this](const TCHAR* N) { const FCompactPoseBoneIndex* I = Bones.Find(N); return I ? *I : FCompactPoseBoneIndex(INDEX_NONE); };
	const FCompactPoseBoneIndex UR = Find(TEXT("upperarm_r")), LR = Find(TEXT("lowerarm_r")), HR = Find(TEXT("hand_r"));
	const FCompactPoseBoneIndex UL = Find(TEXT("upperarm_l")), LL = Find(TEXT("lowerarm_l")), HL = Find(TEXT("hand_l"));
	if (!UR.IsValid() || !LR.IsValid() || !HR.IsValid() || !UL.IsValid() || !LL.IsValid() || !HL.IsValid())
	{
		return;
	}
	FCSPose<FCompactPose> CS;
	CS.InitPose(Output.Pose);
	FTransform R[3] = {CS.GetComponentSpaceTransform(UR), CS.GetComponentSpaceTransform(LR), CS.GetComponentSpaceTransform(HR)};
	FTransform L[3] = {CS.GetComponentSpaceTransform(UL), CS.GetComponentSpaceTransform(LL), CS.GetComponentSpaceTransform(HL)};
	const FTransform R0[3] = {R[0], R[1], R[2]};
	const FTransform L0[3] = {L[0], L[1], L[2]};
	const FVector ShoulderR = R[0].GetLocation(), ShoulderL = L[0].GetLocation();
	const FVector Chest = (ShoulderR + ShoulderL) * 0.5f;
	const float ArmLen = (R[1].GetLocation() - R[0].GetLocation()).Size() + (R[2].GetLocation() - R[1].GetLocation()).Size();
	const bool bRifle = Pose == EM80WeaponPose::Rifle;

	// Weapon direction: at the crosshair, or forward and down when just holding it.
	FVector X = bAimPoint ? (AimCS - Chest).GetSafeNormal() : (CSForward - CSUp * (bRifle ? 0.55f : 1.1f)).GetSafeNormal();
	if (X.IsNearlyZero() || (X | CSForward) < -0.2f)
	{
		X = CSForward;
	}
	X = (X + CSUp * 0.35f * Recoil).GetSafeNormal();  // muzzle kick
	const FVector Z = (CSUp - X * (X | CSUp)).GetSafeNormal();
	const FQuat WeaponRot = FRotationMatrix::MakeFromXZ(X, Z).ToQuat();

	// Where the grip sits: the pistol at arm's length in front of the chest (two hands), the lupara
	// with the stock under the right shoulder; held low: closer to the body.
	FVector GripPos;
	FVector SupportLocal;  // left hand, in the weapon's frame (X barrel, Y right, Z up)
	if (bRifle)
	{
		GripPos = ShoulderR + X * (bAimPoint ? 18.f : 28.f) - Z * 8.f + CSLeft * 4.f;
		SupportLocal = FVector(30.f, -1.f, -4.f);
	}
	else
	{
		const float Reach = bAimPoint ? 0.85f : 0.55f;
		GripPos = Chest + X * ArmLen * Reach - Z * 6.f - CSLeft * 3.f;
		SupportLocal = FVector(-1.f, -3.5f, -4.f);
	}
	GripPos -= X * 5.f * Recoil;
	const FTransform WeaponCS(WeaponRot, GripPos);
	// The weapon hangs off the hand by Grip: hand = Grip^-1 applied to the weapon frame.
	const FTransform HandCS = Grip.Inverse() * WeaponCS;
	const FVector SupportPos = WeaponCS.TransformPosition(SupportLocal);

	// Elbows down and out.
	const FVector ElbowR = (ShoulderR + HandCS.GetLocation()) * 0.5f - CSUp * 35.f - CSLeft * 25.f;
	AnimationCore::SolveTwoBoneIK(R[0], R[1], R[2], ElbowR, HandCS.GetLocation(), false, 1.0, 1.0);
	R[2].SetRotation(HandCS.GetRotation());
	const bool bTwoHands = bAimPoint || bRifle;
	if (bTwoHands)
	{
		const FVector ElbowL = (ShoulderL + SupportPos) * 0.5f - CSUp * 35.f + CSLeft * 25.f;
		const FQuat HandLRot = L[2].GetRotation();
		AnimationCore::SolveTwoBoneIK(L[0], L[1], L[2], ElbowL, SupportPos, false, 1.0, 1.0);
		L[2].SetRotation(HandLRot);
	}
	const float W = ArmsWeight;
	auto Blend = [W](const FTransform& A, const FTransform& B)
	{
		FTransform T;
		T.Blend(A, B, W);
		return T;
	};
	TArray<FBoneTransform> Out;
	Out.Add(FBoneTransform(UR, Blend(R0[0], R[0])));
	Out.Add(FBoneTransform(LR, Blend(R0[1], R[1])));
	Out.Add(FBoneTransform(HR, Blend(R0[2], R[2])));
	CS.SafeSetCSBoneTransforms(Out);
	if (bTwoHands)
	{
		Out.Reset();
		Out.Add(FBoneTransform(UL, Blend(L0[0], L[0])));
		Out.Add(FBoneTransform(LL, Blend(L0[1], L[1])));
		Out.Add(FBoneTransform(HL, Blend(L0[2], L[2])));
		CS.SafeSetCSBoneTransforms(Out);
	}
	FCSPose<FCompactPose>::ConvertComponentPosesToLocalPoses(MoveTemp(CS), Output.Pose);
}

bool FM80OverlayProxy::Evaluate(FPoseContext& Output)
{
	FMemMark Mark(FMemStack::Get());
	EvaluateAnimationNode_WithRoot(Output, &CopyNode);
	if (Bones.Num() == 0)
	{
		return true;
	}
	if (ArmsWeight > 0.01f)
	{
		AimArms(Output);
	}
	if (Swing >= 0.f)
	{
		if (bPunch)
		{
			// Jab: right arm forward and straight, a quick turn of the shoulders.
			const float E = Bump(Swing);
			Rotate(Output, TEXT("spine_04"), CSUp, 18.f * E);
			Rotate(Output, TEXT("upperarm_r"), CSLeft, 75.f * E);
			Rotate(Output, TEXT("lowerarm_r"), CSLeft, -35.f * E);
		}
		else
		{
			// Blow: wind up (arm up and back to the right), swing across to the left, recover.
			const float Up = Swing < 0.3f ? Swing / 0.3f : (Swing < 0.75f ? 1.f : 1.f - (Swing - 0.75f) / 0.25f);
			const float Across = Swing < 0.3f ? -Swing / 0.3f : (Swing < 0.7f ? -1.f + 2.4f * (Swing - 0.3f) / 0.4f : 1.4f * (1.f - (Swing - 0.7f) / 0.3f));
			Rotate(Output, TEXT("spine_04"), CSUp, -25.f * Across);
			Rotate(Output, TEXT("upperarm_r"), CSLeft, 95.f * Up);
			Rotate(Output, TEXT("upperarm_r"), CSUp, -50.f * Across);
			Rotate(Output, TEXT("lowerarm_r"), CSLeft, 30.f * Up);
		}
	}
	return true;
}
