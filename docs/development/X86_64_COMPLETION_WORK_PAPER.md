# Native x86_64-Version: Umsetzung bis zur Systemabnahme

## Stand26.09.: VGA-Textshell samt Hardwarecursor abgenommen

CJ qualification05 besteht alle fuenf eingefrorenen Gates:7 Hosttests,
unveraenderte Standardartefakte, signiertes Textabbild, frische QEMU-Nachweise
fuer Normalbetrieb/Bootfehler/Crash/Hang und echte VMware-Anzeige. Cursor
folgt dem Prompt; VMware-Bild direkt geprueft. Gast-/Host-Grenzen unveraendert.
Belege: build/codex-agent/r83cj-vga/qualification05. Naechster offener Schritt
ist der native64-Text-/Grafik-Uebergang; CB bleibt bis dahin archiviert/queued.
Die alte32-Bit-BIOS-Umschaltung und der nur beim Booten gebundene native
Framebuffer erfuellen diesen Schritt nicht. Gesamt-OS-Abnahme bleibt offen.

## Prioritaet26.09.: sichtbare VGA-Textshell beim Booten

Der Nutzer fordert die echte VGA-Textshell, damit Boot- und Startfehler auf dem
Bildschirm lesbar bleiben. Aktuell schaltet das Desktop-Abbild vor dem Kernel
auf VBE; die native Shell schreibt nur COM1. Ein Entfernen des VBE-Schalters
allein behebt die fehlende Konsolenausgabe nicht. Der vorhandene Runtime-VBE-
Thunk gehoert zur32-Bit-Architektur. Separates begrenztes VGA-Konsolen-Paket
vom Nutzer mit mach weiter freigegeben; CJ ist aktiv. VGA-Textshell und
Konsolenwiederherstellung zuerst, gepruefter nativer Text-/Grafik-Uebergang
anschliessend erforderlich. CB-Kandidat vollstaendig in Archiv02 gesichert.

CB-Fortschritt: Text/Paint-Schliessen und Neuoeffnen in beiden Reihenfolgen
in QEMU nachgewiesen, neue Texteingabe abc binnen300ms,10s stabile neue Apps.
VMware07 scheitert mit-122 nach READY;08 beobachtet einen READY ohne Fehler,
aber keine vollstaendige Wiederherstellung;09 scheitert vor READY am
Eingabedienst/Kanal. Keine VMware-/CB-/Gesamt-OS-Abnahme. Details CURRENT_WORK.


## Desktop-Korrektur25.09.: Fensterziehen geprueft, Abnahme offen

CB-Build51/Medium29:12 Hosttests bestanden. QEMU reproduziert den
Compositor-CPU-Abbruch nach233 Ziehbewegungen; mit begrenzter Zeichenpause
bestehen801 Bewegungen plus10s Stabilitaet sowie die urspruengliche300ms
Zeiger-/Texteingabe. CPU64 bleibt unveraendert.

VMware05 lief170.494s ohne serielle Shell-Rueckkehr. Die nach120s faellige
Speicherdienst-Wiederherstellung war am Testende noch nicht vollstaendig
beobachtet: unabhaengige Pruefung lehnt eine Stabilitaetsabnahme ab.
Die Shell schreibt derzeit nur COM1; sie ist im Framebuffer nicht sichtbar.
CB und die vollstaendige native64-Systemabnahme bleiben offen.

## Aktueller Stand25.09.2026: CI abgenommen, Desktop CB offen

Kernel-Paket898f30d5: vier eingefrorene Abnahmen bestanden. Drei frische
QEMU-Laeufe belegen801 Mausbewegungen, urspruengliche300ms Zeiger-/Texteingabe
und begrenzte CPU-Fehlerisolation mit neuer Anwendungsgeneration. Der genaue
Frame-Besitzvergleich bleibt erhalten; alte deaktivierte Profile bytegleich.
Beleg: build/codex-agent/r83ci-input-return/qualification01/acceptance-seal.json.

Der echte Desktop startet im VMware-Paket20260925-ci. Drei automatisierte
Mauspruefungen brachen vor dem ersten Klick im Windows-Helfer ab; keine
VMware-Eingabe- oder Stabilitaetsabnahme daraus. Manuelle Beobachtung folgt.
CB ist allein aktiv; verifizierte Quellen wiederhergestellt. Seine fuenf
Abnahmen mit acht frischen Fehlerfaellen bleiben ausstehend. Der reale
Supervisor-Backend-Pfad fuer Desktop-LAUNCH liefert weiterhin ENOTSUP;
initiale zwei adoptierte Apps ersetzen diesen fehlenden Startpfad nicht.
Keine abgeschlossene native64-Version; R3.6b bleibt zurueckgestellt.

## BY und BV abgenommen

Abgenommen: R8.3bv-large-file, candidate06. Alle fuenf Gates bestehen:
25 Hosttests, alte Profile, beide Builds/signierte Medien,14 vollstaendige
VM-Nachweise und unabhaengige Rohpruefung. Die vom Nutzer ausdruecklich
freigegebene Wiederverwendung unveraenderter Aufzeichnungen spart neue
VM-Starts; Herkunft und fruehere Fehler bleiben erhalten. 124729 Dateien
sind hashgebunden, originale Gastzeit3447,254s. Acht begrenzte Hash-Leser
reduzieren die Integritaetspruefung auf149,460s; finale Rohpruefung552,500s.
Beleg: build/codex-agent/r83bv-large-file/candidate06/acceptance-seal.json,
SHA256 5216da1e29a4a68af35ae255f528fdb346d05122ce83214269064e92281b220e.
Naechster Schritt nach sauberem lokalem Commit: native QuickJS-/Desktop-
Integration. Der vollstaendige native VMware-Desktop ist noch nicht fertig.

## Historischer Entwicklungsverlauf R8.3bv

Die freigegebene Korrektur in process_run_frames64 beseitigt den gemessenen
Stacküberlauf: Diagnose06 bestätigt64 Byte Scratch und unveränderte
Besitzertabellen. Build05 und signierte Medien03 bestehen. Diagnose08 startet
das1MiB-Programm zweimal über die normale Shell, jeweils LARGETEST_OK/Exit0,
gefolgt von cat und regulärem Shell-Ende; beide Datenträger bleiben unverändert.
Die Rohdatenprüfung wird für gemischte RNPGv2/v3-Abbilder vervollständigt.
Host18 prüft den zusammengesetzten Beobachter und bis261 Frames; Host19 belegt
die alten Windows-/Make-/Python-Baupfade bei ausgeschaltetem neuen Profil.
Die vollständige Fehlermatrix und alle fünf Abnahmegates stehen noch aus.
Die native QEMU-Prüfsteuerung einschließlich freigegebener WHPX-Messung ist
implementiert. Die Messung rechtfertigt keinen anderen VM-Stopp. Kopierarme,
explizit seitenbegrenzte Aufzeichnung senkt die native Beobachtungszeit der
Stichprobe von255 auf37ms je256 Stopps; Host76 bestätigt32 reale Rücksprungpaare.
Build19 besteht. Host77 besteht alle13 aktualisierten BV-Hostregressionen
in32,436s, einschließlich der korrigierten2320-Byte-ELF-Kontextprüfung.
Diagnose33 endet nach276,179s mit abgewiesenem largetest und einem Fehler der
alten Beobachter-Kontextgröße. Letzteres ist korrigiert, aber noch nicht erneut
im Gast geprüft. Cat, Shell-Ende, internes Aufräumen und No-write sind belegt.
Bei119940ms wurde noch ab Offset1030656 gelesen; kein vollständiger Großstart.
Nächster konkreter Vorschlag im Paketvertrag: native Prüfsteuerung auch für
wiederholte Task-Eintritte und PIO-Probes (zwei vorhandene RET-Stellen).
Erste Generationseintritte, CREATE/Console und mutierende Prüfpunkte bleiben
synchron. Diese Erweiterung über die ausdrücklich freigegebenen drei Stellen
ist noch nicht genehmigt oder implementiert. Fristen/IRQ/Gastzeit bleiben fest.
Verbraucht: Hosts01..79, Builds01..19, Medien01..03, Diagnosen01..31 und33;
Diagnose32, Build20 und Medien04 unbenutzt. Kein Abnahmegate oder BV-Commit.
Hardware-Build06 besteht; FAT-8.3-Zuordnung LARGETST.PRG und vollständige
1MiB-Wire-Rekonstruktion sind zusätzlich hostgeprüft. Details und alle endlichen
Versuchsfenster stehen im Paketvertrag; noch keine Laufzeitabnahme.
BV bleibt aktiv und nicht abgenommen; alle früheren Fehlversuche bleiben erhalten.


Fortsetzung genehmigt: Die erneute Benutzeranweisung gibt die dokumentierte
Ein-Datei-Erweiterung für config/x86_64_bootstrap.ld frei. Gates und verbrauchte
Versuche bleiben erhalten.

Historischer Umfangsstopp nach Build02: Programme/Dienste kompilieren; die abschließende
Acht-Prozess-Prüfung in config/x86_64_bootstrap.ld erlaubt den bereits geprüften
großen Scratchbereich noch nicht. Diese Datei fehlt im eingefrorenen Umfang.
Konkrete Ein-Datei-Erweiterung samt unveränderten Gates ist im Abschnitt
„Scope stop“ von NATIVE_LARGE_FILE_CONTRACT.md dokumentiert, noch nicht umgesetzt.
Host04 besteht11,457s;4/12 Hostversuche und2/4 Builds verbraucht, keine BV-Gäste
oder Abnahme. Änderungen und sämtliche Fehlnachweise bleiben erhalten.

Auf sauberem Commit67fa5dfd folgt das bereits genehmigte1MiB-Dateiladeprofil:
versionierte Capture-/FS-/Block-/Dienstadapter, normaler Shellstart und signierte
Medien mit geeignetem EXT2-Layout. Alter Dateipfad und alle CPU-/Heap-/Stack-/
Gerätegrenzen bleiben erhalten. Umfang, endliche Versuche und fünf Gates stehen
in NATIVE_LARGE_FILE_CONTRACT.md. QuickJS folgt nach dieser Abnahme; R3.6b vertagt.

## Abgenommen: R8.3bu – großes natives Programmabbild

Kandidat01 besteht alle fünf Gates (39.402/45.715/9.043/164.156/6.292s).
RNPGv3/CREATE-v7 ermöglicht256 Abbildseiten bei unveränderten alten Versionen,
CPU-/Heap-/Stackgrenzen und kleinem Bootkatalog. Acht Hosttests, vollständige
Standardpfad-Projektion, frischer Build,13 große und2 bisherige Gäste bestehen.
Rohdaten belegen Seitenrechte, hohe physische Frames, Quellüberschreiben,
Schutzfehler, CPU-Grenze, Abbruch und vollständige Freigabe über Generationen.
52 Frame-Zuteilungen je Kind; sechs OOM-Stellen0/1/2/13/26/51 mit Rückabwicklung.
Seal:a23dd20e7fe995d8a852656989a75d47ce435b9784de24aea033e4a4e707d86e.
Nächster bereits genehmigter Schritt: größeres unveränderliches Dateiladeprofil
mit normalem Shellstart, danach natives QuickJS. Noch kein Gesamtabnahme-
oder JavaScript-Gastnachweis. R3.6b bleibt ausdrücklich vertagt.

## Abgenommen: R8.3bt – native Textformatierung

Kandidat03 besteht alle fünf Gates (85.231/6.427/115.368/899.353/92.294s):13 Hosttests,
unveränderte Standardpfade, Referenz-/WHPX-Build, signiertes Acht-Dateien-Medium,
zehn frische Gäste und unabhängiger vollständiger Rohdaten-Replay.
Native LP64-/Varargs-/long-double-Formatierung, errno/FP-Erhalt beim Blockieren,
Zeigerfehler, Absturz, Hängen, CPU-Quote, Elternverlust und neue Generationen
sind geprüft. Kein Kernel- oder Berechtigungswechsel.
Der WHPX-Haltepunktfehler wurde mit kontrollierter Abbruchinjektion reproduziert
und mit derselben Injektion korrigiert nachgewiesen. Der Produktions-Verifier
enthält nur die per-CPU-/PC-gebundene Wiederaufnahme-Korrektur; alte Verifier,
fehlgeschlagene Kandidaten und Diagnosen bleiben erhalten. Die historische
Ursache von Kandidat01 ist mangels damaliger Registerdetails nicht rückwirkend
bewiesen; der reproduzierbare gleiche Fehlmechanismus ist behoben.
Seal:fc9d2d9b27df9c9558ddbb313b0102625732ae3919314b3b0680bd9387440100.
Abgenommen mit lokalem Commit33061693, sauberer Arbeitsbaum vor Folgeinventar.
Die native QuickJS-Größenmessung ergibt754104 ELF-Dateibytes und923968 Byte
Abbildspanne. Bisher erlaubt sind524288 Eingabebytes und196608 Programmbytes oberhalb
des reservierten Stacks. Der Host-Build ist kein Gast-/JavaScript-Nachweis.
Konkreter nächster Vorschlag: NATIVE_LARGE_EXECUTABLE_PROPOSAL.md, getrenntes
1-MiB-/256-Seiten-Profil mit begrenzten höheren FS-/Block-Anfragezahlen;
Laufzeiten, CPU-, Stack- und Geräteberechtigungen bleiben unverändert.
Die damalige Freigabegrenze ist durch die erneute Benutzeranweisung aufgehoben;
R8.3bu ist jetzt als erste begrenzte Transaktion aktiv. Native64 bleibt
unvollständig; R3.6b bleibt ausdrücklich zurückgestellt.

## Abgenommen: R8.3bs – native Mathematiklaufzeit

Aktuell: R8.3bs ist mit Kandidat07 abgenommen:21 Hosttests, Standardprojektion,
Referenz-/Hardwarebuild und signiertes Medium, zehn frische WHPX-Gäste sowie
unabhängiger vollständiger Rohdaten-Replay. Gatezeiten136,69/20,60/124,00/
1544,17/148,27s; jeder Gast unter180s. Enthalten sind44 binary64-Funktionen,
LP64-lrint, vier Rundungsmodi und FP-Isolation einschließlich Fehlerbehandlung,
Besitzerverlust und Wiederanlauf. Nachweise:build/codex-agent/r83bs-native-math/candidate07/.
Die isolierte Verifikator-Korrektur ist über binding09/compile-freeze13 gebunden;
frühere Fehlversuche bleiben erhalten. Nächste Bestandsaufnahme: native begrenzte
Textformatierung als QuickJS-Voraussetzung. Native64-Gesamtfreigabe bleibt offen;
R3.6b bleibt ausdrücklich zurückgestellt.

Vorheriger Stand: Diagnose27 besteht Besitzerverlust und vollständigen Wiederanlauf
in106,840s. Compiler13/binding09 erhält die physische Haltepunktbindung während
der gesamten Debugger-Registrierung; frühere CR3-Wechsel verfälschten Messungen.
Host28 besteht in22,774s mit den negativen Rohdatenfällen und vollständigem Replay.
Kandidat07 erhält unveränderte fünf Gates und zehn neue Gäste mit180s-Limit.
Noch keine Gesamtfreigabe und kein Implementierungscommit.

Vorheriger Stand: Kandidat06 bestand Gate1/2/3 und acht Gäste in94–105s. Der
Owner-loss-Fall scheiterte an einem durch den WHPX-Verifikator veränderten
Instruktionsbyte nach CR3-Wechsel. Compiler11/binding07 bindet die Wiederherstellung
an den physischen Speicher. Diagnose25 besteht damit beide Startbildprüfungen,
verfehlt jedoch die Kontrollpunkte der zweiten Mathematikgeneration. Diagnose26
protokolliert diese Haltepunktbindung begrenzt; keine gelockerten Kriterien,
keine vollständige Abnahme und kein Implementierungscommit.

Vorheriger Stand: Kandidat05 bestand Gate1/2/3 und fünf Gäste; der Absturzfall erreichte
beim zweiten ls das Feedlimit. Nach gemessenem Debugger-Aufwand und geprüfter
Register-/Haltepunktoptimierung besteht Diagnose24 vollständig in94,255s
Gastlaufzeit. Kandidat06 erhält unveränderte Gates, Nachweise und Zeitlimits;
noch keine vollständige Abnahme und kein Implementierungscommit.

Vorheriger Stand: Kandidat04 scheiterte erneut an Kontrollpunktduplikaten. Diagnose20
belegt IRQ-Injektion vor Debugger-Einzelschritt und ignorierte InterruptShadow-
Fehler im portablen Verifikator. Compiler09/binding06 korrigiert diese Ursache;
Diagnose21/22 bestehen vollständig (162,156/170,850s). Kandidat05 erhält zusätzlich
Prüfungen gegen ignorierte Werkzeugfehler und verbleibende Trace-Flags. Keine
abgenommene Gesamtmatrix und noch kein Implementierungscommit.

Vorheriger Stand: Kandidat03 besteht Gate1/2/3 und4-/8-GiB-Gäste. Gate4 stoppt
an doppelten Rundungskontrollpunkten; Diagnose18 belegt den Trace-Flag-Unterschied
bei identischer Rücksprungadresse. Host24 bestätigt die Hardware-Haltepunkt-Bindung
für diesen Kontrollpunkt und weiterhin strikte Duplikatablehnung. Diagnose19 besteht
vollständig (169,042s, Gast157,549s). Kandidat04 bindet den erfolgreichen Rohdaten-
Replay; die vollständige Abnahme und ein Implementierungscommit bleiben offen.

Vorheriger Stand: Der freigegebene portable QEMU/WHPX-Verifikator besteht Diagnose17
vollständig (171,630s): echter MXCSR-#GP13/Status141, numerische/FP-Nachweise
und Wiederherstellung. Host21 bestätigt den unabhängigen Rohdaten-Replay und
Bootstrap-Manipulationsprüfung (15,966s). Die fünf Abnahmegates einschließlich
zehn frischer Gäste bleiben offen; kein Implementierungscommit. Nachfolgende
Blockerbeschreibungen sind historische Diagnosen, keine erneute Freigabeanforderung.

Kandidat01 bestand Gate1/2; Gate3 scheiterte ausschließlich an Build-Pfaden in
identischen Stackberichten. Host22 bestätigt die korrigierte Pfadzuordnung samt
Größenmutation (0,323s). Kandidat02 übernimmt dieselben fünf Abnahmegates.

Kandidat02 bestand Gate1/2 und beide Builds, scheiterte am zusätzlich geprüften
Archivvergleich wegen DWARF-Build-Pfaden. Host23 bestätigt identische Code-/Daten-/
Relokationsinhalte (1,949s). Kandidat03 bindet Roharchive und vergleicht zusätzlich
temporäre Kopien ohne Debuginformationen; unveränderte Gastprädikate und Gates.

C/C++82ce94a0 ist sauber abgenommen. Die nächste gemeinsame JS-Voraussetzung
ist das bisher i386-spezifische libm-Profil:44 double-Funktionen, lrint und
fenv werden gemeinsam für AMD64/LP64 portiert. Vorhandene native eager
FP-Kontextisolation bleibt erhalten; kein neuer Kernelmechanismus.
Normales mathtest, signierte sieben Dateien, rohe numerische/FP-/Cleanup-
Nachweise und zehn frische Gäste gehören zum eingefrorenen Paket.
Kein zusätzliches Datei-, Netzwerk-, Geräte- oder Scriptrecht; R3.6b vertagt.
Vertrag: [NATIVE_MATH_RUNTIME_CONTRACT](../architecture/NATIVE_MATH_RUNTIME_CONTRACT.md).

R8.3bs ist implementiert, aber nicht abgenommen: ELF64/LP64-Mathematik,
FP-Blockierung/Scrub, sieben Dateien und echte x87-Ausnahme sind nachgewiesen.
Diagnose04 zeigt im gebundenen QEMU-TCG-Ziel keinen #GP bei ungültigem MXCSR:
Status95/state4 statt141/state3. Vertrag und Zehn-Gast-Gates bleiben unverändert.
WHPX-Initialisierung ist nachgewiesen. Der anschließend freigegebene optionale
Hardware-Prüfbootstrap besteht Build02 und Host14; Diagnose08 erreicht den
Haltepunkt vor Ring3. Diagnose09 scheitert beim Software-Breakpoint-Fallback,
Diagnose10 belegt ausdrücklich fehlendes Z0-Protokoll im installierten WHPX-Stub.
Der notwendige vollständige Hardware-Beobachter braucht deshalb eine geprüfte
alternative Werkzeugkette außerhalb der bisherigen Bootstrap-Korrektur.
Kein Gate-Erfolg, Implementierungscommit oder JavaScript-Abschluss behauptet.
Host13 besteht alle zehn Hosttests (60,218s), einschließlich der Ablehnung des
fehlenden #GP. Historie steht in CURRENT_WORK und im Vertrag.

## R8.3br: native C/C++-Allokationslaufzeit abgenommen

Kandidat01 besteht alle fünf Gates (39,484/11,414/29,149/1169,317/95,674s)
und zehn frische QEMU-Gäste:4/8GiB, Realloc-Erhalt, ungültige Freigabe,
New-OOM, Absturz, Hänger, CPU-Budget, Elternverlust und wiederholte Generationen.
Normales cpptest, ELF64-Archive/Sysroot, signierte Sechs-Dateien-Medien und
vollbreite Prozess-Backing-Zeiger sind integriert. Rohe Seitentabellen,
Heap-Inhalt und generationsgebundene Bereinigung, CPU-/Frame-/IPC-/Gerätebilanz
bestehen unabhängig; i386 und frühere CLI/GUI/UDP/TCP/DNS/HTTP-Artefakte bleiben
nachgewiesen. Kein Kernelumbau und keine neue Berechtigungsdomäne.
Evidenz: build/codex-agent/r83br-cpp-runtime/candidate01/.
Siegel: `b328527b28eebc5009829a7162a373622d3b0421358fc6321aebc53bbaa6162c`.
Nächste native64-Voraussetzung nach sauberem lokalem Commit inventarisieren;
JavaScript und native64-Gesamtabnahme bleiben offen, R3.6b bleibt vertagt.
Vertrag: [NATIVE_CPP_RUNTIME_CONTRACT](../architecture/NATIVE_CPP_RUNTIME_CONTRACT.md).

## R8.3bq: normales curl im nativen HTTP-Profil abgenommen

Kandidat01 besteht alle fünf Gates (20,298/2,239/37,921/1700,565/8,204s)
und25 frische QEMU-Gäste. Normales curl, strikte lokale TCP-Rechte,
HTTP-Framing und ursprüngliche Frist, begrenzte stdout-Ausgabe sowie signierte
Elf-Dateien-Medien sind integriert. 4/8GiB, Chunking/Fragmentierung, Größenlimits,
ungültige Antworten/Rechte/IPC und Anwendungs-/Dienst-/Elternfehler bestehen.
CPU-, Geräte-, IPC- und Neustartgrenzen bleiben unverändert; frühere Profile
und UDP/TCP/DNS bestehen ebenfalls. HTTPS, Dateischreiben und Browserrechte
bleiben separate Grenzen; R3.6b bleibt ausdrücklich vertagt.
Entwicklung:13 Hostläufe,2 Builds,2 Medienläufe,2 Diagnosegäste; alle früheren
Fehler bleiben erhalten. Evidenz: build/codex-agent/r83bq-application-http/candidate01/.
Siegel: `472ae6b447871fc3d0ee17bcd7b990b5e77a988c48eea002cc22574e19813a03`.
Die native64-Gesamtabnahme bleibt offen; das nächste priorisierte Paket folgt
nach sauberem lokalem Commit.

## R8.3bp: nativer DNS-Resolver abgenommen

Kandidat04 besteht alle fünf Gates (15,534/2,297/42,578/1676,145/9,900 s)
und 25 frische QEMU-Gäste. Normales `nslookup.prg`, sichere Antwort-/Cacheprüfung,
ursprüngliche Gesamtfrist, gepaarte UDP/TCP-Rechte und signierte Medien sind
integriert. 4/8 GiB, TCP-Fragmentierung, ungültige Antworten/Rechte/IPC sowie
Anwendungs-, Stack-, Treiber- und Elternfehler bestehen mit vollständiger
Bereinigung. CPU-/IPC-/Neustartgrenzen bleiben unverändert.

TCP bündelt begrenzt Bestätigungen; UDP/TCP vermeiden zehnfache Schlafaufrufe.
Alle früheren Fehler bleiben erhalten: 31 Entwicklungstests, zehn Builds,
elf Diagnosegäste und insgesamt 68 Abnahmegäste. Kandidaten01..03 sind verworfen.
Evidenz: `build/codex-agent/r83bp-application-dns/candidate04/`.
Siegel: `67de6f79f1197954ae0f6be953bd4f50429a1bce9d96c17ee707c4a1ad6014de`.

Nächster Schritt: verbleibende native64-Integration am sauberen Commit
inventarisieren und das nächste zusammenhängende Paket festlegen.
R3.6b bleibt zurückgestellt; noch keine vollständige native64-Systemabnahme.

## R8.3bo: DNS-Antwortprüfung abgenommen

Drei Gates bestanden (1,853/1,451/1,079 s): C-Verhalten bei O0/O2,
freistehende i386-/x86_64-Kompilierung und Quellenabgleich. Falsche Fragenamen,
beschädigte Paketenden, ungültige Kompressionszeiger/CNAME-Ketten und
unzulässige Antwortsektionen werden vor jeder Ergebnisveröffentlichung
abgewiesen. TTL folgt der gesamten Kette. Der ursprüngliche Fehlernachweis
bleibt erhalten. Diese Parserkorrektur ist noch keine native DNS-Laufzeitabnahme.

Nächster Schritt: Cache-/Fristbindung und native UDP/TCP-Resolverintegration
unter der vorhandenen Netzwerkfreigabe. R3.6b bleibt zurückgestellt.

## R8.3bn: native TCP-Clientobjekte abgenommen

Kandidat06 besteht alle fünf Gates (18.361/2.022/37.174/1482.443/7.681 s) und
25 frische QEMU-Gäste. Normales `nc.prg`, vier begrenzte TCP-Objekte,
Ring3-Protokoll, SDK und signierte Medien sind integriert. Nachgewiesen:
TCP/UDP bei 4/8 GiB, Rechte-/Generationsprüfung, Wiederholungen, volle Puffer,
fehlerhafte Pakete sowie Anwendung-/Stack-/Treiberfehler und Root-Erholung.
CPU-, IPC- und Neustartgrenzen bleiben unverändert; vollständige Bereinigung
und unabhängiges `cat` bestehen nach den Fehlerfällen.

Evidenz: `build/codex-agent/r83bn-application-tcp/candidate06/`.
Siegel: `6257b22f954e8c1bf583c9dc56e79c4b633506f05a72f8c59021324b63350336`.
29 Entwicklungstests, acht Builds, fünf Medienpaare, acht Diagnosegäste und
95 Abnahmegäste über sechs Kandidaten bleiben erhalten. Der vorherige
Commit-Stopp wegen Testdatei-Leerzeichen ist behoben; neue Dateien werden
bereits vor der Abnahme vollständig geprüft.

DNS, passive TCP-Serverlebenszyklen und die vollständige native64-Abnahme
stehen aus. Die Netzwerkfreigabe gilt weiter; R3.6b bleibt vertagt.

## R8.3bm: native UDP-Anwendungsrechte abgenommen

Kandidat04: fünf Gates und zwanzig frische QEMU-Gäste bestanden, einschließlich
Anwendungs-/Dienstfehlern, echter alter Epoche und geschlossenem Handle,
Paketverlust ohne Neustart, begrenzter Wiederherstellung und vollständiger
Ressourcenfreigabe. Normales `udp.prg`, native SDK-Objekte, beide Baupfade und
ein eigenes signiertes Medienprofil sind integriert. Kernel-ABI, alte Profile
und bestehende CPU-/IPC-/Neustartgrenzen bleiben unverändert.

Siegel `build/codex-agent/r83bm-application-udp/candidate04/acceptance-seal.json`:
`9da4534ae5acaf5112a45529b45d2f7e2664b300104b01229229302262b31bbc`.
Alle gescheiterten Kandidaten und Entwicklungsversuche bleiben erhalten.
Nächster zusammenhängender Schritt ist TCP unter der bestehenden Freigabe;
DNS und die weitere Systemintegration folgen. Kein vollständiges native64-
Release, keine öffentliche/physische Netzwerkfreigabe; R3.6b bleibt vertagt.

## 22. September: Anwendungs-Netzwerkrechte freigegeben

Der Benutzer hat den Vorschlag aus `da228540` ausdrücklich bestätigt:
„Ja, begrenzte Anwendungs-Netzwerkrechte freigeben“. Damit sind die dort
beschriebenen UDP/TCP-Anwendungsobjekte im lokalen QEMU-Testnetz autorisiert.
UDP, anschließend TCP und DNS benötigen eigene verifizierte Transaktionen,
jedoch keine erneute Freigabe derselben Berechtigungsdomäne. Frühere Hinweise
auf eine ausstehende Entscheidung sind historisch; eine Laufzeitabnahme
folgt daraus noch nicht.

## R8.3bl: Native Netzwerk-Shell abgenommen

candidate06 besteht fünf Gates (10.936/1.905/2.489/331.066/4.331 s) und vierzehn frische Gäste:
4/8 GiB, Treiber/Stack-Absturz, Hängen und CPU-Limit, beschädigte/veraltete
Steuerantworten, verlorene/verspätete/fremde/prüfsummenfehlerhafte Pakete,
fehlende NIC, manipulierte Dienstdatei, Neustart-Erschöpfung und Elternabsturz.

Normale net/ifconfig/arp/ping-Befehle verwenden getrennte Ring3-Dienste.
Paketverlust verbraucht keinen Neustart. Nach zwei Ersatzgenerationen bleibt
die Netzwerksperre bestehen; unabhängiges cat funktioniert weiter.
Die Rohdaten belegen Gerätesperre vor gruppenbezogenem CANCEL/WAIT,
korrekte Generationen, bereinigte DMA-/Staging-Bereiche und alle freien Frames
nach Sitzungsende. CPU-, IPC- und Neustartgrenzen bleiben unverändert;
Lade- und Anfragepausen liegen innerhalb der bestehenden Fristen.

Build14, signierte Medien11. Siegel:
`build/codex-agent/r83bl-network-session/candidate06/acceptance-seal.json`,
SHA256 `9aa0bc11dd15e8aca40c6e2fb267117933f9b6d4d4edcb684111553dfcf65f03`. Sämtliche Fehlversuche bleiben erhalten.
QEMU-Loopback-Kontrollpfad; keine physische DMA-Isolationszusage und kein
vollständiges native64-Release. TCP/DNS/DHCP, Anwendungssockets und die
Zusammenführung mit dem Desktop bleiben offen. R3.6b bleibt zurückgestellt.

## Nächste Autoritätsgrenze nach `a4c8bc96`

Native Anwendungen benötigen explizit delegierte Netzwerkobjekte; bestehende
Shell-/Treiberrechte oder i386-Syscallnummern erzeugen diese Rechte nicht.
Der [Vorschlag](../architecture/NATIVE_APPLICATION_NETWORK_PROPOSAL.md) begrenzt
UDP/TCP-Ziele und Objektgenerationen auf das lokale QEMU-Testnetz. Gemäß
`AGENTS.md` wartet diese neue Autoritätsdomäne auf eine ausdrückliche Entscheidung.
Keine neue Implementierungs- oder Ausführungsreservierung; R3.6b bleibt vertagt.

## R8.3bk: DMA-Sperre in allen nativen Kernel-Fatalpfaden abgenommen

Candidate03 besteht fünf Gates (1.493/1.540/1.313/33.128/6.595 s) und elf frische QEMU-Fälle:
acht normale Netzwerkfälle sowie Kernel-NX, Schedulerfehler und beschädigte
IO-Verwaltungsdaten bei aktivem DMA. PCI-Bus-Mastering, IMR und RX/TX werden
vor der Diagnose abgeschaltet und zurückgelesen. Beschädigte Daten bleiben
bis zum CLI/HLT-Pfad erhalten; ein danach eingespeistes Ethernet-Frame
verändert den DMA-Puffer nicht. Keine Wiederverwendung nach Kernelkorruption.

Build01; fünf Entwicklungshostläufe, ein Build und insgesamt 27 echte Gäste.
Siegel: `build/codex-agent/r83bk-network-fatal/candidate03/acceptance-seal.json`,
SHA256 `ef04c0a0d0c022461b8efa85294e0a291c1732733b1903e2fc50d9a0a0a15c9a`.
Fehlgeschlagene Versuche und doppelte Debugger-Haltepunktmeldungen bleiben
mit Rohdaten erhalten. Die acht normalen Prozessnachweise bleiben zwingend.

Nächster offener Schritt ist der Ring3-Protokollstack mit normaler
Shell-Einbindung. Kein vollständiges native64-Release; R3.6b bleibt vertagt.

## R8.3bj: Native Netzwerk-/DMA-Vermittlung abgenommen

Fünf Gates und acht frische QEMU-Fälle bestanden; Runtime 23,154 s,
unabhängige Rohdatenprüfung 5,471 s. Build03/Candidate02 verbindet einen
getrennten Ring3-Verbraucher mit festen kernel-eigenen RTL8139-DMA-Puffern.
Absturz, Hänger, CPU-Erschöpfung und Elternverlust sperren den alten Besitzer;
frische Generationen übertragen danach wieder geprüfte Ethernet-Frames.
Fehlende Hardware und IO-Quoten werden begrenzt behandelt.

Siegel: `build/codex-agent/r83bj-network-dma/candidate02/acceptance-seal.json`
(`20f6a40ae3d469ee8ca6a7430cdb37729f8e94f56d8d0199a7e3da26c83ac996`).
Nächster offener Teil: separater Ring3-Netzwerkstack und normale Shell-Nutzung.
Dies ist eine Mechanismusabnahme, keine vollständige native64-Systemabnahme.
Physische Hardware, öffentliche Netze, SMP und R3.6b bleiben außerhalb.

## R8.3bi: Grafische native64-Sitzung abgenommen

Candidate07 besteht alle acht Gates und28 frische QEMU-Gaeste:18 GUI- und
zehn CLI-/Medienfaelle. Runtime1436.462s, unabhaengige Rohdatenpruefung107.509s;
Referenzartefakte und Umfangskontrolle bestanden. Build07/media07 sind gebunden.
Die Sitzung bietet zwei getrennte Ring3-Anwendungen, lokalen Fokus/Capture,
begrenzte Ausgabe sowie gepruefte Fehlerisolation und Wiederherstellung.
GUI-Neustarterschoepfung sperrt weitere GUI-Starts; normale Dateizugriffe bleiben
verfuegbar. Alle Fehlversuche und verbrauchten Budgets bleiben erhalten:
44 Entwicklungshost-Kommandos,88 physische Gaeste,7 Builds/Medien,21 BIOS.

Start: `scripts/start-x86_64-graphical.ps1`; in der seriellen Shell `desktop`.
[Kurzanleitung](NATIVE_GRAPHICAL_SESSION_QUICKSTART.md). Der Starter prueft den
lokalen Abnahmecommit und die unveraenderten Artefakte; Laufzeit maximal180s.
Abnahmebeleg: `build/codex-agent/r83bi-graphical-session/candidate07/acceptance-seal.json`.
Dies ist die abgenommene begrenzte grafische Forschungssitzung. Netzwerk,
Browser/JS, weitere Anwendungen und native System-/Hardwareabnahme bleiben offen.
R3.6b bleibt vertagt; neue Netzwerk-/DMA-/Schreib-/SMP-Rechte sind nicht freigegeben.

