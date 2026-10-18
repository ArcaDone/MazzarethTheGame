#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "M80Climb.generated.h"

class ACharacter;
class UAnimMontage;
class UAnimSequence;

UENUM(BlueprintType)
enum class EM80ClimbState : uint8
{
	None,
	Mantling,    // onto something up to 2.5 m (the sample's traversal montages, motion warped)
	Hanging,     // hands on a ledge
	Shimmying,   // moving along the ledge
	ClimbingUp,  // from hanging onto the top
	Dropping
};

/** A ledge: the top edge of a wall, and the wall's outward normal. */
USTRUCT(BlueprintType)
struct FM80Ledge
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Mazzarino")
	FVector Edge = FVector::ZeroVector;      // on the wall face, at the height of the top

	UPROPERTY(BlueprintReadOnly, Category = "Mazzarino")
	FVector Normal = FVector::ForwardVector; // horizontal, out of the wall

	UPROPERTY(BlueprintReadOnly, Category = "Mazzarino")
	float Height = 0.f;                       // top above the feet

	UPROPERTY(BlueprintReadOnly, Category = "Mazzarino")
	bool bRoomOnTop = false;                  // a standing character fits on the top

	TWeakObjectPtr<AActor> Actor;
};

/**
 * Climbing on anything with collision (houses, balconies, walls, roofs), GTA IV style:
 * - Jump facing something 0.5-2.5 m high: the character climbs onto it (the sample's mantle and climb montages,
 *   warped onto the ledge).
 * - Higher ledges are caught by jumping or falling near them: the hands grab the edge and the character hangs
 *   (Mixamo clips retargeted by Scripts/m80_animazioni_import.py). Hanging: left/right moves along the ledge,
 *   following the wall; jump climbs onto the top (or jumps up to a ledge above, or away from the wall when moving
 *   back); C / Ctrl / gamepad B lets go.
 * While a clip plays the body stays where the clip puts it (hands on the ledge) and the capsule follows it, so the
 * hands never slide off the edge; at the end of climbing up the character stands on the top.
 */
UCLASS(ClassGroup = (Mazzarino), meta = (BlueprintSpawnableComponent))
class MAZZARINOGAMEPLAY_API UM80ClimbComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UM80ClimbComponent();

	virtual void BeginPlay() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/** Jump pressed: climbs, catches a ledge or acts on the ledge held. True when it took the jump (no normal jump). */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	bool JumpPressed();

	/** Movement input in world space (the player controller passes the move stick / WASD while climbing). */
	void SetMoveInput(const FVector& WorldInput) { MoveInput = WorldInput; }

	/** Holds a movement input for a while (tests). */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void ForceMoveInput(FVector WorldInput, float Seconds) { ForcedInput = WorldInput; ForcedTime = Seconds; }

	/** Lets go of the ledge. */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	void Drop();

	/** Lets go of anything held at once and catches no ledge for Seconds (the player in a vehicle, getting in or out, down). */
	void Suspend(float Seconds);

	UFUNCTION(BlueprintPure, Category = "Mazzarino")
	EM80ClimbState GetState() const { return State; }

	UFUNCTION(BlueprintPure, Category = "Mazzarino")
	bool IsClimbing() const { return State != EM80ClimbState::None; }

	/** Out of the wall held (horizontal), while hanging. */
	FVector GetWallNormal() const { return Ledge.Normal; }

	/** Ledge in front of the character between MinRise and MaxRise above its feet (tests and the HUD hint). */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	bool FindLedge(float MinRise, float MaxRise, FM80Ledge& Out) const;

	/** Grabs the ledge (tests): hangs from it at once. */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino")
	bool Grab(const FM80Ledge& Ledge);

	/** Why the last ledge search failed, and what the hanging input was (tests). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Mazzarino")
	FString Debug;

	/** Hand reach above the feet when jumping: ledges up to this height are caught. */
	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	float MaxGrabHeight = 340.f;

	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	float ShimmySpeed = 1.f;

	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	TSoftObjectPtr<UAnimSequence> HangAnim = TSoftObjectPtr<UAnimSequence>(FSoftObjectPath(TEXT("/Game/Mazzarino80/Player/Anim/A_M80_Appeso_Laterale.A_M80_Appeso_Laterale")));

	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	TSoftObjectPtr<UAnimSequence> ClimbUpAnim = TSoftObjectPtr<UAnimSequence>(FSoftObjectPath(TEXT("/Game/Mazzarino80/Player/Anim/A_M80_Appeso_Salita.A_M80_Appeso_Salita")));

	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	TSoftObjectPtr<UAnimMontage> MantleMontage = TSoftObjectPtr<UAnimMontage>(FSoftObjectPath(TEXT("/Game/Characters/UEFN_Mannequin/Animations/Traversal/Mantle/AM_M_Neutral_Traversal_Mantle_1_0_stand_F_Lfoot.AM_M_Neutral_Traversal_Mantle_1_0_stand_F_Lfoot")));

	UPROPERTY(EditAnywhere, Category = "Mazzarino")
	TSoftObjectPtr<UAnimMontage> ClimbMontage = TSoftObjectPtr<UAnimMontage>(FSoftObjectPath(TEXT("/Game/Characters/UEFN_Mannequin/Animations/Traversal/Climb/AM_M_Neutral_Traversal_Climb_Start_2_5_stand_F_Lfoot.AM_M_Neutral_Traversal_Climb_Start_2_5_stand_F_Lfoot")));

private:
	ACharacter* Owner() const;
	bool FindLedgeFrom(const FVector& Feet, const FVector& Forward, float MinRise, float MaxRise, FM80Ledge& Out) const;
	void Note(const FString& S) const { const_cast<UM80ClimbComponent*>(this)->Debug = S; }
	void StartMantle(const FM80Ledge& Ledge);
	void EndMantle();
	void PlayClip(UAnimSequence* Clip, float Time, float Rate);
	FVector HandsWorld() const;
	void AlignHandsTo(const FVector& Target);
	void FollowBody();
	void KeepOffWall(float DeltaTime, bool bCheckWall);
	void TickHang(float DeltaTime);
	void StartClimbUp();
	void FinishClimbUp();
	void Release(const FVector& Push);
	void RestoreBody();
	FVector HoldPoint(const FM80Ledge& L) const;

	EM80ClimbState State = EM80ClimbState::None;
	FM80Ledge Ledge;
	float ClipTime = 0.f;
	float ClipRate = 0.f;
	float ClipLength = 0.f;
	TWeakObjectPtr<UAnimSequence> Clip;
	FTransform MeshRelative;
	uint8 MeshTickOption = 0;
	bool bMeshURO = false;   // the mesh's VisibilityBasedAnimTickOption before climbing
	FVector BodyToCapsule = FVector::ZeroVector;   // capsule centre from the pelvis while hanging
	float Lean = 0.f;                              // degrees the hanging body swings out about the hands
	float MantleTime = 0.f;
	float GrabCooldown = 0.f;
	FVector MoveInput = FVector::ZeroVector;
	FVector ForcedInput = FVector::ZeroVector;
	float ForcedTime = 0.f;
	FVector Input() const { return ForcedTime > 0.f ? ForcedInput : MoveInput; }
	TWeakObjectPtr<UAnimMontage> Montage;
};
