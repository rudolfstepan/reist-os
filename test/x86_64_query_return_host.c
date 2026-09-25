#include <stdio.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){fprintf(stderr,"query failure line %u\n",__LINE__);return 1;}}while(0)
int main(void) {
    reist_native_query_state q={0},zero={0},before;
    CHECK(!qr_reset(0));
    CHECK(!qr_bind(0,0,1));
    CHECK(qr_take(0,0,1)==-1);
    for(unsigned slot=0;slot<8;slot++) {
        CHECK(qr_reset(&q)==1);
        CHECK(!memcmp(&q,&zero,sizeof(q)));
        CHECK(qr_bind(&q,slot,0x7fffffff)==1);
        CHECK(q.generation==0x7fffffff && q.slot==slot && q.remaining==8);
        before=q;CHECK(!qr_bind(&q,slot,1));
        CHECK(!memcmp(&q,&before,sizeof(q)));
        CHECK(qr_take(&q,slot,1)==-1);
        CHECK(qr_take(&q,slot^1,0x7fffffff)==-1);
        CHECK(!memcmp(&q,&before,sizeof(q)));
        for(unsigned n=0;n<7;n++) {
            CHECK(qr_take(&q,slot,0x7fffffff)==1);
            CHECK(q.remaining==7-n && q.inverse_remaining==~q.remaining);
        }
        before=q;
        for(unsigned n=0;n<64;n++)CHECK(qr_take(&q,slot,0x7fffffff)==0);
        CHECK(!memcmp(&q,&before,sizeof(q)));
        CHECK(qr_reset(&q)==1);
        CHECK(qr_bind(&q,slot,1)==1);
        before=q;CHECK(qr_take(&q,slot,0x7fffffff)==-1);
        CHECK(!memcmp(&q,&before,sizeof(q)));
    }
    CHECK(qr_reset(&q));
    CHECK(!qr_bind(&q,8,1));
    CHECK(!qr_bind(&q,0,0));
    CHECK(!qr_bind(&q,0,0x80000000ULL));
    CHECK(!memcmp(&q,&zero,sizeof(q)));
    CHECK(qr_take(&q,0,1)==-1);
    CHECK(qr_bind(&q,4,19));
    reist_native_query_state valid=q;
    for(unsigned bit=0;bit<sizeof(q)*8;bit++) {
        q=valid;((unsigned char *)&q)[bit/8]^=1U<<(bit%8);before=q;
        CHECK(qr_take(&q,4,19)==-1);
        CHECK(!qr_reset(&q));
        CHECK(!memcmp(&q,&before,sizeof(q)));
    }
    q=valid;q.remaining=9;q.inverse_remaining=~q.remaining;before=q;
    CHECK(qr_take(&q,4,19)==-1);
    CHECK(!qr_reset(&q) && !memcmp(&q,&before,sizeof(q)));
    _Alignas(8) unsigned char misaligned[sizeof(q)+8];memset(misaligned,0,sizeof(misaligned));
    CHECK(!qr_reset((void *)(misaligned+1)));
    puts("NATIVE_QUERY_RETURN_OK");return 0;
}
