#pragma once

#include "CoreMinimal.h"

/** 2D polygon helpers for building footprints. Units are cm, polygons are simple (non self-intersecting). */
namespace M80Poly
{
	MAZZARINOHOUSES_API double SignedArea(const TArray<FVector2D>& P);

	/** Removes duplicate and collinear vertices and makes the winding counter-clockwise. */
	MAZZARINOHOUSES_API void Clean(TArray<FVector2D>& P, double MinEdge = 5.0);

	MAZZARINOHOUSES_API bool Contains(const TArray<FVector2D>& P, const FVector2D& Q);

	/** Ear clipping. Returns false if the polygon could not be fully triangulated. Indices are CCW. */
	MAZZARINOHOUSES_API bool Triangulate(const TArray<FVector2D>& P, TArray<int32>& OutTriangles);

	/** Outward normal of edge i of a CCW polygon. */
	MAZZARINOHOUSES_API FVector2D EdgeNormal(const TArray<FVector2D>& P, int32 Edge);

	/** Miter direction at vertex i: offsetting by Miter*d moves both adjacent edges outward by d. */
	MAZZARINOHOUSES_API FVector2D Miter(const TArray<FVector2D>& P, int32 Vertex, double MaxScale = 3.0);

	/** Offsets each edge outward by its own distance (0 keeps the edge in place). */
	MAZZARINOHOUSES_API TArray<FVector2D> OffsetEdges(const TArray<FVector2D>& P, const TArray<double>& EdgeDistance);

	/** Direction of the long axis of the minimum-area bounding rectangle. */
	MAZZARINOHOUSES_API FVector2D LongAxis(const TArray<FVector2D>& P);

	/** Keeps the part of P where dot(Q, Axis) >= Cut (or <= Cut). Concave inputs may keep thin bridges; Clean() after. */
	MAZZARINOHOUSES_API TArray<FVector2D> ClipHalfPlane(const TArray<FVector2D>& P, const FVector2D& Axis, double Cut, bool bKeepGreater);

	/** Distance from Q to segment AB. */
	MAZZARINOHOUSES_API double SegmentDistance(const FVector2D& Q, const FVector2D& A, const FVector2D& B);
}
