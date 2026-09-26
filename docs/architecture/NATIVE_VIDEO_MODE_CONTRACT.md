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

## Window01 observations

Inventory01 passes9.826s on unchanged CJ media with QEMU VMware SVGA:
PCI00:02.0,15ad:0405,IO BAR16bytes atc010h, framebuffer16MiB atfd000000h,
FIFO64KiB atfe000000h, complete QMP query-pci retained. Actual VMware host
log records SVGA-PCI BAR gfbSize134217728/fifoSize8388608. These two frozen
virtual platform apertures must match hypervisor identity, PCI types/bases,
E820 non-RAM validation and device register readback before mapping; other
virtual configurations fail closed. No BAR probing/configuration writes.

Host01 preliminary core passesO0/O2 (25.187s). Host02 correctly rejects the
FIFO wrap fixture:20 free bytes cannot fit a20-byte command plus the required
empty/full discriminator dword. Correct STOP32 to36, retain the failure;
no production bound change. Added idempotent-parent-fence sealing, sticky
deadline/quarantine, resource and actual Ring3 policy regressions before
next host invocation. No selected build/media/mode-changing guest yet.

Host03 passes2.960s: real core/resources/FIFO/policy atO0/O2 and freestanding
hardware-adapter compilation. Build01 kernel mechanism succeeds1404984bytes.
Build02 linked root exceeds the unchanged196608-byte image bound when two
separate terminal images are embedded. Preserve the failure; build one shared
terminal executable from the unchanged VGA source and selected mode source,
with an explicit argc dispatch, using the already approved common terminal
failure domain. Its two instances still have distinct generation/slot rights.
No new source file or image/heap/quota expansion. Reserve builds03..04<=300s
after this evidence-directed deduplication; original two media/four mode
guests and second inventory remain unspent. Root diagnostic observation ends
at original start deadline+4000ms; return remains a fresh recovery2000ms bound.

Build03 still exceeds the unchanged root image bound after shared-driver
deduplication (combined terminal ELF20832bytes). Use the existing root-only
LTO path already used by the DNS profile, selected additionally for CK.
Build04 is the remaining reserved build; default and CJ compilation untouched.

Build04 map shows root end440168h,360bytes beyond the unchanged440000h
limit. Root rodata5b58h requires six pages. Its terminal ELF20832bytes has
only16917 file-backed bytes; a zero-filesz PT_LOAD at offset20480 plus
optional section metadata retains an unnecessary final page. Apply standard
ELF omission of section headers and canonicalize only the zero-filesz file
offset, preserving alignment and every loaded byte/right/entry. Require
complete prepare() output equality and retain original terminal ELF.
Reserve build05<=300s after this concrete layout correction. No linker/image
bound changes, compression/parser feature, or new authority.

Build05 passes after standard ELF compaction. Media01 fails before any guest:
kernel1405160bytes leaves no FAT12 data sector with the fixed boot layout.
The existing objcopy proof already preserves every PT_LOAD byte/header and
all retained symbols. For CK only extend its removed local-debug prefixes to
native_video/native_vga/native_display/family/scheduler (<=768 names), retain
every global and process_run_syscall64.pid, and pass names via a bounded
symbol file to avoid Windows command-length limits. Inventory590 additional
locals saves about31648bytes without changing loaded code. Reserve build06
<=300s then remaining media02<=180s. No disk-format, loader or limit change.

Build06 passes;627 nonloaded local names removed with complete loaded-image
and retained-symbol equality, kernel1373544bytes. Media02 produces boot/data
images but its new checker retains the old five-file directory cap7 including
dot/dotdot. CK has the explicitly frozen sixth video.prg, so the exact cap is8.
Correct only the selected independent consumer (guest filesystem capacities
unchanged), reserve one media03<=180s on exact build06, then diagnostic01<=90s.
Earlier failed media receipts are retained unchanged.

Media03 catches a second six-file fixture error: sequential inode12..17
exceeds the existing16-inode table. Standard EXT2 first_ino is11 and its
record is unused; place only video.prg in inode11, preserving all original
file inode12..16 and the16-inode table/bitmap/1MiB disk geometry. Mirror the
exact mapping in the independent consumer. Reserve media04<=180s on unchanged
build06. No guest launched, filesystem format or runtime capacity changed.

