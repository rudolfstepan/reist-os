#ifndef REIST_X64_PROCESS_RUN_H
#define REIST_X64_PROCESS_RUN_H
/* Private trusted bootstrap contract, not a userspace ABI or a POSIX API. */
#define REIST_X64_RUN_SYSCALLS ((1ULL<<9)|(1ULL<<22)|(1ULL<<40)|(1ULL<<41)|(1ULL<<42))
struct reist_x64_run_task_v1 {
    /* v1: reserved=0. v2 (NativePrograms only): immutable boot image ID3..6.
     * Same layout, explicitly different version; not a public spawn ABI. */
    unsigned long long argument, syscalls, cpu_samples, reserved;
};
struct reist_x64_run_v1 {
    unsigned int version, size, count, reserved;
    struct reist_x64_run_task_v1 tasks[4];
};
_Static_assert(sizeof(struct reist_x64_run_v1)==144, "native run descriptor size");
#endif
