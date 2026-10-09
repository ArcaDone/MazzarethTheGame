#include "M80HouseBuilder.h"
#include "M80Polygon.h"
#include "Algo/Reverse.h"

const TCHAR* const M80NobleKit::Paths[M80NobleKit::Count] = {
	TEXT("/Game/Mazzarino80/Kit/Balconi/SM_M80_Balcone_Lastra_Volute.SM_M80_Balcone_Lastra_Volute"),
	TEXT("/Game/Mazzarino80/Kit/Balconi/SM_M80_Balcone_Lastra_Mascheroni.SM_M80_Balcone_Lastra_Mascheroni"),
	TEXT("/Game/Mazzarino80/Kit/Balconi/SM_M80_Balcone_Lastra_Acanto.SM_M80_Balcone_Lastra_Acanto"),
	TEXT("/Game/Mazzarino80/Kit/Balconi/SM_M80_Balcone_Mensola_Volute.SM_M80_Balcone_Mensola_Volute"),
	TEXT("/Game/Mazzarino80/Kit/Balconi/SM_M80_Balcone_Mensola_Leone.SM_M80_Balcone_Mensola_Leone"),
	TEXT("/Game/Mazzarino80/Kit/Balconi/SM_M80_Balcone_Mensola_Cane.SM_M80_Balcone_Mensola_Cane"),
	TEXT("/Game/Mazzarino80/Kit/Balconi/SM_M80_Balcone_Mensola_Acanto.SM_M80_Balcone_Mensola_Acanto"),
	TEXT("/Game/Mazzarino80/Kit/Balconi/SM_M80_Balcone_Decoro_Riquadro.SM_M80_Balcone_Decoro_Riquadro"),
	TEXT("/Game/Mazzarino80/Kit/Balconi/SM_M80_Balcone_Decoro_Giglio.SM_M80_Balcone_Decoro_Giglio"),
	TEXT("/Game/Mazzarino80/Kit/Balconi/SM_M80_Balcone_Decoro_Rosone.SM_M80_Balcone_Decoro_Rosone"),
	TEXT("/Game/Mazzarino80/Kit/Balconi/SM_M80_Balcone_Ringhiera_Dritta_180.SM_M80_Balcone_Ringhiera_Dritta_180"),
	TEXT("/Game/Mazzarino80/Kit/Balconi/SM_M80_Balcone_Ringhiera_Dritta_240.SM_M80_Balcone_Ringhiera_Dritta_240"),
	TEXT("/Game/Mazzarino80/Kit/Balconi/SM_M80_Balcone_Ringhiera_Dritta_300.SM_M80_Balcone_Ringhiera_Dritta_300"),
	TEXT("/Game/Mazzarino80/Kit/Balconi/SM_M80_Balcone_Ringhiera_PettoOca_180.SM_M80_Balcone_Ringhiera_PettoOca_180"),
	TEXT("/Game/Mazzarino80/Kit/Balconi/SM_M80_Balcone_Ringhiera_PettoOca_240.SM_M80_Balcone_Ringhiera_PettoOca_240"),
	TEXT("/Game/Mazzarino80/Kit/Balconi/SM_M80_Balcone_Ringhiera_PettoOca_300.SM_M80_Balcone_Ringhiera_PettoOca_300"),
};

namespace
{
using FVec = FVector3d;
const FVec Up(0, 0, 1);

enum class EOpen : uint8 { Window, French, Small, Door, Garage, CellarDoor, CellarWindow, Shop };
enum class EShutter : uint8 { None, Open, Closed, Roller };

struct FOpening
{
	EOpen Type = EOpen::Window;
	int32 Edge = 0;
	int32 Level = 0;
	double X0 = 0, X1 = 0, Z0 = 0, Z1 = 0;
	bool bArch = false, bBalcony = false, bGrille = false, bFramed = true, bPointed = false, bBifora = false;
	EShutter Shutter = EShutter::None;
	float Rand = 0.f;

	double Width() const { return X1 - X0; }
	double Mid() const { return (X0 + X1) * 0.5; }
	double Spring() const { return bArch ? Z1 - Width() * (bPointed ? 0.866 : 0.5) : Z1; }
	double TopAt(double X) const
	{
		if (!bArch)
		{
			return Z1;
		}
		if (bPointed)
		{
			// Two arcs of radius = width centred on the opposite jambs (Arab-Norman pointed arch).
			const double Far = Width() * 0.5 + FMath::Abs(X - Mid());
			return Spring() + FMath::Sqrt(FMath::Max(0.0, Width() * Width() - Far * Far));
		}
		const double R = Width() * 0.5, D = X - Mid();
		return Spring() + FMath::Sqrt(FMath::Max(0.0, R * R - D * D));
	}
	bool IsDoorLike() const { return Type == EOpen::Door || Type == EOpen::Garage || Type == EOpen::CellarDoor || Type == EOpen::Shop; }
	bool HasGlass() const { return Type == EOpen::Window || Type == EOpen::French || Type == EOpen::Small || Type == EOpen::CellarWindow; }
};

struct FEdge
{
	FVector2D A, B, U, N;
	double L = 0, Arc = 0;
	EM80EdgeKind Kind = EM80EdgeKind::Street;
	FVec U3() const { return FVec(U.X, U.Y, 0); }
	FVec N3() const { return FVec(N.X, N.Y, 0); }
};

TArray<FVector2D> MakeCCW(TArray<FVector2D> Profile)
{
	if (M80Poly::SignedArea(Profile) < 0)
	{
		Algo::Reverse(Profile);
	}
	return Profile;
}

class FBuilder
{
public:
	FBuilder(const FM80BuildInput& InInput, FM80BuildOutput& InOutput)
		: In(InInput), Out(InOutput), M(InOutput.Mesh), R(InInput.Rules), H(InInput.Params), Rng(InInput.Params.Seed)
	{
	}

	void Run()
	{
		ChooseNobleBalcony();
		Setup();
		PlanOpenings();
		PlanStair();
		M.Ground = [this](const FVector2D& Q) { return G(Q); };
		M.CurrentUnit = In.UnitData;
		for (int32 e = 0; e < E.Num(); ++e)
		{
			EmitWall(e);
			if (!In.bUnfinished)
			{
				EmitPlinth(e);
				EmitCables(e);
			}
		}
		for (const FOpening& O : Openings)
		{
			EmitOpening(O);
		}
		if (In.bUnfinished)
		{
			EmitUnfinished();
		}
		else
		{
			EmitBands();
			EmitCorners();
			EmitCornice();
			EmitTieRods();
		}
		EmitRoof();
		EmitStair();
		EmitVotiveNiche();
		if (!In.bUnfinished)
		{
			EmitDownpipes();
			EmitVegetation();
		}
		Out.Floor0 = Floor0;
		Out.EaveZ = Top;
		Out.Openings = Openings.Num();
		Out.bStair = Stair.Edge >= 0;
	}

private:
	const FM80BuildInput& In;
	FM80BuildOutput& Out;
	FM80MeshBuffer& M;
	const FM80FacadeRules& R;
	const FM80HouseParams& H;
	FRandomStream Rng;

	TArray<FVector2D> P;
	TArray<FEdge> E;
	TArray<FOpening> Openings;
	TArray<FVector2D> AntennaSpots;

	/** Noble balconies: chosen once per house from their own stream, so the other houses do not change. */
	bool bNoble = false;
	bool bNoblePetto = false;
	EM80NobleBalcony NobleKind = EM80NobleBalcony::Volute;

	/** Outside stair: runs along edge Edge from XStart (ground) to the landing at the first-floor door. */
	struct FStair
	{
		int32 Edge = -1;
		double XStart = 0, XLanding0 = 0, XLanding1 = 0, TopZ = 0;
	} Stair;
	static constexpr double StairWidth = 95.0;
	static constexpr double StairRise = 18.0;
	static constexpr double StairRun = 29.0;
	double Floor0 = 0, Top = 0;
	int32 Floors = 1, Basements = 0, Front = 0;

	EM80RoofType Roof = EM80RoofType::Gable;
	double TanPitch = 0, CosPitch = 1;
	FVector2D RidgeDir{1, 0}, Across{0, 1};
	double SMin = 0, SMax = 0, SMid = 0, Half = 0;
	bool bShedLowAtMin = true;
	static constexpr double RoofThk = 16.0;
	static constexpr double ParapetThk = 25.0;

	// ---------------------------------------------------------------- basics

	double G(const FVector2D& Q) const { return In.Ground ? In.Ground(Q) : 0.0; }
	double GroundAt(int32 e, double X) const { return G(E[e].A + E[e].U * X); }
	bool IsFacade(int32 e) const { return E[e].Kind != EM80EdgeKind::Party; }
	bool IsStreet(int32 e) const { return E[e].Kind == EM80EdgeKind::Street; }
	EM80GroundUse UseOf(int32 e) const { return In.Uses.IsValidIndex(e) && IsFacade(e) ? In.Uses[e] : EM80GroundUse::Home; }
	int32 Next(int32 e) const { return (e + 1) % E.Num(); }
	int32 Prev(int32 e) const { return (e + E.Num() - 1) % E.Num(); }

	/** Point on the facade plane of edge e. D > 0 goes into the wall, D < 0 outside. */
	FVec W(int32 e, double X, double Z, double D = 0) const
	{
		const FEdge& Ed = E[e];
		return FVec(Ed.A.X + Ed.U.X * X - Ed.N.X * D, Ed.A.Y + Ed.U.Y * X - Ed.N.Y * D, Z);
	}

	double LevelZ(int32 K) const
	{
		if (K <= 0)
		{
			return Floor0 + K * H.FloorHeight;
		}
		return Floor0 + H.GroundFloorHeight + (K - 1) * H.FloorHeight;
	}

	double RoofLine(const FVector2D& Q) const
	{
		const double S = FVector2D::DotProduct(Q, Across);
		switch (Roof)
		{
		case EM80RoofType::Gable: return Top + TanPitch * (Half - FMath::Abs(S - SMid));
		case EM80RoofType::Shed: return Top + TanPitch * (bShedLowAtMin ? S - SMin : SMax - S);
		default: return Top;
		}
	}

	double ParapetTop() const { return Top + R.ParapetHeight; }

	double WallTop(int32 e, double X) const
	{
		if (Roof == EM80RoofType::Terrace)
		{
			return IsFacade(e) && !In.bUnfinished ? ParapetTop() : Top + 10;
		}
		return RoofLine(E[e].A + E[e].U * X);
	}

	/** X along edge e where the gable roof line has its kink, or -1. */
	double RidgeCrossing(int32 e) const
	{
		if (Roof != EM80RoofType::Gable)
		{
			return -1;
		}
		const double S0 = FVector2D::DotProduct(E[e].A, Across);
		const double DS = FVector2D::DotProduct(E[e].U, Across);
		if (FMath::Abs(DS) < 1e-4)
		{
			return -1;
		}
		const double X = (SMid - S0) / DS;
		return X > 1 && X < E[e].L - 1 ? X : -1;
	}

	FVector2f WallUV(int32 e, double X, double Z) const { return FVector2f(float((E[e].Arc + X) / 100.0), float(-Z / 100.0)); }

	// ---------------------------------------------------------------- setup

	void Setup()
	{
		P = In.Footprint;
		double Arc = 0;
		for (int32 i = 0; i < P.Num(); ++i)
		{
			FEdge Ed;
			Ed.A = P[i];
			Ed.B = P[(i + 1) % P.Num()];
			Ed.L = FVector2D::Distance(Ed.A, Ed.B);
			Ed.U = (Ed.B - Ed.A) / FMath::Max(1e-6, Ed.L);
			Ed.N = M80Poly::EdgeNormal(P, i);
			Ed.Arc = Arc;
			Ed.Kind = In.Kinds.IsValidIndex(i) ? In.Kinds[i] : EM80EdgeKind::Street;
			Arc += Ed.L;
			E.Add(Ed);
		}
		Front = FMath::Clamp(In.FrontEdge, 0, E.Num() - 1);
		Floors = FMath::Max(1, H.Floors);

		// The entrance sets the ground-floor level: one step above the street at the door.
		Floor0 = GroundAt(Front, E[Front].L * 0.5) + 12.0;
		double GMin = Floor0;
		for (int32 e = 0; e < E.Num(); ++e)
		{
			for (double X = 0; X <= E[e].L; X += 50)
			{
				GMin = FMath::Min(GMin, GroundAt(e, X));
			}
		}
		if (Floor0 - GMin > H.BasementThreshold)
		{
			Basements = FMath::Clamp(FMath::FloorToInt((Floor0 - GMin - 40.0) / H.FloorHeight), 1, 2);
		}
		Top = LevelZ(Floors);

		Roof = H.RoofType;
		const double Pitch = H.RoofPitchOverride > 0 ? H.RoofPitchOverride : R.RoofPitch;
		TanPitch = FMath::Tan(FMath::DegreesToRadians(Pitch));
		RidgeDir = H.bRidgeAlongFront ? E[Front].U : M80Poly::LongAxis(P);
		Across = FVector2D(-RidgeDir.Y, RidgeDir.X);
		SMin = TNumericLimits<double>::Max();
		SMax = -SMin;
		for (const FVector2D& Q : P)
		{
			const double S = FVector2D::DotProduct(Q, Across);
			SMin = FMath::Min(SMin, S);
			SMax = FMath::Max(SMax, S);
		}
		SMid = (SMin + SMax) * 0.5;
		Half = (SMax - SMin) * 0.5;
		const FVector2D FrontMid = (E[Front].A + E[Front].B) * 0.5;
		const double SF = FVector2D::DotProduct(FrontMid, Across);
		bShedLowAtMin = FMath::Abs(SF - SMin) <= FMath::Abs(SF - SMax);
		// Keep big blocks believable: cap the rise instead of building towers of roof.
		const double RunLen = Roof == EM80RoofType::Shed ? SMax - SMin : Half;
		const double MaxRise = Roof == EM80RoofType::Shed ? 300.0 : 420.0;
		if (RunLen * TanPitch > MaxRise)
		{
			TanPitch = MaxRise / FMath::Max(1.0, RunLen);
		}
		CosPitch = FMath::Cos(FMath::Atan(TanPitch));
	}

	TArray<double> Bays(int32 e) const
	{
		TArray<double> Centers;
		const double L = E[e].L;
		const double Usable = L - 2 * R.CornerMargin;
		if (Usable < R.WindowWidth + 30)
		{
			if (L > R.WindowWidth + 70)
			{
				Centers.Add(L * 0.5);
			}
			return Centers;
		}
		const int32 Count = FMath::Max(1, FMath::FloorToInt(Usable / R.BayWidth));
		const double Spacing = Usable / Count;
		for (int32 i = 0; i < Count; ++i)
		{
			Centers.Add(R.CornerMargin + Spacing * (i + 0.5));
		}
		return Centers;
	}

	void GroundRange(int32 e, double X0, double X1, double& Lo, double& Hi) const
	{
		Lo = TNumericLimits<double>::Max();
		Hi = -Lo;
		for (int32 i = 0; i <= 4; ++i)
		{
			const double Gz = GroundAt(e, FMath::Lerp(X0, X1, i / 4.0));
			Lo = FMath::Min(Lo, Gz);
			Hi = FMath::Max(Hi, Gz);
		}
	}

	// ---------------------------------------------------------------- facade grammar

