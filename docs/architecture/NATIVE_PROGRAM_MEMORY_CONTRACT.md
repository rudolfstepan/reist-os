# Native program and stack memory — R8.3aj

Frozen after accepted `a1f17276`, 13 September2026, with explicit renewed user
approval of the program/stack boundary, subsequently extended by renewed user
approval to the boot-memory dependency. Eighteen mandatory queue gate groups.
This is a contract, not implementation acceptance or a complete native OS.

Status: attributed candidate resumes under the explicit boot-memory amendment
below; its first whole-image link failure remains evidence, not acceptance.

## Inventory and standard reference

The existing native ELF adapter and RNPGv1 admit eight image pages and one
stack page. Reachable FAT read/stat/readdir code and Unicode data compile to
79705 bytes with the current freestanding Zig/Oz toolchain and section GC;
EXT2 readdir alone has a5192-byte static call frame. Merely linking existing
Ring3 parsers cannot fit. Reuse the current System V ELF64 ET_EXEC AMD64
adapter, Intel64 four-level4KiB paging and AMD64 argc/argv/envp/auxv startup.
No second ELF parser in Ring0, no filesystem parser changes or Unicode cuts.

## Versioned capacity and ownership

NativeWide is an opt-in NativeImport profile. Ordinary build flags, RNPGv1,
old SDK wrappers and CREATE versions1..4 keep their existing semantics.
An append-only CREATE-v5 uses the existing64-byte v4 transport/full profile,
but imports the new RNPGv2 record. No syscall renumbering or ambient rights.
Both v1 and v2 catalogs/imports must remain distinguishable and validated.

RNPGv2 has magic RNPGv2\0\0, u32 version2, u32 size266336, u64 entry,64 page
rights bytes, eight reserved zero bytes,262144 image bytes and4096 argument
bytes. It covers64 slots at0x400000..0x440000. Input ELF is bounded to524288
bytes and eight PT_LOAD/PT_NULL descriptors, with the existing strict flags,
alignment, file-backed entry, ordering, overlap and overflow checks.

The REIST-specific v2 adapter reserves pages7..15 from ELF segments: page7
is the lower guard, page8 remains the existing independently owned stack
frame, and pages9..15 are synthesized zero RW image pages. Their private
task copies extend the stack to32KiB at0x408000..0x410000 without another
allocator or retirement list. This is a versioned mapping adapter, not a new
ELF segment type. Reserved image bytes and guard rights must be zero; the
seven extension pages must be zero/RW. User code/data may occupy slots0..6
and16..63. No sharing of writable stack pages, no executable stack.

Startup writes the ordinary bounded argument frame into the top owned stack
page. Syscall/IRQ context admission selects the exact per-image stack range;
legacy v1 retains4KiB. Pointer checks traverse actual page permissions and
bind all stack pages to their owner. Absent/guard pages grant no authority.
Prepared bytes are snapshotted before publication, independently admitted in
Ring0, and scrubbed on all exits. Immutable import ownership remains7/8 for
dynamic slots2/3; old catalogs3..6 stay independent.

The opt-in private kernel layout expands fixed image/frame arrays to64,
task records to1024 bytes and claims to69 frames. Shared mechanisms retain
the ordinary8-page/256-byte/13-frame layout when not enabled. All record
strides and context offsets derive from one bounded layout definition;
physical uniqueness, alias, zero destination and cleanup checks cover every
new slot. At most133 mapping-frame records,69 task frames and64 image frames
are visited; all pair checks and copies remain fixed-capacity. Existing
physical reserve, generation, fatal/fence and complete OOM rollback rules apply.
Four tasks, eight CREATE attempts/root, CPU1..32, IPC, PIO and heap budgets
do not change. No general unbounded executable-size or source-compatibility claim.

## Boot-memory amendment (renewed user authority)

Inventory: the larger catalog and import snapshot overflow the pre-0x184000
assembly envelope. Keep that assertion, all fixed C sections and C layout4.
NativeWide alone places .native_catalog at0xa00000, exact1065344 initialized
bytes plus zero page padding to1069056 bytes, R/NX. .native_scratch follows
at0xb05000, exact266336 bytes plus page padding to270336, NOLOAD/RW-NX.
End0xb47000 is within the existing eight-page-table16MiB higher-half window.
Linker assertions require the pair, exact sizes, alignment and separation.
The existing physical allocator reserves [0,_x86_64_bootstrap_end); bind that
symbol to the complete scratch extent. No allocator rewrite or writable
direct-map alias. Explicitly clear the scratch before use, independently of
Multiboot zero-fill. Map and verify every occupied leaf before C handoff.
Do not relax the existing C-envelope verifier to accept new regions.

The build-time outer ELF32 reader accepts at most2MiB, and verify_outer admits
files over1MiB only with this exact paired native extension. The inner C ELF64
reader/validator stays at1MiB. Validate exact new section types, flags, addresses,
padding, dedicated PT_LOAD extents/permissions, symbol bounds and bootstrap end;
reject extra/missing sections, file aliases, wrong sizes, permissions and bounds.
No compressed catalog, new runtime parser, moved bridge or initialized NOLOAD.

Five additional allowed files: boot/entry.asm, config/x86_64_bootstrap.ld,
scripts/build_x86_64_c_payload.py, test/test_x86_64_c_payload.py and
test/test_x86_64_program_memory_boot.py (boot path relative to arch/x86_64).
Two extra host gates exercise actual linker/validator negative cases and actual
assembly leaf verification with corrupted first/middle/last leaves. The native
guest oracle additionally proves complete reservation, absent direct aliases,
all new page permissions and zero-before-use scratch.48 files/18 groups total.

## Frozen validation and stop boundary

New host gates run actual C producer/SDK and actual ASM admission, mapping,
claim/release, identity/context and pointer mechanisms at O0/O2 with boundary
fakes. Cover both layouts, all64 positions, malformed/overlapping records,
reserved stack bytes, guard/NX/RX permissions, full-width addresses, ownership,
stale generations, allocation failure and exact cleanup. Compare actual C
prepared output with the host producer. Include guest-observer mutations and
build integration checks; source patterns alone are not runtime evidence.

NativeWide guest matrix: normal4/8GiB, stack guard fault, stack execute fault,
RX write fault, CPU exhaustion, sleep/cancel and replacement; six OOM guests
at0/1/2, one-quarter, one-half and last acquisition of the actual child
construction count (distinct valid indices required). Each guest<=30s,
aggregate guest time<=390s. Execute independently linked code beyond32KiB,
touch and check private data and more than4KiB of real C stack, preserve an
independent peer, immutable import after parent mutation, generation-scoped
WAIT/restart and exact frame balance. A memory fixture is not a filesystem
service proof. Compiler calls<=90s, host executables<=30s, hidden QEMU only.

Retain the complete old import matrix and ordinary bootstrap; compare default
mechanism objects with accepted AI where identical build inputs apply. Original
i386 artifact verification is read-only. The new runtime records actual mapped
bytes, permissions, frame ownership and teardown, not just success markers.
No kernel C payload, common IPC or integrity-arithmetic change is authorized.

All18 groups and direct ABI/bounds/cleanup/scope review precede done and local
commit. No push, no agents. Two focused corrections per concrete gate failure,
never unchanged retries. Stop on remaining failure, pre-existing source failure,
outside-scope production needs or another authority boundary; keep every red
attempt. After clean acceptance freeze the next in-priority cohesive package
without routine handoff. R3.6b stays explicitly deferred; hardware, DMA,
writable filesystems and full OS acceptance remain separate.
