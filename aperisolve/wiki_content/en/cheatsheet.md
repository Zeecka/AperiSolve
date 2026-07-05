Title: Steganography CTF Cheatsheet
Description: Steganography cheatsheet for CTF players: inspect PNG, JPEG, GIF and audio files with file, exiftool, zsteg, steghide, binwalk, foremost and more.
Order: 20

# Cheatsheet

## Disclaimer

This cheatsheet is intended to guide CTF players in their research. This cheatsheet is not representative of modern steganography/steganalysis techniques, and its content does not match with the creation of an interesting challenge 😉.

## Check file type / metadata

- Check the file extension on the internet if you don't know it. Also check the file format.
- Use the `file` command to check that the extension matches the file type. This command is based on the [Magic Bytes](https://en.wikipedia.org/wiki/List_of_file_signatures) at the beginning of the file, so it may return false positives.

```console
$ file data.raw
```

- In case of unknown extension and file, inspect the hexadecimal structure of the file with an editor like [hexed.it](https://hexed.it/) to identify the file structure.
- Display the file's metadata with the `exiftool` command.

```console
$ exiftool data.raw
```

## Modify the file structure {: #filestruct }

- Modify the file structure with a hexadecimal editor like [hexed.it](https://hexed.it/). PNG chunks can be easily edited with [TweakPNG](http://entropymine.com/jason/tweakpng/) (Windows or Wine).

![TweakPNG](/static/img/cheatsheet/tweakpng.png)

- Verify the checksums of the file. These are usually CRC32, some tools like [PngCheck](http://www.libpng.org/pub/png/apps/pngcheck.html) or [PCRT](https://github.com/sherlly/PCRT) are useful to verify and correct these checksums.

```console
$ pngcheck -c file.png
$ PCRT.py -v -i file.png
```

- For many types of files (PNG, WAV, ...) the media size is contained in the headers. This size can then be reduced to display only a part of the media (beginning of an image, beginning of a sound, ...).

## Raw data {: #rawdata }

- It is possible to import a raw file into [Audacity](https://www.audacityteam.org/download/) to listen to it as a soundtrack (File > Import > Raw Data).

![Audacity](/static/img/cheatsheet/audacity_raw.png)

- Similarly, the [GIMP](https://www.gimp.org/downloads/) tool allows image import from raw data (File > Open).
- The [BinVis.io](http://binvis.io/) tool allows you to graphically view binary files and can give hints as to the file type.
- The `strings` command allows you to display the strings present in a file.

```console
$ strings -s file.raw
$ strings -S file.raw
$ strings -b file.raw
$ strings -l file.raw
$ strings -B file.raw
$ strings -L file.raw
```

## Image {: #image }

|             | PNG | JPG/JPEG | BMP |
|-------------|-----|----------|-----|
| Aperi'Solve | OK  | OK       | OK  |
| Zsteg       | OK  | KO       | OK  |
| Steghide    | KO  | OK       | OK  |
| OutGuess    | KO  | OK       | KO  |

- The robustness of steganography relies on the algorithm used and the knowledge of the cover medium. A search of the original media allows us to make a comparison and identify the alterations made. A reverse search on [Google Image](https://images.google.com/) or [Yandex Images](https://yandex.com/images/) can find the original media (be sure to check that the file size and type match).
- The [Stegsolve](http://www.caesum.com/handbook/Stegsolve.jar) tool allows you to perform operations on 2 images, and thus identify the differences between a cover medium and a stegano medium using the XOR operation.

![Stegsolve Xor](/static/img/cheatsheet/stegsolve_xor.png)
![Stegsolve Xor 2](/static/img/cheatsheet/stegsolve_xor2.png)

- The [Zsteg](https://github.com/zed-0xff/zsteg) tool allows you to extract messages and binaries encoded on different layers, such as the 2 green LSB.

```console
$ zsteg file.png 2b,g,lsb,xy
$ zsteg file.png -E '1b,rgb,lsb'
```

- Sometimes, bit-layer analysis on the [Stegsolve](http://www.caesum.com/handbook/Stegsolve.jar) tool (or Aperi'Solve) can highlight specific areas that have been altered. Scripting may then be required to extract specific areas. The following python code retrieves an image as a list of pixels: [(100,120,43), (230, 124, 110), ...]

```python
# pip install Pillow
from PIL import Image
stegano_image = Image.open('file.png')
width, height = stegano_image.size
pxs = list(stegano_image.getdata())
print(pxs[:10])
```

- Stegano mediums can rely on an algorithm using an encryption key. This is the case for [Steghide](http://steghide.sourceforge.net/) and [OutGuess](https://github.com/resurrecting-open-source-projects/outguess). The password can be the name of the file, a string of characters contained in the file (`strings` & `exiftool`), or the object represented by the image. In some cases, the password cannot be retrieved and a bruteforce must be performed. The tool [StegCracker](https://github.com/Paradoxis/StegCracker) and [Stegbrute](https://github.com/R4yGM/stegbrute) allows bruteforce of hidden secrets with [Steghide](http://steghide.sourceforge.net/).

```console
$ steghide extract -p "secret" -sf file.jpg
$ stegcracker file.jpg /usr/share/wordlists/rockyou.txt
```

## PNG (Portable Network Graphics) {: #png }

- Tools like [Steghide](http://steghide.sourceforge.net/) and [OutGuess](https://github.com/resurrecting-open-source-projects/outguess) does not work for PNG files. On the other hand, this type of file allows a backup without compression, and therefore to hide messages on the LSBs. The tool [Zsteg](https://github.com/zed-0xff/zsteg) presented above and available on Aperi'Solve allows the extracting secrets from PNG files.

```console
$ zsteg file.png 2b,g,lsb,xy
$ zsteg file.png -E '1b,rgb,lsb'
```

- PNG offers an ["APNG"](https://en.wikipedia.org/wiki/APNG) extension allowing to have an animation of images like GIF files. It is possible that the visualization of the PNG does not reflect all of its content (for example, a frame with a zero duration, or a very long first frame). The tool [APNG Maker](https://ezgif.com/apng-maker) allows you to view the different frames of an APNG file. A message can also be encoded on the durations of each frame.

![APNG](https://upload.wikimedia.org/wikipedia/commons/1/14/Animated_PNG_example_bouncing_beach_ball.png)

- The tool [TweakPNG](http://entropymine.com/jason/tweakpng/) presented earlier allows to perform several types of operations like recalculate checksums, reorder PNG chunks, increase the visible size of the PNG or modify a header.

![TweakPNG](/static/img/cheatsheet/tweakpng.png)

## JPEG (Joint Photographic Experts Group) {: #jpg }

- The tool [Zsteg](https://github.com/zed-0xff/zsteg) does not work on JPEG files (jpg, jpeg, ...) because the latter necessarily include a compression algorithm reducing the quality of the image and altering the LSBs. In contrast, the tools [Steghide](http://steghide.sourceforge.net/) and [OutGuess](https://github.com/resurrecting-open-source-projects/outguess) shown above are compatible with this file format.

```console
$ outguess -k secret file.jpg output.raw
$ steghide extract -p "secret" -sf file.jpg
```

## GIF (Graphics Interchange Format) {: #gif }

- GIFs are generally animated images whose format is generally poorly supported by steganalysis tools. In addition, the image format generally offers a color palette not exceeding 256 colors, against 16 million for PNG (excluding transparency). However, the tool [GIF Maker](https://ezgif.com/maker) makes it easy to manipulate GIF files.
- GIFs can embed images (frames) with zero duration. These will then not be viewable without an analysis of each frame.

![GIF Maker](/static/img/cheatsheet/gif_maker.png)

- A hidden message can be embedded over the duration of the frames (morse, ascii, binary, ...).
- [Ffmpeg](https://ffmpeg.org/) can be used to extract frames from a GIF. Completeness of extracted frames cannot be guaranteed.

```console
$ ffmpeg -i file.gif -vsync 0 output/file%d.png
```

## Audio {: #audio }

- The most common technique for sound files is based on the audio spectrum. Indeed, it is possible to draw a visible message on the audio spectrum with tools like [Coagula](https://www.abc.se/~re/Coagula/Coagula.html). Then this spectrum can be analyzed using spectral analysis tools like [Sonic Visualiser](https://www.sonicvisualiser.org/), [Audacity](https://www.audacityteam.org/) or the online tool [dcode](https://www.dcode.fr/spectral-analysis).

![Audacity spectrum](/static/img/cheatsheet/audacity_1.png)

Right-clicking the scale to zoom out and view the entire spectrum, or switch to logarithm mode, may be required.

![Audacity spectrum](/static/img/cheatsheet/audacity_2.png)

- Inaudible frequencies can be used to hide messages. A spectral analysis beyond 20KHz and below 20Hz is recommended, a message encoded in morse or binary can be hidden there.
- Sounds are simple telecommunications signals that can be used for other purposes. Special encoding methods can be used, such as [DTMF Code](https://en.wikipedia.org/wiki/Dual-tone_multi-frequency_signaling) formerly used in telephony or [SSTV](https://en.wikipedia.org/wiki/Slow-scan_television) used in television for image transfer. These signals are encoded on audible frequencies but their interpretations require special decoders. We will then opt for a [DTMF decoder](http://dialabc.com/sound/detect/) for the first technique, and an SSTV decoder like [QSSTV](https://doc.ubuntu-fr.org/qsstv) for the second one.
- Just like PNG files, some sound files embed their theoretical sizes in their headers. This is particularly the case for [WAV files](https://fr.wikipedia.org/wiki/Waveform_Audio_File_Format#En-t%C3%AAte_de_fichier_WAV) whose DataSize block can be decreased or increased using a hex editor.
- The LSB technique can be used on certain audio files. It is then necessary to extract the LSBs from the audio data; the [WavSteg](https://github.com/ragibson/Steganography#WavSteg) tool allows you to perform this manipulation on WAV files.

```console
$ stegolsb wavsteg -r -i file.wav -o output.txt -n 1 -b 1000
```

- The tools [Steghide](http://steghide.sourceforge.net/) and [DeepSound](http://jpinsoft.net/deepsound/overview.aspx) are commonly used in CTF to hide messages. These can take a key as a parameter, so you will have to guess this key from the available information (media, file name, challenge name, etc.) or by using a wordlist.

![DeepSound](/static/img/cheatsheet/DeepSound.png)

## Polyglot Files {: #polyglot }

This is a file type that is valid for different file formats. For example an image file which can therefore be viewed and which is also a jar file (which can be executed). There are several types of polyglot file types:

- "Simple" polyglot: This is a simple concatenation of files;
- "Parasitic" polyglot: This is a file that contains another type of file.
- "Mille-feuilles" polyglot: The layers are alternated by controlling the internal structure of the file.
- "Chimera" polyglot: The file has a body (data) and several heads. Since several formats use the same algorithm to store data, such as Zlib's Deflate, the same block of data is used by different headers. (for example, the pixels of an image). Several headers are present so that this image is visible via several formats (jpg, png, ..), within the same file.
- "Schizophrenic" files: This is a single type of file, but its contents are interpreted differently depending on the tool that is running or accessing this file. These are usually PDF files (interpretation or not of javascript) or Images (like the technique of [Gamma](https://carlmastrangelo.com/blog/gamma-steganography)).
- Angecryption : The result of an encryption or decryption of a file gives another valid file of the same type or of a different type:

![Angecryption](/static/img/cheatsheet/Angecryption.png)

- Docx, jar, apk, pptx, odf... files are valid archives and can be decompressed. You must then check whether the file in question can be opened with a tool other than the one associated with its extension. The `file` command does not identify polyglot files.

## Encoding and exotic languages {: #text }

- ASCII text can be encoded in binary in blocks of `8 bits`, it is then easily identifiable because each block corresponding to a letter begins with a 0. It is possible to remove this 0 , the blocks are then only `7 bits`. The text can also be coded on an integer of type `long` (sometimes in a base other than base 10), for example the character string “Hello world! encoded on a long type in base 10 can be decoded with the following python 2 code:

```console
python2> hex(22405534230753963835153736737L)[2:].strip('L').decode("hex")
python2> "48656c6c6f20776f726c6421".decode("hex")
```

- Tools like [CyberChef](https://gchq.github.io/CyberChef/) (and the "magic" option) can help detect the encoding used and decode the hidden message. Sometimes a charset change may be necessary (monoalphabetic substitution, or base change).
- Exotic or esoteric languages are programming languages designed to be unique, difficult to program, or just plain weird. Their design and their charsets can be particular, it is the case of the most found languages in CTF like [BrainFuck](https://esolangs.org/wiki/Brainfuck), [WhiteSpace](https://esolangs.org/wiki/Whitespace), [PIET](https://esolangs.org/wiki/Piet) or [Malbolge](https://esolangs.org/wiki/Malbolge). The website [EsoLang](https://esolangs.org/wiki/Language_list) references these different languages and can be useful in your research.

```console
brainfuck>
++++++++++[>+>+++>+++++++>++++++++++<<<<-]>>>++.>+.+++++++..+++.<<++.>>++++++++.--------.+++.------.--------.<<+.

malbolge>
('&%:9]!~}|z2Vxwv-,POqponl$Hjig%eB@@>}=<M:9wv6WsU2T|nm-,jcL(I&%$#"
`CB]V?Tx<uVtT`Rpo3NlF.Jh++FdbCBA@?]!~|4XzyTT43Qsqq(Lnmkj"Fhg${z@>
```

[![PIET](/static/img/cheatsheet/piet.png)](https://esolangs.org/wiki/Piet)

## To go further {: #more }

- [Aperi'Kube's Blog - Stéganography category](https://www.aperikube.fr/cat/steg/)
- [CTF Time - Writeups (Stegano)](https://ctftime.org/writeups)
- [Corkami](http://corkami.github.io/)
- [Root-Me - Steganography](https://www.root-me.org/en/Challenges/Steganography/)
- [Stereogram](https://en.wikipedia.org/wiki/Autostereogram)
