"""
Inspector Rabbit - Certificate Transparency Module
Search CT logs for a domain's certificates and discover subdomains.
Primary source crt.sh (with retries — it is frequently overloaded);
falls back to SSLMate Cert Spotter's public API.
"""

import re
import json
import time
from datetime import datetime, timezone
from typing import List, Dict
from dataclasses import dataclass, field

import requests
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from . import net

HEADERS = {'User-Agent': net.TOOL_UA, 'Accept': 'application/json'}


@dataclass
class CertEntry:
    id: int = 0
    logged_at: str = ""
    not_before: str = ""
    not_after: str = ""
    common_name: str = ""
    name_value: str = ""
    issuer_name: str = ""
    serial_number: str = ""
    expired: bool = False
    subdomains: List[str] = field(default_factory=list)


@dataclass
class CertTransparencyResult:
    domain: str = ""
    source: str = ""
    total_certs: int = 0
    unique_subdomains: List[str] = field(default_factory=list)
    wildcard_names: List[str] = field(default_factory=list)
    certificates: List[CertEntry] = field(default_factory=list)
    issuers: Dict[str, int] = field(default_factory=dict)
    timeline: List[Dict] = field(default_factory=list)
    error: str = ""


def _in_scope(name: str, domain: str) -> bool:
    return name == domain or name.endswith('.' + domain)


def _is_expired(not_after: str) -> bool:
    try:
        dt = datetime.fromisoformat(not_after.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt < datetime.now(timezone.utc)
    except Exception:
        return False


def _short_issuer(issuer: str) -> str:
    m = re.search(r'O="?([^,"]+)"?', issuer or '')
    if m:
        return m.group(1).strip()
    m = re.search(r'CN="?([^,"]+)"?', issuer or '')
    return m.group(1).strip() if m else (issuer or 'Unknown')[:50]


def _fetch_crtsh(domain: str, deduplicate: bool) -> list:
    last = ''
    for attempt in range(4):
        try:
            resp = requests.get(
                'https://crt.sh/',
                params={'q': f'%.{domain}', 'output': 'json', 'deduplicate': 'Y' if deduplicate else 'N'},
                headers=HEADERS, timeout=60)
            if resp.status_code == 200:
                try:
                    return resp.json()
                except ValueError:
                    last = 'crt.sh returned invalid JSON (often a timeout on large domains)'
            else:
                last = f"crt.sh HTTP {resp.status_code}"
        except requests.exceptions.Timeout:
            last = 'crt.sh timed out'
        except net.ProxyUnavailable:
            raise
        except Exception as e:
            last = f"crt.sh: {e}"
        time.sleep(2 + attempt * 3)
    raise RuntimeError(last)


def _fetch_certspotter(domain: str) -> list:
    """Cert Spotter issuances, normalised to crt.sh-like dicts (unauthenticated, rate-limited)."""
    out, after = [], None
    for _ in range(10):        # up to ~1000 issuances
        params = {'domain': domain, 'include_subdomains': 'true',
                  'expand': ['dns_names', 'issuer']}
        if after:
            params['after'] = after
        r = requests.get('https://api.certspotter.com/v1/issuances', params=params,
                         headers=HEADERS, timeout=30)
        if r.status_code == 429:
            if out:
                break
            raise RuntimeError('Cert Spotter rate limit reached (unauthenticated quota)')
        if r.status_code != 200:
            raise RuntimeError(f'Cert Spotter HTTP {r.status_code}')
        batch = r.json()
        if not batch:
            break
        for it in batch:
            names = it.get('dns_names', []) or []
            issuer = it.get('issuer') or {}
            out.append({
                'id': it.get('id'),
                'entry_timestamp': '',
                'not_before': it.get('not_before', ''),
                'not_after': it.get('not_after', ''),
                'common_name': names[0] if names else '',
                'name_value': '\n'.join(names),
                'issuer_name': issuer.get('friendly_name') or issuer.get('name', ''),
                'serial_number': '',
            })
        after = batch[-1].get('id')
        if len(batch) < 100:
            break
    return out


def search_crtsh(domain: str, include_expired: bool = True,
                 deduplicate: bool = True) -> CertTransparencyResult:
    """Search CT logs for certificates for a domain."""
    result = CertTransparencyResult(domain=domain)
    try:
        try:
            data = _fetch_crtsh(domain, deduplicate)
            result.source = 'crt.sh'
        except net.ProxyUnavailable:
            raise
        except Exception as e:
            crt_err = str(e)
            data = _fetch_certspotter(domain)
            result.source = f'Cert Spotter (crt.sh unavailable: {crt_err})'

        seen_ids = set()
        all_subs, wildcards = set(), set()
        issuers: Dict[str, int] = {}

        for entry in data:
            cert_id = entry.get('id', 0)
            if cert_id in seen_ids:
                continue
            seen_ids.add(cert_id)

            not_after = entry.get('not_after', '')
            expired = _is_expired(not_after)
            if expired and not include_expired:
                continue

            names = set()
            for name in (entry.get('name_value', '') or '').split('\n'):
                name = name.strip().lower().rstrip('.')
                if not name or '@' in name or ' ' in name:
                    continue
                if name.startswith('*.'):
                    base = name[2:]
                    if _in_scope(base, domain):
                        wildcards.add(name)
                        all_subs.add(base)
                    continue
                if _in_scope(name, domain):
                    names.add(name)
                    all_subs.add(name)

            short = _short_issuer(entry.get('issuer_name', ''))
            issuers[short] = issuers.get(short, 0) + 1

            cert = CertEntry(
                id=cert_id,
                logged_at=entry.get('entry_timestamp', '') or entry.get('not_before', ''),
                not_before=entry.get('not_before', ''),
                not_after=not_after,
                common_name=entry.get('common_name', ''),
                name_value=entry.get('name_value', ''),
                issuer_name=short,
                serial_number=str(entry.get('serial_number', '')),
                expired=expired,
                subdomains=sorted(names),
            )
            result.certificates.append(cert)
            if cert.logged_at:
                result.timeline.append({'date': cert.logged_at, 'common_name': cert.common_name,
                                        'issuer': short, 'id': cert_id})

        result.total_certs = len(result.certificates)
        result.unique_subdomains = sorted(all_subs)
        result.wildcard_names = sorted(wildcards)
        result.issuers = dict(sorted(issuers.items(), key=lambda x: -x[1]))
        result.certificates.sort(key=lambda c: c.logged_at or '', reverse=True)
        result.timeline.sort(key=lambda t: t['date'], reverse=True)
    except net.ProxyUnavailable as e:
        result.error = str(e)
    except Exception as e:
        result.error = f"CT lookup failed: {e}"
    return result


class CertTransparencyThread(QThread):
    progress = pyqtSignal(str)
    result_ready = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, domain: str, include_expired: bool = True):
        super().__init__()
        self.domain = net.clean_host(domain)
        self.include_expired = include_expired

    def run(self):
        try:
            self.progress.emit(f"Querying Certificate Transparency logs for *.{self.domain}...")
            result = search_crtsh(self.domain, self.include_expired)
            if not result.error:
                self.progress.emit(
                    f"Found {result.total_certs} certificates, "
                    f"{len(result.unique_subdomains)} unique names (source: {result.source})."
                )
            self.result_ready.emit(result)
        except Exception as e:
            self.error.emit(str(e))
