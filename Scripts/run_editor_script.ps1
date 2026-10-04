# Runs an editor Python script that drives the editor over several frames (m80_seq.Sequencer)
# and waits for the editor to quit. Usage:
#   powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_profile_scene.py [-TimeoutMinutes 30]
# -ExecutePythonScript would quit the editor right after the script returns, so the script is
# started with "py" through -ExecCmds instead. Background CPU throttling is disabled so the
# viewport keeps rendering while the window is not focused.
param(
    [Parameter(Mandatory = $true)][string]$Script,
    [int]$TimeoutMinutes = 30
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
$Process = Start-Process $Editor -ArgumentList $EditorArgs -PassThru
if (-not $Process.WaitForExit($TimeoutMinutes * 60 * 1000)) {
    Stop-Process -Id $Process.Id -Force
    Write-Output "TIMEOUT after $TimeoutMinutes minutes"
    exit 1
}
Write-Output "Editor exited with code $($Process.ExitCode)"
