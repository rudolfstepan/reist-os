# Approved native full-desktop startup profile (CF)

User approval2026-09-25: "ja mach weiter" directly answers the explicit10-second
request. CB is paused as a byte-verified immutable integration fixture:
services-before-start-profile01/files.zip SHA256
ee40925bd41d0f0c2ab1b66dff19e1a786fc1b6d7f6a60c78367985a18760615;
stash67d302f507d02f2d4383a9936eb024f7be25e8af; baseline0af9682e.
All73 CB host commands/45 builds/23 media/27 guests remain spent; no CB gate passed.

## Profile and scope

Existing graphical control-v1 and Surface-v6 wire formats unchanged. Monotonic
milliseconds use the existing absolute-deadline convention. Explicit full desktop
selects10000ms STARTING, including replacement; old builds retain3000ms exactly.
No progress renewal. Bind overflow/late/replay fail before mutation. First actual
ready health transitions to unchanged1000ms health. CPU32/1000ms, restart/reap,
IPC deadlines, task/image/heap limits, device and read authority unchanged.
The compile selector is private and consistent across root, input and clients.
No new public syscall, protocol, rights or persistent format.

## Frozen verification and reservation

Exactly one active package CF. Allowed files are frozen in the executable queue.
Twelve development hosts<=180s, four role builds<=180s, two integration builds
<=300s, two media<=180s, two diagnostics<=600s; count failures without reset.
Final gates once: host test<=180s; defaults<=600s; runtime<=1800s;
review<=300s. A failed gate stops that qualification and preserves evidence.
Host runs actual lifecycle/role parser at O0/O2 in old/full profiles, boundaries,
overflow, stale epoch/owner/sequence, no renewal, replacement, health and cleanup.
Defaults builds old role artifacts byte-exact against accepted baseline and
compiles the new profile. Runtime uses archived CB only as a hash-bound fixture
with declared profile wiring substitutions, restored exactly after execution;
no independent CB implementation or acceptance. Require real frame/input/both
apps, deadline cancellation/reap, replacement, and unchanged CPU exhaustion.
If immutable fixture prevents these proofs, record the concrete failure before
freezing any evidence-directed next transaction; no weakened gate or fake pass.
Review independently replays source/artifact/fixture/result bindings and scope.
After success only, resume CB and its original five gates/eight fresh guests;
VMware visual/performance remains mandatory for delivery.

## Development evidence01 (2026-09-25)

Hosts01 toolchain warning failure;02 expected missing full profile;03 passes
actual lifecycle/parser O0/O2 old/full. Role builds01 baseline completed but
wrapper rejected relative result path;02..04 complete, all four disabled role
ELFs byte-identical, opt-in variants distinct (defaults-dev02/result.json).
Integration build01/media01 pass. Diagnostic01 fails46.9142524s, desktop slot4
owner15 reaches exact32-sample quota in periodic window3 at tick3355; total84.
Input/apps/storage all reaped, original media hashes unchanged, fixture restored
byte-exact. The extended deadline did not expire (root error-32/stage4).
Aborted RIP0x46367a maps to desktop_entry_call, requiring syscall caller evidence.
No final gate, no startup/runtime acceptance. Use remaining diagnostic02 with
hardware syscall observer on the same immutable media, <=600s, no guest memory
writes; this is a new observation, not another unchanged acceptance attempt.
Remaining: hosts04..12, integration build02/media02; guest02 reserved for observer.

## Development evidence02 and concrete scope boundary

Observer diagnostic02 fails45.395759s.169 exact hardware-observed SDK
calls:87 MONOTONIC_MS,38 IPC receive,17 SLEEP,9 malloc,8 send,3 delegate,
3 identity and other3 calls. Recorded callers predominantly channel_clock,
channel_root, channels_input and launch_pump; only6 workspace allocations
completed. CPU exhaustion, not the10s startup deadline, terminates the desktop.
No guest-memory writes. Observer timing is not performance acceptance.
Both VMs/debuggers closed; signed media unchanged; temporary27-file fixture
restored exactly. Guest aggregate92.310012s. Both reserved
guest attempts spent; no unchanged retry and no final gate claimed.

The required correction is in the archived CB SDK pump/allocation scheduling
(desktop_platform.c/desktop_startup.c), not in CF's bounded profile constants,
role argument parsing or role wait bounds. Those source implementations remain
outside CF allowed_files and the immutable-fixture rule forbids silently changing
them. Before implementation, report this architectural dependency and freeze
an explicit corrective scope/transaction preserving both CF and CB final gates.
The longer profile itself is implemented and host-tested but not accepted;
CF cannot be committed as complete from host/default proofs alone.

## Explicit SDK correction continuation (2026-09-25)

User "ja mach weiter" directly answers the documented out-of-scope SDK CPU
blocker and authorizes this limited extension. Same active CF transaction;
CF candidate before correction preserved in before-sdk-correction01/files.zip.
Add desktop_platform.c, desktop_startup.c and their actual platform host test
from the immutable CB archive as editable CF inputs. All other CB fixture files
remain immutable apart from already frozen profile wiring. Default profiles,
CPU32/1000ms, post-ready health, memory/rights and every CF/CB gate unchanged.
On CB resume preserve these corrected files instead of overwriting from stash.
Evidence-directed scope: bounded startup allocation pacing and redundant pump/
console work, with original deadlines, rollback detection and IPC validation.
Reserve hosts04..12 (original remaining), builds02..04<=300s/media02..04<=180s,
guests03..05<=600s; original counts retained. First tighten actual host regression,
then one changed guest per evidence-directed candidate; no unchanged retries.

