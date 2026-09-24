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
