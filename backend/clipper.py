
"""Video clip extraction utilities using ffmpeg/ffprobe.

- make_clip: extracts a clip starting X ms before and ending Y ms after a segment
- batch_extract_clips: convenience function for many segments at once

This module prefers stream copy for speed; if the cut does not align with keyframes,
it falls back to a fast re-encode.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

def _run(cmd: list) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)

def get_video_duration_ms(media_path: str) -> int:
    """Return duration in ms for a media file via ffprobe."""
    result = _run(['ffprobe', '-v', 'error', '-show_entries',
                   'format=duration', '-of', 'json', media_path])
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    data = json.loads(result.stdout)
    return int(float(data['format']['duration']) * 1000)

def make_clip(
    media_path: str,
    start_ms: int,
    end_ms: int,
    before_ms: int = 5000,
    after_ms: int = 10000,
    out_dir: str = "clips",
) -> str:
    """Create a clipped mp4 around a segment with context before/after.

    The actual clip is clamped to media duration. If stream copy fails due
    to non-keyframe boundaries, re-encode using libx264 veryfast.
    """
    out_dir_path = Path(out_dir)
    out_dir_path.mkdir(parents=True, exist_ok=True)

    video_duration_ms = get_video_duration_ms(media_path)
    clip_start_ms = max(0, int(start_ms) - int(before_ms))
    clip_end_ms = min(video_duration_ms, int(end_ms) + int(after_ms))

    # Allow very short clips (>= 1s) by design; user can tune windows.
    ss = clip_start_ms / 1000.0
    to = clip_end_ms / 1000.0

    stem = Path(media_path).stem
    out_file = out_dir_path / f"{stem}_{clip_start_ms}_{clip_end_ms}.mp4"

    # Attempt stream copy first
    cmd_copy = ['ffmpeg', '-y', '-ss', str(ss), '-i', media_path,
                '-to', str(to), '-c', 'copy', str(out_file)]
    res = _run(cmd_copy)

    if res.returncode != 0 or not out_file.exists():
        # Fall back to re-encode at non-keyframe boundaries
        cmd_encode = ['ffmpeg', '-y', '-ss', str(ss), '-i', media_path,
                      '-to', str(to), '-c:v', 'libx264', '-preset', 'veryfast',
                      '-c:a', 'aac', str(out_file)]
        res2 = _run(cmd_encode)
        if res2.returncode != 0:
            raise RuntimeError(f"ffmpeg encode failed: {res2.stderr[:300]}")

    return str(out_file)

def batch_extract_clips(
    segments: List[Dict],
    before_ms: int = 5000,
    after_ms: int = 10000,
    out_dir: str = "clips",
) -> List[Dict[str, Optional[int]]]:
    """Extract clips for a batch of segments. Each item must contain:
       - 'media_path', 'start_ms', 'end_ms'
    Returns a list of dicts per input item containing 'clip_path' and 'window_ms'.
    """
    outputs = []
    for seg in segments:
        p = make_clip(
            seg['media_path'],
            int(seg['start_ms']),
            int(seg['end_ms']),
            before_ms=before_ms,
            after_ms=after_ms,
            out_dir=out_dir,
        )
        outputs.append({
            "clip_path": p,
            "window_ms": [max(0, int(seg['start_ms']) - before_ms),
                          int(seg['end_ms']) + after_ms]
        })
    return outputs
