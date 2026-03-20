"""
Inspector Rabbit - Dark Web / Exposure Lookup Module
Searches public OSINT sources for target exposure indicators.

Sources used (all free / no key):
  1. Ahmia.fi    — public Tor search index
  2. Intelligence X free endpoint
  3. psbdmp.ws   — Pastebin OSINT
  4. darksearch.io — dark-web search API
"""

import re
import time
from datetime import datetime, timezone
from typing import List

import requests
from bs4 import BeautifulSoup
from PyQt6.QtCore import QThread, pyqtSignal


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0.0.0 Safari/537.36'
}

# Keywords used to determine risk level
HIGH_KEYWORDS = {
    "password", "passwd", "credentials", "credential", "breach", "breached",
    "leaked", "leak", "hacked", "hack", "exploit", "dump", "database dump",
    "login", "secret", "token", "api key", "apikey", "private key",
}
MEDIUM_KEYWORDS = {
    "email", "account", "profile", "user", "username", "address",
    "phone", "ssn", "dox", "doxx", "personal", "data",
}


def _assess_risk(text: str) -> str:
    """Return 'high', 'medium', or 'low' based on keyword presence."""
    lower = text.lower()
    for kw in HIGH_KEYWORDS:
        if kw in lower:
            return "high"
    for kw in MEDIUM_KEYWORDS:
        if kw in lower:
            return "medium"
    return "low"


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


