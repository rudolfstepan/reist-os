# Native large immutable capture and ordinary shell launch — R8.3bv

Frozen after accepted BU67fa5dfd,23 September2026. Standing user approval of
NATIVE_LARGE_EXECUTABLE_PROPOSAL applies; no renewed routine permission.
One visible main-worktree transaction, no nested agents/push. R3.6b deferred.

## Inventory and failure boundary

BU qualifies RNPGv3/CREATE-v7 and256 image slots, keeping old catalogs and
versions. Existing Ring3 capture already binds STAT/read/EOF to owner/sequence
and an absolute deadline. Profile2 is524288 bytes,2050 FS and4096 block calls;
its workspace, producer and shell import still select RNPGv2. Block/FS/service
profiles have version2; append version3 rather than changing old meanings.
Use the accepted BT ordinary shell/libc/math/text composition as the baseline.
No QuickJS implementation, script authority, network/display addition, kernel
mechanism change or new device/write/DMA grant in this package.

One cohesive transaction owns immutable media -> driver/FS generation ->
complete bounded capture -> RNPGv3 -> ordinary shell launch -> contained
retirement. Capture failure cannot publish a partial executable or recreate
services/replenish counters inside the failed operation.

## Append-only contracts

System V AMD64 ELF64 ET_EXEC; existing VFS STAT5/READ6, FS/block RPC-v1,
negative errno results, ATA PIO and FAT12/FAT32/EXT2 terminology stay exact.
Append capture observation3 (same552-byte fixed layout), workspace3,
file_stat_v3/file_finish_v4, block/FS/service profile3 adapters and independently
named build/media selectors. Existing v1/v2 observations cannot be converted.
All ordinary programs under the selected new profile use the accepted
CREATE-v7 snapshot; driver/FS images may retain their small v2 construction.
No syscall renumbering or existing public-structure growth.

Input<=1048576, prepared1052960, FS<=4098 total calls (STAT+4096 reads+EOF),
block<=8192 per exact generation. Same120000ms absolute service/capture end,
1000ms RPC,200ms ATA,16-sector cache,100ms first/50ms later pacing. Existing
CPU,stack,heap,task/restart/creation/output/PIO quotas remain unchanged.
Preflight all extents, overlap, observation version/size, canonical STAT,
owner/sequence, remaining calls and time before effects. Full reads and exact
EOF before ELF parsing; final identity/deadline check before one publication.
Admitted workspace scrubs on every return; rejection leaves outputs unchanged.
No hidden retry/rebind, clock regression acceptance or deadline renewal.

Generate only immutable fixture media, never open a user's/physical disk.
New EXT2 reference volume is exactly2MiB/4096 sectors with2KiB blocks;4KiB
variant shares the existing direct/single-indirect parser. A1KiB layout needing
double-indirect access must fail closed, not extend the parser. FAT layouts
reuse existing geometry. No persistent-format modification. Signed BIOS media
reuse existing manifest3/research signing and separate read-only data master;
Windows/Make packaging and the independent consumer bind every byte.

Ordinary largetest.PRG is discoverable on the shell search path, verifies low,
middle and last RW pages plus last RX page, and returns through normal wait.
Its ELF is padded to the exact1MiB input boundary for capture qualification;
padding never enlarges loaded rights. Keep all accepted text/libc/math tools.
No rescue-shell-only command or claim of JavaScript execution.

## Frozen verification and reservations

Development:12 host commands<=600s each;4 builds<=300s;2 media productions
<=180s;6 diagnostic guests<=300s. Record before execution; preserve all spent
counters/failures. Evidence-directed correction reservations require inventory
and a new finite window, never unchanged retry or weaker acceptance.

Five frozen gates, once per fresh candidate, first failure stops:
1. python test/test_x86_64_large_file.py -v (900s).
2. python scripts/verify_x86_64_large_file.py --defaults (900s).
3. python scripts/verify_x86_64_large_file.py --package (900s).
4. python scripts/verify_x86_64_large_file.py --runtime (5000s).
5. python scripts/verify_x86_64_large_file.py --review (900s).

Host O0/O2 executes actual capture/block/FS/service/parser code: old/new caps,
full1MiB, oversized STAT, insufficient calls, stale/reused/converted observation,
wrong version/size/owner, short/extra EOF, malformed ELF, timeout/regression,
unchanged outputs and scrub. Exact disabled source and old behavior protect
all existing profiles. Actual standard EXT22k/4k media and ordinary shell
resolution are tested; source patterns never replace behavior.

Package builds at most one normal and one hardware-qualified image and one
signed reference media set per candidate; no per-fault rebuild. Runtime14
fresh guests: full boundary EXT2-2k4/8GiB, EXT2-4k, FAT12, FAT32; unsupported
EXT2-1k and oversized-input rejection; driver crash, FS crash, FS hang,
malformed reply, application crash/recovery; two accepted legacy references.
Each<=300s, aggregate<=4200s. Include actual signed BIOS reference boot in
EXT2 normal coverage. Same-generation exhaustion, no implicit capture retry,
fence/revoke/reap/recreate/self-test, terminal/shell liveness and old handles
must be proved. Independent complete raw CPU/PIO/IPC/file reconstruction,
page/frame/ownership and media no-write replay plus negative oracle mutations.
No marker-only evidence, hardware isolation claim or relaxed runtime quota.

Final direct scope/ABI/cleanup review, every frozen gate, local commit and a
clean worktree precede next QuickJS inventory. Required source outside the
frozen list is an architectural scope stop. No overall native64 completion
claim from this prerequisite package.

## Development inventory (2026-09-23)

Host01 is expected missing-header failure1.582s. Host02 links actual profile3
capture/block/FS code but FIFO metadata eviction causes deadline exhaustion
at the1MiB boundary8.648s. Host03 keeps the same16 sectors and promotes hits
with at most15 fixed512-byte copies; EXT22k/4k and FAT12 now pass, without a
quota, pacing, deadline or parser change. Old profile2 keeps FIFO semantics.

Host03 retains the remaining FAT32 full1MiB failure9.379s: its1-sector-cluster
chain plus metadata exceeds the16-sector working set. The unchanged120000ms
end rejects before publication. The proposal explicitly makes1MiB an upper
bound, not a success promise. Qualification's full-boundary success remains
EXT22k/4k (and FAT12); FAT32 healthy coverage uses the measured754104-byte
QuickJS-sized input, with a separate exact1MiB deadline/fence/untouched-output
rejection. No larger cache, time budget, alternate FAT geometry, chain parser
or silent fallback is introduced. All rejected capture workspace is scrubbed.
Host04 tests these concrete boundaries and all original injected failures.


## Scope stop: eight-owner linker composition (2026-09-23)

Host04 passes11.457s: actual C O0/O2, four sizes and five layouts, including
explicit unsupported/deadline rejection and20 injected failures on admitted
captures. This is host evidence only. No BV acceptance gate or guest has run.

Build01 fails0.996s because the new CLI selector was not registered; corrected
in the already allowed builder. Build02 compiles all ordinary programs and
services22.457s, validates inner C layout5, then fails the frozen link guard:
`native eight-owner arena requires exact wide boot pair`.

Concrete cause: config/x86_64_bootstrap.ld:146-148 admits the existing7499776
byte eight-owner arena only with270336-byte scratch. Its earlier exact-pair
assertion already admits the BU1056768-byte scratch with1052960-byte payload,
and the unchanged independent C-payload verifier explicitly supports both
layout5 arena and the selected large scratch. BV combines these established
layouts; the final redundant pool guard still excludes their combination.
Removing the task pool would lose the accepted shell/service composition.
Shrinking scratch would violate the accepted RNPGv3 immutable snapshot.
Neither is an acceptable workaround.

Required scope amendment, not applied: add only
`config/x86_64_bootstrap.ld` to BV allowed_files, and extend the final guard to
accept exactly270336 OR1056768 scratch bytes, keeping catalog1069056 and all
existing payload/separation/map-capacity assertions. Add a regression in the
already allowed test/test_x86_64_large_file.py that accepts both exact pool
pairs, rejects neighboring sizes and preserves every other linker assertion.
The independent --large-image outer ELF verifier and all five frozen gates
remain mandatory; runtime14 guests, quotas and authority remain unchanged.

AGENTS.md package protocol4 and this contract require a scope stop for an
additional source file. No linker modification, scope expansion, implementation
commit or acceptance is performed. Visible candidate edits/evidence are retained.
Spent reservations: hosts4/12, builds2/4, media0/2, diagnostics0/6; no reset.
Signed media, complete service host coverage, runtime oracle and all gates remain
outstanding. Resume requires the explicit one-file scope amendment above.


## Approved scope amendment (2026-09-23)

The user's renewed instruction immediately after the concrete one-file request
approves config/x86_64_bootstrap.ld in BV. The scope stop above is historical.
Only the final eight-owner guard gains the already admitted1056768-byte scratch
alternative; all earlier exact payload, layout, overlap and capacity assertions
remain byte-for-byte unchanged. Add actual linker regression for the two exact
sizes and neighboring invalid values. Preserve all spent counters and frozen
gates. Continue the existing visible candidate without a new implementation
package or resetting baseline2cf5228a.


## Continuation evidence after approved linker scope

Host05 reproduces exactly the rejected large scratch pair1.206s. The single
linker correction preserves all other assertions byte-for-byte. Build03 passes
22.685s (layout5 outer ELF,1382936 bytes), all ordinary tools and v3 services.
Host06 verifies the corrected linker with18 actual links and existing captures;
its additional service compile fails because the test omitted LARGE_IMAGE.
Host07 corrects that test selection: service lifecycle versions1/2/3 at O0/O2,
all old injected creation/cleanup/control failures and wrong-version entry
rejection, plus independent2k/4k EXT2 consumer mutation tests pass3.308s.
Media01 passes3.334s: signed BIOS and complete nine-file2MiB data volume,
including exact1MiB largetest, independently verified before index publication.
Host08 actual capture passes both new multi-file EXT2 layouts at O0/O2 and
all existing size/layout/failure combinations12.907s; its source projection
fails on the projector's retained-elif/#else handling. Host09 corrects only
that projector and passes0.659s, proving the twelve selected C/header files
retain old behavior source modulo named equivalent local adapter substitutions.
No package acceptance or guest qualification is implied. Diagnostic01 has a
reserved300s bound and serial-only results cannot satisfy runtime gates.
Counters now: hosts9/12, builds3/4, media1/2, diagnostics1/6. Histories retained.


