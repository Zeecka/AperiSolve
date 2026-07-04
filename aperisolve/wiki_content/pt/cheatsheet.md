Title: Cheatsheet de esteganografia para CTF
Description: Cheatsheet de esteganografia para jogadores de CTF: inspecione arquivos PNG, JPEG, GIF e áudio com file, exiftool, zsteg, steghide, binwalk, foremost e mais.
Order: 20

# Cheatsheet

## Aviso

Esta cheatsheet destina-se a orientar jogadores de CTF em suas pesquisas. Ela não é representativa das técnicas modernas de esteganografia/esteganálise, e seu conteúdo não corresponde à criação de um desafio interessante 😉.

## Verificar o tipo de arquivo / metadados

- Pesquise a extensão do arquivo na internet se você não a conhecer. Verifique também o formato do arquivo.
- Use o comando `file` para conferir se a extensão corresponde ao tipo do arquivo. Esse comando se baseia nos [Magic Bytes](https://en.wikipedia.org/wiki/List_of_file_signatures) no início do arquivo, portanto pode retornar falsos positivos.

```console
$ file data.raw
```

- Em caso de extensão e arquivo desconhecidos, inspecione a estrutura hexadecimal do arquivo com um editor como o [hexed.it](https://hexed.it/) para identificar a estrutura do arquivo.
- Exiba os metadados do arquivo com o comando `exiftool`.

```console
$ exiftool data.raw
```

## Modificar a estrutura do arquivo {: #filestruct }

- Modifique a estrutura do arquivo com um editor hexadecimal como o [hexed.it](https://hexed.it/). Os chunks de PNG podem ser facilmente editados com o [TweakPNG](http://entropymine.com/jason/tweakpng/) (Windows ou Wine).

![TweakPNG](/static/img/cheatsheet/tweakpng.png)

- Verifique os checksums do arquivo. Eles geralmente são CRC32; algumas ferramentas como o [PngCheck](http://www.libpng.org/pub/png/apps/pngcheck.html) ou o [PCRT](https://github.com/sherlly/PCRT) são úteis para verificar e corrigir esses checksums.

```console
$ pngcheck -c file.png
$ PCRT.py -v -i file.png
```

- Em muitos tipos de arquivo (PNG, WAV, ...) o tamanho da mídia está contido nos cabeçalhos. Esse tamanho pode então ser reduzido para exibir apenas uma parte da mídia (início de uma imagem, início de um som, ...).

## Dados brutos {: #rawdata }

- É possível importar um arquivo bruto no [Audacity](https://www.audacityteam.org/download/) para ouvi-lo como uma trilha sonora (File > Import > Raw Data).

![Audacity](/static/img/cheatsheet/audacity_raw.png)

- Da mesma forma, a ferramenta [GIMP](https://www.gimp.org/downloads/) permite importar imagens a partir de dados brutos (File > Open).
- A ferramenta [BinVis.io](http://binvis.io/) permite visualizar graficamente arquivos binários e pode dar pistas sobre o tipo de arquivo.
- O comando `strings` permite exibir as strings presentes em um arquivo.

```console
$ strings -s file.raw
$ strings -S file.raw
$ strings -b file.raw
$ strings -l file.raw
$ strings -B file.raw
$ strings -L file.raw
```

## Imagem {: #image }

|             | PNG | JPG/JPEG | BMP |
|-------------|-----|----------|-----|
| Aperi'Solve | OK  | OK       | OK  |
| Zsteg       | OK  | KO       | OK  |
| Steghide    | KO  | OK       | OK  |
| OutGuess    | KO  | OK       | KO  |

- A robustez da esteganografia depende do algoritmo utilizado e do conhecimento da mídia de cobertura. Uma busca pela mídia original permite fazer uma comparação e identificar as alterações realizadas. Uma busca reversa no [Google Image](https://images.google.com/) ou no [Yandex Images](https://yandex.com/images/) pode encontrar a mídia original (não deixe de verificar se o tamanho e o tipo do arquivo correspondem).
- A ferramenta [Stegsolve](http://www.caesum.com/handbook/Stegsolve.jar) permite realizar operações entre 2 imagens e, assim, identificar as diferenças entre uma mídia de cobertura e uma mídia esteganografada usando a operação XOR.

![XOR no Stegsolve](/static/img/cheatsheet/stegsolve_xor.png)
![XOR no Stegsolve 2](/static/img/cheatsheet/stegsolve_xor2.png)

- A ferramenta [Zsteg](https://github.com/zed-0xff/zsteg) permite extrair mensagens e binários codificados em diferentes camadas, como os 2 LSB do canal verde.

```console
$ zsteg file.png 2b,g,lsb,xy
$ zsteg file.png -E '1b,rgb,lsb'
```

- Às vezes, a análise por planos de bits na ferramenta [Stegsolve](http://www.caesum.com/handbook/Stegsolve.jar) (ou no Aperi'Solve) pode evidenciar áreas específicas que foram alteradas. Pode então ser necessário recorrer a scripts para extrair áreas específicas. O código Python a seguir obtém uma imagem como uma lista de pixels: [(100,120,43), (230, 124, 110), ...]

```python
# pip install Pillow
from PIL import Image
stegano_image = Image.open('file.png')
width, height = stegano_image.size
pxs = list(stegano_image.getdata())
print(pxs[:10])
```

- Mídias esteganografadas podem se apoiar em um algoritmo que usa uma chave de criptografia. É o caso do [Steghide](http://steghide.sourceforge.net/) e do [OutGuess](https://github.com/resurrecting-open-source-projects/outguess). A senha pode ser o nome do arquivo, uma cadeia de caracteres contida no arquivo (`strings` & `exiftool`) ou o objeto representado pela imagem. Em alguns casos, a senha não pode ser recuperada e é preciso realizar um bruteforce. As ferramentas [StegCracker](https://github.com/Paradoxis/StegCracker) e [Stegbrute](https://github.com/R4yGM/stegbrute) permitem o bruteforce de segredos ocultos com o [Steghide](http://steghide.sourceforge.net/).

```console
$ steghide extract -p "secret" -sf file.jpg
$ stegcracker file.jpg /usr/share/wordlists/rockyou.txt
```

## PNG (Portable Network Graphics) {: #png }

- Ferramentas como o [Steghide](http://steghide.sourceforge.net/) e o [OutGuess](https://github.com/resurrecting-open-source-projects/outguess) não funcionam com arquivos PNG. Por outro lado, esse tipo de arquivo permite um salvamento sem compressão e, portanto, esconder mensagens nos LSBs. A ferramenta [Zsteg](https://github.com/zed-0xff/zsteg), apresentada acima e disponível no Aperi'Solve, permite extrair segredos de arquivos PNG.

```console
$ zsteg file.png 2b,g,lsb,xy
$ zsteg file.png -E '1b,rgb,lsb'
```

- O PNG oferece uma extensão ["APNG"](https://en.wikipedia.org/wiki/APNG) que permite ter uma animação de imagens como nos arquivos GIF. É possível que a visualização do PNG não reflita todo o seu conteúdo (por exemplo, um quadro com duração zero, ou um primeiro quadro muito longo). A ferramenta [APNG Maker](https://ezgif.com/apng-maker) permite visualizar os diferentes quadros de um arquivo APNG. Uma mensagem também pode ser codificada nas durações de cada quadro.

![APNG](https://upload.wikimedia.org/wikipedia/commons/1/14/Animated_PNG_example_bouncing_beach_ball.png)

- A ferramenta [TweakPNG](http://entropymine.com/jason/tweakpng/), apresentada anteriormente, permite realizar vários tipos de operações, como recalcular checksums, reordenar os chunks do PNG, aumentar o tamanho visível do PNG ou modificar um cabeçalho.

![TweakPNG](/static/img/cheatsheet/tweakpng.png)

## JPEG (Joint Photographic Experts Group) {: #jpg }

- A ferramenta [Zsteg](https://github.com/zed-0xff/zsteg) não funciona em arquivos JPEG (jpg, jpeg, ...) porque estes incluem necessariamente um algoritmo de compressão que reduz a qualidade da imagem e altera os LSBs. Em contrapartida, as ferramentas [Steghide](http://steghide.sourceforge.net/) e [OutGuess](https://github.com/resurrecting-open-source-projects/outguess) mostradas acima são compatíveis com esse formato de arquivo.

```console
$ outguess -k secret file.jpg output.raw
$ steghide extract -p "secret" -sf file.jpg
```

## GIF (Graphics Interchange Format) {: #gif }

- Os GIFs geralmente são imagens animadas cujo formato costuma ser mal suportado pelas ferramentas de esteganálise. Além disso, esse formato de imagem geralmente oferece uma paleta que não ultrapassa 256 cores, contra 16 milhões do PNG (sem contar a transparência). No entanto, a ferramenta [GIF Maker](https://ezgif.com/maker) facilita a manipulação de arquivos GIF.
- GIFs podem embutir imagens (quadros) com duração zero. Elas não poderão ser visualizadas sem uma análise de cada quadro.

![GIF Maker](/static/img/cheatsheet/gif_maker.png)

- Uma mensagem oculta pode ser embutida nas durações dos quadros (morse, ascii, binário, ...).
- O [Ffmpeg](https://ffmpeg.org/) pode ser usado para extrair os quadros de um GIF. A completude dos quadros extraídos não pode ser garantida.

```console
$ ffmpeg -i file.gif -vsync 0 output/file%d.png
```

## Áudio {: #audio }

- A técnica mais comum para arquivos de som se baseia no espectro de áudio. De fato, é possível desenhar uma mensagem visível no espectro de áudio com ferramentas como o [Coagula](https://www.abc.se/~re/Coagula/Coagula.html). Esse espectro pode então ser analisado com ferramentas de análise espectral como o [Sonic Visualiser](https://www.sonicvisualiser.org/), o [Audacity](https://www.audacityteam.org/) ou a ferramenta online [dcode](https://www.dcode.fr/spectral-analysis).

![Espectro no Audacity](/static/img/cheatsheet/audacity_1.png)

Pode ser necessário clicar com o botão direito na escala para reduzir o zoom e visualizar o espectro inteiro, ou mudar para o modo logarítmico.

![Espectro no Audacity](/static/img/cheatsheet/audacity_2.png)

- Frequências inaudíveis podem ser usadas para esconder mensagens. Recomenda-se uma análise espectral acima de 20KHz e abaixo de 20Hz; uma mensagem codificada em morse ou binário pode estar escondida ali.
- Os sons são simples sinais de telecomunicação que podem ser usados para outros fins. Métodos especiais de codificação podem ser empregados, como o [código DTMF](https://en.wikipedia.org/wiki/Dual-tone_multi-frequency_signaling), antigamente usado em telefonia, ou o [SSTV](https://en.wikipedia.org/wiki/Slow-scan_television), usado na televisão para a transferência de imagens. Esses sinais são codificados em frequências audíveis, mas sua interpretação requer decodificadores especiais. Optaremos então por um [decodificador DTMF](http://dialabc.com/sound/detect/) para a primeira técnica e por um decodificador SSTV como o [QSSTV](https://doc.ubuntu-fr.org/qsstv) para a segunda.
- Assim como os arquivos PNG, alguns arquivos de som embutem seus tamanhos teóricos nos cabeçalhos. É o caso, em particular, dos [arquivos WAV](https://fr.wikipedia.org/wiki/Waveform_Audio_File_Format#En-t%C3%AAte_de_fichier_WAV), cujo bloco DataSize pode ser diminuído ou aumentado com um editor hexadecimal.
- A técnica LSB pode ser usada em certos arquivos de áudio. É preciso então extrair os LSBs dos dados de áudio; a ferramenta [WavSteg](https://github.com/ragibson/Steganography#WavSteg) permite realizar essa manipulação em arquivos WAV.

```console
$ stegolsb wavsteg -r -i file.wav -o output.txt -n 1 -b 1000
```

- As ferramentas [Steghide](http://steghide.sourceforge.net/) e [DeepSound](http://jpinsoft.net/deepsound/overview.aspx) são comumente usadas em CTF para esconder mensagens. Elas podem receber uma chave como parâmetro; será preciso então adivinhar essa chave a partir das informações disponíveis (mídia, nome do arquivo, nome do desafio etc.) ou usando uma wordlist.

![DeepSound](/static/img/cheatsheet/DeepSound.png)

## Arquivos poliglotas {: #polyglot }

Trata-se de um tipo de arquivo que é válido para diferentes formatos de arquivo. Por exemplo, um arquivo de imagem que pode ser visualizado e que também é um arquivo jar (que pode ser executado). Existem vários tipos de arquivos poliglotas:

- Poliglota "simples": é uma simples concatenação de arquivos;
- Poliglota "parasita": é um arquivo que contém outro tipo de arquivo.
- Poliglota "mille-feuilles": as camadas são alternadas controlando a estrutura interna do arquivo.
- Poliglota "quimera": o arquivo tem um corpo (dados) e várias cabeças. Como vários formatos usam o mesmo algoritmo para armazenar dados, como o Deflate da Zlib, o mesmo bloco de dados é usado por cabeçalhos diferentes (por exemplo, os pixels de uma imagem). Vários cabeçalhos estão presentes para que essa imagem seja visível em vários formatos (jpg, png, ...) dentro do mesmo arquivo.
- Arquivos "esquizofrênicos": trata-se de um único tipo de arquivo, mas seu conteúdo é interpretado de forma diferente dependendo da ferramenta que executa ou acessa esse arquivo. Geralmente são arquivos PDF (interpretação ou não de javascript) ou imagens (como a técnica do [Gamma](https://carlmastrangelo.com/blog/gamma-steganography)).
- Angecryption: o resultado da criptografia ou descriptografia de um arquivo gera outro arquivo válido, do mesmo tipo ou de um tipo diferente:

![Angecryption](/static/img/cheatsheet/Angecryption.png)

- Arquivos docx, jar, apk, pptx, odf... são arquivos compactados válidos e podem ser descompactados. É preciso então verificar se o arquivo em questão pode ser aberto com uma ferramenta diferente daquela associada à sua extensão. O comando `file` não identifica arquivos poliglotas.

## Codificação e linguagens exóticas {: #text }

- Um texto ASCII pode ser codificado em binário em blocos de `8 bits`; ele é então facilmente identificável, pois cada bloco correspondente a uma letra começa com 0. É possível remover esse 0, e os blocos passam então a ter apenas `7 bits`. O texto também pode ser codificado em um inteiro do tipo `long` (às vezes em uma base diferente da base 10); por exemplo, a cadeia de caracteres "Hello world!" codificada em um tipo long na base 10 pode ser decodificada com o seguinte código python 2:

```console
python2> hex(22405534230753963835153736737L)[2:].strip('L').decode("hex")
python2> "48656c6c6f20776f726c6421".decode("hex")
```

- Ferramentas como o [CyberChef](https://gchq.github.io/CyberChef/) (e a opção "magic") podem ajudar a detectar a codificação usada e decodificar a mensagem oculta. Às vezes, uma mudança de charset pode ser necessária (substituição monoalfabética ou mudança de base).
- Linguagens exóticas ou esotéricas são linguagens de programação projetadas para serem únicas, difíceis de programar ou simplesmente estranhas. Seu design e seus charsets podem ser peculiares; é o caso das linguagens mais encontradas em CTF, como [BrainFuck](https://esolangs.org/wiki/Brainfuck), [WhiteSpace](https://esolangs.org/wiki/Whitespace), [PIET](https://esolangs.org/wiki/Piet) ou [Malbolge](https://esolangs.org/wiki/Malbolge). O site [EsoLang](https://esolangs.org/wiki/Language_list) cataloga essas diferentes linguagens e pode ser útil nas suas pesquisas.

```console
brainfuck>
++++++++++[>+>+++>+++++++>++++++++++<<<<-]>>>++.>+.+++++++..+++.<<++.>>++++++++.--------.+++.------.--------.<<+.

malbolge>
('&%:9]!~}|z2Vxwv-,POqponl$Hjig%eB@@>}=<M:9wv6WsU2T|nm-,jcL(I&%$#"
`CB]V?Tx<uVtT`Rpo3NlF.Jh++FdbCBA@?]!~|4XzyTT43Qsqq(Lnmkj"Fhg${z@>
```

[![PIET](/static/img/cheatsheet/piet.png)](https://esolangs.org/wiki/Piet)

## Para ir além {: #more }

- [Blog do Aperi'Kube - Categoria Esteganografia](https://www.aperikube.fr/cat/steg/)
- [CTF Time - Writeups (Stegano)](https://ctftime.org/writeups)
- [Corkami](http://corkami.github.io/)
- [Root-Me - Esteganografia](https://www.root-me.org/en/Challenges/Steganography/)
- [Estereograma](https://en.wikipedia.org/wiki/Autostereogram)
