"""
python /Users/chriscremer/code/golftracker123.github.io/zwift/make_html.py
"""

import json
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
with open(index_file, "w", encoding="utf-8") as f:
    f.write("<!DOCTYPE html>\n<html>\n<head><meta charset='UTF-8'><title>Zwift Videos</title></head>\n<body>\n")
    f.write("<h1>Zwift Videos</h1>\n<ul>\n")

    for video in mp4_files:
        rel_path = f"vids/{video.name}"
        note = notes.get(rel_path, "")
        f.write(f'<li><a href="{rel_path}">{video.name}</a>')
        if note:
            f.write(f" — {note}")
        f.write("</li>\n")

    f.write("</ul>\n</body>\n</html>\n")

print(f"Generated {index_file} with {len(mp4_files)} videos. Notes file: {notes_file}")