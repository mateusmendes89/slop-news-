import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

SOURCES_FILE = "sources.json"
OUTPUT_FILE = "news.json"
MAX_ITEMS = 200
PER_SOURCE = 20
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def strip_ns(tag):
    return tag.split("}")[-1]


def child_text(node, name):
    for c in node:
        if strip_ns(c.tag) == name:
            return (c.text or "").strip()
    return ""


def parse_date(text):
    if not text:
        return ""
    try:
        return parsedate_to_datetime(text).astimezone(timezone.utc).isoformat()
    except Exception:
        return text


def entry_link(node):
    for c in node:
        if strip_ns(c.tag) == "link":
            href = c.attrib.get("href")
            if href:
                return href
            if c.text:
                return c.text.strip()
    return ""


def find_image(node):
    for c in node.iter():
        t = strip_ns(c.tag)
        if t in ("thumbnail", "content", "enclosure"):
            url = c.attrib.get("url")
            if not url:
                continue
            kind = c.attrib.get("type", "")
            medium = c.attrib.get("medium", "")
            path = url.lower().split("?")[0]
            if t == "thumbnail" or kind.startswith("image") or medium == "image" or path.endswith(IMG_EXT):
                return __import__("html").unescape(url)
    for c in node.iter():
        t = strip_ns(c.tag)
        if t in ("encoded", "description", "summary", "content") and c.text:
            m = re.search(r'img[^>]+src=["\']([^"\']+)', c.text)
            if m:
                return __import__("html").unescape(m.group(1))
    return ""


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "slop-news/0.3"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return ET.fromstring(resp.read())


def parse(source, root):
    items = []
    nodes = [n for n in root.iter() if strip_ns(n.tag) in ("item", "entry")]
    for n in nodes[:PER_SOURCE]:
        title = child_text(n, "title")
        link = entry_link(n)
        date = child_text(n, "pubDate") or child_text(n, "published") or child_text(n, "updated")
        if title and link:
            items.append({
                "title": title,
                "link": link,
                "source": source["name"],
                "category": source.get("category", "Business"),
                "published": parse_date(date),
                "image": find_image(n),
            })
    return items


def main():
    with open(SOURCES_FILE, encoding="utf-8") as f:
        sources = json.load(f)["sources"]

    seen = {}
    for s in sources:
        try:
            for item in parse(s, fetch(s["url"])):
                seen.setdefault(item["link"], item)
            print("OK   ", s["name"])
        except Exception as exc:
            print("FAIL ", s["name"], exc)

    items = sorted(seen.values(), key=lambda i: i["published"], reverse=True)[:MAX_ITEMS]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "count": len(items),
            "items": items,
        }, f, indent=2, ensure_ascii=False)

    with_img = sum(1 for i in items if i["image"])
    print("Wrote", len(items), "articles,", with_img, "with images")


if __name__ == "__main__":
    sys.exit(main())
