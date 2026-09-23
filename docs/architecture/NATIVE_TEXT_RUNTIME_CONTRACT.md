# Native bounded string formatting — R8.3bt

Frozen after accepted native math9e9e31f0, 23 September2026. Interactive
main-worktree execution, one active package, no agents or push. This contract
extends RING3_STRING_FORMAT_CONTRACT to the existing native AMD64 process
profile; it grants no new authority. Native64 completion remains open.

## Inventory and references

Reuse musl1.2.6 pinned by build_user_math.py, the existing build_user_text.py
extractor and exact-match adapters, private memory stream, public snprintf and
vsnprintf headers, per-process libc errno and accepted libm. ISO C11 N1570
7.21.6.1/5/12 and POSIX.1-2024 error conventions remain the references.
The target is System V AMD64 LP64 with SSE2, no red zone, AVX or MMX.
Windows numeric host evidence is LLP64 and cannot substitute for LP64 guest
or AMD64 variadic-register/stack evidence. No full libc/POSIX compatibility.

All integer lengths, floating conversions, long double, positional arguments,
width/precision, truncation, count overflow, C-locale wide conversions and %n
belong to this single existing formatter failure domain. Retain normal C
pointer/type/object/non-overlap preconditions. Discarded padding must remain
capacity-aware; no billion-iteration loop for a short output buffer. Invalid
process pointers must produce contained real faults. No heap, VFS, driver,
file-stream, locale service, kernel formatter or fabricated successful I/O.

## Implementation boundary

Append an explicit x86_64 selector to compile_text with i386 default unchanged.
Publish ELF64 libreisttext.a, opt-in headers, pkg-config and upstream licenses
alongside the accepted native C/C++/math sysroot. Strong byte/errno symbols
must resolve from accepted libc; inspect actual undefined symbols, linker map,
instruction set and static stack usage. No duplicate division/math helpers.

NativeText implies NativeMath in both build frontends. Reuse the accepted
NativeMathHardware rendezvous only for WHPX qualification. Package ordinary
texttest.prg on the existing shell search path and a separately signed eight-file
read-only EXT2 medium retaining all seven accepted math files byte-for-byte.
Do not modify default images, existing kernel mechanisms or syscall quotas.

Reuse text vectors with actual-ABI long expectations. Retain the old i386
and host1MiB object cases; native fixed-image vectors use an explicit8192-byte
object plus INT_MAX discarded-width/precision cases. This is a test-object
bound, not a formatter API size limit. Add native GP/FP register and stack
varargs, mixed long/double/long-double, va_copy, canaries and %n length proofs.

The foreground test uses the existing fixed5000ms/4096-operation/1024-output
profile and shell wait/CPU bounds. Private zero-default qualification selection
is not a command-line capability. Observe fresh errno/FP defaults, completed
formatting witnesses, a real bounded sleep with errno/rounding preservation,
and actual generation-scoped reap. Normal execution, invalid %s read, invalid
destination, invalid %n write, UD2, sleeping hang, CPU spin, owner loss and
repeated starts must retain the complete accepted shell/IPC/PIO/RET/resource
proof. Never infer fault success from output text or tolerate missing witnesses.
One normal4GiB and8GiB case plus the eight failure/reuse cases give ten guests.

## Frozen verification and finite reservation

Five gates, each executed once per candidate; stop at first failure:

1. `python test/test_x86_64_text_runtime.py -v` (600s).
2. `python scripts/verify_x86_64_text_runtime.py --defaults` (600s): actual
   retained i386 text tests, full disabled-source projection and accepted
   native math/CLI/GUI/network/C++ artifact bindings.
3. `python scripts/verify_x86_64_text_runtime.py --package` (600s): ordinary
   and hardware builds, signed eight-file medium, exact prior program bytes,
   bounded stacks and archive/link closure. Build300s, media180s individually.
4. `python scripts/verify_x86_64_text_runtime.py --runtime` (2200s): ten fresh
   guests180s each,1800s aggregate, fixed profile quotas and raw snapshots.
5. `python scripts/verify_x86_64_text_runtime.py --review` (600s): independent
   full raw replay, source/tool/media binding, scope and cleanup review/seal.

Initial development reservation: eight host invocations600s each, two native
builds300s each, two media180s each and three diagnostic guests180s each.
Every attempt gets a fresh numbered receipt under ignored
build/codex-agent/r83bt-native-text. Preserve failures; evidence-directed
correction windows require an appended finite reservation before execution.
Use accepted BS portable binding09/compile-freeze13 as an immutable tool.
No portable-QEMU source edits or new tool build are in this package scope.

After all gates, only queue and the two current-work documents may change for
closure. Verify frozen source hashes, commit locally and verify a clean tree.
Then inventory the next native64 package. QuickJS/DOM, new time or file/network
rights and R3.6b VMware pointer work remain outside this package.
