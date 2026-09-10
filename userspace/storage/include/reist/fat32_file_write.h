/* Ring-3 FAT32 write preparation. Microsoft FAT v1.03 on-disk terminology;
 * reference: https://www.pcjs.org/documents/papers/microsoft/MS_FAT_OVERVIEW_103-2000-12-06.pdf
 * this is private parser/planner state, not a capability or POSIX API.
 * No heap, VFS calls, raw-write fallback or persistent format of its own. */
#ifndef REIST_FAT32_FILE_WRITE_H
#define REIST_FAT32_FILE_WRITE_H
#include "reist/vfs_shadow_fat32.h"
#include "reist/fat32_transaction.h"

#define REIST_FAT32_OWNERSHIP_VERSION 1U
#define REIST_FAT32_OWNERSHIP_CLUSTERS 65536U
#define REIST_FAT32_OWNERSHIP_MAP_BYTES ((REIST_FAT32_OWNERSHIP_CLUSTERS + 1U + 7U) / 8U)
#define REIST_FAT32_OWNERSHIP_DEPTH 32U
#define REIST_FAT32_OWNERSHIP_WORK 1024U
#define REIST_FAT32_TAIL_CACHE 1024U
#define REIST_FAT32_SEEK_ANCHORS 64U
#define REIST_FAT32_CLUSTER_FREE 1U
#define REIST_FAT32_CLUSTER_FILE 2U
#define REIST_FAT32_CLUSTER_DIRECTORY 3U
#define REIST_FAT32_CLUSTER_OTHER 4U

typedef struct {
    uint32_t first, parent, cluster, sector, entry;
    uint32_t visited, anchor, power, distance, next, entered, ended;
    uint32_t target_aliases;
} reist_fat32_directory_walk_t;

typedef struct {
    uint32_t version, struct_size;
    uint64_t epoch;
    reist_vfs_shadow_fat_view_t view;
    uint32_t first, count, directory_cluster, target_parent;
    uint32_t phase, fat_index, verify_index, target_seen, depth, ready;
    uint32_t whole_volume, verified_until, recovery_only;
    /* Hints retained only across verified own commits. Ring indexed by rank;
     * tail_first..chain_count-1 is the valid suffix, not a chain-size ceiling. */
    uint32_t seek_cluster, seek_rank;
    uint32_t chain_count, tail_first, free_hint;
    uint32_t tail[REIST_FAT32_TAIL_CACHE];
    /* Sparse prefix hints share this same pin/epoch. Power-of-two spacing is
     * compacted while a verified chain grows; never a whole-chain array. */
    uint32_t seek_stride, seek_anchors[REIST_FAT32_SEEK_ANCHORS];
    int32_t error;
    uint64_t chain_visits;
    uint32_t file_cluster, file_size, file_owned, file_visited;
    uint32_t file_anchor, file_power, file_distance;
    uint32_t cache_lba[3], cache_valid[3];
    uint8_t cache[3][X86OS_STORAGE_BLOCK_SIZE];
    /* allocated / unavailable / incoming / reachable / selected-file.
     * One extra slot covers the target's directory cluster outside the window. */
    uint8_t maps[5][REIST_FAT32_OWNERSHIP_MAP_BYTES];
    reist_fat32_directory_walk_t directories[REIST_FAT32_OWNERSHIP_DEPTH];
} reist_fat32_ownership_t;

/* A physical-cluster window is a bounded workspace, not a file-size ceiling.
 * Entire FAT and reachable namespace are scanned incrementally. Only the
 * window and exact directory cluster receive ownership evidence. Other
 * clusters cannot be mutated on the strength of this certificate.
 * The host supplies/rechecks the kernel mutation epoch and live object pin;
 * a foreign mutation, cancel/reap or medium change invalidates the context.
 * Only the verified own-commit paths may advance cached evidence; there
 * is deliberately no generic 'set epoch' or 'trust this allocation' operation. */