class DarkWebThread(QThread):
    result_found = pyqtSignal(dict)   # {source, title, url, snippet, risk_level, query, timestamp}
    progress     = pyqtSignal(str)
    done         = pyqtSignal(dict)   # {total_found, high_risk, sources_checked, exposure_score}

    def __init__(self, query: str, query_type: str, parent=None):
        super().__init__(parent)
        self._query = query
        self._query_type = query_type

    def run(self):
        query      = self._query
        results    = []
        sources_checked = 0

        # ── 1. Ahmia.fi ──────────────────────────────────────────────────────
        self.progress.emit("Searching Ahmia.fi (public Tor index)…")
        try:
            url = f"https://ahmia.fi/search/?q={requests.utils.quote(query)}"
            resp = requests.get(url, headers=HEADERS, timeout=12)
            soup = BeautifulSoup(resp.text, "lxml")
            sources_checked += 1
            items = soup.select("li.result")
            if not items:
                items = soup.select("div.result")
            count = 0
            for item in items[:20]:
                title_el = item.select_one("h4") or item.select_one("h3") or item.select_one("a")
                link_el   = item.select_one("a[href]")
                snippet_el = item.select_one("p") or item.select_one(".description")

                title   = title_el.get_text(strip=True) if title_el else ""
                link    = link_el["href"] if link_el else ""
                snippet = snippet_el.get_text(strip=True)[:200] if snippet_el else ""

                if not title and not snippet:
                    continue

                combined_text = f"{title} {snippet}"
                risk = _assess_risk(combined_text)
                r = {
                    "source": "Ahmia.fi",
                    "title": title[:120],
                    "url": link,
                    "snippet": snippet,
                    "risk_level": risk,
                    "query": query,
                    "timestamp": _now_ts(),
                }
                results.append(r)
                self.result_found.emit(r)
                count += 1
            self.progress.emit(f"  Ahmia.fi → {count} result(s)")
        except Exception as exc:
            self.progress.emit(f"  ⚠️ Ahmia.fi error: {exc}")

        # ── 2. Intelligence X free search ────────────────────────────────────
        self.progress.emit("Querying Intelligence X…")
        try:
            ix_url  = "https://2.intelx.io/intelligent/search"
            payload = {
                "term": query,
                "maxresults": 20,
                "media": 0,
                "sort": 4,
                "terminate": [],
            }
            resp = requests.post(ix_url, json=payload, headers=HEADERS, timeout=15)
            data = resp.json()
            sources_checked += 1
            count = 0
            records = data.get("records") or data.get("results") or []
            if not records and isinstance(data, list):
                records = data
            for record in records[:20]:
                title   = record.get("name") or record.get("title") or ""
                link    = record.get("storageid") or record.get("url") or ""
                snippet = record.get("preview") or record.get("description") or ""
                if isinstance(snippet, list):
                    snippet = " ".join(str(s) for s in snippet)
                snippet = str(snippet)[:200]
                combined = f"{title} {snippet}"
                risk = _assess_risk(combined)
                r = {
                    "source": "Intelligence X",
                    "title": str(title)[:120],
                    "url": str(link),
                    "snippet": snippet,
                    "risk_level": risk,
                    "query": query,
                    "timestamp": _now_ts(),
                }
                results.append(r)
                self.result_found.emit(r)
                count += 1
            self.progress.emit(f"  Intelligence X → {count} result(s)")
        except Exception as exc:
            self.progress.emit(f"  ⚠️ Intelligence X error: {exc}")

        # ── 3. psbdmp.ws (Pastebin OSINT) ────────────────────────────────────
        self.progress.emit("Searching Pastebin via psbdmp.ws…")
        try:
            url = f"https://psbdmp.ws/api/search/{requests.utils.quote(query)}"
            resp = requests.get(url, headers=HEADERS, timeout=12)
            data = resp.json()
            sources_checked += 1
            count = 0
            pastes = data if isinstance(data, list) else data.get("data", [])
            for paste in pastes[:20]:
                paste_id = paste.get("id", "")
                title    = paste.get("tags", "") or paste_id
                snippet  = paste.get("text", "")[:200] if paste.get("text") else ""
                link     = f"https://pastebin.com/{paste_id}" if paste_id else ""
                risk     = _assess_risk(f"{title} {snippet}")
                r = {
                    "source": "Pastebin (psbdmp)",
                    "title": str(title)[:120],
                    "url": link,
                    "snippet": snippet,
                    "risk_level": risk,
                    "query": query,
                    "timestamp": _now_ts(),
                }
                results.append(r)
                self.result_found.emit(r)
                count += 1
            self.progress.emit(f"  psbdmp.ws → {count} result(s)")
        except Exception as exc:
            self.progress.emit(f"  ⚠️ psbdmp.ws error: {exc}")

        # ── 4. DarkSearch.io ─────────────────────────────────────────────────
        self.progress.emit("Searching DarkSearch.io…")
        try:
            url  = f"https://darksearch.io/api/search?query={requests.utils.quote(query)}&page=1"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            data = resp.json()
            sources_checked += 1
            count = 0
            items = data.get("data", []) if isinstance(data, dict) else []
            for item in items[:20]:
                title   = item.get("title", "")
                link    = item.get("link", "") or item.get("url", "")
                snippet = item.get("description", "")[:200]
                risk    = _assess_risk(f"{title} {snippet}")
                r = {
                    "source": "DarkSearch.io",
                    "title": str(title)[:120],
                    "url": str(link),
                    "snippet": snippet,
                    "risk_level": risk,
                    "query": query,
                    "timestamp": _now_ts(),
                }
                results.append(r)
                self.result_found.emit(r)
                count += 1
            self.progress.emit(f"  DarkSearch.io → {count} result(s)")
        except Exception as exc:
            self.progress.emit(f"  ⚠️ DarkSearch.io error: {exc}")

        # ── Summary ──────────────────────────────────────────────────────────
        total       = len(results)
        high_count  = sum(1 for r in results if r["risk_level"] == "high")
        medium_count= sum(1 for r in results if r["risk_level"] == "medium")
        low_count   = sum(1 for r in results if r["risk_level"] == "low")

        exposure_score = high_count * 10 + medium_count * 5 + low_count * 1

        self.progress.emit(
            f"Scan complete: {total} result(s) — "
            f"{high_count} high / {medium_count} medium / {low_count} low  "
            f"(exposure score: {exposure_score})"
        )
        self.done.emit({
            "total_found": total,
            "high_risk": high_count,
            "sources_checked": sources_checked,
            "exposure_score": exposure_score,
        })
