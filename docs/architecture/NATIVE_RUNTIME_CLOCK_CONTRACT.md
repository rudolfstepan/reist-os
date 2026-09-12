# Native Laufzeituhr und Fristen

Stand: 12. September 2026. R8.3ac, Basis `f88a439d`.

## Umfang und Grenze

`NativeRuntime` bündelt Uhr, Schedulerfristen, IPC-Fristen, CPU-Abrechnung und
Retirement als gemeinsamen Zeitvertrag. Es aktiviert NativeProcesses, NativeIPC,
NativeRAM und NativeHeap; NativeImages und NativeBulkIPC sind ausgeschlossen.
Das bisherige signierte Medienprofil und sämtliche Bootstrapprofile bleiben
unverändert. Allgemeiner Programmstart, Ring3-Supervisor und Budgeterneuerung
sind eigene Rechte-/Policygrenzen und werden hier nicht behauptet.

Referenzbegriffe: POSIX monotonic clock, SysV AMD64 und bestehende REIST-
Syscalls40/41/42 sowie IPC49..55/58. Keine POSIX-Binärkompatibilität: weiterhin
REIST-Millisekunden, kein Zeitstellen, keine Uhrzeit und keine behauptete
Wandzeitgenauigkeit.100Hz-PIT-Ereignisse entsprechen nominell je10ms.

## Verbindliche Invarianten

Ein eigener opt-in Timermodus zählt Tick und EOI mit64Bit, behält den Zähler
zwischen unabhängigen Prozessläufen und übergibt volle64Bit bis Scheduler,
IPC und CPU-Kern. Zulässiger Tickbereich ist `[0, 2^60)`; Deadlineaddition und
Millisekundenumrechnung dürfen nie umbrechen. Alte Profile behalten256Ticks.
Die IRQ-Fortschrittslease von3e9 TSC-Zyklen bleibt endlich; dies sind nicht
drei Sekunden. Kontext-, TSC-, Zähler- und EOI-Prüfung gehen Publikation und
Scheduler-Tail voraus. Fehlender IRQ wird nicht als zeitlich unbeschränkt
überwachbar behauptet. Unkorrigierbare Kernfehler führen zum Fatalpfad.

Sleep bleibt1..100ms, IPC übernimmt die bestehenden uint32-Millisekundenfristen.
Ungültige Fristen scheitern vor Queueeffekten. CPU-Budget bleibt insgesamt
höchstens32 Samples pro Generation: kein Reset durch Yield, Schlafen oder IPC,
keine automatische Erneuerung und kein unendlicher CPU-Dienstbetrieb.
Vier Slots, ein Waitnode je Task, private Heapgrenzen und Fencing vor Reap
bleiben erhalten. Ein lokaler CPU-/Prozessfehler muss unabhängige Peers laufen
lassen. Kein neuer öffentlicher ABI- oder persistenter Medienaufbau.

## Eingefrorene Abnahme

Zwölf Gategruppen in `automation/reist-s03b.toml`: tatsächliche Hostarithmetik
und IPC O0/O2, bisherige Prozess-/IPC-/Heap-/Boot-/Dokumentationstests, drei
Buildprofile, neuer Langzeitgast, unveränderter Heapgast und i386-Referenz.
Der neue Gast schläft mindestens300Ticks je Run, führt zwei Runs aus und prüft
Fortsetzung, IPC, Heap, CPU-Ende, Peerfortschritt und vollständiges Retirement.
Ein weiterer Lauf setzt ausschließlich im Debugger den Clockstart vor2^32
und überschreitet die Grenze durch echte IRQs. Keine Produktions-Testsyscalls.
Je neuer Gast maximal20s; alte Gastprüfungen bleiben bei10s. Grenzfälle für
2^60, rückläufige Zeit, doppelte/fehlende EOIs und TSC-Überlauf laufen auf Host.
Der alte Heapkernel muss bytegleich zu SHA256
`b135c6456d48b7eb0468cf220543135588a8d7bb9dbc976fcffce7d88231d5e8` bleiben.
Logs und auch fehlgeschlagene Versuche bleiben unter `build/codex-agent/`.
