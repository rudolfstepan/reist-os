# Native bounded string formatting — R8.3bt

Frozen after accepted native math9e9e31f0, 23 September2026. Interactive
main-worktree execution, one active package, no agents or push. This contract
extends RING3_STRING_FORMAT_CONTRACT to the existing native AMD64 process
profile; it grants no new authority. Native64 completion remains open.

## Inventory and references

Reuse musl1.2.6 pinned by build_user_math.py, the existing build_user_text.py
extractor and exact-match adapters, private memory stream, public snprintf and
vsnprintf headers, per-process libc errno and accepted libm. ISO C11 N1570
7.21.6.1/5/12 and POSIX.1-2024 error conventions remain the references.
The target is System V AMD64 LP64 with SSE2, no red zone, AVX or MMX.
Windows numeric host evidence is LLP64 and cannot substitute for LP64 guest
or AMD64 variadic-register/stack evidence. No full libc/POSIX compatibility.

All integer lengths, floating conversions, long double, positional arguments,
width/precision, truncation, count overflow, C-locale wide conversions and %n
belong to this single existing formatter failure domain. Retain normal C
pointer/type/object/non-overlap preconditions. Discarded padding must remain
capacity-aware; no billion-iteration loop for a short output buffer. Invalid
process pointers must produce contained real faults. No heap, VFS, driver,
file-stream, locale service, kernel formatter or fabricated successful I/O.

## Implementation boundary

Append an explicit x86_64 selector to compile_text with i386 default unchanged.
Publish ELF64 libreisttext.a, opt-in headers, pkg-config and upstream licenses
alongside the accepted native C/C++/math sysroot. Strong byte/errno symbols
must resolve from accepted libc; inspect actual undefined symbols, linker map,
instruction set and static stack usage. No duplicate division/math helpers.

NativeText implies NativeMath in both build frontends. Reuse the accepted
NativeMathHardware rendezvous only for WHPX qualification. Package ordinary
texttest.prg on the existing shell search path and a separately signed eight-file
read-only EXT2 medium retaining all seven accepted math files byte-for-byte.
Do not modify default images, existing kernel mechanisms or syscall quotas.

Reuse text vectors with actual-ABI long expectations. Retain the old i386
and host1MiB object cases; native fixed-image vectors use an explicit8192-byte
object plus INT_MAX discarded-width/precision cases. This is a test-object
bound, not a formatter API size limit. Add native GP/FP register and stack
varargs, mixed long/double/long-double, va_copy, canaries and %n length proofs.

The foreground test uses the existing fixed5000ms/4096-operation/1024-output
profile and shell wait/CPU bounds. Private zero-default qualification selection
is not a command-line capability. Observe fresh errno/FP defaults, completed
formatting witnesses, a real bounded sleep with errno/rounding preservation,
and actual generation-scoped reap. Normal execution, invalid %s read, invalid
destination, invalid %n write, UD2, sleeping hang, CPU spin, owner loss and
repeated starts must retain the complete accepted shell/IPC/PIO/RET/resource
proof. Never infer fault success from output text or tolerate missing witnesses.
One normal4GiB and8GiB case plus the eight failure/reuse cases give ten guests.

## Frozen verification and finite reservation

Five gates, each executed once per candidate; stop at first failure:

1. `python test/test_x86_64_text_runtime.py -v` (600s).
2. `python scripts/verify_x86_64_text_runtime.py --defaults` (600s): actual
   retained i386 text tests, full disabled-source projection and accepted
   native math/CLI/GUI/network/C++ artifact bindings.
3. `python scripts/verify_x86_64_text_runtime.py --package` (600s): ordinary
   and hardware builds, signed eight-file medium, exact prior program bytes,
   bounded stacks and archive/link closure. Build300s, media180s individually.
4. `python scripts/verify_x86_64_text_runtime.py --runtime` (2200s): ten fresh
   guests180s each,1800s aggregate, fixed profile quotas and raw snapshots.
5. `python scripts/verify_x86_64_text_runtime.py --review` (600s): independent
   full raw replay, source/tool/media binding, scope and cleanup review/seal.