	void PlanOpenings()
	{
		const float BalconyChance = H.BalconyChanceOverride >= 0 ? H.BalconyChanceOverride : R.BalconyChance;
		const float OpenChance = H.ShutterOpenOverride >= 0 ? H.ShutterOpenOverride : R.ShutterOpenChance;
		for (int32 e = 0; e < E.Num(); ++e)
		{
			if (!IsFacade(e) || E[e].L < 140)
			{
				continue;
			}
			const bool bStreet = IsStreet(e);
			const bool bFront = e == Front;
			const TArray<double> Centers = Bays(e);
			const int32 NB = Centers.Num();
			if (NB == 0)
			{
				continue;
			}
			const double Spacing = NB > 1 ? Centers[1] - Centers[0] : E[e].L;
			int32 DoorBay = bFront ? NB / 2 : (bStreet && NB >= 2 && Rng.FRand() < 0.3f ? Rng.RandRange(0, NB - 1) : -1);
			if (UseOf(e) != EM80GroundUse::Home && NB == 1)
			{
				DoorBay = -1; // a narrow shop house: the whole ground floor is the shop
			}
			int32 GarageBay = -1;
			if (bFront && NB >= 2 && Spacing >= 270 && Rng.FRand() < R.GarageChance)
			{
				GarageBay = DoorBay == 0 ? NB - 1 : 0;
			}
			const bool bArchDoor = Rng.FRand() < R.ArchedDoorChance;

			// Decisions per vertical column keep the facade orderly, as in the real town.
			TArray<bool> Active, BalconyColumn;
			TArray<EShutter> ColumnShutter;
			for (int32 i = 0; i < NB; ++i)
			{
				Active.Add(In.bUnfinished ? Rng.FRand() < 0.7f : bStreet || i == DoorBay || UseOf(e) != EM80GroundUse::Home || Rng.FRand() < 0.55f);
				BalconyColumn.Add(bStreet && Floors >= 2 && Rng.FRand() < BalconyChance);
				EShutter S = EShutter::None;
				const float Roll = Rng.FRand();
				if (Roll < R.RollerShutterChance)
				{
					S = EShutter::Roller;
				}
				else if (Rng.FRand() < R.ShutterChance)
				{
					S = Rng.FRand() < OpenChance ? EShutter::Open : EShutter::Closed;
				}
				ColumnShutter.Add(S);
			}

			for (int32 K = -Basements; K < Floors; ++K)
			{
				const double Z = LevelZ(K);
				const double ZNext = LevelZ(K + 1);
				const double MaxTop = K == Floors - 1
					? Top - (Roof == EM80RoofType::Terrace ? 30.0 : R.CorniceHeight + 22.0)
					: ZNext - 32.0;
				for (int32 i = 0; i < NB; ++i)
				{
					if (!Active[i])
					{
						continue;
					}
					FOpening O;
					O.Edge = e;
					O.Level = K;
					O.Rand = Rng.FRand();
					O.bFramed = bStreet || Rng.FRand() < 0.4f;
					double Wd = R.WindowWidth, Z0 = Z, Ht = R.WindowHeight;
					if (K < 0)
					{
						const double Gz = GroundAt(e, Centers[i]);
						if (FMath::Abs(Gz - Z) < 40 && Rng.FRand() < 0.6f)
						{
							O.Type = EOpen::CellarDoor; Wd = 105; Z0 = FMath::Max(Z, Gz); Ht = 205;
						}
						else
						{
							O.Type = EOpen::CellarWindow; Wd = 65; Ht = 50; Z0 = ZNext - 105;
						}
						O.bFramed = false;
					}
					else if (K == 0)
					{
						if (i == DoorBay)
						{
							O.Type = EOpen::Door; Wd = R.DoorWidth; Ht = R.DoorHeight; O.bArch = bArchDoor && bFront;
							O.bPointed = O.bArch && Rng.FRand() < R.PointedArchChance;
							if (O.bPointed)
							{
								Ht += 25; // the pointed arch needs a taller opening
							}
						}
						else if (UseOf(e) != EM80GroundUse::Home)
						{
							O.Type = EOpen::Shop; Wd = FMath::Clamp(Spacing - 60, 150.0, 300.0); Ht = FMath::Min(H.GroundFloorHeight - 75.0, 270.0);
							O.bFramed = true;
						}
						else if (i == GarageBay)
						{
							O.Type = EOpen::Garage; Wd = FMath::Min(Spacing - 50, 250.0); Ht = 235;
						}
						else
						{
							O.Type = EOpen::Window; Z0 = Z + R.GroundWindowSill; Ht = R.WindowHeight * 0.85;
							O.bGrille = Rng.FRand() < R.GroundGrilleChance;
							O.Shutter = O.bGrille ? EShutter::None : ColumnShutter[i];
						}
					}
					else if (BalconyColumn[i] && !(R.bSmallTopWindows && K == Floors - 1 && Floors >= 3))
					{
						O.Type = EOpen::French; Ht = R.FrenchWindowHeight; O.bBalcony = true; O.Shutter = ColumnShutter[i];
					}
					else if (R.bSmallTopWindows && K == Floors - 1 && Floors >= 3)
					{
						O.Type = EOpen::Small; Wd = 62; Ht = 62; Z0 = Z + 70;
					}
					else
					{
						O.Type = EOpen::Window; Z0 = Z + R.WindowSill; O.Shutter = ColumnShutter[i];
						if (FMath::Frac(O.Rand * 9.13f) < R.BiforaChance && !In.bUnfinished)
						{
							// Arched bifora: wider, with a small central column, no shutters.
							O.bArch = true;
							O.bPointed = FMath::Frac(O.Rand * 3.71f) < 0.5f;
							O.bBifora = true;
							O.Shutter = EShutter::None;
							Wd *= 1.3;
							Ht += 30;
						}
					}
					O.X0 = Centers[i] - Wd * 0.5;
					O.X1 = Centers[i] + Wd * 0.5;
					O.Z0 = Z0;
					O.Z1 = FMath::Min(Z0 + Ht, O.IsDoorLike() ? ZNext - 30.0 : MaxTop);
					if (O.Type == EOpen::Door && !O.bArch && Rng.FRand() < 0.5f)
					{
						O.Z1 = FMath::Min(O.Z1, Z0 + Ht - 10);
					}
					if (O.Z1 - O.Z0 < 45)
					{
						continue;
					}
					// Terrain: windows must clear the ground, doors must meet it.
					double Lo, Hi;
					GroundRange(e, O.X0 - 10, O.X1 + 10, Lo, Hi);
					if (O.IsDoorLike())
					{
						if (Hi > O.Z0 + 8 || O.Z0 - Lo > 80)
						{
							if (O.Type == EOpen::Door && bFront)
							{
								// Keep the main entrance: the level was derived from it.
							}
							else
							{
								continue;
							}
						}
					}
					else if (O.Z0 < Hi + 35)
					{
						continue;
					}
					if (O.bBalcony && O.Z0 < Hi + 250)
					{
						O.bBalcony = false; // too close to the ground on the uphill side
					}
					Openings.Add(O);
				}
			}
		}
	}

	// ---------------------------------------------------------------- outside stair

	void PlanStair()
	{
		if (In.bUnfinished || Floors < 2 || Basements > 0 || Rng.FRand() >= H.ExternalStairChance)
		{
			return;
		}
		// Back walls first, then street walls; the first edge with room for the flight wins.
		TArray<int32> Order;
		for (int32 e = 0; e < E.Num(); ++e)
		{
			if (IsFacade(e) && UseOf(e) == EM80GroundUse::Home && e != Front)
			{
				IsStreet(e) ? Order.Add(e) : Order.Insert(e, 0);
			}
		}
		if (UseOf(Front) == EM80GroundUse::Home)
		{
			Order.Add(Front); // last resort: stairs on the main facade are common in the old quarters
		}
		const double TopZ = LevelZ(1);
		for (int32 e : Order)
		{
			for (FOpening& O : Openings)
			{
				if (O.Edge != e || O.Level != 1)
				{
					continue;
				}
				const int32 Steps = FMath::CeilToInt((TopZ - GroundAt(e, O.Mid())) / StairRise);
				const double Len = Steps * StairRun;
				const double L0 = O.X0 - 15, L1 = O.X1 + 15;
				double XStart = -1;
				if (L0 - Len >= 15)
				{
					XStart = L0 - Len;
				}
				else if (L1 + Len <= E[e].L - 15)
				{
					XStart = L1 + Len;
				}
				if (XStart < 0 || Steps < 4)
				{
					continue;
				}
				Stair.Edge = e;
				Stair.XStart = XStart;
				Stair.XLanding0 = L0;
				Stair.XLanding1 = L1;
				Stair.TopZ = TopZ;
				// The window becomes a door onto the landing.
				O.Type = EOpen::French;
				O.bBalcony = false;
				O.bGrille = false;
				O.Z0 = TopZ;
				O.Z1 = FMath::Min(TopZ + R.FrenchWindowHeight, LevelZ(2) - 32.0);
				const double S0 = FMath::Min(XStart, L0), S1 = FMath::Max(XStart, L1);
				Openings.RemoveAll([&](const FOpening& G) { return G.Edge == e && G.Level <= 0 && G.X1 > S0 - 10 && G.X0 < S1 + 10; });
				return;
			}
		}
	}

	void EmitVotiveNiche()
	{
		const double Sc = Sicily();
		if (Sc <= 0 || In.CatCount[M80Cat::Wall] <= 0 || Rng.FRand() > 0.3 * Sc || !IsStreet(Front) || E[Front].L < 260)
		{
			return;
		}
		const int32 e = Front;
		const double X = Rng.FRand() < 0.5f ? 70.0 : E[e].L - 70;
		const double Z = Floor0 + FMath::Min(H.GroundFloorHeight - 70.0, 250.0);
		if (ClearOfOpenings(e, X - 45, X + 45, Z - 10, Z + 110))
		{
			AddCat(M80Cat::Wall, W(e, X, Z, -0.5), WallYaw(e));
		}
	}

	void EmitStair()
	{
		if (Stair.Edge < 0)
		{
			return;
		}
		const int32 e = Stair.Edge;
		const FVec U3 = E[e].U3(), N3 = E[e].N3();
		const double Dir = Stair.XStart < Stair.XLanding0 ? 1.0 : -1.0;
		const double XTop = Dir > 0 ? Stair.XLanding0 : Stair.XLanding1;
		const int32 Steps = FMath::Max(1, FMath::RoundToInt(FMath::Abs(XTop - Stair.XStart) / StairRun));
		const double Run = FMath::Abs(XTop - Stair.XStart) / Steps;
		M.FacadeMask = 1.f;
		TArray<FVec> Rail;
		for (int32 s = 0; s < Steps; ++s)
		{
			const double X = Stair.XStart + Dir * Run * (s + 0.5);
			const double Gz = GroundAt(e, X) - 10;
			const double TopS = FMath::Lerp(GroundAt(e, Stair.XStart), Stair.TopZ, double(s + 1) / Steps);
			if (TopS <= Gz + 2)
			{
				continue;
			}
			// Solid masonry under every tread, stone tread on top.
			M.WallBox(In.WallSlot, W(e, X, (Gz + TopS - 4) * 0.5, -StairWidth * 0.5), U3, N3, FVec(Run * 0.5, StairWidth * 0.5, (TopS - 4 - Gz) * 0.5), true);
			M.WallBox(M80Slot::Trim, W(e, X - Dir * 1.5, TopS - 2, -StairWidth * 0.5 - 1.5), U3, N3, FVec(Run * 0.5 + 1.5, StairWidth * 0.5 + 1.5, 2.5), true);
			if (s % 3 == 0)
			{
				Rail.Add(W(e, X, TopS + 92, -StairWidth + 4));
				M.Tube(M80Slot::Iron, {W(e, X, TopS, -StairWidth + 4), W(e, X, TopS + 92, -StairWidth + 4)}, 1.2, 4);
			}
		}
		// Landing in front of the door.
		const double Lx0 = Stair.XLanding0, Lx1 = Stair.XLanding1, Lm = (Lx0 + Lx1) * 0.5;
		double Lo, Hi;
		GroundRange(e, Lx0, Lx1, Lo, Hi);
		M.WallBox(In.WallSlot, W(e, Lm, (Lo - 10 + Stair.TopZ - 4) * 0.5, -StairWidth * 0.5), U3, N3, FVec((Lx1 - Lx0) * 0.5, StairWidth * 0.5, (Stair.TopZ - 4 - Lo + 10) * 0.5), true);
		M.WallBox(M80Slot::Trim, W(e, Lm, Stair.TopZ - 2, -StairWidth * 0.5 - 1.5), U3, N3, FVec((Lx1 - Lx0) * 0.5 + 2, StairWidth * 0.5 + 1.5, 2.5), true);
		const double Far = Dir > 0 ? Lx1 : Lx0;
		Rail.Add(W(e, XTop, Stair.TopZ + 92, -StairWidth + 4));
		Rail.Add(W(e, Far, Stair.TopZ + 92, -StairWidth + 4));
		M.Tube(M80Slot::Iron, {W(e, Far, Stair.TopZ, -StairWidth + 4), W(e, Far, Stair.TopZ + 92, -StairWidth + 4)}, 1.2, 4);
		M.Tube(M80Slot::Iron, {W(e, Far, Stair.TopZ + 92, -StairWidth + 4), W(e, Far, Stair.TopZ + 92, -2)}, 1.2, 4);
		if (Rail.Num() >= 2)
		{
			M.Tube(M80Slot::Iron, Rail, 1.6, 5);
		}
		M.FacadeMask = 0.f;
		// Pots on the steps.
		if (In.NumProps > 0)
		{
			for (int32 k = 0; k < 2; ++k)
			{
				const int32 s = Rng.RandRange(1, Steps - 1);
				const double X = Stair.XStart + Dir * Run * (s + 0.5);
				const double TopS = FMath::Lerp(GroundAt(e, Stair.XStart), Stair.TopZ, double(s + 1) / Steps);
				FM80PropPlacement Prop;
				Prop.Prop = Rng.RandRange(0, In.NumProps - 1);
				Prop.Transform = FTransform(FRotator(0, Rng.FRandRange(0, 360), 0), W(e, X, TopS, -15));
				Out.Props.Add(Prop);
			}
		}
	}

	// ---------------------------------------------------------------- walls

	void EmitWall(int32 e)
	{
		const FEdge& Ed = E[e];
		const int32 Slot = IsFacade(e) ? In.WallSlot : M80Slot::RawWall;
		M.FacadeMask = IsFacade(e) ? 1.f : 0.f;
		M.ElementRandom = 0.f;

		TArray<const FOpening*> Holes;
		TArray<double> Cuts = {0.0, Ed.L};
		for (double X = 100; X < Ed.L; X += 100)
		{
			Cuts.Add(X);
		}
		if (const double K = RidgeCrossing(e); K > 0)
		{
			Cuts.Add(K);
		}
		for (const FOpening& O : Openings)
		{
			if (O.Edge != e)
			{
				continue;
			}
			Holes.Add(&O);
			Cuts.Add(O.X0);
			Cuts.Add(O.X1);
			if (O.bArch)
			{
				for (int32 s = 1; s < 12; ++s)
				{
					Cuts.Add(FMath::Lerp(O.X0, O.X1, s / 12.0));
				}
			}
		}
		Cuts.Sort();
		const FVec Facing = Ed.N3();
		auto Emit = [&](double Xa, double Xb, double Za0, double Zb0, double Za1, double Zb1)
		{
			if (Za1 - Za0 < 0.5 && Zb1 - Zb0 < 0.5)
			{
				return;
			}
			M.Quad(Slot, W(e, Xa, Za0), W(e, Xb, Zb0), W(e, Xb, Zb1), W(e, Xa, Za1),
				WallUV(e, Xa, Za0), WallUV(e, Xb, Zb0), WallUV(e, Xb, Zb1), WallUV(e, Xa, Za1), Facing);
		};
		for (int32 c = 0; c + 1 < Cuts.Num(); ++c)
		{
			const double Xa = Cuts[c], Xb = Cuts[c + 1];
			if (Xb - Xa < 0.5)
			{
				continue;
			}
			const double Xm = (Xa + Xb) * 0.5;
			double Ca = GroundAt(e, Xa) - 40.0, Cb = GroundAt(e, Xb) - 40.0;
			TArray<const FOpening*> Column;
			for (const FOpening* O : Holes)
			{
				if (O->X0 < Xm && Xm < O->X1)
				{
					Column.Add(O);
				}
			}
			Column.Sort([](const FOpening& A, const FOpening& B) { return A.Z0 < B.Z0; });
			for (const FOpening* O : Column)
			{
				Emit(Xa, Xb, Ca, Cb, O->Z0, O->Z0);
				Ca = O->TopAt(Xa);
				Cb = O->TopAt(Xb);
			}
			Emit(Xa, Xb, Ca, Cb, WallTop(e, Xa), WallTop(e, Xb));
		}
		M.FacadeMask = 0.f;
	}

	void EmitPlinth(int32 e)
	{
		if (!IsFacade(e) || R.PlinthHeight <= 1)
		{
			return;
		}
		const FEdge& Ed = E[e];
		const double Proj = 3.0;
		TArray<FVector2D> Skip;
		TArray<double> Cuts = {0.0, Ed.L};
		for (double X = 100; X < Ed.L; X += 100)
		{
			Cuts.Add(X);
		}
		for (const FOpening& O : Openings)
		{
			if (O.Edge == e && O.IsDoorLike())
			{
				const double Pad = O.bFramed ? R.FrameWidth : 2.0;
				Skip.Add(FVector2D(O.X0 - Pad, O.X1 + Pad));
				Cuts.Add(O.X0 - Pad);
				Cuts.Add(O.X1 + Pad);
			}
		}
		Cuts.Sort();
		const FVec N3 = Ed.N3(), U3 = Ed.U3();
		for (int32 c = 0; c + 1 < Cuts.Num(); ++c)
		{
			const double Xa = FMath::Max(0.0, Cuts[c]), Xb = FMath::Min(Ed.L, Cuts[c + 1]);
			if (Xb - Xa < 0.5)
			{
				continue;
			}
			const double Xm = (Xa + Xb) * 0.5;
			bool bSkip = false;
			for (const FVector2D& S : Skip)
			{
				bSkip |= Xm > S.X && Xm < S.Y;
			}
			if (bSkip)
			{
				continue;
			}
			const double Ga = GroundAt(e, Xa), Gb = GroundAt(e, Xb);
			const double Ta = Ga + R.PlinthHeight, Tb = Gb + R.PlinthHeight;
			M.QuadProjected(M80Slot::Trim, W(e, Xa, Ga - 40, -Proj), W(e, Xb, Gb - 40, -Proj), W(e, Xb, Tb, -Proj), W(e, Xa, Ta, -Proj), N3);
			M.QuadProjected(M80Slot::Trim, W(e, Xa, Ta, -Proj), W(e, Xb, Tb, -Proj), W(e, Xb, Tb, 0), W(e, Xa, Ta, 0), Up);
			auto IsBoundary = [&](double X)
			{
				for (const FVector2D& S : Skip)
				{
					if (FMath::Abs(X - S.X) < 0.6 || FMath::Abs(X - S.Y) < 0.6)
					{
						return true;
					}
				}
				return false;
			};
			if (IsBoundary(Xa))
			{
				M.QuadProjected(M80Slot::Trim, W(e, Xa, Ga - 40, 0), W(e, Xa, Ga - 40, -Proj), W(e, Xa, Ta, -Proj), W(e, Xa, Ta, 0), -U3);
			}
			if (IsBoundary(Xb))
			{
				M.QuadProjected(M80Slot::Trim, W(e, Xb, Gb - 40, -Proj), W(e, Xb, Gb - 40, 0), W(e, Xb, Tb, 0), W(e, Xb, Tb, -Proj), U3);
			}
		}
	}

