#!/usr/bin/env python3
"""
fetch_raw.py -- download every raw input of the Snowflake analysis into raw/.

Only existing public datasets and public dataset APIs are contacted:
  * Tor CollecTor (snowflake-stats archive + recent, and its index),
  * Tor Metrics CSV exports (userstats-bridge-combined, userstats-bridge-transport),
  * the IODA outage-events API (country level),
  * git clones of four public gitlab.torproject.org repositories (metrics timeline,
    rdsys-admin, snowflake, and a shallow clone of tor for its ReleaseNotes),
  * the GitHub REST API for two net4people/bbs issues (4 calls in total),
  * usenix.org / arxiv.org for two published papers (proxy-churn figures are
    taken only from these publications).
No measured endpoint, front domain, STUN server, broker, proxy, or blocked name is
ever resolved or contacted.  HTTP requests are paced >= 1.5 s apart.

Usage:
    python3 fetch_raw.py                      # fetch everything missing
    python3 fetch_raw.py --only collector ioda
    python3 fetch_raw.py --refresh            # re-download even if present
    python3 fetch_raw.py --paper-commits      # export the git sources at PAPER_COMMITS
Sections: collector, tormetrics, ioda, gitlab, github, lit

Every raw file gets a record in raw/manifest.json: path, url, retrieved_utc,
sha256, size_bytes, license, redistribute, source, notes (+ git commit, or the
upstream CollecTor sha256 check).  SOURCES.md summarises the same information.
"""

import argparse
import base64
import datetime as dt
import hashlib
import json
import lzma
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
MANIFEST = RAW / "manifest.json"

UA = "Mozilla/5.0 (X11; Linux x86_64) research-dataset-download (no scanning)"
PACE_S = 1.5

# Fixed analysis window (retrieval date 2026-10-03).
TM_START, TM_END = "2019-01-01", "2026-10-03"
IODA_START, IODA_END = "2019-01-01", "2026-10-04"
TM_COUNTRIES = ["ru", "ir", "cn", "tm"]
IODA_COUNTRIES = ["IR", "RU", "CN", "TM"]

# Heads of the git sources at the paper's retrieval (2026-10-03), as recorded in
# raw/manifest.json.  --paper-commits checks these out after cloning; without it the
# clones stay at their current heads.  The tor clone is shallow and always uses the
# head of release-0.4.8 (analysis.py does not read it).
PAPER_COMMITS = {
    "timeline": "e193b45c8be5b86810638d50f753cd409f052d48",
    "rdsys-admin": "0061ce86ee2dfc8c451a78d28d0ef09e4ed7f36e",
    "snowflake": "9850fbe31535ea0fde39ff9f12970c3c1ee808d3",
}

LIC_TOR = "CC0 1.0 (Tor Metrics / CollecTor data; https://metrics.torproject.org/about.html)"
LIC_IODA = ("Copyright Georgia Tech Research Corporation, all rights reserved "
            "(per API response). Cite IODA; do NOT redistribute raw responses.")
LIC_TIMELINE = "CC0 1.0 (COPYING in the metrics/timeline repository)"
LIC_RDSYS = ("No LICENSE file in rdsys-admin. Used for dated facts only "
             "(which front/STUN names were configured when); do not redistribute the raw file.")
LIC_SNOWFLAKE = "BSD-3-Clause (LICENSE in the snowflake repository)"
LIC_TOR_SRC = "BSD-3-Clause (tor source tree)"
LIC_GITHUB = ("GitHub issue content posted by net4people/bbs users; no license. "
              "Quote briefly with citation; do not redistribute the raw JSON.")
LIC_USENIX = ("USENIX open-access proceedings; copyright with the authors. "
              "Cite; do not redistribute the PDF.")
LIC_ARXIV = ("arXiv non-exclusive distribution license "
             "(arxiv.org/licenses/nonexclusive-distrib/1.0/). Cite; do not redistribute the PDF.")


