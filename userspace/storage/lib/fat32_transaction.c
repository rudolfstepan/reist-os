#include "../include/reist/fat32_transaction.h"
#include "../../../lib/libc/string.h"

static int tx_error(reist_fat32_transaction_t* tx, int error) {
    if (!tx->error) tx->error = error;
    return tx->error;
}

static bool tx_io(reist_fat32_transaction_t* tx, uint32_t operation,
                  uint32_t sector, uint32_t count, void* data) {
    if (!tx->active || !tx->token || tx->error) return false;
    /* Ordinary writable objects never repair evidence during attach or stage.
     * Recovery uses the separate host, with its separately admitted token.
     * The unchanged core still validates every journal record and CRC. */
    if (tx->owned && !tx->committing && operation != REIST_STORAGE_JOURNAL_READ) {
        tx_error(tx, -REIST_EACCES);
        return false;
    }
    bool flush = operation == REIST_STORAGE_JOURNAL_FLUSH;
    if (!flush && (sector < tx->first || sector - tx->first >= tx->sectors ||
        !count || count > REIST_STORAGE_JOURNAL_MAX_SECTORS ||
        count > tx->sectors - (sector - tx->first))) {
        tx_error(tx, -REIST_EINVAL);
        return false;
    }
    reist_storage_journal_request_t request = {
        REIST_STORAGE_JOURNAL_VERSION, sizeof(request), operation, tx->token,
        tx->resource, sector, count, 0
    };
    if (operation == REIST_STORAGE_JOURNAL_WRITE_DEFERRED) tx->attempted = true;
    int result = tx->io.transfer(tx->io.context, &request, data);
    if (result) tx_error(tx, result);
    return !result;
}

static bool tx_read(void* context, unsigned short base, uint32_t sector,
                    void* data, bool master) {
    reist_fat32_transaction_t* tx = context;
    if (tx->staging) {
        if (base || !master || !data || !tx->active || !tx->owned ||
            tx->committing || tx->attempted || tx->error || !tx->stage_count ||
            tx->stage_count > ATA_JOURNAL_MAX_ENTRIES || sector < tx->stage_first ||
            sector-tx->stage_first >= tx->stage_count) return false;
        memcpy(data, tx->stage_before[sector-tx->stage_first], ATA_JOURNAL_SECTOR_SIZE);
        return true;
    }
    return !base && master && tx_io(context, REIST_STORAGE_JOURNAL_READ, sector, 1, data);
}
static bool tx_write_many(void* context, unsigned short base, uint32_t sector,
                          uint32_t count, const void* data, bool master) {
    return !base && master && tx_io(context, REIST_STORAGE_JOURNAL_WRITE_DEFERRED,
                                    sector, count, (void*)data);
}
static bool tx_write(void* context, unsigned short base, uint32_t sector,
                     const void* data, bool master) {
    return tx_write_many(context, base, sector, 1, data, master);
}
static bool tx_flush(void* context, unsigned short base, bool master) {
    return !base && master && tx_io(context, REIST_STORAGE_JOURNAL_FLUSH, 0, 0, NULL);
}
static bool tx_write_sync(void* context, unsigned short base, uint32_t sector,
                          const void* data, bool master) {
    return tx_write(context, base, sector, data, master) && tx_flush(context, base, master);
}
static bool tx_commit_begin(void* context, unsigned short base, bool master) {
    const reist_fat32_transaction_t* tx = context;
    return !base && master && tx->active && !tx->error;
}
static bool tx_commit_end(void* context, unsigned short base, bool master, bool commit) {
    return commit && tx_flush(context, base, master);
}
static const ata_journal_transport_t tx_transport = {
    .read = tx_read, .write = tx_write_sync, .commit_write = tx_write_sync,
    .write_deferred = tx_write, .write_sectors_deferred = tx_write_many,
    .flush = tx_flush, .commit_begin = tx_commit_begin,
    .commit_write_deferred = tx_write, .commit_write_sectors_deferred = tx_write_many,
    .commit_end = tx_commit_end
};

