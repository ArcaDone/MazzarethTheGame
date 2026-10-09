#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "M80HouseTypes.generated.h"

class UMaterialInterface;
class UStaticMesh;

UENUM(BlueprintType)
enum class EM80RoofType : uint8
{
	Gable   UMETA(DisplayName = "A capanna (due falde)"),
	Shed    UMETA(DisplayName = "Una falda"),
	Terrace UMETA(DisplayName = "Terrazza piana"),
};

UENUM(BlueprintType)
enum class EM80WallFinish : uint8
{
	Ashlar     UMETA(DisplayName = "Conci squadrati"),
	Rubble     UMETA(DisplayName = "Pietrame"),
	Plaster    UMETA(DisplayName = "Intonaco"),
	PlasterWorn UMETA(DisplayName = "Intonaco rovinato"),
};

/** Carved stone balcony of the palazzi (kit /Game/Mazzarino80/Kit/Balconi). */
UENUM(BlueprintType)
enum class EM80NobleBalcony : uint8
{
	Random     UMETA(DisplayName = "Casuale"),
	Volute     UMETA(DisplayName = "Mensole a volute"),
	Mascheroni UMETA(DisplayName = "Mascheroni (leoni e cani)"),
	Acanto     UMETA(DisplayName = "Acanto e mascherone"),
};

UENUM(BlueprintType)
enum class EM80NobleRailing : uint8
{
	Style    UMETA(DisplayName = "Secondo lo stile (petto d'oca)"),
	Straight UMETA(DisplayName = "Dritta"),
	Bombe    UMETA(DisplayName = "A petto d'oca"),
};

UENUM(BlueprintType)
enum class EM80CornerStyle : uint8
{
	None     UMETA(DisplayName = "Nessuno"),
	Quoins   UMETA(DisplayName = "Cantonali alternati"),
	Pilaster UMETA(DisplayName = "Paraste"),
};

UENUM(BlueprintType)
enum class EM80EdgeKind : uint8
{
	Auto   UMETA(DisplayName = "Automatico"),
	Street UMETA(DisplayName = "Facciata su strada"),
	Back   UMETA(DisplayName = "Retro / cortile"),
	Party  UMETA(DisplayName = "Muro in comune"),
};

/** What the ground floor of a facade is used for. */
UENUM(BlueprintType)
enum class EM80GroundUse : uint8
{
	Home UMETA(DisplayName = "Abitazione"),
	Shop UMETA(DisplayName = "Negozi"),
	Bar  UMETA(DisplayName = "Bar"),
};

/** Material slots of the generated shell, in mesh material-id order. One wall slot per finish. */
namespace M80Slot
{
	enum Type : int32 { WallAshlar = 0, WallRubble, WallPlaster, WallPlasterWorn, Trim, Roof, Terrace, Wood, Glass, Iron, RawWall, Brick, Majolica, Count };

	inline int32 ForFinish(EM80WallFinish Finish) { return WallAshlar + int32(Finish); }
}

/** Categories of the typical Sicilian props of a style, in the order they follow the plants in the prop list. */
namespace M80Cat
{
	enum Type : int32 { Doorside = 0, Balcony, Wall, Basket, Hanging, Terrace, Spout, Civic, Knocker, Crest, Laundry, Count };
}

