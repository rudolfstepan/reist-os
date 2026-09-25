# Selected full-desktop CPU profile — R8.3cg

## Explicit authority and invariant boundary

2026-09-25 user approved separate compositor64 then explicitly answered
"Ja, Supervisor und Desktop jeweils64 freigeben". Only this selected profile
raises root/compositor budgets. Existing profiles and peer/service budgets stay32.
System V AMD64/ELF64 conventions, timer sample units and append-only REIST task
ABI apply; no real-time/utilization or completion claim. Ring0 composes existing
constant-time accounting and bounded admission; no policy, GUI or drivers added.

NativeDesktopCPU is explicit/default-off, requires NativeLargePeriodic and its
large-image/task-pool/service-CPU prerequisites. CREATE-v9 uses existing80-byte
periodic transport with RNPGv3, period1000ms and1..64 samples. Child<=immutable
periodic parent (1..64); v6/v8 children stay1..32, v7 remains lifetime-only.
Reject65, invalid/stale/underbudget/lifetime parent, bad period/reserved/profile/
pointers before any publication, allocation ownership or attempt charge.

Private plan-v6 retains336-byte/eight-slot layout but admits root slot0<=64;
all other initial/unused slots<=32. Root0 and peer1 retain period100 ticks.
Old plan-v5 and CREATE versions retain32 even in the selected kernel. No live
budget edits, epoch renewal, image/memory/IPC/display/IO/rights changes. Existing
scheduler quantum, exhaustion, fencing and idempotent cleanup remain mandatory.
Production full-desktop selection/integration belongs to resumed CF; CG's
controlled Ring3 fixture requests64 only for root0 and large compositor-role
child. Independent peer remains32. No permission to enlarge other services.

## Preserved work / transaction

Implementation base342b4ed6; clean worktree verified after preserving all19
attributed CF files in stash e5a1c1008004cbaa1af453a77224ef953615005f and
build/codex-agent/r83cf-desktop-startup/before-cpu-prerequisite01/files.zip,
SHA25680c47a8aa031a6e13fff21a293513d7c13ce01c3af5b6b8306c9bf44af084fbc.
CF unaccepted counters68 hosts/4 role builds/26 integration builds/media/39 VM
attempts remain spent, all failures retained. Restore source files byte-exact
then explicitly reconcile new CPU integration after CG acceptance; never apply
archived queue wholesale or claim CF/CB acceptance. No nested agent or push.

CG initial development reservation:12 hosts each180s;4 builds each300s including
preimplementation disabled NativeLargePeriodic baseline;8 diagnostics each360s.
Number every invocation, retain logs under build/codex-agent/r83cg-desktop-cpu.
Administrative extensions require evidence-directed scope review, not user yes;
new authority/scope still requires reporting. One implementation package active.

## Frozen gates

Execute once per frozen candidate, in order, stop on first failure:

1. `python test/test_x86_64_desktop_cpu.py -v` <=180s: actual assembly/core
   admission, accounting and dispatch, root-plan and SDK transport; old32/new64,
   65 rejection, malformed requests/parents, unchanged state on reject, finite
   epochs/counters, no skipped-period loop; enabled/disabled selectors.
2. `python scripts/verify_x86_64_desktop_cpu.py --defaults` <=600s: fresh disabled
   NativeLargePeriodic build executable/image bytes equal preimplementation
   baseline; old-version behavior in selected host tests. Preserve whole binary
   evidence, never normalize executable bytes or accept debug stripping.
3. `python scripts/verify_x86_64_desktop_cpu.py --package` <=600s: selected
   reference build, actual plan/ABI/layout validation, immutable artifact hashes.
4. `python scripts/verify_x86_64_desktop_cpu.py --runtime` <=3000s: seven fresh
   guests <=360s each/2520s aggregate: cross-period large child with cumulative
   samples>64, child64 exhaustion, cancellation/reap, partial OOM rollback, high
   RX denial, guard fault, root64 exhaustion. Distinct replacement generations
   where parent survives; root exhaustion fences/reaps whole family. Independent
   root/peer progress and bounds remain observed, no kernel corruption/reboot.
5. `python scripts/verify_x86_64_desktop_cpu.py --review` <=1200s: independently
   replay actual raw CPU/task/plan/PTE/ownership/cleanup records; bind exact
   source/tools/commands and images, reject corrupted evidence. No markers-only
   proof. Carry unchanged mechanisms only with exact source/evidence binding.

After all gates, direct scope/ABI/cleanup diff review and local clean commit,
resume CF for actual GUI/input/apps/replacement/start deadline and VMware gates.
CG acceptance alone is not a working native64 VMware desktop.

## Development ledger (2026-09-25, unaccepted)

Build01 disabled baseline succeeded before source edits (6.082s, HEAD ed1bba6b).
Host01 failed: test passed the wrong charge timestamp and incorrectly expected
terminal exhaustion to renew. Oracle corrected to the actual core contract.
Host02 exposed the missing selected parent64 attenuation; implementation added.
Host03 passed O0/O2 selected and disabled admission/accounting.
Host04 passed four O0/O2 groups, adding real SDK80-byte transport, all partial
request preflights, RNPG dispatch/copy and periodic publication (5.806s).
Build02 selected CPU64+trace succeeded. Build03 disabled comparison found NASM
macro invocation IDs changed symbol bytes even with identical instructions;
macro calls now exist only under the selected flag. Build04 disabled matches
55/56 complete artifacts, including linked kernel and scheduler object. Only
root object differs because its generated header has a different directory.
No binary stripping or normalization accepted. Exact-header recompilation next.

Initial4 build reservations spent; evidence-directed continuation reserves
build05..08 (each300s): exact-header root comparison, extended selected workload
and at most two source-directed corrections. Hosts4/12 and guests0/8 spent.
No frozen gate has run. No GUI/VMware or package acceptance is claimed.

Build05 exact-header full root object comparison passed. Build06 selected longer
normal workload passed. Guest01 failed at live-plan validation after CREATE:
initial-slot32 admission was also used for an already admitted child64. Added a
separate internal live-plan entry: peer1 stays32, child64 requires period100 and
child<=immutable root, initial/unused admission remains32. Existing generation,
ownership and whole-run checks still apply. Host05 passed regression O0/O2.
Build07/guest02 passed normal cross-period proof51.784s; totals143,137,134,124.
Build08 adds deliberate root exhaustion after live child proof. Guest03 passed
14.151s: roots1/4 reach64 in their window, children3/6 cancelled and reaped,
peers2/5 exit77, all frame/heap/profile/IPC/FP/queue cleanup replayed.
Development now5/12 hosts,8/8 builds,3/8 guests spent. Guest01 failure retained.
New selected fixture work and observers remain unaccepted until frozen gates.

## Acceptance

All five frozen gates passed in qualification01, including seven fresh guests,
full raw ownership/CPU replay and six deliberate evidence corruptions rejected.
All56 disabled artifacts match baseline (root object with identical header path).
Acceptance seal SHA256 52d6948f20726a00ac0bb73fbd354a7e602dbeac51b795af99e121a5d16fbf8d.
Direct diff review covered ABI append-only transport, initial versus live plan
admission, default-only macro expansion, bounded accounting and complete cleanup.
No authority, quota period, timeout or gate was weakened. CG done; resume CF.
This accepts the CPU prerequisite only, not GUI/VMware/native64 completion.
