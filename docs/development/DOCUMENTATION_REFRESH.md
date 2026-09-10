# Dokumentationsabgleich vom 10. September 2026

## Eingefrorener Arbeitsumfang D1.1

Ausgang: `a3fa8dfb` (R3.43). Nutzerauftrag: die gesamte Dokumentation auf den
aktuellen Stand bringen. Inventar: 104 bestehende projekteeigene Markdown-
Dokumente unter docs sowie die Einstiegspunkte in README, scripts, userspace,
assets und drivers/usb. AGENTS.md, fremde Upstream-Dokumente, Lizenzen und
generierte Buildbelege sind keine umzuformulierende Produktdokumentation.

Ein zusammenhaengender Dokumentationsschnitt: aktuelle Bedienung, Build,
Architektur-/Featurestatus, offene Fehler, C++-/JS-Fahrplan, Index und lokale
Verweise. Keine Softwareimplementierung, geaenderten Sicherheitsbudgets oder
neuen Abnahmebehauptungen. Historische Fehlerbelege bleiben erhalten;
eingefrorene Vertragsanforderungen werden nicht nachtraeglich abgeschwaecht.

Quellenreihenfolge: Paketqueue, Zielarchitektur, Roadmap, Core-/Subsystem-
Vertrag, dann Code/Tests und bereits akzeptierte Belege. Ein Statuswort ist
keine Implementierung: angenommen, teilweise implementiert, geplant und
hardwareseitig offen muessen unterscheidbar bleiben. Datierten Chroniken wird
ihr damaliger Kontext belassen. Die aktuelle Kurzreferenz ist PROJECT_STATUS.

Arbeitsschritte:

1. Gesamtes Erstparteieninventar und lokale Verweise erfassen; aktuelle
   Einstiegspunkte gegen Code, Queue und R3.42/R3.43-Belege pruefen.
2. Regression fuer Inventar, Links/Anker, aktuelle Kernfakten, geschuetzten
   Runtime-Scope und erhaltene JS-Beispiele hinzufuegen.
3. Veraltete Anleitungen und Statusangaben korrigieren, Fehlstellen offen
   benennen und die Navigation zu saemtlichen Vertragen vervollstaendigen.
4. Genau die drei Queue-Gruppen ausfuehren: Dokumentationstest, vorhandener
   JS-Beispieltest, diff --check. Keine Builds/VMs fuer reine Textaenderungen.
5. Diff und unveraenderten Runtime-Scope pruefen, Belege unter
   build/codex-agent/d11-documentation/ sichern, Queueuebergang und lokaler
   Commit. Kein Push.

Die Farbausgabe bleibt der naechste Implementierungsauftrag vor expliziten
JS-Schreibrechten. Die formale R3.6b-Aktivierung nach diesem Paket widerruft
nicht die ausdrueckliche VMware-Zurueckstellung. R341-H1/H2 bleiben offen.

## Inventar und Leseregeln

Das vollstaendige verlinkte Register steht im Dokumentationsindex. Der
Dokumentationstest erfasst alle Erstparteien-Markdown-Dateien (einschliesslich
dieses neuen Berichts), prueft ihre lokalen Verweise und schreibt den
maschinenlesbaren Bestandsbericht in den ignorierten Belegordner. Historische
Texte erhalten kein falsches neues Abnahmedatum. Normative Zielvertraege sind
keine Behauptung, dass bereits die gesamte Zielarchitektur implementiert sei.

## Ergebnis und Grenzen des Abgleichs

Softwarestand bleibt R3.43 (`a3fa8dfb`), keine Produktionsquelle geändert.
105 projekteeigene Dokumente sind vollständig indexiert. Der lokale Linktest
hat nach der Korrektur des FAT12-Inhaltsverzeichnisankers keine fehlenden
Dateien/Überschriften gefunden. Aktuelle Übersichten trennen die abgenommenen
C++-/Browser-/TTF-/JS-/Storage-Schritte von den unveränderten historischen
Einträgen und den offenen VMware-/R341-H1/H2-Belegen.

Bedienung ist an die echte Ring-3-Shell angeglichen: direkter Programmstart,
exakter JS-Quellname, keine Quote-/Variablen-/Pipe-Auswertung; 512 MiB
Referenzplatte und 1024 MiB VM-RAM; NAT als VMware-Vorgabe. Anzeige/Maus,
große Surface-Geometrie, EXT2-Recovery und FAT32-/ATA-Schreibobjekte sind
aktualisiert. Der neue JS-API-/Exitstatus- und Policy-/Manifest-Vorschlag
bleibt ausdrücklich geplant: Signaturen oder CLI-Anträge erzeugen keine Rechte.

Dokumentationstest: 7 PASS/1.021s. Unveränderte JS-Beispieltests: 6 PASS/0.112s.
Das abschließende `git diff --check` bestand als drittes Gate in 0.169s;
Belege und ursprünglicher negativer Test bleiben im genannten Belegordner.
Die JSON-Inventarliste enthält Pfade, Hashes und lokale Linkanzahlen zum
Prüfzeitpunkt; abschließende Ergebnis-/Queuebuchführung folgt danach.
Dies ist kein Beweis jeder Prosa-Aussage durch einen neuen Runtime-Test,
keine Prüfung externer URLs und keine erneute Hardware-/Performanceabnahme.
