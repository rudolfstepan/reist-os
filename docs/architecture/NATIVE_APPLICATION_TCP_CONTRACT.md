# Native application TCP client v1

R8.3bn-application-tcp, defined after clean accepted UDP commit `1078fae1`.
The explicit application-network approval from22 September2026 persists.
This is one Ring3 connection/object/SDK/nc/media/recovery transaction.

## Inventory and standards

Reuse `reist_tcp_parser.c`, `reist_ipv4_parser.c`, the existing RFC826 ARP
validator and `userspace/programs/nc.c`. The legacy `drivers/net/tcp_socket.c`
has useful fixed-TCB, sequence, ACK and close behavior, but depends on i386
IRQ locks, scheduler wait queues and PIT. Do not link those dependencies into
Ring3 or add native kernel TCP. Existing syscalls101..107 stay unchanged and
unavailable to these native applications.

References: [TCP RFC9293](https://datatracker.ietf.org/doc/html/rfc9293),
[RTO RFC6298](https://www.rfc-editor.org/rfc/rfc6298), RFC791 and RFC826.
Use conventional TCP states and sequence-space arithmetic, IPv4/TCP checksum,
MSS/window bounds, cumulative ACKs, SYN/FIN sequence consumption and EOF.
Initial/minimum RTO is1000ms; use SRTT/RTTVAR, exponential backoff and Karn's
rule. Never retransmit before the current RTO. Application deadlines abort
operations independently; they do not shorten RTO or reset with retransmission.
No full RFC, POSIX, Internet security or general socket compatibility claim.

## One explicit profile and authority boundary

NativeAppTCP implies accepted NativeAppNetwork. Existing disabled profiles
and their artifacts stay unchanged. Keep separate network driver4/stack5,
foreground6, root0 and filesystem2/3. Only the driver receives device32.
Append TCP grant/request/revoke control opcodes13..15; preserve old opcodes,
SDK structures and syscall numbers. Version1 fixed grant64/request608 carries
exact root/application/service/epoch, protocol6, selected local-port base,
explicit peer192.0.2.3 and peer port. Every admission validates all fields,
padding, sequence, deadline and capacity before side effects.

The application receives two directional root IPC capabilities, no driver
endpoint, configuration, task-management, raw syscall or device authority.
Root and stack independently validate the grant. Service replacement revokes
all old objects; app fault, packet loss and peer reset must not restart a
healthy service. Preserve generation-scoped fencing/reap/self-test, exactly
two bounded service replacements, sticky network-only exhaustion and cat.

Normal command: `nc <ipv4> <port> [text]`, exact permitted peer only. Keep the
existing non-native nc behavior. Native hostnames fail closed pending DNS.
SDK open/connect/send/receive/close use explicit objects; stats are bounded
and unsupported listen/accept/ingress fail closed. This package is the active
client connection boundary, including peer-initiated close. Passive listeners
and long-lived server-port reuse require a separate lifecycle/port-retention
transaction; they are not represented as completed by this client profile.

## Finite connection and incarnation profile

Four fixed TCBs,512-byte send/segment bound,2048-byte receive ring per TCB,
one outstanding segment per connection; no heap, IRQ or scheduler dependency
in the protocol engine. Object handles are issued monotonically, never
recycled within a grant; at mostfour opens even after close. Sixty-four
application requests,6000ms grant lifetime,2000ms maximum operation, at most
200 receive turns/eight frames per turn and200 sleep increments<=10ms.
Empty receive polling is paced to100ms within the original absolute deadline.
Keep IPC100ms, frame RPC200ms, service CPU32/100ticks, foreground lifetime32,
all existing startup/health/retirement/creation/restart limits and BIOS sizes.

Use a conservative single-flight sender; respect peer MSS/window, reject
impossible ACKs and checksums, never publish duplicate bytes, advertise actual
free receive space, and abort a timed-out connection before another SEND.
Bounded in-order buffering may discard out-of-order segments with a duplicate
ACK; no unbounded reassembly or implicit application retry. Cover overlap,
wrap, zero window, peer reset, SYN/data retransmission and both close orders.

The finite research client profile assigns four never-reused ephemeral ports
to an application generation: base49152+4*(generation-1), generation1..4096.
Each issued TCB consumes one port permanently for that application identity.
The existing kernel generation counter increases across parent/service
replacement and fails closed at exhaustion. This smaller profile rejects
generations above4096; no modulo wrap or reset. Thus a retired TCP tuple cannot
be assigned to another application or service incarnation in the same boot.
Only a freshly owned QEMU peer channel may start a new boot; no physical or
persisting network channel is supported by this profile. No cryptographic ISN
or peer-authentication claim. Predictable test ISNs are not Internet-safe.

An active close enters TIME-WAIT; explicit grant revocation may abort its
remaining state under the finite supervisor horizon. The burned tuple remains
unavailable for the entire boot. This is a documented research deviation from
retaining a service for the full2MSL, not a claim of full TCP close/reuse
conformance. Passive server admission, port reuse and persistent TIME-WAIT
ownership remain separate lifecycle work. Old-tuple injection after a new
generation must be proved harmless in the guest.

## Frozen gates and execution reservation

Exactly one implementation package; no agents, push or R3.6b activation.
Allowed files are frozen in the task queue. All five gates run once per
immutable candidate, stopping at the first failure:

1. `python test/test_x86_64_application_tcp.py -v`: actual production objects,
   parser/protocol/SDK/root lifecycle O0/O2, malformed/grant/sequence/deadline/
   socket/receive capacities, retransmission timing, close and port retirement.
2. `python scripts/verify_x86_64_application_tcp.py --defaults`: exact disabled
   source/build projection, preserved UDP and earlier accepted artifacts.
3. `python scripts/verify_x86_64_application_tcp.py --package`: fresh fully
   source/tool-bound build and signed nine-file1MiB EXT2 media with nc.prg,
   independent consumer and both Windows/Make layouts.
4. `python scripts/verify_x86_64_application_tcp.py --runtime`:25 fresh guests:
   healthy4/8GiB (including UDP coexistence), wrong/foreign/stale grant and
   malformed IPC, SYN/data retransmission, peer loss, corrupt/foreign/old-tuple
   segments, receive capacity, zero window, peer reset, both close orders,
   app/stack/driver crash/hang/CPU, exhaustion and parent crash.
5. `python scripts/verify_x86_64_application_tcp.py --review`: independent raw
   task/profile/family/CPU/IPC/device/TCP-state and wire replay, exact packet
   sequence/ACK/timing, final authority/DMA/staging/frame restoration, no media
   writes, scope/ABI review and immutable source/tool/log/raw seal.

Initial development reservation:16 host commands<=600s,3 builds<=300s,
3 signed-media publications<=180s/three BIOS each,6 diagnostics<=180s.
Qualification gates1/2/3/5<=600s; gate4<=4800s including cleanup,25 guests<=180s
each/4500s aggregate. Gate3 reserves one fresh build300s/media180s/three BIOS.
Further finite evidence-directed windows are recorded before execution;
failed attempts remain spent. No diagnostic promotion or unchanged retry.
Evidence: `build/codex-agent/r83bn-application-tcp/`.