/** Proportions and probabilities of one architectural style. All lengths in cm. */
USTRUCT(BlueprintType)
struct MAZZARINOHOUSES_API FM80FacadeRules
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Campate", meta = (DisplayName = "Larghezza campata", ClampMin = "150"))
	float BayWidth = 320.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Campate", meta = (DisplayName = "Margine dagli spigoli", ClampMin = "0"))
	float CornerMargin = 80.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Aperture", meta = (DisplayName = "Larghezza finestra"))
	float WindowWidth = 90.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Aperture", meta = (DisplayName = "Altezza finestra"))
	float WindowHeight = 140.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Aperture", meta = (DisplayName = "Davanzale piani alti"))
	float WindowSill = 95.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Aperture", meta = (DisplayName = "Davanzale piano terra"))
	float GroundWindowSill = 125.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Aperture", meta = (DisplayName = "Altezza portafinestra"))
	float FrenchWindowHeight = 230.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Aperture", meta = (DisplayName = "Larghezza porta"))
	float DoorWidth = 125.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Aperture", meta = (DisplayName = "Altezza porta"))
	float DoorHeight = 250.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Aperture", meta = (DisplayName = "Probabilita portale ad arco", ClampMin = "0", ClampMax = "1"))
	float ArchedDoorChance = 0.4f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Aperture", meta = (DisplayName = "Probabilita garage/magazzino", ClampMin = "0", ClampMax = "1"))
	float GarageChance = 0.1f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Aperture", meta = (DisplayName = "Finestrelle all'ultimo piano"))
	bool bSmallTopWindows = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Aperture", meta = (DisplayName = "Profondita mazzetta"))
	float RevealDepth = 24.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Aperture", meta = (DisplayName = "Larghezza cornice finestra"))
	float FrameWidth = 16.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Aperture", meta = (DisplayName = "Sporgenza cornice finestra"))
	float FrameProjection = 4.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Aperture", meta = (DisplayName = "Grata alle finestre del piano terra", ClampMin = "0", ClampMax = "1"))
	float GroundGrilleChance = 0.6f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Persiane", meta = (DisplayName = "Probabilita persiane", ClampMin = "0", ClampMax = "1"))
	float ShutterChance = 0.85f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Persiane", meta = (DisplayName = "Probabilita persiane aperte", ClampMin = "0", ClampMax = "1"))
	float ShutterOpenChance = 0.55f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Persiane", meta = (DisplayName = "Probabilita tapparelle (anni 60-70)", ClampMin = "0", ClampMax = "1"))
	float RollerShutterChance = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Balconi", meta = (DisplayName = "Probabilita balcone", ClampMin = "0", ClampMax = "1"))
	float BalconyChance = 0.45f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Balconi", meta = (DisplayName = "Profondita balcone"))
	float BalconyDepth = 70.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Balconi", meta = (DisplayName = "Spessore lastra balcone"))
	float BalconySlab = 14.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Balconi", meta = (DisplayName = "Altezza ringhiera"))
	float RailingHeight = 100.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Balconi", meta = (DisplayName = "Mensole decorate"))
	bool bOrnateCorbels = false;
	/** Share of houses whose balconies are the carved stone ones of the palazzi (moulded slab on volute, beast or
	 *  acanthus consoles, carved panels between them); the railing is goose-breast with "Probabilita balconi a petto d'oca". */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Balconi", meta = (DisplayName = "Probabilita balcone signorile", ClampMin = "0", ClampMax = "1"))
	float NobleBalconyChance = 0.f;

	/** Arab-Norman pointed arches on the arched doorways. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sicilia", meta = (DisplayName = "Probabilita archi a sesto acuto", ClampMin = "0", ClampMax = "1"))
	float PointedArchChance = 0.f;
	/** Upper windows turned into arched bifore with a small column. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sicilia", meta = (DisplayName = "Probabilita bifore", ClampMin = "0", ClampMax = "1"))
	float BiforaChance = 0.f;
	/** Baroque balconies with the railing bulging out ("petto d'oca"). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sicilia", meta = (DisplayName = "Probabilita balconi a petto d'oca", ClampMin = "0", ClampMax = "1"))
	float PettoOcaChance = 0.f;
	/** Liberty railings with iron scrolls (1900-1930). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sicilia", meta = (DisplayName = "Probabilita ringhiere liberty", ClampMin = "0", ClampMax = "1"))
	float LibertyRailingChance = 0.f;
	/** Majolica tiles under the balcony slabs. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sicilia", meta = (DisplayName = "Probabilita maioliche sotto i balconi", ClampMin = "0", ClampMax = "1"))
	float MajolicaBalconyChance = 0.f;
	/** Stone coat of arms above the arched main doorway. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sicilia", meta = (DisplayName = "Probabilita stemma sul portale", ClampMin = "0", ClampMax = "1"))
	float CrestChance = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Partiture", meta = (DisplayName = "Spigoli"))
	EM80CornerStyle CornerStyle = EM80CornerStyle::Quoins;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Partiture", meta = (DisplayName = "Fascia marcapiano"))
	bool bStringCourse = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Partiture", meta = (DisplayName = "Altezza zoccolo"))
	float PlinthHeight = 70.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Partiture", meta = (DisplayName = "Altezza cornicione"))
	float CorniceHeight = 32.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Partiture", meta = (DisplayName = "Sporgenza cornicione"))
	float CorniceProjection = 26.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tetto", meta = (DisplayName = "Pendenza falde (gradi)", ClampMin = "5", ClampMax = "45"))
	float RoofPitch = 21.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tetto", meta = (DisplayName = "Sporto di gronda"))
	float EaveOverhang = 30.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tetto", meta = (DisplayName = "Altezza parapetto terrazza"))
	float ParapetHeight = 85.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tetto", meta = (DisplayName = "Probabilita comignolo", ClampMin = "0", ClampMax = "1"))
	float ChimneyChance = 0.7f;
};

/** One architectural style: materials plus facade rules. Create one asset per Style 01-04. */
UCLASS(BlueprintType, meta = (DisplayName = "Stile casa Mazzarino"))
class MAZZARINOHOUSES_API UM80HouseStyle : public UDataAsset
{
	GENERATED_BODY()
public:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Regole")
	FM80FacadeRules Rules;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Finitura", meta = (DisplayName = "Finitura muri predefinita"))
	EM80WallFinish DefaultFinish = EM80WallFinish::Ashlar;
	/** Wall tints picked per house by seed. Fed to the master material as custom primitive data. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Finitura", meta = (DisplayName = "Tinte muri"))
	TArray<FLinearColor> WallTints;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Finitura", meta = (DisplayName = "Tinte legno"))
	TArray<FLinearColor> WoodTints;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Materiali") TObjectPtr<UMaterialInterface> AshlarMaterial;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Materiali") TObjectPtr<UMaterialInterface> RubbleMaterial;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Materiali") TObjectPtr<UMaterialInterface> PlasterMaterial;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Materiali") TObjectPtr<UMaterialInterface> PlasterWornMaterial;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Materiali") TObjectPtr<UMaterialInterface> TrimMaterial;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Materiali") TObjectPtr<UMaterialInterface> RoofMaterial;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Materiali") TObjectPtr<UMaterialInterface> TerraceMaterial;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Materiali") TObjectPtr<UMaterialInterface> WoodMaterial;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Materiali") TObjectPtr<UMaterialInterface> GlassMaterial;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Materiali") TObjectPtr<UMaterialInterface> IronMaterial;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Materiali", meta = (DisplayName = "Muro grezzo (muri in comune)"))
	TObjectPtr<UMaterialInterface> RawWallMaterial;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Materiali", meta = (DisplayName = "Mattoni forati (piani non finiti)"))
	TObjectPtr<UMaterialInterface> BrickMaterial;

	/** Small props scattered at doors and balconies (pots, crates). Instanced. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dettagli", meta = (DisplayName = "Vasi e oggetti"))
	TArray<TObjectPtr<UStaticMesh>> PropMeshes;

	/** Ivy and creepers climbing the walls from the ground. Scaled to the wall height they reach. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Vegetazione", meta = (DisplayName = "Rampicanti (edera)"))
	TArray<TObjectPtr<UStaticMesh>> ClimberMeshes;
	/** Weeds, prickly pears and bushes at the foot of the walls and in the corners. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Vegetazione", meta = (DisplayName = "Erbacce e piante alla base"))
	TArray<TObjectPtr<UStaticMesh>> GroundPlantMeshes;
	/** Small plants growing out of cracks and from the top of parapets (capers, wall grass). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Vegetazione", meta = (DisplayName = "Piante nelle crepe (capperi)"))
	TArray<TObjectPtr<UStaticMesh>> WallPlantMeshes;
	/** Typical Sicilian props (Kit/Sicilia), placed by the generator. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sicilia", meta = (DisplayName = "Ai lati del portone (teste di moro, pigne, brocche)"))
	TArray<TObjectPtr<UStaticMesh>> DoorsideMeshes;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sicilia", meta = (DisplayName = "Sui balconi (graste, teste di moro)"))
	TArray<TObjectPtr<UStaticMesh>> BalconyMeshes;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sicilia", meta = (DisplayName = "Sui muri (edicole votive, lanterne)"))
	TArray<TObjectPtr<UStaticMesh>> WallMeshes;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sicilia", meta = (DisplayName = "Panaru calati dai balconi"))
	TArray<TObjectPtr<UStaticMesh>> BasketMeshes;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sicilia", meta = (DisplayName = "Appesi accanto alle porte (peperoncini)"))
	TArray<TObjectPtr<UStaticMesh>> HangingMeshes;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sicilia", meta = (DisplayName = "Sui terrazzi (strattu, quartare)"))
	TArray<TObjectPtr<UStaticMesh>> TerraceMeshes;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sicilia", meta = (DisplayName = "Doccioni dei terrazzi"))
	TArray<TObjectPtr<UStaticMesh>> SpoutMeshes;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sicilia", meta = (DisplayName = "Numeri civici in ceramica"))
	TArray<TObjectPtr<UStaticMesh>> CivicMeshes;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sicilia", meta = (DisplayName = "Batacchi dei portoni"))
	TArray<TObjectPtr<UStaticMesh>> KnockerMeshes;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sicilia", meta = (DisplayName = "Stemmi sui portali"))
	TArray<TObjectPtr<UStaticMesh>> CrestMeshes;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sicilia", meta = (DisplayName = "Panni stesi (sotto le finestre)"))
	TArray<TObjectPtr<UStaticMesh>> LaundryMeshes;
	/** Extra yaw so the front (-Y in Blender) of the Sicilian wall props faces the street. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sicilia", meta = (DisplayName = "Rotazione oggetti a muro"))
	float WallPropYaw = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Materiali", meta = (DisplayName = "Maiolica (sotto i balconi)"))
	TObjectPtr<UMaterialInterface> MajolicaMaterial;

	/** All Sicilian prop lists in M80Cat order. */
	TArray<const TArray<TObjectPtr<UStaticMesh>>*> SicilyLists() const
	{
		return {&DoorsideMeshes, &BalconyMeshes, &WallMeshes, &BasketMeshes, &HangingMeshes, &TerraceMeshes, &SpoutMeshes, &CivicMeshes, &KnockerMeshes, &CrestMeshes, &LaundryMeshes};
	}

