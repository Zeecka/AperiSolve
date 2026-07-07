Title: stegseek - Fast steghide Passphrase Cracker
Description: How stegseek brute-forces a steghide passphrase against a wordlist in seconds, its seed mode for detecting payloads, how to run it locally, and the CTF patterns where it wins.
Order: 115

# stegseek

[stegseek](https://github.com/RickdeJager/stegseek) is the fastest known
[steghide](/wiki/tools/steghide) passphrase cracker — it runs the whole of
`rockyou.txt` in a couple of seconds (benchmarked thousands of times faster than
StegCracker or Stegbrute). It is the modern replacement for the older cracking
tools you will still see in writeups.

!!! note "A companion tool, not an Aperi'Solve analyzer"
    Aperi'Solve runs [steghide](/wiki/tools/steghide) with the single password
    you provide. When you have no candidate password, crack it locally with
    stegseek, then re-run the extraction.

## Cracking a passphrase

```console
$ stegseek file.jpg /usr/share/wordlists/rockyou.txt
```

On a hit, stegseek prints the passphrase and writes the embedded file to
`file.jpg.out`. Point `-wl` at a bigger list (crackstation, custom) if rockyou
fails.

## Seed mode (detect without a password)

steghide can be used with encryption disabled; stegseek's seed mode detects and
extracts such payloads without any wordlist:

```console
$ stegseek --seed file.jpg
```

## Guess before you brute-force

The passphrase is frequently sitting in plain sight — the filename, the
challenge title, the image subject, or a value in
[strings](/wiki/tools/strings) / [exiftool](/wiki/tools/exiftool) output. Try
those first, and confirm data is even present with `steghide info file.jpg`.

## Installing locally

```console
$ # Debian/Ubuntu: grab the .deb from the releases page
$ wget https://github.com/RickdeJager/stegseek/releases/latest/download/stegseek.deb
$ sudo apt install ./stegseek.deb
```

## Limitations

- Cracks **steghide** only (JPEG/BMP/WAV/AU). For other schemes use their own
  extractors — see [Images](/wiki/techniques/images) and
  [Audio](/wiki/techniques/audio).
- A password outside your wordlist will not be found; escalate to a larger list
  or generate a targeted one (CeWL from the challenge site, `crunch`).

## Common CTF patterns

- JPEG with a payload and no obvious password → `stegseek file.jpg rockyou.txt`.
- steghide with encryption disabled → `stegseek --seed`.
- The tool is so fast it is worth running speculatively on any JPEG/WAV before
  assuming it is clean.
