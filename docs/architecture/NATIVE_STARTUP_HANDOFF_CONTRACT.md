# Native startup and IPC handoff boundary

R8.3af, frozen on accepted8a3bed10, 12 September 2026. This is a package
contract, not runtime acceptance. All13 queue groups are mandatory.

Renewed user instruction on12 September after the explicit OOM repair question
authorizes the same attributed candidate to continue. The new fixture had only
one RX page and six total CREATE allocations; injection after6/9 missed CREATE.
Give the child two genuinely used private RW pages (ten total allocations),
and guard the exact CREATE completion so missed injection fails before another
phase. Preserve all13 gates, kernel quotas and failed evidence. Revalidate the
affected host/build/full startup matrix; unaffected passed host evidence stays
valid. Renewed verification retains the one-focused-repair stop condition.

## Inventory and purpose

The native family now owns construction, waits, cancellation and complete
retirement. Its dynamic children still receive immutable catalog arguments.
The shared startup_stack core already admits eight128-byte arguments and
builds AMD64 argc/argv, empty envp and the existing REIST IPC auxiliary entry.
The native IPC binding already delegates explicit rights to generation-valued
PIDs. Reuse these mechanisms; do not invent another process or IPC service.

## Public transport and limits

TASK_CONTROL132 CREATE-v2 keeps the64-byte request layout. Only CREATE uses
v2; its last u64 is a startup pointer. Version1 retains its zero reserved
field and every existing meaning. A separate fixed1040-byte startup-v1 record
contains u32 version,size,argc,flags, then eight128-byte argument cells.
Require version1,size1040,flags0,argc0..8, a NUL within every used cell and
zero unused cells and trailing bytes. There are no embedded user pointers.

The existing SysV AMD64 startup convention remains the reference. This is
a bounded REIST prepared-image adapter, not POSIX spawn compatibility.
Environment stays empty, existing auxv remains unchanged. A supplied textual
IPC handle does not grant authority: existing IPC_DELEGATE55 is mandatory.

Copy the entire source once after ordinary native read-range validation,
then validate the pinned snapshot before charging a creation attempt or
allocating anything. Reuse one fixed4096-byte family scratch page to adapt
the argument cells to the existing startup_stack descriptor. This scratch
belongs to the family zero range; scrub it on every result and final teardown.
The SDK prepares canonical bounded records without heap allocation.

## Ownership and failure model

Four slots, two roots, eight lifetime construction attempts per root, CPU
quota1..32, heap/IPC/frame bounds and private C payload layout4 do not change.
CREATE publication, partial-frame rollback, WAIT receipts, cancellation and
owner loss continue through the accepted family mechanisms. No filesystem
parser, mutable executable record, implicit grant or restart policy in Ring0.

Real Ring3 consumers exercise configurable arguments and a generation-scoped
IPC bootstrap. A child waits for explicit delegation within a finite deadline,
using sleep or blocking IPC, never a busy poll. Invalid/stale messages fail
closed; crash/cancel retirement and replacement preserve the same owner budget.
This is a reusable startup/handoff boundary, not a complete service supervisor.

## Frozen proof

Actual assembly and SDK host behavior at O0/O2, oracle negatives, separate
normal/legacy-family/new builds, hidden4/8GiB startup guests and the complete
unchanged family matrix. Cover0/1/8 arguments, empty/127-byte values, immutable
copies after parent mutation, invalid header/pointer/quota, IPC handoff/stale
generation, crash/cancel/restart and OOM rollback with exact frame balance.
At most20s per new guest; retain old bounds and failed evidence. i386 pins
remain read-only. No new package until all13 groups and local commit pass.