## Correction evidence03/04 preparation

Host04 reproduces insufficient allocation pacing;05 passes actual SDK O0/O2
with200ms pre-allocation yield and unchanged deadline/cleanup. Diagnostic03
fails42.4195462s: input owner16 slot5 exhausts its original32-sample first window;
desktop exits on lost input. Build02/media02 pass; no discarded result.
Actual driver host06 reproduces excessive idle clock/poll work;07 passes old/full
profiles O0/O2: full first-read reuses the just-validated timestamp,20ms idle
sleep remains below existing100ms packet expiry; old10ms variant untouched.
Host08 reproduces redundant console clock calls;09 passes zero-call empty write
and two-call complete short write, existing deadline/partial-write loop retained.
Only already allowed input driver and SDK source changed. Run changed diagnostic04
using build03/media03; no full-profile acceptance or raised quota inferred.

## Correction evidence04/05

Diagnostic04 fails42.4494971s with desktop exit22, no CPU exhaustion. Rootcause
is the agent-introduced single200ms SLEEP exceeding the native100ms syscall
bound; original host mock incorrectly permitted it. Preserve failed build03/
media03/guest04. Host10 now rejects this invalid request. Host11 passes with two
100ms calls, explicit per-step monotonic advancement and original deadline checks
before allocation; no new allocation on failure. Never raise the syscall limit.
Next changed diagnostic05 uses reserved build04/media04, <=600s.

## Evidence-directed terminal observation window

Diagnostic05 fails45.8777596s: desktop completes mouse-settings output then
exhausts CPU (owner15,total101), not startup deadline; input remains contained.
Four integration builds/media and five guests spent. Eleven host commands spent.
Reserve hosts12..20<=180s, builds05..07<=300s, media05..07<=180s, guests06..08
<=600s. Guest06 reuses exact diagnostic05 images with a new read-only hardware
terminal hook instead of stopping every syscall. At most64 terminal events,
one slot4 task4096B and at most4096B current stack; use actual LARGE_IMAGE task
layout (256 pages,4096-byte record,1984-byte register displacement). No guest
writes, no quota changes and no diagnostic promoted to acceptance.

Terminal diagnostic06 fails43.7683425s because terminal context has supervisor
CR3 and the observer tried virtual user stack0x40fba0. Guest memory was never
modified. Correct observer to the existing kernel direct-map alias of the exact
stack frame from that task's256-page vector; bounds/alignment checked. Preserve
failure and use reserved guest07 on unchanged images for this corrected new
observation. Save task bytes before attempting optional stack read.

Terminal diagnostic07 retained actual task but observer's erroneous<4GiB physical
bound rejected the owned high RAM frame0x100636000.4GiB QEMU maps displaced RAM
above the PCI hole; correct bounded8GiB address admission and save metadata before
stack read. Retained registers show native device op30 (display), request on
user stack0x40e670; terminal total72, before first frame. Use reserved guest08 to
read that exact owned frame and attribute the display call without guest writes.

## Startup publication correction

Diagnostic08 captures exact owned stack successfully: active frame chain
launch_clock -> service client clock_read -> service_exchange -> x86os_stat ->
desktop_font_load_progress -> desktop_editor_font_catalog_load -> desktop main.
Prior stack entries also contain display_pump/service during service wait. SDK
platform_pump currently publishes initial black/partial raster before app adoption.
Host12 reproduces those unnecessary commits;13 passes coalescing in existing
buffers until both Surface peers pass existing identity/HELLO binding. Failure
or detach clears publication state. No READY weakening; final physical drain,
actual app pixels and health remain mandatory. No extra buffer or display quota.
Eight guests spent, four integration builds/media, thirteen host commands.
Reserve changed guests09..11<=600s alongside already reserved builds05..07/media05..07;
use09 for this correction, no unchanged retry. CF/CB final gates remain untouched.

Diagnostic09 fails46.5158978s, CPU total96 after desktop-layout fallback; coalescing
reduces font-catalog stage from190 to80ms but does not yet establish startup.
Host14 reproduces fragmented startup console/progress behavior;15/16 pass actual
SDK at O0/O2 after line buffering solely before READY (128 fixed bytes, no heap),
flush on newline/capacity/explicit write/READY/detach, exact byte order including
partial7-byte UART writes, and zero-call empty writes.100ms per completed startup
phase replaces25ms, obeys syscall cap, checks advancement and original deadline
before/after; post-ready behavior unchanged. Build06/media06/guest10 now reserved
for changed candidate. All historical failures and original gates preserved.

## Participant idle scheduling continuation

Diagnostic10 fails45.6988073s: this time root supervisor owner1 reaches CPU quota
(total117), automatically fences children and returns a fresh shell generation.
Reserve hosts21..26<=180s for the same evidence-directed idle correction; prior20
hosts remain spent (19 fixture context mismatch,20 expected redundant-pump failure).
Host17 fails idle regression,18 passes production driver and app loops O0/O2:
full driver sleeps50ms only on empty read,10ms while active, below100ms decoder
expiry; app waits at most100ms in receive before HELLO, clipped to unchanged
absolute deadline (four blocking receives vs40 empty polls/40 sleeps in400ms).
Old profiles remain unchanged. Full supervisor initial poll sleeps50ms, bounded
by10s start and native100ms per-call; no health/Surface deadline or quota change.
Fixture splice now also checks unique following context when archived CB extended
the previous line; host19 is preserved as wrapper failure. Test20 demonstrates
repeated whole-SDK pumps inside40ms service wait. Limit redundant pre-READY service
wait pumps to one per50ms while retaining10ms sleep, every real clock/read check,
root control handling and original1000ms RPC deadline. Post-READY pump unchanged.
Next changed diagnostic11 uses reserved build07/media07; no unchanged retry.

