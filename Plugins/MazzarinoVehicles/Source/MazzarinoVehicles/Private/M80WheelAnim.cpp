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
	float Sum = 0.f;
	int32 Steered = 0;
	for (int32 i = 0; i < Num; ++i)
	{
		if (const UChaosVehicleWheel* W = M->Wheels[i])
		{
			Wheels[i].Spin = W->GetRotationAngle();
			Wheels[i].Steer = W->GetSteerAngle();
			Wheels[i].Offset = W->GetSuspensionOffset();
			Wheels[i].bSteered = W->bAffectedBySteering;
			if (W->bAffectedBySteering)
			{
				Sum += Wheels[i].Steer;
				++Steered;
			}
		}
	}
	SteerYaw = Steered ? Sum / Steered : 0.f;
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
	const int32 Steer = BC.GetPoseBoneIndexForBoneName(TEXT("Steer"));
	SteerIndex = Steer == INDEX_NONE ? FCompactPoseBoneIndex(INDEX_NONE) : BC.MakeCompactPoseIndex(FMeshPoseBoneIndex(Steer));
}

bool FM80WheelAnimProxy::Evaluate(FPoseContext& Output)
{
	Output.Pose.ResetToRefPose();
	FCSPose<FCompactPose> CS;
	CS.InitPose(Output.Pose);
	TArray<FBoneTransform> Out;
	// The steering part turns about its bolt (about the bone's Z: upright on the carts, along the raked head of a moped's
	// fork); the steered wheels on it go round with it.
	FVector Pivot = FVector::ZeroVector;
	FQuat SteerRot(FVector::UpVector, FMath::DegreesToRadians(SteerYaw));
	if (SteerIndex.IsValid())
	{
		FTransform T = CS.GetComponentSpaceTransform(SteerIndex);
		Pivot = T.GetLocation();
		SteerRot = FQuat(T.GetRotation().GetAxisZ(), FMath::DegreesToRadians(SteerYaw));
		T.SetRotation(SteerRot * T.GetRotation());
		Out.Add(FBoneTransform(SteerIndex, T));
	}
	for (const FWheel& W : Wheels)
	{
		if (!W.Index.IsValid())
		{
			continue;
		}
		FTransform T = CS.GetComponentSpaceTransform(W.Index);
		if (SteerIndex.IsValid() && W.bSteered)
		{
			T.SetLocation(Pivot + SteerRot.RotateVector(T.GetLocation() - Pivot));
		}
		T.AddToTranslation(FVector(0.f, 0.f, W.Offset));
		T.SetRotation(SteerIndex.IsValid() && W.bSteered ? SteerRot * FQuat(FRotator(W.Spin, 0.f, 0.f)) * T.GetRotation()
			: FQuat(FRotator(W.Spin, W.Steer, 0.f)) * T.GetRotation());
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
