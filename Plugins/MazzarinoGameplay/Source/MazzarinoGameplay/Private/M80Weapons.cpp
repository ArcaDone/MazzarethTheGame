#include "M80Weapons.h"
#include "M80Vitals.h"
#include "AnimationRuntime.h"
#include "Engine/SkeletalMesh.h"
#include "Components/DecalComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/DamageEvents.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"
#include "Particles/ParticleSystem.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "Sound/SoundBase.h"

namespace
{
const TCHAR* const ShotSound = TEXT("/Game/FPWeapon/Audio/FirstPersonTemplateWeaponFire02.FirstPersonTemplateWeaponFire02");
const TCHAR* const HoleDecal = TEXT("/Game/Mazzarino80/Weapons/M_M80_Foro.M_M80_Foro");
const TCHAR* const HitDust = TEXT("/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Hit/P_Concrete.P_Concrete");
const TCHAR* const HitMetal = TEXT("/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Sparks/P_Sparks_C.P_Sparks_C");
const TCHAR* const HitBlood = TEXT("/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Blood/P_Blood_Splat_Cone.P_Blood_Splat_Cone");

template <typename T>
T* LoadPath(const TCHAR* Path)
{
	return Path ? Cast<T>(StaticLoadObject(T::StaticClass(), nullptr, Path)) : nullptr;
}

FM80WeaponSpec MakeSpecs(EM80Weapon W)
{
	FM80WeaponSpec S;
	switch (W)
	{
	case EM80Weapon::Pugni:
		S.Name = TEXT("Pugni"); S.Slot = 0; S.Pose = EM80WeaponPose::Unarmed;
		S.Damage = 8.f; S.Interval = 0.45f; S.Range = 110.f; S.Impulse = 150.f;
		break;
	case EM80Weapon::Coltello:
		S.Name = TEXT("Coltello"); S.Slot = 1; S.Mesh = TEXT("/Game/Mazzarino80/Weapons/SM_M80_Coltello.SM_M80_Coltello");
		S.Pose = EM80WeaponPose::Melee; S.Damage = 25.f; S.Interval = 0.5f; S.Range = 120.f; S.Impulse = 100.f;
		S.Glow = FLinearColor(0.7f, 0.85f, 1.f);
		break;
	case EM80Weapon::Mazza:
		S.Name = TEXT("Mazza"); S.Slot = 1; S.Mesh = TEXT("/Game/Mazzarino80/Weapons/SM_M80_Mazza.SM_M80_Mazza");
		S.Pose = EM80WeaponPose::Melee; S.Damage = 35.f; S.Interval = 0.8f; S.Range = 160.f; S.Impulse = 900.f;
		S.Glow = FLinearColor(0.7f, 0.85f, 1.f);
		break;
	case EM80Weapon::Revolver:
		S.Name = TEXT("Revolver"); S.Slot = 2; S.Mesh = TEXT("/Game/Mazzarino80/Weapons/SM_M80_Revolver.SM_M80_Revolver");
		S.Pose = EM80WeaponPose::Pistol; S.bMelee = false; S.Damage = 45.f; S.Interval = 0.55f; S.Clip = 6; S.MaxAmmo = 120;
		S.PickupAmmo = 24; S.ReloadTime = 2.f; S.Range = 6000.f; S.SpreadDeg = 1.f; S.Impulse = 2500.f; S.FireSound = ShotSound;
		S.Glow = FLinearColor(1.f, 0.75f, 0.25f);
		break;
	case EM80Weapon::Beretta:
		S.Name = TEXT("Beretta 92"); S.Slot = 2; S.Mesh = TEXT("/Game/Mazzarino80/Weapons/SM_M80_Beretta.SM_M80_Beretta");
		S.Pose = EM80WeaponPose::Pistol; S.bMelee = false; S.Damage = 25.f; S.Interval = 0.22f; S.Clip = 15; S.MaxAmmo = 180;
		S.PickupAmmo = 45; S.ReloadTime = 1.4f; S.Range = 5000.f; S.SpreadDeg = 1.6f; S.Impulse = 1500.f; S.FireSound = ShotSound;
		S.Glow = FLinearColor(1.f, 0.75f, 0.25f);
		break;
	case EM80Weapon::Lupara:
		S.Name = TEXT("Lupara"); S.Slot = 3; S.Mesh = TEXT("/Game/Mazzarino80/Weapons/SM_M80_Lupara.SM_M80_Lupara");
		S.Pose = EM80WeaponPose::Rifle; S.bMelee = false; S.Damage = 14.f; S.Pellets = 8; S.Interval = 0.9f; S.Clip = 2;
		S.MaxAmmo = 60; S.PickupAmmo = 16; S.ReloadTime = 2.2f; S.Range = 2500.f; S.SpreadDeg = 5.f; S.Impulse = 1200.f;
		S.FireSound = TEXT("/Game/Mazzarino80/Audio/M80_Lupara.M80_Lupara"); S.Glow = FLinearColor(1.f, 0.35f, 0.2f);
		break;
	}
	return S;
}
}

