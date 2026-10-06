#include "M80GameHUD.h"
#include "M80Atmosphere.h"
#include "M80Car.h"
#include "M80PlayerController.h"
#include "M80Vitals.h"
#include "M80Weapons.h"
#include "MazzarinoRoadSpline.h"
#include "Components/SplineComponent.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerStart.h"
#include "CanvasItem.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
const FLinearColor White(1.f, 1.f, 1.f);
const FLinearColor Dark(0.f, 0.f, 0.f, 0.55f);
const FLinearColor HealthCol(0.22f, 0.62f, 0.25f);
const FLinearColor ArmourCol(0.25f, 0.55f, 0.85f);
const FLinearColor MoneyCol(0.45f, 0.85f, 0.42f);
const FLinearColor GoldCol(1.f, 0.82f, 0.35f);
const FLinearColor StaminaCol(0.95f, 0.78f, 0.2f);

float Fade(float Age, float Hold, float Out = 0.6f)
{
	return Age < Hold ? 1.f : FMath::Clamp(1.f - (Age - Hold) / Out, 0.f, 1.f);
}

FString Lire(int32 V)
{
	FString Digits = FString::FromInt(FMath::Abs(V));
	for (int32 i = Digits.Len() - 3; i > 0; i -= 3)
	{
		Digits.InsertAt(i, TEXT("."));
	}
	return TEXT("L. ") + Digits;
}
}

AM80GameHUD::AM80GameHUD()
{
}

FVector2D AM80GameHUD::WorldToMapUV(const FVector& P) const
{
	return FVector2D((P.X - MapMin.X) / MapSpan, (P.Y - MapMin.Y) / MapSpan);
}

void AM80GameHUD::Text(const FString& Str, float X, float Y, const FLinearColor& Color, float Scale, bool bRight, bool bBig, bool bCentre)
{
	UFont* Font = bBig ? GEngine->GetLargeFont() : GEngine->GetMediumFont();
	float W = 0.f, H = 0.f;
	Canvas->TextSize(Font, Str, W, H, Scale, Scale);
	FCanvasTextItem Item(FVector2D(bCentre ? X - W / 2 : (bRight ? X - W : X), bCentre ? Y - H / 2 : Y), FText::FromString(Str), Font, Color);
	Item.Scale = FVector2D(Scale, Scale);
	Item.EnableShadow(FLinearColor(0, 0, 0, Color.A * 0.9f), FVector2D(2.f, 2.f));
	Item.bOutlined = true;
	Item.OutlineColor = FLinearColor(0, 0, 0, Color.A * 0.8f);
	Canvas->DrawItem(Item);
}

void AM80GameHUD::Star(float X, float Y, float R, const FLinearColor& Fill, const FLinearColor& Edge)
{
	FVector2D P[10];
	for (int32 i = 0; i < 10; ++i)
	{
		const float A = -HALF_PI + i * PI / 5.f;
		const float Rad = (i % 2 == 0) ? R : R * 0.45f;
		P[i] = FVector2D(X + FMath::Cos(A) * Rad, Y + FMath::Sin(A) * Rad);
	}
	for (int32 Pass = 0; Pass < 2; ++Pass)
	{
		const float K = Pass == 0 ? 1.18f : 1.f;
		const FLinearColor C = Pass == 0 ? Edge : Fill;
		for (int32 i = 0; i < 10; ++i)
		{
			const FVector2D A = FVector2D(X, Y) + (P[i] - FVector2D(X, Y)) * K;
			const FVector2D B = FVector2D(X, Y) + (P[(i + 1) % 10] - FVector2D(X, Y)) * K;
			FCanvasTriangleItem T(FVector2D(X, Y), A, B, GWhiteTexture);
			T.SetColor(C);
			T.BlendMode = SE_BLEND_Translucent;
			Canvas->DrawItem(T);
		}
	}
}

