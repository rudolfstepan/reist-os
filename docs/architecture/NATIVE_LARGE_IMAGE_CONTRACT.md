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
