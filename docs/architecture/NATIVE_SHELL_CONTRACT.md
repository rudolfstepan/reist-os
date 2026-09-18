# Native normal-shell source port — R8.3at

Frozen on clean AS f2e93446,18 September2026. Standing interactive completion
authority, one package, no agents/push. AS final receipt
`build/codex-agent/r83as-console/queue-drain/verification-status-console-final.json`
SHA cc22acfe52aae31a38325cd76446144b832f64f1d0cbc7d0b45cdecdc187b2c4.

## Boundary and references

Build the actual unchanged `userspace/bin/shell.c` and `shell_vfs.c`, not the
historical native scripted shell. AMD64 System V ELF64/LP64 calling convention,
existing REIST syscall numbers and negative errno-compatible errors apply.
No POSIX terminal, filesystem or whole-program compatibility is claimed.
The existing normal command dispatcher, bounded history, line editor and path
parser are authoritative. No new shell commands or kernel rescue entries.

`NativeShell` explicitly selects existing NativeConsole. Only prepared root0
changes; peers remain byte-identical. Existing eight-page image envelope and
separate stack, W^X, CPU32, generation and retirement rules remain unchanged.
Use an ELF linker layout with at most four text pages and four data/BSS pages.
The common producer publishes the identical root ELF as `root/bin/shell.prg`
inside its retained attempt, for both Windows and Make. This staging path is
not evidence of a mounted native root filesystem or normal system boot.

The platform adapter implements only console, monotonic time, bounded sleep,
decimal output and checking the already granted root terminal authority.
CHECK/ATTACH validates arguments and probes a zero-byte READ; it never creates
authority. TRANSFER is unsupported. Files, cwd, drives, spawn/wait/kill/identity,
USB and network return -38/-95 without touching output or producing success.
The normal shell visibly reports unavailable operations. No fake namespace,
resident program, terminal handoff or fallback to Ring0 services.

Whole adapter session <=1800ms from first clock, <=4096 admitted operations,
<=1024 received bytes, <=16384 output bytes, <=4096-byte string scan. Regressed
or invalid clock, failed sleep, malformed IO result and exhausted budgets exit
only this ordinary Ring3 task. Empty input maps EAGAIN to existing shell's zero
sentinel; the shell uses its existing10ms blocking sleep. SDK output retains
partial writes and the smaller remaining absolute session deadline. No heap.

## Frozen qualification

Eight commands and allowed files are authoritative in automation/reist-s03b.toml.
One image; four guests: normal help/path/history/unavailable command at4/8GiB,
real editing/history/unsupported cwd at4GiB, empty-after-command timeout4GiB.
Each includes a fresh healthy replacement generation and independent peers.
20s per guest including3s cleanup,80s total,120s matrix. First failure stops.
No guest writes or synthetic byte acknowledgements. Reuse unchanged AS capture
and feeder in a private namespace with only the fixed input-plan validator and
actual normal-shell banner substitution; preserve every capacity/deadline.
Each chunk <=8 bytes, <=18 chunks/130 bytes total, actual RX acknowledgement.
Full old mapping/ownership/FP/IPC/heap/frame cleanup oracle remains except root
exit code and identical second-run image assignment. Raw UART bytes must prove
real command dispatch and fresh generation. Independent full binary memory
validation and kernel/high-RAM equivalence remain mandatory. AS crash/CPU and
denied peer/legacy proofs are reused only with exact unchanged kernel sources,
preprocessed core and artifact/raw-evidence hashes, not serial markers alone.

Host tests execute actual shell and platform C at O0/O2 with only the syscall
boundary modeled; cover editing, dispatch, failures, clock/IO/attempt bounds,
unsupported untouched outputs and terminal non-delegation. Old shell tests and
console tests run once. Both producer routes, negative selectors before effects,
unchanged default command/source behavior and protected references are checked.
Ignored finite verifier receipts bind commands, elapsed, sources, tools, logs,
artifacts and raw files; preserve every failed attempt. Direct scope/ABI/bounds/
cleanup review before queue advance and clean local commit; then continue.

## Still open

Combined live file service, native cwd/namespace adapter, actual child launch
and generation-scoped terminal handoff, persistent interactive session policy,
standard image boot, desktop/browser and physical platform qualification.
R3.6b remains explicitly deferred. This package cannot finish the full64-bit OS.
