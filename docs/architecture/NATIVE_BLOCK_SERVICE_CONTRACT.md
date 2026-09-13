# Native read-only block service boundary

R8.3ai, frozen on accepted7f452faf, 13 September2026. Queue gates are the
acceptance authority; this document is not a full OS or runtime success claim.

Current scoped runtime evidence on contract873d82fa: all ten block cases
pass145.662s (160 task lifetimes), all ten old PIO cases pass141.818s, eight
old plus one completion-corruption fatal case pass9.658s. Regular roots use
17..28 of the unchanged32 samples. Normal bootstrap and original i386 pins
pass. Actual O0/O2 completion/adapter, IPC semantic/corruption/cost and block
protocol hosts supplement the guests;21 frozen groups govern package acceptance.
The historical candidate failures and later explicit amendments below remain
evidence, not current stop claims or permission to change more mechanisms.

## Inventory and scope

R8.3ah provides full192-bit profiles, read-only generation-owned PIO, reusable
Ring3 ATA IDENTIFY/READ SECTORS, family retirement and common fatal fencing.
Native IPC already supports explicitly delegated rights and fixed140-byte v1
or2060-byte v2 envelopes. Existing storage_service.c depends on i386 request
pools/VFS and includes writable maintenance; do not move those into Ring0 or
pretend that compiling its header ports that service.

Bundle the reusable client, request/reply admission, bounded service dispatch,
actual Ring3 ATA service adapter and IPC/fault/restart proof. This is one block
service failure boundary, a prerequisite of later Ring3 filesystem consumers.
No new shell command, filesystem parser, kernel syscall or disk-write authority.

## Standards and versioned transport

Preserve the existing STORAGE_BLOCK_READ operation1,512-byte block size, sector
offset/LBA units and negative errno categories from the storage SDK. ATA data-in
follows the established references in ATA_PIO_TRANSFER_CONTRACT.md; only the
already admitted primary-master LBA28/READ SECTORS/IDENTIFY profile is used.
The kernel request-pool API is NOT aliased onto this different transport.

Name it REIST native block RPC v1. A fixed64-byte header has four u32 fields
(version1,size64,operation1,flags), four u64 fields (service owner handle,
nonzero sequence,LBA,absolute monotonic deadline_ms), u32 length, i32 status
and one reserved-zero u64. Requests use flags0,length512,status0. Replies use
flags1 and echo exact generation,sequence,LBA,deadline. Success has length512,
status0 plus exactly512 data bytes; error has length0, negative allowed errno
and no data. Reserved and unused transport bytes are zero.

Requests use the existing IPC v1 envelope with length64; replies use v2 with
length64 or576. These are explicit IPC payloads, not new syscalls. A client has
one in-flight request and monotonic sequence; a service accepts exactly the next
sequence for its own generation. Replays/stale owners, invalid widths/versions,
wrong lengths, future or expired deadlines, invalid LBAs and malformed replies
fail before hardware effects or client output. No output byte changes on error.
All transport operations share a monotonic deadline at most1000ms away; no
unbounded wait, background retries or lease extension after progress.

## Service authority and lifecycle

Each generation starts with explicit request-receive/reply-send endpoint grants
and exact PIO ownership. Numeric arguments create no rights. It must perform
fresh IDENTIFY and a complete self-test sector read before readiness is accepted.
A session handles at most8 incoming requests, including malformed ones, with
fixed buffers, fixed CPU budget and bounded idle/transfer deadlines. One service
generation never inherits the preceding generation's readiness or sequence.

Pace consecutive reads with monotonic Ring3 sleep so the already accepted64
PIO operations/100ms quota is respected; do not increase it. ATA wait remains
200ms/finite polls. Four task slots, eight root creation attempts,32 CPU samples,
eight image pages and one4KiB user stack stay unchanged. An opt-in service ELF
may use a second RX page within that existing image capacity; old layouts and
the private C payload layout4 remain unchanged.

Crash during transfer, sleeping hang, CPU spin, invalid reply, owner loss and
normal exit use existing fence/revoke/reap/recreate/self-test transitions.
Client outputs remain unpublished until a complete exact reply is validated.
No replacement before old task retirement; stale endpoint grants and ownership
cannot regain authority. Automatic and explicit recovery use the same state
machine and lifetime attempt budget. Exhaustion leaves the domain fenced.
This is not a system-wide supervisor or persistent indefinitely-running daemon
claim; scalable service budgets are a later explicit lifecycle boundary.

