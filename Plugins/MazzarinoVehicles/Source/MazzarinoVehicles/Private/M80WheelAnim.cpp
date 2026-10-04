#include "M80WheelAnim.h"
#include "ChaosVehicleWheel.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "WheeledVehiclePawn.h"

void FM80WheelAnimProxy::PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds)
{
	FAnimInstanceProxy::PreUpdate(InAnimInstance, DeltaSeconds);
	const AWheeledVehiclePawn* Pawn = Cast<AWheeledVehiclePawn>(InAnimInstance->GetOwningActor());
	const UChaosWheeledVehicleMovementComponent* M = Pawn ? Cast<UChaosWheeledVehicleMovementComponent>(Pawn->GetVehicleMovementComponent()) : nullptr;
	if (!M)
	{
		return;
	}
	const int32 Num = FMath::Min(M->WheelSetups.Num(), M->Wheels.Num());
	if (Wheels.Num() != Num)
	{
		Wheels.SetNum(Num);
		for (int32 i = 0; i < Num; ++i)
		{
			Wheels[i].Bone = M->WheelSetups[i].BoneName;
			Wheels[i].Index = FCompactPoseBoneIndex(INDEX_NONE);
		}
		CacheBones();
	}
	for (int32 i = 0; i < Num; ++i)
	{
		if (const UChaosVehicleWheel* W = M->Wheels[i])
		{
			Wheels[i].Spin = W->GetRotationAngle();
			Wheels[i].Steer = W->GetSteerAngle();
			Wheels[i].Offset = W->GetSuspensionOffset();
		}
	}
}

void FM80WheelAnimProxy::CacheBones()
{
	FAnimInstanceProxy::CacheBones();
	const FBoneContainer& BC = GetRequiredBones();
	if (!BC.IsValid())
	{
		return;
	}
	for (FWheel& W : Wheels)
	{
		const int32 MeshIndex = BC.GetPoseBoneIndexForBoneName(W.Bone);
		W.Index = MeshIndex == INDEX_NONE ? FCompactPoseBoneIndex(INDEX_NONE) : BC.MakeCompactPoseIndex(FMeshPoseBoneIndex(MeshIndex));
	}
}

bool FM80WheelAnimProxy::Evaluate(FPoseContext& Output)
{
	Output.Pose.ResetToRefPose();
	FCSPose<FCompactPose> CS;
	CS.InitPose(Output.Pose);
	TArray<FBoneTransform> Out;
	for (const FWheel& W : Wheels)
	{
		if (!W.Index.IsValid())
		{
			continue;
		}
		FTransform T = CS.GetComponentSpaceTransform(W.Index);
		T.AddToTranslation(FVector(0.f, 0.f, W.Offset));
		T.SetRotation(FQuat(FRotator(W.Spin, W.Steer, 0.f)) * T.GetRotation());
		Out.Add(FBoneTransform(W.Index, T));
	}
	Out.Sort(FCompareBoneTransformIndex());
	if (Out.Num())
	{
		CS.SafeSetCSBoneTransforms(Out);
		FCSPose<FCompactPose>::ConvertComponentPosesToLocalPoses(MoveTemp(CS), Output.Pose);
	}
	return true;
}
