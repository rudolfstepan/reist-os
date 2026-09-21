# Native64 display delivery — R8.3bf

## Scope and inventory

Continue the user's standing native64 completion instruction after accepted
BE commit17d12819 and clean final receipt6c584e979e3cbf56dbf35f53aadf949b8d205481865159b1d4a0cd9b20ff4df8.
BE proves fixed Ring3 tiles and containment in QEMU; it exposes only development
commands. The existing CLI starter already validates signed media, creates
private overlays, uses serial stdio and bounds cleanup. Its CLI-only validator
correctly rejects BE media. Deliver a separate normal starter using the exact
accepted BE image, input hashes, signed media index and display consumer.
No old starter, build, kernel, guest application or medium changes.

## Failure boundary

The host starter owns only its QEMU subprocess and private session directory.
Reject foreign, unsigned, modified or malformed media before creating a
session or launching QEMU. Bind the exact accepted index and twelve input
hashes in addition to the existing independent signed-media validation.
Never infer acceptance from the presence of display symbols or serial markers.
Use unchanged BIOS device layout, readonly data and disposable boot overlays;
verify both media before and after execution with full raw tool evidence.

Use QEMU pc/TCG, qemu64, one CPU,4/8GiB, VGA16MiB, no network or host shares.
Normal user invocation selects the installed GTK display; an explicit headless
switch keeps automated execution invisible. Input remains the serial Ring3
shell. The accepted /boot.prg writes a64x64 test tile; this is no desktop,
keyboard/mouse driver or new graphics API. QEMU CLI conventions and existing
Multiboot/VBE, ELF64, BGRX and REIST display-v1 contracts remain unchanged.

Session duration is an integer30..320 seconds, with the last3 seconds reserved
for bounded termination and media verification. The monotonic deadline starts
before private media preparation and is never renewed. Ctrl+C, timeout, guest
exit and setup/process/media errors converge on owned-process cleanup and
exclusive final evidence. An error remains failure even if cleanup succeeds;
cleanup failure cannot erase the original cause. Stop on unresolved cleanup.

## Frozen acceptance

Nine allowed files and six commands are frozen in the queue. At most four
development host commands300s precede qualification; zero builds/publications.
Host behavior tests cover exact admission, invalid selectors, check-only with
no launch, process failure, timeout, Ctrl+C, setup failure and cleanup failure.
Test the actual Python and PowerShell entry points. Two real headless starter
sessions (HDD4GiB/floppy8GiB,60s each including cleanup) must launch the ordinary
shell, paint via boot.prg, run cat, reap their exact successful generations,
complete both root runs and leave both media unchanged. Maximum120s physical
guest time; runtime gate210s. No debugger or guest patching. Independently
replay serial, command, session timing and every media tool/extent receipt.
Compare all accepted predecessor source/tool/artifact bindings and the i386
reference; full twelve-gate BE evidence remains pinned. Six gates then direct
scope/diff review, local commit and clean final receipt; never push.

R3.6b stays deferred. Desktop/input/network, writable filesystems and additional
hardware/platform acceptance remain subsequent independent boundaries.

Candidate01 gates1/2 passed; gate3 stopped before QEMU start because the old
CLI fixture admits only20/30/320/330 seconds. Zero physical guests, complete
private boot-medium cleanup, original failed capture retained. Three initial
host commands spent. Reserve two further300s host commands for actual fixture
red/green, then candidate02 same six gates/two60s guests. A private exact helper
adapter admits only integer30..320; the existing absolute started+limit tool
deadline, bytes, device paths and all prior checks remain unchanged. The old
CLI implementation is not modified. No guest/runtime resource change.

Both correction host commands spent; the first new-helper absence and the
second test-directory setup error are retained. Production creates that
directory already. One additional300s host command fixes only the test setup;
no guest/build/media consumed and candidate02 gates remain unexecuted.

## Accepted candidate02

All six frozen gates pass: twelve host methods, actual Python/PowerShell
check-only entries and old CLI admission, two complete real headless sessions,
reference artifacts, independent raw replay and exact scope. Each session
contains two successful display launches, two file outputs, four distinct
foreground generations and two clean roots, followed by owned QEMU termination
and full unchanged-media proof. HDD4GiB/floppy8GiB total115.25183679995826s;
zero builds/publications. Candidate01 consumed zero guests. All failure and
host-correction evidence remains under `build/codex-agent/r83bf-display-delivery/`.
Seal and final clean implementation-commit receipt: `candidate02/seal.json`
and `candidate02/final.json`. GTK command selection is host-tested; actual
sessions were headless, without a manual window/input acceptance claim.
