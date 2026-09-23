# Native large prepared image ownership — R8.3bu

## Authority and inventory

The user's renewed "mach weiter bis alles fertig ist" after the concrete
b8aa7ab4 proposal explicitly approves NATIVE_LARGE_EXECUTABLE_PROPOSAL.md.
Accepted text baseline33061693; clean proposal baselineb8aa7ab4. The full
larger mapping/capture scope is authorized once; individual diagnostics and
later in-scope prerequisite transactions do not require another approval.
R3.6b remains explicitly deferred. One main worktree, no agents and no push.

This transaction implements the prepared image/CREATE/frame-ownership boundary.
Larger filesystem/block/capture integration and QuickJS execution follow as
the separate failure domains already listed in the approved proposal. No
additional device, DMA, persistent write, script or network authority.

Inventory: native_layout.inc/h parameterize image/task/frame layouts; pure
boot_program_admit64 handles RNPGv1/v2; task_family.inc preflights and snapshots
imports and scrubs on all results. CREATE-v6 is already the80-byte periodic
service request. image.c is the existing Ring3 System V ELF64 adapter.
NATIVE_PROGRAM_MEMORY_CONTRACT and HIGH_ASSURANCE_CORE_CONTRACT remain binding.
The old NativeWide catalog has four fixed RNPGv2 records at0xa00000, separate
zero-filled scratch at0xb05000 and an existing16MiB mapped boot window.
Keep that catalog format/extent: only imported large records use RNPGv3.
This avoids embedding four1MiB records or changing boot transport authority.

## Fixed append-only profile

NativeLargeImage implies NativeWide/NativeImport, explicitly off by default.
RNPGv3: magic RNPGv3\0\0, version3, size1052960, entry,256 page-right bytes,
eight reserved zero bytes,1048576 image bytes and4096 argument bytes.
ELF input<=1048576, eight PT_LOAD/PT_NULL descriptors, mapping0x400000..0x500000.
Existing canonical address, overflow, alignment, ordering, disjoint segment,
file-backed entry and R/RX/RW checks apply before any output publication.
Reserve slots7..15 as before: absent7/8 in prepared data, zero RW9..15,
independently owned stack frame8, unchanged guarded32KiB stack and startup.
No old version or wrapper accepts a larger input/record under recompilation.

Append CREATE-v7,64-byte transport/full profile/startup, importing RNPGv3 with
ordinary existing CPU admission1..32. CREATE-v6 remains periodic RNPGv2;
this package does not append a periodic large-image operation. All source
chunks are checked before copy, with no partial publication or attempt charge
on failed admission. Staging and teardown scrub1052960 bytes in this profile;
old import/catalog sizes remain exact. Frame allocations roll back exactly.

Private arrays have256 slots, task records4096 bytes, vector shift11,
claim capacity261 frames and mapping ownership capacity517 frames. Existing
frame/identity/context/pointer mechanisms remain bounded and generation-scoped.
No heap/CPU/IPC/restart/task-count or operation-deadline increase. The loader
must clear absent high slots for v1/v2 and never consume payload as flags.

Keep catalog payload1065344/rounded1069056 bytes. Large scratch payload1052960,
rounded1056768, occupies0xb05000..0xc07000 within the already mapped16MiB window.
Version the exact optional boot-area admission; keep old pairs valid and reject
mixed/unselected shapes. Reserve the full extent, verify every leaf and absence
of writable/direct aliases, and prove zero-before-use. No Ring0 ELF parser.

## Cohesive consumer and tests

Reuse the ordinary native memory/lifecycle fixture with a separately linked
large imported child; retain four small v2 boot records. Execute and read
pages beyond0x440000, check first/middle/last private RW pages, guarded stack,
immutable source overwrite after CREATE, independent peer and two generations.
A private zero-default fault selector is only qualification input, never CLI
or additional application authority. This is a mechanism fixture, not a new
shell command or a JavaScript compatibility claim.

Regression first: actual C parser and ASM metadata/range admission at O0/O2;
byte equality with host producer; all256 slots, exact caps, malformed record,
wrong-version/size, RX/RW/NX/guard violations, overflow, unchanged rejected
output, high addresses and complete rollback. Exercise real frame/map/context
mechanisms with the new layout, not source-pattern substitutes. Legacy tests
and exact disabled-source projection protect all old versions.

