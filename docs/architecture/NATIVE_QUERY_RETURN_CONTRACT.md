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
   desktop/both applications, no role loss and original pointer300ms check.
   Record abc300ms unchanged; its mandatory acceptance remains in CF by the
   explicit user approval2026-09-25 below. No finished OS claim without it.
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

## Development continuation 2026-09-25

Build04 adds a zero-byte admission label to avoid observer traps on every
same-task return. Guest03 missed the second cleanup observation; guests04/05
did not observe the eighth-query branch for both roots. All failures retained;
no runtime cap acceptance. Reserve one additional kernel build05<=300s for
the already frozen GUI comparison with the initial media/guest reservation.
Finite administrative extension only; no gate or runtime-limit change.

GUI attempt06 built successfully but media construction rejected FAT12 extent;
no physical guest launched. Exact CF overlays restored. Allocated ELF sections
have identical extents to CF68; added private symbol names enlarged the file.
Shorten private names only and verify identical allocated bytes. Reserve build06
<=300s with media02<=180s and guest attempt07<=600s; no format/safety change.

## Proposed gate allocation after GUI08 - awaiting user approval

GUI08 reuses GUI07 media without rebuilding; VM closed and exact overlays
restored, media hashes unchanged. Pointer300ms check passes, abc300ms fails.
Text receive audit contains a39500ms, b39600ms, c40150ms; final buffer is abc.
The client issues a complete begin/fill/hint/text/commit paint transaction
between event drains. Begin and commit await replies in surface_client.c;
this is an identified separate Ring3 latency path, not yet a measured sole cause.

Proposed CH gate5: still require original pointer300ms, real READY/stable
desktop and both clients, no role loss, byte-bound identical CF fixture and
unchanged media. Record original abc300ms failure without accepting it.
Keep all CH host/default/package/nine guest/replay safety gates unchanged.
Then locally accept CH only as a bounded query-return prerequisite and restore
CF byte-exact. CF retains the original mandatory abc300ms and pointer300ms
acceptance, and all startup/replacement/health checks; CB and actual VMware
qualification remain mandatory. Native OS/VMware completion requires them all.

This moves the remaining client-latency fix into its existing authorized CF
source scope, with one implementation package at a time. No runtime deadline,
CPU allowance, rights, protocol or final OS acceptance limit changes. CH gate5
is frozen, so do not apply this allocation without explicit user approval.

User approved proposed gate allocation2026-09-25: Ja, getrennt abnehmen;
alle endgueltigen Grenzen behalten. Apply allocation above to CH gate5/6;
CF retains both strict300ms GUI checks and all existing safety gates.

GUI08 consumed attempt08/physical guest07; media reused exactly, no build.
Reserve build07<=300s, hosts09..10<=180s, guest09/10<=360s each for the two
query cases. For these cases alone select QEMU instruction-counted TCG time
(-icount shift=3,sleep=on): debugger wall time must not manufacture guest IRQs
between queries. Guest PIT frequency, IRQs, quotas and limits stay identical.
All seven reference cases and GUI retain their existing timing backend.
Observe the actual eighth-query branch; do not remove that proof obligation.
This host-only clock selection is not desktop performance evidence.

Guest09 reached the actual eighth-query branch but transport cloning reread
the original file and lost existing357/360s host bounds. Failed29.335s retained.
Host09 now checks preserved bounds; helper explicitly clones all three changes.
Guest10 uses corrected transport for case8; reserve guest11<=360s for case9.
No image rebuild or guest limit change; no unchanged retry.
