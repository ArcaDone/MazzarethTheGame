#include "MazzarinoHistoricBuilding.h"
#include "MazzarinoRoadSpline.h"
#include "Components/SplineComponent.h"
#include "Components/SplineMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/TextRenderComponent.h"
#include "ProceduralMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "UObject/ConstructorHelpers.h"
#include "Algo/Reverse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"

namespace {
using P2=FVector2D;
double Cross(P2 A,P2 B,P2 C){return (B.X-A.X)*(C.Y-A.Y)-(B.Y-A.Y)*(C.X-A.X);}
bool Inside(const TArray<P2>& P,P2 Q){bool R=false;for(int i=0,j=P.Num()-1;i<P.Num();j=i++)if((P[i].Y>Q.Y)!=(P[j].Y>Q.Y)&&Q.X<(P[j].X-P[i].X)*(Q.Y-P[i].Y)/(P[j].Y-P[i].Y)+P[i].X)R=!R;return R;}
void Clean(TArray<P2>& P){for(int i=P.Num()-1;i>=0&&P.Num()>2;--i)if((P[i]-P[(i+1)%P.Num()]).Size()<.1)P.RemoveAt(i);bool Changed=true;while(Changed&&P.Num()>3){Changed=false;for(int i=0;i<P.Num();++i)if(FMath::Abs(Cross(P[(i+P.Num()-1)%P.Num()],P[i],P[(i+1)%P.Num()]))<.05){P.RemoveAt(i);Changed=true;break;}}}
bool Triangulate(const TArray<P2>& P,TArray<int>& T){TArray<int>I;for(int i=0;i<P.Num();++i)I.Add(i);int Guard=P.Num()*P.Num();while(I.Num()>3&&--Guard>0){bool Found=false;for(int j=0;j<I.Num();++j){int a=I[(j+I.Num()-1)%I.Num()],b=I[j],c=I[(j+1)%I.Num()];if(Cross(P[a],P[b],P[c])<=.05)continue;bool Hit=false;for(int k:I)if(k!=a&&k!=b&&k!=c&&Cross(P[a],P[b],P[k])>=-.01&&Cross(P[b],P[c],P[k])>=-.01&&Cross(P[c],P[a],P[k])>=-.01){Hit=true;break;}if(!Hit){T.Append({a,b,c});I.RemoveAt(j);Found=true;break;}}if(!Found)return false;}if(I.Num()==3)T.Append(I);return I.Num()==3;}
TArray<P2> Clip(const TArray<P2>& P,P2 N,double Cut,bool Low){TArray<P2>Q;for(int i=0;i<P.Num();++i){P2 A=P[i],B=P[(i+1)%P.Num()];double da=FVector2D::DotProduct(A,N)-Cut,db=FVector2D::DotProduct(B,N)-Cut;bool ia=Low?da<=0:da>=0,ib=Low?db<=0:db>=0;if(ia)Q.Add(A);if(ia!=ib)Q.Add(A+(B-A)*(da/(da-db)));}Clean(Q);return Q;}
double EdgeDistance(P2 Q,P2 A,P2 B){P2 D=B-A;double T=FMath::Clamp(FVector2D::DotProduct(Q-A,D)/FMath::Max(1.,D.SizeSquared()),0.,1.);return (Q-A-D*T).Size();}
struct Mesh {
    TArray<FVector> V,N;TArray<int32>T;TArray<FVector2D>UV;TArray<FProcMeshTangent>Tan;
    void Tri(FVector A,FVector B,FVector C,FVector2D Ua,FVector2D Ub,FVector2D Uc){FVector E1=B-A,E2=C-A,Cr=FVector::CrossProduct(E1,E2);if(Cr.SizeSquared()<.01)return;FVector2D D1=Ub-Ua,D2=Uc-Ua;double Det=D1.X*D2.Y-D1.Y*D2.X;FVector Tangent=FMath::Abs(Det)>1.e-8?((E1*D2.Y-E2*D1.Y)/Det).GetSafeNormal():E1.GetSafeNormal();int s=V.Num();V.Append({A,B,C});T.Append({s,s+2,s+1});FVector Normal=Cr.GetSafeNormal();for(int i=0;i<3;++i){N.Add(Normal);Tan.Add(FProcMeshTangent(Tangent,false));}UV.Append({Ua,Ub,Uc});}
    void Quad(FVector A,FVector B,FVector C,FVector D,double Scale=180.,FVector Desired=FVector::ZeroVector,bool ContinuousUV=false){double W=(B-A).Size()/Scale,H=(D-A).Size()/Scale;FVector2D Ua(0,0),Ub(W,0),Uc(W,H),Ud(0,H);if(ContinuousUV&&!Desired.IsNearlyZero()){FVector Along(-Desired.Y,Desired.X,0);auto Project=[&](FVector P){return FVector2D(FVector::DotProduct(P,Along)/Scale,P.Z/Scale);};Ua=Project(A);Ub=Project(B);Uc=Project(C);Ud=Project(D);}if(!Desired.IsNearlyZero()&&FVector::DotProduct(FVector::CrossProduct(B-A,C-A),Desired)<0){Tri(A,C,B,Ua,Uc,Ub);Tri(A,D,C,Ua,Ud,Uc);}else{Tri(A,B,C,Ua,Ub,Uc);Tri(A,C,D,Ua,Uc,Ud);}}
    void Save(UProceduralMeshComponent* C,int Index,UMaterialInterface* Mat,bool Collision=true){if(V.IsEmpty())return;TArray<FLinearColor>Colors;C->CreateMeshSection_LinearColor(Index,V,T,N,UV,Colors,Tan,Collision);C->SetMaterial(Index,Mat);}
};
// A half-plane clip of a concave lot can produce multiple disconnected lobes.
// Split boundary edges at all collinear vertices and cancel opposite bridges.
TArray<TArray<P2>> SimpleLoops(const TArray<P2>& P){
    TArray<P2>Points;for(auto Q:P)if(!Points.ContainsByPredicate([&](P2 A){return (A-Q).Size()<.1;}))Points.Add(Q);
    TArray<TPair<int,int>>Edges;
    for(int i=0;i<P.Num();++i){P2 A=P[i],B=P[(i+1)%P.Num()],D=B-A;if(D.Size()<.1)continue;TArray<TPair<double,int>>Cuts;
        for(int j=0;j<Points.Num();++j){double t=FVector2D::DotProduct(Points[j]-A,D)/D.SizeSquared();if(t>=-.000001&&t<=1.000001&&EdgeDistance(Points[j],A,B)<.1)Cuts.Add({t,j});}
        Cuts.Sort([](auto a,auto b){return a.Key<b.Key;});for(int j=0;j+1<Cuts.Num();++j){int a=Cuts[j].Value,b=Cuts[j+1].Value;if(a==b)continue;int Other=Edges.IndexOfByPredicate([&](auto e){return e.Key==b&&e.Value==a;});if(Other!=INDEX_NONE)Edges.RemoveAt(Other);else if(!Edges.ContainsByPredicate([&](auto e){return e.Key==a&&e.Value==b;}))Edges.Add({a,b});}}
    TArray<TArray<P2>>Result;while(!Edges.IsEmpty()){auto Edge=Edges.Pop();int Start=Edge.Key,Current=Edge.Value;TArray<P2>Loop={Points[Start]};int Guard=Points.Num()*3;while(Current!=Start&&--Guard>0){Loop.Add(Points[Current]);int Next=Edges.IndexOfByPredicate([&](auto e){return e.Key==Current;});if(Next==INDEX_NONE)break;Current=Edges[Next].Value;Edges.RemoveAt(Next);}if(Current==Start){Clean(Loop);if(Loop.Num()>=3)Result.Add(Loop);}}
    return Result;
}
struct Volume {TArray<P2>P;int Floors=2;double Base=0,Rise=0,RidgeAlpha=.5;bool Terrace=false,Upper=false,Shed=false;};
struct Opening {double X=0,W=80,Z=0,H=110;bool Door=false,Balcony=false,French=false,Arch=false,Blocked=false,DamageHole=false;double ArchTop(double D)const{return Arch?H-W*.5+FMath::Sqrt(FMath::Max(0.,W*W*.25-D*D)):H;}};
void Box(UInstancedStaticMeshComponent* C,FVector P,FVector E,FVector S){if(S.GetMin()<=.01)return;C->AddInstance(FTransform(FRotator(0,FMath::RadiansToDegrees(FMath::Atan2(E.Y,E.X)),0),P,S/100.));}
// Round iron profiles keep railings legible close to the player.
void Tube(Mesh& M,const TArray<FVector>& Points,double Radius,int Sides=8){
    for(int i=0;i+1<Points.Num();++i){FVector A=Points[i],B=Points[i+1],D=(B-A).GetSafeNormal();if((B-A).Size()<.01)continue;FVector U=FVector::CrossProduct(D,FMath::Abs(D.Z)>.9?FVector::RightVector:FVector::UpVector).GetSafeNormal(),V=FVector::CrossProduct(D,U);
        for(int k=0;k<Sides;++k){FVector R0=(U*FMath::Cos(2*PI*k/Sides)+V*FMath::Sin(2*PI*k/Sides))*Radius,R1=(U*FMath::Cos(2*PI*(k+1)/Sides)+V*FMath::Sin(2*PI*(k+1)/Sides))*Radius;M.Quad(A+R0,B+R0,B+R1,A+R1,40.,(R0+R1).GetSafeNormal());M.Tri(A,A+R1,A+R0,{0,0},{0,1},{1,0});M.Tri(B,B+R0,B+R1,{0,0},{0,1},{1,0});}}
}
void Corbel(Mesh& M,FVector C,FVector E,FVector O,double Depth,double Width){
    const TArray<FVector2D> Profile={{0,0},{Depth,0},{Depth,-7},{Depth*.85,-10},{Depth*.62,-12},{Depth*.49,-18},{Depth*.37,-28},{Depth*.16,-34},{0,-34}};
    auto Point=[&](int i,double Side){return C+E*Side+O*Profile[i].X+FVector(0,0,Profile[i].Y);};
    for(int i=0;i<Profile.Num();++i){int j=(i+1)%Profile.Num();M.Quad(Point(i,-Width*.5),Point(j,-Width*.5),Point(j,Width*.5),Point(i,Width*.5));}
    // The profile is concave: ear-clip the two ends instead of a fan.
    TArray<P2> Poly=Profile;Algo::Reverse(Poly);TArray<int> Idx;if(Triangulate(Poly,Idx))for(int i=0;i<Idx.Num();i+=3){auto Map=[&](int j,double s){return C+E*s+O*Poly[j].X+FVector(0,0,Poly[j].Y);};M.Tri(Map(Idx[i],-Width*.5),Map(Idx[i+1],-Width*.5),Map(Idx[i+2],-Width*.5),{0,0},{1,0},{0,1});M.Tri(Map(Idx[i],Width*.5),Map(Idx[i+2],Width*.5),Map(Idx[i+1],Width*.5),{0,0},{0,1},{1,0});}
}
void Module(UInstancedStaticMeshComponent* C,UStaticMesh* Mesh,FVector Center,FVector Edge,FVector Out,double Width,double Height){if(!Mesh)return;FBoxSphereBounds B=Mesh->GetBounds();FVector Size=B.BoxExtent*2;if(Size.Z<.01)return;bool NormalX=Size.X<Size.Y;FVector X=NormalX?Out:-Edge,Y=NormalX?Edge:Out;FMatrix Matrix=FMatrix::Identity;Matrix.SetAxes(&X,&Y,&FVector::UpVector);FQuat Rotation(Matrix);FVector Scale=NormalX?FVector(1,Width/Size.Y,Height/Size.Z):FVector(Width/Size.X,1,Height/Size.Z);C->AddInstance(FTransform(Rotation,Center-Rotation.RotateVector(B.Origin*Scale),Scale));}
}

