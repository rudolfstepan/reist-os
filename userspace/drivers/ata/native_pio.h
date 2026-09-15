#ifndef REIST_NATIVE_ATA_PIO_H
#define REIST_NATIVE_ATA_PIO_H
#include <reist/x86_64/pio.h>
/* Explicit native target capacity, never a device grant. Default binaries and
 * APIs retain the four-slot profile; only NativePoolPIO selects eight. */
#ifndef REIST_NATIVE_POOL_PIO
#define REIST_NATIVE_POOL_PIO 0
#endif
#if REIST_NATIVE_POOL_PIO != 0 && REIST_NATIVE_POOL_PIO != 1
#error "native pool PIO must be an explicit boolean profile"
#endif
#if REIST_NATIVE_POOL_PIO
static inline int reist_pio_pool_owner_valid(uint64_t owner){
    return (uint32_t)owner>=2 && (uint32_t)owner<8 &&
        (owner>>32) && (owner>>32)<=0x7fffffff;
}
#endif
typedef struct {
    void *context;
    int64_t (*call)(void *,reist_native_pio_request *);
    uint64_t (*clock)(void *);
    int (*sleep)(void *,unsigned);
} reist_pio_ops;
/* Finite PIO data-in; no output publication until complete verified transfer. */
int reist_pio_identify(const reist_pio_ops *,uint64_t owner,uint32_t *sectors);
int reist_pio_read(const reist_pio_ops *,uint64_t owner,uint32_t sectors,
                   uint32_t lba,unsigned char output[512]);
#endif
