# Minting inputs (`data/minting/raw/`)

In the artifact this directory holds two files, this README and
`manifest.json`. The minting analysis reads 202 input files. They are
third-party documents and data, most of them without an open license, so they
are not redistributed. `../fetch.py` downloads them again from their public
sources.

`manifest.json` is the manifest of the paper's snapshot, downloaded on
2026-10-03 between 21:46:01 and 22:16:01 UTC. For each file it records the id,
the path under `data/minting/`, the URL, the HTTP method and request body, the
final URL after redirects, the retrieval time (UTC), the HTTP status, the
content type, the Last-Modified header, the SHA-256, the size, the license and
a note. Its `failed_requests` list names four requests that returned no file,
among them the ICANN report for July 2026, which was not yet published and
which `fetch.py` does not request. `../SOURCES.md` shows the same inventory as
a table.

`analysis.py` finds every input through `manifest.json` and cannot run without
it. `fetch.py` replaces the entry of each file it downloads. Neither script
reads this README or lists `raw/`, except that `analysis.py` finds the ICANN
reports through the pattern `raw/icann_mrr/*/*.csv`.

The analysis supports Section 6.3 (Minting Economics and Exposure), the
paragraph "Parameters and minting" of Appendix D and single statements in
Sections 1, 3, 5.4, 7 and 8. `../derived/README.md` maps each output to the paper.

## What the downloads touch

- Documentation pages, policies and two arXiv papers.
- Public data files, namely the IANA TLD list, the Public Suffix List, Chrome's
  Certificate Transparency (CT) log list and 120 ICANN monthly registry
  reports.
- Porkbun's keyless pricing API, with one POST request whose body is `{}`.
- Five crt.sh lookups of platform apex wildcards (`*.github.io`,
  `*.vercel.app`, `*.netlify.app`, `*.pages.dev` and `*.web.app`), each for
  that exact identity and for unexpired certificates only.

No request resolves, probes or connects to a tenant name, a blocked name or a
proxy endpoint, and none uses an account, an API key or an approval.
`fetch.py` spaces its requests at least 2 s apart and its crt.sh lookups 20 s
apart. Its source list names 32 hosts, and redirects led to one more in the
snapshot. It contacts them from your address with the User-Agent string set in
`fetch.py` (`UA`).

## Requirements

- Python 3 with `requests` for `fetch.py`, and `pandas` and `matplotlib` for
  `analysis.py`.
- `pdftotext` from poppler-utils.
- `../../simulations/code/figstyle.py` and `paper.mplstyle`, which ship with
  the artifact.
- About 22 MB of disk for `raw/` and 1.6 MB for `../derived/doc_text/`.

The commands below were tested with Python 3.13.7, pandas 3.0.6,
matplotlib 3.10.1, numpy 2.2.4, requests 2.32.3 and pdftotext 25.03.0.

## 1. Save the paper's manifest

`fetch.py` rewrites the manifest entry of a file (SHA-256, size and retrieval
time) as soon as it downloads that file. Keep a copy of the shipped manifest
first. Run this in `data/minting/`.

```sh
cp raw/manifest.json manifest.paper.json
```

The copy sits next to `raw/`, and no script reads it.

## 2. Download

Run this in `data/minting/`. It needs network access.

```sh
python3 fetch.py
```

- `fetch.py` registers 205 requests, and 202 of them produced the snapshot's
  files. The spacing alone takes at least 8 minutes, and a crt.sh lookup can
  take several minutes (180 s timeout, two attempts). The retrieval times of
  the snapshot's 202 files (21.6 MB) span 30 minutes.
- A failed request prints `FAIL <id> <error>` and leaves the manifest entry of
  that id as it was. Running `python3 fetch.py` again retries only the ids
  whose file is missing.
- Three of the registered requests returned no file for the snapshot.
  `le_site_license_md` got HTTP 404, because the license file is
  `LICENSE.txt`, which `le_site_license_txt` fetches. The crt.sh lookups
  `crtsh_wild_vercel_app` and `crtsh_wild_pages_dev` got HTTP 504 and 502.
  Section 4 says what changes if they succeed on a new run.
- `--only <prefix>` (repeatable) limits a run to the ids that start with the
  prefix, and `--force` downloads files again although they are present. The
  ids are listed in `../SOURCES.md` (File inventory) and in `manifest.json`.
  For example

  ```sh
  python3 fetch.py --only porkbun_pricing --only iana_tlds
  python3 fetch.py --force --only chrome_log_list
  ```

- Do not run `python3 fetch.py --sync`. It is meant for changes to the list
  of sources in `fetch.py`. It moves files whose destination changed, deletes
  the files and manifest entries of ids that `fetch.py` no longer lists, and
  stops with `FileNotFoundError` at the first listed file that is missing.
