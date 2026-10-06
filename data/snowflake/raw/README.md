# Snowflake inputs (`data/snowflake/raw/`)

This directory ships with only this README and `manifest.json`. The Snowflake
analysis behind Section 6.2, the Introduction's Snowflake numbers and the
Snowflake paragraph of Appendix D uses only existing public datasets and
documents. Several of them may not be redistributed, so the artifact ships
none of the raw files. `data/snowflake/fetch_raw.py` downloads them again from
the dataset hosts named below. It never resolves or contacts a front domain,
broker, STUN server, proxy or bridge.

`data/snowflake/raw/manifest.json` describes the 202 files the paper used
(30.7 MB, retrieved on 2026-10-03 between 21:46:47 and 21:53:23 UTC). Each
record gives the path below `data/snowflake/raw/`, the URL (for a git export,
the repository, commit and path), the retrieval time, the SHA-256 hash, the
size, the license and whether the file may be redistributed.
`data/snowflake/SOURCES.md` describes each source and repeats the per-file
table. `analysis.py` does not read the manifest.

## Download

The download needs Python 3 with `requests`, the `git` client and network
access. The paper's download took about seven minutes and wrote 30.7 MB, plus
temporary git clones. From the repository root, run

```
cd data/snowflake
cp raw/manifest.json manifest.paper.json
python3 fetch_raw.py --paper-commits --only collector tormetrics ioda gitlab lit
```

- `cp` keeps the paper's manifest as `data/snowflake/manifest.paper.json`,
  next to `raw/`. `fetch_raw.py` overwrites `raw/manifest.json` with the
  hashes of the files it downloads and rewrites the per-file table in
  `data/snowflake/SOURCES.md`. Records of files it does not download keep the
  paper's values, such as the four `github/` files with the command above and
  CollecTor `recent/` files that the index no longer lists.
- `--paper-commits` exports the timeline, rdsys-admin and snowflake
  repositories at the commits the paper used (see "Git sources"). Without it,
  the exports come from the current heads, and later commits to rdsys-admin
  or the timeline change the inputs.
- `--only` leaves out the optional `github` section. The command
  `python3 fetch_raw.py --only github` adds the two net4people/bbs issues,
  which `analysis.py` does not read.
- The script skips files that already exist (`--refresh` downloads them
  again). It always downloads the CollecTor index again, replaces an existing
  CollecTor file once if its SHA-256 disagrees with the index, and always
  clones and exports the git sources again.
- Requests are paced at least 1.5 s apart, with retries after HTTP 429, 502,
  503 and 504. No account or API key is needed. A CollecTor file that the
  index lists but the server no longer has is skipped. An HTTP 404 for any
  other URL stops the script with an error.
- The clones go to a temporary directory that is deleted at the end, or to
  `--clone-dir DIR` if given.

Then check the download as described in the next section and rebuild the
outputs as described in `data/snowflake/derived/README.md`.

## Check the download

This compares every file listed in `manifest.paper.json` with the files in
`raw/`. Run it from `data/snowflake/`.

```
python3 - manifest.paper.json <<'EOF'
import hashlib, json, sys
from collections import Counter
from pathlib import Path
ref = json.loads(Path(sys.argv[1]).read_text())
count = Counter()
for r in ref:
    p = Path("raw") / r["path"]
    if not p.exists():
        status = "MISSING"
    elif hashlib.sha256(p.read_bytes()).hexdigest() == r["sha256"]:
        status = "OK"
    else:
        status = "DIFFERS"
    count[status] += 1
    if status != "OK":
        print(status, r["path"])
print(dict(count), "of", len(ref), "files")
EOF
```

On the paper's files it prints `{'OK': 202} of 202 files`. Several sources are
live, so a new download differs in the following places. Paths are relative to
`data/snowflake/raw/`.

