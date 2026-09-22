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

## Candidate01 development inventory

Sixteen development host commands are spent (host13 is the independent
diagnostic02 replay). Host16 passed all eight groups in11.176s, including
O0/O2 production objects, protocol, SDK and root release/fencing, disabled
projection and rehashed raw-evidence mutation rejection. Earlier failures
remain recorded: fixture ACK ordering, partial-ACK RTO restart, zero-window
ACK, Ethernet zero padding in replay, and acceptable empty-segment sequence.

Three builds are spent. Build01 exceeded the unchanged admitted image by
268bytes. Only this profile moves the2056-byte synchronous IPC buffer into
fixed call-stack storage; it never retains the pointer. Build02/03 pass,
latest21.294s. Compiler stack records report3960bytes for the largest single
frame and2088 for receive transport; these are per-function sizes, not a
claim of complete call-chain or hardware qualification. The fixed32KiB user
stack and image admission limits remain unchanged.

One signed nine-file1MiB medium publication and its three BIOS assemblies
passed3.272s. Two diagnostic guests are spent:42.970s TCP only and83.475s
TCP plus accepted UDP commands, both followed by independent cat and full
cohort cleanup. Neither diagnostic is promoted to acceptance. Candidate01
still executes all five frozen gates, a fresh bound build/media,25 fresh
guests and independent raw replay. No TCP acceptance or native64 completion
is claimed here. The initial development host/build reservations are fully
spent; further development needs an evidence-directed finite window.

## Candidate01 result and correction window

Candidate01 gates1/2/3 passed10.951/1.996/31.351s. Four guests passed raw
review; the fifth, stale-grant, completed its dialogue but failed replay:
the retired handle returns-9 while its deliberately retained TCB remains in
TIME_WAIT. The reviewer incorrectly required CLOSED for every error,
conflating failed handle admission with an admitted wire-operation failure.
Preserve all five guests, the fresh build/media and the failed gate.

Reserve four additional host commands<=600s (cumulative20), no additional
development builds or media, for exact retired-handle replay regression and
review correction. Candidate02 must run the unchanged five gates afresh,
including one fresh bound build/media/three BIOS and25 guests<=180s each,
4500s aggregate/4800s gate4. No candidate01 guest is promoted. Existing
development totals stay16 hosts/3 builds/1 media/2 diagnostic guests; the
initial unspent diagnostic/media slots are not reset or repurposed.

Host17 passes all nine groups in14.694s. Actual stale-grant raw records show
SEND and subsequent CLOSE return-9 with TCB(handle=0,state=TIME_WAIT8).
The corrected reviewer requires no handle authority; admitted wire failures
still require CLOSED and a scrubbed receive ring. Candidate01 gate4 consumed
299.404s. No production/runtime source or acceptance requirement changed in
this correction; cumulative development host count17, qualification guests5.

## Candidate02 result and output correction window

Candidate02 gates1/2/3 passed13.130/2.180/35.830s. Ten guests passed raw
review, including SYN/data retransmission and peer loss without restarts.
The eleventh, receive-capacity, proved the exact2048-byte ring and512-byte
read but both nc applications hit the unchanged32-tick lifetime CPU limit
while writing the response one character/syscall at a time. Preserve both
real quota terminations and the stopped candidate; do not weaken the quota.

Inventory the existing bounded console buffering and add a fixed64-byte
TCP SDK output buffer with partial-write, deadline and output-cap handling.
Use the three remaining host slots18..20 of the existing cumulative20 limit.
Reserve one additional development build04<=300s (cumulative4), one media02
publication<=180s/three BIOS (cumulative2/six BIOS), and diagnostic03 for
receive-capacity plus diagnostic04 for app-cpu, each<=180s (cumulative4).
Candidate03 then runs all five unchanged gates afresh with a new bound
build/media/three BIOS and25 fresh guests180s/4500s aggregate, gate4<=4800s.
Cumulative qualification guests16 (5+11); no previous guest is promoted.