	// ---------------------------------------------------------------- openings

	void EmitOpening(const FOpening& O)
	{
		const int32 e = O.Edge;
		const FEdge& Ed = E[e];
		const FVec U3 = Ed.U3(), N3 = Ed.N3();
		const double D = R.RevealDepth;
		const int32 RevealSlot = O.bFramed ? M80Slot::Trim : In.WallSlot;
		M.ElementRandom = O.Rand;

		// Reveals (mazzette): the wall thickness seen inside the opening.
		const double TopL = O.TopAt(O.X0), TopR = O.TopAt(O.X1);
		M.QuadProjected(RevealSlot, W(e, O.X0, O.Z0, 0), W(e, O.X0, O.Z0, D), W(e, O.X0, TopL, D), W(e, O.X0, TopL, 0), U3);
		M.QuadProjected(RevealSlot, W(e, O.X1, O.Z0, D), W(e, O.X1, O.Z0, 0), W(e, O.X1, TopR, 0), W(e, O.X1, TopR, D), -U3);
		M.QuadProjected(RevealSlot, W(e, O.X0, O.Z0, 0), W(e, O.X1, O.Z0, 0), W(e, O.X1, O.Z0, D), W(e, O.X0, O.Z0, D), Up);
		if (O.bArch)
		{
			const int32 Steps = 12;
			for (int32 s = 0; s < Steps; ++s)
			{
				const double Xa = FMath::Lerp(O.X0, O.X1, double(s) / Steps), Xb = FMath::Lerp(O.X0, O.X1, double(s + 1) / Steps);
				const double Za = O.TopAt(Xa), Zb = O.TopAt(Xb);
				const double Xm = (Xa + Xb) * 0.5, Zm = (Za + Zb) * 0.5;
				const FVec Facing = (U3 * (O.Mid() - Xm) + Up * (O.Spring() - Zm)).GetSafeNormal();
				M.QuadProjected(RevealSlot, W(e, Xa, Za, 0), W(e, Xb, Zb, 0), W(e, Xb, Zb, D), W(e, Xa, Za, D), Facing);
			}
		}
		else
		{
			M.QuadProjected(RevealSlot, W(e, O.X0, O.Z1, D), W(e, O.X1, O.Z1, D), W(e, O.X1, O.Z1, 0), W(e, O.X0, O.Z1, 0), -Up);
		}

		if (In.bUnfinished)
		{
			// Empty hole: a bare brick tunnel to the inner wall seen through it, a lintel on top.
			const double In0 = D, In1 = D + 90;
			M.QuadProjected(M80Slot::Brick, W(e, O.X0, O.Z0, In0), W(e, O.X0, O.Z0, In1), W(e, O.X0, O.Z1, In1), W(e, O.X0, O.Z1, In0), U3);
			M.QuadProjected(M80Slot::Brick, W(e, O.X1, O.Z0, In1), W(e, O.X1, O.Z0, In0), W(e, O.X1, O.Z1, In0), W(e, O.X1, O.Z1, In1), -U3);
			M.QuadProjected(M80Slot::Brick, W(e, O.X0, O.Z1, In1), W(e, O.X1, O.Z1, In1), W(e, O.X1, O.Z1, In0), W(e, O.X0, O.Z1, In0), -Up);
			M.QuadProjected(M80Slot::Terrace, W(e, O.X0, O.Z0, In0), W(e, O.X1, O.Z0, In0), W(e, O.X1, O.Z0, In1), W(e, O.X0, O.Z0, In1), Up);
			M.WallBox(M80Slot::Brick, W(e, O.Mid(), (O.Z0 + O.Z1) * 0.5, In1), U3, N3, FVec(O.Width() * 0.5 + 10, 2, (O.Z1 - O.Z0) * 0.5 + 10), false);
			M.WallBox(M80Slot::Terrace, W(e, O.Mid(), O.Z1 + 10, 1), U3, N3, FVec(O.Width() * 0.5 + 15, 1, 10), false);
			M.ElementRandom = 0.f;
			return;
		}
		EmitFrame(O);
		if (In.bAbandoned && O.Type != EOpen::Shop && O.Type != EOpen::Garage && EmitDerelict(O))
		{
			M.ElementRandom = 0.f;
			return;
		}
		switch (O.Type)
		{
		case EOpen::Door: EmitDoor(O); break;
		case EOpen::Garage: EmitGarage(O); break;
		case EOpen::Shop: EmitShop(O); break;
		case EOpen::CellarDoor: EmitPlankDoor(O); break;
		default: EmitWindow(O); break;
		}
		if (O.IsDoorLike())
		{
			EmitSteps(O);
		}
		if (O.Type == EOpen::Door && O.Level == 0 && !In.bAbandoned)
		{
			EmitSicilyDoor(O);
		}
		if (O.bBalcony)
		{
			EmitBalcony(O);
			++Out.Balconies;
		}
		if ((O.Type == EOpen::French || O.Type == EOpen::Door) && !In.bAbandoned && FMath::Frac(O.Rand * 7.31f) < H.SlatBlindChance)
		{
			EmitSlatBlind(O);
		}
		if (O.Type == EOpen::Window && O.Level >= 1 && !O.bBalcony && IsStreet(O.Edge) && FMath::Frac(O.Rand * 17.3f) < 0.18 * Sicily())
		{
			EmitLaundryRack(O);
		}
		M.ElementRandom = 0.f;
	}

	/** Wall drying rack under a window: two iron T brackets, three lines and the washing hung out. */
	void EmitLaundryRack(const FOpening& O)
	{
		const int32 e = O.Edge;
		const FVec U3 = E[e].U3(), N3 = E[e].N3();
		const double Z = O.Z0 - 12, Reach = 70;
		const double Xa = O.X0 - 25, Xb = O.X1 + 25;
		if (Xa < 10 || Xb > E[e].L - 10 || Z < GroundAt(e, O.Mid()) + 250)
		{
			return;
		}
		M.ElementRandom = Rng.FRand();
		for (double X : {Xa, Xb})
		{
			M.Tube(M80Slot::Iron, {W(e, X, Z, 0), W(e, X, Z, -Reach)}, 1.2, 4);
			M.Tube(M80Slot::Iron, {W(e, X, Z - 25, 0), W(e, X, Z, -Reach * 0.6)}, 0.9, 4);
		}
		for (double D : {-Reach * 0.33, -Reach * 0.66, -Reach + 3})
		{
			M.Tube(M80Slot::Iron, {W(e, Xa, Z + 1, D), W(e, (Xa + Xb) * 0.5, Z - 2.5, D), W(e, Xb, Z + 1, D)}, 0.35, 3);
		}
		M.ElementRandom = 0;
		AddCat(M80Cat::Laundry, W(e, (Xa + Xb) * 0.5, Z - 2, -Reach * 0.66), WallYaw(e));
	}

	/** Abandoned house openings: boarded, bricked up or broken. Returns false to keep the normal opening. */
	bool EmitDerelict(const FOpening& O)
	{
		const int32 e = O.Edge;
		const FVec U3 = E[e].U3(), N3 = E[e].N3();
		const double Wd = O.Width(), Mid = O.Mid(), Zm = (O.Z0 + O.Z1) * 0.5, Ht = O.Z1 - O.Z0, D = R.RevealDepth;
		const float Roll = FMath::Frac(O.Rand * 3.7f);
		if (Roll < 0.3f)
		{
			// Bricked up, set back in the reveal.
			M.WallBox(M80Slot::Brick, W(e, Mid, Zm, 6), U3, N3, FVec(Wd * 0.5, 6, Ht * 0.5), false);
			return true;
		}
		if (Roll < 0.6f)
		{
			// Planks nailed across, a dark void behind.
			M.WallBox(M80Slot::Iron, W(e, Mid, Zm, D - 2), U3, N3, FVec(Wd * 0.5, 1, Ht * 0.5), false);
			FRandomStream Pr(int32(O.Rand * 100000));
			for (double Z = O.Z0 + 12; Z < O.Z1 - 6; Z += Pr.FRandRange(18.f, 30.f))
			{
				const double Ang = FMath::DegreesToRadians(Pr.FRandRange(-9.f, 9.f));
				const FVec Ax = (U3 * FMath::Cos(Ang) + Up * FMath::Sin(Ang)).GetSafeNormal();
				const FVec Az = (Up * FMath::Cos(Ang) - U3 * FMath::Sin(Ang)).GetSafeNormal();
				M.ElementRandom = Pr.FRand();
				M.Box(M80Slot::Wood, W(e, Mid, Z, -2.5), Ax, N3, Az, FVec(Wd * 0.5 + 10, 1.4, 7.5));
			}
			return true;
		}
		if (Roll < 0.8f && O.HasGlass())
		{
			// Broken glass: the room behind dark, a cross bar and two shards left in the frame.
			// The empty room behind: a dark brick tunnel and back wall (no reflecting glass).
			const double In0 = D, In1 = D + 120;
			M.QuadProjected(M80Slot::Brick, W(e, O.X0, O.Z0, In0), W(e, O.X0, O.Z0, In1), W(e, O.X0, O.Z1, In1), W(e, O.X0, O.Z1, In0), U3);
			M.QuadProjected(M80Slot::Brick, W(e, O.X1, O.Z0, In1), W(e, O.X1, O.Z0, In0), W(e, O.X1, O.Z1, In0), W(e, O.X1, O.Z1, In1), -U3);
			M.QuadProjected(M80Slot::Brick, W(e, O.X0, O.Z1, In1), W(e, O.X1, O.Z1, In1), W(e, O.X1, O.Z1, In0), W(e, O.X0, O.Z1, In0), -Up);
			M.QuadProjected(M80Slot::Terrace, W(e, O.X0, O.Z0, In0), W(e, O.X1, O.Z0, In0), W(e, O.X1, O.Z0, In1), W(e, O.X0, O.Z0, In1), Up);
			M.WallBox(M80Slot::Brick, W(e, Mid, Zm, In1), U3, N3, FVec(Wd * 0.5 + 10, 2, Ht * 0.5 + 10), false);
			M.WallBox(M80Slot::Wood, W(e, Mid, Zm, D - 4), U3, N3, FVec(2.5, 3.5, Ht * 0.5), false);
			M.WallBox(M80Slot::Wood, W(e, Mid, Zm, D - 4), U3, N3, FVec(Wd * 0.5, 3.5, 2.5), false);
			const float Keep = M.ElementRandom;
			M.ElementRandom = 0.f;
			M.Tri(M80Slot::Glass, W(e, O.X0 + 4, O.Z0 + 4, D - 3), W(e, O.X0 + Wd * 0.4, O.Z0 + 4, D - 3), W(e, O.X0 + 4, O.Z0 + Ht * 0.45, D - 3),
				{0.f, 1.f}, {0.4f, 1.f}, {0.f, 0.55f}, N3);
			M.Tri(M80Slot::Glass, W(e, O.X1 - 4, O.Z1 - 4, D - 3), W(e, O.X1 - Wd * 0.3, O.Z1 - 4, D - 3), W(e, O.X1 - 4, O.Z1 - Ht * 0.3, D - 3),
				{1.f, 0.f}, {0.7f, 0.f}, {1.f, 0.3f}, N3);
			M.ElementRandom = Keep;
			return true;
		}
		return false;
	}

	/**
	 * Wooden slat blind (tenda a listarelle) hung outside a door or French window: down to the floor
	 * or rolled up part way, with the roll and the cords.
	 */
	void EmitSlatBlind(const FOpening& O)
	{
		const int32 e = O.Edge;
		const FVec U3 = E[e].U3(), N3 = E[e].N3();
		const double HalfW = O.Width() * 0.5 + 6, Mid = O.Mid();
		const double TopZ = O.Z1 + 6;
		const float Roll = FMath::Frac(O.Rand * 13.7f);
		const double Bottom = Roll < 0.45f ? O.Z0 + 2 : FMath::Lerp(O.Z0 + 2, O.Z1, 0.25 + 0.6 * Roll);
		const double Outside = -(R.FrameProjection + 5);
		const bool bRolled = Bottom > O.Z0 + 5;
		M.ElementRandom = FMath::Frac(O.Rand * 5.3f);
		M.WallBox(M80Slot::Wood, W(e, Mid, TopZ + 2, -2), U3, N3, FVec(HalfW + 4, 3, 2), false);
		for (double Z = TopZ - 3; Z > Bottom + 2; Z -= 4.2)
		{
			M.Box(M80Slot::Wood, W(e, Mid, Z, Outside), U3, N3, Up, FVec(HalfW, 0.6, 1.8));
		}
		if (bRolled)
		{
			// Rolled part at the bottom, held by the cords.
			M.Tube(M80Slot::Wood, {W(e, Mid - HalfW, Bottom, Outside - 5), W(e, Mid + HalfW, Bottom, Outside - 5)}, 6.5, 8, true);
		}
		for (double S : {-0.7, 0.7})
		{
			M.Tube(M80Slot::Iron, {W(e, Mid + HalfW * S, TopZ, Outside - 1.5), W(e, Mid + HalfW * S, Bottom - 7, Outside - (bRolled ? 13.5 : 1.5))}, 0.35, 3);
		}
	}

	void EmitFrame(const FOpening& O)
	{
		if (!O.bFramed || O.Type == EOpen::CellarWindow)
		{
			return;
		}
		const int32 e = O.Edge;
		const FVec U3 = E[e].U3(), N3 = E[e].N3();
		const double FW = R.FrameWidth, FP = R.FrameProjection;
		auto Block = [&](double X0, double X1, double Z0, double Z1, double Proj)
		{
			M.WallBox(M80Slot::Trim, W(e, (X0 + X1) * 0.5, (Z0 + Z1) * 0.5, -Proj * 0.5), U3, N3,
				FVec((X1 - X0) * 0.5, Proj * 0.5, (Z1 - Z0) * 0.5));
		};
		if (O.Type == EOpen::Garage)
		{
			Block(O.X0 - 12, O.X1 + 12, O.Z1, O.Z1 + 22, FP);
			return;
		}
		const double JambTop = O.bArch ? O.Spring() : O.Z1;
		const double JambBottom = O.IsDoorLike() ? O.Z0 : O.Z0 - 2;
		Block(O.X0 - FW, O.X0, JambBottom, JambTop + (O.bArch ? 0 : FW), FP);
		Block(O.X1, O.X1 + FW, JambBottom, JambTop + (O.bArch ? 0 : FW), FP);
		if (O.bArch)
		{
			// Archivolt of voussoirs with a keystone.
			const double Radius = O.Width() * 0.5 + FW * 0.5;
			const int32 Segments = 9;
			for (int32 s = 0; s < Segments; ++s)
			{
				const double A0 = PI * s / Segments, A1 = PI * (s + 1) / Segments, Am = (A0 + A1) * 0.5;
				const FVec Radial = U3 * -FMath::Cos(Am) + Up * FMath::Sin(Am);
				const FVec Tangent = FVec::CrossProduct(N3, Radial).GetSafeNormal();
				const FVec Center = W(e, O.Mid(), O.Spring(), -FP * 0.5) + Radial * Radius;
				const double Len = Radius * (A1 - A0);
				const bool bKey = s == Segments / 2;
				M.ElementRandom = Rng.FRand();
				M.Box(M80Slot::Trim, Center + (bKey ? Radial * 4.0 - N3 * 1.5 : FVec::ZeroVector), Tangent, N3, Radial,
					FVec(Len * 0.5 - 0.6, FP * 0.5 + (bKey ? 1.5 : 0), FW * 0.5 + (bKey ? 6 : 0)));
			}
			M.ElementRandom = O.Rand;
		}
		else
		{
			Block(O.X0 - FW, O.X1 + FW, O.Z1, O.Z1 + FW * 1.3, FP + 1);
			if (R.bOrnateCorbels)
			{
				Block(O.X0 - FW - 7, O.X1 + FW + 7, O.Z1 + FW * 1.3, O.Z1 + FW * 1.3 + 7, FP + 6);
			}
		}
		if (!O.IsDoorLike() && O.Type != EOpen::French)
		{
			Block(O.X0 - FW - 4, O.X1 + FW + 4, O.Z0 - 8, O.Z0, 8);
		}
	}

