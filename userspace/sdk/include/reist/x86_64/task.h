#ifndef REIST_X86_64_TASK_H
#define REIST_X86_64_TASK_H
#include <reist/x86_64/syscall.h>
/* All arguments are copied synchronously. WAIT may suspend the calling task,
 * never this pointer; its finite timeout does not cancel the child. */
static inline int64_t reist_x64_task_control(const reist_task_control_request_t *q)
{
    return reist_x64_syscall1(REIST_SYS_TASK_CONTROL,(uint64_t)(uintptr_t)q);
}

/* Ordinary mapped C objects; output may not overlap argument string bytes.
 * Validate every input before publication. No heap, hidden syscall or grant. */
static inline int reist_x64_startup_init(reist_task_startup_v1_t *out,
                                       unsigned argc,const char *const *argv)
{
    const char *strings[8]; unsigned lengths[8];
    if(argc>8) return -7;
    if(!out || (argc && !argv)) return -22;
    uintptr_t begin=(uintptr_t)out;
    if(begin>UINTPTR_MAX-sizeof(*out)) return -22;
    for(unsigned i=0;i<argc;i++) {
        const char *p=argv[i]; unsigned n=0;
        if(!p || (uintptr_t)p>UINTPTR_MAX-128) return -22;
        while(n<128 && p[n]) ++n;
        if(n==128) return -7;
        if((uintptr_t)p<begin+sizeof(*out) && (uintptr_t)p+n+1>begin) return -22;
        strings[i]=p; lengths[i]=n;
    }
    volatile unsigned char *bytes=(volatile unsigned char*)out;
    for(unsigned i=0;i<sizeof(*out);i++) bytes[i]=0;
    out->version=1; out->struct_size=sizeof(*out); out->argc=argc;
    for(unsigned i=0;i<argc;i++)
        for(unsigned j=0;j<lengths[i];j++) out->arguments[i][j]=strings[i][j];
    return 0;
}

static inline int64_t reist_x64_task_create(uint64_t image,uint64_t syscalls,
                                          uint64_t cpu_samples,
                                          const reist_task_startup_v1_t *startup)
{
    reist_task_create_v2_t q={2,64,1,0,0,image,0,syscalls,cpu_samples,(uintptr_t)startup};
    return reist_x64_syscall1(REIST_SYS_TASK_CONTROL,(uint64_t)(uintptr_t)&q);
}
#endif