def utcnow():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Manifest:
    def __init__(self):
        self.recs = {}
        if MANIFEST.exists():
            for r in json.loads(MANIFEST.read_text()):
                self.recs[r["path"]] = r

    def add(self, relpath, url, license, redistribute, source, notes="", retrieved=None, **extra):
        p = RAW / relpath
        rec = dict(path=str(relpath), url=url, retrieved_utc=retrieved or utcnow(),
                   sha256=sha256_file(p), size_bytes=p.stat().st_size,
                   license=license, redistribute=redistribute, source=source, notes=notes)
        rec.update(extra)
        self.recs[str(relpath)] = rec
        return rec

    def save(self):
        RAW.mkdir(parents=True, exist_ok=True)
        out = sorted(self.recs.values(), key=lambda r: r["path"])
        MANIFEST.write_text(json.dumps(out, indent=1, sort_keys=False) + "\n")


class Fetcher:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = UA
        self.last = 0.0
        self.n = 0

    def get(self, url, **kw):
        wait = PACE_S - (time.time() - self.last)
        if wait > 0:
            time.sleep(wait)
        for attempt in range(4):
            try:
                r = self.s.get(url, timeout=180, **kw)
                self.last = time.time()
                self.n += 1
                if r.status_code in (429, 502, 503, 504):
                    time.sleep(10 * (attempt + 1))
                    continue
                if r.status_code == 404:
                    return None
                r.raise_for_status()
                return r
            except requests.RequestException:
                self.last = time.time()
                if attempt == 3:
                    raise
                time.sleep(10 * (attempt + 1))
        raise RuntimeError("unreachable")

    def save(self, url, relpath, refresh=False, **kw):
        """Download url to raw/relpath. Returns (path, retrieved_utc or None if skipped).
        Returns (None, None) if the server answers 404."""
        p = RAW / relpath
        if p.exists() and not refresh:
            return p, None
        p.parent.mkdir(parents=True, exist_ok=True)
        r = self.get(url, **kw)
        if r is None:
            print("  -- 404 (skipped):", url)
            return None, None
        ts = utcnow()
        tmp = p.with_suffix(p.suffix + ".part")
        tmp.write_bytes(r.content)
        tmp.replace(p)
        return p, ts


# ---------------------------------------------------------------------------
# 1. CollecTor snowflake-stats
# ---------------------------------------------------------------------------
def fetch_collector(F, M, refresh):
    base = "https://collector.torproject.org"
    rel = Path("collector/index.json.xz")
    p, ts = F.save(f"{base}/index/index.json.xz", rel, refresh=True)  # always refresh the index
    M.add(rel, f"{base}/index/index.json.xz", LIC_TOR, True, "Tor CollecTor index",
          "CollecTor file index; used to list snowflake files and verify their sha256.", retrieved=ts)
    idx = json.loads(lzma.decompress(p.read_bytes()))

    def find_dir(node, parts):
        for d in node.get("directories", []):
            if d["path"] == parts[0]:
                return d if len(parts) == 1 else find_dir(d, parts[1:])
        return None

    for sub in (("archive", "snowflakes"), ("recent", "snowflakes")):
        d = find_dir(idx, list(sub))
        if d is None:
            print("  !! index has no", "/".join(sub))
            continue
        for f in sorted(d.get("files", []), key=lambda x: x["path"]):
            url = f"{base}/{sub[0]}/{sub[1]}/{f['path']}"
            relf = Path("collector") / sub[0] / f["path"]
            p, ts = F.save(url, relf, refresh=refresh)
            if p is None:  # listed in the index but already rotated out of recent/
                continue
            up = base64.b64decode(f["sha256"]).hex()
            ok = (sha256_file(p) == up)
            if not ok and ts is None:  # stale local copy; re-download once
                p, ts = F.save(url, relf, refresh=True)
                ok = (sha256_file(p) == up)
            prev = M.recs.get(str(relf), {})
            M.add(relf, url, LIC_TOR, True, "Tor CollecTor snowflake-stats",
                  "Snowflake broker daily statistics (spec: snowflake doc/broker-spec.txt).",
                  retrieved=ts or prev.get("retrieved_utc"),
                  upstream_sha256=up, upstream_sha256_match=ok,
                  upstream_last_modified=f.get("last_modified"))
            if not ok:
                print("  !! sha256 mismatch vs CollecTor index:", relf)
        print(f"  collector {'/'.join(sub)}: {len(d.get('files', []))} files")