	void EmitLeaf(int32 e, double XCenter, double ZCenter, double Depth, double Width, double Height, const FVec& LeafOut, double Swing = 0)
	{
		// Louvered persiana: stiles, rails and tilted slats. Swing (degrees) tilts a leaf hanging from one hinge.
		const double Sw = FMath::DegreesToRadians(Swing);
		const FVec LeafUp = (Up * FMath::Cos(Sw) + E[e].U3() * FMath::Sin(Sw)).GetSafeNormal();
		const FVec U3 = (E[e].U3() * FMath::Cos(Sw) - Up * FMath::Sin(Sw)).GetSafeNormal();
		const FVec C = W(e, XCenter, ZCenter, Depth);
		const double T = 1.6;
		M.Box(M80Slot::Wood, C - U3 * (Width * 0.5 - 2.5), U3, LeafOut, LeafUp, FVec(2.5, T, Height * 0.5));
		M.Box(M80Slot::Wood, C + U3 * (Width * 0.5 - 2.5), U3, LeafOut, LeafUp, FVec(2.5, T, Height * 0.5));
		M.Box(M80Slot::Wood, C + LeafUp * (Height * 0.5 - 3), U3, LeafOut, LeafUp, FVec(Width * 0.5 - 5, T, 3));
		M.Box(M80Slot::Wood, C - LeafUp * (Height * 0.5 - 4), U3, LeafOut, LeafUp, FVec(Width * 0.5 - 5, T, 4));
		const double Tilt = FMath::DegreesToRadians(35.0);
		const FVec SlatY = LeafOut * FMath::Cos(Tilt) + LeafUp * FMath::Sin(Tilt);
		const FVec SlatZ = LeafUp * FMath::Cos(Tilt) - LeafOut * FMath::Sin(Tilt);
		for (double Z = -Height * 0.5 + 10; Z < Height * 0.5 - 7; Z += 6.5)
		{
			M.Box(M80Slot::Wood, C + LeafUp * Z, U3, SlatY, SlatZ, FVec(Width * 0.5 - 5, 0.5, 3.0));
		}
	}

	/**
	 * Glass pane for the parallax interiors. UV0 is the position on the front wall of the room
	 * behind it (0-1 across RoomW centred on the opening, 0 at the ceiling, 1 at the floor), so the
	 * window shows part of a full-size room. The room type goes in vertex colour B:
	 * homes 0-0.69, shops 0.7-0.89, bars 0.9-1 (see M_M80_GlassInterior).
	 */
	void Pane(int32 e, double X0, double X1, double Z0, double Z1, double Depth, float Room, double FloorZ, double RoomH, double RoomW = 360.0)
	{
		const float Saved = M.ElementRandom;
		M.ElementRandom = Room;
		const double Left = (X0 + X1) * 0.5 - RoomW * 0.5;
		auto UV = [&](double X, double Z) { return FVector2f(float((X - Left) / RoomW), float((FloorZ + RoomH - Z) / RoomH)); };
		M.Quad(M80Slot::Glass, W(e, X0, Z0, Depth), W(e, X1, Z0, Depth), W(e, X1, Z1, Depth), W(e, X0, Z1, Depth),
			UV(X0, Z0), UV(X1, Z0), UV(X1, Z1), UV(X0, Z1), E[e].N3());
		M.ElementRandom = Saved;
	}

	void EmitWindow(const FOpening& O)
	{
		const int32 e = O.Edge;
		const FVec U3 = E[e].U3(), N3 = E[e].N3();
		const double D = R.RevealDepth;
		const double W0 = O.X0, W1 = O.X1, Z0 = O.Z0, Z1 = O.Z1, Wd = O.Width(), Ht = Z1 - Z0;
		const double Xm = O.Mid(), Zm = (Z0 + Z1) * 0.5;
		const double FD = D - 4; // frame depth centre
		auto Bar = [&](double X, double Z, double HX, double HZ) { M.WallBox(M80Slot::Wood, W(e, X, Z, FD), U3, N3, FVec(HX, 3.5, HZ), false); };

		Pane(e, W0, W1, Z0, Z1, FD + 1, O.Rand * 0.69f, LevelZ(O.Level), LevelZ(O.Level + 1) - LevelZ(O.Level));
		Bar(W0 + 3, Zm, 3, Ht * 0.5);
		Bar(W1 - 3, Zm, 3, Ht * 0.5);
		Bar(Xm, Z1 - 3, Wd * 0.5, 3);
		Bar(Xm, Z0 + 3, Wd * 0.5, 3);
		if (Wd > 60)
		{
			Bar(Xm, Zm, 2.5, Ht * 0.5 - 5);
		}
		if (O.Type == EOpen::French)
		{
			Bar(Xm, Z0 + Ht * 0.78, Wd * 0.5 - 5, 2.5);
			M.WallBox(M80Slot::Wood, W(e, Xm, Z0 + 26, FD - 1), U3, N3, FVec(Wd * 0.5 - 6, 2.5, 20), false);
		}
		else if (Ht > 90)
		{
			Bar(Xm, Z0 + Ht * 0.62, Wd * 0.5 - 5, 2);
		}

		if (O.bBifora)
		{
			// Small column with base and capital between the two lights.
			const double Spr = O.Spring();
			M.Tube(M80Slot::Trim, {W(e, Xm, Z0 + 4, D * 0.5), W(e, Xm, Spr - 8, D * 0.5)}, 4.5, 10);
			M.WallBox(M80Slot::Trim, W(e, Xm, Spr - 4, D * 0.5), U3, N3, FVec(8, D * 0.5 - 1, 4), false);
			M.WallBox(M80Slot::Trim, W(e, Xm, Z0 + 3, D * 0.5), U3, N3, FVec(7, D * 0.5 - 1, 3), false);
		}
		if (O.bGrille || O.Type == EOpen::CellarWindow)
		{
			for (double X = W0 + 9; X < W1 - 4; X += 12)
			{
				M.WallBox(M80Slot::Iron, W(e, X, Zm, 3), U3, N3, FVec(0.8, 0.8, Ht * 0.5 + 2), false);
			}
			for (double Z : {Z0 + 14.0, Z1 - 14.0})
			{
				M.WallBox(M80Slot::Iron, W(e, Xm, Z, 3), U3, N3, FVec(Wd * 0.5, 0.4, 2), false);
			}
		}

		switch (O.Shutter)
		{
		case EShutter::Open:
		{
			const double Leaf = Wd * 0.5, Outside = -(R.FrameProjection + 2.5);
			EmitLeaf(e, W0 - R.FrameWidth * 0.3 - Leaf * 0.5, Zm, Outside, Leaf, Ht, N3);
			if (In.bAbandoned && O.Rand > 0.5f)
			{
				// Broken hinge: the leaf hangs askew.
				EmitLeaf(e, W1 + R.FrameWidth * 0.3 + Leaf * 0.45, Zm - 12, Outside - 3, Leaf, Ht, N3, -14);
			}
			else if (!In.bAbandoned || O.Rand > 0.25f)
			{
				EmitLeaf(e, W1 + R.FrameWidth * 0.3 + Leaf * 0.5, Zm, Outside, Leaf, Ht, N3);
			}
			break;
		}
		case EShutter::Closed:
			EmitLeaf(e, W0 + Wd * 0.25, Zm, 4, Wd * 0.5 - 0.5, Ht - 1, N3);
			EmitLeaf(e, W1 - Wd * 0.25, Zm, 4, Wd * 0.5 - 0.5, Ht - 1, N3);
			break;
		case EShutter::Roller:
		{
			const double Box = 20, Bottom = FMath::Lerp(Z1 - Box, Z0, double(FMath::Clamp(O.Rand * 1.4f, 0.2f, 1.f)));
			M.WallBox(M80Slot::Wood, W(e, Xm, Z1 - Box * 0.5, D * 0.5), U3, N3, FVec(Wd * 0.5, D * 0.5 - 1, Box * 0.5), false);
			if (Z1 - Box - Bottom > 4)
			{
				const double Zc = (Z1 - Box + Bottom) * 0.5;
				M.WallBox(M80Slot::Wood, W(e, Xm, Zc, 5), U3, N3, FVec(Wd * 0.5 - 0.5, 1, (Z1 - Box - Bottom) * 0.5), false);
				for (double Z = Bottom + 3; Z < Z1 - Box - 2; Z += 5)
				{
					M.WallBox(M80Slot::Wood, W(e, Xm, Z, 3.6), U3, N3, FVec(Wd * 0.5 - 0.5, 0.5, 0.7), false);
				}
			}
			break;
		}
		default:
			break;
		}
	}

	void EmitDoor(const FOpening& O)
	{
		const int32 e = O.Edge;
		const FVec U3 = E[e].U3(), N3 = E[e].N3();
		const double D = R.RevealDepth;
		const double Spring = O.Spring();
		const double Leaf = O.Width() * 0.5;
		const double Hgt = Spring - O.Z0;
		for (int32 Side = 0; Side < 2; ++Side)
		{
			const double Xc = O.X0 + Leaf * (Side + 0.5);
			M.WallBox(M80Slot::Wood, W(e, Xc, O.Z0 + Hgt * 0.5, D - 3), U3, N3, FVec(Leaf * 0.5 - 0.4, 3, Hgt * 0.5), false);
			// Raised panels.
			const double PW = Leaf * 0.5 - 11;
			M.WallBox(M80Slot::Wood, W(e, Xc, O.Z0 + Hgt * 0.24, D - 7), U3, N3, FVec(PW, 1.2, Hgt * 0.16), false);
			M.WallBox(M80Slot::Wood, W(e, Xc, O.Z0 + Hgt * 0.68, D - 7), U3, N3, FVec(PW, 1.2, Hgt * 0.24), false);
		}
		M.WallBox(M80Slot::Iron, W(e, O.Mid() + 6, O.Z0 + 105, D - 8), U3, N3, FVec(1.5, 2, 6), false);
		if (O.bArch)
		{
			// Fanlight (rosta): glass under the arch (round or pointed) with radial iron bars.
			const double Rr = O.Width() * 0.5;
			const FVec C = W(e, O.Mid(), Spring, D - 3);
			const int32 Steps = 12;
			M.WallBox(M80Slot::Wood, W(e, O.Mid(), Spring, D - 3), U3, N3, FVec(Rr, 3.5, 4), false);
			auto ArchPoint = [&](double A)
			{
				const double X = O.Mid() - FMath::Cos(A) * Rr;
				return W(e, X, O.TopAt(X) - 3, D - 3);
			};
			for (int32 s = 0; s < Steps; ++s)
			{
				const FVec P0 = ArchPoint(PI * s / Steps), P1 = ArchPoint(PI * (s + 1) / Steps);
				{
					const float Keep = M.ElementRandom;
					M.ElementRandom = 0.f; // dark glass (room code 0)
					M.Tri(M80Slot::Glass, C, P0, P1, {0.5f, 1.f}, {0.f, 0.f}, {1.f, 0.f}, N3);
					M.ElementRandom = Keep;
				}
			}
			for (int32 b = 1; b < 6; ++b)
			{
				const double A = PI * b / 6;
				M.Tube(M80Slot::Iron, {C - N3 * 1.5, C - N3 * 1.5 + (U3 * -FMath::Cos(A) + Up * FMath::Sin(A)) * Rr}, 1.1, 4);
			}
		}
	}

	void EmitGarage(const FOpening& O)
	{
		const int32 e = O.Edge;
		const FVec U3 = E[e].U3(), N3 = E[e].N3();
		const double Zm = (O.Z0 + O.Z1) * 0.5;
		M.WallBox(M80Slot::Iron, W(e, O.Mid(), Zm, 8), U3, N3, FVec(O.Width() * 0.5, 1, (O.Z1 - O.Z0) * 0.5), false);
		for (double Z = O.Z0 + 6; Z < O.Z1 - 4; Z += 9)
		{
			M.WallBox(M80Slot::Iron, W(e, O.Mid(), Z, 6.5), U3, N3, FVec(O.Width() * 0.5, 0.6, 1.4), false);
		}
	}

	/**
	 * Shop front or bar: glazing with a glass door, rolling shutter (up, half down or closed),
	 * painted sign board above and, often, a sun awning.
	 */
	void EmitShop(const FOpening& O)
	{
		const int32 e = O.Edge;
		const FVec U3 = E[e].U3(), N3 = E[e].N3();
		const double Wd = O.Width(), Mid = O.Mid(), D = R.RevealDepth;
		const bool bBar = UseOf(e) == EM80GroundUse::Bar;
		double ShutterBottom = O.Z1;
		if (!bBar && O.Rand < 0.3f)
		{
			ShutterBottom = O.Z0;
		}
		else if (!bBar && O.Rand < 0.5f)
		{
			ShutterBottom = FMath::Lerp(O.Z0, O.Z1, 0.55);
		}
		if (ShutterBottom > O.Z0 + 1)
		{
			const double Hg = O.Z1 - O.Z0;
			M.WallBox(M80Slot::Wood, W(e, Mid, O.Z0 + 20, D - 4), U3, N3, FVec(Wd * 0.5, 3, 20), false);
			Pane(e, O.X0, O.X1, O.Z0 + 40, O.Z1, D - 2, bBar ? 0.95f : 0.7f + O.Rand * 0.19f, LevelZ(0), H.GroundFloorHeight, FMath::Max(Wd + 140, 420.0));
			for (double X : {O.X0 + 3.0, O.X1 - 3.0, Mid - Wd * 0.2, Mid + Wd * 0.2})
			{
				M.WallBox(M80Slot::Wood, W(e, X, O.Z0 + Hg * 0.5, D - 5), U3, N3, FVec(3, 4, Hg * 0.5), false);
			}
			M.WallBox(M80Slot::Wood, W(e, Mid, O.Z1 - 45, D - 5), U3, N3, FVec(Wd * 0.5, 4, 3), false);
			if (bBar)
			{
				// Bead curtain in the doorway.
				for (double X = Mid - Wd * 0.2 + 6; X < Mid + Wd * 0.2 - 4; X += 7)
				{
					M.Tube(M80Slot::Iron, {W(e, X, O.Z1 - 48, D - 10), W(e, X, O.Z0 + 3, D - 10)}, 0.5, 3);
				}
			}
		}
		if (ShutterBottom < O.Z1 - 1)
		{
			const double Zm = (ShutterBottom + O.Z1) * 0.5;
			M.WallBox(M80Slot::Iron, W(e, Mid, Zm, 7), U3, N3, FVec(Wd * 0.5, 1, (O.Z1 - ShutterBottom) * 0.5), false);
			for (double Z = ShutterBottom + 6; Z < O.Z1 - 4; Z += 9)
			{
				M.WallBox(M80Slot::Iron, W(e, Mid, Z, 5.5), U3, N3, FVec(Wd * 0.5, 0.6, 1.4), false);
			}
			M.WallBox(M80Slot::Iron, W(e, Mid, ShutterBottom + 2, 5), U3, N3, FVec(Wd * 0.5, 1.6, 2), false);
		}
		M.WallBox(M80Slot::Iron, W(e, Mid, O.Z1 - 7, 3), U3, N3, FVec(Wd * 0.5, 3, 7), false);

		// Sign board between the shop front and the first-floor windows.
		const double S0 = O.Z1 + R.FrameWidth + 8, S1 = FMath::Min(S0 + (bBar ? 55.0 : 46.0), LevelZ(1) + R.WindowSill - 25);
		if (S1 - S0 > 22)
		{
			const double Sw = Wd * 0.5 + (bBar ? 30 : 12);
			M.WallBox(M80Slot::Trim, W(e, Mid, (S0 + S1) * 0.5, -3), U3, N3, FVec(Sw, 3, (S1 - S0) * 0.5), false);
			M.WallBox(M80Slot::Wood, W(e, Mid, (S0 + S1) * 0.5, -6), U3, N3, FVec(Sw - 6, 1.5, (S1 - S0) * 0.5 - 6), false);
		}

		// Sun awning: canvas slope, front valance and two iron arms.
		if (bBar || O.Rand > 0.55f)
		{
			const double Za = O.Z1 + 4, Reach = bBar ? 150 : 110, Drop = 45;
			const double Xa = O.X0 - 12, Xb = O.X1 + 12;
			const FVec A = W(e, Xa, Za, -2), Bv = W(e, Xb, Za, -2), C = W(e, Xb, Za - Drop, -Reach), Dv = W(e, Xa, Za - Drop, -Reach);
			const FVec Slope = (FVec::CrossProduct(Bv - A, Dv - A)).GetSafeNormal();
			M.ElementRandom = O.Rand;
			M.QuadProjected(M80Slot::Wood, A, Bv, C, Dv, FVec::DotProduct(Slope, Up) > 0 ? Slope : -Slope);
			M.QuadProjected(M80Slot::Wood, Dv, C, Bv, A, FVec::DotProduct(Slope, Up) > 0 ? -Slope : Slope);
			M.QuadProjected(M80Slot::Wood, Dv, C, C - Up * 22, Dv - Up * 22, N3);
			M.QuadProjected(M80Slot::Wood, C, Dv, Dv - Up * 22, C - Up * 22, -N3);
			for (double X : {Xa + 8, Xb - 8})
			{
				M.Tube(M80Slot::Iron, {W(e, X, Za - 95, -1), W(e, X, Za - Drop, -Reach + 4)}, 1.0, 4);
			}
		}
	}

	void EmitPlankDoor(const FOpening& O)
	{
		const int32 e = O.Edge;
		const FVec U3 = E[e].U3(), N3 = E[e].N3();
		const double D = R.RevealDepth;
		const int32 Planks = 5;
		const double PW = O.Width() / Planks;
		for (int32 p = 0; p < Planks; ++p)
		{
			M.ElementRandom = FMath::Frac(O.Rand + p * 0.37f);
			M.WallBox(M80Slot::Wood, W(e, O.X0 + PW * (p + 0.5), (O.Z0 + O.Z1) * 0.5, D - 3), U3, N3, FVec(PW * 0.5 - 0.6, 2.5, (O.Z1 - O.Z0) * 0.5), false);
		}
		for (double Z : {O.Z0 + 35.0, O.Z1 - 35.0})
		{
			M.WallBox(M80Slot::Wood, W(e, O.Mid(), Z, D - 6), U3, N3, FVec(O.Width() * 0.5 - 4, 1.2, 6), false);
		}
	}

