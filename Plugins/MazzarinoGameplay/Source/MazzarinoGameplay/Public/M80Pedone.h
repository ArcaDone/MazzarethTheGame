#pragma once

#include "CoreMinimal.h"
#include "AIController.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "GameFramework/Character.h"
#include "M80Pedone.generated.h"

class UAnimSequence;
class UStaticMeshComponent;

/** What a townsperson is doing. */
UENUM(BlueprintType)
enum class EM80Stato : uint8
{
	Libero,      // walking about or standing between walks
	VaAParlare,  // stopped for a chat, waiting for the other one to come close
	Parla,       // chatting, facing the other one
	Caduto,      // tripped: falls, lies a few seconds, gets up
};

/** How a townsperson walks. */
UENUM(BlueprintType)
enum class EM80Andatura : uint8
{
	Auto,            // from the character (see AM80Pedone::BeginPlay)
	Normale,         // the mannequin's walk
	Vecchio,         // the old man's slow stooped walk
	VecchioTrascina, // old, dragging the legs (a zombie walk's legs under the arms of the walk with a bag)
	Triste,          // slow, head down
	Spesa,           // carrying something in the right hand
};

/** What a townsperson carries in the right hand. */
UENUM(BlueprintType)
enum class EM80Accessorio : uint8
{
	Auto,
	Nessuno,
	Bastone,
	BorsaSpesa,
	Borsetta,
};

/**
 * A townsperson's animation, light enough for many of them (no motion matching): the walk played as fast as the
 * character moves (its legs possibly from another clip), the standing idle when still, blended by speed; a chat clip
 * over it while chatting; the trip played through, held on the ground, then backwards to stand up. Old people are bent
 * a little more: the spine leans forward by Hunch degrees and the neck lifts the head back up.
 */
USTRUCT()
struct FM80PedoneProxy : public FAnimInstanceProxy
{
	GENERATED_BODY()

	FM80PedoneProxy() = default;
	FM80PedoneProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance) {}

	virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override;
	virtual void CacheBones() override;
	virtual bool Evaluate(FPoseContext& Output) override;

