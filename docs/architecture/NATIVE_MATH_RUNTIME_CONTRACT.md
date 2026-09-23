# Native binary64 mathematics — R8.3bs

## Inventory and boundary

Starts after clean82ce94a03afda11a0f0c5277fe98e2c66bb5da4f (native C/C++),
five gates andten fresh guests. Predecessor seal
b328527b28eebc5009829a7162a373622d3b0421358fc6321aebc53bbaa6162c;
final clean receipt317a5e4a4b6e0a17a2542d0a22b6e7d4c7cea683c66d4b78463abf94c66bb4b9.
QuickJS also requires libm and bounded numeric text. Current build_user_math
hardcodes x86-freestanding/i386, no SSE and i386 lrint. The native scheduler
already owns eager FXSAVE64/FXRSTOR64 state per task (R8.3b), including
XMM0..15, x87/MMX and controls. R8.3c admits ordinary Ring3 exceptions.
Do not add another FPU mechanism or change kernel quotas to port libm.

Sources: REIST_ARCHITECTURE, roadmap/native completion work paper,
HIGH_ASSURANCE_CORE_CONTRACT, RING3_MATH_RUNTIME_CONTRACT, accepted native
C/C++ contract, cpu/fp_context.asm and actual scheduler FP save/restore/reap.
This is one numeric execution/rounding/state lifecycle slice. Numeric text,
QuickJS/worker/host, browser and further authority remain subsequent slices.
R3.6b remains expressly deferred. No new permission domain is required:
ordinary arithmetic and the existing session's private terminal/IPC rights
are reused; no network, file writing, device or script authority is added.

## Standards and implementation

ISO C11 sections7.6/7.12, IEEE754 binary64 and AMD64 System V LP64 are the
references. Port all44 existing double functions, long lrint and the four
existing fenv functions together. Keep the accepted musl1.2.6 archive pin
d585fd3b613c66151fc3249e8ed44f77020cb5e6c1e635a616d3f9f82460512a,
bounded extraction, exact original source/license bytes and generic numerical
algorithms. Select the actual upstream x86_64/lrint.c (cvtsd2si, LP64 long)
and x86_64/sqrtl.c internal helper. No host libm substitution or approximate
replacement. No errno, complete libm, float/long-double family or universal
correct-rounding claim. Internal sqrtl stays hidden/renamed.

Extend only explicit architecture-selected extraction/compilation entry points
in the existing math builder; preserve the entire i386 default build and
sources. Native artifacts use an explicit SSE2 AMD64 userspace target, no
AVX/XSAVE, MMX code generation, red zone, hosted runtime or kernel FP code.
Keep the accepted kernel/root/service binaries and C/C++ subset exact.
Publish libm.a, math headers, conventional pkg-config metadata and licenses
in the native cpp-sysroot, with independent ELF64/archive/undefined-symbol
admission. Do not silently mix i386 and AMD64 archives or incremental caches.

NativeMath implies NativeCppRuntime, separately from network/GUI profiles.
Build ordinary mathtest.prg from the existing consumer, preserving the legacy
parent/spawn mode under its original profile. The native foreground path
reuses the same numeric/environment vectors; external kernel/root lifecycle
owns crash, timeout, CPU and parent cleanup. No fake process/global statistics.
Use accepted full-width runtime terminal/clock functions and their original
5000ms/4096-operation/1024-byte limits. Preserve root WAIT1000ms, CPU32,
32768-byte stack,192KiB executable window and resource/restart budgets.
Both Windows and Make layouts package mathtest through ordinary Ring3 shell
resolution on signed seven-file media (the accepted six plus mathtest).

## Runtime evidence

Host executes actual selected algorithms/fenv at O0/O2, all44 functions,
four rounding modes, IEEE specials/flags, signed zero/subnormal, large argument
reduction and bounded independent reference samples. LP64 lrint uses positive
and negative ties, values beyond32bits, representable boundaries and invalid
conversion flags, with no out-of-range C conversion used as an oracle.
Windows host long width must be reported honestly; ELF64 compilation and the
actual guest establish the LP64 calling/result boundary.

Real guest checkpoints capture numerical result bytes and raw FP state,
fresh generation defaults, preserved controls/register payload across actual
blocking/scheduler transitions, and empty retired state. Keep the complete
existing shell CPU/frame/IPC/physical-media/no-write proof, ordinary cat/ls
progress and exact generation-bound cleanup. Raw review must reject changed
result, rounding, FP payload, generation, task outcome and incomplete reap.
Successful serial markers alone never establish acceptance.

The finite command workload runs mathtest plus cat in the first session and
mathtest plus ls in the second. Repeated adds a second mathtest in session1;
owner-loss runs only mathtest before parent loss and both cat/ls in session2.
Thus every guest proves both ordinary file consumers and a fresh numeric
generation; every retained CPU/frame/IPC/device predicate applies to all
executed commands. All seven files remain independently admitted. Diagnostic01
demonstrated that duplicating cat/ls/probe in both sessions exceeds the180s
observer lease for the53704-byte consumer. Preserve that failed attempt and
the original lease, ten cases and all numeric/fault/cleanup acceptance gates.

Private zero-default diagnostic selectors may select numeric state, x87 #MF,
invalid-MXCSR #GP, UD2, hang and CPU exhaustion after real numeric work.
No CLI fault authority. Tests must use actual exception vectors/statuses:
16/144,13/141 and6/134. The QEMU TCG profile does not claim #XM delivery;
the separately documented i386 Workstation #XM proof is not a native proof.
No simulated trap or successful fallback if a required exception is absent.

## Scope and finite reservation

