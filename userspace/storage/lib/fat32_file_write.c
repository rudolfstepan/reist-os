#include "../include/reist/fat32_file_write.h"
#include <stdbool.h>
#include "../../../lib/libc/string.h"

#define FAT_MASK 0x0fffffffU
#define FAT_RESERVED 0x0ffffff0U
#define FAT_EOC 0x0ffffff8U
#define PHASE_FAT 1U
#define PHASE_TREE 2U
#define PHASE_VERIFY 3U
#define PHASE_READY 4U
#define ALLOCATED 0U
#define UNAVAILABLE 1U
#define INCOMING 2U
#define REACHABLE 3U
#define OWNED 4U
#define STEP_YIELD (-11)

static uint32_t get16(const uint8_t* p) { return p[0] | (uint32_t)p[1]<<8; }
static uint32_t get32(const uint8_t* p) { return get16(p) | get16(p+2)<<16; }
static uint32_t entry_cluster(const uint8_t* p) { return get16(p+26) | get16(p+20)<<16; }
static bool same_alias(const uint8_t* a, const uint8_t* b) {
    for (unsigned i = 0; i < 11; ++i) {
        unsigned left = a[i], right = b[i];
        if (left >= 'a' && left <= 'z') left -= 'a'-'A';
        if (right >= 'a' && right <= 'z') right -= 'a'-'A';
        if (left != right) return false;
    }
    return true;
}
static int refuse(reist_fat32_ownership_t* s, int error) {
    if (!s->error) s->error = error;
    s->ready = 0;
    for (unsigned i = 0; i < 3; ++i) s->cache_valid[i] = 0;
    return s->error;
}
static int slot(const reist_fat32_ownership_t* s, uint32_t cluster) {
    if (cluster >= s->first && cluster-s->first < s->count) return (int)(cluster-s->first);
    if (cluster == s->directory_cluster) return REIST_FAT32_OWNERSHIP_CLUSTERS;
    return -1;
}
static bool bit(const reist_fat32_ownership_t* s, unsigned map, unsigned index) {
    return (s->maps[map][index/8] & (1U << (index%8))) != 0;
}
static void mark(reist_fat32_ownership_t* s, unsigned map, unsigned index) {
    s->maps[map][index/8] |= (uint8_t)(1U << (index%8));
}
static bool valid_cluster(const reist_fat32_ownership_t* s, uint32_t cluster) {
    return cluster >= 2 && cluster <= s->view.cluster_count+1;
}
static bool seek_stride_valid(const reist_fat32_ownership_t *s) {
    return s->seek_stride && !(s->seek_stride & (s->seek_stride-1U)) &&
        s->seek_stride <= UINT32_MAX/REIST_FAT32_SEEK_ANCHORS;
}
static int seek_record(reist_fat32_ownership_t *s, uint32_t rank, uint32_t cluster) {
    if (!seek_stride_valid(s) || !valid_cluster(s,cluster) || rank >= s->view.cluster_count) return -22;
    for (unsigned turn=0; turn<32 && (uint64_t)rank >=
            (uint64_t)s->seek_stride*REIST_FAT32_SEEK_ANCHORS; ++turn) {
        if (s->seek_stride > UINT32_MAX/(2U*REIST_FAT32_SEEK_ANCHORS)) return -22;
        for (unsigned i=0;i<REIST_FAT32_SEEK_ANCHORS/2;++i)
            s->seek_anchors[i]=s->seek_anchors[i*2];
        for (unsigned i=REIST_FAT32_SEEK_ANCHORS/2;i<REIST_FAT32_SEEK_ANCHORS;++i)
            s->seek_anchors[i]=0;
        s->seek_stride*=2;
    }
    if ((uint64_t)rank >= (uint64_t)s->seek_stride*REIST_FAT32_SEEK_ANCHORS) return -22;
    if (!(rank%s->seek_stride)) s->seek_anchors[rank/s->seek_stride]=cluster;
    return 0;
}
static int seek_prefix(const reist_fat32_ownership_t *s, uint32_t target,
        uint32_t *cluster, uint32_t *rank) {
    if (!seek_stride_valid(s) || target >= s->chain_count) return -22;
    uint32_t index=target/s->seek_stride;
    if (index >= REIST_FAT32_SEEK_ANCHORS) return -22;
    uint32_t hint=s->seek_anchors[index];
    if (!hint) return 0; /* missing hint does not confer authority */
    if (!valid_cluster(s,hint)) return -5;
    *cluster=hint; *rank=index*s->seek_stride;
    return 0;
}
static int incoming(reist_fat32_ownership_t* s, uint32_t cluster) {
    if (!valid_cluster(s, cluster)) return -5;
    int index = slot(s, cluster);
    if (index >= 0) {
        if (bit(s, INCOMING, (unsigned)index)) return -5;
        mark(s, INCOMING, (unsigned)index);
    }
    return 0;
}
static int sector(reist_fat32_ownership_t* s, const reist_vfs_shadow_io_t* io,
    unsigned cache, uint32_t lba, unsigned* budget) {
    if (lba >= s->view.sectors) return -5;
    if (s->cache_valid[cache] && s->cache_lba[cache] == lba) return 0;
    if (!*budget) return STEP_YIELD;
    --*budget;
    s->cache_valid[cache] = 0;
    int result = io->read_sector(io->context, s->view.object.resource, lba, s->cache[cache]);
    if (result) return result < 0 && result != STEP_YIELD ? result : -5;
    s->cache_valid[cache] = 1;
    s->cache_lba[cache] = lba;
    return 0;
}
static int link_value(reist_fat32_ownership_t* s, const reist_vfs_shadow_io_t* io,
    uint32_t cluster, unsigned* budget, uint32_t* value) {
    if (cluster > s->view.cluster_count+1) return -5;
    unsigned first = s->view.mirrored ? 0 : s->view.active_fat;
    unsigned end = s->view.mirrored ? s->view.fat_count : first+1;
    for (unsigned copy = first; copy < end; ++copy) {
        uint32_t lba = s->view.reserved_sectors + copy*s->view.fat_sectors + cluster/128;
        int result = sector(s, io, copy, lba, budget);
        if (result) return result;
        uint32_t next = get32(s->cache[copy]+(cluster%128)*4) & FAT_MASK;
        if (copy != first && *value != next) return -5;
        *value = next;
    }
    return 0;
}
static int visit(reist_fat32_ownership_t* s, uint32_t cluster, bool owned, uint32_t next) {
    if ((!valid_cluster(s, next) && next < FAT_EOC) || next == cluster) return -5;
    /* A sound tree cannot visit more data clusters than the volume has.
     * This also bounds duplicate directory expansion outside our bit window. */
    if (++s->chain_visits > s->view.cluster_count) return -5;
    int index = slot(s, cluster);
    if (index >= 0) {
        if (!bit(s, ALLOCATED, (unsigned)index) || bit(s, UNAVAILABLE, (unsigned)index) ||
            bit(s, REACHABLE, (unsigned)index)) return -5;
        mark(s, REACHABLE, (unsigned)index);
        if (owned) mark(s, OWNED, (unsigned)index);
    }
    return 0;
}
static int advance(uint32_t next, uint32_t* visited, uint32_t* anchor,
                   uint32_t* power, uint32_t* distance, uint32_t limit) {
    if (*visited >= limit || next == *anchor) return -5;
    ++*visited;
    if (++*distance == *power) {
        *anchor = next; *distance = 0;
        *power = *power <= UINT32_MAX/2 ? *power*2 : UINT32_MAX;
    }
    return 0;
}
static void directory_start(reist_fat32_directory_walk_t* d, uint32_t first, uint32_t parent) {
    memset(d, 0, sizeof(*d));
    d->first = d->cluster = d->anchor = first;
    d->parent = parent; d->visited = d->power = 1;
}

static void window_start(reist_fat32_ownership_t* s, uint32_t first) {
    s->first = first;
    s->count = s->view.cluster_count+2-first;
    if (s->count > REIST_FAT32_OWNERSHIP_CLUSTERS) s->count = REIST_FAT32_OWNERSHIP_CLUSTERS;
    memset(s->maps, 0, sizeof(s->maps));
    memset(s->directories, 0, sizeof(s->directories));
    memset(s->cache_valid, 0, sizeof(s->cache_valid));
    s->fat_index = s->verify_index = s->target_seen = s->depth = s->ready = 0;
    s->chain_visits = s->file_cluster = 0;
    s->chain_count = s->tail_first = 0;
    s->seek_stride=1;
    memset(s->seek_anchors,0,sizeof(s->seek_anchors));
    s->phase = PHASE_FAT;
}

int reist_fat32_ownership_begin(reist_fat32_ownership_t* s,
    const reist_vfs_shadow_io_t* io, const reist_vfs_shadow_object_t* object,
    uint64_t epoch, uint32_t first_cluster) {
    if (!s) return -22;
    memset(s, 0, sizeof(*s));
    if (!epoch) return -22;
    int result = reist_vfs_shadow_fat_view(io, object, &s->view);
    if (result) return refuse(s, result);
    if (!valid_cluster(s, first_cluster)) return refuse(s, -22);
    s->version = REIST_FAT32_OWNERSHIP_VERSION; s->struct_size = sizeof(*s); s->epoch = epoch;
    s->directory_cluster = 2 + (object->locator_a-s->view.data_start)/s->view.sectors_per_cluster;
    window_start(s, first_cluster);
    return 0;
}

int reist_fat32_volume_begin(reist_fat32_ownership_t* s,
    const reist_vfs_shadow_io_t* io, const reist_vfs_shadow_object_t* object, uint64_t epoch) {
    int result = reist_fat32_ownership_begin(s, io, object, epoch, 2);
    if (!result) { s->whole_volume = 1; s->verified_until = 2; s->free_hint = 2; }
    return result;
}

