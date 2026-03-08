"""
python /Users/chriscremer/code/golftracker123.github.io/zwift/make_html.py
"""

import json
import subprocess
from pathlib import Path

# ---- Paths ----
zwift_dir = Path("/Users/chriscremer/code/golftracker123.github.io/zwift")
vids_dir = zwift_dir / "vids"
notes_file = zwift_dir / "video_notes.json"
index_file = zwift_dir / "index.html"

# ---- Load existing notes ----
if notes_file.exists():
    with open(notes_file, "r", encoding="utf-8") as f:
        notes = json.load(f)
else:
    notes = {}

# ---- Find all videos ----
mp4_files = sorted(
    vids_dir.glob("*.mp4"),
    key=lambda f: f.stat().st_mtime,
    reverse=True
)

# ---- Add empty notes for new videos ----
for video in mp4_files:
    rel_path = f"vids/{video.name}"
    if rel_path not in notes:
        notes[rel_path] = ""

# ---- Save updated notes ----
with open(notes_file, "w", encoding="utf-8") as f:
    json.dump(notes, f, indent=2)

# ---- Generate index.html ----
def get_video_duration(video_path: Path) -> float | None:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None

    output = result.stdout.strip()
    if not output:
        return None

    try:
        return float(output)
    except ValueError:
        return None


def format_duration(duration_seconds: float | None) -> str:
    if duration_seconds is None:
        return "unknown"
    total_seconds = int(round(duration_seconds))
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


with open(index_file, "w", encoding="utf-8") as f:
    f.write("<!DOCTYPE html>\n<html>\n<head><meta charset='UTF-8'><title>Zwift Videos</title></head>\n<body>\n")
    f.write("<h1>Zwift Videos</h1>\n<ul>\n")

    for video in mp4_files:
        rel_path = f"vids/{video.name}"
        note = notes.get(rel_path, "")
        duration = format_duration(get_video_duration(video))
        f.write(f'<li><a href="{rel_path}">{video.name}</a> ({duration})')
        if note:
            f.write(f" — {note}")
        f.write("</li>\n")

    f.write("</ul>\n</body>\n</html>\n")

print(f"Generated {index_file} with {len(mp4_files)} videos. Notes file: {notes_file}")
