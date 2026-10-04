using UnrealBuildTool;

public class MazzarinoRoads : ModuleRules
{
    public MazzarinoRoads(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        // Several .cpp files define file-local geometry helpers with the same names.
        bUseUnity = false;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine", "ProceduralMeshComponent", "PCG" });
    }
}