int reist_fat32_recovery_begin(reist_fat32_ownership_t* s,
    const reist_vfs_shadow_io_t* io, uint32_t resource, uint64_t generation) {
    if (!s) return -22;
    memset(s, 0, sizeof(*s));
    if (!generation) return -22;
    int result = reist_vfs_shadow_fat_volume_view(io, resource, &s->view);
    if (result) return refuse(s, result);
    s->version = REIST_FAT32_OWNERSHIP_VERSION; s->struct_size = sizeof(*s); s->epoch = generation;
    s->directory_cluster = s->view.root_cluster;
    s->whole_volume = s->recovery_only = 1; s->verified_until = 2;
    window_start(s, 2);
    return 0;
}

static int fat_step(reist_fat32_ownership_t* s, const reist_vfs_shadow_io_t* io, unsigned* budget) {
    if (s->fat_index == s->view.cluster_count+2) {
        int result = incoming(s, s->view.root_cluster);
        if (result) return result;
        directory_start(&s->directories[0], s->view.root_cluster, 0);
        s->depth = 1; s->phase = PHASE_TREE;
        return 0;
    }
    uint32_t cluster = s->fat_index, next = 0;
    int result = link_value(s, io, cluster, budget, &next);
    if (result) return result;
    if (cluster < 2) {
        /* Reserved entries: dirty/error bits in FAT[1] are not links. */
        if ((!cluster && (next & 0x0fffff00U) != 0x0fffff00U) ||
            (cluster == 1 && (next & 0x03ffffffU) != 0x03ffffffU)) return -5;
    } else {
        if (next && next < FAT_RESERVED && !valid_cluster(s, next)) return -5;
        int index = slot(s, cluster);
        if (index >= 0 && next) mark(s, next < FAT_RESERVED || next >= FAT_EOC ? ALLOCATED : UNAVAILABLE,
                                     (unsigned)index);
        if (next && next < FAT_RESERVED && (result = incoming(s, next)) != 0) return result;
    }
    ++s->fat_index;
    return 0;
}

static int file_step(reist_fat32_ownership_t* s, const reist_vfs_shadow_io_t* io, unsigned* budget) {
    uint32_t next = 0;
    if ((uint64_t)s->file_visited*s->view.sectors_per_cluster*512 > 0x100000000ULL) return -5;
    int result = link_value(s, io, s->file_cluster, budget, &next);
    if (result) return result;
    result = visit(s, s->file_cluster, s->file_owned != 0, next);
    if (result) return result;
    if (s->file_owned) {
        result=seek_record(s,s->file_visited-1,s->file_cluster);
        if (result) return result;
        s->chain_count = s->file_visited;
        s->tail[(s->file_visited-1)%REIST_FAT32_TAIL_CACHE] = s->file_cluster;
        s->tail_first = s->chain_count > REIST_FAT32_TAIL_CACHE ? s->chain_count-REIST_FAT32_TAIL_CACHE : 0;
    }
    if (next >= FAT_EOC) {
        if ((uint64_t)s->file_visited*s->view.sectors_per_cluster*512 < s->file_size) return -5;
        s->file_cluster = 0;
    } else {
        result = advance(next, &s->file_visited, &s->file_anchor, &s->file_power,
                         &s->file_distance, s->view.cluster_count);
        if (result) return result;
        s->file_cluster = next;
    }
    return 0;
}

static int directory_entry(reist_fat32_ownership_t* s, reist_fat32_directory_walk_t* d,
                           const uint8_t* entry, uint32_t lba) {
    uint32_t cluster = entry_cluster(entry), size = get32(entry+28);
    /* Reserved high attribute bits are ignored, not interpreted as new rights. */
    uint32_t attributes = entry[11] & 0x3fU;
    bool dot = !memcmp(entry, ".          ", 11), dotdot = !memcmp(entry, "..         ", 11);
    if (d->first != s->view.root_cluster && d->cluster == d->first && !d->sector && d->entry < 2) {
        if ((attributes & 0x18) != 0x10 || size ||
            (d->entry == 0 ? !dot || cluster != d->first : !dotdot || cluster != d->parent))
            return -5;
        return 0;
    }
    if (!entry[0]) { d->ended = 1; return 0; }
    if (entry[0] == 0xe5) return 0;
    if (dot || dotdot) return -5;
    if (attributes == 0x0f) return get16(entry+26) ? -5 : 0;
    if (attributes & 8) return (attributes & 0x10) || cluster || size || d->first != s->view.root_cluster ? -5 : 0;
    bool target = !s->recovery_only && lba == s->view.object.locator_a && d->entry*32 == s->view.object.locator_b;
    if (!s->recovery_only && same_alias(entry, s->view.entry) && d->target_aliases < 2) ++d->target_aliases;
    if (target) {
        if (memcmp(entry, s->view.entry, 32) || ++s->target_seen != 1 || d->target_aliases != 1) return -116;
        if (s->whole_volume && s->verified_until > 2 && s->target_parent != d->first) return -116;
        s->target_parent = d->first;
    }
    if (s->target_seen && d->first == s->target_parent && d->target_aliases > 1) return -116;
    if (!cluster) return size || (attributes & 0x10) ? -5 : 0;
    if (!valid_cluster(s, cluster)) return -5;
    int result = incoming(s, cluster);
    if (result) return result;
    if (attributes & 0x10) {
        if (size || s->depth == REIST_FAT32_OWNERSHIP_DEPTH) return size ? -5 : -7;
        for (unsigned i = 0; i < s->depth; ++i)
            if (s->directories[i].first == cluster) return -5;
        directory_start(&s->directories[s->depth++], cluster,
            d->first == s->view.root_cluster ? 0 : d->first);
    } else {
        s->file_cluster = s->file_anchor = cluster; s->file_size = size; s->file_owned = target;
        s->file_visited = s->file_power = 1; s->file_distance = 0;
    }
    return 0;
}

static int tree_step(reist_fat32_ownership_t* s, const reist_vfs_shadow_io_t* io, unsigned* budget) {
    if (s->file_cluster) return file_step(s, io, budget);
    if (!s->depth) { s->phase = PHASE_VERIFY; return s->recovery_only || s->target_seen == 1 ? 0 : -116; }
    reist_fat32_directory_walk_t* d = &s->directories[s->depth-1];
    int result;
    if ((uint64_t)d->visited*s->view.sectors_per_cluster*512 > 2097152U) return -5;
    if (!d->entered) {
        result = link_value(s, io, d->cluster, budget, &d->next);
        if (result) return result;
        result = visit(s, d->cluster, false, d->next);
        if (result) return result;
        d->entered = 1;
    }
    if (!d->ended && d->sector < s->view.sectors_per_cluster) {
        uint32_t lba = s->view.data_start + (d->cluster-2)*s->view.sectors_per_cluster + d->sector;
        result = sector(s, io, 2, lba, budget);
        if (result) return result;
        result = directory_entry(s, d, s->cache[2]+d->entry*32, lba);
        if (result) return result;
        if (++d->entry == 16) { d->entry = 0; ++d->sector; }
        return 0;
    }
    if (d->next >= FAT_EOC) { --s->depth; return 0; }
    result = advance(d->next, &d->visited, &d->anchor, &d->power, &d->distance, s->view.cluster_count);
    if (result) return result;
    d->cluster = d->next; d->entered = d->sector = d->entry = 0;
    return 0;
}

static int verify_step(reist_fat32_ownership_t* s) {
    unsigned index = s->verify_index;
    if (index == s->count) {
        if (slot(s, s->directory_cluster) == REIST_FAT32_OWNERSHIP_CLUSTERS)
            index = REIST_FAT32_OWNERSHIP_CLUSTERS;
        else { s->phase = PHASE_READY; s->ready = 1; return 0; }
    } else if (index > s->count) { s->phase = PHASE_READY; s->ready = 1; return 0; }
    bool allocated = bit(s, ALLOCATED, index), reached = bit(s, REACHABLE, index), referred = bit(s, INCOMING, index);
    if (allocated != reached || allocated != referred ||
        (bit(s, UNAVAILABLE, index) && (allocated || reached || referred))) return -5;
    s->verify_index = index+1;
    return 0;
}

int reist_fat32_ownership_step(reist_fat32_ownership_t* s,
    const reist_vfs_shadow_io_t* io, uint64_t epoch) {
    if (!s) return -22;
    if (s->error > 0) s->error = -5;
    if (s->error) return s->error;
    if (!epoch || epoch != s->epoch) return refuse(s, -116);
    if (s->version != REIST_FAT32_OWNERSHIP_VERSION || s->struct_size != sizeof(*s) ||
        s->phase < PHASE_FAT || s->phase > PHASE_READY || s->depth > REIST_FAT32_OWNERSHIP_DEPTH ||
        s->recovery_only > 1 || (s->recovery_only && (!s->whole_volume || s->target_seen || s->file_owned)) ||
        s->whole_volume > 1 || (s->whole_volume && s->verified_until != s->first &&
                              !(s->ready && s->verified_until == s->view.cluster_count+2)))
        return refuse(s, -22);
    reist_vfs_shadow_fat_view_t current;
    int result = s->recovery_only ? reist_vfs_shadow_fat_volume_view(io, s->view.object.resource, &current) :
        reist_vfs_shadow_fat_view(io, &s->view.object, &current);
    if (result) return refuse(s, result);
    if (memcmp(&current, &s->view, sizeof(current))) return refuse(s, -116);
    uint32_t count = valid_cluster(s, s->first) ? current.cluster_count+2-s->first : 0;
    if (count > REIST_FAT32_OWNERSHIP_CLUSTERS) count = REIST_FAT32_OWNERSHIP_CLUSTERS;
    if (!count || s->count != count || s->ready > 1 || s->file_owned > 1 ||
        s->fat_index > current.cluster_count+2U || s->ready != (s->phase == PHASE_READY) ||
        (s->phase != PHASE_FAT && s->fat_index != current.cluster_count+2U) ||
        (s->ready && !s->recovery_only && s->target_seen != 1) ||
        s->directory_cluster != (s->recovery_only ? current.root_cluster :
            2+(current.object.locator_a-current.data_start)/current.sectors_per_cluster) ||
        (s->verify_index > count && s->verify_index != REIST_FAT32_OWNERSHIP_CLUSTERS+1U) ||
        (s->file_cluster && (!valid_cluster(s, s->file_cluster) || !s->file_visited ||
         s->file_visited > current.cluster_count || !s->file_power || s->file_distance >= s->file_power)))
        return refuse(s, -22);
    for (unsigned i = 0; i < 3; ++i)
        if (s->cache_valid[i] > 1) return refuse(s, -22);
    for (unsigned i = 0; i < s->depth; ++i) {
        const reist_fat32_directory_walk_t* d = &s->directories[i];
        if (!valid_cluster(s, d->first) || !valid_cluster(s, d->cluster) || d->entry >= 16 ||
            d->sector > current.sectors_per_cluster || d->entered > 1 || d->ended > 1 || d->target_aliases > 2 ||
            !d->visited || d->visited > current.cluster_count || !d->power || d->distance >= d->power)
            return refuse(s, -22);
    }
    unsigned budget = REIST_VFS_SHADOW_MAX_SECTOR_READS-2;
    for (unsigned work = 0; work < REIST_FAT32_OWNERSHIP_WORK && !s->ready; ++work) {
        result = s->phase == PHASE_FAT ? fat_step(s, io, &budget) :
                 s->phase == PHASE_TREE ? tree_step(s, io, &budget) : verify_step(s);
        if (result == STEP_YIELD) return 1;
        if (result) return refuse(s, result);
    }
    if (s->ready && s->whole_volume) {
        s->verified_until = s->first+s->count;
        if (s->verified_until < s->view.cluster_count+2) {
            window_start(s, s->verified_until);
            return 1;
        }
    }
    return s->ready ? 0 : 1;
}

