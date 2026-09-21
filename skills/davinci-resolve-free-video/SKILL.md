---
name: davinci-resolve-free-video
description: >
  Converts iPhone, Pixel, and other phone-camera footage into edit-friendly
  media for DaVinci Resolve Free, including unsupported HEVC/H.264 variants,
  variable frame rates, Rec.2020 HLG HDR, PQ, and Dolby Vision. Use when Resolve
  cannot import, decode, scrub, or correctly display phone video, or when a
  conversion looks washed out, white, oversaturated, or unlike MPV playback.
license: MIT
compatibility: Requires Bash, ffmpeg, ffprobe, awk, and realpath. HDR conversion requires an FFmpeg build with libplacebo; on NixOS the script can use nixpkgs#ffmpeg-full.
---

# DaVinci Resolve Free video conversion

Convert codecs and color deliberately. A file that Resolve can decode may still
have the wrong pixels. Never treat metadata retagging as HDR-to-SDR conversion.

## Safety rules

- Preserve every source file.
- Inspect before encoding. Do not infer transfer function from filename or phone
  model.
- Create a short preview outside the final output directory before a batch.
- Play the converted preview directly in MPV. This separates encode errors from
  Resolve color-management errors.
- Get user approval for the preview when color conversion or interpolation is
  involved.
- Write final output to a hidden temporary file on the same filesystem.
- Validate the temporary file before moving it over an existing edit file.
- Stop on the first failed encode, probe, or full decode.
- Quote optional stream selectors such as `-map '0:a?'`. An unquoted `?` can be
  consumed by shell globbing.
- Never use a prior lossy or 8-bit intermediate when the original is available,
  unless the user explicitly chooses it.

## Choose the job

There are two separate jobs:

1. **Compatibility transcode:** preserve the source color appearance and change
   only codec, container, audio, or frame-rate representation.
2. **HDR-to-SDR conversion:** transform HDR pixel values and gamut into SDR
   Rec.709, then write matching Rec.709 metadata.

Do not run an HDR transform on ordinary SDR footage. That commonly causes
oversaturation, crushed shadows, or odd contrast. Do not merely add Rec.709 tags
to HDR pixels. That commonly causes washed-out or white images.

## Check tools

```bash
ffmpeg -version
ffprobe -version
ffmpeg -hide_banner -filters | grep -E 'libplacebo|zscale|tonemap'
```

For HDR work, require `libplacebo`. On NixOS, prefer a temporary shell instead
of changing the system:

```bash
nix shell nixpkgs#ffmpeg-full --command \
  ffmpeg -hide_banner -filters
```

Confirm that output contains a `libplacebo` filter. A base FFmpeg package may
omit it while `ffmpeg-full` provides it.

## Bundled scripts

Resolve these paths relative to this `SKILL.md` file:

- `scripts/probe-video.sh` prints the metadata needed to classify one source.
- `scripts/convert-resolve.sh` applies an explicit approved mode, writes a
  same-directory temporary MOV, validates streams and a full decode, then
  atomically renames it to the requested output.

The converter has two verified modes:

- `sdr-rec709`: compatibility transcode from limited-range Rec.709 SDR
- `hlg-bt2446a`: Rec.2020 HLG to limited-range Rec.709 with libplacebo BT.2446A

```bash
./scripts/probe-video.sh --help
./scripts/convert-resolve.sh --help
```

Scripts enforce chosen settings. They do not decide whether footage is SDR,
HLG, PQ, or Dolby Vision. Classify the source and approve a preview first. PQ
and Dolby Vision remain manual preview workflows until a project verifies a
specific mode.

## Inspect every source

Probe one file at a time. Passing several expanded filenames to one `ffprobe`
invocation does not probe them as independent inputs.

```bash
./scripts/probe-video.sh "$input"
```

For a directory:

```bash
for input in ./*.{mp4,mov,MOV}; do
  [ -e "$input" ] || continue
  printf '\n=== %s ===\n' "$input"
  ffprobe -v error -select_streams v:0 \
    -show_entries \
stream=codec_name,profile,width,height,pix_fmt,color_range,color_space,color_transfer,color_primaries,r_frame_rate,avg_frame_rate,duration,nb_frames \
    -of default=nw=1 -- "$input"
done
```

Record:

- codec and profile
- bit depth and pixel format
- dimensions and rotation/orientation
- color range, matrix, transfer, and primaries
- nominal and average frame rates
- timestamps, duration, and frame count
- audio codec, channel count, and sample rate
- HDR or Dolby Vision side data
- phone capture-rate metadata such as `com.android.capture.fps`

### Color classification

Use metadata and a visual check together.

