# JavaScript-Beispiele fuer die REIST-Shell

## Paketvertrag R3.43

Definition vom 10. September 2026 auf `f808b558`. Nutzerauftrag: einige
Testskripte zum direkten Ausfuehren in der normalen Ring-3-Shell bereitstellen.
Genau ein Daten-/Integrationspaket, keine Erweiterung der JS-Hostrechte.
Referenzen: ECMA-262-Sprachsemantik und die bereits implementierten
[Runner-](../architecture/OS_JAVASCRIPT_RUNNER_CONTRACT.md) und
[Datei-Capability-Vertraege](../architecture/OS_JAVASCRIPT_FILE_CAPABILITY_CONTRACT.md).
Kein Node.js-/Browser-API-Kompatibilitaetsanspruch.

Sechs kurze, kommentierte und selbstpruefende Skripte unter `/htdocs`, mit
8.3-kompatiblen Namen identisch im Repository und beiden Referenzimages:
Argumente/Konsole, Berechnungen/Arrays, JSON/Klassen, aufgefangene Fehler,
fehlende Ambient-Rechte und explizites Datei-Lesen. Ein fehlgeschlagener
Selbsttest wirft eine normale JS-Ausnahme; kein nativer Fault/Hang-Test.
Alle Schleifen/Lesemengen bleiben klein und fest begrenzt. Dateibeispiel
schliesst sein delegiertes Objekt explizit auch bei Ausnahmen.

Unveraendert: Kernel, alle Programme, JS-Engine/GC/IPC, Browser, Shell,
5s-Ausfuehrung, Speicher- und Recoverybudgets. Keine Schreib-/Prozess-/Netz-
oder Admin-Rechte. Kein automatischer Start beim Boot. Die fehlenden
JS-Schreibrechte und die zurueckgestellte VMware-Abnahme sind nicht Teil davon.

Eingefrorene Dateiliste und fuenf Gates stehen in `automation/reist-s03b.toml`:
gezielter Hosttest zuerst, zwei sequentielle Referenzbuilds, Imagevergleich,
ein headless QEMU-Gast. Der Imagevergleich bindet die archivierten R3.42-
Images an ihre SHA256-Werte und verlangt bytegleiche Kernel/alle PRGs sowie
exakte neue Skriptbytes. Kein erneuter Benchmark fuer unveraenderten Code.
Der bestehende JS-Gastpruefer erhaelt nur einen opt-in Beispielsatz; seine
bisherigen Assertions und 180s/1024MiB bleiben erhalten. Sechs Beispiele
zweimal aus der normalen Shell, exakte geordnete Resultate und Shell-Fortschritt;
Host-Negativtests lehnen fehlende, doppelte, falsche und fatale Belege ab.
Logs unter `build/codex-agent/r343-js-examples/`; Fehlversuche erhalten.
Nach bestandenen Gates Diff/Scope pruefen, Queue umschalten und lokal committen.

## Aufrufe

Die Beispiele stehen nach dem Image-Neubau unter `/htdocs` bereit.
Aufruf aus der normalen Shell, nicht im Browser oder der Kernel-Rettungsshell:

```text
js /htdocs/jsargs.js hallo 42
js /htdocs/jsmath.js
js /htdocs/jsjson.js
js /htdocs/jserror.js
js /htdocs/jssafe.js
js --read /htdocs/hello.js /htdocs/jsread.js
```

Jedes Skript gibt am Ende eine eigene `JS_EXAMPLE_..._OK`-Zeile aus, wenn
seine Pruefungen erfolgreich waren. `jsargs.js` zeigt zusaetzlich die
uebergebenen Argumente; sie sind Daten, kein auszufuehrender Quelltext.
Die Shell trennt an Leerzeichen und verarbeitet derzeit keine Anfuehrungszeichen.
Mehrzeiligen Quelltext deshalb in Dateien schreiben, nicht hinter `js -e`.

`jserror.js` faengt absichtlich eine JS-Ausnahme ab und prueft `finally`;
das Skript soll erfolgreich enden, kein OS-Absturz entstehen.
`jssafe.js` prueft den normalen Kontext ohne Dateifreigaben. Das ist ein
API-Selbsttest, kein Ersatz fuer den separaten nativen Sandbox-Nachweis.

`jsread.js` liest maximal 64 Bytes der explizit freigegebenen Datei, prueft
Seek, EOF und Close und schreibt nichts. `--read` erteilt nur Leserechte
fuer dieses eine stabile Objekt, keine Verzeichnisrechte. Ohne Freigabe
endet das Skript mit einem erklaerenden Hinweis und einer JS-Ausnahme.
Bestehende Beispiele `hello.js` und `readfile.js` bleiben ebenfalls vorhanden.

Ausgaben werden gepuffert und erst nach abgeschlossener Ausfuehrung validiert
ausgegeben. Timer, Netzwerk, Prozesse, DOM und Dateischreiben werden in diesen
Shell-Beispielen weder vorausgesetzt noch freigeschaltet.
