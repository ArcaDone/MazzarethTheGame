#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "M80EditorLibrary.generated.h"

class UTexture;
class UStaticMesh;
class AM80House;
class ALandscape;
class UMaterialInterface;
class UTextureCube;
class UTextureCubeArray;
class ULandscapeLayerInfoObject;
class USplineComponent;
class USkeletalMesh;

/** Editor helpers callable from Python (unreal.M80EditorLibrary). */
UCLASS()
class MAZZARINOHOUSESEDITOR_API UM80EditorLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()
public:
	/** Shrinks the stored source image so its largest side is <= MaxSize. Returns true if it changed. */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Texture")
	static bool DownsizeTextureSource(UTexture* Texture, int32 MaxSize);

	/** Stores the source image as JPEG (much smaller on disk). Not for normal maps' exactness-critical uses. */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Texture")
	static bool CompressTextureSourceJPEG(UTexture* Texture, int32 Quality = 85);

	/**
	 * Converts the house's current mesh into a Nanite static mesh asset Folder/SM_M80_<LotId>
	 * (overwriting it if it exists) and shows it on the actor. Baked assets are derived data:
	 * keep them out of version control and re-bake from the houses.
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Case")
	static UStaticMesh* BakeHouse(AM80House* House, const FString& Folder, bool bNanite = true);

	/**
	 * Creates an editable Landscape that reproduces the surface of an existing terrain actor (e.g. a
	 * static mesh made from a DEM). The landscape covers ComponentsX x ComponentsY components of
	 * 126 quads (2x2 sections of 63) centred on Center, one quad every QuadSizeCm. Heights are found
	 * by tracing the terrain actor only; points outside it take the nearest valid height.
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Terreno")
	static ALandscape* CreateLandscapeFromTerrain(AActor* Terrain, FVector2D Center, float QuadSizeCm, int32 ComponentsX, int32 ComponentsY, UMaterialInterface* Material);

	/**
	 * Captures the editor world around Location into a new (or replaced) HDR TextureCube asset at
	 * PackagePath, e.g. /Game/Mazzarino80/Rooms/TC_M80_Room_Kitchen. Used to bake parallax interiors.
	 * The asset is created but not saved.
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Stanze")
	static UTextureCube* CaptureRoomCube(FVector Location, int32 Size, const FString& PackagePath);

	/** Creates or refills a TextureCubeArray asset from same-size cubes (one slice per room). Not saved. */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Stanze")
	static UTextureCubeArray* MakeCubeArray(const TArray<UTextureCube*>& Cubes, const FString& PackagePath);

	/**
	 * Returns the paint layer LayerName of the landscape, creating its layer info asset at PackagePath
	 * (e.g. /Game/Mazzarino80/Terrain/Layers/LI_M80_Strada) and registering it on the landscape if needed.
	 * The landscape material must use the layer name (LandscapeLayerSample / LayerBlend). Not saved.
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Terreno")
	static ULandscapeLayerInfoObject* EnsureLandscapeLayer(ALandscape* Landscape, FName LayerName, const FString& PackagePath, bool bNoWeightBlend = true);

	/**
	 * Paints a layer along splines (e.g. the road centre lines): full weight within HalfWidthsCm[i] of
	 * spline i, fading to zero over EdgeCm. With bClear the layer is emptied first, otherwise strokes are
	 * added to what is already painted (so hand painting is kept). Returns the painted vertex count.
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Terreno")
	static int32 PaintLandscapeLayerAlongSplines(ALandscape* Landscape, ULandscapeLayerInfoObject* Layer, const TArray<USplineComponent*>& Splines,
		const TArray<float>& HalfWidthsCm, float EdgeCm = 60.f, bool bClear = true);

	/** Diagnostics: "edit=<painted verts in edit layer 0> final=<in merged data> comps=<components using the layer>". */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Terreno")
	static FString DescribeLandscapeLayer(ALandscape* Landscape, ULandscapeLayerInfoObject* Layer);

	/**
	 * Physics for a drivable car mesh: one body on the root bone made of two boxes (the lower body
	 * between Bottom and Belt, and a shorter cabin up to Top), nothing on the wheels (Chaos traces them).
	 * Box in local cm. Creates or replaces <mesh>_PhysicsAsset next to the mesh and assigns it.
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Vehicles")
	static bool MakeVehiclePhysicsAsset(USkeletalMesh* Mesh, FName RootBone, FVector BoxMin, FVector BoxMax, float BeltHeight, float CabinLengthFraction = 0.55f);

	/** Logical size of the texture source, for reports. */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Texture")
	static FIntPoint GetTextureSourceSize(UTexture* Texture);
};
