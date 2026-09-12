# REIST x86_64 bootstrap contract

Stand: 12. September 2026

R8.3ac führt mit Vertrag `42a41aba` und freigegebener Zusammenführung
`8483d0c5` ein separates `-NativeRuntime` ein: NativeProcesses/IPC/RAM/Heap,
volle64-Bit-PIT-/EOI-/Scheduler-/IPC-/CPU-Zeitwerte und über Runzyklen
fortgeführte Tickzählung. NativeImages/BulkIPC sind ausgeschlossen. Make
benötigt `X86_64_NATIVE_RUNTIME=1` mit denselben vier Abhängigkeiten.
Ticks unter2^60, begrenzte Operationsfristen und32 CPU-Samples pro Generation
bleiben verbindlich; keine automatische Budgeterneuerung. Die vorhandenen
Bootstrapprüfungen leiten ihre Datenseite aus acht bereits zugelassenen
ELF-Seitenrechten ab, ohne zusätzlichen Kernelparser. Alte Profile und der
SHA256 des bisherigen Heapkernels bleiben unverändert.
[Laufzeit-, Seitenbelegungs- und Abnahmevertrag](NATIVE_RUNTIME_CLOCK_CONTRACT.md).
Dies ist keine Freigabe für allgemeines Dateiladen oder residente Dienste.

R8.3ab ergänzt auf Vertrag `3a279429` echte signierte BIOS-Bootmedien.
`scripts/build-x86_64-bootstrap.ps1 -NativeImages` beziehungsweise
`make x86_64-native-image` bündelt NativeProcesses/IPC/RAM/Heap und erzeugt
HDD512MiB plus Rettungsfloppy1,44MiB. Stage1/Stage2, Manifest3 und Research-
Trustpolicy bleiben unverändert. `native-media.json` im x86_64-Ausgabeordner
verweist auf ein separat signiertes und unabhängig geprüftes Paket. Dessen
Kern ist bytegleich mit dem bereits abgenommenen Heapkernel. Die neue BIOS-
Matrix prüft beide Medien,4/8GiB, Signatur-/SHA-/Manifestfehler und A/B-Fallback;
keine normale Dateisystem-Programmausführung oder VMware-Abnahme wird behauptet.
[Signatur-, Veröffentlichungs- und Medienvertrag](NATIVE_BOOT_MEDIA_CONTRACT.md).

R8.3aa ergänzt auf Vertrag `bdb033d8` private native Heapbereiche. Aktivierung:
`-NativeProcesses -NativeRAM -NativeHeap`, für den Gastnachweis zusätzlich
`-NativeIPC`; Make verwendet entsprechend `X86_64_NATIVE_HEAP=1`. Bestehende
Syscalls4/5/6 werden nur in expliziten Profilen zugelassen. Jeder der vier
Tasks besitzt128 Regionen mit zusammen höchstens512MiB ab VA0x100000000,
4KiB/RW/NX. Gespeicherte Aufträge leisten höchstens64 Seitenarbeitsschritte
vor einer Schedulerübergabe; unabhängige Prozesse und IRQs bleiben ausführbar.
Reap widerruft zunächst IPC und gibt danach sämtliche Heap-/Tabellen-/
Schutzframes frei, bevor die bisherigen13 Taskframes freigegeben werden.
Privater Aufbau4 ergänzt397704Byte geschützten Heapzustand ab physisch0x653000;
das gesamte RW/NX-Metadatenareal beträgt7102464Byte. Aufbau2/3,16KiB Stack,
32 CPU-Samples,256Ticks und10s-Gastfrist bleiben unverändert.
[Heapvertrag und Nachweisgrenzen](NATIVE_PRIVATE_HEAP_CONTRACT.md).

R8.3z ist auf `3e80a1c7` vor Umsetzung eingefroren. Der optionale NativeRAM-
Pfad bündelt physische RAM-Karte, Reservierungen, geschützte Allokation und
alle physischen64-Bit-Verbraucher. Private C-Metadaten erhalten dafür einen
expliziten Aufbau3, nicht eine Lockerung des bisherigen Aufbaus2.
Grenzen und Pflichtnachweise: [Speichervertrag](NATIVE_PHYSICAL_MEMORY_CONTRACT.md).

R8.3z implementiert diesen Pfad auf Vertrag `48c47a09`. Aktivierung im
Windows-Build mit `-NativeRAM`, im Make-Build mit `X86_64_NATIVE_RAM=1`.
Die Abnahme kombiniert `-NativeProcesses -NativeIPC -NativeRAM` und dieselbe
Kerneldatei für1/4/8GiB. Physische Kapazität16GiB; private Userblätter bleiben
4KiB, Image-/Task-/IPC-Grenzen bleiben beim jeweiligen bisherigen Profil.
4,531,096Byte C-Zustand und6,701,056Byte Gesamtareal ab physisch2MiB sind
NOBITS/RW/NX. Nur vollständig nutzbare512-Frame-Bereiche erhalten2MiB-
Direct-Map-Blätter; gemischte Bereiche benötigen eine von höchstens512 Tabellen.
Die Gastmatrix prüft reale hohe Frames, Seitenrechte, genaue Freigaben und
Fehlkarten innerhalb der ursprünglichen10s-Frist je Gast.

R8.3y ist vor Umsetzung auf `89ab012f` eingefroren. Die bestehende REIST-ABI
dispatcht beide Nachrichtenformate auf50/51/53/54; Bulk erfordert keine breiteren
Syscallprofile. Private Bindung v2 erweitert die maximale Nachricht auf2060Byte
und bewahrt die ursprüngliche Empfangskapazität auch bei zurückgegebenem v1.
Header12Byte zuerst prüfen, dann genau140/2060Byte über alle betroffenen Seiten,
vor Effekten und nochmals vor verzögerter Ausgabe im eigenen Adressraum.
Die alte140Byte-Adressprüfung bleibt bestehen; ein expliziter Dateneinstieg
erlaubt2060Byte mit denselben Eigentums-/P/U/W/NX-Prüfungen. Alle Aussagen zu
208/216Byte weiter unten beschreiben den akzeptierten historischen X-Stand.

R8.3y umgesetzt auf `0068bdaf`: Private Anfrage2136Byte mit64Byte-Kontrollkopf,
2060Byte-Nachrichtenunion, Handle bei2124 und ursprünglicher Kopiergröße bei2128.
Pending ergänzt Generation/Zustand auf2144Byte.35 feste Integritätsobjekte je
Slot schützen zwei Kontrollabschnitte, drei kleine Nachrichtenabschnitte und
bei aktivem Bulkauftrag dreißig zusätzliche Abschnitte. Metadaten werden vor
der Auswahl geprüft; ein inaktiver großer Schwanz wird nie konsumiert und
bei neuer Anfrage durch die vollständige kopierte Eingabe ersetzt. Reap/Take
nullen den gesamten Pendingdatensatz. Integritätsschatten werden nicht als
forensisch gelöscht behauptet; gemeinsame Endpointgenerationen bleiben erhalten.

Die v2-Empfangsoperation übernimmt die gemeinsame Zweikanalsemantik: zuerst
bereits vorhandene v1-FIFO-Nachrichten, sonst der separate Bulkplatz. Keine
globale FIFO-Reihenfolge über beide Kanäle. Erfolgreiche v1-Ausgabe an einen
v2-Empfänger schreibt dennoch2060Byte mit genulltem Rest. Headerfehler ergeben
vor voller Bereichsprüfung EINVAL, unzugängliche ausgewählte Bereiche EFAULT.
Rechte, Längenfehler und Queueoperationen prüft unverändert der gemeinsame Kern.
Die Gastvariante `-NativeProcesses -NativeIPC -NativeBulkIPC` testet beide
Empfangsformen, überlaufende Seitengrenzen, Druck auf den Bulkplatz sowie alle
vier bestehenden Fehler-/Generationsfälle; der Usercode allein wählt die Variante.

R8.3x ist vor Umsetzung eingefroren: vorhandenes REIST-IPC-v1 mit den
Syscallnummern49..55/58 und POSIX-errno-Bezeichnungen, keine POSIX-IPC-
Kompatibilitätsbehauptung. Der optionale NativeIPC-Lauf delegiert diese Rechte
explizit an unabhängige Tasks. Die unveränderten Common-Operationen arbeiten
intern mit Timeout0; native ausstehende Aufträge besitzen eigene endliche
Deadlines und generationsgebundene, kopierte Eingaben. Höchstens ein Auftrag
und ein Wartelisteneintrag je Task, niemals eine C-Stackfortsetzung. Normale
Operationen warten maximal1000ms, Timeout0 ergibt EAGAIN. Timeout ergibt
ETIMEDOUT; Entzug während eines bereits wartenden Auftrags EPIPE, ein sofort
benutztes altes Handle EBADF. Reap entzieht vor Framefreigabe sämtliche Rechte.

Ein separater kleiner IPC-Prozessdatensatz bindet PID/Generation und lokale
Capabilities; der große i386-Prozessdatensatz wird weder importiert noch auf
native Taskdaten gelegt. IF0/SingleCPU ersetzt die alte Spinlock-Plattform;
unerwartete Konkurrenz, unkorrektierbare Integrität oder ein versuchter
gemeinsamer Blocking-Aufruf sind vertrauenswürdige Zustandsfehler, kein
Userspace-Erfolg. Native IRQ-Klassifikation bleibt rein lesend.
System-V-ELF64-Funktionsbindungen werden gegebenenfalls aus exakt validierten
STT_FUNC-Symbolen generiert; normale SHF_MERGE/SHF_STRINGS-Konstantenmetadaten
dürfen die tatsächlichen W^X/NX-Loadrechte nicht verändern.

R8.3x umgesetzt auf `27d5b50c`: `reist_native_ipc` ist der einzige neue
allowlistgebundene C-Aufruf. Er wird als einmaliges globales STT_FUNC-Symbol
vollständig innerhalb des validierten Textsegments geprüft; seine Adresse
wird in den NASM-Include geschrieben, nicht geraten. Der tatsächlich
gelinkte Konstantenbereich bleibt bei SHF_ALLOC: die vorgesehene optionale
SHF_MERGE/SHF_STRINGS-Erweiterung wurde nicht benötigt und nicht implementiert.
Die strengen v2-ELF-Abschnitts-/Loadrechte sind unverändert.

Der private208Byte-Auftrag enthält fünf64-Bit-Eingabewörter, Resultat,
Deadline, Abschlussmaske, eine140Byte-Nachricht und ein32-Bit-Handle.
Die vier108Byte-Prozessansichten und vier216Byte-Pendingdatensätze werden
gegen feste redundante Integritätssnapshots geprüft. Retirementgenerationen
sind ebenfalls geschützt. Init-/Komplement-/Busywörter bleiben explizit
volatile uint32, nach separater Produktionsübersetzung maschinell geprüft;
ein validierter Init-Snapshot verhindert mehrfaches Lesen für diese Entscheidung.
Unkorrigierbarer Zustand oder unerlaubte gemeinsame Blocking-/Locknutzung
führt über UD2 in die vorhandene vertrauenswürdige Kernel-Fatalgrenze.
Dies ersetzt keinen vollständigen Watchdog-/SMP-Abnahmenachweis.

IPC-PIDs entsprechen hier den vorhandenen GETPID-Generationen und müssen
positive int32 bleiben; ein neuer Lauf wird vor Allocation verworfen, wenn
diese Grenze überschritten würde. Sonstige Native-Profiles bleiben unverändert.
Die endliche Wartezeit muss noch innerhalb des bestehenden256-Tick-Laufs
liegen, sonst EINVAL vor Queueseiteneffekten. V1-Nachrichten und ihre genaue
Fehlercode-Präzedenz prüft allein der gemeinsame Kern. Timer erledigen nur
fällige Timeouts; Nachrichtenzustand wird ausschließlich bei IPC-Ereignissen
erneut versucht. Ein Ende mit Rest-Capabilities/Endpoints/Nachrichten ist fatal.
Inaktive Endpunktgenerationen werden nicht auf null zurückgesetzt und alte
Queuebytes nicht als forensisch gelöscht behauptet. Tatsächlich null sind die
Prozessansicht, Pendingdaten und anschließend die freigegebenen Taskframes.

Der optionale `-NativeProcesses -NativeIPC`-Gast delegiert nur49..55/58 und
verwendet32 Samples je Task innerhalb der unveränderten Maximalgrenze.
Vier ausschließlich nutzerseitige Fälle `-NativeIPCCase 0..3` belegen32
Tasklebensläufe,78 Warteabschlüsse,112 reale Copyouts und32 IPC-Fences vor
Framefreigabe;17 Kernobjekte sind über alle Fälle bytegleich. Normales
Gesamt-ELF/User-ELFs, alte Prozessgäste und i386-Referenzen bleiben unverändert.
Die Grenzen128MiB/vier Tasks, Bulk-/breite Profile, Laufzeit-ELF-Start,
Dienste und vollständige64-Bit-OS-Abnahme bleiben sichtbar offen.

R8.3w, vor Umsetzung eingefroren: Der bestehende gemeinsame Integritätskern
bleibt quellgleich. Der x86-IRQ-Header verwendet in Long Mode64-Bit-Stack-
operanden; das historische uint32-Statustoken enthält weiterhin die definierten
RFLAGS-Statusbits, keine Adresse. Die i386-Präprozessor-/Maschinencodegleichheit
wird gegen `12f93954` geprüft. Optionaler C-Bootgast `-CIntegrityProbe` verwendet
reale IRQ-Save/Restore-Ausführung und die unveränderten SECDED-/CRC-/Copy-
Publikationsregeln. Er injiziert nur eigene feste Testobjekte und muss alle
normalen Folgeprüfungen erreichen. Dies übernimmt einen existierenden
Integritätsmechanismus, erteilt aber weder IPC- noch Geräte-/SMP-Rechte.

