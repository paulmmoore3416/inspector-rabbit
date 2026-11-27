"""
Inspector Rabbit - Breach Aggregator Module

Sources
  Email     HIBP v3 (API key) · XposedOrNot (free) · LeakCheck public (free)
  Username  LeakCheck public (free)
  Domain    Breaches *of* that domain's service: HIBP public catalogue +
            XposedOrNot (free). This says the site itself was breached — it
            does NOT mean an address at that domain was exposed.

Severity is derived from what was exposed (passwords > PII > emails),
not from how big the breach was overall.
"""

import re

import requests
from PyQt6.QtCore import QThread, pyqtSignal

from . import net
from .email_osint import check_xposedornot

HEADERS = {'User-Agent': net.TOOL_UA, 'Accept': 'application/json'}

_HIGH = ('password', 'passwords', 'credit card', 'bank', 'ssn', 'social security',
         'security questions', 'auth tokens', 'private messages', 'government issued ids',
         'passport', 'partial credit card')
_MEDIUM = ('phone', 'physical address', 'home address', 'street', 'dates of birth', 'dob', 'ip address',
           'names', 'geographic locations', 'genders', 'usernames', 'first_name', 'last_name')


def severity_from_classes(classes) -> str:
    text = ' '.join(str(c) for c in (classes or [])).lower()
    if any(k in text for k in _HIGH):
        return 'high'
    if any(k in text for k in _MEDIUM):
        return 'medium'
    return 'low'


def _strip_html(s: str) -> str:
    return re.sub(r'<[^>]+>', '', s or '')


