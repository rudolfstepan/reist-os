# Full native desktop service integration (R8.3cb)

Frozen after display1402c13e and explicit approval of80aaf346. Authority is
exactly NATIVE_DESKTOP_SERVICE_PROPOSAL.md, including its two-app/read-only
limits. No implicit approval of higher display throughput or persistent writes.
Actual desktop.c is the compositor. Keep old prototype and all old profiles
byte-identical when the new explicit selector is disabled.

## Cohesive boundary

Root mediates immutable boot-image objects and exact manifest-bound application
lifecycles. Compositor never receives raw storage or generic task rights. Keep
eight task slots, existing endpoint/capacity pools,32 CPU samples/1000ms and
the established graphical health/restart/reap/fencing state machine. Only slots
6/7 may host applications. Descriptor IDs bind desktop, service and object
generations; no cache/PID may manufacture liveness. Read at most1MiB/object,
eight open read objects,32 entries/response, four queued operations, one active
FS transaction,16 new service requests/1000ms. Complete transfer deadline
120000ms; kernel syscall deadlines and per-call copy limits remain unchanged.

Service wire-v1 uses bounded fixed-size messages over the existing IPC bulk-v2
transport (2060-byte ABI,2048-byte payload), never raw user addresses. The root
control receiver can accept normal health frames alongside bulk requests;
kernel ipc_receive_bulk_timeout already preserves those types. Validate exact
version/size/reserved bytes, identities, sequence, paths, manifest indices,
rights, ranges and deadlines before enqueueing or dispatch. A malformed reply
fences the client session; no publish-on-error and no unchanged retry.
Any long operation advances in bounded steps between health/input checks.
Root blocks for neither a whole large-file capture nor an application lifetime.

Use existing ELF64/RNPGv3 capture/import and pinned SHA-256 for large role images;
preserve old RNPGv2 interfaces and exact disabled behavior. Native file/Surface
APIs retain established field layouts and negative errno conventions. Unsupported
write/acceleration/features report explicit errors. Do not synthesize successful
file reads, identities, launches, clocks or service grants to satisfy linking.

Compositor startup accounts separately for its accepted7291652-byte workspace,
two3MiB display buffers, font and bounded service state inside the unchanged
heap ceiling. Its actual event loop pumps coalesced display damage with input
and health; no100ms/four-tile prototype throttle. Use the actual ordinary shell
desktop dispatch and both Windows/Makefile image layouts. Root must revoke
objects, fence outputs, close channels, reap and validate fresh generations on
every configured exit/fault/hang path before reintegration.

## Execution reservation and frozen gates

Initial window:24 host development commands<=180s,4 builds<=300s,
4 media operations<=180s,4 diagnostics<=180s. Keep individual logs/counters;
failures stay failed. Evidence-directed additional finite windows follow the
standing interactive directive; no routine approval/reset. No nested agents.
All gate commands below run once in the qualification window, first failure
stops it. Complete the adapters and cheap admission checks before guests.

1. python test/test_x86_64_full_desktop.py -v (<=180s)
   Actual C root/client state transitions, ABI/layout, admission before effects,
   complete normal reads/directories/two launches and denied writes/foreign
   generations, quota/deadline/sequence/reply corruption, cancellation and
   revocation, allocator rollback, actual event-loop hooks, old/new hash bounds.
2. python scripts/verify_x86_64_full_desktop.py --defaults (<=300s)
   Complete disabled-source/output projection; bind accepted unchanged kernel,
   input, storage, large-file and earlier graphical evidence. Do not restart
   old VM matrices whose code/tools/images remain exactly unchanged.
3. python scripts/verify_x86_64_full_desktop.py --package (<=600s)
   Normal/hardware builds, genuine no-undefined native desktop ELF, manifest
   integrity, both installation layouts and signed boot media, decoder/import
   limits and exact allowed-file scope. No mini-desktop substitution.
4. python scripts/verify_x86_64_full_desktop.py --runtime (<=5000s)
   Eight new affected-path cases<=600s each,<=4200s aggregate: normal real UI
   and read/launch/exit; compositor fault; compositor hang; input loss; client
   fault/stale handle; storage fault; malformed service reply; root loss and
   fresh generation. Preserve raw logs/pixels/process/frame/IPC/device evidence.
5. python scripts/verify_x86_64_full_desktop.py --review (<=1200s)
   Independently replay every new case and verify input/frame/window/app,
   parent/child/resource cleanup, generation and isolation predicates. Final
   scope/diff review and source/tool/image hashes match the pre-gate freeze.

VMware visual/performance proof is still required after guest acceptance, using
the actual image with supported functions stated accurately. Neither partial
linking nor a painted screenshot completes native64. R3.6b remains deferred.

## Preserved prerequisite boundary

CB development hosts01..05 spent, leaving19/24. First expected absent source;
02..05 pass actual broker/client O0/O2 read/launch/queue/rate/revoke and malformed,
late and oversized replies. No build/media/diagnostic/final gate spent.
The existing native display query exposes only epoch, not actual dimensions;
kernel source needed for a truthful geometry query is outside this frozen scope.
CC therefore precedes runtime integration. All five attributed candidate files
are byte-verified in services-before-geometry01/files.zip under
build/codex-agent/native-vmware-desktop (SHA256
611d015daf4b148b728b8407e46ba60599a6befcc53d906156b8a35cb188e3c6), also preserved
in stash be7747004dd7b7604c7dce418170e2d67866aa32. No candidate acceptance claim.
Restore them after CC; service approval and every frozen CB gate remain valid.

CC accepted all five gates on24.09; actual geometry now available via the
explicit NativeDisplayInfo profile. Resume CB from the byte-verified archive,
retaining all five spent hosts and the full original service acceptance gates.

## Large periodic import authority boundary

After CC, CB hosts06..11 and builds01..03 advanced the actual SDK/storage
adapter. Host11 passes O0/O2 including unchanged VFS file/read clients,
1792-byte prefetch, bulk short-read CRC, path reads, queued absolute deadline,
write/foreign-process denial and supervised launch/identity/cancel/wait.
Build03 compiles41 real sources in5.116s,952552 reachable allocated bytes,
zero reachable undefined imports. This is an ET_REL porting object, not a boot
image or acceptance of every unsupported calendar/storage/namespace feature.
11/24 development hosts and3/4 builds spent; media/diagnostics/final gates0.

Startup inventory found that CREATE-v6 is periodic but RNPGv2-only, whereas
large CREATE-v7 is lifetime-only. The previously approved large-image proposal
explicitly excludes periodic CPU increase. Keep the service approval intact,
but stop before extending this separate kernel resource combination. Concrete
NATIVE_LARGE_PERIODIC_PROPOSAL.md requires explicit approval before freezing
that prerequisite. All nine attributed CB files remain visible and verified in
services-before-periodic01/files.zip (SHA256
 eff172ae42f2b5c489582d13de9d775e5ab79e09d55e827f5f4bf868f016294c).
No counter reset, silent scope expansion, source commit or partial acceptance.


## Resume after accepted CF f5ebfb0d (2026-09-25)

The accepted prerequisites CC/CD/CE/CG/CH/CI/CF supersede the historical
geometry, periodic and CPU exclusions only in their explicitly approved
profiles. Supervisor/compositor64, other roles32, original health/recovery
and final timing gates remain. Preserve actual CB counters73 hosts/45 builds/
23 media/27 guests; earlier sections are historical, not counter resets.

Inventory: materialize the exact CF qualification05 synthetic fixture from
ee40925b archive with accepted source overrides. All16 differing paths are
already CB allowed files; no CF fixes are overwritten. Bind the full fixture
in build/codex-agent/native-vmware-desktop/cb-resume-after-cf01/fixture-binding.json.
Reserve hosts74..81 <=180s each, builds46..48 <=300s, media24..26 <=180s,
guests28..31 <=600s for evidence-directed integration, not unchanged retries.
Implement the still-missing full-desktop verifier and complete eight-case
runner in their original allowed paths. Keep all five original final gates;
reserve their eight fresh guests separately after source freeze. One package,
no nested agents or push. Actual VMware visual acceptance remains separate.