| Files | Status on a new download | Reason |
|---|---|---|
| `collector/recent/*-snowflake-stats` (4 files) | MISSING | CollecTor keeps `recent/` files for about three days. |
| `ioda/*.json` (32 files) | DIFFERS | Every response records its request and response times under `metadata`. The events can change too. |
| `tormetrics/*.csv` (5 files) | DIFFERS | The paper's files end on 2026-10-01. A new download also has 2026-10-02 and 2026-10-03, and Tor Metrics can recompute past estimates. |
| `collector/index.json.xz` | can differ | CollecTor updates its index as files arrive. |
| `collector/archive/snowflakes-2026-09.tar.xz`, `snowflakes-2026-10.tar.xz` | can differ | These months were incomplete on 2026-10-03. |
| `gitlab/tor/*` (2 files) | can differ | The shallow clone always uses the current head of branch `release-0.4.8`. |
| `gitlab/snowflake/commit_*.patch` (4 files) | can differ | `git show` output can change with the git version. |
| `gitlab/metrics-timeline/*`, `gitlab/rdsys-admin/*`, `gitlab/snowflake/*` | can differ without `--paper-commits` | The exports then come from the current heads. |
| `lit/chen2026_arxiv2609.12242.pdf` | can differ | The unversioned arXiv URL serves the latest version. The paper used version 2. |
| `lit/chen2026_arxiv2609.12242_abs.html` | can differ | Live page. |
| `github/*.json` (4 files) | MISSING, or can differ | The command above does not fetch them. Live issue pages. |

The other files come from fixed sources, namely the 87 CollecTor archives from
2019-06 to 2026-08, the Bocovich et al. PDF and, with `--paper-commits`, the
other timeline, rdsys-admin and snowflake exports, which come from fixed
commits.

Effects on the paper's numbers, which the shipped files in
`data/snowflake/derived/` keep.

- The paper's broker numbers use windows with fixed dates. In the paper's
  download, the window that ends 2026-10-03 20:18:16 UTC, one of the six
  behind the 148,719 proxy addresses, came only from
  `collector/recent/2026-10-03-21-16-48-snowflake-stats`. A later download can
  obtain it only from `snowflakes-2026-10.tar.xz`. Without it, the median for
  2026-09-28 to 2026-10-03 rests on five windows.
- `analysis.py` reads every CollecTor archive present, including months after
  2026-10. They do not enter the fixed-date periods, but they change the
  `year_2026` row of `sf_proxy_ips_summary.csv`, the window counts in
  `summary.json` and the full-length tables.
- IODA screens shutdown days only in the per-country series. Its first event
  is on 2022-01-26, after the Turkmenistan window of October 2021, and the
  worldwide series behind the Fastly numbers is not screened by country. In
  the paper's download the shutdown screen excluded no day around either
  event. The broker numbers do not use the screen.
- The rdsys-admin export determines 48 versions, 19 rendezvous names
  introduced and 11 retired. The timeline export determines which days the
  timeline marks as shutdowns. `--paper-commits` pins both.

## What goes where

Paths are relative to `data/snowflake/raw/`. "Read" says whether `analysis.py`
opens the file.

