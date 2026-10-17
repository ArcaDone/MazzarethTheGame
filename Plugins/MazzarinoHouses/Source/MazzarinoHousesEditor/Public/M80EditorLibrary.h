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
class UMaterialExpression;
class AM80Bougainvillea;
class UMetaHumanCharacter;
class UDataflow;

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
	 * Heights of the landscape of the open editor world (only the landscape: what stands on it is ignored) on the grid a
	 * landscape of ComponentsX x ComponentsY components (126 quads each, one every QuadSizeCm, centred on Center) would
	 * have, written to File for CreateLandscapeFromHeightsFile. Only the loaded landscape is seen. False if nothing was hit.
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Terreno")
	static bool SampleLandscapeHeights(FVector2D Center, float QuadSizeCm, int32 ComponentsX, int32 ComponentsY, const FString& File);

	/** A new landscape in the open editor world from the heights written by SampleLandscapeHeights (same Center and size). */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Terreno")
	static ALandscape* CreateLandscapeFromHeightsFile(FVector2D Center, float QuadSizeCm, const FString& File, UMaterialInterface* Material);

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

	/** Connects an expression output to the material's World Position Offset (hidden from Python's MaterialProperty). */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Materiali")
	static bool ConnectWorldPositionOffset(UMaterialExpression* From, const FString& OutputName);

	/**
	 * Bakes a bougainvillea into Folder/SM_M80_BGV_<label>: three hand-made levels of detail (fewer, larger cards far
	 * away), no Nanite, no collision, no distance field; the plant then shows it (HLOD-ready). Re-bakes in place.
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Vegetazione")
	static UStaticMesh* BakeBougainvillea(AM80Bougainvillea* Plant, const FString& Folder);

	/**
	 * The world's World Partition runtime partitions (runtime hash set, hidden from Python), one line per layer:
	 * partition, layer (main or HLOD), class, cell size and loading range in cm. Empty if the world has none.
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|World Partition")
	static FString DescribeRuntimePartitions(UWorld* World);

	/**
	 * Sets the cell size and the loading range (cm) of the main layer of the runtime partition PartitionName and
	 * marks the map dirty. The HLODs are built on the old cells: rebuild them afterwards.
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|World Partition")
	static bool SetRuntimePartitionGrid(UWorld* World, FName PartitionName, int32 CellSize, int32 LoadingRange);

	/**
	 * Reads the LOD0 vertices of head, eyes and teeth from a MetaHuman face DNA file (for
	 * MetaHumanCharacterEditorSubsystem.fit_state_to_target_vertices: the 5.8 Creator refuses to import the DNA of
	 * a legacy online-Creator MetaHuman, whose rig differs, but its meshes have the MetaHuman topology).
	 * Returns one line per mesh of the file (index, name, vertex count), empty if the file can't be read.
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Personaggi")
	static FString ReadFaceDnaVertices(const FString& DnaPath, TArray<FVector>& Head, TArray<FVector>& LeftEye,
		TArray<FVector>& RightEye, TArray<FVector>& Teeth);

	/**
	 * Fits the neck of a MetaHuman Character's face back onto its body, after the body was changed (height,
	 * build): what the experimental MetaHuman Generator's ResetNeckToBody does. The character must be added for
	 * editing (MetaHumanCharacterEditorSubsystem.try_add_object_to_edit).
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Personaggi")
	static bool ResetMetaHumanNeck(UMetaHumanCharacter* Character);

	/**
	 * The face regions of a MetaHuman Character (the Creator's blend and move handles): one position per region,
	 * in the face's space (cm; X sideways, Y up, Z forward). The character must be added for editing.
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Personaggi")
	static TArray<FVector> GetMetaHumanFaceRegions(UMetaHumanCharacter* Character);

	/**
	 * Blends one face region (-1: the whole face) towards the given characters (presets), by weight, as the
	 * Creator's Blend tool does, symmetrically. bShapeOnly keeps the region's proportions and blends its shape.
	 * All characters must be added for editing.
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Personaggi")
	static bool BlendMetaHumanFaceRegion(UMetaHumanCharacter* Character, int32 Region,
		const TArray<UMetaHumanCharacter*>& Sources, const TArray<float>& Weights, bool bShapeOnly);

	/**
	 * Moves one face region by Offset (face space, cm) and scales it by ScaleFactor, symmetrically and within the
	 * Creator's bounds, as dragging its handle does. Returns the region's new position.
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Personaggi")
	static FVector MoveMetaHumanFaceRegion(UMetaHumanCharacter* Character, int32 Region, FVector Offset, float ScaleFactor);

	/**
	 * Why a MetaHuman Character can't be built yet (not rigged, auto-rig in progress, no high resolution
	 * textures ...), empty when it can. The character must be added for editing.
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Personaggi")
	static FString GetMetaHumanBuildStatus(UMetaHumanCharacter* Character);

	/**
	 * A Dataflow graph as text, one node per line: name, type, its editable properties and, for each connected
	 * input, the node and output it comes from. To script copies of Epic's cloth and outfit graphs.
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Personaggi")
	static FString DescribeDataflow(UDataflow* Dataflow);

	/**
	 * Sets a property of a Dataflow graph node from text (as in copy/paste, e.g. an asset path for a mesh
	 * property) and invalidates the node, so the next evaluation uses it. Returns false if node or property
	 * is missing or the text doesn't parse.
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Personaggi")
	static bool SetDataflowNodeProperty(UDataflow* Dataflow, FName Node, const FString& Property, const FString& Value);

	/** The Dataflow graph an asset is made by (cloth asset, outfit asset ...), null if none. */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Personaggi")
	static UDataflow* GetAssetDataflow(UObject* Asset);

	/**
	 * Gives an asset (cloth asset, outfit asset ...) another Dataflow graph and terminal node, then rebuilds it
	 * from the graph. Returns false if the asset can't take a graph or the evaluation fails.
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Personaggi")
	static bool RebuildAssetFromDataflow(UObject* Asset, UDataflow* Dataflow, FName Terminal);

	/**
	 * Sets any property of an object from text, as in copy/paste, also the ones the editor shows but scripts
	 * can't write (e.g. a MetaHuman wardrobe item's PrincipalAsset). Returns false if missing or not parsed.
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Personaggi")
	static bool SetObjectPropertyText(UObject* Object, FName Property, const FString& Value);

	/** Any property of an object as text (as copy would give it), empty if missing. */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Personaggi")
	static FString GetObjectPropertyText(UObject* Object, FName Property);

	/**
	 * Connects a material expression's output to a material input by the input's enum name, also the ones scripts
	 * can't name (MP_CustomData0: the Cloth shading model's Cloth input). Returns false if not connected.
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Personaggi")
	static bool ConnectMaterialInput(UMaterialExpression* Expression, const FString& OutputName, const FString& Input);

	/**
	 * The sizes of a resizable outfit asset (made by Epic's MakeResizableOutfitTemplate graph): for each size,
	 * the cloth asset made on a source body and that body (a MetaHuman full body, *_FullBody / *CombinedSkelMesh).
	 * Rebuilds the outfit. Returns false if the asset's graph has no SizedOutfitSource variable.
	 */
	/**
	 * Screen size at which each LOD of a skeletal mesh is switched in (index i = LOD i; LOD 0 is ignored). For LODs
	 * imported from files (Python cannot reach the LOD info). Not saved. Returns the number of LODs set.
	 */
	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Veicoli")
	static int32 SetSkeletalLODScreenSizes(USkeletalMesh* Mesh, const TArray<float>& ScreenSizes);

	UFUNCTION(BlueprintCallable, Category = "Mazzarino|Personaggi")
	static bool SetOutfitSizes(UObject* Outfit, const TArray<UObject*>& ClothAssets, const TArray<FString>& SizeNames,
		const TArray<USkeletalMesh*>& Bodies);
};