Umsetzung `16328ec8`: der native Compiler verwendet für IRQ-Tokens intern
`uint64_t` und `pushfq`/native `pop`, bei Restore einen nullerweiterten
Operanden und `popfq`. Die i386-Zweige sind unverändert vorverarbeitet und
maschinell bytegleich. Im privaten Testprofil wird exakt der bestehende
`kernel/init/critical_object.c` gelinkt; nur dessen compilerbedingte `memcpy`-
Abhängigkeit wird aus der vorhandenen Stringbibliothek übernommen. Sonstige
Strings-/Parserfunktionen werden bereits beim partiellen Link verworfen.
Der Gast führt1650 Prüflesungen mit Einzelbitfehlern in beiden Kopien,
unabhängiger Kopienrettung, unkorrektierbaren/widersprüchlichen Kopien,
Kapazitäts-/Versions-/Semantik-/Sequenz- und Busyfehlern aus. Ein unabhängiger
Test-Bitwalk versiegelt ausschließlich das gültige Maximal-Sequenz-Testobjekt,
keine alternative Produktionsarithmetik. Ein IF=1-Test maskiert und restauriert
beide PIC-Masken, prüft Save/Restore, reale Leseoperation und Stack-Canaries.
Danach sind alle Testobjekte und Handoffs null und die alte Shell läuft weiter.
Zwölf GDB-Kontrollpunkte und zwei tatsächliche C-Aufrufpaare sind rein lesend;
signierte Registerdarstellungen werden als unveränderte64-Bit-Muster verglichen.
Belege unter `build/codex-agent/r83w-integrity/`; normale Boot-/Userartefakte
bleiben byteidentisch. Das ist kein neuer nativer Userspace-Lockvertrag und
kein allgemeiner IPC-, SMP- oder vollständiger OS-Nachweis.

R8.3v, vor Implementierung eingefroren12.September: privates C-Payloadlayout v2.
System-V-ELF64/EM_X86_64/ET_EXEC bleibt der native C-Linkvertrag, ELF32 nur der
Multiboot-Transportcontainer. Physische feste Hüllbereiche: Bridge0x184000/4KiB,
Text0x185000/64KiB RX, Konstanten0x195000/32KiB R/NX, Daten0x19D000/16KiB RW/NX,
BSS0x1A1000/256KiB RW/NX und Handoffs0x1FF000/192Byte RW/NX. Es werden nur die
tatsächlich belegten Seiten abgebildet, Lücken bleiben nicht präsent. Diese
Grenzen gelten für den gelinkten Bootstrapkernel, nicht für Userheaps.
Der gesamte tatsächliche C-BSS-Bereich wird vor Ausführung initialisiert;
die separaten Handoffstrukturen bleiben128/64Byte v1, ihre privaten Adressen
sind im neuen Layout versioniert. Textentry, Boot-Stateobjekte und drei feste
C-Bridgeadressen müssen den tatsächlichen ELF-Symbolen entsprechen. Ein
Buildzeitprüfer erzeugt erst nach vollständiger ELF-/Bereichs-/Rechteprüfung
die Abschnittsbytes und BSS-Größendefinition. Keine Runtime-ELF-Ausweitung,
unbekannten allozierten Abschnitte, Konstruktoren, TLS, dynamischen Bindungen,
Relokationen, W+X oder impliziten Hosted-Runtime-Abhängigkeiten. Alte datierte
Einseitenangaben unten bleiben die Historie des Layouts v1, nicht das neue Ziel.

Implementiert auf Vertrag `9b8cd75e`: `config/x86_64_c_payload.ld` bindet
Entry sowie32-Byte-Bootobjekte ausdrücklich als erste Abschnittsobjekte.
`scripts/build_x86_64_c_payload.py` akzeptiert höchstens1MiB ELF-Datei,
32 Programmheader,128 Sektionen und4096 Symbole der einzigen Symboltabelle.
Er prüft alle Datei-/Ladeüberlappungen, Rechte, Größen und acht feste Bindungen,
extrahiert erst danach Text/RoData/Data sowie tatsächliche BSS-Größe und
verifiziert das Ergebnis zusätzlich am gelinkten äußeren Container. Statische
Section-/Bridgeadressen bleiben private Buildbindungen, keine neue User-ABI.
Die Datei-Veröffentlichung ist jeweils atomar, nicht als Mehrdateitransaktion;
Make stoppt bei einem Fehler vor Einbettung/Erfolgsmeldung. Eigene exklusive
Stagingdateien erben die Ziel-ACLs, fremde Kollisionen werden nicht gelöscht.

`-CPayloadProbe` bindet eine zusätzliche echte C-Übersetzungseinheit ein:
7832Byte RX-Text einschließlich ausgeführter mehrseitiger Instruktionsfolge,
9122Byte Konstanten,9032Byte initialisierte Daten und12032Byte BSS. Nur dieser
Testcode bereinigt seine eigenen zusätzlichen Arrays; der normale Bootabschluss
löscht weiterhin genau seine32-Byte-Stateobjekte und128/64-Byte-Handoffs.
Die Gastabnahme vergiftet vier exakte neue BSS-Bytes vor Startup, schreibt
danach keinen Zustand und kontrolliert vor/nach C sämtliche13 belegten Seiten,
111 Lücken, WP/NXE und nicht vorhandene Bootstrap-Direct-Map-Aliase. Alle
vorhandenen Shell-/Prozess-/Frame-Reap-Orakel bleiben unverändert erfolgreich.
Host-Mutationen beschädigter Artefakte und reale Linkfehler ergänzen den Gast,
ersetzen ihn nicht. Belege unter `build/codex-agent/r83v-c-payload/`.

Ergänzung12.September2026, R8.3u: Das vor Implementierung eingefrorene optionale
`-NativeProcesses`-Profil verbindet bestehende Kernelmechanismen ohne feste
Shell-/Kindrollen. Ein privater144-Byte-Deskriptor v1 enthält Anzahl1..4 sowie
vier32-Byte-Einträge mit opakem Userargument, expliziter Syscallmaske, CPU-Samples
und nullreserviertem Wort; unbenutzte Einträge sind vollständig null. Er ist
nur über die begrenzte vertrauenswürdige C-Bootkoordination zugänglich, kein
Userspace-Spawnrecht. Der private Kernelaufruf verwendet SysV AMD64, die
User-Syscalls unveränderte REIST-v1-Nummern. Der Demo-Startadapter übergibt das
opake Argument in RDI; er behauptet noch keinen argc/envp/auxv-Prozessstart.
keine POSIX-Prozess-/Wait-Kompatibilitätsbehauptung. GETPID liefert die positive
32-Bit-Taskgeneration im separaten nativen Laufnamensraum; EXIT behält uint32.
Erlaubbar sind EXIT/GETPID/YIELD/SLEEP_MS/MONOTONIC_MS. Sleep1..100ms wird auf
10ms-PIT-Ticks aufgerundet; jeder Task erhält1..32 CPU-Samples, der Lauf maximal
256 Ticks und die abgenommene IRQ-Fortschrittslease. Nicht gewährte Operationen
liefern EACCES, ungültige Argumente EINVAL. Keine IO-/IPC-/Geräteautorität.
Die Ressourcenquoten sind Profilgrenzen dieses128MiB-Prototyps, keine künftigen
OS-Höchstwerte. Ein Userfehler fencet und reapt nur seinen Task, nach Prüfung
des gesamten gebundenen Laufzustands. Generationen werden zwischen zugelassenen
Läufen nicht zurückgesetzt; Überlauf lehnt ab. Ein neuer Lauf ist eine explizite
Zulassung des Aufrufers, kein Kernel-Restartentscheid. Reap erfolgt nach IRQ-EOI
auf Kernelroot/-stack, Profilwiderruf vor Framefreigabe, FP/Budget/Identität null.
Der unveränderte eingebettete ELF-Loader ist weiterhin Bootstrap-Migrationsschuld,
nicht Vorbild für einen produktiven Ring-0-Loader. Alte Prüfprofile bleiben
unverändert und der Standardbuild behält byteidentische User-ELFs.

Der64-Byte-C-Kontrollhandoff v1 ergänzt Service2 mit Flags0x19
(Runqueue, kein Geräterecht, eingebettetes Prozess-ELF). Service1/Flags0x0F
für die bisherige Shell bleiben unverändert. Der neue begrenzte C-Rodata-
Bridgepfad bei0xFFFFFFFF80184200 prüft Descriptorbereich, IF=0, Kernelroot und
Nicht-Reentranz. Die Bootkoordination lässt zwei Gruppen desselben Demo-ELFs
zu;1..4 Einträge und Maskensubsets werden im tatsächlichen Hostkern geprüft.
Die positive Taskgeneration ist laufübergreifend monoton; kein Prozess kann
dieses privilegierte Zulassungsobjekt selbst erzeugen oder ändern.

Private32-Byte-Abschlussquittung `REIST_X86_64_PROCESS_REAP_OK v1=`:
vier little-endian uint32 (Slot, Generation, Rohstatus, terminaler Taskzustand)
und zwei uint64 (CPU-Samples, RIP), als64 Hexziffern. Sie folgt erst auf
Profilwiderruf, normale Frame-/FP-/Budgetfreigabe, Identitätsretirement und
erneute Prüfung der überlebenden Peers. Kein erwarteter Status oder Testablauf
entscheidet über erfolgreiche Kernelbereinigung. `PROCESS_RUN_OK` bestätigt
einen vollständig bereinigten zugelassenen Lauf; der alternative finale Marker
ist `REIST_X86_64_NATIVE_PROCESSES_OK`, ausdrücklich nicht Shell-Kompatibilität.
Die privaten Syscall-Stack-/Registerkopien werden ebenfalls gelöscht. Normale
und beobachtete Gastmatrizen belegen diese Reihenfolge; die Abschlussorakel
lehnen fehlende, doppelte, falsch zugeordnete oder unvollständige Reaps ab.

Ergänzung12.September2026, R8.3t: Im explizit kurzlebigen Bootstraplauf kann
die Eigentümergeneration40 auch mit lebendem oder bereits gereaptem Kind
enden. Kinder41/42 besitzen kein unabhängiges Lebensdauerrecht. Dies ist keine
POSIX-Orphan-/Adoptionssemantik und kein neuer Ring-0-Service-Supervisor.
Allgemeine Prozessadoption, Restartpolicy und Dienstzulassung bleiben offen.

EXIT/uint32, klassifizierte Intel-Userexceptions, unbrauchbarer SYSCALL-/IRQ-
Rückkehrkontext und erschöpftes CPU-Sample-Budget benutzen denselben begrenzten
Owner-Terminalpfad. Ein reiner Besitzprüfer validiert beide Generationen,
Profile, Budgets, exakte Queue-/Deadlineeinträge, Endpoint/Capabilities und
gegebenenfalls den schon gereapten Terminalrecord. Vier Slots, höchstens zwei
sequentielle Kinder und128MiB bleiben die Prototypgrenzen. Fremde/stale Tasks,
Profilabweichungen und widersprüchliche Besitzrecords werden nicht gelöscht,
um einen Erfolg zu erzwingen. Die maximal26 privaten Frame-IDs beider Tasks
werden vor dem Fencing auch auf gegenseitige Aliasierung geprüft.

Erst nach erfolgreicher Prüfung: Lauf sperren, genaue Queue-/Deadlinebindung
entfernen, beide Taskprofile und IPC-Rechte widerrufen, auf Kernel-CR3 wechseln,
lebendes Kind über den bisherigen Frame-/FP-/Identitätsreap freigeben und
danach den Eigentümer reapen. Ein bereits gereaptes Kind wird nur konsumiert;
kein zweiter Free und keine verspätete WAIT-Kopie an den toten Elternprozess.
Klassifizierter Eigentümerfehler nutzt TASK_FAULTED und den privaten Event75,
normaler EXIT weiter TASK_EXITED/Event72. Freier Speicher, Tabellen, FP,
Budgets, Profile, IPC, Queue, Deadlines und Tombstones werden abschließend
geprüft; Forced-Cleanup kann diesen Erfolgspfad nicht erzeugen.

Privater Diagnosebeleg `OWNER_CONTAINED_OK v1=`:40 Bytes als Hex in expliziter
Little-Endian-Reihenfolge, sechs uint32-Felder (Plan1/2/3/4 für kein Kind/READY/
BLOCKED/schon gereapt, klassifizierte Ursache0/1, Endpoint, Nachrichtenbelegung,
Deadlinebelegung, Kindgeneration), danach uint64 RIP und CPU-Samples. Der
bisherige SHELL_REAP-Beleg nennt Rohstatus, Reapzahl und Generationen. Der
historische EXIT_OK-Abschlussmarker bleibt kompatibel; SHELL_ERROR macht
Nichtnullstatus für alte Normalprüfer weiterhin zum Fehler. Der Kernel läuft
nach validiertem Abschluss weiter, ohne einen Wiederanlauf zu behaupten.

CPU-Budgets: Eigentümer128, Kind32 Samples; gemeinsamer PIT-Zähler maximal256
bei nominal100Hz. Die bisher über den ganzen Lauf verwendeten3Milliarden
TSC-Zyklen liefen auf der Referenzmaschine bereits bei80Samples ab. Nach
expliziter Scope-Freigabe gilt nur im SHELL-Modus eine Fortschrittslease:
Die gleiche3e9-Zyklengrenze wird erst nach validiertem Interrupt-/Kontext-/
Deadlinefortschritt erneuert, vor EOI. Rücklauf, Überlauf, Zählerabweichung
und abgelaufene Lease werden abgelehnt; Gesamtzähler und CPU-Budgets werden
nicht zurückgesetzt. Andere Timermodi behalten ihre bisherige absolute Frist.
TSC-Zyklen sind keine behaupteten Sekunden. Bei ausbleibendem Interrupt ist
diese Prüfung kein unabhängiger Hardwarewatchdog; der Gastprüfer bleibt auf
zehn Sekunden begrenzt. Keine Frequenzkalibrierung oder Produktions-FTTI-Zusage.

Nachweise: tatsächliche O0/O2-Assemblerzulassung und Zeitrechnung mit negativen
Mutationen;52 Gastdialoge für zehn Terminierungsarten und beide Kindhistorien;
fünf zusätzliche rein lesende Frame-/Fencing-/Nullzustandsbeobachtungen.
Alle Dialoge verwenden dasselbe reine User-Fixture-ELF, keine Kernel-Testflags
oder verlangsamte QEMU-CPU. Historischer fataler Owner-UD2 und80-Tick-TSC-Abbruch
bleiben erhalten. Die drei normalen User-ELFs bleiben byteidentisch.

