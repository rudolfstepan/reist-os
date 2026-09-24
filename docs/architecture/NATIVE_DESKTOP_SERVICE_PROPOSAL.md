# Real native desktop service authority proposal

Prepared2026-09-24 after accepted display adapter1402c13e. No new authority
is implemented or assumed by this document. User priority: usable real native
desktop in VMware, then complete native64 integration.

Explicitly approved2026-09-24: "Ja, begrenzte Desktop-Dienstrechte freigeben"
in response to the concrete question referencing proposal commit80aaf346.
Implementation may proceed within the bounds below; approval is not acceptance.

## Concrete missing boundary

NATIVE_GRAPHICAL_SESSION_CONTRACT explicitly excludes porting the large
desktop's filesystem authority and applet launch requests. Existing graphical
clients have no filesystem/task-management/identity-query authority. Its root
loads four fixed hash-bound role images; it does not provide a desktop namespace
or general application launcher. shell_graphical.inc retains that exact model.

The real desktop.c calls stat/storage/readdir and spawnv/identity/kill/wait for
assets, Explorer and application windows. Its display adapter now resolves16
imports, but45 non-display imports remain. Ordinary app_files grants cannot
substitute: they admit one immutable16KiB snapshot/32 directory entries with
80 requests and1000ms lifetime, not persistent desktop access. Blindly linking
shell_session.c would transfer root-owned namespace and lifecycle policy into
the compositor and contradict the isolation boundary.

## Requested explicit authority

Authorize a separate, versioned, root-mediated desktop service protocol with:

| Operation | Allowed target | Limit |
| --- | --- | --- |
| stat/read/directory enumeration | Explicitly granted immutable files/directories on the signed local boot image | At most8 logical read objects;32 entries per response;1MiB per complete object, existing120000ms complete-transfer deadline |
| application launch | Exact signed/hash-bound manifest allowlist, captured with the accepted RNPGv3 loader | Existing two graphical client slots6/7 only; at most8 startup arguments; no executable authority from path spelling |
| identity/wait/cancel | Only the exact client generation created for this desktop generation | Supervisor owns cancellation, fencing and reap; no arbitrary PID query or task syscall delegation |

The compositor only requests operations; root independently verifies generation,
epoch, sequence, object/manifest identity, rights and range before side effects.
Use the existing root/compositor control channel, bounded to four queued requests,
one outstanding filesystem transaction and16 admitted service requests/1000ms.
No new task slots, endpoint pool, IPC queue depth, kernel device rights, CPU budget
or heap ceiling. Long reads/launch capture must advance through bounded work steps
while root continues existing health supervision; never block it for120 seconds.
Preserve fixed per-operation bounds, complete cleanup, existing restart exhaustion
and the serial rescue path. Closing or losing the desktop revokes every read
object and fences/reaps its owned applications before any generation reuse.

This grants no persistent writes, arbitrary filesystem root access, external
network, raw PIO/MMIO/DMA, identity of unrelated processes or root privilege.
Write operations remain explicit errors; do not advertise save/delete support.
The separate higher-display-throughput proposal is not implicitly approved.
Two applications and read-only Explorer are a bounded initial visual profile,
not proof that every feature of the complete operating system is finished.

## Required implementation and proof

After approval freeze one cohesive service delegation transaction: shared
request/response validation, root broker, actual desktop SDK binding, immutable
file and application manifest/image layout, startup and cancellation cleanup.
Reuse qualified kernel mechanisms. Prove actual successful asset reads and
application starts plus denied paths/writes/foreign generations, malformed and
stale replies, timeout, process crash/hang, root/desktop retirement and repeated
generations. Both image layouts and normal Ring3 shell dispatch remain required.
Host tests cannot replace complete guest lifecycle proof. Carry forward exact
unchanged old VM evidence; newly affected paths require fresh bounded guests.
Then measure input/frame/window/application behavior on the actual VMware image.

AGENTS.md requires a stop for new authority domains. The existing standing
completion instruction covers implementation workflow, but explicitly does not
grant this previously excluded desktop service authority. The explicit approval
above now authorizes this extension; administrative transitions are not blockers.
