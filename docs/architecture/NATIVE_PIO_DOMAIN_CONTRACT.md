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
Ring3 driver fixture. Old import/startup outcomes, capacities and C layout4
remain unchanged; their approved synchronization/oracle corrections are below.
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
focused in-scope repair unless resumed under the explicit continuous repair
authority below. Only after all16 groups, direct authority/failure/
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

The optimization on311d4db0 passes actual host6/3.799s and both builds. The
unchanged Import matrix passes normal4/8GiB (20 lifetimes each, root CPU at
most24) but fails OOM0: both roots reach32, status256, despite all18 lifetimes
and final frame/context cleanup. Preserve attempt4123370886ab425581580b71fd3e28a2;
this focused repair has reached the stop condition, not package acceptance.
Read-only observer inventory finds the OOM allocator breakpoint stays enabled
even when unarmed or already injected. Its possible CPU impact needs proof.
Scoping that breakpoint to the actual injection window would require the
currently unlisted scripts/run_qemu_x86_64_task_family.py and renewed authority;
no observer, quota, old oracle or i386 reference has been changed here.

The next explicit `ja mach das` authorizes that focused observer repair.
Add scripts/run_qemu_x86_64_task_family.py to scope: allocator breakpoint
disabled initially, enabled only for the existing injection window and
disabled immediately after injecting the exact requested allocation failure.
Rearm for the next root generation, never repeat within the same generation.
Host tests execute the generated observer for all six OOM counts and successive
roots, including inactive allocation calls. ENOMEM boundary, rollback, old
oracles, all16 gates and every runtime quota remain unchanged. Commit this
authority before source edits. No i386 rebaseline or wider media permission.

On contract1a9a3f51 the actual observer host tests pass, and all eight Import
guests pass (148 lifetimes, root CPU maximum26/32) with the same ten kernel
objects as the prior failed OOM candidate. Startup passes seven cases, then
OOM9 fails the old cancellation oracle: gen18 is READY1 rather than BLOCKED6.
All eighteen terminal receipts and final frame/context cleanup exist; both
roots exit70. Existing task-family contract and family_cancel_one64 explicitly
support both READY and BLOCKED cancellation, including queue removal before
fencing. This does not make the frozen gate pass. Retain Import attempt
715c39c376b44fdb979aee2d57e972cb and Startup14cbb3e6cca94dc4a160fdb084335256.
No further repair/retry or implementation commit. Correcting the exact allowed
cancellation-state assertion needs renewed authority for the currently unlisted
scripts/run_qemu_x86_64_task_startup.py plus negative tests; never accept other
states, wrong identities/reasons, missing fencing or incomplete retirement.

The user's subsequent instruction approves this cancellation correction and
requires continued implementation without asking for every routine repair.
Add scripts/run_qemu_x86_64_task_startup.py (33 scoped files). Accept exactly
READY1 or BLOCKED6 before cancellation with exact generation/reason/ordering,
and regression-test every other state and lost/duplicate/misordered evidence.
Bounded evidence-driven repairs within this same failure/authority boundary may
continue after recording the cause without routine one-repair handoffs; retain
all failed evidence and never retry unchanged candidates. All16 frozen gates,
quotas, microkernel boundary, clean acceptance commit and one-package rule stay.
Unrelated/user changes, unresolved external reference acceptance, new hardware
or write authority and architectural scope expansion remain genuine blockers.
No i386 repinning or reference overwrite is granted.

## Candidate implementation notes

The COW adapter creates exclusive generated.raw/disposable.qcow2 files only
under a unique ignored attempt directory, rejects aliases/hardlinks and wrong
guest folders, and uses an explicit read-only backing-node graph. Before and
after each capture (including failure), verify the exact64KiB base bytes/hash,
backing format/path, complete depth1 extent map and logical qcow2/raw equality.
The CLI uses the canonical module class for strict media admission.