Initial development reservation: eight host invocations600s each, two native
builds300s each, two media180s each and three diagnostic guests180s each.
Every attempt gets a fresh numbered receipt under ignored
build/codex-agent/r83bt-native-text. Preserve failures; evidence-directed
correction windows require an appended finite reservation before execution.
Use accepted BS portable binding09/compile-freeze13 as an immutable tool.
No portable-QEMU source edits or new tool build are in this package scope.

After all gates, only queue and the two current-work documents may change for
closure. Verify frozen source hashes, commit locally and verify a clean tree.
Then inventory the next native64 package. QuickJS/DOM, new time or file/network
rights and R3.6b VMware pointer work remain outside this package.

## Development evidence

Host01 confirms the missing native architecture argument before implementation.
Host02 passes actual AMD64 O0/O2 formatting,128 independent reference samples,
mixed register/stack varargs, va_copy and ABI-aware vectors in2.150s.
Build01 ordinary NativeText passed21.464s. Media01 failed before construction
because the new consumer imported itself instead of the accepted math consumer;
correct that exact import. Runtime-adapter generation also stopped before file
publication on an incorrect config.update anchor; correct the anchor.
No guest has run. Existing initial reservations remain; media01 is spent.

Host03 rejected the stale seven-file inode bitmap; the eight-file medium needs
19 allocated inodes and13 free. Correct the consumer bitmap to0x07ffff.
Host04 then passed media checks but observer construction correctly rejected
the ordinary image lacking hardware-gate symbols. Use reserved build02 with
NativeText/NativeMathHardware for hardware observer/guest checks; ordinary
build01 remains the signed-media input. No weakened bootstrap predicate.

Media02 passed3.395s; hardware build02 passed23.070s; host05 passed all three
current tests29.553s, including construction of every hardware observer.
The compiler reports72 total stack files and fmt_fp as dynamic312 bytes because
upstream sizes its big[] field from the conversion type. Host06 reproduces the
static-stack regression0.718s. For native compilation only, exact-match replace
that array declaration with the compile-time maximum for long double, retaining
the original logical bufsize and all output semantics; assert long-double bounds
cover double. Every native frame must then be static<=8192 bytes and the sum of
all compiled frames plus2048 margin must fit the unchanged32768-byte stack.
This is fixed-capacity scratch storage in the same formatter, no new mechanism.
Reserve hardware build03<=300s and media03<=180s after correction. Media03 uses
the corrected build03 only for development; qualification still creates its own
fresh ordinary/hardware pair and signed ordinary medium. Initial hosts07/08 and
all three diagnostics remain available. Keep both prior builds/media unchanged.

Host07 passed2.876s with static-stack evidence and unchanged O0/O2 results.
Build03 passed22.002s. Media03 correctly rejects that hardware image at the
retained BC kernel pin0.333s; do not weaken the signed ordinary-image rule.
Use build03 for direct bounded diagnostics only. The later package gate builds
and signs a fresh ordinary image. Media02 remains the successful earlier
development signing proof; no further development signing retry is needed.

Diagnostic01 healthy4GiB passed73.316s with complete two-session raw evidence.
Host08 passed disabled-source projection and complete healthy replay, then
rejected two actual baseline SSE2 mnemonics absent from the inherited numeric
allowlist: pmuludq and punpckldq. Add only these SSE2 operations; AVX/MMX and
all other ISA restrictions remain. Reserve host09<=600s for the final targeted
archive/static-stack/provider/header/witness and completed diagnostic replays.
Host01–08 are spent. Diagnostic02 invalid-count is active; diagnostic03 owner
loss remains reserved. No qualification gate has run yet.

Diagnostic02 invalid-count passed74.024s with actual #PF/error6/CR2=4 and a
fresh normal generation. Diagnostic03 owner-loss passed74.131s. Host09 passed
archive/strong-provider/static-stack checks, semantic witness mutations and
both complete replays16.025s; its header fixture omitted the SDK's no-unwind
flags and correctly failed object admission on .eh_frame. Apply the actual
no-exceptions/no-unwind fixture flags; reserve host10<=600s for C/C++ headers.
No public-header, object-admission, native library or guest change is required.
Compiler stack evidence:72 reports, all static,14736 total bytes, largest7832;
the unchanged32768-byte stack includes the frozen2048-byte call/entry margin.

