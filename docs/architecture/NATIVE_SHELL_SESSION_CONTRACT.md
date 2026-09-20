# Native shell/service session v1 — R8.3ay

Qualification complete, 2026-09-20: candidate17 passes all ten frozen gates,
18 fresh runtime cases, full independent binary-memory/raw replay and scope
review. Guest sum370.020897600014s. Actual normal Ring3 shell/service/file/
identity/terminal/wait boundary qualified, including all fixed recovery,
degraded, owner-loss, CPU, memory and OOM obligations. Seventh image reused;
zero new qualification builds. All old profiles/ABI/quotas/deadlines preserved.
Actual RET target hit/PC/SP/GPR/flags/CR3 checks with persistent insertion
replace unreliable implicit step progress; no deduplication or inferred return.
Total141 physical guests2862.51474020019s/seven images plus one prelaunch
0.38712120000855066s, including every retained failure. Acceptance seal:
`build/codex-agent/r83ay-shell-session/candidate17/acceptance-seal.json`,
SHA256 `08cc05c7442b00644aab4d9a61fa09a84409669e63f74221a6a8bbf6f611701a`.
This is not complete OS, hardware-platform or certification acceptance.
Historical diagnostic/qualification windows follow; none replaces this seal.

Candidate17: long case6 diagnostic38 fully passes36.573199900012696s with2437
actual RET target proofs and every old raw predicate. Promote only normal
always-inserted on and matching host expectation; all target/PC/SP/register,
flag/CR3/progress/capacity/cleanup guards stay exact. No build/tool/clock change.
Freeze ten gates/eighteen fresh45s guests incl3s cleanup/810s sum/900s runtime,
first failure stops; diagnostic pass is not acceptance. Preserve123 guests
2492.493842600176s/seven images and one prelaunch0.38712120000855066s.

Diagnostic38: candidate16 passes six gates/cases0..5; long case6 exceeds the
42s observation bound (44.178172000014456s incl cleanup),2429 valid RET target
proofs, no progress failure; debugger CPU25.90625s. Preserve122 guests
2455.920642700163s/seven images plus prelaunch0.38712120000855066s.
Only diagnostic insertion policy changes off->on, avoiding removal/reinsertion
of all other hooks at every stop. Existing own-hook disable/restore, exact
actual RET target hit, PC/SP/GPR/flags/CR3 assertions, finally deletion, full
raw predicates and normal observer remain unchanged. No claim based on older
mode-only diagnostics without actual target proof. Host red/green300s, one
long case6 guest45s incl3s cleanup/90s host, zero builds or deadline changes.
Reference: https://sourceware.org/gdb/current/onlinedocs/gdb.html/Set-Breaks.html

Candidate16: diagnostic37 passes cases2/13/15,962/821/751 exact RET target hits,
all original raw oracles,66.83003739998094 guestseconds. Promote only the
source-exact return-target wrapper into normal observation; unchanged image,
tools, callbacks, guards and validators. No trace or build. Full ten gates
and eighteen fresh45s cases incl3s cleanup/810s sum/900s runtime, first failure
stops. Preserve115 guests2273.6467948001523s/seven images plus one prelaunch
0.38712120000855066s. Diagnostic success alone is not acceptance; no commit,
queue transition or completion before all gates and full raw review pass.

Diagnostic37:36 fails early sleep self-test stage159 before any shell probes;
global TB-link output bypasses the address filter. No cause proof; retain
112 guests2206.8167574001714s/seven images plus prelaunch0.38712120000855066s.
Diagnostic-only alternative to observed nonprogressing stepi: disable only
current cold hook, create one internal hardware breakpoint at the saved RET
target, continue exactly once, require exactly one hit at the actual target,
delete in finally and restore original hook even on failure. Keep every
existing opcode/IF0/PC/SP+8/GPR/flags/CR3/pending/capacity guard and callback.
No PC writes, failed-step retry, deduplication, inferred return or tool change.
Normal observer remains unchanged; no QEMU trace. Fixed limits remain; real
target completion required. Host generated-code red/green300s first, at most
cases2/13/15 each45s incl3s cleanup/135s sum/240s host, first failure stops,
zero builds, no qualification promotion.
Reference: https://sourceware.org/gdb/current/onlinedocs/gdb.html/Breakpoints-In-Python.html

Diagnostic36 follows failed candidate15: six gates/two guests pass; case2
stops at actual one-RET progress, PC still at request site. Preserve111 guests
2203.9868998001916s/seven images and one prelaunch0.38712120000855066s.
Read-only upstream analysis suggests cpu_tb_exec can emit a debug exception
after restoring PC for an unexecuted TB; exact installed stripped binary is
not verified against that source. No asserted root-cause proof or tool repair.
Reference: https://raw.githubusercontent.com/qemu/qemu/master/accel/tcg/cpu-exec.c
Diagnostic-only exec log filters exactly the three fixed RET sites; add only
gdbstub_op_stepping/gdbstub_hit_break events. Reuse unchanged bounded trace sink
(8MiB/131072 lines), capture/cleanup limits and every existing assertion.
One targeted host red/green300s, finite cases2/13/15 first-failure sweep, at most
three45s guests incl3s cleanup/135s sum/240s host, zero builds. Normal transport,
shared modules and installed tools unchanged; no inferred execution/retried
step/deduplication or qualification from this diagnosis.

Candidate15: complete diagnostic35 passes21.838s with822 actual RET steps.
Promote the explicit single-step/post-reader outer loop, retaining every old
callback/guard/oracle; no diagnostic ticket wrapper. Preserve all register,
flags and CR3 equality assertions. Use private COLD_STEP_V1 records<=192 bytes
and one final count instead of verbose register dictionaries; case6 already
used7.12MiB-scale bytes, so the existing8MiB ceiling must not grow. Additional
raw replay checks sequence/site/PC/stack/return route and complete end count.
Targeted red/green300s, then ten gates/eighteen45s cases incl3s cleanup,
810s sum/900s runtime, first failure stops. Exact seventh image, zero builds.
Preserve108 physical guests2146.2288713001476s plus one prelaunch0.3871212s.