# ---------------------------------------------------------------------------
# 2. Tor Metrics CSVs
# ---------------------------------------------------------------------------
def fetch_tormetrics(F, M, refresh):
    base = "https://metrics.torproject.org"
    for cc in TM_COUNTRIES:
        url = f"{base}/userstats-bridge-combined.csv?start={TM_START}&end={TM_END}&country={cc}"
        rel = Path(f"tormetrics/userstats-bridge-combined_{cc}.csv")
        p, ts = F.save(url, rel, refresh=refresh)
        prev = M.recs.get(str(rel), {})
        M.add(rel, url, LIC_TOR, True, "Tor Metrics userstats-bridge-combined",
              "Daily estimated bridge users by country x transport; columns low, high, frac "
              "(no point estimate).", retrieved=ts or prev.get("retrieved_utc"))
    url = f"{base}/userstats-bridge-transport.csv?start={TM_START}&end={TM_END}"
    rel = Path("tormetrics/userstats-bridge-transport_all.csv")
    p, ts = F.save(url, rel, refresh=refresh)
    prev = M.recs.get(str(rel), {})
    M.add(rel, url, LIC_TOR, True, "Tor Metrics userstats-bridge-transport",
          "Daily estimated bridge users by transport, all countries.",
          retrieved=ts or prev.get("retrieved_utc"))
    print("  tormetrics: done")


# ---------------------------------------------------------------------------
# 3. IODA outage events (country level)
# ---------------------------------------------------------------------------
def fetch_ioda(F, M, refresh):
    base = "https://api.ioda.inetintel.cc.gatech.edu/v2/outages/events"
    t0 = dt.datetime.fromisoformat(IODA_START).replace(tzinfo=dt.timezone.utc)
    tend = dt.datetime.fromisoformat(IODA_END).replace(tzinfo=dt.timezone.utc)
    for cc in IODA_COUNTRIES:
        y = t0
        while y < tend:
            nxt = min(y.replace(year=y.year + 1), tend)
            a, b = int(y.timestamp()), int(nxt.timestamp())
            url = (f"{base}?entityType=country&entityCode={cc}&from={a}&until={b}"
                   f"&limit=2000")
            rel = Path(f"ioda/outage_events_{cc}_{y.year}.json")
            p, ts = F.save(url, rel, refresh=refresh)
            n = len(json.loads(p.read_text()).get("data") or [])
            if n >= 2000:
                print("  !! IODA limit reached; split the window:", rel)
            prev = M.recs.get(str(rel), {})
            M.add(rel, url, LIC_IODA, False, "IODA outage events API v2",
                  f"Country-level outage events ({n} records); used only to derive "
                  "shutdown-exclusion day masks.", retrieved=ts or prev.get("retrieved_utc"))
            y = nxt
    print("  ioda: done")


# ---------------------------------------------------------------------------
# 4. GitLab repositories (git clones and exports)
# ---------------------------------------------------------------------------
def git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True).stdout


def git_bytes(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True).stdout


def clone(url, dest, commit=None):
    if dest.exists():
        shutil.rmtree(dest)
    time.sleep(PACE_S)
    git("clone", "--quiet", url, str(dest))
    if commit:  # --paper-commits: export from this commit instead of the current head
        git("checkout", "--quiet", "--detach", commit, cwd=dest)
    return git("rev-parse", "HEAD", cwd=dest).strip(), utcnow()


def export_blob(repo, commit, path, rel, M, url, lic, redist, source, notes, ts):
    out = RAW / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(git_bytes("show", f"{commit}:{path}", cwd=repo))
    M.add(rel, f"{url} @ {commit} : {path}", lic, redist, source, notes, retrieved=ts,
          git_repo=url, git_commit=commit, git_path=path)


