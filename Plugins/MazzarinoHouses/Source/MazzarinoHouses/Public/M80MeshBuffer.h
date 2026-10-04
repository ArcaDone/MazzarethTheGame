#pragma once

#include "CoreMinimal.h"

namespace UE::Geometry { class FDynamicMesh3; }

/**
 * Flat-shaded triangle soup with per-triangle material slots.
 * Every primitive takes the outward normal it should face, so callers never reason about winding.
 * UVs are world-scale: one UV unit per metre, so tiling materials keep their real size on any wall.
 *
 * Vertex colour channels, read by the house master material:
 *   R = height above the local ground (0 at ground, 1 at 3 m)  -> rising damp and dirt
 *   G = facade mask (1 on wall faces that may show decay)
 *   B = per-element random value (tint variation between shutters, blocks...)
 * UV channel 1 carries per-unit data: X = position in the style colour palette, Y = decay amount.
 */
struct MAZZARINOHOUSES_API FM80MeshBuffer
{
	TArray<FVector3d> Positions;
	TArray<FVector3f> Normals;
	TArray<FVector2f> UVs;
	TArray<FVector4f> Colors;
	TArray<FVector2f> UnitData;
	TArray<int32> MaterialIds;

	/** Ground height at a local XY, used for the R channel. */
	TFunction<double(const FVector2D&)> Ground;
	/** Current G and B channel values applied to new vertices. */
	float FacadeMask = 0.f;
	float ElementRandom = 0.f;
	/** Current UV1 value applied to new vertices. */
	FVector2f CurrentUnit = FVector2f(0.5f, 0.35f);

	int32 NumTriangles() const { return MaterialIds.Num(); }

	void Tri(int32 Slot, const FVector3d& A, const FVector3d& B, const FVector3d& C,
		const FVector2f& UA, const FVector2f& UB, const FVector2f& UC, const FVector3d& Facing);

	/** Planar quad A-B-C-D (perimeter order) with explicit UVs. */
	void Quad(int32 Slot, const FVector3d& A, const FVector3d& B, const FVector3d& C, const FVector3d& D,
		const FVector2f& UA, const FVector2f& UB, const FVector2f& UC, const FVector2f& UD, const FVector3d& Facing);

	/** Quad with UVs projected on its own plane: U along AB, V along AD (world scale). */
	void QuadProjected(int32 Slot, const FVector3d& A, const FVector3d& B, const FVector3d& C, const FVector3d& D, const FVector3d& Facing);

	/** Oriented box. X/Y are unit axes on the ground plane or any frame; Half is the half size along X, Y, Z. */
	void Box(int32 Slot, const FVector3d& Center, const FVector3d& X, const FVector3d& Y, const FVector3d& Z, const FVector3d& Half,
		bool bSkipBottom = false, bool bSkipBack = false);

	/** Axis-aligned-in-Z box placed against a wall: Along = wall direction, Out = outward normal. */
	void WallBox(int32 Slot, const FVector3d& Center, const FVector3d& Along, const FVector3d& Out, const FVector3d& Half,
		bool bSkipBack = true);

	/** Polygonal tube through points. */
	void Tube(int32 Slot, const TArray<FVector3d>& Points, double Radius, int32 Sides = 6, bool bCaps = false);

	/**
	 * Sweeps a 2D profile (x = outward offset, y = height) along segment Start->End.
	 * StartOut/EndOut are the outward directions at each end (use a miter vector to join segments).
	 */
	void Sweep(int32 Slot, const FVector3d& Start, const FVector3d& End, const FVector3d& StartOut, const FVector3d& EndOut,
		const TArray<FVector2D>& Profile, bool bCapStart, bool bCapEnd);

	/** Flat polygon at height Z (CCW in XY), facing up or down. UV is planar XY. */
	void Polygon(int32 Slot, const TArray<FVector2D>& P, double Z, bool bFaceUp);

	void Append(const FM80MeshBuffer& Other);

	void ToDynamicMesh(UE::Geometry::FDynamicMesh3& Out) const;
};