Diagnostic35:34 fails before spawn (binary observer shape);107 physical guests
2124.3906322001426s/seven images remain, plus one prelaunch attempt0.3871212s.
Keep shared binary configure unchanged: supply its admitted original tail,
then append the existing bounded outer loop AFTER reader configuration in
AY diagnostic capture only. No change to step/loop predicates or deadlines.
Real configure/_capture_run host integration through emitted script, no VM;
red/green300s each then one case13 guest45s incl3s cleanup/90s host, zero builds.

Diagnostic34 fixes only the explicit-step batch continuation:33 proved the
first RET then GDB exited0; remaining command-list continue is discarded after
stepi (documented GDB behavior). Guest timed out42.162s. Preserve107 guests
2124.3906322001426s/seven images. Outer loop <=8192 continues, each return must
have exactly one new verified RET and idle nonfailed dispatcher; otherwise
quit71. Original step helper/callbacks/guards/oracles unchanged. Host red/green
300s each, one case13 guest45s incl3s cleanup/90s host, zero builds/acceptance.
Reference: https://sourceware.org/gdb/current/onlinedocs/gdb.html/Break-Commands.html

Diagnostic33: candidate14 passes six gates/thirteen guests but case13 again
fails the root READ pending guard (6.705s). GDB default insertion mode is not
a demonstrated repair. Preserve106 guests2082.2285526001365s/seven images.
Diagnostic-only explicit RET progress: original callback once, command context
only, disable its hardware breakpoint, one real stepi, restore in finally.
Require actual RET opcode/return PC/RSP+8 and unchanged GPRs/flags/CR3; step
mode7, one pending cold hook, no reentrancy, <=8192 steps. Never write PC,
skip/deduplicate, retry a step or infer a syscall return. Same image, host
red/green300s each, one case13 guest45s incl3s cleanup/90s host, zero builds.
Reference: https://sourceware.org/gdb/current/onlinedocs/gdb.html/Continuing-and-Stepping.html

Candidate14 qualifies the standard GDB insertion mode, not a diagnostic pass.
Diagnostic32 isolated always-inserted off and passed root-crash case15 in
18.14009289999376s. Normal adapter now uses that documented mode; callback
bodies and every guard remain exact. Full ten gates/eighteen fresh cases,
ordinary capture without ticket/failure/audit wrappers. Reuse seventh image,
zero builds,45s incl3s cleanup/810s sum/900s runtime, first failure stops.
Preserve92 guests1798.9659774001343s/seven images. No inferred completions,
deduplication or assertion changes; qualification and repair remain unclaimed.

Diagnostic31 proves repeated debugger notification: pending READ ticket[14,13]
equals fresh failure[14,13] at root0/gen8/tick572. No second kernel entry or
return occurred. Case5 passes17.859s, case15 fails11.323s,16/17 NOT_RUN;
91 guests1780.8258845001405s/seven images retained. Diagnostic32 isolates the
forced always-inserted mode using GDB's documented default off, diagnostic-only.
One host red/green300s each; one case15 guest45s incl3s cleanup/90s host;
zero builds. Exact observer body, tickets and predicates. Not a repair claim.
Reference: https://www.sourceware.org/gdb/current/onlinedocs/gdb.html/Set-Breaks.html

Diagnostic31: diagnostic30 passes (four hosts1.165s/build10.130s/guest19.019s),
but does not reproduce or repair the pending failure. Preserve89 guests
1751.6440516001317s/seven images. Reuse exact seventh image and unchanged
ticket observer in one finite different-case sweep5,15,16,17; first failure
stops, zero builds/host repetitions. Four45s guests incl3s cleanup,180s sum,
270s host, never qualification. Existing predicates/limits stay unchanged.

Diagnostic30: add an independent kernel execution witness, not a runtime fix.
Two private root0/READ15 counters increment at request/immediate-return helpers,
each saturating8193 (valid maximum8192). Sixteen fixed bytes, no authority or
scheduler changes; reset and validate zero at existing finish. Record their
actual pair in each diagnostic READ and failure snapshot, preserving the old
pending guard. This distinguishes duplicate notifications from real new calls.
Bounded host red/green300s each, one common image180s, one case3 guest45s incl
3s cleanup/runtime90s, no acceptance. Preserve88 guests1732.6248232001385s/six
images. No deduplication or inferred return permitted by this diagnosis.

Latest outcome,20 September: correction28 closes the OOM ordering test and
proves real100ms blocking/no root CPU charge, both denials, exact rollback
and later launch/cleanup. Candidate13 gates1..6/cases0..2 pass, case3 stops.
Diagnostic29 reproduces the original pending15 guard after second-root PATH
at5730ms (12.4850385s guest, host regression0.205s). Direct uncached failure
snapshot confirms root0/gen10 RUNNING/request-site PC/IF0, pending bytes
0100010100000000 and enabled request/return hooks with399/309 hits. It rules
out a disabled return hook or wrong slot/generation, but does not distinguish
a repeated request notification from a missing return notification. Outer
capture reports incomplete input; the original guard remains in the raw log.
Result ea709d470653f75fc2fc1dd3cde84993b60918cab0527e009952395f8f2e5a65.
Preserve88 guests1732.6248232001385s/six images. No active execution reservation,
guest, commit or qualification. This unresolved evidence ambiguity is a safety
stop; do not infer completions, deduplicate notifications or retry acceptance
unchanged. The independently passed OOM correction remains visible.

