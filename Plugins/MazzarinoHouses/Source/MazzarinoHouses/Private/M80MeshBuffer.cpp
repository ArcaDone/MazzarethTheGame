#include "M80MeshBuffer.h"
#include "M80Polygon.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"

using UE::Geometry::FDynamicMesh3;

namespace
{
	FVector2f PlanarUV(const FVector3d& P, const FVector3d& U, const FVector3d& V)
	{
		return FVector2f(float(FVector3d::DotProduct(P, U) / 100.0), float(-FVector3d::DotProduct(P, V) / 100.0));
	}
}

void FM80MeshBuffer::Tri(int32 Slot, const FVector3d& A, const FVector3d& B, const FVector3d& C,
	const FVector2f& UA, const FVector2f& UB, const FVector2f& UC, const FVector3d& Facing)
{
	// GeometryCore treats (C-A)x(B-A) as the front normal (left-handed coordinates).
	FVector3d Normal = FVector3d::CrossProduct(C - A, B - A);
	const double Length = Normal.Size();
	if (Length < 1e-4)
	{
		return;
	}
	Normal /= Length;
	const bool bFlip = !Facing.IsNearlyZero() && FVector3d::DotProduct(Normal, Facing) < 0;
	const FVector3d* V[3] = {&A, bFlip ? &C : &B, bFlip ? &B : &C};
	const FVector2f* T[3] = {&UA, bFlip ? &UC : &UB, bFlip ? &UB : &UC};
	if (bFlip)
	{
		Normal = -Normal;
	}
	for (int32 i = 0; i < 3; ++i)
	{
		const FVector3d& P = *V[i];
		float Height = 1.f;
		if (Ground)
		{
			Height = float(FMath::Clamp((P.Z - Ground(FVector2D(P.X, P.Y))) / 300.0, 0.0, 1.0));
		}
		Positions.Add(P);
		Normals.Add(FVector3f(Normal));
		UVs.Add(*T[i]);
		Colors.Add(FVector4f(Height, FacadeMask, ElementRandom, 1.f));
		UnitData.Add(CurrentUnit);
	}
	MaterialIds.Add(Slot);
}

void FM80MeshBuffer::Quad(int32 Slot, const FVector3d& A, const FVector3d& B, const FVector3d& C, const FVector3d& D,
	const FVector2f& UA, const FVector2f& UB, const FVector2f& UC, const FVector2f& UD, const FVector3d& Facing)
{
	Tri(Slot, A, B, C, UA, UB, UC, Facing);
	Tri(Slot, A, C, D, UA, UC, UD, Facing);
}

void FM80MeshBuffer::QuadProjected(int32 Slot, const FVector3d& A, const FVector3d& B, const FVector3d& C, const FVector3d& D, const FVector3d& Facing)
{
	FVector3d N = Facing.GetSafeNormal();
	if (N.IsNearlyZero())
	{
		N = FVector3d::CrossProduct(D - A, B - A).GetSafeNormal();
	}
	// Vertical faces: U runs horizontally, V follows world Z, so courses line up across faces.
	FVector3d U, V;
	if (FMath::Abs(N.Z) < 0.7)
	{
		U = FVector3d::CrossProduct(FVector3d::UnitZ(), N).GetSafeNormal();
		V = FVector3d::UnitZ();
	}
	else
	{
		U = (B - A).GetSafeNormal();
		if (U.IsNearlyZero())
		{
			U = FVector3d::UnitX();
		}
		V = FVector3d::CrossProduct(N, U).GetSafeNormal();
	}
	Quad(Slot, A, B, C, D, PlanarUV(A, U, V), PlanarUV(B, U, V), PlanarUV(C, U, V), PlanarUV(D, U, V), N);
}