CB host74 passed all six existing full-desktop tests at O0/O2 in20.133s
after exact fixture materialization. No CB final gate or build/guest consumed.
VMware visual diagnostic uses the unchanged qualification05 media and remains
a separate platform proof; its bounded180s session does not replace any CB case.

## VMware unattended retirement diagnosis (2026-09-25)

Actual current-media session c269bfd249854c53a0bd8c5961189b98 reached real
DESKTOP_OK/GRAPHICAL_READY and its window was captured. User confirms no
input; later returned to shell. Launcher readiness-only passed flag is NOT
a stability acceptance. Base media unchanged and VMware stopped cleanly.
Serial records filesystem status80 and a failed subsequent GUI generation.
Source inventory: storage is bounded by120000ms; retirement latches backend
fs_phase3, while full_graphical_open reuses it without clearing the retired
transport state for the proven new storage generation. Correct that in the
existing CB source scope; regression must reject old/busy/failed generations
and clear only retired transport fields. Keep120s service limit and existing
group recovery budgets. Reserve development host75 red,76 green, build46,
media24 and guest28 for actual storage-deadline recovery, <=600s. Existing
reservations/counters stay spent. VMware stability remains failed/pending.

Guest28 reproduced the unattended120s expiry and failed reintegration even
after the retired-transport fix. Keep failed result; no corrected VMware
launch. New-generation roles are cancelled before READY, so freeze a bounded
error/stage diagnostic only on failed graphical_launch in the existing root
source, then build47/media25/guest29 from the prior reservation. No timing or
acceptance change and no unchanged retry. Original helper regression stays.

Source follow-up identifies the earlier reintegration failure before grant:
graphical_create invokes full_graphical_replace_binding for new applications
even during whole-group STARTING, when the old broker is correctly revoked.
Host77 reproduces the wrong branch. Restrict the existing replacement call to
LIVE; STARTING keeps full_graphical_open/adopt after all CREATE/BIND receipts.
No generation checks removed, no old broker reactivation. Host78/build48/
media26/guest30 reserved; guest29 retains the prior diagnostic build47.

Guest29 completed (the attempted second-QMP stop could not connect): failed
185.628s with DESKTOP_RESTART_ERRORffffff8c (-116), stage2. This independently
confirms the host77 STARTING branch diagnosis. Host78 all seven full-desktop
tests passed19.351s. Build48 completed all success markers; its receipt wrapper
failed after completion because a relative log was passed to relative_to.
The original log and wrapper-error.json preserve that administrative failure;
no rebuild. Media26 passed its signed-image checks; guest30 now verifies both
fixes across actual storage expiry, unchanged limits. Current counters78 hosts,
48 builds,26 media,30 guests (guest30 running).

Guest30 passed actual storage-deadline recovery in177.848s: exact old FS
status80 receipt, new filesystem/compositor/input/text/paint generations,
unchanged root and role authority/CPU masks, stable10s and media unchanged.
Evidence cb-resume-after-cf01/guest30/proof.json. Corrected VMware package
20260925-tested is now under bounded180s actual-platform observation.
This diagnostic is not the original CB eight-case qualification.

## Real-compositor fault-mode integration inventory

The archived full desktop transports the existing private u/h/q selector in
its handshake but never executes it; the old prototype did. CB compositor
fault/hang gates therefore need the actual launch pump to consume those
existing modes after READY and original startup deadline+500ms. Add bounded
hang60*100ms without health, real invalid-opcode trap, and finite CPU-burn
loop under unchanged kernel CPU bound. Mode0 does nothing. No new wire or
rights. Host79 red/80 green within original reserved hosts; additionally
reserve builds49..50 <=300s, media27..28 <=180s, guests32..33 <=600s for
actual fault/recovery proof. Preserve all78/48/26/30 spent counters and unused
guest31. Final five gates/eight cases remain unchanged and unstarted.

## Proposed CB input-driver scope extension after VMware dd5c10f0 (pending)

Build48/media26 VMware session dd5c10f0b842438c86235abdb36ab8c2 reached real
DESKTOP_OK/GRAPHICAL_READY/MOUSE_OK, then the input owner slot5 generation16
terminated with exact status256/kind3 (CPU budget). Desktop received EPIPE
(-32), and group restart failed at stage4 with -32. Launcher correctly failed
87.447s, stopped its VM and proved base media unchanged. This is distinct from
the fixed storage-boundary restart; no VMware stability acceptance.

The PS/2 implementation uses eight raw reads per round, then only10ms sleep
under active input (50ms when idle). Continuous mouse bytes can therefore
consume its unchanged32-sample/1000ms budget. The relevant file
userspace/drivers/ps2/native_session.c was in predecessor CF but is outside
CB allowed_files. AGENTS package rule4 requires a scope stop/report before
editing this additional source. Proposed narrow extension: that single file;
regression/runner work stays in already allowed test/test_x86_64_full_desktop.py
and scripts/run_qemu_x86_64_full_desktop.py. Pace active input rounds with25ms
bounded sleep, preserving eight-byte fair slices, packet100ms deadlines,
health250/1000ms, event FIFO/rate128, CPU32, authority and old disabled profile.
Require actual continuous-mouse QEMU and VMware proof; if evidence contradicts
that pacing, stop that attempt and diagnose, never raise limits or retry blindly.
No driver edits made pending scope resolution. Freeze host81..84 <=180s,
role builds <=180s, full builds49..50 <=300s/media27..28 <=180s (already reserved),
QEMU guests31..33 <=600s and at most two VMware sessions180s for this correction.
All prior80 hosts/48 builds/26 media/30 guests remain spent.

Additional original CB gate inventory: real desktop ignored transported
private u/h/q fault selectors. Host79 demonstrated missing hook; host80 all
eight tests passed19.626s after bounded launch-pump integration. This source
is uncommitted and has not yet had a fresh runtime build; normal VMware48
contains only the two storage/group corrections. Original five final CB gates
and eight-case runtime remain unstarted. Never infer completion from these
intermediate diagnostics.

User renewed mach weiter after the concrete PS/2 scope request on2026-09-25.
Treat as approval of that narrow proposal; added only the named PS/2 source
to CB allowed_files. Existing reservation81..84/49..50/27..28/31..33 retained.

Host81 expected-red/82 full nine tests passed19.094s; build49/media27 passed.
Guest31 failed after91 movement batches49.998s: input slot5/gen16 terminal110
(kind4), not CPU256. The loop directly exits110 when an incomplete PS/2 packet
reaches its100ms deadline. The fixed25ms/50ms sleep also delayed incomplete
packets. Tighten only incomplete-packet waits to5ms; complete active rounds
remain25ms and idle50ms. Original deadlines/FIFO/eight-read ceiling/CPU32 stay.
Host83 red/84 green, build50/media28/guest32 use existing reservation. Preserve
guest31 failure; do not launch that failed candidate in VMware.

Host83 red/84 nine tests pass19.084s, build50/media28 pass. Guest32 reached
227 movement batches without guest fault, then the inherited generic QMP
transport hit its256-request host limit (53.582s); snapshots/cleanup request
also refused, owned process reaped by existing fallback. Preserve failed run.
The new801-event diagnostic requires more than256 calls; define its own finite
1024-call QMP transport in the allowed full-desktop runner, leaving ordinary
256-call clients and all operation/response/byte/deadline checks intact. This
is the new diagnostic host-command reservation, not any change to frozen CB
gates or guest limits. Guest33 uses the exact same build50/media28 and corrected
observer, no rebuild and no unchanged retry. Total spent84/50/28/32.

Reserve next in-scope verification window hosts85..88 <=180s, guests34..37
<=600s for affected input latency and existing compositor/input fault modes.
No unchanged retries, no resets:84 hosts/50 builds/28 media/33 guests spent
(guest33 running). No new build needed unless a concrete source correction
requires it. Host85 checks real ordinary256/new1024 QMP limits and expired
deadline rejection without socket writes; it does not run another guest.

