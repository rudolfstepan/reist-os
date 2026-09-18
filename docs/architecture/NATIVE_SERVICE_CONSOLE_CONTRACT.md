# Native service-root console authority — R8.3au

18 September 2026. Active, not yet qualified. User explicitly approves the
additional console authority for the initial shell root only. Baseline473da11c.

## Boundary

This is the kernel authority prerequisite for composing the accepted normal
shell with the accepted Ring3 file-service domain. Qualify the new authority
boundary with the full existing service fault matrix before normal-shell
namespace/launch integration. It does not finish the OS or grant a child TTY.

Explicit NativeServiceConsole requires NativeLiveFile, excludes NativeConsole,
NativeShell and other service fixtures, and enables the existing bounded UART
mediator. In this profile only initial root slot0 in run-v5 may request bits15
and20. Existing NativeConsole remains run-v2 only. Other run versions, initial
peer, reserved child slots, driver, filesystem and imported applications never
receive those bits. The existing family profile allowlist continues to reject
them even if the parent possesses them. No inheritance or terminal transfer.

Reuse POSIX-inspired nonblocking read/write byte semantics documented in
NATIVE_CONSOLE_CONTRACT.md, AMD64 System V and existing versioned REIST run/task
ABIs. No new public ABI, POSIX compatibility claim or file descriptor policy.
Generation admission, whole-range validation,64-byte operation bound, partial
progress/errors, quotas, service periods and cleanup remain unchanged.

## Proof

Regression first: execute actual descriptor admission for valid v5 root and
every rejected version/slot/malformed descriptor; execute actual child profile
admission with and without parent console authority. Verify no descriptor writes.
Retain existing mediator/SDK, pool, service CPU, PIO, file and producer tests.
Prove all old profile command vectors and disabled-source behavior unchanged.

One new common image runs the complete25-case LiveFile matrix unchanged:
five media layouts,4/8GiB, application exit/fault/hang/cancel, service and driver
fault/hang/quota/cancel, owner loss, malformed replies/ELF, oversize and OOM.
Additionally exercise root console operations while dependencies and application
are alive, and denied READ/WRITE in each other role. Capture raw generation,
profile, call arguments, before/after bytes and return values. No marker-only
proof. All inherited CPU, complete mappings, private ownership, FP, IPC, heap,
frame cleanup, independent binary transport comparison and disk proofs remain.
Replacement roots get only their own generation-scoped rights.

No media parser, driver policy, polling loop, allocation or formatted output is
added to Ring0. No changes to child profile, UART mediator, shared capture,
CPU/PIO core or physical corruption response. Their exact source binding is
mandatory; no borrowing runtime evidence across changed safety mechanisms.

## Frozen execution

Queue defines12 gates: seven host groups, defaults, build, complete runtime,
reference protection, raw review. Hosts300s, other non-runtime gates180s,
runtime1200s. One image,25 guests,45s each inclusive cleanup<=3s,1125s total.
First failure stops later gates. Preserve sources, commands, tool hashes,
logs, every failure and cumulative spent counts. No unchanged retry.
In-scope evidence-directed corrections require a separately frozen finite
window under standing continuation authority, not routine renewed approval.
Successful direct diff/ABI/bounds/cleanup review precedes queue completion and
local commit. Never push. Normal-shell namespace/launch remains next.
