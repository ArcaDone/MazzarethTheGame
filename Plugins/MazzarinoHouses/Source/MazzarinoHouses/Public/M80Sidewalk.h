#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "M80Sidewalk.generated.h"

class USplineComponent;
class USplineMeshComponent;
class UDynamicMeshComponent;
class UStaticMesh;
class UMaterialInterface;

UENUM(BlueprintType)
enum class EM80CurbSide : uint8
{
	Right UMETA(DisplayName = "Destra"),
	Left UMETA(DisplayName = "Sinistra"),
	Both UMETA(DisplayName = "Entrambi"),
	None UMETA(DisplayName = "Nessuno")
};

/**
 * Sidewalk drawn with a spline (the centre line): a paved slab (tiles of the hand-made "Marciapiede"
 * material, mapped in world space) plus the lava-stone curb of the "marciapiede" blueprints on the road side.
 * It sits on the ground (landscape) and follows slopes; houses ignore it when they look for the ground.
 * "Destra" is the right-hand side walking along the spline from the first point.
 * With "Spline chiusa" the path becomes a ring (e.g. around a block); with "Riempi l'interno" the whole
 * inside is paved (a piazza), draped on the ground, and the curb runs along the outline on the inside.
 */
UCLASS(meta = (DisplayName = "Marciapiede (Mazzarino)"))
class MAZZARINOHOUSES_API AM80Sidewalk : public AActor
{
	GENERATED_BODY()

public:
	AM80Sidewalk();

	virtual void OnConstruction(const FTransform& Transform) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Marciapiede")
	TObjectPtr<USplineComponent> Path;

	/** Paved inside of a closed spline. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Marciapiede")
	TObjectPtr<UDynamicMeshComponent> Fill;

	/** Joins the last point to the first one. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Marciapiede", meta = (DisplayName = "Spline chiusa"))
	bool bClosedLoop = false;

	/** Paves the whole area inside the closed spline (piazza); "Larghezza" is then ignored. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Marciapiede", meta = (DisplayName = "Riempi l'interno (piazza)", EditCondition = "bClosedLoop"))
	bool bFillInside = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Marciapiede", meta = (DisplayName = "Larghezza (cm)", ClampMin = "40", ClampMax = "600"))
	float WidthCm = 150.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Marciapiede", meta = (DisplayName = "Altezza dal suolo (cm)", ClampMin = "0", ClampMax = "60"))
	float TopHeightCm = 16.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Marciapiede", meta = (DisplayName = "Lato del cordolo"))
	EM80CurbSide CurbSide = EM80CurbSide::Right;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Marciapiede", meta = (DisplayName = "Larghezza cordolo (cm)", ClampMin = "10", ClampMax = "100"))
	float CurbWidthCm = 32.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Marciapiede", meta = (DisplayName = "Appoggia sul terreno"))
	bool bSnapToGround = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Marciapiede", meta = (DisplayName = "Collisione"))
	bool bCollision = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Marciapiede", meta = (DisplayName = "Lunghezza pezzi lastra (cm)", ClampMin = "50", ClampMax = "2000"))
	float SlabPieceCm = 300.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mesh", meta = (DisplayName = "Mesh lastra"))
	TObjectPtr<UStaticMesh> SlabMesh;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mesh", meta = (DisplayName = "Mesh cordolo"))
	TObjectPtr<UStaticMesh> CurbMesh;

	/** Optional: replaces the slab mesh material. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mesh", meta = (DisplayName = "Materiale lastra"))
	TObjectPtr<UMaterialInterface> SlabMaterial;

	/** Optional: replaces the curb mesh material. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mesh", meta = (DisplayName = "Materiale cordolo"))
	TObjectPtr<UMaterialInterface> CurbMaterial;

	UFUNCTION(BlueprintCallable, CallInEditor, Category = "Marciapiede", meta = (DisplayName = "Ricostruisci"))
	void Rebuild();

private:
	struct FStation
	{
		FVector Pos;   // world, on the ground
		FVector Right; // world, horizontal
	};

	TArray<FStation> Sample(double Step) const;
	double GroundZ(const FVector& World) const;
	void AddStrip(UStaticMesh* Mesh, UMaterialInterface* Material, const TArray<FStation>& St, double Lateral, double Width, double Top, double Depth);
	/** Paves the inside of the closed spline; returns +1/-1, the side ("Right" sign) where the inside lies. */
	double BuildFill(double Top);
};
