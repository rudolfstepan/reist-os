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

## Resume after accepted CG fa790cf0 (2026-09-25)

User explicitly approved supervisor/compositor64; CG passed all five frozen
gates and seven fresh guests, committed fa790cf0 with clean worktree. The old
CPU32 exclusion is superseded only for these two full-desktop roles. Other
peers/apps/input remain32 and health/startup/device/rights/cleanup gates stand.
Restore16 CF source files byte-exact from before-cpu-prerequisite01 (manifest
and archive verified), keep current queue/history/CG implementation intact.

The immutable CB integration fixture already wires LARGE_PERIODIC separately
for full-desktop. Through the allowed CF verifier, freeze these exact additional
profile substitutions: full-desktop Makefile CPU flags and boot-producer flags
also define DESKTOP_CPU; compositor alone calls accepted CREATE-v9 with64.
Input and applications keep existing32 imports. No general selector changes or
new kernel/SDK code; temporary CB files restored exactly after each build.
The preserved CF renderer/pixel/SDK improvements remain its declared editable
exceptions. These substitutions become CB integration obligations on resume.

Reserve hosts69..74<=180s, integration builds/media27..29<=300/180s and guests
40..42<=600s. Preserve68 hosts,4 role builds,26 integration builds/media and39
failed/unaccepted guests. First build/use the newly accepted64 profile with
original10-second startup; diagnose only evidence-directed failures. Final CF
four gates and later CB five/eight-guest gates remain required, no fake READY.

## CPU64 integration and measured frame pacing (2026-09-25)

Restored16 CF sources exactly; three frozen CPU fixture substitutions applied.
Host69 passed all four groups12.100s. Integration build/media27 passed; guest40
failed51.394s at the unchanged10-second startup deadline, with no CPU exhaustion
(desktop total172, cancelled). Last observed windows7/8/9 used26/30/21 of64.
Read-only scene observer guest41 failed52.475s on identical images: first scene
entry now37550/end40430 leaves2880ms for raster and physical tile drain. No fake
READY, image mutation, health extension or lost fixture restoration.

The64 profile has CPU headroom but retained32-profile100ms raster/drain pauses.
Reduce only those private pauses to50ms; fixed pixel slices, eight-tile pump,
24 drain turns, health checks and absolute deadline remain. The checkpoint also
retains existing0/100 calls and rejects other durations. Host70 tests expose old
pacing: render test hits its60s host timeout after assert; SDK explicitly reports
old drain outside300..450ms. Retain both failures; replace the new render/drain
assertions with explicit errors to avoid a Windows CRT assertion dialog. Host71
and changed build/media28/guest42 follow; all prior counters remain spent.

Host71 passed all four groups11.597s. Build/media28 passed; guest42 failed52.636s
at the original deadline, no CPU exhaustion. Physical nonblack raster advanced
from row447 to575 (of768), bytes1166699->1377921. Last observed windows7/8/9 use
28/24/23 of64; source images restored/unchanged. Remaining bottleneck is initial
physical drain. Reserve hosts72..78<=180s, builds/media29..31<=300/180s and
changed guests43..45<=600s. Keep renderer50ms, reduce only the bounded initial
24-turn drain wait50->20ms; actual display64-commits/100ms throttle stays intact.
No quota, deadline, per-turn capacity or health relaxation. Test wall-time bound
and real pixels before any acceptance. Hosts71/builds28/media28/guests42 spent.

Host72 reproduces old400ms drain; host73 passes four groups11.229s with20ms drain.
Build/media29 pass; guest43 fails51.371s at unchanged root deadline, compositor
cancelled (total202), no CPU exhaustion. Physical raster now reaches row639/767.
Startup workspace admissions still carry one100ms pause per large allocation
from the32 profile. Reduce only that pre-allocation pause to50ms under the
approved64 full frontend; retain deadline validation before side effects and
rollback/health pumping. Host74 reproduces old100ms pacing. Host75 and changed
build/media30/guest44 use the already reserved continuation; no limits raised.

Host75 passes all four groups11.393s. Build/media30 pass; guest44 fails51.420s
at startup deadline without CPU exhaustion, desktop total219, final visible
row703/767. One tile row remains. Optional asset STAT/OPEN probes still impose
up to100ms each before sending an RPC, inherited from32 CPU scheduling. Cap only
this pre-send pause at50ms; preserve each original request/startup deadline,
rate capacity, single-execution rule, health and response validation. Host76
regression requires the mock140ms reply plus no more than50ms pacing (<=200ms);
then host77/build31/media31/guest45, all within the current reservation.

Host76 exposes old240ms asset reply; host77 passes four groups12.160s. Build/
media31 pass. Guest45 reaches actual DESKTOP_OK/GRAPHICAL_READY inside10s and
survives10s input exercise without a role loss, but fails61.759s because the
300ms pointer snapshot is unchanged. Later keyboard snapshot differs only in
cursor pixels (bbox512,384..543,407); it is NOT keyboard proof. Stable snapshot
shows paint's motion response. All framebuffer rows now visible. No acceptance.

Inventory: native x86os_pointer_update only queues dirty tiles. The compositor
marks pointer completion then enters raster work before the next platform pump,
violating its intended pre-raster presentation order. Under the already allowed
renderer/SDK scope, pump one existing bounded input/control/display batch after
successful live pointer update, before raster; retain startup coalescing and all
8-tile/rate/error limits. Regression executes the production pointer helper.
Reserve remaining host78 plus hosts79..84<=180s, builds/media32..34<=300/180s,
guests46..48<=600s. Preserve77 hosts,31 builds/media,45 guest attempts, no gates.
Keyboard diagnostic must later focus the actual text surface and prove glyph
changes; cursor motion alone never qualifies as keyboard application response.

Host78 executes production helper and exposes missing pre-raster pump; host79
passes four groups11.341s after one bounded live pump (no startup publication).
Correct CF input diagnostic in memory, leaving archived CB runner bytes intact:
retain original300ms pointer gate, explicitly click existing text taskbar button
before abc, compare focused baseline and require exact PSF glyph pixels in the
keyboard screenshot. Bind adapter source hash and reject cursor-only changes
and corrupted glyphs. This strengthens the intended input proof; no acceptance
limit or immutable production fixture is relaxed. Host80 then build/media32
and guest46 use the existing reservation. Diagnostic success is not acceptance.

Host80 passes five groups11.435s. Build/media32 pass; guest46 fails51.508s at
startup deadline (visible row703, compositor total222, no CPU exhaustion), so
pointer fix remains guest-unproven. Guest45 success was too close to the boundary.
Inventory still finds two100ms sleeps per framebuffer allocation and100ms per
completed startup phase, inherited from32 CPU pacing. Complete the same64-profile
pacing adaptation: preserve both pauses per buffer and every progress check,
use50ms instead; first scene wait also50ms. Host81 exposes old400ms buffer pacing
and phase100; host82 then changed build/media33/guest47. Original deadlines,
health, quotas, rollback and no-renewal rules unchanged; no unchanged retry.

Host82 passes all five groups11.317s. Build/media33 pass; guest47 reaches full
READY and remains stable, but fails62.202s at the original300ms pointer proof.
No abc glyphs in any frame. Spent82 hosts/33 builds+media/47 guests; no gates.
Guest48 is reserved for read-only causal observation of unchanged47 images:
four hardware breakpoints at driver publish, compositor input admission,
pointer update and display commit, slot filtered, at most4096 events/600s.
The diagnostic adapter skips intermediate snapshots to keep GDB attached until
stable; it preserves final raw capture and cleanup, and cannot pass the normal
pixel checks because skipped captures are absent. This is observation only,
not acceptance or a relaxed300ms test. Bind observer, adapter and exact images.

Guest48 fails50.667s before READY: instrumentation observes154 events, then
app6 exits71 and bounded supervisor cancellation; no input performance claim.
Debugger and VM closed, immutable media and fixture restored. Reserve guest49
<=600s for changed observer attachment ONLY after READY; no image build or
production change. Preserve48 spent guests,82 hosts,33 builds/media. Four
hardware probes and4096 event cap unchanged; this removes startup observer
interference, not any guest deadline or safety check.

Guest49 completes bounded post-READY trace98 records in62.029s, then fails
normal proof as expected because intermediate screenshots were skipped.
No observer error, roles stable, VM/GDB closed, media unchanged. Pointer event
published at tick3946, admitted3951, pointer update4003, first tile4015:
compositor admission-to-update520ms dominates (instrumented, not acceptance).
Reserve guest50<=600s on identical47 images, replacing driver/commit probes by
mouse consumption and Surface runtime poll entry, retaining input/update
probes. Causal distinction: queued input vs client IPC/presentation work.
Same four hardware breakpoints,4096 events, post-READY only, no production edits.
Spent49 guests,82 hosts,33 builds/media; no gate credit.

Guest50 ends64.002s,128 records, no pointer/key delivery in observed interval,
observer exit1; unsuitable for causal input proof. No retries or acceptance.
Source inventory and guest49 agree pointer publication is after client handoff
and Surface polling. Move selected live pointer publication immediately after
coalesced input dispatch and before client IPC/activation, reusing the already
tested bounded helper and pending/error semantics. No new rights or bounds.
Supplement helper behavior tests with production-order regression, then one
changed uninstrumented guest51 (<=600s), existing build/media34 reservation.
Hosts83 expected order failure and84 changed implementation; extend85..86 only
if concrete host corrections required (<=180s). Preserve50 guests/82 hosts.

Host84 passes six groups11.965s. Build/media34 pass; guest51 reaches READY
but fails pointer300ms at62.654s, closed/media unchanged. Early pointer order
alone is insufficient. Inventory shows idle loop pumps input/control/display
four times plus Surface twice: top, generic1ms sleep before/after, finish-frame.
Guest50 observes otherwise idle mouse polls roughly270..350ms apart (not an
acceptance measurement). Reserve host85 regression/86 correction<=180s,
build/media35<=300/180s, guest52<=600s. Add private full-ready idle sleep with
clock-validated1ms only; next loop still executes mandatory platform pump and
Surface poll. Skip finish-frame only for live no-damage idle turns; retain it
for all startup/raster turns and preserve every health/deadline check there.
No busy wait, quota increase, new authority or default-profile change.