AMazzarinoHistoricBuilding::AMazzarinoHistoricBuilding(){
    PrimaryActorTick.bCanEverTick=false;
    Footprint=CreateDefaultSubobject<USplineComponent>(TEXT("Lotto_originale"));SetRootComponent(Footprint);Footprint->SetClosedLoop(true);Footprint->bInputSplinePointsToConstructionScript=true;
    Surface=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("Volumi_aperture_tetti"));Surface->SetupAttachment(Footprint);Surface->bUseComplexAsSimpleCollision=true;
    StoneDetails=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Pietra_soglie_balconi"));
    IronDetails=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Ferro_ringhiere"));
    WoodDetails=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Legno_portoni_persiane"));
    GlassDetails=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Vetri_incassati"));
    StreetDetails=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Canalette_riparazioni"));
    LifeDetails=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Vita_quotidiana"));
    DoorPanels=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Portoni_recuperati"));DoorPanels->SetupAttachment(Footprint);DoorPanels->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Pots=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Vasi_recuperati"));Pots->SetupAttachment(Footprint);Pots->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    HangingClothes=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Bucato_indumenti"));HangingClothes->SetupAttachment(Footprint);HangingClothes->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    RoofTiles=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Coppi_tridimensionali"));RoofTiles->SetupAttachment(Footprint);RoofTiles->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    BalconyModules=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Balconi_completi"));BalconyModules->SetupAttachment(Footprint);BalconyModules->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    static ConstructorHelpers::FObjectFinder<UStaticMesh>Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh>Clothes(TEXT("/Game/Megapack/Meshes/MiddleEast/SM_clothes_A_01.SM_clothes_A_01"));
    HangingClothesMesh=Clothes.Object;
    for(auto* C:{StoneDetails.Get(),IronDetails.Get(),WoodDetails.Get(),GlassDetails.Get(),StreetDetails.Get(),LifeDetails.Get()}){C->SetupAttachment(Footprint);C->SetStaticMesh(Cube.Object);C->SetCollisionEnabled(ECollisionEnabled::NoCollision);}
    StoneDetails->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
}
uint32 AMazzarinoHistoricBuilding::ServiceHash() const{
    uint32 H=0;TInlineComponentArray<USplineComponent*> Paths(this);for(auto* S:Paths)if(S->ComponentHasTag(TEXT("M80ServicePath"))){H=HashCombine(H,GetTypeHash(S->GetFName()));for(int i=0;i<S->GetNumberOfSplinePoints();++i){H=HashCombine(H,GetTypeHash(S->GetLocationAtSplinePoint(i,ESplineCoordinateSpace::Local)));H=HashCombine(H,GetTypeHash(S->GetTangentAtSplinePoint(i,ESplineCoordinateSpace::Local)));}}return H;
}
void AMazzarinoHistoricBuilding::ResetServiceSplines(){TInlineComponentArray<USplineComponent*> Paths(this);for(auto* S:Paths)if(S->ComponentHasTag(TEXT("M80ServicePath"))){RemoveInstanceComponent(S);S->DestroyComponent();}RebuildHouse();MarkPackageDirty();}

