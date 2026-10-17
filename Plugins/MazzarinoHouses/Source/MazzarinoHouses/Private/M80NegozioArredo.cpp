#include "M80House.h"
#include "M80Negozio.h"
#include "Engine/StaticMesh.h"

namespace
{
	/**
	 * A shop room being furnished, in its own frame: X towards the street (the facade's inside at X = 0, the back wall at
	 * X = -D), Y along the street (side walls at +-W/2), Z up from the floor. The packages' pieces face +X with their back
	 * at their bounds' smallest X: a piece against a wall is turned to face into the room and its back put on the wall.
	 */
	struct FRoomFill
	{
		double W = 0, D = 0, H = 0;
		FTransform Frame;
		FRandomStream Rng;
		TArray<FM80SavedProp>& Out;
		TArray<FBox2D> Taken;
		int32 Count = 0;
		/** The counter, once laid: its run (start, direction), length, depth, top. */
		bool bCounter = false;
		FVector2D CounterStart, CounterDir, CounterFace;
		double CounterLen = 0, CounterDepth = 0, CounterTop = 0;

		FRoomFill(double InW, double InD, double InH, const FTransform& InFrame, int32 Seed, TArray<FM80SavedProp>& InOut)
			: W(InW), D(InD), H(InH), Frame(InFrame), Rng(Seed), Out(InOut)
		{
		}

		static FBox Bounds(const UStaticMesh* M) { return M ? M->GetBoundingBox() : FBox(FVector::ZeroVector, FVector::ZeroVector); }
		static double Along(const UStaticMesh* M) { const FBox B = Bounds(M); return B.Max.Y - B.Min.Y; }
		static double Deep(const UStaticMesh* M) { const FBox B = Bounds(M); return B.Max.X - B.Min.X; }

		bool Inside(const FBox2D& B) const
		{
			return B.Min.X >= -D - 1 && B.Max.X <= 1 && B.Min.Y >= -W * 0.5 - 1 && B.Max.Y <= W * 0.5 + 1;
		}
		bool Free(const FBox2D& B) const
		{
			const FBox2D S(B.Min + FVector2D(2, 2), B.Max - FVector2D(2, 2));
			for (const FBox2D& T : Taken)
			{
				if (S.Intersect(T))
				{
					return false;
				}
			}
			return Inside(B);
		}

		/** The room-plan box a piece takes with its back's middle at At, facing Face (an axis), its bottom at Z. */
		FBox2D Footprint(const UStaticMesh* M, const FVector2D& At, const FVector2D& Face) const
		{
			const double A = Along(M), Dp = Deep(M);
			const FVector2D Side(-Face.Y, Face.X);
			const FVector2D C = At + Face * (Dp * 0.5);
			const FVector2D Half = FVector2D(FMath::Abs(Face.X) * Dp * 0.5 + FMath::Abs(Side.X) * A * 0.5, FMath::Abs(Face.Y) * Dp * 0.5 + FMath::Abs(Side.Y) * A * 0.5);
			return FBox2D(C - Half, C + Half);
		}

		/** Places M with its back's middle at At (room plan), facing Face, its bottom at Z. */
		void Put(UStaticMesh* M, const FVector2D& At, const FVector2D& Face, double Z, bool bSolid, bool bTake = true)
		{
			if (!M)
			{
				return;
			}
			const FBox B = Bounds(M);
			const FQuat Q = FRotator(0.0, FMath::RadiansToDegrees(FMath::Atan2(Face.Y, Face.X)), 0.0).Quaternion();
			const FVector Back(B.Min.X, (B.Min.Y + B.Max.Y) * 0.5, B.Min.Z);
			const FVector Local = FVector(At.X, At.Y, Z) - Q.RotateVector(Back);
			FM80SavedProp& P = Out.AddDefaulted_GetRef();
			P.Mesh = M;
			P.Transform = FTransform(Q, Local) * Frame;
			P.bArchitecture = bSolid;
			if (bTake)
			{
				Taken.Add(Footprint(M, At, Face));
			}
			++Count;
		}

		struct FWall
		{
			FVector2D Start, Dir, Face;
			double Len;
		};
		FWall Back() const { return {FVector2D(-D, -W * 0.5), FVector2D(0, 1), FVector2D(1, 0), W}; }
		/** Side walls from the back corner towards the street, stopping 1.4 m short of the shop window. */
		FWall Left() const { return {FVector2D(-D, -W * 0.5), FVector2D(1, 0), FVector2D(0, 1), FMath::Max(0.0, D - 140)}; }
		FWall Right() const { return {FVector2D(-D, W * 0.5), FVector2D(1, 0), FVector2D(0, -1), FMath::Max(0.0, D - 140)}; }

