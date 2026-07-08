Title: Files & Archives Steganography Cheatsheet - Carving, Polyglots, ZIP
Description: A copy-paste command checklist for file-structure CTFs: appended data and carving with binwalk/foremost, polyglot detection, ZIP/Office/PDF extraction, and known-plaintext ZIP cracking with bkcrack, ordered most-common first.
NavTitle: Files & Archives
Order: 40

# Files & Archives cheatsheet

Treat the file as a **structure** before touching pixels or samples. A huge share
of "stego" challenges are really file-format tricks. Depth on the
[Files & Archives technique page](/wiki/techniques/files-archives); passwords on
the [brute-force cheatsheet](/wiki/cheatsheet/brute-force).

## Appended & embedded data {: #appended }

```console
$ file target
$ tail -c 200 target | xxd            # inspect the trailer
$ binwalk target                       # list embedded signatures
$ binwalk -e target                    # auto-extract known signatures
$ foremost -i target -o out/           # header/footer carving when binwalk misses
```

The classic: a ZIP concatenated after an image — `unzip` reads the central
directory at the **end**, so it often just opens:

```console
$ unzip target          # or: 7z x target
$ 7z l target           # list contents without extracting
```

## Polyglots {: #polyglot }

A file valid under two parsers (PDF/ZIP, JPEG/ZIP, GIF/JS). `file` reads only the
start, so it will **not** flag them.

```console
$ binwalk target                       # multiple signatures at nonzero offsets
$ xxd target | grep -iE '25504446|504b0304|ffd8ff|47494638'   # PDF/ZIP/JPEG/GIF magic
```

Build/verify with [mitra](https://github.com/corkami/mitra) or
[truepolyglot](https://github.com/ansemjo/truepolyglot); Corkami's
[posters](https://github.com/corkami/pics) map where each format tolerates junk.

## ZIP archives {: #zip }

```console
$ 7z l target.zip                      # list; note encryption + compression method
$ unzip -l target.zip
```

- **Password-protected** → see the [brute-force cheatsheet](/wiki/cheatsheet/brute-force)
  (`zip2john` + `john`, or `fcrackzip`).
- **ZipCrypto + a known inner file** → known-plaintext attack, no password needed:

```console
$ bkcrack -L target.zip                # list entries + which are ZipCrypto
$ bkcrack -C target.zip -c secret.txt -P plain.zip -p plain.txt   # recover keys
$ bkcrack -C target.zip -k KEY0 KEY1 KEY2 -d out.txt              # decrypt
```

- **AES-256 zip** → not vulnerable to bkcrack; brute-force only.

## Documents (Office / PDF / Java / Android) {: #documents }

`.docx` / `.pptx` / `.xlsx` / `.jar` / `.apk` are ZIPs — unzip and inspect.

```console
$ 7z x report.docx -o docx/            # media/, embeddings/, and XML parts
$ grep -rInE 'flag|CTF|http' docx/
$ unzip -o app.apk -d apk/ && cat apk/AndroidManifest.xml
```

PDFs:

```console
$ pdfdetach -list target.pdf && pdfdetach -saveall target.pdf   # attachments
$ pdf-parser --search flag target.pdf          # objects/streams
$ pdfresurrect -w target.pdf                    # recover overwritten revisions
$ mutool extract target.pdf                      # dump embedded images/fonts
```

## Other containers {: #other }

- **SVG** → XML; a `<script>` or off-canvas `<text>` can hide the flag — open the
  source, not the render.
- **NTFS ADS** → `dir /R` (Windows) or `getfattr`/`7z` lists alternate streams.
- **`.git`** → `git log -p`, `git stash list`, and unreferenced objects
  (`git fsck --lost-found`) hide history.

## Related

- Tools: [binwalk](/wiki/tools/binwalk) · [foremost](/wiki/tools/foremost) ·
  [file](/wiki/tools/file) · [strings](/wiki/tools/strings).
- Depth: [Files & Archives technique page](/wiki/techniques/files-archives).
- Passwords: [Brute-force cheatsheet](/wiki/cheatsheet/brute-force).
- Captures: [Network / PCAP cheatsheet](/wiki/cheatsheet/network).
