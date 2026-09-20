# Native wide shell BIOS media: R8.3bb

## Inventory and scope

Frozen on clean accepted BA `02202bd37e46683bc85b92307dfc9c4582d78afc`.
Final BA receipt: `build/codex-agent/r83ba-wide-file/candidate12/verification-status-wide-file-final.json`,
SHA256 `470f37033ca735de54c0d044b7a1b50b5592691e12cff6dc38c9503e917736c0`.
BA qualifies512KiB input with fixed Ring3 capture/service budgets, not BIOS media.
AZ qualifies signed BIOS media but its deliberately separate consumer limits the
external app to1280 bytes and the EXT2 data image to128KiB. Its existing producer,
independent verifier, BIOS entry handshake and complete no-write proofs are the
implementation base. Reuse mechanisms, not the old profile name or weaker proof.

The next single transaction packages the exact accepted BA kernel/core/catalog/
programs and external29032-byte executable. No kernel or userspace rebuild.
Only an explicitly selected, separately named research host package is new.
Windows and Make invoke the same packaging producer with explicit existing input.
The one historical ShellSession Make projection must remove only the exact new
packaging target; its original equality and mutation predicates stay intact.

## Standards and failure boundary

Reuse GNU Multiboot-v1/E820, ELF32 transport/ELF64 System-V payload, existing
BIOS Stage1/2, Manifest3 and unchanged HDD A/B/floppy extents. Existing RSA2048-
PSS/SHA256/MGF1 salt32 research signing stays unchanged. The public fixture key
does not establish production trust, Secure Boot or antirollback.

Keep the primary-master read-only data volume separate from the BIOS-only
primary-slave boot HDD or rescue floppy. No new device, DMA, write, IRQ or kernel
parser authority. Both media remain immutable, proven by full base hashes,
complete COW maps and logical comparisons before/after every guest. Primary-
channel reset still affects both ATA devices; no independent-controller claim.

Use the already qualified1MiB EXT2-1k generated layout, with direct and single-
indirect block references, existing inode/directory terminology and byte units.
The independent consumer verifies geometry, exact root entry, inode fields,
allocation references, disjoint metadata/data, full file bytes and zero padding.
This media profile admits1537..274432 external bytes (12+256 blocks), not EXT2
double-indirect access. BA's full512KiB EXT2-2k/4k/FAT evidence remains separate;
do not imply full512KiB support on this EXT2-1k package. No filesystem format is
invented or changed, and no general fsck/source-compatibility claim is made.

The signed host index keeps bounded canonical JSON, exact fields/artifact set,
strict profile identity, paths and signature checks. New profile/index names
must not overwrite or widen AZ/default packages. An attempted publication
failure leaves the previous index and every attempt intact. Publish atomically
only after independent verification of actual bytes, not producer assertions.

## Frozen acceptance

Exactly eight gates in queue order, once per frozen candidate; stop on first
failure. Gate limits300/180/180/300/2100/180/180/180s. Zero kernel builds, one
paired-media publication, no separate diagnostic guest. Pin all BA/AZ accepted
sources/tools/artifacts needed by this integration. Preserve their evidence as
prior evidence, not fresh executions. New package hosts include real signed
package corruption/publication checks and unchanged AZ/BA host regressions;
unchanged C compilation/full legacy guest suites are not repeated here.

Ten fresh BIOS cases share the one signed media pair: HDD healthy4GiB,8GiB,
long shell, A-signature fallback plus driver recovery, floppy app-hang recovery;
both HDD signatures, both CRC-valid digest failures, both manifests, floppy
signature and digest rejection. Every positive uses BA's complete unchanged
observer/semantic replay; no serial-marker substitute. Negatives require no
kernel entry and the exact original rejection counts.

Keep BA runtime300s (297s observe/3s cleanup including BOTH media), preceded by
AZ's20s BIOS/setup or30s for A-to-B fallback. Thus positives320/330s whole; five
negatives30/30/20/20/20s. Ten-guest aggregate1730s, runtime gate2100s. BIOS stops
at the actual first kernel instruction, with one bounded host acknowledgment;
start runtime origin once, before any feeder call. No renewed guest deadline,
skipped instruction, missing callback or changed CPU/ATA/IPC/service quota.

Independent full raw replay, direct source/ABI/publication/cleanup review and
frozen scope are required before done transition and clean local commit. Only
generated media under ignored build/codex-agent, no real/user disks, visible VM,
host shares, network, nested agents or push. R3.6b stays deferred. This completes
one bounded research BIOS integration, not the64-bit OS/desktop/hardware release.
