/**
 * @file test/test_critical_object_host.c
 * @brief Hostseitiger Regressionstest für critical object.
 *
 * Layer: Host test harness.
 * Contract: Prüft beobachtbares Verhalten und feste Fehlergrenzen ohne Zielhardware.
 * Safety: Testdoubles dürfen Produktionsverträge nicht abschwächen oder Erfolg vortäuschen.
 */
#include "include/kernel/critical_object.h"

#include <stdint.h>

typedef struct { uint32_t limit; uint32_t mode; } sample_t;

static bool valid_sample(const void *payload, size_t length) {
    if (length != sizeof(sample_t)) return false;
    const sample_t *sample = (const sample_t *)payload;
    return sample->limit <= 1000U && sample->mode <= 3U;
}

#ifndef CRITICAL_EQUIVALENCE_TEST
int main(void) {
    critical_object_t object;
    sample_t input = {500U, 2U}, output = {0, 0};
    size_t length = 0;
    if (critical_object_init(&object, 1U, &input, sizeof(input)) != 0) return 1;
    if (critical_object_read(&object, 1U, &output, sizeof(output), &length,
                             valid_sample) != CRITICAL_READ_OK) return 2;
    if (output.limit != 500U || output.mode != 2U) return 3;

    object.primary.words[CRITICAL_OBJECT_METADATA_WORDS] ^= 1U << 7;
    if (critical_object_read(&object, 1U, &output, sizeof(output), &length,
                             valid_sample) != CRITICAL_READ_CORRECTED) return 4;
    if (output.limit != 500U) return 5;

    object.primary.words[CRITICAL_OBJECT_METADATA_WORDS] ^= 3U;
    if (critical_object_read(&object, 1U, &output, sizeof(output), &length,
                             valid_sample) != CRITICAL_READ_RECOVERED) return 6;
    if (output.limit != 500U) return 7;

    input.limit = 750U;
    if (critical_object_update(&object, 1U, &input, sizeof(input),
                               valid_sample) != 0) return 8;
    if (critical_object_read(&object, 1U, &output, sizeof(output), &length,
                             valid_sample) != CRITICAL_READ_OK) return 9;
    if (output.limit != 750U) return 10;

    object.primary.crc32 ^= 1U;
    object.shadow.crc32 ^= 2U;
    if (critical_object_read(&object, 1U, &output, sizeof(output), &length,
                             valid_sample) != CRITICAL_READ_UNCORRECTABLE) return 11;
    return 0;
}
#else
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <stdlib.h>
uint8_t reference_encode(uint32_t), candidate_encode(uint32_t);
int reference_decode(uint32_t*,uint8_t), candidate_decode(uint32_t*,uint8_t);
uint32_t reference_crc(const void*,size_t,uint32_t), candidate_crc(const void*,size_t,uint32_t);
int reference_init(critical_object_t*,uint32_t,const void*,size_t);
int reference_update(critical_object_t*,uint32_t,const void*,size_t,critical_object_validator_t);
critical_read_result_t reference_read(critical_object_t*,uint32_t,void*,size_t,size_t*,critical_object_validator_t);
static unsigned checks;
#define CHECK(x) do { ++checks; if(!(x)){fprintf(stderr,"critical equivalence:%d: %s\n",__LINE__,#x);exit(1);} } while(0)
static uint32_t random_word(uint32_t* seed) { return *seed=*seed*1664525U+1013904223U; }
static void compare_decode(uint32_t word,uint8_t code,int expected) {
    uint32_t a=word,b=word;
    int first=reference_decode(&a,code),second=candidate_decode(&b,code);
    CHECK(first==second && a==b);
    if(expected!=-2) CHECK(second==expected);
}
static void flip(uint32_t* word,uint8_t* code,unsigned bit) {
    if(bit<32)*word^=1U<<bit;else *code^=(uint8_t)(1U<<(bit-32));
}
static void codes(void) {
    uint32_t seed=0;
    /* Independently enumerate every byte contribution, including overlapping
     * random other bytes. Table-based arithmetic must match the original
     * bit-position walk for every entry, not just sampled complete words. */
    for(unsigned column=0;column<4;++column)for(unsigned byte=0;byte<256;++byte) {
        uint32_t word=(uint32_t)byte<<(8*column);
        CHECK(candidate_encode(word)==reference_encode(word));
        word|=random_word(&seed)&~(0xffU<<(8*column));
        CHECK(candidate_encode(word)==reference_encode(word));
        compare_decode(word,reference_encode(word),0);
        uint8_t value=(uint8_t)byte;
        uint32_t init=random_word(&seed);
        CHECK(candidate_crc(&value,1,init)==reference_crc(&value,1,init));
    }
    /* A linear encoding is determined by zero and its32 basis vectors.
     * Arbitrary words/codes and all39-bit one/two-bit cuts also exercise
     * nonlinear decoder decisions and the reserved eighth ECC bit. */
    for(unsigned sample=0;sample<160;++sample) {
        uint32_t word=sample==0 ? 0 : sample<=32 ? 1U<<(sample-1) : random_word(&seed);
        uint8_t code=reference_encode(word);
        CHECK(candidate_encode(word)==code);
        for(unsigned stored=0;stored<256;++stored)compare_decode(word,(uint8_t)stored,-2);
        compare_decode(word,code,0);
        for(unsigned i=0;i<39;++i) {
            uint32_t a=word;uint8_t c=code;flip(&a,&c,i);compare_decode(a,c,1);
            for(unsigned j=i+1;j<39;++j) {
                uint32_t b=a;uint8_t d=c;flip(&b,&d,j);compare_decode(b,d,-1);
            }
        }
        compare_decode(word,(uint8_t)(code|128U),-1);
    }
    uint8_t bytes[513];
    for(unsigned i=0;i<sizeof(bytes);++i)bytes[i]=(uint8_t)random_word(&seed);
    CHECK((candidate_crc("123456789",9,UINT32_MAX)^UINT32_MAX)==0xcbf43926U);
    for(unsigned n=0;n<=512;++n)for(unsigned offset=0;offset<2;++offset) {
        uint32_t init=random_word(&seed);
        CHECK(candidate_crc(bytes+offset,n,init)==reference_crc(bytes+offset,n,init));
        unsigned middle=n/2;
        CHECK(candidate_crc(bytes+offset+middle,n-middle,candidate_crc(bytes+offset,middle,init))==reference_crc(bytes+offset,n,init));
    }
}
static void compare_read(critical_object_t a,critical_object_t b,size_t capacity,uint32_t version,
                         critical_object_validator_t validator) {
    uint8_t left[64],right[64];memset(left,0x5a,64);memset(right,0x5a,64);
    size_t n=99,m=99;
    int r=reference_read(&a,version,left,capacity,&n,validator);
    int s=critical_object_read(&b,version,right,capacity,&m,validator);
    CHECK(r==s && n==m && !memcmp(left,right,64) && !memcmp(&a,&b,sizeof(a)));
}
static void objects(void) {
    uint8_t bytes[64];for(unsigned i=0;i<64;++i)bytes[i]=(uint8_t)(i*17+3);
    for(unsigned n=1;n<=64;++n) {
        critical_object_t a={0},b={0};
        CHECK(!reference_init(&a,7,bytes,n) && !critical_object_init(&b,7,bytes,n));
        CHECK(!memcmp(&a,&b,sizeof(a)));
        compare_read(a,b,n,7,NULL);compare_read(a,b,n-1,7,NULL);compare_read(a,b,n,8,NULL);
        CHECK(reference_update(&a,7,bytes,n,NULL)==critical_object_update(&b,7,bytes,n,NULL));
        CHECK(!memcmp(&a,&b,sizeof(a)));
    }
    critical_object_t original={0};
    CHECK(!critical_object_init(&original,7,bytes,64));
    for(unsigned bit=0;bit<sizeof(original.primary)*8;++bit)for(unsigned mode=0;mode<3;++mode) {
        critical_object_t fault=original;
        uint8_t* p=(uint8_t*)&fault.primary,*q=(uint8_t*)&fault.shadow;
        p[bit/8]^=(uint8_t)(1U<<(bit%8));
        if(mode==1)p[bit/8]^=(uint8_t)(1U<<((bit+1)%8));
        if(mode==2)q[bit/8]^=(uint8_t)(1U<<(bit%8));
        compare_read(fault,fault,64,7,NULL);
        critical_object_t other=fault;
        CHECK(reference_update(&fault,7,bytes,64,NULL)==critical_object_update(&other,7,bytes,64,NULL));
        CHECK(!memcmp(&fault,&other,sizeof(fault)));
    }
    sample_t good={500,2},bad={1001,4};
    critical_object_t a={0},b={0};
    CHECK(!critical_object_init(&a,1,&good,sizeof(good)));
    CHECK(!critical_object_init(&b,1,&bad,sizeof(bad)));
    compare_read(a,a,64,1,valid_sample);compare_read(b,b,64,1,valid_sample);
    a.shadow=b.primary;compare_read(a,a,64,1,NULL); /* same generation, conflicting valid copies */
    CHECK(!critical_object_update(&b,1,&good,sizeof(good),NULL));
    a.shadow=b.primary;compare_read(a,a,64,1,valid_sample); /* choose newest complete copy */
}
static void cost(void) {
    uint32_t input[16]={0};uint8_t out[64];size_t n=0;
    for(unsigned i=0;i<16;++i)input[i]=i*0xabcdef01U;
    critical_object_t object={0};const unsigned count=10000;
    CHECK(!reference_init(&object,1,input,sizeof(input)));
    clock_t start=clock();
    for(unsigned i=0;i<count;++i)CHECK(reference_read(&object,1,out,sizeof(out),&n,NULL)==0);
    double old=(double)(clock()-start)/CLOCKS_PER_SEC;
    CHECK(!critical_object_init(&object,1,input,sizeof(input)));start=clock();
    for(unsigned i=0;i<count;++i)CHECK(critical_object_read(&object,1,out,sizeof(out),&n,NULL)==0);
    double current=(double)(clock()-start)/CLOCKS_PER_SEC;
    printf("CRITICAL_COST reads=%u baseline_seconds=%.6f candidate_seconds=%.6f\n",count,old,current);
}
int main(void) { codes();objects();cost();printf("CRITICAL_EQUIVALENCE checks=%u\n",checks);return 0; }
#endif
