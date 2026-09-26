/* Isolated prerequisite terminal driver. Shared mode policy is reusable by CB. */
#include "native_mode.h"
#include "../ps2/native_input.h"
#include <reist/x86_64/syscall.h>
#include <x86os.h>
static uint64_t owner,epoch,input_epoch;
static uint64_t now(void *unused) {
    (void)unused;int64_t t=reist_x64_syscall0(REIST_X64_SYS_MONOTONIC_MS);
    return t<0?UINT64_MAX:(uint64_t)t;
}
static int sleep_ms(void *unused,unsigned ms) {
    (void)unused;return (int)reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,ms);
}
static int64_t request(void *unused,unsigned op,unsigned step) {
    (void)unused;reist_video_request_v1 q={1,64,op,step,owner,op==REIST_VIDEO_QUERY?0:epoch,{0}};
    return reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,34,(uintptr_t)&q);
}
static int64_t input(void *unused,unsigned op,unsigned value,uint64_t end) {
    (void)unused;reist_input_request_v1 q={1,64,op,0,owner,input_epoch,end,value,{0,0}};
    return reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,31,(uintptr_t)&q);
}
static int hex(const char *s,uint32_t *out) {
    if(!s)return -22;uint32_t v=0;
    for(unsigned n=0;n<8;n++) {
        unsigned c=(unsigned char)s[n];
        if(c>='0'&&c<='9')c-='0';else if(c>='a'&&c<='f')c=c-'a'+10;else return -22;
        v=v*16+c;
    }
    if(s[8])return -22;*out=v;return 0;
}
static void fault(unsigned mode,unsigned crash,unsigned hang) {
    if(mode==crash)__asm__ volatile("ud2");
    if(mode==hang)for(;;)if(sleep_ms(0,20))__builtin_trap();
}
extern int reist_native_text_main(int,char **);
int main(int argc,char **argv) {
    if(argc==4)return reist_native_text_main(argc,argv);
    uint32_t hi,lo,endpoint;
    if(argc!=5 || hex(argv[1],&hi) || hex(argv[2],&lo) || hex(argv[3],&endpoint) ||
       !argv[4] || argv[4][1])return 22;
    unsigned mode=(unsigned char)argv[4][0];
    if(mode!='0'&&mode!='p'&&mode!='P'&&mode!='g'&&mode!='G'&&mode!='r'&&mode!='R')return 22;
    uint64_t end=(uint64_t)hi<<32|lo;
    if(now(0)>=end || end-now(0)>2000)return 110;
    int64_t pid=reist_x64_syscall0(REIST_X64_SYS_GETPID);
    if(pid<1||pid>0x7fffffff)return 71;owner=(uint64_t)pid<<32|5;
    for(unsigned n=0;n<200&&now(0)<end;n++) {
        int64_t v=request(0,REIST_VIDEO_QUERY,0);
        if(v>0){epoch=(uint64_t)v;break;}
        if(v!=-116&&v!=-32)return 71;
        if(sleep_ms(0,10))return 5;
    }
    if(!epoch)return 110;
    int64_t ie=input(0,REIST_INPUT_QUERY,0,0);if(ie<=0)return 71;input_epoch=(uint64_t)ie;
    reist_ps2_transport keyboard={0,now,input,sleep_ms};
    uint64_t setup=now(0)+1000;if(setup>end)setup=end;
    if(reist_ps2_initialize(&keyboard,setup))return 71;
    fault(mode,'p','P');
    reist_video_transport transport={0,now,request};
    int r=reist_video_enter(&transport,end);if(r)return -r;
    uint64_t heartbeat=now(0),graphic_fault=heartbeat+250,finish=end+5000;
    for(unsigned n=0;n<700&&now(0)<finish;n++) {
        uint64_t stamp=now(0);
        if(stamp>=graphic_fault)fault(mode,'g','G');
        if(stamp-heartbeat>=250) {
            if(request(0,REIST_VIDEO_HEARTBEAT,0))return 110;
            heartbeat=stamp;
        }
        x86os_ipc_message_t message={0};message.version=1;message.struct_size=140;message.length=128;
        int64_t received=reist_x64_syscall3(REIST_X64_SYS_IPC_RECEIVE_TIMEOUT,endpoint,(uintptr_t)&message,0);
        if(!received) {
            if(message.version!=1||message.struct_size!=140||message.length!=1||message.payload[0]!='q')return 71;
            for(unsigned i=1;i<128;i++)if(message.payload[i])return 71;
            fault(mode,'r','R');
            return reist_video_leave(&transport,now(0)+2000)?5:0;
        }
        if(received!=-11)return 71;
        if(sleep_ms(0,10))return 5;
    }
    fault(mode,'r','R');
    return reist_video_leave(&transport,now(0)+2000)?5:0;
}
