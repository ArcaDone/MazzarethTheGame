#include "M80Pedone.h"
#include "Animation/AnimSequence.h"
#include "AnimationRuntime.h"
#include "Animation/AnimationPoseData.h"
#include "Animation/AttributesRuntime.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/BillboardComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/LODSyncComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "Engine/Engine.h"
#include "Engine/OverlapResult.h"
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/TargetPoint.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/DamageType.h"
#include "Kismet/GameplayStatics.h"
#include "M80Car.h"
#include "M80Vitals.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "Navigation/PathFollowingComponent.h"
#include "NavigationPath.h"
#include "NavigationSystem.h"
#include "Sound/SoundBase.h"
#include "TimerManager.h"

namespace
{
// Component space of the UEFN mannequin: the character looks along +Y, +X is its left, +Z up.
const FVector CSLeft(1.f, 0.f, 0.f);
const TCHAR* const MannequinPath = TEXT("/Game/Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin.SKM_UEFN_Mannequin");
const TCHAR* const RetargetAnimPath = TEXT("/Game/Blueprints/RetargetedCharacters/ABP_GenericRetarget.ABP_GenericRetarget_C");
const TCHAR* const WalkPath = TEXT("/Game/Characters/UEFN_Mannequin/Animations/Walk/M_Neutral_Walk_Loop_F.M_Neutral_Walk_Loop_F");
const TCHAR* const RunPath = TEXT("/Game/Characters/UEFN_Mannequin/Animations/Run/M_Neutral_Run_Loop_F.M_Neutral_Run_Loop_F");
const TCHAR* const IdlePath = TEXT("/Game/Characters/UEFN_Mannequin/Animations/Idle/M_Neutral_Stand_Idle_Loop.M_Neutral_Stand_Idle_Loop");
const TCHAR* const PunchPath = TEXT("/Game/Mazzarino80/Player/Anim/A_M80_Pugni_Combo.A_M80_Pugni_Combo");
const TCHAR* const GetUpBackPath = TEXT("/Game/Mazzarino80/Player/Anim/A_M80_Rialzati_Schiena.A_M80_Rialzati_Schiena");
const TCHAR* const DrivePath = TEXT("/Game/Mazzarino80/Player/A_M80_Seduto_Guida.A_M80_Seduto_Guida");
const TCHAR* const BlowSound = TEXT("/Game/Mazzarino80/Audio/M80_Colpo.M80_Colpo");

// Timings of the crowd clips (s, 60 fps sources; see Scripts/m80_folla_animazioni.py).
constexpr float TripLie = 3.5f;          // on the ground after a trip
constexpr float CarHitFrom = 2.4f;       // "Hit By Car" stands still for its first seconds
constexpr float GetUpEnd = 5.2f;         // "Getting Up": standing from here on
constexpr float EnterFrom = 0.9f;        // "Entering Car": at the door, opening it...
constexpr float EnterTo = 3.15f;         // ...seated
constexpr float ExitTo = 3.4f;           // "Exiting Car": out, the door shut behind
constexpr float SitTo = 2.2f;            // "Stand To Sit" / "Sit To Stand"
constexpr float SlideIn = 0.6f;          // from the end of getting in to the driving pose on the seat
// The four blows of A_M80_Pugni_Combo (as M80OverlayAnim): the guard before them, then jab, cross, hook, uppercut.
constexpr float PunchGuard = 0.40f;
const float PunchStart[4] = {0.42f, 0.68f, 0.92f, 1.14f};
const float PunchLength[4] = {0.34f, 0.32f, 0.28f, 0.50f};

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

bool IsFingerBone(const FString& Name)
{
	return Name.StartsWith(TEXT("index_")) || Name.StartsWith(TEXT("middle_")) || Name.StartsWith(TEXT("ring_"))
		|| Name.StartsWith(TEXT("pinky_")) || Name.StartsWith(TEXT("thumb_"));
}

bool IsLegBone(const FString& Name)
{
	return Name == TEXT("pelvis") || Name.StartsWith(TEXT("thigh")) || Name.StartsWith(TEXT("calf")) || Name.StartsWith(TEXT("foot"))
		|| Name.StartsWith(TEXT("ball")) || Name.StartsWith(TEXT("ik_foot"));
}

FM80Mossa Step(UAnimSequence* Clip, float Da = 0.f, float A = -1.f, float Tieni = 0.f, bool bRadice = false)
{
	FM80Mossa M;
	M.Clip = Clip;
	M.Da = Da;
	M.A = A;
	M.Tieni = Tieni;
	M.bRadice = bRadice;
	return M;
}

/** The root's travel of Clip from Da to A, in the actor's space (the mesh is turned -90 degrees under the capsule). */
FVector ClipTravel(const AM80Pedone* P, UAnimSequence* Clip, float Da, float A)
{
	if (!Clip)
	{
		return FVector::ZeroVector;
	}
	const FTransform D = Clip->ExtractRootMotionFromRange(Da, A < 0.f ? Clip->GetPlayLength() : A, FAnimExtractContext());
	FVector V = P->GetMesh()->GetRelativeTransform().TransformVector(D.GetTranslation());
	V.Z = 0.f;
	return V;
}

AM80PedoneAI* BrainOf(const AM80Pedone* P)
{
	return P ? Cast<AM80PedoneAI>(P->GetController()) : nullptr;
}
}

// ---------------------------------------------------------------------------------------------
// Steps acted out

float FM80Mossa::Fine() const
{
	const float L = Clip ? Clip->GetPlayLength() : 0.f;
	return FMath::Clamp(A < 0.f ? L : A, Da, FMath::Max(L - 0.01f, Da));
}

