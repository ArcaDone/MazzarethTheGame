#include "M80DynamicMeshHLOD.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "GameFramework/Actor.h"
#if WITH_EDITOR
#include "WorldPartition/HLOD/HLODBuilder.h"
#include "WorldPartition/HLOD/HLODHashBuilder.h"
#endif

UM80DynamicMeshHLODComponent::UM80DynamicMeshHLODComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

TArray<UDynamicMeshComponent*> UM80DynamicMeshHLODComponent::GetSourceMeshes() const
{
	TArray<UDynamicMeshComponent*> Meshes;
	const AActor* Owner = GetOwner();
	if (!Owner)
	{
		return Meshes;
	}
	TInlineComponentArray<UDynamicMeshComponent*> Components(Owner);
	for (UDynamicMeshComponent* C : Components)
	{
		if (!C || !C->IsVisible() || C->Mobility == EComponentMobility::Movable)
		{
			continue;
		}
#if WITH_EDITORONLY_DATA
		if (!C->bEnableAutoLODGeneration)
		{
			continue;
		}
#endif
		int32 Triangles = 0;
		C->ProcessMesh([&Triangles](const UE::Geometry::FDynamicMesh3& Mesh) { Triangles = Mesh.TriangleCount(); });
		if (Triangles > 0)
		{
			Meshes.Add(C);
		}
	}
	return Meshes;
}

bool UM80DynamicMeshHLODComponent::IsHLODRelevant() const
{
	return CanBeHLODRelevant(this) && !GetSourceMeshes().IsEmpty();
}

#if WITH_EDITOR
TSubclassOf<UHLODBuilder> UM80DynamicMeshHLODComponent::GetCustomHLODBuilderClass() const
{
	// The builder needs editor-only mesh building, so it lives in the editor module.
	return LoadClass<UHLODBuilder>(nullptr, TEXT("/Script/MazzarinoHousesEditor.M80DynamicMeshHLODBuilder"));
}

void UM80DynamicMeshHLODComponent::ComputeHLODHash(FHLODHashBuilder& HashBuilder) const
{
	Super::ComputeHLODHash(HashBuilder);
	// Changing this key rebuilds every HLOD that holds dynamic meshes.
	HashBuilder.HashField(FString(TEXT("M80DynamicMeshHLOD-1")), TEXT("M80DynamicMeshHLODKey"));
	for (const UDynamicMeshComponent* C : GetSourceMeshes())
	{
		HashBuilder.HashField(C->GetComponentTransform(), TEXT("Transform"));
		for (int32 i = 0; i < C->GetNumMaterials(); ++i)
		{
			HashBuilder << C->GetMaterial(i);
		}
		uint32 Geometry = 0;
		C->ProcessMesh([&Geometry](const UE::Geometry::FDynamicMesh3& Mesh)
		{
			for (const int32 V : Mesh.VertexIndicesItr())
			{
				Geometry = HashCombineFast(Geometry, GetTypeHash(Mesh.GetVertex(V)));
			}
			const UE::Geometry::FDynamicMeshMaterialAttribute* Materials = Mesh.HasAttributes() ? Mesh.Attributes()->GetMaterialID() : nullptr;
			for (const int32 T : Mesh.TriangleIndicesItr())
			{
				Geometry = HashCombineFast(Geometry, GetTypeHash(Mesh.GetTriangle(T)));
				if (Materials)
				{
					Geometry = HashCombineFast(Geometry, GetTypeHash(Materials->GetValue(T)));
				}
			}
		});
		HashBuilder.HashField(Geometry, TEXT("Geometry"));
	}
}
#endif
