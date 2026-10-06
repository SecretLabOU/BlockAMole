#!/usr/bin/env python3
"""
analysis.py -- regenerate every file in derived/ from raw/ (no network access).

    python3 analysis.py            # tables + summary.json + figure
    python3 analysis.py --no-fig   # tables + summary.json only
    python3 analysis.py --out DIR  # write the outputs to DIR instead of derived/

What it computes (numbered as the sections of main()):
  (i)   Snowflake proxy-IP counts per broker window, labelled with the counting
        definition in force (daily-reset sets / never-cleared map / cleared map).
  (ii)  Client rendezvous polls by country x method (HTTP, AMP cache, SQS) for the
        most recent valid periods (per-country AMP counts valid only after 2025-08-20).
  (iii) An event table: censor-, provider- and operator-side events touching Snowflake's
        names (fronts) or data path (DTLS), with the change in Tor Metrics Snowflake
        users (low/high bounds), exclusion of IODA / timeline shutdown days and of days
        with anomalous Tor Metrics 'frac', placebo percentiles, comparison transports,
        and broker-side poll changes where the broker data exist.
  (iv)  Proxy churn only as published (Bocovich et al. 2024; Chen et al. 2026), with
        each quoted figure checked against the PDF text (pdftotext).
  plus  The rdsys-admin circumvention.json history as a log of front/STUN names
        introduced and retired per country (defender-side name minting).

Event-study design (iii), all choices are constants below:
  * Daily Tor Metrics values (low and high bounds separately) are 'valid' unless the day is
    missing, its 'frac' deviates > 15 points from the centred 15-day median of frac, it is a
    shutdown day for that country (IODA country-level outage events of <= 14 days covering
    >= 1 h of the UTC day, or a bounded 'shutdown' row of the Tor Metrics timeline), or it
    falls inside another listed event of the same country.
  * Window statistics are MEDIANS of valid days.  Baselines: pre14 = last 14 valid days
    within 28 days before the start (>= 7 needed); pre7 = last 7 valid days within 21 days;
    post7 = first 7 valid days within 21 days after the end.  Primary estimator: for events
    with a known end, during / mean(pre7, post7) ('bracket', robust to trends); otherwise
    during / pre14.  'During' = the event's dates, or 7 days for point events.
  * Placebo percentile: the same estimator at every other start date within +-365 days whose
    'during' days touch no listed event and whose baseline is within 0.5x-2x of the event's
    (same usage regime).  Descriptive, not a p-value (windows overlap).
  * Sensitivity: alternative shutdown rules (none / any overlap / >= 2 IODA sources) in
    event_table_sensitivity.csv; obfs4/webtunnel/meek/<OR> in event_transport_comparison.csv.

All inputs are listed with URL / time / sha256 / license in SOURCES.md and raw/manifest.json.
"""

import argparse
import datetime as dt
import json
import math
import re
import shutil
import subprocess
import sys
import tarfile
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
DER = HERE / "derived"
FIGSTYLE_DIR = HERE.parent.parent / "simulations" / "code"

# ----------------------------------------------------------------------------
# Analysis choices
# ----------------------------------------------------------------------------
# Broker proxy-IP counting definitions (snowflake git history + window data):
#  * up to the broker restart of ~2025-06-24 20:52 UTC: per-window sets reset every
#    window (pre-78cf8e6 code: zeroMetrics) -> daily unique proxy IPs;
#  * commit 78cf8e6 (committed 2025-06-24 17:12 UTC) replaced them by a never-cleared
#    "seen" map -> from the 2nd window after each restart, only IPs new since the last
#    broker restart are counted (a LOWER BOUND on daily unique IPs);
#  * commit c8b0b31, deployed 2025-08-20 13:40 UTC (Tor Metrics timeline), clears the
#    map every window -> daily unique proxy IPs again.
T_V1_LAST = pd.Timestamp("2025-06-25 20:52:06")   # first window after the 2025-06-24 restart
T_V2_FIRST = pd.Timestamp("2025-08-21 13:40:07")  # first full window after the 2025-08-20 fix
# Per-country rendezvous split exists from this window on (broker commit b512e24):
T_COUNTRY_SPLIT = pd.Timestamp("2024-03-21 22:44:14")
# AMP-cache clients geolocated from the SDP only from the 2025-08-20 13:40 deployment:
T_AMP_GEO = T_V2_FIRST
SF_GAP = (pd.Timestamp("2026-06-30"), pd.Timestamp("2026-09-27"))  # CollecTor gap (dates)

PRE_DAYS = 14          # baseline = the last 14 valid days ...
PRE_LOOKBACK = 28      # ... within the 28 days before the event start (>= 7 needed)
MIN_BASELINE_USERS = 100  # % changes on smaller baselines are flagged, not interpreted
SHORT_DAYS = 7         # short baselines: last 7 valid days before / first 7 valid days after
SHORT_LOOK = 21        # ... within 21 days
MIN_SIDE_DAYS = 3      # each side of the bracketing baseline needs >= 3 valid days
POST_DAYS = 14         # recovery window after an event
POINT_DURING = 7       # 'during' window for point events with a lasting effect
FRAC_DEV_MAX = 15      # exclude Tor Metrics days whose frac deviates > 15 points from
FRAC_ROLL = 15         # ... the centered 15-day rolling median of frac
IODA_MIN_HOURS = 1.0   # a day is a shutdown day if outage events cover >= 1 h of it
IODA_MAX_EVENT_DAYS = 14.0  # longer single events are treated as signal artifacts
MIN_VALID_FRAC = 0.5   # a window needs >= 50 % valid days to be evaluated
PLACEBO_RANGE = 365    # placebo start dates within +-365 days of the event ...
PLACEBO_REGIME = (0.5, 2.0)  # ... whose baseline is within 0.5x-2x of the event's baseline

COUNTRIES = ["ru", "ir", "cn", "tm"]
CMP_TRANSPORTS = ["obfs4", "webtunnel", "meek", "<OR>"]


def log(*a):
    print(*a, flush=True)


# ----------------------------------------------------------------------------
# 1. CollecTor snowflake-stats
# ----------------------------------------------------------------------------
RE_END = re.compile(r"snowflake-stats-end (\S+ \S+) \((\d+) s\)")
COUNTRY_FIELDS = {"snowflake-ips": "proxies", "client-http-ips": "http",
                  "client-ampcache-ips": "amp", "client-sqs-ips": "sqs"}
NUM_FIELDS = {
    "snowflake-ips-total": "ips_total", "snowflake-ips-webext": "ips_webext",
    "snowflake-ips-standalone": "ips_standalone", "snowflake-ips-iptproxy": "ips_iptproxy",
    "snowflake-ips-badge": "ips_badge", "snowflake-ips-bloco": "ips_bloco",
    "snowflake-ips-nat-restricted": "nat_restricted",
    "snowflake-ips-nat-unrestricted": "nat_unrestricted",
    "snowflake-ips-nat-unknown": "nat_unknown",
    "snowflake-idle-count": "proxy_idle_polls",
    "client-snowflake-match-count": "client_matches",
    "client-snowflake-timeout-count": "client_timeouts",
    "client-denied-count": "client_denied",
    "client-http-count": "http_polls", "client-ampcache-count": "amp_polls",
    "client-sqs-count": "sqs_polls",
}


def iter_stats_texts():
    for f in sorted((RAW / "collector/archive").glob("snowflakes-*.tar.xz")):
        with tarfile.open(f) as t:
            for m in sorted(t.getmembers(), key=lambda m: m.name):
                if m.isfile():
                    yield f"{f.name}:{m.name}", t.extractfile(m).read().decode("utf-8", "replace")
    for f in sorted((RAW / "collector/recent").glob("*-snowflake-stats")):
        yield f"recent/{f.name}", f.read_text()


def parse_country_map(s):
    out = {}
    if not isinstance(s, str) or not s.strip():
        return out
    for kv in s.split(","):
        k, _, v = kv.partition("=")
        if k and v:
            out[k] = int(v)
    return out


def load_snowflake_stats():
    """Return (windows DataFrame, per-country long DataFrame, hygiene dict)."""
    copies = defaultdict(list)
    n_files = 0
    for src, text in iter_stats_texts():
        n_files += 1
        cur = None
        for ln in text.splitlines():
            if not ln.strip() or ln.startswith("@type"):
                continue
            m = RE_END.match(ln)
            if m:
                cur = {"window_end_utc": m.group(1), "window_secs": int(m.group(2))}
                copies[m.group(1)].append((src, cur))
                continue
            if cur is not None:
                k, _, v = ln.partition(" ")
                cur[k] = v.strip()
    n_records = sum(len(v) for v in copies.values())
    inconsistent = 0
    rows = []
    for end, lst in copies.items():
        base = lst[0][1]
        for _, other in lst[1:]:
            if other != base:
                inconsistent += 1
        r = dict(base)
        r["n_copies"] = len(lst)
        r["first_source"] = lst[0][0]
        rows.append(r)
    raw = pd.DataFrame(rows)
    w = pd.DataFrame({"window_end_utc": pd.to_datetime(raw["window_end_utc"]),
                      "window_secs": raw["window_secs"], "n_copies": raw["n_copies"],
                      "first_source": raw["first_source"]})
    for k, col in NUM_FIELDS.items():
        w[col] = pd.to_numeric(raw[k], errors="coerce") if k in raw else np.nan
    cmaps = {col: raw[k].map(parse_country_map) if k in raw else pd.Series([{}] * len(raw))
             for k, col in COUNTRY_FIELDS.items()}
    w = w.sort_values("window_end_utc").reset_index(drop=True)
    order = raw["window_end_utc"].map(pd.Timestamp).argsort().values
    for col in cmaps:
        cmaps[col] = cmaps[col].iloc[order].reset_index(drop=True)

    # --- hygiene: inactive parallel broker instance (2024-09-19 .. 2024-11-24) ---
    inactive = ((w["proxy_idle_polls"].fillna(0) == 0) & (w["client_matches"].fillna(0) == 0)
                & (w["ips_total"].fillna(0) <= 1))
    w["flag"] = np.where(inactive, "inactive_instance", "")
    # --- date of the window = UTC date of its midpoint ---
    w["date"] = (w["window_end_utc"] - pd.to_timedelta(w["window_secs"] / 2, unit="s")).dt.normalize()
    # --- collisions: keep the most active window per date ---
    act = w[w["flag"] == ""].copy()
    act["_activity"] = act["proxy_idle_polls"].fillna(0) + act["client_matches"].fillna(0)
    keep = act.sort_values("_activity").groupby("date").tail(1).index
    dup_idx = act.index.difference(keep)
    w.loc[dup_idx, "flag"] = "superseded_same_date"
    # --- proxy-count definition ---
    e = w["window_end_utc"]
    w["proxy_count_definition"] = np.select(
        [e <= T_V1_LAST, e < T_V2_FIRST],
        ["daily_unique_reset_each_window", "new_since_last_restart_lower_bound"],
        "daily_unique_cleared_each_window")
    # --- artifact: implausibly low proxy count vs. rolling median (new broker host) ---
    ok = w["flag"] == ""
    med = w.loc[ok, "ips_total"].rolling(15, center=True, min_periods=5).median()
    low = ok & (w["ips_total"] < 0.01 * med.reindex(w.index))
    w.loc[low, "flag"] = "artifact_low_proxy_count"
    # validate the T_V1_LAST constant: standalone proxies must fall sharply in the next window
    nxt = w[(e > T_V1_LAST) & (w["flag"] == "")].head(1)
    cur = w[e == T_V1_LAST]
    v1_check = None
    if len(nxt) and len(cur):
        v1_check = float(nxt["ips_standalone"].iloc[0] / cur["ips_standalone"].iloc[0])
    hyg = dict(n_files=n_files, n_records=n_records, n_unique_windows=len(w),
               n_windows_with_copies=int((w["n_copies"] > 1).sum()),
               n_inconsistent_copies=inconsistent,
               n_inactive_instance=int((w["flag"] == "inactive_instance").sum()),
               n_superseded_same_date=int((w["flag"] == "superseded_same_date").sum()),
               n_artifact_low_proxy_count=int((w["flag"] == "artifact_low_proxy_count").sum()),
               artifact_windows=[str(x) for x in w.loc[w["flag"] == "artifact_low_proxy_count",
                                                       "window_end_utc"]],
               standalone_ratio_after_2025_06_24_restart=v1_check,
               first_window=str(w["window_end_utc"].min()), last_window=str(w["window_end_utc"].max()))
    # --- per-country long table ---
    recs = []
    ends = w["window_end_utc"].tolist()
    cml = {col: cm.tolist() for col, cm in cmaps.items()}
    for i, end in enumerate(ends):
        for col, cm in cml.items():
            for cc, n in cm[i].items():
                recs.append((end, col, cc, n))
    cl = pd.DataFrame(recs, columns=["window_end_utc", "field", "country", "count"])
    return w, cl, hyg


