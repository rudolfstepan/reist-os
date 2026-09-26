# Native64 VGA-/Grafikwechsel: begrenzte Geraeteberechtigung

## Freigabe26.09.2026

Erneutes `mach weiter` unmittelbar nach der konkreten Berechtigungsfrage
zu Commit4a10641a gibt diesen Vorschlag frei. Umsetzung und Nachweis folgen
in NATIVE_VIDEO_MODE_CONTRACT.md; die folgenden Abschnitte dokumentieren
die vorangegangene Entscheidungsvorlage, keine erneute Freigabeanforderung.

## Stand und Entscheidung

26.09.2026, saubere abgenommene Grundlage `f96af9f6` (CJ).
Die echte VGA-Shell samt Hardwarecursor besteht alle fuenf Gates.
Der Fortsetzungsauftrag verlangt als naechsten Schritt den nativen Wechsel
zum echten Desktop und zurueck zur sichtbaren Textshell. Dieses Dokument
bereitet die erforderliche neue Geraeteberechtigung vor. Noch kein aktives
Implementierungspaket, keine Builds oder Gaeste fuer diese Erweiterung.

## Inventar und fehlender Mechanismus

- `arch/x86_64/video/display_domain.inc` bindet nur das unveraenderliche
  `native_display_boot`. Ohne Boot-Framebuffer liefert der Pfad `-19`.
- CJ prueft BIOS-Modus03 und lehnt einen Grafik-Boot-Framebuffer ab.
  VGA-Zellen und Cursorregister erteilen keine SVGA-Modusberechtigung.
- `arch/x86/boot/vbe_runtime.asm` ist ein32-Bit-Pfad; keine gepruefte
  Long-Mode-Umschaltung und keine native64-Portierungsgrundlage ohne Umbau.
- `drivers/video/display_control.c` kennt VMware-SVGA-II-Modusregister,
  Scanout-/BAR-Pruefung, FIFO sowie Disable/Rueckkehr. Dieser alte
  Kernel-Treiber ist nur Inventar, kein Architekturvorbild fuer Ring0.
- `userspace/drivers/video/vmware_svga2d.c` besitzt bereits Ring3-Policy mit
  begrenzten Wartezeiten, verwendet aber die andere Treiber-ABI.
- `userspace/sdk/lib/x86_64/shell_graphical.inc` besitzt bereits die
  generationengebundene grafische Lebensdauer. CB bleibt im geprueften
  Archiv02 und darf erst nach diesem Hardware-Vorbau wieder aufgenommen werden.

Referenzen: VMware SVGA-II Register-/FIFO-Protokoll, PCI-Konfigurationsraum,
IBM VGA-Modus03 und bestehende native Display-/Input-/Terminal-Vertraege.
Keine Behauptung allgemeiner Hardware- oder BIOS-Kompatibilitaet.

## Beantragte Autoritaet

Ein explizites Profil fuer das virtuelle VMware-SVGA-II-Geraet (PCI15ad:0405),
pruefbar auch mit dem entsprechenden QEMU-Geraet. Andere Grafikkarten bleiben
ausserhalb dieser Freigabe. Der freizugebende Wechsel ist ausschliesslich
VGA80x25 <-> Grafik1024x768x32; keine frei waehlbaren Modi.

1. Ein isolierter Ring3-Geraetedienst darf die feste Modussequenz anfordern
   und Rueckgabewerte pruefen. Der Supervisor bindet genau eine lebende
   Dienstgeneration und einen Epoch-Wert; Anwendungen erhalten keine
   Modusrechte. Der Compositor nutzt weiterhin seine begrenzte Display-ABI.
2. Ring0 vermittelt nur fest erlaubte SVGA-Registeroperationen, gepruefte
   Geraeteregionen und Fencing. Keine beliebigen Ports, Register, PCI-Schreib-
   operationen oder User-MMIO-Zeiger. PCI-Inventar und BAR-Groessen werden
   begrenzt geprueft; keine BAR-Verlegung oder Aktivierung von Bus-Mastering.
   Nicht bereits passend konfigurierte Geraete werden abgewiesen.
