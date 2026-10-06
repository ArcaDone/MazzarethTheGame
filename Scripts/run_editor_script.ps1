# Runs an editor Python script that drives the editor over several frames (m80_seq.Sequencer)
# and waits for the editor to quit. Usage:
#   powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_profile_scene.py [-TimeoutMinutes 30]
# -ExecutePythonScript would quit the editor right after the script returns, so the script is
# started with "py" through -ExecCmds instead. Background CPU throttling is disabled so the
# viewport keeps rendering while the window is not focused.
# -ForceLit: photo scripts render through the level viewport, so perspective viewports left in
# Unlit (or another view mode) are switched to Lit for the run and put back as they were afterwards.
param(
    [Parameter(Mandatory = $true)][string]$Script,
    [int]$TimeoutMinutes = 30,
    [switch]$ForceLit
)
$Project = Join-Path $PSScriptRoot '..\MazzarethTheGame.uproject' | Resolve-Path
$ScriptPath = (Resolve-Path $Script).Path -replace '\\', '/'
$Editor = 'D:\UE_5.5\Engine\Binaries\Win64\UnrealEditor.exe'
$EditorArgs = @(
    "`"$Project`"",
    "-ExecCmds=`"py $ScriptPath`"",
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False',
    '-nosplash'
)
$UserIni = Join-Path $PSScriptRoot '..\Saved\Config\WindowsEditor\EditorPerProjectUserSettings.ini'
$Restore = @{}
if ($ForceLit -and (Test-Path $UserIni)) {
    $Text = [IO.File]::ReadAllText($UserIni)
    $Pattern = 'ConfigName="([^"]+)",ConfigSettings=\(ViewportType=LVT_Perspective,PerspViewModeIndex=(VMI_\w+)'
    foreach ($M in [regex]::Matches($Text, $Pattern)) {
        if ($M.Groups[2].Value -ne 'VMI_Lit') { $Restore[$M.Groups[1].Value] = $M.Groups[2].Value }
    }
    foreach ($Name in $Restore.Keys) {
        $Text = $Text.Replace("ConfigName=`"$Name`",ConfigSettings=(ViewportType=LVT_Perspective,PerspViewModeIndex=$($Restore[$Name])",
                              "ConfigName=`"$Name`",ConfigSettings=(ViewportType=LVT_Perspective,PerspViewModeIndex=VMI_Lit")
    }
    [IO.File]::WriteAllText($UserIni, $Text)
}
$Process = Start-Process $Editor -ArgumentList $EditorArgs -PassThru
$Finished = $Process.WaitForExit($TimeoutMinutes * 60 * 1000)
if (-not $Finished) {
    Stop-Process -Id $Process.Id -Force
    Start-Sleep -Seconds 5
}
if ($Restore.Count -gt 0) {
    $Text = [IO.File]::ReadAllText($UserIni)
    foreach ($Name in $Restore.Keys) {
        $Text = [regex]::Replace($Text, 'ConfigName="' + [regex]::Escape($Name) + '",ConfigSettings=\(ViewportType=LVT_Perspective,PerspViewModeIndex=VMI_\w+',
                                 "ConfigName=`"$Name`",ConfigSettings=(ViewportType=LVT_Perspective,PerspViewModeIndex=$($Restore[$Name])")
    }
    [IO.File]::WriteAllText($UserIni, $Text)
}
if (-not $Finished) {
    Write-Output "TIMEOUT after $TimeoutMinutes minutes"
    exit 1
}
Write-Output "Editor exited with code $($Process.ExitCode)"
