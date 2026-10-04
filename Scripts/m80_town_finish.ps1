# Finishes the town map after a district import: automatic shops on the main streets, street plaques
# and road signs, wires across the streets, bake of every house, beauty shots.
# Usage: powershell -ExecutionPolicy Bypass -File Scripts/m80_town_finish.ps1 [-SkipPhotos]
param([switch]$SkipPhotos)
$ErrorActionPreference = 'Stop'
$Root = Join-Path $PSScriptRoot '..' | Resolve-Path
Set-Location $Root
$Map = '/Game/Mazzarino80/Houses/Maps/L_M80_Paese'
$Run = Join-Path $PSScriptRoot 'run_editor_script.ps1'

function Step($Name, $Script, $Minutes, $Env) {
    foreach ($k in $Env.Keys) { Set-Item "Env:$k" $Env[$k] }
    Write-Output ("== {0} ({1})" -f $Name, (Get-Date -Format HH:mm))
    powershell -ExecutionPolicy Bypass -File $Run -Script $Script -TimeoutMinutes $Minutes
    foreach ($k in $Env.Keys) { Remove-Item "Env:$k" -ErrorAction SilentlyContinue }
}

Step 'Negozi e bar' 'Scripts/m80_houses_shops_demo.py' 60 @{ M80_SHOPS_MAP = $Map; M80_SHOPS = 'auto' }
Step 'Targhe e cartelli' 'Scripts/m80_signs_setup.py' 60 @{ M80_SIGNS_MAP = $Map; M80_SIGNS_SKIP_IMPORT = '1' }
Step 'Fili tra le case' 'Scripts/m80_street_wires_setup.py' 60 @{ M80_WIRES_MAP = $Map }
Step 'Cottura' 'Scripts/m80_houses_bake.py' 120 @{ M80_BAKE_MAP = $Map; M80_BAKE_CAPTURE = '0' }
if (-not $SkipPhotos) {
    Step 'Foto' 'Scripts/m80_photos.py' 60 @{ M80_PHOTOS_PREFIX = 'paese_' }
}
Write-Output ("== Fine ({0})" -f (Get-Date -Format HH:mm))
