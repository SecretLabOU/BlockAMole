#!/usr/bin/env python3
"""analysis.py -- regenerate derived/ from raw/ for the burn-units analysis.

Question: at what GRANULARITY do China, Iran and Russia block names on shared
hosting platforms (github.io, pages.dev, workers.dev, ...)?  For each
censor x platform cell we classify:

    suffix   suffix-wide rule (every tenant name under the platform suffix)
    mixed    tenant (per-name) blocks first, then escalation to a suffix rule
    tenant   per-name (tenant) blocking only
      none     no blocking observed (Russia: no registry entry; complete list)
    insuff   insufficient coverage (no suffix rule seen, too few tenants tested)

Inputs (all under raw/, provenance in raw/manifest.json and SOURCES.md):
  gfwatch/      GFWatch censored-domain lookups (China, DNS, 2020-03-20..2024-09-06)
  gfwlist/      gfwlist git bundle (community proxy list; weak, lagged proxy for China)
  ooni/         OONI aggregation API (web_connectivity, per-domain counts), a day-level
                follow-up for Azure Front Door in CN, and 5 raw measurements
  irblock/      IRBlock artifact (Iran, DNS+HTTP blocked names, Nov 2024..2025-01-15)
  zi/, zi_history/  Roskomnadzor registry dumps (z-i mirror) 2021-12-31..2025-10-01,
                kept as platform-suffix EXTRACTS only (the full dumps list illegal content)
  antifilter/   registry-derived domain list of 2026-10-02 (extract) + community list
  tranco/       Tranco top-1M lists: the bare platform suffixes are in the daily test
                input of GFWatch and IRBlock (tenant names are not: Tranco aggregates
                to pay-level domains with the ICANN part of the PSL)
  psl/          Public Suffix List (tenant = registrable domain under the platform)
  qualitative/  primary reports (Tor GitLab #40064, net4people #133 and #417)

Run:  python3 analysis.py            (all steps; about 2-3 minutes)
No network access is made by this script. It needs the git command (gfwlist history)
and, for its last step, the timeline figure, ../../simulations/code/figstyle.py.
"""

import datetime as dt
import glob
import gzip
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from collections import defaultdict

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
DER = os.path.join(HERE, "derived")
os.makedirs(DER, exist_ok=True)

# (suffix used for matching, display label)
PLATFORMS = [
    ("github.io", "github.io"),
    ("pages.dev", "pages.dev"),
    ("workers.dev", "workers.dev"),
    ("vercel.app", "vercel.app"),
    ("netlify.app", "netlify.app"),
    ("herokuapp.com", "herokuapp.com"),
    ("appspot.com", "appspot.com"),
    ("web.app", "web.app"),
    ("firebaseapp.com", "firebaseapp.com"),
    ("cloudfront.net", "cloudfront.net"),
    ("azurewebsites.net", "azurewebsites.net"),
    ("azurefd.net", "azurefd.net"),
    ("run.app", "run.app"),
    ("on.aws", "lambda-url.<region>.on.aws"),
    ("deno.dev", "deno.dev"),
    ("fly.dev", "fly.dev"),
    ("onrender.com", "onrender.com"),
    ("trycloudflare.com", "trycloudflare.com"),
    ("r2.dev", "r2.dev"),
]
SUFFIXES = [p for p, _ in PLATFORMS]
LABEL = dict(PLATFORMS)
CENSORS = ["CN", "IR", "RU"]
CENSOR_NAME = {"CN": "China", "IR": "Iran", "RU": "Russia"}

# Minimum evidence used throughout (recorded in derived/run_meta.json under "thresholds"):
OONI_MIN_MEAS = 3        # a name needs >= 3 non-failed measurements to count as tested
OONI_BLOCK_SHARE = 0.5   # ... and >= 50% anomalous/confirmed to count as blocked
OONI_CLEAR_SHARE = 0.1   # ... and <= 10% anomalous to count as not anomalous
MIN_TESTED = 5           # fewer tested tenant names than this => insufficient coverage


def log(*a):
    print(*a, flush=True)


def under(name, suf):
    return name == suf or name.endswith("." + suf)


def platform_of(name):
    """Most specific platform suffix that `name` falls under (or None)."""
    best = None
    for s in SUFFIXES:
        if under(name, s) and (best is None or len(s) > len(best)):
            best = s
    return best


# ---------------------------------------------------------------------------
# Public Suffix List: tenant = registrable domain under the platform suffix
# ---------------------------------------------------------------------------
class PSL:
    def __init__(self, path):
        self.normal, self.wild, self.exc = set(), set(), set()
        self.private = set()
        self.ok = os.path.exists(path)
        if not self.ok:
            return
        section = None
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if "===BEGIN PRIVATE DOMAINS===" in line:
                section = "private"
            if not line or line.startswith("//"):
                continue
            rule = line.split()[0].lower()
            if rule.startswith("!"):
                self.exc.add(rule[1:])
            elif rule.startswith("*."):
                self.wild.add(rule[2:])
                if section == "private":
                    self.private.add(rule)
            else:
                self.normal.add(rule)
                if section == "private":
                    self.private.add(rule)

    def public_suffix(self, name):
        labels = name.lower().strip(".").split(".")
        best = 1  # implicit '*' rule
        for i in range(len(labels)):
            cand = ".".join(labels[i:])
            n = len(labels) - i
            if cand in self.exc:
                return ".".join(labels[i + 1:])
            if cand in self.normal and n > best:
                best = n
            if i + 1 < len(labels) and ".".join(labels[i + 1:]) in self.wild and n > best:
                best = n
        return ".".join(labels[-best:])

    def registrable(self, name):
        ps = self.public_suffix(name)
        labels = name.lower().strip(".").split(".")
        k = len(ps.split("."))
        if len(labels) <= k:
            return None
        return ".".join(labels[-(k + 1):])

    def entries_under(self, suf):
        """PSL private-section rules equal to or under `suf`."""
        return sorted(r for r in self.private if r.lstrip("*.") == suf or r.endswith("." + suf))


PSLX = PSL(os.path.join(RAW, "psl", "public_suffix_list.dat"))


def tenant_of(name, suf):
    """The tenant unit of a name under platform suffix `suf`.

    Uses the PSL registrable domain when the name's public suffix is the platform
    suffix or lies under it (e.g. foo.github.io, x.lambda-url.us-east-1.on.aws);
    otherwise the first label left of the suffix. Returns None for the bare suffix."""
    name = name.lower().strip(".")
    if name == suf:
        return None
    labels = name[: -(len(suf) + 1)].split(".")
    # Azure Front Door endpoints: <endpoint>-<hash>.<zone>.azurefd.net (zone z01, a02, ...)
    if suf == "azurefd.net" and len(labels) >= 2 and re.fullmatch(r"[a-z]\d\d", labels[-1]):
        return labels[-2] + "." + labels[-1] + "." + suf
    # Azure App Service Kudu: <app>.scm.azurewebsites.net
    if suf == "azurewebsites.net" and len(labels) >= 2 and labels[-1] == "scm":
        return labels[-2] + "." + suf
    if PSLX.ok:
        ps = PSLX.public_suffix(name)
        if under(ps, suf):
            r = PSLX.registrable(name)
            if r:
                return r
    rest = name[: -(len(suf) + 1)]
    return rest.split(".")[-1] + "." + suf


def label_depth(name, suf):
    """Number of labels left of the platform suffix."""
    if name == suf:
        return 0
    return len(name[: -(len(suf) + 1)].split("."))


# ---------------------------------------------------------------------------
# China: GFWatch (DNS), 2020-03-20 .. 2024-09-06
# ---------------------------------------------------------------------------
GFW_START = pd.Timestamp("2020-03-20")
GFW_END = pd.Timestamp("2024-09-06")


def gfw_rule_level(rule, suf):
    """'suffix' if the inferred GFWatch rule covers every name under the suffix,
    'tenant' if it is anchored on something finer, else 'other' (artifacts)."""
    r = (rule or "").strip().lower()
    core = r.lstrip("*").lstrip(".").rstrip("*")
    if core == suf:
        return "suffix"
    if core.endswith("." + suf) or (core.endswith(suf) and len(core) > len(suf)):
        return "tenant"
    return "other"


def load_gfwatch():
    frames = []
    for suf in SUFFIXES:
        path = os.path.join(RAW, "gfwatch", f"lookup_{suf.replace('.', '_')}.json")
        if not os.path.exists(path):
            log("  [gfwatch] missing", path)
            continue
        d = json.load(open(path))
        rows = d["response"]["censored-domains-looked-up"]["data"]
        rows = [r for r in rows if "not found" not in str(r.get("censored_domain", ""))]
        df = pd.DataFrame(rows, columns=["Tranco_rank", "censored_domain", "base_censored_domain",
                                         "blocking_rules", "first_checked", "last_checked",
                                         "base_domain_category"])
        df["platform"] = suf
        frames.append(df)
    g = pd.concat(frames, ignore_index=True)
    g["censored_domain"] = g.censored_domain.str.lower()
    # the regex (^|[.])suffix$ cannot match a longer platform; keep rows under suf
    g = g[[under(n, s) for n, s in zip(g.censored_domain, g.platform)]].copy()
    g["fc"] = pd.to_datetime(g.first_checked, format="%Y/%m/%d")
    g["lc"] = pd.to_datetime(g.last_checked, format="%Y/%m/%d")
    g["level"] = [gfw_rule_level(r, s) for r, s in zip(g.blocking_rules, g.platform)]
    g["tenant"] = [tenant_of(n, s) for n, s in zip(g.censored_domain, g.platform)]
    g["in_tranco"] = g.Tranco_rank.astype(float) < 88888888
    return g