## Frozen proof

Host O0/O2 executes actual C client/dispatcher and service adapter with bounded
transport/clock/ATA witnesses: every malformed field, stale/replayed sequence,
deadline boundary, partial/error response, quota and untouched output. Negative
oracles reject missing, duplicate or reordered runtime/fence/data evidence.

Ten hidden QEMU guests: normal4/8GiB; OOM0/1/2/3/6/9; missing media; owner loss.
Normal cases include actual repeated RPC reads of distinct LBAs and their full
known512-byte payloads, invalid requests and replies, UD2, sleeping/CPU faults,
new-generation recovery, unrelated peer progress and exact frame/IPC cleanup.
Use only exclusive generated64KiB COW fixtures with a fixed per-LBA pattern,
read-only base nodes, unchanged hashes/logical data and no allocated overlay data.
All kernel mechanism objects must equal accepted PIO; no observer changes to
kernel state except explicit fixed OOM injections. Twenty seconds per guest.
Old PIO10/fatal8 and normal bootstrap plus qualified i386 pins remain gates.
All16 groups and direct review precede local commit; no agents or push.

Keep historical vector20/observer failures and R341-H1/H2 visible. R3.6b stays
deferred. No full native OS, physical hardware, DMA, writable recovery or system
timing/stability acceptance is implied by this service package.

## Candidate evidence boundary, 13 September2026

Renewed user authority permits continuous bounded measurement/kernel-cost
diagnosis and corrections. First compare the same exact image and catalog in
at most four20s diagnostic COW guests: detached, minimally connected, full
instrumentation and one targeted counter profile. Diagnostic outcomes never
replace the16 frozen gates. Add diagnose_x86_64_block_costs.py and the shared
capture module to scope,24 files. Do not change CPU/PIO/deadline limits, QEMU
clock rate, kernel state or mechanism objects. Read-only kernel path analysis
is permitted; a demonstrated necessary mechanism correction must first receive
an explicit failure-boundary contract and regression gates. Keep all historical
failures and correct only attributable causes, without routine handoffs.

Implementation is uncommitted on17954988. Actual C O0/O2 and the NativeBlock
build pass, but the first fully observed4GiB guest reaches its32-sample budget
during the second valid RPC. No new guest case is accepted. A prior detached
debugger diagnostic completed the intended service lifecycles; this is not a
substitute gate and used a different candidate than subsequent journal probes.
The candidate fixed Ring3 PIO-return journal, physical reset-OUT return probes
and generation-gated startup observer are still unaccepted instrumentation.
No kernel mechanism or frozen quota has changed. Preserve all failed evidence;
no commit/queue transition or further unchanged retry. A separately authorized
bounded measurement/kernel-cost investigation is needed to determine the next
correction without weakening assurance. CURRENT_WORK.md records exact evidence.

## Deadline co-admission amendment

Controlled same-image diagnostic controlled-9a466ef3a5b24260974cd63abaa5e8d0
confirms budget sensitivity even with minimal instrumentation. Counters reject
the earlier hypothesis that repeated publication/word probes alone explain it.
The service currently crosses the full syscall/scheduler boundary twice per
port operation: clock, then mediated I/O. The mediator already owns monotonic
time and must check its integrity. Co-admit the same absolute deadline there,
without omitting any ownership, state or quota validation.

PIO request v2 retains64 bytes and all v1 offsets. Only read8/write8/read16
operations may use v2; offset48 carries deadline_ms, offset56 remains zero.
V1 reserved bytes and BIND/FENCE stay unchanged. After authority checks and
before any quota/state/port/buffer effect, compare deadline to monotonic tick*10:
expired/equal returns-110; more than1000ms ahead returns-22. Broken clocks still
enter the unchanged fatal path. Service passes the same RPC deadline instead
of a preceding clock syscall; ATA polls and final reply checks remain bounded.
Only the scheduler object containing pio_domain.inc may differ from accepted
AH; all other standalone mechanism hashes and all original gates remain.
Add test_x86_64_pio_deadline.py actual assembly/SDK O0/O2 and expired-v2 runtime
fixture coverage:17 gates,28 files. No silent acceptance from diagnostic runs.