static bool tx_geometry_valid(uint32_t first, uint32_t sectors, uint16_t reserved) {
    return sectors && sectors <= UINT32_MAX - first &&
        reserved >= ATA_JOURNAL_DATA_OFFSET + ATA_JOURNAL_MAX_ENTRIES && reserved <= sectors;
}

static int tx_start(reist_fat32_transaction_t* tx, const reist_fat32_transaction_io_t* io,
    const reist_file_object_guard_request_t* request, uint32_t first, uint32_t sectors,
    uint16_t reserved, const reist_file_object_owned_request_t* admission) {
    memset(tx, 0, sizeof(*tx));
    tx->io = *io;
    tx->resource = request->keys[0].resource;
    tx->token = request->token;
    tx->first = first;
    tx->sectors = sectors;
    tx->reserved = reserved;
    tx->active = true;
    tx->owned = admission != NULL;
    if (admission) tx->admission = *admission;
    ata_undo_journal_init(&tx->journal, &tx_transport, tx);
    if (!ata_undo_journal_attach(&tx->journal, 0, true, first, sectors, reserved) ||
        !tx->journal.enabled || !ata_undo_journal_transaction_begin(&tx->journal)) {
        tx_error(tx, -REIST_EIO);
        uint32_t outcome;
        return reist_fat32_transaction_finish(tx, false, &outcome);
    }
    return 0;
}

int reist_fat32_transaction_begin(reist_fat32_transaction_t* tx,
    const reist_fat32_transaction_io_t* io, const reist_file_object_key_t* key,
    uint32_t first, uint32_t sectors, uint16_t reserved, uint64_t deadline_ms) {
    if (!tx || !io || !io->guard || !io->transfer || !key ||
        key->kind != REIST_FILE_OBJECT_FAT32 || !tx_geometry_valid(first, sectors, reserved) ||
        !deadline_ms) return -REIST_EINVAL;
    if (tx->active) return -REIST_EBUSY;
    reist_file_object_guard_request_t request = {0};
    request.version = REIST_FILE_OBJECT_VERSION;
    request.struct_size = sizeof(request);
    request.operation = REIST_FILE_OBJECT_SNAPSHOT;
    int result = io->guard(io->context, &request);
    if (result) return result;
    request.operation = REIST_FILE_OBJECT_MUTATION_BEGIN;
    request.keys[0] = *key;
    request.flags = REIST_FILE_OBJECT_EXCLUSIVE | REIST_FILE_OBJECT_EXTERNAL_JOURNAL;
    request.deadline_ms = deadline_ms;
    result = io->guard(io->context, &request);
    if (result) return result;
    return tx_start(tx, io, &request, first, sectors, reserved, NULL);
}

int reist_fat32_transaction_begin_owned(reist_fat32_transaction_t* tx,
    const reist_fat32_owned_transaction_io_t* io,
    const reist_file_object_owned_request_t* admission,
    uint32_t first, uint32_t sectors, uint16_t reserved) {
    if (!tx || !io || !io->base.guard || !io->base.transfer || !io->owned || !admission ||
        !tx_geometry_valid(first, sectors, reserved)) return -REIST_EINVAL;
    if (tx->active) return -REIST_EBUSY;
    const reist_file_object_guard_request_t* base = &admission->base;
    const reist_file_object_key_t empty = {0};
    if (base->version != REIST_FILE_OBJECT_OWNED_VERSION || base->struct_size != sizeof(*admission) ||
        base->operation != REIST_FILE_OBJECT_MUTATION_BEGIN ||
        base->flags != (REIST_FILE_OBJECT_EXCLUSIVE | REIST_FILE_OBJECT_EXTERNAL_JOURNAL) ||
        !base->epoch || !base->deadline_ms || base->token || base->reserved ||
        base->client_pid <= 0 || !base->client_generation || base->keys[0].kind != REIST_FILE_OBJECT_FAT32 ||
        base->keys[0].reserved || memcmp(&base->keys[1], &empty, sizeof(empty)) ||
        !admission->pin || !admission->request || admission->reserved[0] || admission->reserved[1])
        return -REIST_EINVAL;
    reist_file_object_owned_request_t request = *admission;
    int result = io->owned(io->base.context, &request);
    if (result) return result;
    return tx_start(tx, &io->base, &request.base, first, sectors, reserved, admission);
}

