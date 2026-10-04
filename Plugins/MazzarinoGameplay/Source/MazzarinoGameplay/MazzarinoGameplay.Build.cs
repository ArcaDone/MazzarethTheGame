using UnrealBuildTool;

public class MazzarinoGameplay : ModuleRules
{
    public MazzarinoGameplay(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput", "ChaosVehicles", "RenderCore", "AnimGraphRuntime", "AnimationCore",
            "MazzarinoVehicles", "MazzarinoRoads" });
    }
}