The ordinary reference generation issues six RPCs: the four different invalid
headers and full reads of both LBA1 and LBA127, after self-test LBA0. Later
generations repeat the reads after faults. This replaces the candidate's two
redundant extra reads of the same LBAs; it does not change the reusable eight-
request session maximum or its host quota/exhaustion proof. All ten cases,
failure modes, byte comparisons and frozen CPU limits remain required.
The four identical invalid-header probes run in the first service generation
of each root transaction, not redundantly in every replacement. Every generation
still uses a fresh owner, fresh self-test and sequence, old-owner PIO rejection,
exact reply generation/data validation, and full fencing/reaping. Fault cases
and actual expired-v2 admission remain covered in every appropriate generation.
The supervisor demonstrates full36896-byte source mutation after its first
successful CREATE. Replacements use its unchanged cached prepared template;
the kernel still copies/admit-checks the complete source at every CREATE and
every published child is compared with that exact imported record. This avoids
repeated userspace copy/mutation demonstrations, not immutable kernel admission.

## Current unaccepted candidate and stop boundary

The template cache is published only after successful ELF preparation; failure
releases its allocation and cannot seed a later CREATE. Actual helper O0/O2
tests cover allocation/preparation failure, CREATE OOM, first-source mutation,
immutable replacement imports and exhaustion. A completed reply or EPIPE may
be consumed after child retirement, but before the next PIO owner or client
fence. Bad-reply cancellation accepts only READY/IPC0, READY/IPC2 or
BLOCKED/IPC1; sleeping-fault cancellation retains its no-IPC requirement.
Host negatives retain exact generation, ordering and frame-cleanup rejection.

Seven blockhost checks, the other mechanism/ABI hosts, three builds, all ten
old PIO guests and eight fatal guests, normal bootstrap and original i386 guard
pass. None replaces the new block matrix. Latest matrix attempt
60e8de6bcc1044ccb168d32666a9d36d fails after12.941s: first4GiB case, both
roots exhaust32 CPU samples after six of eight child generations. No case
accepted. Later cache-error-path/oracle fixes do not address that cost failure;
no unchanged guest retry. Direct physical OUT and READ16 observers replace the
unaccepted journal experiment. All older attempts remain diagnostic evidence.

The four authorized controlled diagnostic guests have completed. No further
proven in-scope correction is identified. Native IPC integrity-cost changes
would affect an additional kernel failure boundary outside the28-file scope;
they require explicit scope and new regression gates before implementation.
No validation skipping, quota increase, peer repurposing, candidate commit,
queue advancement or full-OS claim. See CURRENT_WORK.md for exact gate logs.

## Authorized IPC publication-cost amendment, 13 September2026

Renewed explicit user approval resumes this attributed candidate and permits
bounded native IPC cost analysis and demonstrated optimizations. Inventory shows
check_all verifies every client/control and each active bulk tail, then seal_all
rebuilds even unchanged records after every operation. Retain check_all in full.
Measure actual native critical init/read/update calls in an O0/O2 host harness
against the accepted adapter before changing production code; counts, not noisy
host elapsed time, are the cost gate. Diagnosis is not guest acceptance.

Permit operation-scoped publication only for records touched in this serialized
IF0 transaction: BIND's client; all clients possibly affected by REQUEST/REAP;
retired generations on REAP; pending records on admission, each pump transfer
attempt/completion, TAKE and REAP. Use a local bounded four-bit pending mask, no
persistent dirty cache or trusted external hint. Mark even failed transfer
attempts, because output mutation must not be inferred from errno. Init still
seals every record; active bulk contents and controls are sealed together.
Inactive tail handling, zeroing, ABI, deadline, capability and pump order stay
unchanged. No common critical-object, common IPC pool, scheduler budget or
i386 source/format change is authorized by this amendment.

Add arch/x86_64/ipc/native_ipc.c, test/test_x86_64_ipc_cost.py and
test/x86_64_ipc_cost_host.c:31 files. Freeze the existing17 groups plus native
IPC host, bulk IPC host and new publication-cost/differential-fault host:20.
The new gate covers every slot and v1/v2 wait, completion, timeout, revoke,
rebind and idle path, unchanged snapshots, exact publication counts and raw/
redundant corruption rejection before effects. Only native_ipc.o joins the
already amended scheduler exception to AH hashes; both changed objects must
match new PIO/block variants, all other26 standalone mechanisms stay identical.
All ten block guests and old PIO10/fatal8 remain required at original limits.
Retain prior gates only when inputs are demonstrably unaffected; rerun changed
consumers after correction. Contract commit before production changes, no
candidate commit until all gates pass. All previous failure evidence remains.

