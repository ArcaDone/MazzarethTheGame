#include "M80Pedone.h"
#include "Animation/AnimSequence.h"
#include "AnimationRuntime.h"
#include "Animation/AnimationPoseData.h"
#include "Animation/AttributesRuntime.h"
#include "Components/BillboardComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/LODSyncComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "Engine/Engine.h"
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/TargetPoint.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "Navigation/PathFollowingComponent.h"
#include "NavigationSystem.h"
#include "TimerManager.h"

namespace
{
// Component space of the UEFN mannequin: the character looks along +Y, +X is its left, +Z up.
const FVector CSLeft(1.f, 0.f, 0.f);
const TCHAR* const MannequinPath = TEXT("/Game/Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin.SKM_UEFN_Mannequin");
const TCHAR* const RetargetAnimPath = TEXT("/Game/Blueprints/RetargetedCharacters/ABP_GenericRetarget.ABP_GenericRetarget_C");
const TCHAR* const WalkPath = TEXT("/Game/Characters/UEFN_Mannequin/Animations/Walk/M_Neutral_Walk_Loop_F.M_Neutral_Walk_Loop_F");
const TCHAR* const IdlePath = TEXT("/Game/Characters/UEFN_Mannequin/Animations/Idle/M_Neutral_Stand_Idle_Loop.M_Neutral_Stand_Idle_Loop");

/** A crowd clip (Scripts/m80_folla_animazioni.py: the user's Mixamo clips retargeted onto the mannequin). */
UAnimSequence* Clip(const TCHAR* Name)
{
	const FString Path = FString::Printf(TEXT("/Game/Mazzarino80/Personaggi/Animazioni/A_M80_Folla_%s.A_M80_Folla_%s"), Name, Name);
	return LoadObject<UAnimSequence>(nullptr, *Path, nullptr, LOAD_NoWarn);
}

UAnimSequence* Asset(const TCHAR* Path)
{
	return LoadObject<UAnimSequence>(nullptr, Path, nullptr, LOAD_NoWarn);
}

bool IsLegBone(const FString& Name)
{
	return Name == TEXT("pelvis") || Name.StartsWith(TEXT("thigh")) || Name.StartsWith(TEXT("calf")) || Name.StartsWith(TEXT("foot"))
		|| Name.StartsWith(TEXT("ball")) || Name.StartsWith(TEXT("ik_foot"));
}
}

// ---------------------------------------------------------------------------------------------
// Animation

float FM80PedoneProxy::ClipSpeed(UAnimSequence* Seq)
{
	if (const float* S = Speeds.Find(Seq))
	{
		return *S;
	}
	// The clip's own speed, from its root motion: the feet do not slide at any walking speed.
	float S = 150.f;
	if (Seq && Seq->GetPlayLength() > 0.f)
	{
		const FTransform Root = Seq->ExtractRootMotionFromRange(0.0, Seq->GetPlayLength(), FAnimExtractContext());
		const float Travel = Root.GetTranslation().Size2D() / Seq->GetPlayLength();
		S = Travel > 10.f ? Travel : 150.f;
	}
	Speeds.Add(Seq, S);
	return S;
}

void FM80PedoneProxy::PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds)
{
	FAnimInstanceProxy::PreUpdate(InAnimInstance, DeltaSeconds);
	const AM80Pedone* P = Cast<AM80Pedone>(InAnimInstance->GetOwningActor());
	if (!P)
	{
		return;
	}
	Walk = P->AnimCammina;
	Legs = P->AnimGambe;
	Idle = P->AnimFermo;
	Trip = P->AnimInciampo;
	if (P->AnimParla != Talk)
	{
		Talk = P->AnimParla;
		TalkTime = Talk ? FMath::FRand() * Talk->GetPlayLength() * 0.5f : 0.f;
	}
	if (!bStarted)
	{
		// Each one starts at a different point of the loops, or a crowd walks in step.
		bStarted = true;
		WalkTime = LegsTime = FMath::FRand() * 10.0;
		IdleTime = FMath::FRand() * 10.0;
	}
	Speed = P->GetVelocity().Size2D();
	Hunch = P->GetHunch();
	StrideScale = FMath::Max(P->GetPassoScala(), 0.5f);
	TripTime = P->GetTripTime();
	TalkWeight = FMath::FInterpConstantTo(TalkWeight, P->Stato == EM80Stato::Parla ? 1.f : 0.f, DeltaSeconds, 1.5f);
	// The body's retarget shortens the steps of a shorter body: the clip plays that much faster, or the feet slide.
	if (Walk)
	{
		WalkTime += DeltaSeconds * Speed / (ClipSpeed(Walk) * StrideScale);
	}
	if (Legs)
	{
		LegsTime += DeltaSeconds * Speed / (ClipSpeed(Legs) * StrideScale);
	}
	IdleTime += DeltaSeconds;
	TalkTime += DeltaSeconds;
}