int reist_fat32_ownership_query(const reist_fat32_ownership_t* s,
    uint64_t epoch, uint32_t cluster, uint32_t* classification) {
    if (!classification) return -22;
    *classification = 0;
    if (!s || !epoch || s->version != REIST_FAT32_OWNERSHIP_VERSION || s->struct_size != sizeof(*s)) return -22;
    if (s->epoch != epoch) return -116;
    if (s->error) return s->error < 0 ? s->error : -5;
    if (s->recovery_only) return -13; /* qualification is not file ownership */
    if (s->first < 2 || !s->count || s->count > REIST_FAT32_OWNERSHIP_CLUSTERS ||
        !valid_cluster(s, s->first) || s->count > s->view.cluster_count+2-s->first ||
        !valid_cluster(s, cluster)) return -22;
    if (s->ready != 1 || s->phase != PHASE_READY) return -11;
    int index = slot(s, cluster);
    if (index < 0) return -11;
    *classification = bit(s, OWNED, (unsigned)index) ? REIST_FAT32_CLUSTER_FILE :
        cluster == s->directory_cluster ? REIST_FAT32_CLUSTER_DIRECTORY :
        bit(s, ALLOCATED, (unsigned)index) || bit(s, UNAVAILABLE, (unsigned)index) ?
            REIST_FAT32_CLUSTER_OTHER : REIST_FAT32_CLUSTER_FREE;
    return 0;
}

static int overwrite_error(reist_fat32_overwrite_t* w, int error) {
    if (!w->error) w->error = error < 0 ? error : -REIST_EIO;
    if (w->transaction && w->transaction->active && w->transaction->token == w->token &&
        !w->transaction->error) w->transaction->error = w->error;
    if (w->proof && w->proof->epoch == w->admission.base.epoch) refuse(w->proof, w->error);
    w->ready = 0;
    return w->error;
}

static int overwrite_info(void* context, uint32_t resource, x86os_drive_info_t* info) {
    const reist_fat32_overwrite_t* w = context;
    if (resource != w->proof->view.object.resource) return 0;
    memset(info, 0, sizeof(*info));
    info->type = X86OS_DRIVE_PARTITION; info->sectors = w->transaction->sectors;
    return 1;
}
static int overwrite_read(void* context, uint32_t resource, uint32_t lba, uint8_t* bytes) {
    reist_fat32_overwrite_t* w = context;
    if (resource != w->proof->view.object.resource || lba >= w->transaction->sectors) return -REIST_EINVAL;
    /* Parser addresses are volume-relative; add the admitted extent exactly once. */
    return reist_fat32_transaction_read_media(w->transaction, w->transaction->first+lba, bytes);
}
static int overwrite_identity(reist_fat32_overwrite_t* w) {
    reist_fat32_transaction_t* tx = w->transaction;
    if (!tx->active || !tx->owned || tx->token != w->token ||
        memcmp(&tx->admission, &w->admission, sizeof(w->admission))) return -REIST_ESTALE;
    if (tx->error) return tx->error;
    if (w->proof->epoch != w->admission.base.epoch) return -REIST_ESTALE;
    reist_vfs_shadow_io_t io = {w, overwrite_info, overwrite_read};
    /* READY checks BPB and all32 entry bytes through live token IO. The kernel
     * binds every transfer to the same pin/request/owners/original deadline. */
    int result = reist_fat32_ownership_step(w->proof, &io, w->admission.base.epoch);
    return result > 0 ? -REIST_EACCES : result;
}

int reist_fat32_overwrite_begin(reist_fat32_overwrite_t* w,
    reist_fat32_ownership_t* proof, reist_fat32_transaction_t* tx,
    uint64_t offset, const void* input, uint32_t length) {
    if (!w || !proof || !tx) return -REIST_EINVAL;
    if (w->active) return -REIST_EBUSY;
    memset(w, 0, sizeof(*w));
    w->version = REIST_FAT32_OVERWRITE_VERSION;
    w->proof = proof; w->transaction = tx; w->token = tx->token; w->admission = tx->admission;
    if (!tx->active || !tx->owned || !tx->token) return overwrite_error(w, -REIST_EACCES);
    if (tx->error) return overwrite_error(w, tx->error);
    if (!tx->journal.enabled || tx->journal.transaction_depth != 1 || tx->journal.entry_count ||
        tx->attempted || tx->committing) return overwrite_error(w, -REIST_EBUSY);
    if (proof->version != REIST_FAT32_OWNERSHIP_VERSION || proof->struct_size != sizeof(*proof) ||
        proof->ready != 1 || proof->phase != PHASE_READY || proof->error || proof->recovery_only ||
        proof->whole_volume != 1 || proof->verified_until != proof->view.cluster_count+2)
        return overwrite_error(w, -REIST_EACCES);
    if (!proof->epoch || proof->epoch != w->admission.base.epoch || proof->epoch > UINT64_MAX-2)
        return overwrite_error(w, -REIST_ESTALE);
    const reist_file_object_key_t* key = &w->admission.base.keys[0];
    if (key->kind != REIST_FILE_OBJECT_FAT32 || key->resource != proof->view.object.resource ||
        key->object_a != proof->target_parent || key->object_b || key->reserved || key->alias[11] ||
        memcmp(key->alias, proof->view.entry, 11) || tx->resource != key->resource ||
        tx->sectors != proof->view.sectors || tx->journal.data_lba != tx->first+ATA_JOURNAL_DATA_OFFSET ||
        proof->view.reserved_sectors != tx->reserved ||
        tx->journal.volume_start_lba != tx->first || tx->journal.volume_end_lba != tx->first+tx->sectors ||
        tx->journal.header_lba != tx->first+ATA_JOURNAL_HEADER_OFFSET)
        return overwrite_error(w, -REIST_EACCES);
    if (proof->view.entry[11] & 1) return overwrite_error(w, -REIST_EROFS);
    if ((length && !input) || length > 128U*1024) return overwrite_error(w, -REIST_EINVAL);
    if (offset > UINT32_MAX || length > UINT32_MAX-offset) return overwrite_error(w, -REIST_EOVERFLOW);
    if (length && (offset > proof->view.file_size || length > proof->view.file_size-offset))
        return overwrite_error(w, -REIST_ENOTSUP); /* growth is not disguised as a partial overwrite */
    /* Validate actual geometry before using any cached divisor or locator. */
    if (!seek_stride_valid(proof)) return overwrite_error(w, -REIST_EINVAL);
    memset(proof->cache_valid, 0, sizeof(proof->cache_valid));
    int result = overwrite_identity(w);
    if (result) return overwrite_error(w, result);
    w->offset = (uint32_t)offset; w->input = input; w->bytes = length;
    uint32_t capacity = ATA_JOURNAL_MAX_ENTRIES*512U-(w->offset%512);
    if (w->bytes > capacity) w->bytes = capacity;
    w->cluster = proof->view.object.locator_c;
    uint32_t target_rank = w->offset/(proof->view.sectors_per_cluster*512U);
    if (proof->seek_cluster && (!valid_cluster(proof, proof->seek_cluster) ||
        proof->seek_rank >= proof->view.cluster_count)) return overwrite_error(w, -REIST_EINVAL);
    if (proof->seek_cluster && proof->seek_rank <= target_rank) {
        w->cluster = proof->seek_cluster; w->rank = proof->seek_rank;
    }
    w->anchor = w->cluster; w->power = 1;
    w->active = 1;
    return 0;
}