Derived-link clarification before guest execution: rebuilding native_ipc moves
the validated C export reist_native_memory. physical_memory.o embeds that
address in exactly one MOV RAX,sign-extended-imm32 instruction; no other byte
differs (7472 bytes, two changed immediate bytes in the measured candidate).
Allow only that derived relocation, not another mechanism change. The oracle
must independently validate both inner/outer C payloads, derive the respective
export addresses, require one exact MOV occurrence at the same object offset,
normalize only its four immediate bytes and compare the entire object to AH.
Reject missing, duplicate, wrong opcode, unexpected address or any other byte
change. Add host negatives to the existing blockhost gate;31 files/20 groups
unchanged. Thus25 objects remain byte-identical plus this one exactly checked
derived link; the two explicitly amended implementations still match PIO/block.

Focused same-scope correction after attempt024ef0035bee4ff292465e2c22bb9997:
normal4/8GiB and OOM0/1 pass; OOM2 still exhausts one root. Common IPC inventory
shows successful/non-integrity-error SEND/RECEIVE never mutate Process local
capabilities. Only CREATE49, CLOSE52, DELEGATE55 and RELEASE58 can publish those
views; REAP also clears peer grants. Restrict REQUEST client sealing to these
four capability operations. Transfer integrity errors still enter fatal before
any adapter publication; no quarantine failure is turned into normal success.
The new red client-publication regression observes eight needless writes after
receive. Actual baseline/candidate transcripts, all-slot byte-corruption and
single-copy correction tests remain required; no new files, limits or gates.

The following focused cost regression distinguishes DELEGATE's actual target:
only the matching live target's two client guards may be published, not all
eight client guards. Common delegation either changes that target alone or
returns a non-integrity error without changing local clients; quarantine paths
return EINTEGRITY and cannot reach publication. CREATE/CLOSE/RELEASE and REAP
retain conservative all-client publication. The all-slot differential and
post-operation check_all proof must cover this narrower publication too.
Attempt6d055431707d4bcd9a8ab2f724b6fcca remains failed:4GiB passes, first8GiB
root exhausts after the eighth child; no accepted full matrix or unchanged retry.

Fixture terminal-cleanup correction: attempt3f17cbafa1db4a1d8b4d08ba4c13d091
passes all eight normal/OOM cases, then case2 exposes unused client variables;
all four producer variants now compile under unchanged Werror and are host
checked. Attempt144884d3ec0b4b818ccfa7558ac9793d still fails at root RIP40068c,
independently disassembled immediately after the first terminal IPC_CLOSE52;
all eight children were already retired. For normal/OOM roots, leave the three
owned endpoints to the already required automatic process-reap cleanup instead
of three redundant explicit close calls followed by the same cleanup scan.
Observe three exact live root-owned full-rights capabilities at the existing
final CREATE-exhaustion scrub boundary, then require the unchanged exact
IPC/profile/heap fence before root frame release. No extra syscall or breakpoint,
quota change, skipped exhaustion proof, or cleanup exemption. Missing-media
still exercises explicit close; owner-loss still exercises automatic cleanup
with an active child. The old PIO and actual IPC tests retain explicit-close
behavior. Negative host oracles reject absent/duplicate/misordered owner-release
evidence and stale/malformed capability views. This is the same lifecycle,
not permission to defer cleanup beyond retirement or change kernel code.

## Latest candidate stop after IPC cost correction

Attempt630ff21c1121492d83ee836861c2c4d3 fails15.313s in the first4GiB case.
Root1 exhausts32 samples at actual ELF RIP4008d3, immediately after syscall54
RECEIVE_TIMEOUT for the final LBA127 reply. Child10 is subsequently canceled
by owner loss (reason3, status0/state3,13 samples), not a normal80 result.
Root11 completes78 at30 samples and witnesses three live owned endpoints
before exact automatic fencing/frame cleanup. Both runs must pass; this attempt
accepts no case. Earlier eight-case progress is partial evidence only.

Actual IPC O0/O2 counts,215-step state equivalence and all-slot corruption
checks pass, as do nine blockhost tests and all four Werror program builds.
These do not prove reliable guest completion under the unchanged budget.
No further concrete bounded in-scope correction is demonstrated; stop before
another unchanged guest retry. The earlier four controlled diagnostics are
exhausted. Additional guest cost attribution requires a separately frozen
finite diagnostic budget, not skipped integrity checks, larger quotas, another
kernel mechanism change or acceptance from a partial/detached run. Keep the
package active and all candidate changes/evidence uncommitted and preserved.

## Renewed bounded syscall/scheduler attribution

