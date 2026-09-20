# Native bounded wide-file profile — R8.3ba

User approval20 September2026 follows accepted AZ5db38510 and inventory77b37880.
Exactly one main-worktree implementation transaction. No agents, push, user or
physical media; R3.6b remains deferred. This is not full OS acceptance.

## Boundary and standards

Reuse the actual Ring3 ATA, FAT12/FAT32/EXT2 parsers, native block/FS RPC-v1,
System V AMD64 ELF64 ET_EXEC, unchanged RNPGv2 and kernel CREATE validation.
No persistent format, write operation, DMA, additional controller or Ring0 parser.
The existing ELF input ceiling524288 bytes does not enlarge its64-page mapping
extent, reserved stack/guards or W^X rules. File bytes grant no rights.

Legacy file capture1536/FS8/block16/3000ms/100ms pacing and every old entrypoint,
structure, selector and default remain valid. New explicitly named/versioned
local profile2 APIs select the larger finite budgets; the existing wire format
is unchanged. No old version1 object acquires new semantics by recompilation.

One immutable medium, one exact driver/FS generation pair and one absolute
whole-file deadline bind STAT, data, EOF, ELF preparation and publication.
No implicit retry, counter reset, service recreation or renewed deadline inside
capture. Namespace queries keep their ordinary1000ms RPC bound; a distinct
wide observation records the original120000ms capture end before STAT starts.
The caller cannot convert an old observation into a new successful capture.

## Fixed capacities and recovery

Input524288 bytes, private fixed workspace (file bytes,512-byte frame,266336-byte
prepared record). At most2050 FS requests: one STAT,2048 data reads of256 and
one EOF. The same generation also enforces its total2050 limit. Existing used
clients need sufficient remaining capacity before reading anything.

Block profile2 permits4096 total reads,120000ms absolute generation lifetime.
First read waits at least100ms since initialization, later reads at least50ms
since previous completion. Sleep blocks; no quota retry. Kernel64 PIO calls per
100ms,16 words per transfer, CPU32/1000ms, ATA200ms and individual IPC1000ms
remain unchanged. Quota/backend failures fail closed even before profile limits.

FS profile2 uses exactly16 cache sectors with bounded FIFO replacement, bound
to the same immutable medium/owner and erased on poison/fence/reinitialization.
No returned bytes from an unsuccessful replacement. Metadata traversal bounds
remain those of existing parsers; arbitrary files need not succeed if they
exhaust a declared budget. Generated FAT and EXT2 layouts exercise real chains,
direct/indirect data and sector/cache crossings, not a fake byte backend alone.
The retained EXT2 parser supports direct and single-indirect blocks only.
Full512KiB succeeds on the generated FAT12/FAT32 and EXT2-2KiB/4KiB layouts;
EXT2-1KiB at that size requires unsupported double-indirect traversal and is
a fail-closed negative host case, not a compatibility claim.

Normal shell dispatch, exact generation identity, attenuated child import,
terminal handoff/wait/reclaim and service fencing/reap/recreate all remain real.
Creation8/1000ms and restart2/10000ms unchanged. No implicit device rights or
counter reset. Owner loss and failed cleanup take existing fail-closed paths.

## Qualification

Regression first: actual C O0/O2 block/FS/media/capture/ELF behavior, boundaries
1536/1537, cross-cache, full524288, oversize, insufficient requests, stale/reused
observation, malformed/short/extra EOF, bad ELF, deadline and clock regression,
all unchanged-output and scrub paths. Old host tests cover legacy behavior.
Both Make/Windows selectors and conventional shell command resolution tested.

One new common image and at most one legacy ShellSession regression image.
Twelve new-profile guests: five media,8GiB reference, full input-cap boundary,
driver crash, FS crash, FS hang, malformed reply and application crash/recovery.
Each<=300s including<=3s cleanup. Full old eighteen-case ShellSession regression
each<=45s. Aggregate4410s, runtime gate4800s, first failure stops. No unchanged
retry. Full raw actual CPU/PIO/IPC/ELF/task/frame/terminal/reap evidence required,
including independent byte reconstruction and mutation tests of the oracle.
Private diagnostic sequence ceilings may be enlarged only under the new
selector (fixed262144 records each), same finite ring sizes and every original
record/cleanup predicate; no authority effect. Observer output<=256MiB/guest.

