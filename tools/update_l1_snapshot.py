#!/usr/bin/env python3
"""Refresh nodepulse/l1-snapshot.json from the Bitnodes crawler export.

NodePulse ships a build-time copy of the Bitnodes L1 snapshot (CoreJBH/nodepulse,
fetch_l1.py -> src/data/l1-data.js). This script produces the same object as a plain
JSON file the site serves, so the app can pick up a fresh snapshot without a new APK
build:

    https://corejbh.github.io/nodepulse/l1-snapshot.json

The shape is exactly the one fetch_l1.py writes (capturedAt, totalNodes, height,
countries, coords, coordCountry, topAsns, userAgents, versions, platforms, ...), and
every value is a value Bitnodes reported for one crawler round. Nothing is estimated,
synthesised or carried over from a previous run: if a piece cannot be fetched, this
script fails and the file keeps what it had.

  /api/v1/snapshots/latest/                     total_nodes, height, timestamp, round metadata
  /api/v1/snapshots/latest/?field=coordinates   the unique geolocated lat/lon pairs
  /api/v1/snapshots/latest/?field=top           top ASNs (TOR and I2P are rows here too)
  /api/v1/nodes/?limit=1000&page=N              per-node country, the one field Bitnodes
                                                only exposes in its paginated node list

Usage: python3 tools/update_l1_snapshot.py [--out PATH]
Run from anywhere; paths resolve from this file's location.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_OUT = os.path.join(ROOT, "nodepulse", "l1-snapshot.json")

BASE = "https://bitnodes.io"
UA = {
    "User-Agent": "Mozilla/5.0 (compatible; nodepulse/1.1; "
    "+https://github.com/CoreJBH/nodepulse)",
    "Accept": "application/json",
}
PAGE = 1000


def get(path: str, tries: int = 3):
    """GET one API path as JSON, retrying transport errors and 5xx a few times."""
    last: Exception | None = None
    for i in range(tries):
        try:
            req = urllib.request.Request(BASE + path, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001 - retry any transport or JSON error
            last = e
            if i + 1 < tries:
                time.sleep(2 + i * 3)
    raise RuntimeError("GET %s failed: %s" % (path, last))


def build() -> dict:
    latest = get("/api/v1/snapshots/latest/")
    coords = get("/api/v1/snapshots/latest/?field=coordinates")
    top = get("/api/v1/snapshots/latest/?field=top")

    stamp = latest["timestamp"]
    total = latest["total_nodes"]
    height = latest["latest_height"]
    meta = latest.get("metadata") or {}

    # The three light endpoints are one round; a mismatch means the crawl rolled over
    # between the calls and the file would mix two rounds under one timestamp.
    for name, payload in (("coordinates", coords), ("top", top)):
        if payload.get("timestamp") != stamp:
            raise RuntimeError(
                "snapshots/latest/?field=%s is round %s, not %s"
                % (name, payload.get("timestamp"), stamp)
            )

    # ---- the paginated node list: country counts and coordinate -> country ----
    first = get("/api/v1/nodes/?limit=%d&page=1" % PAGE)
    count = first["count"]
    if count != total:
        raise RuntimeError(
            "nodes list has %d entries, snapshot says %d total nodes" % (count, total)
        )
    pages = max(1, -(-count // PAGE))
    rows = list(first.get("results") or [])
    if pages > 1:
        def page(n: int):
            return get("/api/v1/nodes/?limit=%d&page=%d" % (PAGE, n))

        with cf.ThreadPoolExecutor(3) as ex:
            for n, res in enumerate(ex.map(page, range(2, pages + 1)), start=2):
                rows.extend(res.get("results") or [])
                print("  page %d/%d  rows %d" % (n, pages, len(rows)))
    if len(rows) != count:
        raise RuntimeError("collected %d rows, expected %d" % (len(rows), count))

    countries: dict[str, int] = {}
    country_names: dict[str, str] = {}
    versions: dict[str, int] = {}
    platforms = {"tor": 0, "i2p": 0, "clearnet": 0}
    coord_country: dict[str, str] = {}
    for r in rows:
        iso = r.get("country") or ""
        if iso == "n/a":
            iso = ""          # Bitnodes' own placeholder for a node it could not locate
        if iso:
            countries[iso] = countries.get(iso, 0) + 1
            name = r.get("country_name")
            if name and name != "n/a":
                country_names.setdefault(iso, name)
        ua = r.get("user_agent") or "n/a"
        versions[ua] = versions.get(ua, 0) + 1
        addr = r.get("address") or ""
        if addr.endswith(".onion"):
            platforms["tor"] += 1
        elif addr.endswith(".i2p"):
            platforms["i2p"] += 1
        else:
            platforms["clearnet"] += 1
        lat, lon = r.get("lat"), r.get("lon")
        # Bitnodes reports 0.0/0.0 for nodes it cannot geolocate (Tor/I2P); not a place.
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and (lat or lon):
            if iso:
                coord_country["%.4f,%.4f" % (lat, lon)] = iso

    # the coordinate endpoint is the authoritative unique-location set Bitnodes publishes
    live_coords = coords.get("coordinates") or []
    coord_list = [[round(float(a), 4), round(float(b), 4)] for a, b in live_coords]
    if not coord_list:
        raise RuntimeError("coordinates endpoint returned no points")

    top_body = top.get("top") or {}
    out = {
        "capturedAt": stamp,
        "source": "https://bitnodes.io/api/v1/snapshots/latest/",
        "totalNodes": total,
        "reachableNodes": meta.get("reachable_nodes"),
        "height": height,
        "round": {"complete": bool(meta.get("complete")), "validatedAt": meta.get("validated_at")},
        "countries": sorted(countries.items(), key=lambda kv: (-kv[1], kv[0])),
        "countryNames": country_names,
        "coordCount": len(coord_list),
        "coords": coord_list,
        "coordCountry": coord_country,
        "userAgents": top_body.get("top_user_agents") or [],
        "topAsns": top_body.get("top_asns") or [],
        "versions": sorted(versions.items(), key=lambda kv: (-kv[1], kv[0]))[:24],
        "platforms": platforms,
        "sampleNodes": len(rows),
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=DEFAULT_OUT, help="output path (default: nodepulse/l1-snapshot.json)")
    args = ap.parse_args()

    out = build()

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    tmp = args.out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    os.replace(tmp, args.out)

    size = os.path.getsize(args.out)
    print(
        "wrote %s (%d bytes): %d nodes, height %d, %d countries, %d coords, "
        "tor %d / i2p %d / clearnet %d, captured %s UTC"
        % (
            os.path.relpath(args.out, ROOT), size, out["totalNodes"], out["height"],
            len(out["countries"]), out["coordCount"], out["platforms"]["tor"],
            out["platforms"]["i2p"], out["platforms"]["clearnet"],
            time.strftime("%Y-%m-%d %H:%M", time.gmtime(out["capturedAt"])),
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