Candidate13 stops at gate7/case3: gates1..6 and cases0..2 pass; same gen10
READ15 pending guard after second history, last request6780ms. Later work
NOT_RUN, no commit/qualification. Preserve87 guests1720.1397847001503s/six
images. Diagnostic29 adds only a failure-time direct GDB snapshot (2048 raw
bytes/4096 JSON bytes) of task/pending/syscalls/registers/hit counters. No
healthy-path accesses, tracing or extra breakpoints. Original failure/quit71
survives snapshot errors. One targeted host300s, then one case3 guest45s incl
3s cleanup/runtime90s, zero builds, never qualification. Stop after this
evidence window; do not deduplicate or infer missing completions.

Candidate13 reserves the full unchanged ten gates/eighteen cases after
correction28 passed four host methods7.760s, one build10.681s and the complete
OOM guest18.0846604s. Both driver denials, real100ms blocked pause/no root CPU
charge, exact three-frame rollback, later app82 and full root/peer cleanup
passed every original predicate. Exact sixth image30efcc9a412ee87c07558223a9428c962db4222b08165f1cfe2897f456818987
is reused, no more builds. Eighteen45s guests incl3s cleanup/810s sum/900s gate,
first failure stops. Preserve83 guests1648.5452671001553s/six images. This does
not explain the old intermittent pending-callback failure; guard stays intact.

Correction28 fixes two host-fixture defects exposed by27 (no build/guest):
service deadline_ms is unpublished during construction, so check the actual
100ms previous_ms delta and zero unpublished deadline; align host counters16
after adding syscall_rdi (O2 MOVDQA crash confirmed). Production and one-image/
one-guest limits unchanged; retain27 failure and both passing new raw tests.

Correction27 carries the unchanged26 implementation/reservation after26's
freeze rejected its own still-open redirected log. No build/guest consumed;
failed freeze retained, next freeze writes to tool output, not a bound input.

Correction26 reserves one common image and one case17 guest (45s including
3s cleanup,90s host), after one targeted host command (300s; build180s).
Diagnostic25 proves exact three-frame rollback but fails the existing dual
console-denial predicate: drivergen5 is canceled after READ denial, before
WRITE denial. Only case17/second construction/FS creation now sleeps100ms
before import. The shared1000ms deadline is not renewed. Host regression
covers one-shot ordering, failed sleep and unaffected cases. Additional raw
sleep/time/CPU checks supplement, never replace, every existing predicate.
No acceptance promotion; old pending-observer ambiguity remains. Preserve
82 guests1630.46060670013s/five images and all prior failed evidence.
Inventory amendment: SLEEP41 is not in the old cold-probe filter. Only root0
SLEEP100ms joins that existing private opt-in witness; ordinary polling sleeps
remain unobserved. Actual assembly tests cover all slots/opcodes and10/100/101ms
with preserved registers/flags. No sleep/scheduler implementation changes.
Two targeted red commands followed by one four-method green command,300s each;
the one-image/one-guest reservation remains unchanged.

Diagnostic24 again stops at root quota256/32 before late audit,13.3841795s;
RIP413d1f is IPC_CLOSE return, while23's4136fc is TASK_CONTROL return. No spin
loop cause established. Diagnostic25 isolates optional QEMU continuation/IRQ
tracing: select existing normal capture, exact24 observer/late watch/native raw
CPU/PIO proofs/feeder/oracles unchanged. Cases17 then0 once, first failure stops,
two45s guests incl cleanup3s/90s sum/180s host, no build/qualification.
Retain81 guests1610.6604701001493s/five images and all failed evidence.

Diagnostic23 stops at case0 after11.3816693s: rootgen1 quota fault256/charge32
at RIP4136fc during boot, before watch activation; feeder rejects its incomplete
run. Cases6/15/16/17 NOT_RUN. Diagnostic24 removes early audit target reads,
not quota enforcement. Host-only complete wrapper invokes the original once,
arms only from its existing successful full second-root history WRITE row.
Only then read registers/install the root-byte watch. Original callback bodies,
guards, image and all limits remain. Actual host red/green covers early/foreign/
failed/partial admission and original error/return preservation. One case0
45s incl cleanup3s/host90s, no build/qualification. Retain80 guests
1597.2762906001594s/five images; original missing-completion cause still open.

Diagnostic22 passes case5 in23.383002899994608s, with16 actual root-byte writes
and every original case predicate. This proves scoped instrumentation only,
not a repair. Diagnostic23 freezes one finite provenance sweep: cases0,6,15,16,17
once each, first failure stops, no repeated case5. Exact22 observer/feeder/raw
validators and fifth image; zero builds or production correction. Collect
failure context across normal/idle/root-fault/restart-exhaustion/OOM paths.
Five45s guests incl cleanup3s/225s sum/300s host, never qualification or
retry-until-green. Preserve79 guests1585.8946213001622s/five images.

Diagnostic21 stops after case5 at foreground construction count31.299875s;
case15 NOT_RUN. Its3390 all-slot write stops accompany service CPU-quota faults,
not the missing-completion guard. Diagnostic22 scopes the watch to root0's
single byte, armed only at second-root history WRITE return, after asserting
the byte idle, before the former failing READ. No earlier/service data watch;
all original guards, validators, quotas and deadlines retained. Host red/green
proves no premature read/arm, single late arm and busy/hardware denial.
One case5/8GiB45s incl cleanup3s/host90s, no build/qualification. Preserve78
guests1562.5116184001675s/five images and every prior result.

