# Native bounded block-service profiles — R8.3ak

Frozen after accepted91401365 under continuous interactive completion authority.
20 allowed files,20 mandatory queue groups; this contract is not acceptance.

## Inventory and common boundary

The actual existing EXT2 parser reads a15-byte standard fixture file with ten
sector callbacks and nine distinct LBAs2,3,4,10,42,43,12,44,45 at O0/O2. Even
an ideal per-generation cache cannot fit this into the old eight-request block
session. No parser, Unicode reduction or cache trick fixes that lifetime bound.
The existing PIO adapter also indexes two task records with shl8 and checks
retirement at fixed512/768 offsets, incompatible with accepted1024-byte tasks.

Close these prerequisites together as one read-only block-driver lifecycle
boundary: explicit local session limits, wide-task ownership, build/SDK and
real fault/restart proof. Filesystem parsing/RPC is the next independent Ring3
consumer boundary, not part of this package. Reuse native_block/native_service,
PIO mediation and the existing image/task/IPC/fatal mechanisms; no kernel C,
common IPC, allocator, context, filesystem parser or disk format change.

## Standards, compatibility and bounds

ATA data-in/LBA28/512-byte sectors, the block RPC-v1 wire header, IPC v1/v2
envelopes and negative errno meanings remain as specified in
[the block contract](NATIVE_BLOCK_SERVICE_CONTRACT.md). No new syscall.

Old public structures, init/dispatch functions and their eight-request limit
retain layout and behavior. Add named profile entrypoints and a fixed24-byte
local REIST block profile-v1: u32 version1,size24,request_limit,reserved-zero;
u64 absolute deadline_ms. Admit limit1..16 and a deadline strictly after now,
at most3000ms away; reject overflow, stale/invalid values before init effects.
Snapshot the profile once for this service generation. It never travels in
an untrusted read request and is not a kernel capability or a larger CPU grant.

Keep exactly one authoritative request/sequence counter in the existing server
core. Factor one bounded dispatch implementation; the old wrapper supplies8
and no additional session deadline, while the new profile adapter admits its
snapshot and uses the same core. All incoming attempts count, including invalid
requests, up to the selected cap. Exhaustion and session expiry do not touch
hardware or publish data; no implicit reset, lease extension or same-generation
reinitialization in the service loop. Each real request still uses the existing
<=1000ms RPC deadline and <=200ms ATA wait; enforce the earlier session bound.
New service storage may embed the old service plus its profile, not a duplicate
server counter. No mutation of old layouts or aliasing a new protocol as v1.

NativeBlockProfile is a separate opt-in build profile: NativeWide+NativeImport
and the existing PIO/block transport. Plain NativeWide continues excluding the
old PIO/block fixtures; all old flags keep their meaning. Four task slots,
eight CREATE attempts/root,32 CPU samples,16 input words/PIO call,64 PIO calls
per100ms, IPC pools and all heap/image/stack bounds remain unchanged. Replace
only the identified PIO task strides/retired-slot offsets by native layout
constants. No broader device rights, second wait node, direct-map alias or
unbounded service loop. Standard objects must retain allocated bytes and
relocation semantics; explain any symbol-only object change exactly.

## Lifecycle and acceptance

Supervisor starts with explicit endpoint grants and binds the exact PIO owner;
numeric startup values grant no rights. The child waits boundedly for actual
delegation/bind, runs fresh IDENTIFY and full self-test read, and only then
publishes readiness. A selected nine-request profile proves nine real complete
reads in one generation and rejection of request ten before device effects.
An independent peer must survive. Reap/fence precedes replacement, which must
repeat self-test and read correctly; old endpoints/owners cannot regain rights.
Preserve the same detect/isolate/fence/reap/recreate/self-test sequence for
UD2 during data-in, sleeping hang, CPU spin, malformed reply and owner loss.
No successful16-read guest claim from the nine-read fixture: limits1..16 are
host-admission coverage, normal guest evidence is explicitly the chosen nine.

New host gates execute actual C block/profile/service and actual PIO task
adapters O0/O2, covering every limit, malformed profile, deadline/backward time,
single authoritative counters, all task slots/generations, denied old owners,
partial initialization, no-I/O/no-output error paths and cleanup. Negative
runtime oracles reject missing/duplicate/reordered/malformed receipts. Preserve
old block/PIO/program-memory/producer/ELF/ABI/documentation hosts.

Five builds: normal, NativeWide, NativePIO, NativeBlock, NativeBlockProfile.
New matrix11 guests: normal4/8GiB, UD2, sleep/cancel, CPU spin, bad reply,
missing medium, owner loss, and first-child OOM at0/half/last acquisition.
Use actual compiled acquisition count; exact frame ownership, mapped bytes,
permissions, queue/profile/IPC/heap/FP scrubbing and final balance are required.
Every normal/OOM success includes the ninth read and fresh replacement.
Each guest retains the existing20s transport ceiling, aggregate<=220s.
No increased clocks/deadlines to mask lost progress. Hidden QEMU only, original
media untouched; use existing generated read-only/COW fixture validation.

Keep all ten old block guests, thirteen wide-memory guests, nine fatal guests,
normal bootstrap and original i386 guard. The old block runner may accept an
explicit newly built PIO reference path instead of its fixed historical path;
validate the same inner/outer provenance and unchanged mechanism bindings.
Do not normalize arbitrary differences or compare an artifact with itself.

Compiler processes<=90s, host executables<=30s, bounded logs and callbacks.
All20 gates, direct scope/ABI/cleanup review and clean local commit precede
the next package. No agents/push. Retain all failed attempts. Stop at outside
scope, pre-existing failure, new quota/authority need or the same concrete
failure after two focused corrections; never retry unchanged until green.
R3.6b stays deferred; no filesystem, DMA, hardware or complete OS claim.
