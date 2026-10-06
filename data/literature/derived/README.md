# Literature outputs (`data/literature/derived/`)

`../analysis.py` writes the six CSV files in this directory offline, from the
curated values in `../params_spec.py` and the raw files described in
`../raw/README.md`. All six ship with the artifact, so the paper's numbers can
be read here without downloading the sources.

## Regenerate and compare

`analysis.py` needs Python 3 (standard library only), `pdftotext` from
poppler-utils and the 24 raw files (`../raw/README.md`). To rerun it without
overwriting the shipped files and compare the results:

```
cd data/literature
python3 analysis.py --out derived-rerun
for f in derived/*.csv; do cmp "$f" "derived-rerun/${f#derived/}" && echo "same ${f#derived/}"; done
```

`python3 analysis.py` without `--out` writes into this directory. A complete
run takes about 30 to 40 seconds and ends with

```
manifest: 24 raw files checked
quotes verified: 110/110 (strict 108, strict_nohyphen 2, loose 0)
all checks passed
```

It prints a `PROBLEM` line for each raw file that is missing or differs from
`../raw/manifest.json` and for each quote it cannot find at its cited location,
and then exits with status 1. With the paper's raw files, Python 3.13.7 and
pdftotext 25.03.0, a rerun reproduces all six files byte for byte.

`pdftotext` is required to reproduce the shipped files. Without it,
`analysis.py` falls back to the `pypdf` package (`pip install pypdf`). With
pypdf 5.4.0 the run takes 9 to 11 minutes, finds 135 of the 137 quotes (row
N03 and the first supporting quote of row G34, `G34+1`, are not found), writes
`params_table.csv` and `quote_verification.csv` that differ from the shipped
ones and exits with status 1.

## Check the shipped files

This prints `OK` for each of the six files, both as shipped and after
`python3 analysis.py` on the paper's raw files. Run it in `data/literature`. On
macOS, use `shasum -a 256 -c` instead of `sha256sum -c`.

```
sha256sum -c <<'EOF'
aee187b0d61c6aa3e2a8945a5a556a6cff6b7581e98b50b8d7fa633c2b825b37  derived/params_table.csv
9e5932fcd0704343f31198c54a7a23e349aecff0d6833c326f225d0e655e258b  derived/quote_verification.csv
0985540c7606fb010c7d3ef1ae4adb1815267779f37ca20ca66023776bfe070b  derived/derived_values.csv
6c7de53e826482a4573d48ed838581e9d55917a28c258272e2d8a5f7e3a09690  derived/address_layer_mapping.csv
8bd54fed0e95e5a7a23c893baebbdc50afd45c26251a472b1d6d630453127e68  derived/frontier_sensitivity.csv
3dccef43471f9b0cbba035c743fbc85bdabcc6ed2be5e3636cce890cb5810eb6  derived/name_layer_mapping.csv
EOF
```

## Files

All six files ship, and all are written by `python3 analysis.py` (run in
`data/literature`).

| file | rows | content | statement in the paper | SHA-256 as shipped |
|---|---:|---|---|---|
| `params_table.csv` | 110 | One row per published value, from 19 sources (18 papers and one field report): value, units, context, verbatim quote, location, model quantity, comparability and verification status | Appendix D, "Parameters and minting": 110 values from 18 papers and one field report, each with a verbatim quote found at its cited location. Its rows also stand behind the literature statements listed below | `aee187b0d61c6aa3e2a8945a5a556a6cff6b7581e98b50b8d7fa633c2b825b37` |
| `quote_verification.csv` | 137 | Every quote that was checked: the 110 main quotes and 27 supporting quotes (row ids such as `T04+2`), with location, extraction mode, extractor and match tier | Appendix D, "Parameters and minting": "each with a verbatim quote found at its cited location". The file shows this for all 137 quotes (110 main, 27 supporting), 135 exactly and 2 (rows G39 and T09) once hyphens are ignored | `9e5932fcd0704343f31198c54a7a23e349aecff0d6833c326f225d0e655e258b` |
| `derived_values.csv` | 21 | Arithmetic on quoted numbers (shares, means, medians, ratios), each with its formula and input rows. The input numbers occur in the verified quotes or on the cited pages | `gfw_release_to_block_min_max_2016` (2-36 days) backs Section 1 and `gfw_name_block_median_lower_bound_days` (>=256) backs Section 3, "Blocks persist". The other rows are not printed in the paper. In row `tspu_max_failure_rate`, Table 1 is the table of Xue et al. (row T04), not the paper's | `0985540c7606fb010c7d3ef1ae4adb1815267779f37ca20ca66023776bfe070b` |
| `address_layer_mapping.csv` | 18 | Six address-layer scenarios, each with a low, central and high mean time to block E[D_a]. For each: lambda_a for mint intervals of 5 min, 1 h and 1 d, mu/lambda_a for rotation intervals of 60 s, 5 min and 1 h, and the longest rotation interval with c_a >= 0.95 for n = 1, 2, 4 and 8 | Section 5.3, "Wall-clock timescales" uses the central values of two scenarios, 60 s for Tor bridges that the GFW confirms by active probing (`gfw_tor_dpi_probe`) and 600 s for relays listed in the Tor consensus (`gfw_published_directory`). The other values are not printed in the paper | `6c7de53e826482a4573d48ed838581e9d55917a28c258272e2d8a5f7e3a09690` |
| `frontier_sensitivity.csv` | 84 | c_a and the closed-form time-average frontier at alpha = 0.95, for k_max = 4, 8, 16 and 32, n = 2, 4 and 8, and mu/lambda_a = 0.25, 0.5, 1, 2, 3, 3.75 and 10 | A cross-check, not the source of paper numbers. Its rows for n = 8 and mu/lambda_a = 3 agree with the time-average frontiers of Section 5.2, "Exact frontiers" (0.577, 0.840, 0.980 and 1.035 for k_max = 4, 8, 16 and 32), and c_a = 0.996094 at n = 8 and mu/lambda_a = 1 agrees with Section 5.3 | `8bd54fed0e95e5a7a23c893baebbdc50afd45c26251a472b1d6d630453127e68` |
| `name_layer_mapping.csv` | 6 | Six exposure scenarios, three measured for address units exposed in public channels and three assumed lifetimes of a minted name. For each: the per-unit hazard and the smallest mint rate per day that keeps time-average availability at 0.95 with k_max = 8 and c_a = 1, under the constant-rate model and under a per-unit alternative | Not printed in the paper. Its `basis` column marks the measured scenarios as address units, not names, in line with Appendix D's statement that no source measures the burn rate | `3dccef43471f9b0cbba035c743fbc85bdabcc6ed2be5e3636cce890cb5810eb6` |