Correction to host20/21 attribution: both failed the mock's assertion that an
unknown-path broker request is admitted, before reaching the pump-count assertion.
Host22 uses the actually allowlisted/text.prg and a delayed40ms response; actual
SDK O0/O2 passes exactly one full input/root/display pump during that wait,
including existing startup timeout/STOP/cleanup tests. No failed mock is credited
as a production regression. Participant idle changes passed host18. All changes
stay in approved CF sources; run changed guest11/build07/media07 now.

Diagnostic11 fails43.6416588s: both clients exit71 after their first blocking
receive, desktop then loses child identity. The new wait loop mishandled native
ETIMEDOUT(-110); earlier host mock incorrectly returned nonblocking EAGAIN(-11).
Host23 reproduces real timeout semantics,24 passes handling each100ms timeout as
an intermediate wait while the original absolute deadline remains authoritative;
no change to Surface replies after HELLO. Preserve all failures. Reserve one
changed build08<=300s/media08<=180s/guest12<=600s; existing host25..26 unspent.

Diagnostic12 fails46.4690893s with desktop CPU total69; blocking clients remain
alive until group teardown. Next evidence-directed correction paces only startup
STAT/READDIR/OPEN probes before their RPC, within at most one quarter of each
remaining operation/start deadline, capped100ms; identity/control and post-READY
operations unchanged.26 hosts/eight integration builds/media/12 guests spent.
Host25 rejects unpaced burst;26 catches an overly narrow mock sleep whitelist
(valid75ms was rejected). Permit native1..100ms after frontend entry, preserve
separate initial buffer-pause assertions. Reserve hosts27..32<=180s and one changed
build09<=300s/media09<=180s/guest13<=600s. No acceptance/gate/budget relaxed.

## CPU-contained but deadline-limited startup (diagnostic13)

Diagnostic13 runs57.265488s; no CPU exhaustion. Actual desktop reaches icons
(3990ms), filetypes260ms and sounds240ms, then original10000ms deadline expires.
Retained desktop windows4..9 use16,21,15,19,23,17 samples, all below32; no READY.
Thus preserve allocation pacing and idle fixes, shorten only optional-asset
metadata pause cap100->50ms and completed-phase yield100->75ms. Bounds remain
fractions of original deadlines, native per-call100ms, and no post-ready pause.
Reserve changed build10<=300s/media10<=180s/guest14<=600s; hosts28..32 remain.
No deadline/quota increase, unchanged retry, final gate credit or VMware claim.

Diagnostic14 fails51.290264s; icons3110ms/filetypes170ms/sounds190ms,
then desktop CPU terminal256, total202 samples. Both media hashes unchanged
and owned guest closed. Ten integration builds/media and14 guests spent.
Reserve one read-only terminal-observer guest15<=600s reusing exact diagnostic14
images, no build/media; locate the newly reached CPU terminal before a correction.
This is changed instrumentation, not an unchanged acceptance retry. Original
gates, CPU quota32/1000ms and startup10000ms remain unchanged.

## Concrete renderer scope boundary (diagnostic15)

Read-only terminal observer15 fails55.669438s, debugger exits0, guest closed,
original media hashes unchanged and fixture restored. Receipt desktop slot4,
owner15, terminal256/cause3, CPU total227, RIP0x42eada. Exact saved frame chain
maps against diagnostic14 desktop.map to desktop_window_is_trash, render_window
(return0x42caa4), render_desktop_clip(return0x427614). This is first-frame
frontend rendering CPU exhaustion, not optional metadata RPC or startup expiry.
No speculative SDK delay is an adequate correction to the measured renderer.

Fifteen diagnostic guests, ten integration builds/media, four role builds and
29 host commands spent; no final gate spent/passed. Evidence and counters remain.

Required next source is userspace/gui/compositor/desktop.c, currently immutable
CB fixture and outside CF allowed_files. AGENTS scope rule4 requires stopping
and reporting the architectural reason before expanding that source scope.
Proposed extension: bounded cooperative first-frame rendering using existing
clipped rendering and SDK service/deadline checks, preserving exact pixels,
atomic frame publication, cleanup, original10s start, CPU32/1000ms,100ms native
sleep,1000ms health and all display quotas. Regression must exercise actual
renderer output equality and interruption cleanup; select its existing host
harness at scope inventory, then freeze exact source/test files and finite
commands before implementation. No raising limits or crediting partial frames.
CF remains the sole active unaccepted package; original CF/CB gates unchanged.

## Approved renderer continuation

User ja mach weiter explicitly approves the renderer scope extension after
the diagnostic15 boundary. CF remains the one active transaction. Add actual
desktop.c and test/x86_64_desktop_render_host.c, reuse existing CF test/verifier.
Queue now also explicitly lists the three previously approved editable SDK files;
prior contract/fixture adaptation already declared them, queue omission corrected.
Preserve immutable CB archive and take pre-renderer source snapshot before edits.
Use existing clipped rendering, fixed vertical slices and bounded cooperative
service pauses before READY; cancel incomplete frames on adapter/deadline failure.
No intermediate publication, new authority, budget increase or acceptance change.
Reserve hosts30..35<=180s, integration builds11..12<=300s/media11..12<=180s,
changed guests16..17<=600s. Retain29 hosts/15guests/10builds/media spent.
Host control tests verify exact disjoint clip coverage and cancellation; real
renderer pixels/first READY/apps remain mandatory in the unchanged guest gate.

