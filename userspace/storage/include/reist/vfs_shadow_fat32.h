/**
 * @file userspace/storage/include/reist/vfs_shadow_fat32.h
 * @brief Bounded read-only FAT12/FAT32 metadata parser for the storage service.
 */
#ifndef REIST_VFS_SHADOW_FAT32_H
#define REIST_VFS_SHADOW_FAT32_H

#include <stdint.h>

#include "x86os.h"

#define REIST_VFS_SHADOW_MAX_RESOURCES 22U
#define REIST_VFS_SHADOW_MAX_COMPONENTS 32U
#define REIST_VFS_SHADOW_MAX_CHAIN_CLUSTERS 128U
#define REIST_VFS_SHADOW_MAX_FILE_CHAIN_CLUSTERS 6400U
#define REIST_VFS_SHADOW_MAX_SECTOR_READS 320U
#define REIST_VFS_SHADOW_OBJECT_VERSION 1U
#define REIST_VFS_SHADOW_OBJECT_FAT 1U
#define REIST_VFS_SHADOW_OBJECT_EXT2 2U
#define REIST_VFS_SHADOW_READDIR_CURSOR_VERSION 1U

typedef struct {
    uint32_t version;
    uint32_t struct_size;
    uint32_t filesystem;
    uint32_t resource;
    uint32_t volume_signature;
    uint32_t locator_a;
    uint32_t locator_b;
    uint32_t locator_c;
    uint32_t object_generation;
} reist_vfs_shadow_object_t;

typedef int (*reist_vfs_shadow_drive_info_fn)(
    void *context, uint32_t resource, x86os_drive_info_t *info);
typedef int (*reist_vfs_shadow_read_sector_fn)(
    void *context, uint32_t resource, uint32_t sector,
    uint8_t data[X86OS_STORAGE_BLOCK_SIZE]);

typedef struct {
    void *context;
    reist_vfs_shadow_drive_info_fn drive_info;
    reist_vfs_shadow_read_sector_fn read_sector;
} reist_vfs_shadow_io_t;

/* Ring-3 parser state, not a kernel capability or allocation certificate.
 * Callers must hold/verify their object pin and supply the current mutation
 * epoch. A completed chain proves local links only, not absence of cross-links
 * from other objects. Global allocation/namespace ownership remains required
 * before the write planner may publish a transaction. */
#define REIST_VFS_SHADOW_FAT_CHAIN_VERSION 1U
#define REIST_VFS_SHADOW_FAT_CHAIN_WINDOW 128U
typedef struct {
    reist_vfs_shadow_object_t object;
    uint32_t sectors, reserved_sectors, fat_sectors, data_start, cluster_count;
    uint32_t root_cluster, sectors_per_cluster, fat_count, active_fat, mirrored;
    uint32_t fsinfo_sector, backup_sector, file_size;
    uint8_t entry[32];
} reist_vfs_shadow_fat_view_t;

typedef struct {
    uint32_t version, struct_size;
    uint64_t epoch;
    reist_vfs_shadow_fat_view_t view;
    uint32_t cluster, anchor, power, distance, visited, complete;
    int32_t error;
    uint32_t cache_lba[2], cache_valid[2];
    uint8_t cache[2][X86OS_STORAGE_BLOCK_SIZE];
} reist_vfs_shadow_fat_chain_cursor_t;

int reist_vfs_shadow_fat_view(const reist_vfs_shadow_io_t* io,
    const reist_vfs_shadow_object_t* object, reist_vfs_shadow_fat_view_t* view);
/* Recovery geometry only: no fabricated file locator or object authority. */
int reist_vfs_shadow_fat_volume_view(const reist_vfs_shadow_io_t* io,
    uint32_t resource, reist_vfs_shadow_fat_view_t* view);
/* Pure private projection, not a media read or authority to refresh a handle.
 * Host may publish only after exact journal readback and owned epoch/pin proof. */
int reist_vfs_shadow_fat_shrink_view(const reist_vfs_shadow_fat_view_t* before,
    uint32_t size, uint32_t start, reist_vfs_shadow_fat_view_t* after);
int reist_vfs_shadow_fat_grow_view(const reist_vfs_shadow_fat_view_t* before,
    uint32_t size, uint32_t start, reist_vfs_shadow_fat_view_t* after);
int reist_vfs_shadow_fat_chain_begin(const reist_vfs_shadow_io_t* io,
    const reist_vfs_shadow_object_t* object, uint64_t epoch,
    reist_vfs_shadow_fat_chain_cursor_t* cursor);