void AM80GameHUD::DrawHUD()
{
	Super::DrawHUD();
	if (!Canvas || !GEngine)
	{
		return;
	}
	const float S = Canvas->ClipY / 1080.f;
	const AM80PlayerController* PC = Cast<AM80PlayerController>(PlayerOwner);
	if (PC && PC->bShowMap)
	{
		DrawFullMap(S);
		return;
	}
	const float D = 290.f * S;  // round radar
	DrawRadar(34.f * S, Canvas->ClipY - D - 52.f * S, D, D, S);
	DrawStatus(S);
	DrawNames(S);
	DrawHelp(S);
	DrawWeapon(S);
	DrawSpeed(S);
	DrawEffects(S);
}

void AM80GameHUD::DrawSpeed(float S)
{
	const AM80Car* C = PlayerOwner ? Cast<AM80Car>(PlayerOwner->GetPawn()) : nullptr;
	if (!C)
	{
		return;
	}
	// Speed and gear bottom right, above the street name.
	const float R = Canvas->ClipX - 44.f * S;
	const float Y = Canvas->ClipY - 300.f * S;
	const int32 Kmh = FMath::RoundToInt(FMath::Abs(C->GetSpeedKmh()));
	Text(FString::Printf(TEXT("%d"), Kmh), R - 70.f * S, Y, White, 2.2f * S, true);
	Text(TEXT("km/h"), R, Y + 30.f * S, FLinearColor(0.85f, 0.85f, 0.85f), 0.8f * S, true);
	const int32 Gear = C->GetGear();
	Text(Gear < 0 ? TEXT("R") : (Gear == 0 ? TEXT("N") : FString::FromInt(Gear)), R, Y - 2.f * S, GoldCol, 1.0f * S, true);
	if (C->AreLightsOn())
	{
		Text(TEXT("fari"), R - 160.f * S, Y + 30.f * S, FLinearColor(0.6f, 0.8f, 1.f), 0.7f * S, true);
	}
}

void AM80GameHUD::DrawWeapon(float S)
{
	const AM80PlayerController* PC = Cast<AM80PlayerController>(PlayerOwner);
	const UM80WeaponInventory* Inv = PC ? PC->GetInventory() : nullptr;
	if (!Inv || PC->State != EM80PlayerState::OnFoot)
	{
		return;
	}
	const FM80WeaponSpec& Spec = Inv->CurrentSpec();
	const FM80WeaponSlot Slot = Inv->GetSlot(Inv->GetCurrentSlot());
	// Box left of the clock and money (GTA Vice City: weapon icon top right).
	const float W = 190.f * S, H = 96.f * S;
	const float X = Canvas->ClipX - 40.f * S - 260.f * S - W, Y = 26.f * S;
	FCanvasTileItem Box(FVector2D(X, Y), GWhiteTexture, FVector2D(W, H), FLinearColor(0.f, 0.f, 0.f, 0.45f));
	Box.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Box);
	FCanvasTileItem Edge(FVector2D(X, Y + H - 4.f * S), GWhiteTexture, FVector2D(W, 4.f * S), FLinearColor(Spec.Glow.R, Spec.Glow.G, Spec.Glow.B, 0.9f));
	Canvas->DrawItem(Edge);
	Text(FString(Spec.Name).ToUpper(), X + W / 2, Y + 30.f * S, White, 0.95f * S, false, true, true);
	if (!Spec.bMelee)
	{
		const FString Ammo = Inv->IsReloading() ? TEXT("ricarica...") : FString::Printf(TEXT("%d  /  %d"), Slot.InClip, Slot.Reserve);
		const FLinearColor Col = (Slot.InClip == 0 && Slot.Reserve == 0) ? FLinearColor(0.9f, 0.25f, 0.2f) : GoldCol;
		Text(Ammo, X + W / 2, Y + 66.f * S, Col, 0.85f * S, false, true, true);
	}
	// Crosshair while aiming a gun: four short lines that open with the spread.
	if (PC->IsAiming())
	{
		const float CX = Canvas->ClipX / 2, CY = Canvas->ClipY / 2;
		const float Gap = (6.f + Spec.SpreadDeg * 4.f) * S, Len = 9.f * S;
		const FLinearColor Col(1.f, 1.f, 1.f, 0.9f);
		const FVector2D Dirs[4] = {FVector2D(1, 0), FVector2D(-1, 0), FVector2D(0, 1), FVector2D(0, -1)};
		for (const FVector2D& D : Dirs)
		{
			const FVector2D A = FVector2D(CX, CY) + D * Gap;
			FCanvasLineItem L(A, A + D * Len);
			L.LineThickness = 2.f * S;
			L.SetColor(Col);
			Canvas->DrawItem(L);
		}
	}
}

