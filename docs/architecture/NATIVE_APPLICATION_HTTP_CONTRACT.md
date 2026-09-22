# Native HTTP application contract — R8.3bq

## Baseline and authority

Inventory follows accepted DNS7465e3df, seal
67de6f79f1197954ae0f6be953bd4f50429a1bce9d96c17ee707c4a1ad6014de,
final receipt868768bbce168a716b83b8a1474b204b9ae858df3ead3c53cd3eb3eb3320dce3.
The worktree was clean. Existing explicit destination/generation-bound TCP
approval covers an ordinary foreground curl application to192.0.2.3:80 in
the owned local QEMU peer. No new authority domain is introduced.

Reuse userspace/programs/curl.c and curl_http.c, existing TCP application SDK,
root grants, separate Ring3 stack/driver, and signed DNS media mechanisms.
No HTTP parser or client enters Ring0. The existing curl TLS context alone is
512KiB and requires trusted time, entropy and private heap integration; native
HTTPS is a separate failure/authority slice, not silently stubbed success.
HTTP does not imply transport authentication. Reference contracts: approved
NATIVE_APPLICATION_NETWORK_PROPOSAL, NATIVE_APPLICATION_TCP_CONTRACT,
NATIVE_APPLICATION_DNS_CONTRACT, HIGH_ASSURANCE_CORE_CONTRACT and the shared
HTTP framing in BROWSER_PUBLIC_NAVIGATION_CONTRACT (its browser rights do not
transfer to native curl). R3.6b remains explicitly deferred.

## Cohesive result

NativeAppHTTP implies NativeAppDNS and its existing TCP/network prerequisites.
The ordinary curl.prg is packaged alongside nslookup/nc/udp/cat/ls/probe and
reachable from the normal Ring3 shell, in both Make and Windows layouts.
Keep previous selectors, programs, public SDK numbers and reference artifacts
unchanged when HTTP is disabled. Do not rename a private adapter as POSIX or
claim full upstream curl, TLS or browser compatibility.

Accepted operands: curl [-i|--include] [--max-bytes N] URL, each option once,
N1..512, exact numeric http://192.0.2.3[:80]/path or default slash. Total URL
<=256 bytes, conventional ASCII path/query, no fragments/userinfo/redirect
following. Validate the complete operand vector at root before publishing
application identity/capabilities, and again in the application adapter.
HTTPS, names requiring DNS, foreign peers/ports, -o, private browser IPC,
unknown/duplicate options and out-of-range sizes fail before network effects.
The independent nslookup command remains available; its answer grants no HTTP
rights. Service/configuration/device/restart rights remain root/driver-owned.

The application retains the accepted slot6 lifetime32-tick CPU profile, two
directional root endpoints,64 requests,6s absolute grant, four TCP TCBs with
2048-byte rings and512-byte segments. Root/service retain32 ticks per100 ticks,
existing fixed task/image/stack budgets and two restarts. Each request carries
exact parent/application/service generation, epoch, destination and sequence.
Exit/crash/hang/CPU/revoke uses the existing fence/revoke/reap lifecycle and
never leaves old authority. Do not raise CPU budgets to fit curl.

Native HTTP is an explicit bounded CLI profile: path256, headers512,
body512, stdout1024, copied output chunks64. Shared legacy capacities remain
unchanged. Native connect/IO <=1500ms, transfer hard deadline3000ms and idle
1500ms; operation requests <=2000ms and original6s grant remain controlling.
Close gets <=1000ms, never renews a transfer/grant deadline. Header parsing,
chunking, Content-Length and EOF remain actual shared HTTP code. Native TLS
branches/context are excluded explicitly; no fake authenticated transport.
File/heap/browser IPC calls that remain link-visible fail closed, not successful
no-ops. Ordinary stdout streaming may show partial bytes before a later framing
error; success requires complete validated framing. No atomic stdout claim.

Standards: RFC9110 URI/status/field semantics and RFC9112 HTTP/1.x message
framing, plus existing RFC9293/RFC6298 TCP contracts. Body/header/path/resource
quotas and numeric-only authority admission are documented profile limits.
https://www.rfc-editor.org/rfc/rfc9110.html
https://www.rfc-editor.org/rfc/rfc9112.html

## Frozen scope and finite development reservation

Exactly one package active; allowed_files in automation/reist-s03b.toml is
controlling. Interactive implementation, gates and local commit only; no
nested agents/worktrees/push. Stop for genuinely new authority or unattributed
changes. Source-scope additions require explicit inventory and scope review.
Initial development reservations: hosts01..16 <=600s, builds01..03 <=300s,
media01..03 <=180s, diagnostics01..06 <=180s. Every attempted operation gets
an exclusive receipt under ignored build/codex-agent/r83bq-application-http.
Stop first failure, retain it, correct from evidence; no unchanged retry loop.
Freeze amended finite windows before further in-scope corrections if needed.

Before gates, review actual implementation/cleanup/ABI/deadlines, validate
all tracked and untracked whitespace and exact scope, freeze source/tool and
retained-regression hashes. No implementation/tool edits during gates.

## Acceptance gates (exactly once per frozen candidate)

