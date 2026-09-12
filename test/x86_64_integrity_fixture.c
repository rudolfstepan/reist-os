/* Trusted boot-only consumer of the UNCHANGED shared integrity implementation. */
#include "include/kernel/critical_object.h"
#include "arch/x86/include/interrupt.h"

extern unsigned int x86_64_c_serial_write64(const char *,unsigned long long);
static critical_object_t specimen,original,other,snapshot;
static uint32_t input[16],output[16];
static size_t output_length;
static const char passed[]="REIST_X86_64_C_INTEGRITY_OK\r\n";
static uint32_t cases;
static int failed;
#define CHECK(test) do {if(!(test)){failed=__LINE__;goto cleanup;}} while(0)
static int same(const void *a,const void *b,size_t n) {
    const unsigned char *x=a,*y=b;
    for(size_t i=0;i<n;++i)if(x[i]!=y[i])return 0;
    return 1;
}
static void zero(void *p,size_t n) {
    volatile unsigned char *b=p;for(size_t i=0;i<n;++i)b[i]=0;
}
static bool semantic(const void *p,size_t n) {
    return n==sizeof(input) && ((const uint32_t *)p)[0]==0x10203040U;
}
__attribute__((noinline)) void reist_x64_integrity_checkpoint(
    uint64_t phase,const critical_object_t *object,int64_t result,uint64_t count) {
    __asm__ volatile("" :: "r"(phase),"r"(object),"r"(result),"r"(count) : "memory");
}
static int read_value(size_t capacity,uint32_t version,critical_object_validator_t validator) {
    for(unsigned i=0;i<16;++i)output[i]=0x5a5a5a5aU;
    output_length=99;++cases;
    return critical_object_read(&specimen,version,output,capacity,&output_length,validator);
}
static int unchanged(void) {
    if(!same(&snapshot,&specimen,sizeof(specimen)) || output_length!=99)return 0;
    for(unsigned i=0;i<16;++i)if(output[i]!=0x5a5a5a5aU)return 0;
    return 1;
}
/* Independent bit-walk builds a VALID max-sequence fixture only. Production
 * encoding/decoding/selection remains the shared implementation, unchanged. */
