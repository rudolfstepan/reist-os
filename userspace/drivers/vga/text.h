#ifndef REIST_VGA_TEXT_H
#define REIST_VGA_TEXT_H
#include <stdint.h>

/* IBM VGA cells; row 24 is reserved for kernel early/fatal status.
 * ECMA-48 subset: CUU/CUD/CUF/CUB/CUP/HVP, ED/EL and SGR.
 * Each input byte performs at most 1920 cell writes, with no allocation or IO.
 */
typedef struct {
    uint16_t cells[2000];
    uint16_t arguments[4];
    uint8_t row,column,attribute,wrap,parser,argument,length,dirty;
} reist_vga_text;
void reist_vga_text_init(reist_vga_text *);
int reist_vga_text_byte(reist_vga_text *,uint8_t);
#endif