	void EmitSteps(const FOpening& O)
	{
		const int32 e = O.Edge;
		const FVec U3 = E[e].U3(), N3 = E[e].N3();
		double Lo, Hi;
		GroundRange(e, O.X0, O.X1, Lo, Hi);
		const double Rise = O.Z0 - Lo;
		// Threshold slab always, steps when the street is lower than the door.
		M.WallBox(M80Slot::Trim, W(e, O.Mid(), O.Z0 - 6, -8), U3, N3, FVec(O.Width() * 0.5 + 12, 8 + R.RevealDepth * 0.5, 6), false);
		if (Rise < 14)
		{
			return;
		}
		const int32 Count = FMath::Clamp(FMath::CeilToInt(Rise / 17.0), 1, 6);
		const double StepH = Rise / Count;
		for (int32 s = 1; s < Count; ++s)
		{
			const double TopZ = O.Z0 - s * StepH;
			const double Depth = 16 + s * 30;
			M.WallBox(M80Slot::Trim, W(e, O.Mid(), (TopZ + Lo - 30) * 0.5, -Depth * 0.5), U3, N3,
				FVec(O.Width() * 0.5 + 18, Depth * 0.5, (TopZ - Lo + 30) * 0.5), true);
		}
	}

	TArray<FVector2D> CorbelProfile(double Depth) const
	{
		const double Dp = Depth;
		if (R.bOrnateCorbels)
		{
			return MakeCCW({{0, 0}, {Dp * .86, 0}, {Dp * .86, -6}, {Dp * .78, -10}, {Dp * .64, -11}, {Dp * .58, -16}, {Dp * .62, -21},
				{Dp * .5, -25}, {Dp * .37, -26}, {Dp * .3, -32}, {Dp * .33, -40}, {Dp * .22, -46}, {Dp * .1, -47}, {0, -52}});
		}
		return MakeCCW({{0, 0}, {Dp * .8, 0}, {Dp * .8, -5}, {Dp * .66, -8}, {Dp * .5, -12}, {Dp * .36, -19}, {Dp * .22, -28}, {Dp * .1, -34}, {0, -37}});
	}

	void ChooseNobleBalcony()
	{
		FRandomStream NobleRng(H.Seed * 977 + 13);
		const float Chance = H.NobleBalconyOverride >= 0 ? H.NobleBalconyOverride : R.NobleBalconyChance;
		bNoble = In.NobleFirst >= 0 && !In.bAbandoned && !In.bUnfinished && NobleRng.FRand() < Chance;
		NobleKind = H.NobleBalconyKind != EM80NobleBalcony::Random ? H.NobleBalconyKind
			: EM80NobleBalcony(1 + NobleRng.RandRange(0, 2));
		bNoblePetto = H.NobleRailing == EM80NobleRailing::Style ? NobleRng.FRand() < R.PettoOcaChance : H.NobleRailing == EM80NobleRailing::Bombe;
	}

	/** A kit mesh placed on facade e: kit X along the wall (mirrored, the pieces are symmetric), Y out, Z up. */
	void AddKit(int32 Piece, int32 e, double X, double Z, const FVector& Scale)
	{
		FM80PropPlacement Prop;
		Prop.Prop = In.NobleFirst + Piece;
		const FQuat Q = FRotationMatrix::MakeFromXZ(-E[e].U3(), Up).ToQuat();
		Prop.Transform = FTransform(Q, W(e, X, Z, 0), Scale);
		Prop.bArchitecture = true;
		Out.Props.Add(Prop);
	}

	/** Carved stone balcony of the palazzi: kit slab with its back plate, consoles to the edge of the slab,
	 *  carved panels between them, straight or goose-breast railing. Kit sizes: slab 240 x 80 cm. */
	void EmitNobleBalcony(const FOpening& O, double BW, double BD)
	{
		struct FSet { int32 Slab, ConsoleA, ConsoleB, Decor; double Thick; };
		static const FSet Sets[3] = {
			{M80NobleKit::SlabVolute, M80NobleKit::ConsoleVolute, M80NobleKit::ConsoleVolute, M80NobleKit::DecorPanel, 20.0},
			{M80NobleKit::SlabMascheroni, M80NobleKit::ConsoleLion, M80NobleKit::ConsoleDog, M80NobleKit::DecorFleur, 13.0},
			{M80NobleKit::SlabAcanto, M80NobleKit::ConsoleAcanto, M80NobleKit::ConsoleAcanto, M80NobleKit::DecorRosette, 17.0}};
		const FSet& Set = Sets[FMath::Clamp(int32(NobleKind) - 1, 0, 2)];
		const int32 e = O.Edge;
		const double Z = O.Z0, Xm = O.Mid();
		const double Sy = BD / 80.0;
		AddKit(Set.Slab, e, Xm, Z, FVector(BW / 240.0, Sy, 1.0));
		// Consoles from end to end of the back plate, about every 70 cm; panels in the bays between them.
		const int32 Count = FMath::Max(2, FMath::RoundToInt(BW / 70.0));
		const double X0 = Xm - BW * 0.5 + 18, Step = (BW - 36) / (Count - 1);
		for (int32 j = 0; j < Count; ++j)
		{
			AddKit(j % 2 ? Set.ConsoleB : Set.ConsoleA, e, X0 + j * Step, Z - Set.Thick, FVector(Sy));
			if (j + 1 < Count && Step > 45)
			{
				AddKit(Set.Decor, e, X0 + (j + 0.5) * Step, Z - Set.Thick, FVector(FMath::Min(Sy, (Step - 22) / 42.0), Sy, Sy));
			}
		}
		// Railing: the kit width nearest to the balcony, stretched to it.
		static const double Widths[3] = {180.0, 240.0, 300.0};
		int32 Wi = 0;
		for (int32 i = 1; i < 3; ++i)
		{
			Wi = FMath::Abs(BW - Widths[i]) < FMath::Abs(BW - Widths[Wi]) ? i : Wi;
		}
		AddKit((bNoblePetto ? M80NobleKit::RailBombe180 : M80NobleKit::RailStraight180) + Wi, e, Xm, Z,
			FVector(BW / Widths[Wi], Sy, R.RailingHeight / 100.0));
	}

	void EmitBalcony(const FOpening& O)
	{
		const int32 e = O.Edge;
		const FVec U3 = E[e].U3(), N3 = E[e].N3();
		const double Z = O.Z0, BD = R.BalconyDepth, S = R.BalconySlab;
		const double BW = O.Width() + 2 * R.FrameWidth + 50;
		const double Xm = O.Mid();
		if (bNoble)
		{
			EmitNobleBalcony(O, BW, BD);
			EmitBalconyDetails(O, BW, BD);
			return;
		}
		M.ElementRandom = Rng.FRand();
		M.WallBox(M80Slot::Trim, W(e, Xm, Z - S * 0.5, -BD * 0.5), U3, N3, FVec(BW * 0.5, BD * 0.5, S * 0.5));
		M.WallBox(M80Slot::Trim, W(e, Xm, Z - S - 2.5, -(BD - 5) * 0.5), U3, N3, FVec(BW * 0.5 - 4, (BD - 5) * 0.5, 2.5));

		const TArray<FVector2D> Profile = CorbelProfile(BD - 2);
		const int32 Count = FMath::Max(2, FMath::RoundToInt(BW / 45.0));
		for (int32 j = 0; j < Count; ++j)
		{
			const double X = Xm - BW * 0.5 + 16 + j * (BW - 32) / (Count - 1);
			M.Sweep(M80Slot::Trim, W(e, X - 7, Z - S - 5, 0), W(e, X + 7, Z - S - 5, 0), N3, N3, Profile, true, true);
		}

		// Iron railing with square bars, as in the Mazzarino streets.
		const double RH = R.RailingHeight, Inset = 4;
		const FVec C0 = W(e, Xm - BW * 0.5 + Inset, Z, -1), C1 = W(e, Xm - BW * 0.5 + Inset, Z, -(BD - Inset));
		const FVec C2 = W(e, Xm + BW * 0.5 - Inset, Z, -(BD - Inset)), C3 = W(e, Xm + BW * 0.5 - Inset, Z, -1);
		M.ElementRandom = Rng.FRand();
		M.Tube(M80Slot::Iron, {C0 + Up * RH, C1 + Up * RH, C2 + Up * RH, C3 + Up * RH}, 2.0, 4);
		M.Tube(M80Slot::Iron, {C0 + Up * 9, C1 + Up * 9, C2 + Up * 9, C3 + Up * 9}, 1.1, 4);
		if (R.bOrnateCorbels)
		{
			M.Tube(M80Slot::Iron, {C0 + Up * (RH - 18), C1 + Up * (RH - 18), C2 + Up * (RH - 18), C3 + Up * (RH - 18)}, 1.0, 4);
		}
		for (const FVec& Post : {C1, C2})
		{
			M.Box(M80Slot::Iron, Post + Up * RH * 0.5, U3, N3, Up, FVec(1.8, 1.8, RH * 0.5));
		}
		const FVec Sides[3][2] = {{C0, C1}, {C1, C2}, {C2, C3}};
		const FVec SideOut[3] = {-U3, -N3, U3};
		// Petto d'oca: the bars bulge out in their lower half (baroque balconies of the palazzi).
		const bool bPetto = FMath::Frac(O.Rand * 5.17f) < R.PettoOcaChance;
		const bool bLiberty = !bPetto && FMath::Frac(O.Rand * 7.77f) < R.LibertyRailingChance;
		const double Bulge = bPetto ? 22.0 : 0.0;
		for (int32 si = 0; si < 3; ++si)
		{
			const FVec* Side = Sides[si];
			const double Len = (Side[1] - Side[0]).Size();
			const int32 Bars = FMath::FloorToInt(Len / 11.0);
			for (int32 b = 1; b < Bars; ++b)
			{
				const FVec Base = FMath::Lerp(Side[0], Side[1], double(b) / Bars);
				if (bPetto)
				{
					// Taper the bulge towards the wall on the side railings.
					const double Taper = si == 1 ? 1.0 : FMath::Clamp((Base - C0).Size() / FMath::Max(1.0, BD), 0.2, 1.0);
					const FVec O3 = SideOut[si] * (Bulge * Taper);
					M.Tube(M80Slot::Iron, {Base + Up * 9, Base + Up * (RH * 0.3) + O3, Base + Up * (RH * 0.6) + O3 * 0.6, Base + Up * RH}, 0.8, 4);
				}
				else
				{
					M.Box(M80Slot::Iron, Base + Up * (9 + RH) * 0.5, U3, N3, Up, FVec(0.7, 0.7, (RH - 9) * 0.5));
				}
			}
			if (bLiberty && si == 1)
			{
				// Liberty scrolls (girali) between the bars of the front railing.
				const int32 Scrolls = FMath::Max(1, FMath::FloorToInt(Len / 38.0));
				for (int32 k = 0; k < Scrolls; ++k)
				{
					const FVec Mid0 = FMath::Lerp(Side[0], Side[1], (k + 0.5) / Scrolls);
					const FVec Along = (Side[1] - Side[0]).GetSafeNormal();
					TArray<FVec> Pts;
					for (int32 t = 0; t <= 16; ++t)
					{
						const double A = 2 * PI * t / 16;
						Pts.Add(Mid0 + Up * (22 + (RH - 40) * t / 16.0) + Along * (13 * FMath::Sin(A)) + SideOut[si] * 0.5);
					}
					M.Tube(M80Slot::Iron, Pts, 0.7, 4);
				}
			}
		}
		if (FMath::Frac(O.Rand * 11.3f) < R.MajolicaBalconyChance)
		{
			// Majolica tiles on the underside and front of the slab.
			M.QuadProjected(M80Slot::Majolica, W(e, Xm - BW * 0.5 + 2, Z - S - 0.3, -2), W(e, Xm + BW * 0.5 - 2, Z - S - 0.3, -2),
				W(e, Xm + BW * 0.5 - 2, Z - S - 0.3, -BD + 2), W(e, Xm - BW * 0.5 + 2, Z - S - 0.3, -BD + 2), -Up);
			M.QuadProjected(M80Slot::Majolica, W(e, Xm - BW * 0.5, Z - S + 1, -BD - 0.3), W(e, Xm + BW * 0.5, Z - S + 1, -BD - 0.3),
				W(e, Xm + BW * 0.5, Z - 1, -BD - 0.3), W(e, Xm - BW * 0.5, Z - 1, -BD - 0.3), -N3);
		}
		EmitBalconyDetails(O, BW, BD);
	}

	/** Pots, Moor's heads and the basket on its rope. */
	void EmitBalconyDetails(const FOpening& O, double BW, double BD)
	{
		const int32 e = O.Edge;
		const double Z = O.Z0, Xm = O.Mid(), RH = R.RailingHeight;
		const double Sc = Sicily();
		if (In.CatCount[M80Cat::Balcony] > 0 && Rng.FRand() < 0.85 * Sc)
		{
			const int32 N = Rng.RandRange(1, 3);
			for (int32 k = 0; k < N; ++k)
			{
				const double X = Xm - BW * 0.5 + 18 + (BW - 36) * (N == 1 ? Rng.FRand() : double(k) / (N - 1));
				AddCat(M80Cat::Balcony, W(e, X, Z, -BD + 16), WallYaw(e) + Rng.FRandRange(-10.f, 10.f));
			}
		}
		else if (In.NumProps > 0 && Rng.FRand() < 0.4f)
		{
			FM80PropPlacement Prop;
			Prop.Prop = Rng.RandRange(0, In.NumProps - 1);
			Prop.Transform = FTransform(FRotator(0, Rng.FRandRange(0, 360), 0), W(e, Xm + BW * 0.5 - 18, Z, -BD + 20));
			Out.Props.Add(Prop);
		}
		if (IsStreet(e) && Rng.FRand() < 0.12 * Sc)
		{
			AddCat(M80Cat::Basket, W(e, Xm + BW * 0.3, Z + RH, -BD - 3), WallYaw(e));
		}
	}

	// ---------------------------------------------------------------- horizontal elements

	/** Sweeps a profile along every facade edge accepted by Filter, mitering shared corners. */
	template <typename FilterType, typename HeightType>
	void SweepAlongEdges(int32 Slot, const TArray<FVector2D>& Profile, FilterType Filter, HeightType HeightAt)
	{
		for (int32 e = 0; e < E.Num(); ++e)
		{
			if (!Filter(e))
			{
				continue;
			}
			const bool bJoinPrev = Filter(Prev(e)), bJoinNext = Filter(Next(e));
			const FVector2D M0 = bJoinPrev ? M80Poly::Miter(P, e) : E[e].N;
			const FVector2D M1 = bJoinNext ? M80Poly::Miter(P, Next(e)) : E[e].N;
			TArray<double> Xs = {0.0};
			if (const double K = RidgeCrossing(e); K > 0)
			{
				Xs.Add(K);
			}
			Xs.Add(E[e].L);
			for (int32 i = 0; i + 1 < Xs.Num(); ++i)
			{
				const bool bFirst = i == 0, bLast = i + 2 == Xs.Num();
				const FVec Start = W(e, Xs[i], HeightAt(e, Xs[i]));
				const FVec End = W(e, Xs[i + 1], HeightAt(e, Xs[i + 1]));
				const FVec Out0 = bFirst ? FVec(M0.X, M0.Y, 0) : E[e].N3();
				const FVec Out1 = bLast ? FVec(M1.X, M1.Y, 0) : E[e].N3();
				M.Sweep(Slot, Start, End, Out0, Out1, Profile, bFirst && !bJoinPrev, bLast && !bJoinNext);
			}
		}
	}

	/**
	 * Capochiave: the iron anchors of the tie rods that hold old masonry walls together, at the
	 * floor levels near the corners (crosses, bars, S shapes, round plates), rusty and proud of the wall.
	 */
	void EmitTieRods()
	{
		if (Floors < 2 || Rng.FRand() >= H.TieRodChance)
		{
			return;
		}
		const int32 Shape = Rng.RandRange(0, 3);
		M.ElementRandom = Rng.FRand();
		for (int32 e = 0; e < E.Num(); ++e)
		{
			if (!IsFacade(e) || E[e].L < 250)
			{
				continue;
			}
			TArray<double> Xs = {55.0, E[e].L - 55};
			if (E[e].L > 900)
			{
				Xs.Add(E[e].L * 0.5);
			}
			for (int32 K = 1; K < Floors; ++K)
			{
				const double Z = LevelZ(K) - 18;
				for (double X : Xs)
				{
					if (!ClearOfOpenings(e, X - 30, X + 30, Z - 30, Z + 30))
					{
						continue;
					}
					EmitTieRod(e, X, Z, Shape);
				}
			}
		}
		M.ElementRandom = 0.f;
	}