		/** Modules side by side along a wall, the widest that fit first, from where the wall is free. */
		void AlongWall(const FWall& Wall, const TArray<TObjectPtr<UStaticMesh>>& Modules, double MaxLen, bool bFill, int32 MaxCount, double Z = 0.0, bool bSolid = true)
		{
			TArray<UStaticMesh*> Sorted;
			for (UStaticMesh* M : Modules)
			{
				if (M)
				{
					Sorted.Add(M);
				}
			}
			if (Sorted.IsEmpty())
			{
				return;
			}
			Sorted.Sort([](const UStaticMesh& A, const UStaticMesh& B) { return Along(&A) > Along(&B); });
			const double Limit = MaxLen > 0 ? FMath::Min(MaxLen, Wall.Len) : Wall.Len;
			double S = 10.0, Used = 0.0;
			int32 Placed = 0;
			while (S < Wall.Len - 10.0 && Used < Limit && (bFill || Placed < MaxCount))
			{
				bool bAny = false;
				for (UStaticMesh* M : Sorted)
				{
					const double A = Along(M);
					if (S + A > Wall.Len - 10.0 || Used + A > Limit + 1)
					{
						continue;
					}
					const FVector2D At = Wall.Start + Wall.Dir * (S + A * 0.5);
					if (!Free(Footprint(M, At, Wall.Face)))
					{
						continue;
					}
					Put(M, At, Wall.Face, Z, bSolid);
					S += A;
					Used += A;
					++Placed;
					bAny = true;
					break;
				}
				if (!bAny)
				{
					S += 25.0;   // something in the way here: a little further on
				}
			}
		}

		/** The counter: its chain, cut or lengthened with fillers to the room, its back Distance from the wall. */
		void Counter(const FM80ZonaNegozio& Z)
		{
			TArray<UStaticMesh*> Chain;
			for (UStaticMesh* M : Z.Pezzi)
			{
				if (M)
				{
					Chain.Add(M);
				}
			}
			if (Chain.IsEmpty())
			{
				return;
			}
			const bool bSide = Z.Muro == EM80MuroNegozio::Laterale;
			// Along the back wall: a passage of 90 cm at one end to get behind it. Along a side wall: from the back.
			const double Room = bSide ? D - 140 - 90 : W - 90 - 20;
			auto Total = [&]() { double T = 0; for (UStaticMesh* M : Chain) { T += Along(M); } return T; };
			while (Chain.Num() > 2 && Total() > Room)
			{
				Chain.RemoveAt(Chain.Num() / 2);
			}
			TArray<UStaticMesh*> Fillers;
			for (UStaticMesh* M : Z.Riempitivi)
			{
				if (M)
				{
					Fillers.Add(M);
				}
			}
			Fillers.Sort([](const UStaticMesh& A, const UStaticMesh& B) { return Along(&A) > Along(&B); });
			for (int32 Guard = 0; Guard < 12 && Fillers.Num() && Total() < Room * 0.6; ++Guard)
			{
				UStaticMesh* F = Fillers[0];
				for (UStaticMesh* C : Fillers)
				{
					if (Total() + Along(C) <= Room * 0.6)
					{
						F = C;
						break;
					}
				}
				Chain.Insert(F, FMath::Max(1, Chain.Num() - 1));
			}
			const double Len = Total();
			if (Len > Room + 1)
			{
				return;
			}
			const double Dist = FMath::Clamp(double(Z.Distanza), 80.0, (bSide ? W : D) - 200.0);
			const FVector2D Face = bSide ? FVector2D(0, 1) : FVector2D(1, 0);
			const FVector2D Dir = bSide ? FVector2D(1, 0) : FVector2D(0, 1);
			const FVector2D Start = bSide ? FVector2D(-D + 90, -W * 0.5 + Dist) : FVector2D(-D + Dist, -W * 0.5 + 20);
			double S = 0, Top = 0, Depth = 0;
			for (UStaticMesh* M : Chain)
			{
				const double A = Along(M);
				Put(M, Start + Dir * (S + A * 0.5), Face, 0.0, true);
				S += A;
				Top = FMath::Max(Top, Bounds(M).Max.Z - Bounds(M).Min.Z);
				Depth = FMath::Max(Depth, Deep(M));
			}
			// Behind the counter is the shopkeeper's: nothing else there.
			Taken.Add(bSide ? FBox2D(FVector2D(-D, -W * 0.5), FVector2D(-D + 90 + Len, -W * 0.5 + Dist))
							: FBox2D(FVector2D(-D, -W * 0.5), FVector2D(-D + Dist, -W * 0.5 + 20 + Len)));
			bCounter = true;
			CounterStart = Start;
			CounterDir = Dir;
			CounterFace = Face;
			CounterLen = Len;
			CounterDepth = Depth;
			CounterTop = Top;
		}

