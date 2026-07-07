Title: Text & Unicode Steganography - Whitespace, Zero-Width & Homoglyphs
Description: How data hides in plain text: whitespace encoding with SNOW, zero-width Unicode characters, homoglyph substitution, exotic encodings, and esoteric programming languages - with the tools to detect and decode each.
Order: 30

# Text & Unicode steganography

Plain text looks like the last place to hide data, which is exactly why it
works. The payload lives in characters you cannot see — trailing whitespace,
zero-width code points, or letters that look identical but are not. The tell is
almost always a **byte count larger than the visible text**, or text that
"copies wrong".

[TOC]

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

- Inspect code points with `xxd` / `cat -A`, or paste into an online
  zero-width decoder (330k Unicode Steganography, StegCloak).
- Compare `wc -c file.txt` to the number of characters you can actually see —
  a large gap means hidden code points.

```python
# List every non-ASCII or whitespace code point and its position
import sys
for i, ch in enumerate(sys.stdin.read()):
    if ord(ch) > 127 or ch.isspace():
        print(i, hex(ord(ch)), repr(ch))
```

## Homoglyphs

Different Unicode code points can look identical — Latin `a` (U+0061) versus
Cyrillic `а` (U+0430). Mixing them encodes data or watermarks the text. An
[Irongeek homoglyph decoder](https://www.irongeek.com/i.php?page=security/unicode-steganography-homoglyph-encoder)
recovers the message.

!!! warning "Normalize carefully"
    When you clean up suspicious text, keep a copy of the original — Unicode
    normalization destroys exactly the code points that carry the payload.

## Exotic encodings

Recovered a blob that is not yet a flag? Recognize the encoding:

- ASCII in **8-bit binary** blocks starts each letter with `0`; strip it and you
  have 7-bit blocks. Text may also be a single big integer (sometimes in a
  non-decimal base).
- **[CyberChef](https://gchq.github.io/CyberChef/)** with the *Magic* operation
  detects most base-N, hex and cipher encodings automatically. A charset change
  (monoalphabetic substitution, base change) is sometimes needed.

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
