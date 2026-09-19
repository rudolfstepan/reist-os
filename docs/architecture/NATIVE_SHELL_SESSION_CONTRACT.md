# Native shell/service session v1 — R8.3ay

Frozen19 September2026 after clean AX69282e7613a67263beb7e659d5675b8301066e7d.
AX final receipt231d1df92e6eedf2ded04fd3a1bb5de14439a902d51db156ab66a2b96c9d7c13
qualifies periodic construction, not an interactive system. The existing user
authority explicitly permits a separately versioned persistent shell/supervisor
profile, fixed per-window creation/restart budgets and generation recovery.
One main-worktree package; no agents, push, physical media or R3.6b work.

## Cohesive boundary and inventory

Compose the actual userspace/bin/shell.c and shell_vfs.c with a distinct native
platform adapter and Ring3 dependency supervisor. Bundle namespace lookup,
STAT-to-ELF capture, spawn/identity/terminal/wait, service retirement/recreation
and console lifetime: these share one root-owned publication/rollback boundary.
Do not split media variants or individual SDK stubs into extra packages.

Existing mechanisms: AX root0 eight construction attempts/1000ms, periodic
CPU32/1000ms, eight task slots; AV exact-generation foreground lease; AW
shared-deadline STAT/file capture; real Ring3 ATA and FAT/ext2 FS services.
Existing services retain their finite profiles: ATA2800ms/16 requests,
FS<=3000ms/eight requests, IPC<=1000ms, ATA operation<=200ms. The existing
filesystem.c qualification owns fixed slots2/3 and embedded service ELF files;
extract/reuse its healthy lifecycle rather than move a driver/parser to Ring0.
Its fault workload and all old selectors stay independently reproducible.

Current normal native shell is console-only with an absolute1000ms whole-task
limit and explicit -38 namespace/spawn/wait/identity stubs. Native GETPID is the
positive, nonreused generation, not the task slot. Kernel native syscall114 is
not yet bound: an SDK cache must not fabricate a live process identity.

## Standard-first interface

Preserve System V AMD64/ELF64, existing public syscall numbers and structures,
negative errno, conventional .prg search and the existing real shell dispatcher.
Use existing PROCESS_IDENTITY114 with its established pointer/PID arguments and
16-byte v1 output. The explicit new root profile may query self and its own
live children only; foreign/stale/retired identities fail without publication.
Validate complete writable output, exact generation, parent and all unused
registers before the single publication. No general process-table disclosure,
child TASK_CONTROL inheritance or new device authority. Old profiles deny it.
The bounded eight-slot query is a kernel mechanism, not Ring0 process policy.

Use existing TASK_CONTROL132 CREATE/WAIT/CANCEL, terminal127/v1 and immutable
FS RPC. New private session policy is version1; no POSIX/whole-userland
compatibility claim. Only actual mounted immutable generated media may supply
cwd, drive and directory metadata. No synthetic successful filesystem, resident
program fallback, fabricated child or terminal success. Unsupported USB/network
remain explicit unchanged errors. No new shell command in this package.

## Lifetime, authority and recovery

NativeShellSession is separate from old NativeShell, NativeSession and
NativeTerminal qualification selectors. Root0 is the shell and owns its bounded
Ring3 supervisor state; driver/FS/application remain separate processes. Root1
is an unrelated bounded peer. Root loss invokes existing physical fencing and
descendant retirement; this package does not claim automatic root replacement
or whole-system recovery from the bootstrap's second qualification run.

No whole-session1000ms exit in the new profile. Instead fixed anchored1000ms
windows admit <=4096 adapter operations, <=1024 input bytes and <=16384 output
bytes, with monotonic/cumulative overflow checks and no idle credit. Each I/O
operation remains bounded at <=1000ms and each input read at <=64 bytes. Polling
uses actual blocking sleeps; the native input wait may select100ms in the new
profile, explicitly documented as console latency, not silently lengthening a
requested sleep. Preserve old10ms behavior outside this profile. CPU32/1000ms
is unchanged. Quota/clock/backend-integrity failure stops only this root and
lets kernel fencing/reaping contain its children; no busy retry or reset.

