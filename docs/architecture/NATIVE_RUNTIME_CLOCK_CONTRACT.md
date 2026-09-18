# Native Laufzeituhr und Fristen

Explizite, mit24 Verpflichtungen und14 Gastfaellen qualifizierte Erweiterung:
[periodische Dienst-CPU-Zulassung](NATIVE_SERVICE_CPU_CONTRACT.md).
Das Zeitfenster wird aus der unveränderten monotonen100Hz-Uhr berechnet;
Sleep/IPC/WAIT/Yield setzen keine Zähler zurück. Bestehende Tick-/IRQ-/TSC-
Grenzen und endliche CPU-Budgets aller bisherigen Profile bleiben erhalten.

Stand: 14. September 2026. R8.3ac, Basis `f88a439d`; R8.3am mit `0f4efd17`
abgenommen. Die Idle-Reparaturgeschichte unten bleibt als Nachweis erhalten.

Das zusätzliche [Acht-Task-Profil](NATIVE_TASK_POOL_CONTRACT.md) verändert keine
CPU-, Tick-, IRQ-, WAIT- oder Sleep-Grenze. Acht aktive Task-/Deadlineeinträge
werden nur durch private run-v4 zugelassen; alte Bootstrapproben bleiben bei
vier. Schlafen, IPC, WAIT und Ersatzstarts setzen keine CPU-Quote zurück.

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

### Freigegebene Zusammenführung am12. September

Nach dem expliziten Erweiterungswunsch und der erneuten Nutzeranweisung zur
Bündelung wird die vorhandene Umsetzung mit ELF-Seitenbelegung fortgesetzt.
Die Quellenänderungen bleiben der zugeordnete, noch nicht abgenommene Kandidat
dieser Transaktion; nur die Vertragsergänzung wird vorher lokal committed.
Alle zwölf Gatebefehle und Zeit-/Ressourcenlimits bleiben bestehen.

Der bestehende Loader hat bereits acht geprüfte ELF-Seiten. NativeRuntime
ermittelt die erste RW-Seite aus diesen vorhandenen PF-Rechten in höchstens
acht Schritten; keine neue ELF-Analyse in Ring0. Fehlende RW-/RX-Seiten,
unbekannte oder W+X-Rechte sowie getrennte RW-Bereiche werden verworfen.
Alle bisherigen Fixture-Magic-, Faultpointer- und Isolationsverbraucher lesen
diese abgeleitete Datenseite. Der Fixturevertrag behält seine Feldoffsets ab
Beginn des RW-Bereichs, aber nicht die feste VA0x401000. Tatsächliche O0/O2-
Tests prüfen sämtliche zulässigen Seitenpositionen und ungültige Layouts.
Der echte Gast muss mit Datenseite0x402000 sämtliche alten Isolationsbelege
und anschließend den Laufzeit-/IPC-/Heap-/CPU-Ende-Pfad bestehen.
Defaultprofile, achtseitige Userkapazität, private C-Struktur und persistente
Medienformate bleiben unverändert. Das ist weiterhin kein allgemeiner
Ring3-Dateiloader; dessen andere Autoritätsgrenze wird nicht vorweggenommen.

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

## R8.3am: geprüfter CPL0-IRQ-Rückweg nach Idle-Wake

Freigegebener Kandidat, Verträge `300cfbc2` und `eab12d16`, noch nicht
abgenommen. Referenz ist der Intel64/IA-32-Interrupt-/IRETQ-/STI-Vertrag
([Intel SDM](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html)),
nicht eine neue REIST-Interruptsemantik oder öffentliche ABI.

Native IRQ-Zulassung prüft den gespeicherten Kernel-Idle-Kontext einschließlich
IF, CR3, Stackgrenzen und leerer Readyqueue vor der Tick-/EOI-Publikation.
Der anschließende Wake darf die Readyqueue verändern. Deshalb darf IRETQ
zu derselben Idle-Instruktionsfolge IF nicht wieder setzen, bevor der
Dispatcher seine Voraussetzung erneut geprüft hat. Der CPL0-Arm von
`process_run_irq_tail64` löscht allein Bit9 im zugelassenen gespeicherten
RFLAGS. Alle übrigen Framewerte und CPL3-Rückwege bleiben unverändert.
Interrupts werden erst durch Dispatcher-STI oder den separat zugelassenen
Nutzerkontext wieder erlaubt. Kontext-/Frist-/EOI-Fehler bleiben fail-closed.

