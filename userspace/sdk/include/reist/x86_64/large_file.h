/* Explicit immutable capture profile3; no wire/device authority. */
#ifndef REIST_X86_64_LARGE_FILE_H
#define REIST_X86_64_LARGE_FILE_H
#include <reist/x86_64/file_image.h>
enum { REIST_LARGE_FILE_BYTES=1048576, REIST_LARGE_FILE_MS=120000,
       REIST_LARGE_FS_REQUESTS=4098, REIST_LARGE_BLOCK_REQUESTS=8192,
       REIST_LARGE_EXT2_SECTORS=4096 };
#endif
