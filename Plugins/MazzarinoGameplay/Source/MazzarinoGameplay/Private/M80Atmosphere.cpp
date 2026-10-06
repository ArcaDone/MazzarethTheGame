#include "M80Atmosphere.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/VolumetricCloudComponent.h"
#include "EngineUtils.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
/** Values that change with the weather. */
struct FWeatherLook
{
	float MieScale;          // haze in the sky (sun halo, pale horizon)
	FLinearColor MieAbsorption;
	float FogDensity;
	float ValleyFogDensity;
	float AerialDistanceScale;
	float CloudCoverage;
	FLinearColor Tint;
	float SunScale;
};

FWeatherLook LookFor(EM80Weather Weather)
{
	switch (Weather)
	{
	case EM80Weather::Clear:
		return {0.003f, FLinearColor(0.44f, 0.44f, 0.44f), 0.0012f, 0.004f, 1.f, 0.25f, FLinearColor::White, 1.f};
	case EM80Weather::Scirocco:
		// Sahara dust: yellow-brown sky, flat light, distant hills gone.
		return {0.02f, FLinearColor(0.1f, 0.3f, 0.75f), 0.008f, 0.012f, 3.f, 0.35f, FLinearColor(1.f, 0.93f, 0.8f), 0.7f};
	case EM80Weather::Cloudy:
		return {0.006f, FLinearColor(0.44f, 0.44f, 0.44f), 0.003f, 0.008f, 1.5f, 0.8f, FLinearColor(0.96f, 0.98f, 1.f), 0.55f};
	case EM80Weather::Hazy:
	default:
		// Sicilian summer: milky horizon, warm haze in the valleys.
		return {0.007f, FLinearColor(0.3f, 0.36f, 0.5f), 0.002f, 0.007f, 1.5f, 0.4f, FLinearColor(1.f, 0.98f, 0.94f), 1.f};
	}
}

FVector4 Lerp4(const FVector4& A, const FVector4& B, float T) { return A + (B - A) * T; }
}

AM80Atmosphere::AM80Atmosphere()
{
#if WITH_EDITORONLY_DATA
	bIsSpatiallyLoaded = false;   // World Partition: sky and horizon are always loaded, whatever region is open
#endif
	PrimaryActorTick.bCanEverTick = true;
	USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);

	Sun = CreateDefaultSubobject<UDirectionalLightComponent>(TEXT("Sun"));
	Sun->SetupAttachment(Root);
	Sun->SetMobility(EComponentMobility::Movable);
	Sun->SetAtmosphereSunLight(true);
	Sun->SetAtmosphereSunLightIndex(0);
	Sun->SetLightSourceAngle(0.6f);
	Sun->bCastCloudShadows = true;
	Sun->bEnableLightShaftBloom = true;
	Sun->SetBloomScale(0.15f);
	Sun->SetUseTemperature(true);
	Sun->SetTemperature(5600.f);
	Sun->SetVolumetricScatteringIntensity(1.2f);

	Moon = CreateDefaultSubobject<UDirectionalLightComponent>(TEXT("Moon"));
	Moon->SetupAttachment(Root);
	Moon->SetMobility(EComponentMobility::Movable);
	Moon->SetAtmosphereSunLight(true);
	Moon->SetAtmosphereSunLightIndex(1);
	Moon->SetAtmosphereSunDiskColorScale(FLinearColor(0.02f, 0.02f, 0.025f));
	Moon->SetLightColor(FLinearColor(0.55f, 0.66f, 1.f));
	Moon->SetIntensity(0.f);

	Sky = CreateDefaultSubobject<USkyAtmosphereComponent>(TEXT("Sky"));
	Sky->SetupAttachment(Root);

	Clouds = CreateDefaultSubobject<UVolumetricCloudComponent>(TEXT("Clouds"));
	Clouds->SetupAttachment(Root);
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> CloudMat(TEXT("/Game/Mazzarino80/Sky/MI_M80_Clouds.MI_M80_Clouds"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> EngineClouds(TEXT("/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst.m_SimpleVolumetricCloud_Inst"));
	CloudMaterial = CloudMat.Succeeded() ? CloudMat.Object : EngineClouds.Object;
	static ConstructorHelpers::FObjectFinder<UMaterialParameterCollection> Values(TEXT("/Game/Mazzarino80/Sky/MPC_M80_Atmosfera.MPC_M80_Atmosfera"));
	MaterialValues = Values.Object;

	SkyLight = CreateDefaultSubobject<USkyLightComponent>(TEXT("SkyLight"));
	SkyLight->SetupAttachment(Root);
	SkyLight->SetMobility(EComponentMobility::Movable);
	SkyLight->SetRealTimeCapture(true);
	SkyLight->bLowerHemisphereIsBlack = false;
	SkyLight->SetLowerHemisphereColor(FLinearColor(0.09f, 0.075f, 0.055f));

	Fog = CreateDefaultSubobject<UExponentialHeightFogComponent>(TEXT("Fog"));
	Fog->SetupAttachment(Root);

	Look = CreateDefaultSubobject<UPostProcessComponent>(TEXT("Look"));
	Look->SetupAttachment(Root);
	Look->bUnbound = true;
	Look->Priority = -1.f;   // post-process volumes placed by hand win
}

AM80Atmosphere* AM80Atmosphere::Find(const UObject* WorldContextObject)
{
	UWorld* World = WorldContextObject ? WorldContextObject->GetWorld() : nullptr;
	if (!World)
	{
		return nullptr;
	}
	for (TActorIterator<AM80Atmosphere> It(World); It; ++It)
	{
		return *It;
	}
	return nullptr;
}

void AM80Atmosphere::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	CurrentHour = Hour;
	ApplyAt(CurrentHour);
}