void FM80PedoneProxy::CacheBones()
{
	FAnimInstanceProxy::CacheBones();
	const FBoneContainer& BC = GetRequiredBones();
	if (!BC.IsValid())
	{
		return;
	}
	const FReferenceSkeleton& Ref = BC.GetReferenceSkeleton();
	Bones.Reset();
	LegBone.Init(false, BC.GetCompactPoseNumBones());
	for (int32 i = 0; i < BC.GetCompactPoseNumBones(); ++i)
	{
		const FCompactPoseBoneIndex CI(i);
		const FName Name = Ref.GetBoneName(BC.MakeMeshPoseIndex(CI).GetInt());
		Bones.Add(Name, CI);
		LegBone[i] = IsLegBone(Name.ToString());
	}
}

void FM80PedoneProxy::Sample(UAnimSequence* Seq, double Time, FCompactPose& Out, FBlendedCurve& Curve, const FPoseContext& Like) const
{
	Out.SetBoneContainer(&Like.Pose.GetBoneContainer());
	Curve.InitFrom(Like.Curve);
	UE::Anim::FStackAttributeContainer Attributes;
	FAnimationPoseData Data(Out, Curve, Attributes);
	const double Length = FMath::Max(Seq->GetPlayLength(), 0.01f);
	Seq->GetAnimationPose(Data, FAnimExtractContext(FMath::Fmod(FMath::Max(Time, 0.0), Length), false));
	// The clips carry the root's travel: kept in place, the capsule does the moving.
	Out[FCompactPoseBoneIndex(0)] = FTransform::Identity;
}

void FM80PedoneProxy::Rotate(FPoseContext& Output, FName Bone, const FVector& CSAxis, float Degrees)
{
	const FCompactPoseBoneIndex* I = Bones.Find(Bone);
	if (!I || FMath::IsNearlyZero(Degrees))
	{
		return;
	}
	FCSPose<FCompactPose> CS;
	CS.InitPose(Output.Pose);
	const FCompactPoseBoneIndex Parent = Output.Pose.GetParentBoneIndex(*I);
	const FQuat ParentRot = Parent.IsValid() ? CS.GetComponentSpaceTransform(Parent).GetRotation() : FQuat::Identity;
	const FVector Axis = ParentRot.UnrotateVector(CSAxis).GetSafeNormal();
	FTransform& Local = Output.Pose[*I];
	Local.SetRotation((FQuat(Axis, FMath::DegreesToRadians(Degrees)) * Local.GetRotation()).GetNormalized());
}