The user approves the specifically proposed further four-guest diagnosis.
Freeze one additional batch, each guest at the existing20s ceiling on identical
validated image/catalog/C hashes: detached control, IRQ sample attribution,
IPC operation census, full observer with IRQ attribution. Count actual native
CPU samples by generation and interrupted RIP; correlate saved syscall number
only when the RIP equals that syscall's saved return address. Count IPC entries
by operation and slot separately; debugger wall time is not kernel CPU time.
Use at most4096 callbacks and256 aggregate keys per guest and the existing
observer/serial capacity limits. No extra guest writes or kernel modifications,
clock/CPU/PIO change, acceptance from diagnostics or repeat-until-pass policy.
Reuse the current diagnostic and blockhost files;31 files/20 gates unchanged.
Contract commit precedes diagnostic implementation. Concrete bounded corrections
inside the existing source/authority boundary may continue without routine
questions; any necessary new production failure boundary must be frozen first.

The additional batch is consumed by attribution-c034368876db44fd942c16554ed6cdd3.
IPC census records3134 entries:2724 TAKE,254 REQUEST,114 PUMP,20 BIND,20 REAP,
2 END. The scheduler unconditionally calls TAKE at every native task reentry,
including non-IPC resumes. This identifies a correction candidate, not a proven
complete budget fix. Detached/IRQ/IPC/full-IRQ root receipts all complete78;
none is frozen block acceptance. The full-IRQ final aggregate is missing due
to a CLI-quit diagnostic-output bug; only its receipts are usable. Host tests
now reject missing/duplicate summaries and prove the corrected generated quit
path and callback caps; no replacement or fifth guest was run.

Suppressing no-work C TAKE entries safely requires a new protected generation-
scoped completion contract at process_ipc.inc, outside the current allowed
production files. READY and the removed deadline entry alone are insufficient.
Do not introduce an unprotected work bit or omit real-operation verification.
Freeze this additional source boundary and actual ASM/corruption/lifecycle cost
tests before implementation, retaining all20 gates and original limits. The
candidate remains active but blocked at that scope boundary, not accepted.

## Authorized generation-scoped dispatch completion

Renewed explicit approval adds process_ipc.inc and actual ASM/adapter host
regressions (test_x86_64_ipc_completion.py, x86_64_ipc_completion_host.c).
34 files,21 groups; preserve the previous20 and add one O0/O2 gate. Retain
eight fatal guests and add a real corrupted completion-record fencing/halt
case in the same matrix. Freeze before modifying production code.

Four fixed24-byte records encode generation and unbound/idle/waiting/ready.
Each value has its complement and rotated-XOR check word. Check all four
records and exact generation before any transition or no-work return. BIND
requires a newer generation; pending REQUEST moves idle to waiting; ready
receipt moves waiting to ready before queue publication; TAKE requires ready
and a real non-pending C result, then consumes before copyout. REAP clears
state while retaining retired generation; END requires all unbound. Missing,
duplicate, stale and corrupt completion authority fails before client output.
No allocation, second wait node, persistent C cache or new user ABI.

All actual C IPC operations retain complete check_all, including TAKE. An
IPC-unrelated dispatch checks the completion authority instead of polling
unrelated IPC payloads. Payload integrity is still checked before any IPC
effect or copyout; PIO/context/profile checks remain independently mandatory.
This explicitly changes no-work dispatch, not the C entry validation contract.
The record detects changes in one or two encoded words; coherent corruption
of all three words is not claimed detectable, nor is this SECDED correction.
Corruption enters existing fatal fencing/halt without repairing metadata.

Host proof executes actual assembly for every slot, transition, stale identity,
corrupted word/bit, cancel/rebind and terminal cleanup. The actual adapter's
no-work path must make zero C calls, whereas a ready result must make exactly
one before copyout; missing results and corrupt authority fail closed. Existing
native IPC differential/corruption gates and all new block/old PIO/fatal guests
remain mandatory under unchanged32-sample,20s and PIO limits. Only the already
amended scheduler object changes; other mechanism pins and i386 remain intact.

Direct review after the first ten-case block pass identifies the no-work
serialization obligation formerly checked by C: the completion wrapper must
verify IF=0 before accessing its records, even when no C call follows. Actual
host regression first observes the missing rejection, then models only the
PUSHFQ input to execute the unchanged flags check with IF clear/set. Keep the
successful earlier guest evidence but rebuild/retest the amended scheduler;
no accepted candidate from an omitted serialization check.
