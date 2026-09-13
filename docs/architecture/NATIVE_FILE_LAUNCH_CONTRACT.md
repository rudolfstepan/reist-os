# Native immutable-file execution boundary

R8.3am, frozen on clean accepted `1835ee97` after all21 R8.3al gates.
One cohesive Ring3 transaction: filesystem stat/read, immutable ELF64 capture,
existing image preparation, explicit attenuated CREATE, failure and complete
retirement. No new kernel mechanism, public syscall, file-write right or normal
OS/shell acceptance. Main interactive agent only; no nested agents or push.

## Inventory and authority

R8.3al already supplies actual FAT12/FAT32/EXT2 parsers,64-byte native envelope,
512-byte stat/read/readdir payload,8 requests/session,256-byte reads,16 cached
sectors, separate driver/FS generations and dependency fencing/replacement.
`image.c` already admits ELF64 in Ring3 and prepares immutable RNPGv2;
CREATE-v5 copies that record and independently admits mappings in Ring0.
Existing file consumers still read embedded test content; imported executables
are embedded in their supervisor, not obtained through filesystem RPC.

The native process pool still has four slots, two initial roots and two dynamic
slots, CPU1..32 and eight CREATE attempts/root. Do not silently lift those limits
to suggest a normal shell port. This transaction stages file bytes while the
driver and parser occupy slots2/3, fences/reaps both, then imports the prepared
program into free slot2. A second fresh dependency group and program generation
exercise replacement. Concurrent application/filesystem availability, long-lived
service budgets and ordinary shell integration remain later kernel boundaries.

Reading a file never grants execution, device, IPC or task-management authority.
The supervisor explicitly imports it with a reduced existing profile, no PIO or
TASK_CONTROL; only a fresh private acknowledgement endpoint is delegated. The
filesystem and block driver receive no additional authority.

## Standard-first adapter

Reuse System V ELF64 little-endian ET_EXEC/EM_X86_64, PT_LOAD/R/W/X,4KiB alignment,
argv/env/auxv and the existing RNPGv2 adapter without changing parser semantics.
The small real C qualification program uses the standard GNU ld
[FILEHDR/PHDRS layout](https://sourceware.org/binutils/docs/ld/PHDRS.html) with
headers inside an RX segment; this is not a custom executable format.
FAT/EXT2 formats and native RPC semantics remain those of
[NATIVE_FILESYSTEM_CONTRACT](NATIVE_FILESYSTEM_CONTRACT.md).

Add one reusable explicitly bounded SDK file-image helper, not an exec/POSIX
compatibility alias. It requires a fresh exact FS client generation/sequence,
one immutable-media session, a canonical absolute path and a single monotonic
deadline no greater than3000ms. Reject aliases and arithmetic overflow before
calling transport. Fixed private1536-byte file staging, no heap: one stat, at
most six256-byte reads, then one EOF read fit the existing eight-call session.
Larger/empty/nonregular files fail closed before data reads; a short read,
extra EOF byte, changed identity, transport/protocol fault or deadline failure
never publishes a prepared image. No hidden session restart or cache eviction.

The whole prepared output remains unchanged on failure. Only the existing
ELF64 adapter can publish it after every captured file byte and EOF is checked.
Scrub private file staging on every admitted exit. Malformed ELF does not reach
CREATE or consume a kernel attempt. Caller chooses argv and the attenuated
profile; these do not come from media. No signature/secure-boot claim is added
to executable files on these generated immutable test media.

## Shared implementation and complete lifecycle

Reuse the existing supervisor/driver/parser startup and fencing helpers, keeping
the old NativeFilesystem selection byte-bound to the accepted baseline. Add
explicit NativeFileLaunch/Make selectors and a separately linked real C file
program; neither defaults nor the rescue-shell command set change. This is no
new shell command: normal `/bin/shell.prg` dispatch is not claimed.

Only a finite generated `/boot.prg` file is added in the explicit file-launch
media profile. Its bytes come from the independently linked admitted ELF,
bounded by1536, plus finite malformed/oversize variants for rejection. No user
or physical disk and no arbitrary QEMU options. Existing media defaults stay
exact. Same exclusive read-only base/disposable qcow2 metadata boundary,35.84MB
base/4MiB overlay, exact backing/map/logical bytes and unchanged-before/finally
checks, including all failures. Kernel PIO remains read-only.

Detect failure -> deny publication -> physical fence/revoke -> reap pair ->
fresh pair/self-tests -> retry only as the explicitly budgeted replacement.
Application UD2, noncooperative spin and sleep/cancel use ordinary kernel
containment; independent peer survives. Owner-loss retires all descendants.
Import OOM rolls back completely before one retry; stale generations never
regain rights. Verify actual private frames, image/argv bytes, W^X/stack guards,
all CPU bounds, exact statuses, IPC/heap/FP/context cleanup and frame balance.

## Frozen verification

Thirteen targeted groups: new file-image O0/O2 behavior, new runtime/oracle and
build selection, existing FS/sector-range/media/FS-runtime, ELF import, startup,
boot producer, PIO, native IPC, syscall ABI and documentation. Three builds:
default, old NativeFilesystem, new NativeFileLaunch. Four runtime groups:
new matrix, unchanged full FS18 matrix, normal bootstrap and original i386
reference guard. Twenty groups total, plus direct scope/ABI/cleanup review and
old normal/FS object/catalog/ELF hashes. Preserve all old accepted/failed evidence.

New matrix: eighteen guests, each20s/total360s maximum, one CPU, no visible VM.
Normal five media at4GiB plus EXT2-1KiB at8GiB; application UD2/spin/cancel;
malformed ELF; FS UD2; driver UD2; owner loss; file CREATE OOM first/mid/final;
oversized file; malformed FS reply. Two real PROCESS_RUN invocations each,
fresh dependency and application replacement where applicable; malformed ELF
and oversized files degrade without any application CREATE. Bind all actual
physical bytes and independently prepared imported bytes to the linked file.
Host negatives include every short read/EOF/deadline/identity/admission failure
and retained output, not merely source patterns. Runtime oracle mutations must
reject missing/reordered/stale/fabricated execution and cleanup evidence.

Frozen commands/allowlist live in `automation/reist-s03b.toml`. Stop on outside
scope, unrelated changes, required quota/authority/persistence expansion,
pre-existing failure or the same concrete failed gate after two focused
corrections. No unchanged guest retry, diagnostic-only acceptance or weakened
oracle. All20 groups must pass before queue transition/local implementation
commit. R3.6b stays explicitly deferred; continue the next native transaction
only after a clean accepted boundary.
