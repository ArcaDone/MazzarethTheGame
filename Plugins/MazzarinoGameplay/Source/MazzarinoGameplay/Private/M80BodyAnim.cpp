#include "M80BodyAnim.h"
#include "M80OverlayAnim.h"
#include "Components/SkeletalMeshComponent.h"
#include "Retargeter/IKRetargeter.h"
#include "TwoBoneIK.h"

namespace
{
// Component space of the MetaHuman body (as the mannequin's): it looks along +Y, +X is its left, +Z up.
const FVector BodyForward(0.f, 1.f, 0.f);
const FVector BodyLeft(1.f, 0.f, 0.f);
const FVector BodyUp(0.f, 0.f, 1.f);
}

TWeakObjectPtr<UIKRetargeter> UM80BodyAnimInstance::NextRetargeter;

UIKRetargeter* UM80BodyAnimInstance::FindRetargeter(const USkeletalMeshComponent* Body)
{
	// The animation blueprint picks it (from a map by the mesh's tag) into a variable: read it there.
	if (const UAnimInstance* Old = Body ? Body->GetAnimInstance() : nullptr)
	{
		for (TFieldIterator<FObjectPropertyBase> It(Old->GetClass()); It; ++It)
		{
			if (It->PropertyClass && It->PropertyClass->IsChildOf(UIKRetargeter::StaticClass()))
			{
				if (UIKRetargeter* R = Cast<UIKRetargeter>(It->GetObjectPropertyValue_InContainer(Old)))
				{
					return R;
				}
			}
		}
	}
	return LoadObject<UIKRetargeter>(nullptr, TEXT("/Game/MetaHumans/Common/Common/Rigs/RTG_UEFN_to_Metahuman_nrw.RTG_UEFN_to_Metahuman_nrw"));
}

void FM80BodyProxy::Initialize(UAnimInstance* InAnimInstance)
{
	UM80BodyAnimInstance* I = Cast<UM80BodyAnimInstance>(InAnimInstance);
	if (I && !I->Retargeter)
	{
		I->Retargeter = UM80BodyAnimInstance::NextRetargeter.Get();
	}
	Retarget.RetargetFrom = ERetargetSourceMode::ParentSkeletalMeshComponent;
	Retarget.IKRetargeterAsset = I ? I->Retargeter.Get() : nullptr;
	Retarget.bSuppressWarnings = true;
	FAnimInstanceProxy::Initialize(InAnimInstance);
}

void FM80BodyProxy::PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds)
{
	FAnimInstanceProxy::PreUpdate(InAnimInstance, DeltaSeconds);
	Retarget.PreUpdate(InAnimInstance);
	RideWeight = 0.f;
	const USkeletalMeshComponent* Comp = InAnimInstance->GetSkelMeshComponent();
	const USkeletalMeshComponent* Copy = Comp ? Cast<USkeletalMeshComponent>(Comp->GetAttachParent()) : nullptr;
	const UM80OverlayAnimInstance* O = Copy ? Cast<UM80OverlayAnimInstance>(Copy->GetAnimInstance()) : nullptr;
	if (!O || O->RideWeight <= 0.01f)
	{
		return;
	}
	const FTransform& CT = Comp->GetComponentTransform();
	// The body sits on the copy (and the copy on the animation mesh) at a fixed offset: from the mesh's space straight
	// into this one, without the world (whose points lag behind a fast vehicle).
	const FTransform Rel = Comp->GetRelativeTransform() * Copy->GetRelativeTransform();
	RideWeight = O->RideWeight;
	bRideFeet = O->bRideFeet;
	bSteady = O->bRideSteadyJoints;
	for (int32 k = 0; k < 2; ++k)
	{
		HandCS[k] = O->bRideLocal ? Rel.InverseTransformPosition(O->RideHandLocal[k]) : CT.InverseTransformPosition(O->RideHand[k]);
		FootCS[k] = O->bRideLocal ? Rel.InverseTransformPosition(O->RideFootLocal[k]) : CT.InverseTransformPosition(O->RideFoot[k]);
	}
}