Immutable generated data media only, existing read-only base/disposable COW
discipline and zero allocated overlay data after success/failure. No boot-media
rebuild in this package: the separate new kernel is directly booted for runtime
qualification. AZ BIOS proof stays bound to its original accepted image and is
not relabeled as proof of this new image.

Queue freezes nine gates and scope. Before execution, freeze all source/tool/
command/input hashes and complete finite reservation. Each gate executes once
and stops on first failure. Independent raw review, direct diff/ABI/cleanup
review, all gates and clean local commit precede acceptance/queue advancement.
Keep all failed attempts; subsequent evidence-directed windows must be frozen
separately under standing authority. No partial host pass is runtime acceptance.

## Candidate02 correction window

Candidate01 stopped at gate3 (receipt547e8ed0cd7fc71162cf26b0753fe4c515468754a6bfcc61b8de9ce90d57ae38).
New host gates1/2 and legacy capture/launch pass; the legacy FS regression calls
the private fs_sector callback with its original server pointer. The initial
context refactor changed that private contract and caused host access violations.
Restore the callback contract through an actual shared read helper; preserve the
old regression unchanged. This is an in-scope implementation correction, no
policy/ABI/acceptance change. All nine gates execute once for a new exact freeze.
Zero builds/guests spent; reservation remains two builds and12+18 bounded guests.

## Candidate03 approved projection window

Renewed user approval20 September2026 adds only the historical ShellSession and
Terminal verifier files to scope. Candidate02 stopped at gate3, receipt
9aaa93c0be6375f711dd60acde5aa4ed209eadf4783d4ad0261be4a7f1091b3b;
zero OS builds/guests. Preserve both failures and their exact candidate sources.
Project exact disabled BA Make/Windows selector additions and the full already
accepted AZ packaging-only target before the unchanged historical equality
checks. Missing/duplicate/mutated clauses and unrelated changes still fail;
new mutation hosts supplement the unchanged historical regression suite.
No production change in this window. Same nine gates once, same two-build and
12+18 guest reservation, CPU/ATA/IPC/rights/time/assertion bounds unchanged.

## Candidate04 canonical media correction

Candidate03 passes gates1..5, including all legacy hosts and both OS builds.
Runtime stops before QEMU spawn because the shared collector admits the exact
canonical Fixture class, whereas the BA adapter supplied a subclass. Preserve
stop8031045d64702c6b68a4de4b611aa6bdd4712cf78a66e694e239b0859d1af819,
both images and prelaunch0.11856989999068901s; zero physical guests so far.
Bind BA contents/deadline methods to the original class, preserving its exact
type admission, readonly/COW verification and all cleanup guards. Host capture
admission regression precedes freeze. Proof/test/docs only; unchanged production
sources, tools, build logs and every artifact hash bind both reused images.
Nine gates once (build gate now validates exact existing images), zero builds,
same12+18 guests/4410s. Cumulative builds remain two; first failure stops.

## Candidate05 reader deadline binding

Candidate04 gates1..5 pass, first FAT12 guest48.1580214999849s runs the normal
shell and larger app once, then stops on the retained binary reader42s deadline
during the second root lifecycle. Stop receipt
ea585235f92555fbfe8734dacd76d0fd804e673f8ce5775e3aff57d574a43278 retained.
BA-only configure adapter sets the approved297s observation lifetime once at
reader construction; shared reader source, per-command deadlines, capacities,
translation/equivalence, stop cleanup and all runtime predicates unchanged.
No image changes/builds. New exact nine-gate window,12+18 guests4410s maximum;
spent totals two builds, one guest48.1580214999849s plus prelaunch0.1185699s.
Maximum cumulative31 physical guests4458.1580214999849s, no acceptance/reuse of
the incomplete first guest, first failure stops. Host adapter regression first.