bool FM80PedoneProxy::Evaluate(FPoseContext& Output)
{
	if (!Walk || !Idle)
	{
		Output.ResetToRefPose();
		return true;
	}
	FCompactPose A, B, C;
	FBlendedCurve CA, CB, CC;
	float Bend = Hunch;
	if (TripTime >= 0.f && Trip)
	{
		// Tripped: the fall, held on the ground, then the fall backwards (getting up), then back to standing.
		const float L = Trip->GetPlayLength();
		const float RiseStart = L + AM80Pedone::TripLie;
		const float RiseEnd = RiseStart + L * (1.f - AM80Pedone::TripRiseFrom) / AM80Pedone::TripRise;
		float At = TripTime;
		float ToIdle = 0.f;
		if (TripTime >= L && TripTime < RiseStart)
		{
			At = L - 0.01f;
		}
		else if (TripTime >= RiseStart && TripTime < RiseEnd)
		{
			At = L - (TripTime - RiseStart) * AM80Pedone::TripRise;
		}
		else if (TripTime >= RiseEnd)
		{
			At = L * AM80Pedone::TripRiseFrom;
			ToIdle = FMath::Clamp((TripTime - RiseEnd) / AM80Pedone::TripBlend, 0.f, 1.f);
		}
		Sample(Trip, FMath::Min(At, L - 0.01f), Output.Pose, Output.Curve, Output);
		if (ToIdle > 0.f)
		{
			Sample(Idle, IdleTime, A, CA, Output);
			for (FCompactPoseBoneIndex I : Output.Pose.ForEachBoneIndex())
			{
				Output.Pose[I].BlendWith(A[I], ToIdle);
			}
		}
		Bend *= ToIdle;
	}
	else
	{
		const float W = FMath::Clamp((Speed - 10.f) / 50.f, 0.f, 1.f);
		if (W < 1.f)
		{
			Sample(Idle, IdleTime, A, CA, Output);
		}
		if (W > 0.f)
		{
			Sample(Walk, WalkTime, B, CB, Output);
			if (Legs)
			{
				// The legs (and pelvis) from another walk: the old dragging their feet under an ordinary upper body.
				Sample(Legs, LegsTime, C, CC, Output);
				for (FCompactPoseBoneIndex I : B.ForEachBoneIndex())
				{
					if (LegBone.IsValidIndex(I.GetInt()) && LegBone[I.GetInt()])
					{
						B[I] = C[I];
					}
				}
			}
		}
		for (FCompactPoseBoneIndex I : Output.Pose.ForEachBoneIndex())
		{
			if (W <= 0.f)
			{
				Output.Pose[I] = A[I];
			}
			else if (W >= 1.f)
			{
				Output.Pose[I] = B[I];
			}
			else
			{
				FTransform T = A[I];
				T.BlendWith(B[I], W);
				Output.Pose[I] = T;
			}
		}
		Output.Curve.InitFrom(W > 0.f ? CB : CA);
		if (TalkWeight > 0.f && Talk)
		{
			Sample(Talk, TalkTime, C, CC, Output);
			for (FCompactPoseBoneIndex I : Output.Pose.ForEachBoneIndex())
			{
				Output.Pose[I].BlendWith(C[I], TalkWeight);
			}
			Bend *= 1.f - 0.5f * TalkWeight;
		}
	}
	// Old people: the back bent forward (more in the upper back), the head lifted to look ahead. A positive turn about
	// CSLeft swings a bone hanging down forward (the arms in M80OverlayAnim), so it tips a bone pointing up backward.
	if (Bend > 0.f)
	{
		Rotate(Output, TEXT("spine_02"), CSLeft, -Bend * 0.2f);
		Rotate(Output, TEXT("spine_03"), CSLeft, -Bend * 0.3f);
		Rotate(Output, TEXT("spine_04"), CSLeft, -Bend * 0.3f);
		Rotate(Output, TEXT("spine_05"), CSLeft, -Bend * 0.2f);
		Rotate(Output, TEXT("neck_01"), CSLeft, Bend * 0.45f);
		Rotate(Output, TEXT("head"), CSLeft, Bend * 0.35f);
		// Knees a little bent, as old people walk: thighs forward, shins back, feet level again (not over the
		// dragging legs, already bent).
		for (const TCHAR* Side : {TEXT("_l"), TEXT("_r")})
		{
			if (Legs)
			{
				break;
			}
			Rotate(Output, FName(FString(TEXT("thigh")) + Side), CSLeft, Bend * 0.15f);
			Rotate(Output, FName(FString(TEXT("calf")) + Side), CSLeft, -Bend * 0.3f);
			Rotate(Output, FName(FString(TEXT("foot")) + Side), CSLeft, Bend * 0.15f);
		}
	}
	return true;
}

// ---------------------------------------------------------------------------------------------
// Pedestrian

AM80Pedone::AM80Pedone()
{
	PrimaryActorTick.bCanEverTick = true;
	static ConstructorHelpers::FObjectFinderOptional<USkeletalMesh> Mannequin(MannequinPath);
	USkeletalMeshComponent* M = GetMesh();
	M->SetSkeletalMesh(Mannequin.Get());
	M->SetAnimInstanceClass(UM80PedoneAnimInstance::StaticClass());
	M->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -90.f), FRotator(0.f, -90.f, 0.f));
	M->SetVisibility(false);   // only the MetaHuman shows; the mannequin still animates for it
	M->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	M->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	UCapsuleComponent* Cap = GetCapsuleComponent();
	Cap->InitCapsuleSize(34.f, 90.f);
	Cap->SetCollisionResponseToChannel(ECC_Pawn, ECR_Block);
	Cap->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
	UCharacterMovementComponent* Move = GetCharacterMovement();
	Move->bOrientRotationToMovement = true;
	Move->RotationRate = FRotator(0.f, 240.f, 0.f);
	Move->MaxWalkSpeed = 130.f;
	Move->BrakingDecelerationWalking = 400.f;
	Move->MaxAcceleration = 300.f;
	Move->bUseRVOAvoidance = true;   // they step around each other
	Move->AvoidanceConsiderationRadius = 200.f;
	bUseControllerRotationYaw = false;
	AIControllerClass = AM80PedoneAI::StaticClass();
	AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
}

void AM80Pedone::BeginPlay()
{
	Super::BeginPlay();
	Home = GetActorLocation();
	// People bump into the player and the player into them: the player's capsule ignores pawns in the sample's setup.
	if (ACharacter* Player = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0)))
	{
		UCapsuleComponent* Theirs = Player->GetCapsuleComponent();
		GetCapsuleComponent()->SetCollisionResponseToChannel(Theirs->GetCollisionObjectType(), ECR_Block);
		if (Theirs->GetCollisionResponseToChannel(GetCapsuleComponent()->GetCollisionObjectType()) != ECR_Block)
		{
			Theirs->SetCollisionResponseToChannel(GetCapsuleComponent()->GetCollisionObjectType(), ECR_Block);
		}
	}
	Choose();
	Dress();
	Carry();
}

