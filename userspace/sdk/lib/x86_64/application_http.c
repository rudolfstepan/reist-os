#include <reist/x86_64/application_http.h>
static unsigned length(const char *p) {
    if(!p)return 257;
    unsigned n=0;while(n<=256&&p[n])n++;return n;
}
static int equal(const char *p,const char *q) {
    unsigned n=length(p),m=length(q);if(n>256||n!=m)return 0;
    for(unsigned i=0;i<n;i++)if(p[i]!=q[i])return 0;return 1;
}
static int url(const char *p) {
    static const char prefix[]="http://192.0.2.3";
    unsigned n=length(p);if(n<sizeof(prefix)-1||n>256)return 0;
    for(unsigned i=0;i<sizeof(prefix)-1;i++) {
        unsigned c=(unsigned char)p[i];if(i<4&&c>='A'&&c<='Z')c+=32;
        if(c!=(unsigned char)prefix[i])return 0;
    }
    unsigned i=sizeof(prefix)-1;
    if(p[i]==':') {if(n-i<3||p[i+1]!='8'||p[i+2]!='0')return 0;i+=3;}
    if(i<n&&p[i]!='/'&&p[i]!='?')return 0;
    for(;i<n;i++){unsigned c=(unsigned char)p[i];if(c<=32||c>=127||c=='#'||c=='\\')return 0;}
    return 1;
}
int reist_app_http_operand(int argc,const char *const *argv,reist_app_tcp_grant *out) {
    if(!argv||!out||argc<2||argc>5||!argv[0])return -22;
    unsigned include=0,maximum=0,selected=0;
    for(int i=1;i<argc;i++) {
        if(equal(argv[i],"-i")||equal(argv[i],"--include")) {if(include++)return -22;}
        else if(equal(argv[i],"--max-bytes")) {
            if(maximum++||++i>=argc)return -22;
            unsigned n=length(argv[i]),value=0;if(!n||n>3)return -22;
            for(unsigned j=0;j<n;j++){unsigned c=(unsigned char)argv[i][j];if(c<'0'||c>'9')return -22;value=value*10+c-'0';}
            if(!value||value>512)return -22;
        } else {if(selected++||!url(argv[i]))return -22;}
    }
    if(!selected)return -22;
    *out=(reist_app_tcp_grant){.version=1,.size=64,.protocol=6,.peer=REIST_APP_TCP_PEER,.peer_port=80};
    return 0;
}
