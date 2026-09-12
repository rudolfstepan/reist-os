#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <setjmp.h>
#include <stdio.h>

static jmp_buf stopped;
static uint64_t now, probe_start, storage_start;
static unsigned cache_calls, prepared, fail_prepare, fail_probe, fail_storage;
static unsigned probes, stores;
static uint64_t cold_cost;
static void boot_context(const char *a,const char *b,const char *c,const char *d) {
    assert(a && b && c && d);
}
static void panic(const char *message) { assert(message); longjmp(stopped,1); }
static uint64_t pit_monotonic_ms(void) { return now; }
static bool admin_maintenance_init(void) {
    ++cache_calls;
    if(prepared) return true;
    now += cold_cost;
    if(fail_prepare) return false;
    prepared=1;
    return true;
}
static bool supervisor_start_probe(uint64_t timestamp) {
    ++probes; probe_start=timestamp;
    return !fail_probe;
}
static bool storage_service_start(uint64_t timestamp) {
    ++stores; storage_start=timestamp;
    /* Existing storage startup also prepares admin/rescue dependencies.
     * Cold work must no longer consume either service's startup budget. */
    if(!admin_maintenance_init()) return false;
    return !fail_storage;
}

/* PRODUCTION */

static void reset(void) {
    now=10;probe_start=storage_start=0;
    cache_calls=prepared=fail_prepare=fail_probe=fail_storage=probes=stores=0;
}
int main(void) {
    for(unsigned warm=0;warm<2;++warm) {
        for(unsigned cost=0;cost<=5000;cost+=250) {
            reset(); prepared=warm;cold_cost=cost;
            assert(setjmp(stopped)==0);
            start_boot_services();
            assert(probes==1 && stores==1 && prepared && cache_calls>=1);
            assert(probe_start==now && storage_start==now);
            assert(now==10+(warm ? 0 : cost));
        }
    }
    for(unsigned failure=1;failure<=3;++failure) {
        reset();cold_cost=2000;
        fail_prepare=failure==1;fail_probe=failure==2;fail_storage=failure==3;
        if(setjmp(stopped)==0) { start_boot_services(); assert(!"missing boot failure"); }
        assert(probes==(failure>=2) && stores==(failure==3));
    }
    puts("BOOT_PREPARATION_OK cold/warm=42 failures=3");
    return 0;
}