Queue allowed_files controls exactly one active visible-main-worktree package.
No kernel edits, nested agents/worktrees/push, unrelated changes or silent
scope expansion. Freeze any evidence-directed correction window before use;
keep all failed attempts and original gates. Initial development reservation:
hosts01..12<=600s, builds01..03<=300s, media01..02<=180s,
diagnostics01..04<=180s each. Compiler calls<=90s, at mostfour workers;
host executables<=30s. Logs under build/codex-agent/r83bs-native-math.

After direct scope/ABI/FP/cleanup/diff review, freeze five one-pass gates:

1. `python test/test_x86_64_math_runtime.py -v` (600s): real numeric/fenv
   O0/O2, LP64 admission, archive/pin/closure, media and raw-proof mutations.
2. `python scripts/verify_x86_64_math_runtime.py --defaults` (600s): complete
   disabled/default projection, original i386 math regressions, retained
   accepted CLI/GUI/network/HTTP/C++ artifacts and kernel no-FP boundary.
3. `python scripts/verify_x86_64_math_runtime.py --package` (600s): one fresh
   build<=300s/media<=180s, independent signed consumer, exact admission,
   undefined-symbol/ISA closure and compiler stack limits.
4. `python scripts/verify_x86_64_math_runtime.py --runtime` (2000s): ten fresh
   sequential guests<=180s each/1800s aggregate; healthy4g, healthy8g,
   rounding-state, x87-fault, mxcsr-fault, crash, hang, cpu, owner-loss,
   repeated. Stop at first failure; no diagnostic substitution.
5. `python scripts/verify_x86_64_math_runtime.py --review` (600s): independent
   complete ten-guest raw replay, all source/tool/media bindings, final scope
   and acceptance seal before outcome-only closure/local clean commit.

After acceptance continue the next inventoried native prerequisite. This
package alone does not complete JavaScript or the native operating system.

## Observed qualification blocker (2026-09-23)

Development diagnostic04 (mxcsr-fault,126.261s including review) completed
both guest sessions but failed the required outcome. Its actual ELF64 contains
`movl $0xffffffff,-0x80(%rbp)` at0x4110e3 followed by `ldmxcsr` at0x4110ea.
The private selection is3 for generation7. The raw terminal receipt is
slot4/generation7/status95/state4, with no fault event; the instruction reached
the explicit failure return. Required acceptance remains #GP13/status141/state3.
The second generation and ordinary cat/ls complete. Diagnostic03 separately
proves actual x87 #MF16/status144 and recovery. Preserve both results.

This is an observed limitation of the pinned QEMU-TCG qualification target,
not permission to simulate #GP, accept status95, remove the case or substitute
an i386/host exception proof. The negative host replay must reject diagnostic04.
No candidate gates or implementation commit may be claimed successful.
Resume requires a reviewed native64 execution target that demonstrably delivers
the invalid-MXCSR exception, with the same isolation/recovery evidence. A new
hardware/accelerator qualification boundary must be resolved explicitly under
AGENTS.md; this package does not silently change its frozen QEMU gates.

Host12 (54.255s) proves rejection of the missing #GP, but exposed incomplete
historical snapshot accounting after the checkpoint capture was narrowed to
the actual blocked transition. Preserve its failure. Reserve host13 only
(<=600s, no build/media/guest retry) to verify consuming the older bound
post-resume snapshot as historical evidence alongside the blocked-state proof.
The platform blocker and original gates remain unchanged.

## Resumed target inventory (2026-09-23)

The renewed continuation retains all prior source changes and failed evidence.
Read-only Windows inventory now reports HypervisorPresent=true; the direct
WHvGetCapability(HypervisorPresent) call succeeds with value1. This establishes
API availability, not native64 qualification. Reserve accelerator-probe01 only:
one paused, diskless, networkless QEMU WHPX initialization, <=15s, hidden process,
monitor status then quit; no guest workload, system setting or gate change.
Its receipt goes under build/codex-agent/r83bs-native-math. A successful probe
only makes a concrete separate hardware qualification proposal possible.

Probe01 timed out after15.033s: the HMP startup input lost its first character
and no clean exit was observed. The process was terminated by its subprocess
timeout. Preserve the failure. Reserve accelerator-probe02 <=15s with the same
paused WHPX machine and JSON QMP control in place of HMP, to distinguish control
transport failure from accelerator initialization. No OS execution or gate.

Probe02 also timed out (15.037s); QMP capabilities and quit were answered,
but piped stdin produced JSON parse errors and clean process exit was absent.
Reserve accelerator-probe03 <=15s: loopback TCP QMP with request/reply sequencing,
paused diskless/networkless machine, explicit whpx,kernel-irqchip=off for this
PIC/PIT inventory. QEMU documents this backend option in whpx-all.c. Require
prelaunch/running=false, CPU enumeration and clean quit; otherwise retain the
blocker. This is initialization inventory only, not a changed acceptance gate.

Probe03 passes in0.348s: WHPX with kernel-irqchip=off, stopped vCPU,
QMP prelaunch/running=false and clean exit0. The user's renewed native64
continuation permits making the hardware-test proposal concrete. Reserve
diagnostic05 only (mxcsr-fault,180s) against the existing exact build01 image
and seven-file medium. A private ignored adapter changes only QEMU accelerator
selection to the initialized WHPX profile; retain every original raw observer,
numeric, vector13/status141, CPU, PIO, frame, cleanup and time predicate.
No production source, privilege or host configuration changes. Stop on failure;
this diagnostic cannot replace a frozen TCG gate or count as package acceptance.
Its result determines whether a separate qualification target is reviewable.

Diagnostic05 failed before guest execution (4.160s): WHPX could not insert the
first high-virtual-address breakpoint while the CPU was still at reset. Media
remained unchanged and both processes closed. QEMU's WHPX backend implements
breakpoints by patching guest memory; TCG's reset-time address hooks are not
portable to that backend. Reserve diagnostic06 <=180s with one byte-verified
temporary breakpoint at the existing identity-mapped long_mode_entry, removed
before installing the unchanged high-address observer. Assert actual RIP,
CS and CR0.PG at that transition; no register/PC injection or kernel edit.
Keep all failed records and frozen acceptance criteria. This remains diagnostic
target assessment and cannot authorize a successful package by itself.