| Path | Files | Size | Source | License | Read | Paper numbers that depend on it |
|---|---|---|---|---|---|---|
| `collector/archive/snowflakes-YYYY-MM.tar.xz` | 89 (2019-06 to 2026-10) | 3.4 MB | Tor CollecTor | CC0 | yes | 148,719 proxy addresses, Fastly HTTP polls -85.8% and proxy addresses -2.1%, 36 days |
| `collector/recent/YYYY-MM-DD-HH-MM-SS-snowflake-stats` | 4 | 21 KB | Tor CollecTor | CC0 | yes | the window ending 2026-10-03, one of the six behind 148,719 |
| `collector/index.json.xz` | 1 | 0.3 MB | Tor CollecTor | CC0 | no | none (file list and SHA-256 values for `fetch_raw.py`) |
| `tormetrics/userstats-bridge-combined_{ru,ir,cn,tm}.csv` | 4 | 2.0 MB | Tor Metrics | CC0 | yes | Turkmenistan users 28 to 2, and the coverage (`frac`) screen of every user series |
| `tormetrics/userstats-bridge-transport_all.csv` | 1 | 0.5 MB | Tor Metrics | CC0 | yes | Fastly users -32.5% |
| `ioda/outage_events_{IR,RU,CN,TM}_{2019..2026}.json` | 32 | 0.2 MB | IODA API v2 | all rights reserved | yes, required | IODA events from 2022-01-26 (Appendix D) |
| `gitlab/metrics-timeline/README.md`, `COPYING` | 2 | 0.26 MB | Tor Metrics timeline (git) | CC0 | `README.md`, required | shutdown days in the screen |
| `gitlab/rdsys-admin/circumvention_log.tsv`, `circumvention/*.json` | 1 + 48 | 0.24 MB | rdsys-admin (git) | no license | yes, required for `summary.json` | 48 versions, 19 names introduced and 11 retired |
| `gitlab/rdsys-admin/circumvention_defaults_log.tsv`, `circumvention_defaults/*.json` | 1 + 2 | 1 KB | rdsys-admin (git) | no license | no | none |
| `gitlab/snowflake/` (`broker-spec.txt`, `ChangeLog`, `LICENSE`, `broker_metrics_log.tsv`, 4 commit patches) | 8 | 0.1 MB | snowflake (git) | BSD-3-Clause | no | none (documents the dates hard-coded in `analysis.py`) |
| `gitlab/tor/ReleaseNotes_release-0.4.8`, `LICENSE_release-0.4.8` | 2 | 1.6 MB | tor (git) | BSD-3-Clause | no | none |
| `github/net4people_bbs_issue{197,603}.json`, `..._comments.json` | 4 | 80 KB | GitHub REST API | no license | no | none |
| `lit/bocovich2024_usenixsec24.pdf` | 1 | 1.2 MB | USENIX Security 2024 | authors' copyright | yes, quote checks | about 20 hours, the Turkmenistan block lasting months, the DTLS block (Section 3) |
| `lit/chen2026_arxiv2609.12242.pdf` | 1 | 20.6 MB | arXiv 2609.12242v2 | arXiv license | yes, quote checks | none |
| `lit/chen2026_arxiv2609.12242_abs.html` | 1 | 43 KB | arXiv abstract page | arXiv | no | none |

The quote checks run `pdftotext` and `pdfinfo` from Poppler (package
`poppler-utils` on Debian and Ubuntu). Without Poppler or without the PDFs,
`analysis.py` still runs and marks every quote in `churn_published.csv` as not
found.

## Sources and manual downloads

`fetch_raw.py` finds and `analysis.py` reads files by the names below. A file
saved by hand under its name is used as is, because `fetch_raw.py` skips
existing files, except that it checks CollecTor files against the index.

### Tor CollecTor (`--only collector`)

`fetch_raw.py` downloads `https://collector.torproject.org/index/index.json.xz`
and then every file the index lists under `archive/snowflakes/` and
`recent/snowflakes/`, and compares each file's SHA-256 with the index. By hand,
save each monthly archive
`https://collector.torproject.org/archive/snowflakes/snowflakes-YYYY-MM.tar.xz`
(2019-06 to 2026-10) in `collector/archive/`. `collector/recent/` may stay
empty. `analysis.py` keeps one copy of each broker window, so a window present
both in an archive and in `recent/` counts once.

### Tor Metrics (`--only tormetrics`)

| URL | Saved as |
|---|---|
| `https://metrics.torproject.org/userstats-bridge-combined.csv?start=2019-01-01&end=2026-10-03&country=ru` | `tormetrics/userstats-bridge-combined_ru.csv` |
| `https://metrics.torproject.org/userstats-bridge-combined.csv?start=2019-01-01&end=2026-10-03&country=ir` | `tormetrics/userstats-bridge-combined_ir.csv` |
| `https://metrics.torproject.org/userstats-bridge-combined.csv?start=2019-01-01&end=2026-10-03&country=cn` | `tormetrics/userstats-bridge-combined_cn.csv` |
| `https://metrics.torproject.org/userstats-bridge-combined.csv?start=2019-01-01&end=2026-10-03&country=tm` | `tormetrics/userstats-bridge-combined_tm.csv` |
| `https://metrics.torproject.org/userstats-bridge-transport.csv?start=2019-01-01&end=2026-10-03` | `tormetrics/userstats-bridge-transport_all.csv` |