/**
 * Where the grip goes in the hand bone's space, from the hand's own bones (rest pose): the barrel along
 * the knuckles (wrist -> middle finger), the top towards the thumb; blades and bats stick out of the fist
 * on the thumb side.
 */
FTransform M80GripInHand(const USkeletalMesh* Mesh, bool bBlade)
{
	if (!Mesh)
	{
		return FTransform::Identity;
	}
	const FReferenceSkeleton& Ref = Mesh->GetRefSkeleton();
	const int32 H = Ref.FindBoneIndex(TEXT("hand_r"));
	const int32 Mid = Ref.FindBoneIndex(TEXT("middle_01_r"));
	const int32 Thumb = Ref.FindBoneIndex(TEXT("thumb_01_r"));
	const int32 Index = Ref.FindBoneIndex(TEXT("index_01_r"));
	if (H == INDEX_NONE || Mid == INDEX_NONE || Thumb == INDEX_NONE)
	{
		return FTransform::Identity;
	}
	const FTransform HandCS = FAnimationRuntime::GetComponentSpaceTransformRefPose(Ref, H);
	const FVector MidL = FAnimationRuntime::GetComponentSpaceTransformRefPose(Ref, Mid).GetRelativeTransform(HandCS).GetLocation();
	const FVector ThumbL = FAnimationRuntime::GetComponentSpaceTransformRefPose(Ref, Thumb).GetRelativeTransform(HandCS).GetLocation();
	const FVector IndexL = Index != INDEX_NONE ? FAnimationRuntime::GetComponentSpaceTransformRefPose(Ref, Index).GetRelativeTransform(HandCS).GetLocation() : MidL;
	const FVector Fingers = MidL.GetSafeNormal();
	// Thumb side, square to the fingers.
	const FVector Side = (ThumbL - Fingers * (ThumbL | Fingers)).GetSafeNormal();
	// The palm: away from the back of the hand (the knuckles' plane normal, towards the thumb's root).
	const FVector Palm = (FVector::CrossProduct(Fingers, Side)).GetSafeNormal();
	const FVector Centre = MidL * 0.5f + (IndexL - MidL) * 0.3f;
	if (bBlade)
	{
		// Fist closed on the handle: handle across the palm, the blade out on the thumb side.
		return FTransform(FRotationMatrix::MakeFromXZ(Side, Fingers).ToQuat(), Centre + Palm * 2.5f);
	}
	// Gun: barrel along the knuckles, a bit up; the grip goes down into the fist (palm side).
	const FVector Barrel = (Fingers + Side * 0.25f).GetSafeNormal();
	return FTransform(FRotationMatrix::MakeFromXZ(Barrel, Side).ToQuat(), Centre * 0.6f + Palm * 2.f);
}

