# Data pipelines

Four analyses of existing public data support Section 6 and Appendix D of the
paper, and single statements in other sections (see `PAPER_MAP.md` in the
repository root). None of them makes a new measurement. Each one downloads
public datasets and documents again and rebuilds its outputs offline.

| directory | paper | fetch script | inputs of the paper's run | shipped outputs |
|---|---|---|---|---:|
| `burn_units/` | Table 1, Sections 1, 3, 6.1, 7, 8 and 9, Appendix D ("Registry data", "Burn units") | `fetch.py` (with `fetchlib.py`) | 64 files, 423 MB | 16 |
| `snowflake/` | Sections 1, 2, 3, 6.2 and 9, Appendix D ("Snowflake") | `fetch_raw.py` | 202 files, 30.7 MB | 12 |
| `literature/` | Sections 1, 2, 3, 5.3, 5.4 and 6.2, Appendix D ("Parameters and minting") | `fetch_sources.py` | 24 files, 49.9 MB | 6 |
| `minting/` | Section 6.3, Appendix D ("Parameters and minting"), single statements in Sections 1, 3, 5.4, 7 and 8 | `fetch.py` | 202 files, 21.6 MB | 12 |

All inputs were retrieved on 2026-10-03 (UTC).

## Layout

Each directory has the same layout.

```
<analysis>/
  fetch script        downloads the inputs into raw/ and records them in raw/manifest.json
  analysis.py         rebuilds derived/ from raw/, without network access
  SOURCES.md          sources, licenses and the file table of the paper's snapshot
  raw/README.md       what the inputs are and how to download them
  raw/manifest.json   the paper's manifest: URL, retrieval time, SHA-256, size and license of each input
  derived/            the outputs that ship, and derived/README.md
```

The `raw/` directories hold only `README.md` and `manifest.json`. The
third-party files are not included. Many of them have no license or one that
does not allow redistribution, and the registry extracts of the burn-units
analysis name hosts that Russia's blocking registry lists. Each `raw/README.md`
gives the commands that download the files again, the pinned versions, manual
routes for single files, and a check of the downloads against the paper's
manifest.

The `derived/` directories hold the outputs that carry the paper's numbers,
computed from the paper's inputs. Each `derived/README.md` lists every output
of `analysis.py`, says which ones ship and why the others do not, gives the
SHA-256 of the shipped files and prints the paper's numbers from them without
any download.

## Steps for one analysis

Run them in `data/<analysis>/`. The exact commands, which differ between the
analyses, are in its `raw/README.md` and `derived/README.md`.

1. Keep the paper's manifest with `cp raw/manifest.json manifest.paper.json`.
   The fetch scripts replace the manifest entry of every file they download,
   so this copy, next to `raw/` and not inside it, is the only record of the
   paper's hashes after a download.
2. Download the inputs with the fetch script. This step needs network access.
3. Compare the downloads with `manifest.paper.json`, as `raw/README.md`
   describes. Pinned and archived sources match. Live sources, such as OONI's
   aggregation API or a registrar's price list, can differ.
4. Run `python3 analysis.py`. It runs offline and overwrites the shipped
   files in `derived/`, so copy them first with `cp -r derived derived.paper`
   if you want to keep them. In `snowflake/` and `literature/`, `--out DIR`
   writes the outputs to another directory instead.
5. Compare the outputs with the shipped files with the SHA-256 list in
   `derived/README.md`.

## Requirements

`requirements.txt` in this directory pins the Python packages of the four
pipelines to the versions of the paper's runs. They also need `git` (burn
units and Snowflake) and `pdftotext` from poppler-utils (Snowflake, literature
and minting). The commands in the READMEs are for a POSIX shell, and the
burn-units fetch scripts lock the manifest with `fcntl`, which Windows lacks,
so the pipelines are meant for Linux or macOS.

## Licenses and safety

Files derived from OONI data are licensed CC BY-NC-SA 4.0, as `LICENSE` in the
repository root lists. Russia's registry lists the names, URLs and addresses
under blocking orders, some of them for illegal content.
`burn_units/raw/README.md` describes how its fetch steps filter the registry
files and then delete them, and how to handle the extracts, which must not be
published.
