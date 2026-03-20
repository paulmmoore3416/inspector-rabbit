"""
Inspector Rabbit - Dark Web / Exposure Lookup Module  v1.5.0

Sources (all free, no Tor required):
  1. Ahmia.fi         — public Tor hidden-service search index
  2. Intelligence X   — leaked-data archive search (free tier)
  3. psbdmp.ws        — Pastebin dump/paste OSINT
  4. DarkSearch.io    — dark-web search engine API
  5. grep.app         — leaked credentials / sensitive data in public GitHub
  6. URLScan.io       — malicious / suspicious page scan history (domain/email)
"""

import re
import time
import warnings
from datetime import datetime, timezone

import requests
import urllib3

# Suppress SSL warnings for dark web endpoints with self-signed/expired certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from bs4 import BeautifulSoup
    _BS4 = True
except ImportError:
    _BS4 = False

from PyQt6.QtCore import QThread, pyqtSignal


BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": BROWSER_UA,
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "application/json, text/html, */*",
}

TIMEOUT_SHORT = 10
TIMEOUT_LONG  = 18


# ── Risk classification ────────────────────────────────────────────────────────

HIGH_KEYWORDS = frozenset({
    "password", "passwd", "credentials", "credential",
    "breach", "breached", "leaked", "leak",
    "hacked", "hack", "exploit",
    "database dump", "db dump", "dump",
    "login", "secret", "token", "api key", "apikey",
    "private key", "passphrase", "cleartext", "plaintext",
    "hash", "md5", "sha1", "sha256",
    "credit card", "ssn", "social security",
    "dox", "doxx", "doxed",
    "combo list", "combolist",
    "account takeover", "stealer", "infostealer",
    "ransomware", "0day", "zero-day", "zero day",
    "malware", "trojan", "keylogger",
})

MEDIUM_KEYWORDS = frozenset({
    "email", "account", "profile", "user", "username",
    "address", "phone", "personal", "data", "information",
    "exposed", "exposure", "leaked user", "discord",
    "database", "records", "sensitive",
    "pii", "personally identifiable", "private",
})


def _assess_risk(title: str, snippet: str = "") -> str:
    """
    Return 'high', 'medium', or 'low'.
    Title keyword matches are weighted higher than snippet matches.
    """
    t = title.lower()
    s = snippet.lower()
    combined = f"{t} {s}"

    # Any high keyword in title → instant high
    for kw in HIGH_KEYWORDS:
        if kw in t:
            return "high"

    # Two or more high keywords anywhere → high
    high_hits = sum(1 for kw in HIGH_KEYWORDS if kw in combined)
    if high_hits >= 2:
        return "high"
    if high_hits >= 1:
        return "medium"

    for kw in MEDIUM_KEYWORDS:
        if kw in combined:
            return "medium"

    return "low"


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _make_result(source: str, title: str, url: str,
                 snippet: str, query: str) -> dict:
    risk = _assess_risk(title, snippet)
    return {
        "source":     source,
        "title":      title[:140],
        "url":        url,
        "snippet":    snippet[:280],
        "risk_level": risk,
        "query":      query,
        "timestamp":  _now_ts(),
    }


# ── Worker thread ──────────────────────────────────────────────────────────────

