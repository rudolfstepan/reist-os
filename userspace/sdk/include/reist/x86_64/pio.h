/* Explicit QEMU primary-master, read-only mediated PIO profile. No raw IOPL. */
#ifndef REIST_X86_64_PIO_H
#define REIST_X86_64_PIO_H
#include <reist/x86_64/syscall.h>
#define REIST_NATIVE_PIO_CONTROL 29U
enum { REIST_PIO_BIND=1,REIST_PIO_READ8,REIST_PIO_WRITE8,REIST_PIO_READ16,REIST_PIO_FENCE };
typedef struct {
    uint32_t version,size,operation,reserved0;
    uint64_t owner;
    uint32_t port,value,count,flags;
    uint64_t data,reserved1,reserved2;
} reist_native_pio_request;
typedef char reist_native_pio_size_check[sizeof(reist_native_pio_request)==64?1:-1];
static inline int64_t reist_x64_pio(reist_native_pio_request *q) {
    return reist_x64_syscall2(REIST_SYS_DEVICE_CONTROL,29,(uintptr_t)q);
}
#endif
