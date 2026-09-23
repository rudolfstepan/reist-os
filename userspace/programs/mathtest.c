/* Opt-in libm consumer and bounded generation-scoped Ring-3 fault proof. */
#include <x86os.h>
#include "../../test/math_vectors.h"
#ifdef REIST_NATIVE_MATH_RUNTIME
#include <reist/x86_64/cpp_runtime.h>
#include <reist/x86_64/math_runtime.h>
#include "../../test/x86_64_math_vectors.h"
volatile uint64_t reist_math_runtime_selection[2]
    __attribute__((section(".data.memory_witness")))={0x314854414d545352ULL,0};
volatile uint64_t reist_math_runtime_witness[16];
_Alignas(16) unsigned char reist_math_fp_wanted[512];
_Alignas(16) unsigned char reist_math_fp_observed[512];
_Alignas(16) static unsigned char native_math_clean[512];
__attribute__((noinline)) void reist_math_runtime_checkpoint(void) {__asm__ volatile("":::"memory");}

static void native_word(unsigned char *p,uint32_t value) {
    for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(value>>(8*i));
}
static int native_fp_roundtrip(unsigned mode) {
    for(unsigned i=0;i<512;i++) {
        reist_math_fp_wanted[i]=0;reist_math_fp_observed[i]=0;native_math_clean[i]=0;
    }
    native_word(native_math_clean,0x37f);native_word(native_math_clean+24,0x1f80);
    native_word(reist_math_fp_wanted,0x37f|mode);
    native_word(reist_math_fp_wanted+24,0x1f80|(mode<<3));
    reist_math_fp_wanted[4]=0xff;
    for(unsigned n=0;n<8;n++) {
        unsigned char *p=reist_math_fp_wanted+32+n*16;
        p[0]=(unsigned char)(n+1);p[7]=0x80;p[8]=0xff;p[9]=0x3f;
    }
    for(unsigned n=0;n<256;n++)reist_math_fp_wanted[160+n]=(unsigned char)(n+0x31);
    /* The raw syscall truly blocks. All FP registers are declared clobbered;
     * restore the empty ABI state before returning to compiler-generated C. */
    uint64_t result;
    __asm__ volatile(
        "fxrstor64 %2\n\t"
        "mov $41,%%eax\n\tmov $10,%%edi\n\txor %%esi,%%esi\n\txor %%edx,%%edx\n\t"
        "xor %%r10d,%%r10d\n\txor %%r8d,%%r8d\n\txor %%r9d,%%r9d\n\tsyscall\n\t"
        "fxsave64 %1\n\tfxrstor64 %3"
        : "=a"(result),"=m"(reist_math_fp_observed) : "m"(reist_math_fp_wanted),"m"(native_math_clean)
        : "rdi","rsi","rdx","r10","r8","r9","rcx","r11","memory","cc",
          "st","st(1)","st(2)","st(3)","st(4)","st(5)","st(6)","st(7)",
          "xmm0","xmm1","xmm2","xmm3","xmm4","xmm5","xmm6","xmm7",
          "xmm8","xmm9","xmm10","xmm11","xmm12","xmm13","xmm14","xmm15");
    reist_math_runtime_witness[11]=result;
    if(result)return 1;
    for(unsigned i=0;i<28;i++)if(reist_math_fp_wanted[i]!=reist_math_fp_observed[i])return 2;
    for(unsigned n=0;n<8;n++)for(unsigned i=0;i<10;i++)
        if(reist_math_fp_wanted[32+n*16+i]!=reist_math_fp_observed[32+n*16+i])return 3;
    for(unsigned i=160;i<416;i++)if(reist_math_fp_wanted[i]!=reist_math_fp_observed[i])return 4;
    return 0;
}
#endif

