# Native64 VGA text console prerequisite (CJ)

## Authority and transaction

2026-09-26 user "mach weiter" directly answers the concrete VGA-console
scope/authority request and authorizes that proposal. Default boot must show
actual VGA mode03 text and the ordinary Ring3 shell. Preserve the original
full desktop objective and all CB gates. CB candidate30 files archived and
verified: before-native-vga-console02/candidate.zip SHA256
c3017dca8ad1e368f9876bd72c23dd404e5990d2129727156cdc293da080da77.
Only attributed, byte-verified code was restored to898f30d5; histories remain.
Exactly one implementation package: CJ. CB remains queued/unaccepted.

CJ is the complete VGA console/keyboard/shell/recovery vertical slice. Native64
text-to-graphics and graphics-to-text hardware transition follows as a distinct
hardware acceptance boundary before restored CB desktop integration. The
existing BITS32 BIOS thunk is not native64 evidence. No finished-OS claim or
permanent abandonment of the required desktop transition is permitted.

## Frozen architecture

References: IBM-compatible VGA mode03,80 columns/25 rows, two-byte character/
attribute cells at physical0xb8000; existing PS/2 set1 decoder and existing
terminal foreground ownership; ASCII control characters and explicit bounded
ECMA-48 subset in Ring3. No claim of unrestricted VT compatibility. Private
REIST VGA mediation v1 uses fixed64-byte requests on appended DEVICE_CONTROL
resource33; existing resources30/31/32 and syscall numbers retain meaning.

Ring0 implements only generation/parent/profile/range admission, fixed cell
copies (<=80 cells/request), bounded byte transport (2048 output bytes/64 input
bytes), fencing and a bounded early/fatal status line. VGA's one4KiB mapping
is supervisor-only, writable/NX, cache-disabled, checked before access. No
raw user MMIO/PIO/DMA, font renderer, escape parser or scroll policy in Ring0.
Boot selects text mode03; unsupported/non-text handoff fails closed.
Early/fatal diagnostics write at most80 fixed message bytes to a reserved line;
ordinary running text rendering belongs to the separate Ring3 console process.

The console process owns a fixed2000-cell shadow, parser state and existing
bounded PS/2 initialization/decoding. No heap, file or network authority. Root
spawns it while storage slots2/3 are live, placing it in existing free slot4;
thereafter storage may retire/recreate independently. Existing <=32 CPU samples
per1000ms and task/image/heap/restart bounds apply. No task/pool/quota increase.
Ordinary shell remains root0; existing foreground authorization precedes any
console READ/WRITE mediation. COM1 remains available alongside visible output.

VGA v1 operations: bind1/revoke2/query3/read-output4/write-input5/write-cells6/
heartbeat7/status8. Bind/revoke/status require the controlling direct parent;
service operations require exact live owner/epoch. Query grants no authority.
All reserved fields/sizes/pointers/counts/ranges are checked before side effects.
Bind requires old owner reaped; stale generations never regain access. Root or
service death fences both queues and VGA access; existing PS/2 fencing remains.
Revoke is idempotent. No byte truncation/overwrite when queues fill: return
EAGAIN before effects and retain caller deadlines. Fixed staging is scrubbed.
One service health deadline1000ms, root checks <=250ms apart; initial self-test
and recreation share an absolute2000ms end. Existing restart budget is spent,
never reset. Exhaustion leaves a visible bounded failure status and serial
rescue access. No endless retry or unverified recovery.

## Scope

The active queue's allowed_files is authoritative: native64 entry/scheduler/
console/dispatch/family hooks; new VGA core/adapter/header and Ring3 service;
SDK shell integration; explicit build/media selectors; actual behavior tests;
console package/runtime verifier and this documentation. Unselected builds
must remain byte-identical. No edits to the archived CB source to disguise
prerequisite work. Restore CB only after accepted CJ and required handoff.

## Frozen gates (once per qualification, first failure stops)

1. python test/test_x86_64_vga_console.py -v (180s): actual core/renderer at
   O0/O2; denied pointers/parent/generation/range, saturation before effects,
   exact cell text/scroll/control handling, idempotent revoke, old-owner denial.
2. python scripts/verify_x86_64_vga_console.py --defaults (300s): complete
   disabled source/artifact comparison against898f30d5; accepted dependencies
   remain bound by exact provenance, without repeating unchanged guest matrices.
3. python scripts/verify_x86_64_vga_console.py --package (600s): no undefined
   imports, signed text BIOS media, fixed image/stack/CPU bounds, both shell
   installation layouts and exact allowed-file review.
