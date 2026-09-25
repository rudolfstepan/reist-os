# Bounded native query return — R8.3ch

## Authority and preserved candidate

User explicitly approved the concrete query-return proposal on2026-09-25.
CG fa790cf0 remains accepted. CF is queued, not accepted; preserve all21 files
in build/codex-agent/r83cf-desktop-startup/before-query-prerequisite01/files.zip,
SHA2564219e710cc0c2acb08d6cd0f3ffd0a6f31685cecd2222997024b497404fe2eda,
stash0316372f64818a18832ec45f52753876423ad47b. CF counters113 hosts/4 role builds/
45 integration builds-media/68 guests remain spent. Restore CF source bytes
exact after CH acceptance, reconcile only queue/docs; never restore queue
wholesale or call failed diagnostic evidence acceptance. No agents or push.
Main worktree clean after archived stash, HEAD ec8b1a69 at scope definition.

## Mechanism and scope

POSIX clock_gettime/getpid versus explicit sched_yield provide the reference
semantics; REIST syscall numbers/layout/error results stay unchanged, no POSIX
ABI compatibility claim. Existing MONOTONIC_MS/GETPID both enter the full
READY/enqueue/dispatch path, including whole process/lifecycle validation.
Source evidence establishes that path, not yet its measured latency share.

Only REIST_NATIVE_DESKTOP_CPU selects the new behavior, using its existing
full-desktop and qualification integrations; defaults unchanged. Successful,
fully argument/profile/context-validated queries may return to the same
RUNNING slot/generation through existing context-save and validated user-entry
machinery. No direct SYSRET shortcut or bypass of RIP/RSP/CR3/FP checks.
Fixed complemented state binds current dispatch slot/generation and remaining
burst. Initialize on ordinary validated task admission; clear on ordinary
dispatch. Seven direct query returns maximum; eighth query must enqueue and
dispatch normally. Invalid/corrupt/stale state fails closed. YIELD, errors,
blocking, IPC/devices, exit, fault and IRQ preemption retain ordinary paths.
No new task rights, CPU allowance, quantum/deadline, queue capacity or restart
budget. Existing timer-based CPU accounting and preemption remain mandatory.
Generation reset and final cleanup must leave no live burst ownership.

Frozen source scope is the queue allowed_files. Private assembly/header and
host tests implement/check the fixed budget; scheduler/process adapter owns
return wiring; large_image.c supplies selected qualification-only query-flood
cases, with old/default cases unchanged. New verifier/observer reuse existing
build/CPU/recovery tooling and retain all raw logs. No CF implementation edits.

## Bounded development reservation

Initial12 host invocations<=180s,4 kernel builds<=300s (including disabled
preimplementation baseline), two GUI media builds<=180s, ten diagnostics
<=360s each (GUI<=600s). Number and preserve every attempt under ignored
build/codex-agent/r83ch-query-return. Evidence-directed finite administrative
extensions are autonomous; no unchanged retry until green or counter reset.
Acceptance gates below are separate, once each per frozen candidate. Scope,
source/tool/image bindings and final diff review precede candidate commit.

## Frozen gates

1. python test/test_x86_64_query_return.py -v <=180s. Execute actual production
   assembly budget/owner/corruption transitions at O0/O2, finite cap, rejected
   mutation, generation reset, plus selected/default adapter integration.
2. python scripts/verify_x86_64_query_return.py --defaults <=600s. Fresh disabled
   NativeLargePeriodic artifacts byte-identical to preserved preimplementation
   baseline; exact same-header-path object comparison where tool DWARF embeds
   random path. Never strip/normalize executable evidence. Selected old calls
   and error/YIELD routes retain their results and scheduling boundaries.
3. python scripts/verify_x86_64_query_return.py --package <=600s. Selected build,
   ELF/layout/plan validation, source/tool/artifact identities, protected kernel
   mechanism only, bounded state and no unapproved profile changes.
4. python scripts/verify_x86_64_query_return.py --runtime <=3600s. Nine fresh
   guests <=360s each/3240s aggregate: preserve seven CG lifecycle/CPU cases
   (normal cross-period, child/root exhaustion, cancel/reap, OOM rollback, RX,
   guard) and two query cases covering values/invalid args/cap/peer progress
   and query-flood IRQ preemption/CPU exhaustion. Exact generations, context,
   queue/frame/IPC cleanup; capped read-only observations, not inferred counts.
5. python scripts/verify_x86_64_query_return.py --gui <=1800s. Byte-bound CF
   archive as read-only integration fixture, not accepted CF implementation.
   Preserve baseline68 images and original strict pointer/abc300ms failures;
   build selected candidate with identical CF sources/profile/media setup and
   run original uninstrumented input checks. Require actual READY/stable real
   desktop/both applications, no role loss and both original300ms checks.
   Compare baseline and candidate timing/pixels without weakening the oracle;
   if no safe benefit, do not accept the prerequisite as fixing responsiveness.
   Temporary fixture overlays byte-restored; no actual VMware claim.
6. python scripts/verify_x86_64_query_return.py --review <=300s. Independently
   replay every raw binding/result and corruption rejection; exact default
   bytes, all nine case obligations, GUI originals, state cleanup, frozen
   source scope and queue transition. No partial proof or host-only runtime
   claim. On success local commit only, then restore/resume CF gates and CB.

A/B GUI acceptance here does not waive CF startup/replacement/health gates,
CB services/lifecycle tests, or actual VMware visual/performance qualification.
