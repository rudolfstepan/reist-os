# EXT2-Unterstützung

Stand: 10. September 2026; Software bis R3.43.

EXT2 ist als VFS-Adapter vorhanden. Es kann direkt auf einer veröffentlichten
Blockressource oder auf einer erkannten Partition liegen; ATA und AHCI werden
über denselben Blockgerätevertrag angesprochen.

## Verifiziert

- Superblock- und Signaturerkennung
- Partitionsoffsets
- Verzeichnisauflösung
- direkte und indirekte Blockadressierung im Host-Harness
- Mount und die explizit implementierten VFS-Operationen

Zusätzliche EXT2-Volumes werden unter `/mnt/<device>` veröffentlicht und über
den zugeordneten DOS-Buchstaben erreicht. Die eindeutige FAT32-Systempartition
bleibt Root und wird nicht durch ein früher erkanntes EXT2-Medium verdrängt.

## Grenzen

Der autoritative Ring-3-Storage-Pfad unterstützt inzwischen zusätzlich native,
begrenzte Symlinks und ausgewählte Namespace-Mutationen mit einem eigenen
REIST-Transaktionsjournal. `ln -s`, `readlink`, Unlink und gleichverzeichnisiges
Rename sind im [Werkzeugkatalog](../development/USERSPACE_FILESYSTEM_TOOLS.md)
beschrieben. Das ist kein EXT3-/EXT4-Journal und keine allgemeine
Schreibfreigabe des weiterhin lesenden Legacy-EXT2-Adapters.

R3.37 hat die COMMITTED-Recovery korrigiert: Widersprüchliche Zielsektoren
führen vor Write/Flush zu `EIO`, nicht zum Undo eines bereits abgeschlossenen
Commits. R3.38 bindet Namespace-Mutation und leseseitige Recovery an den
[gemeinsamen Dateiobjekt-Lebensdauervertrag](../architecture/FILE_OBJECT_LIFETIME_CONTRACT.md).
Nachweise und erhaltene Fehlversuche stehen in
[CURRENT_WORK](../development/CURRENT_WORK.md).

- keine EXT3-/EXT4-Kompatibilitätszusage, ACLs oder Extended Attributes
- keine allgemeinen EXT2-Schreibobjekte aus dem FAT32-/ATA-Paket R3.42
- kein automatisches Wiederholen eines unklar abgeschlossenen Schreibzugriffs
- kein Hotplug- oder Online-Resize-Lebenszyklus

EXT2 darf deshalb nach einem unklaren Schreibfehler nicht automatisch als
`ONLINE_RW` reintegriert werden.
