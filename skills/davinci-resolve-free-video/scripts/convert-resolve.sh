#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  convert-resolve.sh --mode MODE [OPTIONS] INPUT OUTPUT.mov

Modes:
  sdr-rec709     Compatibility transcode from limited-range Rec.709 SDR
  hlg-bt2446a    Rec.2020 HLG to limited-range Rec.709 with libplacebo BT.2446A

Options:
  --fps RATE                 Make CFR output at RATE, such as 30 or 30000/1001
  --start TIME               Seek before encoding, for a preview
  --duration TIME            Limit output duration, for a preview
  --replace                  Allow atomic replacement of an existing OUTPUT
  --allow-color-mismatch     Bypass source color-metadata checks
  --expect-size WIDTHxHEIGHT Require these encoded dimensions
  --expect-frames COUNT      Require this encoded video frame count
  --expect-duration SECONDS  Require container duration within tolerance
  --duration-tolerance SEC   Duration tolerance (default: 0.15)
  -h, --help                 Show this help

Environment:
  FFMPEG_BIN                 ffmpeg executable to use (default: ffmpeg)
  FFPROBE_BIN                ffprobe executable to use (default: ffprobe)

The script always writes a same-directory temporary MOV, validates metadata and
a full decode, and only then renames it to OUTPUT. HLG mode falls back to
`nix shell nixpkgs#ffmpeg-full` when the selected ffmpeg lacks libplacebo.

Examples:
  convert-resolve.sh --mode hlg-bt2446a --fps 30 source.mp4 edit/source.mov
  convert-resolve.sh --mode hlg-bt2446a --fps 30 --start 12 --duration 3 \
    source.mp4 preview.mov
  convert-resolve.sh --mode sdr-rec709 --fps 24 --replace \
    source.mov edit/source.mov
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

need_value() {
  [[ $# -ge 2 ]] || die "$1 requires a value"
}

mode=
fps=
start=
duration=
replace=false
allow_color_mismatch=false
expected_size=
expected_frames=
expected_duration=
duration_tolerance=0.15

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      need_value "$@"
      mode=$2
      shift 2
      ;;
    --fps)
      need_value "$@"
      fps=$2
      shift 2
      ;;
    --start)
      need_value "$@"
      start=$2
      shift 2
      ;;
    --duration)
      need_value "$@"
      duration=$2
      shift 2
      ;;
    --replace)
      replace=true
      shift
      ;;
    --allow-color-mismatch)
      allow_color_mismatch=true
      shift
      ;;
    --expect-size)
      need_value "$@"
      expected_size=$2
      shift 2
      ;;
    --expect-frames)
      need_value "$@"
      expected_frames=$2
      shift 2
      ;;
    --expect-duration)
      need_value "$@"
      expected_duration=$2
      shift 2
      ;;
    --duration-tolerance)
      need_value "$@"
      duration_tolerance=$2
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      die "unknown option: $1"
      ;;
    *)
      break
      ;;
  esac
done