void AM80Atmosphere::BeginPlay()
{
	Super::BeginPlay();
	CurrentHour = Hour;
	ApplyAt(CurrentHour);
}

void AM80Atmosphere::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!bAdvanceInGame || GameMinutesPerSecond <= 0.f)
	{
		return;
	}
	CurrentHour = FMath::Fmod(CurrentHour + DeltaSeconds * GameMinutesPerSecond / 60.f, 24.f);
	SinceApply += DeltaSeconds;
	if (SinceApply >= 0.1f)
	{
		SinceApply = 0.f;
		ApplyAt(CurrentHour);
	}
}

void AM80Atmosphere::SetHour(float NewHour)
{
	CurrentHour = FMath::Fmod(FMath::Max(0.f, NewHour), 24.f);
	ApplyAt(CurrentHour);
}

void AM80Atmosphere::Apply()
{
	CurrentHour = Hour;
	ApplyAt(CurrentHour);
}

void AM80Atmosphere::SolarPosition(float AtHour, float& OutElevation, float& OutAzimuth) const
{
	// Local clock time in Sicily: CET, summer time from April to October; Mazzarino is at 14.2 E.
	const bool bSummerTime = DayOfYear >= 90 && DayOfYear <= 300;
	const float SolarNoon = 12.f + (15.f - 14.2f) / 15.f + (bSummerTime ? 1.f : 0.f);
	const double Decl = FMath::DegreesToRadians(23.44 * FMath::Sin(2.0 * PI * (284.0 + DayOfYear) / 365.0));
	const double Lat = FMath::DegreesToRadians((double)Latitude);
	const double H = FMath::DegreesToRadians(15.0 * (AtHour - SolarNoon));
	const double SinEl = FMath::Sin(Lat) * FMath::Sin(Decl) + FMath::Cos(Lat) * FMath::Cos(Decl) * FMath::Cos(H);
	OutElevation = FMath::RadiansToDegrees(FMath::Asin(FMath::Clamp(SinEl, -1.0, 1.0)));
	OutAzimuth = FMath::RadiansToDegrees(FMath::Atan2(FMath::Sin(H), FMath::Cos(H) * FMath::Sin(Lat) - FMath::Tan(Decl) * FMath::Cos(Lat))) + 180.f;
}