Host85 exposes missing private idle adapter; host86 passes all six groups
11.755s. Actual production idle wait performs exactly two monotonic reads and
one1ms sleep; rejects pre-READY state. Startup and raster finish-frame retain
original Surface refresh and full health checks. Build/media35 and changed
guest52 underway; no acceptance claim.

Build/media35 pass. Guest52 reaches DESKTOP_OK/GRAPHICAL_READY and remains
stable, but fails62.436s at unchanged300ms pointer proof. All five snapshots
contain no exact abc glyph sequence; no keyboard claim. Closed VM, unchanged
images, byte-restored fixture. Spent86 hosts,4 role builds,35 integration
builds/media,52 guests. No CF acceptance gates or implementation commit.
Both pointer-order and idle-poll optimizations remain host-tested candidates,
not a demonstrated latency fix. Further correction needs causal observation
of the remaining pre-publication delay; do not retry identical images as
acceptance or increase300ms/startup/health/CPU limits.

Continuation: reserve diagnostic53<=600s on exact52 images, no rebuild.
Post-READY hardware probes now cover input admission, mouse dequeue, console
puts and pointer update, including bounded return-address/string capture.
Require a recorded event before injection (<=5s) to avoid debugger-attachment
race seen in50. This is causal observation, not timing acceptance. Original
300ms proof and all runtime limits unchanged. Preserve86 hosts/35 builds/52 guests.

Guest53 reaches READY; observation ends75.738s on QMP VM-not-running during
a debugger stop, not a guest acceptance. Closed/media unchanged. Trace shows
input admitted3994, consumed4002, console marker4003, pointer4007; subsequent
input admissions4009/4017/4019/4022/4023 occur inside the pointer's full platform
pump before physical display. Earlier idle/order correction reduces admission
to update to130ms in this instrumented sample, but display is still deferred.
Reserve hosts87 regression/88 correction<=180s, build/media36<=300/180s and
changed uninstrumented guest54<=600s. Pointer helper directly invokes existing
bounded display service after update, not another full input/control pass;
mandatory loop-top health/control and device generation validation remain.
No quota, frame, rate or safety bound changes, no new authority.

Host88 passes six groups11.409s. Build/media36 pass. Guest54 first passes
unchanged300ms pointer snapshot, then fails82.645s at keyboard display check;
no abc glyphs, roles stable, closed/media unchanged. Full acceptance remains open.
Keyboard inventory: independent mouse and key FIFOs discard cross-device
sequence order. Desktop read_key runs before mouse handling: a later key can
therefore precede the focus click. Reserve host89<=180s to reproduce this with
actual input adapter (both pointer-before-key and key-before-pointer cases).
No production change until needed header scope is resolved.

Proposed narrow scope addition (not yet approved):
userspace/sdk/include/reist/x86_64/desktop_platform.h, currently immutable CB
fixture, becomes one explicitly editable CF exception. Append private fixed
mouse_sequence[32] and key_sequence[64] arrays (768 bytes inside existing owned
workspace, no allocator quota increase). Store admitted input-v2 sequence per
queued mouse event/ANSI byte; dequeue only the earlier head, clear metadata on
consumption/fencing. ANSI CSI bytes share their source sequence. Preserve
32 mouse/64 byte capacities,128 events rate, generation checks, health/control
and every existing timeout. No syscall, wire format or device rights change.
Tests: both interleavings, same-source FIFO, CSI, wraparound, overflow and stale
epoch; uninstrumented focused abc pixel proof and original pointer gate.
Other CB files remain immutable and no CF/CB gate is removed. AGENTS package
rule4 requires stopping/reporting when an additional source file is required.

Host89 reproduces mouse overtaking an earlier key. Reserve host90<=180s
to report both independent interleavings instead of stopping after the first;
no production change or acceptance retry.

Host90 reproduces both production failures: mouse overtook earlier keyboard
event; key overtook earlier focus click. Proposed header remains untouched.
Scope approval requested under AGENTS rule4; implementation waits for reply.
Cumulative90 hosts,4 role builds,36 integration builds/media,54 guests.
All owned processes closed and overlays restored; no final gates/CF commit.

User replied "mach weiter" to the concrete additional-header request: approve
that one file and the documented fixed sequence arrays. CF remains active.
Freeze hosts91..93<=180s, one integration build/media37<=300/180s and changed
guest55<=600s. Preserve all90 hosts/36 builds/54 guests and frozen gates.
Header baseline is exact archived CB; append-only private fields, unchanged
wire/public syscall formats. Initial90 regression remains the red baseline.

Host91 passes six groups11.442s, both FIFO interleavings/CSI/wrap/fence.
Build/media37 pass; guest55 passes original pointer and image-change checks
62.442s but strengthened abc glyph oracle fails. Retained text-focus snapshot
still shows PAINT and inactive text taskbar; stable shows TEXT. Thus setup
never established actual text focus before typing. Correct the diagnostic
setup (not response limit): after the focus click, at most eight200ms polls
require the real Type glyphs plus active text taskbar pixel. Preserve every
poll image; fail if no focus. Then take baseline, inject original abc50ms
edges and keep original300ms keyboard snapshot/abc proof and pointer gate.
Reserve changed observer-only guest56<=600s on exact55 images, zero builds;
host92<=180s checks strengthened focus oracle against retained frames. No
production code changes, no relaxed latency gate, no acceptance from diagnostics.

Host92/93 glyph/focus oracle tests pass. Guest56 establishes real text focus,
then passes pixel-change checks63.210s but no abc even in stable snapshot.
Reserve guest57<=600s on identical55 media with a read-only final QMP capture
of existing client receive audits and text state. VM is already paused at
stable: walk bounded physical page tables, no debugger breakpoints or guest
writes; max96 cached table pages, fixed20544-byte audits/38-byte text. Capture
actual task generations and bind maps/images/scripts. No latency relaxation.

Guest57 capture ends63.562s at optimized-away paint.text_size; prior text
objects/audits retained: text buffer contains abc, size3; three received
KEYBOARD/pressed1 messages97/98/99 at41870/42240/42770ms, paint received only
pointer motion. No capture acceptance (binding incomplete; leaf filenames may
collide across address spaces). No need to repeat this observation.
Causal source finding: existing Surface PAINT_TEXT carries rect.height=1;
renderer draws16-pixel native glyphs, while damage differences retain height1.
First glyph row is empty, so incremental text repaints stay invisible. Correct
the selected native renderer's damage-to-raster translation by conservatively
including15 additional rows clipped to client bounds. Wire/API unchanged,
fixed8x16 native PSF contract; old profiles unchanged. This is within existing
allowed desktop.c scope. Reserve hosts94..96<=180s, build/media38<=300/180s,
changed guest58<=600s; retain93 hosts/37 builds/57 guest attempts, no gates.

Host94 missing raster-expansion regression; host95 all seven groups pass
11.760s after bounded native-only expansion. Capture utility corrected for
future use: optional text globals only for text role, leaf filenames include
CR3 to prevent cross-role overwrite. Guest57 remains failed, never relabeled.

Build/media38 pass; guest58 pointer/focus/pixel-change checks pass63.101s,
strict keyboard300ms still lacks glyphs. Stable now contains exact abc at
364,333: raster correction is proven visually, response latency remains.
Source inventory: surface_input_queued yields BEFORE runtime poll sends input,
so the peer is scheduled before its message exists. Native-only bounded helper
will poll/send, yield on one CPU, then poll once for the peer response. Preserve
all per-poll limits/health and old profiles. Reserve host96 regression and
host97 correction<=180s, build/media39<=300/180s, guest59<=600s. No limit raised.

Host97 passes seven groups11.942s; build/media39 pass. Guest59 normal
pointer/focus/pixel-change diagnostic63.039s, strict abc300ms still fails;
stable contains exact abc. Preserve failed timing; no CF gate credit.
Reserve one read-only guest60<=600s on exact59 media, zero builds/host gates,
using corrected paused client capture to distinguish admission/paint delay
after the send-before-yield correction. No runtime or latency changes.
Cumulative reservation97 hosts,4 role builds,39 builds/media,60 guests.

Guest60 fails51.719s before actual frontend/root READY: adapter -110,
root startup stage4; no injected keyboard or final client audit. Immutable
media unchanged, VM closed and fixture restored. CPU tail header1023/0/0/0,
retained256 complete records, no exhaustion result in retained tail; this
is not full-lifetime CPU proof. Last desktop charge tick4005; normal teardown
reaps desktop/input/both clients. failure-cpu-tail.json preserves decoded
read-only inventory. Do not retry unchanged or infer a specific timeout call
from shared -110. Need distinguish original startup deadline from health
freshness using bounded existing state capture before another correction.
Spent97 hosts,4 role builds,39 builds/media,60 guests. No final gates/commit.

Continuation: correct queue allowed_files to include already user-approved
private desktop_platform.h (contract approval recorded, queue omitted).
Latency inventory: one read_key per complete compositor iteration; guest57
client receipts spaced370/530ms despite100ms injection intervals. Batch up
to seven additional already queued printable bytes after successful Surface
key dispatch, preserving ordered mouse head, control keys and backpressure.
Private peek validates same state without consuming; enqueue before dequeue,
no additional poll/syscall/wait or wire/capacity change. Existing first key/UI
semantics and old profiles unchanged. Reserve host98 red then99 correction
<=180s, build/media40<=300/180s and guest61<=600s. Startup60 remains failed
and unclassified (-110); no limits raised or unchanged retry.

Host98 missing batch helper baseline; host99 all seven groups pass12.171s.
Reserve host100<=180s for actual SDK peek non-consumption and mouse-order
coverage before spending already reserved build40/guest61.

