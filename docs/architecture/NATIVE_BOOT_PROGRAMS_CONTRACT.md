# Native boot program admission

Status: R8.3ad frozen on667e9aee; not yet implemented or accepted.

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
