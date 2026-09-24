# Bounded parallel desktop build (R8.3bz)

Frozen on clean8eec74fc for the user's repeated development-speed request.
Failure boundary: host compiler execution and deterministic build evidence.
Use Python concurrent.futures with at most four concurrent compiler children,
at most64 compilation commands, bounded batches and no detached processes.
The existing30s per-command and180s whole-build limits remain unchanged.
Keep ELF64/System V AMD64 output, flags, sources, link order and import checks.
Preassign command numbers and separate logs before executing a batch. Write
the manifest in the coordinator. On failure join the current bounded batch,
propagate the original error and never start the next batch or linker.
The linker runs once, serially after every compilation succeeds.

Scope is exactly the queue allowed_files. No guest, device authority, display
quota or ABI change. This improves development builds, not desktop frame rate.
Six development host commands <=180s each; no guest/build diagnostic runs.
Three frozen gates <=180s each, once:

1. python test/test_x86_64_desktop_inventory.py -v
   Existing parser tests plus bounded concurrency, sequential mode, invalid
   admission and failure propagation with no subsequent-batch work.
2. python scripts/build_x86_64_desktop_inventory.py --output build/codex-agent/native-vmware-desktop/parallel-default01
   Real35-source build and existing byte-exact accepted default-object check.
3. python scripts/build_x86_64_desktop_inventory.py --native-workspace --output build/codex-agent/native-vmware-desktop/parallel-native01
   Real36-source build, existing bounds/import checks and compare linked object
   and individual objects against accepted workspace-native01/report.json.

Retain complete command logs under ignored build/codex-agent. Compare measured
build elapsed time with the accepted same-mode baseline; do not promise a
specific speedup before measurement. No full guest matrix is relevant to this
host-only change. Actual native SDK/service integration remains outstanding.

## Acceptance2026-09-24

Development01 records the expected missing-function regression; development02
passes all seven tests. Two of six host reservations spent. All three frozen
gates pass once in0.137/5.811/6.011s. Actual compile/build times are5.658s
(default) and5.861s(native), versus accepted sequential13.796/13.747s.
All36 default and37 native individual/linked objects are byte-identical to
the accepted workspace builds, verified against both stored hashes and actual
files. The timing comparison uses prior accepted runs, not a controlled
benchmark; current host load/cache can affect elapsed time. Source hashes
match before/after all gates. Evidence and full per-command logs are retained
under build/codex-agent/native-vmware-desktop/parallel-gates01 and the two
parallel-default01/parallel-native01 directories. No new guest or UI claim.
