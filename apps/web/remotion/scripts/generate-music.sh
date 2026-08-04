#!/usr/bin/env bash
# Synthesizes an ORIGINAL soft ambient pad loop (no licensing) into public/music.mp3
# using ffmpeg sine sources. Chord progression: I – V – vi – IV in C major.
# Remotion loops it under the narration. Run from apps/web:  bash remotion/scripts/generate-music.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")/../../public" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

DUR=4          # seconds per chord
FADE=0.7       # attack/release to avoid clicks

# chord = three note frequencies (Hz)
make_chord () { # $1=out $2 $3 $4 = freqs
  ffmpeg -y -loglevel error \
    -f lavfi -i "sine=frequency=$2:duration=$DUR" \
    -f lavfi -i "sine=frequency=$3:duration=$DUR" \
    -f lavfi -i "sine=frequency=$4:duration=$DUR" \
    -filter_complex "[0][1][2]amix=inputs=3:normalize=1,afade=t=in:d=$FADE,afade=t=out:st=$(echo "$DUR-$FADE" | bc):d=$FADE[a]" \
    -map "[a]" "$1"
}

make_chord "$TMP/c1.wav" 261.63 329.63 392.00   # C  (C E G)
make_chord "$TMP/c2.wav" 196.00 246.94 293.66   # G  (G B D)
make_chord "$TMP/c3.wav" 220.00 261.63 329.63   # Am (A C E)
make_chord "$TMP/c4.wav" 174.61 220.00 261.63   # F  (F A C)

# concat into a 16s loop
printf "file '%s'\n" "$TMP/c1.wav" "$TMP/c2.wav" "$TMP/c3.wav" "$TMP/c4.wav" > "$TMP/list.txt"
ffmpeg -y -loglevel error -f concat -safe 0 -i "$TMP/list.txt" -c copy "$TMP/loop.wav"

# soften into an ambient pad: warm lowpass, gentle tremolo movement, hall reverb, high-pass rumble
ffmpeg -y -loglevel error -i "$TMP/loop.wav" \
  -af "highpass=f=90,lowpass=f=2400,tremolo=f=0.12:d=0.35,aecho=0.8:0.9:600|1100:0.35|0.22,volume=0.8" \
  -ar 44100 -b:a 160k "$DIR/music.mp3"

echo "✔ Wrote $DIR/music.mp3"
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$DIR/music.mp3" | xargs printf "  duration: %ss\n"
