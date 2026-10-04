#include "MazzarinoPCGBuildingData.h"
#include "PCGComponent.h"
#include "PCGGraph.h"
#include "Components/BoxComponent.h"

AMazzarinoProceduralBuilding::AMazzarinoProceduralBuilding(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    PCGComponent->bIsComponentPartitioned = false;
    GenerationBounds = CreateDefaultSubobject<UBoxComponent>(TEXT("GenerationBounds"));
    GenerationBounds->SetupAttachment(RootComponent);
    GenerationBounds->SetBoxExtent(FVector(1000.0, 1000.0, 1000.0));
    GenerationBounds->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    GenerationBounds->SetVisibility(false);
    GenerationBounds->SetHiddenInGame(true);
}

void AMazzarinoProceduralBuilding::BeginPlay()
{
    Super::BeginPlay();
    // APCGVolume is hidden by default; its generated house instances must render in Play.
    SetActorHiddenInGame(false);
}

void AMazzarinoProceduralBuilding::RegenerateBuilding()
{
    if (!PCGComponent)
    {
        return;
    }
    if (UPCGGraphInterface* Graph = BuildingData.BuildingGraph.LoadSynchronous())
    {
        PCGComponent->SetGraph(Graph);
    }
    PCGComponent->Generate(true);
}
