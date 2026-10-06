#!/usr/bin/env python3
"""analysis.py -- regenerate derived/ for the minting analysis from raw/ only.

No network access. Inputs are the files listed in raw/manifest.json (fetched
by fetch.py). Needs pandas, matplotlib and pdftotext from poppler-utils:

    python3 analysis.py

Outputs (derived/):
  doc_text/<id>.txt             plain-text snapshots of every saved document
  doc_facts.csv                 verbatim quotes and values, checked against raw
  porkbun_tld_prices.csv        Porkbun prices for root-zone (ICANN) TLDs
  porkbun_summary.csv           summary statistics of those prices
  icann_mrr_monthly.csv         monthly registry totals for five cheap gTLDs
  icann_disposability.csv       12-month adds, deletions, renewals and ratios
  psl_platform_suffixes.csv     PSL rule, section and registered domain per
                                platform host pattern
  ct_log_list_summary.csv       Chrome-listed CT logs: API type, MMD, state
  crtsh_platform_wildcards.csv  results of the five exact-identity lookups
  scheitle2018_table4.csv       CT honeypot delays parsed from Scheitle et al.
  acme_mint_rates.csv           issuance ceilings implied by documented limits
  platform_names.csv            default tenant names, limits, CT exposure
  minting_costs.csv             cost, rate ceiling, exposure per unit type
  exposure_channels.csv         channels that reveal a minted name, delays
  fig_exposure_delays.pdf       figure of the delay ranges (not in the paper)
  summary.json                  headline numbers of the tables above
"""

import csv
import glob
import json
import os
import re
import statistics
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
DER = os.path.join(HERE, "derived")
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True          # write no __pycache__ directories
from doctext import file_to_text, norm  # noqa: E402
from facts import FACTS  # noqa: E402

FIGSTYLE_DIR = os.path.abspath(os.path.join(HERE, "..", "..", "simulations",
                                            "code"))

MAN = json.load(open(os.path.join(RAW, "manifest.json")))
SRC = {e["id"]: e for e in MAN["files"]}


def p(sid):
    return os.path.join(HERE, SRC[sid]["path"])


def write_csv(name, rows, cols):
    path = os.path.join(DER, name)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="raise")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    return path


# ---------------------------------------------------------------------------
# 1. Text snapshots and verified facts
# ---------------------------------------------------------------------------
DOC_EXT = (".html", ".htm", ".md", ".pdf")
TEXT = {}


def text_of(sid):
    if sid not in TEXT:
        TEXT[sid] = file_to_text(p(sid))
    return TEXT[sid]


def build_doc_text():
    out = os.path.join(DER, "doc_text")
    os.makedirs(out, exist_ok=True)
    n = 0
    for sid, e in sorted(SRC.items()):
        if e["path"].lower().endswith(DOC_EXT):
            with open(os.path.join(out, sid + ".txt"), "w") as f:
                f.write("# source: %s\n# retrieved_utc: %s\n# sha256: %s\n\n"
                        % (e["url"], e["retrieved_utc"], e["sha256"]))
                f.write(text_of(sid))
            n += 1
    return n


F = {}


def build_facts():
    rows, bad = [], []
    for f in FACTS:
        e = SRC[f["src"]]
        ok = norm(f["quote"]) in norm(text_of(f["src"]))
        if not ok:
            bad.append(f["id"])
        rows.append(dict(fact_id=f["id"], source_id=f["src"],
                         source_url=e["url"], retrieved_utc=e["retrieved_utc"],
                         sha256=e["sha256"], quote=f["quote"],
                         value=f["value"], unit=f["unit"], what=f["what"],
                         verified_in_raw=ok))
        F[f["id"]] = f
    write_csv("doc_facts.csv", rows,
              ["fact_id", "source_id", "source_url", "retrieved_utc",
               "sha256", "quote", "value", "unit", "what",
               "verified_in_raw"])
    if bad:
        raise SystemExit("quotes not found in raw sources: %s" % bad)
    return len(rows)


def num_in(fid, s):
    """Assert that a constant used below appears in the verified quote."""
    assert s in F[fid]["quote"], (fid, s)


# ---------------------------------------------------------------------------
# 2. Porkbun prices (ICANN root-zone TLDs only)
# ---------------------------------------------------------------------------
FOCUS_TLDS = ["xyz", "top", "lol", "casa", "shop", "online", "site", "click",
              "icu", "cfd", "sbs", "com"]


def porkbun():
    j = json.load(open(p("porkbun_pricing")))
    assert j["status"] == "SUCCESS"
    iana = set()
    for ln in open(p("iana_tlds")):
        ln = ln.strip()
        if ln and not ln.startswith("#"):
            iana.add(ln.lower())
    rows = []
    for tld, v in j["pricing"].items():
        if v.get("specialType") or "." in tld or tld not in iana:
            continue
        reg = float(v["registration"].replace(",", ""))
        ren = float(v["renewal"].replace(",", ""))
        if reg <= 0 or ren <= 0:      # artefacts (e.g. a $0 entry)
            continue
        rows.append(dict(tld=tld, registration_usd=reg, renewal_usd=ren,
                         transfer_usd=float(v["transfer"].replace(",", "")),
                         renewal_over_registration=round(ren / reg, 2),
                         two_year_cost_usd=round(reg + ren, 2),
                         coupons=len(v.get("coupons") or [])))
    rows.sort(key=lambda r: (r["registration_usd"], r["tld"]))
    for i, r in enumerate(rows, 1):
        r["rank_by_registration"] = i
        r["focus_tld"] = r["tld"] in FOCUS_TLDS
    cols = ["rank_by_registration", "tld", "registration_usd", "renewal_usd",
            "transfer_usd", "renewal_over_registration", "two_year_cost_usd",
            "coupons", "focus_tld"]
    write_csv("porkbun_tld_prices.csv", rows, cols)
    n_all = len(j["pricing"])
    n_hns = sum(1 for v in j["pricing"].values()
                if v.get("specialType") == "handshake")
    regs = [r["registration_usd"] for r in rows]
    rens = [r["renewal_usd"] for r in rows]
    cheapest = min(regs)
    focus = [r for r in rows if r["tld"] in FOCUS_TLDS and r["tld"] != "com"]
    s = dict(
        porkbun_entries_total=n_all, porkbun_handshake_entries=n_hns,
        icann_tlds_priced=len(rows),
        cheapest_first_year_usd=cheapest,
        cheapest_first_year_tlds=" ".join(r["tld"] for r in rows
                                          if r["registration_usd"] == cheapest),
        n_tlds_first_year_lt_2usd=sum(x < 2 for x in regs),
        n_tlds_first_year_lt_5usd=sum(x < 5 for x in regs),
        median_first_year_usd=round(statistics.median(regs), 2),
        median_renewal_usd=round(statistics.median(rens), 2),
        focus_first_year_min_usd=min(r["registration_usd"] for r in focus),
        focus_first_year_max_usd=max(r["registration_usd"] for r in focus),
        focus_renewal_min_usd=min(r["renewal_usd"] for r in focus),
        focus_renewal_max_usd=max(r["renewal_usd"] for r in focus),
        focus_median_renewal_over_registration=round(statistics.median(
            r["renewal_over_registration"] for r in focus), 2),
        com_first_year_usd=next(r["registration_usd"] for r in rows
                                if r["tld"] == "com"),
        retrieved_utc=SRC["porkbun_pricing"]["retrieved_utc"],
        iana_list_version=open(p("iana_tlds")).readline().strip("# \n"),
    )
    write_csv("porkbun_summary.csv",
              [dict(metric=k, value=v) for k, v in s.items()],
              ["metric", "value"])
    return rows, s


