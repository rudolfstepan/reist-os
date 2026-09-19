# Native two-stage immutable file capture — R8.3aw

Frozen on accepted f05fcc86dfd5f8e6b61b911a349230c5a68c7b29, 19 September2026.
One interactive transaction, no agents/push. R3.6b stays deferred.

## Inventory and boundary

The normal shell performs STAT before SPAWNV. The existing file-image adapter
requires client.sequence==0 and performs its own STAT, so it cannot consume
that preceding lookup within the existing eight-request session. The native
FS already supports stat/read/readdir, exact generation and sequence matching,
fixed storage, immutable media and absolute deadlines. Do not add a second FS
protocol, reset counters, silently restart services or enlarge a quota.

This package owns the single file-capture publication/rollback boundary:
expose its existing STAT and read/EOF/ELF stages as reusable SDK entrypoints,
sharing one absolute deadline and the exact owner/sequence. Keep the old fresh
client entrypoint and its observable errors, untouched outputs, workspace
scrubbing and eight-RPC bound. The existing live-file/terminal fixture calls
that wrapper and therefore executes both new stages in the real guest.
Namespace policy, SPAWNV/wait/identity adapters and normal shell composition
follow as one integration package; they are not claimed here.

References remain the existing System V AMD64 ELF64 adapter and native FS
RPC-v1 using VFS STAT5/READ6 payloads and negative errno-compatible results.
The explicitly REIST-specific capture observation is a fixed version1
552-byte structure: version/size, owner, sequence, absolute deadline_ms,
observed_ms, and the existing512-byte validated STAT frame. This Ring3 value
is not a capability, kernel attestation or new source of authority. The full
file/EOF/ELF admission and kernel image validation remain mandatory.

## Invariants

STAT publishes an observation only after a complete matched FS response and
monotonic deadline check. A used but unpoisoned FS client is allowed; at most
eight total FS requests per generation. Reject exhausted capacity before a
new request. Never retry or rebind internally.

Finish validates complete object extents/non-overlap, version/size/canonical
STAT frame, exact owner and current sequence, file kind/size and enough
remaining requests for all data plus EOF before effects. Reject a used/stale
observation and time regression; the original absolute deadline cannot be
renewed by separating the stages. Maximum file1536 bytes, reads256, fixed
workspace. Error never publishes a prepared image. Scrub admitted workspace
on every completion/failure; pre-admission errors leave all objects intact.
Consume actual sequence progress, require exact read lengths and empty EOF,
validate ELF and recheck identity/deadline immediately before single publication.

The old entrypoint still rejects any nonfresh client and preserves its
existing regression outcomes. No kernel, service, parser, shell, ABI number,
producer selector, console grant, CPU32/1000ms, FS8, block16, session/IPC/ATA
deadline or prior default behavior changes. No new shell command.

## Frozen qualification

Regression first: actual C/FS/block/media/ELF code at O0/O2 on all five media,
successful split capture, interleaved requests, stale generations, exhausted
capacity, malformed observation/clock/replies, exact single publication,
all overlap/scrub paths and unchanged old-wrapper cases. Actual state, not
source patterns alone. Existing file-image, live-file and terminal hosts once.

One NativeTerminal image; reuse the unmodified complete25-case terminal/live
file observer and oracle, all25 fresh guests45s including cleanup<=3s,1125s
total/1200s matrix. Exact kernel object and file-child equality to accepted AV
binds reuse of its two physical-corruption proofs; no new fatal guests needed
for this Ring3-only SDK change. Independent binary memory equality, original
CPU/PIO/IPC/frame/generation/cleanup predicates and reference artifacts remain.
Ten queue gates, first failure stops; no unchanged retry. Host gates300s,
other gates180s except matrix1200s. Preserve every failure and spent count;
standing authority permits only separately frozen evidence-directed windows.
Freeze source/tool/command/scope hashes before gates, review the complete raw
matrix and diff, then documentation-only queue closure and clean local commit.

## Preserved freestanding link stop

Candidate01 passes gates1..5 (40 host methods). Its first build invocation
fails before a complete OS image: the new canonical STAT-info assignment is
lowered by freestanding Oz compilation to an unresolved memcpy. Stop58ad4de9
and all sources/logs remain. Candidate02 replaces only that assignment with
existing bounded file_copy and adds an actual nostdlib/no-undefined link test
before the corrected build. Same ten gates and unchanged25-case raw oracle,
zero previous guests; one corrected image, at most two cumulative build
invocations. No libc, new dependency, weaker assertion or quota change.

## Completed qualification — 19 September2026

Candidate02 passes all ten obligations:41 host methods, including actual
O0/O2 media/FS/block/ELF cases and the freestanding no-implicit-libc link.
All25 fresh guest cases pass in468.5106607999187s. Exact allocated kernel
sections/objects/symbols and unchanged driver, FS and child images bind reuse
and replay of AV's two physical-fence/corruption proofs. One completed image
2042f4de5287201ef4b8596906ac8820033a5ff1291ae255b78d2d8cb63ae571; two build
invocations including the retained failed link, no guest retries.
Review751cd640f8903331b5d9055afe44044aca038c9bd8d2ce9e660d6785907e147d
seals2928 files. Documentation-only closure and the clean local implementation
commit are bound by `build/codex-agent/r83aw-file-capture/candidate02/verification-status-file-capture-final.json`.
This qualifies the shared file-capture boundary, not normal-shell namespace,
spawn/wait integration, persistent sessions, complete OS or physical hardware.