	void EmitTieRod(int32 e, double X, double Z, int32 Shape)
	{
		const FVec U3 = E[e].U3(), N3 = E[e].N3();
		const FVec C = W(e, X, Z, -1.5);
		auto Bar = [&](double AngleDeg, double HalfLen, double HalfWidth)
		{
			const double A = FMath::DegreesToRadians(AngleDeg);
			const FVec Ax = (U3 * FMath::Cos(A) + Up * FMath::Sin(A)).GetSafeNormal();
			const FVec Az = (Up * FMath::Cos(A) - U3 * FMath::Sin(A)).GetSafeNormal();
			M.Box(M80Slot::Iron, C, Ax, N3, Az, FVec(HalfLen, 1.2, HalfWidth));
		};
		switch (Shape)
		{
		case 0: // cross
			Bar(90, 30, 2.5);
			Bar(0, 22, 2.5);
			break;
		case 1: // single bar, slightly tilted
			Bar(90 + Rng.FRandRange(-6.f, 6.f), 34, 2.8);
			break;
		case 2: // S anchor
		{
			TArray<FVec> Pts;
			for (int32 k = 0; k <= 12; ++k)
			{
				const double T = double(k) / 12;
				Pts.Add(C + Up * ((T - 0.5) * 60) + U3 * (10 * FMath::Sin(T * 2 * PI)));
			}
			M.Tube(M80Slot::Iron, Pts, 1.8, 5);
			break;
		}
		default: // round plate with a bolt
			M.Tube(M80Slot::Iron, {C - N3 * 1.0, C + N3 * 1.2}, 13, 10, true);
			break;
		}
		// The end of the rod and its wedge.
		M.Tube(M80Slot::Iron, {C, C + N3 * 4.5}, 1.6, 6, true);
		M.Box(M80Slot::Iron, C + N3 * 3.0, Up, N3, U3, FVec(6, 1.2, 1.5));
	}

	/** Concrete frame of an unfinished floor: corner pillars, ring beam and rebar sticking out on top. */
	void EmitUnfinished()
	{
		const double Bottom = Floor0 - 2;
		for (int32 i = 0; i < P.Num(); ++i)
		{
			const FVector2D Q = P[i];
			const FVector2D Mi = M80Poly::Miter(P, i);
			const FVec C(Q.X - Mi.X * 13, Q.Y - Mi.Y * 13, (Bottom + Top) * 0.5);
			const FVec Ax = E[i].U3(), Ay = E[i].N3();
			M.Box(M80Slot::Terrace, C + FVec(Mi.X, Mi.Y, 0) * 15, Ax, Ay, Up, FVec(16, 16, (Top - Bottom) * 0.5));
			for (int32 k = 0; k < 4; ++k)
			{
				const FVec Bar = FVec(Q.X - Mi.X * (6 + (k % 2) * 14), Q.Y - Mi.Y * (6 + (k / 2) * 14), Top) + FVec(Mi.X, Mi.Y, 0) * 15;
				const double Len = Rng.FRandRange(45.f, 90.f);
				M.Tube(M80Slot::Iron, {Bar, Bar + Up * Len + FVec(Rng.FRandRange(-6.f, 6.f), Rng.FRandRange(-6.f, 6.f), 0)}, 0.7, 4);
			}
		}
		for (int32 e = 0; e < E.Num(); ++e)
		{
			// Ring beam and floor slab edge.
			M.WallBox(M80Slot::Terrace, W(e, E[e].L * 0.5, Top - 12, -1.5), E[e].U3(), E[e].N3(), FVec(E[e].L * 0.5, 1.5, 12), false);
			M.WallBox(M80Slot::Terrace, W(e, E[e].L * 0.5, Floor0 + 6, -1.5), E[e].U3(), E[e].N3(), FVec(E[e].L * 0.5, 1.5, 12), false);
		}
	}

	void EmitBands()
	{
		if (!R.bStringCourse)
		{
			return;
		}
		const TArray<FVector2D> Band = MakeCCW({{0, -14}, {5, -14}, {5, -3}, {7, -3}, {7, 0}, {0, 0}});
		for (int32 K = 1; K < Floors; ++K)
		{
			const double Z = LevelZ(K);
			SweepAlongEdges(M80Slot::Trim, Band, [&](int32 e) { return IsStreet(e) && E[e].L > 60; }, [Z](int32, double) { return Z; });
		}
	}

	void EmitCornice()
	{
		const double Hc = R.CorniceHeight;
		auto Facade = [&](int32 e) { return IsFacade(e); };
		if (Roof == EM80RoofType::Terrace)
		{
			const double Pc = FMath::Min(R.CorniceProjection, 18.f);
			const TArray<FVector2D> Cornice = MakeCCW({{0, -Hc}, {Pc * .3, -Hc}, {Pc * .3, -Hc * .7}, {Pc * .7, -Hc * .55}, {Pc, -Hc * .25}, {Pc, 0}, {0, 0}});
			SweepAlongEdges(M80Slot::Trim, Cornice, Facade, [this](int32, double) { return Top; });
			const TArray<FVector2D> Parapet = MakeCCW({{-ParapetThk, 0}, {0, 0}, {0, R.ParapetHeight}, {-ParapetThk, R.ParapetHeight}});
			SweepAlongEdges(In.WallSlot, Parapet, Facade, [this](int32, double) { return Top; });
			const TArray<FVector2D> Coping = MakeCCW({{-ParapetThk - 3, 0}, {4, 0}, {4, 6}, {-ParapetThk - 3, 6}});
			SweepAlongEdges(M80Slot::Trim, Coping, Facade, [this](int32, double) { return ParapetTop(); });
			return;
		}
		const double Pc = FMath::Max(8.0, FMath::Min<double>(R.CorniceProjection, R.EaveOverhang - 4));
		const TArray<FVector2D> Cornice = MakeCCW({{0, -Hc}, {Pc * .3, -Hc}, {Pc * .3, -Hc * .72}, {Pc * .6, -Hc * .6},
			{Pc * .85, -Hc * .32}, {Pc, -Hc * .18}, {Pc, 0}, {0, 0}});
		SweepAlongEdges(M80Slot::Trim, Cornice, Facade, [this](int32 e, double X) { return WallTop(e, X); });
	}

	void EmitCorners()
	{
		if (R.CornerStyle == EM80CornerStyle::None)
		{
			return;
		}
		for (int32 v = 0; v < E.Num(); ++v)
		{
			const int32 A = Prev(v), B = v;
			if (!IsFacade(A) || !IsFacade(B) || E[A].L < 100 || E[B].L < 100)
			{
				continue;
			}
			const double Turn = E[A].U.X * E[B].U.Y - E[A].U.Y * E[B].U.X;
			if (Turn < 0.2)
			{
				continue; // concave or almost straight
			}
			const double Bottom = G(P[v]) - 40;
			double TopZ = FMath::Min(WallTop(A, E[A].L), WallTop(B, 0.0));
			TopZ = Roof == EM80RoofType::Terrace ? Top - R.CorniceHeight : TopZ - R.CorniceHeight;
			const FVec UA = E[A].U3(), NA = E[A].N3(), UB = E[B].U3(), NB = E[B].N3();
			if (R.CornerStyle == EM80CornerStyle::Pilaster)
			{
				const double Pr = 6, Wd = 42;
				M.WallBox(M80Slot::Trim, W(B, (Wd - Pr) * 0.5, (Bottom + TopZ) * 0.5, -Pr * 0.5), UB, NB, FVec((Wd + Pr) * 0.5, Pr * 0.5, (TopZ - Bottom) * 0.5));
				M.WallBox(M80Slot::Trim, W(A, E[A].L - Wd * 0.5, (Bottom + TopZ) * 0.5, -Pr * 0.5), UA, NA, FVec(Wd * 0.5, Pr * 0.5, (TopZ - Bottom) * 0.5));
				M.WallBox(M80Slot::Trim, W(B, (Wd + 8 - Pr - 4) * 0.5, TopZ - 10, -(Pr + 4) * 0.5), UB, NB, FVec((Wd + 8 + Pr + 4) * 0.5, (Pr + 4) * 0.5, 10));
				M.WallBox(M80Slot::Trim, W(A, E[A].L - (Wd + 8) * 0.5, TopZ - 10, -(Pr + 4) * 0.5), UA, NA, FVec((Wd + 8) * 0.5, (Pr + 4) * 0.5, 10));
				continue;
			}
			const double Pr = 2.5;
			int32 Course = 0;
			for (double Z = Bottom; Z < TopZ - 5; ++Course)
			{
				const double Hb = FMath::Min(Course % 2 ? 28.0 : 34.0, TopZ - Z);
				const double LenB = Course % 2 ? 32.0 : 56.0, LenA = Course % 2 ? 56.0 : 32.0;
				M.ElementRandom = Rng.FRand();
				M.WallBox(M80Slot::Trim, W(B, (LenB - Pr) * 0.5, Z + Hb * 0.5, -Pr * 0.5), UB, NB, FVec((LenB + Pr) * 0.5, Pr * 0.5, Hb * 0.5 - 0.6));
				M.WallBox(M80Slot::Trim, W(A, E[A].L - LenA * 0.5, Z + Hb * 0.5, -Pr * 0.5), UA, NA, FVec(LenA * 0.5, Pr * 0.5, Hb * 0.5 - 0.6));
				Z += Hb;
			}
			M.ElementRandom = 0;
		}
	}

	// ---------------------------------------------------------------- roof

	FVector2f RoofUV(const FVector2D& Q) const
	{
		const double S = FVector2D::DotProduct(Q, Across);
		double Down = 0;
		if (Roof == EM80RoofType::Gable)
		{
			Down = FMath::Abs(S - SMid);
		}
		else
		{
			Down = bShedLowAtMin ? SMax - S : S - SMin;
		}
		return FVector2f(float(FVector2D::DotProduct(Q, RidgeDir) / 100.0), float(Down / CosPitch / 100.0));
	}

	/** Splits a convex polygon by the line S = SMid. */
	static void ClipBySide(const TArray<FVector2D>& Poly, const FVector2D& Axis, double Cut, bool bKeepHigh, TArray<FVector2D>& Result)
	{
		Result.Reset();
		for (int32 i = 0; i < Poly.Num(); ++i)
		{
			const FVector2D& A = Poly[i];
			const FVector2D& B = Poly[(i + 1) % Poly.Num()];
			const double DA = FVector2D::DotProduct(A, Axis) - Cut, DB = FVector2D::DotProduct(B, Axis) - Cut;
			const bool InA = bKeepHigh ? DA >= 0 : DA <= 0, InB = bKeepHigh ? DB >= 0 : DB <= 0;
			if (InA)
			{
				Result.Add(A);
			}
			if (InA != InB)
			{
				Result.Add(A + (B - A) * (DA / (DA - DB)));
			}
		}
	}

	void EmitRoofPiece(const TArray<FVector2D>& Piece)
	{
		if (Piece.Num() < 3)
		{
			return;
		}
		FVector2D C(0, 0);
		for (const FVector2D& Q : Piece)
		{
			C += Q;
		}
		C /= Piece.Num();
		// Normal of the plane through this piece.
		const FVec A3(Piece[0].X, Piece[0].Y, RoofLine(Piece[0]));
		FVec Normal = Up;
		for (int32 i = 1; i + 1 < Piece.Num(); ++i)
		{
			const FVec B3(Piece[i].X, Piece[i].Y, RoofLine(Piece[i])), C3(Piece[i + 1].X, Piece[i + 1].Y, RoofLine(Piece[i + 1]));
			const FVec N = FVec::CrossProduct(B3 - A3, C3 - A3);
			if (N.SizeSquared() > 1)
			{
				Normal = N.GetSafeNormal() * (N.Z < 0 ? -1.0 : 1.0);
				break;
			}
		}
		for (int32 i = 1; i + 1 < Piece.Num(); ++i)
		{
			const FVector2D &Q0 = Piece[0], &Q1 = Piece[i], &Q2 = Piece[i + 1];
			M.Tri(M80Slot::Roof, FVec(Q0.X, Q0.Y, RoofLine(Q0) + RoofThk), FVec(Q1.X, Q1.Y, RoofLine(Q1) + RoofThk), FVec(Q2.X, Q2.Y, RoofLine(Q2) + RoofThk),
				RoofUV(Q0), RoofUV(Q1), RoofUV(Q2), Normal);
			M.Tri(M80Slot::Trim, FVec(Q0.X, Q0.Y, RoofLine(Q0)), FVec(Q1.X, Q1.Y, RoofLine(Q1)), FVec(Q2.X, Q2.Y, RoofLine(Q2)),
				FVector2f(Q0 / 100.0), FVector2f(Q1 / 100.0), FVector2f(Q2 / 100.0), -Normal);
		}
	}

	/** Half-round tile (coppo) lying along Axis, open side down. */
	void Coppo(const FVec& Start, const FVec& Axis, const FVec& Normal, double Length, double Radius)
	{
		const FVec Side = FVec::CrossProduct(Normal, Axis).GetSafeNormal();
		const int32 Seg = 5;
		M.ElementRandom = Rng.FRand();
		for (int32 s = 0; s < Seg; ++s)
		{
			const double A0 = PI * s / Seg, A1 = PI * (s + 1) / Seg;
			const FVec R0 = Side * FMath::Cos(A0) + Normal * FMath::Sin(A0), R1 = Side * FMath::Cos(A1) + Normal * FMath::Sin(A1);
			const FVec P0 = Start + R0 * Radius, P1 = Start + R1 * Radius;
			const FVec I0 = Start + R0 * (Radius - 1.6), I1 = Start + R1 * (Radius - 1.6);
			const FVector2f U0(float(s) / Seg * 0.3f, 0), U1(float(s + 1) / Seg * 0.3f, 0), V(0, float(Length / 100));
			M.Quad(M80Slot::Roof, P0, P1, P1 + Axis * Length, P0 + Axis * Length, U0, U1, U1 + V, U0 + V, (R0 + R1).GetSafeNormal());
			M.Quad(M80Slot::Roof, I1, I0, I0 + Axis * Length, I1 + Axis * Length, U1, U0, U0 + V, U1 + V, -(R0 + R1).GetSafeNormal());
			M.Quad(M80Slot::Roof, P0 + Axis * Length, P1 + Axis * Length, I1 + Axis * Length, I0 + Axis * Length, U0, U1, U1, U0, Axis);
		}
		M.ElementRandom = 0;
	}

	void EmitRoof()
	{
		if (Roof == EM80RoofType::Terrace)
		{
			M.Polygon(M80Slot::Terrace, P, Top, true);
			EmitTerraceDetails();
			return;
		}
		TArray<double> Dist;
		for (int32 e = 0; e < E.Num(); ++e)
		{
			Dist.Add(IsFacade(e) ? R.EaveOverhang : 0.0);
		}
		const TArray<FVector2D> RP = M80Poly::OffsetEdges(P, Dist);
		TArray<int32> Tris;
		M80Poly::Triangulate(RP, Tris);
		TArray<FVector2D> Piece;
		for (int32 t = 0; t + 2 < Tris.Num(); t += 3)
		{
			const TArray<FVector2D> Tri = {RP[Tris[t]], RP[Tris[t + 1]], RP[Tris[t + 2]]};
			if (Roof == EM80RoofType::Gable)
			{
				ClipBySide(Tri, Across, SMid, true, Piece);
				EmitRoofPiece(Piece);
				ClipBySide(Tri, Across, SMid, false, Piece);
				EmitRoofPiece(Piece);
			}
			else
			{
				EmitRoofPiece(Tri);
			}
		}

		// Fascia around the roof slab, split at the ridge so it follows the slopes.
		for (int32 i = 0; i < RP.Num(); ++i)
		{
			const FVector2D A = RP[i], B = RP[(i + 1) % RP.Num()];
			const FVector2D N2 = M80Poly::EdgeNormal(RP, i);
			TArray<FVector2D> Pts = {A};
			const double SA = FVector2D::DotProduct(A, Across) - SMid, SB = FVector2D::DotProduct(B, Across) - SMid;
			if (Roof == EM80RoofType::Gable && SA * SB < 0)
			{
				Pts.Add(A + (B - A) * (SA / (SA - SB)));
			}
			Pts.Add(B);
			for (int32 k = 0; k + 1 < Pts.Num(); ++k)
			{
				const FVector2D Q0 = Pts[k], Q1 = Pts[k + 1];
				M.QuadProjected(M80Slot::Roof, FVec(Q0.X, Q0.Y, RoofLine(Q0)), FVec(Q1.X, Q1.Y, RoofLine(Q1)),
					FVec(Q1.X, Q1.Y, RoofLine(Q1) + RoofThk), FVec(Q0.X, Q0.Y, RoofLine(Q0) + RoofThk), FVec(N2.X, N2.Y, 0));
			}
		}

		// Eave row of coppi: the silhouette that makes the roof read as Sicilian from the street.
		for (int32 i = 0; i < RP.Num(); ++i)
		{
			if (!IsFacade(i))
			{
				continue;
			}
			const FVector2D A = RP[i], B = RP[(i + 1) % RP.Num()];
			const double L = FVector2D::Distance(A, B);
			const FVector2D U = (B - A) / FMath::Max(1.0, L);
			const FVector2D N2 = M80Poly::EdgeNormal(RP, i);
			if (L < 60 || FMath::Abs(FVector2D::DotProduct(U, RidgeDir)) < 0.85 || RoofLine((A + B) * 0.5) > Top + 25)
			{
				continue;
			}
			const double Drop = TanPitch;
			const FVec Axis = FVec(N2.X, N2.Y, -Drop).GetSafeNormal();
			const FVec Normal = (Up - Axis * FVec::DotProduct(Up, Axis)).GetSafeNormal();
			for (double X = 12; X < L - 10; X += 21)
			{
				const FVector2D Q = A + U * X - N2 * 30;
				Coppo(FVec(Q.X, Q.Y, RoofLine(Q) + RoofThk - 2), Axis, Normal, 36, 7.5);
			}
		}

		if (Roof == EM80RoofType::Gable)
		{
			// Ridge row (colmo) along the part of the ridge line inside the roof outline.
			double TMin = TNumericLimits<double>::Max(), TMax = -TMin;
			for (int32 i = 0; i < RP.Num(); ++i)
			{
				const FVector2D A = RP[i], B = RP[(i + 1) % RP.Num()];
				const double SA = FVector2D::DotProduct(A, Across) - SMid, SB = FVector2D::DotProduct(B, Across) - SMid;
				if (SA * SB <= 0 && FMath::Abs(SA - SB) > 1e-6)
				{
					const FVector2D X = A + (B - A) * (SA / (SA - SB));
					const double T = FVector2D::DotProduct(X, RidgeDir);
					TMin = FMath::Min(TMin, T);
					TMax = FMath::Max(TMax, T);
				}
			}
			if (TMax > TMin)
			{
				const FVec Axis(RidgeDir.X, RidgeDir.Y, 0);
				for (double T = TMin; T < TMax - 30; T += 34)
				{
					const FVector2D Q = RidgeDir * T + Across * SMid;
					Coppo(FVec(Q.X, Q.Y, RoofLine(Q) + RoofThk - 3), Axis, Up, 38, 10.5);
				}
			}
		}
		EmitChimneyAndAntenna();
	}

