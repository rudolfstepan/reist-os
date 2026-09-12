# Native task family boundary

R8.3ae, frozen on cbe5b956, 12 September 2026. This is an implementation
contract, not accepted runtime evidence. Queue gates are authoritative.

Renewed user instruction on12 September after the explicit blocked-path
question authorizes correction of the relative evidence directory and renewed
full verification of the same attributed candidate. Resolve and validate the
directory inside build/codex-agent before building variants. Preserve failed
evidence, all17 gate groups and the original one-focused-repair stop condition.

## Standards and authority

Use the existing SysV AMD64 transport and ELF64 prepared-image mechanism.
POSIX spawn/wait terminology and errno categories inform the adapter, but
TASK_CONTROL132 is explicitly REIST-specific: immutable admitted image IDs,
generation-bearing handles, bounded waits and packed terminal receipts.
SPAWN23, WAIT24, KILL27 and SPAWNV30 keep their existing meaning. No kernel
pathname resolver, user ELF parser, implicit capability or compatibility claim.
The first family profile starts children with the admitted catalog arguments;
arbitrary file execution and caller-supplied argv remain a Ring3 loader boundary.

The public v1 request is64 bytes: version/size/operation/flags (four u32),
target/image/timeout_ms/syscalls/cpu_samples/reserved (six u64). Flags and
reserved are zero. CREATE1 requires target=0, image3..6, timeout=0, an admitted
attenuated low64 syscall mask including EXIT and CPU samples1..32. Return an
opaque positive generation32:slot32 handle. WAIT2 requires target, timeout1..1000ms,
other payload fields zero; return reason32:status32 after complete retirement.
CANCEL3 requires target and all other payload fields zero; it requests fencing,
not synchronous reclamation. Reasons are EXIT0, FAULT1, CANCEL2, OWNER_LOSS3.
Negative errno distinguishes malformed requests, bad user memory, denied
authority, foreign/stale children, exhausted capacity/budget, OOM and timeout.
A timed-out wait neither kills a child nor consumes its eventual receipt.

## Single failure and ownership model

NativeLifecycle is opt-in and presets NativePrograms/Runtime/Heap/IPC/RAM.
Private run-v3 retains144 bytes and declares two root slots plus two dynamic
slots. The four descriptors remain fully validated. Version1/2 are unchanged.
New private multiword profiles bind the entire mask to the task generation;
the legacy16-byte profile entry remains available for the old adapters.
Only root generations receive TASK_CONTROL; children cannot delegate it.

Each root has eight creation attempts for its entire generation, including
construction attempts that fail after reservation. No wait, cancel, yield,
sleep or child replacement replenishes this budget. CPU samples remain1..32
per generation. Two independent roots share the original four task slots;
unclaimed terminal receipts retain slots but never frames. All creation,
wait, cancellation, orphan retirement and slot reuse belong to this package.

Construction validates before publication, uses the existing prepared pages,
private stack, CPU/profile/identity and frame ownership, and rolls back partial
acquisitions. Execution is published only after IPC and heap binding. WAIT
stores one generation-scoped pending target and finite monotonic deadline,
using the task's existing sole wait node. Terminal completion wakes only the
matching owner. Expiry removes exactly that wait and returns ETIMEDOUT.

Cancellation and root termination fence runnable, sleeping and IPC-blocked
children before resource reuse. Queues, profiles and IPC are revoked before
the existing bounded heap continuation and13-frame retirement. There is no
kernel-stack continuation across a wait. Orphan receipts are discarded only
after their exact child generation has retired. Stale handles cannot acquire
authority over replacement generations. Exhausted creation budget returns
EAGAIN; service restart/reintegration policy remains in Ring3, not the kernel.

## Frozen verification

Production assembly host tests at O0/O2 cover admission, multiword authority,
owner/generation transitions, quotas and nonmutation. Independent oracle
negatives accompany real hidden QEMU4/8GiB guests covering ordinary and
faulted children, bounded WAIT/timeout, cancel, owner loss, peer continuation,
generation reuse, failed construction and exact final IPC/heap/frame cleanup.
At most20s per new guest. Preserve old guest bounds and pinned i386/media.
All17 gate groups must pass before implementation commit; no scope expansion,
quota change, Ring0 policy/driver shortcut, nested agent, visible VM or push.
