/* Qualification only: bounded active-clock calibration, acknowledged bounded
 * CPU batches before service initialization. Never renew a service session. */
#ifndef REIST_SERVICE_PIO_WORKLOAD_H
#define REIST_SERVICE_PIO_WORKLOAD_H
static uint64_t service_cycles(void) {
    uint32_t low,high;
    __asm__ volatile("lfence; rdtsc" : "=a"(low),"=d"(high) :: "memory");
    return ((uint64_t)high<<32)|low;
}
static uint64_t service_quantum(void) {
    uint64_t best=UINT64_MAX;
    /* Enclose both clock syscalls, including delayed resumes. Remove one
     * 10ms quantization interval; the IRQ observer remains the authority. */
    for(unsigned trial=0;trial<3;trial++) {
        uint64_t begin=service_cycles(),first=(uint64_t)S0(MONOTONIC_MS),now=first;
        if(first>UINT64_MAX-80)return 0;
        unsigned polls;
        for(polls=0;polls<100000;polls++) {
            now=(uint64_t)S0(MONOTONIC_MS);
            if(now<first || now-first>1000)return 0;
            if(now-first>=20)break;
            __asm__ volatile("pause");
        }
        if(polls==100000)return 0;
        uint64_t end=service_cycles();
        if(now<first+20 || now-first>1000 || end<=begin || end-begin>3000000000ULL)return 0;
        uint64_t quantum=(end-begin)*11/(now-first-10);
        if(!quantum || quantum>200000000)return 0;
        if(quantum<best)best=quantum;
    }
    return best;
}

static int service_pio_prepare(unsigned mode) {
    uint64_t quantum=service_quantum();
    if(!quantum)return -1;
    for(unsigned i=0;i<40;i++) {
        uint64_t first=service_cycles();unsigned n;
        for(n=0;n<1000000;n++) {
            uint64_t now=service_cycles();
            if(now<first)return -1;
            if(now-first>=quantum)break;
            __asm__ volatile("pause");
        }
        if(n==1000000 || S1(SLEEP_MS,80))return -1;
        if(i%5==4 && notice(mode,2,i+1))return -1;
    }
    return 0;
}
/* Qualification work must not consume the ATA session's initial CPU window.
 * Real blocking waits only; no quota, origin or session reset. */
static int service_pio_idle(unsigned mode) {
    for(unsigned i=1;i<=12;i++) {
        if(S1(SLEEP_MS,100))return -1;
        if(i%6==0 && notice(mode,3,i))return -1;
    }
    return 0;
}
#endif
