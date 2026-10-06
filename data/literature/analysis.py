#!/usr/bin/env python3
"""
analysis.py -- regenerate data/literature/derived/ from raw/ and params_spec.py.

  python3 analysis.py              # writes derived/
  python3 analysis.py --out DIR    # writes elsewhere (reproducibility check)

Requires pdftotext (poppler-utils) for faithful page text; falls back to pypdf.
Python: standard library only (pypdf only for the fallback).

Steps
  1. Check every raw file against raw/manifest.json (sha256, size).
  2. Extract per-page text from each PDF (pdftotext, reading order and -layout;
     pypdf fallback) and the issue/comment bodies from the GitHub issue page.
  3. Verify that every curated quote (and every `extra_quotes` entry) in
     params_spec.ROWS occurs on the cited page (normalised for whitespace,
     line-break hyphenation, ligatures, typographic quotes/dashes; tiers:
     strict, strict_nohyphen, loose).
  4. Write derived/params_table.csv (+ quote_verification.csv).
  5. Compute derived values that are simple arithmetic on verified numbers
     (derived/derived_values.csv), checking each input number occurs in its quote.
  6. Map literature timescales onto the model's dimensionless rates
     (derived/address_layer_mapping.csv, derived/frontier_sensitivity.csv,
      derived/name_layer_mapping.csv).

No network access. Exit status is non-zero if any hash or quote check fails.
"""

import csv
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
DER = os.path.join(HERE, "derived")
sys.dont_write_bytecode = True  # keep this directory free of __pycache__
sys.path.insert(0, HERE)
from params_spec import ROWS, SOURCES  # noqa: E402

PROBLEMS = []


def problem(msg):
    PROBLEMS.append(msg)
    print("PROBLEM:", msg)


# --------------------------------------------------------------------------- #
# 1. provenance check
# --------------------------------------------------------------------------- #
def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_manifest():
    """Every file listed in raw/manifest.json must exist with the recorded hash and
    size, and every source used by params_spec must be listed."""
    with open(os.path.join(RAW, "manifest.json")) as f:
        man = json.load(f)["files"]
    for fn, meta in man.items():
        path = os.path.join(RAW, fn)
        if not os.path.exists(path):
            problem(f"{fn} missing from raw/")
            continue
        if sha256_of(path) != meta["sha256"] or os.path.getsize(path) != meta["size_bytes"]:
            problem(f"{fn} hash/size differs from manifest")
    for key, src in SOURCES.items():
        if src["file"] not in man:
            problem(f"{src['file']} (source {key}) missing from manifest")
    print(f"manifest: {len(man)} raw files checked")
    return man


# --------------------------------------------------------------------------- #
# 2. text extraction
# --------------------------------------------------------------------------- #
def pdf_pages(path, layout):
    """List of page texts (index 0 = page 1)."""
    if shutil.which("pdftotext"):
        cmd = ["pdftotext", "-enc", "UTF-8"] + (["-layout"] if layout else []) + [path, "-"]
        out = subprocess.run(cmd, capture_output=True, check=True).stdout.decode("utf-8", "replace")
        pages = out.split("\f")
        if pages and not pages[-1].strip():
            pages = pages[:-1]
        return pages, "pdftotext" + (" -layout" if layout else "")
    from pypdf import PdfReader  # fallback (less faithful reading order)
    reader = PdfReader(path)
    return [p.extract_text() or "" for p in reader.pages], "pypdf"


def issue_blocks(path):
    """[(locator, text)] for the GitHub issue body and its comments. A comment is
    located by its position among the comments and its UTC time, not by author."""
    s = open(path, encoding="utf-8").read()
    m = re.search(r'<script type="application/json" data-target="react-app.embeddedData">(.*?)</script>',
                  s, re.S)
    data = json.loads(m.group(1))
    issue = data["payload"]["preloadedQueries"][0]["result"]["data"]["repository"]["issue"]
    blocks = [(f"issue body ({issue['createdAt'][:10]})", issue["body"])]
    for edge in issue["frontTimelineItems"]["edges"]:
        node = edge["node"]
        if "body" in node:
            blocks.append((f"comment {len(blocks)} ({node['createdAt']})", node["body"]))
    return blocks


# --------------------------------------------------------------------------- #
# 3. normalisation and matching
# --------------------------------------------------------------------------- #
TRANS = str.maketrans({
    "‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'",
    "“": '"', "”": '"', "„": '"', "″": '"',
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "―": "-",
    "−": "-", "­": "", " ": " ", " ": " ", " ": " ",
})