Host18 reproduced single-byte writes; host19 passed13.069s after fixed64-byte
batching, preserving100 write attempts,1024-byte output cap and the original
absolute application deadline. No new console ABI or CPU budget. Build04
passed24.403s; media02 passed3.845s. Diagnostic03 receive-capacity passed
48.208s with app CPU6/9 ticks, exact four-segment2048-byte ring and rejected
fifth segment; diagnostic04 app-cpu passed46.472s, including real32-tick
termination and unrelated healthy progress. Host20 passed all ten groups in
13.686s, including independent replays of both diagnostics and retained
candidate02 quota-failure receipts. Candidate02 gate4 consumed614.087s.
Cumulative development20 hosts/4 builds/2 media/six BIOS/4 diagnostics.

## Candidate03 root-console diagnostic window

Candidate03 passed gates1..3 and nine guests. The tenth, bad-segments,
stopped before TCP: root0 reached its actual32/100-tick quota at RIP4126b1
in session_now while the ifconfig line was being entered. The kernel fenced
the old service group, restarted root and completed unrelated cat; missing
configuration/TCP progress correctly fails the gate. Preserve this root quota
failure and all26 cumulative qualification guests (5+11+10).

Freeze diagnostic05<=180s: capture root user stack at termination and repeat
the existing configured-console path eight times before the ordinary TCP
dialogue. This is diagnosis of clock/poll/output work, not acceptance or an
unchanged retry. No production correction is inferred from a passing rerun.
Reserve four hosts21..24<=600s (cumulative24), one further development
build05<=300s (cumulative5), media03<=180s/three BIOS (cumulative3/nine BIOS),
and diagnostic06<=180s for an evidence-directed correction proof. Kernel,
profile quotas, all frozen acceptance commands/requirements remain unchanged.

Diagnostic05 reproduces the root quota failure36.436s while typing the second
ifconfig; raw user stack identifies x86os_getchar_nonblocking/read_shell_input,
RIP41285a immediately after READ15. Host21 reproduces redundant per-byte
clock/health work. TCP-only coalescing retains single-byte reads, unchanged
health deadlines and byte quotas; private output buffering validates at the
existing <=64-byte flush before publication. Host22 passes16.726s.

Build05 is retained. Direct review removes an unnecessary extra idle clock
read from that first correction: after the existing poll, use its already
validated session-policy timestamp. Reserve build06<=300s (cumulative6),
using existing unspent media03/diagnostic06 and host23/24 slots. This is a
changed correction, not a retry of build05. No deadline or quota is increased.

Build06 passed27.606s and media03 passed3.857s. Diagnostic06 still reaches the
root CPU quota while typing the third ifconfig. Coalescing redundant clock
work is insufficient: the empty-input caller sleeps10ms, allowing a wake on
every10ms accounting tick. Preserve this second diagnostic failure.

The next correction only paces the shell's next10ms sleep after an observed
empty terminal read to50ms, within the existing100ms sleep bound. Consume the
hint once; other sleeps, nonempty input, IPC deadlines,400ms health checks and
32/100-tick quota stay unchanged. No input prefetch or terminal-owner change.
Use existing host24 for a failing regression and reserve hosts25..28<=600s
(cumulative28), build07<=300s, media04<=180s/three BIOS and diagnostic07
root-console<=180s. Cumulative ceilings7 builds/4 media/12 BIOS/7 diagnostics.
After its proof, candidate04 reserves the unchanged five gates, fresh
build/media/three BIOS and25 guests180s/4500s aggregate, gate4<=4800s.

Diagnostic07 passed all eight console configuration cycles, then root hit
the unchanged CPU quota in reist_net_receive during TCP CONNECT (88.940s).
The root TCP result wait still uses nonblocking IPC plus1ms sleeps; its
application wait has the same polling pattern. Preserve this failure.
Replace these TCP-only waits with blocking IPC bounded by100ms, the original
absolute operation/grant deadline and existing health expiry. Preserve the
100ms result grace, terminal transport fencing and release-before-reap order.
Use hosts26..28 already reserved; reserve build08<=300s, media05<=180s/three
BIOS and diagnostic08 root-console<=180s. Cumulative ceilings8 builds,
5 media/15 BIOS/8 diagnostics. Candidate04 remains unspent; no gate changes.