Fresh runtime matrix13 large guests: normal4/8GiB; guard-write, stack execute,
RX-write, CPU exhaustion, sleep/cancel; six distinct partial-OOM points0/1/2,
quarter/half/last of measured actual child construction. Each<=120s; aggregate
<=1560s. Two fresh legacy NativeWide normal4/8GiB<=90s each; total<=1740s.
Retain original register, actual memory, PTE, frame/owner, context, scratch,
reap/generation and shutdown assertions. Full independent raw replay and
negative oracle mutations mandatory; success strings alone are insufficient.

## Frozen finite work and gates

Before implementation: one clean-baseline NativeWide build<=300s, recorded
sources/tool pins/artifacts. Development: twelve host commands<=600s each,
three large builds<=300s each, four diagnostic guests<=120s each. No unchanged
retry; preserve spent counters and first-failure logs. Freeze a correction
window only after an evidence review, without weakening acceptance predicates.

Five acceptance gates, each once per fresh candidate:
1. python test/test_x86_64_large_image.py -v (900s).
2. python scripts/verify_x86_64_large_image.py --defaults (900s).
3. python scripts/verify_x86_64_large_image.py --package (600s).
4. python scripts/verify_x86_64_large_image.py --runtime (2200s).
5. python scripts/verify_x86_64_large_image.py --review (900s).

Package gate builds normal and fault-capable qualification images at most
once each, with the same mechanism bytes. Runtime selects only frozen private
faults/OOM inputs, not rebuilt policy. Review replays all15 guests, hashes
sources/tools/artifacts/history, checks allowed scope and frozen gates. Local
commit/queue transition only after success and direct ABI/cleanup review.
A required source outside the frozen list is an architectural scope stop,
not permission to silently expand. No native64 completion claim from this slice.

Baseline01 passed6.511s. Host01 confirms absent new producer; host02 fails
before execution because Zig injects an unused Windows linker argument under
-Werror. Apply the established host -Wno-unused-command-line-argument flag.
Review the negative fixture to use explicitly invalid ELF values (changing an
entry within RX or increasing memsz inside alignment padding can be valid).
Host03 is the next already reserved host slot; no kernel build/guest spent.

## Development evidence and correction window (2026-09-23)

Host04 passes actual v3 assembly admission. Build01 fails argument admission
(absolute output path;0.424s), build02 fails linking the compiler-emitted
memset from the larger flags initializer (1.961s), build03 links both ELFs but
fails outer section admission at the former 1MiB NOBITS ceiling (6.732s).
All three initial build reservations are spent, not reset. Corrections use a
relative output path, bounded explicit volatile initialization, and an exact
1056768-byte scratch ceiling selected only for the large outer profile.
Host05 passes both explicit profile directions (1.938s). Host06 catches an
incorrect test-vector substitution of NX bit63; corrected without changing
production permissions. Host07 exposes the actual old 0x440000 pointer cap.
The range now derives from NATIVE_IMAGE_PAGES; old profiles retain their
original limits. Host08 passes all256 mappings and complete frame-claim and
release behavior (6.781s). Host09 adds CREATE-v4/v5/v6/v7 coexistence and all
1029 source-preflight failure positions; all six tests pass at O0/O2 (7.809s).
Host01..09 are spent; host10..12 remain. No diagnostic guest has run.

Evidence-directed correction reservation: two additional builds, build04/05,
each<=300s, same frozen scope and gates. Build04 verifies the host-proven
outer-admission and pointer-bound corrections together. Build05 may only
follow a distinct recorded failure and reviewed correction, never unchanged
retry. The original four diagnostic guests and all acceptance gates remain
unspent and unchanged. Build03 artifacts remain the negative regression
fixture for explicit old/new outer-layout admission.

Build04 passes6.542s. Diagnostic01 (4.567s,8GiB) proves poisoned scratch
zeroing/reservation/leaf permissions but stops at HIGHER_HALF_STATE_ERROR
before native programs. Inspection identifies verify_native_pages64's old
0xb47000 end check. Under the explicit large selector only, use0xc07000;
the linked-section verifier and runtime observer still check exact extents,
leaf permissions and absence of aliases. Build05 is reserved for this distinct
correction; diagnostic02 will test the corrected image. No guest pass claimed.

