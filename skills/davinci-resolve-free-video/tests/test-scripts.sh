#!/usr/bin/env bash
set -euo pipefail

skill_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
probe="$skill_dir/scripts/probe-video.sh"
convert="$skill_dir/scripts/convert-resolve.sh"
temporary_dir=$(mktemp -d)
trap 'rm -rf -- "$temporary_dir"' EXIT

ffmpeg -hide_banner -loglevel error -y \
  -f lavfi -i 'testsrc2=size=1280x720:rate=24' \
  -f lavfi -i 'sine=frequency=440:sample_rate=48000' \
  -t 0.25 -shortest \
  -vf format=yuv420p \
  -c:v libx265 -preset ultrafast \
  -x265-params 'log-level=error:colorprim=bt709:transfer=bt709:colormatrix=bt709:range=limited' \
  -colorspace bt709 -color_trc bt709 -color_primaries bt709 -color_range tv \
  -c:a aac \
  "$temporary_dir/sdr.mp4"

ffmpeg -hide_banner -loglevel error -y \
  -f lavfi -i 'testsrc2=size=1280x720:rate=24' \
  -f lavfi -i 'sine=frequency=440:sample_rate=48000' \
  -t 0.25 -shortest \
  -vf format=yuv420p10le \
  -c:v libx265 -preset ultrafast \
  -x265-params 'log-level=error:colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc:range=limited' \
  -colorspace bt2020nc -color_trc arib-std-b67 -color_primaries bt2020 -color_range tv \
  -c:a aac \
  "$temporary_dir/hlg.mp4"

sdr_hash=$(sha256sum "$temporary_dir/sdr.mp4")
hlg_hash=$(sha256sum "$temporary_dir/hlg.mp4")

"$probe" "$temporary_dir/hlg.mp4" > "$temporary_dir/probe.json"
python3 -m json.tool "$temporary_dir/probe.json" >/dev/null
grep -q '"color_transfer": "arib-std-b67"' "$temporary_dir/probe.json"
grep -q '"color_primaries": "bt2020"' "$temporary_dir/probe.json"

"$convert" \
  --mode sdr-rec709 \
  --fps 24 \
  --expect-size 1280x720 \
  --expect-frames 6 \
  --expect-duration 0.25 \
  "$temporary_dir/sdr.mp4" "$temporary_dir/sdr.mov"

if "$convert" --mode sdr-rec709 \
  "$temporary_dir/sdr.mp4" "$temporary_dir/sdr.mov" >/dev/null 2>&1; then
  echo 'existing output was replaced without --replace' >&2
  exit 1
fi

validated_hash=$(sha256sum "$temporary_dir/sdr.mov")
if "$convert" \
  --mode sdr-rec709 \
  --fps 24 \
  --replace \
  --expect-frames 7 \
  "$temporary_dir/sdr.mp4" "$temporary_dir/sdr.mov" >/dev/null 2>&1; then
  echo 'incorrect expected frame count passed validation' >&2
  exit 1
fi
[[ "$(sha256sum "$temporary_dir/sdr.mov")" == "$validated_hash" ]]

"$convert" \
  --mode sdr-rec709 \
  --fps 24 \
  --replace \
  --expect-size 1280x720 \
  --expect-frames 6 \
  "$temporary_dir/sdr.mp4" "$temporary_dir/sdr.mov"

"$convert" \
  --mode hlg-bt2446a \
  --fps 24 \
  --expect-size 1280x720 \
  --expect-frames 6 \
  --expect-duration 0.25 \
  "$temporary_dir/hlg.mp4" "$temporary_dir/hlg.mov"

[[ "$(sha256sum "$temporary_dir/sdr.mp4")" == "$sdr_hash" ]]
[[ "$(sha256sum "$temporary_dir/hlg.mp4")" == "$hlg_hash" ]]

if find "$temporary_dir" -maxdepth 1 -name '.*.resolve-tmp.*.mov' -print -quit | grep -q .; then
  echo 'temporary output was not removed' >&2
  exit 1
fi

printf 'Probe, SDR, HLG, replacement, validation, and source-preservation tests passed.\n'
