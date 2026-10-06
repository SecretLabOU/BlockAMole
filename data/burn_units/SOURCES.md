# burn_units: sources

The question: at what granularity (the "burn unit") do China, Iran and Russia block
names on shared hosting platforms? Every input is an existing public dataset or a public
dataset API. No network target was probed, scanned, resolved or contacted. No accounts,
API keys or approvals were used. Retrieval dates are 2026-10-03 (UTC). The per-file
URL, retrieval time, sha256, size and license are in `raw/manifest.json` and in the
generated table at the end of this file.

How to rebuild:

- In the artifact, `raw/README.md` gives the download commands, the pins that match this
  snapshot and the handling rules for the registry data.
- `fetch.py` downloads the raw files, one step per source; the step order is in its
  docstring. Running it again skips any file that exists in `raw/` and has a manifest
  entry. A re-run on another day gets newer upstream data. `python3 fetch.py verify`
  re-hashes `raw/` against the manifest.
- `analysis.py` regenerates `derived/` from `raw/` and makes no network access. Run it
  with `python3 analysis.py`. It needs numpy, pandas, matplotlib and git (the Python
  packages are listed in `requirements.txt` at the top of the artifact) and takes about
  2 minutes.

## Sources

**1. GFWatch** (China, DNS filtering). Hoang et al., "How Great is the Great Firewall?
Measuring China's DNS Censorship", USENIX Security 2021. The data come from the public
dashboard's censored-domains lookup callback.

- **Requests:** `POST https://gfwatch.org/_dash-update-component`, the
  `censored-domains-lookup` state. There were 19 queries, one per platform, sent one at
  a time; each took about 40 s, and the next began 3 s after the previous answer. Each
  used the narrow regex `(^|[.])<suffix>$`, with dots written as `[.]` and no
  backslashes. The request payloads are stored in the manifest.
- **Coverage:** the public dataset is frozen at 2024-09-06. GFWatch began on 2020-03-20.
- **Columns:**
  - `first_checked` is the first day a name was seen blocked. For tenant names fed in
    from secondary inputs it is an upper bound on the block onset. For a bare suffix
    (a zone-file SLD tested daily) it is tight.
  - `last_checked` is the last day a name was seen blocked. It is **not** an unblocking
    date.
  - `blocking_rules` is the **latest** inferred rule.
- **License:** the dashboard states no license. Cite the paper. The raw responses are
  not part of the artifact, and `fetch.py gfwatch` downloads them again. Do not
  redistribute them in bulk.
- **Empty results:** `run.app`, `on.aws`, `trycloudflare.com` and `r2.dev` returned
  "not found".

**2. OONI** (CN, IR, RU). License: **CC BY-NC-SA 4.0**. Derived files that use OONI data
carry the same license.

- **Aggregation API:** `https://api.ooni.io/api/v1/aggregation` with
  `test_name=web_connectivity` and `axis_x=domain`.
  - CN: 2026-07, 2026-08 and 2026-09, one call per month.
  - IR and RU: 2024-10-01 to 2025-10-01 and 2025-10-01 to 2026-10-01.
  - The anomaly, confirmed, failure and ok counts are mutually exclusive; checked: they
    sum to `measurement_count`.
- **Day-level follow-up:** a day by domain aggregation for 39 of the most-measured CN
  Azure Front Door endpoints (`*.a02.azurefd.net`) and their zone apex
  `a02.azurefd.net`, 2025-07-01 to 2026-10-01. The list of names is frozen in
  `fetch.py`.
- **Single measurements:** 3 measurement-list calls and 5 raw measurements from
  `/api/v1/measurements` and `/api/v1/raw_measurement`. These are published data, used
  to check the blocking mechanism.
- **Known pitfall:** OONI reports a site that does not exist (NXDOMAIN at both the probe
  and the control) as not anomalous. Single-label `<account>.workers.dev` names are
  therefore excluded. Raw measurement `20260928202308.876948_CN_webconnectivity_af000bcf9372d783`
  shows such a case.

**3. gfwlist** (community proxy-routing list for China; a **weak, lagged proxy**).

- **Source:** `git clone --bare https://github.com/gfwlist/gfwlist`, stored as
  `raw/gfwlist/gfwlist.bundle` (`python3 fetch.py gfwlist`). `analysis.py` clones the
  bundle into a temporary directory inside `data/burn_units` and removes it afterwards.
- **Snapshot:** HEAD `39e9bcede210515011621dae37b20c16b6d16ed8` (2026-10-02). Of 4,285
  commits, 3,929 touch the base64 `gfwlist.txt`.
- **License:** LGPL-2.1.
- **Caveat:** the list routes whole suffixes through a proxy even when the GFW blocks only
  some tenants (for example, `||github.io`). Its dates are not GFW dates.

**4. IRBlock artifact** (Iran, DNS and HTTP filtering). Tai, Sengottuvelavan, Whiting
and Hoang, USENIX Security 2025. Zenodo record 15572895, doi:10.5281/zenodo.15572895.
License: **CC BY 4.0**.

- **Downloaded:** `README.md` and `blocked_domains.tar.gz`. Both md5 checksums match the
  Zenodo record.
- **Contents:** DNS- and HTTP-censored FQDN and apex lists. A name is listed if it was
  blocked on at least 3 days in a scan run from outside Iran over November 2024 to
  2025-01-15; the IRBlock paper says the domain tests ran December 2024 to January 2025. The
  test inputs were TLD zone files, the Citizen Lab test lists, Tranco and Common Crawl.
- **Not in the IRBlock artifact:** dates per name and inferred rules. It holds only these
  lists.
- **Not downloaded:** the per-day IP files, 1.9 GB and 2.1 GB, exceed the 1.5 GB per-file
  cap and are not needed for names. `blocked_ips.tar.gz` is not needed either.
- **Not used:** numbers from the alpha site irblock.org.

**5. Roskomnadzor registry** (Russia, legal blocking orders), through the GitHub mirror
`zapret-info/z-i`.

- **Latest dump:** commit `9133e4327bbcf9adc1cba24360f50e50a6b4d11c`, header "Updated:
  2025-10-01 10:25:04 +0000". The mirror is stale after this date. The source is the
  split files `dump-00..19.csv`, with fields `IP;domain;URL;org;decision;date`.
  `dump.csv.gz` of the same commit lacks the date field.
- **Historical dumps:** 6 commits were picked from a treeless clone as the last commit
  before each date. Their dumps are dated 2021-12-31, 2022-12-31, 2023-12-31, 2024-05-06,
  2024-05-09 and 2024-12-31. The hashes are listed in `fetch.py`.
- **Kept as extracts only:** the dumps list names, URLs and addresses under blocking
  orders, some of them for illegal content. Each dump was streamed to scratch, hashed,
  and filtered to the entries whose domain or URL host lies under a platform suffix
  (columns platform, field, value, decision date). The full file was then deleted. The
  upstream sha256, size and line count are in the manifest, under
  `upstream_files`, or under `upstream_sha256` and `upstream_size_bytes` for the three
  single-file dumps, with `upstream_lines`. No name or URL from the registry was resolved
  or fetched, and only aggregates appear in `derived/`.
- **Decision dates:** the `date` field is the decision date. It can predate the platform,
  so it is not an inclusion date. Inclusion is dated by the snapshot in which an entry
  first appears.
- **License:** no license file. The content is public under Government Decree No. 1101.
  Do not redistribute the extracts.

**6. antifilter.download** (registry-derived lists).

- **What the site says:** the data come from Roskomnadzor under Decree 1101.
  `domains.lst` and `urls.lst` hold the blocked domains and URLs (`raw/antifilter/index.html`).
- **What was used:** only a platform-suffix extract of `domains.lst`. The upstream
  Last-Modified is 2026-10-02 22:39:16 GMT and the upstream hash is in the manifest. An
  exploratory copy of `urls.lst` was parsed once for platform-host counts and then
  deleted; no result uses it.
- **Community edition:** `community.antifilter.download` (domains list and index page) is
  a user-voted routing list, **not** registry data.
- **License:** none stated.

**7. Tranco** top-1M lists (Le Pochat et al., NDSS 2019), for 2024-09-01, 2025-01-01,
2025-10-01 and 2026-10-01. No explicit license; cite.

- **Use:** all 19 bare platform suffixes are in each list, and GFWatch and IRBlock both
  test the Tranco list daily, so the bare suffix was in their test input.
- **Limitation:** Tranco aggregates to pay-level domains with the ICANN part of the PSL.
  It has no tenant names, so it cannot serve as a tenant-level denominator.

**8. Public Suffix List** (`publicsuffix/list`, main, raw file; MPL-2.0). Defines the
tenant (registrable domain) under each platform suffix.

**9. Qualitative primary reports** (read, not measured; cite and quote briefly).