def fetch_gitlab(F, M, refresh, clone_dir, pins=None):
    clone_dir.mkdir(parents=True, exist_ok=True)
    pins = pins or {}

    # 4a. Tor Metrics timeline (GitLab project 644)
    url = "https://gitlab.torproject.org/tpo/network-health/metrics/timeline.git"
    repo = clone_dir / "timeline"
    head, ts = clone(url, repo, pins.get("timeline"))
    for path in ("README.md", "COPYING"):
        export_blob(repo, head, path, Path(f"gitlab/metrics-timeline/{path}"), M, url,
                    LIC_TIMELINE, True, "Tor Metrics timeline (git)",
                    "README.md holds the dated event table (rendered at metrics.torproject.org/news.html).",
                    ts)

    # 4b. rdsys-admin conf/circumvention.json history (GitLab project 739)
    url = "https://gitlab.torproject.org/tpo/anti-censorship/rdsys-admin.git"
    repo = clone_dir / "rdsys-admin"
    head, ts = clone(url, repo, pins.get("rdsys-admin"))
    for target in ("conf/circumvention.json", "conf/circumvention_defaults.json"):
        log = git("log", "--follow", "--format=COMMIT%x09%H%x09%aI%x09%cI%x09%s",
                  "--name-status", "--", target, cwd=repo)
        rows, cur = [], None
        for ln in log.splitlines():
            if ln.startswith("COMMIT\t"):
                _, h, ad, cd, subj = ln.split("\t", 4)
                cur = dict(commit=h, author_date=ad, commit_date=cd, subject=subj)
                rows.append(cur)
            elif ln.strip() and cur is not None:
                parts = ln.split("\t")
                cur["status"] = parts[0]
                cur["path"] = parts[-1]
        stem = Path(target).stem
        lines = ["commit\tauthor_date\tcommit_date\tstatus\tpath\tsubject\texported_as"]
        for r in rows:
            exp = ""
            if not r.get("status", "M").startswith("D"):
                cd = dt.datetime.fromisoformat(r["commit_date"]).astimezone(dt.timezone.utc)
                exp = f"gitlab/rdsys-admin/{stem}/{cd:%Y%m%dT%H%M%SZ}_{r['commit'][:10]}.json"
                export_blob(repo, r["commit"], r["path"], Path(exp), M, url, LIC_RDSYS, False,
                            "rdsys-admin config history (git)",
                            f"Version of {r['path']} at commit '{r['subject']}'.", ts)
            lines.append("\t".join([r["commit"], r["author_date"], r["commit_date"],
                                    r.get("status", ""), r.get("path", ""), r["subject"], exp]))
        rel = Path(f"gitlab/rdsys-admin/{stem}_log.tsv")
        (RAW / rel).write_text("\n".join(lines) + "\n")
        M.add(rel, f"{url} @ {head} : git log --follow -- {target}", LIC_RDSYS, False,
              "rdsys-admin config history (git)", f"{len(rows)} commits touching {target}.",
              retrieved=ts, git_repo=url, git_commit=head, git_path=target)

    # 4c. snowflake repository: metric definitions and the 2025 counting changes
    url = "https://gitlab.torproject.org/tpo/anti-censorship/pluggable-transports/snowflake.git"
    repo = clone_dir / "snowflake"
    head, ts = clone(url, repo, pins.get("snowflake"))
    for path in ("doc/broker-spec.txt", "ChangeLog", "LICENSE"):
        export_blob(repo, head, path, Path(f"gitlab/snowflake/{Path(path).name}"), M, url,
                    LIC_SNOWFLAKE, True, "snowflake source (git)",
                    "Broker metrics specification / changelog.", ts)
    # short hashes as listed by `git log` on 2026-10-03; resolved to full hashes here
    for c, why in (("c8b0b31",
                    "Clear map of seen proxy IPs: before this, snowflake-ips counted IPs new since the last broker restart (deployed 2025-08-20 13:40 per timeline)."),
                   ("31f879a",
                    "Geolocate AMP-cache clients from the SDP (deployed 2025-08-20 13:40 per timeline)."),
                   ("b512e24",
                    "Per-rendezvous-method client IP tracking (per-country method split)."),
                   ("26ceb6e",
                    "Add metrics for tracking rendezvous method.")):
        full = git("rev-parse", "--verify", f"{c}^{{commit}}", cwd=repo).strip()
        rel = Path(f"gitlab/snowflake/commit_{full[:10]}.patch")
        (RAW / rel).write_bytes(git_bytes("show", "--format=fuller", full, cwd=repo))
        M.add(rel, f"{url} @ {full}", LIC_SNOWFLAKE, True, "snowflake source (git)", why,
              retrieved=ts, git_repo=url, git_commit=full)
    rel = Path("gitlab/snowflake/broker_metrics_log.tsv")
    (RAW / rel).write_text(git("log", "--format=%H%x09%aI%x09%cI%x09%s", "--",
                               "broker/metrics.go", "broker/amp.go", "broker/ipc.go", cwd=repo))
    M.add(rel, f"{url} @ {head} : git log -- broker/metrics.go broker/amp.go broker/ipc.go",
          LIC_SNOWFLAKE, True, "snowflake source (git)", "Commit log of broker metrics code.",
          retrieved=ts, git_repo=url, git_commit=head)

    # 4d. tor ReleaseNotes for the 0.4.8.22 user-counting change.  The GitLab "raw" URL
    # answers with a sign-in page, so use a shallow, blob-less clone of release-0.4.8
    # (only the blobs actually read are transferred).
    url = "https://gitlab.torproject.org/tpo/core/tor.git"
    repo = clone_dir / "tor"
    if repo.exists():
        shutil.rmtree(repo)
    time.sleep(PACE_S)
    git("clone", "--quiet", "--filter=blob:none", "--no-checkout", "--depth", "1",
        "--branch", "release-0.4.8", url, str(repo))
    head, ts = git("rev-parse", "HEAD", cwd=repo).strip(), utcnow()
    for path in ("ReleaseNotes", "LICENSE"):
        export_blob(repo, head, path, Path(f"gitlab/tor/{path}_release-0.4.8"), M, url,
                    LIC_TOR_SRC, True, "tor source (git, branch release-0.4.8)",
                    "The 0.4.8.22 entry documents the consensus-download counting change.", ts)
    stale = RAW / "gitlab/tor/ReleaseNotes_release-0.4.8"
    if stale.exists() and stale.read_bytes()[:15].lower().startswith(b"<!doctype html"):
        raise RuntimeError("tor ReleaseNotes export is an HTML page")
    print("  gitlab: done")