void AM80Pedone::Choose()
{
	const FString Name = Personaggio.ToString();
	const int32 N = Name.Len() > 0 && FChar::IsDigit(Name[Name.Len() - 1]) ? Name[Name.Len() - 1] - TEXT('0') : 1;
	const bool bOldMan = Name.StartsWith(TEXT("Anziano"));
	const bool bOldWoman = Name.StartsWith(TEXT("Anziana"));
	const bool bYoung = Name.StartsWith(TEXT("Ragazz"));
	EM80Andatura Walk = Andatura;
	if (Walk == EM80Andatura::Auto)
	{
		if (bOldMan)
		{
			Walk = N % 2 == 1 ? EM80Andatura::VecchioTrascina : EM80Andatura::Vecchio;
		}
		else if (bOldWoman)
		{
			Walk = (N == 1 || N == 4) ? EM80Andatura::Spesa : (N == 2 ? EM80Andatura::VecchioTrascina : EM80Andatura::Vecchio);
		}
		else if (Name == TEXT("Donna1") || Name == TEXT("Donna3") || Name == TEXT("Ragazza2"))
		{
			Walk = EM80Andatura::Spesa;
		}
		else if (Name == TEXT("Uomo4") || (!bYoung && FMath::FRand() < 0.1f))
		{
			Walk = EM80Andatura::Triste;
		}
		else
		{
			Walk = EM80Andatura::Normale;
		}
	}
	EM80Accessorio Carry = Accessorio;
	if (Carry == EM80Accessorio::Auto)
	{
		Carry = EM80Accessorio::Nessuno;
		if (Walk == EM80Andatura::VecchioTrascina && bOldMan)
		{
			Carry = EM80Accessorio::Bastone;
		}
		else if (Walk == EM80Andatura::Spesa)
		{
			Carry = (bOldWoman || Name == TEXT("Donna3")) ? EM80Accessorio::BorsaSpesa : EM80Accessorio::Borsetta;
		}
	}
	Accessorio = Carry;
	Andatura = Walk;

	AnimFermo = IsOld() ? Clip(TEXT("VecchioFermo")) : Asset(IdlePath);
	AnimInciampo = Clip(TEXT("Inciampo"));
	float Speed = 120.f, Bend = 0.f;
	switch (Walk)
	{
	case EM80Andatura::Vecchio:
		AnimCammina = Clip(TEXT("VecchioCammina"));
		Speed = FMath::FRandRange(45.f, 60.f);
		Bend = 4.f;
		break;
	case EM80Andatura::VecchioTrascina:
		// The arms of the walk with a bag (the right hand still: it holds the stick), the legs of a zombie dragging
		// (the first zombie walk: the second one crouches so low the old seemed to squat).
		AnimCammina = Clip(TEXT("CamminaSpesa"));
		AnimGambe = Clip(TEXT("Trascina"));
		Speed = FMath::FRandRange(32.f, 42.f);
		Bend = 6.f;
		break;
	case EM80Andatura::Triste:
		AnimCammina = Clip(TEXT("CamminaTriste"));
		Speed = FMath::FRandRange(70.f, 85.f);
		break;
	case EM80Andatura::Spesa:
		AnimCammina = Clip(TEXT("CamminaSpesa"));
		Speed = IsOld() ? FMath::FRandRange(60.f, 72.f) : FMath::FRandRange(95.f, 110.f);
		Bend = IsOld() ? 8.f : 0.f;
		break;
	default:
		AnimCammina = Asset(WalkPath);
		Speed = bYoung ? FMath::FRandRange(130.f, 150.f) : FMath::FRandRange(110.f, 130.f);
		break;
	}
	if (!AnimCammina)
	{
		AnimCammina = Asset(WalkPath);   // the crowd clips are missing: the mannequin's walk
		AnimGambe = nullptr;
	}
	if (!AnimFermo)
	{
		AnimFermo = Asset(IdlePath);
	}
	GetCharacterMovement()->MaxWalkSpeed = Passo > 0.f ? Passo : Speed;
	HunchNow = Hunch >= 0.f ? Hunch : Bend;
}

void AM80Pedone::Carry()
{
	const TCHAR* Path = nullptr;
	switch (Accessorio)
	{
	case EM80Accessorio::Bastone: Path = TEXT("/Game/Mazzarino80/Personaggi/Accessori/SM_M80_Bastone.SM_M80_Bastone"); break;
	case EM80Accessorio::BorsaSpesa: Path = TEXT("/Game/Mazzarino80/Personaggi/Accessori/SM_M80_BorsaSpesa.SM_M80_BorsaSpesa"); break;
	case EM80Accessorio::Borsetta: Path = TEXT("/Game/Mazzarino80/Personaggi/Accessori/SM_M80_Borsetta.SM_M80_Borsetta"); break;
	default: return;
	}
	UStaticMesh* Held = LoadObject<UStaticMesh>(nullptr, Path, nullptr, LOAD_NoWarn);
	if (!Held)
	{
		return;
	}
	// Held by the fingers (where the middle finger starts); it hangs straight down whatever the hand does (Tick).
	USkeletalMeshComponent* Hand = Corpo ? Corpo.Get() : GetMesh();
	const FName Grip = Hand->DoesSocketExist(TEXT("middle_01_r")) ? FName(TEXT("middle_01_r")) : FName(TEXT("hand_r"));
	Oggetto = NewObject<UStaticMeshComponent>(this, TEXT("Oggetto"));
	Oggetto->SetStaticMesh(Held);
	Oggetto->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Oggetto->SetupAttachment(Hand, Grip);
	Oggetto->SetUsingAbsoluteRotation(true);
	Oggetto->RegisterComponent();
	AddInstanceComponent(Oggetto);
}

