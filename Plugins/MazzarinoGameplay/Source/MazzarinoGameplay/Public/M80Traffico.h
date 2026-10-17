#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "NavAreas/NavArea.h"
#include "NavRelevantComponent.h"
#include "Subsystems/WorldSubsystem.h"
#include "M80Traffico.generated.h"

class UBoxComponent;
class UArrowComponent;

/**
 * The middle of the roadway: people may walk there but it costs them, so they keep to the strips along the houses (or
 * the sidewalks) and step onto the road only to cross it.
 */
UCLASS()
class MAZZARINOGAMEPLAY_API UM80NavArea_Strada : public UNavArea
{
	GENERATED_BODY()

public:
	UM80NavArea_Strada();
};

/** Marks the roadway of every road of the level as UM80NavArea_Strada for the people's navigation. */
UCLASS(ClassGroup = Navigation, meta = (BlueprintSpawnableComponent))
class MAZZARINOGAMEPLAY_API UM80StradeNavComponent : public UNavRelevantComponent
{
	GENERATED_BODY()

public:
	UM80StradeNavComponent();
	virtual void GetNavigationData(FNavigationRelevantData& Data) const override;
	virtual void CalcAndCacheBounds() const override;
	virtual void OnRegister() override;
	/** How much of each side of the road is left to the people (the strip along the houses), cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Strade")
	float Margine = 110.f;

private:
	struct FPezzo
	{
		FVector A, B;
		float Half;
	};
	mutable TArray<FPezzo> Pezzi;
	void Gather() const;
};

/**
 * One per level with traffic: gives the people's navigation the roadways (see UM80StradeNavComponent). Put it in the
 * level before building the navigation.
 */
UCLASS(meta = (DisplayName = "Strade per la navigazione (Mazzarino)"))
class MAZZARINOGAMEPLAY_API AM80StradeNav : public AActor
{
	GENERATED_BODY()

public:
	AM80StradeNav();
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Strade")
	TObjectPtr<UM80StradeNavComponent> Strade;
};

/** A parking place by the road: a car parks here facing the arrow (the lane's direction). */
UCLASS(meta = (DisplayName = "Parcheggio (Mazzarino)"))
class MAZZARINOGAMEPLAY_API AM80Parcheggio : public AActor
{
	GENERATED_BODY()

public:
	AM80Parcheggio();
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Parcheggio")
	TObjectPtr<UBoxComponent> Area;
#if WITH_EDITORONLY_DATA
	UPROPERTY()
	TObjectPtr<UArrowComponent> Freccia;
#endif
	/** A car is there, or one is coming to park. */
	bool IsTaken(const AActor* Asker) const;
	TWeakObjectPtr<const AActor> Prenotato;
};

/** One lane: a line (world, cm) cars follow in its direction; connectors are the curves across a junction. */
struct MAZZARINOGAMEPLAY_API FM80Corsia
{
	TArray<FVector> P;
	TArray<float> S;
	TArray<int32> Next;
	/** Junction a connector crosses (-1: a lane along a road). */
	int32 Node = -1;
	/** Road piece of a lane along a road. */
	int32 Edge = -1;
	/** Narrow street: a single lane in the middle, one car at a time on the whole piece. */
	bool bStretta = false;
	/** Width of its road (cm) and how far right of the centre line it runs. */
	float RoadWidth = 500.f;
	float Offset = 0.f;
	/** Leads only into dead ends (the edge of the map, a blind alley). */
	bool bCieca = false;
	float Length() const { return S.Num() ? S.Last() : 0.f; }
	FVector At(float D, FVector* OutDir = nullptr) const;
	/** Distance along of the point nearest to Pos, looking within Window of Near (Near < 0: everywhere). */
	float Project(const FVector& Pos, float Near = -1.f, float Window = 800.f) const;
};

/**
 * The traffic of a level: lanes built from its roads (AMazzarinoRoadSpline, AM80Road), with the junctions where they meet
 * and the curves across them; cars drive on the right. Also who holds a junction or a narrow street, and the questions the
 * people ask before crossing.
 */
UCLASS()
class MAZZARINOGAMEPLAY_API UM80Traffico : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	static UM80Traffico* Get(const UObject* Context);

