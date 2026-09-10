# JavaScript-Beispiele fuer die REIST-Shell

## Paketvertrag R3.43

Definition vom 10. September 2026 auf `f808b558`. Nutzerauftrag: einige
Testskripte zum direkten Ausfuehren in der normalen Ring-3-Shell bereitstellen.
Genau ein Daten-/Integrationspaket, keine Erweiterung der JS-Hostrechte.
Referenzen: ECMA-262-Sprachsemantik und die bereits implementierten
[Runner-](../architecture/OS_JAVASCRIPT_RUNNER_CONTRACT.md) und
[Datei-Capability-Vertraege](../architecture/OS_JAVASCRIPT_FILE_CAPABILITY_CONTRACT.md).
Kein Node.js-/Browser-API-Kompatibilitaetsanspruch.

Sieben kurze, kommentierte und selbstpruefende Skripte unter `/htdocs`, mit
8.3-kompatiblen Namen identisch im Repository und beiden Referenzimages:
Argumente/Konsole, Berechnungen/Arrays, JSON/Klassen, aufgefangene Fehler,
fehlende Ambient-Rechte, explizites Datei-Lesen und ASCII-Mandelbrot.
Der ausdrueckliche Zusatzauftrag erweitert die Datenliste um `mandel.js`,
ohne die bereits eingefrorenen fuenf Befehle oder Fristen zu lockern.
Ein fehlgeschlagener
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
bisherigen Assertions und 180s/1024MiB bleiben erhalten. Sieben Beispiele
zweimal aus der normalen Shell, exakte geordnete Resultate und Shell-Fortschritt;
Host-Negativtests lehnen fehlende, doppelte, falsche und fatale Belege ab.
Mandelbrot: genau 24 Zeilen zu 64 ASCII-Pixeln, hoechstens 48 Iterationen je
Pixel, zwei vollstaendige bytegleiche Bilder gegen eine unabhaengige Referenz.
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
js /htdocs/mandel.js
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

`mandel.js` berechnet die Mandelbrot-Menge als 64x24-ASCII-Bild. Die konstanten
Breite/Hoehe/Iterationsgrenze halten Laufzeit und Ausgabe klein. Es benoetigt
keine Dateifreigabe, GUI, Timer oder Farben.

## Zusatzauftrag: einfache Farben (noch offen)

Farbausgabe ist eine eigene Terminal-Ausgabegrenze, kein weiterer Testtext.
Der alte VGA-Pfad kennt einzelne ANSI-SGR-Farben, aber der Framebufferpfad
und ein einfaches Shell-/JS-Format sind damit nicht abgedeckt. Der JS-Runner
ersetzt ESC bisher bewusst durch `?`, um Terminal-Steuerinjektion zu verhindern.
Das Folgepaket muss einen kleinen standardbezogenen, validierten Farbteilumfang
mit einfacher Benutzung, Reset/Cleanup und echten VGA-/Framebuffer-Nachweisen
definieren. Kein ungefiltertes Durchlassen von Escape-Sequenzen und kein neuer
komplexer Parser in Ring 0. Dieser Auftrag bleibt vor der JS-Schreibdelegation
vorgemerkt; in R3.43 werden unveraenderte Programme und Schutzgrenzen verlangt.