Host85 transport regression passed0.786s. Guest33 failed48.550s after13
mouse batches: text slot6/gen17 exited71/kind4; input remained alive.
Retain failure, no stability claim. Guest34 uses reserved600s on unchanged
build50/media28 with a read-only hardware-breakpoint observer for actual text
main error exits after READY. At most four breakpoints, bounded256 hits;
map/PRG hashes and source retained. This is cause diagnosis, not latency proof.
Counters85 hosts/50 builds/28 media/33 guests before guest34.

Guest34 failed50.759s: QMP cont raced GDB continue (VM not running), no
error-site observation obtained; VM closed/media unchanged. Guest35 corrects
observer synchronization by waiting for running state, never issuing a second
cont. Same build50/media28, reserved600s, no unchanged retry.

Guest35 failed49.195s: debugger breakpoints transiently pause VM and QMP
input injection rejects paused targets; no guest error captured. Guest36
records and waits at most20*5ms for that exact host injection rejection,
within existing1024 QMP/600s reservation. All other failures remain fatal.
Same immutable media, no source change, no latency acceptance.

Guest36 failed51.401s after272 batches: input slot5/gen16 CPU256/kind3,
text observer no error. CPU ring confirms32 charges in100-tick window at3970.
Guest37 adds32 read-only input sleep-entry observations (existing four hardware
breakpoints; replaces paint-return site), to distinguish partial5ms from
complete25ms rounds before selecting any source correction. Same600s image.

Guest37 failed48.715s: input exits71/kind4; text health returnsEBADF(-9)
after endpoint revocation. Observed partial sleeps5ms at ticks3640/3652,
so one input round consumed120ms including scheduling. No text-source fix
is justified: its endpoint error is downstream of input loss in this run.
Counters85/50/28/37. Freeze diagnosis38..39 <=600s each (no build/media),
host86..88 remain. Guest38 replaces all routine breakpoints with the single
actual input_failure entry0x410a39, matching linked input map, capturing its
site/status arguments. Preserve prior failures; no unchanged retry.

## Proposed bounded input-read return prerequisite (2026-09-25; not authorized)

Guest38 failed50.042s with input slot5/gen16 CPU256/kind3; no input_failure
callback because kernel CPU fencing happens first. Original signed media
unchanged, own guest closed. Guests34/35 are diagnostic transport failures;
36/38 reproduce the input CPU failure;37 observes text health EBADF after
input endpoint revocation. All failures retained. Spent85 hosts/50 builds/
28 media/38 guests. Guest39 unused; no unchanged rerun is planned.

Read-only source inventory: native_input_syscall64.result in
arch/x86_64/devices/input_domain.inc always goes through process_run_resume64
and the complete dispatcher, even for one valid READ byte or an empty READ.
The existing query_resume64 in process_run.inc already implements the accepted
same-task return with a shared eight-call burst, unchanged IRQ preemption,
CPU accounting and generation ownership. The input loop still makes up to
eight mediated reads, with fresh deadline checks, before sleeping. Guest37
observed two partial-round sleep entries120ms apart despite requesting5ms;
this timing is diagnostic/instrumented, not an acceptance benchmark.

Concrete proposed kernel change, exclusively after normal request validation,
PIO completion and clearing the private64-byte request scratch:
- In the selected desktop CPU profile, use query_resume64 only when the
  validated original operation is READ(3) and result is1..65536 or EAGAIN(-11).
- All invalid requests, lifecycle operations, controller/data writes, quota
  errors and other failures retain process_run_resume64.
- Reuse the existing shared eight-return burst; do not reset it on a read.
  Keep every100ms operation deadline, CPU32 input budget, IRQ, generation,
  FIFO, eight-read round, decoder and128 event/s constraint.
- No new syscall, wire format, direct device right or Ring0 protocol parsing.

Required new source scope: arch/x86_64/devices/input_domain.inc. Existing
query_resume64 is reused without modification. Prior user permission for the
clock/PID kernel prerequisite did not include device-read return paths.
AGENTS rule4 therefore requires approval before implementation. If approved,
freeze a separate prerequisite transaction and preserve all attributed CB
changes byte-exact before switching; no mixed unverified implementation.

Proposed proof: host tests of the actual assembly routing (READ success/empty,
invalid operations/results and old-profile output), existing burst ownership
and CPU-accounting invariants; a fresh uninstrumented801-event mouse run with
same owners and CPU32, original300ms pointer/text checks and a negative fault
case. Preserve all five final CB gates/eight fresh lifecycle cases. No claim
that this improves speed or removes the fault until measured on QEMU and
VMware. Host86 below only reviews preserved evidence; no kernel source edit.

Host86 independent retained-evidence review passed0.052s; exact CPU32
exhaustion in guests36/38 and EBADF health in37 confirmed. git diff --check
passed. Spent86/50/28/38. No new kernel implementation or acceptance claim.


## Resume after accepted CI898f30d5 (2026-09-25)

CI passed all four frozen gates; exact source-only CB archive28394e53 restored
after clean commit boundary. Preserve CB spent86 hosts/50 builds/28 media/38
QEMU diagnostics. VMware sessions01..03 all reach actual desktop; host mouse
injection fails before clicks, not guest acceptance. Sources/media unchanged.
Session04 reserves180s passive/manual observation and bounded owned-VM stop;
launcher must reach complete observation deadline and reject shell return.
Manual input assessment is required because Windows cursor injection could not
be demonstrated. Original five gates/eight runtime cases remain unchanged.
Backend LAUNCH=-95 remains an implementation gap; adopted startup apps do not
prove requested service launch. No new source changes beyond restored CB yet.


## VMware04 real failure and targeted drag reproduction (2026-09-25)

Session91b5a88a failed148.645s: actual desktop98.443s, then slot4/gen15
CPU256/kind3; subsequent startup fails EPIPE(-32),stage4, shell returns.
Stop0/base media unchanged. Screenshot shows moved windows; manual feedback
pending. This invalidates VMware stability, without changing accepted CI gates.
Reserve CB hosts87..90<=180s and guest39<=180s, no build/media. Extend only
existing allowed runner/test files with explicit bounded drag diagnostic and
60..600s selectable timeout (existing default600 unchanged). Reuse byte-exact
CI guest media; hold left button on known paint title and alternate801 small
movements, release, retain raw task/CPU/pixel evidence. No CPU-budget increase,
no guest-source fix until reproduction/localization. Preserve all counters.


## Confirmed unpaced live-frame path; correction window (2026-09-25)

Host87 red missing diagnostic option;host88 two admission/transport tests pass.
Guest39 reproduces failure49.726s after233 drag events,closed/media unchanged.
Raw CPU record303:slot4/gen15,limit64,period100ticks,used63->64,result2.
Source inventory: large/startup frames use50ms bounded checkpoints, while
small live/cached move frames and dirty-loop tail do not sleep. Continuous
window dragging therefore bypasses existing rendering pacing.
Reserve hosts89..96<=180s, build51<=300s,media29<=180s,guests40/41<=180s
each for corrected drag and original300ms pointer/text exercise. Apply existing
50ms live-frame checkpoint to the uncovered small/cached live path, preserving
fixed1000ms frame deadline, all startup/recovery paths, CPU64 and all old
profiles. Allowed desktop.c and full-desktop test only; no kernel edit.
Original final gates unchanged; these remain developmental comparisons.
User corrected visible-shell claim: native_console.inc exclusively COM1, no
visible framebuffer console. Record this separate recovery UI gap; do not
claim serial prompt is visible or silently add a kernel terminal renderer.


Build51/media29 and guests40/41 pass:801 drags+10s stable67.222s; original
300ms pointer/exact abc58.468s. Hosts93/94 independently verify stable owners,
CPU limits, raw trace/no exhaustion and pixels. Hosts spent94 total. Reserve
one180s VMware05 manual/passive session on new20260925-live-frame package;
require full observation, no serial shell return. All prior failures retained.


