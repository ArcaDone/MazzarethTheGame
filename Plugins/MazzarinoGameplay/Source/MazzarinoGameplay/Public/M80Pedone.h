#pragma once

#include "CoreMinimal.h"
#include "AIController.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "GameFramework/Character.h"
#include "M80Pedone.generated.h"

class AM80Car;
class ATargetPoint;
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
	Investito,   // hit by a car: thrown down, lies, gets up (or not, if the car was fast)
	Difende,     // hit by someone: faces them and punches back
	Scappa,      // hit or scared (a shot): runs away
	VaASedersi,  // walking to a chair
	Seduto,      // sitting down, sitting, getting up
	VaAllAuto,   // walking to a parked car
	InAuto,      // getting in, driving, getting out
	Morto,       // knocked out for good
};

/** How a townsperson walks. */
UENUM(BlueprintType)
enum class EM80Andatura : uint8
{
	Auto,            // from the character (see AM80Pedone::BeginPlay)
	Normale,         // the mannequin's walk
	Vecchio,         // the old man's slow stooped walk
	VecchioTrascina, // the old man's walk with short shuffling steps (the feet hardly leave the ground)
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

/** One step of what a townsperson acts out (falls, gets up, sits, gets in a car, punches). */
USTRUCT()
struct FM80Mossa
{
	GENERATED_BODY()

	UPROPERTY()
	TObjectPtr<UAnimSequence> Clip;
	float Da = 0.f;          // clip time it starts from (s)
	float A = -1.f;          // clip time it ends at (s); < 0: the clip's end
	float Rate = 1.f;
	float Tieni = 0.f;       // then held (the last frame, or looping) this long; < 0: until something else is played
	float Fondi = 0.25f;     // blend in from the previous step (s)
	bool bLoop = false;      // loops while held
	bool bRadice = false;    // the capsule follows the clip's root (travel and turning)
	bool bBusto = false;     // upper body only: the legs keep walking

	float Fine() const;
	float Durata() const { return Tieni < 0.f ? TNumericLimits<float>::Max() : (Fine() - Da) / FMath::Max(Rate, 0.01f) + Tieni; }
	/** Clip time at T seconds into the step. */
	float TempoClip(float T) const;
};

/** What the animation needs of the step being acted out (filled by AM80Pedone::GetPosaMossa). */
struct FM80PosaMossa
{
	UAnimSequence* Clip = nullptr;
	float Tempo = 0.f;
	UAnimSequence* Prima = nullptr;   // the step before, held at its end, while this one blends in
	float TempoPrima = 0.f;
	float Fondi = 1.f;
	bool bBusto = false;
};

/**
 * A townsperson's animation, light enough for many of them (no motion matching): the walk played as fast as the
 * character moves (shorter steps for the shuffling old), the run when running, the standing idle when still, blended by
 * speed; a chat clip over it while chatting; whatever it is acting out (AM80Pedone::Recita) over all of it. Old people
 * are bent a little more: the spine leans forward by Hunch degrees and the neck lifts the head back up. The fingers close
 * on what the right hand holds; a blow makes the body flinch.
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
	void Grip(FPoseContext& Output, float Weight);
	float ClipSpeed(UAnimSequence* Seq);
	void Locomotion(FPoseContext& Output);
	void Act(FPoseContext& Output);
	void RelaxFingers(FPoseContext& Output);

	UAnimSequence* Walk = nullptr;
	UAnimSequence* Legs = nullptr;
	UAnimSequence* Run = nullptr;
	UAnimSequence* Idle = nullptr;
	UAnimSequence* Relaxed = nullptr;
	UAnimSequence* Talk = nullptr;
	TMap<UAnimSequence*, float> Speeds;
	double WalkTime = 0.0;
	double LegsTime = 0.0;
	double RunTime = 0.0;
	double IdleTime = 0.0;
	double TalkTime = 0.0;
	float Speed = 0.f;
	float Hunch = 0.f;
	float TalkWeight = 0.f;
	float StrideScale = 1.f;
	float Stride = 1.f;          // 1: the clip's steps; less: shorter steps (the shuffling old)
	float GripWeight = 0.f;
	float Flinch = 0.f;
	bool bStarted = false;
	// What is being acted out, and the last of it while it blends back out.
	FM80PosaMossa Mossa;
	float ActWeight = 0.f;
	UAnimSequence* LastClip = nullptr;
	float LastTime = 0.f;
	bool bLastBusto = false;
	TMap<FName, FCompactPoseBoneIndex> Bones;
	TArray<bool> LegBone;   // by compact bone index: pelvis and legs
	// The fingers of the mannequin's own idle (the Mixamo clips bend them into claws), taken once.
	TArray<FCompactPoseBoneIndex> FingerBones;
	TArray<FTransform> RelaxedFingers;
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
 * chat with others, sits on the chairs of the square, drives the parked cars about; now and then trips and falls; may
 * carry a walking stick or a bag. Hit, it fights back or runs away (by its nerve); a shot nearby scares it away; a car
 * knocks it down.
 */
UCLASS(meta = (DisplayName = "Pedone (Mazzarino)"))
class MAZZARINOGAMEPLAY_API AM80Pedone : public ACharacter
{
	GENERATED_BODY()
	friend class AM80PedoneAI;

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

