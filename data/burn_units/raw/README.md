# Raw inputs of the burn-units analysis

In the artifact this directory holds only this README and `manifest.json`. The 64 input
files behind Table 1 and Section 6.1 are third-party data and are not included. For each
of them `manifest.json` records the URL, the retrieval time (all on 2026-10-03, UTC), the
SHA-256 hash, the size, the license and notes. For the registry extracts it also records
the hash and size of every upstream file they were filtered from and the first line of
the dump, which carries its date.
`../fetch.py` downloads every input again from its public source, and `../analysis.py`
then rebuilds `../derived/` offline. The shipped files in `../derived/` already hold the
paper's numbers, as `../derived/README.md` explains.

No step measures a network target. Every request goes to a public dataset API or file
host (the GFWatch dashboard, the OONI API, GitHub, GitLab, Zenodo, Tranco and
antifilter.download), no blocked name is resolved or contacted, and requests to one host
are at least 2 seconds apart.

## Handling the Russian registry data

Three inputs come from Roskomnadzor's blocking registry or from a list derived from it,
namely `zi/`, `zi_history/` and `antifilter/domains_platform_extract.lst`. The upstream
files behind them, the dumps in the `zapret-info/z-i` mirror and the `domains.lst` of
antifilter.download, list the names, URLs and addresses under blocking orders, some of
them for content that is illegal, some of it in every jurisdiction.

- Get these inputs only through the filter in `fetch.py`, with the steps `zi`,
  `zi_history` and `antifilter`, or with the manual route for the three single-file
  dumps below. Each step streams the upstream files into a scratch directory and records
  their SHA-256 and size. It then keeps only the entries whose domain or URL host lies
  under one of the 19 platform suffixes and deletes the upstream files. The registry
  extracts keep platform, field, host name and decision date, and the antifilter extract
  keeps only the matching host names of `domains.lst`, one per line. No URL path is
  kept.
- Never open the upstream files or the extracts in a browser or an editor, and never
  resolve, visit or fetch any name or URL in them.
- Set `BURN_UNITS_SCRATCH` to a private local directory before you run these steps, as
  shown below. Without it the scratch directory is `blockamole_burn_units` in the system
  temporary directory, where other users of the machine may be able to read it.
- The steps do not clean up after an interruption. If `zi`, `zi_history` or `antifilter`
  stops early, for example on a network error or Ctrl-C, delete the full files it left in
  scratch at once with
  `rm -f "${BURN_UNITS_SCRATCH:?}"/zi_*dump*.csv "${BURN_UNITS_SCRATCH:?}"/antifilter_domains.lst`.
  Then run `python3 fetch.py verify`, delete any extract it reports with `SHA MISMATCH`,
  because a step skips an extract that exists and has a manifest entry, and run the step
  again.
- Do not clone the z-i repository or check out its files. A clone keeps every full dump
  in its object store. `fetch.py` downloads only the pinned files it needs.
- The extracts kept in `raw/` still name individual hosts that the registry lists. Keep
  them private, and never publish, upload or commit them. The paper and the artifact
  report registry content only as aggregates, namely counts and dates per platform.
- `analysis.py` also writes `../derived/ooni_platform_domains.csv`, which lists every
  host name under the 19 suffixes that OONI measured, some of them on the registry. The
  artifact does not include it. Do not publish it either.

## Requirements

- Python 3 with numpy, pandas, matplotlib and requests. The paper's run used Python
  3.13.7, numpy 2.2.4, pandas 3.0.6, Matplotlib 3.10.1 and requests 2.32.3.
