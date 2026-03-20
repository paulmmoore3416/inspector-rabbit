"""
Inspector Rabbit - Batch Processor Module
Process multiple targets in bulk across OSINT modules.
"""

import csv
import re
import socket
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import requests
from PyQt6.QtCore import QThread, pyqtSignal

try:
    import dns.resolver as dns_resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False


# Top 10 sites for quick username check
USERNAME_SITES = [
    ("GitHub",     "https://github.com/{}"),
    ("Twitter/X",  "https://twitter.com/{}"),
    ("Instagram",  "https://www.instagram.com/{}"),
    ("Reddit",     "https://www.reddit.com/user/{}"),
    ("TikTok",     "https://www.tiktok.com/@{}"),
    ("YouTube",    "https://www.youtube.com/@{}"),
    ("Pinterest",  "https://www.pinterest.com/{}"),
    ("Twitch",     "https://www.twitch.tv/{}"),
    ("Medium",     "https://medium.com/@{}"),
    ("DeviantArt", "https://www.deviantart.com/{}"),
]

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

# Country dial-code prefix detection
PHONE_PREFIXES = {
    "+1": "US/Canada",
    "+44": "UK",
    "+49": "Germany",
    "+33": "France",
    "+39": "Italy",
    "+34": "Spain",
    "+55": "Brazil",
    "+52": "Mexico",
    "+61": "Australia",
    "+81": "Japan",
    "+86": "China",
    "+91": "India",
    "+7":  "Russia",
    "+82": "South Korea",
    "+31": "Netherlands",
}


@dataclass
class BatchJob:
    job_id: str
    target: str
    module: str
    status: str        # pending / running / done / error
    result: dict = field(default_factory=dict)
    error_msg: str = ""
    started_at: str = ""
    completed_at: str = ""


