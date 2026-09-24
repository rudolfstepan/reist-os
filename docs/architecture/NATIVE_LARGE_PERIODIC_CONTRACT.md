# Periodic large service import â€” R8.3cd

## Authority, scope and compatibility

User continued immediately after the concrete approval question for proposal
0b05b708. Implement exactly that proposal, including all exclusions. Existing
System V AMD64/ELF64 image conventions and append-only REIST task ABI apply;
this is resource accounting, not a real-time guarantee. NativeLargePeriodic is
explicit, defaults off, requires large-image, wide, task-pool and service CPU.
No new privileged caller, display quota, device or application service rights.

CREATE-v8 uses the existing80-byte v6 layout with version8 and RNPGv3. Parent
must have100 period ticks and1..32 samples; child samples1..parent samples,
period1000ms, reserved/flags zero. Validate the entire80-byte request before
copying it. v6 remains periodic RNPGv2, v7 remains lifetime RNPGv3. Failed
admission publishes no task, plan, frames or attempt charge. Existing v3 import
preflight, copy, validation, argument-tail and cleanup sizes remain exact.
Eight task slots,1MiB image,32KiB stack, heap/caps/endpoints and restart bounds
remain unchanged. Ring0 only composes existing bounded mechanisms.

## Preserved work and finite execution

Clean implementation base follows this contract commit. CB nine-file candidate
is preserved in stash0dd64c8ed7c75b1657b396544462f41a3a40ceb7 and byte-verified
services-before-periodic01 archive SHA256
eff172ae42f2b5c489582d13de9d775e5ab79e09d55e827f5f4bf868f016294c.
CB spent11/24 hosts,3/4 builds,zero media/diagnostics/gates; never reset them.

CD reserves20 development host invocations each180s, four builds each300s
(including preimplementation disabled baseline), six diagnostics each360s.
Every invocation uses a new numbered receipt/log under
build/codex-agent/r83cd-large-periodic; preserve failed attempts. Freeze any
evidence-directed additional reservation before execution, never retry unchanged.

## Frozen acceptance gates

Run each gate once in order for a frozen candidate; stop at first failure.
Source/tool/package binding and full changed-path scope review are mandatory.

1. `python test/test_x86_64_large_periodic.py -v`,180s. Actual assembly admission,
   attenuation, whole-request preflight/snapshot, v3 dispatch, periodic plan
   publication and SDK layout. Enabled/disabled v6/v7/v8 behavior, malformed
   fields, invalid pointers, under-budget/lifetime parents, stale identities;
   rejection leaves state unchanged. Carry forward unchanged mapping/rollback
   tests only with exact source/tool/evidence binding.
2. `python scripts/verify_x86_64_large_periodic.py --defaults`,300s. Disabled
   NativeLargeImage output bytes equal the preimplementation baseline, including
   objects; validate explicit selectors and preserve legacy behavior.
3. `python scripts/verify_x86_64_large_periodic.py --package`,600s. Enabled
   reference build, artifact/layout/profile validation and immutable hash manifest.
4. `python scripts/verify_x86_64_large_periodic.py --runtime`,2400s. Six fresh
   guests, each360s, aggregate2160s: normal cross-period high-address execution
   with total samples above32; same-window exhaustion; cancel/reap; partial OOM
   rollback; high RX write denial; guard/stack violation. Normal and lifecycle
   cases recreate a distinct generation; every case preserves an independent
   peer. Existing finite waits/restarts remain bounded, never loosened.
5. `python scripts/verify_x86_64_large_periodic.py --review`,1200s. Independently
   replay complete raw request/task/plan/PTE/frame/owner/CPU evidence for all
   cases, exact cleanup and no stale authority, plus corruption rejection and
   frozen provenance. Success markers alone are insufficient.

After all gates and direct diff review, commit locally, restore CB exactly and
continue its unchanged desktop acceptance. This prerequisite is not a VMware
desktop or native64 completion claim. Deferred R3.6b remains deferred.

## Development evidence and bounded correction window

Hosts01..04 spent.01 confirmed missing v8;02 passed admission/attenuation;
03 exposed unaligned exported arrays in the host fixture at O2 (GDB movdqa);
04 passed both tests at O0/O2 after aligning those test buffers. No production
alignment change. Build01 baseline56 artifacts6.531s;02 selected6.166s;
03 disabled6.087s: all executable images exact, four objects differ only in
source debug coordinates. Preserve these receipts; add branch-exit line anchors.
Reserve two additional development builds05/06 each300s for corrected disabled
comparison and final selected reference, in addition to unspent build04. This
is evidence-directed, not a retry of unchanged code; final gates remain exact.