void FM80MeshBuffer::Box(int32 Slot, const FVector3d& Center, const FVector3d& X, const FVector3d& Y, const FVector3d& Z, const FVector3d& Half,
	bool bSkipBottom, bool bSkipBack)
{
	if (Half.X <= 0.05 || Half.Y <= 0.05 || Half.Z <= 0.05)
	{
		return;
	}
	auto P = [&](double SX, double SY, double SZ) { return Center + X * (SX * Half.X) + Y * (SY * Half.Y) + Z * (SZ * Half.Z); };
	QuadProjected(Slot, P(1, -1, -1), P(1, 1, -1), P(1, 1, 1), P(1, -1, 1), X);
	QuadProjected(Slot, P(-1, 1, -1), P(-1, -1, -1), P(-1, -1, 1), P(-1, 1, 1), -X);
	QuadProjected(Slot, P(1, 1, -1), P(-1, 1, -1), P(-1, 1, 1), P(1, 1, 1), Y);
	if (!bSkipBack)
	{
		QuadProjected(Slot, P(-1, -1, -1), P(1, -1, -1), P(1, -1, 1), P(-1, -1, 1), -Y);
	}
	QuadProjected(Slot, P(-1, -1, 1), P(1, -1, 1), P(1, 1, 1), P(-1, 1, 1), Z);
	if (!bSkipBottom)
	{
		QuadProjected(Slot, P(-1, 1, -1), P(1, 1, -1), P(1, -1, -1), P(-1, -1, -1), -Z);
	}
}

void FM80MeshBuffer::WallBox(int32 Slot, const FVector3d& Center, const FVector3d& Along, const FVector3d& Out, const FVector3d& Half, bool bSkipBack)
{
	Box(Slot, Center, Along, Out, FVector3d::UnitZ(), Half, false, bSkipBack);
}

void FM80MeshBuffer::Tube(int32 Slot, const TArray<FVector3d>& Points, double Radius, int32 Sides, bool bCaps)
{
	for (int32 i = 0; i + 1 < Points.Num(); ++i)
	{
		const FVector3d A = Points[i], B = Points[i + 1];
		const FVector3d D = (B - A).GetSafeNormal();
		if (D.IsNearlyZero())
		{
			continue;
		}
		const FVector3d U = FVector3d::CrossProduct(D, FMath::Abs(D.Z) > 0.9 ? FVector3d::UnitX() : FVector3d::UnitZ()).GetSafeNormal();
		const FVector3d V = FVector3d::CrossProduct(D, U);
		const float Len = float((B - A).Size() / 100.0);
		for (int32 k = 0; k < Sides; ++k)
		{
			const double A0 = 2 * PI * k / Sides, A1 = 2 * PI * (k + 1) / Sides;
			const FVector3d R0 = (U * FMath::Cos(A0) + V * FMath::Sin(A0)) * Radius;
			const FVector3d R1 = (U * FMath::Cos(A1) + V * FMath::Sin(A1)) * Radius;
			const float U0 = float(k) / Sides, U1 = float(k + 1) / Sides;
			Quad(Slot, A + R0, A + R1, B + R1, B + R0, {U0, 0}, {U1, 0}, {U1, Len}, {U0, Len}, (R0 + R1).GetSafeNormal());
			if (bCaps && i == 0)
			{
				Tri(Slot, A, A + R0, A + R1, {0, 0}, {U0, 0}, {U1, 0}, -D);
			}
			if (bCaps && i + 2 == Points.Num())
			{
				Tri(Slot, B, B + R0, B + R1, {0, 0}, {U0, 0}, {U1, 0}, D);
			}
		}
	}
}

