#include "M80StreetLight.h"
#include "M80Atmosphere.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "UObject/ConstructorHelpers.h"

AM80StreetLight::AM80StreetLight()
{
	PrimaryActorTick.bCanEverTick = false;
	USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);
	Root->SetMobility(EComponentMobility::Static);

	Lantern = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Lantern"));
	Lantern->SetupAttachment(Root);
	Lantern->SetMobility(EComponentMobility::Static);
	Lantern->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Lantern->SetCanEverAffectNavigation(false);
	Lantern->LDMaxDrawDistance = 8000.f;
	static ConstructorHelpers::FObjectFinder<UStaticMesh> WallMesh(TEXT("/Game/Mazzarino80/Kit/Lamps/SM_M80_Lampione_Muro.SM_M80_Lampione_Muro"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> PoleMesh(TEXT("/Game/Mazzarino80/Kit/Lamps/SM_M80_Lampione_Palo.SM_M80_Lampione_Palo"));
	WallModel = WallMesh.Succeeded() ? WallMesh.Object : nullptr;
	PoleModel = PoleMesh.Succeeded() ? PoleMesh.Object : nullptr;
	Lantern->SetStaticMesh(WallModel);

	// Warm sodium-like light, no shadows: dozens of lamps stay cheap at night.
	Light = CreateDefaultSubobject<UPointLightComponent>(TEXT("Light"));
	Light->SetupAttachment(Root);
	Light->SetRelativeLocation(FVector(0, 0, -20));
	Light->SetMobility(EComponentMobility::Movable);
	Light->SetIntensityUnits(ELightUnits::Candelas);
	Light->SetIntensity(0.f);
	Light->SetAttenuationRadius(1600.f);
	Light->SetSourceRadius(8.f);
	Light->SetUseTemperature(true);
	Light->SetTemperature(2300.f);
	Light->SetCastShadows(false);
	Light->SetVisibility(false);
	Light->SetIndirectLightingIntensity(0.6f);
	Light->SetVolumetricScatteringIntensity(0.4f);
	Light->bAffectsWorld = true;
}

void AM80StreetLight::SetNight(float Night)
{
	const float N = bBroken ? 0.f : FMath::Clamp(Night, 0.f, 1.f);
	Light->SetIntensity(NightIntensity * N * (Kind == EM80LampKind::Pole ? PoleScale : 1.f));
	Light->SetVisibility(N > 0.02f);
}

void AM80StreetLight::SetNightForAll(const UWorld* World, float Night)
{
	if (!World)
	{
		return;
	}
	for (TActorIterator<AM80StreetLight> It(World); It; ++It)
	{
		It->SetNight(Night);
	}
}

void AM80StreetLight::PlaceLight()
{
	UStaticMesh* Model = MeshOverride ? MeshOverride.Get() : (Kind == EM80LampKind::Pole ? PoleModel.Get() : WallModel.Get());
	Lantern->SetStaticMesh(Model);
	const float Scale = Kind == EM80LampKind::Pole ? PoleScale : 1.f;
	Light->SetAttenuationRadius(1600.f * FMath::Sqrt(Scale));
	if (!Model)
	{
		return;
	}
	// The glass: for a wall lamp the far end of the bracket, for a pole the top of the candelabra.
	const FBox B = Model->GetBoundingBox();
	FVector At(0, 0, B.Max.Z - 40.0);
	if (Kind == EM80LampKind::Wall)
	{
		const FVector2D Far = FMath::Abs(B.Min.X) > FMath::Abs(B.Max.X) ? FVector2D(B.Min.X, 0) : FVector2D(B.Max.X, 0);
		const FVector2D FarY = FMath::Abs(B.Min.Y) > FMath::Abs(B.Max.Y) ? FVector2D(0, B.Min.Y) : FVector2D(0, B.Max.Y);
		const FVector2D End = Far.Size() > FarY.Size() ? Far : FarY;
		At = FVector(End * 0.9, B.Max.Z - 35.0);
	}
	Light->SetRelativeLocation(At);
}

void AM80StreetLight::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	PlaceLight();
	const AM80Atmosphere* Atmosphere = AM80Atmosphere::Find(this);
	SetNight(Atmosphere ? Atmosphere->GetStreetLights() : 0.f);
}

void AM80StreetLight::BeginPlay()
{
	Super::BeginPlay();
	// Lamps streamed in later (World Partition) take the current light of the Atmosfera.
	const AM80Atmosphere* Atmosphere = AM80Atmosphere::Find(this);
	SetNight(Atmosphere ? Atmosphere->GetStreetLights() : 0.f);
}
