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
$inputArgs = @((Join-Path $PSScriptRoot 'run_x86_64_input.py'), '--layout', $Layout, '--ram', "$Ram", '--seconds', "$Seconds")
if ($Directory) { $inputArgs += @('--directory', $Directory) }
if ($CheckOnly) { $inputArgs += '--check-only' }
if ($Headless) { $inputArgs += '--headless' }
if ($OpenSSL) { $inputArgs += @('--openssl', $OpenSSL) }
Push-Location $repoRoot
try {
    & python @inputArgs
    if ($LASTEXITCODE -ne 0) { throw "Eingabepruefung oder Sitzung fehlgeschlagen (Exit $LASTEXITCODE)." }
} finally {
    Pop-Location
}
