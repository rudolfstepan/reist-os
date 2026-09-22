[CmdletBinding()]
param(
    [ValidatePattern('^build(?:[\\/][A-Za-z0-9_.-]+)*$')]
    [string]$InputDirectory = 'build/x86_64',
    [ValidatePattern('^build[\\/]codex-agent(?:[\\/][A-Za-z0-9_.-]+)+$')]
    [string]$OutputDirectory = 'build/codex-agent/native-network-media'
)
$ErrorActionPreference = 'Stop'
$networkMediaWorkspace = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $networkMediaWorkspace
try {
    & python scripts/build_x86_64_network_media.py --input-directory $InputDirectory --output-directory $OutputDirectory
    if ($LASTEXITCODE -ne 0) { throw "Native network media packaging failed ($LASTEXITCODE)." }
} finally { Pop-Location }
