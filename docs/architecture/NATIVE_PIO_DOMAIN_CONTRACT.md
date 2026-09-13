# Native read-only PIO domain contract

R8.3ah, frozen on acceptedabd9edb4, 12 September2026. This contract is not
runtime acceptance. Original14 groups plus the two approved Startup reference
groups remain mandatory (16 total).

## Inventory and common boundary

Native image import, immutable startup, generation profiles, bounded IPC,
CPU quotas and complete child retirement exist. Storage_service still depends
on i386 VFS/storage mediation. The native CREATE interface carries only the
low64 syscall bits, although the protected profile core already supports
three64-bit words. DEVICE_CONTROL113 cannot yet reach a native driver.

Bundle full profile admission, one read-only PIO device domain, Ring3 ATA
IDENTIFY/sector-read consumer, generation fencing and restart proof. These
share the same driver authority and failure boundary. Do not add filesystem,
partition parsing, protocol policy or a complex ATA driver in Ring0.
Existing i386 ATA/device-domain code is read-only migration reference.

## Explicit reference profile and standards

Only QEMU pc/TCG, one CPU, primary legacy ATA master (ports1f0..1f7 and3f6),
4/8GiB and a generated read-only raw fixture disk under build/codex-agent.
No physical disks, writes, DMA, PCI reconfiguration, AHCI, IOMMU or VMware
acceptance. PIO data-in and ATA IDENTIFY DEVICE/READ SECTORS follow the
references and terminology in ATA_PIO_TRANSFER_CONTRACT.md. Preserve512-byte
sectors,256 sixteen-bit data words, sector count and LBA28 units. Ring3 owns
IDENTIFY interpretation and all protocol waits, each with an absolute monotonic
deadline and SLEEP, never busy polling. Report unsupported/absent device
fail-closed. The generated base is always attached read-only and verified
unchanged; the approved host-only COW exception below does not grant guest writes.

## Public profile and mediation

CREATE-v4 retains64 bytes and imports prepared records like v3. Its syscalls
field becomes a pointer to a fixed40-byte profile-v1: u32 version,size,
three u64 masks and one reserved-zero u64. Copy/admit the entire profile
before a charged attempt or allocation; reuse the existing192-bit profile core.
Preserve versions1..3. Mask0 retains the current allowed native calls; mask1
may additionally contain only DEVICE_CONTROL113 in this profile, mask2 is
zero for children. Root0 alone receives this new platform authority; root1
and ordinary old children do not. Attenuate every word against the exact
parent generation, retain full masks until fencing, scrub temporary masks
and each retired slot. No child TASK_CONTROL, storage-write or DMA grant.

DEVICE_CONTROL113 gains append-only operation29, a native read-only PIO
adapter; old operations and old i386 behavior stay unchanged. A fixed64-byte
versioned request carries operation, generation handle, port/value, bounded
word count and optional data pointer; all reserved/unused fields must be zero.
Bind/fence are root0-only and generation-exact. Only the bound live driver
may access whitelisted ports. Allow eight-bit status/register access and at
most16 input words per operation. Data-port writes and commands other than
IDENTIFY DEVICE and READ SECTORS are denied before port effects. Allow only
the primary master, one-sector requests and nIEN-preserving reset controls.
No raw region mapping or unmediated I/O privilege.

One fixed domain record holds owner/inverse, fenced state and finite I/O
accounting (at most64 operations per100ms). Backward time or exhaustion fences
the domain; later time alone never restores authority. Binding an active old
generation is denied. A new bind requires fenced old ownership and completed
old task retirement. Epoch/owner checks deny old handles after slot reuse.
No heap, formatted logging or waiting in the kernel mediator.

## Recovery boundary

Driver crash, hang, rejected protocol result, quota violation, parent loss,
normal exit and explicit cancellation converge on generation-scoped fencing.
Deny further port operations and assert nIEN/SRST before task/profile/frame
retirement; hold reset across owner loss. New generation releases reset only
after a bounded Ring3 delay and must pass fresh IDENTIFY/read self-test before
its result is accepted. Automatic and explicit test recovery call the same
fence/cancel/wait/create/self-test path and preserve the eight-attempt owner
budget. Exhaustion leaves the domain fenced, never an unbounded restart loop.
A missing device is an unsupported/degraded result, not kernel corruption.

No system-wide service-supervisor or DMA-isolation claim is made. This package
proves the bounded mediation prerequisite and one restartable read-only Ring3
driver. Full storage service, writable media recovery, real hardware and
normal shell/file integration remain later cohesive boundaries.

## Frozen proof and integration

NativePIO presets NativeImport and its dependencies but selects a distinct
Ring3 driver fixture. Old import/startup fixtures and C layout4 remain unchanged.
The root may use the already accepted two-RX-page import layout; all image,
task, heap, CPU and startup capacities remain exact.

Host O0/O2 runs actual mediator/profile assembly against deterministic port
witnesses plus actual Ring3 transfer code. Cover full-word attenuation, invalid
pointer/header/port/command/count, stale owners, I/O exhaustion, backward time,
reset/fence ordering, short/failed transfers, missing device and untouched
outputs before validated success. Negative guest oracles supplement these.

