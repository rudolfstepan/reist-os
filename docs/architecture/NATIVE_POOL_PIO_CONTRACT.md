# Native eight-task PIO ownership — R8.3ao

Frozen after clean accepted `4f4e1df4`, 15 September2026, under continuous
interactive native completion. One visible-main-worktree package; no agent,
push, physical device or host configuration change. This is not acceptance.

## Inventory and one failure boundary

The accepted pool provides eight complete identity/context/image/IPC/heap
owners. The existing single PIO domain still restricts requests, stored owner,
old-owner retirement and diagnostic indexing to slots2/3; finish checks only
those two slots. Ring3 native_pio.valid and native_service_init_profile impose
the same limit. Changing only the syscall comparison leaves inconsistent
admission and potentially incomplete fencing/cleanup. Close them together.

Reuse native_pio/native_service/native_block and the existing full-profile,
generation/family, task retirement and emergency-fence mechanisms. No new ATA
implementation, kernel protocol parser, endpoint implementation or scheduler.
This is the device-ownership prerequisite for the later concurrent native
shell/file path, not a port of that separate application/service policy.

## Explicit profile and authority

NativePoolPIO / X86_64_NATIVE_POOL_PIO=1 selects the existing TaskPool8,
Wide/Import/Startup/Lifecycle/Runtime/Heap/IPC/RAM and PIO/BlockProfile backing.
Reject filesystem/file-launch and unrelated fault selectors before outputs.
Plain NativeTaskPool continues rejecting device combinations. All older
profiles retain four-slot PIO admission and exact executable/object/catalog
bytes. One common new kernel and program catalog serves the whole matrix.

Standard references and terminology remain those of
[ATA PIO](ATA_PIO_TRANSFER_CONTRACT.md),
[the PIO domain](NATIVE_PIO_DOMAIN_CONTRACT.md) and
[block profiles](NATIVE_BLOCK_PROFILE_CONTRACT.md): ATA data-in, IDENTIFY,
READ SECTORS, LBA28 and512-byte sectors, SysV AMD64/ELF64, existing REIST
negative errno, PIO request-v1/v2 and block RPC-v1. No public layout, syscall
number, old wrapper or persistent format changes; no new compatibility claim.

The explicit target build can recognize driver handles for slots2..7 rather
than2..3 in the existing Ring3 transfer/service code. Share one bounded owner
predicate; compile-time capacity is not authority. The default target stays4.
The kernel independently requires the selected eight-owner profile, exact
generation and a live child owned by root0 before BIND. Root1/fillers have no
PIO capability. Only the one bound live generation can access existing ports;
root0 alone controls BIND/FENCE. Keep every full-word attenuation check.

Validate low slot, positive generation<=0x7fffffff and inverse/state integrity
before each computed task/family/diagnostic address. Current and prior owner
checks use the correct1024-byte task and64-byte family stride. A new bind
requires the old owner fenced and retired; terminal receipt alone never
retains frame/device rights. Future/stale/foreign handles cannot regain rights.
Normal finish checks every dynamic slot2..7 FREE before state/trace clearing.
Do not clear a partial pool, forgive a corrupt owner, or repair records.

## Unchanged physical and resource limits

One QEMU pc/TCG CPU, primary legacy ATA master, ports1f0..1f7/3f6. No physical
disk, second device, writes, DMA, PCI, AHCI, IOMMU or VMware support claim.
Use only the already-authorized generated64KiB read-only base and exclusive
disposable qcow2 layer. Verify exact base/logical bytes and no overlay data
allocation before/after every guest including failure; preserve all outputs.

CPU<=32 samples/generation, eight CREATE attempts/root, one intrusive wait
node, existing heap/image/IPC limits, WAIT<=1000ms, SLEEP<=100ms, PIO<=64 calls
per100ms and<=16 input words/call remain. ATA wait<=200ms, RPC<=1000ms and
session<=3000ms remain; no wait polling without SLEEP, replenishment or hidden
restart. Fillers are finite IPC/sleeping processes, not new essential services.

Driver crash, sleeping hang/cancel, CPU exhaustion, invalid reply and root
loss retain detect/isolate/fence/reap/recreate/self-test ordering. The single
replacement redoes actual IDENTIFY and self-test read before accepting data.
Unaffected root1 continues. Normal root teardown cancels/reaps its filler
children through the same generation state machine, without a kernel bypass.
Corrupt kernel owner/retirement state physically asserts nIEN/SRST before
bounded diagnosis/halt; no general cleanup, record repair or resumed task.

