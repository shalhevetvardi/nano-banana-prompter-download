#!/usr/bin/env python3
"""Fail unless index.html links to Aimprove's accessibility statement exactly once.

Run from the repository root:  python3 scripts/check-a11y-link.py
Also fails unless the EqualWeb accessibility widget is present exactly once.
Also fails if the `.footer` CSS rule uses `opacity` or sets a text colour whose contrast
against the page background is below 4.5:1 (the axe-core audit of 12-10-2026 found 2.9:1).
Checks: exactly one anchor with the statement URL as its href, with the exact
visible text, and without a target attribute (the link opens in the same tab).
"""
import re
import sys
from html.parser import HTMLParser

URL = "https://aimprove.co.il/accessibility-statement/"
TEXT = "הצהרת נגישות"
PAGE = "index.html"
# The EqualWeb widget is the inline `window.interdeal` config plus the loader that
# reads `interdeal.domains.js` (cdn.equalweb.com). Each marker must appear exactly once.
WIDGET_MARKERS = ("window.interdeal", "cdn.equalweb.com", "interdeal.domains.js")
# The footer line sits on the flat page background (`--bg` in :root); WCAG AA needs 4.5:1.
PAGE_BG = "#07090f"
MIN_CONTRAST = 4.5
FOOTER_RULE = re.compile(r"(?<![\w-])\.footer\s*\{([^}]*)\}")


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


def luminance(hex_colour):
    channels = []
    for i in (1, 3, 5):
        c = int(hex_colour[i:i + 2], 16) / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(fg, bg):
    hi, lo = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def footer_problems(source):
    rules = FOOTER_RULE.findall(source)
    if len(rules) != 1:
        return ["expected exactly 1 .footer CSS rule, found %d" % len(rules)]
    body = rules[0]
    problems = []
    if re.search(r"(?<![\w-])opacity\s*:", body):
        problems.append(".footer rule uses opacity (dims the text below 4.5:1)")
    colour = re.search(r"(?<![\w-])color\s*:\s*(#[0-9a-fA-F]{6})\s*;", body)
    if not colour:
        problems.append(".footer rule needs an explicit 6-digit hex colour")
    else:
        ratio = contrast(colour.group(1), PAGE_BG)
        if ratio < MIN_CONTRAST:
            problems.append(".footer colour %s on %s is %.2f:1, needs %.1f:1" % (colour.group(1), PAGE_BG, ratio, MIN_CONTRAST))
    return problems


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
    problems.extend(footer_problems(source))
    if problems:
        for problem in problems:
            print("FAIL: " + problem)
        return 1
    print("OK: one accessibility-statement link, exact text, no target, one EqualWeb widget, readable .footer rule")
    return 0


if __name__ == "__main__":
    sys.exit(main())
