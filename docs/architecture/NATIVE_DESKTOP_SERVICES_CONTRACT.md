# Full native desktop service integration (R8.3cb)

Frozen after display1402c13e and explicit approval of80aaf346. Authority is
exactly NATIVE_DESKTOP_SERVICE_PROPOSAL.md, including its two-app/read-only
limits. No implicit approval of higher display throughput or persistent writes.
Actual desktop.c is the compositor. Keep old prototype and all old profiles
byte-identical when the new explicit selector is disabled.

## Cohesive boundary

Root mediates immutable boot-image objects and exact manifest-bound application
lifecycles. Compositor never receives raw storage or generic task rights. Keep
eight task slots, existing endpoint/capacity pools,32 CPU samples/1000ms and
the established graphical health/restart/reap/fencing state machine. Only slots
6/7 may host applications. Descriptor IDs bind desktop, service and object
generations; no cache/PID may manufacture liveness. Read at most1MiB/object,
eight open read objects,32 entries/response, four queued operations, one active
FS transaction,16 new service requests/1000ms. Complete transfer deadline
120000ms; kernel syscall deadlines and per-call copy limits remain unchanged.

Service wire-v1 uses bounded fixed-size messages over the existing IPC bulk-v2
transport (2060-byte ABI,2048-byte payload), never raw user addresses. The root
control receiver can accept normal health frames alongside bulk requests;
kernel ipc_receive_bulk_timeout already preserves those types. Validate exact
version/size/reserved bytes, identities, sequence, paths, manifest indices,
rights, ranges and deadlines before enqueueing or dispatch. A malformed reply
fences the client session; no publish-on-error and no unchanged retry.
Any long operation advances in bounded steps between health/input checks.
Root blocks for neither a whole large-file capture nor an application lifetime.

Use existing ELF64/RNPGv3 capture/import and pinned SHA-256 for large role images;
preserve old RNPGv2 interfaces and exact disabled behavior. Native file/Surface
APIs retain established field layouts and negative errno conventions. Unsupported
write/acceleration/features report explicit errors. Do not synthesize successful
file reads, identities, launches, clocks or service grants to satisfy linking.

Compositor startup accounts separately for its accepted7291652-byte workspace,
two3MiB display buffers, font and bounded service state inside the unchanged
heap ceiling. Its actual event loop pumps coalesced display damage with input
and health; no100ms/four-tile prototype throttle. Use the actual ordinary shell
desktop dispatch and both Windows/Makefile image layouts. Root must revoke
objects, fence outputs, close channels, reap and validate fresh generations on
every configured exit/fault/hang path before reintegration.

## Execution reservation and frozen gates

Initial window:24 host development commands<=180s,4 builds<=300s,
4 media operations<=180s,4 diagnostics<=180s. Keep individual logs/counters;
failures stay failed. Evidence-directed additional finite windows follow the
standing interactive directive; no routine approval/reset. No nested agents.
All gate commands below run once in the qualification window, first failure
stops it. Complete the adapters and cheap admission checks before guests.

1. python test/test_x86_64_full_desktop.py -v (<=180s)
   Actual C root/client state transitions, ABI/layout, admission before effects,
   complete normal reads/directories/two launches and denied writes/foreign
   generations, quota/deadline/sequence/reply corruption, cancellation and
   revocation, allocator rollback, actual event-loop hooks, old/new hash bounds.
2. python scripts/verify_x86_64_full_desktop.py --defaults (<=300s)
   Complete disabled-source/output projection; bind accepted unchanged kernel,
   input, storage, large-file and earlier graphical evidence. Do not restart
   old VM matrices whose code/tools/images remain exactly unchanged.
3. python scripts/verify_x86_64_full_desktop.py --package (<=600s)
   Normal/hardware builds, genuine no-undefined native desktop ELF, manifest
   integrity, both installation layouts and signed boot media, decoder/import
   limits and exact allowed-file scope. No mini-desktop substitution.
4. python scripts/verify_x86_64_full_desktop.py --runtime (<=5000s)
   Eight new affected-path cases<=600s each,<=4200s aggregate: normal real UI
   and read/launch/exit; compositor fault; compositor hang; input loss; client
   fault/stale handle; storage fault; malformed service reply; root loss and
   fresh generation. Preserve raw logs/pixels/process/frame/IPC/device evidence.
5. python scripts/verify_x86_64_full_desktop.py --review (<=1200s)
   Independently replay every new case and verify input/frame/window/app,
   parent/child/resource cleanup, generation and isolation predicates. Final
   scope/diff review and source/tool/image hashes match the pre-gate freeze.

VMware visual/performance proof is still required after guest acceptance, using
the actual image with supported functions stated accurately. Neither partial
linking nor a painted screenshot completes native64. R3.6b remains deferred.
