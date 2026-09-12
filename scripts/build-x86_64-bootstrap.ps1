[CmdletBinding()]
param(
    [ValidatePattern('^build(?:[\\/][A-Za-z0-9_.-]+)*$')]
    [string]$OutputDirectory = 'build',
    [ValidateSet(-1, 0, 3, 6, 13, 14, 16)] [int]$FaultVector = -1,
    [ValidateRange(0, 3)] [int]$FaultPhase = 0,
    [switch]$BusyChild,
    [switch]$InvalidBusyStack,
    [ValidateRange(0, 7)] [int]$ContextCase = 0,
    [ValidateRange(-1, 4294967295)] [long]$ExitStatus = -1,
    [ValidateRange(0, 3)] [int]$IpcCase = 0,
    [ValidateRange(0, 4)] [int]$ArgvCase = 0,
    [ValidateRange(0, 3)] [int]$RequestCase = 0,
    [ValidateRange(0, 1)] [int]$OomCase = 0,
    [ValidateRange(0, 1)] [int]$ProfileCase = 0,
    [ValidateRange(0, 4)] [int]$MappingCase = 0,
    [ValidateRange(0, 3)] [int]$InstructionCase = 0,
    [ValidateRange(-1, 4294967295)] [long]$ShellExitStatus = -1,
    [switch]$OwnerTerminal,
    [switch]$NativeProcesses,
    [ValidateRange(0, 8)] [int]$ProcessCase = 0
)

