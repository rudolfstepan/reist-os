"""Execute actual PIO-v2 deadline admission and SDK at O0/O2."""
from pathlib import Path
import unittest
import test_x86_64_task_frames as host
ROOT=Path(__file__).resolve().parents[1]

class DeadlineTests(unittest.TestCase):
    def test_actual_deadline_before_effects(self):
        core=(ROOT/'arch/x86_64/devices/pio_domain.inc').read_text().split('; END_PIO_CORE')[0]
        sdk=(ROOT/'userspace/sdk/include/reist/x86_64/pio.h').read_text().replace('#include <reist/x86_64/syscall.h>','')
        c='''#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define REIST_SYS_DEVICE_CONTROL 113
static inline int64_t reist_x64_syscall2(unsigned n,uint64_t a,uint64_t b){return n+a+b;}
'''+sdk+'''
#define SYSV __attribute__((sysv_abi))
#define CHECK(x) do {if(!(x)){printf("FAIL line=%d\\n",__LINE__);return 1;}}while(0)
extern int64_t SYSV native_pio_admit64(const reist_native_pio_request *);
extern int64_t SYSV native_pio_apply64(uint64_t *,const reist_native_pio_request *,uint64_t,uint64_t,uint64_t);
static unsigned ports;
uint64_t SYSV native_pio_in8(uint64_t p){(void)p;ports++;return 64;}
uint64_t SYSV native_pio_in16(uint64_t p){(void)p;ports++;return 0x5a5a;}
void SYSV native_pio_out8(uint64_t p,uint64_t v){(void)p;(void)v;ports++;}
int main(void){
    uint64_t owner=0x300000002ULL;
    for(unsigned operation=2;operation<=4;operation++){
        uint16_t output[16];memset(output,0xaa,sizeof(output));
        reist_native_pio_request q={1,64,operation,0,owner,operation==4?0x1f0:0x1f7,operation==3?0x20:0,operation==4?16:0,0,operation==4?(uintptr_t)output:0,0,0};
        reist_native_pio_request v2,savedq=q;
        (void)reist_x64_pio(&q); /* Exercise the unchanged v1 transport wrapper. */
        CHECK(!reist_x64_pio_deadline_prepare(&v2,&q,110));
        CHECK(!memcmp(&q,&savedq,64) && v2.version==2 && reist_x64_pio_deadline_ms(&v2)==110);
        CHECK(native_pio_admit64(&v2)==1);
        for(unsigned n=0;n<6;n++){
            uint64_t state[8]={owner,~owner,0,10,10,0,10,0},before[8];memcpy(before,state,64);
            uint64_t deadline[]={1,109,110,1111,UINT64_MAX,0};v2.reserved1=deadline[n];unsigned old=ports;
            CHECK(native_pio_apply64(state,&v2,owner,11,0)==(n<3?-110:-22));
            CHECK(ports==old && !memcmp(state,before,64));
            for(unsigned i=0;i<16;i++)CHECK(output[i]==0xaaaa);
        }
        for(unsigned ms=111;ms<=1110;ms+=999){
            uint64_t state[8]={owner,~owner,0,10,10,0,10,0};v2.reserved1=ms;unsigned old=ports;
            CHECK(native_pio_apply64(state,&v2,owner,11,0)==(operation==2?64:0));
            CHECK(state[5]==1 && ports==old+(operation==4?16:1));
        }
        q.reserved1=111;CHECK(!native_pio_admit64(&q)); /* Old reserved stays reserved. */
        v2.reserved2=1;CHECK(!native_pio_admit64(&v2));v2.reserved2=0;
        v2.version=3;CHECK(!native_pio_admit64(&v2));v2.version=2;
        v2.operation=1;CHECK(!native_pio_admit64(&v2));v2.operation=5;CHECK(!native_pio_admit64(&v2));
        uint64_t state[8]={owner,~owner,0,10,10,0,10,0};v2=savedq;v2.version=2;v2.reserved1=110;
        CHECK(native_pio_apply64(state,&v2,owner+(1ULL<<32),11,0)==-13);
        CHECK(reist_x64_pio_deadline_prepare(&v2,&savedq,0)==-22);
    }
    puts("PIO_DEADLINE_HOST_OK");return 0;
}
'''
        asm='BITS 64\nsection .text\nextern native_pio_in8,native_pio_in16,native_pio_out8\n'+core
        host.TaskFrameTests().build(asm,c,'PIO_DEADLINE_HOST')

if __name__=='__main__':unittest.main()
