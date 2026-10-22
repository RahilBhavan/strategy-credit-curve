"""Cached fetch of primary-source documents. stdlib only.

Every response is written under data/raw/ and recorded in data/raw/manifest.csv with the URL,
the UTC fetch time and a SHA-256, so each number can be traced to the bytes it came from.
A cached file is never re-fetched unless --refresh is passed.

SEC EDGAR rejects a User-Agent without a contact email (HTTP 403 "Undeclared Automated Tool",
observed 2026-10-21 for "RahilBhavan-research (github.com/RahilBhavan)"). Set SEC_USER_AGENT to
"RahilBhavan-research <contact email>" before fetching from sec.gov.
"""
import csv, datetime as dt, hashlib, os, pathlib, time, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "manifest.csv"
FIELDS = ["path", "url", "fetched_utc", "sha256", "bytes"]
DEFAULT_UA = "RahilBhavan-research (github.com/RahilBhavan)"
BROWSER_UA = "Mozilla/5.0 (X11; Linux x86_64) RahilBhavan-research"
_last = {"t": 0.0}


def _ua(url):
    if "sec.gov" in url:
        return os.environ.get("SEC_USER_AGENT", DEFAULT_UA)
    return os.environ.get("WEB_USER_AGENT", BROWSER_UA)


def manifest():
    if not MANIFEST.exists():
        return {}
    with MANIFEST.open() as f:
        return {r["path"]: r for r in csv.DictReader(f)}


def _record(rel, url, body):
    rows = manifest()
    rows[rel] = {"path": rel, "url": url,
                 "fetched_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
    with MANIFEST.open("w", newline="") as f:
        w = csv.DictWriter(f, FIELDS, lineterminator="\n")
        w.writeheader()
        for k in sorted(rows):
            w.writerow(rows[k])


def get(url, rel, refresh=False, headers=None):
    """Return bytes for url, cached at data/raw/<rel>."""
    path = RAW / rel
    if path.exists() and not refresh:
        return path.read_bytes()
    wait = 0.15 - (time.monotonic() - _last["t"])  # under SEC's 10 requests/s
    if wait > 0:
        time.sleep(wait)
    _last["t"] = time.monotonic()
    h = {"User-Agent": _ua(url), "Accept-Encoding": "identity"}
    h.update(headers or {})
    for backoff in (5, 15, None):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=40) as r:
                body = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and backoff:
                time.sleep(backoff)
                continue
            raise RuntimeError(f"fetch failed, no substitute used: {url}: {e}") from e
    if b"Undeclared Automated Tool" in body[:3000]:
        raise RuntimeError(f"SEC rejected the User-Agent for {url}; set SEC_USER_AGENT")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    _record(rel, url, body)
    return body


def source(rel):
    """Manifest row (url, fetched_utc, sha256) for a cached file."""
    return manifest()[rel]