1. python test/test_x86_64_application_http.py -v (600s): actual C O0/O2
   operand/grant/SDK/output/error/clock behavior, shared HTTP parser/stream
   regressions, native freestanding compile, media corruption and raw reviewer
   negative tests. No source-pattern-only runtime claims.
2. python scripts/verify_x86_64_application_http.py --defaults (600s): complete
   disabled source projection and unchanged accepted reference artifacts,
   including DNS/TCP/UDP seals and ordinary independent tools.
3. python scripts/verify_x86_64_application_http.py --package (600s): fresh
   NativeAppHTTP build<=300s, signed eleven-file media<=180s, independent media
   consumer, exact executable/service bindings and compiler stack audit.
4. python scripts/verify_x86_64_application_http.py --runtime (4800s):25 fresh
   sequential guests<=180s each/4500s aggregate, stop first failure. Cases:
   healthy4g, healthy8g, chunked, fragmented, header-limit, body-limit,
   bad-header, short-body, peer-loss, denied-operands, wrong-grant,
   foreign-owner, stale-grant, malformed-ipc, app-crash, app-hang, app-cpu,
   stack-crash, stack-hang, stack-cpu, driver-crash, driver-hang, driver-cpu,
   exhaustion, parent-crash.
5. python scripts/verify_x86_64_application_http.py --review (600s): independent
   complete raw replay, immutable artifacts, exact scope and acceptance seal.

Runtime proof includes actual ordinary curl request/status/framing/body bytes,
4/8GiB, header/body limits, malformed framing, truncation/peer loss, denied
operands with no unauthorized launch/packets, exact generation/destination
rights, copied requests/replies, application and both service fault domains,
sticky restart exhaustion, parent recovery, independent cat and complete
capability/endpoint/DMA/frame cleanup. Healthy profile demonstrates retained
UDP/TCP/DNS commands. Expected errors never become serial-success shortcuts.
A fresh healthy HTTP application follows recoverable faults; exhaustion stays
closed. Root and role CPU/profile limits are checked from raw kernel evidence.

After all gates and source review: mark package done, commit only owned paths,
verify clean worktree and exact committed contents, record final receipt, then
inventory the next native64 slice without a routine handoff. No overall
native64 completion follows from this bounded HTTP slice alone.

## Development evidence (not acceptance)

Owned implementation remains on setup848cef97. Reserved hosts01..11 were
spent:01 exposed the inherited header quota;02 exposed an incorrect URL test
fixture;03 passed;04 exposed wrong SDK field names in the fixture;05..06
passed;07 exposed successful completion after an output callback crossed the
transfer deadline;08..11 passed after correction. Actual O0/O2 tests now cover
the ordinary curl program, real native TCP SDK (including partial writes and
denied file/heap/IPC authority), operand admission, shared legacy HTTP parser
and stream behavior, eleven-file media corruption and peer wire framing.
Native stdout writes flush the bounded64-byte adapter buffer before returning,
and curl checks the original deadline before/after output and after framing.
Partial output remains possible on error; cleanup has its separate close bound.

Build01 passed45.306s; build02 passed24.945s with output/deadline corrections.
Media01 failed3.319s: the eleventh file's indirect block32 overlapped the old
data start32. HTTP-only producer and independent consumer now start data at33;
media02 passed3.285s, with actual eleven-file and block-corruption regression.
Accepted DNS geometry remains unchanged. Compiler reports for build02 bound
the retained network chain at7528B and HTTP chunk/IPC chain at6784B, including
256B ABI margin within8KiB. A preflight initially referenced a nonexistent
TCP encoder; source inventory corrected it to the actual direct copy path.
Diagnostic01 is reserved against build02 for healthy4g, with exact source
hashes and180s limit. No qualification candidate has been frozen or accepted.
Full receipts and raw evidence remain under
build/codex-agent/r83bq-application-http; failed attempts are not reused.

Hosts12..13 passed actual root operand dispatch, SDK closed-output and clock
regression, and independent raw mutations (authority, selector, HTTP bytes,
CPU receipt, wire replay). Diagnostic01 passed85.929s with two curl and four
retained UDP/TCP/DNS apps,27 packets,138 raw events. Diagnostic02 passed55.828s
with chunked framing,14 packets,61 events. Both used build02 and passed raw
review; neither is qualification. Disabled C tokens, Make/PowerShell rules and
Python AST were compared against848cef97. Preflight corrected a copied Make
media-variable name and an obsolete verifier CLI literal; no accepted profile
source was altered. Initial reservations spent:13 hosts,2 builds,2 media,
2 diagnostics. Candidate01 will freeze the original five gates and25 guests.

## Accepted candidate01

All five frozen gates passed20.298/2.239/37.921/1700.565/8.204s with25 fresh
sequential guests and independent complete raw replay. Seal SHA256:
472ae6b447871fc3d0ee17bcd7b990b5e77a988c48eea002cc22574e19813a03.
Exact frozen source/tool/artifact bindings passed final review before these
queue/documentation closure edits. All approved scope and architecture limits
remain; no TLS, public network, extra device rights or overall native64 claim.
Freeze preflight01 stopped before creating a candidate because the regression
receipt prefix was incorrect; corrected prefix development-host was frozen by
preflight02. No gate was repeated and all earlier attempt evidence remains.
