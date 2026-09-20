/* Local opt-in immutable capture policy; not a wire grant or POSIX exec. */
#ifndef REIST_X86_64_WIDE_FILE_H
#define REIST_X86_64_WIDE_FILE_H
#include <reist/x86_64/file_image.h>
enum { REIST_WIDE_FILE_BYTES=524288, REIST_WIDE_FILE_MS=120000,
       REIST_WIDE_FS_REQUESTS=2050, REIST_WIDE_BLOCK_REQUESTS=4096 };
#endif