Media04 passes. Diagnostic01 stops before launching QEMU because its inherited
data fixture still requires five files. Bind only the CK fixture to the selected
six-file producer, retaining the immutable-media verification and90s deadline.
Use reserved diagnostic02 on unchanged build06/media04; retain diagnostic01.

Diagnostic02 completes32.077s with healthy CAT/LS and responsive shell but no
graphics pixels. Renderer import is rejected before any new task exists:
its inherited terminal+device profile combination is disallowed in the
text-first profile. The probe requires only exit,GETPID,sleep,monotonic and
display device control. Attenuate it to these actual calls; do not broaden
kernel admission. Report actual start/return errors on COM1 for diagnosis.
Reserve build07<=300s and media05<=180s, then remaining diagnostic03<=90s.

Build07/media05 pass. Diagnostic03 completes32.102s; renderer now imports but
exits71 before drawing. Display QUERY returns existing EACCES(-13) between
hardware enable and parent binding; the bounded startup loop omitted that
documented pre-bind result. Admit it only during the unchanged2000ms startup
wait. Add numeric return-path failure diagnostics and retain the final snapshot
even when graphics evidence is missing. Reserve build08<=300s/media06<=180s,
then remaining diagnostic04<=90s. No permission or deadline change.

Build08/media06 pass. Diagnostic04 completes25.090s and identifies the ordinary
shell's terminal-transfer step cancelling the now-live renderer. Apply the
existing supervised-desktop adapter semantics only to the exact active video
child: root retains COM1, the renderer receives no terminal-input capability.
All other terminal operations still use kernel admission. This is supervision
of the authorized noninteractive exerciser, not new input authority. Preserve
four diagnostic results. Window02 reserves builds09..10<=300s, media07..08
<=180s and diagnostics05..06<=90s for this correction and evidence-directed
follow-up. Other original host/inventory/VMware reservations remain unchanged.

Build09/media07 pass. Diagnostic05 passes25.686s: actual1024x768 three-band
pixels, return to new healthy VGA generation/epoch, PS2 command/error output
and hardware cursor at the current prompt. Host04 passes2 tests1.114s,
including actual probe pre-bind wait/pixels/absolute timeout atO0/O2.
Extend the same bounded observer with private six-mode injection, sealed mode
state/descriptor/page snapshots and exact unmap checks. Use diagnostic06 for
preparation crash on unchanged build09/media07 before any new source build.

Diagnostic06 passes25.170s: injected driver UD2 during preparation, parent
detects fenced mode, reaps renderer/driver and restores a new healthy VGA
generation, PS2 and cursor. Raw mode seal, zero descriptor and absent graphics
PDPT entry confirmed. A clone binding typo was corrected before guest launch.
Review finds recovery had not yet charged the frozen restart policy. Charge
the existing shared two/10s policy once for abnormal start, renderer outcome,
driver outcome or stop timeout; normal presentation remains uncharged.
Exhaustion leaves fenced text hardware and COM1, and denies reintegration.
Use remaining build10/media08. Window03 reserves diagnostic07..10<=90s for
repeated healthy, graphics hang, return crash and exhaustion; preserve earlier
attempts. Full frozen matrix is still required, not replaced by diagnostics.

Build10/media08 pass. Diagnostics07..10 pass: repeated healthy28.405s,
graphics hang30.709s, return crash26.787s, restart exhaustion18.027s.
Exhaustion demonstrates exactly two successful VGA reintegrations then -11,
fenced/unmapped video, visible stopped VGA and responsive COM1 HELP.
Use the original reserved VMware diagnostic01<=180s on build10/media08.
Reuse CJ exact-window capture and PID/start-bound cleanup in a fresh CK folder;
verify the actual host log's128MiB/8MiB aperture before typing VIDEO, capture
graphics pixels and post-return keyboard HELP. This is development evidence,
not the unimplemented frozen qualification verifier or final VMware gate.