FCollisionObjectQueryParams M80ShotObjects()
{
	// Shots hit the world, people and vehicles (the visibility channel misses the cars' bodies).
	FCollisionObjectQueryParams O;
	for (const ECollisionChannel C : {ECC_WorldStatic, ECC_WorldDynamic, ECC_Pawn, ECC_PhysicsBody, ECC_Vehicle, ECC_Destructible})
	{
		O.AddObjectTypesToQuery(C);
	}
	return O;
}

const FM80WeaponSpec& M80WeaponSpec(EM80Weapon W)
{
	static const FM80WeaponSpec Table[] = {MakeSpecs(EM80Weapon::Pugni), MakeSpecs(EM80Weapon::Coltello), MakeSpecs(EM80Weapon::Mazza),
		MakeSpecs(EM80Weapon::Revolver), MakeSpecs(EM80Weapon::Beretta), MakeSpecs(EM80Weapon::Lupara)};
	return Table[FMath::Clamp(int32(W), 0, int32(UE_ARRAY_COUNT(Table)) - 1)];
}

// ---------------------------------------------------------------------------------------------
// Inventory

UM80WeaponInventory::UM80WeaponInventory()
{
	PrimaryComponentTick.bCanEverTick = true;
	Slots.SetNum(4);
	Slots[0].bHas = true;
	Slots[0].Weapon = EM80Weapon::Pugni;
}

void UM80WeaponInventory::BeginPlay()
{
	Super::BeginPlay();
	UpdateHeldMesh();
}

USkeletalMeshComponent* UM80WeaponInventory::HandMesh() const
{
	const ACharacter* C = Cast<ACharacter>(GetOwner());
	if (!C)
	{
		return nullptr;
	}
	// The MetaHuman body is the leader of the clothes (they follow its pose).
	TInlineComponentArray<USkeletalMeshComponent*> Meshes(C);
	for (USkeletalMeshComponent* M : Meshes)
	{
		if (USkeletalMeshComponent* Leader = Cast<USkeletalMeshComponent>(M->LeaderPoseComponent.Get()))
		{
			return Leader;
		}
	}
	return C->GetMesh();
}

void UM80WeaponInventory::UpdateHeldMesh()
{
	const FM80WeaponSpec& S = CurrentSpec();
	UStaticMesh* Mesh = LoadPath<UStaticMesh>(S.Mesh);
	USkeletalMeshComponent* Hand = HandMesh();
	if (!Mesh || !Hand)
	{
		if (Held)
		{
			Held->SetVisibility(false);
		}
		return;
	}
	if (!Held)
	{
		Held = NewObject<UStaticMeshComponent>(GetOwner(), TEXT("M80Arma"));
		Held->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Held->SetCastShadow(true);
		Held->RegisterComponent();
	}
	Held->SetStaticMesh(Mesh);
	Held->SetVisibility(true);
	// Grip in the palm: the weapon meshes have the grip at the origin, barrel along +X, top along +Z.
	// UEFN/MetaHuman hand_r: X along the fingers, palm towards -Y... (tuned with the weapons test).
	Held->AttachToComponent(Hand, FAttachmentTransformRules::SnapToTargetNotIncludingScale, TEXT("hand_r"));
	const FTransform Grip = M80GripInHand(Hand->GetSkeletalMeshAsset(), S.Pose == EM80WeaponPose::Melee);
	Held->SetRelativeTransform(Grip);
}

void UM80WeaponInventory::HideWeapon()
{
	if (Held)
	{
		Held->SetVisibility(false);
	}
	bTrigger = false;
}