# ---------------------------------------------------------------------------
# 3. ICANN monthly registry transaction reports
# ---------------------------------------------------------------------------
ICANN_TLDS = ["xyz", "top", "shop", "online", "cfd"]


def icann():
    recs = []
    for f in sorted(glob.glob(os.path.join(RAW, "icann_mrr", "*", "*.csv"))):
        t, ym = re.search(r"/([a-z]+)-transactions-(\d{6})-en\.csv$",
                          f).groups()
        d = pd.read_csv(f, dtype=str, keep_default_na=False)
        tot = d[d["registrar-name"] == "Totals"]
        assert len(tot) == 1, f
        r = tot.iloc[0]
        body = d[d["registrar-name"] != "Totals"]

        def n(c, r=r):
            v = str(r[c]).strip()
            return int(v) if v else 0
        # consistency: registrar rows sum to the Totals row
        for c in ("net-adds-1-yr", "deleted-domains-nograce",
                  "net-renews-1-yr"):
            assert int(pd.to_numeric(body[c], errors="coerce").fillna(0)
                       .sum()) == n(c), (f, c)
        recs.append(dict(
            tld=t, month="%s-%s" % (ym[:4], ym[4:]),
            registrars=len(body),
            total_domains=n("total-domains"),
            net_adds_all_terms=sum(n("net-adds-%d-yr" % k)
                                   for k in range(1, 11)),
            net_adds_1yr=n("net-adds-1-yr"),
            net_renews_all_terms=sum(n("net-renews-%d-yr" % k)
                                     for k in range(1, 11)),
            net_renews_1yr=n("net-renews-1-yr"),
            transfer_gaining_successful=n("transfer-gaining-successful"),
            deleted_domains_grace=n("deleted-domains-grace"),
            deleted_domains_nograce=n("deleted-domains-nograce"),
            restored_domains=n("restored-domains"),
            attempted_adds=n("attempted-adds"),
            source_file=os.path.relpath(f, HERE)))
    df = pd.DataFrame(recs).sort_values(["tld", "month"])
    df.to_csv(os.path.join(DER, "icann_mrr_monthly.csv"), index=False)

    def window(t, a, b):
        x = df[(df.tld == t) & (df.month >= a) & (df.month <= b)]
        return x
    out = []
    for t in ICANN_TLDS:
        y1 = window(t, "2024-07", "2025-06")
        y2 = window(t, "2025-07", "2026-06")
        assert len(y1) == 12 and len(y2) == 12, t
        # 13-month shift with 11-month windows (auto-renew grace can push a
        # renewal into the month after expiry)
        y1b = window(t, "2024-07", "2025-05")
        y2b = window(t, "2025-08", "2026-06")
        kept2 = (y2.net_renews_all_terms.sum() +
                 y2.transfer_gaining_successful.sum() +
                 y2.restored_domains.sum())
        kept2b = (y2b.net_renews_all_terms.sum() +
                  y2b.transfer_gaining_successful.sum() +
                  y2b.restored_domains.sum())
        ub12 = kept2 / y1.net_adds_1yr.sum()
        ub13 = kept2b / y1b.net_adds_1yr.sum()
        dum_mean = y2.total_domains.mean()
        out.append(dict(
            tld=t,
            window="2025-07..2026-06",
            dum_2025_06=int(y1[y1.month == "2025-06"].total_domains.iloc[0]),
            dum_2026_06=int(y2[y2.month == "2026-06"].total_domains.iloc[0]),
            dum_mean=int(round(dum_mean)),
            net_adds_all_terms=int(y2.net_adds_all_terms.sum()),
            net_adds_1yr=int(y2.net_adds_1yr.sum()),
            share_adds_1yr=round(y2.net_adds_1yr.sum() /
                                 y2.net_adds_all_terms.sum(), 4),
            deleted_nograce=int(y2.deleted_domains_nograce.sum()),
            deleted_grace=int(y2.deleted_domains_grace.sum()),
            net_renews_all_terms=int(y2.net_renews_all_terms.sum()),
            transfers_in=int(y2.transfer_gaining_successful.sum()),
            restored=int(y2.restored_domains.sum()),
            adds_per_day=round(y2.net_adds_all_terms.sum() / 365.0, 0),
            deletions_per_year_over_mean_dum=round(
                y2.deleted_domains_nograce.sum() / dum_mean, 3),
            adds_per_year_over_mean_dum=round(
                y2.net_adds_all_terms.sum() / dum_mean, 3),
            prior_year_net_adds_1yr=int(y1.net_adds_1yr.sum()),
            kept_over_prior_1yr_adds_shift12=round(ub12, 3),
            kept_over_prior_1yr_adds_shift13=round(ub13, 3),
            first_year_renewal_upper_bound=round(max(ub12, ub13), 3)))
    cols = list(out[0].keys())
    write_csv("icann_disposability.csv", out, cols)
    return df, out


# ---------------------------------------------------------------------------
# 4. Public Suffix List
# ---------------------------------------------------------------------------
def load_psl():
    rules, section, header = {}, None, None
    version = commit = ""
    for i, ln in enumerate(open(p("psl_canonical"), encoding="utf-8"), 1):
        s = ln.strip()
        if s.startswith("// VERSION:"):
            version = s.split(":", 1)[1].strip()
        if s.startswith("// COMMIT:"):
            commit = s.split(":", 1)[1].strip()
        if "===BEGIN ICANN DOMAINS===" in s:
            section = "ICANN"
        elif "===BEGIN PRIVATE DOMAINS===" in s:
            section = "PRIVATE"
        elif "===END" in s:
            section = None
        if not s:
            header = None
            continue
        if s.startswith("//"):
            # first comment line of a block names the operator; skip the
            # 'Submitted by' lines, which carry personal contact details
            if header is None and "submitted by" not in s.lower():
                header = s[2:].strip()
            continue
        if section:
            rules[s.split()[0].lower()] = dict(section=section, line=i,
                                               org=header or "")
    return rules, version, commit


