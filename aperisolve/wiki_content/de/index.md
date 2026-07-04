Title: Aperi'Solve Wiki - Steganographie-Werkzeuge & Anleitungen
Description: Dokumentation zu Aperi'Solve: Funktionsweise der Analyse, Anleitungen zu jedem Steganographie-Werkzeug (zsteg, steghide, binwalk, exiftool...) und ein CTF-Cheatsheet.
Order: 1

# Aperi'Solve Wiki

Willkommen im Aperi'Solve-Wiki. Aperi'Solve ist eine kostenlose Online-Plattform,
die Ebenenanalyse und Steganographie-Erkennung auf Bildern durchführt: Laden
Sie ein Bild auf der [Startseite](/de/) hoch, und alle Analysewerkzeuge laufen
automatisch.

Dieses Wiki dokumentiert, wie die Ergebnisse zu lesen sind und wie jedes
zugrunde liegende Werkzeug funktioniert, damit Sie die Analyse auf Ihrem
eigenen Rechner reproduzieren und erweitern können.

## Hier beginnen

- [Erste Schritte](/de/wiki/getting-started) — wie Sie Aperi'Solve verwenden
  und die Ergebnisse lesen.
- [Steganographie-CTF-Cheatsheet](/de/wiki/cheatsheet) — eine praktische
  Checkliste für Aufgaben rund um Bilder, Audio und Dateiformate.

## Werkzeug-Anleitungen

Jedes Analysewerkzeug, das auf Ihrem Upload läuft, hat eine eigene Seite: was
das Werkzeug tut, der genaue Befehl, den Aperi'Solve ausführt, wie die Ausgabe
zu interpretieren ist und wie Sie es lokal installieren.

- [Bit-Ebenen-Zerleger](/de/wiki/tools/decomposer) — jedes Bit jedes
  Farbkanals visualisieren.
- [Farbneuzuordnung](/de/wiki/tools/color_remapping) — verborgene Daten mit
  Paletten-Transformationen sichtbar machen.
- [zsteg](/de/wiki/tools/zsteg) — LSB-Steganographie-Erkennung für PNG und BMP.
- [steghide](/de/wiki/tools/steghide) — mit einer Passphrase in JPEG/BMP
  versteckte Daten extrahieren.
- [binwalk](/de/wiki/tools/binwalk) — im Bild eingebettete Dateien finden
  und extrahieren.
- [foremost](/de/wiki/tools/foremost) — eingebettete Dateien per Carving aus
  dem Bild herauslösen.
- [exiftool](/de/wiki/tools/exiftool) — Metadaten lesen (EXIF, XMP, IPTC...).
- [pngcheck](/de/wiki/tools/pngcheck) — die PNG-Struktur prüfen und
  beschädigte Chunks finden.
- [PCRT](/de/wiki/tools/pcrt) — beschädigte PNG-Dateien erkennen und
  reparieren.
- [OutGuess](/de/wiki/tools/outguess) — versteckte Daten aus JPEG-Bildern
  extrahieren.
- [jsteg](/de/wiki/tools/jsteg) — LSB-Daten aus JPEG-DCT-Koeffizienten
  extrahieren.
- [JPHide/JPSeek](/de/wiki/tools/jpseek) — JPHide-Payloads aus JPEG
  extrahieren.
- [OpenStego](/de/wiki/tools/openstego) — randomisierte LSB-Steganographie
  extrahieren.
- [identify](/de/wiki/tools/identify) — Bildeigenschaften mit ImageMagick
  untersuchen.
- [file](/de/wiki/tools/file) — den tatsächlichen Dateityp eines Uploads
  bestimmen.
- [strings](/de/wiki/tools/strings) — lesbaren Text in Bilddateien finden.

Beiträge sind willkommen auf
[GitHub](https://github.com/Zeecka/AperiSolve).

## Was ist Steganographie-Analyse?

Steganographie versteckt Daten in einer unauffälligen Trägerdatei — bei
Bildern bedeutet das die Manipulation von Pixel-Bits, Paletteneinträgen,
Metadatenfeldern oder der Dateistruktur selbst. Steganalyse ist die Praxis,
solche versteckten Daten aufzuspüren. Kein einzelnes Werkzeug deckt jede
Technik ab; deshalb führt Aperi'Solve eine ganze Batterie von
Analysewerkzeugen parallel aus und lässt Sie deren Ausgaben auf einen Blick
vergleichen.