void AM80Pedone::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (Oggetto)
	{
		Oggetto->SetWorldRotation(FRotator(0.f, GetActorRotation().Yaw, 0.f));
	}
	AM80PedoneAI* AI = Cast<AM80PedoneAI>(GetController());
	if (Stato == EM80Stato::Caduto)
	{
		const float L = AnimInciampo ? AnimInciampo->GetPlayLength() : 0.f;
		const float Prev = TripTime;
		TripTime += DeltaSeconds;
		if (AnimInciampo && Prev < L)
		{
			// The fall carries the body forward: the capsule follows the clip's root.
			const FTransform D = AnimInciampo->ExtractRootMotionFromRange(Prev, FMath::Min(TripTime, L), FAnimExtractContext());
			FVector Move = GetMesh()->GetComponentTransform().TransformVector(D.GetTranslation());
			Move.Z = 0.f;
			AddActorWorldOffset(Move, true);
		}
		if (TripTime >= TripTotal(L))
		{
			Stato = EM80Stato::Libero;
			if (AI)
			{
				AI->Resume(FMath::FRandRange(1.f, 3.f));
			}
		}
		return;
	}
	if (Stato == EM80Stato::Libero && CadutePerMinuto > 0.f && GetVelocity().Size2D() > 30.f
		&& FMath::FRand() < CadutePerMinuto * DeltaSeconds / 60.f)
	{
		Inciampa();
	}
}

void AM80Pedone::Inciampa()
{
	if (Stato != EM80Stato::Libero || !AnimInciampo)
	{
		return;
	}
	Stato = EM80Stato::Caduto;
	TripTime = 0.f;
	if (AM80PedoneAI* AI = Cast<AM80PedoneAI>(GetController()))
	{
		AI->StopMovement();
		AI->Resume(-1.f);
	}
}

void AM80Pedone::BeginChat(AM80Pedone* Other)
{
	Compagno = Other;
	Stato = EM80Stato::Parla;
	if (Other)
	{
		SetActorRotation(FRotator(0.f, (Other->GetActorLocation() - GetActorLocation()).Rotation().Yaw, 0.f));
	}
	// Mostly talking, now and then a secret, an argument, rarely shouting.
	const float R = FMath::FRand() * 9.5f;
	AnimParla = Clip(R < 3.f ? TEXT("Parlare") : R < 6.f ? TEXT("Parlare2") : R < 8.f ? TEXT("Segreto") : R < 9.f ? TEXT("Litigare") : TEXT("Urlare"));
}

void AM80Pedone::EndChat()
{
	const bool bWasChatting = Stato == EM80Stato::Parla || Stato == EM80Stato::VaAParlare;
	Compagno = nullptr;
	if (bWasChatting)
	{
		Stato = EM80Stato::Libero;
		if (AM80PedoneAI* AI = Cast<AM80PedoneAI>(GetController()))
		{
			AI->Resume(FMath::FRandRange(0.5f, 2.5f));
		}
	}
}

AM80Pedone* AM80Pedone::SpawnPedone(UObject* WorldContext, FName InPersonaggio, const FTransform& Where)
{
	UWorld* World = GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::LogAndReturnNull);
	if (!World)
	{
		return nullptr;
	}
	AM80Pedone* P = World->SpawnActorDeferred<AM80Pedone>(StaticClass(), Where, nullptr, nullptr, ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn);
	if (P)
	{
		P->Personaggio = InPersonaggio;
		P->FinishSpawning(Where);
	}
	return P;
}

bool AM80Pedone::BuildNavigation(UObject* WorldContext)
{
	UWorld* World = GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::LogAndReturnNull);
	UNavigationSystemV1* Nav = World ? FNavigationSystem::GetCurrent<UNavigationSystemV1>(World) : nullptr;
	if (!Nav)
	{
		return false;
	}
	for (TActorIterator<ANavMeshBoundsVolume> It(World); It; ++It)
	{
		Nav->OnNavigationBoundsUpdated(*It);
	}
	// A map just opened by a script is still under the async loading lock, which makes Build() do nothing.
	Nav->RemoveNavigationBuildLock(ENavigationBuildLock::AsyncLoadLock, UNavigationSystemV1::ELockRemovalRebuildAction::NoRebuild);
	Nav->Build();
	return Nav->IsNavigationBuilt(World->GetWorldSettings());
}