class BreachAggThread(QThread):
    result_ready = pyqtSignal(dict)
    progress = pyqtSignal(str)
    breach_found = pyqtSignal(dict)

    def __init__(self, query: str, query_type: str, hibp_key: str = ""):
        super().__init__()
        self._query = query.strip()
        self._query_type = query_type.lower()   # 'email', 'domain', 'username'
        if self._query_type == 'domain':
            self._query = net.clean_host(self._query)
        elif self._query_type == 'email':
            self._query = self._query.lower()
        self._hibp_key = hibp_key.strip()
        self._total = 0
        self._sources_checked = []
        self._highest_severity = 'low'
        self._seen = set()
        self._errors = []

    def run(self):
        self.progress.emit(f"Starting breach aggregation for: {self._query} [{self._query_type}]")
        if self._query_type == 'email':
            if '@' not in self._query:
                self.progress.emit("⚠️  That does not look like an email address")
            if self._hibp_key:
                self._check_hibp_account()
            else:
                self.progress.emit("HIBP skipped (no API key) — using free sources")
            self._check_xposedornot()
            self._check_leakcheck()
        elif self._query_type == 'username':
            self._check_leakcheck()
        elif self._query_type == 'domain':
            self.progress.emit("ℹ️  Domain mode lists breaches OF this site/service, not of addresses at it.")
            self._check_hibp_domain()
            self._check_xon_domain()
        self.progress.emit(
            f"Scan complete — {self._total} breach record(s) across {len(self._sources_checked)} source(s)")
        self.result_ready.emit({
            'total_breaches': self._total,
            'sources_checked': self._sources_checked,
            'highest_severity': self._highest_severity,
            'query': self._query,
            'errors': self._errors,
        })

    # ── helpers ───────────────────────────────────────────────────────────

    def _emit(self, source, name, date='', count='', classes=None, description='', severity=None):
        key = (name or '').lower().replace(' ', '')
        if key in self._seen:
            return
        self._seen.add(key)
        sev = severity or severity_from_classes(classes)
        self._update_severity(sev)
        self._total += 1
        desc = _strip_html(description)
        if classes:
            desc = (f"Exposed: {', '.join(classes)}. " + desc).strip()
        self.breach_found.emit({
            'source': source,
            'email': self._query,
            'breach_name': name or 'Unknown',
            'date': str(date or ''),
            'count': str(count) if count not in (None, '') else '',
            'severity': sev,
            'description': desc[:400],
            'data_classes': list(classes or []),
        })

    def _fail(self, source, msg):
        self._errors.append(f"{source}: {msg}")
        self.progress.emit(f"  ↳ {source}: {msg}")

    def _update_severity(self, severity: str):
        order = {'low': 0, 'medium': 1, 'high': 2}
        if order.get(severity, 0) > order.get(self._highest_severity, 0):
            self._highest_severity = severity

    # ── HIBP ─────────────────────────────────────────────────────────────

    def _check_hibp_account(self):
        self.progress.emit("Checking HaveIBeenPwned...")
        self._sources_checked.append('HIBP')
        try:
            resp = requests.get(
                f"https://haveibeenpwned.com/api/v3/breachedaccount/{requests.utils.quote(self._query)}",
                params={'truncateResponse': 'false'},
                headers={**HEADERS, 'hibp-api-key': self._hibp_key}, timeout=15)
            if resp.status_code == 200:
                breaches = resp.json()
                self.progress.emit(f"  ↳ HIBP: {len(breaches)} breach(es)")
                for b in breaches:
                    self._emit('HIBP', b.get('Title') or b.get('Name'), b.get('BreachDate'),
                               b.get('PwnCount'), b.get('DataClasses'), b.get('Description'))
            elif resp.status_code == 404:
                self.progress.emit("  ↳ HIBP: not found in any breach")
            elif resp.status_code == 401:
                self._fail('HIBP', 'invalid API key')
            elif resp.status_code == 429:
                self._fail('HIBP', 'rate limited — try again shortly')
            else:
                self._fail('HIBP', f'HTTP {resp.status_code}')
        except Exception as e:
            self._fail('HIBP', str(e))

    def _check_hibp_domain(self):
        self.progress.emit("Checking HIBP public breach catalogue...")
        self._sources_checked.append('HIBP catalogue')
        try:
            resp = requests.get("https://haveibeenpwned.com/api/v3/breaches",
                                params={'domain': self._query}, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                return self._fail('HIBP catalogue', f'HTTP {resp.status_code}')
            breaches = resp.json()
            self.progress.emit(f"  ↳ HIBP catalogue: {len(breaches)} breach(es) of {self._query}")
            for b in breaches:
                self._emit('HIBP catalogue', b.get('Title') or b.get('Name'), b.get('BreachDate'),
                           b.get('PwnCount'), b.get('DataClasses'), b.get('Description'))
        except Exception as e:
            self._fail('HIBP catalogue', str(e))

    # ── XposedOrNot ──────────────────────────────────────────────────────

    def _check_xposedornot(self):
        self.progress.emit("Checking XposedOrNot...")
        self._sources_checked.append('XposedOrNot')
        breaches, err = check_xposedornot(self._query)
        if err:
            return self._fail('XposedOrNot', err)
        self.progress.emit(f"  ↳ XposedOrNot: {len(breaches)} breach(es)")
        for b in breaches:
            self._emit('XposedOrNot', b['Name'], b['BreachDate'], b['PwnCount'],
                       b.get('DataClasses'), b.get('Description'))

    def _check_xon_domain(self):
        self.progress.emit("Checking XposedOrNot breach catalogue...")
        self._sources_checked.append('XposedOrNot catalogue')
        try:
            r = requests.get('https://api.xposedornot.com/v1/breaches',
                             params={'domain': self._query}, headers=HEADERS, timeout=15)
            if r.status_code == 404:
                return self.progress.emit("  ↳ XposedOrNot: none")
            if r.status_code != 200:
                return self._fail('XposedOrNot catalogue', f'HTTP {r.status_code}')
            items = r.json().get('exposedBreaches') or []
            self.progress.emit(f"  ↳ XposedOrNot catalogue: {len(items)} breach(es)")
            for b in items:
                self._emit('XposedOrNot catalogue', b.get('breachID'), (b.get('breachedDate') or '')[:10],
                           b.get('exposedRecords'), b.get('exposedData'), b.get('exposureDescription'))
        except Exception as e:
            self._fail('XposedOrNot catalogue', str(e))

    # ── LeakCheck ────────────────────────────────────────────────────────

    def _check_leakcheck(self):
        self.progress.emit("Checking LeakCheck.io (public API)...")
        self._sources_checked.append('LeakCheck')
        try:
            resp = requests.get("https://leakcheck.io/api/public", params={'check': self._query},
                                headers=HEADERS, timeout=15)
            if resp.status_code == 429:
                return self._fail('LeakCheck', 'rate limited')
            if resp.status_code != 200:
                return self._fail('LeakCheck', f'HTTP {resp.status_code}')
            data = resp.json()
            if not data.get('success'):
                msg = data.get('error', 'not found')
                if 'not found' in str(msg).lower():
                    return self.progress.emit("  ↳ LeakCheck: not found")
                return self._fail('LeakCheck', msg)
            fields = data.get('fields', []) or []
            sources = data.get('sources', []) or []
            self.progress.emit(f"  ↳ LeakCheck: {data.get('found', 0)} record(s) in {len(sources)} source(s); "
                               f"fields: {', '.join(fields[:12])}")
            sev = severity_from_classes(fields)
            for src in sources:
                name = src if isinstance(src, str) else src.get('name', 'Unknown')
                date = '' if isinstance(src, str) else src.get('date', '')
                self._emit('LeakCheck', name, date, '', None,
                           "Listed by LeakCheck. Exposed fields across all matches: " + ', '.join(fields),
                           severity=sev)
        except Exception as e:
            self._fail('LeakCheck', str(e))
