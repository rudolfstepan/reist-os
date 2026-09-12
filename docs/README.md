# Dokumentationsindex

Stand: 11. September 2026; R3.44-Terminalfarben und R3.45-JS-Farbausgabe abgenommen.

Die Dokumentation unterscheidet zwischen aktuellen Referenzen und
historischen Arbeitsberichten. Für Aufbau, Start und Bedienung sind die hier
als **aktuell** bezeichneten Dokumente maßgeblich. Historische Berichte
erklären frühere Entscheidungen, können aber alte Dateipfade, Befehle oder
bereits behobene Fehler enthalten.

## Globale Struktur und Zuständigkeit

Aktiver nativer Programmschnitt: [Bootprogramm-Vertrag](architecture/NATIVE_BOOT_PROGRAMS_CONTRACT.md).

Jede Information besitzt genau einen fachlich autoritativen Ort. Andere
Dokumente geben nur eine kurze Einordnung und verlinken dorthin; sie kopieren
keine vollständigen Statuslisten, ABI-Tabellen oder Bedienungsabläufe.

| Ort | Einzige Aufgabe | Darf nicht duplizieren |
|---|---|---|
| `README.md` | Projekteinstieg, kleinster Schnellstart, wichtigste Grenzen | vollständige Architektur- oder Subsystemverträge |
| `docs/README.md` | globaler Index, Dokumentrollen und Aktualitätsregeln | Subsystemdetails |
| `docs/development/PROJECT_STATUS.md` | kompakter, belegter Ist-Stand und offene Systemgrenzen | Implementierungsanleitungen und ABI-Definitionen |
| `docs/architecture/` | normative, versionierte Architektur-, Sicherheits- und API-Verträge | historische Arbeitsprotokolle |
| `docs/features/`, `docs/filesystems/`, `docs/hardware/`, `docs/networking/` | aktuelles beobachtbares Verhalten je Fachgebiet | globale Roadmap und Paketqueue |
| `docs/development/` | Build-/Testworkflows, Roadmap und klar markierte Arbeitspakete | normative API-Verträge |
| `userspace/*/README.md`, `assets/*/README.md`, `scripts/*.md` | lokale Quellbaum-, Asset- oder Werkzeugreferenz | globalen Projektstatus |

Für Anforderungen und Arbeitsreihenfolge gilt: Paketqueue, Zielarchitektur,
Roadmap, Core-/Subsystemvertrag, dann Code und Tests als Bestandsaufnahme.
Code und bestandene Gates belegen nur den tatsächlich implementierten Umfang;
sie setzen die normative Fehlergrenze nicht außer Kraft. Bestehende monolithische
Altlasten sind kein Präzedenzfall für neue Kernelpolitik. Der Projektstatus
komprimiert diese Belege, historische Berichte behalten ihren damaligen Kontext.

Pflegevorgaben:

- Ein Statuswort wie **aktiv** darf nur die Paketqueue ableiten. Abgeschlossene
  Pakete tragen Datum und Status **abgeschlossen**.
- Aktuelle, statusabhängige Zentralreferenzen tragen einen `Stand:`.
  Historische Dokumente beginnen mit einem deutlich sichtbaren Hinweis und
  werden inhaltlich nicht auf einen heutigen Betriebsweg umgedeutet.
- Öffentliche ABI/API-Details stehen im zuständigen Architekturvertrag und in
  den inline dokumentierten Headern. Quickstarts und Statusseiten verlinken
  dorthin.
- Befehle werden in der normalen Ring-3-Shell und in beiden Image-Layouts
  geprüft; ein Rescue-Shell-Befehl allein wird nicht als reguläre Funktion
  dokumentiert.
- Hardwarebeobachtung, Hosttest, QEMU-/VMware-Gasttest und allgemeine
  Unterstützung bleiben sprachlich getrennte Evidenzstufen.
- Screenshots werden mit dem versionierten
  [QEMU-Capture](assets/screenshots/README.md) erzeugt, nur an fachlich
  passenden Stellen eingebunden und enthalten keine alleinige Status- oder
  ABI-Aussage.

