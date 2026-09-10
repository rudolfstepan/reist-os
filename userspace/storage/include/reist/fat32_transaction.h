/* Ring-3 host adapter for the existing RSTJ v1/v2 undo core. No ambient OS
 * calls: the host explicitly supplies token/guard mediation. Fixed storage;
 * an instance must not live on a small task stack or be shared concurrently. */
#ifndef REIST_FAT32_TRANSACTION_H
#define REIST_FAT32_TRANSACTION_H
#include "reist/abi/syscall.h"
#include "../../../../drivers/block/ata_journal.h"

typedef struct {
    void* context;
    int (*guard)(void*, reist_file_object_guard_request_t*);
    int (*transfer)(void*, const reist_storage_journal_request_t*, void*);
} reist_fat32_transaction_io_t;

/* Separate host capability; old adapters do not gain owned-object authority. */
typedef struct {
    reist_fat32_transaction_io_t base;
    int (*owned)(void*, reist_file_object_owned_request_t*);
} reist_fat32_owned_transaction_io_t;

typedef struct {
    ata_undo_journal_t journal;
    reist_fat32_transaction_io_t io;
    uint32_t resource, token, first, sectors, reserved;
    /* Exact pre-admission identity, retained only for owned object planning.
     * The token is still the kernel authority; this is not a new grant. */
    reist_file_object_owned_request_t admission;
    /* Retained also when attach fails and internally finishes the token. */
    uint32_t last_outcome;
    /* Synchronous, one-shot before-images for one staged contiguous run.
     * Cleared before commit; never used for live identity or write readback. */
    uint32_t stage_first, stage_count;
    uint8_t stage_before[ATA_JOURNAL_MAX_ENTRIES][ATA_JOURNAL_SECTOR_SIZE];
    uint8_t stage_after[ATA_JOURNAL_SECTOR_SIZE];
    int error;
    bool active, attempted, owned, committing, staging;
} reist_fat32_transaction_t;

/* Zero-initialize once. An admitted context cannot be reopened/reinitialized
 * before finish; malformed geometry is rejected before asking for authority. */
int reist_fat32_transaction_begin(reist_fat32_transaction_t* transaction,
    const reist_fat32_transaction_io_t* io, const reist_file_object_key_t* key,
    uint32_t first, uint32_t sectors, uint16_t reserved, uint64_t deadline_ms);
/* Uses the exact object pin/client/request/epoch/deadline supplied by its host.
 * No fresh snapshot, lease renewal, legacy fallback or implicit recovery.
 * The caller's admission remains unchanged; the short token belongs to tx. */
int reist_fat32_transaction_begin_owned(reist_fat32_transaction_t* transaction,
    const reist_fat32_owned_transaction_io_t* io,
    const reist_file_object_owned_request_t* admission,
    uint32_t first, uint32_t sectors, uint16_t reserved);
int reist_fat32_transaction_stage(reist_fat32_transaction_t* transaction,
    uint32_t sector, const void* data);
/* Pure host transform of an exact, sorted <=20-sector manifest. Reads only
 * these targets, coalesces adjacent runs through existing bounded transport,
 * and gives the unchanged undo core the SAME unmodified before-images.
 * Empty owned transaction only, no callback reentry or persistent effects.
 * Caller still validates the entire resulting plan before finish(true). */
typedef int (*reist_fat32_stage_image_fn)(void* context, uint32_t sector, uint8_t* bytes);
int reist_fat32_transaction_stage_images(reist_fat32_transaction_t* transaction,
    const uint32_t* sectors, uint32_t count, reist_fat32_stage_image_fn image, void* context);
int reist_fat32_transaction_read(reist_fat32_transaction_t* transaction,
    uint32_t sector, void* data);
/* Owned pre-commit identity check: read actual media, not this transaction's
 * pending after-image. Same token/range/deadline; no new raw IO authority. */
int reist_fat32_transaction_read_media(reist_fat32_transaction_t* transaction,
    uint32_t sector, void* data);
/* Same fresh, pre-commit transport; bounded contiguous reads only. */
int reist_fat32_transaction_read_media_many(reist_fat32_transaction_t* transaction,
    uint32_t sector, uint32_t count, void* data);
/* Explicit sync of an empty owned transaction, not an early flush of staged
 * changes. Host validates the live object first and must always finish/revoke.
 * One mediated durability command; normal RSTJ commits retain four barriers. */
int reist_fat32_transaction_flush_owned(reist_fat32_transaction_t* transaction);
/* Finishes/revokes the short reservation even after a failed commit. Never
 * retries an uncertain transaction or silently reacquires authority. */
int reist_fat32_transaction_finish(reist_fat32_transaction_t* transaction,
                                   bool commit, uint32_t* outcome);
#endif
