# Native binary64 mathematics — R8.3bs

## Inventory and boundary

Starts after clean82ce94a03afda11a0f0c5277fe98e2c66bb5da4f (native C/C++),
five gates andten fresh guests. Predecessor seal
b328527b28eebc5009829a7162a373622d3b0421358fc6321aebc53bbaa6162c;
final clean receipt317a5e4a4b6e0a17a2542d0a22b6e7d4c7cea683c66d4b78463abf94c66bb4b9.
QuickJS also requires libm and bounded numeric text. Current build_user_math
hardcodes x86-freestanding/i386, no SSE and i386 lrint. The native scheduler
already owns eager FXSAVE64/FXRSTOR64 state per task (R8.3b), including
XMM0..15, x87/MMX and controls. R8.3c admits ordinary Ring3 exceptions.
Do not add another FPU mechanism or change kernel quotas to port libm.

Sources: REIST_ARCHITECTURE, roadmap/native completion work paper,
HIGH_ASSURANCE_CORE_CONTRACT, RING3_MATH_RUNTIME_CONTRACT, accepted native
C/C++ contract, cpu/fp_context.asm and actual scheduler FP save/restore/reap.
This is one numeric execution/rounding/state lifecycle slice. Numeric text,
QuickJS/worker/host, browser and further authority remain subsequent slices.
R3.6b remains expressly deferred. No new permission domain is required:
ordinary arithmetic and the existing session's private terminal/IPC rights
are reused; no network, file writing, device or script authority is added.

## Standards and implementation

ISO C11 sections7.6/7.12, IEEE754 binary64 and AMD64 System V LP64 are the
references. Port all44 existing double functions, long lrint and the four
existing fenv functions together. Keep the accepted musl1.2.6 archive pin
d585fd3b613c66151fc3249e8ed44f77020cb5e6c1e635a616d3f9f82460512a,
bounded extraction, exact original source/license bytes and generic numerical
algorithms. Select the actual upstream x86_64/lrint.c (cvtsd2si, LP64 long)
and x86_64/sqrtl.c internal helper. No host libm substitution or approximate
replacement. No errno, complete libm, float/long-double family or universal
correct-rounding claim. Internal sqrtl stays hidden/renamed.

Extend only explicit architecture-selected extraction/compilation entry points
in the existing math builder; preserve the entire i386 default build and
sources. Native artifacts use an explicit SSE2 AMD64 userspace target, no
AVX/XSAVE, MMX code generation, red zone, hosted runtime or kernel FP code.
Keep the accepted kernel/root/service binaries and C/C++ subset exact.
Publish libm.a, math headers, conventional pkg-config metadata and licenses
in the native cpp-sysroot, with independent ELF64/archive/undefined-symbol
admission. Do not silently mix i386 and AMD64 archives or incremental caches.

NativeMath implies NativeCppRuntime, separately from network/GUI profiles.
Build ordinary mathtest.prg from the existing consumer, preserving the legacy
parent/spawn mode under its original profile. The native foreground path
reuses the same numeric/environment vectors; external kernel/root lifecycle
owns crash, timeout, CPU and parent cleanup. No fake process/global statistics.
Use accepted full-width runtime terminal/clock functions and their original
5000ms/4096-operation/1024-byte limits. Preserve root WAIT1000ms, CPU32,
32768-byte stack,192KiB executable window and resource/restart budgets.
Both Windows and Make layouts package mathtest through ordinary Ring3 shell
resolution on signed seven-file media (the accepted six plus mathtest).

## Runtime evidence

Host executes actual selected algorithms/fenv at O0/O2, all44 functions,
four rounding modes, IEEE specials/flags, signed zero/subnormal, large argument
reduction and bounded independent reference samples. LP64 lrint uses positive
and negative ties, values beyond32bits, representable boundaries and invalid
conversion flags, with no out-of-range C conversion used as an oracle.
Windows host long width must be reported honestly; ELF64 compilation and the
actual guest establish the LP64 calling/result boundary.

Real guest checkpoints capture numerical result bytes and raw FP state,
fresh generation defaults, preserved controls/register payload across actual
blocking/scheduler transitions, and empty retired state. Keep the complete
existing shell CPU/frame/IPC/physical-media/no-write proof, ordinary cat/ls
progress and exact generation-bound cleanup. Raw review must reject changed
result, rounding, FP payload, generation, task outcome and incomplete reap.
Successful serial markers alone never establish acceptance.

Private zero-default diagnostic selectors may select numeric state, x87 #MF,
invalid-MXCSR #GP, UD2, hang and CPU exhaustion after real numeric work.
No CLI fault authority. Tests must use actual exception vectors/statuses:
16/144,13/141 and6/134. The QEMU TCG profile does not claim #XM delivery;
the separately documented i386 Workstation #XM proof is not a native proof.
No simulated trap or successful fallback if a required exception is absent.

## Scope and finite reservation

Queue allowed_files controls exactly one active visible-main-worktree package.
No kernel edits, nested agents/worktrees/push, unrelated changes or silent
scope expansion. Freeze any evidence-directed correction window before use;
keep all failed attempts and original gates. Initial development reservation:
hosts01..12<=600s, builds01..03<=300s, media01..02<=180s,
diagnostics01..04<=180s each. Compiler calls<=90s, at mostfour workers;
host executables<=30s. Logs under build/codex-agent/r83bs-native-math.

After direct scope/ABI/FP/cleanup/diff review, freeze five one-pass gates:

1. `python test/test_x86_64_math_runtime.py -v` (600s): real numeric/fenv
   O0/O2, LP64 admission, archive/pin/closure, media and raw-proof mutations.
2. `python scripts/verify_x86_64_math_runtime.py --defaults` (600s): complete
   disabled/default projection, original i386 math regressions, retained
   accepted CLI/GUI/network/HTTP/C++ artifacts and kernel no-FP boundary.
3. `python scripts/verify_x86_64_math_runtime.py --package` (600s): one fresh
   build<=300s/media<=180s, independent signed consumer, exact admission,
   undefined-symbol/ISA closure and compiler stack limits.
4. `python scripts/verify_x86_64_math_runtime.py --runtime` (2000s): ten fresh
   sequential guests<=180s each/1800s aggregate; healthy4g, healthy8g,
   rounding-state, x87-fault, mxcsr-fault, crash, hang, cpu, owner-loss,
   repeated. Stop at first failure; no diagnostic substitution.
5. `python scripts/verify_x86_64_math_runtime.py --review` (600s): independent
   complete ten-guest raw replay, all source/tool/media bindings, final scope
   and acceptance seal before outcome-only closure/local clean commit.

After acceptance continue the next inventoried native prerequisite. This
package alone does not complete JavaScript or the native operating system.