void AM80Pedone::Dress()
{
	const FString Name = Personaggio.ToString();
	const FString Path = FString::Printf(TEXT("/Game/Mazzarino80/Personaggi/Folla/Build/%s/BP_%s.BP_%s_C"), *Name, *Name, *Name);
	UBlueprintGeneratedClass* Look = LoadObject<UBlueprintGeneratedClass>(nullptr, *Path, nullptr, LOAD_NoWarn);
	if (!Look || !Look->SimpleConstructionScript)
	{
		UE_LOG(LogTemp, Warning, TEXT("M80Pedone: no built MetaHuman %s"), *Path);
		return;
	}
	UClass* RetargetAnim = LoadObject<UClass>(nullptr, RetargetAnimPath, nullptr, LOAD_NoWarn);
	// The built Blueprint: Root > Body > (Face > grooms, clothes). Its components are copied with their settings;
	// the body retargets from the mannequin, the face follows it with its own animation, the clothes take its pose.
	TMap<FName, USceneComponent*> Made;
	USkeletalMeshComponent* Body = nullptr;
	TArray<USCS_Node*> Nodes = Look->SimpleConstructionScript->GetAllNodes();
	// The tree is in each node's children (ParentComponentOrVariableName only names parents from a parent class).
	TMap<USCS_Node*, USCS_Node*> ParentOf;
	for (USCS_Node* Node : Nodes)
	{
		for (USCS_Node* Child : Node ? Node->GetChildNodes() : TArray<USCS_Node*>())
		{
			ParentOf.Add(Child, Node);
		}
	}
	// Parents first: the construction script lists them in order of the tree.
	for (USCS_Node* Node : Nodes)
	{
		if (!Node || !Node->ComponentTemplate || !Node->ComponentTemplate->IsA<USceneComponent>())
		{
			continue;   // LOD sync and the MetaHuman component: below / not needed
		}
		USceneComponent* Template = Cast<USceneComponent>(Node->ComponentTemplate);
		if (Template->GetClass() == USceneComponent::StaticClass())
		{
			Made.Add(Node->GetVariableName(), GetMesh());   // the Root: our mannequin
			continue;
		}
		const bool bSkinned = Template->IsA<USkeletalMeshComponent>();
		const bool bGroom = Template->GetClass()->GetName().Contains(TEXT("Groom"));
		if (!bSkinned && !bGroom)
		{
			continue;
		}
		USceneComponent* C = NewObject<USceneComponent>(this, Template->GetClass(), Node->GetVariableName(), RF_NoFlags, Template);
		USCS_Node* const* ParentNode = ParentOf.Find(Node);
		USceneComponent* const* Parent = ParentNode ? Made.Find((*ParentNode)->GetVariableName()) : nullptr;
		C->SetupAttachment(Parent ? *Parent : GetMesh(), Node->AttachToName);
		Made.Add(Node->GetVariableName(), C);
		if (USkeletalMeshComponent* S = Cast<USkeletalMeshComponent>(C))
		{
			S->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			S->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
			if (Node->GetVariableName() == TEXT("Body"))
			{
				Body = S;
				// ABP_GenericRetarget picks its IK Retargeter by the component's first tag; without one it does not move.
				S->ComponentTags.Insert(TEXT("RTG_UEFN_to_Metahuman_nrw"), 0);
				S->SetAnimInstanceClass(RetargetAnim);
				S->SetRelativeTransform(FTransform::Identity);
			}
		}
		C->RegisterComponent();
		AddInstanceComponent(C);
	}
	if (!Body)
	{
		return;
	}
	Corpo = Body;
	Body->AddTickPrerequisiteComponent(GetMesh());
	// How much longer or shorter its legs are than the mannequin's (the retarget scales the steps by the pelvis height).
	auto PelvisHeight = [](const USkinnedMeshComponent* C)
	{
		const FReferenceSkeleton& Ref = C->GetSkinnedAsset()->GetRefSkeleton();
		const int32 I = Ref.FindBoneIndex(TEXT("pelvis"));
		return I == INDEX_NONE ? 0.f : float(FAnimationRuntime::GetComponentSpaceTransformRefPose(Ref, I).GetLocation().Z);
	};
	const float Mine = Body->GetSkinnedAsset() ? PelvisHeight(Body) : 0.f;
	const float Theirs = GetMesh()->GetSkinnedAsset() ? PelvisHeight(GetMesh()) : 0.f;
	PassoScala = Mine > 1.f && Theirs > 1.f ? FMath::Clamp(Mine / Theirs, 0.6f, 1.4f) : 1.f;
	for (const TPair<FName, USceneComponent*>& It : Made)
	{
		USkeletalMeshComponent* S = Cast<USkeletalMeshComponent>(It.Value);
		if (S && S != Body && S != GetMesh() && !S->GetAnimClass())
		{
			S->SetLeaderPoseComponent(Body);   // clothes
		}
		else if (S && S != Body && S != GetMesh())
		{
			S->AddTickPrerequisiteComponent(Body);   // the face
		}
	}
	// The Blueprint's LOD sync: body and face drive, clothes and hair follow with their own LOD mapping (the hair's
	// cards start at its LOD 3: without the mapping the hair, and with it the hat, shows at the wrong LODs).
	for (USCS_Node* Node : Nodes)
	{
		if (ULODSyncComponent* Template = Cast<ULODSyncComponent>(Node ? Node->ComponentTemplate : nullptr))
		{
			ULODSyncComponent* Sync = NewObject<ULODSyncComponent>(this, Template->GetClass(), Node->GetVariableName(), RF_NoFlags, Template);
			Sync->RegisterComponent();
			AddInstanceComponent(Sync);
		}
	}
}

