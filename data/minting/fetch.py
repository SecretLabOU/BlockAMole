#!/usr/bin/env python3
"""fetch.py -- download the public sources used by the minting analysis.

Every file lands under raw/ and gets an entry in raw/manifest.json with the
URL, HTTP method (and POST body), retrieval time (UTC), HTTP status, sha256,
size and license. Requests are paced at least PACE_S seconds apart.

Scope (no new measurement of any network target): only documentation pages,
the Porkbun public pricing API, ICANN monthly registry reports, the IANA TLD
list, the Public Suffix List, Certificate Transparency policy documents and
Chrome's log list, two arXiv papers, two pinned source files from GitHub
(Let's Encrypt's Boulder and publicsuffix-go), and five exact-identity
crt.sh lookups of platform apex wildcard names. No endpoint, tenant name or
blocked name is resolved, probed or connected to.

Usage:
    python3 fetch.py                 # fetch everything not yet in raw/
    python3 fetch.py --only le_      # fetch ids starting with a prefix
    python3 fetch.py --force ...     # re-fetch even if present
    python3 fetch.py --sync          # refresh manifest metadata; deletes
                                     # files of ids no longer listed here
    python3 fetch.py --sources       # rewrite SOURCES.md from the manifest
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
MANIFEST = os.path.join(RAW, "manifest.json")
PACE_S = 2.0
UA = ("Mozilla/5.0 (X11; Linux x86_64) research-snapshot "
      "(public documentation archive for a censorship-resistance paper)")

# license shorthands
LE_LIC = ("MPL-2.0 (letsencrypt/website repository LICENSE.txt, "
          "raw/docs/le_website_LICENSE.txt); (c) ISRG")
GOOGLE_DOCS = ("CC BY 4.0 for page content, Apache 2.0 for code samples "
               "(stated in the page footer)")
NOT_STATED = ("License not stated on the page (the publisher's docs "
              "repository may carry an open license; not verified here). "
              "Stored as a provenance snapshot: cite, quote briefly, do not "
              "redistribute the file.")
MS_LEARN = NOT_STATED
COPYRIGHT_CITE = ("Copyright of the publisher; no open license stated. "
                  "Stored only as a provenance snapshot: cite the URL, "
                  "quote briefly, do not redistribute the file.")
FACTUAL_API = ("No license stated (public, keyless API returning factual "
               "prices). Cite with retrieval date; do not redistribute bulk.")
ICANN_REPORT = ("Public ICANN registry monthly report (posted under the "
                "Registry Agreement, Spec. 3). No license stated; cite ICANN "
                "and the registry; aggregate figures only.")
IETF = ("IETF Trust Legal Provisions: RFCs may be copied and distributed "
        "in full without modification")
MPL2 = "MPL-2.0 (stated in the file header)"
ARXIV = ("arXiv.org perpetual non-exclusive distribution license "
         "(abstract page); cite the paper, do not redistribute the PDF")
CRTSH = ("crt.sh (Sectigo) search over public CT logs; CT data are public; "
         "no license stated; cite crt.sh")

# id, url, dest (under raw/), license, note, [method, body]
S = []


def src(sid, url, dest, lic, note="", method="GET", body=None,
        headers=None, pace_s=None, timeout=90, tries=3):
    S.append(dict(id=sid, url=url, dest=dest, license=lic, note=note,
                  method=method, body=body, headers=headers or {},
                  pace_s=pace_s, timeout=timeout, tries=tries))


# ---- Certificate authorities and ACME -------------------------------------
src("le_rate_limits", "https://letsencrypt.org/docs/rate-limits/",
    "docs/le_rate_limits.html", LE_LIC,
    "Let's Encrypt rate limits (page stamped 'Last updated').")
src("le_profiles", "https://letsencrypt.org/docs/profiles/",
    "docs/le_profiles.html", LE_LIC,
    "Let's Encrypt certificate profiles (classic, tlsserver, shortlived).")
src("le_ct_logs", "https://letsencrypt.org/docs/ct-logs/",
    "docs/le_ct_logs.html", LE_LIC,
    "Let's Encrypt CT log operation and logging of issued certificates.")
src("le_challenge_types", "https://letsencrypt.org/docs/challenge-types/",
    "docs/le_challenge_types.html", LE_LIC,
    "ACME challenge types; wildcard certificates need DNS-01.")
src("le_blog_index", "https://letsencrypt.org/blog/",
    "docs/le_blog_index.html", LE_LIC,
    "Blog index, used only to locate the short-lived/IP certificate posts.")
src("gts_quotas",
    "https://cloud.google.com/certificate-manager/docs/quotas",
    "docs/gts_certmanager_quotas.html", GOOGLE_DOCS,
    "Certificate Manager quotas incl. Public CA (Google Trust Services) ACME.")
src("gts_public_ca",
    "https://cloud.google.com/certificate-manager/docs/public-ca",
    "docs/gts_public_ca.html", GOOGLE_DOCS,
    "Google Public CA overview (ACME, EAB, validity).")
src("gts_pricing", "https://cloud.google.com/certificate-manager/pricing",
    "docs/gts_certmanager_pricing.html", COPYRIGHT_CITE,
    "Certificate Manager pricing (Public CA certificates free).")
src("zerossl_acme", "https://zerossl.com/documentation/acme/",
    "docs/zerossl_acme.html", COPYRIGHT_CITE,
    "ZeroSSL ACME documentation.")

# ---- Domain prices ---------------------------------------------------------
src("porkbun_pricing", "https://api.porkbun.com/api/json/v3/pricing/get",
    "porkbun/porkbun_pricing.json", FACTUAL_API,
    "Porkbun public pricing endpoint (POST, no key).", method="POST",
    body="{}", headers={"Content-Type": "application/json"})
src("porkbun_api_docs", "https://porkbun.com/api/json/v3/documentation",
    "docs/porkbun_api_docs.html", COPYRIGHT_CITE,
    "Porkbun API v3 documentation (programmatic registration, limits).")

# ---- Public Suffix List ----------------------------------------------------

# ---- Certificate Transparency ----------------------------------------------
src("rfc6962", "https://www.rfc-editor.org/rfc/rfc6962.txt",
    "ct/rfc6962.txt", IETF, "RFC 6962 Certificate Transparency (MMD).")
src("rfc9162", "https://www.rfc-editor.org/rfc/rfc9162.txt",
    "ct/rfc9162.txt", IETF, "RFC 9162 Certificate Transparency v2.0.")
src("chrome_ct_policy", "https://raw.githubusercontent.com/GoogleChrome/"
    "CertificateTransparency/master/ct_policy.md", "ct/chrome_ct_policy.md",
    "Apache-2.0 (repository LICENSE, raw/ct/chrome_ct_LICENSE.txt)",
    "Chrome CT policy (certificates must carry SCTs).")
src("chrome_log_policy", "https://raw.githubusercontent.com/GoogleChrome/"
    "CertificateTransparency/master/log_policy.md", "ct/chrome_log_policy.md",
    "Apache-2.0 (repository LICENSE, raw/ct/chrome_ct_LICENSE.txt)",
    "Chrome CT log policy (MMD requirement).")
src("chrome_ct_license", "https://raw.githubusercontent.com/GoogleChrome/"
    "CertificateTransparency/master/LICENSE", "ct/chrome_ct_LICENSE.txt",
    "(license file itself)", "License of the Chrome CT policy repository.")
src("apple_ct_policy", "https://support.apple.com/en-us/103214",
    "ct/apple_ct_policy.html", COPYRIGHT_CITE,
    "Apple's Certificate Transparency policy.")
src("chrome_log_list", "https://www.gstatic.com/ct/log_list/v3/log_list.json",
    "ct/chrome_log_list_v3.json",
    "Published by Google for public consumption; no license stated; cite",
    "Chrome's CT log list v3 (per-log MMD, state, operator).")
src("static_ct_api", "https://raw.githubusercontent.com/C2SP/C2SP/main/"
    "static-ct-api.md", "ct/c2sp_static_ct_api.md",
    "C2SP repository; no license stated in the file; cite",
    "C2SP static-ct-api spec (tiled logs, SCT after sequencing).")
src("sunlight_readme", "https://raw.githubusercontent.com/FiloSottile/"
    "sunlight/main/README.md", "ct/sunlight_README.md",
    "FiloSottile/sunlight repository; no license stated in the file; cite",
    "Sunlight CT log implementation README.")

# ---- Literature (arXiv) ----------------------------------------------------
src("arxiv_scheitle2018", "https://arxiv.org/pdf/1809.08325",
    "lit/scheitle2018_ct_imc.pdf", ARXIV,
    "Scheitle et al., The Rise of Certificate Transparency and Its "
    "Implications on the Internet Ecosystem, IMC 2018 (CT honeypot timing).")
src("arxiv_scheitle2018_abs", "https://arxiv.org/abs/1809.08325",
    "lit/scheitle2018_abs.html", ARXIV, "arXiv abstract page (license).")
src("arxiv_gfwatch2021", "https://arxiv.org/pdf/2106.02167",
    "lit/hoang2021_gfwatch.pdf", "CC BY-NC-ND 4.0 (arXiv abstract page)",
    "Hoang et al., How Great is the Great Firewall? USENIX Security 2021 "
    "(daily zone-file-driven testing).")
src("arxiv_gfwatch2021_abs", "https://arxiv.org/abs/2106.02167",
    "lit/hoang2021_abs.html", "CC BY-NC-ND 4.0 (arXiv abstract page)",
    "arXiv abstract page (license).")


# ---- Let's Encrypt announcements and license ------------------------------
src("le_blog_6day_ga",
    "https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability",
    "docs/le_blog_2026-01-15_6day_ip_ga.html", LE_LIC,
    "GA announcement of 6-day (shortlived) and IP address certificates.")
src("le_blog_rl_45",
    "https://letsencrypt.org/2026/02/24/rate-limits-45-day-certs",
    "docs/le_blog_2026-02-24_rate_limits_45day.html", LE_LIC,
    "Shorter lifetimes and rate limits (renewals do not count).")
src("le_blog_90_45", "https://letsencrypt.org/2025/12/02/from-90-to-45",
    "docs/le_blog_2025-12-02_from_90_to_45.html", LE_LIC,
    "Timeline for decreasing default lifetimes to 45 days.")
src("le_blog_sunlight",
    "https://letsencrypt.org/2025/06/11/reflections-on-a-year-of-sunlight",
    "docs/le_blog_2025-06-11_sunlight.html", LE_LIC,
    "Let's Encrypt's static-ct (Sunlight) logs after one year.")
src("le_blog_dnspersist", "https://letsencrypt.org/2026/02/18/dns-persist-01",
    "docs/le_blog_2026-02-18_dns_persist_01.html", LE_LIC,
    "DNS-PERSIST-01 persistent authorization record.")
src("le_site_license_txt", "https://raw.githubusercontent.com/letsencrypt/"
    "website/main/LICENSE.txt", "docs/le_website_LICENSE.txt",
    "(license file itself)", "License of the letsencrypt.org website repo.")
src("le_site_license_md", "https://raw.githubusercontent.com/letsencrypt/"
    "website/main/LICENSE.md", "docs/le_website_LICENSE.md",
    "(license file itself)", "License of the letsencrypt.org website repo "
    "(alternate file name).")

# ---- Registries, zone files, NRD feeds -------------------------------------
src("psl_canonical", "https://publicsuffix.org/list/public_suffix_list.dat",
    "psl/public_suffix_list_canonical.dat", MPL2,
    "Canonical PSL URL (the file asks to be pulled from here).")
src("iana_tlds", "https://data.iana.org/TLD/tlds-alpha-by-domain.txt",
    "registry/iana_tlds_alpha_by_domain.txt",
    "IANA public data; no license stated; cite IANA",
    "Root-zone TLD list, used to keep only ICANN TLDs in the price table.")
src("icann_base_ra", "https://itp.cdn.icann.org/en/files/registry-agreements/"
    "base-registry-agreement-21-01-2024-en.html",
    "registry/icann_base_registry_agreement_2024-01-21.html",
    "ICANN public agreement text; cite ICANN",
    "Base gTLD Registry Agreement: Spec. 3 report fields, Spec. 4 zone "
    "file access.")
src("icann_zfa", "https://www.icann.org/resources/pages/zfa-2013-06-28-en",
    "registry/icann_about_zone_file_access.html",
    "ICANN website content; cite ICANN", "About Zone File Access (CZDS).")
src("porkbun_llms_domain", "https://porkbun.com/llms/domain",
    "docs/porkbun_llms_domain.md", COPYRIGHT_CITE,
    "Porkbun domain API reference (registration endpoint, limits).")
src("porkbun_spend_limits", "https://porkbun.com/llms/guides/spend-limits",
    "docs/porkbun_llms_spend_limits.md", COPYRIGHT_CITE,
    "Porkbun API spend controls guide.")
src("porkbun_register_guide",
    "https://porkbun.com/llms/guides/register-a-domain",
    "docs/porkbun_llms_register_a_domain.md", COPYRIGHT_CITE,
    "Porkbun guide: register a domain over the API.")
src("whoisds_nrd", "https://www.whoisds.com/newly-registered-domains",
    "docs/whoisds_newly_registered_domains.html", COPYRIGHT_CITE,
    "WhoisDS free daily newly-registered-domain lists (page only; no list "
    "downloaded).")
src("openintel_zonestream", "https://openintel.nl/data/zonestream/",
    "docs/openintel_zonestream.html",
    "OpenINTEL website; data under CC BY-NC-SA 4.0; page cited only",
    "OpenINTEL Zonestream: real-time newly registered domains from CT.")
src("tor_blog_2025", "https://blog.torproject.org/staying-ahead-of-censors-2025/",
    "docs/tor_blog_staying_ahead_of_censors_2025.html", COPYRIGHT_CITE,
    "Tor Project: WebTunnel non-WebPKI certificates with chain pinning.")
src("tor_webtunnel_setup",
    "https://community.torproject.org/relay/setup/webtunnel/",
    "docs/tor_webtunnel_setup.html", COPYRIGHT_CITE,
    "WebTunnel bridge setup guide (operator domain plus certificate).")
src("gharchive", "https://www.gharchive.org/", "docs/gharchive_home.html",
    COPYRIGHT_CITE, "GH Archive: hourly archives of the public GitHub "
    "event timeline.")

# ---- Platform documentation --------------------------------------------------
GHD = NOT_STATED
CFD = NOT_STATED
src("gh_pages_about", "https://docs.github.com/en/pages/getting-started-with-"
    "github-pages/about-github-pages", "platforms/github_pages_about.html",
    GHD, "GitHub Pages site types, default domains, plans.")
src("gh_pages_limits", "https://docs.github.com/en/pages/getting-started-"
    "with-github-pages/github-pages-limits", "platforms/github_pages_limits.html",
    GHD, "GitHub Pages usage limits.")
src("gh_pages_https", "https://docs.github.com/en/pages/getting-started-with-"
    "github-pages/securing-your-github-pages-site-with-https",
    "platforms/github_pages_https.html", GHD, "GitHub Pages HTTPS.")
src("gh_tos", "https://docs.github.com/en/site-policy/github-terms/"
    "github-terms-of-service", "platforms/github_terms_of_service.html", GHD,
    "GitHub Terms of Service (account rules).")
src("cf_workers_limits",
    "https://developers.cloudflare.com/workers/platform/limits/",
    "platforms/cloudflare_workers_limits.html", CFD,
    "Cloudflare Workers limits (Workers per account).")
src("cf_workers_dev", "https://developers.cloudflare.com/workers/"
    "configuration/routing/workers-dev/", "platforms/cloudflare_workers_dev.html",
    CFD, "workers.dev subdomain format and certificate provisioning.")
src("cf_pages_limits", "https://developers.cloudflare.com/pages/platform/"
    "limits/", "platforms/cloudflare_pages_limits.html", CFD,
    "Cloudflare Pages limits (projects per account).")
src("cf_pages_preview", "https://developers.cloudflare.com/pages/"
    "configuration/preview-deployments/",
    "platforms/cloudflare_pages_preview.html", CFD,
    "Cloudflare Pages preview deployment URLs.")
src("vercel_limits", "https://vercel.com/docs/limits",
    "platforms/vercel_limits.md", COPYRIGHT_CITE, "Vercel limits.")
src("vercel_urls", "https://vercel.com/docs/deployments/generated-urls",
    "platforms/vercel_generated_urls.md", COPYRIGHT_CITE,
    "Vercel generated deployment URLs.")
src("netlify_https", "https://docs.netlify.com/manage/domains/"
    "secure-domains-with-https/https-ssl/", "platforms/netlify_https.html",
    COPYRIGHT_CITE, "Netlify HTTPS.")
src("netlify_domains", "https://docs.netlify.com/manage/domains/"
    "get-started-with-domains/", "platforms/netlify_domains.html",
    COPYRIGHT_CITE, "Netlify default subdomains.")
src("firebase_multisites", "https://firebase.google.com/docs/hosting/"
    "multisites", "platforms/firebase_multisites.html", GOOGLE_DOCS,
    "Firebase Hosting: multiple sites per project.")
src("firebase_quotas", "https://firebase.google.com/docs/hosting/"
    "usage-quotas-pricing", "platforms/firebase_quotas.html", GOOGLE_DOCS,
    "Firebase Hosting quotas and pricing.")
src("firebase_preview", "https://firebase.google.com/docs/hosting/"
    "test-preview-deploy", "platforms/firebase_preview.html", GOOGLE_DOCS,
    "Firebase Hosting preview channels (URL format).")
src("deno_domains", "https://docs.deno.com/deploy/reference/domains/",
    "platforms/deno_deploy_domains.html", COPYRIGHT_CITE,
    "Deno Deploy default domains.")
src("deno_pricing", "https://deno.com/deploy/pricing",
    "platforms/deno_deploy_pricing.html", COPYRIGHT_CITE,
    "Deno Deploy plans and limits.")
src("deno_classic_domains", "https://docs.deno.com/deploy/classic/"
    "custom-domains/", "platforms/deno_deploy_classic_domains.html",
    COPYRIGHT_CITE, "Deno Deploy Classic (deno.dev) domains.")
src("fly_services", "https://fly.io/docs/networking/services/",
    "platforms/fly_public_network_services.html", COPYRIGHT_CITE,
    "Fly.io public network services (fly.dev hostnames, TLS).")
src("fly_custom_domain", "https://fly.io/docs/networking/custom-domain/",
    "platforms/fly_custom_domain.html", COPYRIGHT_CITE,
    "Fly.io custom domains and certificates.")
src("fly_pricing", "https://fly.io/docs/about/pricing/",
    "platforms/fly_pricing.html", COPYRIGHT_CITE, "Fly.io pricing.")
src("render_tls", "https://render.com/docs/tls", "platforms/render_tls.html",
    COPYRIGHT_CITE, "Render managed TLS.")
src("render_free", "https://render.com/docs/free",
    "platforms/render_free.html", COPYRIGHT_CITE, "Render free tier.")
src("render_web", "https://render.com/docs/web-services",
    "platforms/render_web_services.html", COPYRIGHT_CITE,
    "Render web services (onrender.com subdomain).")
src("aws_lambda_urls", "https://docs.aws.amazon.com/lambda/latest/dg/"
    "urls-configuration.html", "platforms/aws_lambda_function_urls.html",
    COPYRIGHT_CITE, "AWS Lambda function URLs (URL format).")
src("aws_lambda_quotas", "https://docs.aws.amazon.com/lambda/latest/dg/"
    "gettingstarted-limits.html", "platforms/aws_lambda_quotas.html",
    COPYRIGHT_CITE, "AWS Lambda quotas.")
src("azure_unique_hostname", "https://learn.microsoft.com/en-us/azure/"
    "app-service/reference-dangling-subdomain-prevention",
    "platforms/azure_unique_default_hostname.html", MS_LEARN,
    "Azure App Service secure unique default hostnames.")
src("azure_limits", "https://learn.microsoft.com/en-us/azure/"
    "azure-resource-manager/management/azure-subscription-service-limits",
    "platforms/azure_subscription_service_limits.html", MS_LEARN,
    "Azure subscription and service limits (App Service).")
src("gcr_https", "https://docs.cloud.google.com/run/docs/triggering/"
    "https-request", "platforms/cloud_run_https_request.html", GOOGLE_DOCS,
    "Cloud Run service URLs.")
src("gcr_quotas", "https://docs.cloud.google.com/run/quotas",
    "platforms/cloud_run_quotas.html", GOOGLE_DOCS, "Cloud Run quotas.")


# ---- GitHub public event types (exposure of github.io names) ---------------
src("gh_event_types", "https://docs.github.com/en/rest/using-the-rest-api/"
    "github-event-types", "platforms/github_event_types.html", GHD,
    "GitHub event types (CreateEvent for repositories) in the public "
    "timeline archived by GH Archive.")
src("gh_events_api", "https://docs.github.com/en/rest/activity/events",
    "platforms/github_rest_events.html", GHD,
    "GitHub REST events endpoints (public events, stated latency).")
src("rfc9525", "https://www.rfc-editor.org/rfc/rfc9525.txt",
    "ct/rfc9525.txt", IETF,
    "RFC 9525 service identity: a wildcard matches exactly one label.")

# ---- Let's Encrypt's registered-domain computation (source code) -----------
# Commits pinned with `git ls-remote <repo> refs/heads/main` on 2026-10-03.
BOULDER = "1578a1d051b87ded8f60f3af7f6e79f0da0a8d81"
PSLGO = "32ef0a9d3d18fb4d7e7af481a56f36263a4b2c43"
src("boulder_ratelimits_utilities", "https://raw.githubusercontent.com/"
    "letsencrypt/boulder/%s/ratelimits/utilities.go" % BOULDER,
    "code/boulder_%s_ratelimits_utilities.go" % BOULDER[:12],
    "MPL-2.0 (letsencrypt/boulder LICENSE.txt)",
    "Boulder (Let's Encrypt CA) rate-limit keys: publicsuffix.Domain().")
src("boulder_license", "https://raw.githubusercontent.com/letsencrypt/"
    "boulder/%s/LICENSE.txt" % BOULDER, "code/boulder_LICENSE.txt",
    "(license file itself)", "Boulder license.")
src("pslgo_publicsuffix", "https://raw.githubusercontent.com/weppos/"
    "publicsuffix-go/%s/publicsuffix/publicsuffix.go" % PSLGO,
    "code/publicsuffix-go_%s_publicsuffix.go" % PSLGO[:12],
    "MIT (weppos/publicsuffix-go LICENSE.txt)",
    "publicsuffix-go: DefaultFindOptions{IgnorePrivate: false}.")
src("pslgo_license", "https://raw.githubusercontent.com/weppos/"
    "publicsuffix-go/%s/LICENSE.txt" % PSLGO, "code/publicsuffix-go_LICENSE.txt",
    "(license file itself)", "publicsuffix-go license.")

# ---- ICANN monthly registry transaction reports ----------------------------
ICANN_TLDS = ["xyz", "top", "shop", "online", "cfd"]
ICANN_MONTHS = ["%04d%02d" % (y, m) for y in (2024, 2025, 2026)
                for m in range(1, 13)
                if (2024, 7) <= (y, m) <= (2026, 6)]
for _t in ICANN_TLDS:
    for _ym in ICANN_MONTHS:
        src("icann_%s_%s" % (_t, _ym),
            "https://www.icann.org/sites/default/files/mrr/%s/"
            "%s-transactions-%s-en.csv" % (_t, _t, _ym),
            "icann_mrr/%s/%s-transactions-%s-en.csv" % (_t, _t, _ym),
            ICANN_REPORT,
            "Per-registrar monthly transactions report, .%s, %s." % (_t, _ym))


# ---- crt.sh: at most five exact-identity lookups of platform apex wildcards --
# Exact identity strings only (no '%' patterns, no suffix-wide queries),
# unexpired certificates only, spaced 20 s apart.
CRTSH_IDS = ["*.github.io", "*.vercel.app", "*.netlify.app", "*.pages.dev",
             "*.web.app"]
for _q in CRTSH_IDS:
    _slug = _q.replace("*.", "wild_").replace(".", "_")
    src("crtsh_" + _slug, "https://crt.sh/?q=%s&output=json&exclude=expired"
        % _q.replace("*", "%2A"), "crtsh/crtsh_%s.json" % _slug, CRTSH,
        "crt.sh exact-identity lookup for '%s' (unexpired certificates)."
        % _q, pace_s=20, timeout=180, tries=2)


def load_manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            return json.load(f)
    return {"description": "Provenance of every raw file (see fetch.py)",
            "files": []}


def save_manifest(m):
    m["files"].sort(key=lambda e: e["path"])
    m["updated_utc"] = now()
    with open(MANIFEST, "w") as f:
        json.dump(m, f, indent=1, sort_keys=False)
        f.write("\n")


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


_last = [0.0]


def pace(p=None):
    wait = (p or PACE_S) - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()


def fetch_one(s, sess):
    timeout = s.get("timeout", 90)
    tries = s.get("tries", 3)
    dest = os.path.join(RAW, s["dest"])
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    err = None
    for k in range(tries):
        pace(s.get("pace_s"))
        t = now()
        try:
            hdr = {"User-Agent": UA}
            hdr.update(s["headers"])
            if s["method"] == "POST":
                r = sess.post(s["url"], data=s["body"], headers=hdr,
                              timeout=timeout)
            else:
                r = sess.get(s["url"], headers=hdr, timeout=timeout)
        except requests.RequestException as e:
            err = repr(e)
            time.sleep(5 * (k + 1))
            continue
        if r.status_code >= 500 or r.status_code == 429:
            err = "HTTP %d" % r.status_code
            time.sleep(10 * (k + 1))
            continue
        if r.status_code >= 400:
            return dict(id=s["id"], url=s["url"],
                        error="HTTP %d" % r.status_code, retrieved_utc=t)
        with open(dest, "wb") as f:
            f.write(r.content)
        return dict(id=s["id"], path=os.path.relpath(dest, HERE),
                    url=s["url"], method=s["method"],
                    request_body=s["body"], final_url=r.url,
                    retrieved_utc=t, http_status=r.status_code,
                    content_type=r.headers.get("Content-Type", ""),
                    last_modified=r.headers.get("Last-Modified", ""),
                    sha256=sha256(dest), size_bytes=os.path.getsize(dest),
                    license=s["license"], note=s["note"])
    return dict(id=s["id"], url=s["url"], error=err, retrieved_utc=now())


def sync(m):
    """Bring manifest metadata in line with the registry without refetching:
    update license/note, move files whose destination changed (sha256 is
    re-checked), and drop entries (and files) no longer in the registry."""
    reg = {s["id"]: s for s in S}
    keep = []
    for e in m["files"]:
        s = reg.get(e["id"])
        old = os.path.join(HERE, e["path"])
        if s is None:
            if os.path.exists(old):
                os.remove(old)
            print("dropped", e["id"], e["path"])
            continue
        new = os.path.join(RAW, s["dest"])
        if os.path.abspath(old) != os.path.abspath(new):
            os.makedirs(os.path.dirname(new), exist_ok=True)
            os.replace(old, new)
            e["path"] = os.path.relpath(new, HERE)
            print("moved", e["id"], "->", e["path"])
        assert sha256(new) == e["sha256"], e["id"]
        e["license"], e["note"] = s["license"], s["note"]
        keep.append(e)
    m["files"] = keep
    save_manifest(m)


# Requests that returned no file (recorded for transparency; times are the
# windows in which the attempts ran, from the surrounding manifest entries).
FAILED = [
    dict(url="https://crt.sh/?q=%2A.vercel.app&output=json&exclude=expired",
         attempts=2, result="HTTP 504 both times",
         window_utc="2026-10-03T22:05:27Z..22:08:54Z"),
    dict(url="https://crt.sh/?q=%2A.pages.dev&output=json&exclude=expired",
         attempts=2, result="HTTP 502 both times",
         window_utc="2026-10-03T22:08:54Z..22:12:05Z"),
    dict(url="https://raw.githubusercontent.com/letsencrypt/website/main/"
         "LICENSE.md", attempts=1, result="HTTP 404 (file is LICENSE.txt)",
         window_utc="2026-10-03"),
    dict(url="https://www.icann.org/sites/default/files/mrr/xyz/"
         "xyz-transactions-202607-en.csv", attempts=1,
         result="HTTP 404 (July 2026 not yet published; June 2026 is the "
         "latest month)", window_utc="2026-10-03"),
]

LIC_SHORT = [  # (prefix of the manifest license string, short label)
    ("MPL-2.0 (letsencrypt/website", "MPL-2.0 (LE site)"),
    ("CC BY 4.0 for page content", "CC BY 4.0"),
    ("License not stated on the page", "not stated; cite"),
    ("Copyright of the publisher", "(c) publisher; cite"),
    ("No license stated (public, keyless API", "no license; cite"),
    ("Public ICANN registry monthly report", "ICANN report; cite"),
    ("ICANN", "ICANN; cite"),
    ("IETF Trust", "IETF Trust (RFC)"),
    ("MPL-2.0", "MPL-2.0"),
    ("MIT", "MIT"),
    ("Apache-2.0", "Apache-2.0"),
    ("arXiv.org perpetual", "arXiv non-exclusive"),
    ("CC BY-NC-ND 4.0", "CC BY-NC-ND 4.0"),
    ("crt.sh", "CT data via crt.sh; cite"),
    ("IANA", "IANA; cite"),
    ("Published by Google", "no license; cite"),
    ("OpenINTEL website", "page cited only"),
    ("(license file itself)", "license text"),
    ("C2SP repository", "not stated; cite"),
    ("FiloSottile/sunlight", "not stated; cite"),
]


def short_license(lic):
    for pre, lab in LIC_SHORT:
        if lic.startswith(pre):
            return lab
    return lic.split(";")[0][:40]


SOURCES_HEAD = """# Sources: minting (cost, speed and exposure of new blockable names)

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
"""


def write_sources(m):
    m["failed_requests"] = FAILED
    save_manifest(m)
    out = [SOURCES_HEAD, "\n## Requests that returned no file\n\n",
           "| URL | attempts | result | when (UTC) |\n|---|---|---|---|\n"]
    for f in FAILED:
        out.append("| %s | %d | %s | %s |\n" % (f["url"], f["attempts"],
                                              f["result"], f["window_utc"]))
    out.append("\n## File inventory (from raw/manifest.json)\n\n"
               "Every raw file with its URL, retrieval time (UTC), sha256, "
               "size and license (short label; the full license text of "
               "each entry is in raw/manifest.json).\n\n"
               "| id | file (under raw/) | URL | retrieved (UTC) | sha256 | "
               "bytes | license |\n|---|---|---|---|---|---|---|\n")
    for e in sorted(m["files"], key=lambda e: e["path"]):
        url = e["url"] + (" (POST %s)" % e["request_body"]
                          if e.get("method") == "POST" else "")
        out.append("| %s | %s | %s | %s | `%s` | %d | %s |\n" % (
            e["id"], e["path"][len("raw/"):], url, e["retrieved_utc"],
            e["sha256"], e["size_bytes"], short_license(e["license"])))
    with open(os.path.join(HERE, "SOURCES.md"), "w") as f:
        f.write("".join(out))
    print("wrote SOURCES.md with %d files" % len(m["files"]))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--sync", action="store_true",
                    help="update manifest metadata from the registry only")
    ap.add_argument("--sources", action="store_true",
                    help="rewrite SOURCES.md from the manifest")
    a = ap.parse_args(argv)
    m = load_manifest()
    if a.sync:
        sync(m)
        return
    if a.sources:
        write_sources(m)
        return
    have = {e["id"]: e for e in m["files"]}
    sess = requests.Session()
    todo = [s for s in S if (not a.only or
                             any(s["id"].startswith(p) for p in a.only))]
    for s in todo:
        if s["id"] in have and not a.force and \
                os.path.exists(os.path.join(HERE, have[s["id"]]["path"])):
            continue
        e = fetch_one(s, sess)
        if "error" in e:
            print("FAIL", s["id"], e["error"], file=sys.stderr)
            continue
        m["files"] = [x for x in m["files"] if x["id"] != s["id"]]
        m["files"].append(e)
        save_manifest(m)
        print("%-28s %3d %9d %s" % (e["id"], e["http_status"],
                                    e["size_bytes"], e["final_url"]))


if __name__ == "__main__":
    main()
