# Native C/C++ allocation runtime — R8.3br

## Inventory and priority

Starts after clean HTTP52eb89e81349223148cf888d3632b278301381eb, five gates and
25 guests, seal472ae6b447871fc3d0ee17bcd7b990b5e77a988c48eea002cc22574e19813a03,
final receiptddf44a3dbb003478260826c3a73ecdbe1ce583de86ff245b8df74ca93765aae2.
The next shared userspace prerequisite is ordinary C/C++ process allocation.
JavaScript's existing QuickJS worker depends on this allocator; its process
provider currently asserts an i386-only28-byte callback layout. Existing
native shell applications already receive private MALLOC/FREE/REALLOC rights
through SESSION_MASK; NativeHeap and generation-scoped cleanup are accepted.
This package introduces no new authority domain and no kernel changes.

Reuse userspace/libc (heap/bytes/runtime/process_heap), userspace/cpp/runtime.cpp,
the six accepted C++ value/ownership types, and ordinary cpptest.cpp. Preserve
explicit initialization, bounded provider callbacks, OOM/failed-realloc
preservation and whole-empty-region return. Inventory sources:
PRIVATE_PROCESS_MEMORY_CONTRACT, NATIVE_PRIVATE_HEAP_CONTRACT,
USERSPACE_SDK_AND_PORTABILITY, HIGH_ASSURANCE_CORE_CONTRACT and the native64
completion work paper. JavaScript worker/host, math/text/engine, browser,
TLS/time/entropy and persistent files remain subsequent independent slices.
R3.6b remains expressly deferred.

## Complete slice and compatibility

Opt-in NativeCppRuntime implies the accepted NativeAppFiles prerequisites;
it is a separate profile from network/GUI, with unchanged ordinary cat/ls/probe,
root, driver and filesystem mechanisms. Package cpptest.prg through normal
Ring3 shell command resolution in both Windows and Make layouts. Use a signed
six-file immutable medium (boot/cat/ls/probe/data/cpptest), independent media
consumer and unchanged earlier artifact pins.

Provide conventional ELF64 relocatable objects/archives and native libc/C++
headers in an explicit native sysroot. C11/C++20 and AMD64 System V LP64 are the
references. Keep default i386 object admission/build output unchanged. Extend
the existing bounded ELF/archive C++ admission with an explicit AMD64 selector,
checking class/machine/header/section/symbol sizes before parsing. Continue
rejecting dynamic initialization, guards, exceptions/RTTI, unwinding, TLS,
thread APIs and hosted STL; no silent discard of forbidden input sections.
No complete libc, POSIX or C++ standard-library compatibility claim.

Backing callbacks are process-local C ABI, never an IPC wire structure. Retain
i386 size28 and add explicit LP64 size40/layout assertions; fixed-width stats
remain24 bytes/version1. Preserve object/region/process ceilings and max_align_t
alignment. No 32-bit cast of pointers, capacities or syscall results. Reuse
native full-width syscall transport for admitted private heap operations and
bounded terminal/IPC operations only. Unsupported legacy process inventory,
child-spawn, file/device/network or global memory-statistics operations are
excluded or fail explicitly; never synthesize successful global statistics.

The ordinary C++ consumer reuses lifetime/new/delete/alignment and bounded
type/handle tests. Native foreground mode leaves external crash/hang/CPU/
parent supervision to the existing shell/kernel lifecycle. Real raw frame and
heap evidence replaces unavailable legacy global memory statistics. Failures
must terminate only the affected application and permit a fresh normal run;
no destructor claim for forcibly terminated processes. Existing native stack,
image,32-tick foreground CPU and root/service limits remain unchanged. A
private debugger-only zero-default selector may inject faults after live heap
acquisition; it grants no script or CLI authority. Shell launch remains the
normal cpptest command, not a rescue-shell entry.

## Scope, reservation and frozen gates

One active visible-main-worktree package; allowed_files in the queue controls
all implementation. No nested agents/worktrees/push. Stop on scope expansion,
unattributed changes or new authority; routine in-scope correction windows may
be recorded without another approval. Initial development reservation:
hosts01..12 <=600s, builds01..03 <=300s, media01..03 <=180s,
diagnostics01..06 <=180s. Preserve every exclusive attempt receipt and failed
input; no unchanged retry. Logs under build/codex-agent/r83br-cpp-runtime.

Before qualification, review final diff and all new-file whitespace, exact
scope, source/tool bindings, ABI layouts, cleanup and native syscall rights.
Freeze once, then no source changes during the five gates:

1. `python test/test_x86_64_cpp_runtime.py -v` (600s): real C/C++ O0/O2
   allocator/provider/runtime/types, high-address pointers, OOM/realloc,
   corruption/fatal paths, native SDK error/clock/output behavior, ELF64 and
   retained i386 admission, media and raw-proof mutation regressions.
2. `python scripts/verify_x86_64_cpp_runtime.py --defaults` (600s): full
   disabled source/build projection, original i386 regression/artifact pins
   and retained accepted CLI/GUI/UDP/TCP/DNS/HTTP artifacts.
3. `python scripts/verify_x86_64_cpp_runtime.py --package` (600s): fresh
   native reference build<=300s, signed media<=180s, independent consumer,
   exact ELF/archive admission and compiler stack limits.
4. `python scripts/verify_x86_64_cpp_runtime.py --runtime` (2000s): ten fresh
   sequential guests<=180s each/1800s aggregate; stop first failure. Cases:
   healthy4g, healthy8g, realloc-failure, heap-fault, new-oom, crash, hang, cpu,
   owner-loss, repeated. Actual allocations above4GiB virtual, aligned objects,
   preserved bytes on failure, returned backing, exact family generations,
   CPU/heap/frames/endpoints, parent loss, and ordinary cat/ls progress must be
   independently checked from raw guest evidence, not just output markers.
5. `python scripts/verify_x86_64_cpp_runtime.py --review` (600s): complete
   independent raw replay, all source/tool/artifact bindings and exact scope,
   acceptance seal before queue/documentation closure and local commit.

After all gates and clean commit, continue the next inventoried native64
prerequisite. This slice alone does not complete JavaScript or the native OS.
