/* Supervisor glue only. Device sequencing/rendering remain separate Ring3 roles. */
#include <reist/x86_64/video_mode.h>
#include <reist/x86_64/display.h>
extern const unsigned char *const reist_native_video_image;
extern const size_t reist_native_video_image_bytes;
static uint64_t video_driver,video_epoch,video_input_epoch,video_display_epoch,video_end;
static uint32_t video_control;
volatile uint64_t reist_video_fault_selection[4] __attribute__((section(".data.memory_witness")))={
    UINT64_C(0x3145444f4d564b43),1,0,0};
static int64_t video_control_call(unsigned op) {
    reist_video_request_v1 q={1,64,op,0,video_driver,op==REIST_VIDEO_BIND?0:video_epoch,{0}};
    return reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,34,(uintptr_t)&q);
}
static int64_t video_input_call(unsigned op) {
    reist_input_request_v1 q={1,64,op,0,video_driver,op==REIST_INPUT_BIND?0:video_input_epoch,0,0,{0,0}};
    return reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,31,(uintptr_t)&q);
}
static int video_stop(int graceful) {
    uint64_t end=session_now()+2000;
    int result=0,faulted=!graceful;
    if(video_driver && graceful && video_control) {
        x86os_ipc_message_t m={1,140,1,{0}};m.payload[0]='q';
        int64_t r=SESSION_S3(IPC_SEND_TIMEOUT,video_control,&m,0);
        if(r)faulted=1;
        if(r && r!=-11)result=-5;
        if(!r) {
            r=service_task(0,2,video_driver,250);
            if(r>=0) {
                if((uint64_t)r>>32>3)session_stop(-5);
                video_driver_reaped=1;if(r)faulted=1;
            }
            else if(r!=-110)result=-5;
            if(r<0)faulted=1;
        }
    }
    if(video_epoch) {
        int64_t r=video_control_call(REIST_VIDEO_FENCE);
        if(r)result=(int)r;video_epoch=0;
    }
    if(video_input_epoch) {
        if(video_input_call(REIST_INPUT_FENCE))result=-5;
        video_input_epoch=0;
    }
    if(video_driver && !video_driver_reaped) {
        if(service_task(0,3,video_driver,0))session_stop(-5);
        if(service_task(0,2,video_driver,250)<0)session_stop(-5);
    }
    video_driver=0;video_driver_reaped=0;
    if(video_control) {
        if(service_close(0,video_control))session_stop(-5);
        video_control=0;
    }
    if(session_child) {
        if(service_task(0,3,session_child,0))session_stop(-5);
        if(service_task(0,2,session_child,250)<0)session_stop(-5);
        session_child=0;
    }
    video_display_epoch=0;session_video_active=0;
    session_retire();
    /* Fault recovery and VGA recovery share the existing two/10s policy.
     * A normal presentation/return is not a restart. Exhaustion never resets. */
    if(faulted) {
        int charged=reist_session_policy_restart(&session_policy,session_now());
        if(charged && !result)result=charged;
    }
    if(!result && session_now()<end) {
        uint64_t storage_end=session_now()+1000;if(storage_end>end)storage_end=end;
        result=session_ensure(storage_end,1);
        if(!result)result=session_vga_start(end);
        session_retire();
    } else if(!result)result=-110;
    session_vga_busy=0;
    if(result)session_vga_disabled=1;
    return result;
}
static int session_video_start(int argc) {
    if(argc!=1 || session_video_active || video_driver)return -22;
    if(reist_video_fault_selection[0]!=UINT64_C(0x3145444f4d564b43) ||
       reist_video_fault_selection[1]!=1 || reist_video_fault_selection[2]>6 ||
       reist_video_fault_selection[3]==UINT64_MAX)return -22;
    uint64_t end=session_now()+2000;
    session_vga_busy=1;session_vga_retire();
    session_video_active=1;video_end=end+4000;
    const char *args[]={"/video.prg"};reist_task_startup_v1_t startup;
    int r=reist_x64_startup_init(&startup,1,args);
    reist_task_profile_v1_t renderer={1,40,{(1ULL<<9)|(1ULL<<22)|(1ULL<<41)|(1ULL<<42),
                                              1ULL<<49,0},0};
    int64_t child=r?r:reist_x64_task_import_periodic(session_prepared,&renderer,32,1000,&startup);
    session_zero(session_prepared,SESSION_PREPARED_BYTES);
    if(child<0){r=(int)child;goto failed;}
    if((uint32_t)child!=4 || (uint64_t)child>>32>0x7fffffff)session_stop(-5);
    session_child=(uint64_t)child;
    r=service_endpoint(0,&video_control);if(r)goto failed;
    r=reist_x64_image_prepare_v2(session_prepared,reist_native_video_image,reist_native_video_image_bytes);
    if(r)goto failed;
    char hi[9],lo[9],ep[9],mode[2]={'0',0};
    static const char faults[]="0pPgGrR";
    mode[0]=faults[reist_video_fault_selection[2]];
    session_hex(hi,(uint32_t)(end>>32));session_hex(lo,(uint32_t)end);session_hex(ep,video_control);
    const char *driver_args[]={"video-driver",hi,lo,ep,mode};
    r=reist_x64_startup_init(&startup,5,driver_args);if(r)goto failed;
    reist_task_profile_v1_t driver={1,40,{(1ULL<<9)|(1ULL<<22)|(1ULL<<41)|(1ULL<<42)|(1ULL<<54),1ULL<<49,0},0};
    child=reist_x64_task_import_periodic(session_prepared,&driver,32,1000,&startup);
    session_zero(session_prepared,SESSION_PREPARED_BYTES);
    if(child<0){r=(int)child;goto failed;}
    if((uint32_t)child!=5 || (uint64_t)child>>32>0x7fffffff)session_stop(-5);
    video_driver=(uint64_t)child;
    r=(int)SESSION_S3(IPC_DELEGATE,video_control,video_driver>>32,2);if(r)goto failed;
    int64_t bound=video_control_call(REIST_VIDEO_BIND);
    if(bound<=0){r=bound<0?(int)bound:-71;goto failed;}video_epoch=(uint64_t)bound;
    bound=video_input_call(REIST_INPUT_BIND);
    if(bound<=0){r=bound<0?(int)bound:-71;goto failed;}video_input_epoch=(uint64_t)bound;
    r=-110;
    for(unsigned n=0;n<200 && session_now()<end;n++) {
        bound=video_control_call(REIST_VIDEO_STATUS);
        if(bound==REIST_VIDEO_GRAPHICS){r=0;break;}
        if(bound<0){r=(int)bound;break;}
        if(bound!=REIST_VIDEO_PREPARING){r=-71;break;}
        if(SESSION_S1(SLEEP_MS,10))session_stop(-5);
    }
    if(r)goto failed;
    reist_display_request_v1 display={1,64,REIST_DISPLAY_BIND,0,session_child,0,0,0,0,0,0,0,0};
    bound=reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,30,(uintptr_t)&display);
    if(bound<=0){r=bound<0?(int)bound:-71;goto failed;}video_display_epoch=(uint64_t)bound;
    reist_video_fault_selection[3]++;
    session_retire();return (int)(session_child>>32);
