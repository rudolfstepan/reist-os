# R3.42: Ring-3 FAT32 writable objects and requalification

Definition on clean `3e7c02add995b5c33aed045913382dc7ccce2d0f`, 9 September 2026.
Status: all37 frozen acceptance groups passed, 10 September2026.
Evidence/source/images: build/codex-agent/r342-fat32-write/accepted-final/;
final candidate32, reference builds24, guest29 and remaining runtime32.
Accepted local commit: `f808b558`; reviewed archive and queue transition complete.
10September recovery correction: a valid cold QUERY for a fenced ACTIVE
repair first requires the exact previous PID/generation to be fully reaped.
It retires that owner's guard and advances the retained record to FAILED,
including its generation, without relying on another media-change event for
an already quarantined device. This grants no IO authority; BEGIN still
requires fresh identity/pool checks and a fresh bounded lease within the
unchanged three-attempt budget. Old tokens and unrelated fences remain closed.
Native O0/O2 tests cover deferred/completed cleanup, missing reap, resumed
commit and three interrupted repairs; the actual guest cuts remain mandatory.
Exhaustion liveness proof distinguishes dependencies: CAT's ordinary file-object
client must still fail when Storage has exhausted its three restarts. A private
Ring-3 probe reads the same actual root file using the existing bounded legacy
read-only syscall path, closes it, and returns to the shell without another
Storage identity. This demonstrates the retained rescue path, not continued
file-object service, a client fallback or new kernel filesystem policy. The
512-byte/5s observer and whole auxiliary-medium oracle remain mandatory.
This is the next JS3 backend slice. R3.41 remains accepted with unresolved
historical risks R341-H1/H2; their disposition is not a waiver for new failures.

9 September, user-approved focused scope amendment: include
`drivers/block/ata_journal.c` only to correct unnecessary CLEAN-v2 header
repair on a primary-only journal. When no mirror is prescribed by the reserved
extent and the primary is valid and CLEAN, attach must remain read-only.
Missing/corrupt prescribed mirrors, inconsistent headers, ACTIVE recovery and
v1 upgrades retain their original validation and effect requirements. The
normal owned-object host still refuses recovery writes during attach. No new
persistent format, syscall, kernel parser or authority; the existing20 slots,
four commit barriers and all27 acceptance groups stay frozen. Require actual
owned/recovery-host regressions and a narrowly anchored journal-source guard.

## Scope and references

10September, explicit ATA-PIO follow-up approval: parameterize checked
read/write transfer helpers and select T13 WRITE MULTIPLE/C5h or EXT/39h
only for mediated external writes with live admission. Negotiate fresh mode
once, then share it between bounded write batches and full readback under
the SAME continuously held ATA mutex. No retained mode cache, cross-syscall
hint, reset/media-generation exception or automatic retry. Readiness,
original deadline and live authorization precede every command/DRQ block;
errors stop subsequent blocks and fence uncertain writes. Legacy NULL-
admission behavior, all capacities and four durability barriers stay intact.
Add the existing ATA multiple host runner/fixture and its subsystem document
to allowed scope. Strengthen that existing gate to O0/O2 actual production
read/write tests; retain all37 groups and their original runtime requirements.
This supersedes only the exact-helper-body restriction for these enumerated
PIO functions, not a whole-file ATA/journal or kernel-migration exception.

R3.42 admission refinement: a fresh per-command journal probe already validates
control, the exact owned pin, media and live request cancellation. Under the
same held VFS transaction mutex, an already attempted-and-pending WRITE is
idempotent: no second guard probe/publication is needed. First WRITE after a
barrier still publishes pending before effects. Never retain the probe across
IO/commands/waits or drop any CRC/ECC, deadline, generation, fence or pool check.
The actual VFS/guard native test must count three fresh protected reads rather
than six for repeated WRITE and still reject every stale/cancelled/corrupt case.
This is within the existing VFS/guard scope, no ABI, driver, journal or gate change.

