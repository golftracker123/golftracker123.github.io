"""
python /Users/chriscremer/code/golftracker123.github.io/zwift/trim_video.py cut_from_end=16 output_duration=180
python /Users/chriscremer/code/golftracker123.github.io/zwift/trim_video.py --start 0:34 --end 2:44
python /Users/chriscremer/code/golftracker123.github.io/zwift/trim_video.py --end 4:55 --duration 180

Modes:
1) Cut from end + output duration:
   cut_from_end=<time> output_duration=<time>
   - cut_from_end: how many seconds to cut from end of source
   - output_duration: desired output length

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
            "Use legacy mode (cut_from_end=<time> output_duration=<time>) "
            "or explicit mode (--start/--end) or (--end/--duration)."
        )
    )
    parser.add_argument(
        "legacy_args",
        nargs="*",
        help="Legacy mode key=value args: cut_from_end=<time> output_duration=<time>",
    )
    parser.add_argument("--start", help="Start timestamp (seconds, m:ss, or h:mm:ss)")
    parser.add_argument("--end", help="End timestamp (seconds, m:ss, or h:mm:ss)")
    parser.add_argument(
        "--duration",
        help="Output duration in seconds or timestamp format (used with --end)",
    )
    return parser


args = build_parser().parse_args()


def parse_legacy_kv(tokens: list[str]) -> tuple[float | None, float | None]:
    if not tokens:
        return None, None

    allowed = {
        "cut_from_end",
        "output_duration",
        # backwards-compatible aliases
        "cut_end_seconds",
        "output_duration_seconds",
    }
    parsed: dict[str, str] = {}

    for token in tokens:
        if "=" not in token:
            raise RuntimeError(
                f"Invalid legacy arg '{token}'. Use key=value form, e.g. cut_from_end=16."
            )
        key, value = token.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key not in allowed:
            raise RuntimeError(f"Unknown legacy arg '{key}'.")
        parsed[key] = value

    cut_raw = parsed.get("cut_from_end", parsed.get("cut_end_seconds"))
    out_raw = parsed.get("output_duration", parsed.get("output_duration_seconds"))

    if (cut_raw is None) != (out_raw is None):
        raise RuntimeError("Legacy mode requires both cut_from_end and output_duration.")
    if cut_raw is None:
        raise RuntimeError(
            "Legacy mode args are incomplete. Use cut_from_end=<time> output_duration=<time>."
        )

    return parse_time(cut_raw), parse_time(out_raw)

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
cut_end_legacy, out_len_legacy = parse_legacy_kv(args.legacy_args)

has_start_end = args.start is not None or args.end is not None
has_end_duration = args.end is not None or args.duration is not None
has_legacy = cut_end_legacy is not None and out_len_legacy is not None

if has_legacy and (has_start_end or args.duration is not None):
    raise RuntimeError("Do not mix legacy mode with --start/--end/--duration options.")

if args.start is not None and args.end is not None and args.duration is None:
    mode = "start_end"
    start = parse_time(args.start)
    end = parse_time(args.end)
elif args.end is not None and args.duration is not None and args.start is None:
    mode = "end_duration"
    end = parse_time(args.end)
    out_len = parse_time(args.duration)
    start = max(0.0, end - out_len)
elif has_legacy:
    mode = "legacy"
    cut_end = cut_end_legacy
    out_len = out_len_legacy
    end = duration - cut_end
    if end <= 0:
        raise RuntimeError("cut_from_end is longer than the video.")
    start = max(0.0, end - out_len)
else:
    raise RuntimeError(
        "Invalid arguments. Use either: "
        "(1) cut_from_end=<time> output_duration=<time>, "
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
