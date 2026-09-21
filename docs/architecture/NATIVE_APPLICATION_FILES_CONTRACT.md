# Native application read-only objects v1 — R8.3bc

## Accepted package evidence — 21 September 2026

Candidate08 passes all nine frozen gates and the complete16-case matrix,
including independent raw replay and scope review. Seal:
`build/codex-agent/r83bc-application-files/candidate08/acceptance-seal.json`,
SHA256 `db3764b54b75fb2204f13fa3c26360a4e6dc47d3c97aae720614acdf7ae7c24b`.
Image SHA256 `f0fe88bc7711257d4af9eec28d73890ffd24b2157a3af9d1d9afb53db84e2730`.
All80 replies are received at23 CPU ticks, with CPU32 and the original1000ms
bound unchanged. Both final transport orderings are qualified; broker work
stops at80, and queued request81 is revoked without processing or response.
Fifteen fresh cases and one exact corrected capture cover all five layouts,
8GiB, repeated starts, authority, app/owner/service failures and recovery.
Cumulative34 physical guests2753.232284900034s, two kernel images and two
separate test-client builds; no historical failure removed or relabelled.
This closes application objects and normal cat/ls, not signed CLI publication,
desktop, network or hardware acceptance. CLI-first delivery follows the clean
local package commit. The dated windows below remain the audit history.

## Authorized IPC correction window — 21 September 2026

The user's renewed `ja mach weiter` approves the preceding explicit request
to extend this active package into the native IPC core path and its regressions.
The originally Ring3-only implementation scope below is amended only for
`arch/x86_64/ipc/native_ipc.c`, `test/test_x86_64_ipc_cost.py` and
`test/x86_64_ipc_cost_host.c`. No ABI, quota, deadline, scheduler, shared IPC
primitive, integrity algorithm or application authority changes are permitted.

Inventory identifies a redundant publication: `pump(false)` marks a pending
request changed before `transfer`, even when the actual shared IPC primitive
returns EAGAIN without writing the message. Each unchanged bulk waiter then
republishes 35 protected chunks. Both receive implementations write output only
after finding a deliverable message; send takes const input. EINTEGRITY remains
fatal before publication. Remove only EAGAIN's changed bit, retaining all entry
verification, retries, terminal-result publication and deadline handling.

First reserve one host-only red/green regression window: each command <=600s,
at most one expected-red cost test, one corrected cost test and the existing
native, bulk, completion and handoff host suites once each. Exercise four/eight
task slots, v1/v2 empty receive and full send retries, unchanged request bytes,
full verification counts, semantic equivalence, and existing corruption/repair
tests. No image build or guest in this first window. Freeze any later runtime
window before execution. A changed kernel requires new runtime evidence; the
15 old passes cannot qualify the new image. Retain the 18 physical guests,
1588.3585832000244s, one kernel build, two test-client builds and all six stops.
CPU32, the original 1000ms deadline and 80 actual responses remain mandatory.

Host-window result: expected-red fails with five redundant v1 publications;
the corrected four-slot O0 semantic/corruption comparison passes. The extended
eight-slot run stops because the historical7f452faf reference has hardcoded
four-slot arrays, not because of a candidate fault. Preserve `ipc-core-red.log`
and `ipc-core-green.log`. Reference-fixture correction only: retain the original
four-slot reference, use the exact pre-change2e05a01d adapter for eight slots.
Reserve one corrected cost-suite run and the four not-yet-run host suites,
each <=600s, still zero image builds/guests and first unexpected failure stop.

The corrected host window passes: cost O0/O2 x four/eight slots38.939s,
native9.299s, bulk2.685s, completion1.868s, handoff1.762s. Freeze candidate07
with one new common kernel image, no new test-client build, the same nine gates
and16 entirely new guests. Only execution order changes: request-budget first,
then the original15 others. Each <=300s with3s cleanup, fresh aggregate4800s,
runtime gate5400s. Reuse the exact candidate06 external test client to isolate
the kernel delta; no payload/quota/oracle changes. Dependency gate also verifies
the five completed IPC host suites against their frozen sources/tools/logs.
Historical18guests1588.3585832000244s/one kernel/two test builds remain counted;
maximum cumulative34guests6388.3585832000244s/two kernels/two test builds.
No old runtime result qualifies the changed kernel. Stop first failed gate.

