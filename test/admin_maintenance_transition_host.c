/* Actual admin/service/safety/ATA entry bodies; only hardware, clock and
 * protected-record storage are deterministic fakes. No process abort/dialog. */
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#define MAX_DRIVES 4
#define DRIVE_TYPE_ATA 1
#define DRIVE_TYPE_PARTITION 2
#define DRIVE_TYPE_FDD 3
#define ADMIN_CONTROL_VERSION 1
#define ADMIN_STORAGE_DEVICE_DOWN 1
#define ADMIN_STORAGE_DEVICE_UP 2
#define ADMIN_STORAGE_MOUNT 3
#define ADMIN_STORAGE_UMOUNT 4
#define ADMIN_EACCES (-13)
#define ADMIN_EIO (-5)
#define REIST_EACCES 13
#define REIST_EINVAL 22
#define REIST_ENOTSUP 95
#define REIST_EBUSY 16
#define REIST_EIO 5
#define BLOCK_DEVICE_OK 0
#define STORAGE_WRITE_DEADLINE_MS 10000U
#define ATA_TRANSACTION_LOCK_TIMEOUT_MS 10000U
typedef struct { int type; uint32_t parent_resource; unsigned short base; bool is_master; } drive_t;
typedef struct { int pid; uint32_t generation; } Process;
typedef struct {
    uint32_t active; int32_t owner_pid; uint32_t owner_generation, command, target,
        resource_mask, transaction_generation, root_resource_mask, reserved;
    uint64_t deadline_ms;
} admin_control_t;
typedef struct {
    int pid; uint32_t process_generation, resource_mask, resource, transaction_generation;
    uint64_t deadline_ms;
} admin_flush_context_t;
typedef struct {
    uint32_t quarantined_resources, read_only_resources, recovering_resources,
        admin_down_resources, admin_transition_resources, admin_failed_resources;
} storage_service_control_t;
typedef struct {
    uint64_t progress_marker, operation_deadline_ms;
    uint32_t write_fenced, operation_active, active_resource;
} storage_control_t;
typedef struct { int (*check)(void*,bool); void* context; int error; } ata_journal_admission_t;
static bool ata_journal_check(ata_journal_admission_t* a, bool effect) {
    if (!a) return true;
    if (!a->error) a->error=a->check ? a->check(a->context,effect) : -13;
    return !a->error;
}
static drive_t detected_drives[MAX_DRIVES];
static int drive_count=3, protected_control, storage_supervisor_handle;
static bool initialized, storage_supervised, storage_integrity_failed, storage_force_fenced, ata_write_fenced;
static bool held, lease, alive, metadata, lock_ok, write_ok, supervisor_ok;
static unsigned commands, ends, locks, unlocks, checks, inject_phase, inject_kind;
static uint64_t now;
static Process owner;
static admin_control_t admin;
static storage_control_t safety;
static storage_service_control_t service;
static bool control_valid(const void* p,size_t n) { return p && n==sizeof(admin); }
static int critical_object_read(const int* object, unsigned v, void* p, size_t n,
    size_t* length, bool (*validate)(const void*,size_t)) {
    (void)object;(void)v;
    if (!metadata || n!=sizeof(admin) || !validate(&admin,sizeof(admin))) return -1;
    memcpy(p,&admin,n); *length=n; return 0;
}
static int control_read(storage_service_control_t* p) { *p=service; return metadata ? 0:-1; }
static bool storage_control_read(storage_control_t* p) { *p=safety; return metadata; }
static bool storage_control_write(const storage_control_t* p) { safety=*p; return metadata; }
static void storage_fence_writes(void) { storage_force_fenced=true; ata_write_fenced=true; }
static void filesystem_fence_mutations(void) {}
static bool storage_handover_is_held(void) { return held; }
static int supervisor_report_progress(int h,uint64_t p,uint64_t t) {
    (void)h;(void)p;(void)t; return supervisor_ok ? 0:-1;
}
static uint64_t pit_monotonic_ms(void) { return now; }
static Process* scheduler_current_process(void) { return &owner; }
static bool process_identity_alive(int pid,uint32_t generation) {
    return alive && owner.pid==pid && owner.generation==generation;
}
static bool leases_valid(int pid,uint32_t generation,uint32_t mask) {
    return lease && pid==7 && generation==9 && mask==admin.resource_mask && now<15100;
}
static void inject(unsigned phase) {
    if (phase!=inject_phase) return;
    switch(inject_kind) {
    case 1: lease=false; break;
    case 2: owner.generation++; break;
    case 3: now=admin.deadline_ms; break;
    case 4: service.quarantined_resources=2; break;
    case 5: service.admin_transition_resources=0; break;
    case 6: admin.transaction_generation++; break;
    case 7: metadata=false; break;
    case 8: storage_force_fenced=true; break;
    case 9: ata_write_fenced=true; break;
    case 10: alive=false; break;
    case 11: held=true; break;
    case 12: service.read_only_resources=2; break;
    }
}
static bool ata_transaction_begin_until(uint64_t deadline) {
    if (!deadline || now>=deadline || deadline-now>ATA_TRANSACTION_LOCK_TIMEOUT_MS) return false;
    locks++; inject(1); return lock_ok;
}
static void ata_transaction_end(void) { unlocks++; }
static drive_t* ata_partition_translate(drive_t* d,uint32_t sector,uint32_t* absolute) {
    *absolute=sector;
    return d->parent_resource<(uint32_t)drive_count ? &detected_drives[d->parent_resource] : NULL;
}
static bool ata_flush_cache_checked(unsigned short base,bool master,const drive_t* drive,
    uint64_t deadline,ata_journal_admission_t* admission) {
    (void)base;(void)master;(void)drive;
    inject(2); /* Selection has waited; callback is immediately before FLUSH. */
    if (now>=deadline || !ata_journal_check(admission,true)) return false;
    commands++; inject(3); return write_ok;
}
static bool storage_write_end(bool durable) {
    ends++; safety.operation_active=0;
    if (!durable || storage_force_fenced) { storage_fence_writes(); return false; }
    return true;
}
static int block_device_flush(const drive_t* drive) { (void)drive; commands++; return 0; }
static int ata_admin_flush_checked_declaration_only;
int ata_admin_flush_checked(uint32_t,uint64_t,ata_journal_admission_t*);
#include "admin-under-test.h"
#define CHECK(x) do { checks++; if (!(x)) { printf("FAIL line %u: %s\n",__LINE__,#x); return 1; } } while(0)
static void reset(void) {
    (void)ata_admin_flush_checked_declaration_only;
    memset(&service,0,sizeof(service)); memset(&safety,0,sizeof(safety));
    memset(&admin,0,sizeof(admin)); memset(detected_drives,0,sizeof(detected_drives));
    initialized=storage_supervised=lease=alive=metadata=lock_ok=write_ok=supervisor_ok=true;
    held=storage_integrity_failed=storage_force_fenced=ata_write_fenced=false;
    commands=ends=locks=unlocks=inject_phase=inject_kind=0;
    owner=(Process){7,9}; now=100;
    admin.active=1;admin.owner_pid=7;admin.owner_generation=9;admin.command=ADMIN_STORAGE_UMOUNT;
    admin.resource_mask=2;admin.transaction_generation=4;admin.root_resource_mask=1;admin.deadline_ms=15100;
    service.admin_transition_resources=2; safety.progress_marker=1;
    safety.active_resource=UINT32_MAX;
    detected_drives[1]=(drive_t){DRIVE_TYPE_ATA,0,0x1f0,false};
    detected_drives[2]=(drive_t){DRIVE_TYPE_PARTITION,1,0,false};
}
int main(void) {
    for(unsigned mode=1;mode<=4;mode++) {
        if(mode==3)continue;
        reset(); admin.command=mode;
        if(mode==2)service.admin_down_resources=2;
        CHECK(!storage_write_begin(1,now)); CHECK(!storage_service_resource_available(1));
        CHECK(flush_resources(2)==0); CHECK(commands==1 && ends==1 && locks==1 && unlocks==1);
        CHECK(!safety.operation_active && !storage_force_fenced);
        CHECK(safety.operation_deadline_ms==10100);
        CHECK(!storage_write_begin(1,now)); CHECK(service.admin_transition_resources==2);
    }
    for(unsigned phase=1;phase<=3;phase++)for(unsigned kind=1;kind<=12;kind++) {
        reset();inject_phase=phase;inject_kind=kind;
        int result=flush_resources(2);
        if (!result)printf("unexpected admission phase=%u kind=%u\n",phase,kind);
        CHECK(result!=0);
        CHECK(commands==(phase==3 ? 1U:0U)); CHECK(locks==unlocks);
        if(phase>1)CHECK(ends==1 && storage_force_fenced);
    }
    for(unsigned fault=0;fault<15;fault++) {
        reset();
        switch(fault) {
        case 0: admin.root_resource_mask=2;break;
        case 1: admin.active=0;break;
        case 2: admin.resource_mask=4;break;
        case 3: admin.command=ADMIN_STORAGE_MOUNT;break;
        case 4: admin.owner_pid++;break;
        case 5: admin.owner_generation++;break;
        case 6: lease=false;break;
        case 7: metadata=false;break;
        case 8: service.admin_failed_resources=service.admin_down_resources=2;break;
        case 9: service.recovering_resources=service.quarantined_resources=2;break;
        case 10: safety.operation_active=1;break;
        case 11: safety.write_fenced=1;break;
        case 12: storage_integrity_failed=true;break;
        case 13: storage_force_fenced=true;break;
        case 14: held=true;break;
        }
        CHECK(flush_resources(2)!=0);CHECK(!commands && locks==unlocks);
    }
    reset();admin.deadline_ms=120;CHECK(flush_resources(2)==0);CHECK(safety.operation_deadline_ms==120);
    reset();admin.resource_mask=4;service.admin_transition_resources=4;
    CHECK(flush_resources(4)==0);CHECK(commands==1);
    reset();admin.resource_mask=6;service.admin_transition_resources=6;
    CHECK(flush_resources(6)==0);CHECK(commands==1); /* Parent flushed once. */
    reset();admin.resource_mask=4;service.admin_transition_resources=4;service.admin_down_resources=2;
    CHECK(flush_resources(4)!=0 && !commands);
    reset();admin.resource_mask=4;service.admin_transition_resources=4;detected_drives[2].parent_resource=MAX_DRIVES;
    CHECK(flush_resources(4)!=0 && !commands);
    reset();write_ok=false;CHECK(flush_resources(2)!=0);CHECK(commands==1 && ends==1 && storage_force_fenced);
    reset();lock_ok=false;CHECK(flush_resources(2)!=0);CHECK(!commands && !ends && !unlocks);
    reset();supervisor_ok=false;CHECK(flush_resources(2)!=0);CHECK(!commands && storage_force_fenced);
    reset();CHECK(ata_admin_flush_checked(1,15100,NULL)==-REIST_EACCES);CHECK(!commands && !locks);
    reset();service.admin_transition_resources=0;CHECK(storage_write_begin(1,now));CHECK(safety.operation_deadline_ms==10100);
    printf("R342 admin transition checks=%u\n",checks);return 0;
}
