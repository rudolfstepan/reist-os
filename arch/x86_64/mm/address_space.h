#ifndef REIST_X64_ADDRESS_SPACE_H
#define REIST_X64_ADDRESS_SPACE_H
#include <stdint.h>
#include <stddef.h>
/* Private SysV AMD64 plan, not a public ABI or an ELF parser. All referenced
 * memory is trusted, pinned and serialized by the caller with IF=0. Source
 * frames remain image-owned; destination frames remain caller-owned, including
 * on failure. No allocation, free or publication of task/CR3 authority here.
 * Intel64 four-level paging: R/RX shared read-only, RW private, R/RW/stack NX.
 * Returns1 on success,0 before any mapping/copy effect on invalid metadata. */
typedef struct {
    uint64_t tables[4], source[8];
    uint8_t flags[8];
    uint64_t private_frames[8], stack, kernel_entries[2];
} ReistX64AddressPlan;
_Static_assert(sizeof(ReistX64AddressPlan)==192,"mapping plan size");
_Static_assert(offsetof(ReistX64AddressPlan,flags)==96,"ELF flag offset");
_Static_assert(offsetof(ReistX64AddressPlan,private_frames)==104,"private frame offset");
_Static_assert(offsetof(ReistX64AddressPlan,stack)==168,"stack frame offset");
_Static_assert(offsetof(ReistX64AddressPlan,kernel_entries)==176,"kernel template offset");
int __attribute__((sysv_abi)) reist_x64_address_space_build(const ReistX64AddressPlan *plan);
/* Side-effect-free adapter; kernel uses its existing direct map. Host tests
 * substitute a controlled frame ledger at link time, never in kernel builds. */
void *__attribute__((sysv_abi)) reist_x64_mapping_pointer64(uint64_t physical);
#endif
