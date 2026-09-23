[CmdletBinding()]
param(
    [ValidatePattern('^build(?:[\\/][A-Za-z0-9_.-]+)*$')]
    [string]$InputDirectory = 'build/x86_64',
    [ValidatePattern('^build[\\/]codex-agent(?:[\\/][A-Za-z0-9_.-]+)+$')]
    [string]$OutputDirectory = 'build/codex-agent/native-text-runtime-media'
)
$ErrorActionPreference = 'Stop'
$textMediaWorkspace = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $textMediaWorkspace
try {
    & python scripts/build_x86_64_text_runtime_media.py --input-directory $InputDirectory --output-directory $OutputDirectory
    if ($LASTEXITCODE -ne 0) { throw "Native text media packaging failed ($LASTEXITCODE)." }
} finally { Pop-Location }
