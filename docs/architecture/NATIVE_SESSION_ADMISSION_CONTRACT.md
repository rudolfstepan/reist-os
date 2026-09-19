# Native session construction admission v1 — R8.3ax

Frozen19 September2026 on fee850d2. The user's renewed yes explicitly approves
the separately proposed durable shell/supervisor profile. AX implements its
kernel creation-admission failure boundary; the Ring3 service/restart policy
and ordinary shell composition remain subsequent work under that authority.
No claim of a completed persistent shell or full64-bit OS follows from AX.

## Standards and scope

Keep System V AMD64, ELF64 and REIST TASK_CONTROL132 CREATE1..6/WAIT/CANCEL.
This is a named REIST boot policy, not a changed POSIX operation or new public
syscall. NativeSession is an explicit device-free NativeServiceCPU opt-in for
qualification. A versioned immutable boot witness declares version1, eight
attempts per1000ms and root0 only. CPU32/1000ms, all child grants, fixed eight
slots, generation exhaustion, operation deadlines and rollback are unchanged.
Root1 and every old profile retain eight attempts for their entire generation.
No clock-driven restart policy, filesystem/driver rights or child TASK_CONTROL.

## One bounded kernel state machine

One fixed56-byte private state: generation, period_ticks100, anchored start,
last observed tick, current-window attempts, cumulative attempts, version1.
Initialize once from the admitted root0 generation and monotonic scheduler
tick. No reset through WAIT/CANCEL/sleep/reaping or empty capacity. Cumulative
attempts are mirrored by the original family record's attempts field and never
decrease. Only final complete family cleanup clears the retired root's state.

Pure bounded admission validates every word before any write. Generation is
positive and at most0x7fffffff; ticks are below2^60, cannot regress; count<=8,
count<=cumulative<=0x7fffffff. Window start is no later than last tick; last tick
belongs to that anchored100-tick window. An idle gap advances the anchor by
whole periods without accumulating credit, multiplication overflow or loops.
CHECK is read-only. CHARGE commits at most one attempt after ordinary request,
capacity, attenuation and global-generation admission but before allocation.
An exhausted current window or cumulative counter returns EAGAIN without any
mutation; allocation failure after charge spends the attempt. Corrupt state,
generation mismatch or regressing time takes existing fatal diagnosis/halt
before construction, never repairs kernel state. Empty slots/retained receipts
remain authoritative for capacity; elapsed time never releases a task slot.

family_total stays cumulative; its former18 bound applies unchanged outside
NativeSession. The explicit profile uses the existing positive31-bit generation
ceiling, checked before publication. Root0's mirrored attempts, window state,
phase and exact task/family generations are revalidated at scheduler boundaries.
No replenishment of frame, heap, IPC, CPU or terminal authority is implied.

## Verification and finite reservation

Queue lists exactly nine gates. Targeted production-assembly O0/O2 tests precede
implementation, including real adapter charge placement and a before-fix red
case. Default preprocessor/producer evidence protects prior profiles. One common
NativeSession image runs unchanged12 CPU lifecycle cases and two CPU fatal
cases, plus a finite session workload exceeding eight total root0 constructions
with fresh generations, blocking window wait, stale rejection and complete
retirement. Two new corruption guests cover private generation/count state and
preserve damaged bytes through fatal diagnostic/CLI-HLT, with no cleanup/resume.
Full existing raw lifecycle/CPU/heap/frame/IPC oracles remain required.

At most17 fresh guests,30 seconds each including at most3 seconds cleanup,
510 seconds aggregate; runtime gate600 seconds. One image/build. First failure
closes the current window; no unchanged retry. Preserve failures, logs, hashes,
spent build/guest counters. Freeze a separately justified finite correction
before continuing. Full source/tool/command/raw binding, direct ABI/bounds/
cleanup review, all gates and a clean local implementation commit are required.
No nested agent, push, visible guest, profile weakening or R3.6b work.
