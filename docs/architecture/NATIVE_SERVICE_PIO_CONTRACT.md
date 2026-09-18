# Native periodic PIO service boundary — R8.3aq

Defined after clean accepted `9011ef1e`,18 September2026, under the standing
interactive completion directive. One package/main agent, no nested agents or
push. The dated amendments below retain the complete implementation history.

## Qualified result

Candidate824caeb2078e26a0 on9731d528 passes all15 obligations and18 same-image
guests. Main host group75/75, actual trace/calibration at O0/O2, four exactly
bound reference builds reused and one new imagec3e816552286537f. All six owner
slots,8GiB, crash/hang/quota/bad-reply/root-loss/no-disk, three real OOM points
and both physical corruption-fence cases pass the unchanged original checks.
Complete raw CPU/PIO/memory/media review passes; guest time507.337903s and
gate commands592.778244s. Retained history: seven images36 attempts958.222516s,
including every prior failure; no remaining QEMU/GDB. No retry or partial
matrix was promoted. Qualification is immutable under active-calibration;
verification-status-service-pio-final.json binds the local commit and clean
worktree after documentation-only closure. This is not ordinary shell/file,
physical hardware or complete64-bit OS acceptance. R3.6b remains deferred.

## Inventory and scope

Current workload correction after explicit user approval: cpu-trace-adapter
passed11 obligations; its first guest completed both runs/four reads and all276
raw CPU records, but warmup samples were21/49/48/49. The40-sample minimum
really failed; neither missing trace data nor an accounting error explains it.
The precise timing cause is not established, and the failed case is not accepted.
Only the private service_quantum calibration changes: three actively executing
20ms monotonic trials, each at most100000 clock polls. No calibration sleep;
reject backward, stalled or >1000ms clocks, invalid TSC intervals, overflow and
the original200000000-cycle limit. Retain11ms scaling and10ms quantization
subtraction; the running-clock hypothesis must still pass actual CPU evidence.
Clock polling occurs only during this finite qualification calibration, not
in any safety/service wait or the forty syscall-free bursts. Eight progress
notices,80ms blocking gaps, twelve idle waits and the client IPC pause remain.
Kernel/trace/SDK/driver and all original runtime predicates stay exact.

New active-calibration evidence binds all previous sources and failures:
six images18 attempts450.884613s spent; at most one new common image, full16+2
fresh guests, same15 obligations once and first-failure stop. Cumulative limit
seven images36 attempts1260.884613s; no reference or diagnostic build/guest.
Guest45s/cleanup3s, matrices720/90s, outer800/150s and CPU/PIO/ATA/IPC/session
limits stay fixed. Host tests run the actual calibration/workload at O0/O2,
cover all error exits and exactly reverse the new delta for historical source
comparisons. This amendment overrides only older workload-exclusion text.
No new qualification or complete64-bit OS acceptance has occurred.

Current explicitly approved qualification amendment: only NativeServicePIO
may add the private CPU trace described below to the scheduler wrapper.
This narrowly overrides the original prohibition on scheduler changes;
pure CPU accounting, production drivers, SDK, workload and limits stay exact.
Other profiles do not define REIST_NATIVE_CPU_TRACE and must produce identical
preprocessed scheduler input against all four retained reference layouts.

Private trace-v1 records are192 little-endian bytes: version/kind/sequence/slot
(four u32), generation/tick/result (three u64), before/after budget+window
(sixteen u64), actual before/after RFLAGS and mode (three u64). A32-byte header
holds total/error/pending/reserved. The256-entry ring and one pending record
occupy49376 fixed bytes outside scheduler reset state. The IRQ-disabled producer
preserves registers/flags, never allocates/waits/logs or changes accounting;
it publishes complete records last, with a2048-charge lifetime cap and sticky
error on invalid metadata/overflow. No consumer acknowledgements or repairs.
The debugger drains before existing lifecycle callbacks and at each full ring,
using at most two contiguous data reads; the four per-charge hooks are removed.
Every raw record must exactly equal its original full-word CPU ledger event;
original independent CPU arithmetic and all owner/cleanup predicates remain.
Reject missing, reordered, corrupt, pending, overwritten, wrong-owner, IF!=0,
future or post-closure records, short IO and missing count/SHA256 closure.
Raw trace, ledger and memory dumps jointly retain2048-file/128MiB limits.

