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
/* Append-only envelope v2: offset48 is deadline_ms only in v2; v1 retains
 * both reserved-zero words. BIND/FENCE deliberately remain deadline-free v1. */
static inline int reist_x64_pio_deadline_prepare(reist_native_pio_request *out,
        const reist_native_pio_request *input,uint64_t deadline_ms) {
    if(!out || !input || input->version!=1 || input->size!=64 ||
       input->operation<REIST_PIO_READ8 || input->operation>REIST_PIO_READ16 ||
       input->reserved0 || input->flags || input->reserved1 || input->reserved2 || !deadline_ms)return -22;
    *out=*input;out->version=2;out->reserved1=deadline_ms;return 0;
}
static inline uint64_t reist_x64_pio_deadline_ms(const reist_native_pio_request *q) {
    return q && q->version==2?q->reserved1:0;
}
/* Append-only BIND-v3: trusted root delegates128 calls/100ms to one exact
 * driver generation. Operations retain v1/v2 and16-word transfer semantics.
 * Rejected construction leaves the caller's request unchanged. */
static inline __attribute__((unused)) int reist_x64_pio_throughput_bind_prepare(reist_native_pio_request *out,uint64_t owner) {
    if(!out || (uint32_t)owner<2 || (uint32_t)owner>7 ||
       !(owner>>32) || owner>>32>0x7fffffff)return -22;
    reist_native_pio_request q={3,64,REIST_PIO_BIND,0,owner,0,0,0,0,0,128,0};
    *out=q;return 0;
}
#endif
