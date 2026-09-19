# Native foreground terminal lease — R8.3av

User continuation explicitly approves the preceding bounded foreground-child
delegation question. Baseline clean c183fef0 after accepted53dd42d5/AU final
receipt8a2633907e2e0c4f. One interactive main-worktree transaction; no agents,
push or physical media. This is an authority mechanism prerequisite, not normal
shell namespace/launch integration or completed64-bit OS.

## Existing standard and identity

Reuse REIST single-terminal foreground ABI127/v1,24-byte request and existing
ATTACH1/TRANSFER2/RELEASE3/CHECK5 meanings and negative errno semantics. This is
the documented bounded adapter, not POSIX termios/process-group compatibility.
ACQUIRE_SERVICE4 remains unsupported(-95). System V AMD64 transport and all
existing numbers/layouts stay unchanged. Native GETPID is the nonreused positive
task generation; target_pid and target_generation both name that identity, not
the reusable slot. A bounded eight-slot lookup resolves the authoritative task.

## Opt-in and least authority

NativeTerminal requires NativeServiceConsole/LiveFile; old/default selectors
remain exact. Root0 gets syscall127 in its existing extended profile. An own
child must explicitly request READ15,WRITE20 and TERMINAL127 together under
parent attenuation, with no PIO or task-management grant. Old profile admission
continues to deny these bits. FS and driver profiles remain unchanged and denied.
No inheritance from file bytes or parenthood; no nested transfer/service acquire.

At most one foreground child. Root retains diagnostic output; while a child
holds the lease root READ/CHECK return EAGAIN(-11), and only the exact leased
child may read/write. Eligible but unleased child IO is EACCES(-13). Root ATTACH
is idempotent; TRANSFER requires its own live eligible generation, identical
transfer is idempotent, a different active target is EBUSY(-16). Missing/stale
target is ESTALE(-116). Child RELEASE is idempotent and cannot revoke another
owner; CHECK is0 only for the foreground identity, otherwise-11. Root RELEASE
and child ATTACH/TRANSFER are denied. Validate size/version/reserved/unused
arguments, complete pointer extent, identity, parent and rights before effects.

Fixed state only. No waits, allocations or formatted output. Discard at most64
pending RX bytes only on a real ownership transition, with one final status
check. UART error or still-ready input fences userspace console, never grants
the next owner or panics/reboots the kernel. This preserves generation isolation
of queued input without an unbounded drain; ordinary empty FIFO costs one read.
Existing64-byte mediator limit, SDK bounds, CPU32/1000ms service period, IPC/
ATA/session deadlines and all scheduler resources stay unchanged.

## Lifecycle and proof

Use common family_terminal64 before profile/IPC/heap retirement: child exit,
fault, CPU exhaustion and cancellation revoke the exact lease and restore root
input; root loss removes all terminal authority before descendant retirement.
Cleanup is idempotent and generation-scoped; slot reuse never revives a lease.
Malformed private state fails through the existing physical-fence/fatal path,
not in-place repair. Normal UART exhaustion only fences this console domain.

The existing independently loaded ELF child requests explicit eligibility,
proves pre-transfer denial, then actual delegated IO and CHECK/RELEASE. Root
proves foreign/driver/FS/stale rejection, exclusive input, duplicate transfer,
reclaim and fresh generations while original live file dependencies remain.
Retain the complete25-case AR lifecycle/media/CPU/fault/OOM oracle and add raw
terminal/profile/request/return/IO/state evidence. Add two bounded corrupt-state
guests proving fail-closed routing. No serial-marker-only or fabricated success.
A compact separate assembly fixture is permitted only for this profile to keep
the existing1280-byte/eight-RPC file bound; preserve startup/IPC/GO/fault checks.

Actual NASM state/admission/adapter and modeled-device tests at O0/O2 precede
build. Regress invalid pointers/arguments/rights/generations, repeated cleanup,
every return path, bounded dirty FIFO and malformed state; no test-only runtime
logic. SDK tests cover real requests and legacy no-effect fallback. Retain
existing console/CPU/pool/file/shell host groups; old producers and disabled
kernel sections must compare exactly, not just compile successfully.

Queue freezes14 gates, one new image,25 normal plus2 fatal guests,45s each
including cleanup<=3s/1215s total. First failure stops. Sources, tools, artifacts,
raw evidence and every failed window stay bound under ignored r83av-terminal.
Standing authority allows separately frozen evidence-directed corrections,
never unchanged retries or weaker gates. All gates and direct scope/ABI/bounds/
cleanup review precede local implementation commit. Then continue native work.

## Qualified result — 2026-09-19

All14 obligations passed:233 host tests and27 qualified guests (the complete25
normal lifecycle/media/CPU/fault/OOM cases and two corrupt-generation cases with
physical device fencing, IF0 and halt). Candidate05 reuses nine exactly bound
gates and executes five fresh gates; final review replays every raw case.
Image SHA256: e2e9172277e67edcf0cbb932a6ba1d725e995ec48723d8f6c42135653c130e10.
The actual file-loaded ELF64 client is1272 bytes within the unchanged1280-byte
bound. Exactly two cumulative images and31 physical guest attempts consumed
502.3338371000136s, retaining all failures and the diagnostic-only control.

The reviewed seal6de066070d27b69967fd442fc57d6c5f6c4791fe5642a4f33c00bbeb1be93105
binds6425 evidence files. The subsequent clean local implementation commit is
bound by `build/codex-agent/r83av-terminal/candidate05/verification-status-terminal-final.json`.
No quota, deadline, existing lifecycle oracle or shared transport was weakened.
This qualifies only the bounded native terminal mechanism and its integration
fixture, not normal-shell namespace/file/launch integration, a complete64-bit OS
or hardware acceptance. Those remain separate completion work.