Host100 actual SDK peek purity/order passes10.100s. Build/media40 pass.
Guest61 reaches READY and pointer/focus but fails57.474s: input role exits71,
then adapter -32; no keyboard snapshot. Retained CPU ring has no exhaustion.
Do not attribute this to batching without evidence: normalized-driver failure
currently hides transfer/decode/publish statuses behind71. Add one bounded
failure-only fixed-format raw WRITE for selected10s driver, distinguishing
read/decode/publish/heartbeat and original status; retain exit statuses. Also
append startup failure clock/deadline/health context to existing adapter error
message (fixed stack buffer, no allocation/waits/formatting). Reserve host101
<=180s, build/media41<=300/180s, changed diagnostic guest62<=600s. These are
diagnostic changes, not a proposed timeout relaxation or acceptance retry.

Host101 seven groups11.870s pass; build/media41 pass. Guest62 fails51.907s
before READY (-110). Added context line absent: source inventory confirms
native console WRITE maximum64, context was93 bytes. Existing error remained
valid; original failure retained. Fold clock/deadline into single64-byte error
line with compile-time bound; no extra WRITE. Reserve host102<=180s (compile
includes static bound), build/media42<=300/180s and guest63<=600s to classify
the recurrent startup failure; no unchanged retry or timing relaxation.

Host102 rejects65-byte diagnostic at compile time (no guest/build spent).
Remove inner separator; two fixed-width16-hex fields in exact64-byte line.
Reserve host103<=180s to verify corrected boundary; build42/guest63 unspent.

Host103 SDK passes; build/media42 pass. Guest63 READY and stable, no role
loss, but original300ms pointer snapshot unchanged; abc absent at keyboard
snapshot and present at stable(364,333). Failed63.329s, no acceptance.
Reserve one observer-only guest64<=600s on exact63 media with corrected
paused client audit capture (zero build/host), to measure batching input
receipts; capture before final assertions so failed latency retains audits.
Cumulative ceiling103 hosts,4 role builds,42 builds/media,64 guests.

Guest64 capture completes, bindings exact; normal pointer checks pass63.661s,
abc300ms fails. Focus41090ms/keyboard41730ms; actual client receives a41480,
b42230,c42330. Batch shortens b/c spacing to100ms but initial delivery/paint
still slow. Inventory finds separate clock syscall before every empty input
and application receive, repeated in runtime polls. Move these clocks after
successful bounded nonblocking receive; validate monotonic time before any
message admission/health/rate mutation. Empty receives mutate no state; outer
pump clock/deadline/health checks unchanged. Reserve host104 regression and
105 correction<=180s, build/media43<=300/180s and guest65<=600s. No quota,
per-poll count, health freshness or latency gate change.

Host104 reproduces extra empty-receive clock calls. Host105 rejects proposed
optimization against existing backward-clock-on-empty regression (line415).
Preserve that invariant; restore production clocks and remove only the new
contradictory optimization expectation. No build43 or guest65 spent. Reserve
host106<=180s for full restored candidate verification.

## Concrete additional-file scope proposal: Surface input fairness

Guest64's bound read-only client audit proves a41480,b42230,c42330ms despite
100ms injected intervals. Current desktop batches pending bytes but runtime
sets input_sent[i] once across all16 drain rounds. Further pending input cannot
be sent while those rounds service synchronous PAINT_BEGIN/COMMIT exchanges.
The pending FIFO, owner validation and bounded send are already implemented in
userspace/gui/compositor/desktop_surface_runtime.c, currently outside CF scope
and immutable fixture. Do not duplicate that transport in desktop.c.
Proposed additional file: this runtime.c only, declared current-file fixture
exception and queue allow-list entry after approval. Native-full profile only:
permit at most one pending input send per live client per existing fair drain
round (max16), retaining IPC queue depth, FIFO order, -11 backpressure without
dequeue, generation checks, stop-on-error and existing16-round bound. Default
profile retains its once-per-poll behavior. Add actual-runtime host tests in
already allowed SDK harness for interleaved paint/input, backpressure and peer
fairness; then original pointer/abc300ms guest checks, all frozen final gates.
No new source file, wire format, capability, CPU/deadline/restart enlargement.
AGENTS package rule4 requires stop/report before editing this additional file;
proposal is not approval or runtime acceptance. Build43/guest65 remain unspent.

Explicit user approval: Ja, zusaetzliche Runtime-Datei freigeben. Add exactly
runtime.c to queue/current-file fixture exceptions. Host106 passed seven
groups11.829s. Reserve hosts107 baseline/108 corrected<=180s for actual poll
body with queued paint/input, peer fairness, -11 and old/full modes at O0/O2;
unspent build43/guest65 follow only passing host coverage.

Host107 actual poll reproduces input starvation under paint; host108 seven
groups12.542s pass O0/O2 old/full fairness and backpressure. Build/media43 pass.
Guest65 stable63.661s but pointer300ms and keyboard glyph latency fail.
Source follow-up: a pure input send is not counted as processed_round, so
without incoming paint requests the poll still ends after first event. Count
successful native input send as work within existing16 rounds; failed/full
sends do not sustain polling. Add input-only regression alongside paint cases.
Reserve hosts109 red/110 correction<=180s, build/media44<=300/180s and guest66
<=600s. Existing source approval covers runtime.c; quotas and gates unchanged.

Host109 hits60s fullO0 subprocess deadline in failing assertion; retain log.
Make expected fairness regression report counts and exit1 explicitly instead
of CRT assertion dialog. Host110 remains baseline, reserve111<=180s for fix.
Build44/guest66 unspent; no production retry.

Host110 reproduces native input-only sent1/1 vs16; host111 seven groups
12.135s pass after successful sends sustain existing rounds. Build/media44
pass. Guest66 READY/stable, no role loss, pointer300ms unchanged and abc only
stable; failure62.939s. No runtime acceptance/performance improvement claim.
Reserve observer-only guest67<=600s on exact66 media with existing bounded
read-only input-loop hardware breakpoints, zero builds/host. Need actual
input-admission-to-publication timings before further production changes.
Cumulative111 hosts,4 role builds,44 builds/media,67 guest ceiling.

Guest67 observer fails56.863s QMP VM-not-running/GDB return1; retain partial
39 observations, no acceptance timing. Pointer admission tick3995, next mouse
dispatch4007, physical pointer update4010. Existing main loop services Surface
rounds before input dispatch even when READY. Defer that first Surface poll
until after native live pointer publication for READY only; startup and old
profile unchanged. Existing end input flush performs the poll when queued;
otherwise perform it once before Surface-window synchronization. Retain all
per-poll fairness/health/fencing, no early send to unchecked peer. Reserve
host112 regression/113 fix<=180s, build/media45<=300/180s, guest68<=600s.

Host112 absent helper regression; host113 seven groups12.089s pass.
Build/media45 pass. Guest68 READY/stable, original pointer300ms and keyboard
abc timing fail63.654s; no role loss. Candidate unaccepted, all evidence kept.

## Concrete kernel prerequisite proposal: bounded query return

Read-only source inventory process_run.inc1224..1240/1293..1309: both native
MONOTONIC_MS and GETPID call process_run_resume64, just like explicit YIELD.
It saves context, changes RUNNING to READY, enqueues the task and enters full
process_run_dispatch64 (validation, heap/lifecycle dispatch and run queue).
Thus even successful read-only queries force scheduling/validation work; the
SDK and required monotonic/health checks invoke these many times per frame.
Guest67 partial observation shows150ms from accepted pointer to publication;
all latest uninstrumented guests still miss300ms. Exact contribution of the
query return path is not yet isolated by an A/B guest; do not claim a proved
performance gain. Removing required clock checks was correctly rejected105.

Propose a separate prerequisite transaction, with CF candidate archived and
paused byte-exact first (no mixed implementation). Selected full-desktop CPU
profile only: successful argument-validated MONOTONIC_MS/GETPID may resume the
same live generation through validated user-return machinery, without an
implicit yield. Cap consecutive query returns at8; mandatory ordinary
dispatch at cap, actual YIELD, block, error, exit, fault or IRQ preemption.
Preserve timer CPU charging/32-vs64 limits, IRQ preemption, immutable profiles,
register/CR3/stack/FP validation, queue ownership and generation cleanup. No
fast IPC/device path, new rights, deadline extension or resource-budget rise.
Reference semantics: POSIX clock_gettime/getpid versus explicit sched_yield;
no POSIX ABI compatibility claim. Defaults retain the old return path.

Source scope to freeze after authorization/inventory: process_run.inc and
cooperative_scheduler.asm plus the existing native CPU integration selectors,
bounded generation-owned counter/validation if needed, and focused host/guest
verifiers. Tests must include query results/invalid args, cap/peer fairness,
IRQ preemption and CPU exhaustion under query flood, stale-generation reuse,
cleanup, default artifact equality, and an A/B input timing proof. No claim
of necessity/sufficiency until those measurements; revert if no safe gain.
AGENTS package rule4 excludes these kernel files from active CF: stop before
implementation and request explicit additional kernel-package scope. User's
runtime.c approval above remains implemented and does not cover this source
expansion. No new package active, no kernel modification/reservation yet.
Final counters113 hosts,4 role builds,45 builds/media,68 guests spent. All
owned guests/debuggers closed and overlays restored; no final CF gate/commit.

User explicitly approved: Ja, begrenztes Kernel-Paket freigeben. Archive CF
byte-exact before separate prerequisite scope/implementation. No GUI or
performance acceptance implied. Current CF files all within approved scope.

## Resume after accepted CH4a755fdc - 2026-09-25

All six CH gates passed. User approved separate kernel acceptance with all
final CF timing limits retained. Restored19 archived CF source/contract files
byte-exact after clean accepted commit; queue/current work reconciled separately.
CF remains sole active; original pointer and abc300ms, startup/replacement/health
gates remain mandatory. CG/CH kernel and SDK are immutable accepted inputs.

Freeze next correction within existing native_client.c and startup host test:
full-profile text client uses the existing dynamic paint layer for line changes
(three bounded commands instead of complete five-command base repaint). Preserve
initial base frame, paint client and legacy profile; exact geometry/colors,
empty-line clearing and immediate error propagation tested before implementation.
No new wire format, rights, wait, queue, deadline or CPU budget. Prior receive
audit confirms a39500/b39600/c40150ms with eventual abc; measure actual effect.
Reservation hosts114..118<=180s, integration build/media46..47 under300/180s
limits, guests69..70<=600s. Spent113 hosts/4 role builds/45 build-media/68 guests
retained. CH guest evidence is separate. All previous failures preserved.