Set-StrictMode -Version Latest
if ($ProcessCase -ne 0 -and -not $NativeProcesses) {
    throw 'ProcessCase requires NativeProcesses.'
}
if ($NativeProcesses -and ($OwnerTerminal -or $ShellExitStatus -ge 0 -or $InstructionCase -ne 0 -or $MappingCase -ne 0 -or $ProfileCase -ne 0 -or $OomCase -ne 0 -or $RequestCase -ne 0 -or $IpcCase -ne 0 -or $ArgvCase -ne 0 -or $ExitStatus -ge 0 -or $ContextCase -ne 0 -or $BusyChild -or $InvalidBusyStack -or $FaultVector -ge 0 -or $FaultPhase -ne 0)) {
    throw 'NativeProcesses is exclusive with shell fixtures.'
}
if ($OwnerTerminal -and ($ShellExitStatus -ge 0 -or $InstructionCase -ne 0 -or $MappingCase -ne 0 -or $ProfileCase -ne 0 -or $OomCase -ne 0 -or $RequestCase -ne 0 -or $IpcCase -ne 0 -or $ArgvCase -ne 0 -or $ExitStatus -ge 0 -or $ContextCase -ne 0 -or $BusyChild -or $InvalidBusyStack -or $FaultVector -ge 0 -or $FaultPhase -ne 0)) {
    throw 'OwnerTerminal is exclusive with other user fixtures.'
}
if ($ShellExitStatus -ge 0 -and ($InstructionCase -ne 0 -or $MappingCase -ne 0 -or $ProfileCase -ne 0 -or $OomCase -ne 0 -or $RequestCase -ne 0 -or $IpcCase -ne 0 -or $ArgvCase -ne 0 -or $ExitStatus -ge 0 -or $ContextCase -ne 0 -or $BusyChild -or $InvalidBusyStack -or $FaultVector -ge 0 -or $FaultPhase -ne 0)) {
    throw 'ShellExitStatus is exclusive with other user fixtures.'
}
if ($InstructionCase -ne 0 -and ($MappingCase -ne 0 -or $ProfileCase -ne 0 -or $OomCase -ne 0 -or $RequestCase -ne 0 -or $IpcCase -ne 0 -or $ArgvCase -ne 0 -or $ExitStatus -ge 0 -or $ContextCase -ne 0 -or $BusyChild -or $InvalidBusyStack -or $FaultVector -ge 0 -or $FaultPhase -ne 0)) {
    throw 'InstructionCase is exclusive with other user fixtures.'
}
if ($MappingCase -ne 0 -and ($ProfileCase -ne 0 -or $OomCase -ne 0 -or $RequestCase -ne 0 -or $IpcCase -ne 0 -or $ArgvCase -ne 0 -or $ExitStatus -ge 0 -or $ContextCase -ne 0 -or $BusyChild -or $InvalidBusyStack -or $FaultVector -ge 0 -or $FaultPhase -ne 0)) {
    throw 'MappingCase is exclusive with other user fixtures.'
}
if ($ProfileCase -ne 0 -and ($OomCase -ne 0 -or $RequestCase -ne 0 -or $IpcCase -ne 0 -or $ArgvCase -ne 0 -or $ExitStatus -ge 0 -or $ContextCase -ne 0 -or $BusyChild -or $InvalidBusyStack -or $FaultVector -ge 0 -or $FaultPhase -ne 0)) {
    throw 'ProfileCase is exclusive with other user fixtures.'
}
if ($OomCase -ne 0 -and ($RequestCase -ne 0 -or $IpcCase -ne 0 -or $ArgvCase -ne 0 -or $ExitStatus -ge 0 -or $ContextCase -ne 0 -or $BusyChild -or $InvalidBusyStack -or $FaultVector -ge 0 -or $FaultPhase -ne 0)) {
    throw 'OomCase is exclusive with other user fixtures.'
}
if ($RequestCase -ne 0 -and ($IpcCase -ne 0 -or $ArgvCase -ne 0 -or $ExitStatus -ge 0 -or $ContextCase -ne 0 -or $BusyChild -or $InvalidBusyStack -or $FaultVector -ge 0 -or $FaultPhase -ne 0)) {
    throw 'RequestCase is exclusive with other user fixtures.'
}
if ($IpcCase -ne 0 -and ($ArgvCase -ne 0 -or $ExitStatus -ge 0 -or $ContextCase -ne 0 -or $BusyChild -or $FaultVector -ge 0 -or $FaultPhase -ne 0)) {
    throw 'IpcCase is exclusive with other user fixtures.'
}
$ErrorActionPreference = 'Stop'
if (($BusyChild -and $FaultVector -ge 0) -or ($InvalidBusyStack -and -not $BusyChild)) {
    throw 'Busy and fault fixtures are exclusive; InvalidBusyStack requires BusyChild.'
}
if ($ContextCase -ne 0 -and ($BusyChild -or $FaultVector -ge 0)) {
    throw 'ContextCase is exclusive with BusyChild and FaultVector.'
}
if ($ExitStatus -ge 0 -and ($ContextCase -ne 0 -or $BusyChild -or $FaultVector -ge 0)) {
    throw 'ExitStatus is exclusive with context, busy and fault fixtures.'
}
if ($ArgvCase -ne 0 -and ($ExitStatus -ge 0 -or $ContextCase -ne 0 -or $BusyChild -or $FaultVector -ge 0 -or $FaultPhase -ne 0)) {
    throw 'ArgvCase is exclusive with other fixture modes and phases.'
}

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path

function Resolve-NativeTool {
    param(
        [Parameter(Mandatory)] [string]$Name,
        [Parameter(Mandatory)] [string[]]$Fallbacks
    )
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    foreach ($candidate in $Fallbacks) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    throw "Required native Windows tool '$Name' was not found."
}

