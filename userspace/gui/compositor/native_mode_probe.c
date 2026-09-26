/* Hardware prerequisite surface, explicitly not the full desktop. */
#include <reist/x86_64/syscall.h>
#include <reist/x86_64/display.h>
static uint32_t tile[4096];
static uint64_t now(void) {
    int64_t t=reist_x64_syscall0(REIST_X64_SYS_MONOTONIC_MS);
    if(t<0)__builtin_trap();return (uint64_t)t;
}
static int wait_ms(unsigned t) {return (int)reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,t);}
int main(int argc,char **argv) {
    (void)argv;if(argc!=1)return 22;
    int64_t pid=reist_x64_syscall0(REIST_X64_SYS_GETPID);
    if(pid<1||pid>0x7fffffff)return 71;
    uint64_t owner=(uint64_t)pid<<32|4,epoch=0,end=now()+2000;
    for(unsigned n=0;n<200&&now()<end;n++) {
        reist_display_request_v1 q={1,64,REIST_DISPLAY_QUERY,0,owner,0,0,0,0,0,0,0,0};
        int64_t r=reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,30,(uintptr_t)&q);
        if(r>0){epoch=(uint64_t)r;break;}
        if(r!=-19&&r!=-116&&r!=-32&&r!=-13)return 71;
        if(wait_ms(10))return 5;
    }
    if(!epoch)return 110;
    end=now()+2000;
    for(unsigned index=0;index<192;index++) {
        unsigned column=index%16,row=index/16;
        uint32_t color=column<5?0x00336699:column<11?0x00339966:0x00996633;
        for(unsigned i=0;i<4096;i++)tile[i]=color;
        reist_display_request_v1 q={1,64,REIST_DISPLAY_COMMIT,0,owner,epoch,now()+100,
                                    (uintptr_t)tile,column*64,row*64,64,64,256};
        int64_t r=reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,30,(uintptr_t)&q);
        if(r)return r>=-4095?(int)-r:71;
        if(now()>=end)return 110;
        /* Four16KiB tiles per10ms stay below64 commits/1MiB per100ms. */
        if(index%4==3&&wait_ms(10))return 5;
    }
    for(unsigned n=0;n<10;n++)if(wait_ms(100))return 5;
    return 0;
}