VMware05 bc5bef69: full170.494s observation and stop0, immutable media, no
serial shell return/CPU256. Storage120s retirement initiated recreation; no
second READY before deadline. Independent review therefore does NOT accept
stability, regardless of raw launcher observation flag. Preserve raw result.
Host95 pixel review confirms exact4,2 title displacement/stability. Spent95
hosts/51builds/29media/41QEMU guests and5 VMware sessions. No CB acceptance.


## Recovery continuation on current build51 (2026-09-25)

Preserve spent95/51/29/41 and five VMware sessions. Freeze hosts96..100
<=180s and QEMU guest42<=600s, using existing approved600s QEMU operation
limit and exact prior storage-recovery observer from guest30. Current media29
has changed live-frame pacing; require actual120s storage retirement, second
READY, newer storage/all GUI owners and10s stable replacement. No debugger,
no timer manipulation, no build/media, no VMware limit change. This is a
current-path recovery proof, not an unchanged retry or final-gate substitute.


## Proposed application-slot decoupling: one additional source file

Inventory after build51 (2026-09-25): the real backend LAUNCH still returns
ENOTSUP. Native clients additionally hard-code application kind into both
owner slot and health/HELLO role: native_client.c uses6+REIST_NATIVE_CLIENT
and2+REIST_NATIVE_CLIENT. Text is therefore permanently tied to slot6 and
paint to slot7. A manifest-bound launch into either of the two available
application slots cannot reuse that identity assumption. Do not invent a
kernel owner, silently discard the launch, or reserve dummy tasks to force
allocation order.

Requested scope addition: userspace/gui/apps/native_client.c only. Current
CB allowed_files does not include it; AGENTS package rule4 requires explicit
scope approval before editing. Existing approval of compositor runtime and
kernel prerequisites is not approval of this separate source file.

Concrete implementation: a new explicit full-desktop build selector enables
private REIST role-arguments-v2. Keep eight argv entries and all size limits;
the existing private fault-mode argument carries a bounded mode/slot pair.
Accept only supervisor-supplied application slots6 or7, exact termination,
existing fault modes and unchanged generation/deadline admission. Derive
health/HELLO role from that admitted slot, independently of text/paint kind.
Kernel owner validation and endpoint delegation remain authoritative; the
argument grants no authority. Original clients/profiles keep v1 arguments and
byte-identical disabled output. POSIX-style argc/argv entry remains unchanged;
the private REIST role protocol is explicitly versioned, not a POSIX feature.

All other implementation files already belong to CB: full-desktop build
wrapper, supervisor service backend, SDK client/channel adapters, desktop
launch dispatch and current host tests. Both commands remain manifest/digest
bound and use existing slots6/7 only. No kernel change, CPU/heap increase,
new task slot, device right, writable file or generic process authority.

After approval freeze hosts101..112<=180s, builds52..53<=300s, media30..31
<=180s, guests43..46<=600s for both launch orders, close/wait/relaunch,
failure rollback and stale owner rejection. Existing final five gates/eight
fresh cases remain mandatory. Approval is scope authority, not acceptance.
Until approval, do not edit native_client.c or change the queue's allowed list.
Current independent recovery guest42 may finish; all existing evidence stays.


Explicit user approval received2026-09-25: "Ja, native_client.c fuer diesen
Startpfad freigeben" in direct answer to the named-file request. Add only that
file to active CB scope; proposed bounded window101..112/52..53/30..31/43..46
is now frozen. Guest42 passes176.487s including natural120s storage retirement,
second READY, new storage/all GUI generations and10s stable replacement.
No VMware extension/acceptance is inferred. Old counters remain95/51/29/42.

Build52 fails the unchanged root image ceiling: text grows from0xdf28 to0xe458,
forcing one more page; image ends0x440f40 beyond0x440000. Preserve failure.
For reserved build53 select existing -Oz also for full-desktop root console,
image parser and storage SDK translation units, previously compiled -O2.
Only the root adapter compilation changes; independent drivers/filesystem and
all disabled profiles retain original flags. No capacity/linker/authority change.
Host107 checks complete current targeted tests before build53; new guest proofs
still mandatory, including timing and launch/reap. Hosts101/104 expected red,
102/105 harness failures,103/106 passed; no final gate has run.

2026-09-26 build53 failed before root link: compiler60s timeout in font_catalog.c.
Host System log records wall-clock changes23:54:21/23:54:49 and standby/resume;
launcher reported7198.577s. No running compiler/build remains. Preserve log;
this is not evidence for root size or guest behavior. Reserve build54<=300s
with explicit subprocess timeout after host resume; no compiler limit increase.
Host107 all13 tests passed20.976s. Media30..31/guests43..46 still unspent.

Build54 failed23.669s: root text0xe3fc, still one page too large. Only92bytes
saved by root -Oz units. Map identifies2631byte unrolled vendor SHA256 block.
Use pinned vendor MBEDTLS_SHA256_SMALLER loop implementation only for full
desktop root hash units; same SHA256 algorithm/digest, existing2000ms hash
deadline and yielding unchanged. Host108 verifies actual large-image hash and
rejection at O0/O2 with this selector, then reserve build55<=300s. No third-party
source edit or disabled-profile change; guest timing remains mandatory.

Build55 passes27.996s; media30 passes. Host108 compact SHA256 and host109
four disabled native-client object comparisons pass (both apps, startup on/off).
Guest43 failed52.368s in observer NameError(struct missing), after both actual
normal app exits; no launch performed. Raw reaps show slots7/6 status0 reason2.
Correct only observer namespace, use already reserved guest44; no image change.

Guest44 fails52.367s: both regular status0/reason2 closes cause new app owners
before requested launch. Current channel_application_fail marks even EPIPE as
fault, so frontend requests replacement despite an acknowledged CLOSE send.
Host110 regression red confirms distinction absent. Record successfully sent
CLOSE for exact owner only through existing1000ms retire window; only EPIPE
inside that window is normal. All other errors/expired closes still fail.
Reset marker on replacement/direct launch; existing reap receipt remains required.
Files remain CB scope, runtime file unchanged. Reserve build56<=300s and
media32<=180s (media31 remains unspent); original guests45..46 remain available.

Build56 passes27.821s/media32 passes. Guest45 fails52.845s in observer:
paint normal close now leaves slot7 free(0,0), old text survives; framebuffer
shows taskbar resized to Computer80..477 and Application478..878. Observer
450,752 focused Explorer and closed it, not text. Use actual text650,752
for reserved guest46 with unchanged candidate; raw images retained.

Guest46 fails52.910s: screenshot shows taskbar650 click minimized text instead
of raising it; again observer closed Explorer, no second app exit. This is UI
toggle semantics, not new root/app failure. Paint-close snapshot proves exposed
text client strip at500,470. Freeze guests47..49<=600s and hosts113..118<=180s
for evidence-directed relaunch qualification;112 still unspent. Use exposed
client focus with visible Type glyph proof before selecting title close; keep
all43..46 failures and current media32, no candidate/build change.

Guest47 reaches both normal exits: slots6/7 empty, desktop/input unchanged.
Observer first Explorer taskbar click minimized the already active window;
paint icon click therefore had no launch target. Second taskbar click restored
Explorer and text launched as newslot6/gen19, slot7empty. Final all-role review
correctly fails; preserve snapshots. Use visible Explorer title500,30 for focus
instead of toggling taskbar for already reserved guest48. Same media32.

Guest48 collected complete79.093s proof: both normal reaps, Paint slot6/gen19,
Text slot7/gen20, original desktop/input15/16, stable10s. Final observer failed
because reused glyph oracle allowlists only abc/Type, not Move. Host113 extends
only explicit oracle allowlist to Move (same exact PSF/pixel matching) and
independently validates retained frames/processes/media/closure. Separate
relaunch-review.json passes; original failed result remains unchanged. Use
reserved guest49 for opposite launch order and actual new-text abc/300ms.