void FM80MeshBuffer::Sweep(int32 Slot, const FVector3d& Start, const FVector3d& End, const FVector3d& StartOut, const FVector3d& EndOut,
	const TArray<FVector2D>& Profile, bool bCapStart, bool bCapEnd)
{
	const FVector3d Along = (End - Start).GetSafeNormal();
	const FVector3d UpDir = FVector3d::UnitZ();
	const FVector3d OutDir = FVector3d::CrossProduct(UpDir, Along).GetSafeNormal() * (FVector3d::DotProduct(FVector3d::CrossProduct(UpDir, Along), StartOut) < 0 ? -1.0 : 1.0);
	auto AtStart = [&](const FVector2D& Q) { return Start + StartOut * Q.X + UpDir * Q.Y; };
	auto AtEnd = [&](const FVector2D& Q) { return End + EndOut * Q.X + UpDir * Q.Y; };
	const int32 N = Profile.Num();
	for (int32 k = 0; k < N; ++k)
	{
		const FVector2D& P0 = Profile[k];
		const FVector2D& P1 = Profile[(k + 1) % N];
		if (FMath::Abs(P0.X) <= 0.01 && FMath::Abs(P1.X) <= 0.01)
		{
			continue; // lies on the wall plane, hidden
		}
		// Profile is CCW in (out, up): the outward 2D normal of a segment is (dy, -dx).
		const FVector2D D = P1 - P0;
		const FVector3d Facing = OutDir * D.Y + UpDir * (-D.X);
		QuadProjected(Slot, AtStart(P0), AtEnd(P0), AtEnd(P1), AtStart(P1), Facing);
	}
	if (bCapStart || bCapEnd)
	{
		TArray<int32> Tris;
		M80Poly::Triangulate(Profile, Tris);
		for (int32 t = 0; t + 2 < Tris.Num(); t += 3)
		{
			const FVector2D &A = Profile[Tris[t]], &B = Profile[Tris[t + 1]], &C = Profile[Tris[t + 2]];
			const FVector2f UA(float(A.X / 100), float(-A.Y / 100)), UB(float(B.X / 100), float(-B.Y / 100)), UC(float(C.X / 100), float(-C.Y / 100));
			if (bCapStart)
			{
				Tri(Slot, AtStart(A), AtStart(B), AtStart(C), UA, UB, UC, -Along);
			}
			if (bCapEnd)
			{
				Tri(Slot, AtEnd(A), AtEnd(B), AtEnd(C), UA, UB, UC, Along);
			}
		}
	}
}

void FM80MeshBuffer::Polygon(int32 Slot, const TArray<FVector2D>& P, double Z, bool bFaceUp)
{
	TArray<int32> Tris;
	M80Poly::Triangulate(P, Tris);
	const FVector3d Facing(0, 0, bFaceUp ? 1 : -1);
	for (int32 t = 0; t + 2 < Tris.Num(); t += 3)
	{
		const FVector2D &A = P[Tris[t]], &B = P[Tris[t + 1]], &C = P[Tris[t + 2]];
		Tri(Slot, FVector3d(A.X, A.Y, Z), FVector3d(B.X, B.Y, Z), FVector3d(C.X, C.Y, Z),
			FVector2f(A / 100.0), FVector2f(B / 100.0), FVector2f(C / 100.0), Facing);
	}
}

void FM80MeshBuffer::Append(const FM80MeshBuffer& Other)
{
	Positions.Append(Other.Positions);
	Normals.Append(Other.Normals);
	UVs.Append(Other.UVs);
	Colors.Append(Other.Colors);
	UnitData.Append(Other.UnitData);
	MaterialIds.Append(Other.MaterialIds);
}

