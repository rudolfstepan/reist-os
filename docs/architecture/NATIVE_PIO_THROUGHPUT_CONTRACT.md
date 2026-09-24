# Native read-only PIO throughput prerequisite — R8.3by

Frozen after df9523be and the user's explicit continuation after the concrete
128-call/25ms resource proposal. BV's35 attributed files are preserved in
build/codex-agent/native-vmware-desktop/paused-bv-throughput/files.zip with
per-file SHA256 and stash cc29b83e4a3b5c1bb89b44d1b2049fae86b632b9.
No BV implementation enters this kernel prerequisite. Restore it after BY
acceptance, preserving new PIO files and metadata, then qualify its full
two-root1MiB pipeline. No frozen BV gate or failure is waived.

## Mechanism and ABI

Reuse native_pio_admit64/apply64/syscall64/terminal64/finish64, their validated
pinned64-byte request/state and exact generation/parent witness. ATA PIO
terminology and existing errno/operation semantics remain. Append request
version3 ONLY for BIND1, size64, quota128 at offset48; all other reserved
fields zero. v1 BIND/FENCE and v1/v2 operations retain their exact contracts.
Only the existing root with both old-reaped/new-owned-live witnesses may
bind. No same-generation rebind or driver self-upgrade.

State64 offset56 is zero for old64-call grants or the redundant encoded tag
0xffffff7f00000080 for128-call grants. Count bounds depend on that exact tag;
all other tag values fail corruption admission before effects. An ownerless
state requires zero tag. Fenced tags are retained only as diagnostics:
fenced grants admit no I/O. Rebinding resets count/tag to the explicitly
requested profile; final reap scrubs the whole state. Old64-call grants
remain byte-identical. No mutable global quota or new port authority.

100ms window, trusted10ms ticks, backward-clock fence,16 words/transfer,
read-only ATA whitelist and v2 per-operation deadlines stay unchanged.
At quota exhaustion the requested read/write/transfer is rejected; existing
idempotent fencing may issue its one control-port reset. "No port effect"
in the proposal means no requested I/O after rejection, not omission of
the existing protective reset. No DMA, IOPL, additional ports or data writes.

The driver and filesystem stay in Ring3.25ms software pacing belongs to
the subsequent BV integration, conditional on this explicitly granted
profile; old100/50ms adapters must remain unchanged.

## Frozen proof and finite reservations

Exactly five gates listed in the queue; limits900/900/600/900/600s.
Host O0/O2 executes the actual assembly with fake hardware/address-space
boundary only:64/65 and128/129, exact100ms reset, stale owner/root-only
delegation, canonical envelope, overflow/invalid tags, reverse clock,
fence/rebind/terminal/reap and unchanged failed read buffers. Existing PIO,
deadline, pool and trace host tests protect all prior profiles.
One opt-in pool-PIO fixture build; real QEMU captures new-profile normal,
driver crash, hang, CPU exhaustion, cancellation/recovery and an old-profile
reference. Full raw PIO/lifecycle/ownership/cleanup proof and independent
replay are mandatory; no console-marker-only acceptance. Maximum eight
guests60s each/480s total. A successful host test alone cannot complete BY.
Direct final scope/ABI/cleanup review, all gates and local commit before BV.

Development reservation: eight host commands600s, two builds300s, three
diagnostic guests60s. Fresh exclusive receipts; first failure stops its
window; evidence-directed correction may reserve another finite window
without asking for routine permission. Preserve failures, no unchanged
retry, no nested agents, no pushing. Full VMware desktop remains unfinished.

## Development evidence, 2026-09-24

Host01 red includes the intended missing-v3 failure and an inadvertently
discovered historical test extractor with a missing `session` local; its full
pool suite is not claimed passed. Hosts02–05 pass the actual O0/O2 mechanism,
SDK construction, observer profile and opt-in compilation checks. The defaults
gate selects the existing actual PIO/deadline/pool lifecycle/trace tests and
uses complete default build-source projections; the stale unrelated extractor
is excluded explicitly, with actual builds still required.

