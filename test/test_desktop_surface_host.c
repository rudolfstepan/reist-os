#include <assert.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include "userspace/gui/compositor/desktop_surface.h"
#include "reist/gui/font_catalog.h"

#ifdef REIST_NATIVE_FULL_DESKTOP
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"atomic line failed: %s\n",#x); exit(1); } } while(0)
static void atomic_line_test(void) {
    static desktop_surface_manager_t m;
    static desktop_surface_slot_t before;
    reist_gui_surface_owner_t o={42,7};
    reist_gui_surface_handle_t h;
    reist_gui_surface_configure_t c;
    desktop_surface_initialize(&m);
    CHECK(!desktop_surface_create(&m,o,REIST_GUI_SURFACE_ROLE_TOPLEVEL,320,192,&h,&c));
    reist_gui_surface_message_t q={0},r;
    q.protocol_version=6;q.message_size=sizeof(q);q.type=24;q.surface=h;
    q.serial=c.serial;q.format=1;q.flags=0xeaf2fa;q.buffer_id=0x18222d;
    q.damage=(reist_gui_rect_t){12,48,296,16};q.byte_size=3;
    memcpy(&q.input,"abc",3);
    before=m.slots[h.id-1];
    CHECK(desktop_surface_dispatch_message(&m,o,&q,&r)<0);
    CHECK(!memcmp(&before,&m.slots[h.id-1],sizeof(before)));
    CHECK(!desktop_surface_ack_configure(&m,o,h,c.serial));
    CHECK(!desktop_surface_dispatch_message(&m,o,&q,&r));
    CHECK(r.type==24 && r.serial==c.serial && !r.flags);
    desktop_surface_slot_t *slot=&m.slots[h.id-1];
    CHECK(slot->committed_dynamic_paint_count==1 && slot->paint_generation);
    CHECK(!memcmp(slot->committed_dynamic_paint[0].text,"abc",3));
    before=*slot;
    for(unsigned n=0;n<19;n++) {
        reist_gui_surface_message_t bad=q;reist_gui_surface_owner_t wrong=o;
        switch(n) {
        case 0:bad.reserved=1;break; case 1:bad.format=2;break;
        case 2:bad.serial++;break;case 3:bad.surface.generation++;break;
        case 4:wrong.process_generation++;break;case 5:bad.byte_size=40;break;
        case 6:bad.byte_size=0;break;case 7:((char *)&bad.input)[0]=1;break;
        case 8:((char *)&bad.input)[39]=1;break;case 9:bad.damage.x=-1;break;
        case 10:bad.damage.height=17;break;case 11:bad.damage.width=321;break;
        case 12:bad.flags|=0xff000000;break;case 13:bad.buffer_id|=0xff000000;break;
        case 14:bad.width=1;break;case 15:bad.parent_surface.id=1;break;
        case 16:bad.buffer_generation=1;break;case 17:bad.stride_bytes=1;break;
        default:bad.damage.width=8;break;
        }
        CHECK(desktop_surface_dispatch_message(&m,wrong,&bad,&r)<0);
        CHECK(!memcmp(&before,slot,sizeof(before)));
    }
    CHECK(!desktop_surface_paint_begin(&m,o,h));before=*slot;
    CHECK(desktop_surface_dispatch_message(&m,o,&q,&r)<0);
    CHECK(!memcmp(&before,slot,sizeof(before)));
    CHECK(!desktop_surface_paint_commit(&m,o,h));
    CHECK(!desktop_surface_dispatch_message(&m,o,&q,&r));before=*slot;
    CHECK(!desktop_surface_dispatch_message(&m,o,&q,&r));
    CHECK(!memcmp(&before,slot,sizeof(before))); /* identical frame causes no damage */
    q.byte_size=1;memset(&q.input,0,sizeof(q.input));memcpy(&q.input,"x",1);
    CHECK(!desktop_surface_dispatch_message(&m,o,&q,&r));
    CHECK(slot->committed_dynamic_paint[0].text_length==1);
    CHECK(slot->committed_dynamic_paint[0].rect.width==296);
    desktop_surface_revoke_owner(&m,o);before=*slot;
    CHECK(desktop_surface_dispatch_message(&m,o,&q,&r)<0);
    CHECK(!memcmp(&before,slot,sizeof(before)));
}
#endif

