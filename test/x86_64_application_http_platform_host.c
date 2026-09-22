#include <assert.h>
#include <string.h>
#define main curl_program_main
#include "userspace/programs/curl.c"
#undef main
static uint64_t ticks;static unsigned opened,closed,sent,received,fragment,late;
static unsigned char emitted[2048];static unsigned emitted_n,wire_at,late_output;
static const char *wire;
int x86os_monotonic_ms(uint64_t *out){*out=ticks++;return 0;}
int x86os_tcp_socket_open(x86os_tcp_socket_t *out){opened++;*out=1;return 0;}
int x86os_tcp_socket_close(x86os_tcp_socket_t socket,uint32_t timeout){assert(socket==1&&timeout<=1000);closed++;return 0;}
int x86os_tcp_connect(const x86os_tcp_connect_t *q){assert(q->destination_ip==0xc0000203&&q->destination_port==80&&q->timeout_ms&&q->timeout_ms<=1500);return 0;}
int x86os_tcp_send(const x86os_tcp_io_t *q,const void *p){assert(p&&q->length<=512&&q->timeout_ms&&q->timeout_ms<=1500&&ticks-1+q->timeout_ms<=http_deadline);sent++;return (int)q->length;}
int x86os_tcp_receive(x86os_tcp_io_t *q,void *p){
 assert(q->length&&q->length<=512&&q->timeout_ms&&q->timeout_ms<=1500&&ticks-1+q->timeout_ms<=http_deadline);received++;
 unsigned n=(unsigned)strlen(wire)-wire_at;if(n>q->length)n=q->length;if(n>fragment)n=fragment;
 memcpy(p,wire+wire_at,n);wire_at+=n;if(late)ticks=http_deadline;return (int)n;
}
int x86os_write(int fd,const void *p,size_t n){assert(fd==1&&n<=sizeof(emitted)-emitted_n);memcpy(emitted+emitted_n,p,n);emitted_n+=(unsigned)n;if(late_output)ticks=http_deadline;return (int)n;}
void x86os_putchar(char c){assert(emitted_n<sizeof(emitted));emitted[emitted_n++]=(unsigned char)c;}
void x86os_puts(const char *p){while(*p)x86os_putchar(*p++);}
void x86os_print_number(int n){(void)n;}
int x86os_dns_resolve(const char *p,uint32_t t,x86os_dns_result_t *r){(void)p;(void)t;(void)r;assert(0);return -13;}
int x86os_create(const char *p){(void)p;assert(0);return -13;}
int x86os_close(int fd){(void)fd;assert(0);return -13;}
int x86os_rename(const char *a,const char *b){(void)a;(void)b;assert(0);return -13;}
int x86os_unlink(const char *p){(void)p;assert(0);return -13;}
void *x86os_malloc(size_t n){(void)n;assert(0);return 0;}
void x86os_free(void *p){(void)p;assert(0);}
int x86os_ipc_send_bulk_timeout(x86os_ipc_handle_t ep,const x86os_ipc_bulk_message_t *p,uint32_t t){(void)ep;(void)p;(void)t;assert(0);return -13;}
int x86os_sleep_ms(uint32_t ms){assert(ms&&ms<=100);ticks+=ms;return 0;}
int main(void){
 for(unsigned mode=0;mode<6;mode++){
  ticks=100;opened=closed=sent=received=emitted_n=wire_at=0;fragment=mode==1?1:512;late=mode==3;late_output=mode==5;
  wire=mode==2?"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nhello\r\n0\r\n\r\n":
    "HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nhello";
  char *args[]={"curl",mode==4?"https://192.0.2.3/":"http://192.0.2.3/",0};
  int r=curl_program_main(2,args);
  if(mode==4){assert(r==2&&!opened&&!sent&&!received&&!closed);continue;}
  assert(opened==1&&closed==1&&sent==1&&received);
  if(mode==3)assert(r==28&&(emitted_n<5||memcmp(emitted,"hello",5)));
  else if(mode==5)assert(r==28&&emitted_n>=5&&!memcmp(emitted,"hello",5));
  else assert(r==0&&emitted_n==5&&!memcmp(emitted,"hello",5));
 }
 return 0;
}
