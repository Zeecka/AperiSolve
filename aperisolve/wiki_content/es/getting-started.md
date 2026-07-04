Title: Primeros pasos con Aperi'Solve
Description: Cómo subir una imagen a Aperi'Solve, usar contraseñas y el análisis profundo, e interpretar los resultados de cada analizador.
Order: 10

# Primeros pasos

## Subir una imagen

Vaya a la [página principal](/es/) y suelte una imagen (PNG, JPG, JPEG, GIF,
BMP, WebP o TIFF). Dos ajustes opcionales cambian lo que se ejecuta:

- **Contraseña** — se reenvía a los analizadores que aceptan contraseña
  ([steghide](/es/wiki/tools/steghide), openstego, jpseek, outguess).
  Déjela vacía si no tiene ninguna frase de contraseña candidata; las
  herramientas se ejecutan entonces con una contraseña vacía, que es una
  configuración habitual en CTF.
- **Análisis profundo** — ejecuta además analizadores más lentos, como
  outguess.

El análisis suele completarse en cuestión de segundos; las imágenes pesadas
o una cola cargada pueden tardar más. La URL de la página de resultados es
estable y se puede compartir: la misma imagen enviada con las mismas
opciones devuelve la misma página al instante.

## Leer los resultados

Los resultados se agrupan por analizador, siempre en el mismo orden:

1. **Los planos de bits y la reasignación de colores** aparecen primero
   porque son visuales: examine las imágenes generadas en busca de
   contornos, texto o códigos QR que aparezcan en un único plano de bits.
2. **Las herramientas de archivo y metadatos** (`file`, `exiftool`,
   `identify`) revelan formatos que no coinciden, comentarios ocultos y
   rastros de edición.
3. **Las herramientas de carving** (`binwalk`, `foremost`) listan los
   archivos incrustados dentro de la imagen; cuando se encuentra algo, un
   botón de descarga proporciona un `.7z` con los archivos extraídos.
4. **Los extractores de esteganografía** (`zsteg`, `steghide`, `jpseek`,
   `jsteg`, `openstego`, `outguess`) intentan extraer la carga propiamente
   dicha. Un bloque rojo es normal: simplemente significa que esa
   herramienta no encontró nada con la contraseña indicada.

## Privacidad y retención

Los envíos se almacenan temporalmente (3 días por defecto) para que los
resultados puedan compartirse, y después se eliminan automáticamente. Si
subió una imagen por error, puede eliminarla usted mismo desde la página de
resultados tras un breve plazo, siempre que solo se haya subido desde su
propia dirección IP.

## Para ir más lejos

Recorra la [cheatsheet](/es/wiki/cheatsheet) para conocer técnicas que
ninguna herramienta automática cubre, y lea las páginas de cada herramienta
para ejecutar el mismo análisis en local sobre archivos que Aperi'Solve no
admite.
