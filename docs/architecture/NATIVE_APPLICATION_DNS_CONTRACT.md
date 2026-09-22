# Native DNS application resolver

Baseline: accepted TCP13ca2095 and DNS parser638f5269, final parser receipt
`308e7fb6ef0b1adba31f250bf34133dbee52faef10d53354529cb534c73e74be`.
The existing user approval covers UDP/TCP DNS to the owned local QEMU peer.
One active implementation transaction; no public/physical networking, new
device/DMA rights, implicit browser/script rights or persistent writes.

## One cohesive resolver lifecycle

Integrate ordinary `nslookup <name> [server]`, the existing shared SDK resolver,
its cache/deadline corrections, an opt-in NativeAppDNS profile, signed media
and complete failure recovery. NativeAppDNS implies NativeAppTCP; disabling
the new profile preserves all previously accepted native profile behavior.
The shared resolver corrections intentionally also apply to legacy callers;
its public declarations/syscall numbers stay unchanged.

DNS parsing stays in the application. Root validates bounded command operands
and grants; it does not parse DNS packets. Stack5 and driver4 remain separate
Ring3 services, application6 has only the accepted two directional IPC caps
and existing ordinary program mask. App lifetime32 ticks and service/root
32/100-tick quotas, creation/restart limits and all image ceilings stay fixed.

### Fixed destination and paired transport grant

The selected server is192.0.2.3, port53, defaulting to that explicitly approved
local peer when omitted. Other servers fail before traffic/cache publication.
Only the DNS executable receives a paired UDP17/TCP6 grant. A resolved address
is data, never a new network capability. No resolver recursion or referrals.

Append internal control16 DNS_GRANT and17 DNS_REVOKE; old1..15 unchanged.
DNS_GRANT carries the existing64-byte grant with protocol17; the service
derives the identical TCP grant with protocol6. Both share exact root/app/
service generations, epoch, peer, port and absolute expiry. Grant both before
acknowledging; partial admission revokes both and fails closed. Direct foreign
grants cannot coexist with the pair. Existing request11/14 select the protocol;
the service validates its respective complete grant on every operation.
Successful RELEASE on either protocol invalidates both before ACK. Root
closes publication on faults, obtains revoke or fences the service group,
then cancels/reaps. Keep successful RELEASE ACK endpoint until child reap.

Root exposes one total64-request sequence, translates it to separate bounded
service UDP/TCP sequences and restores the public sequence in replies. Changing
the protocol alone never changes the grant's other fields. Root starts a fresh
bounded service group for each DNS application to avoid epoch ambiguity with
separately issued ordinary UDP/TCP grants; this planned retirement does not
consume automatic restart budget. Subsequent genuine failures retain the
existing two-replacement/sticky-exhaustion policy. Full fencing is still proven.

Retain four UDP objects/four TCP TCBs,512-byte datagrams/segments,2048-byte TCP
ring,6s grant lifetime,2s maximum object operation,100ms IPC and existing
packet/ARP/retransmission limits. TCP ports use accepted boot-unique generation
leases. Native UDP bind0 selects that exact preallocated local port. It grants
no choice of another port. No socket handle survives release or generation.

### Resolver transaction and cache

Use RFC1035 A/IN, CNAME, compression and2-byte DNS-over-TCP framing, RFC5452
question/tuple validation and RFC2181 TTL rules, retaining the accepted pure
parser. The research profile remains512-byte DNS, at most64 RRs/eight CNAMEs/
eight compression pointers; no EDNS, DNSSEC or Internet spoof-resistance claim.

Resolution has one original caller deadline (nslookup3000ms); bound UDP send
and receive by remaining time and existing<=2000ms caps. One TCP fallback,
connect/send/receive bounded by original remaining time, TCP connect<=1500ms.
Partial writes/reads make bounded positive byte progress. Closing may use the
existing separately bounded<=1000ms cleanup window, always within the native
6s grant; cleanup never publishes a late successful resolution or renews its
deadline. Every clock read detects regression; invalidate cache on regression.

Cache has four process-local entries keyed by validated normalized query AND
selected server. Cache stores the terminal canonical name and remaining TTL;
TTL0 is never cached, expiry uses actual successful-response time and checked
addition. Validate all call operands/server before looking in cache. Failed,
late, malformed or mismatched results never modify caller output or cache.
Native process generation bounds cache lifetime; it is never shared across
replacement applications or granted to other consumers.

### Delivery

Normal Ring3 shell dispatch resolves packaged `/nslookup.prg`; both Windows
and Make builds include it. A distinct signed ten-file1MiB EXT2 profile extends
the accepted nine-file layout:21 allocated/11 free inodes, ten bounded files,
existing boot trust chain and independent media consumer. No old index/layout
mutation. Preserve independent cat/ls/probe artifacts and TCP/UDP tools.

## Frozen gates and finite reservations

Initial16 development host commands<=600s,3 profile builds<=300s,3 signed
media publications<=180s/9 BIOS assemblies and6 diagnostics<=180s. Reserve
each operation before execution, preserve all failures. No unchanged retries.

Five candidate gates: host600s, defaults600s, fresh bound build/media600s,
runtime4800s and independent final review600s. Fresh runtime25 guests<=180s
each/4500s aggregate, sequential, stop first failure. Cases:
healthy4g, healthy8g, cname, truncated, udp-loss, wrong-question,
bad-compression, peer-loss, tcp-fragmented, frame-limit,
wrong-grant, foreign-owner, stale-grant, malformed-ipc,
app-crash, app-hang, app-cpu, stack-crash, stack-hang, stack-cpu,
driver-crash, driver-hang, driver-cpu, exhaustion, parent-crash.

Healthy guests also prove ordinary TCP/UDP coexistence. Every failure case
proves independent cat and exact generation-scoped cleanup; recovered cases
prove a fresh successful DNS app. Raw task/profile/family/CPU/IPC/device/DMA,
paired grant/sequence/packet/result evidence, exact free-frame restoration,
real old grant identities and immutable source/tool/media binding are required.
Serial text and source-pattern checks alone never establish runtime acceptance.
Host tests execute actual resolver, paired grant/root translation and adapters,
including cache/server/TTL/deadline and malformed IPC fault injection at O0/O2.

One accepted package/local commit is a verification boundary, then continue
the next in-priority native64 inventory. Passive server lifecycle and further
system integration remain open; R3.6b stays explicitly deferred. No push or
nested agents, and no complete native64 claim from this DNS package alone.
