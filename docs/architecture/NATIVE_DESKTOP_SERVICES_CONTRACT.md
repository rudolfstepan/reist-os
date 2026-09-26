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
