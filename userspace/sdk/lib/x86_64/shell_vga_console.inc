/* Included by the selected ordinary shell supervisor, never an alternate shell. */
#include <reist/x86_64/vga_console.h>
#include <reist/x86_64/input.h>
extern const unsigned char reist_native_vga_image[];
extern const size_t reist_native_vga_image_bytes;
static uint64_t session_vga_owner,session_vga_epoch,session_vga_input_epoch;
static uint64_t session_vga_checked;
static uint64_t session_vga_recovery_end;
static unsigned session_vga_busy,session_vga_disabled,session_vga_live;
static int session_vga_pending;
/* Host may select only before the first supervisor GETPID. No public ABI,
 * external file, shell command or new authority. 1 first crash; 2 all hang. */
volatile uint64_t reist_vga_fault_selection[4] __attribute__((section(".data.memory_witness")))={
    UINT64_C(0x31414756434a5253),1,0,0};
static int64_t session_vga_control(unsigned operation) {
    reist_vga_request_v1 q={1,64,operation,0,session_vga_owner,
        operation==REIST_VGA_BIND?0:session_vga_epoch,0,0,0,{0,0}};
    return reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,33,(uintptr_t)&q);
}
static int64_t session_vga_input(unsigned operation) {
    reist_input_request_v1 q={1,64,operation,0,session_vga_owner,
        operation==REIST_INPUT_BIND?0:session_vga_input_epoch,0,0,{0,0}};
    return reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,31,(uintptr_t)&q);
}
static void session_vga_retire(void) {
    session_vga_live=0;session_vga_pending=0;session_vga_recovery_end=0;
    if(session_vga_epoch) {
        if(session_vga_control(REIST_VGA_REVOKE))session_stop(-5);
        session_vga_epoch=0;
    }
    if(session_vga_input_epoch) {
        if(session_vga_input(REIST_INPUT_FENCE))session_stop(-5);
        session_vga_input_epoch=0;
    }
    if(session_vga_owner) {
        if(service_task(0,3,session_vga_owner,0))session_stop(-5);
        int64_t r=service_task(0,2,session_vga_owner,1000);
        if(r<0||(uint64_t)r>>32>3)session_stop(-5);
        session_vga_owner=0;
    }
}
static int session_vga_start(uint64_t end) {
    if(session_vga_owner||session_vga_epoch||session_vga_input_epoch)return -16;
    if(session_now()>=end)return -110;
    char hi[9],lo[9];session_hex(hi,(uint32_t)(end>>32));session_hex(lo,(uint32_t)end);
    if(reist_vga_fault_selection[0]!=UINT64_C(0x31414756434a5253)||
       reist_vga_fault_selection[1]!=1||reist_vga_fault_selection[2]>2||
       reist_vga_fault_selection[3]==UINT64_MAX)return -22;
    char mode[2]={'0',0};
    if(reist_vga_fault_selection[2]==1&&!reist_vga_fault_selection[3])mode[0]='u';
    if(reist_vga_fault_selection[2]==2)mode[0]='h';
    const char *args[]={"vga",hi,lo,mode};reist_task_startup_v1_t startup;
    int r=reist_x64_startup_init(&startup,4,args);
    if(!r)r=reist_x64_image_prepare_v2(session_prepared,reist_native_vga_image,reist_native_vga_image_bytes);
    int64_t child=r;
    if(!r) {
        reist_task_profile_v1_t profile={1,40,{(1ULL<<9)|(1ULL<<22)|(1ULL<<41)|(1ULL<<42),1ULL<<49,0},0};
        child=reist_x64_task_import_periodic(session_prepared,&profile,32,1000,&startup);
    }
    session_zero(session_prepared,SESSION_PREPARED_BYTES);session_zero(&startup,sizeof startup);
    if(child<0)return (int)child;
    session_vga_owner=(uint64_t)child;
    reist_vga_fault_selection[3]++;
    if((uint32_t)child!=4||!((uint64_t)child>>32)||(uint64_t)child>>32>0x7fffffff)session_stop(-5);
    int64_t bound=session_vga_control(REIST_VGA_BIND);
    if(bound<=0) { session_vga_retire(); return bound<0?(int)bound:-71; }
    session_vga_epoch=(uint64_t)bound;
    bound=session_vga_input(REIST_INPUT_BIND);
    if(bound<=0) { session_vga_retire(); return bound<0?(int)bound:-71; }
    session_vga_input_epoch=(uint64_t)bound;
    r=-110;
    for(unsigned tries=0;tries<200&&session_now()<end;tries++) {
        r=(int)session_vga_control(REIST_VGA_STATUS);
        if(!r) { session_vga_checked=session_now(); session_vga_live=1; return 0; }
        if(r!=-11)break;
        if(SESSION_S1(SLEEP_MS,10))session_stop(-5);
    }
    session_vga_retire();return r==-11?-110:r;
}
static void session_vga_health(uint64_t now) {
    if(session_vga_busy||session_vga_disabled||!session_vga_live||session_vga_pending)return;
    if(now<session_vga_checked)session_stop(-5);
    if(now-session_vga_checked<100)return;
    session_vga_checked=now;
    int r=(int)session_vga_control(REIST_VGA_STATUS);
    if(!r)return;
    if(r!=-32&&r!=-110)session_stop(r);
    session_vga_pending=r;
    /* Waiting for a safe shell boundary never renews the recovery budget. */
    session_vga_recovery_end=now+2000;
}
static void session_vga_poll(uint64_t now) {
    session_vga_health(now);
    if(session_vga_busy||session_vga_disabled||!session_vga_pending)return;
    int r=session_vga_pending;
    session_vga_busy=1;
    uint64_t end=session_vga_recovery_end;
    session_vga_retire();
    uint64_t restart_now=session_now();
    r=restart_now>=end?-110:reist_session_policy_restart(&session_policy,restart_now);
    if(!r) {
        uint64_t storage_end=session_now()+1000;
        if(storage_end>end)storage_end=end;
        r=session_ensure(storage_end,1);
    }
    if(!r)r=session_vga_start(end);
    session_retire();
    if(r) {
        static const char unavailable[]="VGA console unavailable: ";
        char error[9];session_hex(error,(uint32_t)r);
        session_vga_disabled=1;
        session_write(unavailable,sizeof(unavailable)-1);
        session_write(error,8);session_write("\n",1);
    }
    else {
        static const char recovered[]="\nVGA console recovered. Press Enter.\n";
        session_write(recovered,sizeof(recovered)-1);
    }
    session_vga_busy=0;
}