def gaps_in_dates(dates):
    d = pd.Series(sorted(set(dates)))
    diffs = d.diff().dt.days
    out = []
    for i in np.where(diffs > 1)[0]:
        out.append((d.iloc[i - 1] + pd.Timedelta(days=1), d.iloc[i] - pd.Timedelta(days=1)))
    return out


# ----------------------------------------------------------------------------
# 2. Tor Metrics
# ----------------------------------------------------------------------------
def load_tormetrics():
    parts = [pd.read_csv(RAW / f"tormetrics/userstats-bridge-combined_{c}.csv", comment="#")
             for c in COUNTRIES]
    d = pd.concat(parts, ignore_index=True)
    d["date"] = pd.to_datetime(d["date"])
    g = pd.read_csv(RAW / "tormetrics/userstats-bridge-transport_all.csv", comment="#")
    g["date"] = pd.to_datetime(g["date"])
    # frac validity (frac is identical across countries/transports on a date)
    frac = pd.concat([d.groupby("date")["frac"].first(), g.groupby("date")["frac"].first()]
                     ).groupby(level=0).first().sort_index()
    full = frac.reindex(pd.date_range(frac.index.min(), frac.index.max()))
    rmed = full.rolling(FRAC_ROLL, center=True, min_periods=5).median()
    frac_ok = ((full - rmed).abs() <= FRAC_DEV_MAX).reindex(frac.index)
    fr = pd.DataFrame({"frac": frac, "frac_rolling_median": rmed.reindex(frac.index),
                       "frac_ok": frac_ok})
    return d, g, fr


# ----------------------------------------------------------------------------
# 3. IODA + timeline shutdown masks
# ----------------------------------------------------------------------------
def load_ioda():
    rows = []
    for f in sorted((RAW / "ioda").glob("outage_events_*.json")):
        for e in json.loads(f.read_text()).get("data") or []:
            rows.append(e)
    df = pd.DataFrame(rows)
    df["cc"] = df["location"].str.split("/").str[1].str.lower()
    df = df.drop_duplicates(subset=["cc", "datasource", "method", "start", "duration"])
    df["start_utc"] = pd.to_datetime(df["start"], unit="s")
    df["end_utc"] = df["start_utc"] + pd.to_timedelta(df["duration"], unit="s")
    df["days"] = df["duration"] / 86400.0
    return df.sort_values(["cc", "start"]).reset_index(drop=True)


def load_timeline():
    rows, hdr = [], None
    for ln in (RAW / "gitlab/metrics-timeline/README.md").read_text(encoding="utf-8").splitlines():
        if not ln.startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip()[1:-1].split("|")]
        if cells[0] == "start date":
            hdr = cells
            continue
        if hdr is None or set(ln.replace("|", "").strip()) <= set("-: "):
            continue
        if len(cells) == len(hdr):
            rows.append(dict(zip(hdr, cells)))
    t = pd.DataFrame(rows)
    t["description_plain"] = t["description"].str.replace(r"\[([^\]]*)\]\([^)]*\)", r"\1", regex=True)
    t["approx"] = t["start date"].str.startswith("~")

    def ts(s):
        s = s.lstrip("~").strip()
        if not s or s == "ongoing":
            return pd.NaT
        return pd.Timestamp(s)
    t["start_ts"] = t["start date"].map(ts)
    t["end_ts"] = t["end date"].map(ts)
    t["ongoing"] = t["end date"].eq("ongoing")
    return t


def interval_union_hours(intervals, day):
    """Hours of [day, day+1) covered by the union of (start, end) intervals."""
    a0, a1 = day, day + pd.Timedelta(days=1)
    segs = sorted((max(s, a0), min(e, a1)) for s, e in intervals if e > a0 and s < a1)
    tot, cs, ce = 0.0, None, None
    for s, e in segs:
        if cs is None:
            cs, ce = s, e
        elif s <= ce:
            ce = max(ce, e)
        else:
            tot += (ce - cs).total_seconds()
            cs, ce = s, e
    if cs is not None:
        tot += (ce - cs).total_seconds()
    return tot / 3600.0


def shutdown_masks(ioda, tl, d0, d1):
    """Per country-day: IODA coverage (h) and source counts, timeline shutdown flag,
    and the exclusion masks (primary + sensitivity variants)."""
    days = pd.date_range(d0, d1)
    shut = tl[tl["description_plain"].str.contains("shutdown", case=False)
              & tl["start_ts"].notna() & tl["end_ts"].notna()]
    out = []
    for cc in COUNTRIES:
        ev = ioda[ioda["cc"] == cc]
        tls = []
        for _, r in shut[shut["places"].str.split().apply(lambda p: cc in p)].iterrows():
            s, e = r["start_ts"], r["end_ts"]
            if e == e.normalize() and len(r["end date"]) <= 10:   # date-only end: whole day
                e = e + pd.Timedelta(days=1)
            tls.append((s, e))
        st = ev["start_utc"].to_numpy(dtype="datetime64[ns]")
        en = ev["end_utc"].to_numpy(dtype="datetime64[ns]")
        dd = ev["days"].to_numpy()
        ds = ev["datasource"].to_numpy()
        sc = ev["score"].to_numpy()
        d0n = days.to_numpy(dtype="datetime64[ns]")
        d1n = d0n + np.timedelta64(1, "D")
        ovm = (en[None, :] > d0n[:, None]) & (st[None, :] < d1n[:, None])
        for k, day in enumerate(days):
            j = np.nonzero(ovm[k])[0]
            th = interval_union_hours(tls, day) if tls else 0.0
            if len(j) == 0:
                out.append(dict(country=cc, date=day, ioda_cover_h=0.0, ioda_cover_h_incl_long=0.0,
                                ioda_n_sources=0, ioda_n_sources_incl_long=0, ioda_max_score=0.0,
                                timeline_shutdown_h=round(th, 3)))
                continue
            shortj = [x for x in j if dd[x] <= IODA_MAX_EVENT_DAYS]
            out.append(dict(
                country=cc, date=day,
                ioda_cover_h=round(interval_union_hours([(pd.Timestamp(st[x]), pd.Timestamp(en[x])) for x in shortj], day), 3),
                ioda_cover_h_incl_long=round(interval_union_hours([(pd.Timestamp(st[x]), pd.Timestamp(en[x])) for x in j], day), 3),
                ioda_n_sources=int(len(set(ds[shortj]))),
                ioda_n_sources_incl_long=int(len(set(ds[j]))),
                ioda_max_score=float(sc[j].max()),
                timeline_shutdown_h=round(th, 3)))
    m = pd.DataFrame(out)
    m["excl_primary"] = (m["ioda_cover_h"] >= IODA_MIN_HOURS) | (m["timeline_shutdown_h"] > 0)
    m["excl_any_overlap"] = (m["ioda_cover_h_incl_long"] > 0) | (m["timeline_shutdown_h"] > 0)
    m["excl_multi_source"] = (m["ioda_n_sources"] >= 2) | (m["timeline_shutdown_h"] > 0)
    return m


# ----------------------------------------------------------------------------
# 4. Event table
# ----------------------------------------------------------------------------
TL_IR_SSTATIC = [("2023-01-16", "2023-01-24"), ("2023-01-31", "2023-02-01"),
                 ("2023-02-10", "2023-02-13"), ("2023-02-19", "2023-02-19"),
                 ("2023-02-22", "2023-02-22"), ("2023-03-03", "2023-03-03"),
                 ("2023-03-08", "2023-03-08"), ("2023-03-13", "2023-03-13"),
                 ("2023-03-19", "2023-03-19")]


