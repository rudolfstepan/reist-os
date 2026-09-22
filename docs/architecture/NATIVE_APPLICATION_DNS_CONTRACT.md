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

## Development inventory and image correction

Host01 reproduced cache lookup before invalid-server rejection. Host02 caught
a private/public function-signature edit error; host03 passed after restoring
the public API. Host04 caught disabled host assertions in the toolchain;
host05 uses -UNDEBUG and passes O0/O2 resolver, accepted parser and paired
authority tests, including rollback after partial grant admission. Five of
sixteen host slots spent; no guest/media evidence yet.

Build01 failed18.428s at the unchanged root image ceiling: text0xd286 pushes
rodata/data one page later, final0x440940 exceeds0x440000 by2368 bytes. DNS app
and network roles compiled. Preserve the failed map and all objects.
Use existing build02 reservation for root-only LLVM link-time optimization
(-flto, lld --lto-O2), restoring compiler/linker vectors before independent
roles. This removes cross-unit duplication within existing permissions and
image limits; it adds no parser, dynamic storage or runtime authority. Old
profiles remain exact; role/media pin checks and raw observer-symbol validation
remain required. No guest is admitted until the new image and media validate.

## Scope stop: UDP response lost during repeated ARP

Build02 passed22.892s; media01 passed3.284s, including independent signed
consumer and unchanged ordinary-program pins. Build03 passed23.009s after
the DNS network-status ABI fields and four-live-UDP-object admission fix.
Root LTO retains all required observer symbols; network_blocked is a one-byte
optimized object, so observers must use its map extent rather than assume4.

Host06 reproduced missing network-status version/size; host07 passed after
correction. Host08 added four-object denial/reuse and independent media
corruption checks; host09 added actual root mixed-protocol sequence and
release/ACK/reap ordering. Host10 passed seven groups, including the peer
query bounds. Host11 adds the actual UDP FIFO regression below: seven groups
pass and the new transport regression fails at O0 before its O2 execution.
Eleven of sixteen development host reservations and all three initial build
reservations are spent; failed receipts are retained.

Diagnostic01 failed78.099s in observer tcp_enter on an unmapped DNS marker
address in the ordinary UDP image. Diagnostic02 passed capture78.517s after
classifying ordinary UDP/TCP before reading the DNS marker. Diagnostic03
passed capture66.807s for the truncated-response dialogue. Three of six
diagnostic reservations spent, one of three media publications spent, zero
qualification candidates/gates. These captures remain qualified=false.

Independent inspection of diagnostic02 reveals both successful DNS lookups
used TCP after UDP RECEIVE returned -110: UDP response length512/result-110,
followed by TCP OPEN/CONNECT/query/receive/close/release. The owned peer had
sent the valid DNS datagram immediately after UDP SEND. The subsequent
RECEIVE unconditionally resolves ARP again in application_udp_protocol.c;
network_protocol.c discards the earlier queued non-ARP response while waiting
for that new ARP response. Therefore neither healthy UDP nor TC-triggered
fallback is established by the serial successes in diagnostic02/03.

Host11 executes the existing actual UDP protocol fixture with FIFO delivery:
the datagram queued by SEND is delivered before the later ARP reply. The old
fixture gave ARP unconditional priority. Actual reist_app_udp_exchange now
reproduces the same unexpected timeout; no production workaround is applied.

Required additional production scope:
`userspace/sdk/lib/x86_64/application_udp_protocol.c`, currently NOT allowed.
Proposed correction: retain at most four bounded candidate datagrams while
the existing ARP exchange runs, then validate them against the resolved MAC,
existing grant/IP/port/checksum rules and original deadline before enqueueing.
Reuse the existing UDP parser and fixed queue; preserve all public layouts,
request counters, packet/ARP limits and Ring3 ownership. Cover FIFO delivery,
foreign/malformed packets, overflow, deadlines and revocation in host tests
and fresh DNS guests. Do not simulate away the fault by delaying peer replies
or force TCP-only success. Review stack capacity before admitting staging.

AGENTS.md requires stopping when a needed production file lies outside the
frozen allowed_files. Leave this one package active, all edits and raw evidence
visible, and no implementation commit or queue advance. The next transaction
must explicitly freeze the reviewed scope addition and finite correction/build
reservation; acceptance gates and authority remain unchanged.

## Explicit continuation after scope report

The user renewed completion after the scope-stop report. Add exactly
userspace/sdk/lib/x86_64/application_udp_protocol.c to this same active
package; all previous edits match scope-stop.json and remain attributable.
Freeze correction window: development hosts12..16 from the original budget,
additional builds04..05 <=300s each, remaining media02..03 <=180s each and
remaining diagnostics04..06 <=180s each. Preserve spent counters and all
receipts. Existing five acceptance gates and25 fresh qualification guests
remain unchanged. No new authority, persistent format or public ABI.
Stage at most four candidate frames of554 bytes in the bounded receive
operation, only while ARP is resolving; validate after the actual MAC reply.
Check the complete service call-chain stack against its existing8KiB stack
before a new guest. This is a continuation of the visible active candidate,
not a new implementation package or clean-worktree claim.