# ---------------------------------------------------------------------------
# 5. GitHub: net4people/bbs issues 197 (Iran, cdn.sstatic.net) and 603 (Russia, DTLS 2026)
# ---------------------------------------------------------------------------
def fetch_github(F, M, refresh):
    for num in (197, 603):
        for suffix, rel in (("", f"github/net4people_bbs_issue{num}.json"),
                            ("/comments?per_page=100", f"github/net4people_bbs_issue{num}_comments.json")):
            url = f"https://api.github.com/repos/net4people/bbs/issues/{num}{suffix}"
            p, ts = F.save(url, Path(rel), refresh=refresh,
                           headers={"Accept": "application/vnd.github+json"})
            prev = M.recs.get(rel, {})
            M.add(Path(rel), url, LIC_GITHUB, False, "GitHub REST API (unauthenticated)",
                  f"net4people/bbs issue #{num}{' comments' if suffix else ''}.",
                  retrieved=ts or prev.get("retrieved_utc"))
    print("  github: done")


# ---------------------------------------------------------------------------
# 6. Publications used for proxy-churn figures
# ---------------------------------------------------------------------------
def fetch_lit(F, M, refresh):
    items = [
        ("https://www.usenix.org/system/files/usenixsecurity24-bocovich.pdf",
         "lit/bocovich2024_usenixsec24.pdf", LIC_USENIX,
         "Bocovich, Breault, Fifield, Serene, Wang. Snowflake, a censorship circumvention "
         "system using temporary WebRTC proxies. USENIX Security 2024."),
        ("https://arxiv.org/abs/2609.12242", "lit/chen2026_arxiv2609.12242_abs.html", LIC_ARXIV,
         "arXiv abstract page (metadata, license) for Chen, Sangha, Bocovich, Sundara Raman (2026)."),
        ("https://arxiv.org/pdf/2609.12242", "lit/chen2026_arxiv2609.12242.pdf", LIC_ARXIV,
         "Chen, Sangha, Bocovich, Sundara Raman. Evaluating Practical Enumeration and Blocking "
         "Attacks on the Snowflake Circumvention System. arXiv:2609.12242 (2026)."),
    ]
    for url, rel, lic, note in items:
        p, ts = F.save(url, Path(rel), refresh=refresh)
        prev = M.recs.get(rel, {})
        M.add(Path(rel), url, lic, False, "publication", note,
              retrieved=ts or prev.get("retrieved_utc"))
    print("  lit: done")


