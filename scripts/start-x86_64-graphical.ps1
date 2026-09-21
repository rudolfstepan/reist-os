[CmdletBinding()]
param(
    [ValidateSet('hdd', 'floppy')][string]$Layout = 'hdd',
    [ValidateSet(4096, 8192)][int]$Ram = 4096,
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$graphicalArgs = @((Join-Path $PSScriptRoot 'run_qemu_x86_64_graphical_session.py'), '--layout', $Layout, '--ram', "$Ram")
if ($CheckOnly) { $graphicalArgs += '--check-only' } else { $graphicalArgs += '--launch' }
Push-Location $repoRoot
try {
    & python @graphicalArgs
    if ($LASTEXITCODE -ne 0) { throw "Grafik-Pruefung oder Sitzung fehlgeschlagen (Exit $LASTEXITCODE)." }
} finally {
    Pop-Location
}
