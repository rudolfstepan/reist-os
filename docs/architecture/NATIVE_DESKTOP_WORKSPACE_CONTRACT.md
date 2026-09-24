# Native desktop bounded startup workspace (R8.3bx)

Frozen2026-09-24 after accepted host inventory5f0debf9. User priority remains
full native VMware desktop; no prototype substitution. BV remains preserved.

Failure domain: all-or-nothing allocation of the real desktop's fixed startup
workspaces. Existing native heap hard cap512MiB is unchanged. Component budget
8MiB, at most16 startup allocations, no growth or allocation inside rendering.
Use standard C typed objects, existing malloc/free SDK entry points and ELF64;
no new ABI/syscall, raw address, DMA, namespace or persistent-write authority.

Move16 largest desktop-owned objects from static zero-fill to fixed-size native
workspace slots only when REIST_NATIVE_DESKTOP_WORKSPACE=1. Keep every original
capacity and the exact old i386/default code path. The wrapper validates all
sizes before first allocation, zeros all admitted memory, frees partial state
on any failed allocation, calls the unchanged desktop body only after complete
initialization and clears/frees every slot on normal return. Repeated destroy
is harmless; repeated initialization cannot replace live ownership. Abrupt
process failure remains owned by the existing generation-scoped kernel reap;
this package makes no new guest claim. The next runtime adapter must prove
allocation/handshake CPU bounds, native process failure/recovery and rendering.

Scope: queue allowed_files only. Header/core, actual desktop.c wiring, explicit
inventory-builder selector and host behavior/disabled-projection checks form
one allocation/cleanup boundary. No service stub, kernel change, executable
image/media publication or unrelated performance adjustment.

Eight development host commands<=180s each. Three frozen gates exactly once:
1. python test/test_x86_64_desktop_workspace.py -v (<=180s): actual allocation
   core O0/O2, each of16 failure sites, budget overflow/zero, reentry, complete
   initialization, normal return status and idempotent cleanup; default source
   projection identical to5f0debf9.
2. python scripts/build_x86_64_desktop_inventory.py --output
   build/codex-agent/native-vmware-desktop/workspace-default01 (<=180s): linked
   default object SHA256 identical to qualification01.
3. python scripts/build_x86_64_desktop_inventory.py --native-workspace --output
   build/codex-agent/native-vmware-desktop/workspace-native01 (<=180s): real
   full desktop builds, static reachable section sum below960KiB, all previous
   platform imports retained and only malloc/free added. This is a conservative
   host bound, not a PT_LOAD/native capture/runtime acceptance claim.

Native desktop SDK/IPC/files/assets/application lifecycle adapters and VMware
latency/recovery acceptance follow in subsequent frozen transactions. Do not
mark the full desktop complete from these host gates or launch this ET_REL file.

## Host acceptance24.09

Development01 confirms absent implementation with a compiler failure; host02
passes O0/O2 lifecycle and complete default-source projection. Development03
builds the native full desktop in11.886s. Three of eight host slots spent.
All three frozen gates pass once: behavior/projection1.200s, exact original
object rebuild13.983s, native36-source build13.963s. Evidence:
build/codex-agent/native-vmware-desktop/workspace-gates01/results.json.
Native workspace7291652 bytes in16 unchanged-capacity allocations, within8MiB.
Static reachable section bytes897542 (zero-fill252084), down from8187060.
The default object remains SHA256
fe63724133e5f3022efe450432c6cc2f9ee8b5f09be25ef1d8ef073621ab814f.
The native import set is exactly the old59 services plus malloc/free.
No native guest/desktop/latency claim; the source selector remains opt-in.

Integration dependency found: shell_graphical.inc still captures/hashes/imports
RNPGv2 and the graphical roles have a196608-byte linker span. The real desktop
requires the approved larger image profile plus complete immutable capture;
BV is a functional prerequisite, not merely QuickJS work. Its paused source
must be reconciled after this commit without dropping the accepted desktop
work or resetting historical attempts. Runtime SDK adapters/rendering remain
required after the loader/capture boundary is qualified.