Host10 passed0.565s. Development work is ready for candidate01: ten host
attempts, three builds, three media attempts and three diagnostic guests are
spent and retained. Freeze the five commands above unchanged, including ten
fresh guests and the independent raw replay. No diagnostic result substitutes
for a fresh gate. No further development operation is reserved at this point.

Candidate01 gates1/2/3 passed107.38/9.43/80.66s and healthy4GiB passed76.84s.
Healthy8GiB failed37.006s at the unchanged `RET preserves CPU state` predicate
during the second shell session, after first-session text witnesses completed.
The capture does not identify which register changed. Preserve candidate01;
gate4 failed and gate5 did not run. No text runtime success is inferred from
partial evidence and no register/RET predicate may be relaxed.
Reserve diagnostic04 healthy8GiB<=180s with failure-only bounded before/after
register and remote g-packet capture, then stop for evidence review. This changes
only the observer diagnostics, not guest code or the immutable portable tool.
No next candidate, tool edit, unchanged qualification retry or further guest
is authorized by this diagnostic reservation.

Diagnostic04 passed73.732s without a RET mismatch. This does not correct or
supersede candidate01's failure. The diagnostic and failed-candidate hardware
ELFs are byte-identical (SHA745e0d4c6a9442a93864d834a680845f8919794a310f8b1c4f833e5d50d93de6).
Local GDB help confirms `set remotelogfile` records actual protocol packets.
Reserve diagnostic05 healthy8GiB<=180s with optional diagnostic-only remote
packet recording capped128MiB, checked at every RET. Retain the unchanged
before/after equality and all guest predicates. The default gate observer must
leave packet recording disabled. This is evidence collection, not a repair;
no candidate retry or tool-source change follows from a passing diagnostic.

Diagnostic05 failed6.774s before text execution: setting the remote log after
the target connection left no log file, and the strict size check rejected it.
Configure remotelogfile with a forward-slash path before target remote in the
generated GDB startup file. Reserve diagnostic06 healthy8GiB<=180s for that
corrected logging setup, same128MiB cap and unchanged RET equality. Preserve05;
this corrects instrumentation setup only, not the original register failure.

Diagnostic06 failed13.020s before GDB or any guest instruction: QEMU reports
`cannot set up guest memory '/rom@etc/acpi/tables'`; its metric stop_reason is
vm_exit. The10s bootstrap deadline then fails closed. No logging/RET result is
claimed. Read-only GlobalMemoryStatusEx evidence in host-memory01.json reports
34.312GiB total commitment capacity and only8.077GiB available, versus the
8GiB guest plus QEMU/WHPX/firmware/debugger overhead. Physical availability is
10.931GiB and is not equivalent to available commitment capacity. All owned
guest/debugger processes are closed; no other process or Windows setting was
changed. This is an external host-resource blocker in addition to the still
unattributed RET mismatch. Preserve the visible candidate and failed gates;
no implementation commit or qualification retry until host capacity changes
and a new finite evidence-directed diagnostic window is recorded. Native math
9e9e31f0 remains accepted. Text/default/build/4GiB successes do not constitute
text package or native64 completion.

Renewed continuation: read-only host-memory02.json at 2026-09-23T12:05:09Z
reports 7.906GiB available commitment, below the frozen 8GiB guest itself.
The external allocation blocker persists; no guest retry was started, no
reservation reset, no acceptance predicate or host setting changed.

The user closed unneeded applications. host-memory03.json now records
13.130GiB available commitment. Reserve diagnostic07 healthy8GiB<=180s
with the corrected pre-connect remote logging, capped128MiB, and unchanged
RET/register predicates and immutable binding09. This resumes evidence
collection after the external capacity change, not qualification or repair.
Review its evidence before any further operation; preserve all failed attempts.

