Title: Wiki de Aperi'Solve - Herramientas y guías de esteganografía
Description: Documentación de Aperi'Solve: cómo funciona el análisis, guías de cada herramienta de esteganografía (zsteg, steghide, binwalk, exiftool...) y una cheatsheet CTF.
Order: 1

# Wiki de Aperi'Solve

Bienvenido al wiki de Aperi'Solve. Aperi'Solve es una plataforma en línea
gratuita que realiza análisis por capas y detección de esteganografía en
imágenes: suba una imagen en la [página principal](/es/) y todos los
analizadores se ejecutan automáticamente.

Este wiki documenta cómo leer los resultados y cómo funciona cada
herramienta subyacente, para poder reproducir y ampliar el análisis en su
propia máquina.

## Por dónde empezar

- [Primeros pasos](/es/wiki/getting-started) — cómo usar Aperi'Solve y leer
  sus resultados.
- [Cheatsheet de esteganografía para CTF](/es/wiki/cheatsheet) — una lista
  de comprobación práctica para retos de imágenes, audio y formatos de
  archivo.

## Guías de herramientas

Cada analizador que se ejecuta sobre su envío tiene su propia página: qué
hace la herramienta, el comando exacto que ejecuta Aperi'Solve, cómo
interpretar la salida y cómo instalarla en local.

- [Descomponedor de planos de bits](/es/wiki/tools/decomposer) — visualizar
  cada bit de cada canal de color.
- [Reasignación de colores](/es/wiki/tools/color_remapping) — revelar datos
  ocultos mediante transformaciones de paleta.
- [zsteg](/es/wiki/tools/zsteg) — detección de esteganografía LSB para PNG
  y BMP.
- [steghide](/es/wiki/tools/steghide) — extraer datos ocultos en JPEG/BMP
  con una frase de contraseña.
- [binwalk](/es/wiki/tools/binwalk) — encontrar y extraer archivos
  incrustados dentro de la imagen.
- [foremost](/es/wiki/tools/foremost) — extraer mediante carving los
  archivos incrustados en la imagen.
- [exiftool](/es/wiki/tools/exiftool) — leer metadatos (EXIF, XMP, IPTC...).
- [pngcheck](/es/wiki/tools/pngcheck) — verificar la estructura del PNG y
  encontrar chunks corruptos.
- [PCRT](/es/wiki/tools/pcrt) — detectar y reparar archivos PNG dañados.
- [OutGuess](/es/wiki/tools/outguess) — extraer datos ocultos de imágenes
  JPEG.
- [jsteg](/es/wiki/tools/jsteg) — extraer datos LSB de los coeficientes DCT
  de JPEG.
- [JPHide/JPSeek](/es/wiki/tools/jpseek) — extraer cargas de JPHide desde
  JPEG.
- [OpenStego](/es/wiki/tools/openstego) — extraer esteganografía LSB
  aleatorizada.
- [identify](/es/wiki/tools/identify) — inspeccionar las propiedades de la
  imagen con ImageMagick.
- [file](/es/wiki/tools/file) — identificar el tipo de archivo real de un
  envío.
- [strings](/es/wiki/tools/strings) — encontrar texto legible dentro de los
  archivos de imagen.

Las contribuciones son bienvenidas en
[GitHub](https://github.com/Zeecka/AperiSolve).

## ¿Qué es el análisis de esteganografía?

La esteganografía oculta datos dentro de un archivo portador de apariencia
inocua — en el caso de las imágenes, esto implica manipular los bits de los
píxeles, las entradas de la paleta, los campos de metadatos o la propia
estructura del archivo. El estegoanálisis es la práctica de detectar esos
datos ocultos. Ninguna herramienta cubre todas las técnicas, y por eso
Aperi'Solve ejecuta toda una batería de analizadores en paralelo y permite
comparar sus salidas de un vistazo.