def psl_lookup(rules, host):
    """Return (public_suffix, registered_domain, rule, info) per the PSL
    algorithm (exception rules, wildcards, longest match)."""
    labels = host.lower().split(".")
    best = None
    for k in range(len(labels)):
        cand = ".".join(labels[k:])
        wild = "*." + ".".join(labels[k + 1:]) if k + 1 < len(labels) else None
        if "!" + cand in rules:
            ps = ".".join(labels[k + 1:])
            return ps, cand, "!" + cand, rules["!" + cand]
        for r in (cand, wild):
            if r and r in rules:
                n = len(labels) - k
                if best is None or n > best[0]:
                    best = (n, cand, r)
    if best is None:
        return labels[-1], ".".join(labels[-2:]), "*", {}
    n, ps, r = best
    rd = ".".join(labels[-(n + 1):]) if len(labels) > n else ""
    return ps, rd, r, rules[r]


# Synthetic placeholder labels only (tenant, acct, ...); nothing is resolved.
PLATFORMS = [
    # platform, example host pattern, synthetic example host
    ("GitHub Pages", "<owner>.github.io", "tenant.github.io"),
    ("Cloudflare Workers", "<worker>.<account>.workers.dev",
     "worker.acct.workers.dev"),
    ("Cloudflare Pages", "<project>.pages.dev", "proj.pages.dev"),
    ("Cloudflare Pages (preview)", "<hash>.<project>.pages.dev",
     "hash.proj.pages.dev"),
    ("Vercel", "<project>-<hash>-<scope>.vercel.app",
     "proj-hash-scope.vercel.app"),
    ("Netlify", "<site>.netlify.app", "site.netlify.app"),
    ("Firebase Hosting", "<site>.web.app", "site.web.app"),
    ("Firebase Hosting (alt)", "<site>.firebaseapp.com",
     "site.firebaseapp.com"),
    ("Deno Deploy", "<app>.<org>.deno.net", "app.org.deno.net"),
    ("Deno Deploy Classic", "<project>.deno.dev", "proj.deno.dev"),
    ("Fly.io", "<app>.fly.dev", "app.fly.dev"),
    ("Render", "<service>.onrender.com", "svc.onrender.com"),
    ("AWS Lambda function URL", "<url-id>.lambda-url.<region>.on.aws",
     "urlid.lambda-url.us-east-1.on.aws"),
    ("Azure App Service", "<app>.azurewebsites.net", "app.azurewebsites.net"),
    ("Azure App Service (unique)",
     "<app>-<hash>.<region>.azurewebsites.net",
     "app-hash.eastus-01.azurewebsites.net"),
    ("Google Cloud Run", "<service>-<project-number>.<region>.run.app",
     "svc-123.us-central1.run.app"),
    ("Google Cloud Run (hash URL)", "<service-id>.a.run.app",
     "svcid.a.run.app"),
]


def psl_table():
    rules, version, commit = load_psl()
    rows = []
    for plat, pattern, host in PLATFORMS:
        ps, rd, rule, info = psl_lookup(rules, host)
        rows.append(dict(platform=plat, host_pattern=pattern,
                         synthetic_example=host, matched_rule=rule,
                         psl_section=info.get("section", ""),
                         psl_line=info.get("line", ""),
                         psl_org_header=info.get("org", ""),
                         public_suffix=ps, registered_domain=rd,
                         tenant_is_own_registered_domain=(
                             info.get("section") == "PRIVATE"),
                         psl_version=version, psl_commit=commit))
    write_csv("psl_platform_suffixes.csv", rows, list(rows[0].keys()))
    return rows, version, commit


# ---------------------------------------------------------------------------
# 5. CT log list, crt.sh lookups, Scheitle et al. Table 4
# ---------------------------------------------------------------------------
def ct_logs():
    j = json.load(open(p("chrome_log_list")))
    rows = []
    for op in j["operators"]:
        for kind, key in (("rfc6962", "logs"), ("static-ct-api",
                                                "tiled_logs")):
            for lg in op.get(key, []) or []:
                st = list((lg.get("state") or {"unknown": {}}).keys())[0]
                ti = lg.get("temporal_interval") or {}
                rows.append(dict(operator=op["name"],
                                 description=lg.get("description", ""),
                                 api=kind, mmd_s=lg.get("mmd"), state=st,
                                 interval_start=ti.get("start_inclusive", ""),
                                 interval_end=ti.get("end_exclusive", "")))
    write_csv("ct_log_list_summary.csv", rows, list(rows[0].keys()))
    live = [r for r in rows if r["state"] in ("usable", "qualified")]
    s = dict(log_list_version=j.get("version"),
             log_list_timestamp=j.get("log_list_timestamp"),
             n_logs_usable_or_qualified=len(live),
             n_static_usable_or_qualified=sum(r["api"] == "static-ct-api"
                                              for r in live),
             n_rfc6962_usable_or_qualified=sum(r["api"] == "rfc6962"
                                               for r in live),
             mmd_values_static=sorted({r["mmd_s"] for r in live
                                       if r["api"] == "static-ct-api"}),
             mmd_values_rfc6962=sorted({r["mmd_s"] for r in live
                                        if r["api"] == "rfc6962"}),
             operators_with_static_usable=sorted({
                 r["operator"] for r in live
                 if r["api"] == "static-ct-api" and r["state"] == "usable"}),
             n_operators_usable=len({r["operator"] for r in live
                                     if r["state"] == "usable"}))
    return rows, s


def crtsh():
    rows = []
    for sid in sorted(k for k in SRC if k.startswith("crtsh_")):
        e = SRC[sid]
        ident = re.search(r"q=([^&]+)", e["url"]).group(1).replace("%2A", "*")
        data = json.load(open(p(sid)))
        for c in data:
            rows.append(dict(identity_queried=ident, crtsh_id=c["id"],
                             issuer_name=c["issuer_name"],
                             common_name=c["common_name"],
                             name_value=c["name_value"].replace("\n", " "),
                             not_before=c["not_before"],
                             not_after=c["not_after"],
                             retrieved_utc=e["retrieved_utc"]))
    write_csv("crtsh_platform_wildcards.csv", rows,
              ["identity_queried", "crtsh_id", "issuer_name", "common_name",
               "name_value", "not_before", "not_after", "retrieved_utc"])
    by = {}
    for r in rows:
        by.setdefault(r["identity_queried"], []).append(r)
    return rows, by


