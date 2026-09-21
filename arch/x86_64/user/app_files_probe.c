/* Explicit qualification client. No ambient grants or special kernel role. */
#include "../../../userspace/sdk/lib/x86_64/app_file_platform.c"
/* Qualification only: first-entry observer binds original image bytes before
 * selecting a declared test. No kernel clock, profile or quota modification. */
volatile uint64_t reist_app_probe_selection[4] __attribute__((section(".data.memory_witness")))={
    0x3150464154534554ULL,1,0,0};
#ifdef REIST_APP_BUDGET_CLIENT
/* Test-only wire client: avoid repeating SDK copies/validation when measuring
 * the broker's request bound. The independent guest oracle validates every
 * full request/reply. No sequence, clock or CPU counter is reset. */
static int probe_budget(void) {
    reist_app_frame q;zero(&q,sizeof(q));q.version=1;q.size=512;q.operation=REIST_APP_STAT;
    q.root=app_root;q.child=app_child;q.epoch=app_epoch;q.deadline=app_end;
    /* Bulk RECEIVE validates version/size/capacity, not old output bytes.
     * Keep both buffers within one mapped page and reuse the returned payload. */
    static x86os_ipc_bulk_message_t tx __attribute__((aligned(4096)));
    static x86os_ipc_bulk_message_t rx __attribute__((aligned(4096)));
    zero(&tx,sizeof(tx));zero(&rx,sizeof(rx));
    tx.version=rx.version=2;tx.struct_size=rx.struct_size=sizeof(tx);tx.length=512;
    bytes(tx.payload,&q,512);
    for(uint64_t seq=3;seq<=REIST_APP_REQUESTS+1;seq++) {
        bytes(tx.payload+40,&seq,sizeof(seq));
        int wait=remaining();if(wait<0)return 35;
        int r=(int)CALL(IPC_SEND_TIMEOUT,app_request,&tx,(unsigned)wait);
        if(r)return seq==REIST_APP_REQUESTS+1 && r==-9?36:34;
        if(seq==REIST_APP_REQUESTS+1)return 37;
        rx.length=2048;
        wait=remaining();if(wait<0)return 35;
        r=(int)CALL(IPC_RECEIVE_TIMEOUT,app_reply,&rx,(unsigned)wait);if(r)return 34;
        reist_app_frame answer;bytes(&answer,rx.payload,80);
        if(rx.version!=2 || rx.struct_size!=sizeof(rx) || rx.length!=512 ||
           answer.version!=1 || answer.size!=512 || answer.operation!=REIST_APP_STAT || answer.flags!=1 ||
           answer.root!=app_root || answer.child!=app_child || answer.epoch!=app_epoch ||
           answer.sequence!=seq || answer.deadline!=app_end || answer.status ||
           answer.length!=sizeof(x86os_file_info_t) || answer.offset || answer.requested || answer.reserved)return 38;
        app_sequence=seq;
    }
    return 39;
}
#endif
static int probe_invalid(unsigned mode) {
    reist_app_frame q;zero(&q,sizeof(q));q.version=1;q.size=512;q.operation=REIST_APP_STAT;
    q.root=app_root;q.child=app_child;q.epoch=app_epoch;q.sequence=app_sequence+1;q.deadline=app_end;
    if(mode==2)q.operation=5; /* Unsupported operation; never a write grant. */
    else if(mode==3)--q.epoch;
    else if(mode==4)q.child=app_root;
    x86os_ipc_bulk_message_t m;zero(&m,sizeof(m));m.version=2;m.struct_size=sizeof(m);m.length=512;
    bytes(m.payload,&q,512);
    int r=(int)CALL(IPC_SEND_TIMEOUT,app_request,&m,1000);if(r)return 31;
    zero(&m,sizeof(m));m.version=2;m.struct_size=sizeof(m);m.length=2048;
    r=(int)CALL(IPC_RECEIVE_TIMEOUT,app_reply,&m,1000);
    /* A cancelled child normally never returns. A valid reply is forbidden. */
    return r<0?32:33;
}
int main(int argc,char **argv) {
    if(argc!=2 || !argv || !app_request)return 22;
    if(reist_app_probe_selection[0]!=0x3150464154534554ULL || reist_app_probe_selection[1]!=1 ||
       reist_app_probe_selection[2]>8 || reist_app_probe_selection[3])return 25;
    unsigned mode=(unsigned)reist_app_probe_selection[2];
    reist_app_frame r;
    /* Negative path authority remains denied locally without any FS lookup. */
    x86os_file_info_t info;
    if(reist_vfs_stat("/not-granted",&info,1000)!=-13)return 23;
    if(transact(REIST_APP_STAT,0,0,1000,&r))return 24;
    if(mode==1) {
        /* Poison pointer probes must be denied before any memory access. */
        if(CALL(IPC_CREATE,1,0,0)!=-13 || CALL(IPC_CLOSE,app_request,0,0)!=-13 ||
           CALL(IPC_DELEGATE,app_request,app_root,1)!=-13)return 26;
        x86os_ipc_bulk_message_t m;zero(&m,sizeof(m));m.version=2;m.struct_size=sizeof(m);m.length=512;
        if(CALL(IPC_SEND_TIMEOUT,app_reply,&m,1)!=-13 ||
           CALL(IPC_RECEIVE_TIMEOUT,app_request,&m,1)!=-13)return 27;
        if(CALL(DEVICE_CONTROL,1,1,0)!=-13)return 28;
    } else if(mode>=2 && mode<=4)return probe_invalid(mode);
    else if(mode==5)__builtin_trap();
    else if(mode==6) {
        x86os_ipc_bulk_message_t m;zero(&m,sizeof(m));m.version=2;m.struct_size=sizeof(m);m.length=2048;
        (void)CALL(IPC_RECEIVE_TIMEOUT,app_reply,&m,1000);return 29;
    } else if(mode==7) {
        /* Deliberate bounded hostile CPU work, never a production wait path. */
        for(volatile uint64_t n=0;n<1000000000ULL;n++)__asm__ volatile("" ::: "memory");
        return 30;
    } else if(mode==8) {
#ifdef REIST_APP_BUDGET_CLIENT
        return probe_budget();
#else
        for(unsigned n=2;n<REIST_APP_REQUESTS;n++)if(transact(REIST_APP_STAT,0,0,1000,&r))return 34;
        return probe_invalid(8); /* 81st wire request, no SDK budget reset. */
#endif
    }
    x86os_puts("APP_OBJECT_PROBE_OK\n");return 0;
}
