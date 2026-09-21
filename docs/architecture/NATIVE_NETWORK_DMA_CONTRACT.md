# Native network DMA boundary, v1

Authorized21 September2026 after accepted graphical package952a37bc.
R8.3bj is the hardware-containment prerequisite. Protocol stacks, policy,
complex device logic and normal shell commands follow in Ring3; this package
establishes the sole safe DMA transport with a real separate Ring3 consumer.

## Platform and references

Only QEMU PC/TCG, qemu64, one CPU,4/8GiB, RTL8139 at PCI00:04.0.
RTL8139 legacy C-mode register semantics, PCI command bus-master enable/disable,
IEEE802.3 frame units and conventional negative errno are retained.
References: existing drivers/net/rtl8139.c; Realtek RTL8139(A/B) Programming
Guide V0.1 https://www.cs.usfca.edu/~cruse/cs326f04/RTL8139_ProgrammersGuide.pdf;
QEMU reference model https://qemu.googlesource.com/qemu/+/refs/tags/v8.1.2/hw/net/rtl8139.c.
No socket/POSIX or full-network-stack compatibility is claimed.

## Fixed authority and DMA envelope

Opt-in NativeNetworkDMA implies the existing task-pool profile; all old paths
are exactly unchanged when disabled. Append device32 to DEVICE_CONTROL113,
fixed64-byte request-v1, reserved bytes zero. Root0 may bind only its live child,
old generation reaped first; owner and parent revocation share one kernel path.
No grant comes from a syscall mask alone. Exact owner/epoch required for IO.
Root/control caller cannot transmit or receive on a delegated child channel.

All RX/TX memory is kernel-owned, statically reserved in existing supervisor
NX BSS, below4GiB, never user mapped. One8192-byte RX ring plus2048-byte wrap
slack, four2048-byte TX buffers; DMA addresses and descriptor lengths never
come from userspace. Frame14..1514bytes; short TX zero-padded to60; RX excludes
hardware FCS. No raw PCI/MMIO/PIO/register syscall or descriptor mapping.
IMR stays0; bounded userspace sleep polling, no hard-IRQ work. The mediator
only validates/copies bounded device records and programs fixed safe buffers;
Ethernet/IP/ARP/TCP interpretation and recovery policy are userspace concerns.

Initialization checks PCI identity and assigned IO BAR before writes, disables
bus mastering before reset/zeroing, sets only fixed DMA addresses and enables
mastering after setup. Reset/start are distinct bounded steps, never a kernel
wait loop. Fencing disables device RX/TX, masks IRQ, clears PCI bus mastering
and verifies readback before zeroing or reusing DMA storage. Failed readback
is kernel-fatal containment; never report safe reuse. A previous generation
cannot rebind or recover authority. Without an IOMMU the assurance covers
untrusted software using this validated mediator on the specified emulator;
arbitrary defective/malicious physical DMA devices are unsupported.

## Budgets and validation

Operation deadline<=1000ms,128 IO calls/100ms, clock/sequence wrap fails closed;
one TX operation per fixed slot at a time with100ms completion limit.
No dynamic kernel allocation, VFS, formatted IRQ/fatal logging or busy-wait.
Existing CPU32 and process/IPC/heap capacities remain unchanged.
Protected software state has an inverse mirror; corruption fences hardware
before fatal transition. Bad versions, rights, generations, pointers, lengths
and deadlines are rejected before device side effects. User ranges are fully
validated before copies; staging is scrubbed after every syscall.

Actual O0/O2 production-C tests cover request/owner/epoch/clock/length edges,
shared budgets, reset progression, DMA addresses, RX wrap/header corruption,
TX capacity/completion, fencing/readback failure and generation reuse.
Eight fresh real guests:4GiB,8GiB, child UD, child hang, child CPU32, active
parent UD, IO quota and absent NIC. Normal cases include malformed/stale/
foreign/pointer rejection and a subsequent fresh generation. Each<=45s incl
owned cleanup. A loopback-only bounded host Ethernet peer records exact TX/RX
bytes; no NAT, bridge, TAP, public network or persistent disk writes.
Raw task/profile/parent/device/DMA state, kernel reap receipts, packet bytes,
CPU reason and closure are independently replayed. Success text alone is
insufficient. No new user shell command is advertised by this prerequisite.

## Qualification and efficiency

Five gates as frozen in the queue; one common image, no per-case build.
All old disabled sources and existing reference artifacts are checked once.
Unchanged GUI/BIOS suites are not rerun for this opt-in mechanism boundary.
No nested agent, push or full OS completion claim. R3.6b remains deferred.
