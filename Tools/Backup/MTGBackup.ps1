# Daily backup of Mazzareth The Game sources (scheduled task MTGBackup, 13:00, to C:\MTGBackup).
# Copies new and changed files only; never deletes anything from the backup,
# so files removed by mistake on D: stay recoverable here.
# Regenerable folders (caches, build output) and Blender .blend1 files are skipped.
# External drive: powershell -ExecutionPolicy Bypass -File Tools\Backup\MTGBackup.ps1 -Dest E:\MTGBackup
# (the first run copies everything, the next ones only the differences).
# The project backed up is the one this script lives in (or -Project). It goes to
# <Dest>\GameAnimationSample_UE<EngineAssociation of the .uproject>, so the 5.8 project never mixes
# with the 5.5 backups kept in <Dest>\GameAnimationSample (nothing is deleted, stale files would pile up).
#
# -Transfer: a clean copy to move the project to another PC, in <Dest>\Trasferimento with the same
# layout as D:\ (UE5Projects\GameAnimationSample, UE5Projects\Comune, Mazzarino80_Sorgenti (since 2026-10-17 also
# the old Blender\AssetsMazzarethTheGame, sorted by kind and in Blender_Storico), HDRI, Audio_Music), plus ClaudeMemory (Claude Code's notes, from the user profile).
# It mirrors D: exactly (files deleted on D: are deleted from the copy too, so removed World
# Partition actors do not come back) and includes .git (with the LFS files) and the compiled
# Binaries, so the project opens without Visual Studio on a PC with the same Unreal version.
# Caches, Intermediate and Saved are left out. Close the editor first.
#   powershell -ExecutionPolicy Bypass -File Tools\Backup\MTGBackup.ps1 -Transfer -Dest E:\MTGBackup
param([string]$Dest = 'C:\MTGBackup', [switch]$Transfer, [string]$Project = (Resolve-Path "$PSScriptRoot\..\..").Path)

$ErrorActionPreference = 'Stop'

$Engine = (Get-Content (Join-Path $Project 'MazzarethTheGame.uproject') -Raw | ConvertFrom-Json).EngineAssociation
$ProjectBackup = "$Dest\GameAnimationSample_UE$Engine"

if (-not (Test-Path (Split-Path $Dest -Qualifier))) { throw "Drive not found: $Dest" }
$LogDir = Join-Path $Dest '_logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ("{0}_{1:yyyy-MM-dd_HHmm}.log" -f $(if ($Transfer) { 'transfer' } else { 'backup' }), (Get-Date))

$CommonArgs = @('/E', '/COPY:DAT', '/DCOPY:T', '/R:2', '/W:5', '/MT:8', '/NP', '/NDL', '/FFT', "/LOG+:$Log")

$Jobs = @(
    @{  # Main Unreal project (history is on GitHub, so .git is skipped)
        Src = $Project
        Dst = $ProjectBackup
        XD  = @('.git','.git_old', '.vs', 'Binaries', 'Intermediate', 'DerivedDataCache', 'Saved', '__pycache__')
        XF  = @('*.blend1', '*.tmp', '*.pyc')
    },
    @{  # Editor autosaves and Mazzarino80 work backups/reports
        Src = "$Project\Saved\Autosaves"
        Dst = "$ProjectBackup\Saved\Autosaves"
        XD  = @(); XF = @()
    },
    @{
        Src = "$Project\Saved\Mazzarino80"
        Dst = "$ProjectBackup\Saved\Mazzarino80"
        XD  = @(); XF = @('*.tmp')
    },
    @{  # Comune: only its Migrated folder (the user's own models, not in the Epic library). The game holds its own
        # copy of every asset it uses and the marketplace packs can be downloaded again, so since 2026-10-20 the
        # rest of the Comune project (about 95 GB) is no longer backed up.
        Src = 'D:\UE5Projects\Comune\Content\Migrated'
        Dst = "$Dest\Comune_Migrated"
        XD  = @(); XF = @('*.tmp')
    },
    @{  # Every source file brought into the game, by kind (animations, cars, buildings, interiors, references...), and
        # the old D:\Blender\AssetsMazzarethTheGame (moved here 2026-10-17: Blender_Storico and the kind folders)
        Src = 'D:\Mazzarino80_Sorgenti'
        Dst = "$Dest\Mazzarino80_Sorgenti"
        XD  = @()
        XF  = @('*.blend1', '*.blend2')
    },
    @{  # HDRI skies and music sources
        Src = 'D:\HDRI'
        Dst = "$Dest\HDRI"
        XD  = @(); XF = @()
    },
    @{
        Src = 'D:\Audio_Music'
        Dst = "$Dest\Audio_Music"
        XD  = @(); XF = @()
    },
    @{  # Claude Code's notes on this project (decisions, pitfalls, where the work stands)
        Src = "$env:USERPROFILE\.claude\projects\D--UE5Projects-GameAnimationSample\memory"
        Dst = "$Dest\ClaudeMemory"
        XD  = @(); XF = @()
    }
)

if ($Transfer) {
    if (Get-Process UnrealEditor*, UnrealEditor-Cmd -ErrorAction SilentlyContinue) { throw 'Close Unreal Editor before the transfer copy.' }
    $Root = Join-Path $Dest 'Trasferimento'
    # /MIR deletes from the destination what is no longer on D:, only inside this folder.
    $CommonArgs = @('/MIR', '/COPY:DAT', '/DCOPY:T', '/R:2', '/W:5', '/MT:8', '/NP', '/NDL', '/FFT', "/LOG+:$Log")
    $Jobs = @(
        @{
            Src = $Project
            Dst = "$Root\UE5Projects\GameAnimationSample"
            XD  = @('.git_old', '.vs', 'Intermediate', 'DerivedDataCache', 'Saved', '__pycache__')
            XF  = @('*.blend1', '*.tmp', '*.pyc')
        },
        @{
            Src = 'D:\UE5Projects\Comune'
            Dst = "$Root\UE5Projects\Comune"
            XD  = @('Intermediate', 'DerivedDataCache', 'Saved')
            XF  = @('*.tmp')
        },
        @{
            Src = 'D:\Mazzarino80_Sorgenti'
            Dst = "$Root\Mazzarino80_Sorgenti"
            XD  = @()
            XF  = @('*.blend1', '*.blend2')
        },
        @{
            Src = 'D:\HDRI'
            Dst = "$Root\HDRI"
            XD  = @(); XF = @()
        },
        @{
            Src = 'D:\Audio_Music'
            Dst = "$Root\Audio_Music"
            XD  = @(); XF = @()
        },
        @{  # Goes back to <user profile>\.claude\projects\D--UE5Projects-GameAnimationSample\memory
            Src = "$env:USERPROFILE\.claude\projects\D--UE5Projects-GameAnimationSample\memory"
            Dst = "$Root\ClaudeMemory"
            XD  = @(); XF = @()
        }
    )
}

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
foreach ($Kind in 'backup', 'transfer') {
    Get-ChildItem $LogDir -Filter "${Kind}_*.log" | Sort-Object Name -Descending | Select-Object -Skip 60 | Remove-Item -Force
}

if ($Failed) { exit 1 }