## Concrete hardware qualification scope proposal — pending decision

Diagnostic06 did not hit its initial temporary breakpoint. A read-only QMP
register capture instead found the CPU in the native scheduler idle path,
RIP0xffffffff8010e946, CS8, CR0.PG set, CR3=0x11f000. The expected startup
instruction bytes had matched before continue. Initial lifecycle observations
were therefore missing; the owned VM was stopped through QMP at91.219s.
No successful containment or hardware fault proof follows from this boot.
VMware Workstation is also installed and reports zero running VMs, but the
existing containment script is an i386 serial-marker test and does not supply
the required native64 raw observer.

The concrete next scope is a separate, explicit hardware qualification bootstrap
and observer for the demonstrated WHPX backend, using the same numeric consumer
and lifecycle predicates. Establish a deterministic observation boundary before
the first native task, verify the actual startup bytes/state, then capture the
same CPU/frame/IPC/PIO/FP/reap evidence and genuine invalid-MXCSR #GP. Any bootstrap
instrumentation must be confined to an opt-in qualification image with a complete
disabled/default projection; existing accepted images and their pins stay intact.
No production privilege, driver or new application authority is proposed.

This requires a reviewed change to the current allowed_files and the frozen
qualification-image/target binding: the current package allows no kernel-source
edits and requires the old kernel binary exactly. Do not make that expansion
silently. Proposed additional source scope is arch/x86_64/boot/entry.asm and only
the already allowed bootstrap build/observer/tests; any further need stops for
review. Before implementation, define the one-shot fail-closed bootstrap behavior,
its finite timeout and gate list. Initially reserve at most2 host/build checks
(600s/300s respectively) and2 hardware diagnostic guests (180s each), separately
numbered after the preserved history. These reservations are proposed, not spent.
Preserve all TCG failures and do not claim that TCG implements the missing fault.
Acceptance still requires the actual exception and all original isolation and
recovery properties; the current package remains unaccepted until this decision
and a successful complete qualification. No installation, host setting change,
VMware launch, gate substitution or kernel edit has been authorized by this text.

## Authorized hardware correction window

The user renewed "mach weiter bis alles fertig ist" after the explicit scope
question and concrete proposal. This authorizes the described qualification
bootstrap and entry.asm scope addition, not relaxed fault or isolation checks.
The active transaction continues with its existing owned edits and failures.
Reserve host14..15<=600s, build02..03<=300s and diagnostic07..08<=180s.
No spent counter resets and no unchanged retries.

NativeMathHardware is a separate explicit switch implying NativeMath. Only the
bootstrap entry object receives REIST_NATIVE_MATH_HARDWARE; default code must
project exactly to the prior source and reproduce accepted artifacts. Before
any Ring3 execution, after exception/FP initialization, the qualification gate
publishes ready=1 and polls release for at most1000000000 PAUSE iterations.
Only release=1 succeeds; another nonzero value or counter exhaustion records
ready=-1 and enters the existing CLI/HLT safe halt. Clear both cells before
continuing. This is a qualification-only pre-task wait, not a userspace path.
Host startup is bounded by10s inside the180s guest lease: loopback QMP starts
the paused VM, captures the fixed physical gate cells (<=128 reads), stops at
ready=1 and records the stopped cells. GDB verifies actual gate RIP/CR0/CR3,
installs the complete observer, records its sole release-cell write and resumes.
No PC/register injection; no existing kernel budget, restart or application right
changes. Use breakpoint always-inserted=off on WHPX so stopped raw observations
see restored instruction bytes. Keep independent physical-memory equivalence.
Failure of any original raw predicate remains a failed diagnostic.

The five gate commands, numeric/fault outcomes, ten fresh cases and180s/1800s
bounds are retained. Hardware qualification must additionally bind the opt-in
image, bootstrap transcript, WHPX accelerator and unchanged ordinary artifacts.
The old TCG image and invalid-MXCSR failure remain negative evidence. Do not
freeze or claim acceptance until the hardware observer has real diagnostic proof.

Build02 passed in21.859s; host14 passed both disabled/default projection and
hardware observer construction in3.934s. Diagnostic07 failed before QMP connected
(0.5s connection timeout, total3.944s); permit bounded connection timeouts within
the existing10s startup lease. Diagnostic08 then reached the actual pre-task gate,
captured ready/release=(1,0), stopped, installed the observer and recorded release.
Its startup transcript passed in0.524s, but resume failed because the TCG observer
requests more simultaneous hardware breakpoints than WHPX provides (total4.473s).
Neither diagnostic is accepted as a runtime or containment proof.

Reserve diagnostic09..10<=180s for the evidence-directed observer transport
correction, preserving07/08 and all earlier failures. Host15 remains reserved.
Use software execution breakpoints for the existing observation sites on WHPX,
with always-inserted=off so actual stopped memory remains unpatched. Keep every
callback, actual return-target check, raw physical-memory equivalence comparison
and original lifecycle predicate. No register/PC injection, simulated fault or
removed observation is allowed. A memory mismatch remains a failed diagnostic.

Diagnostic09 failed in4.839s after the gate release: software breakpoint fallback
reached exception_fatal and WHPX reported unexpected VP exit code4; no original
runtime predicate passed. Diagnostic10 explicitly forced the remote Z0 packet
and failed in4.433s with "Enabled packet Z0 (software-breakpoint) not recognized
by stub". This narrows the transport blocker: the installed backend rejects the
required remote execution-breakpoint protocol. Diagnostic08's generic hardware
breakpoint error alone did not establish an actual four-register capacity limit.
Do not retry this backend unchanged, enable GDB's memory-patching fallback or
reinterpret the kernel fatal as the required application #GP.