int main(void) {
#ifdef REIST_NATIVE_FULL_DESKTOP
    atomic_line_test();
#endif
    desktop_surface_manager_t manager;
    desktop_surface_initialize(&manager);
    reist_gui_surface_owner_t owner = {42U, 7U};
    reist_gui_surface_owner_t other_owner = {43U, 1U};
    reist_gui_surface_handle_t handle;
    reist_gui_surface_configure_t configure;
    assert(desktop_surface_create(&manager, owner,
        REIST_GUI_SURFACE_ROLE_TOPLEVEL, 320U, 200U,
        &handle, &configure) == 0);
    assert(desktop_surface_ack_configure(&manager, owner, handle,
        configure.serial) == 0);
    reist_gui_surface_handle_t dialog;
    reist_gui_surface_configure_t dialog_configure;
    assert(desktop_surface_create_dialog(&manager, owner, handle,
        300U, 160U, &dialog, &dialog_configure) == 0);
    assert(manager.slots[dialog.id - 1U].role ==
        REIST_GUI_SURFACE_ROLE_DIALOG);
    assert(manager.slots[dialog.id - 1U].parent.id == handle.id);
    assert(desktop_surface_create_dialog(&manager, owner, handle,
        300U, 160U, &dialog, &dialog_configure) == DESKTOP_SURFACE_ESTATE);
    assert(desktop_surface_destroy(&manager, owner, handle) ==
        DESKTOP_SURFACE_ESTATE);
    assert(desktop_surface_ack_configure(&manager, owner, dialog,
        dialog_configure.serial) == 0);
    assert(desktop_surface_destroy(&manager, owner, dialog) == 0);
    assert(desktop_surface_set_title(
        &manager, owner, handle, "Editor", 6U) == 0);
    assert(desktop_surface_paint_begin(&manager, owner, handle) == 0);
    assert(desktop_surface_paint_fill(
        &manager, owner, handle,
        (reist_gui_rect_t){0, 0, 320U, 200U}, 0x00ffffffU) == 0);
    assert(desktop_surface_paint_text(
        &manager, owner, handle,
        (reist_gui_rect_t){8, 8, 120U, 1U}, 0U, 0x00ffffffU,
        "Document", 8U) == 0);
    assert(desktop_surface_paint_font_text(
        &manager, owner, handle,
        (reist_gui_rect_t){8, 24, 120U, 16U}, 0U, 0x00ffffffU,
        "Font", 4U, REIST_GUI_FONT_FAMILY_UNIFONT, 11U) ==
        DESKTOP_SURFACE_EINVAL);
    assert(desktop_surface_paint_font_text(
        &manager, owner, handle,
        (reist_gui_rect_t){8, 24, 120U, 16U}, 0U, 0x00ffffffU,
        "Font", 4U, 99U, 16U) == DESKTOP_SURFACE_EINVAL);
    assert(desktop_surface_paint_font_text(
        &manager, owner, handle,
        (reist_gui_rect_t){8, 24, 120U, 16U}, 0U, 0x00ffffffU,
        "Font", 4U, REIST_GUI_FONT_FAMILY_UNIFONT, 16U) == 0);
    assert(desktop_surface_paint_commit(&manager, owner, handle) == 0);
    desktop_surface_slot_t *painted = &manager.slots[handle.id - 1U];
    assert(painted->committed_paint_count == 3U);
    assert(painted->committed_paint[2].type ==
           DESKTOP_SURFACE_PAINT_FONT_TEXT);
    assert(painted->committed_paint[2].font_family ==
           REIST_GUI_FONT_FAMILY_UNIFONT);
    assert(painted->committed_paint[2].font_height == 16U);
    assert(painted->paint_generation != 0U);
    reist_gui_rect_t present_damage;
    assert(desktop_surface_present_damage_take(
        &manager, owner, handle, &present_damage) == 0);
    assert(present_damage.x == 0 && present_damage.y == 0 &&
           present_damage.width == 320U && present_damage.height == 200U);
    uint32_t base_generation = painted->paint_generation;
    assert(desktop_surface_paint_begin_layer(
        &manager, owner, handle, 4U) == DESKTOP_SURFACE_EINVAL);
    assert(!painted->paint_active &&
           painted->paint_generation == base_generation);
    assert(desktop_surface_paint_begin_layer(
        &manager, owner, handle,
        REIST_GUI_SURFACE_PAINT_LAYER_OVERLAY) == 0);
    assert(desktop_surface_paint_begin(
        &manager, owner, handle) == DESKTOP_SURFACE_ESTATE);
    assert(desktop_surface_paint_fill(
        &manager, owner, handle,
        (reist_gui_rect_t){4, 4, 80U, 24U}, 0x00000080U) == 0);
    assert(desktop_surface_paint_commit(
        &manager, owner, handle) == DESKTOP_SURFACE_ESTATE);
    assert(desktop_surface_paint_commit_layer(
        &manager, owner, handle,
        REIST_GUI_SURFACE_PAINT_LAYER_OVERLAY) == 0);
    assert(painted->committed_paint_count == 3U);
    assert(painted->committed_overlay_paint_count == 1U);
    assert(painted->committed_overlay_paint[0].foreground == 0x00000080U);
    assert(desktop_surface_present_damage_take(
        &manager, owner, handle, &present_damage) == 0);
    assert(present_damage.x == 4 && present_damage.y == 4 &&
           present_damage.width == 80U && present_damage.height == 24U);
    uint32_t overlay_generation = painted->paint_generation;
    assert(desktop_surface_paint_begin_layer(
        &manager, owner, handle,
        REIST_GUI_SURFACE_PAINT_LAYER_DYNAMIC) == 0);
    assert(desktop_surface_paint_text(
        &manager, owner, handle,
        (reist_gui_rect_t){8, 40, 120U, 1U}, 0U, 0x00ffffffU,
        "Dynamic", 7U) == 0);
    assert(desktop_surface_paint_commit_layer(
        &manager, owner, handle,
        REIST_GUI_SURFACE_PAINT_LAYER_DYNAMIC) == 0);
    assert(painted->committed_dynamic_paint_count == 1U);
    assert(desktop_surface_paint_begin_layer(
        &manager, owner, handle,
        REIST_GUI_SURFACE_PAINT_LAYER_HOVER) == 0);
    for (uint32_t hover = 0U;
         hover < REIST_GUI_SURFACE_MAX_HOVER_PAINT_COMMANDS; ++hover)
        assert(desktop_surface_paint_fill(
            &manager, owner, handle,
            (reist_gui_rect_t){(int32_t)(4U + hover), 4, 1U, 1U},
            hover) == 0);
    assert(desktop_surface_paint_fill(
        &manager, owner, handle,
        (reist_gui_rect_t){12, 4, 1U, 1U}, 0U) ==
        DESKTOP_SURFACE_ECAPACITY);
    assert(desktop_surface_paint_commit_layer(
        &manager, owner, handle,
        REIST_GUI_SURFACE_PAINT_LAYER_HOVER) == 0);
    assert(painted->committed_hover_paint_count ==
           REIST_GUI_SURFACE_MAX_HOVER_PAINT_COMMANDS);
    assert(desktop_surface_present_damage_take(
        &manager, owner, handle, &present_damage) == 0);
    overlay_generation = painted->paint_generation;
    assert(desktop_surface_paint_begin_layer(
        &manager, owner, handle,
        REIST_GUI_SURFACE_PAINT_LAYER_OVERLAY) == 0);
    assert(desktop_surface_paint_fill(
        &manager, owner, handle,
        (reist_gui_rect_t){4, 4, 80U, 24U}, 0x00000080U) == 0);
    assert(desktop_surface_paint_commit_layer(
        &manager, owner, handle,
        REIST_GUI_SURFACE_PAINT_LAYER_OVERLAY) == 0);
    assert(painted->paint_generation == overlay_generation);
    assert(desktop_surface_present_damage_take(
        &manager, owner, handle, &present_damage) == DESKTOP_SURFACE_ESTATE);
    assert(desktop_surface_paint_begin(&manager, owner, handle) == 0);
    assert(desktop_surface_paint_fill(
        &manager, owner, handle,
        (reist_gui_rect_t){0, 0, 320U, 200U}, 0x00ffffffU) == 0);
    assert(desktop_surface_paint_commit(&manager, owner, handle) == 0);
    assert(painted->committed_paint_count == 1U);
    assert(painted->committed_overlay_paint_count == 1U);
    assert(desktop_surface_present_damage_take(
        &manager, owner, handle, &present_damage) == 0);
    assert(present_damage.x == 8 && present_damage.y == 8 &&
           present_damage.width == 120U && present_damage.height == 32U);
    reist_gui_surface_input_t input = {
        REIST_GUI_SURFACE_INPUT_POINTER_MOTION, 1U, 12, 8,
        1, -1, 0U, 0U, 0U, 0U};
    assert(desktop_surface_input_enqueue(
        &manager, owner, handle, &input) == 0);
    assert(desktop_surface_input_dequeue(
        &manager, other_owner, handle, &input) < 0);
    reist_gui_surface_input_t received_input;
    assert(desktop_surface_input_dequeue(
        &manager, owner, handle, &received_input) == 0);
    assert(received_input.serial == 1U && received_input.x == 12);
    input.type = REIST_GUI_SURFACE_INPUT_KEYBOARD;
    input.key = 'a';
    for (uint32_t event_index = 0U;
         event_index < REIST_GUI_SURFACE_MAX_PENDING_EVENTS; ++event_index) {
        input.serial = event_index + 2U;
        assert(desktop_surface_input_enqueue(
            &manager, owner, handle, &input) == 0);
    }
    assert(desktop_surface_input_enqueue(
        &manager, owner, handle, &input) == DESKTOP_SURFACE_ECAPACITY);
    while (desktop_surface_input_dequeue(
        &manager, owner, handle, &received_input) == 0) {}
    uint32_t discarded_motion_serial = 0U;
    for (uint32_t event_index = 0U;
         event_index < REIST_GUI_SURFACE_MAX_PENDING_EVENTS; ++event_index) {
        input.type = event_index == 5U
            ? REIST_GUI_SURFACE_INPUT_POINTER_MOTION
            : REIST_GUI_SURFACE_INPUT_KEYBOARD;
        input.serial = 100U + event_index;
        input.x = 12;
        input.y = 8;
        if (event_index == 5U) discarded_motion_serial = input.serial;
        assert(desktop_surface_input_enqueue(
            &manager, owner, handle, &input) == 0);
    }
    input.type = REIST_GUI_SURFACE_INPUT_POINTER_BUTTON;
    input.serial = 200U;
    input.button = 1U;
    input.pressed = 1U;
    assert(desktop_surface_input_enqueue(
        &manager, owner, handle, &input) == 0);
    for (uint32_t event_index = 0U;
         event_index < REIST_GUI_SURFACE_MAX_PENDING_EVENTS; ++event_index) {
        assert(desktop_surface_input_dequeue(
            &manager, owner, handle, &received_input) == 0);
        assert(received_input.serial != discarded_motion_serial);
        if (event_index + 1U == REIST_GUI_SURFACE_MAX_PENDING_EVENTS) {
            assert(received_input.type ==
                REIST_GUI_SURFACE_INPUT_POINTER_BUTTON);
            assert(received_input.serial == 200U);
        }
    }
    reist_gui_surface_buffer_t buffer = {
        REIST_GUI_SURFACE_BUFFER_API_VERSION, sizeof(buffer), 1U, 1U,
        320U, 200U, 320U * 4U,
        REIST_GUI_SURFACE_BUFFER_FORMAT_XRGB8888, 320U * 200U * 4U, 0U};
    assert(desktop_surface_buffer_create(&manager, owner, &buffer) == 0);
    assert(desktop_surface_attach(&manager, owner, handle,
        1U, 1U, 320U, 200U) == 0);
    assert(desktop_surface_buffer_create(&manager, other_owner, &buffer) == 0);
    assert(desktop_surface_buffer_destroy(
        &manager, other_owner, 1U, 1U) == 0);
    assert(desktop_surface_damage(&manager, owner, handle,
        (reist_gui_rect_t){0, 0, 320U, 200U}) == 0);
    desktop_surface_commit_result_t result;
    assert(desktop_surface_commit(&manager, owner, handle, &result) == 0);
    assert(result.committed == 1U && result.damage.count == 1U);
    assert(result.released_buffer_id == 0U);
    assert(desktop_surface_present_damage_take(
        &manager, owner, handle, &present_damage) == 0);
    assert(present_damage.x == 0 && present_damage.y == 0 &&
           present_damage.width == 320U && present_damage.height == 200U);
    assert(desktop_surface_buffer_destroy(&manager, owner, 1U, 1U) < 0);
    buffer.capability_id = 3U;
    assert(desktop_surface_buffer_create(&manager, owner, &buffer) == 0);
    assert(desktop_surface_attach(&manager, owner, handle,
        3U, 1U, 320U, 200U) == 0);
    assert(desktop_surface_damage(&manager, owner, handle,
        (reist_gui_rect_t){10, 20, 30U, 40U}) == 0);
    assert(desktop_surface_commit(&manager, owner, handle, &result) == 0);
    assert(result.released_buffer_id == 1U &&
           result.released_buffer_generation == 1U);
    assert(desktop_surface_present_damage_take(
        &manager, owner, handle, &present_damage) == 0);
    assert(present_damage.x == 10 && present_damage.y == 20 &&
           present_damage.width == 30U && present_damage.height == 40U);
    assert(desktop_surface_buffer_destroy(&manager, owner, 1U, 1U) == 0);
    reist_gui_surface_configure_t resized;
    assert(desktop_surface_reconfigure(
        &manager, owner, handle, 400U, 260U, &resized) == 0);
    assert(resized.width == 400U && resized.height == 260U);
    desktop_surface_slot_t *resizing = &manager.slots[handle.id - 1U];
    assert(resizing->configure_sent == 0U);
    assert(resizing->width == 320U && resizing->height == 200U);
    assert(resizing->pending_width == 400U &&
           resizing->pending_height == 260U);
    assert(desktop_surface_paint_begin(&manager, owner, handle) == 0);
    assert(desktop_surface_paint_fill(&manager, owner, handle,
        (reist_gui_rect_t){0, 0, 320U, 200U}, 0U) == 0);
    assert(desktop_surface_paint_commit(&manager, owner, handle) == 0);
    assert(desktop_surface_ack_configure(
        &manager, owner, handle, resized.serial) == 0);
    assert(resizing->width == 400U && resizing->height == 260U);
    assert(resizing->pending_width == 0U &&
           resizing->pending_height == 0U);
    assert(desktop_surface_present_damage_take(
        &manager, owner, handle, &present_damage) == 0);
    assert(present_damage.x == 0 && present_damage.y == 0 &&
           present_damage.width == 400U && present_damage.height == 260U);
    assert(desktop_surface_ack_configure(&manager, owner, handle,
        resized.serial + 1U) < 0);
    assert(desktop_surface_destroy(&manager, owner, handle) == 0);
    assert(desktop_surface_buffer_destroy(&manager, owner, 3U, 1U) == 0);
    assert(desktop_surface_destroy(&manager, owner, handle) < 0);

    reist_gui_surface_handle_t bounded_handle;
    reist_gui_surface_configure_t bounded_configure;
    assert(desktop_surface_create(&manager, owner,
        REIST_GUI_SURFACE_ROLE_TOPLEVEL, REIST_GUI_SURFACE_MAX_WIDTH,
        REIST_GUI_SURFACE_MAX_BUFFER_BYTES / (4U * REIST_GUI_SURFACE_MAX_WIDTH), &bounded_handle,
        &bounded_configure) == 0);
    assert(desktop_surface_ack_configure(&manager, owner, bounded_handle,
        bounded_configure.serial) == 0);
    buffer = (reist_gui_surface_buffer_t){
        REIST_GUI_SURFACE_BUFFER_API_VERSION, sizeof(buffer), 2U, 1U,
        REIST_GUI_SURFACE_MAX_WIDTH, REIST_GUI_SURFACE_MAX_BUFFER_BYTES / (4U * REIST_GUI_SURFACE_MAX_WIDTH),
        REIST_GUI_SURFACE_MAX_WIDTH * 4U,
        REIST_GUI_SURFACE_BUFFER_FORMAT_XRGB8888,
        REIST_GUI_SURFACE_MAX_BUFFER_BYTES, 0U};
    assert(desktop_surface_buffer_create(&manager, owner, &buffer) == 0);
    assert(desktop_surface_attach(&manager, owner, bounded_handle,
        2U, 1U, REIST_GUI_SURFACE_MAX_WIDTH,
        REIST_GUI_SURFACE_MAX_BUFFER_BYTES / (4U * REIST_GUI_SURFACE_MAX_WIDTH)) == 0);
    assert(desktop_surface_create(&manager, owner,
        REIST_GUI_SURFACE_ROLE_TOPLEVEL, REIST_GUI_SURFACE_MAX_WIDTH + 1U,
        1U, &bounded_handle, &bounded_configure) < 0);
    desktop_surface_revoke_owner(&manager, owner);
    assert(desktop_surface_buffer_destroy(&manager, owner, 2U, 1U) < 0);
    desktop_surface_revoke_owner(&manager, owner);
    return 0;
}
