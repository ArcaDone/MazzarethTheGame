#pragma once

#include "CoreMinimal.h"
#include "WorldPartition/HLOD/HLODBuilder.h"
#include "M80DynamicMeshHLODBuilder.generated.h"

/**
 * HLOD builder of UM80DynamicMeshHLODComponent: the dynamic meshes of all its source actors become one static mesh
 * (one section per material, the source materials kept), stored in the HLOD actor.
 */
UCLASS(HideDropdown)
class UM80DynamicMeshHLODBuilder : public UHLODBuilder
{
	GENERATED_BODY()

public:
	virtual TArray<UActorComponent*> Build(const FHLODBuildContext& InHLODBuildContext, const TArray<UActorComponent*>& InSourceComponents) const override;
};