TArray<FString> AMazzarinoHistoricBuilding::ExportPCGSurfaceSections(const FString& OutputDirectory)
{
    TArray<FString> Exported;
    if (!Surface || LotId.IsEmpty()) return Exported;
    IFileManager::Get().MakeDirectory(*OutputDirectory, true);
    for (int32 SectionIndex = 0; SectionIndex < Surface->GetNumSections(); ++SectionIndex)
    {
        const FProcMeshSection* Section = Surface->GetProcMeshSection(SectionIndex);
        if (!Section || Section->ProcVertexBuffer.IsEmpty() || Section->ProcIndexBuffer.IsEmpty()) continue;
        FString Obj = FString::Printf(TEXT("o M80_%s_S%d\n"), *LotId, SectionIndex);
        for (const FProcMeshVertex& Vertex : Section->ProcVertexBuffer)
            Obj += FString::Printf(TEXT("v %.6f %.6f %.6f\n"), Vertex.Position.X, -Vertex.Position.Y, Vertex.Position.Z);
        for (const FProcMeshVertex& Vertex : Section->ProcVertexBuffer)
            Obj += FString::Printf(TEXT("vt %.7f %.7f\n"), Vertex.UV0.X, Vertex.UV0.Y);
        for (const FProcMeshVertex& Vertex : Section->ProcVertexBuffer)
            Obj += FString::Printf(TEXT("vn %.7f %.7f %.7f\n"), Vertex.Normal.X, -Vertex.Normal.Y, Vertex.Normal.Z);
        for (int32 Index = 0; Index + 2 < Section->ProcIndexBuffer.Num(); Index += 3)
        {
            const int32 A = Section->ProcIndexBuffer[Index] + 1;
            const int32 B = Section->ProcIndexBuffer[Index + 1] + 1;
            const int32 C = Section->ProcIndexBuffer[Index + 2] + 1;
            Obj += FString::Printf(TEXT("f %d/%d/%d %d/%d/%d %d/%d/%d\n"), A, A, A, B, B, B, C, C, C);
        }
        const FString Path = FPaths::Combine(OutputDirectory, FString::Printf(TEXT("Surface_%s_S%d.obj"), *LotId, SectionIndex));
        if (FFileHelper::SaveStringToFile(Obj, *Path)) Exported.Add(Path);
    }
    return Exported;
}
void AMazzarinoHistoricBuilding::ServiceSpline(FName Name,const TArray<FVector>& Points,double Radius,bool Cable){
    USplineComponent* Path=nullptr;TInlineComponentArray<USplineComponent*> Paths(this);for(auto* S:Paths)if(S->GetFName()==Name&&S->ComponentHasTag(TEXT("M80ServicePath")))Path=S;
    bool Fresh=!Path;if(!Path){Path=NewObject<USplineComponent>(this,Name,RF_Transactional);Path->CreationMethod=EComponentCreationMethod::Instance;Path->ComponentTags.Add(TEXT("M80ServicePath"));Path->SetupAttachment(Footprint);Path->bInputSplinePointsToConstructionScript=true;AddInstanceComponent(Path);Path->RegisterComponent();}
    Path->ComponentTags.AddUnique(TEXT("M80ServiceUsed"));
    if(Fresh||!bPreserveServiceSplines){Path->ClearSplinePoints(false);for(FVector P:Points)Path->AddSplinePoint(P,ESplineCoordinateSpace::Local,false);for(int i=0;i<Path->GetNumberOfSplinePoints();++i)Path->SetSplinePointType(i,ESplinePointType::CurveClamped,false);Path->UpdateSpline();}
    UStaticMesh* Cylinder=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));UStaticMesh* Asset=Cable&&CableMesh?CableMesh.Get():Cylinder;if(!Asset)return;
    double UnitRadius=Cable&&CableMesh?FMath::Max(Asset->GetBounds().BoxExtent.Y,Asset->GetBounds().BoxExtent.Z):50.;
    for(int i=0;i+1<Path->GetNumberOfSplinePoints();++i){auto* Piece=NewObject<USplineMeshComponent>(this,NAME_None,RF_Transactional);Piece->CreationMethod=EComponentCreationMethod::Instance;Piece->ComponentTags.Add(TEXT("M80ServiceMesh"));Piece->SetupAttachment(Path);Piece->SetMobility(EComponentMobility::Movable);Piece->SetStaticMesh(Asset);Piece->SetCollisionEnabled(ECollisionEnabled::NoCollision);Piece->SetForwardAxis(Cable&&CableMesh?ESplineMeshAxis::X:ESplineMeshAxis::Z,false);Piece->SetSplineUpDir(Cable?FVector::UpVector:FVector::ForwardVector,false);Piece->SetStartScale(FVector2D(Radius/UnitRadius),false);Piece->SetEndScale(FVector2D(Radius/UnitRadius),false);Piece->SetStartAndEnd(Path->GetLocationAtSplinePoint(i,ESplineCoordinateSpace::Local),Path->GetTangentAtSplinePoint(i,ESplineCoordinateSpace::Local),Path->GetLocationAtSplinePoint(i+1,ESplineCoordinateSpace::Local),Path->GetTangentAtSplinePoint(i+1,ESplineCoordinateSpace::Local),false);Piece->SetMaterial(0,bGrayPreview?GrayMaterial.Get():IronMaterial.Get());AddInstanceComponent(Piece);Piece->RegisterComponent();Piece->UpdateMesh();}
}
void AMazzarinoHistoricBuilding::OnConstruction(const FTransform& T){AActor::OnConstruction(T);RegisterSupportTicker();UpdateSupport();RebuildHouse();}
void AMazzarinoHistoricBuilding::PostLoad(){Super::PostLoad();RegisterSupportTicker();}
void AMazzarinoHistoricBuilding::BeginDestroy(){if(SupportTicker.IsValid())FTSTicker::GetCoreTicker().RemoveTicker(SupportTicker);Super::BeginDestroy();}
void AMazzarinoHistoricBuilding::RegisterSupportTicker(){
    if(IsTemplate()||SupportTicker.IsValid())return;
    TWeakObjectPtr<AMazzarinoHistoricBuilding> Weak(this);
    SupportTicker=FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Weak](float){auto* A=Weak.Get();if(!A)return false;if(A->GetWorld()&&A->GetWorld()->WorldType==EWorldType::Editor&&A->bFollowSupports&&!A->bBuilding&&!A->IsActorBeingDestroyed())A->UpdateSupport();return true;}),1.f);
}
double AMazzarinoHistoricBuilding::GroundZ(const P2& Q)const{
    FVector W=GetActorTransform().TransformPosition(FVector(Q.X,Q.Y,0));double Result=GetActorLocation().Z-EntranceLift*100.;bool Found=false;
    if(GroundActor){TInlineComponentArray<UPrimitiveComponent*>Cs(GroundActor);FCollisionQueryParams Params(SCENE_QUERY_STAT(M80Support),true);for(auto* C:Cs){FHitResult H;if(C->LineTraceComponent(H,FVector(W.X,W.Y,W.Z+20000),FVector(W.X,W.Y,W.Z-20000),Params)){Result=Found?FMath::Max(Result,H.ImpactPoint.Z):H.ImpactPoint.Z;Found=true;}}}
    if(EntranceRoad&&EntranceRoad->Spline){FVector R=EntranceRoad->Spline->FindLocationClosestToWorldLocation(W,ESplineCoordinateSpace::World);if(FVector2D::Distance(P2(W.X,W.Y),P2(R.X,R.Y))<=EntranceRoad->WidthMeters*50.+60){Result=Found?FMath::Max(Result,R.Z):R.Z;Found=true;}}
    return Result-GetActorLocation().Z;
}
void AMazzarinoHistoricBuilding::UpdateSupport(){
    if(bBuilding||!bFollowSupports||!GetWorld()||Footprint->GetNumberOfSplinePoints()<3)return;
    bool Changed=ServiceHash()!=LastServiceHash;FRotator Rotation=GetActorRotation();if(FMath::Abs(Rotation.Pitch)>.001||FMath::Abs(Rotation.Roll)>.001){SetActorRotation(FRotator(0,Rotation.Yaw,0));Changed=true;}
    FVector Scale=GetActorScale3D();if(!Scale.Equals(FVector::OneVector,.0001)){SetActorScale3D(FVector::OneVector);Changed=true;}
    const int Count=Footprint->GetNumberOfSplinePoints();int F=(FrontEdge%Count+Count)%Count;
    FVector A=Footprint->GetLocationAtSplinePoint(F,ESplineCoordinateSpace::World),B=Footprint->GetLocationAtSplinePoint((F+1)%Count,ESplineCoordinateSpace::World),W=(A+B)*.5;
    double Target=GetActorLocation().Z;
    if(EntranceRoad&&EntranceRoad->Spline){Target=EntranceRoad->Spline->FindLocationClosestToWorldLocation(W,ESplineCoordinateSpace::World).Z+EntranceLift*100.;if(GroundActor){P2 Q=P2(Footprint->GetLocationAtSplinePoint(F,ESplineCoordinateSpace::Local))*.5+P2(Footprint->GetLocationAtSplinePoint((F+1)%Count,ESplineCoordinateSpace::Local))*.5;Target=FMath::Max(Target,GetActorLocation().Z+GroundZ(Q)+EntranceLift*100.);}}
    else if(GroundActor){P2 Q= P2(Footprint->GetLocationAtSplinePoint(F,ESplineCoordinateSpace::Local))*.5+P2(Footprint->GetLocationAtSplinePoint((F+1)%Count,ESplineCoordinateSpace::Local))*.5;Target+=GroundZ(Q)+EntranceLift*100.;}
    if(FMath::Abs(Target-GetActorLocation().Z)>.5){FVector L=GetActorLocation();L.Z=Target;SetActorLocation(L);Changed=true;}
    TArray<double>Heights;for(int i=0;i<Count;++i){FVector Q=Footprint->GetLocationAtSplinePoint(i,ESplineCoordinateSpace::Local);double Z=GroundZ(P2(Q.X,Q.Y));Heights.Add(Z);if(i>=LastSupportHeights.Num()||FMath::Abs(Z-LastSupportHeights[i])>1.)Changed=true;}
    LastSupportHeights=Heights;if(Changed){++SupportRevision;RebuildHouse();MarkPackageDirty();}
}