int reist_fat32_transaction_stage(reist_fat32_transaction_t* tx,
    uint32_t sector, const void* data) {
    if (!tx || !tx->active) return -REIST_ESTALE;
    if (tx->staging) return tx_error(tx, -REIST_EBUSY);
    if (tx->error) return tx->error;
    /* Otherwise the core deliberately selects its legacy direct/automatic
     * write mode. A file-object adapter must never enter that fallback. */
    if (!tx->journal.enabled || tx->journal.transaction_depth != 1)
        return tx_error(tx, -REIST_EIO);
    if (!data || sector < tx->first || sector - tx->first >= tx->sectors)
        return tx_error(tx, -REIST_EINVAL);
    if (!ata_undo_journal_write_sector(&tx->journal, 0, sector, data, true))
        return tx_error(tx, -REIST_EIO);
    return 0;
}

int reist_fat32_transaction_stage_images(reist_fat32_transaction_t* tx,
    const uint32_t* sectors, uint32_t count, reist_fat32_stage_image_fn image, void* context) {
    if (!tx || !tx->active) return -REIST_ESTALE;
    if (tx->error) return tx->error;
    if (!tx->owned || tx->staging || tx->committing || tx->attempted ||
        !tx->journal.enabled || tx->journal.transaction_depth != 1 || tx->journal.entry_count)
        return tx_error(tx, -REIST_EBUSY);
    if (!sectors || !image || !count || count > ATA_JOURNAL_MAX_ENTRIES)
        return tx_error(tx, -REIST_EINVAL);
    uint32_t targets[ATA_JOURNAL_MAX_ENTRIES];
    memcpy(targets, sectors, count*sizeof(*targets));
    for (unsigned i=0; i<count; ++i) {
        uint32_t lba=targets[i];
        if (lba < tx->first || lba-tx->first >= tx->sectors || (i && targets[i-1]>=lba) ||
            (lba >= tx->journal.header_lba && lba < tx->journal.data_lba+ATA_JOURNAL_MAX_ENTRIES) ||
            lba == tx->journal.mirror_lba) return tx_error(tx, -REIST_EINVAL);
    }
    tx->staging = true;
    for (unsigned first=0; first<count && !tx->error;) {
        unsigned end=first+1;
        while (end<count && targets[end] == targets[end-1]+1) ++end;
        tx->stage_first=targets[first]; tx->stage_count=end-first;
        if (!tx_io(tx, REIST_STORAGE_JOURNAL_READ, tx->stage_first, tx->stage_count, tx->stage_before)) break;
        for (unsigned i=first; i<end && !tx->error; ++i) {
            memcpy(tx->stage_after, tx->stage_before[i-first], ATA_JOURNAL_SECTOR_SIZE);
            int result=image(context,targets[i],tx->stage_after);
            if (result) tx_error(tx,result<0 ? result : -REIST_EIO);
            if (!tx->error && !ata_undo_journal_write_sector(&tx->journal,0,targets[i],tx->stage_after,true))
                tx_error(tx,-REIST_EIO);
        }
        first=end;
    }
    tx->staging=false; tx->stage_first=tx->stage_count=0;
    memset(tx->stage_before,0,sizeof(tx->stage_before));
    memset(tx->stage_after,0,sizeof(tx->stage_after));
    return tx->error;
}

