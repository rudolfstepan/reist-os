# Native periodic PIO service boundary — R8.3aq

Frozen after clean accepted `9011ef1e`,18 September2026, under the standing
interactive completion directive. This is a pending implementation contract,
not acceptance. One package/main agent, no nested agents or push.

## Inventory and scope

[Periodic CPU admission](NATIVE_SERVICE_CPU_CONTRACT.md) passed all24 gates
and14 guest cases. [Eight-task PIO](NATIVE_POOL_PIO_CONTRACT.md) already binds
slots2..7 to one generation-scoped read-only ATA device. The build deliberately
rejects their combination. The existing `scheduler_fail` already selects
`native_pio_fail64` before the device-free TaskPool halt; normal owner retirement
already fences. Reuse those mechanisms, CREATE-v6, native_pio/native_service,
block RPC and private CPU-window-v1. No second accounting or recovery engine.

Close this shared CPU/device-owner lifecycle with one explicit
`-NativeServicePIO` / `X86_64_NATIVE_SERVICE_PIO=1` profile. Old ServiceCPU stays
device-free and old PoolPIO stays lifetime32; no implicit profile upgrade.
The new producer selects TaskPool/Wide/PIO/BlockProfile and private run-v5;
only its supervisor explicitly delegates CREATE-v6 to its driver/fillers.
Root1/fillers have no device rights; root0 alone binds/fences. Old versions,
SDK, syscall numbers and all production kernel/driver sources stay exact.
If a missing mechanism requires changing them, stop for architectural review.

References remain System V AMD64/ELF64, ATA IDENTIFY/READ SECTORS/LBA28 with
512-byte sectors, existing versioned REIST PIO/block/negative-errno adapters.
No new standard-compatibility claim, wire ABI or persistent format.

## Bounds and failure model

Keep CPU32 per1000ms, monotonic lifetime usage, immutable origin/no saved credit;
legacy CREATE-v1..5 remains lifetime32. Eight slots/eight CREATE attempts per
root, existing image/heap/IPC/IRQ limits, PIO64 calls/100ms and16 words/call,
ATA200ms, RPC1000ms and session3000ms remain. Only finite qualification workload
wait counts may differ in the new profile: peer60 and filler80 sleeps of100ms,
not new sleep limits or production service policy.

The bound device owner first performs40 calibrated11ms CPU bursts with40ms
sleeps, in four acknowledged batches. Reuse AP's enclosing three-trial TSC/
monotonic calibration and its exact range/error checks. Each progress receive
is bounded by1000ms. No syscall in a CPU burst; the IRQ ledger, not elapsed
time, proves at least40 samples across windows. Only after these bounded
pre-service batches does the existing unchanged service session initialize,
IDENTIFY/self-test/read. Never reset/reopen a service to evade its deadline.

Both initial and replacement drivers preserve root authority, fresh generation,
fencing, read-only media and complete cleanup. UD2, sleeping hang/CANCEL,
CPU-window exhaustion, malformed reply, root loss and OOM follow the existing
detect/isolate/fence/revoke/reap/recreate/self-test path. Independent root1 must
continue; exhaustion is contained, not a kernel panic.

For unknown CPU metadata corruption while a slot7 owner is physically released,
inject exactly one eight-byte window or generation word before pure CPU-core
validation. Require actual OUT DX,AL nIEN/SRST before diagnosis, unchanged
damaged CPU/task/family/device snapshots, IF=0, CLI/HLT and no reap/resume.
This is fatal containment, not in-place repair or fail-operational behavior.

## Frozen proof and efficiency

Use one same-image16-case normal matrix: six healthy driver slots2..7, slot7
at8GiB, driver UD2/hang/CPU exhaustion/bad reply, root0 loss, absent disk,
and first/middle/last actual import-allocation OOM. All others4GiB; two process
runs each and the original one replacement except terminal root loss.
Add exactly two fatal guests for window/generation corruption in slot7.

Preserve every independent frame/context/FP/W^X/private/immutable byte,
generation, IPC/heap retirement, physical ATA/RPC bytes, media and cleanup
predicate from AO; explicitly adapt only run-v5/CREATE-v6, periodic CPU and
declared finite workload timing. Add the AP bounded full-word CPU ledger and
reject missing/reordered/forged records. Normal binary reads retain independent
same-stop equivalence; fatal capture uses direct complete snapshots. No kernel
test syscall, fabricated healthy state or dynamic record repair.

Only the original-zero root fixture mode word may select normal cases (once
per run, with full image/mapping validation). Existing OOM allocation-return
injection is the sole other normal mutation. Preserve all write bindings.
Media is only the existing generated64KiB read-only base with exclusive
disposable qcow2; exact backing/map/logical bytes and no data allocation checked
before/after, including failures. Never use user or physical disks.

Each guest has30s including setup/capture/media/process cleanup; cleanup<=3s.
Normal matrix480s/fatal60s, outer600s/120s; host300s, build/verifier180s.
All15 queue obligations are frozen, each once per unchanged candidate.
The selected AP methods are invoked through their concrete test file, not the
`test.*` package namespace which collides with Python's installed test package.
This host invocation correction precedes any candidate or acceptance gate;
the same seven actual method names and all assertions remain unchanged.
Selected actual AP/AO host mechanisms are reused, not all historical test matrices.
One new common image per changed build-input candidate, no reference rebuilds.
The reference gate binds accepted AP/AO/legacy evidence and original inputs,
tools, profiles, commands, logs, artifacts plus exact legacy preprocessing.

At most three changed candidates, two evidence-directed in-scope corrections,
three builds and54 guests1620s cumulative. First failure stops later gates;
no unchanged retry, extra diagnostic guest, gate waiver or timeout expansion.
Outside scope, pre-existing failure, default drift or a missing production
mechanism stops implementation. All gates plus direct final diff review precede
the local commit/clean queue transition. Preserve all prior evidence.

No filesystem, ordinary shell, new device/DMA/write right, physical platform
or complete64-bit OS claim. This is a prerequisite for later concurrent native
file/service consumers; R3.6b stays explicitly deferred.
