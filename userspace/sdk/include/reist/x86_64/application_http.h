#ifndef REIST_X86_64_APPLICATION_HTTP_H
#define REIST_X86_64_APPLICATION_HTTP_H
#include <reist/x86_64/application_tcp.h>
/* Authority admission only; actual HTTP parsing remains in ordinary curl. */
int reist_app_http_operand(int argc,const char *const *argv,reist_app_tcp_grant *out);
#endif