## R8.3bh: Terminal-Dienstberechtigung abgenommen

Candidate02 besteht alle zehn Gates:15 Eingabe-/Dienstgaeste und zehn
vollstaendige CLI-/Mediengaeste frisch, ohne Wiederverwendung. Runtimegate
1263.880s bei3300s Limit; unabhaengige Rohdaten-, Referenz- und Scope-Pruefung
bestanden. Explizite Zulassung6, Uebernahme4 und Widerruf7 sind generationsgebunden;
Root-Eingabeausschluss, Dienstabsturz, CPU32 und beaufsichtigter Haengeabbruch
sind nachgewiesen. Der Elternausfallgast prueft den Verlust vor der Uebergabe.

Abnahmeseal: `build/codex-agent/r83bh-terminal-service/candidate02/acceptance-seal.json`
SHA256 `d705d285357821083578fc6d165fd1f4afe5293285d7b4a83a97c5b069b85fae`.
Build04/media04 bleiben exakt gebunden. Vier Builds, vier Medienversuche,
zwoelf BIOS-Assemblierungen, zwoelf Entwicklungshost-Kommandos und46 physische
Gaeste einschliesslich aller Fehler bleiben erhalten. Der CLI-Adapter prueft
neue abgelehnte Anfragen strikt; die bisherigen Operationen und Grenzen bleiben erhalten.

Die dauerhafte grafische Sitzung samt Fokus/Capture und Anwendungen ist bereits
freigegeben und folgt nach dem sauberen lokalen Paketcommit. Noch kein Desktop-
oder OS-Abschluss; R3.6b bleibt vertagt.

## Historie R8.3bh: Candidate02 nach strikter CLI-Adapterkorrektur

Candidate01 bestand Gates1..6 und alle15 Eingabe-/Dienstgaeste. Die erste
CLI-Aufzeichnung stoppte bei der alten Terminalauswertung, die neue Operation6
noch nicht kannte. Der neue Adapter akzeptiert ausschliesslich die kanonische,
abgelehnte Anfrage an den lebenden fremden Root-Peer und unveraenderten Besitz.
Alle anderen Operationen bleiben beim bisherigen Validator. Vollstaendige
Wiederauswertung der gespeicherten100.160s-Aufzeichnung und70 Negativmutationen
bestehen; auch alle bisherigen Hostgruppen sind gruen.

Zwölf Entwicklungshost-Kommandos und21 physische Gaeste einschliesslich der
Fehler sind erhalten. Build04/media04 bleiben exakt. Candidate02 wiederholt
alle zehn Gates und25 Gaeste frisch innerhalb unveraenderter Laufzeitgrenzen.
Die bisherige Paketabnahme bleibt offen; anschliessend folgt die autorisierte
dauerhafte grafische Sitzungsintegration ohne Routinefreigabe.

## Historie R8.3bh: Implementierung fertig, vollstaendige Abnahme startet

Geschuetzte Dienstzulassung6, Uebernahme4 und Widerruf7 sind implementiert.
Der normale Ring3-Verbraucher nutzt die Berechtigung; die Shell prueft fremde,
Treiber- und veraltete Generationen sowie ihren eigenen Eingabeausschluss.
Hostverhalten O0/O2, unveraenderte deaktivierte Profile und der vollstaendige
Rohdatenvergleich bestehen. Gesonderte echte Dienstfehler UD/CPU32/Haengen
kehren jeweils zur Shell, zum Dateizugriff und zu neuen gesunden Diensten zurueck.

Neun Entwicklungshost-Kommandos, vier Builds, vier Medienversuche, zwoelf
BIOS-Assemblierungen und fuenf Gaeste sind erhalten, einschliesslich FAT12-
Kapazitaetsfehler und korrigierter Negativpruefung nach beendeter Peer-Generation.
Build04/media04 werden jetzt fuer Candidate01 unveraenderlich gebunden:
zehn Gates,15 Eingabe-/Dienstfaelle und zehn bisherige CLI-Faelle frisch,
anschliessend unabhaengige Rohdaten-, Referenz- und Scope-Pruefung.
Noch keine Paketabnahme; dauerhafte grafische Sitzung bleibt anschliessender Auftrag.

## Historie R8.3bh: Terminal-Dienstberechtigung autorisiert und aktiv

Der erneute Fortsetzungsauftrag gibt die grafische Sitzungsdomaene frei.
Zuerst wird die geschuetzte exklusive Dienstzulassung samt Widerruf und realem
Ring3-Fehlernachweis umgesetzt. Vertrag: `NATIVE_TERMINAL_SERVICE_CONTRACT.md`.
Die anschliessende dauerhafte Ring3-Sitzung/Fokusintegration bleibt Teil des
Auftrags; Paketgrenzen erfordern keine Routinefreigabe. Noch kein Desktop-
oder Systemabschluss. R3.6b bleibt vertagt.

## Historie vor erneuter Freigabe: grafische Sitzungsautoritaet noch offen

Nach sauberem Eingabecommit `fd7a2f77` zeigt die Bestandspruefung eine echte
neue Rechtevergabe: Der vorhandene Desktop verwendet Terminal-Dienstuebernahme
(Operation4), die native64 ausdruecklich mit-95 abweist. Die bisherige
5000ms-Eingabesitzung verteilt nur an einen festen Vordergrundverbraucher.
Dauerhafter Compositor und Fokus-/Capture-Verteilung brauchen einen eigenen
begrenzten, generationgebundenen Dienstvertrag. Konkreter Vorschlag:
[Grafische native Sitzung](../architecture/NATIVE_GRAPHICAL_SESSION_PROPOSAL.md).
`AGENTS.md` verlangt hier ausdrueckliche Freigabe fuer die neue Autoritaetsdomaene;
dies ist keine erneute Diagnose-/Paketbestaetigung. Kein neues aktives Paket,
Build oder Gast reserviert; Eingabeprofil nutzbar, R3.6b weiterhin vertagt.

## Native PS/2-Eingabe R8.3bg abgenommen, 21. September 2026

Alle zehn Gates von Candidate04 bestanden: zwoelf echte Eingabefaelle und
zehn vollstaendige bisherige CLI-Faelle, insgesamt 22 frische Gaeste ohne
Wiederverwendung. Unabhaengige Rohdaten-, Rechte-, Pixel-, Reap- und
Medienpruefung bestanden. Gastzeit insgesamt 1098.291s; Laufzeitgate1199.729s
bei3300s Limit. Getrennter Ring3-Treiber, feste Portvermittlung und gerichtete
IPC-Zustellung funktionieren einschliesslich Absturz, CPU/Hang, Quoten,
veralteter Generation, Protokollfehler, Flut, fehlendem Geraet und Elternausfall.

Build06 und signierte media05 sind ueber den normalen Eingabestarter gebunden.
Start und Grenzen: [Native64-Eingabe](../NATIVE64_INPUT_QUICKSTART.md).
Abnahmeseal: `build/codex-agent/r83bg-input/candidate04/acceptance-seal.json`
SHA256 `5fe736bff6b34ad5aedfb65633639cfb3d74c9354b3c4de39fbc683bd10c7134`.
Historie:43 physische Gaeste, sechs Kernelbuilds, fuenf Medienversuche und
24 Entwicklungshost-Kommandos einschliesslich aller erhaltenen Fehler.
Noch offen: dauerhafte interaktive Shell/Desktop, Netzwerk und weitere
Plattform-/Systemabnahme. R3.6b bleibt ausdruecklich vertagt.

## Historie R8.3bg: autorisierte native Eingabe, Abnahme offen

Candidate01 bestand Gates1..6 und fuenf Eingabefaelle; der Haengefall
stoppte die Abnahme: Der Fehlerfalltreiber verwendete1000ms statt der erlaubten
maximal100ms pro Schlafaufruf. Ein Test des echten Dienstprogramms reproduziert
den Fehler und besteht mit sechzig100ms-Schritten. Build06/media05 sind neu
gebunden; Candidate02 wiederholt alle zehn Gates mit allen22 frischen Gaesten.
Die strikte Forderung nach beaufsichtigtem Abbruch bleibt unveraendert.
Candidate02 besteht den echten Haengeabbruch, stoppt aber beim Quotenoracle:
eine vollstaendige Kernel-Reapmeldung unterbricht die mehrteilige Userausgabe.
Der Hosttest reproduziert die gespeicherten CRLF-Bytes; die korrigierte
Auswertung besteht den kompletten gespeicherten Quotenfall. Rohdaten und
separate Reappruefung bleiben erhalten. Candidate03 wurde vor Gates und Gaesten
zurueckgezogen. Candidate04 wiederholt alle zehn Gates und22 frische Gaeste.

Der Nutzer hat den konkreten PS/2-Vorschlag durch erneuten Fortsetzungsauftrag
am21. September freigegeben. Ein aktives Paket verbindet begrenzte Portvermittlung
mit getrenntem Ring3-Dienst, Tastatur-/Mausdekoder, gerichteter IPC-Zustellung
und normalem Grafikverbraucher. Die bestehende Ein-Peer-Grenze erfordert zwei
Endpunkte mit hoechstens32 kanonischen Weiterleitungen durch die Shell.

Hostverhalten und Build/Medien sind geprueft. Der reale Empfangsnachweis
isolierte einen Fehler bei der seriellen Ausgabe ueber64 Bytes; die Korrektur
hat einen reproduzierenden Hosttest. Gast08 besteht drei Sitzungen samt
Tastatur/Maus, Generationen, Aufraeumen und Dateiliveness in40.289335900044534s.
Die zwoelf Eingabefaelle, volle bisherige CLI-Matrix und zehn eingefrorenen Gates
stehen als naechste geschlossene Abnahme an.
Keine Systemabnahme oder fertiger Desktop; historische BE/BF-Nachweise und
R3.6b-Vertagung bleiben erhalten. Aktueller Vertrag:
`docs/architecture/NATIVE_INPUT_CONTRACT.md`.

## Normaler Grafikstarter R8.3bf abgenommen

Kandidat02 besteht sechs Gates/zwoelf Hostmethoden und zwei echte Sitzungen
HDD4GiB/Diskette8GiB,115.25183679995826s. Normaler Ring3-Programmstart,
Grafik und Dateiausgabe, Generationen/Reap, beide Root-Abschluesse sowie
unveraenderte Medien und begrenztes Cleanup sind vollstaendig nachgeprueft.
Keine Builds/Medienpublikationen; vorheriger Startfehler verbrauchte null
Gaeste und bleibt erhalten. Einstieg `scripts/start-x86_64-display.ps1`,
Anleitung `docs/NATIVE64_DISPLAY_QUICKSTART.md`, Belege
`build/codex-agent/r83bf-display-delivery/candidate02/`.

### Entwicklungshistorie

Sauberer BE-Abschluss `17d12819`, Vertragscommit `9a331894`: separater
Windows-/Python-Starter fuer die exakt abgenommenen Grafikmedien. Signaturen,
Index und alle Eingaben vor Start pruefen; private Medien vor/nach Sitzung,
feste30..320s samt3s Cleanup, serielle Shell. Sechs Gates, zwei60s-Gaeste,
kein neuer Kernel, keine Medienpublikation oder Erweiterung der Gastautoritaet.

## Grafikvermittlung R8.3be abgenommen, 21. September 2026

Kandidat03: zwoelf Gates, neun Grafik- und zehn CLI-/BIOS-Faelle inklusive
unabhaengigem Rohdatenreview bestanden. Nachgewiesen sind feste Ring3-Kacheln,
NX/UC-Kernelvermittlung, Generationen, Quota und Recovery in beiden VBE-Modi.
Fuenf neue Negativgaeste107.87658979999833s;14 vollstaendig nachgepruefte,
unveraenderte Aufzeichnungen wiederverwendet. Insgesamt23 physische Gaeste
1003.9200396001688s/vier Kernelbuilds/zwoelf BIOS-Assemblierungen/vier Medien.
Seal/Commitbeleg unter `build/codex-agent/r83be-display/candidate03/`;
alle gestoppten Kandidaten bleiben unveraendert. Naechste Arbeit erst nach
sauberem lokalem Implementierungscommit. Desktop/Eingabe/Netzwerk und weitere
Plattformabnahme offen, R3.6b bleibt vertagt.

### Entwicklungshistorie

Explizit freigegebenes QEMU-Profil auf der angenommenen CLI. Build04 und
signierte Medien04 sowie ein vollstaendig nachgepruefter Grafiklauf bestehen:
drei Ring3-Kacheln/Generationen, zwei Shell-Laeufe, unberuehrte Medien.
Kandidat01 prueft zwoelf Gates und19 frische Grafik-/CLI-Gaeste. Terminalrecht
und Anzeigerecht werden nur im Opt-in kombiniert; der bestehende Zeigerpruefer
wird in hoechstens16 Teilbereichen vor jeder Ausgabe angewandt. Vier Builds,
zwoelf BIOS-Assemblierungen, vier Medienversuche und vier Entwicklungsgaste
samt allen Fehlerbelegen sind erhalten. Noch keine Grafikpaketabnahme;
Desktop, Eingabe, Netzwerk und weitere Plattformabnahme bleiben offen.

Fortsetzung Kandidat03: nach dokumentiertem Timing-Entscheid und erneuter
Fertigstellungsanweisung private Display-Neubewertung mit unveraenderter
Verarbeitungs-/Kindfrist und ausschliesslich zwei erfolgreichen CLOSE-Paaren
zwischen Timeout und Wecken. Fuenf Hostmethoden/Gegenproben bestehen; alter
CLI-Fehler bleibt archiviert. Hashgebundene komplette Neubewertung von14
vorhandenen Gaesten und genau fuenf noch fehlende BIOS-Negativgaeste, keine
Builds oder Medien. Kandidat02 bleibt gestoppt,18 physische Gaeste insgesamt
896.0434498001705s verbraucht. Zwoelf Gates vor jeder Annahme verpflichtend.

## Vereinbarte CLI-Erstlieferung abgeschlossen, 21. September 2026

R8.3bd/Kandidat02 besteht neun Gates und alle zehn BIOS-/Gastfaelle samt
unabhaengigem Rohdatenreview. Die signierte lokale QEMU-CLI-Version verwendet
den unveraenderten akzeptierten BC-Kernel und normale Shell/cat/ls/probe.
Start und Grenzen: `docs/NATIVE64_CLI_QUICKSTART.md`,
`scripts/start-x86_64-cli.ps1`. Zwei Shell-Laeufe/320s-Sitzung, Nur-Lese-Objekte;
keine Desktop-/Netzwerk-/Hardware- oder Produktionsfreigabe. Uebrige Plattform-
arbeit nachgelagert, R3.6b ausdruecklich vertagt; kein neues aktives Paket.

Seal SHA256 `53465d21bb9809cfb1a1d515fa036a27ae133a7262d6a4ad936f53fc6780752c`.
Finalbeleg mit lokalem Commit:
`build/codex-agent/r83bd-cli-delivery/candidate02/verification-status-cli-delivery-final.json`.
BD insgesamt zehn physische Gaeste585.8585124001256s/ein Medienpaar/drei
unveraenderte BIOS-Assemblierungen, kein Kernel-/Programm-/Testclient-Build.
Der Nachweis getrennter erfolgreicher CLOSE-Aufrufe korrigiert nur die falsche
atomare Zeitstempelannahme; urspruengliche Broker-/Kindfristen und alle
CPU-/IPC-/Rechteentzugs-/Cleanup-Pflichten bleiben bestehen. Alte Fehlbelege
bleiben erhalten, fuenf vorhandene Positivaufzeichnungen vollstaendig neu
ausgewertet, nur fuenf zuvor fehlende Negativgaeste107.99955980008235s neu.

## Historie vor der begrenzten Erstlieferung

BD-Fortsetzung21.09.: Kandidat01 stoppt nach Gates1..5/vier bestandenen
Positivfaellen im Hang-Ausgangsnachweis. Absolute Brokerfrist/erste Sperre4550ms
korrekt; getrennte zweite Kanalschliessung/Wecken4560ms vor originaler
Kindfrist4590ms. Kein atomarer Zwei-Syscall-Zeitstempel garantiert. Begrenzte
Korrektur nur im neuen CLI-Pruefadapter mit Red/Green-Mutationsregression;
unveraenderte BC-/Kernel-/Programmbinaerdateien und alle Sicherheitsfristen.
Kandidat02 bindet fuenf originale Aufzeichnungen477.85895260004327s und
ein Medienpaar; volle Neubewertung plus genau fuenf restliche Negativgaeste,
keine neuen Builds. Neun Gates/komplette Rohdatenabnahme bleiben Pflicht.

Naechste saubere Transaktion21.09.: R8.3bd liefert die ausdruecklich gewaehlte
QEMU-CLI-Forschungsversion auf dem akzeptierten BC-Stand `abe3cc7d` aus.
Signierte BIOS-Medien, normale Programme und Nur-Lese-Daten, begrenzter
Launcher und Kurzanleitung in einem Paket; kein Kernelneubau. Vollstaendige
zehnteilige BIOS-Abnahme bleibt Pflicht. Desktop/Browser/Netzwerk und weitere
Plattformabnahme bleiben nachgelagert, R3.6b explizit vertagt.

Abnahme21.09.: R8.3bc/Kandidat08 besteht alle neun Gates und16 Gastfaelle,
einschliesslich unabhaengiger Gesamtauswertung.80 echte Antworten bei23
CPU-Ticks; CPU32/1000ms unveraendert. Normaler cat/ls-Dateizugriff und
Fehlereindaemmung abgeschlossen, signierte begrenzte CLI-Auslieferung als
naechste saubere Transaktion. Seal SHA256
`db3764b54b75fb2204f13fa3c26360a4e6dc47d3c97aae720614acdf7ae7c24b`.
34 physische Gaeste2753.232284900034s/zwei Kernelimages/zwei Testclient-Builds
einschliesslich aller erhaltenen Fehler. Kein vollstaendiges Desktop-/Netzwerk-
oder Hardware-OS behauptet; R3.6b bleibt vertagt. Nachfolgend die Verlaufslage.

Fortsetzung21.09.: gezielte IPC-Kernpfad-Erweiterung ausdruecklich genehmigt.
Kandidat07 erreicht80 Antworten bei23 CPU-Ticks; Gates1..5 bestanden. Die
Auswertung stoppt an der81.-Anfrage-Queueordnung, nicht mehr am CPU-Budget.
Kandidat08 bindet den korrigierten Nachweis an dieselben kompletten Rohdaten
und dasselbe Image;15 frische restliche Faelle, keine Neubauten reserviert.
Unveraenderte EAGAIN-Warter werden nicht erneut versiegelt; alle Reads bleiben.
Vier/acht Slots O0/O2 sowie IPC-Fault-/Completion-/Handoff-Hosttests bestanden.
Kandidat07 reserviert genau einen Neubau und16 frische Gaeste, Budgetfall zuerst,
Stopp bei erstem Fehler. Alte Nachweise qualifizieren keinen geaenderten Kernel;
alle Quoten, Zeitgrenzen und80 realen Antworten unveraendert erforderlich.

Historischer Stopp20.09.: R8.3bc15/16 Faelle bestanden, Kandidat06-Budgetgast
erreicht52 Antworten vor CPU32 statt erforderlicher80. Gates1..5 bestanden,
Gates7..9 nicht ausgefuehrt; keine Abnahme/Commit/CLI-Publikation.18 physische
Gaeste1588.3585832000244s/ein Kernelimage/zwei Testclient-Builds verbraucht,
saemtliche Fehler erhalten. Weitere kleine Client-Umbauten haben keinen
nachgewiesenen Nutzen. Native IPC-/CPU-Kernpfad-Arbeit samt bestehenden
Integritaets-/Kostenregressionen erfordert eine ausdrueckliche Erweiterung des
aktuellen erlaubten Paketumfangs; keine Sicherheitsgrenze/Pruefung lockern.
Details und exakter Stoppbeleg: [CURRENT_WORK](CURRENT_WORK.md).

20.09.2026: Read-only-Anwendungsrechte ausdruecklich freigegeben. R8.3bc ist
der naechste aktive gemeinsame Schnitt: Ring3-Objektbroker, nativer SDK-Adapter,
echte cat/ls, Windows/Make-Medien und komplette Fehler-/Widerrufs-/Recovery-
Nachweise. Kein Kernel-VFS, keine ambienten oder Schreib-/Geraeterechte.
Kandidat01 besteht Host-/Abhaengigkeits-/Build-/Mediengates1..5. Ein Image,
ein vollstaendiger FAT12-Gast60.63747690001037s; echte cat/ls/probe und alle
bisherigen Rohpruefungen erfolgreich, neue relative Fristenannahme abgewiesen.
Kandidat02 korrigiert nur die Zeitstempel-Auswertung: exakter Ablesezeitpunkt
zwischen letztem Root-Abschluss und Eintritt, Antworten strikt vor gleichem
absolutem Ende. Voller gebundener Rohdaten-Replay, kein Neubau,15 neue Gaeste;
volle16-Fall-Abnahme bleibt offen. [Vertrag](../architecture/NATIVE_APPLICATION_FILES_CONTRACT.md).
Kandidat03: Rechtefall belegt sicheren Fehlerexit nach Endpoint-Widerruf statt
Zwangsabbruch. Nur Prueferkorrektur mit vollstaendiger negativer IPC-/Exitkette;
acht vorhandene Gaeste662.6280681999633s voll wiedergeben, acht neue, kein Neubau.
Neues ausdruecklich genehmigtes erstes Lieferziel: bootfaehige QEMU-CLI-
Forschungsversion mit Shell/Programmstart/Nur-Lese-Dateien; Desktop, Browser,
Netzwerk und restliche Plattformabnahme sind nachgelagerter Ausbau. Kein
vollstaendiges OS behaupten, keine Sicherheitspruefung streichen. Nach sauberem
BC-Abschluss direkt vorhandenes Image/Medien/Startskript/Anleitung buendeln.
Kandidat04: Nach bestandenem Absturzfall ist auch der Haenger sicher beendet,
aber mit SDK-Fehlerexit nach Deadline-Widerruf statt Zwangsabbruch. Nur exakte
zeitliche Pruefkette korrigieren; zehn gespeicherte Gaeste847.548560199968s
voll auswerten, sechs neue, weiterhin ein Image und unveraenderte Sicherheits-
grenzen. Keine Teilabnahme oder vorzeitige Liefermeldung.
Kandidat05:15 Faelle bestanden; Budget-Testlast lief nach70 statt80 Antworten
in CPU32. Nur separaten Testclient effizienter bauen, Normalprogramme und
Kernel exakt behalten. Ein neuer Gast,15 vollstaendige gebundene Replays,
neun Gates unveraendert.16 Gaeste1396.892000199994s/ein Image verbraucht,
fehlgeschlagene Messung bleibt unveraendert; kein teilweiser Abschluss.
Kandidat06: erste Testoptimierung widerlegt (54 Antworten, CPU32). Nur redundant
geloeschten Empfangspuffer gemaess bestehendem IPC-Vertrag wiederverwenden und
feste Puffer seitenausrichten; Nachweis des Nutzens erst im neuen Gast.17 Gaeste
1492.2858473000233s/ein Kernelimage/ein Test-ELF verbraucht; ein weiterer
Test-ELF/Gast reserviert,15 Replays, keine gelockerte Grenze/Teilabnahme.

Sauberer Abschluss20.09.2026: R8.3bb `813606cf`, finaler Nachweis
`build/codex-agent/r83bb-wide-shell-media/candidate02/verification-status-wide-shell-media-final.json`
SHA256 `496442d7a594b347915ad28313474ab6bec2728e84d80e74bd33acd61d7ae4d4`.
Die anschliessende Bestandspruefung identifiziert die naechste echte Rechte-
grenze: AY verbietet Vordergrundprogrammen explizit FS-Endpunkte; vorhandene
cat/ls-Adapter rufen die alte Storage-ABI auf, die native Kindprofile nicht
zulassen. Root-eigener Dateistart erteilt dem Kind keine Datenleserechte.
Vorgeschlagen ist ein eigenes versioniertes, generations-/objektgebundenes
Read-only-Anwendungsprofil mit SDK/normalen Tools/Buildmedien und vollstaendiger
Fehler-/Widerrufs-/Recoveryabnahme in einem Schnitt. Nur explizit ausgewaehlte
unveraenderliche Dateien/Verzeichnisse, keine ambienten Namespace-, Schreib-,
PIO/DMA- oder Taskverwaltungsrechte; alte Profile/Sicherheitsgrenzen bleiben.
Freigabe dieser neuen Autoritaet steht aus: kein Folgepaket aktiviert, keine
Build-/Gastreservierung, keine Implementierung. [Befund](CURRENT_WORK.md).
R3.6b bleibt deferred; die gesamte native Systemabnahme ist weiterhin offen.

Abnahme20.09.2026: R8.3bb/Kandidat02 besteht alle acht Gates samt kompletter
unabhaengiger Zehn-Fall-BIOS-/Runtime-/No-write-Auswertung. Der korrigierte
signierte EXT2-Negativtest erreicht tatsaechlich den Inode-Pruefer bei6528.
Alle zehn originalen Gastbelege exakt quell-/werkzeug-/medien-/rohdateigebunden
wiederverwendet, keine neuen Builds oder Gaeste. Kumulativ null Kernelbuilds,
ein signiertes Medienpaar, zehn physische Gaeste521.0947888000519s. Seal
`build/codex-agent/r83bb-wide-shell-media/candidate02/acceptance-seal.json`,
SHA256 `259fb787ff83399a97a4c32779950b3a533fd5d1db961fd5009da4545b1775ee`.
Die urspruengliche falsch positive Hostbehauptung bleibt abgelehnt erhalten.
Ergebnis-/Queue-Abschluss, danach sauberer lokaler Commit/finaler Beleg und
naechste Bestandspruefung; noch kein vollstaendiges OS/Hardware/Production Trust.
Historische Arbeitsfenster folgen unveraendert, R3.6b bleibt deferred.

R8.3bb/Kandidat02: Nach acht gruenen Gates/zehn bestandenen BIOS-Faellen fand
die direkte Abschlusskontrolle einen Hosttest, dessen CRLF-JSON schon vor der
beabsichtigten EXT2-Pruefung abgewiesen wurde. Kein Abschlusscommit. Korrektur
nur am Pruefadapter (kanonische Bytes plus zwingende EXT2-Fehlerklasse), acht
Gates erneut, null neue Builds/Medien/Gaeste. Alle zehn alten Laufzeitbelege
werden vollstaendig und exakt quell-/werkzeug-/image-/rohdatengebunden erneut
geprueft. Produktcode und publizierte Medien bleiben unveraendert; keine
Umdeutung des fehlerhaften Hostnachweises. Bisher ein Medienpaar/zehn Gaeste.

Aktiv nach sauberem BA-Commit `02202bd3`: R8.3bb bindet das unveraenderte,
abgenommene Wide-File-Image an signierte BIOS-HDD-/Floppy-Medien. Bestehende
AZ-Publikation/Verifikation/BIOS-Handshake und komplette BA-Rohbeweise gemeinsam
wiederverwenden; getrennte Profilidentitaet und1MiB-EXT2-1k-Datenmedium mit
direkter/einfach-indirekter Datei. Kein Kernel-Neubau, ein Medienpaar, zehn
neue begrenzte BIOS-/Recovery-/Korruptionsgaeste, acht eingefrorene Gates.
Noch keine Abnahme dieses neuen Pakets oder des gesamten OS. R3.6b deferred.

Abnahme20.09.2026: R8.3ba/Kandidat12 besteht alle neun Gates und die komplette
12+18-Gastmatrix samt unabhaengiger Rohdaten-/Scope-Pruefung.512KiB in beiden
Root-Durchlaeufen geladen und gestartet (577.539s), alle fuenf Fehlerfaelle gruen.
Kein Neubau; sechs exakt gebundene Normalfaelle wiederverwendet,24 neue Gaeste.
Seal `build/codex-agent/r83ba-wide-file/candidate12/acceptance-seal.json`,
SHA256 `1143439f309e95a9b8d1142a3ddd9c846c420ce488c9829591322b024e23f122`.
Alle Grenzen/Rechte/Legacy-APIs erhalten; kumulativ vier Builds/48 physische
Gaeste3080.7771372999996s, Fehlschlaege erhalten. Ergebnis-/Queue-Schliessung,
danach sauberer lokaler Commit und finaler gebundener Beleg. Kein neuer BIOS-
Medienbeleg und noch keine gesamte64-Bit-OS-/Desktop-/Hardware-Abnahme. EXT2-1k
voll512KiB mit Doppelindirektion bleibt ausgeschlossen. R3.6b weiter deferred.

Historische Freigabe20.09.2026: Nutzerfreigabe fuer Kandidat12 umgesetzt: ausschliesslich
Voll512KiB-Zwei-Root-Hostfrist900s/897s Beobachtung/3s Cleanup; sonst300/45s und
alle Kernel-/CPU-/ATA-/IPC-/Beweisgrenzen unveraendert. Kein Neubau. Sechs exakt
gebundene bestandene Kandidat11-Normalfaelle mit vollstaendigem Rohreplay, sechs
neue BA- plus18 Legacy-Gaeste/3210s reserviert; neun Gates einmalig, erster Fehler
stoppt. Vier Builds/24 physische Gaeste1932.9222295999061s bleiben verbucht.
Das ist eine Pruefvertragsfreigabe, noch keine Paket- oder OS-Abnahme.

Historischer Befund20.09.2026: Kandidat11 Gates1..5 und sechs Normalfaelle bestanden.
Anlaufwartezeit-Fehler korrigiert. Voll512KiB erreicht im ersten Root EOF und
echten Programmeintritt bei89830ms Gastzeit; die volle Zwei-Root-Abnahme stoppt
danach an297s Beobachtung/299.242s gesamt. Zweiter Root bereits gestartet, kein
Kapazitaetsfehler (ca58MiB Trace,2118 CPU-Saetze), aber noch kein voller Nachweis.
Stop12842bf6de4f6a24fff803a99b18bd32352490a1078389a7143034be4cf72582;
vier Builds/24 physische Gaeste1932.9222295999061s. Vorschlag: ausschliesslich
Vollgroessen-Hostfrist900s inklusive3s Cleanup, unveraenderte Kernel-/Einzel-
fristen und Assertions, kein Neubau, sechs exakt gebundene Normalbelege plus
sechs neue BA-/18 Altgaeste. Neun Gates/Gesamtbudgets bleiben. Noch keine
Freigabe/Ausfuehrung dieser Aenderung; [aktueller Befund](CURRENT_WORK.md).
Keine BA-/Gesamt-OS-Abnahme; nachfolgende Fenster sind Historie.

Kandidat11: Diagnosekorrektur und sechs neue Normalgaeste bestehen; direkte
Quellpruefung bestaetigt jedoch einen bisher ungetesteten ersten Lesezugriff
nach abgewiesener Anfrage bei50 statt100ms. Kandidat10 ist deshalb nach sechs
Gaesten fail-closed gestoppt, kein Vollgroessen-/Paketabschluss. In-scope
Korrektur/rote-gruene echte C-Regression und ein neuer begrenzter Abnahmelauf
folgen unter bestehender Fortsetzungsautoritaet. Bisher drei Builds/17 Gaeste,
keine Altbelege fuer korrigiertes Image umetikettiert; [Arbeitsstand](CURRENT_WORK.md).

Fortsetzung20.09.2026: Nutzer genehmigt die unten beschriebene eng begrenzte
Diagnose-Erweiterung. Kandidat10 bereitet BA-only CPU-Sequenz262144 (alter Pfad
2048, Ring256 unveraendert), verlustfreien begrenzten Host-Belegtransport und
genau ein neues gemeinsames Image vor. Kein CPU-/ATA-/IPC-/Gastfristwechsel,
keine Abnahme aus alten Normalbelegen fuer das neue Image. Vollstaendige
neun Gates und12+18 Gaeste bleiben erforderlich; aktueller Fortschritt im
[Arbeitsstand](CURRENT_WORK.md), noch kein BA-/OS-Abschluss.

20.09.2026: R8.3ba unter Vertragscommit `ccd6ff46` bleibt aktiv/unabgenommen.
Kandidat09 besteht Gates1..5 und sechs vollstaendige Normalfaelle: FAT12/FAT32,
EXT2-1/2/4KiB und8GiB RAM. Historische Selektorprojektionen sind nach expliziter
Zwei-Dateien-Freigabe korrigiert; alte Hostmanifestliste ebenfalls gruen.
Der volle512KiB-Gast stoppt nach192.966s an128MiB Textprotokoll, nicht an einer
nachgewiesenen Kernel-Fristverletzung. Nachfolgende Fehler-/Recovery-/Altgaeste
und Gates7..9 nicht ausgefuehrt. Zwei Builds insgesamt (seit Kandidat03 exakt
wiederverwendet), elf physische Gaeste1158.313992799900s; alle Fehler erhalten.
Stop-SHA `ba4a78d0242f865e6218f99dad57edf70ed7e854b23ea527c668e2cc2aab8504`.
Offline-Diagnose zeigt verlustfreie Komprimierbarkeit und bereits1456 von2048
CPU-Diagnosesaetzen im unvollstaendigen ersten Root. Die separate CPU-Quote
bleibt32/1000ms; Trace-Ueberlauf ist noch kein beobachteter Gastfehler.
Vorgeschlagene begrenzte Umfangsfreigabe fuer `arch/x86_64/proc/cpu_trace.inc`,
BA-only Diagnosekapazitaet, verlustfreien begrenzten Belegtransport und genau
ein neues BA-Image steht aus. Keine solche Aenderung/Neuausfuehrung erfolgt.
[Aktueller Befund, Grenzen und konkrete Freigabe](CURRENT_WORK.md).
Keine BA-/Gesamt-OS-Abnahme; sichtbare Kandidatenaenderungen bleiben erhalten.
Die nachstehende fehlende Profilfreigabe ist historische Bestandsaufnahme vor BA.

Aktuell nach sauberem AZ-Abschluss `5db38510` am20.09.2026: acht Gates und
volle Zehnfallmatrix abgenommen, finaler Beleg SHA256
`f38a35397b14d6073e5c99f289ab6d7ede550fd55348b6b3e1705731b169b79f`.
Die naechste Bestandsaufnahme ist erfolgt, ohne Build oder Gast: normaler
Dateistart bleibt auf1536 Byte/FS8/Block16 und gemeinsame1000ms Shellfrist
begrenzt; die reale eingebettete Shell hat163160 Byte, das externe Testprogramm
728 Byte. Der vorhandene ELF-Adapter allein hebt diese Dienstgrenzen nicht auf.
Ein eigener versionierter Nur-Lese-/Dateistartprofil-Vertrag bis zum bestehenden
512KiB-ELF-Eingabelimit muss feste Capture-/Cache-/Anfragen-/Leseraten-/
Gesamtdateibudgets definieren. Dafuer ist eine echte neue Ressourcen-/
Lebensdauerfreigabe erforderlich, nicht ein routinemaessiges Weiter-Signal.
Alte Profile und CPU-/ATA-/einzelne IPC-/Erstellungs-/Restartgrenzen sowie
Geraeterechte bleiben unveraendert. Kein nachtraegliches Frist-/Zaehlererneuern.
Noch kein Folgepaket aktiviert oder Ausfuehrungsfenster reserviert;
[Befund und genaue Grenze](CURRENT_WORK.md). R3.6b bleibt vertagt.
Die nachfolgenden AZ-Fenster sind historische Nachweise, keine offenen Gates.

