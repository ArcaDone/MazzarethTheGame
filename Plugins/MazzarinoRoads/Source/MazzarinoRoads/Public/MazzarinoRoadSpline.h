#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MazzarinoRoadSpline.generated.h"

class USplineComponent;
class USplineMeshComponent;
class UStaticMesh;
class UMaterialInterface;

UCLASS(Blueprintable, meta=(DisplayName="Strada Mazzarino (spline)"))
class MAZZARINOROADS_API AMazzarinoRoadSpline : public AActor
{
    GENERATED_BODY()
public:
    AMazzarinoRoadSpline();
    virtual void OnConstruction(const FTransform& Transform) override;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Strada")
    TObjectPtr<USplineComponent> Spline;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Strada", meta=(DisplayName="Larghezza (metri)", ClampMin="0.2", ClampMax="40.0"))
    float WidthMeters = 5.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Strada", meta=(DisplayName="Mesh pavimentazione"))
    TObjectPtr<UStaticMesh> RoadMesh;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Strada", meta=(DisplayName="Base continua opzionale"))
    TObjectPtr<UStaticMesh> RoadBackingMesh;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Strada", meta=(DisplayName="Materiale pavimentazione"))
    TObjectPtr<UMaterialInterface> RoadMaterial;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Strada", meta=(DisplayName="Scala verticale mesh", ClampMin="0.01", ClampMax="10.0"))
    float MeshVerticalScale = 1.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Strada", meta=(DisplayName="Lunghezza segmento (metri)", ClampMin="1.0", ClampMax="50.0"))
    float SegmentLengthMeters = 10.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Strada", meta=(DisplayName="Collisione attiva"))
    bool bRoadCollision = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Riferimento", meta=(DisplayName="Nome strada"))
    FString RoadName;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Riferimento", meta=(DisplayName="Identificativo OSM"))
    FString OsmWayId;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Riferimento", meta=(DisplayName="Tipo OSM"))
    FString OsmHighway;

    UFUNCTION(BlueprintCallable, CallInEditor, Category="Strada", meta=(DisplayName="Rigenera pavimentazione"))
    void RebuildRoad();

    UFUNCTION(BlueprintCallable, Category="Strada")
    int32 GetRoadSegmentCount() const { return RoadSegments.Num(); }

private:
    UPROPERTY()
    TArray<TObjectPtr<USplineMeshComponent>> RoadSegments;
};