Renderer host30 fails before implementation (missing production helper). Host31
passes slicing O0/O2 and SDK O0/O2 in12.870s; deterministic clipped sink verifies
exact pixel coverage for full/overlapping/negative-origin rectangles and all ten
checkpoint failure positions. This does not substitute actual scene/guest proof.
Host32 adds actual SDK checkpoint100ms/zero-wait/invalid101ms and unchanged
absolute deadline assertions; passes O0/O2. New path executes only pre-READY,
128-row slices with100ms maximum syscall; enclosing frame canceled on error.
Changed diagnostic16/build11/media11 running. No final gate credit.

Diagnostic16 fails52.637350s at original10s deadline, no CPU terminal; actual
DESKTOP_EXPLORER_OK reached, total207 CPU samples, retained windows4..9 max
25,19,20,27,28,16. Icon probes alone3160ms. Build11/media11/guest16 spent.
Evidence-directed optimization within approved desktop.c: native optional icon
theme admission checks /usr/share/icons once. ENOENT or EACCES selects existing
vector fallback for that theme and clears both caches; it does not infer child
absence or acquire rights. A present granted directory retains all per-file
loads/validation; other errors retain existing per-file behavior. Individual
file grants without theme-directory access deliberately keep vector fallback.
Actual immutable boot profile has no icon theme assets. Add host cases for
denied/missing/present/error and stale-cache invalidation. Use host33..35 and
changed build12/media12/guest17 from existing reservation. All gates preserved.

Host33 theme admission cases pass O0/O2. Diagnostic17 fails54.486823s with
unexpected earlier desktop CPU256/total50 before first mode report; no theme
execution reached, so do not attribute this failure to theme semantics.
12 integration builds/media,17 guests,33 hosts now spent. Reserve read-only
terminal observer18<=600s on exact17 images to identify early CPU path; no
build or unchanged acceptance retry. Reserve hosts34..40<=180s and two changed
builds13..14<=300s/media13..14<=180s/guests19..20<=600s for evidence-directed
in-scope correction after capture. Preserve all earlier bounds/gates/failures.

Observer18 fails78.348076s CPU256/total91 at mouse-settings OPEN: saved chain
desktop_entry_call -> open_object -> storage_collect -> file_transact/file_open
-> read_file_bounded_progress -> desktop_load_mouse_settings. Images unchanged,
observer0, owned processes closed. Early failure location varies; retain both
17 and18 evidence rather than crediting a successful retry. Restore the already
CPU-contained diagnostic13 metadata100ms/progress100ms pacing, now combined
with admitted-theme fallback (eliminates ten asset probes/progress waits) and
cooperative rendering. Host34 updates exact progress expectation. Use reserved
changed build13/media13/guest19. This is within current SDK/renderer scope.

Diagnostic19 fails76.040347s CPU256/total107 after mouse settings; longer fixed
pauses alone are insufficient. No owned QEMU/GDB/compiler remains; no resource
limit changed. Inventory: each service reply is polled with nonblocking bulk
receive plus clock/10ms sleep and repeated2048-byte message clearing. Next
in-scope correction: only pre-READY service receive blocks once for at most100ms,
clipped to the original RPC and start deadlines. Remaining channel draining
stays nonblocking, intermediate ETIMEDOUT maps to EAGAIN; original outer deadline
and input/control health checks remain. No public ABI change. Host35 delayed
40ms reply regression first; host36 implementation, reserved build14/media14/
changed guest20.19 guests/13 integration builds/media/34 hosts spent before35.

Host35 reproduces unnecessary polling;36 passes40ms blocking reply at O0/O2.
Host37 extends delay to140ms and correctly hits its mock's unrelated1000ms
whole-start deadline during subsequent100ms progress yield. Host38 gives only
that success scenario2000ms start (still within original3s profile); all existing
timeout/failure cases unchanged. It passes intermediate native ETIMEDOUT100ms,
second bounded receive, one control pump, no RPC deadline renewal, at O0/O2.
38 hosts spent. Run reserved build14/media14/guest20 on changed transport.

Diagnostic20 fails82.563743s with adapter-110, no CPU terminal (total174).
Icons350ms, actual Explorer, both apps run; retained framebuffer shows only
upper desktop tiles. This may be a display/health/start deadline: do not label
all-110 as the10s startup deadline without caller evidence. Reserve observer21
<=600s on exact20 images, adding read-only launch_failed hardware breakpoint
and bounded owned user stack capture, no rebuild.14 integration builds/media,
20 guests and38 hosts spent. Follow-up in-scope hosts39..44<=180s, changed
builds15..16<=300s/media15..16<=180s/guests22..23<=600s reserved after capture.
Original deadlines/display quotas/health unchanged.

Observer21 fails86.414895s, exact adapter caller render_checkpoint ->
render_desktop_frame -> render_desktop_measured -> desktop_native_main, return
0x41580d. Disassembly identifies main-loop render followed by frontend_presented,
not initial render. Thus original start expires during later application redraw.
Current per-rectangle100ms pause over-throttles small damage; early publication
at HELLO also transfers obsolete initial scene. Correct within same renderer
scope: accumulate at most128*1024 pixels between checkpoints across damage
rectangles (each strip still<=128rows); retain one initial bounded checkpoint
and final deadline check. Enable display publication only after both actual
application surfaces pass frontend_presented checks, idempotently; READY still
requires physical display drain. No new buffers, quotas or deadline changes.
Use host39 regression then40; reserved build15/media15/guest22.

