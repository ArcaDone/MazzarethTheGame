#pragma once

#include "CoreMinimal.h"
#include "AIController.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "GameFramework/Character.h"
#include "M80Pedone.generated.h"

class UAnimSequence;

/**
 * A townsperson walking about: light animation in code for many of them (no motion matching): a walk loop played as
 * fast as the character moves, the standing idle when still, blended by speed. Old people are bent: the spine leans
 * forward by Hunch degrees and the neck lifts the head back up so they still look ahead.
 */
USTRUCT()
struct FM80PedoneProxy : public FAnimInstanceProxy
{
	GENERATED_BODY()

	FM80PedoneProxy() = default;
	FM80PedoneProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance) {}

	virtual void Initialize(UAnimInstance* InAnimInstance) override;
	virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override;
	virtual void CacheBones() override;
	virtual bool Evaluate(FPoseContext& Output) override;

	UAnimSequence* Walk = nullptr;
	UAnimSequence* Idle = nullptr;
	float WalkSpeed = 150.f;   // cm/s of the walk loop
	double WalkTime = 0.0;
	double IdleTime = 0.0;
	float Speed = 0.f;
	float Hunch = 0.f;

private:
	void Sample(UAnimSequence* Seq, double Time, FCompactPose& Out, FBlendedCurve& Curve, const FPoseContext& Like) const;
	void Rotate(FPoseContext& Output, FName Bone, const FVector& CSAxis, float Degrees);
	TMap<FName, FCompactPoseBoneIndex> Bones;
};

UCLASS(Transient, NotBlueprintable)
class MAZZARINOGAMEPLAY_API UM80PedoneAnimInstance : public UAnimInstance
{
	GENERATED_BODY()

protected:
	virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override { return new FM80PedoneProxy(this); }
	virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override { delete InProxy; }
};

/**
 * A townsperson: the UEFN mannequin animated by UM80PedoneAnimInstance (hidden), wearing the built MetaHuman of
 * Personaggio (/Game/Mazzarino80/Personaggi/Folla/Build/<Name>/BP_<Name>, made by Scripts/m80_folla_build.py): its body
 * retargets from the mannequin, face, hair and clothes follow the body. Walks about by itself (AM80PedoneAI).
 */
UCLASS(meta = (DisplayName = "Pedone (Mazzarino)"))
class MAZZARINOGAMEPLAY_API AM80Pedone : public ACharacter
{
	GENERATED_BODY()

public:
	AM80Pedone();

	/** Which of the crowd (Anziana1, Uomo2, Ragazza3...). Old people ("Anzian...") are slower and bent. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Pedone")
	FName Personaggio = TEXT("Uomo2");

	/** Degrees the back is bent forward; < 0: from the character (old people about 22, the others none). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Pedone")
	float Hunch = -1.f;

	/** Walking speed (cm/s); <= 0: from the character (old people about 80, the young 140). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Pedone")
	float Passo = 0.f;

	/** How far from where it started it wanders (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Pedone")
	float Raggio = 2500.f;

	UFUNCTION(BlueprintPure, Category = "Pedone")
	bool IsOld() const { return Personaggio.ToString().StartsWith(TEXT("Anzian")); }

	float GetHunch() const { return Hunch >= 0.f ? Hunch : (IsOld() ? 22.f : 0.f); }
	FVector GetHome() const { return Home; }

	/** Spawns a townsperson already set to InPersonaggio (it dresses on BeginPlay, so the name must come first). */
	UFUNCTION(BlueprintCallable, Category = "Pedone", meta = (WorldContext = "WorldContext"))
	static AM80Pedone* SpawnPedone(UObject* WorldContext, FName InPersonaggio, const FTransform& Where);

	/** Builds the navigation mesh inside the world's NavMeshBoundsVolumes now (creating it if missing); false if none. */
	UFUNCTION(BlueprintCallable, Category = "Pedone", meta = (WorldContext = "WorldContext"))
	static bool BuildNavigation(UObject* WorldContext);

protected:
	virtual void BeginPlay() override;

private:
	/** Copies body, face, grooms and clothes of the built MetaHuman Blueprint onto this character. */
	void Dress();
	FVector Home = FVector::ZeroVector;
};

/**
 * A crowd for a level: on Play it puts Quanti townspeople around the level's crowd markers (TargetPoints tagged
 * M80Folla_..., as in L_M80_ProvaFolla) or, without markers, within Raggio of itself, taking the characters in turn.
 */
UCLASS(meta = (DisplayName = "Folla (Mazzarino)"))
class MAZZARINOGAMEPLAY_API AM80Folla : public AActor
{
	GENERATED_BODY()

public:
	AM80Folla();

	/** How many people. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Folla", meta = (ClampMin = "0", ClampMax = "300"))
	int32 Quanti = 42;

	/** The characters, in turn (each needs its build: Scripts/m80_folla_build.py). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Folla")
	TArray<FName> Personaggi;

	/** Start around the M80Folla_ markers when there are any (otherwise within Raggio of this actor). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Folla")
	bool bUsaSegnaposto = true;

	/** How far from this actor they start without markers, and how far each one wanders (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Folla")
	float Raggio = 2500.f;

	/** Same seed, same crowd in the same places. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Folla")
	int32 Seme = 7;

protected:
	virtual void BeginPlay() override;
};

/** Walks its pedestrian to random reachable points around its starting place, stopping a few seconds at each. */
UCLASS()
class MAZZARINOGAMEPLAY_API AM80PedoneAI : public AAIController
{
	GENERATED_BODY()

public:
	virtual void OnPossess(APawn* InPawn) override;
	virtual void OnMoveCompleted(FAIRequestID RequestID, const FPathFollowingResult& Result) override;

private:
	void Next();
	FTimerHandle Wait;
};
