# Literature sources (`data/literature/raw/`)

This directory holds the third-party files that `../analysis.py` reads. The
files are not part of the artifact. The artifact ships only this README and
`manifest.json`. Keep `manifest.json` here, because `../analysis.py` and
`../fetch_sources.py` read it.

The files are 18 papers (PDF), one GitHub issue page that serves as a field
report (HTML) and five web pages kept as evidence of titles, versions and
licenses (HTML). For each file, `manifest.json` records the URL, the final URL,
the HTTP status, the content type, the retrieval time in UTC, the SHA-256, the
size in bytes and a license note. The paper's copies were retrieved on
2026-10-03 between 21:45:37 and 22:28:06 UTC. The 24 files total 49,911,222
bytes (about 50 MB). The largest is `chen2026arxiv_snowflake_enumeration.pdf`
(20,608,120 bytes).

Nothing here measures a network. `../fetch_sources.py` contacts only the 24
URLs listed below.

## Expected files

### Parameter sources (all 19 are required)

`../params_spec.py` holds 110 published values. Each has a verbatim quote and
its location, which is a 1-based PDF page or, for the GitHub issue, the issue
body or a comment. `../analysis.py` extracts the text of each cited page and
checks that every quote occurs there. If one of these 19 files is missing,
`analysis.py` stops with an error before it writes any output. The `key`
column is the `source_key` column of `../derived/params_table.csv`, and `rows`
counts the values taken from each file.

| file | key | rows | work | URL | bytes | license |
|---|---|---:|---|---|---:|---|
| `ensafi2015imc_gfw_hidden_servers.pdf` | ensafi2015imc | 4 | Ensafi et al., Examining How the Great Firewall Discovers Hidden Circumvention Servers, ACM IMC 2015, DOI 10.1145/2815675.2815690 | https://conferences2.sigcomm.org/imc/2015/papers/p445.pdf | 4,937,191 | ACM notice (copyright held by the authors, publication rights licensed to ACM) |
| `ensafi2015popets_gfw_space_time.pdf` | ensafi2015popets | 2 | Ensafi et al., Analyzing the Great Firewall of China Over Space and Time, PoPETs 2015(1), DOI 10.1515/popets-2015-0005 | https://petsymposium.org/popets/2015/popets-2015-0005.pdf | 1,725,932 | no license statement (PoPETs open access) |
| `winter2012foci_gfw_blocking_tor.pdf` | winter2012foci | 3 | Winter and Lindskog, How the Great Firewall of China is Blocking Tor, USENIX FOCI 2012 | https://www.usenix.org/system/files/conference/foci12/foci12-final2.pdf | 424,050 | no license statement (USENIX open access) |
| `alice2020imc_shadowsocks.pdf` | alice2020imc | 7 | Alice et al., How China Detects and Blocks Shadowsocks, ACM IMC 2020, DOI 10.1145/3419394.3423644 (authors' copy) | https://gfw.report/publications/imc20/data/paper/shadowsocks.pdf | 3,797,684 | ACM notice (copyright held by the authors, publication rights licensed to ACM) |
| `dunna2018foci_unpublished_bridges.pdf` | dunna2018foci | 8 | Dunna, O'Brien and Gill, Analyzing China's Blocking of Unpublished Tor Bridges, USENIX FOCI 2018 | https://www.usenix.org/system/files/conference/foci18/foci18-paper-dunna.pdf | 180,549 | no license statement (USENIX open access) |
| `fifield2016foci_censors_delay.pdf` | fifield2016foci | 6 | Fifield and Tsai, Censors' Delay in Blocking Circumvention Proxies, USENIX FOCI 2016 | https://www.usenix.org/system/files/conference/foci16/foci16-paper-fifield.pdf | 1,887,158 | no license statement (USENIX open access) |
| `fifield2017arxiv_detecting_censor_detection.pdf` | fifield2017arxiv | 3 | Fifield, Tsai and Zhong, Detecting Censor Detection, arXiv:1709.08718v1 | https://arxiv.org/pdf/1709.08718v1 | 4,331,791 | CC0 1.0 (arXiv abstract page; the shipped `manifest.json` records the arXiv default license) |
| `wu2023usenix_fully_encrypted.pdf` | wu2023usenix | 6 | Wu et al., How the Great Firewall of China Detects and Blocks Fully Encrypted Traffic, USENIX Security 2023 | https://www.usenix.org/system/files/usenixsecurity23-wu-mingshi.pdf | 1,147,531 | USENIX open access (notice on p. 1) |
| `bock2020foci_iran_whitelister.pdf` | bock2020foci | 4 | Bock et al., Detecting and Evading Censorship-in-Depth: A Case Study of Iran's Protocol Filter, USENIX FOCI 2020 | https://www.usenix.org/system/files/foci20-paper-bock.pdf | 150,002 | no license statement (USENIX open access) |
| `xue2022imc_tspu.pdf` | xue2022imc | 8 | Xue et al., TSPU: Russia's Decentralized Censorship System, ACM IMC 2022, DOI 10.1145/3517745.3561461 (authors' copy) | https://censoredplanet.org/assets/tspu-imc22.pdf | 4,234,259 | ACM notice (copyright held by the authors) |
| `zohaib2025usenix_quic_sni.pdf` | zohaib2025usenix | 9 | Zohaib et al., Exposing and Circumventing SNI-based QUIC Censorship of the Great Firewall of China, USENIX Security 2025 | https://www.usenix.org/system/files/usenixsecurity25-zohaib.pdf | 820,385 | USENIX open access (notice on p. 1) |
| `heitmann2026foci_russia_quic_sni.pdf` | heitmann2026foci | 6 | Heitmann et al., On Russia's Early Introduction of QUIC SNI Censorship, FOCI 2026(2), article foci-2026-0010 | https://petsymposium.org/foci/2026/foci-2026-0010.pdf | 559,028 | CC BY 4.0 |
| `wu2025sp_wall_behind_wall.pdf` | wu2025sp | 5 | Wu et al., A Wall Behind A Wall: Emerging Regional Censorship in China, IEEE S&P 2025 (authors' copy) | https://gfw.report/publications/sp25/data/paper/paper.pdf | 1,025,009 | no license statement (authors' copy) |
| `bocovich2024usenix_snowflake.pdf` | bocovich2024usenix | 8 | Bocovich et al., Snowflake, a censorship circumvention system using temporary WebRTC proxies, USENIX Security 2024 | https://www.usenix.org/system/files/usenixsecurity24-bocovich.pdf | 1,242,882 | USENIX open access (notice on p. 1) |
| `chen2026arxiv_snowflake_enumeration.pdf` | chen2026arxiv | 9 | Chen et al., Evaluating Practical Enumeration and Blocking Attacks on the Snowflake Circumvention System, arXiv:2609.12242v2 (accepted to ACM CCS 2026, DOI 10.1145/3830454.3846627) | https://arxiv.org/pdf/2609.12242v2 | 20,608,120 | arXiv non-exclusive distribution license 1.0 (the PDF states CC BY 4.0 for the CCS version) |
| `hoang2021usenix_gfwatch.pdf` | hoang2021usenix | 5 | Hoang et al., How Great is the Great Firewall? Measuring China's DNS Censorship, USENIX Security 2021 | https://www.usenix.org/system/files/sec21-hoang.pdf | 732,846 | USENIX open access (notice on p. 1) |
| `nasr2019ndss_enemy_gateways.pdf` | nasr2019ndss | 6 | Nasr et al., Enemy At the Gateways: Censorship-Resilient Proxy Distribution Using Game Theory, NDSS 2019, DOI 10.14722/ndss.2019.23496 | https://www.ndss-symposium.org/wp-content/uploads/2019/02/ndss2019_11-2_Nasr_paper.pdf | 741,754 | no license text on p. 1 (NDSS open access) |
| `fares2026foci_game_has_changed.pdf` | fares2026foci | 7 | Fares, Fulsundar and Hopper, The Game Has Changed: Revisiting proxy distribution and game theory, FOCI 2026(1), article foci-2026-0003 | https://petsymposium.org/foci/2026/foci-2026-0003.pdf | 949,358 | CC BY 4.0 |
| `net4people_bbs_issue111.html` | bbs111 | 4 | net4people/bbs issue 111, a field report on Outline servers in Russia, opened 2022-03-27 | https://github.com/net4people/bbs/issues/111 | 289,554 | user content without a license (GitHub Terms of Service) |

