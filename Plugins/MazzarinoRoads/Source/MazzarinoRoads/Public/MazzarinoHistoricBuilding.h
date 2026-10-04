#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Containers/Ticker.h"
#include "MazzarinoHistoricBuilding.generated.h"
class USplineComponent;
class UProceduralMeshComponent;
class UInstancedStaticMeshComponent;
class UMaterialInterface;
class AMazzarinoRoadSpline;
class UStaticMesh;

UENUM(BlueprintType)
enum class EM80HouseFamily : uint8 {
    Automatic UMETA(DisplayName="Automatica ponderata"),
    Popular UMETA(DisplayName="Casa bassa popolare"),
    Narrow UMETA(DisplayName="Casa stretta su piu piani"),
    Corner UMETA(DisplayName="Casa d'angolo"),
    Courtyard UMETA(DisplayName="Casa con cortile"),
    Extended UMETA(DisplayName="Casa ampliata"),
    Palazzetto UMETA(DisplayName="Piccolo palazzetto")
};

// Separate actor: existing city buildings retain their original generator.
UCLASS(Blueprintable, meta=(DisplayName="Casa storica Mazzarino 80"))
class MAZZARINOROADS_API AMazzarinoHistoricBuilding : public AActor {
    GENERATED_BODY()
public:
    AMazzarinoHistoricBuilding();
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void PostLoad() override;
    virtual void BeginDestroy() override;
    UFUNCTION(BlueprintCallable, CallInEditor, Category="PCG") TArray<FString> ExportPCGSurfaceSections(const FString& OutputDirectory);
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Lotto") TObjectPtr<USplineComponent> Footprint;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Lotto") TObjectPtr<UProceduralMeshComponent> Surface;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Lotto") TObjectPtr<UInstancedStaticMeshComponent> StoneDetails;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Lotto") TObjectPtr<UInstancedStaticMeshComponent> IronDetails;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Lotto") TObjectPtr<UInstancedStaticMeshComponent> WoodDetails;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Lotto") TObjectPtr<UInstancedStaticMeshComponent> GlassDetails;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Lotto") TObjectPtr<UInstancedStaticMeshComponent> StreetDetails;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Lotto") TObjectPtr<UInstancedStaticMeshComponent> LifeDetails;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Lotto") TObjectPtr<UInstancedStaticMeshComponent> DoorPanels;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Lotto") TObjectPtr<UInstancedStaticMeshComponent> Pots;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Moduli") TObjectPtr<UInstancedStaticMeshComponent> HangingClothes;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Moduli") TObjectPtr<UInstancedStaticMeshComponent> RoofTiles;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Moduli") TObjectPtr<UInstancedStaticMeshComponent> BalconyModules;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Grammatica", meta=(DisplayName="Famiglia")) EM80HouseFamily Family=EM80HouseFamily::Automatic;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Grammatica", meta=(DisplayName="Seed della singola casa")) int32 Seed=80;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Grammatica", meta=(DisplayName="Famiglia precedente (evita ripetizione)")) EM80HouseFamily PreviousFamily=EM80HouseFamily::Automatic;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Grammatica", meta=(DisplayName="Varieta volumi", ClampMin="0", ClampMax="1")) float VolumeVariation=.7;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Grammatica", meta=(DisplayName="Irregolarita facciate", ClampMin="0", ClampMax="1")) float FacadeIrregularity=.65;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Grammatica", meta=(DisplayName="Densita balconi", ClampMin="0", ClampMax="1")) float BalconyDensity=.28;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Grammatica", meta=(DisplayName="Degrado: 0 curata, 1 molto usurata", ClampMin="0", ClampMax="1")) float Decay=.5;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Grammatica", meta=(DisplayName="Sopraelevazione in laterizio a vista")) bool bUpperBrickFloor=false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Grammatica", meta=(DisplayName="Lacune reali nella muratura", ClampMin="0", ClampMax="1")) float MasonryLoss=0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dimensioni", meta=(DisplayName="Piani: 0 scelta della famiglia", ClampMin="0", ClampMax="3")) int32 FloorsOverride=0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dimensioni", meta=(DisplayName="Altezza piano (m)", ClampMin="2.5", ClampMax="4")) float FloorHeight=2.9;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dimensioni", meta=(DisplayName="Spessore muri (m)", ClampMin=".25", ClampMax=".8")) float WallThickness=.42;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dimensioni", meta=(DisplayName="Rialzo ingresso (m)", ClampMin="0", ClampMax="1.2")) float EntranceLift=.15;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dimensioni", meta=(DisplayName="Profondita balconi (m)", ClampMin=".2", ClampMax="1.2")) float BalconyDepth=.65;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dimensioni", meta=(DisplayName="Rialzo copertura (m)", ClampMin="0", ClampMax="2")) float RoofRise=.8;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dimensioni", meta=(DisplayName="Quota parapetti (m)", ClampMin=".2", ClampMax="1.2")) float ParapetHeight=.6;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dimensioni", meta=(DisplayName="Larghezza cortile / lotto", ClampMin=".2", ClampMax=".5")) float CourtyardWidth=.36;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dimensioni", meta=(DisplayName="Profondita cortile / lotto", ClampMin=".2", ClampMax=".6")) float CourtyardDepth=.42;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dimensioni", meta=(DisplayName="Arretramento sopraelevazione / lotto", ClampMin=".08", ClampMax=".5")) float UpperSetback=.24;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dimensioni", meta=(DisplayName="Alzata massima gradini (m)", ClampMin=".1", ClampMax=".2")) float StepRiser=.17;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dimensioni", meta=(DisplayName="Pedata gradini (m)", ClampMin=".25", ClampMax=".4")) float StepTread=.28;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dimensioni", meta=(DisplayName="Larghezza canaletta (m)", ClampMin=".1", ClampMax=".4")) float DrainWidth=.22;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dimensioni", meta=(DisplayName="Sporgenza davanzale (m)", ClampMin=".02", ClampMax=".15")) float SillProjection=.06;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dimensioni", meta=(DisplayName="Spessore davanzale (m)", ClampMin=".025", ClampMax=".1")) float SillThickness=.045;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dimensioni", meta=(DisplayName="Diametro pluviale (m)", ClampMin=".045", ClampMax=".12")) float DownpipeDiameter=.07;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dimensioni", meta=(DisplayName="Diametro cavo (m)", ClampMin=".005", ClampMax=".025")) float CableDiameter=.012;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dimensioni", meta=(DisplayName="Freccia cavi sospesi (m)", ClampMin=".02", ClampMax=".8")) float CableSag=.22;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Coperture", meta=(DisplayName="Coppi tridimensionali")) bool bShowRoofTiles=true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Coperture", meta=(DisplayName="Passo file coppi (m)", ClampMin=".12", ClampMax=".35")) float TileRowWidth=.20;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Coperture", meta=(DisplayName="Passo longitudinale coppi (m)", ClampMin=".25", ClampMax=".6")) float TileRowLength=.36;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Coperture", meta=(DisplayName="Irregolarita posa coppi", ClampMin="0", ClampMax="1")) float TileIrregularity=.35;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dettagli", meta=(DisplayName="Conserva spline cavi e pluviali modificate")) bool bPreserveServiceSplines=true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PCG", meta=(DisplayName="Conserva solo spline impianti per sostituzione PCG")) bool bPCGVisualReplacement=false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Lotto", meta=(DisplayName="Lato principale del lotto")) int32 FrontEdge=0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Lotto", meta=(DisplayName="Lati ciechi in comune con vicini")) TArray<int32> PartyWallEdges;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Lotto", meta=(DisplayName="Identificativo lotto")) FString LotId;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Appoggio", meta=(DisplayName="Segui terreno e spline automaticamente")) bool bFollowSupports=true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Appoggio", meta=(DisplayName="Strada ingresso")) TObjectPtr<AMazzarinoRoadSpline> EntranceRoad;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Appoggio", meta=(DisplayName="Terreno di appoggio")) TObjectPtr<AActor> GroundActor;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Visibilita", meta=(DisplayName="Balconi e ringhiere")) bool bShowBalconies=true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Visibilita", meta=(DisplayName="Coperture")) bool bShowRoofs=true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Visibilita", meta=(DisplayName="Aperture della facciata")) bool bShowOpenings=true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Visibilita", meta=(DisplayName="Numeri civici indicativi")) bool bShowNumbers=true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Visibilita", meta=(DisplayName="Persiane e portoni")) bool bShowShutters=true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Visibilita", meta=(DisplayName="Cornici e gronde")) bool bShowCornices=true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Visibilita", meta=(DisplayName="Macchie e rappezzi")) bool bShowAging=true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Visibilita", meta=(DisplayName="Cavi pluviali antenne e panni")) bool bShowLife=true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Visibilita", meta=(DisplayName="Soglie e gradini")) bool bShowSteps=true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Visibilita", meta=(DisplayName="Canalette e riparazioni pavimento")) bool bShowStreetDetails=true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Visibilita", meta=(DisplayName="Controllo forme: grigio uniforme")) bool bGrayPreview=false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Materiali") TObjectPtr<UMaterialInterface> PlasterMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Materiali") TObjectPtr<UMaterialInterface> StoneMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Materiali") TObjectPtr<UMaterialInterface> RoofMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Materiali") TObjectPtr<UMaterialInterface> TerraceMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Materiali") TObjectPtr<UMaterialInterface> IronMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Materiali") TObjectPtr<UMaterialInterface> WoodMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Materiali") TObjectPtr<UMaterialInterface> GlassMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Materiali") TObjectPtr<UMaterialInterface> DampMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Materiali") TObjectPtr<UMaterialInterface> RepairMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Materiali") TObjectPtr<UMaterialInterface> ClothMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Materiali") TObjectPtr<UMaterialInterface> GrayMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Materiali") TObjectPtr<UMaterialInterface> ExposedStoneMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Materiali", meta=(DisplayName="Pietra canalette (opaca)")) TObjectPtr<UMaterialInterface> DrainMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Materiali", meta=(DisplayName="Coppi 3D")) TObjectPtr<UMaterialInterface> TileMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Materiali", meta=(DisplayName="Laterizio sopraelevazione")) TObjectPtr<UMaterialInterface> UpperBrickMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Moduli", meta=(DisplayName="Coppo riutilizzabile")) TObjectPtr<UStaticMesh> RoofTileMesh;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Moduli", meta=(DisplayName="Mesh cavo per spline (asse X)")) TObjectPtr<UStaticMesh> CableMesh;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Moduli", meta=(DisplayName="Balcone completo recuperato")) TObjectPtr<UStaticMesh> BalconyModuleMesh;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Moduli", meta=(DisplayName="Larghezza modulo balcone (m)", ClampMin=".9", ClampMax="3")) float BalconyModuleWidth=1.6;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dettagli", meta=(DisplayName="Usa modulo balcone sulle case curate")) bool bUseBalconyModules=true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Moduli", meta=(DisplayName="Portone in legno riutilizzabile")) TObjectPtr<UStaticMesh> DoorMesh;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Moduli", meta=(DisplayName="Vaso riutilizzabile")) TObjectPtr<UStaticMesh> PotMesh;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Moduli", meta=(DisplayName="Indumento appeso riutilizzabile")) TObjectPtr<UStaticMesh> HangingClothesMesh;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Verifica") EM80HouseFamily ResolvedFamily=EM80HouseFamily::Popular;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Verifica") FString GeometryError;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Verifica") int32 GeneratedVolumes=0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Verifica") int32 GeneratedOpenings=0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Verifica") int32 GeneratedBalconies=0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Verifica") int32 SupportRevision=0;
    UFUNCTION(BlueprintCallable, CallInEditor, Category="Grammatica", meta=(DisplayName="Rigenera solo questa casa")) void RebuildHouse();
    UFUNCTION(BlueprintCallable, CallInEditor, Category="Appoggio", meta=(DisplayName="Aggiorna appoggio (Z verticale)")) void UpdateSupport();
    UFUNCTION(BlueprintCallable, CallInEditor, Category="Dettagli", meta=(DisplayName="Ripristina percorsi cavi e pluviali")) void ResetServiceSplines();
private:
    FTSTicker::FDelegateHandle SupportTicker;
    TArray<double> LastSupportHeights;
    bool bBuilding=false;
    uint32 LastServiceHash=0;
    void RegisterSupportTicker();
    double GroundZ(const FVector2D& LocalPoint) const;
    uint32 ServiceHash() const;
    void ServiceSpline(FName Name, const TArray<FVector>& Points, double Radius, bool Cable);
};
