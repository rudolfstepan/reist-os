# Native application network authority — approved, implementation pending

## Explicit user approval, 22 September2026

The user answered the proposal from commit `da228540` with
"Ja, begrenzte Anwendungs-Netzwerkrechte freigeben". This authorizes the
destination- and generation-bound UDP/TCP application objects described below
within the existing local QEMU test network. The approval persists across UDP,
TCP and DNS implementation transactions; routine package or diagnostic
boundaries do not require another permission request. Runtime implementation
and acceptance remain separate from this authority decision.

The original proposal and pre-approval inventory follow as historical context.

22 September2026, inventory after accepted local commit `a4c8bc96`.
R8.3bl passed five gates and fourteen fresh guests; acceptance seal
`9aa0bc11dd15e8aca40c6e2fb267117933f9b6d4d4edcb684111553dfcf65f03`.
This proposal does not activate another implementation package.

## Existing boundary

- NativeNetworkSession grants the shell root control of its two network
  children. Only the driver receives device32; the protocol stack has no
  device or DMA mapping authority. Foreground application profiles have no
  network-service endpoint or socket object grant.
- The accepted private control protocol carries status, configuration, ARP
  and ICMP. It has no application socket object or destination grant.
  See `userspace/sdk/lib/x86_64/shell_network.inc` and
  `userspace/sdk/include/reist/x86_64/network_session.h`.
- Existing public UDP97..100/TCP101..107 syscall numbers and SDK declarations
  describe the i386 implementation. There are no corresponding native socket
  dispatch paths in `arch/x86_64/proc`. Reusing those numbers cannot create
  native object ownership or delegation.
- `userspace/programs/udp.c` is an existing normal application consumer.
  The existing UDP model uses eight objects, four queued datagrams per object
  and512-byte payloads (`drivers/net/net_socket.h`). The packet parsers in
  `userspace/sdk/reist_udp_parser.c` and `reist_tcp_parser.c` are reusable.
- The socket implementations in `drivers/net/net_socket.c` and `tcp_socket.c`
  depend on i386 interrupts, scheduler wait queues, PIT and spinlocks. They
  cannot be linked into native Ring3 unchanged or copied into Ring0 as a
  migration shortcut. The bounded protocol/state logic must be adapted to
  the existing Ring3 transport and monotonic deadlines.

## Requested authority decision

Permit a separately versioned native application network profile: the shell
may grant an exact foreground generation a bounded UDP/TCP socket object for
an explicitly selected protocol, local port and destination address/port.
The network service validates the complete grant on every operation. A socket
handle, executable name or syscall mask alone grants no network access.

Keep all traffic within the already authorized QEMU loopback peer setup.
No public Internet, arbitrary destination, physical NIC, extra DMA/MMIO/PIO
authority, persistent write, SMP or implicit browser/script access follows.
Applications receive no driver endpoint and no ability to change interface
configuration, route policy, service lifecycle or another object's owner.

Objects carry application and service generations. Application exit/crash,
service failure, cancellation and revocation invalidate old handles before
reuse. Old application grants cannot revive after service replacement; fresh
explicit delegation and self-test are required. Queue, payload, operation,
retry and restart capacities remain fixed and separately verified.

## Implementation sequence after authorization

1. Inventory and freeze one cohesive UDP object/transport/application slice:
   RFC768/IPv4 parsing, existing512-byte datagram envelope, bounded IPC object
   grants, SDK adapter and ordinary `udp.prg` dispatch in both image layouts.
   Preserve existing public ABI numbers and fail unsupported old paths closed.
2. Host tests execute production parsing and grant/lifecycle code. Real guests
   prove send/receive, wrong/foreign/stale grants, peer loss, full queues,
   application/service crash/hang/quota, restart exhaustion and independent
   shell/file progress. Raw task/profile/device/packet evidence is mandatory.
3. Stateful TCP and DNS consumers follow in separately frozen cohesive
   transactions under the same explicit destination/object authority; freeze
   their own finite connection/retry/close budgets before implementation.
   Do not claim POSIX or full protocol compatibility without evidence.

`AGENTS.md` requires a stop for a new authority domain. The existing approval
for kernel DMA mediation and shell-owned services does not itself delegate
application socket access. No source implementation, build or guest window
is reserved by this proposal. R3.6b remains explicitly deferred.