	FVector2D InteriorPoint(double Along, double AcrossOffset) const
	{
		FVector2D C(0, 0);
		for (const FVector2D& Q : P)
		{
			C += Q;
		}
		C /= P.Num();
		FVector2D Q = C + RidgeDir * Along + Across * AcrossOffset;
		if (!M80Poly::Contains(P, Q))
		{
			return C;
		}
		return Q;
	}

	bool FarFromEdges(const FVector2D& Q, double Margin) const
	{
		for (int32 e = 0; e < E.Num(); ++e)
		{
			if (M80Poly::SegmentDistance(Q, E[e].A, E[e].B) < Margin)
			{
				return false;
			}
		}
		if (In.KeepOut.Num() >= 3)
		{
			if (M80Poly::Contains(In.KeepOut, Q))
			{
				return false;
			}
			for (int32 i = 0; i < In.KeepOut.Num(); ++i)
			{
				if (M80Poly::SegmentDistance(Q, In.KeepOut[i], In.KeepOut[(i + 1) % In.KeepOut.Num()]) < Margin)
				{
					return false;
				}
			}
		}
		return M80Poly::Contains(P, Q);
	}

	/** Horizontal Yagi: boom along A, elements across it (C), shorter towards the front. */
	void Yagi(const FVec& At, const FVec& A, const FVec& C, double Length, int32 Elements, double Span)
	{
		M.Tube(M80Slot::Iron, {At - A * Length * 0.3, At + A * Length * 0.7}, 0.8, 4);
		for (int32 k = 0; k < Elements; ++k)
		{
			const double T = double(k) / FMath::Max(1, Elements - 1);
			const double HalfSpan = Span * (1.0 - 0.45 * T);
			const FVec Pos = At + A * FMath::Lerp(-Length * 0.3, Length * 0.7, T);
			M.Tube(M80Slot::Iron, {Pos - C * HalfSpan, Pos + C * HalfSpan}, 0.45, 3);
		}
	}

	/**
	 * Rooftop TV antennas of the 70s-80s: VHF Yagi, UHF fishbone with a reflector grid,
	 * stacked pairs and bow-tie dipoles. All aim roughly the same way (the transmitter).
	 */
	void EmitAntenna(const FVector2D& Q, double BaseZ, int32 Type = -1)
	{
		for (const FVector2D& Other : AntennaSpots)
		{
			if (FVector2D::Distance(Other, Q) < 130)
			{
				return;
			}
		}
		AntennaSpots.Add(Q);
		if (Type < 0)
		{
			Type = Rng.RandRange(0, 3);
		}
		const FVec B(Q.X, Q.Y, BaseZ);
		const double Aim = FMath::DegreesToRadians(Rng.FRandRange(-25.f, 25.f));
		const FVector2D Dir = RidgeDir.GetRotated(FMath::RadiansToDegrees(Aim));
		const FVec A(Dir.X, Dir.Y, 0), C(-Dir.Y, Dir.X, 0);
		const double Mast = Rng.FRandRange(220.f, 380.f);
		M.ElementRandom = Rng.FRand();
		M.Tube(M80Slot::Iron, {B, B + Up * Mast}, 1.7, 5);
		M.Box(M80Slot::Iron, B + Up * 6, A, C, Up, FVec(10, 10, 6));
		switch (Type)
		{
		case 0:
			Yagi(B + Up * (Mast - 15), A, C, 150, 7, 34);
			Yagi(B + Up * (Mast - 60), A, C, 120, 5, 30);
			break;
		case 1:
		{
			// UHF fishbone: dense short elements and a grid reflector behind.
			const FVec At = B + Up * (Mast - 10);
			Yagi(At, A, C, 130, 14, 13);
			for (int32 k = -2; k <= 2; ++k)
			{
				const FVec R0 = At - A * 42 + C * (k * 9);
				M.Tube(M80Slot::Iron, {R0 - Up * 28, R0 + Up * 28}, 0.4, 3);
			}
			break;
		}
		case 2:
		{
			// Two antennas on the same mast, aimed at different transmitters.
			Yagi(B + Up * (Mast - 15), A, C, 150, 6, 32);
			const FVector2D Dir2 = Dir.GetRotated(Rng.FRandRange(35.f, 80.f) * (Rng.FRand() < 0.5f ? -1 : 1));
			Yagi(B + Up * (Mast - 75), FVec(Dir2.X, Dir2.Y, 0), FVec(-Dir2.Y, Dir2.X, 0), 110, 10, 13);
			break;
		}
		default:
		{
			// Bow-tie dipoles stacked on a short cross bar.
			for (double Z : {Mast - 20, Mast - 70})
			{
				const FVec At = B + Up * Z;
				for (double S : {-1.0, 1.0})
				{
					const FVec Tip = At + C * (S * 38);
					M.Tube(M80Slot::Iron, {At + C * (S * 4), Tip + Up * 16, Tip - Up * 16, At + C * (S * 4)}, 0.5, 3);
				}
			}
			break;
		}
		}
		// Guy wires to the roof.
		for (int32 k = 0; k < 3; ++k)
		{
			const double Ang = Rng.FRandRange(0.f, 0.4f) + k * 2.09;
			const FVec Foot = B + A * (FMath::Cos(Ang) * 110) + C * (FMath::Sin(Ang) * 110);
			M.Tube(M80Slot::Iron, {B + Up * (Mast * 0.65), Foot + Up * 3}, 0.25, 3);
		}
		M.ElementRandom = 0;
	}

	void EmitChimneyAndAntenna()
	{
		const double Extent = Half;
		if (Rng.FRand() < R.ChimneyChance)
		{
			const FVector2D Q = InteriorPoint(Rng.FRandRange(-1, 1) * Extent * 0.6, Roof == EM80RoofType::Gable ? 45 : 0);
			if (FarFromEdges(Q, 50))
			{
				const double Base = RoofLine(Q) - 20, Ridge = Roof == EM80RoofType::Gable ? Top + TanPitch * Half : RoofLine(Q);
				const double TopZ = Ridge + 85;
				const FVec Ax(RidgeDir.X, RidgeDir.Y, 0), Ay(Across.X, Across.Y, 0);
				M.FacadeMask = 1.f;
				M.Box(In.WallSlot, FVec(Q.X, Q.Y, (Base + TopZ) * 0.5), Ax, Ay, Up, FVec(28, 22, (TopZ - Base) * 0.5), true);
				M.FacadeMask = 0.f;
				M.Box(M80Slot::Trim, FVec(Q.X, Q.Y, TopZ + 3), Ax, Ay, Up, FVec(34, 28, 3));
				M.Box(M80Slot::Trim, FVec(Q.X, Q.Y, TopZ + 22), Ax, Ay, Up, FVec(30, 24, 3));
				for (double S : {-20.0, 20.0})
				{
					M.Box(M80Slot::Trim, FVec(Q.X, Q.Y, TopZ + 12) + Ax * S, Ax, Ay, Up, FVec(5, 18, 7));
				}
			}
		}
		const int32 Antennas = Rng.FRand() < 0.8f ? 1 + (E[Front].L > 700 ? Rng.RandRange(0, 2) : Rng.RandRange(0, 1)) : 0;
		for (int32 k = 0; k < Antennas; ++k)
		{
			const FVector2D Q = InteriorPoint(Rng.FRandRange(-1, 1) * Extent * 0.6, Rng.FRandRange(-40.f, -20.f));
			if (FarFromEdges(Q, 40))
			{
				EmitAntenna(Q, RoofLine(Q) + RoofThk - 5);
			}
		}
	}

	void EmitTerraceDetails()
	{
		const double Sc = Sicily();
		for (int32 k = 0; k < 2; ++k)
		{
			if (Rng.FRand() < 0.45 * Sc)
			{
				const FVector2D Q = InteriorPoint(Rng.FRandRange(-1, 1) * Half * 0.6, Rng.FRandRange(-1, 1) * Half * 0.5);
				if (FarFromEdges(Q, 70))
				{
					AddCat(M80Cat::Terrace, FVec(Q.X, Q.Y, Top), Rng.FRandRange(0, 360));
				}
			}
		}
		if (Rng.FRand() < 0.7 * Sc && !In.bUnfinished)
		{
			for (int32 e = 0; e < E.Num(); ++e)
			{
				if (!IsStreet(e) || E[e].L < 200)
				{
					continue;
				}
				for (double X = Rng.FRandRange(80, 160); X < E[e].L - 60; X += Rng.FRandRange(280, 420))
				{
					AddCat(M80Cat::Spout, W(e, X, Top + 6, 0), WallYaw(e));
				}
			}
		}
		// Pots lined up along the parapet of the street side.
		if (In.NumProps > 0)
		{
			for (int32 e = 0; e < E.Num(); ++e)
			{
				if (!IsStreet(e) || E[e].L < 150)
				{
					continue;
				}
				for (double X = 50; X < E[e].L - 40; X += Rng.FRandRange(60, 160))
				{
					const FVec Spot = W(e, X, Top, ParapetThk + 22);
					if (Rng.FRand() < 0.55f && FarFromEdges(FVector2D(Spot.X, Spot.Y), 20))
					{
						FM80PropPlacement Prop;
						Prop.Prop = Rng.RandRange(0, In.NumProps - 1);
						Prop.Transform = FTransform(FRotator(0, Rng.FRandRange(0, 360), 0), Spot);
						Out.Props.Add(Prop);
					}
				}
			}
		}
		// Rooftop water tank on two concrete blocks, typical of 1970s-80s Sicily.
		if (Rng.FRand() < 0.55f)
		{
			const FVector2D Q = InteriorPoint(Rng.FRandRange(-1, 1) * Half * 0.5, Rng.FRandRange(-1, 1) * Half * 0.3);
			if (FarFromEdges(Q, 90))
			{
				const FVec Ax(RidgeDir.X, RidgeDir.Y, 0), Ay(Across.X, Across.Y, 0);
				const FVec C(Q.X, Q.Y, Top);
				for (double S : {-38.0, 38.0})
				{
					M.Box(M80Slot::Trim, C + Ax * S + Up * 12, Ax, Ay, Up, FVec(9, 30, 12));
				}
				M.ElementRandom = Rng.FRand();
				M.Tube(M80Slot::Iron, {C - Ax * 62 + Up * 66, C + Ax * 62 + Up * 66}, 42, 12, true);
				M.ElementRandom = 0;
			}
		}
		const int32 Antennas = Rng.FRand() < 0.85f ? 1 + Rng.RandRange(0, 2) : 0;
		for (int32 k = 0; k < Antennas; ++k)
		{
			const FVector2D Q = InteriorPoint(Rng.FRandRange(-1, 1) * Half * 0.6, Rng.FRandRange(-1, 1) * Half * 0.5);
			if (FarFromEdges(Q, 50))
			{
				EmitAntenna(Q, Top);
			}
		}
	}

	// ---------------------------------------------------------------- services

	void EmitDownpipes()
	{
		if (!H.bDownpipes || Roof == EM80RoofType::Terrace)
		{
			return;
		}
		for (int32 e = 0; e < E.Num(); ++e)
		{
			if (!IsStreet(e) || E[e].L < 250 || FMath::Abs(FVector2D::DotProduct(E[e].U, RidgeDir)) < 0.85 || WallTop(e, E[e].L * 0.5) > Top + 25)
			{
				continue;
			}
			TArray<double> Xs = {E[e].L - 32.0};
			if (E[e].L > 900)
			{
				Xs.Add(32.0);
			}
			for (double X : Xs)
			{
				bool bClear = true;
				for (const FOpening& O : Openings)
				{
					bClear &= !(O.Edge == e && X > O.X0 - R.FrameWidth - 30 && X < O.X1 + R.FrameWidth + 30);
				}
				if (!bClear)
				{
					continue;
				}
				const double Eave = WallTop(e, X);
				const double Reach = R.EaveOverhang - 8;
				const double Gz = GroundAt(e, X);
				M.ElementRandom = Rng.FRand();
				M.Tube(M80Slot::Iron, {W(e, X, Eave + 4, -Reach), W(e, X, Eave - R.CorniceHeight - 20, -Reach), W(e, X, Eave - R.CorniceHeight - 45, -7),
					W(e, X, Gz + 32, -7), W(e, X, Gz + 14, -17)}, 4.8, 8);
				for (double Z = Gz + 120; Z < Eave - R.CorniceHeight - 60; Z += 170)
				{
					M.WallBox(M80Slot::Iron, W(e, X, Z, -3.5), E[e].U3(), E[e].N3(), FVec(6, 3.5, 1.2), false);
				}
				M.ElementRandom = 0;
			}
		}
	}

	// ---------------------------------------------------------------- vegetation

	bool ClearOfOpenings(int32 e, double X0, double X1, double Z0, double Z1) const
	{
		for (const FOpening& O : Openings)
		{
			if (O.Edge == e && X1 > O.X0 - R.FrameWidth && X0 < O.X1 + R.FrameWidth && Z1 > O.Z0 - 20 && Z0 < O.Z1 + R.FrameWidth)
			{
				return false;
			}
		}
		return true;
	}

	/** A random Sicilian prop of a category; wall props get yaw so their front faces the street. */
	bool AddCat(int32 Cat, const FVec& Location, double Yaw)
	{
		if (In.CatCount[Cat] <= 0)
		{
			return false;
		}
		FM80PropPlacement Prop;
		Prop.Prop = In.CatFirst[Cat] + Rng.RandRange(0, In.CatCount[Cat] - 1);
		Prop.Transform = FTransform(FRotator(0, Yaw, 0), Location);
		Out.Props.Add(Prop);
		return true;
	}

	double WallYaw(int32 e) const { return FMath::RadiansToDegrees(FMath::Atan2(E[e].N.X, -E[e].N.Y)) + In.WallPropYaw; }
	double Sicily() const { return In.bAbandoned || In.bUnfinished ? 0.0 : FMath::Clamp(double(H.SicilyDetails), 0.0, 1.0); }

	/** Civic number, knocker, coat of arms, pots or Moor's heads at the sides, peppers by the main door. */
	void EmitSicilyDoor(const FOpening& O)
	{
		const double S = Sicily();
		const int32 e = O.Edge;
		if (S <= 0 || !IsStreet(e))
		{
			return;
		}
		const double Yaw = WallYaw(e), Fw = R.FrameWidth;
		if (Rng.FRand() < 0.8 * S && O.X1 + Fw + 30 < E[e].L)
		{
			AddCat(M80Cat::Civic, W(e, O.X1 + Fw + 18, O.Z0 + 175, -0.5), Yaw);
		}
		if (O.bArch && Rng.FRand() < 0.7 * S)
		{
			AddCat(M80Cat::Knocker, W(e, O.Mid() + O.Width() * 0.25, O.Z0 + 120, R.RevealDepth - 6.5), Yaw);
		}
		if (O.bArch && e == Front && Rng.FRand() < R.CrestChance)
		{
			AddCat(M80Cat::Crest, W(e, O.Mid(), O.TopAt(O.Mid()) + Fw + 12, -0.5), Yaw);
		}
		if (Rng.FRand() < 0.55 * S)
		{
			// The same pair on both sides, as people do.
			const int32 Cat = M80Cat::Doorside;
			if (In.CatCount[Cat] > 0)
			{
				const int32 Pick = In.CatFirst[Cat] + Rng.RandRange(0, In.CatCount[Cat] - 1);
				for (double X : {O.X0 - Fw - 26, O.X1 + Fw + 26})
				{
					if (X > 15 && X < E[e].L - 15)
					{
						FM80PropPlacement Prop;
						Prop.Prop = Pick;
						Prop.Transform = FTransform(FRotator(0, Yaw, 0), W(e, X, GroundAt(e, X), -24));
						Out.Props.Add(Prop);
					}
				}
			}
		}
		if (Rng.FRand() < 0.2 * S && O.X0 - Fw - 15 > 10)
		{
			AddCat(M80Cat::Hanging, W(e, O.X0 - Fw - 12, O.Z1 + 4, -2), Yaw);
		}
	}

