Title: Bien démarrer avec Aperi'Solve
Description: Comment téléverser une image sur Aperi'Solve, utiliser les mots de passe et l'analyse approfondie, et interpréter les résultats de chaque analyseur.
Order: 10

# Bien démarrer

## Téléverser une image

Rendez-vous sur la [page d'accueil](/fr/) et déposez une image (PNG, JPG,
JPEG, GIF, BMP, WebP ou TIFF). Deux options facultatives modifient ce qui
est exécuté :

- **Mot de passe** — transmis aux analyseurs qui acceptent un mot de passe
  ([steghide](/fr/wiki/tools/steghide), openstego, jpseek, outguess).
  Laissez-le vide si vous n'avez pas de phrase de passe candidate ; les
  outils s'exécutent alors avec un mot de passe vide, une configuration
  courante en CTF.
- **Analyse approfondie** — exécute en plus des analyseurs plus lents comme
  outguess.

L'analyse se termine généralement en quelques secondes ; des images lourdes
ou une file d'attente chargée peuvent prendre plus de temps. L'URL de la
page de résultats est stable et partageable : la même image soumise avec
les mêmes options renvoie instantanément la même page.

## Lire les résultats

Les résultats sont regroupés par analyseur, toujours dans le même ordre :

1. **Les plans de bits et le remappage de couleurs** viennent en premier car
   ils sont visuels : parcourez les images générées à la recherche de
   contours, de texte ou de QR codes qui apparaissent dans un seul plan de
   bits.
2. **Les outils de fichier et de métadonnées** (`file`, `exiftool`,
   `identify`) révèlent les formats incohérents, les commentaires cachés et
   les traces d'édition.
3. **Les outils de carving** (`binwalk`, `foremost`) listent les fichiers
   embarqués dans l'image ; quand quelque chose est trouvé, un bouton de
   téléchargement fournit un `.7z` des fichiers extraits.
4. **Les extracteurs de stéganographie** (`zsteg`, `steghide`, `jpseek`,
   `jsteg`, `openstego`, `outguess`) tentent une extraction réelle de la
   charge utile. Un bloc rouge est normal : cela signifie simplement que
   l'outil n'a rien trouvé avec le mot de passe fourni.

## Confidentialité et conservation

Les images téléversées sont stockées temporairement (3 jours par défaut)
afin que les résultats puissent être partagés, puis supprimées
automatiquement. Si vous avez téléversé une image par erreur, vous pouvez
la supprimer vous-même depuis la page de résultats après un court délai, à
condition qu'elle n'ait été téléversée que depuis votre propre adresse IP.

## Aller plus loin

Parcourez la [cheatsheet](/fr/wiki/cheatsheet) pour les techniques
qu'aucun outil automatisé ne couvre, et lisez les pages dédiées à chaque
outil pour lancer la même analyse en local sur des fichiers qu'Aperi'Solve
ne prend pas en charge.
