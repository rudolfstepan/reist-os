[CmdletBinding()]
param(
    [ValidatePattern('^build(?:[\\/][A-Za-z0-9_.-]+)*$')]
    [string]$InputDirectory = 'build/x86_64',
    [ValidatePattern('^build[\\/]codex-agent(?:[\\/][A-Za-z0-9_.-]+)+$')]
    [string]$OutputDirectory = 'build/codex-agent/native-shell-media'
)
# Packaging only. Obtain the input explicitly with -NativeShellSession first;
# this wrapper never rebuilds a kernel or alters the old NativeImages preset.
$ErrorActionPreference = 'Stop'
$mediaWorkspace = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $mediaWorkspace
try {
    & python scripts/build_x86_64_shell_media.py --input-directory $InputDirectory --output-directory $OutputDirectory
    if ($LASTEXITCODE -ne 0) { throw "Native shell media packaging failed ($LASTEXITCODE)." }
} finally {
    Pop-Location
}
