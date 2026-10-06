# SOURCES: data/literature

Literature calibration of censor-capability parameters. Only published papers,
one public GitHub issue and five publisher or arXiv web pages were downloaded.
No network target was probed, scanned, resolved or connected to, and no new
measurement was made.

## How the raw files were obtained

- `fetch_sources.py` downloads every file below into `raw/`, with requests
  spaced at least 3 s apart, and writes `raw/manifest.json` (URL, final URL,
  HTTP status, content type, retrieval time in UTC, sha256, size, licence).
  Running it again skips files it already has and refreshes only the
  descriptive metadata.
- `analysis.py` re-hashes every file in the manifest before it uses any of them.
- **Local copies.** Two PDFs, `raw/nasr2019ndss_enemy_gateways.pdf` and
  `raw/fares2026foci_game_has_changed.pdf`, were also compared with copies the
  authors already held, and they match byte for byte. Their manifest entries
  record this in `local_copy`, `local_copy_sha256` and
  `local_copy_identical: true`. The `related/` folder named there is not part
  of the artifact.
- **Existence checks.**
  - Chen et al. 2609.12242 v2 (14 Sep 2026; comment "Accepted to 2026 ACM CCS")
    was confirmed through the arXiv API and its abstract page (archived).
  - The Fifield, Tsai and Zhong arXiv paper was found through an arXiv API
    author search. It is *Detecting Censor Detection*, 1709.08718v1.
  - Heitmann et al. is FOCI 2026 issue 2, pages 1–6
    (`foci-2026-0010`, on the archived index and article pages).
- **Xue et al. IMC 2022.** The ACM DL PDF returned HTTP 403, so the authors'
  copy on censoredplanet.org was used. It carries the ACM DOI
  10.1145/3517745.3561461.
- **The GitHub issue.** The issue page HTML was saved and parsed offline: the
  issue body and its 10 comments come from the page's embedded JSON. The GitHub
  REST API was not used. Rows locate a comment by its position and UTC time
  (for example `comment 2 (2022-03-28T06:03:40Z)`), not by the commenter's
  login.
- **Title check.** The USENIX FOCI'20 page for Bock et al. gives the title
  "... Iran's Protocol Whitelister". The PDF's own heading reads "... Iran's
  Protocol Filter", which is the title the paper cites.

## Licences and redistribution

- **CC BY 4.0:** Fares et al. 2026 and Heitmann et al. 2026. Chen et al.'s PDF
  states CC BY 4.0 for its CCS version, but arXiv distributes it under the arXiv
  non-exclusive licence.
- **CC0 1.0:** Fifield, Tsai and Zhong 2017, as its arXiv abstract page states.
- **Everything else** is freely readable but copyrighted by the authors or the
  publisher (ACM, USENIX, the Internet Society, PoPETs), or, for the GitHub
  issue, is user content with no licence.
- **`raw/` is not redistributed.** The artifact ships `fetch_sources.py`,
  `params_spec.py`, `analysis.py` and `raw/manifest.json`, and
  `raw/README.md` explains how to fetch the files again.
- **GFW Report material.** Wu et al. 2025 and Alice et al. 2020 are GFW Report
  copies: cite them and do not redistribute.
- **No OONI or OpenINTEL data are used here**, so no share-alike obligation
  applies to `derived/`. The derived CSVs contain only short quotations
  with page citations, plus arithmetic on the quoted numbers.

## Raw files (from `raw/manifest.json`)

