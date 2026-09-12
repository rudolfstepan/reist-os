/* Optional trusted C layout fixture: real code/objects beyond the old page. */
typedef unsigned int u32;
typedef unsigned long long u64;
extern u32 x86_64_c_serial_write64(const char *,u64);
__attribute__((section(".rodata.payload_probe")))
const unsigned char payload_ro[9000]={[0]=0x5a,[4096]=0xc3,[8999]=0x7e};
__attribute__((section(".data.payload_probe")))
volatile unsigned char payload_data[9000]={[0]=0x71,[4096]=0x92,[8999]=0xe3};
__attribute__((section(".bss.payload_probe")))
volatile unsigned char payload_bss[12000];
static const char payload_ok[]="REIST_X86_64_C_PAYLOAD_PAGES_OK\r\n";
__attribute__((section(".text.payload_probe"),noinline))
u32 x86_64_c_payload_probe(void) {
    /* Executed instructions cross a4KiB boundary; not an unused padding blob. */
    __asm__ volatile(".rept 4608\n nop\n .endr" ::: "memory");
    u32 ok=1;
    const volatile unsigned char *ro=payload_ro;
    for(u32 i=0;i<9000;++i) {
        unsigned char r=i==0?0x5a:i==4096?0xc3:i==8999?0x7e:0;
        unsigned char d=i==0?0x71:i==4096?0x92:i==8999?0xe3:0;
        if(ro[i]!=r || payload_data[i]!=d)ok=0;
    }
    for(u32 i=0;i<12000;++i)if(payload_bss[i]!=0)ok=0;
    for(u32 i=0;i<12000;++i)payload_bss[i]=(unsigned char)(i^0xa5);
    for(u32 i=0;i<12000;++i)if(payload_bss[i]!=(unsigned char)(i^0xa5))ok=0;
    for(u32 i=0;i<12000;++i)payload_bss[i]=0;
    for(u32 i=0;i<9000;++i)payload_data[i]=0;
    if(ok && x86_64_c_serial_write64(payload_ok,sizeof(payload_ok)-1)!=1)ok=0;
    return ok;
}
