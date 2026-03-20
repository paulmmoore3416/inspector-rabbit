"""
Inspector Rabbit - Breach Aggregator Module
Aggregate breach data from multiple free and paid sources:
  - HaveIBeenPwned v3 (requires API key)
  - LeakCheck public API (free)
  - BreachDirectory public API (free)
"""

import requests
from PyQt6.QtCore import QThread, pyqtSignal


HEADERS = {
    'User-Agent': 'InspectorRabbit/1.3.0',
    'Accept': 'application/json',
}


def _severity_from_count(count) -> str:
    """Derive a severity string from a record count."""
    try:
        n = int(count)
    except (TypeError, ValueError):
        return 'low'
    if n >= 1_000_000:
        return 'high'
    if n >= 10_000:
        return 'medium'
    return 'low'


class BreachAggThread(QThread):
    result_ready = pyqtSignal(dict)
    progress = pyqtSignal(str)
    breach_found = pyqtSignal(dict)

    def __init__(self, query: str, query_type: str, hibp_key: str = ""):
        super().__init__()
        self._query = query.strip()
        self._query_type = query_type.lower()   # 'email', 'domain', 'username'
        self._hibp_key = hibp_key.strip()
        self._total = 0
        self._sources_checked = []
        self._highest_severity = 'low'

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def run(self):
        self.progress.emit(f"Starting breach aggregation for: {self._query}")

        if self._hibp_key:
            self._check_hibp()
        else:
            self.progress.emit("HIBP skipped (no API key provided)")

        self._check_leakcheck()
        self._check_breachdirectory()

        # Summary
        self.progress.emit(
            f"Scan complete — {self._total} breach(es) found across "
            f"{len(self._sources_checked)} source(s)"
        )
        self.result_ready.emit({
            'total_breaches': self._total,
            'sources_checked': self._sources_checked,
            'highest_severity': self._highest_severity,
            'query': self._query,
        })

    # ------------------------------------------------------------------
    # HIBP v3
    # ------------------------------------------------------------------

    def _check_hibp(self):
        self.progress.emit("Checking HaveIBeenPwned...")
        self._sources_checked.append('HIBP')
        headers = dict(HEADERS)
        headers['hibp-api-key'] = self._hibp_key

        # Breached account endpoint — only meaningful for email queries
        if self._query_type == 'email':
            try:
                url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{self._query}"
                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    breaches = resp.json()
                    self.progress.emit(f"  ↳ HIBP: {len(breaches)} breach(es) found")
                    for b in breaches:
                        count = b.get('PwnCount', 0)
                        severity = _severity_from_count(count)
                        self._update_severity(severity)
                        self._total += 1
                        self.breach_found.emit({
                            'source': 'HIBP',
                            'email': self._query,
                            'breach_name': b.get('Name', 'Unknown'),
                            'date': b.get('BreachDate', ''),
                            'count': str(count),
                            'severity': severity,
                            'description': b.get('Description', '')[:300],
                        })
                elif resp.status_code == 404:
                    self.progress.emit("  ↳ HIBP: no breaches found for this email")
                elif resp.status_code == 401:
                    self.progress.emit("  ↳ HIBP: invalid API key")
                elif resp.status_code == 429:
                    self.progress.emit("  ↳ HIBP: rate limited — try again later")
                else:
                    self.progress.emit(f"  ↳ HIBP: HTTP {resp.status_code}")
            except Exception as e:
                self.progress.emit(f"  ↳ HIBP account check error: {e}")

        # Domain breach check via free /api/v3/breaches endpoint
        if self._query_type in ('email', 'domain'):
            try:
                domain = self._query.split('@')[-1] if '@' in self._query else self._query
                url = "https://haveibeenpwned.com/api/v3/breaches"
                resp = requests.get(url, headers=headers, params={'domain': domain}, timeout=15)
                if resp.status_code == 200:
                    breaches = resp.json()
                    if breaches:
                        self.progress.emit(f"  ↳ HIBP domain: {len(breaches)} breach(es) involve {domain}")
                        for b in breaches:
                            count = b.get('PwnCount', 0)
                            severity = _severity_from_count(count)
                            self._update_severity(severity)
                            self._total += 1
                            self.breach_found.emit({
                                'source': 'HIBP (domain)',
                                'email': self._query,
                                'breach_name': b.get('Name', 'Unknown'),
                                'date': b.get('BreachDate', ''),
                                'count': str(count),
                                'severity': severity,
                                'description': b.get('Description', '')[:300],
                            })
                    else:
                        self.progress.emit(f"  ↳ HIBP domain: no breaches for {domain}")
            except Exception as e:
                self.progress.emit(f"  ↳ HIBP domain check error: {e}")

    # ------------------------------------------------------------------
    # LeakCheck (free public endpoint)
    # ------------------------------------------------------------------

    def _check_leakcheck(self):
        self.progress.emit("Checking LeakCheck.io (public)...")
        self._sources_checked.append('LeakCheck')
        try:
            url = f"https://leakcheck.io/api/public?check={self._query}"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                found = data.get('found', 0)
                sources = data.get('sources', [])
                self.progress.emit(f"  ↳ LeakCheck: {found} record(s) in {len(sources)} source(s)")
                for src in sources:
                    name = src if isinstance(src, str) else src.get('name', 'Unknown')
                    severity = 'medium' if found > 1000 else 'low'
                    self._update_severity(severity)
                    self._total += 1
                    self.breach_found.emit({
                        'source': 'LeakCheck',
                        'email': self._query,
                        'breach_name': name,
                        'date': '',
                        'count': str(found),
                        'severity': severity,
                        'description': f"Exposed in {name} (LeakCheck public result)",
                    })
            elif resp.status_code == 404:
                self.progress.emit("  ↳ LeakCheck: not found")
            elif resp.status_code == 429:
                self.progress.emit("  ↳ LeakCheck: rate limited")
            else:
                self.progress.emit(f"  ↳ LeakCheck: HTTP {resp.status_code}")
        except Exception as e:
            self.progress.emit(f"  ↳ LeakCheck error: {e}")

    # ------------------------------------------------------------------
    # BreachDirectory (free public endpoint)
    # ------------------------------------------------------------------

    def _check_breachdirectory(self):
        self.progress.emit("Checking BreachDirectory.org (public)...")
        self._sources_checked.append('BreachDirectory')
        try:
            url = f"https://breachdirectory.org/api?func=auto&term={self._query}"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get('result', [])
                if not results and data.get('success') is False:
                    self.progress.emit(f"  ↳ BreachDirectory: no results or API unavailable")
                    return
                self.progress.emit(f"  ↳ BreachDirectory: {len(results)} record(s) found")
                for item in results:
                    src_name = item.get('sources', ['BreachDirectory'])
                    if isinstance(src_name, list):
                        src_name = ', '.join(src_name) or 'BreachDirectory'
                    count = item.get('count', 0)
                    severity = _severity_from_count(count)
                    self._update_severity(severity)
                    self._total += 1
                    self.breach_found.emit({
                        'source': 'BreachDirectory',
                        'email': self._query,
                        'breach_name': src_name,
                        'date': item.get('date', ''),
                        'count': str(count),
                        'severity': severity,
                        'description': item.get('fields', 'Breach data exposure'),
                    })
            elif resp.status_code == 404:
                self.progress.emit("  ↳ BreachDirectory: not found")
            elif resp.status_code == 429:
                self.progress.emit("  ↳ BreachDirectory: rate limited")
            else:
                self.progress.emit(f"  ↳ BreachDirectory: HTTP {resp.status_code}")
        except Exception as e:
            self.progress.emit(f"  ↳ BreachDirectory error: {e}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _update_severity(self, severity: str):
        order = {'low': 0, 'medium': 1, 'high': 2}
        if order.get(severity, 0) > order.get(self._highest_severity, 0):
            self._highest_severity = severity
