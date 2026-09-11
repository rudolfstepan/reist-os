/* Real admission/renderer bodies are injected by the Python harness.
 * Only hardware, usercopy, descriptor/input authority and mutex are faked. */
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "include/reist/abi/syscall.h"
#include "drivers/video/framebuffer.h"
#define REQUIRE(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); exit(1); } } while (0)
#define USE_FRAMEBUFFER 1
#define VGA_COLS 80
#define VGA_ROWS 25
#define SERIAL_COM1 1
#define FONT_WIDTH 8
#define FONT_HEIGHT 16
#define DISPLAY_BACKEND_NONE 0
#define DISPLAY_STATE_TIMEOUT_MS 250
#define PROCESS_DESCRIPTOR_TERMINAL_OUTPUT 5
typedef struct { int alive; } Process;
static Process owner;
static Process *current = &owner;
static int input_result, copy_result, range_result = 1;
static int fd_result, lock_result, locked, locks, unlocks, checks, copies;
static uint8_t fd_kind = PROCESS_DESCRIPTOR_TERMINAL_OUTPUT;
static int display_state_mutex, activation_busy, active_backend, mode_fault_backend;
static unsigned short guarded[VGA_COLS * VGA_ROWS + 2];
static unsigned short *vga_buffer = guarded + 1;
static char current_color = 0x0f;
static int ansi_state = 2, vx, vy;
static uint8_t *fb_address;
static int terminal_cols = 80, terminal_rows = 25, cursor_x, cursor_y;
static uint32_t fg_color = FB_COLOR_WHITE, bg_color = FB_COLOR_BLACK;
static int glyphs, presents, scrolls, serial_count;
static uint32_t last_fg, last_bg;
static char serial_text[128];
static Process *scheduler_current_process(void) { return current; }
static void *paging_current_directory(void) { return &owner; }
static bool user_range_accessible(void *d, uint32_t p, unsigned int size, bool write) {
    REQUIRE(d == &owner && p && size == 96U && !write); return range_result != 0;
}
static int copy_from_user(void *to, const void *from, unsigned int size) {
    REQUIRE(size == 96U); ++copies;
    if (!copy_result) memcpy(to, from, size);
    return copy_result;
}
static int process_descriptor_validate_access(const Process *p, int fd, bool write, uint8_t *kind) {
    REQUIRE(p == &owner && write && !locked);
    if (fd != 1 && fd != 2 && fd != 7) return -9;
    *kind = fd_kind; return fd_result;
}
static int process_terminal_input(Process *p, reist_terminal_input_request_t *r) {
    REQUIRE(p == &owner && !locked && r->operation == REIST_TERMINAL_CHECK);
    REQUIRE(r->version == REIST_TERMINAL_INPUT_VERSION && r->struct_size == sizeof(*r));
    REQUIRE(!r->reserved && !r->target_pid && !r->target_generation);
    ++checks; return input_result;
}
static int kernel_mutex_lock_for(int *m, unsigned int ms) {
    REQUIRE(m == &display_state_mutex && ms == DISPLAY_STATE_TIMEOUT_MS && !locked);
    ++locks; if (lock_result) return lock_result; locked = 1; return 0;
}
static void kernel_mutex_unlock(int *m) { REQUIRE(m == &display_state_mutex && locked); locked = 0; ++unlocks; }
static void get_cursor_position(int *x, int *y) { *x = vx; *y = vy; }
static void set_cursor_position(int x, int y) { REQUIRE(x >= 0 && x < 80 && y >= 0 && y < 25); vx=x; vy=y; }
bool framebuffer_available(void) { return fb_address != NULL; }
static void fb_draw_char(char c, int x, int y, uint32_t fg, uint32_t bg) {
    REQUIRE(locked && c >= 32 && x >= 0 && x < terminal_cols && y >= 0 && y < terminal_rows);
    ++glyphs; last_fg = fg; last_bg = bg;
}
static void framebuffer_present_rect(uint32_t x, uint32_t y, uint32_t w, uint32_t h) {
    REQUIRE(locked && x < (uint32_t)terminal_cols * 8U && y < (uint32_t)terminal_rows * 16U && w == 8 && h == 16);
    ++presents;
}
void framebuffer_scroll(void) { REQUIRE(locked); ++scrolls; }
static void serial_write_char(int port, char c) {
    REQUIRE(locked && port == SERIAL_COM1 && serial_count < 128);
    serial_text[serial_count++] = c;
}
/* PRODUCTION */

