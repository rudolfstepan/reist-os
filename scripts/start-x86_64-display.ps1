[CmdletBinding()]
param(
    [string]$Directory = '',
    [ValidateSet('hdd', 'floppy')][string]$Layout = 'hdd',
    [ValidateSet(4096, 8192)][int]$Ram = 4096,
    [ValidateRange(30, 320)][int]$Seconds = 320,
    [switch]$CheckOnly,
    [switch]$Headless,
    [string]$OpenSSL = ''
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$displayArgs = @((Join-Path $PSScriptRoot 'run_x86_64_display.py'), '--layout', $Layout, '--ram', "$Ram", '--seconds', "$Seconds")
if ($Directory) { $displayArgs += @('--directory', $Directory) }
if ($CheckOnly) { $displayArgs += '--check-only' }
if ($Headless) { $displayArgs += '--headless' }
if ($OpenSSL) { $displayArgs += @('--openssl', $OpenSSL) }
Push-Location $repoRoot
try {
    & python @displayArgs
    if ($LASTEXITCODE -ne 0) { throw "Grafikpruefung oder Sitzung fehlgeschlagen (Exit $LASTEXITCODE)." }
} finally {
    Pop-Location
}
