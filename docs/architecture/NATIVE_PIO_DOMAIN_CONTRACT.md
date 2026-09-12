# Native read-only PIO domain contract

R8.3ah, frozen on acceptedabd9edb4, 12 September2026. This contract is not
runtime acceptance. All14 queue groups remain mandatory.

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
fail-closed. The disk is always attached read-only and verified unchanged.

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
