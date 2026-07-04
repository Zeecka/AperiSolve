Title: Cheatsheet stéganographie CTF
Description: Cheatsheet de stéganographie pour joueurs de CTF : inspectez les fichiers PNG, JPEG, GIF et audio avec file, exiftool, zsteg, steghide, binwalk, foremost et plus encore.
Order: 20

# Cheatsheet

## Avertissement

Cette cheatsheet a pour but de guider les joueurs de CTF dans leurs recherches. Elle n'est pas représentative des techniques modernes de stéganographie/stéganalyse, et son contenu ne correspond pas à la création d'une épreuve intéressante 😉.

## Vérifier le type de fichier / les métadonnées

- Si vous ne connaissez pas l'extension du fichier, recherchez-la sur Internet. Vérifiez également le format du fichier.
- Utilisez la commande `file` pour vérifier que l'extension correspond au type du fichier. Cette commande se base sur les [Magic Bytes](https://en.wikipedia.org/wiki/List_of_file_signatures) au début du fichier ; elle peut donc renvoyer des faux positifs.

```console
$ file data.raw
```

- En cas d'extension et de fichier inconnus, inspectez la structure hexadécimale du fichier avec un éditeur comme [hexed.it](https://hexed.it/) afin d'identifier la structure du fichier.
- Affichez les métadonnées du fichier avec la commande `exiftool`.

```console
$ exiftool data.raw
```

## Modifier la structure du fichier {: #filestruct }