Ergänzung12.September2026, R8.3s: Geordneter Shellabschluss verlangt keinen
bestimmten Testdialog mehr. Null, ein oder zwei vollständig gereapte Kinder
sind zulässig; 18 gelesene Bytes und acht Schreibaufrufe bleiben Obergrenzen.
Vor der Zustandsänderung müssen Runqueue, Kind-/Waitbindung, Endpoints und
übrige Taskslots quieszent sein. Der Abschlussprüfer leitet Ereignisfolge,
Reapzahl und letzte Generation aus derselben validierten Kindzahl ab. Er
prüft auch die feste Vier-Slot-Kapazität des privaten Identitätsrecords.
Frame-, Profil-, FP-, Deadline- und Tombstone-Prüfungen bleiben vollständig.

Referenz bleibt REIST-Syscall-v1: EXIT übernimmt einen uint32-Rohstatus;
kein POSIX-Waitstatus und keine Reduktion auf acht Bits. Werte außerhalb von
uint32 und nichtnullige reservierte Argumente liefern lokal EINVAL, bevor
Retirement beginnt. Die vorhandene geordnete Freigabe erzeugt erst nach
vollständigem Cleanup einen privaten seriellen Status-/Generationsbeleg.
Nichtnulliger Programmstatus setzt zusätzlich den bisherigen SHELL_ERROR-
Marker: alte Normalprüfer lehnen ihn weiterhin ab, obwohl der Kern sauber
weiterläuft. Keine neue Syscallnummer oder erweiterte Prozessautorität.
Elternende bei noch lebendem Kind/Endpoint bleibt ausdrücklich ein eigener
offener Recovery-Schnitt; diese Abnahme behauptet dafür keine Isolation.

Reine Userspace-Fixtures prüfen sechs ungültige Argumentkombinationen und
vier Rohstatusfälle. In 30 endlichen QEMU-Dialogen mit/ohne INFO werden alle
drei Kindzahlen geprüft. 25 Mechanismus-/Probe-/Kindobjekte bleiben identisch.
Beim ELF-Embedding-Adapter werden zusätzlich sämtliche Instruktionsbytes
gegen den alten Loader geprüft; ausschließlich fünf nachweislich von der
Shellgröße abhängige R_386_PC32-Addenden und deren exakte Längen-Konstante
werden auf die Referenz normalisiert. Kein Ignorieren beliebiger Unterschiede.
Der tatsächliche Abschlussprüfer läuft im O0/O2-Hosttest; volatile Bytezugriffe
bilden dort die in C nicht ausdrückliche Aliasbeziehung der Assemblylabels ab.

Ergänzung12. September2026, R8.3r: Derselbe Task-Tabellenrecord erlaubt privat
PF_X=1 für genau ein Instruktionsbyte. Intel64 P/U wird über alle Ebenen
verknüpft, gesetztes NX auf einer beliebigen Ebene verweigert Ausführung;
Schreibrecht ist keine Voraussetzung. Der read-only Prüfkern erzeugt keine
Mappingrechte. Aufrufende Syscall-/IRQ-/Kontextadapter validieren die reale
Taskbindung vor Rückkehr bzw. Kontextpublikation, statt globale ELF-Seiten
als Ausführungsautorität zu benutzen. Bei gültiger Kindidentität ist eine
unzulässige Rückkehradresse lokal raw258; im IRQ wird nur klassifiziert und
erst nach EOI retired. Bereits ausgelöste Userfaults benötigen keine gültige
Rückkehradresse und behalten den vorhandenen vollständigen Fault-Reap.
Andere Kernelkorruption bleibt fatal. Alle bisherigen Kapazitäten bleiben.

Ergänzung12. September2026, R8.3q: Terminal-/IPC-Userpuffer werden aus den
tatsächlichen Tabellen des aufrufenden Tasks zugelassen, nicht aus globalen
ELF-Parserflags. Referenz: [Intel64 SDM Vol3A, Kapitel4 Paging](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html).
P/U gilt auf allen vier Ebenen, Schreiben erfordert zusätzlich W; NX ist kein
Leseverbot. Nur die bereits verwendeten4KiB-Einträge mit P/W/U/A, Blatt-D
und NX sind zulässig, keine großen Seiten/PKU oder neuen Mappingrechte.

Privater32-Byte-SysV-AMD64-Record: Taskpointer, Pointer auf vier physische
Tabellenrecords, Generation, aktives CR3. Gepinnte Kernelobjekte und IF0
bleiben Aufruferpflicht. Identität, RUNNING, CR3/PML4, vier eindeutige Frames
im128MiB-Profil und exakte Tabellenkette werden vor Nutzung geprüft; ein
Blatt darf keine eigene Tabelle aliasieren, die Stackseite muss taskgebunden
sein. Maximal140 Bytes/zwei Blätter im bisherigen achtseitigen Imagebereich
plus Stack. Keine Allokation, Datenkopie, Userdereferenz oder Zustandsmutation
im Kern. Ungültige Userbereiche/Rechte werden lokal abgelehnt, beschädigte
Bindungen/Topologie bleiben fatal. Kein Schutzclaim für beliebig beschädigte
gepinnte Kernelpointer und keine allgemeine SMP-/Prozesszulassung.

R8.3p (11. September2026): Ein privater32-Byte-SysV-AMD64-Bindungsrecord
benennt die bereits gehaltenen8 Privatframe-, Stack-,4 Tabellen- und
CR3-Records. Er ist kein Userpointervertrag. Alle gebundenen Bereiche sind
gepinnte disjunkte Kernelobjekte; der Aufrufer serialisiert IF0 und fencet
den Zieltask. Der Adapter verweigert seine aktuell aktive PML4 vor Effekten.
Normaler Reap/Forced-Cleanup verwendet weiter Kernel-CR3, ein fehlgeschlagener
unveröffentlichter Aufbau besitzt keinen aktiven Kindadressraum.

Der gemeinsame Freigabekern prüft Pointerbereiche, alle maximal13 eindeutigen
4KiB-Frame-IDs im bestehenden128MiB-Profil sowie CR3/PML4 vor jedem ersten
Free. Privatseiten, Stack, PT, PD, PDPT, PML4 werden in dieser Reihenfolge
freigegeben. Nur erfolgreiche Records werden genullt; erster Backendfehler
stoppt mit erhaltenem Restbesitz. Der freie Framebestand muss um genau die
erfolgreichen Freigaben dieses Aufrufs steigen. Kein erneutes Freigeben bereits
gelöschter Records. FP-Scrub folgt erfolgreichem Cleanup; Generation/Profile/
Budget/Identität bleiben außen im bisherigen Lifecycle. Normale Freigabe und
Rollback sind gemeinsame Konsumenten. Kein Wiederanlauf nach Kernelkorruption,
keine Behauptung allgemeiner Dienste, größerer Kapazitäten oder SMP-Freigabe.

Genehmigter IPC-Prüfernachtrag d227a3ef: Drei read-only Hardware-Haltepunkte,
gepaarte Plan-Eintritte/Aufruferrückkehr mit Identitäts-/Stack-/Eingabe-/
Ergebnisprüfung. Reale Instruktionsbytes bestimmen CALL-Ziel/Rückkehrstelle;
geprüftes Einzelschreiten ausschließlich der beiden nicht verzweigenden CMPs
bei IF0, jeweiliger Haltepunkt sofort wieder scharf. Keine verworfenen oder
deduplizierten Ereignisse. Alle alten exakten Branch-/Count-Anforderungen,
maximal256 Aufrufe und10s Gastdeadline bleiben;256KiB Beobachterausgabe direkt
in Datei verhindert GDB-Blockierung durch eine undrainierte Windows-Pipe.

R8.3o (11. September2026): Gemeinsamer privater System-V-AMD64-Mappingkern
für alle bisherigen Scheduler-Modi. Ein192-Byte-Plan benennt vier bereits
reservierte Seitentabellen, acht gestagte Quellseiten/ELF-Flags, acht optionale
private Schreibseiten, Stack und zwei geprüfte Kernel-PML4-Vorlagen.
Intel64-Vier-Level-Paging,4KiB-Seiten: R/RX geteilt und read-only; R ist NX,
RW privat kopiert und NX; Stack privat RW/NX. Nicht benannte Userseiten
bleiben absent. Direct Map bleibt NX/Supervisor, Kernelcode Supervisor.
Physische Records und Pointer sind eindeutig und nicht mit dem Plan oder
Kernelvorlagenframes aliasiert. Alle Zielseiten sind vor Effekten vollständig
nullgeprüft. Keine Allokation, Freigabe, Task-/CR3-Publikation oder Rollenpolitik
im Mappingkern. Der Aufrufer hält Quellen/Ziele gepinnt und serialisiert IF0;
er behält jeden Besitz auch bei Ablehnung und benutzt vorhandenen Rollback.
Keine allgemeine Speicherkarte,128MiB-/1CPU-Bootstrapgrenzen unverändert.
Neue R/RX-ELF-Fixtures beweisen lesbare Daten, PF bei Schreiben/NX-Ausführung,
Reap und Elternfortschritt, nicht vollständige native Anwendungsfreigabe.

Genehmigter Fixture-Nachtrag2e963b34: Ein10-ms-IPC-Timeout ist auch mit
lauffähigem Peer legal. Der Test-Parent wiederholt einen Peer-Receive maximal
achtmal bei ETIMEDOUT; der Test-Sender wartet auf CLOSE mit maximal acht
SEND_TIMEOUT-Versuchen, nur EACCES/ETIMEDOUT sind wiederholbar und YIELD
gibt dazwischen den Owner frei. EBADF bleibt das einzig erfolgreiche
Widerrufsergebnis. Explizite Timeoutprobes, Schutzrechte, PIT-/CPU-Budgets
und verpflichtende echte Close-/Wakeup-Gastbelege bleiben unverändert.

R8.3n (11. September2026): Der private88-Byte-ELF-Kontext bleibt unverändert.
Ein gemeinsamer System-V-AMD64-Freigabekern validiert alle acht Frame-/Flag-
Records vor Effekten (ELF PF_R, PF_R|PF_X oder PF_R|PF_W, eindeutige
ausgerichtete Frames im128MiB-Profil). Markierte noch unallokierte Seiten
bleiben für Ladefehler/OOM-Rollback zulässig. Erfolgreiche Freigaben löschen
nur eigene Records; fehlgeschlagene behalten Besitz. Wiederholung ist
idempotent. Der globale Freiframezähler muss um genau die erfolgreich
freigegebenen Frames steigen, bei serialisiertem Single-CPU-Betrieb unter
IF0. Der historische Ladefreizähler ist nur Diagnose: andere Eigentümer
dürfen seit dem Laden Speicher belegt haben. Metadaten-/Backend-/Bilanzfehler
bleiben fatal. Die abschließende Gesamtbilanz und alle Spawn-/Reap-Gates
bleiben erhalten. Konsumenten vorher fencen/reapen; keine neue Referenzzählung,
keine beliebigen Userpointer oder konkurrierende Eigentumsänderungen.
Sechs Gastpermutationen mit drei Abbildern und einem unabhängigen Canary
beweisen gestagte Lebensdauer, nicht allgemeine parallele Ring3-Dienste.

R8.3m (11. September2026): Installation, Syscallabfrage, IRQ-Bindungsprüfung
und Widerruf verwenden denselben privaten SysV-AMD64-Profilkern.32-Byte-
Descriptor aus Task-/Profilpointer, Generation und expliziter Politikmaske;
die16-Byte-Profile und öffentliche ABI bleiben unverändert. Speicherbereiche
sind getrennt; alle Metadaten werden vor Effekten validiert. Keine Rollen,
PIDs oder impliziten Rechte im Mechanismus. Die Bootstrapadapter behalten
ihre ausdrücklich feste Politik und Kapazität. Aufrufnummern ab64 werden vor
Bitselektion verweigert, nicht auf niedrige Bits verkürzt. EACCES ist lokal;
beschädigte Bindung oder Maske bleibt fatal. Installation nur RESERVED,
Abfrage nur RUNNING, Widerruf terminal/reserviert vor Framefreigabe. Leerer
Widerruf ist nur bei unverändertem generationsgenauem Taskbesitz idempotent.
Der Gastnachweis verwendet unveränderte Rechte und Zeitlimits; er ist keine
Abnahme allgemeiner Prozesspools oder unabhängiger nativer Systemdienste.

R8.3l (11. September2026): SPAWN/SPAWNV besitzen eine begrenzte
Speichertransaktion vor der Identitätsvergabe. ELF-Staging und ein privater
120-Byte-Claim mit maximal13 Frames (4 Tabellen + Stack + bis zu8 private
Schreibseiten) werden vollständig reserviert, dann generationengebunden an
den Task übertragen. OOM führt nur nach bestätigter Rücknahme aller Seiten,
unveränderter Identität/Startquota und unveröffentlichtem Kind zu ENOMEM.
Kein Zurückdrehen einer Generation. Metadaten-/Freigabefehler bleiben fatal.
Der boolesche ELF-Ladevertrag bleibt bestehen; ein privater Last-error-Wert
gilt ausschließlich für den letzten serialisierten Ladeaufruf, nicht als
Bestandteil des88-Byte-Bildkontexts. Interne Calls verwenden System V AMD64,
Fehler REIST-v1; keine neue öffentliche ABI/POSIX-Kompatibilitätsbehauptung.
Die Gastprüfung injiziert Allocator-Nullrückgaben vor Effekten an sechs
aktuellen Kindallokationen. Sie beweist Rollback/Retry in zwei Generationen,
nicht skalierbaren Speicher, Mehrkernbetrieb oder allgemeine ELF-Programme.
128MiB/1CPU/vier Slots/zwei Kinder und frühere Abnahmegrenzen bleiben erhalten.