R8.3az qualifiziert: acht Gates/20 Hosts, vollstaendige Zehnfall-BIOS-Matrix
und unabhaengige Rohdaten-/Scopepruefung bestehen. Vier frische Gaeste
80.15325149998534s plus sechs exakt gebundene Altbelege, keine Neubauten;
313.5655415999354s Fallmatrix. HDD-/Floppy-Boot bis normale Ring3-Shell und
Recovery sowie alle Korruptionsablehnungen belegt, unveraenderte Kernelgrenzen.
Siegel `build/codex-agent/r83az-shell-boot-media/candidate10/acceptance-seal.json`
SHA256 `d252b4215feb18d317992531691a91f06a384dd2345854ae97465178ca56966d`.
Sauberer lokaler Paketcommit ist die Abschlussgrenze; danach naechste native
Bestandsaufnahme ohne Routine-Handoff. Noch kein allgemeines Dateisystem-/
Desktop-/Browser-/Plattform- oder Gesamt-OS-Abschluss; R3.6b bleibt vertagt.
Alle frueheren Fehlfenster bleiben nachfolgend als Historie erhalten.

Kandidat10: Nutzerfreigabe fuer HDD-Doppel-SHA30s gesamt/27s Beobachtung/3s
Cleanup umgesetzt. Vier verbleibende neue Negativgaeste90s, sechs vollstaendig
quelltext-/werkzeug-/image-/rohdatengenau gebundene Altbelege mit unabhaengiger
Vollauswertung, acht Gates/Matrix455s/Gate600s, null Builds. Alle sonstigen
Fristen/Assertions bleiben; erster Fehler stoppt. Noch kein AZ-/OS-Abschluss.

Aktuell Kandidat09 gestoppt: HDD-Doppelsignatur besteht jetzt; Doppel-SHA
scheitert an unvollstaendiger zweiter Ablehnung im alten17s-Beobachtungsfenster.
Kein Kerneleintritt, keine nachfolgenden Gaeste/Gates. Sechs Fallidentitaeten
belegt, nicht volle AZ-/OS-Abnahme.18 physische Gaeste562.2795722998272s,
ein Medienpaar/null Kernelbauten und Vorstart2.088810800021747s separat erhalten.
Offene echte Freigabe: auch HDD-Doppel-SHA30s gesamt,27s Beobachtung/3s Cleanup;
sonst unveraenderte Grenzen/Assertions. Sechs Belege exakt wiederverwenden und
voll auswerten, vier neue Negativfaelle90s/Matrix455s/Gate600s, null Builds.
Vorschlag ist nicht umgesetzt oder freigegeben. Historie folgt.

Kandidat09: Erneutes `ja mach weiter` gibt nur den HDD-Doppelsignatur-Negativfall
mit30s Gesamtzeit frei (27s Beobachtung/3s Cleanup). Sonstige Fristen und alle
Assertions bleiben. Fuenf neue Negativgaeste110s, fuenf exakt gebundene positive
Altbelege mit unabhaengiger Vollauswertung, acht Gates/Matrix445s/Gate600s,
null Builds, erster Fehler stoppt. Keine AZ-/OS-Abnahme aus Teilbelegen.

Aktuell Stop Kandidat08: alle fuenf positiven BIOS-/Shell-/Recoveryfaelle sind
quellen-/werkzeug-/image-/rohdatengenau erhalten. Im HDD-Doppelsignatur-Negativfall
fehlt nach17s Beobachtung die zweite Ablehnung; Gesamt17.718055600009393s,
kein Kerneleintritt und kein weiterer Gast. Vier Gates/18 Hosts bestanden,
vollstaendige Abnahme weiterhin offen.16 Gaeste516.6674756998837s/ein Medienpaar/
null Kernelbauten plus separater Vorstart2.088810800021747s erhalten.
Echte offene Grenze: nur diesen Negativfall30s statt20s gesamt (27s Beobachtung,
3s Cleanup), Negativmatrix110s/volle Matrix445s/Gate600s; unveraenderte sonstige
Fristen/Assertions, null Builds. Vorschlag nicht umgesetzt oder freigegeben.

Kandidat08 schliesst nur den leeren seriellen Vorstart im Negativadapter;
finale Nichtleerpruefung und alle Ablehnungs-/Kapazitaetsgrenzen bleiben.
Alle fuenf Positivfaelle aus Kandidat07 bestehen und werden quelltext-/werkzeug-/
image-/rohdatengenau wiederverwendet sowie vollstaendig unabhaengig ausgewertet.
Keine Neubauten, acht Gates und maximal fuenf neue20s-Negativgaeste, erster
Fehler stoppt. Vollstaendige Zehnfallmatrix bleibt Voraussetzung. Historisch
15 Gaeste498.94942009987426s/ein Medienpaar/null Kernelbauten plus Vorstart
2.088810800021747s erhalten; keine AZ-/OS-Abnahme aus Teilbelegen.

Kandidat07 setzt die ausdruecklich freigegebene A-nach-B-Ausnahme um:30s
BIOS/Setup +42s alte Laufzeit +3s Cleanup,75s insgesamt; sonst65s positiv/20s
negativ, zehn Faelle435s/Gate600s. Rueckfall zuerst, acht Gates einmal, erster
Fehler stoppt. Kein neuer Build, keine Kernel-/Operations-/Assertionsaenderung.
Vorherige neun Gaeste290.54732029986917s/ein Medienpaar/null Kernelbauten und
Vorstart2.088810800021747s bleiben erhalten. Noch keine AZ-/OS-Abnahme.

Aktuell Kandidat06 angehalten: Langfall/normal/8GiB bestehen jetzt komplette
BIOS-/Shell-Rohdatenpruefung. A-nach-B erreicht waehrend zweiter Signaturpruefung
die freigegebene20s-BIOS-/Setupgrenze. Keine spaeteren Faelle/Gates, kein Commit.
9 Gaeste290.54732029986917s/ein Medienpaar/null Kernelbauten bleiben erhalten,
plus separater Vorstart2.088810800021747s. Nur vorgeschlagen: fuer A-nach-B30s
BIOS/Setup, sonst unveraendert42s Laufzeit/3s Cleanup, Gesamt75s/Matrix435s.
Keine Erlaubnis zur Umsetzung oder weiteren Ausfuehrung dieser Aenderung.
Die drei Erfolge sind keine volle AZ-/OS-Abnahme. Historie folgt.

Kandidat06: quittierter echter Kerneleintritt statt unzulaessigem Vergleich
absoluter GDB-/Hostzeit. Beide Phasen nur auf der Eltern-QPC-Uhr; GDB wartet
begrenzt am ersten Kernelbefehl auf die SHA-gebundene Quittung. Kein Zeitausgleich,
kein neuer Build und keine weitere Fristaenderung. Kandidat05 und seine
9.367075299960561s bleiben erhalten:5 physische Gaeste156.73826279994682s,
ein Medienpaar/null Kernelbauten plus Vorstart2.088810800021747s separat.

Aktuell freigegeben durch `ja mach weiter`: ausschliesslich die zuletzt
erfragte BIOS-Hostkomposition20s Setup/BIOS +42s alte Laufzeit +3s Cleanup.
Kandidat05 behaelt alle zehn Faelle, jetzt425s gesamt/65s positiv; Negativ20s
und Gate600s unveraendert. Kein Kernel-/Operationslimit aendern, keine neuen
Builds. Echte atomar belegte erste Kernelinstruktion bindet den Phasenwechsel;
kein laufender Zaehler wird zurueckgesetzt. Acht Gates einmal, Stopp beim
ersten Fehler. Noch keine AZ-/OS-Abnahme. Folgende Stopps sind Historie.

Aktuell angehalten nach AZ-Kandidat04: BIOS kostet gemessen8.218s vor der
ersten Kernelinstruktion, Langfall scheitert erneut am unveraenderten42s-
Beobachterlimit. Kalte Haltepunkte reichen nicht; keine AZ-Abnahme/Commit.
4 physische Gaeste147.37118749998626s/ein Medienpaar/null Kernel-Neubauten und
ein Vorstart2.088810800021747s bleiben getrennt dokumentiert. Echtes offenes
Freigabethema: ausschliesslich fuer die neue BIOS-Komposition20s Boot/Setup
plus alte42s Laufzeit/3s Cleanup (65s positive Gaeste,425s Zehnfallmatrix),
600s-Gate/20s-Negativfaelle und alle Kernel-/Operationsgrenzen unveraendert.
Vorschlag, keine Erlaubnis; vorhandene Medien wiederverwenden, keine Neubauten.
Erst nach ausdruecklicher Richtung neues endliches Fenster einfrieren.

AZ-Kandidat04 korrigiert ausschliesslich die physische Eintrittsadressbindung
nach Kandidat03-Vorstartabweisung: ELF32-Header/Rohsymbol0x101000 gegen den
bisherigen Higher-Half-Beobachter0xffffffff80101000. Kein weiterer VM-Start im
Fehlfenster;2.088810800021747s Vorstart separat erhalten. Alte Guards, acht Gates,
zehn Faelle und Fristen bleiben; bestehendes Medienpaar ohne Neubau verwenden.

AZ-Kandidat02 beweist BIOS bis normale Shell bei4/8GiB, scheitert jedoch am
Langlauf-Hostlimit42s. Kandidat03 prueft kalten BIOS-Eintritt mit nur einem
echten Hardwarehalt an der ersten Kernelinstruktion, danach unveraenderter
vollstaendiger AY-Beobachter. Keine erhoehten Grenzen oder Zielschreibzugriffe;
alle acht Gates/zehn Faelle bleiben, Langfall zuerst.3 Gaeste104.50407969998196s
und ein Medienbau erhalten; derselbe signierte Mediensatz wird ohne Neubau
wiederverwendet. Keine Fertigstellungsbehauptung aus den beiden positiven Faellen.

Folgetransaktion R8.3az auf sauberem AY-Abschluss `455fbb9d`: signierten
BIOS-Start und normale Shell gemeinsam integrieren, ohne den bestehenden
primaeren ATA-Lesevertrag zu erweitern. Eigenes Start-HDD als Slave oder
Rettungsfloppy, bestehendes unveraendertes EXT2-Systemmedium als Master;
Kernel/Shell/Dienste bleiben bytegleich. Ein neuer Medienbau, null Kernel-
Neubauten, acht eingefrorene Gates und maximal zehn Gaeste/325s. Details im
[Bootmedienvertrag](../architecture/NATIVE_SHELL_BOOT_MEDIA_CONTRACT.md).
Das schliesst die Bootintegration, nicht die noch offenen allgemeinen Datei-,
Schreib-, Desktop-, Browser- und Plattformgrenzen. Paket ist noch nicht abgenommen.
AZ-Kandidat01 stoppt vor Medienbau/Gast an einem ANSI/UTF8-Fehler des neuen
Defaultvergleichs. Alte Make-Konfiguration ist bei korrekter Kodierung exakt
gleich. Kandidat02 ist eine reine Prueferkorrektur mit Regression, unveraendertem
achtteiligen Gateplan und erhaltenem Fehlbeleg; bisher null neue Medien/Gaeste.

R8.3ay-Abnahme bestanden am20.09.2026: zehn Gates/18 frische Gastfaelle,
370.020897600014s, kompletter Rohdaten- und unabhaengiger Speicher-Replay.
Normale Ring3-Shell mit echtem lesendem Dateisystem/Dateistart, Identitaet,
Terminaldelegation/Wait und begrenzter generationengebundener Dienst-Recovery
ist damit qualifiziert. Langer Fall, fuenf Medien,8GiB, Dienst-/App-Ausfaelle,
Erschoepfung, Eigentuemer-Verlust und OOM-Rollback bestanden. Vorhandenes
siebentes Image, keine neuen Qualifikations-Builds oder gelockerten Grenzen.
141 physische Gaeste2862.51474020019s/sieben Images plus0.38712120000855066s
Vorstart samt allen Fehlversuchen erhalten. Abnahmesiegel Candidate17:
`08cc05c7442b00644aab4d9a61fa09a84409669e63f74221a6a8bbf6f611701a`.
Gesamte64-Bit-OS-/Hardware-Abnahme bleibt offen; R3.6b bleibt zurueckgestellt.
Naechstes natives Paket erst nach lokalem sauberen Abschluss inventarisieren.
Nachfolgende Fenster sind historische Nachweise, nicht der aktuelle Status.

Candidate17 folgt vollstaendig bestandenem langen Fall6 (Diagnostic38,
36.573199900012696s/2437 echte RET-Zieltreffer). Nur normalen GDB-Einfuegemodus
und Host-Erwartung aendern, alle alten Guards bleiben. Zehn Gates/18 frische
45s-Gaeste inkl3s Cleanup/810s Summe/900s Runtime, erster Fehler stoppt, kein
Build/Toolwechsel.123 Gaeste2492.493842600176s/sieben Images plus0.3871212s
Vorstart erhalten; Diagnose ist keine Abnahme oder Fertigstellung.

Candidate16: sechs Gates/sechs Gastfaelle bestanden. Langer Fall6 erreicht
Beobachtungsgrenze42s (44.178s inkl Cleanup),2429 korrekte RET-Zieltreffer,
Debugger25.906s CPU.122 Gaeste2455.920642700163s/sieben Images plus0.3871212s
Vorstart erhalten. Diagnostic38 prueft allein persistente GDB-Haltepunkte
(always-inserted on) unter allen bestehenden echten RET-Fortschrittsguards.
Host red/green300s, ein Fall6-Gast45s inkl3s Cleanup/90s Host, kein Neubau,
keine Frist-/Quotenlockerung oder Abnahmewertung.

Candidate16: Diagnostic37 besteht2/13/15 mit allen alten Rohdatenpruefungen
und962/821/751 echten RET-Zieltreffern,66.83003739998094s. Nur den unveraendert
geprueften Wrapper in normalen Beobachter uebernehmen, kein Build/Toolwechsel.
Zehn Gates/18 frische45s-Faelle inkl3s Cleanup/810s Summe/900s Runtime, erster
Fehler stoppt.115 Gaeste2273.6467948001523s/sieben Images plus0.38712120000855066s
Vorstart erhalten. Diagnoseerfolg ist noch keine Abnahme/Commit/OS-Fertigstellung.

Diagnostic36 scheitert vor Shellstart an Scheduler-Stufe159 (2.830s); QEMU
filtert globale TB-Link-Zeilen nicht. Kein Ursachenbeweis.112 Gaeste
2206.8167574001714s/sieben Images plus0.38712120000855066s Vorstart erhalten.
Diagnostic37: echte RET-Ausfuehrung durch genau einen Hardwarehaltepunkt am
gespeicherten Ruecksprungziel pruefen, einmal continue statt stepi, exakter
Treffer/PC/SP/Registererhalt und finally-Cleanup. Alle alten Guards bleiben,
normaler Beobachter unveraendert/kein Trace. Host red/green300s, maximal drei
Faelle2/13/15 je45s inkl3s Cleanup/135s Summe/240s Host, erster Fehler stoppt,
kein Build/Toolwechsel/Abnahmeersatz.

Candidate15 gescheitert: sechs Gates/zwei Gaeste bestanden, Fall2 meldet
Einzelschritt ohne PC-Fortschritt13.951s.111 Gaeste2203.9868998001916s/sieben
Images plus0.38712120000855066s Vorstart bleiben erhalten. Diagnostic36:
QEMU-Ausfuehrungslog nur fuer drei RET-Adressen, zwei GDB-Ereignisse, gleicher
8MiB/131072-Zeilen-Puffer. Host red/green300s, maximal Faelle2/13/15 je45s inkl
3s Cleanup/135s Summe/240s Host, erster Fehler stoppt, kein Build/Toolwechsel.
Der passende Upstream-QEMU-Code ist bisher Hypothese, keine bewiesene Ursache
der installierten Binaerdatei. Keine Guardlockerung oder Abnahmebehauptung.

Candidate15 qualifiziert den belegten expliziten RET-Transport: Diagnostic35
Fall13 besteht21.838s/822 Schritte. Kompakte Rohbelege und Abschlusszaehler
halten8MiB unveraendert; Register-/Syscall-Guards bleiben. Zehn Gates/18 neue
45s-Gaeste inkl3s Cleanup/810s Summe/900s Runtime, kein Build.108 physische
Gaeste2146.2288713001476s/sieben Images plus0.3871212s Vorstart erhalten.

Diagnostic35 korrigiert lokale Adapterreihenfolge, nicht den gemeinsamen
Speicherpruefer: Schleife erst nach Reader-Konfiguration.34 war vor Gaststart
abgewiesen.107 Gaeste2124.3906322001426s/sieben Images plus0.3871212s Vorstart
erhalten. Echter Integrationshosttest red/green, ein45s-Gast inkl3s Cleanup/
90s Host, kein Build; unveraenderte Step-/Syscall-Guards und keine Abnahmewertung.

Diagnostic34: aeussere begrenzte Fortsetzungssteuerung nach bewiesenem RET;
Diagnostic33 endete nach erstem erfolgreichen Schritt durch GDB-Batchsemantik.
107 Gaeste2124.3906322001426s/sieben Images erhalten. Genau ein neuer Fall13-
Diagnosegast45s inkl3s Cleanup/90s Host nach Host red/green, kein Build.
Schritt-/Syscall-Guards unveraendert, kein fehlender Return wird ergaenzt.

Candidate14: sechs Gates/13 Gaeste bestanden, Fall13 erneut Pending-Guard;
106 Gaeste2082.2285526001365s/sieben Images. Kein Commit/Abschluss, GDB-Standard-
modus ist keine bewiesene Reparatur. Diagnostic33: begrenzter echter RET-Step
mit geprueftem PC/SP/Registererhalt, unveraenderte Originalcallbacks/Guards.
Host red/green und ein45s-Gast inkl3s Cleanup/90s Host, kein Neubau/Abnahmeersatz.

Candidate14 qualifiziert den dokumentierten GDB-Standardmodus statt erzwungenem
always-inserted on. Diagnostic32/Root-Absturz besteht18.140s; kein Guard wird
gelockert. Zehn Gates/18 frische normale Gastbeweise, exaktes siebentes Image
ohne Neubau;45s inkl3s Cleanup/810s Summe/900s Runtimegate, erster Fehler stoppt.
92 Gaeste1798.9659774001343s/sieben Images erhalten; kein Abschluss aus Diagnose.

Diagnostic31 unterscheidet die Ursache: doppelte Debuggermeldung desselben
READ-Eintritts, Zaehler bleiben[14,13]. Kernelaufruf/Rueckkehr nicht wiederholt.
Fall5 bestanden, Fall15 gestoppt;91 Gaeste1780.8258845001405s/sieben Images.
Diagnostic32 isoliert dokumentiertes GDB always-inserted off (nur Diagnose),
ein Hosttest red/green, ein45s-Gast inkl3s Cleanup/90s Host, kein neuer Build.
Keine Guards lockern, keine Deduplizierung oder Abnahmewertung.

Diagnostic30 besteht mit unabhaengigen Zaehlern, reproduziert den Fehler aber
nicht. Vier Hosts1.165s/Build10.130s/Gast19.019s;89 Gaeste1751.6440516001317s/
sieben Images insgesamt. Diagnostic31: dasselbe Image, andere Faelle5/15/16/17,
unveraenderte Diagnose/Guards, erster Fehler stoppt. Kein Build/Hosttestduplikat,
vier45s Gaeste inkl.3s Cleanup/180s Summe/270s Host, keine Abnahme oder Reparaturbehauptung.

Diagnostic30: zwei begrenzte private Kernel-Zaehler sollen echte READ-Aufrufe
von mehrfachen Debuggermeldungen unterscheiden. Keine Laufzeit-/Rechtekorrektur,
alte Guards bleiben. Hosttest, ein Image, ein45s-Gast inkl.3s Cleanup/90s Host;
88 bisherige Gaeste1732.6248232001385s/sechs Images, keine Abnahmewertung.

Neuester Stand20.September: OOM-Testlastkorrektur inklusive blockierter Pause,
Rollback und spaeterem Appstart bewiesen. Ein gemeinsamer Neubau, danach
Candidate13 sechs Gates/drei Gastfaelle bestanden, vierter Gast am alten
Pending15-Guard gestoppt. Diagnostic29 reproduziert den Guard12.485s und
schliesst falsche Identitaet/deaktivierten Return-Haltepunkt aus; wiederholtes
Request-Ereignis versus fehlender Return bleibt offen.88 Gaeste1732.6248232001385s/
sechs Images insgesamt. Kein Commit/Abschluss oder weiteres reserviertes
Ausfuehrungsfenster bei dieser Beweisluecke; keine unveraenderte Abnahmewiederholung.

Candidate13: Gates1..6 und Faelle0..2 bestanden, Fall3 am alten Pending15-
Beobachterguard gestoppt, Rest nicht gestartet.87 Gaeste1720.1397847001503s/
sechs Images erhalten. Diagnostic29: nur im Fehlerfall frischer Zustand,
kein gesunder Zusatzpfad/Breakpoint/Tracing; ein Hosttest und ein45s-Gast,
kein Build, keine Abnahme oder behauptete Behebung des sporadischen Fehlers.

Correction28 schliesst OOM-Testlastkonflikt mit echter Gastpruefung18.085s und
vier Hostmethoden; sechstes gemeinsames Image gebaut10.681s. Candidate13 nimmt
jetzt alle zehn Gates/18Faelle ohne Neubau ab, unveraenderte45s/3s-Cleanup/
810s-Gastsummen-/900s-Gate-Grenzen, Stopp beim ersten Fehler.83 verbrauchte
Gaeste1648.5452671001553s/sechs Images. Alte sporadische Pending-Luecke bleibt
historischer offener Ursachenbefund, kein Guard oder alter Oracle abgeschwaecht.

Correction28 korrigiert zwei neue Hosttest-Annahmen nach27 (keine Builds/Gaeste):
unpublizierte Dienstfrist und16-Byte-Testarray-Ausrichtung. OOM-Testlast/
Kernel-Prueffilter unveraendert, weiterhin ein Build/ein45s-Gast, alle Belege erhalten.

Correction27 uebernimmt26 nach dessen abgelehntem Freeze (laufendes Log war
irrtuemlich eigener gebundener Eingang); keine Builds/Gaeste verbraucht,
Korrektur/Grenzen unveraendert, historischer Fehlbeleg bleibt erhalten.

Correction26: konkreter OOM-Testlastkonflikt aus Diagnostic25; drei Frames
korrekt zurueckgegeben, aber Treiber vor zweitem Konsolen-Ablehnungstest
beendet. Nur Fall17/zweiter Aufbau wartet vor FS-Erzeugung100ms blockierend;
keine Frist-/Quotenerhoehung. Eine Hostregression, ein gemeinsamer Build,
ein45s-Gast inkl.3s Cleanup/90s Host; alle Assertions plus Pausennachweis.
82 bisherige Gaeste1630.46060670013s/fuenf Images bleiben erhalten. Kein
Abnahmeersatz; sporadischer Pending-Beobachterfehler weiterhin offen.
Pausenbeleg erfordert ausschliesslich den privaten Prueffilter fuer Root0/
SLEEP100ms zu erweitern; keine Schlaf-/Schedulersemantik oder Pollingtraces.
Assemblerregression vor Neubau, weiterhin genau ein Image/ein Gast.

Diagnostic24: erneuter Root-Quotenfehler vor Audit-Aktivierung. Diagnostic25
isoliert die zusaetzliche QEMU-Ereignisspur durch normalen Capture, unveraendertem
spaetem Beobachter/Oracle und exakt gleichem Image. OOM17 dann Normal0 einmalig,
max2x45s inkl.3s Cleanup/180s Host, kein Build oder Abnahmewertung.81 bisherige
Gaeste1610.6604701001493s/fuenf Images erhalten; Ursache weiter offen.

Diagnostic23: Root-CPU-Quotenfehler im ersten Normalgast, vier andere Gaeste
nicht gestartet. Diagnostic24 verlagert auch Registerdiagnostik an die spate
History-Grenze; vorher keinerlei zusaetzliche Audit-Gastzugriffe. Original-
Callbacks/Quoten unveraendert, Hosttest besteht. Ein45s-Fall0, keine Builds
oder Abnahme.80 Gaeste1597.2762906001594s/fuenf Images historisch erhalten.

Diagnostic22 besteht23.383s mit16 unabhaengigen Root-Pending-Uebergaengen.
Diagnostic23: einmaliger begrenzter Ursachenlauf ueber andere Faelle0,6,15,16,17,
kein neuer Build/Produktionsfix, Beobachter/Pruefungen exakt wie22. Erster Fehler
stoppt,5x45s inkl.3s Cleanup/225s Summe/300s Host; keine Abnahmewertung.
79 historische Gaeste1585.8946213001622s/fuenf Images erhalten.

Diagnostic21 durch3390 Daten-Stops zu invasiv; erster Gast scheitert am
App-Konstruktionsnachweis mit Service-CPU-Quotenfehlern, zweiter nicht gestartet.
Diagnostic22: nur Root0-Pending-Byte nach zweiter History-Ausgabe beobachten.
Hosttest erzwingt spaete/einmalige Aktivierung und Idle-Baseline; unveraenderte
Kernel-/Abnahmegrenzen. Ein45s-Diagnosegast, kein Build/Abnahmeersatz.
78 Gaeste1562.5116184001675s/fuenf Images bleiben verbraucht.

Diagnostic21: unabhaengiger Hardware-Schreibhaltepunkt auf bestehende Pending-
Bytes soll echte Kernelzustandsuebergaenge von Funktions-Stopmeldungen trennen.
Keine Kernelmutation oder Builds, unveraenderte Oracles. Maximal Fall5+15 als
Diagnosen,45s je inkl.3s Cleanup/90s Summe/180s Host, erster Fehler stoppt.
77 historische Gaeste1531.2117434001705s/fuenf Images bleiben erhalten.

Neuester Befund20.September: Diagnose19 (8GiB) und20 (Rootabsturz) bestehen
23.0155s/20.6698s, ohne Neubau. Vier gezielte Hostmethoden bestehen. Beide
Diagnosen sind KEINE Abnahme/Reparaturbestaetigung; sporadischer Pending-Guard
aus Candidate12 bleibt ursachenseitig offen.77 Gaeste1531.2117434001705s/
fuenf Images, kein weiterer Lauf reserviert, kein Commit oder AY-Abschluss.
Volle18-Faelle-Abnahme einschliesslich korrigiertem OOM-Messpunkt weiter offen.

Diagnostic19 besteht den8GiB-Fall in23.0154972s; sporadische Ursache weiterhin
offen. Diagnostic20 fuegt einmalig im bereits auffaelligen Rootabsturzfall15
QEMUs eigene Fortsetzungs-/Haltespur zum Registeraudit hinzu. Vorhandener
begrenzter8MiB-Sink,45s inklusive3s Cleanup,keine Neubauten/Abnahmewertung.
76 Gaeste1510.541908700194s/fuenf Images historisch erhalten.

20.September: Diagnostic19 reserviert einen read-only Ereignisdiagnosegast
Fall5/8GiB auf dem vorhandenen fuenften Image, keinen Build. Letzte16 Stops mit
Register-/Task-/Syscall-/Pending-Zustand und GDB-Trefferzaehlern, begrenztes
spaetes infrun-Log; unveraenderte45s/3s Cleanup/8MiB. Originalpruefungen bleiben,
keine Abnahme oder automatische Wiederholung.75 Gaeste1487.5264115001776s
bleiben historisch verbraucht; vorheriger Reservierungsstopp damit aufgehoben.

Aktuell blockiert: Candidate12 reproduziert die fehlende Syscall-Abschluss-
beobachtung auch mit reinem Befehlsdispatcher (Fall5/8GiB, Rootgen10/READ15).
Die Transporthypothese ist damit nicht bestaetigt; Rohdaten trennen doppelte
Stopmeldung und verlorene Rueckkehrmeldung noch nicht sicher. Kein weiteres
Ausfuehrungsfenster, Commit oder AY-Abschluss.75 Gaeste1487.5264115001776s/
fuenf Images verbraucht; gesamte18-Faelle-Abnahme und OOM-Gastnachweis offen.

Candidate12: einheitlicher Befehlsdispatcher fuer alle kalten Syscall-Probes,
keine Gastzugriffe mehr in der Stop-Entscheidung. Originalcallbacks/-assertions
und Image bleiben exakt. Hosttests bestehen; volle Abnahme ist noch notwendig,
Diagnostic18s einzelner Erfolg wird nicht hochgestuft. Null Builds/18 Gaeste,
69 historische Gaeste1347.4950213001287s/fuenf Images bleiben erhalten.

Diagnostic18 erfasst ausschliesslich vorhandene Aufrufidentitaeten im Fehler-
text des durch17 lokalisierten Pending-Guards. Ein45s-Gast, keine Neubauten,
keine Assertionsaenderung oder Abnahme;68 Gaeste1325.1971648001347s bisher.

Candidate11:15 Laufzeitfaelle bestanden, Dauersitzung auf32.384s reduziert.
Diagnostic17 lokalisiert ausschliesslich eine weitere statische Beobachter-
Assertion aus Fall15, mit begrenztem Fehlerkontext und einem45s-Gast am
unveraenderten Image.67 bisherige Gaeste1307.0037873001422s/fuenf Images.
Keine abgeschlossene AY-Abnahme oder behauptete OS-Fertigstellung.

Candidate11 korrigiert nur quadratisches wiederholtes Host-Feeder-Decodieren
nach Candidate10s42s-Aufzeichnungsstopp im Dauersitzungsfall. Beide Roots enden
regulaer, der Abschlussbeleg bleibt dennoch unvollstaendig. Inkrementelles
Lesen mit identischen Pruefentscheidungen fuer17 erhaltene erfolgreiche Faelle
und unveraenderten kumulativen Grenzen; kein Kernel-/Image-/Fristwechsel.
Alle zehn Gates/18 frischen Gaeste erneut, null Builds. Historisch51 Gaeste,
979.5447680000507s/fuenf Images; kein Abschluss aus Teilbelegen.

Candidate09 besteht sechs Gates und17/18 Laufzeitfaelle. Der letzte OOM-Test
misst die Rollback-Baseline vor der regulaeren ELF-Cache-Freigabe. Candidate10
bindet ausschliesslich diesen Beobachter-Messpunkt an die bestehende Kernel-
Transaktionsgrenze; keine Produktionsaenderung oder gelockerte Bilanzpruefung.
Zehn Gates mit exakter Image-Wiederverwendung,18 frische Gaeste, null Neubauten;
44 bisherige Gaeste797.1512432000309s/fuenf Images bleiben dokumentiert.

Candidate09 korrigiert die veraltete Host-Inventarzahl nach der ext2-Aufnahme
auf exakt acht Pfade. Candidate08 stoppte vor Build/Gast; Parser und gesamte
Laufzeitabnahme bleiben unveraendert, historische Verbraeuche bleiben erhalten.

Die explizite Nutzerfreigabe erweitert AY um ext2-Parser und zwei Hosttests.
Candidate08: sektorweises opt-in Verzeichnislesen bei unveraenderten Sicherheits-
grenzen, alte Profile exakt; ein gemeinsamer Build nach Hostregressionen,
vollstaendige18-Faelle-Matrix weiterhin Pflicht. Kein Abschluss aus Teilbelegen.

Aktuell: Candidate07, sechs Gates und drei vollstaendige Medienfaelle bestanden.
Naechster echter Blocker ist ext2-2KiB-Verzeichnis-I/O: gemeinsamer Parser liest
vor Namensvergleich den ganzen Block; erster Dateisektor passt danach nicht
mehr in die unveraenderte1000ms-Frist bei100ms Blockabstand. Parser/zugehoerige
Hosttests sind nicht im Paketumfang. Vor gezielter sektorweiser Verzeichnis-
abfrage ist deren explizite Aufnahme erforderlich. Keine weiteren Builds/Gaeste
reserviert;26 Gaeste392.6945861999993s/vier Images verbraucht, keine OS-Abnahme.

Candidate06: Host-Stopp vor jedem Build/Gast wegen alter Terminal-Eintrittsfolge.
Candidate07 versetzt nur die neue Meldestelle hinter die bestehenden Hooks;
keine Altpruefung geaendert, dieselbe noch ungenutzte Build-/Gastreservierung.

Diagnostic16: beide unveraenderten ext2-Sitzungen ohne laufenden Debugger
erfolgreich. Candidate06 verlegt zwei uebrige Lebenszyklus-Signale auf die
bestehende private kalte Seite; ein gemeinsamer Neubau, keine Lockerung von
Fristen, Quoten oder Rohdatenpruefung. Alle18 Faelle bleiben erforderlich.
Verbraucht22 Gaeste322.3623714999703s/drei Images. Kein Abschluss/Commit.

Candidate05 stoppt nach sechs bestandenen Gates und zwei vollstaendigen
Medienfaellen an Layout2: gemeinsamer STAT/Datei-Timeout beim dritten READ,
kein CPU-Quotenfehler. Ein Layout2-Kontrollgast ohne laufende Debuggerstopps
wird vor jeder Korrektur eingefroren; unveraendertes Image, keine neuen Builds.
21 Gaeste312.56778849996044s/drei Images bleiben verbraucht, Paket weiter offen.

Candidate05: Vollstaendiger Offline-Rohdatennachweis fuer Diagnostic15 besteht;
verbliebene PIO-/IPC-Seitenhaltepunkte entfernt/enger gebunden und fehlender
PIO-End-Ereignistyp im Dispatcher ergaenzt. Keine Quoten-/Uhr-/Kernel-Aenderung.
Alle zehn Abnahmeobligationen und18 frische Gaeste folgen, kein neuer Build;
vorhandenes drittes Image wird an unveraenderte Produktionsquellen gebunden.
18 Gaeste260.68762609994155s/drei Builds verbraucht. Paket bleibt aktiv.

Aktueller Nachweis: Diagnostic14, erstes Layout0, alle sechs normalen Befehle,
Dateiprogramm Exit82 und Root Exit0/12 CPU-Ticks ohne laufende Debuggerstopps.
Die Vollbeobachtung erschoepft dagegen Root CPU32/Tick88. Keine OS-Abnahme:
Kontrolllauf endet am zweiten, unpassenden Standardlayout2 auf Layout0-Medium.
17 Gaeste243.48874109995086s/drei Images verbraucht, kein weiterer Gast/Build
reserviert. Feeder und Dispatcherbindung host-getestet; alle18 vollstaendigen
Rohdatennachweise bleiben erforderlich. Kein Commit/Abschluss aus Teilbelegen.

Diagnostic11 findet nach Feederkorrektur Root-CPU32 bei Tick88. Diagnostic12
prueft ausschliesslich schnelleren Host-Beobachtungstransport am gleichen Image;
keine Quoten-/Frist-/Eingabeplan-Aenderung. Vier gezielte Hosttests bestanden.
14 Gaeste188.78968269994948s verbraucht; genau ein45s Gast, kein Neubau reserviert.