## Einstieg und aktueller Stand

- [Projektübersicht](../README.md) – Schnellstart, Funktionen und Grenzen
- [Quickstart](development/QUICKSTART.md) – nativer Windows-Build und erster Start
- [Projektstatus](development/PROJECT_STATUS.md) – verifizierte Komponenten und offene Grenzen
- [Fehlstellenanalyse und Roadmap](development/OS_GAP_ANALYSIS_AND_ROADMAP.md) – priorisierte Implementierungspakete mit Abhängigkeiten und Abnahmekriterien
- [REIST High-Assurance Core Contract](architecture/HIGH_ASSURANCE_CORE_CONTRACT.md) – verbindliche, branchenunabhängige Regeln für Fehlerbegrenzung, Recovery und Nachweisführung
- [Resilienz- und Degradierungsvertrag](architecture/RESILIENCE_AND_DEGRADATION_CONTRACT.md) – globales Stabilitätsversprechen, Restartbudgets und terminale Systemzustände
- [Ring-3-Treibermodell](architecture/USERSPACE_DRIVER_MODEL.md) – Gerätebesitz, IRQ-, MMIO-/PIO- und DMA-Grenzen für neu startbare Treiber
- [Audiosubsystem](architecture/AUDIO_SUBSYSTEM.md) – Ring-3-HDA-Treiber,
  PCM-Service, `libreistaudio` und vollständig vermitteltes DMA
- [Medical Reference Profile](architecture/MEDICAL_HIGH_ASSURANCE_CONTRACT.md) – optionale medizinische Verschärfung; keine klinische Freigabe
- [REIST-Zielarchitektur](architecture/REIST_ARCHITECTURE.md) – Detect, Contain, Recover, Validate und Reintegrate als technisches Systemmodell
- [Build-Modi](development/BUILD_MODES.md) – `qemu`, `vmware`, `real_hw` und Videoauswahl
- [Nativer Bootdatenträger](development/BOOTABLE_DISK.md) – BIOS/MBR, Stage 2 und FAT32-Image
- [Bootfähige Diskette](development/FLOPPY_BOOT.md) – 1,44-MB-CHS-Image für echte BIOS-PCs
- [Externe Programme](development/USER_PROGRAM_TOOLCHAIN.md) – SDK, ABI und MYPR-Toolchain
- [Userspace-SDK und Portabilität](architecture/USERSPACE_SDK_AND_PORTABILITY.md) – modulare Bibliotheken, Upstream-Toolchain und API-Dokumentationsvertrag
- [GUI-Komponenten, Controls und Dialoge](architecture/GUI_CONTROLS_AND_DIALOGS.md) – unterstützte UI-Bausteine, Dialogstandard und schrittweise Control-Roadmap
- [GUI-Quellbaum und installierte Anwendungen](../userspace/gui/README.md) –
  Compositor, Surface-Clients, SDK-Beispiele und kanonische Imagepfade
- [Image-Library und Bildbetrachter](architecture/IMAGE_SUBSYSTEM.md) –
  wiederverwendbare BMP-/GIF-Decoder und der windowed Surface-Client
- [System- und Programmkonfiguration](architecture/SYSTEM_CONFIGURATION.md) – `/etc/reist`, versionierte Einstellungsdateien und sichere Rückfallwerte
- [Grafischer Desktop-Workflow](development/GRAPHICAL_DESKTOP_WINDOW_MANAGER_WORKFLOW.md) – Window-Manager-, Surface-, GUI-SDK- und VMware-Arbeitsschritte
- [Userspace-Dateisystemwerkzeuge](development/USERSPACE_FILESYSTEM_TOOLS.md) –
  Werkzeuginventar, Systemhierarchie und Timestamp-Vertrag
- [Synchronisationsvertrag](architecture/SYNCHRONIZATION_CONTRACT.md) – Ausführungskontexte, Lock-Reihenfolge und Diagnose

## Bedienung und Laufzeit

