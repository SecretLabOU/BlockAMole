# Minting outputs (`data/minting/derived/`)

`../analysis.py` writes every file of this directory from the files in
`../raw/`, without network access. The artifact ships this README and the 12
files marked "yes" in the table below, which hold the paper's values. The
other outputs are left out, and a rebuild writes them again.

## Rebuild

Run this in `data/minting/` after the downloads described in
`../raw/README.md`.

```sh
python3 analysis.py
```

- It takes about 10 s and 170 MB of memory. It needs `pdftotext` from
  poppler-utils, and `../../simulations/code/figstyle.py` with
  `paper.mplstyle`.
- It first converts the 66 saved HTML, Markdown and PDF documents to text
  (`doc_text/`), then checks the 131 quotes of `../facts.py` and writes the
  tables, the figure and `summary.json`. At the end it prints
  `"docs": 66`, `"facts": 131` and the path of the figure.
- It overwrites the shipped files in this directory. The SHA-256 values below
  identify the shipped versions.
- A rebuild from the snapshot's raw files reproduces the shipped files byte
  for byte, and two rebuilds gave identical outputs, the figure included.
  They used Python 3.13.7, pandas 3.0.6, matplotlib 3.10.1, numpy 2.2.4 and
  pdftotext 25.03.0. Values computed from new downloads can differ, because
  several sources are live (`../raw/README.md`, Section 4).
- `doc_facts.csv`, `porkbun_summary.csv`, `crtsh_platform_wildcards.csv` and
  `summary.json` copy the retrieval times in `../raw/manifest.json`, which
  `fetch.py` rewrites. After a download they therefore differ from the shipped
  versions even where the inputs are unchanged. When step 3 of
  `../raw/README.md` prints `202 identical, 0 changed or missing`, run
  `cp manifest.paper.json raw/manifest.json` in `data/minting/` before
  `python3 analysis.py`, and the rebuild then matches every SHA-256 below.

## Check files against the shipped versions

Run this in `data/minting/derived/`. It prints `OK` for every file that
matches the shipped version. On macOS use `shasum -a 256 -c` instead of
`sha256sum -c`.

```sh
sha256sum -c <<'EOF'
8632538a94e91a49f14f1b3e5f2a75851d658ce0ae01d7ccbd7b7a5b39a3fbc0  acme_mint_rates.csv
ec81fd1a1f64e717e3d58beb50989bfc2fcc27f4f9427710f6f20494914f3c53  crtsh_platform_wildcards.csv
03608a553e48ed495fe3d3097c88be17e341b4a826ac9e96756ef606052579b6  doc_facts.csv
54a554d9055af27252f3edc9fd12f1766ea9dc28280470d07861cf30d6d59e67  exposure_channels.csv
f2885d7052f8cd904168f50d21510a5be7a4a113d868704263fc57b4cbdd455b  icann_disposability.csv
9744e14f28a9deeed256f20bb2cf3ea2cfb7d1959900fbbf86a7fa71ddf9d8ec  icann_mrr_monthly.csv
a84e500328a704ddc3ce9cce97e559714f24176bbae662406487756cccf8ac64  minting_costs.csv
7727a94c8de1f9274d3b81d2ae21e3e30899ee8c74451304a8b889bf3f3b498e  platform_names.csv
d437634dc6b04b3779267addaf119a1cec92f599306ec344c26bff0518c23893  porkbun_summary.csv
5515f6c52acab785a2eed9626f2e402b4837b88e7b3ceaff12d3a21b53fd332b  psl_platform_suffixes.csv
05554ab6e328e90d5a897cefc8c1510a805f557e4efd661d18c92ffcc4f326d2  scheitle2018_table4.csv
dd5bd06b4a645c7330662b7a565a2d77980c810f182dd6b770cf34b0ce0e054e  summary.json
EOF
```

From the snapshot's raw files, a rebuild also writes these two files that
the artifact leaves out.

```text
b5e5d44516479d514e01661ae906870eb3dfc341800e17604f3ad266e6d20037  ct_log_list_summary.csv
81db17abe99cc7d0e156433e91fbe8bbed6ed14223c87d704106c6d950e5eefa  porkbun_tld_prices.csv
```

## Print the paper's values

Run this in `data/minting/`. It reads only the shipped files.