### Columns of `params_table.csv`

`censor`, `parameter`, `value_or_range` (as the source reports it), `units`,
`context` (years, vantage points, method), `source_key` (the `key` of
`../raw/README.md`), `quote` (verbatim, with whitespace collapsed), `page` (the
1-based PDF page, or `issue body (...)` or `comment N (UTC time)` for the
GitHub issue), `printed_page` (the page number printed in the proceedings,
where the copy has one), `row_id`, `param_type` (`addr_discovery`,
`visibility`, `persistence`, `name_layer`, `collateral` or `arrival`),
`model_quantity` (the model quantity the value informs),
`comparable_to_model` (`yes`, `partial` or `no`, as defined in
`../params_spec.py`), `verified` (`True` if the quote and all supporting quotes
were found at the cited location), `match`, `extra_quotes_verified`,
`citation`, `bibkey` (a short citation key of the source, the key of the
paper's bibliography for the 14 sources that the paper cites, see
`../SOURCES.md`), `raw_file` and `note`.

`quote_verification.csv` has one row per quote, with `row_id` (`+k` marks the
k-th supporting quote), `source_key`, `page`, `mode` (`text`, `layout` or
`html`), `extractor`, `verified`, `match`, `also_found_on` (where a quote that
is not at its cited location does occur) and `quote`.

Match tiers: `strict` is an exact match after normalizing whitespace,
typographic quotes and dashes, ligatures and line-break hyphenation.
`strict_nohyphen` is an exact match once hyphens are ignored, because
`pdftotext` drops the hyphen of a compound word split across lines. `loose`
compares letters and digits only, and no row needs it.

### Notation

`lambda_a`, `mu`, `mu/lambda_a`, `c_a`, `k_max` (`kmax`), `alpha`, `beta`,
`lambda_intro` and the burst size `b` are as in the paper.

- `lambda_disc` is the paper's burn rate lambda_burn. The code in
  `simulations/code` calls the same rate `lam_disc`.
- `delta` is the hazard at which one exposed unit is blocked, one over its
  mean time to block.
- `rho_star` and `per_unit_min_mint_per_day` belong to a per-unit alternative
  in which each live name is burned independently at rate `delta`, so the burn
  rate grows with the number of live names. The paper's model uses an
  aggregate burn rate that does not grow with the pool.
  `const_rate_lambda_disc_per_day` is the aggregate rate equal to the per-unit
  rate at a full pool.
- `gamma` in `model_quantity` is the share of a provider's address space that
  a censor accepts to block. No source measures it, and the paper's model sets
  no such limit, since the censor may block any discovered address. Rows that
  name `gamma` describe collateral regimes.

## Statements in the paper and the rows behind them