static void max_sequence(critical_object_copy_t *copy) {
    copy->words[1]=0xffffffffU;
    for(unsigned word=0;word<CRITICAL_OBJECT_WORDS;++word) {
        unsigned code=0,parity=0,bit=0;
        for(unsigned position=1;position<=38;++position) {
            if((position&(position-1))==0)continue;
            if((copy->words[word]>>bit)&1U){code^=position;parity^=1;}
            ++bit;
        }
        for(unsigned i=0;i<6;++i)parity^=(code>>i)&1U;
        copy->ecc[word]=(uint8_t)(code|(parity<<6));
    }
    uint32_t crc=0xffffffffU;
    const uint8_t *bytes=(const uint8_t *)copy;
    for(unsigned i=0;i<100;++i) {
        crc^=bytes[i];
        for(unsigned bit=0;bit<8;++bit)crc=(crc>>1)^((0U-(crc&1U))&0xedb88320U);
    }
    copy->crc32=crc^0xffffffffU;
}
static uint8_t port_read(uint16_t port) {
    uint8_t value;__asm__ volatile("inb %1,%0":"=a"(value):"Nd"(port));return value;
}
static void port_write(uint16_t port,uint8_t value) {
    __asm__ volatile("outb %0,%1"::"a"(value),"Nd"(port):"memory");
}
/* No IRQ can arrive during the IF=1 proof: both saved PIC masks restored. */
static int enabled_irq_roundtrip(void) {
    uint8_t master=port_read(0x21),slave=port_read(0xa1);
    port_write(0x21,0xff);port_write(0xa1,0xff);
    volatile uint64_t guard[2];
    guard[0]=0x1020304050607080ULL;guard[1]=0xfedcba9876543210ULL;
    uint64_t before,after;
    __asm__ volatile("mov %%rsp,%0":"=r"(before)::"memory");
    irq_enable();
    int enabled=irq_enabled();
    uint32_t token=irq_save();
    int disabled=irq_enabled();
    irq_restore(token);
    int restored=irq_enabled();
    int result=read_value(sizeof(output),7,semantic);
    int maintained=irq_enabled();
    irq_disable();
    __asm__ volatile("mov %%rsp,%0":"=r"(after)::"memory");
    port_write(0xa1,slave);port_write(0x21,master);
    return enabled==1 && (token&0x200)!=0 && disabled==0 && restored==1 && maintained==1 &&
        result==CRITICAL_READ_OK && before==after && guard[0]==0x1020304050607080ULL && guard[1]==0xfedcba9876543210ULL;
}
unsigned int x86_64_c_integrity_probe(void) {
    failed=0;cases=0;
    CHECK(!irq_enabled());
    for(unsigned i=0;i<16;++i)input[i]=0x10203040U+i;
    CHECK(sizeof(critical_object_copy_t)==104 && sizeof(critical_object_t)==212);
    CHECK(critical_object_init(&specimen,7,input,sizeof(input))==0);
    original=specimen;
    CHECK(read_value(sizeof(output),7,semantic)==CRITICAL_READ_OK);
    CHECK(output_length==64 && same(input,output,64));
    reist_x64_integrity_checkpoint(1,&specimen,0,cases);
    for(unsigned which=0;which<2;++which)for(unsigned word=0;word<20;++word)for(unsigned bit=0;bit<39;++bit) {
        specimen=original;
        critical_object_copy_t *copy=which?&specimen.shadow:&specimen.primary;
        if(bit<32)copy->words[word]^=1U<<bit;else copy->ecc[word]^=(uint8_t)(1U<<(bit-32));
        CHECK(read_value(sizeof(output),7,semantic)==CRITICAL_READ_CORRECTED);
        CHECK(output_length==64 && same(input,output,64) && specimen.publication_lock==0);
    }
    reist_x64_integrity_checkpoint(2,&specimen,1,cases);
    for(unsigned which=0;which<2;++which)for(unsigned word=0;word<20;++word)for(unsigned fault=0;fault<2;++fault) {
        specimen=original;
        critical_object_copy_t *copy=which?&specimen.shadow:&specimen.primary;
        if(fault)copy->ecc[word]^=128;else copy->words[word]^=3;
        CHECK(read_value(sizeof(output),7,semantic)==CRITICAL_READ_RECOVERED);
        CHECK(output_length==64 && same(input,output,64));
    }
    reist_x64_integrity_checkpoint(3,&specimen,2,cases);
    specimen=original;specimen.primary.crc32^=1;specimen.shadow.crc32^=2;snapshot=specimen;
    CHECK(read_value(sizeof(output),7,semantic)==CRITICAL_READ_UNCORRECTABLE && unchanged());
    reist_x64_integrity_checkpoint(4,&specimen,-1,cases);
    input[1]^=1;CHECK(!critical_object_init(&other,7,input,sizeof(input)));input[1]^=1;
    specimen=original;specimen.shadow=other.primary;snapshot=specimen;
    CHECK(read_value(sizeof(output),7,semantic)==CRITICAL_READ_UNCORRECTABLE && unchanged());
    reist_x64_integrity_checkpoint(5,&specimen,-1,cases);
    specimen=original;snapshot=specimen;
    CHECK(read_value(63,7,semantic)==CRITICAL_READ_INVALID_ARGUMENT && unchanged());
    reist_x64_integrity_checkpoint(6,&specimen,-2,cases);
    CHECK(read_value(64,8,semantic)==CRITICAL_READ_UNCORRECTABLE && unchanged());
    reist_x64_integrity_checkpoint(7,&specimen,-1,cases);
    input[0]=0;CHECK(!critical_object_init(&specimen,7,input,64));input[0]=0x10203040U;snapshot=specimen;
    CHECK(read_value(64,7,semantic)==CRITICAL_READ_UNCORRECTABLE && unchanged());
    reist_x64_integrity_checkpoint(8,&specimen,-1,cases);
    specimen=original;max_sequence(&specimen.primary);specimen.shadow=specimen.primary;
    CHECK(read_value(64,7,semantic)==CRITICAL_READ_OK);snapshot=specimen;
    CHECK(critical_object_update(&specimen,7,input,64,semantic)==-1 && same(&snapshot,&specimen,sizeof(specimen)));
    reist_x64_integrity_checkpoint(9,&specimen,-1,cases);
    specimen=original;specimen.publication_lock=1;snapshot=specimen;
    CHECK(read_value(64,7,semantic)==CRITICAL_READ_UNCORRECTABLE && unchanged());
    CHECK(critical_object_update(&specimen,7,input,64,semantic)==-1 && unchanged());
    reist_x64_integrity_checkpoint(10,&specimen,-1,cases);
    specimen=original;input[1]^=1;
    CHECK(!critical_object_update(&specimen,7,input,64,semantic));
    specimen.primary=original.primary;
    CHECK(read_value(64,7,semantic)==CRITICAL_READ_OK && same(input,output,64) && specimen.primary.words[1]==2);
    reist_x64_integrity_checkpoint(11,&specimen,0,cases);
    CHECK(enabled_irq_roundtrip());
    CHECK(!irq_enabled());
    reist_x64_integrity_checkpoint(12,&specimen,0,cases);
cleanup:
    zero(&specimen,sizeof(specimen));zero(&original,sizeof(original));zero(&other,sizeof(other));zero(&snapshot,sizeof(snapshot));
    zero(input,sizeof(input));zero(output,sizeof(output));output_length=0;cases=0;
    if(failed)return 0;
    return x86_64_c_serial_write64(passed,sizeof(passed)-1)==1;
}
