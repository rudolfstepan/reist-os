#ifndef REIST_X86_64_CPP_RUNTIME_H
#define REIST_X86_64_CPP_RUNTIME_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Private qualification input, never a command argument or authority grant. */
extern volatile uint64_t reist_cpp_runtime_selection[2];
int reist_cpp_runtime_begin(void);
#ifdef __cplusplus
}
#endif
#endif