Diagnostic01 spent8.323s: actual v8 admitted, private high-page/stack proof
passed, but child exhausted32 samples in first window (initialization plus
200ms work); parent correctly reported unexpected child termination208.
No kernel failure or authority bypass. CPU raw evidence shows nine initial
samples and23 burst samples before exhaustion. Reduce test burst to100ms,
retain four periods and independent >32-total proof; do not change CPU limits.
Extend full zero-state observation to all13 image contexts of eight-slot pool.

Diagnostic02 spent5.490s: raw saved RAX=-22 at SLEEP_MS1000 and RIP41086d.
Existing process_run.inc admits sleeps1..100ms. Fix fixture idle to ten bounded
100ms sleeps; no syscall limit change. Preserve diagnostic02. Reserve build07
<=300s for this correction if needed after existing builds05/06; not unchanged
retry. Host snapshot test uses stubs only for profile/startup/image validators,
not a claim of whole guest lifecycle acceptance.

Build06 disabled02: all runtime bytes and DWARF info exact; decoded line diff
isolated only main closing brace136 becoming137..139 across PROGRAM_ID arms.
Add one explicit closing-brace anchor. Reserve build08<=300s to verify all56
artifacts byte-for-byte after this concrete correction; old comparisons remain.

Diagnostic03 passed31.223s: both root runs, four private RNPGv3 generations,
53..67 actual CPU samples per child total, bounded32/window; all raw ownership,
CPU transitions, high-page/stack witnesses and complete13-context cleanup replay.
Host06 passed four actual SDK/assembly O0/O2 tests5.387s. Six hosts/eight builds
and three diagnostics spent. Final gates not started.

Build08 isolated the remaining root object difference to its generated import
header's random directory string in DWARF. No byte difference elsewhere in any
of56 artifacts. Host05 recompiles current production source using the exact
baseline header path (header bytes verified identical): the WHOLE root object
is byte-identical, SHA2569141129b8b245b98ecaadcb95a695630d4f5f4fa91bafddda771db584c648f10.
Initial host05 receipt serialization failed on WindowsPath after successful
compiler execution; reconstructed from retained exact objects without rerun.
The final defaults gate uses the same input-path binding to compare the entire
root object; it never strips/normalizes object bytes. All55 other artifacts
compare directly. Retain both raw random-path objects and the exact recompile.

Reserve final qualification01: the five unchanged commands/limits above, one
fresh disabled build and one fresh selected build (each300s), one<=60s root
object compile with identical generated-header path, six fresh guests. The
normal diagnostic does not replace any final guest. CPU raw events also bind
every result/period/total to the exact before/after state; final review injects
raw budget, window, plan and image corruptions and must reject each.

Qualification01 stopped at runtime gate after gates1..3 passed5.093/7.666/7.543s.
Normal and exhaustion cases passed; cancellation retired first child cleanly,
then root exhausted32 samples while immediately constructing its replacement.
Root raw receipt status256/state3, RIP4100f3; no kernel corruption. Add ten
100ms root sleeps between fixture generations, keeping both starts, fixed CPU
quota and all original finite waits. Normal/source behavior remains selected.
Host07 independently mutated live plan entry in retained CPU evidence; replay
incorrectly accepted it. Tighten observer and independent reader to require
actual live plan entry1. Do not reinterpret qualification01 as accepted.
Reserve qualification02, same five commands/limits and all six fresh guests,
two new300s builds plus60s exact-header compiler. No reused changed observer
captures, no reset of seven development hosts/eight builds/three diagnostics
or qualification01 consumption. Remaining development diagnostics04..06 stay
available; use04 for the corrected cancel/replace path before final freeze.
Reserve development build09<=300s for that evidence-directed correction.

Diagnostic04 spent2.586s, observer rejected dynamic slot2 because its run-plan
first word is immutable kind0 (roots kind1), not a live-state flag. Current
family_create64 publishes profile/budget/image only; task state carries liveness.
Correct the independent plan assertion to kind1 for roots and0 for dynamic
slots; retain separate actual task-state2 and exact generation checks. No guest
change/rebuild needed; diagnostic05 repeats only after this concrete correction.

Diagnostic05 spent5.554s. More precise raw/disassembly evidence corrects the
initial qualification01 hypothesis: root exhaustion occurs at IPC_CLOSE return
4109bd before second construction, after repeated charge observations while
WAIT/CANCEL returns are pending. Pacing only between generations is too late.
Place a finite ten100ms supervisor sleep after the expected initial100ms WAIT
and before CANCEL, within the child's existing2000ms deliberate sleep; retain
exact live-target cancel, reap and both generations. No kernel budget/deadline
change. Reserve build10<=300s; use remaining diagnostic06 for this correction.

