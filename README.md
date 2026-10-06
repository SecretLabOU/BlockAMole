# Block-A-Mole: code, results and data pipelines

This repository holds the code, the result files and the data pipelines of the
paper *Block-A-Mole: The Sustainability Frontier of Moving-Target Censorship
Resistance*. The model results and both figures can be checked and recomputed
offline from what is here. The four data analyses download their public
inputs again and rebuild their outputs. `PAPER_MAP.md` maps each number and
factual statement of the paper to a file, a key and a command.

## Contents

```
simulations/code/               exact solver (exact.py) and exact experiments R1-R13 (exact_experiments.py),
                                event-driven simulator (rotation_game.py, censor_models.py, theory.py) and
                                its experiments E1-E10 (run_experiments.py), extra_values.py, figure style
simulations/results/            the 23 result files behind the paper's model results
paper/figures/make_figures.py   draws Figures 1 and 2 from the result files and checks them
figures/                        frontier.pdf (Figure 1) and phase.pdf (Figure 2)
data/burn_units/                which names China, Iran and Russia block (Table 1, Sections 1, 3, 6.1, 7, 8
                                and 9, Appendix D)
data/snowflake/                 Snowflake's rendezvous names (Sections 1, 2, 3, 6.2 and 9, Appendix D)
data/literature/                published parameter values with verbatim quotes (Sections 1, 2, 3, 5.3, 5.4
                                and 6.2, Appendix D)
data/minting/                   minting costs and exposure at mint (Sections 1, 3, 5.4, 6.3, 7 and 8,
                                Appendix D)
PAPER_MAP.md                    where each number of the paper comes from
LICENSE                         licenses of code, results and data
requirements.txt                Python packages, pinned to the versions of the paper's runs
```

Each part has its own documentation.

- `simulations/README.md` describes the model code, and
  `simulations/results/README.md` each result file, its SHA-256, the paper's
  numbers in it and how to compare a rerun with it.
- `data/README.md` describes the layout of the four analyses. In each
  `data/<analysis>/`, `raw/README.md` says how to download the inputs,
  `derived/README.md` describes the outputs and prints the paper's numbers
  from them, and `SOURCES.md` lists the sources and their licenses.

## What is not included

- Third-party data. Each `data/<analysis>/raw/` holds only `README.md`, with
  the download instructions, and the paper's `manifest.json`, which records
  the URL, retrieval time (2026-10-03, UTC), SHA-256, size and license of each
  input. Many inputs have no license or one that does not allow
  redistribution, and some name hosts that Russia's blocking registry lists.
  The fetch scripts download the 492 inputs (525 MB in `raw/`) again.
- Outputs that would republish third-party data or name individual hosts,
  such as per-host OONI tables, tables built from rdsys-admin, IODA records
  and daily scores, a registrar's full price list, Chrome's CT log list and the
  full text of documentation pages. The analysis scripts write them again
  after the downloads, and each `derived/README.md` lists them with the reason
  they are left out.
- Figures that the paper does not use. `make_figures.py --all`, the FIG step
  of `exact_experiments.py` and three of the analyses draw them when run.
- The independent implementation behind Appendix B's accuracy check, which
  Appendix E describes as a separate check outside the artifact.
- The independent reimplementation that recomputed the numbers of the four
  data analyses (Appendix D).

## Requirements

- Linux or macOS. `exact_experiments.py` runs its Monte Carlo checks with
  Python's `fork` start method, and the burn-units fetch scripts lock the
  manifest with `fcntl`. Windows has neither. The commands below are for a
  POSIX shell.
- Python 3 with NumPy, SciPy, Matplotlib, pandas and requests.
  `python3 -m pip install -r requirements.txt` installs the versions of the
  paper's runs, NumPy 2.2.4, SciPy 1.15.3, Matplotlib 3.10.1, pandas 3.0.6 and
  requests 2.32.3, as PyPI builds. Other versions are untested.
- The paper's runs used Python 3.13.7 on Ubuntu 25.10, with Ubuntu's packages
  of NumPy (2.2.4+ds-1ubuntu1) and SciPy (1.15.3-1), which use the reference
  BLAS and LAPACK 3.12.1, of Matplotlib (3.10.1+dfsg1-4) with fontTools 4.55.3
  and of requests, and with pandas 3.0.6 from PyPI. The PyPI wheels of NumPy
  and SciPy bundle OpenBLAS and can change the last digits of the exact
  results.