Konkreter Vorherbeleg `a0d4be69`: normalisierter IRQ0x20-Frame an
`process_run_dispatch64.idle_wait+2`, CS8/SS0x10/RFLAGS0x10202,
Tick=EOI=last_tick61, Ready1/Deadline3/Live4. Peer2 war bereits READY;
R9=0 schließt einen gemeldeten Clockarithmetikfehler dieses Eintritts aus.
Der alte Rückweg öffnet damit das vor CLI liegende Wiedereintrittsfenster.
Frühere Fatalversuche ohne diesen Snapshot erhalten keine nachträgliche
Ursachenzuordnung.

Deterministischer Host führt echte native IRQ-/Idle-/Tick-/Rückweg-
Assemblerausschnitte aus: Wiedereintrittstest vor Korrektur rot, danach
117 Matrixfälle plus Rückwegtest bei O0/O2 grün. CR3/RDTSC/OUT werden auf
feste Hostadapter abgebildet; vollständige Run-Ownership ist eine explizite
Fixturevoraussetzung mit separaten bestehenden Tests. Keine Aussage, dass
ein Hosttest privilegierten Gastbetrieb ersetzt.

Zwei korrigierte Gäste beobachten Ready1/Deadline0/IF0 am tatsächlichen
Rückweg, erreichen aber vor dem letzten Peer die unveränderte20s-Capturefrist.
Eine Logziel-Bündelung und anschließend vollständig validierte begrenzte
Seitentabellen-Snapshots sind die zwei gezielten Zeitkorrekturen; keine
Frist-/Quotenerhöhung. Die zweite ist nur hostqualifiziert: der letzte Gast
stoppt vorher im älteren Sleep-Schlussprüfpfad (Modus5/Stufe0x9F), dessen
genaues fehlgeschlagenes Prädikat nicht erfasst wurde. Dieser Befund ist
nicht als gleicher Wiedereintrittsfehler oder Wirkung des neuen Lesers belegt.

Vier Matrixversuche verbraucht, kein fünfter. Die drei vorgesehenen echten
Lease-/SS-/EOI-Ablehnungsgäste wurden nicht erreicht. Die20 ursprünglichen
Paketgatebefehle bleiben bestehen; durch die Kernelkorrektur betroffene
Build-/Gastbelege sind erneut erforderlich. Weitergehende Legacy-Sleep-
Diagnose in `cooperative_scheduler.asm` liegt außerhalb dieses Supplements
und braucht einen ausdrücklich erweiterten begrenzten Umfang mit Tests.
Manifest: `build/codex-agent/r83am-file-launch/verification-status-timer-idle.json`.

### Ergebnis der freigegebenen Legacy-Schlussdiagnose

Vertrag `9ebaf6a5` ergänzt ausdrücklich `cooperative_scheduler.asm` und zwei
vorgesehene tatsächliche Assemblerhostdateien, ohne eine unbelegte Änderung
zu verlangen. Der reine Diagnosehost besteht9/.021s. Beide erlaubten
unveränderten FAT12-Gäste erfassen korrekte Schlusszustände: Tick/EOI/
last_tick/final_tick4, Handoffs3, Fehler0, Reaps4 und alle27 festen Ereignisse.
Die zweite Aufzeichnung bindet zusätzlich jeden Event an den realen Tick;
Wake1/2/0 erfolgt bei2/3/4. Beide erreichen `DEADLINE_SLEEP_OK`.

Der historische Abbruch Modus5/0x9F bleibt damit ursächlich ungeklärt, nicht
widerlegt. Keine neue Kerneländerung, kein Ersatz der Ereignisfolge und keine
Behauptung eines belegten erlaubten Interleavings als Fehlerursache. Die neuen
Assemblerhosts bleiben unimplementiert; ohne belegten Defekt kein red/green-
Reparaturnachweis. Beide Gäste scheitern später an der unveränderten20s-
Dateistart-Capturefrist, nicht am Sleep-Schluss. Alle bisherigen Records und
Medien-/COW-Nachweise sind erhalten. Paarbudget ausgeschöpft; kein dritter
Gast oder an eine Legacy-Korrektur gebundener neuer IRQ-Matrixlauf.
Weitere begrenzte Laufzeit-/Beobachterdiagnose benötigt einen ausdrücklich
neuen Umfang. Keine Paketabnahme; ursprüngliche20 Gates und veralteter
NativeFileLaunch-Build bleiben als solche gekennzeichnet.
Manifest: `build/codex-agent/r83am-file-launch/verification-status-legacy-sleep.json`.
