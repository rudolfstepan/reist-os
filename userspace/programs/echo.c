/**
 * @file userspace/programs/echo.c
 * @brief Gibt Argumente auf der Konsole aus.
 *
 * Layer: Ring-3 system program or command.
 * Contract: Argumente und SDK-Rückgaben werden vor weiteren Operationen validiert.
 * Safety: Ressourcenarbeit ist begrenzt; Fehler werden an die Shell gemeldet und nicht verschleiert.
 */
#include "x86os.h"

static int equal(const char *a, const char *b) {
    if (!a || !b) return 0;
    for (unsigned int i = 0; i < 32U; ++i) {
        if (a[i] != b[i]) return 0;
        if (!a[i]) return 1;
    }
    return 0;
}

static int color_echo(int argc, char **argv) {
    static const char *names[16] = {
        "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
        "bright-black", "bright-red", "bright-green", "bright-yellow",
        "bright-blue", "bright-magenta", "bright-cyan", "bright-white"
    };
    int color = -1;
    if (argc >= 3) for (int i = 0; i < 16; ++i) if (equal(argv[2], names[i])) color = i;
    /* Validate the entire command before publishing even a prefix. */
    char output[4096];
    unsigned int used = 0;
    if (color < 0) goto invalid;
    for (int arg = 3; arg < argc; ++arg) {
        if (!argv[arg]) goto invalid;
        if (arg != 3) { if (used >= sizeof(output) - 1U) goto invalid; output[used++] = ' '; }
        for (unsigned int i = 0; argv[arg][i]; ++i) {
            unsigned char c = (unsigned char)argv[arg][i];
            if (used >= sizeof(output) - 1U ||
                (c != '\t' && c != '\n' && (c < 32U || c > 126U))) goto invalid;
            output[used++] = (char)c;
        }
    }
    output[used++] = '\n';
    uint64_t start, now;
    if (x86os_monotonic_ms(&start) != 0) return 1;
    for (unsigned int offset = 0; offset < used;) {
        unsigned int length = 0;
        do { ++length; }
        while (length < 64U && offset + length < used && output[offset + length - 1U] != '\n');
        if (x86os_monotonic_ms(&now) != 0 || now - start >= 5000U ||
            x86os_terminal_write_color(1U, output + offset, length, (uint32_t)color, 0U) != (int)length) {
            x86os_puts("echo: color output denied or timed out\n");
            return 1;
        }
        offset += length;
    }
    return 0;
invalid:
    x86os_puts("echo: invalid color or text (ASCII, maximum 4096 bytes)\n");
    return 1;
}

int main(int argc, char** argv) {
    if (argc > 1 && equal(argv[1], "--color")) return color_echo(argc, argv);
    for (int index = 1; index < argc; ++index) {
        if (index != 1) x86os_putchar(' ');
        x86os_puts(argv[index]);
    }
    x86os_putchar('\n');
    return 0;
}
