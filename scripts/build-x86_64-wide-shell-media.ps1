[CmdletBinding()]
param(
    [ValidatePattern('^build(?:[\\/][A-Za-z0-9_.-]+)*$')]
    [string]$InputDirectory = 'build/x86_64',
    [ValidatePattern('^build[\\/]codex-agent(?:[\\/][A-Za-z0-9_.-]+)+$')]
    [string]$OutputDirectory = 'build/codex-agent/native-wide-shell-media'
)
# Packaging only: explicitly supply the already qualified NativeWideFile input.
$ErrorActionPreference = 'Stop'
$wideMediaWorkspace = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $wideMediaWorkspace
try {
    & python scripts/build_x86_64_wide_shell_media.py --input-directory $InputDirectory --output-directory $OutputDirectory
    if ($LASTEXITCODE -ne 0) { throw "Native wide shell media packaging failed ($LASTEXITCODE)." }
} finally {
    Pop-Location
}
