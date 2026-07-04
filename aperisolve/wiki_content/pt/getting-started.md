Title: Primeiros passos com o Aperi'Solve
Description: Como enviar uma imagem no Aperi'Solve, usar senhas e análise profunda, e interpretar os resultados de cada analisador.
Order: 10

# Primeiros passos

## Enviando uma imagem

Acesse a [página inicial](/pt/) e solte uma imagem (PNG, JPG, JPEG, GIF,
BMP, WebP ou TIFF). Duas opções alteram o que é executado:

- **Senha** — repassada aos analisadores que aceitam senha
  ([steghide](/pt/wiki/tools/steghide), openstego, jpseek, outguess). Deixe
  em branco quando você não tiver uma senha candidata; as ferramentas então
  rodam com senha vazia, o que é uma configuração comum em CTF.
- **Análise profunda** — executa adicionalmente analisadores mais lentos,
  como o outguess.

A análise geralmente termina em segundos; imagens pesadas ou uma fila
ocupada podem levar mais tempo. A URL da página de resultados é estável e
compartilhável: a mesma imagem enviada com as mesmas opções retorna a mesma
página instantaneamente.

## Lendo os resultados

Os resultados são agrupados por analisador, sempre na mesma ordem:

1. **Planos de bits e remapeamento de cores** vêm primeiro porque são
   visuais: examine as imagens geradas em busca de contornos, textos ou QR
   codes que apareçam em um único plano de bits.
2. **Ferramentas de arquivo e metadados** (`file`, `exiftool`, `identify`)
   revelam formatos que não correspondem, comentários ocultos e vestígios
   de edição.
3. **Ferramentas de carving** (`binwalk`, `foremost`) listam arquivos
   embutidos dentro da imagem; quando algo é encontrado, um botão de
   download fornece um `.7z` com os arquivos extraídos.
4. **Extratores de esteganografia** (`zsteg`, `steghide`, `jpseek`,
   `jsteg`, `openstego`, `outguess`) tentam a extração real do payload. Um
   bloco vermelho é normal: significa apenas que aquela ferramenta não
   encontrou nada com a senha informada.

## Privacidade e retenção

Os envios são armazenados temporariamente (3 dias por padrão) para que os
resultados possam ser compartilhados, e depois são excluídos
automaticamente. Se você enviou uma imagem por engano, pode removê-la você
mesmo a partir da página de resultados após um curto intervalo, desde que
ela tenha sido enviada apenas do seu próprio endereço IP.

## Indo além

Percorra a [cheatsheet](/pt/wiki/cheatsheet) para conhecer técnicas que
nenhuma ferramenta automatizada cobre, e leia as páginas de cada ferramenta
para executar a mesma análise localmente em arquivos que o Aperi'Solve não
suporta.
