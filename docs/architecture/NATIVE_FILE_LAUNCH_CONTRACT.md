# Native immutable-file execution boundary

R8.3am, frozen on clean accepted `1835ee97` after all21 R8.3al gates.
One cohesive Ring3 transaction: filesystem stat/read, immutable ELF64 capture,
existing image preparation, explicit attenuated CREATE, failure and complete
retirement. No new kernel mechanism, public syscall, file-write right or normal
OS/shell acceptance. Main interactive agent only; no nested agents or push.

## Inventory and authority

R8.3al already supplies actual FAT12/FAT32/EXT2 parsers,64-byte native envelope,
512-byte stat/read/readdir payload,8 requests/session,256-byte reads,16 cached
sectors, separate driver/FS generations and dependency fencing/replacement.
`image.c` already admits ELF64 in Ring3 and prepares immutable RNPGv2;
CREATE-v5 copies that record and independently admits mappings in Ring0.
Existing file consumers still read embedded test content; imported executables
are embedded in their supervisor, not obtained through filesystem RPC.

The native process pool still has four slots, two initial roots and two dynamic
slots, CPU1..32 and eight CREATE attempts/root. Do not silently lift those limits
to suggest a normal shell port. This transaction stages file bytes while the
driver and parser occupy slots2/3, fences/reaps both, then imports the prepared
program into free slot2. A second fresh dependency group and program generation
exercise replacement. Concurrent application/filesystem availability, long-lived
service budgets and ordinary shell integration remain later kernel boundaries.

Reading a file never grants execution, device, IPC or task-management authority.
The supervisor explicitly imports it with a reduced existing profile, no PIO or
TASK_CONTROL; only a fresh private acknowledgement endpoint is delegated. The
filesystem and block driver receive no additional authority.

## Standard-first adapter