| Likely source | Matrix | Transfer | Primaries | Action |
|---|---|---|---|---|
| SDR HD | `bt709` | `bt709` | `bt709` | Compatibility transcode only |
| sRGB transfer | source-dependent | `iec61966-2-1` | usually `bt709` | Convert transfer explicitly; do not use `sdr-rec709` blindly |
| Rec.2020 HLG | `bt2020nc` | `arib-std-b67` | `bt2020` | Tested HLG-to-SDR path below |
| HDR10/PQ | usually `bt2020nc` | `smpte2084` | `bt2020` | Use a PQ-specific preview; do not use the HLG recipe blindly |
| Dolby Vision | HEVC plus Dolby Vision side data | profile-dependent | profile-dependent | Inspect base layer and side data; require a preview |
| Unspecified | missing or `unknown` fields | missing | missing | Do not guess silently; compare in MPV and inspect phone metadata |

Some iPhone Dolby Vision files use an HLG-compatible base layer. Classify the
actual stream rather than assuming all iPhone HDR is PQ or all Pixel HDR is HLG.

## Default Resolve intermediate

For DaVinci Resolve Free, especially on Linux where phone HEVC/H.264 profiles
may not decode, use QuickTime DNxHR with PCM audio:

- container: MOV
- video: DNxHR HQ
- pixel format: `yuv422p`
- audio: signed 16-bit PCM, 48 kHz, stereo
- range: limited/video range
- explicit output color tags

DNxHR HQ is an 8-bit 4:2:2 editing intermediate. Use DNxHR HQX and a supported
10-bit pixel format only when the project requires a 10-bit intermediate and
Resolve compatibility has been tested. Do not increase bit depth merely to
make the file larger.

## SDR compatibility transcode

Use this only when the source is already SDR Rec.709 or the user wants to keep
its existing color encoding.

```bash
./scripts/convert-resolve.sh \
  --mode sdr-rec709 \
  --fps "$fps" \
  "$input" "$output"
```

Only force BT.709 tags after confirming that the source is meant to be Rec.709.
If it uses another SDR gamut or transfer function, convert it explicitly or
preserve it based on project requirements.

## Tested Rec.2020 HLG to SDR Rec.709 conversion

This path was verified on 10-bit Pixel HEVC tagged as:

- `yuv420p10le`
- `bt2020nc`
- `arib-std-b67`
- `bt2020`
- limited range

Use FFmpeg's `libplacebo` filter with ITU-R BT.2446 Method A:

```text
libplacebo=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=limited:tonemapping=bt.2446a:gamut_mode=perceptual:peak_detect=true:contrast_recovery=0:format=yuv422p
```

The bundled converter selects local FFmpeg when it has `libplacebo`. On NixOS,
it falls back to `nix shell nixpkgs#ffmpeg-full`:

```bash
./scripts/convert-resolve.sh \
  --mode hlg-bt2446a \
  --fps "$fps" \
  "$input" "$output"
```

### Known bad HLG path

Do not use this common pattern without independent calibration:

```text
zscale=t=linear:npl=100,...,tonemap=...
```

On tested Pixel HLG footage, `npl=100` scaled luminance incorrectly before tone
mapping. The result looked washed out and nearly white in both Resolve and MPV.
One measured frame had mean luma about `0.792` and 12.9% near-white clipping,
while MPV's correct SDR rendering had mean luma about `0.526` and 0.003%
near-white clipping. Correct Rec.709 tags did not repair the baked pixels.

## PQ and Dolby Vision

Do not label PQ or Dolby Vision footage as HLG and do not reuse the HLG recipe
without a visual comparison.

For PQ, a reasonable libplacebo preview candidate is BT.2390 into Rec.709:

```text
libplacebo=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=limited:tonemapping=bt.2390:gamut_mode=perceptual:peak_detect=true:format=yuv422p
```

Treat that as a candidate, not a universal preset. Mastering metadata, dynamic
metadata, and intended display peak matter. For Dolby Vision, confirm whether
FFmpeg/libplacebo sees and applies Dolby Vision metadata. If it does not, use a
verified base-layer workflow or a tool that supports the profile. Do not batch
until MPV comparison and user review pass.

## Frame rate and phone VFR

Phone footage is often variable frame rate. Inspect both frame-rate fields and
actual timestamps:

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries frame=best_effort_timestamp_time,pkt_duration_time,key_frame \
  -of csv=p=0 -- "$input" | head -n 120
