<div align="center">

<img src="assets/favicon.png" width="96" height="96" alt="Inspector Rabbit Logo"/>

# 🐇 Inspector Rabbit

### Advanced Open Source Intelligence Suite

![Version](https://img.shields.io/badge/version-1.0.0-00f5ff?style=flat-square&labelColor=010409)
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

Inspector Rabbit packs **14 OSINT modules** into a single elegant dark-themed desktop application:

| Module | Description |
|--------|-------------|
| 👤 **Username Hunt** | Search 100+ social platforms simultaneously (Sherlock-style) |
| 🌐 **Domain Intelligence** | WHOIS · DNS · SSL · headers · tech fingerprinting · subdomain enumeration |
| ✉️ **Email OSINT** | Validation · SMTP verify · Gravatar · HIBP breach check · pattern generation |
| 🔍 **Google Dorks** | 60+ dork templates · DuckDuckGo/Bing execution · category browsing |
| 🖥️ **IP Intelligence** | Geolocation · reverse DNS · blacklist/RBL check · port scan · Shodan · RDAP |
| 📞 **Phone OSINT** | Validation · carrier · country · formats · direct search links |
| 🔐 **Certificate Transparency** | crt.sh CT log search · subdomain discovery via SSL certs · issuer timeline |
| 📄 **Metadata Extractor** | EXIF from images · GPS coordinates · PDF/DOCX author data |
| 📋 **Paste & Leak Scanner** | GitHub · HackerNews · Reddit · Pastebin — exposed credential search |
| 🕷️ **Web Crawler** | Recursive site spidering · email/phone/social link extraction |
| 🕸️ **Network Graph** | Maltego-style force-directed graph visualization · drag · zoom · export |
| 📅 **Investigation Timeline** | Chronological event log · auto-captures all findings · manual notes |
| 📊 **Report Export** | HTML · JSON · PDF export of all findings |
| ⚙️ **Settings** | API key management (Shodan, HIBP) · scan parameters |

---

## 🚀 Installation

### Option 1: .deb Package (Recommended for Ubuntu/Debian)

```bash
# Download the latest release
wget https://github.com/paulmmoore3416/inspector-rabbit/releases/latest/download/inspector-rabbit_1.0.0_amd64.deb

# Install
sudo dpkg -i inspector-rabbit_1.0.0_amd64.deb

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

### Option 3: Build .deb Locally

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

```
PyQt6 >= 6.4.0
requests >= 2.28.0
aiohttp >= 3.8.0
python-whois >= 0.8.0
dnspython >= 2.3.0
shodan >= 1.28.0
beautifulsoup4 >= 4.11.0
lxml >= 4.9.0
reportlab >= 3.6.0
Pillow >= 9.4.0
networkx >= 3.0
matplotlib >= 3.6.0
cryptography >= 39.0.0
pyOpenSSL >= 23.0.0
phonenumbers >= 8.13.0
pypdf >= 3.0.0
```

---

## 🔑 Optional API Keys

Some modules work better with API keys (all optional — app functions without them):

| Service | Module | Get Key |
|---------|--------|---------|
| **Shodan** | IP Intel, Domain | [account.shodan.io](https://account.shodan.io) |
| **HaveIBeenPwned** | Email OSINT | [haveibeenpwned.com/API/Key](https://haveibeenpwned.com/API/Key) |

Configure in **Settings** (⚙️ sidebar) — keys stored locally in `~/.inspector_rabbit_settings.json`.

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

1. **Username Reconnaissance**: Enter a username → click *Hunt* → results appear in real-time across 100+ platforms
2. **Domain Analysis**: Enter `example.com` → DNS, WHOIS, SSL, subdomains, tech stack all collected automatically
3. **Graph It**: Any result has a *Send to Graph* button — build relationship maps between targets
4. **Search Pastes**: Enter an email/username → scans GitHub gists, Reddit, HackerNews, Pastebin for leaks
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