int reist_fat32_overwrite_step(reist_fat32_overwrite_t* w) {
    if (!w || w->version != REIST_FAT32_OVERWRITE_VERSION || !w->active) return -REIST_ESTALE;
    if (w->error) return w->error;
    int result = overwrite_identity(w);
    if (result) return overwrite_error(w, result);
    if (w->target_count > ATA_JOURNAL_MAX_ENTRIES || w->mapped > w->bytes ||
        w->bytes > ATA_JOURNAL_MAX_ENTRIES*512U-w->offset%512 ||
        !w->power || w->distance >= w->power) return overwrite_error(w, -REIST_EINVAL);
    if (w->ready) return 0;
    reist_fat32_ownership_t* proof = w->proof;
    reist_vfs_shadow_io_t io = {w, overwrite_info, overwrite_read};
    unsigned budget = 256;
    uint32_t cluster_bytes = proof->view.sectors_per_cluster*512U;
    for (unsigned work = 0; w->mapped < w->bytes && work < 128; ++work) {
        uint32_t position = w->offset+w->mapped, target_rank = position/cluster_bytes, next = 0;
        if (!valid_cluster(proof, w->cluster) || w->rank > target_rank || w->rank >= proof->view.cluster_count)
            return overwrite_error(w, -REIST_EIO);
        result = link_value(proof, &io, w->cluster, &budget, &next);
        if (result == STEP_YIELD) return 1;
        if (result) return overwrite_error(w, result);
        if ((!valid_cluster(proof, next) && next < FAT_EOC) || next == w->cluster)
            return overwrite_error(w, -REIST_EIO);
        if (w->rank < target_rank) {
            if (!valid_cluster(proof, next) || next == w->anchor) return overwrite_error(w, -REIST_EIO);
            if (++w->distance == w->power) {
                w->anchor = next; w->distance = 0;
                w->power = w->power <= UINT32_MAX/2 ? w->power*2 : UINT32_MAX;
            }
            w->cluster = next; ++w->rank;
            continue;
        }
        uint32_t lba = proof->view.data_start+(w->cluster-2)*proof->view.sectors_per_cluster+
            (position%cluster_bytes)/512;
        if (lba < proof->view.data_start || lba >= proof->view.sectors || lba == proof->view.object.locator_a ||
            w->target_count >= ATA_JOURNAL_MAX_ENTRIES) return overwrite_error(w, -REIST_EIO);
        for (unsigned i = 0; i < w->target_count; ++i)
            if (w->targets[i] == lba) return overwrite_error(w, -REIST_EIO);
        w->targets[w->target_count++] = lba;
        uint32_t amount = 512-position%512;
        if (amount > w->bytes-w->mapped) amount = w->bytes-w->mapped;
        w->mapped += amount;
    }
    if (w->mapped < w->bytes) return 1;
    /* The complete range and exact unique target count are known before stage.
     * Staging only buffers before/after images in the existing20-entry core. */
    uint32_t copied = 0;
    for (unsigned i = 0; i < w->target_count; ++i) {
        uint32_t start = (w->offset+copied)%512, amount = 512-start;
        if (amount > w->bytes-copied) amount = w->bytes-copied;
        /* A complete replacement has no retained bytes to read here. The
         * unchanged journal still reads and checks the real before-image
         * during stage; partial sectors keep their live preservation read. */
        if (start || amount != 512U) {
            result = overwrite_read(w, proof->view.object.resource, w->targets[i], w->sector);
            if (result) return overwrite_error(w, result);
        }
        memcpy(w->sector+start, w->input+copied, amount);
        result = reist_fat32_transaction_stage(w->transaction, w->transaction->first+w->targets[i], w->sector);
        if (result) return overwrite_error(w, result);
        copied += amount;
    }
    w->ready = 1;
    return 0;
}

static bool overwrite_plan_valid(const reist_fat32_overwrite_t* w) {
    const ata_undo_journal_t* journal = &w->transaction->journal;
    if (!journal->enabled || journal->transaction_depth != 1 ||
        w->target_count > ATA_JOURNAL_MAX_ENTRIES || journal->entry_count != w->target_count ||
        w->mapped != w->bytes || w->bytes > ATA_JOURNAL_MAX_ENTRIES*512U-w->offset%512) return false;
    uint32_t copied = 0;
    for (unsigned i = 0; i < w->target_count; ++i) {
        if (journal->entries[i].target_lba != w->transaction->first+w->targets[i] || copied >= w->bytes)
            return false;
        uint32_t start = (w->offset+copied)%512, amount = 512-start;
        if (amount > w->bytes-copied) amount = w->bytes-copied;
        if (memcmp(journal->pending_data[i], journal->undo_data[i], start) ||
            memcmp(journal->pending_data[i]+start, w->input+copied, amount) ||
            memcmp(journal->pending_data[i]+start+amount, journal->undo_data[i]+start+amount, 512-start-amount))
            return false;
        copied += amount;
    }
    return copied == w->bytes;
}

static int owned_finish(reist_fat32_overwrite_t* w, bool commit,
    uint32_t* outcome, uint32_t* durable_bytes) {
    if (!outcome || !durable_bytes) return -REIST_EINVAL;
    *outcome = REIST_FILE_OBJECT_NO_EFFECT; *durable_bytes = 0;
    if (!w || w->version != REIST_FAT32_OVERWRITE_VERSION || !w->active) return -REIST_ESTALE;
    reist_fat32_transaction_t* tx = w->transaction;
    if (!tx->active || tx->token != w->token || memcmp(&tx->admission, &w->admission, sizeof(w->admission))) {
        *outcome = REIST_FILE_OBJECT_UNKNOWN;
        w->active = 0;
        return overwrite_error(w, -REIST_ESTALE); /* never finish a successor */
    }
    int result = reist_fat32_transaction_finish(tx, commit && !w->error, outcome);
    w->active = 0;
    if (!result && commit && !w->error && *outcome == REIST_FILE_OBJECT_DURABLE_COMMIT) {
        *durable_bytes = w->bytes;
        reist_file_object_guard_request_t snapshot = {0};
        snapshot.version = REIST_FILE_OBJECT_VERSION; snapshot.struct_size = sizeof(snapshot);
        snapshot.operation = REIST_FILE_OBJECT_SNAPSHOT;
        /* BEGIN and END each advance exactly once. Other mutations, expiry,
         * replacement and fences invalidate reuse, but not proven durability. */
        int check = tx->io.guard(tx->io.context, &snapshot);
        if (!check) {
            reist_file_object_guard_request_t verify = {0};
            verify.version = REIST_FILE_OBJECT_VERSION; verify.struct_size = sizeof(verify);
            verify.operation = REIST_FILE_OBJECT_VERIFY; verify.token = w->admission.pin;
            verify.client_pid = w->admission.base.client_pid;
            verify.client_generation = w->admission.base.client_generation;
            check = tx->io.guard(tx->io.context, &verify);
        }
        if (!check && snapshot.epoch == w->admission.base.epoch+2 &&
            w->proof->epoch == w->admission.base.epoch && !w->proof->error) {
            w->proof->epoch = snapshot.epoch;
            w->proof->seek_cluster = w->cluster; w->proof->seek_rank = w->rank;
            memset(w->proof->cache_valid, 0, sizeof(w->proof->cache_valid));
        } else refuse(w->proof, check ? check : -REIST_ESTALE);
    } else refuse(w->proof, result ? result : -REIST_ESTALE);
    return result ? result : w->error;
}

int reist_fat32_overwrite_finish(reist_fat32_overwrite_t* w, bool commit,
    uint32_t* outcome, uint32_t* durable_bytes) {
    if (!outcome || !durable_bytes) return -REIST_EINVAL;
    if (w && w->version == REIST_FAT32_OVERWRITE_VERSION && w->active && commit && !w->error) {
        int result = w->ready && overwrite_plan_valid(w) ? overwrite_identity(w) : -REIST_EINVAL;
        if (result) overwrite_error(w, result);
    }
    return owned_finish(w, commit, outcome, durable_bytes);
}

static void put32(uint8_t* p, uint32_t value) {
    for (unsigned i = 0; i < 4; ++i) p[i] = (uint8_t)(value>>(8*i));
}
/* FAT32 sizes have already been range-checked to uint32. Divide before
 * rounding: UINT32_MAX remains valid without overflow or a uint64 divide. */
static uint32_t file_cluster_count(uint32_t bytes, uint32_t cluster_bytes) {
    return bytes/cluster_bytes + (bytes%cluster_bytes != 0U);
}
static bool add_target(uint32_t* targets, uint32_t* count, uint32_t lba) {
    for (unsigned i = 0; i < *count; ++i) if (targets[i] == lba) return true;
    if (*count == ATA_JOURNAL_MAX_ENTRIES) return false;
    targets[(*count)++] = lba;
    return true;
}
static uint32_t shrink_cluster(const reist_fat32_shrink_t* s, uint32_t rank) {
    return s->tail[rank%REIST_FAT32_SHRINK_WINDOW];
}
static bool file_fat_targets(const reist_vfs_shadow_fat_view_t* v, uint32_t cluster,
    uint32_t* targets, uint32_t* count) {
    unsigned first = v->mirrored ? 0 : v->active_fat;
    unsigned end = v->mirrored ? v->fat_count : first+1;
    for (unsigned copy = first; copy < end; ++copy)
        if (!add_target(targets, count, v->reserved_sectors+copy*v->fat_sectors+cluster/128)) return false;
    return true;
}

static int file_fsinfo(reist_fat32_overwrite_t* w, uint32_t* sectors, uint32_t* count) {
    const reist_vfs_shadow_fat_view_t* v = &w->proof->view;
    uint32_t primary = v->fsinfo_sector, backup = v->backup_sector;
    *count = 0;
    /* FSInfo is a hint, never allocation authority. Valid hints become unknown
     * with allocation changes in the SAME journal; invalid hints stay untouched. */
    if (!primary || primary == 0xffffU) return 0;
    uint32_t candidates[2] = {primary, 0};
    if (backup && backup != 0xffffU) candidates[1] = backup+primary;
    for (unsigned i = 0; i < 2; ++i) {
        uint32_t lba = candidates[i];
        if (!lba) continue;
        if (lba >= v->reserved_sectors || lba == backup ||
            (lba >= ATA_JOURNAL_HEADER_OFFSET && lba < ATA_JOURNAL_DATA_OFFSET+ATA_JOURNAL_MAX_ENTRIES) ||
            (w->transaction->journal.mirror_lba && w->transaction->first+lba == w->transaction->journal.mirror_lba))
            return -REIST_EIO;
        int result = overwrite_read(w, v->object.resource, lba, w->sector);
        if (result) return result;
        if (get32(w->sector) == 0x41615252U && get32(w->sector+484) == 0x61417272U &&
            get32(w->sector+508) == 0xaa550000U &&
            (get32(w->sector+488)!=UINT32_MAX || get32(w->sector+492)!=UINT32_MAX))
            sectors[(*count)++] = lba;
    }
    return 0;
}

