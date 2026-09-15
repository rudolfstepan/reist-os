# Native periodic CPU admission — R8.3ap

## 15 September: historical regression scope admission

Renewed user continuation after the explicit one-file question admits
test/test_x86_64_pool_pio.py. Resume the retained unqualified source on11032d65,
1537 inputs/58 evidence and521 protected artifacts. Its historical AO test
must use the already frozen candidate/source snapshots, not today's first
queue package or producer. Preserve all predicates and mutations; no change
to the historical verifier, reference pins, CPU/IRQ limits or24 AP gates.
No AP qualification, new kernel build or guest has run. The existing actual
run-v5 expected-red remains evidence, not permission to rerun it. All three
candidate/42-guest840s bounds remain unspent and unchanged. This adds one test
file to the same transaction, not another package or a gate waiver.

Frozen after accepted `30b8046e`, 15 September 2026, under the continuous
interactive native-completion directive. One visible-worktree transaction;
no agent, push, device, media write or host-policy change. This closes CPU
admission/accounting/retirement together, not the ordinary shell or OS release.

## Inventory and compatibility

The existing32-byte generation budget counts total scheduled PIT samples.
Sleep, yield, IPC and WAIT do not renew it. That is correct for the existing
finite bootstrap profiles, but cannot admit a healthy long-running service.
Keep `reist_x64_budget_apply`, all old selectors, run-v1..4, CREATE-v1..5,
syscall132, reason/status receipts and every old lifetime limit unchanged.
Do not fix this by silently raising32, clearing on waits or restarting users.

Add explicit device-free NativeServiceCPU / X86_64_NATIVE_SERVICE_CPU=1 on
the accepted eight-owner TaskPool/Wide/Runtime/Heap/IPC profile. Reject PIO,
block, filesystem, file-launch and unrelated fault selectors before outputs.
The complete process resource/restart/IRQ limits remain: eight slots, two
roots, eight CREATE attempts per root, one wait node, unchanged memory limits,
Sleep1..100ms, WAIT1..1000ms, tick<2^60 and existing IRQ/TSC lease. No quota
renewal API, implicit device right, scheduling guarantee or service restart.

