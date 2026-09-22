/* Actual shared SDK parser, including retained resolver transport tests. */
#define main retained_dns_main
#include "test_dns_host.c"
#undef main
#include <stdio.h>

static uint8_t packet[520];
static unsigned used;
static void u16(unsigned v) {packet[used++]=(uint8_t)(v>>8);packet[used++]=(uint8_t)v;}
static void u32(uint32_t v) {u16(v>>16);u16(v&65535);}
static void name(const char *s) {
    while(*s) {const char *p=s;while(*s&&*s!='.')s++;packet[used++]=(uint8_t)(s-p);
        while(p<s)packet[used++]=(uint8_t)*p++;if(*s)s++;}
    packet[used++]=0;
}
static void question(const char *s) {
    memset(packet,0,sizeof(packet));used=0;u16(0x1234);u16(0x8180);
    u16(1);u16(0);u16(0);u16(0);name(s);u16(1);u16(1);
}
static unsigned rr(const char *s,unsigned type,uint32_t ttl) {
    packet[7]++;name(s);u16(type);u16(1);u32(ttl);unsigned at=used;u16(0);return at;
}
static unsigned address(const char *s,uint32_t ttl) {
    unsigned at=rr(s,1,ttl);packet[at+1]=4;u32(0xc0000203);return at;
}
static unsigned alias(const char *s,const char *target,uint32_t ttl) {
    unsigned at=rr(s,5,ttl);name(target);packet[at+1]=(uint8_t)(used-at-2);return at;
}
static int check(int expected,uint32_t expected_ttl,const char *query,unsigned length) {
    uint32_t a=0xaaaaaaaa,t=0xbbbbbbbb;
    int rc=reist_dns_parse_response(packet,length,0x1234,query,&a,&t);
    if(rc!=expected) {printf("status=%d expected=%d length=%u\n",rc,expected,length);return 0;}
    return expected==0?(a==0xc0000203&&t==expected_ttl):(a==0xaaaaaaaa&&t==0xbbbbbbbb);
}
#define REJECT() CHECK(check(-74,0,"good.test",used))
int main(void) {
    CHECK(retained_dns_main()==0);
    question("evil.test");address("good.test",60);REJECT();
    question("good.test");address("good.test",60);CHECK(check(0,60,"GOOD.TEST.",used));
    for(unsigned n=0;n<used;n++)CHECK(check(-74,0,"good.test",n));
    CHECK(check(-74,0,"good.test",513));
    uint8_t original[520];memcpy(original,packet,sizeof(packet));
    for(unsigned n=0;n<5;n++) {
        memcpy(packet,original,sizeof(packet));
        if(n==0)packet[0]^=1; /* transaction */
        if(n==1)packet[2]&=0x7f; /* QR */
        if(n==2)packet[2]|=8; /* opcode */
        if(n==3)packet[2]|=2; /* TC */
        if(n==4)packet[3]|=0x40; /* reserved Z */
        REJECT();
    }
    memcpy(packet,original,sizeof(packet));packet[3]|=0x30;CHECK(check(0,60,"good.test",used));
    memcpy(packet,original,sizeof(packet));packet[3]|=3;REJECT();
    memcpy(packet,original,sizeof(packet));packet[5]=2;REJECT();
    memcpy(packet,original,sizeof(packet));packet[24]=2;REJECT(); /* QTYPE */
    memcpy(packet,original,sizeof(packet));packet[26]=2;REJECT(); /* QCLASS */
    memcpy(packet,original,sizeof(packet));packet[13]=0;REJECT();
    memcpy(packet,original,sizeof(packet));packet[13]='.';REJECT();
    memcpy(packet,original,sizeof(packet));packet[13]=0xff;REJECT();
    memcpy(packet,original,sizeof(packet));packet[used++]=0;REJECT();
    question("good.test");address("good.test",60);packet[7]++;packet[used++]=0;REJECT();
    question("good.test");address("good.test",60);packet[7]=0;packet[9]=1;CHECK(check(-2,0,"good.test",used));
    question("good.test");address("good.test",60);packet[7]=0;packet[11]=1;CHECK(check(-2,0,"good.test",used));
    question("good.test");unsigned at=address("good.test",60);packet[at+1]=3;REJECT();
    question("good.test");at=address("good.test",60);memset(packet+at+2,0,4);REJECT();
    question("good.test");alias("good.test","alias.test",10);address("alias.test",60);CHECK(check(0,10,"good.test",used));
    question("good.test");address("alias.test",60);alias("good.test","alias.test",10);CHECK(check(0,10,"good.test",used));
    question("good.test");alias("good.test","alias.test",0);address("alias.test",60);CHECK(check(0,0,"good.test",used));
    question("good.test");address("good.test",7200);CHECK(check(0,3600,"good.test",used));
    address("good.test",4);CHECK(check(0,4,"good.test",used));
    question("good.test");address("good.test",0x80000001U);CHECK(check(0,0,"good.test",used));
    question("good.test");alias("good.test","alias.test",20);alias("alias.test","good.test",20);REJECT();
    question("good.test");alias("good.test","one.test",20);alias("good.test","two.test",20);address("one.test",20);REJECT();
    question("good.test");alias("good.test","alias.test",20);address("good.test",20);REJECT();
    question("good.test");at=alias("unrelated.test","alias.test",20);packet[at+1]--;address("good.test",20);REJECT();
    question("good.test");at=alias("good.test","alias.test",20);packet[at+1]++;address("alias.test",20);REJECT();
    /* Compressed answer owner pointing at the validated question label. */
    question("good.test");packet[7]=1;unsigned pointer=used;u16(0xc00c);u16(1);u16(1);u32(60);u16(4);u32(0xc0000203);
    CHECK(check(0,60,"good.test",used));
    packet[pointer+1]=13;REJECT(); /* middle of a label */
    packet[pointer+1]=(uint8_t)pointer;REJECT(); /* self */
    packet[pointer+1]=(uint8_t)(pointer+2);REJECT(); /* forward */
    packet[pointer+1]=0;REJECT(); /* header */
    question("good.test");unsigned previous=12;
    for(unsigned n=0;n<9;n++) {
        packet[7]++;unsigned start=used;u16(0xc000U|previous);previous=start;
        u16(1);u16(1);u32(60);u16(4);u32(0xc0000203);
        CHECK(check(n<8?0:-74,60,"good.test",used));
    }
    char longest[255];unsigned length=0;
    for(unsigned n=0;n<4;n++) {
        unsigned label=n==3?61:63;
        for(unsigned i=0;i<label;i++)longest[length++]='a';
        if(n!=3)longest[length++]='.';
    }
    longest[length]=0;CHECK(length==253);
    question(longest);packet[7]=1;u16(0xc00c);u16(1);u16(1);u32(60);u16(4);u32(0xc0000203);
    CHECK(check(0,60,longest,used));
    longest[length++]='a';longest[length]=0;CHECK(check(-22,0,longest,used));
    question("good.test");address("good.test",60);packet[7]=65;REJECT();
    char from[16]="good.test",to[16];
    question("good.test");
    for(unsigned i=0;i<8;i++){snprintf(to,sizeof(to),"n%u.test",i);alias(from,to,60-i);strcpy(from,to);}
    address(from,60);CHECK(check(0,53,"good.test",used));
    question("good.test");strcpy(from,"good.test");
    for(unsigned i=0;i<9;i++){snprintf(to,sizeof(to),"n%u.test",i);alias(from,to,60-i);strcpy(from,to);}
    address(from,60);REJECT();
    question("good.test");address("good.test",60);
    uint32_t a=123,t=456;
    CHECK(reist_dns_parse_response(0,used,0x1234,"good.test",&a,&t)==-22);
    CHECK(reist_dns_parse_response(packet,used,0x1234,0,&a,&t)==-22);
    CHECK(reist_dns_parse_response(packet,used,0x1234,"good.test",0,&t)==-22);
    CHECK(reist_dns_parse_response(packet,used,0x1234,"good.test",&a,&a)==-22);
    CHECK(reist_dns_parse_response(packet,used,0x1234,"good.test",(uint32_t *)(void *)packet,&t)==-22);
    CHECK(a==123&&t==456);
    puts("DNS_RESPONSE_VALIDATION_OK");return 0;
}