Diagnostic06 spent21.532s: full two-root capture and clean cancel/reap completed,
but first replacement gen4 reached32 samples in its initial period. Raw task
RIP41083b/clock3110 already exceeded its3060 burst deadline while dispatch was
still observed. Separate child initialization with ten100ms sleeps and reduce
four workload bursts to40ms; retain actual >32 total evidence and each32/1000ms
limit. This is fixture pacing, not relaxed oracle/quota. Reserve build11<=300s
and diagnostics07..08<=360s for corrected cancellation and OOM paths. Hosts01..08,
builds01..10, diagnostics01..06 and failed qualification01 remain spent.
Host08 accepts valid retained normal evidence and rejects mutated root plan.

Diagnostic07 cancel/recreate passed28.208s, fresh normal children44/45 samples.
Diagnostic08 OOM rollback and all ownership/cleanup passed but workload proof
failed: first-generation totals25/28 <=32 (replacements40/43). Do not accept
this as cross-period execution. Use six80ms bursts with900ms idle, plus initial
1000ms idle: nominal6880ms fits unchanged eight1000ms WAIT calls. Each CPU
window still32 samples, all actual transitions replayed. Reserve build12<=300s
and diagnostic09<=360s for corrected OOM workload. Preserve all eight prior
diagnostics and all counters. No reduced >32 check or removed first generation.

Diagnostic09 passed45.505s: partial OOM at acquisition26 in each root, exact
rollback, both fresh large generations, actual child totals68..83, complete
CPU/ownership replay. Eight development hosts,12 development builds,nine
diagnostics spent plus qualification01's three passed gates/two passed guest
cases and failed cancellation case. qualification02 reservation above now
freezes corrected pacing/plan oracle, five host tests including invalid selector
rejection before output, and all six fresh runtime cases. No completion claim.

Qualification02 gates1..3 passed; fresh normal/exhaust/cancel/OOM cases passed.
RX case contained first child's write fault, but replacement construction
exhausted root at period1 used32 (total46), triggering supervised child cancel.
Raw root window origin is0. Sleeping a relative1000ms carried idle charges
into the next construction window. Align the fixture's between-generation
sleep to the next absolute1000ms boundary, at most ten sleeps<=100ms. Require
root origin0 in both observer and independent reader; no invented phase or
budget reset. Keep every kernel quota, CPU trace and both generations.
Reserve build13<=300s and diagnostics10/11<=360s for RX/guard correction.
Then qualification03: same five gates, two300s builds/60s header compile and
six fresh guests; qualification01/02 failures remain failed with full evidence.

Diagnostic10 spent15.151s: corrected RX/replacement root1 succeeded; observer
wrongly assumed origin0 for root5. Each new run binds its own nonzero epoch.
Remove that assumption. Extend only the private qualification selector to24
bytes: debugger copies this root's actual already-admitted window origin into
its own writable fixture field; independent raw replay binds page ownership,
zero-before-write, exact epoch and root generation. Never alter CPU counters,
periods, kernel state or public ABI. Existing selector/mode writes are unchanged.
Fixture aligns idle relative to the supplied actual epoch. No fabricated phase.
Reserve build14<=300s and diagnostic12<=360s in addition to unspent guard11;
run corrected RX as12 then guard11. Frozen runtime gates and exclusions remain.

Diagnostic12 RX and replacement passed27.975s with actual per-run phase input.
Diagnostic11 guard child faulted/was reaped correctly; supervisor hit32 while
returning from first fault WAIT before any between-generation pacing. Share a
bounded wait-next-period helper (<=ten sleeps, each<=100ms) and call it after
READY delivery but before WAIT for fault modes1..4, separating construction
from observed fault teardown. Cancellation keeps its already-proven sequence.
Reserve build15<=300s and diagnostic13<=360s for guard; every failure remains.

Diagnostic13 guard/root1 passed; root5 exhausted at unchanged MONOTONIC return
410c3f before executing the first wait helper instruction. Repeated raw RIP and
charges show per-charge stop overhead can prevent user progress; further pacing
alone is insufficient. Replace two CPU stops per sample with one result stop:
read actual zero-use budget/window and immutable plan at existing first-entry
stop, then every actual result state (64 bytes plus live state/generation16).
The previous recorded result is the next pre-state; require exact +1 total,
unchanged generation/limit/origin and correct window arithmetic. Match complete
per-generation totals to independent terminal reap receipts; missing/duplicated
samples fail. No sampling, marker substitution, changed accounting, removed
failure case or new kernel trace. This reduces per-charge task reads4096->16
and avoids rereading immutable plan336 each sample. Raw initialization still
contains complete plan and task; frame/ownership proof remains unchanged.
Reserve diagnostics14/15<=360s for guard/RX with the same enabled11 guest bytes;
no rebuild or unchanged retry. Prior observers/captures remain preserved.