Read-only executable inventory found only the pinned Program Files QEMU on PATH
and no alternate in the checked workspace/MSYS binary locations. The approved
entry-only qualification bootstrap is working but cannot supply the missing
debugger backend. Acceptance now needs a reviewed isolated verifier toolchain
with actual WHPX Z0/Z1 execution-breakpoint and required watchpoint support, or
another native hardware observer with equivalent complete raw evidence. This
is beyond the approved entry.asm/bootstrap-only correction. No host installation,
emulator source modification, external download or VMware launch is performed.
Preserve the candidate uncommitted and unaccepted; reserve no unchanged guests.
Finish host15 with the retained transport-failure regression and scope review.

Host15 passed11/12 tests; its new retained-transport test looked only in the
observer log, whereas GDB's redirected error is in frame-trace.log (66.706s).
Correct the read-only assertion to inspect both retained logs. Reserve host16
<=600s for this one affected regression only; no guest or full-suite repetition.

Host16 passed the corrected retained-transport regression in0.142s. Together
with host15's other11 passing tests this resolves the host assertion failure;
it does not qualify WHPX. All owned QEMU/GDB processes have exited.

## Proposed verifier-toolchain scope (requires decision)

Permit an isolated portable QEMU verifier under the ignored BS evidence directory,
with exact upstream source/release provenance and SHA256 binding recorded before
execution. Do not replace Program Files binaries, change PATH/system settings,
install services, use public guest networking, launch VMware or modify REIST's
kernel/application behavior. First inspect the accelerator's actual debugger
registration and support for execution breakpoints and the pending-state hardware
watchpoint. Unsupported capabilities stop before any acceptance run. If rebuilding
QEMU is necessary, freeze its exact source changes and finite build reservation
before executing the build; do not silently patch fault emulation or fabricate
MXCSR exceptions. Any further repository source scope needs a separate review.

Initial proposed reservation after approval: at most2 capability probes<=20s
each, one hardware diagnostic<=180s and one targeted host check<=600s. Preserve
the complete old backend/failed-guest bindings. The five acceptance commands,
ten real guests and all numeric, fault, isolation and recovery predicates remain
required. A successful capability probe is not runtime acceptance.

## Verifier-toolchain authorization

The user's renewed "mach weiter bis alles fertig ist" after the concrete
portable-toolchain scope question approves that proposal. Continue inside the
ignored BS evidence directory without system installation or replacement.
Reserve capability probes04..05<=20s, diagnostic11<=180s and host17<=600s;
earlier probes01..03 and diagnostics01..10 stay spent. First inspect the exact
installed upstream revision e470268ff4 and available local build dependencies.
Record downloaded source URLs, exact bytes and SHA256 before any build or use.
Freeze a separate finite compiler reservation only after the source inventory
identifies an actual correction. No changes to guest exception semantics.

Source inventory: installed revision e470268ff4 is not retrievable from the
official GitHub mirror (404), so do not claim its exact source provenance.
The pinned official v9.2.0 tag resolves to ae35f033b874c627d81d51070187fbf55f0bf1a7;
archive SHA256 40b36ca796acf15c565c52c512977936f431df0f2f6ce32cd443579f9af0e2d3.
Its WHPX implementation already consumes CPU execution breakpoints but has no
GDB insert/remove registration. The actual generated BS observer contains no
BP_WATCHPOINT/PendingWatch construction: the proposed watchpoint requirement was
an inventory error, not an acceptance predicate. Preserve its existing execution
hooks and actual return checks; do not add a substitute memory watchpoint.

Freeze portable compiler window01: at most3 configurations<=180s and2 compiler
invocations<=1200s each, jobs4, x86_64-softmmu only, no install. Patch only
target/i386/whpx/whpx-accel-ops.c to register debugger support and bounded single-
CPU execution-breakpoint insert/remove/remove-all using existing CPU breakpoint
APIs. Reject watchpoints, unsupported lengths and multiple CPUs. No changes to
WHPX execution, instruction emulation, exception dispatch or register semantics.
Snapshot exact patch/tool/dependency hashes before compilation. All inputs stay
under portable-qemu; MSYS package hashes are checked against the downloaded
official-mirror database. TLS verification remains enabled; the existing local
MSYS CA bundle resolves the alternate official mirror's issuer chain.

Portable configure01/02/03 failed before compilation (4.455/4.269/6.863s):
missing pinned subprojects, absent executable in the old Python312 directory,
then missing distlib in Python313. Resolve these build prerequisites locally:
the three wrap-pinned subprojects are hash-recorded, Python313 is present and
distlib is added only to the isolated Python search path. Reserve configurations
04..06<=180s with unchanged compiler01..02<=1200s budgets. No guest spent.

Configure04 resolved the dependencies but failed in17.014s at QEMU9.2's hardcoded
POSIX pyvenv/bin/meson path. The selected native Windows Python creates
pyvenv/Scripts/meson.exe. Add the exact build-only configure path adaptation to
the frozen toolchain patch; no generated guest or emulator behavior changes.

Configure05 reached Meson then rejected the POSIX default install prefix (15.169s);
configure06 uses an unused absolute workspace prefix and reaches final test
declarations, then reports missing diff (51.191s). Use the existing Git diff.exe
only in the child tool PATH. Reserve configure07..09<=180s; compiler reservations
remain unspent. No install or runtime relaxation follows from these prerequisites.

Configure07 passed55.959s. Compiler01 failed14.127s: native Windows Meson
full_path() uses backslashes, while trace/meson.build splits only on '/'; it
generated absolute-path-derived trace header names instead of the QAPI basename.
Add a build-only separator normalization before that basename extraction,
preserving every trace event and function. Freeze this third source-file delta
before configure08 and compiler02. Initial audit found exactly the prior two
intended changes across10163 upstream files; repeat for the three-file delta.