class BatchProcessorThread(QThread):
    job_update = pyqtSignal(dict)
    progress = pyqtSignal(int, int)
    done = pyqtSignal(list)

    def __init__(self, targets: list, module: str, settings: dict = None):
        super().__init__()
        self.targets = targets
        self.module = module
        self.settings = settings or {}
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        jobs = []
        total = len(self.targets)

        for idx, target in enumerate(self.targets):
            if self._stop:
                break

            job = BatchJob(
                job_id=str(uuid.uuid4())[:8],
                target=target,
                module=self.module,
                status="running",
                started_at=_now(),
            )
            self.job_update.emit(_job_to_dict(job))

            try:
                result = self._run_module(target, self.module)
                job.result = result
                job.status = "done"
            except Exception as exc:
                job.error_msg = str(exc)
                job.status = "error"

            job.completed_at = _now()
            jobs.append(job)
            self.job_update.emit(_job_to_dict(job))
            self.progress.emit(idx + 1, total)

        self.done.emit([_job_to_dict(j) for j in jobs])

    # ------------------------------------------------------------------
    # Module dispatch
    # ------------------------------------------------------------------

    def _run_module(self, target: str, module: str) -> dict:
        if module == "domain":
            return self._check_domain(target)
        elif module == "email":
            return self._check_email(target)
        elif module == "ip":
            return self._check_ip(target)
        elif module == "username":
            return self._check_username(target)
        elif module == "phone":
            return self._check_phone(target)
        else:
            raise ValueError(f"Unknown module: {module}")

    # ------------------------------------------------------------------
    # Domain check
    # ------------------------------------------------------------------

    def _check_domain(self, domain: str) -> dict:
        result: dict = {"domain": domain, "reachable": False, "ip_addresses": [], "status_code": None}

        # DNS resolve
        try:
            addrs = socket.getaddrinfo(domain, None)
            ips = list({a[4][0] for a in addrs})
            result["ip_addresses"] = ips
        except Exception as exc:
            result["dns_error"] = str(exc)

        # HTTP HEAD
        try:
            resp = requests.head(
                f"https://{domain}",
                headers=HEADERS,
                timeout=8,
                allow_redirects=True,
                verify=False,
            )
            result["status_code"] = resp.status_code
            result["reachable"] = resp.status_code < 500
            result["final_url"] = resp.url
        except requests.exceptions.SSLError:
            try:
                resp = requests.head(
                    f"http://{domain}",
                    headers=HEADERS,
                    timeout=8,
                    allow_redirects=True,
                )
                result["status_code"] = resp.status_code
                result["reachable"] = resp.status_code < 500
            except Exception as exc2:
                result["http_error"] = str(exc2)
        except Exception as exc:
            result["http_error"] = str(exc)

        return result

    # ------------------------------------------------------------------
    # Email check
    # ------------------------------------------------------------------

    def _check_email(self, email: str) -> dict:
        result: dict = {"email": email, "valid_format": False, "mx_records": [], "deliverable": False}

        # Format check
        if not EMAIL_RE.match(email):
            result["format_error"] = "Invalid email format"
            return result
        result["valid_format"] = True

        domain = email.split("@", 1)[1]
        result["domain"] = domain

        # MX record check
        if DNS_AVAILABLE:
            try:
                mx_records = dns_resolver.resolve(domain, "MX")
                mxs = sorted(
                    [(r.preference, str(r.exchange).rstrip(".")) for r in mx_records],
                    key=lambda x: x[0],
                )
                result["mx_records"] = [f"{pref} {exch}" for pref, exch in mxs]
                result["deliverable"] = bool(mxs)
            except Exception as exc:
                result["mx_error"] = str(exc)
        else:
            result["mx_error"] = "dnspython not available"

        return result

    # ------------------------------------------------------------------
    # IP check
    # ------------------------------------------------------------------

    def _check_ip(self, ip: str) -> dict:
        result: dict = {"ip": ip, "geo": {}, "hostname": ""}

        # rDNS
        try:
            hostname, _aliases, _addrs = socket.gethostbyaddr(ip)
            result["hostname"] = hostname
        except Exception:
            result["hostname"] = ""

        # GeoIP via ip-api.com
        try:
            resp = requests.get(
                f"http://ip-api.com/json/{ip}",
                headers=HEADERS,
                timeout=8,
            )
            if resp.status_code == 200:
                data = resp.json()
                result["geo"] = {
                    "country": data.get("country", ""),
                    "region": data.get("regionName", ""),
                    "city": data.get("city", ""),
                    "isp": data.get("isp", ""),
                    "org": data.get("org", ""),
                    "latitude": data.get("lat", ""),
                    "longitude": data.get("lon", ""),
                    "timezone": data.get("timezone", ""),
                    "status": data.get("status", ""),
                }
        except Exception as exc:
            result["geo_error"] = str(exc)

        return result

    # ------------------------------------------------------------------
    # Username check
    # ------------------------------------------------------------------

    def _check_username(self, username: str) -> dict:
        found = []
        not_found = []
        errors = []

        for site_name, url_template in USERNAME_SITES:
            url = url_template.format(username)
            try:
                resp = requests.head(
                    url,
                    headers=HEADERS,
                    timeout=6,
                    allow_redirects=True,
                )
                if resp.status_code == 200:
                    found.append({"site": site_name, "url": url})
                elif resp.status_code == 404:
                    not_found.append(site_name)
                else:
                    errors.append({"site": site_name, "status": resp.status_code})
            except Exception as exc:
                errors.append({"site": site_name, "error": str(exc)})

        return {
            "username": username,
            "found": found,
            "not_found": not_found,
            "errors": errors,
            "found_count": len(found),
        }

    # ------------------------------------------------------------------
    # Phone check
    # ------------------------------------------------------------------

    def _check_phone(self, phone: str) -> dict:
        result: dict = {"phone": phone, "valid": False, "country": "", "formatted": ""}

        # Normalize
        digits_only = re.sub(r"[^\d+]", "", phone)

        # Basic length check
        digit_count = len(re.sub(r"\D", "", digits_only))
        if digit_count < 7 or digit_count > 15:
            result["error"] = f"Invalid length: {digit_count} digits"
            return result

        result["valid"] = True
        result["formatted"] = digits_only
        result["digit_count"] = digit_count

        # Country detection by prefix
        detected_country = ""
        for prefix, country in PHONE_PREFIXES.items():
            if digits_only.startswith(prefix):
                detected_country = country
                result["prefix"] = prefix
                break

        # Fallback: if starts with 1 (NANP)
        if not detected_country and digits_only.startswith("1") and digit_count == 11:
            detected_country = "US/Canada (NANP)"
        elif not detected_country and digit_count == 10:
            detected_country = "Possibly US/Canada (no country code)"

        result["country"] = detected_country or "Unknown"
        return result


# ------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _job_to_dict(job: BatchJob) -> dict:
    return {
        "job_id": job.job_id,
        "target": job.target,
        "module": job.module,
        "status": job.status,
        "result": job.result,
        "error_msg": job.error_msg,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
    }


def parse_csv_targets(file_path: str) -> list:
    """Read a CSV file and return first-column values, skipping header rows."""
    targets = []
    HEADER_WORDS = {"target", "email", "domain", "ip", "username", "phone", "url", "name"}
    try:
        with open(file_path, "r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.reader(fh)
            for row_idx, row in enumerate(reader):
                if not row:
                    continue
                value = row[0].strip()
                if not value:
                    continue
                # Skip header rows
                if row_idx == 0 and value.lower() in HEADER_WORDS:
                    continue
                targets.append(value)
    except Exception:
        pass
    return targets
