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
/* All objects mapped and disjoint where mutable. Caller supplies fixed storage;
 * no heap or CREATE here. Fresh FS client, immutable medium, eight RPC maximum.
 * Prepared output unchanged on error; admitted workspace scrubbed on return.
 * Admission errors leave every object intact. Deadline checked immediately
 * before the bounded final publication; scheduling is not disabled. */
int reist_x64_file_prepare_v2(void *prepared,reist_file_image_workspace *,
    reist_fs_client *,const reist_fs_transport *,const char *path,unsigned length,
    unsigned timeout_ms);
#endif