## Architectural scope stop: frame-validation stack overwrite

Diagnostic01 boots the signed BIOS medium, verifies the kernel signature and
reaches C handoff, but never starts the shell: EXCEPTION_FATAL pio=1. Serial-only
attempt expires297.703s. Its data-medium after-check passes; the boot-medium
after-check cannot run after its expired helper deadline, so no complete
no-write qualification is claimed. It remains a failed attempt.
Diagnostic02 captures scheduler_fail in mode8 with user-access result-4096,
0.963s. Diagnostic03 over-instruments early tests and instead catches a mode5
failure4.065s; retain it as non-equivalent, not evidence for the later cause.
Diagnostic04 arms probes only at process-run entry and captures the real mode8
user-access mismatch0.971s: current CR3/task root0x100033000 versus recorded
page-table root0x10006c000. Diagnostic05 directly brackets process_run_frames64
on the actual scheduler kernel stack0.955s, demonstrating the overwrite:

- Stack capacity16384; invocation scratch8*261*8+64=16768 bytes.
- Actual entry leaves16056 bytes above stack bottom; scratch descends712 bytes
  below that bottom into the immediately preceding ownership/table metadata.
- Before: scheduler_table_frames[0]=0x100033000, matching current task CR3.
- After: scheduler_table_frames[0]=0x10006c000, while the task CR3 is unchanged.
- The frame checker returns1 despite having overwritten its own authority data;
  the subsequent independent access checker detects the mismatch and fences.

Raw registers, complete task bytes and before/after256-byte table snapshots:
`build/codex-agent/r83bv-large-file/diagnostic05/fatal.json`; exact built
instructions in build03/disassembly.txt. This is a kernel integrity defect in
the newly combined8-owner/256-page profile, not a service quota failure.
Four-owner BU requires8416 scratch bytes and did not exercise this combination.

Required additional source, not yet authorized/edited:
`arch/x86_64/proc/process_run.inc`, specifically process_run_frames64.
Concrete correction proposal: under the explicit large-image/task-pool profile,
retain a64-byte invocation-local negative filter, but on collisions compare the
frame against prior entries in the existing bounded task/table arrays instead
of copying every frame to an oversized stack vector. Preserve full-width exact
identity comparison, all frame/range/zero/live checks, all8 owners and261 frame
positions per owner. No heap, shared mutable scratch, new authority, increased
kernel/user stack, quota, weakened overlap check or parser change. Existing
profiles keep their original path. Fixed scan bounds remain explicit.

Add actual assembly host regressions within already allowed BV test files:
maximum live slots and sparse pages, cross-owner/table/stack aliases, zero/free
slots, high frames, scratch canaries, and read-only task/table state. Re-run the
measured guest bracket and complete all frozen package gates and fault matrix.
This is a proposed correction, not a proof that it already works.

AGENTS.md protocol4 requires stopping for this additional source. The earlier
one-file linker approval does not silently add scheduler sources. Preserve the
current visible candidate; no implementation commit or queue completion.
Spent reservations: hosts9/12, builds3/4, media1/2, diagnostics5/6. No reset.


## Approved frame-scan scope amendment

The user's renewed continuation after the explicit process_run.inc request
approves that one additional file and the documented64-byte-filter/prior-entry
scan correction. The stack-overwrite scope stop is historical; preserve all
failed attempts and the baseline. Frozen acceptance remains unchanged.
Use remaining host10..12, build04 and diagnostic06 for the focused correction;
reserve a new finite evidence-directed window only if necessary, without resets.


Frame correction host10 reproduces the stack-canary overwrite0.476s; host11
retains an unsupported NASM defined() syntax failure0.151s. Nested existing
ifdef syntax corrects only that selection. Host12 passes actual assembler at
O0/O2, all0..8 owners dense/sparse,18 cross-position aliases, high frames,
missing/unaligned/out-of-range/root aliases, unchanged arrays and256-byte stack
canary envelope0.909s. Build04 and diagnostic06 use the original remaining
reservations. No guest correction claim until the actual bracket passes.

Following this evidence, reserve correction window02 for continuing the same
BV package: host13..20 (8 commands, each600s), build05..08 (4, each300s),
diagnostic07..12 (6, each300s), media03..04 (2, each180s). Media02 remains from
the original window. This is not a reset; all earlier failures and frozen gates
remain. Window covers necessary old-profile projection, corrected runtime
observer/transport, shell launch and qualification preparation. Scope remains
the approved files and no acceptance from diagnostic output alone.

## Continued correction and observer evidence

Build04 passes22.677s. Diagnostic06 passes0.984s on the actual kernel stack:
64-byte scratch,392-byte complete current stack chain, identical before/after
ownership tables and result1. Media02 passes3.308s. Host13 passes all six then
defined tests18.326s, including actual legacy assembler byte identity.
Diagnostic07 fails271.021s: both ordinary large consumers finish memory checks
but exit27 because terminal access has not yet been granted. Both media checks
pass; this remains a failed launch, not acceptance.

The consumer now uses the existing bounded terminal CHECK/sleep handshake and
console adapter. Build05 passes22.719s, media03 passes3.318s, host14 verifies
actual handshake code at O0/O2 with timeout/regression/overflow/sleep failures
0.774s. Diagnostic08 passes222.988s including process cleanup and both complete
medium after-checks: two ordinary1MiB launches, two LARGETEST_OK/exit0 results,
cat and normal shell exit in both generations. The inner diagnostic records
222.775s; the command receipt includes its full222.988s execution. It remains
qualification:false and does not replace any frozen runtime gate.

Host15 fails0.847s because the generated observer test omitted __file__.
Host16 supplies that module context and passes0.810s: exact mixed RNPGv2/v3
geometry with malformed version/extent/rights/reserved mutations rejected.
Host17 fails2.501s on a checked adaptation matching two occurrences instead of
one; host18 uses the exact complete leaf-read statement and passes2.543s.
The complete composed observer parses, private legacy modules stay unchanged,
all261 owned frames retain exact bytes/order, and over-capacity, duplicate and
unaligned frame lists reject before memory reads. Host19 passes0.311s: complete
disabled PowerShell/Make text and Python AST match the baseline after explicit
selector removal. No ABI or runtime acceptance is implied by source projection.

Current reservations spent: hosts01..19, builds01..05, media01..03,
diagnostics01..08. Window02 still permits host20, builds06..08, media04,
diagnostics09..12. The fourteen fresh qualification guests and five frozen
acceptance gates have not run. Remaining work includes complete case/record/
media binding, raw replay/fault policy and negative oracle mutations.

Host20 passes1.681s binding the actual build05 artifacts: two retained
266336-byte service records and four1052960-byte application records, complete
catalog/ELF/input pins and installed tool equality. No guest started.
With all20 original/window02 host reservations spent, reserve host21..28,
each600s, for the remaining same-package media and raw-verifier corrections.
Build/media/guest reservations stay at their existing counts and bounds.
No gate or failure counter resets. The FAT extension reuses existing fixed
geometry and chain production with the explicit nine-file set and a separate
consumer; no filesystem implementation, runtime quota or format change.

Host21 fails21.949s on the new FAT media extent check: largetest has nine
characters, exceeding the unchanged FAT short-name producer's8.3 format.
The BV adapter therefore explicitly installs `LARGETST.PRG` on FAT12/FAT32;
EXT2 retains `largetest.prg`. This is a documented media-layout name mapping,
not an LFN implementation or hidden shell alias. Generated file sets, separate
consumer, actual C path lookup and runtime record-name admission use it.
Host22 passes17.537s: independent four-layout nine-file media mutations and
actual O0/O2 capture on all prior size/layout cases plus the new multifile
EXT22k/4k and FAT12/32 cases. Full1MiB FAT32 remains the explicitly expected
deadline rejection; success is not claimed for that case.

Host23 passes0.472s: independent executable wire reconstruction through STAT,
contiguous READs and terminal EOF before CREATE-v7. The1MiB boundary accounts
for4098 calls. Mutations removing EOF/STAT/publication, reordering reads,
changing bytes/count/version and exceeding the original120000ms deadline all
reject. Runtime start replay invokes this proof for every ordinary child.
This is a host oracle regression, not a replacement for fresh guest evidence.
Current spent counters: hosts23, builds5, media3, diagnostics8. Host24..28,
build06..08, media04 and diagnostic09..12 remain reserved; gates remain unrun.

Host24 passes21.031s: the EXT2-1k negative fixture now uses all three required
double-indirect leaves for1MiB, with exact file bytes, disjoint pointer/data
blocks, sector accounting and allocated bitmap bits independently checked.
The former single-leaf producer inherited from the smaller profile could
overwrite adjacent pointer storage. This host-only fixture correction keeps
the unsupported parser operation as the rejection reason. Actual capture
still rejects it at O0/O2; no double-indirect filesystem support was added.

Host25 passes5.469s composing the complete raw reference observer, exact
largetest/cat command order, inherited file-object/CPU/PIO/IPC/fencing proofs
and new full executable capture proof. Diagnostic09 fails5.675s during boot
because the unchanged binary transport rejects a read above270336 bytes.
The BV wrapper now divides an at-most1056768-byte logical read into at most
four original bounded reads. It preserves transport deadlines, aggregate
capacities, equivalence and stopped-VM checks, and aborts immediately on a
short or failed read. Host26 verifies those failures plus composition5.709s.

