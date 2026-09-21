#ifndef REIST_NATIVE_COMPOSITOR_SESSION_H
#define REIST_NATIVE_COMPOSITOR_SESSION_H
#include "desktop_wm.h"
#include "desktop_surface.h"
#include <reist/x86_64/graphical_session.h>
#include <reist/x86_64/input.h>
typedef struct {
    uint64_t owner;
    uint32_t endpoint,active;
    reist_gui_surface_handle_t surface;
    reist_graphical_rate requests;
} reist_native_gui_client;
typedef struct {
    desktop_wm_t wm;
    desktop_surface_manager_t surfaces;
    desktop_dirty_region_t dirty;
    reist_native_gui_client clients[2];
    reist_graphical_rate input_rate;
    uint64_t compositor,driver,epoch,sequence;
    int32_t x,y;
    uint32_t buttons,serial,failed_clients,exit_requested;
} reist_native_compositor;
int reist_native_compositor_init(reist_native_compositor *,unsigned width,unsigned height,
    uint64_t compositor,uint64_t driver,uint64_t epoch);
int reist_native_client_bind(reist_native_compositor *,unsigned index,uint64_t owner,uint32_t endpoint);
int reist_native_client_revoke(reist_native_compositor *,unsigned index,uint64_t owner);
int reist_native_client_ready(const reist_native_compositor *,unsigned index,uint64_t health_sequence);
int reist_native_surface(reist_native_compositor *,unsigned index,
    const reist_gui_surface_message_t *,reist_gui_surface_message_t *,uint64_t now);
int reist_native_input(reist_native_compositor *,const reist_input_event_v1 *,uint64_t now);
int reist_native_client_event(reist_native_compositor *,unsigned index,reist_gui_surface_input_t *);
#endif