VMware diagnostic01 fails39.708s, stopped/media unchanged. Actual shell and
positive128MiB/8MiB aperture confirmed, but injected VIDEO never appears in
serial. Captured VMware status explicitly remains "click inside or Ctrl+G";
only an unattributed LS command appears later, so no mode claim is possible.
Use explicit owned-window Ctrl+G capture and mapped keyboard scan codes,
require exact VIDEO echo early, then reserve diagnostic02<=180s on unchanged
build10/media08. Never stop or inject into another VM. Original owned PID30112
was independently absent when exact-identity cleanup reached the host.

VMware diagnostic02 fails33.167s with stopped owned VM and unchanged media:
VIDEO echo still absent after explicit grab/mapped scan codes; LS again appears
without attribution. Helper and actual VMware UI token integrity are both8192,
so elevation mismatch is not established. User asked whether they typed LS.
No unchanged hardware retry; preserve both attempts and inspect input delivery
only after attribution is resolved. Frozen qualification gates remain unrun.

User confirms2026-09-26 that both LS commands were manual. Attribution resolved;
those runs remain failed, not accepted. Replace unreported keybd_event delivery
with Win64 SendInput scan-code events and checked accepted-event counts,
record every event, retain exact foreground-window checks and Ctrl+G grab.
Reserve VMware diagnostic03<=180s on unchanged build10/media08; user advised
not to type during this short automated test. No guest code/resource changes.

VMware diagnostic03 fails48.675s, owned process absent and media unchanged.
Windows SendInput accepts all16 exact scan-code events without error, yet the
guest receives no VIDEO. User confirmed physical LS previously, so reserve
diagnostic04<=180s with manual VIDEO/HELP and automated exact-window pixels,
serial/reap validation and owned cleanup. Host input wait/capture remains
within original130s transition/140s keyboard/180s total bounds. Manual input
is recorded explicitly; no synthetic-input success claim or guest-code change.

Manual diagnostic04 fails55.984s, stopped and media unchanged. HELP/CLS were
entered before VIDEO, and the observer treated their prompt as transition
return. Correct command attribution: only a prompt after the actual VIDEO
echo may finish the transition observation. No new guest attempt reserved or
launched yet; manual-input coordination remains pending. No VMware graphics
success, frozen qualification or final OS completion claimed.

Renewed user continuation reserves manual VMware diagnostic05<=180s on
unchanged build10/media08 with corrected command attribution. Observe VIDEO
pixels and subsequent HELP, retaining all existing guest and host limits.

Diagnostic05 fails56.487s before manual input on the inherited foreground
check. The receipt reports stopped=false; subsequent exact PID30676/start
2026-09-26T11:43:42 host cleanup independently confirms absence. Preserve
the failed receipt. Manual mode injects no input and PrintWindow targets the
exact owned HWND, so remove its unnecessary continuous foreground requirement;
retain all foreground checks for automated input. Reserve diagnostic06<=180s
on identical media, with the same command attribution and timing bounds.

Diagnostic06 fails56.637s with an empty assertion message in the owned-window
capture path;11 mode frames exist, no VIDEO echo. Its stopped=false receipt
is preserved; subsequent exact PID32740/start2026-09-26T11:45:28 host action
confirms absence. No graphics success. Prepare separate visual-test01 from
unchanged signed media08 using only the existing VMware configuration prefix;
prove both copied disk hashes. It is user-owned inspection media, not another
automated guest or qualification. Never clean up a later user-opened instance
as if it belonged to these stopped diagnostics. Gates remain unexecuted.

User directs QEMU-only testing because VMware interferes with their work.
Do not launch or focus VMware. Reserve QEMU diagnostics11..14<=90s each,
aggregate<=360s, on unchanged build10/media08 for remaining preparation hang,
graphics crash, return hang and current-observer healthy capture. Each uses
a fresh directory; stop on failure and inspect before any follow-up. The
required final VMware gate remains deferred, not waived or replaced by QEMU.

