#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include <reist/x86_64/network_session.h>
int main(void) {
    reist_net_channel a,b;reist_net_message q;uint64_t root=1ULL<<32,child=(3ULL<<32)|4;
    assert(!reist_net_channel_init(&a,17,root,child,99));
    assert(!reist_net_channel_init(&b,17,child,root,99));
    const uint8_t bytes[]={1,2,3};
    assert(!reist_net_encode(&a,&q,REIST_NET_CONTROL,bytes,3,0,100,200));
    reist_net_channel old=b;
    q.payload[3]=1;assert(reist_net_decode(&b,&q,101)==-71&&memcmp(&b,&old,sizeof(b))==0);
    q.payload[3]=0;q.owner=child;assert(reist_net_decode(&b,&q,101)==-116);
    q.owner=root;q.epoch=98;assert(reist_net_decode(&b,&q,101)==-116);
    q.epoch=99;assert(reist_net_decode(&b,&q,200)==-110);
    assert(!reist_net_decode(&b,&q,101));old=b;
    assert(reist_net_decode(&b,&q,102)==-116&&memcmp(&b,&old,sizeof(b))==0);
    old=a;assert(reist_net_encode(&a,&q,REIST_NET_CONTROL,q.payload,3,0,102,200)==-22);
    assert(memcmp(&a,&old,sizeof(a))==0);
    a.sent=UINT64_MAX;assert(reist_net_encode(&a,&q,REIST_NET_CONTROL,bytes,3,0,102,200)==-75);
    puts("NETWORK_SESSION_HOST_OK");return 0;
}
