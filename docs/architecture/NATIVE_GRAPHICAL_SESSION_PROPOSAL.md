# Native64: grafische Sitzung und exklusive Eingabeverteilung

## Umsetzung abgeschlossen

R8.3bh und R8.3bi sind abgenommen. BI Candidate07 besteht acht Gates und28
frische Gaeste (18 GUI/10 CLI), einschliesslich aktivem Elternausfall und
GUI-Budgeterschoepfung mit weiter nutzbarer serieller Dateidiagnose.
[Vertrag](NATIVE_GRAPHICAL_SESSION_CONTRACT.md) und
[Startanleitung](../development/NATIVE_GRAPHICAL_SESSION_QUICKSTART.md).
Der folgende Vorschlag dokumentiert die historische Freigabe; seine damaligen
offenen Voraussetzungen sind durch BH/BI innerhalb ihres Vertrags geschlossen.
Netzwerk, DMA, persistierende Schreibrechte, SMP und physische Plattformen
waren nicht Teil dieser Freigabe. Die gesamte native64-Abnahme bleibt offen.

## Historischer Vorschlag und Freigabe

Freigegeben durch den erneuten Fortsetzungsauftrag nach der konkreten Frage.
R8.3bh prueft zuerst die geschuetzte Terminal-Dienstberechtigung einschliesslich
echtem Ring3-Verbraucher und Fehlerlebensdauer. Danach folgt ohne Routinefrage
die separate Ring3-Fokus-/Sitzungsintegration. Der folgende Vorschlag bleibt
als Freigabehistorie erhalten, nicht als erneute Freigabeanforderung.

## Abgenommene Grundlage

Stand21. September2026, sauberer Implementierungscommit
`fd7a2f7786f6905b928bbe9912590e0f950664fa`.
R8.3bg besteht zehn Gates, zwoelf Eingabe- und zehn bestehende CLI-Gaeste,
jeweils frisch. Finaler Beleg:
`build/codex-agent/r83bg-input/candidate04/final.json`, SHA256
`5e26802cdeface9717909f60dd8d5bd45c37d05eb643ec51b1be085ed09f3453`.
Build06/media05 bleiben das nutzbare, begrenzte Eingabeprofil.

Dieses Dokument beschreibt die naechste notwendige Freigabe. Es aktiviert
kein Implementierungspaket und reserviert keine Builds oder Gastlaeufe.

## Konkrete noch fehlende Autoritaet

- `userspace/gui/compositor/desktop.c`, `desktop_terminal_acquire`, verwendet
  `REIST_TERMINAL_ACQUIRE_SERVICE` fuer exklusiven Eingabebesitz. Der native
  Mechanismus `arch/x86_64/proc/native_terminal.inc` weist Operation4 explizit
  mit `-95` ab. Der vorhandene Vordergrundvertrag delegiert nur zwischen Root
  und zugelassenem Kind; eine Dienstuebernahme ist nicht freigegeben.
- `userspace/sdk/lib/x86_64/shell_input.inc` besitzt genau eine5000ms-Sitzung
  mit32 Ereignissen. Der getrennte Treiber und der Verbraucher werden danach
  gesperrt und aufgeraeumt. Das ist kein dauerhafter Eingabebroker.
- Der derzeitige Shellpfad erwartet Vordergrundslot4; Eingabetreiber und
  Ereignisvalidator sind an Slot5 beziehungsweise Zielslot4 gebunden.
  Ein gleichzeitig laufender Compositor, eine Shell und deren Anwendungen
  brauchen eine explizite generationsgebundene Rollen- und Rechtezuordnung.
- Der bestehende GUI-Vertrag verlangt exklusiven Zeichenlesebesitz und
  Compositor-vermittelten Fokus/Capture. Eine Recovery-Shell darf Tasten des
  aktiven Compositors nicht mitlesen. Der jetzige Eingabetest verteilt nur an
  einen fest bestimmten Verbraucher und bietet keine solche Autoritaet.

Quellen: `NATIVE_TERMINAL_LEASE_CONTRACT.md`, `NATIVE_INPUT_CONTRACT.md`,
`GUI_RENDERING_INPUT_AND_LATENCY_CONTRACT.md` sowie die genannten Quellen.
Die alten i386-Dienste sind Portierungsreferenzen; ihre Existenz erteilt keine
native Dienstberechtigung.