- Modifiez la structure du fichier avec un éditeur hexadécimal comme [hexed.it](https://hexed.it/). Les chunks PNG peuvent être facilement édités avec [TweakPNG](http://entropymine.com/jason/tweakpng/) (Windows ou Wine).

![TweakPNG](/static/img/cheatsheet/tweakpng.png)

- Vérifiez les sommes de contrôle du fichier. Il s'agit généralement de CRC32 ; des outils comme [PngCheck](http://www.libpng.org/pub/png/apps/pngcheck.html) ou [PCRT](https://github.com/sherlly/PCRT) sont utiles pour vérifier et corriger ces sommes de contrôle.

```console
$ pngcheck -c file.png
$ PCRT.py -v -i file.png
```

- Pour de nombreux types de fichiers (PNG, WAV, ...), la taille du média est contenue dans les en-têtes. Cette taille peut alors être réduite pour n'afficher qu'une partie du média (début d'une image, début d'un son, ...).

## Données brutes {: #rawdata }

- Il est possible d'importer un fichier brut dans [Audacity](https://www.audacityteam.org/download/) pour l'écouter comme une piste audio (Fichier > Importer > Données brutes).

![Audacity](/static/img/cheatsheet/audacity_raw.png)

- De même, l'outil [GIMP](https://www.gimp.org/downloads/) permet d'importer des images depuis des données brutes (Fichier > Ouvrir).
- L'outil [BinVis.io](http://binvis.io/) permet de visualiser graphiquement des fichiers binaires et peut donner des indices sur le type de fichier.
- La commande `strings` permet d'afficher les chaînes de caractères présentes dans un fichier.

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

- La robustesse d'une stéganographie repose sur l'algorithme utilisé et sur la connaissance du médium de couverture. Une recherche du média original permet de faire une comparaison et d'identifier les altérations effectuées. Une recherche inversée sur [Google Image](https://images.google.com/) ou [Yandex Images](https://yandex.com/images/) peut permettre de retrouver le média original (veillez à vérifier que la taille et le type du fichier correspondent).
- L'outil [Stegsolve](http://www.caesum.com/handbook/Stegsolve.jar) permet d'effectuer des opérations entre 2 images, et ainsi d'identifier les différences entre un médium de couverture et un médium stéganographié à l'aide de l'opération XOR.

![Stegsolve Xor](/static/img/cheatsheet/stegsolve_xor.png)
![Stegsolve Xor 2](/static/img/cheatsheet/stegsolve_xor2.png)

- L'outil [Zsteg](https://github.com/zed-0xff/zsteg) permet d'extraire des messages et des binaires encodés sur différentes couches, comme les 2 LSB du canal vert.

```console
$ zsteg file.png 2b,g,lsb,xy
$ zsteg file.png -E '1b,rgb,lsb'
```

- Parfois, l'analyse des plans de bits avec l'outil [Stegsolve](http://www.caesum.com/handbook/Stegsolve.jar) (ou Aperi'Solve) peut mettre en évidence des zones spécifiques qui ont été altérées. Un script peut alors être nécessaire pour extraire ces zones. Le code python suivant récupère une image sous forme de liste de pixels : [(100,120,43), (230, 124, 110), ...]

```python
# pip install Pillow
from PIL import Image
stegano_image = Image.open('file.png')
width, height = stegano_image.size
pxs = list(stegano_image.getdata())
print(pxs[:10])
```

- Les médiums stéganographiés peuvent reposer sur un algorithme utilisant une clé de chiffrement. C'est le cas de [Steghide](http://steghide.sourceforge.net/) et d'[OutGuess](https://github.com/resurrecting-open-source-projects/outguess). Le mot de passe peut être le nom du fichier, une chaîne de caractères contenue dans le fichier (`strings` & `exiftool`), ou l'objet représenté par l'image. Dans certains cas, le mot de passe ne peut pas être retrouvé et un bruteforce doit être effectué. Les outils [StegCracker](https://github.com/Paradoxis/StegCracker) et [Stegbrute](https://github.com/R4yGM/stegbrute) permettent le bruteforce des secrets cachés avec [Steghide](http://steghide.sourceforge.net/).

```console
$ steghide extract -p "secret" -sf file.jpg
$ stegcracker file.jpg /usr/share/wordlists/rockyou.txt
```

## PNG (Portable Network Graphics) {: #png }

- Les outils comme [Steghide](http://steghide.sourceforge.net/) et [OutGuess](https://github.com/resurrecting-open-source-projects/outguess) ne fonctionnent pas sur les fichiers PNG. En revanche, ce type de fichier permet une sauvegarde sans compression, et donc de cacher des messages sur les LSB. L'outil [Zsteg](https://github.com/zed-0xff/zsteg) présenté plus haut et disponible sur Aperi'Solve permet d'extraire des secrets des fichiers PNG.

```console
$ zsteg file.png 2b,g,lsb,xy
$ zsteg file.png -E '1b,rgb,lsb'
```

- Le PNG offre une extension [« APNG »](https://en.wikipedia.org/wiki/APNG) permettant d'avoir une animation d'images comme les fichiers GIF. Il est possible que la visualisation du PNG ne reflète pas tout son contenu (par exemple, une frame avec une durée nulle, ou une première frame très longue). L'outil [APNG Maker](https://ezgif.com/apng-maker) permet de visualiser les différentes frames d'un fichier APNG. Un message peut également être encodé sur les durées de chaque frame.

![APNG](https://upload.wikimedia.org/wikipedia/commons/1/14/Animated_PNG_example_bouncing_beach_ball.png)

- L'outil [TweakPNG](http://entropymine.com/jason/tweakpng/) présenté précédemment permet d'effectuer plusieurs types d'opérations comme recalculer les sommes de contrôle, réordonner les chunks PNG, augmenter la taille visible du PNG ou modifier un en-tête.

![TweakPNG](/static/img/cheatsheet/tweakpng.png)

## JPEG (Joint Photographic Experts Group) {: #jpg }

- L'outil [Zsteg](https://github.com/zed-0xff/zsteg) ne fonctionne pas sur les fichiers JPEG (jpg, jpeg, ...) car ces derniers incluent nécessairement un algorithme de compression réduisant la qualité de l'image et altérant les LSB. En revanche, les outils [Steghide](http://steghide.sourceforge.net/) et [OutGuess](https://github.com/resurrecting-open-source-projects/outguess) présentés plus haut sont compatibles avec ce format de fichier.

```console
$ outguess -k secret file.jpg output.raw
$ steghide extract -p "secret" -sf file.jpg
```

## GIF (Graphics Interchange Format) {: #gif }

- Les GIF sont généralement des images animées dont le format est le plus souvent mal pris en charge par les outils de stéganalyse. De plus, ce format d'image offre généralement une palette de couleurs ne dépassant pas 256 couleurs, contre 16 millions pour le PNG (hors transparence). L'outil [GIF Maker](https://ezgif.com/maker) permet cependant de manipuler facilement les fichiers GIF.
- Les GIF peuvent embarquer des images (frames) avec une durée nulle. Celles-ci ne seront alors pas visibles sans une analyse de chaque frame.

![GIF Maker](/static/img/cheatsheet/gif_maker.png)

- Un message caché peut être encodé sur la durée des frames (morse, ascii, binaire, ...).
- [Ffmpeg](https://ffmpeg.org/) peut être utilisé pour extraire les frames d'un GIF. L'exhaustivité des frames extraites ne peut pas être garantie.

```console
$ ffmpeg -i file.gif -vsync 0 output/file%d.png
```

## Audio {: #audio }

- La technique la plus courante pour les fichiers audio repose sur le spectre sonore. En effet, il est possible de dessiner un message visible sur le spectre audio avec des outils comme [Coagula](https://www.abc.se/~re/Coagula/Coagula.html). Ce spectre peut ensuite être analysé à l'aide d'outils d'analyse spectrale comme [Sonic Visualiser](https://www.sonicvisualiser.org/), [Audacity](https://www.audacityteam.org/) ou l'outil en ligne [dcode](https://www.dcode.fr/spectral-analysis).

![Spectre Audacity](/static/img/cheatsheet/audacity_1.png)

Il peut être nécessaire de faire un clic droit sur l'échelle pour dézoomer et visualiser l'ensemble du spectre, ou de passer en mode logarithmique.

![Spectre Audacity](/static/img/cheatsheet/audacity_2.png)

- Des fréquences inaudibles peuvent être utilisées pour cacher des messages. Une analyse spectrale au-delà de 20 kHz et en dessous de 20 Hz est recommandée ; un message encodé en morse ou en binaire peut s'y cacher.
- Les sons sont de simples signaux de télécommunication qui peuvent être utilisés à d'autres fins. Des méthodes d'encodage particulières peuvent être employées, comme le [code DTMF](https://en.wikipedia.org/wiki/Dual-tone_multi-frequency_signaling) autrefois utilisé en téléphonie ou la [SSTV](https://en.wikipedia.org/wiki/Slow-scan_television) utilisée en télévision pour le transfert d'images. Ces signaux sont encodés sur des fréquences audibles mais leur interprétation nécessite des décodeurs particuliers. On optera alors pour un [décodeur DTMF](http://dialabc.com/sound/detect/) pour la première technique, et un décodeur SSTV comme [QSSTV](https://doc.ubuntu-fr.org/qsstv) pour la seconde.
- Tout comme les fichiers PNG, certains fichiers audio embarquent leur taille théorique dans leurs en-têtes. C'est notamment le cas des [fichiers WAV](https://fr.wikipedia.org/wiki/Waveform_Audio_File_Format#En-t%C3%AAte_de_fichier_WAV) dont le bloc DataSize peut être diminué ou augmenté à l'aide d'un éditeur hexadécimal.
- La technique LSB peut être utilisée sur certains fichiers audio. Il faut alors extraire les LSB des données audio ; l'outil [WavSteg](https://github.com/ragibson/Steganography#WavSteg) permet d'effectuer cette manipulation sur les fichiers WAV.

```console
$ stegolsb wavsteg -r -i file.wav -o output.txt -n 1 -b 1000
```

- Les outils [Steghide](http://steghide.sourceforge.net/) et [DeepSound](http://jpinsoft.net/deepsound/overview.aspx) sont couramment utilisés en CTF pour cacher des messages. Ceux-ci peuvent prendre une clé en paramètre ; il faudra donc deviner cette clé à partir des informations disponibles (média, nom du fichier, nom de l'épreuve, etc.) ou en utilisant une wordlist.

![DeepSound](/static/img/cheatsheet/DeepSound.png)

## Fichiers polyglottes {: #polyglot }

Il s'agit d'un type de fichier qui est valide pour plusieurs formats de fichiers. Par exemple un fichier image qui peut donc être visualisé et qui est également un fichier jar (qui peut être exécuté). Il existe plusieurs types de fichiers polyglottes :

- Polyglotte « simple » : il s'agit d'une simple concaténation de fichiers ;
- Polyglotte « parasite » : il s'agit d'un fichier qui contient un autre type de fichier.
- Polyglotte « mille-feuilles » : les couches sont alternées en contrôlant la structure interne du fichier.
- Polyglotte « chimère » : le fichier possède un corps (les données) et plusieurs têtes. Puisque plusieurs formats utilisent le même algorithme pour stocker les données, comme le Deflate de Zlib, le même bloc de données est utilisé par différents en-têtes (par exemple, les pixels d'une image). Plusieurs en-têtes sont présents afin que cette image soit visible via plusieurs formats (jpg, png, ...), au sein d'un même fichier.
- Fichiers « schizophrènes » : il s'agit d'un seul type de fichier, mais son contenu est interprété différemment selon l'outil qui l'exécute ou qui y accède. Ce sont généralement des fichiers PDF (interprétation ou non du javascript) ou des images (comme la technique du [Gamma](https://carlmastrangelo.com/blog/gamma-steganography)).
- Angecryption : le résultat du chiffrement ou du déchiffrement d'un fichier donne un autre fichier valide du même type ou d'un type différent :

![Angecryption](/static/img/cheatsheet/Angecryption.png)

- Les fichiers docx, jar, apk, pptx, odf... sont des archives valides et peuvent être décompressés. Il faut alors vérifier si le fichier en question peut être ouvert avec un autre outil que celui associé à son extension. La commande `file` n'identifie pas les fichiers polyglottes.

## Encodage et langages exotiques {: #text }

- Un texte ASCII peut être encodé en binaire par blocs de `8 bits` ; il est alors facilement identifiable car chaque bloc correspondant à une lettre commence par un 0. Il est possible de supprimer ce 0, les blocs ne font alors plus que `7 bits`. Le texte peut aussi être codé sur un entier de type `long` (parfois dans une base autre que la base 10) ; par exemple la chaîne de caractères « Hello world! » encodée sur un type long en base 10 peut être décodée avec le code python 2 suivant :

```console
python2> hex(22405534230753963835153736737L)[2:].strip('L').decode("hex")
python2> "48656c6c6f20776f726c6421".decode("hex")
```

- Des outils comme [CyberChef](https://gchq.github.io/CyberChef/) (et son option « magic ») peuvent aider à détecter l'encodage utilisé et à décoder le message caché. Parfois, un changement de charset peut être nécessaire (substitution monoalphabétique, ou changement de base).
- Les langages exotiques ou ésotériques sont des langages de programmation conçus pour être uniques, difficiles à programmer, ou tout simplement bizarres. Leur conception et leurs jeux de caractères peuvent être particuliers ; c'est le cas des langages les plus rencontrés en CTF comme [BrainFuck](https://esolangs.org/wiki/Brainfuck), [WhiteSpace](https://esolangs.org/wiki/Whitespace), [PIET](https://esolangs.org/wiki/Piet) ou [Malbolge](https://esolangs.org/wiki/Malbolge). Le site [EsoLang](https://esolangs.org/wiki/Language_list) référence ces différents langages et peut être utile dans vos recherches.

```console
brainfuck>
++++++++++[>+>+++>+++++++>++++++++++<<<<-]>>>++.>+.+++++++..+++.<<++.>>++++++++.--------.+++.------.--------.<<+.

malbolge>
('&%:9]!~}|z2Vxwv-,POqponl$Hjig%eB@@>}=<M:9wv6WsU2T|nm-,jcL(I&%$#"
`CB]V?Tx<uVtT`Rpo3NlF.Jh++FdbCBA@?]!~|4XzyTT43Qsqq(Lnmkj"Fhg${z@>
```

[![PIET](/static/img/cheatsheet/piet.png)](https://esolangs.org/wiki/Piet)

## Pour aller plus loin {: #more }

- [Blog d'Aperi'Kube - Catégorie stéganographie](https://www.aperikube.fr/cat/steg/)
- [CTF Time - Writeups (Stégano)](https://ctftime.org/writeups)
- [Corkami](http://corkami.github.io/)
- [Root-Me - Stéganographie](https://www.root-me.org/en/Challenges/Steganography/)
- [Stéréogramme](https://en.wikipedia.org/wiki/Autostereogram)