int reist_fat32_transaction_read(reist_fat32_transaction_t* tx,
    uint32_t sector, void* data) {
    if (!tx || !tx->active) return -REIST_ESTALE;
    if (tx->staging) return tx_error(tx, -REIST_EBUSY);
    if (tx->error) return tx->error;
    if (!data || sector < tx->first || sector - tx->first >= tx->sectors)
        return tx_error(tx, -REIST_EINVAL);
    if (!ata_undo_journal_read_sector(&tx->journal, 0, sector, data, true))
        return tx_error(tx, -REIST_EIO);
    return 0;
}

int reist_fat32_transaction_read_media(reist_fat32_transaction_t* tx,
    uint32_t sector, void* data) {
    return reist_fat32_transaction_read_media_many(tx,sector,1,data);
}

int reist_fat32_transaction_read_media_many(reist_fat32_transaction_t* tx,
    uint32_t sector, uint32_t count, void* data) {
    if (!tx || !tx->active) return -REIST_ESTALE;
    if (tx->staging) return tx_error(tx, -REIST_EBUSY);
    if (tx->error) return tx->error;
    if (!tx->owned || tx->committing || !data) return tx_error(tx, -REIST_EACCES);
    if (!tx_io(tx, REIST_STORAGE_JOURNAL_READ, sector, count, data)) return tx_error(tx, -REIST_EIO);
    return 0;
}

int reist_fat32_transaction_flush_owned(reist_fat32_transaction_t* tx) {
    if (!tx || !tx->active) return -REIST_ESTALE;
    if (tx->staging) return tx_error(tx, -REIST_EBUSY);
    if (tx->error) return tx->error;
    if (!tx->owned || tx->committing || tx->attempted || !tx->journal.enabled ||
        tx->journal.transaction_depth != 1 || tx->journal.entry_count) return tx_error(tx, -REIST_EACCES);
    /* A failed/lost flush cannot assert durability. Kernel mediation still
     * distinguishes rejection before command issue from a possible effect. */
    tx->committing = true; tx->attempted = true;
    bool success = tx_io(tx, REIST_STORAGE_JOURNAL_FLUSH, 0, 0, NULL);
    tx->committing = false;
    return success ? 0 : tx_error(tx, -REIST_EIO);
}

int reist_fat32_transaction_finish(reist_fat32_transaction_t* tx,
                                   bool commit, uint32_t* outcome) {
    if (!tx || !tx->active || !outcome) return -REIST_EINVAL;
    if (tx->staging) return tx_error(tx, -REIST_EBUSY);
    if (!tx->error && (!tx->journal.enabled || tx->journal.transaction_depth != 1))
        tx_error(tx, -REIST_EIO);
    tx->committing = commit && !tx->error;
    if (tx->journal.transaction_depth &&
        !ata_undo_journal_transaction_end(&tx->journal, commit && !tx->error))
        tx_error(tx, -REIST_EIO);
    tx->committing = false;
    *outcome = !tx->attempted ? REIST_FILE_OBJECT_NO_EFFECT :
        tx->error ? REIST_FILE_OBJECT_UNKNOWN : REIST_FILE_OBJECT_DURABLE_COMMIT;
    reist_file_object_guard_request_t request = {0};
    request.version = REIST_FILE_OBJECT_VERSION;
    request.struct_size = sizeof(request);
    request.operation = REIST_FILE_OBJECT_MUTATION_END;
    request.flags = *outcome;
    request.token = tx->token;
    int result = tx->io.guard(tx->io.context, &request);
    if (result) {
        tx_error(tx, result);
        /* Malformed/non-durable finish must not leave an invisible owner.
         * Explicit UNKNOWN is the only fallback; never reacquire or replay. */
        request.flags = *outcome = REIST_FILE_OBJECT_UNKNOWN;
        (void)tx->io.guard(tx->io.context, &request);
    }
    tx->active = false;
    tx->token = 0;
    tx->last_outcome = *outcome;
    return tx->error;
}
