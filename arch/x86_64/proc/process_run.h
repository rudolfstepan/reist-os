#ifndef REIST_X64_PROCESS_RUN_H
#define REIST_X64_PROCESS_RUN_H
#include "native_pool.h"
/* Private trusted bootstrap contract, not a userspace ABI or a POSIX API. */
#define REIST_X64_RUN_SYSCALLS ((1ULL<<9)|(1ULL<<22)|(1ULL<<40)|(1ULL<<41)|(1ULL<<42))
struct reist_x64_run_task_v1 {
    /* v1: reserved=0. v2 (NativePrograms only): immutable boot image ID3..6.
     * v3 (NativeLifecycle): same image IDs, count=4; argument=1 in root
     * slots0/1 and0 in dynamic slots2/3. Only the roots start initially.
     * Imported image7 is additionally valid only for dynamic slot2, image8
     * only for slot3; these private owners never alias catalog IDs3..6.
     * Same layout, explicitly different versions; not a public spawn ABI. */
    unsigned long long argument, syscalls, cpu_samples, reserved;
};
struct reist_x64_run_v1 {
    unsigned int version, size, count, reserved;
    struct reist_x64_run_task_v1 tasks[4];
};
_Static_assert(sizeof(struct reist_x64_run_v1)==144, "native run descriptor size");
/* Explicit private v4, never reinterpret the v1/v2/v3 four-task layout.
 * The trusted caller admits two roots and six generation-owned dynamic slots. */
struct reist_x64_run_v4 {
    unsigned int version, size, count, reserved;
    struct reist_x64_run_task_v1 tasks[8];
};
_Static_assert(sizeof(struct reist_x64_run_v4)==272, "native run-v4 descriptor size");
/* Explicit periodic CPU authority; never infer it from the backing capacity. */
struct reist_x64_run_v5 {
    unsigned int version, size, count, reserved;
    struct reist_x64_run_task_v1 tasks[8];
    unsigned long long period_ticks[8];
};
_Static_assert(sizeof(struct reist_x64_run_v5)==336, "native run-v5 descriptor size");
#if REIST_NATIVE_DESKTOP_CPU
/* Append-only private v6: only root slot0 can initially request up to64. */
struct reist_x64_run_v6 {
    unsigned int version,size,count,reserved;
    struct reist_x64_run_task_v1 tasks[8];
    unsigned long long period_ticks[8];
};
_Static_assert(sizeof(struct reist_x64_run_v6)==336,"native run-v6 descriptor size");
#endif
#endif