static int equal(const char *a,const char *b) {
    for (unsigned i=0;i<32;++i) { if(a[i]!=b[i]) return 0; if(!a[i]) return 1; }
    return 0;
}
static void decimal(char out[11],uint32_t value) {
    char reverse[10]; unsigned n=0;
    do { reverse[n++]=(char)('0'+value%10); value/=10; } while(value && n<10);
    for(unsigned i=0;i<n;++i) out[i]=reverse[n-i-1];
    out[n]=0;
}
static uint32_t parse(const char *s) {
    uint32_t value=0;
    for(unsigned i=0;i<10;++i) {
        if(!s[i]) return value;
        if(s[i]<'0'||s[i]>'9'||value>(UINT32_MAX-(unsigned)(s[i]-'0'))/10) return 0;
        value=value*10+(unsigned)(s[i]-'0');
    }
    return s[10] ? 0 : value;
}
static int send(x86os_ipc_handle_t endpoint) {
    x86os_ipc_message_t msg={X86OS_IPC_MESSAGE_VERSION,sizeof(msg),1,{0x4d}};
    return x86os_ipc_send_timeout(endpoint,&msg,1000);
}
static int receive(x86os_ipc_handle_t endpoint,uint32_t timeout) {
    x86os_ipc_message_t msg={X86OS_IPC_MESSAGE_VERSION,sizeof(msg),0,{0}};
    int result=x86os_ipc_receive_timeout(endpoint,&msg,timeout);
    return result ? result : (msg.version!=X86OS_IPC_MESSAGE_VERSION ||
        msg.struct_size!=sizeof(msg)||msg.length!=1||msg.payload[0]!=0x4d ? -22 : 0);
}
static int defaults(void) {
    uint16_t control; uint32_t simd;
    __asm__ volatile("fnstcw %0; stmxcsr %1" : "=m"(control),"=m"(simd));
    return control==0x037f && simd==0x1f80 && !fetestexcept(FE_ALL_EXCEPT);
}
static int exercise(void) {
    int line=math_vectors();
    if(!line) line=math_environment();
    if(line) {
        x86os_puts("MATH_TEST_FAIL line="); x86os_print_number(line); x86os_puts("\n");
    }
    return line;
}
static int child(const char *mode,x86os_ipc_handle_t command,x86os_ipc_handle_t reply) {
    if(!command || !reply || !defaults()) return 91;
    uint64_t start=0,now=0;
    if(x86os_monotonic_ms(&start)) return 92;
    int ready=0;
    for(unsigned i=0;i<5000;++i) {
        int result=receive(command,0);
        if(!result) { ready=1; break; }
        if(result!=-11 && result!=-13 && result!=-110) return 92;
        if(x86os_monotonic_ms(&now)||now<start||now-start>=5000||x86os_sleep_ms(1)) break;
    }
    if(!ready || exercise() || send(reply) || receive(command,5000)) return 93;
    if(equal(mode,"--normal")) return 37;
    if(equal(mode,"--fault")) {
        uint16_t control;
        feclearexcept(FE_ALL_EXCEPT);
        __asm__ volatile("fnstcw %0" : "=m"(control)); control&=(uint16_t)~FE_INVALID;
        __asm__ volatile("fldcw %0" : : "m"(control) : "memory");
        volatile double negative=-1,result=sqrt(negative); (void)result;
        __asm__ volatile("fwait"); return 94;
    }
    if(equal(mode,"--hold")) {
        if(fesetround(FE_DOWNWARD)) return 95;
        x86os_sleep_ms(5000); return 96;
    }
    return 97;
}
static int owned(int pid,uint32_t generation,int allow_zombie) {
    x86os_process_identity_t identity;
    int result=x86os_process_identity_of(pid,&identity);
    if(result) return allow_zombie && result==-3;
    return identity.generation==generation;
}
static int observe(int pid,uint32_t generation,int wanted,uint32_t budget) {
    uint64_t start=0,now=0;
    if(x86os_monotonic_ms(&start)) return -1;
    for(unsigned round=0;round<10000;++round) {
        if(!owned(pid,generation,wanted==X86OS_PROCESS_ZOMBIE)) return -1;
        for(unsigned i=0;i<32;++i) {
            x86os_process_info_t info;
            int result=x86os_process_info(i,&info);
            if(result<0) return -1;
            if(!result) break;
            if(info.pid==pid) {
                if(info.parent_pid!=x86os_getpid()) return -1;
                if(info.state==wanted) return 0;
                if(info.state==X86OS_PROCESS_ZOMBIE) return -1;
            }
        }
        if(x86os_monotonic_ms(&now)||now<start||now-start>=budget||x86os_sleep_ms(1)) break;
    }
    return -1;
}
static int reap(int pid,uint32_t generation,int expected) {
    int status=-1;
    x86os_process_identity_t identity;
    return observe(pid,generation,X86OS_PROCESS_ZOMBIE,10000) ||
        x86os_wait(pid,&status)!=pid || status!=expected || x86os_wait(pid,&status)>=0 ||
        x86os_process_identity_of(pid,&identity)>=0 ? -1 : 0;
}
static int containment(void) {
    static const char *const modes[]={"--normal","--fault","--hold","--normal"};
    static const int statuses[]={37,144,143,37};
    int previous_pid=0; uint32_t previous_generation=0;
    if(fesetround(FE_UPWARD)) return -1;
    for(unsigned round=0;round<4;++round) {
        x86os_ipc_handle_t command=0,reply=0;
        x86os_process_identity_t identity;
        uint32_t generation=0; int pid=0,ok=0;
        do {
            if(x86os_ipc_create(&command)||x86os_ipc_create(&reply)) break;
            char a[11],b[11]; decimal(a,command); decimal(b,reply);
            const char *args[]={"/usr/bin/mathtest.prg",modes[round],a,b};
            pid=x86os_spawnv(args[0],4,args);
            if(pid<=0||x86os_process_identity_of(pid,&identity)||!identity.generation) break;
            generation=identity.generation;
            if(pid==previous_pid && generation==previous_generation) break;
            previous_pid=pid; previous_generation=generation;
            if(x86os_ipc_delegate(command,pid,X86OS_IPC_RIGHT_RECEIVE)||
               x86os_ipc_delegate(reply,pid,X86OS_IPC_RIGHT_SEND)||send(command)||
               receive(reply,5000)||send(command)) break;
            if(round==2 && (observe(pid,generation,X86OS_PROCESS_SLEEPING,2000)||
                !owned(pid,generation,0)||x86os_kill(pid))) break;
            if(reap(pid,generation,statuses[round])) break;
            pid=0;
            uint16_t control; uint32_t simd;
            __asm__ volatile("fnstcw %0; stmxcsr %1" : "=m"(control),"=m"(simd));
            if(control!=(0x037f|FE_UPWARD)||simd!=(0x1f80|(FE_UPWARD<<3))||fegetround()!=FE_UPWARD) break;
            ok=1;
        } while(0);
        if(pid>0 && generation && owned(pid,generation,0)) {
            if(!x86os_kill(pid)) (void)reap(pid,generation,143);
        }
        if(reply && x86os_ipc_close(reply)) ok=0;
        if(command && x86os_ipc_close(command)) ok=0;
        if(!ok) return -1;
        x86os_puts("MATH_REAP_OK mode="); x86os_puts(modes[round]);
        x86os_puts(" status="); x86os_print_number(statuses[round]);
        x86os_puts(" pid="); x86os_print_number(previous_pid);
        x86os_puts(" generation="); x86os_print_number((int)generation); x86os_puts("\n");
    }
    return fesetround(FE_TONEAREST);
}
int main(int argc,char **argv) {
#ifdef REIST_NATIVE_MATH_RUNTIME
    (void)argv;
    _Static_assert(sizeof(long)==8&&sizeof(void*)==8&&sizeof(double)==8,"native math LP64 ABI");
    if(argc!=1||reist_math_runtime_selection[0]!=0x314854414d545352ULL||
        reist_math_runtime_selection[1]>6||reist_cpp_runtime_begin())return 2;
    if(!defaults()||exercise()||native_lrint_vectors())return 1;
    reist_math_runtime_witness[0]=1;
    reist_math_runtime_witness[1]=math_bits(sin(0.5));
    reist_math_runtime_witness[2]=math_bits(sqrt(2));
    reist_math_runtime_witness[3]=(uint64_t)lrint(0x1p40);
    reist_math_runtime_witness[4]=(uint64_t)lrint(-0x1p40);
    reist_math_runtime_witness[5]=math_bits(nextafter(0,1));
    reist_math_runtime_witness[6]=math_bits(copysign(0,-1));
    reist_math_runtime_witness[7]=44;reist_math_runtime_witness[8]=sizeof(long);
    reist_math_runtime_witness[9]=sizeof(double);
    reist_math_runtime_checkpoint();
    const unsigned modes[]={FE_TONEAREST,FE_DOWNWARD,FE_UPWARD,FE_TOWARDZERO};
    for(unsigned n=0;n<4;n++) {
        unsigned selected=reist_math_runtime_selection[1]==1?3-n:n;
        if(native_fp_roundtrip(modes[selected]))return 3;
        reist_math_runtime_witness[0]=2;reist_math_runtime_witness[10]=modes[selected];
        reist_math_runtime_witness[12]=n;reist_math_runtime_checkpoint();
    }
    switch(reist_math_runtime_selection[1]) {
    case 0:case 1:break;
    case 2:{
        uint16_t control=0x37e;volatile double negative=-1;
        __asm__ volatile("fnclex; fldcw %0; fldl %1; fsqrt; fwait"::"m"(control),"m"(negative):"st","memory");
        return 94;
    }
    case 3:{uint32_t invalid=0xffffffff;__asm__ volatile("ldmxcsr %0"::"m"(invalid):"memory");return 95;}
    case 4:__asm__ volatile("ud2");return 96;
    case 5:for(;;)(void)x86os_sleep_ms(100);
    case 6:for(;;)__asm__ volatile("pause");
    default:return 2;
    }
    x86os_puts("MATH_NUMERIC_OK functions=44\nMATH_FENV_OK rounding=4\nMATH_LP64_OK\nMATH_FP_STATE_OK\nMATH_RUNTIME_OK\n");
    return 0;
#else
    if(argc==4) return child(argv[1],parse(argv[2]),parse(argv[3]));
    if(argc!=1) return 2;
    if(!defaults() || exercise()) { x86os_puts("MATH_TEST_FAIL initial\n"); return 1; }
    x86os_puts("MATH_NUMERIC_OK functions=44\nMATH_FENV_OK rounding=4\n");
    if(containment()) { x86os_puts("MATH_TEST_FAIL containment\n"); return 1; }
    x86os_puts("MATH_PARENT_OK\nMATH_RUNTIME_OK\n"); return 0;
#endif
}