	/** The traffic of Context's world (also the editor's, for the scripts that set up a level). */
	UFUNCTION(BlueprintCallable, Category = "Traffico", meta = (WorldContext = "Context"))
	static UM80Traffico* Trova(const UObject* Context) { return Get(Context); }
	/** Lanes again from the roads there are now. */
	UFUNCTION(BlueprintCallable, Category = "Traffico")
	void Ricostruisci() { Build(); }
	/** Up to Quanti places on the lanes (not narrow, not leading into dead ends) at least Distanza cm apart, facing the
	 *  lane: where cars can start in the traffic. */
	UFUNCTION(BlueprintCallable, Category = "Traffico")
	TArray<FTransform> PostiSuCorsie(int32 Quanti, float Distanza = 3000.f);
	/** Places by the right edge of the roads at least LarghezzaMin cm wide, every 750 cm, away from the junctions,
	 *  facing the lane: candidates for AM80Parcheggio (the caller checks they are clear). */
	UFUNCTION(BlueprintCallable, Category = "Traffico")
	TArray<FTransform> PostiParcheggio(float LarghezzaMin = 900.f);

	/** True when the level has roads with lanes (built on first use). */
	bool HasLanes();
	int32 NumLanes() const { return Lanes.Num(); }
	const FM80Corsia& Lane(int32 i) const { return Lanes[i]; }

	/** Nearest road lane within MaxDist going about the way of Dir; OutS: distance along it. -1 if none. */
	int32 NearestLane(const FVector& Pos, const FVector& Dir, float MaxDist, float& OutS, float MinDot = 0.3f);
	/** A random lane to go on after this one, not into a dead end when there is a choice. */
	int32 PickNext(int32 LaneIndex, FRandomStream& R) const;
	/** Inside the roadway, leaving Margin cm along each edge. */
	bool IsOnRoad(const FVector& P, float Margin = 0.f);
	/** A car within Near of P, or one that will pass within 4 m of it in the next Seconds. */
	bool CarComing(const FVector& P, float Near, float Seconds, const AActor* Ignore = nullptr) const;

	/** Junctions (key = node) and narrow streets (key = 1000000 + piece) are held by one car at a time. */
	bool Reserve(int32 Key, const AActor* Who);
	void Release(int32 Key, const AActor* Who);
	void ReleaseAll(const AActor* Who);

	/** The first free parking place along the lanes from (LaneIndex, S) within Within cm, and where it is along them. */
	AM80Parcheggio* SpotAhead(const TArray<int32>& Route, float S, float Within, const AActor* Asker, int32& OutRouteIndex, float& OutS);

	/** Lanes, junctions, narrow pieces, dead ends, parking places: for the tests. */
	UFUNCTION(BlueprintCallable, Category = "Traffico")
	FString Descrivi();
	/** Draws the lanes for a while (red: dead ends, yellow: narrow, cyan: connectors). */
	UFUNCTION(BlueprintCallable, Category = "Traffico")
	void Disegna(float Seconds = 30.f);

	/** The roads of a level: centre lines (world, every <= 200 cm) and widths; footpaths and steps left out. */
	struct FStrada
	{
		TArray<FVector> P;
		float Width = 500.f;
		FString Kind;
	};
	static void GatherRoads(const UWorld* World, TArray<FStrada>& Out);

private:
	void Build();
	bool bBuilt = false;
	TArray<FM80Corsia> Lanes;
	int32 NumNodes = 0;
	struct FTratto
	{
		FVector A, B;
		float Half;
	};
	TArray<FTratto> Tratti;
	TMap<int32, TWeakObjectPtr<const AActor>> Held;
	TArray<TWeakObjectPtr<AM80Parcheggio>> Spots;
	/** For each spot: its lane and distance along it. */
	TArray<TPair<int32, float>> SpotLane;
};