Host39 rejects old per-rectangle waits and HELLO publication;40 passes corrected
pixel grouping/exact coverage/failure stop and SDK deferred physical-drain proof
at O0/O2 in10.078s. Changed build15/media15/guest22 running. No final gate credit.

Diagnostic22 fails82.448923s adapter-110, then CPU terminal during cleanup,
total161. Icons320ms; apps execute, no full READY. Inspection identifies repeated
pre-READY raster work: initial no-app frame then empty client-window frames
before completed client paint. Coalesce these intermediate scenes: native first
render waits for both fully committed client scenes; service IPC/health continues,
then force full damage once. Reuse shared validated scene predicate in SDK; actual
READY still additionally requires presented generations and physical drain.
No omitted final pixels, relaxed app deadlines or skipped lifecycle proof.
Use host41 regression/42 implementation and reserved build16/media16/guest23.
22 guests/15integration builds/media/40hosts spent before41.

Host41/42 fail due test insertion also matching an earlier unrelated display
fixture (undeclared runtime/manager/windows); neither is credited as a production
regression. Remove only that erroneous assertion and run host43. No guest spent
on the failed compile. Original phase/deadline/cleanup cases remain intact.

Host43 passes actual shared scene validation, deferred display drain and
production clip grouping at O0/O2. Native main defers raster until both committed
client scenes exist; full damage forced once, input/control health still pumped
and sleeping bounded10ms while awaiting scene. Changed build16/media16/guest23
running.43 hosts spent; no final acceptance or commit.

## Concrete pixel-adapter scope boundary (diagnostic23)

Diagnostic23 fails79.030741s, owned guest closed, signed media hashes unchanged
and fixture restored. Desktop CPU256/cause3, total155 samples, RIP0x458dc0 maps
inside x86os_fill_rect (start0x458ce0,size0x264) in the exact desktop.map. Retained
desktop windows4..8 maxima18,12,18,17,32. No READY. Unlike21's render wait timeout,
this is actual pixel fill CPU exhaustion after coalescing the first scene.

Stop before extending scope: required native primitive implementation is
userspace/sdk/lib/x86_64/desktop_display.c, currently immutable CB fixture and
NOT in CF allowed_files. AGENTS rule4 requires architectural reason/report.
Proposal: bounded native pixel fill/copy optimization, inventory emitted machine
code and existing display behavior tests first; preserve clipping, exact pixels,
validated buffer ranges, cancel/commit atomicity and quotas. Use established
x86-64 memory operations only if measured/proved; no speculative backend, DMA,
new memory or kernel driver. Reuse CF test_x86_64_desktop_startup.py plus existing
editable x86_64_desktop_platform_host.c for pixel/guard/overlap/frame-cancel tests;
freeze any additional test file explicitly before edits. Original startup10s,
CPU32/1000ms, per-call limits and all CF/CB gates remain unchanged.

43 hosts,4 role builds,16 integration builds/media,23 failed diagnostic guests
spent; no final gate run/credit, no implementation commit, no current VMware
acceptance. Host44 reservation remains; future builds/guests need new recorded
finite window without resetting spent counters. No owned live tool process.

Final scope inventory caught a queue-edit locator bug: substring id also matched
active_id, placing approved additions into the first package instead of CF.
Remove that misplaced suffix and anchor exact newline-id to CF; no scope or
acceptance is claimed from the incorrect queue. User approvals and contract
explicit file list predated implementation; executable queue now matches them.
Preserve this failed inventory, rerun only the corrected scope/closure check.

## Approved pixel-adapter continuation

User mach weiter explicitly approves previous pixel-adapter scope question.
Add desktop_display.c and existing x86_64_desktop_display_host.c; other CF files
and original gates unchanged. Snapshot before-pixel01/files.zip retained.
Inventory actual emitted x86os_fill_rect shows a state.config.width reload and
integer multiply for EACH pixel because the output uint32 pointer may alias
configuration fields. Use validated dimensions captured once and row pointers,
with equivalent bounded fill/copy/frame semantics. No assembly/SIMD/new buffer
needed. Tighten actual adapter pixel/guard/cancel tests before change.
Reserve hosts44..49<=180s, changed integration builds17..18<=300s/media17..18
<=180s/guests24..25<=600s. Prior43hosts/4role builds/16integration builds/media/
23failed guests remain spent. Final gates not run/credited.

Host47 also repeats link failure: insertion anchor was not unique. No guest
spent. Replace fragile diff application with exact proof: archived display minus
its contiguous idle/service helper block equals saved baseline; insert only that
block into edited display. This proof now passes before host48 is launched.

Host48 passes actual adapter guards/clipped whole-frame pixel oracle/cancel/copy
and SDK integration at O0/O2. Optimization captures validated dimensions and
row pointers; no new memory/ABI/limits. Changed build17/media17/guest24 running.
48hosts spent;49 remains, second changed build18/media18/guest25 reserved.

