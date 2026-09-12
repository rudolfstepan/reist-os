# Native prepared image import boundary

R8.3ag, frozen on accepted7757c747, 12 September 2026. Thirteen mandatory
gate groups in the queue; no runtime acceptance at contract freeze.

## Inventory and cohesive purpose

CREATE-v2 admits immutable arguments but selects only four boot records.
The existing boot_program_admit64 and frame loader already consume bounded
RNPGv1 records, and retirement releases selected images after task frames.
The host Python producer parses ELF64; the old i386 MYPR validator is not an
ELF64 userspace loader. Reuse existing mapping/admission/rollback mechanisms.
Add a reusable freestanding Ring3 C ELF64-to-record adapter and CREATE-v3
record transport together, including SDK, both build frontends and full guest
failure/ownership proof. No ELF parser or file/device policy enters Ring0.
This enables a future file loader; this package itself grants no file access.

## Public contract and authority

The reference remains System V ELF64 little-endian ET_EXEC AMD64 and its
PT_LOAD terminology, flags, alignment and byte units. The bounded REIST
adapter retains the existing host producer subset: at most65536 input bytes,
eight program headers, eight4KiB image pages at0x400000..0x408000,
read/RX/RW only, no page overlap, executable file-backed entry, no dynamic
linking or relocation. Reject malformed inputs before writing output.
C adapter operates on disjoint mapped C objects, no heap or raw syscall.
The existing RNPGv1 fixed36896-byte record stays unchanged; CREATE-v3 uses
its zero-argument tail while separate startup-v1 owns actual arguments.

TASK_CONTROL132 CREATE-v3 retains64 bytes: image becomes a pointer to one
complete RNPGv1 record; startup remains the1040-byte pointer. Versions1/2
keep all meanings. Copy both full user ranges once into fixed scrubbed
scratch before charging an attempt or allocating. Independently admit the
prepared mapping record in Ring0. A text filename or record supplies no extra
syscall/IPC/device authority. Same child syscall attenuation and root-only
CREATE. No new syscall number or child delegation.

Two private imported-image contexts7/8 belong exactly to dynamic slots2/3;
they cannot alias immutable catalog IDs3..6 or each other. Internal context
storage grows from7 to9 only in NativeLifecycle, not any task/heap quota.
Reject malformed/unmapped source with no charged attempt or published task.
Private staging and full image/task ownership rollback precede receipt;
scrub the entire36896-byte image scratch on every result and final teardown.
Partial allocation remains ENOMEM, never a kernel fault or silent success.
Four tasks, two roots, eight lifetime attempts/root, CPU1..32 and all existing
IPC/heap/frame budgets remain unchanged.

## Integration and proof

NativeImport presets NativeStartup; old fixtures remain unchanged. The import
fixture parses an independently linked child ELF in Ring3, creates both
dynamic slots concurrently, mutates source records after CREATE and exercises
the established immutable argv/IPC/fault/cancel/replacement sequence. Both
import contexts, high physical frames, private RW pages, W^X, exact bytes,
generation fences, complete scratch/context clearing and frame balance must
be independently observed. Normal4/8GiB and OOM0/1/2/3/6/9 share one matrix,
at most20s per guest. Old startup eight-case matrix, normal bootstrap and
read-only i386 pins remain mandatory; no unrelated hardware matrix.

The import-only root linker may use two RX pages within the unchanged
eight-page image window to hold the C parser and consumer. Old one-page
linker stays exact. Root input is an embedded immutable ELF byte fixture,
not filesystem authority. Host O0/O2 executes real C parser and assembly
admission; compare valid C output byte-for-byte with the existing Python
producer and cover malformed headers, offsets, ranges, overlap, permissions,
argument transport and unchanged output on rejection. Negative guest oracles
cover source/cross-context/cleanup failures. No synthetic success replaces
actual guest execution.

Stop on unattributed changes, required files outside frozen scope, quota or
deadline widening, or a frozen gate failing after one focused in-scope repair.
Only after all13 groups, direct ABI/ownership/rollback/scope review and clean
local commit may the next native package start. R3.6b remains deferred;
R341-H1/H2 stay open. No full OS, general filesystem or supervisor claim.