Diagnostic10 advances to actual syscalls, then fails5.718s because the cold
read-only identity/terminal hook rejects the enlarged32768-byte task snapshot.
Preserve its strict less-than32768/non-QMP guard: capture the authority table
as two contiguous16384-byte reads in the same stopped callback, followed by
the original512-byte family table. Host27 verifies the exact assembled33280
bytes, read sizes/order and complete observer5.023s. Diagnostic11 uses the next
originally reserved300s attempt; no unchanged retry and no relaxed safety gate.
Current spent reservations include hosts01..27 and diagnostics01..11 (11 in
progress when this entry was recorded); build/media counts stay5/3.

Diagnostic11 fails36.144s after the first root retires: both actual FS children
receive CPU-quota status256, and no foreground application is constructed.
The finish assertion correctly rejects this outcome. The serial-only signed
BIOS success remains separate evidence; no CPU quota or acceptance predicate
is widened. Next use the already qualified portable WHPX toolchain and the
already frozen hardware-image variant to investigate observer timing.
Build06 passes25.671s with NativeLargeFile/NativeMathHardware; kernel1383472
bytes. Host28 fails0.088s before imports on a nested-string newline error in
the command harness; no guest or observer claim. Preserve that failed receipt.
Reserve host29..36 (8 additional commands, each600s) to finish hardware/raw
observer preparation and negative replay. Existing remaining build07..08,
media04 and diagnostic12 reservations stay unchanged. No counters/gates reset.

Host29 corrects only the command harness's raw nested string and passes11.560s:
qualified portable binary/firmware binding, actual build06 image/record inputs,
complete generated WHPX observer Python and exact normal command-order proof.
The accepted hardware transport/bootstrap is privately rebound; only the
unrelated text application's checkpoint is removed because BV observes its
own image/capture lifecycle. Diagnostic12 is the reserved300s WHPX raw reference
attempt, not an acceptance case or replacement for signed BIOS coverage.

Diagnostic12 fails71.850s after12738 decoded events during the first capture:
serial reports EXCEPTION_FATAL vector=20 (hexadecimal PIT vector32). No
foreground image was published. This is not a successful normal run or a
virtualization-exception claim. Timer source inventory shows explicit progress,
context and deadline rejection paths leading to the fatal timer handler.
No timer/scheduler/clock source is changed without a concrete cause and scope
review. Freeze diagnosis window03: diagnostic13..16, four additional guests
each300s, retaining all twelve spent attempts. Diagnostic13 adds read-only
failure-only progress/context/abort probes to retain registers, timer lease,
tick/EOI counts and current slot; it may stop at the failed path with no guest
state writes and cannot qualify. This is an evidence-directed safety diagnosis,
not permission to lengthen a timer lease, change guest clocks or bypass a gate.

Diagnostic13 exhausts300.032s (outer result124), with no timer failure probe
triggered. The old wrapper began its internal lease after configuration, so
outer timeout could precede its cleanup. The retained uniquely path-bound GDB
process5080 was identified and terminated; no matching VM remained. Future BV
raw diagnostics now start their single lease before configuration/binding.
This correction does not relabel the timeout or claim normal guest cleanup.
Host30 fails0.335s on postmortem CRLF decoding; host31 normalizes the retained
text exactly like prior replay and passes5.143s. Separate post-timeout audit:
62967 complete events,1422 reads/364032 confirmed file bytes,40860ms guest time,
zero foreground starts, no partial trailing record, unchanged raw hash and
zero allocated overlay data, exact qemu-img logical comparison. Raw trace
SHA256 b634eb23c8b703b3ff66288a66e2e1699e4ca44c93c555d8a777275fe47062a2.
Post-timeout audit is not in-lease acceptance. Complete proof throughput remains
insufficient; do not broaden the300s gate or reduce raw evidence requirements.
Use reserved diagnostic14 for a host-only cProfile sample ending at1024 command
probe callbacks, explicitly quit75, no guest clock/register/policy changes.
The sample must identify the bottleneck before any transport redesign.

## Scope decision: bounded host observation transport

Diagnostic14 deliberately exits GDB75 at1024 command-probe callbacks28.140s;
the wrapper returns1 because this is not a completed guest. Recorded cleanup
0.078s and the medium after-check pass. Its actual cProfile sample contains
1793483 calls in23.533s:2048/1024 GDB execute calls consume9.094s exclusive;
23567 inferior read_memory calls consume8.397s; selected_frame/read_register
and stepped dispatch account for another2.6s. Thus17.491s, about74 percent,
is already attributable to execution/individual memory transport, before
the remaining per-stop Python overhead. This measured transport cost, together
with diagnostic13's364032-byte progress at the300s limit, motivates a different
observation transport. It does not establish the cause of diagnostic12's fatal
timer rejection or guarantee that a replacement will qualify.

Concrete proposed scope addition (not yet authorized or implemented):

- scripts/build_x86_64_large_file_observer.py: reproducible build/binding of a
  separate workspace-local portable QEMU variant from the retained source and
  toolchain, fixed commands/deadlines, hashes and complete owned-process cleanup.
- scripts/qemu_x86_64_large_file_observer.patch: bounded host-side recording at
  the existing fixed diagnostic probe sites, grouping stopped-context register
  and memory observations without a GDB roundtrip for every individual field.
  Fixed-capacity versioned records retain exact call/return order, full bytes,
  CPU state, real instruction execution/return evidence and lifecycle identity;
  overflow, incomplete reads or unknown sites fail closed. No dropped events,
  synthetic guest PC/clock changes, substituted success records or device access.
- test/test_x86_64_large_file_observer.py: actual transport behavior, capacity,
  truncation/order/identity mutations, exact reference-stream comparison and
  cleanup tests. The existing BV host gate invokes these tests; it is not replaced.

The existing allowed run_qemu_x86_64_large_file.py and verifier bind that new
transport to the unchanged independent replay. Preserve old QEMU binaries,
bindings and evidence; do not replace installed tools. No kernel, timer,
scheduler, ABI, application rights or runtime-resource enlargement. Keep all
five frozen gates, fourteen fresh guests, each300s/aggregate4200s, unchanged
120000ms capture lifetime and existing raw evidence capacity. The fatal timer
case remains unresolved until independently diagnosed and qualified.

AGENTS.md protocol4 requires stopping before these additional source files.
The earlier linker/process_run.inc approvals do not add host-tooling sources.
This is a scope decision, not a request to restart an administrative attempt
window. No proposed source has been created; the active BV candidate stays
visible and uncommitted. Completion/native64 acceptance must not be claimed.
Spent: hosts31, builds6, media3, diagnostics14. Remaining already reserved:
hosts32..36, builds07..08, media04, diagnostics15..16. Frozen gates unrun.

## Approved observer scope continuation

The renewed user continuation immediately after the concrete three-file request
authorizes those three observer sources. Existing linker/process_run.inc
approvals also remain effective. Queue inventory found that those two earlier
path amendments had been inserted into historical package lists instead of BV;
restore those unrelated lists and place all five approved additions in the
active BV allowed_files. This repairs scope bookkeeping, not past acceptance.
All current visible changes are attributable to this package and retained.
Use remaining host32..36 and build07..08 reservations for the transport boundary
first; no new guest until actual host behavior and source/binary binding pass.
The three-file scope stop above is historical; all other limits remain frozen.

## Observer transport implementation window

Host32 passes actual fixed-capacity C request/response behavior at O0/O2
(1.102s); host33 adds exact patch application/context mutations (1.060s).
Build07 rejects before compilation (unexpected nested response files): the
retained link command contains empty block.syms/qemu.syms. Build08 explicitly
validates/hashes those two empty inputs, compiles two isolated translation
units and relinks without modifying retained inputs; pass176.152s. It binds
source/header files, retained objects, tool and patch hashes and verifies
their preservation after linking. This is an incremental diagnostic build,
not a full source rebuild of the accepted QEMU distribution.
Host34 fails startup without useful stderr (5.781s); host35 adds the missing
stderr and identifies the WHPX-only binary rejecting TCG (2.090s). Host36
uses that actual supported accelerator and passes (2.167s): default disabled,
RAM bytes identical to standard physical RSP reads, malformed/replayed
requests rejected, absent RAM rejected, sequence preserved on error, and
both owned VMs terminated. These stopped VMs execute no guest instructions
and provide no BV runtime acceptance.

The extension uses standard GDB Remote Serial Protocol framing/checksums and
the private qreist-mem query, version1. At most32 ascending disjoint spans,
1536 raw bytes,1936 reply bytes,262144 requests. Addresses name only the
fixed kernel/direct-map profile; the server explicitly derives physical RAM
addresses, checks actual RAM regions and excludes RAM devices/MMIO. It does
not perform general virtual-address translation. Existing runtime mapping
and stopped-context proofs must remain authoritative. Replies retain exact
addresses/lengths/sequence/full bytes; all request fields are validated before
reads, all reads before publication. Partial read failure publishes no data
and does not consume sequence. No guest write or execution is added.
This bounded foundation alone does not yet replace per-field GDB reads.

Spent hosts36/builds8/media3/diagnostics14. Freeze host37..42 (600s each) for
client parsing, response/order/truncation mutations, composed observer and
binding checks; builds09..10 (300s each) only if evidence requires a corrected
tool build. Retain media04 and diagnostics15..16 (300s each). Diagnostic15 may
sample1024 callbacks with exact same-stop comparison before measuring the
batched path; no complete-guest claim from that sample. No unchanged retries,
counter reset or gate/runtime/resource changes. Complete BV gates remain unrun.

Host37 passes five observer tests3.857s: actual C at O0/O2, source/binary
binding, stopped WHPX wire equivalence and default-off behavior, exact patch
mutation rejection, and client response version/count/sequence/address/length/
order/truncation/hex mutations. A rejected response permanently closes that
client; no retry or partial cache publication. The composed observer seeds
only the existing ColdHook read-only same-stop cache. It preserves the32768
per-read exclusion, all raw replay, actual RET execution and register checks.