def event_list():
    E = []
    for i, (s, e) in enumerate(TL_IR_SSTATIC, 1):
        E.append(dict(event_id=f"IR-sstatic-{i}", countries=["ir"], start=s, end=e,
                      actor="censor", layer="rendezvous name (front domain cdn.sstatic.net)",
                      description="cdn.sstatic.net (front used by Snowflake and Moat) blocked in some ISPs in Iran",
                      source="Tor Metrics timeline; net4people/bbs #197"))
    E += [
        dict(event_id="CN-front-2023-05", countries=["cn"], start="2023-05-12", end="2023-05-14",
             actor="censor (Snowflake possibly collateral)",
             layer="rendezvous channel (front SNI; triggered by 2-3 same-SNI HTTPS connections)",
             description="Timeline: 'Block of Snowflake default front domain in China'; Bocovich et al. 2024: censorship apparently triggered by multiple same-SNI HTTPS connections to certain IPs, user count about halved, back on 2023-05-15",
             source="Tor Metrics timeline; Bocovich et al. 2024 Sec. 5.3"),
        dict(event_id="TM-front-2021-10", countries=["tm"], start="2021-10-24", end=None,
             actor="censor", layer="rendezvous name (default broker front domain; DNS + TLS SNI)",
             description="Snowflake users in Turkmenistan drop to zero; Bocovich et al. 2024: 'caused by blocking of the default broker front domain' (timeline row still marked X)",
             source="Tor Metrics timeline; Bocovich et al. 2024 Sec. 5.4"),
        dict(event_id="IR-rdvTLS-2022-10", countries=["ir"], start="2022-10-04", end=None,
             actor="censor", layer="rendezvous TLS fingerprint (Go crypto/tls)",
             description="Snowflake rendezvous blocked by TLS fingerprint in Iran, during protests with daily shutdowns and a usage surge (not interpretable as a % change)",
             source="Tor Metrics timeline; Bocovich et al. 2024 Sec. 5.2"),
        dict(event_id="RU-2021-12-01", countries=["ru"], start="2021-12-01", end=None,
             actor="censor", layer="data path (DTLS fingerprint) + other Tor blocking",
             description="Russia blocks Tor directory authorities, relays, default obfs4, meek-azure and Snowflake in some ISPs (Snowflake via DTLS Server Hello supported_groups; fixed in Tor Browser 11.0.3, 2021-12-20)",
             source="Tor Metrics timeline; Bocovich et al. 2024 Sec. 5.1"),
        dict(event_id="RU-DTLS-2024-11", countries=["ru"], start="2024-11-06", end="2024-11-21",
             actor="censor", layer="data path (DTLS fingerprint)",
             description="Blocking of Snowflake DTLS connections in Russia",
             source="Tor Metrics timeline"),
        dict(event_id="RU-DTLS-2026-03-03(timeline)", countries=["ru"], start="2026-03-03", end=None,
             actor="censor", layer="data path (DTLS fingerprint)",
             description="Timeline date for blocking of the default pion/dtls fingerprint (links net4people #603)",
             source="Tor Metrics timeline (date conflicts with #603)"),
        dict(event_id="RU-DTLS-2026-03-30(#603)", countries=["ru"], start="2026-03-30", end=None,
             actor="censor", layer="data path (DTLS fingerprint)",
             description="Snowflake-targeted DTLS filtering in Russia, 'starting 2026-03-30' (net4people #603 title)",
             source="net4people/bbs #603"),
        dict(event_id="Fastly-2024-03-01", countries=["ALL", "ru", "ir", "cn", "tm"],
             start="2024-03-01", end=None, actor="provider", layer="rendezvous name (Fastly fronts in use)",
             description="Fastly stops supporting domain fronting (Snowflake, Moat, Connection Assist); Tor Browser 13.0.11 workaround 2024-03-06",
             source="Tor Metrics timeline; rdsys-admin commit 2024-03-01"),
        dict(event_id="FrontDNS-2023-09-20", countries=["ALL", "ru", "ir", "cn"],
             start="2023-09-20", end=None, actor="provider",
             layer="rendezvous name (front resolves to a different CDN)",
             description="Front domain used by Snowflake, Moat and Connection Assist sometimes resolves to a different CDN ('not caused by any censor action', Bocovich et al. 2024 Sec. 4.1)",
             source="Tor Metrics timeline; Bocovich et al. 2024"),
        dict(event_id="DNSSEC-2025-09-20", countries=["ALL", "ru", "ir", "cn", "tm"],
             start="2025-09-20", end="2025-09-21", actor="operator (Tor's own domains)",
             layer="operator name (torproject.org/.net DNSSEC outage)",
             description="DNSSEC outage prevents resolution of torproject.org/.net; affects Snowflake",
             source="Tor Metrics timeline"),
        dict(event_id="CDN77-outage-2025-06-10", countries=["ALL"], start="2025-06-10", end="2025-06-10",
             actor="provider", layer="rendezvous name (CDN77 fronting, 5.5 h)",
             description="Temporary outage of CDN77 domain fronting 13:55-19:24 UTC",
             source="Tor Metrics timeline"),
    ]
    for e in E:
        e["start"] = pd.Timestamp(e["start"])
        e["end"] = pd.Timestamp(e["end"]) if e["end"] else None
    return E


def during_bounds(ev):
    s = ev["start"]
    if ev["end"] is not None:
        return s, ev["end"], "range"
    return s, s + pd.Timedelta(days=POINT_DURING - 1), f"point (+{POINT_DURING} d)"


def series_for(tm, tmg, cc, transport):
    """Daily low/high series (DatetimeIndex) for a country ('ALL' = global users)."""
    if cc == "ALL":
        x = tmg[tmg["transport"] == transport].set_index("date")["users"]
        return x.astype(float), x.astype(float)
    x = tm[(tm["country"] == cc) & (tm["transport"] == transport)].set_index("date")
    return x["low"].astype(float), x["high"].astype(float)


CAL0, CAL1 = pd.Timestamp("2018-01-01"), pd.Timestamp("2026-12-31")
CAL = pd.date_range(CAL0, CAL1)


def valid_mask(cc, fr, masks, rule="excl_primary"):
    """Boolean array over CAL: Tor Metrics frac OK and (country) not a shutdown day."""
    ok = fr["frac_ok"].reindex(CAL).fillna(False).to_numpy(dtype=bool)
    if cc != "ALL" and masks is not None and rule in masks:
        bad = masks.loc[(masks["country"] == cc) & masks[rule], "date"]
        ok &= ~CAL.isin(bad)
    return ok


class Daily:
    """Daily series on the fixed calendar CAL with a validity mask; O(1) window means."""

    def __init__(self, series, ok):
        v = series.reindex(CAL).to_numpy(dtype=float)
        self.present = ~np.isnan(v)
        use = self.present & ok
        self.v, self.use = v, use
        self.cs = np.concatenate([[0.0], np.cumsum(np.where(use, v, 0.0))])
        self.cn = np.concatenate([[0], np.cumsum(use)])

    @staticmethod
    def i(t):
        return (pd.Timestamp(t) - CAL0).days

    # Window statistics are MEDIANS of the valid daily values: robust to one-day
    # measurement artifacts (e.g. Snowflake-bridge restarts that shift users between
    # transports for a day, as on 2024-02-16/17).
    def mean(self, a, b):
        """Median of valid values in [a, b] -> (median, n_valid, n_days)."""
        i, j = max(0, self.i(a)), min(len(CAL), self.i(b) + 1)
        sel = self.v[i:j][self.use[i:j]]
        return (float(np.median(sel)) if len(sel) else np.nan), int(len(sel)), j - i

    def baseline(self, start, n=PRE_DAYS, lookback=PRE_LOOKBACK):
        """Median of the last n valid days within `lookback` days before `start`.
        Returns (median, n_valid_used, first_day_used)."""
        j = self.i(start)
        i = max(0, j - lookback)
        idx = np.nonzero(self.use[i:j])[0][-n:] + i
        if len(idx) == 0:
            return np.nan, 0, None
        return float(np.median(self.v[idx])), len(idx), CAL[idx[0]]

    def forward(self, end, n=SHORT_DAYS, lookahead=SHORT_LOOK):
        """Median of the first n valid days within `lookahead` days after `end`."""
        i = self.i(end) + 1
        j = min(len(CAL), i + lookahead)
        idx = np.nonzero(self.use[i:j])[0][:n] + i
        if len(idx) == 0:
            return np.nan, 0, None
        return float(np.median(self.v[idx])), len(idx), CAL[idx[-1]]


def pct(a, b):
    return 100.0 * (a / b - 1.0) if (b and not math.isnan(a) and not math.isnan(b) and b > 0) else np.nan


def event_days_mask(all_events, cc, exclude_id=None):
    """CAL-mask of the 'during' days of listed events relevant to country cc."""
    m = np.zeros(len(CAL), dtype=bool)
    for ev in all_events or []:
        if ev["event_id"] == exclude_id:
            continue
        if cc == "ALL" or cc in ev["countries"] or "ALL" in ev["countries"]:
            a, b, _ = during_bounds(ev)
            i, j = max(0, Daily.i(a)), min(len(CAL), Daily.i(b) + 1)
            if j > i:
                m[i:j] = True
    return m


def estimates(L, s, e, is_range):
    """Counterfactual baselines for the during window [s, e]."""
    d_mean, d_n, d_tot = L.mean(s, e)
    b14, n14, f14 = L.baseline(s, PRE_DAYS, PRE_LOOKBACK)
    b7, n7, _ = L.baseline(s, SHORT_DAYS, SHORT_LOOK)
    out = dict(during=d_mean, during_n=d_n, during_tot=d_tot, base14=b14, base14_n=n14,
               base14_first=f14, base7=b7, base7_n=n7, post7=np.nan, post7_n=0, bracket=np.nan)
    if is_range:
        p7, np7, _ = L.forward(e, SHORT_DAYS, SHORT_LOOK)
        out.update(post7=p7, post7_n=np7)
        if n7 >= MIN_SIDE_DAYS and np7 >= MIN_SIDE_DAYS:
            out["bracket"] = 0.5 * (b7 + p7)
    return out


