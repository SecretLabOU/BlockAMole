#!/usr/bin/env python3
"""fetch.py -- download every raw input of the burn_units analysis.

Usage:  python3 fetch.py <step> [...]
Steps (run in this order to rebuild raw/ from scratch):
        gfwatch | gfwlist | ooni | ooni_azurefd | ooni_raw | irblock | antifilter |
        zi | zi_history | qualitative | tranco | psl |
        verify  (re-hash raw/ against the manifest) |
        sources (regenerate the file table in SOURCES.md from raw/manifest.json)
Note: a re-run on another day gets newer upstream data (OONI, antifilter, gfwlist
HEAD, the Public Suffix List, the web pages); the manifest records what this copy
contains.

Nothing here measures a network target: every request goes to a public
dataset API or file host (GFWatch dashboard callback, OONI API, GitHub/GitLab,
Zenodo, antifilter.download). No blocked name is ever resolved or contacted.
Re-running a step skips files that exist in raw/ and have an entry in
raw/manifest.json.
"""

import json
import os
import subprocess
import tempfile
import sys
import time

import fetchlib as F

HERE = F.HERE
RAW = F.RAW
SCRATCH = os.environ.get(  # git clones and temporary files, outside the project
    "BURN_UNITS_SCRATCH", os.path.join(tempfile.gettempdir(), "blockamole_burn_units"))

# ---------------------------------------------------------------------------
# Platform suffixes (the cells of the matrix)
# ---------------------------------------------------------------------------
PLATFORMS = [
    "github.io", "pages.dev", "workers.dev", "vercel.app", "netlify.app",
    "herokuapp.com", "appspot.com", "web.app", "firebaseapp.com",
    "cloudfront.net", "azurewebsites.net", "azurefd.net", "run.app",
    "on.aws",            # lambda-url.<region>.on.aws (Lambda function URLs)
    "deno.dev", "fly.dev", "onrender.com", "trycloudflare.com", "r2.dev",
]

LIC_GFWATCH = ("GFWatch dashboard (gfwatch.org), Hoang et al. USENIX Security 2021; "
               "no explicit license on the dashboard; cite, do not redistribute bulk")


def gfwatch_regex(suffix):
    """Narrow, backslash-free regex: the suffix itself or any name under it."""
    esc = suffix.replace(".", "[.]")
    return f"(^|[.]){esc}$"


def step_gfwatch(only=None):
    url = "https://gfwatch.org/_dash-update-component"
    for suf in PLATFORMS:
        if only and suf not in only:
            continue
        rx = gfwatch_regex(suf)
        payload = {
            "output": "..censored-domains-looked-up.data...censored-domains-looked-up.page_current..",
            "outputs": [{"id": "censored-domains-looked-up", "property": "data"},
                        {"id": "censored-domains-looked-up", "property": "page_current"}],
            "inputs": [{"id": "submit-val", "property": "n_clicks", "value": 1}],
            "changedPropIds": ["submit-val.n_clicks"],
            "state": [{"id": "censored-domains-lookup", "property": "value", "value": rx}],
        }
        rel = f"gfwatch/lookup_{suf.replace('.', '_')}.json"
        t = time.time()
        try:
            ent = F.fetch(url, rel, LIC_GFWATCH, method="POST", json_payload=payload,
                          notes=f"GFWatch censored-domains lookup callback, regex {rx!r}; "
                                "dataset frozen at 2024-09-06",
                          timeout=300, max_bytes=200 * 1024 ** 2)
            print(suf, rx, ent["size_bytes"], f"{time.time()-t:.1f}s", flush=True)
        except Exception as e:  # noqa: BLE001
            print("FAILED", suf, rx, repr(e), flush=True)
        time.sleep(3)


LIC_OONI = "CC BY-NC-SA 4.0 (OONI data policy); derived data must carry the same license"

# OONI aggregation windows: CN by month (CN responses are ~20-23 MB/month: very
# many distinct test names), IR and RU as two 12-month windows (their
# web_connectivity test lists contain few platform tenants).
OONI_QUERIES = [
    ("CN", "2026-07-01", "2026-08-01"),
    ("CN", "2026-08-01", "2026-09-01"),
    ("CN", "2026-09-01", "2026-10-01"),
    ("IR", "2025-10-01", "2026-10-01"),
    ("RU", "2025-10-01", "2026-10-01"),
    # second 12-month window (overlaps the IRBlock window, Nov 2024..Jan 2025)
    ("IR", "2024-10-01", "2025-10-01"),
    ("RU", "2024-10-01", "2025-10-01"),
]


