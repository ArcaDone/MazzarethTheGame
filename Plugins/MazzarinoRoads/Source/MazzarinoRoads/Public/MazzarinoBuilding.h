#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MazzarinoBuilding.generated.h"
class USplineComponent;
class UProceduralMeshComponent;
class UInstancedStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;

UCLASS(Blueprintable, meta=(DisplayName="Edificio Mazzarino (perimetro)"))
class MAZZARINOROADS_API AMazzarinoBuilding : public AActor
{
    GENERATED_BODY()
public:
    AMazzarinoBuilding();
    virtual void OnConstruction(const FTransform& Transform) override;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Edificio") TObjectPtr<USplineComponent> Footprint;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Edificio") TObjectPtr<UProceduralMeshComponent> BuildingSurface;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Edificio") TObjectPtr<UInstancedStaticMeshComponent> Windows;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Edificio") TObjectPtr<UInstancedStaticMeshComponent> Doors;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Edificio") TObjectPtr<UInstancedStaticMeshComponent> WindowBackings;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Edificio") TObjectPtr<UInstancedStaticMeshComponent> MasonryDetails;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Edificio") TObjectPtr<UInstancedStaticMeshComponent> MetalDetails;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Edificio") TObjectPtr<UInstancedStaticMeshComponent> Shutters;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Composizione", meta=(DisplayName="Variante composizione")) int32 CompositionSeed=0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Composizione", meta=(DisplayName="Larghezza prospetto (metri)", ClampMin="4")) float FacadeSectionWidthMeters=9;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Composizione", meta=(DisplayName="Variazione altezze (metri)", ClampMin="0", ClampMax="3")) float HeightVariationMeters=0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Composizione", meta=(DisplayName="Terrazza con vano arretrato")) bool bRoofTerrace=false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Facciata", meta=(DisplayName="Decora anche i lati")) bool bDetailSideFacades=false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Facciata", meta=(DisplayName="Tipo balconi: 0 nessuno, 1 singoli, 2 continui", ClampMin="0", ClampMax="2")) int32 BalconyStyle=1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Facciata", meta=(DisplayName="Profondita balconi (metri)", ClampMin="0.4", ClampMax="1.5")) float BalconyDepthMeters=0.85;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Facciata", meta=(DisplayName="Persiane")) bool bAddShutters=true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Facciata", meta=(DisplayName="Materiale cornici")) TObjectPtr<UMaterialInterface> TrimMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Facciata", meta=(DisplayName="Materiale ringhiere")) TObjectPtr<UMaterialInterface> MetalMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Facciata", meta=(DisplayName="Materiale persiane")) TObjectPtr<UMaterialInterface> ShutterMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Riferimento", meta=(DisplayName="Identificativo OSM")) FString BuildingId;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Riferimento", meta=(DisplayName="Stato ricostruzione")) FString ReconstructionStatus=TEXT("Volume provvisorio");
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Edificio", meta=(DisplayName="Numero piani", ClampMin="1", ClampMax="8")) int32 FloorCount=2;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Edificio", meta=(DisplayName="Altezza piano (metri)", ClampMin="2.0", ClampMax="6.0")) float FloorHeightMeters=3.2f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Edificio", meta=(DisplayName="Materiale facciata")) TObjectPtr<UMaterialInterface> FacadeMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Edificio", meta=(DisplayName="Materiale tetto")) TObjectPtr<UMaterialInterface> RoofMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Edificio", meta=(DisplayName="Rialzo tetto (metri)", ClampMin="0.0", ClampMax="5.0")) float RoofRiseMeters=0.0f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Edificio", meta=(DisplayName="Direzione colmo (gradi)")) float RoofRidgeAngleDegrees=0.0f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Edificio", meta=(DisplayName="Ripetizione materiale (metri)", ClampMin="0.1")) float TextureMeters=2.0f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Facciata", meta=(DisplayName="Aggiungi porte e finestre")) bool bDetailedFacade=false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Facciata", meta=(DisplayName="Lato ingresso")) int32 FrontEdgeIndex=0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Facciata", meta=(DisplayName="Mesh finestra")) TObjectPtr<UStaticMesh> WindowMesh;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Facciata", meta=(DisplayName="Mesh porta")) TObjectPtr<UStaticMesh> DoorMesh;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Facciata", meta=(DisplayName="Materiale vetri")) TObjectPtr<UMaterialInterface> WindowBackingMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Facciata", meta=(DisplayName="Larghezza finestra (metri)", ClampMin="0.3")) float WindowWidthMeters=0.9f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Facciata", meta=(DisplayName="Altezza finestra (metri)", ClampMin="0.3")) float WindowHeightMeters=1.4f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Facciata", meta=(DisplayName="Passo finestre (metri)", ClampMin="1.5")) float WindowSpacingMeters=3.0f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Riferimento", meta=(DisplayName="Errore perimetro")) FString GeometryError;
    UFUNCTION(BlueprintCallable, CallInEditor, Category="Edificio", meta=(DisplayName="Rigenera edificio")) void RebuildBuilding();
};