int reist_fat32_shrink_begin(reist_fat32_shrink_t* s,
    reist_fat32_ownership_t* p, reist_fat32_transaction_t* tx, uint64_t target) {
    if (!s || !p || !tx) return -REIST_EINVAL;
    if (s->owner.active) return -REIST_EBUSY;
    memset(s, 0, sizeof(*s));
    int result = reist_fat32_overwrite_begin(&s->owner, p, tx, 0, NULL, 0);
    if (result) return result;
    s->version = REIST_FAT32_SHRINK_VERSION;
    if (target > UINT32_MAX) return overwrite_error(&s->owner, -REIST_EOVERFLOW);
    if (target > p->view.file_size) return overwrite_error(&s->owner, -REIST_ENOTSUP);
    uint64_t capacity = (uint64_t)p->chain_count*p->view.sectors_per_cluster*512;
    if (p->chain_count > p->view.cluster_count || p->tail_first > p->chain_count ||
        p->chain_count-p->tail_first > REIST_FAT32_TAIL_CACHE || capacity > 0x100000000ULL ||
        capacity < p->view.file_size || (!p->chain_count != !p->view.object.locator_c))
        return overwrite_error(&s->owner, -REIST_EINVAL);
    s->target = (uint32_t)target; s->count = p->chain_count; s->first = p->tail_first;
    for (uint32_t rank = s->first; rank < s->count; ++rank)
        s->tail[rank%REIST_FAT32_SHRINK_WINDOW] = p->tail[rank%REIST_FAT32_TAIL_CACHE];
    s->resulting_size = p->view.file_size; s->resulting_view = p->view;
    s->phase = 1;
    uint32_t cluster_bytes = p->view.sectors_per_cluster*512U;
    uint32_t keep = file_cluster_count(s->target, cluster_bytes);
    if (target == p->view.file_size && keep == s->count) { s->owner.ready = 1; return 0; }
    add_target(s->owner.targets, &s->owner.target_count, p->view.object.locator_a);
    if (keep < s->count) {
        result = file_fsinfo(&s->owner, s->fsinfo, &s->fsinfo_count);
        if (result) return overwrite_error(&s->owner, result);
        for (unsigned i = 0; i < s->fsinfo_count; ++i)
            add_target(s->owner.targets, &s->owner.target_count, s->fsinfo[i]);
    }
    return 0;
}

/* Build the full after-image from immutable undo bytes and the exact suffix
 * plan. Used both for staging and before commit; extra/altered pending bytes
 * cannot acquire publication authority. Never modifies a high FAT nibble. */
static int shrink_image(const reist_fat32_shrink_t* s, uint32_t lba, uint8_t* bytes) {
    const reist_vfs_shadow_fat_view_t* v = &s->owner.proof->view;
    if (lba == v->object.locator_a) {
        if (memcmp(bytes+v->object.locator_b, v->entry, 32)) return -REIST_ESTALE;
        memcpy(bytes+v->object.locator_b, s->resulting_view.entry, 32);
        return 0;
    }
    for (unsigned i = 0; i < s->fsinfo_count; ++i) if (lba == s->fsinfo[i]) {
        if (get32(bytes) != 0x41615252U || get32(bytes+484) != 0x61417272U ||
            get32(bytes+508) != 0xaa550000U) return -REIST_EIO;
        put32(bytes+488, UINT32_MAX); put32(bytes+492, UINT32_MAX);
        return 0;
    }
    if (lba < v->reserved_sectors || lba >= v->data_start) return -REIST_EIO;
    uint32_t copy = (lba-v->reserved_sectors)/v->fat_sectors;
    if (copy >= v->fat_count || (!v->mirrored && copy != v->active_fat)) return -REIST_EIO;
    uint32_t base = ((lba-v->reserved_sectors)%v->fat_sectors)*128;
    uint32_t retained = s->count-s->released;
    bool changed = false;
    for (uint32_t rank = retained ? retained-1 : 0; rank < s->count; ++rank) {
        uint32_t cluster = shrink_cluster(s, rank);
        if (cluster < base || cluster-base >= 128) continue;
        uint8_t* entry = bytes+(cluster-base)*4;
        uint32_t next = get32(entry)&FAT_MASK;
        if (rank+1 == s->count ? (s->terminal_value<FAT_EOC || s->terminal_value>FAT_MASK ||
                next!=s->terminal_value) : next != shrink_cluster(s, rank+1)) return -REIST_EIO;
        put32(entry, (get32(entry)&~FAT_MASK) | (rank < retained ? FAT_MASK : 0));
        changed = true;
    }
    return changed ? 0 : -REIST_EIO;
}

static int shrink_stage_image(void* context, uint32_t lba, uint8_t* bytes) {
    reist_fat32_shrink_t* s=context;
    const reist_vfs_shadow_fat_view_t* v=&s->owner.proof->view;
    uint32_t relative=lba-s->owner.transaction->first;
    /* Capture the exact terminal from the first selected FAT copy's fresh
     * undo image; every other copy and the final plan must agree. No extra
     * pre-read (or assumed canonical EOC encoding) is required. */
    if(s->released && relative>=v->reserved_sectors && relative<v->data_start) {
        uint32_t cluster=shrink_cluster(s,s->count-1);
        if((relative-v->reserved_sectors)%v->fat_sectors==cluster/128 && !s->terminal_value) {
            s->terminal_value=get32(bytes+(cluster%128)*4)&FAT_MASK;
            if(s->terminal_value<FAT_EOC) return -REIST_EIO;
        }
    }
    return shrink_image(s,relative,bytes);
}

static int shrink_stage(reist_fat32_shrink_t* s) {
    reist_fat32_overwrite_t* w = &s->owner;
    uint32_t retained = s->count-s->released;
    uint64_t capacity = (uint64_t)retained*w->proof->view.sectors_per_cluster*512;
    s->resulting_size = capacity < w->proof->view.file_size ? (uint32_t)capacity : w->proof->view.file_size;
    if (file_cluster_count(s->target, w->proof->view.sectors_per_cluster*512U) == retained)
        s->resulting_size = s->target;
    int result = reist_vfs_shadow_fat_shrink_view(&w->proof->view, s->resulting_size,
        retained ? w->proof->view.object.locator_c : 0, &s->resulting_view);
    if (result) return result;
    /* Order only the complete in-RAM plan, before undo/ACTIVE publication.
     * The unchanged journal can then batch adjacent FAT sectors and mirrors.
     * Never sort a live journal or change its20-slot/four-barrier protocol. */
    for (unsigned i = 1; i < w->target_count; ++i) {
        uint32_t lba = w->targets[i];
        unsigned j = i;
        while (j && w->targets[j-1] > lba) {
            w->targets[j] = w->targets[j-1]; --j;
        }
        w->targets[j] = lba;
    }
    uint32_t targets[ATA_JOURNAL_MAX_ENTRIES];
    for (unsigned i=0; i<w->target_count; ++i) targets[i]=w->transaction->first+w->targets[i];
    if (w->target_count) {
        result=reist_fat32_transaction_stage_images(w->transaction,targets,w->target_count,shrink_stage_image,s);
        if (result) return result;
    }
    w->ready = 1;
    return 0;
}

static int shrink_scan_link(reist_fat32_shrink_t* s,uint32_t cluster,unsigned* budget,uint32_t* value) {
    const reist_vfs_shadow_fat_view_t* v=&s->owner.proof->view;
    if (!valid_cluster(s->owner.proof,cluster) || cluster/128>=v->fat_sectors) return -REIST_EIO;
    unsigned first=v->mirrored ? 0 : v->active_fat;
    unsigned end=v->mirrored ? v->fat_count : first+1;
    if (end>2 || first>=end) return -REIST_EIO;
    for(unsigned copy=first;copy<end;++copy) {
        uint32_t start=v->reserved_sectors+copy*v->fat_sectors;
        uint32_t lba=start+cluster/128;
        if(s->read_count[copy]>REIST_FAT32_SHRINK_READ_AHEAD ||
            (s->read_count[copy] && (s->read_first[copy]<start ||
                s->read_first[copy]-start>=v->fat_sectors ||
                s->read_count[copy]>v->fat_sectors-(s->read_first[copy]-start)))) return -REIST_EIO;
        if(!s->read_count[copy] || lba<s->read_first[copy] || lba-s->read_first[copy]>=s->read_count[copy]) {
            uint32_t count=v->fat_sectors-cluster/128;
            if(count>REIST_FAT32_SHRINK_READ_AHEAD) count=REIST_FAT32_SHRINK_READ_AHEAD;
            if(*budget<count) return STEP_YIELD;
            *budget-=count; s->read_count[copy]=0;
            int result=reist_fat32_transaction_read_media_many(s->owner.transaction,
                s->owner.transaction->first+lba,count,s->read_ahead[copy]);
            if(result) return result;
            s->read_first[copy]=lba; s->read_count[copy]=count;
        }
        uint32_t next=get32(s->read_ahead[copy][lba-s->read_first[copy]]+(cluster%128)*4)&FAT_MASK;
        if(copy!=first && next!=*value) return -REIST_EIO;
        *value=next;
    }
    return 0;
}