[[ "$mode" == sdr-rec709 || "$mode" == hlg-bt2446a ]] || {
  usage >&2
  die "--mode must be sdr-rec709 or hlg-bt2446a"
}
[[ $# -eq 2 ]] || {
  usage >&2
  die "INPUT and OUTPUT.mov are required"
}

input=$1
output=$2
ffmpeg_bin=${FFMPEG_BIN:-ffmpeg}
ffprobe_bin=${FFPROBE_BIN:-ffprobe}

[[ -f "$input" ]] || die "input is not a file: $input"
[[ "$output" == *.mov || "$output" == *.MOV ]] || die "output must use a .mov extension: $output"
[[ "$(realpath -- "$input")" != "$(realpath -m -- "$output")" ]] || die "input and output must differ"
command -v "$ffmpeg_bin" >/dev/null 2>&1 || die "ffmpeg not found: $ffmpeg_bin"
command -v "$ffprobe_bin" >/dev/null 2>&1 || die "ffprobe not found: $ffprobe_bin"

if [[ -n "$fps" && ! "$fps" =~ ^([0-9]+([.][0-9]+)?|[0-9]+/[1-9][0-9]*)$ ]]; then
  die "invalid frame rate: $fps"
fi
if [[ -n "$expected_size" && ! "$expected_size" =~ ^[1-9][0-9]*x[1-9][0-9]*$ ]]; then
  die "invalid expected size: $expected_size"
fi
if [[ -n "$expected_frames" && ! "$expected_frames" =~ ^[1-9][0-9]*$ ]]; then
  die "invalid expected frame count: $expected_frames"
fi
for number in "$expected_duration" "$duration_tolerance"; do
  if [[ -n "$number" && ! "$number" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
    die "invalid duration value: $number"
  fi
done

if [[ -e "$output" && "$replace" != true ]]; then
  die "output exists; pass --replace to replace it atomically: $output"
fi

probe_video_field() {
  "$ffprobe_bin" -v error -select_streams v:0 \
    -show_entries "stream=$1" -of default=nw=1:nk=1 -- "$2"
}

probe_audio_field() {
  "$ffprobe_bin" -v error -select_streams a:0 \
    -show_entries "stream=$1" -of default=nw=1:nk=1 -- "$2"
}

source_space=$(probe_video_field color_space "$input")
source_transfer=$(probe_video_field color_transfer "$input")
source_primaries=$(probe_video_field color_primaries "$input")
source_range=$(probe_video_field color_range "$input")

color_mismatch=false
case "$mode" in
  sdr-rec709)
    [[ "$source_space" == bt709 ]] || color_mismatch=true
    [[ "$source_transfer" == bt709 ]] || color_mismatch=true
    [[ "$source_primaries" == bt709 ]] || color_mismatch=true
    [[ "$source_range" == tv ]] || color_mismatch=true
    ;;
  hlg-bt2446a)
    [[ "$source_space" == bt2020nc ]] || color_mismatch=true
    [[ "$source_transfer" == arib-std-b67 ]] || color_mismatch=true
    [[ "$source_primaries" == bt2020 ]] || color_mismatch=true
    [[ "$source_range" == tv ]] || color_mismatch=true
    ;;
esac

if [[ "$color_mismatch" == true && "$allow_color_mismatch" != true ]]; then
  cat >&2 <<EOF
error: source color metadata does not match mode $mode
  color_space=$source_space
  color_transfer=$source_transfer
  color_primaries=$source_primaries
  color_range=$source_range
Inspect the source and choose the correct mode. Use --allow-color-mismatch only
after an independent visual and metadata check.
EOF
  exit 1
fi

ffmpeg=("$ffmpeg_bin")
if [[ "$mode" == hlg-bt2446a ]]; then
  filters=$("${ffmpeg[@]}" -hide_banner -filters 2>/dev/null || true)
  if [[ "$filters" != *libplacebo* ]]; then
    if [[ "$ffmpeg_bin" != ffmpeg ]]; then
      die "$ffmpeg_bin lacks libplacebo"
    fi
    command -v nix >/dev/null 2>&1 || die "ffmpeg lacks libplacebo and nix is unavailable"
    ffmpeg=(nix shell nixpkgs#ffmpeg-full --command ffmpeg)
    filters=$("${ffmpeg[@]}" -hide_banner -filters 2>/dev/null || true)
    [[ "$filters" == *libplacebo* ]] || die "nixpkgs#ffmpeg-full lacks libplacebo"
  fi
fi

output_dir=$(dirname -- "$output")
mkdir -p -- "$output_dir"
output_name=$(basename -- "$output")
temporary="$output_dir/.${output_name%.*}.resolve-tmp.$$.mov"

cleanup() {
  if [[ -n "${temporary:-}" && -e "$temporary" ]]; then
    rm -f -- "$temporary"
  fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

input_options=()
[[ -n "$start" ]] && input_options+=(-ss "$start")
output_options=()
[[ -n "$duration" ]] && output_options+=(-t "$duration")
fps_options=()
[[ -n "$fps" ]] && fps_options=(-fps_mode cfr -r "$fps")
filter_options=()
if [[ "$mode" == hlg-bt2446a ]]; then
  filter_options=(-vf 'libplacebo=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=limited:tonemapping=bt.2446a:gamut_mode=perceptual:peak_detect=true:contrast_recovery=0:format=yuv422p')
fi

printf 'Encoding %s -> %s\n' "$input" "$output"
"${ffmpeg[@]}" -hide_banner -y \
  "${input_options[@]}" -i "$input" \
  "${output_options[@]}" \
  -map_metadata 0 \
  -map 0:v:0 -map '0:a?' \
  "${filter_options[@]}" \
  "${fps_options[@]}" \
  -c:v dnxhd -profile:v dnxhr_hq -pix_fmt yuv422p \
  -colorspace bt709 -color_trc bt709 -color_primaries bt709 -color_range tv \
  -c:a pcm_s16le -ar 48000 -ac 2 \
  "$temporary"

[[ -s "$temporary" ]] || die "encoder produced no output"

assert_video_field() {
  local field=$1 expected=$2 actual
  actual=$(probe_video_field "$field" "$temporary")
  [[ "$actual" == "$expected" ]] || die "$field is $actual; expected $expected"
}

assert_video_field codec_name dnxhd
assert_video_field profile 'DNXHR HQ'
assert_video_field pix_fmt yuv422p
assert_video_field color_range tv
assert_video_field color_space bt709
assert_video_field color_transfer bt709
assert_video_field color_primaries bt709

if [[ -n "$expected_size" ]]; then
  actual_size="$(probe_video_field width "$temporary")x$(probe_video_field height "$temporary")"
  [[ "$actual_size" == "$expected_size" ]] || die "size is $actual_size; expected $expected_size"
fi

if [[ -n "$fps" ]]; then
  actual_fps=$(probe_video_field avg_frame_rate "$temporary")
  awk -v actual="$actual_fps" -v expected="$fps" '
    function value(rate, parts) {
      split(rate, parts, "/")
      return length(parts) == 2 ? parts[1] / parts[2] : parts[1]
    }
    BEGIN {
      difference = value(actual) - value(expected)
      if (difference < 0) difference = -difference
      exit difference <= 0.0001 ? 0 : 1
    }
  ' || die "frame rate is $actual_fps; expected $fps"
fi

if [[ -n "$expected_frames" ]]; then
  actual_frames=$(probe_video_field nb_frames "$temporary")
  [[ "$actual_frames" == "$expected_frames" ]] || die "frame count is $actual_frames; expected $expected_frames"
fi

if [[ -n "$expected_duration" ]]; then
  actual_duration=$("$ffprobe_bin" -v error -show_entries format=duration \
    -of default=nw=1:nk=1 -- "$temporary")
  awk -v actual="$actual_duration" -v expected="$expected_duration" -v tolerance="$duration_tolerance" '
    BEGIN {
      difference = actual - expected
      if (difference < 0) difference = -difference
      exit difference <= tolerance ? 0 : 1
    }
  ' || die "duration is $actual_duration; expected $expected_duration +/- $duration_tolerance"
fi

source_has_audio=$("$ffprobe_bin" -v error -select_streams a:0 \
  -show_entries stream=index -of csv=p=0 -- "$input")
if [[ -n "$source_has_audio" ]]; then
  [[ "$(probe_audio_field codec_name "$temporary")" == pcm_s16le ]] || die "audio codec is not pcm_s16le"
  [[ "$(probe_audio_field sample_rate "$temporary")" == 48000 ]] || die "audio sample rate is not 48000"
  [[ "$(probe_audio_field channels "$temporary")" == 2 ]] || die "audio is not stereo"
fi

printf 'Validating full decode...\n'
"${ffmpeg[@]}" -hide_banner -loglevel error -xerror \
  -i "$temporary" -map 0 -f null -

mv -f -- "$temporary" "$output"
temporary=

printf 'Validated output: %s\n' "$output"
"$ffprobe_bin" -v error \
  -show_entries stream=index,codec_type,codec_name,profile,width,height,pix_fmt,color_range,color_space,color_transfer,color_primaries,r_frame_rate,avg_frame_rate,duration,nb_frames,sample_rate,channels:format=duration,size \
  -of default=nw=1 -- "$output"
