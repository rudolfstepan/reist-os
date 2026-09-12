# Native boot program admission

Status: R8.3ad contractde4fdb7b on667e9aee; attributed implementation candidate
retained, blocked at the pre-existing bootstrap IRQ-admission boundary.
Not accepted; no implementation commit or queue advancement.

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

## Blocking evidence,12 September2026

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

Required authority: amend this same transaction to close the old
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

The executable queue freezes twelve gates: producer and actual admission
behavior, old process/access/runtime/bootstrap/docs tests, three builds,
real multi-image guests, original runtime guests and the i386 artifact check.
New guest leases are20s; old leases and oracles remain unchanged. Exact frame
balance, generation fencing and every existing final zero range are required.

After acceptance, general owner-scoped start/wait/cancel and Ring3 loading
remain a separate lifecycle authority boundary; persistent storage and drivers
remain separate failure domains. R3.6b stays deferred, R341-H1/H2 stay open.
