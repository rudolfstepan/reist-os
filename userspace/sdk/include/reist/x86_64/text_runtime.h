#ifndef REIST_X86_64_TEXT_RUNTIME_H
#define REIST_X86_64_TEXT_RUNTIME_H
#include <stdint.h>
/* Private zero-default qualification data, no command-line authority. */
extern volatile uint64_t reist_text_runtime_selection[2];
extern volatile uint64_t reist_text_runtime_witness[16];
extern char reist_text_runtime_output[256];
void reist_text_runtime_checkpoint(void);
#endif
