#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "PCGVolume.h"
#include "MazzarinoPCGBuildingData.generated.h"

class UMaterialInterface;
class UStaticMesh;
class UPCGGraphInterface;
class UBoxComponent;

USTRUCT(BlueprintType)
struct MAZZARINOROADS_API FBuildingData
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Identita") FString BuildingId;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Lotto") TArray<FVector> FootprintWorldCm;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Lotto") int32 FrontEdge = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Lotto") TArray<int32> PartyWallEdges;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Lotto") FSoftObjectPath EntranceRoad;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Lotto") FSoftObjectPath GroundActor;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Casa") FName Family;
    // Geometric lot family and visual identity are independent. Keep the
    // footprint/party-wall rules while swapping the approved Blender kit.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Casa", meta=(DisplayName="Stile visivo")) FName VisualStyle;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Casa") int32 PrimaryFloors = 1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Casa") float FloorHeightCm = 300.0f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Casa") float WallThicknessCm = 40.0f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Casa") FName RoofType;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Casa") float RoofRiseCm = 0.0f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Casa") FName FacadeType;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Casa") FName CharacterProfile;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Casa") bool bUpperBrickFloor = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Casa", meta=(ClampMin="0", ClampMax="1")) float MasonryLoss = 0.0f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Casa") bool bRooftopTank = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dettagli") bool bCourtyardGate = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dettagli") bool bExternalBathroom = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dettagli") bool bFacadeFlue = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dettagli") bool bCactus = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dettagli") bool bIvy = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Casa") FName GroundRelationship;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Variazione") int32 VariationSeed = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Materiali") TSoftObjectPtr<UMaterialInterface> FacadeMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Materiali") TSoftObjectPtr<UMaterialInterface> RoofMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Materiali") TSoftObjectPtr<UMaterialInterface> UpperBrickMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Moduli") TSoftObjectPtr<UStaticMesh> RoofMesh;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Moduli") TSoftObjectPtr<UStaticMesh> RooftopTankMesh;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Moduli") TSoftObjectPtr<UStaticMesh> TankVesselMesh;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Materiali") TSoftObjectPtr<UMaterialInterface> TankVesselMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PCG") TSoftObjectPtr<UPCGGraphInterface> BuildingGraph;
};

UCLASS(BlueprintType)
class MAZZARINOROADS_API UMazzarinoPCGBuildingCatalog : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Case") TArray<FBuildingData> Buildings;
};

UCLASS(Blueprintable, meta=(DisplayName="Casa procedurale PCG"))
class MAZZARINOROADS_API AMazzarinoProceduralBuilding : public APCGVolume
{
    GENERATED_BODY()
public:
    AMazzarinoProceduralBuilding(const FObjectInitializer& ObjectInitializer);
    virtual void BeginPlay() override;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Casa PCG") TObjectPtr<UBoxComponent> GenerationBounds;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Casa PCG") FBuildingData BuildingData;
    UFUNCTION(BlueprintCallable, CallInEditor, Category="Casa PCG") void RegenerateBuilding();
};