// ---------------------------------------------------------------------------------------------
// Crowd

AM80Folla::AM80Folla()
{
	PrimaryActorTick.bCanEverTick = false;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
#if WITH_EDITORONLY_DATA
	if (UBillboardComponent* Icon = CreateEditorOnlyDefaultSubobject<UBillboardComponent>(TEXT("Icona")))
	{
		Icon->SetupAttachment(RootComponent);
	}
#endif
	for (const TCHAR* Name : {TEXT("Anziano1"), TEXT("Anziana1"), TEXT("Uomo1"), TEXT("Donna1"), TEXT("Ragazzo1"), TEXT("Ragazza1"),
							  TEXT("Anziano2"), TEXT("Anziana2"), TEXT("Uomo2"), TEXT("Donna2"), TEXT("Ragazzo2"), TEXT("Ragazza2"),
							  TEXT("Anziano3"), TEXT("Anziana3"), TEXT("Uomo3"), TEXT("Donna3"), TEXT("Ragazzo3"), TEXT("Ragazza3"),
							  TEXT("Anziano4"), TEXT("Anziana4"), TEXT("Uomo4")})
	{
		Personaggi.Add(Name);
	}
}

void AM80Folla::BeginPlay()
{
	Super::BeginPlay();
	if (Personaggi.IsEmpty())
	{
		return;
	}
	TArray<FVector> Spots;
	if (bUsaSegnaposto)
	{
		for (TActorIterator<ATargetPoint> It(GetWorld()); It; ++It)
		{
			if (It->Tags.ContainsByPredicate([](const FName& T) { return T.ToString().StartsWith(TEXT("M80Folla_")); }))
			{
				Spots.Add(It->GetActorLocation());
			}
		}
	}
	FRandomStream Rand(Seme);
	UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	for (int32 i = 0; i < Quanti; ++i)
	{
		FVector At = Spots.Num() > 0
			? Spots[Rand.RandRange(0, Spots.Num() - 1)] + FVector(Rand.FRandRange(-250.f, 250.f), Rand.FRandRange(-250.f, 250.f), 0.f)
			: GetActorLocation() + FVector(Rand.GetUnitVector().GetSafeNormal2D() * Rand.FRandRange(0.f, Raggio));
		FNavLocation OnNav;
		if (Nav && Nav->ProjectPointToNavigation(At, OnNav, FVector(300.f, 300.f, 500.f)))
		{
			At = OnNav.Location;
		}
		const FTransform Where(FRotator(0.f, Rand.FRandRange(0.f, 360.f), 0.f), At + FVector(0.f, 0.f, 95.f));
		AM80Pedone* P = GetWorld()->SpawnActorDeferred<AM80Pedone>(AM80Pedone::StaticClass(), Where, this, nullptr, ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn);
		if (P)
		{
			P->Personaggio = Personaggi[i % Personaggi.Num()];
			P->Raggio = Raggio;
			P->CadutePerMinuto = CadutePerMinuto;
			P->VogliaDiParlare = VogliaDiParlare;
			P->FinishSpawning(Where);
		}
	}
}

// ---------------------------------------------------------------------------------------------
// Walking about

void AM80PedoneAI::OnPossess(APawn* InPawn)
{
	Super::OnPossess(InPawn);
	// A first pause of a few seconds, different for each: the crowd does not start all at once.
	GetWorldTimerManager().SetTimer(Wait, this, &AM80PedoneAI::Next, FMath::FRandRange(0.2f, 3.f), false);
}

bool AM80PedoneAI::IsWaiting() const
{
	const AM80Pedone* P = Cast<AM80Pedone>(GetPawn());
	return P && P->Stato == EM80Stato::Libero && GetMoveStatus() == EPathFollowingStatus::Idle && GetWorldTimerManager().IsTimerActive(Wait);
}

