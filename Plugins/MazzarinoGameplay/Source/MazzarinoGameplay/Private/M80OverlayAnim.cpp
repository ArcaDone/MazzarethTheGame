#include "M80OverlayAnim.h"
#include "M80BodyAnim.h"
#include "Retargeter/IKRetargeter.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimationPoseData.h"
#include "Animation/AttributesRuntime.h"
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
	// The retarget node keeps the source it found first: a new anim instance looks for the parent again. Our own: the same
	// retarget (the blueprint's retargeter), then the riding IK on the body's own bones (UM80BodyAnimInstance).
	UIKRetargeter* Retargeter = UM80BodyAnimInstance::FindRetargeter(Body);
	const TSubclassOf<UAnimInstance> BodyAnim = Body->GetAnimClass();
	Body->SetAnimInstanceClass(nullptr);
	if (Retargeter)
	{
		UM80BodyAnimInstance::NextRetargeter = Retargeter;
		Body->SetAnimInstanceClass(UM80BodyAnimInstance::StaticClass());
		UM80BodyAnimInstance::NextRetargeter = nullptr;
		UE_LOG(LogTemp, Log, TEXT("M80 body: retarget with %s"), *Retargeter->GetName());
	}
	else
	{
		Body->SetAnimInstanceClass(BodyAnim);
	}
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
	auto Load = [](const TCHAR* Name)
	{
		return LoadObject<UAnimSequence>(nullptr, *FString::Printf(TEXT("/Game/Mazzarino80/Player/Anim/%s.%s"), Name, Name), nullptr, LOAD_NoWarn);
	};
	PistolAim = Load(TEXT("A_M80_Pistola_Mira_Sweep"));
	PistolHold = Load(TEXT("A_M80_Pistola_Pose"));
	RifleAim = Load(TEXT("A_M80_Fucile_Mira_Sweep"));
	RifleHold = Load(TEXT("A_M80_Fucile_Pose"));
	Punches = Load(TEXT("A_M80_Pugni_Combo"));
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
	if (bAimPoint)
	{
		// From the chest (about 1.45 m above the feet), in the mannequin's frame (+Y forward, +X left).
		const FVector D = AimCS - FVector(0.f, 0.f, 145.f);
		AimPitch = FMath::RadiansToDegrees(FMath::Atan2(D.Z, FVector2D(D.X, D.Y).Size()));
		AimYaw = FMath::RadiansToDegrees(FMath::Atan2(D.X, D.Y));
	}
	else
	{
		AimPitch = AimYaw = 0.f;
	}
	Recoil = (bGun && I->bEnabled) ? FMath::Clamp(1.f - I->SinceFire / 0.15f, 0.f, 1.f) : 0.f;
	const float Duration = 0.5f;   // a blow of the bat or knife, the longest blow of the fists
	Swing = (!bGun && I->bEnabled && I->SinceFire < Duration) ? I->SinceFire / Duration : -1.f;
	bPunch = Pose == EM80WeaponPose::Unarmed;
	PunchStep = I->ComboStep;
	PunchTime = I->bEnabled ? I->SinceFire : 99.f;
	bGripLedge = I->bClimbing;
	RideWeight = I->RideWeight;
	bRideFeet = I->bRideFeet;
	RideLean = I->RideLean;
	bRideSteadyJoints = I->bRideSteadyJoints;
	RideFists = I->RideFists;
	const FTransform& CT = Comp->GetComponentTransform();
	for (int32 k = 0; k < 2; ++k)
	{
		// This copy sits on the animation mesh with no offset: its space is the mesh's.
		RideHandCS[k] = I->bRideLocal ? I->RideHandLocal[k] : CT.InverseTransformPosition(I->RideHand[k]);
		RideFootCS[k] = I->bRideLocal ? I->RideFootLocal[k] : CT.InverseTransformPosition(I->RideFoot[k]);
	}
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
	Upper.Reset();
	Fingers.Reset();
	const int32 Spine = Ref.FindBoneIndex(TEXT("spine_01"));
	for (int32 i = 0; i < BC.GetCompactPoseNumBones(); ++i)
	{
		const FCompactPoseBoneIndex CI(i);
		const int32 Mesh = BC.MakeMeshPoseIndex(CI).GetInt();
		const FName Name = Ref.GetBoneName(Mesh);
		Bones.Add(Name, CI);
		{
			const FString N = Name.ToString();
			if ((N.StartsWith(TEXT("thumb_")) || N.StartsWith(TEXT("index_")) || N.StartsWith(TEXT("middle_")) || N.StartsWith(TEXT("ring_"))
				|| N.StartsWith(TEXT("pinky_"))) && !N.Contains(TEXT("metacarpal")))
			{
				Fingers.Add(CI);
			}
		}
		// Under spine_01: the lower spine follows the walk half way, the rest is the weapon pose's.
		for (int32 P = Mesh; P != INDEX_NONE && Spine != INDEX_NONE; P = Ref.GetParentIndex(P))
		{
			if (P == Spine)
			{
				const FString S = Name.ToString();
				Upper.Add({CI, (S == TEXT("spine_01") || S == TEXT("spine_02")) ? 0.5f : 1.f});
				break;
			}
		}
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

void FM80OverlayProxy::LayerUpper(FPoseContext& Output, UAnimSequence* Seq, double Time, float Weight)
{
	FCompactPose P;
	P.SetBoneContainer(&Output.Pose.GetBoneContainer());
	FBlendedCurve Curve;
	Curve.InitFrom(Output.Curve);
	UE::Anim::FStackAttributeContainer Attributes;
	FAnimationPoseData Data(P, Curve, Attributes);
	Seq->GetAnimationPose(Data, FAnimExtractContext(Time, false));
	for (const TPair<FCompactPoseBoneIndex, float>& B : Upper)
	{
		const float W = Weight * B.Value;
		FTransform& Local = Output.Pose[B.Key];
		Local.SetRotation(FQuat::Slerp(Local.GetRotation(), P[B.Key].GetRotation(), W).GetNormalized());
	}
}

void FM80OverlayProxy::Fists(FPoseContext& Output)
{
	if (!Punches || Fingers.Num() == 0)
	{
		return;
	}
	// The fingers of the boxing guard (A_M80_Pugni_Combo before the first blow): a real fist, closed round the grip.
	FCompactPose P;
	P.SetBoneContainer(&Output.Pose.GetBoneContainer());
	FBlendedCurve Curve;
	Curve.InitFrom(Output.Curve);
	UE::Anim::FStackAttributeContainer Attributes;
	FAnimationPoseData Data(P, Curve, Attributes);
	Punches->GetAnimationPose(Data, FAnimExtractContext(0.3, false));
	const float W = FMath::Clamp(RideFists, 0.f, 1.f);
	for (const FCompactPoseBoneIndex& F : Fingers)
	{
		FTransform& Local = Output.Pose[F];
		Local.SetRotation(FQuat::Slerp(Local.GetRotation(), P[F].GetRotation(), W).GetNormalized());
	}
}

bool FM80OverlayProxy::Punch(FPoseContext& Output)
{
	if (!Punches || Upper.Num() == 0)
	{
		return false;
	}
	// The four blows of A_M80_Pugni_Combo (left jab, right cross, left, right), from the guard to the guard; the
	// hits land 0.2 s in.
	static const float Start[4] = {0.42f, 0.68f, 0.92f, 1.14f};
	static const float Length[4] = {0.34f, 0.32f, 0.28f, 0.50f};
	const int32 K = FMath::Clamp(PunchStep, 0, 3);
	if (PunchTime > Length[K])
	{
		return true;
	}
	// In fast, out over the last 0.12 s.
	const float W = FMath::Clamp(PunchTime / 0.06f, 0.f, 1.f) * FMath::Clamp((Length[K] - PunchTime) / 0.12f, 0.f, 1.f);
	LayerUpper(Output, Punches, Start[K] + PunchTime, W);
	return true;
}

bool FM80OverlayProxy::UpperBodyPose(FPoseContext& Output)
{
	const bool bRifle = Pose == EM80WeaponPose::Rifle;
	UAnimSequence* Seq = bAimPoint ? (bRifle ? RifleAim : PistolAim) : (bRifle ? RifleHold : PistolHold);
	if (!Seq || Upper.Num() == 0)
	{
		return false;
	}
	// The aim sweep goes from straight up (start) to straight down (end); the hold pose is its first frame.
	const double Len = Seq->GetPlayLength();
	const double T = bAimPoint ? Len * FMath::Clamp(0.5 - AimPitch / 180.0, 0.0, 1.0) : 0.0;
	LayerUpper(Output, Seq, T, ArmsWeight);
	// What is left to the crosshair sideways: the chest turns (the body follows the camera anyway).
	const float Yaw = FMath::Clamp(AimYaw, -60.f, 60.f) * ArmsWeight;
	Rotate(Output, TEXT("spine_03"), CSUp, Yaw * 0.5f);
	Rotate(Output, TEXT("spine_05"), CSUp, Yaw * 0.5f);
	// Recoil: the forearm and the hand kick up.
	Rotate(Output, TEXT("lowerarm_r"), CSLeft, -12.f * Recoil);
	Rotate(Output, TEXT("hand_r"), CSLeft, -10.f * Recoil);
	return true;
}

void FM80OverlayProxy::CurlThumbs(FPoseContext& Output)
{
	for (const TCHAR* Side : {TEXT("_l"), TEXT("_r")})
	{
		const FCompactPoseBoneIndex* Index = Bones.Find(FName(FString(TEXT("index_02")) + Side));
		if (!Index)
		{
			continue;
		}
		// Fingers curl about their own Z: how far the index finger is bent from the mannequin's rest pose.
		const FQuat Bend = Output.Pose.GetRefPose(*Index).GetRotation().Inverse() * Output.Pose[*Index].GetRotation();
		const float Curl = Bend.GetTwistAngle(FVector::ZAxisVector);
		const TPair<const TCHAR*, float> Thumb[] = {{TEXT("thumb_01"), 0.9f}, {TEXT("thumb_02"), 0.8f}, {TEXT("thumb_03"), 0.6f}};
		for (const TPair<const TCHAR*, float>& T : Thumb)
		{
			if (const FCompactPoseBoneIndex* I = Bones.Find(FName(FString(T.Key) + Side)))
			{
				FTransform& Local = Output.Pose[*I];
				Local.SetRotation((Local.GetRotation() * FQuat(FVector::ZAxisVector, Curl * T.Value)).GetNormalized());
			}
		}
	}
}

void FM80OverlayProxy::RideLimbs(FPoseContext& Output)
{
	auto Find = [this](const TCHAR* N) { const FCompactPoseBoneIndex* I = Bones.Find(N); return I ? *I : FCompactPoseBoneIndex(INDEX_NONE); };
	// The torso over the handlebar or pulled back (the arms follow onto the grips below).
	Rotate(Output, TEXT("spine_02"), CSLeft, -RideLean * 0.6f * FMath::Clamp(RideWeight, 0.f, 1.f));
	Rotate(Output, TEXT("spine_04"), CSLeft, -RideLean * 0.4f * FMath::Clamp(RideWeight, 0.f, 1.f));
	static const TCHAR* const Chains[4][3] = {{TEXT("upperarm_l"), TEXT("lowerarm_l"), TEXT("hand_l")}, {TEXT("upperarm_r"), TEXT("lowerarm_r"), TEXT("hand_r")},
		{TEXT("thigh_l"), TEXT("calf_l"), TEXT("foot_l")}, {TEXT("thigh_r"), TEXT("calf_r"), TEXT("foot_r")}};
	FCSPose<FCompactPose> CS;
	CS.InitPose(Output.Pose);
	const float W = FMath::Clamp(RideWeight, 0.f, 1.f);
	for (int32 k = 0; k < (bRideFeet ? 4 : 2); ++k)
	{
		const FCompactPoseBoneIndex A = Find(Chains[k][0]), B = Find(Chains[k][1]), C = Find(Chains[k][2]);
		if (!A.IsValid() || !B.IsValid() || !C.IsValid())
		{
			continue;
		}
		FTransform T[3] = {CS.GetComponentSpaceTransform(A), CS.GetComponentSpaceTransform(B), CS.GetComponentSpaceTransform(C)};
		const FTransform T0[3] = {T[0], T[1], T[2]};
		const FVector Target = k < 2 ? RideHandCS[k] : RideFootCS[k - 2];
		// The elbow / knee keeps the side the pose bends it to; the hand / foot keeps its turn. An arm reaching almost straight
		// leaves that side undecided from frame to frame (the elbow flipped): on a moped the elbows go out and down, the
		// knees forward.
		FVector Joint = T[1].GetLocation() * 2.f - (T[0].GetLocation() + T[2].GetLocation()) * 0.5f;
		if (bRideSteadyJoints)
		{
			Joint = k < 2 ? T[1].GetLocation() + (k == 0 ? CSLeft : -CSLeft) * 40.f - CSUp * 25.f : T[1].GetLocation() + CSForward * 40.f;
		}
		const FQuat EndRot = T[2].GetRotation();
		FVector Reach = Target;
		if (bRideSteadyJoints)
		{
			// Short of full reach (the grips are about an arm's length away: with the moped's shakes the arm went straight
			// and bent again from frame to frame, the elbow jumping).
			const float Length = (T[1].GetLocation() - T[0].GetLocation()).Size() + (T[2].GetLocation() - T[1].GetLocation()).Size();
			const FVector D = Target - T[0].GetLocation();
			if (D.Size() > Length * 0.96f)
			{
				Reach = T[0].GetLocation() + D.GetSafeNormal() * Length * 0.96f;
			}
		}
		AnimationCore::SolveTwoBoneIK(T[0], T[1], T[2], Joint, Reach, false, 1.0, 1.0);
		T[2].SetRotation(EndRot);
		TArray<FBoneTransform> Out;
		const FCompactPoseBoneIndex Index[3] = {A, B, C};
		for (int32 j = 0; j < 3; ++j)
		{
			FTransform Blended;
			Blended.Blend(T0[j], T[j], W);
			Out.Add(FBoneTransform(Index[j], Blended));
		}
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
	if (bGripLedge)
	{
		CurlThumbs(Output);
	}
	if (RideWeight > 0.01f)
	{
		RideLimbs(Output);
	}
	if (RideFists > 0.01f)
	{
		Fists(Output);
	}
	if (ArmsWeight > 0.01f && !UpperBodyPose(Output))
	{
		AimArms(Output);
	}
	if (Swing >= 0.f)
	{
		if (bPunch && Punch(Output))
		{
		}
		else if (bPunch)
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
