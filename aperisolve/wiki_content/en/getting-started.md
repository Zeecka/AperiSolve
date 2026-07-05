Title: Getting Started with Aperi'Solve
Description: How to upload an image on Aperi'Solve, use passwords and deep analysis, and interpret each analyzer's results.
Order: 10

# Getting started

## Uploading an image

Go to the [home page](/) and drop an image (PNG, JPG, JPEG, GIF, BMP, WebP
or TIFF). Two optional settings change what runs:

- **Password** — forwarded to the password-aware analyzers
  ([steghide](/wiki/tools/steghide), openstego, jpseek, outguess). Leave it
  empty when you have no candidate passphrase; tools then run with an empty
  password, which is a common CTF configuration.
- **Deep analysis** — additionally runs slower analyzers such as outguess.

Analysis usually completes within seconds; heavy images or a busy queue can
take longer. The result page URL is stable and shareable: the same image
submitted with the same options returns the same page instantly.

## Reading the results

Results are grouped per analyzer, in the same order every time:

1. **Bit planes and color remapping** come first because they are visual:
   scan the generated images for outlines, text or QR codes that appear in a
   single bit plane.
2. **File and metadata tools** (`file`, `exiftool`, `identify`) reveal
   mismatched formats, hidden comments and editing traces.
3. **Carving tools** (`binwalk`, `foremost`) list files embedded inside the
   image; when something is found, a download button provides a `.7z` of the
   extracted files.
4. **Steganography extractors** (`zsteg`, `steghide`, `jpseek`, `jsteg`,
   `openstego`, `outguess`) attempt actual payload extraction. A red block
   is normal: it simply means that tool found nothing with the given
   password.

## Privacy and retention

Uploads are stored temporarily (3 days by default) so results can be shared,
then deleted automatically. If you uploaded an image by mistake you can
remove it yourself from the result page after a short delay, provided it was
only uploaded from your own IP address.

## Going further

Work through the [cheatsheet](/wiki/cheatsheet) for techniques that no
automated tool covers, and read the per-tool pages to run the same analysis
locally on files Aperi'Solve does not support.