bool UM80WeaponInventory::Give(EM80Weapon Weapon, int32 Ammo, bool bSelect)
{
	const FM80WeaponSpec& S = M80WeaponSpec(Weapon);
	FM80WeaponSlot& Slot = Slots[S.Slot];
	if (Ammo < 0)
	{
		Ammo = S.PickupAmmo;
	}
	if (Slot.bHas && Slot.Weapon == Weapon)
	{
		if (S.bMelee || Slot.Reserve + Slot.InClip >= S.MaxAmmo)
		{
			return false;
		}
		Slot.Reserve = FMath::Min(S.MaxAmmo - Slot.InClip, Slot.Reserve + Ammo);
		return true;
	}
	// Another weapon of the same kind: swap (GTA keeps one per slot).
	Slot.bHas = true;
	Slot.Weapon = Weapon;
	Slot.InClip = FMath::Min(S.Clip, Ammo);
	Slot.Reserve = FMath::Min(S.MaxAmmo, Ammo) - Slot.InClip;
	if (bSelect)
	{
		SelectSlot(S.Slot);
	}
	return true;
}

void UM80WeaponInventory::SelectSlot(int32 Slot)
{
	if (!Slots.IsValidIndex(Slot) || !Slots[Slot].bHas)
	{
		return;
	}
	Current = Slot;
	ReloadLeft = 0.f;
	Cooldown = FMath::Max(Cooldown, 0.25f);  // drawing the weapon
	UpdateHeldMesh();
}

void UM80WeaponInventory::Cycle(int32 Dir)
{
	for (int32 i = 1; i <= Slots.Num(); ++i)
	{
		const int32 S = (Current + Dir * i + Slots.Num() * 4) % Slots.Num();
		if (Slots[S].bHas)
		{
			SelectSlot(S);
			return;
		}
	}
}

void UM80WeaponInventory::DropCurrent()
{
	if (Current == 0)
	{
		return;
	}
	FM80WeaponSlot& Slot = Slots[Current];
	const AActor* Owner = GetOwner();
	FActorSpawnParameters P;
	P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	const FVector At = Owner->GetActorLocation() + Owner->GetActorForwardVector() * 90.f;
	if (AM80WeaponPickup* Pick = GetWorld()->SpawnActor<AM80WeaponPickup>(At, FRotator::ZeroRotator, P))
	{
		Pick->RespawnTime = 0.f;
		Pick->LifeTime = 120.f;
		Pick->SetWeapon(Slot.Weapon, M80WeaponSpec(Slot.Weapon).bMelee ? 0 : Slot.InClip + Slot.Reserve);
	}
	Slot = FM80WeaponSlot();
	SelectSlot(0);
}

void UM80WeaponInventory::Reload()
{
	const FM80WeaponSpec& S = CurrentSpec();
	const FM80WeaponSlot& Slot = Slots[Current];
	if (S.bMelee || ReloadLeft > 0.f || Slot.InClip >= S.Clip || Slot.Reserve <= 0)
	{
		return;
	}
	ReloadLeft = S.ReloadTime;
}

void UM80WeaponInventory::SetTrigger(bool bDown, FVector AimPoint)
{
	bTrigger = bDown;
	TriggerAim = AimPoint;
}

void UM80WeaponInventory::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	Cooldown -= DeltaTime;
	SinceLastFire += DeltaTime;
	if (ReloadLeft > 0.f)
	{
		ReloadLeft -= DeltaTime;
		if (ReloadLeft <= 0.f)
		{
			FM80WeaponSlot& Slot = Slots[Current];
			const int32 Take = FMath::Min(CurrentSpec().Clip - Slot.InClip, Slot.Reserve);
			Slot.InClip += Take;
			Slot.Reserve -= Take;
		}
	}
	if (bTrigger)
	{
		TryFire(TriggerAim);
	}
}