def gfwatch_summary(g):
    out = []
    for suf in SUFFIXES:
        x = g[g.platform == suf]
        rec = {"platform": suf, "gfw_rows": len(x),
               "gfw_tenants": int(x.tenant.dropna().nunique()),
               "gfw_rules": int(x.blocking_rules.nunique()),
               "gfw_suffix_rule": False, "gfw_suffix_onset": None,
               "gfw_suffix_onset_source": "",
               "gfw_tenant_first": None, "gfw_tenants_pre": 0, "gfw_tenant_rule_rows": 0,
               "gfw_rows_in_tranco": int(x.in_tranco.sum()),
               "gfw_first_any": x.fc.min().date().isoformat() if len(x) else None,
               "gfw_lc_max": x.lc.max().date().isoformat() if len(x) else None,
               "gfw_class": "none"}
        if len(x) == 0:
            out.append(rec)
            continue
        sx = x[x.level == "suffix"]
        apex = x[(x.censored_domain == suf) & (x.level == "suffix")]
        onset = None
        if len(apex):
            onset = apex.fc.min()
            rec["gfw_suffix_onset_source"] = "first_checked of the bare suffix (zone-file SLD, tested daily)"
        elif len(sx):
            onset = sx.fc.min()
            rec["gfw_suffix_onset_source"] = "earliest first_checked among suffix-rule rows (upper bound)"
        trows = x[x.level == "tenant"]
        rec["gfw_tenant_rule_rows"] = len(trows)
        if onset is not None:
            rec["gfw_suffix_rule"] = True
            rec["gfw_suffix_onset"] = onset.date().isoformat()
            pre = x[(x.fc < onset) & (x.censored_domain != suf)]
            pre_or_t = pd.concat([pre, trows[trows.fc < onset]]).drop_duplicates("censored_domain")
        else:
            pre_or_t = trows
        if len(pre_or_t):
            rec["gfw_tenant_first"] = pre_or_t.fc.min().date().isoformat()
            rec["gfw_tenants_pre"] = int(pre_or_t.tenant.dropna().nunique())
        rec["gfw_pre_rows_tenant_rule"] = int(((x.fc < onset) & (x.level == "tenant")).sum()) if onset is not None else int((x.level == "tenant").sum())
        if onset is not None and len(pre_or_t):
            rec["gfw_class"] = "mixed"
        elif onset is not None:
            rec["gfw_class"] = "suffix"
        elif len(x):
            rec["gfw_class"] = "tenant"
        # onset left-censored at the start of GFWatch?
        rec["gfw_onset_left_censored"] = bool(onset is not None and onset <= GFW_START)
        # tenants still seen blocked in the last 30 days of the public window
        rec["gfw_tenants_blocked_last30d"] = int(
            x[(x.lc >= GFW_END - pd.Timedelta(days=30)) & (x.censored_domain != suf)].tenant.nunique())
        out.append(rec)
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# China: gfwlist history (community proxy list; weak, lagged proxy)
# ---------------------------------------------------------------------------
def _autoproxy_match(line, url):
    """Minimal AutoProxy/ABP matcher for a single (non-exception) rule line."""
    if line.startswith("/") and line.endswith("/") and len(line) > 2:
        try:
            return re.search(line[1:-1], url) is not None
        except re.error:
            return False
    def wild(p):
        return ".*".join(re.escape(t) for t in p.split("*"))
    if line.startswith("||"):
        pat = line[2:]
        host = url.split("://", 1)[1]
        # domain anchor: match at host start or after a dot
        return re.match(r"^(?:[^/]*\.)?" + wild(pat), host) is not None
    if line.startswith("|"):
        return re.match(wild(line[1:]), url) is not None
    return re.search(wild(line), url) is not None


def gfwlist_history():
    bundle = os.path.join(RAW, "gfwlist", "gfwlist.bundle")
    rx = re.compile("|".join(re.escape(s) for s in SUFFIXES))
    events = []
    with tempfile.TemporaryDirectory(dir=HERE, prefix=".tmp_gfwlist_") as td:
        repo = os.path.join(td, "g.git")
        subprocess.run(["git", "clone", "-q", "--bare", bundle, repo], check=True)
        out = subprocess.run(["git", "-C", repo, "log", "--reverse", "--format=C %H %ct",
                              "--raw", "--no-abbrev", "--", "gfwlist.txt"],
                             capture_output=True, text=True, check=True).stdout
        commits, cur = [], None
        for line in out.splitlines():
            if line.startswith("C "):
                _, h, ct = line.split()
                cur = [h, int(ct), None]
                commits.append(cur)
            elif line.startswith(":") and cur is not None:
                cur[2] = line.split()[3]
        p = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        prev = set()
        states = []   # (time, commit, frozenset(lines))
        for h, ct, blob in commits:
            if blob is None or set(blob) == {"0"}:
                continue
            p.stdin.write((blob + "\n").encode())
            p.stdin.flush()
            hdr = p.stdout.readline().split()
            size = int(hdr[2])
            data = p.stdout.read(size)
            p.stdout.read(1)
            raw = re.sub(rb"\s", b"", data)
            try:
                txt = __import__("base64").b64decode(raw).decode("utf-8", "replace")
            except Exception:  # noqa: BLE001
                txt = data.decode("utf-8", "replace")
            lines = frozenset(l.strip() for l in txt.splitlines()
                              if l.strip() and not l.startswith("!") and not l.startswith("[")
                              and rx.search(l))
            if lines != prev:
                states.append((ct, h, lines))
                for l in sorted(lines - prev):
                    events.append((ct, h, "add", l))
                for l in sorted(prev - lines):
                    events.append((ct, h, "del", l))
                prev = lines
        p.stdin.close()
        p.wait()
        head_time = commits[-1][1]
        head_hash = commits[-1][0]
    # per platform: does the list (excluding @@ exceptions) cover a random tenant?
    rows = []
    for suf in SUFFIXES:
        probe = [f"http://zqxjtenant7.{suf}/", f"https://zqxjtenant7.{suf}/"]
        covered_runs, tenant_first, suffix_first = [], None, None
        was = False
        start = None
        n_tenant_lines_head = 0
        max_tenant_lines = 0
        for ct, h, lines in states:
            rel = [l for l in lines if suf in l]
            pos = [l for l in rel if not l.startswith("@@")]
            cov = any(_autoproxy_match(l, u) for l in pos for u in probe)
            tl = [l for l in pos if not any(_autoproxy_match(l, u) for u in probe)]
            if tl and tenant_first is None:
                tenant_first = ct
            max_tenant_lines = max(max_tenant_lines, len(tl))
            if cov and not was:
                start = ct
                if suffix_first is None:
                    suffix_first = ct
            if not cov and was:
                covered_runs.append((start, ct))
            was = cov
        if was:
            covered_runs.append((start, None))
        # state at HEAD
        last_lines = states[-1][2] if states else frozenset()
        pos_head = [l for l in last_lines if suf in l and not l.startswith("@@")]
        cov_head = any(_autoproxy_match(l, u) for l in pos_head for u in
                       [f"http://zqxjtenant7.{suf}/", f"https://zqxjtenant7.{suf}/"])
        n_tenant_lines_head = len([l for l in pos_head if not any(
            _autoproxy_match(l, u) for u in [f"http://zqxjtenant7.{suf}/", f"https://zqxjtenant7.{suf}/"])])
        # stable onset: start of the run that is still open at HEAD (or longest run)
        stable = None
        if cov_head and covered_runs:
            stable = covered_runs[-1][0]
        f = lambda t: dt.datetime.fromtimestamp(t, dt.timezone.utc).date().isoformat() if t else None
        rows.append({"platform": suf,
                     "gfwlist_suffix_rule_first": f(suffix_first),
                     "gfwlist_suffix_rule_current_since": f(stable),
                     "gfwlist_suffix_rule_at_head": cov_head,
                     "gfwlist_suffix_rule_runs": len(covered_runs),
                     "gfwlist_tenant_rule_first": f(tenant_first),
                     "gfwlist_tenant_lines_at_head": n_tenant_lines_head,
                     "gfwlist_tenant_lines_max": max_tenant_lines})
    ev = pd.DataFrame(events, columns=["time", "commit", "action", "line"])
    ev["date"] = [dt.datetime.fromtimestamp(t, dt.timezone.utc).date().isoformat() for t in ev.time]
    meta = {"head": head_hash,
            "head_date": dt.datetime.fromtimestamp(head_time, dt.timezone.utc).isoformat(),
            "versions_with_platform_changes": len(states)}
    return pd.DataFrame(rows), ev, meta


# ---------------------------------------------------------------------------
# OONI web_connectivity aggregates (CN Jul-Sep 2026 by month, IR and RU Oct 2024-Sep 2026
# in two 12-month windows)
# ---------------------------------------------------------------------------
_SUFFIX_RX = re.compile(r"(?:^|\.)(?:" + "|".join(re.escape(s) for s in SUFFIXES) + r")$")


def load_ooni():
    rows = []
    for f in sorted(glob.glob(os.path.join(RAW, "ooni", "agg_*_domain.json"))):
        mm = re.fullmatch(r"agg_([A-Z]{2})_(\d{4}-\d\d-\d\d)_(\d{4}-\d\d-\d\d)_domain\.json",
                          os.path.basename(f))
        if not mm:          # e.g. the day-level azurefd follow-up file
            continue
        cc, since, until = mm.groups()
        d = json.load(open(f))
        for r in d["result"]:
            dom = (r.get("domain") or "").lower()
            if not _SUFFIX_RX.search(dom):
                continue
            p = platform_of(dom)
            rows.append({"cc": cc, "since": since, "until": until.replace(".json", ""),
                         "platform": p, "domain": dom,
                         "measurement_count": r["measurement_count"],
                         "anomaly_count": r["anomaly_count"],
                         "confirmed_count": r["confirmed_count"],
                         "failure_count": r["failure_count"], "ok_count": r["ok_count"]})
    return pd.DataFrame(rows)


