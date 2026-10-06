# Sources: minting (cost, speed and exposure of new blockable names)

Every input is an existing public document or dataset, fetched by
`fetch.py` on 2026-10-03 (UTC) without accounts, API keys or approvals.
Nothing was measured: no endpoint, tenant name or blocked name was resolved,
probed or connected to. API calls were spaced at least 2 s apart (crt.sh:
20 s, at most two attempts per lookup).

Reproduce, in `data/minting/` (`raw/README.md` gives the details):

    cp raw/manifest.json manifest.paper.json   # keep the paper's manifest first
    python3 fetch.py      # downloads into raw/ and rewrites raw/manifest.json
    python3 analysis.py   # rebuilds derived/ from raw/ only (no network)

`fetch.py` needs the Python package `requests`. `analysis.py` needs
`pandas`, `matplotlib` and `pdftotext` from poppler-utils, and takes the
figure style from `../../simulations/code/figstyle.py`.

## What was fetched and why

- **Certificate authorities.** Let's Encrypt rate limits (page stamped
  "Last updated: August 5, 2026"), certificate profiles ("Last updated:
  September 8, 2026"; classic 90 days, tlsserver 45 days, shortlived 160
  hours), CT logs, challenge types, and blog posts on 6-day and IP
  certificates (GA 2026-01-15), rate limits under 45-day lifetimes
  (2026-02-24), the 90-to-45-day timeline (2025-12-02), Sunlight logs
  (2025-06-11) and DNS-PERSIST-01 (2026-02-18). Google Trust Services:
  Certificate Manager quotas (stamped "Last updated 2026-10-01 UTC"),
  Public CA overview and pricing. ZeroSSL ACME documentation.
- **How Let's Encrypt computes a registered domain.** Boulder
  `ratelimits/utilities.go` and publicsuffix-go `publicsuffix.go`, both at
  commits pinned with `git ls-remote` (Boulder 1578a1d0..., publicsuffix-go
  32ef0a9d...).
- **Domain prices.** Porkbun's keyless pricing endpoint (POST, 911 entries
  including 273 Handshake names), Porkbun API documentation (registration
  limits, spend cap), and the IANA root-zone TLD list (version 2026100300),
  used to keep only ICANN TLDs.
- **Registry activity.** ICANN per-registrar monthly transaction reports for
  .xyz, .top, .shop, .online and .cfd, July 2024 to June 2026 (120 files;
  June 2026 is the latest month published on 2026-10-03). Field definitions
  come from the base gTLD Registry Agreement (Specification 3) and zone-file
  terms from its Specification 4 and ICANN's "About Zone File Access" page.
- **Public Suffix List.** Canonical file, VERSION 2026-10-01_23-02-52_UTC,
  COMMIT 6cd82aff889e3d64e5e03bc5c1f43da1934a960a.
- **Certificate Transparency.** RFC 6962, RFC 9162, RFC 9525 (wildcards
  match one label), Chrome's CT policy and log policy, Chrome's log list v3
  (version 93.3, 2026-10-03T13:35:24Z), Apple's CT policy, the C2SP
  static-ct-api specification and the Sunlight README.
- **Literature.** Scheitle et al., IMC 2018 (arXiv:1809.08325; CT honeypot
  timing) and Hoang et al., USENIX Security 2021 (arXiv:2106.02167; daily
  zone-file-driven testing).
- **Feeds that turn registrations or CT into name lists** (documentation
  pages only; no list was downloaded): WhoisDS newly registered domains,
  OpenINTEL Zonestream, GH Archive, GitHub event types and events API.
- **Platforms** (documentation pages): GitHub Pages and Terms of Service,
  Cloudflare Workers and Pages, Vercel, Netlify, Firebase Hosting, Deno
  Deploy, Fly.io, Render, AWS Lambda function URLs, Azure App Service,
  Google Cloud Run.
- **crt.sh.** Five exact-identity lookups of platform apex wildcards,
  unexpired certificates only: `*.github.io`, `*.netlify.app` and
  `*.web.app` returned results; `*.vercel.app` and `*.pages.dev` failed
  (see below). No suffix-wide (`%`) query was made.
- **Tor Project.** Blog post of 2025-12-03 (WebTunnel non-WebPKI
  certificates with chain pinning) and the WebTunnel bridge setup guide.

## Licenses and redistribution

- Open licenses: PSL (MPL-2.0), letsencrypt.org pages (MPL-2.0 per the
  letsencrypt/website repository), Boulder (MPL-2.0), publicsuffix-go
  (MIT), Chrome CT policy repository (Apache-2.0), Google developer pages
  that state CC BY 4.0 in their footer, RFCs (IETF Trust), Hoang et al.
  (CC BY-NC-ND 4.0).
- Cite only, do not redistribute the saved file: pages marked
  "(c) publisher; cite" or "not stated; cite" (platform, ZeroSSL, Porkbun,
  Apple, Tor, WhoisDS, GH Archive and similar pages), the Scheitle et al.
  PDF (arXiv non-exclusive license), and Chrome's log list.
- ICANN reports: cite ICANN and the registry; only aggregate (Totals-row)
  figures are used. Porkbun prices: factual list prices; cite with the
  retrieval date.
- No OONI, OpenINTEL, IODA, GFW Report or Russian registry data are used in
  this directory, so no share-alike or redistribution constraint from those
  sources applies to `derived/`.

The artifact ships the scripts, this file, `raw/manifest.json` and the
derived files that `derived/README.md` lists. It omits the downloaded files
under `raw/` and `derived/doc_text/` (full-text copies of the saved pages),
and `derived/README.md` names the other derived files it omits and why.
`fetch.py` downloads the inputs again and `analysis.py` rebuilds every
derived file. `derived/doc_facts.csv` keeps only short quotes.

## Requests that returned no file

| URL | attempts | result | when (UTC) |
|---|---|---|---|
| https://crt.sh/?q=%2A.vercel.app&output=json&exclude=expired | 2 | HTTP 504 both times | 2026-10-03T22:05:27Z..22:08:54Z |
| https://crt.sh/?q=%2A.pages.dev&output=json&exclude=expired | 2 | HTTP 502 both times | 2026-10-03T22:08:54Z..22:12:05Z |
| https://raw.githubusercontent.com/letsencrypt/website/main/LICENSE.md | 1 | HTTP 404 (file is LICENSE.txt) | 2026-10-03 |
| https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202607-en.csv | 1 | HTTP 404 (July 2026 not yet published; June 2026 is the latest month) | 2026-10-03 |

## File inventory (from raw/manifest.json)

Every raw file with its URL, retrieval time (UTC), sha256, size and license (short label; the full license text of each entry is in raw/manifest.json).