- `git` (2.51.0 in the paper's runs) for the burn-units and Snowflake
  pipelines, `pdftotext` from poppler-utils (25.03.0) for the Snowflake,
  literature and minting analyses, and `pdfinfo` from the same package for
  the Snowflake analysis. Without `pdftotext`, `data/literature/analysis.py`
  falls back to the `pypdf` package, which does not reproduce the shipped
  outputs. Two quotes are not found, and the run exits with status 1.
- `mutool` from MuPDF is optional. With it, `make_figures.py` also checks the
  page size, font sizes and page bounds of each figure.
- The byte-for-byte identity of the figures was verified with the Matplotlib
  build of the paper's runs, the Ubuntu package above. Other builds, such as
  the PyPI wheel of the same version, can embed different bytes while all
  checks pass.

## Quick checks without downloads

These commands run from the repository root and need no network access. The
first three take under a minute in all, and the rerun of the exact suite
about five minutes. `simulations/results/README.md` gives the expected output
of each.

The result files record the SHA-256 of the solver code, and R1 records the
SHA-256 of the ten simulation files it compared. This checks both records.

```bash
python3 - <<'EOF'
import hashlib, json, os

res = "simulations/results"
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
code = {f: sha(f"simulations/code/{f}") for f in ("exact.py", "exact_experiments.py")}
bad = [n for n in sorted(os.listdir(res)) if n.startswith("R") and n.endswith(".json")
       and json.load(open(f"{res}/{n}"))["_meta"]["code_sha256"] != code]
inputs = json.load(open(f"{res}/R1_exact_validation.json"))["inputs"]
bad += [n for n, v in inputs.items()
        if v != {"sha256": sha(f"{res}/{n}"), "bytes": os.path.getsize(f"{res}/{n}")}]
print("mismatch:", bad if bad else "none (13 R files match the code, R1 matches the 10 E files)")
EOF
```

It prints `mismatch: none (13 R files match the code, R1 matches the 10 E
files)`. The `sha256sum -c` block in `simulations/results/README.md` checks
the 23 result files, the two solver files and the two figures, and each
`data/<analysis>/derived/README.md` has one for its shipped outputs.

Redraw both figures into `figures_check/` and compare them with the shipped
ones.

```bash
python3 paper/figures/make_figures.py --outdir figures_check
cmp figures/frontier.pdf figures_check/frontier.pdf
cmp figures/phase.pdf figures_check/phase.pdf
```

The script prints 85 checks of the plotted values and ends with
`all checks passed`. `cmp` prints nothing when the files are identical.

Run the solver's self-test, which prints the accuracy figures of Appendix B,
and print the values that the paper computes outside the result files.

```bash
cd simulations/code
python3 exact.py
python3 extra_values.py
cd ../..
```

`exact.py` ends with `self-test passed`. `extra_values.py` prints the values
of Figure 2's description, Section 5.3, Section 7 and Appendices B and C that
no result file stores, and it recomputes the per-name discovery values of
Appendix C. Its timing line depends on the machine.

Rerun the exact suite in a copy, so that the shipped result files stay
unchanged, and compare the copy with them as `simulations/results/README.md`
describes under "Rerun and compare".

```bash
mkdir ../rerun && cp -r simulations ../rerun/
(cd ../rerun/simulations/code && python3 exact_experiments.py)
```

The exact suite takes about five minutes on a 20-core machine. Its Monte
Carlo checks use one process per core, so it takes longer on fewer cores. To
rerun the simulations too, run
`(cd ../rerun/simulations/code && python3 run_experiments.py && python3 exact_experiments.py)`
instead, which takes about one hour more on one core. A rerun of the
simulations changes `_meta.runtime_s` in their files and therefore the input
hashes that R1 records, so never copy rerun files over the shipped ones.

## Data pipelines

Each analysis runs in its own directory, `data/<analysis>/`, in five steps.

1. Keep the paper's manifest with `cp raw/manifest.json manifest.paper.json`.
   The fetch scripts replace the manifest entry of every file they download.
2. Download the inputs. This step needs network access.
3. Compare the downloads with `manifest.paper.json`, with the snippet in
   `raw/README.md`. Pinned and archived inputs match, while live sources can
   differ, as each `raw/README.md` lists.
4. Rebuild the outputs offline with `analysis.py`.
5. Compare the outputs with the shipped files, with the check in
   `derived/README.md`.

| analysis | download (step 2) | rebuild (step 4) | time and size in the paper's run |
|---|---|---|---|
| `burn_units` | `python3 fetch.py <step>` for each step, after setting `BURN_UNITS_SCRATCH` and pinning gfwlist, as listed under "Rebuild `raw/`" in `raw/README.md` | `python3 analysis.py` | GFWatch lookups take 13 minutes, the registry steps about 6 minutes and each other step a few minutes. 1.4 GB transferred and 423 MB kept. Rebuild about 2 minutes and 0.6 GB of memory |
| `snowflake` | `python3 fetch_raw.py --paper-commits --only collector tormetrics ioda gitlab lit` | `python3 analysis.py --no-fig` | download about 7 minutes, 30.7 MB. Rebuild under a minute |
| `literature` | `python3 fetch_sources.py` | `python3 analysis.py --out derived-rerun` | download a little over a minute plus transfer time, 49.9 MB. Rebuild 30 to 40 s |
| `minting` | `python3 fetch.py` | `python3 analysis.py` | download at least 8 minutes because of the spacing of the requests, 21.6 MB. Rebuild about 10 s |

`analysis.py` overwrites the shipped files in `derived/`, except with
`--out DIR` in the literature and Snowflake analyses. To keep the shipped
files, copy them first with `cp -r derived derived.paper`. Each
`raw/README.md` also describes the pinned versions, the manual route for each
source, what a new download cannot reproduce and what happens when an input
is missing. Each `derived/README.md` says how its outputs differ from the
paper's when the inputs differ.

## Runtimes

The times below are from the reference workstation of Appendix E, a 20-core
Linux machine.

| step | time |
|---|---|
| `python3 exact.py` | about 1 s |
| `python3 extra_values.py` | about 3 s |
| `python3 paper/figures/make_figures.py --outdir figures_check` | under a minute |
| `python3 exact_experiments.py` (R1 to R13) | 302 s of wall time on 20 cores |
| `python3 run_experiments.py` (E1 to E10) | about one hour on one core (3,356 s) |
| the four rebuilds of `data/` | about 4 minutes in all |

## Ethics and safety

- The repository makes no new measurements. The fetch scripts contact only
  public dataset APIs, file hosts, publishers and documentation sites. They
  never resolve, probe or connect to a blocked name, a platform tenant, a
  proxy, a broker or a domain front, and they use no account, API key or
  approval. Requests to one host are paced at least 1.5 to 3 s apart, and the
  minting analysis spaces its crt.sh lookups 20 s apart.
- No human subjects are involved. The Tor and Snowflake statistics are
  published aggregates. Some downloaded inputs name people, for example the
  commenters of public GitHub and GitLab issue threads (user names), the
  authors of the four Snowflake commit patches (names and e-mail addresses)
  and the contributors that Tor's release notes credit, a few with e-mail
  addresses. The analyses identify issue threads by URL and date, comments by
  position and time and commits by hash, never by author, and no downloaded
  input is redistributed.
- Russia's blocking registry lists the names, URLs and addresses under
  blocking orders, some of them for illegal content. Read
  `data/burn_units/raw/README.md` before running the burn-units fetch steps
  `zi`, `zi_history` and `antifilter`. They stream the registry files, keep
  only host names under the 19 platform suffixes, with their decision dates
  for the registry dumps, record the hashes of the full files and delete
  them. Never open, resolve or publish the full files or the extracts. The
  shipped files report registry content only as counts and dates per
  platform.
- Do not redistribute the downloads. Their licenses are in each `SOURCES.md`
  and `raw/manifest.json`.

## Licenses

`LICENSE` gives the terms. The code is under the MIT License. The result
files, figures, derived data, manifests and documentation are under CC BY 4.0,
except the eight files derived from OONI data, which are under CC BY-NC-SA
4.0 as OONI's license requires. Quoted passages of third-party sources keep
their sources' rights.

## Paper map

`PAPER_MAP.md` follows the paper section by section. For each number or
statement it names the file, the key or column and the command that prints
it, most of them from the shipped files without any download.