def ooni_domain_table(o):
    """Per (cc, domain): counts summed over that country's windows + class."""
    cnt = ["measurement_count", "anomaly_count", "confirmed_count", "failure_count", "ok_count"]
    a = o.groupby(["cc", "platform", "domain"], as_index=False)[cnt].sum()
    a["valid"] = a.measurement_count - a.failure_count
    a["anom"] = a.anomaly_count + a.confirmed_count
    a["share"] = a.anom / a.valid.where(a.valid > 0)
    a["depth"] = [label_depth(d, p) for d, p in zip(a.domain, a.platform)]
    # Eligible tenant names: not the bare suffix; enough non-failed measurements;
    # for workers.dev only <worker>.<account>.workers.dev (depth >= 2): single-label
    # <account>.workers.dev names have no DNS records and report 'ok' whatever the
    # censor does (OONI marks a site that does not exist as not anomalous).
    a["eligible"] = ((a.depth >= 1) & (a.valid >= OONI_MIN_MEAS) &
                     ~((a.platform == "workers.dev") & (a.depth < 2)))
    a["cls"] = np.where(~a.eligible, "",
                np.where(a.share >= OONI_BLOCK_SHARE, "blocked",
                np.where(a.share <= OONI_CLEAR_SHARE, "clear", "mixed")))
    return a


def ooni_summary(a, o):
    out = []
    windows = o.groupby("cc").agg(since=("since", "min"), until=("until", "max"))
    for cc in CENSORS:
        for suf in SUFFIXES:
            x = a[(a.cc == cc) & (a.platform == suf)]
            e = x[x.eligible]
            bare = x[x.depth == 0]
            rec = {"censor": cc, "platform": suf,
                   "ooni_window": (f"{windows.loc[cc,'since']}..{windows.loc[cc,'until']}"
                                   if cc in windows.index else ""),
                   "ooni_names_any": int((x.depth >= 1).sum()),
                   "ooni_tested": len(e),
                   "ooni_blocked": int((e.cls == "blocked").sum()),
                   "ooni_clear": int((e.cls == "clear").sum()),
                   "ooni_mixed": int((e.cls == "mixed").sum()),
                   "ooni_tenants_tested": int(pd.Series([tenant_of(d, suf) for d in e.domain]).nunique()) if len(e) else 0,
                   "ooni_bare_meas": int(bare.valid.sum()) if len(bare) else 0,
                   "ooni_bare_share": float(bare.anom.sum() / bare.valid.sum()) if len(bare) and bare.valid.sum() > 0 else np.nan}
            rec["ooni_blocked_frac"] = rec["ooni_blocked"] / rec["ooni_tested"] if rec["ooni_tested"] else np.nan
            out.append(rec)
    return pd.DataFrame(out)


def ooni_file_stats():
    """Distinct domains and measurements per OONI aggregation file (all domains)."""
    out = {}
    for f in sorted(glob.glob(os.path.join(RAW, "ooni", "agg_*_domain.json"))):
        if not re.fullmatch(r"agg_[A-Z]{2}_\d{4}-\d\d-\d\d_\d{4}-\d\d-\d\d_domain\.json", os.path.basename(f)):
            continue
        d = json.load(open(f))
        out[os.path.basename(f)] = {"distinct_domains": len(d["result"]),
                                    "measurements": int(sum(r["measurement_count"] for r in d["result"]))}
    return out


def ooni_cn_workers_stability(o):
    """workers.dev <worker>.<account> names in CN: per-month class, and how many
    names measured in all three months changed from blocked to clear."""
    w = o[(o.cc == "CN") & (o.platform == "workers.dev")].copy()
    w["depth"] = [label_depth(d, "workers.dev") for d in w.domain]
    w = w[w.depth >= 2]
    w["valid"] = w.measurement_count - w.failure_count
    w["share"] = (w.anomaly_count + w.confirmed_count) / w.valid.where(w.valid > 0)
    piv = w.pivot_table(index="domain", columns="since", values="share")
    months = sorted(piv.columns)
    allm = piv.dropna()
    last = months[-1]
    sep_clear = piv[piv[last] <= OONI_CLEAR_SHARE]
    first_month = piv.apply(lambda r: r.first_valid_index(), axis=1)
    return {"months": months,
            "names_all_months": len(allm),
            "blocked_first_to_clear_last": int(((allm[months[0]] >= OONI_BLOCK_SHARE) & (allm[last] <= OONI_CLEAR_SHARE)).sum()),
            "clear_in_last_month_any_meas": len(sep_clear),
            "clear_in_last_month_first_seen_in_last_two_months": int(first_month[sep_clear.index].isin(months[-2:]).sum())}


def ooni_monthly_cn(o):
    """CN per-month eligible/blocked counts (to show stability within Jul-Sep 2026)."""
    out = []
    for (since, suf), x in o[o.cc == "CN"].groupby(["since", "platform"]):
        a = ooni_domain_table(x)
        e = a[a.eligible]
        out.append({"month": since[:7], "platform": suf, "tested": len(e),
                    "blocked": int((e.cls == "blocked").sum()),
                    "clear": int((e.cls == "clear").sum())})
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# Iran: IRBlock artifact (DNS + HTTP censored names, >= 3 days, Nov 2024..2025-01-15)
# ---------------------------------------------------------------------------
IRB_FILES = {"dns_fqdn": "blocked_domains/dns_censored_fqdn.txt.gz",
             "http_fqdn": "blocked_domains/http_censored_fqdn.txt.gz",
             "dns_apex": "blocked_domains/dns_censored_apex_domains.txt.gz",
             "http_apex": "blocked_domains/http_censored_apex_domains.txt.gz",
             "categories": "blocked_domains/apex_domain_categories.csv.gz"}


def load_irblock():
    tf = tarfile.open(os.path.join(RAW, "irblock", "blocked_domains.tar.gz"))
    sets, totals = {}, {}
    for key, member in IRB_FILES.items():
        s = set()
        n = 0
        fh = io.TextIOWrapper(gzip.GzipFile(fileobj=tf.extractfile(member)),
                              encoding="utf-8", errors="replace")
        for i, line in enumerate(fh):
            if key == "categories" and i == 0:
                continue
            n += 1
            name = line.strip().split(",")[0].lower().strip(".")
            if _SUFFIX_RX.search(name):
                s.add(name)
        sets[key] = s
        totals[key] = n
    return sets, totals


def irblock_summary(sets):
    out = []
    for suf in SUFFIXES:
        rec = {"platform": suf}
        for key in ["dns_fqdn", "http_fqdn"]:
            names = {n for n in sets[key] if platform_of(n) == suf}
            ten = {n for n in names if n != suf}
            rec[f"irb_{key}_bare"] = suf in names
            rec[f"irb_{key}_names"] = len(ten)
            rec[f"irb_{key}_tenants"] = len({tenant_of(n, suf) for n in ten})
        rec["irb_bare_in_categorised_apexes"] = suf in sets["categories"]
        anyn = {n for k in ["dns_fqdn", "http_fqdn"] for n in sets[k] if platform_of(n) == suf and n != suf}
        rec["irb_any_names"] = len(anyn)
        # names that look machine-generated (nobody lists these one by one):
        # Pages preview deployments <8 hex>.<project>.pages.dev, quick tunnels
        # <word>-<word>-<word>-<word>.trycloudflare.com, default Heroku app names
        # <adjective>-<noun>-<5 digits>.herokuapp.com
        pat = {"pages.dev": r"^[0-9a-f]{8}\.[^.]+\.pages\.dev$",
               "trycloudflare.com": r"^[a-z]+(-[a-z]+){3,}\.trycloudflare\.com$",
               "herokuapp.com": r"^[a-z]+-[a-z]+-\d{5}\.herokuapp\.com$"}.get(suf)
        rec["irb_autogen_names"] = sum(1 for n in anyn if re.match(pat, n)) if pat else None
        rec["irb_any_tenants"] = len({tenant_of(n, suf) for n in anyn})
        rec["irb_bare_blocked"] = rec["irb_dns_fqdn_bare"] or rec["irb_http_fqdn_bare"]
        out.append(rec)
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# Tranco: is the bare platform suffix in the daily test input of GFWatch/IRBlock?
# ---------------------------------------------------------------------------
def tranco_bare():
    out = []
    for f in sorted(glob.glob(os.path.join(RAW, "tranco", "tranco_*_top1m.csv"))):
        date = os.path.basename(f).split("_")[1]
        t = pd.read_csv(f, header=None, names=["rank", "domain"])
        t = t[t.domain.isin(SUFFIXES)]
        n_tenants = 0
        for suf in SUFFIXES:
            r = t[t.domain == suf]
            out.append({"tranco_date": date, "platform": suf,
                        "bare_rank": int(r["rank"].iloc[0]) if len(r) else None})
    df = pd.DataFrame(out)
    return df


