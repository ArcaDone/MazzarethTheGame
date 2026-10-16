#include "M80Pedone.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimationPoseData.h"
#include "Animation/AttributesRuntime.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/BillboardComponent.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "Engine/TargetPoint.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "NavigationSystem.h"
#include "Navigation/PathFollowingComponent.h"
#include "TimerManager.h"

namespace
{
// Component space of the UEFN mannequin: the character looks along +Y, +X is its left, +Z up.
const FVector CSLeft(1.f, 0.f, 0.f);
const TCHAR* const MannequinPath = TEXT("/Game/Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin.SKM_UEFN_Mannequin");
const TCHAR* const RetargetAnimPath = TEXT("/Game/Blueprints/RetargetedCharacters/ABP_GenericRetarget.ABP_GenericRetarget_C");
const TCHAR* const WalkPath = TEXT("/Game/Characters/UEFN_Mannequin/Animations/Walk/M_Neutral_Walk_Loop_F.M_Neutral_Walk_Loop_F");
const TCHAR* const IdlePath = TEXT("/Game/Characters/UEFN_Mannequin/Animations/Idle/M_Neutral_Stand_Idle_Loop.M_Neutral_Stand_Idle_Loop");
}

// ---------------------------------------------------------------------------------------------
// Animation

void FM80PedoneProxy::Initialize(UAnimInstance* InAnimInstance)
{
	FAnimInstanceProxy::Initialize(InAnimInstance);
	Walk = LoadObject<UAnimSequence>(nullptr, WalkPath, nullptr, LOAD_NoWarn);
	Idle = LoadObject<UAnimSequence>(nullptr, IdlePath, nullptr, LOAD_NoWarn);
	if (Walk && Walk->GetPlayLength() > 0.f)
	{
		// The loop's own speed, from its root motion: the feet do not slide at any walking speed.
		const FTransform Root = Walk->ExtractRootMotionFromRange(0.0, Walk->GetPlayLength(), FAnimExtractContext());
		const float S = Root.GetTranslation().Size2D() / Walk->GetPlayLength();
		WalkSpeed = S > 30.f ? S : 150.f;
	}
	// Each one starts at a different point of the loops, or a crowd walks in step.
	WalkTime = FMath::FRand() * 10.0;
	IdleTime = FMath::FRand() * 10.0;
}

void FM80PedoneProxy::PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds)
{
	FAnimInstanceProxy::PreUpdate(InAnimInstance, DeltaSeconds);
	const AM80Pedone* P = Cast<AM80Pedone>(InAnimInstance->GetOwningActor());
	const APawn* Pawn = Cast<APawn>(InAnimInstance->GetOwningActor());
	Speed = Pawn ? Pawn->GetVelocity().Size2D() : 0.f;
	Hunch = P ? P->GetHunch() : 0.f;
	WalkTime += DeltaSeconds * Speed / WalkSpeed;
	IdleTime += DeltaSeconds;
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
	for (int32 i = 0; i < BC.GetCompactPoseNumBones(); ++i)
	{
		const FCompactPoseBoneIndex CI(i);
		Bones.Add(Ref.GetBoneName(BC.MakeMeshPoseIndex(CI).GetInt()), CI);
	}
}

