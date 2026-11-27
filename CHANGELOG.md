# Changelog

All notable changes to Inspector Rabbit are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.6.0] — 2026-11-26

Accuracy and reliability release. Every module was audited against live
services. Anything that faked, guessed or silently dropped data was fixed or removed.

### Added
- **Network privacy layer** (`src/modules/net.py`): route every lookup through Tor
  (service or Tor Browser) or a custom SOCKS5/HTTP proxy. Includes a **kill switch**
  that refuses to send traffic when the proxy is down, DNS-over-HTTPS through the
  proxy (no resolver leaks), SOCKS-tunnelled TCP for SSL/banner/port checks, and a
  guard that blocks unproxyable traffic (ping, traceroute, SMTP, port-43 WHOIS)
  unless allowed. Settings → Network Privacy has a **Test connection** button showing
  the exit IP and whether it is a Tor exit.
- **Hardened container** (`run-container.sh`, `container/`): rootless Podman,
  read-only root filesystem, all capabilities dropped, no host home directory,
  Wayland-only display, a container-private Tor client, and Tor + kill switch on by default.
- `docs/SECURITY.md`: OPSEC guide covering Tor, Tailscale exit nodes, the container and a dedicated VM.
- New free data sources: XposedOrNot breach analytics, Shodan InternetDB, RDAP
  (registration, IP ownership and abuse contacts for all RIRs), Cert Spotter fallback,
  ipwho.is fallback, Gravatar profiles, and Bluesky, Mastodon, GitLab, Keybase, HackerNews,
  DEV, Chess.com, Lichess and Docker Hub profile APIs.
- Optional API keys: GitHub token, Intelligence X, URLScan, Brave Search, Google Programmable Search.
- Domain Intel: SPF/DMARC assessment, security-header audit, TLS trust and expiry
  status, a technology fingerprint built from page bodies, and wildcard-DNS-aware subdomain discovery.
- Metadata: EXIF/GPS from PNG/WebP/TIFF/HEIC (previously JPEG only), PDF XMP,
  DOCX/XLSX/PPTX author/company/editing-time metadata, and SHA-256/MD5 of every file.
- Evidence capture: resolved server IP, TLS verification state, redirect chain,
  proxy route, and a `SHA256SUMS` manifest (`sha256sum -c` compatible).
- Tests: `tests/test_offline.py` (25 unit tests) and `tests/gui_smoke.py` (drives every page end-to-end),
  plus a GitHub Actions workflow that runs the offline tests on every push.
- `tools/build_sites.py`: regenerates and live-validates the username site database.

### Fixed — false or fake results
- Username Hunt: 101 of 102 sites used plain HTTP-status checks, so Instagram,
  TikTok, Twitter and others reported **every** username as found. Replaced with 268 Sherlock-derived
  rules, each live-validated (real account found twice, three random names not found).
  Hits are re-confirmed at scan time, and blocked or rate-limited responses are shown as BLOCKED, never as not found.
- Social Profiles: Twitter/X, TikTok and Instagram "URL only" results were counted as
  found profiles. They are now labelled *unverified (manual check)*. The Twitch check counted
  every username as found.
- IP blacklists: Spamhaus's "public resolver" refusal (127.255.255.x) was reported as
  LISTED. SORBS (shut down) was removed.
- DNS Leak Monitor: raised a HIGH "DNS spoofing" alert every 15 s because example.com's IP
  changed in 2025. Now uses fixed-anycast canaries, discovers systemd-resolved upstreams,
  detects NXDOMAIN hijacking, and recognises Tailscale MagicDNS.
- Connection Guard / Scan Detector: every outbound connection was treated as inbound, so
  the app's own lookups were flagged as port scans. Inbound now means "to a listening port".
- Dorks: DuckDuckGo bot challenges showed as "0 results", and Bing serves unrelated filler
  results to scrapers. Results are now checked against `site:`/`filetype:`/`inurl:`
  operators and off-target results are discarded and reported.
- Breach Aggregator: HIBP's domain endpoint (breaches *of* a site) was presented as
  breaches of the email. Severity was based on breach size rather than exposed data. "Email addresses" no longer counts as medium severity.
- Email: catch-all servers reported every address as valid, null-MX domains were treated as
  deliverable, and the disposable list had 30 entries (now 10,000+ from a maintained list).