def step_ooni(extra=None):
    base = "https://api.ooni.io/api/v1/aggregation"
    qs = list(OONI_QUERIES)
    if extra:
        qs = [tuple(x.split(",")) for x in extra]
    for cc, since, until in qs:
        params = {"probe_cc": cc, "test_name": "web_connectivity",
                  "since": since, "until": until, "axis_x": "domain"}
        rel = f"ooni/agg_{cc}_{since}_{until}_domain.json"
        t = time.time()
        ent = F.fetch(base, rel, LIC_OONI, params=params, timeout=600,
                      notes="OONI aggregation API, web_connectivity, per-domain counts "
                            "(anomaly/confirmed/failure/ok are mutually exclusive)")
        print(cc, since, until, ent["size_bytes"], f"{time.time()-t:.1f}s", flush=True)
        time.sleep(5)


# Day-level follow-up for the CN azurefd.net anomaly change seen in the monthly
# aggregates (Jul-Aug 2026 mostly anomalous, Sep 2026 mostly not): 39 of the most
# measured Azure Front Door endpoints in the Jul-Sep 2026 CN aggregates and their
# zone apex (chosen from raw/ooni/agg_CN_* and frozen here for reproducibility).
OONI_AZUREFD_CN = (
    "rdipowerplatformfd-e5hhgqaahef7fbdr.a02.azurefd.net,p-entitc-frontdoor-endpoint-ecgqa0gseehhf0cr.a02.azurefd.net,"
    "iam-prod3-hfg4hab4addda2gf.a02.azurefd.net,p2blobstore-cdata-hya0gqaxdabaarax.a02.azurefd.net,"
    "fd-plzconn-cdn-op-msop-frontdoor-premium-fhb4bxgcffamgfbh.a02.azurefd.net,media-bkccefdngbaqgdb4.a02.azurefd.net,"
    "pictimecloudaf-pub-g3csanfebyefg3dm.a02.azurefd.net,u9kh456577-e4h5bxhbgfencxay.a02.azurefd.net,"
    "nd4p776834-ezhnhybmgce7ghga.a02.azurefd.net,brgfrontdoorendpoint-ftbgdxcqg6dqhnfb.a02.azurefd.net,"
    "b169868226-hvcucae9a5f8eagb.a02.azurefd.net,carrabbasprod-esdja5eaccfgfnc7.a02.azurefd.net,"
    "9a9f179586-bfffgmekb0buh4cm.a02.azurefd.net,fd-rapp-cdn-fzgxcpehc0ccdxeu.a02.azurefd.net,"
    "apt-prod-d9d6gsemdedkd3gd.a02.azurefd.net,pictime7eus1public-pub-hdf3hecqdpaqeuev.a02.azurefd.net,"
    "vg71233921-h0bndhepaagbfxdm.a02.azurefd.net,ss-p13n-a-route-cqashxc7gshebahk.a02.azurefd.net,"
    "webcomponents-dub9hvc3eachc4e6.a02.azurefd.net,p62a367490-gwbfhwe4bce2bjhy.a02.azurefd.net,"
    "ontariohealth-gbfed6fje7c8e4bj.a02.azurefd.net,mt-pg1-us-east-1-cdn-e2f3g4ftanc9agcx.a02.azurefd.net,"
    "images-h9gsgmdkgwcrd8dq.a02.azurefd.net,arthrexprod-dtd2bphrh2btedff.a02.azurefd.net,"
    "64v8402753-aaabcecgf7h3dmcd.a02.azurefd.net,tapn916417-b0e3hmg6hqd4b5ep.a02.azurefd.net,"
    "ecolab-intelligence-fd-p-bxgxhwd3agfqgtbj.a02.azurefd.net,"
    "rc-d2c-stg-secondary-cdn-frontservicediscovery-h8gxcshuhwcndrcz.a02.azurefd.net,"
    "v5ge487810-hze0dbdzeqg4fhbr.a02.azurefd.net,templafy-hive-frontdoor-cdn-f3dhb0azaufdckh0.a02.azurefd.net,"
    "hs-app-endpoint-gnfjfugjaxgta4c6.a02.azurefd.net,companyportal-bwhfc4dqb5cqguhr.a02.azurefd.net,"
    "storageprodcdnendpoint-fcazfkcfcpdjbjgg.a02.azurefd.net,endpoint-production-arcsdsccamezhgfe.a02.azurefd.net,"
    "tygraphfd-efe2cbaperfhesgt.a02.azurefd.net,vuw2182850-hcfkacagcfgqfzb4.a02.azurefd.net,"
    "aro-gsa4hgdbd8d0d9e3.a02.azurefd.net,36q2444993-dfhhb6eke7gyd3b3.a02.azurefd.net,"
    "storage-prod-f0hmanfcbecneyff.a02.azurefd.net,a02.azurefd.net")