```

Rules:

- Preserve source timing when Resolve handles it and no timeline replacement is
  required.
- For edit intermediates, use a stable CFR when VFR causes dropped frames,
  non-monotonic timestamps, bad seeking, or audio drift.
- Determine intended CFR from capture metadata, a known-good existing edit
  file, or the timeline. Do not trust `r_frame_rate` alone.
- A manually slowed phone file may report `4/1` while metadata says it was
  captured at 30 fps. Forcing 4 fps would be wrong.
- If replacing timeline media, preserve the existing output's frame count,
  duration, dimensions, and intended CFR unless the user asks for a timing
  change.

For deliberate 30 fps CFR:

```text
-fps_mode cfr -r 30
```

Check frame count and duration after encoding. Allow no unexplained timing
change.

## Make and approve a short preview

Select a representative three-second section containing skin, foliage, bright
sky, white objects, and deep shadows when available. Encode outside the final
output directory with the same color filter and video profile intended for the
batch.

Example for HLG at 30 fps:

```bash
./scripts/convert-resolve.sh \
  --mode hlg-bt2446a \
  --fps 30 \
  --start "$start" \
  --duration 3 \
  "$input" "$preview"
```

Play the output directly:

```bash
mpv -- "$preview"
```

Compare the same source timestamp using MPV's HDR-to-SDR renderer:

```bash
mpv --start="$start" \
  --target-prim=bt.709 --target-trc=bt.1886 --target-peak=100 \
  --tone-mapping=bt.2446a -- "$input"
```

Check:

- highlight detail is visible instead of a white haze
- skin and neutral surfaces look plausible
- foliage and saturated objects are not neon
- blacks are not lifted gray or crushed
- orientation and dimensions are correct
- motion cadence and audio sync are acceptable

If converted media looks wrong in MPV, the encode is wrong. Do not troubleshoot
Resolve first. If it looks right in MPV but wrong only in Resolve, then inspect
Resolve color management, clip input color space, LUTs/CST nodes, data levels,
and render cache.

## Safe batch and replacement workflow

For each source:

1. Match the intended output by exact basename.
2. If replacing existing timeline media, probe that file first and save its
   dimensions, frame rate, duration, frame count, and stream layout.
3. Run the converter with explicit expected values and `--replace`.
4. Stop on failure and leave the old destination intact.

```bash
./scripts/convert-resolve.sh \
  --mode hlg-bt2446a \
  --fps 30 \
  --replace \
  --expect-size 3840x2160 \
  --expect-frames "$expected_frames" \
  --expect-duration "$expected_duration" \
  "$input" "$output"
```

The script performs the hidden temporary encode, metadata checks, optional
size/frame/duration assertions, full decode, and atomic rename. A validation
failure removes only the temporary file.

Use a same-directory temporary path so final `mv` is atomic on the filesystem:

```bash
output="edit/${base}.mov"
temporary="edit/.${base}.resolve-tmp.mov"
```

Full decode check:

```bash
ffmpeg -hide_banner -loglevel error \
  -i "$temporary" -map 0 -f null -
```

Expected DNxHR HQ video probe:

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries \
stream=codec_name,profile,width,height,pix_fmt,color_range,color_space,color_transfer,color_primaries,r_frame_rate,avg_frame_rate,duration,nb_frames \
  -of default=nw=1 -- "$temporary"
```

Expected values for baked SDR output:

```text
codec_name=dnxhd
profile=DNXHR HQ
pix_fmt=yuv422p
color_range=tv
color_space=bt709
color_transfer=bt709
color_primaries=bt709
```

Expected audio probe when audio exists:

```bash
ffprobe -v error -select_streams a:0 \
  -show_entries stream=codec_name,sample_rate,channels,duration \
  -of default=nw=1 -- "$temporary"
```

Expected values:

```text
codec_name=pcm_s16le
sample_rate=48000
channels=2
```

After validation:

```bash
mv -f -- "$temporary" "$output"
```

Remove agent-created previews and temporary diagnostics after approval and final
validation. Preserve user-supplied files and original camera media.

## Diagnose bad color

### Washed out or nearly white everywhere

Likely causes:

- HDR values were decoded or tagged as SDR without tone mapping
- HLG was linearized with the wrong nominal peak luminance
- full-range and limited-range values were mismatched
- an HDR-to-SDR transform was applied twice

Check direct MPV playback of the output, output tags, and a representative frame
before changing Resolve.

### Oversaturated or neon color

Likely causes:

- Rec.2020 primaries were tagged as Rec.709 without gamut mapping
- an SDR source was sent through an HDR transform
- matrix and primaries do not describe the encoded pixels
- Resolve applies another input transform or LUT to already baked SDR media

### MPV is correct but Resolve is wrong

Check Resolve only after direct playback passes:

- use ordinary DaVinci YRGB for baked SDR unless the project needs managed color
- do not assign Rec.2100 HLG or PQ to baked Rec.709 clips
- remove HLG/PQ Color Space Transform nodes or LUTs from those clips
- confirm clip data levels are not forced incorrectly
- delete render cache and restart Resolve after replacing files in place

## Report completion

Report:

- source files processed
- output paths
- codec, profile, pixel format, range, matrix, transfer, and primaries
- dimensions, CFR, frame count, and duration
- audio codec, rate, and channels
- preview approval
- full-decode result
- total output size
- any source timing or color ambiguity
- confirmation that originals were not changed
