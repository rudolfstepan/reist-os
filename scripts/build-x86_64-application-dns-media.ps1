[CmdletBinding()]
param(
    [ValidatePattern('^build(?:[\\/][A-Za-z0-9_.-]+)*$')]
    [string]$InputDirectory = 'build/x86_64',
    [ValidatePattern('^build[\\/]codex-agent(?:[\\/][A-Za-z0-9_.-]+)+$')]
    [string]$OutputDirectory = 'build/codex-agent/native-application-dns-media'
)
$ErrorActionPreference = 'Stop'
$dnsMediaWorkspace = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $dnsMediaWorkspace
try {
    & python scripts/build_x86_64_application_dns_media.py --input-directory $InputDirectory --output-directory $OutputDirectory
    if ($LASTEXITCODE -ne 0) { throw "Native DNS media packaging failed ($LASTEXITCODE)." }
} finally { Pop-Location }