/* Actual ECHO adapter with observable SDK boundary: validate-before-prefix,
 * one-LF/64-byte chunks, budget, no hidden retry and unchanged plain mode. */
static char cli_text[8192];
static unsigned int cli_used, cli_calls, cli_color;
static uint64_t cli_clock, cli_step;
static int cli_error;
static void x86os_putchar(char c) { REQUIRE(cli_used < sizeof(cli_text)); cli_text[cli_used++]=c; }
static void x86os_puts(const char *s) { while (*s) x86os_putchar(*s++); }
static int x86os_monotonic_ms(uint64_t *ms) { *ms=cli_clock; cli_clock+=cli_step; return 0; }
static int x86os_terminal_write_color(uint32_t fd, const char *s, uint32_t n, uint32_t fg, uint32_t bg) {
    REQUIRE(fd==1 && n>0 && n<=64 && fg<16 && bg==0);
    unsigned int lf=0;
    for (unsigned int i=0;i<n;++i) {
        unsigned char c=(unsigned char)s[i];
        if (c=='\n') ++lf; else REQUIRE(c=='\t' || (c>=32 && c<=126));
    }
    REQUIRE(lf<=1); ++cli_calls; cli_color=fg;
    if (cli_error) return cli_error;
    for (unsigned int i=0;i<n;++i) x86os_putchar(s[i]);
    return (int)n;
}
/* ECHO */
static void cli_reset(void) {
    cli_used=cli_calls=cli_color=0; cli_error=0; cli_clock=cli_step=0;
    memset(cli_text,0,sizeof(cli_text));
}
static void test_echo(void) {
    char large[4097]; memset(large,'a',sizeof(large)); large[4095]=0;
    char *args[]={"echo","--color","bright-green",large};
    cli_reset(); REQUIRE(echo_main(4,args)==0 && cli_used==4096 && cli_calls==64 && cli_color==10);
    REQUIRE(cli_text[4094]=='a' && cli_text[4095]=='\n');
    cli_reset(); large[4095]='a'; large[4096]=0;
    REQUIRE(echo_main(4,args)==1 && !cli_calls && !strncmp(cli_text,"echo: invalid",13));
    cli_reset(); large[4095]=0; large[4094]='\033';
    REQUIRE(echo_main(4,args)==1 && !cli_calls);
    cli_reset(); args[3]="a\nb\nc";
    REQUIRE(echo_main(4,args)==0 && cli_calls==3 && !strcmp(cli_text,"a\nb\nc\n"));
    cli_reset(); args[2]="invalid"; REQUIRE(echo_main(4,args)==1 && !cli_calls);
    cli_reset(); REQUIRE(echo_main(2,args)==1 && !cli_calls);
    cli_reset(); args[2]="red"; cli_step=5000;
    REQUIRE(echo_main(4,args)==1 && !cli_calls);
    cli_reset(); cli_error=-16; REQUIRE(echo_main(4,args)==1 && cli_calls==1);
    cli_reset(); char *plain[]={"echo","unchanged","text"};
    REQUIRE(echo_main(3,plain)==0 && !cli_calls && !strcmp(cli_text,"unchanged text\n"));
}