void FM80BodyProxy::CacheBones()
{
	FAnimInstanceProxy::CacheBones();
	const FBoneContainer& BC = GetRequiredBones();
	if (!BC.IsValid())
	{
		return;
	}
	static const TCHAR* const Names[4][3] = {{TEXT("upperarm_l"), TEXT("lowerarm_l"), TEXT("hand_l")}, {TEXT("upperarm_r"), TEXT("lowerarm_r"), TEXT("hand_r")},
		{TEXT("thigh_l"), TEXT("calf_l"), TEXT("foot_l")}, {TEXT("thigh_r"), TEXT("calf_r"), TEXT("foot_r")}};
	for (int32 k = 0; k < 4; ++k)
	{
		for (int32 j = 0; j < 3; ++j)
		{
			const int32 Mesh = BC.GetPoseBoneIndexForBoneName(Names[k][j]);
			Chain[k][j] = Mesh == INDEX_NONE ? INDEX_NONE : BC.MakeCompactPoseIndex(FMeshPoseBoneIndex(Mesh)).GetInt();
		}
	}
}

bool FM80BodyProxy::Evaluate(FPoseContext& Output)
{
	EvaluateAnimationNode_WithRoot(Output, &Retarget);
	const float W = FMath::Clamp(RideWeight, 0.f, 1.f);
	if (W <= 0.01f)
	{
		return true;
	}
	FCSPose<FCompactPose> CS;
	CS.InitPose(Output.Pose);
	for (int32 k = 0; k < (bRideFeet ? 4 : 2); ++k)
	{
		if (Chain[k][0] == INDEX_NONE || Chain[k][1] == INDEX_NONE || Chain[k][2] == INDEX_NONE)
		{
			continue;
		}
		const FCompactPoseBoneIndex Index[3] = {FCompactPoseBoneIndex(Chain[k][0]), FCompactPoseBoneIndex(Chain[k][1]), FCompactPoseBoneIndex(Chain[k][2])};
		FTransform T[3] = {CS.GetComponentSpaceTransform(Index[0]), CS.GetComponentSpaceTransform(Index[1]), CS.GetComponentSpaceTransform(Index[2])};
		const FTransform T0[3] = {T[0], T[1], T[2]};
		const FVector Target = k < 2 ? HandCS[k] : FootCS[k - 2];
		// The elbows out and down, the knees forward (steady: an arm almost straight had no side to keep), else the side
		// the pose bends them to.
		FVector Joint = T[1].GetLocation() * 2.f - (T[0].GetLocation() + T[2].GetLocation()) * 0.5f;
		if (bSteady)
		{
			Joint = k < 2 ? T[1].GetLocation() + (k == 0 ? BodyLeft : -BodyLeft) * 40.f - BodyUp * 25.f : T[1].GetLocation() + BodyForward * 40.f;
		}
		// Never quite straight: at full reach the arm went straight and bent again from frame to frame.
		const float Length = (T[1].GetLocation() - T[0].GetLocation()).Size() + (T[2].GetLocation() - T[1].GetLocation()).Size();
		FVector Reach = Target;
		const FVector D = Target - T[0].GetLocation();
		if (D.Size() > Length * 0.97f)
		{
			Reach = T[0].GetLocation() + D.GetSafeNormal() * Length * 0.97f;
		}
		const FQuat EndRot = T[2].GetRotation();
		AnimationCore::SolveTwoBoneIK(T[0], T[1], T[2], Joint, Reach, false, 1.0, 1.0);
		T[2].SetRotation(EndRot);
		TArray<FBoneTransform> Out;
		for (int32 j = 0; j < 3; ++j)
		{
			FTransform Blended;
			Blended.Blend(T0[j], T[j], W);
			Out.Add(FBoneTransform(Index[j], Blended));
		}
		CS.SafeSetCSBoneTransforms(Out);
	}
	FCSPose<FCompactPose>::ConvertComponentPosesToLocalPoses(MoveTemp(CS), Output.Pose);
	return true;
}