Before any candidate07 freeze was written or gate/build/guest began, the main
agent stopped the serial archive inventory after approximately four minutes.
The archive contains31655 files/1113949846 bytes; hashing every old failed raw
capture between fresh guests would duplicate unrelated archive work. No
evidence was removed. Correct the host verifier only: bounded eight-worker
file hashing (not agents); complete old archive hash comparison at freeze and
final review, with original stop/freeze/build receipts, actual external test
client and IPC host evidence bound at every gate. All current sources/tools
and new image/raw proofs retain their existing checks. Same candidate07
reservation, zero additional build/guest, no gate attempt/retry yet.

## Candidate08: distinguish IPC enqueue from broker acceptance

Candidate07 gates1..5 pass; one new image and80.74180430005072s guest.
The unchanged client actually receives all80 canonical responses within the
original1000ms and uses23 CPU ticks. Its81st STAT enters the transport queue
before root revocation; the broker never receives or answers it. Root closes
request, child explicitly exits1, root closes reply, then cancels/reaps and
completes the ordinary recovery commands and second run. The oracle assumed
IPC_SEND must return-9 after revocation; it omitted the valid pre-revocation
enqueue ordering. Keep candidate07 failed and its stop
`bc602b09cd7e58a66eba4e637e03040fea2caf1bac7f3172230aaf9d404584fa`.
Spent19 physical guests1669.1003875000752s/two kernel images/two test clients.

Proof-only correction: preserve the existing rejected-send ordering and add
the exact queued-but-unconsumed ordering with80 actual child receives,
80 broker receives/replies, canonical81st STAT after reply80, no81st broker
operation/reply, successful close of both channels and explicit error exit.
The unchanged IPC-delivery and full cleanup oracle must prove queue removal;
transport enqueue success is never file-operation success. Mutation tests
reject extra broker receive/reply, missing close, reordered send, wrong
sequence, missing actual response and successful child exit. No runtime/source
image/client/observer/CPU/deadline changes. One expected-red targeted test,
then same nine gates once. Fully source/tool/all-raw-bound replay of candidate07
is required before reusing its one complete capture;15 new guests at most,
300s each incl3s cleanup,4500s fresh, same4800s matrix/5400s gate and first
failure stop. Zero new builds. Original failed receipts remain immutable.

## Authority and cohesive transaction

Frozen after clean409c5d0e / accepted BB813606cf. The user's renewed
`ja mach weiter` on20 September2026 grants the immediately proposed separate
application read-only object authority. It does not broaden legacy profiles.
Implement normal cat/ls, SDK, explicit object delegation, both build/layout
paths and complete containment/recovery together, not as syscall micro-packets.

Inventory: AY forbids app FS endpoints; root owns native STAT5/READ6/READDIR7
RPC and the immutable media generation. Existing cat/ls use the legacy
STORAGE_SUBMIT client ABI, which native task profiles exclude. Existing IPC
already provides single-peer directional delegation and generation retirement;
task import, terminal transfer and bounded wait/cancel are accepted. Reuse
these mechanisms. No new kernel code or syscall, shared raw FS endpoint, device
right, writable medium or global path namespace for applications.

## Standard-first semantics and deliberate adapter limits

Keep System V AMD64 ELF64, existing x86os SDK names, byte offsets and negative
errno values. Reuse actual unmodified userspace/programs/cat.c and ls.c. Their
native adapter operates only on one explicitly selected immutable object,
not a claim of general POSIX open/exec or whole SDK compatibility. The REIST
application-object protocol is fixed-size version1 over existing IPC-v2.
It is distinct from legacy storage and native FS RPC, not a format alias.