Diagnostic11 passes25.974s for preparation hang. Review of replay inputs finds
the display state capture included only96 of128 bytes; capture all eight
inverse words from diagnostic12 onward. Add graphics-only raw PD/PT/FIFO-PT
snapshots in three bounded read-only QMP calls for independent page-rights
replay. Earlier partial snapshots remain historical development evidence.

Diagnostic12 passes25.507s for graphics crash; independent raw replay also
passes, checking media/no-write receipts, seals, actual VGA/cursor pixels,
graphics roles/quotas and complete supervisor-only NX/UC framebuffer/FIFO
page tables. Tighten replay to require the exact failed worker's terminal
receipt and reaped family slot. Add host regression mutations for sealed but
unfenced state, user-accessible graphics mapping, unreaped family and altered
fault exit record. Use remaining host06<=180s after diagnostic13 return hang.

Host06 correctly rejects guest12's claimed crash: exact worker receipt is
cancelled0/reason3, not UD2. Renderer exitsEDQUOT122 before fault injection.
Diagnostic13 return-hang similarly fails31.918s, rendererEDQUOT before the
selected fault. Probe submits8 tiles/10ms, potentially80/100ms against the
unchanged64/100ms display limit. Earlier capture-only fault success must not
be accepted without terminal-receipt replay. Add actual quota behavior to
the probe host harness first (host07<=180s expected red), then pace4/10ms
within unchanged2000ms drawing deadline. Reserve build11<=300s/media09<=180s
and host08<=180s. Remaining diagnostic14 uses corrected image for healthy;
reserve diagnostics15..17<=90s for graphics crash/return hang/return crash.

Host07 reproduces EDQUOT0.520s in the actual probe with a64/100ms host quota.
Audit of all old receipts: guests05/07/08/09/12 all rendererEDQUOT122 despite
capture success. Their sampled middle-row colors did not establish the full
raster or successful renderer completion. Withdraw those success conclusions;
retain raw receipts unchanged. Guests06/10/11 retain actual preparation fault
evidence. New replay requires full1024x768 pixels, successful renderer exits
for healthy runs and exact selected driver fault receipts. Host08 uses the
new healthy14 fixture after correction, with four independent tamper cases.

Build11/media09 pass; kernel byte-identical to build10, only video.prg changed.
Diagnostic14 capture passes32.853s but strict host08 replay rejects it2.544s:
renderer exit5 after full drawing, worker cancelled. Kernel SLEEP_MS admits
only1..100ms; probe's final1000ms sleep was invalid. Preserve both records.
Model the existing sleep range in the actual probe harness (host09<=180s,
expected red), then use ten100ms sleeps for the unchanged1000ms hold.
Reserve build12<=300s/media10<=180s and host10<=180s; diagnostic15 now healthy
and16/17 retain return-hang/return-crash, reserve18<=90s for graphics-crash.
No runtime limit or syscall change; VMware remains suspended by user direction.

Host09 reproduces invalid long sleep0.545s. Build12/media10 pass with the
same kernel hash and corrected ordinary video.prg. Diagnostic15 healthy
passes35.336s; host10 passes3 tests5.943s including independent complete-raster,
successful exits, exact device/page/CPU rights replay and all four tamper
denials. This is the first healthy result accepted by the strengthened replay.
Run reserved16..18 sequentially on this exact media and require raw replay
after each capture; stop on the first failure. No further VMware launches.

Diagnostics16..18 and independent replay pass: return-hang34.913s,
return-crash35.189s, graphics-crash33.022s. Reserve QEMU19..23<=90s each,
aggregate<=450s for preparation crash/hang, graphics hang, repeated healthy,
and exhaustion on exact media10. Require successful renderer exit for return
faults and original1000ms health expiry for preparation/graphics hangs.
Repeated capture now records disjoint per-command frame groups, sampled more
sparsely to stay within the existing40-frame cap; each transition must have
its own complete raster. No guest timing/resource change. Stop at first failure.

