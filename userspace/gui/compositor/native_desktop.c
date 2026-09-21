/* Persistent native compositor. Policy remains in this isolated process. */
#include "native_render.h"
#include "../lib/native_surface.h"
#include <reist/x86_64/display.h>
#include <reist/x86_64/terminal.h>
static reist_native_role_args args;
static reist_native_compositor *state;
static reist_native_renderer *renderer;
static uint32_t endpoints[3],bound,integrated;
static uint64_t owners[4],health_ms[4],health_seq[4],reports[4],display_epoch;
static uint64_t previous_surfaces[2];
static struct { reist_gui_surface_message_t message;uint64_t end;unsigned active; } pending[2];
static int create(uint32_t *ep){return (int)reist_x64_syscall1(REIST_X64_SYS_IPC_CREATE,(uintptr_t)ep);}
static int close_ep(uint32_t ep){return (int)reist_x64_syscall1(REIST_X64_SYS_IPC_CLOSE,ep);}
static int report(unsigned type,unsigned role,unsigned flags,uint64_t value) {
    if(role>=4 || reports[role]==UINT64_MAX)return -75;
    reist_graphical_control c={1,64,type,role,args.epoch,
        type==REIST_GRAPHICAL_HEALTH||type==REIST_GRAPHICAL_FAILED?++reports[role]:1,
        owners[role],role?endpoints[role-1]:0,flags,value,0};
    return reist_native_control_send(args.endpoint,&c);
}
static int client_fail(unsigned n,int reason) {
    if(n>=2)return -22;
    uint64_t owner=state->clients[n].owner;
    if(!state->clients[n].active)return 0;
    uint32_t ep=state->clients[n].endpoint;
    reist_gui_surface_handle_t old=state->clients[n].surface;
    /* Close first: the old peer loses the input/output channel before reap. */
    if(close_ep(ep) || reist_native_client_revoke(state,n,owner))return -5;
    previous_surfaces[n]=(uint64_t)old.generation<<32|old.id;
    endpoints[n+1]=0;pending[n].active=0;
    integrated&=~(1U<<(n+2));
    return report(REIST_GRAPHICAL_FAILED,n+2,(unsigned)reason,0);
}
static int flush(unsigned n) {
    if(!pending[n].active)return 0;
    int r=reist_native_send(endpoints[n+1],&pending[n].message,sizeof(pending[n].message),0);
    if(r==-11)return reist_native_now()>=pending[n].end?-110:0;
    if(r)return r;pending[n].active=0;return 0;
}
static int enqueue(unsigned n,const reist_gui_surface_message_t *message) {
    if(pending[n].active)return -16;
    uint64_t now=reist_native_now();if(now>UINT64_MAX-100)return -75;
    pending[n].message=*message;pending[n].end=now+100;pending[n].active=1;return flush(n);
}
static int bind_role(const reist_graphical_control *q) {
    unsigned r=q->role;
    if(r<1 || r>3 || !reist_native_control_valid(q,REIST_GRAPHICAL_BIND,r,args.epoch,q->owner,1) ||
       (uint32_t)q->owner!=4+r || !(q->owner>>32) || q->owner>>32>0x7fffffff ||
       q->flags || q->value || q->endpoint!=endpoints[r-1] || !q->endpoint || bound&(1U<<r))return -71;
    int result=(int)reist_x64_syscall3(REIST_X64_SYS_IPC_DELEGATE,q->endpoint,q->owner>>32,r==1?1:3);
    if(result)return result;
    owners[r]=q->owner;bound|=1U<<r;
    integrated&=~(1U<<r);
    reports[r]=0;
    return report(REIST_GRAPHICAL_BOUND,r,0,0);
}
static int greet(unsigned role) {
    reist_graphical_control hello={1,64,REIST_GRAPHICAL_HELLO,role,args.epoch,1,
        owners[role],endpoints[role-1],0,role>=2?previous_surfaces[role-2]:0,0};
    return reist_native_control_send(endpoints[role-1],&hello);
}
static int receive_control(reist_graphical_control *q) {
    unsigned length=0;int r=reist_native_receive(args.endpoint,q,64,&length,0);
    if(r)return r;return length==64?0:-71;
}
static int draw(void) {
    reist_native_render_damage(renderer,state);
    if(!renderer->tiles[0] && !renderer->tiles[1])return 0;
    int due=reist_native_render_due(renderer,reist_native_now());if(due<=0)return due;
    for(unsigned n=0;n<4;n++) {
        unsigned x,y,width,height;int r=reist_native_render_tile(renderer,state,&x,&y,&width,&height);
        if(r<=0)return r;
        uint64_t now=reist_native_now();if(now>UINT64_MAX-100)return -75;
        reist_display_request_v1 q={1,64,REIST_DISPLAY_COMMIT,0,args.owner,display_epoch,
            now+100,(uintptr_t)renderer->pixels,x,y,(uint16_t)width,(uint16_t)height,256};
        r=(int)reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,30,(uintptr_t)&q);if(r)return r;
    }
    return 0;
}
static int input(void) {
    for(unsigned n=0;n<8;n++) {
        reist_input_event_v1 event;unsigned bytes=0;
        int r=reist_native_receive(endpoints[0],&event,64,&bytes,0);
        if(r==-11)return 0;if(r||bytes!=64)return -71;
        uint64_t now=reist_native_now();r=reist_native_input(state,&event,now);if(r)return r;
        health_ms[1]=now;
    }
    return 0;
}
static int client(unsigned n) {
    if(!state->clients[n].active)return 0;
    int r=flush(n);if(r)return client_fail(n,r);
    if(pending[n].active)return 0;
    for(unsigned turn=0;turn<8;turn++) {
        union { reist_gui_surface_message_t surface;reist_graphical_control control; } message;
        unsigned bytes=0;r=reist_native_receive(endpoints[n+1],&message,sizeof(message),&bytes,0);
        if(r==-11)break;if(r)return client_fail(n,r);
        uint64_t now=reist_native_now();
        if(bytes==64) {
            reist_graphical_control *q=&message.control;
            if(reist_graphical_charge(&state->clients[n].requests,now,128))return client_fail(n,-122);
            if(health_seq[n+2]==UINT64_MAX ||
               !reist_native_control_valid(q,REIST_GRAPHICAL_HEALTH,n+2,args.epoch,
                   owners[n+2],health_seq[n+2]+1) || q->flags!=1 || q->endpoint || q->value)
                return client_fail(n,-71);
            health_seq[n+2]=q->sequence;health_ms[n+2]=now;continue;
        }
        if(bytes!=sizeof(message.surface))return client_fail(n,-71);
        reist_gui_surface_message_t reply;
        r=reist_native_surface(state,n,&message.surface,&reply,now);
        if(r)return client_fail(n,r);
        if(message.surface.type!=REIST_GUI_SURFACE_PAINT_FILL &&
           message.surface.type!=REIST_GUI_SURFACE_PAINT_TEXT) {
            r=enqueue(n,&reply);if(r)return client_fail(n,r);
            if(pending[n].active)break;
        }
    }
    if(!pending[n].active) {
        reist_gui_surface_input_t e;
        if(!reist_native_client_event(state,n,&e)) {
            reist_gui_surface_message_t m={0};m.protocol_version=6;m.message_size=sizeof(m);
            m.type=REIST_GUI_SURFACE_INPUT;m.surface=state->clients[n].surface;m.input=e;
            r=enqueue(n,&m);if(r)return client_fail(n,r);
        }
    }
    if(state->failed_clients&(1U<<n))return client_fail(n,-75);
    if(!state->wm.windows[n].visible && state->clients[n].surface.id)return client_fail(n,0);
    return 0;
}
int main(int argc,char **argv) {
    if(reist_native_role_arguments(argc,argv,4,&args))return 22;
    owners[0]=args.owner;
    for(unsigned r=1;r<4;r++)if(create(&endpoints[r-1]))return 71;
    /* The root delegates the control endpoint immediately after CREATE-v6. */
    for(unsigned r=1;r<4;r++) {
        int result=-9;
        for(unsigned n=0;n<300 && reist_native_now()<args.deadline;n++) {
            result=report(REIST_GRAPHICAL_HELLO,r,0,0);
            if(result!=-9)break;if(reist_native_sleep(10))return 5;
        }
        if(result)return 71;
    }
    uint64_t input_epoch=0;
    for(unsigned turn=0;turn<300 && reist_native_now()<args.deadline;turn++) {
        reist_graphical_control q;int r=receive_control(&q);
        if(r==-11){if(reist_native_sleep(10))return 5;continue;}
        if(r)return 71;
        if(q.type==REIST_GRAPHICAL_BIND){if(bind_role(&q))return 71;continue;}
        if(bound!=14 || !reist_native_control_valid(&q,REIST_GRAPHICAL_READY,0,args.epoch,
            (uint64_t)args.peer_generation<<32,1) || q.flags!=31 || !q.value || q.endpoint)return 71;
        input_epoch=q.value;break;
    }
    if(!input_epoch)return 110;
    state=(void*)(uintptr_t)reist_x64_syscall1(REIST_X64_SYS_MALLOC,sizeof(*state));
    renderer=(void*)(uintptr_t)reist_x64_syscall1(REIST_X64_SYS_MALLOC,sizeof(*renderer));
    if((intptr_t)state<=0 || (intptr_t)renderer<=0 || sizeof(*state)+sizeof(*renderer)>2*1024*1024)return 12;
    reist_native_zero(renderer,sizeof(*renderer));
    if(reist_native_compositor_init(state,640,480,args.owner,owners[1],input_epoch))return 71;
    for(unsigned n=0;n<2;n++)if(reist_native_client_bind(state,n,owners[n+2],endpoints[n+1]) || greet(n+2))return 71;
    reist_display_request_v1 display={1,64,REIST_DISPLAY_QUERY,0,args.owner,0,0,0,0,0,0,0,0};
    int64_t epoch=reist_x64_syscall2(REIST_X64_SYS_DEVICE_CONTROL,30,(uintptr_t)&display);
    if(epoch<=0 || reist_x64_terminal_input(REIST_TERMINAL_ACQUIRE_SERVICE,0,0) ||
       reist_x64_terminal_input(REIST_TERMINAL_CHECK,0,0))return 71;
    display_epoch=(uint64_t)epoch;
    uint64_t last=reist_native_now(),heartbeat=last;unsigned ready=0;
    for(;;) {
        uint64_t now=reist_native_now();if(now<last || now>UINT64_MAX-1000)return 75;last=now;
        if(ready && args.mode!='0' && reist_native_fault_due(now,args.deadline) && reist_native_fault(args.mode))return 110;
        reist_graphical_control q;int control=receive_control(&q);
        if(!control) {
            if(reist_native_control_valid(&q,REIST_GRAPHICAL_STOP,0,args.epoch,
                (uint64_t)args.peer_generation<<32,2) && !q.endpoint && !q.flags && !q.value)return 0;
            /* Client replacement starts only after the old exact generation
             * has been reaped by root; create a fresh endpoint then bind. */
            if(q.type==REIST_GRAPHICAL_CLIENT_REAPED && q.role>=2 && q.role<4 &&
               reist_native_control_valid(&q,REIST_GRAPHICAL_CLIENT_REAPED,q.role,args.epoch,owners[q.role],2) &&
               !state->clients[q.role-2].active && !q.endpoint && !q.flags && !q.value) {
                unsigned role=q.role;if(create(&endpoints[role-1]))return 71;
                bound&=~(1U<<role);health_seq[role]=0;
                if(report(REIST_GRAPHICAL_HELLO,role,0,0))return 71;
            } else if(q.type==REIST_GRAPHICAL_BIND) {
                if(bind_role(&q) || q.role<2 || reist_native_client_bind(state,q.role-2,q.owner,q.endpoint) || greet(q.role))return 71;
                health_ms[q.role]=now;
            } else return 71;
        } else if(control!=-11)return 71;
        if(input() || client(0) || client(1) || draw())return 71;
        now=reist_native_now();
        if(!ready) {
            if(now>=args.deadline)return 110;
            unsigned complete=state->sequence && !renderer->tiles[0] && !renderer->tiles[1];
            for(unsigned n=0;n<2;n++)complete=complete && reist_native_client_ready(state,n,health_seq[n+2]);
            if(complete) {
                if(report(REIST_GRAPHICAL_READY,0,31,0))return 71;
                ready=1;integrated=15;heartbeat=now;
            }
        } else {
            if(now-health_ms[1]>=1000)return 110;
            for(unsigned n=0;n<2;n++)if(state->clients[n].active && now-health_ms[n+2]>=1000)
                if(client_fail(n,-110))return 71;
            if(!renderer->tiles[0] && !renderer->tiles[1])
                for(unsigned n=0;n<2;n++)if(reist_native_client_ready(state,n,health_seq[n+2]))integrated|=1U<<(n+2);
            if(now-heartbeat>=250 && !(args.mode=='l' && reist_native_fault_due(now,args.deadline))) {
                for(unsigned role=0;role<4;role++)if(integrated&(1U<<role))
                    if(report(REIST_GRAPHICAL_HEALTH,role,1,0))return 71;
                heartbeat=now;
            }
        }
        if(state->exit_requested){if(report(REIST_GRAPHICAL_STOP,0,0,0))return 71;return 0;}
        if(reist_native_sleep(10))return 5;
    }
}
