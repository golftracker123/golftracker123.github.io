"""
python /Users/chriscremer/code/golftracker123.github.io/zwift/trim_video.py 16 180

cut_end_seconds: how many seconds to cut from the end of the video
output_duration_seconds: how long the output video should be
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime


# ---- Parse arguments ----
if len(sys.argv) != 3:
    print("Usage: python trim_video.py <cut_end_seconds> <output_duration_seconds>")
    sys.exit(1)

CUT_END = float(sys.argv[1])
OUT_LEN = float(sys.argv[2])

# ---- Find most recent mp4 in Downloads ----
downloads = Path.home() / "Downloads"
mp4_files = list(downloads.glob("*.mp4"))

if not mp4_files:
    raise RuntimeError("No mp4 files found in Downloads.")

latest_file = max(mp4_files, key=lambda f: f.stat().st_mtime)

# ---- Get duration using ffprobe ----
result = subprocess.run(
    [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(latest_file)
    ],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    raise RuntimeError("ffprobe failed.")

duration = float(result.stdout.strip())

# ---- Compute safe trimming window ----
usable_end = duration - CUT_END

if usable_end <= 0:
    raise RuntimeError("CUT_END is longer than the video.")

start = max(0, usable_end - OUT_LEN)
actual_len = usable_end - start

# ---- Output path ----
output = downloads / f"{datetime.now():%Y%m%d_%H%M%S}.mp4"

# ---- Run ffmpeg ----
subprocess.run([
    "ffmpeg",
    "-ss", str(start),
    "-i", str(latest_file),
    "-t", str(actual_len),
    "-vf", "scale=-2:720",
    "-c:v", "libx264",
    "-crf", "28",
    "-preset", "slow",
    "-c:a", "aac",
    "-b:a", "128k",
    str(output)
])

print("Input:", latest_file)
print("Original duration:", round(duration, 2), "seconds")
print("Cut end:", CUT_END, "seconds")
print("Start time:", round(start, 2), "seconds")
print("Output length:", round(actual_len, 2), "seconds")
print("Saved to:", output)