Diagnostics19..23 and independent replay all pass: preparation-crash33.475s,
preparation-hang34.098s, graphics-hang36.057s, repeated37.969s, exhaustion20.577s.
The corrected candidate now has all nine QEMU development cases15..23.
Reserve one final read-only replay audit<=180s over these existing recordings,
binding current source hashes, signed image, QEMU binary and complete recorded
evidence; no new VM or acceptance-gate substitution. Frozen qualification and
the user-deferred VMware gate still remain. No implementation commit yet.

Final read-only audit passes10.263s: all nine cases15..23, aggregate guest
time300.636s,1332 recorded file hashes,29 current source hashes and exact
QEMU executable binding. Receipt qemu-replay-audit01.json explicitly sets
qualification=false. All owned QEMU guests stopped; VMware remains deferred.

Reserve defaults-diagnostic01 <=600s: verify accepted CJ qualification05 seal,
committed f96af9f6 source hashes, exact tools and preserved reference artifacts;
build NativeAppFiles and NativeVgaConsole once each <=300s and require every
recorded artifact byte-identical. Development check only; stop on first failure.
No fresh guest, VMware launch, changed acceptance gate or implementation commit.
Diagnostic01 stopped before any build: Git archive inherited host CRLF export,
while frozen CJ Makefile and committed blob use LF (exact blob hash confirmed).
Use command-local core.autocrlf=false for archive; no repository setting change.
Reserve defaults-diagnostic02 <=600s, same checks/build limits; preserve01.
Diagnostic02 also stopped before build: archive attributes still apply CRLF.
Diagnostic03 <=600s uses one bounded git cat-file --batch call, exact raw blobs,
no text normalization or export; original source hashes remain mandatory.
Diagnostic03 confirms mixed accepted checkout line endings: Makefile LF, some
assembly CRLF. Diagnostic04 <=600s compares each raw committed blob hash,
or explicitly records its exact LF-to-CRLF checkout representation hash for
NUL-free, CR-free text only. No arbitrary normalization; artifact comparisons
remain byte-exact. All three pre-build failures preserved.
Diagnostic04 stops before build on cpu_local.c, whose accepted checkout uses
mixed line endings. Current file exactly matches its frozen hash; removing
CRLF gives the exact committed blob. Diagnostic05 <=600s additionally admits
that exact frozen current-file representation with bytewise blob comparison
apart from CRLF. No substantive source difference is admitted.
Diagnostic05 stops on a CK-modified assembly file: its historical mixed checkout
cannot be reconstructed from the current file. For development diagnostic06
<=600s use the accepted clean-commit receipt linking the sealed CJ checkout to
f96af9f6, retain both original checkout hashes and raw Git blob inventory, and
verify original seal/tool/artifact hashes. Do not claim equal checkout/blob
hashes. Frozen default gate still remains; this diagnostic is not qualification.
Defaults diagnostic06 passes27.682s:91 NativeAppFiles and97 NativeVgaConsole
artifacts all byte-identical to accepted CJ qualification05. No guests started.
Reserve package-diagnostic01 <=180s, existing build12/media10 only: signed media
and ordinary program equality, actual static role stack records, ELF writable
storage <=64KiB per role and no kernel/core undefined symbols. Development
inspection only; selected fresh-build/frontend/frozen gates remain separate.

Package diagnostic01 passes1.036s: signed ordinary program binding, no undefined
kernel/core symbols, actual static role stack sum1912bytes, fixed writable
driver7984bytes/probe16384bytes. No runtime source changes or guest launches.
Frozen qualification still open; no implementation commit.

## Frozen qualification01, QEMU-only execution through gate4

Reserve one ordered qualification01: original host180s/defaults600s/package600s/
runtime1200s gates exactly once, first failure stops. Nine fresh cases each90s,
aggregate<=900s, independently replayed; fresh healthy evidence supplies four
altered-evidence rejection checks. Sources/tools/contract/scope/accepted fixture
hashes frozen before gate1 and checked between gates. Default artifacts remain
byte-exact against sealed accepted CJ; selected build and signed media fresh.
Package checks actual role stack/storage/undefined symbols, root-tree and ext2
program bindings plus common Windows/Make selector forwarding. No guest-code,
resource, acceptance limit or authority change. Gate5 remains user-deferred;
qualify-qemu writes incomplete/pending, never accepted, and launches no VMware.
All prior development failures retained. No commit or CB restoration before
all five original gates pass. Source-bound gate code is frozen for this run.