void AM80GameHUD::DrawRadar(float X, float Y, float W, float H, float S)
{
	const APawn* Pawn = PlayerOwner ? PlayerOwner->GetPawn() : nullptr;
	UMaterialInterface* Mat = RadarMaterial.LoadSynchronous();
	if (!Pawn || !Mat)
	{
		return;
	}
	if (!RadarMID)
	{
		RadarMID = UMaterialInstanceDynamic::Create(Mat, this);
	}
	const AM80Car* Car = Cast<AM80Car>(Pawn);
	const float Speed = Car ? FMath::Abs(Car->GetSpeedKmh()) : 0.f;
	const float Target = Car ? FMath::Lerp(RadarRangeWalk * 1.2f, RadarRangeDrive, FMath::Clamp(Speed / 80.f, 0.f, 1.f)) : RadarRangeWalk;
	RadarRange = FMath::FInterpTo(RadarRange, Target, GetWorld()->GetDeltaSeconds(), 1.5f);
	FRotator View;
	FVector ViewLoc;
	PlayerOwner->GetPlayerViewPoint(ViewLoc, View);
	const float CamYaw = FMath::DegreesToRadians(View.Yaw);
	const float Angle = CamYaw + HALF_PI;
	const FVector2D UV = WorldToMapUV(Pawn->GetActorLocation());
	RadarMID->SetVectorParameterValue(TEXT("Center"), FLinearColor(UV.X, UV.Y, 0, 0));
	RadarMID->SetScalarParameterValue(TEXT("Zoom"), RadarRange / MapSpan);
	RadarMID->SetScalarParameterValue(TEXT("Angle"), Angle);
	RadarMID->SetScalarParameterValue(TEXT("Aspect"), W / H);
	RadarMID->SetScalarParameterValue(TEXT("Corner"), 0.16f);
	RadarMID->SetScalarParameterValue(TEXT("Opacity"), 0.95f);
	RadarMID->SetScalarParameterValue(TEXT("Shape"), 0.f);
	DrawMaterial(RadarMID, X, Y, W, H, 0, 0, 1, 1);

	// Player arrow: rotated by the pawn heading relative to the camera.
	const FVector2D C(X + W / 2, Y + H / 2);
	const float Rel = FMath::DegreesToRadians(Pawn->GetActorRotation().Yaw) - CamYaw;
	auto Rot = [&](float Px, float Py) { return C + FVector2D(Px * FMath::Cos(Rel) - Py * FMath::Sin(Rel), Px * FMath::Sin(Rel) + Py * FMath::Cos(Rel)); };
	const float A = 11.f * S;
	for (int32 Pass = 0; Pass < 2; ++Pass)
	{
		const float K = Pass == 0 ? 1.35f : 1.f;
		FCanvasTriangleItem T1(Rot(0, -A * K), Rot(-A * 0.75f * K, A * 0.8f * K), Rot(0, A * 0.35f * K), GWhiteTexture);
		FCanvasTriangleItem T2(Rot(0, -A * K), Rot(0, A * 0.35f * K), Rot(A * 0.75f * K, A * 0.8f * K), GWhiteTexture);
		const FLinearColor Col = Pass == 0 ? FLinearColor(0, 0, 0, 0.8f) : FLinearColor(1.f, 1.f, 1.f);
		T1.SetColor(Col);
		T2.SetColor(Col);
		Canvas->DrawItem(T1);
		Canvas->DrawItem(T2);
	}

	// North marker (map up = world -Y) on the edge.
	const float B = -Angle;
	const FVector2D Dir(-FMath::Sin(B) * -1.f, -FMath::Cos(B));
	const FVector2D Edge = C + FVector2D(Dir.X * W * 0.37f, Dir.Y * H * 0.37f);
	Text(TEXT("N"), Edge.X - 7.f * S, Edge.Y - 12.f * S, White, 0.8f * S);

	// Health and armour under the radar.
	const AM80PlayerController* PC = Cast<AM80PlayerController>(PlayerOwner);
	const float BarY = Y + H + 4.f * S, BarH = 8.f * S;
	const float HW = W * 0.5f, AW = W * 0.26f;
	X += W * 0.12f;
	W = HW + AW + W * 0.02f;
	auto Bar = [&](float Bx, float By, float Bw, float Bh, float Frac, const FLinearColor& Col)
	{
		FCanvasTileItem Back(FVector2D(Bx, By), GWhiteTexture, FVector2D(Bw, Bh), Col * FLinearColor(0.35f, 0.35f, 0.35f, 0.85f));
		Back.BlendMode = SE_BLEND_Translucent;
		Canvas->DrawItem(Back);
		FCanvasTileItem Fill(FVector2D(Bx, By), GWhiteTexture, FVector2D(Bw * FMath::Clamp(Frac, 0.f, 1.f), Bh), Col);
		Fill.BlendMode = SE_BLEND_Translucent;
		Canvas->DrawItem(Fill);
	};
	const UM80VitalsComponent* V = PC ? PC->GetVitals() : nullptr;
	FLinearColor HCol = HealthCol;
	if (V && V->Health < V->MaxHealth * 0.25f)
	{
		// Low health: the bar blinks red.
		HCol = FMath::Lerp(HealthCol, FLinearColor(0.85f, 0.12f, 0.1f), 0.5f + 0.5f * FMath::Sin(GetWorld()->GetRealTimeSeconds() * 8.f));
	}
	Bar(X, BarY, HW, BarH, V ? V->Health / V->MaxHealth : 1.f, HCol);
	Bar(X + W - AW, BarY, AW, BarH, V ? V->Armour / V->MaxArmour : 0.f, ArmourCol);
	// Stamina: shown only while it is not full (thinner, under the other two).
	const float Frac = V ? V->Stamina / V->MaxStamina : 1.f;
	StaminaAlpha = FMath::FInterpTo(StaminaAlpha, Frac < 0.995f ? 1.f : 0.f, GetWorld()->GetDeltaSeconds(), 3.f);
	if (StaminaAlpha > 0.01f)
	{
		const FLinearColor Col = (V && V->bExhausted) ? FLinearColor(0.85f, 0.35f, 0.1f, StaminaAlpha) : FLinearColor(StaminaCol.R, StaminaCol.G, StaminaCol.B, StaminaAlpha);
		Bar(X, BarY + BarH + 4.f * S, W, BarH * 0.6f, Frac, Col);
	}
}