def norm_strict(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = unicodedata.normalize("NFKC", s)
    return s.translate(TRANS)


def collapse_ws(s):
    return re.sub(r"\s+", " ", s).strip()


def page_variants(text):
    t = norm_strict(text)
    dehyph = re.sub(r"-[ \t]*\n\s*(?=[a-z])", "", t)   # soft hyphen at line break
    keep = re.sub(r"-[ \t]*\n\s*", "-", t)               # real hyphen at line break
    return [collapse_ws(dehyph), collapse_ws(keep), collapse_ws(t)]


def loose(s):
    return "".join(ch for ch in norm_strict(s).lower() if ch.isalnum())


def match_quote(quote, texts):
    """Return the best match tier of quote in any of texts, or None.

    strict           exact after whitespace/typography normalisation
    strict_nohyphen  exact once hyphens are removed from the quote: pdftotext
                     drops the hyphen of a compound word split across lines
                     (e.g. 'nine-\\nmonth' -> 'ninemonth')
    loose            alphanumeric characters only
    """
    q = collapse_ws(norm_strict(quote))
    for t in texts:
        if any(q in v for v in page_variants(t)):
            return "strict"
    qh = q.replace("-", "")
    for t in texts:
        if any(qh in v.replace("-", "") for v in page_variants(t)):
            return "strict_nohyphen"
    lq = loose(quote)
    for t in texts:
        if lq and lq in loose(t):
            return "loose"
    return None


# --------------------------------------------------------------------------- #
# 5. derived values (simple arithmetic on verified numbers)
# --------------------------------------------------------------------------- #
def derived_values(rows_by_id, page_text):
    out = []

    def add(name, value, formula, inputs, unit, note=""):
        out.append(dict(name=name, value=value, unit=unit, formula=formula,
                        inputs=";".join(inputs), note=note))

    def need(row_id, *tokens, page_of=None):
        """Assert each numeric token occurs in the verified quote (or on the cited page)."""
        r = rows_by_id[row_id]
        hay = norm_strict(r["quote"]) if page_of is None else norm_strict(page_text[page_of])
        hay = collapse_ws(hay)
        for tok in tokens:
            if tok not in hay:
                problem(f"derived value input '{tok}' not found for {row_id}")

    # G14: GFW enforcement leakage on blacklisted Tor IP:port pairs (2014)
    need("G14", "116,460", "555", "786", "25,061")
    s2c, none, c2s, err = 116460, 555, 786, 25061
    add("gfw_2014_torrelay_leakage_excl_errors", round(none / (s2c + none + c2s), 5),
        "none / (S->C + none + C->S)", ["G14"], "fraction of non-error tests",
        "Share of client-relay-hour tests in which no packet was dropped, errors excluded.")
    add("gfw_2014_torrelay_leakage_incl_errors", round(none / (s2c + none + c2s + err), 5),
        "none / all tests", ["G14"], "fraction of tests", "")

    # G27/G29: release-to-block delays of default bridges
    need("G27", "7, 2, 18, 11, and 36 days")
    need("G29", "7, 2, 18, 10, 35, and 6 days")
    d16 = [7, 2, 18, 11, 36]
    d17 = [7, 2, 18, 10, 35, 6]
    for tag, d, rid in (("2016", d16, "G27"), ("2017", d17, "G29")):
        add(f"gfw_release_to_block_mean_{tag}", round(sum(d) / len(d), 2), "mean of batch delays", [rid], "days")
        add(f"gfw_release_to_block_median_{tag}", float(sorted(d)[len(d) // 2]) if len(d) % 2 else
            (sorted(d)[len(d) // 2 - 1] + sorted(d)[len(d) // 2]) / 2, "median of batch delays", [rid], "days")
        add(f"gfw_release_to_block_min_max_{tag}", f"{min(d)}-{max(d)}", "range", [rid], "days")

    # G41: GFWatch base-domain persistence within the window
    need("G41", "126K")
    need("G41", "138.7K", page_of=("hoang2021usenix", 5))
    add("gfwatch_base_domains_still_blocked_frac", round(126.0 / 138.7, 3), "126K / 138.7K", ["G41"],
        "fraction", "Right-censored at 31 Dec 2020; includes domains first seen late in the window.")

    # G34: QUIC SNI blocklist as share of tested Tranco FQDNs
    need("G34", "58,207")
    need("G34", "6,955,968", page_of=("zohaib2025usenix", 9))
    add("gfw_quic_ever_blocked_share_of_tranco", round(58207 / 6955968, 5), "58,207 / 6,955,968", ["G34"],
        "fraction of tested FQDNs", "Tested list is popularity-ranked; not a population rate.")
    add("gfw_quic_union_over_weekly_mean", round(58207 / 43800, 3), "58,207 / 43.8K", ["G34"], "ratio",
        "Union over ~14 weeks vs weekly mean; mixes list churn and measurement misses. Do not read as churn.")

    # T03: TSPU coverage
    need("T03", "4,005,138", "1,013,600", "25.31%")
    add("tspu_endpoint_coverage_lower_bound", round(1013600 / 4005138, 4), "1,013,600 / 4,005,138", ["T03"],
        "fraction of endpoints", "Lower bound per authors.")

    # T04: TSPU failure range (whole table on page 6, layout)
    need("T04", "2.19%")
    add("tspu_max_failure_rate", 0.0219, "max over Table 1 cells", ["T04"], "fraction",
        "Min cell 0.00%; ER-Telecom worst; Rostelecom/OBIT have two TSPUs on path.")

    # I01: Iran protocol-filter coverage (denominator ~20,000 is approximate)
    need("I01", "3,595", "17.9%")
    add("iran_filter_ip_share", 0.179, "as reported (3,595 IPs)", ["I01"], "fraction of tested IPs",
        "Denominator (20,000 site IPs minus unresponsive) not stated exactly.")

    # S01/S10: Snowflake churn consistency
    need("S01", "20 hours", "50%")
    need("S10", "2.7% per hour")
    hourly_from_s01 = 1 - 0.5 ** (1 / 20)
    add("snowflake_hourly_turnover_from_20h_halflife", round(hourly_from_s01, 4), "1 - 0.5^(1/20)", ["S01"],
        "per hour", "Assumes memoryless turnover.")
    add("snowflake_halflife_implied_by_2.7pct_per_hour", round(math.log(0.5) / math.log(1 - 0.027), 1),
        "ln 0.5 / ln(1-0.027)", ["S10"], "hours", "vs ~20 h observed (S01): simulation default is slower churn.")

    # G43: name-block durations
    need("G43", "173.8", "256", "35.7", "21")
    add("gfw_name_block_median_lower_bound_days", ">=256", "window length (right-censored)", ["G43"], "days",
        "More than 50% of GFW-blocked domains were blocked for the whole 256-day window.")
    add("henan_over_gfw_mean_duration_ratio", round(35.7 / 173.8, 3), "35.7 / 173.8", ["G43"], "ratio",
        "GFW mean is itself censored at 256 d (lower bound), so the ratio is an upper bound.")

    # H01
    need("H01", "4,196,532", "741,542")
    add("henan_over_gfw_cumulative_blocklist", round(4196532 / 741542, 2), "4,196,532 / 741,542", ["H01"], "ratio")

    # S07/S08 collateral increments of single hyperscaler ASes
    need("S08", "1.37%", "5.48%", "8.22%", "17.81%")
    add("amazon02_top100_collateral_increment_pp", round(5.48 - 1.37, 2), "5.48 - 1.37", ["S08"],
        "percentage points of Tranco top-100", "")
    add("cloudflare_top100_collateral_increment_pp", round(17.81 - 8.22, 2), "17.81 - 8.22", ["S08"],
        "percentage points of Tranco top-100", "")
    return out


# --------------------------------------------------------------------------- #
# 6. model mapping (closed forms of the model: c_a, pi_0, time-average frontier)
# --------------------------------------------------------------------------- #
def ca(n, ratio):
    """Address factor c_a = 1 - (lam_a/(lam_a+mu))^n with ratio = mu/lam_a."""
    return 1.0 - (1.0 / (1.0 + ratio)) ** n


def ratio_needed(n, alpha):
    """Smallest mu/lam_a with c_a >= alpha."""
    return (1.0 - alpha) ** (-1.0 / n) - 1.0


def pi0_const(beta, kmax):
    if abs(beta - 1.0) < 1e-12:
        return 1.0 / (kmax + 1)
    r = 1.0 / beta
    return (1.0 - r) / (1.0 - r ** (kmax + 1))


def bisect(f, lo, hi, tol=1e-10):
    flo = f(lo)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


def beta_star_avg(alpha, c_a, kmax):
    """Theorem (frontier): root of 1 - pi0(beta,kmax) = alpha/c_a (time-average)."""
    target = alpha / c_a
    if target >= 1.0:
        return float("nan")
    return bisect(lambda b: (1.0 - pi0_const(b, kmax)) - target, 1e-6, 1e3)


def pi0_perunit(rho, kmax):
    return 1.0 / sum(rho ** j / math.factorial(j) for j in range(kmax + 1))


def rho_star(alpha, kmax, c_a=1.0):
    """Per-unit burns (each live name burned independently at rate delta, so the burn rate
    grows with K; an alternative to the model's constant aggregate burn rate): smallest
    rho = lam_intro/delta with c_a(1-pi0) >= alpha."""
    if alpha / c_a >= 1.0:
        return float("nan")
    return bisect(lambda r: c_a * (1.0 - pi0_perunit(r, kmax)) - alpha, 1e-9, 1e4)


SEC = dict(s=1.0, min=60.0, h=3600.0, d=86400.0, wk=7 * 86400.0)


def fmt_dur(sec):
    if sec is None or (isinstance(sec, float) and math.isnan(sec)):
        return "n/a"
    if math.isinf(sec):
        return "inf"
    for unit, div in (("d", 86400.0), ("h", 3600.0), ("min", 60.0)):
        if sec >= div:
            return f"{sec / div:.3g} {unit}"
    return f"{sec:.3g} s"


# Address-layer scenarios: time from first use (exposure) to address block.
# lo / central / hi in seconds; every number is tied to verified rows.
ADDR_SCENARIOS = [
    dict(key="gfw_tor_dpi_probe", censor="GFW", label="DPI + active-probe confirmable (Tor, 2012-2018)",
         lo=1.0, central=60.0, hi=300.0, rows="G01;G03;G04",
         basis="probes arrive in 0.55 s median (G01); scans stop after ~1 min (G04); 'a few minutes' (G03). "
               "lo = 1 s is a bound (block cannot precede the probe); central = scan window."),
    dict(key="gfw_shadowsocks", censor="GFW", label="Shadowsocks (2019-2020)",
         lo=60.0, central=float("nan"), hi=float("inf"), rows="G05;G06;G07;G08",
         basis="50% of replay probes within 1 min (G05) bounds time-to-block from below; most probed servers "
               "were never blocked (G07) -> no finite central value."),
    dict(key="gfw_published_directory", censor="GFW", label="unit listed in a public directory (Tor consensus, 2018)",
         lo=600.0, central=600.0, hi=600.0, rows="G26",
         basis="'on average ... after 10 minutes' (G26)."),
    dict(key="gfw_published_release", censor="GFW", label="unit shipped in public software (default bridges, 2015-16)",
         lo=2 * 86400.0, central=11 * 86400.0, hi=36 * 86400.0, rows="G27;G29",
         basis="batch delays 2-36 d, median 11 d (G27); pre-release blocking from Oct 2016 (G30)."),
    dict(key="tspu_field_report", censor="TSPU", label="Outline server, field report (2022)",
         lo=300.0, central=600.0, hi=900.0, rows="T01",
         basis="'web surfing for 5-15 minutes' then IP banned (T01); single field report."),
    dict(key="iran_public_bridges", censor="Iran", label="public default Tor bridges (2015-2017)",
         lo=float("inf"), central=float("inf"), hi=float("inf"), rows="I05;I06",
         basis="no blocking observed (I05, I06); TCP-level tests only."),
]

TAUS = [("5 min", 300.0), ("1 h", 3600.0), ("1 d", 86400.0)]
ROTS = [("60 s", 60.0), ("5 min", 300.0), ("1 h", 3600.0)]


def address_mapping():
    rows = []
    for sc in ADDR_SCENARIOS:
        for which in ("lo", "central", "hi"):
            ED = sc[which]
            r = dict(scenario=sc["key"], censor=sc["censor"], label=sc["label"], bound=which,
                     E_D_a_seconds=ED, E_D_a=fmt_dur(ED), rows=sc["rows"])
            for name, tau in TAUS:
                r[f"lambda_a_dimless_tau_{name}"] = (tau / ED) if (ED and not math.isnan(ED)) else float("nan")
            for name, dt in ROTS:
                r[f"mu_over_lambda_a_rot_{name}"] = (ED / dt) if not math.isnan(ED) else float("nan")
            for n in (1, 2, 4, 8):
                need = ratio_needed(n, 0.95)
                r[f"max_rotation_interval_n{n}_a0.95"] = fmt_dur(ED / need) if not math.isnan(ED) else "n/a"
            rows.append(r)
    return rows


def frontier_sensitivity():
    out = []
    for kmax in (4, 8, 16, 32):
        for n in (2, 4, 8):
            for ratio in (0.25, 0.5, 1.0, 2.0, 3.0, 3.75, 10.0):
                c = ca(n, ratio)
                out.append(dict(alpha=0.95, kmax=kmax, n=n, mu_over_lambda_a=ratio, c_a=round(c, 6),
                                beta_star_avg=round(beta_star_avg(0.95, c, kmax), 4)
                                if c > 0.95 else "none (c_a < alpha)"))
    return out


NAME_SCENARIOS = [
    dict(key="public_directory_gfw2018", label="listed in a public directory (GFW, 2018)", E_D=600.0, rows="G26",
         kind="measured (address units, not names)"),
    dict(key="software_release_gfw2016_median", label="shipped in public software, median (GFW, 2015-16)",
         E_D=11 * 86400.0, rows="G27", kind="measured (address units, not names)"),
    dict(key="software_release_gfw2016_mean", label="shipped in public software, mean (GFW, 2015-16)",
         E_D=14.8 * 86400.0, rows="G27", kind="measured (address units, not names)"),
    dict(key="assume_1d", label="private minted name, ASSUMED 1 d", E_D=86400.0, rows="", kind="assumption"),
    dict(key="assume_7d", label="private minted name, ASSUMED 7 d", E_D=7 * 86400.0, rows="", kind="assumption"),
    dict(key="assume_30d", label="private minted name, ASSUMED 30 d", E_D=30 * 86400.0, rows="", kind="assumption"),
]


def name_mapping():
    kmax, alpha = 8, 0.95
    bstar_avg = beta_star_avg(alpha, 1.0, kmax)
    rho = rho_star(alpha, kmax)
    out = []
    for sc in NAME_SCENARIOS:
        delta_per_day = 86400.0 / sc["E_D"]
        lam_disc_full = delta_per_day * kmax       # constant aggregate burn rate equal to the per-unit rate at a full pool
        out.append(dict(
            scenario=sc["key"], label=sc["label"], basis=sc["kind"], rows=sc["rows"],
            mean_time_to_block=fmt_dur(sc["E_D"]), per_unit_hazard_per_day=round(delta_per_day, 4),
            kmax=kmax, alpha=alpha,
            const_rate_lambda_disc_per_day=round(lam_disc_full, 3),
            const_rate_min_mint_per_day_beta_avg=round(lam_disc_full / bstar_avg, 3),
            per_unit_min_mint_per_day=round(rho * delta_per_day, 3),
            beta_star_avg=round(bstar_avg, 4), rho_star=round(rho, 4)))
    return out


# --------------------------------------------------------------------------- #
def write_csv(path, rows, fields=None):
    fields = fields or list(rows[0].keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    # optional: python3 analysis.py --out DIR  (write outputs elsewhere, e.g. to
    # check that a fresh run reproduces derived/ byte for byte)
    global DER
    if "--out" in sys.argv:
        DER = os.path.abspath(sys.argv[sys.argv.index("--out") + 1])
    os.makedirs(DER, exist_ok=True)
    check_manifest()

    # extraction cache
    texts = {}       # (source, mode) -> list of pages / blocks
    tools = {}
    for key, src in SOURCES.items():
        path = os.path.join(RAW, src["file"])
        if src["file"].endswith(".pdf"):
            for mode in ("text", "layout"):
                pages, tool = pdf_pages(path, layout=(mode == "layout"))
                texts[(key, mode)] = pages
                tools[(key, mode)] = tool
        else:
            texts[(key, "html")] = issue_blocks(path)
            tools[(key, "html")] = "embedded JSON (react-app.embeddedData)"

    def locate(r, quote):
        """(status, found_on) for one quote of row r."""
        if r["mode"] == "html":
            blocks = texts[(r["source"], "html")]
            cited = [t for (loc, t) in blocks if loc == r["page"]]
            status = match_quote(quote, cited) if cited else None
            found_on = [loc for (loc, t) in blocks if match_quote(quote, [t])] if status is None else []
            return status, found_on
        pages_t = texts[(r["source"], "text")]
        pages_l = texts[(r["source"], "layout")]
        p = int(r["page"])
        cited = [pages_t[p - 1], pages_l[p - 1]] if p - 1 < len(pages_t) else []
        status = match_quote(quote, cited)
        found_on = []
        if status is None:
            found_on = [i + 1 for i in range(len(pages_t)) if match_quote(quote, [pages_t[i], pages_l[i]])]
        return status, found_on

    table, verif = [], []
    rows_by_id = {}
    for r in ROWS:
        src = SOURCES[r["source"]]
        status, found_on = locate(r, r["quote"])
        if r["mode"] == "html" or src["printed_offset"] is None:
            printed = ""
        else:
            printed = str(int(r["page"]) + src["printed_offset"])
        extras = r.get("extra_quotes", [])
        extra_ok = 0
        for k, eq in enumerate(extras, 1):
            est, efound = locate(r, eq)
            extra_ok += est is not None
            if est is None:
                problem(f"extra quote {k} not found: {r['id']} ({r['source']} p.{r['page']}); found on {efound}")
            verif.append(dict(row_id=f"{r['id']}+{k}", source_key=r["source"], page=r["page"], mode=r["mode"],
                              extractor=tools[(r["source"], "html" if r["mode"] == "html" else r["mode"])],
                              verified=est is not None, match=est or "", also_found_on=";".join(map(str, efound)),
                              quote=collapse_ws(eq)))
        verified = status is not None and extra_ok == len(extras)
        if status is None:
            problem(f"quote not found on cited page: {r['id']} ({r['source']} p.{r['page']}); found on {found_on}")
        rec = dict(censor=r["censor"], parameter=r["parameter"], value_or_range=r["value"], units=r["units"],
                   context=r["context"], source_key=r["source"], quote=collapse_ws(r["quote"]), page=r["page"],
                   printed_page=printed, row_id=r["id"], param_type=r["ptype"], model_quantity=r["model"],
                   comparable_to_model=r["comparable"], verified=verified, match=status or "",
                   extra_quotes_verified=f"{extra_ok}/{len(extras)}" if extras else "",
                   citation=src["cite"], bibkey=src["bibkey"], raw_file="raw/" + src["file"], note=r["note"])
        table.append(rec)
        rows_by_id[r["id"]] = r
        verif.append(dict(row_id=r["id"], source_key=r["source"], page=r["page"], mode=r["mode"],
                          extractor=tools[(r["source"], "html" if r["mode"] == "html" else r["mode"])],
                          verified=status is not None, match=status or "", also_found_on=";".join(map(str, found_on)),
                          quote=collapse_ws(r["quote"])))
    verif.sort(key=lambda v: (v["row_id"].split("+")[0], v["row_id"]))

    fields = ["censor", "parameter", "value_or_range", "units", "context", "source_key", "quote", "page",
              "printed_page", "row_id", "param_type", "model_quantity", "comparable_to_model", "verified", "match",
              "extra_quotes_verified", "citation", "bibkey", "raw_file", "note"]
    write_csv(os.path.join(DER, "params_table.csv"), table, fields)
    write_csv(os.path.join(DER, "quote_verification.csv"), verif)

    # derived values
    page_text = {}
    for (key, mode), pages in texts.items():
        if mode == "text":
            for i, t in enumerate(pages):
                page_text[(key, i + 1)] = t
    write_csv(os.path.join(DER, "derived_values.csv"), derived_values(rows_by_id, page_text))

    # model mapping
    write_csv(os.path.join(DER, "address_layer_mapping.csv"), address_mapping())
    write_csv(os.path.join(DER, "frontier_sensitivity.csv"), frontier_sensitivity())
    write_csv(os.path.join(DER, "name_layer_mapping.csv"), name_mapping())

    n_ok = sum(1 for r in table if r["verified"])
    print(f"quotes verified: {n_ok}/{len(table)} "
          f"(strict {sum(1 for r in table if r['match'] == 'strict')}, "
          f"strict_nohyphen {sum(1 for r in table if r['match'] == 'strict_nohyphen')}, "
          f"loose {sum(1 for r in table if r['match'] == 'loose')})")
    if PROBLEMS:
        print(f"{len(PROBLEMS)} problem(s)")
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