int reist_fat32_shrink_step(reist_fat32_shrink_t* s) {
    if (!s || s->version != REIST_FAT32_SHRINK_VERSION || !s->owner.active) return -REIST_ESTALE;
    reist_fat32_overwrite_t* w = &s->owner;
    if (w->error) return w->error;
    int result = overwrite_identity(w);
    if (result) return overwrite_error(w, result);
    if (s->count != w->proof->chain_count || s->first > s->count ||
        s->count-s->first > REIST_FAT32_SHRINK_WINDOW || s->released > s->count ||
        s->released >= REIST_FAT32_SHRINK_WINDOW || s->phase < 1 || s->phase > 2 ||
        w->target_count > ATA_JOURNAL_MAX_ENTRIES || s->fsinfo_count > 2)
        return overwrite_error(w, -REIST_EINVAL);
    if (w->ready) return 0;
    reist_fat32_ownership_t* p = w->proof;
    uint32_t cb = p->view.sectors_per_cluster*512U;
    uint32_t keep = file_cluster_count(s->target, cb);
    unsigned budget = 256;
    bool complete = false;
    for (unsigned work = 0; work < 128; ++work) {
        if (s->phase == 2) {
            if (!valid_cluster(p, s->scan_cluster) || s->scan_rank > s->scan_end ||
                !s->power || s->distance >= s->power) return overwrite_error(w, -REIST_EIO);
            if (s->scan_rank == s->scan_end) {
                if (s->scan_cluster != shrink_cluster(s, s->scan_end)) return overwrite_error(w, -REIST_EIO);
                s->first = s->scan_first; s->phase = 1;
                continue;
            }
            uint32_t next = 0;
            result = shrink_scan_link(s, s->scan_cluster, &budget, &next);
            if (result == STEP_YIELD) return 1;
            if (result) return overwrite_error(w, result);
            if (!valid_cluster(p, next) || next == s->anchor) return overwrite_error(w, -REIST_EIO);
            if (s->scan_rank >= s->scan_first)
                s->tail[s->scan_rank%REIST_FAT32_SHRINK_WINDOW] = s->scan_cluster;
            if (++s->distance == s->power) { s->anchor = next; s->distance = 0; s->power *= 2; }
            s->scan_cluster = next; ++s->scan_rank;
            continue;
        }
        uint32_t retained = s->count-s->released;
        if (retained == keep) { complete = true; break; }
        if (retained < keep || !retained) return overwrite_error(w, -REIST_EIO);
        uint32_t rank = retained-1, predecessor = rank ? rank-1 : 0;
        if (predecessor < s->first) {
            /* Refill what the retained cache can use, not the full worst-case
             * contiguous plan every time. A dense plan can extend again in a
             * later bounded turn; fragmented plans do not discard1500+ links
             * immediately after their next small commit. */
            uint32_t first = s->first > REIST_FAT32_TAIL_CACHE ? s->first-REIST_FAT32_TAIL_CACHE : 0;
            uint32_t floor = s->count > REIST_FAT32_SHRINK_WINDOW ? s->count-REIST_FAT32_SHRINK_WINDOW : 0;
            if (first<floor) first=floor;
            if (first >= s->first) return overwrite_error(w, -REIST_EIO);
            s->scan_first = first; s->scan_end = s->first;
            s->scan_cluster = p->view.object.locator_c; s->scan_rank = 0;
            result=seek_prefix(p,first,&s->scan_cluster,&s->scan_rank);
            if (result) return overwrite_error(w,result);
            if (p->seek_cluster && p->seek_rank <= first && p->seek_rank > s->scan_rank) {
                s->scan_cluster = p->seek_cluster; s->scan_rank = p->seek_rank;
            }
            s->anchor = s->scan_cluster; s->power = 1; s->distance = 0; s->phase = 2;
            continue;
        }
        uint32_t targets[ATA_JOURNAL_MAX_ENTRIES], count = w->target_count;
        memcpy(targets, w->targets, sizeof(targets));
        bool fits = true;
        for (uint32_t check = predecessor; check <= rank; ++check) {
            uint32_t cluster = shrink_cluster(s, check);
            if (!valid_cluster(p, cluster)) return overwrite_error(w, -REIST_EIO);
            if (!file_fat_targets(&p->view, cluster, targets, &count)) { fits = false; break; }
        }
        if (!fits) { complete = true; break; }
        /* Select the exact manifest from the pin/epoch-bound suffix, without
         * rereading individual FAT entries here. shrink_image validates EVERY
         * predecessor/released link in EVERY selected FAT copy against the
         * freshly bulk-read immutable undo bytes, before any commit. It also
         * captures and compares the exact terminal value in both copies. The full
         * projected plan is checked again in shrink_plan_valid at finish. */
        memcpy(w->targets, targets, sizeof(targets)); w->target_count = count;
        ++s->released;
        if (work == 127) return 1;
    }
    if (!complete) return 1;
    /* A full step must make visible size or explicit allocation progress. */
    if (!s->released && keep < s->count) return overwrite_error(w, -REIST_EIO);
    result = shrink_stage(s);
    return result ? overwrite_error(w, result) : 0;
}

static bool shrink_plan_valid(reist_fat32_shrink_t* s) {
    reist_fat32_overwrite_t* w = &s->owner;
    const ata_undo_journal_t* journal = &w->transaction->journal;
    if (!w->ready || !journal->enabled || journal->transaction_depth != 1 ||
        w->target_count > ATA_JOURNAL_MAX_ENTRIES || journal->entry_count != w->target_count ||
        s->count != w->proof->chain_count || s->first > s->count ||
        s->count-s->first > REIST_FAT32_SHRINK_WINDOW ||
        s->released > s->count || s->released >= REIST_FAT32_SHRINK_WINDOW || s->fsinfo_count > 2 ||
        s->resulting_size > w->proof->view.file_size || s->resulting_size < s->target) return false;
    uint32_t retained = s->count-s->released;
    if (s->released && retained && retained-1 < s->first) return false;
    uint64_t cb = (uint64_t)w->proof->view.sectors_per_cluster*512;
    uint32_t keep = file_cluster_count(s->target, (uint32_t)cb);
    if (retained < keep) return false;
    uint64_t expected_size = retained*cb;
    if (expected_size > w->proof->view.file_size) expected_size = w->proof->view.file_size;
    if (retained == keep) expected_size = s->target;
    reist_vfs_shadow_fat_view_t expected_view;
    if (expected_size != s->resulting_size || reist_vfs_shadow_fat_shrink_view(&w->proof->view,
        (uint32_t)expected_size, retained ? w->proof->view.object.locator_c : 0, &expected_view) ||
        memcmp(&expected_view, &s->resulting_view, sizeof(expected_view))) return false;
    uint32_t targets[ATA_JOURNAL_MAX_ENTRIES], count = 0;
    if (s->released || s->target != w->proof->view.file_size) {
        if (!add_target(targets, &count, w->proof->view.object.locator_a)) return false;
        for (unsigned i = 0; i < s->fsinfo_count; ++i)
            if (!s->released || !add_target(targets, &count, s->fsinfo[i])) return false;
        if (s->released) for (uint32_t rank = retained ? retained-1 : 0; rank < s->count; ++rank)
            if (!valid_cluster(w->proof, shrink_cluster(s, rank)) ||
                !file_fat_targets(&w->proof->view, shrink_cluster(s, rank), targets, &count)) return false;
    }
    if (count != w->target_count) return false;
    for (unsigned i = 0; i < w->target_count; ++i) {
        if (journal->entries[i].target_lba != w->transaction->first+w->targets[i]) return false;
        bool found = false;
        for (unsigned j = 0; j < count; ++j) if (w->targets[i] == targets[j]) { found = true; break; }
        if (!found) return false;
        for (unsigned j = 0; j < i; ++j) if (w->targets[i] == w->targets[j]) return false;
        memcpy(w->sector, journal->undo_data[i], 512);
        if (shrink_image(s, w->targets[i], w->sector) || memcmp(w->sector, journal->pending_data[i], 512)) return false;
    }
    return true;
}

int reist_fat32_shrink_finish(reist_fat32_shrink_t* s, bool commit,
    uint32_t* outcome, uint32_t* size, uint32_t* released) {
    if (!outcome || !size || !released) return -REIST_EINVAL;
    *outcome = REIST_FILE_OBJECT_NO_EFFECT; *size = *released = 0;
    if (!s || s->version != REIST_FAT32_SHRINK_VERSION || !s->owner.active) return -REIST_ESTALE;
    reist_fat32_overwrite_t* w = &s->owner;
    if (commit && !w->error) {
        /* Validate the live geometry before the plan uses its divisors/offsets. */
        int result = overwrite_identity(w);
        if (!result && !shrink_plan_valid(s)) result = -REIST_EINVAL;
        if (result) overwrite_error(w, result);
    }
    uint32_t ignored;
    int result = owned_finish(w, commit, outcome, &ignored);
    if (!result && commit && *outcome == REIST_FILE_OBJECT_DURABLE_COMMIT) {
        *size = s->resulting_size; *released = s->released;
        reist_fat32_ownership_t* p = w->proof;
        if (p->ready && p->epoch == w->admission.base.epoch+2) {
            /* No post-END disk trust: the journal already fully read back this
             * exact after-image. Only the exact old+2 epoch and original live
             * pin allow publishing its projected locator/generation and hints. */
            p->view = s->resulting_view;
            p->chain_count = s->count-s->released;
            for (unsigned i=0;i<REIST_FAT32_SEEK_ANCHORS;++i)
                if ((uint64_t)i*p->seek_stride >= p->chain_count) p->seek_anchors[i]=0;
            p->tail_first = p->chain_count > REIST_FAT32_TAIL_CACHE ? p->chain_count-REIST_FAT32_TAIL_CACHE : 0;
            if (p->tail_first < s->first) p->tail_first = s->first;
            if (p->tail_first > p->chain_count) p->tail_first = p->chain_count;
            for (uint32_t rank = p->tail_first; rank < p->chain_count; ++rank)
                p->tail[rank%REIST_FAT32_TAIL_CACHE] = shrink_cluster(s, rank);
            p->seek_cluster = p->chain_count ? shrink_cluster(s, p->chain_count-1) : 0;
            p->seek_rank = p->chain_count ? p->chain_count-1 : 0;
            for (uint32_t rank = p->chain_count; rank < s->count; ++rank) {
                uint32_t freed = shrink_cluster(s, rank);
                if (!valid_cluster(p, p->free_hint) || freed < p->free_hint) p->free_hint = freed;
                int index = slot(p, shrink_cluster(s, rank));
                if (index >= 0) for (unsigned map = 0; map < 5; ++map)
                    p->maps[map][(unsigned)index/8] &= (uint8_t)~(1U<<((unsigned)index%8));
            }
        }
    } else if (!result && *outcome == REIST_FILE_OBJECT_NO_EFFECT) *size = w->proof->view.file_size;
    return result;
}

static uint32_t grow_lba(const reist_fat32_grow_t* g, const reist_fat32_grow_data_t* data) {
    const reist_vfs_shadow_fat_view_t* v = &g->owner.proof->view;
    return v->data_start+(data->cluster-2)*v->sectors_per_cluster+
        (data->position/512)%v->sectors_per_cluster;
}

