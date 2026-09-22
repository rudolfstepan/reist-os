[CmdletBinding()]
param(
    [ValidatePattern('^build(?:[\\/][A-Za-z0-9_.-]+)*$')]
    [string]$InputDirectory = 'build/x86_64',
    [ValidatePattern('^build[\\/]codex-agent(?:[\\/][A-Za-z0-9_.-]+)+$')]
    [string]$OutputDirectory = 'build/codex-agent/native-application-udp-media'
)
$ErrorActionPreference = 'Stop'
$udpMediaWorkspace = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $udpMediaWorkspace
try {
    & python scripts/build_x86_64_application_udp_media.py --input-directory $InputDirectory --output-directory $OutputDirectory
    if ($LASTEXITCODE -ne 0) { throw "Native UDP media packaging failed ($LASTEXITCODE)." }
} finally { Pop-Location }