Diagnostic07 failed7.776s with actual trace header end=0/error=1, read
from native_pio_trace at0xffffffff8013efc0; remote logging now works.
The guest trace producer explicitly sets this error on an invalid task/domain
or transfer predicate. Reserve diagnostic08 healthy8GiB<=180s with one
read-only execution probe at native_pio_trace_capture64.error capturing
registers, task slot, domain/request bytes and stack before the error store.
Keep all existing predicates,128MiB log cap, image and tool unchanged.

Diagnostic08 failed7.712s: producer error is the bounded emergency OUT
(port0x3f6,value6) after exception_fatal; state0 is intentionally unowned.
Serial records fatal vector0x20. This is a secondary trace error, not formatter
execution. Reserve diagnostic09 healthy8GiB<=180s with a read-only probe
at x86_64_timer_interrupt64.invalid, recording registers,256-byte exception
frame and fixed timer cells. Retain08 probe and all existing predicates.

Diagnostic09 failed9.983s with the same fatal timer/secondary trace error;
the general .invalid probe did not fire. Native runtime has separate
.shell_invalid/.shell_clock_invalid branches. Reserve diagnostic10<=180s
with both exact branch probes, recording256-byte frame, timer cells and
registers. No image/tool change, no acceptance retry.

Diagnostic10 failed9.759s at .shell_invalid with rax=0,r9=4, ticks=EOIs=4:
timer_runtime_progress64 reports an expired TSC lease, not invalid context.
Full remote packet logging perturbs timing; no deadline change is permitted.
Reserve diagnostic11 healthy8GiB<=180s without full packet logging. Add
raw g-packet before/after each RET in a32-entry memory ring, eachpacket<=8192,
written only at session completion or mismatch. This differentiates actual
remote register state from GDB cached registers while avoiding per-packet disk
logging. Keep exact RET equality, image/tool and runtime bounds unchanged.

Diagnostic11 passed76.617s, all unchanged guest predicates. Offline parsing
of both32-entry end-of-session rings agrees with GDB for every GP register
and EFLAGS. The original candidate failure remains unattributed. Reserve
diagnostic12 healthy8GiB<=180s with the same ring and an explicit1ms host
pause immediately before RET resume for steps2500..2700 (201ms total),
bracketing original failing step2592. This varies the debugger timing only;
no guest registers, deadlines or tool sources change. Capture a32-entry ring
at step2600 as well as session completion and any failure. Review before more.

Diagnostic12 passed75.536s including the201ms aggregate timing perturbation
around the original failure window. Neither11 nor12 reproduced candidate01.
The original failure remains blocking; no corrected runtime or package
acceptance is claimed. All owned guest/debugger processes exited.

## Proposed verifier-only diagnostic scope extension (not authorized/executed)

The package currently fixes BS binary-binding09 and forbids portable source
changes. AGENTS.md requires stopping and reporting when another source file
is needed. The next evidence-directed measurement needs the raw WHPX state
inside the verifier, below GDB's register-cache and protocol boundary.

Proposed sole source path, under ignored evidence:
`build/codex-agent/r83bs-native-math/portable-qemu/qemu-ae35f033b874c627d81d51070187fbf55f0bf1a7/target/i386/whpx/whpx-all.c`.
First preserve and hash its current bytes and the accepted compiler freeze.
Add a diagnostic-only fixed-capacity register record around the three existing
native RET probe addresses0xffffffff80110000..02. Capture actual WHPX GP,
RIP/RSP/RFLAGS/CR3, debugger step state and exit reason before/after execution;
retain at most32 records and publish only on an observed register mismatch
or end-of-guest collection. No register writes, changed breakpoint semantics,
IRQ policy, TF normalization, deadlines or acceptance predicates. API read
failures produce failed diagnostics, never an accepted comparison.

Reserve, only after scope authorization: one source/static review<=120s,
one portable rebuild<=300s into a fresh BT evidence directory with a new
source/tool/DLL/firmware binding, and one healthy8GiB diagnostic<=180s.
Use a fresh receipt for each operation. Keep binary-binding09, runtime08 and
all earlier source freezes, binaries and evidence intact. Do not substitute
this diagnostic binary into any frozen qualification command. Review the
actual state delta before proposing any verifier correction or next candidate.
No REIST kernel, authority domain, system installation or host configuration
change is included. A passing diagnostic cannot erase the original failure.

