# Native64 VGA text console prerequisite (CJ)

## Authority and transaction

2026-09-26 user "mach weiter" directly answers the concrete VGA-console
scope/authority request and authorizes that proposal. Default boot must show
actual VGA mode03 text and the ordinary Ring3 shell. Preserve the original
full desktop objective and all CB gates. CB candidate30 files archived and
verified: before-native-vga-console02/candidate.zip SHA256
c3017dca8ad1e368f9876bd72c23dd404e5990d2129727156cdc293da080da77.
Only attributed, byte-verified code was restored to898f30d5; histories remain.
Exactly one implementation package: CJ. CB remains queued/unaccepted.

CJ is the complete VGA console/keyboard/shell/recovery vertical slice. Native64
text-to-graphics and graphics-to-text hardware transition follows as a distinct
hardware acceptance boundary before restored CB desktop integration. The
existing BITS32 BIOS thunk is not native64 evidence. No finished-OS claim or
permanent abandonment of the required desktop transition is permitted.

## Frozen architecture

References: IBM-compatible VGA mode03,80 columns/25 rows, two-byte character/
attribute cells at physical0xb8000; existing PS/2 set1 decoder and existing
terminal foreground ownership; ASCII control characters and explicit bounded
ECMA-48 subset in Ring3. No claim of unrestricted VT compatibility. Private
REIST VGA mediation v1 uses fixed64-byte requests on appended DEVICE_CONTROL
resource33; existing resources30/31/32 and syscall numbers retain meaning.

Ring0 implements only generation/parent/profile/range admission, fixed cell
copies (<=80 cells/request), bounded byte transport (2048 output bytes/64 input
bytes), fencing and a bounded early/fatal status line. VGA's one4KiB mapping
is supervisor-only, writable/NX, cache-disabled, checked before access. No
raw user MMIO/PIO/DMA, font renderer, escape parser or scroll policy in Ring0.
Boot selects text mode03; unsupported/non-text handoff fails closed.
Early/fatal diagnostics write at most80 fixed message bytes to a reserved line;
ordinary running text rendering belongs to the separate Ring3 console process.

The console process owns a fixed2000-cell shadow, parser state and existing
bounded PS/2 initialization/decoding. No heap, file or network authority. Root
spawns it while storage slots2/3 are live, placing it in existing free slot4;
thereafter storage may retire/recreate independently. Existing <=32 CPU samples
per1000ms and task/image/heap/restart bounds apply. No task/pool/quota increase.
Ordinary shell remains root0; existing foreground authorization precedes any
console READ/WRITE mediation. COM1 remains available alongside visible output.

VGA v1 operations: bind1/revoke2/query3/read-output4/write-input5/write-cells6/
heartbeat7/status8. Bind/revoke/status require the controlling direct parent;
service operations require exact live owner/epoch. Query grants no authority.
All reserved fields/sizes/pointers/counts/ranges are checked before side effects.
Bind requires old owner reaped; stale generations never regain access. Root or
service death fences both queues and VGA access; existing PS/2 fencing remains.
Revoke is idempotent. No byte truncation/overwrite when queues fill: return
EAGAIN before effects and retain caller deadlines. Fixed staging is scrubbed.
One service health deadline1000ms, root checks <=250ms apart; initial self-test
and recreation share an absolute2000ms end. Existing restart budget is spent,
never reset. Exhaustion leaves a visible bounded failure status and serial
rescue access. No endless retry or unverified recovery.

## Scope

The active queue's allowed_files is authoritative: native64 entry/scheduler/
console/dispatch/family hooks; new VGA core/adapter/header and Ring3 service;
SDK shell integration; explicit build/media selectors; actual behavior tests;
console package/runtime verifier and this documentation. Unselected builds
must remain byte-identical. No edits to the archived CB source to disguise
prerequisite work. Restore CB only after accepted CJ and required handoff.

## Frozen gates (once per qualification, first failure stops)

1. python test/test_x86_64_vga_console.py -v (180s): actual core/renderer at
   O0/O2; denied pointers/parent/generation/range, saturation before effects,
   exact cell text/scroll/control handling, idempotent revoke, old-owner denial.
2. python scripts/verify_x86_64_vga_console.py --defaults (300s): complete
   disabled source/artifact comparison against898f30d5; accepted dependencies
   remain bound by exact provenance, without repeating unchanged guest matrices.
3. python scripts/verify_x86_64_vga_console.py --package (600s): no undefined
   imports, signed text BIOS media, fixed image/stack/CPU bounds, both shell
   installation layouts and exact allowed-file review.
4. python scripts/verify_x86_64_vga_console.py --runtime (2400s): three fresh
   bounded QEMU cases<=600s each, <=1800s aggregate: ordinary shell plus PS/2
   command/error/VGA cells; console crash/stale owner and reintegration;
   console hang/restart-budget exhaustion/visible failure. Include injected
   early boot error visibility and serial parity. No synthetic shell substitute.
5. python scripts/verify_x86_64_vga_console.py --review (600s): independent raw
   replay/cell bytes, actual owners/resources/cleanup, source/tool/image binding.
   Bounded VMware text-shell visual proof<=180s also required before delivery.

Development reservation: hosts01..12<=180s, builds01..03<=300s,
media01..03<=180s, QEMU01..04<=300s and VMware01<=180s. Preserve each failure.
New evidence-directed finite reservations follow AGENTS without routine
reauthorization; all frozen gates and per-operation limits remain unchanged.
