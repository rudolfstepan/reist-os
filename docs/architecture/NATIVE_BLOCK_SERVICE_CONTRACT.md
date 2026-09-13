# Native read-only block service boundary

R8.3ai, frozen on accepted7f452faf, 13 September2026. Queue gates are the
acceptance authority; this document is not a full OS or runtime success claim.

## Inventory and scope

R8.3ah provides full192-bit profiles, read-only generation-owned PIO, reusable
Ring3 ATA IDENTIFY/READ SECTORS, family retirement and common fatal fencing.
Native IPC already supports explicitly delegated rights and fixed140-byte v1
or2060-byte v2 envelopes. Existing storage_service.c depends on i386 request
pools/VFS and includes writable maintenance; do not move those into Ring0 or
pretend that compiling its header ports that service.

Bundle the reusable client, request/reply admission, bounded service dispatch,
actual Ring3 ATA service adapter and IPC/fault/restart proof. This is one block
service failure boundary, a prerequisite of later Ring3 filesystem consumers.
No new shell command, filesystem parser, kernel syscall or disk-write authority.

## Standards and versioned transport

Preserve the existing STORAGE_BLOCK_READ operation1,512-byte block size, sector
offset/LBA units and negative errno categories from the storage SDK. ATA data-in
follows the established references in ATA_PIO_TRANSFER_CONTRACT.md; only the
already admitted primary-master LBA28/READ SECTORS/IDENTIFY profile is used.
The kernel request-pool API is NOT aliased onto this different transport.

Name it REIST native block RPC v1. A fixed64-byte header has four u32 fields
(version1,size64,operation1,flags), four u64 fields (service owner handle,
nonzero sequence,LBA,absolute monotonic deadline_ms), u32 length, i32 status
and one reserved-zero u64. Requests use flags0,length512,status0. Replies use
flags1 and echo exact generation,sequence,LBA,deadline. Success has length512,
status0 plus exactly512 data bytes; error has length0, negative allowed errno
and no data. Reserved and unused transport bytes are zero.

Requests use the existing IPC v1 envelope with length64; replies use v2 with
length64 or576. These are explicit IPC payloads, not new syscalls. A client has
one in-flight request and monotonic sequence; a service accepts exactly the next
sequence for its own generation. Replays/stale owners, invalid widths/versions,
wrong lengths, future or expired deadlines, invalid LBAs and malformed replies
fail before hardware effects or client output. No output byte changes on error.
All transport operations share a monotonic deadline at most1000ms away; no
unbounded wait, background retries or lease extension after progress.

## Service authority and lifecycle

Each generation starts with explicit request-receive/reply-send endpoint grants
and exact PIO ownership. Numeric arguments create no rights. It must perform
fresh IDENTIFY and a complete self-test sector read before readiness is accepted.
A session handles at most8 incoming requests, including malformed ones, with
fixed buffers, fixed CPU budget and bounded idle/transfer deadlines. One service
generation never inherits the preceding generation's readiness or sequence.

Pace consecutive reads with monotonic Ring3 sleep so the already accepted64
PIO operations/100ms quota is respected; do not increase it. ATA wait remains
200ms/finite polls. Four task slots, eight root creation attempts,32 CPU samples,
eight image pages and one4KiB user stack stay unchanged. An opt-in service ELF
may use a second RX page within that existing image capacity; old layouts and
the private C payload layout4 remain unchanged.

Crash during transfer, sleeping hang, CPU spin, invalid reply, owner loss and
normal exit use existing fence/revoke/reap/recreate/self-test transitions.
Client outputs remain unpublished until a complete exact reply is validated.
No replacement before old task retirement; stale endpoint grants and ownership
cannot regain authority. Automatic and explicit recovery use the same state
machine and lifetime attempt budget. Exhaustion leaves the domain fenced.
This is not a system-wide supervisor or persistent indefinitely-running daemon
claim; scalable service budgets are a later explicit lifecycle boundary.

## Frozen proof

Host O0/O2 executes actual C client/dispatcher and service adapter with bounded
transport/clock/ATA witnesses: every malformed field, stale/replayed sequence,
deadline boundary, partial/error response, quota and untouched output. Negative
oracles reject missing, duplicate or reordered runtime/fence/data evidence.

Ten hidden QEMU guests: normal4/8GiB; OOM0/1/2/3/6/9; missing media; owner loss.
Normal cases include actual repeated RPC reads of distinct LBAs and their full
known512-byte payloads, invalid requests and replies, UD2, sleeping/CPU faults,
new-generation recovery, unrelated peer progress and exact frame/IPC cleanup.
Use only exclusive generated64KiB COW fixtures with a fixed per-LBA pattern,
read-only base nodes, unchanged hashes/logical data and no allocated overlay data.
All kernel mechanism objects must equal accepted PIO; no observer changes to
kernel state except explicit fixed OOM injections. Twenty seconds per guest.
Old PIO10/fatal8 and normal bootstrap plus qualified i386 pins remain gates.
All16 groups and direct review precede local commit; no agents or push.

Keep historical vector20/observer failures and R341-H1/H2 visible. R3.6b stays
deferred. No full native OS, physical hardware, DMA, writable recovery or system
timing/stability acceptance is implied by this service package.

## Candidate evidence boundary, 13 September2026

Renewed user authority permits continuous bounded measurement/kernel-cost
diagnosis and corrections. First compare the same exact image and catalog in
at most four20s diagnostic COW guests: detached, minimally connected, full
instrumentation and one targeted counter profile. Diagnostic outcomes never
replace the16 frozen gates. Add diagnose_x86_64_block_costs.py and the shared
capture module to scope,24 files. Do not change CPU/PIO/deadline limits, QEMU
clock rate, kernel state or mechanism objects. Read-only kernel path analysis
is permitted; a demonstrated necessary mechanism correction must first receive
an explicit failure-boundary contract and regression gates. Keep all historical
failures and correct only attributable causes, without routine handoffs.

Implementation is uncommitted on17954988. Actual C O0/O2 and the NativeBlock
build pass, but the first fully observed4GiB guest reaches its32-sample budget
during the second valid RPC. No new guest case is accepted. A prior detached
debugger diagnostic completed the intended service lifecycles; this is not a
substitute gate and used a different candidate than subsequent journal probes.
The candidate fixed Ring3 PIO-return journal, physical reset-OUT return probes
and generation-gated startup observer are still unaccepted instrumentation.
No kernel mechanism or frozen quota has changed. Preserve all failed evidence;
no commit/queue transition or further unchanged retry. A separately authorized
bounded measurement/kernel-cost investigation is needed to determine the next
correction without weakening assurance. CURRENT_WORK.md records exact evidence.