## Candidate06 complete observer dispatch capacity

Candidate05 first guest88.60340109997196s stops at the shared observer's8192
dispatch batches, after one complete root and second-root startup; no runtime
acceptance. Stop3bae13a8a59b283cfce5ac98ec4559b86fd203748c64a129f1c6cb18b32541b0.
Apply the already frozen262144 private observer ceiling to the two retained
batch/callback guards too. No reentrancy/pending/cleanup predicate or actual
CPU ledger/budget change. BA-generated observer only, shared modules unchanged.
Same images/tools/production, no builds; all nine gates once and12+18 guests
4410s maximum. Preserve two physical guests136.76142259995686s, two builds and
prelaunch0.1185699s; cumulative maximum32 guests4546.761422599957s. Stop first
failure, no partial proof reuse. Generated full observer host regression first.

## Candidate07 exact physical oracle and complete first-case reuse

Candidate06 completes both FAT12 root runs119.69600840000203s, debugger0,
cleanup0.024229s, readonly medium unchanged; post-capture physical oracle still
limits the old profile to17 sectors/1024 OUT events. Correct only those three
profile capacities to4096 reads/262144 physical events, all byte/port/generation/
quota predicates exact. Full readonly replay now passes18 tasks,797 snapshots,
16591192 snapshot bytes,66 binary reads/8566880 bytes,57024 CPU bytes and10394
probe steps. Preserve stoppedc4a3006d27992a8f963d63b350b217b1f5f3e849203b23dede0ba460b027e884.
Reuse this complete case only through exact collector-source projection,
same production/tool/image hashes, every raw file hash and full independent
replay. Eleven fresh BA guests plus18 legacy,4110s; nine gates once, no builds.
Spent three physical guests256.4574309999589s/two builds plus prelaunch0.1185699s.
Cumulative maximum32 physical guests4366.457430999959s. Full12+18 cases and
all original safety proofs still mandatory; first failure stops.

## Candidate08 serial fragment accounting

Candidate07 gates1..5 pass, FAT12 reused proof passes; FAT32182.0623723999597s
stops on host serial queue overflow with only1442 consumed bytes, not a guest
byte-cap violation. Retain stopped1642b255d895801b15be091eb2956188cdc439ff39e233d81d6f826bd4c34f35.
The shared128-entry queue counted pipe fragments; short reads make its byte
capacity variable. BA-only queue admits at most262144 entries and the producer
independently enforces the unchanged262144-byte lifetime cap before enqueue.
Nonempty chunks imply entry count<=byte count; no discarded successful bytes.
Consumer byte/overflow checks remain exact. Host tests exercise one-byte reads
at128/129/262144/262145. Shared capture unchanged; no kernel/image/build change.
FAT12 raw reuse excludes only this tested host serial adapter in addition to
the exact prior physical oracle correction, not any debugger/runtime predicate.
Nine gates once, eleven fresh BA/eighteen legacy guests4110s, no builds.
Spent four guests438.5198033999186s/two builds plus prelaunch0.1185699s;
cumulative maximum33 guests4548.519803399919s. First failure stops.

## Candidate09 bounded live byte snapshots

Candidate08 gates1..5 pass; FAT32 waits after cd despite complete RX/prompt proof.
Offline feeder replay emits the next command in0.175s; live chunks are separated
by280s. TextIO.read(128MiB characters) follows a concurrently growing CRLF log
instead of a fixed existing byte extent. Guest stops301.3197707000072s, exceeding
whole300s; no acceptance, all failure/cleanup evidence retained, stop SHA
7dc6fb735ddd9b0f689d205ba02225932b84c59b285c979b4203f431faeb09c6.
BA-only live reader snapshots fstat byte extent<=128MiB, reads exactly that many
bytes unbuffered and applies the same universal-newline conversion as replay.
No omitted complete record, capacity increase, timeout renewal or shared-file
change. Host regression includes CRLF/growing tail and oversized admission.
Reuse complete FAT12 raw proof with only the explicit tested host transport
projection; debugger and every safety predicate unchanged. Nine gates once,
no builds, eleven BA/eighteen legacy new guests4110s. Spent five physical guests
739.8395740999258s/two builds plus prelaunch0.1185699s; cumulative maximum34
guests4849.839574099926s. Same300/45s guest limits, first failure stops.