def event_stats(ev, cc, tm, tmg, fr, masks, rule="excl_primary", transport="snowflake",
                with_placebo=True, all_events=None):
    lo, hi = series_for(tm, tmg, cc, transport)
    if lo.empty:
        return None
    ok = valid_mask(cc, fr, masks, rule)
    other = event_days_mask(all_events, cc, exclude_id=ev["event_id"])
    L, H = Daily(lo, ok & ~other), Daily(hi, ok & ~other)
    s, e, kind = during_bounds(ev)
    is_range = ev["end"] is not None
    post_a, post_b = e + pd.Timedelta(days=1), e + pd.Timedelta(days=POST_DAYS)
    r = dict(event_id=ev["event_id"], country=cc, transport=transport,
             exclusion_rule=rule if masks is not None else "none",
             start=s.date(), during_end=e.date(), window_kind=kind)
    el, eh = estimates(L, s, e, is_range), estimates(H, s, e, is_range)
    r.update(pre_low=el["base14"], pre_high=eh["base14"], pre_valid_days=el["base14_n"],
             pre_first_day_used=el["base14_first"].date() if el["base14_first"] is not None else None,
             pre7_low=el["base7"], pre7_valid_days=el["base7_n"],
             post7_low=el["post7"], post7_valid_days=el["post7_n"],
             bracket_low=el["bracket"], bracket_high=eh["bracket"],
             during_low=el["during"], during_high=eh["during"],
             during_valid_days=el["during_n"], during_days=el["during_tot"])
    pm, pn, pt = L.mean(post_a, post_b)
    r.update(post_low=pm, post_valid_days=pn, post_days=pt)
    enough = (r["pre_valid_days"] >= MIN_VALID_FRAC * PRE_DAYS
              and r["during_valid_days"] >= max(1, MIN_VALID_FRAC * r["during_days"]))
    r["evaluable"] = bool(enough)
    r["small_baseline"] = bool(r["pre_low"] < MIN_BASELINE_USERS) if r["pre_low"] == r["pre_low"] else None
    r["chg_vs_pre14_low_pct"] = pct(r["during_low"], r["pre_low"]) if enough else np.nan
    r["chg_vs_pre7_low_pct"] = (pct(r["during_low"], r["pre7_low"])
                                if (enough and r["pre7_valid_days"] >= MIN_SIDE_DAYS) else np.nan)
    r["chg_vs_bracket_low_pct"] = pct(r["during_low"], r["bracket_low"]) if enough else np.nan
    use_bracket = is_range and r["bracket_low"] == r["bracket_low"]
    r["primary_estimator"] = "bracket(pre7,post7)" if use_bracket else "pre14"
    bl = r["bracket_low"] if use_bracket else r["pre_low"]
    bh = r["bracket_high"] if use_bracket else r["pre_high"]
    r["chg_primary_low_pct"] = pct(r["during_low"], bl) if enough else np.nan
    r["chg_primary_high_pct"] = pct(r["during_high"], bh) if enough else np.nan
    # widest interval consistent with the low/high bounds
    r["chg_primary_bound_min_pct"] = pct(r["during_low"], bh) if enough else np.nan
    r["chg_primary_bound_max_pct"] = pct(r["during_high"], bl) if enough else np.nan
    post_ok = r["post_valid_days"] >= MIN_VALID_FRAC * r["post_days"]
    r["chg_post14_vs_pre14_low_pct"] = pct(r["post_low"], r["pre_low"]) if (enough and post_ok) else np.nan
    # missing / excluded day counts over the lookback+during+post span
    i0, i1 = max(0, Daily.i(s - pd.Timedelta(days=PRE_LOOKBACK))), Daily.i(post_b) + 1
    present = L.present[i0:i1]
    fr_ok = fr["frac_ok"].reindex(CAL).fillna(False).to_numpy(dtype=bool)[i0:i1]
    r["days_missing"] = int((~present).sum())
    r["days_excluded_frac"] = int((present & ~fr_ok).sum())
    if cc != "ALL" and masks is not None:
        sh = ~valid_mask(cc, fr.assign(frac_ok=True), masks, rule)[i0:i1]
        r["days_excluded_shutdown"] = int((present & sh).sum())
    else:
        r["days_excluded_shutdown"] = 0
    r["days_excluded_other_events"] = int((present & other[i0:i1]).sum())
    if with_placebo and enough:
        allm = event_days_mask(all_events, cc)
        Lp = Daily(lo, ok & ~allm)
        r.update(placebo(Lp, s, (e - s).days + 1, r["chg_primary_low_pct"], use_bracket, allm, bl))
    return r


def placebo(Lp, s0, n_during, obs, use_bracket, blocked_days, base_obs):
    """Empirical percentile of the observed change among same-length windows starting
    within +-PLACEBO_RANGE days whose 'during' days touch no listed event and whose
    baseline is within PLACEBO_REGIME x the event's baseline (same usage regime), using
    the same estimator (and the same exclusions) as the event."""
    vals = []
    for k in range(-PLACEBO_RANGE, PLACEBO_RANGE + 1):
        if k == 0:
            continue
        s = s0 + pd.Timedelta(days=k)
        b = s + pd.Timedelta(days=n_during - 1)
        if s - pd.Timedelta(days=PRE_LOOKBACK) < CAL0 or b + pd.Timedelta(days=SHORT_LOOK) > CAL1:
            continue
        i, j = Daily.i(s), Daily.i(b) + 1
        if blocked_days[i:j].any():
            continue
        est = estimates(Lp, s, b, use_bracket)
        if est["base14_n"] < MIN_VALID_FRAC * PRE_DAYS or est["during_n"] < max(1, MIN_VALID_FRAC * est["during_tot"]):
            continue
        base = est["bracket"] if use_bracket else est["base14"]
        if not base > 0 or not (PLACEBO_REGIME[0] * base_obs <= base <= PLACEBO_REGIME[1] * base_obs):
            continue
        vals.append(100.0 * (est["during"] / base - 1.0))
    if len(vals) < 30 or obs != obs:
        return dict(placebo_n=len(vals), placebo_pctile=np.nan, placebo_p05=np.nan, placebo_p95=np.nan)
    v = np.array(vals)
    return dict(placebo_n=len(v), placebo_pctile=round(100.0 * float((v <= obs).mean()), 1),
                placebo_p05=round(float(np.percentile(v, 5)), 1),
                placebo_p95=round(float(np.percentile(v, 95)), 1))


def broker_event_stats(ev, w, cl):
    """Pre/during change of broker metrics around an event (global, and per country where valid)."""
    s, e, kind = during_bounds(ev)
    pre_a, pre_b = s - pd.Timedelta(days=PRE_DAYS), s - pd.Timedelta(days=1)
    good = w[w["flag"] == ""].set_index("date")
    out = []

    def add(metric, ser, cc, note=""):
        ser = ser.dropna()
        pre = ser[(ser.index >= pre_a) & (ser.index <= pre_b)]
        dur = ser[(ser.index >= s) & (ser.index <= e)]
        if len(pre) < MIN_VALID_FRAC * PRE_DAYS or len(dur) == 0:
            return
        pm, dm = float(pre.median()), float(dur.median())
        out.append(dict(event_id=ev["event_id"], country=cc, metric=metric,
                        pre_median=pm, pre_n=len(pre), during_median=dm,
                        during_n=len(dur), chg_pct=pct(dm, pm),
                        during_max_ratio=float(dur.max() / pm) if pm > 0 else np.nan,
                        during_min_ratio=float(dur.min() / pm) if pm > 0 else np.nan,
                        note=note))
    if "ALL" in ev["countries"]:
        for m in ["http_polls", "amp_polls", "sqs_polls", "client_matches", "client_timeouts",
                  "ips_total"]:
            if m in good and good[m].notna().any():
                add(m, good[m], "ALL")
    for cc in ev["countries"]:
        if cc == "ALL":
            continue
        for meth in ["http", "amp", "sqs"]:
            x = cl[(cl["field"] == meth) & (cl["country"] == cc.upper())]
            x = x.merge(w[["window_end_utc", "date", "flag"]], on="window_end_utc")
            x = x[x["flag"] == ""]
            if meth == "amp":
                x = x[x["window_end_utc"] >= T_AMP_GEO]
            else:
                x = x[x["window_end_utc"] >= T_COUNTRY_SPLIT]
            if len(x):
                add(f"{meth}_polls_{cc.upper()}", x.set_index("date")["count"].astype(float), cc,
                    "per-country counts rounded up to multiples of 8")
    return out


# ----------------------------------------------------------------------------
# 5. rdsys-admin circumvention.json history
# ----------------------------------------------------------------------------
def host_of(u):
    try:
        return urlparse(u).hostname or ""
    except Exception:
        return ""


def parse_bridge_line(bs):
    toks = bs.split()
    kv = {}
    for t in toks[1:]:
        if "=" in t:
            k, _, v = t.partition("=")
            kv[k] = v
    transport = toks[0]
    names = defaultdict(set)
    fronts = set()
    for k in ("front", "fronts"):
        if k in kv:
            fronts |= {x for x in kv[k].split(",") if x}
    if transport == "snowflake":
        if "sqsqueue" in kv:
            method = "sqs"
            names["sqs_host"].add(host_of(kv["sqsqueue"]))
        elif "ampcache" in kv:
            method = "amp"
            names["amp_front"] |= fronts
            names["ampcache_host"].add(host_of(kv["ampcache"]))
        else:
            method = "http_fronted" if fronts else "http_direct"
            names["front"] |= fronts
            names["broker_cdn_host"].add(host_of(kv.get("url", "")))
        for ice in kv.get("ice", "").split(","):
            if ice.startswith("stun:"):
                h = ice[5:].rsplit(":", 1)[0]
                names["stun_host"].add(h)
    else:
        method = "fronted" if fronts else "other"
        names[f"{transport}_front"] |= fronts
        if "url" in kv:
            names[f"{transport}_url_host"].add(host_of(kv["url"]))
    names = {k: {x for x in v if x} for k, v in names.items()}
    return transport, method, names