## Frozen implementation and proof

First retain an actual expected-red admission test for a valid slot7 owner,
separate from acceptance. Host O0/O2 executes actual kernel assembly and
Ring3 transfer/service code for all slots2..7 plus invalid0/1/8/high values,
all generation boundaries, foreign root, missing rights, stale/replaced owner,
unretired slot7, bad inverse/clock, bounds before indexing, unchanged buffers
before errors, and physical fence before failure. Trace metadata/data/gaps/
zeroing and generated observer paths have executable negative tests. Existing
default PIO/profile/task pool/ABI tests retain their original assertions.

Three builds only: plain TaskPool, existing FileLaunch, new PoolPIO. Compare
all relevant old objects, inner/outer payloads, generated records and program
bytes against accepted AN/AM before reusing any old guest evidence. Old
observer/validator/tool/artifact hashes are bound; no reference pin changes.
Do not run historical full matrices when exact unchanged binaries and original
proofs are established. All20 queue groups remain mandatory.

One same-image lifecycle matrix has16 guests, two process runs each:
cases0..5: healthy driver in slots2..7 respectively (zero..five fillers);
case6: slot7/8GiB; case7: UD2 during data-in; case8: sleeping hang/CANCEL;
case9: CPU32; case10: malformed reply; case11: root0 loss during data-in;
case12: absent disk; cases13..15: OOM at first/middle/last actual driver
construction allocation, with exact rollback and one fresh attempt. All
except case6 use4GiB; fault/OOM cases fill through slot7. Root1 is independent.
Root0 admits at most five fillers plus driver/replacement (seven attempts;
OOM may consume the eighth). No counter reset or changed exhaustion result.

Each guest retains20s including capture/media/process cleanup; lifecycle total
<=320s. Same-image fatal gate adds exactly two20s guests after actual device
reset release: invalid slot8 owner with matching inverse; and a corrupted
slot7 retirement record. Require physical OUT before diagnostics, original
damaged bytes unchanged, no later reap/resume, CLI/HLT and unchanged media.
These injections prove the new bounded rejection path, not a historical cause.

Only a dedicated original-zero Ring3 root0 fixture-mode word may be written
by the lifecycle observer, once per root admission, at most two writes/guest,
after exact image/mapping/byte validation. No kernel state edits except the
existing OOM return adapter and the two explicitly named fatal injections.
Bind every write. No production test syscall or per-case recompilation.
Reuse full independent frame/private/immutable byte, W^X, FP/profile/IPC/heap
fence and zero/free checks; all eight concurrent slots and all six driver
positions are observed. Verify physical IDENTIFY/data bytes, RPC generation,
sequence/deadline/output and replacement. Binary RAM reads retain independent
same-stop kernel/high comparisons,<=2048 reads/128MiB per guest.

Host groups<=300s, builds/verifiers<=180s, lifecycle outer<=600s, fatal<=120s.
Independent hosts may run in parallel; timed guests run sequentially. Each
gate once per unchanged candidate. At most three candidate transactions and
54 guests/1080s total after no more than two evidence-directed corrections;
the first matrix failure stops, never unchanged retries or weakened oracles.
Preserve AN/AM evidence, original failures and i386 artifacts. Stop on outside
scope, user overlap, pre-existing source failure, default byte drift or need
for a different authority/persistence/platform boundary. All20 groups plus
direct ABI/authority/bounds/cleanup review precede local commit/queue advance.
Then continue the next in-priority package; R3.6b stays deferred.

## Candidate implementation bindings (not acceptance)

The new selector defines REIST_NATIVE_POOL_PIO only for the existing PIO
assembly and Ring3 compilation. Every old four-slot instruction branch stays
literal-identical. The Ring3 common predicate only changes target capacity;
the kernel still validates actual live root0 parent/generation authority.
The root prepares the imported ELF once, copies the complete record for each
CREATE and overwrites the source before an explicit GETPID observer boundary.
The eight syscall/profile/heap owners and CPU32 budget are unchanged.

