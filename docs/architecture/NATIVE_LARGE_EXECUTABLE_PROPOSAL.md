# Native large executable profile: measured proposal

Approved by renewed user continuation after commitb8aa7ab4. Implementation starts
with R8.3bu; historical decision/evidence text below is retained.

## Evidence and decision boundary

23 September2026, clean accepted text commit3306169310d4cdddf1ac6e2b93fa1b4ff7e40f42.
BT passes all five gates,13 host tests andten fresh guests; seal
fc9d2d9b27df9c9558ddbb313b0102625732ae3919314b3b0680bd9387440100.

Host-only inventory is retained under build/codex-agent/native-js-inventory01.
Pinned QuickJS2026-06-04 with its existing generated omissions compiles for
AMD64/Oz. The ordinary native libc/math/text/provider archives plus genuine
Zig compiler_rt link a minimal create/evaluate/destroy consumer with no
undefined symbols. The inspection linker expands only its host-side assertion;
this ELF was never admitted, packaged or executed in the OS.

Measured link03: file754104 bytes; loaded span923968 bytes from0x410000;
RX611383, R132584, RW174400 bytes (including zero-filled BSS).
ELF SHA256 cd09ca66eb4fa5f12ed3991cdfd37305b59d76abc55521402e681847afab3be2.
The compiler runtime supplies AMD64 BigInt's __udivti3; no zero-result stub.
Initial inventory12.158s retained its PE-only linker error; ELF link02 retained
its missing compiler-runtime error; real runtime build/link03 passes2.049s.
No guest/runtime, complete language or native JS acceptance claim follows.

The existing explicitly authorized program boundary is RNPGv2/64 image slots
and32KiB stack (NATIVE_PROGRAM_MEMORY_CONTRACT); the current linker allows
196608 bytes above0x410000. Its ELF input cap is524288 bytes. The separately
approved NATIVE_WIDE_FILE_CONTRACT admits524288 captured bytes,2050 filesystem
requests and4096 block reads. Both program mapping and immutable file capture
are insufficient for the measured native engine. Existing successful private
heap allocation does not silently authorize a larger executable import or
more work by the isolated filesystem/block services.

AGENTS.md requires stopping at a genuine authority/safety boundary; its
continuous-work directive removes routine reservation approvals, not new
resource grants. Request one explicit bounded larger-executable/capture
profile covering the following related prerequisites. No implementation
package is active until this scope is approved. R3.6b remains deferred.

## Concrete proposed bounds

| Resource | New explicit profile | Existing profiles |
|---|---|---|
| ELF input / immutable capture | at most1048576 bytes | unchanged |
| Prepared mapping | RNPGv3,256 slots,0x400000..0x500000 | v1/v2 unchanged |
| Program bytes above reserved stack | at most983040 bytes | unchanged |
| Stack / lower guard | existing32KiB/4KiB, no executable stack | unchanged |
| Prepared record | 288-byte header +1048576 image +4096 arguments =1052960 bytes | exact old sizes retained |
| Kernel task record | private4096-byte layout only under explicit selector | old layouts retained |
| Filesystem requests | at most4098: STAT,4096 x256-byte reads, EOF | old limits retained |
| Block reads | at most8192 per exact generation | old limits retained |
| Whole-file / service lifetime | existing120000ms absolute ceiling | unchanged |
| One RPC / ATA operation | existing1000ms /200ms | unchanged |
| Cache / pacing / kernel PIO | existing16 sectors,100ms first/50ms later, existing kernel caps | unchanged |
| Task pool / CPU / creation / restarts | existing explicit limits; no increases | unchanged |
| Heap / output / script authority | no additional grant | unchanged |

The new mapping keeps reserved slots7..15 and existing independently owned
stack page8. W^X, canonical addresses, file-backed entry, ordered disjoint
PT_LOAD ranges, eight segment descriptors and exact zero reserved fields
remain mandatory. Parsing remains in Ring3; Ring0 admits only the fixed
prepared metadata and owned pages. A new append-only CREATE version must be
chosen after existingv6 is inventoried; do not reusev6 or widen its meaning.
Old requests cannot select a larger record by supplying a longer buffer.

Every import validates the complete source range, snapshots before any
publication, rolls back every partial allocation and scrubs the whole staging
record. Fixed-capacity owner/frame arrays, high physical frames, stale
handles, private RW copies and exact generation cleanup require real proofs.
The increase is a hard upper bound, not an eager allocation or success promise.

Capture binds one immutable medium and exact driver/FS generations to one
absolute deadline. No automatic counter reset, retry, deadline renewal or
service recreation inside a capture. Old observations cannot be converted.
Existing FAT12/FAT32 and EXT2 direct/single-indirect parsing remains bounded;
use a suitable generated2KiB/4KiB EXT2 layout where1KiB would require an
unsupported double-indirect block. No parser shortcut or compatibility claim.

No write/persistent-format authority, DMA, new device, public network,
script filesystem/network/DOM authority, periodic CPU increase, arbitrary
executable destination or privilege inheritance is requested. QuickJS's
existing external process supervision remains required; its cooperative
interrupt is not a replacement for fault/hang isolation.

## Successive verification transactions after approval

1. Freeze the complete prepared-image/CREATE/frame ownership mechanism with
   SDK and actual guest consumer. Host O0/O2 executes real parser/admission,
   exact legacy projection and negative mutations before bounded4/8GiB,
   partial-OOM, immutable-copy, fault/reap/recreate and full raw guest proof.
2. Freeze the larger immutable capture/service profile and ordinary shell
   launch together, including Windows/Make media, capacity/generation/deadline
   rejections and driver/FS/app failure recovery. Preserve old artifact pins.
3. Freeze the native QuickJS engine/SDK/ordinary jstest vertical slice using
   the accepted mechanisms, with real AMD64 language/ownership tests, bounded
   OOM/deadline/job failures and external crash/hang/CPU/restart proof. Native
   script file runner/browser integration remains subsequent scope inventory.

Each transaction gets exact allowed files, finite reservations and frozen
acceptance gates before implementation. No failed or diagnostic run counts
as qualification; one active package, local commit only after all gates,
clean-worktree boundary, no nested agent and no push.
