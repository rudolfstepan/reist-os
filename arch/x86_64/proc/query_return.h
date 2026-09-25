#ifndef REIST_NATIVE_QUERY_RETURN_H
#define REIST_NATIVE_QUERY_RETURN_H
#include <stdint.h>
/* Private SysV AMD64 scheduler state. No public syscall/wire ABI. */
typedef struct {
    uint64_t generation,slot,remaining,inverse_generation,inverse_slot,inverse_remaining;
} reist_native_query_state;
_Static_assert(sizeof(reist_native_query_state)==48,"bounded query state");
/* reset/bind:1 success,0 invalid unchanged. take:1 direct,0 dispatch,-1 invalid. */
int __attribute__((sysv_abi)) qr_reset(reist_native_query_state *);
int __attribute__((sysv_abi)) qr_bind(reist_native_query_state *,uint32_t,uint64_t);
int __attribute__((sysv_abi)) qr_take(reist_native_query_state *,uint32_t,uint64_t);
#endif
