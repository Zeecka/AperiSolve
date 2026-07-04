Title: Cheatsheet de esteganografía para CTF
Description: Cheatsheet de esteganografía para jugadores de CTF: inspeccione archivos PNG, JPEG, GIF y de audio con file, exiftool, zsteg, steghide, binwalk, foremost y más.
Order: 20

# Cheatsheet

## Aviso

Esta cheatsheet está pensada para orientar a los jugadores de CTF en sus investigaciones. No es representativa de las técnicas modernas de esteganografía/estegoanálisis, y su contenido no se corresponde con la creación de un reto interesante 😉.

## Comprobar el tipo de archivo / los metadatos

- Busque la extensión del archivo en internet si no la conoce. Compruebe también el formato del archivo.
- Use el comando `file` para comprobar que la extensión coincide con el tipo de archivo. Este comando se basa en los [Magic Bytes](https://en.wikipedia.org/wiki/List_of_file_signatures) del comienzo del archivo, por lo que puede devolver falsos positivos.

```console
$ file data.raw
```

- Si la extensión y el archivo son desconocidos, inspeccione la estructura hexadecimal del archivo con un editor como [hexed.it](https://hexed.it/) para identificar la estructura del archivo.
- Muestre los metadatos del archivo con el comando `exiftool`.

```console
$ exiftool data.raw
```

## Modificar la estructura del archivo {: #filestruct }

- Modifique la estructura del archivo con un editor hexadecimal como [hexed.it](https://hexed.it/). Los chunks PNG se pueden editar fácilmente con [TweakPNG](http://entropymine.com/jason/tweakpng/) (Windows o Wine).

![TweakPNG](/static/img/cheatsheet/tweakpng.png)

- Verifique las sumas de comprobación del archivo. Suelen ser CRC32; algunas herramientas como [PngCheck](http://www.libpng.org/pub/png/apps/pngcheck.html) o [PCRT](https://github.com/sherlly/PCRT) resultan útiles para verificar y corregir estas sumas de comprobación.

```console
$ pngcheck -c file.png
$ PCRT.py -v -i file.png
```

- En muchos tipos de archivos (PNG, WAV, ...) el tamaño del medio está contenido en las cabeceras. Ese tamaño puede reducirse para mostrar solo una parte del medio (el comienzo de una imagen, el comienzo de un sonido, ...).

## Datos en bruto {: #rawdata }

- Es posible importar un archivo en bruto en [Audacity](https://www.audacityteam.org/download/) para escucharlo como pista de audio (File > Import > Raw Data).

![Audacity](/static/img/cheatsheet/audacity_raw.png)

- Del mismo modo, la herramienta [GIMP](https://www.gimp.org/downloads/) permite importar imágenes a partir de datos en bruto (File > Open).
- La herramienta [BinVis.io](http://binvis.io/) permite visualizar gráficamente archivos binarios y puede dar pistas sobre el tipo de archivo.
- El comando `strings` permite mostrar las cadenas de caracteres presentes en un archivo.

```console
$ strings -s file.raw
$ strings -S file.raw
$ strings -b file.raw
$ strings -l file.raw
$ strings -B file.raw
$ strings -L file.raw
```

## Imagen {: #image }

|             | PNG | JPG/JPEG | BMP |
|-------------|-----|----------|-----|
| Aperi'Solve | OK  | OK       | OK  |
| Zsteg       | OK  | KO       | OK  |
| Steghide    | KO  | OK       | OK  |
| OutGuess    | KO  | OK       | KO  |

- La robustez de la esteganografía depende del algoritmo utilizado y del conocimiento del medio portador. Buscar el medio original permite hacer una comparación e identificar las alteraciones realizadas. Una búsqueda inversa en [Google Image](https://images.google.com/) o [Yandex Images](https://yandex.com/images/) puede encontrar el medio original (asegúrese de comprobar que el tamaño y el tipo de archivo coinciden).
- La herramienta [Stegsolve](http://www.caesum.com/handbook/Stegsolve.jar) permite realizar operaciones entre 2 imágenes, y así identificar las diferencias entre un medio portador y un medio esteganografiado mediante la operación XOR.

![Stegsolve Xor](/static/img/cheatsheet/stegsolve_xor.png)
![Stegsolve Xor 2](/static/img/cheatsheet/stegsolve_xor2.png)

- La herramienta [Zsteg](https://github.com/zed-0xff/zsteg) permite extraer mensajes y binarios codificados en distintas capas, como los 2 LSB del canal verde.

```console
$ zsteg file.png 2b,g,lsb,xy
$ zsteg file.png -E '1b,rgb,lsb'
```

- A veces, el análisis por capas de bits con la herramienta [Stegsolve](http://www.caesum.com/handbook/Stegsolve.jar) (o Aperi'Solve) puede resaltar zonas concretas que han sido alteradas. Puede ser necesario entonces recurrir a scripts para extraer zonas específicas. El siguiente código en python recupera una imagen como una lista de píxeles: [(100,120,43), (230, 124, 110), ...]

```python
# pip install Pillow
from PIL import Image
stegano_image = Image.open('file.png')
width, height = stegano_image.size
pxs = list(stegano_image.getdata())
print(pxs[:10])
```

- Los medios esteganografiados pueden basarse en un algoritmo que utiliza una clave de cifrado. Es el caso de [Steghide](http://steghide.sourceforge.net/) y [OutGuess](https://github.com/resurrecting-open-source-projects/outguess). La contraseña puede ser el nombre del archivo, una cadena de caracteres contenida en el archivo (`strings` y `exiftool`) o el objeto representado por la imagen. En algunos casos la contraseña no puede recuperarse y hay que realizar un ataque de fuerza bruta. Las herramientas [StegCracker](https://github.com/Paradoxis/StegCracker) y [Stegbrute](https://github.com/R4yGM/stegbrute) permiten aplicar fuerza bruta a los secretos ocultos con [Steghide](http://steghide.sourceforge.net/).

```console
$ steghide extract -p "secret" -sf file.jpg
$ stegcracker file.jpg /usr/share/wordlists/rockyou.txt
```

## PNG (Portable Network Graphics) {: #png }

- Herramientas como [Steghide](http://steghide.sourceforge.net/) y [OutGuess](https://github.com/resurrecting-open-source-projects/outguess) no funcionan con archivos PNG. En cambio, este tipo de archivo permite un guardado sin compresión, y por lo tanto ocultar mensajes en los LSB. La herramienta [Zsteg](https://github.com/zed-0xff/zsteg) presentada más arriba y disponible en Aperi'Solve permite extraer secretos de archivos PNG.

```console
$ zsteg file.png 2b,g,lsb,xy
$ zsteg file.png -E '1b,rgb,lsb'
```

- PNG ofrece una extensión ["APNG"](https://en.wikipedia.org/wiki/APNG) que permite tener una animación de imágenes como en los archivos GIF. Es posible que la visualización del PNG no refleje todo su contenido (por ejemplo, un fotograma con duración cero o un primer fotograma muy largo). La herramienta [APNG Maker](https://ezgif.com/apng-maker) permite ver los distintos fotogramas de un archivo APNG. También se puede codificar un mensaje en las duraciones de cada fotograma.

![APNG](https://upload.wikimedia.org/wikipedia/commons/1/14/Animated_PNG_example_bouncing_beach_ball.png)

- La herramienta [TweakPNG](http://entropymine.com/jason/tweakpng/) presentada anteriormente permite realizar varios tipos de operaciones, como recalcular las sumas de comprobación, reordenar los chunks PNG, aumentar el tamaño visible del PNG o modificar una cabecera.

![TweakPNG](/static/img/cheatsheet/tweakpng.png)

## JPEG (Joint Photographic Experts Group) {: #jpg }

- La herramienta [Zsteg](https://github.com/zed-0xff/zsteg) no funciona con archivos JPEG (jpg, jpeg, ...) porque estos incluyen necesariamente un algoritmo de compresión que reduce la calidad de la imagen y altera los LSB. En cambio, las herramientas [Steghide](http://steghide.sourceforge.net/) y [OutGuess](https://github.com/resurrecting-open-source-projects/outguess) mostradas más arriba son compatibles con este formato de archivo.

```console
$ outguess -k secret file.jpg output.raw
$ steghide extract -p "secret" -sf file.jpg
```

## GIF (Graphics Interchange Format) {: #gif }

- Los GIF suelen ser imágenes animadas cuyo formato está, en general, mal soportado por las herramientas de estegoanálisis. Además, este formato de imagen suele ofrecer una paleta que no supera los 256 colores, frente a los 16 millones del PNG (sin contar la transparencia). No obstante, la herramienta [GIF Maker](https://ezgif.com/maker) facilita la manipulación de archivos GIF.
- Los GIF pueden incrustar imágenes (fotogramas) con duración cero. Estas no serán visibles sin un análisis de cada fotograma.

![GIF Maker](/static/img/cheatsheet/gif_maker.png)

- Un mensaje oculto puede incrustarse en la duración de los fotogramas (morse, ascii, binario, ...).
- [Ffmpeg](https://ffmpeg.org/) puede usarse para extraer los fotogramas de un GIF. No se puede garantizar la exhaustividad de los fotogramas extraídos.

```console
$ ffmpeg -i file.gif -vsync 0 output/file%d.png
```

## Audio {: #audio }

- La técnica más común para los archivos de sonido se basa en el espectro de audio. En efecto, es posible dibujar un mensaje visible en el espectro de audio con herramientas como [Coagula](https://www.abc.se/~re/Coagula/Coagula.html). Después, ese espectro puede analizarse con herramientas de análisis espectral como [Sonic Visualiser](https://www.sonicvisualiser.org/), [Audacity](https://www.audacityteam.org/) o la herramienta en línea [dcode](https://www.dcode.fr/spectral-analysis).

![Espectro en Audacity](/static/img/cheatsheet/audacity_1.png)

Puede ser necesario hacer clic derecho en la escala para alejar el zoom y ver el espectro completo, o cambiar al modo logarítmico.

![Espectro en Audacity](/static/img/cheatsheet/audacity_2.png)

- Se pueden usar frecuencias inaudibles para ocultar mensajes. Se recomienda un análisis espectral por encima de 20KHz y por debajo de 20Hz; allí puede esconderse un mensaje codificado en morse o en binario.
- Los sonidos son simples señales de telecomunicación que pueden usarse con otros fines. Pueden emplearse métodos de codificación especiales, como el [código DTMF](https://en.wikipedia.org/wiki/Dual-tone_multi-frequency_signaling) usado antiguamente en telefonía o la [SSTV](https://en.wikipedia.org/wiki/Slow-scan_television) usada en televisión para la transmisión de imágenes. Estas señales se codifican en frecuencias audibles, pero su interpretación requiere decodificadores especiales. Se optará entonces por un [decodificador DTMF](http://dialabc.com/sound/detect/) para la primera técnica y por un decodificador SSTV como [QSSTV](https://doc.ubuntu-fr.org/qsstv) para la segunda.
- Al igual que los archivos PNG, algunos archivos de sonido incluyen su tamaño teórico en sus cabeceras. Es el caso, en particular, de los [archivos WAV](https://fr.wikipedia.org/wiki/Waveform_Audio_File_Format#En-t%C3%AAte_de_fichier_WAV), cuyo bloque DataSize puede reducirse o aumentarse con un editor hexadecimal.
- La técnica LSB puede utilizarse en ciertos archivos de audio. Es necesario entonces extraer los LSB de los datos de audio; la herramienta [WavSteg](https://github.com/ragibson/Steganography#WavSteg) permite realizar esta manipulación en archivos WAV.

```console
$ stegolsb wavsteg -r -i file.wav -o output.txt -n 1 -b 1000
```

- Las herramientas [Steghide](http://steghide.sourceforge.net/) y [DeepSound](http://jpinsoft.net/deepsound/overview.aspx) se usan habitualmente en CTF para ocultar mensajes. Pueden recibir una clave como parámetro, por lo que habrá que adivinar esa clave a partir de la información disponible (medio, nombre del archivo, nombre del reto, etc.) o utilizando una wordlist.

![DeepSound](/static/img/cheatsheet/DeepSound.png)

## Archivos políglotas {: #polyglot }

Se trata de un tipo de archivo que es válido para varios formatos de archivo. Por ejemplo, un archivo de imagen que puede visualizarse y que además es un archivo jar (que puede ejecutarse). Existen varios tipos de archivos políglotas:

- Políglota "simple": es una simple concatenación de archivos;
- Políglota "parásito": es un archivo que contiene otro tipo de archivo.
- Políglota "mille-feuilles" (milhojas): las capas se alternan controlando la estructura interna del archivo.
- Políglota "quimera": el archivo tiene un cuerpo (datos) y varias cabezas. Dado que varios formatos usan el mismo algoritmo para almacenar los datos, como el Deflate de Zlib, el mismo bloque de datos es utilizado por distintas cabeceras (por ejemplo, los píxeles de una imagen). Hay varias cabeceras presentes para que esa imagen sea visible mediante varios formatos (jpg, png, ...) dentro del mismo archivo.
- Archivos "esquizofrénicos": es un único tipo de archivo, pero su contenido se interpreta de forma diferente según la herramienta que lo ejecuta o que accede a él. Suelen ser archivos PDF (interpretación o no de javascript) o imágenes (como la técnica de [Gamma](https://carlmastrangelo.com/blog/gamma-steganography)).
- Angecryption: el resultado del cifrado o descifrado de un archivo da otro archivo válido, del mismo tipo o de un tipo diferente:

![Angecryption](/static/img/cheatsheet/Angecryption.png)

- Los archivos docx, jar, apk, pptx, odf... son archivos comprimidos válidos y pueden descomprimirse. Hay que comprobar entonces si el archivo en cuestión puede abrirse con una herramienta distinta de la asociada a su extensión. El comando `file` no identifica los archivos políglotas.

## Codificación y lenguajes exóticos {: #text }

- El texto ASCII puede codificarse en binario en bloques de `8 bits`; es entonces fácilmente identificable porque cada bloque correspondiente a una letra comienza con un 0. Es posible eliminar ese 0, y los bloques pasan a ser de solo `7 bits`. El texto también puede codificarse en un entero de tipo `long` (a veces en una base distinta de la base 10); por ejemplo, la cadena de caracteres “Hello world!” codificada en un tipo long en base 10 puede decodificarse con el siguiente código en python 2:

```console
python2> hex(22405534230753963835153736737L)[2:].strip('L').decode("hex")
python2> "48656c6c6f20776f726c6421".decode("hex")
```

- Herramientas como [CyberChef](https://gchq.github.io/CyberChef/) (y su opción "magic") pueden ayudar a detectar la codificación utilizada y a decodificar el mensaje oculto. A veces puede ser necesario un cambio de charset (sustitución monoalfabética o cambio de base).
- Los lenguajes exóticos o esotéricos son lenguajes de programación diseñados para ser únicos, difíciles de programar o simplemente extraños. Su diseño y sus juegos de caracteres pueden ser peculiares; es el caso de los lenguajes más frecuentes en CTF como [BrainFuck](https://esolangs.org/wiki/Brainfuck), [WhiteSpace](https://esolangs.org/wiki/Whitespace), [PIET](https://esolangs.org/wiki/Piet) o [Malbolge](https://esolangs.org/wiki/Malbolge). El sitio web [EsoLang](https://esolangs.org/wiki/Language_list) recopila estos distintos lenguajes y puede ser útil en sus investigaciones.

```console
brainfuck>
++++++++++[>+>+++>+++++++>++++++++++<<<<-]>>>++.>+.+++++++..+++.<<++.>>++++++++.--------.+++.------.--------.<<+.

malbolge>
('&%:9]!~}|z2Vxwv-,POqponl$Hjig%eB@@>}=<M:9wv6WsU2T|nm-,jcL(I&%$#"
`CB]V?Tx<uVtT`Rpo3NlF.Jh++FdbCBA@?]!~|4XzyTT43Qsqq(Lnmkj"Fhg${z@>
```

[![PIET](/static/img/cheatsheet/piet.png)](https://esolangs.org/wiki/Piet)

## Para ir más lejos {: #more }

- [Blog de Aperi'Kube - categoría Esteganografía](https://www.aperikube.fr/cat/steg/)
- [CTF Time - Writeups (Stegano)](https://ctftime.org/writeups)
- [Corkami](http://corkami.github.io/)
- [Root-Me - Esteganografía](https://www.root-me.org/en/Challenges/Steganography/)
- [Estereograma](https://en.wikipedia.org/wiki/Autostereogram)