Guest49 passes78.975s: text then paint, new19/20, original15/16, real abc
within300ms in new text and10s stable. Guest48 separate replay proves paint
then text. Reserve visual media33 (copy verified signed media32,<=180s),
host114 package/hash review<=180s and VMware06<=180s unchanged launcher.
Fresh isolated folder20260926-app-relaunch; old package/sessions preserved.
Raw launcher observation success is not a recovery acceptance: independent
review must prove second READY after natural storage retirement before claiming it.
All final CB gates remain outstanding; visual package is development only.

VMware06 failed39.642s before any serial/VMX guest log; vmrun reports zero running VMs, no VMware process present. Preserve session6e1f545b47a1420982b60881f70b14ee and unchanged media. Freeze VMware07<=180s with identical candidate/launcher but host execution outside sandbox to test the actual interactive VMware start. No guest safety/time changes or acceptance inference.

VMware07 host execution reaches real READY then fails58.350s total/8.155s
after READY with DESKTOP_ADAPTER_ERROR -122. Compositor reap status122 used63,
not CPU256; replacement fails-32 stage4. Sessionea7e3c7e42ec465b964470a170ea3942
is closed, immutable media, failed. Root cause not yet attributed among input
queue/rate, channel queue or another quota. Do not raise quotas or speculate.
Reserve host116<=180s, build57<=300s, media34<=180s, VMware08<=180s for bounded
Ring3 terminal diagnostic only in existing CB header/startup files: retain
pre-clear input counts, emit one additional<=64byte record with input phase,
rate state/count, pre-clear queues, channel phase and service phase. Existing
fail-closed cleanup/limits unchanged. New image requires proof after correction.

VMware08 finishes170.489s unchanged media/closed, one READY, no adapter error;
independent recovery review remains false because no second READY. Host117
actual input-failure receipt/scrub passes O0/O2. Freeze VMware09<=180s with
existing guarded801-event/15s helper invoked immediately after READY, using
correct unique window title and actual host execution (prior helpers ran in
sandbox). No clicks without foreground/exact1024x768 guest identification and
verified pointer delivery; abort on failed guards. Same build57/media34, new
isolated input-diagnostic folder. Host118 prepares this identical-media variant.


## User priority2026-09-26: actual VGA text shell at boot

Explicit correction: "man muss bei booten die vga text shell sehen um fehler
zu sehen." Preserve CB candidate and stop further visual retries while defining
this prerequisite. Snapshot before-native-vga-console01/candidate.zip contains
all30 attributed candidate files; original worktree/evidence remain untouched.
VMware09 failed before READY: input5/gen16 exits71, channel EPIPE, diagnostic
input phase1/rate.failed0/used11/queues0, channel phase2/service phase1. Mouse
helper was never reached. Session84f969c36c9540fbac13e95110e52902 failed100.250s;
VMware log records exit and vmrun list confirms zero running VMs. Do not label
this as the same -122 reproduction or a passing mouse test.

Inventory: stage2_bios.asm sets mode03 initially and prints BIOS verification
in VGA. Its USE_FRAMEBUFFER branch at the final kernel jump switches to VBE.
Full-desktop media explicitly defines USE_FRAMEBUFFER=1. native_console.inc
READ/WRITE mediate only initialized COM1; console.c/shell_platform.c use those
calls. Native64 boot_framebuffer_parse accepts only active32-bit direct-colour
framebuffers; merely removing the boot selector disables the current display
backend and does not create visible shell output. The existing runtime VBE
thunk is BITS32 (arch/x86/boot/vbe_runtime.asm), not a native64 implementation.

Proposed separate native VGA console prerequisite, requiring package-rule4
scope and new fixed VGA-cell authority approval before source changes:
- Default boot remains VGA mode03,80x25. BIOS errors remain visible; a bounded
  early/fatal status sink reports fixed native boot errors before Ring3 starts.
- The ordinary Ring3 /bin/shell.prg is the command interpreter. A supervised
  Ring3 console service owns text layout/scrolling and existing PS/2 input via
  generation-scoped mediation. No parser, font renderer or general driver in
  Ring0; kernel additions only validate/fence fixed VGA text-cell transfers and
  the minimal early/fatal status record. No raw user MMIO/PIO, DMA, network or
  file-write authority. Use existing task/CPU/storage bounds; no larger pools.
- Keep COM1 diagnostics in parallel. A failed app/GUI start must leave a visible
  diagnostic and usable text shell. Starting graphics and restoring text need
  an explicit validated native64 display-owner/mode handoff; do not pretend the
  existing32-bit BIOS thunk supplies that proof. Keep this transition explicit
  in the prerequisite design; no finished-OS claim from text-only boot.
- Relevant new scope: native64 console/terminal/display mediation and its host
  tests; SDK console and shell output integration; a Ring3 VGA console service;
  native boot/build/media selectors; a separate console verifier and contract.
  Exact paths/opcodes and unchanged resource proof must be frozen after the
  authority decision and focused inventory, before implementation. Do not mix
  unverified VGA code into CB. Preserve/archive CB and perform a clean separate
  prerequisite transaction, then restore CB with hashes checked.
- Required evidence: actual VGA cells at boot and shell prompt; real PS/2
  command/unknown-command error; bounded console crash/hang/fence/recreation;
  stale-owner rejection; early boot error visibility; desktop/text handoff only
  after its own runtime proof. Existing CB five gates/eight cases stay open.

This proposal requests scope/authority only; it does not authorize relaxed
acceptance, unrestricted video registers or an in-kernel graphics driver.


## Resume after CK c5aa5fb9, QEMU-only development window

CK is accepted only for QEMU under the explicitly approved allocation; actual
VMware healthy/fault acceptance remains a mandatory final platform milestone.
CB is the sole active package. A clean main worktree was confirmed after CK.
All prior CB host/build/media/guest counters and failures remain spent.
Latest candidate archive before-native-vga-console02/candidate.zip SHA256
c3017dca8ad1e368f9876bd72c23dd404e5990d2129727156cdc293da080da77
contains26 implementation files plus4 historical docs/queue files. Restore
implementation only; keep current docs/queue and accepted CJ/CK changes.

Read-only merge inventory01 failed before worktree changes because its harness
incorrectly allowed at most3 git merge-file conflicts. Inventory02 records
26 candidate files; Makefile has1 conflict and boot-program builder7. Merge
append-only selectors/LTO/symbol preservation explicitly; never overwrite
accepted VGA/mode mechanisms. Remaining candidate files merge without conflicts.
All26 implementation paths are already within CB allowed_files. No new authority.

Freeze restoration and first integration window: one restored-candidate host119
<=180s; host120<=180s after evidence-directed integration; build58<=300s,
media35<=180s and QEMU guest50<=180s only after host success. Stop each failed
operation, retain receipt and inventory cause before any new attempt. No VMware
launch/focus. Source restoration is not acceptance or a desktop boot claim.
First restore and check existing services/client/display/entry regressions.
Then inventory the actual handoff: VGA owner4 retires before desktop4/input5;
Ring3 mode policy uses existing device34, input/display roles and original
quotas. Freeze any additionally required path before editing it. Kernel files
are outside this CB package; no kernel shortcut or new permission domain.
Original CB five gates/eight fresh cases and300ms input boundaries remain.

Host119 restoration passes16 tests25.956s. Freeze integration within the
existing CB files: selected FullDesktop+VideoMode composes Ring3 desktop/input
with CK kernel mode mediation; only Make kernel defines suppress the obsolete
boot-framebuffer branch, preserving DISPLAY_INFO. No kernel source edit.
Ring3 input driver links existing native_mode.c policy, enters mode after PS/2
self-test and refreshes existing1000ms kernel health every250ms. Root binds
input/mode for exact driver5, waits absolute2000ms before display binding,
fences mode during common retirement, and restores VGA only on final return
(not between automatic GUI restarts). GUI capture/start failure also restores
VGA within2000ms. Keep original desktop quotas/roles/service/restart policy.
Boot media stays mode03; QEMU observer explicitly selects VMware SVGA hardware.
Use reserved host120/build58/media35/QEMU50; no extra package or source scope.

