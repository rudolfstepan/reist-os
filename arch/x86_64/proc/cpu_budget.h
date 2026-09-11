#ifndef REIST_X64_CPU_BUDGET_H
#define REIST_X64_CPU_BUDGET_H
#include <stdint.h>
/* Private serialized, kernel-owned accounting. No process/restart authority.
 * op0 validate, op1 bind (arg=limit), op2 charge (arg=absolute tick), op3 clear.
 * Result0: rejected unchanged;1: accepted;2: last permitted sample consumed.
 * Bind requires all-zero record. Generation32 never truncated. Caller clears
 * only after terminal fencing, never on yield, wait, or reschedule.
 */
struct reist_x64_cpu_budget { uint64_t generation,limit,used,last_tick; };
_Static_assert(sizeof(struct reist_x64_cpu_budget)==32,"budget record");
uint64_t __attribute__((sysv_abi)) reist_x64_budget_apply(
    struct reist_x64_cpu_budget *,uint64_t operation,uint64_t generation,uint64_t arg);
#endif