3. Erlaubte SVGA-Schreibzwecke: Protokoll-ID, Enable/Disable, feste Breite,
   Hoehe und Farbtiefe sowie gegebenenfalls FIFO-Konfiguration und Sync.
   Lesbare Status-/Geometrie-/Speichergroessen dienen nur der Validierung.
   Alle Werte und Operationsreihenfolgen werden vor Hardwarewirkung geprueft.
4. Framebuffer bleibt ausschliesslich im Kernel gemappt und wird nur ueber
   die vorhandene begrenzte Kopiergrenze beschrieben. Neu gebundene Region
   muss im validierten BAR liegen und darf weder RAM noch andere MMIO-Bereiche
   ueberlappen. NX/Cacheattribute und vollstaendige Bereichspruefung bleiben.
5. Falls fuer die sichtbare Ausgabe erforderlich: ausschliesslich feste
   SVGA_CMD_UPDATE-Rechtecke in einem kernelvermittelten, auf4KiB begrenzten
   FIFO-Bereich. Kein User-Kommando-Stream, keine3D-/Beschleunigungsbefehle,
   keine Gast-RAM-Adressen, DMA- oder IRQ-Rechte. Header/Positionen werden
   geprueft; bei voller Queue EAGAIN ohne Teilveroeffentlichung. Es wird
   hoechstens ein Update je bestehendem Display-Commit zugelassen.
6. Die vorhandene isolierte Terminal-Treiberrolle darf fuer dieses Profil
   Modussteuerung und PS/2 bedienen. Beide sind explizite Abhaengigkeiten
   derselben lokalen Terminal-Sitzung: Fehler beendet diese Sitzung und
   fuehrt ueber Fencing zur Textshell. Kein zusaetzlicher dauerhafter Task:
   Textkonsole4 wird vor Grafik ueberwacht beendet; grafische Rollen bleiben
   Compositor4/Treiber5/Anwendungen6 und7. Storage2/3 und Root0 unveraendert.
   Die konkrete Start-/Rueckkehrsequenz wird vor Codeaenderungen eingefroren.

Es werden keine CPU-, Heap-, Task-, Endpoint-, Display-Kopier- oder
Durchsatzgrenzen erweitert. Die bisherigen freigegebenen Desktop-Quoten
bleiben massgeblich. Kein neuer Netzwerk-/Dateischreibzugriff und keine
physischen Plattformen. Falls diese Grenzen nicht ausreichen, ist das ein
konkreter neuer Befund, keine implizite Erweiterung dieser Freigabe.

## Lebensdauer, Rueckkehr und Fehler

Zustaende TEXT -> PREPARING -> GRAPHICS -> REVOKING -> TEXT; jeder Schritt
generationen-/epochgebunden, mit absolutem Deadline-Ende. Im Kernel keine
Warteschleife. Ring3 pollt mit Sleep innerhalb der vorhandenen Deadline.
Health1000ms, Start/Rueckkehr2000ms, zwei Neustarts je10s als Obergrenzen;
engere Grenzen bestehender Dienste bleiben erhalten.

Bei normalem Desktop-Ende, Dienstcrash, Hang, falscher Generation oder
ungueltiger Hardwareantwort: Displayzugriffe sperren, Eingabe/alte Handles
widerrufen, Grafik abschalten, Treiber reapen, VGA-Dienst neu erstellen,
Selbsttest und sichtbaren Prompt samt Cursor pruefen. Keine parallelen
Text-/Grafikschreiber. Fencing darf die feste Disable-Operation auch nach
Treiberverlust ausfuehren. Eine fehlgeschlagene Rueckkehr bleibt diagnostiziert
im degradierten Zustand mit COM1; sie gilt nicht als bestandene VGA-Recovery.
Kernelkorruption wird nicht durch einen Treiberneustart verdeckt.

## Umsetzung und notwendige Abnahme nach Freigabe