# ---------------------------------------------------------------------------
# Russia: Roskomnadzor registry (z-i extracts with decision dates) + antifilter
# ---------------------------------------------------------------------------
def load_registry():
    snaps = []
    files = sorted(glob.glob(os.path.join(RAW, "zi_history", "extract_*.csv")) +
                   glob.glob(os.path.join(RAW, "zi", "extract_*.csv")))
    man = json.load(open(os.path.join(RAW, "manifest.json")))["files"]
    for f in files:
        rel = os.path.relpath(f, RAW)
        hdr = man.get(rel, {}).get("upstream_header", "")
        mm = re.search(r"(\d{4}-\d\d-\d\d)", hdr)
        label = mm.group(1) if mm else os.path.basename(f).split("_")[1]   # dump date
        x = pd.read_csv(f, dtype=str, keep_default_na=False)
        x["snapshot"] = label
        snaps.append(x)
    r = pd.concat(snaps, ignore_index=True)
    r["value"] = r.value.str.lower().str.rstrip(".")
    r["is_mask"] = r.value.str.startswith("*.")
    r["name"] = r.value.str.replace(r"^\*\.", "", regex=True)
    r["platform"] = [platform_of(n) for n in r.name]

    def kind(row):
        if row.field == "url_host":
            return "url_host"
        if row["name"] == row.platform:
            return "suffix"           # '*.pages.dev' or bare 'pages.dev'
        return "tenant_mask" if row.is_mask else "host"
    r["kind"] = r.apply(kind, axis=1)
    r["tenant"] = [tenant_of(n, p) for n, p in zip(r.name, r.platform)]
    return r


def registry_summary(r):
    snaps = sorted(r.snapshot.unique())
    latest = snaps[-1]
    out, ts = [], []
    for suf in SUFFIXES:
        x = r[r.platform == suf]
        rec = {"platform": suf}
        for snap in snaps:
            y = x[x.snapshot == snap]
            ts.append({"platform": suf, "snapshot": snap,
                       "host_entries": int(y[y.kind == "host"].name.nunique()),
                       "tenant_masks": int(y[y.kind == "tenant_mask"].name.nunique()),
                       "suffix_entry": bool((y.kind == "suffix").any()),
                       "url_hosts": int(y[y.kind == "url_host"].name.nunique()),
                       "tenants": int(y[y.kind.isin(["host", "tenant_mask", "url_host"])].tenant.nunique())})
        y = x[x.snapshot == latest]
        dom = y[y.kind.isin(["host", "tenant_mask"])]
        rec.update({
            "reg_snapshot": latest,
            "reg_host_entries": int(y[y.kind == "host"].name.nunique()),
            "reg_tenant_masks": int(y[y.kind == "tenant_mask"].name.nunique()),
            "reg_url_hosts": int(y[y.kind == "url_host"].name.nunique()),
            "reg_tenants": int(y[y.kind.isin(["host", "tenant_mask", "url_host"])].tenant.nunique()),
            "reg_suffix_entry": bool((y.kind == "suffix").any()),
            "reg_suffix_decision_date": (y[y.kind == "suffix"].decision_date.min()
                                         if (y.kind == "suffix").any() else None),
            "reg_tenant_decision_min": dom.decision_date[dom.decision_date != ""].min() if len(dom) else None,
            "reg_tenant_decision_max": dom.decision_date[dom.decision_date != ""].max() if len(dom) else None,
        })
        # first snapshot in which any tenant-level / suffix-level entry is present
        tsx = [t for t in ts if t["platform"] == suf]
        first_t = next((t["snapshot"] for t in tsx if t["host_entries"] + t["tenant_masks"] + t["url_hosts"] > 0), None)
        first_s = next((t["snapshot"] for t in tsx if t["suffix_entry"]), None)
        last_without_s = None
        if first_s:
            before = [t["snapshot"] for t in tsx if t["snapshot"] < first_s and not t["suffix_entry"]]
            last_without_s = before[-1] if before else None
        rec.update({"reg_first_snapshot_tenant": first_t, "reg_first_snapshot_suffix": first_s,
                    "reg_last_snapshot_without_suffix": last_without_s})
        out.append(rec)
    return pd.DataFrame(out), pd.DataFrame(ts)


def antifilter_summary():
    """Current registry-derived domain list (antifilter.download, 2026-10-02 snapshot) and
    the community-voted list. Only platform-suffix matches are parsed."""
    rows = {s: {"af_entries": 0, "af_suffix_entry": False, "afc_suffix_entry": False,
                "afc_entries": 0} for s in SUFFIXES}
    tens = defaultdict(set)
    for line in open(os.path.join(RAW, "antifilter", "domains_platform_extract.lst"), encoding="utf-8", errors="replace"):
        n = line.strip().lower().rstrip(".")
        n2 = n[2:] if n.startswith("*.") else n
        if not n2 or not _SUFFIX_RX.search(n2):
            continue
        p = platform_of(n2)
        if n2 == p:
            rows[p]["af_suffix_entry"] = True
        else:
            rows[p]["af_entries"] += 1
            tens[p].add(tenant_of(n2, p))
    for line in open(os.path.join(RAW, "antifilter", "community_domains.lst"), encoding="utf-8", errors="replace"):
        n = line.strip().lower().rstrip(".")
        n2 = n[2:] if n.startswith("*.") else n
        if not _SUFFIX_RX.search(n2):
            continue
        p = platform_of(n2)
        if n2 == p:
            rows[p]["afc_suffix_entry"] = True
        else:
            rows[p]["afc_entries"] += 1
    df = pd.DataFrame([{"platform": s, **v, "af_tenants": len(tens[s])} for s, v in rows.items()])
    return df


# ---------------------------------------------------------------------------
# CN: Azure Front Door day-level follow-up (episode onset/lift from OONI)
# ---------------------------------------------------------------------------
def azurefd_episode():
    fr = []
    for f in sorted(glob.glob(os.path.join(RAW, "ooni", "agg_CN_azurefd40_*_day_domain.json"))):
        d = json.load(open(f))
        fr.append(pd.DataFrame(d["result"]))
    x = pd.concat(fr, ignore_index=True)
    x = x[x.measurement_count > 0].copy()
    x["day"] = pd.to_datetime(x.measurement_start_day).dt.tz_localize(None)
    x = x[x.domain != "a02.azurefd.net"]          # zone apex, not an endpoint
    daily = x.groupby("day")[["measurement_count", "anomaly_count", "confirmed_count",
                              "failure_count", "ok_count"]].sum()
    daily["valid"] = daily.measurement_count - daily.failure_count
    daily["anom"] = daily.anomaly_count + daily.confirmed_count
    daily["share"] = daily.anom / daily.valid
    daily["endpoints"] = x.groupby("day").domain.nunique()
    first_meas = daily.index.min()
    # lift: first day d such that every later measured day has share < 0.1 and
    # the period after d has >= 14 measured days
    lift = None
    days = list(daily.index)
    for i, dday in enumerate(days):
        rest = daily.loc[dday:]
        if len(rest) >= 14 and (rest.share < 0.1).all() and daily.loc[dday, "share"] < 0.1:
            lift = dday
            break
    before = daily[daily.index < lift] if lift is not None else daily
    last_anom = before[before.anom > 0].index.max()
    pe = x[x.day < lift] if lift is not None else x
    pe = pe.groupby("domain")[["measurement_count", "failure_count", "anomaly_count", "confirmed_count"]].sum()
    pe_share = (pe.anomaly_count + pe.confirmed_count) / (pe.measurement_count - pe.failure_count)
    post = x[x.day >= lift] if lift is not None else x.iloc[0:0]
    weekly = daily.resample("W-SUN").sum()
    weekly["share"] = weekly.anom / weekly.valid
    ep = {"first_measured_day": first_meas.date().isoformat(),
          "first_day_with_anomaly": daily[daily.anom > 0].index.min().date().isoformat(),
          "last_day_with_anomaly_before_lift": last_anom.date().isoformat() if last_anom is not None else None,
          "lift_day": lift.date().isoformat() if lift is not None else None,
          "share_before_lift": float(before.anom.sum() / before.valid.sum()),
          "share_after_lift": float(daily[daily.index >= lift].anom.sum() / daily[daily.index >= lift].valid.sum()) if lift is not None else None,
          "weekly_share_min_before_lift": float(weekly[weekly.index < lift].share.min()) if lift is not None else None,
          "weekly_share_max_before_lift": float(weekly[weekly.index < lift].share.max()) if lift is not None else None,
          "endpoints": int(x.domain.nunique()),
          "measurements_before_lift": int(before.valid.sum()),
          "measurements_after_lift": int(daily[daily.index >= lift].valid.sum()) if lift is not None else 0,
          "endpoints_majority_anomalous_before_lift": int((pe_share >= 0.5).sum()),
          "endpoint_share_min_before_lift": float(pe_share.min()),
          "endpoint_share_median_before_lift": float(pe_share.median()),
          "endpoints_with_any_anomaly_after_lift": int((post.groupby("domain").anomaly_count.sum() > 0).sum())}
    return ep, daily.reset_index()