Diagnostic15 reaches its planned1024-callback stop/GDB75, wrapper1 at25.489s;
cleanup0.120s and media-after pass. Its first64 batched reads compare all bytes
against the original GDB reader in the same stopped context. cProfile:
17.419s versus diagnostic14's23.533s; read_memory17832 calls/5.157s versus
23567/8.397s; GDB execute7.050s versus9.094s exclusive. This sample shows
about26 percent lower measured observation time, not full guest acceptance
or a guaranteed throughput bound. Diagnostic16 uses the remaining reserved
fresh guest for the complete reference with batch reads and failure-only
timer probes, unchanged300s lease and independent replay.

Diagnostic16 fails the session feeder deadline at297.693s,18004 completed
RET records; cleanup0.262s and media-after pass. No timer-failure probe fired.
The packet batch alone is insufficient; do not run acceptance from this state.
Inventory the already recorded return targets before changing their lifecycle.
GDB continue and debugger breakpoint transport remain measured dominant costs.
Freeze a host-only reuse adapter with at most16 retained kernel return targets,
each still bound by actual stack target, code/caller bytes, enabled registration,
exactly one new hit, real RIP/RSP+8 and complete CPU/flags/CR3 equality.
Unexpected stops/hits, capacity exhaustion or stale registration fail closed.
The existing read-only guest contract, raw COLD_STEP_V1 sequence, independent
replay and WHPX physical-registration binding remain unchanged. Do not replace
RET with host emulation, inferred execution, register writes or stepi. This
changes debugger registration lifetime only, not the actual return proof.
Use existing hosts38..42 and reserve diagnostics17 (1024-callback sample) and
18 (complete reference only after host checks/sample) at300s each. Retain all
spent attempts and14 fresh acceptance guests/4200s aggregate; gates unrun.

The queue amendment's earlier substring search matched active_id instead of
the exact BV id line. Final parsed-TOML comparison repairs this deterministically:
all non-BV fields equal HEAD; only BV allowed_files gains the five authorized
paths. No other package is advanced or retrospectively changed.

Diagnostic16 inventory has exactly three return targets over18004 verified
steps (request11972, denied13, return6019). Host38 passes registration reuse,
stale/duplicate-hit/capacity rejection and prior observer checks2.577s.
Diagnostic17 fails5.770s after two verified RETs: a retained enabled target
also stops a helper return which did not enter a cold probe. The unchanged
outer one-RET assertion rejects that extra stop. Do not ignore/filter it.
Correction: retain the bounded GDB object but enable its target only during
the expected RET, disable in finally, keep the source registration enabled.
This removes source registration toggles while retaining the old exact target
arming window; WHPX performs its existing real exclusive step over the source.
Use host39 and reassign reserved diagnostic18 to a1024-callback correction
sample (not the complete reference). No complete retry without new evidence.

Host39 passes2.510s. Diagnostic18 reaches its planned1024/GDB75 stop at22.332s,
cleanup0.072s and media-after pass. cProfile17.035s (read_memory5.019s,
GDB execute7.585s); the small difference from17.419s does not establish a
material further speedup. Leave this adapter opt-in and do not spend another
full guest on unchanged throughput. Before a native recording design, host40
may perform a read-only WHvGetCapability(Features) inventory, inspect the local
declared API/retained backend and record exact host-tool inputs. No partition,
guest, mapping change or debugger predicate is authorized by that inventory.

Host40 read-only capability inventory passes0.114s: features0x2ff includes
DirtyPageTracking and WHvQueryGpaRangeDirtyBitmap is exported; DLL SHA256
07fec05320e576c3c3a65d2c87f055cafaff40bb1b6bb9b6e806db0f2870f947.
This reports availability only. Microsoft WHP's documented reference is
https://github.com/MicrosoftDocs/Virtualization-Documentation/blob/main/virtualization/api/hypervisor-platform/funcs/WHvQueryGpaRangeDirtyBitmap.md
(page-aligned mapped/tracked ranges, one bit per page, bounded bitmap);
the platform overview specifies changes since the preceding query. Host writes
cannot be presumed covered. Freeze a separate, disposable64KiB WHP partition
probe: host41 compiles the actual API harness (30s), diagnostic19 runs a fixed
real-mode store followed by HLT (15s), then checks exact dirty bits, query
clearing, host-write behavior and unmapped-range rejection. No REIST image,
filesystem, device, network or persistent VM. All owned mappings/vCPU/partition
must be released, and outer timeout kills only that harness. This is bounded
host observation-transport development, not native64 acceptance or permission
to install/modify the system hypervisor.

Host41 compiles the harness3.761s; diagnostic19 passes0.143s, real store/HLT,
exact page2 dirty bit, next query clear, host store invisible, unmapped query
80370305, all owned resources released. No production mapping changes made.
Before adopting a larger native recorder, host42 may inventory the existing
GDB's mmap/Windows pipe support with one paused WHPX VM (no guest instruction),
at most256 ordinary memory reads and30s per owned process. Standard RSP named
pipes would preserve the observer unchanged if supported and measurably useful.
TCP already forces nodelay=on in gdbserver_start; do not claim or retry a
TCP_NODELAY fix. No native recorder is implemented or accepted by this note.

Host42's saved result shows mmap available, but direct Windows named-pipe
attachment fails SetCommMask(error1); no memory comparison ran. Its wrapper
also fails printing a replacement character under CP1252 after cleanup; keep
that failure. The test used default WHPX irqchip, which separately logs MSI
injection failure at startup. A correction must select the already accepted
kernel-irqchip=off profile. Before native recording, freeze hosts43..46 at600s
for one transparent stdio-to-private-pipe relay and stopped-VM RSP comparison.
Relay bytes are unchanged, no parsing/event dropping, two fixed16KiB buffers,
2GiB transfer cap,300s lifetime/5s connection, no spawned descendants.
GDB's standard pipe-command transport avoids its serial-port SetCommMask path.
Compile the workspace-only helper from an explicit source embedded in the
approved observer builder; do not install it or alter accepted QEMU binaries.
No complete guest retry until this host transport comparison supplies evidence.

Host43 compiles relay01 (2.469s). Host44 passes256 standard TCP RAM reads
(0.062s), then GDB rejects the backslash command path; wrapper1 at1.382s.
Host45 uses forward slashes; TCP again0.062s, pipe handshake times out; the
parent-only taskkill fails after GDB exits. Closing the owned QEMU closes the
relay; subsequent process inventory finds no GDB/relay/QEMU process remaining.
Host46 uses documented overlapped duplex I/O and peer-first cleanup; TCP256
reads0.078s, pipe still fails vMustReplyEmpty at22.230s; wrapper1 at24.560s.
No pipe speedup or pipe equivalence is established. Preserve all failed logs
and relay C/binaries in ignored evidence; remove the unused relay builder.
Also remove the optional return-registration experiment from candidate sources:
diagnostic18 does not establish a material gain. Its generated observer remains
in its immutable evidence directory. The standalone dirty-tracking C harness
is retained under dirty-probe/probe.c rather than unused production test code.

Only the verified read-only batch path remains. Final host47..48 (600s each)
are reserved for retained observer behavior/binding and one complete cohesive
host regression after removing experiments. Enforce build hashing/inventory
inside the same295s work plus5s cleanup lease, complete DLL/source manifests
and64KiB tool-binding admission. Build08's proven176.152s build is retained;
these administrative guards do not change its QEMU binary. No additional
long guest, new native recorder or acceptance gate in this closing window.

Host47 passes all five retained observer tests3.897s, including incomplete
DLL/source manifests and boolean version rejection. Host48 passes all13
cohesive BV host tests43.542s (real C O0/O2, all media/capture boundaries,
actual assembly/stack canaries, linker, old-source/build projection, lifecycle,
terminal handshake and full-file oracle). These remain development evidence,
not frozen gates. The exact builder used by build08 is reconstructed and
matched to its existing recorded SHA256
459c027db8d14352de4e5c6143e6e39dcab7f94279213595a45c2b25f47c0470,
then added as observer-builder.py without changing any prior evidence file.
Future builds save that original source at build time. Reserve host49<=600s
for only the final builder-archive/source/binary binding admission check;
do not repeat the complete host regression.

## Decision required before native execution control

The approved three-file continuation covered a read-only observation transport.
That implementation is tested, but diagnostic16 proves it insufficient for the
unchanged complete reference300s window. The next proposed design would move
actual cold-probe continuation and return-breakpoint control from GDB into the
workspace-local QEMU verifier. This is execution control, beyond simply grouping
stopped RAM reads. Do not implement that change under the read-only permission.
AGENTS.md's standing continuation explicitly stops at new authority domains or
genuinely unresolved safety decisions; another attempt reservation alone does
not authorize this transition.

Concrete proposed authority, limited to the existing disposable local QEMU
qualification profile, same three observer sources and existing runtime adapter:

1. Default off, explicit per-VM opt-in, one vCPU, exact source/binary/symbol/
   image binding. Only the three existing cold request/denied/return sites and
   their validated actual return targets. No public network or physical media.
2. Fixed state machine: disabled -> armed -> source stop -> bounded complete
   memory/register record -> arm one actual target -> execute real RET ->
   actual target breakpoint -> record complete after-state -> disarm target ->
   resume. At most one in-flight return and262144 events. An unknown stop,
   changed generation/mapping, extra/missing hit, short record, capacity limit,
   observer exception or deadline closes the verifier and fails the guest.
3. Preserve actual instruction/caller bytes, real target hit, RIP/RSP+8,
   every general register, flags/CR3, chronological CPU/PIO/IPC observations,
   complete capture/frame/ownership/recovery/no-write evidence and independent
   negative-mutated replay. Keep creation/lifecycle/fault checkpoints observable.
   No fabricated events, copied-success results, guest register substitution,
   stepi shortcut, changed IRQ/timer/clock rules or widened guest resources.