## CF diagnostic69 and bounded native-input dispatch correction

Host114 red, host115 all7 groups pass12.888s. Build/media46 succeeded;
guest69 failed abc300ms in60.819s: a at deadline, abc later, pointer passes.
All evidence retained and overlay restored. Spent115 hosts/4 role builds/46
build-media/69 guests. Source shows yield ingests native input during the16
Surface rounds, while WM dispatch occurs only after poll returns. Freeze
within approved runtime.c and render host: after one complete fair round,
return to WM when READY/live native queues contain input. Preserve input FIFO,
no consumption here, old/startup paths, quotas and all final gates. Host116
red regression,117 corrected regression; guest70 measures changed candidate.
Existing reservation remains unchanged.

CF host116 reproduces queued native-input delay, host117 all7 groups pass.
Build/media47 and guest70 complete; abc300ms still fails60.731s, stable roles
and immutable media retained, overlay restored. Spent117 hosts/4 role builds/
47 build-media/70 guests. No final gate. Reserve next observation guest71<=600s
with existing diagnostic70 images and paused audit capture (zero rebuild), to
identify client receive/paint timing; no timing acceptance from observer.
Reserve hosts118..120<=180s and guest72<=600s/build-media48<=300/180s only for
an evidence-directed correction; no unchanged retry and all failures retained.

Guest71 capture complete61.343s, abc timing failure retained. Text receive audit
a39290/b39410/c39960ms. Freeze guest72 as read-only four-probe path observation
on unchanged70 media, <=600s, zero rebuild: driver publish, WM key enqueue,
client audit receive, text paint_update. Preserve actual focus/injection and
all original assertions; observer results are not timing acceptance. Host118
verifier compile only. No guest-memory writes, same4096probe/600s bounds.

Observer72 completed62.750s with actual READY and normal abc failure. Its27
probes cover startup only: runner snapshot detached debugger before keyboard;
no inferred path conclusion. No forced termination occurred, all overlays and
media restored. Freeze observer73<=600s on same images, attach after paused
text-focus snapshot, immediately before original key injection. Same four
read-only probes and original gates. Host119 syntax check. No rebuild.

Guest73 observer53.140s failed mid-injection with QMP VM-not-running while
a hardware probe paused execution. Captured a enqueue38650/receive38680/paint
38690ms; no b/c inference. No source/image change or weakened final timing.
Freeze observer-only admission of explicitly rejected (not delivered) QMP
events: at most100 attempts/5s, sleep10ms, unrelated errors immediate. Host120
checks success after rejection, cap and unrelated failure. Reserve guest74
<=600s same image for complete path observation; production exercise unchanged.

Observer74 failed49.899s with input-role loss under hardware tracing. No
production timing conclusion. All failed observations and media preserved;
overlays restored. Stop hardware tracing for this path. Freeze within current
native_surface.c: selected-profile existing128-entry private receive audit also
captures dynamic BEGIN/COMMIT replies16/17; unchanged structure/capacity/rights.
Host121 red/122 actual O0/O2 regression, integration build/media48<=300/180s,
guest75<=600s paused audit only, no live debugger. Gate timing not weakened.
Spent120 hosts/4 role builds/47 build-media/74 guests.

Guest75 failed abc300ms60.541s, normal roles stable. Audit a38530, BEGIN38570,
COMMIT38610; b38970, BEGIN39000, c39030, COMMIT39050, next BEGIN39180/COMMIT39200.
Host121 red/122 eight groups pass12.358s; build/media48 pass. Main latency
is between short paint transactions; frame_begin unconditionally copies3MiB.
Freeze bounded dirty-tile back-buffer synchronization in allowed display.c,
startup.c and display host. Public caller-buffer behavior stays full-copy;
private opt-in only for startup-owned buffers that no caller mutates. Fixed
three-word stale map, <=192 tiles, existing two buffers, no rights/ABI expansion.
Cancellation/deactivation preserves stale writes; swap/immediate writes tracked.
Regression checks successive partial frames/cancel/idle/deactivate/edge tiles
and existing public odd-alignment direct-buffer test. Hosts123..125<=180s,
build/media49<=300/180s, guest76<=600s compare unchanged original input limits.
All prior122/4/48/75 counts retained. No claim this alone closes GUI latency.

Host123 red missing opt-in,124 all8 groups pass12.436s. Build/media49 pass;
guest76 abc300ms still fails60.528s, stable roles. Audit a38510/b38910/c39020;
paint replies38650/38680,38950/38980,39110/39140. Tile tracking alone did not
close latency. Preserve candidate/evidence without speed or acceptance claim.
Next bounded observation uses existing input-role audit too: record successful
normalized publishes with already-read charge timestamp, no extra syscall,
unchanged128 entries/wire/limits. Native_session.c and verifier already allowed.
Host125 actual profile regression; build/media50<=300/180s guest77<=600s paused
capture of driver plus both apps; no debugger. Spent124/4/49/76 retained.

Guest77 normal61s-class run fails abc300ms (60.534s), input publishes
a38450/b38570/c38720, app receives38770/39230/39320. Driver on time; pending
input remains behind compositor rounds. Host125 all8 groups12.521s. Reverted
tile synchronization and its opt-in test byte-exact from diagnostic75 before.zip
(display.c/startup.c/display host): complexity did not improve measured gate.
Freeze private synchronous poll callback within runtime.c/desktop.c and existing
render tests: only after printable Surface key passed normal UI dispatch, route
up to existing7 following printable keys before each existing fair round; no
mouse/control bypass, no stored pointers, no new wait/queue/rights/round budget.
Unrouted polls retain behavior; control/older mouse returns to normal dispatch.
Hosts126..129<=180s, builds/media51..52<=300/180s, guests78..79<=600s. Preserve
125hosts/4rolebuilds/50build-media/77guests and all old failed evidence.

## Proposed bounded empty-IPC-return prerequisite after diagnostic78

CF host126 records missing routed implementation; host127 all8 groups pass
12.378s. Integration build/media51 pass. Guest78 fails original abc300ms in
60.555s; pointer and role stability checks pass, media unchanged, overlay
restored. Text receives a38650/b38820/c38880: within230ms versus510..550ms in
previous candidates, but final visible abc still too late. No final CF gate
passed. Spent127 hosts/4 role builds/51 integration builds-media/78 guests;
hosts128..129/build52/guest79 are unspent. Hardware observer72..74 failures,
all previous results and discarded tile-copy candidate remain preserved.

Inventory: process_ipc.inc process_ipc_syscall64 validates unused registers,
message version/size/read-write ranges and invokes admitted IPC core. For a
completed empty poll it runs ready/copyout handling, clears its2144-byte scratch
and unconditionally jumps to process_run_resume64. This takes the ordinary
scheduler path even for timeout0/-11. The compositor separately polls input,
root and both application channels; these empty polls remain on the full path
after accepted CH, whose direct-return scope is strictly clock/PID only.

Proposed separate prerequisite, requiring explicit additional kernel scope:
only selected REIST_NATIVE_DESKTOP_CPU, fully validated nonblocking receive
(syscall51 or54 with timeout0) returning exactly EAGAIN(-11). After all existing
IPC completion, ready, validation and scratch cleanup, reuse the accepted
same-task return admission with the SAME shared eight-query cap. Never add an
independent cap, skip validation, alter IPC message/handle/generation checks,
change waits or successfully delivered-message scheduling. Nonempty receives,
waits, send, wrong rights/pointers/stale handles and all other errors retain
ordinary scheduling. Query, IRQ, CPU accounting, owner checks and default
artifacts remain mandatory. Feasibility and speed require actual comparison;
this proposal is not a claim that the change is necessary or sufficient.

Candidate source inventory for the next frozen package: arch/x86_64/proc/
process_ipc.inc and process_run.inc; existing query_return.inc/.h and
cooperative_scheduler.asm only if inventory proves adaptation needed. Include
actual host assembly predicate/return tests, native guest empty-poll flood,
peer fairness/eighth dispatch, invalid/stale/timeout/nonempty cases, CPU/IRQ and
cleanup, default artifact equality, complete accepted query regression and
unmodified GUI pointer/abc limits. Freeze exact files and finite development
and qualification reservations before implementation, after archiving CF and
a clean worktree boundary. Keep one active package, preserve CG/CH evidence,
no agent/push. CF/CB/final VMware obligations remain unchanged.

AGENTS package rule4 requires stopping before these kernel files, outside CF
allowed_files. Prior CH authorization names clock/PID only; latest approval
separates CH acceptance but does not expand that source/operation scope.
No kernel edit or new package activation is made before approval.

## Resume after accepted CI8b4baee1

CI six gates accepted, seal1ac6459a82ac5b2d947968b4937a6bf5aad02489741ec75aec11f61ff77ecea5.
Clean worktree checked, CF19 archived files restored byte-exact excluding
CURRENT_WORK; original stash retained. CF127hosts/4rolebuilds/51build-media/
78guests remain spent. Original final abc300ms, pointer, startup/health/recovery
and all CF/CB/VMware gates remain required; no OS completion claim.
Next bounded correction inside native_client.c: while waiting for dynamic
BEGIN, the public client library defers received keyboard events. Consume up
to the existing8 consecutive validated printable-key entries before sending
the line, preserving the first control/pointer barrier. Avoid a second frame
for keys already received. No extra IPC, waits, queues, rights or quotas.
Host regression injects keys during BEGIN and checks one atomic abc frame,
error propagation and barrier preservation before production change. Reserve
host128..132<=180s, integration build/media52..53<=300/180s and guests79..80
<=600s. Qualification remains separate. No library/kernel source expansion.

Host128 test compilation failed;129 reproduces queued-key omission;130 all8
groups pass. Build/media52 and guest79 spent: before keyboard injection, input
slot5/gen16 exits71 afterREADY (77.729s), no role-loss proof. It cannot be
attributed to the new text folding, which has not run yet. Use reserved guest80
with exact79 media and one hardware trap at input_failure to capture site/status
without changing guest state; no performance acceptance from debugger run.
No repeated unchanged acceptance attempt. New observer is within CF verifier.

