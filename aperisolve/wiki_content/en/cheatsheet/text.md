Title: Text & Unicode Steganography Cheatsheet - Whitespace, Zero-Width
Description: A copy-paste command checklist for text steganography CTFs: whitespace/SNOW extraction, zero-width and tag-character Unicode smuggling, variation-selector emoji payloads, bidi and homoglyph tricks, with the exact tools to detect and decode each.
NavTitle: Text
Order: 30

# Text cheatsheet

Command recipes for plain-text and Unicode challenges. The tell is almost always
a **byte count larger than the visible text**, or text that "copies wrong".
Depth on the [Text & Unicode technique page](/wiki/techniques/text); for the
payload you recover, see the
[encodings cheatsheet](/wiki/cheatsheet/encodings).

## First checks {: #first }

```console
$ wc -c file.txt && wc -m file.txt        # bytes vs characters — a gap = hidden code points
$ cat -A file.txt                          # $ at line ends, ^I tabs, M-… high bytes
$ hexdump -C file.txt | less               # see the raw code points
```

## Whitespace encoding (SNOW) {: #whitespace }

Data in **trailing spaces and tabs** at line ends — invisible in most editors.

```console
$ cat -A file.txt                          # reveal trailing whitespace / tabs
$ stegsnow -C file.txt                      # extract, no password
$ stegsnow -p 'secret' -C file.txt          # extract with a password
```

## Zero-width characters {: #zero-width }

Zero-width space (U+200B), non-joiner (U+200C), joiner (U+200D) render as nothing
but carry bits.

```console
$ python3 -c "print([hex(ord(c)) for c in open('file.txt').read() if ord(c)>0x2000])"
```

Decode online: the
[330k zero-width decoder](https://330k.github.io/misc_tools/unicode_steganography.html);
AES-protected variant is [StegCloak](https://stegcloak.surge.sh/).

## Tag characters & variation selectors {: #tags }

- **Tag block (U+E0000–U+E007F)** → invisible ASCII smuggling; each tag char maps
  to a printable ASCII by masking `& 0x7F`. Emoji that "hold" hidden text use
  these.
- **Variation selectors (U+FE00–U+FE0F, U+E0100–U+E01EF)** → attach bytes to a
  carrier glyph; decode by reading the selector indices.

```console
$ python3 -c "s=open('f.txt').read(); print(''.join(chr(ord(c)&0x7f) for c in s if 0xE0000<=ord(c)<=0xE007F))"
```

## Bidi overrides & homoglyphs {: #homoglyphs }

- **Bidi controls (U+202A–U+202E, U+2066–U+2069)** → reorder displayed text to
  hide/spoof content; grep for the code points.
- **Homoglyphs** (Latin `a` vs Cyrillic `а`, U+0430) → mixed-alphabet text; detect
  with an [Irongeek homoglyph decoder](https://www.irongeek.com/) or by listing
  non-ASCII code points.

```console
$ grep -nP "[^\x00-\x7F]" file.txt          # any non-ASCII characters
$ python3 -c "import unicodedata as u,sys; [print(hex(ord(c)),u.name(c,'?')) for c in open('f.txt').read() if ord(c)>127]"
```

!!! tip "Normalise, then diff"
    `python3 -c "import unicodedata;print(unicodedata.normalize('NFKC',open('f.txt').read()))"`
    collapses homoglyphs/compatibility forms — diff against the original to see
    exactly which characters were swapped.

## Related

- Tools: [stegsnow](/wiki/tools/stegsnow) · [strings](/wiki/tools/strings).
- Depth: [Text & Unicode technique page](/wiki/techniques/text).
- Decode the result: [Encodings & esolangs cheatsheet](/wiki/cheatsheet/encodings).
