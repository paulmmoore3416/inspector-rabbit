"""
Inspector Rabbit - Dark Web / Exposure Lookup Module  v1.6.0

Sources:
  1. Ahmia.fi            — Tor hidden-service search index (clearnet)
  2. Intelligence X      — leak/darknet archive (free API key: intelx.io/account?tab=developer)
  3. Paste sites         — pastebin/rentry/ghostbin/etc via the dork engine
  4. GitHub code leaks   — GitHub code search (requires GitHub token)
  5. URLScan.io          — scan history / phishing verdicts (key optional)

Retired: DarkSearch.io and psbdmp.ws (offline), grep.app (browser challenge).
"""

import re
import time
import warnings
from datetime import datetime, timezone

import requests

from . import net
from .config import load_settings

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
        "Paste sites",
        "GitHub code leaks",
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
        return name in self._enabled

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

        self._settings = load_settings()
        checks = [
            ("Ahmia.fi",           self._check_ahmia),
            ("Intelligence X",     self._check_intelx),
            ("Paste sites",        self._check_pastes),
            ("GitHub code leaks",  self._check_github_code),
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
                if count == -2:
                    self.source_status.emit(source_name, 0, "skipped")
                    continue
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
        from urllib.parse import parse_qs, urlparse
        count, seen = 0, set()
        try:
            sess = requests.Session()
            home = sess.get("https://ahmia.fi/", headers=HEADERS, timeout=TIMEOUT_LONG)
            form = BeautifulSoup(home.text, "html.parser").select_one("form")
            params = {i.get("name"): i.get("value", "") for i in (form.select("input[type=hidden]") if form else [])
                      if i.get("name")}
            params["q"] = query
            resp = sess.get("https://ahmia.fi/search/", params=params, headers=HEADERS, timeout=TIMEOUT_LONG)
            if resp.status_code != 200:
                self.progress.emit(f"  ↳ Ahmia: HTTP {resp.status_code}")
                return -1
            if urlparse(resp.url).path in ("", "/"):
                self.progress.emit("  ↳ Ahmia: search token rejected (site changed its anti-bot form)")
                return -1
            soup = BeautifulSoup(resp.text, "html.parser")
            for item in soup.select("li.result"):
                if self._stopped() or count >= 25:
                    break
                a = item.select_one("h4 a") or item.select_one("a")
                if not a:
                    continue
                href = a.get("href", "")
                if "redirect_url=" in href:
                    href = parse_qs(urlparse(href).query).get("redirect_url", [href])[0]
                onion = urlparse(href).hostname or href
                if onion in seen:
                    continue
                seen.add(onion)
                title = a.get_text(" ", strip=True)
                p = item.select_one("p")
                snippet = p.get_text(" ", strip=True) if p else ""
                last = item.select_one("span.lastSeen") or item.select_one(".lastSeen")
                if last:
                    snippet = f"{snippet}  [last seen {last.get_text(strip=True)}]"
                self._emit(_make_result("Ahmia.fi", title or onion, href, snippet, query))
                count += 1
        except net.ProxyUnavailable as exc:
            self.progress.emit(f"  ⚠️  {exc}")
            return -1
        except Exception as exc:
            self.progress.emit(f"  ⚠️  Ahmia error: {exc}")
            return -1
        self.progress.emit(f"  ↳ Ahmia.fi → {count} unique onion service(s)")
        return count

    # ── 2. Intelligence X ─────────────────────────────────────────────────────

    def _check_intelx(self, query: str) -> int:
        key = self._settings.get("intelx_api_key", "")
        if not key:
            self.progress.emit("ℹ️  Intelligence X skipped — add a free API key in Settings")
            return -2
        self.progress.emit("🔎 Intelligence X — searching leak archive…")
        base = self._settings.get("intelx_api_url") or "https://free.intelx.io"
        h = {**HEADERS, "x-key": key, "Content-Type": "application/json"}
        try:
            r = requests.post(f"{base}/intelligent/search", headers=h, timeout=TIMEOUT_LONG,
                              json={"term": query, "maxresults": 25, "media": 0, "sort": 2,
                                    "timeout": 10, "terminate": []})
            if r.status_code == 401:
                self.progress.emit("  ↳ IntelX: API key rejected")
                return -1
            if r.status_code == 402:
                self.progress.emit("  ↳ IntelX: free credits exhausted")
                return -1
            if r.status_code != 200:
                self.progress.emit(f"  ↳ IntelX: HTTP {r.status_code}")
                return -1
            sid = r.json().get("id")
            records = []
            for _ in range(8):
                if self._stopped():
                    break
                time.sleep(1.5)
                rr = requests.get(f"{base}/intelligent/search/result", headers=h,
                                  params={"id": sid, "limit": 25}, timeout=TIMEOUT_LONG)
                if rr.status_code != 200:
                    break
                d = rr.json()
                records.extend(d.get("records") or [])
                if d.get("status") in (1, 2) or len(records) >= 25:
                    break
            count = 0
            for rec in records[:25]:
                name = rec.get("name") or rec.get("systemid", "")
                bucket = rec.get("bucketh") or rec.get("bucket", "")
                date = (rec.get("date") or "")[:10]
                link = f"https://intelx.io/?did={rec.get('systemid')}" if rec.get("systemid") else ""
                self._emit(_make_result("Intelligence X", str(name), link,
                                        f"Bucket: {bucket}  Date: {date}  Size: {rec.get('size', '')} bytes", query))
                count += 1
            self.progress.emit(f"  ↳ Intelligence X → {count} record(s)")
            return count
        except Exception as exc:
            self.progress.emit(f"  ⚠️  IntelX error: {exc}")
            return -1

    # ── 3. Paste sites (through the dork engine) ─────────────────────────────

    PASTE_SITES = ["pastebin.com", "rentry.co", "paste.ee", "ghostbin.cloud", "justpaste.it", "controlc.com"]

    def _check_pastes(self, query: str) -> int:
        from .dorks_engine import search_auto
        self.progress.emit("🔎 Paste sites — search-engine dorks…")
        sites = " OR ".join(f"site:{s}" for s in self.PASTE_SITES)
        res = search_auto(f'({sites}) "{query}"', 20)
        if not res.results:
            # OR-groups aren't honoured by every engine; fall back to the biggest site
            res = search_auto(f'site:pastebin.com "{query}"', 20)
        if not res.results:
            self.progress.emit(f"  ↳ Paste sites: {res.error or 'no results'}")
            return -1 if res.error and res.blocked else 0
        for r in res.results:
            self._emit(_make_result("Paste sites", r.get("title", ""), r.get("url", ""),
                                    r.get("snippet", ""), query))
        self.progress.emit(f"  ↳ Paste sites → {len(res.results)} result(s) via {res.engine}")
        return len(res.results)

    # ── 4. GitHub code leaks ─────────────────────────────────────────────────

    def _check_github_code(self, query: str) -> int:
        from .paste_scanner import search_github_code
        token = self._settings.get("github_token", "")
        if not token:
            self.progress.emit("ℹ️  GitHub code search skipped — add a GitHub token in Settings")
            return -2
        self.progress.emit("🔎 GitHub — searching public code for exposed data…")
        try:
            items = search_github_code(f'"{query}"', 25, token=token)
        except Exception as exc:
            self.progress.emit(f"  ⚠️  GitHub: {exc}")
            return -1
        for it in items:
            r = _make_result("GitHub code leaks", it["title"], it["url"], it["snippet"], query)
            if r["risk_level"] == "low":
                r["risk_level"] = "medium"
            self._emit(r)
        self.progress.emit(f"  ↳ GitHub code → {len(items)} file(s)")
        return len(items)

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
                search_q = f"domain:{net.clean_host(query)}"
            else:
                search_q = '"' + query.replace('"', '') + '"'

            url    = "https://urlscan.io/api/v1/search/"
            params = {"q": search_q, "size": 20}
            h = dict(HEADERS)
            if self._settings.get("urlscan_api_key"):
                h["API-Key"] = self._settings["urlscan_api_key"]
            resp   = requests.get(url, params=params, headers=h, timeout=TIMEOUT_LONG)

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