Diagnostic21 observes the missing causal link directly: a diagnostic-only
hardware WRITE watch on existing native_session_probe_pending[8], armed after
mapped kernel handoff. Collect-only stop, command-context read-only records;
bind PC/hardware type/hits/owner/pending bytes and order against probe callbacks.
Software watch fallback rejects. Same16 records/4096 bytes/8192 events and
original callback capacity, guards, validators and guest state; no new image.
Cases5 then15 once each, stop first failure,45s inclusive cleanup3s each,
90s guests/180s host. No qualification promotion. Retain77 spent guests
1531.2117434001705s/five images. Actual host regression precedes reservation.

Latest outcome20September: diagnostics19/20 both pass without reproducing the
candidate12 failure. They remain unqualified: case5/8GiB23.015497200016398s,
case15/root-crash20.66983469997649s; cleanup0.074512s/0.034602s. QEMU-side trace
is1459055 bytes, within the unchanged sink cap. Four distinct targeted host
methods pass. No new production change/build, no inferred completion, no
commit/queue advance or further execution reservation. Cumulative77 guests
1531.2117434001705s/five images. Ambiguous failure cause remains a safety stop;
successful diagnostic timings do not prove repair. Full18-case/ten-gate
qualification and corrected OOM runtime proof remain open.

Diagnostic20:19 passes case5 in23.015497200016398s; observed qqemu.sstep=0x7,
paired request/return stops, no reproduction or repair of the sporadic failure.
One different case15 adds QEMU continuation/step/hit/IRQ events using the
existing8MiB/131072-line ContinuationTrace sink and bounded cleanup. Only a
separate AY diagnostic capture adapter admits the combination; normal capture,
callback bodies, feeder and raw validators stay exact. Host regression first.
One45s guest/cleanup3s/host90s, zero builds, never qualification. Preserve76
guests1510.541908700194s/five images and every previous result; no unchanged retry.

2026-09-20 diagnostic19: resume evidence-only diagnosis on renewed instruction.
One case5/8GiB guest, exact fifth image, zero builds,45s including cleanup3s,
host90s. Separate adapter retains last16 stops (4096 bytes each/8192 events),
task/syscall/register/private pending snapshots and actual GDB hit counts.
Late second-root history output arms infrun logging for at most64 cold callbacks;
the existing8MiB trace cap remains. qqemu.sstep is queried, never changed.
Original callbacks/guard/validators/feeder remain exact; no inferred completion,
deduplication or diagnostic promotion. Prior75 guests1487.5264115001776s/five
images remain spent. Host-test bounded capture first. This new finite diagnostic
reservation supersedes only the no-reservation sentence of the historical stop.

Latest stop: candidate12 gate7/case5 reproduces the pending READ guard under
command-only dispatch, so that transport change is not a demonstrated fix.
Gates1..6/cases0..4 passed; remaining gates/cases did not execute. Exact failure
is root generation10/op15/pending15 after the observed6910ms request. Current
raw data do not distinguish repeated debugger notification from omitted return
notification. Stop on this unresolved evidence ambiguity per package protocol;
do not infer completion, deduplicate events, weaken gates or retry unchanged.
Keep the visible candidate and every failure, no commit or next reservation.
Cumulative75 guests1487.5264115001776s/five images. OOM baseline correction is
host-proven only; full18-case/ten-gate qualification remains mandatory/open.

Candidate12: diagnostic18 passes case15, but sporadic missing syscall completion
in11/17 is unresolved and no diagnostic qualifies AY. Move every cold-probe
callback into the existing command dispatcher: stop decisions only collect,
without target reads/classification or mutation. Exact original read_only,
callback/drain bodies and all pending/PC/raw oracles remain; duplicates are not
filtered and missing completion still fails. Host tests exercise the actual
dispatcher, deferred reads, duplicate occurrence count and fail-closed quit71.
This is a bounded transport correction, not a claimed cause until qualified.
Ten full gates, zero builds/exact fifth image,18 fresh45s guests/810s with
cleanup3s/runtime900s. Preserve69 spent guests1347.4950213001287s/five images.

Diagnostic18:17 localizes the assertion to the request live/pending-owner
guard but not the failed invocation's identity. Add only that assertion's
message using already read slot/generation/op/live/pending-op values. No
predicate change or extra target read. Host negative test, then one45s case15
diagnostic/cleanup3s/host90s, zero builds; never qualification. Preserve68
spent guests1325.1971648001347s/five images; no speculative kernel change.

Diagnostic17: candidate11 passes gates1..6 and cases0..14, including case6
in32.384s; case15 stops with an unlocated static-probe AssertionError during
the second healthy root. Only add bounded512-character hook/traceback context
to the generated failure handler. Same exception/stop/quit71, no target read,
write or retry. Host-test actual failure/success handler first; one unqualified
full-observer case15 guest on the same image,45s inclusive cleanup3s/host90s,
zero builds. Keep67 spent guests1307.0037873001422s/five images and all failures.
No speculative production fix or weakening; full18-case proof still required.

Candidate11: candidate10 stops at the42s observer limit in case6 after both
roots exit0 but before complete cleanup proof. Prior candidate09's same case
already took41.9854435s. Eliminate repeated full-trace JSON decoding in the host
feeder only: consume appended complete rows, preserve full-prefix continuity,
all cumulative capacities, fixed plans, generation/clock/byte/prompt checks and
the unchanged final replay oracle. Host regression and exact old/new replay of
all17 passed captures confirm identical decisions; case6 replay decodes drop
284052 to16224. No debugger, kernel, image or limit change. Ten full gates,
zero new builds,18 fresh45s guests/810s with cleanup3s/runtime900s; stop first
failure. Retain51 spent guests979.5447680000507s/five images and all failures.