int reist_fat32_ownership_begin(reist_fat32_ownership_t* state,
    const reist_vfs_shadow_io_t* io, const reist_vfs_shadow_object_t* object,
    uint64_t epoch, uint32_t first_cluster);
/* Exhaust all windows under one unchanged epoch before ready. This full proof,
 * not a local chain/window, is required by the later mutation planner. It can
 * be retained across reads and advanced only by a verified own commit; do not
 * restart a whole-volume scan for each data chunk. No request deadline is
 * stored/renewed here: the host bounds every step/IO with its original request. */
int reist_fat32_volume_begin(reist_fat32_ownership_t* state,
    const reist_vfs_shadow_io_t* io, const reist_vfs_shadow_object_t* object, uint64_t epoch);
/* Full-volume repair qualification, including empty volumes. This proof must
 * never be used by a file mutation planner. Host owns the original repair
 * token/deadline; generation binds every step, it does not renew the lease. */
int reist_fat32_recovery_begin(reist_fat32_ownership_t* state,
    const reist_vfs_shadow_io_t* io, uint32_t resource, uint64_t generation);
/* 1 = more bounded work, 0 = evidence complete, negative = sticky refusal.
 * At most1024 work items and320 physical reads in each call. */
int reist_fat32_ownership_step(reist_fat32_ownership_t* state,
    const reist_vfs_shadow_io_t* io, uint64_t epoch);
/* No IO or state publication. A missing window is EAGAIN, never ENOSPC. */
int reist_fat32_ownership_query(const reist_fat32_ownership_t* state,
    uint64_t epoch, uint32_t cluster, uint32_t* classification);

#define REIST_FAT32_OVERWRITE_VERSION 1U
typedef struct {
    uint32_t version, active, ready, token;
    reist_fat32_ownership_t* proof;
    reist_fat32_transaction_t* transaction;
    reist_file_object_owned_request_t admission;
    const uint8_t* input;
    uint32_t offset, bytes, mapped, cluster, rank, target_count;
    uint32_t anchor, power, distance;
    uint32_t targets[ATA_JOURNAL_MAX_ENTRIES];
    int error;
    uint8_t sector[512];
} reist_fat32_overwrite_t;

/* Private planner, not the public write API. Existing-size data only; growth,
 * allocation and incremental resize use the separate planners below.
 * Host grants rights and takes complete immutable request input
 * before owned admission. All reads/writes below use that same token/deadline.
 * Empty, zero-initialized writer and freshly admitted, unstaged owned tx only.
 * A begin failure poisons tx; caller must finish(false), never replay it.
 * Input/proof/tx remain owned by the host and immutable until finish. */
int reist_fat32_overwrite_begin(reist_fat32_overwrite_t* writer,
    reist_fat32_ownership_t* proof, reist_fat32_transaction_t* transaction,
    uint64_t offset, const void* input, uint32_t length);
/* 1 = bounded seek progress; 0 = entire <=20-target plan staged in RAM.
 * At most128 chain links and300 physical reads per call, no persistent effects.
 * No fixed chain/file-size ceiling and no whole-volume rescan per data chunk. */
int reist_fat32_overwrite_step(reist_fat32_overwrite_t* writer);
/* Actual RSTJ commit/abort, then exact old+2 epoch check before evidence reuse.
 * Durable progress remains explicit even when evidence cannot be retained.
 * UNKNOWN or any uncertain proof never advances the cache. Double finish and
 * direct tx replacement are rejected; closing never commits pending data. */
int reist_fat32_overwrite_finish(reist_fat32_overwrite_t* writer, bool commit,
    uint32_t* outcome, uint32_t* durable_bytes);

#define REIST_FAT32_SHRINK_VERSION 1U
/* At most20 FAT sectors can contain2560 released entries, plus predecessor.
 * Larger files continue in explicit independently recoverable steps. */
