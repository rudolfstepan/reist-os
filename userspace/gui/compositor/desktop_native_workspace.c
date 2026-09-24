#include "desktop_native_workspace.h"
#include <x86os.h>

void *reist_desktop_workspaces[REIST_DESKTOP_WORKSPACE_SLOTS];
static unsigned owned;

void reist_desktop_workspace_destroy(void) {
    for (unsigned n = REIST_DESKTOP_WORKSPACE_SLOTS; n; --n) {
        void *p = reist_desktop_workspaces[n - 1];
        reist_desktop_workspaces[n - 1] = 0;
        if (p) x86os_free(p);
    }
    owned = 0;
}

int reist_desktop_workspace_run(int argc, char **argv,
    int (*entry)(int, char **), const size_t sizes[REIST_DESKTOP_WORKSPACE_SLOTS]) {
    if (!entry || !sizes) return -22;
    if (owned) return -16;
    size_t total = 0;
    for (unsigned n = 0; n < REIST_DESKTOP_WORKSPACE_SLOTS; ++n) {
        if (!sizes[n] || sizes[n] > REIST_DESKTOP_WORKSPACE_BUDGET - total)
            return -22;
        total += sizes[n];
    }
    owned = 1;
    for (unsigned n = 0; n < REIST_DESKTOP_WORKSPACE_SLOTS; ++n) {
        void *p = x86os_malloc(sizes[n]);
        if (!p) {
            reist_desktop_workspace_destroy();
            return -12;
        }
        reist_desktop_workspaces[n] = p;
        /* malloc does not promise zero initialization. Keep this bounded
         * initialization explicit and independent of a libc implementation. */
        volatile unsigned char *bytes = p;
        for (size_t i = 0; i < sizes[n]; ++i) bytes[i] = 0;
    }
    int result = entry(argc, argv);
    reist_desktop_workspace_destroy();
    return result;
}