| paper | statement | rows (`row_id`) or file |
|---|---|---|
| Section 1, Introduction | The GFW blocked new Tor Browser bridges 2 to 36 days after release | G46 and G27, and row `gfw_release_to_block_min_max_2016` of `derived_values.csv` |
| Section 1, Introduction | Russia and then China extended name blocking to QUIC | T10, G32 |
| Section 1, Introduction | Simulations find that the rate of new proxies is key to availability | N04, F01 |
| Section 2, "Game-theoretic proxy distribution" | In Nasr et al.'s simulations a system is eventually blocked below a critical arrival rate of new proxies | N03 |
| Section 2, "Game-theoretic proxy distribution" | Fares et al. find that the arrival rate of proxies relative to users matters more than the censor's strategy | F01 |
| Section 3, "Position and capabilities" | The TSPU switched to SNI-based QUIC censorship between May 2022 and July 2023, and the GFW has filtered QUIC by SNI since 7 April 2024 | T10, G32, G31 |
| Section 3, "Position and capabilities" | The censor finds endpoints by classifying traffic, probing suspected servers and harvesting distribution channels | G09 and G50 (traffic classification), G01 and G04 (probing), G27 and G46 (default bridges blocked after release) |
| Section 3, "Blocks persist" | GFW name blocks last a median of at least 256 days, and Henan's regional blocks lapse | G43 and H03, and row `gfw_name_block_median_lower_bound_days` of `derived_values.csv` |
| Section 3, "Blocks persist" | The GFW renews an address block during use and lifts it about 12 hours after the service stops | G18, G19 |
| Section 3, "Discovery is an effective rate" | The GFW applies its filter for fully encrypted traffic only to connections toward certain data-center ranges, and to about a quarter of those | G50 |
| Section 3, "Out of scope" | Residual blocks last seconds to minutes after a detected connection | G12, G33, T06, I03 |
| Section 5.3, "Wall-clock timescales" | Tor bridges that the GFW confirms by active probing are blocked on the order of minutes, and no source reports a mean | G03, G45, G01, G04 and G44, and scenario `gfw_tor_dpi_probe` of `address_layer_mapping.csv` |
| Section 5.3, "Wall-clock timescales" | Relays listed in the public Tor consensus were blocked after about 10 minutes | G26, and scenario `gfw_published_directory` of `address_layer_mapping.csv` |
| Section 5.4, "Strategic block timing" | The GFW apparently delayed and batched its blocks of the Tor Browser default bridges of each release in 2015-16 | G27, G28, G47 |
| Section 6.2, Names in a Peer-to-Peer System | Half the 2023 Snowflake proxy pool turned over in about 20 hours | S01 |
| Appendix D, "Parameters and minting" | 110 values from 18 papers and one field report, each with a verbatim quote found at its cited location | `params_table.csv`, `quote_verification.csv` |
| Appendix D, "Parameters and minting" | No source measures the burn rate | No row gives a burn rate for names a defender mints. The closest rows (G26, G27, G29, G30, G46) concern address units exposed in public channels |

This prints the counts and the rows behind each statement from the shipped
files:

```
cd data/literature
python3 - <<'EOF'
import csv

def load(name):
    with open("derived/" + name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

rows, quotes = load("params_table.csv"), load("quote_verification.csv")
files = {r["raw_file"] for r in rows}
print(len(rows), "values from", sum(f.endswith(".pdf") for f in files), "papers and",
      sum(f.endswith(".html") for f in files), "field report")
print(sum(r["verified"] == "True" for r in rows), "values verified,",
      sum(q["verified"] == "True" for q in quotes), "of", len(quotes), "quotes found at the cited location")
by_id = {r["row_id"]: r for r in rows}
for section, ids in [("1 Introduction", "G46 G27 T10 G32 N04 F01"),
                     ("2 Background and Related Work", "N03 F01"),
                     ("3 Threat Model and Scope",
                      "T10 G32 G31 G09 G50 G01 G04 G27 G46 G43 H03 G18 G19 G12 G33 T06 I03"),
                     ("5.3 When Rotation Speed Matters", "G03 G45 G01 G04 G44 G26"),
                     ("5.4 Beyond the Constant-Rate Censor", "G27 G28 G47"),
                     ("6.2 Names in a Peer-to-Peer System", "S01")]:
    print("\n" + section)
    for i in ids.split():
        r = by_id[i]
        value = r["value_or_range"] if r["value_or_range"] != "qualitative" else '"' + r["quote"] + '"'
        print(f"  {i}  {value}\n       {r['context']}; {r['citation']}, PDF p. {r['page']}")
EOF
```

Its first lines are

```
110 values from 18 papers and 1 field report
110 values verified, 137 of 137 quotes found at the cited location
```

## Values computed elsewhere

The address windows at lambda_a T = 15 and 60 and the wall-clock rotation
thresholds of Section 5.3 (mu/lambda_a >= 2.49, about every 24 s, and
mu/lambda_a >= 4.63, about every 13 s) come from the exact solver, not from
this directory. `python3 extra_values.py`, run in `simulations/code`, prints
them, and `PAPER_MAP.md` at the artifact root lists them. This directory
supplies their input, a mean time to block of about one minute for Tor
bridges that the GFW confirms by active probing (`address_layer_mapping.csv`,
row `gfw_tor_dpi_probe`, bound `central`, `E_D_a_seconds` 60). A session of
one hour then has lambda_a T = 3600 / 60 = 60, and a session of one day has
86400 / 60 = 1440.

## License

The CSV files contain short verbatim quotations of the cited sources, with
page references, and arithmetic on quoted numbers. The same quotations are in
`../params_spec.py`. Cite the source when reusing a quote. `../SOURCES.md`
gives each source's license. No OONI data are used here.
