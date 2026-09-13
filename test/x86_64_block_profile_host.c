#define main legacy_block_main
#include "x86_64_block_service_host.c"
#undef main
typedef struct {Model model;reist_block_profile_v1 profile;} ProfileModel;
static int profile_send(void *v,const x86os_ipc_message_t *q,unsigned timeout){
    ProfileModel *p=v;Model *m=&p->model;CHECK(timeout && timeout<=1000);m->sends++;
    reist_block_backend b={m,clock_now,sleeping,reading};
    (void)reist_block_dispatch_profile(&m->server,&p->profile,&b,q,&m->reply);return 0;
}
static void limits(void){
    CHECK(sizeof(reist_block_profile_v1)==24 && sizeof(reist_block_server)==40);
    for(unsigned limit=1;limit<=16;limit++){
        ProfileModel p;reist_block_client c;reist_block_transport t;unsigned char out[512];
        setup(&p.model,&c,&t);p.profile=(reist_block_profile_v1){1,24,limit,0,3000};
        t.context=&p;t.send=profile_send;
        CHECK(!reist_block_profile_admit(&p.profile,p.model.now));
        for(unsigned n=0;n<limit;n++){
            CHECK(!reist_block_read(&c,&t,n,out,1000));
            CHECK(p.model.server.requests==n+1 && p.model.server.next_sequence==n+2);
            for(unsigned i=0;i<512;i++)CHECK(out[i]==(unsigned char)(i^(n*17)^0xa5));
        }
        memset(out,0xcc,sizeof(out));CHECK(reist_block_read(&c,&t,0,out,1000)==-11);
        CHECK(p.model.reads==limit && p.model.server.requests==limit);
        for(unsigned i=0;i<512;i++)CHECK(out[i]==0xcc);
    }
    reist_block_profile_v1 valid={1,24,9,0,3100};
    CHECK(!reist_block_profile_admit(&valid,100));
    CHECK(reist_block_profile_admit(&valid,99)==-22);
    CHECK(reist_block_profile_admit(&valid,3100)==-22);
    CHECK(reist_block_profile_admit(&valid,UINT64_MAX)==-22);
    for(unsigned field=0;field<5;field++){
        reist_block_profile_v1 bad=valid;
        if(field==0)bad.version=2;if(field==1)bad.size=25;if(field==2)bad.request_limit=17;
        if(field==3)bad.reserved=1;if(field==4)bad.deadline_ms=0;
        CHECK(reist_block_profile_admit(&bad,100)==-22);
    }
    ProfileModel p;reist_block_client c;reist_block_transport t;unsigned char out[512];
    setup(&p.model,&c,&t);p.profile=(reist_block_profile_v1){1,24,9,0,150};
    t.context=&p;t.send=profile_send;memset(out,0xcc,sizeof(out));
    CHECK(reist_block_read(&c,&t,1,out,1000)==-110 && !p.model.reads);
    for(unsigned i=0;i<512;i++)CHECK(out[i]==0xcc);
    setup(&p.model,&c,&t);p.profile=(reist_block_profile_v1){1,24,9,0,100};
    t.context=&p;t.send=profile_send;CHECK(reist_block_read(&c,&t,1,out,1000)==-110 && !p.model.reads);
    CHECK(!p.model.server.requests);
    setup(&p.model,&c,&t);p.profile=(reist_block_profile_v1){1,24,9,0,150};
    p.model.now=99;t.context=&p;t.send=profile_send;
    CHECK(reist_block_read(&c,&t,1,out,1000)==-84 && !p.model.reads);
    for(unsigned limit=1;limit<=16;limit++){
        setup(&p.model,&c,&t);p.profile=(reist_block_profile_v1){1,24,limit,0,3000};
        reist_block_backend backend={&p.model,clock_now,sleeping,reading};
        x86os_ipc_message_t bad={3,140,64,{0}};x86os_ipc_bulk_message_t reply;
        for(unsigned n=0;n<limit;n++){
            CHECK(reist_block_dispatch_profile(&p.model.server,&p.profile,&backend,&bad,&reply)==-22);
            CHECK(p.model.server.requests==n+1 && p.model.server.next_sequence==1 && !p.model.reads);
        }
        CHECK(reist_block_dispatch_profile(&p.model.server,&p.profile,&backend,&bad,&reply)==-11);
        reist_block_server before=p.model.server;memset(&reply,0xab,sizeof(reply));p.profile.reserved=1;
        CHECK(reist_block_dispatch_profile(&p.model.server,&p.profile,&backend,&bad,&reply)==-22);
        CHECK(!memcmp(&before,&p.model.server,sizeof(before)));
        for(unsigned n=0;n<sizeof(reply);n++)CHECK(((unsigned char*)&reply)[n]==0xab);
    }
}
static void profile_adapter(void){
    Ata a={0};reist_pio_ops ops={&a,ata_port,ata_clock,ata_sleep};
    reist_native_profile_service s={0};reist_block_profile_v1 profile={1,24,9,0,3000};
    CHECK(!reist_native_service_init_profile(&s,0x300000002ULL,&ops,&profile));
    CHECK(sizeof(s)==128 && s.service.server.capacity==128 && s.profile.request_limit==9);
    unsigned calls=a.calls;
    reist_native_profile_service before=s;
    CHECK(reist_native_service_init_profile(&s,0x300000002ULL,&ops,&profile)==-22);
    CHECK(!memcmp(&s,&before,sizeof(s)) && a.calls==calls);
    CHECK(reist_native_service_init_profile(&s,0x300000003ULL,&ops,&profile)==-22);
    CHECK(!memcmp(&s,&before,sizeof(s)) && a.calls==calls);
    profile.request_limit=16;CHECK(s.profile.request_limit==9); /* immutable snapshot */
    for(unsigned n=1;n<=calls;n++){
        a=(Ata){.fail=n};s=(reist_native_profile_service){0};
        CHECK(reist_native_service_init_profile(&s,0x300000002ULL,&ops,&profile)<0);
        CHECK(!s.service.server.ready);
        unsigned count=a.calls;CHECK(reist_native_service_init_profile(&s,0x300000002ULL,&ops,&profile)==-22);
        CHECK(a.calls==count);
    }
    for(unsigned n=1;n<=calls;n++){
        a=(Ata){.late=n};s=(reist_native_profile_service){0};
        CHECK(reist_native_service_init_profile(&s,0x300000002ULL,&ops,&profile)==-110);
        CHECK(!s.service.server.ready);
    }
    a=(Ata){0};s=(reist_native_profile_service){0};profile.deadline_ms=1;
    CHECK(reist_native_service_init_profile(&s,0x300000002ULL,&ops,&profile)==-110 && !a.calls);
    a=(Ata){0};s=(reist_native_profile_service){0};profile.deadline_ms=3001;
    before=s;CHECK(reist_native_service_init_profile(&s,0x300000002ULL,&ops,&profile)==-22);
    CHECK(!a.calls && !memcmp(&s,&before,sizeof(s)));
    a=(Ata){0};s=(reist_native_profile_service){0};profile.deadline_ms=3000;
    CHECK(!reist_native_service_init_profile(&s,0x300000002ULL,&ops,&profile));
    CHECK(!reist_native_service_init_profile(&s,0x400000003ULL,&s.service.upstream,&profile));
    CHECK(s.service.server.owner==0x400000003ULL && s.service.server.ready);
    a=(Ata){0};s=(reist_native_profile_service){0};profile=(reist_block_profile_v1){1,24,9,0,3000};
    CHECK(!reist_native_service_init_profile(&s,0x300000002ULL,&ops,&profile));
    profile.request_limit=1;profile.deadline_ms=1;
    for(unsigned n=1;n<=10;n++){
        x86os_ipc_message_t request={1,140,64,{0}};x86os_ipc_bulk_message_t reply;
        reist_block_header h={1,64,1,0,0x300000002ULL,n,n,a.now+1000,512,0,0};
        memcpy(request.payload,&h,64);unsigned before=a.calls;
        CHECK(reist_native_service_dispatch_profile(&s,&request,&reply)==(n==10?-11:0));
        CHECK(s.service.server.requests==(n==10?9:n) && s.profile.request_limit==9 && s.profile.deadline_ms==3000);
        if(n==10)CHECK(a.calls==before && reply.length==64);
        else for(unsigned i=0;i<512;i++)CHECK(reply.payload[64+i]==(unsigned char)(i^(n*17)^0xa5));
    }
}
int main(void){limits();profile_adapter();puts("NATIVE_BLOCK_PROFILE_OK");return 0;}