Five prior images and17 attempts409.052493s remain sealed, including the
inconclusive reduced-observer diagnostic. New evidence is under cpu-trace:
one changed candidate, at most one new common image and the complete16+2
matrix;15 obligations once, first failure stops, no diagnostic guest or
reference rebuild. Cumulative ceiling six images35 attempts1219.052493s;
45s per guest including cleanup,3s cleanup,720/90s matrices,800/150s outer
limits and all CPU/PIO/ATA/IPC/session limits remain. No acceptance yet.

The trace candidate stopped at host gate1 (72/73 passed, real producer O0/O2
passed), before any image or guest: the historical source-identity test still
rejects the authorized wrapper. The bounded cpu-trace-adapter correction
reverses exactly the approved wrapper and scheduler/Make additions before
the old comparisons, with missing/duplicate/mutation negatives. Implementation
and assertions stay fixed, apart from exact evidence path/provenance binding.
One new candidate, same15 obligations and shared one-image/18-guest allowance;
preserve the host failure and stop on the first new failed gate.

[Periodic CPU admission](NATIVE_SERVICE_CPU_CONTRACT.md) passed all24 gates
and14 guest cases. [Eight-task PIO](NATIVE_POOL_PIO_CONTRACT.md) already binds
slots2..7 to one generation-scoped read-only ATA device. The build deliberately
rejects their combination. The existing `scheduler_fail` already selects
`native_pio_fail64` before the device-free TaskPool halt; normal owner retirement
already fences. Reuse those mechanisms, CREATE-v6, native_pio/native_service,
block RPC and private CPU-window-v1. No second accounting or recovery engine.

Close this shared CPU/device-owner lifecycle with one explicit
`-NativeServicePIO` / `X86_64_NATIVE_SERVICE_PIO=1` profile. Old ServiceCPU stays
device-free and old PoolPIO stays lifetime32; no implicit profile upgrade.
The new producer selects TaskPool/Wide/PIO/BlockProfile and private run-v5;
only its supervisor explicitly delegates CREATE-v6 to its driver/fillers.
Root1/fillers have no device rights; root0 alone binds/fences. Old versions,
SDK, syscall numbers and all production kernel/driver sources stay exact.
If a missing mechanism requires changing them, stop for architectural review.

References remain System V AMD64/ELF64, ATA IDENTIFY/READ SECTORS/LBA28 with
512-byte sectors, existing versioned REIST PIO/block/negative-errno adapters.
No new standard-compatibility claim, wire ABI or persistent format.

## Bounds and failure model

Keep CPU32 per1000ms, monotonic lifetime usage, immutable origin/no saved credit;
legacy CREATE-v1..5 remains lifetime32. Eight slots/eight CREATE attempts per
root, existing image/heap/IPC/IRQ limits, PIO64 calls/100ms and16 words/call,
ATA200ms, RPC1000ms and session3000ms remain. Only finite qualification workload
wait counts may differ in the new profile: peer60 and filler80 sleeps of100ms,
not new sleep limits or production service policy.

The bound device owner first performs40 calibrated11ms CPU bursts with80ms
sleeps, in eight acknowledged batches of five. Reuse AP's enclosing three-trial TSC/
monotonic calibration and its exact range/error checks. Each progress receive
is bounded by1000ms. No syscall in a CPU burst; the IRQ ledger, not elapsed
time, proves at least40 samples across windows. Only after these bounded
pre-service batches does the existing unchanged service session initialize,
IDENTIFY/self-test/read. Never reset/reopen a service to evade its deadline.