def step_ooni_azurefd():
    base = "https://api.ooni.io/api/v1/aggregation"
    params = {"probe_cc": "CN", "test_name": "web_connectivity", "since": "2026-05-01",
              "until": "2026-10-01", "domain": OONI_AZUREFD_CN,
              "axis_x": "measurement_start_day", "axis_y": "domain"}
    ent = F.fetch(base, "ooni/agg_CN_azurefd40_2026-05-01_2026-10-01_day_domain.json", LIC_OONI,
                  params=params, timeout=600,
                  notes="OONI aggregation API, CN web_connectivity, 39 Azure Front Door endpoints "
                        "+ zone apex a02.azurefd.net, per day x domain")
    print("azurefd", ent["size_bytes"])
    time.sleep(3)
    params2 = dict(params, since="2025-07-01", until="2026-05-01")
    ent = F.fetch(base, "ooni/agg_CN_azurefd40_2025-07-01_2026-05-01_day_domain.json", LIC_OONI,
                  params=params2, timeout=600,
                  notes="Same 40 names, earlier window (onset search)")
    print("azurefd early", ent["size_bytes"])


OONI_RAW_UIDS = [
    # CN, Azure Front Door endpoint, flagged 'http-failure' (Aug 2026) and a
    # not-anomalous measurement of the same endpoint after 2026-09-05.
    "20260801153920.708278_CN_webconnectivity_9fd6b6e49bbb4a16",
    "20260814204453.616266_CN_webconnectivity_9b044dff6f7db0e0",
    "20260907101803.992549_CN_webconnectivity_4f4b68ede6f7b7fa",
    # CN, workers.dev: a blocked <worker>.<account> name (TLS reset after SNI, DNS
    # consistent) and a never-anomalous new name (NXDOMAIN at probe and control).
    "20260929202119.196158_CN_webconnectivity_3d44e33e0974bd1a",
    "20260928202308.876948_CN_webconnectivity_af000bcf9372d783",
]


def step_ooni_raw():
    base = "https://api.ooni.io/api/v1/measurements"
    F.fetch(base, "ooni/list_CN_azurefd_rdipowerplatformfd_2026-08-01_2026-09-15.json", LIC_OONI,
            params={"probe_cc": "CN", "test_name": "web_connectivity",
                    "domain": "rdipowerplatformfd-e5hhgqaahef7fbdr.a02.azurefd.net",
                    "since": "2026-08-01", "until": "2026-09-15", "limit": 30,
                    "order_by": "measurement_start_time", "order": "asc"},
            notes="OONI measurement list for one Azure Front Door endpoint in CN")
    for dom, rel in [("cva.engineer-c03.workers.dev", "ooni/list_CN_workersdev_blocked_2026-09.json"),
                     ("ancient-bird-0990.isvao15mcrxi.workers.dev", "ooni/list_CN_workersdev_clear_2026-09.json")]:
        F.fetch(base, rel, LIC_OONI,
                params={"probe_cc": "CN", "test_name": "web_connectivity", "domain": dom,
                        "since": "2026-09-01", "until": "2026-10-01", "limit": 5},
                notes="OONI measurement list (to pick raw measurements)")
    for uid in OONI_RAW_UIDS:
        ent = F.fetch("https://api.ooni.io/api/v1/raw_measurement", f"ooni/raw_{uid}.json",
                      LIC_OONI, params={"measurement_uid": uid},
                      notes="OONI raw measurement (published data; not a new measurement)")
        print(uid, ent["size_bytes"])