NativeAppFiles explicitly implies WideFile. The shell chooses the requested
object from the recognized ordinary tool invocation; the command line does
not let an arbitrary file mint rights. Exactly the selected canonical path is
admitted; aliases/cwd are resolved before grant and sent as explicit startup
context. Child-provided paths cannot navigate the parent namespace. A directory
grant exposes only its captured entries, not recursive read/open authority.
File capture is <=16384 bytes; directory capture <=32 entries plus actual EOF.
An over-capacity or failed capture publishes nothing; no truncated success.

Capture the immutable snapshot in the root's bounded Ring3 storage, using the
existing driver/FS processes. Original STAT-to-SPAWN end <=120000ms bounds
code plus object capture; no renewed command clock. Copying data to a child
cannot later erase its knowledge: revocation forbids future broker operations,
not access to already delivered private bytes. No persistent object format.

## Identity, publication and lifetime

One live grant, nonreused epoch and exact root/foreground generations. Two
private IPC endpoints give the child request-send and reply-receive only.
No FS endpoint or delegate/close ownership is passed. New tool profiles also
exclude IPC_CREATE, IPC_CLOSE and IPC_DELEGATE syscalls; the broker owns cleanup.
The existing kernel's single-peer admission prevents onward peer delegation.
Authenticate endpoint
authority plus bound generation/object/epoch/sequence, validate all fields,
sizes, zero reserves, operations and ranges before effect or reply publication.
All replies use a canonical fixed512-byte frame; raw payload bytes are data.
STAT, READ, READDIR and CLOSE are the only object operations, plus initial
binding/self-test. Legacy SDK wrappers adapt explicit handles without
fabricating storage success. Unknown, foreign, stale, closed, exhausted or
expired grants fail closed. Same object cannot rebind/reset its budget.

At most80 requests and one absolute1000ms application/broker lifetime, never
renewed by RPC success; per-call IPC<=1000ms and cleanup wait<=1000ms. No
userspace spin: bounded IPC waits or blocking sleep; task wait/cancel at the
original finite end. CPU32/1000ms, ATA200ms, construction8/1000ms and recovery
2/10000ms remain unchanged. Old profile wait and default imports unchanged.
Broker close/revoke precedes reuse/next foreground. Child exit/crash/hang/quota
must not kill root or peer; uncertain cleanup stops root for kernel fencing.
Root loss revokes its endpoints and descendants through existing lifecycle.
Service/capture error follows existing isolate/fence/reap/recreate/self-test;
never preserve a grant across a failed source generation. No automatic retry
of a partially granted request, reset of exhausted budgets or read rights from
merely finding an executable. Old AY/BA/BB evidence remains separate.

## Frozen verification

Queue lists exact allowed files and nine ordered gates. Host regressions first:
actual C broker/client/root adapter O0/O2, real tool main functions, malformed
and stale requests, overflow, no publication on failure, budgets, cleanup and
old disabled code equality. Actual generated FAT12/FAT32/EXT2-1k/2k/4k media
through existing filesystem parsers, tool lookup and both Windows/Make layouts.
One common new image only after hosts/dependencies pass; no per-case build.

Sixteen complete guests on that image: five compatible layouts,8GiB, repeated
cat/ls and object/stale/foreign/unsupported/write-denial checks; child crash,
hang, quota, root loss, driver crash/hang and malformed FS reply/recovery.
Freeze exact case mapping and input plans in the runtime test before execution.
Each guest300s including cleanup3s, aggregate4800s, matrix gate5400s. Full raw
IPC/CPU/lifecycle/terminal/PIO/snapshot assertions and independent replay;
serial markers alone never qualify. Validate actual file bytes/entries and
foreground task origins, isolation, fence/reap and immutable base/COW state.