Ein zusammenhaengendes Vorbaupaket mit expliziter Dateiliste und endlichem
Build-/Gastbudget vor Implementierung: native Register-/Mapping-Mediation,
Ring3-Moduspolicy, Supervisor-Handoff, ausgewaehlte Build-/Medienadapter und
Host-/Gastpruefer. Die bestehende VGA- und Grafik-ABI bleibt kompatibel;
neue Operationen werden angehaengt/versioniert. Unausgewaehlte Profile exakt
unveraendert. Keine Verschiebung der eingefrorenen CJ-/CB-Abnahmegrenzen.

Erforderliche Belege: reale Mechaniktests fuer falsche Besitzer/Generationen,
Rechte, BAR-/FIFO-Ueberlaeufe und ungueltige Sequenzen; vollstaendige
VGA->Grafik->VGA-Wechsel mit echten Pixeln und Eingabe; Crash/Hang waehrend
Vorbereitung, Grafikbetrieb und Rueckkehr; begrenzte Wiederherstellung und
Erschoepfung. QEMU-SVGA und echte VMware-Instanz muessen den Hardwareweg
jeweils nachweisen. Eine Grafik-Testflaeche prueft nur den Vorbau; danach
folgt der archivierte echte Desktop mit allen bisherigen Latenz-/App-Gates.

Diese Freigabe waere keine Abnahme des Codes oder der gesamten64-Bit-Version.


## Proposed QEMU prerequisite acceptance; VMware remains a final release gate

2026-09-26, pending explicit user decision; not implemented or accepted.

The user requests continued native64 completion and explicitly defers VMware
because its window/input capture disrupts host work. CK qualification01 passed
its four ordered non-VMware gates, including nine fresh QEMU cases and altered-
evidence rejection. Current gate5 cannot pass without actual VMware healthy
and driver-fault/return proofs. Existing package sequencing consequently blocks
CB real-desktop integration even in QEMU. A repeated request to continue is not
silently treated as authorization to waive the frozen hardware gate.

Proposed precise allocation:
1. Complete CK for the QEMU research profile only after the existing independent
   source/tool/scope/evidence review passes. Keep all four preceding gates,
   nine cases, tamper denials, timing/resource limits and historical failures.
2. Carry qualification01 proofs only after verifying every recorded source,
   tool, artifact and raw evidence hash. Any changed guest/build/capture/replay
   implementation requires the affected original gate again. A separately
   inventoried change confined to gate scheduling/receipt handling may carry
   the existing unchanged proofs after independent review; preserve original
   receipts and source freeze, and record the exact verifier diff separately.
3. Freeze actual VMware healthy and driver-fault/return acceptance as an open,
   mandatory platform milestone before claiming a usable VMware release or
   completed native64 OS. Keep180s per hardware case, exact owned cleanup,
   positive aperture inventory, real pixels, successful VGA restoration,
   post-return keyboard/cursor, all original guest safety limits and failure
   retention. QEMU evidence never satisfies these VMware checks.
4. Only after the scoped QEMU review/local commit and clean worktree may CB be
   restored as the sole active package and the real desktop integrated/tested
   under QEMU. Preserve its original tests and VMware delivery requirement.
   Label every intermediate artifact research/QEMU-qualified, VMware-unverified.
5. Do not launch or focus VMware until the user changes the existing deferral.
   Do not claim full CK hardware acceptance, finished desktop or finished OS.

This changes frozen acceptance allocation and therefore requires explicit user
approval under AGENTS.md. It adds no device, resource or process authority.
Without approval, CK remains active/uncommitted and CB remains archived.

## Decision 2026-09-26: scoped QEMU acceptance authorized

The user renewed "mach weiter" directly after the explicit question and
concrete proposal above. Apply that requested split: QEMU-only acceptance
after complete independent review, unchanged evidence reuse, mandatory final
VMware milestone still open. VMware remains closed. This is not a waiver of
the final VMware or OS acceptance.

Reserve acceptance-qemu01: one independent review <=600s, unchanged frozen
source/tool/image binding, all nine raw replays and evidence hashes, actual
tamper receipt, direct scope/diff review. Use a saved outer review script;
leave the frozen verifier and original full-platform --review fail-closed.
No new guest or build; original qualification receipts remain immutable.