```sh
python3 - <<'EOF'
import csv, json
s = json.load(open("derived/summary.json"))
p, c, h = s["porkbun"], s["ct_log_list"], s["scheitle2018"]
print("Porkbun", p["retrieved_utc"], "cheapest first year", p["cheapest_first_year_usd"],
      "USD at", len(p["cheapest_first_year_tlds"].split()), "TLDs,",
      p["n_tlds_first_year_lt_2usd"], "TLDs under 2 USD of", p["icann_tlds_priced"])
print("Let's Encrypt orders per account per day", s["acme"]["le_orders_per_account_per_day"])
print("Chrome log list", c["log_list_version"], "static-ct-api MMD", c["mmd_values_static"],
      "in", c["n_static_usable_or_qualified"], "logs, RFC 6962 MMD",
      c["mmd_values_rfc6962"], "in", c["n_rfc6962_usable_or_qualified"], "logs")
print("2018 honeypot, first DNS lookups", h["dns_min_s"], "to", h["dns_max_s"],
      "s after logging, n =", h["n"])
for q, a, b in sorted({(r["identity_queried"], r["not_before"][:10], r["not_after"][:10])
                       for r in csv.DictReader(open("derived/crtsh_platform_wildcards.csv"))}):
    print("crt.sh", q, a, "to", b)
f = {r["fact_id"]: r for r in csv.DictReader(open("derived/doc_facts.csv"))}
print(sum(r["verified_in_raw"] == "True" for r in f.values()), "of", len(f), "quotes verified")
for k in ("le_free", "gts_free", "zerossl_unlimited", "le_orders_per_account",
          "chrome_ct_required", "apple_ct_required", "rfc6962_mmd", "zfa_daily",
          "tor_nonwebpki_pinning", "tor_wt_requires_domain",
          "tor_wt_requires_cert", "zfa_agreement", "zfa_deny", "zfa_active_names",
          "ra_icann_daily", "ra_once_per_24h", "scheitle_dns_73s_3min", "scheitle_11_names",
          "rfc6962_precert", "chrome_two_scts", "chrome_embed_scts", "chrome_mmd_caps",
          "chrome_incorporate_mmd"):
    print(k, "|", f[k]["quote"])
EOF
```

On the shipped files it prints the following.

```text
Porkbun 2026-10-03T21:46:19Z cheapest first year 1.54 USD at 26 TLDs, 36 TLDs under 2 USD of 543
Let's Encrypt orders per account per day 2400
Chrome log list 93.3 static-ct-api MMD [60] in 43 logs, RFC 6962 MMD [86400] in 21 logs
2018 honeypot, first DNS lookups 73 to 197 s after logging, n = 11
crt.sh *.github.io 2026-08-02 to 2026-10-31
crt.sh *.netlify.app 2026-02-16 to 2027-03-19
crt.sh *.web.app 2026-07-20 to 2026-10-18
131 of 131 quotes verified
le_free | Let's Encrypt is a free, automated, and open Certificate Authority
gts_free | Certificates issued by the Public CA feature of Certificate Manager are free of charge.
zerossl_unlimited | you will be able to generate an unlimited amount of 90-day SSL certificates at no charge, also supporting multi-domain certificates and wildcards.
le_orders_per_account | Up to 300 new orders can be created by a single account every 3 hours. The ability to create new orders refills at a rate of 1 order every 36 seconds.
chrome_ct_required | In CT-enforcing versions of Chrome, all publicly-trusted TLS certificates are required to be CT Compliant to successfully validate.
apple_ct_required | Publicly trusted Transport Layer Security (TLS) server authentication certificates must meet Apple's Certificate Transparency (CT) policy to be evaluated as trusted on Apple platforms.
rfc6962_mmd | The log MUST incorporate a certificate in its Merkle Tree within the Maximum Merge Delay period after the issuance of the SCT.
zfa_daily | Registry operators must provide to ICANN bulk access to the zone files of the Generic Top Level Domain (gTLD) at least on a daily basis.
tor_nonwebpki_pinning | safe non-WebPKI certificate support with certificate-chain pinning
tor_wt_requires_domain | a domain under your control
tor_wt_requires_cert | A valid TLS certificate;
zfa_agreement | electronically sign the agreement via ICANN Centralized Zone Data Service (CZDS)
zfa_deny | Under certain circumstances a Registry Operator may deny or revoke access.
zfa_active_names | a zone file contains information about domain names that are active in that gTLD.
ra_icann_daily | Access will be provided at least daily. Zone files will include SRS data committed as close as possible to 00:00:00 UTC.
ra_once_per_24h | no more than once per 24 hour period
scheitle_dns_73s_3min | we see the first DNS queries for corresponding domain names after 73 seconds to ≈3 minutes
scheitle_11_names | In 3 batches, we create 11 honeypot subdomains over 18 days.
rfc6962_precert | certificate authorities may submit a certificate to logs prior to issuance.
chrome_two_scts | | <= 180 days | 2 |
chrome_embed_scts | Most TLS servers do not support the TLS extension, so CAs should be prepared to embed SCTs into issued certificates
chrome_mmd_caps | static-ct-api logs must not specify a MMD greater than 1 minute and RFC 6962 logs must not specify a MMD greater than 4 hour.
chrome_incorporate_mmd | Incorporate a certificate for which an SCT has been issued by the log within the MMD.
```

