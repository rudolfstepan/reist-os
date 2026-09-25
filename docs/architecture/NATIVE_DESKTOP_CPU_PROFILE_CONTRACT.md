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
