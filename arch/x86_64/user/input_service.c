/* PS/2 protocol and lifecycle live exclusively in this isolated Ring3 task. */
#include <x86os.h>
#include <reist/x86_64/syscall.h>
#include "../../../userspace/drivers/ps2/native_input.h"
static uint64_t owner,target,epoch,sequence,session_end;
static uint32_t endpoint;
static void zero(void *p,unsigned n){unsigned char *b=p;while(n--)*b++=0;}
static uint64_t clock_ms(void *p){(void)p;int64_t r=reist_x64_syscall0(REIST_X64_SYS_MONOTONIC_MS);if(r<0)__builtin_trap();return (uint64_t)r;}
static int sleep_ms(void *p,unsigned n){(void)p;return (int)reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,n);}
static int hex(const char *s,uint32_t *v){*v=0;if(!s)return -22;for(unsigned n=0;n<8;n++){unsigned c=(unsigned char)s[n];if(!c)return -22;unsigned d=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:16;if(d>15)return -22;*v=*v<<4|d;}return s[8]?-22:0;}
static int64_t transfer(void *p,unsigned op,unsigned value,uint64_t end) {
    (void)p;reist_input_request_v1 r={1,64,op,0,owner,epoch,end,value,{0,0}};
    return reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,31,(uintptr_t)&r);
}
static int publish(reist_input_event_v1 *event) {
    if(sequence==32)return -122;
    uint64_t now=clock_ms(0);if(now>=session_end)return -110;
    event->version=1;event->size=64;event->owner=owner;event->target=target;
    event->epoch=epoch;event->sequence=++sequence;
    x86os_ipc_message_t m;zero(&m,sizeof(m));m.version=1;m.struct_size=140;m.length=64;
    for(unsigned n=0;n<64;n++)m.payload[n]=((unsigned char*)event)[n];
    unsigned wait=(unsigned)(session_end-now>100?100:session_end-now);
    return (int)reist_x64_syscall3(REIST_X64_SYS_IPC_SEND_TIMEOUT,endpoint,(uintptr_t)&m,wait);
}
static int failure(reist_ps2_decoder *decoder,int error) {
    reist_ps2_clear(decoder);reist_input_event_v1 event;zero(&event,sizeof(event));
    event.type=REIST_INPUT_ERROR;event.code=error;
    (void)publish(&event);return error==-122?122:error==-110?110:71;
}
int main(int argc,char **argv) {
    uint32_t generation,hi,lo;
    if(argc!=6||!argv||hex(argv[1],&endpoint)||hex(argv[2],&generation)||hex(argv[3],&hi)||hex(argv[4],&lo)||!argv[5]||argv[5][1])return 22;
    int64_t pid=reist_x64_syscall0(REIST_X64_SYS_GETPID);
    if(pid<=0||pid>0x7fffffff||!generation||generation>0x7fffffff)return 22;
    owner=(uint64_t)pid<<32|5;target=(uint64_t)generation<<32|4;
    session_end=(uint64_t)hi<<32|lo;uint64_t now=clock_ms(0);
    if(session_end<4000||session_end<=now||session_end-now>5000)return 22;
    uint64_t startup_end=session_end-4000;
    reist_input_request_v1 query={1,64,REIST_INPUT_QUERY,0,owner,0,0,0,{0,0}};
    int64_t result=-13;
    for(unsigned n=0;n<100&&clock_ms(0)<startup_end;n++) {
        result=reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,31,(uintptr_t)&query);
        if(result!=-13)break;if(sleep_ms(0,10))return 5;
    }
    if(result<=0)return 110;epoch=(uint64_t)result;
    reist_ps2_decoder decoder;reist_ps2_clear(&decoder);
    reist_ps2_transport transport={0,clock_ms,transfer,sleep_ms};
    int r=reist_ps2_initialize(&transport,startup_end);if(r)return failure(&decoder,r);
    reist_input_event_v1 event;zero(&event,sizeof(event));event.type=REIST_INPUT_HEALTHY;
    if(publish(&event))return 71;
    unsigned mode=(unsigned char)argv[5][0];
    if(mode=='u')__builtin_trap();
    if(mode=='q')for(;;)__asm__ volatile("pause");
    if(mode=='h'){for(unsigned n=0;n<60;n++)if(sleep_ms(0,100))return 5;return 110;}
    if(mode=='s') {
        epoch--;result=transfer(0,REIST_INPUT_READ,0,clock_ms(0)+100);epoch++;
        if(result!=-116)return failure(&decoder,-71);
    }
    if(mode=='m') {r=reist_ps2_decode(&decoder,0xc1,0x1e,clock_ms(0),&event);return failure(&decoder,r);}
    if(mode=='b') {
        for(unsigned n=0;n<65;n++){result=transfer(0,REIST_INPUT_READ,0,clock_ms(0)+100);if(result==-122)break;if(result<0&&result!=-11)return failure(&decoder,-71);}
        if(result!=-122||transfer(0,REIST_INPUT_READ,0,clock_ms(0)+100)!=-13)return failure(&decoder,-71);
        return failure(&decoder,-122);
    }
    for(unsigned turn=0;turn<500&&clock_ms(0)+200<session_end;turn++) {
        now=clock_ms(0);
        if((decoder.keyboard_end&&now>=decoder.keyboard_end)||(decoder.mouse_end&&now>=decoder.mouse_end))return failure(&decoder,-110);
        for(unsigned n=0;n<8;n++) {
            now=clock_ms(0);if(now>=session_end)break;
            uint64_t end=session_end-now>100?now+100:session_end;
            result=transfer(0,REIST_INPUT_READ,0,end);
            if(result==-11)break;if(result<0)return failure(&decoder,(int)result);
            if(result==0||result>65536)return failure(&decoder,-71);
            unsigned raw=(unsigned)result-1;
            r=reist_ps2_decode(&decoder,(uint8_t)(raw>>8),(uint8_t)raw,now,&event);
            if(r<0)return failure(&decoder,r);
            if(r && (r=publish(&event)))return failure(&decoder,r);
        }
        if(sleep_ms(0,10))return failure(&decoder,-5);
    }
    reist_ps2_clear(&decoder);return 0;
}
