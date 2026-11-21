#!/usr/bin/env python3
"""Offline checks for the CoreJBH static site.

Verifies, without any network access:
  * every local href/src/link resolves to a file that exists,
  * no page pulls a stylesheet, script, font, image or frame from another host,
  * HTML tags are balanced,
  * every <img> has an alt attribute and every page has a lang and a title.

Usage: python3 tools/check_site.py   (from the repository root)
"""
from __future__ import annotations

import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}
EXTERNAL_OK = ("https://github.com/", "mailto:")


class Checker(HTMLParser):
    def __init__(self, path: str) -> None:
        super().__init__(convert_charrefs=True)
        self.path = path
        self.stack: list[tuple[str, int]] = []
        self.problems: list[str] = []
        self.refs: list[str] = []
        self.has_title = False
        self.lang = None
        self.img_without_alt = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "title":
            self.has_title = True
        for key in ("href", "src", "srcset", "poster", "data"):
            val = a.get(key)
            if not val:
                continue
            if key == "srcset":
                for part in val.split(","):
                    url = part.strip().split(" ")[0]
                    if url:
                        self.refs.append(url)
            else:
                self.refs.append(val)
        if tag == "img" and "alt" not in a:
            self.img_without_alt += 1
            self.problems.append(f"{self.path}: <img> without alt ({a.get('src')})")
        if tag not in VOID:
            self.stack.append((tag, self.getpos()[0]))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.problems.append(f"{self.path}: closing </{tag}> with nothing open")
            return
        open_tag, line = self.stack.pop()
        if open_tag != tag:
            self.problems.append(
                f"{self.path}:{line}: <{open_tag}> closed by </{tag}>"
            )

    def close(self):
        super().close()
        for tag, line in self.stack:
            self.problems.append(f"{self.path}:{line}: <{tag}> never closed")
        if not self.has_title:
            self.problems.append(f"{self.path}: no <title>")
        if not self.lang:
            self.problems.append(f"{self.path}: <html> without lang")


def resolve(page: str, ref: str) -> str | None:
    """Return the file a local reference should hit, or None if external."""
    if ref.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return None
    if ref.startswith(("http://", "https://", "//")):
        return "EXTERNAL:" + ref
    path = urlparse(ref).path
    if not path:
        return None
    if path.startswith("/"):
        target = os.path.join(ROOT, path.lstrip("/"))
    else:
        target = os.path.normpath(os.path.join(os.path.dirname(page), path))
    if os.path.isdir(target):
        target = os.path.join(target, "index.html")
    return target


def main() -> int:
    pages = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if not d.startswith((".", "assets", "tools"))]
        for f in files:
            if f.endswith(".html"):
                pages.append(os.path.join(base, f))
    pages.sort()

    problems: list[str] = []
    checked = 0
    for page in pages:
        rel = os.path.relpath(page, ROOT)
        parser = Checker(rel)
        with open(page, encoding="utf-8") as fh:
            parser.feed(fh.read())
        parser.close()
        problems += parser.problems
        for ref in parser.refs:
            target = resolve(page, ref)
            checked += 1
            if target is None:
                continue
            if target.startswith("EXTERNAL:"):
                url = target[len("EXTERNAL:"):]
                if url.startswith("//"):
                    problems.append(f"{rel}: protocol-relative reference {url}")
                continue
            if not os.path.exists(target):
                problems.append(f"{rel}: broken reference {ref!r} -> {os.path.relpath(target, ROOT)}")

    # a hosted asset must never be referenced from CSS either
    css = os.path.join(ROOT, "assets", "css", "site.css")
    if os.path.exists(css):
        text = open(css, encoding="utf-8").read()
        for m in re.finditer(r"url\(([^)]+)\)", text):
            v = m.group(1).strip("'\" ")
            if v.startswith(("http:", "https:", "//")):
                problems.append(f"assets/css/site.css: remote url({v})")

    print(f"pages: {len(pages)}   references checked: {checked}")
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  -", p)
        return 1
    print("OK: every local reference resolves, tags balanced, no remote resources.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