4. Bounded host-side recording can replace per-field GDB traffic only after
   exact equivalence proofs. A RAM-delta approach must cover both hardware
   guest writes and QEMU/host writes; diagnostic19 explicitly proves hardware
   dirty tracking alone insufficient. Alternatively record the complete bounded
   required state directly at each stopped probe. No inferred unread bytes.
5. Debug breakpoint changes are restricted to the already validated diagnostic
   sites/return targets and use the existing physical-registration safeguards;
   no general application/device/DMA permission is added. The external300s
   watchdog owns complete QEMU/debugger/helper cleanup. All14 fresh acceptance
   guests,4200s aggregate,120000ms capture deadline and five gates stay frozen.
6. Before any qualifying run: actual C host state-machine/capacity/fault tests,
   source/binary default-off projection, independent corruption/truncation/order
   tests, then a fresh bounded calibration retaining both old and native raw
   observation. Prior failed guests remain failed; no native64 completion claim.

No native automatic execution controller has been implemented. BV source
changes remain visible and uncommitted; full runtime matrix/verifier CLI and
five frozen gates remain incomplete. QuickJS stays subsequent and R3.6b deferred.

Closing evidence: host49 passes the final builder/archive/source/binary admission
check0.869s. Parsed queue scope review finds34 changed files and zero outside the
active BV allowed_files; git diff --check passes. No GDB, relay or QEMU process
remains. HEAD remains2cf5228a; no implementation commit, push or frozen gate.
Spent totals are hosts49/builds8/media3/diagnostics19. Builds09..10 and media04
remain reserved but are not needed while the execution-control decision is
pending. The concrete request above has been presented to the user; silence
does not authorize native guest continuation.

## Native execution-control continuation authorized

The user's renewed `mach weiter bis alles fertig ist` directly after the
concrete decision request above authorizes exactly its six numbered bounds.
This supersedes the pending-decision status, not any failed evidence or gate.
Freeze hosts50..55 (600s each) for actual C state-machine/fault tests, adapter
and independent record validation. Retain unspent builds09..10 (300s each)
and media04 (180s); reserve diagnostics20..21 (300s each) for evidence-directed
native calibration only after host proof and exact source/binary binding.
No unchanged guest retry; no acceptance claim from calibration. Spent totals
remain hosts49/builds8/media3/diagnostics19 until each receipt is created.

First implementation step is a fixed-capacity native return-control core in
the existing observer header. Its platform callbacks must report real stopped
CPU state, validated original code/stack and physical binding, successful
target registration, durable complete records and target removal. Any failed
callback latches failure; only an explicitly initialized fresh verifier may
arm. Test this core before connecting it to QEMU stop/resume callbacks.

Host50 passes actual native return-controller C at O0/O2 (1.000s), including
all six callback failures, all preserved registers/physical bindings, three
sites, unknown lifecycle checkpoint handoff, one in-flight return, deadline
and262144-event exhaustion. This core is not yet connected to live QEMU.

Recorder design for this window: explicitly listed, ascending RAM page ranges,
at most32 ranges/8192 pages (32MiB shadow); physically read every selected page
at every before/after stop, compare exact bytes and emit complete changed
pages. First record reads/emits every page, including zero pages. This covers
CPU and host/QEMU writes without dirty-bit assumptions. No unread page may be
served by replay; out-of-envelope reads fail. The envelope limits observation,
not guest allocation. No kernel or guest quota changes. Private versioned
RBVT1/RBVF1 little-endian diagnostic stream; 2GiB output cap, IEEE CRC32 per
complete frame and strict sequence/phase/ascending-page/trailer validation.
Partial writes or reads latch failure, never publish a successful observation
or resume. Existing source/binary/image binding supplies provenance; CRC is
for stream corruption detection, not authentication. External300s lease owns
cleanup and the native core rechecks its monotonic deadline before resuming.

Host51 passes actual C complete-read recorder O0/O2 plus independent Python
replay/corruption tests (1.396s). Direct host writes, missing initial pages,
every read/write failure, CRC-repaired altered after-registers, capacity and
latched failure are exercised. Host52 passes the controller/recorder and exact
three-file patch application (2.164s). Build09 passes7.743s; host53 verifies
its complete binding and stopped-VM default-off native admission3.482s.

The native adapter now keeps CREATE132 entry/return checkpoints in GDB and
drains recorded cold calls before each existing lifecycle observer. First32
native RETs deliberately hand both real stops to GDB: every original observer
RAM read and all19 CPU values are compared at that actual stop and retained
as native-equivalence.jsonl. QEMU owns only the one real target breakpoint;
GDB never substitutes CPU registers or uses stepi. Thereafter the native
controller resumes via one bottom half after VM-stop notification completes.
Unexpected state, mapping, breakpoint ownership or record failure exits the
disposable QEMU with78; default remains disabled.

Host54 passes generated Python AST/order/guard checks0.270s. Build10 adds this
bounded calibration handoff; host55 verifies its source/archive/binary binding,
default-off admission and existing RAM transport3.522s. Hosts50..55 and
builds09..10 are now spent. Diagnostics20..21 remain reserved. Diagnostic20
will use hardware image06 and isolated QEMU build10; its outer process lease
allows295s work plus5s owned-tree cleanup, within the unchanged300s ceiling.
It remains development evidence, never a substitute for the frozen matrix.

Diagnostic20 fails5.028s at native admission, before any native trace file or
event. Cleanup0.061s and no-write audit pass. Its assertion did not preserve
the RSP reply, so the failing admission predicate is not yet established.
Use the remaining diagnostic21 for a concrete bounded reply/breakpoint/CPU
admission record with the same build10; change no admission guard or execution
behavior on speculation. Preserve diagnostic20 as failed. No gate has run.

Diagnostic21 fails4.663s with explicit E14. All admission checks preceding
fopen(path,"wbx") therefore pass; opening the fresh trace file fails before
native control is armed. Preserve that reply and the bounded breakpoint/CPU
inventory. Freeze hosts56..59 (600s each), build11 (300s), diagnostics22..23
(295s work/5s cleanup each) for an actual Windows CRT exclusive-create
reproducer, the minimal file-open correction if confirmed, binding/default-off
checks and the pending native calibration. No unchanged admission retry.
Spent totals hosts55/builds10/media3/diagnostics21; media04 remains unspent.

Host56 confirms the actual CRT rejects fopen("wbx") with EINVAL and the O0
exclusive-open replacement works. Its O2 fixture then fails because it reuses
O0's already-created file; the exact owned O2 process is terminated, result1
at56.303s. Correct only the fixture to remove its own completed file and
inherit the existing process-local noninteractive Windows test mode. Host57
passes both optimizations0.888s, including existing-file preservation and
missing-parent rejection. Native QEMU now uses its established qemu_open_old
with O_CREAT|O_EXCL|O_BINARY, then fdopen("wb"); fdopen failure closes the owned
descriptor. No trace overwrite, changed admission guard or guest rights.

Build11 passes7.627s; host58 passes binding/default-off/native adapter3.531s.
Diagnostic22 now admits successfully and records the RBVT1 envelope, then
fails7.287s on GDB's ordinary boot-hook step at0xffffffff8010166a, step=1.
This PC is outside all three native sites. The adapter incorrectly applied
the native no-single-step condition before handing an unrelated armed-state
stop back to GDB. Move that test after native-source selection and retain it
unconditionally for an in-flight native target. The core's existing unknown
armed-PC handoff test remains authoritative. Do not change CPU stepping.
Reserve build12<=300s for this exact correction; use remaining host59<=600s
for guards/binding/default-off checks and diagnostic23<=300s for calibration.
No additional authority, gate or guest-resource change.

Build12 passes7.567s and host59 passes binding/default-off/guard checks3.526s.
Diagnostic23 fails7.837s after its first complete32,569,648-byte cold-source
snapshot. Independent decoder admits that real before-state at denied site
0xffffffff80110001, return0xffffffff8010eca5. QEMU correctly rejects the next
stop: GDB requests step=1 at the target instead of a native actual-target hit.
The calibration path left GDB's own source breakpoint enabled during its
continue; restore the accepted old dispatch's disable-source/continue/finally-
reenable sequence. Keep QEMU's distinct target armed and its no-step check.
Add a bounded calibration-progress record before continuing so the exact
handoff stage survives a failed return. No native completion/equivalence claim.
Freeze hosts60..62<=600s and diagnostics24..25<=300s for this adapter correction
and evidence-directed follow-up, using unchanged build12. Spent totals remain
hosts59/builds12/media3/diagnostics23; no gate or implementation commit.

Host60 passes the corrected calibration adapter0.267s. Diagnostic24 reaches
all32 real before/target pairs and retained live RAM/register comparisons.
Host61 independently replays these bytes and rejects CPU/RAM mutations0.529s.
The guest then stalls after933 emitted cold returns while input remains
incomplete. Source inventory identifies a required synchronous dependency:
ConsoleFeeder.pump waits for actual CONSOLE_IO RX acknowledgements before
sending the next bounded chunk. Deferring console observations to a later
lifecycle checkpoint can prevent that next checkpoint from occurring.
Keep console15/20 entry and generation-bound return in GDB together with
CREATE132; no feeder acknowledgement may be fabricated, skipped or sent early.
This is an observation/control ordering correction, not a guest quota change.
Reserve hosts62..65<=600s, builds13..14<=300s, and diagnostic26<=300s in
addition to unspent diagnostic25. Diagnostic24 keeps its original watchdog
and immutable result; no parallel second guest or unchanged retry.

