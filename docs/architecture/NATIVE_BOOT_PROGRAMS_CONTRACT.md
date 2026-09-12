# Native boot program admission

Status: implemented on667e9aee under contractsde4fdb7b/f5357439. The original
blocker below is corrected; final13-group acceptance/commit is recorded in
the executable queue. Prepared boot admission is not a completed native OS.

## Implementation evidence

Six new host tests cover actual fixed-record/run-v2/startup assembly and the
preemption IF branches O0/O2, producer malformed-input rejection, preservation
of the old catalog on failed publication, guest-oracle mutations and cleanup
after debugger startup failure. The old IF behavior has a retained failing
regression before the correction; the flags test exercises49152 combinations
at each optimization level without widening forbidden flags.

Final new matrix: attempta9533e48306e447c81f48e01e718b341,37.284s, under
`build/codex-agent/r83ad-programs/guests/`. Normal4/8GiB, UD2 and CPU32 complete
32 native task lifetimes and100 total old/new frame retirements. Six negative
guests reject malformed header/rights/arguments and allocation failure after
0/1/2 acquisitions, with exact pre-load free count and zero retained ownership.
All positive guests verify each actual mapped page, permissions, private frame,
initial stack, argc/argv/envp/auxv and all14 final scrub ranges. Heap controls,
regions and table records and every image context are empty after retirement.

The debugger queries `monitor info pic` read-only before the preemption test's
first task. Six of ten guests observe IRQ0 pending and unmasked with IF0;
the exact subsequent admissions are A(IF0,unarmed), B(IF1,armed), A(IF0,unarmed).
No controller mutation, delayed deadline, ignored IRQ or removed fatal check.
At least one actual pending IRQ is mandatory for accepting the matrix.
The normal bootstrap guest, existing long-runtime/2^32/heap/IPC/CPU guests
and pinned i386 artifact verification also pass. Their original limits remain.

The three legacy staged contexts remain the prefix of seven bounded contexts;
four prepared records add147584 immutable bytes, not a parser. Run-v1 and
default catalog absence remain supported. No public syscall or C-payload
layout change. Fixed image/argument bounds are deliberate bootstrap limits;
the four test programs are not new shell commands or a filesystem search path.

## Authorized same-package amendment

The renewed bundling instruction after the explicit extension question on
12September2026 authorizes correcting this old timer/IF admission window in
the retained candidate. TaskA in the legacy preemption fixture is cooperative:
IF stays clear before its first yield and after taskB retirement/disarm.
Only taskB may start with IF set under the armed timer. The existing syscall
gate must validate these exact states, not simply relax its IF check.
Other modes retain their flags contract. No timer, EOI or fatal-path bypass.

Rebuilt scheduler bytes may change for this correction in all bootstrap
profiles; this explicitly replaces the old byte-identity requirement for that
mechanism only. Pinned old signed media and i386 references are never changed.
Actual assembly regression and pending-IRQ guest observation join existing
gates. All twelve original commands/bounds remain, with one additional
unchanged normal bootstrap runtime gate (thirteen groups total).
The contract amendment is committed alone; attributed candidate edits remain
visible and uncommitted until complete acceptance.

## Historical blocking evidence,12 September2026 (resolved)

The two initial host groups pass (actual prepared/run-v2/startup assembly
O0/O2 and external producer rejection). NativePrograms builds, layout4 retained.
Four positive guests pass in22.235s: normal4/8GiB, UD2 and32-sample CPU
exhaustion, eight task lifetimes each, exact private mappings/argv/BSS/heap,
IPC fences, image ownership, all14 scrub ranges and total frame balance.
Evidence: `build/codex-agent/r83ad-programs/guests/attempt-13cf1b5b5c954f0392561cfd7a80f41b`.
This was only the positive subset, not the complete frozen runtime gate.

