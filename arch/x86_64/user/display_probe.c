/* Normal foreground ELF64. Policy/painting is Ring3; no device address. */
#include <reist/x86_64/syscall.h>
#include <reist/x86_64/terminal.h>
#include <reist/x86_64/display.h>
static uint32_t pixels[64*64];
/* Explicit file-backed multi-page load, using the existing wide-file profile. */
static const unsigned char image_padding[4096] __attribute__((used))={0x44};
static uint64_t now(void) {
    int64_t t=reist_x64_syscall0(REIST_X64_SYS_MONOTONIC_MS);
    if(t<0)__builtin_trap();return (uint64_t)t;
}
static int64_t call(reist_display_request_v1 *r) {
    return reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,30,(uintptr_t)r);
}
static int output(const char *s,unsigned count) {
    uint64_t end=now()+200;unsigned done=0;
    for(unsigned n=0;n<32 && done<count && now()<end;n++) {
        int64_t r=reist_x64_syscall3(REIST_X64_SYS_WRITE,1,(uintptr_t)(s+done),count-done);
        if(r==-11){if(reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,10))return 0;continue;}
        if(r<=0 || (uint64_t)r>count-done)return 0;done+=(unsigned)r;
    }
    return done==count;
}
#ifdef REIST_NATIVE_DISPLAY_INFO
static int info_same(const reist_display_info_v2 *a,const reist_display_info_v2 *b) {
    const unsigned char *x=(const void *)a,*y=(const void *)b;
    for(unsigned n=0;n<64;n++)if(x[n]!=y[n])return 0;
    return 1;
}
static int info_denied(reist_display_info_v2 q,int64_t expected) {
    reist_display_info_v2 before=q;
    return reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,30,(uintptr_t)&q)==expected && info_same(&q,&before);
}
static int info_test(uint64_t owner,uint64_t epoch) {
    reist_display_info_v2 q={.version=2,.size=64,.operation=REIST_DISPLAY_INFO,.owner=owner,.epoch=epoch};
    reist_display_info_v2 clean=q;
    if(reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,30,(uintptr_t)&q))return 0;
    if(q.version!=2 || q.size!=64 || q.operation!=5 || q.flags || q.owner!=owner || q.epoch!=epoch ||
       q.bits_per_pixel!=32 || q.red_field_position!=16 || q.green_field_position!=8 ||
       q.blue_field_position || q.reserved || q.pitch<q.width*4 || q.pitch>16384)return 0;
    unsigned width=q.width,height=q.height;
    if(!((width==1024 && height==768)||(width==800 && height==600)))return 0;
    q=clean;q.epoch--;if(!info_denied(q,-116))return 0;
    q=clean;q.owner++;if(!info_denied(q,-116))return 0;
    q=clean;q.flags=1;if(!info_denied(q,-22))return 0;
    q=clean;q.reserved=1;if(!info_denied(q,-22))return 0;
    q=clean;q.width=1;if(!info_denied(q,-22))return 0;
    if(reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,30,UINT64_MAX)!=-14)return 0;
    static const reist_display_info_v2 readonly={.version=2,.size=64,.operation=REIST_DISPLAY_INFO};
    if(reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,30,(uintptr_t)&readonly)!=-14)return 0;
    return width==1024?output("DISPLAY_INFO_1024\n",18):output("DISPLAY_INFO_800\n",17);
}
#else
/* Preserve the disabled profile's existing DWARF source coordinates. */
#line 23
#endif
int main(int argc,char **argv) {
    unsigned mode=argc>1 && argv && argv[1]?(unsigned char)argv[1][0]:0;
    int64_t pid=reist_x64_syscall0(REIST_X64_SYS_GETPID);
    if(pid<=0 || pid>0x7fffffff)return 250;
    reist_display_request_v1 r={1,64,REIST_DISPLAY_QUERY,0,(uint64_t)pid<<32|4,0,0,0,0,0,0,0,0};
    uint64_t end=now()+200;int64_t epoch=-13;
    for(unsigned n=0;n<20 && now()<end;n++) {
        epoch=call(&r);if(epoch!=-13)break;
        if(reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,10))return 250;
    }
    if(epoch<=0)return 249;
    int lease=-11;
    for(unsigned n=0;n<20 && now()<end;n++) {
        lease=reist_x64_terminal_input(REIST_TERMINAL_CHECK,0,0);if(lease!=-11)break;
        if(reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,10))return 250;
    }
    if(lease)return 248;
#ifdef REIST_NATIVE_DISPLAY_INFO
    if(!info_test(r.owner,(uint64_t)epoch))return 235;
#else
#line 40
#endif
    for(unsigned y=0;y<64;y++)for(unsigned x=0;x<64;x++)
        pixels[y*64+x]=(x*4u<<16)|(y*4u<<8)|0x5a;
    r.operation=REIST_DISPLAY_COMMIT;r.epoch=(uint64_t)epoch;
    r.deadline_ms=now()+200;r.pixels=(uintptr_t)pixels;
    r.x=32;r.y=32;r.width=64;r.height=64;r.stride=256;
    if(mode=='s') {
        r.epoch--;if(call(&r)!=-116)return 240;r.epoch++;
        r.x=UINT32_MAX;if(call(&r)!=-22)return 241;r.x=32;
        r.pixels=UINT64_MAX;if(call(&r)!=-14)return 242;r.pixels=(uintptr_t)pixels;
        r.flags=1;if(call(&r)!=-22)return 243;r.flags=0;
        r.deadline_ms=now();if(call(&r)!=-110)return 244;r.deadline_ms=now()+200;
    }
    if(call(&r))return 247;
    if(!output("DISPLAY_CLIENT_OK\n",18))return 246;
    if(mode=='u')__builtin_trap();
    if(mode=='q')for(;;)__asm__ volatile("pause");
    if(mode=='c') {
        for(unsigned n=0;n<20;n++)if(reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,100))return 245;
        return 245;
    }
    if(mode=='b') {
        r.width=r.height=1;r.stride=4;r.deadline_ms=now()+200;
        int64_t status=0;
        for(unsigned n=0;n<65;n++){status=call(&r);if(status)break;}
        if(status!=-122)return 239;
        if(call(&r)!=-13)return 238;
        if(!output("DISPLAY_QUOTA_FENCED\n",21))return 237;
    }
    if(reist_x64_terminal_input(REIST_TERMINAL_RELEASE,0,0))return 236;
    return 82;
}