Candidate10: candidate09 passes gates1..6 and cases0..16, then case17 stops
in the OOM observer: .found precedes the normal CREATE-v6 staging-image eviction.
Move only its baseline snapshot to .cached_entry, after that eviction and before
new allocations; bind exact PC, persisted slot and kernel family_initial_free.
Keep all rollback equalities, three-allocation injection, raw validators and
production sources unchanged. Host negative tests precede ten full gates.
Reuse the exact passed fifth image/build receipt; zero builds, eighteen fresh
45s guests including cleanup3s/810s aggregate, runtime900s. First failure stops.
Prior44 guests797.1512432000309s/five images remain spent; no old case promoted.

Candidate09 corrects only the AY host inventory assertion (exact eight paths
instead of the old count7). Candidate08 stopped there before any build/guest;
parser and all runtime checks stay identical. Same unspent execution budget.

User-approved candidate08 extends scope by the ext2 parser and its two host
tests. Only NativeShellSession opts into lazy directory-sector reads. Preserve
ext2 on-disk inode/rec_len/name_len semantics and complete mapped-block/range
checks; fetch each needed header/name sector once per block, including split
headers and names. Do not read unused directory padding solely to find an entry.
Old profiles preprocess byte-exact; no new ABI, write policy, heap or timeout.
Run old/opt-in parser host behavior at O0/O2 before one common image and all18
fresh guests. Original ten gates remain; add parser hosts to the manifest.
Stop first failure. Prior26 guests392.6945861999993s/four images retained.

Historical boundary (resolved by the new scope approval): candidate07 passes gates1..6 and full guests0..2, then stops
at guest3/ext2-2KiB. Raw block requests prove four initialization reads, four
whole-directory-sector reads and one file-inode read before first file data.
At2520ms request10 cannot fit required100ms spacing before deadline2540ms.
Both roots and peers finish normally; no CPU quota exhaustion. Directory lookup
eagerly reads the whole block in userspace/storage/lib/vfs_shadow_ext2.c; file
data reads already use sector ranges. That shared parser and its host tests are
outside frozen allowed_files. Implementation stops pending explicit extension;
no timeout/pacing change, fabricated success, new reservation or commit.
Proposed scope: that source plus test/test_vfs_shadow_ext2_host.c and
test/test_reist_vfs_shadow_ext2.py, opt-in AY bounded read-only sector traversal
with full mapped-block/record/range checks and unchanged old-profile projection.
Spent26 guests392.6945861999993s/four images; all prior evidence retained.

Candidate07 preserves the established terminal-validation/PIO-fence entry
prefix after candidate06's old-terminal source-order host rejection. No build
or guest was consumed. The new inert terminal notification follows the existing
PIO hook, before family publication; bind both this CALL and its immediately
preceding fence-hook CALL. All original receipt and release checks remain.
Same ten obligations, one unspent image/eighteen guests; old test unchanged.

Candidate06 cold-lifecycle window: diagnostic16 completes both matching ext2
command runs and file Exit82/root Exit0 without ongoing breakpoints in9.794583s;
it remains unqualified. The two remaining permanent terminal/exception probes
share pages with family validation and sleep-exit respectively. Add only two
opt-in CALL/RET notifications to the existing private cold page; preserve the
actual frame, receipt, branch, CPU, PIO and cleanup checks. One new common image,
same ten gates and18 fresh45s cases, first failure stops. No clock, quota, pacing,
deadline or service change. Prior22 guests322.3623714999703s/three images retained.

Candidate05 stopped at case2 after gates1..6 and cases0/1 passed. Both ext2
roots receive the correct STAT728 and first512 bytes, then the paced block
backend rejects sequence9 before the original capture deadline. No CPU quota
exhaustion. Diagnostic16 reserves only one45s detached default-layout2 control
on the unchanged third image, matching both roots and medium, same six commands;
zero builds. Production, complete observer and all acceptance predicates remain
exact. Serial evidence cannot qualify AY. Spent21 guests312.56778849996044s,
three images; all failures retained. No unchanged retry or timing-limit change.

Candidate05 complete qualification: corrected diagnostic15 capture independently
replays all predicates (18 tasks,324 snapshots, full CPU/PIO/terminal/memory and
cleanup). The diagnostic itself remains failed/unqualified. Use the tested
retirement/hybrid observer for18 fresh cases. Keep ten gates; replace only the
build command by explicit --reuse-image validation of candidate04's passed
build receipt, exact production/tool hashes, inner/outer ELF and shell/catalog
layouts. No new image: reuse04780f7103c5670c3cd8c9ff9268c9b97c9e818398ae6b6c8d9fc35a4e0c4052.
All host/default/reference/raw/scope gates still execute once; first failure
stops. Preserve18 spent guests260.68762609994155s/three builds, reserve18 fresh
45s guests including cleanup<=3s,810s aggregate and900s runtime gate. No guest
reuse or changed safety predicate, except recognizing the fully validated PIO
end tag. Maximum36 guests1070.6876260999416s/three builds.

Diagnostic15 completes both roots and file programs in17.198884999990696s.
The generic event dispatcher omitted the already emitted pio_calls_end tag;
its full raw/count/two-run closure checker exists and stays exact. Host-only
correction admits just that tag, then replays the retained complete capture.
No new guest/build or promotion of the failed diagnostic. Spent18 guests
260.68762609994155s/three images; all prior predicates remain unchanged.

Diagnostic15: the immutable third image places the lifecycle IPC entry probe
on live PIO page113000 and the optional CPU-full sentinel on live IPC page114000.
Move only retirement-pending admission to family_terminal64: bind both actual
callers, future op4 IPC calls, current terminal task/receipt/generation and IF.
All physical fence/release/CPU/PIO proofs remain at their original boundaries.
Remove the optional CPU-full stop, not any record: the unchanged CPU reader
must still reject any gap>256, malformed/incomplete record or overflow. No
quota/clock/kernel/image/feeder change. Host tests first, one45s diagnostic
including cleanup<=3s, no build. Spent17 guests243.48874109995086s/three images;
maximum18 guests288.48874109995086s. No qualification from this diagnostic.