bool UM80WeaponInventory::TryFire(FVector AimPoint)
{
	const FM80WeaponSpec& S = CurrentSpec();
	if (Cooldown > 0.f || ReloadLeft > 0.f)
	{
		return false;
	}
	if (const UM80VitalsComponent* V = GetOwner()->FindComponentByClass<UM80VitalsComponent>(); V && V->IsDead())
	{
		return false;
	}
	FM80WeaponSlot& Slot = Slots[Current];
	if (!S.bMelee)
	{
		if (Slot.InClip <= 0)
		{
			// Empty: reload on its own, as in GTA.
			Reload();
			return false;
		}
		--Slot.InClip;
		FireRanged(S, AimPoint);
		if (Slot.InClip == 0)
		{
			Cooldown = S.Interval;
			Reload();
		}
	}
	else
	{
		FireMelee(S);
	}
	Cooldown = FMath::Max(Cooldown, S.Interval);
	SinceLastFire = 0.f;
	return true;
}

FVector UM80WeaponInventory::MuzzleLocation() const
{
	if (Held && Held->IsVisible() && Held->DoesSocketExist(TEXT("Muzzle")))
	{
		return Held->GetSocketLocation(TEXT("Muzzle"));
	}
	const USkeletalMeshComponent* Hand = HandMesh();
	return Hand ? Hand->GetSocketLocation(TEXT("hand_r")) : GetOwner()->GetActorLocation();
}

void UM80WeaponInventory::FireRanged(const FM80WeaponSpec& S, const FVector& AimPoint)
{
	UWorld* World = GetWorld();
	const FVector Muzzle = MuzzleLocation();
	const FVector Base = (AimPoint - Muzzle).GetSafeNormal();
	FCollisionQueryParams Q(SCENE_QUERY_STAT(M80Shot), true, GetOwner());
	Q.bReturnPhysicalMaterial = true;
	for (int32 i = 0; i < S.Pellets; ++i)
	{
		const FVector Dir = FMath::VRandCone(Base, FMath::DegreesToRadians(S.SpreadDeg));
		FHitResult Hit;
		if (World->LineTraceSingleByObjectType(Hit, Muzzle, Muzzle + Dir * S.Range, M80ShotObjects(), Q))
		{
			Impact(Hit, Dir, S);
		}
	}
	if (USoundBase* Snd = LoadPath<USoundBase>(S.FireSound))
	{
		UGameplayStatics::PlaySoundAtLocation(this, Snd, Muzzle, S.Pellets > 1 ? 1.4f : 1.f, S.Pellets > 1 ? 1.f : (S.Damage > 30.f ? 0.85f : 1.05f));
	}
	// Muzzle flash: a short bright light.
	UPointLightComponent* Flash = NewObject<UPointLightComponent>(GetOwner());
	Flash->SetIntensity(30000.f);
	Flash->SetAttenuationRadius(600.f);
	Flash->SetLightColor(FLinearColor(1.f, 0.75f, 0.4f));
	Flash->SetCastShadows(false);
	Flash->SetWorldLocation(Muzzle);
	Flash->RegisterComponent();
	FTimerHandle T;
	World->GetTimerManager().SetTimer(T, FTimerDelegate::CreateWeakLambda(Flash, [Flash]() { Flash->DestroyComponent(); }), 0.05f, false);
	// Let the town hear it (pedestrians and police will listen later).
	if (APawn* P = Cast<APawn>(GetOwner()))
	{
		P->MakeNoise(1.f, P, Muzzle, 5000.f, TEXT("Sparo"));
	}
}

void UM80WeaponInventory::FireMelee(const FM80WeaponSpec& S)
{
	AActor* Owner = GetOwner();
	const FVector From = Owner->GetActorLocation() + FVector(0, 0, 30.f);
	const FVector To = From + Owner->GetActorForwardVector() * S.Range;
	TArray<FHitResult> Hits;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(M80Melee), false, Owner);
	GetWorld()->SweepMultiByChannel(Hits, From, To, FQuat::Identity, ECC_Pawn, FCollisionShape::MakeSphere(35.f), Q);
	TSet<AActor*> Done;
	for (const FHitResult& Hit : Hits)
	{
		AActor* A = Hit.GetActor();
		if (!A || Done.Contains(A))
		{
			continue;
		}
		Done.Add(A);
		Impact(Hit, Owner->GetActorForwardVector(), S);
	}
}