void AM80PedoneAI::Resume(float Delay)
{
	GetWorldTimerManager().ClearTimer(Wait);
	GetWorldTimerManager().ClearTimer(ChatEnd);
	if (Delay >= 0.f)
	{
		GetWorldTimerManager().SetTimer(Wait, this, &AM80PedoneAI::Next, FMath::Max(Delay, 0.05f), false);
	}
}

void AM80PedoneAI::OnMoveCompleted(FAIRequestID RequestID, const FPathFollowingResult& Result)
{
	Super::OnMoveCompleted(RequestID, Result);
	AM80Pedone* P = Cast<AM80Pedone>(GetPawn());
	if (!P || P->Stato == EM80Stato::Caduto || P->Stato == EM80Stato::Parla)
	{
		return;
	}
	if (P->Stato == EM80Stato::VaAParlare)
	{
		// Walked up to whoever called: the chat starts, both facing each other, for a while.
		AM80Pedone* Other = P->GetCompagno();
		if (Other && Other->Stato == EM80Stato::VaAParlare && Other->GetCompagno() == P
			&& FVector::Dist2D(Other->GetActorLocation(), P->GetActorLocation()) < 250.f)
		{
			P->BeginChat(Other);
			Other->BeginChat(P);
			TWeakObjectPtr<AM80Pedone> A(P), B(Other);
			GetWorldTimerManager().SetTimer(ChatEnd, FTimerDelegate::CreateWeakLambda(this, [A, B]()
			{
				if (A.IsValid()) { A->EndChat(); }
				if (B.IsValid()) { B->EndChat(); }
			}), FMath::FRandRange(8.f, 25.f), false);
		}
		else
		{
			P->EndChat();
			if (Other && Other->GetCompagno() == P)
			{
				Other->EndChat();
			}
		}
		return;
	}
	if (!TryChat())
	{
		GetWorldTimerManager().SetTimer(Wait, this, &AM80PedoneAI::Next, FMath::FRandRange(1.5f, 7.f), false);
	}
}

bool AM80PedoneAI::TryChat()
{
	AM80Pedone* P = Cast<AM80Pedone>(GetPawn());
	if (!P || FMath::FRand() >= P->VogliaDiParlare)
	{
		return false;
	}
	AM80Pedone* Best = nullptr;
	float BestDist = 800.f;
	for (TActorIterator<AM80Pedone> It(GetWorld()); It; ++It)
	{
		AM80PedoneAI* OtherAI = Cast<AM80PedoneAI>(It->GetController());
		const float D = FVector::Dist2D(It->GetActorLocation(), P->GetActorLocation());
		if (*It != P && OtherAI && D < BestDist && OtherAI->IsWaiting())
		{
			Best = *It;
			BestDist = D;
		}
	}
	if (!Best)
	{
		return false;
	}
	// This one waits where it is; the other walks up to it.
	Cast<AM80PedoneAI>(Best->GetController())->ComeToChat(P);
	// Whoever never arrives (blocked path) is given up on.
	TWeakObjectPtr<AM80Pedone> A(P), B(Best);
	GetWorldTimerManager().SetTimer(ChatEnd, FTimerDelegate::CreateWeakLambda(this, [A, B]()
	{
		if (A.IsValid() && A->Stato == EM80Stato::VaAParlare) { A->EndChat(); }
		if (B.IsValid() && B->Stato == EM80Stato::VaAParlare) { B->EndChat(); }
	}), 15.f, false);
	return true;
}

void AM80PedoneAI::ComeToChat(AM80Pedone* Caller)
{
	AM80Pedone* P = Cast<AM80Pedone>(GetPawn());
	GetWorldTimerManager().ClearTimer(Wait);
	if (!P || !Caller)
	{
		return;
	}
	// Remember who called (BeginChat would turn to face it now: only the name is kept until arriving).
	P->BeginChat(Caller);
	P->Stato = EM80Stato::VaAParlare;
	P->AnimParla = nullptr;
	Caller->BeginChat(P);
	Caller->Stato = EM80Stato::VaAParlare;
	Caller->AnimParla = nullptr;
	const FVector Away = (P->GetActorLocation() - Caller->GetActorLocation()).GetSafeNormal2D();
	if (MoveToLocation(Caller->GetActorLocation() + Away * 110.f, 25.f, true, true, false, false) == EPathFollowingRequestResult::Failed)
	{
		P->EndChat();
		Caller->EndChat();
	}
}

void AM80PedoneAI::Next()
{
	const AM80Pedone* P = Cast<AM80Pedone>(GetPawn());
	UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	if (!P || !Nav || P->Stato != EM80Stato::Libero)
	{
		return;
	}
	FNavLocation To;
	if (Nav->GetRandomReachablePointInRadius(P->GetHome(), P->Raggio, To))
	{
		MoveToLocation(To.Location, 60.f, true, true, false, false);
	}
	else
	{
		GetWorldTimerManager().SetTimer(Wait, this, &AM80PedoneAI::Next, 3.f, false);
	}
}
