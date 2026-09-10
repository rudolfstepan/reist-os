#ifdef R342_JOURNAL_PROBE_TEST
#include <stdio.h>
#include <string.h>
#include "include/kernel/file_object_guard.h"
static unsigned checks, protected_reads, protected_updates;
static critical_read_result_t counted_read(critical_object_t *o, uint32_t v, void *p,
    size_t c, size_t *n, critical_object_validator_t validate) {
    ++protected_reads;
    return critical_object_read(o,v,p,c,n,validate);
}
static int counted_update(critical_object_t *o, uint32_t v, const void *p,
    size_t n, critical_object_validator_t validate) {
    ++protected_updates;
    return critical_object_update(o,v,p,n,validate);
}
#define critical_object_read counted_read
#define critical_object_update counted_update
#include "kernel/init/file_object_guard.c"
#undef critical_object_read
#undef critical_object_update
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr,"R342 probe:%d: %s (reads=%u)\n",__LINE__,#x,protected_reads); return 1; } } while(0)
static int probe(file_object_guard_t *g, file_object_owner_t owner, uint32_t token,
                 uint32_t resource, uint64_t now, file_object_mutation_context_t *out) {
#ifdef FILE_OBJECT_JOURNAL_PROBE_VERSION
    return file_object_guard_journal_probe(g,owner,token,resource,now,out);
#else
    /* Exact pre-optimization sequence in vfs_storage_journal_authorized. */
    int r=file_object_guard_context(g,owner,token,out);
    uint32_t request=0;uint64_t deadline=0;
    if(!r)r=file_object_guard_owned_request(g,owner,token,resource,now,&request,&deadline);
    if(!r)r=file_object_guard_journal_io(g,owner,token,resource,FILE_OBJECT_JOURNAL_CHECK,now,NULL);
    return r;
#endif
}
static file_object_guard_t* live_guard;
static uint64_t live_now;
static int pool_error;
static unsigned pool_effects;
#define vfs_object_guards (*live_guard)
#define VFS_FILE_OBJECT_GUARD
static bool vfs_guard_platform_live(int pid,uint32_t generation) { return pid==1 && generation==2; }
static uint64_t vfs_guard_platform_now(void) { return live_now; }
static int vfs_guard_apply_media_changes(void) { return 0; }
static int vfs_repair_access(const reist_storage_journal_request_t* q,int pid,uint32_t generation) {
    (void)q;(void)pid;(void)generation;return 0;
}
static int storage_request_mutation_effect(int pid,uint32_t generation,uint32_t request,uint32_t resource,uint64_t now) {
    (void)pid;(void)generation;(void)request;(void)resource;(void)now;pool_effects++;return pool_error;
}
static int storage_request_mutation_authorized(int pid,uint32_t generation,uint32_t request,uint32_t resource,uint64_t now) {
    (void)pid;(void)generation;(void)request;(void)resource;(void)now;return pool_error;
}
#include "journal_admission.inc"
int main(void) {
    for(unsigned mode=0;mode<11;++mode) {
        file_object_guard_t g={0}; file_object_owner_t service={1,2},client={3,4};
        reist_file_object_key_t key={.kind=REIST_FILE_OBJECT_FAT32,.resource=1,.object_a=2};
        memcpy(key.alias,"TARGET  BIN",11);
        uint64_t epoch=0;uint32_t pin=0,token=0;
        CHECK(!file_object_guard_init(&g));CHECK(!file_object_guard_snapshot(&g,&epoch,1));
        CHECK(!file_object_guard_pin(&g,&key,service,client,epoch,1,&pin));
        CHECK(!file_object_guard_begin_owned(&g,&key,pin,7,service,client,epoch,1,5000,&token));
        uint32_t resource=1;uint64_t now=2;
        if(mode==1)++service.generation;
        if(mode==2)++token;
        if(mode==3)resource=2;
        if(mode==4)now=5000;
        if(mode==5)CHECK(!file_object_guard_merge_fences(&g,2));
        if(mode==6)CHECK(!file_object_guard_cleanup(&g,client));
        if(mode==7)CHECK(!file_object_guard_revoke_media(&g,1));
        if(mode==8)g.pins[0].publication_lock=1;
        if(mode==9)g.media[1].publication_lock=1;
        if(mode==10)g.control.publication_lock=1;
        live_guard=&g;live_now=now;pool_error=0;pool_effects=0;
        file_object_mutation_context_t out={0},empty={0};
        protected_reads=0;
        int status=probe(&g,service,token,resource,now,&out);
        if(mode==0) {
            CHECK(!status && out.request==7 && out.resource==1 && out.deadline_ms==5000 && !out.attempted && !out.repair);
            CHECK(protected_reads==3); /* control, exact owned pin, media; all real CRC/ECC checks */
            const uint32_t events[]={FILE_OBJECT_JOURNAL_WRITE,FILE_OBJECT_JOURNAL_WRITE,
                FILE_OBJECT_JOURNAL_FLUSHED,FILE_OBJECT_JOURNAL_FLUSHED,FILE_OBJECT_JOURNAL_WRITE};
            const unsigned updates[]={1,0,1,0,1};
            for(unsigned i=0;i<5;++i) {
                protected_reads=protected_updates=0;
                CHECK(!file_object_guard_journal_io(&g,service,token,resource,events[i],now,NULL));
                CHECK(protected_reads==3 && protected_updates==updates[i]);
            }
            reist_storage_journal_request_t request={REIST_STORAGE_JOURNAL_VERSION,sizeof(request),
                REIST_STORAGE_JOURNAL_WRITE_DEFERRED,token,resource,100,1,0};
            /* Every command still validates the real control, pin and media.
             * Already pending WRITE needs no second identical guard probe. */
            for(unsigned i=0;i<10;++i) {
                protected_reads=protected_updates=0;
                CHECK(!vfs_storage_journal_authorized(&request,service.pid,service.generation,true));
                CHECK(protected_reads==3 && protected_updates==0 && pool_effects==i+1);
            }
            CHECK(!file_object_guard_journal_io(&g,service,token,resource,FILE_OBJECT_JOURNAL_FLUSHED,now,NULL));
            protected_reads=protected_updates=0;
            CHECK(!vfs_storage_journal_authorized(&request,service.pid,service.generation,true));
            CHECK(protected_reads==6 && protected_updates==1);
            pool_error=-125;protected_updates=0;
            CHECK(vfs_storage_journal_authorized(&request,service.pid,service.generation,true)==-125);
            CHECK(!protected_updates);
        } else {
            CHECK(status<0 && !memcmp(&out,&empty,sizeof(out)));
            if(mode==4)CHECK(status==-110);
            reist_storage_journal_request_t request={REIST_STORAGE_JOURNAL_VERSION,sizeof(request),
                REIST_STORAGE_JOURNAL_WRITE_DEFERRED,token,resource,100,1,0};
            protected_updates=pool_effects=0;
            CHECK(vfs_storage_journal_authorized(&request,service.pid,service.generation,true)<0);
            CHECK(!protected_updates && !pool_effects);
        }
    }
    printf("R342 journal-probe checks: %u\n",checks);return 0;
}
#endif

#ifdef R342_PROGRAM_TEST
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define main fwritest_program_main
#include "userspace/programs/fwritest.c"
#undef main
static unsigned program_checks, opened, closed, mutations, injected, spawned, waited;
static uint32_t model_size, model_offset;
static uint8_t model[4U*1024U*1024U];
static uint64_t program_now;
#define P_CHECK(x) do { ++program_checks; if (!(x)) { fprintf(stderr, "fwritest:%d: %s\n", __LINE__, #x); exit(1); } } while (0)
void x86os_puts(const char* text) { (void)text; }
void x86os_putchar(char c) { (void)c; }
void x86os_print_number(int number_) { (void)number_; }
int x86os_monotonic_ms(uint64_t* now) { *now = ++program_now; return 0; }
int reist_vfs_file_open_writable(const char* path, uint32_t timeout, uint32_t rights, uint32_t flags, reist_vfs_file_handle_t* handle) {
    P_CHECK(!strcmp(path, "/test.bin") && timeout == 5000 && flags == X86OS_O_NOFOLLOW);
    P_CHECK(rights == (REIST_VFS_FILE_RIGHT_DATA | REIST_VFS_WRITE_RIGHT_MUTATIONS));
    ++opened; *handle = 1; model_offset = 0; return 0;
}
int reist_vfs_file_fstat(reist_vfs_file_handle_t h, x86os_file_info_t* info) {
    P_CHECK(h == 1); memset(info, 0, sizeof(*info)); info->size = model_size; return 0;
}
int reist_vfs_file_close(reist_vfs_file_handle_t h) { P_CHECK(h == 1); ++closed; return 0; }
int reist_vfs_file_set_timeout(reist_vfs_file_handle_t h, uint32_t timeout) { P_CHECK(h == 1 && timeout && timeout <= 5000); return 0; }
int reist_vfs_file_seek(reist_vfs_file_handle_t h, int64_t offset, uint32_t whence, uint32_t* result) {
    P_CHECK(h == 1 && whence == REIST_VFS_SEEK_SET && offset >= 0 && (uint64_t)offset <= model_size);
    *result = model_offset = (uint32_t)offset; return 0;
}
int reist_vfs_file_read_bulk(reist_vfs_file_handle_t h, void* data, size_t capacity) {
    P_CHECK(h == 1); uint32_t count = model_size-model_offset;
    if (count > capacity) count = (uint32_t)capacity;
    if (count > 1024) count = 1024; /* real short-read contract */
    memcpy(data, model+model_offset, count); model_offset += count; return (int)count;
}
static int program_progress(reist_vfs_file_progress_t* p) {
    memset(p, 0, sizeof(*p)); ++mutations;
    p->version = 1; p->struct_size = sizeof(*p); p->steps = 1;
    if (injected == mutations) { p->outcome = REIST_FILE_OBJECT_UNKNOWN; p->durable_bytes = 19; return -5; }
    p->flags = REIST_VFS_FILE_PROGRESS_COMPLETE; p->outcome = REIST_FILE_OBJECT_DURABLE_COMMIT; return 0;
}
int reist_vfs_file_resize_bounded(reist_vfs_file_handle_t h, uint64_t size, reist_vfs_file_progress_t* p) {
    P_CHECK(h == 1 && size <= sizeof(model)); int r = program_progress(p); if (r) return r;
    if (size > model_size) memset(model+model_size, 0, (size_t)size-model_size);
    p->durable_size = model_size = (uint32_t)size; return 0;
}
int reist_vfs_file_pwrite_bounded(reist_vfs_file_handle_t h, const void* data, size_t count, uint64_t offset, reist_vfs_file_progress_t* p) {
    P_CHECK(h == 1 && offset <= sizeof(model) && count <= sizeof(model)-offset);
    int r = program_progress(p); if (r) return r;
    if (offset > model_size) memset(model+model_size, 0, (size_t)offset-model_size);
    memcpy(model+offset, data, count); if (offset+count > model_size) model_size = (uint32_t)(offset+count);
    p->durable_size = model_size; p->durable_bytes = count; return 0;
}
int reist_vfs_file_append_bounded(reist_vfs_file_handle_t h, const void* data, size_t count, reist_vfs_file_progress_t* p) {
    return reist_vfs_file_pwrite_bounded(h, data, count, model_size, p);
}
int reist_vfs_file_fsync(reist_vfs_file_handle_t h, reist_vfs_write_result_t* r) {
    P_CHECK(h == 1); memset(r, 0, sizeof(*r)); r->outcome = REIST_FILE_OBJECT_DURABLE_COMMIT; return 0;
}
typedef struct { int unused; } shell_vfs_budget_t;
static int shell_vfs_budget_begin(shell_vfs_budget_t* budget) { (void)budget; return 0; }
static int shell_vfs_executable(shell_vfs_budget_t* budget, const char* path) {
    (void)budget; return !strcmp(path, "/bin/fwritest.prg");
}
int x86os_spawnv(const char* path, int argc, const char* const argv[]) {
    P_CHECK(!strcmp(path, "/bin/fwritest.prg") && argc == 3 && !strcmp(argv[1], "/test.bin") && !strcmp(argv[2], "--test-data"));
    ++spawned; return 42;
}
int x86os_process_identity_of(int pid, x86os_process_identity_t* identity) { (void)identity; P_CHECK(pid == 42); return -3; }
int x86os_terminal_input(uint32_t op, int pid, uint32_t generation) { (void)op; (void)pid; (void)generation; P_CHECK(0); return -5; }
int x86os_kill(int pid) { (void)pid; P_CHECK(0); return -5; }
int x86os_wait(int pid, int* status) { P_CHECK(pid == 42); ++waited; *status = 0; return pid; }
#include "fwritest_shell.inc"
int main(void) {
    char* args[] = {"fwritest", "/test.bin", "--test-data", "exercise", NULL};
    for (unsigned cut = 0; cut <= 4; ++cut) {
        opened = closed = mutations = 0; injected = cut;
        model_size = 2U*1024U*1024U+17; memset(model, 0xcc, sizeof(model));
        int result = fwritest_program_main(4, args);
        P_CHECK(opened == 1 && closed == 1 && (result != 0) == (cut != 0));
        P_CHECK(mutations == (cut ? cut : 4));
        if (!cut) P_CHECK(model_size == 513 && model[0] == 0xcc && model[3] == 23);
    }
    args[2] = "wrong"; P_CHECK(fwritest_program_main(4, args) == 2 && opened == 1);
    args[2] = "--test-data";
    for (unsigned i = 0; i < 3; ++i) {
        const char* command[16] = {i == 0 ? "fwritest" : i == 1 ? "FWRITEST" : "fwritest.prg", "/test.bin", "--test-data"};
        run_program(3, command);
    }
    P_CHECK(spawned == 3 && waited == 3);
    printf("R342 fwritest checks: %u\n", program_checks); return 0;
}
#endif

#ifdef R342_REPAIR_GUARD_TEST
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "include/kernel/file_object_guard.h"
static unsigned repair_checks;
#define R_CHECK(x) do { ++repair_checks; if (!(x)) { fprintf(stderr, "repair-guard:%d: %s\n", __LINE__, #x); exit(1); } } while (0)
int main(void) {
    const file_object_owner_t old = {20, 3}, fresh = {21, 4}, client = {30, 2};
    const reist_file_object_key_t key = {.kind=REIST_FILE_OBJECT_FAT32, .resource=1, .object_a=2, .alias="TARGET  BIN"};
    for (unsigned variant = 0; variant < 11; ++variant) {
        file_object_guard_t guard = {0};
        uint64_t epoch, deadline; uint32_t token=0, normal=0, pin=0, mask;
        R_CHECK(!file_object_guard_init(&guard));
        R_CHECK(!file_object_guard_snapshot(&guard, &epoch, 1));
        R_CHECK(file_object_guard_repair_begin(&guard, 1, fresh, epoch, 1, 100, &token) == -REIST_EACCES && !token);
        R_CHECK(!file_object_guard_pin(&guard, &key, old, client, epoch, 1, &pin));
        R_CHECK(!file_object_guard_merge_fences(&guard, (1U<<1)|(1U<<2)));
        R_CHECK(file_object_guard_repair_begin(&guard, 1, fresh, epoch, 1, 100, &token) == -REIST_EBUSY && !token);
        R_CHECK(!file_object_guard_cleanup(&guard, old));
        R_CHECK(!file_object_guard_snapshot(&guard, &epoch, 1));
        R_CHECK(!file_object_guard_repair_begin(&guard, 1, fresh, epoch, 1, 100, &token) && token);
        R_CHECK(file_object_guard_pin(&guard, &key, fresh, client, epoch, 1, &normal) < 0);
        R_CHECK(file_object_guard_begin(&guard, &key, 1, true, fresh, epoch, 1, 100, &normal) < 0);
        R_CHECK(file_object_guard_mutation_authorized(&guard, fresh, 1, 1) < 0); /* no raw grant */
        R_CHECK(file_object_guard_journal_io(&guard, old, token, 1, FILE_OBJECT_JOURNAL_WRITE, 1, NULL) < 0);
        R_CHECK(file_object_guard_journal_io(&guard, fresh, token, 2, FILE_OBJECT_JOURNAL_WRITE, 1, NULL) < 0);
        R_CHECK(!file_object_guard_journal_io_deadline(&guard, fresh, token, 1, FILE_OBJECT_JOURNAL_CHECK, 1, NULL, &deadline) && deadline == 100);
        R_CHECK(file_object_guard_repair_finish(&guard, token, fresh, true, 1) == -REIST_EINVAL); /* requires verified flush */
        R_CHECK(!file_object_guard_journal_io(&guard, fresh, token, 1, FILE_OBJECT_JOURNAL_WRITE, 1, NULL));
        R_CHECK(file_object_guard_repair_finish(&guard, token, fresh, true, 1) == -REIST_EINVAL);
        R_CHECK(!file_object_guard_journal_io(&guard, fresh, token, 1, FILE_OBJECT_JOURNAL_FLUSHED, 1, NULL));
        if (variant == 1) R_CHECK(!file_object_guard_poll(&guard, 100));
        if (variant == 2) R_CHECK(!file_object_guard_cleanup(&guard, fresh));
        if (variant == 3) R_CHECK(!file_object_guard_revoke_media(&guard, 1));
        if (variant == 4) R_CHECK(!file_object_guard_end(&guard, token, fresh, REIST_FILE_OBJECT_DURABLE_COMMIT, 1));
        if (variant == 5) ++token;
        if (variant == 6) R_CHECK(!file_object_guard_journal_io(&guard, fresh, token, 1, FILE_OBJECT_JOURNAL_WRITE, 1, NULL));
        if (variant == 7) { guard.control.primary.crc32 ^= 1; guard.control.shadow.crc32 ^= 1; }
        if (variant == 8) guard.lock = 1;
        int status = file_object_guard_repair_finish(&guard, token, variant == 9 ? old : fresh, variant != 10, 1);
        if (variant == 8) guard.lock = 0;
        R_CHECK(variant == 0 || variant == 10 ? status == 0 : status < 0);
        int fenced = file_object_guard_fenced(&guard, &mask);
        R_CHECK(variant == 7 ? fenced < 0 && mask == UINT32_MAX : !fenced);
        R_CHECK(mask & (1U<<2)); /* cannot clear a different unsafe volume */
        R_CHECK((mask & (1U<<1)) == (variant == 0 ? 0U : 1U<<1));
        if (!variant) {
            R_CHECK(!file_object_guard_snapshot(&guard, &epoch, 2));
            R_CHECK(!file_object_guard_pin(&guard, &key, fresh, client, epoch, 2, &normal) && normal != pin);
            R_CHECK(file_object_guard_verify(&guard, pin, old, client, 2) == -REIST_ESTALE);
            R_CHECK(file_object_guard_repair_finish(&guard, token, fresh, true, 2) == -REIST_ESTALE);
        }
    }
    printf("R342 repair-guard checks: %u\n", repair_checks); return 0;
}
#endif

#if defined(R342_OVERWRITE_TEST) || defined(R342_SERVICE_TEST)
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "include/kernel/file_object_guard.h"
#include "userspace/storage/include/reist/fat32_file_write.h"
#include "userspace/storage/include/reist/fat32_transaction.h"

enum { W_CLUSTERS = 66000, W_FAT = 516, W_DATA = 32+2*W_FAT,
       W_SECTORS = W_DATA+W_CLUSTERS, W_FIRST = 123, W_LENGTH = 10000 };
