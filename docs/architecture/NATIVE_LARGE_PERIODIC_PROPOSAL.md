# Periodic CPU accounting for the actual large native desktop

## Concrete missing mechanism and approval boundary

Inventoried24.09 on accepted0c820375 while implementing approved CB desktop
services. CC's display-info query passed all five gates and both resolutions.
The actual41-source desktop plus display/service SDK now links with no reachable
undefined symbols:952552 allocated section bytes,5.116s build. Its final load
layout/startup/event loop and complete guest behavior are not yet accepted.
Candidate evidence: build/codex-agent/native-vmware-desktop/services-link03.

The remaining startup incompatibility is explicit in
userspace/sdk/include/reist/x86_64/task.h and arch/x86_64/proc/task_family.inc:

| Existing operation | Image | CPU accounting |
| --- | --- | --- |
| CREATE-v6,80 bytes | RNPGv2,64 image pages |1..32 samples per1000ms, attenuated from a periodic parent |
| CREATE-v7,64 bytes | RNPGv3,256 image pages |1..32 samples for the whole child lifetime |

The actual desktop exceeds the v6 image extent. Sending its RNPGv3 record to
v6 is invalid; v7 does not provide persistent service execution. Repeatedly
recreating a desktop to replenish its lifetime budget is not an acceptable
substitute for the admitted periodic service mechanism.

NATIVE_LARGE_IMAGE_CONTRACT.md explicitly preserves lifetime-only v7 and says
that package does not add periodic large imports. The approved
NATIVE_LARGE_EXECUTABLE_PROPOSAL.md explicitly excludes a periodic CPU increase.
Approval of desktop file/application services required keeping kernel limits.
Therefore do not infer authorization to turn the large-image lifetime budget
into a recurring budget from that service approval. AGENTS.md's standing
completion directive excludes new authority grants and unresolved safety
decisions. This is an actual resource boundary, not an attempt-counter handoff.

## Requested bounded extension

Append a separately selected CREATE-v8 with the existing80-byte v6 transport
layout, full profile-v1 and startup-v1, but requiring an RNPGv3 prepared image.
Enable it only with an explicit NativeLargePeriodic selector and the existing
large-image and periodic-service mechanisms. Disabled behavior remains exact.

The supervisor may import a large graphical service with1..32 CPU samples per
1000ms, never more than its own admitted immutable periodic budget. A lifetime
parent, period other than1000ms, oversized budget, flags/reserved data, stale
generation, malformed startup/profile or wrong image version fails before any
published task, frame ownership or attempt charge. CREATE-v6 and v7 semantics
remain unchanged. No in-place renewal, budget reset or new privileged caller.

Keep1MiB ELF input/image,256 image slots, guarded32KiB stack, current heap,
eight task slots, capability/endpoint pools, per-operation deadlines, fixed
restart budgets and exact generation-scoped fencing/reaping. No display-copy
quota increase, new devices, writable files, DMA/network or unrelated process
authority. Samples are existing scheduler accounting units, not a claim of
milliseconds of measured execution time or real-time certification.

## Qualification before use

After explicit approval, freeze one kernel prerequisite transaction. Exercise
the actual request admission, complete80-byte pointer preflight/copy, parent
attenuation, v3 import selection, staging cleanup and periodic plan publication.
Host tests cover enabled/disabled profiles, v6/v7 coexistence, every malformed
field, nonperiodic/under-budget parents, stale identities and unchanged rejected
state. Bind and carry forward unchanged loader/frame rollback evidence.

Fresh guests must execute a large child using addresses above0x440000 across
multiple periods, consume more than32 samples in total while staying within
each period, and independently prove same-window exhaustion, cancel/fence/reap,
fresh-generation recreation, an independent peer and partial-construction
rollback. Replay complete raw memory/PTE/CPU/frame/owner evidence; no success-
marker-only acceptance. Freeze exact finite reservations and gates before code.

Then restore CB and complete its original eight-case desktop acceptance and
VMware visual/performance proof. This proposal is not completed native64.

## Preserved CB candidate

Nine attributed source/test files remain visible in the worktree and are also
byte-verified in services-before-periodic01/files.zip under
build/codex-agent/native-vmware-desktop. manifest.json records every file hash.
Hosts01..11 spent:10/11 pass broker/client/platform O0/O2, including actual
existing VFS clients,1792-byte prefetch, bulk short reads/CRC, path reads,
immutable request deadlines, denied writes/foreign identities and child control.
Builds01..03 spent:01 exposed missing memcpy linkage;02/03 link the existing
ISO C byte implementation and resolve all SDK imports. No CB media, guest or
final gate has run. Preserve all failures and counters; no implementation commit
or runtime acceptance until the full frozen package gates pass.

Approval status: user renewed "mach weiter" immediately after the concrete
approval question for this proposal0b05b708. Approves this bounded extension
only; the independent display-throughput increase remains unapproved.