## Files

All files are written by `python3 analysis.py`, run in `data/minting/`. The
second column names the function of `analysis.py` that writes the file.

| File | Function | Ships | Paper statement | Value in the shipped file |
|---|---|---|---|---|
| `porkbun_summary.csv` | `porkbun()` | yes | Section 6.3, "On 3 October 2026, one registrar listed 36 top-level domains (TLDs) under $2 for the first year, the cheapest at $1.54". Section 1, "Names are cheap to mint". Appendix D, "one registrar's price list on one day" | `n_tlds_first_year_lt_2usd` 36, `cheapest_first_year_usd` 1.54 (26 TLDs in `cheapest_first_year_tlds`), `icann_tlds_priced` 543, `retrieved_utc` 2026-10-03T21:46:19Z |
| `acme_mint_rates.csv` | `acme_rates()` | yes | Section 6.3, Let's Encrypt "allows 2,400 orders a day per account" | row "Let's Encrypt, per ACME account", `sustained_per_day` 2400 (86,400 s divided by one order every 36 s) |
| `scheitle2018_table4.csv` | `scheitle_table4()` | yes | Section 6.3, "in 2018 third parties looked up new names 73 to 197 s after logging". Appendix D, "a CT honeypot study" | 11 rows of Table 4 of Scheitle et al., `dns_delay_s` from 73 to 197 (median 118) |
| `crtsh_platform_wildcards.csv` | `crtsh()` | yes | Section 6.3, tenant names under a platform wildcard "(as for `*.netlify.app` and `*.web.app`)" | `*.netlify.app` (DigiCert, 2026-02-16 to 2027-03-19, 2 certificates) and `*.web.app` (Google Trust Services, 2026-07-20 to 2026-10-18). The `*.github.io` rows (Let's Encrypt) are not named in the paper, because GitHub's public events publish the owner names |
| `doc_facts.csv` | `build_facts()` | yes | every documentary statement (next section) | 131 quotes, each with source URL, retrieval time and SHA-256, all `verified_in_raw` True |
| `minting_costs.csv` | `minting_costs()` | yes | Section 6.3, labels and tenant names "count as free new names if the censor blocks exact names", and which unit types are exposed at mint (the exposed share near 1 or near 0) | `marginal_cost_per_name_usd` 0.0 in the rows "sub-domain label under an owned domain" and "platform tenant sub-domain (PSL private suffix)", `censor_burn_unit` of those rows (a name of its own only if the censor blocks exact names), `exposed_at_mint` for each unit type, and the first-year prices of 12 TLDs |
| `exposure_channels.csv` | `exposure_channels()` | yes | Section 6.3, the channels that expose a name at mint | `delay_min_s` and `delay_max_s` of each channel, for example 0 to 60 for static CT logs and 0 to 86400 for RFC 6962 logs |
| `platform_names.csv` | `platform_table()` | yes | Section 6.3, "within a platform's per-account cap" and names "not otherwise published". Context for Section 7, step 6 ("within their quotas and terms of service") | 12 platforms, columns `names_per_account`, `account_terms`, `cert_evidence` and `ct_exposure_at_mint` |
| `psl_platform_suffixes.csv` | `psl_table()` | yes | background for Section 6.3, where each tenant name is its own registered domain | 17 synthetic host patterns, all under rules of the private section of the Public Suffix List |
| `icann_mrr_monthly.csv` | `icann()` | yes | none | Totals rows of the 120 ICANN monthly reports |
| `icann_disposability.csv` | `icann()` | yes | none | yearly additions, deletions and renewals of 5 TLDs |
| `summary.json` | `main()` | yes | the values of the rows above | see "Print the paper's values" |
| `porkbun_tld_prices.csv` | `porkbun()` | no, Porkbun's prices for every ICANN TLD it lists, a bulk copy of a source without a license | prices behind `porkbun_summary.csv` | 543 rows |
| `ct_log_list_summary.csv` | `ct_logs()` | no, one row per log of Chrome's log list, a source without a license | logs behind `summary.json` (`ct_log_list`) | 69 logs |
| `fig_exposure_delays.pdf` | `figure()` | no, not used in the paper | none | |
| `doc_text/<id>.txt` | `build_doc_text()` | no, full text of the saved pages | text for the quote checks | 66 files |

## Facts behind the paper's statements

These ids are in the `fact_id` column of `doc_facts.csv`.

- Section 3 (Scope), WebTunnel bridges use the operator's domain name with a
  publicly trusted certificate by default: `tor_wt_requires_domain` and
  `tor_wt_requires_cert`. The WebTunnel guide obtains the certificate with an
  ACME client.
- Section 3 (Scope), "a pinned certificate with no SNI or, as WebTunnel
  supports, an arbitrary one": `tor_nonwebpki_pinning` covers the pinned
  certificate. The arbitrary SNI rests on the paper's other references and is
  outside this analysis.
- Section 5.4 (Mint-time exposure), a name can become visible at mint "when
  its certificate is logged in CT": `chrome_ct_required`,
  `apple_ct_required`, `le_logs_everything` and `rfc6962_precert`.
- Section 6.3, free certificates and 2,400 orders a day: `le_free` and
  `le_orders_per_account`.
- Section 6.3, CT logging that Chrome and Apple platforms require:
  `chrome_ct_required` and `apple_ct_required`.
- Section 6.3, merge delays of 60 s or 24 h: `rfc6962_mmd`,
  `chrome_incorporate_mmd`, `chrome_mmd_caps`, `static_null_mmd` and
  `le_sunlight_zero_mmd`, with the log list values in `summary.json`.
- Section 6.3, the 2018 honeypot: `scheitle_dns_73s_3min` and
  `scheitle_11_names`.
- Section 6.3, daily zone files: `zfa_daily`, `zfa_active_names`,
  `ra_icann_daily` and `ra_once_per_24h`.
- Section 6.3, names under a wildcard certificate and names published by
  other means: `le_dns01_wildcard`, `rfc9525_one_label`, `netlify_instant`,
  `gh_free_public_only`, `gh_createevent_repo`, `gh_event_repo_name` and
  `gh_events_latency`.
- Section 6.3, private pinned certificates in WebTunnel since 2025:
  `tor_nonwebpki_pinning` (Tor blog post of December 2025).
- Section 6.3, per-account caps: `gh_one_site`, `cf_workers_per_account`,
  `cf_pages_100_projects`, `vercel_projects`, `vercel_deploys_day`,
  `firebase_36_sites`, `deno_free_10_apps`, `azure_free_10_apps` and
  `gcr_1000_services`.
- Section 8 (Limits), access-gated zone files of ICANN's Centralized Zone Data
  Service: `zfa_agreement` and `zfa_deny`.
- Appendix D, three free certificate authorities: `le_free`, `gts_free` and
  `zerossl_unlimited`.

## When a run stops

- `FileNotFoundError` for `raw/manifest.json`. The manifest is missing.
- `FileNotFoundError` for another path. A file listed in the manifest is
  missing (`../raw/README.md`, Section 2).
- `quotes not found in raw sources: [...]`. A page downloaded again no longer
  contains a quote (`../raw/README.md`, Section 5). Only `doc_text/` and
  `doc_facts.csv` are rewritten.
- `AssertionError` in `icann()`. A TLD lacks one of its 24 months, a report
  lacks exactly one Totals row, or the registrar rows do not add up to it.
- `AssertionError` in `scheitle_table4()`. The `pdftotext -layout` output
  differs from that of version 25.03.0, and the parser does not find the 11
  rows of Table 4.
- `AssertionError` in `acme_rates()`. A number that the rate table uses is no
  longer in its quote.
- `RuntimeError: pdftotext (poppler-utils) is required for PDFs`. Install
  poppler-utils.
- `ModuleNotFoundError: No module named 'figstyle'`.
  `../../simulations/code/` is missing. All CSV files are written, but
  `summary.json` is not.
- `unknown fact ids cited: [...]`. A fact id that a derived table cites is
  missing from `../facts.py`.

## Licenses

The license terms of the artifact are in `LICENSE` at its root. The quotes in
`doc_facts.csv` are short excerpts of the sources named in each row, cited
with URL, retrieval time and SHA-256. `psl_platform_suffixes.csv` repeats
rule names and operator headers of the Public Suffix List (MPL-2.0).
