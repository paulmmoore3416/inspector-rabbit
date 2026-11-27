<div align="center">

<img src="assets/favicon.png" width="96" height="96" alt="Inspector Rabbit Logo"/>

# 🐇 Inspector Rabbit

### Advanced Open Source Intelligence Suite

![Version](https://img.shields.io/badge/version-1.6.0-00f5ff?style=flat-square&labelColor=010409)
![Python](https://img.shields.io/badge/python-3.9%2B-00f5ff?style=flat-square&labelColor=010409&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-6.x-7c3aed?style=flat-square&labelColor=010409)
![Platform](https://img.shields.io/badge/platform-Linux-3fb950?style=flat-square&labelColor=010409)
![License](https://img.shields.io/badge/license-MIT-ffa657?style=flat-square&labelColor=010409)
![Education](https://img.shields.io/badge/use-educational%20%26%20authorized%20only-f85149?style=flat-square&labelColor=010409)

<img src="assets/rabbit_running.gif" alt="Inspector Rabbit in action" width="400"/>

*Combining the power of Sherlock · Maltego · SpiderFoot · Shodan · Recon-ng · Google Dorks*

---

</div>

## ✨ Features

Inspector Rabbit packs **24 OSINT and counter-surveillance modules** into one dark-themed desktop app.
Every data source was live-tested for v1.6.0. When a source is blocked, rate-limited or needs a key, the app says so instead of guessing.

| Module | What it really does |
|--------|---------------------|
| 👤 **Username Hunt** | 260+ sites with Sherlock-derived rules, each **live-validated** (real account found, random names not found). Hits are re-confirmed before they're reported |
| 🌐 **Domain Intelligence** | RDAP/WHOIS · DNS + SPF/DMARC · TLS trust & expiry · security headers · tech fingerprint · wildcard-aware subdomains · Shodan/InternetDB |
| ✉️ **Email OSINT** | RFC validation · MX/null-MX · 10k-entry disposable list · SMTP probe with catch-all detection · Gravatar profile · XposedOrNot + HIBP breaches |
| 🔍 **Google Dorks** | 60+ templates · Brave/Google APIs or Bing/DDG · off-target results discarded |
| 🖥️ **IP Intelligence** | Geo (ip-api/ipwho.is) · RDAP owner & abuse contacts (all RIRs) · DNSBLs (refusals ≠ listings) · TCP ports · Shodan/InternetDB · IPv6 |
| 📞 **Phone OSINT** | libphonenumber validation · carrier · region · type · timezones · lookup links |
| 🔐 **Certificate Transparency** | crt.sh with retries → Cert Spotter fallback · in-scope subdomains · issuers · expiry |
| 📄 **Metadata Extractor** | EXIF/GPS (JPEG/PNG/WebP/TIFF/HEIC) · PDF info + XMP · DOCX/XLSX/PPTX authors · file hashes |
| 📋 **Paste & Leak Scanner** | GitHub code/repos/commits · HackerNews · Pastebin & Reddit via dork engine |
| 💀 **Breach Aggregator** | HIBP · XposedOrNot · LeakCheck. Severity comes from the data exposed |
| 👥 **Social Profiles** | Real profile data from 13 public APIs. Login-walled sites are marked *unverified* |
| 🌑 **Dark Web** | Ahmia Tor index · Intelligence X · paste sites · GitHub code leaks · URLScan |
| 🕷️ **Web Crawler** | robots-aware spider · validated emails/phones · social links |
| 🗺️ **GeoIP Map** · 🔬 **Evidence Capture** · 🔌 **Net Diagnostics** · 📦 **Batch** · 📂 **Cases** · 🕸️ **Graph** · 📅 **Timeline** | Investigation workflow, SHA-256 evidence manifests, bulk processing |
| 🛡️ **Counter-Surveillance** | Connection guard · scan detector · traffic monitor · DNS leak/hijack monitor (Tailscale-aware) |
| 🧅 **Network Privacy** | Tor / SOCKS / HTTP proxy for every lookup · **kill switch** · DNS-over-HTTPS when proxied |

---

## 🚀 Installation

### Option 1: .deb Package (Recommended for Ubuntu/Debian)

```bash
# Download the latest release
wget https://github.com/paulmmoore3416/inspector-rabbit/releases/latest/download/inspector-rabbit_1.6.0_amd64.deb

# Install
sudo dpkg -i inspector-rabbit_1.6.0_amd64.deb

# Launch
inspector-rabbit
```

### Option 2: Run from Source

```bash
# Clone the repository
git clone https://github.com/paulmmoore3416/inspector-rabbit.git
cd inspector-rabbit

# Install Python dependencies
pip3 install -r requirements.txt

# Launch
python3 inspector_rabbit.py
```

### Option 3: Hardened Container (rootless Podman + built-in Tor)

```bash
sudo apt install podman
./run-container.sh
```

Read-only filesystem, no capabilities, no access to your home directory, and Tor plus the kill switch on by default.
See [`docs/SECURITY.md`](docs/SECURITY.md).

### Option 4: Build .deb Locally

```bash
git clone https://github.com/paulmmoore3416/inspector-rabbit.git
cd inspector-rabbit
chmod +x build_deb.sh
./build_deb.sh
```

---

## 📋 Requirements

- **OS**: Ubuntu 22.04+ / Debian 11+ (or any modern Linux)
- **Python**: 3.9+
- **Dependencies**: See [`requirements.txt`](requirements.txt)

Install with `pip3 install -r requirements.txt`. Key packages: PyQt6, requests + PySocks, dnspython, python-whois, phonenumbers, Pillow, pypdf, cryptography, beautifulsoup4/lxml, reportlab, matplotlib, psutil.

---

## 🔑 Optional API Keys

Some modules work better with API keys (all optional — app functions without them):

| Service | Module | Get Key |
|---------|--------|---------|
| **Shodan** | IP Intel, Domain (free InternetDB used without a key) | [account.shodan.io](https://account.shodan.io) |
| **HaveIBeenPwned** | Email, Breach (XposedOrNot used without a key) | [haveibeenpwned.com/API/Key](https://haveibeenpwned.com/API/Key) |
| **GitHub token** | Paste scanner and Dark Web code search | [github.com/settings/tokens](https://github.com/settings/personal-access-tokens) |
| **Intelligence X** | Dark Web | [intelx.io](https://intelx.io/account?tab=developer) |
| **Brave Search / Google PSE** | Dorks, paste-site search | [brave.com/search/api](https://brave.com/search/api/) · [Google PSE](https://developers.google.com/custom-search/v1/introduction) |
| **URLScan.io** | Dark Web (higher limits) | [urlscan.io](https://urlscan.io/user/profile/) |

Configure keys in **Settings** (⚙️ sidebar). They're stored locally in `~/.inspector_rabbit_settings.json` with owner-only (`0600`) permissions and are never committed.

## 🧅 Privacy & OPSEC

Without a proxy, every lookup reveals your real IP to the target. Set **Settings → Network Privacy → Tor + Kill switch** and press **Test connection**.
[`docs/SECURITY.md`](docs/SECURITY.md) covers Tor, Tailscale exit nodes, the hardened container and VM setups.

## 🧪 Tests

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q tests/test_offline.py   # offline unit tests
QT_QPA_PLATFORM=offscreen python tests/gui_smoke.py                    # live end-to-end run of every page
```

---

## 📸 Screenshots

<table>
<tr>
<td align="center"><b>🏠 Dashboard</b></td>
<td align="center"><b>👤 Username Hunt</b></td>
</tr>
<tr>
<td align="center"><b>🕸️ Network Graph</b></td>
<td align="center"><b>🌐 Domain Intel</b></td>
</tr>
<tr>
<td align="center"><b>📅 Timeline</b></td>
<td align="center"><b>🔐 Cert Transparency</b></td>
</tr>
</table>

---

## 🏗️ Project Structure

```
inspector-rabbit/
├── inspector_rabbit.py          # Entry point + animated splash
├── build_deb.sh                 # .deb package builder
├── requirements.txt             # Python dependencies
├── assets/
│   ├── favicon.png              # Application icon
│   ├── favicon.ico              # Windows-compatible icon
│   └── rabbit_running.gif       # Animated mascot
└── src/
    ├── gui/                     # PyQt6 UI widgets
    │   ├── main_window.py       # Main window + sidebar
    │   ├── styles.py            # Dark cyberpunk QSS theme
    │   ├── dashboard_widget.py
    │   ├── username_widget.py
    │   ├── domain_widget.py
    │   ├── email_widget.py
    │   ├── dorks_widget.py
    │   ├── ip_widget.py
    │   ├── phone_widget.py
    │   ├── cert_widget.py
    │   ├── metadata_widget.py
    │   ├── paste_widget.py
    │   ├── crawler_widget.py
    │   ├── graph_widget.py
    │   ├── timeline_widget.py
    │   └── settings_widget.py
    ├── modules/                 # OSINT backend logic
    │   ├── username_checker.py
    │   ├── domain_intel.py
    │   ├── email_osint.py
    │   ├── dorks_engine.py
    │   ├── web_crawler.py
    │   ├── ip_intel.py
    │   ├── phone_osint.py
    │   ├── cert_transparency.py
    │   ├── metadata_extractor.py
    │   ├── paste_scanner.py
    │   └── report_generator.py
    └── data/
        ├── sites.json           # 100+ sites for username checking
        └── dorks_templates.json # 60+ Google Dork templates
```

---

## ⚡ Quick Start Guide

1. **Username Reconnaissance**: Enter a username → click *Hunt* → results appear in real time across 260+ verified sites
2. **Domain Analysis**: Enter `example.com` → DNS, WHOIS, SSL, subdomains, tech stack all collected automatically
3. **Graph It**: Any result has a *Send to Graph* button — build relationship maps between targets
4. **Search Pastes**: Enter an email/username → scans GitHub code/repos/commits, HackerNews, Pastebin and Reddit for leaks
5. **Track Progress**: The Timeline tab auto-captures every scan you run for case management

---

## 🔒 Legal & Ethics

> **⚠️ For educational and authorized security research only.**
>
> Inspector Rabbit is designed for:
> - Authorized penetration testing and security assessments
> - Security awareness education and training
> - Research on your own infrastructure
> - CTF (Capture The Flag) competitions
>
> **Never use Inspector Rabbit against systems you don't own or don't have explicit written permission to test. Unauthorized use may be illegal.**

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-module`
3. Commit your changes: `git commit -m 'Add new OSINT module'`
4. Push to the branch: `git push origin feature/new-module`
5. Open a Pull Request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Made with 🐇 + Python + PyQt6

*Inspired by: [Sherlock](https://github.com/sherlock-project/sherlock) · [Maltego](https://www.maltego.com/) · [SpiderFoot](https://github.com/smicallef/spiderfoot) · [Shodan](https://www.shodan.io/) · [Recon-ng](https://github.com/lanmaster53/recon-ng)*

</div>