def ooni_raw_mechanisms():
    """Summarise the few raw OONI measurements kept in raw/ooni (mechanism check)."""
    out = []
    for f in sorted(glob.glob(os.path.join(RAW, "ooni", "raw_*.json"))):
        d = json.load(open(f))
        tk = d.get("test_keys", {})
        tls = tk.get("tls_handshakes") or []
        out.append({"measurement_uid": os.path.basename(f)[4:-5],
                    "start_time": d.get("measurement_start_time"), "probe_asn": d.get("probe_asn"),
                    "input": d.get("input"), "blocking": tk.get("blocking"),
                    "dns_consistency": tk.get("dns_consistency"),
                    "dns_experiment_failure": tk.get("dns_experiment_failure"),
                    "control_dns_failure": (tk.get("control") or {}).get("dns", {}).get("failure"),
                    "tls_failures": ";".join(sorted({str(h.get("failure")) for h in tls})) if tls else "",
                    "tcp_connect_failures": ";".join(sorted({str((t.get("status") or {}).get("failure")) for t in (tk.get("tcp_connect") or [])}))})
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# Qualitative primary reports (dates and quotes verified against raw/qualitative)
# ---------------------------------------------------------------------------
QUAL = [
    {"censor": "RU", "id": "tor-gitlab-40064",
     "file": "qualitative/tor_gitlab_40064_discussions.json",
     "url": "https://gitlab.torproject.org/tpo/anti-censorship/censorship-analysis/-/issues/40064",
     "date": "2025-06-23",
     "scope": "WebTunnel bridge domains (not a hosting platform)",
     "signal": "exact-FQDN SNI blocking: the bridge FQDN timed out over TLS while plain HTTP to it "
               "and HTTPS to a sibling subdomain worked; changing the SNI bypassed the block",
     "quotes": ["It seems they aren't blocking webtunnel by IP nor blocking the domain",
                "subdomains are not blocked",
                "using servername=yandex.ru parameter in torrc with patched webtunnel-client I bypassed the block"]},
    {"censor": "RU", "id": "net4people-417",
     "file": "qualitative/net4people_bbs_417.html",
     "url": "https://github.com/net4people/bbs/issues/417",
     "date": "2024-11-05",
     "scope": "Cloudflare ECH (outer SNI cloudflare-ech.com)",
     "signal": "TLS Encrypted Client Hello to Cloudflare blocked (SNI cloudflare-ech.com + ECH "
               "extension), so names behind Cloudflare cannot be hidden from SNI filtering",
     "quotes": ["is blocked in multiple networks in Russia since 2024-11-05",
                "Neither of these elements on its own is sufficient"]},
    {"censor": "IR", "id": "net4people-133",
     "file": "qualitative/net4people_bbs_133.html",
     "url": "https://github.com/net4people/bbs/issues/133",
     "date": "2022-10-10",
     "scope": "all names on Cloudflare IP addresses",
     "signal": "IP-conditioned SNI blocking: on Cloudflare IPs most SNIs got no answer after the "
               "Client Hello except Cloudflare's own names (whole-CDN collateral); a later comment "
               "(2022-10-19) reports the block lifted",
     "quotes": ["Iran blocks all SNI's which go to cloudflare's IP address except cloudflare itself",
                "Apparently, this blockage is lifted"]},
]


def qualitative_events():
    out = []
    for q in QUAL:
        txt = open(os.path.join(RAW, q["file"]), encoding="utf-8", errors="replace").read()
        txt_n = txt.replace("\\u0026#39;", "'").replace("&#39;", "'").replace("\\'", "'")
        ok = all(s in txt or s in txt_n for s in q["quotes"])
        if not ok:
            missing = [s for s in q["quotes"] if s not in txt and s not in txt_n]
            log("  [qual] quote not found in", q["file"], missing)
        rec = {k: v for k, v in q.items() if k != "quotes"}
        rec["quotes_verified"] = ok
        rec["quotes"] = " | ".join(q["quotes"])
        out.append(rec)
    # dates from the raw files
    disc = json.load(open(os.path.join(RAW, "qualitative", "tor_gitlab_40064_discussions.json")))
    notes = [n for dd in disc for n in dd["notes"] if not n.get("system")]
    first_note = min(n["created_at"] for n in notes)[:10]
    for r in out:
        if r["id"] == "tor-gitlab-40064":
            r["date"] = first_note
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# Classification: one row per censor x platform
# ---------------------------------------------------------------------------
RU_TENANT_OONI = {}   # filled by ru_tenant_ooni() before classify()
CN_HEROKU_ROUTING = {}  # filled by cn_heroku_routing() before classify()

_HEROKU_ROUTING_RX = r"\.ingress\.herokuapp\.com$|-virginia\.herokuapp\.com$"


def cn_heroku_routing(a, g):
    """Heroku routing hostnames (CNAME targets for custom domains) in OONI CN 2026
    versus GFWatch 2023-24."""
    allh = a[(a.cc == "CN") & (a.platform == "herokuapp.com") & a.eligible]
    o = allh[allh.domain.str.contains(_HEROKU_ROUTING_RX)]
    rest = allh[~allh.domain.str.contains(_HEROKU_ROUTING_RX)]
    gi = g[(g.platform == "herokuapp.com") & g.censored_domain.str.contains(r"(?:^|\.)ingress\.herokuapp\.com$")]
    return {"others_tested": len(rest), "others_blocked": int((rest.cls == "blocked").sum()),
            "ooni_tested": len(o), "ooni_clear": int((o.cls == "clear").sum()),
            "ooni_mixed": int((o.cls == "mixed").sum()), "ooni_blocked": int((o.cls == "blocked").sum()),
            "gfw_ingress_rows": len(gi),
            "gfw_ingress_first": gi.fc.min().date().isoformat() if len(gi) else None,
            "gfw_ingress_last": gi.lc.max().date().isoformat() if len(gi) else None}


def ru_tenant_ooni(a):
    """Small-sample OONI detail for RU platforms with a registry suffix entry."""
    out = {}
    for suf in SUFFIXES:
        x = a[(a.cc == "RU") & (a.platform == suf)]
        t = x[x.depth >= 1]
        b = x[x.depth == 0]
        out[suf] = {"names": len(t), "max_meas": int(t.valid.max()) if len(t) else 0,
                    "names_no_anom": int((t.anom == 0).sum()),
                    "bare_valid": int(b.valid.sum()), "bare_anom": int(b.anom.sum())}
    return out


GRAN_LABEL = {"suffix": "suffix-wide rule", "mixed": "mixed (tenant, then suffix)",
              "tenant": "per-name (tenant)", "none": "none observed",
              "insuff": "insufficient coverage"}


def _fmt(n):
    return f"{n:,}"


