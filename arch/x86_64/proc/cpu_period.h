#ifndef REIST_X64_CPU_PERIOD_H
#define REIST_X64_CPU_PERIOD_H
#include "cpu_budget.h"
/* Private CPU-window-v1 supplement; never a userspace pointer or reset API.
 * period=0 means all four fields are zero and the original lifetime core is
 * used. period=100 means half-open windows anchored at immutable bind origin.
 * budget.used remains lifetime usage in both modes. No accumulated credit.
 * op0 validate,1 bind,2 charge,3 retirement clear; results match the old core.
 * bind arg = limit | (period_ticks << 32); charge arg = authoritative now.
 * now is a monotonic IRQ tick below2^60. Clear is caller-owned after fencing.
 */
struct reist_x64_cpu_window { uint64_t period,origin,index,used; };
_Static_assert(sizeof(struct reist_x64_cpu_window)==32,"CPU window record");
uint64_t __attribute__((sysv_abi)) reist_x64_period_apply(
    struct reist_x64_cpu_budget *,struct reist_x64_cpu_window *,
    uint64_t operation,uint64_t generation,uint64_t arg,uint64_t now);
#endif