static int grow_start(reist_fat32_grow_t* g, reist_fat32_ownership_t* p,
    reist_fat32_transaction_t* tx, uint64_t target, const void* input, uint32_t length, bool append) {
    if (!g || !p || !tx) return -REIST_EINVAL;
    if (g->owner.active) return -REIST_EBUSY;
    memset(g, 0, sizeof(*g));
    int result = reist_fat32_overwrite_begin(&g->owner, p, tx, 0, NULL, 0);
    if (result) return result;
    reist_fat32_overwrite_t* w = &g->owner;
    g->version = REIST_FAT32_GROW_VERSION;
    if (append) {
        if ((length && !input) || length > 128U*1024) return overwrite_error(w, -REIST_EINVAL);
        target = (uint64_t)p->view.file_size+length;
    }
    if (target > UINT32_MAX) return overwrite_error(w, -REIST_EOVERFLOW);
    if (target < p->view.file_size) return overwrite_error(w, -REIST_ENOTSUP);
    uint32_t cb = p->view.sectors_per_cluster*512U;
    uint64_t capacity = (uint64_t)p->chain_count*cb;
    if (p->chain_count > p->view.cluster_count || p->tail_first > p->chain_count ||
        p->chain_count-p->tail_first > REIST_FAT32_TAIL_CACHE || capacity > 0x100000000ULL ||
        capacity < p->view.file_size || (!p->chain_count != !p->view.object.locator_c) ||
        (p->chain_count && p->tail_first == p->chain_count) || !valid_cluster(p, p->free_hint))
        return overwrite_error(w, -REIST_EINVAL);
    g->target = (uint32_t)target; g->append = append; g->input_length = length;
    g->resulting_view = p->view; g->scan = p->free_hint;
    w->offset = p->view.file_size; w->input = input;
    uint32_t rank = w->offset/cb;
    if (p->chain_count) {
        g->predecessor = p->tail[(p->chain_count-1)%REIST_FAT32_TAIL_CACHE];
        if (!valid_cluster(p, g->predecessor)) return overwrite_error(w, -REIST_EINVAL);
    }
    if (rank == p->chain_count) { w->cluster = 0; w->rank = rank; }
    else if (rank >= p->tail_first) {
        w->cluster = p->tail[rank%REIST_FAT32_TAIL_CACHE]; w->rank = rank;
    } else if (p->seek_cluster && p->seek_rank <= rank) {
        w->cluster = p->seek_cluster; w->rank = p->seek_rank;
    }
    w->anchor = w->cluster; w->power = 1; w->distance = 0;
    if (target == w->offset) { w->ready = 1; return 0; }
    add_target(w->targets, &w->target_count, p->view.object.locator_a);
    if (target > capacity) {
        result = file_fsinfo(w, g->fsinfo, &g->fsinfo_count);
        if (result) return overwrite_error(w, result);
    }
    return 0;
}

int reist_fat32_grow_begin(reist_fat32_grow_t* g, reist_fat32_ownership_t* p,
    reist_fat32_transaction_t* tx, uint64_t target) {
    return grow_start(g, p, tx, target, NULL, 0, false);
}
int reist_fat32_append_begin(reist_fat32_grow_t* g, reist_fat32_ownership_t* p,
    reist_fat32_transaction_t* tx, const void* input, uint32_t length) {
    return grow_start(g, p, tx, 0, input, length, true);
}

static int grow_image(const reist_fat32_grow_t* g, uint32_t lba, uint8_t* bytes) {
    const reist_fat32_overwrite_t* w = &g->owner;
    const reist_vfs_shadow_fat_view_t* v = &w->proof->view;
    if (lba == v->object.locator_a) {
        if (memcmp(bytes+v->object.locator_b, v->entry, 32)) return -REIST_ESTALE;
        memcpy(bytes+v->object.locator_b, g->resulting_view.entry, 32);
        return 0;
    }
    for (unsigned i = 0; i < g->data_count; ++i) if (lba == grow_lba(g, &g->data[i])) {
        const reist_fat32_grow_data_t* d = &g->data[i];
        if (g->append) memcpy(bytes+d->position%512, w->input+(d->position-w->offset), d->amount);
        else memset(bytes+d->position%512, 0, d->amount);
        return 0;
    }
    for (unsigned i = 0; i < g->fsinfo_count; ++i) if (lba == g->fsinfo[i]) {
        if (!g->allocated_count || get32(bytes) != 0x41615252U || get32(bytes+484) != 0x61417272U ||
            get32(bytes+508) != 0xaa550000U) return -REIST_EIO;
        put32(bytes+488, UINT32_MAX); put32(bytes+492, UINT32_MAX);
        return 0;
    }
    if (!g->allocated_count || lba < v->reserved_sectors || lba >= v->data_start) return -REIST_EIO;
    uint32_t copy = (lba-v->reserved_sectors)/v->fat_sectors;
    if (copy >= v->fat_count || (!v->mirrored && copy != v->active_fat)) return -REIST_EIO;
    uint32_t base = ((lba-v->reserved_sectors)%v->fat_sectors)*128;
    bool changed = false;
    for (unsigned i = 0; i <= g->allocated_count; ++i) {
        uint32_t cluster = i ? g->allocated[i-1] : g->predecessor;
        if (!cluster || cluster < base || cluster-base >= 128) continue;
        uint8_t* entry = bytes+(cluster-base)*4;
        uint32_t previous = get32(entry)&FAT_MASK;
        if (i ? previous != 0 : previous < FAT_EOC) return -REIST_EIO;
        uint32_t next = i == g->allocated_count ? FAT_MASK : g->allocated[i];
        put32(entry, (get32(entry)&~FAT_MASK)|next);
        changed = true;
    }
    return changed ? 0 : -REIST_EIO;
}

static int grow_stage(reist_fat32_grow_t* g) {
    reist_fat32_overwrite_t* w = &g->owner;
    uint32_t start = w->proof->view.object.locator_c;
    if (!start && g->allocated_count) start = g->allocated[0];
    int result = reist_vfs_shadow_fat_grow_view(&w->proof->view, w->offset+w->bytes, start, &g->resulting_view);
    if (result) return result;
    for (unsigned i = 0; i < w->target_count; ++i) {
        result = overwrite_read(w, w->proof->view.object.resource, w->targets[i], w->sector);
        if (!result) result = grow_image(g, w->targets[i], w->sector);
        if (!result) result = reist_fat32_transaction_stage(w->transaction,
            w->transaction->first+w->targets[i], w->sector);
        if (result) return result;
    }
    w->ready = 1;
    return 0;
}

int reist_fat32_grow_step(reist_fat32_grow_t* g) {
    if (!g || g->version != REIST_FAT32_GROW_VERSION || !g->owner.active) return -REIST_ESTALE;
    reist_fat32_overwrite_t* w = &g->owner;
    if (w->error) return w->error;
    int result = overwrite_identity(w);
    if (result) return overwrite_error(w, result);
    reist_fat32_ownership_t* p = w->proof;
    if (w->offset != p->view.file_size || g->target < w->offset || w->bytes > g->target-w->offset ||
        g->data_count > ATA_JOURNAL_MAX_ENTRIES || g->allocated_count > ATA_JOURNAL_MAX_ENTRIES ||
        w->target_count > ATA_JOURNAL_MAX_ENTRIES || g->fsinfo_count > 2 ||
        !valid_cluster(p, g->scan) || g->scanned > p->view.cluster_count ||
        g->append > 1 || (g->append && (g->input_length != g->target-w->offset ||
        g->input_length > 128U*1024 || (g->input_length && !w->input)))) return overwrite_error(w, -REIST_EINVAL);
    if (w->ready) return 0;
    reist_vfs_shadow_io_t io = {w, overwrite_info, overwrite_read};
    unsigned budget = 256;
    uint32_t cb = p->view.sectors_per_cluster*512U;
    bool complete = false;
    for (unsigned work = 0; work < 128; ++work) {
        if (w->bytes == g->target-w->offset) { complete = true; break; }
        uint32_t position = w->offset+w->bytes, rank = position/cb;
        if (w->rank > rank || rank > p->chain_count+g->allocated_count) return overwrite_error(w, -REIST_EIO);
        if (!w->cluster) {
            if (rank != p->chain_count+g->allocated_count) return overwrite_error(w, -REIST_EIO);
            if (g->scanned == p->view.cluster_count) {
                if (!w->bytes) return overwrite_error(w, -REIST_ENOSPC);
                complete = true; break; /* explicit short progress, never hidden size change */
            }
            uint32_t candidate = g->scan, value = 0;
            result = link_value(p, &io, candidate, &budget, &value);
            if (result == STEP_YIELD) return 1;
            if (result) return overwrite_error(w, result);
            ++g->scanned; g->scan = candidate == p->view.cluster_count+1 ? 2 : candidate+1;
            bool selected = false;
            for (unsigned i = 0; i < g->allocated_count; ++i) if (g->allocated[i] == candidate) selected = true;
            if (value || selected) continue;
            uint32_t targets[ATA_JOURNAL_MAX_ENTRIES], count = w->target_count;
            memcpy(targets, w->targets, sizeof(targets));
            bool fits = file_fat_targets(&p->view, candidate, targets, &count);
            if (!g->allocated_count) {
                if (g->predecessor && !file_fat_targets(&p->view, g->predecessor, targets, &count)) fits = false;
                for (unsigned i = 0; i < g->fsinfo_count; ++i)
                    if (!add_target(targets, &count, g->fsinfo[i])) fits = false;
            }
            reist_fat32_grow_data_t first = {candidate, position, 0};
            if (!add_target(targets, &count, grow_lba(g, &first))) fits = false;
            if (!fits) { complete = true; break; }
            if (g->allocated_count == ATA_JOURNAL_MAX_ENTRIES) return overwrite_error(w, -REIST_EIO);
            g->allocated[g->allocated_count++] = candidate;
            memcpy(w->targets, targets, sizeof(targets)); w->target_count = count;
            w->cluster = candidate; w->rank = rank;
            continue;
        }
        if (!valid_cluster(p, w->cluster)) return overwrite_error(w, -REIST_EIO);
        uint32_t next = FAT_MASK;
        if (w->rank < p->chain_count) {
            result = link_value(p, &io, w->cluster, &budget, &next);
            if (result == STEP_YIELD) return 1;
            if (result) return overwrite_error(w, result);
            if (w->rank+1 == p->chain_count ? next < FAT_EOC : !valid_cluster(p, next))
                return overwrite_error(w, -REIST_EIO);
            if (w->rank+1 < p->chain_count && w->rank+1 >= p->tail_first &&
                next != p->tail[(w->rank+1)%REIST_FAT32_TAIL_CACHE]) return overwrite_error(w, -REIST_EIO);
        } else if (w->rank-p->chain_count >= g->allocated_count ||
            w->cluster != g->allocated[w->rank-p->chain_count]) return overwrite_error(w, -REIST_EIO);
        if (w->rank < rank) {
            if (next >= FAT_EOC) { w->cluster = 0; ++w->rank; continue; }
            if (!w->power || w->distance >= w->power || next == w->anchor) return overwrite_error(w, -REIST_EIO);
            if (++w->distance == w->power) { w->anchor = next; w->distance = 0; w->power *= 2; }
            w->cluster = next; ++w->rank;
            continue;
        }
        reist_fat32_grow_data_t data = {w->cluster, position, 512-position%512};
        if (data.amount > g->target-position) data.amount = g->target-position;
        uint32_t lba = grow_lba(g, &data);
        if (lba < p->view.data_start || lba >= p->view.sectors || lba == p->view.object.locator_a)
            return overwrite_error(w, -REIST_EIO);
        if (!add_target(w->targets, &w->target_count, lba)) { complete = true; break; }
        for (unsigned i = 0; i < g->data_count; ++i)
            if (lba == grow_lba(g, &g->data[i])) return overwrite_error(w, -REIST_EIO);
        if (g->data_count == ATA_JOURNAL_MAX_ENTRIES) return overwrite_error(w, -REIST_EIO);
        g->data[g->data_count++] = data; w->bytes += data.amount;
    }
    if (!complete) return 1;
    if (!w->bytes) return overwrite_error(w, -REIST_EIO);
    result = grow_stage(g);
    return result ? overwrite_error(w, result) : 0;
}