Candidate04 Gates1..6 bestanden; echter Dateistart SESSION64/Exit82 belegt.
Runtime bleibt offen: Feeder muss nach jeder Befehlszeile den neuen Root-Prompt
abwarten, da Terminaltransfer vorzeitig gesendete RX-Zeichen korrekt verwirft.
Diagnostic11: Hostregression und ein45s Gast am dritten Image, kein Neubau.
13 verbrauchte Gaeste176.52862759996788s; keine Fertigstellungsbehauptung.

Candidate04: fehlende kalte Lebenszyklushooks und CRLF-Feederbindung korrigiert.
Initialmount und Root-Cleanup nun voll beobachtet, Dateistart unter1470 PIO-
Stopps noch CPU32. Neuer privater fester PIO-Ring behaelt alle bisherigen
Anfrage-/Antwort-/Zustandsbytes und ergaenzt Sequenz/IF/Overflow/Cleanup-Proof;
echter Assembler O0/O2 und Hostdecoder bestehen. Ein neuer gemeinsamer Build
mit allen zehn Gates/18 frischen Gaesten eingefroren; keine Quotenlockerung.
Historie zwoelf Gaeste134.17087289996562s/zwei Images bleibt erhalten.

Aktuell: candidate03 besteht Gates1..6/268 Hostmethoden mit zweitem Image
cb61ac05; die18-Faelle-Laufzeitabnahme ist nicht bestanden. Falsche GDB-
Zuordnung benachbarter RET-Proben behoben, CPU-Abbruch mit vollem Beobachter
bleibt. Diagnostic07 zeigt am identischen Image/layout0 einen gesunden
Shell-Initialmount ohne Dauerstopps, Treiber3/FS1 CPU-Ticks. Diagnostic08 mit
gebuendelten Lesezugriffen scheitert weiterhin am CPU32-Limit. Zehn Versuche
84.11793239996769s/zwei Images sind erhalten; keine weiteren Gaeste/Builds
reserviert. Eine getrennte Hostregression belegt und korrigiert fremde
Bootstrap-Bereinigungsereignisse im AY-Beobachter durch den fehlenden Modus8-
Guard. Ein stoppaermerer vollstaendiger Rohdatenpfad bleibt erforderlich.
Kein OS-Abschluss; keine Quoten-/Fristaenderung oder Teilabnahme/Commit.

Naechster aktiver Schnitt19.September: R8.3ay integriert normale Shell und
generationengebundene, endliche Dienstsitzungen unter einem ausdruecklichen
persistenten Rootprofil. Namespace/Dateistart/Identitaet/Terminal/Wait und
Recovery werden gemeinsam qualifiziert; ein Image fuer18 Gastfaelle.
[Eingefrorener Vertrag](../architecture/NATIVE_SHELL_SESSION_CONTRACT.md).

AY-Implementierung im Worktree: echte Shell-/Dateistart-Anbindung, ABI114 und
Ring3-Sitzungsverwaltung sind angelegt. Sechzehn Entwicklungstestmethoden
gezielt geprueft, darunter sechzehn Shell-/Adapter-Szenarien mit O0/O2.
Fehlercode-/Spawnvalidierung, Make-Defaultreihenfolge und gemeinsame
STAT-/Erfassungsfrist korrigiert; rote und gruene Belege bleiben erhalten.
Integrierter Gastbeobachter/Rohdatenpruefer und Zehn-Gate-Ablauf sind angelegt;
IPC-, PIO-, Dateibyte-, Fehlerfolgen- und Gastfristpruefungen hostgeprueft.
Candidate01: Gates1..3 bestanden, Gate4 beim historischen Terminal-
Quellvergleich gestoppt (16/17 Terminaltests bestanden). Der Vergleich ist
nachweislich bereits mit den AX-Aenderungen der unveraenderten Baseline
unvereinbar. Die Aufnahme von scripts/verify_x86_64_terminal.py ist durch
das erneute Nutzer-Ja freigegeben. Candidate02 korrigiert nur die historische
Opt-in-Projektion mit Regressionen; Produktions- und Gastpruefquellen
bleiben unveraendert gebunden. Keine Testauslassung.
Stopped-Beleg5e791946b749d1c0; alle Logs und Quellen bleiben erhalten.
Candidate01 hatte keinen OS-Build/Gast. Candidate02 besteht inzwischen
Gates1..6 mit263 Hostmethoden und genau einem Image8535a0e5432ce38d.
Gate7 stoppt beim ersten Gast nach10.080940099986037s: reale CPU-Quoten-
Erschoepfung von ATA-Dienst und Shell, danach unvollstaendiger Eingabeplan.
Stopped-Beleg844dd1fbe9902794c; keine weiteren Gaeste, keine Paketabnahme
oder Implementierungscommit. Viele Beobachterstopps sind als moeglicher
Einfluss identifiziert, nicht als alleinige Ursache bewiesen. Vor weiterem
Gast ein separat gebundenes Diagnose-/Korrekturfenster am vorhandenen Image,
keine Quotenlockerung oder Abschwaechung der Rohdatennachweise.

Drei Diagnosen danach ohne Neubau: erst ohne laufende Haltepunkte erreicht
das Standardmedium den Shell-Prompt und7s Leerlauf ohne Root-Quotenabbruch.
Dies bleibt Diagnose, nicht Abnahme. Candidate03 korrigiert die zu fruehe
Beobachtung blockierter IPC-Antworten und trennt begrenzte No-op-Pruefpunkte
von normalen Kernel-Codepages; Quoten/SDK/Dienste unveraendert. Assembler
O0/O2 und sechs gezielte Methoden bestehen. Alle zehn Gates mit einem neuen
gemeinsamen Image/18 Gaesten bleiben Pflicht. Bisher vier Gastversuche,
38.65928809996694s und ein Image, alle Fehler erhalten.

19.September, nach AW: Nutzerfreigabe fuer ein separates dauerhaftes Shell-/
Supervisorprofil erteilt. R8.3ax ist qualifiziert, dessen Kernelgrenze versioniert und
generationsgebunden acht Konstruktionen pro Sekunde zulaesst, ohne alte Profile,
CPU-Quoten oder Operationsfristen zu aendern. Ring3-Recovery und normale Shell-
Komposition folgen; noch keine Dauerbetriebs- oder Gesamt-OS-Abnahme.
AX: neun Gates,146 Hostmethoden,17 Gastnachweise;40 Kind-Erzeugungen und44
Bereinigungen ueber zwei Laeufe. Letzte Prueferkorrektur ohne Neubau mit14
exakt gebundenen CPU-Wiederverwendungen und drei frischen Sitzungs-/Fatalgaesten.
Gesamthistorie drei Images/35 Versuche inklusive aller Fehler und Diagnosen.
Review-closure dfcc8ef8fec50cfb; [Vertrag](../architecture/NATIVE_SESSION_ADMISSION_CONTRACT.md).

Aktuell19.September: R8.3av ist alsf05fcc86 abgenommen (14 Gates,233 Hosttests,
27 Gastfaelle); generationsgebundene Vordergrund-Terminalweitergabe ist vorhanden.
R8.3aw ist alse70c454c ebenfalls vollstaendig qualifiziert: zehn Gates,41 Hostmethoden,
25 frische Gastfaelle und zwei exakt gebundene AV-Korruptionsnachweise.
Dateiabfrage und anschliessende ELF-Erfassung teilen im SDK nun eine absolute
Deadline und die unverlaengerte FS-Sitzung. Alter Fresh-Client-Einstieg bleibt
kompatibel. Ein fertiges Image, kein Kernel- oder Dienstumbau.
[Vertrag](../architecture/NATIVE_FILE_CAPTURE_CONTRACT.md). Danach bleibt die
normale Namespace-/Start-/Wait-Komposition offen, nicht eine weitere Terminal-
Autoritaetsfreigabe. Diese Schritte sind noch keine Gesamt-OS-Abnahme.
Die anschliessende Inventur unterscheidet eine weiterhin moegliche endliche
Integration von dauerhaftem Shell-Betrieb: dessen1000ms Gesamtfrist, die
acht FS-Anfragen/3000ms und acht CREATE-Versuche je Root-Generation duerfen
nicht stillschweigend erneuert werden. Ein ausdrueckliches neues dauerhaftes
Shell-/Supervisorprofil mit begrenzten Operationen und zeitfenstergebundenen
Zulassungs-/Neustartbudgets hat nun diese echte Lebensdauerfreigabe; alte
Profile bleiben erhalten. Details und offene Grenze: [CURRENT_WORK](CURRENT_WORK.md).

Neu vollstaendig qualifiziert: R8.3at [normaler nativer Shell-Port](../architecture/NATIVE_SHELL_CONTRACT.md).
Acht Gruppen,8+33+15 Hosttests und vier Gaeste bestanden. Echte normale Shell
bei4/8GiB, Befehle/History/Bearbeitung, Fehler und Timeout samt Ersatzgeneration
und vollstaendiger Bereinigung; keine neuen Kernelrechte. Gesamthistorie zwei
Images/sechs Gaeste29,9656697s, alle Fehler erhalten. Datei-/Prozessintegration,
Terminaluebergabe und normaler Systemstart bleiben offen; keine OS-Gesamtabnahme.

Vollstaendig qualifiziert nach sauberem AR-Commit `7d34f237`: R8.3as
[native Konsolenvermittlung](../architecture/NATIVE_CONSOLE_CONTRACT.md).
Der allgemeine native Prozesspfad vermittelt nun explizit berechtigtes,
nichtblockierendes READ/WRITE mit maximal64 Bytes; Wartepolitik bleibt Ring3.
Alle12 Verpflichtungen,15 Pakettests und sieben Gastfaelle bestanden,
einschliesslich4/8GiB, Fehlerabgrenzung und vollstaendiger Bereinigung.
Ein gemeinsames Image, kein Neubau fuer die Pruefadapterkorrekturen.
Normale Shell und gemeinsame Datei-/Konsolendienstintegration sind damit
vorbereitet, noch nicht umgesetzt. Keine neue Test-Shell als Ersatz.

R8.3aq ist mit sauberem Commit `c7e5e72a` abgeschlossen:15 Pruefgruppen,
18 Gastfaelle, ein neues gemeinsames Image, vollstaendige CPU-/PIO-Rohdaten.
Ebenfalls vollstaendig qualifiziert ist R8.3ar:
[gleichzeitige Datei-/Programmdienst-Lebensdauer](../architecture/NATIVE_LIVE_FILE_CONTRACT.md).
Dateisystem und Treiber bleiben beim Import und Lauf des Dateiprogramms aktiv;
alle Medien-/Fehlerfaelle nutzen ein Image. Alle14 Pruefgruppen und25 Faelle
bestanden,20/20 neue Pakettests. Letzte Runde ohne OS-Build: elf exakt gebundene
Gastbelege wiederverwendet,14 neue bestanden. Gesamtgeschichte ein Image,
28 Versuche452,3134651s. Vollstaendige Rohdatenpruefung und direkter Review
abgeschlossen; Belege unter r83ar-live-file/terminal-receipt.
Normale interaktive Shell-/Dateianbindung und vollstaendige64-Bit-Systemabnahme
bleiben offen. Kernelmechanismen bleiben unveraendert.

Vollstaendig qualifizierter gebündelter Arbeitsschritt R8.3ap:
[periodische CPU-Zulassung](../architecture/NATIVE_SERVICE_CPU_CONTRACT.md).
Die Umsetzung umfasst Zulassung, Zeitfenster, Delegation und Retirement samt
Host-/Gastnachweisen in einer Transaktion:24 Verpflichtungen und14 Gastfaelle
bestanden. Letzter Durchlauf ohne Build mit12 wiederverwendeten und zwei neuen
Gastbelegen. Unveränderte Altprofile, Ring3-Fehlergrenze und verbleibende
Systemabnahme bleiben Anforderungen. R3.6b bleibt ausdrücklich zurückgestellt.

Stand: 15. September 2026. Nutzerpriorität: die 64-Bit-Version fertigstellen.
Basis `fd8dc3d7`; i386 bleibt unveränderter Standard und Rückfallpfad bis zur
eigenen vollständigen Systemabnahme. Dieses Papier ist keine Fertigmeldung.

## R8.3ao: Gerätebesitzgrenze vollständig qualifiziert

Nach sauberem AN-Commit `4f4e1df4` folgt die gekoppelte PIO-/Ring3-Treiber-
Besitzzulassung für Slots2..7. Der einzelne bestehende ATA-Lesetreiber bleibt
bei denselben Rechten, Fristen und Restartgrenzen. Drei Builds, ein gemeinsames
neues Abbild für alle Slot-/Fehlerfälle, vollständiges Fencing/Reap/Selftest;
Details im [PIO-Poolvertrag](../architecture/NATIVE_POOL_PIO_CONTRACT.md).
Alle20 Verpflichtungen bestanden, zwölf Hostgruppen und18 Gäste238,399s;
letzter Kandidat mit zwei wiederverwendeten Referenzbuilds und genau einem
neuen PoolPIO-Build. Alte Fehlerbelege erhalten, CPU32 und Observer unverändert.
Dies ist die Geräte-Voraussetzung für spätere gleichzeitige Shell-/Dateidienste,
keine fertige normale Shell und keine CPU-Budgeterneuerung.

## R8.3an: zusammenhängende native Prozesspool-Kapazität

Nach vollständiger AM-Abnahme und sauberem lokalem Commit `0f4efd17` folgt
das explizite Acht-Prozess-Profil: Identität, Queue, sechs dynamische
Abbildbesitzer, IPC/Completion, Heap und vollständiges Retirement gemeinsam.
Kein bloßes Erhöhen einer Slotkonstante. Private run-v4-/C-layout5-Zulassung,
alte Vier-Slot-Profile bytegleich, unveränderte CPU-/Versuchs-/Zeitbudgets.
24 eingefrorene Verpflichtungen bestanden:21 ausgeführt, drei erfolgreiche
Builds exakt gebunden wiederverwendet, null Neubauten in Kandidat07.
Alle zehn Gäste aus einem gemeinsamen Abbild PASS, Matrix89,245s bei
unveränderten20s-Grenzen einschließlich Cleanup. Direkter ABI-/Grenz-/Cleanup-
Vergleich und unveränderlicher Qualifikationsbeleg abgeschlossen;
Details im [Prozesspoolvertrag](../architecture/NATIVE_TASK_POOL_CONTRACT.md).
Gerätebesitz, langfristige Dienstbudgets und normale Shell bleiben eigene
Grenzen; R3.6b weiterhin zurückgestellt. Queueabschluss folgt erst nach dieser
Qualifikation, lokaler Commit mit separatem sauberen Abschlussbeleg.
Frühere Fehlversuche bleiben unverändert dokumentiert; keine OS-Fertigmeldung.

## R8.3am: Datei, ELF64-Import und Programmlebensdauer

Neuester Stand: vollständige R8.3am-Paketabnahme auf Vertrag `f979c9a6`.
Alle30 Verpflichtungen plus Eingangs-/Abschlussprüfung PASS/REUSED375,114s.
Vollständige neue Dateistart18-Matrix mit zusätzlichem Kernel-/High-Bytevergleich
in jedem Gast PASS302,416s; jeweils14,375..17,458s einschließlich Cleanup.
Separater vollständiger Kontrollgast16,901s PASS. Originaloracles und20s/360s
unverändert; null neue Builds/Links. FS18, Normalboot, vier IRQ-Fälle und
Referenznachweise exakt gebunden wiederverwendet. Gesamtdiff und Beweiskette
geprüft, keine QEMU-/GDB-Prozesse verblieben. Queuepaket abgeschlossen; der
lokale Implementierungscommit erhält einen separaten hashgebundenen Beleg.
Alter22,565s-Timeout bleibt fehlgeschlagen/ungeklärt, kein kausaler Reparatur-
oder vollständiger64-Bit-OS-Nachweis. Nächster priorisierter Kern-/Dienstschnitt
erst nach sauberem Commit; R3.6b bleibt zurückgestellt.
[Stand und Belege](CURRENT_WORK.md).

### Historie: Native Dateisystem- und Bootregression

`b5bec1c8`: Ursprüngliche native FS18-Matrix und normaler
64-Bit-Boot bestanden; sieben Prüfgruppen PASS398,925s.18 FS-Gäste mit
unveränderten Oracles und jeweils12,803..15,321s einschließlich Cleanup,
zusammen264,557s. Ein Vollbuild beweist64 Payloads einschließlich kompletten
Boot-ELF bytegleich zum inkrementellen Link; vierzehn Varianten danach mit
nur dem aktuellen Scheduler-Objekt neu gelinkt, keine weiteren Kompilierungen.
Kernel-/Testquellen unverändert, null QEMU-/GDB-Prozesse nach Abschluss.
Die neun vorherigen Fehlergäste und Referenz7/7 bleiben bestanden. Offen:
ursprüngliche Dateistart18-/native30-Gesamtabnahme und22,565s-Zeitausreißer.
Kein Implementierungscommit/Queuewechsel oder64-Bit-Fertigmeldung.
[Stand und Belege](CURRENT_WORK.md).

### Historie: Native Fehlergäste abgeschlossen

`8fbcd28b`: Fehlende native OOM-/Dateifehler-/IRQ-Prüfung
13/13 Gruppen PASS231,911s, neun reale Gäste PASS, jeweils einschließlich
Cleanup unter20s. OOM erste/mittlere/letzte Allokation, Dateifälle9/10 und
IRQ idle/expired/context/eoi mit vollständigen unveränderten Oracles belegt.
Zehn Hostgruppen wiederverwendet, nur die zwei nie gebauten Varianten neu
kompiliert.12er-Cache unverändert; neue Outputs separat erhalten. Kein Kernel-
oder Testumbau, null verbleibende QEMU-/GDB-Prozesse. Referenz7/7 bleibt grün.
Ursprüngliche18-Fall-/30-Gruppen-Gesamtabnahme und früherer22,565s-Zeitausreißer
weiter offen; kein Implementierungscommit/Queuewechsel oder64-Bit-Fertigmeldung.
[Stand und Belege](CURRENT_WORK.md).

### Historie: Native Variantenbuilds wiederverwenden

`8944049a`: Native Dateistart-Matrix verwendet zwölf gepinnte
Varianten erneut; zusätzliche Variantenbuilds sinken von14 auf2.1509 Eingaben,
16 aktuelle Werkzeuge und924 alte Artefakte/Logs gebunden; Gastoracles/Fristen
unverändert. Nach erhaltener roter Aliasprüfung wird nur der exakt gebundene
WinGet-Make-Installationslink zugelassen.25 Hosttests und reale Cacheprüfung
parallel PASS20,724s, davon Cache2,881s. Kein neuer Kernelbuild oder Gast.
Referenz7/7 bleibt grün; native Zeit-/OOM-/IRQ- und64-Bit-Systemabnahme offen,
kein Implementierungscommit/Queuewechsel. [Stand und Belege](CURRENT_WORK.md).

### Historie: Vollständige Referenzabnahme

`8fafa5d0`: Vollständige i386-Referenzabnahme7/7 PASS313,376s,
sechs reale Referenzgäste bestanden.69 Hosttests und zwei signierte Builds
hash-/quellengebunden wiederverwendet, null Neubauten,288,234s Buildarbeit
vermieden. VMware/APIC-Kopien im erhöhten Konto mit unveränderten Start-/Gast-
und Cleanup-Grenzen erfolgreich; QEMU/APIC/PIT und EXT2-Stat/Symlink-Recovery
regulär bestanden. Nach vollständiger Vorabprüfung nur fünf Guard-Konstanten
aktualisiert, ursprünglicher Guard PASS; null verbleibende VMs. Keine Host-
oder Kernelreparatur behauptet. Referenzhürde geschlossen; native Zeit-/OOM-/
IRQ-Abnahme und vollständige64-Bit-Systemabnahme weiterhin offen, keine neuen
nativen Gastbudgets oder Implementierungscommit/Queuewechsel.
[Stand und Belege](CURRENT_WORK.md).

### Historie: Eigene Test-VM sicher beendet

`dda3f132`: Freigegebener exakter RunAs-Cleanup PASS10,937s;
vollständige Prozesskommandozeile/Programmdatei/Startzeit zur eigenen Test-VM
gebunden. Originaler Cleanup plus abschließendes reguläres Inventar bestätigen
null VMX-Prozesse/VMs. Keine Host-/Dienst-/ACL-Änderung, Builds oder Gaststarts.
Cleanup-Blocker geschlossen, VMware-Steuerkanal nicht als repariert nachgewiesen.
Build-Wiederverwendung weiter verfügbar; native Zeit-/OOM-/IRQ- und vollständige
64-Bit-Abnahme offen. Kein Kernelumbau oder Implementierungscommit/Queuewechsel.
[Stand und Belege](CURRENT_WORK.md).

### Historie: Build-Wiederverwendung

`d0b0bc93`: Prüfer unterstützt feste hashgebundene Wiederverwendung
der erfolgreichen VMware-/QEMU-Referenzbuilds (`--check-builds`).18 Hosttests und
echte Prüfung aller202 Artefakte parallel PASS, null Builds/Gäste. Cacheprüfung
5,164s statt erneuter288,234s Buildarbeit; keine Gastabnahme daraus. Nur sieben
explizite nicht-bildwirksame Prüf-/Statusdateien dürfen variieren; Quellen,
Werkzeuge, Profile, Belege und Ausgaben bleiben gebunden. Künftige Qualifikation
übernimmt passende Buildbelege; historische Läufe werden nicht umgeschrieben.
VMware-Cleanup und native Zeit-/OOM-/IRQ-Abnahme weiter offen; kein neuer
Kernel-Code, Implementierungscommit, Queuewechsel oder Fertigmeldung.
[Stand und Nachweise](CURRENT_WORK.md).

### Historie: VMware-Steuerkanal

`580acdda`: Einmaliger VMware-Vergleich unter `oe3sr` erreicht
mit identischer Kopie APIC, `BOOT_OK` und Ring-3-Shell. Startquittung20s und
Stop10s laufen ins Limit; Diagnose FAIL42,671s, GTEST nicht gesendet. VM-Log
belegt VMAutomation-Socket-/SSL-Fehler10038. Test-VM bleibt aktiv; Cleanup
NICHT bestanden, da CIM die Kommandozeile für den zugehörigen VMX-Prozess
nicht offenlegt. Kein Kill ohne gültige Eigentumsprüfung, keine Hostreparatur.
Zuerst ausdrücklich freigegebener privilegierter Cleanup nur der Testkopie
oder manuelles Ausschalten; danach neuer begrenzter Steuerkanalumfang.
Originale/alte Belege erhalten; keine neuen Abnahmegates, Sollhashänderungen,
OS-/Testkorrekturen oder Implementierungscommits/Queuewechsel. Native Zeit-/OOM-/
IRQ-Abnahme weiter offen; Bootdiagnose beendet keine64-Bit-Migration.
[Genaue Test-VM und Belege](CURRENT_WORK.md).

### Historie: Windows-Metadatenkorrektur und VMware-Start

`9cb39d62`: Windows-Metadatenvergleich nach echter roter CMD-
Regression korrigiert. 64 Hosttests einschließlich phasengenauer tatsächlicher
Mutationen und beide Builds PASS. Ganze Quellaufnahme und Inhalts-/Signatur-
bindung von vier Abbildern/96 Programmen erfolgreich, keine Gastabnahme daraus.
17 Gruppen 12/1/4 in387,591s: erster headless VMware-Start meldet Unknown error.
Eine Startanforderung, kein Bootnachweis; eigene Kopie unverändert und Cleanup
bestätigt null laufende VMs. Hostlogs auch beim erweiterten Lesen gesperrt;
Sandbox-/regulärer Benutzerkontext verschieden, Ursache noch unbewiesen.
Begrenzte VMware-Startdiagnose braucht eigenen Umfang; keine ACL-/Hoständerung,
Wiederholung, Sollhashänderung oder Implementierungscommit/Queuewechsel.
Native Zeit-/OOM-/IRQ-Abnahme und OS-Fertigstellung bleiben offen. [Stand](CURRENT_WORK.md).

### Historie: Quellmetadatenvergleich

`3efc9f37`: Leerdateiregression zunächst erwartungsgemäß rot,
nach separatem Quellhasher grün; Nonempty-Artefaktguard unverändert. Erste
Hostgruppe 8 Tests erfolgreich/2 Fehler, 17 Gruppen insgesamt 0/1/16 in2,949s.
Neuer Prüfer setzt unter Windows abweichende Pfad-/Handle-ctime und Modebits
gleich; 1.516 Eingaben nur lesend verglichen, kein Pfadwert geändert. Normale
Quellen dadurch vor dem Lesen abgewiesen, kein belegter OS-Defekt. Nächster
Umfang: getrennte vollständige Vorher-/Nachherprüfungen mit gemeinsamer
Dateiidentität und echten Rewrite-/CMD-/phasengenauen Mutationstests.
Keine Wiederholung, Builds, Gäste, Image-/Sollhashänderung oder Implementierungs-
commit/Queuewechsel. Native Zeit-/OOM-/IRQ-Abnahme weiter offen; OS nicht fertig.
[Stand](CURRENT_WORK.md).

### Historie: Interpreterkorrektur und Quellaufnahme

`fd35f2f1`: Interpreter auf PowerShell 7 korrigiert; 58 Hosttests
und vollständige VMware-/QEMU-Builds PASS (147,356/145,819s). Keine OS-/Buildskript-
oder Teständerung. Die 17 Referenzgruppen stoppen nach 361,791s bei 12/1/4:
Der Referenzadapter lehnt die vorhandene leere Quelle `kernel/syscall/syscall.c`
mit einer für Bootartefakte bestimmten Nonempty-Regel ab. Unveränderter Git-
Platzhalter, kein belegter Kerneldefekt; Quellen nicht auslassen und Artefaktguard nicht
lockern. Keine Gäste, Reparatur/Wiederholung, Image-/Sollhashänderung oder
Implementierungscommit/Queuewechsel. Begrenzte Quellhasherkorrektur mit echter
Leerdatei-Regression und unveränderter Referenzabnahme braucht eigenen Umfang.
Native Zeit-/OOM-/IRQ-Nachweise bleiben offen; OS nicht fertig. [Stand](CURRENT_WORK.md).

### Historie: Referenz-Interpreterfehler

`0c8fcb5a`: quellgebundener i386-Referenzabnahme-Adapter und
Regression ergänzt. Zehn Hostgruppen/58 Tests PASS; 17 eingefrorene Gruppen
stehen nach erstem Buildfehler bei 10/1/6 in 66,266s. Falscher Interpreter in
der neuen Buildzeile: Windows PowerShell 5.1 kennt die benötigte ArgumentList-
API nicht. Vorhandene PowerShell 7.6.6 bietet sie, durch lesenden Vergleich
bestätigt. Kein Build-Retry, Gast, Image-/Pinwechsel oder OS-/Parserfix.
Nächster eigener Umfang: nur Interpreterwahl korrigieren und identische
Referenzabnahme neu einfrieren. Kein Implementierungscommit/Queuewechsel;
native Zeit-/OOM-/IRQ-Abnahme bleibt offen. [Stand](CURRENT_WORK.md).

Die vorherige Herkunftsdiagnose ordnet den i386-Binärunterschied dem neuen
STORAGE-Programm und der gemeinsamen EXT2-Quelle aus `1835ee97` zu; Kernel
und 95 Programme unverändert. Spätere Benchmark-/Desktop-Schreibspuren sind
separat bytegenau erfasst, kein Grund für automatische Referenzübernahme.

### Historie: direkter Build-Prüfer

`d53f5b7a`: explizite stdout/stderr-Weitergabe im direkten
Build-Prüfer korrigiert; keine OS-/Make-/Teständerung. 26 Hosttests und alle vier
Builds PASS, direkter Make-Aufruf mit Exit 0/vollständigem Log. Alle 35/43/43/43
Kernelartefakte und fünf Dateistartprogramme bytegleich zu den Vergleichsbuilds.
Acht Buildgruppen einmalig: 7 PASS / 1 FAIL / 0 NOT_RUN in 62,635s. Letztes Gate
stoppt an `reference drift: build/reist-os.img`: Isthash `2b58094b...` statt
Sollhash `d6e77ebe...`; Herkunft der Imageänderung nicht belegt. Image und Sollhash
unangetastet, kein Retry. Korrektur früherer Angaben: Die 207 erhaltenen Pins
sind native x86_64-Bootstrap-Artefakte, keine i386-Images; deren separate Prüfung
ist jetzt fehlgeschlagen. Neue lesende Herkunftsklärung braucht eigenen Umfang.
Keine Gast-/30-Gate-Erneuerung, Implementierungscommit oder Queueänderung;
ursprüngliche 23/1/6 Paketgates, Zeit-/OOM-Nachweise bleiben offen. OS nicht fertig.
[Stand und vollständige Hashes](CURRENT_WORK.md).

### Historie: Make-Defaultkorrektur

`18ff9a83`: direkter Make-Defaultfehler reproduziert und die drei
betroffenen ?=0-Zuweisungen vorgezogen. Erst sieben von acht Kombinationen rot,
danach alle acht mit identischem Buildplan grün; 26 Hosttests und drei Windows-
Builds PASS, alle bisherigen Binärdateien unverändert. Buildgruppe 7 endet mit
Code 2/leerem Log; auch deren 43 Kernelartefakte/fünf Programme bytegleich.
Hostvergleich zeigt fehlende explizite Ausgabevererbung im neuen direkten Prüfer;
kein Kernel-/Gastdefekt daraus abgeleitet. 6/1/1 Buildgruppen, Referenzgate nicht
ausgeführt; Prüferreparatur und erneute Buildprüfung brauchen eigenen Umfang.
Keine Gast-/Paketfreigabe: ursprüngliche 23/1/6 Gates, Zeitabweichung und OOM offen.
Kein Implementierungscommit oder Queuewechsel. [Stand](CURRENT_WORK.md).

### Historie: FAT12-Zeitdiagnose

`d53ecf49`: Case6-/FAT12-Diagnoseablauf zusammengeführt,
24 Hosttests PASS. Zwei Kontrollen am unveränderten FAT12-Abbild bestehen den
vollständigen ursprünglichen Oracle in 16,911/17,144s einschließlich Cleanup,
je 16 Reaps/zwei Runs. 75 Uhr-/Peeraufnahmen konsistent, Peers 2/10 enden normal;
keine verlorene Weckung beobachtet. Historischer Zeitfehler nicht reproduziert,
kein belegter Kernel-Fix oder erneuerte Paketabnahme. Beide Diagnoseplätze
verbraucht; ursprüngliche 23/1/6 Gates und offene OOM-Gäste bleiben bestehen.
Nur Diagnose/Test geändert, kein Implementierungscommit oder Queuewechsel.
Direkter Make-Default-Reihenfolgehinweis bleibt eigener offener Review-/Reparatur-
umfang; keine blinde Gesamtwiederholung. [Gesicherter Stand](CURRENT_WORK.md).

### Historie: erneute FAT12-Abnahme

`f934a12d`: vollständige unveränderte Abnahme nach 23 bestandenen
Prüfgruppen bei Gate 24 gestoppt. 20 Hostgruppen (144 Tests/ein bestehender Skip)
und drei Builds PASS; sechs Folgegates NOT_RUN. Erster success/FAT12/4GiB-Gast:
22,565s inklusive Cleanup statt höchstens 20s, 15/16 Reaps und 1/2 Runs.
Vier Dateiprogramme und beide Roots enden korrekt; letzter Peer 10 fehlt.
Kein protokollierter Fatal/Observerfehler. 43 Kernelartefakte und fünf Programme
bytegleich zum früher in 17,605s erfolgreichen Gast, Zeitursache weiter offen.
Keine OOM-Gäste erreicht, kein Retry oder Implementierungscommit/Queuewechsel.
Zusätzlicher statischer Make-Reviewhinweis: Dateistartguard vor FS-Case-Default;
positiver direkter Make-Test noch erforderlich, kein Zusammenhang mit Gasttimeout.
AM aktiv, OS nicht fertig. Nächster eigener Umfang: begrenzte FAT12-Zeitdiagnose
mit unverändertem Oracle und Fristen. [Gesicherter Stand](CURRENT_WORK.md).

### Historie: Case6-Zeitdiagnose

`cb254293`:22 Diagnosehosts PASS; beide unveränderten case6-
Kontrollen bestehen vollständig16.215/16.512s inklusive Cleanup mit14 Reaps und
2 Runs.72 Uhr-/Peer-Snapshots konsistent, tatsächliche45x100ms-Warteschleifen
enden normal. Zeitfehler nicht reproduziert, kein belegter neuer Kernel-Fix.
Beide Diagnoseplätze verbraucht; keine erneuerte Paketabnahme, OOM-Gäste weiter
offen. Original23/1/6 historisch unverändert, AM aktiv; kein Implementierungscommit
oder Queuewechsel. Weitere vollständige Qualifikation braucht einen eigenen
freigegebenen Umfang, keine abgeschwächten Fristen. [Gesicherte Belege](CURRENT_WORK.md).

### Historie: OOM-Prüferkorrektur

`15f650f2`: OOM-Prüfer trennt alte Imagefreigabe exakt von neuer
Allocation-Rückabwicklung; tatsächliche Callback-Hostregression erst rot, dann
grün samt negativen Freigabe-/Bilanz-/Generationsprüfungen.20 Hostgruppen
(142 Tests/ein bestehender Skip),3 Builds und elf vollständige Dateistartgäste
PASS. Gate24 stoppt in Treiber-UD2/case6 nach22.508s an der20s-Frist:
13/14 Reaps,1/2 Runs, letzter Peerabschluss fehlt. FS-Exit90 bleibt korrekt;
Gastartefakte bytegleich zum früher erfolgreichen Lauf. Keine belegte Zeitursache,
kein protokollierter Fatal/Observerfehler. OOM-Gäste noch nicht erreicht;
Prüferkorrektur somit nicht gastabgenommen.23/1/6 Gates, keine Paketabnahme,
Wiederholung oder Queueänderung. Nächster eigener Umfang: begrenzte Diagnose
von Capture-/Peerfortschritt bei unveränderten Grenzen. [Belege](CURRENT_WORK.md).

### Historie: FS-Retirementkorrektur

`ffce1f2c`: Ring-3-Retirementfehler korrigiert; tatsächlicher
C-Host zuvor O0/O2 rot221, danach je89 Prüffälle grün. Treiber-UD2 besteht nun
im Gast16.624s mit14 Reaps/2 Runs und unveränderten FS-Exitwerten90. Insgesamt
13 Dateistartgäste,20 Hostgruppen (139 Tests/ein bestehender Skip) und3 Builds
PASS. Gate24 stoppt im ersten OOM-Fall nach5.634s an der Rollback-Assertion.
Observer-/Kernel-Basis werden laut Code vor/nach alter Imagefreigabe gesetzt;
genaue Freizähler fehlen noch im Fehlerrecord, kein belegtes Speicherleck.
23/1/6 Gates, keine Abnahme oder weitere Wiederholung. Nächster eigener Umfang:
beide OOM-Transaktionsphasen exakt nachweisen. [Gesicherter Stand](CURRENT_WORK.md).

### Historie: Binärleser-Anbindung

`55959eae`: regulärer Binärleser-/Einzellog-Adapter integriert;
ursprüngliche Assertions/Fristen und Gastcode unverändert.20 Hostgruppen mit138
Tests (ein bestehender Skip),3 Builds und elf vollständige Dateistartgäste PASS.
Gate24 stoppt im zwölften Gast (Treiber-UD2) nach9.276s: Supervisor sendet FS-
CANCEL, erwartet aber normalen Exit90; tatsächlicher FS-Abbruch führt zu
Supervisorstatus221 und abgewiesener Abschlussprüfung. Kein Timeout oder
protokollierter Kernel-Fatal.23/30 Gates PASS,1 FAIL,6 NOT_RUN; keine Paketabnahme.
Gezielte Ring-3-Retirementkorrektur mit Host-/Gastregression ist ein neuer,
ausdrücklich freizugebender Umfang. [Befunde und Nachweise](CURRENT_WORK.md).

