# Periodic large service import — R8.3cd

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
