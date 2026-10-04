#include "M80DriveTest.h"
#include "M80Car.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "Components/InputComponent.h"

void AM80DrivePlayerController::BeginPlay()
{
	Super::BeginPlay();
	Cars.Reset();
	for (TActorIterator<AM80Car> It(GetWorld()); It; ++It)
	{
		Cars.Add(*It);
	}
	Cars.Sort([](const AM80Car& A, const AM80Car& B) { return A.GetName() < B.GetName(); });
	NextCar();
}

void AM80DrivePlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();
	InputComponent->BindKey(EKeys::Tab, IE_Pressed, this, &AM80DrivePlayerController::NextCar);
	InputComponent->BindKey(EKeys::Gamepad_RightShoulder, IE_Pressed, this, &AM80DrivePlayerController::NextCar);
}

void AM80DrivePlayerController::NextCar()
{
	if (Cars.IsEmpty())
	{
		return;
	}
	Current = (Current + 1) % Cars.Num();
	if (AM80Car* Car = Cars[Current])
	{
		Possess(Car);
		SetViewTargetWithBlend(Car, 0.6f);
	}
}

void AM80DriveHUD::DrawHUD()
{
	Super::DrawHUD();
	const AM80Car* Car = Cast<AM80Car>(GetOwningPawn());
	if (!Canvas || !GEngine)
	{
		return;
	}
	UFont* Big = GEngine->GetLargeFont();
	UFont* Small = GEngine->GetSmallFont();
	const float X = 40.f, Y = Canvas->ClipY - 170.f;
	if (Car)
	{
		const int32 Gear = Car->GetGear();
		const FString GearText = Gear < 0 ? TEXT("R") : (Gear == 0 ? TEXT("N") : FString::FromInt(Gear));
		DrawText(Car->DisplayName.ToString(), FLinearColor(1.f, 0.85f, 0.5f), X, Y, Big, 1.2f);
		DrawText(FString::Printf(TEXT("%3.0f km/h   marcia %s   %4.0f giri"), FMath::Abs(Car->GetSpeedKmh()), *GearText, Car->GetEngineRPM()),
			FLinearColor::White, X, Y + 40.f, Big, 1.f);
	}
	DrawText(TEXT("W/S gas e freno-retro  A/D sterzo  Spazio freno a mano  Mouse guarda  C camera  R rimetti in strada  Tab cambia auto"),
		FLinearColor(0.85f, 0.85f, 0.85f), X, Y + 90.f, Small, 1.f);
}

AM80DriveTestGameMode::AM80DriveTestGameMode()
{
	DefaultPawnClass = nullptr;
	PlayerControllerClass = AM80DrivePlayerController::StaticClass();
	HUDClass = AM80DriveHUD::StaticClass();
}
