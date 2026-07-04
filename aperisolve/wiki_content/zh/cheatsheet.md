Title: 隐写 CTF 速查表
Description: 面向 CTF 选手的隐写速查表：使用 file、exiftool、zsteg、steghide、binwalk、foremost 等工具分析 PNG、JPEG、GIF 和音频文件。
Order: 20

# 速查表

## 免责声明

本速查表旨在为 CTF 选手的解题研究提供指引。它并不代表现代隐写/隐写分析技术的水平，其内容也与如何设计一道有趣的题目无关 😉。

## 检查文件类型 / 元数据

- 如果不认识文件扩展名，请上网查询，同时确认文件格式。
- 使用 `file` 命令检查扩展名与文件类型是否一致。该命令基于文件开头的[魔数（Magic Bytes）](https://en.wikipedia.org/wiki/List_of_file_signatures)判断，因此可能出现误报。

```console
$ file data.raw
```

- 当扩展名和文件都无法识别时，可用 [hexed.it](https://hexed.it/) 之类的编辑器查看文件的十六进制内容，以识别文件结构。
- 使用 `exiftool` 命令显示文件的元数据。

```console
$ exiftool data.raw
```

## 修改文件结构 {: #filestruct }

- 使用 [hexed.it](https://hexed.it/) 之类的十六进制编辑器修改文件结构。PNG 的块（chunk）可以用 [TweakPNG](http://entropymine.com/jason/tweakpng/)（Windows 或 Wine）轻松编辑。

![TweakPNG](/static/img/cheatsheet/tweakpng.png)

- 校验文件的校验和。这些通常是 CRC32，[PngCheck](http://www.libpng.org/pub/png/apps/pngcheck.html) 或 [PCRT](https://github.com/sherlly/PCRT) 之类的工具可用于校验并修正这些校验和。

```console
$ pngcheck -c file.png
$ PCRT.py -v -i file.png
```

- 许多类型的文件（PNG、WAV 等）在头部记录了媒体尺寸。可以调小这个尺寸，使其只显示媒体的一部分（图片的开头、声音的开头等）。

## 原始数据 {: #rawdata }

- 可以将原始文件导入 [Audacity](https://www.audacityteam.org/download/)，把它当作音轨来收听（File > Import > Raw Data）。

![Audacity](/static/img/cheatsheet/audacity_raw.png)

- 类似地，[GIMP](https://www.gimp.org/downloads/) 工具支持从原始数据导入图像（File > Open）。
- [BinVis.io](http://binvis.io/) 工具可以将二进制文件可视化，为判断文件类型提供线索。
- `strings` 命令可以显示文件中的可打印字符串。

```console
$ strings -s file.raw
$ strings -S file.raw
$ strings -b file.raw
$ strings -l file.raw
$ strings -B file.raw
$ strings -L file.raw
```

## 图片 {: #image }

|             | PNG | JPG/JPEG | BMP |
|-------------|-----|----------|-----|
| Aperi'Solve | OK  | OK       | OK  |
| Zsteg       | OK  | KO       | OK  |
| Steghide    | KO  | OK       | OK  |
| OutGuess    | KO  | OK       | KO  |

- 隐写的健壮性取决于所用算法以及对载体媒体的了解程度。找到原始媒体后即可进行比对，识别其中被修改之处。可通过 [Google 图片](https://images.google.com/) 或 [Yandex Images](https://yandex.com/images/) 反向搜索找到原始媒体（注意确认文件大小和类型是否一致）。
- [Stegsolve](http://www.caesum.com/handbook/Stegsolve.jar) 工具可以对两张图片执行运算，例如通过 XOR（异或）运算找出载体图片与隐写图片之间的差异。

![Stegsolve XOR](/static/img/cheatsheet/stegsolve_xor.png)
![Stegsolve XOR 2](/static/img/cheatsheet/stegsolve_xor2.png)

- [Zsteg](https://github.com/zed-0xff/zsteg) 工具可以提取编码在不同图层上的消息和二进制数据，例如绿色通道的 2 个 LSB。

```console
$ zsteg file.png 2b,g,lsb,xy
$ zsteg file.png -E '1b,rgb,lsb'
```

- 有时，用 [Stegsolve](http://www.caesum.com/handbook/Stegsolve.jar) 工具（或 Aperi'Solve）做位平面分析，能突出显示被改动过的特定区域。此时可能需要编写脚本来提取这些区域。下面的 Python 代码把图片读取为像素列表：[(100,120,43), (230, 124, 110), ...]

```python
# pip install Pillow
from PIL import Image
stegano_image = Image.open('file.png')
width, height = stegano_image.size
pxs = list(stegano_image.getdata())
print(pxs[:10])
```

- 隐写媒体可能采用带加密密钥的算法，[Steghide](http://steghide.sourceforge.net/) 和 [OutGuess](https://github.com/resurrecting-open-source-projects/outguess) 就是如此。密码可能是文件名、文件中包含的某个字符串（`strings` 和 `exiftool`），或图片所描绘的对象。有时无法直接找到密码，只能进行暴力破解。[StegCracker](https://github.com/Paradoxis/StegCracker) 和 [Stegbrute](https://github.com/R4yGM/stegbrute) 工具可以对 [Steghide](http://steghide.sourceforge.net/) 隐藏的秘密进行暴力破解。

```console
$ steghide extract -p "secret" -sf file.jpg
$ stegcracker file.jpg /usr/share/wordlists/rockyou.txt
```

## PNG（Portable Network Graphics，便携式网络图形） {: #png }

- [Steghide](http://steghide.sourceforge.net/) 和 [OutGuess](https://github.com/resurrecting-open-source-projects/outguess) 之类的工具不适用于 PNG 文件。但另一方面，这种格式支持无压缩保存，因此可以在 LSB 上隐藏消息。前文介绍并可在 Aperi'Solve 上使用的 [Zsteg](https://github.com/zed-0xff/zsteg) 工具能够从 PNG 文件中提取隐藏内容。

```console
$ zsteg file.png 2b,g,lsb,xy
$ zsteg file.png -E '1b,rgb,lsb'
```

- PNG 提供了 ["APNG"](https://en.wikipedia.org/wiki/APNG) 扩展，可以像 GIF 文件一样呈现图像动画。PNG 的显示效果可能并未反映其全部内容（例如某一帧的持续时间为零，或第一帧的持续时间极长）。[APNG Maker](https://ezgif.com/apng-maker) 工具可以查看 APNG 文件的各个帧。消息也可能被编码在每一帧的持续时间上。

![APNG](https://upload.wikimedia.org/wikipedia/commons/1/14/Animated_PNG_example_bouncing_beach_ball.png)

- 前面介绍过的 [TweakPNG](http://entropymine.com/jason/tweakpng/) 工具可以执行多种操作，例如重新计算校验和、调整 PNG 块的顺序、增大 PNG 的可见尺寸或修改文件头。

![TweakPNG](/static/img/cheatsheet/tweakpng.png)

## JPEG（Joint Photographic Experts Group，联合图像专家组） {: #jpg }

- [Zsteg](https://github.com/zed-0xff/zsteg) 工具不适用于 JPEG 文件（jpg、jpeg 等），因为这类文件必然经过压缩算法处理，会降低图片质量并破坏 LSB。相反，前面介绍的 [Steghide](http://steghide.sourceforge.net/) 和 [OutGuess](https://github.com/resurrecting-open-source-projects/outguess) 工具兼容这种文件格式。

```console
$ outguess -k secret file.jpg output.raw
$ steghide extract -p "secret" -sf file.jpg
```

## GIF（Graphics Interchange Format，图形交换格式） {: #gif }

- GIF 通常是动态图片，其格式普遍缺乏隐写分析工具的良好支持。此外，这种图片格式的调色板一般不超过 256 色，而 PNG（不含透明度）可达 1600 万色。不过，[GIF Maker](https://ezgif.com/maker) 工具可以方便地处理 GIF 文件。
- GIF 可以嵌入持续时间为零的图像（帧）。若不逐帧分析，这些帧将无法被看到。

![GIF Maker](/static/img/cheatsheet/gif_maker.png)

- 隐藏消息可以编码在各帧的持续时间上（摩尔斯电码、ASCII、二进制等）。
- [Ffmpeg](https://ffmpeg.org/) 可用于从 GIF 中提取帧，但无法保证提取的帧是完整的。

```console
$ ffmpeg -i file.gif -vsync 0 output/file%d.png
```

## 音频 {: #audio }

- 针对声音文件最常见的技术基于音频频谱。事实上，借助 [Coagula](https://www.abc.se/~re/Coagula/Coagula.html) 之类的工具，可以在音频频谱上绘制出可见的消息。随后可以使用 [Sonic Visualiser](https://www.sonicvisualiser.org/)、[Audacity](https://www.audacityteam.org/) 等频谱分析工具，或在线工具 [dcode](https://www.dcode.fr/spectral-analysis) 来分析该频谱。

![Audacity 频谱](/static/img/cheatsheet/audacity_1.png)

可能需要右键点击刻度进行缩小以查看整个频谱，或切换到对数（logarithm）模式。

![Audacity 频谱](/static/img/cheatsheet/audacity_2.png)

- 不可闻的频率也可以用来隐藏消息。建议对 20KHz 以上和 20Hz 以下的频段进行频谱分析，那里可能隐藏着以摩尔斯电码或二进制编码的消息。
- 声音本质上是简单的电信信号，可以被用于其他用途。可能会用到一些特殊的编码方式，例如早期电话使用的 [DTMF 编码](https://en.wikipedia.org/wiki/Dual-tone_multi-frequency_signaling)（双音多频），或电视中用于图像传输的 [SSTV](https://en.wikipedia.org/wiki/Slow-scan_television)（慢扫描电视）。这些信号编码在可听频率上，但解读它们需要专门的解码器。对前一种技术可选用 [DTMF 解码器](http://dialabc.com/sound/detect/)，对后一种则可选用 [QSSTV](https://doc.ubuntu-fr.org/qsstv) 之类的 SSTV 解码器。
- 与 PNG 文件一样，一些声音文件在头部记录了理论大小。[WAV 文件](https://fr.wikipedia.org/wiki/Waveform_Audio_File_Format#En-t%C3%AAte_de_fichier_WAV)尤其如此，可以用十六进制编辑器增大或减小其 DataSize 块。
- LSB 技术也可用于某些音频文件。此时需要从音频数据中提取 LSB；[WavSteg](https://github.com/ragibson/Steganography#WavSteg) 工具可对 WAV 文件执行这一操作。

```console
$ stegolsb wavsteg -r -i file.wav -o output.txt -n 1 -b 1000
```

- [Steghide](http://steghide.sourceforge.net/) 和 [DeepSound](http://jpinsoft.net/deepsound/overview.aspx) 工具在 CTF 中常被用来隐藏消息。它们可以接受一个密钥作为参数，因此需要根据可用信息（媒体内容、文件名、题目名称等）猜出这个密钥，或使用字典进行爆破。

![DeepSound](/static/img/cheatsheet/DeepSound.png)

## Polyglot 文件（多重格式文件） {: #polyglot }

这是一种对多种文件格式都有效的文件。例如一个可以正常查看的图片文件，同时也是一个可以被执行的 jar 文件。Polyglot 文件有以下几种类型：

- “简单”Polyglot：即多个文件的简单拼接；
- “寄生”Polyglot：即一个文件内部包含另一种类型的文件。
- “千层酥”（Mille-feuilles）Polyglot：通过控制文件的内部结构使各层交替排列。
- “嵌合体”（Chimera）Polyglot：文件只有一个主体（数据）但有多个文件头。由于多种格式使用相同的算法来存储数据（例如 Zlib 的 Deflate），同一个数据块（例如图片的像素）可被不同的文件头共用。文件中存在多个文件头，使同一张图片可以在同一个文件内以多种格式（jpg、png 等）显示。
- “精神分裂”（Schizophrenic）文件：这是单一类型的文件，但其内容会因运行或访问它的工具不同而被解读成不同的东西。通常是 PDF 文件（是否解释 JavaScript）或图片（例如 [Gamma](https://carlmastrangelo.com/blog/gamma-steganography) 技术）。
- Angecryption：对一个文件加密或解密后，得到另一个同类型或不同类型的有效文件：

![Angecryption](/static/img/cheatsheet/Angecryption.png)

- Docx、jar、apk、pptx、odf 等文件都是有效的压缩包，可以被解压。因此需要检查目标文件能否用其扩展名对应工具之外的其他工具打开。`file` 命令无法识别 Polyglot 文件。

## 编码与奇异语言 {: #text }

- ASCII 文本可以按每块 `8 bits`（8 位）编码为二进制，这种情况很容易识别，因为每个对应一个字母的块都以 0 开头。也可以去掉这个 0，每块就只有 `7 bits`。文本还可以编码为 `long` 类型的整数（有时使用十进制以外的进制），例如字符串 “Hello world!” 以十进制编码为 long 类型后，可用以下 Python 2 代码解码：

```console
python2> hex(22405534230753963835153736737L)[2:].strip('L').decode("hex")
python2> "48656c6c6f20776f726c6421".decode("hex")
```

- [CyberChef](https://gchq.github.io/CyberChef/)（及其 "magic" 选项）之类的工具可以帮助检测所用的编码并解码隐藏消息。有时可能还需要更换字符集（单表替换或进制转换）。
- 奇异或深奥的编程语言（esoteric languages）是那些被刻意设计得独特、难以编程或干脆怪异的语言。它们的设计和字符集可能很特别，CTF 中最常见的这类语言包括 [BrainFuck](https://esolangs.org/wiki/Brainfuck)、[WhiteSpace](https://esolangs.org/wiki/Whitespace)、[PIET](https://esolangs.org/wiki/Piet) 和 [Malbolge](https://esolangs.org/wiki/Malbolge)。[EsoLang](https://esolangs.org/wiki/Language_list) 网站收录了这些语言，可以为你的研究提供帮助。

```console
brainfuck>
++++++++++[>+>+++>+++++++>++++++++++<<<<-]>>>++.>+.+++++++..+++.<<++.>>++++++++.--------.+++.------.--------.<<+.

malbolge>
('&%:9]!~}|z2Vxwv-,POqponl$Hjig%eB@@>}=<M:9wv6WsU2T|nm-,jcL(I&%$#"
`CB]V?Tx<uVtT`Rpo3NlF.Jh++FdbCBA@?]!~|4XzyTT43Qsqq(Lnmkj"Fhg${z@>
```

[![PIET](/static/img/cheatsheet/piet.png)](https://esolangs.org/wiki/Piet)

## 延伸阅读 {: #more }

- [Aperi'Kube 博客 - 隐写分类](https://www.aperikube.fr/cat/steg/)
- [CTF Time - Writeups（隐写）](https://ctftime.org/writeups)
- [Corkami](http://corkami.github.io/)
- [Root-Me - 隐写术](https://www.root-me.org/en/Challenges/Steganography/)
- [立体图（Stereogram）](https://en.wikipedia.org/wiki/Autostereogram)