The18 September idle correction inserts twelve existing blocking100ms sleeps
after those unchanged40 bursts and before service initialization. A phase3
progress notice after6/12 sleeps keeps each supervisor receive at1000ms.
Complete CPU snapshots at warmup end and both acknowledgements must retain
the immutable origin/lifetime ledger; the authoritative tick difference is
at least60 per half and crosses a100-tick window. No kernel word is reset.
Filler tasks now use120 finite100ms sleeps to cover both driver generations;
peer60, all kernel sleep/IPC/CPU limits and the service session stay unchanged.
The CPU binary stream uses unbuffered host writes so failed-prefix records
remain available; the original strict footer/hash requirement still rejects
an incomplete run. No failed evidence is promoted to acceptance.

Both initial and replacement drivers preserve root authority, fresh generation,
fencing, read-only media and complete cleanup. UD2, sleeping hang/CANCEL,
CPU-window exhaustion, malformed reply, root loss and OOM follow the existing
detect/isolate/fence/revoke/reap/recreate/self-test path. Independent root1 must
continue; exhaustion is contained, not a kernel panic.

For unknown CPU metadata corruption while a slot7 owner is physically released,
inject exactly one eight-byte window or generation word before pure CPU-core
validation. Require actual OUT DX,AL nIEN/SRST before diagnosis, unchanged
damaged CPU/task/family/device snapshots, IF=0, CLI/HLT and no reap/resume.
This is fatal containment, not in-place repair or fail-operational behavior.

## Frozen proof and efficiency

Use one same-image16-case normal matrix: six healthy driver slots2..7, slot7
at8GiB, driver UD2/hang/CPU exhaustion/bad reply, root0 loss, absent disk,
and first/middle/last actual import-allocation OOM. All others4GiB; two process
runs each and the original one replacement except terminal root loss.
Add exactly two fatal guests for window/generation corruption in slot7.

Preserve every independent frame/context/FP/W^X/private/immutable byte,
generation, IPC/heap retirement, physical ATA/RPC bytes, media and cleanup
predicate from AO; explicitly adapt only run-v5/CREATE-v6, periodic CPU and
declared finite workload timing. Add the AP bounded full-word CPU ledger and
reject missing/reordered/forged records. Normal binary reads retain independent
same-stop equivalence; fatal capture uses direct complete snapshots. No kernel
test syscall, fabricated healthy state or dynamic record repair.

The syscall observer retains its full original witness body. General syscall
stops are enabled until every created generation has published its immutable
image/heap proof; afterward only GETPID and family-control stops remain.
CREATE completion and run cleanup re-arm the general observer. Switching never
occurs inside GETPID/family control, so one call cannot invoke both adapters.
CPU/PIO trace, RPC, fault, cancellation and cleanup hooks remain independent.

Only the original-zero root fixture mode word may select normal cases (once
per run, with full image/mapping validation). Existing OOM allocation-return
injection is the sole other normal mutation. Preserve all write bindings.
Fatal guests first use that same admitted case5 setup (mode5 in root0's
original-zero userspace word) to place the device owner in slot7. Bind the
single setup write to its actual private writable mapping before release;
only the later, separately recorded eight-byte CPU injection alters kernel
metadata. No extra mode, syscall, device grant or image is introduced.
Media is only the existing generated64KiB read-only base with exclusive
disposable qcow2; exact backing/map/logical bytes and no data allocation checked
before/after, including failures. Never use user or physical disks.

For the approved host-only renewal each PIO guest has45s including
setup/capture/media/process cleanup:42s observation and cleanup<=3s.
Normal matrix720s/fatal90s, outer800s/150s; host300s, build/verifier180s.
This supersedes the original PIO host30s/matrices480s/60s only. Default20s
and service-CPU30s capture paths remain unchanged; the two explicit service
selectors are strictly boolean and mutually exclusive before side effects.
All15 queue obligations are frozen, each once per unchanged candidate.
The selected AP methods are invoked through their concrete test file, not the
`test.*` package namespace which collides with Python's installed test package.
This host invocation correction precedes any candidate or acceptance gate;
the same seven actual method names and all assertions remain unchanged.
Selected actual AP/AO host mechanisms are reused, not all historical test matrices.
One new common image per changed build-input candidate, no reference rebuilds.
The reference gate binds accepted AP/AO/legacy evidence and original inputs,
tools, profiles, commands, logs, artifacts plus exact legacy preprocessing.