function To-MakePath([string]$Path) {
    return $Path.Replace('\', '/')
}

function Read-Elf64Layout {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [switch]$RequireExecutable,
        [switch]$RequireLinked
    )
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -lt 64 -or $bytes[0] -ne 0x7F -or
        $bytes[1] -ne 0x45 -or $bytes[2] -ne 0x4C -or
        $bytes[3] -ne 0x46 -or $bytes[4] -ne 2 -or $bytes[5] -ne 1) {
        throw "Artifact is not a little-endian ELFCLASS64 file: $Path"
    }
    if ([BitConverter]::ToUInt16($bytes, 18) -ne 62) {
        throw "Artifact is not for EM_X86_64: $Path"
    }
    if ($RequireExecutable -and [BitConverter]::ToUInt16($bytes, 16) -ne 2) {
        throw "Bootstrap is not an ELF64 ET_EXEC artifact."
    }

    $programOffset = [BitConverter]::ToUInt64($bytes, 32)
    $programEntrySize = [BitConverter]::ToUInt16($bytes, 54)
    $programCount = [BitConverter]::ToUInt16($bytes, 56)
    if ($programCount -gt 32 -or ($programCount -gt 0 -and $programEntrySize -lt 56)) {
        throw "ELF64 program-header table is outside its fixed bounds."
    }
    for ($index = 0; $index -lt $programCount; ++$index) {
        $offset = $programOffset + ($index * $programEntrySize)
        if ($offset + 56 -gt $bytes.Length) {
            throw "ELF64 program-header table exceeds the artifact."
        }
        $type = [BitConverter]::ToUInt32($bytes, [int]$offset)
        $flags = [BitConverter]::ToUInt32($bytes, [int]$offset + 4)
        if ($type -eq 1 -and ($flags -band 3) -eq 3) {
            throw "Bootstrap contains a writable-executable PT_LOAD segment."
        }
    }

    $sectionOffset = [BitConverter]::ToUInt64($bytes, 40)
    $sectionEntrySize = [BitConverter]::ToUInt16($bytes, 58)
    $sectionCount = [BitConverter]::ToUInt16($bytes, 60)
    $stringIndex = [BitConverter]::ToUInt16($bytes, 62)
    if ($sectionCount -eq 0 -or $sectionCount -gt 128 -or
        $sectionEntrySize -lt 64 -or $stringIndex -ge $sectionCount) {
        throw "ELF64 section-header table is outside its fixed bounds."
    }
    if ($sectionOffset + ($sectionCount * $sectionEntrySize) -gt $bytes.Length) {
        throw "ELF64 section-header table exceeds the artifact."
    }
    $stringHeader = $sectionOffset + ($stringIndex * $sectionEntrySize)
    $stringOffset = [BitConverter]::ToUInt64($bytes, [int]$stringHeader + 24)
    $stringSize = [BitConverter]::ToUInt64($bytes, [int]$stringHeader + 32)
    if ($stringOffset + $stringSize -gt $bytes.Length) {
        throw "ELF64 section-name table exceeds the artifact."
    }

    for ($index = 1; $index -lt $sectionCount; ++$index) {
        $offset = $sectionOffset + ($index * $sectionEntrySize)
        $nameOffset = [BitConverter]::ToUInt32($bytes, [int]$offset)
        $type = [BitConverter]::ToUInt32($bytes, [int]$offset + 4)
        $flags = [BitConverter]::ToUInt64($bytes, [int]$offset + 8)
        $size = [BitConverter]::ToUInt64($bytes, [int]$offset + 32)
        if ($nameOffset -ge $stringSize) {
            throw "ELF64 section name is outside the string table."
        }
        $nameStart = [int]($stringOffset + $nameOffset)
        $nameEnd = $nameStart
        $nameLimit = [int]($stringOffset + $stringSize)
        while ($nameEnd -lt $nameLimit -and $bytes[$nameEnd] -ne 0) {
            ++$nameEnd
        }
        if ($nameEnd -eq $nameLimit) {
            throw "ELF64 section name is not terminated."
        }
        $name = [Text.Encoding]::ASCII.GetString($bytes, $nameStart,
                                                 $nameEnd - $nameStart)
        if (($flags -band 7) -eq 7) {
            throw "ELF64 section '$name' is writable and executable."
        }
        if ($RequireLinked -and ($type -eq 4 -or $type -eq 9) -and $size -ne 0) {
            throw "Final ELF64 artifact retains relocation section '$name'."
        }
        if ($RequireLinked -and $type -eq 6 -and $size -ne 0) {
            throw "Final ELF64 artifact contains dynamic-link state."
        }
        if ($name -match '^\.(?:eh_frame|gcc_except_table|init_array|fini_array)') {
            throw "Forbidden C runtime section remains: $name"
        }
        if ($RequireLinked -and $type -eq 2 -and $size -ne 0) {
            $entrySize = [BitConverter]::ToUInt64($bytes, [int]$offset + 56)
            $dataOffset = [BitConverter]::ToUInt64($bytes, [int]$offset + 24)
            if ($entrySize -lt 24 -or $dataOffset + $size -gt $bytes.Length) {
                throw "ELF64 symbol table is malformed."
            }
            for ($symbol = 1; $symbol -lt ($size / $entrySize); ++$symbol) {
                $symbolOffset = $dataOffset + ($symbol * $entrySize)
                if ([BitConverter]::ToUInt16($bytes, [int]$symbolOffset + 6) -eq 0) {
                    throw "Final ELF64 artifact retains an undefined symbol."
                }
            }
        }
    }
    return ,$bytes
}