## Approved allocation and QEMU acceptance 2026-09-26

User renewed "mach weiter" directly after the explicit split-acceptance
question and concrete NATIVE_VIDEO_MODE_PROPOSAL.md. The proposal is approved:
CK may close for the QEMU research profile after independent evidence review;
VMware healthy/fault hardware acceptance remains mandatory before a VMware
release or completed native64 OS. VMware stays deferred by user instruction.

Qualification01 gates1..4 passed6.256/31.212/22.670/337.143s. The approved fifth
QEMU-only review is recorded by acceptance-qemu01/review.py (600s bound) and
passes13.076s: all nine raw cases,1335 evidence hashes, exact sources/tools,
signed image/default artifact bindings and fresh tamper-denial receipt.
No guest, capture or replay implementation changed; no rebuilt images or new
VMs were required. Original qualification01 receipts and full-platform review
remain unchanged, including pending.json. The original --review continues to
fail closed without actual VMware acceptance; the scoped external review is
not a claim that that hardware gate passed. Direct final diff/scope review:
fixed append-only ABI, bounded storage/loops/FIFO, generation admission,
fence-before-reap, unchanged old-profile artifacts and historical failures.
Only docs/queue allocation bookkeeping changes follow this source review.

Next transaction: restore the exact latest CB archive after the CK local
commit leaves a clean worktree. Bind to the accepted CK source and integrate
the real desktop in QEMU; preserve CB tests/counters and final VMware gates.

## CL approved FIFO prerequisite, 2026-09-26

User mach weiter immediately after the explicit16KiB/kernel question approves
the concrete CB-contract FIFO proposal. Baseline08478f40 clean after verified
CB archive before-native-fifo01; CB queued/unaccepted. Exactly one active CL.
Use fixed16384-byte FIFO, four existing-table supervisor-only RW/NX/UC leaves
inside previously validated PCI aperture. Minimum usable data>=10240 bytes,
header16..4072 aligned; validate MAX, NEXT/STOP, reserved guard dword, UPDATE
rectangle64x64 bounds, preflight-before-copy and existing generation/fencing.
No new syscall, raw user authority, DMA, CPU/IPC quota or busywait. Reference:
QEMU hw/display/vmware_vga.c vmsvga_fifo_length rejects MAX<MIN+10KiB.

Frozen five gates: host test/test_x86_64_video_mode.py -v<=180s; verifier
--fifo-defaults<=600s; --fifo-package<=600s; --fifo-runtime<=600s;
--fifo-review<=300s. Existing verifier file adds separate CL modes; original CK
gates/receipts unchanged. Defaults: fresh NativeAppFiles/NativeVgaConsole
byte-exact accepted CJ artifacts using existing diagnostic_defaults. Package:
fresh NativeVideoMode build<=300s/media<=180s and actual diagnostic_package.
Runtime: four fresh QEMU cases healthy,repeated,graphics-crash,graphics-hang
each<=90s,total<=360s, existing complete independent replay including fenced
VGA return/CPU/authority checks; exact four-page mappings, actual consumed
FIFO UPDATEs on healthy/repeated captures. Host tests cover >one full ring
wrap with modeled consumer, full/no-effects, malformed header/ranges and guards.
Review: replay all four raw cases, media/source/tool/hash binding and retained
host/default/package receipts; reject tampered FIFO mapping/consumption data.
Gate driver freezes sources/scope/contract/tool hashes before gate1, checks
between gates, stops first failure, stores logs under ignored r83cl-video-fifo.
No VMware launch; actual VMware healthy/fault proof remains final milestone.
No unchanged retries. Reserve development host01 before/after<=180s, then
qualification01 once. Finite next diagnostic only for an observed failure,
record historical counters; no reset or relaxed acceptance.
After passing all gates, direct diff/scope review and local commit; restore CB
source archive without overwriting accepted kernel or queue/current docs.
