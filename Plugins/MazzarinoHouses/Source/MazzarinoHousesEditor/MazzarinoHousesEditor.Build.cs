using UnrealBuildTool;

public class MazzarinoHousesEditor : ModuleRules
{
    public MazzarinoHousesEditor(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine" });
        PrivateDependencyModuleNames.AddRange(new[] { "TextureUtilitiesCommon", "TargetPlatform", "UnrealEd", "MazzarinoHouses",
            "GeometryCore", "GeometryFramework", "MeshConversion", "MeshDescription", "StaticMeshDescription", "ModelingComponentsEditorOnly", "Landscape", "RenderCore", "Foliage" });
    }
}
