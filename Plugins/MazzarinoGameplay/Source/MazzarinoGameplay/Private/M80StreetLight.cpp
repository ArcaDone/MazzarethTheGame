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
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CityMesh(TEXT("/Game/Mazzarino80/Kit/Lamps/SM_M80_LampCity.SM_M80_LampCity"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> GardenMesh(TEXT("/Game/Mazzarino80/Kit/Lamps/SM_M80_LampioneMadonna.SM_M80_LampioneMadonna"));
	WallModel = WallMesh.Succeeded() ? WallMesh.Object : nullptr;
	PoleModel = PoleMesh.Succeeded() ? PoleMesh.Object : nullptr;
	CityModel = CityMesh.Succeeded() ? CityMesh.Object : nullptr;
	GardenModel = GardenMesh.Succeeded() ? GardenMesh.Object : nullptr;
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
	Light->SetIntensity(NightIntensity * N * KindScale());
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

float AM80StreetLight::KindScale() const
{
	switch (Kind)
	{
	case EM80LampKind::Pole: return PoleScale;
	case EM80LampKind::City: return PoleScale * 0.8f;  // three lanterns, lower than the candelabra
	case EM80LampKind::Garden: return 0.6f;            // one small lantern at head height
	default: return 1.f;
	}
}

void AM80StreetLight::PlaceLight()
{
	UStaticMesh* Kinds[] = {WallModel.Get(), PoleModel.Get(), CityModel.Get(), GardenModel.Get()};
	UStaticMesh* Model = MeshOverride ? MeshOverride.Get() : Kinds[FMath::Clamp(int32(Kind), 0, 3)];
	Lantern->SetStaticMesh(Model);
	Light->SetAttenuationRadius(1600.f * FMath::Sqrt(KindScale()));
	// The recovered lamps stand in the street: they block like a post (box collision on their meshes).
	const bool bStanding = Kind == EM80LampKind::City || Kind == EM80LampKind::Garden;
	Lantern->SetCollisionEnabled(bStanding ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
	Lantern->SetCollisionProfileName(bStanding ? TEXT("BlockAll") : TEXT("NoCollision"));
	if (!Model)
	{
		return;
	}
	if (!MeshOverride && bStanding)
	{
		// Measured on the models: the middle of Lamp_city's three lanterns (on arms 45 cm out, 2.2-2.5 m up),
		// the Lampione's lantern on its column.
		Light->SetRelativeLocation(Kind == EM80LampKind::City ? FVector(5, 0, 233) : FVector(4, 0, 150));
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
	// The cook loads each actor on its own, with no ground or neighbours to trace: what the editor built and saved is
	// what ships (rebuilt there, sidewalks climbed the houses and houses stretched to ground that was not there).
	if (IsRunningCookCommandlet())
	{
		return;
	}
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
