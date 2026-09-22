#ifndef REIST_X86_64_APPLICATION_DNS_H
#define REIST_X86_64_APPLICATION_DNS_H
#include <reist/x86_64/application_tcp.h>
#include <reist/x86_64/application_udp.h>
#define REIST_APP_DNS_PORT 53U
int reist_app_dns_operand(int,const char *const *,reist_app_tcp_grant *);
int reist_app_dns_grant_set(reist_app_udp_state *,reist_app_tcp_state *,const reist_app_tcp_grant *,uint64_t);
void reist_app_dns_revoke(reist_app_udp_state *,reist_app_tcp_state *);
int reist_app_dns_udp_admit(const reist_app_udp_state *,const reist_app_udp_request *);
int reist_app_dns_translate(const reist_app_tcp_grant *,const reist_app_tcp_request *,reist_app_tcp_request *,uint64_t [2]);
#endif
