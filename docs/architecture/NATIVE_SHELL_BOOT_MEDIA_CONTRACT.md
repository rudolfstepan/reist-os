# Native shell boot media: R8.3az

Frozen after accepted AY commit `455fbb9d`, 20 September 2026. This document
defines a candidate, not an acceptance result. The eight queue gates are final.

## Inventory and one integration boundary

AY qualifies the real Ring3 shell, file capture/start, terminal/wait and bounded
service recovery through direct QEMU kernel loading. AB separately qualifies
signed BIOS media with the old heap fixture. NativeImages still selects that
fixture and its independent consumer caps kernels at1MiB. AY's1382432-byte
kernel fits the unchanged1540096-byte HDD A/B slots, and the rescue floppy
kernel extent; it must not be mislabeled as the old heap package.

The existing Ring3 FAT adapter expects a volume at sector zero, not an MBR.
AY's exact media/geometry and no-write proof must not be broadened silently.
An integrated boot does not require that broadening: keep the existing primary
ATA master as the read-only data volume and attach the BIOS boot HDD as primary
slave, or use the rescue floppy. Only BIOS accesses those boot devices. The
native mediator still rejects slave selection and every write/DMA command.
No new kernel/driver/parser, resource grant or persistent format is added.

The explicit research profile boots its signed embedded normal shell/service
catalog and reads `/boot.prg` from the existing separate immutable EXT2 volume.
The catalog's normal shell is the existing `root/bin/shell.prg`; it is not an
unsupported promise that the data volume can reload that large ELF. General
file sizes, writable storage, a unified partitioned root, desktop/browser,
boot-health confirmation and physical/VMware acceptance remain separate work.
Do not describe this bounded two-medium configuration as the finished OS.

## Standards and publication

Reuse GNU Multiboot-v1/E820 handoff, existing ELF32 transport/ELF64 System-V
payload admission, BIOS Stage1/Stage2, Manifest3, fixed A/B extents and existing
FAT32/FAT12 media producers. Reuse AB's RSA2048-PSS/SHA256/MGF1 salt32 research
policy and independent signature checker. The public fixture key and writable
bootloader are not a production trust root, Secure Boot or antirollback proof.

One fresh generated package contains the same exact AY kernel on HDD512MiB
and floppy1.44MiB, the128KiB EXT2 data medium, exact embedded catalog/program
inputs and external executable, and a separately named signed host index.
The host index is a versioned research packaging contract, not a guest ABI.
The independent consumer must bind actual media bytes, all signatures, complete
catalog/ELF relationships, external file bytes, geometry and exact artifact set.
Reject duplicates, path escapes, symlinks/junction escapes, invalid versions,
truncation/growth and substitutions. Use bounded reads/streamed hashes and
atomic publication only after independent verification. Preserve every attempt
and previous index. Windows and Make invoke the same producer; no implicit
kernel rebuild and no existing NativeImages/default change.

Only generated bases in ignored build/codex-agent and disposable COW layers.
Data remains the accepted primary-master configuration. The separate boot HDD
must be explicitly primary-slave with BIOS boot priority; no unrestricted
argument pass-through. No network, shares, extra CPUs, visible VM or real disk.
Before and after each guest, prove both base bytes and complete logical COW
contents unchanged, including zero allocated overlay data. Fresh confirmed-A
boot state and original AB signature/digest/manifest rejection cases are in
scope; pending updates or confirmed-B rollback requiring BIOS writes are not.
An attempted boot-control write is failure, not an allowed exception.

## Frozen evidence window

Zero kernel builds. One fresh signed paired-media publication; all immutable
AY artifacts and tool/source receipts bind back to candidate17's accepted final
receipt `058147106d58a0ced94d32dc54000efba177f53aeb39a62044cc80f7d9c577a3`.
Prior eighteen runtime cases remain prior evidence, not fresh AZ runs.

Eight gates in queue order: new host regressions; dependency/source/input
binding; one paired-media build; actual package/signature/corruption/publication
host tests; integration matrix; pinned old reference artifacts; independent
raw review; scope. Host gates300s, runtime600s, other gates180s. Freeze exact
commands, source/tool hashes and finite reservation before executing any gate.

Ten guests maximum,325s aggregate: HDD healthy4GiB (AYcase2),8GiB(case5),
long session(case6), bad A signature with B fallback and driver crash/recovery
(case7), floppy plus sleeping application failure(case13), all with layout2
data and the original full AY observer/oracles. Five BIOS rejection guests:
both HDD signatures, both CRC-valid SHA failures, both manifests; floppy
signature and SHA failure. BIOS ordering/count checks add to existing oracles.
Positive bound45s including cleanup<=3s/observe42s; negative20s. No separate
diagnostic guest reservation or unchanged retries. All CPU, creation, ATA,
IPC, FS, capture and restart quotas/deadlines stay exact.

Keep default/old media source and runtime code unchanged. Review real diffs for
scope, publication, cleanup, media selection and ABI drift. Commit only after
all gates pass and exact queue transition; then continue next clean transaction.
First failure stops the window and retains every artifact and spent count.
Any necessary write, new device authority or changed accepted runtime is a
genuine stop boundary. R3.6b stays deferred. No push or nested agent.
