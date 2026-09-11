#ifndef REIST_X64_TERMINAL_STATUS_H
#define REIST_X64_TERMINAL_STATUS_H
#include <stdint.h>
/* Private SysV AMD64, no pointer or memory access. kind0: classified fault,
 * quota or rejected context. kind1: normal REIST uint32 raw exit status.
 * Returns validated nonnegative raw status or -22 (EINVAL). Only RAX/flags
 * are clobbered; no relation to POSIX signal/wait or low-eight-bit encoding. */
int64_t __attribute__((sysv_abi)) reist_x64_terminal_status(uint64_t kind, uint64_t raw);
#endif