def classify(gfw, gl, oo, irb, reg, regts, af, tr, ep):
    rows = []
    oo = oo.set_index(["censor", "platform"])
    gfw = gfw.set_index("platform")
    gl = gl.set_index("platform")
    irb = irb.set_index("platform")
    reg = reg.set_index("platform")
    af = af.set_index("platform")
    tr_cn = tr[tr.tranco_date == "2024-09-01"].set_index("platform").bare_rank.notna().to_dict()
    tr_ir = tr[tr.tranco_date == "2025-01-01"].set_index("platform").bare_rank.notna().to_dict()
    for cc in CENSORS:
        for suf in SUFFIXES:
            o = oo.loc[(cc, suf)]
            n_t, n_b = int(o.ooni_tested), int(o.ooni_blocked)
            rec = {"censor": cc, "platform": LABEL[suf], "suffix": suf,
                   "granularity": "", "first_date": "", "first_date_meaning": "",
                   "suffix_date": "", "lifted_date": "",
                   "evidence": "", "n_tested": n_t, "n_blocked": n_b,
                   "coverage_source": f"OONI {cc} web_connectivity {o.ooni_window}: distinct host names "
                                      f"with >= {OONI_MIN_MEAS} non-failed measurements (blocked = "
                                      f">= {int(OONI_BLOCK_SHARE*100)}% anomalous or confirmed)",
                   "rule_source_blocked_names": None, "notes": ""}
            notes = []
            if suf == "workers.dev":
                notes.append("OONI counts only <worker>.<account>.workers.dev names (single-label "
                             "account names do not resolve and always look 'ok')")
            if cc == "CN":
                g = gfw.loc[suf]
                rec["evidence"] = "GFWatch (DNS) 2020-03-20..2024-09-06; OONI CN 2026-07..09; gfwlist (weak)"
                rec["rule_source_blocked_names"] = int(g.gfw_rows)
                cls = g.gfw_class
                if cls == "suffix":
                    rec["first_date"] = g.gfw_suffix_onset
                    rec["suffix_date"] = g.gfw_suffix_onset
                    rec["first_date_meaning"] = ("bare suffix first seen DNS-blocked by GFWatch" +
                                                 (" (= GFWatch start: left-censored)" if g.gfw_onset_left_censored else ""))
                elif cls == "mixed":
                    rec["first_date"] = g.gfw_tenant_first
                    rec["suffix_date"] = g.gfw_suffix_onset
                    rec["first_date_meaning"] = ("first_checked of the earliest tenant blocked before the suffix "
                                                 "rule (upper bound on onset); suffix_date = bare suffix first "
                                                 "seen DNS-blocked")
                    notes.append(f"{int(g.gfw_tenants_pre)} tenant(s) blocked before the suffix rule "
                                 f"({int(g.gfw_pre_rows_tenant_rule)} of those rows still carry a tenant-specific "
                                 "inferred rule)")
                elif cls == "tenant":
                    rec["first_date"] = g.gfw_tenant_first
                    rec["first_date_meaning"] = ("earliest GFWatch first_checked among tenant names (upper "
                                                 "bound on onset; 2020-03-20 = GFWatch start)")
                if len(g) and g.gfw_rows:
                    notes.append(f"GFWatch: {_fmt(int(g.gfw_rows))} censored names, {_fmt(int(g.gfw_tenants))} "
                                 f"tenants, {int(g.gfw_rules)} distinct inferred rules")
                if cls == "none":
                    notes.append(("bare suffix is in the Tranco top-1M of 2024-09-01 (GFWatch daily input)"
                                  if tr_cn.get(suf) else "bare suffix NOT in the 2024-09-01 Tranco list")
                                 + " and never appears in GFWatch: no suffix-wide DNS rule 2020-03..2024-09; "
                                 "how many tenant names GFWatch tested is unknown")
                    cls = "none" if (n_t >= MIN_TESTED and n_b == 0) else "insuff"
                if suf == "azurefd.net" and ep:
                    cls = "mixed"
                    rec["suffix_date"] = ep["first_day_with_anomaly"]
                    rec["lifted_date"] = ep["lift_day"]
                    notes.append(f"platform-wide episode: {ep['endpoints_majority_anomalous_before_lift']} of the "
                                 f"{ep['endpoints']} most-measured *.a02.azurefd.net endpoints anomalous in >= 50% of "
                                 f"their measurements (median {ep['endpoint_share_median_before_lift']:.0%}) from the first OONI test "
                                 f"({ep['first_measured_day']}, left-censored) to {ep['last_day_with_anomaly_before_lift']} "
                                 f"({ep['share_before_lift']:.0%} of {_fmt(ep['measurements_before_lift'])} "
                                 f"measurements; weekly {ep['weekly_share_min_before_lift']:.0%}-"
                                 f"{ep['weekly_share_max_before_lift']:.0%}), then {ep['share_after_lift']:.1%} "
                                 f"from {ep['lift_day']} ({ep['endpoints_with_any_anomaly_after_lift']} endpoint with any "
                                 "anomaly after); TLS reset after ClientHello with consistent DNS (raw OONI "
                                 "measurements); name vs (IP,name) trigger undetermined")
                gq = gl.loc[suf]
                if isinstance(gq.gfwlist_suffix_rule_first, str) and gq.gfwlist_suffix_rule_first:
                    notes.append(f"gfwlist suffix rule first {gq.gfwlist_suffix_rule_first}"
                                 + (f", current since {gq.gfwlist_suffix_rule_current_since}" if gq.gfwlist_suffix_rule_at_head
                                    else " (not in the 2026-10-02 list)"))
                if suf == "herokuapp.com" and CN_HEROKU_ROUTING:
                    h = CN_HEROKU_ROUTING
                    notes.append(f"OONI 2026: {h['ooni_clear']} of {h['ooni_tested']} tested Heroku routing "
                                 f"names (*.ingress.herokuapp.com, *-virginia.herokuapp.com) not anomalous "
                                 f"({h['ooni_mixed']} intermittent, {h['ooni_blocked']} blocked) while "
                                 f"{h['others_blocked']} of the other {h['others_tested']} tested names were "
                                 f"blocked; GFWatch has {h['gfw_ingress_rows']} DNS-blocked names under "
                                 f"ingress.herokuapp.com ({h['gfw_ingress_first']}..{h['gfw_ingress_last']})")
                if suf == "workers.dev":
                    notes.append("2026 mechanism in the kept raw OONI measurement "
                                 "20260929202119.196158_CN_webconnectivity_3d44e33e0974bd1a: DNS consistent, "
                                 "TCP connect ok, TLS reset after ClientHello on all 4 IPs (SNI-triggered); "
                                 "GFWatch's 2022-24 rule was DNS")
            elif cc == "IR":
                b = irb.loc[suf]
                rec["evidence"] = "IRBlock artifact (DNS+HTTP, Nov 2024-2025-01-15); OONI IR 2024-10..2026-09"
                rec["rule_source_blocked_names"] = int(b.irb_any_names)
                bare = []
                if b.irb_dns_fqdn_bare:
                    bare.append("DNS")
                if b.irb_http_fqdn_bare:
                    bare.append("HTTP")
                if b.irb_bare_blocked and b.irb_any_names >= 10:
                    cls = "suffix"
                    rec["first_date"] = "2025-01-15"
                    rec["suffix_date"] = "2025-01-15"
                    rec["first_date_meaning"] = ("observed by the end of the IRBlock window (Nov 2024-"
                                                 "2025-01-15); onset unknown")
                    notes.append(f"bare suffix itself blocked ({'+'.join(bare)}) and {_fmt(int(b.irb_any_names))} "
                                 f"tenant names ({_fmt(int(b.irb_dns_fqdn_names))} DNS, "
                                 f"{_fmt(int(b.irb_http_fqdn_names))} HTTP)"
                                 + (f", {_fmt(int(b.irb_autogen_names))} of them machine-generated names "
                                    "(preview hashes / quick-tunnel words / default app names)"
                                    if pd.notna(b.irb_autogen_names) and b.irb_autogen_names else ""))
                elif b.irb_any_names > 0:
                    cls = "tenant"
                    rec["first_date"] = "2025-01-15"
                    rec["first_date_meaning"] = "observed by the end of the IRBlock window; onset unknown"
                    notes.append(f"IRBlock: {int(b.irb_any_names)} tenant names blocked "
                                 f"({int(b.irb_dns_fqdn_names)} DNS, {int(b.irb_http_fqdn_names)} HTTP); "
                                 + ("bare suffix in the 2025-01-01 Tranco top-1M (IRBlock daily input) and "
                                    "not blocked" if tr_ir.get(suf) else "bare suffix not in Tranco"))
                else:
                    cls = "none" if (n_t >= MIN_TESTED and n_b == 0) else "insuff"
                    notes.append("IRBlock: no blocked name under the suffix; "
                                 + ("bare suffix in the 2025-01-01 Tranco top-1M (IRBlock daily input) and not "
                                    "blocked, so no suffix-wide rule Nov 2024-Jan 2025; " if tr_ir.get(suf) else
                                    "bare suffix not in Tranco; ")
                                 + "number of tenant names IRBlock tested is unknown")
            else:  # RU
                r = reg.loc[suf]
                a = af.loc[suf]
                rec["evidence"] = ("RKN registry (z-i snapshots 2021-12-31..2025-10-01; antifilter 2026-10-02); "
                                   "OONI RU 2024-10..2026-09")
                rec["rule_source_blocked_names"] = int(r.reg_tenants)
                ts = regts[regts.platform == suf].set_index("snapshot")
                first_snap = sorted(regts.snapshot.unique())[0]
                if r.reg_suffix_entry:
                    first_t = r.reg_first_snapshot_tenant
                    if first_t and first_t < r.reg_first_snapshot_suffix:
                        cls = "mixed"
                        rec["first_date"] = first_t
                        rec["first_date_meaning"] = ("date of the first analysed registry dump that holds a "
                                                     "per-host entry (inclusion on or before this date"
                                                     + ("; earliest dump analysed, so left-censored" if first_t == first_snap else "")
                                                     + "); suffix_date = first dump holding the suffix entry")
                    else:
                        cls = "suffix"
                        rec["first_date"] = r.reg_first_snapshot_suffix
                        rec["first_date_meaning"] = "first analysed registry dump holding the suffix entry"
                    rec["suffix_date"] = r.reg_first_snapshot_suffix
                    notes.append(f"suffix entry '*.{suf}' (registry decision date {r.reg_suffix_decision_date}) "
                                 f"absent from the dump of {r.reg_last_snapshot_without_suffix}, present in the "
                                 f"dump of {r.reg_first_snapshot_suffix}"
                                 + ("; still listed by antifilter on 2026-10-02" if a.af_suffix_entry else ""))
                elif r.reg_tenants > 0:
                    cls = "tenant"
                    rec["first_date"] = r.reg_first_snapshot_tenant
                    rec["first_date_meaning"] = ("date of the first analysed registry dump holding a per-host "
                                                 "entry (inclusion on or before this date"
                                                 + ("; earliest dump analysed, so left-censored)" if r.reg_first_snapshot_tenant == first_snap else ")"))
                else:
                    cls = "none" if not a.af_entries else "tenant"
                    notes.append("no registry entry under the suffix (complete registry 2025-10-01 and "
                                 "antifilter 2026-10-02); out-of-registry TSPU blocking not covered")
                if r.reg_tenants:
                    counts = ", ".join(f"{s}: {_fmt(int(ts.loc[s, 'tenants']))}" for s in ts.index)
                    notes.append(f"registry tenants by snapshot: {counts}; antifilter 2026-10-02: "
                                 f"{_fmt(int(a.af_tenants))}")
                if a.afc_suffix_entry:
                    notes.append("bare suffix also on the community (user-voted) antifilter list")
                if r.reg_suffix_entry and suf in RU_TENANT_OONI:
                    t = RU_TENANT_OONI[suf]
                    notes.append(f"OONI RU: {t['names']} host names under the suffix, each measured <= "
                                 f"{t['max_meas']} times, {t['names_no_anom']} without any anomaly; bare suffix "
                                 f"{t['bare_valid']} measurements, {t['bare_anom']} anomalous: enforcement of the "
                                 "suffix entry is not confirmed by OONI")
            rec["granularity"] = GRAN_LABEL[cls]
            rec["class"] = cls
            if n_t:
                notes.append(f"OONI: {n_b}/{n_t} tested host names blocked")
            elif o.ooni_names_any:
                notes.append(f"OONI: {int(o.ooni_names_any)} host names seen but none with >= {OONI_MIN_MEAS} "
                             "measurements")
            # flags: OONI vs rule source disagreement
            if cls in ("suffix", "mixed") and n_t >= MIN_TESTED and n_b / n_t < 0.5 and not (cc == "CN" and suf == "azurefd.net"):
                notes.append("FLAG: OONI blocked share < 50% despite a suffix rule")
            if cls == "tenant" and n_t >= MIN_TESTED and n_b / n_t >= 0.8:
                notes.append("FLAG: OONI blocked share >= 80%: possible later escalation")
            rec["notes"] = "; ".join(n for n in notes if n)
            rows.append(rec)
    df = pd.DataFrame(rows)
    cols = ["censor", "platform", "granularity", "first_date", "evidence", "n_tested", "n_blocked",
            "notes", "class", "suffix_date", "lifted_date", "first_date_meaning",
            "rule_source_blocked_names", "coverage_source", "suffix"]
    return df[cols]


