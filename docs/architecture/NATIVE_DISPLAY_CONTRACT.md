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

21 September host window correction: six development commands spent, zero
kernel/media/guest builds. Parser/core O0/O2, PIO9 and family4 pass. Terminal
16/17 and shell59/62 stop on historical disabled-source projections and one
literal retirement-hook sequence. Original logs remain under
`build/codex-agent/r83be-display/development-{terminal,shell_session}.log`.
Explicitly add `scripts/verify_x86_64_terminal.py` and
`scripts/verify_x86_64_shell_session.py` to this package's scope: their exact
predecessor comparison must compose the disabled opt-in successor. A new
helper may remove only fully matched display additions; all surrounding
bytes and predecessor references remain mandatory. Add mutation regressions,
restore the historical hook sequence, then reserve at most six further host
commands of600s each, zero builds/media/guests. This is a verification-scope
correction, with no new device authority or relaxed acceptance predicate.

The graphics probe is a normal ELF64 foreground program selected as /boot.prg
in this opt-in research image; it is reached through the existing Ring3 shell
lookup/SPAWNV/WAIT path in both Make and Windows builds. Root0 delegates the
display operation only for this explicitly selected file and binds its exact
child handle. Other file tools retain their existing profiles. Normal CLI
proofs exercise unchanged cat/ls/probe operations on the new kernel; graphics
proofs additionally verify syscall authority, pixel bytes, fault retirement,
stale handles, generation reuse and a subsequent live serial command.

## Candidate01 qualification

Four development builds and four signed-media attempts are retained, including
the initial FAT12 capacity failure caused by unintended debug sections. Guest01
identified the terminal-only mask composition; native_terminal.inc was added
explicitly to scope and all three checks now permit the combined profile only
when DISPLAY is selected. Actual O0/O2 helper red/green and all17 old terminal
tests pass. Guest02 identified the existing2060-byte pointer-check limit. The
display adapter now validates the entire tile through at most16 chunks of1024
bytes before any staging or output; old generic limits remain unchanged.
Guest03 painted twice but exposed a reset-state observer error. Guest04 and
independent physical/pixel/media replay pass with three tiles and epochs, two
root runs and five foreground reaps. All failed raw evidence remains archived.

Candidate01 freezes twelve gates, zero further builds/media and19 fresh guests:
nine display cases of at most320s and the complete unchanged ten-case CLI BIOS
matrix of at most1730s. Host runtime bound5000s, aggregate guest bound4610s.
The parent-loss test uses only the existing first-entry root case15 selector;
no executable, register, quota or clock modification. Independent replay checks
all pixels, directory/leaf flags, generations, zero staging, complete task reap,
exact committed tile counts, ordinary CLI liveness and unchanged media. The old
CLI binary-memory, CPU, IPC, PIO, terminal and object oracles remain mandatory.

## Candidate02 stopped: original first-close deadline predicate

Candidate01 stopped at gate7 on a single extra blank line in the disabled boot
projection, after six passing host groups and before any qualification guest.
Candidate02 corrects only that exact insertion seam and the media-host adapter;
the actual build04/media04 inputs remain identical. Gates1..8 and all nine
display guests pass, including exact pixels, quota, parent loss and independent
raw replay. Four CLI positives pass; the fifth captures a complete hang/recovery
run but fails the unchanged first-request-close timing predicate. No negative
CLI guest or later gate was executed.

Raw evidence: broker receive returns ETIMEDOUT at its original4840ms deadline.
Both subsequent successful IPC_CLOSE call/return pairs occur4850ms. Reply close
wakes the child with EPIPE4850ms before its original3890+1000ms receive end.
The accepted CLI contract line118 explicitly retains the first request fence
at the broker deadline. Its current observer requires that first CLOSE call
to share the deadline's exact clock sample. This candidate does not satisfy
that frozen predicate; no successful graphics result overrides it.

The read-only diagnosis is retained as `hang02-diagnosis.json`, with all original
raw files, and reproduces the old failure. A contract decision is pending:
either explicitly qualify processing deadline separately from bounded endpoint
cleanup, or implement a separately scoped kernel deadline fence. No such
decision, new protocol, weakened gate, renewed lifetime or package acceptance
is inferred from the diagnostic. Cumulative18 physical guests896.0434498001705s,
four kernels/twelve BIOS assemblies/four publication attempts remain recorded.

## Renewed continuation: processing deadline and bounded cleanup

After the timing-contract alternatives were presented, the user again ordered
completion. Continue with the proposed smaller verification correction, using
the original application contract's separate processing lifetime and cleanup
bounds (NATIVE_APPLICATION_FILES_CONTRACT.md164..170). This explicitly replaces
the inherited first-CLOSE-in-the-timeout-tick assumption only for this display
qualification. Historical CLI source and its failed candidate remain unchanged.

The new private adapter requires the original broker receive timeout at exactly
its absolute deadline. From that completed timeout through the child's actual
wakeup, the only recorded root operations may be the two complete successful
request/reply CLOSE pairs, ordered after timeout. Every call/return timestamp
must be monotonic. Actual reply-close return must equal the observed EPIPE
wakeup and occur strictly before the child's original1000ms receive deadline.
No additional broker work, missing/failed close, deadline renewal, arbitrary
tick slack or inferred completion is accepted. All other capture, object,
CPU, IPC, PIO, memory, terminal, retirement and no-write predicates remain.

Red/green and negative mutations precede candidate03. Reuse is permitted only
with exact runtime sources, tools, image, media and complete raw-file hashes,
and independent replay of nine display and five CLI captures. The prior failed
hang result remains failed in its original receipt. Run exactly the five
missing BIOS negatives under their unchanged20/30s individual bounds and120s
aggregate; no kernel or media rebuild. Twelve gates and complete final replay
remain mandatory before a local commit.

Correction window spent three host commands: initial missing-import failure,
the actual legacy-predicate red regression, then all five test methods green
(14.655s), including adversarial cleanup mutations. Candidate03 command limits
are six host gates600s each, build binding180s, media300s, runtime1200s,
reference180s, independent review900s, scope180s. Runtime reserves five fresh
negative guests120s total and14 retained complete captures; zero new builds
or media publications. All original stopped receipts remain immutable.

## Accepted candidate03

All twelve frozen gates passed, including all nine original display captures,
the five complete CLI positives, five fresh BIOS negatives and independent
raw replay of all19 cases. The corrected hang evaluation passes while its
original candidate02 failure remains unchanged. New negative guest time is
107.87658979999833s; cumulative23 physical guests1003.9200396001688s,
four kernel builds/twelve BIOS assemblies/four media attempts. Build04/media04
were reused with exact complete source/tool/artifact bindings. Acceptance seal
and final clean-child-commit receipt reside under
`build/codex-agent/r83be-display/candidate03/`. This is the bounded QEMU display
boundary only; the explicit exclusions and remaining native64 work still apply.