	/** Chance of going to sit on a free chair nearby, at each stop. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Pedone")
	float VogliaDiSedersi = 0.25f;

	/** Chance of taking a free parked car nearby for a drive, at each stop (< 0: from the character; the old do not drive). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Pedone")
	float VogliaDiGuidare = -1.f;

	/** Hit by someone: chance of fighting back instead of running away (< 0: from the character). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Pedone")
	float Coraggio = -1.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Pedone")
	float Salute = 100.f;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Pedone")
	EM80Stato Stato = EM80Stato::Libero;

	UFUNCTION(BlueprintPure, Category = "Pedone")
	bool IsOld() const { return Personaggio.ToString().StartsWith(TEXT("Anzian")); }

	float GetHunch() const { return HunchNow; }
	float GetStride() const { return Stride; }
	FVector GetHome() const { return Home; }
	bool IsGripping() const { return Oggetto != nullptr; }
	float GetFlinch() const { return Flinch; }
	/** The body's legs against the mannequin's (pelvis heights): its steps are that much shorter or longer. */
	UFUNCTION(BlueprintPure, Category = "Pedone")
	float GetPassoScala() const { return PassoScala; }

	/** The clips the animation plays (chosen in BeginPlay; the chat clip for each chat). */
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> AnimCammina;
	/** The legs (and pelvis) of the walk from another clip (the old: the mannequin's straight legs, short steps). */
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> AnimGambe;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> AnimCorsa;
	/** The mannequin's idle: its relaxed fingers, and the legs the short steps start from. */
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> AnimRilassato;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> AnimFermo;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> AnimParla;

	/** Acting out: the steps one after the other, then Poi. Replaces whatever was being acted out. */
	void Recita(const TArray<FM80Mossa>& InMosse, TFunction<void()> Poi = nullptr);
	void SmettiMosse();
	bool IsActing() const { return Mosse.IsValidIndex(MossaN); }
	bool GetPosaMossa(FM80PosaMossa& Out) const;

	/** Chatting: faces the other one with one of the chat clips. */
	void BeginChat(AM80Pedone* Other);
	void EndChat();
	AM80Pedone* GetCompagno() const { return Compagno.Get(); }

	/** Spawns a townsperson already set to InPersonaggio (it dresses on BeginPlay, so the name must come first). */
	UFUNCTION(BlueprintCallable, Category = "Pedone", meta = (WorldContext = "WorldContext"))
	static AM80Pedone* SpawnPedone(UObject* WorldContext, FName InPersonaggio, const FTransform& Where);

	/** Builds the navigation mesh inside the world's NavMeshBoundsVolumes now (creating it if missing); false if none. */
	UFUNCTION(BlueprintCallable, Category = "Pedone", meta = (WorldContext = "WorldContext"))
	static bool BuildNavigation(UObject* WorldContext);

	/** Something frightening at Where (a shot): the townspeople within Radius run away from it. */
	UFUNCTION(BlueprintCallable, Category = "Pedone", meta = (WorldContext = "WorldContext"))
	static void Spaventa(UObject* WorldContext, FVector Where, float Radius, AActor* Source);

	/** Trips now (tests). */
	UFUNCTION(BlueprintCallable, Category = "Pedone")
	void Inciampa();

	/** Hit by a car going at Kmh towards Direction (tests call it too). */
	UFUNCTION(BlueprintCallable, Category = "Pedone")
	void Investi(FVector Direction, float Kmh, AActor* Car);

	/** Goes to sit on Chair (a chair tagged M80Sedia, standing, facing the way one sits on it); false if it cannot get there. */
	UFUNCTION(BlueprintCallable, Category = "Pedone")
	bool VaiASedere(AActor* Chair);

	/** Chairs are physics objects (pushed by people and cars): one sat on is held still and marked taken (M80Occupata). */
	static void TieniSedia(AActor* Chair, bool bSeated);
	/** A chair that can be sat on: tagged M80Sedia, standing up, free. */
	static bool SediaLibera(const AActor* Chair);
	/** Where one stands to sit down on Chair with Clip (it steps back onto the seat), at the height of From. */
	static FVector DoveSedersi(const AActor* Chair, const ACharacter* Who, UAnimSequence* SitClip, float To);

	/** Walks to Car, gets in, drives it about for Seconds, parks and gets out; false if it cannot get there. */
	UFUNCTION(BlueprintCallable, Category = "Pedone")
	bool VaiAGuidare(AM80Car* Car, float Seconds = 60.f);

	/** Gets out of the car it drives (at once if bSubito: pulled out by the player, it then runs away). */
	void Scendi(bool bSubito);

	/** Hit by Who: fights back or runs away. */
	void Reagisci(AActor* Who, bool bForzaFuga = false);