def ru_ooni_vs_registry(a, r):
    """Aggregate only: OONI RU measurements of tenant names that are / are not
    registry-listed (z-i 2025-10-01 or antifilter 2026-10-02). No names output."""
    latest = sorted(r.snapshot.unique())[-1]
    listed = set(r[r.snapshot == latest].name)
    for line in open(os.path.join(RAW, "antifilter", "domains_platform_extract.lst"), encoding="utf-8", errors="replace"):
        n = line.strip().lower().rstrip(".")
        if n and _SUFFIX_RX.search(n):
            listed.add(n[2:] if n.startswith("*.") else n)
    y = a[(a.cc == "RU") & (a.depth >= 1)].copy()
    y["registry_listed"] = y.domain.isin(listed)
    out = y.groupby(["platform", "registry_listed"]).agg(
        names=("domain", "size"), names_eligible=("eligible", "sum"),
        names_blocked=("cls", lambda c: int((c == "blocked").sum())),
        names_any_anomaly=("anom", lambda v: int((v > 0).sum())),
        max_valid_per_name=("valid", "max"),
        valid=("valid", "sum"), anomalous=("anom", "sum")).reset_index()
    out["anomalous_share"] = out.anomalous / out.valid.where(out.valid > 0)
    return out


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
TEX_ORDER = [  # grouped by provider
    "github.io",
    "pages.dev", "workers.dev", "r2.dev", "trycloudflare.com",
    "vercel.app", "netlify.app", "herokuapp.com", "onrender.com", "fly.dev", "deno.dev",
    "appspot.com", "web.app", "firebaseapp.com", "run.app",
    "cloudfront.net", "on.aws",
    "azurewebsites.net", "azurefd.net",
]
TEX_NAME = {"on.aws": r"\texttt{*.lambda-url.*.on.aws}"}


def _yy(d):
    return "'" + d[2:4] if isinstance(d, str) and len(d) >= 4 else ""


def tex_cell(row):
    c = row["class"]
    cc = row["censor"]
    sd = row.get("suffix_date") or ""
    if c == "suffix":
        sym = r"$\bullet$"
        yr = "" if cc == "IR" else ((r"$\le$" if cc == "CN" and sd <= "2020-03-20" else "") + _yy(sd))
    elif c == "mixed":
        sym = r"$\circ{\to}\bullet$"
        yr = "" if cc == "IR" else _yy(sd)
    elif c == "tenant":
        sym, yr = r"$\circ$", ""
    elif c == "none":
        sym, yr = r"--", ""
    else:
        sym, yr = r"?", ""
    mark = ""
    if row.get("lifted_date"):
        mark = r"$^{\dagger}$"
    if cc == "RU" and c in ("suffix", "mixed"):
        mark += r"$^{\ddagger}$"
    if cc == "CN" and row["suffix"] == "herokuapp.com":
        mark += r"$^{\ast}$"
    return sym + ((r"\,{\scriptsize " + yr + "}") if yr else "") + mark


def write_tex(m, path):
    lines = [
        "% Generated by data/burn_units/analysis.py -- do not edit by hand.",
        "% Needs booktabs (loaded by acmart). One row per platform suffix.",
        r"\begin{table}[t]",
        r"\centering",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{5pt}",
        r"\caption{The blockable unit on shared hosting platforms: the granularity at which each "
        r"censor has been observed to block names under a platform suffix. Derived from existing "
        r"public datasets only (no new measurements).}",
        r"\label{tab:burn-units}",
        r"\begin{tabular}{@{}lccc@{}}",
        r"\toprule",
        r"Platform suffix & China & Iran & Russia \\",
        r"\midrule",
    ]
    mm = m.set_index(["censor", "suffix"])
    groups = [["github.io"], ["pages.dev", "workers.dev", "r2.dev", "trycloudflare.com"],
              ["vercel.app", "netlify.app", "herokuapp.com", "onrender.com", "fly.dev", "deno.dev"],
              ["appspot.com", "web.app", "firebaseapp.com", "run.app"],
              ["cloudfront.net", "on.aws"], ["azurewebsites.net", "azurefd.net"]]
    for gi, grp in enumerate(groups):
        for suf in grp:
            name = TEX_NAME.get(suf, r"\texttt{" + suf + "}")
            cells = [tex_cell(mm.loc[(cc, suf)].to_dict() | {"censor": cc, "suffix": suf})
                     for cc in CENSORS]
            lines.append(f"{name} & " + " & ".join(cells) + r" \\")
        if gi < len(groups) - 1:
            lines.append(r"\addlinespace[2pt]")
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\par\smallskip",
        r"\parbox{\columnwidth}{\scriptsize",
        r"$\bullet$~suffix-wide rule; "
        r"$\circ{\to}\bullet$~per-name blocks first, then a suffix-wide rule; "
        r"$\circ$~per-name (tenant) blocks only; --~no registry entry (out-of-registry blocking "
        r"not covered); ?~no suffix-wide rule seen (the bare suffix was tested daily and never "
        r"blocked) but too few tenant names tested. "
        r"Years: suffix rule first observed. "
        r"China: GFWatch DNS data 2020-03--2024-09 plus OONI 2026-07--09; "
        r"Iran: IRBlock, Nov.~2024--Jan.~2025 (onset unknown); "
        r"Russia: Roskomnadzor registry dumps 2021-12--2025-10 and a 2026-10 snapshot. "
        r"$^{\dagger}$All 39 most-measured \texttt{*.a02.azurefd.net} endpoints impaired from "
        r"their first tests (Aug.~2025 to Jul.~2026) until the block was lifted on 2026-09-05. "
        r"$^{\ddagger}$Registry order; enforcement not confirmed by OONI. "
        r"$^{\ast}$Heroku routing names exempt in 2026.}",
        r"\end{table}",
    ]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def evidence_long(gfw, gl, oo, irb, reg, regts, af, tr, ep, mon):
    rows = []

    def add(cc, suf, src, metric, value, window="", note=""):
        rows.append({"censor": cc, "platform": suf, "source": src, "metric": metric,
                     "value": value, "window": window, "note": note})
    for _, g in gfw.iterrows():
        for k, v in g.items():
            if k != "platform":
                add("CN", g.platform, "GFWatch", k, v, "2020-03-20..2024-09-06")
    for _, g in gl.iterrows():
        for k, v in g.items():
            if k != "platform":
                add("CN", g.platform, "gfwlist", k, v, "2009-02..2026-10-02", "community proxy list")
    for _, o in oo.iterrows():
        for k, v in o.items():
            if k not in ("platform", "censor", "ooni_window"):
                add(o.censor, o.platform, "OONI", k, v, o.ooni_window)
    for _, x in mon.iterrows():
        add("CN", x.platform, "OONI monthly", f"tested_{x.month}", x.tested, x.month)
        add("CN", x.platform, "OONI monthly", f"blocked_{x.month}", x.blocked, x.month)
    for _, b in irb.iterrows():
        for k, v in b.items():
            if k != "platform":
                add("IR", b.platform, "IRBlock", k, v, "2024-11..2025-01-15")
    for _, r in reg.iterrows():
        for k, v in r.items():
            if k != "platform":
                add("RU", r.platform, "RKN registry (z-i)", k, v, "2021-12-31..2025-10-01")
    for _, t in regts.iterrows():
        for k in ["host_entries", "tenant_masks", "suffix_entry", "url_hosts", "tenants"]:
            add("RU", t.platform, "RKN registry (z-i)", f"{k}@{t.snapshot}", t[k], t.snapshot)
    for _, a in af.iterrows():
        for k, v in a.items():
            if k != "platform":
                add("RU", a.platform, "antifilter", k, v, "2026-10-02")
    for _, t in tr.iterrows():
        add("all", t.platform, "Tranco", "bare_suffix_rank", t.bare_rank, t.tranco_date)
    for k, v in ep.items():
        add("CN", "azurefd.net", "OONI day-level (40 names)", k, v, "2025-07-01..2026-09-30")
    return pd.DataFrame(rows)


