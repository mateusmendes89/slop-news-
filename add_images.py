import html
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor

FILE = "news.json"
PATTERNS = [
    r'meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
    r'meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    r'meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',
]


def og_image(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (slop-news)"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            page = resp.read(200000).decode("utf-8", "ignore")
        for pat in PATTERNS:
            m = re.search(pat, page)
            if m:
                return html.unescape(m.group(1))
    except Exception:
        pass
    return ""


def main():
    with open(FILE, encoding="utf-8") as f:
        data = json.load(f)

    missing = [i for i in data["items"] if not i.get("image")]
    print("Looking for pictures for", len(missing), "articles...")

    filled = 0
    with ThreadPoolExecutor(8) as pool:
        for item, img in zip(missing, pool.map(lambda i: og_image(i["link"]), missing)):
            if img:
                item["image"] = img
                filled += 1

    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("Found", filled, "new pictures")


if __name__ == "__main__":
    main()
