# Native Ring3 network session v1

Frozen 22 September 2026 on 07b6ff89, R8.3bl. Existing authorization is
limited to QEMU loopback Ethernet. R3.6b remains deferred.

## Cohesive acceptance boundary

Implement the existing network-control v2 ABI in the ordinary native shell:
status, static configuration, ARP and ICMP echo. Keep driver and protocol
stack in separate Ring3 children, alongside the existing read-only filesystem
pair. Root owns lifecycle; only the network driver receives device32 binding.
Reuse RFC791/RFC792 parsers; RFC826 ARP and IEEE802.3 Ethernet framing use
network byte order. No socket, DHCP, TCP, DNS or full RFC compatibility claim.
Those require their own stateful transport/API work after this control plane.

NativeNetworkSession is explicit, implies NativeNetworkDMA and NativeAppFiles,
excludes GUI/other qualification consumers. Existing disabled profiles retain
their behavior and limits. Preserve root identity/terminal rights; child
rights remain subsets with no inherited NIC ownership. No syscall addition,
raw IO, kernel packet parser, DMA mapping, task or CPU budget expansion.

Load /netdrv.prg and /netstack.prg through the existing immutable filesystem,
admit role-specific SHA256 prepared-image hashes from the signed shell image,
and keep both Windows and Make packaging paths consistent. Reuse the existing
vendor SHA256 adapter. Existing /cat.prg remains independently usable.

## Protocol and lifetime

One control request in flight; finite fixed-size messages and buffers.
Root-to-stack and stack-to-driver endpoints are separate single-peer channels.
Every internal message validates version, extent, generation, epoch, sequence,
deadline and reserved bytes before publication. The NIC epoch is the actual
BIND result, never guessed. All waits use monotonic deadlines and sleep;
receive work is at most eight frames per turn. Keep mediator IO128/100ms,
TX completion100ms and existing CPU32 unchanged. Public operation<=2000ms,
startup<=3000ms after image admission, health<=1000ms, retirement<=5000ms.

Only validated solicited ARP replies populate one operation-local binding;
no persistent ARP cache or authority from unsolicited packets. Existing
drivers/net/arp_binding_cache.c depends on Ring0 interrupt locks and protected
objects, so it is not linked into the Ring3 stack. New requests discard old
correlation, including after timeout. Reject fragmented/malformed IPv4,
invalid checksums, foreign destinations, wrong echo identifiers/sequences,
late replies and trailing internal-message data. No packet side effect on
failed admission. Configure atomically; no zero, multicast, broadcast or
invalid mask/gateway configuration. Payload correlation prevents old echo
replies from satisfying a new operation with repeated public identifiers.

Native synchronous adapter: the existing shell ARP request uses timeout0;
this profile assigns1000ms, including control pacing and the complete200ms
frame-IPC reservation. This is a bounded synchronous observation, not a
compatibility claim for legacy asynchronous ARP queuing. Control pacing sleeps
at most250ms within the original request deadline; restart pacing sleeps1000ms
within the original3000ms startup deadline. No budget or deadline is renewed.

Failure path: detect, isolate, fence device32, close channels, cancel/wait
exact children, recreate, self-test, reintegrate. At most two replacements
within the existing shared parent budget; network exhaustion is sticky for
that domain and cannot disable unrelated file commands. Manual retry uses the
same path and budget. No recovery after uncertain fencing or kernel corruption.

## Frozen verification

Five gates: actual production C host behavior at O0/O2 plus freestanding role
builds; disabled-profile/reference guards; one combined reference package and
signed media validation; real guest matrix; independent raw evidence replay
and scope review. No previous diagnostic promoted to acceptance.

Fresh matrix: healthy4GiB, healthy8GiB, driver crash/hang/CPU, stack
crash/hang/CPU, stale/malformed control, withheld/late/foreign/bad-checksum
packets with later progress, absent NIC, altered service image, restart
exhaustion, active parent crash. Fourteen cases, each<=180s including cleanup,
aggregate<=2520s. Healthy guests exercise ordinary net/ifconfig/arp/ping and
read-only cat after network activity. Every recoverable fault proves cat
progress, generation change, device fencing and finite cleanup; exhaustion
proves subsequent manual admission denied. Packet bytes, task/profile/parent,
device/DMA state, kernel reap receipts and read-only media evidence are required.
Success strings alone do not qualify. No public networking or physical DMA
assurance claim. Keep all failed attempts and spent counters.

Initial development reservation: twelve logged host commands<=600s each,
three builds<=300s, three media publications<=180s, six diagnostic guests
<=180s. On evidence-directed correction, record an additional finite window
before use, preserve all counters and frozen acceptance gates. First failure
stops that qualification candidate. No nested agent, push or automatic retry.
