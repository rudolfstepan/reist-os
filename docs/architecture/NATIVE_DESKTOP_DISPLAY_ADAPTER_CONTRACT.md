# Native desktop software display adapter (R8.3ca)

Frozen on clean36feeecc. Boundary: the real desktop's private Ring3 raster and
presentation queue. Implement its existing x86os display functions, not another
desktop. Standard references: packed XRGB8888, Unicode UTF-8 and existing
CP437 glyph mapping, half-open pixel rectangles, errno-style negative results.
Native adapter-v1 queues presentation: successful frame commit publishes the
private completed image and damage, not synchronous physical scanout or vblank.
A bounded pump submits complete64x64-or-smaller tiles through an injected
generation/epoch-scoped transport. It never creates authority or maps devices.
Actual native transport/lifecycle integration and guest proof are subsequent;
these host tests alone cannot justify a bootable desktop or latency claim.

Maximum1024x768 pixels, two caller-owned disjoint3MiB buffers, one16KiB tile,
fixed192-bit damage sets and64 send timestamps. No allocation during rendering.
Framebuffer memory is separate from the unchanged BX16-slot startup workspace;
future runtime integration must account for both within the existing heap cap.
Attach validates all inputs before writes and requires increasing nonzero epoch.
Deactivate/detach revoke local presentation; transport failure/clock reversal
latches failure until a fresh attach. Never retry failed physical submissions.
Admission errors have no raster/presentation side effect. Cancel restores the
unpublished frame boundary; no frame contents reach transport before commit.
One staged blit per frame captures the previously committed image and is applied
at commit, preserving later drawing order of the original API where applicable.
The existing desktop stages before drawing. For native adapter-v1, staging
after frame drawing returns ENOTSUP before changes so the existing full-redraw
fallback runs; copying a modified source would require a third snapshot buffer.
Unsupported acceleration/shared surface objects return ENOTSUP, never success.

Existing kernel caps remain64 copies/1MiB per100ms and16KiB percopy. Enforce
a conservative sliding100ms history using post-submit timestamps. A pump call
submits at most8 tiles, never waits, and leaves remaining damage coalesced.
On a full history return a next eligible monotonic time; callers must service
health/input and wait through their existing bounded scheduler, not busy-spin.
Cursor updates dirty only old/new cursor tiles and compose over output copies.
No new quota, display grant, process, filesystem, network or persistence rights.

Eight development host commands<=180s each. Three frozen gates<=180s once:
1. python test/test_x86_64_desktop_display.py -v
   Real C adapter O0/O2: invalid attach, clipping/overflow, strict UTF8,
   exact pixels, frame commit/cancel/stale serial, overlap blit, pointer overlay,
   bounded queue/quota, clock reversal, failed transport, detach/reattach epoch.
2. python scripts/build_x86_64_desktop_inventory.py --output build/codex-agent/native-vmware-desktop/display-default01
   Accepted original desktop object stays byte-identical.
3. python scripts/build_x86_64_desktop_inventory.py --native-workspace --native-display --output build/codex-agent/native-vmware-desktop/display-native01
   Actual production desktop links with adapter; remaining import set is exactly
   the workspace import set minus implemented display entry points. Keep960KiB
   conservative static bound. No placeholder for unresolved non-display services.

Only queue allowed_files may change. Logs and measured evidence under ignored
build/codex-agent/native-vmware-desktop. Freeze any evidence-directed correction
window without resetting failed attempts. Keep the proposed higher quota pending.

## Host acceptance2026-09-24

Four of eight development commands spent. Development01 retains the expected
missing-implementation failure. Development02 reached the quota test but its
assumption of an empty history was wrong after earlier rendering; development03
corrects only that setup by advancing the fake clock100ms. Development04 also
covers strict umlaut mapping, aliased text denial, stage-after-draw fallback,
800x600 edge tiles and deactivation/reactivation. O0/O2 both pass.
All three frozen gates pass once1.278/5.658/6.332s. The original desktop object
is byte-identical. The real37-source native partial link resolves exactly16
display imports and retains45 actual non-display platform imports, with919891
reachable allocated section bytes below960KiB. No non-display service stub.
Evidence: build/codex-agent/native-vmware-desktop/display-gates01/results.json;
source digests agree before/after gates. The private attach/pump API still needs
supervised startup and event-loop integration, actual resource/lifecycle proof
and VMware presentation/input measurements. No bootable/runtime acceptance.
