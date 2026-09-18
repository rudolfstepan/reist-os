# Native normal-shell source port — R8.3at

Frozen on clean AS f2e93446,18 September2026. Standing interactive completion
authority, one package, no agents/push. AS final receipt
`build/codex-agent/r83as-console/queue-drain/verification-status-console-final.json`
SHA cc22acfe52aae31a38325cd76446144b832f64f1d0cbc7d0b45cdecdc187b2c4.

## Qualified result,18 September2026

All eight gates pass: eight package hosts,33 existing shell tests,15 console
tests and four real guests22.8463759s. Actual normal shell dispatch at4/8GiB,
editing/history, unavailable-service errors and bounded empty-input exit work;
fresh replacement and independent peers, all mapping/FP/IPC/heap/frame cleanup
and independent kernel/high-memory transport evidence pass. Additional final
review compares every transmitted command/output byte, including history
numbers, backspace erasure, repeated-command suppression and prompts.

Image aa949fe650813739c9503d803426cd7cf370ea8132507c79ffd772adab21bb6e.
Successful gate commands50.5416325s. Complete history: two OS images,six guest
attempts29.9656697s including two failures. All earlier failed host/preflight
windows and diagnostics remain retained; no guest/debugger left. Review seal
f5a01a4c0eb715655cad3c8702f4f8e4a19941924c4c8fe5810eca58b8a73b81 binds5199
evidence files under r83at-shell; buffered/verification-status-shell-final.json
binds the clean local implementation commit. No kernel/ABI/authority change.
This closes the finite console-only normal-shell source port, not file/process
integration or a normal native OS boot/session. Historical stops below are
superseded by this accepted result, not erased or converted to successes.

## Boundary and references

User continuation on18 September approves the reported shared-shell extension.
Drive-fix window supersedes only the unchanged-shell restriction: both drive
enumerators make at most32 calls and stop immediately on errors/invalid status.
Longest-prefix selection is published only on successful end, never on partial
error/capacity exhaustion.32 is a shell work budget, not a changed public drive
limit. All other normal shell source remains exact. O0/O2 i386/AMD64 host tests
execute the actual functions, preserving healthy drive and mount semantics.
Original blocked seal550c61fc8419a303 and all two failed host windows plus
diagnostics stay spent; no prior OS build/guest. One fresh eight-gate window,
same unspent one-image/four-guest reserve, first failure stops. The raw startup
oracle now also requires the existing USB diagnostics-unavailable line; no
guest behavior changes. Host child launches use existing no-dialog policy.

Build the actual `userspace/bin/shell.c` (only approved drive fixes) and unchanged `shell_vfs.c`, not the
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

Line-feed reaches real HELP/PATH/HISTORY/unavailable command; root is then
contained at CPU32 (status256/state3) after24/25 received bytes, before exit's
newline. Peers remain62/63/64. Failed guest4.5209964s retained; cumulative two
failed guests7.1192938s and one image. Buffered window batches only Ring3 output
in fixed64-byte storage; flush full/newline and on empty read before caller
sleeps. Preserve exact ordered bytes, partial progress, operation/byte quotas,
absolute1000ms deadline and all kernel quotas. No normal-shell changes. Fresh
host behavior checks first; one additional image native-buffered, four guests
80s, cumulative at most two images/six guests87.1192938s. Eight original gates,
first failure stops; all previous sources/raw/logs remain immutable.

Capture window: first actual guest2.5982974s prints normal shell startup.
Host sends68656c700d706174; raw RX is68656c7070, missing CR, so exact feeder
correctly rejects. No specific QEMU/Windows transformation cause is asserted.
Line-feed window uses LF, already accepted by unchanged read_line, instead of
CR in only the frozen host scripts; actual host shell covers both. Preserve
all failed bytes/receipts. Same image, zero builds, four fresh guests80s and
cumulative five attempts82.5982974s max;20s per guest unchanged. Same eight
obligations, same exact raw input/output/cleanup assertions; first error stops.

Encoding window passes groups1..5 and builds the first image29b4092a38668285.
Runtime preflight stops on relative evidence path before any guest. Capture
window resolves that path and regresses the real entrypoint with only launch
modeled. Eight obligations remain; reuse original successful build with exact
596 source inputs,97 artifact hashes, tools/command/log binding. No new build,
four fresh guests in capture/guests; zero previously spent guests. Limits and
raw assertions unchanged. Preserve all failed windows and source snapshots.

Assertions window passes six package hosts (actual O0/O2 shell and i386/AMD64
drive functions),33 existing shell tests and15 console tests. Gate4 stops on
Windows default-codepage versus UTF8 comparison of the unchanged German source
comment. Encoding window corrects only the source comparison, adds its actual
positive/mutation regression and preserves all previous evidence. Same eight
gates, zero spent OS builds/guests, no production/oracle change.

Drive-fix host window: real normal-shell O0 modes0..16 and i386 drive O0 pass.
Optimized host compilation stops because Zig defines NDEBUG; assertions were
removed and Werror detects unused test variables. No OS build/guest. Retain
all receipts/sources. One assertions-only window explicitly undefines NDEBUG
in host builds and rejects it at compile time in both harnesses. No production
change or gate relaxation; same eight gates and original runtime reserve.

First host gate stopped before compilation: Zig's injected Windows runtime
option trips unused-command-line-argument under Werror. Four other tests pass;
zero builds/guests. Stop e9d5fc683b3c473e and full candidate snapshots retained.
One host-fix window adds the repository's existing narrow compiler-driver
warning exception, without disabling C warnings; same eight gates and unspent
one-image/four-guest reserve. Runtime code unchanged. Concrete session deadline
is1000ms, within the1800ms ceiling. Root retirement RIP must lie in its actual
four-page RX envelope; peers retain the old single-page check.

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

## Historical shared-shell stop

Qualification stopped before any OS build/guest. `userspace/bin/shell.c`
find_drive (line279) and current_drive (line301) both retry negative
x86os_drive_info returns without a bound. Native -38 is correct, but normal
PATH hits this pre-existing infinite enumeration. The real O0 host program
times out60s; a separately retained5s boundary-traced diagnostic demonstrates
main, admitted terminal probe and real SDK partial-write/sleep execution.
The PDB-only executable could not supply a GDB symbolic backtrace; that25s
diagnostic is not acceptance evidence. No exact instruction sample is claimed.

Required scope change: include the shared normal shell and bound/error-handle
both enumeration loops, with legacy/native behavior regressions. Do not mask
unsupported namespace authority as successful enumeration end. This violates
the present unchanged-shell invariant and allowed_files, so the transaction
stops under the pre-existing-source-failure rule. No implementation commit,
queue advance or completion claim. All failed sources/logs remain preserved.

## Still open

Combined live file service, native cwd/namespace adapter, actual child launch
and generation-scoped terminal handoff, persistent interactive session policy,
standard image boot, desktop/browser and physical platform qualification.
R3.6b remains explicitly deferred. This package cannot finish the full64-bit OS.