- `git` (2.51.0 in the paper's run), used by `fetch.py gfwlist` and by `analysis.py`.
- Linux or macOS. `fetchlib.py` locks the manifest with `fcntl`, which Windows lacks.
- Disk space. `raw/` takes 423 MB. While the registry steps run, scratch holds up to
  240 MB of upstream files, plus the 94 MB gfwlist clone. The downloads total about
  1.4 GB, of which 0.94 GB are registry dumps and antifilter's list, deleted after
  filtering.

## Rebuild `raw/`

Run these commands in `data/burn_units`. In the paper's run the 19 GFWatch lookups took
13 minutes, the three registry steps about 6 minutes together and every other step a few
minutes at most.

```sh
cp raw/manifest.json manifest.paper.json      # keep the paper's manifest
export BURN_UNITS_SCRATCH="$HOME/burn_units_scratch"
mkdir -p "$BURN_UNITS_SCRATCH" && chmod 700 "$BURN_UNITS_SCRATCH"

python3 fetch.py gfwatch          # 19 lookups, about 40 s each
git clone --bare https://github.com/gfwlist/gfwlist "$BURN_UNITS_SCRATCH/gfwlist.git"
git -C "$BURN_UNITS_SCRATCH/gfwlist.git" update-ref refs/heads/master 39e9bcede210515011621dae37b20c16b6d16ed8
git -C "$BURN_UNITS_SCRATCH/gfwlist.git" rev-parse HEAD     # must print 39e9bce...
python3 fetch.py gfwlist          # bundles the pinned clone, no download
python3 fetch.py ooni
python3 fetch.py ooni_azurefd
python3 fetch.py ooni_raw
python3 fetch.py irblock          # ends with two "md5 ... OK" lines
python3 fetch.py antifilter       # registry-derived, see the handling rules
python3 fetch.py zi               # registry, see the handling rules
python3 fetch.py zi_history       # registry, see the handling rules
python3 fetch.py qualitative
python3 fetch.py tranco
# Public Suffix List: the pinned copy, see "Public Suffix List" below
python3 fetch.py verify
```

Then rebuild the outputs and delete the scratch directory, which still holds the gfwlist
clone.

```sh
cp -r derived derived.paper       # optional, keeps the shipped outputs
python3 analysis.py               # offline, about 2 minutes, overwrites derived/
rm -rf "${BURN_UNITS_SCRATCH:?}"
```

- `cp raw/manifest.json manifest.paper.json` must come first. Each download replaces
  the manifest entry of its file with the hash of your copy, so the copy outside `raw/`
  is the only record of the paper's hashes left after a run. Keep it next to `raw/`, not
  inside it, because `fetch.py verify` reports every unlisted file in `raw/`.
- A step skips a file that exists in `raw/` and has a manifest entry, so you can run a
  step again after an error. Lines that start with `FAILED` mean a file is missing. Run
  that step again, for GFWatch with the suffix alone, as in
  `python3 fetch.py gfwatch workers.dev`.
- `python3 fetch.py verify` reports files that are missing, files that are not in the
  manifest and files whose SHA-256 differs from their entry. Before any download it
  prints `verify: 64 manifest entries; 64 problems`, one `MISSING FILE` per input.
  After a complete run it prints `verify: 64 manifest entries; 0 problems`. It checks
  each file that `fetch.py` downloaded against the hash of your download, and each file
  saved by hand against the paper's hash, because only `fetch.py` records a download in
  the manifest. Compare the downloads with the paper's copy as described under "Check
  your copy against the paper's".
- Put no other files into `raw/` or its subdirectories. `verify` reports them, and
  `analysis.py` reads every `ooni/agg_<CC>_<since>_<until>_domain.json`,
  `zi/extract_*.csv`, `zi_history/extract_*.csv` and `tranco/tranco_*_top1m.csv` it
  finds. A file at a path that the manifest lists, such as `irblock/README.md` (the
  IRBlock artifact's own README), stops `fetch.py` from downloading that path.
- Do not run `python3 fetch.py sources`. It rewrites the file table at the end of
  `../SOURCES.md` from your manifest.
- Do not pass extra windows to `python3 fetch.py ooni`. The files they create change the
  OONI counts.

## What goes where

| path under `raw/` | files | step | bytes | license | read by `analysis.py` |
|---|---:|---|---:|---|---|
| `gfwatch/lookup_<suffix>.json`, dots in the suffix written `_` | 19 | `gfwatch` | 89,278,792 | none stated, cite, do not redistribute | yes |
| `gfwlist/gfwlist.bundle` | 1 | `gfwlist` | 93,933,444 | LGPL-2.1 | yes |
| `ooni/agg_<CC>_<since>_<until>_domain.json` | 7 | `ooni` | 73,877,641 | CC BY-NC-SA 4.0 | yes |
| `ooni/agg_CN_azurefd40_<since>_<until>_day_domain.json` | 2 | `ooni_azurefd` | 540,915 | CC BY-NC-SA 4.0 | yes |
| `ooni/raw_<measurement uid>.json` | 5 | `ooni_raw` | 147,811 | CC BY-NC-SA 4.0 | yes |
| `ooni/list_*.json` | 3 | `ooni_raw` | 19,599 | CC BY-NC-SA 4.0 | no, they record how the 5 measurements were picked |
| `irblock/blocked_domains.tar.gz` | 1 | `irblock` | 69,389,814 | CC BY 4.0 | yes |
| `irblock/README.md`, `irblock/zenodo_record_15572895.json` | 2 | `irblock` | 15,919 | CC BY 4.0 | no |
| `zi/extract_2025-10-01_9133e4327b.csv` | 1 | `zi` | 1,013,323 | none, do not redistribute | yes |
| `zi_history/extract_<date>_<commit>.csv` | 6 | `zi_history` | 2,954,674 | none, do not redistribute | yes |
| `antifilter/domains_platform_extract.lst` | 1 | `antifilter` | 558,671 | none stated, do not redistribute | yes |
| `antifilter/community_domains.lst` | 1 | `antifilter` | 7,351 | none stated | yes |
| `antifilter/index.html`, `antifilter/community_index.html` | 2 | `antifilter` | 23,804 | none stated | no |
| `tranco/tranco_<date>_<list id>_top1m.csv` | 4 | `tranco` | 90,099,905 | none stated, free for research, cite | yes |
| `tranco/tranco_<date>_meta.json` | 4 | `tranco` | 1,676 | as above | no |
| `psl/public_suffix_list.dat` | 1 | `psl` or by hand | 334,645 | MPL-2.0 | yes |
| `qualitative/tor_gitlab_40064_discussions.json`, `qualitative/net4people_bbs_133.html`, `qualitative/net4people_bbs_417.html` | 3 | `qualitative` | 931,584 | none stated, cite, quote briefly | yes |
| `qualitative/tor_gitlab_40064_issue.json` | 1 | `qualitative` | 2,309 | as above | no |
| `manifest.json` | 1 | every step | 83,205 | | yes, for the dump dates |

`analysis.py` names each registry snapshot after the first date in the `upstream_header`
field of its manifest entry, for example `Updated: 2021-12-31 16:42:00 +0000`. The
shipped manifest holds this field for all seven extracts, and `fetch.py` writes it again.
Without it the six history snapshots take the date in their file name, one day later.
Every snapshot date before 2025-10-01 in `../derived/` then moves one day later, in
`ru_registry_timeseries.csv`, the `reg_*_snapshot_*` columns, the Russian `first_date`,
`suffix_date` and `notes` and `burn_units_evidence_long.csv`, while the decision dates
and Table 1 stay the same, and the snippet in `../derived/README.md` stops with a
`KeyError`. Without `manifest.json` at all, `analysis.py` stops.

## Sources and pins

### GFWatch, China, DNS filtering (`gfwatch/`)

Hoang et al., How Great is the Great Firewall? Measuring China's DNS Censorship, USENIX
Security 2021. The public dashboard at https://gfwatch.org lists the names that China
blocked by DNS from 2020-03-20 until its public data were frozen on 2024-09-06.
`fetch.py gfwatch` sends one `POST https://gfwatch.org/_dash-update-component` per
suffix, the dashboard's censored-domain lookup, with the regular expression
`(^|[.])<suffix>$` in which each dot is written `[.]`, for example
`(^|[.])github[.]io$`. The full JSON body of each request is in the manifest under
`request_payload`. The lookups for `run.app`, `on.aws`, `trycloudflare.com` and `r2.dev`
return "not found", and their files of about 260 bytes must exist all the same.

To get one file by hand, replay the stored request in `data/burn_units`, or run the
lookup on https://gfwatch.org and save the JSON answer of the `_dash-update-component`
request from the browser's developer tools.

```sh
python3 - <<'EOF'
import json, os, requests
rel = "gfwatch/lookup_github_io.json"
payload = json.load(open("manifest.paper.json"))["files"][rel]["request_payload"]
r = requests.post("https://gfwatch.org/_dash-update-component", json=payload, timeout=300)
r.raise_for_status()
os.makedirs("raw/gfwatch", exist_ok=True)
open("raw/" + rel, "wb").write(r.content)
EOF
```

The dashboard states no license. Cite Hoang et al. and do not redistribute the responses.

### gfwlist (`gfwlist/`)

The community proxy list at https://github.com/gfwlist/gfwlist (LGPL-2.1), kept as a git
bundle with its full history. The paper's snapshot is commit
`39e9bcede210515011621dae37b20c16b6d16ed8` of 2026-10-02 13:31:39 UTC. `fetch.py gfwlist`
clones into `$BURN_UNITS_SCRATCH/gfwlist.git` only if that directory does not exist, so
after the `git clone` and `git update-ref` commands above it bundles the pinned history.
If `update-ref` fails, the pinned commit is no longer on GitHub, and the gfwlist outputs
change. No number in the paper uses them, but `analysis.py` stops without the bundle.
Two bundles of the same history can differ in their bytes, so compare the `git_head`
field in the manifest, not the hash. `analysis.py` unpacks the bundle into a temporary
`.tmp_gfwlist_*` directory inside `data/burn_units` and deletes it at the end.

### OONI, China, Iran and Russia (`ooni/`)

Open Observatory of Network Interference, CC BY-NC-SA 4.0. Derived files with OONI
numbers carry the same license.

- `python3 fetch.py ooni` calls the aggregation API once per window as
  `https://api.ooni.io/api/v1/aggregation?probe_cc=<CC>&test_name=web_connectivity&since=<since>&until=<until>&axis_x=domain`
  and saves `ooni/agg_<CC>_<since>_<until>_domain.json`. China has three monthly windows
  from 2026-07-01 to 2026-10-01. Iran and Russia have two windows each, 2024-10-01 to
  2025-10-01 and 2025-10-01 to 2026-10-01. `until` is exclusive.
- `python3 fetch.py ooni_azurefd` gets day-level counts for the impairment of Azure Front
  Door names in China, with `axis_x=measurement_start_day`, `axis_y=domain` and `domain`
  set to the 40 names frozen in `fetch.py` as `OONI_AZUREFD_CN` (39 endpoints and their
  zone apex), for 2025-07-01 to 2026-05-01 and 2026-05-01 to 2026-10-01.
- `python3 fetch.py ooni_raw` gets the five published raw measurements listed in
  `fetch.py` as `OONI_RAW_UIDS` from `https://api.ooni.io/api/v1/raw_measurement`, and
  the three measurement lists from `https://api.ooni.io/api/v1/measurements` that
  record how they were picked.

By hand, request the URL that the paper's manifest records for each file. This prints
them.

```sh
python3 -c "import json; m = json.load(open('manifest.paper.json'))['files']; [print(k, m[k]['url']) for k in sorted(m) if k.startswith('ooni/')]"
```

Save each answer under its path in `raw/`, for example with
`curl -sSfL --create-dirs '<url>' -o raw/<path>`. If `api.ooni.io` stops answering,
OONI's API documentation gives the current base URL.

### IRBlock, Iran, DNS and HTTP filtering (`irblock/`)

Tai, Sengottuvelavan, Whiting and Hoang, USENIX Security 2025. Zenodo record 15572895,
doi:10.5281/zenodo.15572895, CC BY 4.0. The record lists the names found blocked on at
least 3 days by scans from outside Iran between November 2024 and 2025-01-15.
`fetch.py irblock` saves `https://zenodo.org/api/records/15572895` as
`irblock/zenodo_record_15572895.json` and
`https://zenodo.org/api/records/15572895/files/<name>/content` for `README.md` and
`blocked_domains.tar.gz`, then checks both md5 sums against the record. By hand, download
the two files from https://zenodo.org/records/15572895 into `irblock/`. `analysis.py`
reads five members of the archive, all under `blocked_domains/`, namely
`dns_censored_fqdn.txt.gz`, `http_censored_fqdn.txt.gz`,
`dns_censored_apex_domains.txt.gz`, `http_censored_apex_domains.txt.gz` and
`apex_domain_categories.csv.gz`. The per-day IP archives and `blocked_ips.tar.gz` are not
needed.

### Russian registry, zapret-info mirror (`zi/` and `zi_history/`)

Roskomnadzor's registry of blocked resources as mirrored at
https://github.com/zapret-info/z-i. The repository has no license file, and the registry
is public in Russia under Government Decree No. 1101. The mirror stopped updating after
the dump of 2025-10-01. The commits are pinned in `fetch.py` (`ZI_COMMIT` and
`ZI_HISTORY`), and each history snapshot is the last commit before the date in its file
name. `fetch.py` streams each file from
`https://raw.githubusercontent.com/zapret-info/z-i/<commit>/<file>` as the handling rules
describe.

| extract | commit | upstream files | first line of the dump | upstream bytes | lines | rows kept |
|---|---|---|---|---:|---:|---:|
| `zi_history/extract_2022-01-01_d291c7d7d7.csv` | `d291c7d7d7e406fbd8d08b1c9413a4ebb51fc42a` | `dump.csv` | Updated: 2021-12-31 16:42:00 +0000 | 92,609,391 | 548,880 | 3,191 |
| `zi_history/extract_2023-01-01_9e1f59db33.csv` | `9e1f59db3360f5caaaf8ebde0581e867b7fff4c8` | `dump.csv` | Updated: 2022-12-31 16:46:00 +0000 | 96,085,709 | 621,039 | 5,471 |
| `zi_history/extract_2024-01-01_99aec91c81.csv` | `99aec91c810505e9b60129cc70c0f8c58411a11c` | `dump.csv` | Updated: 2023-12-31 11:25:03 +0000 | 96,734,011 | 541,641 | 7,024 |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | `94b080bebc7338dcbb6045ad6147656a1db974e3` | `dump-00.csv` to `dump-19.csv` | Updated: 2024-05-06 16:30:03 +0000 | 111,337,880 | 632,016 | 8,845 |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | `b6429c7268a249f0cad7663b3ac6b2bd91b67e09` | `dump-00.csv` to `dump-19.csv` | Updated: 2024-05-09 14:15:02 +0000 | 111,944,318 | 635,045 | 8,897 |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | `1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b` | `dump-00.csv` to `dump-19.csv` | Updated: 2024-12-31 12:05:02 +0000 | 159,597,912 | 891,700 | 12,254 |
| `zi/extract_2025-10-01_9133e4327b.csv` | `9133e4327bbcf9adc1cba24360f50e50a6b4d11c` | `dump-00.csv` to `dump-19.csv` | Updated: 2025-10-01 10:25:04 +0000 | 239,271,417 | 1,203,340 | 15,639 |

- Each extract is a CSV with the columns `platform`, `field`, `value` and
  `decision_date`. `field` is `domain` or `url_host`, and `value` is a lower-case host
  name, with the leading `*.` of a registry mask kept. `decision_date` is the date of the
  registry decision, which can predate the platform, so the analysis dates each entry by
  the first snapshot that lists it.
- The manifest holds the SHA-256 of every upstream file, under `upstream_files`, or under
  `upstream_sha256` for the three single-file dumps of the paper's run. The filter is
  deterministic, so the same upstream bytes give extracts with the paper's hashes.
- For the three single-file dumps there is a manual route that pipes the dump through
  the same filter and never stores it. Run it in `data/burn_units` with the shipped
  `raw/manifest.json` in place, which holds the `upstream_header` of these files, then
  check the result with `python3 fetch.py verify`. The example is the 2021-12-31
  snapshot. The other two differ only in commit and file name. Use `fetch.py` for the
  four snapshots stored as 20 split files.

```sh
set -o pipefail
mkdir -p raw/zi_history
curl -sSfL https://raw.githubusercontent.com/zapret-info/z-i/d291c7d7d7e406fbd8d08b1c9413a4ebb51fc42a/dump.csv | python3 -c 'import sys, fetch; print(fetch.zi_extract(sys.stdin.buffer, sys.argv[1]))' raw/zi_history/extract_2022-01-01_d291c7d7d7.csv
```

The command prints the dump's first line, its number of data lines and the number of
rows kept, which should be 548,880 and 3,191 for this snapshot. If it exits with an error
or prints other counts, delete the extract before you try again. A failed download leaves
an extract with only its header line, and `fetch.py zi_history` skips any extract that
exists and has a manifest entry.

### antifilter.download (`antifilter/`)

- `https://antifilter.download/list/domains.lst` is a domain list derived from the
  registry. `fetch.py antifilter` filters it into `domains_platform_extract.lst` as the
  handling rules describe. The paper's copy had Last-Modified Fri, 02 Oct 2026 22:39:16
  GMT, 32,420,045 bytes, 1,698,776 lines and SHA-256
  `8baa7d2601264b076e89d1e5ffb267b9129775ad0f7ff3741d04eade678bb9a6`, and 17,143 lines were
  kept. The site serves only its current list, so your copy will differ.
- `https://community.antifilter.download/list/domains.lst` is a user-voted routing list,
  not registry data. The two index pages describe the lists and are not read.
- No license is stated for any of them, and the paper does not use them for any number.
  In `analysis.py` the extract decides whether a Russian platform without any registry
  entry is shown as ∅, joins the registry in marking names as listed in
  `ru_ooni_vs_registry.csv`, and adds antifilter counts to the notes and to
  `ru_antifilter_platform_summary.csv`.
- To avoid handling a registry-derived list, skip `fetch.py antifilter` and create both
  lists empty, with
  `mkdir -p raw/antifilter && : > raw/antifilter/domains_platform_extract.lst && : > raw/antifilter/community_domains.lst`.
  With the paper's other inputs, Table 1, every OONI count, `ru_ooni_vs_registry.csv`
  and `run_meta.json` stay the same. Only the antifilter part of the notes in
  `burn_units.csv`, `burn_units_evidence_long.csv` and
  `ru_antifilter_platform_summary.csv` change, and `verify` reports the four antifilter
  files as missing or different.

### Tranco (`tranco/`)

Daily top-1M lists of Le Pochat et al., NDSS 2019, free for research with no explicit
license, so cite them. `fetch.py tranco` asks `https://tranco-list.eu/api/lists/date/<date>`
for the list id, saves the answer as `tranco_<date>_meta.json`, and downloads
`https://tranco-list.eu/download/<list id>/1000000` as
`tranco_<date>_<list id>_top1m.csv`, with lines `rank,domain` and no header. The paper's
lists are `4Q6GX` (2024-09-01), `24LY9` (2025-01-01), `9WZV2` (2025-10-01) and `Y83YG`
(2026-10-01). A list id names a fixed list, so these files should match the paper's. The
lists show that each bare suffix was in the daily test input of GFWatch and IRBlock, and
the paper quotes no rank.

### Public Suffix List (`psl/`)

`https://raw.githubusercontent.com/publicsuffix/list/main/public_suffix_list.dat`,
MPL-2.0. `analysis.py` uses it to group host names into tenants, that is registrable
domains. `python3 fetch.py psl` takes the current file. The paper's copy has 334,645
bytes and SHA-256 `102b252c18b5f87f4c81f017e75282a82c18e00cd0c2e601b5b02a0f7a601f2c`, was
retrieved at 2026-10-03 21:56:59 UTC and carries no version line, so find its commit by
hash. Run this in `data/burn_units`.

```sh
git clone --filter=blob:none --no-checkout https://github.com/publicsuffix/list "$BURN_UNITS_SCRATCH/psl"
for c in $(git -C "$BURN_UNITS_SCRATCH/psl" rev-list -n 20 --before='2026-10-03 21:57:00 +0000' main -- public_suffix_list.dat); do
  h=$(git -C "$BURN_UNITS_SCRATCH/psl" show "$c:public_suffix_list.dat" | sha256sum | cut -d' ' -f1)
  if [ "$h" = 102b252c18b5f87f4c81f017e75282a82c18e00cd0c2e601b5b02a0f7a601f2c ]; then echo "$c"; break; fi
done
```

On macOS write `shasum -a 256` in place of `sha256sum`. Then download the file of the
printed commit and skip `fetch.py psl`.

```sh
mkdir -p raw/psl
curl -sSfL "https://raw.githubusercontent.com/publicsuffix/list/<commit>/public_suffix_list.dat" -o raw/psl/public_suffix_list.dat
```

Without the pin, tenant counts can change for any platform whose PSL rules have changed
since. Without the file, `analysis.py` silently groups names by the first label left of
the suffix. With the paper's other inputs that changes the tenant counts of
`appspot.com` and `run.app` and leaves Table 1 and every number in the paper the same.

### Qualitative reports (`qualitative/`)

These reports are read, not measured. None states a license, so cite them and quote
briefly.

- `tor_gitlab_40064_discussions.json` comes from
  `https://gitlab.torproject.org/tpo/anti-censorship/censorship-analysis/-/issues/40064/discussions.json`.
  The GitLab front end answers 403 until the client sends the cookie that its own 403
  page sets, so `fetch.py` sends the headers `Cookie: _gitlab_session=1` and
  `Accept: application/json`.
- `tor_gitlab_40064_issue.json` comes from
  `https://gitlab.torproject.org/api/v4/projects/tpo%2Fanti-censorship%2Fcensorship-analysis/issues/40064`.
  `analysis.py` does not read it.
- `net4people_bbs_133.html` and `net4people_bbs_417.html` are the pages
  `https://github.com/net4people/bbs/issues/133` and
  `https://github.com/net4people/bbs/issues/417`.
- `analysis.py` checks that the quoted sentences occur in each file and takes the date of
  the first GitLab comment, 2025-06-23. By hand, save the pages from a browser. The paper
  cites the Tor GitLab issue in Section 3.

## Check your copy against the paper's

After a run, `raw/manifest.json` describes the files that `fetch.py` downloaded. Run this
in `data/burn_units` to compare them with `manifest.paper.json`.

```sh
python3 - <<'EOF'
import json

def upstream(entry):
    up = {u["url"]: u["sha256"] for u in entry.get("upstream_files", [])}
    if "upstream_sha256" in entry:
        up[entry["url"]] = entry["upstream_sha256"]
    return up

paper = json.load(open("manifest.paper.json"))["files"]
mine = json.load(open("raw/manifest.json"))["files"]
for rel, p in sorted(paper.items()):
    m = mine.get(rel)
    if m is None:
        print("NOT FETCHED", rel)
        continue
    print("same       " if m["sha256"] == p["sha256"] else "DIFFERENT  ", rel)
    want, got = upstream(p), upstream(m)
    if want:
        bad = [u for u, h in want.items() if got.get(u) != h]
        print("    upstream files:", "same" if not bad else f"{len(bad)} of {len(want)} differ")
    if "git_head" in p:
        print("    git_head:", "same" if m.get("git_head") == p["git_head"] else m.get("git_head"))
EOF
```

Only `fetch.py` records a download in `raw/manifest.json`. A file saved by one of the
manual routes keeps the paper's entry, so the snippet prints `same` for it whatever it
holds. Check such files with `python3 fetch.py verify`, which compares them with the
paper's hash. `SHA MISMATCH` there means that the file differs from the paper's copy.

With the pins above, expect these results.

- Same:
  - the 7 registry extracts and all their upstream files, as long as GitHub serves the
    pinned commits
  - `irblock/README.md` and `irblock/blocked_domains.tar.gz`
  - the 4 Tranco lists and their metadata
  - the 5 raw OONI measurements
  - the pinned `psl/public_suffix_list.dat`
  - `qualitative/tor_gitlab_40064_issue.json`, unless the issue has changed
  - probably the 19 GFWatch files, whose public data are frozen (not checked)
- Different by design:
  - the 9 OONI aggregation files, because each answer embeds query statistics
    (`db_stats`) and OONI can add or reprocess measurements
  - the 3 OONI measurement lists, which embed their query time
  - `gfwlist/gfwlist.bundle`, whose `git_head` should still be the same
  - everything in `antifilter/`
  - `irblock/zenodo_record_15572895.json`, whose view and download counters change
  - the two GitHub pages and the GitLab discussion JSON

## What a new download cannot reproduce

- **OONI.** The aggregation answers cannot be fetched again as the paper used them. Counts
  can move, and with them the OONI numbers of Section 6.1 (6 of 980, 984 of 1,100, 1,008
  of 1,008 and 357 of 376), the Azure Front Door episode, the five-name minimum behind
  Table 1 and the OONI notes.
- **antifilter.** The site serves only its current list. A new copy changes the
  antifilter notes and `ru_antifilter_platform_summary.csv`, and it changes Table 1 only
  if `fly.dev`, `on.aws`, `trycloudflare.com` or `r2.dev` gained an entry.
- **gfwlist and the Public Suffix List without the pins.** Without the gfwlist pin,
  `cn_gfwlist_platform_history.csv` and the gfwlist notes change. The paper uses neither.
  Without the PSL pin, tenant counts can change for platforms whose PSL rules have
  changed.
- **The web pages.** If a GitHub or GitLab page has changed, `quotes_verified` in
  `../derived/qualitative_events.csv` can turn false, and `analysis.py` prints
  `[qual] quote not found`.
- **Disappearing sources.** If the z-i repository, the GFWatch dashboard or the OONI API
  disappears or changes its interface, the inputs from it cannot be rebuilt. The shipped
  `../derived/` files keep the paper's numbers in any case.

## If an input is missing

| missing | what `analysis.py` does |
|---|---|
| `manifest.json` | stops, because it needs the registry dump dates |
| one `gfwatch/` file | prints `[gfwatch] missing` and treats the platform as never blocked in China, so its China cell turns into `?` or ∅, and stops if all are missing. For `github.io`, `appspot.com`, `herokuapp.com`, `workers.dev` and `vercel.app`, which the timeline figure draws, the run writes every table and then ends with a `TypeError` in `make_figure()` |
| `gfwlist/gfwlist.bundle` | stops |
| one OONI aggregation window | runs with other OONI counts, and stops if all are missing |
| `ooni/agg_CN_azurefd40_2025-07-01_2026-05-01_day_domain.json` | runs, with an Azure Front Door series that starts in May 2026 |
| `ooni/agg_CN_azurefd40_2026-05-01_2026-10-01_day_domain.json`, or both files | stops before it writes any output. Without the later file the episode has no lift day, and `classify()` ends with a `TypeError` |
| `ooni/raw_*.json` | runs, with an empty mechanism table |
| `irblock/blocked_domains.tar.gz` | stops |
| one registry extract | runs with a shorter Russian time series, which can change Russian cells and dates, and stops if all are missing |
| either antifilter list | stops |
| all Tranco lists | stops. A missing 2024-09-01 or 2025-01-01 list changes only the notes |
| `psl/public_suffix_list.dat` | runs silently with the cruder tenant rule described above |
| a qualitative file that `analysis.py` reads | stops |
