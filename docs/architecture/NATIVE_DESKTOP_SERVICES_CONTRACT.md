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
