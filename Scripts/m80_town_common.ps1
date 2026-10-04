# Town map update with the hand-made buildings and the shared "Comune" assets (L_M80_Paese):
# exclusion zones around the hand-made buildings, roads painted on the landscape, worn signs, posters,
# neoclassic palaces, parked cars, sidewalks. Each step saves the map; a failed step stops the chain.
# Usage: powershell -ExecutionPolicy Bypass -File Scripts/m80_town_common.ps1 [-From 2]
param([int]$From = 1)
Set-Location (Join-Path $PSScriptRoot '..')
$steps = @(
    @{ Script = 'Scripts/m80_town_zones.py'; Report = 'Saved/Mazzarino80/zones_report' },
    @{ Script = 'Scripts/m80_town_roads.py'; Report = 'Saved/Mazzarino80/Terrain/roads_report' },
    @{ Script = 'Scripts/m80_town_props.py'; Report = 'Saved/Mazzarino80/props_report' },
    @{ Script = 'Scripts/m80_town_sidewalks.py'; Report = 'Saved/Mazzarino80/sidewalks_report' }
)
for ($i = $From - 1; $i -lt $steps.Count; $i++) {
    $s = $steps[$i]
    Remove-Item "$($s.Report).error.txt" -ErrorAction SilentlyContinue
    Write-Output ("[{0}] step {1}: {2}" -f (Get-Date -Format HH:mm:ss), ($i + 1), $s.Script)
    & powershell -ExecutionPolicy Bypass -File Scripts/run_editor_script.ps1 -Script $s.Script -TimeoutMinutes 90
    if (Test-Path "$($s.Report).error.txt") {
        Write-Output "FAILED:"
        Get-Content "$($s.Report).error.txt"
        exit 1
    }
    if (-not (Test-Path "$($s.Report).json")) {
        Write-Output "FAILED: no report"
        exit 1
    }
    Get-Content "$($s.Report).json" -TotalCount 40
}
Write-Output ("[{0}] done" -f (Get-Date -Format HH:mm:ss))
