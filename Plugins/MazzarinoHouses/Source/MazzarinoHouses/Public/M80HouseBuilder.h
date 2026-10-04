#pragma once

#include "CoreMinimal.h"
#include "M80HouseTypes.h"
#include "M80MeshBuffer.h"

/** Everything the generator needs, already resolved by the actor. Local space, cm. */
struct MAZZARINOHOUSES_API FM80BuildInput
{
	/** Cleaned CCW footprint. */
	TArray<FVector2D> Footprint;
	/** Street/Back/Party for each edge (edge i: point i -> i+1). */
	TArray<EM80EdgeKind> Kinds;
	int32 FrontEdge = 0;
	/** Terrain height at a local XY. */
	TFunction<double(const FVector2D&)> Ground;
	FM80HouseParams Params;
	FM80FacadeRules Rules;
	int32 NumProps = 0;
	/** Plant meshes follow the props in the actor's mesh list: climbers, ground plants, wall plants. */
	int32 NumClimbers = 0;
	int32 NumGroundPlants = 0;
	int32 NumWallPlants = 0;
	float ClimberYaw = 0.f;
	/** Sicilian prop categories (M80Cat) in the actor's mesh list. */
	int32 CatFirst[M80Cat::Count] = {};
	int32 CatCount[M80Cat::Count] = {};
	float WallPropYaw = 0.f;
	/** Material slot of the facade walls (depends on the finish). */
	int32 WallSlot = M80Slot::WallAshlar;
	/** Abandoned house: boarded and bricked-up openings, broken glass, hanging shutters, no lamps or pots. */
	bool bAbandoned = false;
	/** Bare brick floor never finished: concrete frame, empty openings, rebar on top. */
	bool bUnfinished = false;
	/** Ground floor use per edge (missing = home). */
	TArray<EM80GroundUse> Uses;
	/** Roof details (tanks, antennas, pots) stay out of this area: the set-back upper floor. */
	TArray<FVector2D> KeepOut;
	/** UV1 per-unit data: palette position and decay. */
	FVector2f UnitData = FVector2f(0.5f, 0.35f);
};

struct MAZZARINOHOUSES_API FM80PropPlacement
{
	int32 Prop = 0;
	FTransform Transform;
	/** > 0: the actor scales the mesh uniformly so its bounds reach this height (cm). */
	float TargetHeight = 0.f;
	/** Reach TargetHeight by stacking copies near their real size instead of stretching one (ivy strands). */
	bool bStack = false;
};

struct MAZZARINOHOUSES_API FM80BuildOutput
{
	FM80MeshBuffer Mesh;
	TArray<FM80PropPlacement> Props;
	/** Ground-floor level and eave height, local Z. */
	double Floor0 = 0;
	double EaveZ = 0;
	int32 Openings = 0;
	int32 Balconies = 0;
	bool bStair = false;
};

MAZZARINOHOUSES_API void M80BuildHouse(const FM80BuildInput& In, FM80BuildOutput& Out);

/**
 * Free-standing courtyard wall from A to B (Outward = the street side), following the ground in
 * steps, with stone coping and optionally an arched gateway with an iron gate in the middle.
 */
MAZZARINOHOUSES_API void M80BuildCourtWall(const FVector2D& A, const FVector2D& B, const FVector2D& Outward,
	const TFunction<double(const FVector2D&)>& Ground, int32 WallSlot, bool bGate, int32 Seed, const FVector2f& UnitData, FM80MeshBuffer& M);