Latest retained result, diagnostic14 (not acceptance): first layout0 root
executes the exact six healthy command lines, file child exits82 and root exits
0/state4 using12 total CPU ticks without ongoing debugger stops. Full observation
had exhausted32 ticks at tick88. Second root defaults to layout2 while the same
medium remains layout0, so it cannot establish a healthy prompt; control stops
at42.18977359999553s. Never promote this incomplete control to qualification.
Spent17 guests243.48874109995086s/three images. No further build/guest reserved.
Feeder command-boundary and dispatcher-binding host corrections are retained.
The unresolved requirement is a complete low-perturbation lifecycle/ABI proof;
all original quotas, clocks, raw assertions and eighteen acceptance cases remain.

Diagnostic13 still reaches root CPU32 at tick88 after the hybrid binding fix.
Spent16 guests201.29896749995533s/three images. Diagnostic14 is a command-level
untraced control: same first layout0/image/healthy command bytes, one checked
entry selection then detach, second root remains default layout2. Serial prompt
pacing is admissible only for this diagnosis, never the acceptance feeder.
At most12 sends/64 bytes/4096 polls, total45s including cleanup<=3s, no build.
Every full raw qualification validator stays unchanged; no success promotion.

Diagnostic12 stops at the first deferred CREATE: ColdHook omitted the existing
StopDispatcher.bind initialization of service_retire. Actual-dispatcher host
regression reproduces the AttributeError. Diagnostic13 adds only that binding;
same image/quotas/fields/assertions. Spent15 guests190.67283299993142s,3 images;
one45s diagnostic including cleanup<=3s, no build. No acceptance from this run.

Diagnostic11 confirms the feeder correction, but root1 exhausts CPU32 at
tick88 before its first100-tick renewal. It consumed12.261055099981604s;
fourteen spent guests188.78968269994948s/three images. Diagnostic12 changes
only host callback transport: existing static ReadOnlyCPUStops/SameStopReads
for request/denied/return, with actual TASK_CONTROL calls/completions routed
through the existing deferred dispatcher for CREATE hook mutation. Preserve
all data, PC/helper checks, raw drains, lifecycle controls and validators.
Host behavior regression then one45s same-image guest, cleanup<=3s included;
no build or clock/quota/input-plan change. Maximum15 guests233.78968269994948s.

2026-09-19 bounded feeder correction: candidate04 gates1..6 pass and its third
image starts SESSION64, exits82 and retires the dependent services. Gate7 stops
after42.35775470000226s because the feeder sent the next command across a
terminal ownership transition:24 bytes sent,19 acknowledged; the mandatory
RX discard removed `histo`. Keep the terminal drain unchanged. Restrict each
host chunk to one command, and wait for a new actual root prompt TX after the
previous command's RX newline before sending another. All fixed input plans,
acknowledgements and raw replay remain required. One45s diagnostic11, cleanup
included<=3s, no build, proof/docs-only changes and host regression first.
Spent13 guests176.52862759996788s/three images; maximum14 guests221.52862759996788s.
This is not qualification and preserves all earlier failed evidence.

Frozen19 September2026 after clean AX69282e7613a67263beb7e659d5675b8301066e7d.
AX final receipt231d1df92e6eedf2ded04fd3a1bb5de14439a902d51db156ab66a2b96c9d7c13
qualifies periodic construction, not an interactive system. The existing user
authority explicitly permits a separately versioned persistent shell/supervisor
profile, fixed per-window creation/restart budgets and generation recovery.
One main-worktree package; no agents, push, physical media or R3.6b work.

## Cohesive boundary and inventory

Compose the actual userspace/bin/shell.c and shell_vfs.c with a distinct native
platform adapter and Ring3 dependency supervisor. Bundle namespace lookup,
STAT-to-ELF capture, spawn/identity/terminal/wait, service retirement/recreation
and console lifetime: these share one root-owned publication/rollback boundary.
Do not split media variants or individual SDK stubs into extra packages.

Existing mechanisms: AX root0 eight construction attempts/1000ms, periodic
CPU32/1000ms, eight task slots; AV exact-generation foreground lease; AW
shared-deadline STAT/file capture; real Ring3 ATA and FAT/ext2 FS services.
Existing services retain their finite profiles: ATA2800ms/16 requests,
FS<=3000ms/eight requests, IPC<=1000ms, ATA operation<=200ms. The existing
filesystem.c qualification owns fixed slots2/3 and embedded service ELF files;
extract/reuse its healthy lifecycle rather than move a driver/parser to Ring0.
Its fault workload and all old selectors stay independently reproducible.

Current normal native shell is console-only with an absolute1000ms whole-task
limit and explicit -38 namespace/spawn/wait/identity stubs. Native GETPID is the
positive, nonreused generation, not the task slot. Kernel native syscall114 is
not yet bound: an SDK cache must not fabricate a live process identity.

## Standard-first interface

Preserve System V AMD64/ELF64, existing public syscall numbers and structures,
negative errno, conventional .prg search and the existing real shell dispatcher.
Use existing PROCESS_IDENTITY114 with its established pointer/PID arguments and
16-byte v1 output. The explicit new root profile may query self and its own
live children only; foreign/stale/retired identities fail without publication.
Validate complete writable output, exact generation, parent and all unused
registers before the single publication. No general process-table disclosure,
child TASK_CONTROL inheritance or new device authority. Old profiles deny it.
The bounded eight-slot query is a kernel mechanism, not Ring0 process policy.