10September, explicit follow-up approval repairs the reproduced admin ATA
flush deadlock in admin_maintenance.c and the already scoped ATA/service/safety
mediation. A separate FLUSH-only entry requires the current protected admin
transaction, live owner/generation, original maintenance lease, exact resource
and transition state before each command. Keep ordinary resource availability,
read-only/quarantine/recovery and global/driver fences unchanged; no transient
un-fencing or generic write capability. The control deadline records the
original lease expiry; the shorter drain deadline remains separate. Existing
supervision bounds the flush and an uncertain effect fails closed. Native O0/O2
actual-function tests and a headless ATA admin lifecycle/whole-media proof are
two additional groups (37 total); all35 previous groups remain required.
New paths: test/admin_maintenance_transition_host.c, scripts/run_qemu_admin_ata.py
and existing test/test_admin_maintenance.py. No AHCI/FDD driver changes or
userspace ABI change. The earlier failed admin/fault evidence remains failed.

10September, further explicit approval covers a local timed-wakeup correction
in kernel/sched/scheduler.c and its host tests. Expiry already publishes READY;
when the local CPU is idle, its existing post-EOI PIT hook must dispatch without
waiting for the10ms LAPIC quantum. Reuse the CPU-local pending-preemption bit,
never switch inside the hard IRQ or under the task-table lock. Running-task
quanta, class selection/accounting, stack and ownership checks, SMP ABI, timer
frequency and deadlines remain unchanged. Remote CPUs retain the established
periodic fallback. An executable O0/O2 test covers the actual wake/PIT bodies,
coalescing, empty/future/cancelled/stale waits, affinity, preemption and lock
deferral. Existing scheduler-time/slack/SMP hosts and APIC/PIT/SMP guests are
mandatory: seven added groups,35 total, no replacement of the original28.
The source guard allows only these three bodies and checks exact preservation
of every other scheduler path. This supersedes only the scheduler restriction
below, not the protected CPU-local/IRQ/backend/policy contract.

10September, explicit user approval expands this package solely by
kernel/init/critical_object.c and its existing two host-test files. Measure the
shared primitive first; optimize only equivalent CRC32/SECDED arithmetic.
Every copy, ECC/CRC/semantic check, correction result, generation/sequence,
lock/IRQ rule, publication order and64-byte format remain unchanged. Freeze
the accepted3e7c02ad implementation as independent executable reference for
O0/O2 encodings, arbitrary syndromes, single/double-bit faults, complete public
objects and bounded timing samples. Add its host-test group to the original27
unchanged groups (28 total); all original guest/performance proofs still apply.
No cache-based suppression of integrity checks or new hardware/WCET claim.

The same approved arithmetic-only scope now uses four immutable256-byte
SECDED contribution columns and one immutable256-entry CRC32 table. No lazy
initialization, object-result cache or skipped copy/check. All1024 byte
contributions plus overlapping random words are checked against the accepted
bit-position reference, alongside every existing fault/decoder/object test.
Host timings compare arithmetic cost only; they do not replace guest gates.

Implement one cohesive object/transaction boundary: explicit writable handles,
validated bulk input, overwrite, append, zero-filled growth, shrinking, sync,
and recovery before writable reintegration. First backend: existing regular
files on the default ATA-PIO FAT32 images. Include fragmented files, partial
sectors, empty files and supported FAT32 cluster/mirroring variants together.
No new file creation, namespace authority, FAT12 remap protocol, EXT2 data-write
backend, AHCI/FDD qualification, persistent format or JS write binding here.

