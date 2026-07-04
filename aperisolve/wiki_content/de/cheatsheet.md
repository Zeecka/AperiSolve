Title: Steganographie-CTF-Cheatsheet
Description: Steganographie-Cheatsheet für CTF-Spieler: PNG-, JPEG-, GIF- und Audiodateien mit file, exiftool, zsteg, steghide, binwalk, foremost und mehr untersuchen.
Order: 20

# Cheatsheet

## Haftungsausschluss

Dieses Cheatsheet soll CTF-Spielern bei ihrer Recherche als Leitfaden dienen. Es ist nicht repräsentativ für moderne Steganographie-/Steganalyse-Techniken, und sein Inhalt entspricht nicht dem, was eine interessante Challenge ausmacht 😉.

## Dateityp / Metadaten prüfen

- Recherchieren Sie die Dateiendung im Internet, wenn Sie sie nicht kennen. Prüfen Sie auch das Dateiformat.
- Prüfen Sie mit dem Befehl `file`, ob die Endung zum Dateityp passt. Dieser Befehl stützt sich auf die [Magic Bytes](https://en.wikipedia.org/wiki/List_of_file_signatures) am Anfang der Datei und kann daher falsch-positive Ergebnisse liefern.

```console
$ file data.raw
```

- Untersuchen Sie bei unbekannter Endung und Datei die hexadezimale Struktur der Datei mit einem Editor wie [hexed.it](https://hexed.it/), um die Dateistruktur zu identifizieren.
- Zeigen Sie die Metadaten der Datei mit dem Befehl `exiftool` an.

```console
$ exiftool data.raw
```

## Die Dateistruktur verändern {: #filestruct }

- Verändern Sie die Dateistruktur mit einem Hexadezimal-Editor wie [hexed.it](https://hexed.it/). PNG-Chunks lassen sich bequem mit [TweakPNG](http://entropymine.com/jason/tweakpng/) bearbeiten (Windows oder Wine).

![TweakPNG](/static/img/cheatsheet/tweakpng.png)

- Überprüfen Sie die Prüfsummen der Datei. Dabei handelt es sich in der Regel um CRC32; Werkzeuge wie [PngCheck](http://www.libpng.org/pub/png/apps/pngcheck.html) oder [PCRT](https://github.com/sherlly/PCRT) sind nützlich, um diese Prüfsummen zu überprüfen und zu korrigieren.

```console
$ pngcheck -c file.png
$ PCRT.py -v -i file.png
```

- Bei vielen Dateitypen (PNG, WAV, ...) ist die Mediengröße in den Headern enthalten. Diese Größe kann dann verkleinert werden, um nur einen Teil des Mediums anzuzeigen (Anfang eines Bildes, Anfang eines Tons, ...).

## Rohdaten {: #rawdata }

- Eine Rohdatei lässt sich in [Audacity](https://www.audacityteam.org/download/) importieren, um sie als Tonspur anzuhören (File > Import > Raw Data).

![Audacity](/static/img/cheatsheet/audacity_raw.png)

- Ebenso erlaubt das Werkzeug [GIMP](https://www.gimp.org/downloads/) den Bildimport aus Rohdaten (File > Open).
- Das Werkzeug [BinVis.io](http://binvis.io/) ermöglicht die grafische Darstellung von Binärdateien und kann Hinweise auf den Dateityp geben.
- Der Befehl `strings` zeigt die in einer Datei enthaltenen Zeichenketten an.

```console
$ strings -s file.raw
$ strings -S file.raw
$ strings -b file.raw
$ strings -l file.raw
$ strings -B file.raw
$ strings -L file.raw
```

## Bild {: #image }

|             | PNG | JPG/JPEG | BMP |
|-------------|-----|----------|-----|
| Aperi'Solve | OK  | OK       | OK  |
| Zsteg       | OK  | KO       | OK  |
| Steghide    | KO  | OK       | OK  |
| OutGuess    | KO  | OK       | KO  |

- Die Robustheit der Steganographie beruht auf dem verwendeten Algorithmus und der Kenntnis des Trägermediums. Eine Suche nach dem Originalmedium erlaubt einen Vergleich und die Identifizierung der vorgenommenen Veränderungen. Eine Rückwärtssuche auf [Google Image](https://images.google.com/) oder [Yandex Images](https://yandex.com/images/) kann das Originalmedium auffinden (achten Sie darauf, dass Dateigröße und Dateityp übereinstimmen).
- Das Werkzeug [Stegsolve](http://www.caesum.com/handbook/Stegsolve.jar) ermöglicht Operationen auf 2 Bildern und damit die Identifizierung der Unterschiede zwischen einem Trägermedium und einem Stegano-Medium mithilfe der XOR-Operation.

![Stegsolve Xor](/static/img/cheatsheet/stegsolve_xor.png)
![Stegsolve Xor 2](/static/img/cheatsheet/stegsolve_xor2.png)

- Das Werkzeug [Zsteg](https://github.com/zed-0xff/zsteg) ermöglicht das Extrahieren von Nachrichten und Binärdaten, die auf verschiedenen Ebenen codiert sind, etwa auf den 2 grünen LSBs.

```console
$ zsteg file.png 2b,g,lsb,xy
$ zsteg file.png -E '1b,rgb,lsb'
```

- Manchmal kann die Bit-Ebenen-Analyse mit dem Werkzeug [Stegsolve](http://www.caesum.com/handbook/Stegsolve.jar) (oder Aperi'Solve) bestimmte veränderte Bereiche hervorheben. Zum Extrahieren bestimmter Bereiche kann dann Scripting erforderlich sein. Der folgende Python-Code liest ein Bild als Liste von Pixeln ein: [(100,120,43), (230, 124, 110), ...]

```python
# pip install Pillow
from PIL import Image
stegano_image = Image.open('file.png')
width, height = stegano_image.size
pxs = list(stegano_image.getdata())
print(pxs[:10])
```

- Stegano-Medien können auf einem Algorithmus mit Verschlüsselungsschlüssel beruhen. Das ist bei [Steghide](http://steghide.sourceforge.net/) und [OutGuess](https://github.com/resurrecting-open-source-projects/outguess) der Fall. Das Passwort kann der Dateiname sein, eine in der Datei enthaltene Zeichenkette (`strings` & `exiftool`) oder das auf dem Bild dargestellte Objekt. In manchen Fällen lässt sich das Passwort nicht ermitteln, und es muss ein Bruteforce durchgeführt werden. Die Werkzeuge [StegCracker](https://github.com/Paradoxis/StegCracker) und [Stegbrute](https://github.com/R4yGM/stegbrute) ermöglichen das Bruteforcen von mit [Steghide](http://steghide.sourceforge.net/) versteckten Geheimnissen.

```console
$ steghide extract -p "secret" -sf file.jpg
$ stegcracker file.jpg /usr/share/wordlists/rockyou.txt
```

## PNG (Portable Network Graphics) {: #png }

- Werkzeuge wie [Steghide](http://steghide.sourceforge.net/) und [OutGuess](https://github.com/resurrecting-open-source-projects/outguess) funktionieren nicht bei PNG-Dateien. Andererseits erlaubt dieser Dateityp eine Speicherung ohne Kompression und damit das Verstecken von Nachrichten in den LSBs. Das oben vorgestellte und auf Aperi'Solve verfügbare Werkzeug [Zsteg](https://github.com/zed-0xff/zsteg) ermöglicht das Extrahieren von Geheimnissen aus PNG-Dateien.

```console
$ zsteg file.png 2b,g,lsb,xy
$ zsteg file.png -E '1b,rgb,lsb'
```

- PNG bietet mit ["APNG"](https://en.wikipedia.org/wiki/APNG) eine Erweiterung, die wie bei GIF-Dateien eine Bildanimation erlaubt. Es ist möglich, dass die Darstellung des PNG nicht dessen gesamten Inhalt wiedergibt (zum Beispiel ein Frame mit einer Dauer von null oder ein sehr langer erster Frame). Mit dem Werkzeug [APNG Maker](https://ezgif.com/apng-maker) lassen sich die einzelnen Frames einer APNG-Datei betrachten. Eine Nachricht kann auch über die Dauer der einzelnen Frames codiert sein.

![APNG](https://upload.wikimedia.org/wikipedia/commons/1/14/Animated_PNG_example_bouncing_beach_ball.png)

- Das zuvor vorgestellte Werkzeug [TweakPNG](http://entropymine.com/jason/tweakpng/) erlaubt mehrere Arten von Operationen, etwa Prüfsummen neu berechnen, PNG-Chunks umordnen, die sichtbare Größe des PNG vergrößern oder einen Header verändern.

![TweakPNG](/static/img/cheatsheet/tweakpng.png)

## JPEG (Joint Photographic Experts Group) {: #jpg }

- Das Werkzeug [Zsteg](https://github.com/zed-0xff/zsteg) funktioniert nicht bei JPEG-Dateien (jpg, jpeg, ...), da diese zwingend einen Kompressionsalgorithmus enthalten, der die Bildqualität reduziert und die LSBs verändert. Die oben gezeigten Werkzeuge [Steghide](http://steghide.sourceforge.net/) und [OutGuess](https://github.com/resurrecting-open-source-projects/outguess) sind dagegen mit diesem Dateiformat kompatibel.

```console
$ outguess -k secret file.jpg output.raw
$ steghide extract -p "secret" -sf file.jpg
```

## GIF (Graphics Interchange Format) {: #gif }

- GIFs sind in der Regel animierte Bilder, deren Format von Steganalyse-Werkzeugen meist schlecht unterstützt wird. Zudem bietet das Bildformat üblicherweise eine Farbpalette von höchstens 256 Farben, gegenüber 16 Millionen bei PNG (ohne Transparenz). Das Werkzeug [GIF Maker](https://ezgif.com/maker) erleichtert jedoch die Bearbeitung von GIF-Dateien.
- GIFs können Bilder (Frames) mit einer Dauer von null einbetten. Diese sind dann ohne eine Analyse jedes einzelnen Frames nicht sichtbar.

![GIF Maker](/static/img/cheatsheet/gif_maker.png)

- Eine versteckte Nachricht kann über die Dauer der Frames eingebettet sein (Morse, ASCII, binär, ...).
- [Ffmpeg](https://ffmpeg.org/) kann verwendet werden, um Frames aus einem GIF zu extrahieren. Die Vollständigkeit der extrahierten Frames kann nicht garantiert werden.

```console
$ ffmpeg -i file.gif -vsync 0 output/file%d.png
```

## Audio {: #audio }

- Die häufigste Technik bei Audiodateien beruht auf dem Audiospektrum. Tatsächlich ist es möglich, mit Werkzeugen wie [Coagula](https://www.abc.se/~re/Coagula/Coagula.html) eine sichtbare Nachricht auf das Audiospektrum zu zeichnen. Dieses Spektrum kann anschließend mit Spektralanalyse-Werkzeugen wie [Sonic Visualiser](https://www.sonicvisualiser.org/), [Audacity](https://www.audacityteam.org/) oder dem Online-Werkzeug [dcode](https://www.dcode.fr/spectral-analysis) analysiert werden.

![Audacity-Spektrum](/static/img/cheatsheet/audacity_1.png)

Ein Rechtsklick auf die Skala, um herauszuzoomen und das gesamte Spektrum zu sehen, oder ein Wechsel in den Logarithmus-Modus kann erforderlich sein.

![Audacity-Spektrum](/static/img/cheatsheet/audacity_2.png)

- Unhörbare Frequenzen können zum Verstecken von Nachrichten genutzt werden. Eine Spektralanalyse oberhalb von 20KHz und unterhalb von 20Hz ist empfehlenswert; dort kann eine in Morse oder binär codierte Nachricht versteckt sein.
- Töne sind einfache Telekommunikationssignale, die auch für andere Zwecke genutzt werden können. Es können spezielle Codierungsverfahren zum Einsatz kommen, etwa der früher in der Telefonie verwendete [DTMF-Code](https://en.wikipedia.org/wiki/Dual-tone_multi-frequency_signaling) oder das im Fernsehen für die Bildübertragung genutzte [SSTV](https://en.wikipedia.org/wiki/Slow-scan_television). Diese Signale sind auf hörbaren Frequenzen codiert, ihre Interpretation erfordert jedoch spezielle Decoder. Für die erste Technik greift man zu einem [DTMF-Decoder](http://dialabc.com/sound/detect/), für die zweite zu einem SSTV-Decoder wie [QSSTV](https://doc.ubuntu-fr.org/qsstv).
- Wie PNG-Dateien betten auch manche Audiodateien ihre theoretische Größe in ihre Header ein. Das gilt insbesondere für [WAV-Dateien](https://fr.wikipedia.org/wiki/Waveform_Audio_File_Format#En-t%C3%AAte_de_fichier_WAV), deren DataSize-Block mit einem Hex-Editor verkleinert oder vergrößert werden kann.
- Die LSB-Technik kann bei bestimmten Audiodateien eingesetzt werden. Dazu müssen die LSBs aus den Audiodaten extrahiert werden; das Werkzeug [WavSteg](https://github.com/ragibson/Steganography#WavSteg) ermöglicht diese Manipulation bei WAV-Dateien.

```console
$ stegolsb wavsteg -r -i file.wav -o output.txt -n 1 -b 1000
```

- Die Werkzeuge [Steghide](http://steghide.sourceforge.net/) und [DeepSound](http://jpinsoft.net/deepsound/overview.aspx) werden in CTFs häufig zum Verstecken von Nachrichten verwendet. Sie können einen Schlüssel als Parameter erhalten; diesen Schlüssel müssen Sie dann aus den verfügbaren Informationen erraten (Medium, Dateiname, Challenge-Name usw.) oder mithilfe einer Wortliste ermitteln.

![DeepSound](/static/img/cheatsheet/DeepSound.png)

## Polyglott-Dateien {: #polyglot }

Dies ist ein Dateityp, der für verschiedene Dateiformate gültig ist. Zum Beispiel eine Bilddatei, die sich betrachten lässt und zugleich eine jar-Datei ist (die ausgeführt werden kann). Es gibt mehrere Arten von Polyglott-Dateien:

- "Einfacher" Polyglott: eine simple Aneinanderreihung von Dateien;
- "Parasitärer" Polyglott: eine Datei, die eine Datei eines anderen Typs enthält.
- "Mille-feuilles"-Polyglott: Die Schichten wechseln sich ab, indem die interne Struktur der Datei gezielt kontrolliert wird.
- "Chimären"-Polyglott: Die Datei hat einen Körper (Daten) und mehrere Köpfe. Da mehrere Formate denselben Algorithmus zum Speichern von Daten verwenden, etwa Deflate von Zlib, wird derselbe Datenblock von verschiedenen Headern genutzt (zum Beispiel die Pixel eines Bildes). Mehrere Header sind vorhanden, sodass dieses Bild innerhalb derselben Datei über mehrere Formate (jpg, png, ...) sichtbar ist.
- "Schizophrene" Dateien: Es handelt sich um einen einzigen Dateityp, dessen Inhalt jedoch je nach dem Werkzeug, das diese Datei ausführt oder öffnet, unterschiedlich interpretiert wird. Meist sind das PDF-Dateien (Interpretation von JavaScript oder nicht) oder Bilder (wie die Technik von [Gamma](https://carlmastrangelo.com/blog/gamma-steganography)).
- Angecryption: Das Ergebnis der Ver- oder Entschlüsselung einer Datei ergibt eine andere gültige Datei desselben oder eines anderen Typs:

![Angecryption](/static/img/cheatsheet/Angecryption.png)

- Docx-, jar-, apk-, pptx-, odf-... Dateien sind gültige Archive und können entpackt werden. Sie müssen dann prüfen, ob sich die betreffende Datei mit einem anderen Werkzeug als dem zu ihrer Endung gehörenden öffnen lässt. Der Befehl `file` erkennt Polyglott-Dateien nicht.

## Codierungen und exotische Sprachen {: #text }

- ASCII-Text kann binär in Blöcken von `8 bits` codiert werden; er ist dann leicht zu erkennen, da jeder Block, der einem Buchstaben entspricht, mit einer 0 beginnt. Diese 0 kann entfernt werden, die Blöcke sind dann nur noch `7 bits` lang. Der Text kann auch als Ganzzahl vom Typ `long` codiert sein (manchmal in einer anderen Basis als Basis 10). Zum Beispiel kann die Zeichenkette „Hello world!“, codiert als long-Typ in Basis 10, mit dem folgenden Python-2-Code decodiert werden:

```console
python2> hex(22405534230753963835153736737L)[2:].strip('L').decode("hex")
python2> "48656c6c6f20776f726c6421".decode("hex")
```

- Werkzeuge wie [CyberChef](https://gchq.github.io/CyberChef/) (und die Option "magic") können helfen, die verwendete Codierung zu erkennen und die versteckte Nachricht zu decodieren. Manchmal kann ein Zeichensatzwechsel erforderlich sein (monoalphabetische Substitution oder Basiswechsel).
- Exotische oder esoterische Sprachen sind Programmiersprachen, die einzigartig, schwer zu programmieren oder schlicht seltsam sein sollen. Ihr Design und ihre Zeichensätze können eigenwillig sein; das gilt für die in CTFs am häufigsten anzutreffenden Sprachen wie [BrainFuck](https://esolangs.org/wiki/Brainfuck), [WhiteSpace](https://esolangs.org/wiki/Whitespace), [PIET](https://esolangs.org/wiki/Piet) oder [Malbolge](https://esolangs.org/wiki/Malbolge). Die Website [EsoLang](https://esolangs.org/wiki/Language_list) führt diese verschiedenen Sprachen auf und kann bei Ihrer Recherche hilfreich sein.

```console
brainfuck>
++++++++++[>+>+++>+++++++>++++++++++<<<<-]>>>++.>+.+++++++..+++.<<++.>>++++++++.--------.+++.------.--------.<<+.

malbolge>
('&%:9]!~}|z2Vxwv-,POqponl$Hjig%eB@@>}=<M:9wv6WsU2T|nm-,jcL(I&%$#"
`CB]V?Tx<uVtT`Rpo3NlF.Jh++FdbCBA@?]!~|4XzyTT43Qsqq(Lnmkj"Fhg${z@>
```

[![PIET](/static/img/cheatsheet/piet.png)](https://esolangs.org/wiki/Piet)

## Zum Weitermachen {: #more }

- [Blog von Aperi'Kube - Kategorie Steganographie](https://www.aperikube.fr/cat/steg/)
- [CTF Time - Writeups (Stegano)](https://ctftime.org/writeups)
- [Corkami](http://corkami.github.io/)
- [Root-Me - Steganographie](https://www.root-me.org/en/Challenges/Steganography/)
- [Stereogramm](https://en.wikipedia.org/wiki/Autostereogram)