Diagnostic80 spent89.841s, no failure-site hit: early hardware breakpoint
slows boot/input enough that pointer300ms fails before the focus operation
that preceded79 input exit. Retain as observational failure, no performance
claim. Narrow attachment to AFTER the unchanged pointer check, immediately
before focus input. Same79 guest bytes; no weakened assertion. Reserve one
additional diagnostic81<=600s, host132 syntax<=180s; prior counts retained.

Diagnostic81 closes89.215s with stable roles/no failure-site hit, but abc300ms
fails; debugger run is not performance acceptance. Original79 input exit remains
unresolved, never relabelled. Audit shows keys still arrive during successive
BEGIN/COMMIT waits. Next correction: selected text client keeps a fixed100ms
coalescing interval from FIRST dirty event, never renewed by later keys, while
preserving existing>=100ms frame-rate bound,8-event drain and all queue limits.
Post-BEGIN fold remains bounded. Regression checks first-event latency cap and
frame-rate cap; old/paint profiles unchanged. Reserve hosts133..136<=180s,
build/media53..54<=300/180s, guests82..84<=600s, no debugger in performance
run. Spent132hosts/4rolebuilds/52build-media/81guests retained.

Host133 red/134 all8 pass. Build/media53 and guest82: stable69.462s and
pointer pass, abc300ms fails. Clean audit first key39010 driver ->39310 text,
so queue-to-client delivery already costs300ms. Source inventory: platform
pump reads native input, then always submits up to8 display tiles BEFORE the
WM can dispatch that input. Bound correction inside approved platform file:
once defer display batch when live native input is queued; next pump MUST
service display even if input remains. Control/health always run first, same
8-tile cap and deadlines, no starvation or new rights. Host integration first
proves key ready with zero tile commits, then mandatory next-pump progress.
Use remaining hosts135/136, build/media54 and guest83. Existing limits stand.

Host135 red/136 all8 pass. Build/media54 pass; diagnostic83 fails9.981s with
empty serial, QMP TimeoutError before boot. Host19GiB free RAM, no leftover
QEMU/GDB/Python, D:6.5GiB free; no evidence of guest role execution or disk/RAM
exhaustion. Preserve this transport failure. Diagnostic84 uses exact83 media
with bounded host QMP-operation receipts, retaining every existing256-command/
2-second deadline and guest oracle. No guest debugger or memory mutation.
Reserve host137 syntax<=180s for added diagnostic receipts; no extra build.

Diagnostic84: exact83 image stable60.422s, pointer passed, abc300ms failed;
QMP phases captured (normal quit SHUTDOWN notification rejected by inherited
allowlist, VM still closed). Preserve after-gui84 candidate ZIP and binding.
100ms coalescing has not closed the limit; remove the added first-dirty delay
and its test while keeping the original100ms frame-rate bound. Next smallest
correction: selected runtime publishes its already queued one input per client
BEFORE polling paint requests in the same existing16 fair rounds. Existing
FIFO, backpressure, disconnect, capacity and yield budget retained. Regression
requires pending input attempted before first paint poll. Reserve hosts138..141
<=180s, builds/media55..56<=300/180s, guests85..86<=600s. Spent137 hosts/4 role
builds/54 build-media/84 guests retained. No final gate or OS claim.

Host138 negative assertion path timed out60s (Windows abort reporting); use
explicit failing exit in regression. Host139 all8 groups pass. Build/media55
and guest85 stable61.119s/pointer passed, abc300ms fails. Audit c delivered
38810, commit38930 vs driver key-up38690: only60ms remains for physical raster.
Inventory: every frame copies entire3MiB via REP MOVSQ. CPU admission already
requires SSE2 and eager FXSAVE64 preserves XMM0..15; existing FP lifecycle
guests pass, no AVX/XSAVE admission. Within allowed display adapter, use four
unaligned SSE2 vectors per64-byte copy/clear chunk, retain exact8/4-byte tails.
Function-local target attribute only; global no-SSE compilation defaults stay.
Existing host tests prove full buffers,4-byte alignment, odd tail, sentinels,
cancel/commit and cursor equivalence. No extra allocation or pixel publication,
no CPU/display/frame-rate quota change. Host140 all8 groups then reserved
build/media56/guest86; speed requires actual GUI proof, not host assumptions.

## GUI86 evidence and concrete Surface scope request

Host140 all8 groups passed; build/media56 and guest86 spent. Guest86 stable
61.972s, pointer passed, abc300ms failed. Keyboard snapshot CPU last tick38870ms;
text c received38660, BEGIN38780, COMMIT38820. Only50ms between COMMIT receipt
and snapshot, physical abc absent. Prior85 likewise COMMIT38930 vs snapshot
lasttick38980. These are coarse existing tick observations, not exact render
duration. Existing private audit records both asynchronous input and replies.
The separate BEGIN wait plus later COMMIT wait remains in the critical path.
SSE2 experiment did not close the gate; preserve tracked after-gui86 ZIP
SHA2568eae4abe044c62e048c1d0101a954848d5659a6a388e2a0b89c508b415db64fb, then restore display adapter exact
after-gui84 REP MOVSQ/STOSQ bytes. No unproven SIMD dependency remains.
Spent140 hosts/4 role builds/56 builds-media/86 guests; all failures retained.
No CF final gate started, no CF/CB/VMware acceptance. CI8b4baee1 stays accepted.

Proposed extension requiring AGENTS rule4 approval before source edits:
- userspace/gui/include/reist/gui/surface.h
- userspace/gui/include/reist/gui/surface_client.h
- userspace/gui/lib/surface_client.c
- userspace/gui/compositor/desktop_surface.c
- test/test_desktop_surface_host.c
- test/test_gui_surface_client_host.c
- test/test_gui_surface_source.py
This is the exact additional source/test list. Existing CF app/runtime/host/verifier files remain in scope.

Add one optional append-only Surface opcode for atomic dynamic text-frame
replacement using the existing fixed124-byte message geometry. Preserve every
old opcode, wire layout and wrapper; legacy peers reject the unsupported new
operation fail-closed. Before changing visible or staged state, validate owner,
generation, configured surface, text length/encoding, coordinates, colors,
reserved fields, layer and transaction state. Build a complete bounded candidate
using existing fixed paint-command capacity, then publish once or leave the old
frame byte-identical on failure. One correlated reply replaces the two separate
BEGIN/COMMIT acknowledgements. No speculative pipelining: sending TEXT/COMMIT
ahead of a rejected BEGIN could incorrectly mutate an older open transaction.

This is a documented additive extension of REIST Surface-v6 (project protocol;
no claim of Wayland/X11 wire compatibility). Determine whether feature/version
negotiation is required from the existing contract before freezing ABI details.
Same128-message quota,32-sample app budget,64-sample supervisor/compositor,
500ms existing maximum reply wait, queue/memory bounds and final300ms limits.
No new application rights, kernel or device/DMA change. Old profiles remain
exact. Host negative/rollback/stale/interleaved-input/busy tests first; actual
QEMU pixel/role-loss/CPU and full CF/CB/VMware gates remain mandatory.

Implementation pauses at this concrete scope/atomic-protocol decision. Do not
modify the above out-of-scope source or treat current host proofs as acceptance.

Archive correction: the first after-gui84/86 ZIP commands used git diff paths,
which exclude untracked CF inputs. Both originals are retained. A complete
after-gui86 snapshot now adds the unchanged untracked sources/tests/verifier to
the original tracked snapshot: complete-candidate.zip SHA256fa84e17e40232bc730e06d083338d52d4c33cdf7aea2567d6f95081dee6c997d.
Every entry is byte-verified and individually bound in complete-binding.json.
The saved SSE candidate is retained; current display source remains exact REP
copy implementation from after-gui84. No evidence was deleted.

## Approved atomic text implementation window

2026-09-25 renewed user "mach weiter da es schnell fertig werden muss" directly
after the concrete Surface scope question approves exactly the seven listed
files. Continue the existing attributed CF candidate; CI remains accepted.
Reserve hosts141..146 <=180s each, builds/media57..58 <=300/180s and guests87..88
<=600s. Prior140/4/56/86 spent retained, no final gate started.
Optional opcode24 in unchanged Surface-v6 envelope: dynamic layer only,
format=extension version1, serial=acknowledged configure serial, damage is
the complete line rectangle (height16), flags/buffer_id are XRGB foreground/
background, byte_size1..39 printable ASCII bytes, remaining payload zero.
All other fields zero. Reject active paint transaction, wrong owner/generation,
unacknowledged/stale configure, invalid bounds/colors/encoding before mutation.
Build one fixed command locally, replace dynamic list once, using existing
damage generation machinery. Existing optional-opcode precedent needs no
handshake: only selected matching full-desktop peer invokes it, unsupported
peers reject without fallback or speculative mutation. No automatic retry.
Server selected by REIST_NATIVE_FULL_DESKTOP, client by existing full startup
selector; old compiled profiles retain original code paths. Surface-v6 follows
wl_surface atomic commit state semantics but is not wire-compatible Wayland.
Same FIFO/deferred events, bounded reply wait, quotas and final300ms gates.

Host141 failed new positive dispatch as expected (opcode absent); host142 all9 groups pass, including real manager rollback and client interleaved-input/error behavior. Proceed reserved build/media57 and guest87, unchanged300ms pixel gate and no debugger.

Guest87/build-media57: stable60.703s, pointer pass, abc300ms fails; later stable
image contains exact abc. Input c38420, client38600, atomic reply38720, snapshot
last CPU38770ms. Preserve all evidence. Remaining full-screen3MiB frame-begin
copy is on every local line redraw. Within already approved display source,
selected full profile reuses existing staged bitmap as back-buffer repair set
between transactions. At begin copy only marked bounded64x64 tiles from front
to back then clear set; inside frame it records writes as before. Commit swaps
and retains changed tile set; cancel retains it without visible swap. Direct
front writes mark repair too; deactivate preserves it for later reactivation.
No new memory, publication, quota or authority. Old profile unchanged. Verify
full raster/cancel/blit/recovery tests at O0/O2 in selected profile and focused
partial-frame/cancel/reactivate regression. Reserve host143 reference behavior,144 full
hosts, remaining build/media58 and guest88 after passing hosts.

