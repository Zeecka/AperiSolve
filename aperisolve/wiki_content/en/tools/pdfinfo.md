Title: pdfinfo - Read PDF Metadata and Structure
Description: How the poppler pdfinfo tool reports a PDF's metadata, page count, version and encryption state, and what those fields reveal on a CTF challenge.
Order: 280

# pdfinfo

[pdfinfo](https://poppler.freedesktop.org/) (from the poppler suite) prints
the **document-level metadata** of a PDF: title, author, producer, creation
and modification dates, page count, PDF version, page size and whether the
file is encrypted. It is the quickest way to size up a PDF challenge.

## What Aperi'Solve runs

```console
$ pdfinfo document.pdf
```

The output is returned as a table of the non-blank lines.

## Reading the output

```
Title:           Annual Report
Author:          alice
Producer:        LibreOffice 7.4
CreationDate:    Sat Jul  5 12:00:00 2025 UTC
Pages:           3
Encrypted:       no
Page size:       612 x 792 pts (letter)
PDF version:     1.7
```

- **Author / Producer / Creator** — the tool that generated the file. A
  mismatch with the document's apparent origin, or a telling username, is a
  common early clue.
- **CreationDate / ModDate** — timestamps that can order events or expose a
  file that was edited after it was "signed".
- **Pages** — a blank-looking PDF with more pages than you can see hides
  content off-canvas or in a hidden layer.
- **Encrypted: yes** — the content stream is protected; you may need the
  password (or a permissions crack) before other tools can read it.

## Installing locally

```console
$ apt install poppler-utils
```

The same package provides `pdftotext`, `pdfimages` and `pdftk`-style
helpers for extracting the actual content.

## Limitations

- Reports only the document metadata, not the objects inside — for
  suspicious JavaScript, embedded files or auto-actions use
  [pdfid](/wiki/tools/pdfid), which also runs on your upload.
- Malformed or truncated PDFs may report nothing; poppler is fairly lenient
  but not a repair tool.

## Common CTF patterns

- A revealing `Author` or `Producer` string, or a comment left in the
  metadata.
- Extra pages beyond what a viewer shows, holding hidden text.
- `Encrypted: yes` pointing you toward a password/permissions puzzle before
  the flag is reachable.
