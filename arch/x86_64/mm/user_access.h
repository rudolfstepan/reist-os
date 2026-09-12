#ifndef REIST_X64_USER_ACCESS_H
#define REIST_X64_USER_ACCESS_H
#include <stdint.h>
/* Private SysV AMD64 binding, not a user ABI. Caller pins the existing task
 * and four table-frame records and serializes IF=0 on this single-CPU profile.
 * task begins with state, generation, CR3, stack frame; generation and active
 * CR3 independently bind the executing owner. No authority is granted here.
 * Intel64 SDM Vol3A: data access needs P/U at all levels, writes also W.
 * PF_X=1 checks one instruction byte with P/U and NX clear at every level.
 * Existing4KiB user leaves/8 image pages + stack; no user huge pages or PKU.
 * Physical bounds:128MiB default,16GiB with the explicit NativeRAM build.
 * Kernel direct-map large leaves do not enlarge user authority.
 * Returns1 admitted,0 invalid user range/rights, -4096 corrupt trusted state.
 * No data dereference, allocation, copy, logging, or modification. */
typedef struct {
    const uint64_t *task, *tables;
    uint64_t generation, active_cr3;
} ReistX64UserAccess;
_Static_assert(sizeof(ReistX64UserAccess)==32,"user access binding");
int64_t __attribute__((sysv_abi)) reist_x64_user_access(
    const ReistX64UserAccess *,uint64_t address,uint64_t length,uint64_t elf_access);
/* Explicit bulk-data entry, maximum2060 bytes; PF_R/PF_W only. The original
 * entry still caps data at140 and execution at one byte. */
int64_t __attribute__((sysv_abi)) reist_x64_user_access_bulk(
    const ReistX64UserAccess *,uint64_t address,uint64_t length,uint64_t elf_access);
#endif