Use existing TASK_CONTROL132 CREATE/WAIT/CANCEL, terminal127/v1 and immutable
FS RPC. New private session policy is version1; no POSIX/whole-userland
compatibility claim. Only actual mounted immutable generated media may supply
cwd, drive and directory metadata. No synthetic successful filesystem, resident
program fallback, fabricated child or terminal success. Unsupported USB/network
remain explicit unchanged errors. No new shell command in this package.

## Lifetime, authority and recovery

NativeShellSession is separate from old NativeShell, NativeSession and
NativeTerminal qualification selectors. Root0 is the shell and owns its bounded
Ring3 supervisor state; driver/FS/application remain separate processes. Root1
is an unrelated bounded peer. Root loss invokes existing physical fencing and
descendant retirement; this package does not claim automatic root replacement
or whole-system recovery from the bootstrap's second qualification run.

No whole-session1000ms exit in the new profile. Instead fixed anchored1000ms
windows admit <=4096 adapter operations, <=1024 input bytes and <=16384 output
bytes, with monotonic/cumulative overflow checks and no idle credit. Each I/O
operation remains bounded at <=1000ms and each input read at <=64 bytes. Polling
uses actual blocking sleeps; this implementation retains the actual shared
shell10ms input wait in both profiles, with no silent duration substitution.
CPU32/1000ms
is unchanged. Quota/clock/backend-integrity failure stops only this root and
lets kernel fencing/reaping contain its children; no busy retry or reset.

The supervisor has fixed state for one driver, one FS, one foreground child,
one canonical cwd and one pending STAT observation. Allocate bounded prepared
image/workspace only in ordinary Ring3 context and release them on every exit.
Per-operation deadlines never extend on intermediate success. Only a matching
current-generation/path STAT may feed AW capture; stale, consumed, failed or
capacity-insufficient observations are rejected or explicitly start a separate
fresh operation after retiring the old dependencies, never reset a client.

Start dependencies in order, bind PIO, validate complete actual self-test replies
and only then publish healthy FS. Creation attempts also consume AX's kernel
budget. No opportunistic repeated spawn on EAGAIN. A command may report EAGAIN
and leave the shell usable. A service lifetime/request boundary triggers bounded
planned retirement and new generations before a later command, not renewal of
the old profile. Keep old-generation counters/receipts diagnosable.

Crash, hang, malformed reply and quota failure use the same transaction:
detect -> isolate -> physical PIO fence -> cancel/wait/reap dependents -> close
endpoints -> recreate -> actual self-test -> reintegrate. At most two automatic
recovery attempts in an anchored10000ms window, one retry per failed user
operation, and cumulative attempts never reset. Exhaustion latches DEGRADED;
window expiry alone does not clear that latch. Console HELP/PATH/HISTORY remain
usable; filesystem operations return a real unavailable error. No new manual
recovery command or administrative budget bypass. Unknown cleanup/fencing
result terminates the root so the kernel's existing containment completes.

Foreground app receives only explicit attenuated ordinary/terminal rights,
never FS endpoint, PIO or task management. Exact identity precedes terminal
transfer. Ordinary wait is bounded1000ms; timeout cancels and boundedly reaps
before returning an error. Exit/crash/quota/cancel restores terminal authority
through AV, never SDK bookkeeping alone. Stale handles cannot regain authority.

## Frozen verification and reservation

Candidate04 PIO capture correction: diagnostic10 retains1470 ABI113 entry/
return stops and quota failure during file capture despite complete root
retirement. The private AY witness becomes a fixed32-entry ring,384 bytes per
record,32-byte header (total,error,pending,reserved),<=2048 records per run.
This follows existing private trace-v1 little-endian terminology, not a new
public ABI. Each record contains version/denial, sequence, slot/generation,
entry/return ticks, result, six arguments, full64-byte request before/after,
both24-byte terminal states,64-byte final PIO state, both RFLAGS and modes.
Validate user ranges through the existing bounded validator before copying;
denied profiles never cause a user read. Preserve every register and flag.
No allocation, blocking, kernel policy, new device authority or timer change.
The witness is non-authoritative: malformed/overflow/incomplete capture fails
qualification without changing syscall outcomes. Notify only after committed
records at32-entry boundaries; no consumer acknowledgement or guest wait.
Drain before all lifecycle transitions and erase all12320 bytes on cleanup.
Host reconstruction must retain every original generic ABI113 field, plus
raw sequence/hash/IF/mode/ownership/capacity proof. All old runtime predicates
remain, and the cleanup extent strengthens by12320 bytes. O0/O2 actual assembly
and decoder/mutation/ordering regressions precede the ten unchanged gates.
One native-pio-capture image and18 fresh45s guests/810s including cleanup3s;
first failure stops. Preserve twelve prior attempts134.17087289996562s and
two images; no previous diagnostic qualifies as a matrix case.

Candidate03 cold-probe correction after three bounded diagnostics:
default-layout no-breakpoint boot remains at the shell prompt for7s, with
driver2 CPU ticks; this is diagnostic serial evidence, not qualification.
Only the AY opt-in adds four no-op sites on a dedicated4096-byte executable
page, with fixed72-byte eight-slot generation/pending bookkeeping. Preserve
all registers/flags and syscall results; no authority, quota, deadline or
driver/SDK change. First-entry/completion observation occurs after existing
IPC copyout. Immediate return snapshots remain before scheduling. Zero the
private witness at complete run cleanup and prove those additional72 bytes.
All prior runtime predicates stay exact; O0/O2 assembly and callback regression
precede all ten gates. One new native-cold-probes image, eighteen fresh45s
guests/810s, first failure stops. Preserve four spent guests38.65928809996694s
and the first image: cumulative maximum two images/twenty-two guests.

