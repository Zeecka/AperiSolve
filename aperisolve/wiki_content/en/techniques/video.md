Title: Video Steganography - Frames, Subtitle Tracks & Container Tricks
Description: How data hides in video files and how to recover it: probe the container, extract and analyze frames, pull subtitle/attachment/chapter tracks, carve trailing data past the moov atom, and reach the audio track - with ffmpeg and mkvextract commands.
Order: 25

# Video steganography

A video is a **container** (MP4/MOV, Matroska/WebM, AVI) wrapping several
streams — video, audio, subtitles, attachments, chapters and metadata. That
gives a challenge author many more places to hide data than a still image, but
the attack is systematic: **probe the container, split it into its streams, and
then apply the technique for each stream** — image techniques to the frames,
[audio techniques](/wiki/techniques/audio) to the soundtrack. Always
[identify the real container first](/wiki/methodology).

## Probe the container

Enumerate every stream, its codec, and the format-level metadata before you
touch the pixels:

```console
$ ffprobe -hide_banner file.mp4                 # streams, codecs, durations
$ mediainfo file.mkv                            # human-readable track table
$ exiftool -a -u -g1 file.mp4                   # container metadata + tags
```

Note the **number of streams** and their types. An extra subtitle, data or
attachment stream that has no business being there is the whole challenge.

!!! tip "Count the streams first"
    The most common video trick is not stego in the pixels at all — it is a
    second track (subtitles, an attached font/image, a `data` stream) riding
    alongside the video. `ffprobe` lists them in seconds; check it before any
    slow per-frame analysis.

## Metadata and appended data

Containers carry free-text metadata (`title`, `comment`, `©xyz` atoms) exactly
like EXIF, and — like every other format — anything appended past the logical
end of the file survives:

```console
$ ffprobe -show_format -show_streams file.mp4   # format tags = metadata
$ binwalk file.mp4                              # second file / archive inside
$ tail -c 256 file.mp4 | xxd                    # trailing data after the media
```

In MP4/MOV the media is described by the **`moov` atom**; bytes after the final
atom, or an oversized `free`/`skip`/`mdat` atom, are classic hiding spots. See
[Files & Archives](/wiki/techniques/files-archives) for carving embedded files.

## Extract and analyze frames

Split the video into images, then run the full
[image toolkit](/wiki/techniques/images) on the frames — a flag is often drawn
onto **one** frame, or hidden in the **LSBs of every** frame.

```console
$ ffmpeg -i file.mp4 -vsync 0 frames/f%05d.png        # every frame, lossless
$ ffmpeg -i file.mp4 -vf "select=eq(pict_type\,I)" -vsync 0 key/k%03d.png  # keyframes only
$ ffmpeg -ss 12.5 -i file.mp4 -frames:v 1 shot.png    # a single frame at a timestamp
```

- **A single odd frame** → scrub the thumbnails; a one-frame flash is invisible
  at normal speed. `ffmpeg … -vf "fps=1"` thins a long clip.
- **Per-frame LSB** → export to **lossless** PNG (never JPEG), then run
  [zsteg](/wiki/tools/zsteg) or the [bit-plane decomposer](/wiki/tools/decomposer)
  on the frames.
- **Difference between frames** → a payload can live in the handful of pixels
  that change between two near-identical frames (same idea as
  [GIF frame diffing](/wiki/techniques/images#gif)).

!!! warning "Re-encoding destroys pixel LSBs"
    Lossy video codecs (H.264/H.265/VP9) throw pixel bits away, so raw-pixel LSB
    stego only survives in **lossless** or intra-only encodes. If frames were
    re-encoded, look in the container, subtitles or audio instead — or in the
    **DCT/motion-vector domain** (research tools like `msu-stego`), not the
    spatial LSBs.

## Subtitle, attachment and chapter tracks

Non-video streams are the highest-yield target and the fastest to check:

```console
$ ffmpeg -i file.mkv -map 0:s:0 subs.srt              # rip the first subtitle track
$ mkvextract tracks file.mkv 2:subs.ass              # Matroska, track id from mkvmerge -i
$ ffmpeg -dump_attachment:t "" -i file.mkv           # dump every attached file (fonts, images)
$ ffprobe -show_chapters file.mp4                    # chapter titles can spell a message
```

Subtitles can carry the flag as off-screen timed text, as
[zero-width/whitespace Unicode](/wiki/techniques/text), or split one character
per cue. Attachments in Matroska are arbitrary files (fonts, cover images) — an
attached PNG may itself be a stego image.

## The audio track

Every video has (or can hide) audio. Demux it and switch to the
[audio techniques](/wiki/techniques/audio) — spectrogram first:

```console
$ ffmpeg -i file.mp4 -vn -acodec copy audio.aac       # extract without re-encoding
$ ffmpeg -i file.mp4 -vn audio.wav                    # decode to WAV for spectrogram/LSB
```

A message painted into the **spectrogram** of the soundtrack is a very common
"video" challenge — the video is just a wrapper.

## Related

- Analyze the extracted frames: [Images](/wiki/techniques/images).
- Analyze the extracted soundtrack: [Audio](/wiki/techniques/audio).
- Carve embedded files and inspect the container:
  [Files & Archives](/wiki/techniques/files-archives).
- Decode a recovered blob: [Encodings & obfuscation](/wiki/techniques/encodings).
- Drive a challenge from the [cheatsheet](/wiki/cheatsheet#video).