$Make = Resolve-NativeTool 'make' @('C:\ProgramData\chocolatey\bin\make.exe')
$Nasm = Resolve-NativeTool 'nasm' @(
    'C:\tmp\nasm-3.02-portable\nasm-3.02\nasm.exe'
)
$Zig = Resolve-NativeTool 'zig' @(
    'C:\tmp\zig-0.16.0-portable\zig-x86_64-windows-0.16.0\zig.exe'
)
$Objcopy = Resolve-NativeTool 'objcopy' @('C:\msys64\mingw64\bin\objcopy.exe')
$MsysShell = Resolve-NativeTool 'sh' @('C:\msys64\usr\bin\sh.exe')
$Artifact = Join-Path $RepoRoot "$OutputDirectory\x86_64\reist-x86_64-bootstrap.elf"
$UserProbe = Join-Path $RepoRoot "$OutputDirectory\x86_64\reist-x86_64-user-probe.elf"
$UserShell = Join-Path $RepoRoot "$OutputDirectory\x86_64\reist-x86_64-user-shell.elf"
$UserShellObject = Join-Path $RepoRoot "$OutputDirectory\x86_64\user_shell.o"
$UserChild = Join-Path $RepoRoot "$OutputDirectory\x86_64\reist-x86_64-user-child.elf"
$UserChildObject = Join-Path $RepoRoot "$OutputDirectory\x86_64\user_child.o"
$CObject = Join-Path $RepoRoot "$OutputDirectory\x86_64\bootstrap_core.o"
$CElf = Join-Path $RepoRoot "$OutputDirectory\x86_64\reist-x86_64-c-core.elf"
$CText = Join-Path $RepoRoot "$OutputDirectory\x86_64\bootstrap_core_text.bin"
$CRodata = Join-Path $RepoRoot "$OutputDirectory\x86_64\bootstrap_core_rodata.bin"
$CData = Join-Path $RepoRoot "$OutputDirectory\x86_64\bootstrap_core_data.bin"