## Candidate09 stopped: full-size evidence capacity, no new window

Gates1..5 pass. The complete FAT12 raw case from candidate06 replays unchanged;
five fresh FAT32/EXT2-1KiB/2KiB/4KiB/8GiB cases pass both root lifecycles in
38.36470360000385/46.77672649995657/46.796513199980836/45.55000370001653/
48.0200557000353s. Full512KiB then stops192.9664159999811s at the128MiB live
text limit, first root offset298240. Preserve stop SHA256
ba4a78d0242f865e6218f99dad57edf70ed7e854b23ea527c668e2cc2aab8504 and freeze
0774ecb81471c503e0532898c4b1ce4d6f0956d7d2b47261b76b87216fe97b8b.
No later guest/gate/acceptance/commit. Cumulative two builds, eleven physical
guests1158.313992799900s plus prelaunch0.11856989999068901s; reused FAT12 is
not charged twice. All subsequent work is read-only diagnosis/documentation.

The failed raw log is134334666 bytes, with78865 SHELL_SESSION rows. Offline
zlib level1 measurement yields5075920 bytes without changing any evidence;
this is not implemented transport or acceptance. Last root call50740ms precedes
capture end120850ms. No kernel deadline violation established by this stop.
Raw CPU trace contains1456 records (638 root/257 driver/561 FS),279552 bytes.
The separate private CPU producer and reader still cap the whole two-root
trace at2048. Further overflow is a forecast risk, not this observed failure.

Proposed, not authorized/frozen: add only arch/x86_64/proc/cpu_trace.inc to scope
for BA-selected262144 private sequence ceiling with unchanged256-entry ring
and legacy2048. No runtime quota or accounting/recovery change. Adapt CPU
transport/count projections only in already scoped BA scripts/tests; retain
all record decoding, continuity, exact charge/receipt/quota and corruption
predicates. Add bounded lossless host evidence encoding/complete replay with
mutation tests,128MiB stored trace/128MiB snapshots/256MiB aggregate unchanged,
decoded offline text bounded to512MiB. No missing records or lossy compression.
One additional common BA image only; unchanged legacy image reused. A fresh
nine-gate window would reserve12 new BA/18 old guests, same300/45s including3s
cleanup,4410s aggregate, first failure stops. Prior six normal cases remain
evidence for their old image, never relabeled as proof of a new kernel. This
would cap cumulative builds at three and physical guests at41/5568.313992799900s.
No proposed source/transport/build/guest change performed without scope approval.

## Candidate10 approved diagnostic/encoding correction

Renewed user ja mach weiter grants precisely the preceding extension. Add only
cpu_trace.inc; the two guarded CMP constants become262144 for BA, otherwise
the file projects byte-exactly to the original2048 path, same256-entry ring.
BA host copies of CPU decoder/reader and lifecycle oracle alter only total
diagnostic capacities, never accounting, per-window quotas, record fields,
ring-overrun rejection, identity, closure or recovery. No shared host change.
Old regression image remains exactly bound to its original sources/artifacts.

