#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "M80DynamicMeshHLOD.generated.h"

class UDynamicMeshComponent;

/**
 * Puts the owner's dynamic meshes (sidewalk slabs, road slabs, stairs and wall cores) into the World Partition HLODs.
 * The engine only takes static meshes there, so without this the far town showed a sidewalk's curbs but not its paving.
 * When the HLODs are built, the editor builder UM80DynamicMeshHLODBuilder merges the visible, non-empty dynamic mesh
 * components of the owner into one static mesh kept in the HLOD actor. It adds nothing in game.
 */
UCLASS(ClassGroup = (Mazzarino), meta = (BlueprintSpawnableComponent, DisplayName = "HLOD da mesh dinamiche"))
class MAZZARINOHOUSES_API UM80DynamicMeshHLODComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UM80DynamicMeshHLODComponent();

	/** The owner's dynamic meshes that go into the HLOD: visible, not movable, with triangles. */
	TArray<UDynamicMeshComponent*> GetSourceMeshes() const;

	virtual bool IsHLODRelevant() const override;
#if WITH_EDITOR
	virtual TSubclassOf<class UHLODBuilder> GetCustomHLODBuilderClass() const override;
	/** Transform, materials and geometry of every source mesh: the HLOD is rebuilt only when one of them changes. */
	virtual void ComputeHLODHash(class FHLODHashBuilder& HashBuilder) const override;
#endif
};
