#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "AnimNodes/AnimNode_CopyPoseFromMesh.h"
#include "M80Weapons.h"
#include "M80OverlayAnim.generated.h"

class ACharacter;

/**
 * Upper body overlay for the sample character, all in code (the sample's animation blueprint stays
 * untouched): a hidden copy of the animation mesh copies its pose every frame and moves the arms with
 * two-bone IK so the gun points exactly at the crosshair (right hand on the grip, left hand holding
 * under it, or on the fore-end of the lupara), held low when not aiming; recoil after a shot; punches
 * and blows. The MetaHuman body retargets from this copy instead of the original.
 */
USTRUCT()
struct FM80OverlayProxy : public FAnimInstanceProxy
{
	GENERATED_BODY()

	FM80OverlayProxy() = default;
	FM80OverlayProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance) {}

	virtual void Initialize(UAnimInstance* InAnimInstance) override;
	virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override;
	virtual void CacheBones() override;
	virtual bool Evaluate(FPoseContext& Output) override;
	virtual FAnimNode_Base* GetCustomRootNode() override { return &CopyNode; }
	virtual void GetCustomNodes(TArray<FAnimNode_Base*>& OutNodes) override { OutNodes.Add(&CopyNode); }

	FAnimNode_CopyPoseFromMesh CopyNode;

	// Game thread state copied in PreUpdate.
	EM80WeaponPose Pose = EM80WeaponPose::Unarmed;
	float ArmsWeight = 0.f;      // IK on the arms (0..1)
	bool bAimPoint = false;      // aiming at AimCS, else holding the gun low
	FVector AimCS = FVector::ZeroVector;
	float Recoil = 0.f;          // 0..1, decays after a shot
	float Swing = -1.f;          // melee blow phase 0..1, <0 none
	bool bPunch = false;
	FTransform Grip = FTransform::Identity;  // weapon frame in the hand bone's space (UEFN hand)

private:
	void Rotate(FPoseContext& Output, FName Bone, const FVector& CSAxis, float Degrees);
	void AimArms(FPoseContext& Output);

	TMap<FName, FCompactPoseBoneIndex> Bones;
};

UCLASS(Transient, NotBlueprintable)
class MAZZARINOGAMEPLAY_API UM80OverlayAnimInstance : public UAnimInstance
{
	GENERATED_BODY()

public:
	/** Adds the overlay copy under the character's animation mesh and moves the body onto it (once). */
	static UM80OverlayAnimInstance* Install(ACharacter* Character);

	/** Set by the player controller every frame. */
	EM80WeaponPose Pose = EM80WeaponPose::Unarmed;
	bool bAiming = false;
	FVector AimPoint = FVector::ZeroVector;   // world
	float SinceFire = 99.f;
	bool bEnabled = true;

	float BlendArms = 0.f;

protected:
	virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override { return new FM80OverlayProxy(this); }
	virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override { delete InProxy; }

	friend struct FM80OverlayProxy;
};
