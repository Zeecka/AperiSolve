Title: stegsnow - Whitespace Steganography (SNOW)
Description: How stegsnow hides and extracts data in the trailing whitespace of text using the SNOW scheme, how to reveal whitespace, run it locally, and the CTF patterns where whitespace stego shows up.
Order: 260

# stegsnow

[stegsnow](https://www.kali.org/tools/stegsnow/) (the SNOW scheme by Matthew
Kwan) hides data in the **trailing whitespace** of text — appending spaces and
tabs at the end of lines, where they are invisible in almost every viewer. It
encodes roughly three bits per eight columns and can optionally compress and
password-protect the payload.

!!! note "A companion tool, not an Aperi'Solve analyzer"
    stegsnow is for text carriers, which Aperi'Solve does not process. Use it by
    hand when a `.txt`, README or source file is suspiciously large or copies
    "wrong".

## Revealing whitespace first

Before extracting, confirm there is hidden whitespace:

```console
$ cat -A file.txt        # spaces stay blank, tabs show as ^I, line ends as $
$ wc -c file.txt         # compare to the visible character count
```

Trailing `^I`/spaces before each `$` are the tell.

## Extracting

```console
$ stegsnow -C file.txt                 # extract (auto-decompress), no password
$ stegsnow -p 'secret' -C file.txt     # extract with a password
```

## Hiding (for building challenges / testing)

```console
$ stegsnow -C -m "hidden message" -p "secret" cover.txt out.txt
```

`-m` is the message, `-C` enables compression, `-p` sets the password.

## Installing locally

```console
$ sudo apt install stegsnow        # Kali/Debian; part of the "snow" package
```

## Limitations

- Works on **text** carriers only. For zero-width Unicode or homoglyph hiding,
  see the [Text & Unicode techniques](/wiki/techniques/text).
- Editors that strip trailing whitespace on save will destroy the payload —
  always work on an untouched copy.

## Common CTF patterns

- A `.txt` whose `wc -c` far exceeds its visible length → `stegsnow -C`.
- Whitespace stego is easy to miss; add `cat -A` to your standard text checklist.
- Overlaps with the [Whitespace](https://esolangs.org/wiki/Whitespace) esolang —
  if `cat -A` shows only spaces/tabs/newlines, consider both.
