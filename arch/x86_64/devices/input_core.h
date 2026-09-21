#ifndef REIST_INPUT_CORE_H
#define REIST_INPUT_CORE_H
#include <stdint.h>
#include "userspace/sdk/include/reist/x86_64/input.h"
typedef struct {uint64_t owner,parent,epoch,fenced,window,last,operations,prefix,inverse[8];} native_input_state;
extern int64_t __attribute__((sysv_abi)) native_input_core_init64(native_input_state *);
extern int64_t __attribute__((sysv_abi)) native_input_core_admit64(native_input_state *);
extern int64_t __attribute__((sysv_abi)) native_input_core_apply64(native_input_state *,const reist_input_request_v1 *,uint64_t,uint64_t,uint64_t);
extern int64_t __attribute__((sysv_abi)) native_input_core_fence64(native_input_state *,uint64_t);
extern int64_t __attribute__((sysv_abi)) native_input_core_written64(native_input_state *,uint64_t,uint64_t);
#endif
