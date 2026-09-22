[CmdletBinding()]
param(
    [ValidatePattern('^build(?:[\\/][A-Za-z0-9_.-]+)*$')]
    [string]$InputDirectory = 'build/x86_64',
    [ValidatePattern('^build[\\/]codex-agent(?:[\\/][A-Za-z0-9_.-]+)+$')]
    [string]$OutputDirectory = 'build/codex-agent/native-application-http-media'
)
$ErrorActionPreference = 'Stop'
$httpMediaWorkspace = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $httpMediaWorkspace
try {
    & python scripts/build_x86_64_application_http_media.py --input-directory $InputDirectory --output-directory $OutputDirectory
    if ($LASTEXITCODE -ne 0) { throw "Native HTTP media packaging failed ($LASTEXITCODE)." }
} finally { Pop-Location }