$buildRoot = [IO.Path]::GetFullPath((Join-Path $RepoRoot 'build'))
$outputRoot = [IO.Path]::GetFullPath((Join-Path $RepoRoot $OutputDirectory))
if ($outputRoot -ne $buildRoot -and
    -not $outputRoot.StartsWith($buildRoot + [IO.Path]::DirectorySeparatorChar,
                               [StringComparison]::OrdinalIgnoreCase)) {
    throw 'x86_64 output must remain within the repository build directory.'
}
$savedZigGlobalCache = $env:ZIG_GLOBAL_CACHE_DIR
$savedZigLocalCache = $env:ZIG_LOCAL_CACHE_DIR
$savedBuildPath = $env:Path
Push-Location $RepoRoot
try {
    # Keep compiler/linker caches inside the writable workspace, including lld.
    $env:ZIG_GLOBAL_CACHE_DIR = Join-Path $buildRoot 'zig-global-cache'
    $env:ZIG_LOCAL_CACHE_DIR = Join-Path $outputRoot 'x86_64\zig-cache'
    New-Item -ItemType Directory -Force -Path $env:ZIG_GLOBAL_CACHE_DIR,
        $env:ZIG_LOCAL_CACHE_DIR | Out-Null
    # GNU Make may execute simple recipes directly; make the native MSYS
    # mkdir available just like the production Windows build does.
    $env:Path = "$(Split-Path -Parent $MsysShell);$env:Path"
    & $Make 'x86_64-bootstrap' `
        "OUTPUT_DIR=$($OutputDirectory.Replace('\', '/'))" `
        "SHELL=$(To-MakePath $MsysShell)" `
        "AS=$(To-MakePath $Nasm)" `
        "OBJCOPY=$(To-MakePath $Objcopy)" `
        "X86_64_CC=$(To-MakePath $Zig) cc" `
        "X86_64_FAULT_VECTOR=$FaultVector" `
        "X86_64_FAULT_PHASE=$FaultPhase" `
        "X86_64_BUSY_CHILD=$([int]$BusyChild.IsPresent)" `
        "X86_64_BUSY_INVALID_STACK=$([int]$InvalidBusyStack.IsPresent)" `
        "X86_64_CONTEXT_CASE=$ContextCase" `
        "X86_64_EXIT_STATUS=$ExitStatus" `
        "X86_64_IPC_CASE=$IpcCase" `
        "X86_64_ARGV_CASE=$ArgvCase" `
        "X86_64_REQUEST_CASE=$RequestCase" `
        "X86_64_OOM_CASE=$OomCase" `
        "X86_64_PROFILE_CASE=$ProfileCase" `
        "X86_64_MAPPING_CASE=$MappingCase" `
        "X86_64_INSTRUCTION_CASE=$InstructionCase" `
        "X86_64_SHELL_EXIT_STATUS=$ShellExitStatus" `
        "X86_64_OWNER_TERMINAL=$([int]$OwnerTerminal.IsPresent)" `
        "X86_64_NATIVE_PROCESSES=$([int]$NativeProcesses.IsPresent)" `
        "X86_64_PROCESS_CASE=$ProcessCase" `
        "LD=$(To-MakePath $Zig) ld.lld"
    if ($LASTEXITCODE -ne 0) {
        throw "x86_64 bootstrap build failed with exit code $LASTEXITCODE."
    }
    if (-not (Test-Path -LiteralPath $Artifact -PathType Leaf)) {
        throw "x86_64 bootstrap artifact was not produced: $Artifact"
    }
    if (-not (Test-Path -LiteralPath $UserProbe -PathType Leaf)) {
        throw "x86_64 ELF64 user probe was not produced: $UserProbe"
    }
    if (-not (Test-Path -LiteralPath $UserShell -PathType Leaf) -or
        -not (Test-Path -LiteralPath $UserShellObject -PathType Leaf)) {
        throw "x86_64 ELF64 Ring-3 shell artifacts were not produced."
    }
    if (-not (Test-Path -LiteralPath $UserChild -PathType Leaf) -or
        -not (Test-Path -LiteralPath $UserChildObject -PathType Leaf)) {
        throw "x86_64 ELF64 Ring-3 child artifacts were not produced."
    }
    if (-not (Test-Path -LiteralPath $CObject -PathType Leaf)) {
        throw "x86_64 freestanding C object was not produced: $CObject"
    }
    if (-not (Test-Path -LiteralPath $CElf -PathType Leaf)) {
        throw "x86_64 linked C payload was not produced: $CElf"
    }
    foreach ($payload in @($CText, $CRodata, $CData)) {
        if (-not (Test-Path -LiteralPath $payload -PathType Leaf)) {
            throw "x86_64 C payload section was not produced: $payload"
        }
    }
    $probeItem = Get-Item -LiteralPath $UserProbe
    if ($probeItem.Length -lt 64 -or $probeItem.Length -gt 64KB) {
        throw "x86_64 ELF64 user probe size is outside the fixed 64..65536-byte range."
    }
    $probeMagic = ([System.IO.File]::ReadAllBytes($UserProbe))[0..4]
    if ($probeMagic[0] -ne 0x7F -or $probeMagic[1] -ne 0x45 -or
        $probeMagic[2] -ne 0x4C -or $probeMagic[3] -ne 0x46 -or
        $probeMagic[4] -ne 0x02) {
        throw "x86_64 user probe is not an ELFCLASS64 artifact."
    }
    $shellItem = Get-Item -LiteralPath $UserShell
    if ($shellItem.Length -lt 64 -or $shellItem.Length -gt 4096) {
        throw "x86_64 ELF64 Ring-3 shell exceeds its fixed compact page."
    }
    $item = Get-Item -LiteralPath $Artifact
    if ($item.Length -le 0 -or $item.Length -gt 2MB) {
        throw "x86_64 bootstrap artifact size is outside the fixed 1..2097152-byte range."
    }
    $artifactBytes = [System.IO.File]::ReadAllBytes($Artifact)
    if ($artifactBytes.Length -lt 52 -or $artifactBytes[4] -ne 1 -or
        [BitConverter]::ToUInt16($artifactBytes, 16) -ne 2 -or
        [BitConverter]::ToUInt16($artifactBytes, 18) -ne 3) {
        throw "Multiboot bootstrap is not an ELF32 EM_386 ET_EXEC container."
    }
    $cElfBytes = Read-Elf64Layout -Path $CElf -RequireExecutable -RequireLinked
    $objectBytes = Read-Elf64Layout -Path $CObject
    $shellBytes = Read-Elf64Layout -Path $UserShell -RequireExecutable -RequireLinked
    $shellObjectBytes = Read-Elf64Layout -Path $UserShellObject
    $childBytes = Read-Elf64Layout -Path $UserChild -RequireExecutable -RequireLinked
    $childObjectBytes = Read-Elf64Layout -Path $UserChildObject
    $objectText = [Text.Encoding]::ASCII.GetString($objectBytes)
    $shellObjectText = [Text.Encoding]::ASCII.GetString($shellObjectBytes)
    foreach ($forbidden in @('__stack_chk', 'memcpy', 'memset', 'memmove',
                              '_Unwind', '__cxa_', 'malloc', 'free')) {
        if ($objectText.Contains($forbidden)) {
            throw "x86_64 C object references forbidden runtime symbol '$forbidden'."
        }
        if ($shellObjectText.Contains($forbidden)) {
            throw "x86_64 shell object references forbidden runtime symbol '$forbidden'."
        }
        if ([Text.Encoding]::ASCII.GetString($childObjectBytes).Contains($forbidden)) {
            throw "x86_64 child object references forbidden runtime symbol '$forbidden'."
        }
    }
    # Only the explicit two-PT_LOAD mapping fixture adds a compact R/NX page.
    $childLimit = if ($MappingCase -eq 4 -or $InstructionCase -ne 0) { 12288 } elseif ($MappingCase -ne 0) { 8192 } else { 4096 }
    if ($childBytes.Length -lt 64 -or $childBytes.Length -gt $childLimit) {
        throw "x86_64 ELF64 Ring-3 child exceeds its fixed compact page."
    }
    $cTextLength = (Get-Item -LiteralPath $CText).Length
    $cRodataLength = (Get-Item -LiteralPath $CRodata).Length
    $cDataLength = (Get-Item -LiteralPath $CData).Length
    if ($cElfBytes.Length -gt 64KB -or $cTextLength -le 0 -or
        $cTextLength -gt 4096 -or $cRodataLength -le 0 -or
        $cRodataLength -gt 4096 -or $cDataLength -ne 32) {
        throw "x86_64 C payload sections exceed their fixed page or ABI bounds."
    }
    Write-Host "X86_64_BOOTSTRAP_BUILD_OK path=$Artifact bytes=$($item.Length)"
    Write-Host "X86_64_USER_PROBE_BUILD_OK path=$UserProbe bytes=$($probeItem.Length)"
    Write-Host "X86_64_USER_SHELL_BUILD_OK path=$UserShell bytes=$($shellBytes.Length)"
    Write-Host "X86_64_USER_CHILD_BUILD_OK path=$UserChild bytes=$($childBytes.Length)"
    Write-Host "X86_64_C_CORE_BUILD_OK path=$CObject bytes=$($objectBytes.Length)"
    Write-Host "X86_64_C_PAYLOAD_BUILD_OK path=$CElf bytes=$($cElfBytes.Length)"
} finally {
    $env:ZIG_GLOBAL_CACHE_DIR = $savedZigGlobalCache
    $env:ZIG_LOCAL_CACHE_DIR = $savedZigLocalCache
    $env:Path = $savedBuildPath
    Pop-Location
}