### Historie: Reguläre GDB-Abnahme

`3c72519b`: einmalige reguläre Abnahme begonnen,23/30 Gates PASS
(20 Hostgruppen,3 Builds), Gate24 im ersten FAT12-Dateistartgast fehlgeschlagen,
6 Gates nicht mehr ausgeführt.15/16 Reaps, kein protokollierter Kernel-Fatal oder
OBSERVER_FAIL;22.459s Capture inklusive Cleanup. Frischer FAT12-Kernel bytegleich
zum Diagnoseimage. Regulärer Prüfer nutzt noch GDB-Speicherlesungen und doppelte
Logs, nicht den optionalen Binärtransport erfolgreicher Diagnosekontrollen.
Keine weitere Ausführung/Korrektur in diesem gestoppten Prüfblock. Nächster
Vorschlag: ausdrücklich begrenzte Anbindung dieses Lesers an die reguläre
Dateistartmatrix mit allen bisherigen Assertions/Fristen; keine Fertigmeldung.
[Prüfergebnisse, Artefaktunterschiede und offene Gates](CURRENT_WORK.md).

### Historie: Äquivalenz-Lesekosten

`4db9ec7f`: tatsächlicher Äquivalenzpfad in beiden Diagnosegästen
vollständig18.554/17.196s, je16 Lebenszyklen und2 Programmstarts.20 Hosts/.460s
PASS. Die zwei zusätzlichen GDB-Vergleiche über425984 Byte kosten nur156/110ms,
beide byte-/hashgebunden korrekt. Kein belegter teurer Zusatzvergleich und keine
neue Kernel-/Transportreparatur. Diagnosepaar verbraucht, keine rückwirkende
Abnahme oder Gateerneuerung; reguläre Paket-/IRQ-Prüfung weiterhin offen.
Vorschlag: ausdrücklich begrenzte Abnahmewiederaufnahme statt weiterer
Profilierung. [Befunde und offene Prüfungen](CURRENT_WORK.md).

### Historie: Timer-/Fortsetzungspaar

`5e04515b`: Timer-/Fortsetzungspaar vollständig, beide originalen
Prüfer18.291/18.721s,16 Lebenszyklen und2 Programmstarts. Host13/16 PASS.
QEMU-Spur: je916 IRQ0/Vektor32, keine Zustellung in Stop-/Einzelschrittphasen;
79 monotone, übereinstimmende native Tick-/EOI-Aufnahmen. Debuggerstopps5.096/
5.429s, Einzelschritt-Laufphasen nur.270/.274s. Kein neuer Kerneldefekt.
Die frühere Zeitüberschreitung ist nicht reproduziert; tatsächlicher
Äquivalenzpfad mit Zusatzlesevorgängen bleibt ungeklärt und nicht abgenommen.
Diagnosepaar verbraucht, keine Gate-/IRQ-Erneuerung oder Paketfreigabe.
[Gesicherte Einzelheiten und nächste Umfangsgrenze](CURRENT_WORK.md).

### Historie: gemeinsame Zeitmessung und letzte Korrektur

`96a228f1`/`277405bc`: gemeinsame Zeitmessung (Host13/.223s)
belegt zwei vollständige Diagnosegäste17.294/18.102s und regelrechten Abschluss
beider Peers. Die gemessenen75 Verbindungsaufbauten/1.073s begründen die letzte
freigegebene Korrektur: QMP-Verbindung nur innerhalb eines angehaltenen Callbacks
teilen, sämtliche Prüfungen pro Zugriff und Schließen vor Fortsetzung erhalten.
Echter Rot-/Grün-Host14/.568s; anschließender Äquivalenzgast dennoch20s/15 von16
Reaps, kein neuer Fatal oder Prüfbytefehler. Messpaar verbraucht, letzte Korrektur
gestoppt, keine Paketfreigabe oder IRQ-/Gateerneuerung. Die zeitliche Differenz
zwischen Kontroll- und Äquivalenzlauf bleibt ungeklärt. [Belege](CURRENT_WORK.md).

### Historie: erster Binärtransport

Vertrag `aa6086a2`: optionaler binärer RAM-Prüftransport,
vier Hostgruppen12/10/8/8 PASS. Beide Gastversuche belegen Kernel-/High-RAM
bytegleich zu GDB. Ein QMP-Ereignisstau wird durch je Lesevorgang neue und
begrenzte Verbindungen behoben (echter Rot-/Grün-Test). Der korrigierte Gast
schafft73 Exporte, aber nur15/16 Reaps bis20s; vollständige Abnahme weiterhin
offen. Keine gelockerte Frist, keine neue Kernel-/Gaständerung, keine erneuerte
IRQ-/Originalgatematrix. Zwei von maximal vier Gästen genutzt; kein identischer
Retry ohne belegte Quellkorrektur. [Befunde und Bindung](CURRENT_WORK.md).

### Historie: Stop-/Timerpaar

Vertrag `491443ac`: Stop-/Timerpaar abgeschlossen; acht
Diagnosehosts PASS. Beide20s-Gäste bleiben im zweiten Lauf unvollständig.
73 native Zustandsaufnahmen belegen monotone, übereinstimmende Tick-/EOI-
Werte und Fortschritt des zweiten Peers; an dessen letzter Aufnahme fehlen
noch mindestens3220ms nominelle Gastzeit. Keine vollständige OS-/Paketabnahme
und keine neu belegte Kernelstörung. Callback-/Zwischenzeiten werden getrennt
ausgewiesen; GDB meldet die internen Fortsetzungen nicht einzeln. Beide neuen
Diagnoseplätze verbraucht, nur Diagnosecode/Host geändert, keine weitere
Reparatur- oder Laufautorität. [Belege und Fortsetzungsgrenze](CURRENT_WORK.md).

### Historie: gebündelter Speichertransport

Gemeinsame Transportdiagnose (`617832e1`, `af247388`,
`6c59454d`) abgeschlossen, aber keine Paketabnahme. Ein vollständiger
Diagnoseprüfer besteht bei19.615s aktiver Zeit; beide gezielten Korrekturen
an tatsächlichen Seitentabellen-/RAM-Lesezugriffen bestehen die Hosttests,
die profilierten Gäste überschreiten weiterhin20s vor dem zweiten Peerende.
Dateistart8, Kostenmessung4 und gemeinsamer Transport10 Hosttests PASS.
Sechs von sechs Gäste verbraucht, Stopregel nach zwei Korrekturen aktiv.
Keine weitere Kernel-/Quoten-/Friständerung, keine neue IRQ-Matrix oder
Implementierungsfreigabe. Quellen34/erlaubte Pfade36 und alle alten Belege
bleiben erhalten; [Befunde und Fortsetzungsgrenze](CURRENT_WORK.md).

### Historie: begrenzte Legacy-Sleep-Diagnose

Vertrag `9ebaf6a5`: beide begrenzten Legacy-Sleep-Diagnosen
erreichen den korrekten Schlussmarker. Tick/EOI/Schlussfrist jeweils4,
27 exakte Ereignisse, Handoffs3/Fehler0/Reaps4; zweiter Lauf bindet zusätzlich
alle27 Ereignisse an tatsächliche Ticks. Host9/.021s PASS. Kein neuer Fatal,
keine reproduzierte Ursache des früheren Modus5/0x9F-Abbruchs; deshalb keine
Legacy-Kernelkorrektur. Beide Gäste stoppen später an der20s-Dateistart-
Capturefrist, im zweiten PROCESS_RUN. Das freigegebene Paarbudget ist verbraucht;
die nur nach belegter Legacy-Korrektur erlaubte IRQ-Matrix bleibt NOT_RUN.
Weitere begrenzte Laufzeit-/Beobachterdiagnose braucht ausdrücklichen Umfang.
Quellen und Fehlerbelege bleiben erhalten, keine neue Abnahme oder
Implementierungscommit. [Neueste Befunde und Bindungen](CURRENT_WORK.md).

### Historie: native IF-Korrektur und anschließender Legacy-Scope-Stopp

Aktuell: gezielte native Idle-IRQ-Korrektur als uncommitteter Kandidat,
Verträge `300cfbc2`/`eab12d16`,29 Quellen. Ein echter Post-Fencing-Snapshot
belegt IRQ-Wiedereintritt am Idle-CLI nach bereits erfolgtem Wake; der
gespeicherte CPL0-Frame behält jetzt IF=0 bis zur erneuten Dispatcherzulassung.
Deterministischer echter Assemblerhost zuerst rot, danach O0/O2 grün;
der Gast zeigt zweimal den korrekt maskierten Rückweg. Keine Quoten-/ABI-
Erweiterung, keine rückwirkende Ursachenzuordnung zu alten unbeobachteten Fatals.

Vollabnahme weiterhin blockiert: zwei Kontrollgäste überschreiten die feste
20s-Frist beim letzten Peer. Der vierte und letzte erlaubte Versuch scheitert
bereits im älteren Sleep-Schlussprüfpfad (Modus5/Stufe0x9F) vor dem Dateistart.
Dessen konkretes Prädikat ist unbekannt und `cooperative_scheduler.asm` liegt
außerhalb des freigegebenen Kernelumfangs. Keine fünfte Wiederholung;
begrenzte Legacy-Diagnose/Korrektur benötigt ausdrückliche Scope-Erweiterung.
Neue gebündelte Seitentabellenlese besteht den tatsächlichen Hosttest, aber
ihre Gastqualifikation wurde nicht erreicht. Drei IRQ-Fehlinjektionsgäste
bleiben NOT_RUN. Historische20 Gates4 PASS/1 FAIL/15 NOT_RUN, betroffene
Build-/Laufzeitbelege müssen wegen der Kerneländerung erneuert werden.
Keine Paket-/OS-Fertigmeldung; [aktueller Befund und Belege](CURRENT_WORK.md).

### Historische Datei-/Diagnosebefunde vor der Idle-Korrektur

Zweite Diagnosefreigabe `d0263b65`: vorhandener kalter Fatal-Callback ohne
zusätzlichen Breakpoint, Host6/.003s PASS. Ein unveränderter FAT12-Gast besteht
den vollständigen Prüfer in17.547s: zwei PROCESS_RUN/16 Lebenszyklen mit vier
Dateiprogrammen, Peerfortschritt, Fencing und vollständiger Ressourcenbilanz.
Kein Timer-Fatal oder IRQ-Snapshot; frühere Ursache weiterhin offen und keine
Beobachter-/Kernelreparatur belegt. Diagnose zählt nicht als Abnahme;20 Gates
bleiben4 PASS/1 FAIL/15 NOT_RUN. Weitere Diagnose-/Reparaturautorität ist offen.

Update14. September: Diagnosesupplement `5ad56853`, Host3/.002s PASS;
ein unveränderter FAT12/4GiB-Gast7.742s ohne Reproduktion des Timer-Fatals.
Treiber3 erreicht vorher32 CPU-Samples/Status256; FS-Erfolgsbeobachter stoppt,
keine IRQ-Register erfasst. Ursache des ursprünglichen Timer-Fatals bleibt offen.
Ein-Lauf-Diagnosebudget verbraucht, keine weitere Lauf-/Kernelautorität und
keine neue Abnahme. Alle bisherigen Kandidaten- und Fehlerbelege bleiben erhalten.

Kandidat auf Vertrag `f2040a17`: echter Datei-/ELF-Adapter, Medien-/Löschhosts,
neuer Build und fünf Runtime-/Oraclehosts bestehen. Der erste FAT12-Gast startet
beide Dateiprogramm-Generationen korrekt82 und beendet den Supervisor83 bei
25/32 CPU-Samples. Danach fataler Timer-IRQ0x20; Peerabschluss und zweiter
PROCESS_RUN fehlen,0/18 neue Gäste akzeptiert. Kernelobjekte unverändert zum AL;
konkrete IRQ-/Registerursache nicht gesichert. Weitere Timer-/Idle-Diagnose nach
dem oben dokumentierten Einzellauf braucht ausdrückliche begrenzte Freigabe,
kein Kernelumbau oder unveränderter Gastretry. Kandidat aktiv/uncommitted,
4/20 Gruppen PASS, ein FAIL,15 offen. [Fehlbelege und Grenzen](CURRENT_WORK.md).

Nach sauberem Abschluss `1835ee97` verbindet der nächste Schnitt die vorhandenen
Ring3-Adapter von stat/read bis zum tatsächlich gestarteten nativen ELF64.
Alle fünf Medien und dieselbe begrenzte Fehler-/Wiederanlaufgrenze zusammen;
keine Quoten-/Kernel-Erweiterung oder normale parallele Shell-Zusage.
Die feste1536-Byte-Dateigrenze folgt aus dem bestehenden Acht-Anfragen-Profil,
nicht aus einem geänderten ELF-Format. Standard-GNU-Linklayout und echter C-
Verbraucher,20 Gates einschließlich neuer18- und alter18-Gast-Matrix.
[Vertrag](../architecture/NATIVE_FILE_LAUNCH_CONTRACT.md),
[Arbeitsstand](CURRENT_WORK.md). Noch keine Implementierungsabnahme.

## R8.3al: Read-only-Dateisystemprofil und Referenznachweise

Der gemeinsame FAT12/FAT32/EXT2-Dienst mit getrenntem PIO-Treiber ist im
begrenzten nativen Profil umgesetzt:18 Dateisystemgäste, elf alte Blockprofil-
gäste, drei Trace-Ablehnungsfälle, Standardstart und Referenzartefakte bestehen.
Vertrag `3d608fb9` umfasst24 Dateien/21 Gruppen; konkrete Befehle, Zeiten,
Quellbindungen und erhaltene Fehlerhistorie stehen im [Arbeitsstand](CURRENT_WORK.md).
Gemeinsame kalte Beobachtungsrouten und der zeitlich begrenzte alte Antwortfang
ändern weder Gast noch Kernel/Quoten. Eine frühere isolierte Framebilanz-
abweichung bleibt ursächlich offen; verschärfte Vorher-/Nachherprüfungen
bestehen in der vollständigen neuen Matrix. Keine System-Timing-Zusage.
Normale Shell-/Userland-Anbindung und vollständige OS-Abnahme bleiben offen.

## Historie R8.3al: Scope-Stopp und Wiederaufnahme

Aktuell ist die Nacharbeit am alten Blockprofil-Beobachter samt Runtime-Test
ausdrücklich freigegeben: derselbe zugeordnete Kandidat,24 Dateien/21 Gates.
Die folgenden Stopbelege bleiben historisch erhalten; die gemeinsamen
Beobachtungsgrenzen werden bei unveränderten Bildern und Quoten konsolidiert.

Eingefroren auf sauberem `3cd8fe87`: R8.3al bündelt den
nativen Read-only-IPC-/Cacheadapter, FAT12/FAT32 und sämtliche unterstützten
EXT2-Blockgrößen mit getrenntem Treiber, frischen Selftests und begrenztem
Abhängigkeitsersatz.22 Dateien/19 Gates; keine Quoten-, Kernel- oder
Schreibrechtserweiterung. [Dateisystemvertrag](../architecture/NATIVE_FILESYSTEM_CONTRACT.md).

Der Kandidat und die drei Builds sind vorhanden. Tatsächliche O0/O2-Tests
prüfen alle fünf Medien, unveränderte Ausgabe bei Fehlern, Protokoll-/Cache-
Grenzen und EXT2-Bereichslesen einschließlich alter Guard-/Objektverbraucher.
Der kurze EXT2-Dateizugriff braucht8/10/14 statt9/13/21 verschiedene Sektoren.
Die gemeinsame18-Gast-Dateisystemmatrix einschließlich aller Fehler-/OOM-
Fälle besteht (`runtime-08.log`,278.136s Gastzeit). Die Pflichtwiederholung
des alten Blockprofils scheitert aber trotz bytegleichem Gast und Beobachter
an CPU32 vor Antwort9.15/19 Gruppen PASS, ein FAIL, drei offen. Der alte
Beobachter und sein Runtime-Test liegen außerhalb der22 freigegebenen Dateien:
Vertragsstopp, Kandidat uncommitted, keine Queue-Weitergabe. Weitere gezielte
Beobachterarbeit erfordert ausdrückliche Scope-Freigabe. Keine Quoten-/Kernel-
änderung oder Gesamt-OS-Zusage; alle bisherigen207 Artefakte unverändert.
[Aktueller Stand und Belege](CURRENT_WORK.md).

## R8.3ak: begrenzte Blockprofile und vollständige Gastnachweise

Elf vollständige Blockprofil-Gäste bestehen nach begrenzten Release-/CREATE-
Haltepunkten auf unverändertem Gastabbild und bei unveränderten Quoten.
Neun reale Reads, Fehlercontainment, Ersatz und vollständige Löschung sind
in den vorgesehenen Fällen nachgewiesen. Alle acht Diagnosekontrollen sind
verbraucht. Auch Manipulation3, alter Blockdienst10, Wide13/104 Lebensläufe,
Fatal9, Standardboot, ursprüngliche i386-Artefakte, Fachhosts und fünf Builds
bestehen. Paketumfang25 Gates inklusive Dokumentation; konkrete Abschluss-
belege im Arbeitsstand. Normale Ring3-Dateisystemintegration bleibt der nächste
Schritt, nicht Bestandteil dieser Abnahme. Keine fertige64-Bit-OS-Version.
[Aktueller Stand und Belege](CURRENT_WORK.md).

## Historie R8.3aj/R8.3ak: Kapazität, Blockprofile und Diagnose

Neu ausdrücklich freigegeben: begrenzte QEMU/GDB-Transportdiagnose mit
sechs Vergleichsgästen und höchstens zwei gezielten Folgekontrollen,
je20s/insgesamt160s.30 Dateien/25 Gates, gleicher zugeschriebener Kandidat,
keine Gasttakt-, Quoten- oder Oracleänderung. Ein nachgewiesener Transportfix
darf innerhalb dieser Grenze unmittelbar umgesetzt werden; Diagnose allein
ersetzt keine vollständige Profil-/Systemabnahme. Details: [Arbeitsstand](CURRENT_WORK.md).

Aktuell auf Vertrag `d461a797`: Das nicht autoritative PIO-Journal ist als
Kandidat umgesetzt; tatsächliche O0/O2-Pufferhosts, Consumer-Negativtests
und der Profilbuild bestehen. Der Vollbeobachter erreicht trotz zwei gezielter
Korrekturen weiterhin32 CPU-Samples, zuletzt im fünften Auftrag nach vier
korrekten Antworten. Physisches Fence/Reap und komplette Journal-Löschung
im ersten Lauf bestehen; keine Ersatz-/Zweitlauf- oder Neun-Anfragen-Abnahme.
Die drei Diagnosefehler-Gäste sind noch nicht ausgeführt, übrige betroffene
Gates/Legacy-Bytebindung offen. Stop-Bedingung erreicht, kein
Implementierungscommit/Queuewechsel. Weitere begrenzte QEMU/GDB-
Ursachendiagnose braucht neue ausdrückliche Freigabe.27 Dateien/24 Gates;
[aktueller Stand und historische Belege](CURRENT_WORK.md).

Historie der Freigaben und Vorbefunde:

Neu ausdrücklich freigegeben: begrenzte nicht autoritative PIO-Ereigniserfassung
mit unveränderten Vollprüfungen und zusätzlichen Überlauf-/Manipulations-/
Cleanupnachweisen.27 Dateien/24 Gates; gleicher aktiver Blockdienstkandidat,
kein Folgepaket und keine vorgezogene Systemabnahme.

Aktuell auf `907359a9`: lokale Framekostenkorrektur besteht tatsächliche
O0/O2-Differenz-/Kollisionsprüfungen; der aktualisierte Ownership-Test und
Wide13 bestehen. Die neue Blockprofilmatrix bricht unter Vollbeobachtung
weiterhin am32-Sample-Budget ab, jetzt im fünften Leseauftrag. Vier kontrollierte
Minimal-/Snapshotgäste vor/nach der Änderung enden dagegen regulär mit nur1..2
Dienstsamples. Keine Profilabnahme aus dieser Diagnose. Eine andere vollständig
geprüfte Erfassungstechnik braucht einen ausdrücklich erweiterten Vertrag;
keine weitere Prüfungsreduktion, Quoten- oder Timeränderung.25 Dateien/22 Gates,
sichtbarer Kandidat uncommitted; [Detailstand](CURRENT_WORK.md).

Die erneute ausdrückliche Nutzerfreigabe setzt R8.3ak mit einer begrenzten
Frameprüfungs-Kostenanalyse fort:24 Dateien/22 Gates, unveränderte vollständige
Besitzprüfungen und Quoten. Historische Stopbelege bleiben erhalten; dies ist
keine Vorwegnahme einer Gast- oder Systemabnahme.

R8.3aj ist mit `91401365` und allen18 Gates abgeschlossen. Der folgende
R8.3ak-Kandidat auf `61efea3d` ist nicht abgenommen: Nach zwei gezielten
Beobachterkorrekturen beendet das unveränderte32-Sample-Budget den Wide-
Blockdienst im vierten Leseauftrag. Neun erfolgreiche Anfragen und Ersatz-
lebenslauf fehlen. Host-/Buildpässe und alte Block10 ersetzen diese Gast-
abnahme nicht. Stop-Bedingung erreicht; sichtbare Änderungen und Fehlbelege
bleiben erhalten. Begrenzte Kostenanalyse benötigt eine neue ausdrückliche
Vertragsfreigabe; keine Quotenanhebung oder stillschweigende Scopeerweiterung.
Details: [Arbeitsstand](CURRENT_WORK.md).

Auf sauberem Abschluss `91401365` folgt R8.3ak: Der vorhandene EXT2-Parser
benötigt schon für15 Dateibytes neun unterschiedliche Sektoren, das alte
Blockprofil erlaubt acht Anfragen. Ein eigenes begrenztes Dienstprofil und
die noch fehlende Wide-PIO-Taskanbindung bilden die nächste gemeinsame
Blockdienstgrenze; bestehende API-/Kernelquoten bleiben unverändert.
20 Dateien/20 Gates; [Profilvertrag](../architecture/NATIVE_BLOCK_PROFILE_CONTRACT.md).
Die eigentliche Dateisystemintegration folgt erst nach dieser Abnahme.

Vertrag `60c65385` erweitert versioniert RNPGv2/CREATE-v5 auf64 Image-Slots
und einen privaten32KiB-NX-Stack mit Guardpage. Wiederverwendete Mechanismen
decken alle neuen Slots, vollständige Rollbacks und frische Bytes nach Reap
ab; Standardprofile und alte ABI-Versionen bleiben erhalten. Ein separat
reserviertes R/NX-Katalog-/RW-NX-Scratchareal erhält die feste C-Brücke,
C-Grenzen und bisherige16MiB-Bootabbildung. Keine CPU-/IPC-Quotenänderung.

13 neue Gastfälle/104 Lebensläufe bestehen einschließlich4/8GiB, Guard-/NX-/
RX-Fault, CPU-Ausfall, Cancel, Ersatzgeneration und sechs OOM-Punkten.
Reale12KiB-C-Stackbytes, alle327 Bootseiten und vollständige Framebilanz sind
beobachtet; tatsächliche O0/O2-Hostmechanismen und negative Oracles ergänzen
den Nachweis. Acht alte Importfälle, Normalboot und originale i386-Pins
bestehen.48 Dateien/18 Gategruppen; Detailbelege und erhaltene Erstfehler:
[Arbeitsstand](CURRENT_WORK.md), [Vertrag](../architecture/NATIVE_PROGRAM_MEMORY_CONTRACT.md).

Dies beseitigt die belegte Kapazitätsabhängigkeit der bestehenden Ring3-
Dateisystemparser, integriert diese aber noch nicht. Nach sauberem Paketcommit
folgt die nächste kohärente native Diensttransaktion ohne Routineübergabe.
Dateizugriff/-laden, normales Userland sowie volle System-/Hardwareabnahme
bleiben offen; R3.6b bleibt ausdrücklich zurückgestellt.

## R8.3ai: Block-RPC, Dienst und geschützte Komplettierung zusammen

Auf Vertrag `873d82fa` ist der gemeinsame Read-only-Blockdienst umgesetzt:
wiederverwendbarer Client/Dispatcher, Ring3-ATA-Service, echte IPC-Übergabe,
Deadline-Co-Admission und generationsgebundener Fehler-/Neustartpfad.
Die ausdrücklich freigegebene IPC-Kostenkorrektur kombiniert unveränderte
volle C-Eintrittsprüfung mit gezielter Neuversiegelung und einem geschützten
Komplettierungszustand für den Dispatch. IF=0 bleibt auch ohne C-Aufruf Pflicht.

Die finale Blockmatrix besteht zehn Fälle/160 Lebensläufe in145.662s; alte
PIO10 bestehen141.818s, Fatal9 bestehen9.658s einschließlich beschädigtem
Komplettierungsrecord. Reguläre Roots bleiben17..28 von32 Samples. Tatsächliche
O0/O2-Protokoll-, IPC-Kosten-/Korruptions- und ASM-/Adaptertests ergänzen die
Gastbelege. Normaler Bootstrap und originale i386-Pins bleiben gültig.
34 Dateien/21 Gategruppen; alle historischen Fehlversuche erhalten. Einzelne
Diagnosepässe oder fehlende Diagnosesummen wurden nicht als Abnahme verwendet.
Details und Kommandobelege: [Arbeitsstand](CURRENT_WORK.md).

Das ist noch keine vollständige64-Bit-Version: Dateisystemverbraucher,
Dateiladen über Dienstgrenzen, normales Userland und System-/Hardwareabnahme
bleiben offen. Keine Schreib-/DMA-Autorität oder alte Timerursache behauptet.
R3.6b bleibt ausdrücklich zurückgestellt.

## R8.3ah: Treiberrechte, Lesen und Fehlergrenze zusammen

Auf abgenommenem `abd9edb4` bündelt R8.3ah CREATE-v4 mit vollständigem192-Bit-
Profil, begrenzte Read-only-PIO-Mediation, Ring3-ATA-IDENTIFY/Sektortransfer,
Generation-Recovery und gemeinsame Kernel-Fatal-Sperre. Alte ABI-Versionen,
Quoten und Fristen bleiben erhalten. Kein Ring0-ATA-/Dateisystemparser.

Die finale PIO-Matrix besteht zehn Fälle/160 Lebenszyklen in111.471s; Import
und Startup jeweils acht Fälle/148 Lebenszyklen in58.280s beziehungsweise
52.978s. Insgesamt456 Lebenszyklen und898 Frame-Retirements. Acht zusätzliche
Fatalgäste in7.789s belegen physische Sperre vor Diagnose, unveränderte
beschädigte Metadaten und Halt statt Force-Cleanup/Return. Host O0/O2 und
negative Oracles ergänzen die realen Nachweise. Alle erzeugten COW-Medien
bleiben bytegleich. [PIO-Vertrag](../architecture/NATIVE_PIO_DOMAIN_CONTRACT.md).

Die separate i386-Referenzabnahme besteht unter Vertrag `92df3aa2`: zwei
exklusive VMware/APIC-Kopien und der eigene QEMU-Neubau mit APIC/PIT, vier
volle GTEST-/Recoveryfälle in146.810s. Signierte Plattformkerne, alle96
Programme und unveränderte Originalhashes sind unabhängig belegt. Feste Pins
erst danach überprüft aktualisiert; der finale Byteguard besteht in1.822s.

Fehlversuche und Gatebelege stehen im [Arbeitsstand](CURRENT_WORK.md).
Der frühere vector20 ist mangels damaliger Registerdaten nicht ursächlich
erklärt; die neue begrenzte Ursachenbeobachtung liefert keinen rückwirkenden
Beweis. System-Timing/Stabilität und vollständige OS-Abnahme bleiben offen,
ebenso normale Storage-/Datei-/Shellintegration und weitere Hardwareprofile.

## R8.3ag: Ring3-ELF64 bis zum nativen Abbildbesitz zusammen

Auf `7757c747`, Verträge `5d7bfef6` und `8b530433`: C-ELF-Aufbereitung,
CREATE-v3, beide privaten Abbildkontexte, SDK/Build und Fehler-/OOM-/IPC-
Abnahme bilden einen gemeinsamen Ladepfad. Kein Einzelpaket je ELF-Feld,
Kindslot oder Fehlerpunkt. [Importvertrag](../architecture/NATIVE_IMAGE_IMPORT_CONTRACT.md).
Die achtteilige Importmatrix besteht mit148 nativen Lebensläufen. Quoten und
alte öffentliche Versionen bleiben unverändert; Ring0 parst keine ELF-Datei.
Gateabschluss und historische Fehler stehen im [Arbeitsstand](CURRENT_WORK.md).
Dateibytes kommen in dieser Abnahme noch aus einem eingebetteten Ring3-Abbild;
Dateisystem-/Gerätemediation und normaler Shell-Dateizugriff bleiben offen.

## R8.3af: konfigurierbarer Start und IPC-Verbindung zusammen

Auf `8a3bed10` sind CREATE-v2, unveränderliche Startargumente, SDK und
explizite generationsgebundene IPC-Übergabe ein gemeinsamer Schnitt mit13
Gategruppen. Kein Einzelpaket je Argumentzahl, Fehler, Neustart oder OOM-Punkt.
[Startvertrag](../architecture/NATIVE_STARTUP_HANDOFF_CONTRACT.md).
Alle acht neuen Gastfälle bestehen mit148 nativen Lebensläufen; die zwölf
alten Family-Fälle, normaler Bootstrap und i386-Pins bestehen ebenfalls.
Die vorab freigegebene OOM-Fixturekorrektur erhält alle Mechanismen und Grenzen;
konkrete Belege und historische Fehler stehen im [Arbeitsstand](CURRENT_WORK.md).

Die gemeinsame Start-/Besitz-/IPC-Grenze ist damit für Ring3-Verbraucher
nutzbar. Eine vollständige Dienstüberwachung samt Self-Test, endlichen
Restartbudgets und sicherem Ausfallzustand ist noch nicht integriert.
Ebenso offen: Dateiladen außerhalb Ring0, native Geräte-/Dateidienste,
normales Userland und eigene vollständige Systemabnahme. Die nächste Inventur
bündelt einen solchen vollständigen Sicherheitsbereich; i386 bleibt Fallback.

## R8.3ae: Start, Wait, Cancel und Elternausfall zusammen

Nach `cbe5b956` wird die gemeinsame Besitzgrenze als ein Paket eingefroren:
versioniertes Task-Control, vollständige Syscallautorität, dynamische Starts,
endliches Warten, Abbruch, Elternausfall und vollständige Ressourcenfreigabe.
Keine Einzelpakete je Operation oder Fehlerfall. Umfang und17 Gategruppen:
[Task-Family-Vertrag](../architecture/NATIVE_TASK_FAMILY_CONTRACT.md).
Dateipfade, ELF-Aufbereitung und Dienstpolitik bleiben außerhalb Ring0.

Der gemeinsame Mechanismus ist umgesetzt: zwölf neue Gastfälle bestehen,
216 native Tasklebensläufe und420 vollständige Frame-Retirements. Alte zehn
Programm-Gastfälle, normaler Bootstrap, i386-Pins und neun Hostgruppen
bestehen ebenfalls. Die abschließenden17 Gates und der lokale Commit werden
in der Queue festgehalten; konkrete Belege stehen im [Arbeitsstand](CURRENT_WORK.md).
Die nächste Inventur muss Ring3-Dienstintegration und wiederverwendbare
Start-/IPC-/Recoverypolitik verbinden, ohne Dateiparser oder Treiber nach
Ring0 zu verschieben. Ein weiterer Fehlerfall ist kein eigenes Paket.

## R8.3ad: ein vollständiger Bootprogramm-Schnitt

Nach der Abnahme `667e9aee` werden externe ELF64-Zulassung, vier eigenständige
C-Programme, Argumentstart, private Abbilddaten und Retirement gemeinsam
umgesetzt und geprüft. [Vertrag](../architecture/NATIVE_BOOT_PROGRAMS_CONTRACT.md).
Kein weiteres Paket je Layout, Argument oder Fehlerfall. Die nächste
Owner-/Start-/Wait-/Cancel-Grenze folgt erst nach sauberer Abnahme; Dateisystem,
Treiber und persistente Recovery werden nicht in diesen Bootvertrag gemischt.
Diese Bündelung ersetzt keine vollständige OS-Abnahme und keinen Ring3-Lader.
Der gemeinsame Kandidat enthält jetzt auch die über `f5357439` freigegebene
Timer-/IF-Korrektur. Sechs Hosttests, drei Builds, alle zehn neuen Gastfälle,
alte Laufzeitgäste, normaler Bootstrap und i386-Referenz bestehen. In sechs
Gästen ist der zuvor tödliche, anstehende IRQ0 direkt am PIC nachgewiesen.
Keine Frist-, CPU- oder Heapquotenlockerung. Der ausführbare Queue-Status ist
maßgeblich für die abschließende13-Gruppen-Abnahme und den lokalen Commit.

## R8.3ac: Laufzeit und vorhandene ELF-Seitenbelegung zusammenführen

Auf `42a41aba`, erweitert durch die erneute Nutzerfreigabe und Vertrag
`8483d0c5`: voller Zeitpfad statt256-Tick-Laufgrenze im expliziten
NativeRuntime-Profil. Timer, Schlafen, IPC-Timeout, CPU-Samples und Retirement
verwenden64-Bit-Ticks; der Zähler bleibt über unabhängige Runs erhalten.
Die gewachsene Ring3-Fixture nutzt eine zweite RX-Seite. Die bisherigen
Isolations-/Magic-/Faultpointerprüfungen beziehen ihre Datenseite daher aus
den bereits validierten ELF-Seitenrechten statt aus der festen VA0x401000.
Ein neuer Parser in Ring0 oder zusätzliche Startrechte sind nicht enthalten.

Die gemeinsame Abnahme umfasst normale Langzeitläufe, echte IRQs über2^32,
CPU-Ende bei weiterlaufenden Peers, Heap-/IPC- und vollständige Reapbelege.
Alte32-Sample-Quoten, Defaultprofile, private Aufbau4 und signierte Medien
bleiben unverändert; keine implizite Budget- oder Restart-Erneuerung.
Ergebnisse und historische Fehlversuche: [CURRENT_WORK](CURRENT_WORK.md),
[verbindlicher Laufzeitvertrag](../architecture/NATIVE_RUNTIME_CLOCK_CONTRACT.md).
Allgemeiner Programmstart, Ring3-Supervisor und native Dienste bleiben die
nächsten miteinander abzustimmenden Besitz-/Rechtegrenzen, nicht erledigte
Eigenschaften dieses Mechanismusnachweises.

## R8.3ab: native Medien und BIOS-Vertrauenskette gemeinsam