Diagnostics14/15 passed29.444/30.423s for guard/RX: both faults contained,
fresh replacements66..76 total samples, every actual result and final reap
counter matched, complete frame/plan/phase/cleanup replay. Eight development
hosts,15 development builds,15 diagnostics plus qualifications01/02 remain
spent. Qualification03 reservation above now freezes the one-result-stop
observer and six corruption classes: initial budget/window/plan/image, private
phase input and post-charge counter. All six fresh guests remain required.

Qualification03 host gate passed; defaults stopped before any selected build
or guest. Only program2.o changed beyond generated-header directory: skipped
root-only epoch helper shifted child declarations26..58 to44..76 in DWARF.
All executable bytes exact. Add branch-local #line26 before the unchanged
child declarations. Preserve qualification03; reserve qualification04 with
unchanged five gates/two300s builds/60s header compile/six fresh guests. This
corrects diagnostic coordinates, never relaxes byte equality or runtime proof.

## Scope stop after qualification04 — concrete next prerequisite

qualification04 host/default/package gates passed5.084/7.769/7.513s. Normal,
exhaustion, cancel/recreate and OOM cases passed43.740/29.837/29.501/44.038s.
RX root5 still exhausted32 samples at MONOTONIC return410c3f and cancelled its
child before the intended RX fault. Guard and final review were not run. The
package is NOT accepted; no implementation commit. Keep qualifications01..04.
The repeated same-RIP charges support observer interference as a hypothesis,
not a proven kernel fix. Stop modifying workload timing speculatively.

Inventory found the already accepted bounded CPU trace in
arch/x86_64/proc/cpu_trace.inc and scripts/native_cpu_trace.py. It records exact
before/after states in a256-entry192-byte ring,2048 lifetime charge ceiling,
no allocation, logging, waiting or guest acknowledgement in IRQ. Makefile
currently enables it only for service-PIO/live-file; cpu_trace.inc explicitly
requires REIST_NATIVE_POOL_PIO. Device-free CD cannot use it without changing
that protected source file, which is outside this package's allowed_files.
AGENTS.md requires stopping and reporting that architectural scope boundary;
do not bypass it with a fake PIO macro, copied source or expanded allowed_files.

Concrete next prerequisite: separately freeze an explicit device-free
qualification trace selector for the existing NativeServiceCPU mechanism,
keeping disabled profiles exact and all ring/counter/IRQ/authority limits.
Required source scope: cpu_trace.inc, Makefile and Windows build selector;
existing native_cpu_trace decoder/reader can be reused without public ABI.
Verify actual trace bytes/overflow/error/register preservation against the
accepted PIO trace, legacy byte equality and a fresh device-free guest using
batched trace drain and independent full before/after replay. No per-charge
GDB stops; validate exact source/tool/image binding and preserve all failures.
No new CPU/device/process grant, pool increase or safety threshold change.

Then restore this exact CD candidate, bind its v8 guest to that accepted trace,
freeze a finite new qualification window and run all unchanged gates/cases.
The four passed cases are preserved evidence, not permission to mark the whole
package done. CB's nine-file archive/stash/counters remain unchanged. No push,
no nested agent, no user files overwritten, no finished desktop claim.

## Resume after accepted CE ecb00165

Device-free NativeCPUTrace prerequisite accepted five gates, normal/exhaust guests
and full closed evidence seal94d8ba789e74758132d0bacd836ce49a2bbce449f381219f6625064d1edb2393.
Restore scope-stop01 source byte-exact, merge only accepted Make/PS trace selectors.
Never overwrite CE queue/status/source. Previous CD8 hosts/15 builds/15 diagnostics
and failed qualifications01..04 remain spent. No workload pacing change in this
window: replace per-charge debugger stop with unchanged256x192-byte trace reader,
2048 maximum records. Initialize zero ring at boot, drain before every lifecycle
callback and at ring-full, bind live generation, exact initial plan/budget/window,
full recorded before/after transition and every terminal reap CPU total. Replay
actual memory ring records independently and compare raw trace closure. Preserve
all ownership/frame/source-overwrite/OOM/fault/cancel checks and cases.

Reserve hosts09..12<=180s, builds16/17<=300s, diagnostics16..18<=360s for
normal/RX/guard. Then qualification05 has the same five commands, six fresh
guests<=360s each/2160s aggregate and original corruption classes. Accepted CE
trace explicitly selected only in enabled CD qualification builds. Reuse exact
preimplementation baseline01/head6f5dfc65 for disabled raw artifact equality;
CE exact disabled guards introduce no guest code. The new setup commit is the
CD source binding HEAD; history still binds original baseline and every failure.
No extra authority, CPU quota, pool, guest limit, display approval or gate waiver.