void AM80GameHUD::DrawEffects(float S)
{
	const AM80PlayerController* PC = Cast<AM80PlayerController>(PlayerOwner);
	if (!PC)
	{
		return;
	}
	auto FullScreen = [&](const FLinearColor& Col)
	{
		FCanvasTileItem T(FVector2D(0, 0), GWhiteTexture, FVector2D(Canvas->ClipX, Canvas->ClipY), Col);
		T.BlendMode = SE_BLEND_Translucent;
		Canvas->DrawItem(T);
	};
	auto Edges = [&](const FLinearColor& Col, float Size)
	{
		// Red vignette: a few nested translucent frames, stronger at the screen edge.
		for (int32 i = 0; i < 6; ++i)
		{
			const float D = Size * (i + 1) / 6.f;
			const FLinearColor C(Col.R, Col.G, Col.B, Col.A / 6.f);
			const float CX = Canvas->ClipX, CY = Canvas->ClipY;
			const FVector2D Pos[4] = {FVector2D(0, 0), FVector2D(0, CY - D), FVector2D(0, D), FVector2D(CX - D, D)};
			const FVector2D Size2[4] = {FVector2D(CX, D), FVector2D(CX, D), FVector2D(D, CY - 2 * D), FVector2D(D, CY - 2 * D)};
			for (int32 k = 0; k < 4; ++k)
			{
				FCanvasTileItem T(Pos[k], GWhiteTexture, Size2[k], C);
				T.BlendMode = SE_BLEND_Translucent;
				Canvas->DrawItem(T);
			}
		}
	};
	if (const UM80VitalsComponent* V = PC->GetVitals())
	{
		if (V->SinceHit() < 0.6f)
		{
			Edges(FLinearColor(0.8f, 0.f, 0.f, 0.55f * (1.f - V->SinceHit() / 0.6f)), 160.f * S);
		}
		if (!V->IsDead() && V->Health < V->MaxHealth * 0.25f)
		{
			Edges(FLinearColor(0.6f, 0.f, 0.f, 0.25f + 0.15f * FMath::Sin(GetWorld()->GetRealTimeSeconds() * 4.f)), 120.f * S);
		}
	}
	if (PC->State == EM80PlayerState::Dead)
	{
		const float T = PC->DeathTime;
		const float Out = FMath::Clamp((T - (PC->RespawnDelay - 1.2f)) / 1.f, 0.f, 1.f);
		FullScreen(FLinearColor(0.25f, 0.f, 0.f, FMath::Clamp(T / 1.5f, 0.f, 1.f) * 0.35f));
		const float A = FMath::Clamp((T - 0.6f) / 0.8f, 0.f, 1.f);
		const float Grow = 3.6f + 0.8f * FMath::Clamp(T / 4.f, 0.f, 1.f);
		Text(TEXT("SEI MORTO"), Canvas->ClipX * 0.5f, Canvas->ClipY * 0.42f, FLinearColor(0.75f, 0.06f, 0.05f, A), Grow * S, false, true, true);
		FullScreen(FLinearColor(0, 0, 0, Out));
	}
	else if (PC->RespawnAge < 1.5f)
	{
		FullScreen(FLinearColor(0, 0, 0, 1.f - PC->RespawnAge / 1.5f));
	}
}