### IODA outage events (`--only ioda`)

IODA's data are copyright Georgia Tech Research Corporation, all rights
reserved. The analysis fetches them only to build the shutdown-day masks that
screen the per-country user series. Cite IODA and do not redistribute the
responses. The script sends one request per country and calendar year, 32 in
total, to

```
https://api.ioda.inetintel.cc.gatech.edu/v2/outages/events?entityType=country&entityCode=<CC>&from=<FROM>&until=<UNTIL>&limit=2000
```

with `<CC>` in IR, RU, CN and TM, and saves each response as
`ioda/outage_events_<CC>_<YEAR>.json`. The Unix times are the following.

| Year | from | until |
|---|---|---|
| 2019 | 1546300800 | 1577836800 |
| 2020 | 1577836800 | 1609459200 |
| 2021 | 1609459200 | 1640995200 |
| 2022 | 1640995200 | 1672531200 |
| 2023 | 1672531200 | 1704067200 |
| 2024 | 1704067200 | 1735689600 |
| 2025 | 1735689600 | 1767225600 |
| 2026 | 1767225600 | 1791072000 |

On 2026-10-03 the API returned 848 events, the first starting on 2022-01-26
22:40 UTC. A new download never has the paper's SHA-256 values. Compare
`ioda.n_events` and `ioda.first_event` in the rebuilt `summary.json` with the
shipped values instead.

### Git sources (`--only gitlab`)

`fetch_raw.py` clones four public repositories and writes the files with
`git show <commit>:<path>`.

