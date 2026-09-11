# Native x86_64-Version: Umsetzung bis zur Systemabnahme

Stand: 11. September 2026. Nutzerpriorität: die 64-Bit-Version fertigstellen.
Basis `fd8dc3d7`; i386 bleibt unveränderter Standard und Rückfallpfad bis zur
eigenen vollständigen Systemabnahme. Dieses Papier ist keine Fertigmeldung.

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
je Lauf aktiv; spätere Etappen erhalten erst nach Bestandsprüfung ihren Scope.

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
