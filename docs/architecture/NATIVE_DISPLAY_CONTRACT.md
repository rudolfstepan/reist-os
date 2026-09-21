# Native64 bounded display mediation — R8.3be

## Authority and baseline

The user authorized a first QEMU graphics boundary on 21 September 2026 after
the accepted signed CLI delivery `a8cfbde4`. This is one opt-in research profile,
not a desktop or a claim about other hardware. The i386 images and the signed
native CLI media remain unchanged. R3.6b stays deferred.

The earlier four-file parser prototype was written before a queue package was
selected. It is archived verbatim with SHA256 entries under
`build/codex-agent/r83be-display/prototype-20260921/`. Its temporary O0/O2 host
pass is development feedback only. The cache-access failure and the initial
NDEBUG/assert compilation failure remain historical failures. This contract
and the active queue entry establish the implementation transaction; no source
acceptance, build or guest proof is claimed by the setup commit.

## Inventoried mechanisms and failure mode

BIOS stage 2 already selects and validates a VBE 2/3 linear 32-bit direct-colour
mode (1024x768 preferred, 800x600 fallback) and publishes Multiboot-v1
framebuffer fields at offsets 88..115 only after a successful mode set. The
existing CLI stage2 is assembled without USE_FRAMEBUFFER, so this profile must
explicitly select the existing framebuffer path in separately signed media.
The
native64 boot entry preserves the Multiboot pointer, but its physical-memory
direct map contains only E820-usable RAM. No native64 display syscall, MMIO
mapping or Ring-3 graphics owner exists. Treating the LFB as RAM, or handing
its physical address to a process, would cross the device boundary.

## Fixed reference profile

Only QEMU pc/TCG, qemu64, one CPU, 4/8 GiB, the existing signed BIOS boot
chain and its 1024x768/800x600 VBE modes qualify this package. Interpret the
boot record with Multiboot-v1 framebuffer semantics and VBE direct-colour mask
fields. Accept exactly 32-bpp, type 1, one plane, positive pitch, a supported
geometry, non-overlapping 8-bit RGB masks, a page-aligned mapping envelope
below 4 GiB and overflow-checked `pitch * height`. Reject absent, partial,
reserved, malformed or inconsistent records before mapping or publishing
authority. Do not infer device memory from E820 usable RAM.

The initial QEMU profile requires BGRX byte order (red16, green8, blue0),
pitch divisible by4 from width*4 through16384, LFB at or above0xc0000000,
and at most32 E820 ranges. This is a restrictive platform profile, not the
general VBE format. Missing/unsupported boot graphics leaves the serial CLI
available with display requests rejected as ENODEV. No partial graphics
record or mapping is published.

Create one kernel-owned, NX, supervisor-only LFB mapping with the platform's
validated device cache type. No user PTE or general physical-memory direct-map
alias may expose it. A fixed display record contains mode geometry, mapping,
owner generation, epoch, fence state and a bounded operation counter. Its
initial state is fenced. A fresh Ring-3 display client may bind only after
the previous generation is dead and fenced. The client has no raw physical
address, I/O ports, DMA, mode-setting or arbitrary framebuffer mapping.

Use the existing shared higher-half hierarchy's unused PDPT entry509,
virtual base0xffffffff40000000, with one fixed PD and at most six fixed PTs.
All leaves are4KiB, supervisor RW/NX, PCD/PWT selecting PAT index3; verify
the CPU supports PAT and index3 is UC before the first output. The linked
tables and staging tile remain excluded from the writable RAM direct map.
Fencing forbids subsequent writes; the last complete/partial image may remain
visible. No claim of electrically blanked scanout or safety-actuator fencing
is made for this research display.

Append operation 30 with a versioned, fixed-size request to native
DEVICE_CONTROL 113; retain every existing operation and profile. Validate the
complete user source range, exact owner generation, profile bit, size, stride,
coordinates, rectangle containment and an absolute deadline no more than
1000 ms ahead before copying any pixel. A commit is at most 64x64 pixels,
16384 bytes. Admit at most 64 commits and 1 MiB per 100 ms period; budget
exhaustion fences the display domain. Never copy a whole screen in one syscall.
Copy through a kernel-owned fixed staging tile so user memory cannot change
after validation and before publication. No heap, VFS, wait or formatted log
in the mediator. Every loop has a fixed byte bound. Rejected operations cause
no scanout write. A CPU fault during the final MMIO copy is a kernel/platform
fault: fence outputs and enter the existing fatal path rather than claiming
that arbitrary hardware failure can be repaired in place.

The Ring-3 client paints a deterministic test image from private memory in
bounded tiles, reports a health/self-test result, and exits or crashes under
test control. Exit, fault, hang, owner loss, quota violation and explicit
cancel all use `detect -> isolate -> fence/revoke -> reap -> recreate ->
self-test -> reintegrate`. Exact generation and epoch checks prevent stale
clients from writing after reuse. Exhaustion remains fenced and enters the
profile-defined degraded state. The serial shell stays alive.

## Frozen proof boundary

Host behavior tests cover every malformed Multiboot field, arithmetic edge,
RAM/MMIO overlap, mapping flags, request size and pointer, wrong/stale owner,
budget, fence idempotence and restart exhaustion. Source checks only supplement
these behavior tests. A real signed-BIOS QEMU guest must capture pixels through
QMP and verify the exact pattern at both accepted resolutions, plus crash,
hang and stale-owner denial while the serial shell remains responsive.
Compare the complete accepted CLI predicates and reference artifacts; no
partial boot marker counts as success. Use one frozen build and bounded guest
matrix with preserved logs under `build/codex-agent/`; stop at the first failed
gate, retain all failure evidence and commit only after all gates pass.

This package adds no keyboard, mouse, compositor, Surface ABI, network,
filesystem writes, DMA, PCI driver or physical/VMware assurance.

## Execution and review

The queue freezes the complete allowed-file set and twelve final gate commands.
Candidate01 initially reserves at most twelve host development commands of
600 seconds each, zero kernel builds, zero media publications and zero guests.
Build/media/runtime commands receive a finite recorded reservation before
execution. A failed gate stops that window; retain its evidence and freeze
the evidence-directed correction window under standing continuation authority.
Do not broaden the file scope or weaken an acceptance predicate silently.

The graphics probe is a normal ELF64 foreground program selected as /boot.prg
in this opt-in research image; it is reached through the existing Ring3 shell
lookup/SPAWNV/WAIT path in both Make and Windows builds. Root0 delegates the
display operation only for this explicitly selected file and binds its exact
child handle. Other file tools retain their existing profiles. Normal CLI
proofs exercise unchanged cat/ls/probe operations on the new kernel; graphics
proofs additionally verify syscall authority, pixel bytes, fault retirement,
stale handles, generation reuse and a subsequent live serial command.