Host120 passes16 tests32.772s. Build58 stops before guest build on missing
Namespace.desktop_cpu: archived CB removed the accepted selector/guard, while
the merged signature retained it. Restore both accepted parser and validation
unchanged. Add actual CLI/admission regression; reserve targeted host121<=180s
and build59<=300s. Media35/guest50 remain unspent. Capture now explicitly selects
VMware SVGA in headless QEMU; no VMware host launch or guest-limit change.

Host121 selector regression passes. Build59 compiles the full selected roles
but root link exceeds the existing0x440000 image ceiling: end0x444fa0.
Map identifies embedded VGA16736bytes plus block16736bytes and filesystem106848.
Keep admission/stack/resource limits. Selected root may place compact immutable
VGA+block ELF bytes in the already admitted RNPGv2 slots0..6 (0x400000..0x407000),
read-only/NX, separate ordinary ELF PT_LOAD. Code remains0x410000 upward;
guard/stack slots7..15 and the64-slot total remain unchanged. Existing compact_elf
preserves exact prepared bytes/rights/entry; sizes12757+12320 fit the28KiB region.
Filesystem image and emitted dependency PRGs remain byte-identical. Generate
selected linker script from existing wide script; assert low/high bounds.
No kernel source/parser change or mapping-capacity increase. Reserve targeted
host122<=180s and build60<=300s; original media35/guest50 still unspent.

Build60 and signed media35 pass. Guest50 fails26.377s before GUI startup:
block driver2/gen6 exits256 (CPU budget), filesystem is reaped, text shell
survives; media unchanged and guest closed. Storage PRGs and actual desktop
ELF are byte-identical to old successful build57. New VGA role still runs
while the first393672-byte desktop image is captured; retirement currently
occurs too late, only after file_finish. Move the already required VGA
retirement before that capture, restore it on capture failure, and compare
with the same bounded diagnostic. No quota/timing/driver change. Reserve
build61<=300s/media36<=180s/QEMU51<=180s. Preserve50 as failed; no unchanged retry.

Build61/media36 pass; guest51 fails48.388s at DESKTOP_START_STAGE2 with
-13 after all four image captures. VGA retirement before initial capture
removes the observed storage CPU exit in this run. Guest/media cleanup passes.
Inventory finds family_profile_admit64 permits terminal bit127 plus device
bit113 only under REIST_NATIVE_DISPLAY; CK native mode selects its separate
display path without that macro. Full desktop requires both already approved
rights. Reserve one read-only host123<=180s executing the actual admission
assembly under legacy-display/native-mode/terminal-only selectors. No further
guest or kernel edit before resolving the additional source scope.

## Proposed native-mode terminal profile composition (after guest51)

Host123 executes the unchanged production family_profile_admit64 assembly at
O0/O2 under three selectors. Exact terminal+device profile returns1 under
REIST_NATIVE_DISPLAY, -13 under REIST_NATIVE_VIDEO_MODE, and -13 in plain
terminal-only mode. This reproduces the stage2 guest rejection without QEMU.
Evidence: resume-after-ck02/admission-diagnostic.py and host123.json/log;
assembly/build/run logs retained under r83p-retirement/CB_ADMISSION-*.

Additional source requiring explicit scope decision:
arch/x86_64/proc/task_family.inc, only family_profile_admit64 terminal branch.
Permit its existing DISPLAY combination when VIDEO_MODE is selected too,
using the identical mask check. Native mode already mediates resources30/34;
this fixes composition of existing approved desktop terminal/device rights.
Do not set global DISPLAY (that duplicates input/display includes), drop the
terminal ownership checks, add syscall bits, change attenuation, quotas,
resource ownership or device operations. No driver policy moves to Ring0.
All other kernel code is excluded. CB remains the sole active package.

On approval: append this one source to CB allowed_files before editing; add
actual assembly regression in existing allowed test/test_x86_64_full_desktop.py.
Cover terminal-only and legacy display controls, exact native-mode combination,
missing terminal bits, unrelated mask bits, unchanged input records and parent
attenuation. Reserve targeted host124<=180s, selected build62<=300s, signed
media37<=180s, headless QEMU52<=180s after host success. Guest must reach actual
desktop READY and exercise real mouse/keyboard; failure remains failure.
Existing CB frozen gates, crash/hang/restart and300ms acceptance remain required.
No VMware launch. No kernel change has been made for this proposal.

User renewed mach weiter immediately after the concrete additional-kernel-file
question approves only the proposed family_profile_admit64 correction. Added
that source to CB allowed_files before implementation. Host124 includes the
pre-fix negative witness and post-fix regression within180s each phase; all
other reserved operations/limits unchanged.

Host124-before reproduces expected native-mode denial. Host124-after stops
at assembly: NASM does not accept ifdefined; no build/media/guest consumed.
Use supported ifdef/elifdef with the identical three-instruction mask check.
Reserve host125<=180s; build62/media37/guest52 remain unspent.

Host125 passes actual admission/attenuation O0/O2 including legacy controls.
Build62/media37 pass; guest52 fails38.609s in initial capture with storage
CPU exit256, before GUI creation. VGA retires71; root shell survives; media
unchanged and VM closed. Earlier51 alone did not prove storage issue fixed.
Inventory also identifies the same DISPLAY-only combined-profile checks in
native_terminal.inc (root/child plan and live-child validation). Reserve
read-only host126<=180s to execute existing terminal plan and decode saved
CPU trace; no further source/kernel edits or guest retries.

## Proposed matching terminal handoff correction after host126

Actual unchanged native_terminal_plan64 under O0/O2 accepts the existing
terminal+device profile under DISPLAY (0), rejects it under VIDEO_MODE (-13),
without modifying proposal on rejection. Host126 proves this separately from
guest52, which failed earlier in storage and does not prove terminal behavior.
Native terminal service op6 calls this same plan for desktop takeover.

Additional source requested: arch/x86_64/proc/native_terminal.inc, only its
three DISPLAY profile-combination checks: root-to-child ownership plan, child
check/release plan, live-child profile validation. Mirror the accepted legacy
mask treatment for VIDEO_MODE, as in the now tested task_family.inc correction.
Retain all owner/generation/liveness checks, terminal bit coupling, denial of
unrelated bits, quotas and unchanged other modes. No terminal-service-core,
scheduler, device driver or other kernel source changes. Existing CB scope
otherwise unchanged. Explicit AGENTS rule4 scope decision required before edit.

On approval freeze targeted host127<=180s for actual O0/O2 ownership plan and
live-child checks, including stale identity/foreign parent/unrelated rights
and no publication on denial, plus unchanged terminal-only/display controls.
Reproduce native-mode failure before correction, preserve that witness.
No new guest reservation here: first diagnose retained storage CPU exhaustion.
Raw guest50/52 trace confirms slot2/gen6 exhausts32-sample periodic budget;
guest51 succeeding does not establish that VGA retirement fixed this.
cpu-readonly-analysis.json preserves decoded records; trace ring has only
last256 records plus exhaustion record, so no claim of complete history.
No quota increase or unchanged retry is authorized by this correction.

Final scope audit catches queue-edit anchor matching active_id instead of the
CB package id; the approved source was accidentally appended to CK. Corrected
anchor to exact package line, removed accidental CK addition, revalidated
one active CB and complete changed-file set. User-approved source scope is
unchanged; no CK implementation/acceptance changed. Preserve this audit failure.

Renewed user mach weiter after the concrete native_terminal.inc question
approves the three-check counterpart correction. CB scope updated using exact
package-id anchor before edits. Host127 before/after phases <=180s each.