class DarkWebThread(QThread):
    result_found  = pyqtSignal(dict)   # emitted per result
    source_status = pyqtSignal(str, int, str)  # source_name, count, status
    progress      = pyqtSignal(str)
    done          = pyqtSignal(dict)

    SOURCE_LIST = [
        "Ahmia.fi",
        "Intelligence X",
        "Pastebin (psbdmp)",
        "DarkSearch.io",
        "grep.app (GitHub)",
        "URLScan.io",
    ]

    def __init__(self, query: str, query_type: str,
                 enabled_sources: list[str] | None = None,
                 parent=None):
        super().__init__(parent)
        self._query   = query.strip()
        self._qtype   = query_type.lower()
        self._enabled = set(enabled_sources) if enabled_sources else set(self.SOURCE_LIST)
        self._running = True
        self._results: list[dict] = []

    def stop(self):
        self._running = False

    # ── helpers ────────────────────────────────────────────────────────────────

    def _emit(self, r: dict):
        self._results.append(r)
        self.result_found.emit(r)

    def _stopped(self) -> bool:
        return not self._running

    def _src_enabled(self, name: str) -> bool:
        # Allow partial match for flexibility
        return any(name in s or s in name for s in self._enabled)

    # ── main entry ─────────────────────────────────────────────────────────────

    def run(self):
        """Entry point — wraps _run_impl() so done is always emitted."""
        try:
            self._run_impl()
        except BaseException as exc:
            # Catch anything (including C-level crashes re-raised as Python
            # exceptions) and emit a safe done signal so the UI unlocks.
            try:
                self.progress.emit(f"💥 Fatal scan error: {type(exc).__name__}: {exc}")
                total        = len(self._results)
                high_count   = sum(1 for r in self._results if r["risk_level"] == "high")
                medium_count = sum(1 for r in self._results if r["risk_level"] == "medium")
                low_count    = sum(1 for r in self._results if r["risk_level"] == "low")
                self.done.emit({
                    "total_found":     total,
                    "high_risk":       high_count,
                    "medium_risk":     medium_count,
                    "low_risk":        low_count,
                    "sources_checked": 0,
                    "exposure_score":  high_count * 10 + medium_count * 5 + low_count,
                    "query":           self._query,
                    "query_type":      self._qtype,
                })
            except Exception:
                pass

    def _run_impl(self):
        q = self._query
        self.progress.emit(f"🔍 Starting dark web scan for: {q}")
        self.progress.emit(f"   Query type: {self._qtype}")
        self.progress.emit("")

        checks = [
            ("Ahmia.fi",           self._check_ahmia),
            ("Intelligence X",     self._check_intelx),
            ("Pastebin (psbdmp)",  self._check_psbdmp),
            ("DarkSearch.io",      self._check_darksearch),
            ("grep.app (GitHub)",  self._check_grepapp),
            ("URLScan.io",         self._check_urlscan),
        ]

        sources_checked = 0
        for source_name, fn in checks:
            if self._stopped():
                self.progress.emit("⏹  Scan stopped by user.")
                break
            if not self._src_enabled(source_name):
                self.source_status.emit(source_name, 0, "skipped")
                continue

            try:
                count = fn(q)
                sources_checked += 1
                status = "ok" if count >= 0 else "error"
                self.source_status.emit(source_name, max(count, 0), status)
            except Exception as exc:
                self.progress.emit(f"  ⚠️  {source_name} error: {exc}")
                self.source_status.emit(source_name, 0, "error")

        total        = len(self._results)
        high_count   = sum(1 for r in self._results if r["risk_level"] == "high")
        medium_count = sum(1 for r in self._results if r["risk_level"] == "medium")
        low_count    = sum(1 for r in self._results if r["risk_level"] == "low")
        score        = high_count * 10 + medium_count * 5 + low_count * 1

        self.progress.emit("")
        self.progress.emit(
            f"✅ Scan complete — {total} result(s) from {sources_checked} source(s)"
        )
        self.progress.emit(
            f"   🔴 High: {high_count}  🟡 Medium: {medium_count}  "
            f"🟢 Low: {low_count}  |  Exposure score: {score}"
        )
        self.done.emit({
            "total_found":     total,
            "high_risk":       high_count,
            "medium_risk":     medium_count,
            "low_risk":        low_count,
            "sources_checked": sources_checked,
            "exposure_score":  score,
            "query":           self._query,
            "query_type":      self._qtype,
        })

    # ══════════════════════════════════════════════════════════════════════════
    # Source implementations
    # ══════════════════════════════════════════════════════════════════════════

    # ── 1. Ahmia.fi ────────────────────────────────────────────────────────────

    def _check_ahmia(self, query: str) -> int:
        self.progress.emit("🔎 Ahmia.fi — searching Tor index…")
        if not _BS4:
            self.progress.emit("  ⚠️  beautifulsoup4 not installed")
            return -1

        count = 0
        for page in range(1, 3):       # fetch up to 2 pages
            if self._stopped():
                break
            try:
                params = {"q": query, "page": page}
                resp = requests.get(
                    "https://ahmia.fi/search/",
                    params=params,
                    headers=HEADERS,
                    timeout=TIMEOUT_LONG,
                    verify=False,
                )
                if resp.status_code != 200:
                    self.progress.emit(f"  ↳ Ahmia: HTTP {resp.status_code}")
                    break

                soup  = BeautifulSoup(resp.text, "html.parser")

                # Try multiple selectors — Ahmia sometimes changes its HTML
                items = (
                    soup.select("li.result") or
                    soup.select("div.result") or
                    soup.select("article") or
                    []
                )

                if not items:
                    # Fallback: grab all h4 > a links
                    for link_tag in soup.select("h4 a")[:15]:
                        if self._stopped():
                            break
                        title   = link_tag.get_text(strip=True)
                        href    = link_tag.get("href", "")
                        snippet = ""
                        parent  = link_tag.find_parent()
                        if parent:
                            p_tag = parent.find_next_sibling("p")
                            if p_tag:
                                snippet = p_tag.get_text(strip=True)[:200]
                        if not title:
                            continue
                        r = _make_result("Ahmia.fi", title, href, snippet, query)
                        self._emit(r)
                        count += 1
                    break

                for item in items[:12]:
                    if self._stopped():
                        break
                    title_el   = (item.select_one("h4 a") or
                                  item.select_one("h3 a") or
                                  item.select_one("a"))
                    snippet_el = (item.select_one("p.description") or
                                  item.select_one("p") or
                                  item.select_one(".description"))

                    title   = title_el.get_text(strip=True) if title_el else ""
                    href    = title_el.get("href", "") if title_el else ""
                    snippet = snippet_el.get_text(strip=True)[:200] if snippet_el else ""

                    if not title:
                        continue

                    r = _make_result("Ahmia.fi", title, href, snippet, query)
                    self._emit(r)
                    count += 1

                if len(items) < 5:
                    break           # no more pages worth fetching
                time.sleep(0.8)

            except Exception as exc:
                self.progress.emit(f"  ⚠️  Ahmia page {page} error: {exc}")
                break

        self.progress.emit(f"  ↳ Ahmia.fi → {count} result(s)")
        return count

    # ── 2. Intelligence X ─────────────────────────────────────────────────────

    def _check_intelx(self, query: str) -> int:
        self.progress.emit("🔎 Intelligence X — checking leaked data archive…")

        # Try both the v1 and v2 free endpoints
        endpoints = [
            ("POST", "https://2.intelx.io/intelligent/search",
             {"term": query, "maxresults": 20, "media": 0, "sort": 4, "terminate": []}),
            ("GET",  f"https://intelx.io/api/search/simple?q={requests.utils.quote(query)}&apikey=test-key&limit=20",
             None),
        ]

        count = 0
        for method, url, payload in endpoints:
            if self._stopped():
                break
            try:
                if method == "POST":
                    resp = requests.post(url, json=payload, headers=HEADERS, timeout=TIMEOUT_LONG, verify=False)
                else:
                    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT_LONG, verify=False)

                if resp.status_code not in (200, 201):
                    continue

                data = resp.json()
                records = (
                    data.get("records") or
                    data.get("results") or
                    data.get("items") or
                    (data if isinstance(data, list) else [])
                )

                for rec in records[:20]:
                    if self._stopped():
                        break
                    title   = str(rec.get("name") or rec.get("title") or "")
                    link    = str(rec.get("storageid") or rec.get("url") or "")
                    snippet = rec.get("preview") or rec.get("description") or ""
                    if isinstance(snippet, list):
                        snippet = " ".join(str(s) for s in snippet)
                    snippet = str(snippet)[:280]

                    if not title and not snippet:
                        continue

                    # Build a usable URL when only a storage ID is returned
                    if link and not link.startswith("http"):
                        link = f"https://intelx.io/?did={link}"

                    r = _make_result("Intelligence X", title, link, snippet, query)
                    self._emit(r)
                    count += 1

                if count > 0:
                    break   # got results from this endpoint

            except Exception as exc:
                self.progress.emit(f"  ↳ IntelX endpoint error: {exc}")
                continue

        self.progress.emit(f"  ↳ Intelligence X → {count} result(s)")
        return count

    # ── 3. psbdmp.ws ──────────────────────────────────────────────────────────

    def _check_psbdmp(self, query: str) -> int:
        self.progress.emit("🔎 Pastebin OSINT via psbdmp.ws…")
        count = 0
        try:
            url  = f"https://psbdmp.ws/api/v3/search/{requests.utils.quote(query)}"
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SHORT, verify=False)

            if resp.status_code == 404:
                self.progress.emit("  ↳ psbdmp: no results")
                return 0

            data   = resp.json()
            pastes = data if isinstance(data, list) else data.get("data", [])

            for paste in pastes[:20]:
                if self._stopped():
                    break
                paste_id = paste.get("id", "")
                tags     = paste.get("tags") or paste.get("name") or paste_id or "Untitled paste"
                snippet  = (paste.get("text") or paste.get("content") or "")[:280]
                link     = f"https://pastebin.com/{paste_id}" if paste_id else ""
                size     = paste.get("size") or paste.get("length") or ""

                title = str(tags)
                if size:
                    title += f"  ({size} bytes)"

                r = _make_result("Pastebin (psbdmp)", title, link, snippet, query)
                self._emit(r)
                count += 1

        except Exception as exc:
            self.progress.emit(f"  ⚠️  psbdmp.ws error: {exc}")
            return -1

        self.progress.emit(f"  ↳ psbdmp.ws → {count} result(s)")
        return count

    # ── 4. DarkSearch.io ──────────────────────────────────────────────────────

    def _check_darksearch(self, query: str) -> int:
        self.progress.emit("🔎 DarkSearch.io — dark web index…")
        count = 0
        try:
            # Try page 1 and 2
            for page in range(1, 3):
                if self._stopped():
                    break
                url  = (
                    f"https://darksearch.io/api/search"
                    f"?query={requests.utils.quote(query)}&page={page}"
                )
                resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT_LONG, verify=False)

                if resp.status_code == 429:
                    self.progress.emit("  ↳ DarkSearch: rate limited")
                    break
                if resp.status_code != 200:
                    break

                data  = resp.json()
                items = data.get("data", []) if isinstance(data, dict) else []

                for item in items[:15]:
                    if self._stopped():
                        break
                    title   = str(item.get("title", "") or "")
                    link    = str(item.get("link", "") or item.get("url", "") or "")
                    snippet = str(item.get("description", "") or "")[:280]

                    # Some entries have no useful content
                    if not title and not snippet:
                        continue

                    r = _make_result("DarkSearch.io", title, link, snippet, query)
                    self._emit(r)
                    count += 1

                if len(items) < 5:
                    break
                time.sleep(0.6)

        except Exception as exc:
            self.progress.emit(f"  ⚠️  DarkSearch.io error: {exc}")
            return -1

        self.progress.emit(f"  ↳ DarkSearch.io → {count} result(s)")
        return count

    # ── 5. grep.app — leaked credentials in public GitHub ─────────────────────

    def _check_grepapp(self, query: str) -> int:
        """
        Searches public GitHub repositories for the query string.
        Extremely useful for finding accidentally committed credentials,
        API keys, emails, and passwords in source code.
        """
        self.progress.emit("🔎 grep.app — scanning public GitHub repos for exposed data…")
        count = 0
        try:
            url = "https://grep.app/api/search"
            params = {
                "q":      query,
                "regexp": "false",
                "case":   "false",
                "results": 20,
            }
            resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT_LONG, verify=False)

            if resp.status_code != 200:
                self.progress.emit(f"  ↳ grep.app: HTTP {resp.status_code}")
                return 0

            data  = resp.json()
            hits  = data.get("hits", {}).get("hits", [])

            for hit in hits[:20]:
                if self._stopped():
                    break
                src      = hit.get("_source", {})
                repo_raw = src.get("repo", {}).get("raw", "")
                path_raw = src.get("path", {}).get("raw", "")

                content  = src.get("content", {})
                if isinstance(content, dict):
                    snippet = content.get("snippet", "")
                    # Strip HTML highlight tags from snippet
                    snippet = re.sub(r"</?em>", "", snippet)
                elif isinstance(content, str):
                    snippet = content[:280]
                else:
                    snippet = ""

                title    = f"{repo_raw} / {path_raw}" if repo_raw else path_raw
                link     = (
                    f"https://github.com/{repo_raw}/blob/HEAD/{path_raw}"
                    if repo_raw else ""
                )

                if not title:
                    continue

                r = _make_result("grep.app (GitHub)", title, link, snippet, query)
                # GitHub hits are almost always leaked data → boost to at least medium
                if r["risk_level"] == "low":
                    r["risk_level"] = "medium"
                self._emit(r)
                count += 1

        except Exception as exc:
            self.progress.emit(f"  ⚠️  grep.app error: {exc}")
            return -1

        self.progress.emit(f"  ↳ grep.app → {count} result(s)")
        return count

    # ── 6. URLScan.io — suspicious/malicious scan history ─────────────────────

    def _check_urlscan(self, query: str) -> int:
        """
        URLScan.io indexes pages scanned by researchers.
        Best for domain and email queries — shows historical malicious
        or phishing pages associated with the target.
        """
        self.progress.emit("🔎 URLScan.io — checking scan history for malicious activity…")
        count = 0

        # Only useful for domain and email queries
        if self._qtype not in ("domain", "email", "keyword"):
            self.progress.emit("  ↳ URLScan.io: skipped (use domain/email/keyword query type)")
            return 0

        try:
            # Build a targeted query for URLScan
            if self._qtype == "domain":
                search_q = f"domain:{query}"
            elif self._qtype == "email":
                search_q = query
            else:
                search_q = query

            url    = "https://urlscan.io/api/v1/search/"
            params = {"q": search_q, "size": 20}
            resp   = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT_LONG, verify=False)

            if resp.status_code == 429:
                self.progress.emit("  ↳ URLScan.io: rate limited — try again later")
                return 0
            if resp.status_code != 200:
                self.progress.emit(f"  ↳ URLScan.io: HTTP {resp.status_code}")
                return 0

            data    = resp.json()
            results = data.get("results", [])

            for item in results[:15]:
                if self._stopped():
                    break
                page     = item.get("page", {})
                verdict  = item.get("verdicts", {}).get("overall", {})
                score_v  = item.get("verdicts", {}).get("urlscan", {})

                domain_v  = page.get("domain", "")
                url_link  = page.get("url", "")
                title_v   = page.get("title", "") or domain_v
                country   = page.get("country", "")
                ip_addr   = page.get("ip", "")
                malicious = verdict.get("malicious", False)
                score_num = score_v.get("score", 0)
                tags      = ", ".join(verdict.get("tags", []))
                scan_date = item.get("task", {}).get("time", "")[:10]

                snippet = (
                    f"IP: {ip_addr}  Country: {country}  "
                    f"Scan: {scan_date}  Score: {score_num}"
                )
                if tags:
                    snippet += f"  Tags: {tags}"
                if malicious:
                    snippet += "  ⚠️ Flagged MALICIOUS"

                if not url_link:
                    continue

                r = _make_result("URLScan.io", title_v, url_link, snippet, query)
                if malicious:
                    r["risk_level"] = "high"
                elif score_num > 50:
                    r["risk_level"] = "medium"
                self._emit(r)
                count += 1

        except Exception as exc:
            self.progress.emit(f"  ⚠️  URLScan.io error: {exc}")
            return -1

        self.progress.emit(f"  ↳ URLScan.io → {count} result(s)")
        return count
