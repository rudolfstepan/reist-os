# Native Ring3 read-only filesystem contract

R8.3al, frozen on clean accepted `3cd8fe87`. This is an explicitly selected
native service qualification profile, not an accepted normal OS, shell command,
writable filesystem, hardware target or POSIX binary-compatibility claim.
The interactive main agent executes the queue's nineteen frozen groups,
reviews scope and commits locally only after every gate passes. No agents/push.

## One immutable-media failure domain

Root0 is client/supervisor, root1 the independent essential-function witness.
Dynamic task2 is the existing bounded ATA PIO block driver; task3 runs the
existing FAT12/FAT32 and EXT2 parsers with a native read-only adapter. No parser
or new authority enters Ring0. The filesystem has no DEVICE_CONTROL/PIO or
TASK_CONTROL grant. Preserve exact task, address-space, capability and image
generations, Wide W^X/private-frame ownership, copied source and stack guards.

Each dependency group has one driver and one filesystem lifetime, then at most
one replacement group. Failure means detect, deny publication, fence/revoke,
reap both dependent processes, recreate, fresh driver IDENTIFY/LBA0 and
filesystem root self-test, then reintegrate. A malformed medium remains degraded;
it is not repaired. The supervisor and unrelated peer must survive a component
failure; root owner-loss deliberately terminates its children and leaves the
independent peer. No claim that storage remains available while it is isolated.
This profile does not add an alternate manual recovery bypass or `svcctl` command.

IPC remains two-party: the driver creates and owns its request/reply endpoints
and explicitly delegates SEND/RECEIVE to the exact live FS generation. Separate
root-owned control endpoints carry bounded startup/health handshakes. Do not
delegate a root-owned block endpoint to two peers (existing IPC rejects that),
relay filesystem data through the kernel or infer authority from a numeric PID.
All channels and cached data retire with their owning generation.

## Standards and local adapter

Media terminology and layouts follow the Microsoft *FAT Specification v1.03*
(FAT12/FAT32 BPB, cluster thresholds, short/LFN names) and the Linux kernel
EXT2 filesystem documentation (little-endian superblock at byte1024,
1/2/4KiB blocks, inode/directory and feature fields). Reuse existing supported
subsets, Unicode15.0 NFC/case-folding, directory and chain bounds; do not silently
accept unsupported features or describe this as exFAT or an EXT3/4 journal.

