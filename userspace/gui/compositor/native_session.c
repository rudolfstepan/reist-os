/* Native adapter: trusted role binding, Surface-v6, compositor-local WM.
 * No syscalls, allocation, raw ports or kernel policy in this module. */
#include "native_session.h"
static void zero(void *p,unsigned bytes){unsigned char *d=p;while(bytes--)*d++=0;}
static reist_gui_surface_owner_t identity(const reist_native_gui_client *c) {
    return (reist_gui_surface_owner_t){(uint32_t)(c->owner>>32),(uint32_t)(c->owner>>32)};
}
static int same(reist_gui_surface_handle_t a,reist_gui_surface_handle_t b) {
    return a.id==b.id && a.generation==b.generation;
}
int reist_native_compositor_init(reist_native_compositor *c,unsigned width,unsigned height,
    uint64_t compositor,uint64_t driver,uint64_t epoch) {
    if(!c || width<640 || height<480 || width>1920 || height>1080 ||
       (uint32_t)compositor!=4 || !((compositor>>32)&0x7fffffff) || compositor>>63 ||
       (uint32_t)driver!=5 || !((driver>>32)&0x7fffffff) || driver>>63 || !epoch || epoch>>63)return -22;
    zero(c,sizeof(*c));c->compositor=compositor;c->driver=driver;c->epoch=epoch;c->x=8;c->y=8;
    desktop_surface_initialize(&c->surfaces);
    desktop_wm_initialize(&c->wm,width,height,28,(int32_t)height,24);
    /* First native clients use fixed geometry; move, focus, capture and close
     * are retained. No configure/resize promise is made by this adapter. */
    c->wm.resize_margin=0;
    for(unsigned n=0;n<2;n++) {
        c->wm.windows[n].x=20+(int)n*240;c->wm.windows[n].y=40+(int)n*160;
        c->wm.windows[n].width=326;c->wm.windows[n].height=219;
        c->wm.windows[n].flags=DESKTOP_WM_WINDOW_STATE_BLOCKED;
    }
    desktop_dirty_initialize(&c->dirty,width,height);desktop_dirty_full(&c->dirty);return 0;
}
int reist_native_client_bind(reist_native_compositor *c,unsigned n,uint64_t owner,uint32_t ep) {
    if(!c || n>=2 || !ep || (uint32_t)owner!=6+n || !(owner>>32) || owner>>32>0x7fffffff)return -22;
    reist_native_gui_client *p=&c->clients[n];
    if(p->active)return -16;
    if(owner>>32<=p->owner>>32)return -116;
    zero(p,sizeof(*p));p->owner=owner;p->endpoint=ep;p->active=1;
    c->failed_clients&=~(1U<<n);return 0;
}
int reist_native_client_revoke(reist_native_compositor *c,unsigned n,uint64_t owner) {
    if(!c || n>=2 || !owner)return -22;
    reist_native_gui_client *p=&c->clients[n];
    if(p->owner!=owner)return -116;
    if(!p->active)return 0;
    desktop_surface_revoke_owner(&c->surfaces,identity(p));
    desktop_rect_t damage=desktop_wm_window_bounds(&c->wm,n);
    desktop_wm_close(&c->wm,n);desktop_dirty_add(&c->dirty,damage);
    p->active=0;p->endpoint=0;p->surface=(reist_gui_surface_handle_t){0,0};return 0;
}
int reist_native_client_ready(const reist_native_compositor *c,unsigned n,uint64_t health) {
    if(!c || n>=2 || !health)return 0;
    const reist_native_gui_client *p=&c->clients[n];
    if(!p->active || !p->owner || !p->endpoint || !p->surface.id ||
       p->surface.id>DESKTOP_SURFACE_CAPACITY || !c->wm.windows[n].visible)return 0;
    const desktop_surface_slot_t *s=&c->surfaces.slots[p->surface.id-1];
    reist_gui_surface_owner_t expected=identity(p);
    return s->active && same(s->handle,p->surface) && s->owner.pid==expected.pid &&
        s->owner.process_generation==expected.process_generation && s->configured_serial &&
        s->acknowledged_serial==s->configured_serial && s->paint_generation;
}
int reist_native_surface(reist_native_compositor *c,unsigned n,
    const reist_gui_surface_message_t *q,reist_gui_surface_message_t *reply,uint64_t now) {
    if(!c || n>=2 || !q || !reply || q==reply || q->reserved ||
       q->protocol_version!=6 || q->message_size!=sizeof(*q))return -22;
    reist_native_gui_client *p=&c->clients[n];
    if(!p->active)return -116;
    if(q->type==REIST_GUI_SURFACE_PAINT_TEXT || q->type==REIST_GUI_SURFACE_SET_TITLE) {
        if(!q->byte_size || q->byte_size>=REIST_GUI_SURFACE_PAINT_TEXT_CAPACITY)return -22;
        const unsigned char *text=(const unsigned char*)&q->input;
        for(unsigned i=0;i<q->byte_size;i++)if(text[i]>=128)return -95;
    }
    if(q->type==REIST_GUI_SURFACE_CREATE) {
        if(p->surface.id)return -16;
        if(c->surfaces.next_generation==UINT32_MAX || c->surfaces.next_configure_serial==UINT32_MAX ||
           c->wm.next_generation==UINT32_MAX)return -75;
        if(q->flags!=REIST_GUI_SURFACE_ROLE_TOPLEVEL || q->width!=320 || q->height!=192 ||
           q->surface.id || q->surface.generation || q->parent_surface.id || q->parent_surface.generation)return -22;
    } else if(!p->surface.id || !same(q->surface,p->surface))return -116;
    if(p->surface.id && c->surfaces.slots[p->surface.id-1].paint_generation==UINT32_MAX)return -75;
    /* Retained paint only; pixel-buffer capabilities and optional applet
     * launch requests have no native backing and get the conventional error. */
    if(q->type!=REIST_GUI_SURFACE_CREATE && q->type!=REIST_GUI_SURFACE_DESTROY &&
       q->type!=REIST_GUI_SURFACE_ACK_CONFIGURE && q->type!=REIST_GUI_SURFACE_SET_TITLE &&
       (q->type<REIST_GUI_SURFACE_PAINT_BEGIN || q->type>REIST_GUI_SURFACE_PAINT_HOVER_COMMIT))return -95;
    int r=reist_graphical_charge(&p->requests,now,128);if(r)return r;
    r=desktop_surface_dispatch_message(&c->surfaces,identity(p),q,reply);
    if(r)return r;
    if(q->type==REIST_GUI_SURFACE_CREATE) {
        p->surface=reply->surface;
        c->surfaces.slots[p->surface.id-1].window_index=n;
        desktop_wm_event_t e={0};e.type=DESKTOP_WM_EVENT_OPEN;e.target=n;
        desktop_wm_dispatch_result_t result;
        if(desktop_wm_dispatch(&c->wm,&e,&result))return -5;
        desktop_dirty_add_regions(&c->dirty,&result.dirty);
    } else if(q->type==REIST_GUI_SURFACE_DESTROY) {
        desktop_dirty_add(&c->dirty,desktop_wm_window_bounds(&c->wm,n));
        desktop_wm_close(&c->wm,n);p->surface=(reist_gui_surface_handle_t){0,0};
    } else {
        reist_gui_rect_t damage;
        if(!desktop_surface_present_damage_take(&c->surfaces,identity(p),p->surface,&damage)) {
            desktop_window_t *w=&c->wm.windows[n];
            desktop_dirty_add(&c->dirty,(desktop_rect_t){w->x+3+damage.x,w->y+24+damage.y,damage.width,damage.height});
        }
    }
    return 0;
}
static int local_event(reist_native_compositor *c,int target,unsigned type,
                       unsigned button,unsigned pressed,unsigned key,int dx,int dy) {
    if(target<0 || target>=2)return 0;
    reist_native_gui_client *p=&c->clients[target];
    if(!p->active || !p->surface.id)return 0;
    if(c->serial==UINT32_MAX)return -75;
    desktop_window_t *w=&c->wm.windows[target];
    int x=c->x-w->x-3,y=c->y-w->y-24;
    /* Existing Surface-v6 requires in-area positions, also during an outside
     * implicit grab. Clamp locally; preserve signed relative motion. */
    if(x<0)x=0;if(x>319)x=319;if(y<0)y=0;if(y>191)y=191;
    reist_gui_surface_input_t e={type,++c->serial,x,y,dx,dy,button,pressed,key,0};
    if(type==REIST_GUI_SURFACE_INPUT_KEYBOARD)e.x=e.y=0;
    int r=desktop_surface_input_enqueue(&c->surfaces,identity(p),p->surface,&e);
    if(r){c->failed_clients|=1U<<(unsigned)target;return 0;}
    return 0;
}
static unsigned character(unsigned scan,unsigned flags) {
    static const char plain[89]="\0\0331234567890-=\b\tqwertyuiop[]\n\0asdfghjkl;'`\0\\zxcvbnm,./\0*\0 \0";
    static const char shift[89]="\0\033!@#$%^&*()_+\b\tQWERTYUIOP{}\n\0ASDFGHJKL:\"~\0|ZXCVBNM<>?\0*\0 \0";
    if(scan>=89 || flags&2)return 0;
    unsigned key=(unsigned char)((flags&4)?shift[scan]:plain[scan]);
    if(flags&32){if(key>='a'&&key<='z')key-=32;else if(key>='A'&&key<='Z')key+=32;}
    return key;
}
static int dispatch(reist_native_compositor *c,unsigned type,unsigned pressed) {
    desktop_wm_event_t e={type,c->x,c->y,DESKTOP_WM_BUTTON_LEFT,pressed,0,0};
    desktop_wm_dispatch_result_t result;
    int r=desktop_wm_dispatch(&c->wm,&e,&result);if(r)return r;
    desktop_dirty_add_regions(&c->dirty,&result.dirty);return 0;
}
int reist_native_input(reist_native_compositor *c,const reist_input_event_v1 *e,uint64_t now) {
    if(!c || !e)return -22;
    if(e->version!=2 || e->size!=64 || e->owner!=c->driver || e->target!=c->compositor ||
       e->epoch!=c->epoch || c->sequence==UINT64_MAX || e->sequence!=c->sequence+1)return -116;
    if(!c->sequence && e->type!=REIST_INPUT_HEALTHY)return -116;
    if(e->type==REIST_INPUT_HEALTHY) {
        if(e->flags||e->code||e->dx||e->dy||e->buttons)return -116;
    } else if(e->type==REIST_INPUT_KEY) {
        if(e->flags&~63U || e->code<=0 || e->code>0x58 || e->dx || e->dy || e->buttons)return -116;
    } else if(e->type==REIST_INPUT_POINTER) {
        if(e->flags || e->code || e->dx< -256 || e->dx>255 || e->dy< -256 || e->dy>255 || e->buttons>7)return -116;
    } else return -116;
    int r=reist_graphical_charge(&c->input_rate,now,128);if(r)return r;
    c->sequence=e->sequence;
    if(e->type==REIST_INPUT_HEALTHY)return 0;
    if(e->type==REIST_INPUT_KEY) {
        if(!(e->flags&1) && e->code==0x0f && e->flags&16) {
            int next=c->wm.keyboard_focus==0?1:0;
            desktop_wm_event_t event={0};event.type=DESKTOP_WM_EVENT_SELECT;event.target=(unsigned)next;
            desktop_wm_dispatch_result_t result;
            if(desktop_wm_dispatch(&c->wm,&event,&result))return -5;
            desktop_dirty_add_regions(&c->dirty,&result.dirty);return 0;
        }
        if(e->code==1 && !(e->flags&1)){c->exit_requested=1;return 0;}
        unsigned key=character((unsigned)e->code,e->flags);
        return key?local_event(c,c->wm.keyboard_focus,REIST_GUI_SURFACE_INPUT_KEYBOARD,0,!(e->flags&1),key,0,0):0;
    }
    int oldx=c->x,oldy=c->y;
    c->x+=e->dx;c->y-=e->dy;
    if(c->x<0)c->x=0;if(c->y<0)c->y=0;
    if((unsigned)c->x>=c->wm.screen_width)c->x=(int)c->wm.screen_width-1;
    if((unsigned)c->y>=c->wm.screen_height)c->y=(int)c->wm.screen_height-1;
    desktop_dirty_add(&c->dirty,(desktop_rect_t){oldx,oldy,8,12});
    desktop_dirty_add(&c->dirty,(desktop_rect_t){c->x,c->y,8,12});
    r=dispatch(c,DESKTOP_WM_EVENT_POINTER_MOTION,0);if(r)return r;
    int target=c->wm.capture_kind==DESKTOP_WM_CAPTURE_CLIENT?c->wm.capture_window:
        c->wm.capture_kind==DESKTOP_WM_CAPTURE_NONE?desktop_wm_window_at(&c->wm,c->x,c->y):-1;
    if(target>=0 && target<2 && c->wm.capture_kind!=DESKTOP_WM_CAPTURE_CLIENT) {
        const desktop_window_t *w=&c->wm.windows[target];
        if(c->x<w->x+3 || c->x>=w->x+323 || c->y<w->y+24 || c->y>=w->y+216)target=-1;
    }
    if(c->x!=oldx || c->y!=oldy) {
        r=local_event(c,target,REIST_GUI_SURFACE_INPUT_POINTER_MOTION,0,0,0,c->x-oldx,c->y-oldy);if(r)return r;
    }
    for(unsigned button=0;button<3;button++)if((c->buttons^e->buttons)&(1U<<button)) {
        unsigned pressed=(e->buttons>>button)&1;
        int previous=c->wm.capture_kind==DESKTOP_WM_CAPTURE_CLIENT?c->wm.capture_window:-1;
        if(!button){r=dispatch(c,DESKTOP_WM_EVENT_POINTER_BUTTON,pressed);if(r)return r;}
        target=previous>=0?previous:c->wm.capture_kind==DESKTOP_WM_CAPTURE_CLIENT?c->wm.capture_window:-1;
        r=local_event(c,target,REIST_GUI_SURFACE_INPUT_POINTER_BUTTON,button+1,pressed,0,0,0);if(r)return r;
    }
    c->buttons=e->buttons;return 0;
}
int reist_native_client_event(reist_native_compositor *c,unsigned n,reist_gui_surface_input_t *e) {
    if(!c || n>=2 || !e)return -22;
    reist_native_gui_client *p=&c->clients[n];
    if(!p->active || !p->surface.id)return -116;
    return desktop_surface_input_dequeue(&c->surfaces,identity(p),p->surface,e);
}