Preflight found the pinned GDB Python lacks zlib and _ctypes (no guest/build).
Use REIST-private WIDE_D1 lossless evidence envelope instead: original ASCII
record length, CRC32 and RFC4648 base64 containing literal ASCII bytes,
fixed dictionary tokens128..254 or marker255 plus LE24 count of ASCII zeroes.
Dictionary and encoder are embedded identically in the observer. This is a
private diagnostic format, not claimed zlib/DEFLATE compatibility. Standard
compression cannot be used without an unavailable extension; no installation,
additional executable or native call. Complete original records are decoded
before all original semantic predicates, and frozen file SHA256 binds stored
evidence. Length<=65536 per decoded record, cumulative512MiB, stored trace128MiB,
snapshots128MiB and aggregate256MiB remain fail-closed. Reject unknown versions,
tokens, truncated/oversized runs, noncanonical base64, checksum/length mismatch.
No discarded records. Root-start and CONSOLE_IO records remain plaintext for
the unchanged acknowledged-input feeder; its exact stored-prefix receipts are
replayed before decoding. CPU/PIO record sequence and all raw byte comparisons
remain mandatory. Actual GDB encoder and corruption/default-projection tests
precede one approved new image and all twelve new-profile/eighteen legacy guests.
Same nine gates,300/45s with3s cleanup,4410s reservation, first failure stops.
No earlier guest reused as proof of the new image. Two prior builds/eleven
guests1158.313992799900s and all failures remain preserved.

## Candidate11 confirmed initial-pacing correction

Candidate10 gates1..5 pass, one new image d4bb6e642c9b1e718a7b69f2bbf1cb46c4f6ed3d23f262ba781a01ee131dd78a
differs from the previous kernel in exactly four bytes (two2048->262144 CMP
immediates); userspace catalog is identical. All six fresh normal cases pass
239.38784969999688s. During direct source review, actual C regression confirms
that a rejected request increments requests and incorrectly spends the initial
100ms read guard: next valid request attempts I/O at50ms and the behavioral
backend rejects it. Red development log initial-pacing-red.log and candidate10
freeze/sources/results retained. Adding this regression deliberately invalidates
the running source binding; the already started eighth-GiB case cleans up and
passes, then binding stops BEFORE full-size or fault/legacy guests. No predicate
was weakened or successful matrix claimed. Stop87f0a0935308067f7cc5611cb6a5d01e7c782cef34d82f94ce6370c887829e72.

Evidence-directed correction stays in already allowed native_block.c and host C.
For wide spacing50 only, ready1 retains the initial100ms guard until a successful
physical read; ready2 then uses50ms. Invalid requests and failed/short waits
cannot spend it. No ABI layout, operation count, request limit, lifetime, kernel
quota or rights change. Old dispatch wrappers always pass100: both old/new
expressions equal100, and neither ready update executes. Exact source projection
plus actual O0/O2 legacy-path tests justify retaining the original legacy image;
do not describe it as rebuilt from candidate11. Five rejected-first variants
(malformed envelope, sequence, too-short deadline, short sleep, wrong owner)
and following two successful reads are tested on every host media/size vector.

Under AGENTS.md standing in-scope correction authority, reserve one additional
corrected BA image in wide-pacing and twelve fresh300s BA/eighteen45s old guests,
same4410s total/nine gates/first failure stop. This is a new bounded window,
not another diagnostic retry or a change of the CPU-extension authority. The
unexpected production bug makes the earlier diagnostic-only image insufficient.
Preserve cumulative three builds/seventeen physical guests1397.7018424998969s
and prelaunch0.11856989999068901s; next maximum four builds/47 physical guests/
5807.7018424998969s. No earlier case is reused as proof of the corrected image.

## Candidate11 stopped at whole-guest observation deadline

Gates1..5 pass; corrected image2fb2abf870364be311cc69d2979215b9c28fb7703ed2100c5828e37db5314df9.
Six fresh normal cases pass235.9782201999915s. Full512KiB records the first
root's exact EOF request at offset524288/time89820ms and app generation9 entry
at89830ms, SESSION64 output/app exit82 and root exit0. This is partial diagnostic
evidence, not a replacement for full two-root raw replay. Root1 finishes at
host287.161466s; root2 starts, reaches offset9728, then the unchanged297s feeder
deadline stops capture. Whole guest299.24216690001776s/cleanup2.036394s; GDB CPU
196.359375s/QEMU CPU102.109375s. Five offline complete live-reader snapshots take
0.342s, not the previous unbounded growing-text read. Stored trace60556364 bytes,
CPU2118 records; no record/capacity weakening. No later guest/gate executed.
Stop12842bf6de4f6a24fff803a99b18bd32352490a1078389a7143034be4cf72582,
freeze b9e55dc9371503127b100c63d5256af069a25c7d683156083318686abef95868 retained.
Cumulative four builds/24 physical guests1932.9222295999061s and original
prelaunch0.11856989999068901s. No acceptance, queue transition or local commit.