/* 1 = bounded progress, 0 = complete chain, negative = error. Each step checks
 * the unchanged BPB/entry and reads at most320 sectors; no6400-cluster ceiling.
 * Error is sticky until an explicit new begin; no implicit restart/replay. */
int reist_vfs_shadow_fat_chain_step(const reist_vfs_shadow_io_t* io,
    uint64_t epoch, reist_vfs_shadow_fat_chain_cursor_t* cursor);

/**
 * Replaceable parser hint for one sequential FAT directory walk.
 *
 * The hint carries no authority.  Every use resolves the path and validates
 * the medium, directory identity and complete cluster prefix again.  Zeroed
 * or malformed state selects the ordinary bounded cold scan.
 */
typedef struct {
    uint32_t version;
    uint32_t struct_size;
    uint32_t next_index;
    uint32_t resource;
    uint32_t volume_signature;
    uint32_t directory_generation;
    uint32_t directory_cluster;
    uint32_t cluster;
    uint32_t cluster_depth;
    uint32_t sector_index;
    uint32_t entry_offset;
    uint32_t fat_type;
    uint32_t active;
} reist_vfs_shadow_fat_readdir_cursor_t;

/** Returns the public SYS_STAT error convention: 0, -2, -5, -22 or -110. */
int reist_vfs_shadow_fat32_stat(const reist_vfs_shadow_io_t *io,
                                const char *absolute_path,
                                uint32_t path_length,
                                x86os_file_info_t *info);

/** Auto-detects Microsoft FAT12 or FAT32; FAT16 is rejected. */
int reist_vfs_shadow_fat_stat(const reist_vfs_shadow_io_t *io,
                              const char *absolute_path,
                              uint32_t path_length,
                              x86os_file_info_t *info);

int reist_vfs_shadow_fat_read(const reist_vfs_shadow_io_t *io,
                              const char *absolute_path,
                              uint32_t path_length, uint32_t offset,
                              uint8_t *data, uint32_t capacity,
                              uint32_t *transferred);

int reist_vfs_shadow_fat_readdir(const reist_vfs_shadow_io_t *io,
                                 const char *absolute_path,
                                 uint32_t path_length, uint32_t index,
                                 x86os_file_info_t *info);

int reist_vfs_shadow_fat_readdir_continue(
    const reist_vfs_shadow_io_t *io, const char *absolute_path,
    uint32_t path_length, uint32_t index,
    reist_vfs_shadow_fat_readdir_cursor_t *cursor,
    x86os_file_info_t *info);

int reist_vfs_shadow_fat_object_open(
    const reist_vfs_shadow_io_t *io, const char *absolute_path,
    uint32_t path_length, reist_vfs_shadow_object_t *object,
    x86os_file_info_t *info);
/* Same single bounded resolution, additionally projecting the final canonical
 * directory identity. The key alone is not an admitted pin or access grant.
 * Resource/physical-volume normalization is the trusted kernel's job. */
int reist_vfs_shadow_fat_object_open_key(
    const reist_vfs_shadow_io_t *io, const char *absolute_path,
    uint32_t path_length, reist_vfs_shadow_object_t *object,
    x86os_file_info_t *info, reist_file_object_key_t *key);
int reist_vfs_shadow_fat_object_stat(
    const reist_vfs_shadow_io_t *io,
    const reist_vfs_shadow_object_t *object, x86os_file_info_t *info);
int reist_vfs_shadow_fat_object_read(
    const reist_vfs_shadow_io_t *io,
    const reist_vfs_shadow_object_t *object, uint32_t offset, uint8_t *data,
    uint32_t capacity, uint32_t *transferred);

/* Host-controlled continuation, not a renewed lease. Called before/after the
 * read and at most128 chain/data work items apart; must check the original
 * request deadline and live pin, yield, and return zero or a negative errno.
 * IO callbacks must also enforce that deadline. The legacy API retains its
 * fixed total budgets. This API retains320 reads per window and the volume's
 * finite cluster bound, with cycle state preserved across every continuation.
 * Failure clears the entire output, never publishes a partial read. */
typedef int (*reist_vfs_shadow_progress_fn)(void *context);
int reist_vfs_shadow_fat_object_read_windowed(
    const reist_vfs_shadow_io_t *io, const reist_vfs_shadow_object_t *object,
    uint32_t offset, uint8_t *data, uint32_t capacity, uint32_t *transferred,
    reist_vfs_shadow_progress_fn progress, void *context);

#endif
