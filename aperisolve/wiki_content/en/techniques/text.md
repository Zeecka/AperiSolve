Title: Text & Unicode Steganography - Whitespace, Zero-Width & Homoglyphs
Description: How data hides in plain text: whitespace (SNOW), zero-width Unicode, tag-character ASCII smuggling, variation-selector emoji smuggling, bidi overrides, homoglyphs, exotic encodings and esolangs - with the tools to detect and decode each.
Order: 30

# Text & Unicode steganography

Plain text looks like the last place to hide data, which is exactly why it
works. The payload lives in characters you cannot see — trailing whitespace,
zero-width code points, or letters that look identical but are not. The tell is
almost always a **byte count larger than the visible text**, or text that
"copies wrong".

## Whitespace encoding (SNOW)

Data is encoded in **trailing spaces and tabs** at the end of lines — invisible
in most editors.

- **Reveal it:** `cat -A file.txt` shows `$` at line ends and `^I` for tabs;
  VS Code's *Render Whitespace* does the same visually.
- **Extract it:** [stegsnow](/wiki/tools/stegsnow) implements the SNOW scheme
  (up to 7 spaces + a tab per column group, optional password):

```console
$ stegsnow -C file.txt                 # extract, no password
$ stegsnow -p 'secret' -C file.txt     # extract with a password
```

## Zero-width characters

Zero-width space (U+200B), non-joiner (U+200C) and joiner (U+200D) render as
nothing but carry bits. Two zero-width characters → binary → bytes.

- Inspect code points with `xxd` / `cat -A`, or paste into the
  [330k zero-width decoder](https://330k.github.io/misc_tools/unicode_steganography.html);
  the AES-protected variant is [StegCloak](https://stegcloak.surge.sh/).
- Compare `wc -c file.txt` to the number of characters you can actually see —
  a large gap means hidden code points.

```python
# List every non-ASCII or whitespace code point and its position
import sys
for i, ch in enumerate(sys.stdin.read()):
    if ord(ch) > 127 or ch.isspace():
        print(i, hex(ord(ch)), repr(ch))
```

## Tag characters, variation selectors and bidi

The same "invisible character" idea has several modern variants. Run the
code-point dump above first, then match the ranges you find:

- **Unicode tag block (U+E0000)** — "ASCII smuggling". Deprecated tag characters
  U+E0020–U+E007F map 1:1 to ASCII with offset `0xE0000` (so `A` → U+E0041). They
  render as nothing but are read by parsers and LLMs. Decode with
  [ASCII Smuggler](https://embracethered.com/blog/ascii-smuggler.html).

```python
# Tag characters -> ASCII
print("".join(chr(ord(c) - 0xE0000) for c in text if 0xE0000 <= ord(c) <= 0xE007F))
```

- **Variation selectors (emoji smuggling)** — any byte can ride on a single base
  character: bytes 0–15 → U+FE00…U+FE0F, bytes 16–255 → U+E0100…U+E01EF. One
  visible glyph (😀, `a`, …) can carry an arbitrary byte string. Decode with
  [Paul Butler's tool](https://emoji.paulbutler.org/?mode=decode).
- **Sneaky bits** — invisible-math operators: ASCII→binary with `0` → U+2062
  (invisible times) and `1` → U+2064 (invisible plus). Map the two symbols back
  to bits.
- **Bidirectional override (RLO)** — U+202E / U+202D and the isolates
  U+2066–U+2069 reorder how text *displays* versus how it is *stored* (the
  "Trojan Source" trick, CVE-2021-42574). Detect with `hexdump -C` or
  `grep -P '[\x{202a}-\x{202e}\x{2066}-\x{2069}]'`, then strip them to read the
  true logical order.

## Homoglyphs

Different Unicode code points can look identical — Latin `a` (U+0061) versus
Cyrillic `а` (U+0430). Mixing them encodes data or watermarks the text. An
[Irongeek homoglyph decoder](https://www.irongeek.com/i.php?page=security/unicode-steganography-homoglyph-encoder)
recovers the message.

!!! warning "Normalize carefully"
    When you clean up suspicious text, keep a copy of the original — Unicode
    normalization destroys exactly the code points that carry the payload.

## Exotic encodings

Recovered a blob that is not yet a flag? The
[Encodings & obfuscation](/wiki/techniques/encodings) page is the full
recognition-and-decoding reference (bases, XOR, classical ciphers, Morse,
Braille, QR); the essentials for text blobs:

- ASCII in **8-bit binary** blocks starts each letter with `0`; strip it and you
  have 7-bit blocks. Text may also be a single big integer (sometimes in a
  non-decimal base).
- **Braille** — Unicode Braille pattern glyphs (U+2800 block, `⠿`) decode with a
  [Braille translator](https://www.dcode.fr/braille-alphabet). **Morse** — a
  string of only `.`/`-` (or two repeated tokens); CyberChef *From Morse Code*.
  Both frequently yield a *password* for a later stage rather than the flag.
- **[CyberChef](https://gchq.github.io/CyberChef/)** with the *Magic* operation
  (enable *Intensive mode*) auto-detects and peels **nested** encoding chains
  (base64 → base32 → hex → …) — iterate until the flag prefix appears.

```text
python2> "48656c6c6f20776f726c6421".decode("hex")   # -> "Hello world!"
```

## Esoteric languages

Esolangs have unusual charsets that stand out in a file. The ones seen most in
CTF:

- **[Brainfuck](https://esolangs.org/wiki/Brainfuck)** — only `+-<>[].,`
- **[Whitespace](https://esolangs.org/wiki/Whitespace)** — only spaces, tabs,
  newlines (overlaps with whitespace stego above)
- **[Piet](https://esolangs.org/wiki/Piet)** — the *program is an image* of
  colored blocks
- **[Malbolge](https://esolangs.org/wiki/Malbolge)** — deliberately unreadable

```text
brainfuck>
++++++++++[>+>+++>+++++++>++++++++++<<<<-]>>>++.>+.+++++++..+++.
```

[![Piet program](/static/img/cheatsheet/piet.png)](https://esolangs.org/wiki/Piet)

The [esolangs language list](https://esolangs.org/wiki/Language_list) helps
identify an unknown one.

## Related

- Drive a challenge from the [cheatsheet](/wiki/cheatsheet#text).
- Whitespace also appears in source files and archives —
  [Files & Archives](/wiki/techniques/files-archives).