Host127-before reproduces denial; after passes actual ownership plans and
live-child validation at O0/O2 for native/legacy/plain modes and negative
identity/profile cases. Additional observer inventory finds guests50..52
incorrectly combine -vga vmware with legacy -device VGA,vgamem_mb=16, unlike
accepted CK single-adapter setup. Remove only that inherited duplicate device
in full-desktop observer, assert expected legacy argument before replacement.
Do not change storage pacing/quotas on this unproven hypothesis. Reserve
host128<=180s for actual argument regression, build63<=300s/media38<=180s
and QEMU53<=180s with corrected hardware composition and terminal fix.

Guest53 fails29.604s at initial capture, same storage CPU exit256 despite
single SVGA adapter. VGA retirement succeeds normally; no GUI reached.
Keep that corrected hardware setup. Existing root session_fs_send spaces
full-desktop FS requests by10ms versus40ms for network composition. Reuse
the established40ms root request spacing for selected FullDesktop to reduce
request pressure on unchanged32-sample storage workers. This is bounded sleep,
not larger CPU/device quotas; recheck remaining absolute deadline before send.
All request counts/deadlines and120000ms capture limit unchanged. Actual
large capture timing remains a guest gate; no claim from static arithmetic.
Freeze host129 before/after<=180s for actual send function with clock/transport
stubs (plain/full/network, deadlines and sleep failures), build64<=300s,
media39<=180s and QEMU54<=180s. No storage-driver/kernel edit or retry unchanged.

Host129 passes O0/O2 plain/full/network pacing and deadline/error checks.
Build64/media39 pass. Guest54 passes159.852s: actual1024x768 desktop READY,
mouse/keyboard pixel changes,10s stable, closed guest and unchanged media.
Reviewed real screenshots: explorer and application windows visible. This
coarse keyboard check does not prove text abc or300ms exact response. Preserve
raw PPMs; lossless PNG conversion uses standard-library zlib after PIL absent.

Next diagnostic uses the SAME signed media39, no rebuild. Extend observer with
explicit --return-to-shell after --exercise: ordinary Start menu/Desktop beenden
clicks, DESKTOP_EXIT_OK and shell prompt, physical VGA text cells at0xb8000.
Reserve guest55<=240s (observer230s leaves cleanup); startup54 used159.852s
including input/stability, so allow room for explicit return and snapshots.
No guest deadlines, quotas, final300ms gates or hardware permissions changed.
Source compile/scope check before launch; no unchanged retry or VMware start.

Guest55 fails175.075s after successful startup/input/stability: Start-button
click triggers client6/gen18 exit71, then DESKTOP_ADAPTER_ERROR -11. No
DESKTOP_EXIT_OK or exit-menu snapshot, so this is NOT expected shutdown.
Raw image shows partial menu repaint. Media unchanged/guest closed.
Reserve bounded client-failure diagnostic in existing allowed native_client.c:
selected role-v2 only emits one <=64-byte site/error record before the same
exit71 at receive, repaint and heartbeat failure. No fallback/retry/limits
changed. Host130<=180s preserves disabled client bytes; build65<=300s,
media40<=180s, guest56<=240s (230s observer) repeats the concrete failing
menu path with added evidence. Old failure remains failed; not acceptance.

Host130 disabled client bytes pass1.990s. Build65/media40 pass. Guest56
fails157.565s at old keyboard pixel inequality, before the menu probe; no
client failure marker. Inspection shows Paint initially covers Text; printable
keys do not render in Paint. Therefore old pixel inequality was not a valid
text oracle (earlier pass54 remains diagnostic only, never300ms evidence).
Correct observer: explicitly focus Text via its taskbar button, verify Type
glyph, inject abc, require existing independent keyboard_glyphs oracle within
the same300ms wait, then test normal menu exit. Preserve role-loss guard.
Same media40; reserve guest57<=240s/observer230s. No rebuild/source workaround,
quota change or weaker gate. New focus steps and actual glyph oracle explain
the changed diagnostic; guest56 remains failed.

Guest57 fails147.844s during text taskbar focus: client6 exits71, compositor
-11, then other roles retire and root exits5; fresh text shell is recreated.
No CLIENT_FAILURE serial record because existing client profile excludes WRITE20.
Do not add console rights. Reserve read-only denial observer for guest58 on
identical media40: one hardware breakpoint at process_run_syscall64.denied,
attached only after pointer snapshot, <=32 hits, capture only client6/7 WRITE20
buffer<=64 bytes while task address space is current. Bind original/compacted
loaded bytes with existing observer audit. No register/memory modification,
no new guest rights. Save adapted observer source/hash. Guest58<=240s with
230s observer; not a pass/retry claim, solely evidence for the failed call.

Guest58 fails147.639s; debugger captures no client WRITE denial. Instead
input5 exits110 after attachment, frontend-32. Observer closes cleanly but
this timing-perturbed failure cannot diagnose original client71. Preserve it.
Replace ineffective client WRITE with a selected-role-v2 diagnostic exit
encoding: low byte71 remains original failure, bits24..30 site1..5, bits8..23
absolute errno. Kernel already records32-bit exit status before reaping; no
new syscall/authority, logging, debugger pause or recovery fallback. Only
fatal diagnostic paths change; unselected binary bytes must stay exact.
This diagnostic encoding must be removed before final qualification. Extend
sites to invalid input serial/reserved and pointer bounds. Reserve host131
<=180s (disabled projection), build66<=300s/media41<=180s/guest59<=240s using
existing focused-text/menu observer without GDB. No retry of unchanged setup.

Guest59 fails146.006s without debugger. Encoded client6 exit0x01002047
proves receive site1 errno32 (EPIPE), original low byte71. Compositor reports
-11 and closes the channel, so client failure is downstream. Inventory finds
poll_client consumes/applies a request before nonblocking send_response;
EAGAIN is returned as fatal by poll_clients, closing a healthy client.
Reserve host132<=180s to execute actual poll_client with full reply queue,
verify consumed/dispatched request and lost response, O0/O2. No Runtime source
edit: desktop_surface_runtime.c/.h are outside current CB allowed_files.

Host132 stops before compilation because omitted explicit Zig caches select
a nonwritable host directory. No source result. Reserve host133<=180s with
both Zig caches in the existing workspace build directory, same host witness.

Host133 link retains unrelated exported runtime functions under COFF despite
section-GC flags; missing host stubs stop it. No runtime claim. Host134<=180s
extracts unchanged production clear/send/poll_client functions with actual
header, stubs unused applet branches, and isolates only the reply-pressure
witness. Extraction and all failed logs retained; no production edits.

## Proposed bounded Surface reply retention after host134

Host134 executes unchanged production poll_client/send_response O0/O2. A valid
request is consumed and dispatched once, reply send returns-11 (EAGAIN), next
poll sees no request and never resends the reply: first=-11,second=0,received=2,
dispatched=1,sent=1. Production poll_clients treats that-11 as fatal, closes
the channel and revokes the client. This matches guest59 client EPIPE and
frontend-11. All evidence is retained in resume-after-ck02. Temporary selected
client exit encoding is now removed from source; diagnostic binaries remain.

Requested additional CB source scope (not yet edited):
- userspace/gui/compositor/desktop_surface_runtime.c
- userspace/gui/compositor/desktop_surface_runtime.h
Earlier runtime-file approval covered input drain rounds; this new correction
adds bounded reply retention and explicitly requires this scope decision.

For selected FullDesktop only, retain at most one already produced Surface
reply per client when nonblocking send returns EAGAIN. Flush it before consuming
another request or delivering later input on that client; keep other clients
progressing within existing16 fair drain rounds and IPC queue capacities.
Never redispatch the consumed request or repeat its side effects. Use a fixed
absolute deadline at most the existing500ms client response timeout, never
extended by retries. On expiry, peer loss or invalid identity use existing
isolate/revoke/retire path. Scrub pending bytes on revoke/rebind/cleanup so no
old generation can receive a reply. Keep existing zero-timeout syscalls; no
busy wait, blocking UI send, larger IPC/CPU quota, heap ceiling or Ring0 change.
Private fixed struct space must fit the existing compositor workspace/heap
bounds, measured in the selected build. Old profiles retain exact code/layout.