def scheitle_table4():
    txt = file_to_text(p("arxiv_scheitle2018"), layout=True)
    pat = re.compile(r"^\s*([A-K])\s+(\d\d-\d\d) (\d\d:\d\d:\d\d)\s+"
                     r"(\d\d:\d\d:\d\d)\s+(\d+)s\s+(\d+)\s+(\d+)\s+(\d+)\s+.*?"
                     r"(\d\d-\d\d) (\d\d:\d\d:\d\d)\s+(\d+)([md])\s")
    rows = []
    for ln in txt.splitlines():
        m = pat.match(ln)
        if not m:
            continue
        (lab, d0, t0, t1, dt, q, nas, cs, d2, t2, h, unit) = m.groups()
        hh = [int(x) for x in t0.split(":")]
        gg = [int(x) for x in t1.split(":")]
        diff = (gg[0] * 3600 + gg[1] * 60 + gg[2]) - \
            (hh[0] * 3600 + hh[1] * 60 + hh[2])
        rows.append(dict(subdomain=lab, ct_log_entry="2018-%s %s" % (d0, t0),
                         first_dns_query_time=t1, dns_delay_s=int(dt),
                         dns_delay_recomputed_s=diff,
                         dns_queries=int(q), querying_ases=int(nas),
                         first_https="2018-%s %s" % (d2, t2),
                         https_delay_min=int(h) * (1440 if unit == "d" else 1),
                         https_delay_reported="%s%s" % (h, unit)))
    assert len(rows) == 11, len(rows)
    # In a few rows, the Delta-t column of Scheitle et al. disagrees with
    # their timestamps; keep both and report statistics for each.
    for r in rows:
        r["delta_matches_timestamps"] = (r["dns_delay_s"] ==
                                         r["dns_delay_recomputed_s"])
    write_csv("scheitle2018_table4.csv", rows, list(rows[0].keys()))
    d = [r["dns_delay_s"] for r in rows]
    d2 = [r["dns_delay_recomputed_s"] for r in rows]
    h = [r["https_delay_min"] for r in rows]
    return rows, dict(n=len(rows), dns_min_s=min(d), dns_median_s=
                      statistics.median(d), dns_max_s=max(d),
                      dns_recomputed_min_s=min(d2),
                      dns_recomputed_median_s=statistics.median(d2),
                      dns_recomputed_max_s=max(d2),
                      rows_delta_mismatch=[r["subdomain"] for r in rows
                                           if not r["delta_matches_timestamps"]],
                      https_min_min=min(h), https_median_min=
                      statistics.median(h), https_max_min=max(h))


# ---------------------------------------------------------------------------
# 6. Issuance and registration ceilings implied by documented limits
# ---------------------------------------------------------------------------
DAY = 86400.0