Diagnostic24 times out299.446s; outer taskkill is denied, but the inner owner
finishes cleanup2.088s and no-write replay passes. No QEMU/GDB remains.
Build13 and host62 binding/default-off/adapter3.552s pass. Diagnostic25 fixes
the input dependency and progresses through real file RPCs, but times out
297.607s with1,297,713,472 bytes of native trace; inner cleanup0.221s and
no-write audit pass, no surviving QEMU/GDB. Native observation remains too
expensive; no gate or healthy full-reference acceptance.

Next bounded correction uses remaining build14/diagnostic26 and hosts63..65.
Inventory: cold callbacks read kernel mechanism/IPC/trace state below2MiB and
actual user pages through upper-RAM page tables. Scratch, allocator ledger
and heap-state bulk are read by the retained live lifecycle hooks. Narrow
the native low-RAM envelope to1..2MiB, retain the full16MiB upper envelope,
and reject every replay read outside the explicitly recorded pages.
Translate and validate each complete RAM range once per stopped record under
RCU, then copy every page from those same-stop RAM mappings. No cached mapping
survives a stop; no MMIO fallback, inferred RAM or change to guest allocation.

Append diagnostic RBVT2/RBVF2: each changed4096-byte page carries an explicit
64-bit mask and the exact changed64-byte blocks. First snapshot requires all
bits/all pages; unchanged blocks come only from an earlier complete snapshot.
Every physical page is still physically read and compared at every stop.
Existing v1 decoder and all original evidence remain supported. This bounded
private delta representation addresses measured trace amplification, not a
public ABI or persistent guest-format change. Keep the2GiB stream cap and
IEEE CRC32, replacing only its bitwise implementation with a fixed lookup
table. Actual C O0/O2, both-format replay, CRC-repaired mutation tests and a
fresh32-stop live comparison precede any runtime acceptance.

Host63 passes v2 actual C O0/O2, v1 real-record compatibility, independent
corruption tests and adapter checks2.472s. Build14 and host64 binding/default
off3.511s pass. Diagnostic26 still times out299.502s, but trace storage falls
to313,231,280 bytes; actual guest progress reaches98440ms and3300 file READs.
QEMU CPU141.156s and debugger CPU100.422s show remaining costs on both sides.
No-write replay and inner cleanup2.084s pass; no complete launch or gate.

Use remaining host65<=600s for the native profiling adapter, and reserve
diagnostic27<=60s (55s work/5s cleanup) for a deliberate stop75 after at most
1024 cold steps, retaining cProfile and raw evidence. Do not repeat a complete
guest until this sample identifies the next cost. Tighten the outer GDB loop
to retain its original exactly-one-explicit-dispatch condition; native records
have their own independently replayed count and cannot excuse an unexplained
outer stop. No additional QEMU build, checkpoint authority or format is frozen
in this profiling window.

Host65 passes0.283s. Diagnostic27 reaches its deliberate debugger75 stop in
16.554s, cleans0.065s and preserves no-write evidence. cProfile11.527s:
GDB execute7.436s (includes guest/native execution),8108 live RAM reads1.683s,
native stream decoding0.166s and old semantic encoding0.458s. The native path
roughly halves the earlier23.533s sample; storage is no longer the main issue.

Freeze hosts66..69<=600s, build15<=300s, diagnostic28<=300s. Keep the current
17MiB observation envelope; do not shrink upper RAM on guesswork. The next
change removes only unused after-RET RAM capture beyond the32 live calibration
pairs. The accepted old RET proof consumes all actual CPU registers, real
target hit, RIP/RSP+8 and physical bindings, not a second complete RAM image.
Native C still reads/revalidates source opcode and all three current mappings.
Append RBVT3/RBVF3 with an explicit FULL_RAM flag after the fixed CPU metadata.
Before records and first32 after records remain complete RAM snapshots.
Later after records are explicitly CPU-only: zero page updates, no successful
RAM read API until the next actual full snapshot. Never infer unchanged RAM
from this record. The next before record physically rereads every selected
page and compares against the last actually read snapshot; both guest and
host writes remain covered. v1/v2 replay and all old evidence remain readable.
Required host tests include actual C read-call counts, host writes between
CPU-only and next full record, denied after-memory access, version/flag/order/
truncation mutations and preserved real-target/register checks.

## Closing native-controller evidence and proposed WHPX scope

Hosts66/67 pass the v3 C/replay/adapter and bound-build/default-off checks
in2.608s/3.509s. Build15 succeeds. Diagnostic28 still fails the full reference
deadline in297.620s; inner cleanup takes0.219s and media-after reports passed,
zero allocated overlay data. Outer taskkill was denied; this is not a successful
external-watchdog cleanup proof. Host68 passes all13 BV host regressions28.128s.
Host69 independently validates diagnostic28's32 real before/after calibration
pairs and negative CPU/RAM mutations0.444s. These are development checks, not
the frozen acceptance gates. Totals: hosts69, builds15, media3, diagnostics28
spent; media04 remains unused. No qualifying full raw run or implementation
commit. The full verifier CLI, fourteen-case matrix and five gates remain open.

Source inventory: system/cpus.c do_vm_stop disables guest ticks, pauses CPUs,
notifies observers, then drains and flushes block devices. The current native
hook runs inside that observer notification and schedules restart afterward.
The relative cost of this global-stop path has not yet been measured separately;
profiling alone does not establish it as the dominant bottleneck.

Proposed scope addition, requiring explicit approval under the frozen three-file
QEMU source restriction: target/i386/whpx/whpx-all.c in a new workspace-local
bound verifier build only. Keep the existing three observer sources, builder,
runtime adapter and tests; no guest authority or public ABI changes. Do not edit
accepted verifier sources or binaries. The builder must bind and rebuild this
fourth translation unit and preserve the default-off source/binary projection.

First phase: bounded monotonic timing counters at actual WHPX debug exits and
the existing native source/target callbacks. One fixed-size result at teardown;
no per-event formatted logging. This must separate VM transition time from
snapshot/guest execution before selecting a correction. Reserve, only after
approval, hosts70..73<=600s, builds16..17<=300s, diagnostics29..30<=60s each
(55s work plus5s cleanup). No further full300s retry is reserved here.

Any subsequent fast path is limited to the same three cold sites and their
actual return targets, one vCPU and one in-flight return. It must preserve
physical-breakpoint restoration, balanced CPU/exclusive state, BQL/RAM-write
quiescence, frozen virtual-clock and pending-IRQ ordering, actual RET execution,
all register/mapping comparisons and the32 live calibration pairs. CREATE,
console, lifecycle, faults and unknown stops retain the old GDB path. A running
guest clock during observation or merely holding the vCPU is not equivalent
to the existing stop and cannot qualify. No implementation of an alternate
stop protocol until these invariants have a concrete reviewable design and
tests; unresolved clock/quiescence semantics remain a safety stop. Approval of
the additional source does not waive that stop or any acceptance gate.

The user's renewed continuation immediately following this concrete proposal
approves the fourth-source scope. Activate the reserved hosts70..73, builds16..17
and diagnostics29..30; no fast-path protocol change is selected. Timing remains
separately opt-in after native admission. Measure WHPX debug-exit to native
notification, native callback, and callback-to-resume-bottom-half intervals.
All callers hold BQL. Emit one fixed aggregate after256 automatic native stops
instead of teardown, because the owning debugger deliberately terminates the
sample; after that no further timing accumulation/output. This is a measurement
window, not per-event logging or a modified guest clock. Test disabled behavior,
exact arithmetic, backward timestamps and saturation using the actual C code.

Host70 passes actual C timing/controller/recorder, adapter and exact patch2.858s. Build16 fails at the new WHPX TU: relocated source cannot find sibling whpx-internal.h. Preserve the failure; add the retained source parent as an explicit quoted-header lookup (all its headers already hash-bound). Use reserved build17 for this correction; no guest attempted.

Build17 and host71 bound-binary/default-off/adapter checks pass (host3.566s).
Diagnostic29 reaches its planned debugger75 in15.821s, cleans0.079s and passes
no-write. Measured256 automatic stops: entry5731us, controller255368us,
tail11367us. Global stop transition costs are small in this sample; do not
introduce an alternative WHPX stop/clock protocol on this evidence.

Next conservative correction: eliminate the redundant4096-byte staging copy
for unchanged RAM pages. Retain the entire17MiB envelope, actual physical read
and exact memcmp at every full stop, CRC/delta format and before/after rules.
The pinned same-stop RCU RAM view may supply a const page pointer only during
bv_snapshot_record; no mapping survives callback return. Keep the old copying
reader as the host/fallback adapter and compare complete emitted bytes under
both paths, including host writes, read failures and CPU-only after records.
Reserve build18<=300s; hosts72..73 and diagnostic30<=60s remain unspent. No full
runtime retry or reduced observation coverage is authorized by this correction.

Host72 passes byte-identical copying/pinned recorder O0/O2 plus controller,
patch, adapter and timing tests4.173s; build18/host73 binding3.565s pass.
Diagnostic30 planned75 in15.284s, no-write passes. Controller sample214769us
versus255368us before (about16% lower); transition5740+10574us remains small.
Do not repeat the full reference for this modest gain alone.

Freeze hosts74..78<=600s, builds19..20<=300s and diagnostics31..32<=60s each.
Evidence-directed sparse capture: retain the17MiB maximum envelope but append
RBVT4/RBVF4, with a CRC-covered page availability bitmap for each full record.
Physically read all low1..2MiB pages and all eight current task page-table chains
plus every present leaf in their fixed0x400000..0x4fffff image. The accepted
cold observer's user(), file_leaves(), syscall()/complete() read through these
chains; other cold trace/state/caller bytes reside in the retained low range.
No page selection from hardware dirty bits or a previous task generation.
Recompute selection at each full stop under the same RCU/BQL guard, bound to
8 tasks,4 tables per task,256 leaves each. Out-of-envelope/large-page/missing
parent mappings fail closed. No semantic kernel validation is replaced by this
selection: the unchanged observer validates the recorded bytes independently.
Every selected page is physically read. Unselected cached bytes remain
unreadable; first-ever selected pages require complete contents; reselected
pages compare actual RAM against previously recorded bytes. Host writes remain
visible. CPU-only records still expose no RAM. v1/v2/v3 decoding is retained.
Test actual selection bounds and malformed tables, first selection, unselect,
reselect after host write, denied unavailable reads, CRC-repaired bitmap/data
mutations, and byte-identical selected bytes before any fresh guest. No full
runtime retry in this window and no weakened guest clock or acceptance gates.