typedef struct { uint32_t sector, used; uint8_t bytes[512]; } w_sector_t;
static w_sector_t w_disk[128], w_stable[128];
static uint8_t w_boot[512], w_entry[512], w_payload[128*1024];
static uint32_t w_spc = 1, w_reserved = 32, w_copies = 2, w_data = W_DATA, w_sectors = W_SECTORS;
static uint32_t w_length = W_LENGTH, w_stride = 5;
static unsigned w_different, w_bad_fsinfo;
static unsigned w_checks, w_reads, w_effects, w_flushes, w_cut, w_through, w_read_cut, w_snapshot_mode;
static unsigned w_write_requests, w_read_requests;
static uint64_t w_now;
static file_object_guard_t w_guard;
static const file_object_owner_t w_server = {9, 7}, w_client = {20, 3};
static reist_file_object_owned_request_t w_admission;
static reist_fat32_transaction_t w_tx;
static reist_fat32_ownership_t w_proof, w_saved_proof;
static reist_vfs_shadow_object_t w_object;
#define W_CHECK(x) do { ++w_checks; if (!(x)) { fprintf(stderr, "R342 overwrite:%d: %s\n", __LINE__, #x); exit(1); } } while (0)
static void w_put(uint8_t* p, uint32_t value) {
    for (unsigned i = 0; i < 4; ++i) p[i] = (uint8_t)(value>>(i*8));
}
static uint32_t w_cluster(unsigned rank) { return 3+rank*w_stride; }
static uint32_t w_lba(uint32_t position) {
    return w_data+(w_cluster(position/(w_spc*512))-2)*w_spc+(position/512)%w_spc;
}
static int w_info(void* context, uint32_t resource, x86os_drive_info_t* info) {
    (void)context;
    if (resource) return 0;
    memset(info, 0, sizeof(*info)); info->type = X86OS_DRIVE_PARTITION;
    info->sectors = w_sectors; strcpy(info->mount_point, "/"); return 1;
}
static void w_original(uint32_t sector, uint8_t* bytes) {
    memset(bytes, 0, 512);
    if (!sector) memcpy(bytes, w_boot, 512);
    else if (sector == w_data) memcpy(bytes, w_entry, 512);
    else if (sector == 1 || sector == 7) {
        w_put(bytes, 0x41615252); w_put(bytes+484, 0x61417272);
        w_put(bytes+488, 123); w_put(bytes+492, 456); w_put(bytes+508, 0xaa550000);
        if (w_bad_fsinfo && (sector == 1 || w_bad_fsinfo == 2)) bytes[0] ^= 1;
    }
    else if (sector == 8 || (sector == 31 && w_reserved > 31)) {
        ata_journal_record_t record; ata_undo_journal_make_clean(&record, 7); memcpy(bytes, &record, 512);
    } else if (sector >= w_reserved && sector < w_data) {
        uint32_t base = ((sector-w_reserved)%W_FAT)*128;
        for (unsigned i = 0; i < 128; ++i) {
            uint32_t cluster = base+i, value = 0;
            if (cluster < 3) value = cluster ? 0xfffffff : 0xffffff8;
            else if ((cluster-3)%w_stride == 0 && (cluster-3)/w_stride < w_length)
                value = (cluster-3)/w_stride+1 == w_length ? 0xfffffff : cluster+w_stride;
            if (w_different && cluster == 3 && sector >= w_reserved+W_FAT) value ^= 1;
            w_put(bytes+4*i, value | (sector < w_reserved+W_FAT ? 0xa0000000 : 0xb0000000));
        }
    } else if (sector >= w_data) {
        for (unsigned i = 0; i < 512; ++i) bytes[i] = (uint8_t)(sector*13+i*7);
    }
}
static int w_read(void* context, uint32_t resource, uint32_t sector, uint8_t* bytes) {
    (void)context;
    if (resource || sector >= w_sectors || ++w_reads == w_read_cut) return -REIST_EIO;
    for (unsigned i = 0; i < 128; ++i)
        if (w_disk[i].used && w_disk[i].sector == sector) { memcpy(bytes, w_disk[i].bytes, 512); return 0; }
    w_original(sector, bytes); return 0;
}
static void w_write(uint32_t sector, const uint8_t* bytes) {
    for (unsigned i = 0; i < 128; ++i) {
        if (w_disk[i].used && w_disk[i].sector != sector) continue;
        w_disk[i].used = 1; w_disk[i].sector = sector; memcpy(w_disk[i].bytes, bytes, 512); return;
    }
    W_CHECK(0); /* Test media overlay exhausted, not production ENOSPC. */
}
static int w_guard_call(void* context, reist_file_object_guard_request_t* request) {
    (void)context;
    W_CHECK(file_object_guard_request_valid(request));
    if (request->operation == REIST_FILE_OBJECT_SNAPSHOT) {
        if (w_snapshot_mode == 1) return -REIST_EIO;
        if (w_snapshot_mode == 2) {
            /* A real other-volume mutation between END and snapshot. */
            uint64_t epoch; uint32_t token;
            reist_file_object_key_t key = w_admission.base.keys[0]; key.resource = 1;
            W_CHECK(!file_object_guard_snapshot(&w_guard, &epoch, w_now));
            W_CHECK(!file_object_guard_begin_mode(&w_guard, &key, 1, REIST_FILE_OBJECT_EXCLUSIVE,
                w_server, epoch, w_now, 5000, &token));
            W_CHECK(!file_object_guard_end(&w_guard, token, w_server, REIST_FILE_OBJECT_NO_EFFECT, w_now));
        }
        if (w_snapshot_mode == 3) W_CHECK(!file_object_guard_release(&w_guard, w_admission.pin, w_server, w_client));
        return file_object_guard_snapshot(&w_guard, &request->epoch, w_now);
    }
    if (request->operation == REIST_FILE_OBJECT_VERIFY)
        return file_object_guard_verify(&w_guard, request->token, w_server,
            (file_object_owner_t){request->client_pid, request->client_generation}, w_now);
    W_CHECK(request->operation == REIST_FILE_OBJECT_MUTATION_END);
    return file_object_guard_end(&w_guard, request->token, w_server, request->flags, w_now);
}
static int w_owned(void* context, reist_file_object_owned_request_t* request) {
    (void)context;
    W_CHECK(!memcmp(request, &w_admission, sizeof(*request)) && file_object_guard_owned_valid(request));
    return file_object_guard_begin_owned(&w_guard, &request->base.keys[0], request->pin, request->request,
        w_server, w_client, request->base.epoch, w_now, request->base.deadline_ms, &request->base.token);
}
static int w_transfer(void* context, const reist_storage_journal_request_t* request, void* bytes) {
    (void)context;
    W_CHECK(file_object_guard_journal_request_valid(request));
    int result = file_object_guard_journal_io(&w_guard, w_server, request->token, 0,
        FILE_OBJECT_JOURNAL_CHECK, w_now, NULL);
    if (result) return result;
    if (request->operation == REIST_STORAGE_JOURNAL_WRITE_DEFERRED) ++w_write_requests;
    if (request->operation == REIST_STORAGE_JOURNAL_FLUSH) {
        ++w_flushes;
        if (++w_effects == w_cut) return -REIST_EIO;
        memcpy(w_stable, w_disk, sizeof(w_disk));
        return file_object_guard_journal_io(&w_guard, w_server, request->token, 0,
            FILE_OBJECT_JOURNAL_FLUSHED, w_now, NULL);
    }
    W_CHECK(request->resource == 0 && request->sector >= W_FIRST &&
        request->sector-W_FIRST < w_sectors && request->count <= w_sectors-(request->sector-W_FIRST));
    if (request->operation == REIST_STORAGE_JOURNAL_READ) {
        ++w_read_requests;
        for (unsigned i = 0; i < request->count; ++i) {
            result = w_read(NULL, 0, request->sector-W_FIRST+i, (uint8_t*)bytes+512*i);
            if (result) return result;
        }
        return 0;
    }
    result = file_object_guard_journal_io(&w_guard, w_server, request->token, 0,
        FILE_OBJECT_JOURNAL_WRITE, w_now, NULL);
    if (result) return result;
    for (unsigned i = 0; i < request->count; ++i) {
        if (++w_effects == w_cut) return -REIST_EIO;
        w_write(request->sector-W_FIRST+i, (uint8_t*)bytes+512*i);
        if (w_through) memcpy(w_stable, w_disk, sizeof(w_disk));
    }
    return 0;
}
static const reist_vfs_shadow_io_t w_io = {NULL, w_info, w_read};
static const reist_fat32_owned_transaction_io_t w_tx_io = {{NULL, w_guard_call, w_transfer}, w_owned};
static void w_reset(bool qualify) {
    memset(w_disk, 0, sizeof(w_disk)); memset(w_stable, 0, sizeof(w_stable));
    memset(&w_guard, 0, sizeof(w_guard)); memset(&w_tx, 0, sizeof(w_tx));
    W_CHECK(!file_object_guard_init(&w_guard));
    w_now = 1; w_reads = w_effects = w_flushes = w_cut = w_through = w_read_cut = w_snapshot_mode = 0;
    w_write_requests=w_read_requests=0;
    memset(&w_admission, 0, sizeof(w_admission));
    w_admission.base = (reist_file_object_guard_request_t){
        .version=REIST_FILE_OBJECT_OWNED_VERSION, .struct_size=sizeof(w_admission),
        .operation=REIST_FILE_OBJECT_MUTATION_BEGIN,
        .flags=REIST_FILE_OBJECT_EXCLUSIVE|REIST_FILE_OBJECT_EXTERNAL_JOURNAL,
        .client_pid=w_client.pid, .client_generation=w_client.generation, .deadline_ms=5000
    };
    x86os_file_info_t info;
    W_CHECK(!reist_vfs_shadow_fat_object_open_key(&w_io, "/TARGET.BIN", 11, &w_object, &info,
        &w_admission.base.keys[0]));
    W_CHECK(!file_object_guard_snapshot(&w_guard, &w_admission.base.epoch, w_now));
    W_CHECK(!file_object_guard_pin(&w_guard, &w_admission.base.keys[0], w_server, w_client,
        w_admission.base.epoch, w_now, &w_admission.pin));
    w_admission.request = 513;
    if (qualify) {
        W_CHECK(!reist_fat32_volume_begin(&w_proof, &w_io, &w_object, w_admission.base.epoch));
        int result; unsigned steps = 0;
        do { result = reist_fat32_ownership_step(&w_proof, &w_io, w_admission.base.epoch); W_CHECK(++steps < 1000); } while (result == 1);
        W_CHECK(!result); w_saved_proof = w_proof;
    } else w_proof = w_saved_proof;
    int admitted = reist_fat32_transaction_begin_owned(&w_tx, &w_tx_io, &w_admission,
        W_FIRST, w_sectors, (uint16_t)w_reserved);
    if (admitted) fprintf(stderr, "Owned attach refused: reserved=%u spc=%u FATs=%u status=%d effects=%u\n",
        w_reserved, w_spc, w_copies, admitted, w_effects);
    W_CHECK(!admitted);
}
#ifdef REIST_FAT32_OVERWRITE_VERSION
static unsigned w_prepare(reist_fat32_overwrite_t* writer, uint32_t offset, uint32_t length) {
    W_CHECK(!memcmp(&w_tx.admission, &w_admission, sizeof(w_admission)));
    W_CHECK(!reist_fat32_overwrite_begin(writer, &w_proof, &w_tx, offset, w_payload, length));
    unsigned steps = 0; int result;
    do {
        unsigned before = w_reads;
        result = reist_fat32_overwrite_step(writer);
        W_CHECK(w_reads-before <= 300 && ++steps < 1000 && !w_effects);
    } while (result == 1);
    W_CHECK(!result && writer->ready && writer->target_count <= 20);
    W_CHECK(w_tx.journal.entry_count == writer->target_count);
    return steps;
}
static bool w_media_matches(uint32_t offset, uint32_t length) {
    /* Verify all expected changed sectors, including an absent overlay slot.
     * Checking only sectors actually written would accept a missing suffix. */
    for (uint32_t copied = 0; copied < length;) {
        uint32_t position = offset+copied, start = position%512, amount = 512-start;
        if (amount > length-copied) amount = length-copied;
        uint32_t lba = w_lba(position);
        uint8_t expected[512], actual[512];
        w_original(lba, expected); memcpy(expected+start, w_payload+copied, amount);
        W_CHECK(!w_read(NULL, 0, lba, actual));
        if (memcmp(expected, actual, 512)) return false;
        copied += amount;
    }
    for (unsigned slot = 0; slot < 128; ++slot) {
        if (!w_disk[slot].used) continue;
        uint32_t sector = w_disk[slot].sector;
        if ((sector >= 8 && sector < 29) || (sector == 31 && w_reserved > 31)) continue;
        uint8_t expected[512]; w_original(sector, expected);
        uint32_t cluster = sector >= w_data ? 2+(sector-w_data)/w_spc : 0;
        if (cluster >= 3 && (cluster-3)%5 == 0) {
            uint32_t rank = (cluster-3)/5;
            for (unsigned byte = 0; byte < 512; ++byte) {
                uint32_t position = rank*w_spc*512+((sector-w_data)%w_spc)*512+byte;
                if (position >= offset && position-offset < length) expected[byte] = w_payload[position-offset];
            }
        }
        if (memcmp(expected, w_disk[slot].bytes, 512)) return false;
    }
    return true;
}
static void w_negatives(void) {
    for (unsigned variant = 0; variant < 16; ++variant) {
        w_reset(false);
        reist_fat32_overwrite_t writer = {0};
        uint64_t offset = 3; uint32_t length = 2000;
        if (variant == 0) w_proof.whole_volume = 0;
        if (variant == 1) --w_proof.verified_until;
        if (variant == 2) ++w_proof.epoch;
        if (variant == 3) ++w_tx.admission.base.keys[0].object_a;
        if (variant == 4) w_tx.admission.base.keys[0].alias[0] ^= 1;
        if (variant == 5) w_tx.owned = false;
        if (variant == 6) w_tx.admission.base.keys[0].resource = 1;
        if (variant == 7) w_proof.view.entry[11] |= 1;
        if (variant == 8) w_proof.view.sectors_per_cluster = 0;
        if (variant == 9) offset = UINT64_MAX;
        if (variant == 10) offset = W_LENGTH*512;
        if (variant == 11) length = 128*1024+1;
        if (variant == 12) w_now = 5001;
        if (variant == 13) W_CHECK(!file_object_guard_release(&w_guard, w_admission.pin, w_server, w_client));
        if (variant == 14) W_CHECK(!reist_fat32_transaction_stage(&w_tx, W_FIRST+W_DATA+1, w_payload));
        if (variant == 15) w_read_cut = w_reads+1;
        W_CHECK(reist_fat32_overwrite_begin(&writer, &w_proof, &w_tx, offset, w_payload, length) < 0);
        W_CHECK(!w_effects && !writer.active);
        uint32_t outcome = 0;
        (void)reist_fat32_transaction_finish(&w_tx, false, &outcome);
        W_CHECK(!w_effects && w_media_matches(0, 0));
    }
}
static unsigned w_normal(void) {
    unsigned maximum_effects = 0;
    static const uint32_t offsets[] = {0, 3, 511, 512, 9000*512+17, W_LENGTH*512-16, UINT32_MAX};
    static const uint32_t lengths[] = {128*1024, 2000, 1, 700, 128*1024, 16, 0};
    for (unsigned variant = 0; variant < sizeof(offsets)/sizeof(offsets[0]); ++variant) {
        w_reset(false);
        reist_fat32_overwrite_t writer = {0};
        unsigned steps = w_prepare(&writer, offsets[variant], lengths[variant]);
        if (variant == 4) W_CHECK(steps > 1 && w_reads < 2500);
        uint32_t outcome = 0, durable = 0;
        W_CHECK(!reist_fat32_overwrite_finish(&writer, true, &outcome, &durable));
        W_CHECK(durable == writer.bytes && w_media_matches(offsets[variant], durable));
        if (lengths[variant]) {
            W_CHECK(outcome == REIST_FILE_OBJECT_DURABLE_COMMIT && w_flushes == 4 && w_proof.ready);
            W_CHECK(w_proof.epoch == w_admission.base.epoch+2);
            W_CHECK(w_media_matches(offsets[variant], 0) == false);
        } else W_CHECK(outcome == REIST_FILE_OBJECT_NO_EFFECT && !w_effects);
        W_CHECK(!memcmp(w_stable, w_disk, sizeof(w_disk)) && !w_tx.active && !w_tx.token);
        W_CHECK(!file_object_guard_verify(&w_guard, w_admission.pin, w_server, w_client, w_now));
        if (w_effects > maximum_effects) maximum_effects = w_effects;
        unsigned before = w_effects;
        W_CHECK(reist_fat32_overwrite_finish(&writer, true, &outcome, &durable) == -REIST_ESTALE);
        W_CHECK(w_effects == before && !durable);
    }
    return maximum_effects;
}
static void w_retention(void) {
    w_reset(false);
    reist_fat32_overwrite_t writer = {0};
    uint32_t offset = 9000*512+17, outcome, durable;
    w_prepare(&writer, offset, sizeof(w_payload));
    W_CHECK(!reist_fat32_overwrite_finish(&writer, true, &outcome, &durable));
    offset += durable;
    W_CHECK(!file_object_guard_snapshot(&w_guard, &w_admission.base.epoch, w_now));
    ++w_admission.request;
    W_CHECK(!reist_fat32_transaction_begin_owned(&w_tx, &w_tx_io, &w_admission, W_FIRST, W_SECTORS, 32));
    w_effects = w_flushes = 0;
    unsigned before = w_reads;
    W_CHECK(w_prepare(&writer, offset, sizeof(w_payload)) == 1);
    W_CHECK(w_reads-before < 40); /* full sectors need only the journal's real undo read */
    W_CHECK(!reist_fat32_overwrite_finish(&writer, true, &outcome, &durable) && w_proof.ready);
    for (unsigned mode = 1; mode <= 3; ++mode) {
        w_reset(false); memset(&writer, 0, sizeof(writer));
        w_prepare(&writer, 3, 2000); w_snapshot_mode = mode;
        W_CHECK(!reist_fat32_overwrite_finish(&writer, true, &outcome, &durable));
        W_CHECK(outcome == REIST_FILE_OBJECT_DURABLE_COMMIT && durable == 2000 && !w_proof.ready);
        W_CHECK(w_media_matches(3, 2000)); /* Proven data survives loss of reusable evidence. */
    }
}
static void w_oracle_negatives(void) {
    w_reset(false);
    reist_fat32_overwrite_t writer = {0}; uint32_t outcome, durable;
    w_prepare(&writer, 3, 2000);
    W_CHECK(!reist_fat32_overwrite_finish(&writer, true, &outcome, &durable));
    W_CHECK(w_media_matches(3, durable));
    for (unsigned i = 0; i < 128; ++i) {
        if (!w_disk[i].used || w_disk[i].sector != W_DATA+w_cluster(3)-2) continue;
        w_disk[i].used = 0;
        W_CHECK(!w_media_matches(3, durable) && !w_media_matches(0, 0));
        w_disk[i].used = 1;
    }
    uint8_t bad[512]; w_original(W_DATA, bad); bad[128] ^= 1; w_write(W_DATA, bad);
    W_CHECK(!w_media_matches(3, durable) && !w_media_matches(0, 0));
}
static void w_stage_faults(void) {
    for (unsigned variant = 0; variant < 9; ++variant) {
        w_reset(false);
        reist_fat32_overwrite_t writer = {0};
        uint32_t outcome, durable;
        if (variant == 0) {
            W_CHECK(!reist_fat32_overwrite_begin(&writer, &w_proof, &w_tx, 9000*512, w_payload, 2000));
            W_CHECK(reist_fat32_overwrite_step(&writer) == 1);
        } else w_prepare(&writer, 3, 2000);
        if (variant == 1) w_now = 5001;
        if (variant == 2) w_tx.journal.pending_data[0][5] ^= 1;
        if (variant == 3) w_tx.journal.pending_data[0][0] ^= 1;
        if (variant == 4) W_CHECK(!reist_fat32_transaction_stage(&w_tx, W_FIRST+32, w_payload));
        if (variant == 5) ++w_tx.admission.request;
        if (variant == 6) { w_read_cut = w_reads+1; }
        if (variant == 7) w_entry[28] ^= 1;
        int result = reist_fat32_overwrite_finish(&writer, variant != 8, &outcome, &durable);
        if (variant == 8) W_CHECK(!result && outcome == REIST_FILE_OBJECT_NO_EFFECT);
        else W_CHECK(result < 0);
        W_CHECK(!durable && !w_effects && !w_proof.ready && w_media_matches(0, 0));
        if (variant == 5) { --w_tx.admission.request; (void)reist_fat32_transaction_finish(&w_tx, false, &outcome); }
        if (variant == 7) w_entry[28] ^= 1;
    }
}
/* Model crash restoration invokes the real RSTJ core, NOT a claim
 * that the still-missing production fenced requalification service exists. */