The reference is the quota/period model in the official
[Linux CPU bandwidth contract](https://www.kernel.org/doc/html/v6.11/admin-guide/cgroup-v2.html#cpu-interface-files),
plus SysV AMD64 and the existing REIST monotonic-millisecond ABI. This is NOT
cgroup/POSIX compatibility or measured CPU microseconds: REIST counts actual
100Hz scheduled IRQ samples. The explicit deviation is fail-closed retirement
on the last permitted sample, not throttling. No credit accumulation, burst,
wall-clock reset or unlimited-quota spelling. Units and version name differ.

## Explicit authority and fixed layouts

Private run-v5 is336 bytes: the unchanged v4 header/eight32-byte task entries
followed by eight u64 period_ticks fields. Initial roots request100 ticks;
unstarted dynamic entries have zero. Runtime child entries are zero (legacy
lifetime) or100 (explicit periodic admission). Version/count/size/backing and
every reserved field are validated together; old descriptors never imply this
authority. The standard legacy bootstrap probes still use four active slots.

Public CREATE-v6 is80 bytes: unchanged CREATE-v4/v5 first64 bytes plus u64
cpu_period_ms and reserved. Operation is CREATE only, period exactly1000ms,
reserved zero, cpu_samples1..32, RNPGv2 image, full attenuated syscall profile
and startup-v1. Copy/admit the full extent before allocation/publication.
Only a periodic root can delegate this profile; period must match and the
child sample limit must not exceed its parent's admitted limit. Numeric
handles and a version field alone confer no authority. Existing CREATE-v1..5
remain lifetime accounting even inside the new profile. WAIT/CANCEL remain v1.

Reuse each existing32-byte budget for generation, limit, lifetime used and
last charged tick. Add a separate fixed32-byte per-slot window record:
period_ticks, immutable bind origin, last charged window index, window used.
Both records are private kernel metadata; the legacy path requires an empty
window record. Bind only all-zero records at a valid current monotonic tick.
Windows are half-open [origin+n*100, origin+(n+1)*100). Charge at most once per
strictly advancing actual scheduled IRQ tick. Compute its window directly,
without walking skipped periods. Reset only window used on that time-derived
transition; lifetime used never decreases. No syscall/wakeup action resets
either record. An exhausted generation cannot acquire a fresh window.

Validate generation, all counters, origin, current clock, window arithmetic
and requested operation before writes. No wrap or partial change on rejection.
The32nd sample in a32-sample window returns the existing CPU-fault outcome256;
normal task faults/cancel/owner loss use the existing revoke/fence/reap chain.
Clear both records only at generation retirement. Stale or corrupt metadata
must not resume; unknown kernel ownership enters the existing bounded fatal
path without speculative cleanup. Final zero/free proof includes both arrays,
the appended run fields, full profiles, IPC, heap, FP and imported image state.

## Cohesive implementation and proof

Include the new pure accounting implementation only in the explicit profile;
keep the original budget core's default code bytes unchanged. Cover the actual
production core, run admission, syscall snapshot/attenuation, publication,
rollback and retirement at O0/O2, including NDEBUG-safe checks. Initial red
must exercise the actual missing run-v5 admission before implementation.
Negatives cover every layout/version/range/authority field; skipped and exact
window boundaries, 2^32 crossing, 2^60 horizon, overflow, backward/duplicate
ticks, stale generations, corruption, last-sample exhaustion and no reset on
yield/sleep/IPC/WAIT. SDK layout and dispatch tests include old and new ABIs.

Reuse the eight-task Ring3 fixture/observer's full isolation and cleanup
checks. Add only explicit service-profile behavior: healthy generations must
consume at least40 actual scheduled samples across multiple windows, while
their window limit is never reached. Preserve finite fixture deadlines.
Include real periodic CPU exhaustion, legacy lifetime exhaustion across
windows, UD2, cancellation, owner loss, full pool/retained receipt/replacement,
OOM at first/middle/last acquisition and independent peer progress. Test
eight concurrent tasks, all six imported owners and two complete runs.
No synthetic tick/charge success, runtime budget write or altered receipt.

One immutable native image serves twelve lifecycle guests: the original ten
pool cases (4/8GiB normal, UD2, periodic CPU spin, CANCEL, owner loss, retained
receipt, OOM first/middle/last), then legacy lifetime exhaustion and periodic
window-crossing/idle-resume. Two fatal guests corrupt one last-slot window
counter and one last-slot generation binding after real publication; observe
fatal halt with no later resume or ownership cleanup. All normal guests retain
full binary snapshots and independent same-stop equivalence. Fixture mode
writes remain four validated Ring3 words/guest; OOM uses only the existing
three-register allocator-return adapter. Fatal writes are separately bounded
to the exact documented metadata word, original bytes retained.

## Frozen gates and bounds

The queue freezes all commands before implementation. Run independent host
groups in parallel where safe, never timed guests concurrently. Each group
runs once on one unchanged candidate; first failure stops later groups.
At most three changed candidates total, after at most two evidence-directed
in-scope corrections. No identical retry or altered oracle after a failure.
Host groups<=300s, builds/default/review<=180s, lifecycle outer<=600s,
fatal outer<=120s; each guest20s including cleanup, lifecycle240s/fatal40s,
at most42 guests/840s across all three candidates. No milestone/full suite.

Build each required profile once per candidate: default TaskPool, PoolPIO,
FileLaunch and the new service profile. The three legacy proofs cover the
changed shared ABI/scheduler at both capacities and the device boundary;
do not rebuild a profile per fault case. Source/tool/profile/command/artifact-
bound unchanged builds may be reused explicitly, never inferred from a PASS
name. All legacy linked images/PRGs/catalogs and non-path object bytes remain
identical to accepted AN/AO/AM outputs. The already qualified bounded DWARF4
single generated include-directory normalization may be used only for these
three exact new manifest-bound reference directories; no general debug strip,
source-line/address/opcode exception or reference-pin update.

Preserve all prior accepted and failed evidence, including the unexplained
AO8GiB CPU32 failure and AM timeout. Stop on unrelated changes, a required file
outside allowed_files, default binary drift, missing input, another authority
domain or exhausted correction budget. Only every gate PASS and direct ABI,
scope, cleanup and documentation review permit done/local commit. Afterwards
continue from a clean worktree; R3.6b remains deferred. Periodic sample
accounting alone is not long-lived device/FS service acceptance, certification,
ordinary native shell, desktop/browser, SMP or a finished64-bit OS.
