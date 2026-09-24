# Native display information mechanism (R8.3cc)

Inventoried on6db35a01 during CB. DEVICE_CONTROL30/QUERY returns only the
delegated epoch; no native DISPLAY_INFO implementation exposes geometry.
The kernel already validates exactly1024x768 or800x600 VBE/BGRX32 boot modes.
The full desktop cannot safely assume the preferred mode or describe a smaller
invented viewport as the physical display. CB's frozen scope excludes kernel
mediation, so pause and preserve its candidate rather than silently expanding it.

Append info request-v2, operation5, fixed64 bytes. Input: version2,size64,op5,
flags0, exact owner and granted epoch, and all output/reserved fields zero.
Output adds width,height,pitch,bits-per-pixel and RGB field positions, retaining
the input identity/header. Units/meaning follow VBE2/3 and existing SDK display
information; no framebuffer address, mapping, cache, mode-change or device grant.
Only the existing live display owner can query. Validate the entire input range
and writable output range, size/version/reserved data, owner/epoch/fence before
publishing any byte. Reject stale/foreign/readonly/unmapped requests without
output changes. Query does not consume/reset copy quotas or change device state.
No heap, waits or complex parser in Ring0; use the validated boot record and
fixed staging record. Kernel corruption retains the existing fatal transition.

Explicit NativeDisplayInfo requires NativeDisplay. Disabled build remains
byte-identical to the clean preimplementation NativeDisplay build. Version1
query/commit/bind/fence behavior and all quotas remain unchanged. The pending
higher display-throughput request is not approved by this metadata mechanism.

Initial reservation:8 development host commands<=180s,3 builds<=300s (clean
baseline then final disabled/enabled),one signed media operation<=180s and
two optional diagnostics<=120s. Preserve all receipts/failures and stop a
qualification window on its first failure; no unchanged retries or agents.

Five frozen gates, once:
1. python test/test_x86_64_display_info.py -v (<=180s): actual assembly core and
   syscall copy adapter with range-check backend at O0/O2; exact old disabled
   code/projection, malformed versions/fields, foreign/stale/fenced identity,
   readonly/unmapped pointers, exact copy and unchanged state/quota counters.
2. python scripts/verify_x86_64_display_info.py --defaults (<=300s): build
   disabled selector, compare complete boot image/program artifacts to the
   preimplementation build; source projection agrees with the frozen baseline.
3. python scripts/verify_x86_64_display_info.py --package (<=600s): enabled
   native build and signed two-medium BIOS package; exact input/output binding.
4. python scripts/verify_x86_64_display_info.py --runtime (<=700s): two fresh
   cases1024x768 and800x600,320s each/640s aggregate. Real Ring3 info self-tests
   and denied operations plus the unchanged complete display/CLI/reap/authority/
   mapping/pixel/immutable-COW oracle. Geometry must agree with QMP/boot data.
5. python scripts/verify_x86_64_display_info.py --review (<=180s): independent
   complete replay of both captures, extra geometry assertions, source/tool/
   image binding, final scope/diff. No repeated old unrelated guest matrices.

After clean acceptance restore the exact CB candidate archive and continue its
approved service integration with spent counters intact. CC is a mechanism
prerequisite, not a usable desktop or completed native OS.

Qualification01 stopped at defaults:92/93 artifacts exact, including complete
boot ELF/program binaries; only file-program.o DWARF line coordinates moved
because opt-in source was inserted. Full objdump comparison recorded the cause.
Preserve all bytes, including debug coordinates, using disabled #line anchors;
do not weaken artifact comparison. Hosts01..04 spent (01 expected absent ABI,
02 O2 test assertions incorrectly disabled by NDEBUG,03/04 pass after test fix).
Baseline build and disabled01 spent; enabled build/media/guests remain unused.
Reserve one additional disabled02 build<=300s and qualification02 with the same
five gates, two320s guests/640s aggregate. Original evidence stays immutable.

Qualification02 accepted: all five frozen gates passed. Host2 tests exercise
actual assembly enabled/disabled at O0/O2 and replay mutations. All93 disabled
artifacts, including DWARF, match the clean baseline exactly. Signed media and
two real BIOS/Ring3 guests pass (29.133s1024,27.600s800), with three actual query/
denial self-tests each and complete existing display/CLI/reap/COW assertions.
Independent full replay passed4.076s. Seal under r83cc-display-info/qualification02.
No display budget increase or full desktop completion claimed. Resume CB.
