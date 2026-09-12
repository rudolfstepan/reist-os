#ifndef REIST_NATIVE_HEAP_H
#define REIST_NATIVE_HEAP_H
#include "include/kernel/critical_object.h"
#define NATIVE_HEAP_BASE UINT64_C(0x100000000)
#define NATIVE_HEAP_LIMIT UINT64_C(0x20000000)
#define NATIVE_HEAP_PENDING INT64_C(-4095)
enum { NATIVE_HEAP_BOOT, NATIVE_HEAP_BIND, NATIVE_HEAP_MALLOC,
       NATIVE_HEAP_FREE, NATIVE_HEAP_REALLOC, NATIVE_HEAP_STEP,
       NATIVE_HEAP_CANCEL, NATIVE_HEAP_ACCESS };
typedef struct {
    uint64_t operation, slot, generation, root, pdpt, first, second, result;
} NativeHeapCall;
typedef struct {
    uint64_t generation, last_generation, root, pdpt, pd, budget, used, result;
    uint64_t size, progress;
    uint32_t operation, phase, region, old_region, scan, flags;
    uint64_t occupied[2], reserved;
} NativeHeapControl;
typedef struct { uint64_t address, requested, mapped, total, state; } NativeHeapRegion;
typedef struct { uint64_t pt, guards[4]; uint32_t used, phase; } NativeHeapTable;
typedef struct {
    NativeHeapControl control;
    critical_object_t control_guards[2];
    NativeHeapRegion regions[128];
    critical_object_t region_guards[128];
    NativeHeapTable tables[256];
    critical_object_t table_guards[256];
} NativeHeapTask;
typedef struct {
    volatile uint32_t initialized, inverse, entered;
    uint32_t reserved;
    critical_object_t guard;
    NativeHeapTask tasks[4];
} NativeHeapState;
_Static_assert(sizeof(NativeHeapCall)==64 && sizeof(NativeHeapControl)==128,
               "private heap request/control binding");
_Static_assert(sizeof(NativeHeapState)<512*1024,"fixed native heap metadata");
_Static_assert(sizeof(NativeHeapState)==397704,"private layout4 state binding");
extern NativeHeapState native_heap_state;
uint64_t reist_native_heap(NativeHeapCall *call);
uint64_t reist_native_heap_frame(bool user);
void *reist_native_heap_pointer(uint64_t frame);
void reist_native_heap_release(uint64_t frame);
_Noreturn void reist_native_heap_fault(void);
#endif
