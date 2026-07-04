Title: Wiki Aperi'Solve - Outils et guides de stéganographie
Description: Documentation d'Aperi'Solve : fonctionnement de l'analyse, guides pour chaque outil de stéganographie (zsteg, steghide, binwalk, exiftool...) et cheatsheet CTF.
Order: 1

# Wiki Aperi'Solve

Bienvenue sur le wiki d'Aperi'Solve. Aperi'Solve est une plateforme en ligne
gratuite qui effectue une analyse par calques et une détection de
stéganographie sur les images : déposez une image sur la
[page d'accueil](/fr/) et tous les analyseurs s'exécutent automatiquement.

Ce wiki documente comment lire les résultats et comment fonctionne chaque
outil sous-jacent, afin de pouvoir reproduire et prolonger l'analyse sur
votre propre machine.

## Par où commencer

- [Bien démarrer](/fr/wiki/getting-started) — comment utiliser Aperi'Solve
  et lire ses résultats.
- [Cheatsheet stéganographie CTF](/fr/wiki/cheatsheet) — une checklist
  pratique pour les épreuves sur les images, l'audio et les formats de
  fichiers.

## Guides des outils

Chaque analyseur exécuté sur votre image possède sa propre page : ce que
fait l'outil, la commande exacte lancée par Aperi'Solve, comment interpréter
la sortie et comment l'installer en local.

- [Décomposeur de plans de bits](/fr/wiki/tools/decomposer) — visualiser
  chaque bit de chaque canal de couleur.
- [Remappage de couleurs](/fr/wiki/tools/color_remapping) — révéler des
  données cachées grâce à des transformations de palette.
- [zsteg](/fr/wiki/tools/zsteg) — détection de stéganographie LSB pour PNG
  et BMP.
- [steghide](/fr/wiki/tools/steghide) — extraire des données cachées dans
  des JPEG/BMP avec une phrase de passe.
- [binwalk](/fr/wiki/tools/binwalk) — trouver et extraire des fichiers
  embarqués dans l'image.
- [foremost](/fr/wiki/tools/foremost) — extraire par carving les fichiers
  embarqués dans l'image.
- [exiftool](/fr/wiki/tools/exiftool) — lire les métadonnées (EXIF, XMP,
  IPTC...).
- [pngcheck](/fr/wiki/tools/pngcheck) — vérifier la structure d'un PNG et
  trouver les chunks corrompus.
- [PCRT](/fr/wiki/tools/pcrt) — détecter et réparer les fichiers PNG
  corrompus.
- [OutGuess](/fr/wiki/tools/outguess) — extraire des données cachées des
  images JPEG.
- [jsteg](/fr/wiki/tools/jsteg) — extraire les données LSB des coefficients
  DCT des JPEG.
- [JPHide/JPSeek](/fr/wiki/tools/jpseek) — extraire les charges utiles
  JPHide des JPEG.
- [OpenStego](/fr/wiki/tools/openstego) — extraire la stéganographie LSB
  randomisée.
- [identify](/fr/wiki/tools/identify) — inspecter les propriétés d'une
  image avec ImageMagick.
- [file](/fr/wiki/tools/file) — identifier le vrai type de fichier d'un
  envoi.
- [strings](/fr/wiki/tools/strings) — trouver le texte lisible dans les
  fichiers image.

Les contributions sont les bienvenues sur
[GitHub](https://github.com/Zeecka/AperiSolve).

## Qu'est-ce que la stéganalyse ?

La stéganographie cache des données dans un fichier porteur anodin — pour
les images, cela passe par la manipulation des bits de pixels, des entrées
de palette, des champs de métadonnées ou de la structure même du fichier.
La stéganalyse est l'art de détecter ces données cachées. Aucun outil ne
couvre toutes les techniques : c'est pourquoi Aperi'Solve exécute toute une
batterie d'analyseurs côte à côte et permet de comparer leurs sorties d'un
coup d'œil.
