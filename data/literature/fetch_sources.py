#!/usr/bin/env python3
"""
fetch_sources.py -- download the open-access sources of the literature parameters
(params_spec.py) into raw/ and record provenance in raw/manifest.json.

This script only downloads published papers, one public GitHub issue page and
five publisher or arXiv web pages that document titles, versions and licenses.
It never contacts any measurement target, endpoint, or blocked name.

Usage:  python3 fetch_sources.py            # download anything missing
        python3 fetch_sources.py --force    # re-download everything

A file that exists and is listed in raw/manifest.json is kept. Every file it
downloads gets a new manifest entry (URL, retrieval time, sha256, size), and
the script prints whether the new sha256 matches the entry it replaces.

Requests are paced (>= 3 s apart). Each file is size-checked against a hard
cap (1.5 GB per file; the largest source here is about 21 MB).
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
MANIFEST = os.path.join(RAW, "manifest.json")
UA = "Mozilla/5.0 (X11; Linux x86_64) literature-calibration (no measurements)"
PACE_S = 3.0
MAX_BYTES = int(1.5e9)

# key: short source key used in derived/params_table.csv
# bibkey: a short citation key of the work ('-' for evidence pages); the 14 works
#         that the paper cites use their keys in its bibliography
# license: as stated on the PDF / publisher page (checked by hand, see SOURCES.md)
SOURCES = [
    dict(key="ensafi2015imc", bibkey="gfw_hidden",
         title="Examining How the Great Firewall Discovers Hidden Circumvention Servers",
         venue="ACM IMC 2015", url="https://conferences2.sigcomm.org/imc/2015/papers/p445.pdf",
         file="ensafi2015imc_gfw_hidden_servers.pdf",
         license="ACM notice on p.1 ('Copyright is held by the owner/author(s). Publication rights licensed to ACM'); copy hosted by the IMC 2015 site. Quote briefly with citation; do not redistribute."),
    dict(key="ensafi2015popets", bibkey="gfw_space_time",
         title="Analyzing the Great Firewall of China Over Space and Time",
         venue="PoPETs 2015(1)", url="https://petsymposium.org/popets/2015/popets-2015-0005.pdf",
         file="ensafi2015popets_gfw_space_time.pdf",
         license='No license statement printed in the PDF; freely available from petsymposium.org (PoPETs open access). Quote briefly with citation; do not redistribute.'),
    dict(key="alice2020imc", bibkey="gfw_shadowsocks",
         title="How China Detects and Blocks Shadowsocks",
         venue="ACM IMC 2020", url="https://gfw.report/publications/imc20/data/paper/shadowsocks.pdf",
         file="alice2020imc_shadowsocks.pdf",
         license="Author-posted copy (gfw.report). ACM notice on p.1 ('(c) 2020 Copyright held by the owner/author(s). Publication rights licensed to ACM'). Quote briefly with citation; do not redistribute."),
    dict(key="dunna2018foci", bibkey="unpublished_bridges",
         title="Analyzing China's Blocking of Unpublished Tor Bridges",
         venue="USENIX FOCI 2018", url="https://www.usenix.org/system/files/conference/foci18/foci18-paper-dunna.pdf",
         file="dunna2018foci_unpublished_bridges.pdf",
         license='No license statement in the PDF; USENIX open-access proceedings. Quote briefly with citation; do not redistribute.'),
    dict(key="fifield2016foci", bibkey="censors_delay",
         title="Censors' Delay in Blocking Circumvention Proxies",
         venue="USENIX FOCI 2016", url="https://www.usenix.org/system/files/conference/foci16/foci16-paper-fifield.pdf",
         file="fifield2016foci_censors_delay.pdf",
         license='No license statement in the PDF; USENIX open-access proceedings. Quote briefly with citation; do not redistribute.'),
    dict(key="fifield2017arxiv", bibkey="censor_detection",
         title="Detecting Censor Detection",
         venue="arXiv:1709.08718v1 (2017)", url="https://arxiv.org/pdf/1709.08718v1",
         file="fifield2017arxiv_detecting_censor_detection.pdf",
         license='CC0 1.0 public domain dedication (license link on the arXiv abs page). Cite when quoting.'),
    dict(key="wu2023usenix", bibkey="gfw_fullyencrypted",
         title="How the Great Firewall of China Detects and Blocks Fully Encrypted Traffic",
         venue="USENIX Security 2023", url="https://www.usenix.org/system/files/usenixsecurity23-wu-mingshi.pdf",
         file="wu2023usenix_fully_encrypted.pdf",
         license="USENIX open access ('Open access to the Proceedings ... is sponsored by USENIX', p.1). Quote briefly with citation; do not redistribute."),
    dict(key="bock2020foci", bibkey="iran_whitelister",
         title="Detecting and Evading Censorship-in-Depth: A Case Study of Iran's Protocol Whitelister",
         venue="USENIX FOCI 2020", url="https://www.usenix.org/system/files/foci20-paper-bock.pdf",
         file="bock2020foci_iran_whitelister.pdf",
         license='No license statement in the PDF; USENIX open-access proceedings. Quote briefly with citation; do not redistribute.'),
    dict(key="xue2022imc", bibkey="tspu",
         title="TSPU: Russia's Decentralized Censorship System",
         venue="ACM IMC 2022", url="https://censoredplanet.org/assets/tspu-imc22.pdf",
         file="xue2022imc_tspu.pdf",
         license="Author-posted copy (censoredplanet.org). ACM notice on p.1 ('(c) 2022 Copyright held by the owner/author(s)'). Quote briefly with citation; do not redistribute."),
    dict(key="zohaib2025usenix", bibkey="gfw_quic",
         title="Exposing and Circumventing SNI-based QUIC Censorship of the Great Firewall of China",
         venue="USENIX Security 2025", url="https://www.usenix.org/system/files/usenixsecurity25-zohaib.pdf",
         file="zohaib2025usenix_quic_sni.pdf",
         license='USENIX open access (p.1 notice). Quote briefly with citation; do not redistribute.'),
    dict(key="heitmann2026foci", bibkey="russia_quic_sni",
         title="On Russia's Early Introduction of QUIC SNI Censorship",
         venue="FOCI 2026(2)", url="https://petsymposium.org/foci/2026/foci-2026-0010.pdf",
         file="heitmann2026foci_russia_quic_sni.pdf",
         license='CC BY 4.0 (p.1 notice and FOCI article page).'),
    dict(key="wu2025sp", bibkey="wall_behind_wall",
         title="A Wall Behind A Wall: Emerging Regional Censorship in China",
         venue="IEEE S&P 2025", url="https://gfw.report/publications/sp25/data/paper/paper.pdf",
         file="wu2025sp_wall_behind_wall.pdf",
         license='Author-posted copy (gfw.report); no license statement in the PDF. Quote briefly with citation; do not redistribute (GFW Report material: cite, do not redistribute).'),
    dict(key="bocovich2024usenix", bibkey="snowflake",
         title="Snowflake, a censorship circumvention system using temporary WebRTC proxies",
         venue="USENIX Security 2024", url="https://www.usenix.org/system/files/usenixsecurity24-bocovich.pdf",
         file="bocovich2024usenix_snowflake.pdf",
         license='USENIX open access (p.1 notice). Quote briefly with citation; do not redistribute.'),
    dict(key="chen2026arxiv", bibkey="snowflake_enumeration",
         title="Evaluating Practical Enumeration and Blocking Attacks on the Snowflake Circumvention System",
         venue="arXiv:2609.12242v2 (accepted to ACM CCS 2026)", url="https://arxiv.org/pdf/2609.12242v2",
         file="chen2026arxiv_snowflake_enumeration.pdf",
         license="arXiv non-exclusive distribution license 1.0 (abs page); the PDF states CC BY 4.0 for the CCS'26 version. Quote with citation."),
    dict(key="hoang2021usenix", bibkey="gfwatch",
         title="How Great is the Great Firewall? Measuring China's DNS Censorship",
         venue="USENIX Security 2021", url="https://www.usenix.org/system/files/sec21-hoang.pdf",
         file="hoang2021usenix_gfwatch.pdf",
         license='USENIX open access (p.1 notice). Quote briefly with citation; do not redistribute.'),
    dict(key="nasr2019ndss", bibkey="nasr_enemy_gateways",
         title="Enemy At the Gateways: Censorship-Resilient Proxy Distribution Using Game Theory",
         venue="NDSS 2019", url="https://www.ndss-symposium.org/wp-content/uploads/2019/02/ndss2019_11-2_Nasr_paper.pdf",
         file="nasr2019ndss_enemy_gateways.pdf",
         license='NDSS open-access proceedings (Internet Society); no license text found on p.1. Quote briefly with citation; do not redistribute.'),
    dict(key="fares2026foci", bibkey="fares_game_changed",
         title="The Game Has Changed: Revisiting proxy distribution and game theory",
         venue="FOCI 2026(1), pp. 14-22", url="https://petsymposium.org/foci/2026/foci-2026-0003.pdf",
         file="fares2026foci_game_has_changed.pdf",
         license='CC BY 4.0 (p.1 notice).'),
    dict(key="winter2012foci", bibkey="gfw_blocking_tor",
         title="How the Great Firewall of China is Blocking Tor",
         venue="USENIX FOCI 2012", url="https://www.usenix.org/system/files/conference/foci12/foci12-final2.pdf",
         file="winter2012foci_gfw_blocking_tor.pdf",
         license='No license statement in the PDF; USENIX open-access proceedings. Quote briefly with citation; do not redistribute.'),
    dict(key="bbs111", bibkey="n4p_issue111",
         title="net4people/bbs issue #111: Outline server is not accessible by certain time after connecting by client in Russia",
         venue="GitHub issue (field report), opened 2022-03-27",
         url="https://github.com/net4people/bbs/issues/111",
         file="net4people_bbs_issue111.html",
         license='User-generated GitHub content with no explicit license (GitHub Terms of Service). Quote briefly with attribution as a field report; do not redistribute.'),
    # --- evidence pages (existence, licence, issue listing); not parameter sources
    dict(key="arxiv_abs_1709", bibkey="-", title="arXiv abstract page for 1709.08718v1 (licence evidence)",
         venue="arXiv", url="https://arxiv.org/abs/1709.08718v1", file="arxiv_abs_1709.08718v1.html",
         license="arXiv page; cite."),
    dict(key="arxiv_abs_2609", bibkey="-", title="arXiv abstract page for 2609.12242v2 (existence, licence, CCS comment)",
         venue="arXiv", url="https://arxiv.org/abs/2609.12242v2", file="arxiv_abs_2609.12242v2.html",
         license="arXiv page; cite."),
    dict(key="foci2026_index", bibkey="-", title="FOCI 2026 proceedings index (issue 1 and 2 listings)",
         venue="petsymposium.org", url="https://petsymposium.org/foci/2026/", file="foci2026_index.html",
         license="Publisher page; cite."),
    dict(key="foci2026_0010_page", bibkey="-", title="FOCI 2026 article page for Heitmann et al. (pages 1-6, CC BY 4.0)",
         venue="petsymposium.org", url="https://petsymposium.org/foci/2026/foci-2026-0010.php",
         file="foci2026_0010_article.html", license="Publisher page; article CC BY 4.0."),
    dict(key="usenix_foci20_bock_page", bibkey="-", title="USENIX FOCI'20 presentation page for Bock et al. (official title)",
         venue="usenix.org", url="https://www.usenix.org/conference/foci20/presentation/bock",
         file="usenix_foci20_bock_page.html", license="Publisher page; cite."),
]


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            return json.load(f)
    return {"description": "Provenance of raw files for data/literature (see SOURCES.md).",
            "files": {}}


def fetch(src, sess):
    dest = os.path.join(RAW, src["file"])
    r = sess.get(src["url"], stream=True, timeout=120, allow_redirects=True)
    status = r.status_code
    clen = int(r.headers.get("Content-Length") or 0)
    if clen > MAX_BYTES:
        r.close()
        raise RuntimeError(f"{src['key']}: Content-Length {clen} exceeds cap; not downloaded")
    total = 0
    tmp = dest + ".part"
    with open(tmp, "wb") as f:
        for chunk in r.iter_content(1 << 16):
            total += len(chunk)
            if total > MAX_BYTES:
                f.close()
                os.remove(tmp)
                raise RuntimeError(f"{src['key']}: exceeded size cap while streaming")
            f.write(chunk)
    if status != 200:
        os.remove(tmp)
        raise RuntimeError(f"{src['key']}: HTTP {status}")
    os.replace(tmp, dest)
    return dict(final_url=r.url, http_status=status,
                content_type=r.headers.get("Content-Type", ""))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true",
                    help="download every file again, including files that raw/ already has")
    force = ap.parse_args().force
    os.makedirs(RAW, exist_ok=True)
    man = load_manifest()
    sess = requests.Session()
    sess.headers["User-Agent"] = UA
    first = True
    for src in SOURCES:
        dest = os.path.join(RAW, src["file"])
        if os.path.exists(dest) and not force and src["file"] in man["files"]:
            # refresh descriptive metadata only; keep retrieval time and hash
            man["files"][src["file"]].update(
                key=src["key"], bibkey=src["bibkey"], title=src["title"],
                venue=src["venue"], license=src["license"])
            print("have", src["file"])
            continue
        if not first:
            time.sleep(PACE_S)
        first = False
        t = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
        info = fetch(src, sess)
        entry = dict(key=src["key"], bibkey=src["bibkey"], title=src["title"],
                     venue=src["venue"], url=src["url"], retrieved_utc=t,
                     sha256=sha256_of(dest), size_bytes=os.path.getsize(dest),
                     license=src["license"], **info)
        old = man["files"].get(src["file"], {}).get("sha256")
        same = "" if old is None else ("  same sha256 as before" if old == entry["sha256"]
                                       else "  sha256 differs from the replaced entry")
        man["files"][src["file"]] = entry
        print(f"got  {src['file']}  {entry['size_bytes']} B  {entry['sha256'][:12]}{same}")
        with open(MANIFEST, "w") as f:
            json.dump(man, f, indent=2, sort_keys=True)
    with open(MANIFEST, "w") as f:
        json.dump(man, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