Configure08 passed55.679s; compiler02 passed the corrected trace names but failed
43.015s on unescaped Windows backslashes in generated C #line filenames (\u).
Normalize only Event.filename and out_filename in scripts/tracetool/__init__.py
to forward slashes before emission. This fourth source delta changes compiler
diagnostic paths only. Reserve compiler03..04<=1200s/jobs4 after the complete
four-file source audit; all prior results retained, no guest spent.

Compiler03 failed26.291s: backend/log.py applies os.path.relpath after the earlier
normalization, restoring backslashes in #line. Normalize at that actual emission
site; remove the now redundant Event.filename normalization, retain out_filename
normalization. The resulting five-file toolchain delta still changes only debugger
registration and build/diagnostic paths. Use the reserved compiler04 after audit.

Compiler04 progressed through748 actions then failed154.138s because the
auto-enabled optional D-Bus display generator did not create its Windows output.
The headless verifier uses -display none and needs no D-Bus display. Disable that
optional backend in configuration09, retaining all guest devices and WHPX.
Reserve compiler05..06<=1200s/jobs4, audit the same five source deltas and new
configuration. No protocol, guest instruction or acceptance predicate changes.

Configure09 passed61.113s; compiler05 passed348.713s. The new executable hash is
2aa094093f5a9429fe5d88a36fc27dd6524713009c6a8c04b1565064bfbaf2b9;12 local
DLLs and80 firmware inputs are bound. Probe04 failed11.668s before QMP because
running directly beside Meson's qemu-bundle directory triggers QEMU's Windows
relocation path error. Package the identical executable/DLL bytes in a separate
portable runtime directory, pass the exact firmware directory with -L and use
reserved probe05. Preserve binding01 and probe04; no emulator source correction
or unchanged backend retry is involved.

Probe05 booted the portable runtime to the expected pre-task cells in0.520s,
then failed1.090s because the new probe hardcoded a nonexistent MSYS GDB path.
Use the existing PATH-resolved WinLibs GDB already used by all accepted guests,
record its hash and reserve probe06<=20s for the corrected launcher. No full
hardware diagnostic or host17 has been spent yet.

Probe06 hit the first actual Z0 breakpoint and verified its original8 code bytes,
then timed out18.151s after replacing it with Z1 at the same address. Do not claim
Z1/repeated-stop support. The BS hardware adapter explicitly uses Z0 execution
breakpoints at all sites and contains no hbreak/watchpoint commands. Reserve
probe07<=20s to exercise two distinct consecutive Z0 instruction sites, including
actual RIP and independent stopped physical bytes. The full diagnostic must still
prove all recurring callbacks and actual RET transitions; this probe cannot replace
that proof. No emulator source or guest-semantic change is made for this probe.

Probe07 passed1.484s with two actual Z0 instruction stops and independent physical
code equivalence. Host17 passed8.980s (portable binding/tamper rejection, complete
observer construction and default projection). Diagnostic11 reached the original
boot callback but failed its exact4096-byte probe-page predicate (5.791s).
Reserve diagnostic12<=180s solely to capture those actual4096 bytes before the
unchanged assertion, plus host18<=600s for the evidence-directed correction.
No byte normalization or relaxed pristine-code predicate is authorized.

Diagnostic12 failed6.078s and captured exactly seven differing bytes: the seven
RET probe sites contain0xf1 rather than0xc3; all4089 padding bytes match. The ELF
input page is independently pristine. This is debugger-byte contamination, not
a permitted guest invariant change. Reserve probe08<=20s to test same-site Z0
recurrence and adjacent probe-page restoration before any Ring3 execution; keep
the whole runtime diagnostic stopped pending this concrete transport issue.

Probe08 restores all seven adjacent probe bytes at its first stop, then times out
18.087s on same-site Z0 recurrence. Source review identifies a candidate WHPX
bookkeeping defect: running_cpus is incremented before an early halted-CPU return
that lacks the matching decrement/last-stop cleanup. Do not fix this speculatively.
Reserve compiler06<=1200s/jobs4 for bounded host-only debug logging (first32
debug exits: running count, step state and guest RIP) in whpx-all.c, plus probe09
<=20s and diagnostic13<=180s. This sixth source delta observes debugger state
without changing guest execution, exception delivery or predicates. Preserve
the working compiler05 executable/DLLs and binding02 in runtime/ unchanged.

Compiler06 passed3.490s. Probe09 retained the same-site timeout18.071s and logged
only its first debug exit. Diagnostic13 failed4.959s and logged running_cpus=4
on a single-CPU guest, confirming the halted-return imbalance. Separate source
inventory establishes that WHPX registers no gdbstub_supported_sstep_flags;
the shared stub masks SSTEP_ENABLE to0, explaining why requested stepping never
produces a second debug exit despite WHPX's existing TF implementation.

Freeze two precise debugger-lifecycle corrections in the already scoped whpx-all.c:
balance running_cpus and run last-stop cleanup on the demonstrated halted return;
register exactly SSTEP_ENABLE (no unsupported NOIRQ/NOTIMER promises). Preserve
the existing physical instruction execution and exception handling. Reserve
compiler07..08<=1200s/jobs4, probe10<=20s (same-site recurrence and restored adjacent
bytes) and diagnostic14<=180s. Host18 remains unspent. Retain all old binaries,
bindings and negative evidence; the complete original raw predicates still apply.

Compiler07 passed3.236s; probe10 passed2.241s including same-site Z0 recurrence
and adjacent code restoration. Diagnostic14 passed the pristine probe-page boot
predicate and showed running_cpus=1, then failed4.721s at the observer's literal
TCG qqemu.sstep=0x7 transport binding. WHPX correctly advertises only0x1.
Bind the explicit hardware adapter to exactly0x1; retain TCG's0x7 unchanged.
The accepted return observer executes continue to a temporary actual target
breakpoint, not stepi. Preserve its IF=0, exact RET byte, actual target hit,
RSP+8, complete register/flags/CR3 preservation, callback and raw CPU history
checks. Do not advertise IRQ/timer suppression unsupported by WHPX.
Reserve diagnostic15<=180s; use unspent host18<=600s for the precise adapter
construction/default/binding regression before that guest. This changes only
the backend-specific protocol binding, not a guest isolation acceptance predicate.