User continuation after the explicit scope proposal authorizes that diagnostic
extension. Execute its one review, one build and one guest reservation.
End-of-guest collection uses the existing remove-all debugger breakpoint
callback; at most one32-record dump, also on first actual RET mismatch.
Accepted runtime08/binding09 remain immutable and are not replaced.

Source review01 stopped before source publication: CRLF/LF anchor mismatch.
Preserved source and freeze hashes match. Reserve source review02<=120s with
newline-normalized matching; the build and guest reservations are unspent.

Source review02 passed0.083s; diagnostic compile01 passed13.732s.
Diagnostic13 consumes the authorized180s healthy8GiB reservation with the
new portable-diagnostic01/binary-binding01.json and the retained GDB ring.
No qualification gate or accepted binding changed.

Diagnostic13 passed85.791s with5008 direct WHPX RET transitions and no
raw mismatch. Its final32x19 register pairs preserve all checked state;
GDB full guest/reap/CPU/PIO checks also pass. The original failure is still
unattributed. Reserve diagnostic14<=180s: existing repeated-generation case
(mode6) at8192MiB rather than4096, same diagnostic binary and GDB ring.
This exercises additional generation turnover at the failing RAM profile,
not an unchanged qualification retry. No new build or source change.

Diagnostic14 failed2.701s before any guest: the inherited case/layout
contract admits8GiB only for case5. Preserve that guard. Reserve diagnostic15
repeated generations at its existing4096MiB profile<=180s, same diagnostic
binary/rings. This covers generation turnover without a new case/layout ABI.
No observer admission guard or qualification matrix is altered.

Reserve diagnostic16 healthy8GiB<=180s using the same direct WHPX binary
but the original GDB read cadence (no per-RET maintenance g-packets, no
delay injection). The failure-only raw packet capture remains. This tests
whether extra register queries perturb the original failure; no source/build
or guest behavior change. Run only after diagnostic15 completes and review.

Diagnostic15 passed96.858s:6394 direct WHPX RET transitions, no mismatch;
final32x19 pairs and full repeated-generation guest proof pass. Proceed with
the already reserved cadence comparison16. No qualification retry.

Diagnostic16 passed79.991s with the original GDB read cadence; direct WHPX
registers also agree. Additional g-packets are not required for that success.
Original failure occurred under greater host load; reserve diagnostic17
healthy8GiB<=180s with the same binary/cadence and two bounded host hash
workers (1MiB fixed input each,160s maximum, stop/join at guest completion).
This is a scheduling-contention diagnostic, not a memory-pressure test or
host-setting change. Stop workers on failure as well. No new build, guest
register changes, acceptance retry or deadline relaxation.

Diagnostic17 passed81.511s,5018 direct RET transitions without mismatch.
Both bounded hash workers stopped and joined. Higher CPU load alone did not
reproduce the failure. No further unchanged healthy-case repeats are planned.
Reserve diagnostic18..22 for the not-yet-run native fault cases invalid-read,
invalid-write, crash, hang and cpu, respectively:180s each,900s aggregate;
stop on first failure. Same diagnostic binary and original GDB cadence.
These complete independent missing development fault coverage while also
retaining direct WHPX failure evidence; they are not qualification gates or
substitutes for the still-required fresh ten-case acceptance matrix.

Diagnostic18/19 passed81.367/81.209s (invalid read/write). Diagnostic20
ran its guest to completion but full replay failed80.348s on the foreground
timeout/cancel expectation. BT inherited C++ mode5=hang; BT mode5=UD2 and
mode6=hang. Its fault-vector/outcome mapping is already correct, but two
foreground timeout predicates still use5. Batch stopped;21/22 remain unspent.
Reserve host11<=120s to reproduce with the retained complete crash evidence,
then correct only both exact inherited timeout predicates to BT mode6 and
reserve host12<=120s for that full replay regression. No fresh crash guest
is needed for this development correction; qualification stays fresh.

