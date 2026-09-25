# CI: bounded PS/2 READ return

User renewed `mach weiter` immediately after the concrete scope question
approves the input-read kernel prerequisite on2026-09-25. CB source is paused
byte-exact in build/codex-agent/r83ci-input-return/before-ci01/files.zip,
SHA25628394e53e280b0031ce2c92a1c9d53c0a8f4cc9305bc710248222b0c9b9fab46.
Baseline f5ebfb0d. CB counters86 hosts/50 builds/28 media/38 guests retained;
all five CB gates/eight final cases remain. No CB acceptance or OS completion.

Exactly one active implementation: R8.3ci-input-return. Scope: existing
native_input_syscall64.result only, under REIST_NATIVE_DESKTOP_CPU. READ3
results1..65536 or EAGAIN(-11) use existing query_resume64 after scratch erase.
Everything else uses process_run_resume64. No query burst reset; same shared
8-call ownership, interrupts, CPU32, deadlines, quotas, decoder and rights.
PS/2 wire protocol and errno meanings remain unchanged; private return
routing creates no ABI. No Ring0 protocol parsing. Old disabled assembly
must be byte-identical. No modification to the accepted query-return core.

Failure model: inefficient per-byte dispatch contributes to observed input
CPU fencing and secondary lost application endpoints. Improvement remains
a hypothesis until the original input load/latency proofs pass.

Development reservation: hosts1..8<=180s, builds1..2<=300s, media1..2<=180s,
guests1..4<=600s. Evidence-directed extensions must preserve spent counters.
Frozen final gates, once each per fully frozen qualification:
1. python test/test_x86_64_input_return.py -v (180s): actual assembly routing,
   scratch erasure, success/empty/error/old profile and shared burst invariants.
2. python scripts/verify_x86_64_input_return.py --package (600s): complete
   native desktop build/media from hash-bound immutable paused CB fixture.
3. python scripts/verify_x86_64_input_return.py --runtime (2000s): three fresh
   guests <=600s each, total1800s:801-event mouse stress+10s stable owners,
   original300ms mouse/exact abc+10s stability, existing CPU-fault isolation
   with replacement. No debugging stops in performance cases.
4. python scripts/verify_x86_64_input_return.py --review (180s): independent
   raw-state/pixel/receipt review, immutable source/fixture/artifact hashes,
   scope and closed guests with unchanged base media.

Package gate builds the already preserved CB sources as an immutable fixture;
no CB implementation edits allowed during CI. Success commits CI and resumes
CB integration; do not re-run unrelated unchanged VM matrices. No push.

## Evidence-directed scope extension proposed after CI guest3 (not yet approved)

Contract baseline b6a7eeb2. Hosts1 expected-red,2 green4.826s; build1
29.422s/media1 complete. Guest1 failed48.737s with frontend EDQUOT and
input exit71. Guest2 failed49.686s with input CPU256: the read-return
shortcut alone does not satisfy the frozen stress gate. No acceptance claim.
Guest3 captured actual healthy READY ownership arrays47.339s without debugger
or injected load; media unchanged and all own guests closed.

Host3 executes the current production process_run_frames64 assembly against
those exact captured task/table/original-CR3 arrays. Only a counter before
its existing full-width collision comparison is added. O0/O2 each validate
200 scans with no ownership mutation:52514 prior-frame comparisons per scan,
0.012s total on the host. These are host costs, not guest timing or a speedup.
Source, snapshot and result hashes are retained in
build/codex-agent/r83ci-input-return/host03-frame-measurement.json.
The scan is called from process_run_validate64 at syscall entry and again
on ordinary dispatch. Each old inner iteration also branches on whether
its position denotes private memory, the stack or a page table.

Proposed additional source: arch/x86_64/proc/process_run.inc, ONLY the
REIST_LARGE_POOL_FRAME_SCAN collision path of process_run_frames64.
Replace repeated per-position type dispatch with separate contiguous scans
of the previous private-frame prefix, one stack comparison, and the prior
page-table prefix. All original prior positions, including zero entries,
remain compared with full64-bit equality; current position is excluded.
Preserve the64-byte local negative filter, original outer validation,
free-slot checks, alignment/range/CR3 checks, bounded8*261 positions,
stack bound, generation/CPU/IRQ checks and fail-closed semantics. No cache,
SIMD, heap, new authority, limit change or additional persistent scratch.

Same active CI failure model and frozen four gates; do not weaken or split
the801-event stress/300ms input/CPU-fault requirements. Add differential
actual-assembly tests against b6a7eeb2 for captured and dense/sparse owner
arrays, collisions/duplicate frames across every region, invalid frame
values/free owners and stack canaries. Any speed claim requires an actual
comparison and the unchanged fresh guest gates. Existing test file is in
scope; the additional kernel source is not. AGENTS rule4 requires approval
before changing this file. No frame-scan implementation change made.
Counters3 hosts/1 build/1 media/3 guests spent; all failures retained.

2026-09-25 renewed user mach weiter immediately after the concrete frame-scan
question approves the proposed process_run.inc scope extension. Same active
CI transaction and four frozen gates. Add differential/canary tests first;
existing hosts4..8/build2/media2/guest4 reservations retained.

Development hosts4 baseline/5..7 green. Build2/media2 retained FAT12 size
failure; build3/media3 fit but guest4 CPU-failed. Bounded REPNE full-width
comparison variant build4/media4 passes guest5 (67.101s), all801 batches
and10s stable exact owners/rights/CPU32. No final acceptance yet. Preserve
old large-pool profiles byte-exact with REIST_NATIVE_DESKTOP_CPU guard;
selected instructions unchanged. Host8 checks complete old-profile scan
bytes and selected differential behavior. Spent7/4/4/5; guest6 reserved.
Final qualification remains the four original gates, three fresh guests.

Host8 failed harness assembly: selected DesktopCPU test omitted required
LargePeriodic macro. Complete the test profile, preserve failed log. Reserve
hosts9..10 <=180s for corrected regression and verifier admission checks;
no guest/source behavior change or unchanged retry.

Host9 passes selected and disabled assembly checks. Host10 admission caught
a queue-edit anchor error: the approved source was inserted into an earlier
completed package instead of active CI. Restore that historical row and put
the explicitly approved file in CI only; no authority or gate change.
Reserve host11<=180s for corrected scope/pixel/owner verifier admission.

Host11 verifier admission passes1.251s (exact801 endpoint pointer and
unchanged live owners/CPU bounds); host9 selected/disabled differential pass.
Freeze qualification01 now: same four gates, one fresh build/media and three
fresh guests, unchanged gate/deadline/resource limits. Development totals
11 hosts/4 builds/4 media/5 guests, all failures retained.

## Accepted qualification01 (2026-09-25)

All four frozen gates pass: targeted5.278s; package37.651s;
runtime218.786s; independent review5.233s. Three fresh guests:801-event
mouse load plus10s stability, original300ms pointer/exact abc with10s
stability, CPU256/kind3 isolation and replacement. Original input CPU32,
root/compositor64, rights/generations and base-media integrity verified.
Signed package kernel1391504 bytes fits the unchanged FAT12 medium.
Development11 hosts/4 builds/4 media/5 guests preserved; final qualification
adds its own1 build/1 media/3 guests. No failed attempt was relabelled.
Acceptance seal and all raw/hash-bound artifacts: qualification01 under
build/codex-agent/r83ci-input-return. CI done; restore CB after local commit.
This accepts the kernel prerequisite, not VMware stability or the full OS.
