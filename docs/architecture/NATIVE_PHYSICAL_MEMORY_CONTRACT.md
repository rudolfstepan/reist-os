# Native physische Speicherverwaltung – R8.3z

Stand:12. September2026, vor Umsetzung auf `3e80a1c7` eingefroren.
Dies ist der physische Besitzschnitt, nicht die Freigabe großer virtueller Heaps.

Freigegebene Ergänzung am12. September2026: `proc/process_run.inc` gehört
zum selben physischen Besitzschnitt. Seine Gesamtprozessprüfung verwendet
noch die alte128MiB-Grenze und weist dadurch gültige hohe Frames ab. Der Nutzer
hat die gezielte Aufnahme nach dem Gastbefund ausdrücklich bestätigt.
Alle14 Gates und Lebenszyklus-/Rechtebedingungen bleiben unverändert.

## Standards und Umfang

[GNU Multiboot0.6.96](https://www.gnu.org/software/grub/manual/multiboot/html_node/Boot-information-format.html)
liefert64-Bit-Basis/Länge in der RAM-Karte; die Übergabezeiger bleiben32-Bit.
Typ1 ist verwendbarer RAM, überlappende Reservierungen gewinnen. Ganze freie
4KiB-Frames werden nach innen, reservierte Bereiche nach außen gerundet;
Überlauf, unvollständige Records und zu viele Einträge scheitern geschlossen.
Die bestehende Zweipassverarbeitung und4096Byte/128Einträge/32Module bleiben.

[Intel64 SDM, Vol.3A](https://cdrdv2-public.intel.com/874249/253668-090-sdm-vol-3a.pdf)
bestimmt P/U/W/NX, physische Adressbreite und2MiB-PDEs. NativeRAM prüft die
CPUID-Breite und begrenzt physische Adressen auf16GiB. Das deckt die gemeinsam
geprüften1/4/8GiB-Gäste einschließlich PCI-Löchern ab; es ist keine Behauptung,
dass16GiB eingebaut oder jeder Bereich verwendbar sei. Der alte128MiB-Default
bleibt als separat geprüfter Rückfallpfad bestehen.

## RAM-Autorität, Integrität und Aufwand

Nur firmwarezugelassene, nicht reservierte Frames dürfen allokiert werden.
Kernel, Bootdaten, Module und der neue Metadatenbereich sind ausgeschlossen.
Die Supervisor-Direct-Map ist RW/NX: volle nutzbare2MiB-Bereiche dürfen große
Blätter verwenden; gemischte Bereiche benötigen4KiB-Blätter. Höchstens512
solche Tabellen; Kapazitätsmangel ist ein Bootfehler, keine Freigabe von Löchern.
Seitengrößen werden nach Veröffentlichung nicht umgeschaltet.

Ein fester Metadatenbereich hält verwendbare/belegte Frames und geschützte
Verfügbarkeitszusammenfassungen. Der vorhandene `critical_object`-Kern schützt
die Kontroll-/Bitmapabschnitte; keine neue Integritätsarithmetik. Hierarchische
Wortauswahl ersetzt die RAM-weite Bitsuche je Allocation. Die betroffenen
geschützten Abschnitte werden vor einer Mutation geprüft. IF0/SingleCPU
serialisiert ohne Spinretry. Fehlende Frames ergeben normalen Mangel; falsche
Freigaben verändern nichts. Unkorrigierbarer vertrauenswürdiger Zustand führt
in die bestehende Fatalgrenze. Keine behauptete DIMM-/SMP-Ausfalltoleranz.

Allocation, Nullung, Freigabe und Zähler besitzen genau eine autoritative
Verwaltung. Die alten Assembleraufrufe werden gebunden, nicht durch einen
parallel konkurrierenden Pool ergänzt. Vollbreite gilt auch für ELF-Abbilder,
private Tabellen, CR3, Pointerprüfung, Rollback und Reap. Keine neuen Syscalls,
Prozessrechte, VFS-/Treiberpolitik oder privaten virtuellen Heaps.

## Privater Speicheraufbau und Abnahme

Nur NativeRAM ergänzt privaten C-Aufbau3: NOBITS/RW/NX ab physisch2MiB,
C-Metadaten höchstens5MiB, gesamtes zusätzliches Areal mit Direct-Map-Tabellen
höchstens8MiB. Die Higher-Half-Abbildung bleibt seitenweise begrenzt auf
höchstens16MiB; C-Brücke, Text, Daten und Handoff behalten ihre festen Adressen.
Aufbau2 und seine strengen Defaultprüfungen bleiben erhalten. Kein neues
öffentliches ELF-Format oder Akzeptieren beliebiger Zusatzabschnitte.

14 eingefrorene Gruppen prüfen echte Hostfunktionen O0/O2, ungültige RAM-Karten,
Reserven/Löcher, Hierarchie, Nullung/Mangel/Rollback, Metadatenfehler und alle
betroffenen64-Bit-Frameverbraucher.1/4/8GiB-QEMU muss echte hohe Frames und
vollständiges Retirement beweisen, nicht nur einen größeren Zahlenwert melden.
Invalides Bootmaterial darf keinen Betrieb beginnen. Große Gast-RAM-Angaben
erlauben keinen Test, der den Host-RAM vollständig belegt. Alte IPC-/Frame-
Prüfungen, i386-/VMware-Referenzen und offene historische Gates bleiben bestehen.