		/** Objects along the counter: on its top or hanging over it. */
		void OnCounter(const FM80ZonaNegozio& Z, bool bHanging)
		{
			if (!bCounter)
			{
				return;
			}
			const int32 N = FMath::Max(1, Z.Max);
			for (int32 i = 0; i < N; ++i)
			{
				UStaticMesh* M = Z.Pezzi.Num() ? Z.Pezzi[Rng.RandRange(0, Z.Pezzi.Num() - 1)].Get() : nullptr;
				if (!M)
				{
					continue;
				}
				const double S = CounterLen * (i + 0.5 + Rng.FRandRange(-0.2f, 0.2f)) / N;
				const FVector2D At = CounterStart + CounterDir * S + CounterFace * (CounterDepth * 0.5 - Deep(M) * 0.5);
				const double Z0 = bHanging ? H - (Bounds(M).Max.Z - Bounds(M).Min.Z) - 15.0 : CounterTop;
				Put(M, At, CounterFace, Z0, false, false);
			}
		}

		/** Objects on the floor: in the middle of the room, or along the walls. */
		void Scatter(const FM80ZonaNegozio& Z, bool bMiddle)
		{
			const int32 N = FMath::Max(1, Z.Max);
			int32 Placed = 0;
			for (int32 Try = 0; Try < N * 12 && Placed < N; ++Try)
			{
				UStaticMesh* M = Z.Pezzi.Num() ? Z.Pezzi[Rng.RandRange(0, Z.Pezzi.Num() - 1)].Get() : nullptr;
				if (!M)
				{
					return;
				}
				FVector2D At, Face;
				if (bMiddle)
				{
					Face = Rng.FRand() < 0.5f ? FVector2D(1, 0) : FVector2D(0, 1);
					At = FVector2D(Rng.FRandRange(-D + 100, -180), Rng.FRandRange(-W * 0.5 + 80, W * 0.5 - 80)) - Face * (Deep(M) * 0.5);
				}
				else
				{
					const FWall Wall = Rng.FRand() < 0.5f ? Left() : Right();
					Face = Wall.Face;
					At = Wall.Start + Wall.Dir * Rng.FRandRange(20.f, FMath::Max(40.f, float(Wall.Len - 20)));
				}
				if (Free(Footprint(M, At, Face)))
				{
					Put(M, At, Face, 0.0, true);
					++Placed;
				}
			}
		}

		/** Tables with chairs round them, by the shop window. */
		void Tables(const FM80ZonaNegozio& Z)
		{
			UStaticMesh* Table = Z.Pezzi.Num() ? Z.Pezzi[0].Get() : nullptr;
			UStaticMesh* Chair = Z.Pezzi.Num() > 1 ? Z.Pezzi[1].Get() : nullptr;
			if (!Table)
			{
				return;
			}
			const int32 N = FMath::Max(1, Z.Max);
			int32 Placed = 0;
			for (double Y = -W * 0.5 + 110; Y < W * 0.5 - 110 && Placed < N; Y += 220)
			{
				for (double X = -150; X > -D + 150 && Placed < N; X -= 230)
				{
					const FVector2D C(X, Y);
					const FBox2D Area(C - FVector2D(100, 100), C + FVector2D(100, 100));
					if (!Free(Area))
					{
						continue;
					}
					Put(Table, C - FVector2D(Deep(Table) * 0.5, 0), FVector2D(1, 0), 0.0, true, false);
					const int32 Chairs = Chair ? Rng.RandRange(2, 4) : 0;
					for (int32 k = 0; k < Chairs; ++k)
					{
						const FVector2D Dir = FVector2D(1, 0).GetRotated(90.0 * k + 45.0 * (Rng.FRand() < 0.5f));
						const double R = FMath::Max(Deep(Table), Along(Table)) * 0.5 + 25.0;
						// The chair faces the table: its back away from it.
						Put(Chair, C + Dir * (R + Deep(Chair)), -Dir, 0.0, false, false);
					}
					Taken.Add(Area);
					++Placed;
				}
			}
		}

