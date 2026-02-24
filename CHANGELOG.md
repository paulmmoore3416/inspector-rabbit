# Changelog

All notable changes to Inspector Rabbit are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-02-24

### 🚀 Initial Release

#### Core OSINT Modules
- **Username Hunt** — Async username search across 100+ social platforms (Sherlock-compatible sites.json)
- **Domain Intelligence** — WHOIS, DNS (8 record types), SSL certificate analysis, HTTP headers, tech fingerprinting, subdomain enumeration (60+ common subdomains), robots.txt, Shodan integration
- **Email OSINT** — MX validation, SMTP banner grabbing, Gravatar lookup, HaveIBeenPwned breach check, email pattern generator
- **Google Dorks Engine** — 60+ dork templates across 6 categories, DuckDuckGo and Bing execution, configurable delays
- **Web Crawler** — Recursive website spider, email/phone/social link extraction, configurable depth/page limits

#### New in 1.0.0 — Extended Intelligence Suite
- **IP Intelligence** — Geolocation via ip-api.com, reverse DNS, RBL/blacklist checks against 8 servers, port scan (18 common ports with banner grabbing), Shodan query, RDAP abuse contact lookup
- **Phone OSINT** — International phone validation using `phonenumbers` library, carrier/country/timezone detection, all format variants, direct search engine links
- **Certificate Transparency** — crt.sh JSON API integration for CT log search, subdomain discovery via SAN entries, issuer analysis, chronological certificate timeline
- **Metadata Extractor** — EXIF extraction from images (JPEG, PNG, TIFF, GIF), GPS coordinate detection with Google Maps integration, PDF metadata (title, author, creator, dates), pypdf integration
- **Paste & Leak Scanner** — Multi-source paste search: GitHub gists/code/repos, HackerNews (Algolia API), Reddit (Pushshift), Pastebin (psbdmp.ws), risk classification (high/medium/low)
- **Investigation Timeline** — Chronological event log auto-capturing all scans, manual note entry, filter by event type, JSON/TXT export, session statistics

#### GUI & Visualization
- Dark cyberpunk theme (`#0d1117` background, `#00f5ff` cyan, `#7c3aed` purple accents)
- Animated boot splash screen with matrix rain, pulsing glow, loading progress bar
- Maltego-style force-directed network graph (custom Fruchterman-Reingold physics, 60fps)
- Interactive graph: drag nodes, scroll to zoom, F to fit, right-click context menu, PNG export
- Scrollable sidebar with 14 navigation items
- Real-time status bar and investigation timeline auto-capture
- Navigate menu for keyboard-friendly page switching

#### Package & Distribution
- `.deb` package for Ubuntu/Debian (amd64)
- Desktop entry for application menu integration
- User-local install option (no sudo required)
- Animated rabbit GIF mascot and favicon (PNG + ICO)

### Dependencies Added
- `phonenumbers` — phone number parsing and validation
- `pypdf` — PDF metadata extraction
- All other deps: PyQt6, requests, aiohttp, python-whois, dnspython, shodan, beautifulsoup4, lxml, reportlab, Pillow, networkx, matplotlib, cryptography, pyOpenSSL

---

## [Unreleased]

### Planned
- Dark web Tor `.onion` search integration
- OSINT workflow automation / playbooks
- Collaborative investigation sharing (encrypted export)
- Whois history timeline
- More paste sources (GitLab snippets, PrivateBin)
- Username check for additional 50+ platforms
- Map visualization for geolocation results
- Plugin/extension API for custom modules
