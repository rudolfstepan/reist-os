#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <reist/x86_64/desktop_services.h>
#include <reist/x86_64/filesystem.h>
#include <reist/x86_64/service_session.h>

static reist_desktop_broker broker;
static reist_desktop_service_manifest manifest[3];
static uint64_t now=1000, seq, child;
static reist_fs_client session_fs;
static reist_service_session_v1 session_service;
static uint64_t session_operation_deadline;
static int64_t task_receipt=-11;
static unsigned task_waits,task_cancels,fs_reads,fs_case;
static unsigned fs_send_wait,fs_receive_wait;
static x86os_ipc_bulk_message_t fs_wire;
static uint64_t session_now(void){return now;}
static void session_bytes(void *to,const void *from,size_t count){memcpy(to,from,count);}
static int64_t service_task(void *unused,unsigned operation,uint64_t owner,unsigned timeout) {
    (void)unused;assert(owner==(12ULL<<32|6));
    if(operation==2 && !timeout)return -22; /* Actual frozen TASK_CONTROL ABI. */
    assert(timeout==(operation==2?1U:0U));
    if(operation==2){task_waits++;return task_receipt;}
    assert(operation==3);task_cancels++;return 0;
}
int x86os_process_identity_of(int pid,x86os_process_identity_t *out) {
    assert(pid==12 && out);
    if(task_receipt!=-11)return -3;
    *out=(x86os_process_identity_t){1,16,pid,(unsigned)pid};return 0;
}
static int full_fs_send(const x86os_ipc_bulk_message_t *q) {
    assert(!session_operation_deadline);
    if(fs_send_wait){fs_send_wait--;return -11;}
    fs_wire=*q;fs_reads++;return fs_case==1?-19:0;
}
static int full_fs_receive(x86os_ipc_bulk_message_t *out) {
    assert(!session_operation_deadline);
    if(fs_receive_wait){fs_receive_wait--;return -11;}
    reist_fs_header h;reist_fs_frame frame;
    memcpy(&h,fs_wire.payload,64);memcpy(&frame,fs_wire.payload+64,512);
    if(h.operation==5) {
        assert(!strcmp(frame.stat.path,"/"));
        frame.stat.info.type=fs_case==2?X86OS_FILE:X86OS_DIRECTORY;
        strcpy(frame.stat.info.name,"/");
    } else {
        assert(h.operation==6 && frame.read.requested<=256);
        frame.read.transferred=frame.read.requested-(fs_case==2?1:0);
        for(unsigned n=0;n<frame.read.transferred;n++)frame.read.data[n]=(unsigned char)(frame.read.offset+n);
    }
    h.flags=1;if(fs_case==3)h.owner+=1ULL<<32;
    if(fs_case==4)now+=1000;
    if(fs_case==5)session_fs.owner+=1ULL<<32;
    if(fs_case==7)frame.read.offset^=1;
    memcpy(fs_wire.payload,&h,64);memcpy(fs_wire.payload+64,&frame,512);
    if(fs_case==8)fs_wire.payload[2047]=1;
    *out=fs_wire;return 0;
}
#include "../userspace/sdk/lib/x86_64/shell_full_desktop.inc"
static void root_backend_tests(void) {
    full_desktop_backend s={0};s.children[0].owner=12ULL<<32|6;
    reist_desktop_service_frame q={0},out={0};q.object=s.children[0].owner;
    q.operation=REIST_DESKTOP_IDENTITY;
    assert(!full_desktop_child_step(&s,&q,&out) && !out.status && !task_waits);
    q.operation=REIST_DESKTOP_CANCEL;
    assert(!full_desktop_child_step(&s,&q,&out) && task_cancels==1 && !s.children[0].reaped);
    q.operation=REIST_DESKTOP_WAIT;
    assert(!full_desktop_child_step(&s,&q,&out) && out.status==-11);
    task_receipt=(2ULL<<32)|257;out.status=0;q.operation=REIST_DESKTOP_IDENTITY;
    assert(!full_desktop_child_step(&s,&q,&out) && out.status==-3 && s.children[0].reaped);
    unsigned consumed=task_waits;out.status=0;q.operation=REIST_DESKTOP_WAIT;
    assert(!full_desktop_child_step(&s,&q,&out) && !out.status && out.offset==257 && task_waits==consumed);
    assert(!full_desktop_child_step(&s,&q,&out) && out.status==-3 && task_waits==consumed);
    q.object+=1ULL<<32;assert(full_desktop_child_step(&s,&q,&out)==-116);
    const uint32_t statuses[]={256,UINT32_MAX};
    for(unsigned n=0;n<2;n++) {
        s.children[0]=(full_desktop_child){12ULL<<32|6,0,0,0};
        task_receipt=(3ULL<<32)|statuses[n];out=(reist_desktop_service_frame){0};q.object=s.children[0].owner;
        assert(!full_desktop_child_step(&s,&q,&out) && out.offset==statuses[n]);
    }
    s.children[0]=(full_desktop_child){12ULL<<32|6,0,0,0};task_receipt=4ULL<<32;
    assert(full_desktop_child_step(&s,&q,&out)==-71 && !s.children[0].reaped);
    reist_desktop_service_manifest file={0};strcpy(file.path,"/asset");
    file.info.type=X86OS_FILE;file.info.size=4096;file.rights=1;
    for(fs_case=0;fs_case<6;fs_case++) {
        memset(&s,0,sizeof(s));memset(&session_fs,0,sizeof(session_fs));now=1000;
        session_service.phase=REIST_SESSION_HEALTHY;fs_reads=0;
        s.service_generation=10ULL<<32|3;assert(!reist_fs_client_bind(&session_fs,s.service_generation));
        q=(reist_desktop_service_frame){0};q.operation=REIST_DESKTOP_READ;q.sequence=1;
        q.deadline_ms=2000;q.offset=17;q.count=1792;out=(reist_desktop_service_frame){0};
        int result=full_desktop_read_step(&s,&q,&file,&out);
        assert(result==1 && !fs_reads && !out.count);
        q.sequence++;assert(full_desktop_read_step(&s,&q,&file,&out)==-84 && !fs_reads);q.sequence--;
        for(unsigned turn=0;turn<21 && result==1;turn++)result=full_desktop_read_step(&s,&q,&file,&out);
        if(fs_case) {
            const int expected[]={0,-19,-84,-71,-110,-116};assert(result==expected[fs_case] && !out.count);
        } else {
            assert(!result);
            assert(fs_reads==7 && out.count==1792 && !s.read_used && !s.read_sequence);
            for(unsigned n=0;n<1792;n++)assert(out.payload.bytes[n]==(unsigned char)(17+n));
            session_fs.owner+=1ULL<<32;assert(full_desktop_read_step(&s,&q,&file,&out)==-116 && fs_reads==7);
        }
        assert(!session_operation_deadline);
    }
    for(fs_case=0;fs_case<6;fs_case++) {
        memset(&s,0,sizeof(s));memset(&session_fs,0,sizeof(session_fs));now=1000;
        session_service.phase=REIST_SESSION_HEALTHY;fs_reads=0;
        s.service_generation=10ULL<<32|3;s.last_io_ms=now;
        assert(!reist_fs_client_bind(&session_fs,s.service_generation));
        assert(!full_desktop_service_poll(&s) && !fs_reads);
        now+=249;assert(!full_desktop_service_poll(&s) && !fs_reads);
        now++;s.read_sequence=1;assert(!full_desktop_service_poll(&s) && !fs_reads);
        s.read_sequence=0;
        const int expected[]={0,-19,-84,-71,-110,-116};
        assert(!full_desktop_service_poll(&s) && !fs_reads && s.fs_phase==1);
        int result=full_desktop_service_poll(&s);
        if(!result)result=full_desktop_service_poll(&s);
        assert(result==expected[fs_case] && fs_reads==1);
        assert(!session_operation_deadline);
        if(!fs_case)assert(s.last_io_ms==now && !full_desktop_service_poll(&s) && fs_reads==1);
    }
    /* Root can process other control traffic between each poll, including
     * responses later than the removed100ms blocking quantum. */
    for(unsigned scenario=0;scenario<5;scenario++) {
        memset(&s,0,sizeof(s));memset(&session_fs,0,sizeof(session_fs));now=1000;
        session_service.phase=REIST_SESSION_HEALTHY;fs_reads=0;
        s.service_generation=10ULL<<32|3;assert(!reist_fs_client_bind(&session_fs,s.service_generation));
        q=(reist_desktop_service_frame){0};q.operation=REIST_DESKTOP_READ;q.sequence=1;
        q.deadline_ms=2000;q.count=256;out=(reist_desktop_service_frame){0};
        fs_case=scenario>=3?scenario+4:0;
        fs_send_wait=scenario==1?2:0;fs_receive_wait=scenario==1?3:0;
        assert(full_desktop_read_step(&s,&q,&file,&out)==1 && !fs_reads);
        int result=1;
        for(unsigned turn=0;turn<12 && result==1;turn++) {
            now+=scenario==2?500:50;
            result=full_desktop_read_step(&s,&q,&file,&out);
            if(result==1)assert(!out.count && s.fs_header.deadline_ms==2000);
        }
        int expected=scenario==2?-110:scenario>=3?-71:0;
        assert(result==expected && !fs_send_wait && !fs_receive_wait);
        if(!result)assert(out.count==256 && now>=1100 && fs_reads==1 && !session_fs.busy);
        else assert(!out.count);
        assert(!session_operation_deadline);
    }
    fs_case=0;now=1000;
}
static unsigned calls, aborts, delay, broken;
static unsigned late, wire_ready, wire_corrupt, client_failures, backpressure;
static reist_desktop_service_frame wire;
static reist_desktop_service_client client;
static int clock_ms(void *unused,uint64_t *value) { (void)unused; *value=now; return 0; }
static int step(void *unused,const reist_desktop_service_frame *q,
    const reist_desktop_service_manifest *m,reist_desktop_service_frame *out) {
    (void)unused; calls++;
    if(delay) { delay--; return 1; }
    if(q->operation==REIST_DESKTOP_READ) {
        assert(m==manifest+1);
        out->count=q->count;
        for(unsigned n=0;n<out->count;n++) out->payload.bytes[n]=(unsigned char)(q->offset+n);
    } else if(q->operation==REIST_DESKTOP_LAUNCH) {
        assert(m==manifest+2); child=(11ULL<<32)|6; out->object=child;
    } else if(q->operation==REIST_DESKTOP_IDENTITY) {
        out->object=child;
    } else if(q->operation==REIST_DESKTOP_CANCEL) {
        assert(q->object==child);
    } else if(q->operation==REIST_DESKTOP_WAIT) {
        out->offset=7; out->object=child;
    } else assert(!"unexpected backend call");
    if(broken) out->epoch++;
    if(late) now+=1001;
    return 0;
}
static int abort_all(void *unused) { (void)unused; aborts++; return 0; }
static int send_request(void *unused,const reist_desktop_service_frame *q) {
    (void)unused;
    if(backpressure) { backpressure--; return -11; }
    int r=reist_desktop_broker_submit(&broker,q,now);
    if(r) { assert(reist_desktop_service_reject(q,r,&wire)==0); wire_ready=1; }
    return 0;
}
static int receive_reply(void *unused,reist_desktop_service_frame *out) {
    (void)unused;
    if(!wire_ready) return -11;
    *out=wire; wire_ready=0;
    if(wire_corrupt) out->sequence++;
    return 0;
}
static int client_wait(void *unused,unsigned ms) {
    (void)unused; assert(ms && ms<=10); now+=ms;
    if(!wire_ready) {
        int r=reist_desktop_broker_step(&broker,&wire,now);
        if(r<0) return r;
        if(r==2) wire_ready=1;
    }
    return 0;
}
static void client_failed(void *unused,int error) {
    (void)unused; assert(error<0); client_failures++;
}
static reist_desktop_service_frame client_request(unsigned op) {
    reist_desktop_service_frame q={0}; q.version=1; q.size=sizeof(q); q.operation=op; return q;
}
static reist_desktop_service_frame request(unsigned operation) {
    reist_desktop_service_frame q={0};
    q.version=1; q.size=sizeof(q); q.operation=operation;
    q.root=1ULL<<32; q.desktop=(2ULL<<32)|4; q.epoch=1;
    q.sequence=seq+1; q.deadline_ms=now+1000;
    return q;
}
static reist_desktop_service_frame transact(reist_desktop_service_frame q) {
    reist_desktop_service_frame out;
    memset(&out,0xa5,sizeof(out));
    assert(reist_desktop_broker_submit(&broker,&q,now)==0); seq++;
    int r;
    do { r=reist_desktop_broker_step(&broker,&out,now); now++; } while(r==1);
    assert(r==2 && out.sequence==seq && out.root==q.root && out.desktop==q.desktop && out.epoch==q.epoch);
    return out;
}
int main(void) {
    root_backend_tests();
    strcpy(manifest[0].path,"/"); strcpy(manifest[0].info.name,"/");
    manifest[0].info.type=X86OS_DIRECTORY; manifest[0].rights=REIST_DESKTOP_MANIFEST_READ;
    strcpy(manifest[1].path,"/asset.bin"); strcpy(manifest[1].info.name,"asset.bin");
    manifest[1].info.type=X86OS_FILE; manifest[1].info.size=1048576; manifest[1].rights=REIST_DESKTOP_MANIFEST_READ;
    strcpy(manifest[2].path,"/text.prg"); strcpy(manifest[2].info.name,"text.prg");
    manifest[2].info.type=X86OS_FILE; manifest[2].info.size=8192;
    manifest[2].rights=REIST_DESKTOP_MANIFEST_EXEC; manifest[2].digest[0]=1;
    reist_desktop_broker_config c={0};
    c.root=1ULL<<32; c.desktop=(2ULL<<32)|4; c.epoch=1; c.service_generation=3;
    c.manifest=manifest; c.manifest_count=3; c.clock_ms=clock_ms; c.step=step; c.abort=abort_all;
    assert(reist_desktop_broker_init(&broker,&c,now)==0);
    assert(reist_desktop_broker_init(&broker,&c,now)==-16);
    reist_desktop_service_frame q=request(REIST_DESKTOP_OPEN);
    strcpy(q.payload.command.path,"/asset.bin");
    reist_desktop_service_frame bad=q; bad.desktop++;
    assert(reist_desktop_broker_submit(&broker,&bad,now)==-13 && !calls);
    bad=q; strcpy(bad.payload.command.path,"/../asset.bin");
    assert(reist_desktop_broker_submit(&broker,&bad,now)==-22 && !calls);
    bad=q; bad.reserved[0]=1;
    assert(reist_desktop_broker_submit(&broker,&bad,now)==-22 && !calls);
    reist_desktop_service_frame out=transact(q);
    assert(!out.status && out.object && out.payload.info.size==1048576);
    uint64_t object=out.object;
    q=request(REIST_DESKTOP_READ); q.object=object; q.offset=10; q.count=1792;
    bad=q; bad.count=1793; assert(reist_desktop_broker_submit(&broker,&bad,now)==-22);
    bad=q; bad.offset=1048576; assert(reist_desktop_broker_submit(&broker,&bad,now)==-22);
    delay=2; out=transact(q); assert(!out.status && out.count==1792 && out.payload.bytes[1791]==(unsigned char)1801);
    q=request(REIST_DESKTOP_CLOSE); q.object=object; out=transact(q); assert(!out.status);
    q=request(REIST_DESKTOP_READ); q.object=object; q.count=1;
    assert(reist_desktop_broker_submit(&broker,&q,now)==-116);
    q=request(REIST_DESKTOP_READDIR); strcpy(q.payload.command.path,"/"); q.count=32;
    out=transact(q); assert(!out.status && out.count==2);
    assert(!strcmp(out.payload.entries[0].name,"asset.bin"));
    q=request(REIST_DESKTOP_LAUNCH); strcpy(q.payload.command.path,"/asset.bin");
    q.argc=1; strcpy(q.payload.command.argv[0],"/asset.bin");
    assert(reist_desktop_broker_submit(&broker,&q,now)==-13);
    q=request(REIST_DESKTOP_LAUNCH); strcpy(q.payload.command.path,"/text.prg");
    q.argc=1; strcpy(q.payload.command.argv[0],"/text.prg");
    out=transact(q); assert(!out.status && out.object==child);
    q=request(REIST_DESKTOP_IDENTITY); q.object=child+1;
    assert(reist_desktop_broker_submit(&broker,&q,now)==-13);
    q.object=child; out=transact(q); assert(!out.status && out.object==child);
    q=request(REIST_DESKTOP_CANCEL); q.object=child; out=transact(q); assert(!out.status);
    q=request(REIST_DESKTOP_WAIT); q.object=child; out=transact(q); assert(!out.status && out.offset==7);
    q=request(REIST_DESKTOP_IDENTITY); q.object=child;
    assert(reist_desktop_broker_submit(&broker,&q,now)==-13);
    now+=1000;
    for(unsigned i=0;i<4;i++) {
        q=request(REIST_DESKTOP_STAT); strcpy(q.payload.command.path,"/asset.bin");
        assert(reist_desktop_broker_submit(&broker,&q,now)==0); seq++;
    }
    q.sequence=seq+1; assert(reist_desktop_broker_submit(&broker,&q,now)==-11);
    for(unsigned i=0;i<4;i++) assert(reist_desktop_broker_step(&broker,&out,now)==2);
    for(unsigned i=4;i<16;i++) { q=request(REIST_DESKTOP_STAT); strcpy(q.payload.command.path,"/asset.bin"); out=transact(q); }
    q=request(REIST_DESKTOP_STAT); strcpy(q.payload.command.path,"/asset.bin");
    assert(reist_desktop_broker_submit(&broker,&q,now)==-11);
    now+=1000; q=request(REIST_DESKTOP_OPEN); strcpy(q.payload.command.path,"/asset.bin");
    out=transact(q); object=out.object;
    q=request(REIST_DESKTOP_READ); q.object=object; q.count=1; broken=1;
    assert(reist_desktop_broker_submit(&broker,&q,now)==0);
    memset(&out,0xa5,sizeof(out)); assert(reist_desktop_broker_step(&broker,&out,now)==-71);
    assert(aborts==1 && ((unsigned char *)&out)[0]==0xa5);
    assert(reist_desktop_broker_submit(&broker,&q,now)==-116);
    assert(reist_desktop_broker_revoke(&broker)==0 && aborts==1);
    assert(reist_desktop_broker_init(&broker,&c,now)==-116);
    c.epoch++; assert(reist_desktop_broker_init(&broker,&c,now)==0);
    assert(reist_desktop_broker_revoke(&broker)==0 && aborts==2);
    c.epoch++; broken=0; assert(reist_desktop_broker_init(&broker,&c,now)==0);
    reist_desktop_service_client_config cc={0};
    cc.root=c.root; cc.desktop=c.desktop; cc.epoch=c.epoch;
    cc.clock_ms=clock_ms; cc.send=send_request; cc.receive=receive_reply;
    cc.wait=client_wait; cc.failed=client_failed;
    assert(reist_desktop_service_client_init(&client,&cc)==0);
    q=client_request(REIST_DESKTOP_OPEN); strcpy(q.payload.command.path,"/asset.bin");
    backpressure=2;
    assert(reist_desktop_service_exchange(&client,&q,&out,1000)==0 && out.object);
    object=out.object; assert(client.sequence==1 && broker.sequence==1 && !backpressure);
    q=client_request(REIST_DESKTOP_OPEN); strcpy(q.payload.command.path,"/not-granted");
    memset(&out,0xa5,sizeof(out));
    assert(reist_desktop_service_exchange(&client,&q,&out,1000)==-13 && !client_failures);
    assert(client.sequence==1 && broker.sequence==1 && ((unsigned char *)&out)[0]==0xa5);
    q=client_request(REIST_DESKTOP_READ); q.object=object; q.count=1792; delay=2;
    assert(reist_desktop_service_exchange(&client,&q,&out,1000)==0 && out.count==1792);
    assert(out.payload.bytes[1791]==(unsigned char)1791);
    wire_corrupt=1; q=client_request(REIST_DESKTOP_CLOSE); q.object=object;
    memset(&out,0xa5,sizeof(out));
    assert(reist_desktop_service_exchange(&client,&q,&out,1000)==-71 && client_failures==1);
    assert(((unsigned char *)&out)[0]==0xa5);
    assert(reist_desktop_service_exchange(&client,&q,&out,1000)==-116 && client_failures==1);
    assert(reist_desktop_broker_revoke(&broker)==0);
    reist_desktop_service_client_detach(&client);
    assert(reist_desktop_service_client_init(&client,&cc)==-116);
    c.epoch++; cc.epoch=c.epoch; wire_corrupt=0; wire_ready=0;
    assert(reist_desktop_broker_init(&broker,&c,now)==0);
    assert(reist_desktop_service_client_init(&client,&cc)==0);
    q=client_request(REIST_DESKTOP_OPEN); strcpy(q.payload.command.path,"/asset.bin");
    assert(reist_desktop_service_exchange(&client,&q,&out,1000)==0); object=out.object;
    q=client_request(REIST_DESKTOP_READ); q.object=object; q.count=1; late=1;
    memset(&out,0xa5,sizeof(out));
    assert(reist_desktop_service_exchange(&client,&q,&out,1000)==-110);
    assert(client_failures==2 && broker.phase==2 && ((unsigned char *)&out)[0]==0xa5);
    q=request(REIST_DESKTOP_READ); q.object=17; q.count=UINT32_MAX;
    assert(reist_desktop_service_reject(&q,-22,&out)==0);
    out.status=0; out.flags=REIST_DESKTOP_REPLY_ADMITTED; out.count=UINT32_MAX;
    assert(reist_desktop_service_reply_valid(&q,&out)==-71);
    c.epoch++;assert(!reist_desktop_broker_init(&broker,&c,now));
    uint64_t owners[2]={21ULL<<32|6,22ULL<<32|7};
    const uint64_t invalid[][2]={{0,22ULL<<32|7},{21ULL<<32|5,22ULL<<32|7},
        {21ULL<<32|6,21ULL<<32|7},{2ULL<<32|6,22ULL<<32|7},
        {21ULL<<32|6,UINT64_MAX}};
    for(unsigned n=0;n<sizeof(invalid)/sizeof(invalid[0]);n++) {
        reist_desktop_broker saved=broker;
        assert(reist_desktop_broker_adopt(&broker,invalid[n],now)<0);
        assert(!memcmp(&saved,&broker,sizeof(broker)));
    }
    assert(!reist_desktop_broker_adopt(&broker,owners,now));
    assert(broker.children[0]==owners[0] && broker.children[1]==owners[1]);
    assert(reist_desktop_broker_adopt(&broker,owners,now)==-16);
    /* Root-only replacement must not silently re-authorize a retired owner. */
    uint64_t replacement=25ULL<<32|6;
    reist_desktop_broker saved_replacement=broker;
    assert(reist_desktop_broker_replace(&broker,owners[0],owners[0],now)==-116);
    assert(reist_desktop_broker_replace(&broker,owners[0]+(1ULL<<32),replacement,now)==-116);
    assert(reist_desktop_broker_replace(&broker,owners[0],25ULL<<32|7,now)==-22);
    assert(!memcmp(&broker,&saved_replacement,sizeof(broker)));
    broker.count=1;broker.queue[0].object=owners[0];saved_replacement=broker;
    assert(reist_desktop_broker_replace(&broker,owners[0],replacement,now)==-16);
    assert(!memcmp(&broker,&saved_replacement,sizeof(broker)));
    broker.queue[0].object=owners[1];
    assert(!reist_desktop_broker_replace(&broker,owners[0],replacement,now));
    assert(broker.children[0]==replacement && broker.last_children[0]==replacement);
    assert(broker.children[1]==owners[1] && broker.count==1 && broker.queue[0].object==owners[1]);
    assert(reist_desktop_broker_replace(&broker,owners[0],replacement,now)==-116);
    broker.count=0;memset(broker.queue,0,sizeof(broker.queue));
    owners[0]=replacement;
    assert(!reist_desktop_broker_revoke(&broker));c.epoch++;
    assert(!reist_desktop_broker_init(&broker,&c,now));
    assert(reist_desktop_broker_adopt(&broker,owners,now)==-116);
    owners[0]+=2ULL<<32;owners[1]+=2ULL<<32;
    assert(!reist_desktop_broker_adopt(&broker,owners,now));
    assert(!reist_desktop_broker_revoke(&broker));
    q=request(REIST_DESKTOP_WAIT);q.object=23ULL<<32|6;
    assert(!reist_desktop_service_reject(&q,-11,&out));
    out.status=0;out.flags=REIST_DESKTOP_REPLY_ADMITTED;
    const uint32_t native_status[]={256,257,UINT32_MAX};
    for(unsigned n=0;n<3;n++){out.offset=native_status[n];assert(!reist_desktop_service_reply_valid(&q,&out));}
    puts("desktop broker: read/launch, queue/rate, generations and revocation passed");
    return 0;
}