	void AddPlant(int32 First, int32 Count, const FVec& Location, double Yaw, double Height, bool bStack = false)
	{
		if (Count <= 0)
		{
			return;
		}
		FM80PropPlacement Prop;
		Prop.Prop = First + Rng.RandRange(0, Count - 1);
		Prop.Transform = FTransform(FRotator(0, Yaw, 0), Location);
		Prop.TargetHeight = float(Height);
		Prop.bStack = bStack;
		Out.Props.Add(Prop);
	}

	/**
	 * Plants where they really grow on old Sicilian houses: weeds along the foot of the walls and in
	 * the corners, ivy climbing between the openings (more on back walls), capers in the cracks of
	 * stone walls and on top of parapets.
	 */
	void EmitVegetation()
	{
		const double D = FMath::Clamp(double(H.Vegetation), 0.0, 1.0);
		if (D <= 0)
		{
			return;
		}
		const int32 Climbers = In.NumProps;
		const int32 GroundPlants = Climbers + In.NumClimbers;
		const int32 WallPlants = GroundPlants + In.NumGroundPlants;
		const bool bStoneWall = In.WallSlot != M80Slot::WallPlaster;
		for (int32 e = 0; e < E.Num(); ++e)
		{
			if (!IsFacade(e) || E[e].L < 120)
			{
				continue;
			}
			const double OutYaw = FMath::RadiansToDegrees(FMath::Atan2(E[e].N.Y, E[e].N.X));
			const double Back = IsStreet(e) ? 1.0 : 1.8;

			// Foot of the wall: corners first, then sparse tufts where no door opens.
			for (double X = 25; X < E[e].L - 10; X += Rng.FRandRange(90, 170))
			{
				const bool bCorner = X < 60 || X > E[e].L - 60;
				const double Gz = GroundAt(e, X);
				if (Rng.FRand() < D * (bCorner ? 0.7 : 0.3) * Back && ClearOfOpenings(e, X - 35, X + 35, Gz, Gz + 60))
				{
					AddPlant(GroundPlants, In.NumGroundPlants, W(e, X, Gz - 4, -Rng.FRandRange(8, 22)), Rng.FRandRange(0, 360),
						Rng.FRandRange(35, 80) * (bCorner ? 1.4 : 1.0));
				}
			}

			// Ivy climbs from the ground up a strip free of windows.
			const int32 Tries = FMath::Max(1, FMath::RoundToInt(E[e].L / 400));
			for (int32 t = 0; t < Tries; ++t)
			{
				if (In.NumClimbers <= 0 || Rng.FRand() > D * 0.45 * Back)
				{
					continue;
				}
				const double X = Rng.FRand() < 0.5 ? (Rng.FRand() < 0.5 ? 45.0 : E[e].L - 45) : Rng.FRandRange(60, E[e].L - 60);
				const double Gz = GroundAt(e, X);
				const double Height = FMath::Max(150.0, (Top - Gz) * Rng.FRandRange(0.35, 0.95));
				if (ClearOfOpenings(e, X - 45, X + 45, Gz, Gz + Height))
				{
					// A patch of strands: tallest in the middle, fanning out.
					const int32 Strands = Rng.RandRange(7, 13);
					for (int32 k = 0; k < Strands; ++k)
					{
						const double Off = Rng.FRandRange(-55.f, 55.f);
						const double StrandX = FMath::Clamp(X + Off, 5.0, E[e].L - 5);
						AddPlant(Climbers, In.NumClimbers, W(e, StrandX, GroundAt(e, StrandX) - 5, -3 - k * 0.6),
							OutYaw + In.ClimberYaw + Rng.FRandRange(-8.f, 8.f), Height * (1.0 - FMath::Abs(Off) / 90.0) * Rng.FRandRange(0.7f, 1.0f), true);
					}
				}
			}

			// Capers in the cracks of stone walls, below the cornice.
			if (bStoneWall)
			{
				for (int32 t = 0; t < 3; ++t)
				{
					const double X = Rng.FRandRange(40, E[e].L - 40);
					const double Z = Rng.FRandRange(Floor0 + 80, Top - R.CorniceHeight - 40);
					if (Rng.FRand() < D * 0.4 * Back && Z > GroundAt(e, X) + 60 && ClearOfOpenings(e, X - 50, X + 50, Z - 50, Z + 50))
					{
						AddPlant(WallPlants, In.NumWallPlants, W(e, X, Z - 20, -6), OutYaw + Rng.FRandRange(-40, 40), Rng.FRandRange(30, 60));
					}
				}
			}

			// Grass and capers on top of terrace parapets.
			if (Roof == EM80RoofType::Terrace && Rng.FRand() < D * 0.5)
			{
				const double X = Rng.FRandRange(30, E[e].L - 30);
				AddPlant(WallPlants, In.NumWallPlants, W(e, X, ParapetTop(), ParapetThk * 0.5), Rng.FRandRange(0, 360), Rng.FRandRange(25, 45));
			}
		}
	}

	void EmitCables(int32 e)
	{
		if (!IsStreet(e) || E[e].L < 300)
		{
			return;
		}
		const double Z = Floor0 + H.GroundFloorHeight - 32;
		if (Z < GroundAt(e, E[e].L * 0.5) + 150)
		{
			return;
		}
		// A bundle of 1-3 power/phone cables clipped to the wall, each with its own sag.
		const double Span = 380;
		const int32 Spans = FMath::Max(1, FMath::RoundToInt((E[e].L - 20) / Span));
		const int32 Cables = Rng.RandRange(1, 3);
		for (int32 c = 0; c < Cables; ++c)
		{
			const double Zc = Z - c * 7;
			const double Sag = Rng.FRandRange(4.f, 14.f);
			TArray<FVec> Points;
			for (int32 s = 0; s < Spans; ++s)
			{
				for (int32 k = 0; k < 6; ++k)
				{
					const double T = double(k) / 6;
					const double X = 10 + (E[e].L - 20) * (s + T) / Spans;
					Points.Add(W(e, X, Zc - Sag * FMath::Sin(PI * T), -5 - c * 1.5));
				}
			}
			Points.Add(W(e, E[e].L - 10, Zc, -5 - c * 1.5));
			M.Tube(M80Slot::Iron, Points, c == 0 ? 0.8 : 0.55, 4);
		}
		for (int32 s = 0; s <= Spans; ++s)
		{
			const double X = 10 + (E[e].L - 20) * s / Spans;
			M.WallBox(M80Slot::Iron, W(e, X, Z + 2 - (Cables - 1) * 3.5, -3), E[e].U3(), E[e].N3(), FVec(1, 3, 1 + (Cables - 1) * 3.5), false);
			// Junction boxes where the line is tapped.
			if (s > 0 && s < Spans && Rng.FRand() < 0.35f && ClearOfOpenings(e, X - 20, X + 20, Z - 30, Z + 30))
			{
				M.ElementRandom = Rng.FRand();
				M.WallBox(M80Slot::Trim, W(e, X, Z - 12, -5), E[e].U3(), E[e].N3(), FVec(9, 5, 11), false);
				M.ElementRandom = 0;
			}
		}
		// A second, older line under the cornice on tall houses.
		const double Zt = Top - R.CorniceHeight - 18;
		if (Zt - Z > 200 && Rng.FRand() < 0.45f)
		{
			TArray<FVec> Points;
			for (int32 k = 0; k <= 12; ++k)
			{
				const double T = double(k) / 12;
				Points.Add(W(e, 15 + (E[e].L - 30) * T, Zt - 9 * FMath::Sin(PI * FMath::Frac(T * Spans)), -4));
			}
			M.Tube(M80Slot::Iron, Points, 0.6, 4);
			// Drop to the floor below near one end.
			const double Xd = Rng.FRand() < 0.5f ? 15.0 : E[e].L - 15;
			M.Tube(M80Slot::Iron, {W(e, Xd, Zt, -4), W(e, Xd, Z + 4, -5)}, 0.6, 4);
		}
		// Street lamp on a curved iron bracket, on some long street walls.
		if (E[e].L > 600 && !In.bAbandoned && Rng.FRand() < 0.35f)
		{
			const double Zl = Floor0 + H.GroundFloorHeight + 70;
			for (int32 t = 0; t < 4; ++t)
			{
				const double X = Rng.FRandRange(80, E[e].L - 80);
				if (Zl < Top - 40 && ClearOfOpenings(e, X - 40, X + 40, Zl - 60, Zl + 60))
				{
					M.ElementRandom = Rng.FRand();
					M.WallBox(M80Slot::Iron, W(e, X, Zl, -2), E[e].U3(), E[e].N3(), FVec(6, 2, 14), false);
					const FVec Tip = W(e, X, Zl + 18, -95);
					M.Tube(M80Slot::Iron, {W(e, X, Zl - 10, -2), W(e, X, Zl + 8, -40), W(e, X, Zl + 22, -75), Tip}, 1.6, 5);
					M.Tube(M80Slot::Iron, {W(e, X, Zl + 10, -2), W(e, X, Zl + 30, -30), W(e, X, Zl + 22, -70)}, 0.8, 4);
					M.Tube(M80Slot::Iron, {Tip, Tip - Up * 14}, 1.0, 4);
					M.Box(M80Slot::Iron, Tip - Up * 18, E[e].U3(), E[e].N3(), Up, FVec(17, 17, 4));
					{
						const float Keep = M.ElementRandom;
						M.ElementRandom = 0.f; // dark glass (room code 0)
						M.Box(M80Slot::Glass, Tip - Up * 27, E[e].U3(), E[e].N3(), Up, FVec(9, 9, 6));
						M.ElementRandom = Keep;
					}
					M.ElementRandom = 0;
					break;
				}
			}
		}
		// Front door gets the meter box and, often, a wall lantern.
		if (e == Front)
		{
			for (const FOpening& O : Openings)
			{
				if (O.Edge != e || O.Type != EOpen::Door)
				{
					continue;
				}
				const double Bx = O.X1 + R.FrameWidth + 40;
				if (Bx < E[e].L - 30)
				{
					M.WallBox(M80Slot::Trim, W(e, Bx, O.Z0 + 150, -6), E[e].U3(), E[e].N3(), FVec(16, 6, 22), false);
				}
				if (!In.bAbandoned && Rng.FRand() < 0.6f)
				{
					const double Lx = O.X0 - R.FrameWidth - 30;
					const FVec Base = W(e, Lx, O.Z1 + 45, 0);
					const FVec Tip = W(e, Lx, O.Z1 + 52, -42);
					M.Tube(M80Slot::Iron, {Base, W(e, Lx, O.Z1 + 70, -14), Tip}, 1.4, 5);
					{
						const float Keep = M.ElementRandom;
						M.ElementRandom = 0.f; // dark glass (room code 0)
						M.Box(M80Slot::Glass, Tip - Up * 18, E[e].U3(), E[e].N3(), Up, FVec(8, 8, 12));
						M.ElementRandom = Keep;
					}
					M.Box(M80Slot::Iron, Tip - Up * 4, E[e].U3(), E[e].N3(), Up, FVec(10, 10, 2.5));
				}
				if (In.NumProps > 0 && !In.bAbandoned)
				{
					for (double Side : {-1.0, 1.0})
					{
						if (Rng.FRand() < 0.45f)
						{
							const double X = Side < 0 ? O.X0 - R.FrameWidth - 30 : O.X1 + R.FrameWidth + 30;
							FM80PropPlacement Prop;
							Prop.Prop = Rng.RandRange(0, In.NumProps - 1);
							Prop.Transform = FTransform(FRotator(0, Rng.FRandRange(0, 360), 0), W(e, X, GroundAt(e, X), -28));
							Out.Props.Add(Prop);
						}
					}
				}
			}
		}
	}
};
}

void M80BuildHouse(const FM80BuildInput& In, FM80BuildOutput& Out)
{
	Out = FM80BuildOutput();
	if (In.Footprint.Num() < 3)
	{
		return;
	}
	FBuilder(In, Out).Run();
}

void M80BuildCourtWall(const FVector2D& A, const FVector2D& B, const FVector2D& Outward,
	const TFunction<double(const FVector2D&)>& Ground, int32 WallSlot, bool bGate, int32 Seed, const FVector2f& UnitData, FM80MeshBuffer& M)
{
	const double L = FVector2D::Distance(A, B);
	if (L < 60)
	{
		return;
	}
	FRandomStream Rng(Seed);
	const FVector2D U = (B - A) / L;
	const FVector3d U3(U.X, U.Y, 0), N3(Outward.X, Outward.Y, 0);
	const double Thick = 34, Height = Rng.FRandRange(240.f, 300.f);
	const double GateW = bGate ? FMath::Min(260.0, L - 120) : 0;
	const double Gx0 = (L - GateW) * 0.5, Gx1 = Gx0 + GateW;
	const bool bHasGate = bGate && GateW >= 160;
	M.Ground = Ground;
	M.CurrentUnit = UnitData;
	auto At = [&](double X, double Z, double D) { const FVector2D Q = A + U * X - Outward * D; return FVector3d(Q.X, Q.Y, Z); };
	auto G = [&](double X) { return Ground(A + U * X); };

	// Wall pieces stepping with the ground; coping on top.
	const int32 Pieces = FMath::Max(1, FMath::CeilToInt(L / 120));
	for (int32 i = 0; i < Pieces; ++i)
	{
		double X0 = L * i / Pieces, X1 = L * (i + 1) / Pieces;
		TArray<TPair<double, double>> Spans;
		if (bHasGate && X1 > Gx0 && X0 < Gx1)
		{
			if (X0 < Gx0) Spans.Add({X0, Gx0});
			if (X1 > Gx1) Spans.Add({Gx1, X1});
		}
		else
		{
			Spans.Add({X0, X1});
		}
		for (const TPair<double, double>& S : Spans)
		{
			const double Xm = (S.Key + S.Value) * 0.5, Hw = (S.Value - S.Key) * 0.5;
			const double Gz = FMath::Min(G(S.Key), G(S.Value)) - 15;
			const double Top = FMath::Max(G(S.Key), G(S.Value)) + Height;
			M.FacadeMask = 1.f;
			M.Box(WallSlot, At(Xm, (Gz + Top) * 0.5, Thick * 0.5), U3, N3, Up, FVector3d(Hw, Thick * 0.5, (Top - Gz) * 0.5));
			M.FacadeMask = 0.f;
			M.Box(M80Slot::Trim, At(Xm, Top + 3, Thick * 0.5), U3, N3, Up, FVector3d(Hw + 1, Thick * 0.5 + 4, 3));
		}
	}
	if (!bHasGate)
	{
		return;
	}
	// Arched gateway: pilasters, voussoirs, wall above, iron gate.
	const double Gm = (Gx0 + Gx1) * 0.5, Gz = FMath::Min(G(Gx0), G(Gx1)), R = GateW * 0.5;
	const double Spring = Gz + 230, Crown = Spring + R + 60;
	for (double X : {Gx0 - 22.0, Gx1 + 22.0})
	{
		M.Box(M80Slot::Trim, At(X, (Gz - 15 + Spring) * 0.5, Thick * 0.5), U3, N3, Up, FVector3d(22, Thick * 0.5 + 6, (Spring - Gz + 15) * 0.5));
	}
	const int32 Stones = 11;
	for (int32 k = 0; k < Stones; ++k)
	{
		const double Ang = PI * (k + 0.5) / Stones;
		const FVector3d Dir = U3 * -FMath::Cos(Ang) + Up * FMath::Sin(Ang);
		const FVector3d C = At(Gm, Spring, Thick * 0.5) + Dir * (R + 16);
		const FVector3d Tang = (U3 * FMath::Sin(Ang) + Up * FMath::Cos(Ang)).GetSafeNormal();
		M.Box(M80Slot::Trim, C, Tang, N3, Dir, FVector3d(R * PI / Stones * 0.5 + 1, Thick * 0.5 + 6, 16));
	}
	// Wall filling the corners above the arch, up to the crown.
	M.FacadeMask = 1.f;
	for (double Side : {-1.0, 1.0})
	{
		const double Xc = Gm + Side * R * 0.62;
		const double Zb = Spring + R * 0.62;
		M.Box(WallSlot, At(Xc, (Zb + Crown) * 0.5, Thick * 0.5), U3, N3, Up, FVector3d(R * 0.38 + 22, Thick * 0.5, (Crown - Zb) * 0.5));
	}
	M.Box(WallSlot, At(Gm, (Spring + R + 16 + Crown) * 0.5, Thick * 0.5), U3, N3, Up, FVector3d(R * 0.3, Thick * 0.5, (Crown - Spring - R - 16) * 0.5 + 1));
	M.FacadeMask = 0.f;
	M.Box(M80Slot::Trim, At(Gm, Crown + 4, Thick * 0.5), U3, N3, Up, FVector3d(R + 50, Thick * 0.5 + 6, 4));
	// Iron gate: two leaves of bars under the arch.
	M.ElementRandom = Rng.FRand();
	for (double X = Gx0 + 6; X < Gx1 - 4; X += 11)
	{
		const double D = X - Gm;
		const double TopZ = Spring + FMath::Sqrt(FMath::Max(0.0, R * R - D * D)) - 6;
		M.Tube(M80Slot::Iron, {At(X, Gz, Thick * 0.5), At(X, TopZ, Thick * 0.5)}, 0.9, 4);
	}
	for (double Z : {Gz + 20, Gz + 110, Spring - 10})
	{
		M.Tube(M80Slot::Iron, {At(Gx0 + 2, Z, Thick * 0.5), At(Gx1 - 2, Z, Thick * 0.5)}, 1.3, 4);
	}
	M.ElementRandom = 0;
}