4. python scripts/verify_x86_64_vga_console.py --runtime (2400s): three fresh
   bounded QEMU cases<=600s each, <=1800s aggregate: ordinary shell plus PS/2
   command/error/VGA cells; console crash/stale owner and reintegration;
   console hang/restart-budget exhaustion/visible failure. Include injected
   early boot error visibility and serial parity. No synthetic shell substitute.
5. python scripts/verify_x86_64_vga_console.py --review (600s): independent raw
   replay/cell bytes, actual owners/resources/cleanup, source/tool/image binding.
   Bounded VMware text-shell visual proof<=180s also required before delivery.

Development reservation: hosts01..12<=180s, builds01..03<=300s,
media01..03<=180s, QEMU01..04<=300s and VMware01<=180s. Preserve each failure.
New evidence-directed finite reservations follow AGENTS without routine
reauthorization; all frozen gates and per-operation limits remain unchanged.

## Development evidence 2026-09-26 (not acceptance)

Contract baseline01106c77. hosts01 absent implementation (expected red),02
assert/NDEBUG compilation failure retained,03 renderer O0/O2 pass,04 actual
core/renderer O0/O2 pass,05 includes domain assembly/service compilation pass.
builds01..03 pass (13.025/13.046/13.108s). media01 fails floppy capacity;
media02/03 signed HDD/floppy checks pass after existing input-local-symbol
compaction, with every loaded byte unchanged. No media/runtime cap increased.
guest01 fails62.702s before shell; guest02 adds raw registers/stack and fails
8.896s: fault CR2=ffffffff80200030, native memory self-test. VGA boot check
clobbered the RAM page-table cursor EAX; build03 preserves it. guest03 passes
14.501s: actual mode03/80x25, ordinary shell, PS/2 HELP and unknown command,
visible VGA/UART error, live console slot4/gen5/epoch1, immutable media and stop.
All evidence: build/codex-agent/r83cj-vga; original hosts under
build/codex-agent/native-vmware-desktop/cj-hostNN.log. No frozen gate started.

Private mediation phase word is 0 starting,1 fenced,2 self-tested; first
heartbeat publishes readiness, STATUS returns EAGAIN while starting. A
separate serial CR/LF cannot clear the reserved error line. Ring3 implements
LF-to-CRLF output processing; ECMA48 cursor/erase/SGR subset has four bounded
parameters,999 maximum,32 parameter bytes. Reserved final row is never scrolled.

Next bounded work: VMware01 (already reserved <=180s), fault/recovery and
independent pointer/profile/source/cleanup proof. Reserve builds04..06<=300s,
media04..06<=180s and QEMU05..08<=300s for evidence-directed corrections and
fault observer integration; existing QEMU04 and hosts06..12 remain available.
All original five gates, crash/hang/exhaustion, early error injection, VMware
proof and subsequent text/graphics handoff remain mandatory. Do not infer
qualification or OS completion from the healthy guest03 diagnostic.

Fault qualifier: root-private four-qword witness (magic/version/mode/start count),
zero mode in every produced image. Observer may write mode1(first console UD2)
or2(all console generations sleep without heartbeat) only before the first root
GETPID. Supervisor passes the private one-byte0/u/h startup mode. Fault begins
500ms after successful self-test. Existing1000ms health,2000ms recreation,
restart/CPU/creation budgets and exact old-owner reap remain unchanged.

VMware01 stopped before any VM start: diagnostic helper resolved the repository
one parent too high (module import failed). Log retained. Correct that path;
reserve VMware02<=180s with the same fresh bundle, capture, media hash and
bounded-stop requirements. This is an observer correction, no unchanged retry.

VMware02 reaches the ordinary serial shell in10.237s; captureScreen requires
guest login and is unavailable without Tools, so visual proof fails13.307s.
VM stopped and media unchanged. Reserve VMware03<=180s: explicitly open the
owned Workstation window with the repository's existing vmware.exe -x method,
capture only its exact title through the existing host PrintWindow helper,
and retain20s observation/stop/hash requirements. No guest-login authority.

## Scope decision: ordinary file applications beside the console

Inventory after the real VGA-shell proof found an additional existing source
assumption: userspace/sdk/lib/x86_64/shell_app_files.inc line98 admits only
application slot4. The authorized console occupies slot4 while storage uses2/3;
an ordinary file application therefore imports into slot5 and the old check
would terminate the supervisor. The matching outer check in shell_session.c
is already within CJ scope. The broker/SDK file grants use generations, not a
fixed slot, and existing terminal mediation admits direct children2..7.

