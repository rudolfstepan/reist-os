#ifndef REIST_X64_CONSOLE_H
#define REIST_X64_CONSOLE_H
#include <stdint.h>
#define REIST_X64_CONSOLE_CHUNK 64U
#define REIST_X64_CONSOLE_MAX_BYTES 4096U
#define REIST_X64_CONSOLE_ATTEMPTS 128U
/* Explicit non-POSIX completion adapter over nonblocking fd0/fd1 operations.
 * 1..1000ms absolute deadline; <=4096 bytes, <=128 attempts. No heap.
 * On admitted completion/error, *completed reports actual transferred bytes.
 * Invalid arguments do not mutate output or invoke a syscall. Buffer and
 * completed must be disjoint caller-owned objects; raw syscall validates maps.
 * Return0 complete, otherwise negative errno (partial progress is retained). */
int reist_x64_console_read(void *buffer,uint32_t bytes,uint32_t timeout_ms,uint32_t *completed);
int reist_x64_console_write(const void *buffer,uint32_t bytes,uint32_t timeout_ms,uint32_t *completed);
#endif