def step_gfwlist():
    """Full-history bare clone of gfwlist into scratch, bundled into raw/."""
    rel = "gfwlist/gfwlist.bundle"
    if rel in F.load_manifest()["files"] and os.path.exists(os.path.join(RAW, rel)):
        print("have", rel)
        return
    os.makedirs(SCRATCH, exist_ok=True)
    repo = os.path.join(SCRATCH, "gfwlist.git")
    t0 = F.now_utc()
    if not os.path.exists(repo):
        subprocess.run(["git", "clone", "--bare", "https://github.com/gfwlist/gfwlist", repo], check=True)
    os.makedirs(os.path.join(RAW, "gfwlist"), exist_ok=True)
    subprocess.run(["git", "-C", repo, "bundle", "create", os.path.join(RAW, rel), "--all"], check=True)
    head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True,
                          check=True).stdout.strip()
    F.record(rel, "https://github.com/gfwlist/gfwlist (git clone --bare; git bundle create --all)",
             "LGPL-2.1 (gfwlist/gfwlist COPYING.txt)",
             notes="Full history bundle of gfwlist/gfwlist (base64 AutoProxy list in gfwlist.txt). "
                   "Community proxy-routing list: weak proxy for GFW blocking.",
             retrieved=t0, extra={"git_head": head})
    print("gfwlist", head)


def step_irblock():
    rec = "https://zenodo.org/api/records/15572895"
    lic = "CC-BY-4.0 (Zenodo record 10.5281/zenodo.15572895)"
    F.fetch(rec, "irblock/zenodo_record_15572895.json", lic,
            notes="Zenodo record metadata (file list, md5 checksums)")
    for key in ["README.md", "blocked_domains.tar.gz"]:
        url = f"https://zenodo.org/api/records/15572895/files/{key}/content"
        ent = F.fetch(url, f"irblock/{key}", lic,
                      notes="IRBlock (Tai et al., USENIX Security 2025) artifact file")
        print(key, ent["size_bytes"], flush=True)
    # verify md5 against the Zenodo record
    import hashlib
    meta = json.load(open(os.path.join(RAW, "irblock/zenodo_record_15572895.json")))
    for f in meta["files"]:
        p = os.path.join(RAW, "irblock", f["key"])
        if os.path.exists(p):
            h = hashlib.md5(open(p, "rb").read()).hexdigest()
            print("md5", f["key"], "OK" if f["checksum"] == "md5:" + h else "MISMATCH")


LIC_AF = ("antifilter.download: no explicit license; lists are derived from the "
          "Roskomnadzor registry (Government Decree No. 1101 of 2012-10-26)")
LIC_AFC = ("community.antifilter.download: no explicit license; community-voted "
           "routing list, NOT registry data")


def _suffix_match(name):
    n = name.strip().lower().rstrip(".")
    n2 = n[2:] if n.startswith("*.") else n
    return bool(n2) and _platform_of(n2) is not None


