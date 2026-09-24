# Native full desktop port and VMware priority

Frozen 2026-09-24, after user instruction to do everything necessary.
Baseline 2cf5228a. Exactly one active package: R8.3bw-desktop-port.

## Corrected delivery and preserved work

BI is a two-client graphical session, not the existing full desktop.
GRAPHICAL_READY proves startup, not frame latency or visual equivalence.
The user rejected the VMware prototype for both missing desktop and severe
stutter. Four64x64 tiles per100ms take20 batches for640x480; this intentional
production throttle alone prevents a responsive full desktop redraw.
No performance fix or full desktop delivery has yet passed acceptance.

BV is paused, not passed or discarded. Its34 changed files are preserved
byte-for-byte with SHA256 in build/codex-agent/native-vmware-desktop/paused-bv
and Git stash8e5102d0e1d748066a24a7a05ec67c22fbc9278c. Ignored build/guest
records remain in place. Resume by explicit reconciliation with later accepted
changes, preserving spent counters and all five original gates.

## First architectural boundary: actual source and service requirements

Compile the existing DESKTOP.PRG source list from build_system_programs.py,
including its real splash, GUI/image/config/storage libraries, using the
existing pinned Zig compiler and ELF64 x86-64 System V ABI. Standard static
ELF relocatable linking must retain unresolved platform symbols. Do not invent
success stubs, feed i386 objects to the native loader, or call int80 with the
legacy SDK. The output is a porting object, never an executable delivery.
Inspect ELF class/machine/type, allocated bytes by section, undefined symbols
and exact source/tool hashes. This is a host build inventory, not a guest or
native SDK compatibility proof. Include dependencies emitted by the compiler.

Existing desktop.c compiles natively with the actual exported include roots.
Inventory01's missing display_mode.h was a host include omission; inventory02
corrected it without source changes. All15 desktop C files now compile.
A closed list of required native services and loaded/static bytes determines
the next cohesive runtime package; do not substitute native_desktop.c.

## Gates and finite reservations

Scope is exactly the queue allowed_files. No production source change here.
Eight development host commands <=180s each, then two frozen gates exactly
once: test/test_x86_64_desktop_inventory.py -v <=180s and the inventory builder
--output build/codex-agent/native-vmware-desktop/qualification01 <=180s.
No kernel build, guest, network, signing or persistent format change.
The builder uses <=64 inputs,30s per compiler and180s whole command, fixed
output directory with refusal to overwrite, bounded ELF/log processing.
Host tests cover rejected ELF class/type/machine/bounds and symbol reporting;
real compilation is the package gate. Queue/contract definition commits are
administrative, never accepted implementation or runtime evidence.

## Required continuation, not fulfilled by this package

Use full desktop.c with native SDK/service adapters, existing menus, window
manager, fonts, explorer and application dispatch. Preserve Ring3 ownership,
generations, W^X, bounded input/IPC, watchdog and recovery. Display throughput
must be changed and measured as its own render/mediation failure boundary;
raising unmeasured limits or host vCPU count is not an accepted correction.
New persistent-write or hardware authority needs a concrete reviewed boundary.
Publish the native VMware VM only after real desktop startup, input, window
movement, menu/application dispatch, frame/input latency and component fault
recovery are demonstrated. Report unsupported functions explicitly. Follow
with remaining native OS completion; do not mark all work done from this
host-only prerequisite or re-deliver the BI prototype as the real desktop.