#define REIST_FAT32_SHRINK_WINDOW (ATA_JOURNAL_MAX_ENTRIES*128U+1U)
#define REIST_FAT32_SHRINK_READ_AHEAD 64U
typedef struct {
    reist_fat32_overwrite_t owner;
    uint32_t version, target, count, first, released, phase, terminal_value;
    uint32_t scan_cluster, scan_rank, scan_first, scan_end, anchor, power, distance;
    /* Same transaction only; every physical sector is charged to step budget.
     * Never participates in undo staging or post-write readback. */
    uint32_t read_first[2], read_count[2];
    uint8_t read_ahead[2][REIST_FAT32_SHRINK_READ_AHEAD][512];
    uint32_t tail[REIST_FAT32_SHRINK_WINDOW];
    uint32_t fsinfo[2], fsinfo_count, resulting_size;
    reist_vfs_shadow_fat_view_t resulting_view;
} reist_fat32_shrink_t;

/* Host-owned fixed workspace, not a small task-stack local.
 * Private tail-first half of resize_step; growth is not admitted here.
 * released_clusters makes progress explicit even for preallocated file tails
 * whose release does not yet change the visible size. No implicit repeat. */
int reist_fat32_shrink_begin(reist_fat32_shrink_t* shrink,
    reist_fat32_ownership_t* proof, reist_fat32_transaction_t* transaction, uint64_t target);
/* <=128 chain/planning items, <=300 reads per call, no persistent effects. */
int reist_fat32_shrink_step(reist_fat32_shrink_t* shrink);
int reist_fat32_shrink_finish(reist_fat32_shrink_t* shrink, bool commit,
    uint32_t* outcome, uint32_t* resulting_size, uint32_t* released_clusters);

#define REIST_FAT32_GROW_VERSION 1U
typedef struct {
    uint32_t cluster, position, amount;
} reist_fat32_grow_data_t;
typedef struct {
    reist_fat32_overwrite_t owner;
    uint32_t version, target, append, input_length, data_count;
    uint32_t allocated_count, allocated[ATA_JOURNAL_MAX_ENTRIES];
    uint32_t predecessor, scan, scanned, fsinfo[2], fsinfo_count;
    reist_fat32_grow_data_t data[ATA_JOURNAL_MAX_ENTRIES];
    reist_vfs_shadow_fat_view_t resulting_view;
} reist_fat32_grow_t;
/* Fixed host-owned workspace. Growth starts at the pinned, reserved EOF;
 * grow_begin zeroes the visible extension, append_begin consumes immutable
 * complete input (<=128KiB). No hidden pwrite gap or automatic continuation.
 * Newly allocated cluster tails stay unexposed until initialized by later steps. */
int reist_fat32_grow_begin(reist_fat32_grow_t* grow,
    reist_fat32_ownership_t* proof, reist_fat32_transaction_t* transaction, uint64_t target);
int reist_fat32_append_begin(reist_fat32_grow_t* grow,
    reist_fat32_ownership_t* proof, reist_fat32_transaction_t* transaction,
    const void* input, uint32_t length);
/* <=128 seek/allocation/data items, <=300 physical reads; no effects until
 * finish. Full journal capacity returns an explicit short durable step;
 * ENOSPC requires exhausting the volume, not a cache window or time budget. */
int reist_fat32_grow_step(reist_fat32_grow_t* grow);
int reist_fat32_grow_finish(reist_fat32_grow_t* grow, bool commit,
    uint32_t* outcome, uint32_t* resulting_size, uint32_t* durable_bytes);

#define REIST_FAT32_SYNC_VERSION 1U
/* Explicit live-object durability boundary, no staged data and no close/GC
 * writeback. Host must grant sync rights separately. Success confirms the
 * flush, not a content change; NO_EFFECT abort and UNKNOWN stay distinct. */
int reist_fat32_sync_begin(reist_fat32_overwrite_t* sync,
    reist_fat32_ownership_t* proof, reist_fat32_transaction_t* transaction);
int reist_fat32_sync_finish(reist_fat32_overwrite_t* sync, bool commit, uint32_t* outcome);
#endif