- [JS-Shell-Beispiele](development/JS_SHELL_EXAMPLES.md) – sieben gelieferte
  Skripte einschließlich ASCII-Mandelbrot, Argumente und explizite Leserechte
- [Gemeinsame JS-Laufzeit](development/OS_JAVASCRIPT_SCRIPTING_WORK_PAPER.md) –
  aktuelle API, geplante CLI-Fassade/Exitstatus und Policy-/Manifest-Delegation
- [Bekannte Fehler und Grenzen](development/KNOWN_ISSUES.md) – einschließlich
  offener R341-H1/H2-Belege und zurückgestellter VMware-Abnahme
- [Aktueller Arbeitsnachweis](development/CURRENT_WORK.md) und
  [Dokumentationsabgleich](development/DOCUMENTATION_REFRESH.md)
- [Shell und Pfade](features/SHELL_ENHANCEMENTS.md) – DOS-artige Befehle und Tastaturbearbeitung
- [Laufwerke und Mounts](filesystems/DRIVE_MOUNTING_SYSTEM.md) – Zuordnung, VFS-Pfade und Laufwerkswechsel
- [VFS-Architektur](filesystems/VFS_ARCHITECTURE.md) – gemeinsame Dateisystemschnittstelle
- [BASIC-Interpreter](features/BASIC_INTERPRETER.md) – Syntax, Laden und Speichern
- [Tastaturkürzel](features/KEYBOARD_SHORTCUTS.md) – Zeilenbearbeitung und Verlauf
- [Framebuffer](features/FRAMEBUFFER.md) – nativer VBE-Pfad, Ring-3-Display-ABI und Desktop-MVP

## Hardware und Netzwerk

- [PCI-Geräte und Treiberstatus](hardware/PCI_DEVICES.md) – übliche PCI-Klassen,
  erkannte Geräte und tatsächlich unterstützte REIST-Treiber
- [PCI-Audio-Arbeitspaket](development/PCI_AUDIO_WORK_PACKAGE.md) –
  abgeschlossenes Implementierungsprotokoll der ersten HDA-Wiedergabe
- [Fertige VMware-VM](hardware/VMWARE.md) – VMX/VMDK, LAN-Bridge und Fehlerdiagnose
- [Netzwerkstack](networking/NETWORK.md) – Ethernet-Treiber, DHCP, ARP,
  IPv4/ICMP, UDP, DNS, TCP und HTTP/1.0
- [TAP-Netzwerk](networking/TAP_NETWORKING.md) – optionaler Linux/QEMU-Testweg
- [USB-Design](hardware/USB_DESIGN.md) – begrenzter xHCI-/HID-Stand und
  offene Geräteklassen
- [EXT2](filesystems/EXT2_SUPPORT.md), [FAT12](filesystems/FAT12_IMPROVEMENTS.md) und
  [FAT32](filesystems/FAT32_OPTIMIZATIONS.md) – Dateisystemstatus und Grenzen

## Tests

- [Tests ausführen](../scripts/README_TESTING.md) – aktuelle Befehle
- [Testabdeckung](../scripts/TESTING_SUMMARY.md) – geprüfte Invarianten und Grenzen

Der derzeitige Referenzdatenträger ist ein BIOS/MBR-Image mit einer markierten
FAT32-Systempartition. VMware verwendet SATA/AHCI, QEMU hält zusätzlich den
ATA/IDE-Regressionspfad bereit. Für reale Datenträger dürfen ausschließlich
die zielgebundenen Installationsskripte nach Prüfung von Modell, Seriennummer
und Größe verwendet werden.

## Historische Arbeitsberichte

Die folgenden Dokumente bleiben als Entwicklungsprotokoll erhalten. Ihre
Kopfzeile weist darauf hin, dass sie nicht den aktuellen Betriebsweg
beschreibt:

- `architecture/ARCHITECTURE_IMPROVEMENTS.md`
- `development/DIAGNOSTIC_REPORT.md`
- `development/REORGANIZATION.md`
- `development/FIXES_ISSUE_1_INTERRUPT_MANAGEMENT.md`
- `development/PRIORITY3_CURSOR_POSITIONING.md`
- `development/DEBUGGING_BOOT_SECTOR.md`
- `hardware/KEYBOARD_ANALYSIS.md`
- `hardware/KEYBOARD_IMPROVEMENTS.md`
- `networking/NE2000_LOOPBACK_FIX.md`
- `features/BASIC_INTERPRETER_UPDATES.md`
- `filesystems/FAT12_ANALYSIS.md`

Abgeschlossene Arbeitspakete wie
`development/RUNTIME_GRAPHICS_DESKTOP_WORK_PACKAGE.md`,
`development/USERSPACE_DRIVER_DOMAIN_WORK_PACKAGE.md` und
`development/PCI_AUDIO_WORK_PACKAGE.md` dokumentieren Scope und Abnahme eines
bestimmten Entwicklungsstands. Für den heutigen Betriebsweg gelten die oben
verlinkten Referenzdokumente.


## Vollständiges Register

- [JavaScript-Farbausgabe](architecture/JS_COLOR_OUTPUT_CONTRACT.md) – R3.45-Hostgrenze und Abnahme

- [Native x86_64-Fertigstellung](development/X86_64_COMPLETION_WORK_PAPER.md) – Bestand, Umsetzung und Systemabnahme

108 projekteeigene Markdown-Dokumente einschließlich dieses Index und des
Abgleichberichts. Upstream-Texte, Lizenzen, AGENTS.md und generierte Belege
werden nicht zu aktuellen Produktanleitungen umgeschrieben. Ein Vertrag
beschreibt Anforderungen und abgegrenzte Teilabnahmen, nicht automatisch
einen vollständig implementierten Funktionsumfang. Normative Zielprofile,
Arbeitspläne und historische Texte behalten ihre jeweilige Rolle und Datierung.

### Architekturverträge und technische Referenzen

