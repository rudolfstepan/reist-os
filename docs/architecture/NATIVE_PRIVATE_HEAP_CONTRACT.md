# Native private Heapbereiche – R8.3aa

Stand:12. September2026. Vor Umsetzung auf `d8b7e52f` eingefroren.

## Referenz und Besitz

Der [bestehende Prozessspeichervertrag](PRIVATE_PROCESS_MEMORY_CONTRACT.md)
beschreibt ISO-C11-Lebensdauer und REIST-Seitenregionen. Native Syscalls4/5/6
übernehmen dessen Nullgrößen-, Fehler- und Realloc-Erhaltungssemantik mit
vollbreiten Argumenten. Keine neue Syscallnummer oder POSIX-mmap-Behauptung.
Die libc-Unterteilung in Objekte bleibt Ring3 und folgt als SDK-Portierung.

Optionales NativeHeap setzt NativeRAM und NativeProcesses voraus. Vier
generationstreue Tasks erhalten jeweils höchstens128 Regionen und512MiB
private Kapazität ab virtueller Adresse0x100000000. Kapazität wird nach Bedarf
physisch belegt. Alle Userblätter sind4KiB/RW/NX; Fenstergrenzen bleiben
unmapped. Datenframes bewahren1/16 der verwalteten Frames für Kernel/Recovery.
Bestehender physischer Pool und Zähler bleiben autoritativ.

## Fortschritt und Fehler

Die i386-Implementierung arbeitet mit Schedulerübergaben aus C-Aufrufen.
Der native Kern unterstützt diese schlafenden C-Stacks nicht. Ein Auftrag
speichert daher Operation, kopierte Argumente, Phase und Cursor im Kernel;
höchstens64 Seitenarbeitsschritte pro Dispatch. Zwischen Schritten muss ein
unabhängiger bereiter Task laufen können. Kein Frame darf währenddessen nur
auf dem C-Stack gehalten werden. Pro Task besteht höchstens ein Heapauftrag;
er überlappt keine IPC-Warteoperation und belegt keinen zweiten Wait-Knoten.

Fehlgeschlagene Allokation rollt sämtliche neuen Daten-, Schutz- und
Tabellenframes zurück. Fehlgeschlagenes Realloc erhält die alten Bytes.
Free verlangt die exakte Basis; Null, ungültige Größen, Überläufe, Quoten,
falsche Generationen und unbenutzte Argumente folgen den bestehenden Regeln.
Exit, Fault und CPU-Ende widerrufen zunächst IPC, bearbeiten dann Heap-Reap
in begrenzten Schritten und geben danach die bisherigen Image-/Stack-/Root-
Frames frei. Die Taskgeneration bleibt bis zur vollständigen Bereinigung
gebunden; normale Fehler dürfen unabhängige Prozesse nicht stoppen.

## Geschützte Metadaten und Aufbau

Der gemeinsame `critical_object` schützt Kontrollzustand, Regionsdatensätze
und Tabellenbesitz. Dynamische Schutzseiten müssen vor jeder Übergabe im
Tabellenauftrag registriert sein. Erwartete Leafchunks sind geschützt;
hardwaregesetzte A/D-Bits werden beim Abgleich ausdrücklich berücksichtigt.
Unkorrigierbare Metadaten führen vor Effekten in die bestehende Fatalgrenze.
Es wird keine neue Integritätsarithmetik oder DIMM-Isolation eingeführt.

Optionaler privater C-Aufbau4 darf nur exakt benannten Heapzustand ergänzen.
Die bisherigen5MiB C-/8MiB Gesamtareal- und16MiB Higher-Half-Grenzen bleiben.
Aufbau2/3 und frühere Belege bleiben erhalten. Öffentliche ABIs, i386-Code,
Treiber, Shared-Memory- und SMP-Autorität gehören nicht zu diesem Paket.

## Abnahme

Die14 unveränderlichen Gruppen stehen in der Queue. Hosttests führen echte
O0/O2-Operationen mit Fehlern an Erwerbsgrenzen, OOM-Rollback, Realloc-Erhalt,
hohen Adressen, Generationen und Metadatenkorruption aus.4/8GiB-Gäste müssen
Heapbytes tatsächlich benutzen, IPC-Puffer aus dem Heap zulassen, Fortschritt
unabhängiger Tasks und exaktes Retirement bei Free/Exit/Fault/CPU-Ende sowie
Folgegenerationen beweisen. Höchstens256MiB werden insgesamt berührt.
Bestehende Zeitlimits und Referenzorakel werden nicht gelockert.
