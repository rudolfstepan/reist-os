# Native read-only PIO throughput prerequisite — R8.3by

Frozen after df9523be and the user's explicit continuation after the concrete
128-call/25ms resource proposal. BV's35 attributed files are preserved in
build/codex-agent/native-vmware-desktop/paused-bv-throughput/files.zip with
per-file SHA256 and stash cc29b83e4a3b5c1bb89b44d1b2049fae86b632b9.
No BV implementation enters this kernel prerequisite. Restore it after BY
acceptance, preserving new PIO files and metadata, then qualify its full
two-root1MiB pipeline. No frozen BV gate or failure is waived.

## Mechanism and ABI

Reuse native_pio_admit64/apply64/syscall64/terminal64/finish64, their validated
pinned64-byte request/state and exact generation/parent witness. ATA PIO
terminology and existing errno/operation semantics remain. Append request
version3 ONLY for BIND1, size64, quota128 at offset48; all other reserved
fields zero. v1 BIND/FENCE and v1/v2 operations retain their exact contracts.
Only the existing root with both old-reaped/new-owned-live witnesses may
bind. No same-generation rebind or driver self-upgrade.

State64 offset56 is zero for old64-call grants or the redundant encoded tag
0xffffff7f00000080 for128-call grants. Count bounds depend on that exact tag;
all other tag values fail corruption admission before effects. An ownerless
state requires zero tag. Fenced tags are retained only as diagnostics:
fenced grants admit no I/O. Rebinding resets count/tag to the explicitly
requested profile; final reap scrubs the whole state. Old64-call grants
remain byte-identical. No mutable global quota or new port authority.

100ms window, trusted10ms ticks, backward-clock fence,16 words/transfer,
read-only ATA whitelist and v2 per-operation deadlines stay unchanged.
At quota exhaustion the requested read/write/transfer is rejected; existing
idempotent fencing may issue its one control-port reset. "No port effect"
in the proposal means no requested I/O after rejection, not omission of
the existing protective reset. No DMA, IOPL, additional ports or data writes.

The driver and filesystem stay in Ring3.25ms software pacing belongs to
the subsequent BV integration, conditional on this explicitly granted
profile; old100/50ms adapters must remain unchanged.

## Frozen proof and finite reservations

Exactly five gates listed in the queue; limits900/900/600/900/600s.
Host O0/O2 executes the actual assembly with fake hardware/address-space
boundary only:64/65 and128/129, exact100ms reset, stale owner/root-only
delegation, canonical envelope, overflow/invalid tags, reverse clock,
fence/rebind/terminal/reap and unchanged failed read buffers. Existing PIO,
deadline, pool and trace host tests protect all prior profiles.
One opt-in pool-PIO fixture build; real QEMU captures new-profile normal,
driver crash, hang, CPU exhaustion, cancellation/recovery and an old-profile
reference. Full raw PIO/lifecycle/ownership/cleanup proof and independent
replay are mandatory; no console-marker-only acceptance. Maximum eight
guests60s each/480s total. A successful host test alone cannot complete BY.
Direct final scope/ABI/cleanup review, all gates and local commit before BV.

Development reservation: eight host commands600s, two builds300s, three
diagnostic guests60s. Fresh exclusive receipts; first failure stops its
window; evidence-directed correction may reserve another finite window
without asking for routine permission. Preserve failures, no unchanged
retry, no nested agents, no pushing. Full VMware desktop remains unfinished.
