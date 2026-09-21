# Native PS/2 input — R8.3bg

## Authority, inventory, standards

On21 September2026 the user renewed continuous completion in direct response
to the PS/2 proposal. This authorizes the shared keyboard/pointer domain.
Baseline is clean `f85a9c8f`, accepted BE17d12819/BFc33943da. Their evidence
and the i386 fallback remain intact. Proposal inventory remains historical.

Reference: i8042 status/command/data semantics, translated PS/2 scan-code set1
and standard three-byte relative mouse packets. QEMU pc/TCG,qemu64,one CPU,
4/8GiB only. Upstream controller reference:
https://github.com/qemu/qemu/blob/master/hw/input/pckbd.c
Actual QMP input proof follows input-send-event in
https://www.qemu.org/docs/master/interop/qemu-qmp-ref.html .
No USB, DMA, PCI, network, physical input capture or hardware compatibility
claim. Existing key tables/semantics in drivers/char/kb.c are reference only;
the kernel driver is not linked into native64.

## Mechanism and fixed profile

Append DEVICE_CONTROL113 operation31, request v1/64 bytes: u32 version,size,
operation,flags; u64 owner,epoch,deadline_ms,value,reserved[2]. Operations are
BIND1,QUERY2,READ3,CONTROLLER4,DATA5,FENCE6. Old operations/profiles unchanged.
Owner is root0's exact live child; bind requires old fence and reap. Fixed
128-byte state: owner,parent,epoch,fenced,window,last,operations,prefix plus
inverse. Epoch survives root cleanup. Inconsistent trusted state is fatal.

QUERY returns epoch; READ returns packed status<<8|byte plus1 or EAGAIN.
It performs one status read and only if OBF one data read. Reads preserve
AUX/error bits for Ring3 validation. Writes perform one status read and only
if IBF clear one8-bit write; EAGAIN never advances the prefix. Valid accesses
charge64 operations/100ms, absolute deadline<=1000ms, no credit accumulation;
exhaustion fences. Invalid requests have no IO effect. No allocation or wait.

Controller whitelist:20(read config),60(config prefix),a7/ad(disable ports),
a8/ae(enable ports),d4(mouse prefix). Data without prefix or with mouse prefix
permits onlyff(reset device),f5(disable),f6(defaults),f4(enable). Config data
permits only70(disabled) or40(enabled), translation on and IRQ bits off. Never
admit output-port/A20/CPU reset, injected-output commands or arbitrary bytes.
The safe60 prefix may supersede an unfinished prefix during fresh takeover;
every other invalid prefix transition fails before IO. Successful data clears
prefix. Logical fencing immediately forbids further IO/delivery, clears the
prefix and does not claim electrical disable. New driver must reset controller
configuration, drain stale bytes, reset/self-test both devices and clear all
decoder/modifier state before publishing HEALTHY. No stale event reintegration.

Use bounded Ring3 polling with10ms SLEEP and absolute deadlines, not IRQ1/12.
The existing IRQ0-only PIC/PIT profile remains exact. Fixed admission is
sufficient for this polled QEMU profile; no asynchronous IRQ guarantee.

## Ring3 lifecycle and consumer

The normal shell still starts /boot.prg in foreground slot4, with its existing
display/terminal rights. For this opt-in image it also creates one IPC endpoint
and a separate embedded input driver in slot5. Delegate RECEIVE only to4,
SEND only to5. Root binds input5 and display4, never raw input to the client.
Capture ordinary service/file2/3 before driver5, preserving old slot behavior.
Driver uses existing periodic32 samples/1000ms; foreground uses its existing
32-sample limit. No creation/restart quota increase. SDK records bind target,
driver,epoch,sequence and canonical size/type; cap32 delivered events.

Only this input command gets a5000ms absolute session, including startup;
startup<=1000ms and every IPC/wait<=1000ms. Shell waits in at most five bounded
slices, without renewing the end; all old commands keep their1000ms policy.
Driver parses keyboard modifiers/extended/release sequences and mouse signs,
buttons/overflow; incomplete sequences expire, faults clear state and isolate.
Client displays bounded pointer feedback and serial event records. Its normal
EXIT, failure, crash/hang/quota and parent loss converge on root fence, cancel,
reap and endpoint close. A later invocation recreates and self-tests through
the same construction/cleanup path. Ambiguous cleanup exits root. Persistent
desktop focus/global keyboard routing is subsequent, not claimed by this
finite input session.

## Frozen proof

Actual assembly host O0/O2 admission/nonmutation/quotas/prefix/fence tests;
Ring3 decoder and controller transcript host behavior including malformed,
missing, stuck modifiers, timeout, overflow and reset. Guest matrix12 cases:
healthy,8GiB,800x600,driver crash,CPU spin,hang,quota,stale,malformed,flood,
missing controller,parent loss. QMP actual key/pointer injection, independent
raw events, pixel/state readback, exact IPC generations/profile/reap, later
file/shell liveness and all no-write proofs. Preserve full inherited ten-case
CLI runtime/containment matrix. Source patterns alone never establish runtime.
Ten gates in queue; direct diff/scope review and clean local commit follow
only after all pass. Development reservations in queue are finite and distinct
from qualification; every failed command/image/guest is retained. R3.6b deferred.
