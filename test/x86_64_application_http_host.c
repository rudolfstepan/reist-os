#include <assert.h>
#include <string.h>
#include "userspace/programs/curl_http.h"
#include <reist/x86_64/application_http.h>
int main(void) {
    reist_app_tcp_grant grant,old;memset(&old,0xa5,sizeof(old));
    const char *good[]={"curl","-i","--max-bytes","512","HTTP://192.0.2.3:80/a?x=1"};
    assert(!reist_app_http_operand(5,good,&grant));
    assert(grant.version==1&&grant.size==64&&grant.protocol==6&&grant.peer==0xc0000203&&grant.peer_port==80);
    assert(!grant.application&&!grant.service&&!grant.root&&!grant.epoch&&!grant.expires&&!grant.reserved);
    const char *bad_url[]={"https://192.0.2.3/","http://192.0.2.4/","http://test.local/",
        "http://192.0.2.3:8080/","http://user@192.0.2.3/","http://192.0.2.3.evil/",
        "http://192.0.2.3/#x","http://192.0.2.3/a\r\nb","http://192.0.2.3/a b",0};
    for(unsigned i=0;i<sizeof(bad_url)/sizeof(*bad_url);i++) {
        const char *args[]={"curl",bad_url[i]};grant=old;
        assert(reist_app_http_operand(2,args,&grant)<0&&!memcmp(&grant,&old,sizeof(grant)));
    }
    const char *bad_args[][5]={{"curl","-o","out","http://192.0.2.3/",0},
        {"curl","--reist-ipc","42","http://192.0.2.3/",0},
        {"curl","--max-bytes","513","http://192.0.2.3/",0},
        {"curl","--max-bytes","0","http://192.0.2.3/",0},
        {"curl","-i","--include","http://192.0.2.3/",0},
        {"curl","-L","http://192.0.2.3/",0,0}};
    for(unsigned i=0;i<sizeof(bad_args)/sizeof(*bad_args);i++) {
        grant=old;assert(reist_app_http_operand(i==5?3:4,bad_args[i],&grant)<0);
        assert(!memcmp(&grant,&old,sizeof(grant)));
    }
    char long_url[258];memcpy(long_url,"http://192.0.2.3/",17);memset(long_url+17,'a',240);long_url[257]=0;
    const char *args[]={"curl",long_url};assert(reist_app_http_operand(2,args,&grant)<0);
    long_url[256]=0;assert(!reist_app_http_operand(2,args,&grant));
    assert(reist_app_http_operand(2,0,&grant)<0&&reist_app_http_operand(2,args,0)<0);
    static unsigned char head[600];reist_curl_response_head_t parsed;
    const char *prefix="HTTP/1.1 200 OK\r\nX-Large: ";unsigned n=(unsigned)strlen(prefix);
    memcpy(head,prefix,n);memset(head+n,'x',sizeof(head)-n-4);memcpy(head+sizeof(head)-4,"\r\n\r\n",4);
    assert(reist_curl_parse_response_head(head,sizeof(head),&parsed)<0);
    const unsigned char valid[]="HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\n";
    assert(!reist_curl_parse_response_head(valid,sizeof(valid)-1,&parsed));
    assert(parsed.status==200&&parsed.content_length==5);
    const unsigned char bad[]="HTTP/1.1 200 OK\r\nContent-Length: 5\r\nTransfer-Encoding: chunked\r\n\r\n";
    assert(reist_curl_parse_response_head(bad,sizeof(bad)-1,&parsed)<0);
    return 0;
}
