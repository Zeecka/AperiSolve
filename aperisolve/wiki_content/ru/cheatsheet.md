Title: Шпаргалка по стеганографии для CTF
Description: Шпаргалка по стеганографии для участников CTF: анализ PNG, JPEG, GIF и аудиофайлов с помощью file, exiftool, zsteg, steghide, binwalk, foremost и других инструментов.
Order: 20

# Шпаргалка

## Отказ от ответственности

Эта шпаргалка призвана направить участников CTF в их поисках. Она не отражает современные техники стеганографии/стегоанализа, а её содержание не имеет отношения к созданию интересного задания 😉.

## Проверка типа файла / метаданных

- Если расширение файла вам незнакомо, поищите его в интернете. Проверьте также формат файла.
- Используйте команду `file`, чтобы убедиться, что расширение соответствует типу файла. Команда опирается на [магические байты](https://en.wikipedia.org/wiki/List_of_file_signatures) в начале файла, поэтому возможны ложные срабатывания.

```console
$ file data.raw
```

- Если расширение и файл неизвестны, изучите шестнадцатеричную структуру файла в редакторе вроде [hexed.it](https://hexed.it/), чтобы определить структуру файла.
- Выведите метаданные файла командой `exiftool`.

```console
$ exiftool data.raw
```

## Изменение структуры файла {: #filestruct }

- Изменяйте структуру файла с помощью шестнадцатеричного редактора, например [hexed.it](https://hexed.it/). Чанки PNG удобно редактировать в [TweakPNG](http://entropymine.com/jason/tweakpng/) (Windows или Wine).

![TweakPNG](/static/img/cheatsheet/tweakpng.png)

- Проверяйте контрольные суммы файла. Обычно это CRC32; такие инструменты, как [PngCheck](http://www.libpng.org/pub/png/apps/pngcheck.html) или [PCRT](https://github.com/sherlly/PCRT), помогают проверить и исправить эти контрольные суммы.

```console
$ pngcheck -c file.png
$ PCRT.py -v -i file.png
```

- Для многих типов файлов (PNG, WAV, ...) размер медиа содержится в заголовках. Этот размер можно уменьшить, чтобы отобразить лишь часть медиа (начало изображения, начало звука, ...).

## Сырые данные {: #rawdata }

- Сырой файл можно импортировать в [Audacity](https://www.audacityteam.org/download/), чтобы прослушать его как звуковую дорожку (File > Import > Raw Data).

![Audacity](/static/img/cheatsheet/audacity_raw.png)

- Аналогично, инструмент [GIMP](https://www.gimp.org/downloads/) позволяет импортировать изображение из сырых данных (File > Open).
- Инструмент [BinVis.io](http://binvis.io/) позволяет просматривать двоичные файлы в графическом виде и может дать подсказки о типе файла.
- Команда `strings` выводит строки, присутствующие в файле.

```console
$ strings -s file.raw
$ strings -S file.raw
$ strings -b file.raw
$ strings -l file.raw
$ strings -B file.raw
$ strings -L file.raw
```

## Изображения {: #image }

|             | PNG | JPG/JPEG | BMP |
|-------------|-----|----------|-----|
| Aperi'Solve | OK  | OK       | OK  |
| Zsteg       | OK  | KO       | OK  |
| Steghide    | KO  | OK       | OK  |
| OutGuess    | KO  | OK       | KO  |

- Стойкость стеганографии зависит от используемого алгоритма и знания исходного носителя. Поиск оригинального медиа позволяет провести сравнение и выявить внесённые изменения. Обратный поиск в [Google Image](https://images.google.com/) или [Yandex Images](https://yandex.com/images/) может найти оригинал (убедитесь, что размер и тип файла совпадают).
- Инструмент [Stegsolve](http://www.caesum.com/handbook/Stegsolve.jar) позволяет выполнять операции над двумя изображениями и таким образом выявлять различия между чистым носителем и стегоносителем с помощью операции XOR.

![XOR в Stegsolve](/static/img/cheatsheet/stegsolve_xor.png)
![XOR в Stegsolve 2](/static/img/cheatsheet/stegsolve_xor2.png)

- Инструмент [Zsteg](https://github.com/zed-0xff/zsteg) позволяет извлекать сообщения и двоичные данные, закодированные в различных слоях, например в 2 младших битах (LSB) зелёного канала.

```console
$ zsteg file.png 2b,g,lsb,xy
$ zsteg file.png -E '1b,rgb,lsb'
```

- Иногда анализ битовых слоёв в инструменте [Stegsolve](http://www.caesum.com/handbook/Stegsolve.jar) (или в Aperi'Solve) позволяет заметить отдельные изменённые области. Тогда для извлечения этих областей может понадобиться написать скрипт. Следующий код на python получает изображение в виде списка пикселей: [(100,120,43), (230, 124, 110), ...]

```python
# pip install Pillow
from PIL import Image
stegano_image = Image.open('file.png')
width, height = stegano_image.size
pxs = list(stegano_image.getdata())
print(pxs[:10])
```

- Стегоносители могут опираться на алгоритм с ключом шифрования. Так работают [Steghide](http://steghide.sourceforge.net/) и [OutGuess](https://github.com/resurrecting-open-source-projects/outguess). Паролем может быть имя файла, строка символов, содержащаяся в файле (`strings` и `exiftool`), или объект, изображённый на картинке. В некоторых случаях пароль восстановить не удаётся, и приходится прибегать к брутфорсу. Инструменты [StegCracker](https://github.com/Paradoxis/StegCracker) и [Stegbrute](https://github.com/R4yGM/stegbrute) позволяют перебором находить секреты, скрытые с помощью [Steghide](http://steghide.sourceforge.net/).

```console
$ steghide extract -p "secret" -sf file.jpg
$ stegcracker file.jpg /usr/share/wordlists/rockyou.txt
```

## PNG (Portable Network Graphics) {: #png }

- Такие инструменты, как [Steghide](http://steghide.sourceforge.net/) и [OutGuess](https://github.com/resurrecting-open-source-projects/outguess), не работают с PNG-файлами. Зато этот тип файлов допускает сохранение без сжатия, а значит, позволяет прятать сообщения в младших битах (LSB). Инструмент [Zsteg](https://github.com/zed-0xff/zsteg), представленный выше и доступный на Aperi'Solve, позволяет извлекать секреты из PNG-файлов.

```console
$ zsteg file.png 2b,g,lsb,xy
$ zsteg file.png -E '1b,rgb,lsb'
```

- У PNG есть расширение ["APNG"](https://en.wikipedia.org/wiki/APNG), позволяющее создавать анимацию из изображений, как в GIF-файлах. Возможно, что при просмотре PNG видно не всё его содержимое (например, кадр с нулевой длительностью или очень длинный первый кадр). Инструмент [APNG Maker](https://ezgif.com/apng-maker) позволяет просмотреть отдельные кадры APNG-файла. Сообщение также может быть закодировано в длительностях кадров.

![APNG](https://upload.wikimedia.org/wikipedia/commons/1/14/Animated_PNG_example_bouncing_beach_ball.png)

- Инструмент [TweakPNG](http://entropymine.com/jason/tweakpng/), представленный ранее, позволяет выполнять операции нескольких типов: пересчитывать контрольные суммы, переупорядочивать чанки PNG, увеличивать видимый размер PNG или изменять заголовок.

![TweakPNG](/static/img/cheatsheet/tweakpng.png)

## JPEG (Joint Photographic Experts Group) {: #jpg }

- Инструмент [Zsteg](https://github.com/zed-0xff/zsteg) не работает с JPEG-файлами (jpg, jpeg, ...), поскольку они обязательно используют алгоритм сжатия, снижающий качество изображения и изменяющий LSB. Зато представленные выше инструменты [Steghide](http://steghide.sourceforge.net/) и [OutGuess](https://github.com/resurrecting-open-source-projects/outguess) совместимы с этим форматом файлов.

```console
$ outguess -k secret file.jpg output.raw
$ steghide extract -p "secret" -sf file.jpg
```

## GIF (Graphics Interchange Format) {: #gif }

- GIF — это, как правило, анимированные изображения, формат которых обычно плохо поддерживается инструментами стегоанализа. Кроме того, этот формат изображений обычно предлагает палитру не более чем из 256 цветов против 16 миллионов у PNG (без учёта прозрачности). Тем не менее инструмент [GIF Maker](https://ezgif.com/maker) упрощает работу с GIF-файлами.
- GIF может содержать изображения (кадры) с нулевой длительностью. Увидеть их без анализа каждого кадра невозможно.

![GIF Maker](/static/img/cheatsheet/gif_maker.png)

- Скрытое сообщение может быть закодировано в длительностях кадров (морзе, ascii, двоичный код, ...).
- Для извлечения кадров из GIF можно использовать [Ffmpeg](https://ffmpeg.org/). Полнота извлечённых кадров не гарантируется.

```console
$ ffmpeg -i file.gif -vsync 0 output/file%d.png
```

## Аудио {: #audio }

- Самая распространённая техника для звуковых файлов основана на звуковом спектре. Действительно, на спектре можно нарисовать видимое сообщение с помощью инструментов вроде [Coagula](https://www.abc.se/~re/Coagula/Coagula.html). Затем этот спектр можно изучить средствами спектрального анализа, такими как [Sonic Visualiser](https://www.sonicvisualiser.org/), [Audacity](https://www.audacityteam.org/) или онлайн-инструмент [dcode](https://www.dcode.fr/spectral-analysis).

![Спектр в Audacity](/static/img/cheatsheet/audacity_1.png)

Может понадобиться щёлкнуть правой кнопкой мыши по шкале, чтобы уменьшить масштаб и увидеть весь спектр, либо переключиться в логарифмический режим.

![Спектр в Audacity](/static/img/cheatsheet/audacity_2.png)

- Для сокрытия сообщений могут использоваться неслышимые частоты. Рекомендуется спектральный анализ выше 20 кГц и ниже 20 Гц — там может скрываться сообщение, закодированное морзе или двоичным кодом.
- Звуки — это простые телекоммуникационные сигналы, которые могут применяться и для других целей. Возможны особые методы кодирования, такие как [код DTMF](https://en.wikipedia.org/wiki/Dual-tone_multi-frequency_signaling), ранее использовавшийся в телефонии, или [SSTV](https://en.wikipedia.org/wiki/Slow-scan_television), применяемый в телевидении для передачи изображений. Эти сигналы кодируются на слышимых частотах, но для их интерпретации нужны специальные декодеры. Для первой техники подойдёт [декодер DTMF](http://dialabc.com/sound/detect/), для второй — декодер SSTV, например [QSSTV](https://doc.ubuntu-fr.org/qsstv).
- Как и PNG-файлы, некоторые звуковые файлы хранят свой теоретический размер в заголовках. Это особенно касается [WAV-файлов](https://fr.wikipedia.org/wiki/Waveform_Audio_File_Format#En-t%C3%AAte_de_fichier_WAV), у которых блок DataSize можно уменьшить или увеличить с помощью hex-редактора.
- Техника LSB может применяться к некоторым аудиофайлам. В этом случае нужно извлечь LSB из аудиоданных; инструмент [WavSteg](https://github.com/ragibson/Steganography#WavSteg) позволяет проделать эту манипуляцию с WAV-файлами.

```console
$ stegolsb wavsteg -r -i file.wav -o output.txt -n 1 -b 1000
```

- Инструменты [Steghide](http://steghide.sourceforge.net/) и [DeepSound](http://jpinsoft.net/deepsound/overview.aspx) часто используются в CTF для сокрытия сообщений. Они могут принимать ключ в качестве параметра, поэтому этот ключ придётся угадать по доступной информации (медиа, имя файла, название задания и т. д.) или подобрать по словарю.

![DeepSound](/static/img/cheatsheet/DeepSound.png)

## Файлы-полиглоты {: #polyglot }

Это тип файла, который валиден сразу в нескольких форматах. Например, файл изображения, который можно просматривать и который одновременно является jar-файлом (то есть может быть исполнен). Существует несколько разновидностей файлов-полиглотов:

- «Простой» полиглот: обычная конкатенация файлов;
- «Паразитический» полиглот: файл, содержащий внутри себя файл другого типа.
- Полиглот «мильфей»: слои чередуются за счёт управления внутренней структурой файла.
- Полиглот «химера»: у файла есть тело (данные) и несколько голов. Поскольку многие форматы используют один и тот же алгоритм хранения данных, например Deflate из Zlib, один и тот же блок данных используется разными заголовками (например, пиксели изображения). В файле присутствует несколько заголовков, так что это изображение можно просмотреть в нескольких форматах (jpg, png, ...) в рамках одного и того же файла.
- «Шизофренические» файлы: это файл единственного типа, но его содержимое интерпретируется по-разному в зависимости от инструмента, который его запускает или открывает. Обычно это PDF-файлы (интерпретация или неинтерпретация javascript) либо изображения (как в технике [Gamma](https://carlmastrangelo.com/blog/gamma-steganography)).
- Angecryption: результат шифрования или расшифровки файла даёт другой валидный файл того же или иного типа:

![Angecryption](/static/img/cheatsheet/Angecryption.png)

- Файлы docx, jar, apk, pptx, odf... являются валидными архивами и могут быть распакованы. Следует проверять, открывается ли рассматриваемый файл инструментом, отличным от того, что связан с его расширением. Команда `file` не распознаёт файлы-полиглоты.

## Кодировки и экзотические языки {: #text }

- Текст ASCII может быть закодирован в двоичном виде блоками по `8 bits`; его легко распознать, поскольку каждый блок, соответствующий букве, начинается с 0. Этот 0 можно убрать — тогда блоки занимают всего `7 bits`. Текст также может быть закодирован целым числом типа `long` (иногда в системе счисления, отличной от десятичной); например, строку символов "Hello world!", закодированную в тип long в десятичной системе, можно декодировать следующим кодом на python 2:

```console
python2> hex(22405534230753963835153736737L)[2:].strip('L').decode("hex")
python2> "48656c6c6f20776f726c6421".decode("hex")
```

- Такие инструменты, как [CyberChef](https://gchq.github.io/CyberChef/) (и его опция "magic"), помогают определить использованную кодировку и декодировать скрытое сообщение. Иногда может понадобиться смена набора символов (моноалфавитная подстановка или смена системы счисления).
- Экзотические, или эзотерические, языки — это языки программирования, задуманные как уникальные, сложные для программирования или просто странные. Их устройство и наборы символов могут быть весьма своеобразными; таковы чаще всего встречающиеся в CTF языки: [BrainFuck](https://esolangs.org/wiki/Brainfuck), [WhiteSpace](https://esolangs.org/wiki/Whitespace), [PIET](https://esolangs.org/wiki/Piet) или [Malbolge](https://esolangs.org/wiki/Malbolge). Сайт [EsoLang](https://esolangs.org/wiki/Language_list) каталогизирует эти языки и может пригодиться в ваших поисках.

```console
brainfuck>
++++++++++[>+>+++>+++++++>++++++++++<<<<-]>>>++.>+.+++++++..+++.<<++.>>++++++++.--------.+++.------.--------.<<+.

malbolge>
('&%:9]!~}|z2Vxwv-,POqponl$Hjig%eB@@>}=<M:9wv6WsU2T|nm-,jcL(I&%$#"
`CB]V?Tx<uVtT`Rpo3NlF.Jh++FdbCBA@?]!~|4XzyTT43Qsqq(Lnmkj"Fhg${z@>
```

[![PIET](/static/img/cheatsheet/piet.png)](https://esolangs.org/wiki/Piet)

## Для дальнейшего изучения {: #more }

- [Блог Aperi'Kube — раздел «Стеганография»](https://www.aperikube.fr/cat/steg/)
- [CTF Time — райтапы (Stegano)](https://ctftime.org/writeups)
- [Corkami](http://corkami.github.io/)
- [Root-Me — Стеганография](https://www.root-me.org/en/Challenges/Steganography/)
- [Стереограммы](https://en.wikipedia.org/wiki/Autostereogram)
