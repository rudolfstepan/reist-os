/* Ordinary foreground consumer. No port access; bounded IPC and display. */
#include <x86os.h>
#include <reist/x86_64/syscall.h>
#include <reist/x86_64/terminal.h>
#include <reist/x86_64/display.h>
#include <reist/x86_64/input.h>
static uint32_t pixels[64*64];
static const unsigned char image_padding[4096] __attribute__((used))={0x44};
static void zero(void *p,unsigned n){unsigned char *b=p;while(n--)*b++=0;}
static uint64_t now(void){int64_t t=reist_x64_syscall0(REIST_X64_SYS_MONOTONIC_MS);if(t<0)__builtin_trap();return (uint64_t)t;}
static int hex(const char *s,uint32_t *v){*v=0;if(!s)return -22;for(unsigned n=0;n<8;n++){unsigned c=(unsigned char)s[n];if(!c)return -22;unsigned d=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:16;if(d>15)return -22;*v=*v<<4|d;}return s[8]?-22:0;}
static int output(const char *s,unsigned count) {
    uint64_t end=now()+200;unsigned done=0;
    for(unsigned n=0;n<32&&done<count&&now()<end;n++) {
        unsigned chunk=count-done;if(chunk>64)chunk=64;
        int64_t r=reist_x64_syscall3(REIST_X64_SYS_WRITE,1,(uintptr_t)(s+done),chunk);
        if(r==-11){if(reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,10))return 0;continue;}
        if(r<=0||(uint64_t)r>chunk)return 0;done+=(unsigned)r;
    }
    return done==count;
}
static int record(const reist_input_event_v1 *e) {
    char text[145];const char prefix[]="INPUT_EVENT v1=";unsigned at=0;
    for(unsigned n=0;n<sizeof(prefix)-1;n++)text[at++]=prefix[n];
    for(unsigned n=0;n<64;n++){unsigned b=((const unsigned char*)e)[n];text[at++]="0123456789abcdef"[b>>4];text[at++]="0123456789abcdef"[b&15];}
    text[at++]='\n';return output(text,at);
}

#ifdef REIST_NATIVE_TERMINAL_SERVICE
/* Private diagnostic modes: the supervisor keeps the ordinary fixed budgets. */
static int service_fault(unsigned mode) {
    if(mode=='c')__builtin_trap();
    if(mode=='d')for(;;)__asm__ volatile("pause");
    for(unsigned n=0;n<60;n++)if(reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,100))return 5;
    return 110;
}
#endif
int main(int argc,char **argv) {
    uint32_t endpoint,hi,lo;if(argc!=5||!argv||hex(argv[2],&endpoint)||hex(argv[3],&hi)||hex(argv[4],&lo))return 22;
    int64_t pid=reist_x64_syscall0(REIST_X64_SYS_GETPID);if(pid<=0||pid>0x7fffffff)return 22;
    uint64_t target=(uint64_t)pid<<32|4,end=(uint64_t)hi<<32|lo,t=now();
    if(end<4000||end<=t||end-t>5000)return 22;
    uint64_t startup_end=end-4000,owner=0,epoch=0,sequence=0;
    reist_display_request_v1 r={1,64,REIST_DISPLAY_QUERY,0,target,0,0,0,0,0,0,0,0};
    int64_t display=-13;int lease=-11;
    for(unsigned n=0;n<100&&now()<startup_end;n++) {
        display=reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,30,(uintptr_t)&r);
#ifdef REIST_NATIVE_TERMINAL_SERVICE
        if(display>0)lease=reist_x64_terminal_input(REIST_TERMINAL_ACQUIRE_SERVICE,0,0);
        if(lease==-13)lease=-11;
#else
        if(display>0)lease=reist_x64_terminal_input(REIST_TERMINAL_CHECK,0,0);
#endif
        if(display>0&&!lease)break;
        if((display<=0&&display!=-13)||(lease&&lease!=-11))return 71;
        if(reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,10))return 5;
    }
    if(display<=0||lease)return 110;
#ifdef REIST_NATIVE_TERMINAL_SERVICE
    if(reist_x64_terminal_input(REIST_TERMINAL_CHECK,0,0) || !output("TERMINAL_SERVICE_OK\n",20))return 71;
#endif
    for(unsigned y=0;y<64;y++)for(unsigned x=0;x<64;x++)pixels[y*64+x]=(x*4u<<16)|(y*4u<<8)|0x5a;
    r.operation=REIST_DISPLAY_COMMIT;r.epoch=(uint64_t)display;r.deadline_ms=now()+200;
    r.pixels=(uintptr_t)pixels;r.x=32;r.y=32;r.width=64;r.height=64;r.stride=256;
    if(reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,30,(uintptr_t)&r)||!output("DISPLAY_CLIENT_OK\n",18))return 71;
    int px=128,py=128,status=82;
    /* Finish before the parent's immutable end to leave bounded cleanup time. */
    for(unsigned turn=0;turn<500&&now()+100<end;turn++) {
        t=now();uint64_t receive_end=sequence?end-100:startup_end;
        if(t>=receive_end){status=sequence?82:110;break;}
        unsigned wait=(unsigned)(receive_end-t>100?100:receive_end-t);
        x86os_ipc_message_t m;zero(&m,sizeof(m));m.version=1;m.struct_size=140;m.length=128;
        int64_t rc=reist_x64_syscall3(REIST_X64_SYS_IPC_RECEIVE_TIMEOUT,endpoint,(uintptr_t)&m,wait);
        if(rc==-110)continue;if(rc){status=71;break;}
        if(m.version!=1||m.struct_size!=140||m.length!=64){status=71;break;}
        unsigned bad=0;for(unsigned n=64;n<128;n++)bad|=m.payload[n];
        reist_input_event_v1 e;for(unsigned n=0;n<64;n++)((unsigned char*)&e)[n]=m.payload[n];
        if(bad||!reist_input_event_valid(&e,owner,target,epoch,sequence+1)){status=71;break;}
        owner=e.owner;epoch=e.epoch;sequence=e.sequence;
        if(!record(&e)){status=71;break;}
        if(e.type==REIST_INPUT_HEALTHY){if(!output("INPUT_READY\n",12)){status=71;break;}}
#ifdef REIST_NATIVE_TERMINAL_SERVICE
        if(e.type==REIST_INPUT_HEALTHY && argv[1] && !argv[1][1] &&
           (argv[1][0]=='c'||argv[1][0]=='d'||argv[1][0]=='e'))return service_fault((unsigned char)argv[1][0]);
#endif
        if(e.type==REIST_INPUT_ERROR){status=e.code==-122?122:e.code==-110?110:71;break;}
        if(e.type==REIST_INPUT_POINTER) {
            px+=e.dx;py-=e.dy;if(px<0)px=0;if(px>736)px=736;if(py<0)py=0;if(py>536)py=536;
            for(unsigned n=0;n<64*64;n++)pixels[n]=e.buttons?0x00ff9000:0x0000d0ff;
            r.x=(unsigned)px;r.y=(unsigned)py;r.deadline_ms=now()+100;
            if(reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,30,(uintptr_t)&r)){status=71;break;}
        }
        if(sequence==32){status=122;break;}
    }
    if(!sequence)status=110;
    if(!output("INPUT_END\n",10))return 71;
    if(reist_x64_terminal_input(REIST_TERMINAL_RELEASE,0,0))return 71;
    return status;
}