Host143 reference behavior passed; host144 all10 groups passed19.890s. Partial repair preserves cancel, direct writes, odd edge tiles, blit and deactivate/reactivate behavior; old adapter path also passes. Proceed reserved build/media58 and guest88. No acceptance claim.

Guest88/build-media58 spent: stable60.855s/pointer pass, abc300ms fail. Text
c received38460, atomic replies38490/38620, snapshot last CPU38740ms. Later
image correct. Preserve144 hosts/4 rolebuilds/58 media-builds/88 guests. Next
evidence-directed window: host145 syntax<=180s; guest89<=600s exact88 media,
no build. Add read-only compositor adapter/task capture immediately AFTER
paused keyboard snapshot; existing deadline/pixels unchanged, no debugger.
Fixed state17128bytes at exact linker symbol, slot4 CR3, max7pages,96tables,
existing QMP256 cap. Determine pending frame/dirty tiles before further fixes.

GUI89 exact88 media passes both pixel checks61.313s; read-only keyboard capture
shows frame0, dirty0, valid6 recently committed tiles. Previous88 failure stays
failed; this diagnostic is not retry-based acceptance. Timing remains variable.
Inventory: poll_clients always yields after a productive fair round even when
a newly committed frame needs immediate raster. Selected READY runtime should
return after that complete fair round if any active surface paint_generation
differs from presented_generation, preserving service to both clients,16-round
ceiling, input FIFO and all quotas. Startup/old profiles keep existing drain.
Already approved runtime file. Reserve hosts146..149<=180s, builds/media59..60
<=300/180s, guests90..92<=600s; no reset of145/4/58/89 spent counters. Regression
first: live READY paint exits before yield while both clients get their slice;
startup/inactive preserve prior fairness. NTFS compression01 of8 old disk images
freed4GiB with full before/after hashes identical; no evidence path deleted.

Host146 reproduces15 unnecessary drain yields with READY committed paint; host147 all10 groups pass. Proceed build/media59 and guest90 with selected early raster, no hardware observer.

GUI90/build-media59 passes real pointer and exact abc300ms checks61.002s after
early-raster correction. Host147 all10 groups passed. Preserve89 pass and88
failure without retry-based acceptance. Before qualification inventory finds
launch_pump deliberately returns-95 for replacement BIND; full frontend also
stores fault mode without invoking it. Replacement/startup-cancel/CPU runtime
proofs therefore remain open; no final gate or CF acceptance. Reserve three
development role builds05..07<=180s via defaults-dev03<=600s to check old exact
and selected roles now, plus remaining guests91/92 for evidence-directed lifecycle
diagnostic using existing private selector mechanism only. No new authority.

Defaults-dev03 passed three role builds05..07: all four old PRGs byte-identical
to accepted0af9682e, selected artifacts built. Guest91 exact90 media uses existing
validated first-root-entry private selector7 (text crash) through inherited
fault_selection helper. Only existing16-byte selector written before root entry;
no code/CPU/IRQ/authority patch. Capture READY and20s later lifecycle/tasks32768
within original600s/QMP bounds; diagnostic only. Host148 syntax before execution.

## GUI91 recovery failure and concrete supervisor scope request

Guest91 exact GUI90 image, inherited private root selector7, collection71.156s
completed and closed. Collection result.passed is NOT lifecycle acceptance.
Independent lifecycle-proof.json records replacement_observed=false: at READY
roles4/5/6/7 generations15/16/17/18 live. Text17 faults with UD receipt; adapter
logs ffffffa1 (-95), then paint/input/compositor/storage are reaped. A group
restart creates21..24 but fails; final slots2..7 empty, shell returns. Preserve
all raw task/CPU/device/serial captures and selection provenance. No final gate.

Root cause inventory: desktop_startup.c launch_pump explicitly rejects every
non-STOP control including CLIENT_REAPED/BIND with-95; the root replacement
protocol in shell_graphical.inc already requires CLIENT_REAPED -> new endpoint
HELLO -> actual CREATE/BIND -> BOUND. Immutable CB shell_full_desktop.inc tracks
only initial child owners in full_backend->children, full_desktop_child_step
rejects a different owner. desktop_services.c broker_adopt is startup-only and
requires both child slots empty; its last_children generation floor must not
be bypassed by directly overwriting arrays. Thus frontend-only replacement
would leave service identity/WAIT/cancel bound to the retired generation.

Concrete additional editable files requested under AGENTS rule4 (all currently
immutable CB archive inputs, same ee40925... fixture provenance):
- userspace/sdk/lib/x86_64/shell_full_desktop.inc
- userspace/sdk/lib/x86_64/desktop_services.c
- userspace/sdk/include/reist/x86_64/desktop_services.h
- test/x86_64_desktop_services_host.c
Existing approved startup/platform/runtime/shell_graphical/verifier/host files
cover the frontend half; no further source extension is proposed here.

Proposed bounded correction in the same active CF prerequisite:
1. On application failure stop serving its Surface, revoke its endpoint and
   retire only that owner's windows/events. Request root recovery using the
   existing FAILED control; preserve unrelated compositor/input/other app.
2. Root alone consumes or reuses the exact stored terminal/reap receipt. Add a
   private broker transition admitting replacement only for the same one of
   two slots after the old generation is fenced/reaped, with strict increasing
   generation, validated actual CREATE owner, existing global restart budget.
   Reject pending service operations for that child before publishing a new
   identity; preserve unrelated read objects/other child and every old handle
   rejection. No caller-provided receipt creates authority.
3. Existing CLIENT_REAPED/HELLO/BIND/BOUND handshake, unchanged control-v1 and
   surface-v6, supplies a fresh endpoint and new10s STARTING deadline. Reintegrate
   only after new generation, Surface configure/paint and healthy READY proof.
   Failure/exhaustion retains the existing bounded degraded/safe transition.
4. Complete same-profile deadline cancellation and CPU-exhaustion diagnostics
   using existing fault-mode semantics before original frozen CF gates. Do not
   move replacement into a later waived gate or call collection a proof.

Host tests first: wrong/old owner or receipt, generation rollback/replay, pending
operation, interleaved other child, delayed BIND/READY, deadline and exhausted
restart, idempotent cleanup. Fresh guest fault/replacement must preserve live
compositor/input/other app and prove stale identities cannot recover authority.
Retain original300ms input, CPU32/64, two apps, service16/1000ms and4queue,
10s startup, memory/IPC budgets and all CF/CB/VMware gates. No new syscall, wire
format, file-write/network/device/DMA rights, kernel change or extra application.
Do not edit these four files or expand queue before explicit scope approval.

Spent148 hosts/7 role builds/59 integration build-media/91 guests. Last complete
host147 all10 groups pass; defaults-dev03 old4 roles byte-exact, selected built;
GUI90 pointer+abc300ms pass. Remaining host149 is reserved for final syntax/scope
review only; build60/guest92 remain unspent pending genuine supervisor scope
decision. All processes closed, no implementation commit or final acceptance.

Host149 scope review caught bookkeeping error: queue edit matched active_id
substring and appended the seven user-approved Surface paths to the first
package instead of CF. No user authority was exceeded; correct only this own
queue edit, retaining all other package data. Reserve host150<=180s for exact
CF scope/syntax/diff recheck;149 failure retained. Four new supervisor files
remain unapproved/unmodified. No implementation or acceptance commit.

Host150 passes exact CF scope, syntax and diff check after queue correction. Final spent150 hosts/7 role builds/59 integration build-media/91 guests. Current complete candidate preserved in after-gui91/candidate.zip with per-file hashes; no active process or final gate. Await only the four-file supervisor scope decision above.

## Approved supervisor recovery implementation window

2026-09-25 renewed "mach weiter da es schnell fertig werden muss" immediately
after the concrete four-file question approves exactly those files. Verified
entire28-file after-gui91 candidate byte-for-byte before continuing attributed
CF implementation. Restored four approved CB fixture inputs exact archive hash.
Freeze hosts151..158<=180s, integration builds/media60..62<=300/180s, guests92..95
<=600s, including previously unspent60/92, no counter reset. Spent150/7/59/91.
Implement existing generation-scoped replacement protocol, broker/root binding
and frontend reintegration together, preserving every boundary in proposal.
No CF gate or commitment until all frozen proofs pass. No other package active.

Hosts151..155 retained:151 expected red missing broker replacement;152 old invalid-control error expectation;153/154 recovery fixture retained frontend_ready=0 from prior deadline negative test. Restore established READY only for recovery fixture; production continues to reject unready recovery. Host155 all11 groups pass26.040s. Add explicit late REAPED rejection before new deadline and exact replacement client/window checks. Host156 reserved for resulting complete host suite. Spent155/7/59/91, no frozen gate or acceptance. Next build/media60 and guest92 exercise actual selector7 replacement on fresh corrected media.

Host156 all11 groups pass25.743s. Build/media60 pass31.206/3.701s; guest92 collection69.094s: actual text17 reap and live replacement19, compositor15/input16/paint18 unchanged. Replacement text prompt visible in framebuffer, raw lifecycle-proof.json retained, not final acceptance. Direct review finds fault selector reset after replacement CREATE would inherit test fault; move reset before CREATE for full profile only. Host157 verifies resulting candidate; build61/guest93 will observe beyond replacement fault deadline with independent generation/pixel checks. Spent156/7/60/92.

Guest93 stable replacement proof passes88.627s, prompt pixels and generations retained over second20s observation. Host15712 groups passed23.365s. Further root review shows session_graphical_start already resets ordinary modes after initial launch, while selector13 intentionally keeps stale-handle mode. Remove redundant pre-CREATE reset and its source assertion; preserve93 evidence and use exact gui92 production image for next CPU/latency cases. Host158 validates restored11-group implementation and observer. Guest94 uses selector9 and demands actual status256 receipt plus isolated stable replacement; guest95 restores normal300ms input proof. Counters157/7/61/93 before those commands; no gate acceptance.

