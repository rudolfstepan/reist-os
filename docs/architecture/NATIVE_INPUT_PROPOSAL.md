# Native64 input boundary — accepted proposal history

The renewed completion instruction after the explicit approval question on
21 September2026 authorizes this proposal. R8.3bg/NATIVE_INPUT_CONTRACT.md
now freezes its bounded implementation and proof; the inventory below is
retained history, not a renewed approval requirement.

Inventory21 September2026 on clean accepted display starter `c33943da`,
final receipt SHA256
`e6620d2a8d53135c1429f235639ce3e7b9d7f81cf5f6e33cb3aebd91818eed0b`.
Display mediation `17d12819` and starter `c33943da` are complete. This document
does not activate another implementation or reserve builds/guests.

## Concrete missing boundary

- `arch/x86_64/proc/native_console.inc` and `native_terminal.inc` read COM1.
  A QEMU window keystroke does not enter this serial stream.
- `arch/x86_64/devices/pio_domain.inc` admits only the primary ATA master
  register/command whitelist. Ports0x60/0x64 are rejected; permitting them
  through that domain would mix storage and input ownership.
- `arch/x86_64/cpu/timer_interrupt.asm` enables only IRQ0: PIC master mask0xfe,
  slave0xff. There is no native Ring3 input IRQ ownership or dispatch.
- `drivers/char/kb.c` is an existing i386 kernel driver. Its bounded controller
  takeover, scancode tables and key semantics are migration references. Linking
  the driver into native Ring0 would violate the protected microkernel boundary.
- The accepted display profile explicitly excludes input devices. AGENTS.md's
  interactive directive preserves a stop for new authority domains even under
  the continuous-completion order. This is not an exhausted diagnostic window.

## Proposed next cohesive slice

Authorize one opt-in QEMU PS/2 controller domain for keyboard and pointer
together: they share the i8042 controller and recovery boundary. Restrict it
to QEMU pc/TCG, one CPU,4/8GiB and emulated ports0x60/0x64. No new ATA rights,
DMA, PCI, USB/xHCI, network, host input capture or physical-platform claim.

Keep scancode/packet parsing, layout/modifier policy and device protocol in
a separate Ring3 driver/service. Reuse existing semantics behind explicit
adapters where they fit. Ring0 provides only whitelisted bounded transport,
fixed-capacity raw records, exact-generation ownership, deadlines, fencing
and any necessary bounded IRQ mechanism. Preserve the i8042/PS/2 terminology,
port/status semantics and scan-code/packet formats; append and version REIST
requests without reusing the ATA operation or changing old profiles.

No raw port privilege or controller-reset/output-port command reaches an
ordinary process. Freeze allowed commands, polling/IRQ choice, capacities,
per-call/window quotas, deadlines and reset/self-test policy before code.
Any polling sleeps in Ring3 under an absolute deadline; no userspace busy-wait.
Fencing, stale input discard, reap, recreation and self-test are mandatory
for keyboard and pointer together. Exhaustion leaves input unavailable while
serial diagnostics, display and unrelated file services remain usable.

Integrate the normal Ring3 consumer and SDK in the same transaction. Prove real
QEMU-generated key/pointer events and normal command/event delivery; include
missing device, malformed/incomplete sequences, stuck modifiers, queue flood,
quota, stale owner, crash, hang and parent loss, then exact-generation recovery.
Keep the existing display and read-only file behavior, original CPU/IPC limits
and independent raw replay. Do not claim a complete desktop from an input test.

After authority is resolved, inventory all affected consumers and freeze one
complete file scope and finite qualification matrix. The alternative is to
retain serial-only input; that leaves native desktop completion pending.
R3.6b remains explicitly deferred in either case.