Page numbers in `../params_spec.py` are indices into these exact files. Another
copy of the same paper, such as a digital-library copy instead of an authors'
copy, can be paginated differently, and its quotes are then reported as not
found on the cited page. Use the URLs above. For Xue et al. 2022 the ACM
Digital Library returned HTTP 403 at retrieval, so the authors' copy on
censoredplanet.org is the reference copy.

`analysis.py` reads the GitHub issue from the page's HTML as the server sends
it. It takes the issue body and the 10 comments from the JSON inside the
page's `<script type="application/json" data-target="react-app.embeddedData">`
element and locates a comment by its position and UTC time, for example
`comment 2 (2022-03-28T06:03:40Z)`. A copy saved by a browser as a "complete"
page can be rewritten and may lack this element.

### Evidence pages (checked against the manifest only)

| file | URL | bytes | what it shows |
|---|---|---:|---|
| `arxiv_abs_1709.08718v1.html` | https://arxiv.org/abs/1709.08718v1 | 40,450 | arXiv license of Fifield, Tsai and Zhong |
| `arxiv_abs_2609.12242v2.html` | https://arxiv.org/abs/2609.12242v2 | 43,498 | existence, license and ACM CCS 2026 note of Chen et al. |
| `foci2026_index.html` | https://petsymposium.org/foci/2026/ | 7,188 | FOCI 2026 issue listings |
| `foci2026_0010_article.html` | https://petsymposium.org/foci/2026/foci-2026-0010.php | 4,311 | pages 1 to 6 and CC BY 4.0 of Heitmann et al. |
| `usenix_foci20_bock_page.html` | https://www.usenix.org/conference/foci20/presentation/bock | 30,692 | program title of Bock et al. |

