# Native full desktop: bounded display throughput decision

Status: proposal only, 24 September2026, clean accepted baseline3cad8aef.
No implementation package is active. The user prioritizes the real native
VMware desktop and explicitly requests faster execution. BV is accepted;
its evidence-reuse approval does not silently expand device quotas.

## Measured source boundary

The real desktop.c native workspace inventory is accepted (BW/BX):61 native
platform imports,897542 conservative allocated section bytes and7291652
startup workspace bytes. This source, its menus/window manager/explorer and
ordinary application dispatch remain the target. native_desktop.c is the
rejected two-client prototype, not a substitute delivery. QuickJS expansion
is behind the requested visual desktop integration.

NATIVE_DISPLAY_CONTRACT.md and the actual native display core freeze:
64 commits and1048576 bytes per100ms, at most64x64 BGRX pixels/16384 bytes
per operation. Exceeding that budget fences the display. Native mappings use
supervisor-only UC PAT index3. The prototype adds four tiles per100ms.
Thus its640x480 repaint needs80 tiles/20 batches, at least1900ms spacing.
A1024x768 full frame needs192 tiles/3145728 bytes: even without that extra
throttle, the kernel budget requires at least three windows (200ms spacing).
These are exact capacity lower bounds, not measured host latency or a claim
that every interaction redraws the whole screen. Source references:
arch/x86_64/video/display_core.inc, display_domain.inc,
userspace/gui/compositor/native_render.c and native_desktop.c.

## Explicit bounded opt-in requested

Authorize a separately selected native full-desktop display profile:

- At most1024 commits and16777216 bytes per100ms for one explicitly delegated,
  generation/epoch-bound compositor. Old64/1MiB grants remain unchanged.
- Keep the exact64x64/16384-byte per-call bound, complete pointer/range checks,
  fixed kernel staging tile, private RAM ownership and fail-closed fencing.
  No whole-screen syscall, user framebuffer mapping, raw device, PIO or DMA.
- Append an explicit bind/profile ABI; no implicit upgrade by program name,
  larger request size or old bind. Root authorization remains mandatory.
- CPU admission, health/restart budgets, IPC quotas, heap hard limits and
  per-operation deadlines remain unchanged. This does not authorize any
  native persistent-write, network or new process-management domain.
- The Ring3 renderer keeps a fixed dirty set, coalesces work, prioritizes
  input/health and reserves its own finite window budget before committing.
  Exhaustion defers bounded pending work; malformed/stale requests still fail.
- Inventory optional cache optimization against existing i386 framebuffer
  practice and architecture rules. Admit WC only with proven platform/cache
  semantics and no conflicting alias; otherwise keep UC and report the
  performance profile unsupported. Never infer WC from a PTE bit alone.

The higher ceiling permits bounded multi-megabyte frames. It is not a
throughput, FPS or latency promise; those must be demonstrated on VMware.
No blanket increase in vCPU count or replacement of the genuine desktop.

## Required acceptance after authorization

Freeze one cohesive display-mechanism transaction before code changes.
Host behavior covers old quotas byte-for-byte, exact new caps, zero-write
rejection, stale generations, forged profiles, rollback and fencing.
Real guest proofs cover actual copies, boundary exhaustion, retirement and
new generations while the serial supervisor remains alive. Preserve all
prior evidence; reuse only demonstrably unchanged captures under the user's
explicit reuse approval, with complete validation of changed behavior.
Follow with real desktop SDK/service integration and VMware input/frame/
window movement/application dispatch/recovery measurements. Publish the VM
for visual testing only with accurate supported-function status. BV and
these prerequisites do not finish the complete native OS. R3.6b stays deferred.
