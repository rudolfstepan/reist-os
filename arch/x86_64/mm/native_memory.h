#ifndef REIST_NATIVE_MEMORY_H
#define REIST_NATIVE_MEMORY_H
#include "include/kernel/critical_object.h"
#define NATIVE_MEMORY_LIMIT UINT64_C(0x400000000)
#define NATIVE_MEMORY_FRAMES (NATIVE_MEMORY_LIMIT/4096)
#define NATIVE_MEMORY_WORDS (NATIVE_MEMORY_FRAMES/64)
#define NATIVE_MEMORY_REGIONS (NATIVE_MEMORY_FRAMES/256)
enum { NATIVE_MEMORY_INIT, NATIVE_MEMORY_ALLOC, NATIVE_MEMORY_FREE,
       NATIVE_MEMORY_COUNT, NATIVE_MEMORY_HIGH_FLOOR };
typedef struct {
    uint32_t managed, free;
    volatile uint32_t initialized, inverse;
    uint64_t roots[4];
} NativeMemoryControl;
/* Private layout3, single object at HIGH+2MiB. The32-bit capture owns only
 * managed/free and usable before INIT. All state is zeroed before capture.
 * One region guard covers256 frames (32 usable +32 allocated bytes).
 * One availability bit names a non-full region; roots name nonzero words.
 * No heap, caller roles, virtual mapping policy or implicit authority. */
typedef struct {
    NativeMemoryControl control;
    volatile uint32_t entered;
    uint32_t reserved[3];
    uint64_t usable[NATIVE_MEMORY_WORDS], allocated[NATIVE_MEMORY_WORDS];
    uint64_t available[NATIVE_MEMORY_REGIONS/64];
    critical_object_t region_guards[NATIVE_MEMORY_REGIONS];
    critical_object_t summary_guards[NATIVE_MEMORY_REGIONS/512];
    critical_object_t control_guard;
} NativeMemoryState;
_Static_assert(sizeof(NativeMemoryControl)==48 && offsetof(NativeMemoryState,usable)==64,
               "native memory capture prefix");
_Static_assert(sizeof(NativeMemoryState)<5*1024*1024,"native metadata arena");
_Static_assert(sizeof(NativeMemoryState)==4531096 &&
               offsetof(NativeMemoryState,allocated)==64+524288,
               "private layout3 state binding");
extern NativeMemoryState native_memory_state;
uint64_t reist_native_memory(uint64_t operation,uint64_t argument);
void reist_native_memory_zero(uint64_t frame);
_Noreturn void reist_native_memory_fault(void);
#endif
