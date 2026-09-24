#include "../userspace/gui/compositor/desktop_native_workspace.h"
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static void *owned[16];
static unsigned calls, frees, fail_at, entered;
static size_t sizes[16];
void *x86os_malloc(size_t bytes) {
    assert(calls < 16);
    unsigned slot = calls++;
    if (slot == fail_at) return 0;
    void *p = malloc(bytes); assert(p);
    memset(p, 0xa5, bytes); owned[slot] = p; return p;
}
void x86os_free(void *p) {
    assert(p);
    for (unsigned n = 0; n < 16; ++n) if (owned[n] == p) {
        assert(!reist_desktop_workspaces[n]);
        owned[n] = 0; ++frees; free(p); return;
    }
    assert(!"foreign or duplicate free");
}
static void empty(void) {
    for (unsigned n = 0; n < 16; ++n)
        assert(!owned[n] && !reist_desktop_workspaces[n]);
}
static void reset(unsigned fail) {
    empty(); calls = frees = entered = 0; fail_at = fail;
    for (unsigned n = 0; n < 16; ++n) sizes[n] = n * 8 + 1;
}
static int entry(int argc, char **argv) {
    assert(argc == 3 && argv == (char **)(uintptr_t)32);
    ++entered;
    for (unsigned n = 0; n < 16; ++n) {
        assert(reist_desktop_workspaces[n] == owned[n]);
        unsigned char *bytes = reist_desktop_workspaces[n];
        for (size_t i = 0; i < sizes[n]; ++i) assert(bytes[i] == 0);
        bytes[0] = 77;
    }
    assert(reist_desktop_workspace_run(argc, argv, entry, sizes) == -16);
    return -71;
}
int main(void) {
    for (unsigned fail = 0; fail < 16; ++fail) {
        reset(fail);
        assert(reist_desktop_workspace_run(3, (char **)(uintptr_t)32, entry, sizes) == -12);
        assert(!entered && calls == fail + 1 && frees == fail);
        empty(); reist_desktop_workspace_destroy(); empty();
    }
    reset(99);
    assert(reist_desktop_workspace_run(3, (char **)(uintptr_t)32, entry, sizes) == -71);
    assert(entered == 1 && calls == 16 && frees == 16);
    empty(); reist_desktop_workspace_destroy(); assert(frees == 16);
    for (unsigned bad = 0; bad < 16; ++bad) {
        for (unsigned variant = 0; variant < 3; ++variant) {
            reset(99);
            sizes[bad] = variant == 0 ? 0 : variant == 1 ? SIZE_MAX : REIST_DESKTOP_WORKSPACE_BUDGET;
            assert(reist_desktop_workspace_run(3, (char **)(uintptr_t)32, entry, sizes) == -22);
            assert(!calls && !entered); empty();
        }
    }
    reset(99);
    assert(reist_desktop_workspace_run(0, 0, 0, sizes) == -22);
    assert(reist_desktop_workspace_run(0, 0, entry, 0) == -22);
    assert(!calls); empty();
    /* Exact cap, full initialization, and cleanup use actual allocated bytes. */
    sizes[0] = REIST_DESKTOP_WORKSPACE_BUDGET;
    for (unsigned n = 1; n < 16; ++n) sizes[0] -= sizes[n];
    assert(reist_desktop_workspace_run(3, (char **)(uintptr_t)32, entry, sizes) == -71);
    assert(entered == 1 && calls == frees && frees == 16); empty();
    return 0;
}