Tests in already allowed CB host files: immediate send; EAGAIN then success
with exact one dispatch/one reply and FIFO; repeated EAGAIN/deadline; peer loss;
revocation/rebind/stale generation; fairness for other client and no old reply
after reuse; actual queue-pressure regression at O0/O2. Include default layout
projection. Freeze hosts135/136<=180s each, build67<=300s/media42<=180s, and
QEMU60/61<=240s each (230s observer) for real focused abc300ms plus Start-menu
exit/VGA return and app close/relaunch respectively. Stop first failure,
retain evidence, no unchanged retry. These are development diagnostics; original
CB five gates/eight cases and final VMware milestone remain mandatory.
No implementation of this additional source scope before explicit decision.

User mach weiter after concrete two-file question approves the reply-retention
scope. Added both exact runtime paths to CB allowed_files before implementation.
Host135 before/after phases <=180s each; remaining reserved operations unchanged.

Host135 before fails as expected, after passes; host136 both pressure/FIFO and
disabled object projection pass. Build67/media42 pass. Guest60 fails101.296s
during focus, client6 exit71/frontend-11; closed, media hashes unchanged.
Reply retention alone does not close the real failure. Preserve guest61 for
relaunch after positive input proof. Reserve temporary selected Ring3 error-site
diagnostics in already allowed runtime.c/native_client.c, build68<=300s,
media43<=180s, guest62<=240s (230s observer), host137<=180s review. Only failure
paths emit fixed bounded diagnostics or encode diagnostic exit status. Remove
these probes before acceptance; no unchanged retry or safety-limit change.

Build68/media43 pass. Guest62 fails107.617s: client receive EPIPE again,
no Surface failure-site record, adapter-11. This rules out asserting reply
retention as the complete fix. Reserve build69<=300s/media44<=180s/guest63<=240s
for a raw bounded first platform-failure caller-address record in already
allowed desktop_platform.c; bypass only failed logging adapter, not authority.
Remove all temporary probes after capture. Original gates unchanged.

Guest63 retains receive EPIPE and first platform failure caller0x45c36e,
resolved by exact build69 map to platform_pump. Inventory identifies another
concrete integration defect: native_video_reserve64 returns EAGAIN before
framebuffer writes when SVGA FIFO is full; display_pump permanently latches it.
Freeze correction within already allowed desktop_display.c and display host
test files: FullDesktop-only retain existing dirty tile on EAGAIN, first-failure
absolute100ms deadline, at most one retry per10ms, return to caller between
attempts; no extra queue, quota, syscall loop or renewed deadline. Other errors
remain fatal, detach scrubs state, unselected behavior unchanged. Host137 before/
after<=180s each, host138<=180s selected+default tests, build70<=300s, media45
<=180s, guest64<=240s focused input/return. Guest diagnosis will determine if
this closes the observed failure; no root-cause certainty from inventory alone.

Host137-before compile fails duplicate local next in new host test, no runtime
claim. Rename duplicate; host139 before/after<=180s each replaces this spent
host slot, logs retained. No acceptance change.

Guest64 fails116.988s with adapter-110 instead of-11 after bounded pressure
handling. Upstream QEMU hw/display/vmware_vga.c vmsvga_fifo_length explicitly
requires fifo_max>=fifo_min+10KiB; our kernel selects MAX4096. Installed QEMU
reports11.1.0 v11.1.0-12130-ge470268ff4; exact upstream commit URL unavailable,
so upstream reading is not claimed as binary identity. Reserve guest65<=240s
with same media45 but changed read-only observer: capture existing FIFO PTE
and physical first4KiB at stopped snapshots to verify NEXT/STOP progression
on this installed executable. No kernel edits.

Temporary runtime/client/platform error probes removed from candidate source;
diagnostic builds68..70 retained. Tightened retry syscall deadline to original
pressure deadline (not now+100), added selected display regression to frozen
full desktop host suite. Reserve host140<=180s for reply pressure/default
projection and selected display pressure after cleanup; no new guest build
until kernel FIFO scope/resource decision.

## Proposed native SVGA FIFO capacity correction (approval required)

Reference: QEMU upstream hw/display/vmware_vga.c, vmsvga_fifo_length,
https://github.com/qemu/qemu/blob/master/hw/display/vmware_vga.c . It rejects
FIFO_MAX < FIFO_MIN+10KiB. Existing native configuration sets MAX4096 and maps
only one kernel-only FIFO page. Full-screen raster exceeds that unconsumed
ring after roughly203 commands; CK small-update proof did not exercise sustained
FIFO consumption and is not evidence for the real desktop's steady operation.
Installed-binary read-only FIFO observation is guest65 (in progress at freeze).

Requested correction: fixed16KiB FIFO (four existing-table pages) within the
already validated64KiB QEMU or8MiB VMware PCI aperture. Validate MIN/MAX, header
size, alignment, NEXT/STOP and original UPDATE-only64x64 rectangle bounds before
effects; keep last guard dword, nonblocking reserve, fixed mapping/cleanup,
mirrored state validation, generation revocation and fail-closed VGA recovery.
No new user mapping, raw register/device/DMA right, CPU/IPC quota or polling loop.
This changes the previously frozen device-buffer capacity and kernel source
scope, so existing in-scope continuation authority alone is insufficient.

Exact proposed prerequisite source/test scope:
- arch/x86_64/video/video_mode.c: fixed-capacity admission, four-leaf mapping,
  configuration and full cleanup using the existing FIFO page table.
- arch/x86_64/video/video_mode.h: shared fixed FIFO byte constant if needed.
- test/x86_64_video_mode_host.c and test/test_x86_64_video_mode.py:
  minimum usable capacity, wrap, pressure, corruption and guarded storage tests.
- scripts/run_qemu_x86_64_video_mode.py and scripts/verify_x86_64_video_mode.py:
  exact four-leaf proof and bounded repeated UPDATE consumption; healthy, driver
  crash/hang and fenced VGA return on QEMU. Preserve every historical CK result
  and final VMware milestone. No launch of VMware without user availability.
- automation/reist-s03b.toml, this contract, NATIVE_VIDEO_MODE_CONTRACT.md and
  CURRENT_WORK.md: prerequisite scope, gates and complete evidence attribution.

After approval, preserve current unaccepted CB candidate in a hash-verified
archive before activating the separate cohesive kernel prerequisite; never
mix its implementation into an unverified CB commit. Freeze exact commands
and finite operation reservations before implementation, retain old failures.
Original CB five gates/eight guests, exact300ms input and final hardware proof
remain mandatory. The proposal itself does not authorize kernel edits.

Guest65 fails131.326s, closed and media unchanged. Actual installed-QEMU
FIFO headers (MIN,MAX,NEXT,STOP): desktop(16,4096,3856,16), pointer
(16,4096,3996,16). Thus192 then199 UPDATEs published without any consumption,
matching upstream minimum-size rejection. Failure snapshot(16,4096,16,16) is
after recovery reconfiguration; do not call it a full-ring snapshot. Raw proof
and hashes: resume-after-ck02/fifo-progress-review.json. Host140 all3 targeted
tests pass after diagnostic removal. Default display host138 passes; selected
pressure host139 before fails/after O0/O2 passes. All guests closed.
Kernel FIFO proposal remains unimplemented awaiting resource/scope approval.

User mach weiter after explicit16KiB/kernel question approves proposed scope
and fixed capacity extension. CB preserved in before-native-fifo01 candidate.zip
SHA256 e3726f53313ddb209f0f2a5dfe5e7eec64eb19fffcaeb4cb19a200d18041ccdf.
All35 changed files individually hashed; tracked base restored and clean before
CL definition. CL prerequisite active; CB queued, all evidence/limits retained.