Use POSIX.1-2024 terminology for byte offsets, write/pwrite, append, short
writes and fsync. Preserve the distinction between transferred bytes and
durable completion. The standard's
[file-operation atomicity rules](https://pubs.opengroup.org/onlinepubs/9799919799/functions/V2_chap02.html#tag_16_09_07)
are a reference, not a compatibility claim. A deliberately incremental resize
is called `resize_step`, NOT `ftruncate`: an error may follow a reported durable
size change. This versioned REIST deviation avoids both a hidden partial
truncate and a new persistent orphan-intent format. No POSIX/Node fs claim.
FAT geometry, cluster values and directory fields retain the existing Microsoft
FAT on-disk interpretation; RSTJ v1/v2 and the existing20-entry journal remain
unchanged. ATA commands, sector units and durability barriers remain unchanged.

## Inventory: reuse and exact gaps

| Boundary | Reuse | Required change |
| --- | --- | --- |
| Object lifetime |16 service slots, four per client, stable canonical key, kernel pin, generation-scoped close/reap | Admit a transaction with its exact owned pin still present; all other conflicting pins/nodes continue to exclude it |
| Request transport | Eight requests, two per client; two128KiB kernel bulk buffers; cancellation/copy quiescence | Stage complete client input before claim; service takes immutable bytes bound to the request and both owner generations |
| Transaction | R3.41 external-journal token, maximum5s absolute deadline, deferred/readback IO, four flush barriers | Bind normal mutation to the claimed request and owned pin; add no maintenance/raw-write fallback |
| FAT32 backend | Ring-3 geometry/locator parser and cache; legacy cluster/directory algorithms; transport-neutral journal core | Ring-3-owned transaction planner, allocation/cursor validation and post-commit locator refresh, without legacy global-state shims |
| Reintegration | R3.39 retire/reap order, sticky uncertain-media fences, media fingerprints | Repair-only admission while ordinary writes remain fenced; fresh generation and verified recovery before any writable publication |

Code anchors: `vfs_object_*` in userspace/programs/storage_service.c;
userspace/storage/lib/{vfs_file_client,vfs_shadow_fat32,fat32_transaction}.c;
kernel/init/{storage_request_pool,file_object_guard,storage_service,
storage_safety,filesystem_safety}.c; existing VFS and ATA external-journal hooks.
Read legacy fs/fat32/{fat32_cluster,fat32_files,fat32_vfs_adapter}.c for reuse,
but do not move their process-global boot sector, allocator or journal state
into a second owner. No new filesystem parser or recovery policy in Ring0.

Specific hazards already found:

- EXCLUSIVE currently rejects the writer's own lifetime pin. Dropping/re-pinning
  it or reopening a path is not a repair.
- Existing bulk transport only publishes service output. Passing a client's
  pointer to Storage, or claiming before input copy completes, is invalid.
- FAT32 locator validation includes the start cluster. Only this object's
  verified commit may refresh that locator when empty/grown/shrunk-to-zero;
  accepting a foreign entry change is not cache invalidation.
- Current parser limits (320 reads,6400 file-chain steps) are per-operation
  safety bounds, not a writable file-size contract. Add bounded resumable
  cursors; do not remove all bounds or silently report EOF at these limits.
- Current requalification checks media identity but does not clear an object
  fence. The existing polling path intentionally skips fenced resources.
  Neither a fresh PID nor `accept_formatted_media` authorizes recovery.
- Clearing global ATA/filesystem fences temporarily to repair one volume could
  authorize unrelated writes. Repair transport must remain a separate mode.

## Implementation order inside this single package

### Candidate wire/lifetime contract (10 September, not runtime accepted)

Storage operation35 alone carries `reist_vfs_write_frame_t` v2 (512 bytes).
Its separate operations are OPEN1, DELEGATE2, ADOPT3, DATA4, APPEND5, RESIZE6,
SYNC7. Old512-byte frames, old descriptors and DATA7/ALL15 are unchanged.
Explicit WRITE/APPEND/RESIZE/SYNC bits are16/32/64/128; the extended255 mask is
not a replacement for old ALL. Existing Script/Compositor domains cannot submit
operation35. Old ADOPT skips both unqualified and writable pending objects.
All input reply/reserved fields are zero; the outer offset equals the complete
input length, not a file offset. `offset`/`target_size` in the frame use bytes.

The64-byte v1 result at frame offset256 correlates the original kernel request,
errno, outcome, durable user bytes, released clusters, effective offset,
previous size and resulting size. SIZE_KNOWN marks reliable sizes; DONE applies
only to resize, including completed allocation-tail release. A single-step
UNKNOWN reports no known durable bytes or size. A future multi-step convenience
adapter must preserve earlier durable progress separately from an uncertain
suffix. A data gap may report durable size-only progress (requiring RESIZE),
never pretend zero filling transferred user bytes. A successful no-op resize
already at the required size/allocation returns NO_EFFECT plus DONE.

Client step functions return errno, with counts in the mandatory result, not
POSIX ssize_t. Only acknowledged durable bytes advance write/append seek state;
pwrite preserves it. Input is staged once; malformed/lost/late receipts cancel,
never ACK or replay. The service/client retain the original request deadline;
neither planner continuation nor input copying renews a transaction lease.
Even an internally aborted attach retains its final UNKNOWN outcome.

Open/adopt first qualify geometry, complete allocation ownership and read-only
CLEAN journal evidence before publishing rights. A newly delivered writable
open/adopt must receive its first owner-bound use within the existing5000ms
handoff budget; otherwise bounded reap releases its pin. This explicit v2
REIST lifetime deviation bounds lost-reply leaks; it is not POSIX open lifetime
compatibility. First verified use clears that handoff timer, not the object's
generation checks or mutation deadlines. Close can release it without effects.
The existing16/four object bounds and old read-only open semantics remain.

Storage uses one <256KiB fixed job (including immutable128KiB input) and one
<48KiB pin/epoch-bound ownership cache. These are private Ring-3 buffers, not a
third kernel bulk slot. Bounded planner/qualification turns interleave claim,
reap and boot-health handling. Whole-volume evidence is retained across own
verified commits, not recomputed per data chunk. Qualification/recovery after
an UNKNOWN fence is still required before package acceptance; ordinary opens
cannot repair journals or clear those fences.

### 1. Freeze executable negatives and append-only ABI

Add actual O0/O2 regressions before the corresponding production change.
Keep syscalls0..130 and count131, old wrappers, old112-byte guard requests,
old512-byte object frames and descriptors v1/v2 valid with their old semantics.
Extend existing versioned mediators/operation namespaces; no new syscall is
needed. Add explicit new object operations for writable open, mutation and
attenuated delegation. Old OPEN/OPEN_RIGHTS/OPEN_FLAGS and old READ/SEEK/STAT/
DELEGATE masks DATA=7, ALL=15 never acquire write rights.

The extended API distinguishes overwrite, append, resize and sync authority;
append-only objects cannot overwrite or shrink. New rights are explicit bits,
not a widened old ALL constant. Reject unknown versions/flags, nonzero reserved
fields, conflicting modes and arithmetic overflow before state publication.
Define new fixed-size structs with compile-time size/offset checks in the
central ABI/SDK and behavioral marshalling tests. Use a new descriptor version
to expose the kernel's original request deadline, never a client-renewed lease.
Keep old ABI/domain tests, including default Script denial, mandatory.

### 2. Complete input and owned-pin admission

Add client-to-service bulk transfer using the existing two128KiB slots, not a
third unbounded staging store. A submitted write is unclaimable while input is
incomplete. Copy and CRC publication bind request handle, client/service
generations, length and direction; bind the resolved media identity at owned-pin
admission. Reject double publish/take, crossed output
buffers and stale handles. Cancellation during copy quarantines that slot until
the copier is quiescent; it must never expose a successor's bytes. Exhaustion
returns a bounded error without a partially executable request.

An extended guard admission identifies the claimed request and exact owned pin,
canonical key, current client and Storage generations, media and namespace epoch.
Only that one verified pin is exempted from exclusive conflict checking. A
second pin, including another pin of the same client, is not exempt. Keep the
pin for the full object lifetime; the exclusive reservation lasts only for one
transaction, at most min(original request deadline, now+5000ms). Other-volume
objects are unaffected. No renewable operation or volume lease.

Validate cancellation/retirement before admission and after waits at every IO
boundary. Preserve the existing VFS -> metadata/ATA lock order and exact deadline
through command issue/readback/flush. No lock survives a userspace return.
Protected records remain <=64 bytes; extra fixed metadata needs its own checked
record, not a larger critical-record limit. Cancel before effects is NO_EFFECT;
cancel/lost reply after possible effects is UNKNOWN and fenced, not a retry.

10September candidate optimization: the private kernel journal probe obtains
correlation, pending state and deadline with one checked control/pin/media
snapshot. Revalidate after the VFS mutex wait and at every existing PIO command
boundary; it is not a capability cache. Pool cancellation, repair leases and
final completion remain separate live checks. Idempotent WRITE/FLUSHED events
do not update an identical protected record, but still perform its full CRC/ECC
validation. No critical-object primitive, protected-record format or wire ABI
change is authorized by this optimization. Full-sector overwrite staging may
omit its redundant preservation read, never the journal's real undo read;
partial-sector untouched bytes and all four barriers stay proven by the same
native media/fault oracles. The128KiB guest deadline is not yet satisfied.

### 3. One bounded FAT32 transaction planner

Add userspace/storage/{include/reist,lib}/fat32_file_write.{h,c}; reuse the
existing FAT32 parser and transport-neutral RSTJ implementation through the
transaction adapter. Do not copy the journal or fall back to SYS_WRITE.
Before each effect, validate the complete transaction: stable object, immutable
input, checked offsets, chain/range/loop integrity, allocation ownership,
mirrored FAT policy, unique target sectors and journal capacity.
Preserve high FAT bits and untouched directory fields; FSInfo is a hint, not
allocation authority. Corrupt/cross-linked chains, ambiguous mirror state and
unsupported geometry fail closed. Reuse epoch-bound validation/cursor caches;
never trust an allocation certificate after another mutation/media generation.
Any ownership scan is bounded/resumable and in Ring3, not a repeated unbounded
whole-volume scan in the kernel or per data chunk.

Overwrites preserve bytes outside the requested range, including sector tails.
Append chooses EOF under the same reservation as publication; pwrite uses its
explicit offset and does not change the client's seek position. Zero-length
write has no allocation or size effect. Offset/growth gaps and new visible
cluster bytes are zero-filled before publication. Free clusters never expose
previous file data. Distinguish actual ENOSPC from workspace/deadline exhaustion.

Transactions account for data, both relevant FAT copies, directory entry and
FSInfo targets before writing. Split at the actual20-target capacity, not an
arbitrary file-size ceiling. Preserve undo -> ACTIVE -> targets -> CLEAN flush
barriers and full readback. Coalesce contiguous IO where the existing core
permits; no implicit flush for each sector. Only successful durable completion
refreshes cached size/start cluster/offset. Mixed legacy IO remains excluded
during reservation and legacy hints are invalidated before the next owner.

The shrink planner sorts its complete <=20-sector RAM target list before
staging. The unchanged journal batches adjacent LBAs; all undo evidence and
the four barriers remain mandatory. A live journal is never reordered.
For this exact manifest the owned Ring-3 adapter reads adjacent before-images
in bounded runs and passes the SAME immutable bytes to the unchanged undo
core while applying a pure after-image transform. Its <=20-sector scratch is
inside the unchanged <256KiB job budget. It is synchronous, refuses reentry,
and is zeroed before finish/abort; live geometry and all post-write readback
always reach media. This is not a cache across commits or a relaxed journal
validation. Every predecessor/released link is checked in every FAT copy in
these fresh before-images, then again against the sealed plan at finish. The
terminal value is captured from the first selected FAT copy's fresh undo
image and must match every other copy exactly; distinct otherwise-valid EOC
values cannot evade mirror validation. Already-unknown valid FSInfo counters
remain unchanged without a redundant journal target; known hints still become
unknown in the same allocation-changing transaction.
The existing <48KiB ownership cache also retains64 sparse prefix hints with
power-of-two spacing, compacted during validated chain traversal/growth.
They share the exact pin/epoch with the tail cache, are pruned only after a
verified shrink commit, and cannot survive failed admission or foreign epochs.
Refilling a depleted tail starts at a bounded cached prefix, then validates
every traversed link/mirror until the already known suffix. Invalid hints or
spacing fail closed. Refills extend by at most the existing1024-entry retained
cache, clipped to the2561-entry plan workspace; a dense plan can extend again
in later bounded turns. This avoids loading a worst-case prefix that would be
discarded after the next small fragmented commit. No increased capacity,
persistent index or kernel parser.
The refill reader uses two64-sector FAT read-ahead windows inside the SAME
<256KiB job (now also compile-time asserted). Only the existing mediated bulk
READ is used; all physical sectors, including read-ahead, consume the original
256-sector planning budget and remain inside that FAT copy. The128-work bound,
live identity checks at each turn, mirror/cycle checks and original transaction
deadline remain unchanged. Windows never cross transactions or feed journal
staging/readback; scattered media may use more bounded turns, not more quota.

### 4. Explicit long-resource and outcome semantics

Each reply carries a versioned result: request correlation, errno, durable byte
count, resulting size, and NO_EFFECT / DURABLE_COMMIT / UNKNOWN outcome. A
durable prefix before an uncertain suffix is recorded separately; it never
asserts that the uncertain suffix had no effect. Lost/malformed replies cannot
be reconstructed as success from a local timeout. No automatic mutation replay.

Provide write/pwrite/append step operations and `resize_step(target_size)` plus
bounded client convenience loops using one original deadline. Every completed
step is independently recoverable. A long append may interleave with another
operation between steps; no whole-resource atomicity claim. The caller must
receive short progress and can explicitly continue with a new request, not an
automatic reset of its time budget. Seek alone never grows a file.

Client implementation: `reist_vfs_file_{write,pwrite,append,resize}_bounded`
returns errno and a version1,128-byte `reist_vfs_file_progress_t`. This is a
local adapter result, not a new wire frame/capability or POSIX return contract.
It retains confirmed bytes, released clusters, first confirmed data offset,
initial observed size, last confirmed size and the exact last64-byte receipt.
An aggregate UNKNOWN may therefore coexist with a confirmed earlier prefix;
the last confirmed size does not assert the current size of an uncertain
suffix. A local stop has last.request0 and does not erase preceding receipts'
counts. COMPLETE requires a successful final data/resize-DONE step, not merely
some durable bytes. Append offsets are per-step, not one contiguous guarantee.
The original min(session timeout,5000ms) deadline includes input staging and
all steps. Submit receives only the remaining duration; backward time relative
to any preceding observation, clock failure or deadline expiry stops the call.
Zero-length input is validated without data publication or gap allocation.

Object reads use a host-controlled windowed parser path with the original
descriptor-v3 deadline, checked before each mediated sector read and after
IO. Every128 chain/data items the host rechecks its live object pin and yields;
320 physical reads per window remain the bound. Cycle/range state persists
across continuations and the validated volume cluster count is the total walk
bound. Failed/cancelled host progress clears the complete output. FAT caches
persist only within this synchronous request, under its pin, not across epochs.
Both inline and bulk object reads use this path. Old path-based/parser wrappers
retain their original total quotas; no larger kernel buffer or renewable lease.
This closes the old6400-step ceiling exposed when reading the successful append
at the end of the4MiB fragmented guest file.

Growth publishes only durably zeroed/initialized data. A write beyond EOF first
uses explicit growth progress when the entire gap cannot fit one transaction;
do not hide a changed size behind a zero-byte ordinary write failure. Shrink
works from the tail, publishing each smaller valid size with its corresponding
FAT releases in the same transaction. It must not unlink a whole long suffix
and then forget its unreachable clusters after a crash. Truncate-to-zero is
the final recoverable step. No new orphan log or implicit partial ftruncate.
Support large resources beyond the old parser walk limit with bounded windows,
not a one-megabyte exception. FAT32's32-bit file-size limit remains explicit.

`fsync` is an explicit checked durability boundary for this live object and
backend, not a new grant or a no-op that conceals prior failure. Mutations
already acknowledged durable need not rewrite their data. No dirty deferred
writeback at close/GC; close/revoke is idempotent and never silently commits.

### 5. Recover while fenced, then qualify fresh objects

Normal requests remain denied on the uncertain resource. Use the existing
supervisor/restart state machine for both automatic and manual recovery: retire
the exact old generation, fence/revoke, reap, recreate, self-test, then qualify.
Old handles and revoked mounts stay stale; clients close/unmount and acquire
fresh mounts/objects only after qualification. No implicit regrant or remount.

The current Storage generation may obtain a short repair-only token when the
previous owner is quiescent/reaped, no conflicting nodes/pins exist and the
original resource extent, medium fingerprint and journal identity match.
Retain the kernel-owned resource/extent revocation record across unmount so
repair never requires reviving a revoked mount or accepting a caller's range.
Keep ordinary raw writes and normal object mutations fenced throughout repair.
Only token-bound ATA-PIO recovery IO is admitted under the original bounded
deadline. The kernel mediates extents/generations/effects; Ring3 validates all
existing journal before-images before any restoration, then applies the
existing RSTJ recovery algorithm and verifies CLEAN/readback/flush.

Reintegration requires successful journal/geometry/allocation self-test, stable
media identity, no pending write, and generation-matched publication at every
layer. Separate fixed qualification metadata may record this handshake; it
must not enlarge the existing64-byte Storage control or grant policy to Ring0.
Never clear another unsafe volume's fence or a sticky integrity-corruption
fence. A partial publication failure refences before admitting any ordinary IO.
Recovery fault/hang/expiry keeps quarantine and consumes the existing bounded
restart budget; it cannot create an endless sequence of new5s repair leases.
Conflicting/corrupt evidence needs intervention, not formatting or blind replay.

### 6. Prove, inspect, archive and commit

Recovery implementation protocol: Sys129 discriminator/version3 carries the
64-byte `reist_file_repair_request_t`; old discriminator0/v1 and2 remain intact.
QUERY1 returns only a retained fenced resource after old-owner reap; BEGIN2
echoes immutable geometry, fingerprint and record generation plus one <=5000ms
deadline. COMMIT3/ABORT4 echo the exact admitted token/frame; they return errno
without a copyout, so successful publication cannot lose an output capability.
BEGIN copyout failure aborts fail-closed. No user-selected media range, mount,
normal write grant or implicit retry. Invalid versions/reserved fields fail
before publication. Resource-relative512-byte sectors; BPB and backup BPB are
write-protected, including the standard absent-backup value0xffff.

The64-byte retained record and existing guard/pool records serialize repair
under VFS; no token survives an expired deadline, owner cleanup or generation
change. Fixed three-attempt ceiling complements (never enlarges) the existing
Storage restart budget. A hung repair triggers the same bounded retirement even
when its object-fence bit was already observed. Receipt/copier quiescence is
required before clearing only that resource's pool fence. Final guard release
is last; any partial failure refences every affected layer. Integrity poison
is sticky. Kernel repair IO checks current service authority before each PIO
command and never calls a normal write-begin through a temporary fence clear.

Ring3's recovery-only allocation certificate has no valid file-object locator
and is rejected by ordinary mutation planners. The same resumable window walker
checks all allocated/reachable clusters, including empty volumes. Before CLEAN,
restored sectors are flushed as a group; redundant CLEAN headers are separately
durable. Fresh read-only CLEAN attach and final flush precede publication. No
changed RSTJ format,20-target capacity, normal four-barrier commit or raw fallback.
Only FAT32 exposes the no-media-I/O revoked-unmount callback; active reservations,
pins and open nodes continue to prevent detach. Other backends get no exception.

Implement FWRITEST.PRG as an explicit file-object exercise on a caller-selected
test file, packaged in both Windows and Makefile images and resolved by the
normal Ring-3 shell. It has no raw/recovery authority. Private service fault
hooks live only in generated test images, not release opcodes or magic paths.
Keep native Windows errors/dialogs suppressed by the existing bounded runner.

Frozen commands and allowed files are in automation/reist-s03b.toml. Required:

- Native O0/O2 actual client/pool/guard/VFS/planner/journal/requalification code:
  sizes/rights, copy/cancel races, stale identities, all target/barrier/recovery
  cuts, exact whole-media old-or-step-final oracles, capacity/overflow, malformed
  media, fragmented/empty/long files and bounded allocation/IO counts.
- Normal VMware then QEMU reference builds,1024MiB; independently match image
  kernels and every payload. Against the accepted R3.41 archive only STORAGE,
  new FWRITEST and the enumerated existing file-client consumers may differ.
  Consumer changes must be attributable to the shared client ABI/library; their
  application sources and feature rights stay unchanged. Protect BENCHMARK,
  CURL, JSTEST, JSWORK, REIST and all non-consumer payloads byte-for-byte.
- Headless QEMU normal overwrite/append/growth/shrink/sync, long fragmented
  resource and shell dispatch; real owner/service fault, noncooperative hang,
  cancellation/lost reply, stale handle reuse, interrupted recovery and exhausted
  recovery. Exact disk oracle and independent root/shell liveness in each case;
  fresh objects only after qualification, corrupt evidence never unfenced.
- Existing journal/retirement/FAT32 recovery, JS-file, restricted worker and
  external-script browser proofs remain mandatory. A library rebuild is not a
  new JS grant. Retain original failures and stop on a new acceptance failure.
- Compare one accepted baseline and one candidate QEMU benchmark at identical
  settings, with unchanged BENCHMARK.PRG; retain raw times and deterministic
  batch/flush/cache-work counts. No new GUI synchronous RPC, scheduler/CPU-local/
  framebuffer change, or general ATA hotpath rewrite. Enumerate cold recovery
  hooks in the artifact checker, with negative tests against broad exemptions.
  Investigate a material slowdown before acceptance; do not repeat unchanged
  runs until a favorable timing appears or call one VM pair hardware evidence.

The17 existing direct file-client consumers, frozen from the baseline build
manifest, are JS, JSRUNTST, CAT, CHKDSK, BASIC, DESKTOP, NOTEPAD, BROWSER,
IMAGEVIEWER, CONTROL, MOUSE, DISPLAY, COPY, HTTPD, EDIT, GTEST and OBJGDTST
(.PRG each). User-approved10September amendment adds exactly two indirect
consumers, WAVPLAY.PRG and SOUNDPLAYER.PRG: the unchanged AUDIO_LIBRARY_SOURCES
archive includes vfs_file_client.c. Total19 consumer exceptions; pin the SDK
archive recipe, audio sources, path helper and both application sources to the
accepted baseline. Only the shared file client explains their relink; no audio
feature/rights change, other payload exception or gate/budget waiver.
This is a link-dependency exception only, not authority to edit
their application sources or silently remove protections from other programs.
Record each actual changed payload and the linked-library cause. The new guest
also proves expired/cancelled mutation authority issues zero fresh PIO commands;
UNKNOWN after an earlier effect still requires recovery, not NO_EFFECT.

Host compiler <=90s, individual native executable <=30s. New guest cases <=180s,
new object/recovery campaign <=1080s, benchmark pair <=360s; inherited guest
limits stay unchanged. Run one compiler/build/VM group at a time. No agents,
visible VMs, external media, destructive cleanup or push. No unverifiable
performance, hardware power-loss, WCET, certification or JS-completion claim.

Only after all frozen groups pass: inspect scope/ABI/cleanup and final diff,
archive evidence, mark R3.42 done and perform the existing next-queued transition,
then local implementation commit. The VMware deferral remains binding even if
R3.6b becomes formally active. Subsequent explicit JS write delegation requires
its own host-authority package; do not implement it in this run.