Host18 passed8.721s. Diagnostic15 passed the boot page and backend-mode binding,
then failed5.246s at the exact caller predicate for native_session_probe_return_site64.
Reserve diagnostic16<=180s to capture the actual caller/RSP/instruction/expected
helper on that failure, retaining the original equality assertion; host19<=600s
is reserved for its evidence-directed correction. No inferred return is accepted.

Diagnostic16 failed4.352s and identifies the mismatch precisely: QEMU logs actual
RIP at start_site+0, while GDB's software-breakpoint interpretation reports the
adjacent return_site one byte earlier. The unchanged stack/call bytes resolve to
native_session_probe_start64, not return64. Therefore the temporary SW conversion
is unsuitable for adjacent one-byte probe sites. Restore the original observer's
hardware execution-breakpoint types for the portable backend, now that Z1 and
single-stepping are registered; retain the original breakpoint locations and all
PC/caller assertions. No manual RIP adjustment or register write is permitted.
Reserve probe11<=20s for adjacent Z1 sites and same-site recurrence, followed by
diagnostic17<=180s. No QEMU binary/source change; host19 remains unspent.

Probe11 passed0.747s and host19 passed7.375s. Diagnostic17 passed171.630s
(guest161.053s): the full unchanged numeric, actual #GP13/status141, CPU,
RET, IPC, PIO, generation, FP scrub and frame recovery predicates passed.
Raw evidence covers20 tasks,7143 probe steps and2182 snapshots. This is a
development diagnosis, not the ten-guest acceptance matrix.

Freeze the final qualification integration: retain the ordinary NativeMath
build and signed seven-file medium; additionally build NativeMathHardware and
require identical userspace catalogs, consumers, archive exports and stack
bounds. All ten fresh180s guests use portable-qemu/binary-binding04.json
(QEMU SHA256 c03916206e76433cbe29bd3e2f2a83b053e3b83b6e5699c8fffcbd5bb1a0eb14).
The complete10163-file source audit, six precise source deltas, configuration09,
compiler07, twelve runtime DLLs and eighty firmware inputs remain hash-bound.
Reproduction inputs and patches are retained in portable-qemu alongside
compile-freeze07.json; no system installation or host PATH changes are required.
Preserve original hardware breakpoint types and actual RET/CPU predicates.
Replay QMP command order, physical cells, release registers, pristine4096-byte
probe page and a new raw16-byte cleared-gate witness for every acceptance guest.
Reserve host20<=600s solely for the hardware raw replay and bootstrap mutation
test before candidate freeze. No further diagnostic guest is reserved.
The five frozen gate commands and600/600/600/2000/600s limits remain unchanged.

Host20 failed0.154s before test execution: incorrect unittest class name
MathRuntimeTests. The actual class is NativeMathRuntime. Preserve that receipt;
reserve host21<=600s for the identical intended test with its correct name.

Host21 passed15.966s: complete hardware MXCSR raw replay, physical-cell address
mutation rejection and mandatory cleared-cell evidence for fresh qualification.
Candidate01 may now freeze the reviewed source/scope/tool and diagnostic inputs;
no implementation acceptance is claimed until all five gates pass.

Candidate01: gate1 passed110.714s (14 tests), gate2 passed29.300s; gate3
failed101.569s after both builds and signed media succeeded. No guest gate ran.
Inventory proves identical seven consumer files and archive; both stack totals
are4056 bytes. Compiler .su keys embed different build directories, so comparing
the raw dictionaries as though paths were identical is erroneous. Preserve all
raw keys and compare only after removing each exact bound program-directory
prefix (with Windows separators normalized). Function paths, line numbers,
names, sizes, uniqueness, static-frame bounds and aggregate remain checked.
Reserve host22<=600s for this specific regression, including a size mutation.
Candidate02 then freezes the corrected verifier and retained candidate01 records;
the same five gates run once with their unchanged limits and first-failure stop.

Host22 passed0.323s: exact source-root correspondence and changed-frame rejection.

Candidate02: gate1 passed99.154s (15 tests), gate2 passed22.774s, gate3
failed99.767s. Both builds/media and the corrected stack correspondence passed;
the additional raw archive equality detected DWARF source-directory differences.
archive-diagnosis01 retains a hash-bound objcopy inspection: --strip-debug copies
are byte-identical130138-byte relocatable archives, SHA256
80e8304260644bc60d06a8e0b74996846fdb39673d41fc3e0916f3306a1cee75.
Keep both complete original archive hashes, exports, dependencies and ISA checks.
Compare code/data/relocations through temporary --strip-debug copies using the
explicitly hash-bound existing objcopy, without modifying or replacing artifacts.
No numeric instruction or guest acceptance predicate changes. Reserve host23
<=600s for the actual two-archive debug-directory regression. Candidate03 freezes
this correction and both failed candidate records; same five gates and limits.

Host23 passed1.949s: actual differing raw archives have identical retained
relocatable contents, exports, symbol dependencies and admitted ISA.

Candidate03: gates1/2/3 passed109.06/24.58/100.61s. The 4GiB/8GiB guests
passed170.247/163.135s; rounding-state completed166.17s but raw history rejected
13 checkpoints instead of10. Generation7 has duplicate unchanged witnesses
after rounding indices0,1,3; generation17 has the expected five. Both have four
actual blocked FP captures and normal status0. Do not deduplicate or weaken the
exact history predicate. Reserve diagnostic18<=180s to record bounded actual
checkpoint RIP/RSP/flags/caller and witness values at the existing stops, keeping
all original assertions. Use the same hardware image and binding04; no QEMU or
guest modification, no unchanged retry. Reserve host24<=600s for the resulting
evidence-directed observer regression before any new qualification candidate.