Proposed narrow scope addition: userspace/sdk/lib/x86_64/shell_app_files.inc.
Use one root-defined application-slot constant:5 only for NativeVgaConsole,
4 for unchanged profiles. Replace the existing exact-slot comparison in that
include and its already authorized outer shell check. Keep all existing
profile masks, manifest/digest binding, generation checks, task/CPU/heap and
restart limits. No extra slot allocation, dummy task, new authority or changed
default artifact. Prove actual CAT/LS resolution and terminal return through
the VGA shell, plus byte-identical unselected output. AGENTS package rule4
requires approval before editing this additional source file; it has not been
edited and is not yet added to allowed_files.


2026-09-26 explicit user approval: "Ja, zusaetzliche Datei fuer
VGA-Anwendungsstarts freigeben". The additional shell_app_files.inc path is
now authorized and included in CJ allowed_files. Implement only the proposed
slot selection, retaining all default-profile checks and artifacts.

Build06 passed13.145s with the sticky degraded-status correction; no media or
guest executed for that intermediate build. Freeze builds07..09<=300s each
for the approved application-slot integration and evidence-directed fixes.
Existing media06<=180s and guests07..08<=300s remain available. All prior
failures and spent counters remain; no frozen gate or runtime limit changes.

Host09 passes2.116s. Build07/media06 pass. Guest07 stops15.224s at CAT
output: snapshot guest tick2870 shows root/driver/FS blocked, no application
import yet and healthy console; the observer used an unconditional2s host
delay during real ELF capture. Preserve that negative evidence. Tighten the
observer to wait for actual next shell prompt, bounded20s per command within
the unchanged90s guest budget, before asserting complete output. Reserve
guests09..10<=300s each for this observer and any evidence-directed follow-up;
guests07/08 remain spent. No change to guest deadlines or acceptance limits.

Guest08 passes18.407s: three console generations, two restarts, fenced
exhaustion, sticky visible failure and working ordinary serial rescue. Guest09
passes22.857s: actual PS/2 CAT data.txt, LS, HELP and unknown command with VGA
and UART output and terminal return. Guest10 passes22.666s: console UD2,
old-owner reap, new generation/epoch, then the same ordinary applications.
All bind build07/media06; development evidence only, final gates unrun.

Reserve guest11<=300s for the required early-error observer: at the existing
x86_64_nx_resume rendezvous, redirect RIP to the existing fixed
physical_memory_state_error branch. Record both exact addresses and observe
its real VGA status, serial message and halt. This proves early error-branch
visibility, not physical-memory fault detection. No guest-byte modification.

Reserve VMware04<=180s for build07/media06 using the established exact-window
PrintWindow observer and a fresh -apps development bundle; verify media hashes
and bounded stop as in VMware03. The earlier proof binds build03 only.

Guest11 reaches the injected existing error branch and UART reports the real
PHYSICAL_MEMORY_ERROR text. Observer incorrectly expected the label-derived
PHYSICAL_MEMORY_STATE_ERROR; retain its bounded failure. Source inventory
confirms the literal in entry.asm1435. Correct only the observer literal and
stop marker; reserve guest12<=300s for that corrected visibility proof.

Final scope review identifies a remaining health-scheduling defect before
qualification: root polls console health only from getchar, while existing
file/application IPC and task waits can block1000ms. That cannot establish the
frozen <=250ms supervision requirement during commands. In the already
authorized shell_session.c and shell_vga_console.inc, split only the existing
1..1000ms selected-profile waits into <=100ms waits under the same absolute
deadline and finite11-attempt bound. Check health from the existing monotonic
clock adapter at100ms intervals; fence on expired health immediately, and
defer recreation to the ordinary safe shell boundary to avoid recursive FS
transactions. Default profiles and larger/invalid syscall inputs retain their
original path. Use remaining hosts10..12, builds08..09; reserve media07..08
<=180s and guests13..15<=300s for this evidence-directed correction. No
acceptance gate or operation/restart/CPU deadline is enlarged.

Guest12 early error-branch visibility passes10.320s on build07/media06.
VMware04 actual shell visible10.273s, but overall failed40.392s because
vmrun stop8s timed out. Follow-up20s also timed out. Exact PID26852/start
09:10:27 UTC bound to this VM's log; targeted Stop-Process succeeded, vmrun
list zero and original media hashes unchanged. Original failure retained;
no VMware04 full qualification claim. Host10 new wait harness failed local
Zig cache permissions; host11 failed function extraction matching a macro.
Fixed observer cache paths/anchored definition extraction. Host12 all three
tests pass2.708s, including actual selected wait/probe functions at O0/O2
for all1..1000ms deadlines, success, errors, deferred recovery and exclusion.

