#include "M80StreetLight.h"
#include "M80Atmosphere.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
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

	// The whip lamp (Scripts/m80_lampione_frusta_setup.py): a pole stretched to the height, the head on top.
	static ConstructorHelpers::FObjectFinder<UStaticMesh> WhipPoleMesh(TEXT("/Game/Mazzarino80/Kit/Lamps/SM_M80_Frusta_Palo.SM_M80_Frusta_Palo"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> WhipHeadMesh(TEXT("/Game/Mazzarino80/Kit/Lamps/SM_M80_Frusta_Testa.SM_M80_Frusta_Testa"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> Sodium(TEXT("/Game/Mazzarino80/Kit/Lamps/MI_M80_Frusta_VetroSodio.MI_M80_Frusta_VetroSodio"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> Mercury(TEXT("/Game/Mazzarino80/Kit/Lamps/MI_M80_Frusta_VetroMercurio.MI_M80_Frusta_VetroMercurio"));
	WhipPoleModel = WhipPoleMesh.Succeeded() ? WhipPoleMesh.Object : nullptr;
	WhipHeadModel = WhipHeadMesh.Succeeded() ? WhipHeadMesh.Object : nullptr;
	SodiumGlass = Sodium.Succeeded() ? Sodium.Object : nullptr;
	MercuryGlass = Mercury.Succeeded() ? Mercury.Object : nullptr;
	Pole = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Pole"));
	Pole->SetupAttachment(Root);
	Pole->SetMobility(EComponentMobility::Static);
	Pole->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Pole->SetCanEverAffectNavigation(false);
	Pole->SetVisibility(false);

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
	case EM80LampKind::Whip: return 4.f * FMath::Square(PoleHeightM / 9.f); // the road below, 9 m down
	default: return 1.f;
	}
}

void AM80StreetLight::PlaceLight()
{
	// The whip's assets may be made after the class was loaded (the setup script imports them in the same session).
	if (Kind == EM80LampKind::Whip && !WhipHeadModel)
	{
		WhipPoleModel = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Mazzarino80/Kit/Lamps/SM_M80_Frusta_Palo.SM_M80_Frusta_Palo"), nullptr, LOAD_NoWarn);
		WhipHeadModel = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Mazzarino80/Kit/Lamps/SM_M80_Frusta_Testa.SM_M80_Frusta_Testa"), nullptr, LOAD_NoWarn);
		SodiumGlass = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Mazzarino80/Kit/Lamps/MI_M80_Frusta_VetroSodio.MI_M80_Frusta_VetroSodio"), nullptr, LOAD_NoWarn);
		MercuryGlass = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Mazzarino80/Kit/Lamps/MI_M80_Frusta_VetroMercurio.MI_M80_Frusta_VetroMercurio"), nullptr, LOAD_NoWarn);
	}
	UStaticMesh* Kinds[] = {WallModel.Get(), PoleModel.Get(), CityModel.Get(), GardenModel.Get(), WhipHeadModel.Get()};
	UStaticMesh* Model = MeshOverride ? MeshOverride.Get() : Kinds[FMath::Clamp(int32(Kind), 0, 4)];
	Lantern->SetStaticMesh(Model);
	Lantern->SetRelativeLocation(FVector::ZeroVector);
	Light->SetAttenuationRadius(1600.f * FMath::Sqrt(KindScale()));
	Light->SetTemperature(2300.f);
	const bool bWhip = Kind == EM80LampKind::Whip;
	// The whip's glass colour is an override of its "Vetro" slot: dropped when the lamp becomes another kind.
	for (int32 i = 0; i < Lantern->OverrideMaterials.Num(); ++i)
	{
		const UMaterialInterface* M = Lantern->OverrideMaterials[i];
		if (M && (M == SodiumGlass || M == MercuryGlass))
		{
			Lantern->SetMaterial(i, nullptr);
		}
	}
	// A whip lamp is seen from far down the road.
	Lantern->SetCullDistance(bWhip ? 0.f : 8000.f);
	Pole->SetCullDistance(0.f);
	Pole->SetVisibility(bWhip);
	Pole->SetStaticMesh(bWhip ? WhipPoleModel.Get() : nullptr);
	Pole->SetCollisionEnabled(bWhip ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
	Pole->SetCollisionProfileName(bWhip ? TEXT("BlockAll") : TEXT("NoCollision"));
	if (bWhip && !MeshOverride)
	{
		// Measured on the model (M80_LampioneFrusta.json): the head's luminaire sits 206 cm above its joint with
		// the pole and 175 cm out along +X; the 1 m pole is stretched to bring it to the chosen height.
		const double PoleCm = FMath::Max(100.0, PoleHeightM * 100.0 - 206.0);
		Pole->SetRelativeScale3D(FVector(1, 1, PoleCm / 100.0));
		Lantern->SetRelativeLocation(FVector(0, 0, PoleCm));
		const int32 GlassSlot = Lantern->GetMaterialIndex(TEXT("Vetro"));
		if (GlassSlot != INDEX_NONE)
		{
			Lantern->SetMaterial(GlassSlot, bMercury ? MercuryGlass.Get() : SodiumGlass.Get());
		}
		Light->SetRelativeLocation(FVector(175, 0, PoleCm + 194));
		Light->SetTemperature(bMercury ? 4200.f : 2000.f);
		return;
	}
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