- [architecture/TERMINAL_COLOR_OUTPUT_CONTRACT.md](architecture/TERMINAL_COLOR_OUTPUT_CONTRACT.md)
- [architecture/ARCHITECTURE_DEEP_DIVE.md](architecture/ARCHITECTURE_DEEP_DIVE.md)
- [architecture/ATA_PIO_TRANSFER_CONTRACT.md](architecture/ATA_PIO_TRANSFER_CONTRACT.md)
- [architecture/AUDIO_SUBSYSTEM.md](architecture/AUDIO_SUBSYSTEM.md)
- [architecture/BROWSER_ENGINE_PORT_PLAN.md](architecture/BROWSER_ENGINE_PORT_PLAN.md)
- [architecture/BROWSER_FORM_INTERACTION_CONTRACT.md](architecture/BROWSER_FORM_INTERACTION_CONTRACT.md)
- [architecture/BROWSER_PUBLIC_NAVIGATION_CONTRACT.md](architecture/BROWSER_PUBLIC_NAVIGATION_CONTRACT.md)
- [architecture/BROWSER_SCRIPTING_CONTRACT.md](architecture/BROWSER_SCRIPTING_CONTRACT.md)
- [architecture/DISPLAY_SETTINGS_CONTRACT.md](architecture/DISPLAY_SETTINGS_CONTRACT.md)
- [architecture/EXTERNAL_SAFETY_MONITOR_CONTRACT.md](architecture/EXTERNAL_SAFETY_MONITOR_CONTRACT.md)
- [architecture/FAT32_RECOVERY_ADMISSION_CONTRACT.md](architecture/FAT32_RECOVERY_ADMISSION_CONTRACT.md)
- [architecture/FAT32_RING3_HANDOFF_CONTRACT.md](architecture/FAT32_RING3_HANDOFF_CONTRACT.md)
- [architecture/FAT32_WRITABLE_OBJECT_CONTRACT.md](architecture/FAT32_WRITABLE_OBJECT_CONTRACT.md)
- [architecture/FILE_OBJECT_LIFETIME_CONTRACT.md](architecture/FILE_OBJECT_LIFETIME_CONTRACT.md)
- [architecture/FPU_CONTEXT_ISOLATION_CONTRACT.md](architecture/FPU_CONTEXT_ISOLATION_CONTRACT.md)
- [architecture/GUI_CONTROLS_AND_DIALOGS.md](architecture/GUI_CONTROLS_AND_DIALOGS.md)
- [architecture/GUI_RENDERING_INPUT_AND_LATENCY_CONTRACT.md](architecture/GUI_RENDERING_INPUT_AND_LATENCY_CONTRACT.md)
- [architecture/HIGH_ASSURANCE_CORE_CONTRACT.md](architecture/HIGH_ASSURANCE_CORE_CONTRACT.md)
- [architecture/HIGH_RESOLUTION_SURFACE_CONTRACT.md](architecture/HIGH_RESOLUTION_SURFACE_CONTRACT.md)
- [architecture/IMAGE_SUBSYSTEM.md](architecture/IMAGE_SUBSYSTEM.md)
- [architecture/JAVASCRIPT_SERVICE_CONTRACT.md](architecture/JAVASCRIPT_SERVICE_CONTRACT.md)
- [architecture/KERNEL_LOG.md](architecture/KERNEL_LOG.md)
- [architecture/MEDICAL_HIGH_ASSURANCE_CONTRACT.md](architecture/MEDICAL_HIGH_ASSURANCE_CONTRACT.md)
- [architecture/MEMORY_RESILIENCE.md](architecture/MEMORY_RESILIENCE.md)
- [architecture/NATIVE_PHYSICAL_MEMORY_CONTRACT.md](architecture/NATIVE_PHYSICAL_MEMORY_CONTRACT.md)
- [architecture/NATIVE_PRIVATE_HEAP_CONTRACT.md](architecture/NATIVE_PRIVATE_HEAP_CONTRACT.md)
- [architecture/NATIVE_BOOT_MEDIA_CONTRACT.md](architecture/NATIVE_BOOT_MEDIA_CONTRACT.md)
- [architecture/NATIVE_RUNTIME_CLOCK_CONTRACT.md](architecture/NATIVE_RUNTIME_CLOCK_CONTRACT.md)
- [architecture/MOUSE_SETTINGS_CONTRACT.md](architecture/MOUSE_SETTINGS_CONTRACT.md)
- [architecture/NETWORK_ARP_LIFECYCLE_CONTRACT.md](architecture/NETWORK_ARP_LIFECYCLE_CONTRACT.md)
- [architecture/NETWORK_RECEIVE_PROGRESS_CONTRACT.md](architecture/NETWORK_RECEIVE_PROGRESS_CONTRACT.md)
- [architecture/OS_JAVASCRIPT_FILE_CAPABILITY_CONTRACT.md](architecture/OS_JAVASCRIPT_FILE_CAPABILITY_CONTRACT.md)
- [architecture/OS_JAVASCRIPT_RUNNER_CONTRACT.md](architecture/OS_JAVASCRIPT_RUNNER_CONTRACT.md)
- [architecture/PRIVATE_PROCESS_MEMORY_CONTRACT.md](architecture/PRIVATE_PROCESS_MEMORY_CONTRACT.md)
- [architecture/PROCESS_ARGUMENT_CONTRACT.md](architecture/PROCESS_ARGUMENT_CONTRACT.md)
- [architecture/REIST_ARCHITECTURE.md](architecture/REIST_ARCHITECTURE.md)
- [architecture/RESILIENCE_AND_DEGRADATION_CONTRACT.md](architecture/RESILIENCE_AND_DEGRADATION_CONTRACT.md)
- [architecture/RING3_FILE_WRITE_CONTRACT.md](architecture/RING3_FILE_WRITE_CONTRACT.md)
- [architecture/RING3_JAVASCRIPT_CORE_CONTRACT.md](architecture/RING3_JAVASCRIPT_CORE_CONTRACT.md)
- [architecture/RING3_MATH_RUNTIME_CONTRACT.md](architecture/RING3_MATH_RUNTIME_CONTRACT.md)
- [architecture/RING3_STRING_FORMAT_CONTRACT.md](architecture/RING3_STRING_FORMAT_CONTRACT.md)
- [architecture/SCHEDULER_BACKGROUND_SLACK_CONTRACT.md](architecture/SCHEDULER_BACKGROUND_SLACK_CONTRACT.md)
- [architecture/SMP_SUBSYSTEM.md](architecture/SMP_SUBSYSTEM.md)
- [architecture/STORAGE_GENERATION_RETIREMENT_CONTRACT.md](architecture/STORAGE_GENERATION_RETIREMENT_CONTRACT.md)
- [architecture/SYNCHRONIZATION_CONTRACT.md](architecture/SYNCHRONIZATION_CONTRACT.md)
- [architecture/SYSTEM_CONFIGURATION.md](architecture/SYSTEM_CONFIGURATION.md)
- [architecture/TERMINAL_INPUT_OWNERSHIP_CONTRACT.md](architecture/TERMINAL_INPUT_OWNERSHIP_CONTRACT.md)
- [architecture/USB_SUBSYSTEM.md](architecture/USB_SUBSYSTEM.md)
- [architecture/USERSPACE_DRIVER_MODEL.md](architecture/USERSPACE_DRIVER_MODEL.md)
- [architecture/USERSPACE_SDK_AND_PORTABILITY.md](architecture/USERSPACE_SDK_AND_PORTABILITY.md)
- [architecture/VIDEO_SUBSYSTEM.md](architecture/VIDEO_SUBSYSTEM.md)
- [architecture/WINDOW_STATE_CONTROLS_CONTRACT.md](architecture/WINDOW_STATE_CONTROLS_CONTRACT.md)
- [architecture/X86_64_BOOTSTRAP.md](architecture/X86_64_BOOTSTRAP.md)

