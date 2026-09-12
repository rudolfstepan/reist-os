#include <reist/x86_64/syscall.h>
typedef unsigned long long u64;
static volatile u64 initialized=0x706f726772616d00ULL+PROGRAM_ID;
static volatile unsigned char zero_data[4096];
static int equal(const char *a,const char *b) {
    for(unsigned n=0;n<128;n++){if(a[n]!=b[n])return 0;if(!a[n])return 1;}return 0;
}
int main(u64 argc,char **argv,char **envp) {
    const char name[]={'p','r','o','g','r','a','m','0'+PROGRAM_ID,'.','p','r','g',0};
    const char number[]={'0'+PROGRAM_ID,0};
    if(argc!=2 || argv[2] || *envp || !equal(argv[0],name) || !equal(argv[1],number))return 200;
    const u64 *aux=(const u64 *)(envp+1);
    if(aux[0]!=0x52534901 || aux[1] || aux[2] || aux[3])return 201;
    if(initialized!=0x706f726772616d00ULL+PROGRAM_ID)return 202;
    for(unsigned n=0;n<sizeof zero_data;n++)if(zero_data[n])return 203;
    initialized^=0xffff;zero_data[4095]=PROGRAM_ID+1;
    long long a=reist_x64_syscall1(4,65536);
    if(a<0 || (u64)a<0x100000000ULL)return 204;
    volatile unsigned char *p=(volatile unsigned char *)(u64)a;
    for(unsigned n=0;n<65536;n++) {if(p[n])return 205;p[n]=(unsigned char)(n+PROGRAM_ID);}
    long long b=reist_x64_syscall2(6,(u64)a,131072);
    if(b<0)return 206;
    p=(volatile unsigned char *)(u64)b;
    for(unsigned n=0;n<65536;n++)if(p[n]!=(unsigned char)(n+PROGRAM_ID))return 207;
    if(reist_x64_syscall1(41,100)!=0)return 208;
#if PROGRAM_ID==2 && PROGRAM_CASE==1
    __asm__ volatile("ud2");
#elif PROGRAM_ID==2 && PROGRAM_CASE==2
    /* Deliberate hostile busy task: existing32-sample kernel quota must retire it. */
    for(;;)__asm__ volatile("pause");
#endif
    if(PROGRAM_ID%2==0 && reist_x64_syscall1(5,(u64)b)!=0)return 209;
    if(zero_data[4095]!=PROGRAM_ID+1 || initialized!=(0x706f726772616d00ULL+PROGRAM_ID^0xffff))return 210;
    return 40+PROGRAM_ID;
}
