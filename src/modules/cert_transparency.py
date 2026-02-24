"""
Inspector Rabbit - Certificate Transparency Module
Search crt.sh CT logs for domain certificates and subdomain discovery
"""

import re
import json
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QThread


HEADERS = {
    'User-Agent': 'Inspector-Rabbit/1.0 OSINT-Tool',
    'Accept': 'application/json',
}


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
    subdomains: List[str] = field(default_factory=list)


@dataclass
class CertTransparencyResult:
    domain: str = ""
    total_certs: int = 0
    unique_subdomains: List[str] = field(default_factory=list)
    certificates: List[CertEntry] = field(default_factory=list)
    issuers: Dict[str, int] = field(default_factory=dict)
    timeline: List[Dict] = field(default_factory=list)
    error: str = ""


def search_crtsh(domain: str, include_expired: bool = True,
                  deduplicate: bool = True) -> CertTransparencyResult:
    """Search crt.sh for certificates for a domain"""
    result = CertTransparencyResult(domain=domain)

    try:
        # Query crt.sh JSON API
        resp = requests.get(
            'https://crt.sh/',
            params={
                'q': f'%.{domain}',
                'output': 'json',
                'deduplicate': '1' if deduplicate else '0',
            },
            headers=HEADERS,
            timeout=30
        )

        if resp.status_code != 200:
            result.error = f"crt.sh returned status {resp.status_code}"
            return result

        data = resp.json()
        result.total_certs = len(data)

        seen_ids = set()
        all_subdomains = set()
        issuers = {}

        for entry in data:
            cert_id = entry.get('id', 0)
            if cert_id in seen_ids:
                continue
            seen_ids.add(cert_id)

            # Parse name_value (SANs)
            name_value = entry.get('name_value', '')
            subdomains = []
            for name in name_value.split('\n'):
                name = name.strip().lower()
                if name and not name.startswith('*'):
                    subdomains.append(name)
                    all_subdomains.add(name)
                elif name.startswith('*.'):
                    # Wildcard — add the base
                    base = name[2:]
                    all_subdomains.add(base)

            # Track issuers
            issuer = entry.get('issuer_name', 'Unknown')
            # Extract just the O= part for brevity
            o_match = re.search(r'O=([^,]+)', issuer)
            short_issuer = o_match.group(1).strip() if o_match else issuer[:50]
            issuers[short_issuer] = issuers.get(short_issuer, 0) + 1

            cert = CertEntry(
                id=cert_id,
                logged_at=entry.get('entry_timestamp', ''),
                not_before=entry.get('not_before', ''),
                not_after=entry.get('not_after', ''),
                common_name=entry.get('common_name', ''),
                name_value=name_value,
                issuer_name=short_issuer,
                serial_number=str(entry.get('serial_number', '')),
                subdomains=subdomains,
            )
            result.certificates.append(cert)

            # Build timeline
            if cert.logged_at:
                result.timeline.append({
                    'date': cert.logged_at,
                    'common_name': cert.common_name,
                    'issuer': short_issuer,
                    'id': cert_id,
                })

        # Sort unique subdomains
        result.unique_subdomains = sorted(all_subdomains)
        result.issuers = dict(sorted(issuers.items(), key=lambda x: -x[1]))

        # Sort certificates by date (newest first)
        result.certificates.sort(
            key=lambda c: c.logged_at or '', reverse=True
        )
        result.timeline.sort(key=lambda t: t['date'], reverse=True)

    except requests.exceptions.Timeout:
        result.error = "crt.sh request timed out (try again)"
    except json.JSONDecodeError:
        result.error = "Invalid JSON response from crt.sh"
    except Exception as e:
        result.error = str(e)

    return result


class CertTransparencyThread(QThread):
    progress = pyqtSignal(str)
    result_ready = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, domain: str, include_expired: bool = True):
        super().__init__()
        self.domain = domain.strip().lower()
        # Strip protocol
        self.domain = re.sub(r'^https?://', '', self.domain).split('/')[0]
        self.include_expired = include_expired

    def run(self):
        try:
            self.progress.emit(f"Querying crt.sh for *.{self.domain}...")
            result = search_crtsh(self.domain, self.include_expired)
            if not result.error:
                self.progress.emit(
                    f"Found {result.total_certs} certificates, "
                    f"{len(result.unique_subdomains)} unique subdomains."
                )
            self.result_ready.emit(result)
        except Exception as e:
            self.error.emit(str(e))