| file | key | URL | retrieved (UTC) | bytes | sha256 | licence |
|---|---|---|---|---:|---|---|
| `ensafi2015imc_gfw_hidden_servers.pdf` | ensafi2015imc | https://conferences2.sigcomm.org/imc/2015/papers/p445.pdf | 2026-10-03T21:45:37Z | 4,937,191 | `c099e0f253bcb11541f0a51bee75596b96a7574217d9b1cb310583c21a0fa089` | ACM notice on p.1 (copyright held by the owner/author(s), publication rights licensed to ACM). Quote with citation; do not redistribute. |
| `ensafi2015popets_gfw_space_time.pdf` | ensafi2015popets | https://petsymposium.org/popets/2015/popets-2015-0005.pdf | 2026-10-03T21:45:41Z | 1,725,932 | `6958fdeaa7536a0318eefde6a05b2404c78bcd34a268493560457b4f927cb60f` | No licence statement in the PDF; PoPETs open access. Quote with citation; do not redistribute. |
| `alice2020imc_shadowsocks.pdf` | alice2020imc | https://gfw.report/publications/imc20/data/paper/shadowsocks.pdf | 2026-10-03T21:45:45Z | 3,797,684 | `37684d43b88d9665a8ed9145b066d70565d65652fe4b6d18f5f6f27d2e8f3d07` | Authors' copy (GFW Report); ACM notice on p.1. Quote with citation; do not redistribute. |
| `dunna2018foci_unpublished_bridges.pdf` | dunna2018foci | https://www.usenix.org/system/files/conference/foci18/foci18-paper-dunna.pdf | 2026-10-03T21:45:48Z | 180,549 | `28bd769092b80cdf80a03508cfe63cdb8b30f7c5dd0cf0216a45d68cab20ce3f` | No licence statement; USENIX open access. Quote with citation; do not redistribute. |
| `fifield2016foci_censors_delay.pdf` | fifield2016foci | https://www.usenix.org/system/files/conference/foci16/foci16-paper-fifield.pdf | 2026-10-03T21:45:52Z | 1,887,158 | `be78b5dacab3758b26b1bc1c63936ec1429630135861ad99dca3d9ca164262b4` | No licence statement; USENIX open access. Quote with citation; do not redistribute. |
| `fifield2017arxiv_detecting_censor_detection.pdf` | fifield2017arxiv | https://arxiv.org/pdf/1709.08718v1 | 2026-10-03T21:45:55Z | 4,331,791 | `524d4b5bf38a762ac484fef96392846e93323e5ed8f7ec85599b449a7526fc6d` | CC0 1.0 (arXiv abstract page). `raw/manifest.json`, kept as retrieved, records the arXiv default licence for this file. |
| `wu2023usenix_fully_encrypted.pdf` | wu2023usenix | https://www.usenix.org/system/files/usenixsecurity23-wu-mingshi.pdf | 2026-10-03T21:45:59Z | 1,147,531 | `e65cb401693df38d33f6ae4a418735ed8717adbefc2f579af69d94e63588b2f3` | USENIX open access (p.1 notice). Quote with citation; do not redistribute. |
| `bock2020foci_iran_whitelister.pdf` | bock2020foci | https://www.usenix.org/system/files/foci20-paper-bock.pdf | 2026-10-03T21:46:03Z | 150,002 | `0dbbe3796447ccd359d2c6064adb11c906f153a127a6cf8448368a564e53a5eb` | No licence statement; USENIX open access. Quote with citation; do not redistribute. |
| `xue2022imc_tspu.pdf` | xue2022imc | https://censoredplanet.org/assets/tspu-imc22.pdf | 2026-10-03T21:46:06Z | 4,234,259 | `a6a6d781fb6d39d1f0a4eb3a671929c2de972bb3a1efa151089513eba389170b` | Authors' copy; ACM notice on p.1 (copyright held by the owner/author(s)). Quote with citation; do not redistribute. |
| `zohaib2025usenix_quic_sni.pdf` | zohaib2025usenix | https://www.usenix.org/system/files/usenixsecurity25-zohaib.pdf | 2026-10-03T21:46:10Z | 820,385 | `e3f9ec5fd6e72231966fe521e9f2fa0df189efe6474d38d3b690e093b3735d4e` | USENIX open access (p.1 notice). Quote with citation; do not redistribute. |
| `heitmann2026foci_russia_quic_sni.pdf` | heitmann2026foci | https://petsymposium.org/foci/2026/foci-2026-0010.pdf | 2026-10-03T21:46:13Z | 559,028 | `e9b40abe47c34c4b879df4d8c072a67492081a36c3ad1ebf0b9a464a48e13a90` | CC BY 4.0. |
| `wu2025sp_wall_behind_wall.pdf` | wu2025sp | https://gfw.report/publications/sp25/data/paper/paper.pdf | 2026-10-03T21:46:17Z | 1,025,009 | `5f6c3647feeab362420a40a6f8a7c4c12966a243fcb21d40ae18bc647d2729c1` | Authors' copy (GFW Report); no licence statement. Cite; do not redistribute. |
| `bocovich2024usenix_snowflake.pdf` | bocovich2024usenix | https://www.usenix.org/system/files/usenixsecurity24-bocovich.pdf | 2026-10-03T21:46:20Z | 1,242,882 | `78fbe6e4d688a79bbb8d10f372fba2c51ca3839efe97995c62517850ba553110` | USENIX open access (p.1 notice). Quote with citation; do not redistribute. |
| `chen2026arxiv_snowflake_enumeration.pdf` | chen2026arxiv | https://arxiv.org/pdf/2609.12242v2 | 2026-10-03T21:46:24Z | 20,608,120 | `e84f2fe8d9e96c92cd7262678df12edd8cf69dba71951786f49d18e7ef70deea` | arXiv non-exclusive licence 1.0 (abstract page); the PDF states CC BY 4.0 for the CCS version. |
| `hoang2021usenix_gfwatch.pdf` | hoang2021usenix | https://www.usenix.org/system/files/sec21-hoang.pdf | 2026-10-03T21:46:27Z | 732,846 | `5a27353833c15ca243ce342fa0a0ce5f30826b09fd7cc53de357ad028c792a71` | USENIX open access (p.1 notice). Quote with citation; do not redistribute. |
| `nasr2019ndss_enemy_gateways.pdf` | nasr2019ndss | https://www.ndss-symposium.org/wp-content/uploads/2019/02/ndss2019_11-2_Nasr_paper.pdf | 2026-10-03T21:46:31Z | 741,754 | `83d5ccbf56cf13dd2929fe042080502a5d1bc25631bf0df1692a6b4f3567c2ef` | NDSS open access; no licence text on p.1. Quote with citation; do not redistribute. |
| `fares2026foci_game_has_changed.pdf` | fares2026foci | https://petsymposium.org/foci/2026/foci-2026-0003.pdf | 2026-10-03T21:46:34Z | 949,358 | `3700d51325f054226258a0bf8e40ce5e7c8183e7a8f4edd08d2ce1b349d68514` | CC BY 4.0. |
| `winter2012foci_gfw_blocking_tor.pdf` | winter2012foci | https://www.usenix.org/system/files/conference/foci12/foci12-final2.pdf | 2026-10-03T21:46:37Z | 424,050 | `4e274a6a822b949c514acc0a7be56d3242b0b7e9150bf2c09e5478514d4ef6f9` | No licence statement; USENIX open access. Quote with citation; do not redistribute. |
| `net4people_bbs_issue111.html` | bbs111 | https://github.com/net4people/bbs/issues/111 | 2026-10-03T21:46:41Z | 289,554 | `d3390ffe53dd6b28b8096931e6de219cae4e7b9499615152a7a5e862a39cc94d` | User content, no explicit licence (GitHub Terms of Service). Quote briefly as a field report; do not redistribute. |
| `arxiv_abs_1709.08718v1.html` | arxiv_abs_1709 | https://arxiv.org/abs/1709.08718v1 | 2026-10-03T22:23:38Z | 40,450 | `d001501abfbf92011066a7b7d954b32da90edfb515c9a25e38715912d91f4742` | arXiv page (licence evidence). |
| `arxiv_abs_2609.12242v2.html` | arxiv_abs_2609 | https://arxiv.org/abs/2609.12242v2 | 2026-10-03T22:23:41Z | 43,498 | `3e5e2eeb1d6e8fe40608860e101187da99bbf2281496b73fb8b6d6430ab8ecdd` | arXiv page (existence, licence, CCS comment). |
| `foci2026_index.html` | foci2026_index | https://petsymposium.org/foci/2026/ | 2026-10-03T22:23:44Z | 7,188 | `0ab9fc98aaa693beeedae8036fa47b5f1fb83ac1acf0659e29e1589a9a6b100c` | Publisher page (issue listing). |
| `foci2026_0010_article.html` | foci2026_0010_page | https://petsymposium.org/foci/2026/foci-2026-0010.php | 2026-10-03T22:23:47Z | 4,311 | `473c75044ec00a86ac0561bd62c25338f7f8240111e78f8d4125f8a7679facec` | Publisher page (CC BY 4.0 statement). |
| `usenix_foci20_bock_page.html` | usenix_foci20_bock_page | https://www.usenix.org/conference/foci20/presentation/bock | 2026-10-03T22:28:06Z | 30,692 | `7a10c1d240fe705bb73f18ffa3aa4256468210f0916dd34f75413cab913d5f18` | Publisher page (official title). |

Total: 24 files, 49,911,222 bytes (about 50 MB). The largest is Chen et al. at
20.6 MB, far below the 1.5 GB per-file cap.

## Consulted but not archived

The arXiv API responses (`export.arxiv.org/api/query`) for `id_list=2609.12242`
and `au:Fifield AND au:Tsai`, retrieved 2026-10-03 about 21:42 UTC, were used
only to find the two arXiv IDs. The archived abstract pages above carry the same
facts.

## Paper-side references

The `bibkey` column of `derived/params_table.csv` holds a short citation key
for each source. The paper cites 14 of the 19 sources under these keys. The
other five, `gfw_space_time`, `gfw_shadowsocks`, `censor_detection`,
`snowflake_enumeration` and `n4p_issue111`, contribute 25 rows to the table but
are not in the paper's bibliography.