## Vorgeschlagene Freigabe

Eine explizite native grafische Sitzungsdomaene im bisherigen QEMU-PC/TCG-
Profil mit einer CPU,4/8GiB und den bestehenden signierten BIOS-Medien:

1. Ein separater Ring3-Sitzungscompositor darf exklusiven Terminal-Dienstbesitz
   erhalten und Eingabe ausschliesslich an den aktuellen, generationsgenau
   zugelassenen Fokusinhaber verteilen. Anwendungen bekommen nur ihre lokalen
   Surface-/Eingaberechte; keine globale Eingabe- oder Geraeteberechtigung.
2. Ein eigener Ring3-Eingabedienst und der Compositor duerfen ueber mehrere
   Vordergrundprogramme hinweg leben. Hierfuer werden explizite periodische
   CPU-, Speicher-, Ereignis-, Health- und Restartbudgets vor Umsetzung
   eingefroren. Die abgenommenen5000ms/32-Ereignis-Grenzen des alten Profils
   werden nicht still veraendert oder durch endlose Neustarts umgangen.
3. Der Root-Supervisor ordnet Rollen, gerichtete Endpunkte und schwaechere
   Anwendungsprofile explizit zu. Terminaluebernahme, Fokuswechsel, Capture,
   Dienstfehler und manuelle Wiederherstellung verwenden dieselben
   `detect -> isolate -> fence/revoke -> reap -> recreate -> self-test ->
   reintegrate`-Uebergaenge. Erschoepfung laesst die grafische Eingabe gesperrt;
   die serielle Diagnose darf erst nach nachgewiesenem Widerruf uebernehmen.
4. Normale Shell-/Programmstarts, Tastatureingabe, lokale Pointerzustellung und
   begrenzte Surface-Ausgabe werden als gemeinsamer nutzbarer Pfad integriert.
   Bestehende REIST-Terminal-/Surface-Begriffe und versionierte ABI werden
   ueber dokumentierte native Adapter bewahrt. Keine Wayland-/POSIX-
   Kompatibilitaetsbehauptung ohne eigene Nachweise.

Der Kernel enthaelt weiterhin nur die begrenzten Schutz-, Mediation-,
Scheduling-, Capability- und Fencingmechanismen. Fokus, Layout, Scancode-
Interpretation, Rendering und Anwendungsprotokolle bleiben in Ring3.
Keine neuen Rohports, DMA-, USB-, Netzwerk-, persistierenden Schreibrechte,
SMP- oder physischen Plattformrechte sind Teil dieser Freigabe. R3.6b bleibt
vertagt. Die bisherigen nativen CLI-/Grafik-/Eingabeprofile bleiben Referenzen.

## Abnahme vor Fertigmeldung

Vor Implementierung: vollstaendige betroffene Verbraucher inventarisieren,
genau ein zusammenhaengendes Paket mit expliziten Dateien, unveraenderlichen
Grenzen und endlicher Build-/Gastreservation einfrieren. Kein pauschales
Hochsetzen aller Syscallprofile und kein direktes Linken alter Kerneltreiber.

Tatsaechliche Hosttests und QEMU-Nachweise muessen normalen Shell-/Appwechsel,
exklusiven Fokus, Capture/Release, unberechtigte Beobachter, stale Handles,
Compositor-/Treiber-/Client-Crash und Hang, Quoten, verlorene Antworten,
Elternausfall und Budgeterschoepfung einschliesslich nachfolgender Recovery
belegen. Unabhaengige serielle Dateidiagnose und alte Mediennachweise bleiben
Pflicht. Erst danach folgen die getrennten noch offenen Netzwerk-, Browser-,
JS-, VMware-/SMP- und Systemabnahmen.

## Warum hier eine Freigabe erforderlich ist

`AGENTS.md`, Interactive execution directive, verlangt trotz des fortlaufenden
Fertigstellungsauftrags einen Stopp bei neuen Autoritaetsdomaenen. Hier geht es
um bislang verweigerte exklusive Dienstuebernahme und globale Fokusverteilung,
nicht um eine weitere Diagnose oder die Reservierung eines Prueffensters.
Nach Freigabe kann die interaktive Umsetzung ohne Paket-fuer-Paket-Rueckfrage
fortgesetzt werden. Bis dahin bleibt `active_id` leer und der abgenommene
Stand vollstaendig erhalten.