def step_antifilter():
    """antifilter.download: site descriptions, the community list, and an EXTRACT
    of the registry-derived domains.lst (only lines under a platform suffix; the full
    list names illegal content and is streamed to scratch, hashed and deleted).
    urls.lst is not used."""
    items = [
        ("https://antifilter.download/", "antifilter/index.html", LIC_AF,
         "Site description of each list (Russian)."),
        ("https://community.antifilter.download/", "antifilter/community_index.html", LIC_AFC,
         "Community edition description."),
        ("https://community.antifilter.download/list/domains.lst",
         "antifilter/community_domains.lst", LIC_AFC, "Community-voted domain list."),
    ]
    for url, rel, lic, notes in items:
        ent = F.fetch(url, rel, lic, notes=notes)
        print(rel, ent["size_bytes"], ent.get("last_modified_header"), flush=True)
    rel = "antifilter/domains_platform_extract.lst"
    m = F.load_manifest()["files"]
    if rel in m and os.path.exists(os.path.join(RAW, rel)):
        print("have", rel)
        return
    url = "https://antifilter.download/list/domains.lst"
    # a full upstream file already in raw/, with a manifest entry, is filtered like a
    # download and then deleted
    old = os.path.join(RAW, "antifilter", "domains.lst")
    if os.path.exists(old) and "antifilter/domains.lst" in m:
        e = m["antifilter/domains.lst"]
        up = {"url": url, "sha256": e["sha256"], "size_bytes": e["size_bytes"],
              "retrieved_utc": e["retrieved_utc"], "last_modified_header": e.get("last_modified_header")}
        src = old
    else:
        src = os.path.join(SCRATCH, "antifilter_domains.lst")
        up = _stream_to(url, src)
    n = 0
    keep = []
    with open(src, encoding="utf-8", errors="replace") as f:
        for line in f:
            n += 1
            if _suffix_match(line):
                keep.append(line.strip().lower())
    with open(os.path.join(RAW, rel), "w") as f:
        f.write("\n".join(sorted(set(keep))) + "\n")
    F.record(rel, url, LIC_AF,
             notes=("EXTRACT of antifilter.download domains.lst (registry-blocked domains): only lines "
                    "whose name is a platform suffix or under one. Full list hashed, filtered, deleted "
                    "(it names illegal content)."),
             retrieved=up["retrieved_utc"],
             extra={"upstream_files": [up], "upstream_lines": n})
    import fcntl
    with open(os.path.join(RAW, ".manifest.lock"), "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        mm = F.load_manifest()
        mm["files"].pop("antifilter/domains.lst", None)
        mm["files"].pop("antifilter/urls.lst", None)
        F.save_manifest(mm)
        fcntl.flock(lk, fcntl.LOCK_UN)
    for p in [src, os.path.join(RAW, "antifilter", "urls.lst")]:
        if os.path.exists(p):
            os.remove(p)
    print("antifilter extract lines", n, "kept", len(set(keep)))


ZI_COMMIT = "9133e4327bbcf9adc1cba24360f50e50a6b4d11c"   # 'Updated: 2025-10-01 10:25:04 +0000'


def step_zi():
    """Latest z-i registry snapshot (commit ZI_COMMIT, 'Updated: 2025-10-01 10:25:04').

    The 20 split files dump-00..19.csv carry 6 fields (IP;domain;URL;org;decision;date);
    dump.csv.gz of the same commit has only IP;domain;URL. The splits are streamed to
    scratch, hashed, filtered to platform-suffix entries (zi_extract) and deleted; only
    the extract is kept in raw/ (the full dump contains URLs of illegal content)."""
    import hashlib
    import requests
    rel = f"zi/extract_2025-10-01_{ZI_COMMIT[:10]}.csv"
    m = F.load_manifest()["files"]
    if rel in m and os.path.exists(os.path.join(RAW, rel)):
        print("have", rel)
        return
    os.makedirs(SCRATCH, exist_ok=True)
    upstream, paths = [], []
    for i in range(20):
        fn = f"dump-{i:02d}.csv"
        url = f"https://raw.githubusercontent.com/zapret-info/z-i/{ZI_COMMIT}/{fn}"
        # a full upstream file already in raw/, with a manifest entry, is filtered like
        # a download and then deleted
        old = os.path.join(RAW, "zi", fn)
        if os.path.exists(old) and f"zi/{fn}" in m:
            e = m[f"zi/{fn}"]
            upstream.append({"url": url, "sha256": e["sha256"], "size_bytes": e["size_bytes"],
                             "retrieved_utc": e["retrieved_utc"]})
            paths.append(old)
            continue
        tmp = os.path.join(SCRATCH, f"zi_head_{fn}")
        F._pace(url)
        t0 = F.now_utc()
        r = requests.get(url, headers={"User-Agent": F.UA}, timeout=900, stream=True)
        r.raise_for_status()
        h = hashlib.sha256()
        size = 0
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                h.update(chunk)
                size += len(chunk)
                f.write(chunk)
        upstream.append({"url": url, "sha256": h.hexdigest(), "size_bytes": size,
                         "retrieved_utc": t0})
        paths.append(tmp)

    def lines():
        for p in paths:
            with open(p, "rb") as f:
                for line in f:
                    yield line
    os.makedirs(os.path.join(RAW, "zi"), exist_ok=True)
    header, n, nrows = zi_extract(lines(), os.path.join(RAW, rel))
    F.record(rel, f"https://github.com/zapret-info/z-i/tree/{ZI_COMMIT} (dump-00..19.csv)",
             "No license file in zapret-info/z-i; Roskomnadzor registry dump (public under "
             "Decree 1101). Extract only; do not redistribute.",
             notes=(f"EXTRACT of the 20 split files at commit {ZI_COMMIT} ('{header}'): only "
                    "entries whose domain or URL host is under a platform suffix (platform, "
                    "field, value, decision_date). Upstream files hashed, filtered, deleted."),
             retrieved=min(u["retrieved_utc"] for u in upstream),
             extra={"upstream_files": upstream, "upstream_lines": n, "git_commit": ZI_COMMIT,
                    "upstream_header": header})
    # delete the full files and drop any per-file manifest entries for them
    import fcntl
    with open(os.path.join(RAW, ".manifest.lock"), "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        mm = F.load_manifest()
        for i in range(20):
            mm["files"].pop(f"zi/dump-{i:02d}.csv", None)
        mm["files"].pop("zi/dump.csv.gz", None)
        F.save_manifest(mm)
        fcntl.flock(lk, fcntl.LOCK_UN)
    for p in paths + [os.path.join(RAW, "zi", "dump.csv.gz")]:
        if os.path.exists(p):
            os.remove(p)
    print("zi extract", header, "lines", n, "rows", nrows, flush=True)


# Historical registry snapshots (z-i commits picked from a treeless clone,
# `git clone --bare --filter=tree:0 https://github.com/zapret-info/z-i`, as the
# last commit before each date). For these snapshots only a platform-suffix
# EXTRACT is kept in raw/ (the full dump, ~95 MB of mostly unrelated and partly
# illegal-content URLs, is streamed to scratch, hashed, filtered and deleted).
ZI_HISTORY = [
    # (label, commit, files): 'dump.csv' = single 6-field file (until 2024-01);
    # 'splits' = dump-00..19.csv (6 fields incl. decision date; dump.csv of
    # 2024-05 has only 3 fields and from late 2024 on only dump.csv.gz exists).
    ("2022-01-01", "d291c7d7d7e406fbd8d08b1c9413a4ebb51fc42a", "dump.csv"),  # Updated: 2021-12-31 16:42
    ("2023-01-01", "9e1f59db3360f5caaaf8ebde0581e867b7fff4c8", "dump.csv"),  # Updated: 2022-12-31 16:46
    ("2024-01-01", "99aec91c810505e9b60129cc70c0f8c58411a11c", "dump.csv"),  # Updated: 2023-12-31 11:25
    ("2024-05-07", "94b080bebc7338dcbb6045ad6147656a1db974e3", "splits"),    # Updated: 2024-05-06 16:30
    ("2024-05-10", "b6429c7268a249f0cad7663b3ac6b2bd91b67e09", "splits"),    # Updated: 2024-05-09 14:15
    ("2025-01-01", "1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b", "splits"),    # Updated: 2024-12-31 12:05
]


def _platform_of(name):
    best = None
    for s in PLATFORMS:
        if name == s or name.endswith("." + s):
            if best is None or len(s) > len(best):
                best = s
    return best


def zi_extract(path_or_bytes_iter, out_csv):
    """Write rows (platform, field, value, decision_date) for every registry
    entry whose domain (or URL host) is under a platform suffix. Nothing else
    from the dump is kept. Returns (header_line, n_lines, n_rows)."""
    import csv as _csv
    import urllib.parse as _up
    rows = []
    header = None
    n = 0
    for raw in path_or_bytes_iter:
        if header is None:
            header = raw.decode("cp1251", "replace").strip()
            continue
        n += 1
        s = raw.decode("cp1251", "replace").rstrip("\r\n")
        parts = s.split(";")
        if len(parts) >= 6:          # IP;domain;URL;org;decision;date
            dom, url, date = parts[1], ";".join(parts[2:-3]), parts[-1]
        elif len(parts) >= 2:        # IP;domain;URL (no decision date)
            dom, url, date = parts[1], ";".join(parts[2:]), ""
        else:
            continue
        d = dom.strip().lower().rstrip(".")
        dd = d[2:] if d.startswith("*.") else d
        if dd and _platform_of(dd):
            rows.append((_platform_of(dd), "domain", d, date))
        for uu in (url.split(" | ") if url else []):
            try:
                host = (_up.urlsplit(uu.strip()).hostname or "").lower()
            except Exception:  # noqa: BLE001
                host = ""
            if host and _platform_of(host):
                rows.append((_platform_of(host), "url_host", host, date))
    with open(out_csv, "w", newline="") as f:
        w = _csv.writer(f)
        w.writerow(["platform", "field", "value", "decision_date"])
        w.writerows(sorted(set(rows)))
    return header, n, len(set(rows))


def _stream_to(url, path):
    import hashlib
    import requests
    F._pace(url)
    t0 = F.now_utc()
    r = requests.get(url, headers={"User-Agent": F.UA}, timeout=900, stream=True)
    r.raise_for_status()
    h = hashlib.sha256()
    size = 0
    with open(path, "wb") as f:
        for chunk in r.iter_content(1 << 20):
            h.update(chunk)
            size += len(chunk)
            f.write(chunk)
    return {"url": url, "sha256": h.hexdigest(), "size_bytes": size, "retrieved_utc": t0}


def step_zi_history():
    os.makedirs(SCRATCH, exist_ok=True)
    for label, commit, mode in ZI_HISTORY:
        rel = f"zi_history/extract_{label}_{commit[:10]}.csv"
        m = F.load_manifest()["files"]
        if rel in m and os.path.exists(os.path.join(RAW, rel)):
            print("have", rel)
            continue
        names = ["dump.csv"] if mode == "dump.csv" else [f"dump-{i:02d}.csv" for i in range(20)]
        upstream, paths = [], []
        for fn in names:
            url = f"https://raw.githubusercontent.com/zapret-info/z-i/{commit}/{fn}"
            tmp = os.path.join(SCRATCH, f"zi_{commit[:10]}_{fn}")
            upstream.append(_stream_to(url, tmp))
            paths.append(tmp)

        def lines():
            for p in paths:
                with open(p, "rb") as f:
                    for line in f:
                        yield line
        os.makedirs(os.path.join(RAW, "zi_history"), exist_ok=True)
        header, n, nrows = zi_extract(lines(), os.path.join(RAW, rel))
        for p in paths:
            os.remove(p)
        F.record(rel, f"https://github.com/zapret-info/z-i/tree/{commit} ({mode})",
                 "No license file in zapret-info/z-i; Roskomnadzor registry dump (public under "
                 "Decree 1101). Extract only; do not redistribute.",
                 notes=(f"EXTRACT of z-i {mode} at commit {commit} ('{header}'): only entries "
                        "whose domain or URL host is under a platform suffix (platform, field, "
                        "value, decision_date). Upstream files streamed to scratch, hashed, "
                        "filtered and deleted (they contain URLs of illegal content)."),
                 retrieved=min(u["retrieved_utc"] for u in upstream),
                 extra={"upstream_files": upstream, "upstream_lines": n, "git_commit": commit,
                        "upstream_header": header})
        print(label, commit[:10], header, "upstream bytes", sum(u["size_bytes"] for u in upstream),
              "lines", n, "extract rows", nrows, flush=True)
        time.sleep(3)


def step_qualitative():
    items = [
        ("https://gitlab.torproject.org/tpo/anti-censorship/censorship-analysis/-/issues/40064/discussions.json",
         "qualitative/tor_gitlab_40064_discussions.json",
         "Tor Project GitLab issue comments; no explicit license; cite, quote briefly"),
        ("https://gitlab.torproject.org/api/v4/projects/tpo%2Fanti-censorship%2Fcensorship-analysis/issues/40064",
         "qualitative/tor_gitlab_40064_issue.json",
         "Tor Project GitLab issue body; no explicit license; cite, quote briefly"),
        ("https://github.com/net4people/bbs/issues/133", "qualitative/net4people_bbs_133.html",
         "net4people/bbs forum post (GitHub); no explicit license; cite, quote briefly"),
        ("https://github.com/net4people/bbs/issues/417", "qualitative/net4people_bbs_417.html",
         "net4people/bbs forum post (GitHub); no explicit license; cite, quote briefly"),
    ]
    for url, rel, lic in items:
        hdrs = None
        notes = "Qualitative primary report (read, not measured)"
        if "gitlab.torproject.org" in url and url.endswith("discussions.json"):
            # The GitLab front end answers 403 'Access limited' until the client
            # carries the session cookie that its own 403 page sets via JavaScript.
            hdrs = {"Cookie": "_gitlab_session=1", "Accept": "application/json"}
            notes += "; sent the cookie _gitlab_session=1 that the site's 403 page sets"
        try:
            ent = F.fetch(url, rel, lic, notes=notes, headers=hdrs)
            print(rel, ent["size_bytes"], flush=True)
        except Exception as e:  # noqa: BLE001
            print("FAILED", url, repr(e), flush=True)
        time.sleep(2)


# Tranco daily top-1M lists. GFWatch and IRBlock both state that they test the
# Tranco list every day, so a bare platform suffix that appears in Tranco was in
# their daily test input (a suffix-wide rule covering the bare name would have
# shown up). Tranco aggregates to pay-level domains with the ICANN part of the
# PSL, so it contains no tenant names and cannot serve as a tenant denominator.
TRANCO_DATES = ["2024-09-01",   # end of the public GFWatch window (2024-09-06)
                "2025-01-01",   # inside the IRBlock window (2024-11 .. 2025-01-15)
                "2025-10-01",   # date of the last z-i registry dump
                "2026-10-01"]   # date of the antifilter.download snapshot
LIC_TRANCO = ("Tranco list (Le Pochat et al., NDSS 2019), tranco-list.eu; free for research, "
              "no explicit license; cite")


def step_tranco():
    for d in TRANCO_DATES:
        meta_rel = f"tranco/tranco_{d}_meta.json"
        ent = F.fetch(f"https://tranco-list.eu/api/lists/date/{d}", meta_rel, LIC_TRANCO,
                      notes=f"Tranco list id for {d}")
        meta = json.load(open(os.path.join(RAW, meta_rel)))
        lid = meta["list_id"]
        ent = F.fetch(f"https://tranco-list.eu/download/{lid}/1000000",
                      f"tranco/tranco_{d}_{lid}_top1m.csv", LIC_TRANCO,
                      notes=f"Tranco daily top-1M, list {lid} (config: {json.dumps(meta.get('configuration'))})")
        print(d, lid, ent["size_bytes"], flush=True)


def step_psl():
    # Pinned via the GitHub raw URL of the current main; commit recorded from the
    # response is not available, so the sha256 in the manifest identifies the copy.
    ent = F.fetch("https://raw.githubusercontent.com/publicsuffix/list/main/public_suffix_list.dat",
                  "psl/public_suffix_list.dat", "MPL-2.0 (Public Suffix List)",
                  notes="Public Suffix List; used to mark which platform suffixes are PSL "
                        "private-section entries (each tenant = its own registrable domain)")
    print("psl", ent["size_bytes"])


def step_verify():
    m = F.load_manifest()["files"]
    bad = 0
    for root, _dirs, files in os.walk(RAW):
        for fn in files:
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, RAW)
            if rel in ("manifest.json", ".manifest.lock", "README.md") or rel.endswith(".part"):
                continue
            if rel not in m:
                print("NOT IN MANIFEST:", rel)
                bad += 1
    for rel, ent in sorted(m.items()):
        p = os.path.join(RAW, rel)
        if not os.path.exists(p):
            print("MISSING FILE:", rel)
            bad += 1
            continue
        if F.sha256_file(p) != ent["sha256"]:
            print("SHA MISMATCH:", rel)
            bad += 1
    print("verify:", len(m), "manifest entries;", bad, "problems")


def step_sources():
    """Regenerate the per-file table at the end of SOURCES.md from the manifest."""
    m = F.load_manifest()["files"]
    lines = ["| raw file | URL | retrieved (UTC) | size (bytes) | sha256 | license |",
             "|---|---|---|---:|---|---|"]
    for rel, e in sorted(m.items()):
        url = e["url"].replace("|", "%7C")
        lines.append(f"| `{rel}` | {url} | {e['retrieved_utc']} | {e['size_bytes']} | "
                     f"`{e['sha256']}` | {e['license']} |")
    # upstream files that were streamed, hashed, filtered and deleted (extracts)
    up = ["", "Upstream files behind the extracts (streamed to scratch, hashed, filtered, deleted):", "",
          "| extract in raw/ | upstream URL | retrieved (UTC) | size (bytes) | sha256 |",
          "|---|---|---|---:|---|"]
    for rel, e in sorted(m.items()):
        for u in e.get("upstream_files", []) or []:
            up.append(f"| `{rel}` | {u['url']} | {u['retrieved_utc']} | {u['size_bytes']} | "
                      f"`{u['sha256']}` |")
        if "upstream_sha256" in e:
            up.append(f"| `{rel}` | {e['url']} | {e['retrieved_utc']} | {e['upstream_size_bytes']} | "
                      f"`{e['upstream_sha256']}` |")
    table = "\n".join(lines + up) + "\n"
    path = os.path.join(HERE, "SOURCES.md")
    head = open(path).read() if os.path.exists(path) else ""
    marker = "<!-- BEGIN FILE TABLE (generated by fetch.py sources) -->"
    if marker in head:
        head = head.split(marker)[0]
    with open(path, "w") as f:
        f.write(head + marker + "\n\n" + table)
    print("wrote", path)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    step = sys.argv[1]
    args = sys.argv[2:]
    if step == "gfwatch":
        step_gfwatch(only=args or None)
    elif step == "gfwlist":
        step_gfwlist()
    elif step == "ooni":
        step_ooni(extra=args or None)
    elif step == "irblock":
        step_irblock()
    elif step == "ooni_azurefd":
        step_ooni_azurefd()
    elif step == "ooni_raw":
        step_ooni_raw()
    elif step == "antifilter":
        step_antifilter()
    elif step == "zi":
        step_zi()
    elif step == "zi_history":
        step_zi_history()
    elif step == "qualitative":
        step_qualitative()
    elif step == "tranco":
        step_tranco()
    elif step == "psl":
        step_psl()
    elif step == "verify":
        step_verify()
    elif step == "sources":
        step_sources()
    else:
        raise SystemExit(f"unknown step {step}")


if __name__ == "__main__":
    main()
