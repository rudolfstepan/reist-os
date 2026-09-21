[CmdletBinding()]
param(
    [string]$Directory = '',
    [ValidateSet('hdd', 'floppy')][string]$Layout = 'hdd',
    [ValidateSet(4096, 8192)][int]$Ram = 4096,
    [switch]$CheckOnly,
    [string]$OpenSSL = ''
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$cliArgs = @((Join-Path $PSScriptRoot 'run_x86_64_cli.py'), '--layout', $Layout, '--ram', "$Ram")
if ($Directory) { $cliArgs += @('--directory', $Directory) }
if ($CheckOnly) { $cliArgs += '--check-only' }
if ($OpenSSL) { $cliArgs += @('--openssl', $OpenSSL) }
Push-Location $repoRoot
try {
    & python @cliArgs
    if ($LASTEXITCODE -ne 0) { throw "CLI-Pruefung oder Sitzung fehlgeschlagen (Exit $LASTEXITCODE)." }
} finally {
    Pop-Location
}