Diagnostic18 failed172.200s and proves one duplicate with identical RIP0x41002d,
RSP0x40fed8, caller0x41106b and witness, but flags0x346 rather than0x246 (TF).
The portable backend's execution stops already require Z1 for the original
kernel probes; MathCheckpoint still used GDB's default software type. Select
explicit BP_HARDWARE_BREAKPOINT for that one proven problematic checkpoint in
the portable adapter only. Preserve every stop and exact count; no filtering,
deduplication, CPU writes, guest change or QEMU change. Host24 checks constructor
binding and continued rejection of diagnostic18. Reserve diagnostic19<=180s for
the corrected rounding observer with all original predicates and raw debug data.

Host24 passed15.674s. Diagnostic19 passed169.042s (guest157.549s): exactly ten
checkpoints/eight blocked FP captures across two generations, complete original
CPU/RET/IPC/PIO/math/lifecycle predicates and bootstrap raw evidence. No duplicate
filter was added. Candidate04 binds diagnostics18/19 and failed candidate03 and
adds the successful rounding raw replay to the frozen host suite. Execute the
same five gates once, with the original per-gate/guest limits and first-failure
stop. No further development host or guest is reserved at this point.

Candidate04: gates1/2/3 passed123.33/20.23/105.34s; healthy4g completed158.55s
but generation17's initial checkpoint repeated with flags0x312 versus0x212,
identical RIP/RSP/caller/witness. Thus Z1 alone is insufficient; diagnostic19
was not a general transport qualification. Preserve candidate04 and exact
duplicate rejection. Use previously unspent compiler08<=1200s/jobs4 solely for
bounded WHPX host logging around the concrete numeric checkpoint: incoming
cached PC/flags, native exit PC/flags/reason and debugger/exclusive step state,
at most64 records. No instruction, exception or guest-state modification.
Reserve diagnostic20<=180s with that separately bound logging binary/runtime04;
retain runtime03/binding04 and compiler07 unchanged. No next acceptance candidate
until the resulting concrete debugger-lifecycle defect is addressed.

Compiler08 passed3.387s; binding05 SHA256
8e41018a5ce3ae3e93163ac5d0d9d560e06e6747c3df2cb6177369a82b44e33d.
Diagnostic20 records WHPX InterruptState failures c0350015 while debugger
step=1/exclusive=0. Native execution then enters the IRQ handler and later
reaches the same checkpoint with TF still set. Source review shows pre_run
injects pending IRQs before configuring single-step interrupt shadow; both
configuration HRESULTs are ignored. This explains the duplicate raw stops.
Freeze the precise correction in the existing whpx-all.c delta: defer pre_run
IRQ injection during debugger single-step, as already done for exclusive
breakpoint stepping; preserve pending requests for the next normal run.
Check both single-step configuration HRESULTs and use the existing fatal
verifier-error cleanup on failure, before further execution. Do not change
architectural guest exceptions, instruction emulation or any observer predicate.
Reserve compiler09<=1200s/jobs4, diagnostics21 (healthy4g) and22 (rounding-state)
<=180s each, and host25<=600s for the bound tool/observer regression. Retain all
old deployments and diagnostics. No unmodified retry or duplicate filtering.

Diagnostic20 failed162.741s with the retained duplicate history. Compiler09
passed3.129s; binding06 SHA256
9e4a08d0c13c77cb7bed0cfecca1b3dad1a85841a0f0f5944d21d28970920bfb,
runtime05, compile-freeze09 and the same twelve DLLs/eighty firmware files.
Diagnostics21/22 passed162.156/170.850s (guests152.560/160.435s), with all
original predicates, exact checkpoint counts, no InterruptState failures and
no TF at any numeric checkpoint. Bind this tool for candidate05, preserving
all four failed candidates. Additionally reject any WHPX verifier-error log
and require bounded checkpoint CPU witnesses to match the raw numeric snapshot
and carry no TF. Host25 replays both corrected guests and rejects diagnostic20
under that new verifier-error rule before the unchanged five-gate transaction.

Host25 passed40.589s. Freeze candidate05 with binding06/compile-freeze09,
nineteen host tests and the same five gate commands/limits and ten fresh guests.

Candidate05: gates1/2/3 passed137.08/21.55/110.50s. Five guests passed
(4GiB128.57s,8GiB161.09s,rounding150.97s,x87153.66s,MXCSR156.08s).
Crash stopped177.253s at the unchanged feeder deadline: actual #UD was reaped,
cat completed, the second math generation passed and was reaped; ls had started.
No duplicate/TF/WHPX error appeared. Capture metrics retain QEMU72.09 CPU seconds
and debugger123.08 CPU seconds, versus60.33/107.88 in the completed MXCSR case.
Reserve probe12<=20s, before Ring3 with release cell0, solely to compare exact
register values and bounded timings of GDB parse_and_eval versus the documented
Frame.read_register interface. All guest limits, raw register/RET checks and
event counts remain frozen; no guest retry before an evidence-directed change.
Reference: https://sourceware.org/gdb/current/onlinedocs/gdb.html/Frames-In-Python.html

Probe12 passed0.840s, exact agreement for26 registers/3328 reads per method:
expression0.034659s versus direct register0.021922s. Replace only reg(n)'s
expression parser with selected_frame().read_register(n) in the portable
observer, retaining fresh reads at every stop and the exact64-bit mask. Never
cache values across execution. Reserve host26<=600s for observer construction
and the bound comparison receipt; diagnostic23<=180s captures cProfile for
the first crash session and intentionally quits71 at its finish hook, before
second-session execution. This profiling-only stop is not an accepted guest.
Use its bounded profile to identify further necessary host overhead reductions;
do not widen deadlines, remove events or weaken any raw assertion.