Diagnostic24 fails52.972630s without CPU exhaustion, total156; no full READY,
root-110. Reserve read-only scene observer25<=600s reusing exact24 media; this
replaces unspent changed-guest25 reservation, build18/media18 remain unspent.
Host49 compiles actual structure layout for bounded slot/window field capture.
Observe first scene-check args once, then exact-110 instruction once (symbol/map
and disassembly bound), alongside existing bounded terminal/error observers.
No guest memory writes, no guessed READY or acceptance.49 hosts/17integration
builds/media/24 guests spent. Reserve hosts50..54<=180s and changed guest26<=600s
for evidence-directed in-scope correction using remaining build18/media18.

Observer25 fails52.105858s: both actual surfaces fully painted/acknowledged,
correct owner generations17/18, windows visible/positive generations/sizes/content
tags, no active paint. Thus do not change Surface state rules speculatively.
Framebuffer still black. Extend read-only capture with exact compiled timing
field offsets, platform previous-clock/config symbols at first scene entry and
-110 return; distinguish start deadline from health age. Host50 layout v2 passes.
Reserve observer26<=600s on unchanged24 media (instrumentation changed), and
changed guest27<=600s using still-unspent build18/media18 if evidence warrants.
25guests/17integration builds/media/50hosts spent. Original gates untouched.

Observer26 fails50.519888s; first scene entry has2480ms start time remaining,
input and both apps fresh. Inspection finds observer25/26 breakpoint error:
mov eax,-110 sets a default result BEFORE condition checks; capture was not an
actual timeout. Preserve both runs and retract timeout-state attribution.
Select the function's unique RET instead, verify actual EAX=-110, bound2048
returns/last64 timing records. Reserve corrected observer27<=600s on24 images,
no build, then changed guest28<=600s with still-unspent build18/media18.
26failed diagnostic guests spent; no unchanged acceptance retry or gate credit.

Corrected observer27 fails50.584931s and proves actual health timeout: scene
ready at37220 (end39740), return-110 at38110; input fresh38050, app health still
37100/37190. Start has1630ms left, first app age1010ms. Both scene states valid.
Correct production post-render ordering: drain existing bounded Surface runtime
(including queued HEALTH), then input/root pump, then readiness age/publication
checks. New paint received there cannot earn READY until presented generation
matches. Use private shared SDK finish-frame helper so host test exercises exact
path with1001ms-old health and queued fresh messages. No health/deadline extension.
Host51 regression then52 implementation; changed build18/media18/guest28 reserved.
27guests/17integration builds/media/50hosts spent before51.

Host51 regression link failure;52 passes actual queued-health refresh at O0/O2.
Diagnostic28 fails50.778141s, no CPU terminal, now physical framebuffer contains
748058 nonblack bytes (previously0); first complete output still not READY,
root-110. This advances past stale-health rejection but does not prove full drain.
Inventory remaining display pump computes cursor coordinates/shape for EVERY
pixel, though only8x12 cursor pixels can differ. Optimize validated tile row copy
and overlay clipped cursor afterward; same pixels/stride/commit/rate semantics.
Add exact cursor oracle at tile crossing63,63 and clipped screen edge1020,764.
Reserve hosts53..58<=180s, builds19..20<=300s/media19..20<=180s, changed guests
29..30<=600s.52hosts/18integration builds/media/28guests spent, no gate credit.

Host53 cursor oracle failed because tile-crossing region contains an earlier
UTF-8 glyph; assuming a black background was wrong. Preserve failure; compare
against exact pre-cursor pixels instead. Apply row-copy/clipped-cursor optimization
and run host54 with corrected oracle plus SDK integration.

Host54 passed adapter and SDK O0/O2. Diagnostic29/build19/media19 failed: CPU terminal256, total141, RIP0x463f1a (desktop_entry_call); no READY. Preserve evidence; convert reserved guest30 into read-only terminal observer on identical29 media, <=600s, no rebuild. Build20/media20 remain unspent. 54hosts/19integration builds/media/29guests spent. Original gates and limits unchanged.

Observer30 fails51.504732s, terminal receipt reason0 (no CPU exhaustion), root-110; retained stack in channels_surface. Exact same29 media unchanged and fixture restored. Diagnostic29 failed49.940583s. Last256 CPU records for desktop contain91 events in29 (47 clock135,43 receive131,1 sleep70), reaching32 in window8;30 has75 (40 clock,35 receive), no terminal budget. Do not infer full-run totals from ring. Reserve read-only scene observer31<=600s on29 media to establish first-scene time and actual rejection; existing observer instrumentation adds timing, no new build or guest-code retry. 30 guests spent; build20/media20 unspent, hosts55..58 retained.

Scene observer31 fails54.146791s; first scene at39480/end41360 (1880ms remain), no CPU terminal; root revokes by original deadline. No actual scene-timeout return captured. Evidence plus main-loop inventory shows first drain interleaves entire compositor iterations for each small tile batch. Freeze in-scope finish-frame correction: maximum24 initial drain turns, existing bounded Surface poll/input/root/display service,10ms sleeps, original scene/health/deadline validation each turn; exit on pending new paint, failure or READY. No post-READY loop, no limits changed. Host55 regression/56 implementation within reservation; changed guest32<=600s consumes remaining build20/media20.31guests/19builds/media/54hosts spent.

Host55 regression fails as expected at missing bounded drain progress; host56 passes actual SDK/Surface/display integration O0/O2 in8.119s. Initial finish-frame loop capped24,10ms sleeps, valid scene required, unchanged frontend-ready path exits after one existing pump. Host preserves invalid visibility/content/minimized checks, queued HEALTH refresh, exact130 committed tiles and no READY until display idle. Changed build20/media20/guest32 launched;56hosts and31completed guests spent before launch.