Runtime observations read actual completed16-word input transfers and completed
OUT8 instructions, independently compare the known512-byte sector and identify
capacity, and require fencing plus full profile/IPC/heap/queue/frame retirement.
Only the completed family scrub is observed, not every unrelated syscall.
The Ring3 fixture prepares one private immutable ELF record then copies it to
the independently mutated import transport. Its single root-owned IPC endpoint
is explicitly delegated again to each new generation; retirement revokes grants.
All eight creation attempts and32 CPU samples remain unchanged.

Actual O0/O2 adapter regressions close an unbound-replacement terminal bug:
a newer task can terminate while the domain retains an older, already-fenced
owner. Leave that valid old state untouched; unfenced or future-owner mismatch
still physically fences and fails fatally without repairing metadata. Repeated
valid fencing now causes no extra port write. First fencing and new-generation
reset still execute physically, before retirement or release.

These implementation notes are not runtime or package acceptance. Failed
captures, including the observed timer fatal, remain evidence in CURRENT_WORK.

## Authorized reference qualification, 13 September2026

The renewed user instruction authorizes the requested separately verified i386
reference update, not blind learning of changed bytes. The same PIO transaction
adds three scoped reference-checker/test files and three frozen host, isolated
rebuild and qualification groups (19 total). All original16 groups remain.
Freeze this amendment before implementing the reference consumer.

Rebuild VMware/vga under `build/codex-agent/r83ah-pio/reference-rebuild`, never
in the original build directory. Bind both original disks to the existing SBOM,
signed boot manifests and all96 independently rebuilt programs/kernel. The main
disk contains later runtime data; its differing bytes are not a pristine release
claim. Four QEMU snapshot guests (both disks, APIC/PIT,60s each, one CPU) must
pass existing crash/hang/invalid-reply and normal runtime assertions. Hash all
references before and afterward, including failure paths. Preserve historical
framebuffer and old pins as evidence; replace reviewed constants only after
all qualification gates pass. The guard must never learn pins at runtime.
No original overwrite, user VM control, hardware acceptance, larger native
quota/deadline or unrelated implementation. Native timer failure remains open.

Qualification result: the frozen QEMU-on-VMware-image plan is invalid as a
platform acceptance route. Both disks and independently rebuilt programs/kernel
pass content/signature binding, but the first cross-profile guest fails at font
I/O (-110, UNICODE_RASTER). Existing R3.7 evidence already requires a matching
target build; ATA polling differs between VMware and QEMU. The consumer now
rejects this mismatch before launch. The four frozen guest requirements are
not silently replaced or declared passed. Corrected platform-matched acceptance
authority is required; old pins and failed evidence remain, no package commit.

## Authorized invisible Workstation correction

The renewed user instruction explicitly permits starting/stopping isolated
invisible VMware copies, never existing user VMs. Correct the four cross-profile
cases to actual Workstation `nogui`: both byte-exact disk copies with APIC and
CPUID-masked APIC/PIT, one CPU/1GiB/60s runtime. Require the actual backend marker,
full GTEST and recovery assertions; a mask alone proves nothing. Same36 source
files and19 groups; keep unaffected native/build evidence and historical failures.

Create each VM exclusively below a fresh ignored evidence folder. Generate an
allowlisted VMX and local flat descriptor; copy/hash the disk, never use an
original extent. No network adapter, physical floppy, audio, USB passthrough or
shared folders. Only an ephemeral loopback RFB endpoint injects the fixed GTEST
command using the existing RFB3.8 contract. Never use a visible GUI fallback.
Bound start/list/stop, refuse existing VMX processes, and finally stop only the
owned test VM and prove it gone even after ambiguous start. Missing headless
support or incomplete cleanup stops acceptance. Original hashes and all signed
rebuild/content requirements remain. No pin update until actual qualification.