- `python3 fetch.py --sources` makes no request. It rewrites `../SOURCES.md`
  from `manifest.json` and writes a new `updated_utc` into `manifest.json`.

## 3. Compare with the paper's snapshot

Run this in `data/minting/`.

```sh
python3 - <<'EOF'
import hashlib, json, os
ref = json.load(open("manifest.paper.json"))
bad = [e["path"] for e in ref["files"]
       if not os.path.exists(e["path"])
       or hashlib.sha256(open(e["path"], "rb").read()).hexdigest() != e["sha256"]]
print(len(ref["files"]) - len(bad), "identical,", len(bad), "changed or missing")
for path in bad:
    print(path)
EOF
```

On the paper's files it prints `202 identical, 0 changed or missing`.

- Inputs fixed by version can match. These are RFC 6962, 9162 and 9525, the
  Boulder and publicsuffix-go files at the commits pinned in `fetch.py`
  (`1578a1d051b87ded8f60f3af7f6e79f0da0a8d81` and
  `32ef0a9d3d18fb4d7e7af481a56f36263a4b2c43`), the 120 ICANN monthly reports
  (July 2024 to June 2026) unless ICANN posts a corrected month, and the two
  arXiv PDFs. The snapshot holds version 1 of both papers, while `fetch.py`
  asks arXiv for the current version.
- Live inputs usually differ (Section 4).

## 4. Live sources

Several inputs change over time, so a new download can give other values than
the paper. The shipped files in `../derived/` keep the paper's values.

| Input under `raw/` | Snapshot | Paper values that depend on it |
|---|---|---|
| `porkbun/porkbun_pricing.json` | retrieved 2026-10-03T21:46:19Z | cheapest first-year price $1.54 (26 TLDs), 36 TLDs under $2 |
| `registry/iana_tlds_alpha_by_domain.txt` | Version 2026100300 | the 543 ICANN TLDs behind the price statistics |
| `psl/public_suffix_list_canonical.dat` | VERSION 2026-10-01_23-02-52_UTC, COMMIT 6cd82aff889e3d64e5e03bc5c1f43da1934a960a | no paper value. A newer list changes the `psl_line`, `psl_version` and `psl_commit` columns of `../derived/psl_platform_suffixes.csv` |
| `ct/chrome_log_list_v3.json` | version 93.3, 2026-10-03T13:35:24Z | 43 usable or qualified static-ct-api logs with MMD 60 s and 21 RFC 6962 logs with MMD 86,400 s |
| `crtsh/` | 2026-10-03, 22:05 to 22:12 UTC | the `*.netlify.app` and `*.web.app` wildcard certificates |
| `docs/`, `platforms/`, `ct/` (pages) | 2026-10-03 | the quotes in `../facts.py` (Section 5) |

- The Porkbun numbers come from the keyless pricing API (POST to
  `https://api.porkbun.com/api/json/v3/pricing/get`). The paper's reference
  `porkbun_pricing` cites the public price page
  `https://porkbun.com/products/domains`.
- The snapshot's `*.web.app` certificate expires on 2026-10-18, its
  `*.github.io` certificates on 2026-10-31 and its `*.netlify.app`
  certificates on 2027-03-19, so later lookups return other certificates.
- If the crt.sh lookups of `*.vercel.app` or `*.pages.dev` succeed, their rows
  enter `../derived/crtsh_platform_wildcards.csv` and
  `../derived/summary.json`. `../derived/platform_names.csv` still says that
  those lookups failed, because `../analysis.py` writes that text as it is.
- Chrome's CT policy and log policy come from the master branch of the
  GoogleChrome/CertificateTransparency repository, and the C2SP static-ct-api
  text and the Sunlight README from the main branches of their repositories.
  The paper's reference `chrome_ct_policy` cites the rendered page of the same
  policy.
- publicsuffix.org serves only the current list, and the list asks to be
  pulled only from there.

## 5. When analysis.py stops on new downloads

`analysis.py` checks each of the 131 quotes in `../facts.py` against the text
of its page, and it stops with `quotes not found in raw sources: [...]` when a
quote is missing.

- `whoisds_next_day` quotes the WhoisDS table row of the list for 2026-10-02,
  so it fails on any later download.
