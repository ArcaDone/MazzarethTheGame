#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "AnimNodes/AnimNode_RetargetPoseFromMesh.h"
#include "M80BodyAnim.generated.h"

class UIKRetargeter;

/**
 * The MetaHuman body of the player: the retarget from the animation copy (as the sample's ABP_GenericRetarget, same IK
 * retargeter), then, riding a cart or a moped, the wrists and ankles placed on the vehicle's grips and pedals on this
 * body's own bones. Done on the copy before the retarget they arrived elsewhere (other proportions: the hands high over
 * the grips) and the arms jumped from frame to frame.
 */
USTRUCT()
struct FM80BodyProxy : public FAnimInstanceProxy
{
	GENERATED_BODY()

	FM80BodyProxy() = default;
	FM80BodyProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance) {}

	virtual void Initialize(UAnimInstance* InAnimInstance) override;
	virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override;
	virtual void CacheBones() override;
	virtual bool Evaluate(FPoseContext& Output) override;
	virtual FAnimNode_Base* GetCustomRootNode() override { return &Retarget; }
	virtual void GetCustomNodes(TArray<FAnimNode_Base*>& OutNodes) override { OutNodes.Add(&Retarget); }

	FAnimNode_RetargetPoseFromMesh Retarget;

	// From the overlay copy's instance (the player controller sets it), in this body's component space.
	float RideWeight = 0.f;
	bool bRideFeet = false;
	bool bSteady = false;
	FVector HandCS[2] = {FVector::ZeroVector, FVector::ZeroVector};
	FVector FootCS[2] = {FVector::ZeroVector, FVector::ZeroVector};

	// upperarm, lowerarm, hand (left, right), thigh, calf, foot (left, right): compact pose indices, INDEX_NONE if missing.
	int32 Chain[4][3] = {{INDEX_NONE, INDEX_NONE, INDEX_NONE}, {INDEX_NONE, INDEX_NONE, INDEX_NONE}, {INDEX_NONE, INDEX_NONE, INDEX_NONE},
		{INDEX_NONE, INDEX_NONE, INDEX_NONE}};
};

UCLASS(Transient, NotBlueprintable)
class MAZZARINOGAMEPLAY_API UM80BodyAnimInstance : public UAnimInstance
{
	GENERATED_BODY()

public:
	/** The retargeter of the body's animation blueprint (read from it before it is replaced), else the MetaHuman one. */
	static UIKRetargeter* FindRetargeter(const USkeletalMeshComponent* Body);

	/** Given to the next instance made (its proxy is initialised before anything can be set on it). */
	static TWeakObjectPtr<UIKRetargeter> NextRetargeter;

	UPROPERTY(Transient)
	TObjectPtr<UIKRetargeter> Retargeter;

protected:
	virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override { return new FM80BodyProxy(this); }
	virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override { delete InProxy; }
	friend struct FM80BodyProxy;
};
