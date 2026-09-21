#ifndef REIST_NATIVE_PS2_H
#define REIST_NATIVE_PS2_H
#include <reist/x86_64/input.h>
typedef struct {
    unsigned char down[32],packet[3],mouse_count,extended,pause;
    uint32_t modifiers;
    uint64_t last,keyboard_end,mouse_end;
} reist_ps2_decoder;
void reist_ps2_clear(reist_ps2_decoder *);
/* status/data are the actual i8042 pair. No transport or authority here. */
int reist_ps2_decode(reist_ps2_decoder *,uint8_t status,uint8_t data,uint64_t now,reist_input_event_v1 *);
typedef struct {
    void *context;
    uint64_t (*clock)(void *);
    int64_t (*transfer)(void *,unsigned operation,unsigned value,uint64_t end);
    int (*sleep)(void *,unsigned ms);
} reist_ps2_transport;
int reist_ps2_initialize(const reist_ps2_transport *,uint64_t end);
#endif