## Remaining startup cancellation proof window

Host158 all11 groups pass22.327s. GUI94 existing exact gui92 guest-source hashes
match current candidate; selector9 proves actual old text17 status256 CPU receipt,
new19 stable and prompt visible, compositor15/input16/paint18 unchanged87.839s.
GUI95 normal pointer/abc300ms is now running on same exact media. Spent158 hosts,
7 role builds,61 integration build-media,95 guests including running95.

Remaining concrete frozen claim is real STARTING deadline cancellation/reap.
Existing full frontend accepts but does not execute compositor fault modes;
selector15 is already admitted by root and unused. Freeze within existing
approved shell_graphical.inc/desktop_startup.c/host/verifier scope a selected-full
private selector15 -> mode s startup-stall diagnostic. After existing argument/
clock/deadline validation, sleep via existing bounded handshake_pause until the
original absolute deadline; never renew it, allocate endpoints or publish READY.
Normal selector0 and old profiles byte semantics unchanged. This tests the
actual supervisor deadline cancellation/reap, not an artificially smaller limit.
Host negative first: mode s never enters frontend, frees launch allocation,
no endpoints published; bounded fault sleep failures and original deadline.
Real guest must show no READY, compositor terminal/reap, no GUI live children,
no device owner and retained shell. No kernel, ABI or rights change.
Reserve hosts159..164<=180s, builds/media62..63<=300/180s and guests96..99<=600s;
62 already reserved and unspent, counters never reset. Each diagnostic remains
unaccepted until the original four gates and independent binding review pass.

GUI95 fails unchanged abc300ms59.868s; stable screenshot contains exact abc. Raw audit: input c38000, client38160, paint replies38180/38300; keyboard last tick38350. Actual client restarts100ms frame interval after synchronous reply, adding response latency to every frame. Correct selected text cadence to original paint start, preserving at least100ms between starts, request/CPU limits and old profile. Host159 expected-red actual extracted client branch regression,160 full suite; build62/guest96 latency proof before startup-stall work. No weakened deadline or unchanged retry.

STOP actual host disk exhaustion: build62(gui96) fails compiler command13, D available118784 then49152 bytes; no media/guest96 launched. Host159 expected red cadence;160 complete suite passed. Spent160/7/62/95. Lossless NTFS compression02 nine files initially reports zero compressed; force sets attribute without freeing bytes. Sparse release of independently verified zero tail268435456 bytes on gui95 boot-medium/base.raw reports reduced allocation, but total free remains49152 and final hash read fails ENOSPC. Preserve original matching gui92 media and recorded before SHA in compression02/result.json; no evidence deleted. Need actual host capacity before further builds/readback. No final gate or commit. Details disk-full-blocker.json.

Continuation: D now356700090368 bytes free. gui95 base.raw full SHA256 verified f847fe048deb49e9a3a4d304b213c2c7a52504fc78b2a0e9a8a5d80da546c834 against preserved before record; disk-recovery.json. Build63/media and guest96 reserved at gui96-rebuild, preceding build62 failure retained. No source change since passing host160.

Build63 succeeds29.644s; guest96 still fails abc300ms60.865s, stable abc present. Client c38740, final paint ACK38930, keyboard snapshot last tick38950. Production input flush unconditionally yields and drains again even after first fair poll returns a committed unpresented frame; this defeats runtime early-raster return. Host161 regression first for no extra yield/drain on completed paint;162 full host after correction. Freeze one additional build/media64<=300/180s for guest97 on changed renderer; preserve all prior counters, no unchanged retry. Startup-stall work remains subsequent within same CF.

Host162 all12 pass22.361s after fair-poll pending-paint fix. To avoid another integration rebuild, finish previously frozen selector15 startup-stall host regression163/correction164 before build64. This adds only diagnostic s path and selected-full selector mapping, normal paths unchanged; guests97 normal input,98 deadline cancellation,99 replacement reserved on that one image.

Host164 all12 pass22.143s. Build64/guest97 completes but abc300ms remains failed59.832s; input c37990 reaches text38290, final reply38370 after keyboard tick38340. Preserve evidence; next latency diagnosis must cover input dispatch/heartbeat delay rather than another unchanged retry. Guest98 independently tests implemented startup-stall selector15 using exact source-cloned selector admission and original diagnostic cleanup; demands no READY, real compositor terminal, reaped GUI profiles/tasks, fenced or unbound devices, live original shell. No gate waiver.

Guest98 deadline proof passes51.761s: compositor15 exits110, fully reaped GUI/profile state, devices fenced/unbound, original shell1 retained. Guest99 is a new read-only four-site keyboard diagnostic on exact gui97 media, replacing paint_update probe with launch_send to correlate heartbeat scheduling with actual input publication/enqueue/reception. Hardware stops are diagnostic only, never latency acceptance. Reserve hosts165..170<=180s, builds/media65..66<=300/180s, guests100..103<=600s for evidence-directed correction/qualification preparation; prior164/7/64/98 retained.

Guest99 read-only hardware observer ends51.625s with input16 fault142 before useful trace, not acceptance; logs retained. No normal-image fault inferred from instrumented capture. Standing user priority expressly requests actual VMware visual testing as soon as possible. Prepare isolated ignored full-desktop preview from exact gui97 signed floppy/ext2, existing4GiB/1CPU/PS2/no-network/no-shares hardware profile and bounded launcher. Reserve one VMware diagnostic<=120s (plus bounded start/stop), independent preview only: require real DESKTOP_OK+GRAPHICAL_READY and screenshot. CF/CB gates and pending300ms unchanged, no source package transition or release claim.

VMware preview from gui97 actually reaches LONG_MODE_BOOT_OK/DESKTOP_EXPLORER_OK/DESKTOP_OK/GRAPHICAL_READY. Sandbox pre-start failed Unknown error; approved host start succeeds, capture15s/stop8s timeout from VMware socket10038. Exact owned PID28612 force-terminated and base media SHA verified. No visual/performance acceptance; ignored separate preview launcher now handles optional capture and bounded owned-process fallback.
Next evidence-directed latency change: production launch_pump sends four synchronous health IPCs consecutively before returning to input dispatch. Successful IPC sends each take the normal scheduling path; this creates a four-handoff burst every250ms. Host165 actual extracted branch first proves current four sends instead of one; bounded correction emits at most one HEALTH per pump, preserving all four roles, original250ms round admission,1000ms health deadline, failure/recovery suppression and quotas. Host166 targeted heartbeat+SDK, build65/guest100 comparison; no traced timing accepted and no unchanged retry.

Build65/guest100 normal desktop stable, abc300ms still fails59.745s. The existing channel_read_wait advertises/zeros2060-byte bulk buffers even on input and application endpoints whose contract only admits64/124-byte IPC-v1 payloads. Use existing140-byte v1 envelope for those endpoints, keep root service bulk2060, reject replies larger than advertised before publication. This reduces hot receive buffer work without skipping clocks, relaxing deadlines or changing wire ABI/rights. Host167 regression first for actual envelope admission,168 integration; build66/guest101 comparison. Spent166 hosts/7 roles/65 build-media/100 QEMU guests plus one failed pre-start VMware attempt and one actual VMware boot diagnostic.


## Final CF qualification reservation (2026-09-25)

Host167 expected-red envelope admission;168 SDK passes7.779s. Build66 and
GUI101 fresh normal guest pass60.2667s: actual mouse raster and exact abc at
original300ms, unchanged owners in stable observation. Production now receives
140-byte IPC-v1 on input/surface endpoints, root retains2060-byte bulk envelope.
No clock/deadline/rights/CPU relaxation. GUI100 failure remains preserved.
Read-only verifier preflight169 confirms1787 source bindings, scope, actual
GUI101 role authority and pointer raster, and prior134/256/110 terminal receipts.
Spent169 development hosts/7 role builds/66 integration builds/101 QEMU guests.

Freeze qualification01 exact source/fixture/archive/base/gates in binding.json.
Run original four gates once, in order: targeted180s; defaults600s; runtime1800s;
review300s. Reserve three role builds (cumulative10), integration build/media67
300/180s and four fresh guests102..105 (normal, crash7, CPU9, startup-stall15).
Runtime guest deadline additionally capped by a shared1500s host window and540s
per guest, leaving the original1800s gate budget for cleanup/hash collection.
No guest timing assertion or acceptance criterion is relaxed. Review independently
checks raw pixel/task/profile/family/CPU/device/terminal evidence, exact old role
binaries, source and artifact hashes and signed media. No package transition or
commit until all four frozen gates pass. CB and full VMware acceptance remain open.


Qualification01: targeted13 tests pass24.984s; defaults pass16.909s (all four
old binaries exact). Build/media67 and guest102 complete but original abc300ms
fails65.821s; review not run, no acceptance. Both overlays restored exactly.
Spent169 development hosts/10 role builds/67 integration builds/102 QEMU guests.
Audit: a received40560/paint reply40590, b published40580 but received40860,
c40680/40890, final text reply41090. Stable pixels contain exact abc.
Full-profile paint_update always clears296 pixels even for one character, causing
five or six64-pixel display tile commits, each a scheduler handoff, before further
input dispatch. Freeze an in-scope app correction: dynamic line background width
is8*max(last successfully painted length,current length,1), bounded296. Preserve
old extent on failed response and include previous length when shortening. No
frame-rate, IPC, queue, CPU or time-limit change. Actual function host regression
first. Reserve development hosts170..174<=180s, builds/media68..69<=300/180s,
guests103..106<=600s; prior counts and failed qualification01 retained. Subsequent
qualification uses new directory and all original gates, never overwrite failure.


Host170 expected red whole-line extent;171 catches old width296 fixture assertion;
172 all14 groups pass20.835s. Build68 passes25.734s; guest103 still fails300ms
71.906s, stable abc present. Raw adapter confirms reduced one-tile text damage,
so retain the tested transfer reduction but do not claim it resolves input latency.
b publication38980/reception39300, c39080/39380; pending physical tile at39440.

