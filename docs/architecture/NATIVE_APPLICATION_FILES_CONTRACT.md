# Native application read-only objects v1 — R8.3bc

## Authority and cohesive transaction

Frozen after clean409c5d0e / accepted BB813606cf. The user's renewed
`ja mach weiter` on20 September2026 grants the immediately proposed separate
application read-only object authority. It does not broaden legacy profiles.
Implement normal cat/ls, SDK, explicit object delegation, both build/layout
paths and complete containment/recovery together, not as syscall micro-packets.

Inventory: AY forbids app FS endpoints; root owns native STAT5/READ6/READDIR7
RPC and the immutable media generation. Existing cat/ls use the legacy
STORAGE_SUBMIT client ABI, which native task profiles exclude. Existing IPC
already provides owner-only directional delegation and generation retirement;
task import, terminal transfer and bounded wait/cancel are accepted. Reuse
these mechanisms. No new kernel code or syscall, shared raw FS endpoint, device
right, writable medium or global path namespace for applications.

## Standard-first semantics and deliberate adapter limits

Keep System V AMD64 ELF64, existing x86os SDK names, byte offsets and negative
errno values. Reuse actual unmodified userspace/programs/cat.c and ls.c. Their
native adapter operates only on one explicitly selected immutable object,
not a claim of general POSIX open/exec or whole SDK compatibility. The REIST
application-object protocol is fixed-size version1 over existing IPC-v2.
It is distinct from legacy storage and native FS RPC, not a format alias.

NativeAppFiles explicitly implies WideFile. The shell chooses the requested
object from the recognized ordinary tool invocation; the command line does
not let an arbitrary file mint rights. Exactly the selected canonical path is
admitted; aliases/cwd are resolved before grant and sent as explicit startup
context. Child-provided paths cannot navigate the parent namespace. A directory
grant exposes only its captured entries, not recursive read/open authority.
File capture is <=16384 bytes; directory capture <=32 entries plus actual EOF.
An over-capacity or failed capture publishes nothing; no truncated success.

Capture the immutable snapshot in the root's bounded Ring3 storage, using the
existing driver/FS processes. Original STAT-to-SPAWN end <=120000ms bounds
code plus object capture; no renewed command clock. Copying data to a child
cannot later erase its knowledge: revocation forbids future broker operations,
not access to already delivered private bytes. No persistent object format.

## Identity, publication and lifetime

One live grant, nonreused epoch and exact root/foreground generations. Two
private IPC endpoints give the child request-send and reply-receive only.
No FS endpoint or delegate/close ownership is passed. Authenticate endpoint
authority plus bound generation/object/epoch/sequence, validate all fields,
sizes, zero reserves, operations and ranges before effect or reply publication.
All replies use a canonical fixed512-byte frame; raw payload bytes are data.
STAT, READ, READDIR and CLOSE are the only object operations, plus initial
binding/self-test. Legacy SDK wrappers adapt explicit handles without
fabricating storage success. Unknown, foreign, stale, closed, exhausted or
expired grants fail closed. Same object cannot rebind/reset its budget.

At most80 requests and one absolute1000ms application/broker lifetime, never
renewed by RPC success; per-call IPC<=1000ms and cleanup wait<=1000ms. No
userspace spin: bounded IPC waits or blocking sleep; task wait/cancel at the
original finite end. CPU32/1000ms, ATA200ms, construction8/1000ms and recovery
2/10000ms remain unchanged. Old profile wait and default imports unchanged.
Broker close/revoke precedes reuse/next foreground. Child exit/crash/hang/quota
must not kill root or peer; uncertain cleanup stops root for kernel fencing.
Root loss revokes its endpoints and descendants through existing lifecycle.
Service/capture error follows existing isolate/fence/reap/recreate/self-test;
never preserve a grant across a failed source generation. No automatic retry
of a partially granted request, reset of exhausted budgets or read rights from
merely finding an executable. Old AY/BA/BB evidence remains separate.

## Frozen verification

Queue lists exact allowed files and nine ordered gates. Host regressions first:
actual C broker/client/root adapter O0/O2, real tool main functions, malformed
and stale requests, overflow, no publication on failure, budgets, cleanup and
old disabled code equality. Actual generated FAT12/FAT32/EXT2-1k/2k/4k media
through existing filesystem parsers, tool lookup and both Windows/Make layouts.
One common new image only after hosts/dependencies pass; no per-case build.

Sixteen complete guests on that image: five compatible layouts,8GiB, repeated
cat/ls and object/stale/foreign/unsupported/write-denial checks; child crash,
hang, quota, root loss, driver crash/hang and malformed FS reply/recovery.
Freeze exact case mapping and input plans in the runtime test before execution.
Each guest300s including cleanup3s, aggregate4800s, matrix gate5400s. Full raw
IPC/CPU/lifecycle/terminal/PIO/snapshot assertions and independent replay;
serial markers alone never qualify. Validate actual file bytes/entries and
foreground task origins, isolation, fence/reap and immutable base/COW state.

No signed BIOS publication in this application-authority package: BB's signed
pair is independently pinned. New generated data/tool layouts accompany the
explicit Windows/Make native profile; signing the resulting new image is a
separate trust/publication transaction after acceptance. Preserve existing
reference artifacts. Stop first failed gate; freeze evidence-directed finite
corrections without routine approval, preserve all failed work and costs.
Acceptance requires all gates, direct diff/scope review, done transition, clean
local commit and bound final receipt. No push, nested agents, user disks or
full64-bit OS/desktop/hardware/production-trust claim. R3.6b remains deferred.