private:
	void Sample(UAnimSequence* Seq, double Time, FCompactPose& Out, FBlendedCurve& Curve, const FPoseContext& Like) const;
	void Rotate(FPoseContext& Output, FName Bone, const FVector& CSAxis, float Degrees);
	float ClipSpeed(UAnimSequence* Seq);

	UAnimSequence* Walk = nullptr;
	UAnimSequence* Legs = nullptr;
	UAnimSequence* Idle = nullptr;
	UAnimSequence* Talk = nullptr;
	UAnimSequence* Trip = nullptr;
	TMap<UAnimSequence*, float> Speeds;
	double WalkTime = 0.0;
	double LegsTime = 0.0;
	double IdleTime = 0.0;
	double TalkTime = 0.0;
	float TripTime = -1.f;
	float Speed = 0.f;
	float Hunch = 0.f;
	float TalkWeight = 0.f;
	float StrideScale = 1.f;
	bool bStarted = false;
	TMap<FName, FCompactPoseBoneIndex> Bones;
	TArray<bool> LegBone;   // by compact bone index: pelvis and legs, taken from Legs
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
 * retargets from the mannequin, face, hair and clothes follow the body. Walks about by itself (AM80PedoneAI), stops to
 * chat with others, now and then trips and falls; may carry a walking stick or a bag.
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

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Pedone")
	EM80Andatura Andatura = EM80Andatura::Auto;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Pedone")
	EM80Accessorio Accessorio = EM80Accessorio::Auto;

	/** Degrees the back is bent forward on top of the walk; < 0: from the character. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Pedone")
	float Hunch = -1.f;

	/** Walking speed (cm/s); <= 0: from the walk. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Pedone")
	float Passo = 0.f;

	/** How far from where it started it wanders (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Pedone")
	float Raggio = 2500.f;

	/** Chance of tripping over, per minute of walking. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Pedone")
	float CadutePerMinuto = 0.02f;

	/** Chance of stopping for a chat when someone free is near, at each stop. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Pedone")
	float VogliaDiParlare = 0.4f;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Pedone")
	EM80Stato Stato = EM80Stato::Libero;

	UFUNCTION(BlueprintPure, Category = "Pedone")
	bool IsOld() const { return Personaggio.ToString().StartsWith(TEXT("Anzian")); }

	float GetHunch() const { return HunchNow; }
	FVector GetHome() const { return Home; }
	float GetTripTime() const { return Stato == EM80Stato::Caduto ? TripTime : -1.f; }
	/** The body's legs against the mannequin's (pelvis heights): its steps are that much shorter or longer. */
	UFUNCTION(BlueprintPure, Category = "Pedone")
	float GetPassoScala() const { return PassoScala; }

	/** The clips the animation plays (chosen in BeginPlay; the chat clip for each chat). */
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> AnimCammina;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> AnimGambe;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> AnimFermo;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> AnimParla;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> AnimInciampo;

	/** Chatting: faces the other one with one of the chat clips. */
	void BeginChat(AM80Pedone* Other);
	void EndChat();
	AM80Pedone* GetCompagno() const { return Compagno.Get(); }

	/** Trip timeline (seconds): the clip, lying on the ground, getting up (the fall backwards), back to standing. */
	static constexpr float TripLie = 3.5f;
	static constexpr float TripRise = 0.8f;      // playback rate of the fall backwards
	static constexpr float TripRiseFrom = 0.45f; // down to this fraction of the clip
	static constexpr float TripBlend = 0.6f;
	static float TripTotal(float Length) { return Length + TripLie + Length * (1.f - TripRiseFrom) / TripRise + TripBlend; }

	/** Spawns a townsperson already set to InPersonaggio (it dresses on BeginPlay, so the name must come first). */
	UFUNCTION(BlueprintCallable, Category = "Pedone", meta = (WorldContext = "WorldContext"))
	static AM80Pedone* SpawnPedone(UObject* WorldContext, FName InPersonaggio, const FTransform& Where);

	/** Builds the navigation mesh inside the world's NavMeshBoundsVolumes now (creating it if missing); false if none. */
	UFUNCTION(BlueprintCallable, Category = "Pedone", meta = (WorldContext = "WorldContext"))
	static bool BuildNavigation(UObject* WorldContext);

	/** Trips now (tests). */
	UFUNCTION(BlueprintCallable, Category = "Pedone")
	void Inciampa();

protected:
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

private:
	/** Copies body, face, grooms, clothes and LOD sync of the built MetaHuman Blueprint onto this character. */
	void Dress();
	void Choose();
	void Carry();

	FVector Home = FVector::ZeroVector;
	float HunchNow = 0.f;
	float PassoScala = 1.f;
	float TripTime = 0.f;
	TWeakObjectPtr<AM80Pedone> Compagno;
	UPROPERTY(Transient)
	TObjectPtr<USkeletalMeshComponent> Corpo;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMeshComponent> Oggetto;
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

	/** Falls per minute for each person (0: nobody trips). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Folla")
	float CadutePerMinuto = 0.02f;

	/** Chance of stopping for a chat at each stop when someone is near (0: nobody chats). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Folla", meta = (ClampMin = "0", ClampMax = "1"))
	float VogliaDiParlare = 0.4f;

protected:
	virtual void BeginPlay() override;
};

/**
 * Walks its pedestrian to random reachable points around its starting place, stopping a few seconds at each; at a
 * stop it may call someone free nearby for a chat (the other one walks up to it), then both go on.
 */
UCLASS()
class MAZZARINOGAMEPLAY_API AM80PedoneAI : public AAIController
{
	GENERATED_BODY()

public:
	virtual void OnPossess(APawn* InPawn) override;
	virtual void OnMoveCompleted(FAIRequestID RequestID, const FPathFollowingResult& Result) override;

	/** Free and waiting between two walks (can be called for a chat). */
	bool IsWaiting() const;
	/** Stops whatever it was doing (a chat, a trip) and goes on walking after Delay seconds. */
	void Resume(float Delay);
	/** Called for a chat: walks up to Caller. */
	void ComeToChat(AM80Pedone* Caller);

private:
	void Next();
	bool TryChat();
	FTimerHandle Wait;
	FTimerHandle ChatEnd;
};
