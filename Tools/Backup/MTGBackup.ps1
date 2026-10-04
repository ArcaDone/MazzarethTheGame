# Daily backup of Mazzareth The Game sources (scheduled task MTGBackup, 13:00, to C:\MTGBackup).
# Copies new and changed files only; never deletes anything from the backup,
# so files removed by mistake on D: stay recoverable here.
# Regenerable folders (caches, build output) and Blender .blend1 files are skipped.
# External drive: powershell -ExecutionPolicy Bypass -File Tools\Backup\MTGBackup.ps1 -Dest E:\MTGBackup
# (the first run copies everything, the next ones only the differences).
param([string]$Dest = 'C:\MTGBackup')

$ErrorActionPreference = 'Stop'

if (-not (Test-Path (Split-Path $Dest -Qualifier))) { throw "Drive not found: $Dest" }
$LogDir = Join-Path $Dest '_logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ("backup_{0:yyyy-MM-dd_HHmm}.log" -f (Get-Date))

$CommonArgs = @('/E', '/COPY:DAT', '/DCOPY:T', '/R:2', '/W:5', '/MT:8', '/NP', '/NDL', '/FFT', "/LOG+:$Log")

$Jobs = @(
    @{  # Main Unreal project (history is on GitHub, so .git is skipped)
        Src = 'D:\UE5Projects\GameAnimationSample'
        Dst = "$Dest\GameAnimationSample"
        XD  = @('.git', '.vs', 'Binaries', 'Intermediate', 'DerivedDataCache', 'Saved', '__pycache__')
        XF  = @('*.blend1', '*.tmp', '*.pyc')
    },
    @{  # Editor autosaves and Mazzarino80 work backups/reports
        Src = 'D:\UE5Projects\GameAnimationSample\Saved\Autosaves'
        Dst = "$Dest\GameAnimationSample\Saved\Autosaves"
        XD  = @(); XF = @()
    },
    @{
        Src = 'D:\UE5Projects\GameAnimationSample\Saved\Mazzarino80'
        Dst = "$Dest\GameAnimationSample\Saved\Mazzarino80"
        XD  = @(); XF = @('*.tmp')
    },
    @{  # Comune: source project for buildings and materials
        Src = 'D:\UE5Projects\Comune'
        Dst = "$Dest\Comune"
        XD  = @('Binaries', 'Intermediate', 'DerivedDataCache', 'Saved')
        XF  = @('*.tmp')
    },
    @{  # Blender sources (CaseSoluzione.blend etc.)
        Src = 'D:\Blender\AssetsMazzarethTheGame'
        Dst = "$Dest\Blender_AssetsMazzarethTheGame"
        XD  = @()
        XF  = @('*.blend1', '*.blend2')
    }
)

$Failed = $false
foreach ($Job in $Jobs) {
    if (-not (Test-Path $Job.Src)) {
        Add-Content $Log "SKIPPED (missing source): $($Job.Src)"
        continue
    }
    $RoboArgs = @($Job.Src, $Job.Dst) + $CommonArgs
    if ($Job.XD.Count) { $RoboArgs += '/XD'; $RoboArgs += $Job.XD }
    if ($Job.XF.Count) { $RoboArgs += '/XF'; $RoboArgs += $Job.XF }
    & robocopy @RoboArgs | Out-Null
    # Robocopy exit codes 0-7 are success; 8 and above mean some files failed.
    if ($LASTEXITCODE -ge 8) {
        $Failed = $true
        Add-Content $Log "FAILED ($LASTEXITCODE): $($Job.Src)"
    }
}

Add-Content $Log ("FINISHED {0:yyyy-MM-dd HH:mm} - {1}" -f (Get-Date), $(if ($Failed) { 'WITH ERRORS' } else { 'OK' }))

# Keep the last 60 logs
Get-ChildItem $LogDir -Filter 'backup_*.log' | Sort-Object Name -Descending | Select-Object -Skip 60 | Remove-Item -Force

if ($Failed) { exit 1 }
