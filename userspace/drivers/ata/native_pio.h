#ifndef REIST_NATIVE_ATA_PIO_H
#define REIST_NATIVE_ATA_PIO_H
#include <reist/x86_64/pio.h>
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