void AM80GameHUD::DrawStatus(float S)
{
	const AM80PlayerController* PC = Cast<AM80PlayerController>(PlayerOwner);
	const float R = Canvas->ClipX - 40.f * S;
	float Y = 30.f * S;
	// Clock: the atmosphere's (sun and clock together), else from the start hour.
	const AM80Atmosphere* Atmosphere = AM80Atmosphere::Find(this);
	const float Minutes = Atmosphere ? Atmosphere->GetHour() * 60.f : StartHour * 60.f + GetWorld()->GetTimeSeconds();
	const int32 Hh = FMath::FloorToInt(Minutes / 60.f) % 24, Mm = FMath::FloorToInt(Minutes) % 60;
	Text(FString::Printf(TEXT("%02d:%02d"), Hh, Mm), R, Y, White, 1.25f * S, true);
	Y += 44.f * S;
	Text(Lire(PC ? PC->Money : 0), R, Y, MoneyCol, 1.6f * S, true);
	Y += 64.f * S;
	// Wanted level: five empty stars.
	for (int32 i = 0; i < 5; ++i)
	{
		Star(R - 18.f * S - i * 40.f * S, Y, 15.f * S, FLinearColor(0.12f, 0.12f, 0.12f, 0.55f), FLinearColor(0.f, 0.f, 0.f, 0.7f));
	}
}

