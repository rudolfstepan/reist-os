/* Private layout selection, not an application ABI. See native_layout.inc. */
#ifndef REIST_NATIVE_LAYOUT_H
#define REIST_NATIVE_LAYOUT_H
#ifdef REIST_NATIVE_LARGE_IMAGE
#ifndef REIST_NATIVE_WIDE
#error NativeLargeImage requires NativeWide
#endif
#define NATIVE_IMAGE_PAGES 256U
#define NATIVE_TASK_WORDS 512U
#elif defined(REIST_NATIVE_WIDE)
#define NATIVE_IMAGE_PAGES 64U
#define NATIVE_TASK_WORDS 128U
#else
#define NATIVE_IMAGE_PAGES 8U
#define NATIVE_TASK_WORDS 32U
#endif
#define NATIVE_REG_DELTA ((NATIVE_IMAGE_PAGES-8U)*8U)
#define NATIVE_CLAIM_FRAMES (NATIVE_IMAGE_PAGES+5U)
#endif