| Repository | Commit with `--paper-commits` | Exported to |
|---|---|---|
| `https://gitlab.torproject.org/tpo/network-health/metrics/timeline.git` | `e193b45c8be5b86810638d50f753cd409f052d48` | `gitlab/metrics-timeline/README.md`, `COPYING` |
| `https://gitlab.torproject.org/tpo/anti-censorship/rdsys-admin.git` | `0061ce86ee2dfc8c451a78d28d0ef09e4ed7f36e` | `gitlab/rdsys-admin/` |
| `https://gitlab.torproject.org/tpo/anti-censorship/pluggable-transports/snowflake.git` | `9850fbe31535ea0fde39ff9f12970c3c1ee808d3` | `gitlab/snowflake/` |
| `https://gitlab.torproject.org/tpo/core/tor.git` | current head of `release-0.4.8` (the paper's was `6a82e897be51c855b6a4b46359e00ce962c45d2a`) | `gitlab/tor/` |

- `--paper-commits` runs `git checkout --detach <commit>` after each of the
  first three clones. The commits are in `PAPER_COMMITS` in `fetch_raw.py`.
  The tor clone is shallow (`--depth 1 --filter=blob:none`) and cannot be
  pinned. `analysis.py` does not read it.
- For rdsys-admin, the script lists the history of
  `conf/circumvention.json` with the command below and writes one row per
  commit to `gitlab/rdsys-admin/circumvention_log.tsv`, with the columns
  `commit`, `author_date`, `commit_date`, `status`, `path`, `subject` and
  `exported_as`. It saves each version as
  `gitlab/rdsys-admin/circumvention/<commit time in UTC as YYYYmmddTHHMMSSZ>_<first 10 hex digits of the commit>.json`,
  and does the same for `conf/circumvention_defaults.json`.
  `analysis.py` reads only the versions listed in `circumvention_log.tsv`. The
  paper's file has 48 rows (2022-02-25 to 2026-03-18) and SHA-256
  `1d9ee880b35b29d7e5991a91e54ce65b3d1ec179095eeffebf4053d070c5a7f3`.
- For snowflake, it exports `doc/broker-spec.txt`, `ChangeLog` and `LICENSE`,
  the commits `c8b0b31`, `31f879a`, `b512e24` and `26ceb6e` as
  `commit_<10 hex digits>.patch` (`git show --format=fuller`), and the log of
  `broker/metrics.go`, `broker/amp.go` and `broker/ipc.go` as
  `broker_metrics_log.tsv`.
- The timeline export `README.md` holds the dated event table. The paper's
  file has SHA-256
  `84a1aa20e2c9e9c33cd7c72834513c5d9fc84f553a1894671577267c664472cc`.

The rdsys-admin history command, run inside the clone, is

```
git log --follow --format=COMMIT%x09%H%x09%aI%x09%cI%x09%s --name-status -- conf/circumvention.json
```

The exports have no simpler manual route. Use
`python3 fetch_raw.py --only gitlab --paper-commits`, which needs Python 3 with
`requests`, git and network access.

### Publications (`--only lit`)

| URL | Saved as | SHA-256 of the paper's copy |
|---|---|---|
| `https://www.usenix.org/system/files/usenixsecurity24-bocovich.pdf` | `lit/bocovich2024_usenixsec24.pdf` | `78fbe6e4d688a79bbb8d10f372fba2c51ca3839efe97995c62517850ba553110` |
| `https://arxiv.org/pdf/2609.12242` (the paper's copy is version 2, which this URL served on 2026-10-03 and `https://arxiv.org/pdf/2609.12242v2` always serves) | `lit/chen2026_arxiv2609.12242.pdf` | `e84f2fe8d9e96c92cd7262678df12edd8cf69dba71951786f49d18e7ef70deea` |
| `https://arxiv.org/abs/2609.12242` | `lit/chen2026_arxiv2609.12242_abs.html` | live page |

To use version 2 of the arXiv PDF, save it from the versioned URL under its
name before running `fetch_raw.py`, which then keeps it.

### net4people/bbs issues (`--only github`, optional)

`https://api.github.com/repos/net4people/bbs/issues/197` and `.../issues/603`,
each with `/comments?per_page=100`, saved as
`github/net4people_bbs_issue<N>.json` and
`github/net4people_bbs_issue<N>_comments.json`. They document event dates that
`analysis.py` hard-codes. These are 4 unauthenticated calls.

## If an input is missing

`analysis.py` writes its outputs in a fixed order. First come the five `sf_*`
tables, then the two mask tables, the IODA long-event table and the timeline
extract, the four event tables, the six `rdsys_*` tables,
`churn_published.csv`, `summary.json` and the optional figure.

| Missing input | Effect on `python3 analysis.py` |
|---|---|
| every file in `collector/` | stops at once and writes nothing |
| some CollecTor months | runs, and numbers that use those months change without warning |
| any `tormetrics/` CSV, every `ioda/` file, or `gitlab/metrics-timeline/README.md` | writes the five `sf_*` tables, then stops with an error |
| `gitlab/rdsys-admin/circumvention_log.tsv` or a JSON file it lists | writes 13 tables, then stops before the `rdsys_*` tables, `churn_published.csv` and `summary.json` |
| `lit/*.pdf`, or Poppler's `pdftotext` and `pdfinfo` | runs, and `churn_published.csv` marks every quote as not found |
| `gitlab/snowflake/`, `gitlab/tor/`, `github/`, `collector/index.json.xz` | no effect |

## Safety and licensing

- Do not resolve, probe or connect to the front domains, AMP front, SQS
  host, STUN servers or broker names in the exported files. The analysis
  needs no connection to them, and `fetch_raw.py` makes none.
- Some rdsys-admin versions contain the client credentials that Tor
  publishes for Snowflake's SQS rendezvous. `analysis.py` reads only methods
  and host names and never copies the credentials. Do not use them or
  redistribute the exported files.
- IODA data are all rights reserved. rdsys-admin has no license file. The
  GitHub issues are user posts without a license and carry user names. The
  two publications are copyrighted. `manifest.json` marks these 91 files
  `"redistribute": false`. Keep the downloaded files and
  `manifest.paper.json` out of any public copy of this repository.
- CollecTor, Tor Metrics and the timeline are CC0, and the snowflake and tor
  exports are BSD-3-Clause. The four commit patches of the snowflake export
  and the tor release notes name people, some with e-mail addresses, so keep
  them out of a public copy too. The analysis identifies commits by hash and
  date, never by author.
