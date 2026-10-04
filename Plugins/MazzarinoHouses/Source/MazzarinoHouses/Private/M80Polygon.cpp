#include "M80Polygon.h"
#include "Algo/Reverse.h"

namespace M80Poly
{
namespace
{
	double Cross(const FVector2D& A, const FVector2D& B, const FVector2D& C)
	{
		return (B.X - A.X) * (C.Y - A.Y) - (B.Y - A.Y) * (C.X - A.X);
	}

	bool InTriangle(const FVector2D& Q, const FVector2D& A, const FVector2D& B, const FVector2D& C)
	{
		return Cross(A, B, Q) >= -1e-6 && Cross(B, C, Q) >= -1e-6 && Cross(C, A, Q) >= -1e-6;
	}
}

double SignedArea(const TArray<FVector2D>& P)
{
	double Area = 0;
	for (int32 i = 0, j = P.Num() - 1; i < P.Num(); j = i++)
	{
		Area += P[j].X * P[i].Y - P[i].X * P[j].Y;
	}
	return Area * 0.5;
}

void Clean(TArray<FVector2D>& P, double MinEdge)
{
	for (int32 i = P.Num() - 1; i >= 0 && P.Num() > 3; --i)
	{
		if (FVector2D::Distance(P[i], P[(i + 1) % P.Num()]) < MinEdge)
		{
			P.RemoveAt(i);
		}
	}
	// Drop vertices whose turn is negligible relative to the adjacent edge lengths.
	bool bChanged = true;
	while (bChanged && P.Num() > 3)
	{
		bChanged = false;
		for (int32 i = 0; i < P.Num(); ++i)
		{
			const FVector2D& A = P[(i + P.Num() - 1) % P.Num()];
			const FVector2D& C = P[(i + 1) % P.Num()];
			const double Base = FMath::Max(1.0, FVector2D::Distance(A, C));
			if (FMath::Abs(Cross(A, P[i], C)) / Base < 2.0)
			{
				P.RemoveAt(i);
				bChanged = true;
				break;
			}
		}
	}
	if (SignedArea(P) < 0)
	{
		Algo::Reverse(P);
	}
}

bool Contains(const TArray<FVector2D>& P, const FVector2D& Q)
{
	bool bInside = false;
	for (int32 i = 0, j = P.Num() - 1; i < P.Num(); j = i++)
	{
		if ((P[i].Y > Q.Y) != (P[j].Y > Q.Y) &&
			Q.X < (P[j].X - P[i].X) * (Q.Y - P[i].Y) / (P[j].Y - P[i].Y) + P[i].X)
		{
			bInside = !bInside;
		}
	}
	return bInside;
}

bool Triangulate(const TArray<FVector2D>& P, TArray<int32>& Out)
{
	Out.Reset();
	TArray<int32> Ring;
	for (int32 i = 0; i < P.Num(); ++i)
	{
		Ring.Add(i);
	}
	if (SignedArea(P) < 0)
	{
		Algo::Reverse(Ring);
	}
	int32 Guard = P.Num() * P.Num() + 8;
	while (Ring.Num() > 3 && --Guard > 0)
	{
		bool bClipped = false;
		for (int32 j = 0; j < Ring.Num(); ++j)
		{
			const int32 A = Ring[(j + Ring.Num() - 1) % Ring.Num()], B = Ring[j], C = Ring[(j + 1) % Ring.Num()];
			if (Cross(P[A], P[B], P[C]) <= 1e-6)
			{
				continue;
			}
			bool bBlocked = false;
			for (int32 K : Ring)
			{
				if (K != A && K != B && K != C && InTriangle(P[K], P[A], P[B], P[C]))
				{
					bBlocked = true;
					break;
				}
			}
			if (!bBlocked)
			{
				Out.Append({A, B, C});
				Ring.RemoveAt(j);
				bClipped = true;
				break;
			}
		}
		if (!bClipped)
		{
			// Degenerate leftovers: clip the flattest vertex so the cap still closes.
			Out.Append({Ring[Ring.Num() - 1], Ring[0], Ring[1]});
			Ring.RemoveAt(0);
		}
	}
	if (Ring.Num() == 3)
	{
		Out.Append({Ring[0], Ring[1], Ring[2]});
	}
	return Guard > 0;
}

FVector2D EdgeNormal(const TArray<FVector2D>& P, int32 Edge)
{
	const FVector2D D = (P[(Edge + 1) % P.Num()] - P[Edge]).GetSafeNormal();
	return FVector2D(D.Y, -D.X);
}

FVector2D Miter(const TArray<FVector2D>& P, int32 Vertex, double MaxScale)
{
	const FVector2D N0 = EdgeNormal(P, (Vertex + P.Num() - 1) % P.Num());
	const FVector2D N1 = EdgeNormal(P, Vertex);
	const double Denominator = 1.0 + FVector2D::DotProduct(N0, N1);
	if (Denominator < 1e-3)
	{
		return N1;
	}
	FVector2D M = (N0 + N1) / Denominator;
	if (M.Size() > MaxScale)
	{
		M = M.GetSafeNormal() * MaxScale;
	}
	return M;
}

TArray<FVector2D> OffsetEdges(const TArray<FVector2D>& P, const TArray<double>& Distance)
{
	// Intersect each pair of consecutive offset edge lines.
	const int32 N = P.Num();
	TArray<FVector2D> Out;
	Out.SetNum(N);
	for (int32 i = 0; i < N; ++i)
	{
		const int32 Prev = (i + N - 1) % N;
		const FVector2D N0 = EdgeNormal(P, Prev), N1 = EdgeNormal(P, i);
		const FVector2D A0 = P[Prev] + N0 * Distance[Prev], D0 = P[i] - P[Prev];
		const FVector2D A1 = P[i] + N1 * Distance[i], D1 = P[(i + 1) % N] - P[i];
		const double Det = D0.X * D1.Y - D0.Y * D1.X;
		if (FMath::Abs(Det) < 1e-6)
		{
			Out[i] = A1;
			continue;
		}
		const FVector2D Delta = A1 - A0;
		const double T = (Delta.X * D1.Y - Delta.Y * D1.X) / Det;
		Out[i] = A0 + D0 * T;
		// Very sharp corners would spike far away: clamp to a sane miter.
		const double MaxShift = 3.0 * FMath::Max(Distance[Prev], Distance[i]) + 1.0;
		if (FVector2D::Distance(Out[i], P[i]) > MaxShift)
		{
			Out[i] = P[i] + (Out[i] - P[i]).GetSafeNormal() * MaxShift;
		}
	}
	return Out;
}

FVector2D LongAxis(const TArray<FVector2D>& P)
{
	double BestArea = TNumericLimits<double>::Max();
	FVector2D Best(1, 0);
	for (int32 i = 0; i < P.Num(); ++i)
	{
		const FVector2D U = (P[(i + 1) % P.Num()] - P[i]).GetSafeNormal();
		if (U.IsNearlyZero())
		{
			continue;
		}
		const FVector2D V(-U.Y, U.X);
		double MinU = TNumericLimits<double>::Max(), MaxU = -MinU, MinV = MinU, MaxV = -MinU;
		for (const FVector2D& Q : P)
		{
			const double DU = FVector2D::DotProduct(Q, U), DV = FVector2D::DotProduct(Q, V);
			MinU = FMath::Min(MinU, DU); MaxU = FMath::Max(MaxU, DU);
			MinV = FMath::Min(MinV, DV); MaxV = FMath::Max(MaxV, DV);
		}
		const double Area = (MaxU - MinU) * (MaxV - MinV);
		if (Area < BestArea)
		{
			BestArea = Area;
			Best = (MaxU - MinU) >= (MaxV - MinV) ? U : V;
		}
	}
	return Best;
}

TArray<FVector2D> ClipHalfPlane(const TArray<FVector2D>& P, const FVector2D& Axis, double Cut, bool bKeepGreater)
{
	TArray<FVector2D> Out;
	for (int32 i = 0; i < P.Num(); ++i)
	{
		const FVector2D& A = P[i];
		const FVector2D& B = P[(i + 1) % P.Num()];
		const double DA = FVector2D::DotProduct(A, Axis) - Cut, DB = FVector2D::DotProduct(B, Axis) - Cut;
		const bool bInA = bKeepGreater ? DA >= 0 : DA <= 0;
		const bool bInB = bKeepGreater ? DB >= 0 : DB <= 0;
		if (bInA)
		{
			Out.Add(A);
		}
		if (bInA != bInB)
		{
			Out.Add(A + (B - A) * (DA / (DA - DB)));
		}
	}
	return Out;
}

double SegmentDistance(const FVector2D& Q, const FVector2D& A, const FVector2D& B)
{
	const FVector2D D = B - A;
	const double T = FMath::Clamp(FVector2D::DotProduct(Q - A, D) / FMath::Max(1e-6, D.SizeSquared()), 0.0, 1.0);
	return FVector2D::Distance(Q, A + D * T);
}
}
