"""fetchlib.py -- download helper that records provenance for every raw file.

Every file written under raw/ gets an entry in raw/manifest.json with:
url, method, request payload (if any), retrieval time (UTC), sha256, size,
license, and free-text notes. The file table at the end of SOURCES.md is generated
from the manifest by `python3 fetch.py sources`.

Rules this helper enforces:
  * only GET/POST requests to public dataset APIs and file hosts;
  * at least MIN_GAP seconds between successive requests to the same host;
  * a hard refusal to download any single file larger than MAX_FILE bytes
    (checked from Content-Length when the server sends it, and while streaming).
"""

import datetime as _dt
import hashlib
import json
import os
import time
import urllib.parse

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
MANIFEST = os.path.join(RAW, "manifest.json")
UA = "Mozilla/5.0 (X11; Linux x86_64) research-dataset-download (no measurement)"
MIN_GAP = 2.0                     # seconds between requests to one host
MAX_FILE = int(1.5 * 1024 ** 3)   # 1.5 GB hard cap per file

_last_hit = {}


def now_utc():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path, bufsize=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(bufsize)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def load_manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            return json.load(f)
    return {"files": {}}


def save_manifest(m):
    os.makedirs(RAW, exist_ok=True)
    tmp = MANIFEST + ".tmp"
    with open(tmp, "w") as f:
        json.dump(m, f, indent=1, sort_keys=True)
    os.replace(tmp, MANIFEST)


def record(relpath, url, license, notes="", method="GET", payload=None,
           retrieved=None, extra=None):
    """Add/refresh the manifest entry for raw/<relpath> (file must exist).

    The read-modify-write of manifest.json happens under an exclusive lock so
    that concurrent fetch steps cannot drop each other's entries."""
    import fcntl
    path = os.path.join(RAW, relpath)
    ent = {
        "url": url,
        "method": method,
        "retrieved_utc": retrieved or now_utc(),
        "sha256": sha256_file(path),
        "size_bytes": os.path.getsize(path),
        "license": license,
        "notes": notes,
    }
    if payload is not None:
        ent["request_payload"] = payload
    if extra:
        ent.update(extra)
    os.makedirs(RAW, exist_ok=True)
    with open(os.path.join(RAW, ".manifest.lock"), "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        m = load_manifest()
        m["files"][relpath] = ent
        save_manifest(m)
        fcntl.flock(lk, fcntl.LOCK_UN)
    return ent


def _pace(url):
    host = urllib.parse.urlparse(url).netloc
    last = _last_hit.get(host)
    if last is not None:
        wait = MIN_GAP - (time.time() - last)
        if wait > 0:
            time.sleep(wait)
    _last_hit[host] = time.time()


def fetch(url, relpath, license, notes="", method="GET", json_payload=None,
          params=None, headers=None, timeout=600, skip_if_exists=True,
          max_bytes=MAX_FILE):
    """Download url to raw/<relpath> and record provenance.

    Returns the manifest entry. If the file already exists and is recorded in
    the manifest, it is not downloaded again (skip_if_exists=True).
    """
    path = os.path.join(RAW, relpath)
    m = load_manifest()
    if skip_if_exists and os.path.exists(path) and relpath in m["files"]:
        return m["files"][relpath]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _pace(url)
    hdrs = {"User-Agent": UA}
    if headers:
        hdrs.update(headers)
    full_url = url
    if params:
        full_url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    t0 = now_utc()
    if method == "GET":
        r = requests.get(full_url, headers=hdrs, timeout=timeout, stream=True)
    elif method == "POST":
        r = requests.post(full_url, headers=hdrs, json=json_payload,
                          timeout=timeout, stream=True)
    else:
        raise ValueError(method)
    r.raise_for_status()
    cl = r.headers.get("Content-Length")
    if cl is not None and int(cl) > max_bytes:
        r.close()
        raise RuntimeError(f"refusing {full_url}: Content-Length {cl} > cap")
    n = 0
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        for chunk in r.iter_content(1 << 20):
            n += len(chunk)
            if n > max_bytes:
                f.close()
                os.remove(tmp)
                raise RuntimeError(f"refusing {full_url}: exceeded cap while streaming")
            f.write(chunk)
    os.replace(tmp, path)
    extra = {"http_status": r.status_code,
             "content_type": r.headers.get("Content-Type"),
             "last_modified_header": r.headers.get("Last-Modified")}
    return record(relpath, full_url, license, notes, method=method,
                  payload=json_payload, retrieved=t0, extra=extra)