def load_rdsys():
    log_tsv = pd.read_csv(RAW / "gitlab/rdsys-admin/circumvention_log.tsv", sep="\t", dtype=str)
    log_tsv = log_tsv[log_tsv["exported_as"].notna() & (log_tsv["exported_as"] != "")]
    log_tsv["commit_date_utc"] = pd.to_datetime(log_tsv["commit_date"], utc=True).dt.tz_convert(None)
    log_tsv = log_tsv.sort_values("commit_date_utc").reset_index(drop=True)
    cfg_rows = []
    state = {}
    for _, c in log_tsv.iterrows():
        d = json.loads((RAW / c["exported_as"]).read_text())
        snap = {}
        for cc, v in d.items():
            per = defaultdict(set)
            methods = set()
            sources = []
            for s in v.get("settings", []):
                b = s.get("bridges", {})
                sources.append(f"{b.get('type')}:{b.get('source')}")
                for bs in b.get("bridge_strings", []) or []:
                    tr, meth, names = parse_bridge_line(bs)
                    if tr == "snowflake":
                        methods.add(meth)
                    for k, vv in names.items():
                        per[k] |= vv
            snap[cc] = (per, methods, sources)
            cfg_rows.append(dict(commit_date_utc=c["commit_date_utc"], commit=c["commit"][:10],
                                 subject=c["subject"], country=cc,
                                 settings_order=" > ".join(sources),
                                 snowflake_methods=",".join(sorted(methods)),
                                 snowflake_fronts=",".join(sorted(per.get("front", []))),
                                 snowflake_amp_fronts=",".join(sorted(per.get("amp_front", []))),
                                 snowflake_sqs_hosts=",".join(sorted(per.get("sqs_host", []))),
                                 snowflake_stun_hosts=",".join(sorted(per.get("stun_host", []))),
                                 n_stun_hosts=len(per.get("stun_host", [])),
                                 meek_fronts=",".join(sorted(set().union(*[vv for k, vv in per.items()
                                                                           if k.endswith("_front") and k.startswith("meek")])))
                                 if any(k.startswith("meek") and k.endswith("_front") for k in per) else ""))
        state[c["commit"]] = snap
    cfg = pd.DataFrame(cfg_rows)
    # name add/remove events between consecutive versions
    ev_rows = []
    prev = {}
    for _, c in log_tsv.iterrows():
        snap = state[c["commit"]]
        for cc in sorted(set(snap) | set(prev)):
            new = snap.get(cc, ({}, set(), []))[0]
            old = prev.get(cc, ({}, set(), []))[0]
            for kind in sorted(set(new) | set(old)):
                if kind in ("broker_cdn_host", "ampcache_host"):
                    pass
                a, b = set(new.get(kind, set())), set(old.get(kind, set()))
                for nm in sorted(a - b):
                    ev_rows.append(dict(commit_date_utc=c["commit_date_utc"], commit=c["commit"][:10],
                                        subject=c["subject"], country=cc, kind=kind, name=nm,
                                        action="added"))
                for nm in sorted(b - a):
                    ev_rows.append(dict(commit_date_utc=c["commit_date_utc"], commit=c["commit"][:10],
                                        subject=c["subject"], country=cc, kind=kind, name=nm,
                                        action="removed"))
        prev = snap
    nev = pd.DataFrame(ev_rows)
    # lifetimes (per country x kind x name); a name may be re-added -> several spells
    last_date = log_tsv["commit_date_utc"].max()
    spells = []
    for (cc, kind, nm), g in nev.sort_values("commit_date_utc").groupby(["country", "kind", "name"]):
        open_at = None
        for _, r in g.iterrows():
            if r["action"] == "added":
                open_at = r
            elif open_at is not None:
                spells.append(dict(country=cc, kind=kind, name=nm, added=open_at["commit_date_utc"],
                                   removed=r["commit_date_utc"], censored=False,
                                   lifetime_days=(r["commit_date_utc"] - open_at["commit_date_utc"]).total_seconds() / 86400,
                                   added_subject=open_at["subject"], removed_subject=r["subject"]))
                open_at = None
        if open_at is not None:
            spells.append(dict(country=cc, kind=kind, name=nm, added=open_at["commit_date_utc"],
                               removed=pd.NaT, censored=True,
                               lifetime_days=(last_date - open_at["commit_date_utc"]).total_seconds() / 86400,
                               added_subject=open_at["subject"], removed_subject=""))
    sp = pd.DataFrame(spells)

    def reason(subj):
        """Failure stated in the commit subject, verbatim keyword; no inference beyond it.
        Only the subject line is read, not the commit body.
        Note: 'Remove blocked Fastly domain fronts' (2024-03-01) refers to Fastly ending
        domain fronting (provider-side; Tor Metrics timeline 2024-03-01), not a censor."""
        s = (subj or "").lower()
        if not s:
            return ""
        words = [k for k in ("blocked", "nonfunctional", "no longer working", "broken", "not working")
                 if k in s]
        if not words:
            return "no failure stated in commit subject"
        who = "Fastly fronts" if "fastly" in s else ("Azure" if "azure" in s else "unnamed")
        return f"failure stated ('{words[0]}'; {who})"

    if len(sp):
        sp["removal_reason"] = sp["removed_subject"].map(reason)
        sp["lifetime_days"] = sp["lifetime_days"].round(1)
    # per name across all countries: first added anywhere .. last removal everywhere
    pn = []
    for (kind, nm), g in sp.groupby(["kind", "name"]):
        still = bool(g["censored"].any())
        first, last = g["added"].min(), (last_date if still else g["removed"].max())
        pn.append(dict(kind=kind, name=nm, countries=",".join(sorted(g["country"].unique())),
                       first_added=first, last_removed=pd.NaT if still else g["removed"].max(),
                       present_at_last_commit=still,
                       span_days=round((last - first).total_seconds() / 86400, 1),
                       removal_reasons=";".join(sorted(set(r for r in g["removal_reason"] if r)))))
    per_name = pd.DataFrame(pn)
    # removal bursts: how many distinct names one commit retires
    rem = nev[(nev["action"] == "removed") & nev["kind"].isin(["front", "amp_front", "sqs_host"])]
    bursts = (rem.groupby(["commit_date_utc", "commit", "subject"])
              .agg(n_names=("name", "nunique"), n_country_name_pairs=("name", "size"),
                   countries=("country", lambda x: ",".join(sorted(set(x)))))
              .reset_index())
    bursts["reason"] = bursts["subject"].map(reason)
    return cfg, nev, sp, log_tsv, per_name, bursts


# ----------------------------------------------------------------------------
# 6. Published churn figures (verified against the PDF text)
# ----------------------------------------------------------------------------
LIT = [
    # (source key, pdf, claim id, value, unit, quote that must appear in the text, context)
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "daily_unique_proxy_ips_2024", 140000, "proxy IPs/day",
     "140,000 daily IP addresses", "unique proxy IPs per day around early 2024 (Fig. 6 discussion)"),
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "overlap_after_1h", 97.3, "% of reference-window IPs still present",
     "97.3% of addresses in common", "proxy churn experiment, January 2023 (Sec. 4.3, Fig. 7)"),
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "overlap_after_12h", 68.8, "%",
     "after 12 hours, the fraction had fallen to 68.8%", "Sec. 4.3"),
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "overlap_after_24h", 38.2, "%",
     "after 24 hours, 38.2%", "Sec. 4.3"),
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "overlap_after_40h", 27.6, "%",
     "after 40 hours, 27.6%", "Sec. 4.3"),
    ("Chen2026", "lit/chen2026_arxiv2609.12242.pdf", "enumerated_unique_proxy_ips_48d", 21000, "proxy IPs (lower bound, 'over')",
     "over 21,000 unique proxy IP addresses", "48 days of measurement, May-June 2025 (abstract)"),
    ("Chen2026", "lit/chen2026_arxiv2609.12242.pdf", "enumerated_ases", 1000, "ASes ('almost')",
     "almost 1,000 autonomous systems", "abstract"),
    ("Chen2026", "lit/chen2026_arxiv2609.12242.pdf", "top1pct_AS_block_share", 30, "% of observed Snowflakes ('more than')",
     "blocks more than 30% of observed Snowflakes", "abstract"),
    ("Chen2026", "lit/chen2026_arxiv2609.12242.pdf", "top1pct_AS_tranco_top1m_collateral", 2.5, "% of Tranco top-1M domains (~)",
     "2.5% of Top 1M domains", "abstract"),
    ("Chen2026", "lit/chen2026_arxiv2609.12242.pdf", "churn_reduces_blocking", None, "qualitative",
     "higher proxy churn significantly reduces blocking effectiveness", "abstract (simulation)"),
    ("Chen2026", "lit/chen2026_arxiv2609.12242.pdf", "churn_limits_enumeration", None, "qualitative",
     "proxy churn limits the overall effectiveness of enumeration over time", "abstract (measurement)"),
    ("Chen2026", "lit/chen2026_arxiv2609.12242.pdf", "top1pct_AS_tranco_top100_collateral", 0, "% of Tranco top-100 domains",
     "affecting 0% of Tranco Top 100 domains", "abstract"),
    ("Chen2026", "lit/chen2026_arxiv2609.12242.pdf", "top1pct_AS_tranco_top1m_collateral_exact", 2.45, "% of Tranco top-1M domains",
     "only 2.45% of Tranco Top 1M domains", "Sec. 1 (contributions)"),
    ("Chen2026", "lit/chen2026_arxiv2609.12242.pdf", "churn_strongest_effect_on_blocking", None, "qualitative (simulation)",
     "Churn has the strongest effect on blocking", "simulation results (Effect of Churn Rate)"),
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "half_pool_turnover_about_20h", 20, "hours (about)",
     "It takes about 20 hours for 50% of the proxy pool to turn over", "Fig. 7 caption (January 2023)"),
    # published case-study statements used to label events (Bocovich et al. 2024)
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "rendezvous_front_collateral", None, "design rationale",
     "A censor cannot easily block domain-fronted rendezvous without also blocking unrelated connections to the front domain, which should be selected to have high value to the censor",
     "Sec. 2.1"),
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "amp_rendezvous_collateral", None, "design rationale",
     "This rendezvous method is not easily blocked without blocking the cache server as a whole",
     "Sec. 2.1 (AMP cache)"),
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "frontdns_2023_09_20_not_censor", None, "event label",
     "The drop in users on 2023-09-20 was not caused by any censor action",
     "Sec. 4.1: front domain changed hosting to a different CDN"),
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "ru_2021_dtls_supported_groups", None, "event label",
     "Specifically, it was the presence of a supported_groups extension in the DTLS Server Hello message produced by Pion",
     "Sec. 5.1, Russia December 2021"),
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "ru_users_dec2021_400_to_4000", None, "event context",
     "From the beginning to the end of December 2021, the number of users in Russia grew from about 400 to over 4,000",
     "Sec. 5.1"),
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "ir_2022_10_tls_fingerprint", None, "event label",
     "the cause of the decline was TLS fingerprint blocking, which stopped Snowflake rendezvous from working",
     "Sec. 5.2, Iran October 2022"),
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "ir_2023_01_front_sni_block", None, "event label",
     "The default rendezvous front domain was blocked (by TLS SNI) in some ISPs between 2023-01-16 and 2023-01-24",
     "Sec. 5.2"),
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "ir_2023_01_amp_continued", None, "event label",
     "AMP cache rendezvous continued to work", "Sec. 5.2"),
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "ir_2023_later_sporadic_little_effect", None, "event label",
     "If these were further attempts at blocking, they did not have much of an effect", "Sec. 5.2"),
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "cn_2019_proxy_ip_block_outgrown", None, "event label",
     "It stopped being a problem as the proxy pool grew in size", "Sec. 5.3, China May 2019 (proxy IP blocking)"),
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "cn_2019_stun_block_more_servers", None, "event label",
     "The solution was to add more STUN servers", "Sec. 5.3, China May 2019 (default STUN server blocked)"),
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "cn_2023_05_multi_sni_trigger", None, "event label",
     "censorship was triggered by observing multiple (two or three) HTTPS connections with the same TLS SNI to certain IP addresses within a short time",
     "Sec. 5.3, China May 2023"),
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "cn_2023_05_users_halved", None, "event label",
     "The user count from China was about halved during those three days", "Sec. 5.3"),
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "tm_2021_10_24_front_block", None, "event label",
     "The drop on 2021-10-24 was caused by blocking of the default broker front domain", "Sec. 5.4"),
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "tm_alt_front_confirmed_aug2022", None, "event duration",
     "not until August 2022", "Sec. 5.4 (alternative front confirmed working)"),
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "tm_stun_port_block", None, "event label",
     "Testing revealed blocking of the default STUN port, UDP 3478", "Sec. 5.4"),
    ("Bocovich2024", "lit/bocovich2024_usenixsec24.pdf", "dtls_defenses_reactive", None, "context",
     "are reactive rather than proactive", "Sec. 3 (DTLS fingerprinting defenses)"),
]


def pdf_pages_text(pdf):
    if not shutil.which("pdftotext"):
        return None
    n = 0
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout if shutil.which("pdfinfo") else ""
    m = re.search(r"Pages:\s+(\d+)", info)
    n = int(m.group(1)) if m else 0
    pages = []
    for p in range(1, n + 1):
        t = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), str(pdf), "-"],
                           capture_output=True, text=True).stdout
        pages.append(t)
    return pages


def norm(s):
    """Normalize PDF text and quotes: soft hyphens, line-break hyphenation, dashes,
    ligatures, curly quotes, whitespace, case."""
    s = s.replace("­", "").replace("-\n", "").replace("–", "-").replace("—", "-")
    s = s.replace("ﬁ", "fi").replace("ﬂ", "fl").replace("~", "")
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip().lower()