Workstation result on88592bdc: the first APIC copy passes full GTEST/recovery
and shell return; the intended PIT copy also finishes GTEST but still uses
APIC. The checked ULM host logs the CPUID setting but no applied VM masks.
Both exact copies are stopped and originals unchanged. PIT and second-disk
acceptance remain open; no pin/queue update or global Hyper-V/VBS changes.
Actual backend admission now precedes GTEST input, with conflicting/missing
backend regression cases. A matching PIT environment or explicitly revised
platform matrix is needed; the failed case is never relabeled successful.

## Authorized platform-matched reference matrix

The user approves two original VMware disks on exclusive invisible Workstation
APIC copies, and an independent QEMU/vga build with APIC/PIT snapshot guests.
Four complete GTEST/recovery cases, one CPU/1GiB/60s, actual backend assertions.
One additional isolated QEMU build makes20 frozen groups; same36 source files.
Both rebuilds must contain identical96 user programs; their target-specific
signed kernels/manifests bind to their own profile, never to the other kernel.
All original16 groups, protected source hashes and failed evidence remain.
No VMware PIT claim, original overwrite, user VM control or host Hyper-V/VBS
change. Keep unaffected passed gates; rerun only the materially corrected
qualification and affected hosts. Ordinary scoped repairs need no new handoff.

Qualification on92df3aa2 passes all four matching guests in146.810s, evidence
reference-qualification-f6047a0a5c5d485db69225327f5e6704. Both VMware copies are
stopped; original and rebuilt hashes are unchanged. Both signed platform
builds and identical96 program payloads pass independent binding. Reviewed
guard constants are updated only afterward; historical framebuffer is unchanged,
old pins retained. Reference host16/.125s and byte guard1.105s pass.

## Final review stop: common fatal fencing outside scope

The reference result is not package acceptance. The common exception_fatal
path logs and halts without invoking the new physical PIO fence. The timer
abort adapter rejects MODE_PROCESS and returns to this same exception path.
The existing native_pio_fail64 entry fences its own failures, not every fatal
kernel/IRQ entry. This read-only code finding does not establish the cause of
the historical vector20 failure or imply its last BIND failed to assert reset.

Completing a common physical fence before fatal diagnostics requires
arch/x86_64/cpu/exceptions.asm, outside the frozen36 files. Stop without silent
scope expansion or implementation commit. Require an explicit amendment for
common fatal fencing and bounded timer cause evidence, with host and actual
guest negative proofs, unchanged quotas/deadlines, no metadata repair and no
i386 behavior change. Keep this package active and all failed evidence.

## Authorized common fatal boundary and bounded diagnosis

The renewed user approval permits this exact expansion and continued scoped
repairs without routine handoffs. Add exceptions.asm, timer_interrupt.asm and
the existing runtime-clock host consumer:39 files, one active PIO transaction.
NativePIO exception and scheduler fatal entries must physically assert nIEN/SRST
before diagnostics, independent of corrupt domain metadata. Do not run general
cleanup, repair records or return to the caller after kernel-corrupt failure.
Normal Ring3 retirement and all non-PIO/i386 behavior remain unchanged.

Preserve the timer's exact acceptance and all quotas/deadlines. Add bounded
failure-only cause witnesses, not a new clock policy. Keep the historical
vector20 failure as unknown when its missing evidence cannot be reconstructed;
a deliberately injected matching symptom proves a mechanism, not that history.
The existing runtime-clock host gate and a new --fatal PIO guest gate make22
groups. At most eight20s/one-CPU/4GiB generated-COW guests inject expired,
backward or invalid lease, tick/EOI disagreement, invalid IRQ context, actual
kernel exception and PIO metadata corruption after actual reset release.
Require exact cause, physical OUT before diagnosis, unchanged damaged records,
no subsequent reap/resume and unchanged generated media. Host negative tests
precede implementation; preserve existing normal/fault/recovery matrices.
Keep unaffected reference/build evidence; rerun only affected consumers after
material changes. Freeze this amendment before code changes, never push.
