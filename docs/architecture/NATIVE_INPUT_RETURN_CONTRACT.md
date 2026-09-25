# CI: bounded PS/2 READ return

User renewed `mach weiter` immediately after the concrete scope question
approves the input-read kernel prerequisite on2026-09-25. CB source is paused
byte-exact in build/codex-agent/r83ci-input-return/before-ci01/files.zip,
SHA25628394e53e280b0031ce2c92a1c9d53c0a8f4cc9305bc710248222b0c9b9fab46.
Baseline f5ebfb0d. CB counters86 hosts/50 builds/28 media/38 guests retained;
all five CB gates/eight final cases remain. No CB acceptance or OS completion.

Exactly one active implementation: R8.3ci-input-return. Scope: existing
native_input_syscall64.result only, under REIST_NATIVE_DESKTOP_CPU. READ3
results1..65536 or EAGAIN(-11) use existing query_resume64 after scratch erase.
Everything else uses process_run_resume64. No query burst reset; same shared
8-call ownership, interrupts, CPU32, deadlines, quotas, decoder and rights.
PS/2 wire protocol and errno meanings remain unchanged; private return
routing creates no ABI. No Ring0 protocol parsing. Old disabled assembly
must be byte-identical. No modification to the accepted query-return core.

Failure model: inefficient per-byte dispatch contributes to observed input
CPU fencing and secondary lost application endpoints. Improvement remains
a hypothesis until the original input load/latency proofs pass.

Development reservation: hosts1..8<=180s, builds1..2<=300s, media1..2<=180s,
guests1..4<=600s. Evidence-directed extensions must preserve spent counters.
Frozen final gates, once each per fully frozen qualification:
1. python test/test_x86_64_input_return.py -v (180s): actual assembly routing,
   scratch erasure, success/empty/error/old profile and shared burst invariants.
2. python scripts/verify_x86_64_input_return.py --package (600s): complete
   native desktop build/media from hash-bound immutable paused CB fixture.
3. python scripts/verify_x86_64_input_return.py --runtime (2000s): three fresh
   guests <=600s each, total1800s:801-event mouse stress+10s stable owners,
   original300ms mouse/exact abc+10s stability, existing CPU-fault isolation
   with replacement. No debugging stops in performance cases.
4. python scripts/verify_x86_64_input_return.py --review (180s): independent
   raw-state/pixel/receipt review, immutable source/fixture/artifact hashes,
   scope and closed guests with unchanged base media.

Package gate builds the already preserved CB sources as an immutable fixture;
no CB implementation edits allowed during CI. Success commits CI and resumes
CB integration; do not re-run unrelated unchanged VM matrices. No push.
