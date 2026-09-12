#ifndef REIST_X86_64_TASK_H
#define REIST_X86_64_TASK_H
#include <reist/x86_64/syscall.h>
/* All arguments are copied synchronously. WAIT may suspend the calling task,
 * never this pointer; its finite timeout does not cancel the child. */
static inline int64_t reist_x64_task_control(const reist_task_control_request_t *q)
{
    return reist_x64_syscall1(REIST_SYS_TASK_CONTROL,(uint64_t)(uintptr_t)q);
}
#endif
