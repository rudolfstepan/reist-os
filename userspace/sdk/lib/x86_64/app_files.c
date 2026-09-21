#include <reist/x86_64/app_files.h>
#include <stddef.h>
static int empty(const void *p,size_t n) {
    const unsigned char *b=p;for(size_t i=0;i<n;i++)if(b[i])return 0;return 1;
}
static void copy(void *to,const void *from,size_t n) {
    volatile unsigned char *a=to;const unsigned char *b=from;for(size_t i=0;i<n;i++)a[i]=b[i];
}
static int info_valid(const x86os_file_info_t *p) {
    if(p->type!=X86OS_FILE && p->type!=X86OS_DIRECTORY)return 0;
    unsigned end=0;while(end<sizeof(p->name) && p->name[end])end++;
    return end && end<sizeof(p->name) && empty(p->name+end,sizeof(p->name)-end);
}
static int shape(const reist_app_snapshot *s) {
    return s && (s->info.type==X86OS_FILE?
        s->length<=REIST_APP_BYTES && s->length==s->info.size && !s->count:
        s->info.type==X86OS_DIRECTORY && !s->length && s->count<=REIST_APP_ENTRIES);
}
static int equal(const char *a,const char *b) {
    for(unsigned i=0;i<128;i++){if(a[i]!=b[i])return 0;if(!a[i])return 1;}return 0;
}
int reist_app_operand(unsigned tool,int argc,const char *const *argv,const char **path) {
    if(!path || !argv || argc<1 || argc>6 || (tool!=1 && tool!=2))return -22;
    for(int i=0;i<argc;i++) {
        if(!argv[i])return -22;
        unsigned n=0;while(n<128 && argv[i][n])n++;
        if(!n || n==128)return -36;
    }
    if(tool==1){if(argc!=2)return -22;*path=argv[1];return 0;}
    const char *selected=".";
    for(int i=1;i<argc;i++) {
        const char *a=argv[i];
        if(equal(a,"--help"))return 1;
        if(equal(a,"--pager") || equal(a,"--no-pager"))continue;
        if(a[0]!='-' || !a[1]){if(!equal(selected,"."))return -22;selected=a;continue;}
        for(unsigned n=1;a[n];n++) {
            char c=a[n];if(c!='1' && c!='C' && c!='l' && c!='a' && c!='p' && c!='h')return -22;
        }
    }
    *path=selected;return 0;
}
int reist_app_grant_init(reist_app_grant *g,const reist_app_snapshot *s,
    uint64_t root,uint64_t child,uint64_t epoch,uint64_t now) {
    if(!g || !shape(s) || !empty(g,sizeof(*g)) || !info_valid(&s->info) ||
       !root || root>0x7fffffff || child<=root || child>0x7fffffff || !epoch ||
       now>INT64_MAX-REIST_APP_MS)return -22;
    if(s->info.type==X86OS_DIRECTORY)
        for(unsigned i=0;i<s->count;i++)if(!info_valid(&s->entries[i]))return -22;
    g->version=1;g->size=sizeof(*g);g->phase=REIST_APP_READY;
    g->root=root;g->child=child;g->epoch=epoch;g->previous=now;
    g->deadline=now+REIST_APP_MS;g->object=s;return 0;
}
void reist_app_revoke(reist_app_grant *g) {
    if(g){g->phase=REIST_APP_CLOSED;g->object=0;}
}
int reist_app_dispatch(reist_app_grant *g,const reist_app_snapshot *s,
    const reist_app_frame *q,reist_app_frame *out,uint64_t now) {
    if(!g || !q || !out)return -22;
    if(g->version!=1 || g->size!=sizeof(*g) || g->reserved || !g->root ||
       g->root>0x7fffffff || g->child<=g->root || g->child>0x7fffffff ||
       !g->epoch || g->sequence>REIST_APP_REQUESTS || g->phase<REIST_APP_READY ||
       g->phase>REIST_APP_CLOSED || g->deadline>INT64_MAX ||
       g->previous>g->deadline || g->deadline-g->previous>REIST_APP_MS)return -84;
    if(g->phase==REIST_APP_CLOSED)return -116;
    if(g->object!=s || !shape(s))return -84;
    if(now<g->previous)return -84;
    if(now>=g->deadline || g->sequence==REIST_APP_REQUESTS)return -110;
    if(q->version!=1 || q->size!=512 || q->flags || q->status || q->length ||
       q->reserved || !empty(q->payload,sizeof(q->payload)))return -22;
    if(q->child!=g->child)return -13;
    if(q->sequence!=g->sequence+1)return -116;
    if(q->operation>REIST_APP_CLOSE)return -95;
    if(q->operation==REIST_APP_HELLO) {
        if(g->phase!=REIST_APP_READY)return -116;
        if(q->root || q->epoch || q->deadline)return -13;
    } else {
        if(g->phase!=REIST_APP_BOUND)return -116;
        if(q->root!=g->root || q->epoch!=g->epoch)return -13;
        if(q->deadline!=g->deadline)return -116;
    }
    if(q->operation==REIST_APP_READ) {
        if(s->info.type!=X86OS_FILE)return -21;
        if(!q->requested || q->requested>REIST_APP_CHUNK || q->offset>s->length)return -22;
    } else if(q->operation==REIST_APP_READDIR) {
        if(s->info.type!=X86OS_DIRECTORY)return -20;
        if(q->requested || q->offset>s->count)return -22;
    } else if(q->offset || q->requested)return -22;
    reist_app_frame reply;
    for(unsigned i=0;i<sizeof(reply);i++)((volatile unsigned char *)&reply)[i]=0;
    reply.version=1;reply.size=512;reply.operation=q->operation;reply.flags=1;
    reply.root=g->root;reply.child=g->child;reply.epoch=g->epoch;
    reply.sequence=q->sequence;reply.deadline=g->deadline;
    reply.offset=q->offset;reply.requested=q->requested;
    if(q->operation==REIST_APP_HELLO || q->operation==REIST_APP_STAT) {
        reply.length=sizeof(s->info);copy(reply.payload,&s->info,sizeof(s->info));
    } else if(q->operation==REIST_APP_READ) {
        reply.length=s->length-q->offset;
        if(reply.length>q->requested)reply.length=q->requested;
        copy(reply.payload,s->bytes+q->offset,reply.length);
    } else if(q->operation==REIST_APP_READDIR && q->offset<s->count) {
        reply.status=1;reply.length=sizeof(s->info);
        copy(reply.payload,&s->entries[q->offset],sizeof(s->info));
    }
    g->sequence=q->sequence;g->previous=now;
    g->phase=q->operation==REIST_APP_CLOSE?REIST_APP_CLOSED:REIST_APP_BOUND;
    if(g->phase==REIST_APP_CLOSED)g->object=0;
    copy(out,&reply,sizeof(reply));return 0;
}
