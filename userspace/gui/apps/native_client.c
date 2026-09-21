/* Two ordinary Surface clients sharing the unchanged public client library. */
#include "../lib/native_surface.h"
#include <reist/gui/surface_client.h>
#ifndef REIST_NATIVE_CLIENT
#define REIST_NATIVE_CLIENT 0
#endif
static reist_native_role_args args;
static reist_gui_surface_client_t client;
static char text[38]=" ";
static unsigned text_size,pointer_x=80,pointer_y=96,pressed;
static uint64_t health_sequence;
static int health(unsigned ready) {
    if(health_sequence==UINT64_MAX)return -75;
    reist_graphical_control c={1,64,REIST_GRAPHICAL_HEALTH,2+REIST_NATIVE_CLIENT,
        args.epoch,++health_sequence,args.owner,0,ready,0,0};
    return reist_native_control_send(args.endpoint,&c);
}
static int paint(void) {
    int r=reist_gui_surface_client_paint_begin(&client);if(r)return r;
    r=reist_gui_surface_client_paint_fill(&client,(reist_gui_rect_t){0,0,320,192},0x18222d);if(r)return r;
    const char *hint=REIST_NATIVE_CLIENT?"Move and click inside this window.":"Type here. Enter clears the line.";
    r=reist_gui_surface_client_paint_text(&client,12,16,296,hint,REIST_NATIVE_CLIENT?34:32,0xa7bbce,0x18222d);if(r)return r;
    r=reist_gui_surface_client_paint_text(&client,12,48,296,text,text_size?text_size:1,0xeaf2fa,0x18222d);if(r)return r;
    if(REIST_NATIVE_CLIENT) {
        unsigned x=pointer_x>303?303:pointer_x,y=pointer_y>175?175:pointer_y;
        r=reist_gui_surface_client_paint_fill(&client,(reist_gui_rect_t){(int)x,(int)y,16,16},pressed?0xedba54:0x52bec7);if(r)return r;
    }
    return reist_gui_surface_client_paint_commit(&client);
}
int main(int argc,char **argv) {
    if(reist_native_role_arguments(argc,argv,6+REIST_NATIVE_CLIENT,&args))return 22;
    reist_graphical_control hello;unsigned length=0;int r=-9;
    for(unsigned n=0;n<300 && reist_native_now()<args.deadline;n++) {
        r=reist_native_receive(args.endpoint,&hello,sizeof(hello),&length,0);
        if(r!=-9&&r!=-11)break;if(reist_native_sleep(10))return 5;
    }
    if(r || length!=64 || !reist_native_control_valid(&hello,REIST_GRAPHICAL_HELLO,
        2+REIST_NATIVE_CLIENT,args.epoch,args.owner,1) || hello.endpoint!=args.endpoint || hello.flags)return 71;
    reist_gui_surface_handle_t previous={(uint32_t)hello.value,(uint32_t)(hello.value>>32)};
    if((hello.value && (!previous.id || previous.id>REIST_GUI_SURFACE_MAX_SURFACES || !previous.generation)) ||
       (args.mode=='t' && !hello.value))return 71;
    if(reist_gui_surface_client_init(&client,args.endpoint) ||
       reist_gui_surface_client_create(&client,REIST_GUI_SURFACE_ROLE_TOPLEVEL,320,192) ||
       reist_gui_surface_client_ack_configure(&client,client.configured_serial) || paint() || health(1))return 71;
    uint64_t heartbeat=reist_native_now(),last=heartbeat,last_paint=heartbeat;
    unsigned dirty=0;
    for(;;) {
        uint64_t now=reist_native_now();if(now<last || now>UINT64_MAX-1000)return 75;last=now;
        if(args.mode!='0' && reist_native_fault_due(now,args.deadline)) {
            if(reist_native_fault(args.mode))return 110;
            if(args.mode=='m' || args.mode=='t') {
                reist_gui_surface_message_t bad={0};bad.protocol_version=6;bad.message_size=sizeof(bad);
                bad.type=REIST_GUI_SURFACE_PAINT_BEGIN;bad.surface=args.mode=='t'?previous:client.surface;
                bad.reserved=args.mode=='m'?1:0;
                if(reist_native_send(args.endpoint,&bad,sizeof(bad),100))return 71;
                args.mode='0';
            }
        }
        for(unsigned n=0;n<8;n++) {
            reist_gui_surface_message_t m;r=reist_gui_surface_client_receive(&client,&m,0);
            if(r==-11)break;if(r)return 71;
            if(m.type==REIST_GUI_SURFACE_CLOSE)return 0;
            if(m.type!=REIST_GUI_SURFACE_INPUT)continue;
            if(!m.input.serial || m.input.reserved)return 71;
            if(m.input.type==REIST_GUI_SURFACE_INPUT_KEYBOARD && m.input.pressed && !REIST_NATIVE_CLIENT) {
                unsigned key=m.input.key;
                if(key==8){if(text_size)text[--text_size]=0;}
                else if(key>=32 && key<=126 && text_size<37){text[text_size++]=(char)key;text[text_size]=0;}
                else if(key=='\n'){text_size=0;text[0]=' ';text[1]=0;}
                dirty=1;
            }
            if(REIST_NATIVE_CLIENT && (m.input.type==REIST_GUI_SURFACE_INPUT_POINTER_MOTION ||
                                       m.input.type==REIST_GUI_SURFACE_INPUT_POINTER_BUTTON)) {
                if(m.input.x<0||m.input.x>=320||m.input.y<0||m.input.y>=192)return 71;
                pointer_x=(unsigned)m.input.x;pointer_y=(unsigned)m.input.y;
                if(m.input.type==REIST_GUI_SURFACE_INPUT_POINTER_BUTTON)pressed=m.input.pressed;
                dirty=1;
            }
        }
        now=reist_native_now();
        /* <=Six requests/frame and <=10 frames/s retain the128 request budget. */
        if(dirty && now-last_paint>=100){if(paint())return 71;dirty=0;last_paint=reist_native_now();}
        now=reist_native_now();if(now-heartbeat>=250){if(health(1))return 71;heartbeat=now;}
        if(reist_native_sleep(10))return 5;
    }
}
