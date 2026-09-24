/* Explicit bounded immutable-file adapter, not exec/POSIX or new authority. */
#ifndef REIST_X86_64_FILE_IMAGE_H
#define REIST_X86_64_FILE_IMAGE_H
#include <reist/x86_64/filesystem.h>
#include <reist/x86_64/image.h>
#define REIST_X64_FILE_IMAGE_BYTES 1536U
typedef struct {
    uint8_t file[REIST_X64_FILE_IMAGE_BYTES];
    reist_fs_frame frame;
    uint8_t prepared[REIST_X64_PREPARED_V2_BYTES];
} reist_file_image_workspace;
/* An observation of one actual STAT, not a capability or kernel attestation.
 * Ring3 callers own this ordinary value. The immutable-media, exact EOF/ELF
 * and kernel admission checks remain mandatory, including if it is modified.
 * Units are absolute monotonic milliseconds; separating stages never renews
 * the original deadline or resets the FS generation's eight-request budget. */
typedef struct {
    uint32_t version,struct_size;
    uint64_t owner,sequence,deadline_ms,observed_ms;
    reist_fs_frame frame;
} reist_file_capture_v1;
typedef char reist_file_capture_size_check[sizeof(reist_file_capture_v1)==552?1:-1];
/* Output observation remains unchanged on error. Accept an already-used FS
 * client, but never an exhausted/poisoned generation. No retry or rebind. */
int reist_x64_file_stat_v1(reist_file_capture_v1 *,reist_fs_client *,
    const reist_fs_transport *,const char *path,unsigned length,unsigned timeout_ms);
/* Accept only the exact current observation and enough remaining FS capacity.
 * Prepared output unchanged on error; pre-admission leaves workspace intact,
 * all admitted paths scrub it. Successful reads consume the observation via
 * the client's real sequence progress; it cannot be used a second time. */
int reist_x64_file_finish_v2(void *prepared,reist_file_image_workspace *,
    reist_fs_client *,const reist_fs_transport *,const reist_file_capture_v1 *);
/* All objects mapped and disjoint where mutable. Caller supplies fixed storage;
 * no heap or CREATE here. Fresh FS client, immutable medium, eight RPC maximum.
 * Prepared output unchanged on error; admitted workspace scrubbed on return.
 * Admission errors leave every object intact. Deadline checked immediately
 * before the bounded final publication; scheduling is not disabled. */
int reist_x64_file_prepare_v2(void *prepared,reist_file_image_workspace *,
    reist_fs_client *,const reist_fs_transport *,const char *path,unsigned length,
    unsigned timeout_ms);
/* Explicit wide observation2/workspace2. Old versions are not convertible.
 * deadline_ms is an already established absolute bound, never renewed by STAT.
 * Every individual RPC remains<=1000ms. */
typedef reist_file_capture_v1 reist_file_capture_v2;
typedef struct {
    uint8_t file[524288];
    reist_fs_frame frame;
    uint8_t prepared[REIST_X64_PREPARED_V2_BYTES];
} reist_file_image_workspace_v2;
int reist_x64_file_stat_v2(reist_file_capture_v2 *,reist_fs_client *,
    const reist_fs_transport *,const char *path,unsigned length,uint64_t deadline_ms);
int reist_x64_file_finish_v3(void *prepared,reist_file_image_workspace_v2 *,
    reist_fs_client *,const reist_fs_transport *,const reist_file_capture_v2 *);
#ifdef REIST_NATIVE_LARGE_FILE
/* Observation3 keeps the552-byte layout; versions are not convertible. */
typedef reist_file_capture_v1 reist_file_capture_v3;
typedef struct {
    uint8_t file[1048576];
    reist_fs_frame frame;
    uint8_t prepared[REIST_X64_PREPARED_V3_BYTES];
} reist_file_image_workspace_v3;
int reist_x64_file_stat_v3(reist_file_capture_v3 *,reist_fs_client *,
    const reist_fs_transport *,const char *,unsigned,uint64_t deadline_ms);
int reist_x64_file_finish_v4(void *,reist_file_image_workspace_v3 *,
    reist_fs_client *,const reist_fs_transport *,const reist_file_capture_v3 *);
#endif
#endif
