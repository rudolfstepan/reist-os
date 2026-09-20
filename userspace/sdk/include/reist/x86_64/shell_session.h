#ifndef REIST_X86_64_SHELL_SESSION_H
#define REIST_X86_64_SHELL_SESSION_H
#include <stddef.h>
/* Build-owned immutable service images, never filesystem-derived authority. */
typedef struct {
    const unsigned char *driver;size_t driver_bytes;
    const unsigned char *filesystem;size_t filesystem_bytes;
} reist_shell_images;
extern const reist_shell_images reist_native_shell_images;
#endif
