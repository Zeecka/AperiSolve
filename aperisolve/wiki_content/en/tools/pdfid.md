Title: pdfid - Triage Suspicious PDF Objects
Description: How Didier Stevens' pdfid counts the risky keywords in a PDF (JavaScript, OpenAction, Launch, embedded files) so you can spot a weaponized or data-carrying document fast.
Order: 290

# pdfid

[pdfid](https://blog.didierstevens.com/programs/pdf-tools/) by Didier
Stevens scans a PDF for a fixed list of **potentially dangerous keywords**
and prints how many times each appears. It does not execute or fully parse
the document, so it is a safe first-pass triage: one glance tells you
whether a PDF merely holds text or is actively trying to do something.

## What Aperi'Solve runs

```console
$ pdfid document.pdf
```

The counts are returned as a table of the non-blank lines.

## Reading the output

```
PDFiD 0.2.8 document.pdf
 PDF Header: %PDF-1.7
 obj                    8
 endobj                 8
 stream                 2
 endstream              2
 /JS                    1
 /JavaScript            1
 /OpenAction            1
 /Launch                0
 /EmbeddedFile          1
 /URI                   0
```

The keywords that matter most:

- **/JavaScript, /JS** — the PDF carries script. Legitimate documents rarely
  do; in a CTF it usually builds or hides the flag.
- **/OpenAction, /AA** — an action that fires automatically when the file
  opens (often to run the JavaScript above).
- **/Launch** — attempts to run an external program. Almost always malicious
  or a challenge hook.
- **/EmbeddedFile** — another file is stored inside the PDF; extract it (for
  example with `pdfdetach` or [binwalk](/wiki/tools/binwalk)).
- **/URI** — an embedded link, sometimes the next step of the challenge.

A non-zero count next to any of these is your cue to dig into that object.

## Installing locally

`pdfid.py` is a single script; download it from Didier Stevens' site and run
it with Python 3:

```console
$ python3 pdfid.py document.pdf
```

## Limitations

- It only *counts* keywords — it does not extract or decode the script or
  the embedded file. Follow up with `pdf-parser.py`, `pdfdetach` or
  [binwalk](/wiki/tools/binwalk).
- Keywords can be obfuscated with hex names (`/J#61vaScript`); pdfid
  normalizes many but not all, so a clean report is not a guarantee.
- For plain document metadata (author, pages, encryption) use
  [pdfinfo](/wiki/tools/pdfinfo), which also runs on your upload.

## Common CTF patterns

- `/JavaScript` + `/OpenAction` present — read the script object; it often
  assembles the flag at open time.
- `/EmbeddedFile` present — a payload (image, archive, second PDF) is
  attached; carve it out.
- Every dangerous count is zero — the flag is likely in the visible content
  or metadata, not in an active object.