Real hidden QEMU matrix: normal4/8GiB; OOM0/1/2/3/6/9; missing-disk and owner-loss
cases. At most20s per guest. Normal cases include complete known512-byte reads,
partial-transfer UD2, sleeping hang, CPU exhaustion, forbidden write commands,
stale handles and fresh-generation recovery with an independently progressing
peer. Require exact privilege/profile fences before all task frame frees,
bounded driver receipts, complete context/scratch/domain cleanup and unchanged
disk bytes. Do not replace physical port execution with an emulated success
marker. Reuse existing frame/heap/IPC observers and independently compare disk
content. The old eight-case image-import matrix, normal bootstrap and read-only
i386 pins are mandatory; no unrelated full hardware matrix.

Stop on unattributed changes, required files outside allowed_files, widened
quotas/deadlines, external hardware authority, or a failed gate after one
focused in-scope repair. Only after all14 groups, direct authority/failure/
cleanup/scope review and a clean local commit may another package start.
R3.6b stays deferred, R341-H1/H2 open; no full64-bit OS completion claim.

## Implementation stop, not a contract amendment

12 September2026: the attributed candidate on4b351bf3 builds and its initial
actual mediator/profile/transfer host test passes O0/O2. It is not accepted.
QEMU11.1.0 rejects an IDE hard disk backed by a read-only raw node before
unpausing the CPU (`Block node is read-only`). A generated64KiB fixture,
three bounded paused attachment variants and unchanged SHA256 confirm this
under build/codex-agent/r83ah-pio/readonly-probe-8251731b8f954f3e8b1d4b95d8de679d.
Neither disabling write cache nor explicit blockdev/ide-hd attachment admits it.

The read-only-medium invariant and all14 gates above are still frozen.
No writable backend, overlay or real/user disk has been used. A disposable
COW test layer over a read-only generated base would change this acceptance
boundary and requires explicit user authorization before implementation.
Guest write/DMA denial would remain mandatory, with independent base hash
and no changed overlay-sector proof; this is a proposal, not current authority.
The PIO guest runner/oracle and final runtime/integrity review remain unfinished.

13 September2026 continuation: actual terminal/finish and full-profile adapter
regressions now prove shared integrity admission, physical fail fencing without
metadata repair, all192 syscall positions and rejection of ignored extended
mask corruption. Host O0/O2 and all three build variants pass; no acceptance.
The frozen old import guest fails at child237/root225: its fixed20ms delegation
delay races the child's first unauthorized-send assertion. A bounded handshake
requires task_startup.c outside frozen allowed_files; no such edit authorized.
Separately the frozen i386 image hash differs, with a running VMware instance;
neither reference rebasing/restoration nor VM termination is authorized.
All gates, media rules and scope remain frozen; see CURRENT_WORK for evidence.

## Approved test-boundary amendment, 13 September2026

The user's explicit `ja mach das` authorizes the two requested adjustments.
Only a newly generated64KiB raw base and a disposable qcow2 layer may be used,
in a unique ignored build/codex-agent attempt directory. QEMU opens the backing
file node explicitly read-only. The overlay satisfies IDE backend admission;
the native mediator still denies all guest write/DMA commands. Verify the base
SHA256, logical bytes and absence of overlay data allocation before and after
each guest, including failures. Retain diagnostic files rather than deleting
them. No real/user disk, unrestricted QEMU arguments, physical hardware or
persistent-format claim is authorized. Historical read-only rejection above
remains evidence; this is the sole exception to host fixture writability.

Add task_startup.c to allowed_files for a finite explicit IPC acknowledgement
before granting the tested endpoint. Preserve the denied-first-send proof,
all startup argument/attempt/CPU/image bounds, old outcomes and cleanup.
Increasing a fixed delay or accepting a prematurely successful first send is
not the repair. Keep the original14 gates and add NativeStartup build plus
its old eight-case matrix;16 total. Contract commit precedes source edits.

The confirmed i386 artifact changes still require provenance/acceptance
clarification. Existing pins and the guard remain unchanged; no blind rebase,
reference overwrite or VMware process control is authorized by this amendment.

The approved handshake candidate on02e2e179 passes host O0/O2 and both builds.
Its frozen Import guest fails after that focused repair at the root's exact
32-sample CPU budget (16/20 expected retirements). The original child237 race
is absent; this is still failure, not acceptance. Retain attempt
5ecd5b7fad7c4173a16d24456edf00d8 and stop under the existing repair rule.
No second fix/retry, CPU quota widening or implementation commit is allowed
without renewed direction. The authorized COW harness is still unfinished.

The subsequent explicit `ja mach das` resumes this same candidate for one
focused fixture optimization within the unchanged31-file scope and16 gates.
One root-owned acknowledgement channel may span sequential children, with
separate generation grants and exact sender/sequence checks each time. Cache
immutable root identity/arguments and use bounded full-width source overwrites;
all source bytes must still be mutated after import. Preserve every negative
test, child iteration, stale-rights check and cleanup, including final channel
close. CPU quota32, deadlines and old runtime oracles remain unchanged. Commit
this authority before implementation; the earlier failure is retained evidence.
This does not authorize i386 reference replacement or unchecked rebaselining.