Nach `aac73e4f` ist der nächste große zusammengehörige Bootpfad eingefroren:
HDD und Rettungsfloppy, Signatur-/Inhaltsprüfung, Build-/Publikationsweg und
BIOS-Normal-/Fallback-/Fehlerbelege in einem13-Gate-Paket. Vorhandener Stage2
liefert schon Multiboot/E820 und unterstützt die ELF32-Hülle des ELF64-Kerns.
Kein neues Format oder Schlüssel, keine Wiederimplementierung dieser Logik.
[Verbindlicher Medienvertrag](../architecture/NATIVE_BOOT_MEDIA_CONTRACT.md).
Auf Vertrag `3a279429` umgesetzt: gemeinsamer Windows-/Make-Preset, beide
Medien mit identischem abgenommenen Kernel, signierter Hostindex und unabhängige
Rückleseprüfung bis zu den FAT-Dateiketten. Neun BIOS-Fälle bestehen; konkrete
Belege und Grenzen stehen im [aktuellen Arbeitsstand](CURRENT_WORK.md).
Darauf folgen Dateistart und Dienstintegration nach ihren Besitzgrenzen;
dieser Mediennachweis darf deren fehlende Laufzeitautorität nicht verdecken.

## R8.3aa: private virtuelle Regionen bis zum Retirement

Nach dem abgenommenen physischen Schnitt `d8b7e52f` wird der vorhandene
Prozess-Heap-Vertrag nativ angebunden. Eine Inventur zeigt die feste native
User-Pointertopologie und das vollständige synchrone13-Frame-Retirement;
beide benötigen einen expliziten Heapbesitz und begrenzte Fortsetzungen.
Syscalls, Mapping, Rollback, Realloc, Pointer-/IPC-Zulassung und Reap bilden
ein gemeinsames Paket mit14 Gates. Details:
[Native-Heapvertrag](../architecture/NATIVE_PRIVATE_HEAP_CONTRACT.md).

Der zusammenhängende Schnitt ist auf Vertrag `bdb033d8` implementiert;
konkrete Host-/Gastbelege und Grenzen stehen im [Arbeitsstand](CURRENT_WORK.md).
Gespeicherte Fortsetzungen verbinden Syscalls4/5/6, private Tabellen, IPC-
Pointerprüfung und vollständiges Terminal-Reap. Geschützte Belegungsbits
begrenzen Prüfkosten auf lebende Regionen.4/8GiB-Tests verwenden tatsächlich
hohe Frames und Folgegenerationen. Dies ersetzt noch keine native Dienst-
oder Userlandintegration. Nutzerweisung vom12. September: nächste Pakete als
größtmögliche kohärente Systempfade bündeln; unabhängige Sicherheits-, Besitz-
und Abnahmegrenzen bleiben getrennt. Kein Wechsel vor Abschluss der14 Gates.

## R8.3z: skalierbare physische Speichergrenze gemeinsam erweitern

Baseline `3e80a1c7`;14 Gates vor Umsetzung eingefroren. Die Inventur fand die
128MiB-Grenze nicht nur im Allocator, sondern in Bootübergabe, Reservierung,
Direct-Map, Frameclaims, Image-/Adressraumaufbau, Pointerprüfung und Reap.
Diese kompatiblen Verbraucher werden gemeinsam behandelt. Reihenfolge:
Hostregression; versioniertes begrenztes Metadatenareal; vorhandene RAM-Karte
und geschützte hierarchische Frameverwaltung; vollbreite Verbraucher; reale
1/4/8GiB-Gäste mit Frames oberhalb4GiB; abschließende Referenzen und Commit.
[Speichervertrag](../architecture/NATIVE_PHYSICAL_MEMORY_CONTRACT.md).
Keine per-RAM-Größe getrennten Pakete, keine ungeschützte Vergrößerung der
Bitmaps, keine RAM-weite Bitsuche je Allocation und keine neuen Prozessrechte.

Auf Vertrag `48c47a09` umgesetzt:16GiB physischer Adressraum mit geschützter
hierarchischer Verfügbarkeit, versioniertem C-Areal und vollbreitem Besitz
bis zum Reap. Reale1/4/8GiB-Gäste bestehen mit ursprünglichem10s-Limit je Gast,
24 Tasklebensläufen,75 Frame-Retirements und drei abgewiesenen Bootkarten.
Das30s-Limit im zwischenzeitlichen Prüfer wurde im Abschlussreview entfernt.
Belege und Grenzen stehen im [aktuellen Arbeitsstand](CURRENT_WORK.md).
Der darauf aufbauende Heapbesitz einschließlich Mappingrechten, OOM-Rollback
und generationsgebundenem Reap wird gemeinsam in R8.3aa behandelt;
physische Kapazität allein stellt diese Rechte nicht bereit.

## R8.3y: kompatible IPC-Nachrichtenformate vervollständigen

Baseline `89ab012f`, dreizehn Gates vor Umsetzung eingefroren. Inventurkorrektur:
Bulk benutzt schon50/51/53/54, nicht neue Syscallnummern. Ein breiteres Profil
ist dafür nicht nötig. Die alte Annahme im X-Vertrag bleibt als korrigierte
Historie sichtbar. Reihenfolge: Regression; Header-/Seitenprüfung; private
v2-Snapshots mit erhaltener Empfangskapazität; tatsächliche Ring3-Transfers
und Fehler-/Reapprüfung; Commit. Keine neuen Rechte oder gemeinsamen IPC-
Verfahren. Zusätzliche Integritätsarbeit nur für aktive große Aufträge.

Umgesetzt auf Vertrag `0068bdaf`: private2136Byte-Anfrage,2144Byte-Pending-
Datensatz und2144Byte-skrubbender Stackslot. Immer zuerst geschützte Metadaten,
dann140Byte-Präfix; zusätzliche1920Byte nur bei aktivem Bulkauftrag. Eingaben
bleiben kopiert, Empfangskapazität bleibt2060 auch bei zurückgegebenem v1.
Keine Kernelparser, weiteren Syscallrechte oder Änderung am gemeinsamen Kern.

V1: vier Gastfälle/32Tasks,78 Warteabschlüsse,112 Copyouts,58,708s.
V2: vier Gastfälle/32Tasks,73 Warteabschlüsse,64 vollständige2060Byte-Copyouts
über Seitengrenzen,60,949s. Besitzer-UD2, Peer-Release, CPU-Grenze und zweite
Generationen sind in beiden Matrizen belegt; je32 Fences und100 Frame-Reaps.
17 Kernobjekte sind zwischen sämtlichen Userfällen identisch. Host-O0/O2
prüft zusätzlich gemischte FIFO-/Bulk-Priorität,0/128/2048Byte, isolierte Kopien,
falsche Größen, Timeout/Reap und beschädigte Bulk-/Kapazitätssnapshots.

Fehlbelege bleiben erhalten: fehlende v2-Bindung; zunächst um69Byte zu großes
Fixture-Textsegment verletzte den alten Testvertrag mit Datenseite1; danach
verbrauchte der Prüfer sein10s-Limit mit byteweisen Debuggerabfragen. Fixture
komprimiert und dieselben vollständigen Nullprüfungen in drei Lesezugriffen
gebündelt; weder Gastlimits noch geforderte Prüfungen abgeschwächt.
Kein voller64-Bit-Systemabschluss. Nach akzeptiertem Commit folgt der nächste
zusammenhängende native Schnitt aus sauberer Baseline.

## R8.3x: IPC-Pools, Syscalls und Wartelebensdauer gemeinsam

Baseline `b90c2cab`; dreizehn Gates vor Umsetzung eingefroren. Der vorhandene
C-IPC-Kern wird mit kleinen expliziten nativen Prozessansichten verbunden,
nicht mit einem Cast auf die historische große `Process`-Struktur. Seine
Pool-/Handle-/Nachrichtenverfahren und der optimierte Integritätskern bleiben
erhalten. Nur die Plattformbindung wird architekturspezifisch.

Reihenfolge innerhalb dieses einen Pakets: Hostregression und Bindungsvertrag;
vorhandene Pools nativ linken; explizite Syscallrechte und geprüfte Kopien;
asynchrone Aufträge/Deadline-/Ereignisabschluss; Fencing vor Reap; reale
unabhängige Ring3-Paare einschließlich Fehlern und Wiederverwendung prüfen.
Der gemeinsame Kernelstack verbietet das Übernehmen schlafender C-Fortsetzungen.
Deshalb nutzt der Adapter die alten Operationen nichtblockierend und hält
höchstens vier kopierte Aufträge. Das ist keine Pollingschleife: Arbeit erfolgt
nur bei IPC-Ereignis, Taskende oder endlicher Deadline, außerhalb des IRQ-Bodys.

V1 behält16 Endpunkte,64 globale/8 lokale Capabilities,4 Nachrichten und128Byte
Nutzlast, abschwächende Delegation ohne CONTROL, EAGAIN/ETIMEDOUT/EPIPE/EBADF.
Bulk benutzt dieselben Syscalls, wurde in X aber noch nicht angebunden;
die frühere gegenteilige Planannahme war falsch. Weitere
Speicher-/Dienst-/Userland-Portierung folgt erst nach akzeptiertem Commit.

Umsetzung auf `27d5b50c`: dieser gesamte IPC-Schnitt ist gemeinsam gebaut und
im echten Ring3 geprüft, nicht in weitere Pool-/Timeout-/Fehlerpakete geteilt.
Vier Userfälle mit32 Tasks zeigen normale Kommunikation, Besitzer-UD2,
Peer-Freigabe und CPU-Begrenzung;78 Warteabschlüsse,112 adressraumgebundene
Copyouts und32 Fences vor Reap sind unabhängig beobachtet. Die neue Plattform
verwendet weder alte schlafende C-Stacks noch Spin-Retries. Bereits geschlossene
Endpointgenerationen bleiben erhalten; Prozessansichten und ausstehende
Nachrichten sind vor Freigabe des jeweiligen privaten Adressraums null.
Unzugängliche alte Queue-Speicherbytes werden nicht als forensisch gelöscht
ausgewiesen. Shared-IPC-Verfahren und Integritätsarithmetik bleiben quellgleich.

Effizienzkorrekturen aus der Abnahme: Timerarbeit erst bei fälliger Deadline,
keine Nachrichtenpolls auf Uhrticks; vorhandene32-Sample-Grenze für das längere
IPC-Testprofil nutzen, alte Profile unverändert; Produktions-TU zusätzlich
getrennt auf die tatsächliche Speicherbreite redundanter Kontrollwörter prüfen.
Ein in die Fehlertest-TU eingebundener C-Kern allein erfasst die anders
optimierte Produktionsübersetzung nicht. Fehlercode-Präzedenz der Nachrichten
bleibt beim gemeinsamen Kern, kein zweiter fast gleicher Validator im Adapter.

Normalbild samt User-ELFs bleibt byteidentisch; alte Prozessmatrix und
Frame-/i386-Guards bestehen. Vollständige Zahlen und Belegpfade stehen im
[aktuellen Arbeitsstand](CURRENT_WORK.md). Die Auswahl des nächsten großen
nativen Schnitts erfolgt erst nach Abnahme und sauberem lokalen Commit.

## R8.3w: vorhandenen Integritätskern übernehmen

Nach R8.3v `12f93954`: Die vorhandene IPC-Implementierung hängt am gemeinsamen
SECDED-/CRC-Integritätskern. Dessen reale native Übersetzung scheitert derzeit
an `push/pop %eax` im IRQ-Save/Restore; Beleg unter
`build/codex-agent/r83w-integrity-inventory/compile-before.log`. Der gemeinsame
x86-Header erhält native Stackbreite bei unverändertem32-Bit-Statustoken,
während sein i386-Präprozessor-/Codepfad exakt erhalten bleibt. Die bestehenden
Integritätsalgorithmen und Leistungsoptimierungen werden nicht neu geschrieben.
Optionaler `-CIntegrityProbe`-Gast prüft den tatsächlichen gemeinsamen C-Kern
mit Bitfehlern, unabhängiger Kopie, doppelter/semantischer Korruption, endlichem
Busyfehler, IRQ-/Stackerhalt und vollständiger Bereinigung. Elf fixierte Gates;
erst danach allgemeine IPC-Pools. Keine neue native Userspace-Lock- oder
SMP-Abnahme durch einen Boot-Selbsttest behaupten.

Umgesetzt auf `16328ec8`: i386-Präprozessor und tatsächliches Integritätsobjekt
bleiben identisch; die vorhandenen gemeinsamen C-Quellen bleiben unangetastet.
Der native Gast besteht1650 Leseprüfungen einschließlich1560 Bitkorrekturen,
80 Wiederherstellungen und aller Ablehnungs-/IRQ-/Cleanupfälle in1.681s.
GDB liest zwölf Kontrollpunkte und zwei reale C-Aufrufe/Rückkehrstellen.
Das normale native Bootabbild bleibt byteidentisch zu R8.3v; die bisherigen
Prozess-/Reap- und gepinnten i386-Gates bestehen. Neue fünf Hosttests sowie
die unveränderten Integritäts-/Kostenprüfungen unter O0/O2 sind grün.
Der eingefrorene Scope verändert weder die SECDED-/CRC-Arithmetik noch den
existierenden begrenzten Publikations-Lock. Dessen Eignung für einen neuen
nativen Userspace-IPC-Pfad muss bei jener Anbindung getrennt nachgewiesen werden.

## R8.3v: mehrseitiger nativer C-Payload

Nächster zusammenhängender Schnitt nach `df6b82ac`: R8.3v beseitigt vor der
allgemeinen IPC-Portierung die Einseiten-/32Byte-C-Payloadgrenze. Ein eigener
nativer ELF64-Linkerplan und Buildzeitprüfer verbinden mehrere C-Objekte mit
begrenzten RX/R-NX/RW-NX-Sektionen; Größen, BSS-Initialisierung und Bridge-
Symbolbindungen werden aus dem tatsächlichen ELF überprüft. Mehrseitiger
ausführbarer C-Testpayload plus reale Paging-/BSS-Nachweise sind Bestandteil
derselben zehn Gates. Keine größere physische RAM-Zulassung und keine
Aufnahme von Treibern/Protokollpolitik in Ring0. Danach ist der allgemeine
IPC-Autoritäts-/Lebensdauerschnitt wieder der nächste Kandidat.

Umsetzung auf Vertrag `9b8cd75e`: tatsächlicher Mehrmodul-Link und strikt
begrenzter ELF-Buildprüfer; Layout v2 ist im Bootstrapvertrag beschrieben.
Der Gast führt mehrseitigen C-Code aus und prüft alle Konstanten-/Datenbytes,
genulltes, danach beschriebenes und wieder bereinigtes BSS. Vorherige gezielte
BSS-Vergiftung beweist die Bootinitialisierung unabhängig vom Multibootloader.
Zwei read-only Pagingbeobachtungen bestätigen13 belegte und111 nichtpräsente
Seiten, WP/NXE und keine direkten Bootstrap-Aliase. Elf neue Hosttests2.088s,
Mehrseitengast0.672s; bestehende Prozessmatrix56.444s und Frame-Reap1.882s
grün. Normale User-ELFs und gepinnte i386-Artefakte unverändert. Keine
physische Speichererweiterung, geänderte User-ABI oder produktive OS-Abnahme.
Alle zehn eingefrorenen Kommandos und Transaktionsstatus stehen in der Queue.

## R8.3u: unabhängiger nativer Prozesslauf

Aktuelle Fortsetzung auf Erfolgscommit `3a8c97d2`: R8.3u bündelt allgemeine
Taskzulassung, unabhängige Lebensdauern, Scheduling/Deadlines und gemeinsamen
individuellen Reap in einem Paket statt einzelner PID-/Syscallfälle. Das optionale
native Prozessprofil nimmt versionierte feste1..4-Task-Deskriptoren an, mit
explizitem Syscallmasken-/CPU-Budget pro Task. Unabhängige Peers überleben den
Userfehler eines Tasks. Generationen bleiben über aufeinanderfolgende zugelassene
Läufe monoton; Slotwiederverwendung erteilt keine alten Rechte. Vierzehn Gates
prüfen Hostverhalten, echte Gäste und unveränderte i386-Referenzen. Der bisherige
Bootstrap bleibt Standard; allgemeine Endpoints, skalierbarer Speicher, Ring-3-
Loader/Supervisor und echte Dienste bleiben nachgeordnete eigene Grenzen.

Umsetzung12.September: `process_run.inc` ist der vom Gast benutzte gemeinsame
Adapter, keine ungenutzte Metadatenbibliothek. Der feste C-Bootkoordinator lässt
zwei unabhängige Vierergruppen desselben eingebetteten Demo-ELFs nacheinander
zu; die Kernelmechanismen kennen weder Demoargumente noch Sollstatus oder
Fehlertestnummern. Neun Uservarianten bestehen mit72 Taskabschlüssen, zusätzlich
fünf read-only GDB-Läufe mit40 Taskabschlüssen und125 Gesamt-Frame-Reaps,
einschließlich85 unveränderter früherer Bootstrap-Reaps (46.192s). Gemeinsame
Generationen, Queue, Deadline, Profil, Kontext, Budget und Frame/FP-Kerne bleiben
wiederverwendet. Hostzulassung und Wake-Übergänge laufen O0/O2, mutierte
Besitz-/Queue-/Profil-/Framezustände lehnen ohne Mutation ab. Bestehende
Eigentümer-, Request-, Frame- und i386-Referenzgates sind unverändert grün.
Die Ausführung ist weiterhin optional und begrenzt; `-NativeProcesses` besitzt
einen eigenen privaten Kontroll-Service2 und eigenen Abschlussmarker, statt
eine nicht gestartete Shell als erfolgreich auszugeben. Endpoints, mehr RAM,
produktiver Ring-3-Loader/Supervisor und echte Programme sind noch offen.

## R8.3t: Eigentümerabschluss mit abhängigen Prozessen

Nachfolgepaket R8.3t auf `af9ec117`: gemeinsamer Eigentümer-Terminalpfad für
EXIT, Fault, unbrauchbaren Userkontext und CPU-Budget, einschließlich aller
abhängigen Kind-/IPC-Zustände. Das bisherige eingebaute Bootstraplaufprofil
erhält eine ausdrückliche kurzlebige Eigentümer-/Kindbindung: Kein Kind ist
als unabhängiger Dienst zugelassen. Fencing/Reap dieses begrenzten Laufs ist
ein Mechanismus, keine allgemeine Orphan-, Restart- oder Supervisorpolitik.
Unabhängige Prozesse dürfen nicht stillschweigend als Abhängige umgedeutet
werden. Der spätere Ring-3-Supervisor braucht eigene Zulassung und Nachweise.
Bestehende Queue-, Deadline-, Profil-, Identitäts-, Frame- und FP-Mechanismen
werden wiederverwendet. Vierzehn eingefrorene Gruppen prüfen Host und reale
Gäste; 32-Bit-Referenzen bleiben gepinnt. Kein vorgezogener Geräte-/GUI-Port.

Umsetzung12.September:52 Dialoge und fünf zusätzliche rein lesende GDB-
Beobachtungen bestehen, einschließlich CPU128, ungültiger SYSCALL-/IRQ-Kontexte,
IPC-blockierter und schon gereapter Kinder. Die Besitzprüfung läuft als echte
Assembly O0/O2; unbekannte Generationen, fremde Queue-/IPC-Bindungen und
Framealiasierung werden vor Effekten abgelehnt. Default-User-ELFs unverändert.
Das freigegebene Timerscope-Delta ist in Vertrag `23ee459e` festgehalten:
Die3e9-TSC-Zyklen sind nun nur für SHELL eine validierte Fortschrittslease,
nicht eine frequenzabhängig zu kurze Gesamtfrist. Maximal256 PIT-Ticks sowie
128/32 CPU-Samples bleiben fest. Hosttests prüfen reale Lease-Arithmetik,
die alten Fatalbelege bleiben sichtbar. Kein unabhängiger Hardwarewatchdog-
oder vollständiger OS-Claim. Bestehende30 Exitdialoge,20 Frame-Reaps,
24 Faultfälle/48 Generationen und drei Requestfälle/sechs Generationen sind
ebenfalls grün; i386-Referenzguard bestätigt die unveränderten Artefakte.
Abnahmekommandos und endgültiger Transaktionsstatus stehen in der Queue.

## R8.3s: geordneter Shellabschluss unabhängig vom Testdialog

Basis1e7645c8, Vertragdcbfb4d8.
Nutzerunterbrechung12.September: R3.46 Anzeige-Checkboxen wurde vorgezogen,
einschließlich freigegebener Boot-Vorbereitung vor den Selbsttestfristen.
Noch keine native Produktionsänderung. Vorbereitete eigene Hosttests unter
`build/codex-agent/r83s-shell-exit/paused-draft/`, echter Host-Rotbeleg
`01-host-red.log`; nach R3.46-Abschluss wieder aktives Paket. Die Umsetzung
wird als eigene Transaktion auf sauberem Commitstand neu aufgenommen.

Umsetzungsstand nach Wiederaufnahme: Der geordnete Abschluss ist implementiert.
Der vorherige Absatz beschreibt den archivierten Unterbrechungsstand. Frühes
EXIT des alten Artefakts liefert reproduzierbar STAGE_54/C_KERNEL_CONTROL_ERROR;
mit der Korrektur bestehen 30 Dialog-/Statusfälle. Volle uint32-Statuswerte
und sechs ungültige Argumentkombinationen werden rein in Userspace geprüft,
ohne zusätzliche Schreibquoten oder Testselektoren im Kernel. Der O0/O2-Test
prüft die reale Abschluss-Assembly byteweise auf unveränderten Zustand;
die festen vier Identitätsslots werden nun ebenfalls ausdrücklich geprüft.
Default-Shell, Kind und Probe bleiben byteidentisch. Alle elf eingefrorenen
Gruppen bestehen, einschließlich der unveränderten 24 Faultfälle mit
48 Generationen, des Frame-Reap-Nachweises und der Request-/IPC-Regression.
Die fehlgeschlagenen Zwischenläufe bleiben erhalten. Direkte Diff-/Scopeprüfung
und lokaler Commit bilden die Transaktionsgrenze zum nächsten nativen Paket.

Freigegebene Abnahmeergänzung12.September: Der historische JS-Prüfer meldet
auf dem abgenommenen `7bd4bef0` bereits `kernel drift: main-vmware`, weil
R3.46 die Bootvorbereitung absichtlich korrigiert hat. Ein eigener nativer
Referenzprüfer schützt jetzt den aktuellen i386-Stand und das historische
Framebufferartefakt getrennt durch fest gepinnte SHA-256-Werte. Aufnahme vor
nativen Änderungen, kein automatisches Neubaselining; gesperrte, fehlende oder
veränderte Artefakte sind Fehler. Ein zusätzlicher Regressionstest prüft
Manipulation, fehlende Dateien und Inventardrift. Historischer JS-Prüfer und
Nachweise bleiben unverändert. Die übrigen nativen Gates bleiben eingefroren;
insgesamt elf Prüfgruppen. Eine laufende Benutzer-VM wird nicht beendet.

Frühes EXIT scheitert derzeit an exakt18 gelesenen Zeichen,
acht Schreibaufrufen und zwei Kindern, auch wenn keinerlei fremder Besitz
mehr besteht. Zusammenhängender Schnitt: null/ein/zwei vollständig gereapte
Kinder, uint32-Rohstatus und lokale Ablehnung ungültiger EXIT-Argumente.
Die I/O-Zahlen bleiben Obergrenzen. Ereignisfolge, Reapanzahl und letzte
Generationen werden aus validierten Abschlusszahlen abgeleitet; sämtliche
Null-/Ressourcenprüfungen bleiben. Fehlerstatus ist Programmfehler, nicht
Kernelkorruption, muss aber jeden bisherigen Normaltest weiterhin ablehnen.

Reihenfolge: alte Assembly/echten Gastfehler erhalten; regressionsfähiger
Hosttest des tatsächlichen Abschlussprüfers; Kernelanbindung und reine
Userspace-Fixtures; elf eingefrorene Host-/Build-/Gast-/Doku-/i386-Gruppen.
Keine neue API oder Testlogik im Kernel. Elternende bei lebendem Kind oder
Endpoint samt Orphan-/Gruppen-Recovery ist eine separate destruktive Politik
und bleibt ausdrücklich offen; der bestehende Fail-closed-Pfad wird dafür
nicht als vollständige Prozessisolation ausgegeben.

## R8.3r: Ausführungs- und Rückkehradressen im eigenen Task

Nach ab3b5531 schließt Vertragb8339cd7 die separate Rückkehr-Autoritätsgrenze.
Realer Altgast: legaler YIELD von0x401000 wird an Rückkehr0x401007 fälschlich
retired, weil die ausgewählte Shell nur die erste RX-Seite besitzt. Der
gemeinsame Tabellenprüfer erhält eine Einbyte-PF_X-Abfrage mit P/U und NX
über alle Ebenen. Syscall-Rückkehr und Kontextaufnahme/Timer werden gemeinsam
angebunden; IRQ-Retirement bleibt nach EOI. Keine Änderung von ELF-Lader,
Rollenpolitik, Mappingrechten oder öffentlich sichtbarer ABI.

Reihenfolge: Host-Rot und echter alter Gast; Produktionskern/Adapter;
Hostmatrix aller36.864 Instruktionspositionen zusätzlich zu den Datentests;
drei echte Zweitseiten-Fixtures (YIELD, CPU-Spin, Rückkehr ins Loch), je zwei
Generationen. Alte Kontext-, Fault-, CPU-, NX-, Datenpuffer- und Reap-Matrizen
bilden mit Build/Host/Doku/i386 insgesamt15 eingefrorene Gruppen.
Normaler Userspace bleibt unverändert, Fixtureunterschiede nur im Userabbild.
Ergebnisse und verbleibende Systemgrenzen in [CURRENT_WORK](CURRENT_WORK.md)
und Queue. Detailzeiten in den Belegen; Implementierungszeit nicht separat
gemessen. Kein Routine-Clean und keine Änderung alter Prüfanforderungen.

## R8.3q: gemeinsame taskgebundene Userpuffer-Zulassung

Nach Buildreparatur1aabfd50 ist dies der nächste zusammenhängende native
Speicherzugriffsschnitt, Vertrag9af7a87e. Die alten global ausgewählten
ELF-Seitenflags sind kein zuverlässiger Beleg für den gerade laufenden Task.
Terminal und IPC erhalten deshalb gemeinsam eine read-only Prüfung der
tatsächlichen generation-/CR3-gebundenen Seitentabellen. Keine Erweiterung
der Geräte-, Prozess-, Speicher- oder Scriptrechte.

Reihenfolge: alten falschen Imagebezug ausführbar erhalten; gemeinsamen
SysV-AMD64-Kern mit tatsächlicher Assembly O0/O2 prüfen; vorhandene
Terminal-/IPC-Pufferadapter anbinden; getrennte R/NX-Kinddaten über eine
Seitengrenze real per IPC transportieren, Loch als EFAULT ablehnen; normale
zwei Generationen mit WAIT/Reap und unveränderten Kernmechanismen nachweisen.
Alle36.864 Bytepositionen, beide Zugriffsrichtungen, Zwischenebenenrechte,
Überlauf/Null/Stale/CR3/Frame-/Backendfehler und Nichtmutation gehören zusammen.

Risikobasierte13 Gruppen statt ungezielt übernommener historischer Vollmatrix:
neue Host-/Gastgruppe, vorhandene Mapping/Request/Boot/IPC-Observer-Hosts,
normaler Build, Request-/Mapping-/IPC-/Task-Reap-Gäste, i386-Guard und Doku.
Kein bestehendes Oracle oder Zeitbudget wird abgeschwächt. Normaler Userspace
bleibt bytegleich; nur User-Fixture4 besitzt die größeren Testdaten.
Verbindlicher Abnahmestand in der Queue und [CURRENT_WORK](CURRENT_WORK.md).
Implementierungs-/Diagnosezeit nicht separat gemessen; Build-/Testzeiten in
den vorhandenen Logs, keine geschätzte Zeit als Messwert. Allgemeine Rollen,
RIP-/Startparameterbindung, Endpoint-Pools und großer RAM bleiben offen.

## R8.3p: gemeinsame validierte Task-Frame-Freigabe

Basis a0f919a3 (R8.3o, alle25 Gruppen abgenommen). Der bisherige
Task-Cleanup gibt Frames einzeln frei und erkennt doppelte Metadaten erst
nach dem ersten Effekt. Vor allgemeiner Prozess-/Speicherzulassung braucht
der zusammenhängende Freigabe-/Rollbackpfad dieselbe Vorabvalidierung wie
Mapping und Imagebesitz. Keine Erweiterung von Kapazität oder Recoverypolitik.

Privater32-Byte-SysV-AMD64-Bindungsrecord: Pointer auf acht Privatframes,
Stackrecord, vier Tabellenframes und CR3record. Alle Recordbereiche, maximal13
Frame-IDs und die CR3/PML4-Beziehung vor Freigabe prüfen. Nur erfolgreiche
Freigaben löschen ihren Record; erster Backendfehler stoppt und erhält den
Restbesitz. Freiframe-Delta je Aufruf prüfen, kein Vergleich mit einem alten
globalen Ladebestand. Endgültige FP-Nullung, Profil-/Budget-/Identitätswiderruf
und Generationen bleiben verpflichtend. Kernelkorruption bleibt fatal.

Reihenfolge: tatsächlichen alten Duplicate-after-free-Fehler erhalten;
Produktionsassembly O0/O2 mit8192 Sparse-Belegungen, allen Fehlerpositionen,
Nichtmutation, Restbesitz/Idempotenz und unabhängigen Eigentümern prüfen;
alle Task-Freigaben/Rollbacks anbinden; echte Gast-Receipts inklusive
FP-/Tabellen-/Privat-/CR3-Nullung und Elternfortschritt. Alle25 bisherigen
Gates plus neuer Host-/Gastnachweis zunächst27 Gruppen; genehmigter
IPC-Beobachternachtrag d227a3ef ergänzt einen Hosttest auf insgesamt28.
User-ELFs bleiben gegenüber
a0f919a3 bytegleich,1CPU/128MiB/vier Slots/zwei Kinder und Zeitbudgets gleich.
Belege build/codex-agent/r83p-retirement. Keine vollständige OS-Fertigmeldung.

