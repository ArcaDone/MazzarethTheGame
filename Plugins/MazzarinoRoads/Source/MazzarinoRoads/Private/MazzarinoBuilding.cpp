#include "MazzarinoBuilding.h"
#include "Components/SplineComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "ProceduralMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"
#include "Algo/Reverse.h"

namespace {
double Cross2(const FVector2D& A,const FVector2D& B,const FVector2D& C){return (B.X-A.X)*(C.Y-A.Y)-(B.Y-A.Y)*(C.X-A.X);}
// Ear clipping keeps the cap inside concave imported footprints.
bool Triangulate(const TArray<FVector2D>& P,TArray<int32>& T){
    TArray<int32> I; for(int32 j=0;j<P.Num();++j)I.Add(j);
    int32 Guard=P.Num()*P.Num();
    while(I.Num()>3 && --Guard>0){bool Found=false;
        for(int32 j=0;j<I.Num();++j){int32 a=I[(j+I.Num()-1)%I.Num()],b=I[j],c=I[(j+1)%I.Num()];
            if(Cross2(P[a],P[b],P[c])<0.01)continue;
            bool Inside=false;
            for(int32 k:I){if(k==a||k==b||k==c)continue;
                if(Cross2(P[a],P[b],P[k])>=-0.01 && Cross2(P[b],P[c],P[k])>=-0.01 && Cross2(P[c],P[a],P[k])>=-0.01){Inside=true;break;}}
            if(!Inside){T.Append({a,b,c});I.RemoveAt(j);Found=true;break;}
        }
        if(!Found)return false;
    }
    if(I.Num()!=3)return false;T.Append(I);return true;
}
TArray<FVector2D> Clip(const TArray<FVector2D>& In,const FVector2D& Across,double Mid,bool Low){
    TArray<FVector2D> Out;
    for(int32 i=0;i<In.Num();++i){FVector2D A=In[i],B=In[(i+1)%In.Num()];
        double da=FVector2D::DotProduct(A,Across)-Mid,db=FVector2D::DotProduct(B,Across)-Mid;
        bool ia=Low?da<=0:da>=0,ib=Low?db<=0:db>=0;
        if(ia)Out.Add(A);if(ia!=ib)Out.Add(A+(B-A)*(da/(da-db)));
    }return Out;
}
void PlaceModule(UInstancedStaticMeshComponent* C,UStaticMesh* Mesh,const FVector& Center,const FVector& Edge,const FVector& Out,double Width,double Height){
    if(!Mesh)return;
    const FBoxSphereBounds Bounds=Mesh->GetBounds();FVector Size=Bounds.BoxExtent*2;
    if(Size.Z<0.01 || FMath::Max(Size.X,Size.Y)<0.01)return;
    bool NormalX=Size.X<Size.Y;
    FVector X=NormalX?Out:-Edge,Y=NormalX?Edge:Out;
    FMatrix Matrix=FMatrix::Identity;Matrix.SetAxes(&X,&Y,&FVector::UpVector);
    FQuat Rotation(Matrix);FVector Scale=NormalX?FVector(1,Width/Size.Y,Height/Size.Z):FVector(Width/Size.X,1,Height/Size.Z);
    FVector Location=Center-Rotation.RotateVector(Bounds.Origin*Scale);
    C->AddInstance(FTransform(Rotation,Location,Scale));
}
}
AMazzarinoBuilding::AMazzarinoBuilding(){
    PrimaryActorTick.bCanEverTick=false;
    Footprint=CreateDefaultSubobject<USplineComponent>(TEXT("Perimetro"));SetRootComponent(Footprint);
    Footprint->SetClosedLoop(true);Footprint->bInputSplinePointsToConstructionScript=true;
    BuildingSurface=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("ParetiETetto"));BuildingSurface->SetupAttachment(Footprint);
    BuildingSurface->bUseComplexAsSimpleCollision=true;
    Windows=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Finestre"));Windows->SetupAttachment(Footprint);
    Doors=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Porte"));Doors->SetupAttachment(Footprint);
    WindowBackings=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Vetri"));WindowBackings->SetupAttachment(Footprint);
    MasonryDetails=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("CorniciBalconiTerrazze"));MasonryDetails->SetupAttachment(Footprint);
    MetalDetails=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Ringhiere"));MetalDetails->SetupAttachment(Footprint);
    Shutters=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Persiane"));Shutters->SetupAttachment(Footprint);
    for(auto* C:{Windows.Get(),Doors.Get(),WindowBackings.Get()})C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));WindowBackings->SetStaticMesh(Cube.Object);
    for(auto* C:{MasonryDetails.Get(),MetalDetails.Get(),Shutters.Get()}){C->SetStaticMesh(Cube.Object);C->SetCollisionEnabled(ECollisionEnabled::NoCollision);}
}
void AMazzarinoBuilding::OnConstruction(const FTransform& Transform){Super::OnConstruction(Transform);RebuildBuilding();}
void AMazzarinoBuilding::RebuildBuilding(){
    BuildingSurface->ClearAllMeshSections();Windows->ClearInstances();Doors->ClearInstances();WindowBackings->ClearInstances();GeometryError.Empty();
    MasonryDetails->ClearInstances();MetalDetails->ClearInstances();Shutters->ClearInstances();
    TArray<FVector2D> P;
    for(int32 i=0;i<Footprint->GetNumberOfSplinePoints();++i){FVector V=Footprint->GetLocationAtSplinePoint(i,ESplineCoordinateSpace::Local);FVector2D Q(V.X,V.Y);
        if(P.IsEmpty() || FVector2D::Distance(P.Last(),Q)>0.1)P.Add(Q);}
    if(P.Num()>2 && FVector2D::Distance(P[0],P.Last())<0.1)P.Pop();
    const int32 RawFront=P.IsEmpty()?0:(FrontEdgeIndex%P.Num()+P.Num())%P.Num();
    const FVector2D FrontTarget=P.IsEmpty()?FVector2D::ZeroVector:(P[RawFront]+P[(RawFront+1)%P.Num()])*0.5;
    bool Reduced=true;while(Reduced && P.Num()>3){Reduced=false;for(int32 i=0;i<P.Num();++i){if(FMath::Abs(Cross2(P[(i+P.Num()-1)%P.Num()],P[i],P[(i+1)%P.Num()]))<0.01){P.RemoveAt(i);Reduced=true;break;}}}
    double Area=0;for(int32 i=0;i<P.Num();++i)Area+=P[i].X*P[(i+1)%P.Num()].Y-P[i].Y*P[(i+1)%P.Num()].X;
    if(P.Num()<3 || FMath::Abs(Area)<1){GeometryError=TEXT("Perimetro troppo piccolo");return;}
    if(Area<0)Algo::Reverse(P);
    int32 Front=0;double BestDistance=MAX_dbl;
    for(int32 i=0;i<P.Num();++i){auto A=P[i],B=P[(i+1)%P.Num()],D=B-A;
        double t=FMath::Clamp(FVector2D::DotProduct(FrontTarget-A,D)/FMath::Max(0.01,D.SizeSquared()),0.,1.);
        double Distance=(FrontTarget-(A+D*t)).SizeSquared();if(Distance<BestDistance){BestDistance=Distance;Front=i;}}
    const FVector2D Along=(P[(Front+1)%P.Num()]-P[Front]).GetSafeNormal();
    double AlongMin=MAX_dbl,AlongMax=-MAX_dbl;
    for(auto Q:P){double d=FVector2D::DotProduct(Q,Along);AlongMin=FMath::Min(AlongMin,d);AlongMax=FMath::Max(AlongMax,d);}
    int32 Sections=HeightVariationMeters>0?FMath::Clamp(FMath::RoundToInt((AlongMax-AlongMin)/(FMath::Max(4.f,FacadeSectionWidthMeters)*100)),1,12):1;
    double SectionWidth=(AlongMax-AlongMin)/Sections;
    auto SectionAt=[&](FVector2D Q){return FMath::Clamp(FMath::FloorToInt((FVector2D::DotProduct(Q,Along)-AlongMin)/FMath::Max(1.,SectionWidth)),0,Sections-1);};
    auto HeightOffset=[&](int32 S){const double Pattern[]={0.,0.65,0.22,1.,0.4};return HeightVariationMeters*100*Pattern[((S+CompositionSeed)%5+5)%5];};
    TArray<int32> Cap;if(!Triangulate(P,Cap)){GeometryError=TEXT("Perimetro non triangolabile: verificare incroci");return;}
    double Wall=FMath::Max(1,FloorCount)*FMath::Max(2.f,FloorHeightMeters)*100,UVScale=FMath::Max(0.1f,TextureMeters)*100;
    double R=FMath::DegreesToRadians(RoofRidgeAngleDegrees);FVector2D Across(-FMath::Sin(R),FMath::Cos(R));
    double Min=MAX_dbl,Max=-MAX_dbl;for(auto Q:P){double D=FVector2D::DotProduct(Q,Across);Min=FMath::Min(Min,D);Max=FMath::Max(Max,D);}double Mid=(Min+Max)*0.5;
    auto RoofZ=[&](FVector2D Q,int32 S){return Wall+HeightOffset(S)+FMath::Max(0.f,RoofRiseMeters)*100*FMath::Max(0.,1.-FMath::Abs(FVector2D::DotProduct(Q,Across)-Mid)/FMath::Max(1.,(Max-Min)*0.5));};
    TArray<FVector> V,N;TArray<int32>T;TArray<FVector2D> UV;TArray<FProcMeshTangent> Tang;
    TArray<FVector2D> WallPoints;
    for(int32 i=0;i<P.Num();++i){auto A=P[i],B=P[(i+1)%P.Num()];WallPoints.Add(A);
        TArray<double> Cuts;double da=FVector2D::DotProduct(A,Across)-Mid,db=FVector2D::DotProduct(B,Across)-Mid;
        if(RoofRiseMeters>0 && da*db<0)Cuts.Add(da/(da-db));
        double aa=FVector2D::DotProduct(A,Along),ab=FVector2D::DotProduct(B,Along);
        if(FMath::Abs(ab-aa)>0.01)for(int32 s=1;s<Sections;++s){double t=(AlongMin+s*SectionWidth-aa)/(ab-aa);if(t>0.00001 && t<0.99999)Cuts.Add(t);}
        Cuts.Sort();for(double t:Cuts)WallPoints.Add(A+(B-A)*t);}
    for(int32 i=0;i<WallPoints.Num();++i){FVector2D A=WallPoints[i],B=WallPoints[(i+1)%WallPoints.Num()],E=(B-A).GetSafeNormal();double L=FVector2D::Distance(A,B);int32 s=V.Num();
        if(L<0.01)continue;
        int32 Section=SectionAt((A+B)*0.5);
        V.Append({FVector(A.X,A.Y,0),FVector(B.X,B.Y,0),FVector(B.X,B.Y,RoofZ(B,Section)),FVector(A.X,A.Y,RoofZ(A,Section))});
        T.Append({s,s+2,s+1,s,s+3,s+2});
        UV.Append({FVector2D(0,0),FVector2D(L/UVScale,0),FVector2D(L/UVScale,RoofZ(B,Section)/UVScale),FVector2D(0,RoofZ(A,Section)/UVScale)});
        for(int32 j=0;j<4;++j){N.Add(FVector(E.Y,-E.X,0));Tang.Add(FProcMeshTangent(E.X,E.Y,0));}
    }
    TArray<FLinearColor> Colors;
    BuildingSurface->CreateMeshSection_LinearColor(0,V,T,N,UV,Colors,Tang,true);BuildingSurface->SetMaterial(0,FacadeMaterial);
    V.Reset();N.Reset();T.Reset();UV.Reset();Tang.Reset();
    for(int32 i=0;i<Cap.Num();i+=3){TArray<FVector2D> Triangle={P[Cap[i]],P[Cap[i+1]],P[Cap[i+2]]};
        for(int32 section=0;section<Sections;++section)for(int32 side=0;side<2;++side){auto Part=Clip(Triangle,Along,AlongMin+section*SectionWidth,false);Part=Clip(Part,Along,AlongMin+(section+1)*SectionWidth,true);Part=Clip(Part,Across,Mid,side==0);if(Part.Num()<3)continue;
            for(int32 j=1;j+1<Part.Num();++j){FVector A(Part[0].X,Part[0].Y,RoofZ(Part[0],section)),B(Part[j].X,Part[j].Y,RoofZ(Part[j],section)),C(Part[j+1].X,Part[j+1].Y,RoofZ(Part[j+1],section));
                FVector Cross=FVector::CrossProduct(B-A,C-A);if(Cross.SizeSquared()<1.)continue;FVector Normal=Cross.GetSafeNormal();
                int32 s=V.Num();V.Append({A,B,C});T.Append({s,s+2,s+1});
                for(auto Q:{A,B,C}){N.Add(Normal);UV.Add(FVector2D((Q.X*FMath::Cos(R)+Q.Y*FMath::Sin(R))/UVScale,(-Q.X*FMath::Sin(R)+Q.Y*FMath::Cos(R))/UVScale));Tang.Add(FProcMeshTangent(FMath::Cos(R),FMath::Sin(R),0));}
            }
        }
    }
    BuildingSurface->CreateMeshSection_LinearColor(1,V,T,N,UV,Colors,Tang,true);BuildingSurface->SetMaterial(1,RoofMaterial);
    // Close every roof step. Intersection pairs also work for concave footprints.
    V.Reset();N.Reset();T.Reset();UV.Reset();Tang.Reset();
    FVector2D Perp(-Along.Y,Along.X);
    for(int32 section=1;section<Sections;++section){double Cut=AlongMin+section*SectionWidth;TArray<double> Hits;
        for(int32 i=0;i<P.Num();++i){auto A=P[i],B=P[(i+1)%P.Num()];double da=FVector2D::DotProduct(A,Along)-Cut,db=FVector2D::DotProduct(B,Along)-Cut;
            if((da<=0 && db>0)||(db<=0 && da>0))Hits.Add(FVector2D::DotProduct(A+(B-A)*(da/(da-db)),Perp));}
        Hits.Sort();for(int32 j=0;j+1<Hits.Num();j+=2){TArray<double> Ends={Hits[j],Hits[j+1]};
            double denom=FVector2D::DotProduct(Perp,Across);if(RoofRiseMeters>0 && FMath::Abs(denom)>0.001){double ridge=(Mid-Cut*FVector2D::DotProduct(Along,Across))/denom;if(ridge>Ends[0] && ridge<Ends[1])Ends.Insert(ridge,1);}
            for(int32 k=0;k+1<Ends.Num();++k){auto A=Along*Cut+Perp*Ends[k],B=Along*Cut+Perp*Ends[k+1];int32 s=V.Num();
                if((B-A).Size()<0.01)continue;
                double Low=FMath::Min(HeightOffset(section-1),HeightOffset(section)),High=FMath::Max(HeightOffset(section-1),HeightOffset(section));if(High-Low<0.01)continue;
                double za=RoofZ(A,section)-HeightOffset(section),zb=RoofZ(B,section)-HeightOffset(section);
                V.Append({FVector(A.X,A.Y,za+Low),FVector(B.X,B.Y,zb+Low),FVector(B.X,B.Y,zb+High),FVector(A.X,A.Y,za+High)});
                bool HigherRight=HeightOffset(section)>HeightOffset(section-1);
                if(HigherRight)T.Append({s,s+1,s+2,s,s+2,s+3});else T.Append({s,s+2,s+1,s,s+3,s+2});
                for(int32 l=0;l<4;++l){N.Add(FVector(Along.X,Along.Y,0)*(HigherRight?-1:1));UV.Add(FVector2D((l==1||l==2)?(B-A).Size()/UVScale:0,l>=2?(High-Low)/UVScale:0));Tang.Add(FProcMeshTangent(Perp.X,Perp.Y,0));}
            }
        }
    }
    if(V.Num()){BuildingSurface->CreateMeshSection_LinearColor(2,V,T,N,UV,Colors,Tang,true);BuildingSurface->SetMaterial(2,FacadeMaterial);}
    BuildingSurface->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);BuildingSurface->SetCollisionResponseToAllChannels(ECR_Block);
    if(!bDetailedFacade)return;
    Windows->SetStaticMesh(WindowMesh);Doors->SetStaticMesh(DoorMesh);WindowBackings->SetMaterial(0,WindowBackingMaterial);
    MasonryDetails->SetMaterial(0,TrimMaterial?TrimMaterial.Get():FacadeMaterial.Get());MetalDetails->SetMaterial(0,MetalMaterial);Shutters->SetMaterial(0,ShutterMaterial);
    auto Box=[&](UInstancedStaticMeshComponent* Component,FVector C,FVector E,FVector Size){FRotator Rot(0,FMath::RadiansToDegrees(FMath::Atan2(E.Y,E.X)),0);Component->AddInstance(FTransform(Rot,C,Size/100));};
    auto Rail=[&](FVector C,FVector E,FVector O,double Width,double Depth){
        Box(MetalDetails,C+O*Depth+FVector(0,0,100),E,FVector(Width,4,4));Box(MetalDetails,C+O*Depth+FVector(0,0,12),E,FVector(Width,3,3));
        int32 Bars=FMath::Max(2,FMath::CeilToInt(Width/13));for(int32 j=0;j<=Bars;++j)Box(MetalDetails,C+E*(Width*(double(j)/Bars-.5))+O*Depth+FVector(0,0,55),E,FVector(2.5,2.5,90));
        for(double side:{-1.,1.}){Box(MetalDetails,C+E*Width*.5*side+O*Depth*.5+FVector(0,0,100),E,FVector(4,Depth,4));for(int32 j=0;j<=FMath::CeilToInt(Depth/15);++j)Box(MetalDetails,C+E*Width*.5*side+O*(Depth*j/FMath::CeilToInt(Depth/15))+FVector(0,0,55),E,FVector(2.5,2.5,90));}
    };
    for(int32 Facade=0;Facade<P.Num();++Facade){if(Facade!=Front && !bDetailSideFacades)continue;
    FVector2D A=P[Facade],B=P[(Facade+1)%P.Num()],E=(B-A).GetSafeNormal();
    FVector Edge(E.X,E.Y,0),Out(E.Y,-E.X,0);double L=FVector2D::Distance(A,B),WW=WindowWidthMeters*100,WH=WindowHeightMeters*100;
    int32 Count=FMath::Clamp(FMath::FloorToInt(L/FMath::Max(150.f,WindowSpacingMeters*100)),1,30);
    FVector Base(A.X,A.Y,0);
    if(L<200)continue;
    int32 Entrances=Facade==Front?FMath::Clamp(FMath::RoundToInt(L/(FacadeSectionWidthMeters*100)),1,8):0;
    for(int32 j=0;j<Entrances;++j)PlaceModule(Doors,DoorMesh,Base+Edge*(L*(j+.5)/Entrances)+Out*5+FVector(0,0,110),Edge,Out,110,220);
    Box(MasonryDetails,Base+Edge*(L*.5)+Out*9+FVector(0,0,40),Edge,FVector(L,22,80));
    for(int32 floor=1;floor<FloorCount;++floor){double Z=floor*FloorHeightMeters*100;Box(MasonryDetails,Base+Edge*(L*.5)+Out*13+FVector(0,0,Z-6),Edge,FVector(L,32,12));}
    // Cornices follow the separate top heights, never bridge a step with a flat strip.
    for(int32 s=0;s<Sections;++s){double aa=FVector2D::DotProduct(A,Along),ab=FVector2D::DotProduct(B,Along),lo=0,hi=1;
        if(FMath::Abs(ab-aa)>.01){double t1=(AlongMin+s*SectionWidth-aa)/(ab-aa),t2=(AlongMin+(s+1)*SectionWidth-aa)/(ab-aa);lo=FMath::Clamp(FMath::Min(t1,t2),0.,1.);hi=FMath::Clamp(FMath::Max(t1,t2),0.,1.);}else if(SectionAt((A+B)*.5)!=s)continue;
        if(hi-lo<.001)continue;double Z=Wall+HeightOffset(s);
        Box(MasonryDetails,Base+Edge*(L*(lo+hi)*.5)+Out*16+FVector(0,0,Z-8),Edge,FVector(L*(hi-lo),42,20));
        if(RoofRiseMeters<=0)Box(MasonryDetails,Base+Edge*(L*(lo+hi)*.5)-Out*8+FVector(0,0,Z+45),Edge,FVector(L*(hi-lo),20,90));
    }
    if(BalconyStyle==2)for(int32 floor=1;floor<FloorCount;++floor){double Width=FMath::Max(50.,L-40),Depth=BalconyDepthMeters*100,Z=floor*FloorHeightMeters*100;FVector C=Base+Edge*(L*.5)+FVector(0,0,Z);Box(MasonryDetails,C+Out*(Depth*.5)+FVector(0,0,-9),Edge,FVector(Width,Depth,18));Rail(C,Edge,Out,Width,Depth);}
    for(int32 floor=0;floor<FloorCount;++floor)for(int32 j=0;j<Count;++j){double D=L*(j+0.5)/Count;
        bool AtDoor=false;for(int32 k=0;k<Entrances;++k)if(FMath::Abs(D-L*(k+.5)/Entrances)<WW*.5+75)AtDoor=true;
        if(D<WW*0.6 || D>L-WW*0.6 || (floor==0 && AtDoor))continue;
        bool Balcony=floor>0 && (BalconyStyle==2 || (BalconyStyle==1 && (j+floor+CompositionSeed)%3!=0));
        double H=Balcony?220:WH,Sill=Balcony?8:90;double Z=floor*FloorHeightMeters*100;
        FVector Center=Base+Edge*D+Out*9+FVector(0,0,Z+Sill+H*.5);
        PlaceModule(Windows,WindowMesh,Center,Edge,Out,WW,H);
        FRotator Rot(0,FMath::RadiansToDegrees(FMath::Atan2(Edge.Y,Edge.X)),0);
        WindowBackings->AddInstance(FTransform(Rot,Center-Out*3,FVector(WW/100,0.03,H/100)));
        Box(MasonryDetails,Center+FVector(0,0,-H*.5-5)+Out*7,Edge,FVector(WW+24,32,12));
        Box(MasonryDetails,Center+FVector(0,0,H*.5+7),Edge,FVector(WW+24,22,14));
        for(double side:{-1.,1.}){Box(MasonryDetails,Center+Edge*(WW*.5+5)*side,Edge,FVector(10,20,H));if(bAddShutters && (j+CompositionSeed)%4!=0){FVector C=Center+Edge*(WW*.75+12)*side+Out*7;Box(Shutters,C,Edge,FVector(WW*.45,8,H));for(double z=-H*.5+12;z<H*.5;z+=18)Box(Shutters,C+Out*4+FVector(0,0,z),Edge,FVector(WW*.43,6,3));}}
        if(Balcony && BalconyStyle==1){double Width=FMath::Min(L/Count-30,WW+90),Depth=BalconyDepthMeters*100;FVector C=Base+Edge*D+FVector(0,0,Z);Box(MasonryDetails,C+Out*Depth*.5+FVector(0,0,-9),Edge,FVector(Width,Depth,18));Rail(C,Edge,Out,Width,Depth);}
    }
    // Narrow projecting strips divide long mapped blocks into legible house fronts.
    for(int32 j=1;j<Entrances;++j)Box(MasonryDetails,Base+Edge*(L*j/Entrances)+Out*6+FVector(0,0,Wall*.5),Edge,FVector(18,18,Wall));
    }
    if(bRoofTerrace && RoofRiseMeters<=0){
        // Place a small service room only when its complete rectangle lies inside the footprint.
        FVector2D C=FVector2D::ZeroVector;for(auto Q:P)C+=Q;C/=P.Num();FVector2D E=Along,O(-E.Y,E.X);
        auto Inside=[&](FVector2D Q){bool Result=false;for(int32 i=0,j=P.Num()-1;i<P.Num();j=i++)if((P[i].Y>Q.Y)!=(P[j].Y>Q.Y) && Q.X<(P[j].X-P[i].X)*(Q.Y-P[i].Y)/(P[j].Y-P[i].Y)+P[i].X)Result=!Result;return Result;};
        bool Fits=true;for(double x:{-180.,180.})for(double y:{-160.,160.})Fits &= Inside(C+E*x+O*y);
        if(Fits){FVector Edge(E.X,E.Y,0),Out(O.X,O.Y,0);double Z=RoofZ(C,SectionAt(C));FVector Center(C.X,C.Y,Z);Box(MasonryDetails,Center+FVector(0,0,125),Edge,FVector(360,320,250));Box(MasonryDetails,Center+FVector(0,0,255),Edge,FVector(390,350,16));PlaceModule(Windows,WindowMesh,Center-Out*164+FVector(0,0,150),Edge,-Out,85,105);}
    }
}
