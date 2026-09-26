/* Persistent, isolated text console; all protocol and layout policy is Ring3. */
#include "text.h"
#include "../ps2/native_input.h"
#include <reist/x86_64/syscall.h>
#include <reist/x86_64/vga_console.h>

static reist_vga_text text;
static uint16_t published[1920];
static reist_ps2_decoder decoder;
static uint64_t owner,epoch,input_epoch;
static uint64_t now_ms(void *unused) {
    (void)unused;
    int64_t r=reist_x64_syscall0(REIST_X64_SYS_MONOTONIC_MS);
    return r<0?UINT64_MAX:(uint64_t)r;
}
static int sleep_ms(void *unused,unsigned ms) {
    (void)unused;
    return (int)reist_x64_syscall1(REIST_X64_SYS_SLEEP_MS,ms);
}
static int64_t vga(unsigned op,void *buffer,unsigned count,unsigned offset) {
    reist_vga_request_v1 q={1,64,op,0,owner,op==REIST_VGA_QUERY?0:epoch,
                            (uintptr_t)buffer,count,offset,{0,0}};
    return reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,REIST_VGA_RESOURCE,(uintptr_t)&q);
}
static int64_t input(void *unused,unsigned op,unsigned value,uint64_t end) {
    (void)unused;
    reist_input_request_v1 q={1,64,op,0,owner,input_epoch,end,value,{0,0}};
    return reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,31,(uintptr_t)&q);
}
static int hex(const char *s,uint32_t *out) {
    uint32_t value=0;
    if(!s)return -22;
    for(unsigned i=0;i<8;i++) {
        unsigned c=(unsigned char)s[i];
        if(c>='0'&&c<='9') c-='0';
        else if(c>='a'&&c<='f') c=c-'a'+10;
        else return -22;
        value=(value<<4)|c;
    }
    if(s[8])return -22;
    *out=value; return 0;
}
static unsigned key_bytes(const reist_input_event_v1 *e,uint8_t out[3]) {
    static const char plain[89]="\0\0331234567890-=\b\tqwertyuiop[]\n\0asdfghjkl;'`\0\\zxcvbnm,./\0*\0 \0";
    static const char shifted[89]="\0\033!@#$%^&*()_+\b\tQWERTYUIOP{}\n\0ASDFGHJKL:\"~\0|ZXCVBNM<>?\0*\0 \0";
    if(e->type!=REIST_INPUT_KEY || e->code<1 || e->code>88 || (e->flags&1))return 0;
    if(e->flags&2) {
        unsigned char c=e->code==0x48?'A':e->code==0x50?'B':e->code==0x4d?'C':e->code==0x4b?'D':0;
        if(c){out[0]=27;out[1]='[';out[2]=c;return 3;}
        if(e->code==0x1c){out[0]='\n';return 1;}
        if(e->code==0x53){out[0]=127;return 1;}
        return 0;
    }
    uint8_t c=(uint8_t)((e->flags&4)?shifted[e->code]:plain[e->code]);
    if(e->flags&32) {
        if(c>='a'&&c<='z')c-=32;
        else if(c>='A'&&c<='Z')c+=32;
    }
    if(e->flags&8) {
        if(c>='a'&&c<='z')c=(uint8_t)(c-'a'+1);
        else if(c>='A'&&c<='Z')c=(uint8_t)(c-'A'+1);
    }
    out[0]=c; return c?1:0;
}
int main(int argc,char **argv) {
    uint32_t hi,lo;
    if(argc!=4||hex(argv[1],&hi)||hex(argv[2],&lo)||!argv[3]||argv[3][1]||
       (argv[3][0]!='0'&&argv[3][0]!='u'&&argv[3][0]!='h'))return 22;
    unsigned mode=(unsigned char)argv[3][0];
    uint64_t end=(uint64_t)hi<<32|lo, now=now_ms(0);
    if(now>=end||end-now>2000)return 110;
    int64_t pid=reist_x64_syscall0(REIST_X64_SYS_GETPID);
    if(pid<1||pid>0x7fffffff)return 71;
    owner=(uint64_t)pid<<32|4;
    for(unsigned tries=0;tries<200&&now_ms(0)<end;tries++) {
        int64_t r=vga(REIST_VGA_QUERY,0,0,0);
        if(r>0) { epoch=(uint64_t)r; break; }
        if(r!=-116&&r!=-32)return 71;
        if(sleep_ms(0,10))return 5;
    }
    if(!epoch)return 110;
    for(unsigned tries=0;tries<200&&now_ms(0)<end;tries++) {
        int64_t r=input(0,REIST_INPUT_QUERY,0,0);
        if(r>0) { input_epoch=(uint64_t)r; break; }
        if(r!=-13)return 71;
        if(sleep_ms(0,10))return 5;
    }
    if(!input_epoch)return 110;
    reist_vga_text_init(&text);
    reist_ps2_clear(&decoder);
    reist_ps2_transport transport={0,now_ms,input,sleep_ms};
    uint64_t setup=now_ms(0)+1000;
    if(setup>end)setup=end;
    if(reist_ps2_initialize(&transport,setup))return 71;
    if(vga(REIST_VGA_HEARTBEAT,0,0,0))return 110;
    uint64_t heartbeat=now_ms(0),last=heartbeat,pending_end=0;
    const uint64_t fault_at=heartbeat+500;
    unsigned scan=0,pending_count=0,published_cursor=UINT32_MAX;
    uint8_t pending[3]={0};
    for(;;) {
        now=now_ms(0);
        if(now<last||now>UINT64_MAX-1000)return 75;
        last=now;
        /* Explicit supervisor-selected qualification faults; healthy mode 0
         * never enters them. The ordinary supervisor must fence/reap us. */
        if(now>=fault_at&&mode=='u')__asm__ volatile("ud2");
        if(now>=fault_at&&mode=='h') {
            for(;;)if(sleep_ms(0,20))return 5;
        }
        if(now-heartbeat>=250) {
            if(vga(REIST_VGA_HEARTBEAT,0,0,0))return 110;
            heartbeat=now;
        }
        uint8_t output[64];
        int64_t got=vga(REIST_VGA_READ_OUTPUT,output,64,0);
        if(got>64||(got<0&&got!=-11))return 71;
        for(int64_t i=0;i<got;i++) {
            /* Shell console output processing: LF implies CR, like ONLCR. */
            if(output[i]=='\n'&&reist_vga_text_byte(&text,'\r'))return 84;
            if(reist_vga_text_byte(&text,output[i]))return 84;
        }
        for(unsigned budget=0;budget<2;budget++) {
            unsigned row=scan;
            scan=(scan+1)%24;
            int changed=0;
            for(unsigned x=0;x<80;x++) if(text.cells[row*80+x]!=published[row*80+x])changed=1;
            if(!changed)continue;
            if(vga(REIST_VGA_WRITE_CELLS,&text.cells[row*80],80,row*80))return 71;
            for(unsigned x=0;x<80;x++)published[row*80+x]=text.cells[row*80+x];
        }
        unsigned cursor=text.row*80+text.column;
        if(cursor!=published_cursor) {
            int painted=1;
            for(unsigned x=0;x<80;x++)
                if(text.cells[text.row*80+x]!=published[text.row*80+x])painted=0;
            if(painted) {
                if(vga(REIST_VGA_SET_CURSOR,0,0,cursor))return 71;
                published_cursor=cursor;
            }
        }
        if(pending_count) {
            if(now>=pending_end)return 110;
            int64_t r=vga(REIST_VGA_WRITE_INPUT,pending,pending_count,0);
            if(r==(int64_t)pending_count)pending_count=0;
            else if(r!=-11)return 71;
        }
        /* Stop reading hardware while a decoded key is back-pressured. */
        if(!pending_count) {
            int64_t sample=input(0,REIST_INPUT_READ,0,now+100);
            if(sample>0&&sample<=65536) {
                unsigned pair=(unsigned)(sample-1);
                reist_input_event_v1 event={0};
                int decoded=reist_ps2_decode(&decoder,(uint8_t)(pair>>8),(uint8_t)pair,now,&event);
                if(decoded<0)return 71;
                if(decoded)pending_count=key_bytes(&event,pending);
                if(pending_count)pending_end=now+1000;
            } else if(sample!=-11)return 71;
        }
        if((decoder.keyboard_end&&now>=decoder.keyboard_end)||
           (decoder.mouse_end&&now>=decoder.mouse_end))return 110;
        if(sleep_ms(0,10))return 5;
    }
}
