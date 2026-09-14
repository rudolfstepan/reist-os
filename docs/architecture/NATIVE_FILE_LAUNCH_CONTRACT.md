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

Second and last directed followup, `full-batch-profile`: f5f1e66 still reaches
20s despite reducing observed bytes to14,599,975. Its8036 reads cost5.632s;
start reads account for1.15s, post-release reads for0.36s. Batch exactly the
RAM required at those same paused boundaries. Fetch the64 native image leaf
entries together after validating their three common parents. Validate every
leaf and owned-frame condition before batching the requested payload pages;
retain every existing content and startup assertion. Coalesce adjacent released
frames for the complete zero proof, retaining the exact returned-frame ledger.
At most69 fixed4KiB regions, no reads across gaps, each transfer at most270336
bytes, exact transfer lengths, no cache across callbacks or guest execution.
Host tests execute the real helpers and transformed observer, including short
transfers and invalid entries/frames. This sixth diagnostic guest retains the
same image, cost accounting,20s bound and all oracles. A repeated timeout stops
this diagnosis; it does not authorize another retry or a looser acceptance gate.

### Separate bounded stop/timer timeline diagnosis

Renewed approval permits exactly two differently instrumented diagnostic guests,
`--timeline stops` then `--timeline peer-clock`, after matching34 sources and159
evidence hashes in `verification-status-file-transport.json`. Reuse only the
transport diagnostic and its host test; all36 allowed paths, production observer,
kernel, userspace and common capture remain unchanged. Same source-bound FAT12/
4GiB image,20s active capture per guest/40s total, existing bounded cleanup.

Wrap the existing callbacks and observe the documented GNU GDB Python
[cont/stop notifications](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Events-In-Python.html).
Do not change breakpoint locations, conditions, enabled states, return values,
guest bytes or existing assertions. A callback interval proves that the guest
is stopped during that interval; a gap also contains guest execution and cannot
be assigned to pure debugger overhead. Notifications need not represent every
internal single step; record their actual coverage, do not invent missing events.

Journal limits:4096 callbacks,8192 notifications,16384 records of at most2048
bytes each, monotonic nanosecond timestamps. Buffer one file, flush after32
records or200ms and at snapshots/exits; a timeout can leave a bounded unflushed
tail, which is explicitly incomplete evidence. No extra hot timer breakpoint.
The second mode adds at most192 fixed-RAM snapshots of at most1280 bytes,
paced200ms except existing first-publication/retirement/finish boundaries.
Record exact clock widths, deadlines/queue bytes, root/peer identities and saved
peer registers; never chase an observed guest pointer or modify admission from
these diagnostic values. Include the snapshot reads in callback time.

Actual host execution covers the recorder, wrappers, fixed reader and parser,
including original exceptions, short reads, malformed sequence/accounting and
capacity bounds. Preserve default transport/source and complete file oracle.
All earlier budgets remain spent. This new pair permits no correction, IRQ
renewal, acceptance retry or implementation commit by itself; stop after two
guests or an unknown new failure and retain every historical result.

### Opt-in bounded binary RAM transport

Renewed approval permits the queue's `binary_memory_files` supplement after
matching34 sources/65 evidence from `verification-status-file-timeline.json`.
The existing desktop/hotplug QMP clients own input/device commands and do not
provide this RAM-only admission contract; keep those clients unchanged. Reuse
the native capture's process/media cleanup and the original complete observer.

