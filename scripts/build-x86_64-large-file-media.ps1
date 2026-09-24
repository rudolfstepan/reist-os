[CmdletBinding()]
param(
    [ValidatePattern('^build(?:[\\/][A-Za-z0-9_.-]+)*$')]
    [string]$InputDirectory = 'build/x86_64',
    [ValidatePattern('^build[\\/]codex-agent(?:[\\/][A-Za-z0-9_.-]+)+$')]
    [string]$OutputDirectory = 'build/codex-agent/native-large-file-media'
)
$ErrorActionPreference = 'Stop'
$largeMediaWorkspace = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $largeMediaWorkspace
try {
    & python scripts/build_x86_64_large_file_media.py --input-directory $InputDirectory --output-directory $OutputDirectory
    if ($LASTEXITCODE -ne 0) { throw "Native large file media packaging failed ($LASTEXITCODE)." }
} finally { Pop-Location }