void FM80PedoneProxy::Sample(UAnimSequence* Seq, double Time, FCompactPose& Out, FBlendedCurve& Curve, const FPoseContext& Like) const
{
	Out.SetBoneContainer(&Like.Pose.GetBoneContainer());
	Curve.InitFrom(Like.Curve);
	UE::Anim::FStackAttributeContainer Attributes;
	FAnimationPoseData Data(Out, Curve, Attributes);
	const double Length = FMath::Max(Seq->GetPlayLength(), 0.01f);
	Seq->GetAnimationPose(Data, FAnimExtractContext(FMath::Fmod(Time, Length), false));
	// The loops carry the root's travel: kept in place, the capsule does the moving.
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
	const float W = FMath::Clamp((Speed - 10.f) / 50.f, 0.f, 1.f);
	FCompactPose A, B;
	FBlendedCurve CA, CB;
	Sample(Idle, IdleTime, A, CA, Output);
	Sample(Walk, WalkTime, B, CB, Output);
	for (FCompactPoseBoneIndex I : Output.Pose.ForEachBoneIndex())
	{
		FTransform T = A[I];
		T.BlendWith(B[I], W);
		Output.Pose[I] = T;
	}
	Output.Curve.InitFrom(CB);
	// Old people: the back bent forward (more in the upper back), the head lifted to look ahead. A positive turn about
	// CSLeft swings a bone hanging down forward (the arms in M80OverlayAnim), so it tips a bone pointing up backward.
	if (Hunch > 0.f)
	{
		Rotate(Output, TEXT("spine_02"), CSLeft, -Hunch * 0.2f);
		Rotate(Output, TEXT("spine_03"), CSLeft, -Hunch * 0.3f);
		Rotate(Output, TEXT("spine_04"), CSLeft, -Hunch * 0.3f);
		Rotate(Output, TEXT("spine_05"), CSLeft, -Hunch * 0.2f);
		Rotate(Output, TEXT("neck_01"), CSLeft, Hunch * 0.45f);
		Rotate(Output, TEXT("head"), CSLeft, Hunch * 0.35f);
		// Knees a little bent, as old people walk: thighs forward, shins back, feet level again.
		for (const TCHAR* Side : {TEXT("_l"), TEXT("_r")})
		{
			Rotate(Output, FName(FString(TEXT("thigh")) + Side), CSLeft, Hunch * 0.15f);
			Rotate(Output, FName(FString(TEXT("calf")) + Side), CSLeft, -Hunch * 0.3f);
			Rotate(Output, FName(FString(TEXT("foot")) + Side), CSLeft, Hunch * 0.15f);
		}
	}
	return true;
}

// ---------------------------------------------------------------------------------------------
// Pedestrian

AM80Pedone::AM80Pedone()
{
	PrimaryActorTick.bCanEverTick = false;
	static ConstructorHelpers::FObjectFinderOptional<USkeletalMesh> Mannequin(MannequinPath);
	USkeletalMeshComponent* M = GetMesh();
	M->SetSkeletalMesh(Mannequin.Get());
	M->SetAnimInstanceClass(UM80PedoneAnimInstance::StaticClass());
	M->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -90.f), FRotator(0.f, -90.f, 0.f));
	M->SetVisibility(false);   // only the MetaHuman shows; the mannequin still animates for it
	M->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	M->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	GetCapsuleComponent()->InitCapsuleSize(34.f, 90.f);
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
	const FString Name = Personaggio.ToString();
	float Speed = Passo;
	if (Speed <= 0.f)
	{
		Speed = IsOld() ? FMath::FRandRange(70.f, 90.f) : (Name.StartsWith(TEXT("Ragazz")) ? FMath::FRandRange(130.f, 150.f) : FMath::FRandRange(110.f, 130.f));
	}
	GetCharacterMovement()->MaxWalkSpeed = Speed;
	Dress();
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
		USceneComponent* Template = Cast<USceneComponent>(Node ? Node->ComponentTemplate : nullptr);
		if (!Template || Template->GetClass() == USceneComponent::StaticClass())
		{
			if (Node)
			{
				Made.Add(Node->GetVariableName(), GetMesh());   // the Root: our mannequin
			}
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
	Body->AddTickPrerequisiteComponent(GetMesh());
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

void AM80PedoneAI::OnMoveCompleted(FAIRequestID RequestID, const FPathFollowingResult& Result)
{
	Super::OnMoveCompleted(RequestID, Result);
	GetWorldTimerManager().SetTimer(Wait, this, &AM80PedoneAI::Next, FMath::FRandRange(1.5f, 7.f), false);
}

void AM80PedoneAI::Next()
{
	const AM80Pedone* P = Cast<AM80Pedone>(GetPawn());
	UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	if (!P || !Nav)
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