Host74 passes sparse selection, unavailable-page and CRC-repaired mutation
checks plus prior recorder/controller/adapter4.691s. Build19 and host75 binding
3.630s pass. Diagnostic31 planned75 in13.997s:256-stop entry4892us, controller
37082us, tail5912us. Host76 independently verifies its32 live before/after pairs
and negative mutations0.300s. Native observation cost is about85% below the
original timed sample; this is not a complete runtime acceptance.
Reserve diagnostic33<=300s (295s work/5s owner cleanup) for one full reference
with build19 after this measured correction. Diagnostic32<=60s remains unused;
hosts77..78 and build20 remain unused. No unchanged retry, gate or counter reset.

Diagnostic33 exits71 after276.179s, cleanup0.067s and no-write pass. The first largetest is rejected; cat and shell exit still work. The finish assertion is independently traced to inherited592-byte/576+580 ELF-context geometry, whereas BU NATIVE_IMAGE_RECORD is2320 with the four-byte diagnostic counter at2304. Correct both live collection and independent replay to14 contexts of2320, preserving every other zero requirement. Add actual AST-executed first/last-byte/flag/padding corruption tests; do not label this observer mismatch kernel corruption. Use unspent host77 for the complete updated BV regression. Host78's bounded8MiB tail analysis passes1.241s and retains service cleanup evidence; it does not yet identify the initial capture error.

Reserve host79<=600s for bounded streaming analysis of complete diagnostic33 root IPC/FS errors (at most16 summary records), before choosing another runtime correction. No additional guest or build.

## Decision required: repeated start and PIO observation sites

Host77 passes all13 updated BV regressions32.436s, including actual execution
of live/replay ELF-context cleanup predicates and corruption of the enlarged
records. Host79 streams the full diagnostic33 log10.060s: at119940ms the root
still requests data at offset1030656, shortly before its capture limit; the
guest subsequently rejects largetest, recovers services, runs cat and exits.
No completed large-file launch is proved. The source context-size correction
is host-verified only; diagnostic33 remains failed and immutable.

The remaining live observation is material: diagnostic31's profile records
307 start callbacks and408 other live Hook callbacks during the1024-cold-step
sample;7907 live RAM reads cost2.066s including the reader adapter. Native
capture costs fell from255368us to37082us per256 automatic stops, but this
does not remove those synchronous GDB callbacks. There is no evidence to
justify changing the VM clock, capture deadline or scheduling policy.

Concrete proposal, not implemented: extend the native diagnostic controller
from the three approved request/denied/return RET sites to the existing two
additional read-only sites native_session_probe_start_site64 (bound image06:
0xffffffff80110003) and native_session_probe_pio_site64 (0xffffffff80110004).
Both are actual RET instructions on the existing diagnostic page. Start is
called by cooperative_scheduler.asm after process_ipc_take64; repeated starts
observe actual blocked-IPC completion. The PIO site returns from
native_session_pio_return64 after each32 recorded operations. No kernel edit,
probe frequency change, general breakpoint or new application right.

One cohesive extension in the same four QEMU sources, builder/runtime/test
files: version the private admission query, bind all five sources and actual
CALL/RET targets, retain one in-flight target, unchanged262144-event cap,
monotonic lease, IF/register/mapping checks and failure termination. Preserve
the original three-site mode for comparison. For each newly admitted site,
require live before/after register and every consumed-RAM comparison before
asynchronous qualification, including independent malformed-record replay.

First task entry, new/reused/unknown generation and every startup mutation stay
in GDB. A bounded eight-slot acknowledgement from the completed live start
callback binds each admitted slot/generation; stale acknowledgements fail.
Blocked CREATE and console15/20 completions also remain synchronous. Native
replay invokes the unchanged start/drain callbacks in exact order with the
recorded state, so pending IPC and PIO rings are not skipped or fabricated.
Fault injection, task creation, release/fencing, terminal handover and unknown
stops retain their current live path. The extra PIO site must use its actual
helper binding, not the naming convention for request/start probes.

AGENTS.md and the earlier explicit "only the three" execution-control grant
require approval before enlarging this controlled-PC set. The WHPX source
approval authorized measurement, not these extra execution-control sites.
Do not implement them from an attempt reservation alone. On approval, first
freeze a finite host/build/calibration window and test the five-site state
machine and generation handoff. All five acceptance gates,14 guests,300s
per guest,120000ms capture, IRQ/clock semantics and old evidence remain fixed.
No claim that the proposed extension will necessarily satisfy the deadlines.

Current spent totals: hosts01..79, builds01..19, media01..03; diagnostics01..31
and33. Diagnostic32, build20 and media04 remain unspent. HEAD2cf5228a, no frozen
gate or implementation commit. Full matrix/verifier CLI and native64 completion
remain outstanding; no push or nested agent.


## Approved five-site implementation window (2026-09-24)

The renewed continuation immediately following the concrete two-site request
approves repeated start and PIO execution control within that proposal. Freeze
hosts80..85<=600s, builds20..21<=300s, diagnostics34..35<=60s each (55+5).
Old diagnostic32 remains unused; no full300s guest is reserved in this window.
First implement/test the bounded3/5-site core and eight-slot generation
acknowledgement, then the versioned query and actual GDB handoff/calibration.
Source inventory shows PIO uses the caller of native_session_probe_return64
via a tail jump, so PIO and return share an actual return target. Five-site
mode permits that exact target sharing with one in-flight physical breakpoint;
source PCs remain unique and disjoint from every target. Three-site admission
retains its original distinct-target rule. No additional probe or kernel edit.

Host80 fails as expected on the missing five-site/acknowledgement API0.277s.
Host81 passes actual3/5-site C, every after-register on all five sources,
shared-target admission, stale/foreign/replayed acknowledgements, old recorder
and sparse/adapter regressions5.554s. Keep three-site query-v1 and RBVT4;
five-site query-v2 selects RBVT5/RBVF5 with160 consecutive live calibration
pairs and full after-RAM for those160. Before asynchronous continuation, all
five site bits must have been observed; missing coverage fails closed. The
independent replay requires the same full five-site coverage and160 exact
CPU/RAM comparisons. New five-site RET evidence uses NATIVE_STEP_V2; it must
not be passed off as the old three-site COLD_STEP_V1 proof. Runtime matrix
integration of this appended evidence remains required before any acceptance.

Host82 passes C behavior but fails the old source-pattern assertion expecting literal3 at unknown-PC handoff. Update it to site_count, retaining the ordering before singlestep rejection. Add actual RBVT5/RBVF5 O0/O2 through162 pairs, proving the160/full-after cutoff and denied CPU-only reads; no change to runtime guards.

Host83 passes controller/adapter but the162-pair recorder fixture exhausts its old65536-byte host-only sink. Increase only that extended test fixture to262144 bytes; production2GiB trace bound and all guest limits remain unchanged. Preserve the failed test.

Host84 passes controller/acknowledgement, RBVT5 through162 pairs, old pinned
records and both generated adapters5.845s. Build20 passes and host85 verifies
binary/default-off/adapter3.721s. Diagnostic34 reaches planned75 in15.224s:
160 live pairs cover all five sites, no-write passes; independent160-pair audit
is still pending. User now prioritizes a native64 VMware package for visual
inspection. Pause BV runtime expansion at this preserved uncommitted state;
no gate/commit, no discarded evidence. VMware delivery will use isolated copies
of previously accepted BI graphical artifacts, not this unfinished BV image.


## Desktop dependency resume after BX3b829aee (24.09.2026)

BW5f0debf9 and BX3b829aee qualify the real desktop host port and fixed8MiB
startup workspace. Its897542 static section bytes exceed the graphical RNPGv2
span, making the already approved large capture/image path a real desktop
prerequisite.32 BV files restored byte-exact from verified archive/stash;
accepted desktop changes and all evidence retained. Queue definitiondf9523be
reserves hosts86..91<=600s and one diagnostic36<=300s after positive160-pair
audit; existing build21/diagnostic35<=60s remain unused. No counter reset.

Host86 independently verifies diagnostic34's160 CPU/RAM pairs and negative
mutations0.990s. Host87 verifies all five routes against actual ELF32-container
CALL/RET bytes, shared PIO target, versioned complete NATIVE_STEP_V2 stream,
all receipt-field mutations and both generated adapters0.622s. The unchanged
old three-site path remains COLD_STEP_V1. Five-site fallback and final-count
receipts now use the same appended version; independent runtime evaluation
uses the actual kernel-derived routes, never relabelled v1 evidence.
Diagnostic36 uses build06 kernel/build20 bound observer, five sites, full
reference with295s work plus5s owner cleanup. No profile cutoff, clock/IRQ
change, quota increase, additional control site, acceptance claim or gate.

Diagnostic36 fails27.607s after1806 version2 step receipts: ordinary shell
starts largetest, guest emits EXCEPTION_FATAL vector20. Capture rejects
incomplete console input. This is not acceptance or evidence to relax timer
checks. Use the still-unspent diagnostic35<=60s with the existing read-only
timer-failure probes enabled (no profile cutoff) to capture the exact failing
branch/registers/state. Same kernel/bound observer/five sites;55s work plus5s
owner cleanup. All failure evidence retained; no unchanged retry.