Build01 passes. Diagnostic01 stops at an old trace decoder accidentally retained
by the private observer-body function; the generated observer now has a regression
test. Diagnostic02 correctly rejects a normal second driver exhausting CPU32;
both captures close and preserve all evidence. The previously Oz-compiled ATA
and block/service units now use O2 only for the opt-in profile. No driver source,
CPU budget or expected terminal result changes. Build02 passes; diagnostic03
passes full two-root normal case1 proof in15.173s. Diagnostics are not gates.
The five gates build one fresh candidate image and use seven fresh guests.

Candidate01: gate1 passed; gate2 stopped before legacy tests because Windows
locale decoding of the Makefile differed from the UTF-8 Git baseline. Explicit
UTF-8 source reads correct this verifier-only failure. No guest ran in that
window. Candidate02 reserves the same five unchanged gates, one fresh build
and seven guests with the same per-operation and aggregate limits.

Candidate02: gate1 passes; gate2 passes15 existing tests but the deadline
harness rejects the new optional static inline helper as unused after embedding
the header directly in its C translation unit. Marking this helper unused
preserves strict warning settings and all runtime predicates. Candidate03
reserves the same five gates, one build and seven guests at unchanged limits;
both earlier stopped windows remain recorded and started no guests.

Candidate03: gate1 passes all3 new tests; gate2 passes all16 selected legacy
tests and all default-source projections, then stops at the existing immutable
i386 reference guard: build/vmware/reist-os/reist-os-flat.vmdk expected
9f2998be4acc1ed6a8b7ab3051746fd14de1de06851575871422a0ad996309f5,
observed35e6459b3633cedcd0ef89aa79466c8a05c5002f9774b4bbfe0f643cf06e9be5.
The file predates this BY implementation (24 September07:40:06 local); its
VMware log records a07:39–07:40 boot of the ELF32 desktop. No reference image
was changed by BY. reference-drift.json retains hashes of the current disk and
three historical copies; none of those three matches the immutable pin.
Gates3–5 did not start. No acceptance commit, no BV restoration, no quota or
gate relaxation. A separate reference recovery decision is pending; current
disk, candidate evidence and all source edits are retained. The working new
profile is still diagnostic-only and the full native VMware desktop is open.

## Authorized reference recovery and fourth qualification window

The user renewed automatic completion after the concrete separate-reference
recovery request. reference-recovery01 preserves the complete existing VMware
directory with per-file hashes. Read-only bounded archive inventories found no
whole matching image. Comparison with the former runtime copy showed29 changed
sectors in mutable filesystem areas. Reconstruction01 rejects the first MBR
partition (boot partition2048); its empty output is retained. Reconstruction02
admits the identical complete MBR and second FAT32 partition8192/1040384, combines
the preserved original signed boot area with the previously qualified pristine
FAT32 partition from reference-metadata/vmware/reist-os.img. The FULL512MiB image
hash is exactly the original9f2998be4acc1ed6a8b7ab3051746fd14de1de06851575871422a0ad996309f5.
Only after full hash verification, absence of VMware processes/locks and exact
backup/current-image checks was that original restored atomically. No new pin,
requalification shortcut, source or user-data loss; restored.json records it.
This is authorized artifact recovery, not a second implementation package.

Candidate04 reserves the same five frozen gates, one fresh build and seven
fresh guests with unchanged60s/480s limits. Candidates01–03 and all earlier
diagnostics remain failed as recorded. No acceptance is inferred from recovery.

Candidate04 passes gates1/2 including the exact original reference guard;
gate3 rejects its absolute output path before compilation. The build wrapper
requires a relative build/... path, as used by both successful development
builds. Correct that argument only. Candidate05 reserves the same five gates,
one fresh build and seven fresh guests at unchanged limits. No prior failure
or spent command is discarded; no gate predicates change.

Candidate05 passes gates1–3; runtime passes old case0 and new case1, then
case6/8GiB reaches lifetime CPU32 in the first driver and fails the complete
cleanup oracle after root exits214. It remains failed. Reserve diagnostic04
<=60s using that exact built image and new read-only per-syscall CPU/clock
samples at the existing observer stop; no added guest write, changed quota,
new build or unchanged retry. The trace will locate the charged work before
choosing a correction. Host07/08 from the original host reservation remain
available for correction regression; no new candidate gate window yet.

