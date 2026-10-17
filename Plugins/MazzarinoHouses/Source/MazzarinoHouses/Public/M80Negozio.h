#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "M80Negozio.generated.h"

class UStaticMesh;
class UMaterialInterface;

/** How the pieces of a zone of a shop are laid out in its room. */
UENUM(BlueprintType)
enum class EM80TipoZona : uint8
{
	/** Modules side by side along a wall (Muro), filling it or up to Lunghezza. */
	Muro UMETA(DisplayName = "Lungo un muro"),
	/** A chain of counter pieces parallel to a wall (Muro) at Distanza from it, fillers to close the gaps. */
	Banco UMETA(DisplayName = "Banco"),
	/** Objects on the counter's top. */
	SulBanco UMETA(DisplayName = "Sul banco"),
	/** Objects hanging over the counter. */
	SopraBanco UMETA(DisplayName = "Sopra il banco"),
	/** Objects in the middle of the room. */
	Centro UMETA(DisplayName = "Centro stanza"),
	/** Objects on the floor along the walls. */
	ATerra UMETA(DisplayName = "A terra lungo i muri"),
	/** Tables (first piece) with chairs (the others) by the shop window. */
	Tavoli UMETA(DisplayName = "Tavoli e sedie"),
	/** Things hung on the walls at eye height. */
	Pareti UMETA(DisplayName = "Alle pareti"),
	/** Lamps on the ceiling, one every OgniM2 square metres. */
	Soffitto UMETA(DisplayName = "Soffitto"),
};

UENUM(BlueprintType)
enum class EM80MuroNegozio : uint8
{
	Fondo UMETA(DisplayName = "Fondo"),
	Laterale UMETA(DisplayName = "Laterale"),
	Qualsiasi UMETA(DisplayName = "Fondo o laterale"),
};

/** One zone of a shop prototype (from the packages' docs/prototipo_*.json, Scripts/m80_negozi_prototipi.py). */
USTRUCT(BlueprintType)
struct MAZZARINOHOUSES_API FM80ZonaNegozio
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Zona")
	FString Nome;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Zona")
	EM80TipoZona Tipo = EM80TipoZona::Muro;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Zona")
	EM80MuroNegozio Muro = EM80MuroNegozio::Fondo;
	/** Modules, the counter chain in order, the objects, the table and its chairs. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Zona")
	TArray<TObjectPtr<UStaticMesh>> Pezzi;
	/** Short counter pieces closing the chain to the room's size. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Zona")
	TArray<TObjectPtr<UStaticMesh>> Riempitivi;
	/** Fill the whole wall with the modules (otherwise up to Lunghezza). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Zona")
	bool bRiempi = true;
	/** Longest run along a wall, cm (0: the whole wall). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Zona")
	float Lunghezza = 0.f;
	/** Counter: distance of its front from the wall, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Zona")
	float Distanza = 200.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Zona")
	int32 Max = 1;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Zona")
	float OgniM2 = 8.f;
};

/**
 * A kind of shop (Alimentari, Bar Sport, Tabaccheria, Edicola...) a house can have behind one of its facades: the room it
 * wants and how it is furnished. Made from the shop packages by Scripts/m80_negozi_prototipi.py.
 */
UCLASS(BlueprintType, meta = (DisplayName = "Prototipo negozio Mazzarino"))
class MAZZARINOHOUSES_API UM80PrototipoNegozio : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Negozio")
	FString Nome;
	/** A bar: bar front (bead curtain, wider sign, awning). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Negozio")
	bool bBar = false;
	/** Smallest room (width along the street, depth), cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Negozio")
	FVector2D StanzaMin = FVector2D(480, 600);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Finiture")
	TObjectPtr<UMaterialInterface> Pareti;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Finiture")
	TObjectPtr<UMaterialInterface> Pavimento;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arredo")
	TArray<FM80ZonaNegozio> Zone;
};

/** A shop chosen for one side of a house (AM80House "Negozi"). */
USTRUCT(BlueprintType)
struct MAZZARINOHOUSES_API FM80NegozioScelto
{
	GENERATED_BODY()

	/** Side of the house (the numbers "Mostra numeri dei lati" draws); -1 = the main facade. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Negozio", meta = (DisplayName = "Lato (-1 = facciata principale)"))
	int32 Lato = -1;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Negozio")
	TObjectPtr<UM80PrototipoNegozio> Prototipo;
	/** Where along the side its middle is: 0 = the side's start, 1 = its end. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Negozio", meta = (DisplayName = "Posizione lungo il lato", ClampMin = "0", ClampMax = "1"))
	float Posizione = 0.5f;
	/** Room width along the street, cm (0: as wide as the prototype wants and the side allows). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Negozio", meta = (DisplayName = "Larghezza (cm, 0 = automatica)", ClampMin = "0", ClampMax = "2000"))
	float Larghezza = 0.f;
};