Diagnostic32 fails50.573833s, CPU256 total154, original limit32 in window8; no READY. 56hosts/20integration builds/media/32guests spent. Correct trace interpretation: cpu_trace.inc stores saved RFLAGS at offsets168/176, NOT syscall numbers. Retract prior attribution of135/131 to clock/receive. Window accounting remains valid. The bounded drain change has host behavioral proof but no accepted guest performance proof. Reserve read-only call observer33<=600s on unchanged32 media: one hardware entry breakpoint, actual SysV RSI operation, return address, bounded8192 calls/128 recent records and fixed operation/caller aggregates. No guest memory writes, no rebuild. Exact map symbols and disassembly verified before capture. Hosts57..58 remain; no final gate credit.

Call observer33 fails53.213575s, captured752 actual entry calls (455 MONOTONIC42,157 RECEIVE54,52 SLEEP41), exact symbols/disassembly and SysV RSI; no trace-flags inference. Terminal256 total173 at0x4588a0 in frame_begin full786432-pixel scalar copy, before first raster. Freeze direct pixel-copy optimization in approved display adapter: AMD64 REP MOVSQ plus odd32-bit tail, existing non-overlap/range validation, supports4-byte alignment, no SIMD/FPU/new buffers/ABI. Earlier no-assembly-needed statement described initial row-loop change, not an acceptance gate. Host57 extends actual whole-copy oracle with odd321x241 and4-byte-aligned buffers, host58 verifies implementation O0/O2 plus SDK. Reserve build21<=300s/media21<=180s/changed guest34<=600s; hosts59..62<=180s for evidence-directed follow-up.33guests/20builds/media/56hosts spent; no accepted gates.

Host57 baseline odd-copy oracle passed;58 copy+SDK O0/O2 passes8.917s. Diagnostic34/build21/media21 fails50.712632s, CPU256 total167; no READY or performance acceptance.33 observed frame_begin copies before first100ms renderer checkpoint: existing pacing protects raster but not its preceding3MiB copy. Freeze moving (not adding) that first checkpoint into a private startup frame-begin helper before copy, with same total waits/absolute deadline. Host59 regression/60 implementation verifies failure before frame creation and all existing strip failure positions. Reserve changed build22<=300s/media22<=180s/guest35<=600s.34guests/21builds/media/58hosts spent; hosts61..62 retained.

Host59 missing-helper regression failed;60 renderer and SDK tests pass. Diagnostic35/build22/media22 fails49.898274s CPU256 total126/window8 used32. Preserve result, no gate credit. Inventory pending-first-scene branch uses10ms generic sleep which pumps before/after, then re-enters whole compositor; actual call observer33 established repeated Surface/input/root polling. Replace only pending initial scene wait with existing direct100ms render checkpoint (one pump, bounded sleep, unchanged original deadline), allowing peers to complete without repeated empty polls. No post-READY change. Host61 targeted renderer/SDK; reserve build23<=300s/media23<=180s/guest36<=600s.35guests/22integration builds/media/60hosts spent; host62 retained.

Host61 passed. Diagnostic36/build23/media23 fails49.974196s CPU256 total130;413762 nonblack PPM bytes proves output began, not full READY. First drain currently calls generic10ms sleep, which pumps twice in addition to next finish-frame pump: up to24 tiles per10ms sleep. Freeze startup-only replacement with existing render_checkpoint(100): one pump then direct100ms sleep, plus next finish-frame pump, up to16 tiles between waits.24-turn bound and original deadline/health checks preserved; post-READY unchanged. Host62 regression pacing oracle on130 actual commits,63 implementation. Reserve hosts63..66<=180s/build24<=300s/media24<=180s/changed guest37<=600s.36guests/23integration builds/media/61hosts spent. No quota/deadline expansion or final gate credit.

Host62 pacing regression failed as intended;63 compiler rejected missing private checkpoint declaration. Added exact existing prototype,64 passes SDK integration O0/O2. No counters reset;64hosts spent. Changed diagnostic37/build24/media24 now launched.

Diagnostic37/build24/media24 fails51.292898s with root-110, no CPU terminal (total150); output584152 nonblack bytes. Retained window maxima6=11,7=24,8=18,9=24, no claim about discarded trace. With display now paced, original10s deadline is limiting. Actual call observer33 recorded seven large frontend allocations each paying two100ms sleeps. Freeze reducing only frontend workspace admission from two to one100ms wait (saves700ms for observed seven), same preallocation pump, monotonic/deadline checks and native call bound. Separate two framebuffer-allocation pauses remain unchanged. Host65 regression/66 implementation; reserve build25<=300s/media25<=180s/changed guest38<=600s.37guests/24builds/media/64hosts spent.

Host65 regression failed;66 one-wait SDK passed. Diagnostic38/build25/media25 fails51.601217s root-110, no CPU terminal total171;911930 nonblack bytes, rows511+ stillblack. Emitted actual attach code0x45840a reloads config width/height and multiplies per pixel while clearing two3MiB buffers, despite prior disjoint validation. Freeze approved pixel-adapter zero initialization via AMD64 integer REP STOSQ+odd tail with dimensions captured once; no new buffer/ABI/authority. Host67 baseline whole-zero oracle/68 changed pixel+SDK verification. Reserve hosts67..70<=180s/build26<=300s/media26<=180s/guest39<=600s.38guests/25integration builds/media/66hosts spent.