Produktionskern und20 reale Task-Freigaben geprüft. Der genehmigte IPC-Prüfer
paart Eintritt/Rückkehr über Hardware-Haltepunkte und prüft echte CALL-/CMP-
Instruktionen, Stack, Identität, Eingaben und Resultat. Explizites Einzelschreiten
der nicht verzweigenden Vergleichsinstruktion verhindert unkontrolliertes
Fortsetzen direkt auf dem scharfen Haltepunkt. Keine Duplikatfilterung und
keine Lockerung des alten exakten Branch-/Count-Oracles. Alle vier neuen
IPC-Gastfälle bestanden; alte Fehlbelege bleiben erhalten.27 Code-/Build-/
Laufzeitgruppen grün, Dokumentationsgate/Paketabschluss in der Queue.
Prüferumfang, unveränderte Abnahmeanforderungen und erhaltene Belege stehen
in [CURRENT_WORK](CURRENT_WORK.md#r83p-validierte-task-frame-freigabe-und-rollback).

## R8.3o: gemeinsamer validierter Adressraumaufbau

Basis0e2d95c6. Der bestehende Taskaufbau benutzt den global gewählten
ELF-Kontext direkt und lehnt gültige PF_R-Seiten ohne PF_X ab. Vor allgemeiner
Programmzulassung wird diese Mappinggrenze zusammenhängend repariert:
expliziter physischer Plan statt Rollen-/Parserabhängigkeit im Mappingkern.

Privater192-Byte-Plan: vier Tabellenframes, acht Quellframes mit ELF-Flags,
acht optionale private Schreibframes, Stack und zwei bestehende geschützte
Kernel-PML4-Einträge. System V AMD64; Intel64-Vier-Level-Paging. Alle maximal
21 nichtleeren Frames, Flagklassen, Überläufe, Eindeutigkeit, Pointerabbildungen
und leeren Zielseiten vor dem ersten Schreibeffekt prüfen. RX und R bleiben
geteilt und schreibgeschützt; R ist NX. RW wird privat kopiert und ist NX,
ebenso der private Stack. Lücken/Guards bleiben ungemappt, Kernel bleibt
Supervisor-only. Bestehende Quoten, Claim-/Rollback-/Reap- und Bildlebensdauer
bleiben bestehen; keine Allokation oder ELF-Policy im gemeinsamen Mappingkern.

Reihenfolge: echte R-Daten-Fixture als erhaltene Vorher-Regression; tatsächlichen
Assemblykern mit kontrolliertem Hostbackend O0/O2 und Nichtmutation prüfen;
alle bisherigen Taskaufbauten anbinden. Drei exklusive reine User-Fixtures
beweisen R-Lesen, abgefangenen Schreibzugriff auf R und abgefangene Ausführung
von R/NX, je zwei Generationen und weiterlaufende Eltern-Shell. Read-only-
Gastbelege prüfen die echten Tabellen und Privat-/Sharedbesitz zusätzlich.
Danach sämtliche22 bisherigen Gruppen; ursprünglich24 eingefrorene Gategruppen.
Belege build/codex-agent/r83o-mappings. Der genehmigte Nachtrag2e963b34
erlaubt ausschließlich begrenzte IPC-Retries im normalen Usercode und ergänzt
deren tatsächlichen Host-Verhaltenstest: insgesamt25 Gruppen. Alle bisherigen
Gates und Kernelrechte/-deadlines/-budgets bleiben unverändert.
Dies ersetzt noch keine allgemeine Eltern-/Supervisor-Recovery oder native
Dienste. Unverändert1CPU/128MiB/vier Slots/zwei Kinder und alle Zeitlimits;
R3.6b bleibt zurückgestellt, keine vollständige64-Bit-Fertigmeldung.

Historischer Zwischenstand R8.3o: Mappingkern und alle drei R/RX-Gäste funktionieren;
21/24 Gruppen bestanden. IPC-Handoff-Fall0 ist rot, derselbe Fehler wurde
im unveränderten Vorgänger0e2d95c6 reproduziert und ein regulärer Sendetimeout
(-110) als Ursache des Testkind-Fehlers78 beobachtet. Die letzten beiden
Gruppen sind noch offen. Kein Kandidatencommit oder Abschluss: die im Paket
eingefrorene Bytegleichheit der normalen Testprogramme darf nicht still
aufgegeben werden. Inzwischen explizit genehmigter Vertragsnachtrag und Belege in
[CURRENT_WORK](CURRENT_WORK.md#r83o-gemeinsame-mappingprüfung-und-schreibgeschützte-daten).

Die genehmigte Reparatur ist umgesetzt: begrenzte Peer-Receive-Retries und
EACCES/ETIMEDOUT-Behandlung beim Warten auf CLOSE; ausschließlich EBADF
bestätigt den Widerruf. Tatsächliche Fixturefunktionen bei O0/O2 geprüft.
Die erneuten24 Code-/Build-/Laufzeitgruppen bestehen, einschließlich aller
vier unveränderten IPC-Interleaving-Oracles; Dokumentationsgate separat vor
Commit.19 Mechanismen über74 Builds identisch, alte17 unverändert;
Kernelobjekte vor/nach Fixture-Reparatur sämtlich bytegleich. Normalbild
187344 Bytes. Keine neue Kapazität/Autorität oder vollständige OS-Fertigmeldung.

## R8.3n: unabhängige Lebensdauer gestagter Programmabbilder

Basisb9b82a5a: Der ELF-Cleanup vergleicht nach Freigabe noch mit dem globalen
Freiframebestand vom Ladezeitpunkt. Später geladene unabhängige Bilder oder
andere lebende Frames machen diesen Vergleich falsch. Die gemeinsame
Eigentumsgrenze wird repariert, nicht die Kapazität künstlich vergrößert.

Bestehender88-Byte-Kontext, maximal8 Frames, private System-V-AMD64-Schnittstelle.
Vor Freigabe Frame-/Flag-/Eindeutigkeitsmetadaten prüfen, nur eigene Records
freigeben und den Delta-Freizähler der tatsächlich erfolgreichen Freigaben
innerhalb IF0 prüfen. Fehlgeschlagene Freigaben behalten ihren Besitz,
Teilfortschritt wird explizit gespeichert, Wiederholung gibt nichts doppelt
frei. Beschädigte Kernelmetadaten sind kein ENOMEM. Der alte Ladefreizähler
bleibt Diagnose; Gesamtbilanz am Bootstrap-/Spawn-/Reap-Ende bleibt Pflicht.
Konsumenten müssen weiterhin vorher gefenced/geerntet sein; keine neue
Shared-RX-Referenzzählung oder allgemeine ELF-/VFS-Autorität.

Reihenfolge: Gastregression für den bisherigen Fehler erhalten; tatsächlichen
Freigabekern mit kontrolliertem Hostbackend O0/O2 prüfen; Loader anbinden;
alle drei gestagten Abbilder und einen unabhängigen Canaryframe im Gast
in allen sechs Freigabereihenfolgen prüfen; dann alle bestehenden Matrizen.
Neue Gäste beweisen Frame-/Inhaltserhalt und18 unabhängige Bildfreigaben,
nicht bereits parallele Ring3-Dienste oder skalierbares RAM.
22 eingefrorene Gategruppen, Belege build/codex-agent/r83n-images.
Unverändert:128MiB/1CPU/vier Slots/zwei Kinder, alle Zeit-/Ressourcenlimits,
i386-Referenz, R3.6b-Zurückstellung und offene Hardware-/Systemabnahmen.

Abnahme R8.3n: alle22 Gruppen bestanden. Vorher-Gast belegt den falschen
Ladebestand32343 gegen32340 nach Freigabe bei fremdem Restbesitz. Neuer
Freigabekern O0/O2 über256 Belegungen und1024 einzelne Backendfehler;
Restbesitz/Retry und unveränderte Nachbarn geprüft. Neuer Gast sechs
Permutationen/18 Freigaben mit Read-only-IF0-/Freizählerbelegen in0.843s.
Normalbild177300 Bytes; normale IPC0-Kinder bleiben Exit77 (echte RIP),
nicht Exit91 aus der IPC1-Fixture.18 Mechanismen über71 Builds bytegleich,
alle bisherigen17 Mechanismen und normalen User-ELFs gegenüber R8.3m
unverändert. Sämtliche alten Gastmatrizen und i386-Guard bestanden.
Ein alter Quelltest grenzt den Allokationspunkt jetzt ausdrücklich auf den
Lader statt den vorgeschalteten Canary-Selbsttest ein. Negative Vorher- und
Prüferbelege bleiben erhalten. [Abnahmebelege](CURRENT_WORK.md#r83n-unabhängige-freigabe-nativer-programmabbilder).

## R8.3m: gemeinsamer Lebenszyklus der Syscall-Profile

Basis31b6395b: Identität/Queues sind bereits private wiederverwendbare Kerne.
Installation, syscallseitige Prüfung, IRQ-Prüfung und Widerruf von Profilen
duplizieren dagegen Masken-/Generationslogik im Scheduler. Diese eine
Autoritätsgrenze wird in einem gemeinsamen Assemblykern zusammengeführt.

Bestehende16-Byte-Profile bleiben kompatibel. Privater32-Byte-Descriptor:
Taskpointer, Profilpointer, erwartete Generation, explizite Vertrauensmaske.
Keine Rollen/PIDs, Userpointer, Allokationen oder impliziten Rechte im Kern.
Installation nur RESERVED, Syscallabfrage nur RUNNING, Widerruf vor
Framefreigabe nur aus terminaler/reservierter Generation. Ein bereits leeres
Profil darf nur bei unverändertem Taskbesitz idempotent widerrufen werden.
IRQ prüft dieselbe Bindung. Eine verweigerte Nummer liefert lokal EACCES;
beschädigte Bindung/Masken sind Kernelkorruption. Volle64-Bit-Nummer vor
Bitabfrage prüfen. Bestehende Rollenpolitik bleibt ausdrücklich im Adapter.

Abnahme20 Gruppen: tatsächlicher Kern O0/O2 mit beliebigen Generationen und
Masken, Guard-/Nichtmutation-/Alias-/Lebenszyklusfällen. Im Gast prüfen beide
Rollen alle nicht freigegebenen Nummern0..63 und High-Bit-Nummern, dann den
normalen IPC/WAIT/Reap-Verlauf. Read-only-GDB protokolliert die echte
Installation/Abfrage/Freigabe; Kernelmechanismen bleiben fixtureunabhängig.
Alle bisherigen Matrizen und i386-Guard bleiben unverändert. Belege unter
build/codex-agent/r83m-profiles. Keine neue Prozesskapazität/Autorität,
keine allgemeinen Dienste oder Supervisor-Recovery aus diesem Nachweis.

Abnahme R8.3m: alle20 Gruppen bestanden. Neuer Host4/1.413s, alter
OOM3/0.924s, Requests3/1.044s, Bootstrap55/0.041s, Startup4/1.420s,
Exit3/0.957s, Context2/1.150s. Profilgast222 verweigerte Aufrufe/
444 Eintrittsbeobachtungen und sechs Profilübergänge in5.443s bestanden.
Normalbild175440 Bytes; alte Shell-/Kind-ELFs unverändert und das gesamte
Normalbild aus abschließendem Quellstand bytegleich zum ersten Normalbuild.
OOM6/12 in8.499s, Requests3/6 in9.243s, Argv4/8 in12.012s,
Exit24/48 in71.449s, Fault24/48 in68.358s, Busy2/4 in6.503s,
Context7/14 in20.947s, IPC4/8 in13.138s.17 Mechanismusobjekte über75 Builds
bytegleich, einschließlich erhaltener negativer Kontrollen; i386-Guard5.013s.
Die neue Fixture synchronisiert den längeren Selbsttest mit begrenztem
nichtblockierendem RECEIVE/YIELD und CLOSE-Bestätigung. Große Debugbelege
gehen direkt in eine128KiB-begrenzte Datei, ohne die Windows-Pipe zu füllen.
Das Reap-Oracle fordert den bestehenden Kindzustand ZOMBIE8 exakt.
Keine vorherigen Gates, Kernelmasken oder Quoten abgeschwächt.

## R8.3l: atomare Speicherreservierung vor Prozessidentität

Basis a22c30ed. Eine zusammenhängende Spawn-Transaktion schließt OOM beim
ELF-Staging und beim Aufbau von Seitentabellen, privaten ELF-Seiten und Stack.
Erst alle benötigten Frames reservieren, dann eine Generation vergeben.
Ein Fehlschlag darf keine Generation zurückdrehen oder Startquota verbrauchen.

Reihenfolge: Admission und Endpoint prüfen; Freiframe-/Identitätsbasis sichern;
ELF laden; exakt 4 Tabellen + 1 Stack + bis zu 8 Schreibseiten in einem privaten
120-Byte-Claim reservieren; Identität reservieren, Frames übertragen, Task
fertigstellen und veröffentlichen. Ein Allocator-Nullergebnis gibt nur nach
vollständiger Rücknahme, unveränderter Identität und geprüftem Freiframebestand
ENOMEM zurück. Freigabe-/Metadatenfehler bleiben Kernelkorruption, kein OOM.
Der boolesche ELF-Ladevertrag bleibt erhalten; private Last-error-Abfrage.
Kein allgemeiner In-Kernel-ELF/VFS-Dienst, keine neue öffentliche ABI.

Abnahme: 18 eingefrorene Gruppen. Tatsächlicher Claim-Assemblykern O0/O2 mit
jedem Teilpräfix, Übergabe-/Cleanupbesitz und negativen Metadaten/Freigaben.
Im echten Gast wird vor Allokatoreffekten an jeder der sechs aktuellen
Kindallokationen einmal Null injiziert, jeweils in beiden Generationen.
Erwartet: ENOMEM, vollständiger Rollback, erfolgreicher Retry, IPC, WAIT,
unveränderte Generationen und kompletter Reap. Das ist Fehlereinjektion,
kein Nachweis skalierbaren RAMs. Alle bisherigen Gastmatrizen bleiben Gates.
128MiB/1CPU/vier Slots/zwei Kinder und Zeitbudgets unverändert. Belege unter
build/codex-agent/r83l-oom; erst nach Abnahme committen und weiterarbeiten.

Abnahme R8.3l: alle18 Gruppen bestanden. Host3/0.901s einschließlich echtem
O0/O2-Assemblykern und negativen Gastoracles; Bootstrap55/0.028s,
Requests3/0.841s, Startup4/1.219s, Exit3/0.850s, Context2/1.088s.
Normalbild174728 Bytes, unveränderte Shell-/Kind-ELFs; OOM6 Fälle/12
Generationen7.312s. Alte Request-/Argv-/Exit-/Fault-/Busy-/Context-/IPC-Matrizen
bestehen;16 Mechanismusobjekte über70 Builds bytegleich. i386-Guard4.931s.
Der erste Normalfehler (Ausrichtung der Budgetdaten) samt Diagnose bleibt
erhalten; neue erfolgreiche Normalbelege unter normal-fixed. Kein anderer
Fehler wurde zum lokalen OOM umklassifiziert, keine Quoten geändert.

## Bestand und eigentlicher Abstand

R8.1a bis R8.2r sind abgenommen: Long Mode, W^X/NX, getrennte User-Adressräume,
Frameverwaltung, ELF64-Testprogramme, Interrupt-/Preemption-Proben, Runqueue,
Sleep, Spawn/Wait, Argumente, Syscallprofile und IPC einschließlich Timeout,
Backpressure, Widerruf und generationsgenauem Reap. Der vorhandene C-Kern
übergibt noch an einen überwiegend in Assembly implementierten Nachweisablauf.
Quelle: [Bootstrapvertrag](../architecture/X86_64_BOOTSTRAP.md), Code unter
`arch/x86_64`, `test/test_x86_64_boot.py` und abgeschlossene Queuepakete.

Das ist noch kein allgemeiner Kernel: 128MiB physischer Verwaltungsbereich,
vier Taskslots, eingebettete ELF-Programme, feste Rollen/Generationen und ein
einzelner IPC-Endpunkt. Die Test-Shell besitzt HELP/INFO/RUN/EXIT, nicht die
normale i386-Shell mit Dateisystem, Diensten, Desktop oder Browser. Das äußere
Multiboot-v1-Artefakt ist absichtlich ELF32; eingebetteter C-Kern und Userspace
sind ELF64. Ein geändertes Compilerflag oder größere VM-RAM-Zahl löst das nicht.

## Ziel und verbindliche Reihenfolge

Kompatible Fälle werden je Fehler-/Autoritätsgrenze gemeinsam umgesetzt, nicht
als einzelne Syscall- oder Feld-Mikropakete. Nur ein eingefrorenes Paket ist
je Pakettransaktion aktiv; spätere Etappen erhalten erst nach Bestandsprüfung
ihren Scope. Nutzeranweisung vom11. September: Nach erfolgreicher Abnahme,
lokalem Commit und sauberem Worktree folgt die nächste Transaktion automatisch
im selben interaktiven Arbeitsgang, ohne routinemäßige Bestätigungsfrage.
`AGENTS.md` hält diesen Ablauf fest. Sicherheits-/Berechtigungs-/Scopeblocker
bleiben echte Stopgründe; Paketübergaben allein sind keine Gesprächspause.

| Etappe | Zusammenhängendes Ergebnis | Pflichtnachweis vor Abschluss |
|---|---|---|
| R8.3a: ABI-/SDK-Basis | Wiederverwendbarer 64-Bit-Syscalltransport, zentrale Nummern, echte Shell als erster Verbraucher | volle Registerbreite, C/C++, ELF64-Build, alter Ring3-Dialog samt IPC/Reap, unverändertes i386 |
| Allgemeiner Kernel-Lebenszyklus | Probephasen aus produktiven Mechanismen herauslösen; konfigurierte Task-/Endpoint-Pools, Scheduling, vollständiger Kontext einschließlich FPU/SSE, Deadlines, Generationen und Supervisorzustände | beliebige zulässige Rollen statt erwarteter Token/PIDs; Crash/Hang/Quota, Fairness und Wiederanlauf ohne Verlust unabhängiger Tasks |
| Skalierbare Speicherverwaltung | 64-Bit-physische Adressen, RAM-Karten/Reservierungen, dynamische Seitentabellen, private Heaps, Shared-Memory-Rechte und kontrollierte Caches | mindestens1/4/8GiB Profile; echte Allokation oberhalb4GiB, Löcher/Überläufe, W^X/NX/Guardpages, OOM und vollständiges Reap; keine beliebige128MiB-Grenze |
| Vertrauenswürdiger Boot und Prozessstart | explizites signiertes natives x86_64-Medium, gemeinsame validierte Bootdaten, allgemeines ELF64-Laden außerhalb Ring0, versionierte argv/env/auxv | beschädigte Kandidaten, Rollback/Fallback, Pointer-/Segment-/Rights-Prüfung, unvollständiger Spawn ohne Ressourcenverlust |
| Ring3-Dienste und Geräte | bestehende Dienste portieren; VFS/Storage, Timer/IRQ und Gerätezugriffe nur über validierte Mediation, anschließend Netzwerk und Grafik/Input | reale Datei-/Netz-/Gerätearbeit plus abgestürzter/hängender Dienst, Fence/Revoke/Reap/Recreate/Selftest; DMA-Grenzen ausdrücklich nachweisen |
| Vollständiger Userspace | libc/C++-SDK, normale Shell/Tools, JS-Worker/-Host, Desktop/Applets und Browser als echte64-Bit-Prozesse | Pointer-/Layout-Audit je ABI, normale Shelldispatches, große Ressourcen und Resizes, alle bisherigen fachlichen Regressionen und fehlende Ambient-Rechte |
| Systemabnahme | getrennte native QEMU-/VMware-Images, Installations-/Recoveryweg und reproduzierbare Releaseartefakte | Start bis Desktop/Browser/JS, Service-/Speicher-Faultinjektion, Langlauf, SMP und Performance-/Latenzvergleich auf gleichen Hostbedingungen |

SMP und sichere IRQ/MMIO/PIO/DMA-Vermittlung sind Voraussetzungen der jeweils
betroffenen Plattformpakete, keine späte Dekoration. Ohne IOMMU nur validierte
kernel-eigene DMA-Mediation oder ausdrücklicher Ausschluss des Assuranceprofils.
Kein neuer komplexer Ring0-Treiber als Portierungsabkürzung. Kein automatischer
32-Bit-Binärmodus: vorhandene Anwendungen werden nativ neu übersetzt; ein
Kompatibilitätsmodus wäre ein gesondert zu autorisierender Vertrag.

Fertig bedeutet: normale native Systemimages mit funktionierender Shell,
Diensten, Desktop, Browser und JS, skalierbarem Speicher sowie geprüfter
Isolation/Recovery. Ein einzelner Bootmarker erfüllt das nicht. Performance
und Resilienz sind gemeinsam abzunehmen; i386-Referenzen bleiben erhalten.

## Effiziente Umsetzung: Bündelung, Prüfaufwand und Zeitrahmen

Nutzerpriorität vom 11. September 2026: Zeit und Ausführungskosten minimieren.
Maßstab ist ein abgenommenes, nutzbares Ergebnis je Transaktion, nicht die
Anzahl kleiner Pakete oder grüner Einzeltests. Diese Planung ändert keine
bereits eingefrorenen Gates, Rechte, Ressourcenlimits oder Zurückstellungen.

### Grober verbleibender Aufwand

Ab dem abgenommenen Stand R8.3p (`9cb27ace`) gilt als vorläufiger
Planungsrahmen: **100–300 weitere aktive Agentenstunden** bis zur vollständigen
nativen Version einschließlich Diensten, Desktop, Browser, JavaScript und
Systemabnahme. Darin enthalten sind grob **20–60 Stunden** bis zum ersten
nutzbaren Zwischenstand: normale native Shell mit Dateisystemzugriff und
Programmstart. Die zweite Spanne ist Teil der Gesamtspanne, nicht zusätzlich.

Beide Angaben sind unsichere Schätzungen, keine gemessene Restaufwandsprognose,
Terminzusage oder automatisch bewilligten Laufzeitbudgets. Aktive Zeit umfasst
Implementierung, Diagnose, Builds und automatische Tests; Standby und Warten
auf externe Freigaben sind nicht enthalten. Wiederverwendbarkeit des i386-Codes,
ABI-/Pointerfehler und notwendige Geräte-/Recoveryanpassungen können die Spanne
wesentlich verändern. Nach jedem nutzbaren Meilenstein anhand tatsächlich
aufgewendeter Zeiten und verbleibender Abhängigkeiten neu schätzen.

### Was zusammengefasst wird

Die folgenden Arbeitsstränge konkretisieren die Reihenfolge oben. Eine Zeile
ist kein pauschales Sammelpaket: Innerhalb eines Strangs wird jeweils der
größte zusammenhängende Schnitt mit gemeinsamer Fehler-/Autoritätsgrenze und
gemeinsamem Freigabe-/Rollbackvertrag eingefroren. Unabhängige Fehlerdomänen,
persistente Formate und Hardwareabnahmen bleiben getrennte Transaktionen.

| Arbeitsstrang | Gemeinsam umsetzen und prüfen | Nutzbares Ergebnis |
|---|---|---|
| Allgemeiner Prozessbetrieb | Rollenunabhängige Taskverwaltung mit Kontext, Scheduling, Generationen, Budget und gemeinsamem Retirement; kompatible Rollen-/Fehlerfälle in einer Matrix statt je PID oder Syscall ein Paket. Endpoint-Verwaltung bleibt bei eigener Autoritätsgrenze ein eigener Schnitt. | Mehrere reguläre Prozesse statt fest verdrahtetem Testdialog |
| Skalierbarer Speicher | RAM-Karte, Reservierungen und physische Adressbreite innerhalb der Frame-Verwaltungsgrenze zusammen behandeln; 1/4/8-GiB- und Oberhalb-4-GiB-Fälle gemeinsam prüfen. Darauf private Heaps, Mapping und Reap je Besitzgrenze integrieren. | Tatsächlich nutzbarer großer RAM mit erhaltenem Speicherschutz |
| Boot, Dateien und Programmstart | Gemeinsame ELF64-/argv/env/auxv-Validierung samt unvollständigem Spawn und Rollback bündeln; bestehende SDK-/Shellpfade direkt anbinden. Signiertes Bootmedium und Storage-/VFS-Recovery wegen eigener Vertrauens-/Persistenzgrenzen getrennt abnehmen. | Normale Ring-3-Shell startet native Programme aus dem Dateisystem |
| Dienst- und Geräteportierung | Pro Dienst vorhandene Implementierung, 64-Bit-IPC-/Pointeradapter und vollständigen Crash-/Hang-/Restartnachweis gemeinsam portieren. Storage, Netzwerk und Grafik/Input nicht zu einer gemeinsamen Fehlerdomäne zusammenziehen. | Reale Datei-, Netzwerk-, Anzeige- und Eingabefunktionen |
| SDK und Anwendungen | Gemeinsame libc-/C++-/Buildkorrekturen einmal zentral durchführen; darauf kompatible Programme gesammelt neu übersetzen und prüfen. JS-Engine wiederverwenden, Browser-/Shell-Hostrechte weiterhin getrennt halten. Keine gleichzeitige funktionale Browser-Neuentwicklung. | Native Tools, JavaScript, Desktop/Applets und Browser |
| Systemabnahme | Auf einem stabilen Kandidaten die gemeinsame funktionale Matrix ausführen; QEMU-/VMware-, Recovery-, SMP-, Langlauf- und Performancebelege je erforderlicher Plattform erhalten. | Reproduzierbare, nutzbare native Systemimages |

Erster sichtbarer Meilenstein bleibt die normale Shell mit Datei- und
Programmzugriff. Dafür notwendige Voraussetzungen zuerst schließen; nicht
unabhängige Desktopfunktionen oder zusätzliche JS-APIs vorziehen. Kein komplexer
Ring-0-Treiber, keine gelockerten Capabilities und kein weggelassener Recoverypfad
als Abkürzung zu diesem Meilenstein.

### Verbindliche Effizienzregeln für kommende Paketdefinitionen

1. Vor Umsetzung vorhandene Mechanismen und Verbraucher inventarisieren;
   gemeinsame Adapter und etablierte Bibliotheken wiederverwenden. Keine zweite
   Zustandsverwaltung oder komplette C-/Assembly-Neufassung nur wegen 64 Bit.
2. Paketumfang inklusive aller betroffenen Verbraucher, Tests und Dokumentation
   vorab vollständig bestimmen. Varianten derselben Grenze zusammen einfrieren;
   keine künstlichen Pakete je Register, Feld, Fehlercode oder RAM-Profil.
3. Prüfmatrix vor dem Einfrieren aus Abhängigkeiten und Risiken ableiten.
   Historische Vollmatrizen nicht ohne sachlichen Grund in jedes neue Paket
   übernehmen. Tatsächliche Host-Ausführung und Gastnachweis der betroffenen
   Laufzeitgrenze bleiben Pflicht; reine Quellmuster sind kein Ersatz.
4. Unveränderte Hosttests nicht pro Video-/Hardwarevariante wiederholen.
   Inkrementelle Builds und gültige Compiler-Caches nutzen; keine routinemäßigen
   Clean-Builds. Gemeinsame Artefakte nur bei nachgewiesen identischen Quellen,
   Konfigurationen und Werkzeugen wiederverwenden. Jede eingefrorene Gastvariante
   bleibt auszuführen; gemeinsame Binärdateien ersetzen keine Laufzeitbelege.
5. Pro unverändertem Kandidaten jeden eingefrorenen Gate genau einmal ausführen.
   Nach einer Korrektur alle dadurch ungültig gewordenen Nachweise erneuern;
   keine pauschale Anerkennung alter Ergebnisse. Bereits eingefrorene Gate-Sätze
   nicht nachträglich aus Zeitgründen kürzen. Vollsuite und umfassende
   Plattformmatrix an den dafür definierten Meilensteinen ausführen.
6. Bei Fehlern zuerst den erhaltenen Erstbeleg und gezielte Regression verwenden.
   Keine unveränderten Wiederholungsschleifen bis zufällig Grün erscheint.
   Beobachterfehler innerhalb genehmigten Umfangs reparieren, niemals Oracle,
   Deadline oder Fehlernachweis zugunsten eines grünen Ergebnisses abschwächen.
7. Unabhängige Leseprüfungen und sichere Hosttests dürfen parallel laufen;
   keine konkurrierenden Builds im selben Ausgabeverzeichnis oder zeitkritischen
   VM-/Performancemessungen. Weiterhin ein Hauptagent, keine Subagenten.
8. Dokumentation und Ergebnisbericht knapp auf Änderungen, Belege und offene
   Risiken begrenzen; Detailprotokolle unter `build/codex-agent/`. Nach grünen
   Gates, Scopeprüfung, lokalem Commit und sauberem Worktree unmittelbar die
   nächste priorisierte Transaktion beginnen, ohne routinemäßige Rückfrage.
9. Je Paket Implementierungs-/Diagnosezeit, Build-/Testzeit und externe Wartezeit
   getrennt festhalten, soweit messbar; Unbekanntes nicht schätzen und als Messung
   ausgeben. Kosten nach abgenommenen Meilensteinen beurteilen. Kein zusätzliches
   Metriksystem als eigenes Nebenprojekt; vorhandene Zeit-/Gateprotokolle nutzen.

Performance und Resilienz bleiben gleichzeitige Abnahmekriterien. Einsparungen
entstehen durch Wiederverwendung, größere kohärente Schnitte und vermiedene
Doppelarbeit, nicht durch schwächere Isolation oder unbelegte Fertigmeldungen.

## Eingefrorenes erstes Paket R8.3a

Ein ABI-/Toolchain-Schnitt, keine Änderung am Kernel, an Rechten, Profilen,
Framegrenzen, Taskkapazitäten, persistenten Formaten oder Dienstverhalten.
`userspace/sdk/include/reist/x86_64/syscall.h` bietet C/C++-Transport für0..6
Argumente. Nummern werden aus der bestehenden autoritativen
`REIST_SYSCALL_LIST` projiziert, nicht erneut von Hand nummeriert. Die echte
64-Bit-Test-Shell verwendet ihn statt ihrer lokalen Kopie.

Referenz: [System-V AMD64 psABI](https://gitlab.com/x86-psABIs/x86-64-ABI),
insbesondere [Kernel Calling Convention](https://gitlab.com/x86-psABIs/x86-64-ABI/-/blob/master/x86-64-ABI/kernel.tex).
Produktionsziel ist `x86_64-freestanding-none`, LP64. Nummer in RAX, Argumente
in RDI/RSI/RDX/R10/R8/R9, Ergebnis als int64_t aus RAX. RCX/R11, Flags und
Speicher sind Compiler-Clobbers; Red Zone ist deaktiviert. Unbenutzte Argumente
werden null gesetzt. Header nutzt uint64_t/uintptr_t statt int-Pointercasts.
REIST-Nummern/Fehler und explizite Profile bleiben erhalten: keine Linux-
Binärkompatibilität und keine Behauptung, alle gelisteten Syscalls seien schon
unter x86_64 implementiert. Raw-Transport erteilt niemals Autorität, fügt kein
errno, keine automatischen Wiederholungen und keinen i386-Fallback hinzu.

Der Native-Hosttest ersetzt ausschließlich die Instruktion durch eine feste
Assembly-Registersonde. Der ausdrücklich benannte Testschalter ist niemals im
Gastbuild gesetzt; die Sonde führt keine Windows-/Host-Syscalls aus. Sie prüft
echten kompilierten Code bei O0/O2 in C und C++, alle sieben Aufrufbreiten,
Werte oberhalb4GiB, High-Bit-Ergebnisse, negative Fehler und RCX/R11-Clobbers.
Ein separater freestanding-Compile prüft LP64; i386 wird geschlossen abgewiesen.
Der echte Gast beweist anschließend die existierende Kernelgrenze unverändert.

Sechs eingefrorene Gruppen stehen in der Queue: neuer SDK-Hosttest, bestehende
55 Bootstrap-Quellverträge (nur Kopiernummern-Assertions auf gemeinsame Quelle
umstellen), Dokumentation, separater Windows-Build, echter QEMU-Dialog mit
INFO/RUN/RUN/EXIT und vollständigem Cleanup sowie R3.45-Image-/PRG-Hashguard.
Build und Logs ausschließlich unter `build/codex-agent/r83a-sdk/`; keine
bestehenden Images oder Belege überschreiben. QEMU bleibt headless, eine CPU,
128MiB/10s für diesen unveränderten Prototypnachweis. Keine Hardware-/SMP- oder
Mehr-GiB-Zusage aus diesem Paket. R341-H1/H2 und die ausdrückliche R3.6b-
Zurückstellung bleiben offen. JS-Folgefeatures sind zugunsten x86_64 nachgeordnet.

### Genehmigter Prüfernachtrag vom 11. September 2026

Der Nutzer hat die gezielte Erweiterung von
`scripts/verify_js_colors_artifacts.py` samt `test/test_js_colors.py` genehmigt:
Der vorhandene Hauptbuild ist VMware/VGA, nicht QEMU/VGA. Der Prüfer muss
das konfigurierte Profil der Rohplatte verwenden und im Bericht benennen.
Alle Kernel-, Programm-, Beispiel- und authentifizierten Archivprüfungen
bleiben bestehen; VMware darf nicht als QEMU-Nachweis erscheinen.
Framebuffer-Archivierung bleibt ausschließlich QEMU/Framebuffer.
Die sechs ursprünglichen Gatebefehle bleiben unverändert, hinzu kommt
`python test/test_js_colors.py -v` mit positiven und negativen Profil- und
Binärregressionen. Keine vorhandenen Images neu bauen oder überschreiben.

### Ergebnis R8.3a

SDK-Basis abgenommen: C/C++ O0/O2, LP64 und Architekturabweisung,55 bestehende
Bootstrapverträge, Dokumentation, separater nativer Build und echter QEMU-
Dialog mit beiden IPC-Kindgenerationen bestanden. Der genehmigte Imageprüfer-
Nachtrag ist mit7 Hosttests und realen Images geprüft. Alle ursprünglichen
Kernel-/PRG-Checks bleiben aktiv. Vollständige Belege und Grenzen stehen in
[CURRENT_WORK](CURRENT_WORK.md). Nächster fachlicher Schritt ist der allgemeine
Kernel-Lifecycle, ausdrücklich nicht die Erklärung des Prototyps zum fertigen OS.

## R8.3b: vollständiger Besitz des FP-Registerzustands

Bestandsprüfung nach `0ceed8e0`: Der Scheduler sichert nur GPRs; für x87/MMX,
XMM0..15, MXCSR und Rundungskontrollen fehlt ein eigener Kontext. Dieser
Fehlerbereich wird gemeinsam über alle vorhandenen Scheduler-Modi geschlossen,
bevor der allgemeine Lifecycle neue Prozesse zulässt. Keine einzelnen Pakete
je Register, Syscall oder Scheduler-Modus.

Referenz ist das [Intel SDM](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html),
FXSAVE64/FXRSTOR64 und CR0/CR4, sowie die Empfehlung zum eager Restore in
[INTEL-SA-00145](https://www.intel.com/content/www/us/en/security-center/advisory/intel-sa-00145.html).
Kernelprivate,16-Byte-ausgerichtete512-Byte-Abbilder stehen neben den bestehenden
GPR-Records; deren Offsets und alle öffentlichen ABIs bleiben unverändert.
Neue Generationen erhalten vollständig genullte Payloads, leere x87-Tags,
FCW0x037f/MXCSR0x1f80. Save vor Verlassen eines fortsetzbaren Tasks, eager
Restore vor jedem Eintritt; kein Userpointer, Lazy-Owner oder #NM-Replay.
Terminale Zustände und fehlgeschlagener Aufbau werden gelöscht; Wiederverwendung
bekommt einen frischen Zustand. Kernel-C bleibt ohne FP/SIMD-Codegenerierung.

CPUID muss FPU/FXSR/SSE/SSE2 melden. CR0.MP/NE an, EM/TS aus;
CR4.OSFXSR/OSXMMEXCPT an, OSXSAVE aus. Bereits aktives OSXSAVE wird abgewiesen,
nicht still abgeschaltet; Readback vor erster Userausführung. Das Paket bleibt
auf den bisherigen eingebetteten, zugelassenen Test-ELFs. Allgemeine #MF/#XM/
#GP-Prozessbeendigung, freier Prozessstart, allgemeine Pools und SMP bleiben
verpflichtende Lifecycle-Arbeit vor nativer JS-/Anwendungsfreigabe. Vorhandene
Fault-/Reap-Probes prüfen hier die Registertrennung nach Prozessfehlern; daraus
folgt ausdrücklich noch keine allgemeine FP-Ausnahmeabnahme.

Acht eingefrorene Gruppen: neuer nativer Host-Instruktionstest O0/O2, bestehende
SDK- und Bootstraptests, Dokumentation, isolierter Build, vollständiger echter
QEMU-Dialog, negative CPU-Admission und unveränderter i386-Imageguard. Gast-
Fixtures verwenden unterschiedliche FP-Muster bei Yield, Timerwechsel, Sleep,
Spawn/Wait und IPC; alle bisherigen Markernachweise bleiben verpflichtend.
Logs unter `build/codex-agent/r83b-fp/`, positive und negative Gäste höchstens10s,
eine CPU/128MiB, keine sichtbare VM. R3.6b bleibt zurückgestellt.

Abnahme: R8.3b ist umgesetzt und mit allen acht Gruppen geprüft. Die Sonde
verwendet private Scratchdaten statt temporärer Stackframes, damit auch eine
IRQ-Unterbrechung innerhalb der FP-Prüfung den bisherigen festen User-RSP-
Vertrag erfüllt. Das RX-only-Kind verwendet den unteren1072-Byte-Bereich seiner
vorhandenen privaten Stackseite; kein neues Segment oder Ressourcenbudget.
Der erste Fehlgast bleibt erhalten, der korrigierte Lauf nutzt ausschließlich
einen neuen Logpfad (`guest-stackless.log`); alle übrigen Gateanforderungen
bleiben gleich. Belege in [CURRENT_WORK](CURRENT_WORK.md). Der verbleibende
allgemeine Lifecycle ist weiterhin offen, insbesondere allgemeine Userfault-
Beendigung und Ablösung der fest verdrahteten Probephasen.

## R8.3c: Ausnahmebeendigung und vollständiges Kind-Retirement

Nach `473ce58c` fehlt die normale Beendigung eines fehlerhaften Shellkindes.
Der vorhandene Exceptionpfad kennt überwiegend exakte Probeadressen; der
Shell-Kindexit akzeptiert ausschließlich77 bei bereits geschlossener IPC.
R8.3c behandelt diese eine Fehler-/Ownershipgrenze zusammenhängend: frühe
Fehler, noch gepufferte Nachrichten, wartender Receive-Elternprozess und
bereits blockierendes WAIT. Keine Einzelpakete je Vektor oder IPC-Phase.

Die Intel-Exceptionvektoren bleiben unverändert. Ein kleiner, auch nativ am
Host ausführbarer Assembly-Klassifikator akzeptiert CPL3-Fehler0/1/3/4/5/6/
13/14/16/17/19; Kernelherkunft, NMI, Double Fault, Machine Check, #NM und
unbekannte Vektoren werden nicht als reparierbarer Prozessfehler behandelt.
RIP/RSP sind Diagnosedaten und werden niemals dereferenziert oder als gültige
Useradresse vorausgesetzt: gerade ein ungültiger Stack/Entry kann Fehlerursache
sein. Der bestehende REIST-Raw-Status nutzt128+Vektor für Ausnahmebeendigung;
kein POSIX-`waitpid`-Bitlayout und keine Linux-Binärkompatibilitätsbehauptung.

Unter gesperrten Interrupts Identität, Generation, Elternbeziehung, Queue und
Deadlinebesitz prüfen; anschließend Kind und dessen vorhandene exklusive
Eltern-/Kind-IPC-Verbindung fencen, Nachrichten/Waits verwerfen, Timer abmelden,
Profil/FP/Frames/Seitentabellen/ELF reapten. Erst danach darf der Elternprozess
fortsetzen. Eine feste generationgebundene Terminalquittung bleibt bis WAIT,
ohne Kindframes oder Rechte zu behalten. WAIT konsumiert genau einmal;
nachträgliches CLOSE derselben bereits eingezäunten Verbindung ist idempotent.
Ein blockierter Receive kehrt mit EPIPE zurück. Keine Policy für beliebige
geteilte Endpoints oder verwaiste Eltern in diesem Paket.

Normaler Kindexit und Ausnahme-Retirement behalten die bestehenden positiven
Probes. Zusätzliche Build-Testparameter wählen ausschließlich die eingebettete
Kindfixture (Vektor und vier Phasen); weder Kernelklassifikation noch Rechte
werden davon abhängig. Der C-Shell-Prüfer erwartet den entsprechenden Raw-
Status und prüft Recovery/Reap in beiden Generationen. Kein neuer Produkt-
Shellbefehl, keine normale i386-Imageänderung.

Neun eingefrorene Gruppen: Hostklassifikation O0/O2 mit negativen Frames und
unzugänglichen Useradressen, bestehende FP-/SDK-/55 Bootstraptests, Doku,
Normalbuild/Normalgast,24 reale TCG-Varianten (DE/BP/UD/GP/PF/MF je vier Phasen)
und i386-Imageguard. Je Gast eine CPU/128MiB/maximal10s; je isoliertem Build
maximal90s. Matrixbelege in eindeutigen Unterordnern, kein Überschreiben.
#XM/#AC-Klassifikation ist kein echter Hardware-Ausnahmenachweis; deren
Zielhardware-Abnahme bleibt vor allgemeiner nativer FP-Anwendungsfreigabe offen.
R3.6b und R341-H1/H2 bleiben zurückgestellt beziehungsweise offen.

Abnahme R8.3c: alle neun Gruppen bestanden,24 reale Fehlvarianten und48
Kindgenerationen. Der Klassifikator benötigt keine zugelassene Probe-RIP;
die unabhängige Gastauswertung dagegen bindet den Nachweis an die tatsächliche
ELF-Fehlerinstruktion, Generation, Elternzustand und Queuebelegung. Sie weist
fehlende/zusätzliche Quittungen, falsche Reihenfolge und alte Generationen ab.
Der vorhandene rücksetzbare Breakpoint-Gatevertrag gilt auch für Shelltasks;
ein echter erster Fehlgast deckte die bislang fehlende Freigabe auf.
Endpointgeneration und wartender Puffer werden vor Fencing überprüft.
Die private Terminalquittung umfasst48 Bytes und bleibt ohne Ressourcenrechte.
Normalbuild/Normalgast, bisherige FP-/SDK-/Bootstrapprüfungen und i386-Images
bleiben gültig. Endgültige Belege und erhaltene Fehlversuche in
[CURRENT_WORK](CURRENT_WORK.md). Der nächste fachliche Schritt bleibt der
allgemeine, nicht auf die festen Testgenerationen beschränkte Lifecycle;
keine Freigabe beliebiger nativer Programme aus dieser Teilabnahme.

## R8.3d: rollenunabhängiger Ready-/Deadline-Kern

Bestand nach `bf471ba3`: FIFO, sortierte Deadline-Einfügung und Entnahme sind
im großen Assembly-Proof mit Modusprüfung und teils rollenabhängiger Löschung
vermischt. Diese eine Queue-/Besitzgrenze wird gemeinsam herausgelöst, nicht
als Pakete pro Operation. Die tatsächlich benutzten Mechanismen erhalten
einen privaten Kernel-Descriptor und kennen weder Testmodus noch PID/Token.
Vorhandene Taskzustands-/Profil- und Tickregeln verbleiben im ausdrücklich
begrenzten Bootstrapadapter. Keine zweite parallele Schedulerautorität.

Interne SysV-AMD64-Aufrufkonvention; keine neue öffentliche API oder POSIX-
Schedulerkompatibilitätsbehauptung. FIFO bewahrt Ankunftsreihenfolge, Deadlines
sortieren nach absolutem monotonem Tick und bei Gleichstand nach Slot, wie
bisher. Kapazität1..64 konfigurierbar, Bootstrap weiter4. Bestehende private
Generation32-/Slotpackung bleibt erhalten; null und High-Bit-Eingaben werden
abgewiesen, niemals abgeschnitten. Generationsüberlauf darf keine alte
Identität reaktivieren. RAM-/Taskbudgetänderungen sind damit nicht freigegeben.

Descriptor und Speicher sind ausschließlich kernel-eigen und unter IF=0 auf
dem bisherigen Ein-CPU-Profil serialisiert. Vollständige begrenzte Prüfung
von Metadaten, sortierter/zyklischer Form, Leerstellen und eindeutigem Besitz
vor der ersten Mutation. Doppelte Queueaufnahme, fremde Generation, volle oder
beschädigte Queue bewirken keine Mutation. Deadlineentfernung ist exakt
generationgebunden und kompaktierend; fehlender Eintrag bleibt ohne Wirkung.
Adapter verhindern gleichzeitige Ready-/Deadline-Mitgliedschaft. Kein Heap,
I/O, Logging, Busy-Wait oder versteckte Reparatur korrupter Kernelmetadaten.

Neun eingefrorene Gruppen: neuer echter Assembly-Hostnachweis O0/O2 mit
Kapazitäten1/3/4/64, FIFO-Wrap/Fairness, Deadlinereihenfolge/Gleichständen/
Cancel, negativen Generationen und Snapshot-Nichtmutation sowie modellbasiertem
Stress; bestehende Bootstrap-/FP-/Fault-/Dokutests, Normalbuild/Normalgast,
24 bestehende echte Faultvarianten und i386-Imageguard. Alte Gastmarker bleiben
Pflicht; nur überholte Quellassertions werden auf Mechanismus plus Adapter
umgestellt. Belege `build/codex-agent/r83d-queue/`, kein Überschreiben alter
Fehlläufe. Keine SMP-/beliebige-Prozess-/vollständige64-Bit-Freigabe daraus.

Abnahme: R8.3d ist mit neun Gruppen abgeschlossen. Tatsächliche FIFO- und
Deadlineverbraucher einschließlich Timeout/Cancel/Fault-Retirement rufen den
gleichen Kern wie der native Hosttest auf; es bleibt keine zweite aktive
Queueimplementierung. Modellnachweis je96.000 Operationen bei O0/O2,
Kapazitäten1/3/4/64 und sämtliche24 bisherigen CPU-Fehlvarianten bestanden.
Alter Normalgast und i386-Images bleiben gültig. Generationen werden hier
validiert, nicht vergeben; spätere Wiederverwendung muss weiterhin gegen
Überlauf abgesichert werden. Die vollständige Queueprüfung ist linear in der
konfigurierten Kapazität, alle Mutationen bleiben begrenzt. Belege und bewusst
offene Prozess-/Systemgrenzen in [CURRENT_WORK](CURRENT_WORK.md).

## R8.3e: Reservierung und Lebensdauer nativer Taskidentitäten

Nach `af0a07b4` sind Queues allgemein, aber Generationen werden noch direkt
aus Probe-Konstanten in Taskrecords geschrieben. Eine zusammenhängende
Identitätsgrenze löst Reservierung, Veröffentlichung und Retirement für die
tatsächliche native Shell-/Kindbeziehung heraus. Andere historische Modi
bleiben begrenzte Adapter, ihre bisherigen Nachweise werden nicht entfernt.

Privater SysV-AMD64-Aufruf, keine öffentliche ABI. Ein24-Byte-Pooldescriptor
referenziert bestehende256-Byte-Taskrecords und pro Slot einen32-Bit-
Retirementvermerk; Kapazität1..64 und letzter vergebener Zähler sind intern.
Keine zweite Zustandsautorität. FREE muss vollständig genullt sein; eine
Reservierung verbraucht die nächste nichtnull Generation und setzt den neuen
privaten Zustand RESERVED9. Erst nach validiertem Frame-/Kontextaufbau und
Syscallprofil darf READY veröffentlicht werden. Counterwerte werden nicht
abgeschnitten, zurückgesetzt oder über UINT32_MAX gewrappt. Rückabwicklung
verbraucht ihre Generation ebenfalls. Neue Poolinstanzen sind getrennte
Namespaces; diese Arbeit erlaubt keinen Neustart eines Pools mit alten Handles.

Retirement ist nur für genau passende Generation und terminalen Zustand
FAULTED/EXITED/ZOMBIE oder eine zurückzurollende Reservierung zulässig. CR3,
Stack und private Frames müssen bereits freigegeben sein; Profil-/IPC-/FP-/
Tabellenfreigabe bleibt Verantwortung des vorhandenen geprüften Adapters.
Dann GPRrecord löschen und Tombstone veröffentlichen. Wiederholtes Retirement
ist ausschließlich bei weiterhin freiem Slot und genau gleichem Tombstone
erfolgreich; alte Generation darf niemals eine wiederbelegte Generation ändern.
Poolzustand, Nullrecords, Generationen und Duplikate werden vor Mutation
begrenzt geprüft. Caller besitzt alle Speicherbereiche und serialisiert IF=0.

Neun Gruppen: echter Assembly-Hosttest O0/O2 mit Kapazitäten1/4/64, reserviertem
Aufbau/Publish/Retire/Rollback, Wiederverwendung und Erschöpfung, Nichtmutation
bei alten/oberen Bits, korrupten Identitäten und noch besessenen Ressourcen;
bestehende Bootstrap-/Queue-/FP-/Dokutests, Normalbuild/-gast und24 Faultgäste,
i386-Imageguard. Gast weiterhin4 Tasks/128MiB/eine CPU/maximal10s. Belege unter
`build/codex-agent/r83e-identity/`. Allgemeine Prozess-/OOM-/Supervisorfreigabe
und Speicher-/Dienstportierung bleiben offen. Keine Gesamtfertigmeldung.

Abnahme R8.3e: alle neun Gruppen bestanden. Echte Shell-/Kindgenerationen
benutzen denselben Kern wie der O0/O2-Hosttest; die abschließende Gastprüfung
verlangt Nullrecords und exakt passende Retirementvermerke. Kapazitäten1/4/64,
Wiederverwendung, Erschöpfung, Rollback und negative Snapshotprüfungen bestehen.
Auch Kollisionen zwischen aktiven und retired Generationen oder zwei Tombstones
werden vor Mutation abgewiesen; begrenzt quadratische Prüfung bei höchstens64
Slots. Normalgast,24 Fehlvarianten/48 Generationen und i386-Imageguard grün.
Fehlversuche und finale Belege getrennt erhalten; siehe
[CURRENT_WORK](CURRENT_WORK.md). Der allgemeine Kernel-Lifecycle bleibt offen.

## R8.3f: gemeinsame Registersicherung und lebende Userstacks

Bestand `4616b210`: Registersicherung für SYSCALL und IRQ ist dupliziert;
Timerzulassung verlangt einen konstanten User-RSP. Das verhindert eine
belastbare allgemeine Präemption normalen C/C++-Codes. Ein gemeinsamer
privater Contextkern validiert und übernimmt beide Varianten in die bestehenden
Taskrecords, ohne zweite dauerhafte Kontextablage. Die normierte176-Byte-
Exceptionframeform bleibt erhalten; der Syscalladapter erzeugt dieselbe Form
auf seinem begrenzten Kernelstack.48-Byte-Descriptor: Record, Generation,
aktueller CR3, Stackunter-/obergrenze und Frameart; Validate oder Capture.

Referenz sind die vorhandenen Intel-IA-32e-Interrupt-/IRETQ-/SYSCALL-Verträge
und die private SysV-AMD64-Aufrufkonvention. SYSCALL konsumiert RCX/R11 als
RIP/RFLAGS und setzt den anfänglichen Ergebniswert RAX auf0; Handler liefern
ihre bisherigen Ergebnisse. IRQ bewahrt alle15 GPRs und RIP/RSP/RFLAGS.
Recordzustand RUNNING, exakte Generation32, CR3, Userselektoren, Frameart,
kanonische untere48-Bit-Adressen und zugelassene Stackgrenzen werden vor
Mutation geprüft. IRQ verlangt IF; privilegierte/reservierte Flags bleiben
abgewiesen. RIP/RSP werden niemals dereferenziert. Mapping-/Profilzulassung
und FP-Besitz bleiben in den vorhandenen Adaptern. Keine öffentliche ABI,
kein neuer Timermodus oder allgemeines Shell-Hang-Recoveryversprechen.

Neun Gruppen: derselbe Assemblykern O0/O2 am Host mit vollständigem
Registervergleich, beiden Framearten und negativen Nichtmutationsfällen;
Bootstrap-/Identitäts-/FP-/Dokutests, Normalbuild und echter Gast mit belegtem
Stack, Canaries und wechselndem RSP während Timerpräemption,24 bestehende
Fehlvarianten/48 Generationen und i386-Guard. Alle alten Gastmarker bleiben
Pflicht, keine bloße Quellmusterabnahme. Belege `build/codex-agent/r83f-context/`;
Gastbudget unverändert. Allgemeiner Scheduler/Supervisor und skalierbarer
Speicher folgen weiterhin; keine vollständige64-Bit-Fertigmeldung.

Abnahme R8.3f: alle neun Gruppen bestanden, tatsächliche Syscall-/IRQ-
Verbraucher und O0/O2-Hosttest nutzen denselben Kern. Reale Quantumwechsel
bewahren belegte Stacks und Canaries; beide gespeicherten RSP müssen unterhalb
Stacktop liegen. Normalgast und24 bestehende Fehlvarianten/48 Generationen
bestehen. Ein erster realer IRQ deckte RF als zulässiges gespeichertes Flag
auf; die Korrektur bewahrt es nur für IRQ/IRETQ und besitzt einen roten/grünen
Hostnachweis. Weitere Flags bleiben gesperrt, kein Gate abgeschwächt.
Belege und weiterhin offene Timer-/Hang-/Systemgrenzen in
[CURRENT_WORK](CURRENT_WORK.md).

## R8.3g: gemeinsame Shellzeit, Präemption und CPU-Spin-Begrenzung

Bestand nach R8.3f: Shelltasks laufen noch IF=0; IPC-Waits setzen den Timer
jeweils neu auf Tick0 und melden ihn bei Abschluss ab. Ein permanenter
CPU-Verbraucher kann so trotz geprüfter IRQ-Kontexte nicht unterbrochen werden.
Diese eine CPU-Ausführungsgrenze umfasst deshalb gemeinsam Clock-Lebensdauer,
absolute IPC-Deadlines, Präemption und generationsgenaues Budget-Retirement.

Das bestehende Ein-CPU-PIC/PIT-Profil bekommt einen gemeinsamen100-Hz-Shell-
Modus mit höchstens256 gelieferten Ticks und bisheriger begrenzter TSC-Lease.
Beide Shelltasks laufen IF=1. IRQ validiert Herkunft und Kontext, verarbeitet
begrenzte Deadline-Wakeups und quittiert EOI; erst danach folgen Kontextwechsel
oder Retirement im Scheduler-Tail. IPC-Abschluss entfernt nur seinen Wait,
nicht die Scheduling-Zeitbasis. Cleanup/Fencing beendet die Lease ausdrücklich.
Die bisherigen isolierten Timermodi bleiben geprüfte Adapter.

Ein privater generationsgebundener CPU-Budgetrecord zählt laufende Samples;
für zugelassene Kinder32 PIT-Ticks, niemals Reset durch Yield oder IPC. Volles
Budget führt über denselben Fencing-/Reap-/WAIT-Pfad wie ein terminaler Fehler,
mit ausdrücklich REIST-eigenem Raw-Status256, keinem POSIX-Signal-/Waitlayout.
Generation, monotoner Tick, Grenzen und Nichtmutation werden am tatsächlichen
Assemblykern O0/O2 geprüft. Das ist gesampelte CPU-Zeit, keine exakte Zeitmessung,
FTTI-Zusage oder allgemeine Supervisor-/Prozess-/SMP-Abnahme.

Elf Gruppen: Budgethost und negativer Quittungsoracle, bestehende Bootstrap-/
Context-/Identitäts-/FP-/Dokutests, Normalbuild/-gast,24 bisherige Fehlvarianten,
echter Busy-Gast und i386-Guard. Der Busy-Build ändert ausschließlich Userspace-
Fixture/Erwartungen, nicht Kernelbudget/Rechte: ein syscallfreier Spin zwingt
den Elternprozess zur echten IRQ-Fortsetzung;32 Samples, vollständiges Reap,
Raw-Status256 und RUN werden für Generation41/42 unabhängig geprüft. Die
Schleifenadresse stammt aus dem ELF, nicht aus einer Kernel-RIP-Freigabeliste.
Belege `build/codex-agent/r83g-preempt/`, alle Gäste weiter maximal10s.

Abnahme R8.3g: elf Gruppen bestanden. Derselbe Budgetkern läuft O0/O2 am Host
und in tatsächlichen Shell-Kindprozessen. Permanenter Timer, absolute IPC-
Deadlines und EOI-vor-Scheduler-Tail sind im Gast geprüft. Beide syscallfreien
Spingenerationen geben die CPU an den Elternprozess ab und werden nach32
Samples vollständig gereapt. Der zusätzliche negative User-RSP-Fall deckte
einen echten Bootstrapabbruch auf und wird nun nach validierter Kernelidentität
ohne Stackdereferenzierung lokal beendet: expliziter REIST-Raw-Status257,
keine fingierte #GP und keine ABI-Umnummerierung. Beide Stackgenerationen
besitzen eigene Quittungs-/ELF-Negativprüfungen; Originalgates bleiben erhalten.
Private Terminalquittung um8-Byte-Samplefeld ergänzt, nach WAIT vollständig
null. Neue Testflags betreffen nur Userspace, nicht die Kernelbudgetregeln.
Normaldialog,24 alte CPU-Fehlvarianten/48 Generationen und i386-Guard grün;
Belege und unverändert offene Systemgrenzen in [CURRENT_WORK](CURRENT_WORK.md).

## R8.3h: Userkontext-Zulassung über Systemaufruf und IRQ

Bestand `c57e9f8f`: RSP=0 wird bei IRQ lokal beendet, beim SYSCALL jedoch
noch zum Bootstrapfehler. Zudem weist der Contextkern normale Userflags wie
DF zurück. Dieser zusammenhängende Eintritts-/Rückkehrschnitt behandelt
Userkontextfehler erst nach geprüfter Kernelidentität und Syscallprofil,
vor Handlerwirkung. Kein neues Prozessmodell oder Supervisorrecht.

Referenz: [Intel SDM](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html),
RFLAGS, SYSCALL/IA32_FMASK und IRETQ. DF/AC/ID/TF werden im Userkontext
bewahrt; RF weiterhin nur im IRQ-Abbild. IOPL, reservierte und privilegierte
Flags bleiben gesperrt. Usergesetztes NT darf nicht in einen Long-Mode-IRETQ
gelangen: lokale terminale Ablehnung mit ausdrücklich REIST-Raw258, kein
erfundenes POSIX-Signal. Ungültiger Stack bleibt Raw257, ohne Dereferenzierung.
Kernelstackwechsel, CLD und bestehende FMASK bleiben verpflichtend; IRQ
quittiert EOI vor Retirement. Kernel-/Elternfehler bleiben fail-closed.

Elf eingefrorene Gruppen: erweiterter echter Context-Assemblyhost O0/O2,
negative Quittungsoracles, Bootstrap-/Fault-/Dokutests, Normalbuild/-gast,
neuer realer Kontextgast mit Null-/nichtkanonischem SYSCALL-RSP,
nichtkanonischem IRQ-RSP, erlaubten Flags über erlaubte/abgewiesene Syscalls
und IRQ, NT bei beiden Eintrittsarten und echtem TF-Debugtrap; je zwei
Generationen mit unabhängiger ELF-/Reap-/WAIT-Prüfung. Alle alten24 Faultfälle
und Busy-/Stackgäste bleiben Gates, ebenso der i386-Byteguard. Testschalter
betreffen nur Userspace; native Ressourcen-/Zeitbudgets unverändert. Belege
unter `build/codex-agent/r83h-context/`. Keine vollständige64-Bit-Freigabe.

Abnahme R8.3h: elf Gruppen bestanden. Echter O0/O2-Contextkern bewahrt
zulässige Flags und verwirft privilegierte/reservierte Bits ohne Mutation.
Die reale Matrix mit sieben Fällen/14 Generationen belegt lokale Stack-/NT-
Beendigung, erfolgreichen YIELD/abgewiesenen GETPID mit erhaltenen DF/AC/ID,
laufende Flagsprüfung nach IRQ und echten #DB-Trap. Unabhängige Opcodeprüfung
in Objekt und gelinktem ELF sowie negative Quittungs-/Instruktionsoracles;
alle bisherigen Normal-/Fault-/Busy-Gates bestanden, i386-Bytes unverändert.
Belege und offene Grenzen in [CURRENT_WORK](CURRENT_WORK.md).

## R8.3i: phasenunabhängige Kindprozess-Steuerung

Bestand `d4560692`: YIELD eines Kindes prüft noch konkrete IPC-Testphasen;
normaler EXIT verlangt Status77, einen bereits wartenden Elternprozess und
vollständig geschlossene IPC. Für reguläre Programme ist das kein zulässiger
Prozessvertrag. Dieser eine Kontroll-/Terminalgrenzschnitt löst beide
Operationen von den Probephasen, nicht von Identität, Profil oder Budget.

YIELD ist argumentlos; wie bei einer Register-Aufrufkonvention üblich
werden nicht verwendete Argumentregister ignoriert. Es verändert weder IPC
noch CPU-Budget. EXIT behält ausdrücklich den REIST-Raw-uint32-Vertrag;
keine POSIX-wait-Kodierung oder Behauptung von `_exit`-Low8-Bit-Kompatibilität.
Werte oberhalb UINT32_MAX liefern vor Wirkung EINVAL. Normaler Exit bekommt
einen eigenen privaten Terminalgrund, sodass Status128/256/257/258 niemals
als Exception oder Budgetereignis umgedeutet wird. Privater Statusklassifikator
ohne Speicherzugriff, tatsächliche Assembly O0/O2 am Host; kein öffentliches
Strukturlayout oder Syscallindex verändert sich.

Normaler und fehlerhafter Abschluss teilen die bestehenden Identitäts-/Profil-/
Endpoint-/Waitprüfungen und vollständiges Fencing/Reap vor Statuspublikation.
Der normale Zustand bleibt terminal normal, keine fingierte Exception.
Ein zusätzlicher privater8-Byte-Terminalgrund wird nach WAIT gelöscht und
beim Teardown geprüft. Eltern-/Supervisorfehler und allgemeine Prozesszulassung
bleiben offen. Bestehende Ressourcen-/Zeitbudgets und i386 unverändert.

Zwölf Gruppen: neuer Host-/Negativoracle, Bootstrap-/Fault-/Context-/Dokutests,
Normalbuild/-gast, sechs normale Exitstatus0/77/128/256/258/UINT32_MAX über alle
vier IPC-Phasen und je zwei Generationen. Fixture prüft vorher Wide-EXIT mit
EINVAL und YIELD mit unbenutzten, nichtnull Argumentregistern. Unabhängige
ELF-/Status-/Generations-/Eltern-/Queue-/Reap-vor-RUN-Prüfung. Alle bisherigen
24 echten Faultfälle, Busy-/Stack- und sieben Kontextfälle bleiben Gates,
ebenso i386-Byteguard. Belege `build/codex-agent/r83i-control/`.

Abnahme R8.3i: zwölf Gruppen bestanden. Normaler Exit nutzt statt der
bisherigen duplizierten Status77-Bereinigung denselben generationsgebundenen
Terminalpfad mit eigenem Normalgrund/ZOMBIE. Tatsächlicher O0/O2-Statuskern,
24 Exitvarianten/48 Generationen über alle vier IPC-Phasen, Wide-EXIT/EINVAL
und phasenunabhängiges YIELD geprüft; unabhängige Opcode-/Quittungsmutationen.
Alte24 Faultvarianten, Busy-/Stack- und sieben Kontextfälle sowie Normaldialog
und i386-Byteguard bestehen unverändert. Neun Kernelobjekte sind in allen
25 Normal-/Exit-Testbildern identisch. Belege und verbleibende allgemeine
Systemgrenzen in [CURRENT_WORK](CURRENT_WORK.md).

## R8.3j: tatsächliche begrenzte SPAWNV-Argumente

Vorgezogene Voraussetzung R8.3j1, vom Nutzer am11. September nach Rückfrage
freigegeben: Die Exitmatrix des Argumentkandidaten reproduziert Tick4 mit
Kind-SEND_TIMEOUT nach erfolgreicher Eltern-DELEGATE-Rückkehr, aber vor der
Eltern-SEND-Publikation. Der bisherige IPC-Probehandler springt dabei nach
`scheduler_fail`. Das ist keine Kernelkorruption und kein argv-Fehler.
Der Kandidat einschließlich seiner Dokumentation ist vollständig in Git-Stash
`aed0d01b29cae7c9dd0d49100b6503b8ba135f7a` gesichert; alle Laufbelege bleiben
unter `build/codex-agent/r83j-argv/`. Zu diesem Zeitpunkt war R8.3j unangenommen.

R8.3j1 repariert die zusammenhängende IPC-Admission-/Übergabegrenze: geprüfte
lokale Fehler vor Seiteneffekten, Nachrichten-/Capability-Publikation auch
bei Präemption, volle/leere Queue und Widerruf vor/nach Senderwait. Bestehende
REIST-v1-ABI und Ressourcenbudgets bleiben unverändert; keine erfundene
POSIX-/Linux-IPC-Kompatibilität. Tatsächlicher privater Assemblykern O0/O2,
deterministischer Gast für beide Reihenfolgen und alle bisherigen Gastoracles
sind Pflicht. Zusätzliche YIELD-Zählung oder größere Deadlines ersetzen keine
Reparatur. Vertrauenswürdige Ownershipkorruption bleibt fail-closed.

Vierzehn eingefrorene Prüfgruppen stehen in der Queue. Nach ihrer erfolgreichen
Abnahme und lokalem Commit wird R8.3j wiederhergestellt, mit den neuen
IPC-Mechanismen abgeglichen und erneut vollständig abgenommen. Das ist eine
freigegebene Paket-Neuordnung, keine zweite parallele Implementierung.

Abnahme R8.3j1:14 Gruppen bestanden. IPC-Queue-/Waiter-/Widerrufsentscheidungen
sind von Testnutzlasten und Probephasen gelöst; fehlerhafte Nutzerparameter
werden lokal abgewiesen. Vier tatsächliche Produktionsinterleavings und acht
Generationen per GDB beobachtet,13 Mechanismusobjekte bytegleich; Host O0/O2,
alter Normaldialog,24 Exit-/24 Fault-/2 Busy-/7 Contextvarianten und i386-
Byteguard bestanden. Kein Zeit-/Ressourcenbudget gelockert. Der private
Tombstone verhindert erneute Autorität eines geschlossenen Bootstraphandles.
Details und Profilgrenzen in [CURRENT_WORK](CURRENT_WORK.md#r83j1-präemptierbare-ipc-übergabe-repariert).

Bestand `e5da029e`: SPAWNV verlangt exakt zwei Eingaben und token77, der
Kindstack wird unabhängig davon aus Kernelkonstanten aufgebaut. Eine
wiederverwendbare, tatsächlich mit Userdaten gespeiste Startupgrenze ersetzt
diese Kopie. Referenz bleibt System-V AMD64: argc/argv, Null-envp, auxv und
16-Byte-RSP; bestehender REIST-IPC-Auxiliary-Tag, keine neue Autorität.

Ein privater56-Byte-Descriptor enthält Kernelquell-/Zielseitenpointer,
Quell-Virtualbasis, Ziel-Stacktop, User-argv, argc und vertrauenswürdigen
IPC-Auxwert. Quelle ist ausdrücklich die aktuelle private Eltern-Stackseite,
keine neue allgemeine Heap-/VFS-/ELF-Admission. Validate oder Build verwenden
denselben Assemblykern. Alle Pointer-/Count-/Terminatorprüfungen erfolgen
vor erster Zielmutation bzw. Allokation; Kernelmetadatenfehler bleiben fatal,
Userfehler liefern EFAULT/E2BIG. IF0 und private Quelle verhindern TOCTOU.

Profil0..8 Argumente, je höchstens128 Bytes inklusive NUL; leere und mehrfach
referenzierte Strings sind erlaubt, Bytes werden unverändert kopiert.
argc0 verlangt null argv. Bis1024 Stringbytes und1152 Startupbytes passen
in dieselbe4096-Byte-NX-Stackseite und bleiben über dem unteren FP-Probenbereich.
Defaultargc2 behält exakt seinen bisherigen128-Byte-Stackbereich, argv0 an
Stacktop-32 und argv1 an Stacktop-16. Legacy-SPAWN behält seinen Adapter.
Keine öffentliche ABI-/Speicher-/Prozess-/Zeitbudgeterweiterung oder envp-API.

Dreizehn Gruppen: echter O0/O2-Assemblyhost mit vollständigem Byte-/Guard-/
Padding-/Auxoracle,64-Bit-Adressen, Counts0..8, Leer-/Alias-/Maximalstrings
und negativen Nichtmutationsfällen; Bootstrap-/Exit-/Context-/Dokutests,
Normalbuild/-gast und vier reale Startupfälle argc0/3/8/default2 mit negativen
SPAWNV-Proben vor dem erfolgreichen Start. Kind prüft RSP/argv/Bytes/Aux und
liefert Status90+Fall; Eltern-WAIT/RUN und Generation41/42 bleiben Pflicht.
Alle bisherigen24 Exit-,24 Fault-,zwei Busy- und sieben Kontextfälle sowie
i386-Byteguard bleiben Gates. Belege `build/codex-agent/r83j-argv/`.

Historischer Abnahmestopp R8.3j vor R8.3j1: tatsächlicher Argumenthost und alle vier Startupgäste
bestehen, ebenso Normaldialog, alte Fault-/Busy-/Contextgäste und i386-Guard.
Die alte Exitmatrix scheitert jedoch bei Status128/Phase3. GDB reproduziert
eine Präemption zwischen Eltern-DELEGATE und Eltern-SEND: das Kind ruft
SEND_TIMEOUT in der noch leeren Probephase auf, der unveränderte Handler
behandelt dies als Kernelzustandsfehler. Quell- und Artefaktvergleich schließen
geänderte IPC-Handler oder geänderte Exit-Fixtureprogramme aus. Reparatur
erfordert einen eigenen IPC-Zustands-/Interleavingschnitt, nicht ein Umgehen
der Prüfung oder mehr YIELDs. Diese Reparatur ist mit R8.3j1 (`e0dc4d0f`)
abgenommen; der gesicherte Argumentkandidat ist wiederhergestellt und auf
dieser Basis erneut geprüft. Keine vollständige Systemabnahme.
Details und alte Belege in [CURRENT_WORK](CURRENT_WORK.md#r83j-historische-erstabnahme-vor-der-ipc-reparatur).

Abnahme R8.3j: alle13 Gruppen bestanden; echter O0/O2-Startupkern, vollständige
Nichtmutation-/Layoutoracles und vier reale Argumentfälle/acht Generationen.
Normaldialog und alle24 Exit-/24 Fault-/2 Busy-/7 Contextvarianten bestanden.
Die zusätzliche unveränderte IPC-Übergabeprüfung besteht ebenfalls;14
Mechanismusobjekte sind über66 Builds bytegleich. Buildtest schließt gemischte
IPC-/Argumentfixtures vor Effekten aus. i386-Byteguard bestanden; keine
Budgeterweiterung, keine neue ELF-/VFS-/Prozessautorität. Neue Belege unter
`build/codex-agent/r83j-argv/after-ipc/`; vorherige Fehlläufe bleiben erhalten.

## R8.3k: lokale Fehler nichtterminaler Systemaufrufe

Bestand `01ae89a9`: Fehler in READ/WRITE-Deskriptoren, Größen und Puffern,
GETPID-Restregistern sowie SPAWN-/WAIT-Aufrufreihenfolgen führen teilweise
noch direkt zu `scheduler_fail`. Zudem wird der für SPAWN nötige leere
Endpoint erst beim Stackbau nach Allokation geprüft. Diese eine gemeinsame
Admissiongrenze wird zusammenhängend geschlossen, ohne neue Prozessrechte.

Referenz bleibt REIST-v1 mit den bestehenden errno-Kategorien und privatem
System-V-AMD64-Aufrufvertrag. Ein privater80-Byte-Descriptor verbindet
Operation/Argumente mit Kernelquellseite, Userbasis und validiertem Snapshot
von Kindbelegung, Start-/Abschlusszähler und Endpointzustand. Der gemeinsame
reine Assemblykern unterscheidet zugelassen, wirkungsfreier Nulltransfer,
lokaler Aufruffehler und beschädigte Kernelmetadaten. Pointerübersetzung und
Capability-/Generationsnachweise bleiben in den vorhandenen Adaptern.

Zero-length IO liefert0 ohne Zugriff; EBADF für falschen Deskriptor, EINVAL
für Profilgröße/Optionen, EFAULT für Pointer. GETPID ignoriert Restregister.
Das begrenzte eingebettete Pfadprofil liefert ENOENT bzw. ENAMETOOLONG statt
Kernelabbruch. SPAWN prüft vor Allokation: belegtes/erschöpftes Kind EAGAIN,
fehlender Endpoint EBADF, belegte Nachricht/Waiter EAGAIN. WAIT liefert bei
fremdem/fehlendem Kind ECHILD, falschen Optionen EINVAL, schlechtem Ziel
EFAULT; lebendes, derzeit nicht READYes Kind explizit EAGAIN im Bootstrap-
Adapter. Dies ist keine allgemeine POSIX-WAIT- oder Dateisystemkompatibilität.

Unverändert: private Stack-/IPC-/FP-/Generation-/Reap-Verträge, alle Quoten,
1CPU/128MiB/vier Slots/zwei Kinder, parent-EXIT als Bootstrapabschluss.
Allgemeine Eltern-/Supervisorfehler, OOM-Rollback, variable Prozesspools und
Dienste bleiben nachfolgende eigenständige Grenzen, nicht still erteilt.
16 eingefrorene Gruppen inklusive echter O0/O2-Assemblyprüfung, drei realer
Aufruffehler-Fixtures und sämtlicher alter Gastmatrizen. Neue Belege unter
`build/codex-agent/r83k-requests/`; Commit erst nach vollständiger Abnahme.

Historischer Abnahmestopp: Host und Normalgast bestehen, neue Console-/Spawnfälle ebenso.
Die WAIT-Fixture zeigt in Generation42 eine tatsächliche frühe EACCES-Antwort,
die das IPC-Testkind selbst mit UD2 beantwortet. SPAWN und die spätere
Eltern-DELEGATE sind keine atomare Rechteübergabe; der Kernel darf ohne
Capability keinen Sendzugriff gewähren. Eine begrenzte Übergabesynchronisierung
in `arch/x86_64/user/child.asm` ist erforderlich, die Datei liegt aber außerhalb
des eingefrorenen15-Dateien-Pakets. Freigabe steht aus, Kandidat bleibt
uncommittet/aktiv; rote Belege und unauffällige Diagnosen bleiben getrennt.

Freigegebener Nachtrag `ad52c557`: `arch/x86_64/user/child.asm` ist als
16. Datei zugelassen. Alle16 Gategruppen bleiben unverändert. Das Kind darf
frühe EACCES-Antworten bei höchstens acht Sendversuchen und kooperativem YIELD
behandeln; der Kernel erteilt keinerlei implizite Rechte.

Abnahme: alle16 Gruppen bestanden. Der erzwungene Kindlauf vor Delegation
scheitert im Vorher-Bild und besteht mit der korrigierten Fixture. Neue
Aufruffälle3/6 Generationen und alle alten Argument-/IPC-/Exit-/Fault-/Busy-/
Contextmatrizen bestehen. Host O0/O2 plus Nichtmutation/Negativoracles;
15 Mechanismusobjekte über73 Builds bytegleich, i386-Byteguard bestanden.
Belege `build/codex-agent/r83k-requests/`; keine Budgeterweiterung.
