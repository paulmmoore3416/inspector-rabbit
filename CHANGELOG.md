# Changelog

All notable changes to Inspector Rabbit are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.3.0] — 2026-03-02

### Changed — Dashboard Redesign + Page Visual Identity

- **Dashboard** — complete visual overhaul:
  - `HeroBanner` — custom `paintEvent()` with dot-grid background (26px spacing, 22-alpha cyan), corner HUD brackets, top-right radial glow, and a gradient cyan border line along the bottom
  - `StatCard` — redesigned with coloured left-stripe accent per stat (3px border-left in module colour), bold icon + value layout, uppercase muted label
  - `FeatureCard` — redesigned with per-module top-border accent (3px border-top), icon+title header row, improved action button styling
  - Section labels — now inline accented: 3px cyan block + uppercase muted text
- **Per-module page headers** — all 14 OSINT module pages now have a distinct coloured accent:
  - Each topbar uses `apply_page_header_style(bar, accent_color)` from the new `components.py`
  - Dark horizontal gradient background (`#0e1824 → #060b14`) with a 4px left-border stripe and matching bottom border in the module's accent colour
  - Username: cyan · Domain: purple · Email: green · Dorks: orange · IP: red · Phone: sky · Cert: amber · Metadata: orange · Pastes: pink · Crawler: blue · Graph: pink · Timeline: indigo · Counter Sur: danger-red · Settings: grey
- **`src/gui/components.py`** (new) — `MODULE_ACCENTS` dict and `apply_page_header_style()` shared utility
- **Global stylesheet** (`styles.py`) — refreshed across the board:
  - Underline-style tabs (no box border, 2px bottom accent on selected)
  - Slimmer scrollbars (6px, transparent track)
  - Darker card backgrounds (`#0d1117`) for better contrast
  - Tighter table alternating rows, darker headers
  - Improved button hover/press states
  - Sidebar: dimmer inactive icons, thinner active stripe
- Version bumped to 1.3.0 throughout

---

## [1.2.0] — 2026-02-24

### Added — Counter Surveillance Suite

- **Counter Surveillance Monitor** — new 🛡️ split-screen page with 4 defensive modules:
  - **Connection Guard** (`connection_guard.py`) — real-time TCP/UDP monitoring via psutil, inbound probe detection, port-scan heuristics (3+ ports in 8s = scan), suspicious outbound port alerts, one-click kill-switch using `ss -K` with process-level fallback
  - **Traffic Monitor** (`traffic_monitor.py`) — 1Hz psutil I/O sampling, rolling 120-sample history, spike anomaly detection (4× baseline = alert), tracks bytes/packets in+out per second
  - **Scan Detector** (`scan_detector.py`) — detects if external hosts are port-scanning or flooding the local machine; classifies sequential_scan, port_scan, host_probe, syn_flood by connection-state analysis
  - **DNS Leak Monitor** (`dns_leak_monitor.py`) — watches `/etc/resolv.conf` for tampering, validates canary domains against expected IPs, flags slow DNS responses (>2s = proxy suspected), alerts on unknown resolvers
- **Split-screen GUI** — left: terminal-style green-on-black scan activity log; right: tabbed threat panel (Threats · Connections · Scanners · DNS Checks); bottom: live matplotlib graphs for traffic I/O and scan attempts
- **Real-time metrics graphs** — embedded matplotlib: traffic bytes/sec with fill + scan attempt count history
- **⚡ Kill Connection button** — select any connection row and kill it; confirmation dialog prevents accidents
- All OSINT module activity auto-relayed to Counter Surveillance terminal via `status_message` signals
- Dashboard card added for Counter Surveillance with navigation
- Version bumped to 1.2.0 throughout

### Changed

- `requirements.txt` — added `psutil>=5.9.0`
- Stat card updated: 14 → 15+ OSINT modules
- Dashboard subtitle reflects new module count

---

## [1.1.0] — 2026-02-24

### Fixed

- **Dashboard navigation** — all 12 feature cards and 6 quick-action buttons now navigate to their respective OSINT module pages when clicked (previously buttons had no signal connections)
- Dashboard card `mousePressEvent` also triggers navigation so clicking anywhere on a card works
- Updated stat cards: "6 OSINT Modules" → "14 OSINT Modules" to reflect all current modules

### Changed

- Dashboard header subtitle now shows correct module count and version
- Added 6 new feature cards to the dashboard grid (IP Intel, Phone, Cert CT, Metadata, Paste Scanner, Timeline)
- Added a **Quick Actions** bar above the disclaimer with one-click shortcuts to key modules
- Sidebar version label updated to v1.1.0

---

## [1.0.0] — 2026-02-24

### Added — Initial Release

#### Core OSINT Modules

- **Username Hunt** — Async username search across 100+ social platforms (Sherlock-compatible sites.json)
- **Domain Intelligence** — WHOIS, DNS (8 record types), SSL certificate analysis, HTTP headers, tech fingerprinting, subdomain enumeration (60+ common subdomains), robots.txt, Shodan integration
- **Email OSINT** — MX validation, SMTP banner grabbing, Gravatar lookup, HaveIBeenPwned breach check, email pattern generator
- **Google Dorks Engine** — 60+ dork templates across 6 categories, DuckDuckGo and Bing execution, configurable delays
- **Web Crawler** — Recursive website spider, email/phone/social link extraction, configurable depth/page limits

#### Extended Intelligence Suite

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

## [1.4.0] — 2026-05-14

### Added

- **Dark Web Search Module** — new 🕵️‍♂️ page for searching onion services:
  - Integrates Ahmia and Phobos public gateways
  - Async multi-gateway search without local Tor proxy requirement
  - Automated onion address extraction and source attribution
  - One-click copy to clipboard for onion links
- **WHOIS History** — enhanced Domain Intelligence:
  - Scrapes IP history and past ownership data from ViewDNS.info
  - New "History" tab in Domain Intelligence results
  - Tracks IP changes, locations, and owners over time
- **Integrated Dashboard** — Dark Web Search added to capabilities and feature grid
- **Enhanced Module Count** — Now featuring 16+ core OSINT modules

## [Unreleased]

### Planned

- OSINT workflow automation / playbooks
- Collaborative investigation sharing (encrypted export)
- More paste sources (GitLab snippets, PrivateBin)
- Username check for additional 50+ platforms
- Map visualization for geolocation results
- Plugin/extension API for custom modules