Build08/media07 and guests13/14/15 pass27.078/18.781/28.498s for ordinary
applications, hang/exhaustion and crash/reintegration respectively. Added raw
family/profile and four-level VGA page-table snapshots prove real ownership
and supervisor-only writable/NX/cache-disabled0xb8000 mapping. Build09 retains
exact build08 kernel/catalog/C-core bytes after restoring the old DISPLAY/INPUT
source guard nesting on the disabled path. integration-review01.json proves
seven exact disabled source projections against898f30d5 and10 raw live console
owner/parent/syscall-mask snapshots. This remains diagnostic evidence; complete
build-selector/default artifacts and all five frozen gates are still required.

## Qualification completion window (2026-09-26 continuation)

All existing edits are attributed CJ work on clean contract baseline01106c77;
no unrelated changes found. Reserve at most3 development host commands13..15
<=180s for the new independent replay/default-projection verifier. Frozen
qualification retains the five listed commands/limits, each once, stop on
first failure. Its defaults/package gates each include one bounded300s build;
package includes one180s media production. Runtime groups are healthy (normal
shell plus one separate early-error branch boot), crash and hang; each group
<=600s, aggregate<=1800s. All captures fresh, each existing90s observer bound.
One VMware proof<=180s belongs to review. After vmrun's bounded8s stop, an
optional exact PID/start-time match against the owned VM log may terminate
only that process; verify vmrun list and immutable media afterward. This is
the already authorized bounded cleanup, not a guest limit/acceptance waiver.
Old VMware04 remains failed. No extra implementation package or nested agent.

Host13 development audit passes: all10 complete disabled source/AST projections,
three independent historical raw replays,1656 source bindings and11 tools.
Host14 all4 targeted tests pass4.129s, including deliberate authority, cells,
page-permission and media-proof mutations rejected by independent replay.
Fresh qualification snapshots additionally record actual CPU budgets/windows;
review requires exact console generation,32 samples and100-tick period. Only
the explicitly named historical host mutation fixture omits those new fields;
all fresh runtime/review calls require them. Guest kernel bytes unchanged.
Qualification01 now freezes the implemented verifier and the five original
gates. No earlier diagnostic is being promoted to qualification.

Qualification01: gate1 passes4.029s; gate2 fails14.705s after a successful
disabled build because its new verifier incorrectly used old BC golden pins
for the kernel/root/catalog. All other nine immutable service/application/core
artifacts still match BC. Frozen requirement is898f30d5, not BC. Preserve all
qualification01 results. Build the exact898f30d5 Git archive once as an
unmodified verification fixture under ignored reference-898f30d5 (no Git
clone/worktree, branch or implementation edits). Reserve this reference build
<=300s; verify every source byte against the archive afterward. Defaults must
compare all objects/images/catalogs/layout metadata with that precise baseline,
plus all10 disabled source/AST projections. Freeze its archive/artifact/tool
hashes. Qualification02 will execute the same five gates once with original
limits and fresh runtime captures. No guest failure or limit change.

Reference archive build succeeds. Host15 compares91 artifacts: every delivery
ELF/PRG/catalog and86/91 files are byte-identical. Five intermediate objects
differ only in .debug_str and .rela.debug_info: LLVM interns the longer
reference-fixture compilation directory in a different string-table order.
No allocated section differs. Refine comparison to resolve only DWARF string
relocations and canonicalize the exact source-directory prefix; retain every
other section byte/header/symbol/relocation, and require all delivery artifacts
byte-identical. This corrects location metadata in a verification fixture, not
a guest/default behavior exception. Reserve host16<=180s for this comparator
and host17<=180s only if a concrete comparator defect is found.

Host16 passes: all91 baseline artifacts compared (86 byte-identical,5 with
only independently resolved DWARF compilation-directory differences), plus
all10 complete disabled-source projections. Added mutation regression ensures
normalization cannot hide changes to executable bytes or DWARF relocations.
Qualification02 includes this regression and otherwise retains the same five
commands, all deadlines and fresh guests. Reference source/archive untouched.

Qualification02 gates1..4 pass; all four physical QEMU boots replay correctly
(healthy21.020s, early9.575s, crash22.302s, hang14.468s), with exact CPU quotas.
Gate5 fails VMware cleanup39.073s after real shell10.329s and complete visual
capture: vmrun stop timed out and the PID command returned nonzero before a
final vmrun-list observation. Immediate follow-up finds zero VMs/no vmx
process and unchanged media. Preserve original failure. Cleanup must always
record the PID command output and check final VM absence, including the race
where the process exits between list and Get-Process. Exact PID/start checks
remain mandatory before any kill; no new termination authority or time cap.