void AM80GameHUD::DrawNames(float S)
{
	const AM80PlayerController* PC = Cast<AM80PlayerController>(PlayerOwner);
	if (!PC)
	{
		return;
	}
	const float R = Canvas->ClipX - 44.f * S;
	float Y = Canvas->ClipY - 150.f * S;
	const float VA = Fade(PC->VehicleNameAge, 3.f);
	if (VA > 0.f && !PC->VehicleName.IsEmpty())
	{
		Text(PC->VehicleName.ToUpper(), R, Y - 70.f * S, FLinearColor(GoldCol.R, GoldCol.G, GoldCol.B, VA), 1.7f * S, true);
	}
	const float SA = Fade(PC->StreetNameAge, 4.f, 1.f);
	if (SA > 0.f && !PC->StreetName.IsEmpty())
	{
		Text(PC->StreetName, R, Y, FLinearColor(1, 1, 1, SA), 1.1f * S, true);
		Text(TEXT("Mazzarino"), R, Y + 38.f * S, FLinearColor(0.8f, 0.8f, 0.8f, SA), 0.8f * S, true);
	}
}

void AM80GameHUD::DrawHelp(float S)
{
	const AM80PlayerController* PC = Cast<AM80PlayerController>(PlayerOwner);
	if (!PC)
	{
		return;
	}
	FString Msg;
	if (PC->HintAge < 2.5f)
	{
		Msg = PC->Hint;
	}
	else if (const AM80Car* C = PC->GetCarInReach())
	{
		Msg = FString::Printf(TEXT("Premi  E  per salire sulla %s"), *C->DisplayName.ToString());
	}
	if (Msg.IsEmpty())
	{
		return;
	}
	float W = 0.f, H = 0.f;
	Canvas->TextSize(GEngine->GetLargeFont(), Msg, W, H, 0.9f * S, 0.9f * S);
	FCanvasTileItem Box(FVector2D(36.f * S, 36.f * S), GWhiteTexture, FVector2D(W + 40.f * S, H + 28.f * S), Dark);
	Box.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Box);
	Text(Msg, 56.f * S, 50.f * S, White, 0.9f * S);
}

void AM80GameHUD::DrawFullMap(float S)
{
	UMaterialInterface* Mat = RadarMaterial.LoadSynchronous();
	if (!Mat)
	{
		return;
	}
	if (!MapMID)
	{
		MapMID = UMaterialInstanceDynamic::Create(Mat, this);
	}
	const float H = Canvas->ClipY * 0.86f, W = H;
	const float X = (Canvas->ClipX - W) / 2, Y = (Canvas->ClipY - H) / 2;
	FCanvasTileItem Back(FVector2D(0, 0), GWhiteTexture, FVector2D(Canvas->ClipX, Canvas->ClipY), FLinearColor(0, 0, 0, 0.6f));
	Back.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Back);
	MapMID->SetVectorParameterValue(TEXT("Center"), FLinearColor(0.5f, 0.5f, 0, 0));
	MapMID->SetScalarParameterValue(TEXT("Zoom"), 0.5f);
	MapMID->SetScalarParameterValue(TEXT("Angle"), 0.f);
	MapMID->SetScalarParameterValue(TEXT("Aspect"), 1.f);
	MapMID->SetScalarParameterValue(TEXT("Corner"), 0.04f);
	MapMID->SetScalarParameterValue(TEXT("Opacity"), 0.97f);
	MapMID->SetScalarParameterValue(TEXT("Shape"), 1.f);
	DrawMaterial(MapMID, X, Y, W, H, 0, 0, 1, 1);
	if (const APawn* Pawn = PlayerOwner ? PlayerOwner->GetPawn() : nullptr)
	{
		const FVector2D UV = WorldToMapUV(Pawn->GetActorLocation());
		const FVector2D P(X + UV.X * W, Y + UV.Y * H);
		const float Yaw = FMath::DegreesToRadians(Pawn->GetActorRotation().Yaw) + HALF_PI;
		auto Rot = [&](float Px, float Py) { return P + FVector2D(Px * FMath::Cos(Yaw) - Py * FMath::Sin(Yaw), Px * FMath::Sin(Yaw) + Py * FMath::Cos(Yaw)); };
		const float A = 12.f * S;
		FCanvasTriangleItem T(Rot(0, -A), Rot(-A * 0.7f, A * 0.8f), Rot(A * 0.7f, A * 0.8f), GWhiteTexture);
		T.SetColor(FLinearColor(1.f, 0.85f, 0.2f));
		Canvas->DrawItem(T);
	}
	const bool bPaused = PlayerOwner && PlayerOwner->IsPaused();
	Text(TEXT("MAZZARINO  1980"), X + 20.f * S, Y + 16.f * S, GoldCol, 1.4f * S);
	if (bPaused)
	{
		Text(TEXT("PAUSA"), X + W - 20.f * S, Y + 12.f * S, White, 1.6f * S, true);
	}
	Text(bPaused ? TEXT("P  riprendi") : TEXT("M  chiudi la mappa"), X + W - 20.f * S, Y + H - 44.f * S, White, 0.8f * S, true);
}