At most three changed candidates, two evidence-directed in-scope corrections,
three builds and54 guests1620s cumulative. First failure stops later gates;
no unchanged retry, extra diagnostic guest, gate waiver or timeout expansion.
Outside scope, pre-existing failure, default drift or a missing production
mechanism stops implementation. All gates plus direct final diff review precede
the local commit/clean queue transition. Preserve all prior evidence.

The user approved one further bounded correction after the three original
candidates stopped: one changed candidate under `idle-renewal`, at most one
new common build and18 new guests, zero diagnostic guests/reference builds.
All15 obligations remain; stop at the first failed gate, without another
candidate or retry. The two spent guests21.4284s remain counted; the renewed
cumulative ceiling is20 guests561.4284s. Old images and raw failures remain.

That idle candidate also stopped at gate12: the complete69-record CPU prefix
proves warmup itself exhausted32 samples in window[107,207), at51 lifetime
samples, before30 bursts and before idle/ATA. The explicitly approved spacing
correction changes only warmup40ms sleeps to80ms and progress every10 to5
bursts; all40 bursts, calibration, actual40-sample minimum, complete idle
proof and all original safety assertions remain. Its single candidate under
`spacing-renewal` permits one new image and18 guests, no reference rebuild or
diagnostic guest. All15 obligations and first-failure stop remain. The three
spent guests27.025603s count toward21 guests567.025603s; both old images and
all failures are retained. Spacing-model tests are not guest acceptance.

The spacing candidate passed11 gates and its first guest reached three
healthy driver generations (75/78/79 lifetime samples), but its observation
deadline ended the second run before closure. Its341-record prefix is not
acceptance. The user-approved `host-budget` renewal changes only host timing
and shared capture/binary-reader adapters with both complete host regression
modules included in gate1. All observer/oracle bodies, assertions, kernel
limits and qualification workload remain exact. One changed candidate,
zero builds and at most18 new guests; no partial matrix reuse or diagnostic
guest. Bind the successful spacing build by source/tool/profile/command/log/
artifact equality (image4e67cbdd), not just filename. Retain all three images,
four spent guests56.571504s and every failure; cumulative22 guests866.571504s
maximum. All15 obligations, first-failure stop and full18-case review remain.

The host-budget renewal passed11 obligations and complete cases0/1, then
case2 failed: its healthy second-run replacement used32 service CPU samples
after the full idle, at lifetime83. All394 CPU records close and match the
pure core; fencing, balanced frame retirement and media guards pass, but
READ fails with EPIPE. This is not a host deadline. Seven attempts143.078498s
and three images are retained; no AQ acceptance follows from containment.

The bounded `reap-probe` continuation narrows only the normal observer's
`cold_reap` breakpoint from every IPC lifecycle invocation (including timer
expiry checks) to the existing op4-only `MOV EAX,5` at entry+19. Before task
entry, bind all24 instruction bytes and the existing `not_reap` label+24.
Keep the full callback, generation/IF/pending guards and every other observer,
CPU snapshot, ledger and runtime assertion. No kernel, driver, fixture,
transport, guest clock or image change. Host tests bind the actual image,
all prefix-byte mutations and old/new callback behavior. A timing benefit
is only a hypothesis until the complete16+2 guest matrix passes.
One changed candidate, zero builds, at most18 new guests; cumulative25
guests953.078498s. Same15 obligations and exact gate11 build reuse, unchanged
45s/3s guest/cleanup and720s/90s matrix bounds; stop at the first failure.

That reap-only candidate passes cases0/1/2 but case3 exhausts two healthy
slot5 generations. Its323-record failed prefix proves initialization costs
23/24 samples before the next request uses the remaining9/8. The data field
includes LBA0 self-test plus LBA1 read, separately from512 IDENTIFY bytes;
only160/288 requested bytes complete. Fencing occurs, but the unchanged final
task-count assertion rejects the absent second-run replacement. All failures,
eleven attempts249.672145s and three images remain retained.