Host67 baseline whole-zero oracle passed;68 optimized clear/copy+SDK O0/O2
passed. Diagnostic39/build26/media26 fails50.713295s CPU256 total151; no READY.
39 diagnostic guests,26 integration builds/media,4 development role builds,
68 host tests spent. All failed evidence retained, no final gate credit.

## Decision required: separate bounded CPU profile for the actual desktop

Status: proposal only, NOT authorized or implemented (2026-09-25).
The current32-sample/1000ms profile remains authoritative. Diagnostics37/38
avoid CPU exhaustion but miss the original10s startup deadline;39 again reaches
the CPU ceiling after the optimized initialization shifts the work in time.
This does not prove execution at32 is impossible. It does show that the current
pacing/optimization candidate has not qualified and cannot be delivered as done.

Proposed alternative to continued tuning within32:

- Add an explicitly selected, append-only large-image periodic CREATE variant
  (next available version, currently9 after verifying all dispatch sites),
  RNPGv3/profile-v1/startup-v1, existing80-byte periodic transport, fixed1000ms
  period, maximum64 CPU samples. Preserve CREATE-v6/v8 maximum32 and all legacy
  behavior. Do not silently reinterpret an existing operation.
- Only the real full-desktop compositor requests64. Input, application peers
  and other existing service budgets remain unchanged. Require an admitted
  periodic parent with an immutable budget at least as large; no child may
  expand its parent's authority. Verify the actual full-profile parent before
  implementation; do not raise a parent budget implicitly.
- Retain CPU exhaustion fencing/reap, all generation checks, memory/IPC/display
  limits, the original10s startup deadline and1000ms health deadline. No new
  filesystem, network, device, DMA or process rights.
- CPU samples are timer-accounting units, not a promised utilization percentage
  or a realtime guarantee. Increasing the admitted bound can reduce available
  CPU time for peer services and requires new starvation/recovery evidence.
- Preserve old32/default byte and behavior evidence. Add actual assembly host
  proofs for64 admission,65 rejection before side effects, wrong periods,
  nonperiodic/underbudget parents and old-version32 preservation. Fresh guest
  evidence must prove64 exhaustion/reap and unrelated input/service progress,
  as well as the real full first frame, both apps, input, replacement and cleanup.
  Existing CPU-exhaustion tests stay; add the new variant's proof rather than
  dropping them. No diagnostic or quota change itself counts as acceptance.

This is a changed resource-authority domain and changed frozen acceptance claim,
not an administrative retry reservation. AGENTS.md requires explicit user
approval. Likely prerequisite sources include native task-family admission,
scheduler periodic-profile dispatch, the native task SDK wrapper and their
existing host/guest validators, outside CF's current allowed_files. Inventory
and freeze exact scope/gates only after approval. Preserve the current CF
candidate and all prior counters; never mix an unverified prerequisite into a
claimed accepted CF package or start another agent. No such source edited now.

## Approval received; parent-budget prerequisite found (2026-09-25)

User `mach weiter` immediately after the64-profile approval question authorizes
that proposal, including its explicit parent-attenuation and unchanged-other-
budgets restrictions. No renewed approval is needed for that same proposal.
No candidate CPU-profile source has been edited; CF remains the sole active
transaction and the19-file candidate is preserved in before-cpu-profile01.

Read-only inventory finds the proposal's parent eligibility premise is false:

- diagnostic39/guest/failure/cpu-budgets.bin is256 bytes; slot0 is exactly
  generation1, limit32, total189, last3906; all retired child slots are zero.
- task_family.inc family_cpu_attenuate64 reads the parent's immutable limit
  from process_run_plan and rejects child limit greater than parent limit;
  it additionally validates the parent as1..32 and period100 ticks.
- process_run.inc admission and cpu_period.inc bind also reject limits above32.
- SHELL_OWNER_CPU_BUDGET128 belongs to a different legacy shell execution path;
  it is not evidence of a128-sample periodic parent in the actual full desktop.

Therefore do NOT implement a64 child under the existing32 parent, relax
attenuation, or silently enlarge the parent. The approved proposal explicitly
forbids an implicit parent increase. This is a genuine extra authority decision,
not an attempt-counter reservation. No tests/builds/VMs were spent this turn;
CF counters remain68 hosts/4 role builds/26 integration builds/media/39 guests.

### Concrete amendment requiring approval

For the explicitly selected full-desktop CPU profile only, admit the graphical
supervisor/root (slot0) with a fixed64-sample/1000ms periodic budget as well as
the actual compositor with64. Other services, PS/2 and application peers retain32.
The supervisor's own CPU budget increases; this is not just a delegation field.
Preserve child<=immutable-parent attenuation, no in-place renewal or budget edit,
existing quantum/fencing/reap and all other rights/limits. Nonselected roots and
old process-run/CREATE versions retain their exact32-sample semantics.

Inventory indicates that an append-only selected process-run plan version is
needed in addition to the proposed CREATE-v9 and accounting selection; do not
reinterpret the existing plan version5. Freeze exact dispatch/build/SDK/test
scope after approval, with old-byte equality, actual admission/attenuation,
64/65 boundary, exhaustion of both root and compositor, full family cleanup,
stale-generation denial and independent-peer/input progress guest evidence.
No CPU profile acceptance or desktop completion may be claimed without those
proofs. The original10s startup and1000ms health limits remain unchanged.

User explicitly approved: Ja, Supervisor und Desktop jeweils64 freigeben. Both-profile amendment is authorized; other peer/default budgets remain32. Preserve CF candidate and proceed with one separate bounded CPU prerequisite transaction, then resume CF with all historical obligations.