Host11 reproduces the crash-replay error6.375s. Host12 passes9.579s
after correcting both exact inherited hang predicates from5 to6. The
original crash capture/failed summary remains unchanged; full raw replay
now proves its actual UD2/reap/restart sequence. This fixes a separate
verifier mode-mapping defect, not candidate01's RET mismatch. Continue
unspent diagnostics21/22 with the corrected evaluator and unchanged guest.

Diagnostic21 passed81.545s with the corrected hang mapping and actual
timeout/cancel/reap/restart. Reserve host13<=120s after22 completes for
full raw crash/hang/CPU regression replays. Keep the failing20 summary as
history; its corrected proof is the separate host regression, not a rewrite.

Diagnostic22 passed80.967s: actual CPU quota containment and fresh normal
process. Host13 passed30.867s: full raw UD2/hang/CPU regression replays.
The direct-register review covers46488 WHPX RET transitions over nine guests,
with no mismatch; every retained32x19 pair preserves checked registers.
All owned guest/debugger processes and stress workers are closed. Original
BS runtime08 and compile-freeze13 hashes still match accepted binding09.

Current unresolved acceptance blocker is specifically candidate01's RET
register mismatch, whose failing capture lacks before/after register values.
No later diagnostic reproduces it, including original GDB read cadence,
repeated generations, bounded CPU contention and all remaining fault modes.
The corrected timeout-mode adapter explains diagnostic20 only; it does not
explain or repair that earlier register discrepancy. Repeating unchanged
healthy runs or changing runtime/debugger semantics without a measured delta
would not provide an evidence-directed correction. No acceptance retry,
queue completion or implementation commit is justified by these results.
The read-only WHPX ring and failure-only GDB dump are ready for a concrete
reproduction; an independent explanation of the original failed comparison
remains required. This is an unresolved safety/evidence decision, not an
administrative reservation stop. Preserve all candidates, failures and the
visible implementation. Native64 completion is not claimed.

Renewed evidence review identifies a concrete timing correlation: candidate01
sent run2's first8 input bytes at36.751442s from trace prefix ending at RET2590;
RET2592 then failed after a root console read returned -EAGAIN. Diagnostic16
used the same prefix but passed, so this is a testable overlap, not a cause.
Host-memory04.json records13.432GiB available commitment. Reserve diagnostics
23/24 healthy8GiB<=180s each (360s aggregate), using accepted binding09 and
original GDB query cadence with failure-only register dump. Delay only the
first second-session8-byte host input write by1ms/8ms, respectively; preserve
payload, generation/ack checks, all deadlines and the existing feeder replay.
Record actual write timing and trace prefix in a separate bounded receipt.
No WHPX source/build, VM register write, new input authority, acceptance retry
or altered guest profile. Stop the pair on first failed guest for evidence
review. This targets asynchronous input overlap, not unchanged healthy retries.

Diagnostic23 passed72.802s with accepted binding09. The measured first
run2 write follows the same trace prefix ending at RET2590 as candidate01;
actual delay1.073ms. No RET mismatch; proceed with reserved8ms phase24.
Microsoft WHPX Exit Context Data Types documentation confirms that each
exit supplies a reason-specific context; this does not establish cancellation
as the cause. Reference: https://learn.microsoft.com/en-us/virtualization/api/hypervisor-platform/funcs/whvexitcontextdatatypes

Diagnostic24 passed72.370s; measured second-session first-chunk delay8.080ms.
Both phase receipts match the existing replayed chunk payload/prefix, both
full guest proofs pass, and both processes are closed. The serial-input
correlation did not reproduce the register mismatch with either delay.
No causal conclusion or candidate acceptance follows. Existing direct WHPX
measurements, mode-mapping correction and failed candidate remain preserved.
No additional source/runtime change or unchanged retry is justified by these
results. The missing failing register delta remains the precise evidence
blocker; the failure-only capture is ready should that condition recur.

