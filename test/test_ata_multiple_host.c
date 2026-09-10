#undef NDEBUG
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "drivers/block/ata.h"

/* Report a normal failing exit, never raise a native Windows abort dialog. */
#undef assert
#define assert(condition) do { if (!(condition)) { fprintf(stderr,"ATA:%u %s\n",(unsigned)__LINE__,#condition); exit(1); } } while(0)

#define ATA_WAIT_TIMEOUT_MS 500U
#define ATA_POLL_DELAY_MS 1U
drive_t detected_drives[MAX_DRIVES];
typedef struct {
    uint16_t base; uint32_t lba; bool is_master, valid; uint8_t data[512];
} ata_cache_entry_t;
static ata_cache_entry_t caches[32];
static uint32_t consecutive_read_failures;
static uint64_t now;
static uint32_t sleeps, spins, commands, identifies, sets, transferred;
static uint32_t written_blocks, written_sectors, read_blocks, live_checks, deny_check, expire_check, illegal_io;
static bool authority_lost, memory_io;
static uint8_t media[256][512];
static uint32_t io_lba;
static uint32_t blocks[128], block_count, busy, step, fail_block;
static uint8_t command, count_register, last_read_command;
static uint8_t reg_values[16];
static unsigned reg_count;
static uint16_t max_word, current_word;
static bool frozen, sleep_fail, sleepable, irqs, in_irq, fail_final, fail_set, fail_identify;
static int task, forced_status;
static uint8_t port_status(void) {
    if (forced_status >= 0) return (uint8_t)forced_status;
    if (busy) { --busy; return 0x81; } /* ERR is not valid under BSY. */
    if (command == ATA_IDENTIFY) return fail_identify ? 0x41 : 0x48;
    if (command == ATA_SET_MULTIPLE_MODE) return fail_set ? 0x41 : 0x40;
    if (command == ATA_READ_MULTIPLE || command == ATA_READ_MULTIPLE_EXT ||
        command == ATA_READ_SECTORS || command == ATA_READ_SECTORS_EXT ||
        command == ATA_WRITE_MULTIPLE || command == ATA_WRITE_MULTIPLE_EXT ||
        command == ATA_WRITE_SECTORS || command == ATA_WRITE_SECTORS_EXT) {
        if (fail_block && block_count == fail_block) return 0x41;
        if (transferred < count_register) return 0x48;
        return fail_final ? 0x41 : 0x40;
    }
    return 0x40;
}
static uint8_t inb(uint16_t port) { (void)port; return port_status(); }
static void outb(uint16_t port, uint8_t value) {
    if (port == ATA_SECTOR_CNT(0x1f0)) count_register=value;
    if (port == ATA_COMMAND(0x1f0)) {
        if(authority_lost || now>=500) ++illegal_io;
        command=value; ++commands;
        if (value==ATA_IDENTIFY) ++identifies;
        else if (value==ATA_SET_MULTIPLE_MODE) {
            ++sets; if (!fail_set) current_word=0x100U | count_register;
        } else { last_read_command=value; transferred=block_count=0; }
    } else if (port >= ATA_SECTOR_CNT(0x1f0) && port <= ATA_LBA_HIGH(0x1f0)) {
        if (reg_count<sizeof(reg_values)) reg_values[reg_count++]=value;
    }
}
static void insw(uint16_t port, void *buffer, unsigned words) {
    (void)port;
    if (command==ATA_IDENTIFY) {
        assert(words==256); uint16_t *data=buffer;
        memset(data,0,512); data[0]=0x40; data[47]=max_word; data[59]=current_word;
        command=0; return;
    }
    assert(words && words%256==0 && words<=128*256);
    if(authority_lost || now>=500) ++illegal_io;
    assert(block_count<128); blocks[block_count++]=words/256;
    ++read_blocks;
    for (unsigned i=0;i<words/256;i++)
        if(memory_io)memcpy((uint8_t*)buffer+i*512,media[(io_lba+transferred+i)%256],512);
        else memset((uint8_t *)buffer+i*512,(int)(transferred+i+1),512);
    transferred+=words/256;
}
static void outsw(uint16_t port,const void* buffer,unsigned words) {
    (void)port;
    if(authority_lost || now>=500) ++illegal_io;
    assert(command==ATA_WRITE_MULTIPLE || command==ATA_WRITE_MULTIPLE_EXT ||
        command==ATA_WRITE_SECTORS || command==ATA_WRITE_SECTORS_EXT);
    uint32_t block=command==ATA_WRITE_MULTIPLE || command==ATA_WRITE_MULTIPLE_EXT ? current_word&255U : 1U;
    uint32_t expected=count_register-transferred;if(expected>block)expected=block;
    assert(words==expected*256U && expected && block_count<128);
    blocks[block_count++]=expected;++written_blocks;written_sectors+=expected;
    for(unsigned i=0;i<expected;++i)memcpy(media[(io_lba+transferred+i)%256],(const uint8_t*)buffer+i*512,512);
    transferred+=expected;
}
uint16_t ata_control_port_for_base(uint16_t base) { return base+0x206; }
static void ata_selection_delay(uint16_t base) {
    for (unsigned i=0;i<4;i++) (void)inb(ATA_ALT_STATUS(base));
}
static uint64_t pit_monotonic_ms(void) { return now; }
static bool scheduler_can_sleep(void) { return sleepable; }
static int scheduler_current_task_id(void) { return task; }
static bool irq_enabled(void) { return irqs; }
static bool irq_in_context(void) { return in_irq; }
static int scheduler_sleep_ms(uint32_t ms) {
    ++sleeps; if (!frozen) now+=step ? step : ms;
    return sleep_fail ? -1 : 0;
}
static void pit_delay(uint32_t ms) { ++spins; if (!frozen) now+=ms; }
static bool ata_select_target(uint16_t base, uint8_t head, uint32_t ms) {
    (void)base; (void)head; (void)ms; return true;
}
static bool wait_for_drive_data_ready(uint16_t base,uint32_t timeout) {
    (void)base;(void)timeout;return (port_status()&0xc9)==0x48;
}
static bool wait_for_drive_ready(uint16_t base,uint32_t timeout) {
    (void)base;(void)timeout;return (port_status()&0xc9)==0x40;
}
static int ata_resource_index(uint16_t base, bool master) {
    return base==0x1f0 && master ? 0 : -1;
}
static ata_cache_entry_t *ata_cache_slot(uint16_t base, uint32_t lba, bool master) {
    (void)base; (void)master; return &caches[lba%32];
}
/* PRODUCTION */
static drive_t partition_drive;
static unsigned partition_on,transactions,transaction_ends,ahci_calls,pending_calls;
static bool journal_active,pending_view;
static drive_t *ata_compat_partition_drive(uint16_t base) {
    (void)base; return partition_on ? &partition_drive : NULL;
}
static drive_t *ata_partition_translate(drive_t *part,uint32_t lba,uint32_t *absolute) {
    if(lba>=part->sectors || lba>UINT32_MAX-100U) return NULL;
    *absolute=lba+100U; return &detected_drives[0];
}
static drive_t *ata_compat_ahci_drive(uint16_t base) {
    return base==0x1f0 && detected_drives[0].type==DRIVE_TYPE_AHCI ? &detected_drives[0] : NULL;
}
static bool ata_transaction_begin(void) { ++transactions; return true; }
static void ata_transaction_end(void) { ++transaction_ends; }
bool ata_journal_transaction_active(void) { return journal_active; }
static bool ata_journal_range_has_pending(uint16_t base,uint32_t lba,uint32_t count,bool master) {
    (void)base; (void)lba; (void)count; (void)master; return pending_view;
}
static bool ata_read_pending_range(uint16_t base,uint32_t lba,uint32_t count,void *buffer,bool master) {
    (void)base; (void)lba; (void)master; assert(count<=ATA_PIO_MAX_SECTORS);
    ++pending_calls; memset(buffer,0xA5,count*512U); return true;
}
static bool ahci_read_sectors(drive_t *drive,uint32_t lba,uint32_t count,void *buffer) {
    (void)drive; (void)lba; assert(count<=ATA_PIO_MAX_SECTORS);
    ++ahci_calls; memset(buffer,0x5A,count*512U); return true;
}
/* ADAPTER */
static void reset(void) {
    memset(caches,0,sizeof(caches)); memset(detected_drives,0,sizeof(detected_drives));
    detected_drives[0].sectors=UINT32_MAX; detected_drives[0].lba48_supported=true;
    detected_drives[0].type=DRIVE_TYPE_ATA;
    detected_drives[0].base=0x1f0; detected_drives[0].is_master=true;
    partition_on=transactions=transaction_ends=ahci_calls=pending_calls=0;
    journal_active=pending_view=false;
    memset(&partition_drive,0,sizeof(partition_drive)); partition_drive.sectors=200;
    now=sleeps=spins=commands=identifies=sets=transferred=0;
    block_count=busy=step=fail_block=0; command=count_register=last_read_command=0;
    max_word=0x8010; current_word=0x110; frozen=sleep_fail=false;
    sleepable=irqs=true; in_irq=fail_final=fail_set=fail_identify=false; task=1;
    reg_count=0; memset(reg_values,0,sizeof(reg_values));
    forced_status=-1;
    written_blocks=written_sectors=read_blocks=live_checks=deny_check=expire_check=illegal_io=0;
    authority_lost=memory_io=false;io_lba=0;memset(media,0,sizeof(media));
}
static unsigned cache_count(void) {
    unsigned count=0; for(unsigned i=0;i<32;i++) count+=caches[i].valid; return count;
}
static int live_admission(void* context,bool effect) {
    (void)context;(void)effect;
    ++live_checks;
    if(live_checks==expire_check) now=500;
    if(live_checks==deny_check || now>=500) authority_lost=true;
    return authority_lost ? -125 : 0;
}
static void multiple_writes(void) {
    uint8_t input[20*512+2],output[20*512+2];
    for(unsigned i=0;i<sizeof(input);++i)input[i]=(uint8_t)(i*17+23);
    for(unsigned extended=0;extended<2;++extended)for(unsigned mode=1;mode<=128;mode*=2)
        for(unsigned count=1;count<=20;++count) {
            reset();memory_io=true;max_word=0x8080;current_word=0x100|mode;
            ata_journal_admission_t admission={live_admission,NULL,0};
            int block=ata_pio_read_block_size_checked(0x1f0,true,500,&admission);
            assert(block==(int)mode);
            uint32_t lba=extended ? ATA_LBA28_LIMIT-1 : 5;
            io_lba=lba;
            assert(ata_write_sectors_pio_mode_checked(0x1f0,lba,count,input+1,true,500,&admission,block));
            assert(written_sectors==count && written_blocks==(count+mode-1)/mode && !illegal_io);
            assert(last_read_command==(lba+count-1>=ATA_LBA28_LIMIT ? (mode>1?0x39:0x34) : (mode>1?0xc5:0x30)));
            memset(output,0xEE,sizeof(output));
            assert(ata_read_sectors_pio_mode_checked(0x1f0,lba,count,output+1,true,500,&admission,block));
            assert(identifies==1 && !sets && read_blocks==(count+mode-1)/mode);
            assert(!memcmp(input+1,output+1,count*512) && output[0]==0xEE && output[count*512+1]==0xEE);
        }
    /* Every denial/expiry point before and between the actual DRQ blocks.
     * No command/data after refusal, and no transfer replay/fallback. */
    for(unsigned expiry=0;expiry<2;++expiry)for(unsigned cut=1;cut<=3;++cut) {
        reset();current_word=0x110;
        if(expiry)expire_check=cut;else deny_check=cut;
        ata_journal_admission_t a={live_admission,NULL,0};
        assert(!ata_write_sectors_pio_mode_checked(0x1f0,5,20,input+1,true,500,&a,16));
        assert(authority_lost && !illegal_io && commands<=1 && written_sectors<=16);
    }
    for(unsigned mode=0;mode<5;++mode) {
        reset();ata_journal_admission_t a={live_admission,NULL,0};
        int invalid[]={0,-1,3,129,256};
        assert(!ata_write_sectors_pio_mode_checked(0x1f0,0,20,input,true,500,&a,invalid[mode]));
        assert(!commands && !written_sectors);
    }
    reset();assert(!ata_write_sectors_pio_mode_checked(0x1f0,0,20,input,true,500,NULL,16) && !commands);
    reset();fail_block=1;ata_journal_admission_t a={live_admission,NULL,0};
    assert(!ata_write_sectors_pio_mode_checked(0x1f0,0,20,input,true,500,&a,16));
    assert(written_sectors==16 && commands==1);
    reset();fail_final=true;a=(ata_journal_admission_t){live_admission,NULL,0};
    assert(!ata_write_sectors_pio_mode_checked(0x1f0,0,20,input,true,500,&a,16));
    assert(written_sectors==20 && commands==1);
    reset();assert(ata_write_sectors_pio_deferred_checked(0x1f0,0,20,input,true,500,NULL));
    assert(!identifies && written_blocks==20 && last_read_command==ATA_WRITE_SECTORS);
    puts("ATA_MULTIPLE_WRITE_OK cases=320 fresh-mode shared-readback fail-closed legacy-unchanged");
}
int main(void) {
    multiple_writes();
    uint8_t bytes[128*512+2];
    for(unsigned part=0;part<2;++part) {
        reset(); partition_on=part;
        assert(ata_read_batch_capacity(0x1f0,true)==128);
        assert(ata_read_sectors(0x1f0,12,128,bytes,true));
        assert(transactions==1 && transaction_ends==1 && identifies==1 && !ahci_calls);
        reset(); partition_on=part; detected_drives[0].type=DRIVE_TYPE_AHCI;
        assert(ata_read_batch_capacity(0x1f0,true)==20);
        assert(!ata_read_sectors(0x1f0,12,21,bytes,true) && !transactions);
        assert(ata_read_sectors(0x1f0,12,20,bytes,true));
        assert(ahci_calls==1 && transactions==1 && transaction_ends==1 && !commands);
        reset(); partition_on=part; journal_active=pending_view=true;
        assert(ata_read_batch_capacity(0x1f0,true)==20);
        assert(!ata_read_sectors(0x1f0,12,128,bytes,true));
        assert(transactions==transaction_ends && !commands && !pending_calls);
        assert(ata_read_sectors(0x1f0,12,20,bytes,true));
        assert(pending_calls==1 && bytes[0]==0xA5 && !commands);
        reset(); partition_on=part; fail_final=true;
        assert(!ata_read_sectors(0x1f0,12,128,bytes,true));
        assert(transactions==1 && transaction_ends==1 && !cache_count());
    }
    reset(); partition_on=1;
    assert(!ata_read_sectors(0x1f0,195,6,bytes,true) && !transactions);
    reset(); assert(ata_read_batch_capacity(0x1f0,true)==128); journal_active=true;
    assert(!ata_read_sectors(0x1f0,0,21,bytes,true) && !commands && transactions==transaction_ends);
    reset(); assert(!ata_read_sectors(0x1f0,0,129,bytes,true) && !transactions);
    assert(!ata_read_sectors(0x1f0,0,0,bytes,true) && !transactions);
    assert(!ata_read_sectors(0x1f0,0,1,NULL,true) && !transactions);
    reset(); memset(bytes,0xEE,sizeof(bytes));
    assert(ata_read_sectors_pio_impl(0x1f0,12,128,bytes+1,true));
    assert(identifies==1 && block_count==8 && transferred==128);
    assert(bytes[0]==0xEE && bytes[sizeof(bytes)-1]==0xEE);
    for(unsigned i=0;i<128*512;i++) assert(bytes[i+1]==i/512+1);
    assert(!ata_pio_range_valid(&detected_drives[0],0,21)); /* Write quota unchanged. */
    reset(); max_word=0;
    assert(ata_read_sectors_pio_impl(0x1f0,12,128,bytes,true));
    assert(last_read_command==ATA_READ_SECTORS && block_count==128);
    reset(); fail_block=7;
    assert(!ata_read_sectors_pio_impl(0x1f0,12,128,bytes,true));
    assert(transferred==112 && !cache_count());
    reset(); fail_final=true;
    assert(!ata_read_sectors_pio_impl(0x1f0,12,128,bytes,true) && !cache_count());
    reset(); memset(bytes,0xEE,sizeof(bytes));
    assert(ata_read_sectors_pio_impl(0x1f0,12,20,bytes+1,true));
    assert(identifies==1 && sets==0 && block_count==2);
    assert(blocks[0]==16 && blocks[1]==4 && last_read_command==ATA_READ_MULTIPLE);
    assert(cache_count()==20 && bytes[0]==0xEE && bytes[sizeof(bytes)-1]==0xEE);
    for(unsigned i=0;i<20*512;i++) assert(bytes[i+1]==i/512+1);
    /* Fresh identity after a reset-like mode change; no cached enabled mode. */
    command=0; transferred=block_count=0; current_word=0;
    assert(ata_read_sectors_pio_impl(0x1f0,12,20,bytes,true));
    assert(identifies==2 && sets==1 && current_word==0x110);
    reset(); current_word=0x104;
    assert(ata_read_sectors_pio_impl(0x1f0,12,9,bytes,true));
    assert(block_count==3 && blocks[0]==4 && blocks[1]==4 && blocks[2]==1);
    reset(); assert(ata_read_sectors_pio_impl(0x1f0,ATA_LBA28_LIMIT,3,bytes,true));
    assert(last_read_command==ATA_READ_MULTIPLE_EXT && block_count==1);
    assert(reg_count==8 && reg_values[0]==0 && reg_values[1]==0x10 && reg_values[4]==3);
    reset(); detected_drives[0].lba48_supported=false;
    assert(!ata_read_sectors_pio_impl(0x1f0,ATA_LBA28_LIMIT,3,bytes,true)); assert(!commands);
    reset(); assert(ata_read_sectors_pio_impl(0x1f0,ATA_LBA28_LIMIT-1,3,bytes,true));
    assert(last_read_command==ATA_READ_MULTIPLE_EXT);
    reset(); assert(ata_read_sectors_pio_impl(0x1f0,0,1,bytes,true));
    assert(!identifies && !sets && last_read_command==ATA_READ_SECTORS);
    reset(); max_word=0x8080; current_word=0x180;
    assert(ata_read_sectors_pio_impl(0x1f0,0,20,bytes,true));
    assert(block_count==1 && blocks[0]==20);
    reset(); max_word=0x8080; current_word=0;
    assert(ata_read_sectors_pio_impl(0x1f0,0,20,bytes,true));
    assert(sets==1 && current_word==0x110);
    reset(); assert(ata_program_pio_batch(0x1f0,5,3,true,true,false,false,0));
    assert(last_read_command==ATA_WRITE_SECTORS && count_register==3 && !identifies);
    reset(); assert(ata_program_pio_batch(0x1f0,ATA_LBA28_LIMIT,3,true,true,true,false,0));
    assert(last_read_command==ATA_WRITE_SECTORS_EXT && count_register==3 && !identifies);
    reset(); assert(ata_program_pio_batch(0x1f0,5,20,true,true,false,true,500));
    assert(last_read_command==0xC5 && count_register==20);
    reset(); assert(ata_program_pio_batch(0x1f0,ATA_LBA28_LIMIT,20,true,true,true,true,500));
    assert(last_read_command==0x39 && count_register==20);
    reset(); assert(!ata_read_sectors_pio_impl(0x1f0,UINT32_MAX-1,3,bytes,true)); assert(!commands);
    reset(); assert(!ata_read_sectors_pio_impl(0x1f0,0,129,bytes,true)); assert(!commands);
    reset(); assert(!ata_read_sectors_pio_impl(0x1f0,0,0,bytes,true)); assert(!commands);
    reset(); assert(!ata_read_sectors_pio_impl(0x1f0,0,1,NULL,true)); assert(!commands);
    for(unsigned i=0;i<4;i++) {
        reset(); uint16_t bad[]={0,0x8011,0xff10,0x8001}; max_word=bad[i];
        assert(ata_read_sectors_pio_impl(0x1f0,0,3,bytes,true));
        assert(last_read_command==ATA_READ_SECTORS && block_count==3 && !sets);
    }
    reset(); current_word=0x103;
    assert(ata_read_sectors_pio_impl(0x1f0,0,3,bytes,true));
    assert(last_read_command==ATA_READ_SECTORS && !sets);
    reset(); fail_identify=true;
    assert(!ata_read_sectors_pio_impl(0x1f0,0,20,bytes,true)); assert(commands==1 && !cache_count());
    reset(); current_word=0; fail_set=true;
    assert(!ata_read_sectors_pio_impl(0x1f0,0,20,bytes,true)); assert(commands==2 && !cache_count());
    reset(); fail_block=1;
    assert(!ata_read_sectors_pio_impl(0x1f0,0,20,bytes,true));
    assert(transferred==16 && commands==2 && !cache_count());
    reset(); fail_final=true;
    assert(!ata_read_sectors_pio_impl(0x1f0,0,20,bytes,true)); assert(!cache_count());
    for(unsigned i=0;i<4;i++) {
        reset(); int bad[]={0,0xff,0x41,0x60}; forced_status=bad[i];
        assert(!ata_pio_wait_status(0x1f0,0x08,0,false,5)); assert(!sleeps);
    }
    reset(); forced_status=0x48;
    assert(!ata_pio_wait_status(0x1f0,0x40,0x08,false,5)); assert(!sleeps);
    reset(); busy=1; assert(ata_pio_wait_status(0x1f0,0x40,0x08,false,5));
    assert(sleeps==1 && !spins);
    reset(); busy=1000; frozen=true;
    assert(!ata_pio_wait_status(0x1f0,0x40,0x08,false,5)); assert(sleeps<=502 && !spins);
    reset(); busy=1; step=10;
    assert(!ata_pio_wait_status(0x1f0,0x40,0x08,false,5)); assert(sleeps==1);
    reset(); busy=1; sleep_fail=true;
    assert(!ata_pio_wait_status(0x1f0,0x40,0x08,false,5)); assert(sleeps==1);
    reset(); busy=1; sleepable=false;
    assert(!ata_pio_wait_status(0x1f0,0x40,0x08,false,5)); assert(!sleeps && !spins);
    reset(); busy=1; task=-1;
    assert(ata_pio_wait_status(0x1f0,0x40,0x08,false,5)); assert(spins==1 && !sleeps);
    reset(); busy=1; task=-1; irqs=false;
    assert(!ata_pio_wait_status(0x1f0,0x40,0x08,false,5)); assert(!spins);
    puts("ATA_MULTIPLE_HOST_OK"); return 0;
}
