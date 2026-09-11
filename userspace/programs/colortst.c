/* Normal-shell, bounded typed-console ABI/authority/lifecycle proof. */
#include "x86os.h"

static int raw(reist_terminal_color_request_t *r) {
    return x86os_syscall(X86OS_SYS_TERMINAL_WRITE_COLOR, (uintptr_t)r, 0, 0);
}
static reist_terminal_color_request_t valid(void) {
    reist_terminal_color_request_t r = {0};
    r.version = 1; r.struct_size = sizeof(r); r.descriptor = 1;
    r.length = 1; r.foreground = 1; r.text[0] = 'X'; return r;
}
#define CHECK(c) do { if (!(c)) { x86os_puts("COLOR_TEST_FAIL line="); x86os_print_number(__LINE__); x86os_putchar('\n'); return 1; } } while (0)

static int child(const char *mode) {
    char *args[] = {"/bin/colortst.prg", (char*)mode};
    int pid = x86os_spawnv(args[0], 2, args);
    if (pid <= 0) return -1;
    uint64_t start, now;
    if (x86os_monotonic_ms(&start) != 0) return -1;
    do {
        for (unsigned int i = 0; i < 256U; ++i) {
            x86os_process_info_t info;
            int got = x86os_process_info(i, &info);
            if (got <= 0) break;
            if (info.pid == pid && info.state == X86OS_PROCESS_ZOMBIE) {
                int status = -1;
                return x86os_wait(pid, &status) == pid && status == 0 ? 0 : -1;
            }
        }
        x86os_sleep_ms(1);
        if (x86os_monotonic_ms(&now) != 0) break;
    } while (now - start < 5000U);
    (void)x86os_kill(pid);
    return -1;
}

int main(int argc, char **argv) {
    if (argc == 2) {
        if (argv[1][0] == 's') {
            if (x86os_process_restrict_script() != 0) return 1;
            return x86os_terminal_write_color(1, "DENIED", 6, 1, 0) == -13 ? 0 : 1;
        }
        return x86os_terminal_write_color(1, "DENIED", 6, 1, 0) == -11 ? 0 : 1;
    }
    reist_terminal_color_request_t r = valid();
    CHECK(raw((reist_terminal_color_request_t*)1U) == -14);
    for (unsigned int field=0; field<8; ++field) {
        r=valid(); ((uint32_t*)&r)[field]=0xffffffffU;
        CHECK(raw(&r) == (field==2 ? -9 : -22));
    }
    r=valid(); r.length=0; CHECK(raw(&r)==-22);
    r=valid(); r.length=65; CHECK(raw(&r)==-22);
    r=valid(); r.foreground=16; CHECK(raw(&r)==-22);
    r=valid(); r.background=8; CHECK(raw(&r)==-22);
    r=valid(); r.text[63]='!'; CHECK(raw(&r)==-22);
    r=valid(); r.length=3; r.text[1]='\n'; r.text[2]='\n'; CHECK(raw(&r)==-22);
    for (unsigned int c=0; c<256; ++c) {
        if (c=='\n' || c=='\t' || (c>=32 && c<=126)) continue;
        r=valid(); r.text[0]=(char)c; CHECK(raw(&r)==-22);
    }
    r=valid(); r.descriptor=0; CHECK(raw(&r)==-9);
    int fd=x86os_open_flags("/htdocs/hello.js", X86OS_O_RDWR);
    CHECK(fd>=0); r=valid(); r.descriptor=(uint32_t)fd;
    int result=raw(&r); (void)x86os_close(fd); CHECK(result==-95);
    CHECK(x86os_terminal_write_color(2,"COLOR_ABI_OK\n",13,7,0)==13);
    CHECK(child("deny")==0 && child("script")==0);
    x86os_puts("COLOR_DENIAL_OK\nCOLOR_REAP_OK\n");
    CHECK(child("deny")==0);
    x86os_puts("COLOR_RESTART_OK\nCOLOR_TEST_OK\n");
    return 0;
}
