
import os
import pytest
from pathlib import Path
from backend.clipper import make_clip, get_video_duration_ms

@pytest.mark.skipif(not Path("sample.mp4").exists(), reason="sample.mp4 not present")
def test_clip_at_video_start():
    # This test requires a small local sample.mp4.
    duration = get_video_duration_ms("sample.mp4")
    clip = make_clip("sample.mp4", 0, min(5000, duration//2), before_ms=1000, after_ms=1000)
    assert Path(clip).exists()