One same-image runner derives the accepted pool frame/context/zero proof and
the existing diagnostic decoder, changing only the two explicit slot bounds.
Old observers remain unchanged. Cold release/fatal routes keep their actual
machine-code branch checks. Lifecycle writes are two root0 mode words and
the three-register OOM return adapter, solely at the first driver construction
after fillers. Actual-source host tests mutate every required event and receipt.

Fatal snapshots bind64-byte PIO state,8192-byte tasks,512-byte family records,
256-byte profiles,128-byte extended masks and192-byte IPC completions before
the exact16-byte owner/inverse or8-byte slot7-state injection and after OUT,
diagnosis and halt. Diagnostic trace storage is excluded from immutable corrupt
state because it can record its own rejected metadata. The retirement case
allows exactly four already completed first-run receipts before injection;
no subsequent reap/resume/cleanup or PROCESS_RUN_DONE is allowed. These small
snapshots use ordinary paused GDB reads, not a second binary RAM transport.

## 15 September: approved debug-metadata correction and build reuse

Candidate01 remains15 PASS /1 FAIL /4 NOT_RUN: all twelve host groups and the
three builds succeeded; default byte comparison rejected only the two pool
root objects. The54 other pool artifacts (including every linked executable,
catalog and kernel) and all69 FileLaunch artifacts match exactly. The two
objects differ in a generated include-directory path inside non-allocated
.debug_line and the resulting relocation offset; no guest has run.

The renewed user instruction after the explicit exception request permits a
strict comparison adapter only for pool programs/program0.o and program1.o.
Use ELF64 ET_REL section/relocation semantics and
[DWARF4 section6.2.4](https://dwarfstd.org/doc/DWARF4.pdf): one exact directory
bound to each producer manifest, corresponding unit/header lengths and
.rela.debug_line address-operand offset. Bounded parsing must preserve every
other byte, debug opcode, relocation symbol/addend, section attribute and
loadable section. Gaps must be zero, extents disjoint and fully bounded.
Do not discard debug sections, normalize arbitrary directories or accept
symbol/address/code changes. Linked ELF/PRG/catalog remain raw byte-identical.
Retain original objects, raw hashes and the original failed receipt.

Before changing the verifier, retain one real two-object expected-red test.
Then freeze unchanged20 obligations with only the five queue-listed metadata
files changed from candidate01. Preserve three successful builds: gates13..15
are explicitly REUSED after exact source/tool/profile/command/log/artifact
validation, not rerun or relinked. All twelve host groups and the remaining
default, sixteen lifecycle/two fatal guests, reference and review gates remain.
Original candidate/guest/time bounds are not reset. This is verification-only
authority, not runtime acceptance, reference-pin renewal or OS completion.

## 15 September: approved final runtime correction

The renewed instruction after the explicit runtime-correction request admits
the unchanged stopped candidate02:16 PASS (including three REUSED builds),
one FAIL, three NOT_RUN. Its six4GiB guests passed; the8GiB guest failed at
root0 generation1 CPU32/status256/RIP410831 after FREE(record). Both reads,
driver retirements, peer progress and full zero/free succeeded, but none of
that converts the failed workload to acceptance. Preserve all1474 files and
the seven-guest100.944622s ledger. Accumulated CPU cost is not causally
attributed to8GiB, host timing, observer or compiler from this single run.

Candidate03, the last original attempt, changes only the four explicit
PoolPIO fixture compiler selections from-Oz to-O2, matching the existing
plain TaskPool optimization. The generated machine code shows scalar large
copy/poison loops under-Oz; reducing that work is a proposed correction,
not a proven explanation. No source/ABI, library optimization, work item,
record size, syscall, quota, timer, driver, observer or expected outcome changes.
First execute and preserve an expected-red compiler-command regression, then
test actual producer command assembly for all affected and default profiles.

Reuse gates13/14 only with exact original inputs, tools, profiles, logs and
outputs and a byte-exact producer adapter admitting solely this conditional
optimization expression. Old pool/FileLaunch commands remain identical.
Gate15 runs once in fresh runtime-correction/native, never overwriting the
old image. Only its output directory and the corresponding image argument of
gates17/18 change; all20 logical obligations and original deadlines remain.
The verifier may adapt these provenance/image bindings, not the guest oracle.
The full16+2 matrix remains mandatory; historical guests are not substituted.
No fourth candidate, unchanged retry, larger CPU budget or reference pin change.