Ergänzung 11. September 2026: Die native64-Bit-Fertigstellung hat Vorrang.
R8.3a hat die native Test-Shell auf den gemeinsamen C/C++-Syscalltransport
umgestellt; Registerbreite, Nummern und echte IPC-/Reap-Abfolge sind geprüft.
Der bisherige Bootstrapumfang bleibt unverändert begrenzt. Abnahmestand und
weitere zusammenhängende Etappen im
[Fertigstellungsplan](../development/X86_64_COMPLETION_WORK_PAPER.md).

R8.3b ergänzt eager FXSAVE64/FXRSTOR64 mit privaten, bei Aufbau und Reap
bereinigten Zuständen und CPU-Admission. Alle bestehenden Modi/Marker bleiben
geprüft; die ursprünglichen FP-Sonden selbst verändern den User-RSP nicht.
R8.3f ergänzt unten ausdrücklich Timerproben mit belegtem Stack. Weiterhin nur
eingebettete Testprogramme: keine allgemeine FP-Ausnahme-/Anwendungsfreigabe,
kein AVX/XSAVE oder SMP. Abnahmebelege in
[CURRENT_WORK](../development/CURRENT_WORK.md).

R8.3c ergänzt CPL3-Ausnahme-Retirement für die vorhandene exklusive Shell-/
Kindbeziehung: Vektoren0/1/3/4/5/6/13/14/16/17/19 werden klassifiziert,
Kernelherkunft und andere Vektoren nicht als Kindfehler behandelt. Die
öffentlichen Strukturen und Syscallnummern bleiben unverändert; WAIT liefert
den REIST-Raw-Status128+Vektor, kein POSIX-Waitstatus. Private48-Byte-
Terminalquittung nach vollständigem Reap, generationgebundener einmaliger
Verbrauch; kein RIP/RSP-Zugriff über den gespeicherten Userpointer. Die
exklusive Paar-IPC wird geschlossen und ihre Deadline entfernt, wartender
Receive bekommt EPIPE. CLOSE desselben Handles ist bis zum WAIT idempotent;
andere IPC-Anfragen während dieser Terminalphase erhalten EPIPE ohne Wirkung.
Das bestehende CPL3-Breakpoint-Gate wird für den Shell-Lifecycle geleast und
bei Cleanup zurückgesetzt; andere IDT-Gates bleiben unverändert.

Abnahme: DE/BP/UD/GP/PF/MF in vier Lifecyclephasen, jeweils zwei Generationen,
echte Instruktionsadressen, Queue-/Elternzustand und weiterlaufende Shell.
Die Buildparameter `-FaultVector`/`-FaultPhase` ändern nur Test-ELFs und deren
Erwartungen, niemals den Kernelklassifikator. #XM/#AC nur Hostklassifikation,
kein Zielhardwarebeleg. Das ist keine allgemeine Prozess- oder FP-Anwendungs-
freigabe und keine vollständige64-Bit-Systemversion.

R8.3d trennt FIFO und sortierte Deadlineaufnahme/-entfernung in einen privaten
rollenunabhängigen Assemblykern. Derselbe Code läuft im Hostnachweis O0/O2
und in sämtlichen bestehenden nativen Queueverbrauchern. Kernel-eigene,
getrennte Arrays und ein32-Byte-Descriptor, unter IF=0 auf einer CPU
serialisiert; kein öffentlicher Syscall und keine neue Prozessautorität.
Die gesamte Queueform/Mitgliedschaft wird vor Mutation begrenzt überprüft.
FIFO bleibt zyklisch, Deadlines sind nach Tick/Slot sortiert; Entfernung ist
generationsgenau, fehlend/fremd/korrupt liefert null ohne Änderung. Interne
Kapazität1..64, bestehendes Gastprofil weiterhin4; Generationen behalten ihre
explizite32-Bit-Packung, höhere Bits werden nicht abgeschnitten. Vergabe und
Überlaufsperre bleiben Aufgabe des Prozess-Lifecycles, nicht der Queue.
Taskzustand, Rechte und bisherige Probeabnahme bleiben im Bootstrapadapter;
die neuen Mechanismen sind noch keine allgemeine Scheduler-/Systemabnahme.

R8.3e ergänzt einen privaten24-Byte-Identitätspool über den vorhandenen
Taskrecords, ohne zweite Zustandstabelle. Shell und Kinder reservieren eine
monotone Generation32 vor Frameaufbau (RESERVED9) und werden erst nach
Profil-/Kontextprüfung READY. Retirement oder Aufbaurücknahme verlangt bereits
freigegebene Ressourcen; ein exakter Tombstone erlaubt idempotente Wiederholung
nur bei weiterhin freiem Slot. Kein Wrap, keine doppelten aktiven oder retired
Identitäten. Vollständige Prüfung begrenzt quadratisch bei maximal64 Slots,
Gast weiterhin4; IF=0/eine CPU, keine Allokation oder öffentliche ABI. Ein
neuer Pool ist ein neuer Namespace, kein Resetrecht für lebende Handles.
Host O0/O2, Normalgast und24 Fehlvarianten/48 Generationen abgenommen; keine
allgemeine Prozesszulassung, OOM-/Supervisor-Recovery oder Systemfreigabe.