void FM80MeshBuffer::ToDynamicMesh(FDynamicMesh3& Out) const
{
	Out.Clear();
	Out.EnableAttributes();
	Out.Attributes()->EnableMaterialID();
	Out.Attributes()->EnablePrimaryColors();
	Out.Attributes()->SetNumUVLayers(2);
	auto* UVOverlay = Out.Attributes()->PrimaryUV();
	auto* UnitOverlay = Out.Attributes()->GetUVLayer(1);
	auto* NormalOverlay = Out.Attributes()->PrimaryNormals();
	auto* ColorOverlay = Out.Attributes()->PrimaryColors();
	auto* Materials = Out.Attributes()->GetMaterialID();

	// Weld vertices that share every attribute: flat-shaded quads then cost 4 vertices instead of 6.
	struct FKey
	{
		FVector3d P; FVector3f N; FVector2f UV; FVector4f C; FVector2f Unit;
		bool operator==(const FKey& O) const { return P == O.P && N == O.N && UV == O.UV && C == O.C && Unit == O.Unit; }
	};
	struct FKeyFuncs : BaseKeyFuncs<TPair<FKey, int32>, FKey>
	{
		static const FKey& GetSetKey(const TPair<FKey, int32>& E) { return E.Key; }
		static bool Matches(const FKey& A, const FKey& B) { return A == B; }
		static uint32 GetKeyHash(const FKey& K)
		{
			uint32 Hash = GetTypeHash(K.P.X);
			for (const double V : {K.P.Y, K.P.Z})
			{
				Hash = HashCombineFast(Hash, GetTypeHash(V));
			}
			for (const float V : {K.N.X, K.N.Y, K.N.Z, K.UV.X, K.UV.Y, K.C.X, K.C.Y, K.C.Z, K.C.W, K.Unit.X, K.Unit.Y})
			{
				Hash = HashCombineFast(Hash, GetTypeHash(V));
			}
			return Hash;
		}
	};
	TSet<TPair<FKey, int32>, FKeyFuncs> Welded;
	Welded.Reserve(Positions.Num() / 2);
	TArray<int32> VertexOf;
	VertexOf.SetNumUninitialized(Positions.Num());
	TArray<FIntVector4> Elements; // uv, normal, color, unit element per welded vertex
	for (int32 i = 0; i < Positions.Num(); ++i)
	{
		const FKey Key{Positions[i], Normals[i], UVs[i], Colors[i], UnitData[i]};
		if (const TPair<FKey, int32>* Found = Welded.Find(Key))
		{
			VertexOf[i] = Found->Value;
			continue;
		}
		const int32 V = Out.AppendVertex(Positions[i]);
		Elements.Add(FIntVector4(UVOverlay->AppendElement(UVs[i]), NormalOverlay->AppendElement(Normals[i]), ColorOverlay->AppendElement(Colors[i]),
			UnitOverlay->AppendElement(UnitData[i])));
		Welded.Add({Key, V});
		VertexOf[i] = V;
	}
	for (int32 t = 0; t < MaterialIds.Num(); ++t)
	{
		int32 A = VertexOf[t * 3], B = VertexOf[t * 3 + 1], C = VertexOf[t * 3 + 2];
		if (A == B || B == C || A == C)
		{
			continue;
		}
		int32 Tid = Out.AppendTriangle(A, B, C);
		if (Tid < 0)
		{
			// Edge already shared by two triangles (coplanar overlap): give this one private vertices.
			int32* Ids[3] = {&A, &B, &C};
			for (int32 k = 0; k < 3; ++k)
			{
				const int32 Src = t * 3 + k;
				*Ids[k] = Out.AppendVertex(Positions[Src]);
				Elements.Add(FIntVector4(UVOverlay->AppendElement(UVs[Src]), NormalOverlay->AppendElement(Normals[Src]), ColorOverlay->AppendElement(Colors[Src]),
					UnitOverlay->AppendElement(UnitData[Src])));
			}
			Tid = Out.AppendTriangle(A, B, C);
			if (Tid < 0)
			{
				continue;
			}
		}
		UVOverlay->SetTriangle(Tid, UE::Geometry::FIndex3i(Elements[A].X, Elements[B].X, Elements[C].X));
		NormalOverlay->SetTriangle(Tid, UE::Geometry::FIndex3i(Elements[A].Y, Elements[B].Y, Elements[C].Y));
		ColorOverlay->SetTriangle(Tid, UE::Geometry::FIndex3i(Elements[A].Z, Elements[B].Z, Elements[C].Z));
		UnitOverlay->SetTriangle(Tid, UE::Geometry::FIndex3i(Elements[A].W, Elements[B].W, Elements[C].W));
		Materials->SetValue(Tid, MaterialIds[t]);
	}
}