### Entwicklung, Bedienung und Fachgebiete

- [REIST_CPP_MIGRATION_PLAN.md](REIST_CPP_MIGRATION_PLAN.md)
- [assets/screenshots/README.md](assets/screenshots/README.md)
- [development/BOOTABLE_DISK.md](development/BOOTABLE_DISK.md)
- [development/BUILD_MODES.md](development/BUILD_MODES.md)
- [development/CPP_MIGRATION_BASELINE.md](development/CPP_MIGRATION_BASELINE.md)
- [development/CURRENT_WORK.md](development/CURRENT_WORK.md)
- [development/DESKTOP_DISPLAY_SETTINGS_PLAN.md](development/DESKTOP_DISPLAY_SETTINGS_PLAN.md)
- [development/DOCUMENTATION_REFRESH.md](development/DOCUMENTATION_REFRESH.md)
- [development/FLOPPY_BOOT.md](development/FLOPPY_BOOT.md)
- [development/GRAPHICAL_DESKTOP_WINDOW_MANAGER_WORKFLOW.md](development/GRAPHICAL_DESKTOP_WINDOW_MANAGER_WORKFLOW.md)
- [development/JS_SHELL_EXAMPLES.md](development/JS_SHELL_EXAMPLES.md)
- [development/KNOWN_ISSUES.md](development/KNOWN_ISSUES.md)
- [development/OS_GAP_ANALYSIS_AND_ROADMAP.md](development/OS_GAP_ANALYSIS_AND_ROADMAP.md)
- [development/OS_JAVASCRIPT_SCRIPTING_WORK_PAPER.md](development/OS_JAVASCRIPT_SCRIPTING_WORK_PAPER.md)
- [development/PCI_AUDIO_WORK_PACKAGE.md](development/PCI_AUDIO_WORK_PACKAGE.md)
- [development/PROJECT_STATUS.md](development/PROJECT_STATUS.md)
- [development/QUICKSTART.md](development/QUICKSTART.md)
- [development/RUNTIME_GRAPHICS_DESKTOP_WORK_PACKAGE.md](development/RUNTIME_GRAPHICS_DESKTOP_WORK_PACKAGE.md)
- [development/SOURCE_DOCUMENTATION_STANDARD.md](development/SOURCE_DOCUMENTATION_STANDARD.md)
- [development/USB_KEYBOARD_IMPLEMENTATION_PLAN.md](development/USB_KEYBOARD_IMPLEMENTATION_PLAN.md)
- [development/USERSPACE_DRIVER_DOMAIN_WORK_PACKAGE.md](development/USERSPACE_DRIVER_DOMAIN_WORK_PACKAGE.md)
- [development/USERSPACE_FILESYSTEM_TOOLS.md](development/USERSPACE_FILESYSTEM_TOOLS.md)
- [development/USER_PROGRAM_TOOLCHAIN.md](development/USER_PROGRAM_TOOLCHAIN.md)
- [features/BASIC_INTERPRETER.md](features/BASIC_INTERPRETER.md)
- [features/FRAMEBUFFER.md](features/FRAMEBUFFER.md)
- [features/KEYBOARD_SHORTCUTS.md](features/KEYBOARD_SHORTCUTS.md)
- [features/SHELL_ENHANCEMENTS.md](features/SHELL_ENHANCEMENTS.md)
- [filesystems/DRIVE_MOUNTING_SYSTEM.md](filesystems/DRIVE_MOUNTING_SYSTEM.md)
- [filesystems/EXT2_SUPPORT.md](filesystems/EXT2_SUPPORT.md)
- [filesystems/FAT12_IMPROVEMENTS.md](filesystems/FAT12_IMPROVEMENTS.md)
- [filesystems/FAT32_OPTIMIZATIONS.md](filesystems/FAT32_OPTIMIZATIONS.md)
- [filesystems/VFS_ARCHITECTURE.md](filesystems/VFS_ARCHITECTURE.md)
- [hardware/PCI_DEVICES.md](hardware/PCI_DEVICES.md)
- [hardware/USB_DESIGN.md](hardware/USB_DESIGN.md)
- [hardware/VMWARE.md](hardware/VMWARE.md)
- [networking/NETWORK.md](networking/NETWORK.md)
- [networking/TAP_NETWORKING.md](networking/TAP_NETWORKING.md)

