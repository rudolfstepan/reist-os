/* Root-only native graphical group supervision. No input decoding or rendering. */
#include <reist/x86_64/graphical_session.h>
#include "graphical_manifest.h"
static reist_graphical_state graphical;
static void *graphical_images[4];
static uint32_t graphical_control,graphical_endpoints[3];
static uint64_t graphical_display,graphical_input;
static unsigned graphical_terminal,graphical_stop_requested;
/* Private pre-entry qualification selector; never modified by a GUI client. */
volatile uint64_t reist_graphical_selection[2] __attribute__((section(".data.memory_witness")))={0x315549474e545352ULL,0};
static unsigned graphical_modes[4],graphical_fault;
static const char *const graphical_paths[4]={"/desktop.prg","/input.prg","/text.prg","/paint.prg"};
static int graphical_send(const reist_graphical_control *q) {
    x86os_ipc_message_t m;session_zero(&m,sizeof(m));m.version=1;m.struct_size=140;m.length=64;
    session_bytes(m.payload,q,64);
    return (int)SESSION_S3(IPC_SEND_TIMEOUT,graphical_control,&m,100);
}
static int graphical_receive(reist_graphical_control *q) {
    x86os_ipc_message_t m;session_zero(&m,sizeof(m));m.version=1;m.struct_size=140;m.length=128;
    int r=(int)SESSION_S3(IPC_RECEIVE_TIMEOUT,graphical_control,&m,0);if(r)return r;
    if(m.version!=1||m.struct_size!=140||m.length!=64)return -71;
    for(unsigned n=64;n<128;n++)if(m.payload[n])return -71;
    session_bytes(q,m.payload,64);
    if(q->version!=1||q->size!=64||q->epoch!=graphical.epoch||q->role>=4||q->reserved)return -71;
    return 0;
}
static uint64_t graphical_hash_clock(void *p){(void)p;return session_now();}
static int graphical_hash_sleep(void *p,unsigned ms){(void)p;return x86os_sleep_ms(ms);}
static const reist_graphical_hash_ops graphical_hash_ops={0,graphical_hash_clock,graphical_hash_sleep};
static int graphical_admit(unsigned role,uint64_t capture_end) {
    if(role>=4||!graphical_images[role])return -22;
    int r=reist_graphical_hash_admit(session_prepared,REIST_GRAPHICAL_PREPARED_HASH_BYTES,
        graphical_hashes[role],&graphical_hash_ops);
    if(!r && session_now()>=capture_end)r=-110;
    if(!r)session_bytes(graphical_images[role],session_prepared,REIST_X64_PREPARED_V2_BYTES);
    session_zero(session_prepared,REIST_X64_PREPARED_V2_BYTES);return r;
}
static void graphical_free(void) {
    for(unsigned n=0;n<4;n++)if(graphical_images[n]) {
        session_zero(graphical_images[n],REIST_X64_PREPARED_V2_BYTES);
        if(SESSION_S1(FREE,graphical_images[n]))session_stop(-5);
        graphical_images[n]=0;
    }
}
static int graphical_capture(uint64_t first_end) {
    if(first_end<REIST_WIDE_FILE_MS || first_end>UINT64_MAX-3*REIST_WIDE_FILE_MS)return -22;
    uint64_t all_end=first_end+3*REIST_WIDE_FILE_MS;
    for(unsigned role=0;role<4;role++) {
        graphical_images[role]=(void*)(uintptr_t)SESSION_S1(MALLOC,REIST_X64_PREPARED_V2_BYTES);
        if((intptr_t)graphical_images[role]<=0){graphical_images[role]=0;return -12;}
        uint64_t capture_end=first_end;
        if(role) {
            x86os_file_info_t info;int r=reist_vfs_stat(graphical_paths[role],&info,1000);if(r)return r;
            if(info.type!=X86OS_FILE)return -22;
            capture_end=session_observation.deadline_ms;
            if(session_operation_deadline)session_stop(-5);
            session_operation_deadline=capture_end;
            r=reist_x64_file_finish_v2(session_prepared,session_workspace,&session_fs,&session_transport,&session_observation);
            session_operation_deadline=0;session_zero(&session_observation,sizeof(session_observation));
            if(r)return session_operation_result(r);
        }
        int r=graphical_admit(role,capture_end);if(r)return r;
        if(session_now()>=all_end)return -110;
    }
    return 0;
}
static int graphical_create(unsigned role,uint32_t endpoint,uint64_t end) {
#if defined(REIST_NATIVE_FULL_DESKTOP) || defined(REIST_NATIVE_FULL_DESKTOP_STARTUP)
    uint64_t now=session_now();
    if(end<REIST_GRAPHICAL_START_MS || now>=end || end-now>REIST_GRAPHICAL_START_MS)return -110;
#endif
#line 68
    if(role>=4 || !endpoint || !graphical_images[role])return -22;
    char ep[9],peer[9],eh[9],el[9],dh[9],dl[9],mode[2]={(char)graphical_modes[role],0};
    session_hex(ep,endpoint);session_hex(peer,role?(uint32_t)(graphical.roles[0].owner>>32):(uint32_t)session_policy.owner);
    session_hex(eh,(uint32_t)(graphical.epoch>>32));session_hex(el,(uint32_t)graphical.epoch);
    session_hex(dh,(uint32_t)(end>>32));session_hex(dl,(uint32_t)end);
    const char *args[]={graphical_paths[role],ep,peer,eh,el,dh,dl,mode};
    reist_task_startup_v1_t startup;int r=reist_x64_startup_init(&startup,8,args);if(r)return r;
    uint64_t mask=(1ULL<<9)|(1ULL<<22)|(1ULL<<40)|(1ULL<<41)|(1ULL<<42)|(1ULL<<53);
    reist_task_profile_v1_t profile={1,40,{mask,0,0},0};
    if(role!=1)profile.masks[0]|=1ULL<<54;
    if(role==0) {
        profile.masks[0]|=(1ULL<<4)|(1ULL<<5)|(1ULL<<15)|(1ULL<<20)|(1ULL<<49)|(1ULL<<52)|(1ULL<<55)|(1ULL<<58);
        profile.masks[1]=(1ULL<<49)|(1ULL<<63);
    } else if(role==1)profile.masks[1]=1ULL<<49;
    int64_t child=reist_x64_task_import_periodic(graphical_images[role],&profile,32,1000,&startup);
    session_zero(&startup,sizeof(startup));if(child<0)return (int)child;
    r=reist_graphical_bind(&graphical,role,(uint64_t)child,session_now());
    if(r)session_stop(-5); /* unexpected slot/identity: root terminal path fences all children */
#if defined(REIST_NATIVE_FULL_DESKTOP) || defined(REIST_NATIVE_FULL_DESKTOP_STARTUP)
    graphical.roles[role].health_ms=end-REIST_GRAPHICAL_START_MS;
#endif
#line 86
    if(!role) {
        session_child=(uint64_t)child;
        return (int)SESSION_S3(IPC_DELEGATE,graphical_control,(uint64_t)child>>32,3);
    }
#ifdef REIST_NATIVE_FULL_DESKTOP
    if(role>=2 && full_backend && full_backend->children[role-2].owner) {
        r=full_graphical_replace_binding(role,(uint64_t)child);if(r)return r;
    }
#endif
    reist_graphical_control q={1,64,REIST_GRAPHICAL_BIND,role,graphical.epoch,1,(uint64_t)child,endpoint,0,0,0};
    return graphical_send(&q);
}
static int graphical_fence_device(unsigned operation,uint64_t owner,uint64_t epoch) {
    if(operation==30) {
        reist_display_request_v1 q={1,64,REIST_DISPLAY_FENCE,0,owner,epoch,0,0,0,0,0,0,0};
        return (int)reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,30,(uintptr_t)&q);
    }
    reist_input_request_v1 q={1,64,REIST_INPUT_FENCE,0,owner,epoch,0,0,{0,0}};
    return (int)reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,31,(uintptr_t)&q);
}
static int graphical_retire(unsigned degraded) {
    uint64_t now=session_now(),end=now+5000;
    if(reist_graphical_isolate(&graphical,0,now))session_stop(-5);
    if(graphical_terminal && reist_x64_terminal_service(7,graphical.roles[0].owner))session_stop(-5);
    graphical_terminal=0;
    if(graphical_display && graphical_fence_device(30,graphical.roles[0].owner,graphical_display))session_stop(-5);
    if(graphical_input && graphical_fence_device(31,graphical.roles[1].owner,graphical_input))session_stop(-5);
    graphical_display=graphical_input=0;
    if(graphical_control && SESSION_S1(IPC_CLOSE,graphical_control))session_stop(-5);
    graphical_control=0;
    /* Compositor terminal retirement also closes its owned single-peer
     * channels. Reap it before cancelling clients or reusing any endpoint. */
    for(unsigned role=0;role<4;role++) {
        reist_graphical_role *v=&graphical.roles[role];
        if(v->phase==REIST_GRAPHICAL_OFF || v->phase==REIST_GRAPHICAL_REAPED)continue;
        if(service_task(0,3,v->owner,0))session_stop(-5);
        int64_t result=service_task(0,2,v->owner,1000);
        if(result<0 || (uint64_t)result>>32>3 || session_now()>=end)session_stop(-5);
        if(reist_graphical_fenced(&graphical,role,v->owner,REIST_GRAPHICAL_FENCE_ALL,session_now()) ||
           reist_graphical_reaped(&graphical,role,v->owner,session_now()))session_stop(-5);
    }
    session_child=0;session_graphical_active=0;session_zero(graphical_endpoints,sizeof(graphical_endpoints));
    if(reist_graphical_finish(&graphical,degraded,session_now()) ||
       reist_x64_terminal_input(REIST_TERMINAL_CHECK,0,0))session_stop(-5);
    return 0;
}
static int graphical_grant(void) {
    uint64_t compositor=graphical.roles[0].owner,driver=graphical.roles[1].owner;
    reist_display_request_v1 display={1,64,REIST_DISPLAY_BIND,0,compositor,0,0,0,0,0,0,0,0};
    int64_t result=reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,30,(uintptr_t)&display);
    if(result<=0)return result<0?(int)result:-5;graphical_display=(uint64_t)result;
    reist_input_request_v1 input={1,64,REIST_INPUT_BIND,0,driver,0,0,0,{0,0}};
    result=reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,31,(uintptr_t)&input);
    if(result<=0)return result<0?(int)result:-5;graphical_input=(uint64_t)result;
    int r=reist_x64_terminal_service(6,compositor);if(r)return r;graphical_terminal=1;
    /* Actual observer denial on the compositor-owned raw-input channel. */
    x86os_ipc_message_t m;session_zero(&m,sizeof(m));m.version=1;m.struct_size=140;m.length=128;
    if(SESSION_S3(IPC_RECEIVE_TIMEOUT,graphical_endpoints[0],&m,0)!=-9 ||
       reist_x64_terminal_input(REIST_TERMINAL_CHECK,0,0)!=-11 || SESSION_S3(READ,0,0,0)!=-11)session_stop(-5);
    reist_graphical_control ready={1,64,REIST_GRAPHICAL_READY,0,graphical.epoch,1,
        graphical.root,0,31,graphical_input,0};
    return graphical_send(&ready);
}
static int graphical_launch(void) {
    uint64_t now=session_now();int r=reist_graphical_begin(&graphical,now);if(r)return r;
    uint64_t end=graphical.start_end;
    if((r=(int)SESSION_S1(IPC_CREATE,&graphical_control)) || (r=graphical_create(0,graphical_control,end)))return r;
    unsigned created=0,confirmed=0,granted=0;
    for(unsigned turn=0;turn<REIST_GRAPHICAL_START_MS/10 && session_now()<end;turn++) {
        for(unsigned n=0;n<8;n++) {
            reist_graphical_control q;r=graphical_receive(&q);
            if(r==-11)break;if(r)return r;
            if(q.type==REIST_GRAPHICAL_HELLO && q.role>=1 && q.role<=3 &&
               q.sequence==1 && !q.flags && !q.value && !q.owner && q.endpoint && !(created&(1U<<q.role))) {
                graphical_endpoints[q.role-1]=q.endpoint;
                r=graphical_create(q.role,q.endpoint,end);if(r)return r;created|=1U<<q.role;
            } else if(q.type==REIST_GRAPHICAL_BOUND && q.role>=1 && q.role<=3 &&
                      q.sequence==1 && !q.flags && !q.value && q.owner==graphical.roles[q.role].owner &&
                      q.endpoint==graphical_endpoints[q.role-1] && created&(1U<<q.role) && !(confirmed&(1U<<q.role))) {
                confirmed|=1U<<q.role;
            } else if(q.type==REIST_GRAPHICAL_READY && q.role==0 && q.sequence==1 &&
                      q.owner==graphical.roles[0].owner && q.flags==31 && !q.endpoint && !q.value && granted) {
                r=reist_graphical_ready(&graphical,graphical.epoch,q.flags,session_now());
                if(!r){session_graphical_active=1;session_write("GRAPHICAL_READY\n",16);}return r;
            } else return -71;
        }
        if(confirmed==14 && !granted){r=graphical_grant();if(r)return r;granted=1;}
#if defined(REIST_NATIVE_FULL_DESKTOP) || defined(REIST_NATIVE_FULL_DESKTOP_STARTUP)
        if(x86os_sleep_ms(50))return -5;
#else
        if(x86os_sleep_ms(10))return -5;
#endif
    }
    return -110;
}
static int graphical_restart_admit(void) {
    int r=reist_graphical_restart(&graphical,&session_policy,session_now());
    if(r)graphical.phase=REIST_GRAPHICAL_DEGRADED;
    return r;
}
static int graphical_replace(unsigned role,unsigned restart) {
    reist_graphical_role *v=&graphical.roles[role];uint64_t old=v->owner;
    if(reist_graphical_isolate(&graphical,role,session_now()) ||
       reist_graphical_fenced(&graphical,role,old,REIST_GRAPHICAL_FENCE_CHANNEL,session_now()))session_stop(-5);
    if(service_task(0,3,old,0))session_stop(-5);
    int64_t result=service_task(0,2,old,1000);
    if(result<0 || (uint64_t)result>>32>3 || reist_graphical_reaped(&graphical,role,old,session_now()))session_stop(-5);
    if(!restart)return 0;
    int r=reist_graphical_restart(&graphical,&session_policy,session_now());if(r)return r;
    reist_graphical_control reaped={1,64,REIST_GRAPHICAL_CLIENT_REAPED,role,graphical.epoch,2,old,0,0,0,0};
    r=graphical_send(&reaped);if(r)return r;
#if defined(REIST_NATIVE_FULL_DESKTOP) || defined(REIST_NATIVE_FULL_DESKTOP_STARTUP)
    uint64_t now=session_now();if(now>UINT64_MAX-REIST_GRAPHICAL_START_MS)return -75;
    uint64_t end=now+REIST_GRAPHICAL_START_MS;unsigned created=0;
#else
    uint64_t end=session_now()+REIST_GRAPHICAL_START_MS;unsigned created=0;
#endif
#line 189
    for(unsigned turn=0;turn<REIST_GRAPHICAL_START_MS/10 && session_now()<end;turn++) {
        reist_graphical_control q;r=graphical_receive(&q);
        if(r==-11){x86os_sleep_ms(10);continue;}if(r)return r;
        if(q.type==REIST_GRAPHICAL_HEALTH) {
            if(q.flags!=1||q.value || q.owner!=graphical.roles[q.role].owner || q.role==role ||
               q.endpoint!=(q.role?graphical_endpoints[q.role-1]:0) ||
               reist_graphical_heartbeat(&graphical,q.role,q.owner,q.epoch,q.sequence,session_now()))return -71;
            continue;
        }
        if(q.role!=role || q.sequence!=1 || q.flags || q.value)return -71;
        if(q.type==REIST_GRAPHICAL_HELLO && q.owner==old && q.endpoint && !created) {
            graphical_endpoints[role-1]=q.endpoint;r=graphical_create(role,q.endpoint,end);if(r)return r;created=1;
            graphical_modes[role]='0';
        } else if(q.type==REIST_GRAPHICAL_BOUND && created && q.owner==v->owner && q.endpoint==graphical_endpoints[role-1])return 0;
        else return -71;
    }
    return -110;
}
static int session_graphical_start(int argc,uint64_t capture_end) {
    if(argc!=1)return -22;
    if(!graphical.root && reist_graphical_init(&graphical,session_policy.owner<<32,session_now()))return -5;
    if(graphical.phase==REIST_GRAPHICAL_DEGRADED)return -11;
    if(graphical.phase!=REIST_GRAPHICAL_OFF || graphical_images[0])return -16;
    if(reist_graphical_selection[0]!=0x315549474e545352ULL || reist_graphical_selection[1]>15)return -22;
    graphical_fault=(unsigned)reist_graphical_selection[1];graphical_stop_requested=0;
    for(unsigned n=0;n<4;n++)graphical_modes[n]='0';
    if(graphical_fault>=1&&graphical_fault<=9) {
        unsigned role=(graphical_fault-1)/3,index=(graphical_fault-1)%3;
        graphical_modes[role]=index==0?'u':index==1?'h':'q';
    }
    if(graphical_fault==10)graphical_modes[2]='m';
    if(graphical_fault==11)graphical_modes[0]='l';
    if(graphical_fault==13)graphical_modes[2]='u';
    if(graphical_fault==14)graphical_modes[0]='u';
#ifdef REIST_NATIVE_FULL_DESKTOP
    if(graphical_fault==15)graphical_modes[0]='s';
#endif
    int r=graphical_capture(capture_end);
    if(r){graphical_free();return r;}
    r=graphical_launch();
    if(graphical_fault!=14)for(unsigned n=0;n<4;n++)graphical_modes[n]='0';
    if(graphical_fault==13)graphical_modes[2]='t';
    if(r){graphical_retire(0);graphical_free();return r;}
    if(graphical_fault==12)__asm__ volatile("ud2"); /* AFTER actual READY and authority */
    return (int)(session_child>>32);
}
static int session_graphical_wait(int *status) {
    int outcome=0;
    for(;;) {
        unsigned recover=0;
        if(graphical_stop_requested)break;
        for(unsigned n=0;n<8;n++) {
            reist_graphical_control q;int r=graphical_receive(&q);
            if(r==-11)break;if(r){recover=1;break;}
            reist_graphical_role *role=&graphical.roles[q.role];
            if(q.owner!=role->owner){recover=1;break;}
            if(q.type==REIST_GRAPHICAL_STOP && !q.role && q.sequence==1 && !q.flags && !q.value && !q.endpoint)
                {graphical_stop_requested=1;break;}
            if(q.type==REIST_GRAPHICAL_FAILED && q.role>=2 && q.sequence==role->sequence+1 &&
               !q.endpoint && !q.value && (int32_t)q.flags<=0 && (int32_t)q.flags>=-4095) {
                if(graphical_replace(q.role,q.flags!=0)){recover=1;break;}
            } else if(q.type!=REIST_GRAPHICAL_HEALTH || q.flags!=1 || q.value ||
                      q.endpoint!=(q.role?graphical_endpoints[q.role-1]:0) ||
                      reist_graphical_heartbeat(&graphical,q.role,q.owner,q.epoch,q.sequence,session_now()))
                {recover=1;break;}
        }
        if(graphical_stop_requested)break;
        int expired=reist_graphical_expired(&graphical,session_now());if(expired<0)session_stop(-5);
        if(expired)recover=1;
        if(recover) {
            graphical_retire(0);
            if(graphical_restart_admit()){outcome=110;break;}
            int r=graphical_launch();
            if(r){graphical_retire(1);outcome=110;break;}
        }
        x86os_sleep_ms(10);
    }
    if(graphical.phase==REIST_GRAPHICAL_LIVE)graphical_retire(0);
    graphical_free();session_retire();*status=outcome;return 0;
}
static int session_graphical_kill(void){graphical_stop_requested=1;return 0;}