AM80GameMode::AM80GameMode()
{
	PlayerControllerClass = AM80PlayerController::StaticClass();
	HUDClass = AM80GameHUD::StaticClass();
}

void AM80GameMode::StartPlay()
{
	Super::StartPlay();
	if (!bSpawnWeaponPickups)
	{
		return;
	}
	const APlayerStart* Start = nullptr;
	for (TActorIterator<APlayerStart> It(GetWorld()); It; ++It)
	{
		Start = *It;
		break;
	}
	if (!Start)
	{
		return;
	}
	// Points along the streets 12-150 m from the start, at least 15 m apart.
	const FVector Origin = Start->GetActorLocation();
	TArray<FVector> Spots;
	for (TActorIterator<AMazzarinoRoadSpline> It(GetWorld()); It && Spots.Num() < 12; ++It)
	{
		const USplineComponent* Sp = It->Spline;
		if (!Sp || !Sp->Bounds.GetBox().ExpandBy(15000.f).IsInsideXY(Origin))
		{
			continue;
		}
		const float Len = Sp->GetSplineLength();
		for (float D = 0.f; D < Len && Spots.Num() < 12; D += 700.f)
		{
			const FVector P = Sp->GetLocationAtDistanceAlongSpline(D, ESplineCoordinateSpace::World);
			const float Dist = FVector::Dist2D(P, Origin);
			if (Dist < 1200.f || Dist > 15000.f || Spots.ContainsByPredicate([&](const FVector& Q) { return FVector::Dist2D(P, Q) < 1500.f; }))
			{
				continue;
			}
			FHitResult Hit;
			FCollisionQueryParams Q(SCENE_QUERY_STAT(M80Pickup), false);
			if (GetWorld()->LineTraceSingleByChannel(Hit, P + FVector(0, 0, 800.f), P - FVector(0, 0, 1500.f), ECC_Visibility, Q))
			{
				Spots.Add(Hit.ImpactPoint + FVector(0, 0, 55.f));
			}
		}
	}
	Spots.Sort([&](const FVector& A, const FVector& B) { return FVector::DistSquared2D(A, Origin) < FVector::DistSquared2D(B, Origin); });
	const EM80Weapon Order[] = {EM80Weapon::Beretta, EM80Weapon::Mazza, EM80Weapon::Lupara, EM80Weapon::Coltello, EM80Weapon::Revolver};
	for (int32 i = 0; i < Spots.Num(); ++i)
	{
		FActorSpawnParameters P;
		P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		if (AM80WeaponPickup* Pick = GetWorld()->SpawnActor<AM80WeaponPickup>(Spots[i], FRotator::ZeroRotator, P))
		{
			Pick->SetWeapon(Order[i % UE_ARRAY_COUNT(Order)], -1);
		}
	}
}

void AM80GameMode::InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage)
{
	UClass* Pawn = PlayerCharacter.TryLoadClass<APawn>();
	if (!Pawn)
	{
		Pawn = FSoftClassPath(TEXT("/Game/Blueprints/RetargetedCharacters/CBP_SandboxCharacter_Metahuman_Kellan.CBP_SandboxCharacter_Metahuman_Kellan_C")).TryLoadClass<APawn>();
	}
	if (Pawn)
	{
		DefaultPawnClass = Pawn;
	}
	Super::InitGame(MapName, Options, ErrorMessage);
}
