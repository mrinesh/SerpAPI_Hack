"""Spike S-01: tabulate what the recorded SerpApi responses contain. Reads fixtures only.

    uv run python scripts/s01_analyze.py

Prints, per query: how many results come from the target portals, the URL pattern of each
result, and which listing facts appear in the snippet. Then field coverage across all portal
results, and what Google Maps / Local return. Findings are written up by hand in
docs/spikes/S-01-data-coverage.md.
"""

import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "serpapi"
PORTALS = {"99acres.com": "99acres", "magicbricks.com": "magicbricks", "nobroker.in": "nobroker"}

# Candidate facts in snippet text. These are what the spike measures, not final parsers.
FACTS = {
    "price": re.compile(
        r"₹\s?[\d.,]+\s*(?:Lacs?|Lakhs?|Cr|Crores?)\b|₹\s?\d{1,3}(?:,\d{2,3})+", re.I
    ),
    "price_per_sqft": re.compile(r"₹\s?[\d,]+\s*/\s*sq\.?\s?ft", re.I),
    "area": re.compile(r"\b[\d,]{3,6}\s*(?:sq\.?\s?ft|sqft|sq\.?\s?m|sqm|sq\.?\s?yd)\b", re.I),
    "bhk": re.compile(r"\b\d\s?BHK\b", re.I),
    "status": re.compile(r"ready to move|under construction|resale|new launch", re.I),
    "listing_count": re.compile(r"\b\d[\d,]*\+?\s+(?:properties|flats|houses|apartments)", re.I),
}


def url_pattern(url: str) -> str:
    """Last path segment with digits and words collapsed, e.g. '...-ffid', '...-pppfs'."""
    path = urlparse(url).path.rstrip("/")
    tail = re.sub(r"/page-\d+$", "", path).rsplit("/", 1)[-1]
    tail = re.sub(r"-page-\d+$", "", tail)
    return tail.rsplit("-", 1)[-1] if "-" in tail else tail


def portal_of(url: str) -> str | None:
    host = urlparse(url).netloc.removeprefix("www.")
    return PORTALS.get(host)


def main() -> None:
    coverage: Counter[tuple[str, str]] = Counter()
    portal_results: Counter[str] = Counter()
    patterns: Counter[tuple[str, str]] = Counter()

    for path in sorted((FIXTURES / "google").glob("*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        q, start = fixture["params"]["q"], fixture["params"].get("start", 0)
        results = fixture["response"].get("organic_results", [])
        on_target = [r for r in results if portal_of(r.get("link", ""))]
        print(f"\n[{len(on_target)}/{len(results)} portal] start={start} {q}")
        for r in results:
            portal = portal_of(r.get("link", ""))
            if not portal:
                continue
            portal_results[portal] += 1
            pattern = url_pattern(r["link"])
            patterns[(portal, pattern)] += 1
            text = f"{r.get('title', '')} {r.get('snippet', '')}"
            found = [name for name, rx in FACTS.items() if rx.search(text)]
            for name in found:
                coverage[(portal, name)] += 1
            rich = "Y" if r.get("rich_snippet") else "-"
            print(f"   {portal:11} {pattern:8} rich={rich} {','.join(found)}")

    print("\n== URL patterns (portal, last segment) ==")
    for (portal, pattern), n in patterns.most_common():
        print(f"   {portal:11} {pattern:12} {n}")
    print("\n== Fact coverage in title+snippet, share of portal results ==")
    for portal, total in portal_results.items():
        shares = ", ".join(f"{name} {coverage[(portal, name)] * 100 // total}%" for name in FACTS)
        print(f"   {portal:11} n={total:3}  {shares}")

    for engine in ("google_maps", "google_local"):
        print(f"\n== {engine} ==")
        for path in sorted((FIXTURES / engine).glob("*.json")):
            fixture = json.loads(path.read_text(encoding="utf-8"))
            results = fixture["response"].get("local_results", [])
            types = Counter(r.get("type") for r in results)
            with_gps = sum(1 for r in results if r.get("gps_coordinates"))
            print(f"   {fixture['params']['q']!r}: {len(results)} results, {with_gps} with GPS")
            print(f"      types: {dict(types.most_common(6))}")


if __name__ == "__main__":
    main()
