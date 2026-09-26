#include "text.h"

enum { COLUMNS=80, ROWS=24, CELLS=COLUMNS*ROWS };
static uint16_t blank(const reist_vga_text *t) { return (uint16_t)(t->attribute<<8)|32; }
static void erase(reist_vga_text *t,unsigned first,unsigned end) {
    for(unsigned i=first;i<end;i++) t->cells[i]=blank(t);
    t->dirty=1;
}
static void next_row(reist_vga_text *t) {
    if(t->row<ROWS-1) { t->row++; return; }
    for(unsigned i=0;i<CELLS-COLUMNS;i++) t->cells[i]=t->cells[i+COLUMNS];
    erase(t,CELLS-COLUMNS,CELLS);
}
static void reset_escape(reist_vga_text *t) {
    t->parser=t->argument=t->length=0;
    for(unsigned i=0;i<4;i++) t->arguments[i]=0;
}
void reist_vga_text_init(reist_vga_text *t) {
    if(!t) return;
    t->row=t->column=t->wrap=0; t->attribute=7;
    reset_escape(t);
    for(unsigned i=0;i<2000;i++) t->cells[i]=0x0720;
    t->dirty=1;
}
static unsigned parameter(const reist_vga_text *t,unsigned n) {
    return t->arguments[n] ? t->arguments[n] : 1;
}
static unsigned minimum(unsigned a,unsigned b) { return a<b?a:b; }
static void csi(reist_vga_text *t,uint8_t c) {
    unsigned a=t->arguments[0], n=parameter(t,0), pos=t->row*COLUMNS+t->column;
    if(c=='m') {
        static const uint8_t vga[8]={0,4,2,6,1,5,3,7};
        for(unsigned i=0;i<=t->argument;i++) {
            unsigned value=t->arguments[i];
            if(value==0) t->attribute=7;
            else if(value==1) t->attribute|=8;
            else if(value==22) t->attribute&=0xf7;
            else if(value>=30&&value<=37) t->attribute=(t->attribute&0xf8)|vga[value-30];
            else if(value==39) t->attribute=(t->attribute&0xf8)|7;
            else if(value>=40&&value<=47) t->attribute=(t->attribute&15)|(vga[value-40]<<4);
            else if(value==49) t->attribute&=15;
        }
        return;
    }
    if((c=='H'||c=='f') && t->argument<=1) {
        t->row=(uint8_t)minimum(n-1,ROWS-1);
        t->column=(uint8_t)minimum(parameter(t,1)-1,COLUMNS-1);
    } else if(!t->argument) {
        switch(c) {
        case 'A': t->row=(uint8_t)(t->row-minimum(t->row,n)); break;
        case 'B': t->row=(uint8_t)minimum(t->row+n,ROWS-1); break;
        case 'C': t->column=(uint8_t)minimum(t->column+n,COLUMNS-1); break;
        case 'D': t->column=(uint8_t)(t->column-minimum(t->column,n)); break;
        case 'J':
            if(a==0) erase(t,pos,CELLS);
            else if(a==1) erase(t,0,pos+1);
            else if(a==2) erase(t,0,CELLS);
            break;
        case 'K':
            if(a==0) erase(t,pos,(t->row+1)*COLUMNS);
            else if(a==1) erase(t,t->row*COLUMNS,pos+1);
            else if(a==2) erase(t,t->row*COLUMNS,(t->row+1)*COLUMNS);
            break;
        default: return;
        }
    } else return;
    t->wrap=0;
}
int reist_vga_text_byte(reist_vga_text *t,uint8_t c) {
    if(!t) return -22;
    if(t->row>=ROWS||t->column>=COLUMNS||t->wrap>1||t->parser>3||
       t->argument>3||t->length>32||t->dirty>1||t->attribute>127) return -84;
    for(unsigned i=0;i<4;i++) if(t->arguments[i]>999) return -84;
    if(c==27) { reset_escape(t); t->parser=1; return 0; }
    if(c==24||c==26) { reset_escape(t); return 0; }
    if(t->parser) {
        if(t->parser==1) {
            if(c=='[') t->parser=2;
            else reset_escape(t);
            return 0;
        }
        if(c>=0x40&&c<=0x7e) {
            if(t->parser==2) csi(t,c);
            reset_escape(t); return 0;
        }
        if(t->parser==3) return 0;
        if(t->length==32) { t->parser=3; return 0; }
        t->length++;
        if(c>='0'&&c<='9') {
            unsigned a=t->arguments[t->argument]*10+c-'0';
            if(a>999) t->parser=3;
            else t->arguments[t->argument]=(uint16_t)a;
        } else if(c==';'&&t->argument<3) t->argument++;
        else t->parser=3;
        return 0;
    }
    if(c=='\r') { t->column=t->wrap=0; return 0; }
    if(c=='\n') { t->wrap=0; next_row(t); return 0; }
    if(c=='\b') { if(t->column) t->column--; t->wrap=0; return 0; }
    if(c=='\t') { t->column=(uint8_t)minimum((t->column+8)&~7u,COLUMNS-1); t->wrap=0; return 0; }
    if(c<32||c==127) return 0;
    if(t->wrap) { t->column=t->wrap=0; next_row(t); }
    t->cells[t->row*COLUMNS+t->column]=(uint16_t)(t->attribute<<8)|c;
    t->dirty=1;
    if(t->column==COLUMNS-1) t->wrap=1;
    else t->column++;
    return 0;
}
