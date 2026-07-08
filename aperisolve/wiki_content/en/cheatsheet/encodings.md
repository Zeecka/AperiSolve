Title: Encodings & Esolangs Cheatsheet - CyberChef, Base-N, Morse, QR
Description: A copy-paste reference for the encodings a recovered CTF payload turns out to be: base-N, hex, Morse, Braille, QR/barcodes, and esoteric languages - with CyberChef, dcode and command-line decoders for each.
NavTitle: Encodings
Order: 60

# Encodings & esolangs cheatsheet

You recovered *something* that is not yet the flag. Recognize the encoding and
decode it. When unsure, paste it into
[CyberChef](https://gchq.github.io/CyberChef/) and run the **Magic** operation —
it identifies and decodes most of the below automatically.

## Base-N & hex {: #base }

```console
$ echo "SGVsbG8=" | base64 -d
$ echo "NBSWY3DP" | base32 -d
$ echo "48656c6c6f" | xxd -r -p                 # hex → bytes
$ echo "Q0lZ..." | base64 -d | xxd | head       # decode then inspect bytes
```

- **base58 / base62 / base85 (ascii85/z85)** → CyberChef, or
  `python3 -c "import base64;print(base64.b85decode(b'...'))"`.
- **base-N of unknown radix / bacon / atbash / rot-N** →
  [dcode.fr](https://www.dcode.fr/) has a decoder per cipher; ROT13:
  `tr 'A-Za-z' 'N-ZA-Mn-za-m'`.

## Numbers, Morse & Braille {: #symbols }

- **Binary / decimal / octal ASCII** → group by 8 (binary) and convert; CyberChef
  *From Binary* / *From Decimal*.
- **Morse** (`.- -...`) → CyberChef *From Morse Code*, or
  [dcode Morse](https://www.dcode.fr/morse-code).
- **Braille** (`⠓⠑⠇⠇⠕` or `.`/`,` patterns) → CyberChef *From Braille*.
- **A blob whose length is a perfect square** → likely a **QR** bitmap; render it
  (below) rather than decode as text.

## QR codes & barcodes {: #qr }

```console
$ zbarimg --raw code.png                    # QR / EAN / Code128 / DataMatrix
$ zbarimg --raw -q code.png | xxd | head     # inspect binary QR payloads
```

Build a QR from a bitstring with an online QR-from-binary tool, or
`qrencode`/`segno` to test hypotheses.

## Ciphers & keys {: #ciphers }

- **XOR (single/multi-byte)** → CyberChef *XOR Brute Force*, or
  `xortool -c 20 payload.bin` to recover the key length and key.
- **Vigenère / substitution** → [quipqiup](https://quipqiup.com/) (mono-alphabetic),
  dcode Vigenère (with/without key).

## Esoteric languages {: #esolangs }

Recognize the source, then run an interpreter (mostly on
[tio.run](https://tio.run/)):

- **Brainfuck** — `+-<>[].,` only.
- **Whitespace** — only spaces/tabs/newlines (pairs with SNOW findings).
- **Malbolge** — dense, unreadable ASCII soup.
- **Piet** — a *picture*: blocks of 20 colors (decode with `npiet`).
- **Ook! / Rockstar / Chef** — word-based; identify via
  [esolangs.org language list](https://esolangs.org/wiki/Language_list).

!!! tip "Chained encodings"
    Payloads are often wrapped twice (base64 → hex → gzip). Decode one layer,
    `file`/`xxd` the result, and repeat. CyberChef *Magic* with "Intensive mode"
    follows several layers for you.

## Related

- Recover the payload first: [Text cheatsheet](/wiki/cheatsheet/text) ·
  [Image cheatsheet](/wiki/cheatsheet/image).
- Method: [Methodology → near-stego encodings](/wiki/methodology).