The sixteen cases are FAT12, FAT32, EXT2-1k/2k/4k, EXT2-1k at8GiB,
repeated cat/ls, one combined authority case, application crash/hang/CPU quota,
root loss, ATA-driver crash/hang, malformed FS reply/recovery and broker request
exhaustion. Each has two complete kernel process runs; the second runs ordinary
cat, ls and probe again. The authority case runs four separate probe generations:
directional and CREATE/CLOSE/DELEGATE/PIO denial, unsupported operation5,
stale epoch, foreign child generation. All use the same immutable data/tool
images. Private probe selection is written once before its first instruction,
only after complete original page/ELF verification; before/after bytes and the
selected mode must be independently replayed. No kernel state or clock mutation.
Observer IPC delivery, CPU accounting, image, identity, terminal, PIO and probe
step predicates remain unchanged from BA. New independent object/FS byte oracles
verify all replies and the complete root capture including actual EOF before
the child constructor; successful console output is not that proof.

No signed BIOS publication in this application-authority package: BB's signed
pair is independently pinned. New generated data/tool layouts accompany the
explicit Windows/Make native profile; signing the resulting new image is a
separate trust/publication transaction after acceptance. Preserve existing
reference artifacts. Stop first failed gate; freeze evidence-directed finite
corrections without routine approval, preserve all failed work and costs.
Acceptance requires all gates, direct diff/scope review, done transition, clean
local commit and bound final receipt. No push, nested agents, user disks or
full64-bit OS/desktop/hardware/production-trust claim. R3.6b remains deferred.

## Candidate02: relative-clock proof correction, no new image

Candidate01 passes gates1..5; its first complete FAT12 two-root qualification
takes60.63747690001037s. Both roots run the actual cat/ls/probe, full prior raw
predicates pass, but the new object validator incorrectly requires the relative
timeout to be computed at the later kernel-entry timestamp. Actual syscall ABI
takes a relative timeout: a timer interrupt can separate userspace clock sampling
from entry. Example end3570, timeout960, previous return2610, entry/completion2620.
The exact sample is2610, not2620. No tolerance/slack or deadline extension is
introduced: require previous completion <= end-timeout <= entry <= completion
< unchanged end, and0<timeout<=1000, for every successful broker operation.
Retain all canonical binding/sequence/reply/CPU/IPC/fence/cleanup predicates.
Host red/green cases reject a stale/renewed sample, oversized wait and late reply.

Only runtime proof, host regression, verifier and queue/docs change. Source/tool/
all-raw binding permits full replay of this complete qualification capture, not
a diagnostic-to-acceptance promotion. Original failed row/logs are immutable.
New finite window: nine original gates once, zero new builds, fifteen new guests
<=300s each/4500s plus the retained60.63747690001037s. Full sixteen-case matrix
and direct review still required. Same kernel, image, ABI, clocks and quotas.

## Candidate03: prove revocation followed by error exit

Candidate02 passes seven cases; the complete authority case then exposes a
second overly narrow outcome predicate. All three invalid requests are rejected:
root closes the directed endpoints, blocked client RECEIVE returns-32, the
SDK's subsequent canonical CLOSE SEND returns-9, and the SDK issues EXIT1 before
root CANCEL0 and WAIT1. Requiring forced cancellation after a process has already
exited would reject this fail-closed ordering. Accept it only with that complete
raw chain, exact directed handles, original child/root generations, error exit
and unchanged fence/reap; never accept a successful invalid request or arbitrary
nonzero exit. Host mutations remove each required event/change the result and
must fail. All ordinary success, crash/quota/hang and cleanup requirements remain.

One image/eight physical guests662.6280681999633s spent. Retain both stops and
original failed rows. Candidate03 changes only outcome proof/tests/verifier and
queue/docs; observer, inputs and all production bytes stay exact. Full replay of
the eight complete prior cases, then eight fresh300s guests/2400s maximum; same
nine gates and full16-case acceptance, first-failure stop, no new build.

The user separately approved delivering a limited bootable QEMU CLI research
version first; desktop/browser/network/remaining platform acceptance follow.
That publication transaction begins only after this package is accepted cleanly.

## Candidate04: expired hang and SDK error exit

