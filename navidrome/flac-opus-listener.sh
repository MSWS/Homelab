#!/usr/bin/env bash
# /home/iboaz/navidrome/flac-opus-listener.sh — sweep music dir, transcode FLAC -> Opus
# Usage: flac-opus-listener.sh [--dry-run]
MUSIC_DIR="/mnt/samsung/media/navidrome/music/"

DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run|-n) DRY_RUN=1 ;;
    esac
done

log() { printf '%s\n' "$1"; }

[ "$DRY_RUN" = 1 ] && log "=== DRY RUN sweep (no files will be modified) ==="

find "$MUSIC_DIR" -type f -name '*.flac' -print0 |
while IFS= read -r -d '' f; do
    out="${f%.flac}.opus"

    if [ "$DRY_RUN" = 1 ]; then
        log "WOULD convert: $f -> $out"
        if ffmpeg -nostdin -loglevel error -i "$f" -c:a libopus -b:a 128k -f null -; then
            log "  decode OK, would delete: $f"
        else
            log "  DECODE FAILED (would skip): $f"
        fi
        continue
    fi

    if ffmpeg -nostdin -loglevel error -i "$f" \
            -c:a libopus -b:a 128k -map_metadata 0 -f ogg "$out.tmp" \
        && mv -f "$out.tmp" "$out" \
        && rm -f "$f"; then
        log "converted: $f"
    else
        rm -f "$out.tmp"
        log "FAILED: $f" >&2
    fi
done

log "sweep done"