float FM80Mossa::TempoClip(float T) const
{
	const float Span = Fine() - Da;
	const float Played = T * Rate;
	if (bLoop && Span > 0.05f)
	{
		return Da + FMath::Fmod(Played, Span);
	}
	return Da + FMath::Clamp(Played, 0.f, Span);
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
	Run = P->AnimCorsa;
	Idle = P->AnimFermo;
	Relaxed = P->AnimRilassato;
	if (P->AnimParla != Talk)
	{
		Talk = P->AnimParla;
		TalkTime = Talk ? FMath::FRand() * Talk->GetPlayLength() * 0.5f : 0.f;
	}
	if (!bStarted)
	{
		// Each one starts at a different point of the loops, or a crowd walks in step.
		bStarted = true;
		WalkTime = LegsTime = RunTime = FMath::FRand() * 10.0;
		IdleTime = FMath::FRand() * 10.0;
	}
	Speed = P->GetVelocity().Size2D();
	Hunch = P->GetHunch();
	Stride = FMath::Clamp(P->GetStride(), 0.2f, 1.f);
	StrideScale = FMath::Max(P->GetPassoScala(), 0.5f);
	Flinch = P->GetFlinch();
	GripWeight = FMath::FInterpConstantTo(GripWeight, P->IsGripping() ? 1.f : 0.f, DeltaSeconds, 3.f);
	TalkWeight = FMath::FInterpConstantTo(TalkWeight, P->Stato == EM80Stato::Parla ? 1.f : 0.f, DeltaSeconds, 1.5f);
	Mossa = FM80PosaMossa();
	P->GetPosaMossa(Mossa);
	ActWeight = FMath::FInterpConstantTo(ActWeight, Mossa.Clip ? 1.f : 0.f, DeltaSeconds, 4.f);
	if (Mossa.Clip)
	{
		LastClip = Mossa.Clip;
		LastTime = Mossa.Tempo;
		bLastBusto = Mossa.bBusto;
	}
	// The body's retarget shortens the steps of a shorter body (and Stride the shuffling old's): the clip plays that
	// much faster, or the feet slide.
	if (Walk && Legs)
	{
		// The legs set the pace; the upper body's clip follows at the same point of its own cycle.
		LegsTime += DeltaSeconds * Speed / (ClipSpeed(Legs) * StrideScale * Stride);
		const double LL = FMath::Max(Legs->GetPlayLength(), 0.01f);
		WalkTime = FMath::Fmod(LegsTime, LL) / LL * Walk->GetPlayLength();
	}
	else if (Walk)
	{
		WalkTime += DeltaSeconds * Speed / (ClipSpeed(Walk) * StrideScale * Stride);
	}
	if (Run)
	{
		RunTime += DeltaSeconds * Speed / (ClipSpeed(Run) * StrideScale);
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
	FingerBones.Reset();
	RelaxedFingers.Reset();
	LegBone.Init(false, BC.GetCompactPoseNumBones());
	for (int32 i = 0; i < BC.GetCompactPoseNumBones(); ++i)
	{
		const FCompactPoseBoneIndex CI(i);
		const FName Name = Ref.GetBoneName(BC.MakeMeshPoseIndex(CI).GetInt());
		Bones.Add(Name, CI);
		LegBone[i] = IsLegBone(Name.ToString());
		if (IsFingerBone(Name.ToString()))
		{
			FingerBones.Add(CI);
		}
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

void FM80PedoneProxy::Grip(FPoseContext& Output, float Weight)
{
	// The right hand closes on the handle: each finger turns about the knuckle line (index to little finger), towards
	// the palm. Turning about that same line keeps it where it is, so all the turns can be worked out on the pose as
	// it was.
	const FCompactPoseBoneIndex* Index = Bones.Find(TEXT("index_01_r"));
	const FCompactPoseBoneIndex* Pinky = Bones.Find(TEXT("pinky_01_r"));
	if (!Index || !Pinky)
	{
		return;
	}
	FCSPose<FCompactPose> CS;
	CS.InitPose(Output.Pose);
	const FVector Knuckles = (CS.GetComponentSpaceTransform(*Index).GetLocation() - CS.GetComponentSpaceTransform(*Pinky).GetLocation()).GetSafeNormal();
	if (Knuckles.IsNearlyZero())
	{
		return;
	}
	struct FBend { const TCHAR* Bone; float Degrees; };
	static const FBend Bends[] = {
		{TEXT("index_01_r"), 55.f}, {TEXT("index_02_r"), 75.f}, {TEXT("index_03_r"), 40.f},
		{TEXT("middle_01_r"), 60.f}, {TEXT("middle_02_r"), 75.f}, {TEXT("middle_03_r"), 40.f},
		{TEXT("ring_01_r"), 65.f}, {TEXT("ring_02_r"), 75.f}, {TEXT("ring_03_r"), 40.f},
		{TEXT("pinky_01_r"), 70.f}, {TEXT("pinky_02_r"), 75.f}, {TEXT("pinky_03_r"), 40.f},
		{TEXT("thumb_02_r"), 25.f}, {TEXT("thumb_03_r"), 35.f},
	};
	for (const FBend& B : Bends)
	{
		const FCompactPoseBoneIndex* I = Bones.Find(B.Bone);
		if (!I)
		{
			continue;
		}
		const FCompactPoseBoneIndex Parent = Output.Pose.GetParentBoneIndex(*I);
		const FQuat ParentRot = Parent.IsValid() ? CS.GetComponentSpaceTransform(Parent).GetRotation() : FQuat::Identity;
		const FVector Axis = ParentRot.UnrotateVector(Knuckles);
		// Right hand: towards the palm is a negative turn about the line from the little finger to the index.
		FTransform& Local = Output.Pose[*I];
		Local.SetRotation((FQuat(Axis, FMath::DegreesToRadians(-B.Degrees * Weight)) * Local.GetRotation()).GetNormalized());
	}
}

void FM80PedoneProxy::Locomotion(FPoseContext& Output)
{
	FCompactPose A, B, R, C;
	FBlendedCurve CA, CB, CR, CC;
	const float W = FMath::Clamp((Speed - 10.f) / 50.f, 0.f, 1.f);
	const float WR = Run ? FMath::Clamp((Speed - 200.f) / 120.f, 0.f, 1.f) : 0.f;
	const bool bShuffle = Stride < 0.99f;
	// Legs (and pelvis) of one pose under the upper body of another: the spine keeps the upper body's lean in
	// component space (the Mixamo old man leans on a forward-tipped pelvis; on the mannequin's upright one his
	// back came out straighter and his head tipped back, looking at the sky).
	const FCompactPoseBoneIndex* Pelvis = Bones.Find(TEXT("pelvis"));
	const FCompactPoseBoneIndex* Spine = Bones.Find(TEXT("spine_01"));
	auto SwapLegs = [&](FCompactPose& Upper, const FCompactPose& Lower)
	{
		const FQuat Qv = Pelvis ? Upper[*Pelvis].GetRotation() : FQuat::Identity;
		const FQuat Qn = Pelvis ? Lower[*Pelvis].GetRotation() : FQuat::Identity;
		for (FCompactPoseBoneIndex I : Upper.ForEachBoneIndex())
		{
			if (LegBone.IsValidIndex(I.GetInt()) && LegBone[I.GetInt()])
			{
				Upper[I] = Lower[I];
			}
		}
		if (Pelvis && Spine)
		{
			const FQuat Fix = Qn.Inverse() * Qv;
			FTransform& S = Upper[*Spine];
			S.SetRotation((Fix * S.GetRotation()).GetNormalized());
			S.SetTranslation(Fix.RotateVector(S.GetTranslation()));
		}
	};
	FCompactPose Stand;
	FBlendedCurve CS;
	const bool bOwn = Legs && Relaxed;
	if (bOwn || (bShuffle && Relaxed))
	{
		Sample(Relaxed, 0.5, Stand, CS, Output);
	}
	if (W < 1.f || bShuffle)
	{
		Sample(Idle, IdleTime, A, CA, Output);
		if (bOwn)
		{
			SwapLegs(A, Stand);   // the old standing on straight legs too
		}
	}
	if (W > 0.f)
	{
		Sample(Walk, WalkTime, B, CB, Output);
		if (Legs)
		{
			// The legs (and pelvis) from the other clip: the old walk upright legs under their stooped walk.
			Sample(Legs, LegsTime, C, CC, Output);
			SwapLegs(B, C);
		}
		if (bShuffle)
		{
			// Shorter steps: the legs only part of the way from standing to the walk's (the feet hardly leave the ground),
			// from the mannequin's own standing legs (the old's idle stands on bent knees).
			const FCompactPose& From = Relaxed ? Stand : A;
			for (FCompactPoseBoneIndex I : B.ForEachBoneIndex())
			{
				if (LegBone.IsValidIndex(I.GetInt()) && LegBone[I.GetInt()])
				{
					FTransform T = From[I];
					T.BlendWith(B[I], Stride);
					B[I] = T;
				}
			}
		}
		if (WR > 0.f)
		{
			Sample(Run, RunTime, R, CR, Output);
			for (FCompactPoseBoneIndex I : B.ForEachBoneIndex())
			{
				B[I].BlendWith(R[I], WR);
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
	}
}

void FM80PedoneProxy::Act(FPoseContext& Output)
{
	UAnimSequence* Clip = Mossa.Clip ? Mossa.Clip : LastClip;
	if (!Clip)
	{
		return;
	}
	const bool bBusto = Mossa.Clip ? Mossa.bBusto : bLastBusto;
	FCompactPose P, Q;
	FBlendedCurve CP, CQ;
	Sample(Clip, Mossa.Clip ? Mossa.Tempo : LastTime, P, CP, Output);
	if (Mossa.Clip && Mossa.Prima && Mossa.Fondi < 1.f)
	{
		// The step before, held where it ended, while this one comes in.
		Sample(Mossa.Prima, Mossa.TempoPrima, Q, CQ, Output);
		for (FCompactPoseBoneIndex I : P.ForEachBoneIndex())
		{
			FTransform T = Q[I];
			T.BlendWith(P[I], Mossa.Fondi);
			P[I] = T;
		}
	}
	for (FCompactPoseBoneIndex I : Output.Pose.ForEachBoneIndex())
	{
		if (bBusto && LegBone.IsValidIndex(I.GetInt()) && LegBone[I.GetInt()])
		{
			continue;
		}
		Output.Pose[I].BlendWith(P[I], ActWeight);
	}
}

bool FM80PedoneProxy::Evaluate(FPoseContext& Output)
{
	if (!Walk || !Idle)
	{
		Output.ResetToRefPose();
		return true;
	}
	Locomotion(Output);
	float Bend = Hunch * (1.f - 0.5f * TalkWeight);
	if (ActWeight > 0.f)
	{
		Act(Output);
		if (!(Mossa.Clip ? Mossa.bBusto : bLastBusto))
		{
			Bend *= 1.f - ActWeight;
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
		// The head back up to look ahead, by less than the back bends (looking at the sky otherwise); the old man's
		// walk already looks ahead.
		if (!Legs)
		{
			Rotate(Output, TEXT("neck_01"), CSLeft, Bend * 0.3f);
			Rotate(Output, TEXT("head"), CSLeft, Bend * 0.15f);
		}
		// Knees a little bent, as old people walk: thighs forward, shins back, feet level again (not over the
		// mannequin's legs: their short steps are the point).
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
	// A blow: the chest and the head jerk back for a moment.
	if (Flinch > 0.f)
	{
		Rotate(Output, TEXT("spine_03"), CSLeft, 9.f * Flinch);
		Rotate(Output, TEXT("spine_05"), CSLeft, 7.f * Flinch);
		Rotate(Output, TEXT("head"), CSLeft, 10.f * Flinch);
	}
	RelaxFingers(Output);
	if (GripWeight > 0.f)
	{
		Grip(Output, GripWeight);
	}
	return true;
}

void FM80PedoneProxy::RelaxFingers(FPoseContext& Output)
{
	if (!Relaxed || FingerBones.IsEmpty())
	{
		return;
	}
	if (RelaxedFingers.Num() != FingerBones.Num())
	{
		FCompactPose R;
		FBlendedCurve CR;
		Sample(Relaxed, 0.5, R, CR, Output);
		RelaxedFingers.Reset();
		for (FCompactPoseBoneIndex I : FingerBones)
		{
			RelaxedFingers.Add(R[I]);
		}
	}
	for (int32 k = 0; k < FingerBones.Num(); ++k)
	{
		Output.Pose[FingerBones[k]] = RelaxedFingers[k];
	}
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
	// Walking into a chair or a table nudges it (the default push, the player's, throws a chair over).
	Move->bEnablePhysicsInteraction = true;
	Move->PushForceFactor = 60000.f;
	Move->InitialPushForceFactor = 100.f;
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
	const bool bMan = Name.StartsWith(TEXT("Uomo")) || Name.StartsWith(TEXT("Ragazzo"));
	EM80Andatura Walk = Andatura;
	if (Walk == EM80Andatura::Auto)
	{
		if (bOldMan)
		{
			Walk = N % 2 == 1 ? EM80Andatura::VecchioTrascina : EM80Andatura::Vecchio;
		}
		else if (bOldWoman)
		{
			Walk = (N == 1 || N == 4) ? EM80Andatura::Spesa : EM80Andatura::Vecchio;
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
	if (Coraggio < 0.f)
	{
		Coraggio = IsOld() ? 0.1f : (bMan ? (bYoung ? 0.6f : 0.5f) : 0.2f);
	}
	if (IsOld())
	{
		VogliaDiGuidare = 0.f;
		VogliaDiSedersi = FMath::Min(1.f, VogliaDiSedersi * 2.f);
		Salute = FMath::Min(Salute, 60.f);
	}
	else if (VogliaDiGuidare < 0.f)
	{
		VogliaDiGuidare = 0.08f;
	}

	// The old man's idle for the old men (on straight legs, see Locomotion); the old women stand as the others, bent.
	AnimFermo = bOldMan ? Clip(TEXT("VecchioFermo")) : Asset(IdlePath);
	AnimRilassato = Asset(IdlePath);
	AnimCorsa = IsOld() ? nullptr : Asset(RunPath);
	AnimGambe = nullptr;
	float Speed = 120.f, Bend = 0.f;
	Stride = 1.f;
	switch (Walk)
	{
	case EM80Andatura::Vecchio:
		if (bOldWoman)
		{
			// Old women: the mannequin's walk with short steps, the back bent (the old man's walk on them was a squat
			// with the arms out).
			AnimCammina = Asset(WalkPath);
			Stride = 0.6f;
			Speed = FMath::FRandRange(40.f, 52.f);
			Bend = 14.f;
			break;
		}
		// The old man's stooped upper body over the mannequin's upright legs, shorter steps (the Mixamo old man walks
		// on bent knees, on our people a squat).
		AnimCammina = Clip(TEXT("VecchioCammina"));
		AnimGambe = Asset(WalkPath);
		Stride = 0.75f;
		Speed = FMath::FRandRange(45.f, 60.f);
		Bend = 4.f;
		break;
	case EM80Andatura::VecchioTrascina:
		// The same with short shuffling steps (the zombie walks the user suggested for the dragging legs looked like
		// squatting or marching on our people).
		AnimCammina = Clip(TEXT("VecchioCammina"));
		AnimGambe = Asset(WalkPath);
		Stride = 0.5f;
		Speed = FMath::FRandRange(28.f, 36.f);
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
		Stride = 1.f;
	}
	if (!AnimFermo)
	{
		AnimFermo = Asset(IdlePath);
	}
	WalkSpeed = Passo > 0.f ? Passo : Speed;
	GetCharacterMovement()->MaxWalkSpeed = WalkSpeed;
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
	// Held by the fingers (where the middle finger starts); turned in Tick (bags hang straight down, the stick leans
	// from the hand to the ground in front of the feet).
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

void AM80Pedone::Capsula(bool bOn)
{
	UCapsuleComponent* Cap = GetCapsuleComponent();
	Cap->SetCollisionEnabled(bOn ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
	UCharacterMovementComponent* Move = GetCharacterMovement();
	if (bOn)
	{
		Move->SetMovementMode(MOVE_Walking);
	}
	else
	{
		Move->StopMovementImmediately();
		Move->DisableMovement();
	}
}

void AM80Pedone::Recita(const TArray<FM80Mossa>& InMosse, TFunction<void()> Poi)
{
	// What was being acted out stays as the pose the first step blends in from (also a sequence that ended this very
	// frame, calling this from its end: TickMosse keeps its last step until the next frame).
	if (Mosse.IsValidIndex(MossaN))
	{
		MossaPrima = Mosse[MossaN].Clip;
		MossaPrimaT = Mosse[MossaN].TempoClip(MossaT);
	}
	Mosse = InMosse;
	MossaN = Mosse.Num() > 0 ? 0 : INDEX_NONE;
	MossaT = 0.f;
	DopoMosse = MoveTemp(Poi);
}

void AM80Pedone::SmettiMosse()
{
	Mosse.Reset();
	MossaN = INDEX_NONE;
	MossaPrima = nullptr;
	DopoMosse = nullptr;
}

bool AM80Pedone::GetPosaMossa(FM80PosaMossa& Out) const
{
	if (!Mosse.IsValidIndex(MossaN) || !Mosse[MossaN].Clip)
	{
		return false;
	}
	const FM80Mossa& M = Mosse[MossaN];
	Out.Clip = M.Clip;
	Out.Tempo = M.TempoClip(MossaT);
	Out.Prima = MossaPrima;
	Out.TempoPrima = MossaPrimaT;
	Out.Fondi = M.Fondi > 0.f ? FMath::Clamp(MossaT / M.Fondi, 0.f, 1.f) : 1.f;
	Out.bBusto = M.bBusto;
	return true;
}

void AM80Pedone::TickMosse(float DeltaSeconds)
{
	if (!Mosse.IsValidIndex(MossaN))
	{
		MossaPrima = nullptr;   // back to walking: the next act blends in from it
		return;
	}
	const FM80Mossa& M = Mosse[MossaN];
	const float Prev = MossaT;
	MossaT += DeltaSeconds;
	if (M.bRadice && M.Clip)
	{
		const float A0 = M.TempoClip(Prev);
		const float A1 = M.TempoClip(MossaT);
		if (A1 > A0)
		{
			// The capsule follows the clip's root: its travel (in the mesh's space) and its turning.
			const FTransform D = M.Clip->ExtractRootMotionFromRange(A0, A1, FAnimExtractContext());
			FVector Move = GetMesh()->GetComponentTransform().TransformVector(D.GetTranslation());
			Move.Z = 0.f;
			const bool bSweep = GetCapsuleComponent()->GetCollisionEnabled() != ECollisionEnabled::NoCollision;
			AddActorWorldOffset(Move, bSweep);
			const float Yaw = D.GetRotation().Rotator().Yaw;
			if (!FMath::IsNearlyZero(Yaw))
			{
				AddActorWorldRotation(FRotator(0.f, Yaw, 0.f));
			}
		}
	}
	if (MossaT >= M.Durata())
	{
		MossaPrima = M.Clip;
		MossaPrimaT = M.TempoClip(M.Durata());
		++MossaN;
		MossaT = 0.f;
		if (!Mosse.IsValidIndex(MossaN))
		{
			Mosse.Reset();
			MossaN = INDEX_NONE;
			TFunction<void()> Then = MoveTemp(DopoMosse);
			DopoMosse = nullptr;
			if (Then)
			{
				Then();
			}
		}
	}
}

void AM80Pedone::Torna(float Delay)
{
	Stato = EM80Stato::Libero;
	Nemico.Reset();
	StateTime = 0.f;
	GetCharacterMovement()->MaxWalkSpeed = WalkSpeed;
	if (AM80PedoneAI* AI = BrainOf(this))
	{
		AI->Resume(Delay);
	}
}

void AM80Pedone::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	StateTime += DeltaSeconds;
	Flinch = FMath::FInterpConstantTo(Flinch, 0.f, DeltaSeconds, 3.f);
	MakeWayWait -= DeltaSeconds;
	TickMosse(DeltaSeconds);
	if (Oggetto)
	{
		Oggetto->SetVisibility(Stato != EM80Stato::InAuto);
		const float Yaw = GetActorRotation().Yaw;
		if (Accessorio == EM80Accessorio::Bastone)
		{
			// The stick from the hand to the ground a little in front of the feet (it swings with the arm).
			const FVector Grip = Oggetto->GetComponentLocation();
			const FVector Tip(Grip.X + GetActorForwardVector().X * 15.f, Grip.Y + GetActorForwardVector().Y * 15.f,
				GetActorLocation().Z - GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
			const FVector Down = (Tip - Grip).GetSafeNormal();
			Oggetto->SetWorldRotation(Down.IsNearlyZero() ? FRotator(0.f, Yaw, 0.f) : FRotationMatrix::MakeFromZX(-Down, GetActorForwardVector()).Rotator());
		}
		else
		{
			Oggetto->SetWorldRotation(FRotator(0.f, Yaw, 0.f));
		}
	}
	switch (Stato)
	{
	case EM80Stato::Difende:
		TickDifende(DeltaSeconds);
		break;
	case EM80Stato::Scappa:
		if (StateTime > 14.f)
		{
			Torna(FMath::FRandRange(1.f, 3.f));
		}
		break;
	case EM80Stato::InAuto:
		TickAuto(DeltaSeconds);
		break;
	case EM80Stato::Libero:
		if (CadutePerMinuto > 0.f && GetVelocity().Size2D() > 30.f && FMath::FRand() < CadutePerMinuto * DeltaSeconds / 60.f)
		{
			Inciampa();
		}
		break;
	default:
		break;
	}
	CheckCars(DeltaSeconds);
}

void AM80Pedone::Inciampa()
{
	if (Stato != EM80Stato::Libero)
	{
		return;
	}
	UAnimSequence* Fall = Clip(TEXT("Inciampo"));
	if (!Fall)
	{
		return;
	}
	Stato = EM80Stato::Caduto;
	StateTime = 0.f;
	if (AM80PedoneAI* AI = BrainOf(this))
	{
		AI->StopMovement();
		AI->Resume(-1.f);
	}
	// Falls forward (the clip carries the body over the ground), lies a while, gets up from the back (it ends half
	// turned on its back).
	FM80Mossa Down = Step(Fall, 0.f, -1.f, TripLie, true);
	FM80Mossa Up = Step(Asset(GetUpBackPath), 0.f, -1.f, 0.f, true);
	Up.Fondi = 0.7f;
	Recita(Up.Clip ? TArray<FM80Mossa>{Down, Up} : TArray<FM80Mossa>{Down}, [this]() { Torna(FMath::FRandRange(1.f, 3.f)); });
}

void AM80Pedone::Muori(UAnimSequence* Caduta, float Da)
{
	EndChat();
	if (Stato == EM80Stato::Seduto)
	{
		TieniSedia(Sedia.Get(), false);
	}
	Stato = EM80Stato::Morto;
	Sedia.Reset();
	if (AM80PedoneAI* AI = BrainOf(this))
	{
		AI->StopMovement();
		AI->Resume(-1.f);
	}
	Capsula(false);
	if (Caduta)
	{
		Recita({Step(Caduta, Da, -1.f, -1.f, true)});
	}
	SetLifeSpan(120.f);
}

void AM80Pedone::Investi(FVector Direction, float Kmh, AActor* Car)
{
	if (Stato == EM80Stato::Morto || Stato == EM80Stato::InAuto || Stato == EM80Stato::Investito)
	{
		return;
	}
	UAnimSequence* Hit = Clip(TEXT("Investito"));
	EndChat();
	if (Stato == EM80Stato::Seduto)
	{
		TieniSedia(Sedia.Get(), false);
	}
	Sedia.Reset();
	Flinch = 1.f;
	Salute -= Kmh * 1.5f;
	// The clip throws the body to its right: turned so that its right is where the car pushes.
	const FVector Dir = Direction.GetSafeNormal2D();
	if (!Dir.IsNearlyZero())
	{
		SetActorRotation(FRotator(0.f, Dir.Rotation().Yaw - 90.f, 0.f));
	}
	if (AM80PedoneAI* AI = BrainOf(this))
	{
		AI->StopMovement();
		AI->Resume(-1.f);
	}
	// Down on the ground: the car and the others go over or around it, it does not stop them.
	Capsula(false);
	if (Salute <= 0.f || Kmh > 50.f || !Hit)
	{
		Muori(Hit ? Hit : Clip(TEXT("Inciampo")), Hit ? CarHitFrom : 0.4f);
		return;
	}
	Stato = EM80Stato::Investito;
	StateTime = 0.f;
	FM80Mossa Down = Step(Hit, CarHitFrom, -1.f, FMath::FRandRange(2.f, 4.f), true);
	Down.Rate = FMath::Clamp(Kmh / 25.f, 0.9f, 1.3f);
	Down.Fondi = 0.08f;
	FM80Mossa Up = Step(Clip(TEXT("Rialzati")), 0.f, GetUpEnd, 0.f, true);
	Up.Fondi = 0.8f;
	Recita(Up.Clip ? TArray<FM80Mossa>{Down, Up} : TArray<FM80Mossa>{Down}, [this]()
	{
		Capsula(true);
		// Shaken: runs off from the place (or just walks on, old).
		Torna(FMath::FRandRange(0.5f, 1.5f));
	});
}

void AM80Pedone::CheckCars(float DeltaSeconds)
{
	CarCheck -= DeltaSeconds;
	if (CarCheck > 0.f || Stato == EM80Stato::Morto || Stato == EM80Stato::InAuto || Stato == EM80Stato::Investito)
	{
		return;
	}
	CarCheck = 0.08f;
	const FVector P = GetActorLocation();
	for (TActorIterator<AM80Car> It(GetWorld()); It; ++It)
	{
		AM80Car* C = *It;
		if (C == Auto.Get() || FVector::DistSquared2D(C->GetActorLocation(), P) > FMath::Square(700.f))
		{
			continue;
		}
		// Inside the car's box grown by the capsule radius (car space), and the car coming at it?
		const FBox Local = C->GetMesh()->CalcBounds(FTransform::Identity).GetBox().ExpandBy(FVector(40.f, 40.f, 20.f));
		if (!Local.IsInside(C->GetActorTransform().InverseTransformPosition(P)))
		{
			continue;
		}
		const FVector Away = (P - C->GetActorLocation()).GetSafeNormal2D();
		const float Kmh = (C->GetVelocity() | Away) * 0.036f;
		if (Kmh > 9.f)
		{
			Investi(C->GetVelocity().GetSafeNormal2D() * 0.6f + Away * 0.4f, Kmh, C);
			return;
		}
	}
	// Out of the cars' way: one coming at it (in front of a car going forward, behind one reversing), or one it is
	// about to walk into (parked cars are not in the walking paths).
	if (Stato != EM80Stato::Libero && Stato != EM80Stato::Parla && Stato != EM80Stato::VaAParlare)
	{
		return;
	}
	for (TActorIterator<AM80Car> It(GetWorld()); It; ++It)
	{
		AM80Car* C = *It;
		if (C == Auto.Get() || FVector::DistSquared2D(C->GetActorLocation(), P) > FMath::Square(1500.f))
		{
			continue;
		}
		const FBox B = C->GetMesh()->CalcBounds(FTransform::Identity).GetBox();
		const FVector L = C->GetActorTransform().InverseTransformPosition(P);
		const float Kmh = C->GetSpeedKmh();
		const bool bInLane = FMath::Abs(L.Y) < B.Max.Y + 90.f;
		const bool bAhead = Kmh > 3.f && bInLane && L.X > B.Max.X - 50.f && L.X < B.Max.X + 300.f + Kmh * 15.f;
		const bool bBehind = Kmh < -3.f && bInLane && L.X < B.Min.X + 50.f && L.X > B.Min.X - 300.f;
		const bool bInto = B.ExpandBy(FVector(70.f, 70.f, 50.f)).IsInside(L) && GetVelocity().Size2D() > 20.f
			&& (GetVelocity() | (C->GetActorLocation() - P)) > 0.f;
		if (bAhead || bBehind || bInto)
		{
			Scansati(C, FMath::Abs(Kmh) > 15.f);
			return;
		}
	}
}

float AM80Pedone::TakeDamage(float DamageAmount, FDamageEvent const& DamageEvent, AController* EventInstigator, AActor* DamageCauser)
{
	const float Got = Super::TakeDamage(DamageAmount, DamageEvent, EventInstigator, DamageCauser);
	if (Stato == EM80Stato::Morto || Got <= 0.f)
	{
		return Got;
	}
	Flinch = 1.f;
	Salute -= Got;
	AActor* Who = EventInstigator && EventInstigator->GetPawn() ? EventInstigator->GetPawn() : DamageCauser;
	if (Stato == EM80Stato::InAuto)
	{
		return Got;
	}
	if (Salute <= 0.f)
	{
		if (Stato == EM80Stato::Seduto || Stato == EM80Stato::VaASedersi)
		{
			Capsula(true);
		}
		Muori(Clip(TEXT("Inciampo")), 0.6f);
		return Got;
	}
	// Big blows (shots, a bat) send everyone running; a punch may be answered.
	Reagisci(Who, Got >= 20.f);
	return Got;
}

void AM80Pedone::Reagisci(AActor* Who, bool bForzaFuga)
{
	if (!Who || Who == this || Stato == EM80Stato::Caduto || Stato == EM80Stato::Investito || Stato == EM80Stato::Morto
		|| Stato == EM80Stato::InAuto || Stato == EM80Stato::VaAllAuto)
	{
		return;
	}
	if ((Stato == EM80Stato::Difende && Nemico.Get() == Who) || Stato == EM80Stato::Scappa)
	{
		return;
	}
	// Whatever it was doing ends: the chat (the other one runs off too), the chair.
	if (AM80Pedone* Other = Compagno.Get())
	{
		EndChat();
		Other->EndChat();
		Other->Reagisci(Who, true);
	}
	EndChat();
	if (Sedia.IsValid() || Stato == EM80Stato::Seduto)
	{
		if (Stato == EM80Stato::Seduto)
		{
			TieniSedia(Sedia.Get(), false);
		}
		Sedia.Reset();
		SmettiMosse();
		Capsula(true);
	}
	AM80PedoneAI* AI = BrainOf(this);
	if (AI)
	{
		AI->StopMovement();
		AI->Resume(-1.f);
	}
	Nemico = Who;
	StateTime = 0.f;
	if (!bForzaFuga && FMath::FRand() < Coraggio)
	{
		// Puts its fists up and goes at whoever hit it.
		Stato = EM80Stato::Difende;
		PunchWait = 0.3f;
		GetCharacterMovement()->MaxWalkSpeed = IsOld() ? 70.f : 250.f;
		if (UAnimSequence* Fists = Asset(PunchPath))
		{
			FM80Mossa Guard = Step(Fists, 0.f, PunchGuard, -1.f);
			Guard.bBusto = true;
			Recita({Guard});
		}
		return;
	}
	// Runs away from it, far, as fast as it can (the old hurry as they can).
	Stato = EM80Stato::Scappa;
	SmettiMosse();
	GetCharacterMovement()->MaxWalkSpeed = IsOld() ? 100.f : FMath::FRandRange(360.f, 430.f);
	UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	FVector Away = (GetActorLocation() - Who->GetActorLocation()).GetSafeNormal2D();
	if (Away.IsNearlyZero())
	{
		Away = -GetActorForwardVector();
	}
	FNavLocation To;
	const FVector Far = GetActorLocation() + Away * FMath::FRandRange(1500.f, 2500.f);
	if (AI && Nav && (Nav->GetRandomReachablePointInRadius(Far, 700.f, To) || Nav->ProjectPointToNavigation(Far, To, FVector(800.f, 800.f, 400.f))))
	{
		AI->MoveToLocation(To.Location, 100.f, true, true, false, false);
	}
}

void AM80Pedone::Scansati(const AActor* Car, bool bFast)
{
	if (!Car || MakeWayWait > 0.f || !(Stato == EM80Stato::Libero || Stato == EM80Stato::Parla || Stato == EM80Stato::VaAParlare))
	{
		return;
	}
	AM80PedoneAI* AI = BrainOf(this);
	if (!AI)
	{
		return;
	}
	MakeWayWait = bFast ? 1.5f : 3.f;
	if (bFast)
	{
		GetCharacterMovement()->MaxWalkSpeed = IsOld() ? 110.f : 320.f;
	}
	if (AM80Pedone* Other = Compagno.Get())
	{
		Other->EndChat();
	}
	EndChat();
	AI->Resume(-1.f);
	// Off the car's way, to the side it is already on, a little ahead.
	const FVector Fwd = Car->GetActorForwardVector().GetSafeNormal2D();
	FVector Side(-Fwd.Y, Fwd.X, 0.f);
	if (((GetActorLocation() - Car->GetActorLocation()) | Side) < 0.f)
	{
		Side = -Side;
	}
	AI->MoveToLocation(GetActorLocation() + Side * 300.f + Fwd * 50.f, 40.f, false, true, true, false);
}

void AM80Pedone::Spaventa(UObject* WorldContext, FVector Where, float Radius, AActor* Source)
{
	UWorld* World = GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull);
	if (!World)
	{
		return;
	}
	for (TActorIterator<AM80Pedone> It(World); It; ++It)
	{
		if (FVector::DistSquared(It->GetActorLocation(), Where) < FMath::Square(Radius))
		{
			It->Reagisci(Source ? Source : nullptr, true);
		}
	}
}

void AM80Pedone::TickDifende(float DeltaSeconds)
{
	AActor* Enemy = Nemico.Get();
	const UM80VitalsComponent* Vitals = Enemy ? Enemy->FindComponentByClass<UM80VitalsComponent>() : nullptr;
	const float Dist = Enemy ? FVector::Dist2D(Enemy->GetActorLocation(), GetActorLocation()) : 1e9f;
	if (!Enemy || Dist > 2000.f || StateTime > 25.f || (Vitals && Vitals->IsDead()))
	{
		SmettiMosse();
		Torna(FMath::FRandRange(1.f, 3.f));
		return;
	}
	// Badly beaten: gives up and runs.
	if (Salute < 25.f)
	{
		SmettiMosse();
		Stato = EM80Stato::Libero;
		Reagisci(Enemy, true);
		return;
	}
	AM80PedoneAI* AI = BrainOf(this);
	const FVector To = (Enemy->GetActorLocation() - GetActorLocation()).GetSafeNormal2D();
	if (Dist > 115.f)
	{
		if (AI && AI->GetMoveStatus() == EPathFollowingStatus::Idle)
		{
			AI->MoveToActor(Enemy, 70.f, true, true, false);
		}
	}
	else
	{
		if (AI)
		{
			AI->StopMovement();
		}
		SetActorRotation(FMath::RInterpTo(GetActorRotation(), FRotator(0.f, To.Rotation().Yaw, 0.f), DeltaSeconds, 8.f));
	}
	UAnimSequence* Fists = Asset(PunchPath);
	if (!Fists)
	{
		return;
	}
	PunchWait -= DeltaSeconds;
	const bool bPunching = IsActing() && Mosse[MossaN].Tieni >= 0.f;
	if (bPunching && !bPunchHit && MossaT > 0.45f * Mosse[MossaN].Durata())
	{
		// The blow lands if the other is still in reach, in front.
		bPunchHit = true;
		if (Dist < 140.f && (GetActorForwardVector() | To) > 0.5f)
		{
			FHitResult Hit(Enemy, nullptr, Enemy->GetActorLocation(), -To);
			UGameplayStatics::ApplyPointDamage(Enemy, IsOld() ? 2.f : 4.f, To, Hit, GetController(), this, UDamageType::StaticClass());
			UGameplayStatics::PlaySoundAtLocation(this, LoadObject<USoundBase>(nullptr, BlowSound, nullptr, LOAD_NoWarn), Enemy->GetActorLocation());
		}
	}
	if (!bPunching && Dist < 125.f && PunchWait <= 0.f)
	{
		const int32 K = FMath::RandRange(0, 3);
		FM80Mossa Blow = Step(Fists, PunchStart[K], PunchStart[K] + PunchLength[K]);
		Blow.bBusto = true;
		Blow.Fondi = 0.06f;
		FM80Mossa Guard = Step(Fists, 0.f, PunchGuard, -1.f);
		Guard.bBusto = true;
		Guard.Fondi = 0.12f;
		Recita({Blow, Guard});
		bPunchHit = false;
		PunchWait = FMath::FRandRange(1.f, 1.8f) * (IsOld() ? 1.8f : 1.f);
	}
}

// ---------------------------------------------------------------------------------------------
// Sitting

bool AM80Pedone::SediaLibera(const AActor* Chair)
{
	return Chair && Chair->ActorHasTag(TEXT("M80Sedia")) && !Chair->ActorHasTag(TEXT("M80Occupata"))
		&& Chair->GetActorUpVector().Z > 0.95f;
}

void AM80Pedone::TieniSedia(AActor* Chair, bool bSeated)
{
	if (!Chair)
	{
		return;
	}
	if (UPrimitiveComponent* Body = Cast<UPrimitiveComponent>(Chair->GetRootComponent()))
	{
		if (Body->Mobility == EComponentMobility::Movable)
		{
			Body->SetSimulatePhysics(!bSeated);
		}
	}
	if (bSeated)
	{
		Chair->Tags.AddUnique(TEXT("M80Occupata"));
	}
	else
	{
		Chair->Tags.Remove(TEXT("M80Occupata"));
	}
}

FVector AM80Pedone::DoveSedersi(const AActor* Chair, const ACharacter* Who, UAnimSequence* SitClip, float To)
{
	FVector Back = FVector::ZeroVector;
	if (SitClip && Who)
	{
		const FTransform D = SitClip->ExtractRootMotionFromRange(0.f, To, FAnimExtractContext());
		Back = Who->GetMesh()->GetRelativeTransform().TransformVector(D.GetTranslation());
		Back.Z = 0.f;
	}
	FVector Start = Chair->GetActorLocation() - FRotator(0.f, Chair->GetActorRotation().Yaw, 0.f).RotateVector(Back);
	Start.Z = Who ? Who->GetActorLocation().Z : Start.Z;
	return Start;
}

bool AM80Pedone::VaiASedere(AActor* Chair)
{
	AM80PedoneAI* AI = BrainOf(this);
	UAnimSequence* Down = Clip(TEXT("Siediti"));
	if (!AI || !SediaLibera(Chair) || !Down || Stato != EM80Stato::Libero)
	{
		return false;
	}
	// Where to stand so that sitting down (the clip steps back) ends on the seat; only chairs with that spot on the
	// walking ways (one pushed under its table is left alone).
	const FVector Start = DoveSedersi(Chair, this, Down, SitTo);
	UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	FNavLocation OnNav;
	if (!Nav || !Nav->ProjectPointToNavigation(Start, OnNav, FVector(60.f, 60.f, 200.f)))
	{
		return false;
	}
	Sedia = Chair;
	Stato = EM80Stato::VaASedersi;
	StateTime = 0.f;
	// As near as the walking ways get (a chair at a table: its front is under the table), then the last step in Siediti.
	if (AI->MoveToLocation(OnNav.Location, 30.f, false, true, false, false, nullptr, true) == EPathFollowingRequestResult::Failed)
	{
		Sedia.Reset();
		Stato = EM80Stato::Libero;
		return false;
	}
	return true;
}

void AM80Pedone::Siediti()
{
	AActor* Chair = Sedia.Get();
	// Pushed over or taken while walking to it: never mind.
	if (!SediaLibera(Chair))
	{
		Sedia.Reset();
		Torna(1.f);
		return;
	}
	const FVector Start = DoveSedersi(Chair, this, Clip(TEXT("Siediti")), SitTo);
	if (FVector::Dist2D(Start, GetActorLocation()) > 150.f)
	{
		Sedia.Reset();
		Torna(1.f);
		return;
	}
	Stato = EM80Stato::Seduto;
	StateTime = 0.f;
	Capsula(false);
	SetActorLocationAndRotation(Start, FRotator(0.f, Chair->GetActorRotation().Yaw, 0.f));
	TieniSedia(Chair, true);
	// Sits down, stays a while (still, chatting, laughing, shaking the head), gets up.
	TArray<FM80Mossa> Steps;
	Steps.Add(Step(Clip(TEXT("Siediti")), 0.f, SitTo, 0.f, true));
	const TCHAR* Loops[] = {TEXT("Seduto"), TEXT("Seduto_Parla"), TEXT("Seduto"), TEXT("Seduto_Ride"), TEXT("Seduto_Incredulo")};
	const int32 Count = FMath::RandRange(2, 4);
	for (int32 i = 0; i < Count; ++i)
	{
		UAnimSequence* L = Clip(Loops[i == 0 ? 0 : FMath::RandRange(0, UE_ARRAY_COUNT(Loops) - 1)]);
		if (L)
		{
			// Looping for 6-14 s in all (the loop goes on while held).
			FM80Mossa S = Step(L);
			S.bLoop = true;
			S.Tieni = FMath::Max(0.f, FMath::FRandRange(6.f, 14.f) - (S.Fine() - S.Da));
			S.Fondi = 0.5f;
			Steps.Add(S);
		}
	}
	FM80Mossa Up = Step(Clip(TEXT("Alzati")), 0.f, SitTo, 0.f, true);
	Up.Fondi = 0.4f;
	Steps.Add(Up);
	Steps.RemoveAll([](const FM80Mossa& S) { return !S.Clip; });
	Recita(Steps, [this]()
	{
		TieniSedia(Sedia.Get(), false);
		Sedia.Reset();
		Capsula(true);
		Torna(FMath::FRandRange(0.5f, 2.f));
	});
}

// ---------------------------------------------------------------------------------------------
// Driving

bool AM80Pedone::VaiAGuidare(AM80Car* Car, float Seconds)
{
	AM80PedoneAI* AI = BrainOf(this);
	UAnimSequence* In = Clip(TEXT("Sale"));
	if (!AI || !Car || !In || Stato != EM80Stato::Libero || Car->bWrecked || Car->GetController())
	{
		return false;
	}
	// Getting in walks the body from the door into the seat, turning from facing the car to facing its front: start
	// where that walk ends on the seat.
	const FRotator Facing(0.f, Car->GetActorRotation().Yaw + 90.f, 0.f);
	const FVector Seat = Car->GetMesh()->GetComponentTransform().TransformPosition(Car->SeatOffset);
	FVector Start = Seat - Facing.RotateVector(ClipTravel(this, In, EnterFrom, EnterTo));
	Start.Z = GetActorLocation().Z;
	Auto = Car;
	GuidaSecondi = Seconds;
	Stato = EM80Stato::VaAllAuto;
	StateTime = 0.f;
	if (AI->MoveToLocation(Start, 20.f, false, true, false, false) == EPathFollowingRequestResult::Failed)
	{
		Auto.Reset();
		Stato = EM80Stato::Libero;
		return false;
	}
	return true;
}

void AM80Pedone::Sali()
{
	AM80Car* Car = Auto.Get();
	if (!Car || Car->bWrecked || Car->GetController())
	{
		Auto.Reset();
		Torna(1.f);
		return;
	}
	Stato = EM80Stato::InAuto;
	StateTime = 0.f;
	SetActorRotation(FRotator(0.f, Car->GetActorRotation().Yaw + 90.f, 0.f));
	Capsula(false);
	FM80Mossa In = Step(Clip(TEXT("Sale")), EnterFrom, EnterTo, 0.f, true);
	Recita({In}, [this]()
	{
		AM80Car* C = Auto.Get();
		if (!C)
		{
			Capsula(true);
			Torna(1.f);
			return;
		}
		// Seated: on the car from now on, sliding onto the seat while the driving pose comes in.
		AttachToComponent(C->GetMesh(), FAttachmentTransformRules::KeepWorldTransform);
		StateTime = 0.f;
		UAnimSequence* Pose = C->RidePose.IsNull() ? Asset(DrivePath) : Cast<UAnimSequence>(C->RidePose.LoadSynchronous());
		if (Pose)
		{
			FM80Mossa Sit = Step(Pose, 0.f, -1.f, -1.f);
			Sit.bLoop = true;
			Sit.Fondi = SlideIn;
			Recita({Sit});
		}
	});
}

void AM80Pedone::TickAuto(float DeltaSeconds)
{
	if (ExitDrop > 0.f && IsActing())
	{
		// Down at first, back to the ground as the feet come out of the car (1.6-2.4 s into the clip).
		const float Up = FMath::Clamp((MossaT - 0.6f) / 1.8f, 0.f, 1.f);
		GetMesh()->SetRelativeLocation(FVector(0.f, 0.f, -90.f - ExitDrop * (1.f - Up)));
	}
	AM80Car* Car = Auto.Get();
	if (!Car || !IsAttachedTo(Car))
	{
		return;   // getting in (the clip moves it) or out
	}
	if (Car->bWrecked)
	{
		Scendi(true);
		return;
	}
	// Sliding onto the seat, then driving off.
	if (StateTime <= SlideIn + DeltaSeconds)
	{
		const float A = FMath::Clamp(StateTime / SlideIn, 0.f, 1.f);
		const float E = A * A * (3.f - 2.f * A);
		USceneComponent* Root = GetRootComponent();
		Root->SetRelativeLocation(FMath::Lerp(Root->GetRelativeLocation(), Car->SeatOffset, E));
		Root->SetRelativeRotation(FQuat::Slerp(Root->GetRelativeRotation().Quaternion(), FRotator(Car->SeatRecline, 0.f, 0.f).Quaternion(), E));
		if (A >= 1.f)
		{
			Guida();
		}
	}
}

void AM80Pedone::Guida()
{
	AM80Car* Car = Auto.Get();
	if (!Car || Car->GetController())
	{
		return;
	}
	FActorSpawnParameters SP;
	SP.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	if (AM80AutistaAI* Driver = GetWorld()->SpawnActor<AM80AutistaAI>(AM80AutistaAI::StaticClass(), Car->GetActorTransform(), SP))
	{
		Driver->Guida(Car, this, GuidaSecondi, FMath::Max(Raggio, 2500.f));
	}
}

void AM80Pedone::Scendi(bool bSubito)
{
	AM80Car* Car = Auto.Get();
	if (Stato != EM80Stato::InAuto)
	{
		return;
	}
	if (Car)
	{
		if (AM80AutistaAI* Driver = Cast<AM80AutistaAI>(Car->GetController()))
		{
			Driver->UnPossess();
			Driver->SetLifeSpan(0.5f);
		}
	}
	const FRotator Yaw(0.f, Car ? Car->GetActorRotation().Yaw : GetActorRotation().Yaw, 0.f);
	DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
	FVector At = GetActorLocation();
	if (Car)
	{
		// From the seat, at standing height (the clip starts seated).
		At = Car->GetMesh()->GetComponentTransform().TransformPosition(Car->SeatOffset);
		At.Z = Car->GetActorLocation().Z + GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 2.f;
	}
	SetActorLocationAndRotation(At, Yaw, false, nullptr, ETeleportType::TeleportPhysics);
	Auto.Reset();
	UAnimSequence* Out = Clip(TEXT("Scende"));
	if (bSubito || !Out)
	{
		// Pulled out: out of the door at once, and away.
		if (Car)
		{
			SetActorLocation(Car->GetActorTransform().TransformPosition(Car->DoorOffset * FVector(1.f, 1.f, 0.f)) + FVector(0.f, 0.f, At.Z - Car->GetActorLocation().Z));
		}
		SmettiMosse();
		Capsula(true);
		Stato = EM80Stato::Libero;
		if (Car)
		{
			Reagisci(Car, true);
		}
		else
		{
			Torna(1.f);
		}
		return;
	}
	// Gets out to its left (the driver's door), shuts the door, then walks on. The clip sits on a car seat 81 cm
	// from the ground (as tall as the clip's skeleton): our seats are lower, the head would come out of the roof.
	FM80Mossa Step1 = Step(Out, 0.f, ExitTo, 0.f, true);
	Step1.Fondi = 0.3f;
	// Seated, our pelvis is about as high as the seat offset (capsule centre over the car's ground).
	ExitDrop = Car ? FMath::Clamp(81.f - float(Car->SeatOffset.Z), 0.f, 45.f) : 0.f;
	Recita({Step1}, [this]()
	{
		ExitDrop = 0.f;
		GetMesh()->SetRelativeLocation(FVector(0.f, 0.f, -90.f));
		Capsula(true);
		Torna(FMath::FRandRange(0.5f, 2.f));
	});
}

// ---------------------------------------------------------------------------------------------
// Chatting

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
	AnimParla = nullptr;
	if (bWasChatting)
	{
		Stato = EM80Stato::Libero;
		if (AM80PedoneAI* AI = BrainOf(this))
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
			P->VogliaDiSedersi = VogliaDiSedersi;
			P->VogliaDiGuidare = VogliaDiGuidare;
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
	// A walk cut short by a new one (going to a chair, to a car, running away): the new one decides.
	if (!P || Result.HasFlag(FPathFollowingResultFlags::NewRequest))
	{
		return;
	}
	switch (P->Stato)
	{
	case EM80Stato::VaASedersi:
		if (Result.IsSuccess())
		{
			P->Siediti();
		}
		else
		{
			P->Torna(1.f);
		}
		return;
	case EM80Stato::VaAllAuto:
		if (Result.IsSuccess())
		{
			P->Sali();
		}
		else
		{
			P->Torna(1.f);
		}
		return;
	case EM80Stato::Scappa:
		// Far enough: catches its breath, then on.
		P->Torna(FMath::FRandRange(2.f, 5.f));
		return;
	case EM80Stato::VaAParlare:
		break;
	case EM80Stato::Libero:
		P->GetCharacterMovement()->MaxWalkSpeed = P->WalkSpeed;   // after hurrying out of a car's way
		if (!TryChat() && !TrySit() && !TryDrive())
		{
			GetWorldTimerManager().SetTimer(Wait, this, &AM80PedoneAI::Next, FMath::FRandRange(1.5f, 7.f), false);
		}
		return;
	default:
		return;   // fallen, chatting, fighting, sitting, driving: handled by the pedestrian
	}
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

bool AM80PedoneAI::TrySit()
{
	AM80Pedone* P = Cast<AM80Pedone>(GetPawn());
	if (!P || FMath::FRand() >= P->VogliaDiSedersi)
	{
		return false;
	}
	// The nearest chair (tagged M80Sedia, standing, nobody on it) nobody else walks to.
	TSet<AActor*> Taken;
	for (TActorIterator<AM80Pedone> It(GetWorld()); It; ++It)
	{
		if (AActor* S = It->GetSedia())
		{
			Taken.Add(S);
		}
	}
	AActor* Best = nullptr;
	float BestDist = 1500.f;
	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
	{
		if (!It->ActorHasTag(TEXT("M80Sedia")))
		{
			continue;
		}
		const float D = FVector::Dist2D(It->GetActorLocation(), P->GetActorLocation());
		if (D < BestDist && !Taken.Contains(*It) && AM80Pedone::SediaLibera(*It))
		{
			Best = *It;
			BestDist = D;
		}
	}
	return Best && P->VaiASedere(Best);
}

bool AM80PedoneAI::TryDrive()
{
	AM80Pedone* P = Cast<AM80Pedone>(GetPawn());
	if (!P || FMath::FRand() >= P->VogliaDiGuidare)
	{
		return false;
	}
	TSet<AM80Car*> Taken;
	for (TActorIterator<AM80Pedone> It(GetWorld()); It; ++It)
	{
		if (AM80Car* C = It->GetAuto())
		{
			Taken.Add(C);
		}
	}
	AM80Car* Best = nullptr;
	float BestDist = 3000.f;
	for (TActorIterator<AM80Car> It(GetWorld()); It; ++It)
	{
		AM80Car* C = *It;
		const float D = FVector::Dist2D(C->GetActorLocation(), P->GetActorLocation());
		if (!C->bCart && !C->bWrecked && !C->GetController() && C->GetActorUpVector().Z > 0.9f && D < BestDist && !Taken.Contains(C)
			&& FMath::Abs(C->GetSpeedKmh()) < 1.f)
		{
			Best = C;
			BestDist = D;
		}
	}
	return Best && P->VaiAGuidare(Best, FMath::FRandRange(40.f, 90.f));
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

// ---------------------------------------------------------------------------------------------
// Driving a car

AM80AutistaAI::AM80AutistaAI()
{
	PrimaryActorTick.bCanEverTick = true;
}

void AM80AutistaAI::Guida(AM80Car* Car, AM80Pedone* InDriver, float Seconds, float InRadius)
{
	Driver = InDriver;
	MaxTime = Seconds;
	Radius = InRadius;
	Home = Car->GetActorLocation();
	Possess(Car);
	if (UChaosWheeledVehicleMovementComponent* M = Cast<UChaosWheeledVehicleMovementComponent>(Car->GetVehicleMovementComponent()))
	{
		M->SetHandbrakeInput(false);
	}
	NewGoal();
}

void AM80AutistaAI::OnUnPossess()
{
	Super::OnUnPossess();
	// Taken by someone else (the player pulling the driver out): the driver gets out at once.
	if (!bParked)
	{
		bParked = true;
		if (AM80Pedone* D = Driver.Get())
		{
			D->Scendi(true);
		}
	}
	SetLifeSpan(0.5f);
}

void AM80AutistaAI::NewGoal()
{
	Path.Reset();
	Point = 0;
	const AM80Car* Car = Cast<AM80Car>(GetPawn());
	UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	if (!Car || !Nav)
	{
		return;
	}
	// The navigation of the people: the car follows the open ways they walk (the squares and streets), but only
	// where it fits: every leg is checked for walls, tables, chairs as wide as the car (people step aside).
	FNavLocation From;
	if (!Nav->ProjectPointToNavigation(Car->GetActorLocation(), From, FVector(600.f, 600.f, 400.f)))
	{
		return;
	}
	const FBox Box = Car->GetMesh()->CalcBounds(FTransform::Identity).GetBox();
	const float Half = FMath::Max(Box.Max.Y, 70.f) + 25.f;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(M80AutistaWay), false, Car);
	if (AM80Pedone* D = Driver.Get())
	{
		Q.AddIgnoredActor(D);
	}
	FCollisionObjectQueryParams Things;
	Things.AddObjectTypesToQuery(ECC_WorldStatic);
	Things.AddObjectTypesToQuery(ECC_WorldDynamic);
	Things.AddObjectTypesToQuery(ECC_PhysicsBody);
	Things.AddObjectTypesToQuery(ECC_Vehicle);
	auto Clear = [&](const TArray<FVector>& Way)
	{
		for (int32 i = 0; i + 1 < Way.Num(); ++i)
		{
			const FVector A = Way[i], B = Way[i + 1];
			const FVector D = B - A;
			const float Len = D.Size2D();
			if (Len < 1.f)
			{
				continue;
			}
			// A box from the floor's height + 35 cm (kerbs, steps of the paving pass under) up to the roof.
			const FVector Mid = (A + B) * 0.5f + FVector(0.f, 0.f, 95.f);
			const FQuat Rot = FRotationMatrix::MakeFromX(FVector(D.X, D.Y, 0.f)).ToQuat();
			if (GetWorld()->OverlapAnyTestByObjectType(Mid, Rot, Things, FCollisionShape::MakeBox(FVector(Len * 0.5f + 60.f, Half, 60.f)), Q))
			{
				return false;
			}
		}
		return true;
	};
	for (int32 Try = 0; Try < 24; ++Try)
	{
		FNavLocation To;
		if (!Nav->GetRandomReachablePointInRadius(Home, Radius, To) || FVector::Dist2D(To.Location, From.Location) < 1200.f)
		{
			continue;
		}
		// Somewhere ahead first (no U-turns in a narrow place), anywhere only if nothing ahead will do.
		const FVector Local = Car->GetActorTransform().InverseTransformPositionNoScale(To.Location);
		if (Try < 16 && FMath::Abs(FMath::RadiansToDegrees(FMath::Atan2(Local.Y, Local.X))) > 70.f)
		{
			continue;
		}
		// Straight there if the way is free, else along the walking path if that is.
		const TArray<FVector> Straight = {From.Location, To.Location};
		if (Clear(Straight))
		{
			Path = Straight;
			Point = 1;
			return;
		}
		UNavigationPath* P = UNavigationSystemV1::FindPathToLocationSynchronously(GetWorld(), From.Location, To.Location);
		if (P && P->PathPoints.Num() > 1 && Clear(P->PathPoints))
		{
			Path = P->PathPoints;
			Point = 1;
			return;
		}
	}
}

void AM80AutistaAI::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	AM80Car* Car = Cast<AM80Car>(GetPawn());
	UChaosWheeledVehicleMovementComponent* M = Car ? Cast<UChaosWheeledVehicleMovementComponent>(Car->GetVehicleMovementComponent()) : nullptr;
	if (!M)
	{
		return;
	}
	Time += DeltaSeconds;
	HornWait -= DeltaSeconds;
	const float Speed = Car->GetSpeedKmh();
	if (bParked)
	{
		M->SetThrottleInput(0.f);
		M->SetBrakeInput(0.f);
		M->SetHandbrakeInput(true);
		return;
	}
	if (Time > MaxTime)
	{
		bParking = true;
	}
	if (bParking)
	{
		// Stops where it is, handbrake on, and the driver gets out.
		M->SetThrottleInput(0.f);
		M->SetSteeringInput(0.f);
		M->SetBrakeInput(FMath::Abs(Speed) > 1.5f ? 1.f : 0.f);
		if (FMath::Abs(Speed) <= 1.5f)
		{
			M->SetHandbrakeInput(true);
			bParked = true;
			if (AM80Pedone* D = Driver.Get())
			{
				D->Scendi(false);
			}
		}
		return;
	}
	if (Point >= Path.Num())
	{
		NewGoal();
		if (Path.Num() == 0)
		{
			M->SetThrottleInput(0.f);
			M->SetBrakeInput(0.f);
			M->SetHandbrakeInput(true);
			Diario = TEXT("no path");
			return;
		}
	}
	// Aim at the first point of the path a few metres ahead (looking further when faster).
	const FVector Pos = Car->GetActorLocation();
	const float Ahead = 550.f + FMath::Max(Speed, 0.f) * 8.f;
	while (Point < Path.Num() - 1 && FVector::Dist2D(Pos, Path[Point]) < Ahead)
	{
		++Point;
	}
	if (Point == Path.Num() - 1 && FVector::Dist2D(Pos, Path[Point]) < 450.f)
	{
		NewGoal();
		return;
	}
	const FVector Local = Car->GetActorTransform().InverseTransformPositionNoScale(Path[Point]);
	const float Angle = FMath::RadiansToDegrees(FMath::Atan2(Local.Y, Local.X));
	M->SetHandbrakeInput(false);
	const FBox Box = Car->GetMesh()->CalcBounds(FTransform::Identity).GetBox();
	FCollisionQueryParams Q(SCENE_QUERY_STAT(M80Autista), false, Car);
	if (AM80Pedone* D = Driver.Get())
	{
		Q.AddIgnoredActor(D);
	}
	auto PeopleAt = [&](float X0, float X1, TArray<FOverlapResult>& Out)
	{
		const FVector Centre = Car->GetActorTransform().TransformPosition(FVector((X0 + X1) * 0.5f, 0.f, 90.f));
		GetWorld()->OverlapMultiByObjectType(Out, Centre, Car->GetActorQuat(), FCollisionObjectQueryParams(ECC_Pawn),
			FCollisionShape::MakeBox(FVector(FMath::Abs(X1 - X0) * 0.5f, FMath::Max(Box.Max.Y, 80.f) + 20.f, 90.f)), Q);
		return Out.Num() > 0;
	};
	if (Reverse > 0.f)
	{
		// Backing out of a corner: brake held at a standstill puts it in reverse, wheels the other way; never into
		// someone behind.
		TArray<FOverlapResult> Behind;
		if (PeopleAt(Box.Min.X - 300.f, Box.Min.X, Behind))
		{
			Reverse = 0.f;
			M->SetBrakeInput(FMath::Abs(Speed) > 1.5f ? 1.f : 0.f);
			Diario = TEXT("someone behind: no reversing");
			return;
		}
		Reverse -= DeltaSeconds;
		Diario = FString::Printf(TEXT("reversing %.1f s, %.0f km/h"), Reverse, Speed);
		// Reverse gear and a little throttle (not the brake held at a standstill: the gearbox would stay in reverse).
		if (M->GetCurrentGear() >= 0)
		{
			M->SetTargetGear(-1, true);
		}
		M->SetThrottleInput(0.4f);
		M->SetBrakeInput(0.f);
		M->SetSteeringInput(Angle > 0.f ? -1.f : 1.f);
		if (Reverse <= 0.f)
		{
			NewGoal();
		}
		return;
	}
	const float Steer = FMath::Clamp(Angle / 35.f, -1.f, 1.f);
	float Target = Kmh * (1.f - 0.65f * FMath::Clamp(FMath::Abs(Angle) / 70.f, 0.f, 1.f));
	// Someone in front (people, the player): slows down and stops; they step aside; honks at whoever stays there.
	const float Look = 300.f + FMath::Max(Speed, 0.f) * 14.f;
	TArray<FOverlapResult> Hits;
	const bool bSomeone = PeopleAt(Box.Max.X, Box.Max.X + Look, Hits);
	for (const FOverlapResult& H : Hits)
	{
		if (AM80Pedone* P = Cast<AM80Pedone>(H.GetActor()))
		{
			P->Scansati(Car);
		}
	}
	if (bSomeone)
	{
		Target = 0.f;
		Blocked += DeltaSeconds;
		if (Blocked > 2.f && HornWait <= 0.f)
		{
			Car->Horn();
			HornWait = 3.f;
		}
	}
	else
	{
		Blocked = 0.f;
	}
	float Throttle = 0.f, Brake = 0.f;
	if (Speed < -2.f)
	{
		Brake = 1.f;   // still rolling back: stop first
	}
	else if (Target < 1.f)
	{
		Brake = FMath::Abs(Speed) > 2.f ? 1.f : 0.f;
		M->SetHandbrakeInput(FMath::Abs(Speed) <= 2.f);
	}
	else if (Speed < Target - 2.f)
	{
		Throttle = FMath::Clamp((Target - Speed) / 12.f, 0.25f, 0.7f);
	}
	else if (Speed > Target + 4.f)
	{
		Brake = 0.3f;
	}
	else
	{
		Throttle = 0.15f;
	}
	// Against a wall (throttle well on, not moving, after the start): backs off and looks for another way.
	Stuck = (Time > 4.f && Throttle >= 0.25f && FMath::Abs(Speed) < 3.f) ? Stuck + DeltaSeconds : 0.f;
	if (Stuck > 2.f)
	{
		Stuck = 0.f;
		Reverse = 1.8f;
	}
	int32 OnGround = 0;
	for (int32 i = 0; i < M->Wheels.Num(); ++i)
	{
		OnGround += M->GetWheelState(i).bInContact ? 1 : 0;
	}
	Diario = FString::Printf(TEXT("point %d/%d angle %.0f target %.0f speed %.0f throttle %.2f brake %.2f people %d blocked %.1f stuck %.1f gear %d rpm %.0f handbrake %d wheels %d sim %d"),
		Point, Path.Num(), Angle, Target, Speed, Throttle, Brake, Hits.Num(), Blocked, Stuck, M->GetCurrentGear(), M->GetEngineRotationSpeed(),
		M->GetHandbrakeInput() ? 1 : 0, OnGround, Car->GetMesh()->IsSimulatingPhysics());
	// Forward again after backing off (the automatic gearbox stays in reverse with the throttle on).
	if (Throttle > 0.f && M->GetCurrentGear() < 0)
	{
		M->SetTargetGear(1, true);
	}
	M->SetSteeringInput(Steer);
	M->SetThrottleInput(Throttle);
	M->SetBrakeInput(Brake);
}