The supervisor has fixed state for one driver, one FS, one foreground child,
one canonical cwd and one pending STAT observation. Allocate bounded prepared
image/workspace only in ordinary Ring3 context and release them on every exit.
Per-operation deadlines never extend on intermediate success. Only a matching
current-generation/path STAT may feed AW capture; stale, consumed, failed or
capacity-insufficient observations are rejected or explicitly start a separate
fresh operation after retiring the old dependencies, never reset a client.

Start dependencies in order, bind PIO, validate complete actual self-test replies
and only then publish healthy FS. Creation attempts also consume AX's kernel
budget. No opportunistic repeated spawn on EAGAIN. A command may report EAGAIN
and leave the shell usable. A service lifetime/request boundary triggers bounded
planned retirement and new generations before a later command, not renewal of
the old profile. Keep old-generation counters/receipts diagnosable.

Crash, hang, malformed reply and quota failure use the same transaction:
detect -> isolate -> physical PIO fence -> cancel/wait/reap dependents -> close
endpoints -> recreate -> actual self-test -> reintegrate. At most two automatic
recovery attempts in an anchored10000ms window, one retry per failed user
operation, and cumulative attempts never reset. Exhaustion latches DEGRADED;
window expiry alone does not clear that latch. Console HELP/PATH/HISTORY remain
usable; filesystem operations return a real unavailable error. No new manual
recovery command or administrative budget bypass. Unknown cleanup/fencing
result terminates the root so the kernel's existing containment completes.

Foreground app receives only explicit attenuated ordinary/terminal rights,
never FS endpoint, PIO or task management. Exact identity precedes terminal
transfer. Ordinary wait is bounded1000ms; timeout cancels and boundedly reaps
before returning an error. Exit/crash/quota/cancel restores terminal authority
through AV, never SDK bookkeeping alone. Stale handles cannot regain authority.

## Frozen verification and reservation

Regression-first actual C/assembly O0/O2 tests cover adapter outputs unchanged
on failure, all quotas/windows/clock overflow, actual normal shell dispatch,
five media layouts, observed STAT/shared deadline, generation/identity/pointers,
cleanup/fencing order, partial construction, stale replies, restart exhaustion,
terminal ownership and old-profile equivalence. Source patterns supplement,
never replace executed behavior. No new complex Ring0 driver/parser.

Freeze exactly ten gates from the queue: AY host behavior, existing native shell
hosts, existing normal shell/lookup hosts, retained subsystem hosts once via
one manifest, default/ABI/scope proof, one common Windows image, runtime matrix,
protected references, full raw review, final direct scope/bounds review.
Host command ceilings300s (retained manifest900s), build180s, runtime900s,
other gates180s. One build/image, eighteen fresh guests at45s maximum each
including cleanup<=3s,810s summed guest ceiling. Stop at first failed gate/guest;
no unchanged retry, in-window repair or further image. Preserve all counters;
separately freeze any evidence-directed correction under standing authority.

One image covers five healthy immutable media layouts,8GiB, input idle beyond
old lifetime, >eight cumulative constructions, real ordinary file execution,
driver/FS UD2 and hang, malformed reply, app UD2/quota/cancel, owner loss,
recovery-budget exhaustion, partial-construction OOM and stale/foreign authority.
Each declared runtime claim needs actual raw request/return, generation, CPU,
memory/FP/IPC/heap/frame/PIO/terminal and byte-stream proof with independent
kernel/high-RAM memory equality. Serial success alone is insufficient.
Capture feeder may add an explicit bounded session mode for the new profile;
old feeder/defaults, per-guest limits and assertions remain exact.

Exact matrix (4GiB unless noted):0..4 healthy layout0..4;5 healthy layout2 at
8GiB;6 layout2 idle and repeated commands spanning>=5000ms and>eight cumulative
constructions;7 driver UD2;8 driver hang;9 FS UD2;10 FS hang;11 malformed FS
reply;12 app UD2;13 app CPU exhaustion;14 app cancel;15 root owner loss;
16 restart-budget exhaustion;17 partial-construction OOM. Cases7..17 use
layout2. Healthy and fault cases include stale/foreign identity/terminal
rejection, independent peer progress and bounded generation cleanup. Each
fault proof must observe the actual triggering event, not a scripted status.

Before done: all ten gates, exact source/tool/command/image/raw bindings,
direct ABI/failure/bounds/cleanup review and clean local implementation commit.
Then continue the next native priority without routine handoff. This is not
signed normal boot, complete desktop/browser or physical-platform acceptance.