Reuse System V ELF64 little-endian ET_EXEC/EM_X86_64, PT_LOAD/R/W/X,4KiB alignment,
argv/env/auxv and the existing RNPGv2 adapter without changing parser semantics.
The small real C qualification program uses the standard GNU ld
[FILEHDR/PHDRS layout](https://sourceware.org/binutils/docs/ld/PHDRS.html) with
headers inside an RX segment; this is not a custom executable format.
FAT/EXT2 formats and native RPC semantics remain those of
[NATIVE_FILESYSTEM_CONTRACT](NATIVE_FILESYSTEM_CONTRACT.md).

Add one reusable explicitly bounded SDK file-image helper, not an exec/POSIX
compatibility alias. It requires a fresh exact FS client generation/sequence,
one immutable-media session, a canonical absolute path and a single monotonic
deadline no greater than3000ms. Reject aliases and arithmetic overflow before
calling transport. Fixed private1536-byte file staging, no heap: one stat, at
most six256-byte reads, then one EOF read fit the existing eight-call session.
Larger/empty/nonregular files fail closed before data reads; a short read,
extra EOF byte, changed identity, transport/protocol fault or deadline failure
never publishes a prepared image. No hidden session restart or cache eviction.

The whole prepared output remains unchanged on failure. Only the existing
ELF64 adapter can publish it after every captured file byte and EOF is checked.
Scrub private file staging on every admitted exit. Malformed ELF does not reach
CREATE or consume a kernel attempt. Caller chooses argv and the attenuated
profile; these do not come from media. No signature/secure-boot claim is added
to executable files on these generated immutable test media.

## Shared implementation and complete lifecycle

Reuse the existing supervisor/driver/parser startup and fencing helpers, keeping
the old NativeFilesystem selection byte-bound to the accepted baseline. Add
explicit NativeFileLaunch/Make selectors and a separately linked real C file
program; neither defaults nor the rescue-shell command set change. This is no
new shell command: normal `/bin/shell.prg` dispatch is not claimed.

Only a finite generated `/boot.prg` file is added in the explicit file-launch
media profile. Its bytes come from the independently linked admitted ELF,
bounded by1536, plus finite malformed/oversize variants for rejection. No user
or physical disk and no arbitrary QEMU options. Existing media defaults stay
exact. Same exclusive read-only base/disposable qcow2 metadata boundary,35.84MB
base/4MiB overlay, exact backing/map/logical bytes and unchanged-before/finally
checks, including all failures. Kernel PIO remains read-only.

Detect failure -> deny publication -> physical fence/revoke -> reap pair ->
fresh pair/self-tests -> retry only as the explicitly budgeted replacement.
Application UD2, noncooperative spin and sleep/cancel use ordinary kernel
containment; independent peer survives. Owner-loss retires all descendants.
Import OOM rolls back completely before one retry; stale generations never
regain rights. Verify actual private frames, image/argv bytes, W^X/stack guards,
all CPU bounds, exact statuses, IPC/heap/FP/context cleanup and frame balance.

## Frozen verification

Thirteen targeted groups: new file-image O0/O2 behavior, new runtime/oracle and
build selection, existing FS/sector-range/media/FS-runtime, ELF import, startup,
boot producer, PIO, native IPC, syscall ABI and documentation. Three builds:
default, old NativeFilesystem, new NativeFileLaunch. Four runtime groups:
new matrix, unchanged full FS18 matrix, normal bootstrap and original i386
reference guard. Twenty groups total, plus direct scope/ABI/cleanup review and
old normal/FS object/catalog/ELF hashes. Preserve all old accepted/failed evidence.

New matrix: eighteen guests, each20s/total360s maximum, one CPU, no visible VM.
Normal five media at4GiB plus EXT2-1KiB at8GiB; application UD2/spin/cancel;
malformed ELF; FS UD2; driver UD2; owner loss; file CREATE OOM first/mid/final;
oversized file; malformed FS reply. Two real PROCESS_RUN invocations each,
fresh dependency and application replacement where applicable; malformed ELF
and oversized files degrade without any application CREATE. Bind all actual
physical bytes and independently prepared imported bytes to the linked file.
Host negatives include every short read/EOF/deadline/identity/admission failure
and retained output, not merely source patterns. Runtime oracle mutations must
reject missing/reordered/stale/fabricated execution and cleanup evidence.

Frozen commands/allowlist live in `automation/reist-s03b.toml`. Stop on outside
scope, unrelated changes, required quota/authority/persistence expansion,
pre-existing failure or the same concrete failed gate after two focused
corrections. No unchanged guest retry, diagnostic-only acceptance or weakened
oracle. All20 groups must pass before queue transition/local implementation
commit. R3.6b stays explicitly deferred; continue the next native transaction
only after a clean accepted boundary.

## 2026-09-14: authorized timer/idle diagnostic supplement

The user renewed execution after the explicit bounded timer/idle register
diagnosis question. Resume only the attributed candidate whose22 source hashes
and469 evidence hashes match the blocked manifest. This is not a fresh package
or a clean accepted implementation boundary. Keep the original20 gates frozen.

The queue's explicit `diagnostic_files` supplement permits only the host-side
`scripts/diagnose_x86_64_file_timer.py` and its bounded host regression
`test/test_x86_64_file_timer_diagnostic.py`. No kernel, guest, ABI, quota,
timeout, acceptance oracle or original observer changes. Freeze this contract
before instrumentation. The supplement runs one host group, then exactly one
case0/layout0/4GiB guest using the already built failed attempt
`19bf6f9b71af490786906d4dc0c079be` image and its exact program/catalog bytes.
Reuse the unchanged observer and immutable generated FAT12/COW fixture.

Add rejection-only debugger hooks to capture registers, the176-byte IRQ frame,
clock/queue metadata and four fixed task records, at most eight bounded records.
No register/data writes, forced clock advance, instruction skipping, IRQ mask
change or recovery injection. Existing observer behavior remains unchanged.
Use the existing20-second guest bound and hidden single-CPU capture cleanup.
Keep every prior image/log/manifest unchanged; place new evidence under
`build/codex-agent/r83am-file-launch/timer-diagnostic` with a unique attempt.

The diagnostic result is never acceptance, even if the guest happens to pass.
Stop after the one run and report concrete captured findings or non-reproduction.
Kernel repair and additional guest attempts require a new explicitly bounded
scope; neither is inferred from diagnostic authority. R8.3am stays active and
unaccepted, R3.6b deferred, and no implementation commit or push is permitted.

### Renewed authority: one cold-fatal diagnostic run

After the first diagnostic guest stopped before the timer fatal on driver CPU32,
the user explicitly renewed execution in response to the single further cold-
fatal/Fencing diagnostic question. First match all24 current source hashes and
15 diagnostic evidence hashes to `verification-status-timer-diagnostic.json`.
Preserve the previous diagnostic source texts as ignored, hash-bound snapshots.
Only the same two `diagnostic_files` may change, plus this contract/queue and
already allowed status documentation. Freeze this renewal before implementation.

Use `--cold` to run exactly one additional case0/layout0/4GiB guest from the
unchanged19bf6f9b image. A separate single-use output directory retains the old
attempt and manifest. No added debugger breakpoint or new executable address:
wrap the existing `serial_init64` host callback, verify both CALL instructions
on the exact `exception_fatal`/`native_pio_fail64` routes, and record at most one
16KiB snapshot after physical emergency fencing. Always delegate to the original
callback, including its unconditional native-PIO fatal rejection. Never skip an
instruction or change guest registers/data. On the exact generic fatal route,
the saved176-byte IRQ frame is at RSP+8; pointer/range bounds still apply.

Renew the same host group with actual wrapper/route/frame regressions. All20
acceptance groups, kernel and user program bytes, resources,20s guest deadline,
media checks and existing observer/oracle semantics remain unchanged. This
diagnostic can identify a captured rejection or report non-reproduction, never
accept the package. No further guest or kernel repair is authorized by this
renewal; stop after the one run. All historical causes remain open unless the
new evidence directly supports them; do not infer breakpoint causality.

### Timer/idle deterministic regression and demonstrated-cause repair

The renewed user instruction explicitly authorizes investigating the timer/idle
path with deterministic regression tests and correcting a thereby demonstrated
cause. Match the24-source cold manifest before edits, retain all source/evidence
snapshots, and freeze this supplement before implementation. One AM transaction
remains active; this does not accept the unfinished candidate or start a package.

`timer_repair_files` explicitly supplements the allowed scope with only
`arch/x86_64/cpu/timer_interrupt.asm`, `arch/x86_64/proc/process_run.inc`,
`test/test_x86_64_timer_idle.py`, `test/x86_64_timer_idle_host.c` and
`NATIVE_RUNTIME_CLOCK_CONTRACT.md`. The existing two diagnostic files may supply
the fixed guest observer and its regression. A kernel correction requires a
deterministically failing production-behavior test, not a speculative policy
change. No quota, deadline, public ABI, device authority or persistence expansion.

The new host group executes actual native IRQ/idle/tick assembly at O0/O2 with
explicit host-only adapters for privileged CR3/RDTSC/PIO. Fixed fixtures check
valid idle, heap-retirement work, frame/selector/queue/stack errors, full-width
clock boundaries, fail-before-publication and exact EOI/tail ordering. Existing
runtime-clock and process-run host groups remain required. Four finite generated
FAT12/4GiB guests under `--irq-regression` qualify last-peer idle and injected
expired lease, bad saved SS and tick/EOI mismatch, each20s/total80s. Arm the IRQ
probe only after the first root's complete retirement; never add a hot timer
breakpoint during file/driver work. Keep actual immutable media, old observer
proofs, exact clock reason and admission state, physical fence before fatal
diagnosis, unchanged damaged metadata and terminal halt. No effects are injected
into an acceptance guest. Missing injection or missing evidence is failure.

Preserve original20 acceptance groups and all history. After a demonstrated
in-scope correction, renew the affected frozen gates and complete every remaining
gate before any queue transition or implementation commit. A diagnostic passing
guest or deliberately matching fatal symptom does not explain past missing
register evidence and cannot replace package acceptance. Stop on scope expansion
or the same concrete failure after two focused corrections; no blind retry.

The concrete-failure accounting distinguishes the captured pre-CLI IRQ reentry
(`a0d4be69`) from the subsequent control-guest20s timeout (`d5d51087`). The
first timeout correction uses one complete diagnostic log sink (`ebb4fd35`,
still timeout). The second batches page-table reads only in the new file-launch
observer: at most eight4KiB table snapshots per paused read, validating every
requested entry and retaining all bytes, ranges and authority checks; no cache
survives that read. Its actual host test proves full266336-byte data, five total
transfers and fail-before-data behavior for invalid entries and bounds. One
final changed matrix attempt is permitted under the already frozen two-focused-
corrections rule; the two different failure classes yield at most four matrix
attempts total, never a fifth. Guest deadlines and required proofs do not change.

### Renewed bounded Legacy-Sleep diagnosis and demonstrated repair

The user explicitly approved extending the early mode5/stage0x9F diagnosis to
`cooperative_scheduler.asm` and regression tests. Match all29 source hashes and
298 evidence hashes in `verification-status-timer-idle.json` before edits.
`legacy_sleep_files` adds that scheduler source plus the actual O0/O2 host
`test/test_x86_64_legacy_sleep.py` and `test/x86_64_legacy_sleep_host.c`.
The attributed AM transaction now has32 allowed sources; no new package.

Use the existing diagnostic runner for at most two distinct read-only guests
from the unchanged fixed FAT12/4GiB image, each20s/40s total. `--legacy-sleep`
captures the exact final-check state and, if reached, post-fence state (at most
two16KiB records). If those records do not identify the failure, the distinct
`--legacy-sleep-events` additionally records at most40 actual events only while
mode5 is active. No guest writes, changed clocks/quotas, arbitrary launch
options, hot native timer hooks or identical retry. Bind registers, all27 actual
and expected events, timer/final tick/EOI, four task records, queues and counters.
Original callbacks, complete file observer, media proof and cleanup remain.
These diagnostic guests never count as acceptance. Stop on unresolved findings
after this finite pair, not an unbounded repetition until a desired outcome.

A demonstrated cause requires an actual production-assembly red/green test
before correction. Keep every lifecycle event, generation/deadline/EOI check
and exact terminal task/queue/resource cleanup. If a strict event total-order
rejects a demonstrated valid interrupt interleaving, replace only the accidental
timing assumption with a bounded exact lifecycle, FIFO and dependency proof.
No wildcard events, count-only success, ignored mismatch or arbitrary permutation
acceptance; mutate missing, duplicate, premature, stale and reordered events.
No other scheduler redesign, public ABI, persistence or device authority change.

Only after that demonstrated correction, rebuild the source-bound FAT12 image
and run one new `--irq-regression-after-sleep` matrix (four cases, unchanged
20s/80s bounds and all previous IRQ/file/fence/halt oracles). The old four-attempt
directory remains spent and untouched. First new failure stops; no automatic
new attempt budget. Renew the legacy host and queue groups, existing timer/
clock/process/diagnostic groups and all affected original20 gates. Original
unaffected results remain bound, stale builds cannot substitute for new ones.
No implementation commit or queue advance until complete acceptance. Stop on
unknown new failure, outside scope or the same failure after two focused fixes.

### Bounded common-transport cost diagnosis

Renewed user approval explicitly includes the common QEMU/GDB transport and
bounded cost measurement. First match30 existing sources and32 evidence files
in `verification-status-legacy-sleep.json`; the two unused Legacy-Sleep host
paths stay pending, without a speculative kernel correction. The queue's
`file_transport_files` adds the common capture runner, a dedicated file-transport
diagnostic and host test, and the existing block-transport regression. The
allowed union is36 paths, one unfinished AM transaction, no new package.

Reuse the optional documented child-process CPU counters. Record capture/cleanup
phases, actual stop reason, bounded serial progress, QEMU/GDB CPU and debugger
callback/read/register time. Default capture and every existing assertion,
20s active capture, serial/observer limits and media/finally cleanup remain.
No systemwide tuning, timer resolution, power policy, clock, single-step mask,
guest quota, guest writes or arbitrary QEMU/GDB options. Do not confuse time
spent in a debugger callback with guest execution time or assume causality from
one timing sample.

Four fixed controls use the exact previously built FAT12/4GiB image: detached,
finish-only, full observer, full observer with cost wrappers. Only the full
variants carry the complete existing file proof; none is package acceptance.
Costs are bounded by4096 callbacks,64 names,1e6 reads/registers and128MiB observed
bytes. At most128 private8KiB JSON cost checkpoints survive a timeout; these
are separate from the unchanged64KiB observer-log bound. Reuse existing
callbacks, never extra hot timer probes for measurement. Full completion still
requires both real process runs and all16 lifetimes, bytes, fencing and cleanup.

At most two evidence-directed changed followups may be frozen separately before
execution. Total at most six20s active captures/120s, plus separately recorded
existing bounded cleanup; no identical retry or extension to wait for success.
Old four-attempt IRQ and two-guest legacy directories remain spent and untouched.
Stop on unknown new fault, outside scope, exhausted diagnosis or the same
concrete failure after two targeted corrections. Preserve all historical evidence.

A demonstrated transport/observer correction within these paths requires an
actual host regression and retains every check. It may then renew affected
original gates plus one `--irq-regression-after-transport` four-case matrix
(20s/80s; original idle, expired-lease, invalid-SS, EOI, fence and halt proofs).
That conditional renewal is independent of the unproven legacy repair, not a
retroactive explanation of its historical fatal. No speculative kernel change.
Complete all original20 and required supplementary groups before a local
implementation commit/queue advance; no agents or push.

First directed followup, `full-span-profile`: initial288fc570 completes detached
and finish controls in9.825/9.824s active capture. Full observation19.615s passes
its byte/lifecycle oracle; the profiled counterpart reaches20s before last peer.
The last checkpoint attributes6.407 of6.634 callback seconds to8109 reads of
23,548,535 bytes; IPC reads account for3.243s. This identifies a concrete
overfetch introduced by full-table snapshots for tiny `user` requests.

Read exactly the needed contiguous entry span per visited table: at most eight
spans of at most4KiB, computed from the remaining validated virtual extent.
Keep every requested entry and payload check, exact transfer lengths, no
cross-call cache, and fail before payload on any invalid entry/span. Tiny reads
require32 table bytes, large reads still use bounded batched entry transfer.
Real host negatives and page/PT-boundary cases precede this one changed profiled
guest; same image,20s bound and all full oracles. One followup slot remains,
only for a separately frozen evidence-directed change, never identical retry.
