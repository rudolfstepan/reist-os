# Native signierte Bootmedien – R8.3ab

Stand:12. September2026. Vor Umsetzung auf `aac73e4f` eingefroren.

## Gemeinsamer Schnitt

Festplatten- und Rettungsdiskettenvarianten werden gemeinsam gebaut und
abgenommen: bestehende FAT32-/FAT12-Erzeuger, Bootsektoren, Manifest3,
Research-Signierer und unabhängiger Signatur-/Manifestprüfer. Stage2 liefert
bereits GNU-Multiboot-v1/E820. Die native ELF32-Transporthülle besitzt echte
ELF64-Kern-/Userkomponenten; kein32-Bit-Userspace-Kompatibilitätsmodus.

`-NativeImages` beziehungsweise das entsprechende Makeziel wählt gemeinsam
NativeProcesses/NativeIPC/NativeRAM/NativeHeap. Beide Medien erhalten dieselbe
Kerneldatei und denselben ausdrücklich als Fixture gekennzeichneten ELF64-
Programmbaum. Eine separate native VM-Konfiguration verwendet1CPU/4GiB,
keine Hostfreigaben, Netzwerk-/Audio-/RFB-Geräte oder HID-Durchreichung.
Keine VM wird automatisch gestartet; VMware-Abnahme bleibt offen.

## Vertrauens- und Veröffentlichungsgrenze

RSA-2048-PSS/SHA256/MGF1 mit32Byte Salt und der vorhandenen gepinnten
Research-Policy bleiben unverändert. Der absichtlich öffentliche Testschlüssel
ist kein Release-Schlüssel. Stage1/Stage2 auf beschreibbarem Medium bilden
keinen physischen Vertrauensanker. Keine Secure-Boot-/Antirollback-Behauptung.

Manifest3, A/B-Bereiche und Boot-Control-Records werden nicht erweitert.
Der Erzeuger und ein unabhängiger Paketprüfer validieren tatsächliche
Kernel-/Signaturbytes beider Slots und Medien sowie die deklarierte
ELF64-Dateibelegung. Ein begrenzter versionierter Hostindex beschreibt
Architektur, Profil, Dateinamen und Hashes; er ist kein neuer Bootdatenträger-
oder Laufzeit-ABI-Vertrag. Traversal, Escapes, Trunkierung und Architektur-
Substitution sind vor Veröffentlichung abzuweisen.

Jeder Bau verwendet ein frisches begrenztes Ausgabeverzeichnis. Alte Versuche
bleiben erhalten. Erst nach kompletter Prüfung wird der Hostindex atomar
ersetzt. HDD512MiB, Floppy1,44MiB und bestehende Kernel-/Stage2-Kapazitäten
bleiben erhalten; Imagehashes werden gestreamt. Keine Raw-Devices oder
vorhandenen Nutzer-/Referenzmedien beschreiben.

## Abnahme und verbleibende Grenzen

Die13 unveränderlichen Gruppen stehen in der Queue. Neun BIOS-Gastfälle:
HDD normal4/8GiB; defekte A-Signatur mit gültigem B; beide Signaturen defekt;
beide Kernel CRC-gültig/SHA-defekt; beide Manifeste ungültig; Floppy normal,
Signaturfehler und CRC-gültiger SHA-Fehler. Positive Fälle müssen die ganze
native Prozess-/Heapfixture nach echtem BIOS-Start erreichen. Negative Fälle
beweisen genaue Ablehnung/Fallback ohne Kernelausführung. Snapshot-Overlays
verhindern Referenzschreibzugriffe. Neue BIOS-Frist20s inklusive Firmware,
Disk und Kryptografie; bestehender Heapnachweis10s und Kernel32 CPU-Samples/
256Ticks unverändert. Alle VMs verborgen, begrenzt und vollständig beendet.

Das Paket ersetzt weder Storage-/VFS-Dienste, Boot-Erfolgsbestätigung durch
einen solchen Dienst noch allgemeines ELF64-Laden in Ring3. Die mitkopierten
Dateisystemprogramme werden nicht dadurch vertrauenswürdige ausführbare
Objekte. Diese Autoritätsgrenzen folgen separat als größtmögliche kohärente
Systempfade; signierte Images allein sind kein fertiges64-Bit-Betriebssystem.

## Implementierung auf Vertrag3a279429

Windows und Make verwenden denselben Paketbau. Der bestehende Bootkernel
bleibt bytegleich. Der begrenzte Index ist eine JSON-Hülle mit Paketdaten und
256-Byte-RSA-PSS-Signatur in Hex. Kanonisches `package.json` und dessen Signatur
liegen im frischen Versuch; der Verbraucher verlangt exakte Übereinstimmung,
Policy-verifizierte Signatur und die feste14-Dateien-Belegung, bevor er Images
oder Konfigurationen akzeptiert. Zusätzlich bleibt die ursprüngliche
Kernel-Signatur in jedem Bootmanifest verpflichtend. Dieser signierte
Hostindex ergänzt keine Laufzeit-Boot-Control-Autorität.

Dateihashes lesen höchstens die deklarierte Kapazität plus ein Prüfbyte;
Wachstum oder Trunkierung während der Prüfung wird abgewiesen. Native Eingaben,
Index, Versuch und Artefakte dürfen nicht über Symlinks/Junctions entkommen.
Der unabhängige FAT-Leser prüft beide FAT-Kopien, maximal2048 Cluster, Zyklen,
genaue Pfadauflösung und vollständige ELF64-Dateibytes. Die festen Programme
liegen auf beiden Medien als `bin/shell.prg`, `usr/bin/probe.prg` und
`usr/bin/child.prg`; es sind weiterhin Bootstrapfixtures, keine normale
Dateisystem-Shell. Gestrippte User-ELFs benötigen keine private C-Symboltabelle.

Veröffentlichung erfolgt durch einen atomaren Austausch von `native-media.json`
nach erfolgreichem separatem Prüferprozess. Faultinjektion unmittelbar davor
beweist den Erhalt des vorherigen Index und Pakets. Die VMX/VMDK-Prüfung lässt
nur den exakten lokalen Native-Aufbau zu; zusätzliche Geräte/Freigaben und
externe Extents werden auch in ansonsten gültig signierten Paketen abgewiesen.