Build05 passes6.593s; diagnostic02 (3.760s) starts and cleanly reaps both
catalog tasks but root returns205 before child publication. Inspection finds
five v5/v6 dispatch guards still choosing v1 size or cached images for v7
when SERVICE_CPU is disabled. Under LARGE_IMAGE, those already-admitted
version comparisons now use the same >=5 branch, followed by the explicit
v7 size/range/tail selection. v6 admission remains SERVICE_CPU-only.
Reserve one correction build06<=300s for these five dispatch guards, followed
by existing diagnostic03<=120s. Counters/evidence and gates remain intact.

Diagnostic03 passes10.362s on8GiB: eight retired tasks, four large child
instances, high RX/middle/final RW, immutable source overwrite, complete
frame/FP/context/scratch cleanup. Actual child construction uses52 frames.
Diagnostic04 fails1.816s in the new private-selector observer before modifying
it: root embeds the child ELF, so scanning for shared witness magic is
ambiguous. Bind selection to the exact root linker-map symbol instead and
check its original bytes and RW page before writing. No guest/kernel change.
Reserve diagnostic05/06<=120s each for selector/raw-replay qualification;
original four diagnostic slots remain spent. All acceptance gates unchanged.

Diagnostic05 completes guest checks but raw replay rejects a missing final
callback-end record: debugger quit exits before the wrapper can append it.
Emit that terminator before detach/quit; diagnostic06 passes full replay
11.001s. Host10 retains the30s identity stress timeout and three ineffective
mutations of non-authoritative bytes. Host11 binds mutations to checked
state/record fields and passes all8 tests52.583s. Identity vectors retain128
reuse rounds at capacities1/4 and three complete rounds at capacity64,
including every256 image field; per-process30s bounds remain unchanged.
Host12 fails the new exact disabled Make projection0.734s. Production/gates
are unchanged; reserve host13/14<=600s for this verifier correction and
legacy raw-adapter validation. Original host01..12 stay spent.

Host13/14 retain diagnostic failures (wrong traceback frame, then Windows
console encoding). Inspection resolves the actual Make projection mismatch:
Path.read_text used the Windows default encoding while git original uses
UTF-8; specify UTF-8 throughout the new verifier. Reserve host15..18<=600s
for exact source projection, adapter and remaining frozen-test setup checks.
These are bounded verifier corrections; no source/gate acceptance is inferred
from either failed diagnostic and no counter is reset.

Host15 passes exact complete disabled assembly/C/Windows/Make/Python
projection and both observer compilations0.891s. Reserve diagnostic07/08,
each<=120s: legacy8GiB raw adapter and large8GiB guard-write containment,
respectively. No rebuild, no quota/permission change. Acceptance matrix stays
15 fresh guests after freeze; these two diagnostics are not acceptance reuse.

Diagnostic07 passes legacy8GiB full raw replay6.841s; diagnostic08 passes
large8GiB guard-write containment and complete replay11.297s. Candidate01
freezes all five original gates. The single normal qualification build already
contains the zero-default private selector; the same mechanism/image serves
all fault and OOM cases, with no second build or policy change needed.
Direct review confirms version7 uses64-byte request/lifetime CPU accounting,
full1029-chunk preflight, exact snapshot/tail, fresh-cache release and complete
scratch scrub. Old source projection passes; no outside-scope source change.
All development evidence remains hashed and retained. No package acceptance
or complete native64 claim before all15 fresh guests and five gates pass.

## Accepted candidate01

All five frozen commands pass39.402/45.715/9.043/164.156/6.292s. Eight host
tests and legacy regressions, exact disabled source projection, one fresh
large build,13 large plus2 legacy guests and complete independent raw replay.
Seal a23dd20e7fe995d8a852656989a75d47ce435b9784de24aea033e4a4e707d86e.
Direct final raw-index inspection independently counts52 allocator callbacks
per successful CREATE and n+1 callbacks at each failed OOM position n,
followed by fresh52-call construction. Source/ABI/cleanup review is complete;
no unbounded runtime path or authority/CPU/heap/stack increase introduced.
All historical failed attempts remain preserved. Queue now closes BU only;
R3.6b remains deferred and approved capture/QuickJS work is still outstanding.
