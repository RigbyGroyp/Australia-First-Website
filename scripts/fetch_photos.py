#!/usr/bin/env python3
"""Fetch member portrait URLs from Wikipedia (Wikimedia Commons, freely licensed).

For each incumbent, searches Wikipedia, validates the top hit is actually an
Australian politician (via its short description), and records the lead-image
thumbnail URL plus the source page for attribution. Hotlinks the Wikimedia CDN
(upload.wikimedia.org), which is stable and permits reasonable hotlinking.

Output: data/photos.json  ->  { "<candidate id>": {"photo_url","page_url","page_title"} }
Unresolved members (no confident match) are listed but left without a photo.

Usage: python3 scripts/fetch_photos.py
"""

import json
import os
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CANDIDATES = os.path.join(HERE, "..", "data", "candidates.json")
DEST = os.path.join(HERE, "..", "data", "photos.json")
UA = "AUFirstTransparencyDB/1.0 (Wikipedia portrait lookup; +https://github.com/rickybert30/Australia-First-Website)"
POLITICAL = ("politician", "senator", "member of", "mp,", "parliament", "minister")


def api(params):
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def lookup(name, context):
    """Search Wikipedia for the person; return (thumb, title, description) or Nones."""
    d = api({
        "action": "query",
        "generator": "search",
        "gsrsearch": f"{name} {context} Australian politician",
        "gsrlimit": 1,
        "prop": "pageimages|description",
        "piprop": "thumbnail",
        "pithumbsize": 320,
        "format": "json",
        "redirects": 1,
    })
    pages = d.get("query", {}).get("pages", {})
    if not pages:
        return None, None, None
    p = list(pages.values())[0]
    return (p.get("thumbnail", {}).get("source"), p.get("title"), (p.get("description") or ""))


def main():
    data = json.load(open(CANDIDATES))
    incumbents = [c for c in data["candidates"] if c.get("status") == "incumbent"]
    results, unresolved = {}, []

    for c in incumbents:
        context = c.get("electorate") or c.get("state") or ""
        try:
            thumb, title, desc = lookup(c["name"], context)
        except Exception as e:
            unresolved.append((c["id"], f"error: {e}"))
            continue
        is_pol = any(k in desc.lower() for k in POLITICAL)
        if thumb and title and is_pol:
            results[c["id"]] = {
                "photo_url": thumb,
                "page_title": title,
                "page_url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
            }
        else:
            unresolved.append((c["id"], f"title={title!r} desc={desc!r} thumb={bool(thumb)}"))
        time.sleep(0.1)

    json.dump(dict(sorted(results.items())), open(DEST, "w"), indent=2, ensure_ascii=False)
    print(f"Resolved photos: {len(results)}/{len(incumbents)}")
    print(f"Unresolved: {len(unresolved)}")
    for uid, why in unresolved:
        print(f"  - {uid}: {why}")


if __name__ == "__main__":
    main()