- `le_rl_updated` ("Last updated: August 5, 2026"), `le_profiles_updated`
  ("Last updated: September 8, 2026") and `gts_quota_updated` ("Last updated
  2026-10-01 UTC") quote the date stamps of their pages, so they fail as soon
  as those pages are updated.
- Any other quote fails when the wording of its page changes.

Such a run writes `../derived/doc_text/` and `../derived/doc_facts.csv`, whose
`verified_in_raw` column shows the failing quotes, and stops before any other
output, so the other files in `../derived/` stay as they were. To analyze
new downloads, change each failing quote (and its value) in `../facts.py` to
the current text and keep its id, because the derived tables cite fact ids.
Some limits must also appear in their quotes, for example "300" and
"36 seconds" in `le_orders_per_account`, and `analysis.py` stops with an
`AssertionError` when such a number has changed. Only the numbers of
`../derived/acme_mint_rates.csv` are checked against their quotes. The limits
and texts of `../derived/platform_names.csv`, `minting_costs.csv` and
`exposure_channels.csv` are written in `../analysis.py` (`platform_table()`,
`minting_costs()` and `exposure_channels()`), so when such a quote changes,
change the matching text there too.

## 6. Manual download

`analysis.py` takes every input path from `manifest.json` and never checks
hashes, so it uses a file saved by other means at the path listed for its id.
Run this in `data/minting/` to print the id, path, method and URL of every
file.

```sh
python3 -c 'import json; [print(e["id"], e["path"], e["method"], e["url"]) for e in json.load(open("raw/manifest.json"))["files"]]'
```

- The Porkbun price list needs a POST with the body `{}` and the header
  `Content-Type: application/json`.
- Send the User-Agent string of `fetch.py`. The Vercel pages (`vercel_limits`,
  `vercel_urls`) and the Porkbun guides under `porkbun.com/llms/` arrived as
  Markdown (`text/markdown`), and the quotes in `../facts.py` match that text.
  A page saved from a browser as HTML can fail the quote check.
- Version 1 of the arXiv papers is at `https://arxiv.org/pdf/1809.08325v1` and
  `https://arxiv.org/pdf/2106.02167v1`.
- For a file saved by hand, `manifest.json` keeps the snapshot's SHA-256 and
  retrieval time, and `../derived/doc_facts.csv` copies them.

## Directory contents

| Under `raw/` | Files | Bytes | Contents | License |
|---|---|---|---|---|
| `porkbun/` | 1 | 82,548 | Porkbun's price list from its keyless pricing API | no license stated, factual prices, cite |
| `registry/` | 3 | 749,064 | IANA TLD list, ICANN base gTLD Registry Agreement and ICANN's page "About Zone File Access" | IANA and ICANN, cite |
| `icann_mrr/<tld>/` | 120 | 4,609,997 | ICANN monthly transaction reports of .xyz, .top, .shop, .online and .cfd, July 2024 to June 2026 | ICANN reports, cite, only Totals rows used |
| `psl/` | 1 | 334,734 | Public Suffix List | MPL-2.0 |
| `ct/` | 10 | 528,273 | Chrome's CT log list, RFC 6962, 9162 and 9525, Chrome's CT policy, log policy and repository license, Apple's CT policy, C2SP static-ct-api, Sunlight README | IETF Trust (RFCs), Apache-2.0 (Chrome policy repository), others cite |
| `lit/` | 4 | 2,561,050 | Scheitle et al. (arXiv 1809.08325) and Hoang et al. (arXiv 2106.02167), PDFs and abstract pages | arXiv non-exclusive license (Scheitle et al.), CC BY-NC-ND 4.0 (Hoang et al.) |
| `docs/` | 24 | 3,256,179 | Let's Encrypt documentation, blog posts and site license, Google Trust Services, ZeroSSL, Porkbun API guides, WhoisDS, OpenINTEL Zonestream, GH Archive, a Tor blog post and the WebTunnel bridge guide | MPL-2.0 (letsencrypt.org), CC BY 4.0 (two Google pages), others cite |
| `platforms/` | 32 | 9,396,353 | Documentation of GitHub, Cloudflare, Vercel, Netlify, Firebase, Deno Deploy, Fly.io, Render, AWS Lambda, Azure App Service and Cloud Run | CC BY 4.0 (Google pages), others cite |
| `code/` | 4 | 36,278 | Boulder `ratelimits/utilities.go` and publicsuffix-go `publicsuffix.go` at pinned commits, with their licenses | MPL-2.0 (Boulder), MIT (publicsuffix-go) |
| `crtsh/` | 3 | 1,494 | crt.sh results for `*.github.io`, `*.netlify.app` and `*.web.app` | CT data through crt.sh, cite |
| total | 202 | 21,555,970 | | |

The full license string of every file is in `manifest.json`. "Cite" means
that the file is cited and quoted briefly and not redistributed.

## Warnings

- Do not redistribute `raw/` or `../derived/doc_text/`, which holds the full
  text of the saved pages. Most of them are cite-only, and the Scheitle et al.
  PDF is under arXiv's non-exclusive license.
- Keep the crt.sh queries to exact identities. A pattern query (`%`) returns
  tenant names, which this analysis does not collect.