Renewed source review: whpx_vcpu_run chooses exclusive step-over solely from
current PC and an active breakpoint, without checking whether the last exit
actually hit it. A host cancellation at an armed return target can therefore
be mistaken for a previously delivered breakpoint. This is a hypothesis,
not attribution of the missing candidate01 register delta.
Freeze one isolated verifier fault-injection transaction: source review<=120s,
portable rebuild<=300s, diagnostic25 healthy8GiB<=180s. At exactly one genuine
RET-target debug exit in transitions2580..2620, retain all real registers and
memory but present Canceled instead of Exception to the verifier switch.
Record the original reason/PC/flags/count before that metadata substitution.
This deliberately tests verifier event handling; it does not fabricate guest
success and must never be used for qualification. Keep all original register,
PC, stack and hit-count assertions; stop at first mismatch and review raw data.
Same already authorized portable whpx-all.c diagnostic source only; no kernel,
IRQ-policy, deadline, guest register write, external action or new rights.
Fresh source backup, binding and receipts; prior binaries/freezes immutable.
Diagnostic25 failed40.385s as expected under the single controlled cancellation:
actual RET2580 preserves all direct WHPX registers, but the GDB continuation
skips its first target encounter and returns there later with changed GPRs.
The strict RET assertion fails with the recorded before/after delta. This
reproduces the failure mechanism, without proving the historical candidate01
cancellation (its old capture omitted that delta). All failed evidence retained.
Freeze correction01: same portable whpx-all.c only, per-vCPU debug-stop PC
and validity; consume permission to step over only after a reported debugger
stop at that PC or an explicit debugger single-step. Canceled exits must not
grant it. One source review<=120s, incremental build<=300s, same injected
healthy8GiB diagnostic26<=180s. Existing exact CPU/stack/PC/hit assertions and
full raw guest replay remain required; no acceptance or kernel change.
Correction01 build passed3.371s; diagnostic26 passed76.690s with exactly the
same single cancellation at RET2580 and unchanged assertions/full raw replay.
This provides fail-to-pass evidence for the measured debugger event defect.
Freeze production verifier preparation: source review<=120s, one build<=300s
from accepted BS whpx-all.c plus exactly the debug-resume correction; omit
both read-only RET instrumentation and synthetic cancellation. Preserve BS
binary09 and all prior source/build receipts. Add a host regression checking
the failed25 delta, successful26 full replay and exact production patch
projection, then qualify candidate02 through the same five gates/ten fresh
guests (existing600/600/600/2200/600 limits). Bind all prior candidate01 raw
failure evidence and portable source/patch/build/binary history before freeze.
No additional development guest; qualification itself exercises the clean
production verifier. Native implementation/kernel/ABI and safety limits stay
unchanged. Historical failure cannot be retrospectively attributed with
certainty; the reproducible equivalent failure is fixed and requalification
remains mandatory. Stop at first gate failure and retain its evidence.
Candidate02 gate1 failed81.884s: twelve tests passed; the new cancellation
replay supplied case0 (4GiB) for the correctly captured healthy8GiB case5.
The unchanged matrix-member guard rejected that caller before replay. Zero
qualification builds/guests spent for candidate02; all evidence retained.
Correct the test argument from the existing explicit spec_for('healthy8g'),
reserve host14<=120s for this regression only, then candidate03 with the
unchanged five frozen gates and ten fresh guests. Include candidate02 history
in regression input bindings. No guest/tool/runtime change or relaxed guard.
Host14 passes7.822s: complete corrected cancellation replay and exact four-hunk
projection onto the accepted source. Candidate03 is the next fresh qualification.

Candidate03 accepted: allfive gates [85.231, 6.427, 115.368, 899.353, 92.294]s,13 host tests andten fresh guests.
Independent complete raw replay passed; seal fc9d2d9b27df9c9558ddbb313b0102625732ae3919314b3b0680bd9387440100.
Only queue/status/acceptance documentation changes follow frozen gates.
Original BS binaries and all failed candidates/diagnostics remain retained.
No complete native64 claim; next prerequisite inventory, R3.6b deferred.