| id | file (under raw/) | URL | retrieved (UTC) | sha256 | bytes | license |
|---|---|---|---|---|---|---|
| boulder_ratelimits_utilities | code/boulder_1578a1d051b8_ratelimits_utilities.go | https://raw.githubusercontent.com/letsencrypt/boulder/1578a1d051b87ded8f60f3af7f6e79f0da0a8d81/ratelimits/utilities.go | 2026-10-03T22:15:55Z | `51c3a2bf989c08ee0eeb0dfec83700c43438eb21682afadc774e274c9614e338` | 4051 | MPL-2.0 |
| boulder_license | code/boulder_LICENSE.txt | https://raw.githubusercontent.com/letsencrypt/boulder/1578a1d051b87ded8f60f3af7f6e79f0da0a8d81/LICENSE.txt | 2026-10-03T22:15:57Z | `0dd1ee4d74b797c1b8dfa0fd52ac4a2fe9e26e3e852e333a85dcb315569afbb5` | 16770 | license text |
| pslgo_publicsuffix | code/publicsuffix-go_32ef0a9d3d18_publicsuffix.go | https://raw.githubusercontent.com/weppos/publicsuffix-go/32ef0a9d3d18fb4d7e7af481a56f36263a4b2c43/publicsuffix/publicsuffix.go | 2026-10-03T22:15:59Z | `5ac6a1692b27e90cfb3ea2537ecdfbe5ef74427379a1d93bcd8682af0f667cc5` | 14371 | MIT |
| pslgo_license | code/publicsuffix-go_LICENSE.txt | https://raw.githubusercontent.com/weppos/publicsuffix-go/32ef0a9d3d18fb4d7e7af481a56f36263a4b2c43/LICENSE.txt | 2026-10-03T22:16:01Z | `a96cc75b417b7fedb0a92984a92df6e1ad894855f2ba2923376963b198ba3d4e` | 1086 | license text |
| crtsh_wild_github_io | crtsh/crtsh_wild_github_io.json | https://crt.sh/?q=%2A.github.io&output=json&exclude=expired | 2026-10-03T22:05:27Z | `2efb4306322bcbbe1920c4f92ee637748553801cb8f66afde2a87bc1f97c23d0` | 567 | CT data via crt.sh; cite |
| crtsh_wild_netlify_app | crtsh/crtsh_wild_netlify_app.json | https://crt.sh/?q=%2A.netlify.app&output=json&exclude=expired | 2026-10-03T22:08:54Z | `0f5b0385053369055474794b586be3a65486159354b8d34224a86314a57e477b` | 643 | CT data via crt.sh; cite |
| crtsh_wild_web_app | crtsh/crtsh_wild_web_app.json | https://crt.sh/?q=%2A.web.app&output=json&exclude=expired | 2026-10-03T22:12:05Z | `bfbe808f9ae86eac1072924fbd469255abeda439bd84bf9715864caf8bfed5ed` | 284 | CT data via crt.sh; cite |
| apple_ct_policy | ct/apple_ct_policy.html | https://support.apple.com/en-us/103214 | 2026-10-03T21:46:41Z | `d7ab0cee4238e8b0b0524f929b04edafa4fcc4928570c74b78dbc93daf1dc332` | 159623 | (c) publisher; cite |
| static_ct_api | ct/c2sp_static_ct_api.md | https://raw.githubusercontent.com/C2SP/C2SP/main/static-ct-api.md | 2026-10-03T21:46:45Z | `e7173ca6fc226ada35d4bffb2cb8bf5a68f6ba7f12a3057fbb696fc6d32b6b5a` | 14179 | not stated; cite |
| chrome_ct_license | ct/chrome_ct_LICENSE.txt | https://raw.githubusercontent.com/GoogleChrome/CertificateTransparency/master/LICENSE | 2026-10-03T21:46:39Z | `58d1e17ffe5109a7ae296caafcadfdbe6a7d176f0bc4ab01e12a689b0499d8bd` | 11357 | license text |
| chrome_ct_policy | ct/chrome_ct_policy.md | https://raw.githubusercontent.com/GoogleChrome/CertificateTransparency/master/ct_policy.md | 2026-10-03T21:46:35Z | `b27b1cbdc554ec3de19b6f2617bb38f4fbd75a23eecf4bed4e689edd83ffe50b` | 6657 | Apache-2.0 |
| chrome_log_list | ct/chrome_log_list_v3.json | https://www.gstatic.com/ct/log_list/v3/log_list.json | 2026-10-03T21:46:43Z | `d23ab4cd867239b3ff227d52eb9d60210fbd5eb0c66ab2b6d2bded8e6852d406` | 50629 | no license; cite |
| chrome_log_policy | ct/chrome_log_policy.md | https://raw.githubusercontent.com/GoogleChrome/CertificateTransparency/master/log_policy.md | 2026-10-03T21:46:37Z | `b3884c2191e5a33be5c196f3d12fb963df834c1872aac3147bb61773d7b73feb` | 19492 | Apache-2.0 |
| rfc6962 | ct/rfc6962.txt | https://www.rfc-editor.org/rfc/rfc6962.txt | 2026-10-03T21:46:31Z | `08fdf31c10b9f20872a65c027a9fe8cee27280f930120784241a57de744752af` | 55048 | IETF Trust (RFC) |
| rfc9162 | ct/rfc9162.txt | https://www.rfc-editor.org/rfc/rfc9162.txt | 2026-10-03T21:46:33Z | `a0e432ce7580c99fcc8faf0cf3f6191f9ce6b4864f949158e020d4ecb295081f` | 128266 | IETF Trust (RFC) |
| rfc9525 | ct/rfc9525.txt | https://www.rfc-editor.org/rfc/rfc9525.txt | 2026-10-03T22:00:15Z | `ed8116c2435376dffe37ec2ca688c3a8515e36820852b29e0b6cdfbe92abd2c5` | 69260 | IETF Trust (RFC) |
| sunlight_readme | ct/sunlight_README.md | https://raw.githubusercontent.com/FiloSottile/sunlight/main/README.md | 2026-10-03T21:46:47Z | `ae58bdd2a52e7a5191d0915575949886f80d3640d3a9eb7e6505ec1ad28066b0` | 13762 | not stated; cite |
| gharchive | docs/gharchive_home.html | https://www.gharchive.org/ | 2026-10-03T21:54:00Z | `566652fbedd9b3bb651be34291f37d7543c41694d65a405921ece5e43170bc06` | 19366 | (c) publisher; cite |
| gts_pricing | docs/gts_certmanager_pricing.html | https://cloud.google.com/certificate-manager/pricing | 2026-10-03T21:46:15Z | `a67707288fcd850012f010c14e2c5ac9a2def0357dd2110bef38322805d544c5` | 2221651 | (c) publisher; cite |
| gts_quotas | docs/gts_certmanager_quotas.html | https://cloud.google.com/certificate-manager/docs/quotas | 2026-10-03T21:46:11Z | `1d2fdcaa7367930a1a800159a79602507f96187b103a200d1e88bda35ced187c` | 137714 | CC BY 4.0 |
| gts_public_ca | docs/gts_public_ca.html | https://cloud.google.com/certificate-manager/docs/public-ca | 2026-10-03T21:46:13Z | `8acb99c7f5b074724e42075b78d38c9534d16b02a6d6ca3a2d916c3868c20a8c` | 139123 | CC BY 4.0 |
| le_blog_sunlight | docs/le_blog_2025-06-11_sunlight.html | https://letsencrypt.org/2025/06/11/reflections-on-a-year-of-sunlight | 2026-10-03T21:53:30Z | `46b10c3a30e6babc03cb962cb64654a30879cb3dc0c8864948f5a2edc3b69942` | 41226 | MPL-2.0 (LE site) |
| le_blog_90_45 | docs/le_blog_2025-12-02_from_90_to_45.html | https://letsencrypt.org/2025/12/02/from-90-to-45 | 2026-10-03T21:53:28Z | `19d28ce5646e7683723e5c7f834cb5a6bb97708e74df50266df18e9c25603445` | 32938 | MPL-2.0 (LE site) |
| le_blog_6day_ga | docs/le_blog_2026-01-15_6day_ip_ga.html | https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability | 2026-10-03T21:53:24Z | `a579480a14d34a932c2000cad577393a7785622c2f0299c0943f26c3d4349b92` | 29882 | MPL-2.0 (LE site) |
| le_blog_dnspersist | docs/le_blog_2026-02-18_dns_persist_01.html | https://letsencrypt.org/2026/02/18/dns-persist-01 | 2026-10-03T21:53:32Z | `ef2524080310817ff4578ffe5c98dea36dc9ca7fda9be7d6bffc1833da365067` | 35916 | MPL-2.0 (LE site) |
| le_blog_rl_45 | docs/le_blog_2026-02-24_rate_limits_45day.html | https://letsencrypt.org/2026/02/24/rate-limits-45-day-certs | 2026-10-03T21:53:26Z | `b23901feb536ada8de2da076ef420616e34ca99a51c3d6c8c39303560e26fbb5` | 27638 | MPL-2.0 (LE site) |
| le_blog_index | docs/le_blog_index.html | https://letsencrypt.org/blog/ | 2026-10-03T21:46:09Z | `723d6e4c83dbe9d67e9c8d28722aeafcb8f0327bbaf21df314e782cd7f78ea24` | 116040 | MPL-2.0 (LE site) |
| le_challenge_types | docs/le_challenge_types.html | https://letsencrypt.org/docs/challenge-types/ | 2026-10-03T21:46:07Z | `c9b51fea9ba2c0641dd81d5c8c5bceda69a17d56a5f4ac63923e6656d682a7dd` | 34054 | MPL-2.0 (LE site) |
| le_ct_logs | docs/le_ct_logs.html | https://letsencrypt.org/docs/ct-logs/ | 2026-10-03T21:46:05Z | `4549511f685e30ae12ae6fc12bdb90064f26fcd33e30dad075078a482a9b50a9` | 32842 | MPL-2.0 (LE site) |
| le_profiles | docs/le_profiles.html | https://letsencrypt.org/docs/profiles/ | 2026-10-03T21:46:03Z | `788821e3b3ff74ab5b643402780a33f9ad25b8621c48aa7743d40c1cfb4ea87b` | 42607 | MPL-2.0 (LE site) |
| le_rate_limits | docs/le_rate_limits.html | https://letsencrypt.org/docs/rate-limits/ | 2026-10-03T21:46:01Z | `8f6f724c3f3e13713cbf6ad51f8a5bfb94219547cc81b93391dfd0e8e855ee12` | 44096 | MPL-2.0 (LE site) |
| le_site_license_txt | docs/le_website_LICENSE.txt | https://raw.githubusercontent.com/letsencrypt/website/main/LICENSE.txt | 2026-10-03T21:53:34Z | `fab3dd6bdab226f1c08630b1dd917e11fcb4ec5e1e020e2c16f83a0a13863e85` | 16726 | license text |
| openintel_zonestream | docs/openintel_zonestream.html | https://openintel.nl/data/zonestream/ | 2026-10-03T21:53:54Z | `dea7cd39e245d8824e0cfc95c30b4dac86536d5d0cdf6ffba43172849655fee1` | 20074 | page cited only |
| porkbun_api_docs | docs/porkbun_api_docs.html | https://porkbun.com/api/json/v3/documentation | 2026-10-03T21:46:27Z | `3d892beabed4f5d8cdf9d80a1cdd6024810c489775e89ffb4a2b6e4cc890ad4d` | 19753 | (c) publisher; cite |
| porkbun_llms_domain | docs/porkbun_llms_domain.md | https://porkbun.com/llms/domain | 2026-10-03T21:53:46Z | `c0b4b108d116043ed844303de720941d6e062bc0aec25ca133f733cea7b846a0` | 57744 | (c) publisher; cite |
| porkbun_register_guide | docs/porkbun_llms_register_a_domain.md | https://porkbun.com/llms/guides/register-a-domain | 2026-10-03T21:53:50Z | `f90978337b414d9d2c794886fdcb99f1bd23b189123bc4f40af8f6ce73bd5acd` | 7427 | (c) publisher; cite |
| porkbun_spend_limits | docs/porkbun_llms_spend_limits.md | https://porkbun.com/llms/guides/spend-limits | 2026-10-03T21:53:48Z | `7d0d3b03acad9f944f5919a492b4fa30dd49cfc062016208453ffc844280ff51` | 3622 | (c) publisher; cite |
| tor_blog_2025 | docs/tor_blog_staying_ahead_of_censors_2025.html | https://blog.torproject.org/staying-ahead-of-censors-2025/ | 2026-10-03T21:53:56Z | `aef473556e2a73a700e748a2ebcbe6409fb43ee5863f692cddfba5245dabf6e8` | 20482 | (c) publisher; cite |
| tor_webtunnel_setup | docs/tor_webtunnel_setup.html | https://community.torproject.org/relay/setup/webtunnel/ | 2026-10-03T21:53:58Z | `c199785df52d7f1bd0c588987ffa5b089d1372475244c55ba309b00b412cf1d8` | 28145 | (c) publisher; cite |
| whoisds_nrd | docs/whoisds_newly_registered_domains.html | https://www.whoisds.com/newly-registered-domains | 2026-10-03T21:53:52Z | `2b4f3a44fb332bdded1162eb06b675f9276e3afe3b1a804abe49eb01552a53b3` | 50572 | (c) publisher; cite |
| zerossl_acme | docs/zerossl_acme.html | https://zerossl.com/documentation/acme/ | 2026-10-03T21:46:17Z | `e39be894e0f975601a3ff6b8fe4424e8fb0415a1460662ee195e3057857039b7` | 76541 | (c) publisher; cite |
| icann_cfd_202407 | icann_mrr/cfd/cfd-transactions-202407-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202407-en.csv | 2026-10-03T22:03:43Z | `03b996a21eab5cf8af302d0168b841e0cd9f565d866630f028bcdf0a0cea36fd` | 30307 | ICANN report; cite |
| icann_cfd_202408 | icann_mrr/cfd/cfd-transactions-202408-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202408-en.csv | 2026-10-03T22:03:45Z | `dcd8fe8d3683424c49f57ae451ac293e15db636d0c6a59cc2ebb3d42155295b3` | 30490 | ICANN report; cite |
| icann_cfd_202409 | icann_mrr/cfd/cfd-transactions-202409-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202409-en.csv | 2026-10-03T22:03:47Z | `f76b9438fda5c0ebe37674cb08b574dbed4771e716484b37eebe924c10702525` | 30981 | ICANN report; cite |
| icann_cfd_202410 | icann_mrr/cfd/cfd-transactions-202410-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202410-en.csv | 2026-10-03T22:03:49Z | `526bf7f543e5145ac1d948d94202474c83a05f096f9b28a5a4b3e26edd87259f` | 31373 | ICANN report; cite |
| icann_cfd_202411 | icann_mrr/cfd/cfd-transactions-202411-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202411-en.csv | 2026-10-03T22:03:51Z | `ac1da968b41b197d7acf6960bf4bbd94a7efced66c1c7f96840bde41db54013b` | 31571 | ICANN report; cite |
| icann_cfd_202412 | icann_mrr/cfd/cfd-transactions-202412-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202412-en.csv | 2026-10-03T22:03:53Z | `dce71749a5ca05451fb987e5d43ce327a98d290a01a95e6279f1c5d46c88a881` | 31563 | ICANN report; cite |
| icann_cfd_202501 | icann_mrr/cfd/cfd-transactions-202501-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202501-en.csv | 2026-10-03T22:03:55Z | `9b7b45cc6af2c61d5c35ba65e85b7ced4643c386f821dd59f9b899726ae32802` | 31810 | ICANN report; cite |
| icann_cfd_202502 | icann_mrr/cfd/cfd-transactions-202502-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202502-en.csv | 2026-10-03T22:03:57Z | `0c136978ac26131daf00467432365acbbfb77cdb0788b137b892c117c642995c` | 31764 | ICANN report; cite |
| icann_cfd_202503 | icann_mrr/cfd/cfd-transactions-202503-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202503-en.csv | 2026-10-03T22:03:59Z | `e6a5835420aae233486944420cd2bb47254dc3dd06d7068ca0fce115c6131629` | 31774 | ICANN report; cite |
| icann_cfd_202504 | icann_mrr/cfd/cfd-transactions-202504-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202504-en.csv | 2026-10-03T22:04:01Z | `5e54716e52861e6ecb9f3450b42ca067c5556a76dac45b3c0736bb95ecff89dc` | 31770 | ICANN report; cite |
| icann_cfd_202505 | icann_mrr/cfd/cfd-transactions-202505-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202505-en.csv | 2026-10-03T22:04:03Z | `a944e0c55b2f2e16ee7caae7a5b5554159a78e5d719fb4a0030e464d9a3be034` | 32026 | ICANN report; cite |
| icann_cfd_202506 | icann_mrr/cfd/cfd-transactions-202506-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202506-en.csv | 2026-10-03T22:04:05Z | `405a1b39f1d48ee530f04b14dcdbd90ecf8669691efc8e3aa985a2a2f33420b9` | 32327 | ICANN report; cite |
| icann_cfd_202507 | icann_mrr/cfd/cfd-transactions-202507-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202507-en.csv | 2026-10-03T22:04:07Z | `f7f673dd96feeef5a95635e2f7e4c8583e9fd644e44e6123652e68d715e32d2e` | 32634 | ICANN report; cite |
| icann_cfd_202508 | icann_mrr/cfd/cfd-transactions-202508-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202508-en.csv | 2026-10-03T22:04:09Z | `3a9eb9adae43218f78a80061ae31ae58cc0ce001bb93a93b80d38112e284ac51` | 32833 | ICANN report; cite |
| icann_cfd_202509 | icann_mrr/cfd/cfd-transactions-202509-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202509-en.csv | 2026-10-03T22:04:11Z | `aa95d3ec563988ec6b79a8e38e283484c82cc124c026a9dc6a0ccb585cce47b1` | 32938 | ICANN report; cite |
| icann_cfd_202510 | icann_mrr/cfd/cfd-transactions-202510-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202510-en.csv | 2026-10-03T22:04:13Z | `e612c14142cdbd2c81063620ec5b0f4800f33f230e4269314e6ae7437fa9921f` | 33165 | ICANN report; cite |
| icann_cfd_202511 | icann_mrr/cfd/cfd-transactions-202511-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202511-en.csv | 2026-10-03T22:04:15Z | `30c0e484ebd88118530e33e92a00af515401ec616044d5b122704e8a71dcc679` | 33292 | ICANN report; cite |
| icann_cfd_202512 | icann_mrr/cfd/cfd-transactions-202512-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202512-en.csv | 2026-10-03T22:04:17Z | `d8d68c2b3eefc5945b6f5bf5bb7ee9d44ea62178a316b9dc08319cc63a0a56b6` | 33718 | ICANN report; cite |
| icann_cfd_202601 | icann_mrr/cfd/cfd-transactions-202601-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202601-en.csv | 2026-10-03T22:04:19Z | `ff7b8c3ec830e9ab90c6d68f26bd1878a1002a5c98c2b0d1dbb8163a769dabd7` | 33808 | ICANN report; cite |
| icann_cfd_202602 | icann_mrr/cfd/cfd-transactions-202602-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202602-en.csv | 2026-10-03T22:04:21Z | `4616ecbb65b723a6e222e07c3a6a45b2ddcc369c6c3095c7b0aa8cfc90b8898f` | 33795 | ICANN report; cite |
| icann_cfd_202603 | icann_mrr/cfd/cfd-transactions-202603-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202603-en.csv | 2026-10-03T22:04:23Z | `d9ff32b23cf9b31c577005649c61decfd2a60f5ff13ebbfd22aaf88c0486a867` | 33803 | ICANN report; cite |
| icann_cfd_202604 | icann_mrr/cfd/cfd-transactions-202604-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202604-en.csv | 2026-10-03T22:04:25Z | `bc775e5490c699d8426e63551bb80192ba87d2451305a48e384020b1e69c12a5` | 33817 | ICANN report; cite |
| icann_cfd_202605 | icann_mrr/cfd/cfd-transactions-202605-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202605-en.csv | 2026-10-03T22:04:27Z | `571b1ef2cf2cac8aab34c848f3feba71a2ac844969a61999e2f16678bc4362d5` | 34357 | ICANN report; cite |
| icann_cfd_202606 | icann_mrr/cfd/cfd-transactions-202606-en.csv | https://www.icann.org/sites/default/files/mrr/cfd/cfd-transactions-202606-en.csv | 2026-10-03T22:04:29Z | `97f95b461678e0724eb136a562b937dbfa8a5e1c4e826cd7bd1b1b9fef1169ce` | 34768 | ICANN report; cite |
| icann_online_202407 | icann_mrr/online/online-transactions-202407-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202407-en.csv | 2026-10-03T22:02:55Z | `9744de20a05a9890a8e418604ca74a2139fc8fba0464a2a0f1468716e09a13af` | 44363 | ICANN report; cite |
| icann_online_202408 | icann_mrr/online/online-transactions-202408-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202408-en.csv | 2026-10-03T22:02:57Z | `b543cca0af0bb73a14b112dd6c636a97b12f977c685e2ed1d879d2b84c54a7b0` | 44461 | ICANN report; cite |
| icann_online_202409 | icann_mrr/online/online-transactions-202409-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202409-en.csv | 2026-10-03T22:02:59Z | `07992470cf9e5c8caf233a42a8d77fbacbfe3ff2958234661b18dde39399df79` | 44842 | ICANN report; cite |
| icann_online_202410 | icann_mrr/online/online-transactions-202410-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202410-en.csv | 2026-10-03T22:03:01Z | `07446a625d8f603a89037b911b2e9a1efe3434ab070a930377205fd1b3234482` | 45093 | ICANN report; cite |
| icann_online_202411 | icann_mrr/online/online-transactions-202411-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202411-en.csv | 2026-10-03T22:03:03Z | `dc9fa93fcfb6af6ac85173d0236cabcc370e2fb4378d0e522aab8f6e2ae66ab0` | 45300 | ICANN report; cite |
| icann_online_202412 | icann_mrr/online/online-transactions-202412-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202412-en.csv | 2026-10-03T22:03:05Z | `da740bb53d6fec78af1f88de5c1c89dd5bea189de5d64885750d295a89c673ba` | 45447 | ICANN report; cite |
| icann_online_202501 | icann_mrr/online/online-transactions-202501-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202501-en.csv | 2026-10-03T22:03:07Z | `682f498499c916731e7160cd848858a2b05d1fd99c71a240fb6352b09dda2a2d` | 45437 | ICANN report; cite |
| icann_online_202502 | icann_mrr/online/online-transactions-202502-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202502-en.csv | 2026-10-03T22:03:09Z | `55a83d42499567291cbadc766c4bf5420a520915083fe852286f70ab871d9721` | 45222 | ICANN report; cite |
| icann_online_202503 | icann_mrr/online/online-transactions-202503-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202503-en.csv | 2026-10-03T22:03:11Z | `348743f67078d95b0027ca8c8783dac707816e1d4ce182e3f0982dea7b51cef7` | 45447 | ICANN report; cite |
| icann_online_202504 | icann_mrr/online/online-transactions-202504-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202504-en.csv | 2026-10-03T22:03:13Z | `1470d392b9dc14dad16aa6976d943abb6354fdf7b1069b941f5340382f109125` | 45386 | ICANN report; cite |
| icann_online_202505 | icann_mrr/online/online-transactions-202505-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202505-en.csv | 2026-10-03T22:03:15Z | `60e9dd5154d650cb597fd639c4b0b9ff59fcc070f2e4f94b0cfedcba461613fc` | 45487 | ICANN report; cite |
| icann_online_202506 | icann_mrr/online/online-transactions-202506-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202506-en.csv | 2026-10-03T22:03:17Z | `c8e60a082c860657d83aadaa3555f76db1188cef4bd82ab3df379fcdb233f13f` | 45774 | ICANN report; cite |
| icann_online_202507 | icann_mrr/online/online-transactions-202507-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202507-en.csv | 2026-10-03T22:03:19Z | `f0d274e2688a133b695c4a49e2f4788770f6130502d57550616ce583016c7f86` | 46140 | ICANN report; cite |
| icann_online_202508 | icann_mrr/online/online-transactions-202508-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202508-en.csv | 2026-10-03T22:03:21Z | `b561a5d75aa48ba1c1983f0d0cb534453b13764403d398de051c1a0403fa190d` | 46298 | ICANN report; cite |
| icann_online_202509 | icann_mrr/online/online-transactions-202509-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202509-en.csv | 2026-10-03T22:03:23Z | `14e8b654280b6fc746f5bdada8a408f2ef0de9ccb8768992fb0f1530702b3c54` | 46589 | ICANN report; cite |
| icann_online_202510 | icann_mrr/online/online-transactions-202510-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202510-en.csv | 2026-10-03T22:03:25Z | `ea32138cde4922eae66bacbdf0922218113dba3d5eaa597e3a4ceae544d2a41b` | 46878 | ICANN report; cite |
| icann_online_202511 | icann_mrr/online/online-transactions-202511-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202511-en.csv | 2026-10-03T22:03:27Z | `b018ecfac8bb58a5c45c769ba21184cd57279651db0937853dd3acf3a0bb0524` | 47123 | ICANN report; cite |
| icann_online_202512 | icann_mrr/online/online-transactions-202512-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202512-en.csv | 2026-10-03T22:03:29Z | `640a299e511bd0e54649367dbb4775abe0b7795ddfde39f1b4a9a7b9b0aa7841` | 47529 | ICANN report; cite |
| icann_online_202601 | icann_mrr/online/online-transactions-202601-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202601-en.csv | 2026-10-03T22:03:31Z | `3532fb32e839fe2964de68c2c23650cea7fca3cd908965ae7f5a19ac18b69928` | 47698 | ICANN report; cite |
| icann_online_202602 | icann_mrr/online/online-transactions-202602-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202602-en.csv | 2026-10-03T22:03:33Z | `bec420596ecb561049c0bce82b8f70484ab6c3b2dfc30f727fdf529c2f01b653` | 47560 | ICANN report; cite |
| icann_online_202603 | icann_mrr/online/online-transactions-202603-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202603-en.csv | 2026-10-03T22:03:35Z | `d0b99d71ddef53c3ab2c15f35b60de19e34a5cd5e55f67c32dc70c3b978c6bf3` | 47419 | ICANN report; cite |
| icann_online_202604 | icann_mrr/online/online-transactions-202604-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202604-en.csv | 2026-10-03T22:03:37Z | `cf84cc758ec396ebc8f23449549b4a5349b9bc85f7a03ab8a7892365cd87f650` | 38713 | ICANN report; cite |
| icann_online_202605 | icann_mrr/online/online-transactions-202605-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202605-en.csv | 2026-10-03T22:03:39Z | `a36029c9795b7315b2574a325d090d5314718ed5e9ac641a1ee75f92d4d892f1` | 39194 | ICANN report; cite |
| icann_online_202606 | icann_mrr/online/online-transactions-202606-en.csv | https://www.icann.org/sites/default/files/mrr/online/online-transactions-202606-en.csv | 2026-10-03T22:03:41Z | `faea6610d3861ff91e8e8e55246cc5902bfb0abc8704d6c6b1b18c4b20a3e596` | 39426 | ICANN report; cite |
| icann_shop_202407 | icann_mrr/shop/shop-transactions-202407-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202407-en.csv | 2026-10-03T22:02:07Z | `56a75ac548200a17afb53d0e4c28e40c5c224bd4aa54cb063bead6bdd8382b77` | 41247 | ICANN report; cite |
| icann_shop_202408 | icann_mrr/shop/shop-transactions-202408-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202408-en.csv | 2026-10-03T22:02:09Z | `81b2428ddf328dbbd371a706358de6277cc0ef24a54e025176165b44d0cfebe2` | 41571 | ICANN report; cite |
| icann_shop_202409 | icann_mrr/shop/shop-transactions-202409-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202409-en.csv | 2026-10-03T22:02:11Z | `3609445a929b617cc49d3fdf22d9d7c1d3a5dc6b8f042dde0370c7574c60f7e4` | 41770 | ICANN report; cite |
| icann_shop_202410 | icann_mrr/shop/shop-transactions-202410-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202410-en.csv | 2026-10-03T22:02:13Z | `9dca9c0c73626a58e593ad30f625bb0ada05bddb1b07c39ba8add7c4bfc503e4` | 41997 | ICANN report; cite |
| icann_shop_202411 | icann_mrr/shop/shop-transactions-202411-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202411-en.csv | 2026-10-03T22:02:15Z | `0808e2ee6a51e85691079bc1b27fe7a34db38e31b48ef23404f7e7485489059b` | 42244 | ICANN report; cite |
| icann_shop_202412 | icann_mrr/shop/shop-transactions-202412-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202412-en.csv | 2026-10-03T22:02:17Z | `bb2302e0e959c1eeab0053a1945658f1ce3ff310f5ffe73fe3b952cb052f8940` | 42960 | ICANN report; cite |
| icann_shop_202501 | icann_mrr/shop/shop-transactions-202501-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202501-en.csv | 2026-10-03T22:02:19Z | `15844ac48e4c1cd1b8b83ba92c901fde1920c7ff63a439a413494f7943b89ff0` | 42978 | ICANN report; cite |
| icann_shop_202502 | icann_mrr/shop/shop-transactions-202502-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202502-en.csv | 2026-10-03T22:02:21Z | `a5f2995585b248764ecb317b4b61229be550c2ce99386b00caf51edfeaafd931` | 42964 | ICANN report; cite |
| icann_shop_202503 | icann_mrr/shop/shop-transactions-202503-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202503-en.csv | 2026-10-03T22:02:23Z | `53a47151093ccec36fe0db157b25c05ecb6214697aadc68ae787af75cb72cb00` | 43165 | ICANN report; cite |
| icann_shop_202504 | icann_mrr/shop/shop-transactions-202504-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202504-en.csv | 2026-10-03T22:02:25Z | `7911dfc3e22da81b10d625fdeb760b21870033bf6132e81ea147a170399e2eb1` | 43165 | ICANN report; cite |
| icann_shop_202505 | icann_mrr/shop/shop-transactions-202505-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202505-en.csv | 2026-10-03T22:02:27Z | `8b6795a4bab207da09fdd179fccf3ca2beba558fffc4368c85253abe537a9b72` | 43533 | ICANN report; cite |
| icann_shop_202506 | icann_mrr/shop/shop-transactions-202506-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202506-en.csv | 2026-10-03T22:02:29Z | `271523291e2c66eab2e17f802ac0dcabc81314afe90ef26598906f1ab9f7327d` | 43520 | ICANN report; cite |
| icann_shop_202507 | icann_mrr/shop/shop-transactions-202507-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202507-en.csv | 2026-10-03T22:02:31Z | `185d6954046bf2c06cb2581d6c87b7738ec7d08e1e1fbdd87af52df957ff2dfd` | 43554 | ICANN report; cite |
| icann_shop_202508 | icann_mrr/shop/shop-transactions-202508-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202508-en.csv | 2026-10-03T22:02:33Z | `f7b2b65c9c7762b813bf0ebc9ad57a36dd58c83bd4e18189b1707d42e587985f` | 43708 | ICANN report; cite |
| icann_shop_202509 | icann_mrr/shop/shop-transactions-202509-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202509-en.csv | 2026-10-03T22:02:35Z | `137dbc55d267b4dbfe1085cff3be61b2b643bdcd42f0fce8477120e225942606` | 43712 | ICANN report; cite |
| icann_shop_202510 | icann_mrr/shop/shop-transactions-202510-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202510-en.csv | 2026-10-03T22:02:37Z | `ccfedb30eb2fcb4b8dce5b1777d301cf7c3d7943647262b5aee2a8c6d18bb90e` | 44435 | ICANN report; cite |
| icann_shop_202511 | icann_mrr/shop/shop-transactions-202511-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202511-en.csv | 2026-10-03T22:02:39Z | `e45dd7bda67c765efd196375f1958865d62cf347ab140b45f05551b229e609eb` | 44950 | ICANN report; cite |
| icann_shop_202512 | icann_mrr/shop/shop-transactions-202512-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202512-en.csv | 2026-10-03T22:02:41Z | `39eb49a60c4ae5dcdc676272aca9d361a0b37c3af0c96e428d0f4780976480cb` | 45320 | ICANN report; cite |
| icann_shop_202601 | icann_mrr/shop/shop-transactions-202601-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202601-en.csv | 2026-10-03T22:02:43Z | `51ce00cc28cbceacd1ff12793f1c1542dc1a92202b1167cddf10cefe5c4fea65` | 45323 | ICANN report; cite |
| icann_shop_202602 | icann_mrr/shop/shop-transactions-202602-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202602-en.csv | 2026-10-03T22:02:45Z | `5ca7a32329a23b58ab97b7c48db266466b383cbe43e86387a769de517e435adc` | 45307 | ICANN report; cite |
| icann_shop_202603 | icann_mrr/shop/shop-transactions-202603-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202603-en.csv | 2026-10-03T22:02:47Z | `9a894f86f7a756e30281f60ab842aaf9c7653168ea7be9ca4289f5cc935ce785` | 45737 | ICANN report; cite |
| icann_shop_202604 | icann_mrr/shop/shop-transactions-202604-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202604-en.csv | 2026-10-03T22:02:49Z | `bfb0fdcbfb193fee0c195b1dd23ee0d05ffc0fb31428176d30e240e3aa1a969c` | 46267 | ICANN report; cite |
| icann_shop_202605 | icann_mrr/shop/shop-transactions-202605-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202605-en.csv | 2026-10-03T22:02:51Z | `d49de03b429605445c4a9b90be9741be4991cfb76230eab7c70f98feaa179c69` | 46615 | ICANN report; cite |
| icann_shop_202606 | icann_mrr/shop/shop-transactions-202606-en.csv | https://www.icann.org/sites/default/files/mrr/shop/shop-transactions-202606-en.csv | 2026-10-03T22:02:53Z | `8296401139d22ff095ea8c14e0c01559bee83889c38b0e961dc7881c53e7e673` | 46813 | ICANN report; cite |
| icann_top_202407 | icann_mrr/top/top-transactions-202407-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202407-en.csv | 2026-10-03T22:01:19Z | `0c67252473bfb586338ceeb203df62f7891f1d970bd23f5fd4ae361b656584d5` | 21975 | ICANN report; cite |
| icann_top_202408 | icann_mrr/top/top-transactions-202408-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202408-en.csv | 2026-10-03T22:01:21Z | `edaf204eab7f1b35a3b6bba3d3df33fd594caee64b039d37e93c6253b1096967` | 22175 | ICANN report; cite |
| icann_top_202409 | icann_mrr/top/top-transactions-202409-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202409-en.csv | 2026-10-03T22:01:23Z | `a93a524ab0ecbdfd147d2256f960a6198d6a8714c26937099e54d0eea12bace8` | 22171 | ICANN report; cite |
| icann_top_202410 | icann_mrr/top/top-transactions-202410-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202410-en.csv | 2026-10-03T22:01:25Z | `8f1464735746f371b7bf57df7c72c0fb5da765eed01817571b3706ea322edc2f` | 22205 | ICANN report; cite |
| icann_top_202411 | icann_mrr/top/top-transactions-202411-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202411-en.csv | 2026-10-03T22:01:27Z | `5b5ccd46f275f583a9fc1760a8bc1b10a0802a98836ad3f9b1438ebad8dda881` | 22330 | ICANN report; cite |
| icann_top_202412 | icann_mrr/top/top-transactions-202412-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202412-en.csv | 2026-10-03T22:01:29Z | `864274245cdbad0ff238680dd5c425b619412e258b92e0d96e46b427331d0258` | 22342 | ICANN report; cite |
| icann_top_202501 | icann_mrr/top/top-transactions-202501-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202501-en.csv | 2026-10-03T22:01:31Z | `7be7fddc6dbe060c8bd426e9ba4f667fec7bdddb4af66328b9904f1733efd3d1` | 22340 | ICANN report; cite |
| icann_top_202502 | icann_mrr/top/top-transactions-202502-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202502-en.csv | 2026-10-03T22:01:33Z | `ee79e501f27c984fe96997feab2bc107cdc0d30d816f9516df7d178f37e0d198` | 22300 | ICANN report; cite |
| icann_top_202503 | icann_mrr/top/top-transactions-202503-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202503-en.csv | 2026-10-03T22:01:35Z | `346abefcfc45447055ac8b2eb353ed33e6c80af59bfb9e39e71395826ad04bdf` | 22328 | ICANN report; cite |
| icann_top_202504 | icann_mrr/top/top-transactions-202504-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202504-en.csv | 2026-10-03T22:01:37Z | `c3618095300da8541a99fa5109d2f2da6eed466da96d68d6e2d6e15a24b64e34` | 22356 | ICANN report; cite |
| icann_top_202505 | icann_mrr/top/top-transactions-202505-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202505-en.csv | 2026-10-03T22:01:39Z | `494a80b1ee82b44ab6e31b1aee2a1a5b4a793c55033396c3b5f60611b3970d6b` | 22447 | ICANN report; cite |
| icann_top_202506 | icann_mrr/top/top-transactions-202506-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202506-en.csv | 2026-10-03T22:01:41Z | `27092e89d9521586695468ce0ceda673ca8642a30a2f0d41a04f1eb0951aae14` | 22550 | ICANN report; cite |
| icann_top_202507 | icann_mrr/top/top-transactions-202507-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202507-en.csv | 2026-10-03T22:01:43Z | `eddc01bcffb4c972276c49af395347fbb1076935d96b8498252c6f84fceb90c8` | 22648 | ICANN report; cite |
| icann_top_202508 | icann_mrr/top/top-transactions-202508-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202508-en.csv | 2026-10-03T22:01:45Z | `aa09e114c4a1134533a74324a5997b9db10d62a9de608926e102792239e2a6ce` | 22659 | ICANN report; cite |
| icann_top_202509 | icann_mrr/top/top-transactions-202509-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202509-en.csv | 2026-10-03T22:01:47Z | `8da7da1ef08a94fb777fadcbd5788d177a3d984680d4ed0ba6db1b04afbc4c90` | 22906 | ICANN report; cite |
| icann_top_202510 | icann_mrr/top/top-transactions-202510-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202510-en.csv | 2026-10-03T22:01:49Z | `19577cc4eb1a3ce09ce9078039a02f1476119decf42ec8f90ed490704def28f9` | 22886 | ICANN report; cite |
| icann_top_202511 | icann_mrr/top/top-transactions-202511-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202511-en.csv | 2026-10-03T22:01:51Z | `117302f045d58ee14b5871d1a0e6a90ed0da53156eba191a6fa298bac09ccab9` | 22980 | ICANN report; cite |
| icann_top_202512 | icann_mrr/top/top-transactions-202512-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202512-en.csv | 2026-10-03T22:01:53Z | `d8636d4216a2ab7adf9eae06346199c573f28354667e962d78b5519a2da55c1a` | 23182 | ICANN report; cite |
| icann_top_202601 | icann_mrr/top/top-transactions-202601-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202601-en.csv | 2026-10-03T22:01:55Z | `4e26fb0e8ce0ffa886ce3392b4211ba2dea94c44cec84c71e7cceabaeec2a581` | 23201 | ICANN report; cite |
| icann_top_202602 | icann_mrr/top/top-transactions-202602-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202602-en.csv | 2026-10-03T22:01:57Z | `1efa3a51057a5e3dbcef4412ac75144450bd53e3a2a6ed5aa2378bc5b038e0eb` | 21074 | ICANN report; cite |
| icann_top_202603 | icann_mrr/top/top-transactions-202603-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202603-en.csv | 2026-10-03T22:01:59Z | `d3f9af3d54638bd70b610405e30e127b23a20be5246af434fe6b7285f3b12183` | 21145 | ICANN report; cite |
| icann_top_202604 | icann_mrr/top/top-transactions-202604-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202604-en.csv | 2026-10-03T22:02:01Z | `a3fb2253045666399bf09a48fa1d8d471c18cbca46b4049cfcc07ea465c6e51d` | 21116 | ICANN report; cite |
| icann_top_202605 | icann_mrr/top/top-transactions-202605-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202605-en.csv | 2026-10-03T22:02:03Z | `875a9683c67255732afe23174c5ccab6cda3db94c24b05c76488cfd54c777d1b` | 21258 | ICANN report; cite |
| icann_top_202606 | icann_mrr/top/top-transactions-202606-en.csv | https://www.icann.org/sites/default/files/mrr/top/top-transactions-202606-en.csv | 2026-10-03T22:02:05Z | `53c9a8b572d3ecbffde14985c07118e75be1c306d301f3a4d51594c1b1e1277d` | 21372 | ICANN report; cite |
| icann_xyz_202407 | icann_mrr/xyz/xyz-transactions-202407-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202407-en.csv | 2026-10-03T22:00:43Z | `ce747858b503b3a0f1440c720569b21a17dd6f366b1ae464154a78390e3bccaa` | 46800 | ICANN report; cite |
| icann_xyz_202408 | icann_mrr/xyz/xyz-transactions-202408-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202408-en.csv | 2026-10-03T22:00:45Z | `8061540d760dddf3de630aec4765ab93c1d8a3bd61fff3ef1641860acb96f731` | 46863 | ICANN report; cite |
| icann_xyz_202409 | icann_mrr/xyz/xyz-transactions-202409-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202409-en.csv | 2026-10-03T22:00:47Z | `027b97719fdeb7ac6fa1a798a5f5e005190e0800db1a825149e4153a72f215cc` | 47229 | ICANN report; cite |
| icann_xyz_202410 | icann_mrr/xyz/xyz-transactions-202410-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202410-en.csv | 2026-10-03T22:00:49Z | `beff8ef378df4a619afbc945c3204ed737e64cb5c94bdf54c7c1521103442117` | 47517 | ICANN report; cite |
| icann_xyz_202411 | icann_mrr/xyz/xyz-transactions-202411-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202411-en.csv | 2026-10-03T22:00:51Z | `93102b63d7f1d259a4d4b50b7a3c538caa3e91f4f1805e1854b77000496de590` | 47605 | ICANN report; cite |
| icann_xyz_202412 | icann_mrr/xyz/xyz-transactions-202412-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202412-en.csv | 2026-10-03T22:00:53Z | `fd785ef1aa5b4c623db31bc8cb617f21d173dfecf9c61f940e3c232a7ae1c754` | 47642 | ICANN report; cite |
| icann_xyz_202501 | icann_mrr/xyz/xyz-transactions-202501-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202501-en.csv | 2026-10-03T22:00:55Z | `881023ccf5ad08709ba22a7c2f91a4af33f8ff9cafcdccd8b52be384de451e7b` | 47637 | ICANN report; cite |
| icann_xyz_202502 | icann_mrr/xyz/xyz-transactions-202502-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202502-en.csv | 2026-10-03T22:00:57Z | `100c669c77d12ad41d31c38c227a5eae9cc5cdf68f69cb8e258c126e6b33f338` | 47390 | ICANN report; cite |
| icann_xyz_202503 | icann_mrr/xyz/xyz-transactions-202503-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202503-en.csv | 2026-10-03T22:00:59Z | `255fe0722fe27a4037b66879a49b76d36590a66bd016165117917a73d79ee1ec` | 47634 | ICANN report; cite |
| icann_xyz_202504 | icann_mrr/xyz/xyz-transactions-202504-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202504-en.csv | 2026-10-03T22:01:01Z | `b27a0ed8f91c9bb25934c23fc8f275a5cd3e92c8d9d5894b76224e338870bcae` | 47582 | ICANN report; cite |
| icann_xyz_202505 | icann_mrr/xyz/xyz-transactions-202505-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202505-en.csv | 2026-10-03T22:01:03Z | `86469f59c276b5b5f5a87bc55fc1d29a98da8a6fb050766a3c3e9e33c524141d` | 47713 | ICANN report; cite |
| icann_xyz_202506 | icann_mrr/xyz/xyz-transactions-202506-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202506-en.csv | 2026-10-03T22:01:05Z | `30c44c79f5a123d31ab4fea5d29c5ac21dd0562e07c14b8a5f34590bd776bd69` | 47982 | ICANN report; cite |
| icann_xyz_202507 | icann_mrr/xyz/xyz-transactions-202507-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202507-en.csv | 2026-10-03T22:01:07Z | `29105978db1134fec02dc8002a128a956a843061bb580cae2009a834b66e3548` | 48256 | ICANN report; cite |
| icann_xyz_202508 | icann_mrr/xyz/xyz-transactions-202508-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202508-en.csv | 2026-10-03T22:01:09Z | `770af495e960d166cf15c8806764d6bf8f8bfa850569199f587b42b4ed8cf7ec` | 48461 | ICANN report; cite |
| icann_xyz_202509 | icann_mrr/xyz/xyz-transactions-202509-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202509-en.csv | 2026-10-03T22:01:11Z | `5bcee72d89cc563a8c5cd83f610ee1b15c4430d96c4bf50b609b621b5a613e5a` | 48500 | ICANN report; cite |
| icann_xyz_202510 | icann_mrr/xyz/xyz-transactions-202510-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202510-en.csv | 2026-10-03T22:01:13Z | `4a4e2fe6b298f45f47f6db52efdf79f1c8812df715a08db76b46256896a0f08c` | 48780 | ICANN report; cite |
| icann_xyz_202511 | icann_mrr/xyz/xyz-transactions-202511-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202511-en.csv | 2026-10-03T22:01:15Z | `60ef14042d96af3cc6a2ba704c78a5a9319df0318313ee61832dcaac0252911e` | 49038 | ICANN report; cite |
| icann_xyz_202512 | icann_mrr/xyz/xyz-transactions-202512-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202512-en.csv | 2026-10-03T22:01:17Z | `647c0be51501c2aeb897c75f3b063c4f3ed4bb4e49f97126ef037022c8a11488` | 49380 | ICANN report; cite |
| icann_xyz_202601 | icann_mrr/xyz/xyz-transactions-202601-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202601-en.csv | 2026-10-03T22:00:17Z | `c728316bfe7d7c9ad120a91d142d24613ed1c04d316baea83b5ae7eefe6425c5` | 49405 | ICANN report; cite |
| icann_xyz_202602 | icann_mrr/xyz/xyz-transactions-202602-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202602-en.csv | 2026-10-03T22:00:19Z | `7f5e2b1ff2c9b5ef8ae1430d3e5cfe9f7f57107b2d3ed702d9623cb4051c3bba` | 49319 | ICANN report; cite |
| icann_xyz_202603 | icann_mrr/xyz/xyz-transactions-202603-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202603-en.csv | 2026-10-03T22:00:21Z | `f8ef6a449b07d9bf66e06771e75270155248192fbfb150547b2862c957aa182c` | 49355 | ICANN report; cite |
| icann_xyz_202604 | icann_mrr/xyz/xyz-transactions-202604-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202604-en.csv | 2026-10-03T22:00:23Z | `da5c6ee322d4e948d97cef2ee99c97419f4b3f6ddaecc509891aab7b77cc6019` | 49141 | ICANN report; cite |
| icann_xyz_202605 | icann_mrr/xyz/xyz-transactions-202605-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202605-en.csv | 2026-10-03T22:00:25Z | `3dee368f5e36bd9990ca88bf1ea8d41d8623990d3e24dc2c56e7e6c0641d4335` | 49969 | ICANN report; cite |
| icann_xyz_202606 | icann_mrr/xyz/xyz-transactions-202606-en.csv | https://www.icann.org/sites/default/files/mrr/xyz/xyz-transactions-202606-en.csv | 2026-10-03T22:00:27Z | `98ee6aa695684145e24cfa8e1c3061163a5dca26a6dddde62d1f1d5f5b40f167` | 50488 | ICANN report; cite |
| arxiv_gfwatch2021_abs | lit/hoang2021_abs.html | https://arxiv.org/abs/2106.02167 | 2026-10-03T21:46:55Z | `4c3b0e2273aad23fc713ac68bb137e136965ea9f7899470096f3d64875a4f5f6` | 45072 | CC BY-NC-ND 4.0 |
| arxiv_gfwatch2021 | lit/hoang2021_gfwatch.pdf | https://arxiv.org/pdf/2106.02167 | 2026-10-03T21:46:53Z | `35a758642858cedd9337bde7b2830d2416924c3994470696210a74f4ef15e182` | 693218 | CC BY-NC-ND 4.0 |
| arxiv_scheitle2018_abs | lit/scheitle2018_abs.html | https://arxiv.org/abs/1809.08325 | 2026-10-03T21:46:51Z | `b5f21ff9c42eaa13356ffc193942a11365328899f381544817c342a8d92bc2c7` | 44089 | arXiv non-exclusive |
| arxiv_scheitle2018 | lit/scheitle2018_ct_imc.pdf | https://arxiv.org/pdf/1809.08325 | 2026-10-03T21:46:49Z | `03223e87a10ebeb1878c7884c31ed824a67a5fd72897bd55a8bba7b1b7b0d751` | 1778671 | arXiv non-exclusive |
| aws_lambda_urls | platforms/aws_lambda_function_urls.html | https://docs.aws.amazon.com/lambda/latest/dg/urls-configuration.html | 2026-10-03T21:54:50Z | `d3045c5533a301c7f1c3c41277e81b66572f14834ea8e5a46387bd5ba3c69757` | 36907 | (c) publisher; cite |
| aws_lambda_quotas | platforms/aws_lambda_quotas.html | https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html | 2026-10-03T21:54:52Z | `b1be52a4107210083f78e33474c85fb0da1c85a9f9c6834eb8b2edefa9136ef7` | 41681 | (c) publisher; cite |
| azure_limits | platforms/azure_subscription_service_limits.html | https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/azure-subscription-service-limits | 2026-10-03T21:54:56Z | `e467aa97452a16de1071a79de4deba3e685ff1ca5d37556ca5cbf420146c4540` | 383817 | not stated; cite |
| azure_unique_hostname | platforms/azure_unique_default_hostname.html | https://learn.microsoft.com/en-us/azure/app-service/reference-dangling-subdomain-prevention | 2026-10-03T21:54:54Z | `4152ea4cddf34b80eca3f42e01639d8f34a738b2541a272e66df4b3192379fc8` | 61229 | not stated; cite |
| gcr_https | platforms/cloud_run_https_request.html | https://docs.cloud.google.com/run/docs/triggering/https-request | 2026-10-03T21:54:58Z | `aab64b56663cd202497c7ac3618388fed83478e0ebd54808857a21981440ea7c` | 223738 | CC BY 4.0 |
| gcr_quotas | platforms/cloud_run_quotas.html | https://docs.cloud.google.com/run/quotas | 2026-10-03T21:55:00Z | `8bc3d8b0d8f176fed0c29fb7a9957cd2d3589fba3ace4741e29af087369cd9dc` | 141802 | CC BY 4.0 |
| cf_pages_limits | platforms/cloudflare_pages_limits.html | https://developers.cloudflare.com/pages/platform/limits/ | 2026-10-03T21:54:14Z | `8077e036fa968e802d5bb8c26ca660fbd9fedee687306582e8f908cf91c55367` | 128863 | not stated; cite |
| cf_pages_preview | platforms/cloudflare_pages_preview.html | https://developers.cloudflare.com/pages/configuration/preview-deployments/ | 2026-10-03T21:54:16Z | `d1fc2dbafcd3589034ca983bf2a4a84e6cb1fe2fae2ac78f3c6312eecdce30bc` | 126924 | not stated; cite |
| cf_workers_dev | platforms/cloudflare_workers_dev.html | https://developers.cloudflare.com/workers/configuration/routing/workers-dev/ | 2026-10-03T21:54:12Z | `8e56c455acdd1b85abd92347f6fac1738348c8ea1490efc5ec46b6f6f18aefe0` | 195861 | not stated; cite |
| cf_workers_limits | platforms/cloudflare_workers_limits.html | https://developers.cloudflare.com/workers/platform/limits/ | 2026-10-03T21:54:10Z | `ac9cba69707928757a7c57c877eb6e4d6287d203dbea4f2e6ef568066830bd47` | 248286 | not stated; cite |
| deno_classic_domains | platforms/deno_deploy_classic_domains.html | https://docs.deno.com/deploy/classic/custom-domains/ | 2026-10-03T21:54:36Z | `7a9fdc8d78bad88e355d56efc8aa8f1fdc647ecb1b57096dd74371dbaddda1dc` | 48411 | (c) publisher; cite |
| deno_domains | platforms/deno_deploy_domains.html | https://docs.deno.com/deploy/reference/domains/ | 2026-10-03T21:54:32Z | `103996f1ee70ba1a4a329de4cf44455777c1a24fc57ab71ae6aad8dda9621a27` | 63299 | (c) publisher; cite |
| deno_pricing | platforms/deno_deploy_pricing.html | https://deno.com/deploy/pricing | 2026-10-03T21:54:34Z | `e96f2e87d8d0aa80fc0fae45e08be8a62fc1e4ba8183822c6b005ad6c271ae38` | 235538 | (c) publisher; cite |
| firebase_multisites | platforms/firebase_multisites.html | https://firebase.google.com/docs/hosting/multisites | 2026-10-03T21:54:26Z | `b22241c89a943503536eb72c199c8f77d00efba18f7f6ca79f51f20b0e7a4f5f` | 444621 | CC BY 4.0 |
| firebase_preview | platforms/firebase_preview.html | https://firebase.google.com/docs/hosting/test-preview-deploy | 2026-10-03T21:54:30Z | `849274b0644e39508b61b9f03d4b18601596db348576aee3da38a9868cbf0fc0` | 449716 | CC BY 4.0 |
| firebase_quotas | platforms/firebase_quotas.html | https://firebase.google.com/docs/hosting/usage-quotas-pricing | 2026-10-03T21:54:28Z | `dbc3eef4dd6f47723cd5a7a8f11d40e8178d93f9085e3fc7df31baa03e77afd4` | 437919 | CC BY 4.0 |
| fly_custom_domain | platforms/fly_custom_domain.html | https://fly.io/docs/networking/custom-domain/ | 2026-10-03T21:54:40Z | `9301816644e31140e2ce1949d4a02f8229b8cf50bc99cb72742475f93ea305fe` | 528278 | (c) publisher; cite |
| fly_pricing | platforms/fly_pricing.html | https://fly.io/docs/about/pricing/ | 2026-10-03T21:54:42Z | `b8da2037f0ad15282bde8d91cdfaa6ff6f79ec04e4315da9aa42df15f445d409` | 618987 | (c) publisher; cite |
| fly_services | platforms/fly_public_network_services.html | https://fly.io/docs/networking/services/ | 2026-10-03T21:54:38Z | `46a610318c6993be005e5007f43a41fc750a42d63760f545b7a7047059ce9cfc` | 679970 | (c) publisher; cite |
| gh_event_types | platforms/github_event_types.html | https://docs.github.com/en/rest/using-the-rest-api/github-event-types | 2026-10-03T22:00:13Z | `39d65bacbc47331906c08a640ee060790473f88d9ec472e0f1d671962863284b` | 479728 | not stated; cite |
| gh_pages_about | platforms/github_pages_about.html | https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages | 2026-10-03T21:54:02Z | `dac95a956e020946cd707c65cbee288a48f8a507006b0f4de4ede639a3013a61` | 94629 | not stated; cite |
| gh_pages_https | platforms/github_pages_https.html | https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https | 2026-10-03T21:54:06Z | `9e21ee36f2d85317090a196fd4193971911f72bb74e5a2faab43ef1f03a7b3bd` | 145339 | not stated; cite |
| gh_pages_limits | platforms/github_pages_limits.html | https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits | 2026-10-03T21:54:04Z | `33f61c2ad725d56fee6bbc191583b5a4e153408590f9c8cd033ef708f2878e82` | 89148 | not stated; cite |
| gh_events_api | platforms/github_rest_events.html | https://docs.github.com/en/rest/activity/events | 2026-10-03T22:04:59Z | `a75352a34b79887acdb8db040d34d9524cf223dfd90ed5b85a8ac69ea0fdd6be` | 1547617 | not stated; cite |
| gh_tos | platforms/github_terms_of_service.html | https://docs.github.com/en/site-policy/github-terms/github-terms-of-service | 2026-10-03T21:54:08Z | `e2a59f47553fa8a8ee06ea3b123e5c2e743b81410f2559ffdb5f8198a580fdf5` | 367260 | not stated; cite |
| netlify_domains | platforms/netlify_domains.html | https://docs.netlify.com/manage/domains/get-started-with-domains/ | 2026-10-03T21:54:24Z | `8bee4ed20dcc59ce6da889a49766e7c75a2fde17d05729ceacdac5bb84cf724d` | 175903 | (c) publisher; cite |
| netlify_https | platforms/netlify_https.html | https://docs.netlify.com/manage/domains/secure-domains-with-https/https-ssl/ | 2026-10-03T21:54:22Z | `77f9f5b6f1b41e072ce2d8c966ff56ffdfa1be18a8c785208eb80c65fbbe6beb` | 149043 | (c) publisher; cite |
| render_free | platforms/render_free.html | https://render.com/docs/free | 2026-10-03T21:54:46Z | `00271bec42cfd05bec22c0656acb231a353e8823b10152e0371768c3d8b553fc` | 389098 | (c) publisher; cite |
| render_tls | platforms/render_tls.html | https://render.com/docs/tls | 2026-10-03T21:54:44Z | `e5540a679261f552890d2be512064c388f703360b2510fd4d5f4aa9dbfc74ac0` | 281923 | (c) publisher; cite |
| render_web | platforms/render_web_services.html | https://render.com/docs/web-services | 2026-10-03T21:54:48Z | `2069f5d4e6548555528de5c398a18f2d8602ae9f44582b04e9bbdce18c7a0245` | 507534 | (c) publisher; cite |
| vercel_urls | platforms/vercel_generated_urls.md | https://vercel.com/docs/deployments/generated-urls | 2026-10-03T21:54:20Z | `a9deb0446f5bdbd592ef7dfb03605da497a7b6b24426411e9edbca4ac2f5ab11` | 11282 | (c) publisher; cite |
| vercel_limits | platforms/vercel_limits.md | https://vercel.com/docs/limits | 2026-10-03T21:54:18Z | `ffce7e037057817c7bef479b00c6b32e3c97b585a1d52a2fd69f5dc485638bb2` | 62002 | (c) publisher; cite |
| porkbun_pricing | porkbun/porkbun_pricing.json | https://api.porkbun.com/api/json/v3/pricing/get (POST {}) | 2026-10-03T21:46:19Z | `68c2052a4ea338dbe1bbb519e310f1ea0e0398513c8fe3248086b97fb935359c` | 82548 | no license; cite |
| psl_canonical | psl/public_suffix_list_canonical.dat | https://publicsuffix.org/list/public_suffix_list.dat | 2026-10-03T21:53:38Z | `e0fe072d26b0536525badea237953ff451c9f8e64c9d02c6daa81a4491d2fc66` | 334734 | MPL-2.0 |
| iana_tlds | registry/iana_tlds_alpha_by_domain.txt | https://data.iana.org/TLD/tlds-alpha-by-domain.txt | 2026-10-03T21:53:40Z | `f9816a9e5f92191d4a3d73045a579f57eda381dd1ad7b4c535505c7ec610218c` | 9528 | IANA; cite |
| icann_zfa | registry/icann_about_zone_file_access.html | https://www.icann.org/resources/pages/zfa-2013-06-28-en | 2026-10-03T21:53:44Z | `426cd2be73f240d63dae518f6e7a28c7019cc61ec0bc55a18e1056c7d60ea402` | 71081 | ICANN; cite |
| icann_base_ra | registry/icann_base_registry_agreement_2024-01-21.html | https://itp.cdn.icann.org/en/files/registry-agreements/base-registry-agreement-21-01-2024-en.html | 2026-10-03T21:53:42Z | `f5eb83eb63e0b83f8da10d64834e18c77dde48fe596cddc159bfe021ca4eb50e` | 668455 | ICANN; cite |
