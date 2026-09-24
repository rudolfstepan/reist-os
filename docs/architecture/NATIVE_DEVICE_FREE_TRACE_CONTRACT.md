# Device-free qualification trace prerequisite (CE)

User renewed mach weiter after reported CD scope stop. This separately frozen
prerequisite changes no authority domain or CPU limit. CD candidate is preserved
in scope-stop01/files.zip SHA256 b35598ac164aae27085acc63718d66890524957adea4edeeeaf05412030ecc45
and stash5e56958408f1b47a589d50bdc23a6565b78690cf. All CD failures remain failures;
CB archive/counters and deferred R3.6b remain unchanged.

## Mechanism and failure model

Add explicit NativeCPUTrace/X86_64_NATIVE_CPU_TRACE=1 for the existing device-free
NativeServiceCPU profile. Never synthesize PIO authority. Keep existing PIO trace
selection/output exact; disabled profiles byte-exact. NASM requires ServiceCPU
plus either existing PoolPIO or explicit DEVICE_FREE_CPU_TRACE. No change below
the producer admission guard: private LE192 trace-v1,256 entries/2048 lifetime
samples, fixed BSS, IRQ-disabled single producer, exact register/flag preservation,
no allocation/wait/logging, observational errors never repair accounting.
No ABI, workload timing, scheduler, resource limit or release change.

## Frozen verification and reservations

Initial development: one clean serviceCPU baseline build <=300s before source
edits; up to4 host tests<=180s,2 selected builds<=300s,2 diagnostic guests<=60s.
Five final gates, each exactly once per frozen candidate:
1. python test/test_x86_64_device_free_trace.py -v (180s): actual production
   trace/core O0/O2 via existing harness on PIO and device-free; consumer corrupt
   records, overflow, IF, generations, time and closure; invalid selectors rejected.
2. verify --defaults (360s): fresh ServiceCPU build, every artifact byte-equal to
   clean baseline; old PIO producer assembly byte-equal and exact recipe projection.
3. verify --package (360s): explicit selector build, ELF/symbol/layout validation;
   all userspace artifacts exact versus disabled, trace outside scheduler reset.
4. verify --runtime (180s): two fresh device-free serviceCPU guests case0(normal)
   and case3(exhaust/recovery), each<=60s,total<=120s. Existing full pool/CPU oracle
   and actual192-byte trace replay; no per-charge breakpoint, only ring-full and
   existing lifecycle hooks. Guest CPU limits unchanged. Host capture may use57s
   plus transport grace within60s. Runtime claims require complete both-root proof.
5. verify --review (180s): source/tool/image/evidence binding, independent full
   replay of both captures plus missing/changed/reordered trace rejection.

Verifier freezes source/tools/package/HEAD before gate1, records exclusive
started/result/log files and stops at first failure. No retry or failed candidate
commit. Inspect direct final diff and scope; after all gates pass mark CE done,
reactivate CD, commit locally, then restore exact CD candidate with CE selectors
merged explicitly and preserve CD frozen gates. Never push or run another agent.

## Development evidence before qualification01

Clean baseline56 artifacts passed6.107s. Host01 failed in the new harness
indentation, host02 then demonstrated the expected rejected device-free guard.
Host03 seven actual producer/consumer/selector tests passed3.091s. Selected
development build01 passed; diagnostic01 normal guest passed14.482s with16
complete task lifecycles/769 exact charge records, full ring wrapping/closure.
One diagnostic and one selected build remain available; no final gates run.

Inventory found the two root .o files embed the random import_blob.h directory
in DWARF. Exact disabled equivalence uses the established same-header-path
method: require identical generated header bytes, recompile actual source with
original flags and original header path, compare entire raw object bytes. No
stripping, normalization, instruction or symbol exclusion; all other artifacts
compare directly. Reserve four compiler calls<=60s total per pair within the
frozen defaults/package gates. Sources and producer recipe unchanged.

qualification01 host passed3.145s; disabled native build passed. The standalone
same-header compiler failed because its implicit Zig cache was outside the
workspace. No object comparison, selected final build or guest took place.
Preserve that failure. Set explicit workspace Zig cache directories, matching
the production builder. Reserve qualification02 with the same five gates and
limits; this changes only host compiler environment, no guest or acceptance gate.

qualification02 host/default build and both same-header raw object comparisons
passed. The recipe text projection then failed because Path.read_text used the
Windows legacy codec while git.decode used UTF-8. Original Makefile bytes are
unchanged outside the explicit selector additions. Use UTF-8 for source text
comparison; reserve qualification03 with identical five gates/limits. No selected
final build or final guest has yet run. The accidental diagnostic defaults() call
was rejected by the fresh-directory guard before executing a build.

qualification03 five commands passed3.090/9.488/9.537/31.389/3.252s. Both
guests passed15.183/13.856s with16 complete lifecycles each,791/725 charges.
Post-gate seal audit detected exactly one mismatch: review.log was still open
when review generated its seal and subsequent binding warnings appended to it.
Do not accept that seal. Review now writes a proof excluding only its actively
open log; the outer verifier checks all reviewed bytes after all five commands
close, then seals every complete log/receipt/evidence file. Reserve qualification04
with the unchanged five gates/two fresh guests; preserve03 including bad seal.
No guest or observer code changed and no safety criterion waived.