SECTIONS = ["collector", "tormetrics", "ioda", "gitlab", "github", "lit"]

BEGIN, END = "<!-- BEGIN FILE TABLE (generated by fetch_raw.py) -->", "<!-- END FILE TABLE -->"


def write_sources_table():
    """Re-render the per-file table of SOURCES.md from raw/manifest.json (no network)."""
    recs = sorted(json.loads(MANIFEST.read_text()), key=lambda r: r["path"])
    lines = [BEGIN, "",
             f"{len(recs)} files, {sum(r['size_bytes'] for r in recs) / 1e6:.1f} MB in total. "
             "'Redistribute' = whether the raw file may be shared with a public artifact "
             "(derived aggregates may be shared in all cases, with citation).", "",
             "| raw path | URL (or git repo @ commit : path) | retrieved (UTC) | sha256 | bytes | license | redistribute |",
             "|---|---|---|---|---:|---|---|"]
    for r in recs:
        url = r["url"].replace("|", "%7C")
        lic = r["license"].split(" (")[0] if len(r["license"]) > 60 else r["license"]
        lines.append(f"| `{r['path']}` | {url} | {r['retrieved_utc']} | `{r['sha256']}` | "
                     f"{r['size_bytes']} | {lic} | {'yes' if r['redistribute'] else 'no'} |")
    lines += ["", END]
    sp = HERE / "SOURCES.md"
    text = sp.read_text() if sp.exists() else ""
    if BEGIN in text and END in text:
        text = text[:text.index(BEGIN)] + "\n".join(lines) + text[text.index(END) + len(END):]
    else:
        text = text.rstrip() + "\n\n## Per-file provenance\n\n" + "\n".join(lines) + "\n"
    sp.write_text(text)
    print(f"SOURCES.md: table with {len(recs)} files")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", nargs="*", choices=SECTIONS, default=SECTIONS)
    ap.add_argument("--refresh", action="store_true", help="re-download files already present")
    ap.add_argument("--clone-dir", default=None,
                    help="where to put temporary git clones (default: a fresh temp dir)")
    ap.add_argument("--sources-only", action="store_true",
                    help="only re-render the SOURCES.md file table from raw/manifest.json")
    ap.add_argument("--paper-commits", action="store_true",
                    help="check out the timeline, rdsys-admin and snowflake clones at "
                         "PAPER_COMMITS (the paper's snapshot) instead of their current heads")
    a = ap.parse_args()
    if a.sources_only:
        write_sources_table()
        return 0
    RAW.mkdir(parents=True, exist_ok=True)
    F, M = Fetcher(), Manifest()
    clone_dir = Path(a.clone_dir) if a.clone_dir else Path(tempfile.mkdtemp(prefix="sf_clones_"))
    try:
        for s in a.only:
            print(f"[{s}]")
            fn = {"collector": fetch_collector, "tormetrics": fetch_tormetrics,
                  "ioda": fetch_ioda, "github": fetch_github, "lit": fetch_lit}.get(s)
            if s == "gitlab":
                fetch_gitlab(F, M, a.refresh, clone_dir,
                             PAPER_COMMITS if a.paper_commits else None)
            else:
                fn(F, M, a.refresh)
            M.save()
    finally:
        M.save()
        if not a.clone_dir:
            shutil.rmtree(clone_dir, ignore_errors=True)
    tot = sum(r["size_bytes"] for r in M.recs.values())
    print(f"manifest: {len(M.recs)} files, {tot/1e6:.1f} MB; {F.n} HTTP requests this run")
    write_sources_table()


if __name__ == "__main__":
    sys.exit(main())