### Historische Analysen

- [architecture/ARCHITECTURE_IMPROVEMENTS.md](architecture/ARCHITECTURE_IMPROVEMENTS.md)
- [development/DEBUGGING_BOOT_SECTOR.md](development/DEBUGGING_BOOT_SECTOR.md)
- [development/DIAGNOSTIC_REPORT.md](development/DIAGNOSTIC_REPORT.md)
- [development/FIXES_ISSUE_1_INTERRUPT_MANAGEMENT.md](development/FIXES_ISSUE_1_INTERRUPT_MANAGEMENT.md)
- [development/PRIORITY3_CURSOR_POSITIONING.md](development/PRIORITY3_CURSOR_POSITIONING.md)
- [development/REORGANIZATION.md](development/REORGANIZATION.md)
- [features/BASIC_INTERPRETER_UPDATES.md](features/BASIC_INTERPRETER_UPDATES.md)
- [filesystems/FAT12_ANALYSIS.md](filesystems/FAT12_ANALYSIS.md)
- [hardware/KEYBOARD_ANALYSIS.md](hardware/KEYBOARD_ANALYSIS.md)
- [hardware/KEYBOARD_IMPROVEMENTS.md](hardware/KEYBOARD_IMPROVEMENTS.md)
- [networking/NE2000_LOOPBACK_FIX.md](networking/NE2000_LOOPBACK_FIX.md)

### Lokale Quellbaum- und Werkzeugreferenzen

- [README.md](../README.md)
- [assets/audio/README.md](../assets/audio/README.md)
- [assets/fonts/README.md](../assets/fonts/README.md)
- [assets/icons/README.md](../assets/icons/README.md)
- [drivers/usb/usb_recommendations.md](../drivers/usb/usb_recommendations.md)
- [scripts/README_TESTING.md](../scripts/README_TESTING.md)
- [scripts/TESTING_SUMMARY.md](../scripts/TESTING_SUMMARY.md)
- [userspace/gui/README.md](../userspace/gui/README.md)
