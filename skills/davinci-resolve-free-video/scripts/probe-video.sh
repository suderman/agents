#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: probe-video.sh INPUT

Print the video, audio, color, timing, metadata, and side-data fields needed to
plan a DaVinci Resolve Free intermediate. Output is JSON from ffprobe.

Environment:
  FFPROBE_BIN  ffprobe executable to use (default: ffprobe)
EOF
}

case "${1:-}" in
  -h|--help)
    usage
    exit 0
    ;;
esac

if [[ $# -ne 1 ]]; then
  usage >&2
  exit 2
fi

input=$1
ffprobe_bin=${FFPROBE_BIN:-ffprobe}

if ! command -v "$ffprobe_bin" >/dev/null 2>&1; then
  printf 'error: ffprobe not found: %s\n' "$ffprobe_bin" >&2
  exit 1
fi

if [[ ! -f "$input" ]]; then
  printf 'error: input is not a file: %s\n' "$input" >&2
  exit 1
fi

exec "$ffprobe_bin" -v error \
  -show_entries \
'stream=index,codec_type,codec_name,profile,width,height,pix_fmt,color_range,color_space,color_transfer,color_primaries,r_frame_rate,avg_frame_rate,time_base,start_time,duration,nb_frames,sample_rate,channels:stream_tags:stream_side_data:format=filename,duration,size,bit_rate:format_tags' \
  -of json -- "$input"
