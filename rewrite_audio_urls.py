#!/usr/bin/env python3
"""Rewrite audio URLs to point at media.droptrio.com (R2).
Usage:  python3 rewrite_audio_urls.py          # apply changes
        python3 rewrite_audio_urls.py --dry    # preview only

Handles three URL forms:
  1. Absolute legacy: http(s)://[www.]droptrio.com/path.mp3 -> R2
  2. Root-relative:   /path.mp3                              -> R2
  3. Relative refs:   href="songs/foo.mp3" (resolved against file dir) -> R2
URLs already at media.droptrio.com are skipped.
"""
import os, re, sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
DRY = "--dry" in sys.argv
R2_HOST = b"https://media.droptrio.com"

PROCESS_EXTS = {".html", ".htm", ".m3u", ".xml", ".xspf", ".pls"}
SKIP_DIRS = {".git", "node_modules"}
AUDIO_GROUP = rb"(?:mp3|wav|rm|m4a)"

# Pass 1: absolute legacy URLs and root-relative paths.
# Two alternatives:
#   alt 1: full URL prefixed with http(s)://[www.|media.]droptrio.com
#   alt 2: bare /path bounded by URL-context char (quote / equals / space / >)
# media.* matches are post-filtered out so we don't double-rewrite.
ABS_PATTERN = re.compile(
    rb"(?:"
    rb"https?://(?:www\.|media\.)?droptrio\.com(/[^\s\"'<>]+?\." + AUDIO_GROUP + rb")"
    rb"|"
    rb"(?<=[\"'\s=>])(/[^\s\"'<>]+?\." + AUDIO_GROUP + rb")"
    rb")",
    re.I,
)

# Pass 2: relative paths inside href= / src= attributes.
# Excludes paths starting with / or a scheme.
REL_PATTERN = re.compile(
    rb"((?:href|src)=)([\"'])((?!https?://|/)[^\"'<>]+?\." + AUDIO_GROUP + rb")\2",
    re.I,
)


def pass1_replace(m: re.Match) -> bytes:
    full = m.group(0)
    if b"media.droptrio.com" in full:
        return full
    path = m.group(1) or m.group(2)
    return R2_HOST + path


def make_pass2_replace(file_dir: Path):
    def replace(m: re.Match) -> bytes:
        url = m.group(3).decode("utf-8", "replace")
        resolved = (file_dir / url).resolve()
        try:
            rel_to_root = resolved.relative_to(ROOT)
        except ValueError:
            return m.group(0)
        new_url = R2_HOST + b"/" + rel_to_root.as_posix().encode("utf-8")
        return m.group(1) + m.group(2) + new_url + m.group(2)
    return replace


def process(path: Path) -> int:
    try:
        content = path.read_bytes()
    except OSError:
        return 0
    new = ABS_PATTERN.sub(pass1_replace, content)
    new = REL_PATTERN.sub(make_pass2_replace(path.parent.resolve()), new)
    if new == content:
        return 0
    # Count actual replacements by re-running on original
    n_abs = sum(1 for m in ABS_PATTERN.finditer(content) if b"media.droptrio.com" not in m.group(0))
    n_rel = sum(1 for _ in REL_PATTERN.finditer(content))
    n = n_abs + n_rel
    if not DRY:
        path.write_bytes(new)
    print(f"{'[dry] ' if DRY else ''}{path.relative_to(ROOT)}: {n}")
    return n


def main():
    total_files, total_subs = 0, 0
    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            p = Path(dirpath) / f
            if p.suffix.lower() not in PROCESS_EXTS:
                continue
            n = process(p)
            if n:
                total_files += 1
                total_subs += n
    print(f"\n{'Would update' if DRY else 'Updated'} {total_files} files, "
          f"{total_subs} total replacements.")


if __name__ == "__main__":
    main()