Candidate03 crash passes92.37514919997193s. Complete hang92.54534280003281s
proves root RECEIVE timeout exactly at HELLO end4650, both endpoint closes at
4650, blocked child RECEIVE3700..4650 returns-32, then SDK EXIT1 at4660 before
CANCEL0/WAIT1. No successful work after expiry; the SDK rejects CLOSE locally.
The outcome oracle now requires this complete timed chain for mode6 self-exit,
not an arbitrary error exit. Mutation hosts reject missing/changed events,
early timeout, nonblocking receive and premature exit. All existing raw
CPU/identity/IPC/PIO/fence/reap and next-command recovery predicates remain.
Ten physical guests847.548560199968s/one image total retained. Freeze the same
nine gates; ten exact full replays, at most six new300s guests/1800s, no build.
First failure stops; full16-case acceptance required before CLI publication.

## Candidate05: a separate budget-exhaustion test client

Candidate04 passes fifteen cases. Its final client consumes CPU32 and exits
with quota status256 after70 replies, before the required80. This is a valid
CPU fence, NOT a request-budget proof. Preserve the failed119.33345410000766s
capture; total16 physical guests1396.892000199994s/one kernel image.

Only the final fault fixture gains a separately built external probe selected
with REIST_APP_BUDGET_CLIENT. Default source projects exactly to the original;
all normal delivered tools, embedded programs and kernel bytes stay unchanged.
Compile one probe object/link against the original startup/broker object, no
kernel build. Cache the canonical request buffer and increment only genuinely
earned sequences; retain original end and bounded IPC. The independent observer
still checks every full512-byte reply, exact80 successful broker operations,
CPU32, fence/reap and next-command recovery. Error self-exit additionally needs
80 actual received replies and a canonical81st STAT rejected on the revoked
request endpoint, then EXIT1/CANCEL0/WAIT1. Host C runs the actual broker;
mutation tests forbid accepting70 replies, quota termination or missing events.

Fifteen exact existing captures are replayed, the failed one never accepted.
Freeze nine unchanged gates, one test-client build, zero kernel builds and one
new300s guest including3s cleanup. Count the failed guest in cumulative elapsed
time and physical count17. Full16 unique cases and all gates remain required.

## Candidate06: reuse bounded test receive buffers

Candidate05 reaches only54 replies before CPU32; its performance hypothesis
failed. Preserve95.39384710002923s and the distinct failed test ELF, stop
ab529177d7e969b5b7c1e74733249fbb3f2b7cfd6a35e2daea3bde218a1e71c3.
Actual kernel/ipc/ipc.c bulk_message_valid admits existing output payload;
only version, size and capacity are input requirements. Within the test-only
branch, place TX/RX in separate aligned fixed pages and initialize RX once,
resetting only its capacity between receives. No protocol, clock, deadline,
sequence or observer change; every full reply remains independently validated.
Host regression requires the preceding reply to survive until the next RECEIVE.
This reduces known redundant work, but runtime improvement is not assumed.
Freeze the same nine gates, one distinct test-ELF build and one300s guest,
15 exact complete replays. No kernel/normal-tool build. Retain17 physical
guests1492.2858473000233s/one kernel image/one test ELF already spent, including
both failed quota cases214.7273012000369s; physical count18 after the new guest.

Candidate06 outcome: only52 replies before CPU32/status256/state3. The receive-
buffer hypothesis did not close the required80-response proof. Gates1..5 pass;
gate6 stops, gates7..9 never execute. Preserve its96.07273590000113s capture and
stop05383adc4a8735d622bc545f120280c2fa7ed70ce9b4c3b614b5870cf5e49183.
Total18 physical guests1588.3585832000244s, one kernel image/two test clients.
No acceptance/implementation commit/publication or new execution reservation.
The next kernel IPC/CPU-path implementation lies outside allowed_files and
requires explicit scope expansion with unchanged safety obligations. This is
not evidence of a kernel defect, nor proof that80 is fundamentally unreachable;
do not weaken the frozen criterion or treat earlier quota termination as it.