Host26 passed3.060s. Diagnostic23 intentionally stopped70.325s at the first
finish hook; its profile has5,681,168 calls/65.951s, of which gdb.execute consumes
39.787s and inferior.read_memory13.898s. It is not a complete accepted guest.
The adapter still forces always-inserted off from the earlier broken WHPX
bookkeeping diagnostics, causing breakpoint registration traffic at every stop.
The accepted original observer uses on. Reserve probe13<=20s to test on with
binding06 and the corrected stop cleanup: adjacent probe bytes and the current
instruction must remain pristine after two real stops, and QMP must agree.
Only if it passes restore on for the portable adapter, then reserve diagnostic24
<=180s for a complete crash run with direct register reads, no profiler and all
original predicates. Retain every event and exact RET retirement check.
Reference: https://sourceware.org/gdb/current/onlinedocs/gdb.html/Set-Breaks.html

Probe13 passed0.898s with pristine current/adjacent instructions and physical
QMP agreement. Diagnostic24 then passed101.968s (guest94.255s), including the
actual #UD, both sessions,20 tasks,7147 RET probes,2183 snapshots and complete
original cleanup predicates. Default qualification never enables cProfile or
the intentional first-session stop. Reserve host27<=600s for the full crash
replay, strict bootstrap/TF/error checks, register comparison and default observer
construction. Candidate06 binds all prior candidates/diagnostics and restores
registered breakpoint persistence only for the corrected portable backend.
The same five gates and ten fresh180s guests remain mandatory.

Host27 passed12.969s. Candidate06 includes twenty host tests and binds the full
accelerator-probe folders as well as their receipts, including register timing
and pristine instruction observations. No further diagnostic reservation.

Candidate06: gates1/2/3 passed135.95/20.24/110.57s and eight fresh guests
passed (4GiB104.30s,8GiB105.38s,rounding93.98s,x8795.35s,MXCSR94.52s,
crash94.20s,hang94.82s,CPU95.08s). Owner-loss failed35.182s at the second
root's exact image predicate. Retained QMP ram-0029.bin begins with the root
code page; comparison to ram-0028.bin's page16 finds exactly one changed byte:
offset45/address0x41002d is0x55 instead of0xcc, matching the math checkpoint's
original PUSH RBP instruction. The WHPX breakpoint record stores virtual
address/original byte only, and restores through the current CR3 after switching
away from the cancelled math task. Never normalize the corrupted image.

The isolated verifier correction needs physical address/attributes/address-space
binding in its breakpoint record. Explicitly expand the portable source audit
from six to seven files by adding target/i386/whpx/whpx-internal.h; repository
allowed_files and guest authority remain unchanged. Bind each insertion to the
translated physical RAM address using the existing QEMU debug translation and
address-space primitives. Restore and step/rearm that bound byte, never resolve
the original VA through a different CR3. Validate the current byte before a
write: preserve a byte superseded by guest cleanup, and fail closed on actual
memory-operation errors or inconsistent rearming. Retain all previous tool
deployments. Reserve compiler10<=1200s/jobs4, diagnostic25 owner-loss<=180s and
host28<=600s for the concrete byte-corruption regression and complete corrected
guest replay. No gate retry before that proof; all acceptance predicates remain.

Compiler10 failed2.436s: missing declaration for cpu_synchronize_state and opaque
CPUAddressSpace internals. Use sysemu/hw_accel.h and cpu_get_address_space(),
the existing public QEMU interfaces. The complete seven-file audit finished
without source changes during the failed compile; preserve both receipts.
Reserve compiler11<=1200s/jobs4 for that precise compile correction; diagnostic25
and host28 remain unspent. No new guest or authority scope.

Compiler11 passed4.138s; binding07/runtime06 pins that seven-file correction.
Diagnostic25 completed both sessions102.3865s with pristine root images, but
offline validation failed: generation7 has one checkpoint before cancellation,
generation14 has none although it prints the expected success output. Do not
relax the five-checkpoint/four-block requirement for the second session.
Reserve compiler12<=1200s/jobs4 and diagnostic26 owner-loss<=180s for bounded
logging of math-breakpoint binding/restore physical addresses, CR3 and bytes
(at most96 records). This is a diagnostic-only tool change, no guest change.
Host28 remains unspent until a complete corrected replay exists. Preserve25
as rejected evidence; do not restart qualification yet.

Compiler12 passed3.260s; diagnostic26 failed the same strict count105.145s.
Its bounded log proves the registered VA is rebound from math physical
0x10007002d to shell physical0x10000702d on resume. Restoring by physical
address fixes corruption but rebinding on every stop loses process-local probes.
Reserve compiler13<=1200s/jobs4 and diagnostic27 owner-loss<=180s: preserve
physical binding for each debugger registration across stops and unrelated
registration changes; invalidate it explicitly on removal before reuse.
Removal must fail if the patch has not been restored. No guest code, count,
deadline or error-predicate changes. Host28 still requires a complete proof.

Compiler13 passed3.502s. Binding09/runtime08 pins the seven-file tool correction
(EXE3a15d61116678df35c96681e68160f2a27d78aa012d8dd9cb04eec88d70760a2).
Diagnostic27 owner-loss passed106.840s with both complete sessions and all five
checkpoints/four blocked FP snapshots for the recreated generation. Host28
passed22.774s: exact prior one-byte corruption, rejection of incomplete25/26,
complete27 replay, bootstrap checks and current tool/observer binding.
Candidate07 retains all historical failures and binds their raw regression
inputs. Reserve the unchanged five one-pass gates and ten fresh180s guests,
1800s aggregate. No new authority, scope expansion or acceptance relaxation.