def make_figure(m, gfw, reg, ep, path):
    sys.path.insert(0, os.path.join(HERE, "..", "..", "simulations", "code"))
    import figstyle
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    figstyle.use_style()
    C_T, C_S = figstyle.COL[0], figstyle.COL[1]
    gf = gfw.set_index("platform")
    rg = reg.set_index("platform")
    D = lambda s: pd.Timestamp(s)
    GFW0, GFW1 = D("2020-03-20"), D("2024-09-06")
    O0, O1 = D("2026-07-01"), D("2026-09-30")
    RU1 = D("2026-10-02")
    rows = []   # (label, segments[(start, end, kind)], markers[(date, kind)])

    def cn_row(suf):
        g = gf.loc[suf]
        segs, marks = [], []
        t0 = D(g.gfw_tenant_first) if isinstance(g.gfw_tenant_first, str) else None
        s0 = D(g.gfw_suffix_onset) if isinstance(g.gfw_suffix_onset, str) else None
        if s0 is not None:
            if t0 is not None and t0 < s0:
                segs.append((t0, s0, "tenant"))
                marks.append((t0, "tenant"))
            segs.append((s0, GFW1, "suffix"))
            marks.append((s0, "suffix_left" if s0 <= GFW0 else "suffix"))
            segs.append((GFW1, O0, "gap_suffix"))
            segs.append((O0, O1, "suffix"))
        else:
            segs.append((t0, GFW1, "tenant"))
            marks.append((t0, "tenant_left" if t0 <= GFW0 else "tenant"))
            segs.append((GFW1, O0, "gap_tenant"))
            segs.append((O0, O1, "tenant"))
        return segs, marks

    for suf in ["appspot.com", "herokuapp.com", "workers.dev", "vercel.app"]:
        s, mk = cn_row(suf)
        rows.append((f"CN {suf}", s, mk))
    # azurefd: tenant DNS blocks (GFWatch), gap, episode, lifted
    g = gf.loc["azurefd.net"]
    t0 = D(g.gfw_tenant_first)
    e0, e1, lift = D(ep["first_measured_day"]), D(ep["last_day_with_anomaly_before_lift"]), D(ep["lift_day"])
    rows.append(("CN azurefd.net", [(t0, GFW1, "tenant"), (GFW1, e0, "gap_tenant"),
                                    (e0, e1, "suffix"), (lift, O1, "tenant")],
                 [(t0, "tenant"), (e0, "suffix_left"), (lift, "lifted")]))
    s, mk = cn_row("github.io")
    rows.append(("CN github.io", s, mk))
    # RU pages.dev and cloudfront.net from registry snapshots
    r = rg.loc["pages.dev"]
    t0, s0 = D(r.reg_first_snapshot_tenant), D(r.reg_first_snapshot_suffix)
    rows.append(("RU pages.dev", [(t0, s0, "tenant"), (s0, RU1, "suffix")],
                 [(t0, "tenant"), (s0, "suffix")]))
    r = rg.loc["cloudfront.net"]
    t0 = D(r.reg_first_snapshot_tenant)
    rows.append(("RU cloudfront.net", [(t0, RU1, "tenant")], [(t0, "tenant_left")]))

    # exact 3.33 in column width: fixed axes box, no tight bbox
    W, H = 3.33, 2.3
    fig = plt.figure(figsize=(W, H))
    L, R, B, T = 1.0, 0.08, 0.27, 0.25         # margins in inches (labels, legend)
    ax = fig.add_axes([L / W, B / H, (W - L - R) / W, (H - B - T) / H])
    n = len(rows)
    for i, (lab, segs, marks) in enumerate(rows):
        y = n - 1 - i
        for a0, a1, kind in segs:
            if kind == "tenant":
                ax.plot([a0, a1], [y, y], color=C_T, lw=1.4, solid_capstyle="butt", zorder=2)
            elif kind == "suffix":
                ax.plot([a0, a1], [y, y], color=C_S, lw=4.2, solid_capstyle="butt", zorder=3)
            elif kind == "gap_suffix":
                ax.plot([a0, a1], [y, y], color=C_S, lw=1.0, ls=(0, (1, 1.6)), zorder=1)
            elif kind == "gap_tenant":
                ax.plot([a0, a1], [y, y], color=C_T, lw=1.0, ls=(0, (1, 1.6)), zorder=1)
        for d0, kind in marks:
            if kind == "tenant":
                ax.plot(d0, y, "o", ms=3.6, mfc="white", mec=C_T, mew=1.0, zorder=4)
            elif kind == "tenant_left":
                ax.plot(d0, y, "<", ms=3.8, color=C_T, zorder=4)
            elif kind == "suffix":
                ax.plot(d0, y, "o", ms=4.2, color=C_S, mec="white", mew=0.5, zorder=5)
            elif kind == "suffix_left":
                ax.plot(d0, y, "<", ms=4.4, color=C_S, zorder=5)
            elif kind == "lifted":
                ax.plot(d0, y, marker="x", ms=4.2, color="#1a1a1a", mew=1.1, zorder=6)
    ax.set_yticks(range(n))
    ax.set_yticklabels([r[0] for r in rows][::-1], fontsize=7.5)
    ax.set_ylim(-0.7, n - 0.3)
    ax.set_xlim(D("2020-01-01"), D("2026-12-31"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=[4, 7, 10]))
    ax.yaxis.set_minor_locator(plt.NullLocator())
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", labelsize=7.5)
    ax.grid(True, axis="x", which="major", color=figstyle.GRIDGRAY, alpha=0.25, lw=0.5)
    ax.grid(False, axis="y")
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color=C_T, lw=1.4, marker="o", mfc="white", mec=C_T, ms=3.6, label="per-name blocks"),
         Line2D([], [], color=C_S, lw=4.2, label="suffix-wide"),
         Line2D([], [], color="0.35", lw=1.0, ls=(0, (1, 1.6)), label="no data"),
         Line2D([], [], color="#1a1a1a", lw=0, marker="x", ms=4.2, mew=1.1, label="lifted")]
    fig.legend(handles=h, loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=4, frameon=False,
               fontsize=7, handlelength=1.5, handletextpad=0.35, columnspacing=0.9,
               borderaxespad=0.1)
    with plt.rc_context({"savefig.bbox": "standard"}):   # keep the exact 3.33 in page
        fig.savefig(path, metadata={"CreationDate": None})  # deterministic PDF
    plt.close(fig)


def main():
    global RU_TENANT_OONI
    log("[1/8] GFWatch (China, DNS)")
    g = load_gfwatch()
    gfw = gfwatch_summary(g)
    log("[2/8] gfwlist history (about 1 minute)")
    gl, gl_ev, gl_meta = gfwlist_history()
    log("[3/8] OONI")
    o = load_ooni()
    a = ooni_domain_table(o)
    oo = ooni_summary(a, o)
    mon = ooni_monthly_cn(o)
    RU_TENANT_OONI = ru_tenant_ooni(a)
    globals()["RU_TENANT_OONI"] = RU_TENANT_OONI
    globals()["CN_HEROKU_ROUTING"] = cn_heroku_routing(a, g)
    ep, daily = azurefd_episode()
    mech = ooni_raw_mechanisms()
    log("[4/8] IRBlock (about 1 minute)")
    sets, irb_tot = load_irblock()
    irb = irblock_summary(sets)
    log("[5/8] Russian registry + antifilter")
    r = load_registry()
    reg, regts = registry_summary(r)
    af = antifilter_summary()
    log("[6/8] Tranco, qualitative reports")
    tr = tranco_bare()
    qual = qualitative_events()
    ruvr = ru_ooni_vs_registry(a, r)
    low = ruvr[ruvr.registry_listed & (ruvr.max_valid_per_name <= 2)]
    ru_low = {"platforms": sorted(low.platform), "names": int(low.names.sum()),
              "valid": int(low.valid.sum()), "anomalous": int(low.anomalous.sum())}
    log("[7/8] classification")
    m = classify(gfw, gl, oo, irb, reg, regts, af, tr, ep)
    log("[8/8] writing derived/")
    m[["censor", "platform", "granularity", "first_date", "evidence", "n_tested", "n_blocked",
       "notes", "suffix_date", "lifted_date", "first_date_meaning", "rule_source_blocked_names",
       "coverage_source"]].to_csv(os.path.join(DER, "burn_units.csv"), index=False)
    write_tex(m, os.path.join(DER, "burn_units_table.tex"))
    ev = evidence_long(gfw, gl, oo, irb, reg, regts, af, tr, ep, mon)
    ev.to_csv(os.path.join(DER, "burn_units_evidence_long.csv"), index=False)
    gfw.to_csv(os.path.join(DER, "cn_gfwatch_platform_summary.csv"), index=False)
    gl.to_csv(os.path.join(DER, "cn_gfwlist_platform_history.csv"), index=False)
    gl_ev.drop(columns=["time"]).to_csv(os.path.join(DER, "cn_gfwlist_platform_line_events.csv"), index=False)
    oo.to_csv(os.path.join(DER, "ooni_platform_summary.csv"), index=False)
    mon.to_csv(os.path.join(DER, "ooni_cn_monthly.csv"), index=False)
    daily.to_csv(os.path.join(DER, "ooni_cn_azurefd_daily.csv"), index=False)
    mech.to_csv(os.path.join(DER, "ooni_raw_mechanism_checks.csv"), index=False)
    irb.to_csv(os.path.join(DER, "ir_irblock_platform_summary.csv"), index=False)
    reg.to_csv(os.path.join(DER, "ru_registry_platform_summary.csv"), index=False)
    regts.to_csv(os.path.join(DER, "ru_registry_timeseries.csv"), index=False)
    af.to_csv(os.path.join(DER, "ru_antifilter_platform_summary.csv"), index=False)
    tr.to_csv(os.path.join(DER, "tranco_bare_suffix_ranks.csv"), index=False)
    qual.to_csv(os.path.join(DER, "qualitative_events.csv"), index=False)
    ruvr.to_csv(os.path.join(DER, "ru_ooni_vs_registry.csv"), index=False)
    # OONI per-name class table: every OONI-measured host name under the 19 suffixes,
    # including names that a registry or antifilter extract also lists. It does not
    # ship and must not be published.
    a.drop(columns=["eligible"]).to_csv(os.path.join(DER, "ooni_platform_domains.csv"), index=False)
    meta = {"generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "gfwlist": gl_meta, "irblock_line_totals": irb_tot,
            "azurefd_episode": ep,
            "ooni_file_stats": ooni_file_stats(),
            "ooni_cn_workersdev_stability": ooni_cn_workers_stability(o),
            "ru_registry_listed_low_coverage": ru_low,
            "cn_heroku_routing": globals().get("CN_HEROKU_ROUTING"),
            "thresholds": {"OONI_MIN_MEAS": OONI_MIN_MEAS, "OONI_BLOCK_SHARE": OONI_BLOCK_SHARE,
                           "OONI_CLEAR_SHARE": OONI_CLEAR_SHARE, "MIN_TESTED": MIN_TESTED},
            "class_counts": {cc: m[m.censor == cc]["class"].value_counts().to_dict() for cc in CENSORS}}
    json.dump(meta, open(os.path.join(DER, "run_meta.json"), "w"), indent=1, default=str)
    try:
        make_figure(m, gfw, reg, ep, os.path.join(DER, "fig_burn_units_timeline.pdf"))
    except Exception as e:  # noqa: BLE001
        log("figure failed:", repr(e))
        raise
    log("done:", len(m), "cells;", meta["class_counts"])


if __name__ == "__main__":
    main()
