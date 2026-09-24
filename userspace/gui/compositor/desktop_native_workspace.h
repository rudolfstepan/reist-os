#ifndef REIST_DESKTOP_NATIVE_WORKSPACE_H
#define REIST_DESKTOP_NATIVE_WORKSPACE_H
#include <stddef.h>
#define REIST_DESKTOP_WORKSPACE_SLOTS 16U
#define REIST_DESKTOP_WORKSPACE_BUDGET (8U * 1024U * 1024U)
/* One process-owned startup allocation transaction; no render-loop growth. */
extern void *reist_desktop_workspaces[REIST_DESKTOP_WORKSPACE_SLOTS];
int reist_desktop_workspace_run(int argc, char **argv,
    int (*entry)(int, char **), const size_t sizes[REIST_DESKTOP_WORKSPACE_SLOTS]);
void reist_desktop_workspace_destroy(void);
#endif