Proposed genuine verifier-contract change, not yet approved/frozen: only the
full-size two-root case may use900s host whole/897s observe/3s cleanup. All
other300/45s bounds, original kernel120000ms capture generation, CPU32/1000ms,
ATA/individual IPC, identities/rights, stored/decoded proof capacities and
semantic assertions remain exact. No new image. Bind and replay the six fully
passed candidate11 normal cases against exact collector sources, tools, image
and all raw files. Six fresh BA cases (full plus five failures) and18 old ones,
3210s new guest reservation; together with235.9782201999915s reused evidence
this fits the original4410s aggregate/4800s runtime gate. Same nine gates once,
first failure stops. Cumulative ceiling remains four builds,48 physical guests,
5142.922229599906s. Never relabel the failed full case or omit its second root.
No proposed deadline adaptation or new execution has been performed.

## Candidate12 authorized full-only host window and exact reuse

The user's renewed `ja mach weiter` approves the preceding proposal. Only the
full512KiB two-root host case uses900s whole/897s observation/3s cleanup. Every
other BA case remains300s and every legacy case45s. All kernel capture/CPU/PIO/
ATA/IPC/rights and proof-capacity/semantic assertions stay unchanged. No builds.
The corrected candidate11 image and original legacy image are admitted through
their exact source/tool/build-log/artifact receipts. The six complete normal
proofs retain original paths, whole collector projection and all raw hashes;
full independent replay is required before freeze, in runtime and in review.
The failed full case is never reused. Candidate12 reserves six fresh BA cases
(full and five faults) plus18 legacy,3210s new guest time, within original4410s
aggregate including235.9782201999915s reused evidence. Nine gates once, unchanged
4800s runtime gate, first failure stops. Four prior builds/24 physical guests/
1932.9222295999061s and prelaunch0.11856989999068901s remain in the ledger.
Cumulative ceiling four builds/48 guests/5142.922229599906s. No acceptance or
queue transition before every gate, direct review and clean local commit.

## Candidate12 qualification complete

All nine frozen gates passed, including targeted and seven legacy host groups,
the complete12-case BA and18-case legacy matrices, independent full30-case raw
replay and scope review. No new OS build. Six earlier normal cases retain exact
original source/tool/image/all-raw identities;24 fresh guests consumed
1147.8549077000935s. The full512KiB two-root case passed577.539102300012s,18 tasks,
46406 verified probe steps and13123 snapshots (128318360 snapshot bytes), within
the unchanged capacities and kernel/service/CPU limits. Physical media remains
unchanged with zero overlay data writes. All five new-profile fault cases pass.

Immutable pre-commit seal: `build/codex-agent/r83ba-wide-file/candidate12/acceptance-seal.json`,
SHA256 `1143439f309e95a9b8d1142a3ddd9c846c420ce488c9829591322b024e23f122`.
Retained total: four builds,48 physical guests,3080.7771372999996s plus original
prelaunch0.11856989999068901s. Direct diff review covers ABI/default compatibility,
fixed bounds, generation cleanup, physical fencing and no in-kernel parser.
Only these outcome documents and the exact done queue transition follow the
seal. A separate final receipt binds the clean local implementation commit.
This is bounded read/capture/launch qualification, not complete OS/desktop or
hardware acceptance; no new BIOS media was qualified here. EXT2-1k full-size
double-indirect input stays unsupported, and R3.6b stays explicitly deferred.
