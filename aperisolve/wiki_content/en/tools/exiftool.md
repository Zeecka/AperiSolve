Title: exiftool - Read Image Metadata (EXIF, XMP, IPTC)
Description: How exiftool reveals metadata in images, how Aperi'Solve runs it including unknown tags, and which fields commonly hide CTF flags.
Order: 130

# exiftool

[ExifTool](https://exiftool.org/) reads (and writes) metadata in virtually
every image format: EXIF, XMP, IPTC, ICC profiles, maker notes and dozens of
proprietary blocks. Metadata is the single most common hiding spot for CTF
flags.

## What Aperi'Solve runs

```console
$ exiftool -a -u -g1 image.jpg
```

- `-a` shows duplicated tags instead of hiding them.
- `-u` shows **unknown** tags — where hand-crafted data usually hides.
- `-g1` groups the output by metadata block.

## Fields worth reading first

| Field | Why it matters |
|-------|----------------|
| `Comment` / `UserComment` | Free-text fields, the classic flag location |
| `Artist`, `Author`, `Copyright`, `Software` | Free-text, often overlooked |
| `ImageDescription`, `XPTitle`, `XPComment` | More free-text variants |
| `GPS*` | Coordinates can encode a location-based hint |
| `ThumbnailImage` | The embedded thumbnail may differ from the visible image |
| Unknown tags (`-u`) | Arbitrary attacker/author-controlled data |

## Extracting binary metadata

Some fields contain whole files (thumbnails, ICC profiles):

```console
$ exiftool -b -ThumbnailImage image.jpg > thumb.jpg
$ exiftool -b -ICC_Profile image.jpg > profile.icc
```

## Installing locally

```console
$ apt install libimage-exiftool-perl
```

## Common CTF patterns

- Base64 in `Comment` — decode anything that looks like `Zmxh...`.
- A flag split across several metadata fields.
- The thumbnail shows the *original* image before sensitive content was
  cropped or masked.
- Timestamps/GPS encoding a puzzle (dates as ASCII codes, coordinates
  pointing at a place name).