static bool grow_plan_valid(reist_fat32_grow_t* g) {
    reist_fat32_overwrite_t* w = &g->owner;
    const reist_fat32_ownership_t* p = w->proof;
    const ata_undo_journal_t* journal = &w->transaction->journal;
    if (!w->ready || !journal->enabled || journal->transaction_depth != 1 ||
        w->target_count > ATA_JOURNAL_MAX_ENTRIES || journal->entry_count != w->target_count ||
        g->data_count > ATA_JOURNAL_MAX_ENTRIES || g->allocated_count > ATA_JOURNAL_MAX_ENTRIES ||
        g->fsinfo_count > 2 || w->offset != p->view.file_size || g->target < w->offset ||
        w->bytes > g->target-w->offset || g->append > 1 ||
        (g->append && (g->input_length != g->target-w->offset || g->input_length > 128U*1024 ||
        (g->input_length && !w->input)))) return false;
    uint32_t cb = p->view.sectors_per_cluster*512U;
    uint32_t resulting_size = w->offset+w->bytes;
    uint32_t required = file_cluster_count(resulting_size, cb);
    if (required < p->chain_count) required = p->chain_count;
    if (required-p->chain_count != g->allocated_count ||
        (p->chain_count ? g->predecessor != p->tail[(p->chain_count-1)%REIST_FAT32_TAIL_CACHE] : g->predecessor != 0))
        return false;
    reist_vfs_shadow_fat_view_t expected;
    uint32_t start = p->view.object.locator_c;
    if (!start && g->allocated_count) start = g->allocated[0];
    if (reist_vfs_shadow_fat_grow_view(&p->view, resulting_size, start, &expected) ||
        memcmp(&expected, &g->resulting_view, sizeof(expected))) return false;
    uint32_t targets[ATA_JOURNAL_MAX_ENTRIES], count = 0, copied = 0;
    if (w->bytes && !add_target(targets, &count, p->view.object.locator_a)) return false;
    for (unsigned i = 0; i < g->data_count; ++i) {
        const reist_fat32_grow_data_t* d = &g->data[i];
        if (!valid_cluster(p, d->cluster) || d->position != w->offset+copied || copied >= w->bytes ||
            !d->amount || d->amount > 512-d->position%512 || d->amount > w->bytes-copied) return false;
        uint32_t rank = d->position/cb;
        if (rank >= p->chain_count) {
            if (rank-p->chain_count >= g->allocated_count || d->cluster != g->allocated[rank-p->chain_count]) return false;
        } else if (rank >= p->tail_first && d->cluster != p->tail[rank%REIST_FAT32_TAIL_CACHE]) return false;
        uint32_t lba = grow_lba(g, d);
        if (lba < p->view.data_start || lba >= p->view.sectors || lba == p->view.object.locator_a ||
            !add_target(targets, &count, lba)) return false;
        for (unsigned j = 0; j < i; ++j) if (lba == grow_lba(g, &g->data[j])) return false;
        copied += d->amount;
    }
    if (copied != w->bytes) return false;
    if (g->allocated_count) {
        if (g->predecessor && !file_fat_targets(&p->view, g->predecessor, targets, &count)) return false;
        for (unsigned i = 0; i < g->fsinfo_count; ++i) if (!add_target(targets, &count, g->fsinfo[i])) return false;
        for (unsigned i = 0; i < g->allocated_count; ++i) {
            if (!valid_cluster(p, g->allocated[i]) || g->allocated[i] == g->predecessor ||
                !file_fat_targets(&p->view, g->allocated[i], targets, &count)) return false;
            for (unsigned j = 0; j < i; ++j) if (g->allocated[j] == g->allocated[i]) return false;
        }
    }
    if (count != w->target_count) return false;
    for (unsigned i = 0; i < w->target_count; ++i) {
        if (journal->entries[i].target_lba != w->transaction->first+w->targets[i]) return false;
        bool found = false;
        for (unsigned j = 0; j < count; ++j) if (w->targets[i] == targets[j]) found = true;
        if (!found) return false;
        for (unsigned j = 0; j < i; ++j) if (w->targets[i] == w->targets[j]) return false;
        memcpy(w->sector, journal->undo_data[i], 512);
        if (grow_image(g, w->targets[i], w->sector) || memcmp(w->sector, journal->pending_data[i], 512)) return false;
    }
    return true;
}

int reist_fat32_grow_finish(reist_fat32_grow_t* g, bool commit,
    uint32_t* outcome, uint32_t* size, uint32_t* durable) {
    if (!outcome || !size || !durable) return -REIST_EINVAL;
    *outcome = REIST_FILE_OBJECT_NO_EFFECT; *size = *durable = 0;
    if (!g || g->version != REIST_FAT32_GROW_VERSION || !g->owner.active) return -REIST_ESTALE;
    reist_fat32_overwrite_t* w = &g->owner;
    if (commit && !w->error) {
        int result = overwrite_identity(w);
        if (!result && !grow_plan_valid(g)) result = -REIST_EINVAL;
        if (result) overwrite_error(w, result);
    }
    int result = owned_finish(w, commit, outcome, durable);
    if (!result && commit && *outcome == REIST_FILE_OBJECT_DURABLE_COMMIT) {
        *size = g->resulting_view.file_size;
        reist_fat32_ownership_t* p = w->proof;
        if (p->ready && p->epoch == w->admission.base.epoch+2) {
            p->view = g->resulting_view;
            for (unsigned i = 0; i < g->allocated_count; ++i) {
                uint32_t cluster = g->allocated[i];
                int cached=seek_record(p,p->chain_count,cluster);
                if (cached) { refuse(p,cached); break; }
                p->tail[p->chain_count++%REIST_FAT32_TAIL_CACHE] = cluster;
                int index = slot(p, cluster);
                if (index >= 0) {
                    mark(p, ALLOCATED, (unsigned)index); mark(p, INCOMING, (unsigned)index);
                    mark(p, REACHABLE, (unsigned)index); mark(p, OWNED, (unsigned)index);
                }
                p->free_hint = cluster == p->view.cluster_count+1 ? 2 : cluster+1;
            }
            if (p->chain_count > REIST_FAT32_TAIL_CACHE && p->tail_first < p->chain_count-REIST_FAT32_TAIL_CACHE)
                p->tail_first = p->chain_count-REIST_FAT32_TAIL_CACHE;
            if (g->data_count) {
                p->seek_cluster = g->data[g->data_count-1].cluster;
                p->seek_rank = g->data[g->data_count-1].position/(p->view.sectors_per_cluster*512U);
            }
        }
    } else if (!result && *outcome == REIST_FILE_OBJECT_NO_EFFECT) *size = w->proof->view.file_size;
    return result;
}

int reist_fat32_sync_begin(reist_fat32_overwrite_t* w, reist_fat32_ownership_t* p,
    reist_fat32_transaction_t* tx) {
    int result = reist_fat32_overwrite_begin(w, p, tx, 0, NULL, 0);
    if (!result) {
        w->ready = 1;
        /* Sync must not discard a valid sequential-data hint. */
        w->cluster = p->seek_cluster; w->rank = p->seek_rank;
    }
    return result;
}

int reist_fat32_sync_finish(reist_fat32_overwrite_t* w, bool commit, uint32_t* outcome) {
    if (!outcome) return -REIST_EINVAL;
    *outcome = REIST_FILE_OBJECT_NO_EFFECT;
    if (!w || w->version != REIST_FAT32_OVERWRITE_VERSION || !w->active) return -REIST_ESTALE;
    if (commit && !w->error) {
        int result = overwrite_identity(w);
        if (!result && (!w->ready || w->bytes || w->mapped || w->target_count ||
            w->transaction->journal.entry_count)) result = -REIST_EINVAL;
        if (!result) result = reist_fat32_transaction_flush_owned(w->transaction);
        if (result) overwrite_error(w, result);
    }
    uint32_t ignored;
    return owned_finish(w, commit, outcome, &ignored);
}
