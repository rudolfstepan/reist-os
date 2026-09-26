/* Included only by the opt-in native shell adapter. All state is Ring3-owned. */
#include <reist/x86_64/app_files.h>
static reist_app_snapshot *session_app_snapshot;
static reist_app_grant session_app_grant;
static uint64_t session_app_epoch;
static uint32_t session_app_request,session_app_reply;
static int session_app_dispose(void) {
    reist_app_revoke(&session_app_grant);
    if(session_app_request) {
        if(SESSION_S1(IPC_CLOSE,session_app_request))session_stop(-5);
        session_app_request=0;
    }
    if(session_app_reply) {
        if(SESSION_S1(IPC_CLOSE,session_app_reply))session_stop(-5);
        session_app_reply=0;
    }
    if(session_app_snapshot) {
        session_zero(session_app_snapshot,sizeof(*session_app_snapshot));
        if(SESSION_S1(FREE,session_app_snapshot))session_stop(-5);
        session_app_snapshot=0;
    }
    return 0;
}
static int session_app_rpc(unsigned op,const char *path,unsigned length,unsigned index,
    unsigned requested,uint64_t end,reist_fs_frame *frame) {
    uint64_t now=session_now();if(now>=end)return -110;
    int r=reist_fs_request_init(frame,op,path,length,index,requested);if(r)return r;
    if(session_operation_deadline)session_stop(-5);
    session_operation_deadline=end;
    r=reist_fs_call(&session_fs,&session_transport,frame,(unsigned)(end-now>1000?1000:end-now));
    session_operation_deadline=0;
    if(r>=0 && session_now()>=end)r=-110;
    return r;
}
static int session_app_capture(const char *operand,uint64_t end) {
    char path[192];int length=session_path(operand,path);if(length<0)return length;
    if(session_app_snapshot || session_app_request || session_app_reply)return -16;
    uint64_t now=session_now();if(now>=end)return -110;
    uint64_t startup=end-now>1000?now+1000:end;
    int r=session_ensure(startup,0);if(r)return r;
    session_app_snapshot=(void*)(uintptr_t)SESSION_S1(MALLOC,sizeof(*session_app_snapshot));
    if((intptr_t)session_app_snapshot<=0){session_app_snapshot=0;return -12;}
    session_zero(session_app_snapshot,sizeof(*session_app_snapshot));
    reist_fs_frame frame;r=session_app_rpc(5,path,(unsigned)length,0,0,end,&frame);if(r)goto failed;
    session_bytes(&session_app_snapshot->info,&frame.stat.info,sizeof(frame.stat.info));
    if(frame.stat.info.type==X86OS_FILE) {
        uint32_t size=frame.stat.info.size;if(size>REIST_APP_BYTES){r=-27;goto failed;}
        unsigned offset=0;
        while(offset<size) {
            unsigned count=size-offset;if(count>256)count=256;
            r=session_app_rpc(6,path,(unsigned)length,offset,count,end,&frame);if(r)goto failed;
            if(frame.read.transferred!=count){r=-84;goto failed;}
            session_bytes(session_app_snapshot->bytes+offset,frame.read.data,count);offset+=count;
        }
        r=session_app_rpc(6,path,(unsigned)length,size,1,end,&frame);if(r)goto failed;
        if(frame.read.transferred){r=-84;goto failed;}
        session_app_snapshot->length=size;return 0;
    }
    if(frame.stat.info.type!=X86OS_DIRECTORY){r=-95;goto failed;}
    for(unsigned n=0;n<=REIST_APP_ENTRIES;n++) {
        r=session_app_rpc(7,path,(unsigned)length,n,0,end,&frame);
        if(r==1){session_app_snapshot->count=n;return 0;}
        if(r)goto failed;
        if(n==REIST_APP_ENTRIES){r=-27;goto failed;}
        session_bytes(&session_app_snapshot->entries[n],&frame.directory.info,sizeof(frame.directory.info));
    }
    r=-84;
failed:
    session_app_dispose();return session_operation_result(r);
}
static int session_app_equal(const char *a,const char *b) {
    for(unsigned n=0;n<192;n++){if(a[n]!=b[n])return 0;if(!a[n])return 1;}return 0;
}
static int64_t session_app_import(const char *path,int argc,const char *const *argv,
    uint64_t end,reist_task_startup_v1_t *startup,reist_task_profile_v1_t *profile) {
    unsigned tool=session_app_equal(path,"/cat.prg") || session_app_equal(path,"/probe.prg")?1:session_app_equal(path,"/ls.prg")?2:0;
    if(!tool)return reist_x64_task_import_wide(session_prepared,profile,32,startup);
    const char *operand=0;int r=reist_app_operand(tool,argc,argv,&operand);
    if(r==1)return reist_x64_task_import_wide(session_prepared,profile,32,startup);
    if(r)return r;
    r=session_app_capture(operand,end);if(r)return r;
    if(session_app_epoch==UINT64_MAX){session_app_dispose();return -75;}
    ++session_app_epoch;
    r=(int)SESSION_S1(IPC_CREATE,&session_app_request);if(r)goto failed;
    if(!session_app_request)session_stop(-5);
    r=(int)SESSION_S1(IPC_CREATE,&session_app_reply);if(r)goto failed;
    if(!session_app_reply || session_app_reply==session_app_request)session_stop(-5);
    char request[14]="@af1:",reply[14]="@af1:";
    session_hex(request+5,session_app_request);session_hex(reply+5,session_app_reply);
    const char *args[8];for(int n=0;n<argc;n++)args[n]=argv[n];args[argc]=request;args[argc+1]=reply;
    r=reist_x64_startup_init(startup,(unsigned)argc+2,args);if(r)goto failed;
    /* Existing single-peer IPC plus no CREATE/CLOSE/DELEGATE syscall rights:
     * the child cannot extend the root's one-peer directional capability. */
    profile->masks[0]&=~((1ULL<<49)|(1ULL<<52)|(1ULL<<55));
    uint64_t issued=session_now();if(issued>=end){r=-110;goto failed;}
    int64_t child=reist_x64_task_import_wide(session_prepared,profile,32,startup);
    if(child<0){r=child>=-4095?(int)child:-5;goto failed;}
    if(!child || (uint32_t)child!=SESSION_APPLICATION_SLOT || (uint64_t)child>>32>0x7fffffff)session_stop(-5);
    session_zero(&session_app_grant,sizeof(session_app_grant));
    r=reist_app_grant_init(&session_app_grant,session_app_snapshot,session_policy.owner,(uint64_t)child>>32,session_app_epoch,issued);
    if(!r)r=(int)SESSION_S3(IPC_DELEGATE,session_app_request,(uint64_t)child>>32,1);
    if(!r)r=(int)SESSION_S3(IPC_DELEGATE,session_app_reply,(uint64_t)child>>32,2);
    if(!r && session_now()>=session_app_grant.deadline)r=-110;
    if(!r)return child;
    /* Close first even on partial delegation; never let a failed publication
     * survive until a later child's generation or endpoint allocation. */
    session_app_dispose();
    if(service_task(0,3,(uint64_t)child,0))session_stop(-5);
    int64_t retired=service_task(0,2,(uint64_t)child,1000);
    if(retired<0 || (uint64_t)retired>>32>3)session_stop(-5);
    return r;
failed:
    session_app_dispose();return r;
}
static int64_t session_app_wait(int *timed_out) {
    uint64_t end=session_app_grant.deadline;int fault=0;
    for(unsigned count=0;count<REIST_APP_REQUESTS;count++) {
        uint64_t now=session_now();if(now>=end){fault=-110;break;}
        x86os_ipc_bulk_message_t message;session_zero(&message,sizeof(message));
        message.version=2;message.struct_size=sizeof(message);message.length=2048;
        int r=(int)SESSION_S3(IPC_RECEIVE_TIMEOUT,session_app_request,&message,(unsigned)(end-now));
        if(r){fault=r;break;}
        if(message.version!=2 || message.struct_size!=sizeof(message) || message.length!=512){fault=-71;break;}
        for(unsigned n=512;n<2048;n++)if(message.payload[n]){fault=-71;break;}
        if(fault)break;
        reist_app_frame request,reply;session_bytes(&request,message.payload,512);
        r=reist_app_dispatch(&session_app_grant,session_app_snapshot,&request,&reply,session_now());
        if(r){fault=r;break;}
        now=session_now();if(now>=end){fault=-110;break;}
        session_zero(&message,sizeof(message));message.version=2;message.struct_size=sizeof(message);message.length=512;
        session_bytes(message.payload,&reply,512);
        r=(int)SESSION_S3(IPC_SEND_TIMEOUT,session_app_reply,&message,(unsigned)(end-now));
        if(r){fault=r;break;}
        if(session_app_grant.phase==REIST_APP_CLOSED)break;
        if(count==REIST_APP_REQUESTS-1)fault=-110;
    }
    uint64_t now=session_now();
    *timed_out=fault==-110 || now>=end;
    if(fault || now>=end) {
        session_app_dispose();
        if(service_task(0,3,session_child,0))session_stop(-5);
        return service_task(0,2,session_child,1000);
    }
    int64_t result=service_task(0,2,session_child,(unsigned)(end-now));
    if(result==-110) {
        *timed_out=1;
        session_app_dispose();
        if(service_task(0,3,session_child,0))session_stop(-5);
        result=service_task(0,2,session_child,1000);
    }
    session_app_dispose();
    return result;
}
