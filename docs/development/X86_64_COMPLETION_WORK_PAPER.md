# Native x86_64-Version: Umsetzung bis zur Systemabnahme

Stand: 11. September 2026. Nutzerpriorität: die 64-Bit-Version fertigstellen.
Basis `fd8dc3d7`; i386 bleibt unveränderter Standard und Rückfallpfad bis zur
eigenen vollständigen Systemabnahme. Dieses Papier ist keine Fertigmeldung.

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
