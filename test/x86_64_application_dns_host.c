/* Actual resolver transport/cache state and paired authority regressions. */
#ifdef REIST_DNS_CORE_TEST
#include <assert.h>
#include <string.h>
#include <reist/x86_64/application_dns.h>
static reist_app_udp_state udp;
static reist_app_tcp_state tcp;
int main(void) {
 uint64_t root=1ULL<<32,service=(3ULL<<32)|5,app=(4ULL<<32)|6;
 assert(!reist_app_udp_init(&udp,root,service,100));assert(!reist_app_tcp_init(&tcp,root,service,100));
 reist_app_tcp_grant g={1,64,root,app,service,1,6100,17,REIST_APP_TCP_PEER,49164,53,0};
 assert(!reist_app_dns_grant_set(&udp,&tcp,&g,100));
 assert(udp.active&&tcp.active&&udp.grant.protocol==17&&tcp.grant.protocol==6);
 reist_app_udp_request uq={.grant=udp.grant,.deadline=1100,.operation=REIST_APP_UDP_OPEN},ur;
 for(unsigned n=1;n<=4;n++) {
  uq.sequence=n;assert(!reist_app_dns_udp_admit(&udp,&uq));
  assert(!reist_app_udp_begin(&udp,&uq,&ur,100)&&!ur.result&&ur.handle==n);
 }
 uq.sequence=5;assert(reist_app_dns_udp_admit(&udp,&uq)==-24&&udp.issued==4&&udp.sequence==4);
 uq.operation=REIST_APP_UDP_CLOSE;uq.handle=2;
 assert(!reist_app_dns_udp_admit(&udp,&uq));assert(!reist_app_udp_begin(&udp,&uq,&ur,100));
 uq.operation=REIST_APP_UDP_OPEN;uq.handle=0;uq.sequence=6;
 assert(!reist_app_dns_udp_admit(&udp,&uq));
 assert(!reist_app_udp_begin(&udp,&uq,&ur,100)&&ur.handle==5);
 assert(reist_app_dns_grant_set(&udp,&tcp,&g,100)==-16);
 uint64_t seq[2]={0};reist_app_tcp_request q={.grant=g,.sequence=1},out={0};
 assert(!reist_app_dns_translate(&g,&q,&out,seq)&&out.sequence==1);
 q.grant.protocol=6;q.sequence=2;assert(!reist_app_dns_translate(&g,&q,&out,seq)&&out.sequence==1);
 q.grant.protocol=17;q.sequence=3;assert(!reist_app_dns_translate(&g,&q,&out,seq)&&out.sequence==2);
 q.grant.peer++;reist_app_tcp_request before=out;assert(reist_app_dns_translate(&g,&q,&out,seq)==-116&&!memcmp(&before,&out,sizeof(out)));
 assert(seq[0]==2&&seq[1]==1);
 reist_app_dns_revoke(&udp,&tcp);assert(!udp.active&&!tcp.active&&!udp.grant.epoch&&!tcp.grant.epoch);
 assert(reist_app_dns_grant_set(&udp,&tcp,&g,100)<0);
 /* TCP denial after UDP admission must leave neither live. */
 g.epoch=2;assert(reist_app_dns_grant_set(&udp,&tcp,&g,100)<0);assert(!udp.active&&!tcp.active);
 g.application=(5ULL<<32)|6;g.local_port=49168;g.epoch=3;assert(!reist_app_dns_grant_set(&udp,&tcp,&g,100));
 reist_app_dns_revoke(&udp,&tcp);
 const char *args[]={"nslookup","good.test","192.0.2.3"};assert(!reist_app_dns_operand(3,args,&g));
 args[2]="192.0.2.4";assert(reist_app_dns_operand(3,args,&g)==-13);
 return 0;
}
#else
#include "x86os.h"
#define main retained_dns_main
#define x86os_udp_sendto retained_udp_sendto
#define x86os_udp_recvfrom retained_udp_recvfrom
#define x86os_udp_socket_close retained_udp_close
#define x86os_tcp_socket_close retained_tcp_close
#include "test_dns_host.c"
#undef x86os_udp_sendto
#undef x86os_udp_recvfrom
#undef x86os_udp_socket_close
#undef x86os_tcp_socket_close
#undef main
#include <stdio.h>
static unsigned mode,wire_ttl=60,send_delay,receive_timeout;
static unsigned udp_close_delay,tcp_close_delay;
int x86os_udp_socket_close(x86os_udp_socket_t socket) {
 host_now+=udp_close_delay;return retained_udp_close(socket);
}
int x86os_tcp_socket_close(x86os_tcp_socket_t socket,uint32_t timeout) {
 if(tcp_close_delay>timeout)return -22;
 host_now+=tcp_close_delay;return retained_tcp_close(socket,timeout);
}
static uint8_t captured[512];static unsigned captured_size;static uint32_t server;
int x86os_udp_sendto(const x86os_udp_datagram_t *d,const void *data) {
 int r=retained_udp_sendto(d,data);if(r<0)return r;
 memcpy(captured,data,d->length);captured_size=d->length;server=d->ip;
 host_now+=send_delay;return r;
}
int x86os_udp_recvfrom(x86os_udp_datagram_t *d,void *data) {
 receive_timeout=d->timeout_ms;
 if(!mode)return retained_udp_recvfrom(d,data);
 uint8_t *p=data;memcpy(p,captured,captured_size);p[2]=0x81;p[3]=0x80;p[7]=1;
 uint8_t a[]={0xc0,0x0c,0,1,0,1,0,0,0,0,0,4,192,0,2,3};
 a[9]=(uint8_t)wire_ttl;memcpy(p+captured_size,a,sizeof(a));
 d->length=captured_size+sizeof(a);d->ip=server;d->source_port=53;
 if(mode==2||mode==6)p[2]|=2;
 if(mode==5||mode==6)host_now+=1200;
 if(mode==3)host_now+=d->timeout_ms+20;
 if(mode==4)host_now-=1000;
 return (int)d->length;
}
int main(void) {
 CHECK(retained_dns_main()==0);
 x86os_dns_result_t result,before;memset(&result,0xa5,sizeof(result));before=result;
 CHECK(x86os_dns_resolve_at("google.com",0,3000,&result)==-22);
 CHECK(!memcmp(&result,&before,sizeof(result)));
 mode=1;unsigned count=udp_queries;
 CHECK(!x86os_dns_resolve_at("Cache.Test.",0x0a000203,3000,&result));
 CHECK(!strcmp(result.canonical_name,"cache.test")&&!result.from_cache&&udp_queries==count+1);
 CHECK(!x86os_dns_resolve_at("cache.test",0x0a000203,3000,&result));
 CHECK(result.from_cache&&result.ttl_seconds<=60&&udp_queries==count+1);
 CHECK(!x86os_dns_resolve_at("cache.test",0x0a000204,3000,&result));
 CHECK(!result.from_cache&&udp_queries==count+2);
 wire_ttl=0;count=udp_queries;
 CHECK(!x86os_dns_resolve_at("zero.test",0x0a000203,3000,&result));
 CHECK(!x86os_dns_resolve_at("zero.test",0x0a000203,3000,&result));
 CHECK(!result.from_cache&&!result.ttl_seconds&&udp_queries==count+2);
 wire_ttl=2;count=udp_queries;
 CHECK(!x86os_dns_resolve_at("expiry.test",0x0a000203,3000,&result));host_now+=2100;
 CHECK(!x86os_dns_resolve_at("expiry.test",0x0a000203,3000,&result));CHECK(udp_queries==count+2&&!result.from_cache);
 send_delay=1800;CHECK(!x86os_dns_resolve_at("shared.test",0x0a000203,3000,&result));CHECK(receive_timeout<=1200);send_delay=0;
 mode=2;count=tcp_queries;CHECK(!x86os_dns_resolve_at("fallback.test",0x0a000203,3000,&result));CHECK(tcp_queries==count+1);
 mode=3;count=tcp_queries;memset(&result,0xa5,sizeof(result));before=result;
 send_delay=1800;CHECK(x86os_dns_resolve_at("late.test",0x0a000203,3000,&result)==-110);send_delay=0;
 CHECK(!memcmp(&result,&before,sizeof(result))&&tcp_queries==count);
 for(unsigned transport=0;transport<2;transport++) {
  mode=transport?6:5;send_delay=1100;
  udp_close_delay=transport?0:800;tcp_close_delay=transport?800:0;
  const char *name=transport?"tcp-cleanup.test":"udp-cleanup.test";
  CHECK(x86os_dns_resolve_at(name,0x0a000203,3000,&result)==-110);
  CHECK(!memcmp(&result,&before,sizeof(result)));
  mode=1;send_delay=udp_close_delay=tcp_close_delay=0;count=udp_queries;
  CHECK(!x86os_dns_resolve_at(name,0x0a000203,3000,&result));
  CHECK(!result.from_cache&&udp_queries==count+1);
  memset(&result,0xa5,sizeof(result));before=result;
 }
 mode=4;CHECK(x86os_dns_resolve_at("clock.test",0x0a000203,3000,&result)<0);
 CHECK(!memcmp(&result,&before,sizeof(result)));
 puts("DNS_RESOLVER_AUTHORITY_OK");return 0;
}
#endif