def acme_rates(pb):
    num_in("le_orders_per_account", "300")
    num_in("le_orders_per_account", "36 seconds")
    num_in("le_certs_per_regdomain", "50")
    num_in("le_certs_per_regdomain_refill", "202 minutes")
    num_in("le_accounts_per_ipv4", "18 minutes")
    num_in("le_accounts_per_ipv6_48", "500")
    num_in("le_neworder_per_ip", "300")
    num_in("le_classic_100names", "100")
    num_in("le_tlsserver_25names", "25")
    num_in("gts_neworder", "100 per hour")
    num_in("gts_newauthz", "300 per hour")
    num_in("gts_newaccount", "100 per hour")
    num_in("pb_success_limit", "1000")
    num_in("pb_attempt_limit", "1 attempt per second")
    num_in("pb_spend_default", "$100")
    le_orders_day = DAY / 36
    le_regdom_day = DAY / (202 * 60)
    rows = [
        dict(issuer="Let's Encrypt", scope="per ACME account",
             limit="new orders: 300 per 3 h, refill 1 per 36 s",
             sustained_per_day=round(le_orders_day), burst=300,
             names_per_day_if_one_name_per_cert=round(le_orders_day),
             names_per_day_max_sans=round(le_orders_day * 100),
             note="One name per order keeps names unlinked in CT; up to "
                  "100 names per order (classic) or 25 (tlsserver, "
                  "shortlived) puts them on one CT-logged certificate.",
             facts="le_orders_per_account;le_identifiers_per_cert;"
                   "le_classic_100names;le_tlsserver_25names"),
        dict(issuer="Let's Encrypt", scope="per registered domain (PSL "
             "eTLD+1, all accounts)",
             limit="50 certificates per 7 days, refill 1 per 202 min",
             sustained_per_day=round(le_regdom_day, 2), burst=50,
             names_per_day_if_one_name_per_cert=round(le_regdom_day, 2),
             names_per_day_max_sans="",
             note="Binds only when many per-name certificates are issued "
                  "under ONE registrable domain; a fresh registrable domain "
                  "(or a PSL-private platform tenant) has its own bucket; a "
                  "single wildcard certificate covers unlimited labels.",
             facts="le_certs_per_regdomain;le_certs_per_regdomain_refill;"
                   "le_uses_psl;boulder_psl_domain;pslgo_private_included"),
        dict(issuer="Let's Encrypt", scope="per IPv4 address",
             limit="new accounts: 10 per 3 h, refill 1 per 18 min",
             sustained_per_day=round(DAY / (18 * 60)), burst=10,
             names_per_day_if_one_name_per_cert="",
             names_per_day_max_sans="",
             note="Accounts persist, so each new account adds 2,400 orders "
                  "per day of capacity; per-IP order submission is capped "
                  "only by the load-balancer limit below.",
             facts="le_accounts_per_ipv4"),
        dict(issuer="Let's Encrypt", scope="per IPv6 /48",
             limit="new accounts: 500 per 3 h",
             sustained_per_day=round(500 * 8), burst=500,
             names_per_day_if_one_name_per_cert="",
             names_per_day_max_sans="", note="",
             facts="le_accounts_per_ipv6_48"),
        dict(issuer="Let's Encrypt", scope="per IP (load balancer)",
             limit="/acme/new-order: 300 requests per second, burst 200",
             sustained_per_day=int(300 * DAY), burst=200,
             names_per_day_if_one_name_per_cert="",
             names_per_day_max_sans="",
             note="Request-rate ceiling; not a practical constraint.",
             facts="le_neworder_per_ip"),
        dict(issuer="Let's Encrypt", scope="renewals",
             limit="ARI renewals exempt from all rate limits",
             sustained_per_day="unlimited", burst="",
             names_per_day_if_one_name_per_cert="",
             names_per_day_max_sans="",
             note="Keeping K live names on 160-hour certificates costs no "
                  "rate-limit capacity.",
             facts="le_ari_exempt;le_renewals_exempt"),
        dict(issuer="Google Trust Services (Certificate Manager Public CA)",
             scope="per Google Cloud project (shared by its ACME accounts)",
             limit="newOrder 100 per hour; newAuthz 300 per hour",
             sustained_per_day=100 * 24, burst="",
             names_per_day_if_one_name_per_cert=100 * 24,
             names_per_day_max_sans=300 * 24,
             note="Authorizations (one per name) cap multi-name orders at "
                  "7,200 names per day per project; EAB binding to a "
                  "project is required.",
             facts="gts_neworder;gts_newauthz;gts_per_project;gts_eab"),
        dict(issuer="ZeroSSL", scope="per user",
             limit="'unlimited amount of 90-day SSL certificates'; EAB "
                   "credentials capped per user per day (value unpublished)",
             sustained_per_day="unpublished", burst="",
             names_per_day_if_one_name_per_cert="unpublished",
             names_per_day_max_sans="", note="Abusive users can be limited "
             "or blocked.", facts="zerossl_unlimited;zerossl_eab_cap;"
             "zerossl_abuse"),
        dict(issuer="Porkbun (registrar API)", scope="per account",
             limit="1 attempt per second; 1000 successful registrations "
                   "per 86400 s (defaults, configurable)",
             sustained_per_day=1000, burst="",
             names_per_day_if_one_name_per_cert=1000,
             names_per_day_max_sans="",
             note="Default monthly API spend cap of $100 allows %d names "
                  "per month at the cheapest first-year price ($%.2f) until "
                  "the account holder raises it; email and phone "
                  "verification and prepaid credit are required."
                  % (int(100 // pb["cheapest_first_year_usd"]),
                     pb["cheapest_first_year_usd"]),
             facts="pb_attempt_limit;pb_success_limit;pb_spend_default;"
                   "pb_verify;pb_min_duration"),
    ]
    write_csv("acme_mint_rates.csv", rows,
              ["issuer", "scope", "limit", "sustained_per_day", "burst",
               "names_per_day_if_one_name_per_cert", "names_per_day_max_sans",
               "note", "facts"])
    return rows, dict(le_orders_per_account_per_day=round(le_orders_day),
                      le_certs_per_regdomain_per_day=round(le_regdom_day, 2),
                      le_new_accounts_per_ipv4_per_day=round(DAY / 1080),
                      gts_orders_per_project_per_day=2400,
                      gts_authz_per_project_per_day=7200,
                      porkbun_registrations_per_day_default=1000)


# ---------------------------------------------------------------------------
# 7. Platform names: limits and CT exposure of tenant names
# ---------------------------------------------------------------------------
def platform_table(psl_rows, crt_by):
    def crt_note(ident):
        rs = crt_by.get(ident, [])
        if not rs:
            return ""
        iss = sorted({re.sub(r".*O=([^,]+).*", r"\1", r["issuer_name"])
                      for r in rs})
        nb = min(r["not_before"] for r in rs)[:10]
        na = max(r["not_after"] for r in rs)[:10]
        return "crt.sh: unexpired %s certificate(s) for %s, %s to %s" % (
            "/".join(iss), ident, nb, na)
    reg = {r["platform"]: r for r in psl_rows}
    T = [
        dict(platform="GitHub Pages", default_name="<owner>.github.io",
             psl=reg["GitHub Pages"],
             names_per_account="1 hostname per account (project sites are "
             "paths under it)", account_terms="one free account per person; "
             "no bot-registered accounts; free plan needs a public repo",
             cert_evidence=crt_note("*.github.io") + "; docs: github.io "
             "sites served over HTTPS automatically",
             ct_exposure_at_mint="not via CT (a *.github.io wildcard "
             "exists), but the owner name is published by the public event "
             "for the (public) repository, 30 s to 6 h after creation",
             facts="gh_one_site;gh_default_location;gh_tos_one_free;"
             "gh_tos_no_bots;gh_free_public_only;gh_https_auto;"
             "gh_createevent_repo;gh_event_repo_name;gh_events_latency"),
        dict(platform="Cloudflare Workers",
             default_name="<worker>.<account>.workers.dev",
             psl=reg["Cloudflare Workers"],
             names_per_account="100 Workers (Free), 500 (Paid); one "
             "<account>.workers.dev subdomain",
             account_terms="Cloudflare account; Free plan",
             cert_evidence="not documented; crt.sh not queried (two-level "
             "names need a certificate naming at least the account label)",
             ct_exposure_at_mint="account label: yes if a publicly trusted "
             "certificate names *.<account>.workers.dev (inferred: a "
             "*.workers.dev wildcard cannot cover two labels); worker "
             "labels: not needed",
             facts="cf_workers_per_account;cf_workers_dev_format;"
             "cf_worker_route_format;rfc9525_one_label;chrome_ct_required"),
        dict(platform="Cloudflare Pages", default_name="<project>.pages.dev; "
             "previews <hash>.<project>.pages.dev",
             psl=reg["Cloudflare Pages"],
             names_per_account="100 projects per account (not routinely "
             "raised); unlimited preview deployments",
             account_terms="Free plan; new accounts throttled in first 48 h",
             cert_evidence="crt.sh lookup for *.pages.dev failed (HTTP 502 "
             "twice); not documented",
             ct_exposure_at_mint="project label: yes if previews are served "
             "under a publicly trusted *.<project>.pages.dev (inferred)",
             facts="cf_pages_100_projects;cf_pages_48h;cf_pages_free_plan;"
             "cf_pages_preview_format;cf_pages_unlimited_previews;"
             "rfc9525_one_label"),
        dict(platform="Vercel", default_name="<project>-<hash>-<scope>."
             "vercel.app", psl=reg["Vercel"],
             names_per_account="200 projects, 100 deployments per day "
             "(Hobby); each Git-commit deployment gets a new hostname with "
             "a random 9-character hash",
             account_terms="Free (Hobby) plan",
             cert_evidence="crt.sh lookup for *.vercel.app failed (HTTP 504 "
             "twice); not documented",
             ct_exposure_at_mint="unknown from documentation (single-label "
             "names could be covered by one wildcard)",
             facts="vercel_projects;vercel_deploys_day;vercel_free_deploys;"
             "vercel_url_format;vercel_hash_9"),
        dict(platform="Netlify", default_name="<site>.netlify.app",
             psl=reg["Netlify"], names_per_account="not stated in the "
             "fetched pages", account_terms="certificates free; plan "
             "prices not checked",
             cert_evidence=crt_note("*.netlify.app") + "; docs: new sites "
             "'instantly secured' at the netlify.app URL",
             ct_exposure_at_mint="tenant name not needed in CT (wildcard "
             "exists)", facts="netlify_instant;netlify_custom_le;"
             "netlify_free_certs"),
        dict(platform="Firebase Hosting", default_name="<site>.web.app, "
             "<site>.firebaseapp.com", psl=reg["Firebase Hosting"],
             names_per_account="36 sites per Firebase project",
             account_terms="no-cost tier (10 GB storage)",
             cert_evidence=crt_note("*.web.app"),
             ct_exposure_at_mint="tenant name not needed in CT for web.app "
             "(wildcard exists)", facts="firebase_36_sites;firebase_no_cost;"
             "firebase_default_domains;firebase_preview_format"),
        dict(platform="Deno Deploy", default_name="<app>.<org>.deno.net",
             psl=reg["Deno Deploy"], names_per_account="10 active apps per "
             "organization (Free)", account_terms="Free plan $0/month",
             cert_evidence="not documented; crt.sh not queried",
             ct_exposure_at_mint="org label: yes if a publicly trusted "
             "*.<org>.deno.net certificate is used (inferred)",
             facts="deno_org_domain;deno_app_two_level;deno_free_plan;"
             "deno_free_10_apps;rfc9525_one_label"),
        dict(platform="Fly.io", default_name="<app>.fly.dev",
             psl=reg["Fly.io"], names_per_account="not stated",
             account_terms="no free tier; credit card on file",
             cert_evidence="not documented; crt.sh not queried",
             ct_exposure_at_mint="unknown from documentation",
             facts="fly_default;fly_no_free_tier;fly_card"),
        dict(platform="Render", default_name="<service>.onrender.com",
             psl=reg["Render"], names_per_account="not stated (750 free "
             "instance hours per workspace per month)",
             account_terms="free web services",
             cert_evidence="docs: free TLS certificates for the onrender.com "
             "subdomain (wildcard or per-service not stated)",
             ct_exposure_at_mint="unknown from documentation",
             facts="render_subdomain;render_tls;render_750h;"
             "render_free_services"),
        dict(platform="AWS Lambda function URL",
             default_name="<url-id>.lambda-url.<region>.on.aws",
             psl=reg["AWS Lambda function URL"],
             names_per_account="no per-account count documented (storage "
             "and concurrency quotas only)", account_terms="AWS account",
             cert_evidence="not documented; crt.sh not queried",
             ct_exposure_at_mint="unknown from documentation",
             facts="aws_url_format"),
        dict(platform="Azure App Service",
             default_name="<app>-<hash>.<region>.azurewebsites.net",
             psl=reg["Azure App Service (unique)"],
             names_per_account="Free tier: 10 apps per App Service plan",
             account_terms="Azure subscription; Free tier",
             cert_evidence="not documented; crt.sh not queried",
             ct_exposure_at_mint="unknown from documentation",
             facts="azure_unique_format;azure_noreuse;azure_free_10_apps"),
        dict(platform="Google Cloud Run",
             default_name="<service>-<project-number>.<region>.run.app",
             psl=reg["Google Cloud Run"],
             names_per_account="1,000 services per project and region",
             account_terms="Google Cloud project",
             cert_evidence="not documented; crt.sh not queried",
             ct_exposure_at_mint="unknown from documentation",
             facts="gcr_deterministic_format;gcr_1000_services"),
    ]
    rows = []
    for t in T:
        ps = t.pop("psl")
        t.update(psl_rule=ps["matched_rule"], psl_section=ps["psl_section"],
                 tenant_registered_domain_example=ps["registered_domain"],
                 tenant_is_own_registered_domain=ps[
                     "tenant_is_own_registered_domain"])
        rows.append(t)
    cols = ["platform", "default_name", "psl_rule", "psl_section",
            "tenant_registered_domain_example",
            "tenant_is_own_registered_domain", "names_per_account",
            "account_terms", "cert_evidence", "ct_exposure_at_mint", "facts"]
    write_csv("platform_names.csv", rows, cols)
    return rows


# ---------------------------------------------------------------------------
# 8. Cost per name by unit type
# ---------------------------------------------------------------------------
def minting_costs(prices, pb, rates):
    focus = {r["tld"]: r for r in prices}
    rows = []
    for t in FOCUS_TLDS:
        if t not in focus:
            continue
        r = focus[t]
        rows.append(dict(
            unit_type="registrable domain (eTLD+1)", variant="." + t,
            first_year_usd=r["registration_usd"],
            renewal_usd=r["renewal_usd"],
            marginal_cost_per_name_usd=r["registration_usd"],
            certificate_cost_usd=0.0,
            mint_rate_ceiling="registrar: 1000/day/account (Porkbun default); "
            "CA: 2400 single-name orders/day/account (LE)",
            exposed_at_mint="yes: gTLD zone file (daily) and new-domain "
            "lists (next day); CT at issuance if it gets a publicly trusted "
            "certificate (static logs before the SCT is returned, RFC 6962 "
            "logs within 24 h)", censor_burn_unit="applies when the censor "
            "burns registrable domains (all sub-domains then share fate)",
            source="porkbun_pricing; facts pb_success_limit, "
            "le_orders_per_account, zfa_daily, ra_icann_daily, "
            "whoisds_next_day, chrome_ct_required, le_logs_everything, "
            "static_null_mmd, rfc6962_mmd"))
    rows.append(dict(
        unit_type="registrable domain (eTLD+1)",
        variant="cheapest ICANN TLD at Porkbun (%s)"
        % pb["cheapest_first_year_tlds"],
        first_year_usd=pb["cheapest_first_year_usd"], renewal_usd="",
        marginal_cost_per_name_usd=pb["cheapest_first_year_usd"],
        certificate_cost_usd=0.0, mint_rate_ceiling="as above",
        exposed_at_mint="as above", censor_burn_unit="registrable domain",
        source="porkbun_tld_prices.csv"))
    rows.append(dict(
        unit_type="registrable domain (eTLD+1)",
        variant="median ICANN TLD at Porkbun (n=%d)" % pb["icann_tlds_priced"],
        first_year_usd=pb["median_first_year_usd"],
        renewal_usd=pb["median_renewal_usd"],
        marginal_cost_per_name_usd=pb["median_first_year_usd"],
        certificate_cost_usd=0.0, mint_rate_ceiling="as above",
        exposed_at_mint="as above", censor_burn_unit="registrable domain",
        source="porkbun_tld_prices.csv"))
    rows += [
        dict(unit_type="sub-domain label under an owned domain",
             variant="per-label public certificate (HTTP-01 or DNS-01)",
             first_year_usd="", renewal_usd="",
             marginal_cost_per_name_usd=0.0, certificate_cost_usd=0.0,
             mint_rate_ceiling="LE: %.2f new certificates/day per registered "
             "domain sustained (50 per 7 days, burst 50); more parent "
             "domains or accounts scale it" % rates[
                 "le_certs_per_regdomain_per_day"],
             exposed_at_mint="yes: each label appears in CT at issuance",
             censor_burn_unit="the label (exact FQDN) or the parent domain, "
             "whichever the censor blocks",
             source="facts le_certs_per_regdomain, chrome_ct_required, "
             "le_logs_everything"),
        dict(unit_type="sub-domain label under an owned domain",
             variant="one wildcard public certificate (DNS-01)",
             first_year_usd="", renewal_usd="",
             marginal_cost_per_name_usd=0.0, certificate_cost_usd=0.0,
             mint_rate_ceiling="no CA limit per label (one certificate "
             "covers every label one level down)",
             exposed_at_mint="parent only: CT shows *.<parent>; labels are "
             "not logged", censor_burn_unit="label if the censor blocks "
             "exact FQDNs; otherwise the parent domain (one unit)",
             source="facts le_dns01_wildcard, rfc9525_one_label"),
        dict(unit_type="private name with pinned certificate",
             variant="label under an owned domain, private CA or self-signed "
             "certificate pinned in the client (e.g. WebTunnel non-WebPKI "
             "mode)", first_year_usd="", renewal_usd="",
             marginal_cost_per_name_usd=0.0, certificate_cost_usd=0.0,
             mint_rate_ceiling="none from CAs; registrar limits apply only "
             "to the parent domain",
             exposed_at_mint="no mint-time channel (not publicly trusted, so "
             "not CT-logged; labels are not in zone files or NRD lists); "
             "exposed at first use (DNS/SNI on path)",
             censor_burn_unit="label if the censor blocks exact FQDNs; "
             "otherwise the parent domain (one unit)",
             source="facts chrome_ct_required, apple_ct_required, "
             "tor_nonwebpki_pinning, zfa_active_names, gfwatch_sld_only"),
        dict(unit_type="platform tenant sub-domain (PSL private suffix)",
             variant="documented free plans: github.io (GitHub Free), "
             "workers.dev and pages.dev (Cloudflare Free), vercel.app "
             "(Free/Hobby), web.app (no-cost tier), deno.net (Free), "
             "onrender.com (Free instances), azurewebsites.net (Free tier); "
             "fly.dev has no free tier; free allowances of on.aws and "
             "run.app not checked",
             first_year_usd="", renewal_usd="",
             marginal_cost_per_name_usd=0.0, certificate_cost_usd=0.0,
             mint_rate_ceiling="per-account quotas (platform_names.csv), "
             "e.g. 1 github.io host per account, 100 Pages projects, 100 "
             "Workers (Free), 200 Vercel projects and 100 deployments/day "
             "(Hobby), 36 Firebase sites per project",
             exposed_at_mint="not via CT when a platform wildcard covers "
             "the name (github.io, netlify.app, web.app); account/project "
             "labels of two-level schemes likely via CT; platform metadata "
             "(e.g. GitHub public events)", censor_burn_unit="tenant name, "
             "or the whole platform suffix if the censor accepts the "
             "collateral", source="platform_names.csv; facts "
             "gh_free_public_only, cf_pages_free_plan, vercel_free_deploys, "
             "firebase_no_cost, deno_free_plan, render_free_services, "
             "azure_free_10_apps, fly_no_free_tier"),
        dict(unit_type="IP address with publicly trusted certificate",
             variant="LE shortlived profile (160 h), IP identifier",
             first_year_usd="", renewal_usd="",
             marginal_cost_per_name_usd="not computed (cost of the address)",
             certificate_cost_usd=0.0,
             mint_rate_ceiling="LE: 50 certificates per IPv4 address (or "
             "IPv6 /64) per 7 days", exposed_at_mint="yes: the IP address "
             "itself is CT-logged at issuance", censor_burn_unit="the IP "
             "address", source="facts le_6day_ga, le_ip_must_be_short, "
             "le_shortlived_ip, le_certs_per_regdomain"),
    ]
    cols = ["unit_type", "variant", "first_year_usd", "renewal_usd",
            "marginal_cost_per_name_usd", "certificate_cost_usd",
            "mint_rate_ceiling", "exposed_at_mint", "censor_burn_unit",
            "source"]
    write_csv("minting_costs.csv", rows, cols)
    return rows


# ---------------------------------------------------------------------------
# 9. Exposure channels and their delays
# ---------------------------------------------------------------------------
def exposure_channels(ct, sch):
    H = 3600
    rows = [
        dict(channel="CT log, static-ct-api (e.g. Let's Encrypt Sycamore, "
             "Willow)", exposes="every DNS name and IP in a publicly trusted "
             "(pre)certificate", trigger="issuance (precertificate logged "
             "before the certificate is issued)", delay_min_s=0,
             delay_max_s=60, delay_basis="entries sequenced before the SCT "
             "is returned (null merge delay); Chrome caps MMD at 60 s; all "
             "%d usable/qualified static logs list MMD %s s"
             % (ct["n_static_usable_or_qualified"],
                "/".join(str(x) for x in ct["mmd_values_static"])),
             access="public, no account", applies_to="registrable domains, "
             "FQDN labels with their own certificate, IP certificates",
             facts="static_null_mmd;le_sunlight_zero_mmd;chrome_mmd_caps;"
             "le_logs_everything;rfc6962_precert;chrome_embed_scts;"
             "le_embeds_scts;chrome_ct_required;apple_ct_required"),
        dict(channel="CT log, RFC 6962", exposes="as above",
             trigger="issuance", delay_min_s=0, delay_max_s=24 * H,
             delay_basis="log MMD; all %d usable/qualified RFC 6962 logs in "
             "Chrome's list v%s specify %s s; new RFC 6962 applicants are "
             "capped at 4 h" % (ct["n_rfc6962_usable_or_qualified"],
                                 ct["log_list_version"],
                                 "/".join(str(x) for x in
                                          ct["mmd_values_rfc6962"])),
             access="public, no account", applies_to="as above",
             facts="rfc6962_mmd;rfc9162_mmd_no_limit;chrome_incorporate_mmd;"
             "chrome_mmd_caps"),
        dict(channel="CT monitors acting on new names (observed, 2018)",
             exposes="names from new CT entries", trigger="CT entry",
             delay_min_s=sch["dns_min_s"], delay_max_s=sch["dns_max_s"],
             delay_basis="first DNS lookups of 11 honeypot names %d-%d s "
             "(median %d s) after the CT entry; first HTTP(S) connections "
             "%d min to %d days later" % (
                 sch["dns_min_s"], sch["dns_max_s"], sch["dns_median_s"],
                 sch["https_min_min"], sch["https_max_min"] // 1440),
             access="any CT monitor", applies_to="names with public certs",
             facts="scheitle_dns_73s_3min;scheitle_11_names"),
        dict(channel="CT-derived newly-registered-domain stream (OpenINTEL "
             "Zonestream)", exposes="registrable domains first seen in CT",
             trigger="CT entry", delay_min_s="", delay_max_s="",
             delay_basis="described as real-time; no bound documented",
             access="public, under OpenINTEL's data terms",
             applies_to="registrable "
             "domains with public certificates",
             facts="zonestream_ct_nrd"),
        dict(channel="gTLD zone file (ICANN CZDS)", exposes="registrable "
             "domains active in the gTLD", trigger="registration",
             delay_min_s=0, delay_max_s=48 * H,
             delay_basis="daily snapshot as close as possible to 00:00 UTC "
             "(<= 24 h wait) plus one download per 24 h (<= 24 h)",
             access="signed zone-file access agreement via CZDS (registry "
             "may deny or revoke)", applies_to="registrable domains in gTLDs "
             "(zone files list second-level names, not sub-domain labels)",
             facts="ra_icann_daily;ra_once_per_24h;zfa_daily;"
             "zfa_active_names;zfa_agreement;zfa_deny;gfwatch_daily_zones;"
             "gfwatch_sld_only"),
        dict(channel="Daily newly-registered-domain list (e.g. WhoisDS)",
             exposes="registrable domains registered on day D",
             trigger="registration", delay_min_s=0, delay_max_s=48 * H,
             delay_basis="list for day D is created on day D+1 (free list "
             "capped at 70,000 names per day)", access="public download",
             applies_to="registrable domains", facts="whoisds_next_day;"
             "whoisds_reuse"),
        dict(channel="GitHub public event timeline (GH Archive)",
             exposes="the owner name, i.e. the <owner>.github.io host, of "
             "any public repository event such as creating the Pages repo",
             trigger="repository creation", delay_min_s=30,
             delay_max_s=6 * H, delay_basis="public events API latency 30 s "
             "to 6 h; GH Archive files are hourly",
             access="public", applies_to="GitHub Pages sites on the free "
             "plan (public repositories)", facts="gh_createevent_repo;"
             "gh_event_repo_name;gh_events_latency;gharchive_hourly;"
             "gh_free_public_only"),
        dict(channel="Wildcard certificate (own domain or platform)",
             exposes="only the parent of the wildcard (*.parent)",
             trigger="issuance of the wildcard", delay_min_s="",
             delay_max_s="", delay_basis="labels served only under the "
             "wildcard do not appear in CT; a wildcard matches exactly one "
             "label",
             access="", applies_to="labels one level below the wildcard",
             facts="rfc9525_one_label;le_dns01_wildcard"),
        dict(channel="Private-CA or pinned (non-WebPKI) certificate",
             exposes="nothing at mint", trigger="none", delay_min_s="",
             delay_max_s="", delay_basis="Chrome's and Apple's CT "
             "requirements apply to publicly trusted certificates; a "
             "private or self-signed certificate pinned by the defender's "
             "client is under no logging requirement", access="",
             applies_to="labels under an owned domain; IP endpoints",
             facts="chrome_ct_required;apple_ct_required;"
             "tor_nonwebpki_pinning"),
        dict(channel="First use on the censor's path (DNS query, TLS SNI)",
             exposes="the name a client presents", trigger="first client "
             "connection", delay_min_s="", delay_max_s="",
             delay_basis="time from mint to first use (operator-controlled); "
             "not a mint-time channel", access="on-path censor",
             applies_to="all names", facts=""),
    ]
    write_csv("exposure_channels.csv", rows,
              ["channel", "exposes", "trigger", "delay_min_s", "delay_max_s",
               "delay_basis", "access", "applies_to", "facts"])
    return rows


# ---------------------------------------------------------------------------
# 10. Figure (not in the paper): when does a minted name become visible?
# ---------------------------------------------------------------------------
def figure(sch):
    """Documented delay bounds per exposure channel on a log axis. Bars that
    start at the left edge start at zero (the axis cannot show zero)."""
    sys.path.insert(0, FIGSTYLE_DIR)
    import figstyle  # noqa: E402
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    figstyle.use_style()
    H, D = 3600.0, 86400.0
    X0 = 1.0                                   # left edge stands for 0 s
    items = [  # label, lo, hi, kind
        ("CT, static log", X0, 60, "doc"),
        ("CT, RFC 6962 log", X0, 24 * H, "doc"),
        ("CT monitors' first\nDNS lookups (2018)", sch["dns_min_s"],
         sch["dns_max_s"], "obs"),
        ("GitHub public events", 30, 6 * H, "doc"),
        ("gTLD zone file (CZDS)", X0, 48 * H, "doc"),
        ("Daily new-domain list", X0, 48 * H, "doc"),
        ("Wildcard-covered, private\nor pinned names", None, None, "none"),
    ]
    # fixed 3.33 in x 2.3 in canvas (no tight bbox), so fonts stay at 7 pt
    # when the PDF is placed at column width
    fig = plt.figure(figsize=(3.33, 2.3))
    ax = fig.add_axes([0.355, 0.165, 0.625, 0.715])
    n = len(items)
    for i, (lab, lo, hi, kind) in enumerate(items):
        y = n - 1 - i
        if kind == "none":
            ax.text(X0 * 1.3, y, "no mint-time channel (first use only)",
                    va="center", ha="left", fontsize=7, style="italic",
                    color="#444444")
            continue
        col = figstyle.COL[0] if kind == "doc" else figstyle.COL[1]
        ax.plot([lo, hi], [y, y], color=col, lw=5, solid_capstyle="butt")
    ax.set_yticks(range(n))
    ax.set_yticklabels([it[0] for it in items][::-1], fontsize=7)
    ax.set_xscale("log")
    ax.set_xlim(X0, 3 * D)
    ax.set_ylim(-0.6, n - 0.4)
    ticks = [X0, 60, H, D]
    ax.set_xticks(ticks)
    ax.set_xticklabels(["0", "1 min", "1 h", "1 day"], fontsize=7)
    ax.minorticks_off()
    ax.set_xlabel("Delay after issuance or registration", fontsize=7)
    ax.tick_params(axis="y", length=0)
    ax.grid(True, axis="x", color=figstyle.GRIDGRAY, alpha=0.3, lw=0.5)
    ax.grid(False, axis="y")
    hd = [Line2D([0], [0], color=figstyle.COL[0], lw=4,
                 label="documented range"),
          Line2D([0], [0], color=figstyle.COL[1], lw=4,
                 label="observed (2018)")]
    ax.legend(handles=hd, bbox_to_anchor=(0.0, 1.01), loc="lower left",
              ncol=2, frameon=False, fontsize=7, handlelength=1.2,
              columnspacing=1.0, borderaxespad=0)
    out = os.path.join(DER, "fig_exposure_delays.pdf")
    with plt.rc_context({"savefig.bbox": "standard"}):
        # no CreationDate, so the PDF holds no local time and is reproducible
        fig.savefig(out, metadata={"CreationDate": None})
    plt.close(fig)
    return out


def check_fact_refs():
    """Every fact id cited in a derived table must exist (and was verified
    against raw/ in build_facts)."""
    known = {f["id"] for f in FACTS}
    missing = set()
    for name, col in (("acme_mint_rates.csv", "facts"),
                      ("platform_names.csv", "facts"),
                      ("exposure_channels.csv", "facts"),
                      ("minting_costs.csv", "source")):
        for r in csv.DictReader(open(os.path.join(DER, name))):
            v = r[col]
            if col == "source":
                if "facts " not in v:
                    continue
                v = v.split("facts ", 1)[1]
            for tok in re.split(r"[;,\s]+", v):
                if tok and tok not in known:
                    missing.add((name, tok))
    if missing:
        raise SystemExit("unknown fact ids cited: %s" % sorted(missing))


# ---------------------------------------------------------------------------
def main():
    os.makedirs(DER, exist_ok=True)
    n_docs = build_doc_text()
    n_facts = build_facts()
    prices, pb = porkbun()
    _, disp = icann()
    psl_rows, psl_ver, psl_commit = psl_table()
    _, ct = ct_logs()
    _, crt_by = crtsh()
    _, sch = scheitle_table4()
    _, rates = acme_rates(pb)
    platform_table(psl_rows, crt_by)
    minting_costs(prices, pb, rates)
    exposure_channels(ct, sch)
    check_fact_refs()
    fig = figure(sch)
    summary = dict(
        porkbun=pb, ct_log_list=ct, scheitle2018=sch, acme=rates,
        psl=dict(version=psl_ver, commit=psl_commit),
        icann_disposability={d["tld"]: d for d in disp},
        crtsh_wildcards={k: len(v) for k, v in crt_by.items()},
        n_doc_text=n_docs, n_facts_verified=n_facts,
        figure=os.path.relpath(fig, HERE))
    with open(os.path.join(DER, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=str)
        f.write("\n")
    print(json.dumps(dict(docs=n_docs, facts=n_facts,
                          figure=os.path.relpath(fig, HERE)), indent=1))


if __name__ == "__main__":
    main()