		/** Things hung on the free stretches of the side walls, at eye height. */
		void OnWalls(const FM80ZonaNegozio& Z)
		{
			const int32 N = FMath::Max(1, Z.Max);
			for (int32 i = 0; i < N && i < Z.Pezzi.Num(); ++i)
			{
				UStaticMesh* M = Z.Pezzi[i].Get();
				if (!M)
				{
					continue;
				}
				const FWall Wall = (i % 2) ? Right() : Left();
				const double Hm = Bounds(M).Max.Z - Bounds(M).Min.Z;
				const double S = Wall.Len * Rng.FRandRange(0.3f, 0.9f);
				Put(M, Wall.Start + Wall.Dir * S, Wall.Face, FMath::Clamp(165.0 - Hm * 0.5, 20.0, H - Hm - 10.0), false, false);
			}
		}

		/** Ceiling lamps, one every PerM2 square metres, spread over the room. */
		void Ceiling(const FM80ZonaNegozio& Z)
		{
			UStaticMesh* M = Z.Pezzi.Num() ? Z.Pezzi[0].Get() : nullptr;
			if (!M)
			{
				return;
			}
			const int32 N = FMath::Clamp(FMath::RoundToInt(W * D / 10000.0 / FMath::Max(1.f, Z.OgniM2)), 1, 8);
			const int32 Cols = FMath::Max(1, FMath::RoundToInt(FMath::Sqrt(N * W / D)));
			const int32 Rows = FMath::Max(1, FMath::DivideAndRoundUp(N, Cols));
			const FBox B = Bounds(M);
			for (int32 r = 0; r < Rows; ++r)
			{
				for (int32 c = 0; c < Cols; ++c)
				{
					const FVector2D At(-D * (r + 0.5) / Rows - Deep(M) * 0.5, -W * 0.5 + W * (c + 0.5) / Cols);
					Put(M, At, FVector2D(1, 0), H - (B.Max.Z - B.Min.Z), false, false);
				}
			}
		}
	};
}

int32 AM80House::ArredaNegozio(const UM80PrototipoNegozio* P, const FTransform& Frame, double Width, double Depth, double Height, int32 Seed,
	TArray<FM80SavedProp>& Out)
{
	if (!P || Width < 150 || Depth < 150)
	{
		return 0;
	}
	FRoomFill F(Width, Depth, Height, Frame, Seed, Out);
	// Walls and counters first (they take the room), then what goes on, over and between them.
	for (int32 Pass = 0; Pass < 3; ++Pass)
	{
		for (const FM80ZonaNegozio& Z : P->Zone)
		{
			switch (Z.Tipo)
			{
			case EM80TipoZona::Muro:
				if (Pass == 0)
				{
					if (Z.Muro == EM80MuroNegozio::Fondo || Z.Muro == EM80MuroNegozio::Qualsiasi)
					{
						F.AlongWall(F.Back(), Z.Pezzi, Z.Lunghezza, Z.bRiempi, Z.Max);
					}
					if (Z.Muro == EM80MuroNegozio::Laterale)
					{
						F.AlongWall(F.Rng.FRand() < 0.5f ? F.Left() : F.Right(), Z.Pezzi, Z.Lunghezza, Z.bRiempi, Z.Max);
					}
				}
				break;
			case EM80TipoZona::Banco:
				if (Pass == 0 && !F.bCounter)
				{
					F.Counter(Z);
				}
				break;
			case EM80TipoZona::SulBanco:
			case EM80TipoZona::SopraBanco:
				if (Pass == 1)
				{
					F.OnCounter(Z, Z.Tipo == EM80TipoZona::SopraBanco);
				}
				break;
			case EM80TipoZona::Tavoli:
				if (Pass == 1)
				{
					F.Tables(Z);
				}
				break;
			case EM80TipoZona::Centro:
			case EM80TipoZona::ATerra:
				if (Pass == 2)
				{
					F.Scatter(Z, Z.Tipo == EM80TipoZona::Centro);
				}
				break;
			case EM80TipoZona::Pareti:
				if (Pass == 2)
				{
					F.OnWalls(Z);
				}
				break;
			case EM80TipoZona::Soffitto:
				if (Pass == 2)
				{
					F.Ceiling(Z);
				}
				break;
			}
		}
	}
	return F.Count;
}
