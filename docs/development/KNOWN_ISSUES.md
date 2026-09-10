# Bekannte offene Probleme

Stand: 10. September 2026, Softwarestand `a3fa8dfb`.

## Offene Grenzen und priorisierte Folgearbeit

- **Farbausgabe:** einfacher sicherer Shell-/JS-Farbweg fehlt. Der VGA-
  Altpfad versteht einzelne SGR-Farben, der Framebuffer nicht; JS filtert ESC.
  Keine pauschale Freigabe von Terminal-Steuersequenzen als Reparatur.
- **CLI-API / Exitstatus:** `system.args/cwd/exit`, `fs.*` und `%ERRORLEVEL%`
  sind Vorschläge, keine aktuelle API. `reist.setExitCode(0..125)` setzt nur
  den Abschlusscode; die Shell wartet auf Kinder, veröffentlicht ihren Status
  aber noch nicht als Skriptvariable. Pipes/Verkettung sind nicht implementiert.
- **Policy / Manifeste:** `--grant=...`, signierte Skriptmanifeste und
  administrative JS-Hosts sind noch nicht implementiert. Eine Signatur oder
  CLI-Anforderung erteilt keine Rechte. Geplante Delegations- und Prüfgrenzen:
  [JS-Work-Paper](OS_JAVASCRIPT_SCRIPTING_WORK_PAPER.md).
- **JS-Schreibrechte / Verzeichnisse:** R3.36 delegiert einzelne lesbare
  Objekte. R3.42 ist ein FAT32-Schreibbackend, keine JS-Freigabe. Sichere
  Pfadauflösung relativ zu stabilen Verzeichnisrechten fehlt weiterhin.
- **Browser:** dynamische DOM-Ereignisse/Fragmente, Timer und asynchrones fetch,
  Webfonts und vollständige Layout-/Formularkompatibilität bleiben offen.
  Ein erfolgreicher URL-Load beweist keine vollständige Seitenfunktion.
- **R3.6b:** VMware-Pointer-/Hover-Abnahme ausdrücklich zurückgestellt. Die
  verbesserten manuellen Geschwindigkeitsbeobachtungen und die späteren
  QEMU-Gates ersetzen ihre ursprünglichen VMware-Gates nicht.
- **Hardware/Assurance:** breite Controller-/BIOS-/USB-Matrix, reale Power-
  Loss- und unabhängige Supervisor-/DMA-Isolation nicht allgemein nachgewiesen.

## Historische, nicht aufgeklärte R3.41-Risiken

- **R341-H1:** `resume-arp/guest-wrap/result.json`: ein 128-KiB-Stage-5-Read
  wurde vor der beabsichtigten Hang-Injektion verweigert. Quarantäne und Prompt
  folgten, Datenträger unverändert. Der ursprüngliche errno fehlt; die konkrete
  Admission-/Transport-/Completion-Ursache ist nicht bewiesen.
- **R341-H2:** `resume-arp/guest-timer/result.json`: STAT erfolgreich, kein
  folgender Prompt innerhalb 120s. Medium entspricht dem Erfolgsoracle;
  Exit/Wait/UART-/Host-Kontinuitätsdaten fehlen. Gast-Liveness- oder Beobachtungs-
  fehler nicht ausgeschlossen; Standby ist keine nachgewiesene Erklärung.

Die explizite Risikoentscheidung erlaubt nicht, neue Fehler zu ignorieren.
Originale Fehlbelege bleiben fehlgeschlagen. Vollständiger Vertrag:
[FAT32-Handoff](../architecture/FAT32_RING3_HANDOFF_CONTRACT.md).

## VMWARE-GUI-001: instabiler Retained-Surface-Resize

- Status: zurückgestellt, offen
- Betroffen: VMware-Gast mit SVGA-II/Desktop und mehreren vCPUs
- Nicht reproduziert: bisherige Tests auf echter Hardware
- Symptom: Nach interaktivem Resize von Notepad können verzögerte oder
  unvollständige Repaints auftreten; in einzelnen Läufen beendet sich die
  Anwendung oder der Desktop wird instabil.
- Bereits eingegrenzt: Configure/ACK verwendet die bestätigte Surface-Größe,
  der finale ACK invalidiert die vollständige Clientfläche und Resize benutzt
  keinen asynchronen VMware-RECT_COPY mehr. Die Beobachtung bleibt trotzdem
  offen und gilt nicht als geschlossen, bis sie auf VMware wiederholt und mit
  Gastdiagnose korreliert wurde.
- Nächste Untersuchung: serielle Gastlogs mit Prozessende-/Page-Fault-Marker,
  Configure- und Paint-Serials, SVGA-Fencezustand, vCPU-Anzahl sowie p95/p99
  von Resize-Event bis Frame-Commit erfassen. Mit einem und mehreren vCPUs und
  deaktivierter SVGA-Beschleunigung vergleichen.
- Abschlusskriterium: mindestens 100 automatisierte Resize-Sequenzen unter
  VMware ohne Prozessabbruch, verlorenen Damage oder fehlerhaften Frame sowie
  ein negativer Kontrolllauf auf echter Hardware.

Diese Notiz ist ein Fehlerdatensatz, kein Zertifizierungs- oder
Zuverlässigkeitsnachweis.
