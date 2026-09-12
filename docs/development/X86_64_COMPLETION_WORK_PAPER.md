# Native x86_64-Version: Umsetzung bis zur Systemabnahme

Stand: 12. September 2026. Nutzerpriorität: die 64-Bit-Version fertigstellen.
Basis `fd8dc3d7`; i386 bleibt unveränderter Standard und Rückfallpfad bis zur
eigenen vollständigen Systemabnahme. Dieses Papier ist keine Fertigmeldung.

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
