#!/usr/bin/env python3
"""Fail unless index.html links to Aimprove's accessibility statement exactly once.

Run from the repository root:  python3 scripts/check-a11y-link.py
Also fails unless the EqualWeb accessibility widget is present exactly once.
Checks: exactly one anchor with the statement URL as its href, with the exact
visible text, and without a target attribute (the link opens in the same tab).
"""
import sys
from html.parser import HTMLParser

URL = "https://aimprove.co.il/accessibility-statement/"
TEXT = "הצהרת נגישות"
PAGE = "index.html"
# The EqualWeb widget is the inline `window.interdeal` config plus the loader that
# reads `interdeal.domains.js` (cdn.equalweb.com). Each marker must appear exactly once.
WIDGET_MARKERS = ("window.interdeal", "cdn.equalweb.com", "interdeal.domains.js")


class Collector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.anchors = []  # each: {"attrs": dict, "text": str}
        self._open = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._open = {"attrs": dict(attrs), "text": ""}
            self.anchors.append(self._open)

    def handle_endtag(self, tag):
        if tag == "a":
            self._open = None

    def handle_data(self, data):
        if self._open is not None:
            self._open["text"] += data


def main():
    try:
        with open(PAGE, encoding="utf-8") as fh:
            source = fh.read()
    except OSError as exc:
        print("FAIL: cannot read %s: %s" % (PAGE, exc))
        return 1

    collector = Collector()
    collector.feed(source)
    matches = [a for a in collector.anchors if a["attrs"].get("href") == URL]

    problems = []
    if len(matches) != 1:
        problems.append("expected exactly 1 anchor with href %s, found %d" % (URL, len(matches)))
    else:
        anchor = matches[0]
        if anchor["text"] != TEXT:
            problems.append("anchor text is %r, expected %r" % (anchor["text"], TEXT))
        if "target" in anchor["attrs"]:
            problems.append("the anchor has a target attribute (%r)" % anchor["attrs"]["target"])
    for marker in WIDGET_MARKERS:
        found = source.count(marker)
        if found != 1:
            problems.append("expected exactly 1 occurrence of %r (EqualWeb widget), found %d" % (marker, found))
    if problems:
        for problem in problems:
            print("FAIL: " + problem)
        return 1
    print("OK: one accessibility-statement link, exact text, no target, one EqualWeb widget")
    return 0


if __name__ == "__main__":
    sys.exit(main())