- **Tor GitLab `tpo/anti-censorship/censorship-analysis#40064`** ("[Russia] Blocking of
  webtunnel", opened 2025-06-23).
  - Files: `discussions.json` and the issue JSON from the public API v4 issue endpoint.
  - The GitLab front end returned 403 until the request carried the session cookie that
    its own 403 page sets (`_gitlab_session=1`). The notes API (401) was not used.
- **net4people/bbs#133** ("Cloudflare CDN looks blocked in Iran", 2022-10-10) and
  **#417** ("Blocking of Cloudflare ECH in Russia, 2024-11-05"). Each is one HTML page,
  fetched once without the REST API.

**Considered and not used:**

- GreatFire's analyzer: its lookups can trigger new tests.
- Censored Planet and the GFW Report SNI lists: not among the sources chosen for this
  analysis.
- `irblock.org`: alpha data.
- Commercial passive DNS.

**Scratch-only helpers:** these are not needed to re-run `analysis.py` and are not in
`raw/`.

- A blobless shallow clone and a treeless clone of `zapret-info/z-i`, used to list files
  and commit dates.
- Exploratory API responses.

<!-- BEGIN FILE TABLE (generated by fetch.py sources) -->

| raw file | URL | retrieved (UTC) | size (bytes) | sha256 | license |
|---|---|---|---:|---|---|
| `antifilter/community_domains.lst` | https://community.antifilter.download/list/domains.lst | 2026-10-03T21:57:34Z | 7351 | `1fbb9b3b8862814c84371ff96b59f7b14bd3bcc7462a8396886d222ed8973e94` | community.antifilter.download: no explicit license; community-voted routing list, NOT registry data |
| `antifilter/community_index.html` | https://community.antifilter.download/ | 2026-10-03T21:57:32Z | 2096 | `d697e40592e1931da9635eebaf23945ce33645a7e5ee7f9fd485445ce3d707db` | community.antifilter.download: no explicit license; community-voted routing list, NOT registry data |
| `antifilter/domains_platform_extract.lst` | https://antifilter.download/list/domains.lst | 2026-10-03T21:57:21Z | 558671 | `260d7620118bca8ed84779a8a1b9a4d5ed434b045101370d9f52826ed1679f19` | antifilter.download: no explicit license; lists are derived from the Roskomnadzor registry (Government Decree No. 1101 of 2012-10-26) |
| `antifilter/index.html` | https://antifilter.download/ | 2026-10-03T21:57:19Z | 21708 | `7edb84214a21c806c2523206f5aefca25c25115e65383a8fbb1726fc40bf5908` | antifilter.download: no explicit license; lists are derived from the Roskomnadzor registry (Government Decree No. 1101 of 2012-10-26) |
| `gfwatch/lookup_appspot_com.json` | https://gfwatch.org/_dash-update-component | 2026-10-03T21:47:39Z | 18207590 | `3f59ce364fa991862f31e602d238092428c4d6bc1c664537fba134a850817ac9` | GFWatch dashboard (gfwatch.org), Hoang et al. USENIX Security 2021; no explicit license on the dashboard; cite, do not redistribute bulk |
| `gfwatch/lookup_azurefd_net.json` | https://gfwatch.org/_dash-update-component | 2026-10-03T21:51:03Z | 1014 | `3a129fd346754a142da4a6d5d9ead0d4ab6f48d1b8c9cd1a3a3039e71a8285fc` | GFWatch dashboard (gfwatch.org), Hoang et al. USENIX Security 2021; no explicit license on the dashboard; cite, do not redistribute bulk |
| `gfwatch/lookup_azurewebsites_net.json` | https://gfwatch.org/_dash-update-component | 2026-10-03T21:50:27Z | 12068 | `270d714de85c3037722f0e86bf4acf767a32d06ac3ad4e2fa0c1386e7040c792` | GFWatch dashboard (gfwatch.org), Hoang et al. USENIX Security 2021; no explicit license on the dashboard; cite, do not redistribute bulk |
| `gfwatch/lookup_cloudfront_net.json` | https://gfwatch.org/_dash-update-component | 2026-10-03T21:49:49Z | 50661 | `22c822354066ad975dd5b3b5519f367196eee4e1d237d4eba5b6bebdf5bab62f` | GFWatch dashboard (gfwatch.org), Hoang et al. USENIX Security 2021; no explicit license on the dashboard; cite, do not redistribute bulk |
| `gfwatch/lookup_deno_dev.json` | https://gfwatch.org/_dash-update-component | 2026-10-03T21:53:19Z | 540 | `30643edabd0cf1ec65be822a51ddef2a71f3fc5f8b5b2bf7789e38a6abdb9520` | GFWatch dashboard (gfwatch.org), Hoang et al. USENIX Security 2021; no explicit license on the dashboard; cite, do not redistribute bulk |
| `gfwatch/lookup_firebaseapp_com.json` | https://gfwatch.org/_dash-update-component | 2026-10-03T21:49:10Z | 1939 | `f79976bb3cfbe166113a245150a3af425c7a3ffda3fe34b3f42ccbf4c46b3e52` | GFWatch dashboard (gfwatch.org), Hoang et al. USENIX Security 2021; no explicit license on the dashboard; cite, do not redistribute bulk |
| `gfwatch/lookup_fly_dev.json` | https://gfwatch.org/_dash-update-component | 2026-10-03T21:54:04Z | 1560 | `49e2f6baae08522c82afc6b2ace9e9180f1f35414c5fe8039d30bc2cccfa7067` | GFWatch dashboard (gfwatch.org), Hoang et al. USENIX Security 2021; no explicit license on the dashboard; cite, do not redistribute bulk |
| `gfwatch/lookup_github_io.json` | https://gfwatch.org/_dash-update-component | 2026-10-03T21:43:53Z | 112537 | `be2e7426f83f5f56b4e16df756030df1b3399bad98dc9d0cd7d7d88852a10268` | GFWatch dashboard (gfwatch.org), Hoang et al. USENIX Security 2021; no explicit license on the dashboard; cite, do not redistribute bulk |
| `gfwatch/lookup_herokuapp_com.json` | https://gfwatch.org/_dash-update-component | 2026-10-03T21:46:55Z | 35051137 | `e34ce9f6f949b46495918acd13795d58420a58d7cc4d3691a4551cbbd59ff396` | GFWatch dashboard (gfwatch.org), Hoang et al. USENIX Security 2021; no explicit license on the dashboard; cite, do not redistribute bulk |
| `gfwatch/lookup_netlify_app.json` | https://gfwatch.org/_dash-update-component | 2026-10-03T21:46:12Z | 4276 | `b2fd224a9eae6c64e8caad4cd27fc49b7e4e6c4de8383c3205b6d0d7eee3ec11` | GFWatch dashboard (gfwatch.org), Hoang et al. USENIX Security 2021; no explicit license on the dashboard; cite, do not redistribute bulk |
| `gfwatch/lookup_on_aws.json` | https://gfwatch.org/_dash-update-component | 2026-10-03T21:52:32Z | 258 | `4904c23cdc00f3de3c4214da794f0f9e2abe4262fa27ebe01b5ad924d5058795` | GFWatch dashboard (gfwatch.org), Hoang et al. USENIX Security 2021; no explicit license on the dashboard; cite, do not redistribute bulk |
| `gfwatch/lookup_onrender_com.json` | https://gfwatch.org/_dash-update-component | 2026-10-03T21:54:50Z | 1164 | `8e30cc1cdc6377793843aa2337057a73937cf921d3eaf5e890538288b6b4d621` | GFWatch dashboard (gfwatch.org), Hoang et al. USENIX Security 2021; no explicit license on the dashboard; cite, do not redistribute bulk |
| `gfwatch/lookup_pages_dev.json` | https://gfwatch.org/_dash-update-component | 2026-10-03T21:42:59Z | 2958 | `ad9f9ed9cd5aae745985e42b6ff72ef60571d45055d1545da1cc115453be50b6` | GFWatch dashboard (gfwatch.org), Hoang et al. USENIX Security 2021; no explicit license on the dashboard; cite, do not redistribute bulk |
| `gfwatch/lookup_r2_dev.json` | https://gfwatch.org/_dash-update-component | 2026-10-03T21:56:07Z | 258 | `d39a11cec57ec42525fc755689cf4de2234b7c3bbbe04243cfdf919e4c9091cc` | GFWatch dashboard (gfwatch.org), Hoang et al. USENIX Security 2021; no explicit license on the dashboard; cite, do not redistribute bulk |
| `gfwatch/lookup_run_app.json` | https://gfwatch.org/_dash-update-component | 2026-10-03T21:51:45Z | 259 | `5dfbe8ed3d029bf58a0d8054250d11974f1ae1429308af64b6a49da0f6047155` | GFWatch dashboard (gfwatch.org), Hoang et al. USENIX Security 2021; no explicit license on the dashboard; cite, do not redistribute bulk |
| `gfwatch/lookup_trycloudflare_com.json` | https://gfwatch.org/_dash-update-component | 2026-10-03T21:55:32Z | 262 | `a8b5589e171f3988549e0bb10f0adce593a3fce800b289bcb1305e720f825b58` | GFWatch dashboard (gfwatch.org), Hoang et al. USENIX Security 2021; no explicit license on the dashboard; cite, do not redistribute bulk |
| `gfwatch/lookup_vercel_app.json` | https://gfwatch.org/_dash-update-component | 2026-10-03T21:45:24Z | 29522296 | `b1e8aff26dbde6345d1fc4a1f3aa6182d82189dacd31b978a0024ddafe880093` | GFWatch dashboard (gfwatch.org), Hoang et al. USENIX Security 2021; no explicit license on the dashboard; cite, do not redistribute bulk |
| `gfwatch/lookup_web_app.json` | https://gfwatch.org/_dash-update-component | 2026-10-03T21:48:24Z | 1075 | `f9806353e8dfb92bccdaa0e3f1b8782f6cec8da3b42fdb74b4614a0b1480455f` | GFWatch dashboard (gfwatch.org), Hoang et al. USENIX Security 2021; no explicit license on the dashboard; cite, do not redistribute bulk |
| `gfwatch/lookup_workers_dev.json` | https://gfwatch.org/_dash-update-component | 2026-10-03T21:44:41Z | 6306940 | `cbc339601c593c8db1d90797e6357581278b6167bc0c313dbb637c72262d551d` | GFWatch dashboard (gfwatch.org), Hoang et al. USENIX Security 2021; no explicit license on the dashboard; cite, do not redistribute bulk |
| `gfwlist/gfwlist.bundle` | https://github.com/gfwlist/gfwlist (git clone --bare; git bundle create --all) | 2026-10-03T21:45:10Z | 93933444 | `2723d584673d69b27d43823728dd6b46f619b894545029c98868e0974461d06d` | LGPL-2.1 (gfwlist/gfwlist COPYING.txt) |
| `irblock/README.md` | https://zenodo.org/api/records/15572895/files/README.md/content | 2026-10-03T21:48:12Z | 8537 | `523110f96b41a807fd3b56e40392fad9be96508fed9d5b93125ac5c8e43671a0` | CC-BY-4.0 (Zenodo record 10.5281/zenodo.15572895) |
| `irblock/blocked_domains.tar.gz` | https://zenodo.org/api/records/15572895/files/blocked_domains.tar.gz/content | 2026-10-03T21:48:14Z | 69389814 | `168dd389671853bb9bc7009e55adbc92866ab1ececa549c1fa6255706613e83a` | CC-BY-4.0 (Zenodo record 10.5281/zenodo.15572895) |
| `irblock/zenodo_record_15572895.json` | https://zenodo.org/api/records/15572895 | 2026-10-03T21:48:10Z | 7382 | `e5d916dc84d9a73647223b6219de507ae61a75625d8cbb15289472925e579c0a` | CC-BY-4.0 (Zenodo record 10.5281/zenodo.15572895) |
| `ooni/agg_CN_2026-07-01_2026-08-01_domain.json` | https://api.ooni.io/api/v1/aggregation?probe_cc=CN&test_name=web_connectivity&since=2026-07-01&until=2026-08-01&axis_x=domain | 2026-10-03T21:57:48Z | 19735929 | `ae50f8157391751b5b74923206530b0d6f01ee21390eaa34f55044df36fc0951` | CC BY-NC-SA 4.0 (OONI data policy); derived data must carry the same license |
| `ooni/agg_CN_2026-08-01_2026-09-01_domain.json` | https://api.ooni.io/api/v1/aggregation?probe_cc=CN&test_name=web_connectivity&since=2026-08-01&until=2026-09-01&axis_x=domain | 2026-10-03T21:57:58Z | 20412861 | `ec30cac5f4755c184b0f2225ffccaeacec55a306ae4b7adc7f57c1ec060906c4` | CC BY-NC-SA 4.0 (OONI data policy); derived data must carry the same license |
| `ooni/agg_CN_2026-09-01_2026-10-01_domain.json` | https://api.ooni.io/api/v1/aggregation?probe_cc=CN&test_name=web_connectivity&since=2026-09-01&until=2026-10-01&axis_x=domain | 2026-10-03T21:58:08Z | 23312018 | `5523e7437ea3b9be673db3673e3388be5eda3e7bf9f6e69dc345cd1e7d78996c` | CC BY-NC-SA 4.0 (OONI data policy); derived data must carry the same license |
| `ooni/agg_CN_azurefd40_2025-07-01_2026-05-01_day_domain.json` | https://api.ooni.io/api/v1/aggregation?probe_cc=CN&test_name=web_connectivity&since=2025-07-01&until=2026-05-01&domain=rdipowerplatformfd-e5hhgqaahef7fbdr.a02.azurefd.net%2Cp-entitc-frontdoor-endpoint-ecgqa0gseehhf0cr.a02.azurefd.net%2Ciam-prod3-hfg4hab4addda2gf.a02.azurefd.net%2Cp2blobstore-cdata-hya0gqaxdabaarax.a02.azurefd.net%2Cfd-plzconn-cdn-op-msop-frontdoor-premium-fhb4bxgcffamgfbh.a02.azurefd.net%2Cmedia-bkccefdngbaqgdb4.a02.azurefd.net%2Cpictimecloudaf-pub-g3csanfebyefg3dm.a02.azurefd.net%2Cu9kh456577-e4h5bxhbgfencxay.a02.azurefd.net%2Cnd4p776834-ezhnhybmgce7ghga.a02.azurefd.net%2Cbrgfrontdoorendpoint-ftbgdxcqg6dqhnfb.a02.azurefd.net%2Cb169868226-hvcucae9a5f8eagb.a02.azurefd.net%2Ccarrabbasprod-esdja5eaccfgfnc7.a02.azurefd.net%2C9a9f179586-bfffgmekb0buh4cm.a02.azurefd.net%2Cfd-rapp-cdn-fzgxcpehc0ccdxeu.a02.azurefd.net%2Capt-prod-d9d6gsemdedkd3gd.a02.azurefd.net%2Cpictime7eus1public-pub-hdf3hecqdpaqeuev.a02.azurefd.net%2Cvg71233921-h0bndhepaagbfxdm.a02.azurefd.net%2Css-p13n-a-route-cqashxc7gshebahk.a02.azurefd.net%2Cwebcomponents-dub9hvc3eachc4e6.a02.azurefd.net%2Cp62a367490-gwbfhwe4bce2bjhy.a02.azurefd.net%2Contariohealth-gbfed6fje7c8e4bj.a02.azurefd.net%2Cmt-pg1-us-east-1-cdn-e2f3g4ftanc9agcx.a02.azurefd.net%2Cimages-h9gsgmdkgwcrd8dq.a02.azurefd.net%2Carthrexprod-dtd2bphrh2btedff.a02.azurefd.net%2C64v8402753-aaabcecgf7h3dmcd.a02.azurefd.net%2Ctapn916417-b0e3hmg6hqd4b5ep.a02.azurefd.net%2Cecolab-intelligence-fd-p-bxgxhwd3agfqgtbj.a02.azurefd.net%2Crc-d2c-stg-secondary-cdn-frontservicediscovery-h8gxcshuhwcndrcz.a02.azurefd.net%2Cv5ge487810-hze0dbdzeqg4fhbr.a02.azurefd.net%2Ctemplafy-hive-frontdoor-cdn-f3dhb0azaufdckh0.a02.azurefd.net%2Chs-app-endpoint-gnfjfugjaxgta4c6.a02.azurefd.net%2Ccompanyportal-bwhfc4dqb5cqguhr.a02.azurefd.net%2Cstorageprodcdnendpoint-fcazfkcfcpdjbjgg.a02.azurefd.net%2Cendpoint-production-arcsdsccamezhgfe.a02.azurefd.net%2Ctygraphfd-efe2cbaperfhesgt.a02.azurefd.net%2Cvuw2182850-hcfkacagcfgqfzb4.a02.azurefd.net%2Caro-gsa4hgdbd8d0d9e3.a02.azurefd.net%2C36q2444993-dfhhb6eke7gyd3b3.a02.azurefd.net%2Cstorage-prod-f0hmanfcbecneyff.a02.azurefd.net%2Ca02.azurefd.net&axis_x=measurement_start_day&axis_y=domain | 2026-10-03T22:23:02Z | 271943 | `4cebaa5cadcc9b2cfce3de369e6d5a815d4de856041ffcd8af06fcab82ac418d` | CC BY-NC-SA 4.0 (OONI data policy); derived data must carry the same license |
| `ooni/agg_CN_azurefd40_2026-05-01_2026-10-01_day_domain.json` | https://api.ooni.io/api/v1/aggregation?probe_cc=CN&test_name=web_connectivity&since=2026-05-01&until=2026-10-01&domain=rdipowerplatformfd-e5hhgqaahef7fbdr.a02.azurefd.net%2Cp-entitc-frontdoor-endpoint-ecgqa0gseehhf0cr.a02.azurefd.net%2Ciam-prod3-hfg4hab4addda2gf.a02.azurefd.net%2Cp2blobstore-cdata-hya0gqaxdabaarax.a02.azurefd.net%2Cfd-plzconn-cdn-op-msop-frontdoor-premium-fhb4bxgcffamgfbh.a02.azurefd.net%2Cmedia-bkccefdngbaqgdb4.a02.azurefd.net%2Cpictimecloudaf-pub-g3csanfebyefg3dm.a02.azurefd.net%2Cu9kh456577-e4h5bxhbgfencxay.a02.azurefd.net%2Cnd4p776834-ezhnhybmgce7ghga.a02.azurefd.net%2Cbrgfrontdoorendpoint-ftbgdxcqg6dqhnfb.a02.azurefd.net%2Cb169868226-hvcucae9a5f8eagb.a02.azurefd.net%2Ccarrabbasprod-esdja5eaccfgfnc7.a02.azurefd.net%2C9a9f179586-bfffgmekb0buh4cm.a02.azurefd.net%2Cfd-rapp-cdn-fzgxcpehc0ccdxeu.a02.azurefd.net%2Capt-prod-d9d6gsemdedkd3gd.a02.azurefd.net%2Cpictime7eus1public-pub-hdf3hecqdpaqeuev.a02.azurefd.net%2Cvg71233921-h0bndhepaagbfxdm.a02.azurefd.net%2Css-p13n-a-route-cqashxc7gshebahk.a02.azurefd.net%2Cwebcomponents-dub9hvc3eachc4e6.a02.azurefd.net%2Cp62a367490-gwbfhwe4bce2bjhy.a02.azurefd.net%2Contariohealth-gbfed6fje7c8e4bj.a02.azurefd.net%2Cmt-pg1-us-east-1-cdn-e2f3g4ftanc9agcx.a02.azurefd.net%2Cimages-h9gsgmdkgwcrd8dq.a02.azurefd.net%2Carthrexprod-dtd2bphrh2btedff.a02.azurefd.net%2C64v8402753-aaabcecgf7h3dmcd.a02.azurefd.net%2Ctapn916417-b0e3hmg6hqd4b5ep.a02.azurefd.net%2Cecolab-intelligence-fd-p-bxgxhwd3agfqgtbj.a02.azurefd.net%2Crc-d2c-stg-secondary-cdn-frontservicediscovery-h8gxcshuhwcndrcz.a02.azurefd.net%2Cv5ge487810-hze0dbdzeqg4fhbr.a02.azurefd.net%2Ctemplafy-hive-frontdoor-cdn-f3dhb0azaufdckh0.a02.azurefd.net%2Chs-app-endpoint-gnfjfugjaxgta4c6.a02.azurefd.net%2Ccompanyportal-bwhfc4dqb5cqguhr.a02.azurefd.net%2Cstorageprodcdnendpoint-fcazfkcfcpdjbjgg.a02.azurefd.net%2Cendpoint-production-arcsdsccamezhgfe.a02.azurefd.net%2Ctygraphfd-efe2cbaperfhesgt.a02.azurefd.net%2Cvuw2182850-hcfkacagcfgqfzb4.a02.azurefd.net%2Caro-gsa4hgdbd8d0d9e3.a02.azurefd.net%2C36q2444993-dfhhb6eke7gyd3b3.a02.azurefd.net%2Cstorage-prod-f0hmanfcbecneyff.a02.azurefd.net%2Ca02.azurefd.net&axis_x=measurement_start_day&axis_y=domain | 2026-10-03T22:21:34Z | 268972 | `dfdec416ba79554eaf5e3896ce41c1cbfa179b87567f0260793d41af85a77834` | CC BY-NC-SA 4.0 (OONI data policy); derived data must carry the same license |
| `ooni/agg_IR_2024-10-01_2025-10-01_domain.json` | https://api.ooni.io/api/v1/aggregation?probe_cc=IR&test_name=web_connectivity&since=2024-10-01&until=2025-10-01&axis_x=domain | 2026-10-03T22:25:11Z | 369870 | `5d64b1223b0a8028a1857df3a0ea89eafa7ac35179d5aeedae0c70ab80009171` | CC BY-NC-SA 4.0 (OONI data policy); derived data must carry the same license |
| `ooni/agg_IR_2025-10-01_2026-10-01_domain.json` | https://api.ooni.io/api/v1/aggregation?probe_cc=IR&test_name=web_connectivity&since=2025-10-01&until=2026-10-01&axis_x=domain | 2026-10-03T21:58:19Z | 391032 | `e642cfff8118511151a2d688fd4ef281f49b7c7350ef64a1f2d6b0fc4289819e` | CC BY-NC-SA 4.0 (OONI data policy); derived data must carry the same license |
| `ooni/agg_RU_2024-10-01_2025-10-01_domain.json` | https://api.ooni.io/api/v1/aggregation?probe_cc=RU&test_name=web_connectivity&since=2024-10-01&until=2025-10-01&axis_x=domain | 2026-10-03T22:25:24Z | 463929 | `e5509d91905e4f04f602fc490dde48cc853d185461685548935fef413bc297d9` | CC BY-NC-SA 4.0 (OONI data policy); derived data must carry the same license |
| `ooni/agg_RU_2025-10-01_2026-10-01_domain.json` | https://api.ooni.io/api/v1/aggregation?probe_cc=RU&test_name=web_connectivity&since=2025-10-01&until=2026-10-01&axis_x=domain | 2026-10-03T21:58:27Z | 9192002 | `123bc301b57007d2ed6e1ac0f0bcc74c086ba80446b97aa05511c3e3d7e836b6` | CC BY-NC-SA 4.0 (OONI data policy); derived data must carry the same license |
| `ooni/list_CN_azurefd_rdipowerplatformfd_2026-08-01_2026-09-15.json` | https://api.ooni.io/api/v1/measurements?probe_cc=CN&test_name=web_connectivity&domain=rdipowerplatformfd-e5hhgqaahef7fbdr.a02.azurefd.net&since=2026-08-01&until=2026-09-15&limit=30&order_by=measurement_start_time&order=asc | 2026-10-03T22:22:14Z | 13249 | `60e25ca24034577cb5b01c6a365e6bec1c92e4d19a724cacc76aefd2425ba083` | CC BY-NC-SA 4.0 (OONI data policy); derived data must carry the same license |
| `ooni/list_CN_workersdev_blocked_2026-09.json` | https://api.ooni.io/api/v1/measurements?probe_cc=CN&test_name=web_connectivity&domain=cva.engineer-c03.workers.dev&since=2026-09-01&until=2026-10-01&limit=5 | 2026-10-03T22:24:27Z | 3961 | `28a32a91050da481d5d49c4d874b0ad6cfc1df19070b14e82935d02373a0bf10` | CC BY-NC-SA 4.0 (OONI data policy); derived data must carry the same license |
| `ooni/list_CN_workersdev_clear_2026-09.json` | https://api.ooni.io/api/v1/measurements?probe_cc=CN&test_name=web_connectivity&domain=ancient-bird-0990.isvao15mcrxi.workers.dev&since=2026-09-01&until=2026-10-01&limit=5 | 2026-10-03T22:24:29Z | 2389 | `e715774c26e7d6e97b3a9e24a1c1d1f3e28c1675ebebd0712908b8c14e0bd891` | CC BY-NC-SA 4.0 (OONI data policy); derived data must carry the same license |
| `ooni/raw_20260801153920.708278_CN_webconnectivity_9fd6b6e49bbb4a16.json` | https://api.ooni.io/api/v1/raw_measurement?measurement_uid=20260801153920.708278_CN_webconnectivity_9fd6b6e49bbb4a16 | 2026-10-03T22:22:16Z | 35850 | `848dd553dcd5bdfa54ea1f02b496727cf2a60ad30fb45b96e3929119906ca3ae` | CC BY-NC-SA 4.0 (OONI data policy); derived data must carry the same license |
| `ooni/raw_20260814204453.616266_CN_webconnectivity_9b044dff6f7db0e0.json` | https://api.ooni.io/api/v1/raw_measurement?measurement_uid=20260814204453.616266_CN_webconnectivity_9b044dff6f7db0e0 | 2026-10-03T22:22:18Z | 35855 | `bcc500a36022a51cc36c4121f4a7a0a3aa500cfb965f64981954f56d08782505` | CC BY-NC-SA 4.0 (OONI data policy); derived data must carry the same license |
| `ooni/raw_20260907101803.992549_CN_webconnectivity_4f4b68ede6f7b7fa.json` | https://api.ooni.io/api/v1/raw_measurement?measurement_uid=20260907101803.992549_CN_webconnectivity_4f4b68ede6f7b7fa | 2026-10-03T22:22:20Z | 56233 | `ddea1c2b9976e36a2da4268fafbfd44009f707e6436a0abed831c9850219182a` | CC BY-NC-SA 4.0 (OONI data policy); derived data must carry the same license |
| `ooni/raw_20260928202308.876948_CN_webconnectivity_af000bcf9372d783.json` | https://api.ooni.io/api/v1/raw_measurement?measurement_uid=20260928202308.876948_CN_webconnectivity_af000bcf9372d783 | 2026-10-03T22:24:33Z | 4856 | `29d39a7d1ee5c869e170d19a3e5c0ea61a32db4febe7a0ee64929a474e1c858a` | CC BY-NC-SA 4.0 (OONI data policy); derived data must carry the same license |
| `ooni/raw_20260929202119.196158_CN_webconnectivity_3d44e33e0974bd1a.json` | https://api.ooni.io/api/v1/raw_measurement?measurement_uid=20260929202119.196158_CN_webconnectivity_3d44e33e0974bd1a | 2026-10-03T22:24:31Z | 15017 | `d7a95b1428953443513afc8f01eaa447a40a7173044a67028b53d558c9d0cb45` | CC BY-NC-SA 4.0 (OONI data policy); derived data must carry the same license |
| `psl/public_suffix_list.dat` | https://raw.githubusercontent.com/publicsuffix/list/main/public_suffix_list.dat | 2026-10-03T21:56:59Z | 334645 | `102b252c18b5f87f4c81f017e75282a82c18e00cd0c2e601b5b02a0f7a601f2c` | MPL-2.0 (Public Suffix List) |
| `qualitative/net4people_bbs_133.html` | https://github.com/net4people/bbs/issues/133 | 2026-10-03T21:57:42Z | 304110 | `6b85500b75c4898239fe607ee80b1b1b0ba23d5d64a451025e837982fe7d05d3` | net4people/bbs forum post (GitHub); no explicit license; cite, quote briefly |
| `qualitative/net4people_bbs_417.html` | https://github.com/net4people/bbs/issues/417 | 2026-10-03T21:57:44Z | 377250 | `27314507e5149d0b8e657e732022333b40b3d480c913905ee59b6a2341ff091b` | net4people/bbs forum post (GitHub); no explicit license; cite, quote briefly |
| `qualitative/tor_gitlab_40064_discussions.json` | https://gitlab.torproject.org/tpo/anti-censorship/censorship-analysis/-/issues/40064/discussions.json | 2026-10-03T22:01:23Z | 250224 | `64a1606c0ac3eddbeec8ec5302650f3bc7b21c5e44d013ee3c4095ba08a14a3b` | Tor Project GitLab issue comments; no explicit license; cite, quote briefly |
| `qualitative/tor_gitlab_40064_issue.json` | https://gitlab.torproject.org/api/v4/projects/tpo%2Fanti-censorship%2Fcensorship-analysis/issues/40064 | 2026-10-03T21:57:40Z | 2309 | `de7824b2000391ba68d855d7670fd07813996ec9b04dd3545f4d3d6e8235402f` | Tor Project GitLab issue body; no explicit license; cite, quote briefly |
| `tranco/tranco_2024-09-01_4Q6GX_top1m.csv` | https://tranco-list.eu/download/4Q6GX/1000000 | 2026-10-03T21:57:01Z | 22584082 | `df7dc54be4d2a738ba345d20881dcd7a189046aef6a8462fa7b5b69eadf9901e` | Tranco list (Le Pochat et al., NDSS 2019), tranco-list.eu; free for research, no explicit license; cite |
| `tranco/tranco_2024-09-01_meta.json` | https://tranco-list.eu/api/lists/date/2024-09-01 | 2026-10-03T21:56:59Z | 419 | `5816bb96a368adf35b03240fea820f45a60b7bd5313be19a5e837eaebf4d687f` | Tranco list (Le Pochat et al., NDSS 2019), tranco-list.eu; free for research, no explicit license; cite |
| `tranco/tranco_2025-01-01_24LY9_top1m.csv` | https://tranco-list.eu/download/24LY9/1000000 | 2026-10-03T21:57:05Z | 22664230 | `d871c6c9c083c4eca55f1cb0e5c053b92e64cf05e3e908396a37de916d24a457` | Tranco list (Le Pochat et al., NDSS 2019), tranco-list.eu; free for research, no explicit license; cite |
| `tranco/tranco_2025-01-01_meta.json` | https://tranco-list.eu/api/lists/date/2025-01-01 | 2026-10-03T21:57:03Z | 419 | `5ec598bc42cabfc73e1290cc0a15ac59e1fcccf3647aa11f2f3e017492688666` | Tranco list (Le Pochat et al., NDSS 2019), tranco-list.eu; free for research, no explicit license; cite |
| `tranco/tranco_2025-10-01_9WZV2_top1m.csv` | https://tranco-list.eu/download/9WZV2/1000000 | 2026-10-03T21:57:09Z | 22247335 | `8f2cee5e6531cb62a3fb44506216601d3d25cdd12a5cb6d0dd294e64f804ad89` | Tranco list (Le Pochat et al., NDSS 2019), tranco-list.eu; free for research, no explicit license; cite |
| `tranco/tranco_2025-10-01_meta.json` | https://tranco-list.eu/api/lists/date/2025-10-01 | 2026-10-03T21:57:07Z | 419 | `e9f41f63848787914bf0275c52108cd46b6407bcf18e80450721ee41f9c6f80a` | Tranco list (Le Pochat et al., NDSS 2019), tranco-list.eu; free for research, no explicit license; cite |
| `tranco/tranco_2026-10-01_Y83YG_top1m.csv` | https://tranco-list.eu/download/Y83YG/1000000 | 2026-10-03T21:57:18Z | 22604258 | `b3f7246defc90158d80324b59c75fb78cf7bf0ed1d2f11a1279caf88e5a6a7c0` | Tranco list (Le Pochat et al., NDSS 2019), tranco-list.eu; free for research, no explicit license; cite |
| `tranco/tranco_2026-10-01_meta.json` | https://tranco-list.eu/api/lists/date/2026-10-01 | 2026-10-03T21:57:16Z | 419 | `63e891621c9ddd71e6daeaf878d7e02598c7ee3b3ec400645501b5230a6b76f7` | Tranco list (Le Pochat et al., NDSS 2019), tranco-list.eu; free for research, no explicit license; cite |
| `zi/extract_2025-10-01_9133e4327b.csv` | https://github.com/zapret-info/z-i/tree/9133e4327bbcf9adc1cba24360f50e50a6b4d11c (dump-00..19.csv) | 2026-10-03T22:12:49Z | 1013323 | `1e74dfe5340a25c191d23e270a95663d2f973baa6597350de3c2e5c002456cc0` | No license file in zapret-info/z-i; Roskomnadzor registry dump (public under Decree 1101). Extract only; do not redistribute. |
| `zi_history/extract_2022-01-01_d291c7d7d7.csv` | https://raw.githubusercontent.com/zapret-info/z-i/d291c7d7d7e406fbd8d08b1c9413a4ebb51fc42a/dump.csv | 2026-10-03T22:15:26Z | 211904 | `791384e3cea18e5785945d0e6e25a7d144a3ab9c7d4e1d42ba243afde61a9259` | No license file in zapret-info/z-i; Roskomnadzor registry dump (public under Decree 1101). Extract only; do not redistribute. |
| `zi_history/extract_2023-01-01_9e1f59db33.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9e1f59db3360f5caaaf8ebde0581e867b7fff4c8/dump.csv | 2026-10-03T22:15:42Z | 362936 | `1a176c5d61c9f038669f54146f69ec5806888f88e489a3383ab148aa1048be26` | No license file in zapret-info/z-i; Roskomnadzor registry dump (public under Decree 1101). Extract only; do not redistribute. |
| `zi_history/extract_2024-01-01_99aec91c81.csv` | https://raw.githubusercontent.com/zapret-info/z-i/99aec91c810505e9b60129cc70c0f8c58411a11c/dump.csv | 2026-10-03T22:15:58Z | 447777 | `01338fa270fbb91523edd8ebb026ff13e3d1bb09bb1864b57d4b3804873cbb0e` | No license file in zapret-info/z-i; Roskomnadzor registry dump (public under Decree 1101). Extract only; do not redistribute. |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | https://github.com/zapret-info/z-i/tree/94b080bebc7338dcbb6045ad6147656a1db974e3 (splits) | 2026-10-03T22:17:13Z | 568451 | `ac88e549ec17e6955f5f66edaf3bb1defa03cca7cceddd3834bd57fe0312e20a` | No license file in zapret-info/z-i; Roskomnadzor registry dump (public under Decree 1101). Extract only; do not redistribute. |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | https://github.com/zapret-info/z-i/tree/b6429c7268a249f0cad7663b3ac6b2bd91b67e09 (splits) | 2026-10-03T22:18:05Z | 572054 | `9f0104169f7620f6550e303c6a9e6bd9135ac4daf485c3d5f2cf4cd62cc8f23f` | No license file in zapret-info/z-i; Roskomnadzor registry dump (public under Decree 1101). Extract only; do not redistribute. |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | https://github.com/zapret-info/z-i/tree/1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b (splits) | 2026-10-03T22:19:05Z | 791552 | `9886bb2983ddbe2c556e08ce6df448cca3d59e4cf1d2ea197f803958cb89dd9f` | No license file in zapret-info/z-i; Roskomnadzor registry dump (public under Decree 1101). Extract only; do not redistribute. |

Upstream files behind the extracts (streamed to scratch, hashed, filtered, deleted):

| extract in raw/ | upstream URL | retrieved (UTC) | size (bytes) | sha256 |
|---|---|---|---:|---|
| `antifilter/domains_platform_extract.lst` | https://antifilter.download/list/domains.lst | 2026-10-03T21:57:21Z | 32420045 | `8baa7d2601264b076e89d1e5ffb267b9129775ad0f7ff3741d04eade678bb9a6` |
| `zi/extract_2025-10-01_9133e4327b.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9133e4327bbcf9adc1cba24360f50e50a6b4d11c/dump-00.csv | 2026-10-03T22:12:49Z | 12033030 | `c16659dfdf017a0e900ce99c595f8c54134b26180e107b5f5c691c85cce53dc4` |
| `zi/extract_2025-10-01_9133e4327b.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9133e4327bbcf9adc1cba24360f50e50a6b4d11c/dump-01.csv | 2026-10-03T22:12:51Z | 12033023 | `4e5d7ff353f3fcd86ef83e0faca1389c70046aba1d49cfd36f65b65b6b72b978` |
| `zi/extract_2025-10-01_9133e4327b.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9133e4327bbcf9adc1cba24360f50e50a6b4d11c/dump-02.csv | 2026-10-03T22:12:53Z | 12033027 | `8e92236e7c6b3a81fcf01e1855140520751cb7411724112112485abc200952e3` |
| `zi/extract_2025-10-01_9133e4327b.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9133e4327bbcf9adc1cba24360f50e50a6b4d11c/dump-03.csv | 2026-10-03T22:12:55Z | 12032968 | `df560733b701ac645d962c44f1c0853e3219a9faaaf4b4cf281af80298eb66da` |
| `zi/extract_2025-10-01_9133e4327b.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9133e4327bbcf9adc1cba24360f50e50a6b4d11c/dump-04.csv | 2026-10-03T22:12:57Z | 12033039 | `1e906cd80048b5daca82455415efc7ac90b907fdf5e6486db8392b8f92a4c754` |
| `zi/extract_2025-10-01_9133e4327b.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9133e4327bbcf9adc1cba24360f50e50a6b4d11c/dump-05.csv | 2026-10-03T22:12:59Z | 12033005 | `e24213173b98f8bc69bbfbc4ddfc93a4af43b69908c19ae8561c1a76539eade8` |
| `zi/extract_2025-10-01_9133e4327b.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9133e4327bbcf9adc1cba24360f50e50a6b4d11c/dump-06.csv | 2026-10-03T22:13:01Z | 12033003 | `81b4c511cb98e9182c176d0d232bfe7a7699705667d514018b498cb29a8b55e6` |
| `zi/extract_2025-10-01_9133e4327b.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9133e4327bbcf9adc1cba24360f50e50a6b4d11c/dump-07.csv | 2026-10-03T22:13:03Z | 12032989 | `ae6573c29eeff89f352064fbfee7e59a1b8214bfcab64000bfc11462aac59113` |
| `zi/extract_2025-10-01_9133e4327b.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9133e4327bbcf9adc1cba24360f50e50a6b4d11c/dump-08.csv | 2026-10-03T22:13:05Z | 12033036 | `8ebd3c19c5ff18f408d07448883f36a68f731ede81b258bd8423a9b078cb296c` |
| `zi/extract_2025-10-01_9133e4327b.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9133e4327bbcf9adc1cba24360f50e50a6b4d11c/dump-09.csv | 2026-10-03T22:13:07Z | 12032835 | `623fc435672ce62312ac0e983a499746b444160d538a06b4a2f26ccdfefd49f3` |
| `zi/extract_2025-10-01_9133e4327b.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9133e4327bbcf9adc1cba24360f50e50a6b4d11c/dump-10.csv | 2026-10-03T22:13:09Z | 12033037 | `bacfd3ac7fef927520daf12e23e561fd4174c13e9a81b260ebdb50eace324cbc` |
| `zi/extract_2025-10-01_9133e4327b.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9133e4327bbcf9adc1cba24360f50e50a6b4d11c/dump-11.csv | 2026-10-03T22:13:11Z | 12033076 | `3eaaa746e6046ed8f1758feb36a9e92c34bc92674f40e317232d8c7fe8d657d1` |
| `zi/extract_2025-10-01_9133e4327b.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9133e4327bbcf9adc1cba24360f50e50a6b4d11c/dump-12.csv | 2026-10-03T22:13:13Z | 12032757 | `8b65baa9069ab134b6638ee589392c1659e18104621a23bcd9f5146edbe2a0e0` |
| `zi/extract_2025-10-01_9133e4327b.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9133e4327bbcf9adc1cba24360f50e50a6b4d11c/dump-13.csv | 2026-10-03T22:13:15Z | 12033038 | `19eeda4dbda3440b47451ee69bf1b36340fd7bac21b2e909d0948fdf6e35650e` |
| `zi/extract_2025-10-01_9133e4327b.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9133e4327bbcf9adc1cba24360f50e50a6b4d11c/dump-14.csv | 2026-10-03T22:13:17Z | 12032676 | `57a9c1f8726b99ccb52d84eb0eb156ca5f2737b9ef7fbbd52a580059cea0c29b` |
| `zi/extract_2025-10-01_9133e4327b.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9133e4327bbcf9adc1cba24360f50e50a6b4d11c/dump-15.csv | 2026-10-03T22:13:19Z | 12032918 | `a6feb8a38272242e8245b0037cfb951511901295efa3cb4d4399867da105b065` |
| `zi/extract_2025-10-01_9133e4327b.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9133e4327bbcf9adc1cba24360f50e50a6b4d11c/dump-16.csv | 2026-10-03T22:13:21Z | 12020704 | `ddea9f8a5b6797fe3d9aa7aca077e509847faa8c1203cc1cf8184fb0a2f96aa2` |
| `zi/extract_2025-10-01_9133e4327b.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9133e4327bbcf9adc1cba24360f50e50a6b4d11c/dump-17.csv | 2026-10-03T22:13:23Z | 12025129 | `9b5ef89b44744f400bb6e546d7716a9ff4fbff6712721e7b6105e89048237ce7` |
| `zi/extract_2025-10-01_9133e4327b.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9133e4327bbcf9adc1cba24360f50e50a6b4d11c/dump-18.csv | 2026-10-03T22:13:25Z | 11871909 | `ebdd787e514876b51e2ad7260e0bd353b94124d87a16e8226fa62f7d377fb65b` |
| `zi/extract_2025-10-01_9133e4327b.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9133e4327bbcf9adc1cba24360f50e50a6b4d11c/dump-19.csv | 2026-10-03T22:13:27Z | 10826218 | `9bb8ec8ca4a029b9625a637907f0c7430f05cb5f3f7a3a37c857f35f856b6937` |
| `zi_history/extract_2022-01-01_d291c7d7d7.csv` | https://raw.githubusercontent.com/zapret-info/z-i/d291c7d7d7e406fbd8d08b1c9413a4ebb51fc42a/dump.csv | 2026-10-03T22:15:26Z | 92609391 | `c1b78e698793fa27a07ae623e675cd4cff44e1cf64cfdb6deebc6b697bca131a` |
| `zi_history/extract_2023-01-01_9e1f59db33.csv` | https://raw.githubusercontent.com/zapret-info/z-i/9e1f59db3360f5caaaf8ebde0581e867b7fff4c8/dump.csv | 2026-10-03T22:15:42Z | 96085709 | `07cc68047f34fb7de96eb40c5253ca3c3d8499f8d29b54c1f21895a3b22cb8ae` |
| `zi_history/extract_2024-01-01_99aec91c81.csv` | https://raw.githubusercontent.com/zapret-info/z-i/99aec91c810505e9b60129cc70c0f8c58411a11c/dump.csv | 2026-10-03T22:15:58Z | 96734011 | `d162e790f17bd40385b40eb4f6e25c9eab3afe77f17e8c4a6dc23f26cbc8059c` |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | https://raw.githubusercontent.com/zapret-info/z-i/94b080bebc7338dcbb6045ad6147656a1db974e3/dump-00.csv | 2026-10-03T22:17:13Z | 5788084 | `637a432484c8f26b71adb8a00924288d3973e2d80bb85a9da1d90d7dee41cdce` |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | https://raw.githubusercontent.com/zapret-info/z-i/94b080bebc7338dcbb6045ad6147656a1db974e3/dump-01.csv | 2026-10-03T22:17:15Z | 5788050 | `f352ae5d3667d9a04ef7b795239cc924ef9ff882e6716596c47fcde57086c3d4` |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | https://raw.githubusercontent.com/zapret-info/z-i/94b080bebc7338dcbb6045ad6147656a1db974e3/dump-02.csv | 2026-10-03T22:17:17Z | 5788113 | `806bcf485729242cbdb071b5e31a3de6a7192865b1d79206a0f8d3a344fefa7a` |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | https://raw.githubusercontent.com/zapret-info/z-i/94b080bebc7338dcbb6045ad6147656a1db974e3/dump-03.csv | 2026-10-03T22:17:19Z | 5788120 | `ff917f21c4fa68121f4746ed71381c4afd37ea35ff7bc6218c81c20020210e4a` |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | https://raw.githubusercontent.com/zapret-info/z-i/94b080bebc7338dcbb6045ad6147656a1db974e3/dump-04.csv | 2026-10-03T22:17:21Z | 5788029 | `ea4603fe7b25bb34b088c1e28a1abe1b8888100c00da2c73117d67d1e92e235b` |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | https://raw.githubusercontent.com/zapret-info/z-i/94b080bebc7338dcbb6045ad6147656a1db974e3/dump-05.csv | 2026-10-03T22:17:23Z | 5788065 | `f6cf752cf776e7c2fc3097a65aed8b178d2547ca52d8cc6412bc49695989aff4` |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | https://raw.githubusercontent.com/zapret-info/z-i/94b080bebc7338dcbb6045ad6147656a1db974e3/dump-06.csv | 2026-10-03T22:17:25Z | 5788071 | `376d9b7cc114ea0bd476b8cd584b608e13397eee464a2dd43ac9a6c744039cce` |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | https://raw.githubusercontent.com/zapret-info/z-i/94b080bebc7338dcbb6045ad6147656a1db974e3/dump-07.csv | 2026-10-03T22:17:27Z | 5787983 | `56d269dbd1506e2f21ef508a9a2d572c7e6c10ac4122bc72877984b18f982429` |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | https://raw.githubusercontent.com/zapret-info/z-i/94b080bebc7338dcbb6045ad6147656a1db974e3/dump-08.csv | 2026-10-03T22:17:29Z | 5788094 | `44490002b71a4730de315e67f31946ab8417eae977b59ac1a864737f2aef694a` |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | https://raw.githubusercontent.com/zapret-info/z-i/94b080bebc7338dcbb6045ad6147656a1db974e3/dump-09.csv | 2026-10-03T22:17:31Z | 5787879 | `911aba40d58d201f4d889d16ad76abb6c40385428814fe785721f2afcd88259a` |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | https://raw.githubusercontent.com/zapret-info/z-i/94b080bebc7338dcbb6045ad6147656a1db974e3/dump-10.csv | 2026-10-03T22:17:33Z | 5788090 | `349b03dc59a0ecbe722ea9cd135e84ba6e33856c68b4fce940941bf389c19567` |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | https://raw.githubusercontent.com/zapret-info/z-i/94b080bebc7338dcbb6045ad6147656a1db974e3/dump-11.csv | 2026-10-03T22:17:35Z | 5787857 | `610df007770884665c1e7fab10ea94d7bbcec7896dfd773332b3837658d3c736` |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | https://raw.githubusercontent.com/zapret-info/z-i/94b080bebc7338dcbb6045ad6147656a1db974e3/dump-12.csv | 2026-10-03T22:17:37Z | 5787934 | `f43279c21bf96bfa0e37bbc2ba1283c17b8f6f898837f989d4b0c36b38c01b7a` |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | https://raw.githubusercontent.com/zapret-info/z-i/94b080bebc7338dcbb6045ad6147656a1db974e3/dump-13.csv | 2026-10-03T22:17:39Z | 5788028 | `3af8962bd6ac9f8a2b924831ccdd84f40ae9bd71d8b1d4547a618d6f9660451f` |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | https://raw.githubusercontent.com/zapret-info/z-i/94b080bebc7338dcbb6045ad6147656a1db974e3/dump-14.csv | 2026-10-03T22:17:41Z | 5787916 | `83d97cee0591410f99da84c3fa3b7ca9543b914757117aad9ef4bfd9180c9252` |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | https://raw.githubusercontent.com/zapret-info/z-i/94b080bebc7338dcbb6045ad6147656a1db974e3/dump-15.csv | 2026-10-03T22:17:43Z | 5788001 | `30c0193108fac8ac9fa22801ae545a3723e8f2a3df9b5152df38b8e2a965d2e0` |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | https://raw.githubusercontent.com/zapret-info/z-i/94b080bebc7338dcbb6045ad6147656a1db974e3/dump-16.csv | 2026-10-03T22:17:45Z | 5787935 | `825e5c2ada5f915dc20488418893fc0b0241ab6be6553bed5f5e94ec9ef537e3` |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | https://raw.githubusercontent.com/zapret-info/z-i/94b080bebc7338dcbb6045ad6147656a1db974e3/dump-17.csv | 2026-10-03T22:17:47Z | 5788082 | `b5cf9dc53e0992006b4aaabcd8f397c173d426d4bc90fbca80c14f783250964c` |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | https://raw.githubusercontent.com/zapret-info/z-i/94b080bebc7338dcbb6045ad6147656a1db974e3/dump-18.csv | 2026-10-03T22:17:49Z | 5788059 | `7b4904b0e9c1b1d382551298654aea744041c269ddda6f5c4fa39070b3406ca1` |
| `zi_history/extract_2024-05-07_94b080bebc.csv` | https://raw.githubusercontent.com/zapret-info/z-i/94b080bebc7338dcbb6045ad6147656a1db974e3/dump-19.csv | 2026-10-03T22:17:51Z | 1365490 | `baca07445dec5253007c542739e4d7cb49b73a1e5ecc52e6a829ca7c3724b118` |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | https://raw.githubusercontent.com/zapret-info/z-i/b6429c7268a249f0cad7663b3ac6b2bd91b67e09/dump-00.csv | 2026-10-03T22:18:05Z | 5788066 | `839689e1c83ba6af77aeb7f77b4014883e383550d81ae04b930ee2d7ac78f308` |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | https://raw.githubusercontent.com/zapret-info/z-i/b6429c7268a249f0cad7663b3ac6b2bd91b67e09/dump-01.csv | 2026-10-03T22:18:07Z | 5788109 | `f3060b3cacba719c7a9a6bcf867e87eed77ecdc560786782a7493b9b529f7b8e` |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | https://raw.githubusercontent.com/zapret-info/z-i/b6429c7268a249f0cad7663b3ac6b2bd91b67e09/dump-02.csv | 2026-10-03T22:18:09Z | 5788067 | `4a0cfb26035fb7e0b5e6638b9a210a9e5b2a106500ecca54126f02bb0f72ef02` |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | https://raw.githubusercontent.com/zapret-info/z-i/b6429c7268a249f0cad7663b3ac6b2bd91b67e09/dump-03.csv | 2026-10-03T22:18:11Z | 5787878 | `854d28c7abcac15b50ff4ce0983e1e4163d29d267af20308a69ff36e8c7359ca` |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | https://raw.githubusercontent.com/zapret-info/z-i/b6429c7268a249f0cad7663b3ac6b2bd91b67e09/dump-04.csv | 2026-10-03T22:18:13Z | 5788032 | `7784cf6df770c05f573d788f60e873f1c54bea2fc99e64009afd051028deb43f` |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | https://raw.githubusercontent.com/zapret-info/z-i/b6429c7268a249f0cad7663b3ac6b2bd91b67e09/dump-05.csv | 2026-10-03T22:18:15Z | 5788054 | `d027acaf204341406727d3368ffd2637966d0dc850e58038190d0ebf4b5b462f` |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | https://raw.githubusercontent.com/zapret-info/z-i/b6429c7268a249f0cad7663b3ac6b2bd91b67e09/dump-06.csv | 2026-10-03T22:18:17Z | 5788076 | `e20b8af4bf691744811b87b993308b6c874a454cd3d08d3ce8b8c7a2a2a47a57` |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | https://raw.githubusercontent.com/zapret-info/z-i/b6429c7268a249f0cad7663b3ac6b2bd91b67e09/dump-07.csv | 2026-10-03T22:18:19Z | 5788009 | `c30693d5aecf32e3036265749a0dcc99ffcba87c5412727504c2bbd4d528817b` |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | https://raw.githubusercontent.com/zapret-info/z-i/b6429c7268a249f0cad7663b3ac6b2bd91b67e09/dump-08.csv | 2026-10-03T22:18:21Z | 5788119 | `3e8e357a2dd7d8e08c8d5579c8f21b08a2306c1a7d4b53acc44c1dafbaac0b5d` |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | https://raw.githubusercontent.com/zapret-info/z-i/b6429c7268a249f0cad7663b3ac6b2bd91b67e09/dump-09.csv | 2026-10-03T22:18:23Z | 5788063 | `76dccdc02e124a3148c206ed28371ae2f2e8c48723cb213e1a1d6810c6409764` |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | https://raw.githubusercontent.com/zapret-info/z-i/b6429c7268a249f0cad7663b3ac6b2bd91b67e09/dump-10.csv | 2026-10-03T22:18:25Z | 5787012 | `d20dc0aa9d4761da6962df21809ab25b20352cdafe4a3e3f8281e21272013ac8` |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | https://raw.githubusercontent.com/zapret-info/z-i/b6429c7268a249f0cad7663b3ac6b2bd91b67e09/dump-11.csv | 2026-10-03T22:18:27Z | 5788054 | `f8f6e6c1ee5c38b25c149b2a51f4bf882ce93c8a209db15510ff541216e0b1ff` |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | https://raw.githubusercontent.com/zapret-info/z-i/b6429c7268a249f0cad7663b3ac6b2bd91b67e09/dump-12.csv | 2026-10-03T22:18:29Z | 5788006 | `e07c7bdaf12303f7e2cb74d0cc55e6a539481428112cb8a200aa95450aa11e35` |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | https://raw.githubusercontent.com/zapret-info/z-i/b6429c7268a249f0cad7663b3ac6b2bd91b67e09/dump-13.csv | 2026-10-03T22:18:31Z | 5788010 | `1ace3d212808bbf82ad94bebb394ecf6d29bd4ca564a63005af9770f061ce0d9` |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | https://raw.githubusercontent.com/zapret-info/z-i/b6429c7268a249f0cad7663b3ac6b2bd91b67e09/dump-14.csv | 2026-10-03T22:18:33Z | 5787838 | `4ed5bef725ec55cf39e105c50286a40c64c897540d5c9b07b2d18220f85967d7` |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | https://raw.githubusercontent.com/zapret-info/z-i/b6429c7268a249f0cad7663b3ac6b2bd91b67e09/dump-15.csv | 2026-10-03T22:18:35Z | 5787926 | `2aab767f0e1166f39616905bcfe462d7533248bace3aa342d92a960e6d4757b7` |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | https://raw.githubusercontent.com/zapret-info/z-i/b6429c7268a249f0cad7663b3ac6b2bd91b67e09/dump-16.csv | 2026-10-03T22:18:37Z | 5748730 | `0c4a9d2c6eeef004911a91bd1301d04e6a57da4a4e5dc4af07e4fd04f19d6649` |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | https://raw.githubusercontent.com/zapret-info/z-i/b6429c7268a249f0cad7663b3ac6b2bd91b67e09/dump-17.csv | 2026-10-03T22:18:39Z | 5787929 | `41922fd8177e22697e79e6a205416fa87ff8dea62fed1d7173840ca836204537` |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | https://raw.githubusercontent.com/zapret-info/z-i/b6429c7268a249f0cad7663b3ac6b2bd91b67e09/dump-18.csv | 2026-10-03T22:18:41Z | 5788110 | `bb6ff8fde3d62a0636be02fc4b4db312d37f78089d3502417e384101aed422a5` |
| `zi_history/extract_2024-05-10_b6429c7268.csv` | https://raw.githubusercontent.com/zapret-info/z-i/b6429c7268a249f0cad7663b3ac6b2bd91b67e09/dump-19.csv | 2026-10-03T22:18:43Z | 2012230 | `489d9c96e053dc934a9717cea168a2f963fd70b736030cf24555edde61b0aa02` |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | https://raw.githubusercontent.com/zapret-info/z-i/1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b/dump-00.csv | 2026-10-03T22:19:05Z | 8144410 | `f78b0dbb61f5548e2abefca5fb6f22fe340950934a3ddb759efc1e439b1f5ba9` |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | https://raw.githubusercontent.com/zapret-info/z-i/1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b/dump-01.csv | 2026-10-03T22:19:07Z | 8144280 | `ff49827c5cf7772bee54f9c295dfd3539025b4cf3deb5b7b4a89501179a678b5` |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | https://raw.githubusercontent.com/zapret-info/z-i/1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b/dump-02.csv | 2026-10-03T22:19:09Z | 8144348 | `66f0b05b35447be5f057c881b188f3d4fc52f372e2053a1508dc74598233fdc9` |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | https://raw.githubusercontent.com/zapret-info/z-i/1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b/dump-03.csv | 2026-10-03T22:19:11Z | 8144351 | `0ad883f4d1e07deb137d85859062432e01349e7f1d117ab18822d50be19c57aa` |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | https://raw.githubusercontent.com/zapret-info/z-i/1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b/dump-04.csv | 2026-10-03T22:19:13Z | 8144430 | `cafc0b39c342290e990e324e5b726487a1fd612d1c92d4e80dd99153ab57b47a` |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | https://raw.githubusercontent.com/zapret-info/z-i/1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b/dump-05.csv | 2026-10-03T22:19:15Z | 8144390 | `91343c7d215df037647af2c6277a2439be761391729a35c90a3ae3983be00e32` |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | https://raw.githubusercontent.com/zapret-info/z-i/1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b/dump-06.csv | 2026-10-03T22:19:17Z | 8144464 | `1e3ddf10913d3e6c1b9f01a7cce3f285d1f74a7147f35de746117bf51bcd09fa` |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | https://raw.githubusercontent.com/zapret-info/z-i/1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b/dump-07.csv | 2026-10-03T22:19:19Z | 8144418 | `6c70d8af9be25f58192f12077375d20d4fab351450535218bacf25ff02989829` |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | https://raw.githubusercontent.com/zapret-info/z-i/1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b/dump-08.csv | 2026-10-03T22:19:21Z | 8144432 | `024abd24b9dc84599d18afe60e9df303c98b4857bfe00150a5004dc086ae53ba` |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | https://raw.githubusercontent.com/zapret-info/z-i/1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b/dump-09.csv | 2026-10-03T22:19:23Z | 8144418 | `8a50080eff43ba57c415237d378c468a0815627af461af0b6281904a220d95c5` |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | https://raw.githubusercontent.com/zapret-info/z-i/1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b/dump-10.csv | 2026-10-03T22:19:25Z | 8144440 | `7f1374c594f595a767664dd63e614cb2671157459707e6b9cfe90587a402e851` |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | https://raw.githubusercontent.com/zapret-info/z-i/1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b/dump-11.csv | 2026-10-03T22:19:27Z | 8144340 | `dc955ddb93a51c0741503275ad112e9fd2274d26655fa9867e4c512f526abe04` |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | https://raw.githubusercontent.com/zapret-info/z-i/1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b/dump-12.csv | 2026-10-03T22:19:29Z | 8144361 | `9052312f47577faaa7b8137e3d1419b337509c0abb850a8eab2b6cf48aec5ae9` |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | https://raw.githubusercontent.com/zapret-info/z-i/1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b/dump-13.csv | 2026-10-03T22:19:31Z | 8144441 | `b22a66b5b098d6f2f54957dd53a3d6c2ee48e33d591f7d7e19beaa4431e1f00d` |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | https://raw.githubusercontent.com/zapret-info/z-i/1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b/dump-14.csv | 2026-10-03T22:19:33Z | 8026951 | `6cba3acb6272514ff08e8db44ca5992bf0b8521b361185fc47adc01d055403dc` |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | https://raw.githubusercontent.com/zapret-info/z-i/1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b/dump-15.csv | 2026-10-03T22:19:35Z | 8143741 | `e8773beb552be4f10ade93beccbdf5b70677c07a411f4d4fe341f896974c37bb` |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | https://raw.githubusercontent.com/zapret-info/z-i/1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b/dump-16.csv | 2026-10-03T22:19:37Z | 8144253 | `d3ac02b31ef604c96554ccdf1cb43bee6b37d8a8babb03344147c28e029be3d1` |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | https://raw.githubusercontent.com/zapret-info/z-i/1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b/dump-17.csv | 2026-10-03T22:19:39Z | 8140863 | `e434f012dab7db04b7b7a3a786393cce1a7e096d8e3f2bbd482ad02f18a45304` |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | https://raw.githubusercontent.com/zapret-info/z-i/1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b/dump-18.csv | 2026-10-03T22:19:41Z | 8144347 | `ea733ed2e66cefaa57ef34e1c3247e86e361936a258ac859a8830af9ae59e3db` |
| `zi_history/extract_2025-01-01_1553f20a86.csv` | https://raw.githubusercontent.com/zapret-info/z-i/1553f20a86dc909d460ce2ec9041e4fe8e5e4a0b/dump-19.csv | 2026-10-03T22:19:43Z | 4976234 | `b72c680e5e11e3d7087cef256e3290214d1921cba7bb0d61d32812ba0636e613` |
