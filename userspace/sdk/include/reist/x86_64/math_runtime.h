#ifndef REIST_X86_64_MATH_RUNTIME_H
#define REIST_X86_64_MATH_RUNTIME_H
#include <stdint.h>
/* Private, zero-default qualification selector; no command-line authority. */
extern volatile uint64_t reist_math_runtime_selection[2];
extern volatile uint64_t reist_math_runtime_witness[16];
extern unsigned char reist_math_fp_wanted[512];
extern unsigned char reist_math_fp_observed[512];
void reist_math_runtime_checkpoint(void);
#endif