static reist_terminal_color_request_t valid(void) {
    reist_terminal_color_request_t r = {0};
    r.version = 1; r.struct_size = sizeof(r); r.descriptor = 1;
    r.length = 1; r.foreground = 1; r.text[0] = 'X'; return r;
}
static void reset(void) {
    current=&owner; input_result=copy_result=fd_result=lock_result=0; range_result=1;
    fd_kind=PROCESS_DESCRIPTOR_TERMINAL_OUTPUT;
    activation_busy=active_backend=mode_fault_backend=0;
    checks=copies=locks=unlocks=locked=0;
    glyphs=presents=scrolls=serial_count=0;
    fb_address=NULL; vx=vy=cursor_x=cursor_y=0;
    terminal_cols=80; terminal_rows=25;
    memset(guarded, 0, sizeof(guarded)); guarded[0]=0xabcd; guarded[2001]=0xdcba;
}
static void denied(reist_terminal_color_request_t *r, int error) {
    unsigned short before[2002]; memcpy(before, guarded, sizeof(before));
    REQUIRE(syscall_terminal_write_color(r) == error);
    REQUIRE(!locked && !glyphs && !serial_count && !presents && !scrolls);
    REQUIRE(!memcmp(before, guarded, sizeof(before)) && !vx && !vy);
    REQUIRE(current_color == 15 && ansi_state == 2 && fg_color == FB_COLOR_WHITE && bg_color == FB_COLOR_BLACK);
}
int main(void) {
    reset(); reist_terminal_color_request_t r=valid();
    denied(NULL,-14); REQUIRE(!copies);
    current=NULL; denied(&r,-13); current=&owner;
    range_result=0; denied(&r,-14); REQUIRE(!copies);
    range_result=1; copy_result=-1; denied(&r,-14); copy_result=0;
    for (unsigned int field=0; field<8; ++field) {
        r=valid(); ((uint32_t*)&r)[field]=0xffffffffU;
        denied(&r, field == 2 ? -9 : -22);
    }
    r=valid(); r.length=0; denied(&r,-22);
    r=valid(); r.length=65; denied(&r,-22);
    r=valid(); r.background=8; denied(&r,-22);
    r=valid(); r.foreground=16; denied(&r,-22);
    for (unsigned int i=1; i<64; ++i) { r=valid(); r.text[i]='z'; denied(&r,-22); }
    for (unsigned int c=0; c<256; ++c) {
        if (c=='\n' || c=='\t' || (c>=32 && c<=126)) continue;
        r=valid(); r.length=2; r.text[1]=(char)c; denied(&r,-22);
    }
    r=valid(); r.length=3; r.text[1]='\n'; r.text[2]='\n'; denied(&r,-22);
    r=valid(); r.descriptor=0; denied(&r,-9);
    r=valid(); fd_result=-9; denied(&r,-9); fd_result=0;
    fd_kind=3; denied(&r,-95); fd_kind=PROCESS_DESCRIPTOR_TERMINAL_OUTPUT;
    input_result=-11; denied(&r,-11); input_result=-3; denied(&r,-3); input_result=0;
    lock_result=-110; denied(&r,-110); lock_result=0;
    activation_busy=1; denied(&r,-16); activation_busy=0;
    active_backend=1; denied(&r,-16); active_backend=0;
    mode_fault_backend=1; denied(&r,-16); mode_fault_backend=0;
    static const unsigned char palette[16]={0,4,2,6,1,5,3,7,8,12,10,14,9,13,11,15};
    for (unsigned int fg=0; fg<16; ++fg) for (unsigned int bg=0; bg<8; ++bg) {
        reset(); r=valid(); r.foreground=fg; r.background=bg; r.descriptor=7;
        REQUIRE(syscall_terminal_write_color(&r)==1);
        REQUIRE(vga_buffer[0]==('X' | ((palette[fg] | (palette[bg]<<4))<<8)));
        REQUIRE(vx==1 && vy==0 && serial_count==1 && serial_text[0]=='X');
        REQUIRE(copies==1 && checks==1 && locks==1 && unlocks==1 && !locked);
        reset(); fb_address=(uint8_t*)&owner;
        REQUIRE(syscall_terminal_write_color(&r)==1 && glyphs==1 && presents==1);
        REQUIRE(last_fg==vga_to_fb_color(palette[fg]) && last_bg==vga_to_fb_color(palette[bg]));
        REQUIRE(fg_color==FB_COLOR_WHITE && bg_color==FB_COLOR_BLACK && current_color==15 && ansi_state==2);
    }
    reset(); r=valid(); vx=79; vy=24;
    REQUIRE(syscall_terminal_write_color(&r)==1 && vx==0 && vy==24);
    REQUIRE(vga_buffer[23*80+79]==0x0458 && vga_buffer[24*80]==0x0f20);
    REQUIRE(guarded[0]==0xabcd && guarded[2001]==0xdcba);
    reset(); vy=25; REQUIRE(syscall_terminal_write_color(&r)==-19 && !serial_count);
    reset(); vx=-1; REQUIRE(syscall_terminal_write_color(&r)==-19 && !serial_count);
    reset(); fb_address=(uint8_t*)&owner; cursor_x=79; cursor_y=24;
    REQUIRE(syscall_terminal_write_color(&r)==1 && scrolls==1 && !presents && cursor_y==24);
    reset(); fb_address=(uint8_t*)&owner; terminal_cols=0; denied(&r,-19);
    reset(); fb_address=(uint8_t*)&owner; cursor_y=25; denied(&r,-19);
    reset(); r=valid(); r.length=64; memset(r.text,'a',64); r.text[10]='\t'; r.text[63]='\n';
    REQUIRE(syscall_terminal_write_color(&r)==64 && serial_count==64 && vx==0 && vy==1);
    REQUIRE(current_color==15 && ansi_state==2 && !locked);
    test_echo();
    puts("TERMINAL_COLOR_HOST_OK"); return 0;
}