def verify_lit():
    cache = {}
    rows = []
    for key, pdf, cid, val, unit, quote, ctx in LIT:
        p = RAW / pdf
        if pdf not in cache:
            cache[pdf] = pdf_pages_text(p) if p.exists() else None
        pages = cache[pdf]
        found, page = False, None
        if pages:
            q = norm(quote)
            for i, t in enumerate(pages, 1):
                if q in norm(t):
                    found, page = True, i
                    break
        rows.append(dict(source=key, claim=cid, value=val, unit=unit, quote=quote, context=ctx,
                         pdf=pdf, verified_in_pdf_text=found, pdf_page=page))
    df = pd.DataFrame(rows)
    # derived (ours): linear interpolation of the 50 % overlap crossing between 12 h and 24 h
    a, b = 68.8, 38.2
    t50 = 12 + 12 * (a - 50) / (a - b)
    df = pd.concat([df, pd.DataFrame([dict(
        source="ours (from Bocovich2024 points)", claim="hours_to_50pct_overlap_linear_interp",
        value=round(t50, 1), unit="hours", quote="", context="linear interpolation between the published 12 h (68.8%) and 24 h (38.2%) overlaps; not a number stated in the paper",
        pdf="", verified_in_pdf_text=np.nan, pdf_page=np.nan)])], ignore_index=True)
    return df


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def main():
    global DER
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fig", action="store_true")
    ap.add_argument("--out", default=None,
                    help="write outputs to this directory instead of derived/ (reproducibility checks)")
    a = ap.parse_args()
    if a.out:
        DER = Path(a.out).resolve()
    DER.mkdir(parents=True, exist_ok=True)
    S = {}  # summary numbers

    # ---------------- (i) broker windows and proxy counts ----------------
    w, cl, hyg = load_snowflake_stats()
    S["collector_hygiene"] = hyg
    good = w[w["flag"] == ""].copy()
    gaps = gaps_in_dates(good["date"])
    S["collector_date_gaps_over_7d"] = [(str(x.date()), str(y.date())) for x, y in gaps
                                        if (y - x).days + 1 >= 7]
    cols = ["window_end_utc", "date", "window_secs", "flag", "proxy_count_definition", "n_copies",
            "first_source"] + list(NUM_FIELDS.values())
    out = w[cols].copy()
    for cc in ["IR", "RU", "CN", "TM", "US", "DE"]:
        x = cl[(cl["field"] == "proxies") & (cl["country"] == cc)].set_index("window_end_utc")["count"]
        out[f"proxies_in_{cc}"] = out["window_end_utc"].map(x)
    out.to_csv(DER / "sf_broker_windows.csv", index=False)

    def period_stats(df, name, a_, b_):
        x = df[(df["date"] >= a_) & (df["date"] <= b_)]
        r = dict(period=name, date_from=str(pd.Timestamp(a_).date()), date_to=str(pd.Timestamp(b_).date()),
                 n_windows=len(x), definitions=";".join(sorted(x["proxy_count_definition"].unique())))
        for c in ["ips_total", "ips_webext", "ips_iptproxy", "ips_standalone", "ips_badge", "ips_bloco"]:
            v = x[c].dropna()
            r[f"{c}_median"] = float(v.median()) if len(v) else np.nan
            r[f"{c}_p25"] = float(v.quantile(.25)) if len(v) else np.nan
            r[f"{c}_p75"] = float(v.quantile(.75)) if len(v) else np.nan
        return r
    pr = [
        period_stats(good, "v1_last_year_before_2025-06-24", "2024-06-25", "2025-06-24"),
        period_stats(good, "lower_bound_period", "2025-06-26", "2025-08-20"),
        period_stats(good, "v2_pre_gap", "2025-08-21", "2026-06-29"),
        period_stats(good, "v2_last28_pre_gap", "2026-06-02", "2026-06-29"),
        period_stats(good, "v2_post_gap", "2026-09-28", "2026-10-03"),
    ]
    for y in range(2019, 2027):
        pr.append(period_stats(good, f"year_{y}", f"{y}-01-01", f"{y}-12-31"))
    prox = pd.DataFrame(pr)
    prox.to_csv(DER / "sf_proxy_ips_summary.csv", index=False)
    # jump at the 2025-08-20 fix (definition change, not growth)
    b4 = good[(good["window_end_utc"] < T_V2_FIRST)].tail(1)
    af = good[(good["window_end_utc"] >= T_V2_FIRST)].head(1)
    S["proxy_def_change_2025_08_20"] = dict(
        last_window_before=str(b4["window_end_utc"].iloc[0]), ips_before=float(b4["ips_total"].iloc[0]),
        first_window_after=str(af["window_end_utc"].iloc[0]), ips_after=float(af["ips_total"].iloc[0]))
    S["proxy_periods"] = {r["period"]: {k: r[k] for k in ("n_windows", "ips_total_median", "ips_total_p25",
                                                         "ips_total_p75", "ips_webext_median",
                                                         "ips_iptproxy_median", "ips_standalone_median")}
                          for r in pr if not r["period"].startswith("year_")}
    log(f"(i) broker windows: {len(w)} unique, {len(good)} usable; gaps>=7d: {S['collector_date_gaps_over_7d']}")

    # ---------------- (ii) rendezvous by country x method ----------------
    rz = cl[cl["field"].isin(["http", "amp", "sqs"])].merge(
        w[["window_end_utc", "date", "flag"]], on="window_end_utc")
    rz = rz[rz["flag"] == ""].copy()
    rz["valid"] = np.where(rz["field"] == "amp", rz["window_end_utc"] >= T_AMP_GEO,
                           rz["window_end_utc"] >= T_COUNTRY_SPLIT)
    keep_cc = ["RU", "IR", "CN", "TM", "US", "DE", "??"]
    rzo = rz[rz["country"].isin(keep_cc)].rename(columns={"field": "method", "count": "polls"})
    tot = good[["window_end_utc", "date", "http_polls", "amp_polls", "sqs_polls"]].melt(
        id_vars=["window_end_utc", "date"], var_name="method", value_name="polls")
    tot["method"] = tot["method"].str.replace("_polls", "")
    tot["country"] = "ALL"
    tot["valid"] = tot["polls"].notna()
    rzo = pd.concat([rzo[["window_end_utc", "date", "country", "method", "polls", "valid"]],
                     tot[["window_end_utc", "date", "country", "method", "polls", "valid"]]])
    rzo.sort_values(["date", "country", "method"]).to_csv(DER / "sf_rendezvous_country_method_daily.csv",
                                                          index=False)
    periods = {"v2_post_gap_2026-09-28_to_10-03": ("2026-09-28", "2026-10-03"),
               "v2_last28_pre_gap_2026-06-02_to_06-29": ("2026-06-02", "2026-06-29"),
               "v2_full_2025-08-21_to_2026-06-29": ("2025-08-21", "2026-06-29")}
    rows = []
    for pname, (a_, b_) in periods.items():
        x = rz[(rz["date"] >= a_) & (rz["date"] <= b_) & rz["valid"]]
        nwin = good[(good["date"] >= a_) & (good["date"] <= b_)]["window_end_utc"].nunique()
        for cc in ["RU", "IR", "CN", "TM", "US", "??", "ALL"]:
            if cc == "ALL":
                g = good[(good["date"] >= a_) & (good["date"] <= b_)]
                m = {"http": g["http_polls"].sum(), "amp": g["amp_polls"].sum(), "sqs": g["sqs_polls"].sum()}
            else:
                y = x[x["country"] == cc]
                m = {k: float(y.loc[y["field"] == k, "count"].sum()) for k in ("http", "amp", "sqs")}
            t = sum(m.values())
            for k, v in m.items():
                rows.append(dict(period=pname, date_from=a_, date_to=b_, n_windows=nwin, country=cc,
                                 method=k, polls_sum=v, polls_per_window=v / nwin if nwin else np.nan,
                                 share_of_country_polls_pct=100 * v / t if t else np.nan))
    rec = pd.DataFrame(rows)
    # country share of each method's global polls (per-country sums are rounded up -> slight overcount)
    glob_ = rec[rec["country"] == "ALL"].set_index(["period", "method"])["polls_sum"]
    rec["share_of_global_method_pct"] = [100 * r.polls_sum / glob_[(r.period, r.method)]
                                         if glob_[(r.period, r.method)] else np.nan
                                         for r in rec.itertuples()]
    rec.to_csv(DER / "sf_rendezvous_recent_by_country_method.csv", index=False)
    S["rendezvous_recent"] = {
        p: {cc: {r.method: dict(polls_per_window=round(r.polls_per_window), share_pct=round(r.share_of_country_polls_pct, 1))
                 for r in rec[(rec["period"] == p) & (rec["country"] == cc)].itertuples()}
            for cc in ["RU", "IR", "CN", "ALL", "??"]} for p in periods}
    # monthly per-country series (context)
    mon = rz.copy()
    mon["month"] = mon["date"].dt.to_period("M").astype(str)
    mon = mon[mon["country"].isin(["RU", "IR", "CN", "TM"])]
    mm = mon.groupby(["month", "country", "field", "valid"]).agg(polls_sum=("count", "sum"),
                                                                 n_windows=("window_end_utc", "nunique")).reset_index()
    mm["polls_per_window"] = mm["polls_sum"] / mm["n_windows"]
    mm.rename(columns={"field": "method"}).to_csv(DER / "sf_rendezvous_monthly_country_method.csv", index=False)
    log("(ii) rendezvous recent:", json.dumps(S["rendezvous_recent"]["v2_post_gap_2026-09-28_to_10-03"]))

    # ---------------- Tor Metrics, masks ----------------
    tm, tmg, fr = load_tormetrics()
    ioda = load_ioda()
    tl = load_timeline()
    masks = shutdown_masks(ioda, tl, "2021-01-01", "2026-10-03")
    masks.to_csv(DER / "shutdown_day_masks.csv", index=False)
    fr.reset_index().rename(columns={"index": "date"}).to_csv(DER / "tormetrics_frac_validity.csv", index=False)
    S["ioda"] = dict(n_events=int(len(ioda)), first_event=str(ioda["start_utc"].min()),
                     n_long_events_gt14d=int((ioda["days"] > IODA_MAX_EVENT_DAYS).sum()),
                     excluded_days_primary={cc: int(masks[(masks.country == cc)]["excl_primary"].sum()) for cc in COUNTRIES})
    ioda_long = ioda[ioda["days"] > IODA_MAX_EVENT_DAYS][["cc", "datasource", "start_utc", "end_utc", "days", "score"]]
    ioda_long.to_csv(DER / "ioda_long_events_not_used_in_primary_mask.csv", index=False)
    frm = fr.copy()
    frm["month"] = frm.index.to_period("M")
    fm = frm.groupby("month")["frac"].median()
    S["tormetrics_frac"] = dict(
        median_2025_06_to_09=float(fr.loc["2025-06-01":"2025-09-30", "frac"].median()),
        median_2025_10_to_2026_09=float(fr.loc["2025-10-01":"2026-09-30", "frac"].median()),
        n_days_frac_not_ok=int((~fr["frac_ok"].fillna(False)).sum()),
        last_date=str(fr.index.max().date()))
    miss = pd.date_range("2021-01-01", fr.index.max()).difference(fr.index)
    S["tormetrics_missing_dates_since_2021"] = [str(x.date()) for x in miss]

    # timeline extract
    pat = re.compile(r"snowflake|sstatic|fastly|domain.front|cdn77|amp ?cache|0\.4\.8\.22|broker|shutdown", re.I)
    tsel = tl[tl["description_plain"].str.contains(pat) | tl["protocols"].str.contains("snowflake")]
    tsel = tsel[(tsel["start_ts"] >= "2018-01-01") | tsel["start_ts"].isna()]
    tsel[["start date", "end date", "places", "protocols", "description_plain", "?"]].rename(
        columns={"description_plain": "description"}).to_csv(DER / "timeline_snowflake_related.csv", index=False)

    # ---------------- (iii) events ----------------
    EV = event_list()
    rows, rows_sens, rows_cmp, rows_brk = [], [], [], []
    for ev in EV:
        for cc in ev["countries"]:
            r = event_stats(ev, cc, tm, tmg, fr, masks, all_events=EV)
            if r is None:
                continue
            r.update(actor=ev["actor"], layer=ev["layer"], description=ev["description"],
                     source=ev["source"])
            rows.append(r)
            for rule in ("none", "excl_any_overlap", "excl_multi_source"):
                if cc == "ALL":
                    continue
                if rule == "none":
                    rr = event_stats(ev, cc, tm, tmg, fr, None, with_placebo=False)
                else:
                    rr = event_stats(ev, cc, tm, tmg, fr, masks, rule=rule, with_placebo=False)
                if rr:
                    rr["exclusion_rule"] = rule
                    rows_sens.append(rr)
            for trn in CMP_TRANSPORTS:
                if cc == "ALL":
                    continue
                rr = event_stats(ev, cc, tm, tmg, fr, masks, transport=trn, with_placebo=False)
                if rr:
                    rows_cmp.append({k: rr[k] for k in ("event_id", "country", "transport", "pre_low",
                                                        "during_low", "primary_estimator",
                                                        "chg_primary_low_pct", "chg_vs_pre14_low_pct",
                                                        "chg_post14_vs_pre14_low_pct", "evaluable")})
        rows_brk += broker_event_stats(ev, w, cl)
    et = pd.DataFrame(rows)
    order = ["event_id", "country", "actor", "layer", "start", "during_end", "window_kind", "evaluable",
             "small_baseline", "primary_estimator", "chg_primary_low_pct", "chg_primary_high_pct",
             "chg_primary_bound_min_pct", "chg_primary_bound_max_pct", "placebo_pctile", "placebo_p05",
             "placebo_p95", "placebo_n", "chg_vs_pre14_low_pct", "chg_vs_pre7_low_pct",
             "chg_vs_bracket_low_pct", "chg_post14_vs_pre14_low_pct",
             "pre_low", "pre_high", "pre_valid_days", "pre_first_day_used", "pre7_low",
             "pre7_valid_days", "post7_low", "post7_valid_days", "bracket_low", "bracket_high",
             "during_low", "during_high", "during_valid_days", "during_days", "post_low",
             "post_valid_days", "post_days", "days_missing", "days_excluded_frac",
             "days_excluded_shutdown", "days_excluded_other_events", "exclusion_rule", "transport",
             "description", "source"]
    et = et[[c for c in order if c in et.columns]]
    cmp_ = pd.DataFrame(rows_cmp)
    # snowflake-minus-obfs4 difference (pp) as a crude transport-specificity check
    ob = cmp_[cmp_["transport"] == "obfs4"].set_index(["event_id", "country"])["chg_primary_low_pct"]
    et["obfs4_chg_primary_low_pct"] = [ob.get((r.event_id, r.country), np.nan) for r in et.itertuples()]
    et["snowflake_minus_obfs4_pp"] = et["chg_primary_low_pct"] - et["obfs4_chg_primary_low_pct"]
    for c in et.columns:
        if et[c].dtype.kind == "f":
            et[c] = et[c].round(2)
    et.to_csv(DER / "event_table.csv", index=False)
    pd.DataFrame(rows_sens).round(2).to_csv(DER / "event_table_sensitivity.csv", index=False)
    cmp_.round(2).to_csv(DER / "event_transport_comparison.csv", index=False)
    brk = pd.DataFrame(rows_brk).round(3)
    brk.to_csv(DER / "event_broker_metrics.csv", index=False)
    S["events"] = {f"{r.event_id}|{r.country}": dict(
        estimator=r.primary_estimator, chg_low=r.chg_primary_low_pct, chg_high=r.chg_primary_high_pct,
        bounds=[r.chg_primary_bound_min_pct, r.chg_primary_bound_max_pct],
        chg_vs_pre14=r.chg_vs_pre14_low_pct, chg_vs_pre7=r.chg_vs_pre7_low_pct,
        chg_vs_bracket=r.chg_vs_bracket_low_pct, post14_vs_pre14=r.chg_post14_vs_pre14_low_pct,
        placebo_pctile=r.placebo_pctile, placebo_p05=r.placebo_p05, pre14_low=r.pre_low,
        pre7_low=r.pre7_low, post7_low=r.post7_low, during_low=r.during_low, evaluable=r.evaluable,
        small_baseline=r.small_baseline, obfs4=r.obfs4_chg_primary_low_pct,
        excl_shutdown=r.days_excluded_shutdown, excl_frac=r.days_excluded_frac,
        excl_other_events=r.days_excluded_other_events, missing=r.days_missing) for r in et.itertuples()}
    S["event_broker"] = {f"{r.event_id}|{r.metric}": dict(pre=r.pre_median, during=r.during_median, chg_pct=r.chg_pct,
                                                          max_ratio=r.during_max_ratio, min_ratio=r.during_min_ratio)
                         for r in brk.itertuples()}
    # Fastly: recovery of HTTP polls after the re-mint (Tor Browser 13.0.11, 2024-03-06)
    g2 = good.set_index("date")
    base = g2.loc["2024-02-16":"2024-02-29", "http_polls"].median()
    post = g2.loc["2024-03-02":"2024-05-31", "http_polls"]
    rec50 = post[post >= 0.5 * base]
    rec80 = post[post >= 0.8 * base]
    S["fastly_http_recovery"] = dict(
        pre_median_2024_02_16_to_29=float(base), min_after=float(post.min()), min_date=str(post.idxmin().date()),
        min_pct_of_pre=float(100 * post.min() / base),
        first_date_ge50pct=str(rec50.index.min().date()) if len(rec50) else None,
        first_date_ge80pct=str(rec80.index.min().date()) if len(rec80) else None,
        value_2024_03_31=float(g2.loc["2024-03-31", "http_polls"]) if pd.Timestamp("2024-03-31") in g2.index else None,
        amp_pre_median=float(g2.loc["2024-02-16":"2024-02-29", "amp_polls"].median()),
        amp_median_2024_03_02_to_08=float(g2.loc["2024-03-02":"2024-03-08", "amp_polls"].median()),
        matches_pre_median=float(g2.loc["2024-02-16":"2024-02-29", "client_matches"].median()),
        matches_median_2024_03_02_to_08=float(g2.loc["2024-03-02":"2024-03-08", "client_matches"].median()),
        http_median_2024_03_02_to_08=float(g2.loc["2024-03-02":"2024-03-08", "http_polls"].median()))
    log("(iii) events:", len(et), "rows; broker rows:", len(brk))

    # ---------------- rdsys-admin name history ----------------
    cfg, nev, sp, rlog, per_name, bursts = load_rdsys()
    cfg.to_csv(DER / "rdsys_circumvention_snowflake_config.csv", index=False)
    nev.to_csv(DER / "rdsys_name_events.csv", index=False)
    sp.to_csv(DER / "rdsys_name_lifetimes.csv", index=False)
    per_name.to_csv(DER / "rdsys_name_spans_all_countries.csv", index=False)
    bursts.to_csv(DER / "rdsys_removal_bursts.csv", index=False)
    rn = per_name[per_name["kind"].isin(["front", "amp_front", "sqs_host"])]
    S["rdsys_rendezvous_names"] = dict(
        n_distinct=int(len(rn)), n_present_at_last_commit=int(rn["present_at_last_commit"].sum()),
        first_added_by_year=dict(Counter(pd.to_datetime(rn["first_added"]).dt.year.astype(int).tolist())),
        span_days_removed_median=float(rn.loc[~rn["present_at_last_commit"], "span_days"].median()),
        span_days_removed_min=float(rn.loc[~rn["present_at_last_commit"], "span_days"].min()),
        span_days_removed_max=float(rn.loc[~rn["present_at_last_commit"], "span_days"].max()),
        removal_bursts=[dict(date=str(r.commit_date_utc), n_names=int(r.n_names), reason=r.reason,
                             subject=r.subject) for r in bursts.itertuples()])
    fronts = sp[sp["kind"].isin(["front", "amp_front"])]
    S["rdsys"] = dict(
        n_commits=int(len(rlog)), first_commit=str(rlog["commit_date_utc"].min()),
        last_commit=str(rlog["commit_date_utc"].max()),
        n_distinct_snowflake_fronts=int(sp.loc[sp["kind"] == "front", "name"].nunique()),
        n_distinct_amp_fronts=int(sp.loc[sp["kind"] == "amp_front", "name"].nunique()),
        n_distinct_stun_hosts=int(sp.loc[sp["kind"] == "stun_host", "name"].nunique()),
        n_front_spells=int(len(sp[sp["kind"] == "front"])),
        n_front_spells_removed=int((~sp.loc[sp["kind"] == "front", "censored"]).sum()),
        front_lifetime_days_removed_median=float(sp.loc[(sp["kind"] == "front") & ~sp["censored"], "lifetime_days"].median())
        if len(sp[(sp["kind"] == "front") & ~sp["censored"]]) else None,
        front_removal_reasons=dict(Counter(sp.loc[(sp["kind"] == "front") & ~sp["censored"], "removal_reason"])),
        n_commits_changing_snowflake_fronts=int(nev[nev["kind"].isin(["front", "amp_front"])]["commit"].nunique()),
        n_commits_changing_stun=int(nev[nev["kind"] == "stun_host"]["commit"].nunique()),
        methods_at_last_commit={r.country: r.snowflake_methods for r in
                                cfg[cfg["commit_date_utc"] == cfg["commit_date_utc"].max()].itertuples()})
    log("rdsys:", json.dumps(S["rdsys"], default=str)[:400])

    # rdsys commits that change snowflake fronts/STUN for RU/IR/CN/TM -> user change around them
    rd_ev = []
    sub = nev[nev["country"].isin(COUNTRIES) & nev["kind"].isin(["front", "amp_front", "stun_host", "sqs_host"])]
    for (cd, cm, subj, cc), g in sub.groupby(["commit_date_utc", "commit", "subject", "country"]):
        ev = dict(event_id=f"rdsys-{cm}", countries=[cc], start=cd.normalize(), end=None,
                  actor="defender (rdsys-admin)", layer="name mint/retire", description=subj,
                  source="rdsys-admin git")
        r = event_stats(ev, cc, tm, tmg, fr, masks, all_events=EV)
        if r is None:
            continue
        r.update(commit_subject=subj,
                 names_added=";".join(f"{k}:{n}" for k, n in g[g.action == "added"][["kind", "name"]].values),
                 names_removed=";".join(f"{k}:{n}" for k, n in g[g.action == "removed"][["kind", "name"]].values))
        rd_ev.append(r)
    rde = pd.DataFrame(rd_ev)
    if len(rde):
        keepc = ["event_id", "country", "start", "commit_subject", "names_added", "names_removed",
                 "evaluable", "small_baseline", "pre_low", "during_low", "chg_primary_low_pct",
                 "chg_post14_vs_pre14_low_pct", "placebo_pctile", "days_excluded_shutdown",
                 "days_missing"]
        rde[keepc].round(2).to_csv(DER / "rdsys_commit_user_changes.csv", index=False)

    # ---------------- (iv) published churn ----------------
    lit = verify_lit()
    lit.to_csv(DER / "churn_published.csv", index=False)
    S["lit_verified"] = {f"{r.source}:{r.claim}": (bool(r.verified_in_pdf_text) if r.verified_in_pdf_text == r.verified_in_pdf_text else None,
                                                     None if pd.isna(r.pdf_page) else int(r.pdf_page))
                         for r in lit.itertuples()}
    log("(iv) lit:", S["lit_verified"])

    # summary.json is written before the optional figure, so a failed figure step keeps it
    (DER / "summary.json").write_text(json.dumps(S, indent=1, default=str) + "\n")

    # ---------------- figure ----------------
    if not a.no_fig:
        make_figure(good, tm, tmg, fr, masks, cl)
    log("wrote", sorted(p.name for p in DER.iterdir()))