static bool w_recovery_read(void* context, unsigned short base, uint32_t lba, void* data, bool master) {
    (void)context; W_CHECK(!base && master && lba >= W_FIRST);
    return !w_read(NULL, 0, lba-W_FIRST, data);
}
static bool w_recovery_write(void* context, unsigned short base, uint32_t lba, const void* data, bool master) {
    (void)context; W_CHECK(!base && master && lba >= W_FIRST);
    w_write(lba-W_FIRST, data); memcpy(w_stable, w_disk, sizeof(w_disk)); return true;
}
static void w_commit_faults(unsigned effect_count) {
    static ata_undo_journal_t recovery;
    const ata_journal_transport_t transport = {.read=w_recovery_read, .write=w_recovery_write};
    for (unsigned through = 0; through <= 1; ++through) {
        for (unsigned cut = 1; cut <= effect_count; ++cut) {
            w_reset(false); w_through = through;
            reist_fat32_overwrite_t writer = {0};
            uint32_t outcome, durable;
            w_prepare(&writer, 3, sizeof(w_payload)); w_cut = cut;
            W_CHECK(reist_fat32_overwrite_finish(&writer, true, &outcome, &durable) < 0);
            W_CHECK(!durable && outcome == REIST_FILE_OBJECT_UNKNOWN && !w_proof.ready);
            W_CHECK(file_object_guard_can_open(&w_guard, 0, w_now) == -REIST_EIO);
            memcpy(w_disk, w_stable, sizeof(w_disk));
            ata_undo_journal_init(&recovery, &transport, NULL);
            W_CHECK(ata_undo_journal_attach(&recovery, 0, true, W_FIRST, w_sectors, (uint16_t)w_reserved));
            W_CHECK(w_media_matches(0, 0) || w_media_matches(3, writer.bytes));
            W_CHECK(!memcmp(w_disk, w_stable, sizeof(w_disk)));
        }
    }
}
static void w_read_faults(void) {
    w_reset(false);
    reist_fat32_overwrite_t writer = {0}; uint32_t outcome, durable;
    unsigned first = w_reads;
    w_prepare(&writer, 3, 2000);
    W_CHECK(!reist_fat32_overwrite_finish(&writer, true, &outcome, &durable));
    unsigned reads_in_operation = w_reads-first;
    for (unsigned cut = 1; cut <= reads_in_operation; ++cut) {
        w_reset(false); memset(&writer, 0, sizeof(writer));
        w_read_cut = w_reads+cut;
        int result = reist_fat32_overwrite_begin(&writer, &w_proof, &w_tx, 3, w_payload, 2000);
        if (!result) {
            do { result = reist_fat32_overwrite_step(&writer); } while (result == 1);
            result = reist_fat32_overwrite_finish(&writer, true, &outcome, &durable);
        } else {
            durable = 0;
            result = reist_fat32_transaction_finish(&w_tx, false, &outcome);
        }
        W_CHECK(result < 0 && !durable && !w_proof.ready);
        W_CHECK(outcome == (w_effects ? REIST_FILE_OBJECT_UNKNOWN : REIST_FILE_OBJECT_NO_EFFECT));
        W_CHECK(w_reads == w_read_cut); /* sticky cut, no more IO or retry */
    }
}
static void w_geometry(unsigned variant) {
    w_spc = variant == 1 ? 2 : variant == 2 ? 128 : 1;
    w_copies = variant == 3 ? 1 : 2;
    w_reserved = variant == 5 ? 29 : 32;
    w_different = variant == 4;
    w_data = w_reserved+w_copies*W_FAT; w_sectors = w_data+W_CLUSTERS*w_spc;
    w_boot[13] = (uint8_t)w_spc; w_boot[14] = (uint8_t)w_reserved; w_boot[16] = (uint8_t)w_copies;
    w_boot[40] = variant == 4 ? 0x80 : 0;
    w_put(w_boot+32, w_sectors); w_put(w_entry+28, w_length*w_spc*512);
}
static void w_layouts(void) {
    for (unsigned variant = 1; variant <= 6; ++variant) {
        w_geometry(variant); w_reset(true);
        reist_fat32_overwrite_t writer = {0};
        uint32_t offset = w_spc*512-3, outcome, durable;
        if (variant == 6) {
            w_different = 1; /* changed mirrored link is rejected on fresh token IO */
            W_CHECK(!reist_fat32_overwrite_begin(&writer, &w_proof, &w_tx, offset, w_payload, 2000));
            W_CHECK(reist_fat32_overwrite_step(&writer) < 0);
            W_CHECK(reist_fat32_overwrite_finish(&writer, true, &outcome, &durable) < 0);
            W_CHECK(outcome == REIST_FILE_OBJECT_NO_EFFECT && !w_effects && !durable);
        } else {
            w_prepare(&writer, offset, 2000);
            W_CHECK(!reist_fat32_overwrite_finish(&writer, true, &outcome, &durable));
            W_CHECK(durable == 2000 && w_flushes == 4 && w_proof.ready && w_media_matches(offset, durable));
        }
    }
    /* The newly admitted single-header layout must preserve all four commit
     * barriers and exact recovery at every effect/read cut too. */
    w_geometry(5); w_reset(true);
    reist_fat32_overwrite_t writer = {0}; uint32_t outcome, durable;
    w_prepare(&writer, 3, sizeof(w_payload));
    W_CHECK(!reist_fat32_overwrite_finish(&writer, true, &outcome, &durable));
    W_CHECK(outcome == REIST_FILE_OBJECT_DURABLE_COMMIT && w_effects == 46 && w_flushes == 4);
    W_CHECK(w_media_matches(3, durable));
    w_commit_faults(46); w_read_faults();
    w_geometry(0); w_reset(true);
}
#endif
#ifdef REIST_FAT32_SHRINK_VERSION
static void w_shrink_expected(uint32_t lba, uint32_t size, uint32_t released, uint8_t* bytes) {
    w_original(lba, bytes);
    uint32_t retained = w_length-released;
    if (lba == w_data) {
        w_put(bytes+28, size);
        if (!retained) bytes[20] = bytes[21] = bytes[26] = bytes[27] = 0;
    } else if (released && (lba == 1 || lba == 7)) {
        w_put(bytes+488, UINT32_MAX); w_put(bytes+492, UINT32_MAX);
    } else if (released && lba >= w_reserved && lba < w_data) {
        uint32_t copy = (lba-w_reserved)/W_FAT;
        if ((w_boot[40]&0x80) && copy != (w_boot[40]&15)) return;
        uint32_t first = ((lba-w_reserved)%W_FAT)*128;
        for (unsigned i = 0; i < 128; ++i) {
            uint32_t cluster = first+i;
            if (cluster < 3 || (cluster-3)%w_stride) continue;
            uint32_t rank = (cluster-3)/w_stride;
            if (rank >= w_length) continue;
            if (rank >= retained || (retained && rank+1 == retained)) {
                uint8_t high = bytes[4*i+3]&0xf0;
                w_put(bytes+4*i, rank >= retained ? 0 : 0xfffffff);
                bytes[4*i+3] |= high;
            }
        }
    }
}
static bool w_shrink_matches(uint32_t size, uint32_t released) {
    /* Every possible metadata target, including a missing suffix/FAT copy;
     * all other modified sectors must remain exactly their initial bytes. */
    uint8_t expected[512], actual[512];
    for (uint32_t lba = 0; lba <= w_data; ++lba) {
        if (lba != 1 && lba != 7 && lba != w_data && lba < w_reserved) continue;
        w_shrink_expected(lba, size, released, expected);
        W_CHECK(!w_read(NULL, 0, lba, actual));
        if (memcmp(expected, actual, 512)) return false;
    }
    for (unsigned i = 0; i < 128; ++i) if (w_disk[i].used) {
        uint32_t lba = w_disk[i].sector;
        if ((lba >= 8 && lba < 29) || (w_reserved > 31 && lba == 31)) continue;
        w_shrink_expected(lba, size, released, expected);
        if (memcmp(expected, w_disk[i].bytes, 512)) return false;
    }
    return true;
}
static unsigned w_shrink_prepare(reist_fat32_shrink_t* s, uint32_t target) {
    W_CHECK(!reist_fat32_shrink_begin(s, &w_proof, &w_tx, target));
    int result; unsigned steps = 0;
    do {
        unsigned before = w_reads;
        result = reist_fat32_shrink_step(s);
        W_CHECK(w_reads-before <= 300 && ++steps < 1000 && !w_effects);
    } while (result == 1);
    W_CHECK(!result && w_tx.journal.entry_count <= 20);
    W_CHECK(!w_tx.staging && !w_tx.stage_count && !w_tx.stage_first);
    for(unsigned i=0;i<sizeof(w_tx.stage_before);++i) W_CHECK(!((uint8_t*)w_tx.stage_before)[i]);
    for(unsigned i=0;i<sizeof(w_tx.stage_after);++i) W_CHECK(!w_tx.stage_after[i]);
    for(unsigned i=1;i<w_tx.journal.entry_count;++i)
        W_CHECK(w_tx.journal.entries[i-1].target_lba < w_tx.journal.entries[i].target_lba);
    return steps;
}
static void w_shrink_cuts(void) {
    const ata_journal_transport_t transport = {.read=w_recovery_read, .write=w_recovery_write};
    static ata_undo_journal_t recovery;
    for (unsigned layout = 0; layout < 3; ++layout) {
        w_length = layout == 2 ? 3 : 400; w_stride = layout == 2 ? 5 : 128;
        w_geometry(layout == 1 ? 5 : 0); w_reset(true);
        reist_fat32_shrink_t s = {0}; uint32_t outcome, size, released;
        w_shrink_prepare(&s, 0);
        W_CHECK(!reist_fat32_shrink_finish(&s, true, &outcome, &size, &released));
        unsigned effects = w_effects;
        W_CHECK(w_shrink_matches(size, released));
        for (unsigned through = 0; through <= 1; ++through) for (unsigned cut = 1; cut <= effects; ++cut) {
            w_reset(false); memset(&s, 0, sizeof(s)); w_through = through;
            w_shrink_prepare(&s, 0); w_cut = cut;
            W_CHECK(reist_fat32_shrink_finish(&s, true, &outcome, &size, &released) < 0);
            W_CHECK(outcome == REIST_FILE_OBJECT_UNKNOWN && !size && !released && !w_proof.ready);
            W_CHECK(file_object_guard_can_open(&w_guard, 0, w_now) == -REIST_EIO);
            memcpy(w_disk, w_stable, sizeof(w_disk));
            ata_undo_journal_init(&recovery, &transport, NULL);
            W_CHECK(ata_undo_journal_attach(&recovery, 0, true, W_FIRST, w_sectors, (uint16_t)w_reserved));
            W_CHECK(w_shrink_matches(w_length*w_spc*512, 0) || w_shrink_matches(s.resulting_size, s.released));
        }
    }
}
static uint32_t w_get(const uint8_t* p);
static void w_shrink_negatives(void) {
    w_length = 400; w_stride = 128; w_geometry(0); w_reset(true);
    /* Corruption after begin must be found in the fresh bulk undo images,
     * not hidden by the earlier suffix/terminal hints. No effect is allowed. */
    for(unsigned variant=0;variant<4;++variant) {
        w_reset(false); reist_fat32_shrink_t s={0};
        W_CHECK(!reist_fat32_shrink_begin(&s,&w_proof,&w_tx,0));
        uint32_t cluster=w_cluster(variant<2 ? w_length-2 : w_length-1);
        uint32_t lba=w_reserved+(variant&1U)*W_FAT+cluster/128;
        uint8_t bytes[512]; W_CHECK(!w_read(NULL,0,lba,bytes));
        uint32_t old=w_get(bytes+(cluster%128)*4);
        w_put(bytes+(cluster%128)*4,(old&0xf0000000U)|(variant<2 ? cluster : 0x0ffffff8U));
        w_write(lba,bytes);
        int status; unsigned steps=0;
        do { status=reist_fat32_shrink_step(&s); W_CHECK(++steps<1000); } while(status==1);
        W_CHECK(status<0 && !w_effects && !w_proof.ready);
        uint32_t outcome=0,size=0,released=0;
        W_CHECK(reist_fat32_shrink_finish(&s,true,&outcome,&size,&released)<0);
        W_CHECK(!w_effects && !released && outcome==REIST_FILE_OBJECT_NO_EFFECT);
    }
    for (unsigned variant = 0; variant < 14; ++variant) {
        w_reset(false);
        reist_fat32_shrink_t s = {0}; uint32_t outcome, size, released;
        w_shrink_prepare(&s, 0);
        /* Transaction reads see staged metadata; identity reads must not. */
        uint8_t pending[512], media[512];
        W_CHECK(!reist_fat32_transaction_read(&w_tx, W_FIRST+w_data, pending));
        W_CHECK(!reist_fat32_transaction_read_media(&w_tx, W_FIRST+w_data, media));
        W_CHECK(memcmp(pending, media, 512) && !memcmp(media, w_entry, 512));
        if (variant == 0) w_now = 5001;
        if (variant == 1) w_tx.journal.pending_data[0][128] ^= 1;
        if (variant == 2) w_tx.journal.pending_data[1][100] ^= 1;
        if (variant == 3) W_CHECK(!reist_fat32_transaction_stage(&w_tx, W_FIRST+w_data+1, w_payload));
        if (variant == 4) ++w_tx.admission.request;
        if (variant == 5) w_read_cut = w_reads+1;
        if (variant == 6) w_entry[28] ^= 1;
        if (variant == 7) ++s.resulting_view.object.object_generation;
        if (variant == 8) ++s.resulting_size;
        if (variant == 9) W_CHECK(!file_object_guard_release(&w_guard, w_admission.pin, w_server, w_client));
        if (variant == 10) --s.released;
        if (variant == 12) w_proof.view.sectors_per_cluster = 0;
        if (variant == 13) w_proof.view.object.locator_b = UINT32_MAX;
        int result = reist_fat32_shrink_finish(&s, variant != 11, &outcome, &size, &released);
        if (variant == 11) W_CHECK(!result && outcome == REIST_FILE_OBJECT_NO_EFFECT);
        else W_CHECK(result < 0);
        W_CHECK(!released && !w_effects && !w_proof.ready);
        if (variant == 4) { --w_tx.admission.request; (void)reist_fat32_transaction_finish(&w_tx, false, &outcome); }
        if (variant == 6) w_entry[28] ^= 1;
        w_read_cut = 0;
        W_CHECK(w_shrink_matches(w_length*w_spc*512, 0));
    }
    /* Every read cut, including final physical identity and commit readback. */
    w_reset(false);
    reist_fat32_shrink_t s = {0}; uint32_t outcome, size, released;
    unsigned before = w_reads;
    w_shrink_prepare(&s, 0);
    W_CHECK(!reist_fat32_shrink_finish(&s, true, &outcome, &size, &released));
    unsigned reads = w_reads-before;
    static ata_undo_journal_t recovery;
    const ata_journal_transport_t transport = {.read=w_recovery_read, .write=w_recovery_write};
    for (unsigned through = 0; through <= 1; ++through) for (unsigned cut = 1; cut <= reads; ++cut) {
        w_reset(false); memset(&s, 0, sizeof(s)); w_read_cut = w_reads+cut;
        w_through = through;
        int result = reist_fat32_shrink_begin(&s, &w_proof, &w_tx, 0);
        if (!result) do { result = reist_fat32_shrink_step(&s); } while (result == 1);
        if (s.owner.active) result = reist_fat32_shrink_finish(&s, true, &outcome, &size, &released);
        else { released = 0; result = reist_fat32_transaction_finish(&w_tx, false, &outcome); }
        W_CHECK(result < 0 && !released && !w_proof.ready && w_reads == w_read_cut);
        W_CHECK(outcome == (w_effects ? REIST_FILE_OBJECT_UNKNOWN : REIST_FILE_OBJECT_NO_EFFECT));
        if (w_effects) W_CHECK(file_object_guard_can_open(&w_guard, 0, w_now) == -REIST_EIO);
        w_read_cut = 0;
        memcpy(w_disk, w_stable, sizeof(w_disk));
        ata_undo_journal_init(&recovery, &transport, NULL);
        W_CHECK(ata_undo_journal_attach(&recovery, 0, true, W_FIRST, w_sectors, (uint16_t)w_reserved));
        W_CHECK(w_shrink_matches(w_length*w_spc*512, 0) || w_shrink_matches(s.resulting_size, s.released));
    }
}
static int w_stage_transform(void* context, uint32_t lba, uint8_t* bytes) {
    unsigned mode=*(unsigned*)context;
    if(mode==1) return 1;
    if(mode==2) return -REIST_ESTALE;
    if(mode==3) { uint32_t outcome=0; return reist_fat32_transaction_finish(&w_tx,true,&outcome); }
    if(mode==4) return reist_fat32_transaction_read_media(&w_tx,lba,bytes);
    if(mode==5) return reist_fat32_transaction_read(&w_tx,lba,bytes);
    if(mode==6) return reist_fat32_transaction_flush_owned(&w_tx);
    if(mode==7) return reist_fat32_transaction_stage(&w_tx,lba,bytes);
    bytes[0]^=1;
    return 0;
}
static void w_stage_images_tests(void) {
    w_length=400; w_stride=5; w_geometry(0); w_reset(true);
    for(unsigned variant=0;variant<19;++variant) {
        w_reset(false);
        uint32_t targets[2]={W_FIRST+w_data+1,W_FIRST+w_data+2};
        unsigned mode=variant<8 ? variant : 0;
        unsigned count=2, before=w_reads, requests=w_read_requests;
        const uint32_t* manifest=targets;
        reist_fat32_stage_image_fn transform=w_stage_transform;
        if(variant==8) count=0;
        if(variant==9) count=21;
        if(variant==10) manifest=NULL;
        if(variant==11) transform=NULL;
        if(variant==12) targets[1]=targets[0];
        if(variant==13) targets[1]=targets[0]-1;
        if(variant==14) targets[0]=W_FIRST-1;
        if(variant==15) targets[1]=W_FIRST+w_sectors;
        if(variant==16) targets[0]=W_FIRST+ATA_JOURNAL_HEADER_OFFSET;
        if(variant==17) targets[0]=w_tx.journal.mirror_lba;
        if(variant==18) w_tx.owned=false;
        int status=reist_fat32_transaction_stage_images(&w_tx,manifest,count,transform,&mode);
        W_CHECK(!w_effects && !w_tx.staging && !w_tx.stage_count && !w_tx.stage_first);
        for(unsigned i=0;i<sizeof(w_tx.stage_before);++i) W_CHECK(!((uint8_t*)w_tx.stage_before)[i]);
        for(unsigned i=0;i<sizeof(w_tx.stage_after);++i) W_CHECK(!w_tx.stage_after[i]);
        if(!variant) {
            W_CHECK(!status && w_reads-before==2 && w_read_requests-requests==1 && w_tx.journal.entry_count==2);
            for(unsigned i=0;i<2;++i) {
                uint8_t original[512]; w_original(targets[i]-W_FIRST,original);
                W_CHECK(!memcmp(original,w_tx.journal.undo_data[i],512)); original[0]^=1;
                W_CHECK(!memcmp(original,w_tx.journal.pending_data[i],512));
            }
        } else {
            W_CHECK(status<0 && !w_tx.journal.entry_count);
            W_CHECK(w_reads-before==(variant<8?2U:0U));
        }
        uint32_t outcome=0;
        (void)reist_fat32_transaction_finish(&w_tx,false,&outcome);
        W_CHECK(!w_effects && outcome==REIST_FILE_OBJECT_NO_EFFECT && !w_tx.active);
    }
}
static void w_shrink_retention(void) {
    w_stage_images_tests();
    w_length = 400; w_stride = 128; w_geometry(0); w_reset(true);
    reist_fat32_shrink_t s = {0}; uint32_t outcome, size, released;
    for(unsigned lba=1;lba<=7;lba+=6) {
        uint8_t bytes[512]; W_CHECK(!w_read(NULL,0,lba,bytes));
        w_put(bytes+488,UINT32_MAX); w_put(bytes+492,UINT32_MAX); w_write(lba,bytes);
    }
    w_shrink_prepare(&s,0);
    W_CHECK(!s.fsinfo_count && w_tx.journal.entry_count<=19);
    W_CHECK(!reist_fat32_shrink_finish(&s,true,&outcome,&size,&released));
    W_CHECK(w_shrink_matches(size,released));
    w_reset(false); memset(&s,0,sizeof(s));
    unsigned total = 0;
    for (unsigned step = 0; step < 5; ++step) {
        if (step) {
            W_CHECK(!file_object_guard_snapshot(&w_guard, &w_admission.base.epoch, w_now));
            ++w_admission.request;
            W_CHECK(!reist_fat32_transaction_begin_owned(&w_tx, &w_tx_io, &w_admission,
                W_FIRST, w_sectors, (uint16_t)w_reserved));
            w_effects = w_flushes = 0;
        }
        unsigned before = w_reads;
        unsigned writes_before=w_write_requests;
        unsigned requests_before=w_read_requests;
        W_CHECK(w_shrink_prepare(&s, 0) == 1 && w_reads-before < 80);
        printf("R342 shrink-stage sectors=%u requests=%u\n",w_reads-before,w_read_requests-requests_before);
        W_CHECK(w_reads-before <= 48);
        /* Six live geometry/FSInfo reads plus five exact runs:
         * two FSInfo sectors, two mirrored FAT runs and the directory. */
        W_CHECK(w_read_requests-requests_before <= 11);
        W_CHECK(!reist_fat32_shrink_finish(&s, true, &outcome, &size, &released) && w_proof.ready);
        W_CHECK(w_write_requests-writes_before<=10 && w_flushes==4);
        for(unsigned i=0;i<REIST_FAT32_SEEK_ANCHORS;++i) {
            uint64_t rank=(uint64_t)i*w_proof.seek_stride;
            W_CHECK(w_proof.seek_anchors[i]==(rank<w_proof.chain_count?w_cluster((unsigned)rank):0));
        }
        total += released;
        W_CHECK(w_shrink_matches(size, total));
    }
    for (unsigned mode = 1; mode <= 3; ++mode) {
        w_reset(false); memset(&s, 0, sizeof(s)); w_shrink_prepare(&s, 0); w_snapshot_mode = mode;
        W_CHECK(!reist_fat32_shrink_finish(&s, true, &outcome, &size, &released));
        W_CHECK(outcome == REIST_FILE_OBJECT_DURABLE_COMMIT && released && !w_proof.ready);
        W_CHECK(w_shrink_matches(size, released));
    }
    w_length=10000; w_stride=5; w_geometry(0); w_reset(true);
    /* A valid but depleted tail hint must not force another cold head scan. */
    w_proof.tail_first=w_proof.chain_count-1; w_proof.seek_cluster=0;
    memset(&s,0,sizeof(s)); unsigned before=w_reads, requests_before=w_read_requests;
    w_shrink_prepare(&s,0);
    printf("R342 shrink-refill reads=%u requests=%u\n",w_reads-before,w_read_requests-requests_before);
    W_CHECK(w_reads-before<180);
    W_CHECK(w_read_requests-requests_before<60);
    /* Includes failures inside both prefetched FAT runs, before any effect. */
    for(unsigned cut=1;cut<=136;++cut) {
        w_reset(false); w_proof.tail_first=w_proof.chain_count-1; w_proof.seek_cluster=0;
        memset(&s,0,sizeof(s)); w_read_cut=w_reads+cut;
        int status=reist_fat32_shrink_begin(&s,&w_proof,&w_tx,0);
        unsigned steps=0;
        while(!status || status==1) {
            unsigned prior=w_reads;
            status=reist_fat32_shrink_step(&s);
            W_CHECK(w_reads-prior<=300 && ++steps<1000);
            if(!status) break;
        }
        W_CHECK(status<0 && w_reads==w_read_cut && !w_effects && !w_proof.ready);
        uint32_t ignored=0;
        (void)reist_fat32_transaction_finish(&w_tx,false,&ignored);
        W_CHECK(!w_effects && ignored==REIST_FILE_OBJECT_NO_EFFECT);
    }
    for(unsigned variant=0;variant<3;++variant) {
        w_reset(false); w_proof.tail_first=w_proof.chain_count-1; w_proof.seek_cluster=0;
        if(!variant) w_proof.seek_stride=0;
        if(variant==1) w_proof.seek_stride=3;
        if(variant==2) w_proof.seek_anchors[(w_proof.tail_first-REIST_FAT32_TAIL_CACHE)/w_proof.seek_stride]=1;
        memset(&s,0,sizeof(s));
        int status=reist_fat32_shrink_begin(&s,&w_proof,&w_tx,0);
        for(unsigned step=0; !status && !s.owner.ready && step<1000; ++step) {
            status=reist_fat32_shrink_step(&s);
            if(status==1) status=0;
        }
        W_CHECK(status<0 && !w_effects && !w_proof.ready);
    }
}
static void w_shrink_edges(void) {
    uint32_t outcome, size, released;
    for (unsigned variant = 0; variant < 4; ++variant) {
        w_length = variant == 3 ? 65999 : 3; w_stride = variant == 3 ? 1 : 5;
        w_geometry(0);
        uint32_t original_size = variant == 0 ? 0 : variant == 1 ? 1 : w_length*512;
        w_put(w_entry+28, original_size); w_reset(true);
        reist_fat32_shrink_t s = {0};
        uint32_t target = variant == 2 ? original_size : variant == 3 ? original_size-512 : 0;
        w_shrink_prepare(&s, target);
        W_CHECK(!reist_fat32_shrink_finish(&s, true, &outcome, &size, &released));
        if (variant == 2) W_CHECK(outcome == REIST_FILE_OBJECT_NO_EFFECT && !w_effects && size == original_size && !released);
        else {
            W_CHECK(outcome == REIST_FILE_OBJECT_DURABLE_COMMIT && size == target && released);
            W_CHECK(w_shrink_matches(size, released) && w_proof.ready);
            if (!size) {
                x86os_file_info_t info;
                W_CHECK(reist_vfs_shadow_fat_object_stat(&w_io, &w_object, &info) == -REIST_ESTALE);
                W_CHECK(!reist_vfs_shadow_fat_object_stat(&w_io, &w_proof.view.object, &info));
            } else {
                uint32_t kind;
                W_CHECK(!reist_fat32_ownership_query(&w_proof, w_proof.epoch, w_cluster(w_length-1), &kind));
                W_CHECK(kind == REIST_FAT32_CLUSTER_FREE);
            }
        }
    }
    w_length = 3; w_stride = 5; w_geometry(0); w_reset(true);
    for (unsigned variant = 0; variant < 8; ++variant) {
        w_reset(false); reist_fat32_shrink_t s = {0};
        uint64_t target = 0;
        if (variant == 0) target = UINT64_MAX;
        if (variant == 1) target = w_length*512+1;
        if (variant == 2) w_proof.chain_count = 0;
        if (variant == 3) w_proof.tail_first = w_proof.chain_count+1;
        if (variant == 4) w_proof.whole_volume = 0;
        if (variant == 5) w_proof.view.fsinfo_sector = 8;
        if (variant == 6) w_now = 5001;
        if (variant == 7) w_proof.view.entry[11] |= 1;
        W_CHECK(reist_fat32_shrink_begin(&s, &w_proof, &w_tx, target) < 0);
        W_CHECK(!w_effects && !w_proof.ready);
        if (s.owner.active) (void)reist_fat32_shrink_finish(&s, false, &outcome, &size, &released);
        else (void)reist_fat32_transaction_finish(&w_tx, false, &outcome);
        W_CHECK(!w_effects && w_shrink_matches(w_length*512, 0));
    }
    w_reset(false);
    reist_fat32_shrink_t s = {0}; w_shrink_prepare(&s, 0);
    W_CHECK(!reist_fat32_shrink_finish(&s, true, &outcome, &size, &released));
    W_CHECK(w_shrink_matches(size, released));
    /* Deliberately remove one FAT copy: neither a partial final image nor an
     * untouched-media claim may satisfy the independent oracle. */
    bool removed = false;
    for (unsigned i = 0; i < 128; ++i) if (w_disk[i].used && w_disk[i].sector == w_reserved+W_FAT) {
        w_disk[i].used = 0; removed = true;
        W_CHECK(!w_shrink_matches(size, released) && !w_shrink_matches(w_length*512, 0));
        w_disk[i].used = 1;
    }
    W_CHECK(removed);
    uint8_t bytes[512]; w_original(w_data+1, bytes); bytes[7] ^= 1; w_write(w_data+1, bytes);
    W_CHECK(!w_shrink_matches(size, released) && !w_shrink_matches(w_length*512, 0));
}
#endif
static void w_shrink_tests(void) {
#ifndef REIST_FAT32_SHRINK_VERSION
    W_CHECK(0 && "Missing owned tail-first resize planner");
#else
    W_CHECK(sizeof(w_proof) <= 48U*1024);
    for (unsigned variant = 0; variant < 8; ++variant) {
        w_length = variant == 1 ? 3 : variant == 2 ? 1 : variant == 3 ? 400 : W_LENGTH;
        w_stride = variant == 3 ? 128 : variant == 4 ? 1 : 5;
        w_geometry(variant == 4 ? 3 : variant == 5 ? 2 : variant == 6 ? 4 : variant == 7 ? 5 : 0);
        w_entry[20] = w_entry[21] = 0; w_entry[26] = 3; w_entry[27] = 0;
        w_reset(true);
        uint32_t target = variant == 0 ? w_length*512-700 : variant == 5 ? w_length*w_spc*512-1 : 0;
        reist_fat32_shrink_t shrink = {0};
        W_CHECK(!reist_fat32_shrink_begin(&shrink, &w_proof, &w_tx, target));
        int result; unsigned steps = 0;
        do {
            unsigned before = w_reads;
            result = reist_fat32_shrink_step(&shrink);
            W_CHECK(w_reads-before <= 300 && ++steps < 1000 && !w_effects);
        } while (result == 1);
        W_CHECK(!result && w_tx.journal.entry_count <= 20);
        uint32_t outcome, size, released;
        result = reist_fat32_shrink_finish(&shrink, true, &outcome, &size, &released);
        if (result) fprintf(stderr, "Shrink variant=%u result=%d outcome=%u released=%u targets=%u\n",
            variant, result, outcome, shrink.released, shrink.owner.target_count);
        W_CHECK(!result);
        W_CHECK(outcome == REIST_FILE_OBJECT_DURABLE_COMMIT && size >= target);
        W_CHECK(size == target || released > 0);
        W_CHECK(w_flushes == 4 && w_proof.ready && w_proof.view.file_size == size);
        W_CHECK(w_proof.chain_count == w_length-released);
        if (variant == 1 || variant == 2) W_CHECK(!size && released == w_length && !w_proof.view.object.locator_c);
        if (variant == 3) W_CHECK(released == 7); /* 3 metadata + 2*(7 freed + predecessor) */
        if (variant == 4) W_CHECK(released > 1024); /* capacity, not tail-cache length, splits a step */
        W_CHECK(w_shrink_matches(size, released));
        x86os_file_info_t info;
        W_CHECK(!reist_vfs_shadow_fat_object_stat(&w_io, &w_proof.view.object, &info));
        /* Independent complete namespace/ownership verification, not just cached size. */
        static reist_fat32_ownership_t recovered;
        W_CHECK(!reist_fat32_volume_begin(&recovered, &w_io, &w_proof.view.object, w_proof.epoch));
        do { result = reist_fat32_ownership_step(&recovered, &w_io, w_proof.epoch); } while (result == 1);
        W_CHECK(!result && recovered.chain_count == w_length-released);
    }
    w_shrink_cuts(); w_shrink_negatives(); w_shrink_retention(); w_shrink_edges();
    w_length = W_LENGTH; w_stride = 5; w_geometry(0); w_reset(true);
#endif
}
#ifdef REIST_FAT32_GROW_VERSION
static uint32_t w_get(const uint8_t* p) {
    return p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static unsigned w_grow_allocations(uint32_t size, uint32_t* clusters) {
    uint32_t required = (uint32_t)(((uint64_t)size+w_spc*512-1)/(w_spc*512));
    unsigned count = required > w_length ? required-w_length : 0;
    W_CHECK(count <= 128);
    uint32_t candidate = 3;
    for (unsigned i = 0; i < count; ++i) {
        while ((candidate-3)%w_stride == 0 && (candidate-3)/w_stride < w_length) ++candidate;
        W_CHECK(candidate <= W_CLUSTERS+1);
        clusters[i] = candidate++;
    }
    return count;
}
static void w_grow_expected(uint32_t lba, uint32_t size, bool append,
    const uint32_t* clusters, unsigned count, uint8_t* bytes) {
    w_original(lba, bytes);
    if (lba == w_data) {
        w_put(bytes+28, size);
        if (!w_length && count) {
            bytes[26] = (uint8_t)clusters[0]; bytes[27] = (uint8_t)(clusters[0]>>8);
            bytes[20] = (uint8_t)(clusters[0]>>16); bytes[21] = (uint8_t)(clusters[0]>>24);
        }
    } else if (count && w_boot[48] == 1 && !w_boot[49] &&
        (lba == 1 || (lba == 7 && w_boot[50] == 6)) && w_get(bytes) == 0x41615252) {
        w_put(bytes+488, UINT32_MAX); w_put(bytes+492, UINT32_MAX);
    } else if (count && lba >= w_reserved && lba < w_data) {
        uint32_t copy = (lba-w_reserved)/W_FAT;
        if ((w_boot[40]&0x80) && copy != (w_boot[40]&15)) return;
        uint32_t base = ((lba-w_reserved)%W_FAT)*128;
        for (unsigned entry = 0; entry < 128; ++entry) {
            uint32_t cluster = base+entry, value = 0; bool changed = false;
            if (w_length && cluster == w_cluster(w_length-1)) { value = clusters[0]; changed = true; }
            for (unsigned i = 0; i < count; ++i) if (cluster == clusters[i]) {
                value = i+1 == count ? 0xfffffff : clusters[i+1]; changed = true;
            }
            if (changed) w_put(bytes+entry*4, (w_get(bytes+entry*4)&0xf0000000)|value);
        }
    } else if (lba > w_data) {
        uint32_t cluster = 2+(lba-w_data)/w_spc, rank = UINT32_MAX;
        if (cluster >= 3 && (cluster-3)%w_stride == 0 && (cluster-3)/w_stride < w_length)
            rank = (cluster-3)/w_stride;
        for (unsigned i = 0; i < count; ++i) if (cluster == clusters[i]) rank = w_length+i;
        if (rank != UINT32_MAX) for (unsigned i = 0; i < 512; ++i) {
            uint64_t position = (uint64_t)rank*w_spc*512+((lba-w_data)%w_spc)*512+i;
            uint32_t old_size = w_get(w_entry+28);
            if (position >= old_size && position < size)
                bytes[i] = append ? w_payload[position-old_size] : 0;
        }
    }
}
static bool w_grow_matches(uint32_t size, bool append) {
    uint32_t clusters[128]; unsigned count = w_grow_allocations(size, clusters);
    uint8_t expected[512], actual[512];
    for (uint32_t lba = 0; lba <= w_data; ++lba) {
        if (lba != 1 && lba != 7 && lba != w_data && lba < w_reserved) continue;
        w_grow_expected(lba, size, append, clusters, count, expected);
        W_CHECK(!w_read(NULL, 0, lba, actual));
        if (memcmp(actual, expected, 512)) return false;
    }
    for (uint32_t position = w_get(w_entry+28); position < size;) {
        uint32_t rank = position/(w_spc*512);
        uint32_t cluster = rank < w_length ? w_cluster(rank) : clusters[rank-w_length];
        uint32_t lba = w_data+(cluster-2)*w_spc+(position/512)%w_spc;
        w_grow_expected(lba, size, append, clusters, count, expected);
        W_CHECK(!w_read(NULL, 0, lba, actual));
        if (memcmp(actual, expected, 512)) return false;
        uint32_t amount = 512-position%512;
        if (amount > size-position) amount = size-position;
        position += amount;
    }
    for (unsigned i = 0; i < 128; ++i) if (w_disk[i].used) {
        uint32_t lba = w_disk[i].sector;
        if ((lba >= 8 && lba < 29) || (w_reserved > 31 && lba == 31)) continue;
        w_grow_expected(lba, size, append, clusters, count, expected);
        if (memcmp(w_disk[i].bytes, expected, 512)) return false;
    }
    return true;
}
static unsigned w_grow_prepare(reist_fat32_grow_t* g, bool append, uint32_t amount, uint32_t input_offset) {
    int result = append ? reist_fat32_append_begin(g, &w_proof, &w_tx, w_payload+input_offset, amount) :
        reist_fat32_grow_begin(g, &w_proof, &w_tx, (uint64_t)w_proof.view.file_size+amount);
    W_CHECK(!result);
    unsigned steps = 0;
    do {
        unsigned before = w_reads;
        result = reist_fat32_grow_step(g);
        W_CHECK(w_reads-before <= 300 && ++steps < 1000 && !w_effects);
    } while (result == 1);
    if (result) fprintf(stderr, "Growth prepare error=%d mapped=%u allocated=%u targets=%u\n",
        result, g->owner.bytes, g->allocated_count, g->owner.target_count);
    W_CHECK(!result && w_tx.journal.entry_count <= 20);
    return steps;
}
static void w_grow_fixture(unsigned layout) {
    w_length = layout == 2 ? 0 : 400; w_stride = 128;
    w_geometry(layout == 1 ? 5 : layout == 2 ? 2 : 0);
    w_entry[20] = w_entry[21] = w_entry[27] = 0; w_entry[26] = w_length ? 3 : 0;
    w_reset(true);
}
static void w_grow_cuts(void) {
    const ata_journal_transport_t transport = {.read=w_recovery_read, .write=w_recovery_write};
    static ata_undo_journal_t recovery;
    for (unsigned layout = 0; layout < 3; ++layout) for (unsigned append = 0; append <= 1; ++append) {
        w_grow_fixture(layout);
        reist_fat32_grow_t g = {0}; uint32_t outcome, size, durable;
        w_grow_prepare(&g, append != 0, 70000, 0);
        W_CHECK(!reist_fat32_grow_finish(&g, true, &outcome, &size, &durable));
        unsigned effects = w_effects;
        W_CHECK(w_grow_matches(size, append != 0));
        for (unsigned through = 0; through <= 1; ++through) for (unsigned cut = 1; cut <= effects; ++cut) {
            w_reset(false); memset(&g, 0, sizeof(g)); w_through = through;
            w_grow_prepare(&g, append != 0, 70000, 0); w_cut = cut;
            W_CHECK(reist_fat32_grow_finish(&g, true, &outcome, &size, &durable) < 0);
            W_CHECK(outcome == REIST_FILE_OBJECT_UNKNOWN && !size && !durable && !w_proof.ready);
            W_CHECK(file_object_guard_can_open(&w_guard, 0, w_now) == -REIST_EIO);
            memcpy(w_disk, w_stable, sizeof(w_disk));
            ata_undo_journal_init(&recovery, &transport, NULL);
            W_CHECK(ata_undo_journal_attach(&recovery, 0, true, W_FIRST, w_sectors, (uint16_t)w_reserved));
            W_CHECK(w_grow_matches(w_get(w_entry+28), false) || w_grow_matches(g.resulting_view.file_size, append != 0));
        }
    }
    /* Every read boundary also restores exactly old or step-final media. */
    w_grow_fixture(0);
    reist_fat32_grow_t g = {0}; uint32_t outcome, size, durable;
    unsigned before = w_reads;
    w_grow_prepare(&g, true, 70000, 0);
    W_CHECK(!reist_fat32_grow_finish(&g, true, &outcome, &size, &durable));
    unsigned reads = w_reads-before;
    for (unsigned through = 0; through <= 1; ++through) for (unsigned cut = 1; cut <= reads; ++cut) {
        w_reset(false); memset(&g, 0, sizeof(g)); w_read_cut = w_reads+cut; w_through = through;
        int result = reist_fat32_append_begin(&g, &w_proof, &w_tx, w_payload, 70000);
        if (!result) do { result = reist_fat32_grow_step(&g); } while (result == 1);
        if (g.owner.active) result = reist_fat32_grow_finish(&g, true, &outcome, &size, &durable);
        else { durable = 0; result = reist_fat32_transaction_finish(&w_tx, false, &outcome); }
        W_CHECK(result < 0 && !durable && !w_proof.ready && w_reads == w_read_cut);
        W_CHECK(outcome == (w_effects ? REIST_FILE_OBJECT_UNKNOWN : REIST_FILE_OBJECT_NO_EFFECT));
        if (w_effects) W_CHECK(file_object_guard_can_open(&w_guard, 0, w_now) == -REIST_EIO);
        w_read_cut = 0; memcpy(w_disk, w_stable, sizeof(w_disk));
        ata_undo_journal_init(&recovery, &transport, NULL);
        W_CHECK(ata_undo_journal_attach(&recovery, 0, true, W_FIRST, w_sectors, (uint16_t)w_reserved));
        W_CHECK(w_grow_matches(w_get(w_entry+28), false) || w_grow_matches(g.resulting_view.file_size, true));
    }
}
static void w_grow_negatives(void) {
    w_grow_fixture(0);
    for (unsigned variant = 0; variant < 12; ++variant) {
        w_reset(false); reist_fat32_grow_t g = {0}; uint32_t outcome, size, durable;
        w_grow_prepare(&g, true, 70000, 0);
        if (variant == 0) w_now = 5001;
        if (variant == 1) w_tx.journal.pending_data[0][128] ^= 1;
        if (variant == 2) w_tx.journal.pending_data[w_tx.journal.entry_count-1][100] ^= 1;
        if (variant == 3) W_CHECK(!file_object_guard_release(&w_guard, w_admission.pin, w_server, w_client));
        if (variant == 4) ++w_tx.admission.request;
        if (variant == 5) w_payload[0] ^= 1;
        if (variant == 6) w_entry[28] ^= 1;
        if (variant == 7) ++g.resulting_view.object.object_generation;
        if (variant == 8) --g.allocated_count;
        if (variant == 9) g.data[0].amount = UINT32_MAX;
        if (variant == 10) w_proof.view.sectors_per_cluster = 0;
        int result = reist_fat32_grow_finish(&g, variant != 11, &outcome, &size, &durable);
        if (variant == 11) W_CHECK(!result && outcome == REIST_FILE_OBJECT_NO_EFFECT);
        else W_CHECK(result < 0);
        W_CHECK(!durable && !w_effects && !w_proof.ready);
        if (variant == 4) { --w_tx.admission.request; (void)reist_fat32_transaction_finish(&w_tx, false, &outcome); }
        if (variant == 5) w_payload[0] ^= 1;
        if (variant == 6) w_entry[28] ^= 1;
        W_CHECK(w_grow_matches(w_get(w_entry+28), false));
    }
    for (unsigned variant = 0; variant < 8; ++variant) {
        w_reset(false); reist_fat32_grow_t g = {0}; uint32_t outcome, size, durable;
        if (variant == 2) w_proof.whole_volume = 0;
        if (variant == 3) w_proof.free_hint = UINT32_MAX;
        if (variant == 4) w_proof.chain_count = 0;
        if (variant == 5) w_now = 5001;
        int result = variant < 2 ? reist_fat32_grow_begin(&g, &w_proof, &w_tx,
            variant == 0 ? UINT64_MAX : 0) : reist_fat32_append_begin(&g, &w_proof, &w_tx,
            variant == 6 ? NULL : w_payload, variant == 7 ? sizeof(w_payload)+1 : 1000);
        W_CHECK(result < 0 && !w_effects && !w_proof.ready);
        if (g.owner.active) (void)reist_fat32_grow_finish(&g, false, &outcome, &size, &durable);
        else (void)reist_fat32_transaction_finish(&w_tx, false, &outcome);
        W_CHECK(!w_effects && w_grow_matches(w_get(w_entry+28), false));
    }
}
static void w_grow_retention(void) {
    w_grow_fixture(0);
    reist_fat32_grow_t g = {0}; uint32_t outcome, size, durable, total = 0;
    for (unsigned step = 0; step < 4; ++step) {
        if (step) {
            W_CHECK(!file_object_guard_snapshot(&w_guard, &w_admission.base.epoch, w_now));
            ++w_admission.request;
            W_CHECK(!reist_fat32_transaction_begin_owned(&w_tx, &w_tx_io, &w_admission,
                W_FIRST, w_sectors, (uint16_t)w_reserved));
            w_effects = w_flushes = 0;
        }
        unsigned before = w_reads;
        W_CHECK(w_grow_prepare(&g, true, 70000-total, total) == 1 && w_reads-before < 80);
        W_CHECK(!reist_fat32_grow_finish(&g, true, &outcome, &size, &durable) && w_proof.ready);
        total += durable;
        W_CHECK(w_grow_matches(size, true));
    }
    for (unsigned mode = 1; mode <= 3; ++mode) {
        w_reset(false); memset(&g, 0, sizeof(g)); w_grow_prepare(&g, true, 70000, 0); w_snapshot_mode = mode;
        W_CHECK(!reist_fat32_grow_finish(&g, true, &outcome, &size, &durable));
        W_CHECK(outcome == REIST_FILE_OBJECT_DURABLE_COMMIT && durable && !w_proof.ready);
        W_CHECK(w_grow_matches(size, true));
    }
}
static void w_grow_edges(void) {
    uint32_t outcome, size, durable;
    for (unsigned partial = 0; partial <= 1; ++partial) {
        w_length = W_CLUSTERS-1; w_stride = 1; w_geometry(0);
        uint32_t old_size = w_length*512-(partial ? 3 : 0);
        w_entry[20] = w_entry[21] = w_entry[27] = 0; w_entry[26] = 3;
        w_put(w_entry+28, old_size); w_reset(true);
        reist_fat32_grow_t g = {0};
        W_CHECK(!reist_fat32_grow_begin(&g, &w_proof, &w_tx, (uint64_t)old_size+10));
        int result; unsigned steps = 0;
        do {
            unsigned before = w_reads;
            result = reist_fat32_grow_step(&g);
            W_CHECK(w_reads-before <= 300 && ++steps < 1000 && !w_effects);
        } while (result == 1);
        W_CHECK(steps > 500 && g.scanned == W_CLUSTERS); /* no fake ENOSPC at a workspace limit */
        if (partial) {
            W_CHECK(!result && !reist_fat32_grow_finish(&g, true, &outcome, &size, &durable));
            W_CHECK(outcome == REIST_FILE_OBJECT_DURABLE_COMMIT && durable == 3 && size == old_size+3);
            W_CHECK(w_grow_matches(size, false));
        } else {
            W_CHECK(result == -REIST_ENOSPC);
            W_CHECK(reist_fat32_grow_finish(&g, true, &outcome, &size, &durable) == -REIST_ENOSPC);
            W_CHECK(!w_effects && !durable && outcome == REIST_FILE_OBJECT_NO_EFFECT && w_grow_matches(old_size, false));
        }
    }
    /* A high-cluster empty-file start wraps once, without trusting FSInfo's hint. */
    w_length = 0; w_stride = 5; w_geometry(0); w_entry[26] = 0; w_reset(true);
    w_proof.free_hint = W_CLUSTERS+1;
    reist_fat32_grow_t g = {0}; w_grow_prepare(&g, true, 700, 0);
    W_CHECK(g.allocated_count == 2 && g.allocated[0] == W_CLUSTERS+1 && g.allocated[1] == 3);
    W_CHECK(!reist_fat32_grow_finish(&g, true, &outcome, &size, &durable));
    W_CHECK(size == 700 && durable == 700 && w_proof.view.object.locator_c == W_CLUSTERS+1);
    uint32_t kind;
    W_CHECK(!reist_fat32_ownership_query(&w_proof, w_proof.epoch, W_CLUSTERS+1, &kind));
    W_CHECK(kind == REIST_FAT32_CLUSTER_FILE);
    uint8_t bytes[512];
    W_CHECK(!w_read(NULL, 0, w_data+(W_CLUSTERS-1), bytes) && !memcmp(bytes, w_payload, 512));
    W_CHECK(!w_read(NULL, 0, w_data+1, bytes) && !memcmp(bytes, w_payload+512, 188));
    static reist_fat32_ownership_t verified;
    W_CHECK(!reist_fat32_volume_begin(&verified, &w_io, &w_proof.view.object, w_proof.epoch));
    int result;
    do { result = reist_fat32_ownership_step(&verified, &w_io, w_proof.epoch); } while (result == 1);
    W_CHECK(!result && verified.chain_count == 2);
    /* Shrink then zero-grow must not reveal the formerly visible bytes. */
    w_length = 3; w_stride = 5; w_geometry(0); w_entry[26] = 3; w_reset(true);
    reist_fat32_shrink_t s = {0}; uint32_t released;
    w_shrink_prepare(&s, 100);
    W_CHECK(!reist_fat32_shrink_finish(&s, true, &outcome, &size, &released) && size == 100 && released == 2);
    W_CHECK(!file_object_guard_snapshot(&w_guard, &w_admission.base.epoch, w_now));
    ++w_admission.request;
    W_CHECK(!reist_fat32_transaction_begin_owned(&w_tx, &w_tx_io, &w_admission, W_FIRST, w_sectors, (uint16_t)w_reserved));
    w_effects = w_flushes = 0; memset(&g, 0, sizeof(g));
    w_grow_prepare(&g, false, 1436, 0);
    W_CHECK(!reist_fat32_grow_finish(&g, true, &outcome, &size, &durable) && size == 1536 && durable == 1436);
    for (unsigned rank = 0; rank < 3; ++rank) {
        uint32_t lba = w_data+1+rank;
        W_CHECK(!w_read(NULL, 0, lba, bytes));
        for (unsigned i = rank ? 0 : 100; i < 512; ++i) W_CHECK(!bytes[i]);
        if (!rank) {
            uint8_t original[512]; w_original(lba, original); W_CHECK(!memcmp(bytes, original, 100));
        }
    }
    W_CHECK(!reist_fat32_volume_begin(&verified, &w_io, &w_proof.view.object, w_proof.epoch));
    do { result = reist_fat32_ownership_step(&verified, &w_io, w_proof.epoch); } while (result == 1);
    W_CHECK(!result && verified.chain_count == 3);
    /* Oracle counterexamples: absent initialized data and corruption outside it. */
    w_grow_fixture(0); memset(&g, 0, sizeof(g)); w_grow_prepare(&g, true, 70000, 0);
    W_CHECK(!reist_fat32_grow_finish(&g, true, &outcome, &size, &durable) && w_grow_matches(size, true));
    bool removed = false;
    for (unsigned i = 0; i < 128; ++i) if (w_disk[i].used && w_disk[i].sector == w_data+2) {
        w_disk[i].used = 0; removed = true;
        W_CHECK(!w_grow_matches(size, true) && !w_grow_matches(w_get(w_entry+28), false));
        w_disk[i].used = 1;
    }
    W_CHECK(removed);
    w_original(w_data+1, bytes); bytes[7] ^= 1; w_write(w_data+1, bytes);
    W_CHECK(!w_grow_matches(size, true) && !w_grow_matches(w_get(w_entry+28), false));
    for (unsigned hints = 0; hints < 3; ++hints) {
        w_grow_fixture(0);
        w_bad_fsinfo = hints;
        if (!hints) w_boot[48] = w_boot[49] = 0xff;
        w_reset(true); memset(&g, 0, sizeof(g)); w_grow_prepare(&g, true, 70000, 0);
        W_CHECK(g.fsinfo_count == (hints == 1 ? 1U : 0U));
        W_CHECK(!reist_fat32_grow_finish(&g, true, &outcome, &size, &durable) && w_grow_matches(size, true));
        w_bad_fsinfo = 0; w_boot[48] = 1; w_boot[49] = 0;
    }
}
#endif
static void w_grow_tests(void) {
#ifndef REIST_FAT32_GROW_VERSION
    W_CHECK(0 && "Missing owned zero-growth/append planner");
#else
    for (unsigned variant = 0; variant < 10; ++variant) {
        w_length = variant == 2 || variant == 3 ? 0 : variant == 4 || variant == 8 ? 3 : W_LENGTH;
        w_stride = 5;
        w_geometry(variant == 3 ? 2 : variant == 5 ? 3 : variant == 6 ? 4 : variant == 7 ? 5 : 0);
        w_entry[20] = w_entry[21] = w_entry[27] = 0; w_entry[26] = w_length ? 3 : 0;
        uint32_t old_size = w_length*w_spc*512;
        if (variant == 1) old_size -= 3;
        if (variant == 4) old_size = 1;
        w_put(w_entry+28, old_size); w_reset(true);
        reist_fat32_grow_t g = {0};
        bool append = variant == 1 || variant == 2 || variant == 5 || variant == 6 || variant == 7;
        uint64_t target = variant == 4 ? 600 : variant == 8 ? old_size :
            variant == 9 ? UINT32_MAX : old_size+70000ULL;
        int result = append ? reist_fat32_append_begin(&g, &w_proof, &w_tx, w_payload, sizeof(w_payload)) :
            reist_fat32_grow_begin(&g, &w_proof, &w_tx, target);
        W_CHECK(!result);
        unsigned steps = 0;
        do {
            unsigned before = w_reads;
            result = reist_fat32_grow_step(&g);
            W_CHECK(w_reads-before <= 300 && ++steps < 1000 && !w_effects);
        } while (result == 1);
        W_CHECK(!result && w_tx.journal.entry_count <= 20);
        uint32_t outcome, size, durable;
        W_CHECK(!reist_fat32_grow_finish(&g, true, &outcome, &size, &durable));
        if (variant == 8) W_CHECK(outcome == REIST_FILE_OBJECT_NO_EFFECT && !w_effects && !durable && size == old_size);
        else {
            W_CHECK(outcome == REIST_FILE_OBJECT_DURABLE_COMMIT && size > old_size && size-old_size == durable);
            W_CHECK(w_flushes == 4 && w_proof.ready && w_proof.view.file_size == size);
            if (variant == 3) W_CHECK(durable < 65536 && w_proof.chain_count == 1);
            if (variant == 4) W_CHECK(size == 600 && w_proof.chain_count == w_length);
            static reist_fat32_ownership_t verified;
            W_CHECK(!reist_fat32_volume_begin(&verified, &w_io, &w_proof.view.object, w_proof.epoch));
            do { result = reist_fat32_ownership_step(&verified, &w_io, w_proof.epoch); } while (result == 1);
            W_CHECK(!result && verified.chain_count == w_proof.chain_count);
            W_CHECK(w_grow_matches(size, append));
        }
    }
    w_grow_cuts(); w_grow_negatives(); w_grow_retention(); w_grow_edges();
#endif
}
static void w_sync_tests(void) {
#ifndef REIST_FAT32_SYNC_VERSION
    W_CHECK(0 && "Missing explicit owned file synchronization");
#else
    w_grow_fixture(0);
    for (unsigned variant = 0; variant < 7; ++variant) {
        w_reset(false); reist_fat32_overwrite_t sync = {0}; uint32_t outcome;
        w_proof.seek_cluster = w_cluster(399); w_proof.seek_rank = 399;
        W_CHECK(!reist_fat32_sync_begin(&sync, &w_proof, &w_tx) && !w_effects);
        if (variant == 1) w_now = 5001;
        if (variant == 2) w_cut = 1;
        if (variant == 3) w_read_cut = w_reads+1;
        if (variant == 4) W_CHECK(!reist_fat32_transaction_stage(&w_tx, W_FIRST+w_data+1, w_payload));
        if (variant == 5) ++w_tx.admission.request;
        int result = reist_fat32_sync_finish(&sync, variant != 6, &outcome);
        if (!variant) {
            W_CHECK(!result && outcome == REIST_FILE_OBJECT_DURABLE_COMMIT && w_flushes == 1 && w_effects == 1);
            W_CHECK(w_proof.ready && w_proof.epoch == w_admission.base.epoch+2);
            W_CHECK(w_proof.seek_cluster == w_cluster(399) && w_proof.seek_rank == 399);
        } else if (variant == 6) W_CHECK(!result && !w_effects && outcome == REIST_FILE_OBJECT_NO_EFFECT);
        else {
            W_CHECK(result < 0 && !w_proof.ready);
            W_CHECK(w_effects == (variant == 2 ? 1U : 0U));
            if (variant == 2) W_CHECK(outcome == REIST_FILE_OBJECT_UNKNOWN && file_object_guard_can_open(&w_guard, 0, w_now) == -REIST_EIO);
        }
        if (variant == 5) { --w_tx.admission.request; (void)reist_fat32_transaction_finish(&w_tx, false, &outcome); }
        w_read_cut = 0;
        W_CHECK(w_grow_matches(w_get(w_entry+28), false));
        unsigned before = w_effects;
        W_CHECK(reist_fat32_sync_finish(&sync, true, &outcome) == -REIST_ESTALE && w_effects == before);
    }
#endif
}
#ifdef R342_SERVICE_TEST
#include "userspace/storage/include/reist/vfs_file_client.h"
static reist_vfs_write_frame_t ws_reply;
static int ws_completion_error, ws_completed, ws_input_error, ws_cancelled, ws_end_error;
static uint32_t ws_input_length;
static unsigned ws_repair_enabled, ws_repair_committed, ws_repair_aborted;
/* Client and real Storage/planners share only a modeled SDK transport here.
 * Kernel pool cancellation/recovery and guest scheduling remain separate gates. */
static int ws_client_transport, ws_submitted, ws_started, ws_input_ready;
static uint32_t ws_client_calls, ws_fail_at, ws_fail_kind, ws_acknowledged;
static uint64_t ws_client_deadline;
static uint8_t ws_input[128U*1024U];
static union {
    reist_vfs_write_frame_t write;
    x86os_vfs_shadow_object_frame_t control;
} ws_frame;
static x86os_storage_descriptor_v3_t ws_pending;
static uintptr_t ws_client_bulk(x86os_storage_bulk_control_t *, uintptr_t, uintptr_t);
static uint32_t format_crc32(const uint8_t *bytes, uint32_t count) {
    uint32_t crc = 0xffffffffU;
    for (uint32_t i = 0; i < count; ++i) {
        crc ^= bytes[i];
        for (unsigned b = 0; b < 8; ++b) crc = (crc>>1) ^ (0xedb88320U & (uint32_t)-(int32_t)(crc&1));
    }
    return crc^0xffffffffU;
}
#include "write_service.inc"
uintptr_t x86os_syscall(uint32_t number, uintptr_t a, uintptr_t b, uintptr_t c) {
    if (number == X86OS_SYS_FILE_OBJECT_GUARD) {
        if (c == REIST_FILE_REPAIR_VERSION) {
            reist_file_repair_request_t* q = (void*)a;
            W_CHECK(q->version == 3 && q->struct_size == sizeof(*q) && !b);
            if (q->operation == REIST_FILE_REPAIR_QUERY) {
                if (q->resource || !ws_repair_enabled || ws_repair_committed) return (uintptr_t)-2;
                q->generation = 8; q->fingerprint = 0x1234; q->first_sector = 0;
                q->sector_count = w_sectors; q->reserved_sectors = w_reserved; q->backup_sector = 6;
                return 0;
            }
            W_CHECK(!q->resource && q->generation == 8 && q->fingerprint == 0x1234 && !q->first_sector);
            if (q->operation == REIST_FILE_REPAIR_BEGIN) {
                uint64_t epoch;
                W_CHECK(!file_object_guard_snapshot(&w_guard, &epoch, w_now));
                return file_object_guard_repair_begin(&w_guard, 0, w_server, epoch, w_now, q->deadline_ms, &q->token);
            }
            if (q->operation == REIST_FILE_REPAIR_COMMIT) {
                W_CHECK(vfs_write_proof.recovery_only && vfs_write_proof.ready && vfs_write_proof.verified_until == W_CLUSTERS+2);
                int result = file_object_guard_repair_finish(&w_guard, q->token, w_server, true, w_now);
                if (!result) ++ws_repair_committed;
                return result;
            }
            W_CHECK(q->operation == REIST_FILE_REPAIR_ABORT);
            ++ws_repair_aborted;
            return file_object_guard_repair_finish(&w_guard, q->token, w_server, false, w_now);
        }
        if (c == REIST_FILE_OBJECT_OWNED_VERSION) {
            reist_file_object_owned_request_t *r = (void *)a;
            W_CHECK(file_object_guard_owned_valid(r));
            W_CHECK(r->request == vfs_write_job.request.handle && r->base.deadline_ms == vfs_write_job.deadline);
            if (ws_cancelled) return (uintptr_t)-125;
            return file_object_guard_begin_owned(&w_guard, &r->base.keys[0], r->pin, r->request, w_server,
                (file_object_owner_t){r->base.client_pid, r->base.client_generation}, r->base.epoch,
                w_now, r->base.deadline_ms, &r->base.token);
        }
        reist_file_object_guard_request_t *r = (void *)a;
        W_CHECK(!b && !c && file_object_guard_request_valid(r));
        file_object_owner_t client = {r->client_pid, r->client_generation};
        if (r->operation == REIST_FILE_OBJECT_PIN)
            return file_object_guard_pin(&w_guard, &r->keys[0], w_server, client, r->epoch, w_now, &r->token);
        if (r->operation == REIST_FILE_OBJECT_RELEASE)
            return file_object_guard_release(&w_guard, r->token, w_server, client);
        if (r->operation == REIST_FILE_OBJECT_MUTATION_END && ws_end_error) {
            ws_end_error = 0; return (uintptr_t)-5;
        }
        return w_guard_call(NULL, r);
    }
    if (number == X86OS_SYS_STORAGE_JOURNAL_IO) {
        reist_storage_journal_request_t r = *(const reist_storage_journal_request_t *)a;
        if (vfs_repair_active) {
            uint32_t fences;
            W_CHECK(!file_object_guard_fenced(&w_guard, &fences) && (fences & 1));
            if (r.operation == REIST_STORAGE_JOURNAL_FLUSH) {
                int marked = file_object_guard_journal_io(&w_guard, w_server, r.token, 0, FILE_OBJECT_JOURNAL_WRITE, w_now, NULL);
                if (marked) return marked;
            }
        }
        if (ws_cancelled) return (uintptr_t)-125;
        /* Test drive has a nonzero physical displacement; production host must
         * submit volume-relative sectors. The mediated device applies it once. */
        W_CHECK(!c && (r.operation == REIST_STORAGE_JOURNAL_FLUSH || r.sector < w_sectors));
        if (r.operation != REIST_STORAGE_JOURNAL_FLUSH) r.sector += W_FIRST;
        return w_transfer(NULL, &r, (void *)b);
    }
    W_CHECK(number == X86OS_SYS_STORAGE_BULK);
    x86os_storage_bulk_control_t *control = (void *)a;
    if (ws_client_transport && control->operation != X86OS_STORAGE_BULK_INPUT_TAKE)
        return ws_client_bulk(control, b, c);
    W_CHECK(b == 0U);
    W_CHECK(control->version == 2U && control->operation == X86OS_STORAGE_BULK_INPUT_TAKE);
    W_CHECK(control->handle == vfs_write_job.request.handle && control->length == 128U*1024U);
    if (ws_input_error) return (uintptr_t)ws_input_error;
    W_CHECK(!ws_client_transport || ws_input_ready);
    memcpy((void *)c, ws_client_transport ? ws_input : w_payload, ws_input_length);
    control->transferred = ws_input_length;
    return 0;
}
int x86os_storage_block_read(uint32_t resource, uint32_t sector, void *data) { return w_read(NULL, resource, sector, data); }
int x86os_drive_info(uint32_t resource, x86os_drive_info_t *info) { return w_info(NULL, resource, info); }
void x86os_puts(const char* text) { (void)text; }
void x86os_print_number(int value) { (void)value; }
int x86os_monotonic_ms(uint64_t *now) { *now = w_now; return 0; }
int x86os_process_identity_of(int pid, x86os_process_identity_t *identity) {
    *identity = (x86os_process_identity_t){1U, sizeof(*identity), pid, w_client.generation}; return 0;
}
int x86os_storage_complete(x86os_storage_handle_t handle, int32_t result, const void *data) {
    W_CHECK(handle && result <= 0);
    ++ws_completed;
    if (!result) { W_CHECK(data); memcpy(&ws_reply, data, sizeof(ws_reply)); }
    else { memset(&ws_reply, 0, sizeof(ws_reply)); ws_reply.reply.result = result; }
    return ws_completion_error;
}
static x86os_storage_descriptor_v3_t ws_descriptor(uint32_t length) {
    static uint32_t next = 513;
    return (x86os_storage_descriptor_v3_t){3U, sizeof(x86os_storage_descriptor_v3_t), next++, 35U, 0U,
        length, 512U, w_client.pid, w_client.generation, w_server.generation, 5000U};
}
static void ws_drain(void) {
    unsigned steps = 0;
    while (vfs_write_job.active) {
        unsigned before = w_reads;
        vfs_object_reap_one();
        int status = vfs_write_poll();
        W_CHECK(status == ws_completion_error && ++steps < 3000 && w_reads-before <= 400);
    }
}
int reist_vfs_resolve_path(const char *path, char *output, uint32_t *length) {
    if (!path || strcmp(path, "/TARGET.BIN") || !output || !length) return -22;
    memcpy(output, path, 12); *length = 11; return 0;
}
int x86os_storage_submit(const x86os_storage_submit_t *request, const void *data,
    x86os_storage_handle_t *handle) {
    W_CHECK(ws_client_transport && !ws_submitted && request->length == 512U);
    W_CHECK(request->operation == X86OS_STORAGE_VFS_OBJECT_MUTATE ||
            request->operation == X86OS_STORAGE_VFS_SHADOW_STAT);
    ws_pending = ws_descriptor(request->offset);
    ws_pending.operation = request->operation;
    ws_pending.deadline_ms = w_now+request->timeout_ms;
    W_CHECK(ws_pending.deadline_ms <= ws_client_deadline);
    memcpy(&ws_frame, data, sizeof(ws_frame));
    *handle = ws_pending.handle;
    ws_submitted = 1; ws_started = ws_completed = ws_input_ready = 0;
    if (request->operation == X86OS_STORAGE_VFS_OBJECT_MUTATE && ++ws_client_calls == ws_fail_at && ws_fail_kind == 1U)
        w_cut = w_effects+1U;
    return 0;
}
static uintptr_t ws_client_bulk(x86os_storage_bulk_control_t *control, uintptr_t b, uintptr_t c) {
    W_CHECK(ws_submitted && control->handle == ws_pending.handle);
    if (control->operation == X86OS_STORAGE_BULK_INPUT_PUBLISH) {
        W_CHECK(!b && c && control->length == ws_pending.offset && control->length <= sizeof(ws_input));
        memcpy(ws_input, (const void *)c, control->length);
        ws_input_length = control->length; ws_input_ready = 1; return 0;
    }
    if (control->operation == X86OS_STORAGE_BULK_RECEIPT_ACK) {
        W_CHECK(!b && !c && ws_completed == 1);
        if (ws_client_calls == ws_fail_at && ws_fail_kind == 2U) return (uintptr_t)-110;
        ++ws_acknowledged; ws_submitted = 0; return 0;
    }
    W_CHECK(control->operation == X86OS_STORAGE_BULK_RECEIPT_COLLECT && b && !c);
    if (!ws_started) {
        ws_started = 1;
        W_CHECK(!vfs_write_start(&ws_frame.write, &ws_pending));
    }
    if (vfs_write_job.active) {
        unsigned before = w_reads;
        vfs_object_reap_one();
        W_CHECK(!vfs_write_poll() && w_reads-before <= 400U);
    }
    if (!ws_completed) return (uintptr_t)-11;
    W_CHECK(ws_completed == 1);
    control->result = 0;
    memcpy((void *)b, &ws_reply, sizeof(ws_reply)); return 0;
}
int x86os_storage_collect(x86os_storage_handle_t handle, int32_t *result, void *data) {
    /* Only legacy CLOSE is needed by this write integration test. Resolve and
     * release the actual owner-bound service slot; do not emulate write replies. */
    W_CHECK(ws_client_transport && ws_submitted && handle == ws_pending.handle && result && data);
    x86os_vfs_shadow_object_frame_t *frame = data;
    memcpy(frame, &ws_frame.control, sizeof(*frame));
    W_CHECK(frame->operation == X86OS_VFS_SHADOW_OBJECT_CLOSE);
    vfs_object_slot_t *slot = NULL;
    frame->result = vfs_object_resolve_local(frame->object_token, frame->service_generation,
        w_client.pid, w_client.generation, w_server.generation, &slot);
    if (!frame->result) frame->result = vfs_object_release(slot);
    *result = 0; ws_submitted = 0; return 0;
}
int x86os_storage_cancel(x86os_storage_handle_t handle) {
    W_CHECK(ws_client_transport && ws_submitted && handle == ws_pending.handle);
    ws_cancelled = 1; ws_drain(); ws_submitted = 0; return 0;
}
int x86os_storage_bulk_collect(x86os_storage_handle_t handle, int32_t *result,
    void *frame, void *data, uint32_t capacity, uint32_t *transferred) {
    (void)handle; (void)result; (void)frame; (void)data; (void)capacity; (void)transferred;
    W_CHECK(0); return -95; /* this proof never reads through a mocked Client */
}
int x86os_sleep_ms(uint32_t duration) { W_CHECK(duration == 1U); w_now += duration; return 0; }
int x86os_yield(void) { ++w_now; return 0; }
static reist_vfs_write_frame_t ws_operation(uint32_t op, uint64_t offset, uint64_t target, uint32_t length) {
    reist_vfs_write_frame_t frame = {0};
    frame.version = REIST_VFS_WRITE_VERSION; frame.struct_size = sizeof(frame); frame.operation = op;
    frame.object_token = vfs_object_token(0, vfs_objects[0].generation);
    frame.service_generation = w_server.generation; frame.rights = vfs_objects[0].rights;
    frame.offset = offset; frame.target_size = target; frame.length = length;
    frame.data_crc32 = format_crc32(w_payload, length); ws_input_length = length;
    return frame;
}
static void ws_open(void) {
    w_length = 400; w_stride = 5; w_geometry(0);
    w_entry[20] = w_entry[21] = w_entry[27] = 0; w_entry[26] = 3;
    w_reset(true);
    uint32_t outcome;
    W_CHECK(!reist_fat32_transaction_finish(&w_tx, false, &outcome));
    W_CHECK(!file_object_guard_release(&w_guard, w_admission.pin, w_server, w_client));
    memset(vfs_objects, 0, sizeof(vfs_objects)); memset(&vfs_write_job, 0, sizeof(vfs_write_job));
    vfs_write_cache_pin = 0; ws_completion_error = ws_completed = ws_input_error = ws_cancelled = ws_end_error = 0;
    reist_vfs_write_frame_t frame = {0};
    frame.version = REIST_VFS_WRITE_VERSION; frame.struct_size = sizeof(frame); frame.operation = REIST_VFS_WRITE_OPEN;
    frame.rights = REIST_VFS_WRITE_RIGHT_MASK; frame.path_length = 11;
    memcpy(frame.path, "/TARGET.BIN", 12);
    x86os_storage_descriptor_v3_t d = ws_descriptor(0);
    W_CHECK(!vfs_write_start(&frame, &d) && vfs_write_job.active);
    W_CHECK(!vfs_objects[0].rights && vfs_objects[0].pending); /* no premature grants */
    ws_drain();
    W_CHECK(ws_completed == 1 && !ws_reply.reply.result && ws_reply.object_token);
    W_CHECK(ws_reply.rights == 255 && vfs_objects[0].rights == 255 && !vfs_objects[0].pending);
    W_CHECK(!w_effects && vfs_write_proof.ready && vfs_write_cache_pin == vfs_objects[0].kernel_pin);
}
static void ws_run(uint32_t op, uint64_t offset, uint64_t target, uint32_t length) {
    reist_vfs_write_frame_t f = ws_operation(op, offset, target, length);
    x86os_storage_descriptor_v3_t d = ws_descriptor(length);
    W_CHECK(!vfs_write_start(&f, &d)); ws_drain();
}
static void ws_recovery_tests(void) {
    /* Actual extracted host + guard + RSTJ + whole-volume walker. Kernel
     * retained extent/lifecycle/pool are exercised by their separate seam. */
    w_length = W_LENGTH; w_stride = 5; w_geometry(0);
    w_entry[20] = w_entry[21] = w_entry[27] = 0; w_entry[26] = 3;
    w_reset(true);
    for (unsigned variant = 0; variant < 34; ++variant) {
        w_length = W_LENGTH; w_geometry(variant == 6 ? 5 : 0); w_reset(false);
        memset(&vfs_write_job, 0, sizeof(vfs_write_job)); memset(&vfs_repair_job, 0, sizeof(vfs_repair_job));
        ws_repair_enabled = 1; ws_repair_committed = ws_repair_aborted = 0;
        vfs_repair_active = vfs_write_cache_pin = 0; ws_cancelled = 0;
        W_CHECK(!file_object_guard_cleanup(&w_guard, w_server));
        W_CHECK(!file_object_guard_merge_fences(&w_guard, 3));
        if (variant != 1 && variant != 6) {
            ata_journal_record_t active; ata_undo_journal_make_clean(&active, 8);
            active.state = ATA_JOURNAL_ACTIVE; active.entry_count = 20;
            for (unsigned i = 0; i < 20; ++i) {
                uint8_t bytes[512]; uint32_t lba = w_lba(i*512);
                w_original(lba, bytes); w_write(9+i, bytes);
                active.entries[i].target_lba = lba;
                active.entries[i].data_crc32 = format_crc32(bytes, 512);
                memset(bytes, 0xa5, sizeof(bytes)); w_write(lba, bytes);
            }
            if (variant == 2) active.entries[19].data_crc32 ^= 1;
            active.header_crc32 = 0; active.header_crc32 = format_crc32((const uint8_t*)&active, 512);
            w_write(8, (const uint8_t*)&active); w_write(31, (const uint8_t*)&active);
        }
        memcpy(w_stable, w_disk, sizeof(w_disk));
        if (variant >= 8) w_cut = variant-7; /* all20 restore +4 barriers +2 headers cuts */
        int result = vfs_repair_poll();
        W_CHECK(!result && vfs_repair_active);
        unsigned steps = 0;
        do {
            if (variant == 3 && steps == 1) w_now = vfs_repair_job.request.deadline_ms;
            if (variant == 4 && steps == 1) w_now = 0;
            if (variant == 5 && steps == 1) w_read_cut = w_reads+1;
            if (variant == 7 && steps == 1) {
                uint8_t bytes[512]; W_CHECK(!w_read(NULL, 0, w_reserved, bytes));
                w_put(bytes+4*4, 0xfffffff); w_write(w_reserved, bytes);
                W_CHECK(!w_read(NULL, 0, w_reserved+W_FAT, bytes));
                w_put(bytes+4*4, 0xfffffff); w_write(w_reserved+W_FAT, bytes); /* orphan */
            }
            result = vfs_repair_poll();
            W_CHECK(++steps < 1000);
        } while (!result && vfs_repair_active);
        uint32_t fences;
        W_CHECK(!file_object_guard_fenced(&w_guard, &fences) && (fences & 2));
        if (variant == 0 || variant == 1 || variant == 6) {
            W_CHECK(!result && ws_repair_committed == 1 && !ws_repair_aborted && !(fences & 1));
            W_CHECK(!vfs_write_proof.ready && !vfs_write_cache_pin);
            W_CHECK(w_flushes == (variant == 0 ? 4U : 1U)); /* independent of20 restored targets */
            if (!variant) for (unsigned i = 0; i < 20; ++i) {
                uint8_t expected[512], actual[512]; w_original(w_lba(i*512), expected);
                W_CHECK(!w_read(NULL, 0, w_lba(i*512), actual) && !memcmp(actual, expected, 512));
            }
            for (unsigned i = 0; !vfs_repair_job.scanned && i < 44; ++i) W_CHECK(!vfs_repair_poll());
            W_CHECK(vfs_repair_job.scanned);
        } else {
            W_CHECK(result < 0 && !ws_repair_committed && ws_repair_aborted == 1 && (fences & 1));
            if (variant == 2) W_CHECK(!w_effects); /* corrupt final before-image: zero writes */
        }
    }
    ws_repair_enabled = 0;
    printf("R342 repair-service checks: %u\n", w_checks);
}

static void ws_tests(void) {
    W_CHECK(sizeof(vfs_write_job) < 256U*1024U && sizeof(vfs_write_proof) < 48U*1024U);
    ws_open(); unsigned before = w_reads;
    ws_run(REIST_VFS_WRITE_DATA, 3, 0, 2000);
    W_CHECK(!ws_reply.reply.result && ws_reply.reply.durable_bytes == 2000 && w_flushes == 4);
    W_CHECK(w_reads-before < 160 && w_media_matches(3, 2000));
    ws_open(); ws_run(REIST_VFS_WRITE_APPEND, 0, 0, 70000);
    W_CHECK(!ws_reply.reply.result && ws_reply.reply.outcome == REIST_FILE_OBJECT_DURABLE_COMMIT);
    W_CHECK(ws_reply.reply.durable_bytes && w_grow_matches((uint32_t)ws_reply.reply.resulting_size, true));
    before = w_reads; ws_run(REIST_VFS_WRITE_APPEND, 0, 0, 1);
    W_CHECK(!ws_reply.reply.result && ws_reply.reply.durable_bytes == 1 && w_reads-before < 160);
    ws_open(); ws_run(REIST_VFS_WRITE_RESIZE, 0, 700000, 0);
    W_CHECK(!ws_reply.reply.result && !ws_reply.reply.durable_bytes);
    W_CHECK(w_grow_matches((uint32_t)ws_reply.reply.resulting_size, false));
    ws_open(); ws_run(REIST_VFS_WRITE_RESIZE, 0, 0, 0);
    W_CHECK(!ws_reply.reply.result && ws_reply.reply.released_clusters > 0);
    W_CHECK(ws_reply.reply.resulting_size < ws_reply.reply.previous_size);
    ws_open(); ws_run(REIST_VFS_WRITE_SYNC, 0, 0, 0);
    W_CHECK(!ws_reply.reply.result && ws_reply.reply.outcome == REIST_FILE_OBJECT_DURABLE_COMMIT && w_flushes == 1);
    ws_open(); ws_run(REIST_VFS_WRITE_RESIZE, 0, w_get(w_entry+28), 0);
    W_CHECK(!ws_reply.reply.result && (ws_reply.reply.flags & REIST_VFS_WRITE_DONE) && !w_effects);
    ws_open();
    reist_vfs_write_frame_t f = ws_operation(REIST_VFS_WRITE_DATA, 0, 0, 20);
    x86os_storage_descriptor_v3_t d = ws_descriptor(20);
    W_CHECK(!vfs_write_start(&f, &d));
    w_read_cut = w_reads+1; ws_end_error = 1;
    ws_drain();
    W_CHECK(ws_reply.reply.result < 0 && ws_reply.reply.outcome == REIST_FILE_OBJECT_UNKNOWN);
    ws_open();
    f = ws_operation(REIST_VFS_WRITE_DELEGATE, 0, 0, 0);
    f.target_pid = 42; f.target_generation = w_client.generation; f.rights = REIST_VFS_WRITE_RIGHT_APPEND;
    d = ws_descriptor(0);
    W_CHECK(!vfs_write_start(&f, &d)); ws_drain();
    W_CHECK(!ws_reply.reply.result && vfs_objects[1].pending && vfs_objects[1].rights == REIST_VFS_WRITE_RIGHT_APPEND);
    memset(&f, 0, sizeof(f)); f.version = 2; f.struct_size = 512; f.operation = REIST_VFS_WRITE_ADOPT;
    d = ws_descriptor(0); d.client_pid = 42;
    W_CHECK(!vfs_write_start(&f, &d)); ws_drain();
    W_CHECK(!ws_reply.reply.result && !vfs_objects[1].pending && ws_reply.rights == REIST_VFS_WRITE_RIGHT_APPEND);
    W_CHECK(!w_effects && vfs_objects[0].in_use);
    ws_open();
    w_now = 5001; /* delivered but never used: no permanent leaked lifetime pin */
    for (unsigned i = 0; i < 16; ++i) vfs_object_reap_one();
    W_CHECK(!vfs_objects[0].in_use && !w_effects);
    ws_open();
    f = ws_operation(REIST_VFS_WRITE_DATA, 0, 0, 20); d = ws_descriptor(20);
    f.data_crc32 ^= 1U;
    W_CHECK(!vfs_write_start(&f, &d)); ws_drain();
    W_CHECK(ws_reply.reply.result == -84 && !w_effects);
    ws_open();
    f = ws_operation(REIST_VFS_WRITE_DATA, 0, 0, 20); d = ws_descriptor(20);
    W_CHECK(!vfs_write_start(&f, &d));
    reist_vfs_write_frame_t busy = ws_operation(REIST_VFS_WRITE_DATA, 0, 0, 20);
    x86os_storage_descriptor_v3_t other = ws_descriptor(20);
    W_CHECK(!vfs_write_start(&busy, &other) && ws_reply.reply.result == -16);
    W_CHECK(vfs_write_job.request.handle == d.handle); ws_drain();
    W_CHECK(!ws_reply.reply.result && ws_reply.reply.durable_bytes == 20);
    ws_open();
    f = ws_operation(REIST_VFS_WRITE_DATA, 0, 0, 20); d = ws_descriptor(20);
    W_CHECK(!vfs_write_start(&f, &d));
    W_CHECK(!vfs_write_poll() && vfs_write_job.transaction.active && !w_effects);
    w_now = 5000; ws_drain();
    W_CHECK(ws_reply.reply.result < 0 && !w_effects && !vfs_write_cache_pin);
    for (unsigned mode = 0; mode < 5; ++mode) {
        ws_open();
        if (mode == 0) ws_input_error = -84;
        if (mode == 1) ws_cancelled = 1;
        if (mode == 2) w_now = 5000;
        if (mode == 3) {
            uint64_t epoch; uint32_t pin;
            W_CHECK(!file_object_guard_snapshot(&w_guard, &epoch, w_now));
            W_CHECK(!file_object_guard_pin(&w_guard, &vfs_objects[0].key, w_server, w_client, epoch, w_now, &pin));
        }
        if (mode == 4) w_cut = 1;
        ws_run(REIST_VFS_WRITE_DATA, 0, 0, 20);
        W_CHECK(ws_reply.reply.result < 0 && !ws_reply.reply.durable_bytes);
        if (mode == 4) W_CHECK(ws_reply.reply.outcome == REIST_FILE_OBJECT_UNKNOWN && vfs_objects[0].closing);
        else W_CHECK(ws_reply.reply.outcome == REIST_FILE_OBJECT_NO_EFFECT && !w_effects);
    }
    printf("R342 write-service checks: %u\n", w_checks);
}
static void ws_client_tests(void) {
    for (unsigned mode = 0; mode < 11; ++mode) {
        ws_open();
        W_CHECK(!vfs_object_release(&vfs_objects[0]));
        ws_client_transport = 1; ws_submitted = 0;
        ws_client_calls = ws_fail_at = ws_fail_kind = ws_acknowledged = 0;
        ws_client_deadline = w_now+5000;
        reist_vfs_file_handle_t handle;
        reist_vfs_file_progress_t p;
        W_CHECK(!reist_vfs_file_open_writable("/TARGET.BIN", 5000, 255, 0, &handle));
        W_CHECK(!w_effects && ws_client_calls == 1 && ws_acknowledged == 1);
        ws_client_calls = ws_acknowledged = 0;
        ws_client_deadline = w_now+5000;
        unsigned before = w_reads;
        if (mode == 4 || mode == 5) { ws_fail_at = 3; ws_fail_kind = mode == 4 ? 1 : 2; }
        int status = mode == 7 ? reist_vfs_file_write_bounded(handle, NULL, 0, &p) :
            mode == 8 ? reist_vfs_file_pwrite_bounded(handle, NULL, 0, UINT32_MAX, &p) :
            mode == 9 ? reist_vfs_file_append_bounded(handle, NULL, 0, &p) :
            mode == 10 ? reist_vfs_file_resize_bounded(handle, 400U*512U, &p) :
            mode == 1 ? reist_vfs_file_append_bounded(handle, w_payload, 32771, &p) :
            mode == 2 ? reist_vfs_file_resize_bounded(handle, 0, &p) :
            mode == 3 ? reist_vfs_file_resize_bounded(handle, 400U*512U+32771, &p) :
            mode == 6 ? reist_vfs_file_pwrite_bounded(handle, w_payload, 20000, 400U*512U+1031, &p) :
                        reist_vfs_file_pwrite_bounded(handle, w_payload, 32771, 3, &p);
        W_CHECK((mode >= 7 ? p.steps == 1 : p.steps > 1) && p.steps == ws_client_calls);
        W_CHECK(w_reads-before < 10000U); /* no cold allocation/namespace re-scan per step */
        if (mode == 4 || mode == 5) {
            W_CHECK(status < 0 && p.outcome == REIST_FILE_OBJECT_UNKNOWN && p.steps == 3);
            W_CHECK(p.durable_bytes > 0 && p.durable_bytes < 32771);
            /* A valid UNKNOWN receipt is ACKed; it is not a committed step. */
            W_CHECK(ws_acknowledged == (mode == 4 ? 3U : 2U));
            W_CHECK(!(p.flags & REIST_VFS_FILE_PROGRESS_COMPLETE));
            W_CHECK(w_media_matches(3, (uint32_t)p.durable_bytes + (mode == 5 ? ws_reply.reply.durable_bytes : 0)));
            if (mode == 4) W_CHECK(file_object_guard_can_open(&w_guard, 0, w_now) == -REIST_EIO);
            uint32_t calls = ws_client_calls;
            reist_vfs_write_result_t r;
            W_CHECK(reist_vfs_file_pwrite_step(handle, w_payload, 1, 0, &r) == -116 && ws_client_calls == calls);
        } else if (mode >= 7) {
            W_CHECK(!status && !w_effects && !p.durable_bytes && !p.released_clusters);
            W_CHECK(p.outcome == REIST_FILE_OBJECT_NO_EFFECT && p.durable_size == 400U*512U);
            W_CHECK((p.flags & REIST_VFS_FILE_PROGRESS_COMPLETE) && ws_acknowledged == 1);
            W_CHECK(w_media_matches(0, 0));
        } else {
            W_CHECK(!status && (p.flags & REIST_VFS_FILE_PROGRESS_COMPLETE) && p.outcome == REIST_FILE_OBJECT_DURABLE_COMMIT);
            W_CHECK(ws_acknowledged == p.steps && w_flushes == 4U*p.steps);
            if (mode == 0) W_CHECK(p.durable_bytes == 32771 && w_media_matches(3, 32771));
            if (mode == 1) W_CHECK(p.durable_bytes == 32771 && w_grow_matches((uint32_t)p.durable_size, true));
            if (mode == 2) W_CHECK(!p.durable_size && p.released_clusters == 400 && w_shrink_matches(0, 400));
            if (mode == 3) W_CHECK(p.durable_size == 400U*512U+32771 && w_grow_matches((uint32_t)p.durable_size, false));
            if (mode == 6) {
                W_CHECK(p.durable_bytes == 20000 && p.durable_size == 400U*512U+1031+20000);
                uint8_t bytes[512];
                for (uint32_t offset = 400U*512U; offset < p.durable_size;) {
                    uint32_t amount = (uint32_t)p.durable_size-offset;
                    if (amount > sizeof(bytes)) amount = sizeof(bytes);
                    uint32_t read = 0;
                    W_CHECK(!reist_vfs_shadow_fat_object_read(&w_io, &vfs_write_proof.view.object, offset, bytes, amount, &read));
                    W_CHECK(read == amount);
                    for (uint32_t i = 0; i < read; ++i) {
                        uint32_t index = offset+i-400U*512U;
                        W_CHECK(bytes[i] == (index < 1031 ? 0 : w_payload[index-1031]));
                    }
                    offset += read;
                }
            }
        }
        ws_fail_at = 0; ws_client_deadline = w_now+5000;
        W_CHECK(!reist_vfs_file_close(handle));
        ws_client_transport = 0;
    }
    printf("R342 client-service integration checks: %u\n", w_checks);
}
#endif
int main(void) {
    memset(w_boot, 0, sizeof(w_boot)); w_boot[12] = 2; w_boot[13] = 1; w_boot[14] = 32; w_boot[16] = 2;
    w_put(w_boot+32, W_SECTORS); w_put(w_boot+36, W_FAT); w_put(w_boot+44, 2);
    w_boot[48] = 1; w_boot[50] = 6; w_boot[510] = 0x55; w_boot[511] = 0xaa;
    memcpy(w_entry, "TARGET  BIN", 11); w_entry[11] = 0x20; w_entry[26] = 3; w_put(w_entry+28, W_LENGTH*512);
    for (unsigned i = 0; i < sizeof(w_payload); ++i) w_payload[i] = (uint8_t)(i*3+1);
    w_reset(true);
    w_proof.whole_volume = 0; /* A valid local window must not authorize any write. */
#ifndef REIST_FAT32_OVERWRITE_VERSION
    /* The real existing generic adapter has no ownership/planner boundary.
     * Demonstrate the missing integration, not a mock of FAT or the journal. */
    int result = reist_fat32_transaction_stage(&w_tx, W_FIRST+W_DATA+w_cluster(0)-2, w_payload);
    W_CHECK(result == -REIST_EACCES);
#else
    reist_fat32_overwrite_t writer = {0};
    W_CHECK(reist_fat32_overwrite_begin(&writer, &w_proof, &w_tx, 3, w_payload, 2000) == -REIST_EACCES);
    w_negatives();
    unsigned effects = w_normal();
    w_retention(); w_oracle_negatives(); w_stage_faults(); w_commit_faults(effects); w_read_faults(); w_layouts();
#endif
    w_shrink_tests();
    w_grow_tests();
    w_sync_tests();
#ifdef R342_SERVICE_TEST
    ws_tests();
    ws_client_tests();
    ws_recovery_tests();
#endif
    printf("R342 overwrite checks: %u\n", w_checks); return 0;
}
#endif

#ifdef R342_READ_CONTEXT_TEST
#include <stdio.h>
#include <stdint.h>
#include "x86os.h"
typedef struct { int unused; } vfs_object_slot_t;
typedef struct { vfs_object_slot_t *slot; uint64_t deadline,last; } vfs_object_read_context_t;
static uint64_t now;
static int clock_error, guard_error, yield_error, io_error, after_io;
static unsigned checks, io_calls, yields, guards;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr,"read context:%d: %s\n",__LINE__,#x); return 1; } } while(0)
int x86os_monotonic_ms(uint64_t *out) { *out=now; return clock_error; }
int x86os_yield(void) { ++yields; ++now; return yield_error; }
static int vfs_object_guard_slot(vfs_object_slot_t *s, uint32_t operation) {
    (void)s; (void)operation; ++guards; return guard_error;
}
int x86os_drive_info(uint32_t resource,x86os_drive_info_t *info) {
    (void)resource; (void)info; ++io_calls; return 1;
}
int x86os_storage_block_read(uint32_t resource,uint32_t sector,void *data) {
    (void)resource; (void)sector; (void)data; ++io_calls; now+=after_io; return io_error;
}
#include "read_context.inc"
int main(void) {
    vfs_object_read_context_t c={.deadline=10};
    CHECK(!vfs_object_read_progress(&c) && guards==1 && yields==1 && c.last==1);
    now=10; CHECK(vfs_object_read_progress(&c)==-110 && guards==1 && yields==1);
    CHECK(vfs_object_read_sector(&c,0,0,0)==-110 && io_calls==0);
    x86os_drive_info_t info;
    CHECK(vfs_object_read_info(&c,0,&info)==-110 && io_calls==0);
    now=0; CHECK(vfs_object_read_clock(&c)==-110); /* regressed clock */
    now=2; guard_error=-116;
    CHECK(vfs_object_read_progress(&c)==-116 && yields==1);
    guard_error=0; yield_error=-5;
    CHECK(vfs_object_read_progress(&c)==-5 && yields==2);
    yield_error=0; clock_error=-5;
    CHECK(vfs_object_read_sector(&c,0,0,0)==-5 && io_calls==0);
    clock_error=0; now=9; CHECK(vfs_object_read_progress(&c)==-110 && now==10);
    now=10; c.last=0; c.deadline=20; after_io=10;
    CHECK(vfs_object_read_sector(&c,0,0,0)==-110 && io_calls==1);
    now=11; after_io=0; c.last=0;
    CHECK(vfs_object_read_info(&c,0,&info)==1 && io_calls==2);
    io_error=-5; CHECK(vfs_object_read_sector(&c,0,0,0)==-5 && io_calls==3);
    printf("R342 read-context checks: %u\n",checks); return 0;
}
#endif

#if defined(R342_CHAIN_TEST) || defined(R342_OWNERSHIP_TEST)
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include "userspace/storage/include/reist/vfs_shadow_fat32.h"
#ifdef R342_OWNERSHIP_TEST
#include "userspace/storage/include/reist/fat32_file_write.h"
#endif

enum { CHAIN_LENGTH = 10000, CLUSTERS = 100000, FAT_SECTORS = 782,
       DATA_START = 32 + 2*FAT_SECTORS, TOTAL_SECTORS = DATA_START + CLUSTERS };
static uint8_t boot[512], directory[512];
static uint32_t fat[CLUSTERS+2], reads, checks, different_cluster, read_cut;
static uint32_t volume_sectors;
#ifdef R342_OWNERSHIP_TEST
static uint8_t child_directory[512];
static uint32_t child_cluster, generated_depth;
#endif
static uint32_t data_start_value;
static int fail(const char* expression, int line) {
    fprintf(stderr, "R342 chain:%d: %s\n", line, expression); return 1;
}
#define CHECK(x) do { ++checks; if (!(x)) return fail(#x, __LINE__); } while (0)
static void put32(uint8_t* bytes, uint32_t value) {
    for (unsigned i = 0; i < 4; ++i) bytes[i] = (uint8_t)(value >> (8*i));
}
static uint32_t cluster_at(unsigned index) { return 3 + (index*7)%90001U; }
static int drive_info(void* context, uint32_t resource, x86os_drive_info_t* info) {
    (void)context;
    if (resource) return 0;
    memset(info, 0, sizeof(*info)); info->type = X86OS_DRIVE_PARTITION;
    info->sectors = volume_sectors; strcpy(info->mount_point, "/"); return 1;
}
static int read_sector(void* context, uint32_t resource, uint32_t sector, uint8_t* data) {
    (void)context;
    if (resource || sector >= volume_sectors) return -5;
    if (++reads == read_cut) return -5;
    memset(data, 0, 512);
    if (!sector) memcpy(data, boot, 512);
    else if (sector == data_start_value) memcpy(data, directory, 512);
#ifdef R342_OWNERSHIP_TEST
    else if (child_cluster && sector == data_start_value+(child_cluster-2)*boot[13])
        memcpy(data, child_directory, 512);
    else if (generated_depth && sector >= data_start_value+(80000-2)*boot[13] &&
             sector < data_start_value+(80000+generated_depth-2)*boot[13]) {
        uint32_t cluster = 2+(sector-data_start_value)/boot[13];
        memcpy(data, ".          ", 11); data[11] = 0x10;
        data[26] = (uint8_t)cluster; data[27] = (uint8_t)(cluster>>8); data[20] = (uint8_t)(cluster>>16);
        memcpy(data+32, "..         ", 11); data[43] = 0x10;
        uint32_t parent = cluster == 80000 ? 0 : cluster-1;
        data[58] = (uint8_t)parent; data[59] = (uint8_t)(parent>>8); data[52] = (uint8_t)(parent>>16);
        if (cluster+1 < 80000+generated_depth) {
            ++cluster; memcpy(data+64, "SUBDIR     ", 11); data[75] = 0x10;
            data[90] = (uint8_t)cluster; data[91] = (uint8_t)(cluster>>8); data[84] = (uint8_t)(cluster>>16);
        }
    }
#endif
    else if (sector >= 32 && sector < data_start_value) {
        unsigned copy = (sector-32)/FAT_SECTORS;
        unsigned first = ((sector-32)%FAT_SECTORS)*128;
        for (unsigned i = 0; i < 128 && first+i < CLUSTERS+2; ++i) {
            uint32_t value = fat[first+i] | (copy ? 0xa0000000U : 0xb0000000U);
            if (copy && different_cluster && first+i == different_cluster) value ^= 1;
            put32(data+i*4, value);
        }
    }
#ifdef R342_CHAIN_TEST
    else if (sector > data_start_value) {
        for(unsigned i=0;i<512;++i) data[i]=(uint8_t)(sector*17U+i*3U);
    }
#endif
    return 0;
}
static const reist_vfs_shadow_io_t io = {NULL, drive_info, read_sector};
static void reset_chain(void) {
    memset(boot, 0, sizeof(boot)); memset(directory, 0, sizeof(directory));
    memset(fat, 0, sizeof(fat));
    boot[12] = 2; boot[13] = 1; boot[14] = 32; boot[16] = 2;
    put32(boot+32, TOTAL_SECTORS); put32(boot+36, FAT_SECTORS); put32(boot+44, 2);
    boot[48] = 1; boot[50] = 6; boot[510] = 0x55; boot[511] = 0xaa;
    memcpy(directory, "LONG    BIN", 11); directory[11] = 0x20;
    directory[26] = 3; put32(directory+28, CHAIN_LENGTH*512);
    fat[0] = 0xffffff8; fat[1] = fat[2] = 0xfffffff;
    for (unsigned i = 0; i < CHAIN_LENGTH; ++i)
        fat[cluster_at(i)] = i+1 == CHAIN_LENGTH ? 0xfffffff : cluster_at(i+1);
    reads = different_cluster = read_cut = 0;
    volume_sectors = TOTAL_SECTORS;
    data_start_value = DATA_START;
#ifdef R342_OWNERSHIP_TEST
    child_cluster = generated_depth = 0;
    memset(child_directory, 0, sizeof(child_directory));
#endif
}
#ifdef R342_CHAIN_TEST
static unsigned continuations, checkpoint_reads, abort_at;
static int read_progress(void *context) {
    (void)context;
    if (reads-checkpoint_reads > REIST_VFS_SHADOW_MAX_SECTOR_READS) return -75;
    checkpoint_reads=reads;
    return ++continuations==abort_at ? -125 : 0;
}
static int long_read_case(void) {
    reist_vfs_shadow_object_t object; x86os_file_info_t info;
    reset_chain();
    CHECK(!reist_vfs_shadow_fat_object_open(&io,"/LONG.BIN",9,&object,&info));
    uint8_t data[513]; uint32_t count=0;
    CHECK(reist_vfs_shadow_fat_object_read(&io,&object,9000U*512U+3U,data,sizeof(data),&count)==-110);
    unsigned completed_callbacks=0;
    for(unsigned variant=0;variant<7;++variant) {
        reset_chain(); continuations=0; checkpoint_reads=reads; abort_at=variant==1?1:variant==2?4:0;
        memset(data,0xcc,sizeof(data)); count=0;
        if(variant==3) fat[cluster_at(8999)]=0xfffffff;
        if(variant==4) read_cut=reads+8;
        if(variant==5) fat[cluster_at(127)]=cluster_at(127); /* cycle at window edge */
        if(variant==6) abort_at=completed_callbacks; /* deny after data was copied */
        int result=reist_vfs_shadow_fat_object_read_windowed(&io,&object,
            9000U*512U+3U,data,sizeof(data),&count,read_progress,0);
        if(!variant) {
            CHECK(!result && count==sizeof(data) && continuations>60);
            completed_callbacks=continuations;
            for(unsigned i=0;i<sizeof(data);++i) {
                unsigned position=3U+i;
                uint32_t sector=DATA_START+cluster_at(9000U+position/512U)-2U;
                CHECK(data[i]==(uint8_t)(sector*17U+(position%512U)*3U));
            }
            CHECK(reads<1000); /* cached prefix, not full-volume requalification */
        } else {
            CHECK(result<0 && !count);
            for(unsigned i=0;i<sizeof(data);++i) CHECK(!data[i]);
            if(variant==1) CHECK(!reads);
        }
    }
    reset_chain(); continuations=0;checkpoint_reads=0;abort_at=0;
    CHECK(!reist_vfs_shadow_fat_object_read_windowed(&io,&object,CHAIN_LENGTH*512U,
        data,sizeof(data),&count,read_progress,0) && !count);
    return 0;
}
int main(void) {
    reist_vfs_shadow_object_t object;
    x86os_file_info_t info;
    reset_chain();
    CHECK(!long_read_case());
    CHECK(!reist_vfs_shadow_fat_object_open(&io, "/LONG.BIN", 9, &object, &info));
#ifndef REIST_VFS_SHADOW_FAT_CHAIN_VERSION
    /* Actual old path refuses this valid fragmented chain at its fixed walk
     * budget. The new API must yield bounded progress instead of hiding EOF. */
    uint8_t data[1]; uint32_t count = 0;
    CHECK(!reist_vfs_shadow_fat_object_read(&io, &object, (CHAIN_LENGTH-1)*512, data, 1, &count));
#else
    reist_vfs_shadow_fat_chain_cursor_t cursor;
    CHECK(sizeof(cursor) < 2048);
    for (unsigned variant = 0; variant < 13; ++variant) {
        reset_chain();
        uint32_t length = CHAIN_LENGTH;
        if (variant == 5) { directory[26] = 0; put32(directory+28, 0); }
        if (variant == 6) { boot[40] = 0x81; different_cluster = cluster_at(90); }
        if (variant == 9) directory[11] |= 1; /* read-only attribute remains visible */
        if (variant == 10) { boot[40] = 0x80; different_cluster = cluster_at(90); } /* inactive copy ignored */
        if (variant == 11) boot[40] = 1; /* active index ignored when mirroring enabled */
        if (variant == 12) {
            length = 70000;
            boot[13] = 128;
            volume_sectors = DATA_START + CLUSTERS*128U;
            put32(boot+32, volume_sectors); put32(directory+28, UINT32_MAX);
            for (uint32_t i = 0; i < length; ++i)
                fat[cluster_at(i)] = i+1 == length ? 0xfffffff : cluster_at(i+1);
        }
        CHECK(!reist_vfs_shadow_fat_object_open(&io, "/LONG.BIN", 9, &object, &info));
        CHECK(!reist_vfs_shadow_fat_chain_begin(&io, &object, 23, &cursor));
        CHECK((cursor.view.entry[11] & 1) == (variant == 9));
        if (variant == 1) different_cluster = cluster_at(9000);
        if (variant == 2) fat[cluster_at(9000)] = cluster_at(8500); /* late loop */
        if (variant == 3) fat[cluster_at(9000)] = 0xfffffff; /* short chain */
        if (variant == 4) fat[cluster_at(9000)] = 0xffffff7; /* bad cluster */
        if (variant == 7) put32(directory+28, CHAIN_LENGTH*512-1); /* foreign change */
        if (variant == 8) read_cut = reads+4;
        unsigned steps = 0; int status;
        do {
            uint32_t before = reads;
            status = reist_vfs_shadow_fat_chain_step(&io, 23, &cursor);
            CHECK(reads-before <= REIST_VFS_SHADOW_MAX_SECTOR_READS);
            CHECK(++steps < 1000);
        } while (status == 1);
        if (variant == 0 || variant == 5 || variant >= 9) {
            CHECK(!status && cursor.complete);
            CHECK(cursor.visited == (variant == 5 ? 0 : length));
            CHECK(reads < length/5); /* cached FAT windows, not a cold full walk per step */
        } else {
            CHECK(status < 0 && !cursor.complete);
            uint32_t before = reads;
            CHECK(reist_vfs_shadow_fat_chain_step(&io, 23, &cursor) == status);
            CHECK(reads == before); /* failure cannot turn into a restarted scan */
        }
        uint32_t before = reads;
        CHECK(reist_vfs_shadow_fat_chain_step(&io, 24, &cursor) == -116);
        CHECK(reads == before); /* old certificate cannot cross an epoch */
    }
#endif
    printf("R342 long-chain checks: %u\n", checks); return 0;
}
#else
static reist_fat32_ownership_t ownership;
static void another_entry(uint32_t cluster, uint32_t size) {
    memcpy(directory+32, "OTHER   BIN", 11); directory[43] = 0x20;
    directory[58] = (uint8_t)cluster; directory[59] = (uint8_t)(cluster>>8);
    directory[52] = (uint8_t)(cluster>>16); directory[53] = (uint8_t)(cluster>>24);
    put32(directory+60, size);
}
static int volume_cases(void) {
    for (unsigned variant = 0; variant < 21; ++variant) {
        reset_chain();
        bool nested = variant < 5 || variant == 18;
        if (nested) {
            child_cluster = 4; fat[4] = 0xfffffff;
            memcpy(child_directory+64, directory, 32);
            memset(directory, 0, sizeof(directory));
            memcpy(directory, "SUBDIR     ", 11); directory[11] = 0x10; directory[26] = 4;
            memcpy(child_directory, ".          ", 11); child_directory[11] = 0x10; child_directory[26] = 4;
            memcpy(child_directory+32, "..         ", 11); child_directory[43] = 0x10;
        }
        if (variant == 1) child_directory[58] = 3; /* invalid parent */
        if (variant == 2) { memcpy(directory+32, directory, 32); directory[32] = 'A'; }
        if (variant == 3) {
            memcpy(child_directory+96, "LOOP       ", 11);
            child_directory[107] = 0x10; child_directory[122] = 2;
        }
        if (variant == 4) fat[4] = 3;
        if (variant == 5) { fat[2] = 5; fat[5] = 0xfffffff; } /* allocated directory tail after end marker */
        if (variant == 6) fat[99999] = 0xfffffff; /* only the second window sees this orphan */
        if (variant == 10) {
            boot[16] = 1; data_start_value = 32+FAT_SECTORS;
            volume_sectors = data_start_value+CLUSTERS; put32(boot+32, volume_sectors);
        }
        if (variant == 11) { boot[13] = 2; volume_sectors = DATA_START+CLUSTERS*2; put32(boot+32, volume_sectors); }
        if (variant == 12 || variant == 13) {
            generated_depth = variant == 12 ? 31 : 32;
            another_entry(80000, 0); directory[43] = 0x10;
            for (uint32_t i = 0; i < generated_depth; ++i) fat[80000+i] = 0xfffffff;
        }
        if (variant == 14 || variant == 15) {
            boot[13] = 128; volume_sectors = DATA_START+CLUSTERS*128U;
            put32(boot+32, volume_sectors); put32(directory+28, UINT32_MAX);
            uint32_t length = variant == 14 ? 65536 : 70000;
            for (uint32_t i = 0; i < length; ++i)
                fat[cluster_at(i)] = i+1 == length ? 0xfffffff : cluster_at(i+1);
        }
        if (variant == 16 || variant == 17) {
            boot[13] = 128; volume_sectors = DATA_START+CLUSTERS*128U; put32(boot+32, volume_sectors);
            uint32_t length = variant == 16 ? 31 : 32;
            fat[2] = 80000;
            for (uint32_t i = 0; i < length; ++i) fat[80000+i] = i+1 == length ? 0xfffffff : 80001+i;
        }
        if (variant == 18) { child_directory[11] = 0xf7; child_directory[43] = 0x37; }
        if (variant == 19 || variant == 20) {
            another_entry(4, 512); fat[4] = 0xfffffff; memcpy(directory+32, directory, 11);
            if (variant == 20) directory[32] = 'l';
        }
        const char* path = nested ? "/SUBDIR/LONG.BIN" : "/LONG.BIN";
        reist_vfs_shadow_object_t object; x86os_file_info_t info;
        CHECK(!reist_vfs_shadow_fat_object_open(&io, path, (uint32_t)strlen(path), &object, &info));
        CHECK(!reist_fat32_volume_begin(&ownership, &io, &object, 17));
        if (variant == 7) read_cut = reads+3;
        unsigned steps = 0, windows = 0, start_reads = reads; int status;
        do {
            uint32_t before = reads, window_before = ownership.first;
            status = reist_fat32_ownership_step(&ownership, &io, variant == 8 && steps == 2 ? 18 : 17);
            CHECK(reads-before <= REIST_VFS_SHADOW_MAX_SECTOR_READS);
            CHECK(++steps < 1000);
            if (ownership.first != window_before) { ++windows; CHECK(!ownership.ready); }
            if (variant == 9 && steps == 2) boot[67] ^= 1;
        } while (status == 1);
        bool good = variant == 0 || variant == 5 || (variant >= 10 && variant <= 12) ||
                    variant == 14 || variant == 16 || variant == 18;
        if (good) {
            CHECK(!status && ownership.ready && windows == 1);
            CHECK(ownership.verified_until == CLUSTERS+2);
            CHECK(reads-start_reads < (variant == 14 ? 24000U : 8000U));
            uint32_t before = reads;
            CHECK(!reist_fat32_ownership_step(&ownership, &io, 17) && reads-before == 2); /* no rescan */
            uint32_t classification;
            CHECK(!reist_fat32_ownership_query(&ownership, 17, nested ? 4 : 2, &classification) &&
                  classification == REIST_FAT32_CLUSTER_DIRECTORY);
        } else {
            CHECK(status < 0 && !ownership.ready);
            if (variant == 6) CHECK(windows == 1); /* no early publication after window one */
            if (variant == 13) CHECK(status == -7); /* explicit workspace/depth error, not ENOSPC */
            unsigned before = reads;
            CHECK(reist_fat32_ownership_step(&ownership, &io, 17) == status && reads == before);
        }
    }
    return 0;
}
static int ownership_faults(void) {
    static const unsigned cuts[] = {1, 2, 3, 4, 317, 318, 319, 320, 1000, 2000, 3000};
    for (unsigned cut = 0; cut < sizeof(cuts)/sizeof(cuts[0]); ++cut) {
        reset_chain();
        reist_vfs_shadow_object_t object; x86os_file_info_t info;
        CHECK(!reist_vfs_shadow_fat_object_open(&io, "/LONG.BIN", 9, &object, &info));
        CHECK(!reist_fat32_volume_begin(&ownership, &io, &object, 17));
        read_cut = reads+cuts[cut];
        int status; unsigned steps = 0;
        do {
            unsigned before = reads;
            status = reist_fat32_ownership_step(&ownership, &io, 17);
            CHECK(reads-before <= REIST_VFS_SHADOW_MAX_SECTOR_READS && ++steps < 1000);
        } while (status == 1);
        CHECK(status == -5 && reads == read_cut && !ownership.ready);
        read_cut = 0;
        unsigned before = reads;
        CHECK(reist_fat32_ownership_step(&ownership, &io, 17) == -5 && reads == before);
        uint32_t classification = 123;
        CHECK(reist_fat32_ownership_query(&ownership, 17, 3, &classification) == -5 && !classification);
    }
    for (unsigned field = 0; field < 5; ++field) {
        reset_chain();
        reist_vfs_shadow_object_t object; x86os_file_info_t info;
        CHECK(!reist_vfs_shadow_fat_object_open(&io, "/LONG.BIN", 9, &object, &info));
        CHECK(!reist_fat32_volume_begin(&ownership, &io, &object, 17));
        if (field == 0) ownership.count = REIST_FAT32_OWNERSHIP_CLUSTERS+1;
        if (field == 1) ownership.cache_valid[2] = 2;
        if (field == 2) ownership.depth = REIST_FAT32_OWNERSHIP_DEPTH+1;
        if (field == 3) ownership.phase = 99;
        if (field == 4) ownership.error = 1;
        unsigned before = reads;
        int result = reist_fat32_ownership_step(&ownership, &io, 17);
        CHECK(result == (field == 4 ? -5 : -22) && !ownership.ready && reads-before <= 2);
    }
    return 0;
}
int main(void) {
    CHECK(sizeof(ownership) < 48*1024);
    for (unsigned variant = 0; variant < 15; ++variant) {
        reset_chain();
        if (variant == 1) another_entry(3, CHAIN_LENGTH*512); /* shared starting cluster */
        if (variant == 2) { another_entry(99997, 1024); fat[99997] = cluster_at(90); } /* shared suffix */
        if (variant == 3) fat[99997] = cluster_at(90); /* orphan outside window refers into file */
        if (variant == 4) { another_entry(4, 512); fat[4] = 0; } /* namespace points at free cluster */
        if (variant == 5) fat[4] = 0xfffffff; /* orphan inside window */
        if (variant == 6) { directory[26] = 0; put32(directory+28, 0); memset(fat+3, 0, sizeof(fat)-12); }
        if (variant == 7) different_cluster = cluster_at(90);
        if (variant == 8) fat[cluster_at(9000)] = cluster_at(8990);
        if (variant == 9) { another_entry(4, 0); directory[43] = 0x10; fat[4] = 0xfffffff; } /* no dot entries */
        if (variant == 10) { another_entry(3, 0); directory[43] = 0x0f; } /* LFN masquerades as cluster owner */
        if (variant == 12) { boot[40] = 0x80; different_cluster = cluster_at(90); }
        if (variant == 13) fat[4] = 0xffffff7; /* unavailable is not free */
        reist_vfs_shadow_object_t object;
        x86os_file_info_t info;
        CHECK(!reist_vfs_shadow_fat_object_open(&io, "/LONG.BIN", 9, &object, &info));
        if (variant == 1 || variant == 2 || variant == 3 || variant == 5) {
            /* The real local chain check passes: this is the missing ownership
             * guarantee, not just another loop/range test. */
            reist_vfs_shadow_fat_chain_cursor_t chain;
            CHECK(!reist_vfs_shadow_fat_chain_begin(&io, &object, 7, &chain));
            int status; do { status = reist_vfs_shadow_fat_chain_step(&io, 7, &chain); } while (status == 1);
            CHECK(!status);
        }
        unsigned first = variant == 11 ? 65538 : 2;
        CHECK(!reist_fat32_ownership_begin(&ownership, &io, &object, 7, first));
        uint32_t classification = 99;
        CHECK(reist_fat32_ownership_query(&ownership, 7, 3, &classification) == -11 && !classification);
        unsigned steps = 0, start_reads = reads; int status;
        do {
            uint32_t before = reads;
            status = reist_fat32_ownership_step(&ownership, &io, 7);
            CHECK(reads-before <= REIST_VFS_SHADOW_MAX_SECTOR_READS);
            CHECK(++steps < 1000);
            if (variant == 14 && steps == 2) put32(directory+28, CHAIN_LENGTH*512-1);
        } while (status == 1);
        if (!variant || variant == 6 || variant == 11 || variant == 12 || variant == 13) {
            CHECK(!status && ownership.ready);
            CHECK(reads-start_reads < 4000);
            CHECK(!reist_fat32_ownership_query(&ownership, 7, 2, &classification) &&
                  classification == REIST_FAT32_CLUSTER_DIRECTORY);
            CHECK(!reist_fat32_ownership_query(&ownership, 7, variant == 11 ? cluster_at(9500) : 3, &classification));
            CHECK(classification == (variant == 6 ? REIST_FAT32_CLUSTER_FREE : REIST_FAT32_CLUSTER_FILE));
            if (variant == 11) {
                CHECK(reist_fat32_ownership_query(&ownership, 7, 3, &classification) == -11 && !classification);
            } else {
                CHECK(!reist_fat32_ownership_query(&ownership, 7, 4, &classification));
                CHECK(classification == (variant == 13 ? REIST_FAT32_CLUSTER_OTHER : REIST_FAT32_CLUSTER_FREE));
            }
        } else {
            CHECK(status < 0 && !ownership.ready);
            uint32_t before = reads;
            CHECK(reist_fat32_ownership_step(&ownership, &io, 7) == status && reads == before);
            CHECK(reist_fat32_ownership_query(&ownership, 7, 3, &classification) == status && !classification);
        }
        CHECK(reist_fat32_ownership_query(&ownership, 8, 2, &classification) == -116 && !classification);
    }
    CHECK(!volume_cases());
    CHECK(!ownership_faults());
    for (unsigned variant = 0; variant < 9; ++variant) {
        reset_chain();
        if (variant == 1) { memset(directory, 0, sizeof(directory)); memset(fat+3, 0, sizeof(fat)-12); }
        if (variant == 2) fat[99997] = 0xfffffff; /* far-window orphan */
        if (variant == 3) another_entry(3, CHAIN_LENGTH*512);
        if (variant == 4) different_cluster = 3;
        if (variant == 5) fat[cluster_at(9000)] = cluster_at(8990);
        if (variant == 6) { boot[40] = 0x80; different_cluster = 3; }
        CHECK(!reist_fat32_recovery_begin(&ownership, &io, 0, 77));
        int status; unsigned steps = 0;
        do {
            if (variant == 7 && steps == 3) boot[13] = 2;
            if (variant == 8 && steps == 3) read_cut = reads+1;
            uint32_t before = reads;
            status = reist_fat32_ownership_step(&ownership, &io, 77);
            CHECK(reads-before <= REIST_VFS_SHADOW_MAX_SECTOR_READS && ++steps < 1000);
        } while (status == 1);
        if (variant == 0 || variant == 1 || variant == 6) {
            CHECK(!status && ownership.ready && ownership.verified_until == CLUSTERS+2 && !ownership.target_seen && !ownership.file_owned);
            uint32_t classification;
            CHECK(reist_fat32_ownership_query(&ownership, 77, 3, &classification) == -13 && !classification);
            CHECK(!ownership.view.object.version && !ownership.view.object.filesystem);
        } else CHECK(status < 0 && !ownership.ready);
    }
    printf("R342 ownership checks: %u\n", checks); return 0;
}
#endif
#endif

#ifdef R342_OWNED_PIN_TEST
#include <stdio.h>
#include <string.h>
#include "include/kernel/file_object_guard.h"

static file_object_guard_t guard;
static const file_object_owner_t service = {40, 8}, client = {50, 9};
static reist_file_object_key_t key;
static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr, "R342:%d: %s\n", __LINE__, #x); return 1; } } while (0)

static uint64_t epoch(void) {
    uint64_t value = 0;
    if (file_object_guard_snapshot(&guard, &value, 100)) return 0;
    return value;
}

static int owned(uint32_t pin, uint32_t request, const reist_file_object_key_t *object,
                 file_object_owner_t server, file_object_owner_t consumer,
                 uint64_t observed, uint64_t now, uint64_t deadline, uint32_t *token) {
#ifdef FILE_OBJECT_GUARD_OWNED_VERSION
    return file_object_guard_begin_owned(&guard, object, pin, request, server,
        consumer, observed, now, deadline, token);
#else
    /* Baseline behavior, not a mock of the missing implementation. */
    (void)pin; (void)request; (void)consumer;
    return file_object_guard_begin_mode(&guard, object, 1,
        REIST_FILE_OBJECT_EXCLUSIVE | REIST_FILE_OBJECT_EXTERNAL_JOURNAL,
        server, observed, now, deadline, token);
#endif
}

static int reset(uint32_t *pin) {
    memset(&guard, 0, sizeof(guard));
    key = (reist_file_object_key_t){.kind=REIST_FILE_OBJECT_FAT32, .resource=1, .object_a=2};
    memcpy(key.alias, "FILE    TXT", 11);
    CHECK(file_object_guard_init(&guard) == 0);
    CHECK(file_object_guard_pin(&guard, &key, service, client, epoch(), 100, pin) == 0);
    return 0;
}

int main(void) {
    uint32_t pin, other, token = 0, count = 0, mask = 0;
    CHECK(reset(&pin) == 0);
    CHECK(file_object_guard_begin_mode(&guard, &key, 1, 3, service, epoch(), 100, 500,
                                       &token) == -REIST_EBUSY);
    CHECK(file_object_guard_verify(&guard, pin, service, client, 100) == 0);
    CHECK(owned(pin, 101, &key, service, client, epoch(), 100, 500, &token) == 0);
    CHECK(token != 0);
    CHECK(file_object_guard_verify(&guard, pin, service, client, 101) == 0);
    CHECK(file_object_guard_end(&guard, token, service, REIST_FILE_OBJECT_NO_EFFECT, 102) == 0);
    CHECK(file_object_guard_count(&guard, 1, &count, 103) == 0 && count == 1);
    CHECK(file_object_guard_verify(&guard, pin, service, client, 103) == 0);
    CHECK(file_object_guard_fenced(&guard, &mask) == 0 && mask == 0);

#ifdef FILE_OBJECT_GUARD_OWNED_VERSION
    uint32_t request = 999;
    uint64_t deadline = 999;
    CHECK(file_object_guard_owned_request(&guard, service, token, 1, 103, &request, &deadline)
          == -REIST_ESTALE && request == 0 && deadline == 0);
#endif

    file_object_owner_t foreign = {client.pid, client.generation+1};
    token = 999;
    CHECK(owned(pin, 101, &key, service, foreign, epoch(), 100, 500, &token) == -REIST_EACCES);
    CHECK(token == 0);
    CHECK(owned(pin, 0, &key, service, client, epoch(), 100, 500, &token) == -REIST_EINVAL);
    CHECK(owned(pin, 101, &key, service, client, epoch(), 100, 5101, &token) == -REIST_EINVAL);
    CHECK(owned(pin, 101, &key, service, client, epoch(), 100, 100, &token) == -REIST_EINVAL);
    reist_file_object_key_t alias = key;
    alias.alias[0] = 'Z';
    CHECK(owned(pin, 101, &alias, service, client, epoch(), 100, 500, &token) == -REIST_EACCES);
    CHECK(owned(pin, 101, &key, foreign, client, epoch(), 100, 500, &token) == -REIST_EACCES);

    CHECK(file_object_guard_pin(&guard, &alias, service, client, epoch(), 100, &other) == 0);
    CHECK(owned(pin, 101, &key, service, client, epoch(), 100, 500, &token) == -REIST_EBUSY);
    CHECK(file_object_guard_release(&guard, other, service, client) == 0);
    alias.resource = 2;
    CHECK(file_object_guard_pin(&guard, &alias, service, client, epoch(), 100, &other) == 0);
    CHECK(owned(pin, 101, &key, service, client, epoch(), 100, 500, &token) == 0);
#ifdef FILE_OBJECT_GUARD_OWNED_VERSION
    CHECK(file_object_guard_owned_request(&guard, service, token, 1, 110, &request, &deadline) == 0);
    CHECK(request == 101 && deadline == 500);
    CHECK(file_object_guard_owned_request(&guard, service, token, 2, 110, &request, &deadline)
          == -REIST_EACCES && !request && !deadline);
#endif
    CHECK(file_object_guard_mutation_authorized(&guard, service, 1, 110) == -REIST_EBUSY);
    CHECK(file_object_guard_journal_io(&guard, service, token, 1, FILE_OBJECT_JOURNAL_WRITE, 110, NULL) == 0);
    CHECK(file_object_guard_end(&guard, token, service, REIST_FILE_OBJECT_NO_EFFECT, 110) == -REIST_EINVAL);
    CHECK(file_object_guard_end(&guard, token, service, REIST_FILE_OBJECT_DURABLE_COMMIT, 110) == -REIST_EINVAL);
    CHECK(file_object_guard_journal_io(&guard, service, token, 1, FILE_OBJECT_JOURNAL_FLUSHED, 110, NULL) == 0);
    CHECK(file_object_guard_end(&guard, token, service, REIST_FILE_OBJECT_DURABLE_COMMIT, 110) == 0);
    CHECK(file_object_guard_verify(&guard, pin, service, client, 111) == 0);

    /* Releasing the borrowed pin must retire/fence before removing its identity. */
    CHECK(owned(pin, 102, &key, service, client, epoch(), 100, 500, &token) == 0);
    CHECK(file_object_guard_release(&guard, pin, service, client) == 0);
    CHECK(file_object_guard_release(&guard, pin, service, client) == 0);
    CHECK(file_object_guard_fenced(&guard, &mask) == 0 && mask == 2);
    CHECK(file_object_guard_journal_io(&guard, service, token, 1, FILE_OBJECT_JOURNAL_CHECK, 110, NULL) < 0);
    CHECK(file_object_guard_verify(&guard, other, service, client, 110) == 0);

    for (unsigned scenario = 0; scenario < 4; ++scenario) {
        CHECK(reset(&pin) == 0);
        CHECK(owned(pin, 103, &key, service, client, epoch(), 100, 500, &token) == 0);
        CHECK(file_object_guard_journal_io(&guard, service, token, 1, FILE_OBJECT_JOURNAL_WRITE, 110, NULL) == 0);
        if (scenario == 0) CHECK(file_object_guard_cleanup(&guard, client) == 0);
        if (scenario == 1) CHECK(file_object_guard_cleanup(&guard, service) == 0);
        if (scenario == 2) CHECK(file_object_guard_revoke_media(&guard, 1) == 0);
        if (scenario == 3) CHECK(file_object_guard_poll(&guard, 500) == 0);
        CHECK(file_object_guard_fenced(&guard, &mask) == 0 && mask == 2);
        CHECK(file_object_guard_can_open(&guard, 2, 501) == 0);
        CHECK(file_object_guard_verify(&guard, pin, service, client, 501) < 0);
        CHECK(file_object_guard_init(&guard) == 0);
        CHECK(file_object_guard_fenced(&guard, &mask) == 0 && mask == 2);
    }
    CHECK(reset(&pin) == 0);
    CHECK(owned(pin, 104, &key, service, client, epoch(), 100, 500, &token) == 0);
    CHECK(file_object_guard_poll(&guard, 500) == 0);
    CHECK(file_object_guard_fenced(&guard, &mask) == 0 && !mask);
    CHECK(file_object_guard_verify(&guard, pin, service, client, 501) == 0);
    CHECK(reset(&pin) == 0);
    CHECK(file_object_guard_release(&guard, pin, service, client) == 0);
    CHECK(file_object_guard_pin(&guard, &key, service, client, epoch(), 100, &other) == 0);
    CHECK(other != pin);
    CHECK(owned(pin, 104, &key, service, client, epoch(), 100, 500, &token) == -REIST_ESTALE);
    CHECK(file_object_guard_verify(&guard, other, service, client, 110) == 0);
    CHECK(file_object_guard_fenced(&guard, &mask) == 0 && mask == 0);
    printf("R342 owned-pin checks: %u\n", checks);
    return 0;
}
#elif defined(R342_INPUT_TEST)
#include <stdio.h>
#include <string.h>
#include "include/kernel/storage_request_pool.h"
static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr, "R342 input:%d: %s\n", __LINE__, #x); return 1; } } while (0)
static uint8_t frame[512], bytes[128*1024];
#ifdef STORAGE_REQUEST_INPUT_VERSION
static uint8_t output[512], copy[128*1024];
#endif
static storage_request_submit_t submit = {1, sizeof(submit), 35, 0, sizeof(bytes), 512, 200};
#ifdef STORAGE_REQUEST_INPUT_VERSION
static storage_request_handle_t cancel_handle, attempted_handle;
static int cancel_result, second_cancel_result, capacity_result;
static void cancel_during_copy(void) {
    storage_request_test_set_input_hook(NULL);
    cancel_result = storage_request_cancel(50, 9, cancel_handle);
    second_cancel_result = storage_request_cancel(50, 9, cancel_handle);
    capacity_result = storage_request_submit(52, 9, &submit, frame, 100, &attempted_handle);
}
#endif
int main(void) {
    storage_request_handle_t handle = 0;
    CHECK(storage_request_pool_init() == 0);
    CHECK(storage_request_bind_service(40, 8) == 0);
    memset(frame, 0x11, sizeof(frame));
    for (unsigned i=0; i<sizeof(bytes); ++i) bytes[i]=(uint8_t)(i * 17U + (i >> 8));
    CHECK(storage_request_submit(50, 9, &submit, frame, 100, &handle) == 0);
#ifdef STORAGE_REQUEST_INPUT_VERSION
    storage_request_descriptor_v2_t old;
    storage_request_descriptor_v3_t request;
    uint32_t taken = 777;
    int32_t result = 777;
    CHECK(storage_request_claim_v3(40, 8, 100, &request, output) == -11);
    CHECK(storage_request_input_publish(50, 10, handle, bytes, sizeof(bytes), 100) == -13);
    CHECK(storage_request_input_publish(50, 9, handle, bytes, sizeof(bytes)-1, 100) == -90);
    CHECK(storage_request_input_publish(50, 9, handle, bytes, sizeof(bytes), 100) == 0);
    CHECK(storage_request_input_publish(50, 9, handle, bytes, sizeof(bytes), 100) < 0);
    CHECK(storage_request_claim_v2(40, 8, 100, &old, output) == -11);
    CHECK(storage_request_claim_v3(40, 8, 101, &request, output) == 0);
    CHECK(request.version == 3 && request.struct_size == 48 && request.deadline_ms == 300);
    CHECK(request.client_pid == 50 && request.client_generation == 9 && request.service_generation == 8);
    CHECK(memcmp(frame, output, sizeof(frame)) == 0);
    CHECK(storage_request_mutation_context(40, 8, handle, 101, &request) == -11);
    CHECK(storage_request_bulk_publish(40, 8, handle, bytes, sizeof(bytes)) == -13);
    CHECK(storage_request_input_take(40, 7, handle, copy, sizeof(copy), &taken, 101) == -13 && taken == 0);
    CHECK(storage_request_input_take(40, 8, handle, copy, sizeof(copy)-1, &taken, 101) == -90 && taken == 0);
    CHECK(storage_request_input_take(40, 8, handle, copy, sizeof(copy), &taken, 101) == 0);
    CHECK(taken == sizeof(bytes) && memcmp(copy, bytes, sizeof(bytes)) == 0);
    CHECK(storage_request_input_take(40, 8, handle, copy, sizeof(copy), &taken, 101) < 0 && taken == 0);
    CHECK(storage_request_mutation_context(40, 8, handle, 102, &request) == 0 && request.deadline_ms == 300);
    CHECK(storage_request_mutation_context(40, 8, handle, 300, &request) == -110);
    CHECK(storage_request_complete(40, 8, handle, 0, frame) == 0);
    CHECK(storage_request_mutation_reply_begin(50, 9, handle, 102, &result, output) == 0 && result == 0);
    CHECK(storage_request_mutation_reply_end(50, 9, handle, true, 102) == 0);
    CHECK(storage_request_mutation_reply_ack(50, 9, handle, 102) == 0);
    CHECK(memcmp(frame, output, sizeof(frame)) == 0);
    CHECK(storage_request_input_publish(50, 9, handle, bytes, sizeof(bytes), 102) < 0);

    /* Pending input expires without ever being claimed; no abandoned bulk slot. */
    for (unsigned i=0; i<8; ++i) {
        CHECK(storage_request_submit(50, 9, &submit, frame, 100, &handle) == 0);
        CHECK(storage_request_claim_v3(40, 8, 300, &request, output) == -11);
        CHECK(storage_request_mutation_reply_begin(50, 9, handle, 300, &result, output) == -110);
    }
    CHECK(storage_request_submit(50, 9, &submit, frame, 100, &handle) == 0);
    CHECK(storage_request_input_publish(50, 9, handle, bytes, sizeof(bytes), 100) == 0);
    CHECK(storage_request_claim_v3(40, 8, 100, &request, output) == 0);
    CHECK(storage_request_test_corrupt_bulk(handle) == 0);
    memset(copy, 0x7c, sizeof(copy));
    CHECK(storage_request_input_take(40, 8, handle, copy, sizeof(copy), &taken, 101) == -84 && !taken);
    CHECK(storage_request_mutation_context(40, 8, handle, 102, &request) < 0);
    CHECK(storage_request_cancel(50, 9, handle) == 0);
    CHECK(storage_request_mutation_context(40, 8, handle, 102, &request) == -125);
    CHECK(storage_request_complete(40, 8, handle, -125, NULL) == 0);

    for (unsigned direction=0; direction<2; ++direction) {
        CHECK(storage_request_pool_init() == 0);
        CHECK(storage_request_bind_service(40, 8) == 0);
        submit.offset = sizeof(bytes);
        storage_request_handle_t held;
        CHECK(storage_request_submit(50, 9, &submit, frame, 100, &cancel_handle) == 0);
        CHECK(storage_request_submit(51, 9, &submit, frame, 100, &held) == 0);
        if (direction) {
            CHECK(storage_request_input_publish(50, 9, cancel_handle, bytes, sizeof(bytes), 100) == 0);
            CHECK(storage_request_claim_v3(40, 8, 100, &request, output) == 0);
        }
        storage_request_test_set_input_hook(cancel_during_copy);
        if (!direction) {
            CHECK(storage_request_input_publish(50, 9, cancel_handle, bytes, sizeof(bytes), 100) == -125);
            CHECK(second_cancel_result < 0);
        } else {
            CHECK(storage_request_input_take(40, 8, cancel_handle, copy, sizeof(copy), &taken, 100) == -125);
            CHECK(!taken && second_cancel_result == 0);
            for (unsigned i=0; i<sizeof(copy); ++i) CHECK(copy[i] == 0);
            CHECK(storage_request_complete(40, 8, cancel_handle, -125, NULL) == 0);
        }
        CHECK(cancel_result == 0 && capacity_result == -28);
        CHECK(storage_request_submit(52, 9, &submit, frame, 100, &attempted_handle) == 0);
        CHECK(storage_request_cancel(52, 9, attempted_handle) == 0);
        CHECK(storage_request_cancel(51, 9, held) == 0);
    }

    /* Control-only object mutations need no bulk buffer, but still require v3. */
    submit.offset = 0;
    CHECK(storage_request_submit(50, 9, &submit, frame, 100, &handle) == 0);
    CHECK(storage_request_claim_v3(40, 8, 100, &request, output) == 0);
    CHECK(storage_request_mutation_context(40, 8, handle, 101, &request) == 0);
    CHECK(storage_request_input_publish(50, 9, handle, NULL, 0, 100) < 0);
    CHECK(storage_request_cancel(50, 9, handle) == 0);
    CHECK(storage_request_mutation_context(40, 8, handle, 101, &request) == -125);
    CHECK(storage_request_complete(40, 8, handle, -125, NULL) == 0);
#endif
    printf("R342 complete-input checks: %u\n", checks);
    return 0;
}
#elif defined(R342_RECEIPT_TEST)
#include <stdio.h>
#include <string.h>
#include "include/kernel/storage_request_pool.h"
static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr, "R342 receipt:%d: %s\n", __LINE__, #x); return 1; } } while (0)
static uint8_t frame[512], output[512];
static storage_request_submit_t submit = {1, sizeof(submit), 35, 0, 0, 512, 200};
static int claimed(storage_request_handle_t* handle) {
    storage_request_descriptor_v3_t request;
    int result=storage_request_submit(50, 9, &submit, frame, 100, handle);
    return result ? result : storage_request_claim_v3(40, 8, 100, &request, output);
}
int main(void) {
    storage_request_handle_t handle=0;
    int32_t result=777;
    CHECK(storage_request_pool_init() == 0 && storage_request_bind_service(40, 8) == 0);
    CHECK(claimed(&handle) == 0);
    CHECK(storage_request_complete(40, 8, handle, 0, frame) == 0);
    /* The legacy collector releases before syscall copyout/semantic validation.
     * Mutation replies must be inaccessible through that destructive path. */
    CHECK(storage_request_collect(50, 9, handle, &result, output) == -22);
#ifdef STORAGE_REQUEST_RECEIPT_VERSION
    CHECK(storage_request_mutation_reply_begin(50, 9, handle, 101, &result, output) == 0 && result == 0);
    CHECK(storage_request_mutation_reply_end(50, 9, handle, false, 101) == 0);
    uint32_t mask=777;
    CHECK(storage_request_mutation_fences(101, &mask) == 0 && !mask);

    /* Every interruption after a possible write, including after durable END,
     * retains a resource fence. No media callback runs under the pool lock. */
    for (unsigned cut=0; cut<8; ++cut) {
        CHECK(storage_request_pool_init() == 0 && storage_request_bind_service(40, 8) == 0);
        CHECK(claimed(&handle) == 0);
        CHECK(storage_request_mutation_bind(40, 8, handle, 3, 101) == 0);
        CHECK(storage_request_mutation_authorized(40, 8, handle, 3, 101) == 0);
        CHECK(storage_request_mutation_authorized(40, 8, handle, 4, 101) == -13);
        CHECK(storage_request_mutation_authorized(40, 8, handle, 3, 300) == -110);
        CHECK(storage_request_mutation_bind(40, 8, handle, 4, 101) == -13);
        CHECK(storage_request_complete(40, 8, handle, 0, frame) == -11);
        CHECK(storage_request_mutation_effect(40, 7, handle, 3, 101) == -13);
        CHECK(storage_request_mutation_effect(40, 8, handle, 4, 101) == -13);
        CHECK(storage_request_mutation_effect(40, 8, handle, 3, 300) == -110);
        CHECK(storage_request_mutation_effect(40, 8, handle, 3, 102) == 0);
        CHECK(storage_request_mutation_finish(40, 8, handle, 3, STORAGE_MUTATION_NO_EFFECT, 102) == -13);
        if (cut >= 2) {
            CHECK(storage_request_mutation_finish(40, 8, handle, 3, STORAGE_MUTATION_DURABLE, 102) == 0);
            CHECK(storage_request_mutation_effect(40, 8, handle, 3, 102) == -13);
            CHECK(storage_request_complete(40, 8, handle, 0, frame) == 0);
        }
        if (cut == 0 || cut == 2) CHECK(storage_request_cancel(50, 9, handle) == 0);
        if (cut == 1 || cut == 3) storage_request_cancel_process(40, 8);
        if (cut >= 4 && cut <= 6) {
            CHECK(storage_request_mutation_reply_begin(50, 9, handle, 103, &result, output) == 0);
            CHECK(storage_request_mutation_reply_begin(50, 9, handle, 103, &result, output) < 0);
            CHECK(storage_request_mutation_reply_ack(50, 9, handle, 103) < 0);
            if (cut == 5) {
                CHECK(storage_request_cancel(50, 9, handle) == 0);
                CHECK(storage_request_cancel(50, 9, handle) == 0);
                storage_request_cancel_process(50, 9);
                storage_request_stats_t stats;
                CHECK(storage_request_stats(&stats) == 0 && stats.active_requests == 1);
                CHECK(storage_request_mutation_reply_end(50, 9, handle, true, 104) == -125);
            } else {
                CHECK(storage_request_mutation_reply_end(50, 9, handle, cut == 6, 104) == 0);
                if (cut == 6) CHECK(storage_request_cancel(50, 9, handle) == 0); /* Malformed reply. */
            }
        }
        CHECK(storage_request_mutation_fences(cut == 7 ? 300 : 105, &mask) == 0 && mask == (1U<<3));
        storage_request_unbind_service(40, 8);
        CHECK(storage_request_bind_service(41, 10) == 0);
        CHECK(storage_request_mutation_fences(301, &mask) == 0 && mask == (1U<<3));
        CHECK(storage_request_recovery_refence(4) == 0);
        CHECK(storage_request_recovery_clear(40, 8, 3) == -13);
        CHECK(storage_request_recovery_ready(41, 10, 3) == 0);
        CHECK(storage_request_recovery_clear(41, 10, 3) == 0);
        CHECK(storage_request_mutation_fences(301, &mask) == 0 && mask == (1U<<4));
        CHECK(storage_request_recovery_refence(3) == 0);
        CHECK(storage_request_mutation_fences(301, &mask) == 0 && mask == ((1U<<3)|(1U<<4)));
    }

    for (unsigned effect=0; effect<2; ++effect) {
        CHECK(storage_request_pool_init() == 0 && storage_request_bind_service(40, 8) == 0);
        CHECK(claimed(&handle) == 0);
        CHECK(storage_request_mutation_bind(40, 8, handle, 0, 101) == 0);
        if (effect) CHECK(storage_request_mutation_effect(40, 8, handle, 0, 102) == 0);
        CHECK(storage_request_mutation_finish(40, 8, handle, 0,
              effect ? STORAGE_MUTATION_DURABLE : STORAGE_MUTATION_NO_EFFECT, 103) == 0);
        CHECK(storage_request_complete(40, 8, handle, 0, frame) == 0);
        CHECK(storage_request_mutation_reply_begin(50, 8, handle, 104, &result, output) == -13);
        CHECK(storage_request_mutation_reply_begin(50, 9, handle, 104, &result, output) == 0);
        CHECK(storage_request_recovery_refence(0) == 0);
        CHECK(storage_request_recovery_ready(40, 8, 0) == -16);
        CHECK(storage_request_recovery_clear(40, 8, 0) == -16);
        CHECK(storage_request_mutation_reply_end(50, 9, handle, true, 104) == 0);
        CHECK(storage_request_mutation_reply_ack(50, 8, handle, 105) == -13);
        CHECK(storage_request_mutation_reply_ack(50, 9, handle, 105) == 0);
        CHECK(storage_request_recovery_ready(40, 8, 0) == 0);
        CHECK(storage_request_recovery_clear(40, 8, 0) == 0);
        CHECK(storage_request_mutation_reply_ack(50, 9, handle, 105) < 0);
        storage_request_cancel_process(50, 9);
        CHECK(storage_request_mutation_fences(301, &mask) == 0 && !mask);
    }
    CHECK(storage_request_pool_init() == 0 && storage_request_bind_service(40, 8) == 0);
    CHECK(claimed(&handle) == 0);
    CHECK(storage_request_mutation_bind(40, 8, handle, 31, 101) == 0);
    CHECK(storage_request_cancel(50, 9, handle) == 0); /* Before any effect. */
    CHECK(storage_request_mutation_effect(40, 8, handle, 31, 102) == -125);
    CHECK(storage_request_complete(40, 8, handle, -125, NULL) == 0);
    CHECK(storage_request_mutation_fences(301, &mask) == 0 && !mask);

    /* Output corruption, late copy/ACK, UNKNOWN and request-generation reuse. */
    for (unsigned cut=0; cut<4; ++cut) {
        CHECK(storage_request_pool_init() == 0 && storage_request_bind_service(40, 8) == 0);
        CHECK(claimed(&handle) == 0);
        CHECK(storage_request_mutation_bind(40, 8, handle, 32, 101) == -22);
        CHECK(storage_request_mutation_bind(40, 8, handle, 31, 101) == 0);
        CHECK(storage_request_mutation_effect(40, 8, handle, 31, 102) == 0);
        CHECK(storage_request_mutation_finish(40, 8, handle, 31,
              cut == 3 ? STORAGE_MUTATION_UNKNOWN : STORAGE_MUTATION_DURABLE, 103) == 0);
        CHECK(storage_request_complete(40, 8, handle, 0, frame) == 0);
        if (!cut) {
            CHECK(storage_request_test_corrupt_data(handle, true) == 0);
            CHECK(storage_request_mutation_reply_begin(50, 9, handle, 104, &result, output) == -84);
            CHECK(storage_request_cancel(50, 9, handle) == 0);
        } else {
            CHECK(storage_request_mutation_reply_begin(50, 9, handle, 104, &result, output) == 0);
            CHECK(storage_request_mutation_reply_end(50, 9, handle, true, cut == 1 ? 300 : 104) ==
                (cut == 1 ? -110 : 0));
            if (cut != 1) CHECK(storage_request_mutation_reply_ack(50, 9, handle, cut == 2 ? 300 : 105) ==
                (cut == 2 ? -110 : 0));
        }
        CHECK(storage_request_mutation_fences(0, &mask) == 0 && mask == (1U<<31));
        storage_request_handle_t next;
        CHECK(claimed(&next) == 0 && next != handle);
        CHECK(storage_request_mutation_reply_ack(50, 9, handle, 105) == -22);
        CHECK(storage_request_mutation_bind(40, 8, next, 31, 101) == -5);
        CHECK(storage_request_mutation_bind(40, 8, next, 30, 101) == 0);
        CHECK(storage_request_mutation_authorized(40, 8, next, 30, 102) == 0);
        CHECK(storage_request_cancel(50, 9, next) == 0);
    }
#endif
    printf("R342 receipt checks: %u\n", checks);
    return 0;
}
#elif defined(R342_SYSCALL_TEST)
#include <stdio.h>
#include <string.h>
#include "include/kernel/storage_request_pool.h"
#include "userspace/sdk/include/x86os.h"
enum { PROCESS_DOMAIN_COMPATIBILITY=1, PROCESS_DOMAIN_COMPOSITOR=2,
       PROCESS_DOMAIN_ADMIN=3, PROCESS_DOMAIN_MAINTENANCE=4, SCRIPT=5 };
typedef struct { int pid; uint32_t generation; struct { int kind; } domain_profile; } Process;
typedef int page_directory_t;
static Process process = {50, 9, {PROCESS_DOMAIN_COMPATIBILITY}};
static uint64_t now = 100;
static bool deny_read, deny_write, fail_copyout;
static unsigned copyout_calls, fail_copyout_on;
static storage_request_handle_t cancel_on_copy;
static unsigned checks;
static uintptr_t mapped[3];
static uint8_t bytes[128*1024], output[128*1024], frame[512];
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr, "R342 syscall:%d: %s\n", __LINE__, #x); return 1; } } while (0)
static Process* scheduler_current_process(void) { return &process; }
static page_directory_t* paging_current_directory(void) { return NULL; }
static bool storage_service_authorized(int pid, uint32_t generation) { return pid == 40 && generation == 8; }
static bool storage_service_component_ready(void) { return true; }
static uint64_t pit_monotonic_ms(void) { return now; }
static bool user_range_accessible(page_directory_t* directory, uint32_t address, size_t length, bool write) {
    (void)directory;
    return address && length && !(write ? deny_write : deny_read);
}
static int copy_from_user(void* target, const void* source, size_t length) {
    if (deny_read) return -1;
    memcpy(target, source, length); return 0;
}
static int copy_to_user_space(page_directory_t* directory, uint32_t address, const void* source, size_t length) {
    (void)directory;
    ++copyout_calls;
    if (fail_copyout || deny_write || copyout_calls == fail_copyout_on) return -1;
    for (unsigned i=0; i<3; ++i) if ((uint32_t)mapped[i] == address) {
        memcpy((void*)mapped[i], source, length);
        if (cancel_on_copy) {
            (void)storage_request_cancel(50, 9, cancel_on_copy);
            cancel_on_copy = 0;
        }
        return 0;
    }
    return -1;
}
#include "input_syscalls.inc"
uintptr_t x86os_syscall(uint32_t number, uintptr_t a, uintptr_t b, uintptr_t c) {
    mapped[0]=a; mapped[1]=b; mapped[2]=c;
    if (number == X86OS_SYS_STORAGE_SUBMIT)
        return syscall_storage_submit((const storage_request_submit_t*)a, (const uint8_t*)b,
                                      (storage_request_handle_t*)c);
    if (number == X86OS_SYS_STORAGE_CLAIM_IDENTITY && c == 3)
        return syscall_storage_claim_identity_v3((storage_request_descriptor_v3_t*)a, (uint8_t*)b);
    if (number == X86OS_SYS_STORAGE_BULK)
        return syscall_storage_bulk((storage_request_bulk_control_t*)a, (uint8_t*)b, (uint8_t*)c);
    return (uintptr_t)-22;
}
int main(void) {
    _Static_assert(sizeof(x86os_storage_descriptor_v3_t) == sizeof(storage_request_descriptor_v3_t), "SDK v3");
    _Static_assert(offsetof(x86os_storage_descriptor_v3_t, deadline_ms) == 40, "SDK deadline");
    _Static_assert(X86OS_STORAGE_VFS_OBJECT_MUTATE == STORAGE_REQUEST_VFS_OBJECT_MUTATE, "operation");
    CHECK(storage_request_pool_init() == 0 && storage_request_bind_service(40, 8) == 0);
    x86os_storage_submit_t submit = {1, sizeof(submit), X86OS_STORAGE_VFS_OBJECT_MUTATE, 0, sizeof(bytes), 512, 200};
    storage_request_handle_t handle = 777;
    for (int domain=PROCESS_DOMAIN_COMPOSITOR; domain<=SCRIPT; ++domain) {
        process.domain_profile.kind=domain;
        CHECK((int)x86os_syscall(X86OS_SYS_STORAGE_SUBMIT, (uintptr_t)&submit,
              (uintptr_t)frame, (uintptr_t)&handle) == -13 && handle == 777);
    }
    process.domain_profile.kind=PROCESS_DOMAIN_COMPATIBILITY;
    deny_read=true;
    CHECK((int)x86os_syscall(X86OS_SYS_STORAGE_SUBMIT, (uintptr_t)&submit,
          (uintptr_t)frame, (uintptr_t)&handle) == -14 && handle == 777);
    deny_read=false;
    CHECK((int)x86os_syscall(X86OS_SYS_STORAGE_SUBMIT, (uintptr_t)&submit,
          (uintptr_t)frame, (uintptr_t)&handle) == 0);
    x86os_storage_bulk_control_t malformed = {1, sizeof(malformed),
        X86OS_STORAGE_BULK_INPUT_PUBLISH, handle, sizeof(bytes), 0, 0, 0};
    CHECK((int)x86os_syscall(X86OS_SYS_STORAGE_BULK, (uintptr_t)&malformed, 0, (uintptr_t)bytes) == -22);
    malformed.version=X86OS_STORAGE_BULK_INPUT_VERSION;
    malformed.operation=X86OS_STORAGE_BULK_PUBLISH;
    CHECK((int)x86os_syscall(X86OS_SYS_STORAGE_BULK, (uintptr_t)&malformed, 0, (uintptr_t)bytes) == -22);
    malformed.operation=X86OS_STORAGE_BULK_INPUT_PUBLISH;
    malformed.reserved=1;
    CHECK((int)x86os_syscall(X86OS_SYS_STORAGE_BULK, (uintptr_t)&malformed, 0, (uintptr_t)bytes) == -22);
    malformed.reserved=0; malformed.length=sizeof(bytes)+1;
    CHECK((int)x86os_syscall(X86OS_SYS_STORAGE_BULK, (uintptr_t)&malformed, 0, (uintptr_t)bytes) == -22);
    malformed.length=sizeof(bytes); malformed.struct_size--;
    CHECK((int)x86os_syscall(X86OS_SYS_STORAGE_BULK, (uintptr_t)&malformed, 0, (uintptr_t)bytes) == -22);
    malformed.struct_size++;
    CHECK((int)x86os_syscall(X86OS_SYS_STORAGE_BULK, (uintptr_t)&malformed,
          (uintptr_t)frame, (uintptr_t)bytes) == -22);
    process.generation++;
    CHECK(x86os_storage_input_publish(handle, bytes, sizeof(bytes)) == -13);
    process.generation--;
    process.domain_profile.kind=SCRIPT;
    CHECK(x86os_storage_input_publish(handle, bytes, sizeof(bytes)) == -13);
    process.domain_profile.kind=PROCESS_DOMAIN_COMPATIBILITY;
    memset(bytes, 0x39, sizeof(bytes));
    x86os_storage_descriptor_v3_t descriptor;
    CHECK(x86os_storage_claim_identity_v3(&descriptor, frame) == -13);
    deny_read=true;
    CHECK(x86os_storage_input_publish(handle, bytes, sizeof(bytes)) == -14);
    deny_read=false;
    CHECK(x86os_storage_input_publish(handle, bytes, sizeof(bytes)) == 0);
    process=(Process){40, 8, {0}};
    deny_write=true;
    CHECK(x86os_storage_claim_identity_v3(&descriptor, frame) == -14);
    deny_write=false;
    CHECK(x86os_storage_claim_identity_v3(&descriptor, frame) == 0);
    CHECK(descriptor.deadline_ms == 300 && descriptor.client_pid == 50 && descriptor.client_generation == 9);
    uint32_t taken=777;
    CHECK(x86os_storage_input_publish(handle, bytes, sizeof(bytes)) == -13);
    deny_write=true;
    CHECK(x86os_storage_input_take(handle, output, sizeof(output), &taken) == -14 && !taken);
    deny_write=false;
    CHECK(x86os_storage_input_take(handle, output, sizeof(output), &taken) == 0);
    CHECK(taken == sizeof(bytes) && memcmp(bytes, output, sizeof(bytes)) == 0);
    CHECK(storage_request_cancel(50, 9, handle) == 0);
    CHECK(storage_request_complete(40, 8, handle, -125, NULL) == 0);
    process=(Process){50, 9, {PROCESS_DOMAIN_COMPATIBILITY}};
    fail_copyout=true;
    CHECK((int)x86os_syscall(X86OS_SYS_STORAGE_SUBMIT, (uintptr_t)&submit,
          (uintptr_t)frame, (uintptr_t)&handle) == -14);
    fail_copyout=false;
    storage_request_stats_t stats;
    CHECK(storage_request_stats(&stats) == 0 && stats.active_requests == 0);
    CHECK((int)x86os_syscall(X86OS_SYS_STORAGE_SUBMIT, (uintptr_t)&submit,
          (uintptr_t)frame, (uintptr_t)&handle) == 0);
    CHECK(x86os_storage_input_publish(handle, bytes, sizeof(bytes)) == 0);
    process=(Process){40, 8, {0}};
    fail_copyout=true;
    CHECK(x86os_storage_claim_identity_v3(&descriptor, frame) == -14);
    fail_copyout=false;
    int32_t result;
    process=(Process){50, 9, {PROCESS_DOMAIN_COMPATIBILITY}};
    CHECK(x86os_storage_mutation_collect(handle, &result, frame) == 0 && result == -14);
    CHECK(x86os_storage_mutation_ack(handle) == 0);
    CHECK(storage_request_stats(&stats) == 0 && stats.active_requests == 0);

    /* Actual SDK -> syscall -> pool: both copyout cuts, concurrent cancellation,
     * explicit semantic rejection and successful validation/ACK. */
    for (unsigned cut=0; cut<5; ++cut) {
        CHECK(storage_request_pool_init() == 0 && storage_request_bind_service(40, 8) == 0);
        storage_request_submit_t request = {1, sizeof(request), 35, 0, 0, 512, 200};
        storage_request_descriptor_v3_t claimed;
        CHECK(storage_request_submit(50, 9, &request, frame, now, &handle) == 0);
        CHECK(storage_request_claim_v3(40, 8, now, &claimed, frame) == 0);
        CHECK(storage_request_mutation_bind(40, 8, handle, 2, now) == 0);
        CHECK(storage_request_mutation_effect(40, 8, handle, 2, now) == 0);
        CHECK(storage_request_mutation_finish(40, 8, handle, 2, STORAGE_MUTATION_DURABLE, now) == 0);
        CHECK(storage_request_complete(40, 8, handle, 0, frame) == 0);
        process.domain_profile.kind=SCRIPT;
        CHECK(x86os_storage_mutation_collect(handle, &result, frame) == -13);
        CHECK(x86os_storage_mutation_ack(handle) == -13);
        process.domain_profile.kind=PROCESS_DOMAIN_COMPATIBILITY;
        CHECK(x86os_storage_mutation_ack(handle) == -13); /* Not delivered yet. */
        deny_write=true;
        CHECK(x86os_storage_mutation_collect(handle, &result, frame) == -14);
        deny_write=false;
        uint32_t mask;
        CHECK(storage_request_mutation_fences(now, &mask) == 0 && !mask); /* Prevalidation is retryable collect. */
        copyout_calls=0;
        fail_copyout_on=cut == 1 || cut == 2 ? cut : 0;
        cancel_on_copy=cut == 3 ? handle : 0;
        CHECK(x86os_storage_mutation_collect(handle, &result, frame) ==
            (cut == 1 || cut == 2 ? -14 : cut == 3 ? -125 : 0));
        fail_copyout_on=0;
        if (!cut) CHECK(x86os_storage_mutation_ack(handle) == 0);
        if (cut == 4) CHECK(storage_request_cancel(50, 9, handle) == 0);
        CHECK(storage_request_mutation_fences(now, &mask) == 0 && mask == (cut ? 4U : 0U));
        CHECK(storage_request_stats(&stats) == 0 && stats.active_requests == 0);
    }
    printf("R342 syscall checks: %u\n", checks);
    return 0;
}
#endif
