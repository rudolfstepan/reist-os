#ifndef REIST_X64_VGA_CONSOLE_H
#define REIST_X64_VGA_CONSOLE_H
#include <stdint.h>
enum { REIST_VGA_RESOURCE=33, REIST_VGA_BIND=1, REIST_VGA_REVOKE,
       REIST_VGA_QUERY, REIST_VGA_READ_OUTPUT, REIST_VGA_WRITE_INPUT,
       REIST_VGA_WRITE_CELLS, REIST_VGA_HEARTBEAT, REIST_VGA_STATUS,
       REIST_VGA_SET_CURSOR };
typedef struct {
    uint32_t version,size,operation,flags;
    uint64_t owner,epoch,buffer;
    uint32_t count,offset;
    uint64_t reserved[2];
} reist_vga_request_v1;
_Static_assert(sizeof(reist_vga_request_v1)==64,"VGA request v1");
#endif