	/** Extra yaw so the front of the climber meshes faces away from the wall. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Vegetazione", meta = (DisplayName = "Rotazione rampicanti"))
	float ClimberYaw = 0.f;
};

/** Per-house settings shown on the actor. Values < 0 fall back to the style. */
USTRUCT(BlueprintType)
struct MAZZARINOHOUSES_API FM80HouseParams
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Casa", meta = (DisplayName = "Stile"))
	TObjectPtr<UM80HouseStyle> Style;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Casa", meta = (DisplayName = "Numero piani", ClampMin = "1", ClampMax = "7"))
	int32 Floors = 2;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Casa", meta = (DisplayName = "Altezza piano terra", ClampMin = "220", ClampMax = "600"))
	float GroundFloorHeight = 340.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Casa", meta = (DisplayName = "Altezza piani superiori", ClampMin = "220", ClampMax = "500"))
	float FloorHeight = 310.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Casa", meta = (DisplayName = "Variante (seed)"))
	int32 Seed = 1;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Finitura", meta = (DisplayName = "Usa finitura dello stile"))
	bool bUseStyleFinish = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Finitura", meta = (DisplayName = "Finitura muri", EditCondition = "!bUseStyleFinish"))
	EM80WallFinish Finish = EM80WallFinish::Ashlar;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Finitura", meta = (DisplayName = "Degrado", ClampMin = "0", ClampMax = "1"))
	float Decay = 0.35f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tetto", meta = (DisplayName = "Tipo tetto"))
	EM80RoofType RoofType = EM80RoofType::Gable;
	/** Ridge parallel to the main facade instead of the long axis of the footprint. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tetto", meta = (DisplayName = "Colmo parallelo alla facciata"))
	bool bRidgeAlongFront = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tetto", meta = (DisplayName = "Pendenza (-1 = stile)"))
	float RoofPitchOverride = -1.f;

	/** Index of the main facade edge; -1 picks the longest street edge. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Lati", meta = (DisplayName = "Lato facciata principale (-1 = auto)"))
	int32 FrontEdge = -1;
	/** Optional per-edge override, by edge index (edge i goes from point i to point i+1). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Lati", meta = (DisplayName = "Tipo di ogni lato"))
	TArray<EM80EdgeKind> EdgeKinds;
	/** Ground floor use of each edge, by edge index like "Tipo di ogni lato": shop fronts or a bar instead of windows. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Lati", meta = (DisplayName = "Uso piano terra di ogni lato"))
	TArray<EM80GroundUse> EdgeGroundUse;
	/** Detect walls shared with other houses (no windows there). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Lati", meta = (DisplayName = "Rileva muri in comune"))
	bool bDetectPartyWalls = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dettagli", meta = (DisplayName = "Balconi (-1 = stile)"))
	float BalconyChanceOverride = -1.f;
	/** 1 = this house has the carved stone balconies of the palazzi, 0 = never; -1 = the style's chance. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dettagli", meta = (DisplayName = "Balcone signorile (-1 = stile)", ClampMin = "-1", ClampMax = "1"))
	float NobleBalconyOverride = -1.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dettagli", meta = (DisplayName = "Tipo balcone signorile"))
	EM80NobleBalcony NobleBalconyKind = EM80NobleBalcony::Random;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dettagli", meta = (DisplayName = "Ringhiera balcone signorile"))
	EM80NobleRailing NobleRailing = EM80NobleRailing::Style;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dettagli", meta = (DisplayName = "Persiane aperte (-1 = stile)"))
	float ShutterOpenOverride = -1.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dettagli", meta = (DisplayName = "Pluviali"))
	bool bDownpipes = true;

	/** Chance that a house of 2+ floors has its top floor set back behind a terrace. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Volumi", meta = (DisplayName = "Probabilita ultimo piano arretrato", ClampMin = "0", ClampMax = "1"))
	float SetbackChance = 0.25f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Volumi", meta = (DisplayName = "Profondita terrazzo", ClampMin = "150", ClampMax = "600"))
	float SetbackDepth = 280.f;
	/** 0 = none, 1 = Moor's heads, pots, votive niches and jugs everywhere. Uses the style's Sicilian props. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Vissuto", meta = (DisplayName = "Quantita dettagli siciliani", ClampMin = "0", ClampMax = "1"))
	float SicilyDetails = 0.5f;
	/** Iron anchor plates of the tie rods (capochiave) at the floor levels, near the corners. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Vissuto", meta = (DisplayName = "Probabilita capochiave dei tiranti", ClampMin = "0", ClampMax = "1"))
	float TieRodChance = 0.55f;
	/** Roll-down blinds of wooden slats hung outside doors and French windows. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Vissuto", meta = (DisplayName = "Probabilita tende di legno a listarelle", ClampMin = "0", ClampMax = "1"))
	float SlatBlindChance = 0.25f;
	/** Chance that a house of the row is abandoned: boarded or bricked-up windows, broken glass and shutters, weeds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Vissuto", meta = (DisplayName = "Probabilita casa abbandonata", ClampMin = "0", ClampMax = "1"))
	float AbandonChance = 0.12f;
	/** Chance that a deep house is split into a front and a back block around an inner courtyard. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Volumi", meta = (DisplayName = "Probabilita cortile interno", ClampMin = "0", ClampMax = "1"))
	float CourtyardChance = 0.4f;
	/** Minimum depth of the house (from the front) for a courtyard, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Volumi", meta = (DisplayName = "Profondita minima per il cortile", ClampMin = "800"))
	float CourtyardMinDepth = 1500.f;
	/** Chance of an outside masonry stair along a wall up to a first-floor door (more on back walls). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Volumi", meta = (DisplayName = "Probabilita scala esterna", ClampMin = "0", ClampMax = "1"))
	float ExternalStairChance = 0.15f;
	/** Chance of an unfinished top floor in bare hollow bricks with a concrete frame and rebar on top. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Volumi", meta = (DisplayName = "Probabilita piano non finito", ClampMin = "0", ClampMax = "1"))
	float UnfinishedChance = 0.12f;

	/** 0 = clean walls, 1 = abandoned house overgrown with ivy and weeds. Uses the style's plant meshes. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Vegetazione", meta = (DisplayName = "Quantita vegetazione", ClampMin = "0", ClampMax = "1"))
	float Vegetation = 0.4f;

	/**
	 * OSM footprints often merge a whole row of houses. Split the lot along the street into
	 * separate units, each with its own floors, finish, colour and roof.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schiera", meta = (DisplayName = "Dividi in case a schiera"))
	bool bSplitIntoUnits = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schiera", meta = (DisplayName = "Larghezza minima casa", ClampMin = "300", EditCondition = "bSplitIntoUnits"))
	float UnitWidthMin = 480.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schiera", meta = (DisplayName = "Larghezza massima casa", ClampMin = "400", EditCondition = "bSplitIntoUnits"))
	float UnitWidthMax = 900.f;
	/** Each unit may have up to this many floors more or less than the lot. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schiera", meta = (DisplayName = "Variazione piani", ClampMin = "0", ClampMax = "3", EditCondition = "bSplitIntoUnits"))
	int32 FloorVariation = 1;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schiera", meta = (DisplayName = "Varia tetti", EditCondition = "bSplitIntoUnits"))
	bool bVaryRoofs = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schiera", meta = (DisplayName = "Varia finiture", EditCondition = "bSplitIntoUnits"))
	bool bVaryFinish = true;
	/** Extra styles the units may use besides the main one (e.g. a 1960s plastered house in a stone row). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schiera", meta = (DisplayName = "Stili alternativi", EditCondition = "bSplitIntoUnits"))
	TArray<TObjectPtr<UM80HouseStyle>> AlternativeStyles;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Terreno", meta = (DisplayName = "Segui il terreno"))
	bool bFollowTerrain = true;
	/** Height difference above which the downhill side gets a visible lower floor. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Terreno", meta = (DisplayName = "Dislivello per piano seminterrato", ClampMin = "100"))
	float BasementThreshold = 220.f;
};