void UM80WeaponInventory::Impact(const FHitResult& Hit, const FVector& Dir, const FM80WeaponSpec& S)
{
	AActor* A = Hit.GetActor();
	APawn* Instigator = Cast<APawn>(GetOwner());
	if (A)
	{
		UGameplayStatics::ApplyPointDamage(A, S.Damage, Dir, Hit, Instigator ? Instigator->GetController() : nullptr, GetOwner(), UDamageType::StaticClass());
	}
	if (UPrimitiveComponent* C = Hit.GetComponent(); C && C->IsSimulatingPhysics())
	{
		C->AddImpulseAtLocation(Dir * S.Impulse * (C->GetMass() > 200.f ? 1.f : 0.2f), Hit.ImpactPoint, Hit.BoneName);
	}
	if (S.bMelee)
	{
		UGameplayStatics::PlaySoundAtLocation(this, LoadPath<USoundBase>(TEXT("/Game/Mazzarino80/Audio/M80_Colpo.M80_Colpo")), Hit.ImpactPoint);
		return;
	}
	// Impact effects: blood on people, sparks on vehicles and metal, dust and a hole elsewhere.
	const bool bFlesh = A && A->IsA<ACharacter>();
	const bool bMetal = A && (A->IsA<APawn>() && !bFlesh);
	if (UParticleSystem* Fx = LoadPath<UParticleSystem>(bFlesh ? HitBlood : (bMetal ? HitMetal : HitDust)))
	{
		UGameplayStatics::SpawnEmitterAtLocation(this, Fx, Hit.ImpactPoint, Hit.ImpactNormal.Rotation(), FVector(bFlesh ? 0.5f : 0.35f));
	}
	if (!bFlesh)
	{
		if (UMaterialInterface* Decal = LoadPath<UMaterialInterface>(HoleDecal))
		{
			FRotator R = (-Hit.ImpactNormal).Rotation();
			R.Roll = FMath::FRandRange(0.f, 360.f);
			if (UDecalComponent* D = UGameplayStatics::SpawnDecalAttached(Decal, FVector(4.f, 4.f, 4.f), Hit.GetComponent(), NAME_None,
				Hit.ImpactPoint, R, EAttachLocation::KeepWorldPosition, 60.f))
			{
				D->SetFadeScreenSize(0.002f);
			}
		}
	}
}

// ---------------------------------------------------------------------------------------------
// Pickup

AM80WeaponPickup::AM80WeaponPickup()
{
	PrimaryActorTick.bCanEverTick = true;
	Trigger = CreateDefaultSubobject<USphereComponent>(TEXT("Trigger"));
	Trigger->SetSphereRadius(70.f);
	Trigger->SetCollisionProfileName(TEXT("OverlapAllDynamic"));
	Trigger->SetGenerateOverlapEvents(true);
	RootComponent = Trigger;
	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Trigger);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetRelativeScale3D(FVector(2.2f));
	Halo = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Halo"));
	Halo->SetupAttachment(Trigger);
	Halo->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Halo->SetCastShadow(false);
	static ConstructorHelpers::FObjectFinderOptional<UStaticMesh> Disc(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	Halo->SetStaticMesh(Disc.Get());
	Halo->SetRelativeScale3D(FVector(0.9f, 0.9f, 0.01f));
	Halo->SetRelativeLocation(FVector(0, 0, -50.f));
	Glow = CreateDefaultSubobject<UPointLightComponent>(TEXT("Glow"));
	Glow->SetupAttachment(Trigger);
	Glow->SetIntensity(2500.f);
	Glow->SetAttenuationRadius(220.f);
	Glow->SetCastShadows(false);
}

