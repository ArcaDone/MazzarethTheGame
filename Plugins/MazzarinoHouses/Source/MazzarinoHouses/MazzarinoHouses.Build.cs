using UnrealBuildTool;

public class MazzarinoHouses : ModuleRules
{
    public MazzarinoHouses(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine", "GeometryCore", "GeometryFramework" });
        PrivateDependencyModuleNames.Add("Landscape");
    }
}
