"""facts.py -- documented facts used by the minting analysis.

Each fact is a short verbatim quote from a saved source in raw/ (identified
by its manifest id), plus the value it supports. analysis.py checks that
every quote occurs in the text snapshot of its source (case-, quote-style-
and whitespace-insensitive) and stops if one does not.

Fields: id, src (manifest id), quote, value, unit, what.
"""

FACTS = [
    # ---------------- Let's Encrypt rate limits -----------------------------
    dict(id="le_rl_updated", src="le_rate_limits",
         quote="Last updated: August 5, 2026",
         value="2026-08-05", unit="date",
         what="Date stamp of the Let's Encrypt rate-limits page"),
    dict(id="le_accounts_per_ipv4", src="le_rate_limits",
         quote="Up to 10 accounts can be created from a single IP address "
               "every 3 hours. The ability to create new accounts refills at "
               "a rate of 1 account every 18 minutes.",
         value="10/3h; refill 1 per 18 min", unit="accounts per IP",
         what="New ACME accounts per IP address"),
    dict(id="le_accounts_per_ipv6_48", src="le_rate_limits",
         quote="Up to 500 accounts can be created from a single /48 IPv6 "
               "subnet every 3 hours.",
         value="500/3h", unit="accounts per IPv6 /48",
         what="New ACME accounts per IPv6 /48"),
    dict(id="le_orders_per_account", src="le_rate_limits",
         quote="Up to 300 new orders can be created by a single account every "
               "3 hours. The ability to create new orders refills at a rate of "
               "1 order every 36 seconds.",
         value="300/3h; refill 1 per 36 s", unit="orders per account",
         what="New orders (certificate requests) per account"),
    dict(id="le_identifiers_per_cert", src="le_rate_limits",
         quote="A single certificate can include up to 100 identifiers (DNS "
               "names or IP addresses) depending on the certificate profile "
               "selected.",
         value="100", unit="identifiers per certificate (max)",
         what="Names per certificate"),
    dict(id="le_certs_per_regdomain", src="le_rate_limits",
         quote="Up to 50 certificates can be issued per registered domain (or "
               "IPv4 address, or IPv6 /64 range) every 7 days.",
         value="50/7d", unit="certificates per registered domain",
         what="Certificates per registered domain (global, all accounts)"),
    dict(id="le_certs_per_regdomain_refill", src="le_rate_limits",
         quote="refills at a rate of 1 certificate every 202 minutes",
         value="1 per 202 min", unit="refill",
         what="Sustained rate of the per-registered-domain limit"),
    dict(id="le_uses_psl", src="le_rate_limits",
         quote="We use the Public Suffix List to identify registered domains.",
         value="PSL", unit="", what="How LE defines a registered domain"),
    dict(id="le_exact_set", src="le_rate_limits",
         quote="Up to 5 certificates can be issued per exact same set of "
               "identifiers every 7 days.",
         value="5/7d", unit="certificates per identical name set",
         what="Duplicate-certificate limit"),
    dict(id="le_neworder_per_ip", src="le_rate_limits",
         quote="| /acme/new-order | 300 | 200",
         value="300 req/s, burst 200", unit="requests per IP",
         what="Overall new-order request limit per IP address"),
    dict(id="le_ari_exempt", src="le_rate_limits",
         quote="Renewals coordinated by ARI offer the unique benefit of being "
               "exempt from all rate limits.",
         value="exempt", unit="", what="ARI renewals and rate limits"),
    dict(id="le_points_to_ct", src="le_rate_limits",
         quote="You can get a list of certificates issued for your registered "
               "domain by searching crt.sh or Censys, which use the public "
               "Certificate Transparency logs.",
         value="", unit="", what="Issued names are enumerable from CT"),
    # ---------------- Let's Encrypt profiles --------------------------------
    dict(id="le_profiles_updated", src="le_profiles",
         quote="Last updated: September 8, 2026", value="2026-09-08",
         unit="date", what="Date stamp of the profiles page"),
    dict(id="le_shortlived_6ish", src="le_profiles",
         quote="the resulting certificate is only valid for 6ish days",
         value="~6 days", unit="validity", what="shortlived profile"),
    dict(id="le_shortlived_160h", src="le_profiles",
         quote="| Validity Period | 160 hours",
         value="160", unit="hours", what="shortlived validity"),
    dict(id="le_shortlived_ip", src="le_profiles",
         quote="| Identifier Types | DNS, IP",
         value="DNS, IP", unit="", what="shortlived allows IP identifiers"),
    dict(id="le_classic_90d", src="le_profiles",
         quote="| Validity Period | 90 days", value="90", unit="days",
         what="classic (default) validity"),
    dict(id="le_classic_100names", src="le_profiles",
         quote="| Max Names | 100", value="100", unit="names",
         what="classic profile max names per certificate"),
    dict(id="le_tlsserver_25names", src="le_profiles",
         quote="| Max Names | 25", value="25", unit="names",
         what="tlsserver/shortlived max names per certificate"),
    dict(id="le_br_validity", src="le_profiles",
         quote="The Baseline Requirements require this period not to exceed "
               "200 days; the limit falls to 100 days for certificates issued "
               "from March 15, 2027, and to 47 days from March 15, 2029.",
         value="200 d now; 100 d from 2027-03-15; 47 d from 2029-03-15",
         unit="max validity", what="CA/B Forum validity schedule"),
    # ---------------- Let's Encrypt CT, challenges, blog --------------------
    dict(id="le_logs_everything", src="le_ct_logs",
         quote="Let's Encrypt submits all certificates we issue to CT logs.",
         value="all", unit="", what="LE logs every certificate"),
    dict(id="le_operates_static_logs", src="le_ct_logs",
         quote="Let's Encrypt currently operates static-ct logs based on "
               "Sunlight.", value="", unit="", what="LE CT log software"),
    dict(id="le_dns01_wildcard", src="le_challenge_types",
         quote="It also allows you to issue wildcard certificates.",
         value="DNS-01", unit="", what="Wildcards need DNS-01"),
    dict(id="le_http01_no_wildcard", src="le_challenge_types",
         quote="This challenge cannot be used to issue wildcard certificates.",
         value="", unit="", what="HTTP-01 cannot issue wildcards"),
    dict(id="le_6day_ga", src="le_blog_6day_ga",
         quote="Short-lived and IP address certificates are now generally "
               "available from Let's Encrypt. These certificates are valid "
               "for 160 hours, just over six days.",
         value="2026-01-15", unit="GA date",
         what="6-day and IP certificates generally available"),
    dict(id="le_ip_must_be_short", src="le_blog_6day_ga",
         quote="IP address certificates must be short-lived certificates",
         value="", unit="", what="IP certificates are 160 h only"),
    dict(id="le_250_per_day_ok", src="le_blog_rl_45",
         quote="The 250 new certificates daily will still be well under our "
               "New Orders per Account limit of 300 per three hours.",
         value="250/day", unit="new-name certificates",
         what="LE's own example of a sustained new-name issuance rate"),
    dict(id="le_renewals_exempt", src="le_blog_rl_45",
         quote="Our rate limits affect issuance for new domain names (or "
               "groups of domain names), but renewals are exempt.",
         value="", unit="", what="Renewals are exempt"),
    dict(id="le_45_day_2028", src="le_blog_90_45",
         quote="February 16, 2028: We will further update the classic "
               "profile to issue 45-day certificates with a 7 hour "
               "authorization reuse period.",
         value="2028-02-16", unit="", what="Default lifetime falls to 45 d"),
    dict(id="le_sunlight_zero_mmd", src="le_blog_sunlight",
         quote="they always completely incorporate newly-submitted "
               "certificates before returning an SCT to the submitter, so the "
               "effective merge delay is zero!",
         value="0", unit="s", what="Sunlight logs: no merge delay"),
    dict(id="le_sunlight_all_certs", src="le_blog_sunlight",
         quote="We've been logging all of our own issued certificates, which "
               "represent a majority of the total volume of all "
               "publicly-trusted certificates, into our Sunlight logs.",
         value="", unit="", what="LE certs go to its Sunlight logs (2025)"),
    # ---------------- Google Trust Services (Certificate Manager) -----------
    dict(id="gts_quota_updated", src="gts_quotas",
         quote="Last updated 2026-10-01 UTC.", value="2026-10-01",
         unit="date", what="Date stamp of the GTS quotas page"),
    dict(id="gts_per_project", src="gts_quotas",
         quote="Certificate Manager applies quotas at the Google Cloud "
               "project level.", value="per project", unit="",
         what="Scope of Public CA quotas"),
    dict(id="gts_neworder", src="gts_quotas",
         quote="(newOrder) | 100 per hour", value="100/h",
         unit="orders per project", what="Public CA new orders"),
    dict(id="gts_newaccount", src="gts_quotas",
         quote="(newAccount) | 25 per minute, 100 per hour",
         value="25/min, 100/h", unit="ACME accounts per project",
         what="Public CA account creation"),
    dict(id="gts_newauthz", src="gts_quotas",
         quote="(newAuthz) | 300 per hour", value="300/h",
         unit="authorizations per project", what="Public CA authorizations"),
    dict(id="gts_eab", src="gts_public_ca",
         quote="Your ACME client must support external account binding (EAB) "
               "to work with Public CA.", value="EAB", unit="",
         what="GTS needs a Google Cloud project and EAB"),
    dict(id="gts_free", src="gts_pricing",
         quote="Certificates issued by the Public CA feature of Certificate "
               "Manager are free of charge.", value="0", unit="USD",
         what="GTS certificates are free"),
    # ---------------- ZeroSSL -----------------------------------------------
    dict(id="zerossl_unlimited", src="zerossl_acme",
         quote="you will be able to generate an unlimited amount of 90-day "
               "SSL certificates at no charge, also supporting multi-domain "
               "certificates and wildcards.",
         value="unlimited, 0 USD", unit="", what="ZeroSSL ACME terms"),
    dict(id="zerossl_eab_cap", src="zerossl_acme",
         quote="EAB credentials are limited to a maximum per user/per day.",
         value="unpublished cap", unit="", what="ZeroSSL EAB cap"),
    dict(id="zerossl_abuse", src="zerossl_acme",
         quote="malicious users can be limited or even blocked.",
         value="", unit="", what="ZeroSSL abuse clause"),
    # ---------------- Porkbun registrar API ---------------------------------
    dict(id="pb_verify", src="porkbun_llms_domain",
         quote="Account email and phone must be verified",
         value="", unit="", what="Registration via API needs verification"),
    dict(id="pb_min_duration", src="porkbun_llms_domain",
         quote="Registrations are always for the registry-minimum duration "
               "(usually 1 year).", value="1", unit="year",
         what="API registrations are 1-year"),
    dict(id="pb_attempt_limit", src="porkbun_llms_domain",
         quote="Attempt limit (default: 1 attempt per second per account)",
         value="1/s", unit="attempts per account", what="Registration attempts"),
    dict(id="pb_success_limit", src="porkbun_llms_domain",
         quote="Success limit (default: 1000 successful registrations per "
               "86400 seconds per account)",
         value="1000/day", unit="registrations per account",
         what="Successful registrations per day (default, configurable)"),
    dict(id="pb_spend_default", src="porkbun_spend_limits",
         quote="An account that has not set a limit gets **$100 a month** for "
               "each.", value="100", unit="USD per month",
         what="Default API spend cap (raisable by the account holder)"),
    # ---------------- Certificate Transparency policy -----------------------
    dict(id="chrome_ct_required", src="chrome_ct_policy",
         quote="In CT-enforcing versions of Chrome, all publicly-trusted TLS "
               "certificates are required to be CT Compliant to successfully "
               "validate.", value="", unit="",
         what="Chrome rejects publicly trusted certs without SCTs"),
    dict(id="chrome_two_scts", src="chrome_ct_policy",
         quote="| <= 180 days | 2 |", value="2", unit="SCTs",
         what="Embedded SCTs needed for certificates of <= 180 days"),
    dict(id="chrome_mmd_caps", src="chrome_log_policy",
         quote="static-ct-api logs must not specify a MMD greater than 1 "
               "minute and RFC 6962 logs must not specify a MMD greater than "
               "4 hour.", value="60 s / 4 h", unit="max MMD for applicants",
         what="Chrome log policy MMD caps for logs applying for inclusion"),
    dict(id="chrome_incorporate_mmd", src="chrome_log_policy",
         quote="Incorporate a certificate for which an SCT has been issued by "
               "the log within the MMD.", value="", unit="",
         what="Logs must publish within their MMD"),
    dict(id="apple_ct_required", src="apple_ct_policy",
         quote="Publicly trusted Transport Layer Security (TLS) server "
               "authentication certificates must meet Apple's Certificate "
               "Transparency (CT) policy to be evaluated as trusted on Apple "
               "platforms.", value="", unit="",
         what="Apple platforms require CT"),
    dict(id="rfc6962_mmd", src="rfc6962",
         quote="The log MUST incorporate a certificate in its Merkle Tree "
               "within the Maximum Merge Delay period after the issuance of "
               "the SCT.", value="", unit="", what="RFC 6962 MMD definition"),
    dict(id="rfc6962_precert", src="rfc6962",
         quote="certificate authorities may submit a certificate to logs prior "
               "to issuance.",
         value="", unit="", what="Precertificates are logged before issuance"),
    dict(id="static_null_mmd", src="static_ct_api",
         quote="Note that by design this encourages a null Merge Delay, since "
               "entries must be sequenced before an SCT is returned",
         value="0", unit="s", what="Static CT API: sequenced before SCT"),
    dict(id="rfc9525_one_label", src="rfc9525",
         quote="A wildcard in a presented identifier can only match one label "
               "in a reference identifier.", value="1", unit="label",
         what="Wildcard covers exactly one label"),
    # ---------------- Literature --------------------------------------------
    dict(id="scheitle_dns_73s_3min", src="arxiv_scheitle2018",
         quote="we see the first DNS queries for corresponding domain names "
               "after 73 seconds to ≈3 minutes",
         value="73 s to ~3 min", unit="", what="CT honeypot (IMC 2018)"),
    dict(id="scheitle_11_names", src="arxiv_scheitle2018",
         quote="In 3 batches, we create 11 honeypot subdomains over 18 days.",
         value="11", unit="names", what="Honeypot sample size"),
    dict(id="gfwatch_daily_zones", src="arxiv_gfwatch2021",
         quote="which we refresh on a daily basis", value="daily", unit="",
         what="GFWatch zone files refreshed daily"),
    dict(id="gfwatch_411m", src="arxiv_gfwatch2021",
         quote="with an average of 411M domains daily tested.",
         value="411M", unit="domains per day", what="GFWatch test volume"),
    # ---------------- Zone files and NRD feeds ------------------------------
    dict(id="ra_once_per_24h", src="icann_base_ra",
         quote="no more than once per 24 hour period",
         value="24", unit="h", what="CZDS users may download once per 24 h"),
    dict(id="ra_icann_daily", src="icann_base_ra",
         quote="Access will be provided at least daily. Zone files will "
               "include SRS data committed as close as possible to 00:00:00 "
               "UTC.", value="daily, ~00:00 UTC", unit="",
         what="Zone-file snapshot cadence"),
    dict(id="zfa_daily", src="icann_zfa",
         quote="Registry operators must provide to ICANN bulk access to the "
               "zone files of the Generic Top Level Domain (gTLD) at least on "
               "a daily basis.", value="daily", unit="",
         what="gTLD zone files at least daily"),
    dict(id="zfa_active_names", src="icann_zfa",
         quote="a zone file contains information about domain names that are "
               "active in that gTLD.", value="", unit="",
         what="Zone files list active names"),
    dict(id="ra_def_net_adds_1", src="icann_base_ra",
         quote="number of domains successfully registered (i.e., not in EPP "
               "pendingCreate status) with an initial term of one (1) year "
               "(and not deleted within the add grace period).",
         value="", unit="", what="Definition of net-adds-1-yr"),
    dict(id="ra_def_net_renews_1", src="icann_base_ra",
         quote="number of domains successfully renewed (i.e., not in EPP "
               "pendingRenew status) either automatically or by command with a "
               "new renewal period of one (1) year",
         value="", unit="", what="Definition of net-renews-1-yr"),
    dict(id="ra_def_deleted_nograce", src="icann_base_ra",
         quote="domains deleted outside the add grace period",
         value="", unit="", what="Definition of deleted-domains-nograce"),
    dict(id="whoisds_next_day", src="whoisds_nrd",
         quote="| 2026-10-02 [Only Domains, No Whois Data] | 70000 | "
               "2026-10-03 |", value="D+1", unit="",
         what="Free NRD list for day D is created on day D+1 (70,000 names)"),
    dict(id="whoisds_reuse", src="whoisds_nrd",
         quote="they may be reused, including for commercial purposes, "
               "without a license and without any payment.",
         value="", unit="", what="WhoisDS free-list terms"),
    dict(id="zonestream_ct_nrd", src="openintel_zonestream",
         quote="Newly registered domain names extracted from CT Logs.",
         value="real time", unit="", what="OpenINTEL Zonestream topic"),
    # ---------------- Platforms ---------------------------------------------
    dict(id="gh_one_site", src="gh_pages_limits",
         quote="You can only create one user or organization site for each "
               "account on GitHub.", value="1", unit="host per account",
         what="GitHub Pages: one <owner>.github.io per account"),
    dict(id="gh_default_location", src="gh_pages_about",
         quote="| Default site location | http(s)://<owner>.github.io | "
               "http(s)://<owner>.github.io/<repositoryname>",
         value="<owner>.github.io", unit="",
         what="Project sites share the owner's hostname"),
    dict(id="gh_free_public_only", src="gh_pages_about",
         quote="GitHub Pages is available in public repositories with GitHub "
               "Free and GitHub Free for organizations",
         value="", unit="", what="Free plan Pages needs a public repo"),
    dict(id="gh_https_auto", src="gh_pages_https",
         quote="GitHub Pages sites created after June 15, 2016, and using "
               "github.io domains are served over HTTPS automatically.",
         value="", unit="", what="github.io HTTPS without per-site action"),
    dict(id="gh_custom_le", src="gh_pages_https",
         quote="GitHub queues a job to request a TLS certificate from Let's "
               "Encrypt.", value="", unit="",
         what="Custom-domain Pages sites get per-name LE certificates"),
    dict(id="gh_tos_one_free", src="gh_tos",
         quote="One person or legal entity may maintain no more than one free "
               "Account", value="1", unit="free account per person",
         what="GitHub ToS"),
    dict(id="gh_tos_no_bots", src="gh_tos",
         quote="Accounts registered by \"bots\" or other automated methods are "
               "not permitted.", value="", unit="", what="GitHub ToS"),
    dict(id="gh_createevent_repo", src="gh_event_types",
         quote="Can be either branch, tag, or repository.",
         value="", unit="", what="CreateEvent covers repository creation"),
    dict(id="gh_events_latency", src="gh_events_api",
         quote="Depending on the time of day, event latency can be anywhere "
               "from 30s to 6h.", value="30 s to 6 h", unit="",
         what="Public events API latency"),
    dict(id="gharchive_hourly", src="gharchive",
         quote="These events are aggregated into hourly archives",
         value="1", unit="h", what="GH Archive cadence"),
    dict(id="cf_workers_per_account", src="cf_workers_limits",
         quote="| Workers per account | 100 |", value="100 (Free), 500 (Paid)",
         unit="Workers per account", what="Cloudflare Workers"),
    dict(id="cf_workers_dev_format", src="cf_workers_dev",
         quote="workers.dev subdomains take the format: "
               "<YOUR_ACCOUNT_SUBDOMAIN>.workers.dev.",
         value="", unit="", what="One workers.dev subdomain per account"),
    dict(id="cf_worker_route_format", src="cf_workers_dev",
         quote="<YOUR_WORKER_NAME>.<YOUR_SUBDOMAIN>.workers.dev",
         value="two labels", unit="", what="Worker hostnames are two-level"),
    dict(id="cf_pages_100_projects", src="cf_pages_limits",
         quote="Cloudflare Pages has a limit of 100 projects",
         value="100", unit="projects per account", what="Cloudflare Pages"),
    dict(id="cf_pages_48h", src="cf_pages_limits",
         quote="Cloudflare limits the number of new Pages projects you can "
               "create within your first 48 hours of using the service.",
         value="", unit="", what="New-account throttle"),
    dict(id="cf_pages_preview_format", src="cf_pages_preview",
         quote="<hash>.<project>.pages.dev", value="two labels", unit="",
         what="Pages preview hostnames are two-level"),
    dict(id="cf_pages_unlimited_previews", src="cf_pages_limits",
         quote="You can have an unlimited number of preview deployments "
               "active on your project at a time.", value="unlimited",
         unit="", what="Preview deployments"),
    dict(id="vercel_projects", src="vercel_limits",
         quote="| Projects | 200 | Unlimited | Unlimited |",
         value="200 (Hobby)", unit="projects", what="Vercel"),
    dict(id="vercel_deploys_day", src="vercel_limits",
         quote="You are able to deploy `100` times every `86400` seconds "
               "(1 day).", value="100/day (Hobby)", unit="deployments",
         what="Vercel Hobby deployments per day"),
    dict(id="vercel_url_format", src="vercel_urls",
         quote="<project-name>-<unique-hash>-<scope-slug>.vercel.app",
         value="one label", unit="", what="Vercel deployment URL"),
    dict(id="netlify_instant", src="netlify_https",
         quote="When you create a new site on Netlify, it's instantly secured "
               "at the Netlify-generated URL",
         value="", unit="", what="netlify.app sites need no per-site issuance"),
    dict(id="netlify_custom_le", src="netlify_https",
         quote="If you add a custom domain, we will automatically provision a "
               "certificate with Let's Encrypt", value="", unit="",
         what="Custom domains get per-name LE certificates"),
    dict(id="firebase_36_sites", src="firebase_multisites",
         quote="The multisite feature supports a maximum of 36 sites per "
               "Firebase project.", value="36", unit="sites per project",
         what="Firebase Hosting"),
    dict(id="firebase_default_domains", src="firebase_multisites",
         quote="SITE_ID.web.app", value="", unit="",
         what="Firebase default domain"),
    dict(id="firebase_preview_format", src="firebase_preview",
         quote="PROJECT_ID--CHANNEL_ID-RANDOM_HASH.web.app",
         value="one label", unit="", what="Firebase preview channel URL"),
    dict(id="deno_org_domain", src="deno_domains",
         quote="an organization with the slug acme-inc would have a default "
               "domain of acme-inc.deno.net.", value="", unit="",
         what="Deno Deploy default domain"),
    dict(id="deno_app_two_level", src="deno_domains",
         quote="my-app.acme-inc.deno.net", value="two labels", unit="",
         what="Deno Deploy app hostnames are two-level"),
    dict(id="deno_cert_90s", src="deno_domains",
         quote="This process can take up to 90 seconds.", value="90", unit="s",
         what="Let's Encrypt provisioning time for a custom domain"),
    dict(id="fly_default", src="fly_custom_domain",
         quote="When you create a Fly App, it is automatically given a "
               "fly.dev subdomain, based on the app's name.",
         value="", unit="", what="Fly.io default hostname"),
    dict(id="fly_no_free_tier", src="fly_pricing",
         quote="New organizations don't have a free tier or a monthly free "
               "usage allowance.", value="", unit="", what="Fly.io pricing"),
    dict(id="fly_card", src="fly_pricing",
         quote="All organizations (except for Linked Organizations) require a "
               "credit card on file.", value="", unit="", what="Fly.io"),
    dict(id="render_subdomain", src="render_web",
         quote="Every Render web service gets a unique onrender.com subdomain",
         value="", unit="", what="Render default hostname"),
    dict(id="render_tls", src="render_tls",
         quote="You get free TLS certificates for the onrender.com subdomain "
               "for your service", value="", unit="", what="Render TLS"),
    dict(id="render_750h", src="render_free",
         quote="Render grants 750 Free instance hours to each workspace per "
               "calendar month", value="750", unit="h per workspace-month",
         what="Render free tier"),
    dict(id="aws_url_format", src="aws_lambda_urls",
         quote="https://<url-id>.lambda-url.<region>.on.aws",
         value="", unit="", what="Lambda function URL format"),
    dict(id="azure_unique_format", src="azure_unique_hostname",
         quote="<AppName>-<Hash>.<Region>.azurewebsites.net",
         value="", unit="", what="Azure secure unique default hostname"),
    dict(id="azure_noreuse", src="azure_unique_hostname",
         quote="Unique hash every time. Maximum isolation.",
         value="", unit="", what="NoReuse scope"),
    dict(id="gcr_deterministic_format", src="gcr_https",
         quote="https://[TAG---]SERVICE_NAME-PROJECT_NUMBER.REGION.run.app",
         value="", unit="", what="Cloud Run deterministic URL"),
    dict(id="gcr_1000_services", src="gcr_quotas",
         quote="| Maximum number of services | 1000 | per project and region",
         value="1000", unit="services per project and region",
         what="Cloud Run"),
    # ---------------- Pinned / non-WebPKI deployments -----------------------
    dict(id="tor_nonwebpki_pinning", src="tor_blog_2025",
         quote="safe non-WebPKI certificate support with certificate-chain "
               "pinning", value="", unit="",
         what="WebTunnel supports pinned non-WebPKI certificates (Dec 2025)"),
    dict(id="tor_ru_listing", src="tor_blog_2025",
         quote="in June, the Russian censors began listing most of our "
               "WebTunnel bridges", value="", unit="",
         what="Russia listed most WebTunnel bridges (2025)"),
    dict(id="tor_wt_requires_domain", src="tor_webtunnel_setup",
         quote="a domain under your control", value="", unit="",
         what="WebTunnel bridge needs an operator domain"),
    dict(id="tor_wt_requires_cert", src="tor_webtunnel_setup",
         quote="A valid TLS certificate;", value="", unit="",
         what="WebTunnel bridge needs a TLS certificate (ACME in the guide)"),
    # ---------------- LE registered-domain computation (source code) --------
    dict(id="boulder_psl_domain", src="boulder_ratelimits_utilities",
         quote="domain, err := publicsuffix.Domain(ident.Value)",
         value="", unit="", what="LE rate-limit key is the PSL eTLD+1"),
    dict(id="pslgo_private_included", src="pslgo_publicsuffix",
         quote="var DefaultFindOptions = &FindOptions{IgnorePrivate: false, "
               "DefaultRule: DefaultRule}", value="", unit="",
         what="publicsuffix.Domain includes PRIVATE-section rules"),
    # ---------------- Free plans, CZDS access, SCT embedding -----------------
    dict(id="vercel_free_deploys", src="vercel_limits",
         quote="Deployments per day (Free). | `api-deployments-free-per-day` "
               "| 100 | 86400", value="100/day", unit="deployments (Free)",
         what="Vercel free (Hobby) plan deployment rate limit"),
    dict(id="cf_pages_free_plan", src="cf_pages_limits",
         quote="Below are limits observed by the Cloudflare Free plan.",
         value="", unit="", what="Pages limits are those of the Free plan"),
    dict(id="firebase_no_cost", src="firebase_quotas",
         quote="Storage for your Hosting content is at no cost up to 10 GB.",
         value="10", unit="GB at no cost", what="Firebase Hosting no-cost tier"),
    dict(id="deno_free_plan", src="deno_pricing",
         quote="Free $0/month For personal use and smaller projects",
         value="0", unit="USD/month", what="Deno Deploy Free plan"),
    dict(id="deno_free_10_apps", src="deno_pricing",
         quote="Total number of deployments that can be active at any given "
               "time in your organization | 10 |", value="10",
         unit="active apps (Free)", what="Deno Deploy Free plan app limit"),
    dict(id="render_free_services", src="render_free",
         quote="Preview the Render platform with free web services and "
               "datastores.", value="", unit="", what="Render free tier"),
    dict(id="azure_free_10_apps", src="azure_limits",
         quote="apps per azure app service plan1 | 10 | 100 |",
         value="10 (Free), 100 (Shared)", unit="apps per plan",
         what="Azure App Service Free tier"),
    dict(id="netlify_free_certs", src="netlify_https",
         quote="Netlify-managed certificates are offered to all Netlify sites "
               "for free.", value="0", unit="USD", what="Netlify certificates"),
    dict(id="zfa_agreement", src="icann_zfa",
         quote="electronically sign the agreement via ICANN Centralized Zone "
               "Data Service (CZDS)", value="", unit="",
         what="Zone-file access needs a signed agreement (CZDS)"),
    dict(id="zfa_deny", src="icann_zfa",
         quote="Under certain circumstances a Registry Operator may deny or "
               "revoke access.", value="", unit="", what="CZDS access can be "
         "denied"),
    dict(id="le_embeds_scts", src="le_blog_sunlight",
         quote="we'll begin including SCTs from these logs in our own "
               "certificates (alongside SCTs from traditional CT logs)",
         value="", unit="", what="LE embeds SCTs from its own and other logs"),
    dict(id="chrome_embed_scts", src="chrome_ct_policy",
         quote="Most TLS servers do not support the TLS extension, so CAs "
               "should be prepared to embed SCTs into issued certificates",
         value="", unit="", what="SCTs are embedded at issuance"),
    dict(id="gh_event_repo_name", src="gh_event_types",
         quote="The name of the repository, which includes the owner and "
               "repository name.", value="", unit="",
         what="Every public event names the repository owner"),
    dict(id="gfwatch_sld_only", src="arxiv_gfwatch2021",
         quote="Since TLD zone files contain only second-level domains "
               "(SLDs), they do not allow us to observe cases in which the GFW "
               "censors subdomains of these SLDs.", value="", unit="",
         what="TLD zone files list second-level names only"),
    dict(id="le_free", src="le_rate_limits",
         quote="Let's Encrypt is a free, automated, and open Certificate "
               "Authority", value="0", unit="USD", what="LE certificates "
         "are free"),
    dict(id="rfc9162_mmd_no_limit", src="rfc9162",
         quote="This document deliberately does not specify any limits on "
               "the value to allow for experimentation.", value="", unit="",
         what="RFC 9162 leaves the MMD to log policy (browsers set it)"),
    dict(id="vercel_hash_9", src="vercel_urls",
         quote="9 randomly generated numbers and letters", value="9",
         unit="characters", what="Vercel unique-hash component"),
]