References: [Microsoft FAT v1.03](https://www.cs.fsu.edu/~cop4610t/assignments/project3/spec/fatspec.pdf),
[Linux EXT2 documentation](https://www.kernel.org/doc/html/latest/filesystems/ext2.html).

Reuse the existing fixed512-byte VFS stat/read-at/readdir-at payload layouts,
operations5/6/7, path192 and read256 limits, units and result semantics.
A separately named native filesystem RPC-v1 envelope carries version/size,
operation, flags, exact FS owner, monotonically increasing sequence, immutable
absolute monotonic deadline, length/status and zero reserved fields. It uses
existing bulk IPC, not STORAGE_SUBMIT/COLLECT, and is not a new syscall or wire
compatibility alias. Header64 plus payload512 fits existing2048-byte bulk IPC.
Admit complete header, payload, padding, owner, sequence and deadline before any
read or publication. Client output remains unchanged on any rejected response;
valid data is published only after exact response matching. Transport/protocol
faults poison the generation; normal bounded filesystem errno is not corruption.

## Bounded read path

No heap allocation in the reusable FS adapter. At most16 fixed512-byte sectors,
no eviction, tied to exact FS/block owners, selected immutable-media geometry
and one session deadline; zero at initialization, invalidation and retirement.
Check monotonic progress/deadline even on cache hits. A backend error, stale
reply, quota or deadline failure denies further generation use; partial data
cannot be returned as success. New generations must perform fresh self-tests,
not inherit a mount or cache merely because an LBA is the same.

FS sessions admit at most8 requests and an absolute future deadline at most
3000ms. Every physical read uses the existing block RPC and at most1000ms,
bounded by the remaining FS session. The driver keeps the accepted explicit
profile of at most16 requests and3000ms,32 CPU samples per task,16 words per
PIO read,64 operations/100ms,8 CREATE attempts/root and existing IRQ/clock rules.
No quota increases or busy waits. Capacity exhaustion is an explicit failure,
not permission to restart invisibly until an operation succeeds.

Existing EXT2 regular-file reads currently fetch whole data blocks: actual
short-file inventory costs9/13/21 distinct sectors for1/2/4KiB. Read only the
sectors intersecting the requested regular-file range, after retaining complete
inode/block/volume admission. Keep metadata/directory parsing unchanged, EOF,
errno, supported block mapping and public zero-on-failure semantics. Exercise
cross-sector/block offsets, maximum offsets, rejected geometry, every injected
read failure, sparse/unsupported mappings and old guarded/object consumers.
No journal, mutation ordering, persistent format or recovery-policy change.

## Build and frozen acceptance

`-NativeFilesystem` and the corresponding Make variables explicitly select the
new Wide+Import+PIO+BlockProfile consumer; existing/default branches and artifacts
remain byte-bound to `3cd8fe87`. Build both independent child ELFs before root
embeds their immutable raw inputs. Preserve producer admission, stack layout,
linker capacity and both Windows/Make selection/negative validation. Do not
introduce a command reachable only from the kernel rescue shell.

Twelve targeted groups cover actual O0/O2 adapter behavior and parser ranges,
generated-media geometry and COW safety, runtime-oracle negatives, old FAT/EXT2,
block profile/PIO/producer/native IPC, syscall ABI and documentation. Three
builds: default, old BlockProfile and new Filesystem. Four runtime groups:
new matrix, old full BlockProfile11, default boot, original i386 artifact guard.
Keep failed attempts and exact source/artifact/gate bindings under ignored
`build/codex-agent/r83al-filesystem/`; no historical source-only pass is runtime
evidence. Direct final scope/ABI/cleanup/default-object review is mandatory.

New matrix: eighteen sequential guests, each20s maximum, aggregate guest time
at most360s, one CPU, explicit4GiB (plus one8GiB EXT2 reference), no visible VM.
Five normal layouts (FAT12/FAT32/EXT2 1/2/4KiB) plus the8GiB reference; six
reference1KiB fault cases (FS UD2, sleep/cancel, CPU spin, malformed reply,
driver UD2, supervisor owner loss); three FS CREATE OOM points0/mid/final;
malformed FAT12/FAT32/EXT2-4KiB media. Two real PROCESS_RUN invocations each;
normal/fault/OOM cases require replacement and fresh generation self-test,
owner loss requires complete descendant retirement, malformed media requires
bounded degraded exit without read publication. The same unchanged disposable
generated medium is used throughout a guest; no data repair between lifetimes.

Observe actual physical PIO bytes against independently generated sectors,
complete RPC/path/data/sequence/deadline matching, all published task pages,
immutable input copies, private frames/stack guards and rights, every retirement
and frame balance, IPC/heap/FP cleanup, physical fencing and full trace clear,
both caller returns and the independent peer. Preserve every relevant assertion;
scope dormant GDB page-sharing hooks to their actual lifecycle as established
by R8.3ak, never compensate with guest clock/quota changes. Oracle mutation
tests must reject missing, stale, duplicated, reordered or altered evidence.

Only generated read-only base images under unique ignored evidence folders;
an exclusive disposable qcow2 layer is permitted solely for QEMU IDE metadata.
Explicit finite layout selectors, no arbitrary image bytes/path/QEMU arguments,
base at most70000*512 bytes, overlay at most4MiB. Verify exact generated bytes,
backing identity, virtual size, full depth1 map, zero allocated overlay data and
logical equality before and in finally after every guest, including failures.
Preserve old64KiB media profile defaults and all original evidence/pins.

Stop on a required file outside the frozen22-file allowlist, new authority or
persistence boundary, unrelated changes, pre-existing source failure, or the
same concrete frozen failure after two focused corrections. No unchanged
runtime retry or diagnostic-only acceptance. Deferred R3.6b stays deferred.