Final source review also tightens the pending recovery deadline: health
detection during an active file command now records its absolute now+2000ms
end immediately. Deferring recreation to the safe shell boundary must not
renew that deadline. If the remaining time expires, retire/fence and degrade
without a late import. Add sticky-deadline regression to the actual host
health function. No larger operation/CPU/restart allowance. Qualification03
will rerun the same five gates and fresh guests once, with unchanged limits.

## User cursor correction (2026-09-26)

Qualification03 gates1..4 pass; review fails bounded VMware cleanup after
the real shell is visible (9.805s). Nested PowerShell cannot terminate the
owned vmware-vmx process (access denied). Preserve this failure and its raw
captures; host cleanup needs the interactive host execution context.

The user reports that the cursor stays on the old line. Inventory confirms
the renderer tracks row/column but never programs the mode03 hardware cursor.
Within the existing VGA device and listed CJ files, append operation9
SET_CURSOR to the private64-byte v1 request: buffer/count zero, offset0..1919,
same generation/epoch/profile and health checks. Only fixed color CRTC
registers0Eh/0Fh at ports3D4h/3D5h may be written (four bounded OUTs); no
caller-selected registers or raw port authority. VGA cursor-location register
semantics apply; the existing BIOS cursor shape remains unchanged. Ring3
publishes its logical position after the corresponding text row is painted.
No queue, CPU, restart or time limit changes. Regression covers bounds,
foreign/stale/fenced callers and renderer line wrapping/scrolling. Actual
guest screenshots must show the cursor at the latest prompt.

Reserve cursor development hosts18..20<=180s, build10<=300s, media08<=180s
and diagnostic guest16<=90s. Prior spent attempts stay spent; host17 remains
unused. Qualification04 is not started until the concrete cursor and host
cleanup corrections are ready; the original five gates remain mandatory.

Host18 all5 tests pass4.050s; build10/media08 succeed. Guest16 stops14.733s
because the pixel observer assumed unavailable Pillow; no guest failure.
Read the exact bounded QEMU P6 raster with the Python standard library.
Reserve guest17<=90s after this concrete observer correction, reusing exact
build10/media08. Qualification04 will retain all five original gates and
fresh guests, additionally requiring actual prompt-cursor raster evidence.
For VMware access-denied cleanup, emit an exact PID/start/vmx request and
allow at most35s for the interactive host tool to perform the already
authorized targeted termination. The verifier independently observes VM
absence and immutable media; original total180s limit remains mandatory.

Guest17 passes22.272s on unchanged build10/media08: actual PS/2 CAT, LS,
HELP/error with hardware underline at each latest prompt, including row
changes. Pixel oracle regression rejects a blank frame, old row, wrong
column and truncated raster; adapter rejects invalid cursor before OUT.
Freeze qualification04 now: same five commands/limits, fresh four physical
QEMU boots, added cursor evidence, bounded VMware host cleanup handoff.

Qualification04 gates1..3 pass. The healthy guest and cursor captures pass,
but independent replay fails because its new local integer row shadows the
result record used for elapsed time. Rename to cursor_row; guest/image bytes
unchanged. Preserve qualification04 failure. Host19<=180s exercises complete
fresh replay before qualification05, which retains
the original five commands/limits and fresh captures. No acceptance waiver.

Host19 complete qualification04 healthy/cursor replay passes; raw guest
elapsed23.040s. Add this full cursor path to the targeted regression so an
observer result-record collision cannot hide behind the historical fixture.

## Accepted qualification05

All five frozen gates pass:4.740/14.470/19.680/82.236/58.201s. Seven targeted
tests pass. Fresh healthy22.211s/early8.734s/crash25.833s/hang18.500s prove
the console, application slots, early errors, bounded recreation and restart
exhaustion. Cursor pixel evidence follows each current prompt. VMware actual
mode03 shell appears9.927s, cursor visually reviewed directly after C:\>;
complete53.352s proof includes stopped VM and unchanged media. Exact host
cleanup first refused a JSON-date-coercion mismatch without side effects;
literal PID30676/start2026-09-26T10:08:45 UTC revalidation completed the
owned-process cleanup. Verifier independently confirmed absence within180s.

Final diff review: appended operation9 only, no public syscall renumbering,
no raw port selection, bounded four CRTC writes after admission, fixed-row
publication, unchanged CPU/queues/health/restart limits, selected-only code.
All source/tool/contract bindings pass before documentation/queue transition.
Final receipt and manual acceptance seal under qualification05. CJ accepted;
CB deliberately remains queued until the separately required native64 mode
transition. No active implementation is selected across that genuine hardware
authority boundary. No complete-OS claim; all original desktop gates remain.
