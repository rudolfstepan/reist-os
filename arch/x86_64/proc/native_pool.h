#ifndef REIST_NATIVE_POOL_H
#define REIST_NATIVE_POOL_H
/* Private build profile; neither public handles nor backing size grant rights.
 * Legacy probes retain four active slots even in an eight-slot native build. */
#ifndef REIST_NATIVE_TASK_POOL
#define REIST_NATIVE_TASK_POOL 0
#endif
#if REIST_NATIVE_TASK_POOL != 0 && REIST_NATIVE_TASK_POOL != 1
#error "native task pool must be an explicit boolean profile"
#endif
#define REIST_NATIVE_LEGACY_TASKS 4U
#define REIST_NATIVE_ROOT_TASKS 2U
#if REIST_NATIVE_TASK_POOL
#define REIST_NATIVE_TASKS 8U
#else
#define REIST_NATIVE_TASKS 4U
#endif
#define REIST_NATIVE_TASK_MASK ((1U << REIST_NATIVE_TASKS)-1U)
#define REIST_NATIVE_CHILD_MASK (REIST_NATIVE_TASK_MASK & ~3U)
#endif