R8.3f verwendet einen gemeinsamen privaten Contextkern für die tatsächlich
gesicherten Syscall-/Quantum-Kontexte. Ein48-Byte-Descriptor und eine normierte
176-Byte-Frameform liegen nur auf dem Kernelstack; Taskrecords bleiben die
einzige dauerhafte Autorität. Vor Capture: RUNNING, exakte Generation/CR3,
Frameart/Selektoren, kanonische untere48-Bit-RIP und zugelassener Stackbereich,
Flags. Keine Userpointerdereferenzierung, keine Änderung von Ressourcen oder
Taskidentität. IRQ bewahrt15 GPRs/RIP/RSP/RFLAGS, SYSCALL initialisiert RAX=0
und behält die architektonischen RCX/R11-Clobber. Handlerergebnisse bleiben
unverändert. IF ist für IRQ erforderlich; RF darf im IRQ-Frame gesetzt sein
und wird für IRETQ bewahrt, nicht als Syscallflag zugelassen. Referenz:
[Intel SDM: Event- und Resume-Flag-Verhalten](https://cdrdv2-public.intel.com/671294/252046-sdm-change-document.pdf).
Privilegierte und reservierte Bits bleiben gesperrt. Timerzulassung akzeptiert
jetzt gültige Stackpositionen statt nur den ursprünglichen Stacktop. Reale
Quantumproben prüfen Stack-Canaries und gespeicherte RSP unterhalb Stacktop;
die Timer-/Rollen-/Budgetgrenzen bleiben ansonsten unverändert. Das ist noch
keine allgemeine Präemption oder Hangbehandlung der nativen Shellprozesse.

R8.3g erweitert das zugelassene Shellprofil um IF=1 und einen persistenten
100-Hz-Scheduler-Timer. IPC benutzt absolute Deadlines und beendet nur den
eigenen Wait, nicht die gemeinsame Uhr. IRQ prüft Identität/Profil/Kontext
und verarbeitet begrenzte Wakeups; nach EOI übernimmt der Scheduler-Tail
FP/GPR und dispatcht die bestehende generationsgebundene FIFO. Die bisherige
TSC-Lease und maximal256 gelieferte Ticks begrenzen weiterhin den Bootstrap,
nicht ein freigegebenes dauerhaft interaktives System. Keine neue öffentliche
API oder Timer-/Prozessautorität für den Userspace.

Private32-Byte-Budgetrecords gehören zur Taskgeneration. Bind nur aus null,
Charge nur mit neuerem absoluten Tick;32 laufende Samples pro zugelassenem
Kind, kein Reset durch Yield oder IPC. Terminales Reap entfernt auch den
Budgetbesitz. Raw-Status256 bezeichnet hier CPU-Budgeterschöpfung,257 den
abgewiesenen User-Stackbereich bei validierter Kind-/Kernelidentität. Beides
sind explizite REIST-Profilwerte, keine POSIX-Signale oder fingierte Exception-
Vektoren. Stackablehnung dereferenziert/rekonstruiert den User-RSP nicht.
Die private Terminalquittung erhält ein zusätzliches8-Byte-Samplefeld, das
beim WAIT-Verbrauch gelöscht und am Ende auf null geprüft wird; öffentliche
WAIT-Struktur unverändert. Unbekannte Kernelzustände bleiben fail-closed.

Abnahme: unveränderter Normaldialog,24 alte echte Faultvarianten sowie
zwei syscallfreie Spin- und zwei RSP=0-Generationen mit unabhängiger ELF-/
Quittungsprüfung. Budgetkern zusätzlich O0/O2 am Host. Das ist keine allgemeine
Prozess-/Supervisor-/Kontextfehler-/SMP- oder vollständige64-Bit-Systemfreigabe;
gesampelte laufende Ticks sind keine exakte CPU-Zeit oder FTTI-Zusage.

## Zweck und Grenze

R8.3k trennt nichtterminale Aufrufablehnung von Kernelkorruption. READ/WRITE,
GETPID, SPAWN/SPAWNV und WAIT verwenden einen privaten80-Byte-Snapshot und
denselben reinen Admissionkern. Nulltransfer verändert weder Puffer, Gerät
noch Zähler; falsche Deskriptoren/Größen/Puffer liefern EBADF/EINVAL/EFAULT.
GETPID ignoriert Restregister. Der eingebettete Pfadadapter liefert ENOENT
bzw. ENAMETOOLONG; Kindbelegung und ausgeschöpftes Startprofil EAGAIN.
Endpoint-/Capability-/Queuevalidierung liegt vor der ersten Spawnallokation
und wird vor der Stackpublikation erneut geprüft. WAIT liefert ECHILD bei
fehlendem/fremdem Kind, EINVAL bei Optionen und EFAULT bei falschem Statusziel;
ein derzeit BLOCKEDes Kind erhält vor Waitpublikation im Bootstrapadapter
EAGAIN. Alle bestehenden generationgebundenen Reap-Nachweise bleiben erhalten.
Keine POSIX-READ/WRITE/WAIT-Kompatibilitätszusage: Lesen bleibt auf ein Byte,
Schreiben auf64 Bytes begrenzt; auch die festen Dialog-/Startquoten und der
Eltern-EXIT als Bootstrapabschluss bleiben explizite Migrationsgrenzen.
Die Kind-Fixture wartet nach frühem EACCES mit höchstens acht Sendversuchen
und kooperativem YIELD auf die ausdrückliche SEND-Delegation; keine impliziten
Rechte, unterdrückte Präemption oder größeren Kernelbudgets. Ein neuer
Gastfall erzwingt den Kindlauf vor dieser Delegation.

R8.3j ersetzt im SPAWNV-Pfad das feste Zweier-/Tokenlayout durch tatsächlichen
Argumenttransport. Ein privater56-Byte-Descriptor und ein reiner Assemblykern
validieren die stabile private Eltern-Stackseite vollständig vor Allokation
und Zielmutation. Zulässig sind0..8 Argumente, je1..128 Bytes inklusive NUL;
leere und aliasierte Strings bleiben unverändert. argc0 verlangt null argv.
Maximal1152 Startupbytes belegen dieselbe4-KiB-NX-Stackseite; kein neues Heap-,
Dateisystem-, envp- oder ELF-Laderecht. System-V AMD64 argc/argv, Null-envp,
auxv und16-Byte-RSP bleiben erhalten; der IPC-Auxwert stammt nur vom Kernel.
EFAULT/E2BIG sind lokale Nutzerfehler; fehlerhafte Kernelmetadaten bleiben
fatal. Das bisherige argc2-Layout bleibt bytegenau128 Bytes groß, der
Legacy-SPAWN-Adapter bleibt erhalten. Referenz und Abnahmebelege stehen im
[Fertigstellungsplan](../development/X86_64_COMPLETION_WORK_PAPER.md#r83j-tatsächliche-begrenzte-spawnv-argumente).

R8.3i entfernt IPC-Probephasen als Voraussetzung für argumentloses YIELD
und normalen Kindexit. Beide benutzen die vorhandenen generationsgeprüften
Queue-/Terminalpfade. Normaler Exit erhält einen separaten privaten Grund
und Zustand ZOMBIE; Fencing/FP-/Frame-/ELF-/Budgetfreigabe werden mit den
Fehlerfällen geteilt. Die öffentliche Raw-uint32-WAIT-Publikation bleibt nach
vollständigem Reap. Wide-EXIT liefert EINVAL vor Wirkung. Ein normaler
Exitstatus128/256/258 ist deshalb kein Fault-/Quotagrund; keine POSIX-
Waitkodierung oder Low8-Bit-Kompatibilität. Privates Grundfeld nach WAIT null
und beim Teardown geprüft. Alle24 normalen Exitvarianten/48 Generationen
und sämtliche alten Normal-/Fault-/Busy-/Contextgates bestehen; i386 und
native Ressourcen-/Zeitquoten unverändert. Allgemeine Eltern-/Supervisor-
und Prozesszulassung bleibt außerhalb dieses zugelassenen Kindprofils.

R8.3h schließt die zugelassene Userkontextgrenze zwischen SYSCALL und IRQ:
ungültiger SYSCALL-RSP wird nach exakter Kernelidentität/Profil lokal als
Raw257 gereapt; User-NT bei beiden Eintrittsarten als Raw258, niemals per
IRETQ wiederhergestellt. Auch eine nichtausführbare SYSCALL-Rückkehradresse
wird lokal abgewiesen. Kernel-/Elternkorruption bleibt fail-closed. Das sind
ausdrückliche REIST-Profilwerte und keine öffentlichen POSIX-Statusformate.
Der Contextkern bewahrt jetzt DF/AC/ID/TF, IRQ zusätzlich RF; privilegierte
und reservierte Bits bleiben unverändert gesperrt. Kernelstackwechsel, CLD,
FMASK und EOI-vor-Tail bleiben erhalten. O0/O2-Hostprüfung plus sieben reale
Kontextfälle/14 Generationen, alter Normaldialog,24 alte Faultvarianten und
beide Busy-/Stackvarianten bestanden. Testparameter ändern nur Userspace,
keine Kernelrechte. Allgemeine Syscall-/Prozess-/Supervisorportierung und
native Dienste bleiben offen; Ressourcen-/Zeitbudget unverändert.

R8.1a fuehrt ein getrenntes Architektur-Prototypartefakt ein. Es beginnt im
von Multiboot definierten 32-Bit-Protected-Mode, prueft die benoetigten
CPU-Faehigkeiten, aktiviert mit statischen Tabellen IA-32e Paging und springt
in einen 64-Bit-Codesegment. Erst dort darf der serielle Erfolgsmarker
`REIST_X86_64_LONG_MODE_BOOT_OK` erscheinen.

R8.1b ergaenzt danach eine begrenzte Exceptiongrundlage. Sie veroeffentlicht
genau die Vektoren 0 bis 31, normalisiert CPU- und synthetische Fehlercodes,
sichert alle allgemeinen Register und laedt eine 64-Bit-TSS. Nur Double Fault
verwendet deren festen IST1. Ein einzelner `UD2`-Probe darf ausschliesslich bei
Vektor 6, Fehlercode null und exakt passender RIP zur festen Fortsetzung
zurueckkehren.

R8.1c fuegt einen kanonischen Higher-Half-Alias ab
`0xFFFFFFFF80000000` hinzu. Die physische Adresse bleibt dabei als Offset
erhalten. Nur die gelinkten Text-, RoData-, Data- und BSS-Seiten werden mit
4-KiB-PTEs abgebildet. Nach dem Wechsel von RIP und RSP auf diesen Alias wird
die niedrige Uebergangsabbildung aus PML4[0] entfernt und CR3 neu geladen.
Ein Sprung auf ein festes Byte in der NX-Datenseite muss danach exakt einen
Supervisor-Instruction-Fetch-Page-Fault erzeugen.

R8.1d erfasst den Multiboot-v1-Handoff noch im ungepageten 32-Bit-Einstieg.
Die variable Speicherkarte wird zweimal innerhalb fester Grenzen ausgewertet:
zuerst werden vollstaendige nutzbare 4-KiB-Frames aufgenommen, danach
ueberstimmen alle nicht nutzbaren Eintraege jede Ueberlappung. Bootstrap,
ausgewertete Multiboot-Strukturen, Modultabelle und Modulnutzdaten werden vor
der Freigabe reserviert. Zwei feste Bitmaps trennen verwaltbare Frames von
laufenden Allokationen.

R8.1e baut ein eigenstaendiges freestanding x86_64-`ET_EXEC` mit NASM und dem
ELF64-Linker und bettet genau dieses Artefakt in den Bootstrap ein. Der
Gastloader validiert die ELF64-/System-V-Identitaet und hoechstens zwei
`PT_LOAD`-Segmente vollstaendig, bevor er Frames allokiert. Er staged Datei-
und BSS-Bytes in ein festes Acht-Seiten-Fenster, prueft Inhalt und W^X-
Metadaten und gibt danach alle Frames frei. Das Probeprogramm wird nicht
ausgefuehrt.

Das Artefakt ist kein vollstaendiger REIST-Kernel. Seine physische Verwaltung
endet bei 128 MiB und verwendet weder dynamische Seitentabellen noch NUMA oder
Highmem. Die spaeteren R8.1-/R8.2-Nachweise besitzen einen begrenzten
Prozess-, Syscall- und Ring-3-Shellpfad, aber keine produktive
Hardwareinterruptbehandlung, Treiber, VFS-Integration oder signiertes natives
64-Bit-Medienlayout. Die isolierten Nachweise begruenden deshalb keine
vollstaendige ELF64-Prozess-, Hardware- oder Fail-operational-Kompatibilitaet.

## Referenzstandard

Der Eintritt folgt Intel 64/IA-32 SDM: CPUID weist die erweiterte Funktion
`0x80000001`, NX-Bit EDX[20] und Long-Mode-Bit EDX[29] nach. CR4.PAE,
EFER.LME zusammen mit EFER.NXE sowie CR0.PG zusammen mit CR0.WP werden in
dieser Reihenfolge aktiviert. Nach dem Far-Transfer prueft der 64-Bit-Code die
Kontrollbits erneut. Die vierstufige Seitentabellenstruktur, kanonischen
Adressen und Page-Fault-Fehlerbits folgen Intel 64/IA-32 SDM. Der Ladevertrag
ist Multiboot Version 1; er bleibt auf das separate Bootstrap-Artefakt begrenzt.

## Feste Ressourcen

- eine statische, page-aligned PML4, PDPT, niedrige und hohe Page Directory
  sowie eine hohe Page Table;
- genau eine temporaere 2-MiB-Identity-Map ab physischer Adresse null;
- feste 4-KiB-Higher-Half-Abbildungen nur fuer die gelinkten Abschnitte;
- Text read-only/executable, RoData read-only/NX und Data/BSS read-write/NX;
- maximal 4.096 Byte Multiboot-Speicherkarte mit 128 Eintraegen und 32 Modulen;
- zwei feste 4.096-Byte-Bitmaps fuer 32.768 Frames unter 128 MiB;
- eine feste RW/NX-Direct-Map mit 64 Page Tables und ausschliesslich
  verwaltbaren RAM-Frames;
- ein separat gelinktes ELF64-`ET_EXEC` mit maximal 64 KiB, vier Program
  Headern, zwei `PT_LOAD`-Segmenten und acht staged Userseiten;
- ein statischer 16-KiB-Bootstack innerhalb dieser Map;
- ein getrennter 16-KiB-C-Entry-Stack und ein exakt 128 Byte grosser
  versionierter Assembly-Handoff;
- genau 32 statische 16-Byte-IDT-Gates und eine gepackte 104-Byte-TSS;
- ein statischer 16-KiB-IST ausschliesslich fuer Double Fault;
- maximal 65.536 Statusabfragen je gesendetem COM1-Byte;
- genau eine vCPU, 128 MiB RAM und zehn Sekunden im automatisierten QEMU-Gate.

Nicht unterstuetzte CPU-Faehigkeiten und inkonsistente Kontrollregister enden
mit einem eigenen seriellen Fehlermarker und anschliessendem `hlt`. Der
produktive i386-Build verwendet keine Datei aus `arch/x86_64` und bleibt die
Standardauswahl aller bisherigen Build- und Installationswege.

## Abnahme R8.1a

Der Quellvertrag bestand sechs Tests. Der getrennte Windows-Build erzeugte ein
14.360 Byte grosses Bootstrap-ELF. Der begrenzte QEMU-x86_64-Lauf mit einer
vCPU und 32 MiB RAM veroeffentlichte nach den erneuten 64-Bit-Zustandspruefungen
`REIST_X86_64_LONG_MODE_BOOT_OK` in 1,8 Sekunden. Dieser Nachweis gilt nur fuer
den Emulator und den beschriebenen Architekturuebergang.

## Abnahme R8.1b

Der erweiterte Quellvertrag bestand neun Tests. Der warnungsfreie Windows-Build
linkte getrennte Entry- und Exceptionobjekte zu einem 16.844 Byte grossen ELF.
Der weiterhin auf eine vCPU, 32 MiB und zehn Sekunden begrenzte QEMU-Lauf
meldete in dieser Reihenfolge `REIST_X86_64_LONG_MODE_BOOT_OK`,
`REIST_X86_64_EXCEPTION_IDT_READY`, `REIST_X86_64_EXCEPTION_UD_OK` und
`REIST_X86_64_EXCEPTION_RECOVERY_OK`. Erweiterte Seitentabellen, Hardware-IRQs,
Prozesse, Syscalls, ELF64-Userspace und physische Hardware bleiben offen.

## Abnahme R8.1c

Der Quellvertrag prueft den festen Tabellenumfang, seitengetrennte
Linkergrenzen, W^X/NX/WP, den Higher-Half-Stack, den Low-Map-Widerruf und die
exakte NX-Fehlerbehandlung. Die Laufzeit-Selbstpruefung vergleicht physische
Adresse und Schutzbits exakt und ignoriert dabei ausschliesslich die von der
CPU gepflegten Accessed-/Dirty-Bits. Der QEMU-Lauf muss geordnet zusaetzlich
`REIST_X86_64_HIGHER_HALF_PAGING_OK` und `REIST_X86_64_PAGING_NX_OK`
veroeffentlichen. Erst danach darf der bestehende
`REIST_X86_64_EXCEPTION_RECOVERY_OK`-Abschlussmarker erscheinen. Der Nachweis
bleibt auf eine vCPU, 32 MiB und zehn Sekunden begrenzt.

Der finale Quellvertrag bestand elf Tests. Der warnungsfreie Windows-Build
erzeugte ein 26.180 Byte grosses ELF. Nach einer gezielten Korrektur der
PTE-Selbstpruefung, die nun ausschliesslich CPU-eigene Accessed-/Dirty-Bits
maskiert, veroeffentlichte der QEMU-Lauf alle sechs geforderten Marker in
exakter Reihenfolge innerhalb einer Sekunde. Damit sind Higher-Half-Wechsel,
Low-Map-Widerruf, bestehender UD2-Resume und die exakte NX-Schutzwirkung fuer
dieses isolierte Artefakt nachgewiesen.

## Abnahme R8.1d

Der Quellvertrag fordert exakte Multiboot-Magic-, Pointer-, Laengen-,
Entrygroessen-, Kapazitaets- und 64-Bit-Ueberlaufpruefungen vor jeder
Publikation. Reservierte Bereiche muessen jede nutzbare Ueberlappung
ueberstimmen. Der QEMU-Lauf muss nach dem bestehenden NX-Probe drei eindeutige
Frames allozieren, deren RW/NX-Direct-Map beschreiben, einen Frame freigeben
und exakt wiederverwenden, danach alle Frames freigeben sowie unaligned und
doppeltes Free ablehnen. Erst nach wiederhergestelltem Freizaehler darf
`REIST_X86_64_PHYSICAL_MEMORY_OK` vor dem Abschlussmarker erscheinen.

Der finale Quellvertrag bestand vierzehn Tests. Der warnungsfreie Windows-
Build linkte Entry-, Exception- und Physikalspeicherobjekt zu einem 29.788 Byte
grossen ELF. Der Ein-vCPU-/32-MiB-QEMU-Lauf verarbeitete die reale
Multiboot-v1-Speicherkarte und bestand Allokation, Direct-Map-Schreibprobe,
Free/Reuse, unaligned Free, Double Free und Freizaehlerwiederherstellung.
`REIST_X86_64_PHYSICAL_MEMORY_OK` erschien innerhalb einer Sekunde in der
geforderten Reihenfolge. Der Nachweis gilt nicht fuer Speicher oberhalb
64 MiB oder physische Hardware.

## Abnahme R8.1e

Der Quellvertrag verlangt einen unabhaengigen ELF64-Toolchainlauf und eine
vollstaendige Vorabvalidierung von Identitaet, Maschine, Typ, Headergroessen,
Programmtabelle, allen 64-Bit-Bereichen, Alignment, Entry-Point und W^X. Erst
danach duerfen hoechstens acht R8.1d-Frames belegt werden. Der Gast muss alle
Dateibytes sowie die genullten Speicherenden nachpruefen und vor
`REIST_X86_64_ELF64_LOAD_OK` jeden Frame sowie den urspruenglichen
Freizaehler wiederherstellen. Ring-3-Transfer, User-Seitentabellen, Syscalls
und Payload-Ausfuehrung sind ausdruecklich R8.1f vorbehalten.

Alle 17 Quellvertragstests bestanden. Nach einer gezielten Korrektur eines
mehrdeutigen NASM-Labels erzeugte der warnungsfreie Windows-Build ein
45.156-Byte-Bootstrap und ein unabhaengig gelinktes 9.008-Byte-ELF64-`ET_EXEC`.
Der auf eine vCPU, 32 MiB und zehn Sekunden begrenzte QEMU-Lauf meldete
`REIST_X86_64_ELF64_LOAD_OK` innerhalb einer Sekunde geordnet zwischen
`REIST_X86_64_PHYSICAL_MEMORY_OK` und
`REIST_X86_64_EXCEPTION_RECOVERY_OK`. Der Nachweis gilt nicht fuer
Payload-Ausfuehrung, Ring 3, physische Hardware oder HPASA.

## Abnahme R8.1f

Der erste User-Ausfuehrungspfad bleibt auf dasselbe eingebettete ELF64-Abbild,
hoechstens acht Abbildseiten und eine feste separate NX-Stackseite begrenzt.
Eine private Vier-Ebenen-Hierarchie uebernimmt nur die bestehenden Supervisor-
Eintraege fuer Higher-Half-Kernel und Direct Map; User-PTEs werden
ausschliesslich aus den validierten ELF-Rechten abgeleitet. DPL3-Code und
-Daten, TSS-RSP0, Entry, Stack und feste RFLAGS muessen vor `IRETQ` geprueft
sein.

Alle 21 Quellvertragstests bestanden. Der warnungsfreie Windows-Build erzeugte
ein 50.980-Byte-Bootstrap und ein unabhaengig gelinktes 9.048-Byte-ELF64-
`ET_EXEC`. Der auf eine vCPU, 32 MiB und zehn Sekunden begrenzte QEMU-Lauf
beruehrte die User-Stackseite, nahm exakt `EXIT` 9 mit Status 100 an, enthielt
anschliessend den erwarteten CPL3-`UD2` und meldete
`REIST_X86_64_USER_EXECUTION_OK` innerhalb einer Sekunde zwischen
`REIST_X86_64_ELF64_LOAD_OK` und `REIST_X86_64_EXCEPTION_RECOVERY_OK`.
Die wiederholte Tabellenpruefung maskiert ausschliesslich CPU-eigene
Accessed-/Dirty-Bits; der Faultpfad verlangt das architektonische Resume-Flag.
Scheduler, allgemeine Syscalls, produktiver 64-Bit-Userspace und physische
Hardware bleiben offen; HPASA bleibt ein getrenntes Projekt.

Der Syscall-Nachweis folgt Intel 64 `SYSCALL`/`SWAPGS` und der System-V-AMD64-
Registerkonvention. Nur der append-only REIST-v1-Index 9 (`EXIT`) mit dem
erwarteten Status ist zulaessig. Der Entry muss vor dem Lesen des Requests auf
den festen Kernelstack wechseln; `SYSRET` ist nicht zulaessig. Ein zweiter
Eintritt provoziert `UD2`; nur Vektor 6 mit Fehlercode null, CPL3-Selektoren und
einer RIP in einer validierten ausfuehrbaren ELF-Seite darf enthalten werden.
Vor `REIST_X86_64_USER_EXECUTION_OK` muessen Original-CR3 und Kernelzustand
wiederhergestellt, die temporaeren Syscall-MSRs deaktiviert, alle User-PTEs
geloescht, alle Frames freigegeben und der urspruengliche Freizaehler erreicht
sein.

## Abnahme R8.1g

Der Prozessnachweis bleibt auf zwei feste Slots und eine endliche kooperative
Abfolge begrenzt. Jede Generation besitzt eine private Vier-Ebenen-Hierarchie,
private writable ELF-Seiten und eine private NX-Stackseite. Ausschliesslich
validierte nichtschreibbare RX-Seiten duerfen physisch geteilt werden. Die
Probe muss ihre jeweils eigene Datenseite nach mehreren CR3-Wechseln
wiedererkennen.

Der AMD64-`SYSCALL`-Pfad akzeptiert nur die vorhandenen REIST-v1-Indizes
`YIELD` 40 und `EXIT` 9. `YIELD` speichert einen festen Userkontext und der
Chooser untersucht hoechstens zwei Slots. Ein exakt validierter CPL3-`UD2`
von Task B muss nur diese Generation isolieren und reapen; Task A muss danach
weiterlaufen und mit dem erwarteten Status beenden. Vor
`REIST_X86_64_PROCESS_SCHEDULER_OK` muessen Original-CR3, TSS und Syscall-MSRs
wiederhergestellt, alle Taskdaten genullt und alle Frames freigegeben sein.
Timerpreemption, Hardwareinterrupts, SMP und produktive Prozessintegration
bleiben ausserhalb dieser Scheibe.

Alle 26 Quellvertragstests bestanden. Der warnungsfreie Windows-Build erzeugte
ein 62.612-Byte-Bootstrap und ein 9.264-Byte-ELF64-`ET_EXEC`. Der auf eine
vCPU, 32 MiB und zehn Sekunden begrenzte QEMU-Lauf fuehrte die exakte Folge
`A:YIELD`, `B:YIELD`, `A:YIELD`, `B:UD2`, `A:EXIT(101)` aus. Task B wurde vor
der Fortsetzung von Task A generation-gebunden reaptiert. Erst nach der
vierzehnteiligen Lebenszykluspruefung, dem Widerruf aller temporaeren
Architekturzustande und vollstaendiger Framefreigabe erschien
`REIST_X86_64_PROCESS_SCHEDULER_OK` zwischen `USER_EXECUTION_OK` und
`EXCEPTION_RECOVERY_OK`.

## Abnahme R8.1h

Die feste IDT wird ausschliesslich um den standardmaessigen PIC-IRQ0-Vektor 32
erweitert. Beide PIC-Masken werden vor dem Remap auf 32/40 gesichert; nur
Master-IRQ0 darf waehrend des Nachweises unmaskiert sein. PIT-Kanal 0 verwendet
den standardisierten 1.193.182-Hz-Eingang und einen festen 100-Hz-Divisor.
Exakt drei normalisierte Kernel-Frames muessen Generation, CR3, Vektor,
Fehlercode, Selektoren und RIP-Bereich bestehen und je ein Master-EOI senden.

Der Warteloop besitzt eine feste TSC-Obergrenze und verwendet kein `HLT`. Vor
`REIST_X86_64_TIMER_IRQ_OK` muessen IF deaktiviert, IRQ0 wieder maskiert, beide
gesicherten PIC-Masken restauriert und die temporaere Generation inaktiv sein.
CPL3-Praeemption, LAPIC, IOAPIC und SMP bleiben offen.

Alle 27 Quellvertragstests bestanden. Der warnungsfreie Windows-Build erzeugte
ein 68.888-Byte-Bootstrap bei unveraendertem 9.264-Byte-ELF64-Probeabbild. Der
Ein-vCPU-/32-MiB-QEMU-Lauf nahm genau drei Vektor-32-Frames an und meldete
`REIST_X86_64_TIMER_IRQ_OK` geordnet zwischen `PROCESS_SCHEDULER_OK` und
`EXCEPTION_RECOVERY_OK`. Jeder Frame bestand Generation, CR3, Fehlercode,
Kernel-CS, IF und Higher-Half-Text-RIP; drei Ereignisse erzeugten drei
Master-EOIs. Danach waren IF, IRQ0, beide PIC-Masken und der temporaere Zustand
restauriert.

## Abnahme R8.1i

Task A gibt genau einmal ueber `YIELD` 40 an die CPU-gebundene Task B ab. Erst
dann wird PIT-IRQ0 fuer eine Generation armiert. Der normalisierte CPL3-Frame
muss B, deren privaten CR3, Userselektoren, IF, Stack und ausfuehrbare RIP
exakt validieren, IRQ0 maskieren, genau einen EOI senden und nur B reapen. Task
A muss danach ihre private Datenseite bestaetigen und ueber `EXIT` 9 mit Status
102 enden. Bs TSC-Limit verhindert einen unbegrenzten Userloop.

Alle 28 Quellvertragstests bestanden. Der warnungsfreie Windows-Build erzeugte
ein 70.964-Byte-Bootstrap und ein 9.400-Byte-ELF64-Probeabbild. Der auf eine
vCPU, 32 MiB und zehn Sekunden begrenzte QEMU-Lauf nahm genau einen validierten
CPL3-Vektor-32-Frame an, setzte nur B auf `PREEMPTED`, reapte diese Generation
und setzte A bis `EXIT` 9/Status 102 fort. Nach dem zehnteiligen Lebenszyklus
und der vollstaendigen Wiederherstellung erschien
`REIST_X86_64_TIMER_PREEMPTION_OK` zwischen `TIMER_IRQ_OK` und
`EXCEPTION_RECOVERY_OK`.

## Abnahme R8.1j

Eine feste vierteilige PIT-Generation schaltet zwei private CPU-gebundene
CPL3-Tasks exakt in der Folge A-B-A-B-A um. Jeder IRQ validiert Generation,
CR3, Userframe, IF, Stack und ausfuehrbare RIP vor Zustandsaenderung und EOI
und speichert danach alle allgemeinen Register sowie den IRET-Kontext. Beide
Tasks muessen aus dem unterbrochenen Kontext fortfahren und unabhaengigen
privaten Fortschritt erzeugen. Tick vier reapt nur B und signalisiert A den
begrenzten Abschluss; A bestaetigt ihre private Datenseite und liefert `EXIT`
9/Status 103. Ein globales TSC-Limit begrenzt den gesamten Nachweis.

Alle 29 Quellvertragstests bestanden. Der warnungsfreie Windows-Build erzeugte
ein 73.820-Byte-Bootstrap und ein 9.688-Byte-ELF64-Probeabbild. Der auf eine
vCPU, 32 MiB und zehn Sekunden begrenzte QEMU-Lauf nahm genau vier validierte
CPL3-Vektor-32-Frames und vier Master-EOIs an. Beide privaten Tasks setzten
ihren vollstaendigen unterbrochenen Kontext mit eigenem Fortschritt fort. Tick
vier reapte nur B; A lieferte danach `EXIT` 9/Status 103. Erst nach der
vollstaendigen Wiederherstellung erschien `REIST_X86_64_QUANTUM_SWITCH_OK`
zwischen `TIMER_PREEMPTION_OK` und `EXCEPTION_RECOVERY_OK`.

## Abgenommene FIFO-Lebenszyklen R8.1k

Vier feste private Prozessslots besitzen je eine nichtnull Generation. Eine
Vier-Eintrag-Ringqueue bindet jeden Eintrag an Slot und Generation und
validiert `READY`, Grenzen, Membership und Aktualitaet vor jeder Mutation. Die
exakte Laufreihenfolge 0-1-2-3-0-2 umfasst je ein `YIELD` von 0 und 2, direkte
Exits 110/111/112 und einen exakt validierten CPL3-`INT3` von Task 3. Ein
doppelter und ein staler Enqueue-Versuch muessen den Queuezustand unveraendert
lassen. Erfolg verlangt eine leere Queue, vier genullte freie Slots und den
urspruenglichen Framezaehler. Die Implementierung erfuellt diese Folge im
81.524-Byte-Bootstrap mit dem 9.936-Byte-Probeabbild. Vector 3 wird nur fuer
die Dauer des Nachweises fuer CPL3 freigegeben und danach auch auf Fehlerpfaden
auf seinen Ring-0-Gatezustand zurueckgesetzt. Der kurze Ein-vCPU-/32-MiB-Lauf
meldete `REIST_X86_64_RUNQUEUE_LIFECYCLE_OK` vor dem Abschlussmarker.

## Abgenommener Deadline-Sleep R8.1l

Die vorhandene Vier-Slot-FIFO besitzt zusaetzlich eine feste sortierte
Vier-Eintrag-Deadline-Liste. `SLEEP_MS` behaelt den REIST-v1-Index 41 und
Millisekunden als Einheit; die isolierte 100-Hz-Implementierung akzeptiert
hier exakt 10, 20 oder 30 ms und rechnet geprueft in ein, zwei oder drei
relative Ticks um. `MONOTONIC_MS` behaelt Index 42. Absolute Deadlines sind
64 Bit breit und auf einen festen Acht-Tick-Nachweishorizont begrenzt, damit
auch ein bereits anstehender PIT-Tick beim ersten CPL3-Eintritt sicher
beruecksichtigt wird.

Slot, Generation, `RUNNING`, Dauer, Ueberlauf, Membership und Kapazitaet
werden vor jeder Publikation validiert. Pro IRQ werden hoechstens vier
Deadline-Eintraege untersucht. Die vier privaten Tasks liefern Status 120 bis
123; nach dem Monotonic-Task werden die blockierten Tasks exakt in der Folge
1, 2, 0 geweckt. Erfolg verlangt die 27 festen Lebenszyklusereignisse, leere
und genullte Run- und Deadline-Queues, vier genullte Taskrecords sowie die
Wiederherstellung von Timer, PIC, CR3, TSS, Syscall-MSRs, Frames und
Freizaehler.

Alle 31 Quellvertragstests bestanden. Der Build erzeugte ein 89.188-Byte-
Bootstrap und ein 10.088-Byte-ELF64-Probeabbild. Der begrenzte Ein-vCPU-/
32-MiB-QEMU-Lauf meldete `REIST_X86_64_DEADLINE_SLEEP_OK` vor dem unveraenderten
Abschlussmarker. Dynamische Tasks, Prioritaeten, SMP und produktive
x86_64-Integration bleiben offen.

## Abgenommener Spawn-/Wait-Lebenszyklus R8.1n

Der dynamische Nachweis startet ausschliesslich Parent-Slot 0. `GETPID` 22
liefert dessen feste Test-PID 200. `SPAWN` 23 liest hoechstens 16 Bytes aus
einer privaten beschreibbaren ELF-Seite und akzeptiert nur den vollstaendig
terminierten Testpfad `/probe/child`. Erst danach werden die privaten Frames
fuer Slot 1 erzeugt und PID 201 mit Generation 31 beziehungsweise beim zweiten
Lebenszyklus Generation 32 veroeffentlicht.

`WAIT` 24 validiert die exakte Kindgeneration und einen ausgerichteten
privaten Vier-Byte-Statusausgang vor dem Zustandswechsel. Der Parent blockiert
ohne Polling, das Kind liefert Status 77, wird genau einmal reaptiert und erst
dann wird der Parent mit PID 201 und geschriebenem Status geweckt. Nullpfad,
doppelter Spawn, fremde PID, Null-Statuszeiger und ein bereits konsumiertes
stales Wait werden ohne Kind-, Queue- oder Ausgabemutation abgewiesen. Der
Parent beendet nach zwei Kindgenerationen mit Status 130.

Alle 32 Quellvertragstests bestanden. Der Build erzeugte ein 92.372-Byte-
Bootstrap und ein 10.264-Byte-ELF64-Probeabbild. Der begrenzte Ein-vCPU-/
32-MiB-QEMU-Lauf meldete `REIST_X86_64_SPAWN_WAIT_OK` vor dem unveraenderten
Abschlussmarker. Allgemeines VFS-Laden, `SPAWNV`, Argumentvererbung,
wait-any, Signale, Gruppen, SMP und produktive Integration bleiben offen.

## Abgenommener freestanding-C-Kern-Handoff R8.2a

Der fuer Multiboot v1 benoetigte aeussere Bootstrap bleibt ein ELF32-`ET_EXEC`.
Er bettet die Text-, RoData- und Data-Seiten eines separat vollstaendig
gelinkten ELF64-C-Payloads ein, das der normale x86_64-freestanding-C-Compiler
erzeugt. Die Produktionsziele fuer i386 bleiben davon getrennt. Assembly publiziert nach
allen bisherigen Markern genau den gepackten 128-Byte-Handoff Version 1 auf
einem eigenen 16-KiB-Stack nach SysV AMD64. C validiert die vollstaendige ABI
vor globaler Mutation, prueft initialisierte Data- und genullte BSS-Werte,
feste Arithmetik und eine auf 128 Byte begrenzte Kopie und ruft den ebenfalls
auf 64 Byte begrenzten seriellen Assembly-Adapter auf.

Der Abschluss ist fail-closed: C loescht sowohl den Handoff als auch alle
veraenderlichen C-Testwerte. Assembly prueft diese Bereiche erneut und meldet
erst danach `REIST_X86_64_C_CORE_HANDOFF_OK`. Der Build lehnt Red Zone,
Stackprotektor, Unwind- und Konstruktorabschnitte, Hosted-Runtime-Symbole,
undefinierte Endsymbole, verbleibende Relokationen sowie W+X-Abschnitte und
-Segmente ab. Der Nachweis fuehrt keine Geraete-, VFS-, DMA-, SMP- oder
produktive x86_64-Autoritaet ein und macht das Artefakt weiterhin nicht zu
einem vollstaendigen REIST-Kernel.

Alle 37 Quellvertragstests bestanden. Der Build erzeugte den 106.808-Byte-
Bootstrap, das 13.328-Byte-gelinkte ELF64-C-Payload, dessen 5.496-Byte-
Objekt und das unveraenderte 10.264-Byte-User-Probeabbild. Der begrenzte
Ein-vCPU-/32-MiB-QEMU-Lauf meldete nach allen R8.1-Markern geordnet
`REIST_X86_64_C_CALLBACK_OK` und `REIST_X86_64_C_CORE_HANDOFF_OK`.

## Abgenommener Ring-3-Shell-Schnitt R8.2b

R8.2b fuehrt ein getrennt gelinktes freestanding-C-ELF64 als einzigen
interaktiven Ring-3-Prozess aus. Nur die bestehenden REIST-v1-Indizes `READ`
15, `WRITE` 20, `YIELD` 40 und `EXIT` 9 werden fuer dessen feste serielle
Standardkanaele vermittelt. Reads blockieren nicht, Writes bleiben auf 64
Byte begrenzt und jeder nichtterminale Rueckweg verwendet einen validierten
`IRETQ`-Frame. Der automatisierte Dialog ist auf `INFO` und `EXIT` begrenzt;
allgemeines VFS-Laden und produktive Terminal- oder Geraeteautoritaet folgen
nicht aus diesem Nachweis. Die Abnahme umfasst 41 Quellvertragstests, einen
117.260-Byte-Bootstrap mit separat gelinkter 1.256-Byte-RX-Shell und den
begrenzten Ein-vCPU-/32-MiB-QEMU-Lauf. Der Gast meldet geordnet
`RING3_SHELL_READY`, `RING3_SHELL_INFO_OK`, die vollstaendige Bereinigung mit
`RING3_SHELL_EXIT_OK` und abschliessend `RING3_SHELL_OK`.

## Abgenommener Scheduler-Shell-Schnitt R8.2c

R8.2c ersetzt den Boot-Sonderaufruf der Shell durch einen vorhandenen,
fest kapazitierten Prozessslot. Das unveraenderte Shell-ELF wird als genau eine
nichtnullige Generation READY publiziert, in die Runqueue aufgenommen und ueber
den gemeinsamen Scheduler-Eintritt nach Ring 3 dispatcht. READ, WRITE und YIELD
kehren nicht direkt ueber einen separaten Shellpfad zurueck, sondern speichern
den Kontext, stellen den Slot erneut READY und durchlaufen generationengepruefte
Queue und `IRETQ`-Wiederherstellung. EXIT wechselt ueber EXITED zu FREE und
raeumt erst danach Loaderauswahl, Seitentabellen, Stack, TSS und Syscall-MSRs
auf. Der Schnitt fuehrt weder VFS noch allgemeine Terminal-, Geraete-, SMP-
oder produktive i386-Autoritaet ein. Die Abnahme umfasst 42 Quellvertragstests,
den isolierten Build und den begrenzten Ein-vCPU-/32-MiB-QEMU-Dialog. Nach dem
exakten Reap und der vollstaendigen Bereinigung meldet der Gast geordnet
`RING3_SHELL_EXIT_OK`, `SCHEDULED_SHELL_OK` und `RING3_SHELL_OK`.

## Abgenommener C-Kernel-Control-Schnitt R8.2d

R8.2d behaelt den 128-Byte-Bootstrap-Handoff unveraendert und fuegt einen
getrennten gepackten 64-Byte-Control-Handoff Version 1 hinzu. Nach dem
abgenommenen C-Core-Nachweis autorisiert er genau Shell-Service 1 als
Generation 1 mit den vorhandenen festen Kapazitaeten und Syscall-ABI Version 1.
Der C-Kern validiert Adresse und alle Felder vor dem ersten Effekt und erreicht
den Scheduler nur ueber einen festen Assembly-Adapter, der Kernel-CR3, IF und
eine exklusive Lease prueft und die SysV-ABI erhaelt. C loescht den Vertrag und
meldet Erfolg erst nach Rueckkehr des vollstaendig bereinigten Shell-
Lifecycles; Assembly prueft den autoritaetsfreien Zustand erneut vor dem
unveraenderten finalen Marker. Der Schnitt fuehrt keine allgemeine Spawn-, VFS-,
Terminal-, Geraete- oder SMP-Autoritaet ein. Die Abnahme umfasst 44
Quellvertragstests, den isolierten Build und den begrenzten Ein-vCPU-/32-MiB-
QEMU-Dialog. Der Gast meldet `C_CORE_HANDOFF_OK` vor der Scheduler-Shell,
danach `C_KERNEL_CONTROL_OK` und abschliessend den unveraenderten
`RING3_SHELL_OK`-Marker.

## Abgenommener physischer 128-MiB-Schnitt R8.2e

R8.2e erweitert ausschliesslich die feste physische Verwaltungsgrenze des
isolierten Artefakts. Zwei 4.096-Byte-Bitmaps verwalten hoechstens 32.768
4-KiB-Frames; 64 feste Page Tables bilden nur von Multiboot als nutzbar
gemeldete und nicht reservierte Frames RW/NX in der Direct-Map ab. Die
internen C-Seiten beginnen nun bei physisch `0x00184000`, damit die vergroesserte
Assembly-BSS disjunkt bleibt; das gesamte Bootstrap-Artefakt muss weiterhin
unter der bestehenden 2-MiB-Identity-Grenze enden. Ein separater, auf die
obere Bitmaphaelfte begrenzter Selbsttest allokiert genau einen Frame ab
64 MiB, prueft Zero-Fill und einen 64-Bit-Schreib-/Lesezugriff ueber die
Direct-Map, gibt ihn frei, verwirft ein doppeltes Free und stellt den exakten
Freizaehler wieder her. Erst danach erscheint
`REIST_X86_64_PHYSICAL_MEMORY_128M_OK`. Der bestehende 128-Byte-C-Handoff
behaelt Layout und Rechte; nur sein vorhandenes Speicherlimit betraegt nun
128 MiB. Dynamische Seitentabellen, Speicher oberhalb 128 MiB, NUMA, SMP und
produktive Hardwareintegration bleiben offen.

## Begrenzter High-Frame-Verbraucherschnitt R8.2f

Der normale lowest-first Allocator und die bestehenden ELF64-, Userstack- und
Prozess-Seitentabellenvertraege verwenden gemeinsam die bereits abgenommene
128-MiB-Grenze. Ein nur im Boot-Selbsttest aktiviertes festes Fenster erzwingt
Frames aus `[64 MiB, 128 MiB)` fuer den unveraenderten Loader- und ersten
Prozessaufbau. Es wird vor dem Ring-3-Eintritt geloescht; Erfolg verlangt die
normalen Zero-fill-, W^X-, NX-, Release- und Duplicate-free-Pruefungen sowie den
exakten urspruenglichen Freizaehler. Dynamische Seitentabellen und Speicher
oberhalb 128 MiB bleiben ausgeschlossen.

## Dynamische Scheduler-Seitentabellen R8.2g

Die vier generationengebundenen Scheduler-Slots behalten ihre feste
Kapazitaet, beziehen PML4, PDPT, PD und PT aber einzeln aus dem gemeinsamen
Frame-Allocator. Eine feste Vier-mal-vier-Metadatenmatrix besitzt diese Frames
bis zum Reap. `TASK_CR3` und READY duerfen erst nach vollstaendigem W^X-/NX-
Aufbau sichtbar werden. Teilaufbau, normaler Reap und Force-Cleanup stellen
zuerst Kernel-CR3 her, nullen und geben PT bis PML4 exakt einmal frei und
muessen den anfaenglichen Freizaehler sowie eine leere Matrix wiederherstellen.
Der fruehe Einzelprozessnachweis behaelt unabhaengige statische Tabellen.

## Dynamische fruehe Ausfuehrungstabellen R8.2h

Auch der verbleibende Einzelprozess-/Shell-Sondernachweis bezieht PML4, PDPT,
PD und PT aus dem gemeinsamen Frame-Allocator. Eine feste Vier-Eintrag-
Besitzliste ersetzt seine letzte statische 16-KiB-Tabellenarena. `user_cr3`
wird erst nach vollstaendigem Direct-Map-Aufbau und W^X-/NX-Nachweis
publiziert. Erfolg, CPL3-Fehler und jeder Teilfehler stellen zuerst Kernel-CR3
her und geben Stack, ELF- sowie Tabellenframes exakt einmal zurueck. Damit
bleiben im isolierten x86_64-Prozesspfad keine statischen User-Tabellenarenen.

Die Abnahme umfasst 48 Quellvertragstests, den warnungsfreien isolierten
125.944-Byte-Build und den begrenzten nativen Ein-vCPU-/128-MiB-QEMU-Lauf.
Nach leerer Besitzliste und wiederhergestelltem Freizaehler erschien
`EARLY_EXECUTION_TABLES_OK` geordnet vor allen Scheduler-, C-Control- und
Shell-Markern bis `RING3_SHELL_OK`.

## Reales Shell-Spawn/Wait R8.2i

Das exakte Shell-Kommando `RUN` verbindet den C-gesteuerten geplanten
Shellprozess mit `GETPID` 22, `SPAWN` 23 und `WAIT` 24. Nur PID 300 darf den
festen Stackpfad `/shell/child` verwenden. Kindslot 1/Generation 41 teilt
ausschliesslich das validierte RX-Shellabbild, erhaelt private dynamische
Tabellen und einen NX-Stack und startet mit einem festen Kindmodus in `RDI`.
Das Kind fuehrt kein I/O aus und beendet sich mit Status 77. WAIT blockiert
Generation 40 ohne Polling, publiziert den Status erst nach terminaler
Kindvalidierung und reapt alle Kindressourcen vor `RUN_OK`.

Die Abnahme umfasst 49 Quellvertragstests und ein 126.700-Byte-Bootstrap.
Der warnungsfreie isolierte Build erzeugte die 1.672-Byte-Shell. Der begrenzte
Ein-vCPU-/128-MiB-QEMU-Dialog fuehrte `INFO`, `RUN` und `EXIT` aus, erreichte
`RING3_SHELL_RUN_OK` und meldete nach vollstaendigem Kind-Reap alle bisherigen
Marker geordnet bis `RING3_SHELL_OK`.

## Generationensichere Shell-Kindwiederverwendung R8.2j

Der reale Shellpfad akzeptiert genau einen zweiten sequenziellen `RUN`-Zyklus.
Nach dem vollstaendigen Reap von Generation 41 muessen Slot 1, Stack- und
private ELF-Frames, alle vier Tabellenframes, Runqueue, Parentbeziehung und
WAIT-Metadaten null sein. Erst dann darf derselbe Slot mit frischen Ressourcen
als Generation 42 READY werden. PID 301 und Status 77 bleiben Teil der
unveraenderten REIST-v1-ABI; die Generation bleibt kernelintern.

50 Quellvertragstests und der warnungsfreie 126.868-Byte-Build bestanden. Der
begrenzte Ein-vCPU-/128-MiB-QEMU-Dialog sendete `INFO`, `RUN`, `RUN`, `EXIT`,
beobachtete exakt zwei geordnete `RING3_SHELL_RUN_OK`-Marker und erreichte nach
vollstaendigem Cleanup alle bisherigen Marker bis `RING3_SHELL_OK`.

## Separates Shell-Kind-ELF R8.2k

`/shell/child` waehlt nun ein unabhaengig assembliertes und gelinktes
System-V-AMD64-`ET_EXEC` mit genau einem RX-Segment. Das 360-Byte-Abbild fuehrt
keine Ein-/Ausgabe aus und beendet sich ausschliesslich ueber `EXIT` 9 mit
Status 77. Die Shell besitzt keinen Kindmodus mehr.

Der Loader verwaltet exakt drei feste 88-Byte-Kontexte fuer Probe, Shell und
Kind. Shell und Kind duerfen gleichzeitig aktiv sein, teilen aber weder
Frameeintraege noch Flags, Entry oder Cleanupzaehler. Nach jeder Generation
wird unter Kernel-CR3 zuerst der Task reaptiert, danach der Kindkontext
freigegeben und erst dann die Shell wieder ausgewaehlt. Gemeinsames Cleanup
laeuft Kind, Shell, Probe.

51 Quellvertragstests und der warnungsfreie 127.488-Byte-Build bestanden. Der
native Ein-vCPU-/128-MiB-QEMU-Dialog lud das Kind zweimal frisch, beobachtete
exakt zwei `RUN_OK`-Marker und erreichte nach leerem Kontext- und Framebesitz
alle bisherigen Marker bis `RING3_SHELL_OK`.

## Begrenztes SPAWNV und argv R8.2l

`RUN` verwendet nun den unveraenderten REIST-v1-Syscall `SPAWNV` 30. Im
privaten Shell-NX-Stack liegen exakt `/shell/child`, `token77` und ein
8-Byte-ausgerichteter Zwei-Pointer-Vector. Der Kernel akzeptiert nur Shell-PID
300/Generation 40, `argc == 2`, disjunkte 16-Byte-Bereiche und beide
NUL-terminierten Sollstrings, bevor Loader oder Taskzustand veraendert werden.

Nach ELF- und Adressraumvalidierung entsteht im privaten Kindstack ein
vollstaendig genullter 96-Byte-Startblock. `%rsp` ist 16-Byte-ausgerichtet und
zeigt auf `argc`; es folgen zwei `argv`-Pointer, NULL, eine leere Umgebung und
ein `AT_NULL`-Paar. Das RX-only-Kind prueft Stackadresse, Alignment, alle
Pointer, Terminatoren und Strings. Nur Erfolg beendet sich mit 77, jede
Abweichung mit 78.

52 Quellvertragstests und der nach einer fokussierten Immediate-Reparatur
warnungsfreie 128.328-Byte-Build bestanden. Der native QEMU-Dialog validierte
beide Generationen und erreichte mit exakt zwei `RUN_OK`-Markern alle
bisherigen Marker bis `RING3_SHELL_OK`.

## Generationsgebundene Syscallprofile R8.2m

Der unveraenderte 256-Byte-Taskrecord besitzt keine freie ABI-Flaeche. Deshalb
ordnet eine separate feste Vier-Slot-Tabelle jedem Taskslot genau eine
64-Bit-Generation und eine 64-Bit-Syscallmaske zu. Das Elternprofil fuer
Generation 40 enthaelt ausschliesslich `EXIT`, `READ`, `WRITE`, `GETPID`,
`SPAWN`, `WAIT`, `SPAWNV` und `YIELD`; die Kindprofile 41 und 42 enthalten nur
`EXIT`. Profilgeneration, exakte Rollenmaske und Indexgrenze werden vor dem
Shell-Dispatcher geprueft. Stale oder missgebildete Metadaten brechen
fail-closed ab, eine gueltige Ablehnung liefert `EACCES` ueber den normalen
gespeicherten Kontext und IRETQ-/Runqueue-Rueckweg.

Das RX-only-Kind ruft vor seiner bisherigen Stackpruefung einmal `GETPID` 22
mit Nullargumenten auf und akzeptiert ausschliesslich `-13`. Danach bleiben
96-Byte-System-V-Startstack und Exitstatus 77 unveraendert. Reap leert Maske
und Generation nur bei exaktem Match vor Task- und Abbildfreigabe; die finale
Pruefung verlangt alle vier Records null. 53 Quellvertragstests und der nach
einer fokussierten 64-Bit-Immediate-Reparatur warnungsfreie 129.680-Byte-Build
bestanden. Der native Ein-vCPU-/128-MiB-QEMU-Dialog durchlief beide
Kindgenerationen, meldete exakt zwei `RUN_OK`-Marker und erreichte alle
bisherigen Marker bis `RING3_SHELL_OK`.

## IPC-Admission und präemptierbare Übergabe R8.3j1

R8.3j1 ersetzt die unten historisch beschriebenen Token-/Sendphasen als
Kernelentscheidung durch Capability-, Queue- und Waiterzustand. Öffentliche
REIST-v1-Nummern und140-Byte-Nachrichten bleiben unverändert; Nutzlastlänge
0..128 wird ohne Tokeninterpretation transportiert. Privater96-Byte-Descriptor
prüft Generation, Handle, Rechte und volle Pointer-/Header-/Längenparameter;
ein tatsächlicher Assembly-Planer entscheidet Enqueue, Deliver, Consume,
Sender-/Receiverwait, Close oder Release. Fehlernummern nutzen die bestehenden
POSIX-benannten errno-Bedeutungen; keine POSIX-/Linux-IPC-Kompatibilitätszusage.

Leere Queue bei SEND_TIMEOUT ist kein Kernelzustandsfehler: sie nimmt die
Nachricht sofort an. Volle Queue liefert EAGAIN bei SEND oder bindet den
einzigen Sender-Snapshot an seine Deadline. Ein wartender Empfänger erhält
die Nachricht direkt; Dequeue kann einen wartenden Sender nachrücken lassen.
Generation, Capability, privater Ausgabeframe und exakter Deadlineeintrag sind
vor Publikation geprüft. Release/Close wirken vor oder nach dem Peer-Wait;
bereits freigegebene Ressourcen werden nicht erneut freigegeben.

Das Profil bleibt eine CPU,128MiB, ein Endpoint, eine140-Byte-Queue und ein
Sender- oder Empfängerwait mit10ms. Imagequellen und unmittelbare Imageausgaben
nutzen die vorhandene Mapping-/Rechtevalidierung; blockierende Receive-Ausgaben
benötigen weiterhin den privaten Stackframe. Nicht unterstützte Ausgabe-
geometrie liefert vor Waitpublikation EFAULT. Keine allgemeine Pin-/Scatter-
Abbildung und kein dynamischer Endpoint-Pool werden behauptet.

Der private Handle-Tombstone bleibt nach Close bis zum Namespaceende erhalten.
Nur das exakte letzte Handle erlaubt idempotentes Owner-Close. CREATE für
denselben verbrauchten Bootstrap-Epochenslot oder während des Kind-Lifecycle
liefert EAGAIN; kein geschlossenes Handle gewinnt erneut Rechte. Task- und
Endpointgenerationsbudgets werden nicht erweitert. Unbekannte Kernelownership
bleibt fail-closed; Nutzerparameter dürfen diesen Pfad nicht auslösen.

Vier reale, per GDB beobachtete Produktionspfade und acht Generationen,
Actual-Assembly O0/O2 mit Nichtmutations-/Negativoracles sowie alle früheren
Normal-/Exit-/Fault-/Busy-/Context- und i386-Gates bestehen. Benutzer-Fixtures
und ihre eingebetteten ELF-Bytes unterscheiden sich,13 eigenständige Kernel-
Mechanismusobjekte nicht. Vollständige Belege und verbleibende Grenzen:
[CURRENT_WORK](../development/CURRENT_WORK.md#r83j1-präemptierbare-ipc-übergabe-repariert).

## Expliziter IPC-Capability-Transfer R8.2n

Der reale `RUN`-Pfad verwendet die bestehenden REIST-v1-Indizes `IPC_CREATE`
49, `IPC_SEND` 50, `IPC_RECEIVE` 51, `IPC_CLOSE` 52, `IPC_DELEGATE` 55 und
`IPC_RELEASE` 58. Genau ein Endpoint, eine Nachricht mit festem 140-Byte-v1-
Layout und vier 24-Byte-Capabilityrecords sind statisch reserviert. Generation
40 besitzt `SEND | RECEIVE | CONTROL` und delegiert ausschliesslich `SEND` an
die bereits aufgebaute Generation 41 beziehungsweise 42. Das Kind erhaelt das
opaque Generation-plus-Slot-Handle ueber den REIST-privaten System-V-Auxv-Typ
`AT_REIST_IPC_HANDLE = 0x52534901`; der auf 128 Byte erweiterte Startstack
behaelt `argc = 2`, `argv`, leere Umgebung, `AT_NULL` und 16-Byte-Ausrichtung.

Nach `GETPID -> EACCES` prueft das Kind den Startstack, erhaelt fuer einen
strukturell gueltigen `IPC_RECEIVE` wegen des fehlenden Rechts erneut
`EACCES`, sendet die bytegenaue `token77`-Nachricht, gibt die Capability frei
und beendet sich mit 77. Der Parent wartet generationengenau, empfaengt und
validiert die Nachricht und schliesst den Endpoint vor `RUN_OK`. Reap,
Fehlercleanup und die finale Pruefung verlangen Endpoint, Nachricht sowie alle
vier Capabilityrecords null. 54 Quellvertragstests, der warnungsfreie
136.364-Byte-Build und der native Ein-vCPU-/128-MiB-QEMU-Dialog bestanden mit
exakt zwei `RUN_OK`-Markern bis `RING3_SHELL_OK`. Eine fokussierte Reparatur lud
den physischen Kind-Stackframe unmittelbar vor der Direct-Map-Initialisierung
neu und wird durch eine Regressionserwartung gesichert.

## Deadlinebegrenzter IPC-Receive R8.2o

Der reale `RUN`-Pfad verwendet nun zusaetzlich den bestehenden REIST-v1-Index
`IPC_RECEIVE_TIMEOUT` 54. Genau ein fester Waiterrecord bindet Generation 40,
Endpointhandle und den vorvalidierten privaten Outputframe an einen Eintrag der
vorhandenen Vier-Slot-Deadlinequeue. Der isolierte Nachweis akzeptiert exakt
10 ms, entsprechend einem Tick des bereits getesteten 100-Hz-PIT-Timers.

Unmittelbar nach `IPC_CREATE` blockiert ein leerer Receive ohne lauffaehigen
Peer, idlet mit `STI; HLT`, wacht nur durch die monotone Deadline und liefert
`ETIMEDOUT`, ohne Header oder Payload zu veraendern. Nach SPAWNV und der
abgeschwaechten SEND-Delegation blockiert der Parent erneut vor dem Kind. Der
Kind-SEND validiert Capability, Endpoint, Nachricht, Taskgeneration, Waiter,
privaten Direct-Map-Bereich und Deadline vor Queue-Publikation; vor Wake werden
dieselben Beziehungen erneut geprueft. Danach werden Deadline und Timer
widerrufen, `token77` wird in den privaten Parent-Frame kopiert und nur
Generation 40 wird READY. Erst nach der Receive-Pruefung folgt das bestehende
WAIT/Reap.

54 Quellvertragstests, der warnungsfreie 138.000-Byte-Build und der native
Ein-vCPU-/128-MiB-QEMU-Dialog bestanden mit zwei vollstaendigen Timeout-/Wake-
Zyklen, exakt zwei `RUN_OK`-Markern und `RING3_SHELL_OK`. Abschlusspruefung und
Fehlercleanup verlangen Timer-, Deadline-, Waiter-, Endpoint-, Nachrichten-,
Capability-, Task-, Loader- und Framezustand null. Mehrere Waiter,
blockierende Sender, tiefere Queues und produktive Integration bleiben
ausgeschlossen.

## Queue-Backpressure R8.2p

Das abgeschlossene Paket behaelt den einzelnen 140-Byte-Queue-Slot bei und prueft ihn
erstmals asynchron. Die normale Delegate-Rueckkehr und drei geplante
Parent-`YIELD`s lassen das Kind ueber die beiden erhaltenen Denial-Proofs bis
zur `token76`-Publikation und danach zum wiedereingereihten Full-Queue-Versuch
laufen, ohne dass ein Receive-Wait besteht. Der strukturell gueltige
`token77`-SEND muss `EAGAIN` liefern und darf
weder Queue noch Waiter, Deadline, Capability, Endpoint oder Usernachricht
veraendern. Das Kind gibt danach ebenfalls mit `YIELD` ab.

Generation 40 entnimmt und validiert `token76`, blockiert anschliessend mit dem
bestehenden 10-ms-Receive und wird erst vom generationengenauen `token77`-Retry
des Kindes geweckt. Ein fester Send-Phasenrecord verhindert Auslassung,
Doppelpublikation und stale Wiederverwendung. Blocking-Sender, Queue-Tiefe
groesser eins und mehrere Waiter bleiben explizit ausgeschlossen.

54 Quellvertragstests, der warnungsfreie 142.800-Byte-Build und der native
Ein-vCPU-/128-MiB-QEMU-Dialog bestanden mit exakt zwei `RUN_OK`-Markern bis
`RING3_SHELL_OK`. Release, WAIT, Reap, Close, Abschlusspruefung und
Fehlercleanup hinterliessen Sendphase, Timer, Deadline, Waiter, Endpoint,
Nachricht, Capabilities, Runqueue, Loader, Tasks und Frames null.

## Deadlinebegrenzter IPC-Send R8.2q

Das abgeschlossene Paket bindet den bestehenden REIST-v1-Index
`IPC_SEND_TIMEOUT` 53
an genau einen festen kernel-eigenen 140-Byte-Snapshot. Der Waiter traegt nur
Handle, exakte Sendergeneration und einen Eintrag der vorhandenen Vier-Slot-
Deadlinequeue; der blockierte Pfad behaelt keinen autoritativen Userpointer.

Vor dem Kind-Lifecycle belegt Generation 40 den Slot mit `token75` und muss
beim folgenden `token74`-Send ohne Peer echt bis `ETIMEDOUT` idlen. Im
Kindpfad blockiert dagegen `token77` nach dem erhaltenen Full-Queue-`EAGAIN`.
Das Parent-Dequeue von `token76` validiert Snapshot und Deadline vor Effekten,
entfernt die Deadline, stoppt den Timer, setzt `token77` in den freien Slot und
weckt nur den exakten Kind-Sender. Der bestehende direkte Receive-Wakeup bleibt
als anschliessender separater Nachweis erhalten.

Alle 54 Quellvertragstests, der warnungsfreie 145.572-Byte-Build und der native
Ein-vCPU-/128-MiB-QEMU-Dialog bestanden mit exakt zwei `RUN_OK`-Markern bis
`RING3_SHELL_OK`. Timeout, Dequeue-Wakeup, Release, WAIT, Reap, Close und
Abschlusscleanup hinterliessen Sendphase, Send-Waiter, Timer, Deadline,
Receive-Waiter, Endpoint, Nachricht, Capabilities, Runqueue, Loader, Tasks und
Frames null. Weitere Senderwaiter und tiefere Queues bleiben ausgeschlossen.

## Abgeschlossener IPC-Widerrufsnachweis R8.2r

Der naechste begrenzte Schnitt verwendet weiterhin genau einen Endpoint,
einen 140-Byte-Queue-Slot, je einen Receive- und Send-Waiter sowie die
vorhandene Vier-Slot-Deadlinequeue. Beide realen `RUN`-Generationen muessen
zuerst alle bisherigen Timeout-, Backpressure-, Retry- und Direct-Wakeup-
Nachweise unveraendert durchlaufen.

Danach blockiert Parentgeneration 40 erneut auf dem leeren Endpoint. Das
delegierte Kind gibt seine `SEND`-Capability frei; die Implementierung muss
Capability, Endpoint, Generation, Task, privaten Outputframe und exakte
Deadline vor jeder Wirkung validieren, Deadline und Timer entfernen und nur
den Parent mit `EPIPE` wecken. Nach der Resume-Pruefung wird dieselbe lebende
Kindgeneration erneut delegiert. `token78` belegt den Queue-Slot, waehrend
`token79` als kernel-eigener Send-Snapshot blockiert. Owner-`IPC_CLOSE`
widerruft nach vollstaendiger Validierung Queue, Snapshot, Deadline, Timer,
beide Capabilities und Endpoint und weckt nur dieses Kind mit `EBADF`.
Ein begrenzter, vollstaendig validierter Kind-`YIELD` nach erneuter Delegation
ordnet in der Round-Robin-Runqueue die Parent-Publikation von `token78` vor dem
Kind-Snapshot `token79`. 55 Quellvertragstests, der native Build und beide
realen QEMU-`RUN`-Generationen bestanden bis `RING3_SHELL_OK`. Startupstack,
opakes Handle, REIST-v1-ABI und alle Kapazitaeten bleiben gleich.
