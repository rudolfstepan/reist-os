# Native64 graphical session contract (R8.3bi)

Status: frozen implementation package, 21 September 2026. Not accepted.
Baseline: `63e20d3dd597994cb53b6172fa1639f81e6c3435` (BH).
Authority: the approved `NATIVE_GRAPHICAL_SESSION_PROPOSAL.md` and standing
interactive completion instruction. One implementation transaction, no agents.

## Inventory and boundary

BH supplies explicit terminal service authorization, acquisition and revocation.
Native CREATE-v6 already supplies periodic32 CPU samples/1000ms; eight task
slots, eight IPC capabilities/task, sixteen endpoints and depth-four messages
are unchanged. Device operations30/31 already mediate framebuffer/i8042.
The old input profile remains5000ms/32events. No new kernel mechanism is planned.

`desktop_wm.c` and `desktop_surface.c` already implement bounded focus/capture,
generation-scoped surfaces and Surface-v6 validation. Reuse these implementations
without porting the large i386 desktop or its device/filesystem authority.
Surface-v6/API2 preserves local coordinates, configure/ACK and paint commit;
its documented wl_surface/xdg_toplevel references do not imply compatibility.
PS/2 decoding and initialization reuse `userspace/drivers/ps2/native_input.c`.

The accepted root image ends at0x43f108, leaving3832 bytes in its192KiB interval.
The graphical profile therefore loads its compositor/input/client programs
from immutable files and verifies their prepared RNPGv2 bytes against hashes
bound into the signed root image, before import or any grant. SHA-256 uses the
pinned Mbed TLS4.1.1 archive and FIPS180 terminology. The hash covers all262240
bytes preceding the separate4096-byte startup arguments; role arguments are
constructed by the supervisor. No authority follows merely from a path or ELF.

## Roles and dependencies

Opt-in NativeGraphicalSession requires NativeTerminalService. Normal shell
command `desktop` resolves `/desktop.prg` using the existing search rules.
The root remains slot0; storage dependencies2/3 retain their current profiles.
Compositor4, PS/2 worker5 and two distinct application processes6/7 receive
explicit periodic profiles. Only compositor4 has terminal and display rights;
only worker5 has input-device rights. Clients have no terminal, global input,
device, filesystem, task-management or identity-query authority.

Root owns one supervisor/compositor control endpoint. Compositor owns three
single-peer endpoints: raw input and two Surface channels. Root communicates
the exact generation handles through its trusted control channel; compositor
delegates each endpoint only to that role. Root has no raw-input capability.
All roles, epochs, message sizes and sequences are checked before mutation.
No sibling identity query or implicit inheritance is assumed.

The common shell remains the launcher and serial recovery interface. Two
packaged Surface applications exercise text entry and interactive painting;
normal exit returns to the shell after fencing and reap. This package does not
claim a port of the full file manager, browser, scripting or all i386 applets.

## Frozen runtime budgets

- Existing CPU32 samples/1000ms, task creation8/1000ms, restart2/10000ms,
  IPC depth4, per-call timeout<=1000ms, ATA200ms, input64 operations/100ms,
  display64 operations/100ms and native heap512MiB hard cap remain unchanged.
- Fixed startup allocations only: compositor<=2MiB total, root<=4MiB including
  existing file workspace and prepared images; applications<=64KiB each.
  These are component allocation limits, not a claim of smaller kernel quotas.
- Up to four immutable GUI captures, each using the existing120000ms/512KiB
  file bound; complete launch480000ms. Hashing uses<=65 chunks of4096 bytes,
  deadline2000ms and bounded sleep between chunks. No renewed capture deadline.
- After files are admitted, role/endpoint/device/self-test handshake<=3000ms.
  READY requires terminal acquisition, driver self-test, both configured
  applications and first visible committed frame. No READY from profile alone.
- Service loops sleep10ms, inspect at most8 messages or controller reads per
  turn. Health every250ms, health expiry1000ms, individual sends<=100ms.
  Input<=128 events/1000ms including health, monotonic64-bit sequence; Surface
  <=128 requests/client/1000ms, pending events<=16. Excess isolates the role.
- Rendering uses fixed64x64 BGRX tiles, at most4 commits/turn and bounded
  dirty rectangles. Feedback work precedes bulk redraw. Full redraw is paced;
  no full-screen busy wait or unbounded queued frames.
- Recovery fence/revoke precedes cancel/reap. Each wait<=1000ms, whole group
  retirement<=5000ms. Health loss, crash, malformed reply, exhausted quota and
  manual recovery share this path. Restart admission uses the existing root
  budget; no counter reset on GUI entry or shell return. Exhaustion latches
  degraded graphical state. Serial input resumes only after confirmed fencing.
- Lifetime may continue across finite periods; each operation, queue and
  health interval is bounded. Counter/clock wrap is an error, never renewal.

## Failure model and required proof

Client loss revokes its generation, focus and capture without killing the
unrelated client or compositor. Driver/compositor loss fences the graphical
group before recreation, self-test and reintegration. Active root loss AFTER
READY must prove protected terminal/display/input revocation and child cleanup;
BH's before-handoff root-loss guest is not substituted for that proof.

Host behavior tests execute actual lifecycle, hash admission, WM/Surface and
input code at O0/O2; reject malformed/stale/foreign messages, partial startup,
overflow, deadline and quota edges, and demonstrate bounded cleanup. Hash KATs
and altered prepared header/page/rights/zero-fill cases run actual vendor code.
Exact opt-out source/build projection retains BH and all previous profiles.

Fresh QEMU GUI matrix: HDD4GiB and floppy8GiB normal sessions lasting>5000ms
and delivering>32 events, focus/capture/release and local-coordinate checks,
client crash/hang/quota/malformed message with unrelated-client liveness,
driver crash/hang/quota, compositor crash/hang/quota, lost control reply,
active parent loss, stale generation after restart, restart exhaustion,
and corrupted service file before authority. Exactly eighteen GUI guests,
each<=180s, aggregate<=3240s. The inherited ten CLI/media cases remain fresh
with their unchanged individual limits and1730s aggregate. Runtime gate5400s.
Independent replay checks raw IPC, task/profile/parent and lease/device state,
pixels, input events, reap and immutable media, not success strings alone.

Signed BIOS HDD/floppy formats and boot capacity1391616 remain unchanged.
The distinct graphical read-only EXT2-1KiB data volume has32 inodes and fixed
nine-file set, within1MiB. Old five-file layouts and seven tool bytes remain
reference artifacts. Both PowerShell and Make paths package the same files.
The ordinary graphical starter pins accepted artifacts only after all gates.

## Execution reservation

Initial development: at most16 host commands<=600s, one fresh common build<=300s,
one signed media publication<=180s/three BIOS assemblies, one healthy diagnostic
guest<=180s. First unexpected failure stops its window for evidence review.
Record every attempt under `build/codex-agent/r83bi-graphical-session/`; no
unchanged retries, resets or reuse as fresh qualification.

Qualification freezes eight gates once: new hosts600s, existing desktop hosts
600s, existing Surface hosts600s, package180s, runtime5400s, reference180s,
independent raw review900s, scope180s. No implementation edits during gates.
Scope review, queue completion and local commit follow all passes. No push.
R3.6b remains deferred. No network/DMA/USB/write/SMP/physical authority added.