# ----------------------------------------------------------------------------
# Figure
# ----------------------------------------------------------------------------
FIG_DAYS = (-14, 28)


def _index_series(series, ok_dates, day0, base_days=(-14, -1), span=FIG_DAYS):
    """Event-time index: value / median(valid values in base_days). Invalid days -> NaN."""
    day0 = pd.Timestamp(day0)
    offs = np.arange(span[0], span[1] + 1)
    dates = day0 + pd.to_timedelta(offs, unit="D")
    v = series.reindex(dates).to_numpy(dtype=float)
    ok = np.array([d in ok_dates for d in dates]) & ~np.isnan(v)
    v = np.where(ok, v, np.nan)
    b = (offs >= base_days[0]) & (offs <= base_days[1]) & ok
    base = float(np.nanmedian(v[b])) if b.any() else np.nan
    return offs, v / base, base, int(b.sum())


def make_figure(good, tm, tmg, fr, masks, cl):
    sys.path.insert(0, str(FIGSTYLE_DIR))
    import figstyle
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FixedLocator, NullFormatter, FuncFormatter
    figstyle.use_style()
    C_USERS, C_HTTP, C_AMP = figstyle.COL[0], figstyle.COL[1], figstyle.COL[2]
    INK2, SHADE = "#595959", "#d9d9d9"
    plt.rcParams.update({"font.size": 7.5, "axes.labelsize": 7.5, "xtick.labelsize": 7,
                         "ytick.labelsize": 7, "legend.fontsize": 7, "axes.titlesize": 7.5})

    frac_ok = set(fr.index[fr["frac_ok"].fillna(False)])

    def ok_dates(cc):
        if cc == "ALL":
            return frac_ok
        bad = set(masks.loc[(masks["country"] == cc) & masks["excl_primary"], "date"])
        return frac_ok - bad

    def users(cc):
        lo, _ = series_for(tm, tmg, cc, "snowflake")
        return lo

    gb = good.set_index("date")

    def polls(cc, meth):
        if cc == "ALL":
            return gb[f"{meth}_polls"].astype(float)
        x = cl[(cl["field"] == meth) & (cl["country"] == cc)]
        x = x.merge(good[["window_end_utc", "date"]], on="window_end_utc")
        if meth == "amp":
            x = x[x["window_end_utc"] >= T_AMP_GEO]
        return x.set_index("date")["count"].astype(float)

    all_dates = set(gb.index)
    fig = plt.figure(figsize=(3.33, 3.55))
    gs = fig.add_gridspec(3, 2, height_ratios=[1, 0.85, 1], hspace=0.62, wspace=0.12,
                          left=0.135, right=0.985, top=0.885, bottom=0.095)
    axA = fig.add_subplot(gs[0, :])
    axB1 = fig.add_subplot(gs[1, 0])
    axB2 = fig.add_subplot(gs[1, 1], sharey=axB1)
    axC = fig.add_subplot(gs[2, :])
    info = {}

    def style_ax(ax, yticks, ylim):
        ax.set_yscale("log")
        ax.set_ylim(*ylim)
        ax.yaxis.set_major_locator(FixedLocator(yticks))
        ax.yaxis.set_minor_formatter(NullFormatter())
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
        ax.set_xlim(FIG_DAYS[0] - 0.5, FIG_DAYS[1] + 0.5)
        ax.xaxis.set_major_locator(FixedLocator([-14, -7, 0, 7, 14, 21, 28]))
        ax.axhline(1.0, color=INK2, lw=0.6, alpha=0.6, zorder=1)
        figstyle.tidy(ax)
        ax.yaxis.set_minor_locator(FixedLocator([]))

    def line(ax, x, y, c, label=None, ms=2.2):
        ax.plot(x, y, color=c, lw=1.1, marker="o", ms=ms, mew=0, label=label, zorder=3)

    def vmark(ax, x, text, ytext, ha="left"):
        ax.axvline(x, color=INK2, lw=0.7, zorder=2)
        ax.text(x + (0.6 if ha == "left" else -0.6), ytext, text, fontsize=7,
                color=INK2, ha=ha, va="center")

    # (a) Fastly, global
    d0 = "2024-03-01"
    x, yu, bu, nu = _index_series(users("ALL"), ok_dates("ALL"), d0)
    _, yh, bh, nh = _index_series(polls("ALL", "http"), all_dates, d0)
    _, ya, ba, na = _index_series(polls("ALL", "amp"), all_dates, d0)
    line(axA, x, yh, C_HTTP, "HTTP rendezvous polls")
    line(axA, x, ya, C_AMP, "AMP-cache rendezvous polls")
    line(axA, x, yu, C_USERS, "Snowflake users (Tor Metrics)")
    style_ax(axA, [0.1, 0.25, 0.5, 1, 2], (0.08, 3.6))
    vmark(axA, 0, "Fastly ends fronting", 2.9, ha="left")
    vmark(axA, 5, "new fronts (Tor Browser 13.0.11)", 1.5, ha="left")
    axA.set_title("(a) Provider-side front burn: Fastly, 1 Mar 2024 (all users)", loc="left", pad=3)
    info["a"] = dict(base_users=bu, n_users=nu, base_http=bh, base_amp=ba)

    # (b) censor blocks the front: IR 2023-01-16..24, CN 2023-05-12..14
    for ax, cc, d0, nblk, ttl in ((axB1, "ir", "2023-01-16", 9, "(b) Front SNI blocked: Iran,\n16-24 Jan 2023 (some ISPs)"),
                                  (axB2, "cn", "2023-05-12", 3, "Fronted rendezvous blocked:\nChina, 12-14 May 2023")):
        x, yu, bu, nu = _index_series(users(cc), ok_dates(cc), d0)
        ax.axvspan(-0.5, nblk - 0.5, color=SHADE, alpha=0.6, lw=0, zorder=0)
        line(ax, x, yu, C_USERS)
        style_ax(ax, [0.5, 0.75, 1, 1.25, 1.5], (0.5, 1.6))
        ax.set_title(ttl, loc="left", pad=3)
        info[f"b_{cc}"] = dict(base_users=bu, n_valid_base_days=nu)
    axB1.xaxis.set_major_locator(FixedLocator([-14, 0, 14, 28]))
    axB2.xaxis.set_major_locator(FixedLocator([-14, 0, 14, 28]))
    plt.setp(axB2.get_yticklabels(), visible=False)

    # (c) Russia, DTLS block of 2026-03-30: users fall, rendezvous polls rise
    d0 = "2026-03-30"
    x, yu, bu, nu = _index_series(users("ru"), ok_dates("ru"), d0)
    _, yh, bh, _ = _index_series(polls("RU", "http"), all_dates, d0)
    _, ya, ba, _ = _index_series(polls("RU", "amp"), all_dates, d0)
    line(axC, x, yh, C_HTTP)
    line(axC, x, ya, C_AMP)
    line(axC, x, yu, C_USERS)
    style_ax(axC, [0.5, 1, 2, 4], (0.4, 6.0))
    vmark(axC, 0, "DTLS filtering starts", 0.47, ha="left")
    vmark(axC, 9, "covert-DTLS proxies (8 Apr)", 1.22, ha="left")
    axC.set_title("(c) DTLS data path blocked: Russia, 30 Mar 2026", loc="left", pad=3)
    axC.set_xlabel("Days since event start")
    info["c"] = dict(base_users=bu, n_users=nu, base_http_RU=bh, base_amp_RU=ba)
    fig.text(0.012, 0.50, "Index (median of the 14 days before = 1; log scale)", rotation=90,
             va="center", ha="left", fontsize=7.5, color="#1a1a1a")
    h, l = axA.get_legend_handles_labels()
    order = [2, 0, 1]
    fig.legend([h[i] for i in order], [l[i] for i in order], loc="upper left",
               bbox_to_anchor=(0.005, 0.999), ncol=2, frameon=False, fontsize=7,
               handlelength=1.4, columnspacing=0.9, handletextpad=0.4, borderaxespad=0.1)
    out = DER / "fig_snowflake.pdf"
    # exact 3.33 in canvas (paper style sets savefig.bbox='tight', which would widen the
    # page and shrink text below 7 pt once scaled to the column): save the full canvas
    plt.rcParams["savefig.bbox"] = "standard"
    fig.savefig(out, metadata={"CreationDate": None})  # no local creation time in the PDF
    fig.savefig(DER / "fig_snowflake_preview.png", dpi=220)
    plt.close(fig)
    (DER / "fig_snowflake_data.json").write_text(json.dumps(info, indent=1, default=str) + "\n")
    log("figure:", out.name, json.dumps(info, default=str))


if __name__ == "__main__":
    sys.exit(main())
