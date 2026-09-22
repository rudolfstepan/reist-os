# DNS response validation prerequisite

The user's renewed continuous-completion instruction authorizes correction
of the pre-existing failure recorded under
`build/codex-agent/r83bo-dns-inventory/`. TCP13ca2095 remains accepted.

## Scope and failure boundary

One pure Ring3 SDK packet-validation boundary, shared by existing callers and
the future native resolver. No kernel, network authority, cache lifecycle,
transport handoff, new command or guest integration changes in this package.
The complete packet must validate before address/TTL publication. This is a
host/freestanding parser correction, not a native DNS runtime acceptance.
Cache/server binding and shared transport deadlines belong to the subsequent
stateful resolver transaction. R3.6b stays deferred.

References: [RFC1035](https://www.rfc-editor.org/rfc/rfc1035.txt), sections
4.1 and7.3; [RFC5452](https://www.rfc-editor.org/rfc/rfc5452.txt), section9.1.
Preserve existing C API and error conventions: invalid arguments -22,
malformed/nonmatching response -74, no eligible A answer -2.

## Frozen acceptance

- Match transaction, standard response opcode, QR, one exact case-insensitive
  question, A type and IN class. An optional terminal root dot is equivalent.
- Reject truncation/error responses and reserved Z bit; AD/CD remain flags,
  never a claim of DNSSEC validation. Existing512-byte packet bound remains.
- Validate every declared RR and exact packet extent before publishing output.
  At most64 records; only answer-section A/CNAME can satisfy the query.
- Compression uses only previously validated label boundaries, backward
  pointers, at most8 pointer traversals and128 labels per name. Reject embedded
  NUL/dot and non-printable label octets that cannot be represented faithfully
  by this string API. No claim of arbitrary binary-label support.
- Text names at most253 bytes; labels1..63; fixed-capacity metadata only.
  Follow at most8 CNAME links independent of answer order, reject cycles,
  conflicting aliases and simultaneous CNAME/A. Exact CNAME RDLENGTH and A4.
- TTL is the minimum of the accepted chain and address RRset, capped3600s;
  zero stays zero. No output mutation on any rejection, including a malformed
  suffix after an otherwise valid A. Null/overlapping output parameters fail.
- Actual C host tests at O0/O2: retained legacy tests, recorded mismatch,
  header/question mutations, compression/RDATA/bounds, reordered chains,
  cycles, section poisoning, TTL and output nonpublication. Deterministic
  packet-prefix truncation coverage. Freestanding i386 and x86_64 compilation
  checks the existing SDK ABI; no guest runtime claim from those checks.

## Transaction and reservations

Exactly this package active. Initial at most8 development host commands600s;
no guest/media/kernel-build reservation. Freeze exact source/header/tool hashes
and three gates once per candidate: host600s, compile300s, review120s. Full
logs/evidence under ignored `build/codex-agent/r83bo-dns-validation/`.
Check new-file whitespace before freezing; final local commit only after all
gates pass and exact scope review. No push, agents or destructive Git recovery.
After the clean commit, inventory/freeze native resolver integration under the
existing destination/generation-scoped application network approval.