Diagnostic04 records100 syscall samples,77 PIO entries, with charged ticks
advancing mainly across those observed PIO entries; CPU32 remains enforced.
The old generic syscall observer has no work after a child's heap/image witness
except root CREATE/CANCEL and GETPID paths. Scope that same complete observer:
arm generic entry at each new child start, disarm only once all live children
are proved; retain CREATE/CANCEL and GETPID at their actual dispatcher branches,
asserting the exact saved syscall number and avoiding duplicate observation.
No old assertion, data comparison, lifecycle proof or guest instruction changes.
Host07 verifies dispatch/unchanged oracle and actual kernel regressions;
diagnostic05<=60s checks case6 using the exact candidate05 image. No build.

Hosts07/08 pass. The final split retains the entire original syscall oracle at
the two cold branches and copies only its unchanged child-witness loop into
the generic callback, preventing double CREATE/CANCEL dispatch. Diagnostic05
still fails CPU32 (55 PIO trace events versus49 previously), with cleanup.
The GETPID hook remains on the hot dispatcher page even when the driver has
no GETPID observation pending. Reuse the existing scheduler state-published
stop, which executes at every task entry: enable PID only for root/peer,
family only for root, generic witness only for an unproved child. No extra
stop or modified guest memory. Reserve host09<=600s and diagnostic06<=60s
on the same image; all previous results retained, no changed safety budget.

Host09 passes. Diagnostic06 passes the full two-root8GiB/eight-slot proof,
18 exact task retirements,17.254s on the identical image1bacb256… with CPU32
unchanged. The correction is entirely observer trap lifetime; no guest code,
quota, result expectation, raw comparison or cleanup assertion changed.
Candidate06 reserves the same five gates, one fresh build and seven fresh
guests at60s each/480s aggregate. The normal diagnostic is not gate evidence.

Candidate06 passes gates1–3 and old/new4GiB runtime cases. Case6 now completes
both driver generations (8/12 CPU ticks in root1,8/11 in root2), but root1
exhausts32 ticks during final cleanup; full terminal oracle correctly fails.
Root2 takes27 ticks and exits normally. Root's family/PID traps were still
parked during expensive kernel CREATE/reap work. Disable both immediately
after their input witness; the already observed state-published boundary
rearms them before EVERY next userspace entry (process_run_resume64 queues
and dispatches through that boundary). No guest code or oracle removed.
Reserve host10<=600s and diagnostic07<=60s on the exact unchanged image.

Host10 passes; diagnostic07 still fails root1 CPU32 while all four healthy
driver instances use6–10 ticks and root2 uses29. Reserve diagnostic08<=60s
as a control measurement: identical image/media/RAM, original mode6 write at
each of the two fresh root entries, no other guest writes, only root-entry
and batch-finish debugger stops. Full serial outcomes are diagnostic CPU data,
never a replacement for the complete frozen runtime oracle. This separates
guest execution cost from the full observer before any further correction.

Diagnostic08 rejects before the mode write: state-published precedes loading
the user's CR3, so direct user-virtual reading is unavailable there. Reserve
diagnostic09<=60s with the same two control stops and the already used bounded
four-level physical page walk; validate the root PTE and original zero witness
before writing the same eight-byte mode field. Keep diagnostic08 failed.

Diagnostic09 completes both control runs10.576s: root CPU4/6, driver0/1/0/1;
all normal serial outcomes. This demonstrates ample unobserved CPU margin,
not acceptance. The complete oracle parks allocator/free breakpoints throughout
the frame-clearing routines. Keep each original entry observation/count/order,
disable its entry trap while that nonrecursive call executes, and rearm at
its exact saved return address via one temporary breakpoint. At most two
pending return probes; finish requires none. No OOM cases are selected in BY
(assert OOM is None), no frame/heap/PTE assertion removed or modeled.
Reserve host11<=600s and diagnostic10<=60s on the same candidate05 image.