The expanded matrix stops at its first malformed-header case, before the
catalog injection. The same failure recurs with the full baseline observers
(attempt61f16781b3ff4a9e8c565546011208c5,25.709s). Diagnostic95db939191924f8ea455589c446af425
breaks at `x86_64_timer_interrupt64.invalid`: tick/EOI3, timer generation0,
active0, deadline0, user CS0x33, RIP0x400000, RFLAGS0x10202 and
CR3=0x100003000. A pending IRQ0 reaches the unarmed timer and fails closed.

Existing `scheduler_build_task64.preempt_ids` sets IF for both legacy tasks;
only the later `scheduler_handle_yield64.preemption_yield` arms the timer.
No new catalog process has been admitted or executed at this point. This is
a pre-existing source failure under the repository stop rule, not an OOM
rollback result. Original failed traces are retained; no deadline, expected
fault, hardware state or old oracle has been changed to hide it.

The authority requested at the stop was to amend this same transaction to close the old
preemption-test timer/IF admission window and prove a pending-IRQ regression,
with affected old-reference gates renewed. Do not silently change the frozen
default-profile guarantee. The remaining negative cases and old-reference
gates stay unaccepted until that boundary is resolved.

This transaction combines external executable preparation, independent image
ownership, initial arguments and complete retirement. It is the trusted boot
admission boundary, not a filesystem loader or an automatic supervisor.

## Standards and explicit limits

The input is [System V ELF64](https://refspecs.linuxfoundation.org/elf/gabi4%2B/ch5.pheader.html),
with [AMD64 process entry](https://gitlab.com/x86-psABIs/x86-64-ABI).
Only static little-endian ET_EXEC/EM_X86_64 is admitted; no interpreter,
dynamic relocations or TLS. At most64KiB input, eight program headers and
eight4KiB image pages at0x400000. Segments must be ascending, page-disjoint,
readable, non-W+X, with a file-backed executable entry. Unsupported input
fails before output publication. Section headers do not grant authority.

A private version1 prepared record consists of a32-byte header,32768 image
bytes and a4096-byte argument-source page. Header: eight-byte magic,
uint32 version/size, uint64 entry, eight standard PF_* page flags. Four
records form the bounded catalog. The kernel checks fixed metadata, never
parses incoming ELF files. Build inputs belong to the same trusted authority
as the embedded kernel; this does not create a runtime executable trust store.

Private run version2 uses its existing final task word as catalog image ID;
version1 keeps that word zero and retains the original probe. No public ABI
is repurposed. Two independent four-task runs permute the four images.
Initial stack reuses the existing bounded AMD64 argc/argv adapter: at most
eight128-byte strings, empty envp and explicit REIST IPC auxiliary entry,
not a claim of complete Linux process-environment compatibility.

## Failure and ownership

Prepared metadata and arguments are admitted before allocation. Every acquired
staged page is recorded in the existing image owner before another acquisition;
the existing release helper rolls back partial acquisition. R/RX are shared
read-only; RW and the stack are private. Image contexts remain owned until all
dependent tasks have been fenced and reaped. Terminal user fault and CPU quota
exhaustion follow the same IPC/heap/task retirement as orderly exit. No quota
or automatic restart replenishment is added. Four slots,32 CPU samples and
the existing heap, clock, stack and C-payload limits remain unchanged.

## Acceptance and next boundary

The executable queue freezes thirteen gates: producer and actual admission
behavior, old process/access/runtime/bootstrap/docs tests, three builds,
real multi-image guests, original runtime guests, the i386 artifact check and
the unchanged normal bootstrap guest added by the authorized amendment.
New guest leases are20s; old leases and oracles remain unchanged. Exact frame
balance, generation fencing and every existing final zero range are required.

After acceptance, general owner-scoped start/wait/cancel and Ring3 loading
remain a separate lifecycle authority boundary; persistent storage and drivers
remain separate failure domains. R3.6b stays deferred, R341-H1/H2 stay open.
