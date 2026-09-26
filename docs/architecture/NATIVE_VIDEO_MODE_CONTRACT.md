# CK: native64 bounded VMware mode transition

## Authority and baseline

2026-09-26 user `mach weiter` immediately following the explicit question
for proposal4a10641a authorizes NATIVE_VIDEO_MODE_PROPOSAL.md. Accepted
implementation baselinef96af9f6; proposal commit4a10641a is clean. Exactly
one implementation package R8.3ck-video-mode. CB stays queued and archived.
This is the hardware prerequisite; a test surface is never a desktop claim.

## Frozen boundary

Only opt-in NativeVideoMode, layered on CJ text console. Existing default,
CJ and graphical boot-framebuffer profiles retain identical behavior/bytes.
PCI15ad:0405, VGA80x25 and1024x768x32 only; oneCPU, signed BIOS media.
Ring3 owns mode sequence, status polling and presentation policy. Ring0
validates fixed register operations, identity/generation/epoch, mappings and
bounded UPDATE-only FIFO publication. No arbitrary register/port, PCI config
write, raw MMIO, DMA, IRQ, 3D, task/CPU/heap expansion. Device apertures must
be positively established within non-RAM/non-overlapping firmware resources;
device-size registers alone are not proof of an otherwise unknown BAR size.
If read-only inventory cannot establish the virtual platform aperture, stop
that platform before hardware mutation and report the concrete missing input.

Private appended DEVICE_CONTROL resource34, request v1 exactly64bytes.
Operations bind/fence/query/step/heartbeat/status; unused fields zero.
Parent authorizes exact direct child after old reap; service-only hardware
steps. State and inverses sealed; corrupt state enters existing kernel failure
path, invalid requests cause no side effects. Every state change follows full
request validation. No caller can supply a physical address or hardware value.
Monotonic time<2^60; health1000ms, start/return absolute2000ms, two restarts
per10s, no renewal on intermediate success. Existing tighter limits prevail.
Mode-state transitions TEXT/PREPARING/GRAPHICS/REVOKING/TEXT. Timeout/error
fences old operations before fixed disable; reintegration requires self-test.

Geometry exact1024x768x32, pitch4096; framebuffer visible extent3MiB inside
verified aperture. Supervisor-only NX/UC mapping; staged existing display
copies <=16KiB, unchanged per-window quotas. Optional FIFO mapping4KiB only,
MIN/MAX/NEXT_CMD/STOP checked each time, one fixed20-byte UPDATE per commit,
no partial publication on full queue, no kernel waits. Overflow/overlap and
hardware echo mismatches fail closed. Nothing maps arbitrary RAM as MMIO.

## Cohesive delivery and userspace dispatch

Normal boot remains the real CJ shell. Package `/video.prg` on the ordinary
shell search path in both producer layouts as the bounded hardware exerciser.
Root captures the authorized images through the existing read-only path,
retires text-console4, starts renderer4 and mode/input-driver5, and binds
their attenuated roles. Mode worker has device34; renderer only existing
display30. Storage2/3, root0, future applications6/7 remain unchanged.
Only the driver chooses hardware steps. Root waits with existing health
probes and finite deadlines, fences devices before reaping, then recreates
the VGA console and verifies its health before returning to the shell.
Persistent driver role may later serve the existing desktop; CB restoration
and its original full desktop gates remain a subsequent clean transaction.

Original graphical/PS2/terminal isolation remains. Failures at preparation,
graphics and return must not leave mixed text/graphics writers. Unrecoverable
hardware return degrades visibly where possible and retains COM1; it is a
failed hardware acceptance, never a successful recovery record.

## Frozen gates, each once per qualification, first failure stops

1. `python test/test_x86_64_video_mode.py -v` <=180s: actual core atO0/O2,
   invalid/stale/foreign requests, sealed state, identity/aperture/overflow,
   fixed register ordering and FIFO wrap/full/corruption before effects;
   actual Ring3 policy through a transcript harness including bounded waits.
2. `python scripts/verify_x86_64_video_mode.py --defaults` <=600s: exact
   unchanged CJ and default delivery artifacts againstf96af9f6; carry existing
   accepted dependency evidence with exact source/tool/artifact provenance.
3. `python scripts/verify_x86_64_video_mode.py --package` <=600s: selected
   kernel/userspace build, fixed stack/storage/undefined-symbol checks,
   signed media, normal userspace dispatch and both image-layout bindings.
4. `python scripts/verify_x86_64_video_mode.py --runtime` <=1200s: fresh QEMU
   VMware-SVGA guest proofs, <=90s each/<=900s aggregate. Healthy repeated
   text/graphics/text plus actual post-return keyboard/prompt/cursor; crash
   and hang in preparation/graphics/return; restart exhaustion. Real pixels,
   generation/device/profile/page snapshots and immutable media; independent
   replay rejects edited evidence. No source-only runtime claims.
5. `python scripts/verify_x86_64_video_mode.py --review` <=600s: independent
   full evidence/source/tool/scope replay and actual VMware healthy and driver
   fault/return proofs, <=180s each, exact owned-process cleanup. Reuse CJ
   host cleanup handoff, correctly preserving JSON timestamps as strings.

Final direct diff review and local commit only after all gates pass. Never
push. No nested agent. Scope is the exact queue allowed_files; additions
require prior inventory/freeze under the existing interactive directive.

## Development window01

At most8 host invocations<=180s, two selected builds<=300s, two media builds
<=180s, two read-only device-inventory guests<=60s, four diagnostic guests
<=90s and one actual VMware diagnostic<=180s. All start from fresh directories
under build/codex-agent/r83ck-video-mode and retain failures. Not acceptance.
No unchanged retry. Administrative reservation exhaustion records results and
freezes the evidence-directed next finite window without routine permission.