Use documented QEMU QMP capability negotiation, query-name/query-status and
[pmemsave](https://www.qemu.org/docs/master/interop/qemu-qmp-ref.html#command-pmemsave).
Only an opt-in loopback endpoint and unique guest name are added. Validate
identity, matching integer reply IDs, bounded JSON/event traffic and monotonic
deadlines. No arbitrary monitor commands or guest state mutation. Every binary
read requires a stopped guest, a canonical native kernel/direct alias, the
actual current CR3 translation (4KiB and2MiB leaves), and a RAM-only physical
extent. Native4/8GiB reference profiles only: kernel RAM1..128MiB or high RAM
4GiB..(RAM+1GiB); no MMIO/low device hole. Reject unsupported mappings.

Only reads32768..270336 bytes use binary transport; small GDB reads stay as-is.
At most eight exact page-table spans per read, no cache across calls or stops.
At most2048 freshly named files/128MiB total, no overwrite/deletion, exact
length plus SHA256 journal, stopped-state validation before and after export.
Failures propagate to the original observer rejection; never silently fallback.
Keep original breakpoints, assertions, complete byte comparisons and lifecycle.

Execute actual host regressions first (protocol fragmentation/error/ID/event
bounds, running/wrong guest, mapping/size/range/short-file rejection, source
wrapping and unchanged default capture/media cleanup). Then fixed-image
`--binary equivalence` compares the first large kernel and high-RAM reads with
the original GDB result byte-for-byte. `--binary full` retains the full oracle
without duplicate reads. Both must pass the original20s capture-plus-cleanup
admission and20s active limit, not just eventual completion. Two source-changed,
evidence-directed corrections maximum, at most four guests/80s active total;
no identical retry or reopening an earlier spent budget. Preserve all evidence.

Only successful equivalence and full proof authorize the queue's fresh-output
renewal of affected original20 gates and original four-case IRQ matrix. All
required supplementary groups, final ABI/cleanup/default-path/scope review and
all acceptance gates precede an implementation commit. No speculative legacy
or kernel repair, no full-OS claim from a bootstrap or transport diagnostic.

### Joint transport and peer-clock measurement

Renewed approval resumes36 sources/319 evidence from the binary manifest.
Only the existing transport diagnostic/host test and queue/contract/status docs
change. Production capture, binary reader, full observer, kernel and guest bytes
remain unchanged. Two newly instrumented controls, `--combined binary` then
`--combined gdb`, use the same3c79f8be FAT12/4GiB image and full assertions.
Only the large-read backend differs; no new breakpoint, write or clock option.
Each20s active capture, total40s plus existing bounded cleanup, no repeat.

Reuse Cost, Timeline and the fixed timeline_sample decoder. Measure raw GDB
reads/registers, virtual translation, binary read, QMP connection/status/export/
request/close and snapshot cost with nested inclusive/exclusive intervals.
Fixed16 names,8 stack frames,1e6 calls; at most128 checkpoints of16384 bytes.
Retain4096 callback/16384 timeline record and192 fixed1280-byte snapshot limits;
snapshots are paced200ms plus existing retirement/finish boundaries. Include
measurement overhead in callback time, do not subtract an estimated correction.
Guest clock/RBX state gives nominal pending Sleep time, not measured host wait.
Unobserved gaps contain guest execution and debugger/transport work.

Host tests execute wrappers and validators including exceptions, nesting,
monotonicity, capacities and unchanged original observer functions. No package
acceptance from measurements. All previous budgets and failed evidence remain;
binary2/4 and one correction are used. This pair adds no correction or gate
authority: a demonstrated in-scope repair may use only the earlier remaining
conditional authority. Stop after the pair or an unknown new fault; preserve
sources and evidence, no implementation commit or push.

Last already-authorized binary correction, after the completed measurement pair:
both controls pass all16 lifetimes and original assertions at17.294/18.102s,
but are not acceptance.75 QMP connections cost1.0725s including requests;
source opens separately for adjacent reads in the same stopped callback.
Reuse only the connection within one original Hook.stop/ReleaseEnd.stop call.
Close in finally before returning to GDB/resuming and immediately on any error;
reject nested/failed scopes. Keep per-read behavior outside explicit stop scope.
No byte/mapping cache or skipped validation: each read retains current CR3,
RAM bounds, pre/post stopped-state, exact file size/hash and original oracle.
Host red/green covers success, exception, corruption and no cross-stop reuse.
Only existing binary-reader/host files change. This consumes the last directed
correction and remaining two original binary controls, equivalence then full,
each20s including cleanup. First failure stops; no third correction or new retry.
Only full success enables the earlier conditional original/IRQ gate renewal.

### Bounded debugger-continuation diagnosis (2026-09-14)

Renewed user approval covers measurement, not another transport repair or
acceptance retry. Preserve the36-source/375-evidence combined manifest and raw
source snapshots. Exactly two controls, plain then measured, retain the same
immutable3c79f8be FAT12/4GiB image, current stop-scoped binary full reader and
full original assertions. Measured reuses the unchanged combined observer;
plain has no callback/snapshot/stage instrumentation. Each has20s active capture
plus existing separately accounted bounded cleanup. No new breakpoint or guest
state, clock, stepmask, quota, host timer/power or security setting change.

Both read qqemu.sstepbits/qqemu.sstep once and enable only fixed QEMU log events:
vm_state_notify, gdbstub_op_continue, gdbstub_op_continue_cpu,
gdbstub_op_stepping, gdbstub_hit_break, pic_interrupt, pic_set_irq,
pit_ioport_write. No remote-packet/payload logging. The opt-in common capture
drains stderr in4096-byte chunks, retaining at most8MiB/131072 lines, failing
closed on overflow/read failure; all default capture paths remain unchanged.
Bounded host tests exercise reader capacity, failures/cleanup, option forwarding,
trace decoding and unchanged observer assertions before the two guests.
Bind installed QEMU version/hash/event inventory and preserve failed evidence.
QEMU trace timestamps describe emulator events, not proof of guest acceptance;
mixed callback gaps are not pure debugger cost or host waiting time.

Use only existing capture/diagnostic and their host paths plus queue/contract/
status docs. Older budgets remain spent, last binary correction remains failed.
The pair cannot renew gates, repair the kernel or accept a package. Stop after
the pair or an unknown fault; pending original20 and IRQ obligations remain.

### Bounded equivalence-read cost diagnosis (2026-09-14)

Renewed user approval covers the two additional original GDB byte comparisons
in the still-failed equivalence path. Preserve36 source/306 evidence hashes from
verification-status-file-continuation.json and raw source snapshots. Only the
existing transport diagnostic/host and queue/contract/status docs may change;
binary reader, common capture, production observer and kernel/user code stay.

Exactly two diagnostic controls, --equivalence-cost minimal then profiled,
use the same3c79f8be FAT12/4GiB image and actual binary_memory=equivalence path.
Both keep all original assertions and20s active capture,40s total plus existing
separately bounded cleanup. Report the original20s including cleanup as well.
No QEMU trace, new breakpoint, extra guest read, time/stepmask/quota or host
setting changes. Time only the original two large GDB calls with entry and
return/exception records, exact address/length/returned SHA, maximum4x1024 bytes,
two32768..270336-byte calls, monotonic elapsed<24s. Small reads pass unchanged.
Profiled additionally reuses unmodified Cost callback/read/register accounting
and its4096 callback/64 function/1e6 read/128MiB/128x8192 checkpoint limits;
no timeline or new RAM snapshots. Measurements include their own overhead.

Host tests execute the binding and actual production Reader._read with bounded
valid translation/stopped/export adapters: both byte comparisons, mismatch and
exception propagation, no extra read, caps, observer identity and pair budget.
Bind the two returned hashes to the immutable binary dump ledger; distinguish
directly measured comparison cost from unmeasured historical timing variation.
Stop after this pair or an unknown fault. Timeout is diagnostic, not accepted.
All old budgets and original/IRQ obligations remain unchanged; no speculative
repair, new acceptance/gate renewal, implementation commit, queue advance or push.

### One regular qualification renewal (2026-09-14)

Renewed user approval explicitly restarts regular qualification once. Preserve
the36-source/267-evidence equivalence-cost manifest and raw source snapshots.
Freeze30 gate commands and all current source/helper hashes before execution:
original13 targeted hosts, seven existing supplementary timer/transport hosts,
original3 builds and4 runtime groups, binary equivalence/full and IRQ matrix.
Only substitute the original evidence prefix with qualification-renewal/ beneath
the same ignored package directory. No production/test implementation change,
oracle reduction, timeout/selector/stepmask or default-capture change.

Original file and filesystem18-case matrices retain default GDB transport and
each20s/total360s guest bounds. Supplementary binary controls and four IRQ cases
reuse unchanged actual observers/validators and the fresh FAT12 case0 image from
the successful original file matrix, with linked-file/catalog/config provenance.
Each remains20s including cleanup, binary pair40s and IRQ matrix80s. Preserve
the existing exact normal-idle, expired-lease, saved-SS, EOI, fencing and physical
halt requirements. No failed legacy predicate was repaired; its conditional
unimplemented correction hosts do not become evidence obligations for a change
that did not occur. Existing timer/queue/process mechanisms remain tested.

Main agent executes gates in the visible worktree. Ordinary deterministic
ignored verification helpers are source-hash frozen, not agents; no nested
Codex/runner/reviewer. Host process envelopes180s, builds90s, original matrix
orchestration1800s only cover their already-bounded builds and guests, not a
larger per-guest deadline. Exactly once in sequence, stop the entire pass at the
first failure, timeout or unattributed source change. No correction/retry or
profiling loop in this pass. Old attempt budgets/directories remain untouched.
No retroactive acceptance of a diagnostic control. All30 gates and final direct
scope/ABI/cleanup/default/FS artifact review are required before implementation
commit and queue transition. Otherwise remain active with complete evidence.
No push or claim that this bounded file-launch package completes the native OS.

### Regular file-profile binary capture integration (2026-09-14)

The renewed user approval covers the proposed concrete integration after gate24
of 3c72519b failed with15/16 reaps. Match36 sources/648 evidence hashes from
verification-status-qualification.json and preserve raw snapshots first. This
resumes the attributed unaccepted candidate, not a fresh clean transaction.
Only the existing file-launch runner and its host test may implement changes;
queue, this contract and status docs record the boundary. No kernel repair.

One file-profile adapter inserts the existing single GDB logging sink and
explicitly selects the existing binary_memory=full capture option for all18
regular matrix cases. Original observer generation, callbacks, byte assertions,
validators, binary reader, common capture defaults and diagnostics remain exact.
No public CLI extension or silent fallback. Other profiles retain their default
GDB path. Keep stopped-state/translation checks, complete bytes and dump hashes,
bounded cleanup and every20s/360s matrix admission check. No extra guest reads,
breakpoints, tracing, profiling, timeout/quota/clock/stepmask or guest changes.

Host red/green proves actual matrix call dispatch, exact argument propagation,
single logging sink with identical original observer body, malformed logging
shape rejection before capture and original transport exception propagation.
Then freeze the same30 ordered qualification gates with the binary-integration/
evidence prefix and all source/helper hashes. Ordinary ignored helpers may reuse
the previous deterministic gate and supplementary guest functions; no agents.
Binary equivalence/full and original four IRQ cases remain independent required
gates on the fresh matrix FAT12 image, with unchanged20s including cleanup,
40s/80s totals and full existing validators. Previous attempts stay spent.

Execute each gate once, stopping the pass at first failure, timeout or unrelated
change. No correction/retry loop in the pass. All30 and direct scope/ABI/cleanup/
default/FS artifact review must pass before implementation commit/queue advance.
The shared earlier IF-bit correction changes cooperative_scheduler.o and the
outer normal/FS ELFs; retain explicit review rather than claim full binary
identity. No legacy repair or invented conditional legacy proof, no OS-complete
claim, nested agent or push.

### Failed-init FS retirement correction (2026-09-14)

Renewed user approval covers the demonstrated case6 Ring-3 lifecycle failure:
driver UD2, FS initialization reply -5, unconditional supervisor CANCEL followed
by WAIT expecting natural exit90, actual FS status0/state3 and supervisor221.
Preserve36 sources/2683 evidence hashes from verification-status-binary-integration
and the entire previous evidence chain, raw snapshots and207 i386 pins. Resume
the attributed unaccepted package, not a new clean implementation transaction.

Only file_launch.c and its existing file-launch host test may implement changes.
Compile the actual retirement statements at O0/O2 with explicit bounded host
syscall adapters. Prove both reply-before-exit and already-exited ordering,
normal/FS-fault/driver-fault/malformed-reply cases, exact fence/cancel/wait/reap/
close order, fixed owner generations,1000ms wait/1ms stale probes, and error
short-circuiting before further side effects. Record red before correction.
Keep the existing fence first and bounded WAIT with exact expected status90;
omit only the conflicting failed-init cancellation. No alternative accepted
status, delay loop, deadline extension or kernel mechanism. Other retirement
modes, shared FS implementation, observer/validator/transport, ABI and quotas stay.

After the directed correction, freeze the same30 ordered qualification gates,
all source/helper hashes and retirement-renewal/ output prefix. Original file
matrix uses the integrated binary reader/single log sink; other defaults remain.
Original18x20s/360s matrices, binary pair20s each/40s and four IRQ cases20s/80s
including cleanup and full original assertions remain required. No diagnostic
substitute, new guest profiling or reuse of old successful attempts as acceptance.
Execute each once and stop at first failure/timeout/unrelated change; no repair
or retry in this pass. All30 plus scope/ABI/cleanup/default/FS artifact identity
and changed file-supervisor/catalog provenance before commit/queue transition.
Queue/contract/status docs may record results. No nested agents or push.

### OOM observer transaction boundary correction (2026-09-14)

The renewed user approval resumes the attributed36 sources/3063 evidence from
verification-status-retirement.json, not a clean or accepted new package.
All prior evidence and207 reference pins are preserved and raw sources saved.
The failed case8/first observer samples free frames at CREATE.found, before
CREATE-v5 retires the old selected image; the kernel deliberately resets its
allocation baseline after that retirement. No measured leak or kernel repair
is inferred from the compound assertion. Host-execute actual generated callbacks
with deterministic memory/allocator boundaries to reproduce the mismatch first.

Only the file observer and existing file-launch test may change. For each of the
two injected program CREATEs, arm cold hooks for old-image release entry, actual
frame frees and the existing cached_entry boundary. Bind owner, slot, selector
and last retired driver generation; validate all64 ownership/flag entries,
unique high frames, exact free order, full zeroed pages, cleared metadata and
exact free-counter delta. No new allocation may precede the completed proof.
Only then replace the observer allocation baseline. ENOMEM must still return
exactly that baseline, with unchanged acquired count, no published child and
the original complete final cleanup. Missing/duplicate/wrong frees, dirty bytes,
wrong generation, stale metadata, leaks and unexpected callback order fail.
Emit and independently validate the separate retirement receipt before OOM and
rollback. Hooks remain disabled outside these two CREATE operations; existing
callback/page capacities, original small reads and binary adapter remain intact.

No guest kernel, userspace ABI, shared observer, capture, quota, timeout, clock,
media or legacy change. After host red/green, freeze all36 source hashes and the
same30 ordered gates with oom-boundary-renewal/ and ordinary frozen helpers.
Execute each once; the first failure stops this pass without repair or retry.
Both18x20s/360s matrices, binary pair20s/40s and IRQ4x20s/80s including cleanup
retain all obligations. No diagnostic substitute. All30 plus direct scope,
ABI/cleanup and byte-identical guest-artifact review before implementation
commit or queue transition. Queue/contract/status docs may record results.
Old attempts remain spent; no nested agent, push or full-OS completion claim.

### Case6 capture/peer timing diagnosis (2026-09-14)

Renewed approval covers the proposed timing investigation after15f650f2 gate24:
case6 exceeded20s (22.508s including cleanup),13/14 reaps and1/2 runs; both FS
exits remained90, only peer9's final receipt absent. Preserve36 current sources,
2737 latest/16732 total chain evidence hashes, raw snapshots and207 i386 pins.
The case6 image is pinned in the queue to the failed attempt; its43 artifacts
and five programs match the earlier16.624s complete guest. Neither identity nor
the absence of a fatal proves the cause of timing variation. OOM is not reached.

Only the existing transport diagnostic and its host test may change. Two finite
controls share the original full case6/layout2/4GiB observer and validator:
minimal reuses timeline_observer(stops); profiled reuses combined_observer with
the existing fixed clock/peer snapshots and callback/read/QMP stage accounting.
Both use the current binary full reader, one log sink and existing capture
metrics. Snapshot192x1280B, callback4096, timeline16384 and cost128 limits remain.
No new breakpoint address, guest write, trace/stepmask/clock mutation or rebuild;
kernel, Ring3, production observer, binary reader and capture remain unchanged.

Host regressions first exercise actual wrapper/dispatch identity, malformed
selection/image rejection and exact pair reservation. Freeze source/helper
hashes and the three commands before execution. Exactly one host group then
minimal/profiled once each; reserve before launch,45s command envelope per guest.
The existing20s capture plus bounded cleanup is not enlarged. A successfully
recorded deadline diagnosis is distinct from the complete original oracle
within20s including cleanup, and neither is package acceptance. Unexpected
fatal/assertion/measurement failure stops the pair. After both measurements or
non-reproduction, retain evidence and stop: no guessed repair or renewed
qualification, extra guests, implementation commit, queue transition or push.
Further implementation needs a demonstrated cause and its own bounded scope.

### Complete qualification after case6 diagnosis (2026-09-14)

Renewed user approval explicitly covers one complete qualification renewal.
Resume36 sources/249 latest evidence from verification-status-case6-timing.json;
preserve all16981 chain evidence files, raw snapshots and207 reference pins.
Neither successful diagnostic control accepts the earlier failed package.
No implementation, test, diagnostic, kernel or program source changes here.

Freeze the same30 ordered commands and source/helper hashes, substituting only
post-case6-renewal/ and an ordinary frozen supplementary guest bridge. Retain
20 host groups,3 builds, original file/FS18-case matrices, normal/reference gates,
binary equivalence/full and the four IRQ cases. Current file binary full/single
logging adapter and exact OOM-retirement proof stay; other defaults unchanged.
Matrices18x20s/360s each, binary pair20s/40s and IRQ4x20s/80s including cleanup;
host180s/build90s/matrix orchestration1800s envelopes unchanged. No invented
conditional legacy tests for a repair that was not made.

Execute each exactly once. First failure, timeout or unrelated source change
stops this whole pass: no repair, retry, extra profiling or diagnostic substitute.
Old attempts remain spent. All30 plus direct scope/ABI/cleanup and normal/FS/file
artifact review before implementation commit or queue transition. Queue/contract
and status docs may record results. After successful local package commit and
clean worktree, continue the next cohesive native64 priority package under the
interactive directive. No nested agent, push or full-OS completion claim.

### Bounded FAT12 timing diagnosis (2026-09-14)

Renewed user approval covers diagnosis of the first post-case6 qualification
guest: success/case0/FAT12/4GiB,22.565s including cleanup,15/16 reaps and1/2 runs.
Four programs exit82 and roots1/9 exit83; final peer10 receipt is absent.
Its43 kernel artifacts and five programs match a17.605s successful guest, but
the existing logs cannot distinguish host/debugger delay from guest progress.
Preserve36 sources/731 latest and17712 total evidence files plus207 i386 pins.

Reuse the existing timing mechanisms, consolidating case6 and FAT12 execution
behind one fixed-profile dispatcher. Only the existing diagnostic/test files
may change beyond queue/contract/status docs. Preserve the old case6 wrapper,
selectors and budget. FAT12 uses only the queue-pinned failed image, no rebuild.
Minimal records original callback intervals; profiled adds the existing fixed
clock/peer snapshots and bounded read/QMP cost accounting. Neither changes the
original observer/validator, capture, binary reader, guest or kernel. No new
breakpoint, guest write, trace, stepmask, timer or authority change. Snapshot
192x1280B, callback4096, timeline16384 and cost128 limits remain unchanged.

Host regressions cover both actual fixed-profile dispatches, exact image/path,
invalid selection and reservation order/budget. Freeze one180s host group and
two45s diagnostic commands before execution; each runs once, reserve before
launch. Keep20s active capture and existing bounded cleanup; full acceptance
still requires the entire original oracle within20s including cleanup. A
recorded deadline diagnosis is not oracle success or package acceptance.
Unexpected guest/observer/measurement failures stop the pair. After the pair
or non-reproduction, retain evidence and stop, with no speculative repair,
extra guest, qualification retry, implementation commit, queue transition or
push. The static direct-Make default-order finding remains pending and outside
this diagnosis. Old attempts remain spent; no nested agent.

### Direct Make default ordering correction (2026-09-14)

Renewed user approval covers the recorded direct-Make finding and its regression,
not another timing diagnosis. Preserve36 current sources,260 latest/17972 total
evidence files and207 i386 reference pins. This is the same attributed R8.3am
candidate, not a new accepted package. Only Makefile and its existing file-launch
host test may change beyond queue/contract/status documentation.

GNU Make conditional evaluation consumes FILESYSTEM_CASE, PIO_CASE and
STARTUP_CASE before their existing ?=0 assignments. The Windows wrapper passes
these values explicitly. Test actual direct Make plans with all eight combinations
of omitted/explicit zeros against the all-explicit plan. Run this selected new
test once before correction; require the measured expected-red default errors.
Then relocate only the three assignments before their first consumers. Preserve
all guards, explicit overrides, prerequisite enables, recipes and image layouts.
Keep all existing tests and cover all five filesystem layouts, eleven file cases
and incompatible configurations rejected before any build-output publication.

Freeze eight green groups before executing them once: file-launch/boot-producer/
media hosts180s each; normal/FS/file Windows builds90s each; one direct Make file
build90s using explicit profile enables but omitted case defaults; original i386
reference guard180s. The direct build uses the same discovered native tools and
workspace caches, not another agent. Review exact normal/FS/file binary identity
to the pre-fix build, and direct-Make versus Windows file-program/catalog/kernel
identity. First unexpected red cause or green failure stops without retry.

No kernel, Ring3, ABI, observer, capture, diagnostic, timeout, quota or authority
change. No new guest or renewal of the thirty-gate qualification; the unresolved
timing failure, OOM guest proof and remaining runtime gates stay open. Build-only
success permits neither package acceptance nor implementation commit/queue
transition. Preserve prior budgets/evidence; no nested agent, push or OS claim.

### Direct-build stdio correction and build renewal (2026-09-14)

Renewed approval covers the demonstrated helper defect and the same eight build
groups. Preserve36 sources/553 latest and18525 total evidence files,207 pins and
raw snapshots. The old pass stays6/1/1: direct Make returned2 with empty log,
despite byte-identical binaries. The small stdout-only host comparison failed
with implicit streams and passed with explicit streams; it is not acceptance.

Keep every old frozen helper intact. The new make_stdio_build.py changes only
the output prefix and adds stdout=sys.stdout,stderr=sys.stderr to the existing
bounded subprocess invocation. No OS, Makefile, test, observer or capture change.
Freeze source/helper/tool hashes and the same eight commands with fresh outputs:
three180s hosts, four90s builds (direct child80s), reference guard180s. Execute
each once; first failure stops without retry. Direct exit0, nonempty completion
log and unchanged43 kernel/five program comparison are all required, alongside
the original reference guard and normal/FS/file artifact identity review.

Build success does not renew the thirty-gate guest qualification or accept the
package. No guest, deadline change, implementation commit, queue transition,
nested agent or push. Original timing/OOM/runtime proof and budgets stay open;
queue/contract/status documentation may record this bounded repair.

### Source-bound i386 reference renewal (2026-09-14)

Explicit renewed approval covers the later i386 build and its shared EXT2
dependency, not an OS repair or another native qualification attempt. Resume
36 attributed sources,19084 preserved evidence files and207 native bootstrap
artifacts. Earlier reports calling those207 i386 pins were incorrect. Preserve
all original images, signatures, programs and historical qualification records.

Candidate main2b58094b/package9f2998be and historical framebufferac4b127e are
fixed before tests. Exactly STORAGE changes from6450b474 to4cb46748; reviewed
96-program digest7ba8d99a, common VMware kernel3be2b5c9 unchanged. Fresh separate
VMware/QEMU builds must reproduce the reviewed program bytes and their correct
platform kernels. Freeze non-document tracked build inputs, current sources,
helpers, tools and original artifacts. No parser/kernel/source repair is allowed.

Add only the reference-renewal consumer and its host regression, plus the old
guard's literal pins/attribution after successful qualification. Reuse the actual
existing content/signature/SBOM/image admissions and all platform-matched guest
oracles and cleanup. Temporary fixed legacy consumer constants must restore in
finally, never change originals or expose arbitrary image/profile inputs.

Freeze17 ordered groups:10 hosts180s each (renewal, original reference, EXT2
ranges, shadow EXT2/FAT32, symlink, EXT2 stat fixture, boot manifest/signature,
EXT2 recovery), two fresh VGA builds900s each, original four reference guests
under600s (two VMware APIC copies and QEMU APIC/PIT snapshots,60s per guest),
existing EXT2 stat150s and symlink/recovery180s guests (outer180/210s), reviewed
admission180s, then the original guard180s. Each runs once; first failure stops
without repair, retry, later guest or pin change. Existing user VMs are never
stopped; copies run headless, QEMU references use snapshots and only the unique
EXT2 fixture is writable. No network or device authority expansion.

Only after groups1..16 pass and direct review may guard image/program literals
and qualification attribution change; group17 then verifies those exact pins.
The previous guard source is already an external evidence entry. Preserve its
raw bytes before edits at reference-renewal-source/
scripts__verify_x86_64_reference_artifacts.py; historical evidence resolution
may substitute only this one path with its exact prior SHA256, not change any
historical manifest or log. No automatic learning or other evidence relocation.

Reference success does not accept AM or renew its30 native groups. All prior
timing/OOM/IRQ obligations and spent budgets remain. No implementation commit,
queue transition, nested agent, push or claim of a finished64-bit OS.

### Reference interpreter correction (2026-09-14)

Renewed approval changes only the two build-command interpreter selections to
the installed absolute PowerShell7 executable, SHA-bound before execution.
The previous10/1/6 result remains failed: our WindowsPowerShell5.1 invocation
lacked ProcessStartInfo.ArgumentList, while installed Core7.6.6 supports it.
Preserve39 attributed sources,19168 evidence entries,117 original artifacts
and207 native bootstrap pins; archive current source bytes before edits.

Keep the old frozen helper and logs. A new ordinary-command helper delegates
its unchanged execution, checks and first-failure handling. It substitutes
only the two interpreters and a fresh reference-pwsh/ output prefix. The existing
renewal adapter changes only fixed output-prefix and contract-commit literals;
no logic, production build-script, OS, parser, test, guest, timeout or oracle
change. Freeze all1516 inputs and the same17 ordered groups with their original
deadlines once. First failure stops without another repair, retry, guest or
pin change. Only after first16PASS and direct review may the previously approved
guard literals/attribution change, then gate17 runs once. The historical guard
archive exception is unchanged. No native30-gate renewal, implementation commit,
queue transition, nested agent, push or full64-bit OS acceptance follows from
reference-only success.

### Source-only reference digest correction (2026-09-14)

Renewed approval covers the demonstrated empty-source admission defect in the
existing renewal adapter and test. Preserve39 attributed sources,22679 evidence
entries,117 original artifacts,202 prior-build artifacts and207 native bootstrap
pins. The previous12/1/4 remains failed before every guest; neither the committed
empty syscall.c placeholder nor any other source is removed from the inventory.

First execute one selected empty-source regression against the unchanged old
adapter,180s maximum; require the original invalid-artifact-size error. Then
introduce a source-only SHA256 reader: allow zero through the existing1GiB
maximum,1MiB chunks, fixed size-derived read count and one EOF byte. Require
regular single-link files, existing path/alias checks and stable path/open-file
identity, size and timestamps before/after. Reject missing, directory, link,
oversize, shortened, grown, changed or wrong-hash inputs. Images, programs and
logs retain the original nonempty artifact hasher; original_artifacts calls
select that policy explicitly. Actual regression tests cover the empty/source
distinction, size/type/link bounds and mutations during reads; old tests stay.

Only adapter/test and new ignored command helper change beyond documentation;
no OS, parser, build-script, platform oracle, guest, time or resource-budget
correction. Keep old helpers/results and use reference-source/ plus the fixed
new authority literal. Freeze all1516 inputs and the same17 groups, order and
deadlines under the existing PowerShell7 pin. Unexpected red or first frozen
failure stops without repair, retry, later guest or pin change. After first16
PASS/direct review, only previously approved guard literals/attribution may
change, then gate17 once. Historical guard archive exception unchanged. No
native30-gate renewal, implementation commit, queue transition, nested agent,
visible VM, existing VM control, push or complete64-bit OS claim.

### Windows source metadata views (2026-09-14)

Renewed approval corrects only the demonstrated cross-view source-identity
comparison in the existing adapter/test. Preserve39 sources,22743 evidence
entries,117 originals,202 prior-build artifacts and207 native bootstrap pins.
Previous0/1/16 and its8-success/2-error host result remain failed; the empty
source regression passed but ordinary source positives failed before reading.
The read-only inventory observed1300 stable path/handle differences, including
1299ctime values and four CMD mode projections; no source omission is permitted.

First execute one180s new actual CMD/rewrite positive against the unchanged old
adapter, requiring source-changed-before-read as expected red; never execute
the command file. Then compare shared device/inode/type/link/size/mtime/optional
birthtime across views, and each view's full identity including ctime/mode with
itself before/after reading. Keep zero-length sources,1GiB/1MiB bounds, exact
reads/EOF, paths, links, missing/type checks and original nonempty artifact/log
policy. Add real rewrite/CMD positives, cross-view mismatch and local-view
ctime/mode negatives. Actual grow/shorten/mtime regressions must record their
mutation, consume payload and require the exact rejection phase; a generic
pre-read ValueError is not evidence of a mid-read fault being detected.

Only adapter/test and fresh ignored command helpers change beyond docs; no
kernel, OS, parser, build-script, guest, deadline or oracle correction. Use
reference-metadata/ and its fixed authority, preserve all old helpers/logs,
freeze all1516 inputs and the same17 commands/deadlines under the existing
PowerShell7 pin. First unexpected red or frozen failure stops without repair,
retry, later guest or pin change. First16PASS/direct review permits only the
previously approved guard literals/attribution, then gate17 once. Historical
guard archive exception unchanged. No native30-gate renewal, implementation
commit, queue transition, agents, visible/existing VM control, push or OS claim.

### Regular-user VMware startup comparison (2026-09-14)

Renewed approval permits one diagnostic comparison in the regular user account,
not another reference acceptance pass. Preserve39 attributed sources,26272
earlier evidence entries,117 originals,404 build artifacts and207 native pins.
The prior17-group result remains12/1/4: source and signed-content admission
completed, but sandbox vmrun failed Unknown error before any serial output.

Freeze the original1516 inputs/tools and an ignored ordinary-command helper
under reference-user/. Run once through reviewed regular-user escalation as
asusnb/oe3sr, using the unchanged original VmwareCopy main/APIC case and a new
exclusive copy of the same reviewed build/reist-os.img (2b58094b7bc68eb261f18ab0cf053b4815f8528bc6e33ed6ca68e73232353bc7).
Temporarily override only the evidence root. Keep all VM settings, original
GTEST/recovery/timer checks,20s launch,60s guest and owned-copy cleanup unchanged.
The child envelope is180s; exhaustion fails and permits only original cleanup
of this exact fresh VM path. Existing VMs or VMX processes prevent launch.

Preserve the fresh copy, serial/VM logs and command/cleanup receipts; verify
sources, original artifacts and earlier evidence again. Only bounded relevant
read-only host diagnosis may follow. No production/test/guard change, new
builds or acceptance gates, retry, pin update, ACL/service/security/hypervisor
change, visible/existing VM control, nested agent or push. Stop after the
single comparison. A successful diagnostic is not reference/package acceptance,
does not renew native30 gates and permits no implementation commit or queue
transition. Different execution context alone is not a proven internal cause.