The explicitly approved `client-pause` correction changes only the new root
fixture: after a successful ready/self-test notice and before client bind or
request, one existing blocking800ms sleep; absent media skips it. Filler
lifetime becomes160 finite100ms sleeps. No driver/SDK/kernel change, quota
increase, session reopening, request deadline extension or old-profile drift.
The normal observer additionally records the actual root SLEEP_MS800, driver
IPC BLOCKED within100ms, and request arrival after at least800ms root delay
and700ms unchanged blocked driver CPU state. All three snapshots are bound
to generation, root, full CPU ledger and the unchanged24-byte service profile
and deadline. Two temporary hooks are disabled outside this narrow pause;
at most16 dispatch checks, all existing8192 callback/2048 charge caps remain.
Original owner/CPU/fatal assertions remain; missing/forged/unblocked/short or
charged pause evidence fails. Models do not substitute for guest proof.
One changed candidate, exactly one new common image and at most18 guests;
no reference rebuild or diagnostic guest, first failure stops. Cumulative
ceiling four images29 attempts1059.672145s. Same15 gates,45s guests including
cleanup,3s cleanup cap,720/90s matrices and800/150s outer limits.

The client-pause candidate stopped at host gate1:65 of66 tests passed, while
the historical observer comparison could not resolve its virtual compile
filename through Python source inspection. No build or guest was started.
The approved `client-pause-adapter` candidate changes only that test loader
to the exact immutable snapshot filename. All comparisons, runtime observer,
fixture, kernel, driver, SDK and transport behavior stay unchanged; only the
new evidence paths and exact admission bindings differ. Retain the failed
gate and source-lookup diagnosis, then run all15 obligations once. The combined
client-pause allowance remains one new image and at most18 new guests, with
unchanged cumulative counts, deadlines, first-failure stop and full review.

The adapter candidate passes11 gates but its first guest exits at root245:
the unchanged native SLEEP_MS admission accepts1..100ms, not800ms. The74-record
prefix has no CPU exhaustion; driver fencing and peer completion occur, but
there is no requested read or pause completion. Preserve this fixture defect,
four images and12 attempts258.358061s; no kernel defect or acceptance inferred.

The approved `ipc-pause` candidate replaces only that invalid sleep with one
existing IPC_RECEIVE_TIMEOUT800 on the already-consumed notification endpoint.
Reinitialize the140-byte receive object to version1/size140/capacity128 and
require ETIMEDOUT(-110); a message, EPIPE, invalid handle or other result fails.
The endpoint and generation already belong to the supervisor; no new grant,
endpoint, kernel limit or service-session extension. Filler160 stays exact.
The pause witness binds READY's actual endpoint, the canonical receive object,
both root/driver BLOCKED within100ms and at least700ms unchanged driver CPU
state. One additional temporary IPC TAKE completion hook binds the actual
request/handle/buffer/800ms, deadline=start+80ticks, capacity140 and result-110
before the read request; all hooks must be disabled afterward. Existing CPU,
owner, fatal, memory, media and timing predicates remain. Tests execute the
actual sleep guard and real IPC adapter at O0/O2, including early messages,
revocation, invalid inputs, copied pending state and complete cleanup.
One changed candidate, exactly one new image and full16+2 guests at most;
all15 obligations once, first failure stops. Cumulative five images30 attempts
1068.358061s; per-guest45s/cleanup3s, matrices720/90s and outer800/150s remain.

The first IPC candidate stops at host gate1 before any image/guest:67/68 tests
pass, but the new real-IPC harness omitted REIST_NATIVE_RUNTIME and selected
the old256-tick horizon. Its READY-send deadline300 is correctly rejected.
The in-scope `ipc-pause-profile` correction adds only that existing target
build selector to the host test. All assertions and runtime sources remain;
the failed gate is retained. One fresh frozen candidate, same15 obligations
and first-failure stop; the combined IPC allowance is still one image/18 guests,
not an additional reservation. No quota or production profile is changed.

No filesystem, ordinary shell, new device/DMA/write right, physical platform
or complete64-bit OS claim. This is a prerequisite for later concurrent native
file/service consumers; R3.6b stays explicitly deferred.