No output depends on these pages. If one is missing or differs from
`manifest.json`, `analysis.py` prints a `PROBLEM` line, writes all outputs and
exits with status 1.

## Step 1. Keep the paper's manifest

Run this once, before the first download:

```
cd data/literature
cp raw/manifest.json manifest.paper.json
```

`fetch_sources.py` replaces the manifest entry of every file it downloads, so
`manifest.paper.json` keeps the paper's hashes for Step 3. If `manifest.json`
has already been rewritten, take the file again from the artifact.

## Step 2. Download the files

**Option A, with the script.** It needs Python 3 and the `requests` package.

```
cd data/literature
python3 fetch_sources.py
```

- It keeps a file that exists in `raw/` and is listed in `manifest.json`, and
  downloads every other file. With `--force` it downloads all 24 again.
- It waits at least 3 s between requests and caps each file at 1.5 GB. A full
  download is about 50 MB and takes a little over a minute plus transfer
  time.
- For each download it writes a new manifest entry (retrieval time, SHA-256,
  size, HTTP status) and prints either `same sha256 as before` or
  `sha256 differs from the replaced entry`, a comparison with the entry it
  replaced.
- It stops at the first HTTP status other than 200, for example 403 from a
  host that refuses scripts. The entries of the files downloaded before then
  are saved. Download that file by hand (Option B) and run the script again,
  which keeps the files it already has.

**Option B, by hand.** Download each URL in the two tables with a browser or
any HTTP client and save it in this directory under the exact file name given.
Keep the shipped `manifest.json`, so `analysis.py` checks every file against
the paper's SHA-256 and size. For the GitHub issue, save the HTML exactly as
the server sends it (see above).

## Step 3. Compare with the paper's copies

```
cd data/literature
python3 - <<'EOF'
import hashlib, json, os
paper = json.load(open("manifest.paper.json"))["files"]
counts = {"same": 0, "differs": 0, "missing": 0}
for name in sorted(paper):
    path = os.path.join("raw", name)
    if not os.path.exists(path):
        state = "missing"
    else:
        with open(path, "rb") as f:
            same = hashlib.sha256(f.read()).hexdigest() == paper[name]["sha256"]
        state = "same" if same else "differs"
    counts[state] += 1
    print(f"{state:8s} {name}")
print(counts)
EOF
```

With the paper's copies it prints `same` for all 24 files and
`{'same': 24, 'differs': 0, 'missing': 0}`.

## What can differ from the paper's copies

- The six HTML files are generated on request, so their SHA-256 usually
  differs from the paper's. For the five evidence pages this has no effect on
  any output. After Option B, `analysis.py` reports each differing file in a
  `PROBLEM` line and exits with status 1 after writing all outputs.
- The GitHub issue page is parsed. As long as GitHub keeps the embedded JSON
  and the issue's comments are unchanged, its four rows (T01, T15, T16 and T17
  in `../params_spec.py`) verify as in the shipped outputs. If the format has
  changed, `analysis.py` stops in `issue_blocks()` with an error before it
  writes any output. If comments were added, removed or edited, a quote can
  be reported as not found at its cited comment, together with the locations
  where it does occur. The UTC time in each locator identifies the comment.
- The arXiv URLs pin versions v1 and v2. The other hosts can move or replace a
  file. A PDF with a different SHA-256 can be paginated differently, and
  `analysis.py` then reports each quote it cannot find on the cited page,
  with the pages where it occurs.
- Retrieval times always differ.

## Next step

```
cd data/literature
python3 analysis.py --out derived-rerun
```

This runs offline in about 30 to 40 seconds and needs `pdftotext` from
poppler-utils. It writes the six outputs to `derived-rerun/` and leaves the
shipped files in `../derived/` unchanged. Compare them as "Regenerate and
compare" in `../derived/README.md` shows.

## Licenses and safety

- Two papers are CC BY 4.0 (Heitmann et al. 2026 and Fares et al. 2026), and
  arXiv lists Fifield, Tsai and Zhong 2017 under CC0 1.0. The other papers are
  free to read but copyrighted by their authors or publishers. The GitHub issue
  is user content without a license, and the web pages carry none. The artifact
  ships no raw file. Do not commit these files to a public repository, and
  quote only short passages, with a citation. `../SOURCES.md` gives each
  license note.
- The GitHub issue page also contains the commenters' GitHub logins and
  profile data. The derived files locate comments by position and time
  only. Do not republish the page.
- `fetch_sources.py` contacts only the publisher, author, arXiv and GitHub
  URLs above, with the User-Agent
  `Mozilla/5.0 (X11; Linux x86_64) literature-calibration (no measurements)`.
  It never contacts a measurement target, an endpoint or a blocked name.