failed:
    session_zero(session_prepared,SESSION_PREPARED_BYTES);
    {
        int restored=video_stop(0);char error[9];
        session_write("Video start failed: ",20);session_hex(error,(uint32_t)r);
        session_write(error,8);session_write("; VGA return: ",14);
        session_hex(error,(uint32_t)restored);session_write(error,8);session_write("\n",1);
    }
    return r;
}
static int session_video_wait(int *out) {
    int r=-110;int exit_code=0;
    for(unsigned n=0;n<120 && session_now()<video_end;n++) {
        int64_t health=video_control_call(REIST_VIDEO_STATUS);
        if(health!=REIST_VIDEO_GRAPHICS){r=health<0?(int)health:-71;break;}
        int64_t joined=service_task(0,2,session_child,50);
        if(joined>=0) {
            if((uint64_t)joined>>32>3)session_stop(-5);
            exit_code=(int)(uint32_t)joined;session_child=0;
            r=joined?-5:0;break;
        }
        if(joined!=-110){r=(int)joined;break;}
    }
    int restored=video_stop(!r);
    if(restored) {
        char error[9];session_hex(error,(uint32_t)restored);
        session_write("VGA return failed: ",19);session_write(error,8);session_write("\n",1);
        return restored;
    }
    if(r)return r;
    *out=exit_code;return 0;
}
