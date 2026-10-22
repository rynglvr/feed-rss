#!/usr/bin/env python3
"""Convert Muse Feed units (JSON) to an RSS 2.0 feed.

Input: a JSON file containing a list of unit objects, newest first:
  {
    "unit_id": "uuid",
    "title": "Post title",
    "kicker": "KICKER TEXT",
    "category": "Category name",
    "body_md": "Markdown body ...",
    "created_at_ms": 1792686444481
  }

Usage:
  python3 build_feed.py units.json [--out feed.xml]

Stdlib only. Channel metadata is fixed for Ryan's Muse Feed / the
rynglvr/feed-rss GitHub repo.
"""
import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from email.utils import format_datetime

CHANNEL_TITLE = "Ryan's Muse Feed"
CHANNEL_LINK = "https://github.com/rynglvr/feed-rss"
CHANNEL_DESC = ("Ryan's personal Muse Feed \u2014 daily digests, Daily Learning, "
                "music updates and more, as an RSS feed.")
SELF_URL = "https://raw.githubusercontent.com/rynglvr/feed-rss/main/feed.xml"

COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
URL_RE = re.compile(r"https?://[^\s)\]]+")
LINK_RE = re.compile(r"\[([^\]]*)\]\((https?://[^)\s]+)(?:\s+\"[^\"]*\")?\)")
IMG_RE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")


def clean(text: str) -> str:
    """Strip HTML comments and any local workspace paths."""
    text = COMMENT_RE.sub("", text or "")
    text = re.sub(r"(?:/home/|~/|sandbox://)workspace/[^\s)\]]*", "", text)
    return text.strip()


def first_url(text: str):
    m = URL_RE.search(text or "")
    return m.group(0).rstrip(".,;") if m else None


def inline_html(text: str) -> str:
    """Convert inline markdown (links, bold, italic, code) to HTML."""
    text = html.escape(text)
    # links: text was escaped first, so rebuild from the escaped form
    text = re.sub(r"\[([^\]]*)\]\((https?://[^)\s]+)\)",
                  r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\w)\*([^*\n]+)\*(?!\w)", r"<em>\1</em>", text)
    text = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def md_to_html(md: str) -> str:
    md = clean(md)
    if not md:
        return ""
    blocks = re.split(r"\n\s*\n", md)
    out = []
    for block in blocks:
        lines = [ln.rstrip() for ln in block.strip().split("\n") if ln.strip()]
        if not lines:
            continue
        # Heading (single-line block)
        hm = re.match(r"^(#{1,6})\s+(.*)$", lines[0]) if len(lines) == 1 else None
        if hm:
            level = len(hm.group(1))
            out.append(f"<h{level}>{inline_html(hm.group(2))}</h{level}>")
            continue
        # Bullet list: every line starts with -, * or bullet char
        if all(re.match(r"^\s*[-*\u2022]\s+", ln) for ln in lines):
            items = "".join(
                f"<li>{inline_html(re.sub(r'^\\s*[-*\\u2022]\\s+', '', ln))}</li>"
                for ln in lines)
            out.append(f"<ul>{items}</ul>")
            continue
        out.append("<p>" + "<br/>".join(inline_html(ln) for ln in lines) + "</p>")
    return "\n".join(out)


def plain_text(md: str, limit: int = 400) -> str:
    text = clean(md)
    text = IMG_RE.sub(r"\1", text)
    text = LINK_RE.sub(r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.M)
    text = re.sub(r"[*_`>#]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        cut = text[:limit].rsplit(" ", 1)[0]
        text = cut + "\u2026"
    return text


def rfc822_from_ms(ms) -> str:
    dt = datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc)
    return format_datetime(dt, usegmt=True)


def build(units: list) -> str:
    now = format_datetime(datetime.now(timezone.utc), usegmt=True)
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" '
           'xmlns:content="http://purl.org/rss/1.0/modules/content/">',
           '  <channel>',
           f'    <title>{html.escape(CHANNEL_TITLE)}</title>',
           f'    <link>{html.escape(CHANNEL_LINK)}</link>',
           f'    <description>{html.escape(CHANNEL_DESC)}</description>',
           '    <language>en-us</language>',
           f'    <lastBuildDate>{now}</lastBuildDate>',
           f'    <atom:link href="{html.escape(SELF_URL, quote=True)}" '
           'rel="self" type="application/rss+xml"/>']
    for u in units:
        title = (u.get("title") or "").strip()
        body = u.get("body_md") or ""
        if not title and not body.strip():
            continue
        if not title:
            title = (u.get("kicker") or "Untitled").strip()
        link = first_url(clean(body)) or f"{CHANNEL_LINK}#{u.get('unit_id','')}"
        out.append('    <item>')
        out.append(f'      <title>{html.escape(title)}</title>')
        out.append(f'      <link>{html.escape(link)}</link>')
        out.append(f'      <guid isPermaLink="false">'
                   f'{html.escape(str(u.get("unit_id", "")))}</guid>')
        if u.get("created_at_ms"):
            out.append(f'      <pubDate>{rfc822_from_ms(u["created_at_ms"])}</pubDate>')
        if u.get("category"):
            out.append(f'      <category>{html.escape(u["category"])}</category>')
        out.append(f'      <description>{html.escape(plain_text(body))}</description>')
        content_html = md_to_html(body)
        cdata = content_html.replace("]]>", "]]]]><![CDATA[>")
        out.append(f'      <content:encoded><![CDATA[{cdata}]]></content:encoded>')
        out.append('    </item>')
    out.append('  </channel>')
    out.append('</rss>')
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("units_json", help="JSON file with a list of unit objects")
    ap.add_argument("--out", default=None, help="Write here instead of stdout")
    args = ap.parse_args()
    with open(args.units_json, encoding="utf-8") as f:
        units = json.load(f)
    xml = build(units)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(xml)
    else:
        sys.stdout.write(xml)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
