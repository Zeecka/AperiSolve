Title: Passwords & Brute-Force Cheatsheet - stegseek, John, fcrackzip
Description: A copy-paste command checklist for cracking steganography and archive passphrases in CTFs: guess before brute-forcing, stegseek for steghide, John/hashcat for ZIP/PDF/Office, fcrackzip, and bkcrack known-plaintext, ordered by likelihood.
NavTitle: Brute-force
Order: 70

# Passwords & brute-force cheatsheet

When a payload is passworded, **guess before you brute-force** — then reach for
wordlists. Recipes below are ordered by likelihood of success.

## Guess first {: #guess }

The passphrase is very often one of these — try them (and their
lower/upper/leet variants) before any wordlist:

- the **filename** (with and without extension) and the **challenge name**;
- the image/audio **subject** or author;
- any string already in [`strings`](/wiki/tools/strings) /
  [`exiftool`](/wiki/tools/exiftool) output;
- the empty password `''` (the single most-forgotten step for steghide).

```console
$ steghide extract -sf image.jpg -p ''                 # always try this
$ for p in "$(basename image.jpg .jpg)" "$(cat clue.txt)"; do \
    steghide extract -sf image.jpg -p "$p" && break; done
```

## Wordlists {: #wordlists }

```console
$ ls -la /usr/share/wordlists/rockyou.txt              # the default CTF list
$ gunzip -k /usr/share/wordlists/rockyou.txt.gz        # if it's still gzipped
```

Generate a targeted list from page/challenge words when rockyou fails:
`cewl https://challenge.example -w words.txt`, or mangle with
`john --wordlist=words.txt --rules --stdout`.

## steghide (JPEG/BMP/WAV/AU) {: #steghide }

```console
$ stegseek image.jpg /usr/share/wordlists/rockyou.txt   # ~seconds on rockyou
$ stegseek --seed image.jpg                              # detect payload, no wordlist
```

[stegseek](/wiki/tools/stegseek) is far faster than the classic
`stegcracker`. On success it writes the passphrase and the extracted file.

## ZIP {: #zip }

```console
$ zip2john secret.zip > zip.hash && john --wordlist=rockyou.txt zip.hash
$ fcrackzip -u -D -p /usr/share/wordlists/rockyou.txt secret.zip   # -u verifies
$ fcrackzip -b -c 'a1' -l 1-6 secret.zip                            # brute force
```

- **ZipCrypto + known inner file** → skip cracking entirely, use a
  known-plaintext attack with `bkcrack` (see the
  [files cheatsheet](/wiki/cheatsheet/files#zip)).

## PDF / Office / other {: #other }

```console
$ pdf2john secret.pdf   > h && john --wordlist=rockyou.txt h
$ office2john secret.docx > h && john --wordlist=rockyou.txt h
$ john --show h                                        # print the cracked password
```

`*2john` helpers exist for RAR (`rar2john`), 7z (`7z2john.pl`), KeePass
(`keepass2john`), and more. For GPUs, feed the same hash to `hashcat` with the
matching mode (`hashcat --help | grep -i zip`).

## WPA handshakes {: #wpa }

```console
$ aircrack-ng -w rockyou.txt capture.pcap             # or hcxpcapngtool → hashcat -m 22000
```

!!! warning "Know when to stop"
    Strong crypto (AES-256 zip, modern Office, WPA3) will not fall to rockyou.
    If the "password" resists, re-read the challenge — the key is usually
    *findable* (a clue, a reused string, a known-plaintext file), not brute-forced.

## Related

- Tools: [stegseek](/wiki/tools/stegseek) · [steghide](/wiki/tools/steghide) ·
  [strings](/wiki/tools/strings) · [exiftool](/wiki/tools/exiftool).
- Archives & known-plaintext: [Files & Archives cheatsheet](/wiki/cheatsheet/files).
