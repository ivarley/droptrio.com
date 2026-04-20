#!/usr/bin/env python3
"""Rewrite absolute droptrio.com URLs to root-relative so the site works locally.
Usage:  python3 rewrite_urls.py          # apply changes
        python3 rewrite_urls.py --dry    # preview only
"""
import os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DRY = "--dry" in sys.argv

TARGET_DIRS = ["Music", "Bio", "Photos", "Press", "Showdates", "Band", "Email"]
TARGET_ROOT_FILES = ["index.html", "droptric.html", "signup.htm"]

SKIP_EXTS = {".m3u", ".pls", ".xspf", ".mp3", ".rm", ".ram", ".jpg", ".jpeg",
             ".gif", ".png", ".swf", ".ico", ".pdf", ".zip"}
SKIP_FILES = {"live_podcast.xml", "live.xml", "podcast_pointer.asp"}

PATTERN = re.compile(rb'https?://(?:www\.)?droptrio\.com/')
# Section-relative footer/nav links (e.g. href="Music/music.html") break at any
# depth >= 1. Rewrite to root-relative so they work from every page.
SECTION_PATTERN = re.compile(
    rb'href="(Music|Bio|Photos|Press|Showdates|Band|Email|blog)/'
)

def should_process(path):
    name = os.path.basename(path)
    if name in SKIP_FILES:
        return False
    ext = os.path.splitext(name)[1].lower()
    return ext not in SKIP_EXTS

def rewrite(path):
    with open(path, "rb") as f:
        content = f.read()
    new, n1 = PATTERN.subn(b'/', content)
    new, n2 = SECTION_PATTERN.subn(rb'href="/\1/', new)
    n = n1 + n2
    if n == 0:
        return 0
    if not DRY:
        with open(path, "wb") as f:
            f.write(new)
    print(f"{'[dry] ' if DRY else ''}{path}: {n} replacement(s)")
    return n

def walk():
    total_files, total_subs = 0, 0
    for name in TARGET_ROOT_FILES:
        p = os.path.join(ROOT, name)
        if os.path.isfile(p) and should_process(p):
            n = rewrite(p)
            if n:
                total_files += 1
                total_subs += n
    for d in TARGET_DIRS:
        for dirpath, _, files in os.walk(os.path.join(ROOT, d)):
            for f in files:
                p = os.path.join(dirpath, f)
                if should_process(p):
                    n = rewrite(p)
                    if n:
                        total_files += 1
                        total_subs += n
    print(f"\n{'Would update' if DRY else 'Updated'} {total_files} files, "
          f"{total_subs} total replacements.")

if __name__ == "__main__":
    walk()
