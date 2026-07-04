Title: Wiki Aperi'Solve - Ferramentas e guias de esteganografia
Description: Documentação do Aperi'Solve: como funciona a análise, guias de cada ferramenta de esteganografia (zsteg, steghide, binwalk, exiftool...) e uma cheatsheet de CTF.
Order: 1

# Wiki Aperi'Solve

Bem-vindo ao wiki do Aperi'Solve. O Aperi'Solve é uma plataforma online
gratuita que realiza análise por camadas e detecção de esteganografia em
imagens: envie uma imagem na [página inicial](/pt/) e todos os analisadores
são executados automaticamente.

Este wiki documenta como ler os resultados e como funciona cada ferramenta
subjacente, para que você possa reproduzir e estender a análise na sua
própria máquina.

## Comece por aqui

- [Primeiros passos](/pt/wiki/getting-started) — como usar o Aperi'Solve e
  ler seus resultados.
- [Cheatsheet de esteganografia para CTF](/pt/wiki/cheatsheet) — uma
  checklist prática para desafios de imagem, áudio e formatos de arquivo.

## Guias das ferramentas

Cada analisador executado sobre o seu envio tem sua própria página: o que a
ferramenta faz, o comando exato que o Aperi'Solve executa, como interpretar
a saída e como instalá-la localmente.

- [Decompositor de planos de bits](/pt/wiki/tools/decomposer) — visualize
  cada bit de cada canal de cor.
- [Remapeamento de cores](/pt/wiki/tools/color_remapping) — revele dados
  ocultos com transformações de paleta.
- [zsteg](/pt/wiki/tools/zsteg) — detecção de esteganografia LSB para PNG e
  BMP.
- [steghide](/pt/wiki/tools/steghide) — extraia dados ocultos em JPEG/BMP
  com uma senha.
- [binwalk](/pt/wiki/tools/binwalk) — encontre e extraia arquivos embutidos
  dentro da imagem.
- [foremost](/pt/wiki/tools/foremost) — recupere (carving) arquivos
  embutidos na imagem.
- [exiftool](/pt/wiki/tools/exiftool) — leia metadados (EXIF, XMP, IPTC...).
- [pngcheck](/pt/wiki/tools/pngcheck) — verifique a estrutura do PNG e
  encontre chunks corrompidos.
- [PCRT](/pt/wiki/tools/pcrt) — detecte e repare arquivos PNG corrompidos.
- [OutGuess](/pt/wiki/tools/outguess) — extraia dados ocultos de imagens
  JPEG.
- [jsteg](/pt/wiki/tools/jsteg) — extraia dados LSB dos coeficientes DCT de
  JPEG.
- [JPHide/JPSeek](/pt/wiki/tools/jpseek) — extraia payloads JPHide de JPEG.
- [OpenStego](/pt/wiki/tools/openstego) — extraia esteganografia LSB
  randomizada.
- [identify](/pt/wiki/tools/identify) — inspecione propriedades da imagem
  com o ImageMagick.
- [file](/pt/wiki/tools/file) — identifique o tipo real de arquivo de um
  envio.
- [strings](/pt/wiki/tools/strings) — encontre texto legível dentro de
  arquivos de imagem.

Contribuições são bem-vindas no
[GitHub](https://github.com/Zeecka/AperiSolve).

## O que é análise de esteganografia?

A esteganografia esconde dados dentro de um arquivo portador inofensivo —
para imagens, isso significa manipular bits de pixels, entradas de paleta,
campos de metadados ou a própria estrutura do arquivo. A esteganálise é a
prática de detectar esses dados ocultos. Nenhuma ferramenta cobre todas as
técnicas, e é por isso que o Aperi'Solve executa uma bateria inteira de
analisadores lado a lado e permite comparar suas saídas de relance.