void AMazzarinoHistoricBuilding::RebuildHouse(){
    if(bBuilding)return;TGuardValue<bool> Guard(bBuilding,true);
    GeometryError.Empty();GeneratedVolumes=GeneratedOpenings=GeneratedBalconies=0;Surface->ClearAllMeshSections();
    for(auto* C:{StoneDetails.Get(),IronDetails.Get(),WoodDetails.Get(),GlassDetails.Get(),StreetDetails.Get(),LifeDetails.Get()})C->ClearInstances();
    DoorPanels->ClearInstances();DoorPanels->SetStaticMesh(DoorMesh);Pots->ClearInstances();Pots->SetStaticMesh(PotMesh);
    HangingClothes->ClearInstances();HangingClothes->SetStaticMesh(HangingClothesMesh);
    RoofTiles->InstancingRandomSeed=Seed;RoofTiles->ClearInstances();RoofTiles->SetStaticMesh(RoofTileMesh);RoofTiles->SetVisibility(bShowRoofs&&bShowRoofTiles);
    BalconyModules->ClearInstances();BalconyModules->SetStaticMesh(BalconyModuleMesh);
    TInlineComponentArray<USplineMeshComponent*> Services(this);for(auto* C:Services)if(C->ComponentHasTag(TEXT("M80ServiceMesh"))){RemoveInstanceComponent(C);C->DestroyComponent();}
    TInlineComponentArray<USplineComponent*> Paths(this);for(auto* S:Paths)S->ComponentTags.Remove(TEXT("M80ServiceUsed"));
    for(auto* C:{DoorPanels.Get(),Pots.Get(),HangingClothes.Get()}){C->EmptyOverrideMaterials();if(bGrayPreview&&GrayMaterial)for(int i=0;i<C->GetNumMaterials();++i)C->SetMaterial(i,GrayMaterial);}
    BalconyModules->EmptyOverrideMaterials();if(bGrayPreview&&GrayMaterial)for(int i=0;i<BalconyModules->GetNumMaterials();++i)BalconyModules->SetMaterial(i,GrayMaterial);
    TInlineComponentArray<UTextRenderComponent*>Texts(this);for(auto* T:Texts)if(T->ComponentHasTag(TEXT("M80GeneratedNumber")))T->DestroyComponent();
    TArray<P2>Original;for(int i=0;i<Footprint->GetNumberOfSplinePoints();++i){auto V=Footprint->GetLocationAtSplinePoint(i,ESplineCoordinateSpace::Local);Original.Add(P2(V.X,V.Y));}
    if(Original.Num()<3){GeometryError=TEXT("Servono almeno tre punti del lotto");return;}
    int F=(FrontEdge%Original.Num()+Original.Num())%Original.Num();P2 FrontMid=(Original[F]+Original[(F+1)%Original.Num()])*.5;
    P2 Along=(Original[(F+1)%Original.Num()]-Original[F]).GetSafeNormal(),In(-Along.Y,Along.X);
    TArray<P2>P=Original;Clean(P);double Area=0;for(int i=0;i<P.Num();++i)Area+=Cross(P2::ZeroVector,P[i],P[(i+1)%P.Num()]);if(Area<0){Algo::Reverse(P);In=-In;}
    TArray<int>Test;if(!Triangulate(P,Test)){GeometryError=TEXT("Lotto incrociato o non triangolabile");return;}
    double S0=MAX_dbl,S1=-MAX_dbl,T0=MAX_dbl,T1=-MAX_dbl;for(P2 Q:P){double s=FVector2D::DotProduct(Q,Along),t=FVector2D::DotProduct(Q,In);S0=FMath::Min(S0,s);S1=FMath::Max(S1,s);T0=FMath::Min(T0,t);T1=FMath::Max(T1,t);}double Width=S1-S0,Depth=T1-T0;
    FRandomStream Rand(Seed);ResolvedFamily=Family;
    if(Family==EM80HouseFamily::Automatic){TArray<TPair<EM80HouseFamily,double>>Weights={{EM80HouseFamily::Popular,32},{EM80HouseFamily::Narrow,24},{EM80HouseFamily::Corner,12},{EM80HouseFamily::Courtyard,Width>850&&Depth>750?10.:0.},{EM80HouseFamily::Extended,16},{EM80HouseFamily::Palazzetto,6}};double Total=0;for(auto& W:Weights){if(W.Key==PreviousFamily)W.Value*=.15;Total+=W.Value;}double Pick=Rand.FRand()*Total;for(auto W:Weights){Pick-=W.Value;if(Pick<=0){ResolvedFamily=W.Key;break;}}}
    int Floors=ResolvedFamily==EM80HouseFamily::Popular?1:ResolvedFamily==EM80HouseFamily::Narrow?3:2;if(FloorsOverride>0)Floors=FMath::Clamp(FloorsOverride,1,3);
    double FH=FMath::Clamp(FloorHeight,2.5f,4.f)*100.,Thickness=WallThickness*100.;
    TArray<Volume>Volumes;
    auto Add=[&](TArray<P2>Q,int N,double Base,double Rise,bool Terrace,bool Upper=false){Clean(Q);if(Q.Num()<3)return;for(auto Loop:SimpleLoops(Q)){double A=0;for(int i=0;i<Loop.Num();++i)A+=Cross(P2::ZeroVector,Loop[i],Loop[(i+1)%Loop.Num()]);if(A<0){Algo::Reverse(Loop);A=-A;}TArray<int>Cap;if(!Triangulate(Loop,Cap)){GeometryError=TEXT("Divisione lotto non valida: ridurre articolazione");continue;}if(A<25000)continue;FRandomStream RoofRand(Seed+Volumes.Num()*2719);Volume V;V.P=Loop;V.Floors=N;V.Base=Base;V.Rise=Rise*(.85+RoofRand.FRand()*.3);V.RidgeAlpha=.38+RoofRand.FRand()*.24;V.Shed=Volumes.Num()>0&&RoofRand.FRand()<.4;V.Terrace=Terrace;V.Upper=Upper;Volumes.Add(V);}};
    if(ResolvedFamily==EM80HouseFamily::Courtyard&&Width>750&&Depth>650){double Left=S0+Width*(.5-CourtyardWidth*.5),Right=S0+Width*(.5+CourtyardWidth*.5),Back=T0+Depth*CourtyardDepth;Add(Clip(P,Along,Left,true),Floors,0,RoofRise*100,false);Add(Clip(P,Along,Right,false),1,20*VolumeVariation,RoofRise*65,false);auto Rear=Clip(Clip(Clip(P,Along,Left,false),Along,Right,true),In,Back,false);Add(Rear,2,0,0,true);
        // The yard is a real open void. Its floor stays in the lot and is collidable.
    }else if(ResolvedFamily==EM80HouseFamily::Extended&&Width>650){double Cut=S0+Width*(.46+Rand.FRand()*.12);Add(Clip(P,Along,Cut,true),Floors,0,RoofRise*100,false);auto Right=Clip(P,Along,Cut,false);Add(Right,1,0,0,true);auto Upper=Clip(Right,In,T0+Depth*UpperSetback,false);Add(Upper,FMath::Min(2,Floors),FH,0,true,true);
    }else if(ResolvedFamily==EM80HouseFamily::Corner&&Width>700){double Cut=T0+Depth*.6;Add(Clip(P,In,Cut,true),Floors,0,RoofRise*100,false);Add(Clip(P,In,Cut,false),1,0,RoofRise*60,false);
    }else if(Width>1700&&VolumeVariation>.2&&ResolvedFamily!=EM80HouseFamily::Palazzetto){int Count=FMath::Clamp(FMath::CeilToInt(Width/1100.),2,4);for(int i=0;i<Count;++i){auto Q=Clip(Clip(P,Along,S0+i*Width/Count,false),Along,S0+(i+1)*Width/Count,true);Add(Q,FMath::Clamp(Floors+((i+Seed)%3==0?-1:0),1,3),30*VolumeVariation*(i%2),i%2?0:RoofRise*100,i%2==1);}}
    else Add(P,Floors,0,ResolvedFamily==EM80HouseFamily::Narrow||ResolvedFamily==EM80HouseFamily::Palazzetto?0:RoofRise*100,ResolvedFamily==EM80HouseFamily::Narrow||ResolvedFamily==EM80HouseFamily::Palazzetto);
    if(Volumes.IsEmpty())return;
    Mesh M[12];
    auto Mat=[&](UMaterialInterface* A){return bGrayPreview&&GrayMaterial?GrayMaterial.Get():A;};
    StoneDetails->SetMaterial(0,Mat(StoneMaterial));IronDetails->SetMaterial(0,Mat(IronMaterial));WoodDetails->SetMaterial(0,Mat(WoodMaterial));GlassDetails->SetMaterial(0,Mat(GlassMaterial));StreetDetails->SetMaterial(0,Mat(DrainMaterial?DrainMaterial.Get():StoneMaterial.Get()));LifeDetails->SetMaterial(0,Mat(ClothMaterial));RoofTiles->SetMaterial(0,Mat(TileMaterial?TileMaterial.Get():RoofMaterial.Get()));
    auto RoofZ=[&](const Volume& V,P2 Q){double lo=MAX_dbl,hi=-MAX_dbl;for(auto R:V.P){double t=FVector2D::DotProduct(R,In);lo=FMath::Min(lo,t);hi=FMath::Max(hi,t);}double a=(FVector2D::DotProduct(Q,In)-lo)/FMath::Max(1.,hi-lo);double H=V.Shed?a:(a<V.RidgeAlpha?a/V.RidgeAlpha:(1-a)/(1-V.RidgeAlpha));return V.Base+V.Floors*FH+V.Rise*H;};
    auto Rail=[&](FVector C,FVector E,FVector O,double W,double D){
        int Style=ResolvedFamily==EM80HouseFamily::Palazzetto?2:FMath::Abs(Seed)%2;
        auto Bar=[&](FVector A,FVector B,double R){Tube(M[9],{A,B},R);};FVector Front=C+O*D;
        Bar(Front-E*W*.5+FVector(0,0,98),Front+E*W*.5+FVector(0,0,98),1.5);
        Bar(Front-E*W*.5+FVector(0,0,12),Front+E*W*.5+FVector(0,0,12),1.1);
        int Count=FMath::Max(2,FMath::CeilToInt(W/(Style==2?23.:13.)));for(int i=0;i<=Count;++i){double x=W*(double(i)/Count-.5);Bar(Front+E*x+FVector(0,0,12),Front+E*x+FVector(0,0,98),i==0||i==Count?1.5:.85);
            if(Style==1&&i<Count){FVector Center=Front+E*(x+W/Count*.5)+FVector(0,0,52);TArray<FVector> Ring;for(int k=0;k<=16;++k)Ring.Add(Center+E*(W/Count*.42*FMath::Cos(2*PI*k/16.))+FVector(0,0,13*FMath::Sin(2*PI*k/16.)));Tube(M[9],Ring,.6);}
            if(Style==2&&i<Count){double Cell=W/Count;TArray<FVector> Scroll;for(int k=0;k<=24;++k){double t=double(k)/24.;Scroll.Add(Front+E*(x+Cell*.5+Cell*.35*FMath::Sin(2*PI*t))+FVector(0,0,18+72*t));}Tube(M[9],Scroll,.75);}}
        if(D>10)for(double side:{-1.,1.}){Bar(C+E*W*.5*side+FVector(0,0,98),Front+E*W*.5*side+FVector(0,0,98),1.4);Bar(C+E*W*.5*side+FVector(0,0,12),Front+E*W*.5*side+FVector(0,0,12),1.);for(double y=0;y<D;y+=13)Bar(C+E*W*.5*side+O*y+FVector(0,0,12),C+E*W*.5*side+O*y+FVector(0,0,98),.85);}
    };
    for(int vi=0;vi<Volumes.Num();++vi){Volume& V=Volumes[vi];++GeneratedVolumes;TArray<int>Cap;Triangulate(V.P,Cap);
        double Lo=MAX_dbl,Hi=-MAX_dbl,LeftS=MAX_dbl,RightS=-MAX_dbl;for(auto Q:V.P){double d=FVector2D::DotProduct(Q,In),s=FVector2D::DotProduct(Q,Along);Lo=FMath::Min(Lo,d);Hi=FMath::Max(Hi,d);LeftS=FMath::Min(LeftS,s);RightS=FMath::Max(RightS,s);}double Ridge=Lo+(Hi-Lo)*V.RidgeAlpha;
        for(int j=0;j<Cap.Num();j+=3)for(int side=0;side<2;++side){auto Part=Clip({V.P[Cap[j]],V.P[Cap[j+1]],V.P[Cap[j+2]]},In,Ridge,side==0);for(int k=1;k+1<Part.Num();++k){FVector A(Part[0].X,Part[0].Y,RoofZ(V,Part[0])),B(Part[k].X,Part[k].Y,RoofZ(V,Part[k])),C(Part[k+1].X,Part[k+1].Y,RoofZ(V,Part[k+1]));M[V.Rise>0?2:3].Tri(A,B,C,{FVector2D::DotProduct(Part[0],Along)/180.,FVector2D::DotProduct(Part[0],In)/180.},{FVector2D::DotProduct(Part[k],Along)/180.,FVector2D::DotProduct(Part[k],In)/180.},{FVector2D::DotProduct(Part[k+1],Along)/180.,FVector2D::DotProduct(Part[k+1],In)/180.});}}
        // Close soffits and floors independently for every volume, including upper additions.
        for(int j=0;j<Cap.Num();j+=3){P2 A=V.P[Cap[j]],B=V.P[Cap[j+1]],C=V.P[Cap[j+2]];M[0].Tri(FVector(A.X,A.Y,V.Base),FVector(C.X,C.Y,V.Base),FVector(B.X,B.Y,V.Base),A/180.,C/180.,B/180.);}
        if(V.Rise>0&&bShowRoofs&&bShowRoofTiles&&RoofTileMesh){
            FRandomStream TilesRand(Seed+vi*7171);double StepS=TileRowWidth*100.,StepT=TileRowLength*100.;
            for(double s=LeftS+StepS*.5;s<RightS;s+=StepS)for(double t=Lo+StepT*.5;t<Hi;t+=StepT){P2 Q=Along*s+In*t;bool Fits=Inside(V.P,Q);for(double ds:{-.45*StepS,.45*StepS})for(double dt:{-.48*StepT,.48*StepT})Fits=Fits&&Inside(V.P,Q+Along*ds+In*dt);if(!Fits)continue;
                bool Covered=false;for(int vj=0;vj<Volumes.Num();++vj)if(vj!=vi&&Inside(Volumes[vj].P,Q)&&RoofZ(Volumes[vj],Q)>RoofZ(V,Q)+8)Covered=true;if(Covered)continue;
                double Slope=(RoofZ(V,Q+In)-RoofZ(V,Q-In))*.5;FVector X(In.X,In.Y,Slope);X.Normalize();FVector Y=FVector::CrossProduct(FVector::UpVector,X).GetSafeNormal(),Z=FVector::CrossProduct(X,Y);FMatrix Basis=FMatrix::Identity;Basis.SetAxes(&X,&Y,&Z);FQuat Rot(Basis);Rot.Normalize();double J=(TilesRand.FRand()-.5)*TileIrregularity;
                FVector Location(Q.X,Q.Y,RoofZ(V,Q)+1+J);FVector Scale(TileRowLength/.36,TileRowWidth/.20,1.+J*.05);RoofTiles->AddInstance(FTransform(Rot,Location,Scale));
            }
            // Raised overlapping ridge caps, limited to the lot, give the ridge a real silhouette.
            if(!V.Shed)for(double s=LeftS+22;s<RightS-22;s+=36){P2 Q=Along*s+In*Ridge;if(!Inside(V.P,Q))continue;FVector X(Along.X,Along.Y,0),Y=FVector::CrossProduct(FVector::UpVector,X),Z=FVector::UpVector;FMatrix Basis=FMatrix::Identity;Basis.SetAxes(&X,&Y,&Z);FQuat Rotation(Basis);Rotation.Normalize();RoofTiles->AddInstance(FTransform(Rotation,FVector(Q.X,Q.Y,RoofZ(V,Q)+6),FVector(1.,1.2,1.1)));}
        }
        for(int e=0;e<V.P.Num();++e){P2 A=V.P[e],B=V.P[(e+1)%V.P.Num()],E=(B-A).GetSafeNormal(),O(E.Y,-E.X),Mid=(A+B)*.5;double L=(B-A).Size();if(L<.5)continue;
            FVector Edge(E.X,E.Y,0),Out(O.X,O.Y,0),Base(A.X,A.Y,0);bool Shared=false;double NeighborRoof=-MAX_dbl;
            for(int vj=0;vj<Volumes.Num();++vj)if(vj!=vi&&Inside(Volumes[vj].P,Mid+O*2)&&Volumes[vj].Base<V.Base+V.Floors*FH){Shared=true;NeighborRoof=FMath::Max(NeighborRoof,RoofZ(Volumes[vj],Mid));}
            bool Party=false;for(int OriginalEdge:PartyWallEdges){int p=(OriginalEdge%Original.Num()+Original.Num())%Original.Num();if(EdgeDistance(Mid,Original[p],Original[(p+1)%Original.Num()])<3)Party=true;}
            bool Front=FVector2D::DotProduct(O,-In)>.45;bool Street=Front||(ResolvedFamily==EM80HouseFamily::Corner&&FMath::Abs(FVector2D::DotProduct(O,Along))>.55&&!Party);
            double FloorBase=V.Base,BottomA=V.Upper?V.Base:GroundZ(A)-20,BottomB=V.Upper?V.Base:GroundZ(B)-20;
            // A midpoint neighbor test may suppress openings, never the structural wall.
            // Each volume remains closed when an adjacent roof is lower or crosses its ridge.
            TArray<Opening>Ops;
            bool DoorMade=false;double DoorPosition=L*(ResolvedFamily==EM80HouseFamily::Palazzetto?.5:.27+Rand.FRand()*.45);
            int Bays=FMath::Clamp(FMath::FloorToInt(L/(ResolvedFamily==EM80HouseFamily::Palazzetto?310.:290.)),1,12);double Bay=L/Bays;
            if(bShowOpenings&&!Shared&&!Party&&L>195){
                if(Street&&!V.Upper){Opening D;D.Door=true;D.X=FMath::Clamp(DoorPosition,80.,L-80.);D.W=ResolvedFamily==EM80HouseFamily::Palazzetto?145:95+Rand.FRand()*25;D.H=215+Rand.FRand()*20;D.Z=V.Base;D.Arch=(ResolvedFamily==EM80HouseFamily::Palazzetto||ResolvedFamily==EM80HouseFamily::Courtyard||Rand.FRand()<.16)&&D.W>100;double Diff=D.Z-GroundZ(A+E*D.X+O*25);double Run=FMath::CeilToDouble(FMath::Max(0.,Diff)/(StepRiser*100.))*StepTread*100.;double Available=FMath::Max(D.X,L-D.X)-D.W*.5-15;if(Diff>=-15&&Diff<=150&&Run<=Available){Ops.Add(D);DoorMade=true;}}
                for(int f=0;f<V.Floors;++f)for(int b=0;b<Bays;++b){if(!Street&&Rand.FRand()<.42)continue;if(f==0&&Rand.FRand()<.28)continue;if(ResolvedFamily!=EM80HouseFamily::Palazzetto&&Rand.FRand()<.14*FacadeIrregularity)continue;
                    Opening W;double Shift=(Rand.FRand()-.5)*Bay*.22*FacadeIrregularity;W.X=Bay*(b+.5)+Shift;W.W=FMath::Min(Bay*.42,65+Rand.FRand()*36);W.H=95+Rand.FRand()*45;W.Z=V.Base+f*FH+80+Rand.FRand()*15*FacadeIrregularity;
                    W.Balcony=f>0&&Street&&bShowBalconies&&Rand.FRand()<BalconyDensity*(ResolvedFamily==EM80HouseFamily::Palazzetto?1.6:ResolvedFamily==EM80HouseFamily::Popular?.5:1.);
                    W.French=W.Balcony&&Rand.FRand()<.4;if(W.Balcony){W.H=205;W.Z=V.Base+f*FH+8;}W.Blocked=!W.Balcony&&Rand.FRand()<Decay*.14;
                    if(!W.Balcony&&!W.Blocked){int Style=(FMath::Abs(Seed)+f*7+b*11+vi*3)%9;if(Style==0){W.W*=.62;W.H*=.68;W.Z+=32;}else if(Style==1&&W.W>72){W.Arch=true;W.H=FMath::Max(W.H,125.);}else if(Style==2&&f>0){W.W*=.80;W.H*=1.15;W.Z-=12;}}
                    bool Hit=false;for(auto D:Ops)if(FMath::Abs(D.X-W.X)<(D.W+W.W)*.5+50&&W.Z<D.Z+D.H+15&&W.Z+W.H>D.Z-15){Hit=true;break;}if(W.X-W.W*.5<55||W.X+W.W*.5>L-55)Hit=true;if(!Hit)Ops.Add(W);
                }
            }
            // Small missing masonry units are actual recesses in the wall, not painted spots.
            // Keep them off party walls, away from usable openings and below the roof line.
            if(MasonryLoss>0.f&&!Shared&&!Party&&Street&&L>340&&Rand.FRand()<MasonryLoss){
                for(int k=0;k<(L>850&&MasonryLoss>.55f?2:1);++k){
                    Opening H;H.DamageHole=true;H.W=18+Rand.FRand()*19;H.H=12+Rand.FRand()*15;
                    H.X=L*(.18+Rand.FRand()*.64);H.Z=V.Base+FH*(.28+Rand.FRand()*.44);
                    bool Hit=H.X-H.W*.5<55||H.X+H.W*.5>L-55;
                    for(const Opening& Op:Ops)if(FMath::Abs(Op.X-H.X)<(Op.W+H.W)*.5+22&&H.Z<Op.Z+Op.H+22&&H.Z+H.H>Op.Z-22){Hit=true;break;}
                    if(!Hit)Ops.Add(H);
                }
            }
            // Split walls into solid panels surrounding actual holes, including sampled arches.
            TArray<double>Cuts={0.,L};double da=FVector2D::DotProduct(A,In)-Ridge,db=FVector2D::DotProduct(B,In)-Ridge;if(da*db<0)Cuts.Add(L*da/(da-db));
            for(auto Op:Ops){Cuts.Add(Op.X-Op.W*.5);Cuts.Add(Op.X+Op.W*.5);if(Op.Arch)for(int k=1;k<12;++k)Cuts.Add(Op.X-Op.W*.5+Op.W*k/12.);}
            Cuts.Sort();for(int c=0;c+1<Cuts.Num();++c){double x0=Cuts[c],x1=Cuts[c+1];if(x1-x0<.05)continue;double x=(x0+x1)*.5;P2 Q0=A+E*x0,Q1=A+E*x1;double ground0=FMath::Lerp(BottomA,BottomB,x0/L),ground1=FMath::Lerp(BottomA,BottomB,x1/L),Top0=RoofZ(V,Q0),Top1=RoofZ(V,Q1);
                auto Panel=[&](double z0,double z1,double z2,double z3){
                    auto Piece=[&](Mesh& Bucket,double low0,double low1,double high0,double high1){
                        high0=FMath::Max(low0,high0);high1=FMath::Max(low1,high1);
                        if(FMath::Max(high0-low0,high1-low1)<.05)return;
                        FVector A0(Q0.X,Q0.Y,low0),A1(Q0.X,Q0.Y,high0),B1(Q1.X,Q1.Y,high1),B0(Q1.X,Q1.Y,low1),D=Out*Thickness;
                        Bucket.Quad(A0,A1,B1,B0,180.,Out,true);Bucket.Quad(B0-D,B1-D,A1-D,A0-D,180.,-Out,true);
                        Bucket.Quad(A1,A1-D,B1-D,B1);Bucket.Quad(B0,B0-D,A0-D,A0);
                        Bucket.Quad(A0,A0-D,A1-D,A1);Bucket.Quad(B1,B1-D,B0-D,B0);
                    };
                    double high0=FMath::Max(z0,z3),high1=FMath::Max(z1,z2);
                    if(bUpperBrickFloor&&UpperBrickMaterial&&V.Floors>=2){
                        double seam=V.Upper?V.Base:V.Base+(V.Floors-1)*FH;
                        Piece(M[0],z0,z1,FMath::Min(high0,seam),FMath::Min(high1,seam));
                        Piece(M[10],FMath::Min(high0,FMath::Max(z0,seam)),FMath::Min(high1,FMath::Max(z1,seam)),high0,high1);
                    }else Piece(M[0],z0,z1,high0,high1);
                };
                double z0=ground0,z1=ground1;
                TArray<Opening>Here;for(auto Op:Ops)if(x>Op.X-Op.W*.5-.01&&x<Op.X+Op.W*.5+.01)Here.Add(Op);Here.Sort([](const Opening&a,const Opening&b){return a.Z<b.Z;});
                for(auto Op:Here){Panel(z0,z1,Op.Z,Op.Z);z0=Op.Z+Op.ArchTop(x0-Op.X);z1=Op.Z+Op.ArchTop(x1-Op.X);}Panel(z0,z1,Top1,Top0);
                // Sparse tapered damp and moss follow the ground without rectangular tiles.
                if(bShowAging&&!Shared&&Decay>.35&&Here.IsEmpty()&&Rand.FRand()<.28){double H=18+Decay*48*(.5+Rand.FRand());FVector N=Out*.9;FVector A0(Q0.X,Q0.Y,ground0+15),B0(Q1.X,Q1.Y,ground1+15),MidPoint=(A0+B0)*.5;M[4].Tri(A0+N,B0+N,MidPoint+N+FVector(0,0,H),{0,0},{1,0},{.5,1});}
            }
            for(auto Op:Ops){++GeneratedOpenings;FVector C=Base+Edge*Op.X+FVector(0,0,Op.Z),Left=C-Edge*Op.W*.5,Right=C+Edge*Op.W*.5;double Recess=Thickness*.82;
                M[1].Quad(Left,Left-Out*Thickness,Left-Out*Thickness+FVector(0,0,Op.H-(Op.Arch?Op.W*.5:0)),Left+FVector(0,0,Op.H-(Op.Arch?Op.W*.5:0)));
                M[1].Quad(Right,Right+FVector(0,0,Op.H-(Op.Arch?Op.W*.5:0)),Right-Out*Thickness+FVector(0,0,Op.H-(Op.Arch?Op.W*.5:0)),Right-Out*Thickness);
                M[1].Quad(Left,Right,Right-Out*Thickness,Left-Out*Thickness);
                int ArchSegments=Op.Arch?12:1;for(int k=0;k<ArchSegments;++k){double x0=-Op.W*.5+Op.W*k/ArchSegments,x1=-Op.W*.5+Op.W*(k+1)/ArchSegments;FVector A0=C+Edge*x0+FVector(0,0,Op.ArchTop(x0)),A1=C+Edge*x1+FVector(0,0,Op.ArchTop(x1));M[1].Quad(A0,A1,A1-Out*Thickness,A0-Out*Thickness,180.,FVector::DownVector);if(bShowCornices&&!Op.DamageHole){FVector D=A1-A0;double Len=D.Size();FVector CrossOut=FVector::CrossProduct(Out,D.GetSafeNormal());M[1].Quad(A0+Out*3,A1+Out*3,A1+CrossOut*9+Out*3,A0+CrossOut*9+Out*3);}}
                if(Op.DamageHole)continue;
                if(Op.Door&&DoorMesh)Module(DoorPanels,DoorMesh,C-Out*Recess+FVector(0,0,Op.H*.5),Edge,Out,Op.W,Op.H);
                else if(Op.Arch){for(int k=0;k<ArchSegments;++k){double x0=-Op.W*.5+Op.W*k/ArchSegments,x1=-Op.W*.5+Op.W*(k+1)/ArchSegments;FVector A0=C+Edge*x0-Out*Recess,A1=C+Edge*x1-Out*Recess;(Op.Door?M[6]:M[11]).Quad(A0,A0+FVector(0,0,Op.ArchTop(x0)),A1+FVector(0,0,Op.ArchTop(x1)),A1,180.,Out);}}
                else if(Op.Blocked){
                    // A shuttered, neglected opening reads as a dark recess
                    // with uneven timber boards instead of a white plug.
                    FVector Back=C-Out*Recess+FVector(0,0,Op.H*.5);
                    Box(GlassDetails,Back,Edge,FVector(Op.W,4,Op.H));
                    int Boards=FMath::Max(4,FMath::FloorToInt(Op.W/14.));
                    double Pitch=Op.W/Boards;
                    for(int board=0;board<Boards;++board){
                        if((board+Seed)%7==0)continue;
                        double H=Op.H*(.88+.04*((board+Seed)%3));
                        FVector BoardCenter=Back+Edge*(-Op.W*.5+(board+.5)*Pitch)+Out*5+FVector(0,0,-(Op.H-H)*.5);
                        Box(WoodDetails,BoardCenter,Edge,FVector(Pitch*.82,3,H));
                    }
                    for(double height:{.28,.72})Box(WoodDetails,Back+Out*9+FVector(0,0,Op.H*(height-.5)),Edge,FVector(Op.W*.96,4,6));
                }
                else Box(Op.Door?WoodDetails.Get():GlassDetails.Get(),C-Out*Recess+FVector(0,0,Op.H*.5),Edge,FVector(Op.W,6,Op.H));
                if(Op.Door&&bShowNumbers&&!bGrayPreview){FVector NP=C+Edge*(Op.W*.5+25)+Out*4+FVector(0,0,170);Box(StoneDetails,NP,Edge,FVector(25,5,17));auto* Text=NewObject<UTextRenderComponent>(this,NAME_None,RF_Transactional);Text->CreationMethod=EComponentCreationMethod::UserConstructionScript;Text->ComponentTags.Add(TEXT("M80GeneratedNumber"));Text->SetupAttachment(Footprint);Text->SetRelativeLocation(NP+Out*3);Text->SetRelativeRotation(FRotator(0,FMath::RadiansToDegrees(FMath::Atan2(Out.Y,Out.X)),0));Text->SetHorizontalAlignment(EHTA_Center);Text->SetVerticalAlignment(EVRTA_TextCenter);Text->SetWorldSize(12);Text->SetTextRenderColor(FColor(48,45,38));Text->SetText(FText::FromString(FString::FromInt(10+FMath::Abs(Seed)%90)));Text->SetCollisionEnabled(ECollisionEnabled::NoCollision);Text->RegisterComponent();}
                if(bShowCornices){double Trim=ResolvedFamily==EM80HouseFamily::Palazzetto?12.:6.;for(double side:{-1.,1.})Box(StoneDetails,C+Edge*(Op.W*.5+Trim*.5)*side+Out*2+FVector(0,0,Op.H*.5-(Op.Arch?Op.W*.25:0)),Edge,FVector(Trim,10,Op.H-(Op.Arch?Op.W*.5:0)));}
                double Projection=FMath::Clamp(SillProjection*100.,2.,15.),Slab=FMath::Clamp(SillThickness*100.,2.5,10.);double TotalDepth=Thickness+Projection;
                Box(StoneDetails,C+Out*((Projection-Thickness)*.5)-FVector(0,0,Slab*.5),Edge,FVector(Op.W+8,TotalDepth,Slab));
                if(!Op.Door&&!Op.Blocked){Box(WoodDetails,C-Out*(Recess-5)+FVector(0,0,Op.H*.5),Edge,FVector(4,5,Op.H));Box(WoodDetails,C-Out*(Recess-5)+FVector(0,0,Op.H*.6),Edge,FVector(Op.W,5,3));
                    if(bShowShutters&&Rand.FRand()<.68){int State=Rand.RandRange(0,3);for(double side:{-1.,1.}){double X=State==0?Op.W*.25:Op.W*.75+7;FVector S=C+Edge*X*side+Out*(State==0?4:10)+FVector(0,0,Op.H*.5);FVector SE=State==2?(Edge+Out*.8*side).GetSafeNormal():Edge;Box(WoodDetails,S,SE,FVector(Op.W*.47,5,Op.H));for(double z=10;z<Op.H;z+=17)Box(WoodDetails,S+Out*3+FVector(0,0,z-Op.H*.5),SE,FVector(Op.W*.44,3,2));}}
                }
                if(Op.Balcony){++GeneratedBalconies;double BW=FMath::Min(Bay-35,Op.W+(ResolvedFamily==EM80HouseFamily::Palazzetto?110:65)),BD=Op.French?9:BalconyDepth*100.;FVector BC=C-FVector(0,0,8);
                    bool UseModule=!Op.French&&bUseBalconyModules&&BalconyModuleMesh&&(ResolvedFamily==EM80HouseFamily::Palazzetto||ResolvedFamily==EM80HouseFamily::Corner)&&BW>=140;
                    if(UseModule){auto Bounds=BalconyModuleMesh->GetBounds();FVector Size=Bounds.BoxExtent*2;double Scale=FMath::Clamp(FMath::Min(BW,BalconyModuleWidth*100.)/Size.X,.55,.95);FVector X=-Edge,Y=Out,Z=FVector::UpVector;FMatrix Basis=FMatrix::Identity;Basis.SetAxes(&X,&Y,&Z);FQuat Rot(Basis);Rot.Normalize();FVector Anchor(Bounds.Origin.X,Bounds.Origin.Y-Bounds.BoxExtent.Y,Bounds.Origin.Z-Bounds.BoxExtent.Z+52);BalconyModules->AddInstance(FTransform(Rot,BC-Rot.RotateVector(Anchor*Scale),FVector(Scale)));}
                     else{if(!Op.French){Box(StoneDetails,BC+Out*BD*.5-FVector(0,0,6),Edge,FVector(BW,BD,12));Box(StoneDetails,BC+Out*(BD-2)-FVector(0,0,10),Edge,FVector(BW+3,5,5));for(double side:{-.32,.32})Corbel(M[1],BC+Edge*BW*side-FVector(0,0,12),Edge,Out,BD*.67,14);}Rail(BC,Edge,Out,BW,BD);}
                     if(!Op.French&&PotMesh&&BD>35&&Rand.FRand()<.32){auto Bounds=PotMesh->GetBounds();double Scale=32./FMath::Max(1.,Bounds.BoxExtent.Z*2.);FVector At=BC+Edge*BW*.30+Out*(BD*.60)+FVector(0,0,16);Pots->AddInstance(FTransform(FQuat::Identity,At-Bounds.Origin*Scale,FVector(Scale)));}
                }
                if(Op.Door&&bShowSteps){double Ground=GroundZ(P2(C.X+Out.X*25,C.Y+Out.Y*25));double Diff=Op.Z-Ground;int N=FMath::Clamp(FMath::CeilToInt(Diff/FMath::Max(8.,StepRiser*100.)),0,64);bool Parallel=N*StepTread*100.>50.;auto GroundUnder=[&](const FVector& Sample){return GroundZ(P2(Sample.X,Sample.Y));};if(Parallel&&N>0){FVector StepPoint=C+Out*25;double Low=FMath::Min3(GroundUnder(StepPoint),GroundUnder(StepPoint+Edge*(Op.W*.5+6)),GroundUnder(StepPoint-Edge*(Op.W*.5+6)))-25;Box(StoneDetails,StepPoint+FVector(0,0,(Op.Z+Low)*.5-Op.Z),Edge,FVector(Op.W+12,50,Op.Z-Low));}for(int k=0;k<N;++k){double Sign=DoorPosition<L*.5?1.:-1.;FVector Offset=Parallel?Out*25+Edge*Sign*(Op.W*.5+6+StepTread*100.*(k+.5)):Out*(StepTread*50.+StepTread*100.*k);FVector StepPoint=C+Offset;FVector Size=Parallel?FVector(StepTread*100.+2,50,1):FVector(Op.W+20,StepTread*100.+2,1);FVector Span=Parallel?Edge*(Size.X*.5):Out*(Size.Y*.5);double Low=FMath::Min3(GroundUnder(StepPoint),GroundUnder(StepPoint+Span),GroundUnder(StepPoint-Span))-25;double Top=Op.Z-Diff*k/FMath::Max(1,N);Size.Z=FMath::Max(3.,Top-Low);Box(StoneDetails,StepPoint+FVector(0,0,(Top+Low)*.5-Op.Z),Edge,Size);}}
            }
            if(!Shared&&!Party&&bShowCornices){int Parts=FMath::Max(1,FMath::CeilToInt(L/120.));for(int k=0;k<Parts;++k){if(Decay>.78&&Rand.FRand()<.13)continue;double x0=L*k/Parts,x1=L*(k+1)/Parts;P2 Q0=A+E*x0,Q1=A+E*x1;double Z0=RoofZ(V,Q0),Z1=RoofZ(V,Q1);FVector P0(Q0.X,Q0.Y,Z0),P1(Q1.X,Q1.Y,Z1);double D=ResolvedFamily==EM80HouseFamily::Palazzetto?24:12;M[1].Quad(P0+Out*D-FVector(0,0,10),P0+Out*D,P1+Out*D,P1+Out*D-FVector(0,0,10),180.,Out);M[1].Quad(P0-Out*8,P0+Out*D,P1+Out*D,P1-Out*8);
                    if(V.Terrace){double H=ParapetHeight*100.;M[0].Quad(P0,P0+FVector(0,0,H),P1+FVector(0,0,H),P1,180.,Out);M[1].Quad(P0-Out*16+FVector(0,0,H),P0+FVector(0,0,H),P1+FVector(0,0,H),P1-Out*16+FVector(0,0,H));M[0].Quad(P1-Out*16,P1-Out*16+FVector(0,0,H),P0-Out*16+FVector(0,0,H),P0-Out*16,180.,-Out);}}
            }
            // Do not add flat repair polygons: from the street they look pasted onto the wall.
            // Real masonry holes above and the terrain-following damp line remain in use.
            if(bShowLife&&Street&&!Shared&&!Party){double X=FMath::Min(L-30,35.+Seed%30);FVector C=Base+Edge*X+Out*8;double Z=RoofZ(V,A+E*X),Bottom=GroundZ(A+E*X+O*20)+12;double Rise=Z-Bottom;
                if(Rise>80){ServiceSpline(*FString::Printf(TEXT("Pluviale_v%d_e%d"),vi,e),{C+Out*10+FVector(0,0,Z),C+Out*10+FVector(0,0,Z-25),C+FVector(0,0,Z-42),C+FVector(0,0,Bottom+32),C+Out*8+FVector(0,0,Bottom+12),C+Out*23+FVector(0,0,Bottom)},DownpipeDiameter*50.,false);
                    for(double z=Bottom+70;z<Z-40;z+=150){Box(IronDetails,C+FVector(0,0,z),Edge,FVector(DownpipeDiameter*100+2,DownpipeDiameter*100+2,2));Box(IronDetails,C-Out*4+FVector(0,0,z),Edge,FVector(3,10,3));}}
                double CZ=V.Base+FH*.85;TArray<FVector> CablePoints;for(int k=0;k<=4;++k)CablePoints.Add(Base+Edge*(L*k/4.)+Out*6+FVector(0,0,CZ-CableSag*100.*FMath::Sin(PI*k/4.)));ServiceSpline(*FString::Printf(TEXT("Cavo_v%d_e%d"),vi,e),CablePoints,CableDiameter*50.,true);
                if(Rand.FRand()<.4){FVector C0=Base+Edge*(L*.6)-Out*150+FVector(0,0,RoofZ(V,Mid)+100);Box(IronDetails,C0,Edge,FVector(2.8,2.8,180));Box(IronDetails,C0+FVector(0,0,80),Edge,FVector(95,2,2));for(int k=-2;k<=2;++k)Box(IronDetails,C0+Edge*k*17+FVector(0,0,80),Edge,FVector(2,55-5*FMath::Abs(k),2));}
                if(GeneratedBalconies>0&&HangingClothesMesh&&Rand.FRand()<.25&&L>400){FVector C0=Base+Edge*(L*.5)+Out*50+FVector(0,0,V.Base+FH+140);Box(IronDetails,C0,Edge,FVector(180,1.2,1.2));for(double Side:{-1.,1.}){FVector Support=Base+Edge*(L*.5+Side*82)+Out*25+FVector(0,0,V.Base+FH+140);Box(IronDetails,Support,Out,FVector(50,2.5,2.5));}FVector ClothX=Out,ClothY=Edge,ClothZ=FVector::UpVector;FMatrix Basis=FMatrix::Identity;Basis.SetAxes(&ClothX,&ClothY,&ClothZ);FQuat Rotation(Basis);Rotation.Normalize();for(int k=-1;k<=1;++k){double Scale=.78+Rand.FRand()*.27;HangingClothes->AddInstance(FTransform(Rotation,C0+Edge*k*58-FVector(0,0,3*Scale),FVector(Scale)));}}
                if(Rand.FRand()<.35&&DoorMade&&PotMesh){FVector C0=Base+Edge*FMath::Clamp(DoorPosition+105.,30.,L-30)+Out*35+FVector(0,0,GroundZ(A+E*DoorPosition)+17);auto Bounds=PotMesh->GetBounds();double Scale=34./FMath::Max(1.,Bounds.BoxExtent.Z*2.);Pots->AddInstance(FTransform(FQuat::Identity,C0-Bounds.Origin*Scale,FVector(Scale)));}
            }
            if(bShowStreetDetails&&Street&&!Shared&&!Party){double W=DrainWidth*100.;for(double x=0;x<L;x+=42){double Len=FMath::Min(41.,L-x),MidX=x+Len*.5;P2 Q=A+E*MidX+O*(W*.5+8);double z=GroundZ(Q);Box(StreetDetails,FVector(Q.X,Q.Y,z+1),Edge,FVector(Len,W,3));for(double Side:{-1.,1.})Box(StreetDetails,FVector(Q.X,Q.Y,z+3.5)+Out*(W*.5-2),Edge,FVector(Len,4,5));if(FMath::FloorToInt(x/42.)%14==FMath::Abs(Seed)%14){for(double b=-W*.35;b<=W*.35;b+=4)Box(IronDetails,FVector(Q.X,Q.Y,z+5)+Out*b,Edge,FVector(30,1.2,1.2));}}}
        }
    }
    if(ResolvedFamily==EM80HouseFamily::Courtyard&&Width>750&&Depth>650){double Left=S0+Width*(.5-CourtyardWidth*.5),Right=S0+Width*(.5+CourtyardWidth*.5),Back=T0+Depth*CourtyardDepth;auto Yard=Clip(Clip(Clip(P,Along,Left,false),Along,Right,true),In,Back,true);for(auto Loop:SimpleLoops(Yard)){TArray<int>Cap;if(Triangulate(Loop,Cap))for(int j=0;j<Cap.Num();j+=3){P2 A=Loop[Cap[j]],B=Loop[Cap[j+1]],C=Loop[Cap[j+2]];M[8].Tri(FVector(A.X,A.Y,GroundZ(A)+3),FVector(B.X,B.Y,GroundZ(B)+3),FVector(C.X,C.Y,GroundZ(C)+3),A/150.,B/150.,C/150.);}}}
    M[0].Save(Surface,0,Mat(PlasterMaterial));M[1].Save(Surface,1,Mat(StoneMaterial));M[2].Save(Surface,2,Mat(RoofMaterial));M[3].Save(Surface,3,Mat(TerraceMaterial));M[4].Save(Surface,4,Mat(DampMaterial),false);M[5].Save(Surface,5,Mat(RepairMaterial),false);M[6].Save(Surface,6,Mat(WoodMaterial));
    M[7].Save(Surface,7,Mat(ExposedStoneMaterial?ExposedStoneMaterial.Get():StoneMaterial.Get()),false);M[8].Save(Surface,8,Mat(TerraceMaterial));Surface->SetMeshSectionVisible(2,bShowRoofs);Surface->SetMeshSectionVisible(3,bShowRoofs);
    M[9].Save(Surface,9,Mat(IronMaterial),false);
    M[10].Save(Surface,10,Mat(UpperBrickMaterial));
    M[11].Save(Surface,11,Mat(GlassMaterial),false);
    TInlineComponentArray<USplineComponent*> RemainingPaths(this);for(auto* S:RemainingPaths)if(S->ComponentHasTag(TEXT("M80ServicePath"))&&!S->ComponentHasTag(TEXT("M80ServiceUsed"))){RemoveInstanceComponent(S);S->DestroyComponent();}
    LastServiceHash=ServiceHash();
    Surface->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Surface->SetCollisionResponseToAllChannels(ECR_Block);
    if (bPCGVisualReplacement)
    {
        Surface->SetVisibility(false);
        Surface->SetHiddenInGame(true);
        Surface->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        TInlineComponentArray<UInstancedStaticMeshComponent*> OriginalModules(this);
        for (UInstancedStaticMeshComponent* Module : OriginalModules)
        {
            Module->SetVisibility(false);
            Module->SetHiddenInGame(true);
            Module->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        }
        TInlineComponentArray<UTextRenderComponent*> OriginalNumbers(this);
        for (UTextRenderComponent* Number : OriginalNumbers)
        {
            if (Number->ComponentHasTag(TEXT("M80GeneratedNumber")))
            {
                Number->SetVisibility(false);
                Number->SetHiddenInGame(true);
            }
        }
    }
}
