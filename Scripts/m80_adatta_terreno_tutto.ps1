# Fits the whole town to the terrain (m80_adatta_terreno.py) a few tiles per editor: one editor for the whole town runs
# out of memory. Starts again from the report's "prossimo" tile, so it also resumes after a crash or a stop.
# A fresh start from tile 0: -DaCapo. Usage:
#   powershell -File Scripts/m80_adatta_terreno_tutto.ps1 [-Quanti 8] [-DaCapo]
param(
    [int]$Quanti = 8,
    [switch]$DaCapo
)
$Report = Join-Path $PSScriptRoot '..\Saved\Mazzarino80\Terreno\adatta_terreno.json'
$Runner = Join-Path $PSScriptRoot 'run_editor_script.ps1'
$Script = Join-Path $PSScriptRoot 'm80_adatta_terreno.py'
$Next = 0
if (-not $DaCapo -and (Test-Path $Report)) {
    $R = Get-Content $Report -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($R.finito) { Write-Output 'Gia finito: -DaCapo per rifarlo tutto.'; exit 0 }
    if ($R.prossimo) { $Next = [int]$R.prossimo }
}
$Failures = 0
while ($true) {
    Write-Output ("{0:HH:mm} riquadri da {1} a {2}" -f (Get-Date), $Next, ($Next + $Quanti - 1))
    $env:M80_DA = "$Next"
    $env:M80_QUANTI = "$Quanti"
    & powershell -File $Runner -Script $Script -TimeoutMinutes 120 | Select-Object -Last 1
    $R = Get-Content $Report -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($R.finito) { break }
    $Done = [int]$R.prossimo
    if ($Done -le $Next) {
        # Crashed before finishing a single tile: try that tile again, then give up.
        $Failures += 1
        if ($Failures -ge 2) { Write-Output "Fermo: il riquadro $Next non riesce."; exit 1 }
    } else {
        $Failures = 0
    }
    $Next = $Done
}
Remove-Item Env:M80_DA, Env:M80_QUANTI
Write-Output ("Finito: {0} case rifatte, {1} invariate, {2} marciapiedi/strade/scale rifatti, {3} minuti" -f `
    $R.case_rifatte.Count, $R.invariati.case, $R.seguono_rifatti.Count, $R.minuti)