Host26 reproduced nonblocking root application IPC; host27 passes all twelve
behavior groups12.606s with blocking root receives and absolute deadline,
health expiry, broken-channel and release-order checks. Build08 passed21.025s,
media05 passed2.975s. Diagnostic08 root-console passed68.579s: all eight
configurations, two ordinary TCP applications, unrelated cat and full raw
resource review. Preserve all three failed root diagnostics. Candidate04
binds these records and adds their replay as the thirteenth host group.
Spent development totals27 hosts/8 builds/5 media/15 BIOS/8 diagnostics;
qualification26 guests across three failed candidates. Candidate04 starts
all five unchanged gates and25 fresh guests; no diagnostic is acceptance.

## Candidate04 service-generation review correction

Gates1..3 passed13.115/2.039/32.770s; gate4 stopped931.041s at stack-hang
after18 accepted cases. Its guest dialogue passed but raw review counted all
slot5 cancellation receipts(0,3), including deliberate healthy group retirements,
as injected hangs. The actual selected second slot5 generation14 was cancelled
while handling TCP CONNECT; ordinary generations10/19/28 were retired from
CONFIGURE. All other fencing, resource and restart requirements stay frozen.
Reuse the accepted UDP review's exact selected-generation binding, retaining
global crash/CPU counts where those statuses are unambiguous. Regress against
this real raw capture and a rehashed wrong-operation mutation. No production
or kernel change. Use remaining host28 for red; reserve hosts29..30<=600s.
Candidate05 reserves the unchanged five gates, fresh build<=300s, media<=180s/
three BIOS and25 fresh guests180s/4500s aggregate, gate4<=4800s. Development
build/media/diagnostic counts stay8/5/8; qualification guests45 (26+19).

Host28 reproduced the ambiguous cancellation count; host29 passes all fourteen
groups15.716s. The exact generation14 raw capture now passes, and a rehashed
mutation replacing its pending CONNECT with OPEN is rejected. Ordinary group
cancellations remain fully covered by fencing/cleanup review; unambiguous
crash/CPU counts and exact restart budgets are unchanged. Candidate05 binds
this raw regression and starts with cumulative29 development host runs.

## Accepted candidate05

All five gates passed14.549/1.980/33.297/1261.927/9.090s; all25 fresh guests
and independent raw replay passed. Seal SHA256:
`9494fa7fc4349ab17cb8b1e7f63c3edb02deb5ebecf772e46b48374be5524f9f`.
Counters:29 development hosts,8 builds,5 media/15 BIOS,8 diagnostics;
70 qualification guests over5 candidates,5 fresh qualification builds/media.
All previous failures remain. This accepts the explicit active TCP client
profile only; passive server lifecycle, DNS and complete native64 remain open.
The only queued legacy package R3.6b stays explicitly deferred. Clear active_id
for the clean transaction boundary, then inventory the next native package.

## Candidate05 commit-boundary correction

Allfive gates/25 guests passed, but git diff --cached --check stopped before
commit: one trailing space in the new host-test C prefix at line172. Earlier
git diff --check omitted untracked paths. Preserve the acceptance evidence and
scope reviews; no commit occurred. Remove only that space and extend freeze
with Git's full-file whitespace check for each untracked source. The test
AST/C behavior and every production byte remain unchanged. This is a tooling
correction, not a runtime failure. Return queue to active pending a fresh
candidate06 with the same five gates, bound build300s/media180s/three BIOS
and25 fresh guests180s/4500s aggregate/gate4<=4800s. No development guest,
build, media or host reservation is consumed. Qualification70 guests remain.

Candidate06 first freeze rejected Git's informational LF-to-CRLF warning,
before any gate or candidate directory. The new-file check now disables only
safecrlf warnings for this read-only diff; whitespace error checking stays
unchanged. Retain candidate06-freeze.log; corrected admission uses a new log.

## Accepted candidate06 final boundary

Allfive gates passed18.361/2.022/37.174/1482.443/7.681s; all25 fresh guests and independent
raw review pass. Seal SHA256 `6257b22f954e8c1bf583c9dc56e79c4b633506f05a72f8c59021324b63350336`.
Cumulative95 qualification guests/six builds/media; development29 hosts/8
builds/5 media/8 diagnostics unchanged. The full new-file whitespace check
also passes. Candidate05 remains valid historical runtime evidence but was
not committed. Candidate06 is the final accepted source/tool binding.
