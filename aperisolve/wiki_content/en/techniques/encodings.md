Title: Encodings & Obfuscation - Recognize and Decode a Recovered Payload
Description: A recognition-and-decoding reference for CTF payloads: base64/32/16 and other bases, binary and integer text, XOR and classical ciphers (Caesar/ROT, Vigenere, Atbash, rail fence), Morse and Braille, QR and barcodes, and CyberChef Magic for nested chains.
Order: 60

# Encodings & obfuscation

Steganography usually gives you *something* — a blob of text or bytes — that is
**not yet the flag**. Recognizing what it is and peeling the layers is a skill
of its own, and the same encodings recur everywhere: in
[LSB](/wiki/techniques/images) output, in [audio](/wiki/techniques/audio) signal
decodes, in [text](/wiki/techniques/text) files and in carved
[archives](/wiki/techniques/files-archives). This page is the shared
recognition-and-decoding reference those pages point to.

The golden rule: when in doubt, paste it into
[CyberChef](https://gchq.github.io/CyberChef/) and run **Magic** — it identifies
and unwraps most of what follows automatically. Use this page to recognize by
eye and to reach for the exact decoder when Magic stalls.

## Recognize it by its shape

| Tell (what you see)                                   | Likely encoding |
|-------------------------------------------------------|-----------------|
| `A–Z a–z 0–9 + /`, length ÷ 4, `=` padding            | **Base64** |
| `A–Z 2–7`, `=` padding, all uppercase                 | **Base32** |
| `0–9 a–f` only, even length                           | **Hex** |
| Only `0` and `1`, in 7/8-bit groups                   | **Binary** ASCII |
| One long run of digits                                | **Decimal / big integer** (try other bases) |
| `.` and `-` (or two repeated tokens)                  | **Morse** |
| `⠿`-style dot glyphs (U+2800 block)                   | **Braille** |
| Printable ASCII shifted / rotated                     | **Caesar / ROT13 / ROT47** |
| `begin 644 …` header                                  | **uuencode** |
| `<~ … ~>` or `A–Za-z!–u`                              | **Ascii85 / Base85** |
| Perfect-square byte count, black/white                | a **QR code** image |
| Only `+-<>[].,`                                        | **Brainfuck** ([esolang](/wiki/techniques/text#esoteric-languages)) |

## Bases and numeric text

```console
$ echo 'aGVsbG8=' | base64 -d                 # base64
$ echo 'NBSWY3DP' | base32 -d                  # base32
$ echo '68656c6c6f' | xxd -r -p               # hex -> bytes
$ echo '01101000 01101001' | perl -lpe '$_=pack"B*",join"",split" "'   # binary -> ASCII
```

- **Base64 variants:** URL-safe base64 swaps `+/` for `-_`; base64 sometimes
  wraps another layer (base64 → gzip, base64 → base64). Iterate.
- **A big integer** may be bytes in disguise: convert with
  `python3 -c "import sys;n=int(sys.argv[1]);print(n.to_bytes((n.bit_length()+7)//8,'big'))" <n>`,
  and try bases 2/8/16 if decimal is gibberish.
- **uudecode** (`begin 644 name`) and **Ascii85** are handled by CyberChef
  *From UUEncoding* / *From Base85*.

!!! tip "Peel nested chains with CyberChef Magic"
    Real challenges stack layers (base64 → hex → reversed → base32). CyberChef
    *Magic* with **Intensive mode** brute-forces the chain and stops when a
    flag-like string appears. Feed it the raw blob and read the branch that
    surfaces `CTF{`/printable text.

## XOR and classical ciphers

When a blob decodes to fixed-length bytes that still look random, it is often
**XOR** or a **classical cipher**:

- **Single-byte XOR** — brute-force all 256 keys and score for printable/flag
  text (CyberChef *XOR Brute Force*, or `xortool` for repeating keys).
- **Repeating-key XOR** — `xortool -c 20 blob.bin` guesses the key length from
  byte frequency, then recovers the key.
- **Known-plaintext XOR** — if you know the output starts with `CTF{` or a PNG
  magic, XOR the ciphertext against the known bytes to leak the key.

```console
$ xortool -c 00 blob.bin                        # find key length + candidate keys
$ python3 -c "print(bytes(b^0x2a for b in open('blob.bin','rb').read()))"  # single-byte XOR
```

Classical ciphers show up as readable-but-scrambled letters:

| Cipher | Tell | Decode |
|--------|------|--------|
| **Caesar / ROT13 / ROT47** | uniform letter shift | `tr` / CyberChef *ROT13*, *ROT47* |
| **Atbash** | `a↔z` mirror | CyberChef *Atbash* |
| **Vigenère** | needs a keyword | [dcode Vigenère](https://www.dcode.fr/vigenere-cipher) (auto-solve) |
| **Substitution** | 1:1 letter map | [quipqiup](https://quipqiup.com/) frequency solver |
| **Rail fence / transposition** | right letters, wrong order | CyberChef *Rail Fence*, dcode |

[dcode.fr](https://www.dcode.fr/) has an auto-identifier and a decoder for
nearly every classical cipher — paste the text and let it guess.

## Morse and Braille

- **Morse** — a string of only `.`/`-`, or two repeated symbols (`10`, `ab`)
  standing in for dot/dash. Split on the separator and decode with CyberChef
  *From Morse Code* or [dcode Morse](https://www.dcode.fr/morse-code). Morse also
  hides in [audio waveforms](/wiki/techniques/audio) and GIF frame durations.
- **Braille** — Unicode Braille pattern glyphs (`⠓⠑⠇⠇⠕`, U+2800 block) decode
  with a [Braille translator](https://www.dcode.fr/braille-alphabet).

Both frequently yield a **password** for a later stage rather than the flag
itself.

## QR codes and barcodes

Extraction often produces an image that is itself a code:

```console
$ zbarimg --raw code.png                        # QR, DataMatrix, EAN, Code128...
$ convert code.png -resize 400% big.png && zbarimg --raw big.png   # upscale a tiny code
```

A broken QR can often be repaired by fixing the three finder patterns by hand;
a QR with a wrong ECC level may still decode after upscaling and thresholding.

## Esoteric languages

Unusual charsets that are actually *programs* — Brainfuck (`+-<>[].,`),
Whitespace, Piet (a colored image), Malbolge — are covered on the
[Text & Unicode page](/wiki/techniques/text#esoteric-languages), with the
[esolangs list](https://esolangs.org/wiki/Language_list) for identifying an
unknown one.

## Related

- Recovered the blob from an image, audio or text carrier? Go back to
  [Images](/wiki/techniques/images) · [Audio](/wiki/techniques/audio) ·
  [Text & Unicode](/wiki/techniques/text).
- The triage flow that gets you here:
  [Methodology](/wiki/methodology#6-near-stego-encodings).
- Drive a challenge from the [cheatsheet](/wiki/cheatsheet).
