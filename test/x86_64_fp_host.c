#include <stdio.h>
extern int fp_witness(void);
int main(void) {
    int result = fp_witness();
    if (result) { fprintf(stderr, "FP witness failed: %d\n", result); return result; }
    puts("X86_64_FP_HOST_OK defaults=1 xmm=16 x87=8 switches=64 scrub=1");
    return 0;
}