Diagnostic35 fails18.639s with bounded cleanup0.094s and read-only timer
evidence: timer_runtime_progress64.fail r9=4, ticks=eois452, TSC48771866270
exceeds deadline43728534179. Exact cause is an overdue TSC lease, not counter
corruption. Whether accumulated GDB replay causes the pause is not yet measured.
Freeze diagnostic37<=60s (55+5) with existing failure probes and an explicit
default-off host-only native-drain timing sampler, at most128 records. Host88
checks generated adapters before running it. No kernel/clock/limit/control-site
change or new QEMU build; build21 remains unused.

Diagnostic37 fails17.973s with the same overdue branch. The explicit sampler
measures1575 accumulated native returns (sequence161..1735) replayed during
one GDB pause in1.953s. This supplies the missing causal timing evidence.
Keep the kernel TSC lease and every clock unchanged. Bound queued native
replay to64 completed returns by handing the next already admitted source
back to its existing GDB callback before another native record. No new site,
CPU mutation, skip, control-path alias or altered total262144 cap. Original
3-site behavior stays unchanged; five-site160-pair calibration is retained.
Host89 first demonstrates missing pure handoff helper, host90 checks actual
C O0/O2/helper/controller/adapter, reserved build21 builds the four-source
patch, host91 verifies the new binding. Reserve diagnostic38<=300s (295+5)
with failure probes/timing after those pass. Existing diagnostics35..37 stay
failed; no deadline renewal or VM clock correction is authorized here.

Host89 expected missing helper failure0.792s; host90 actual bounded replay/controller/adapter/patch tests pass2.809s. Host91 was incorrectly started while build21 was still running and fails0.408s because binary-binding.json did not exist; no guest started. Preserve this orchestration error. Build21 now finishes successfully in89.976s. Reserve host92<=600s for binding/default-off/adapter checks only after the completed build. Diagnostics38 remains unspent and conditional on those checks.

Host92 passes3.552s. Diagnostic38 fails235.539s at the host snapshot
envelope after the first complete1MiB LARGETEST_OK, cat and normal root exit.
No timer failure; the first128 replay samples take at most0.093s for64
events. Cleanup combines the1052960-byte import record with scheduler,
family and probe state, exceeding the erroneous1052960 per-record cap.
All checks preceding the write passed; this is not full cleanup acceptance.
Reserve hosts93..96<=600s for a regression-first private BV2MiB snapshot
envelope correction, emitted producer and independent reader boundaries,
exact cleanup size/zero checks and backlog regression integration. Retain
aggregate/count limits and every guest quota. No new guest is reserved:
the235s first-root duration requires further evidence-directed performance
work before the unchanged two-root300s reference can be attempted.

Host93 reproduces the cleanup envelope failure1.556s; host94 passes the
emitted writer/independent reader at combined cleanup and exact2MiB, rejects
2MiB+1 and mismatched semantic lengths1.917s. For measured steady-state
costs reserve diagnostic39<=90s (85s work/5s owner cleanup), same build06/21
and five sites, explicitly truncated cProfile at8192 native receipts.
Extend only the optional host profiler ceiling from1024 to8192; host95
checks adapter generation, rejection above the new bound, cleanup and
backpressure. This run cannot qualify; no guest/clock/recording limit changes.

Host95 adapter/backpressure tests pass1.135s. Diagnostic39 ends at the
planned8192 native-receipt profiler cutoff/GDB75 in41.610s, cleanup0.077s;
the capture wrapper correctly rejects this incomplete reference. Profile:
36.205s total,23.072s exclusive GDB execute (includes guest running/waiting),
9.227s cumulative native drain,3.072s evidence encoding. Do not attribute
all GDB execute time to debugger overhead. Existing block_dispatch's50ms
minimum sector spacing alone implies approximately102.4s for2048 distinct
sectors, per large capture, before metadata and observation. Preserve that
rate and both complete root generations. Host96 closes the envelope
regression with actual cleanup replay predicates (nonzero first/last byte)
and independently audits diagnostic39's160 calibration pairs. No full guest
retry, acceptance-gate attempt or desktop delivery is claimed.

24 September: user explicitly approves the concrete600s HOST-only complete
two-root verification proposal. Total matrix4200s and runtime gate5000s stay
fixed. Guest limits and all semantic proof predicates remain unchanged.
Reserve hosts97..102<=600s, isolated observer build22<=300s, diagnostic40
<=600s (595s work/5s owned cleanup), first failure stops. Before that guest,
bind all private BV host deadline layers consistently: capture/setup/reader,
fixture, native five-site controller, audit and external owner. Old three-site
controller stays300s. Bound two-root evidence at256MiB each for snapshots
and stored trace,512MiB aggregate memory evidence, unchanged512MiB decoded
trace,2GiB native trace and262144 event/record caps. Diagnostic38 measured
80746512 snapshot bytes and78361880 stored trace bytes for just one root,
so old128/256MiB envelopes cannot accommodate both full generations.
These are private host buffers, not guest memory/authority. Verify producer,
consumer and live feeder consistency, capacity rejection and old-profile
isolation before the one corrected full reference. No qualification claim.

Host97 first rejects600s as expected in the old native controller0.746s.
Host98 rejects an ambiguous source replacement1.484s (the shorter string
also matched console_started); exact setup-expression binding fixes it.
Host99 passes11.935s: actual O0/O2 five-site600s/600s+1 and old three-site
300s/300s+1 admission, controller/adapter, private capture factory compilation,
evidence codec/extent isolation and actual cleanup writer/reader predicates.
Build22 is the reserved isolated QEMU rebuild with explicit five-site600s
and old three-site300s controller limits; host100 must bind it after completion.

Build22 completes successfully; host100 binding/stopped transport/composed
hardware capture passes6.156s. Diagnostic40 was stopped after173.935s when
static follow-up discovered the remaining SessionFeeder elapsed<297 guard.
This was an incomplete deadline propagation, not a guest failure; retain the
partial raw evidence and stop receipt. Sandbox taskkill was denied; explicit
escalated owner-PID/tree cleanup succeeded. No desktop/acceptance claim.
Correct only that private feeder to597s and add actual boundary execution
at596.999/597, setup and expired fixture tests in reserved host101. Reserve
diagnostic41<=600s (595+5) after those checks, unchanged build06/build22.

Host101 passes9.030s, including actual feeder/setup/fixture deadline cases.
While diagnostic41 runs, finish the already scoped defaults entry point:
exact disabled source/build projection, accepted wide-file behavior and
hash-bound retained GUI/network/application/text/large-image artifacts.
Reserved host102 checks the artifact consumer's real changed-file/path/hash
rejection and projection only; it does not execute or count the frozen gate.

Host102 passes1.911s. Diagnostic41 captures both complete root sessions,
debugger exit0/success_marker at446.891s, cleanup0.073s; the overall diagnosis
fails472.713s at the inherited512MiB decoded-trace cap. Stored records declare
753230213 decoded bytes,363312 compressed records. Crucially guest console
contains only ONE LARGETEST_OK and one Bad command: the second large launch
failed. Completion markers therefore do NOT establish functional success.
Reserve hosts103..106<=600s for bounded streaming root2 IPC/error analysis,
correct private host decode capacity only if needed and independent replay.
No further VM reserved until the real second-launch failure is explained.
Preserve diagnostic41 as failed; do not substitute an offline review for gates.

Hosts103/104/105 streaming analyses pass37.091/37.750/34.295s without a VM.
First large FS generation issues4098 requests, exact EOF at1048576, times
850..118870ms. Second issues4088, last data offset1046016 at242260ms against
242290ms deadline; no FS error reply. First large launch succeeds; second
does not construct a child. The capture budget is exhausted near completion.
Existing kernel64 PIO calls/100ms and16-word transfer bound constrain faster
Ring3 pacing. The proposed separately granted128-call/25ms read-only profile
is written in NATIVE_LARGE_EXECUTABLE_PROPOSAL.md. Its kernel mediation files
are outside BV allowed_files: explicit architecture/scope stop pending that
resource decision. No pacing, guest deadline or kernel quota was changed.
Host106 remains unused; no new guest/build is reserved. The approved600s
host exception persists and is not requested again.

## Resume after accepted BY01d88a52

BY candidate08 passes all five gates, seven full WHPX guests and independent
raw replay. Its explicit root-only BIND-v3/128 calls per100ms is now available;
old BIND-v1 grants remain64. The user repeatedly authorized automatic completion,
including the concrete128-call/25ms proposal. Restore the35 archived BV files
from verified paused-bv-throughput/files.zip without replacing accepted BY:
retain current queue/docs and perform explicit three-way merges of Makefile,
the PowerShell wrapper and the program producer against archived df9523be.
Preserve the stash and all historical failures. No other package is active.

Select the accepted BIND-v3 constructor only for the existing new service
profile3, before starting its driver. That profile alone uses25ms subsequent
sector pacing, keeping the100ms first guard,120000ms capture,1000ms RPC,
200ms ATA,16-word transfers,CPU32/1000ms,8192 block/4098 FS calls and all
generation/fencing rules. Old profile1/2 retain their100/50ms behavior and
64-call grants. This explicit authorization supersedes the original profile3
50ms/64-call paragraph above, never the old public profiles or other limits.
Extend the private verifier's PIO state/tag decoder to the exact accepted BY
tag and bound its host decoded evidence at1GiB: diagnostic41 declared753230213
bytes, exceeding the former512MiB host envelope. This is host evidence storage,
not a guest memory/resource expansion; each raw semantic record stays exact.

Freeze hosts106–112<=600s, one native kernel build23<=300s, one signed media04
production<=180s only if required by changed byte bindings, and one full
reference diagnostic42<=600s only after targeted host/binding checks. Reuse
unchanged build22 observer binaries only after their existing hash/source
admission; no new observer-control site or debugger authority. Finish the
already allowed package/runtime/review verifier entry points and execute the
original five gates/14 guests,600s per complete guest,4200s total/5000s gate.
Diagnostic evidence is never substituted for those gates. No QuickJS or full
desktop claim yet; next packages follow only after clean BV acceptance.
