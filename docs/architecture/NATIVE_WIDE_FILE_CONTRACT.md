# Native bounded wide-file profile — R8.3ba

User approval20 September2026 follows accepted AZ5db38510 and inventory77b37880.
Exactly one main-worktree implementation transaction. No agents, push, user or
physical media; R3.6b remains deferred. This is not full OS acceptance.

## Boundary and standards

Reuse the actual Ring3 ATA, FAT12/FAT32/EXT2 parsers, native block/FS RPC-v1,
System V AMD64 ELF64 ET_EXEC, unchanged RNPGv2 and kernel CREATE validation.
No persistent format, write operation, DMA, additional controller or Ring0 parser.
The existing ELF input ceiling524288 bytes does not enlarge its64-page mapping
extent, reserved stack/guards or W^X rules. File bytes grant no rights.

Legacy file capture1536/FS8/block16/3000ms/100ms pacing and every old entrypoint,
structure, selector and default remain valid. New explicitly named/versioned
local profile2 APIs select the larger finite budgets; the existing wire format
is unchanged. No old version1 object acquires new semantics by recompilation.

One immutable medium, one exact driver/FS generation pair and one absolute
whole-file deadline bind STAT, data, EOF, ELF preparation and publication.
No implicit retry, counter reset, service recreation or renewed deadline inside
capture. Namespace queries keep their ordinary1000ms RPC bound; a distinct
wide observation records the original120000ms capture end before STAT starts.
The caller cannot convert an old observation into a new successful capture.

## Fixed capacities and recovery

Input524288 bytes, private fixed workspace (file bytes,512-byte frame,266336-byte
prepared record). At most2050 FS requests: one STAT,2048 data reads of256 and
one EOF. The same generation also enforces its total2050 limit. Existing used
clients need sufficient remaining capacity before reading anything.

Block profile2 permits4096 total reads,120000ms absolute generation lifetime.
First read waits at least100ms since initialization, later reads at least50ms
since previous completion. Sleep blocks; no quota retry. Kernel64 PIO calls per
100ms,16 words per transfer, CPU32/1000ms, ATA200ms and individual IPC1000ms
remain unchanged. Quota/backend failures fail closed even before profile limits.

FS profile2 uses exactly16 cache sectors with bounded FIFO replacement, bound
to the same immutable medium/owner and erased on poison/fence/reinitialization.
No returned bytes from an unsuccessful replacement. Metadata traversal bounds
remain those of existing parsers; arbitrary files need not succeed if they
exhaust a declared budget. Generated FAT and EXT2 layouts exercise real chains,
direct/indirect data and sector/cache crossings, not a fake byte backend alone.

Normal shell dispatch, exact generation identity, attenuated child import,
terminal handoff/wait/reclaim and service fencing/reap/recreate all remain real.
Creation8/1000ms and restart2/10000ms unchanged. No implicit device rights or
counter reset. Owner loss and failed cleanup take existing fail-closed paths.

## Qualification

Regression first: actual C O0/O2 block/FS/media/capture/ELF behavior, boundaries
1536/1537, cross-cache, full524288, oversize, insufficient requests, stale/reused
observation, malformed/short/extra EOF, bad ELF, deadline and clock regression,
all unchanged-output and scrub paths. Old host tests cover legacy behavior.
Both Make/Windows selectors and conventional shell command resolution tested.

One new common image and at most one legacy ShellSession regression image.
Twelve new-profile guests: five media,8GiB reference, full input-cap boundary,
driver crash, FS crash, FS hang, malformed reply and application crash/recovery.
Each<=300s including<=3s cleanup. Full old eighteen-case ShellSession regression
each<=45s. Aggregate4410s, runtime gate4800s, first failure stops. No unchanged
retry. Full raw actual CPU/PIO/IPC/ELF/task/frame/terminal/reap evidence required,
including independent byte reconstruction and mutation tests of the oracle.
Private diagnostic sequence ceilings may be enlarged only under the new
selector (fixed262144 records each), same finite ring sizes and every original
record/cleanup predicate; no authority effect. Observer output<=256MiB/guest.

Immutable generated data media only, existing read-only base/disposable COW
discipline and zero allocated overlay data after success/failure. No boot-media
rebuild in this package: the separate new kernel is directly booted for runtime
qualification. AZ BIOS proof stays bound to its original accepted image and is
not relabeled as proof of this new image.

Queue freezes nine gates and scope. Before execution, freeze all source/tool/
command/input hashes and complete finite reservation. Each gate executes once
and stops on first failure. Independent raw review, direct diff/ABI/cleanup
review, all gates and clean local commit precede acceptance/queue advancement.
Keep all failed attempts; subsequent evidence-directed windows must be frozen
separately under standing authority. No partial host pass is runtime acceptance.