Diagnostic01 after candidate02 quota stop: one additional healthy case0/layout0
4GiB guest,45s including cleanup3s; zero builds, exact image8535a0e5432ce38d.
The sole differential observation change uses existing PIO bind/fence branches
instead of stopping on each driver port request. Complete physical data/port
traces, CPU records and all validation functions stay byte-identical. No
qualification claim, default observer and eighteen-case requirement unchanged.
Production stays identical. Preserve one previously spent guest10.080940099986037s
and one image; cumulative maximum two guests55.080940099986037s.
Scope only AY runner/test/verifier and queue/docs, no retries of this window.

Candidate02 correction window (2026-09-19, explicit renewed user approval):
include only scripts/verify_x86_64_terminal.py as the additional scoped file.
Its historical disabled-source oracle projects versioned AY/AX opt-ins before
AV and still compares every remaining byte with the original AU baseline.
Regression-first historical and mutation cases live in the AY test file.
Only this adapter, AY tests/verifier and queue/docs may differ from stopped
candidate01; all production and guest proof sources remain hash-identical.
Preserve the stopped receipt and baseline diagnosis, repeat all ten unchanged
gates exactly once in the new window, first failure stops. No OS build or guest
was spent; the same one-image/eighteen-guest reservation remains available.

Regression-first actual C/assembly O0/O2 tests cover adapter outputs unchanged
on failure, all quotas/windows/clock overflow, actual normal shell dispatch,
five media layouts, observed STAT/shared deadline, generation/identity/pointers,
cleanup/fencing order, partial construction, stale replies, restart exhaustion,
terminal ownership and old-profile equivalence. Source patterns supplement,
never replace executed behavior. No new complex Ring0 driver/parser.

Freeze exactly ten gates from the queue: AY host behavior, existing native shell
hosts, existing normal shell/lookup hosts, retained subsystem hosts once via
one manifest, default/ABI/scope proof, one common Windows image, runtime matrix,
protected references, full raw review, final direct scope/bounds review.
Host command ceilings300s (retained manifest900s), build180s, runtime900s,
other gates180s. One build/image, eighteen fresh guests at45s maximum each
including cleanup<=3s,810s summed guest ceiling. Stop at first failed gate/guest;
no unchanged retry, in-window repair or further image. Preserve all counters;
separately freeze any evidence-directed correction under standing authority.

One image covers five healthy immutable media layouts,8GiB, input idle beyond
old lifetime, >eight cumulative constructions, real ordinary file execution,
driver/FS UD2 and hang, malformed reply, app UD2/quota/cancel, owner loss,
recovery-budget exhaustion, partial-construction OOM and stale/foreign authority.
Each declared runtime claim needs actual raw request/return, generation, CPU,
memory/FP/IPC/heap/frame/PIO/terminal and byte-stream proof with independent
kernel/high-RAM memory equality. Serial success alone is insufficient.
Capture feeder may add an explicit bounded session mode for the new profile;
old feeder/defaults, per-guest limits and assertions remain exact.

Exact matrix (4GiB unless noted):0..4 healthy layout0..4;5 healthy layout2 at
8GiB;6 layout2 idle and repeated commands spanning>=5000ms and>eight cumulative
constructions;7 driver UD2;8 driver hang;9 FS UD2;10 FS hang;11 malformed FS
reply;12 app UD2;13 app CPU exhaustion;14 app cancel;15 root owner loss;
16 restart-budget exhaustion;17 partial-construction OOM. Cases7..17 use
layout2. Healthy and fault cases include stale/foreign identity/terminal
rejection, independent peer progress and bounded generation cleanup. Each
fault proof must observe the actual triggering event, not a scripted status.

The first run selects the declared case, the second is a fresh healthy root
generation (not a claim of automatic root replacement). Initial mount/self-test
is healthy; service faults arm the first subsequent command session so cached
root lookup cannot consume a fixture before its failing path executes. Case16
issues four file attempts: initial failure, two budgeted recoveries, then actual
DEGRADED rejection, followed by console-only commands. Case17 fails the fourth
allocator call during FS construction in that first post-mount session, proves
partial rollback and driver isolation, then tries one separate later file
command. Case15 blocks the root once for10ms after foreground construction,
before its UD2, so owner-loss proof includes an actually entered child still
waiting for terminal authority. No operation deadline or automatic retry count
is enlarged.

Diagnostic07 isolates the observer variable left open by diagnostic03:
exact second image/layout0/4GiB, one first-root-entry hardware stop for the
existing private selection only, then detach before user execution. Seven
seconds observation, ten seconds including cleanup<=3s, no input or build.
The eight prior attempts64.85462879997795s/two images are preserved. This is
diagnostic evidence only and does not replace any complete raw runtime gate.

Diagnostic09 reuses existing checked off-page exception/fatal/revoke routes
and scopes dormant same-page cleanup/construction hooks to reachable phases.
All original callback fields and runtime predicates remain; eight-slot revoke
tracking is fixed-capacity and generation-bound. One45s case0/layout0 guest
including cleanup3s on the second image, no build. Preserve ten prior guests
84.11793239996769s; diagnostic success is not full matrix acceptance.

Diagnostic10 keeps those routes and every raw field. Its host-only reader
joins two <=512-byte same-page spans and reuses already-read bytes only during
one deferred syscall/denied/return callback, using the existing bounded cache.
The persisted ASCII trace is interpreted with the same universal newlines as
the live feeder; raw bytes/hashes and all predicates remain unchanged.
Preserve eleven attempts109.6792204999656s/two images; one45s same-image
case0/layout0 guest including cleanup3s, no build, first failure stops.

Before done: all ten gates, exact source/tool/command/image/raw bindings,
direct ABI/failure/bounds/cleanup review and clean local implementation commit.
Then continue the next native priority without routine handoff. This is not
signed normal boot, complete desktop/browser or physical-platform acceptance.
