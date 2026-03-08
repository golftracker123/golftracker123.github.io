"""
python /Users/chriscremer/code/golftracker123.github.io/zwift/trim_video.py 16 180
python /Users/chriscremer/code/golftracker123.github.io/zwift/trim_video.py --start 0:34 --end 2:44
python /Users/chriscremer/code/golftracker123.github.io/zwift/trim_video.py --end 4:55 --duration 180

Modes:
1) Legacy mode:
   <cut_end_seconds> <output_duration_seconds>
   - cut_end_seconds: how many seconds to cut from end of source
   - output_duration_seconds: desired output length

2) Explicit range mode:
   --start <time> --end <time>
   - extracts exactly this interval from the source

3) End + lookback mode:
   --end <time> --duration <time>
   - output starts at (end - duration) and ends at end

Time format for all inputs:
- plain seconds (e.g., 180)
- m:ss (e.g., 2:44)
- h:mm:ss (e.g., 1:02:03)
"""

import argparse
import subprocess
from pathlib import Path
from datetime import datetime


def parse_time(value: str) -> float:
    parts = value.split(":")
    if len(parts) == 1:
        return float(parts[0])
    if len(parts) == 2:
        minutes = float(parts[0])
        seconds = float(parts[1])
        return minutes * 60 + seconds
    if len(parts) == 3:
        hours = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    raise ValueError(f"Invalid time value: {value}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Trim the most recent mp4 in Downloads. "
            "Use legacy mode (<cut_end_seconds> <output_duration_seconds>) "
            "or explicit mode (--start/--end) or (--end/--duration)."
        )
    )
    parser.add_argument("cut_end_seconds", nargs="?", help="Legacy mode: seconds to cut from end")
    parser.add_argument("output_duration_seconds", nargs="?", help="Legacy mode: desired output duration")
    parser.add_argument("--start", help="Start timestamp (seconds, m:ss, or h:mm:ss)")
    parser.add_argument("--end", help="End timestamp (seconds, m:ss, or h:mm:ss)")
    parser.add_argument(
        "--duration",
        help="Output duration in seconds or timestamp format (used with --end)",
    )
    return parser


args = build_parser().parse_args()

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

# ---- Compute trimming window ----
mode = ""
if args.start is not None and args.end is not None:
    mode = "start_end"
    start = parse_time(args.start)
    end = parse_time(args.end)
elif args.end is not None and args.duration is not None:
    mode = "end_duration"
    end = parse_time(args.end)
    out_len = parse_time(args.duration)
    start = max(0.0, end - out_len)
elif args.cut_end_seconds is not None and args.output_duration_seconds is not None:
    mode = "legacy"
    cut_end = parse_time(args.cut_end_seconds)
    out_len = parse_time(args.output_duration_seconds)
    end = duration - cut_end
    if end <= 0:
        raise RuntimeError("cut_end_seconds is longer than the video.")
    start = max(0.0, end - out_len)
else:
    raise RuntimeError(
        "Invalid arguments. Use either: "
        "(1) <cut_end_seconds> <output_duration_seconds>, "
        "(2) --start <time> --end <time>, or "
        "(3) --end <time> --duration <time>."
    )

if start < 0:
    raise RuntimeError("Start time cannot be negative.")
if end > duration:
    raise RuntimeError(f"End time {end:.2f}s is beyond video duration {duration:.2f}s.")
if end <= start:
    raise RuntimeError("End time must be greater than start time.")

actual_len = end - start

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
print("Mode:", mode)
print("Start time:", round(start, 2), "seconds")
print("End time:", round(end, 2), "seconds")
print("Output length:", round(actual_len, 2), "seconds")
print("Saved to:", output)