	/** A car wants to pass, comes at it, or it is about to walk into one: steps out of its way (and ends a chat in the
	 *  road); hurrying if the car is fast. */
	void Scansati(const AActor* Car, bool bFast = false);

	/** The chair it sits on or walks to, the car it drives or walks to (tests). */
	UFUNCTION(BlueprintPure, Category = "Pedone")
	AActor* GetSedia() const { return Sedia.Get(); }
	UFUNCTION(BlueprintPure, Category = "Pedone")
	AM80Car* GetAuto() const { return Auto.Get(); }

	virtual float TakeDamage(float DamageAmount, struct FDamageEvent const& DamageEvent, AController* EventInstigator, AActor* DamageCauser) override;

protected:
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

private:
	/** Copies body, face, grooms, clothes and LOD sync of the built MetaHuman Blueprint onto this character. */
	void Dress();
	void Choose();
	void Carry();
	void TickMosse(float DeltaSeconds);
	void TickDifende(float DeltaSeconds);
	void TickAuto(float DeltaSeconds);
	void CheckCars(float DeltaSeconds);
	void Rialzati(UAnimSequence* Caduta, float FineCaduta, float Distesa);
	void Muori(UAnimSequence* Caduta, float Da);
	void Torna(float Delay);
	void Capsula(bool bOn);
	void Siediti();
	void Sali();
	void Guida();

	FVector Home = FVector::ZeroVector;
	float HunchNow = 0.f;
	float Stride = 1.f;
	float WalkSpeed = 120.f;
	float PassoScala = 1.f;
	float Flinch = 0.f;
	float CarCheck = 0.f;
	float StateTime = 0.f;
	float PunchWait = 0.f;
	float MakeWayWait = 0.f;
	/** Getting out: the body starts seated as high as the clip's car seat (higher than ours) and comes down to it. */
	float ExitDrop = 0.f;
	bool bPunchHit = false;
	float GuidaSecondi = 60.f;
	TWeakObjectPtr<AM80Pedone> Compagno;
	TWeakObjectPtr<AActor> Nemico;
	TWeakObjectPtr<AActor> Sedia;
	TWeakObjectPtr<AM80Car> Auto;
	UPROPERTY(Transient)
	TArray<FM80Mossa> Mosse;
	int32 MossaN = INDEX_NONE;
	float MossaT = 0.f;
	TFunction<void()> DopoMosse;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> MossaPrima;
	float MossaPrimaT = 0.f;
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

	/** Chance of sitting on a free chair at each stop (0: nobody sits). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Folla", meta = (ClampMin = "0", ClampMax = "1"))
	float VogliaDiSedersi = 0.25f;

	/** Chance of taking a free parked car at each stop, for the adults and the young (0: nobody drives). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Folla", meta = (ClampMin = "0", ClampMax = "1"))
	float VogliaDiGuidare = 0.08f;

protected:
	virtual void BeginPlay() override;
};

/**
 * Walks its pedestrian to random reachable points around its starting place, stopping a few seconds at each; at a
 * stop it may call someone free nearby for a chat (the other one walks up to it), go and sit on a free chair, or take a
 * free parked car for a drive, then goes on.
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
	/** Stops whatever it was doing (a chat, a trip) and goes on walking after Delay seconds; < 0: only stops. */
	void Resume(float Delay);
	/** Called for a chat: walks up to Caller. */
	void ComeToChat(AM80Pedone* Caller);

private:
	void Next();
	bool TryChat();
	bool TrySit();
	bool TryDrive();
	FTimerHandle Wait;
	FTimerHandle ChatEnd;
};

/**
 * Drives a townsperson's car: possesses the AM80Car, follows the navigation paths to random places around where it
 * started (slowly, slowing in the bends, braking for people and honking at whoever stays in the way), and after the
 * given time stops, puts the handbrake on and lets the driver get out. Pulled out by the player, the driver runs away.
 */
UCLASS()
class MAZZARINOGAMEPLAY_API AM80AutistaAI : public AAIController
{
	GENERATED_BODY()

public:
	AM80AutistaAI();
	virtual void Tick(float DeltaSeconds) override;
	virtual void OnUnPossess() override;

	void Guida(AM80Car* Car, AM80Pedone* Driver, float Seconds, float Radius);
	bool IsParked() const { return bParked; }

	/** Cruising speed (km/h): a town in the 80s. */
	float Kmh = 28.f;

	/** What it is doing, for the tests (path point, speeds, inputs, blocked/stuck timers). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Autista")
	FString Diario;

private:
	void NewGoal();
	TWeakObjectPtr<AM80Pedone> Driver;
	TArray<FVector> Path;
	int32 Point = 0;
	FVector Home = FVector::ZeroVector;
	float Radius = 4000.f;
	float Time = 0.f;
	float MaxTime = 60.f;
	float Blocked = 0.f;
	float Stuck = 0.f;
	float Reverse = 0.f;
	float HornWait = 0.f;
	bool bParking = false;
	bool bParked = false;
};