void AM80Atmosphere::ApplyAt(float AtHour)
{
	if (!Sun || !Sky || !Fog || !Look)
	{
		return;
	}
	float Elevation = 0.f, Azimuth = 0.f;
	SolarPosition(AtHour, Elevation, Azimuth);
	SunElevation = Elevation;
	const FWeatherLook W = LookFor(Weather);
	const float K = FMath::Clamp(LookStrength, 0.f, 1.5f);

	// 0 by day, 1 in the dark; golden near the horizon.
	const float Night = 1.f - FMath::SmoothStep(-9.f, -1.f, Elevation);
	const float Golden = (1.f - FMath::SmoothStep(4.f, 24.f, Elevation)) * (1.f - Night);
	const float Day = 1.f - Night;

	// Sun: the light travels from the sun towards the ground.
	const float SunYaw = NorthYaw + Azimuth;
	Sun->SetWorldRotation(FRotator(-Elevation, SunYaw + 180.f, 0.f));
	Sun->SetIntensity(SunLux * W.SunScale * FMath::SmoothStep(-4.f, 3.f, Elevation));
	Sun->SetTemperature(FMath::Lerp(5900.f, 4600.f, Golden));
	Sun->SetCastShadows(Elevation > -4.f);

	// Moon: high in the opposite part of the sky, cold and dim.
	Moon->SetWorldRotation(FRotator(-38.f, SunYaw, 0.f));
	Moon->SetIntensity(0.35f * Night);
	Moon->SetCastShadows(Night > 0.5f);

	// Sky: Mediterranean haze (strong forward scattering around the sun, pale horizon).
	Sky->SetMieScatteringScale(W.MieScale);
	Sky->SetMieAbsorptionScale(W.MieScale * 0.25f);
	Sky->SetMieAbsorption(W.MieAbsorption);
	Sky->SetMieAnisotropy(0.82f);
	Sky->SetRayleighScatteringScale(0.0331f * (Weather == EM80Weather::Scirocco ? 0.7f : 0.95f));
	Sky->SetGroundAlbedo(FColor(110, 96, 72));
	Sky->SetAerialPespectiveViewDistanceScale(W.AerialDistanceScale);
	Sky->SetHeightFogContribution(1.f);
	Sky->SetMultiScatteringFactor(1.f);

	if (Clouds)
	{
		Clouds->SetLayerBottomAltitude(Weather == EM80Weather::Cloudy ? 1.8f : 3.f);
		Clouds->SetLayerHeight(Weather == EM80Weather::Cloudy ? 6.f : 4.f);
		Clouds->SetTracingMaxDistance(80.f);
		if (CloudMaterial)
		{
			UMaterialInstanceDynamic* Mid = Cast<UMaterialInstanceDynamic>(Clouds->GetMaterial());
			if (!Mid || Mid->Parent != CloudMaterial)
			{
				Mid = UMaterialInstanceDynamic::Create(CloudMaterial, this);
				Clouds->SetMaterial(Mid);
			}
			Mid->SetScalarParameterValue(TEXT("Cloud_GlobalCoverage"), W.CloudCoverage);
		}
	}

	if (SkyLight)
	{
		SkyLight->SetIntensity(FMath::Lerp(1.25f, 0.8f, Night));
		SkyLight->SetLowerHemisphereColor(FMath::Lerp(FLinearColor(0.09f, 0.075f, 0.055f), FLinearColor(0.005f, 0.006f, 0.01f), Night));
	}

	// Fog: thin over the town, thicker in the valleys below; warm glow towards the low sun.
	Fog->SetWorldLocation(GetActorLocation());
	Fog->SetFogDensity(W.FogDensity);
	Fog->SetFogHeightFalloff(0.2f);
	Fog->SetStartDistance(1500.f);
	Fog->SetSecondFogDensity(W.ValleyFogDensity);
	Fog->SetSecondFogHeightFalloff(0.8f);
	Fog->SetSecondFogHeightOffset(-9000.f);
	// Haze colour: warm grey by day, deep blue in the blue hour (sun just below the horizon), dark at night.
	const float Blue = 1.f - FMath::SmoothStep(-2.f, 3.f, Elevation);
	const FLinearColor DayHaze = FMath::Lerp(FLinearColor(0.5f, 0.47f, 0.42f), FLinearColor(0.06f, 0.09f, 0.19f), Blue);
	Fog->SetFogInscatteringColor(FMath::Lerp(DayHaze, FLinearColor(0.012f, 0.016f, 0.03f), Night) * W.Tint);
	// Never fully opaque: the far hills and Etna stay readable as pale layers instead of cutting the clouds.
	Fog->SetFogMaxOpacity(Weather == EM80Weather::Scirocco ? 0.97f : 0.88f);
	Fog->SetDirectionalInscatteringColor(FMath::Lerp(FLinearColor(0.35f, 0.3f, 0.24f), FLinearColor(0.95f, 0.55f, 0.25f), Golden) * Day);
	Fog->SetDirectionalInscatteringExponent(6.f);
	Fog->SetDirectionalInscatteringStartDistance(4000.f);
	Fog->SetVolumetricFog(true);
	Fog->SetVolumetricFogDistance(9000.f);
	Fog->SetVolumetricFogExtinctionScale(0.3f);
	Fog->SetVolumetricFogScatteringDistribution(0.6f);

	// Colour grade: warm highlights, slightly cool shadows, soft contrast, film grain.
	FPostProcessSettings& P = Look->Settings;
	const FVector4 One(1, 1, 1, 1);
	const FVector4 Zero(0, 0, 0, 0);
	P.bOverride_WhiteTemp = true;
	P.WhiteTemp = 6500.f + K * (450.f + 900.f * Golden - 1600.f * Night);
	P.bOverride_SceneColorTint = true;
	P.SceneColorTint = FMath::Lerp(FLinearColor::White, W.Tint, FMath::Min(K, 1.f));
	P.bOverride_ColorSaturation = true;
	P.ColorSaturation = Lerp4(One, FVector4(1.04f, 1.03f, 1.0f, 1.0f - 0.25f * Night), K);
	P.bOverride_ColorContrast = true;
	P.ColorContrast = Lerp4(One, FVector4(1.06f, 1.06f, 1.06f, 1.f), K);
	P.bOverride_ColorGainHighlights = true;
	P.ColorGainHighlights = Lerp4(One, FVector4(1.05f + 0.04f * Golden, 1.0f, 0.92f - 0.05f * Golden, 1.f), K);
	P.bOverride_ColorSaturationHighlights = true;
	P.ColorSaturationHighlights = Lerp4(One, FVector4(1.f, 1.f, 1.f, 0.94f), K);
	P.bOverride_ColorOffsetShadows = true;
	P.ColorOffsetShadows = Lerp4(Zero, FVector4(-0.002f, 0.0f, 0.006f + 0.006f * Night, 0.f), K);
	P.bOverride_FilmToe = true;
	P.FilmToe = FMath::Lerp(0.55f, 0.6f, FMath::Min(K, 1.f));
	P.bOverride_BloomIntensity = true;
	P.BloomIntensity = 0.675f + K * (0.15f + 0.35f * Golden);
	P.bOverride_VignetteIntensity = true;
	P.VignetteIntensity = 0.4f * K + 0.15f * Night;
	P.bOverride_FilmGrainIntensity = true;
	P.FilmGrainIntensity = 0.12f * K;
	P.bOverride_LensFlareIntensity = true;
	P.LensFlareIntensity = 0.25f * K;
	P.bOverride_LocalExposureHighlightContrastScale = true;
	P.LocalExposureHighlightContrastScale = FMath::Lerp(1.f, 0.85f, FMath::Min(K, 1.f));
	P.bOverride_LocalExposureShadowContrastScale = true;
	P.LocalExposureShadowContrastScale = FMath::Lerp(1.f, 0.8f, FMath::Min(K, 1.f));
	// Exposure: nights stay dark (the eye does not adapt to full daylight under the moon).
	P.bOverride_AutoExposureBias = true;
	// The floor of the adaptation rises at dusk, so the blue hour and the night read darker than the day.
	P.AutoExposureBias = 0.2f + 0.2f * Golden - 0.6f * Night;
	P.bOverride_AutoExposureMinBrightness = true;
	P.AutoExposureMinBrightness = FMath::Lerp(-2.5f, 0.f, Night);
	P.bOverride_AutoExposureMaxBrightness = true;
	P.AutoExposureMaxBrightness = 16.f;

	// Rooms behind the windows: dark by day (as seen from a sunny street), lit at dusk and at night.
	if (MaterialValues)
	{
		UKismetMaterialLibrary::SetScalarParameterValue(this, MaterialValues, TEXT("Finestre"), FMath::Lerp(0.12f, 1.f, FMath::Max(Night, 0.5f * Golden)));
		UKismetMaterialLibrary::SetScalarParameterValue(this, MaterialValues, TEXT("Notte"), Night);
	}
}
