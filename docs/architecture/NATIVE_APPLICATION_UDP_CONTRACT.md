# Native application UDP v1

R8.3bm-application-udp, frozen on the clean implementation baseline `da228540`
after the user's explicit application-network approval on 22 September2026.
The approval record and this package definition precede candidate source edits.

## One implementation transaction

Deliver an explicit NativeAppNetwork profile extending NativeNetworkSession:
bounded UDP objects, production parser reuse, Ring3 stack transport, native SDK,
ordinary `/udp.prg` invocation, signed immutable media and fault containment.
Both PowerShell and Make builds select the same profile. Disabled profiles,
including accepted BL, retain their existing source/build projections.

Use RFC768 UDP, RFC791 IPv4, RFC826 ARP and Ethernet network byte order.
Reuse `reist_udp_parser.c` and `reist_ipv4_parser.c`; adapt the fixed-capacity
socket model from `drivers/net/net_socket.c` without its i386 IRQ, scheduler,
PIT or lock dependencies. All packet parsing, queues and policy remain Ring3.
Existing syscall numbers97..107 remain unchanged and unsupported native raw
socket syscalls fail closed. The SDK uses explicit IPC objects instead.

## Authority and bounds

The root issues a version1 grant after explicit command operand validation:
exact root identity, application identity, stack identity, monotonically
increasing grant epoch, UDP protocol17, local port, peer IPv4 address and port,
and absolute expiration. Only the existing QEMU peer is admissible. The app
receives two directional root IPC capabilities, never a driver/frame endpoint,
configuration, lifecycle, device or delegation capability. Root checks the
actual endpoint peer; stack independently checks the complete grant on every
forwarded operation. A path or handle alone is insufficient authority.

Native command grammar: `udp send <ip> <port> <local-port> <text>` and
`udp recv <ip> <port> <local-port> [timeout-ms]`. The explicit receive-peer
operands are a documented native adapter restriction. Preserve the old i386
receive grammar. Reject missing, overflowing and disallowed operands before
grant publication or packet output. Append only the two private IPC arguments,
within the existing eight-argument startup limit; remove them before main.

Eight sockets, four queued datagrams per socket,512-byte payload maximum.
Fixed storage, no queue overwrite. One foreground grant, at most64 requests
and6000ms total after publication; individual packet operations at most2000ms.
The original absolute deadline survives SDK/root/stack forwarding. A pending
operation uses bounded polling/sleep and100ms IPC calls; it never extends a
kernel IPC timeout past1000ms. At most200 receive turns/eight frames per turn.
Keep all existing CPU32/1000ms, device IO128/100ms, frame RPC200ms,
startup3000ms, health1000ms, retirement5000ms and restart limits.

Implementation clarification: foreground applications retain the existing
stricter lifetime32-tick CPU budget; periodic32/100-tick windows apply to the
network services. The raw reviewer distinguishes both existing contracts.
When adapting the existing relative ARP timeout, clamp every frame callback
to the original absolute UDP deadline; a later clock sample cannot renew it.

Slot0 root,1 baseline peer,2/3 filesystem,4/5 network services,6 foreground;
no task-pool expansion. Root captures the executable before launching the
network group, preserving fixed image and filesystem deadlines. Foreground
revocation precedes group retirement; no unrelated file capture may retire
an active granted application silently. Cleanup is generation-scoped and
idempotent, scrubs queues and closes both application capabilities. Parent
loss uses the existing kernel fence/cleanup. Service replacement invalidates
all grants; self-test plus fresh explicit delegation is required for reuse.
Application timeout/crash/quota must not consume a service restart if the
service remains healthy. Exhausted network recovery permits independent cat.

UDP itself carries no application-generation token. Grant/handle replay and
late local operations must fail; do not claim wire-level anti-replay or peer
authentication from a UDP source tuple. No proprietary payload envelope or
untested full RFC/POSIX compatibility claim. No TCP/DNS implementation in this
transaction, public Internet, physical NIC, new device rights, GUI combination,
writes, SMP, nested agent, push or activation of deferred R3.6b.

## Frozen acceptance and finite execution

Five gates, once per immutable candidate, stop at first failure:

1. `python test/test_x86_64_application_udp.py -v`: production C behavior at
   O0/O2; grant/owner/epoch/sequence/deadline/padding mutations, request quota,
   socket/queue capacity, close/revoke/reuse, production IPv4/UDP corruption,
   command resolution and native SDK transport including negative outcomes.
2. `python scripts/verify_x86_64_application_udp.py --defaults`: exact disabled
   build/source projections and accepted reference artifacts.
3. `python scripts/verify_x86_64_application_udp.py --package`: separately
   named signed eight-file1MiB EXT2 profile including udp.prg; independent
   consumer, both image layouts and actual immutable file reads. Kernel image
   and BIOS limits unchanged; metadata-only existing compaction if required.
4. `python scripts/verify_x86_64_application_udp.py --runtime`: twenty fresh
   guests: healthy4/8GiB send/receive; missing/wrong destination grant; foreign
   owner; stale epoch/handle; malformed IPC; lost peer; corrupt/foreign packets;
   full receive queue; application crash/hang/CPU; stack crash/hang/CPU; driver
   crash/hang/CPU; restart exhaustion; parent crash. Each case180s maximum,
   total3600s. Compound cases share one physical guest only when their exact
   expected observations are independently proved.
5. `python scripts/verify_x86_64_application_udp.py --review`: independent raw
   task/profile/family/CPU-window/IPC/device/packet review, signed inputs,
   exact owners, fence before root CANCEL/WAIT, zero final authority/staging,
   no media writes and all frames restored. Scope and ABI review; immutable
   source/tool/command/log/raw-bound seal. No serial-only runtime claims.

Initial development reservation: twelve host commands600s each, three
builds300s each, three media publications180s each (three BIOS assemblies per
publication), six diagnostic guests180s each. Qualification host/defaults/
package/review each600s; runtime3900s including owned cleanup. Record each
attempt before execution and its result after; preserve all failures. Further
evidence-directed finite windows require a recorded scope/evidence review,
not another routine permission question. No unchanged retry-until-green.
Logs and counters: `build/codex-agent/r83bm-application-udp/`.

## Accepted implementation

Candidate04 on implementation baseline35bfdcf2 passes all five gates and all
20 fresh guests. Seal9da4534ae5acaf5112a45529b45d2f7e2664b300104b01229229302262b31bbc
binds sources, tools, signed media, raw evidence and independent replay.
Development captures and earlier failed candidates are retained separately;
none substitutes for the final fresh matrix. No whole-OS completion claim.
