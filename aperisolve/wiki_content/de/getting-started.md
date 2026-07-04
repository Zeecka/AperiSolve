Title: Erste Schritte mit Aperi'Solve
Description: Wie Sie ein Bild auf Aperi'Solve hochladen, Passwörter und Tiefenanalyse verwenden und die Ergebnisse der einzelnen Analysewerkzeuge interpretieren.
Order: 10

# Erste Schritte

## Ein Bild hochladen

Öffnen Sie die [Startseite](/de/) und legen Sie ein Bild ab (PNG, JPG, JPEG,
GIF, BMP, WebP oder TIFF). Zwei optionale Einstellungen beeinflussen, was
ausgeführt wird:

- **Passwort** — wird an die passwortfähigen Analysewerkzeuge weitergereicht
  ([steghide](/de/wiki/tools/steghide), openstego, jpseek, outguess). Lassen
  Sie das Feld leer, wenn Sie keine mögliche Passphrase haben; die Werkzeuge
  laufen dann mit leerem Passwort, was eine gängige CTF-Konfiguration ist.
- **Tiefenanalyse** — führt zusätzlich langsamere Analysewerkzeuge wie
  outguess aus.

Die Analyse ist in der Regel innerhalb von Sekunden abgeschlossen; große
Bilder oder eine ausgelastete Warteschlange können länger dauern. Die URL der
Ergebnisseite ist stabil und teilbar: Dasselbe Bild, mit denselben Optionen
eingereicht, liefert sofort dieselbe Seite.

## Die Ergebnisse lesen

Die Ergebnisse sind pro Analysewerkzeug gruppiert, stets in derselben
Reihenfolge:

1. **Bit-Ebenen und Farbneuzuordnung** kommen zuerst, weil sie visuell sind:
   Durchsuchen Sie die erzeugten Bilder nach Umrissen, Text oder QR-Codes,
   die nur in einer einzelnen Bit-Ebene erscheinen.
2. **Datei- und Metadaten-Werkzeuge** (`file`, `exiftool`, `identify`)
   decken nicht übereinstimmende Formate, versteckte Kommentare und
   Bearbeitungsspuren auf.
3. **Carving-Werkzeuge** (`binwalk`, `foremost`) listen Dateien auf, die im
   Bild eingebettet sind; wird etwas gefunden, stellt ein Download-Button
   eine `.7z`-Datei mit den extrahierten Dateien bereit.
4. **Steganographie-Extraktoren** (`zsteg`, `steghide`, `jpseek`, `jsteg`,
   `openstego`, `outguess`) versuchen die eigentliche Extraktion der
   Nutzdaten. Ein roter Block ist normal: Er bedeutet lediglich, dass das
   Werkzeug mit dem angegebenen Passwort nichts gefunden hat.

## Datenschutz und Aufbewahrung

Uploads werden vorübergehend gespeichert (standardmäßig 3 Tage), damit
Ergebnisse geteilt werden können, und anschließend automatisch gelöscht.
Wenn Sie ein Bild versehentlich hochgeladen haben, können Sie es nach einer
kurzen Wartezeit selbst über die Ergebnisseite entfernen, sofern es
ausschließlich von Ihrer eigenen IP-Adresse hochgeladen wurde.

## Weiterführendes

Arbeiten Sie das [Cheatsheet](/de/wiki/cheatsheet) für Techniken durch, die
kein automatisiertes Werkzeug abdeckt, und lesen Sie die Seiten der einzelnen
Werkzeuge, um dieselbe Analyse lokal auf Dateien anzuwenden, die Aperi'Solve
nicht unterstützt.
