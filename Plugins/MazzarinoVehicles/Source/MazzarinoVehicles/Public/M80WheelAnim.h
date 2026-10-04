#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "M80WheelAnim.generated.h"

/**
 * Wheel animation for the cars imported from Blender (skeleton Root + Wheel_FL/FR/RL/RR), in code: no
 * animation blueprint needed. Every frame each wheel bone of the vehicle's wheel setups turns with the
 * wheel, steers and follows the suspension, as the Chaos "Wheel Controller" node does.
 */
USTRUCT()
struct FM80WheelAnimProxy : public FAnimInstanceProxy
{
	GENERATED_BODY()

	FM80WheelAnimProxy() = default;
	FM80WheelAnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance) {}

	virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override;
	virtual void CacheBones() override;
	virtual bool Evaluate(FPoseContext& Output) override;

	struct FWheel
	{
		FName Bone;
		FCompactPoseBoneIndex Index = FCompactPoseBoneIndex(INDEX_NONE);
		float Spin = 0.f;      // degrees
		float Steer = 0.f;     // degrees
		float Offset = 0.f;    // cm, suspension
	};
	TArray<FWheel> Wheels;
};

UCLASS(Transient, NotBlueprintable)
class MAZZARINOVEHICLES_API UM80WheelAnimInstance : public UAnimInstance
{
	GENERATED_BODY()

protected:
	virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override { return new FM80WheelAnimProxy(this); }
	virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override { delete InProxy; }
};