Host11 passes; diagnostic10 adds excessive return-stop overhead and fails both
CPU32/root1 and the inherited20s transport during root2. Remove that experiment
and the TCG-only syscall scoping from the candidate; generated historical
observers/logs remain preserved. The proven no-observer CPU4/6 versus32 margin
justifies using the already accepted BS WHPX environment and its hash-bound
portable-qemu/binary-binding09.json. Reuse entry.asm's existing finite pre-task
rendezvous through an explicit NativePIOThroughputHardware build selector;
no entry.asm/source mechanism change or new hardware/authority domain. Keep
the complete original pool observer, all cases, real PIT CPU32, deadlines,
frame-order/zero/cleanup and raw replay predicates. No simulated clock/icount.
Only debugger execution probes use the accepted hardware registration mechanism.
Record/replay the bounded QMP bootstrap and sole pre-task release/cleared cells.
Reserve hosts12–14<=600s, one hardware development build03<=300s and diagnostic11
<=60s; no new frozen gate window until that exact full case6 proof succeeds.

Host12 passes the actual assembly and complete hardware-observer preservation
checks. Build03 passes7.835s; diagnostic11 passes the complete case6 proof19.866s,
18 exact retirements, root CPU12/13 and driver6/9/7/8. The guest child record
is byte-identical to TCG; only the existing opt-in pre-task bootstrap differs.
Independent replay now also validates raw QMP ready/paused/read order, the sole
release registers, cleared cells and the exact pinned WHPX executable/firmware.
Candidate07 reserves the same five gates, one fresh hardware build and all
seven full guests at60s/480s. Existing native guest CPU/time/rights and old
default build projections remain fixed. All previous candidates remain failed.

Host13 independently replays diagnostic11 including95 raw files. Candidate07
passes gates1–3, then case0 fails before the pool workload: legacy scheduler
mode5/stage159 self-test under prematurely active task-entry execution probes.
Keep fatal detection and C-core handoff active from bootstrap; defer all other
probe enabled states until that existing handoff, restore them exactly before
the native workload. Full old bootstrap serial markers and all later predicates
remain mandatory. Reserve host14 (existing reservation) and diagnostic12<=60s
on candidate07's exact hardware image, case0; no rebuild or unchanged retry.

Host14 passes syntax/oracle checks. Direct source review finds Hook stores fn,
not name; use the actual callback identity to exempt boot/fatal before any
guest. Add an execution test of the generated defer predicate, preserving both
enabled and disabled states. Reserve host15<=600s; diagnostic12 is still unused.

Host15 and diagnostic12 pass: old-profile case0/4GiB, both roots/eight exact
retirements16.882s with deferred pre-workload probes. The inherited plain
capture20s lease is too close to the measured19.866s full eight-slot proof;
select the EXISTING host-only service_pio_budget45s transport (42s capture/3s
cleanup) for hardware runs, within BY's frozen complete60s and480s aggregate.
No guest deadline/clock/CPU/profile changes; this flag is host observation only.
Candidate08 reserves the same five gates, one build and seven hardware guests.

## Acceptance, candidate08

All five frozen gates pass1.648/33.501/10.970/136.188/3.336s. Four new host tests
plus16 legacy tests pass; old default source projections and original artifact
pins match. Seven fresh WHPX guests pass at16.230/16.479/18.580/18.613/19.035/
18.738/16.475s, aggregate134.571s including complete replay;106 exact task
retirements. Independent review repeats the full PIO/lifecycle/ownership/heap/
frame-zero/media/raw hardware-bootstrap proof and checks unchanged artifacts.
Direct scope/ABI/cleanup review finds only the explicit BIND-v3 extension,
fixed64-byte state, exact-tag quota selection and bounded verifier changes.
Precommit seal b5f7f862b1a5d9a0879e3abb22c6fa09fdae46d4318a4d35b36237f31f085078.
No earlier failed candidate/diagnostic is reclassified. BY done; BV active
but still unaccepted, restored only after a clean local BY commit. No push.