void AM80WeaponPickup::BeginPlay()
{
	Super::BeginPlay();
	Trigger->OnComponentBeginOverlap.AddUniqueDynamic(this, &AM80WeaponPickup::OnOverlap);
	SetWeapon(Weapon, Ammo);
	Pause = LifeTime > 0.f ? 1.5f : 0.f;
}

void AM80WeaponPickup::SetWeapon(EM80Weapon InWeapon, int32 InAmmo)
{
	Weapon = InWeapon;
	Ammo = InAmmo;
	const FM80WeaponSpec& S = M80WeaponSpec(Weapon);
	Mesh->SetStaticMesh(LoadPath<UStaticMesh>(S.Mesh));
	Glow->SetLightColor(S.Glow);
	if (UMaterialInterface* M = LoadPath<UMaterialInterface>(TEXT("/Game/Mazzarino80/Weapons/M_M80_Bagliore.M_M80_Bagliore")))
	{
		UMaterialInstanceDynamic* D = Halo->CreateDynamicMaterialInstance(0, M);
		D->SetVectorParameterValue(TEXT("Colore"), S.Glow);
	}
	// Centre the mesh on the pivot so it turns on itself.
	if (Mesh->GetStaticMesh())
	{
		const FVector C = Mesh->GetStaticMesh()->GetBounds().Origin * Mesh->GetRelativeScale3D();
		Mesh->SetRelativeLocation(-C + FVector(0, 0, 10.f));
	}
}

void AM80WeaponPickup::SetAvailable(bool bOn)
{
	bAvailable = bOn;
	Mesh->SetVisibility(bOn);
	Glow->SetVisibility(bOn);
	Halo->SetVisibility(bOn);
	Trigger->SetCollisionEnabled(bOn ? ECollisionEnabled::QueryOnly : ECollisionEnabled::NoCollision);
}

void AM80WeaponPickup::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	Age += DeltaSeconds;
	Pause -= DeltaSeconds;
	Mesh->AddRelativeRotation(FRotator(0.f, 90.f * DeltaSeconds, 0.f));
	Glow->SetIntensity(2000.f + 900.f * FMath::Sin(Age * 4.f));
	const float Pulse = 0.9f + 0.12f * FMath::Sin(Age * 4.f);
	Halo->SetRelativeScale3D(FVector(0.9f * Pulse, 0.9f * Pulse, 0.01f));
	if (!bAvailable)
	{
		Hidden += DeltaSeconds;
		if (RespawnTime > 0.f && Hidden > RespawnTime)
		{
			SetAvailable(true);
		}
		return;
	}
	if (LifeTime > 0.f && Age > LifeTime)
	{
		Destroy();
		return;
	}
	if (Pause <= 0.f)
	{
		// Somebody already standing on it (dropped at the feet, or waiting for the pause to end).
		TArray<AActor*> Over;
		Trigger->GetOverlappingActors(Over, ACharacter::StaticClass());
		for (AActor* A : Over)
		{
			OnOverlap(Trigger, A, nullptr, 0, false, FHitResult());
			if (!bAvailable || IsActorBeingDestroyed())
			{
				return;
			}
		}
	}
}

void AM80WeaponPickup::OnOverlap(UPrimitiveComponent* OverlappedComp, AActor* Other, UPrimitiveComponent* OtherComp, int32 BodyIndex, bool bFromSweep, const FHitResult& Sweep)
{
	if (!bAvailable || Pause > 0.f)
	{
		return;
	}
	UM80WeaponInventory* Inv = Other ? Other->FindComponentByClass<UM80WeaponInventory>() : nullptr;
	if (!Inv || !Inv->Give(Weapon, Ammo))
	{
		return;
	}
	UGameplayStatics::PlaySound2D(this, LoadPath<USoundBase>(TEXT("/Engine/VREditor/Sounds/UI/Click_on_Button.Click_on_Button")));
	if (RespawnTime > 0.f && LifeTime <= 0.f)
	{
		Hidden = 0.f;
		SetAvailable(false);
	}
	else
	{
		Destroy();
	}
}