Evidence-directed next correction in already allowed native_client.c: both idle
full-profile clients currently poll empty IPC then sleep10ms, repeatedly becoming
runnable while compositor dispatch is pending. Use existing blocking IPC receive
on first event only, up to50ms when no dirty frame waits; admitted messages wake
immediately. Translate its bounded -110 to empty, preserve eight-event slice and
10ms sleep after actual event work; do not add a second sleep after an empty wait.
Dirty frames use original nonblocking cadence. Old profile remains byte-exact.
No syscall/rights/budget changes or new timer; existing250ms heartbeat and fault
checks retain at most50ms idle wake interval, below1000ms health. Host173 red,
174 corrected suite; build69/guest104 comparison. Subsequent reservation remains
finite and counters never reset. Qualification01 failed evidence preserved.

Host173 new regression fixture fails compilation (missing local r/legacy indentation warning), no production execution. Correct fixture before red174. Reserve hosts175..180<=180s for correction verification; builds69..70 and guests104..107 remain finite. No reset of historical counters.


Host174 confirms the expected old-function assertion then assertion UI reaches
10s subprocess bound; retained as failed, not passed. Host175 all15 tests pass
23.546s. Build69 pass27.898s. GUI104 normal mouse+exact abc300ms now passes,
followed by stable live applications, media unchanged and VM closed.
Spent175 development hosts/10 role builds/69 integration builds/104 QEMU guests.
Freeze qualification02 for this changed candidate, retaining01 untouched. Original
four gate commands/time limits unchanged; reserve three role builds(cumulative13),
one build/media70 and four fresh guests105..108. Shared runtime host deadline and
independent raw review as01. No retry of unchanged failed candidate, no acceptance
or commit before all gates pass. VMware preview update uses this real GUI104 image
in a new isolated ignored directory, does not claim final acceptance.


Qualification02 targeted15 pass21.752s; defaults pass14.011s; build/media70,
guest105 fails exact abc300ms80.081s. Review and three other guests not run.
Spent175 development hosts/13 roles/70 builds/105 guests, all failures retained.
Raw c publication38110, reception38280, final paint reply38380; paused display
clock38370, stable abc present. Source inventory identifies a remaining startup
path on every live dirty frame: frontend_finish_frame drains application IPC and
pumps root/input before physical publication, although the main live loop already
does this and immediately follows. Freeze normal READY/no-recovery finish to one
existing bounded display-service batch and immediate return to that main loop.
STARTING and any recovery keep their original24-turn lifecycle/health/scene path;
invalid channels fail closed. Device validation, per-batch8 and sliding64/100ms
commit quota, next-loop health/root/input checks remain. No new authority, wait,
CPU or acceptance limit. Host176 actual adapter proof first: one dirty tile is
published without another IPC drain;177 full tests. Build71/media and guest106
comparison reserved300/180/600s; previous reserved build70 spent by qualification.


Host176 actual normal finish regression expected red;177 all15 pass20.920s.
Build/media71 and GUI106 now pass mouse/exact abc300ms and stable observation.
Spent177 development hosts/13 role builds/71 integration builds/106 guests.
Freeze qualification03 changed normal frame publication candidate: original four
gates once, unchanged180/600/1800/300s limits. Reserve3 role builds(cumulative16),
build/media72 and fresh guests107..110. Previous qualification01/02 preserved
failed; no acceptance claimed. STARTING/recovery paths unchanged by new fast finish.


Qualification03 targeted15 pass23.506s, defaults14.430s; build72/normal guest107
passes original mouse/abc300ms. Crash guest108 fails isolated replacement87.304s:
old text17 status134 valid; replacement19 created but compositor15 exhausts64 CPU
samples in the recovery repaint (tick4221), root fences/reaps the session. Trace
shows consecutive compositor IRQ charges4200..4210 and window count64 at4221.
No review/CPU/deadline final guests run. Counters177/16/72/108.

Inventory: full scene repaint on replacement still uses the unpaced live raster;
only initial STARTING uses the existing128K-pixel slices/50ms checkpoints. Extend
that same renderer pacing to active recovery. Checkpoints use the earliest
original nonzero recovery_end of active slots (no renewed deadline), and keep
startup behavior exact. Full64 CPU and all frame/input gates unchanged. Existing
allowed desktop.c, desktop_platform.c and host files only. Host178 regression:
READY recovery must use original recovery deadline after initial start expired;
179 complete suite. Reserve build/media73 and fresh crash109,normal110<=600s,
then CPU/deadline111..112 on the same changed image if both pass. No acceptance
from collection alone; all original final gates remain mandatory.


Host179 all15 pass23.925s; build73 and crash109 fail87.582s with the same actual
compositor64-sample exhaustion. Normal110 not started by the stopped sequence.
Do not infer raster pacing sufficient. Reserve guest110 instead as a read-only
terminal observer on exact build73: existing hardware terminal breakpoint reads
saved registers, one user-stack page and CPU bounds at compositor termination.
No timing acceptance for debugger run. Existing selector7 and cleanup retained;
observer survives READY snapshot only in this explicit diagnostic option. No
production change before locating the actual exhausted call chain. Spent179/16/73/109.


Guest110 terminal observer collects no terminal: batch GDB receives QMP snapshot
SIGINT at READY and detaches before the later fault, exit0 not a diagnostic pass.
Preserve log88.540s. Correct only observer attachment order: attach after paused
READY snapshot, before the20s fault window. No production change or timing claim.
Guest111 replaces its unspent diagnostic slot with this corrected observer on
build73; guest112 remains unspent. Counters179/16/73/110.


Guest111 now captures actual compositor CPU terminal: IPC receive on replacement
endpoint0x207, caller channels_surface+0x175, replacement HEALTH sequence8. The
one-page stack ends before higher callers. Host180 compiles exact current private
channel layout (2592bytes). Guest112 extends same single terminal observation to
bounded full saved user stack(max32KiB) and exact platform/channel state using its
saved page tables; no new breakpoint or production change. Capture identifies
where quota was reached, not yet which earlier work consumed the whole window.


Guest112 bounded terminal capture92.437s: channels live, frontend READY,
application failed/closed allzero, replacement health sequence5 fresh42330,
other31 fresh42250, recovery WAIT_READY(8), original end50950, now42460.
Saved chain launch_send -> launch_pump -> platform_pump -> main; CPU is spent
cycling while waiting for replacement presentation, not a stalled app or expired
recovery deadline. Full capture retained, no debugger timing accepted.
Freeze one existing50ms checkpoint after each still-pending recovery finish,
using its already validated earliest original recovery deadline. Normal frames
retain the new immediate publication path, completed recovery has no added wait.
This bounds recovery polling CPU independently of idle peers; all64/32 quotas,
health and10s deadlines remain. Actual SDK test181 red/182 corrected, then fresh
build74/crash113 and normal114; reserve hosts181..186<=180s, builds74..75<=300/180s,
guests113..116<=600s. Spent180/16/73/112; no counter reset or gate waiver.


Build74/crash113 passes109.260s: text17 status134, replacement19 and all unrelated
roles stable in both20s observations, actual prompt pixels. Same-image normal114
passes mouse/abc300ms and stable roles80.658s. No acceptance yet. Spent182 hosts,
16 role builds,74 integration builds,114 guests. Freeze qualification04 for this
changed recovery candidate: original four gates once with180/600/1800/300s limits,
three role builds(cumulative19), build/media75, fresh guests115..118(normal/crash/
CPU/deadline). All previous qualification failures retained, no unchanged retry.


Qualification04 targeted15 pass26.478s/defaults14.725s; build75/normal115 fails
47.813s during taskbar focus mouse-down, before keyboard. Failure snapshot proves
compositor quota64 at tick3633, protected display/input fenced; this is NOT an
application protocol error despite the first serial receipts being child71 reap.
Large live focus repaint still bypasses the bounded raster used for startup and
recovery. Spent182 hosts/19 role builds/75 integration builds/115 guests.

Freeze same128K-pixel/50ms clipped rendering for live damage exceeding128K pixels.
Small keyboard damage keeps its current immediate path. Live large frames carry
one local absolute monotonic deadline(now+1000ms), passed unchanged to each private
checkpoint; no renewal, heap, authority or queue changes. Each checkpoint preserves
control/input/health pumping and fixed wait<=50ms, checks the same deadline after
sleep. Initial/recovery deadlines and old profile remain exact; CPU64 and300ms
input gates remain. Add actual clipped-pixel equivalence/live fixed-deadline host
regressions183 first,184 full corrected suite. Existing allowed desktop.c,
desktop_platform.c/render/platform host/verifier files only. Reserve build/media76,
normal116 then crash117; finite remaining hosts183..186, builds76..77 and guests
116..120<=600s. Prior failures retained; no final acceptance.


Host183 expected red missing live-frame deadline/classifier;184 all15 pass23.627s.
Build76/normal116 passes focus, mouse, exact abc300ms and stable roles80.812s;
same-image crash117 passes isolated replacement and both20s observations109.662s.
Spent184 development hosts/19 roles/76 integration builds/117 guests. Freeze
qualification05 changed large-live-frame candidate: original four commands once,
180/600/1800/300s, three role builds(cumulative22), build/media77, fresh guests
118..121(normal/crash/CPU/deadline). Earlier failures retained. No CF acceptance,
queue transition or implementation commit before all four gates pass.


## CF accepted qualification05 (2026-09-25)

All four original gates passed once for this frozen candidate: targeted 24.082s,
defaults 14.732s, runtime 420.813s, independent review 5.348s. Four fresh
guests118..121 prove mouse and exact abc at300ms, stable roles, isolated crash
and CPU replacements, and original STARTING deadline cleanup. Old roles are
byte-exact. Reviewed source binding312fe122b9b87c311769bcd913791c5f89d1dc974dadf03b20b0dbb40e14e92c.
Evidence: build/codex-agent/r83cf-desktop-startup/qualification05/acceptance-seal.json
SHA256 edfce3c99981181f07bf0eb049ce008fe5c79f89d143959c058d8b5fe277a7da. All failed qualifications01..04 remain.
Spent counters:184 development hosts,22 role builds,77 integration build/media,
121 guests. CF is accepted; CB original five gates/eight new guests and actual
VMware/full native64 acceptance remain open. No whole-OS completion claim.