- Web Crawler: the phone regex matched dates and IDs (libphonenumber validation is now used),
  `mailto:`/`tel:` links were ignored, share/intent links counted as social profiles, and
  the depth limit counted against the page budget.
- Batch Processor: the username check used HTTP 200 = found and the phone check guessed
  from prefixes. Batch mode now runs the same logic as the individual modules.
- HTML reports inserted scraped data unescaped, so a page title could inject script into the report.

### Fixed — crashes and broken features
- Paste Scanner: the module emitted objects while the UI expected dicts, so it crashed on the first
  result. Pushshift and psbdmp are offline. GitHub code search silently returned nothing without a token.
- Metadata Extractor: URL fetches crashed (a dataclass was emitted on a dict signal).
- Phone and email-pattern lookups could abort the app ("QThread destroyed while running").
- API keys were only applied after pressing Save. Saved keys were ignored at startup.
- Dark Web: Ahmia now requires a form token (it always returned 0 results). DarkSearch and
  psbdmp are offline, the hard-coded fake IntelX "test-key" was removed, and grep.app needs a browser challenge.
- Domain Intel: Shodan list fields were never displayed, technology detection never saw the
  page body, WHOIS/SSL errors were hidden, and WHOIS failed for many TLDs (RDAP is now primary).
- Certificate Transparency: crt.sh 502s were fatal (it now retries, then falls back to Cert Spotter).
  The "include expired" option did nothing, and out-of-scope SAN names were included.
- Network Diagnostics: Linux-only ping/traceroute flags, so the Windows build couldn't run them. The SSH banner was corrupted by probing
  before reading.
- Report timestamps were labelled UTC but used local time.
- **Timeline infinite loop**: the Timeline page's own status messages were logged back
  into the Timeline. Every status update recursed until RecursionError (possible crash)
  and filled `~/.inspector_rabbit_timeline.json` with ~500 junk events.
- Counter-surveillance terminal rendered relayed text as HTML (now escaped).
- `INSPECTOR_RABBIT_HOME` relocates all app data (used by the container and the tests).

### Security
- Settings file (API keys) is written atomically with `0600` permissions. Case and evidence directories are `0700`.
- No more blanket `verify=False`: TLS is verified first, and any fallback is recorded.

### Removed
- Unused dependencies: aiohttp, googlesearch-python, colorama, tqdm, socid-extractor,
  networkx, pyOpenSSL. Added PySocks, phonenumbers and pypdf, which the app needs.

---

## [1.4.0] — 2026-03-20

### Added — 9 New Modules (5 community-requested + 4 enhancements)

**Research-backed community requests:**
- **🖼️ Reverse Image Search** — Load from URL or file, EXIF/GPS preview, launch Google Lens · TinEye · Yandex · Bing Visual Search
- **💀 Breach Aggregator** — Multi-source credential exposure: HIBP · LeakCheck · BreachDirectory with severity scoring
- **👥 Social Profile OSINT** — GitHub · Reddit public APIs + profile links for Twitter/X · Instagram · TikTok · YouTube · Twitch
- **🗺️ GeoIP Map Tracker** — Batch-resolve IPs via ip-api.com, plot on dark world-map scatter chart with ISP/org data
- **🌑 Dark Web Monitor** — Search Ahmia · Intelligence X · psbdmp · DarkSearch for target exposure and risk scoring

**Recommended enhancements:**
- **🔬 Evidence Capture** — SHA-256/MD5 page archiving, headers, JSON evidence bundles in `~/.inspector_rabbit_evidence/`
- **🔌 Network Diagnostics** — Ping · traceroute · port banner grab · rDNS · service fingerprinting in live terminal output
- **📦 Batch Processor** — Upload CSV of targets, run any OSINT module in bulk, aggregate results with export
- **📂 Case Manager** — Full investigation lifecycle: create/notes/status/findings, PDF/JSON export

### Changed
- NAV_ITEMS expanded from 15 → 24 pages (sidebar scrolls)
- Dashboard: v1.4.0 · 24 Modules, 9 new feature cards added
- `MODULE_ACCENTS` in `components.py` updated with 9 new accent colours
- Signal wiring (`status_message`, `send_to_graph`, `apply_settings`) extended to all new pages
- Version bumped to 1.4.0 throughout

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
