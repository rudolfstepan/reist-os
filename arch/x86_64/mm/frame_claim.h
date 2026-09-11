/* Private kernel-only frame transaction. SysV AMD64, no public ABI. */
#ifndef REIST_X64_FRAME_CLAIM_H
#define REIST_X64_FRAME_CLAIM_H
#include <stdint.h>
struct reist_x64_frame_claim { uint64_t frames[13], count, cursor; };
_Static_assert(sizeof(struct reist_x64_frame_claim)==120, "claim layout");
#define X64_CLAIM_ABI __attribute__((sysv_abi))
long long X64_CLAIM_ABI reist_x64_frame_claim_begin(struct reist_x64_frame_claim *, uint64_t);
long long X64_CLAIM_ABI reist_x64_frame_claim_take(struct reist_x64_frame_claim *);
long long X64_CLAIM_ABI reist_x64_frame_claim_abort(struct reist_x64_frame_claim *);
#endif
