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
static inline int64_t reist_x64_task_import(const void *prepared,uint64_t syscalls,
                                          uint64_t cpu_samples,
                                          const reist_task_startup_v1_t *startup)
{
    reist_task_create_v3_t q={3,64,1,0,0,(uintptr_t)prepared,0,syscalls,cpu_samples,(uintptr_t)startup};
    return reist_x64_syscall1(REIST_SYS_TASK_CONTROL,(uint64_t)(uintptr_t)&q);
}
static inline int64_t reist_x64_task_import_profile(const void *prepared,
    const reist_task_profile_v1_t *profile,uint64_t cpu_samples,
    const reist_task_startup_v1_t *startup)
{
    reist_task_create_v4_t q={4,64,1,0,0,(uintptr_t)prepared,0,(uintptr_t)profile,cpu_samples,(uintptr_t)startup};
    return reist_x64_syscall1(REIST_SYS_TASK_CONTROL,(uint64_t)(uintptr_t)&q);
}
/* Append-only CREATE-v5: identical full-profile transport, RNPGv2 only.
 * NativeWide supplies the bounded larger mapping/stack; old kernels reject it. */
static inline int64_t reist_x64_task_import_wide(const void *prepared,
    const reist_task_profile_v1_t *profile,uint64_t cpu_samples,
    const reist_task_startup_v1_t *startup)
{
    reist_task_create_v4_t q={5,64,1,0,0,(uintptr_t)prepared,0,(uintptr_t)profile,cpu_samples,(uintptr_t)startup};
    return reist_x64_syscall1(REIST_SYS_TASK_CONTROL,(uint64_t)(uintptr_t)&q);
}
/* Explicit x86-64 CREATE-v6; samples per1000ms period, not lifetime samples
 * or measured CPU microseconds. Keep this native-only SDK extension beside
 * its wrapper; the generated common syscall ABI header remains exact.
 * Only an admitted periodic root may delegate it. RNPGv2/profile-v1/startup-v1
 * are unchanged. Old kernels reject this version. */
#define REIST_TASK_PERIODIC_IMPORT_VERSION 6U
typedef struct {
    uint32_t version,struct_size,operation,flags;
    uint64_t target,prepared,timeout_ms,profile,cpu_samples,startup;
    uint64_t cpu_period_ms,reserved;
} reist_task_create_v6_t;
typedef char reist_task_periodic_size_check[sizeof(reist_task_create_v6_t)==80U?1:-1];

/* No ambient periodic right, in-place renewal, burst or reset operation. */
static inline int64_t reist_x64_task_import_periodic(const void *prepared,
    const reist_task_profile_v1_t *profile,uint64_t cpu_samples,uint64_t cpu_period_ms,
    const reist_task_startup_v1_t *startup)
{
    reist_task_create_v6_t q={REIST_TASK_PERIODIC_IMPORT_VERSION,80,1,0,0,
        (uintptr_t)prepared,0,(uintptr_t)profile,cpu_samples,(uintptr_t)startup,cpu_period_ms,0};
    return reist_x64_syscall1(REIST_SYS_TASK_CONTROL,(uint64_t)(uintptr_t)&q);
}
#ifdef REIST_NATIVE_LARGE_IMAGE
#ifdef REIST_NATIVE_LARGE_PERIODIC
/* Same transport as v6, explicitly importing RNPGv3. No ambient renewal. */
#define REIST_TASK_LARGE_PERIODIC_IMPORT_VERSION 8U
static inline int64_t reist_x64_task_import_large_periodic(const void *prepared,
        const reist_task_profile_v1_t *profile, uint64_t cpu_samples,
        const reist_task_startup_v1_t *startup) {
    reist_task_create_v6_t q={REIST_TASK_LARGE_PERIODIC_IMPORT_VERSION,80,1,0,0,
        (uintptr_t)prepared,0,(uintptr_t)profile,cpu_samples,(uintptr_t)startup,1000,0};
    return reist_x64_syscall1(REIST_SYS_TASK_CONTROL,(uintptr_t)&q);
}
#endif
#line 90
/* Ordinary lifetime CPU accounting. v6 periodic imports still require RNPGv2. */
#define REIST_TASK_LARGE_IMPORT_VERSION 7U
static inline int64_t reist_x64_task_import_large(const void *prepared,
    const reist_task_profile_v1_t *profile,uint64_t cpu_samples,
    const reist_task_startup_v1_t *startup)
{
    reist_task_create_v4_t q={REIST_TASK_LARGE_IMPORT_VERSION,64,1,0,0,
        (uintptr_t)prepared,0,(uintptr_t)profile,cpu_samples,(uintptr_t)startup};
    return reist_x64_syscall1(REIST_SYS_TASK_CONTROL,(uint64_t)(uintptr_t)&q);
}
#endif
#endif
