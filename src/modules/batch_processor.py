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
    """Runs the same lookups as the individual modules, one target at a time."""
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
        from .domain_intel import normalize_domain, resolve_ips, lookup_whois, fetch_homepage
        domain = normalize_domain(domain)
        result: dict = {"domain": domain, "reachable": False, "ip_addresses": resolve_ips(domain),
                        "status_code": None}
        if not result["ip_addresses"]:
            result["dns_error"] = "Domain does not resolve"
        w = lookup_whois(domain)
        result.update({"registrar": w.registrar, "created": w.creation_date,
                       "expires": w.expiration_date, "name_servers": w.name_servers[:4]})
        if w.error and not w.registrar:
            result["whois_error"] = w.error
        if result["ip_addresses"]:
            headers, _ = fetch_homepage(domain)
            if "_error" in headers:
                result["http_error"] = headers["_error"]
            else:
                result["status_code"] = headers.get("_status_code")
                result["final_url"] = headers.get("_final_url")
                result["reachable"] = (result["status_code"] or 600) < 500
                result["server"] = headers.get("Server") or headers.get("server", "")
        return result

    def _check_email(self, email: str) -> dict:
        from .email_osint import (validate_format, get_mx_records, check_disposable,
                                  FREE_PROVIDERS, check_xposedornot)
        email = email.strip().lower()
        result: dict = {"email": email, "valid_format": validate_format(email), "mx_records": [],
                        "deliverable_domain": False}
        if not result["valid_format"]:
            result["format_error"] = "Invalid email format"
            return result
        domain = email.split("@", 1)[1]
        result["domain"] = domain
        result["mx_records"] = get_mx_records(domain)
        result["deliverable_domain"] = bool(result["mx_records"])
        result["disposable"] = check_disposable(domain)
        result["free_provider"] = domain in FREE_PROVIDERS
        breaches, err = check_xposedornot(email)
        result["breach_count"] = len(breaches)
        result["breaches"] = [b["Name"] for b in breaches][:50]
        if err:
            result["breach_error"] = err
        return result

    def _check_ip(self, target: str) -> dict:
        from .ip_intel import resolve_to_ip, ip_scope, get_reverse_dns, get_geolocation, get_rdap
        ip = resolve_to_ip(target)
        if not ip:
            return {"ip": target, "error": "Could not resolve"}
        result: dict = {"ip": ip, "scope": ip_scope(ip), "hostname": ", ".join(get_reverse_dns(ip))}
        if result["scope"] == "public":
            g = get_geolocation(ip)
            result["geo"] = {"country": g.country, "region": g.region, "city": g.city,
                             "isp": g.isp, "org": g.org, "asn": g.asn, "latitude": g.lat,
                             "longitude": g.lon, "timezone": g.timezone, "proxy": g.proxy,
                             "hosting": g.hosting, "source": g.source}
            if g.error and not g.country:
                result["geo_error"] = g.error
            rd = get_rdap(ip)
            result["network"] = rd.get("name", "")
            result["abuse"] = rd.get("abuse", [])
        return result

    def _check_username(self, username: str) -> dict:
        from .username_checker import load_sites, check_single_site
        import concurrent.futures
        from . import net as _net
        sites = {k: v for k, v in load_sites().items() if not v.get("nsfw")}
        http = _net.session(retries=1)
        found, not_found, errors = [], [], []
        with concurrent.futures.ThreadPoolExecutor(max_workers=int(self.settings.get("max_threads", 20))) as ex:
            futs = [ex.submit(check_single_site, n, d, username, int(self.settings.get("request_timeout", 10)), http, True)
                    for n, d in sites.items()]
            for f in concurrent.futures.as_completed(futs):
                if self._stop:
                    break
                r = f.result()
                if r.found:
                    found.append({"site": r.site, "url": r.url})
                elif r.state in ("error", "blocked"):
                    errors.append({"site": r.site, "error": r.error})
                else:
                    not_found.append(r.site)
        return {"username": username, "sites_checked": len(sites), "found": sorted(found, key=lambda x: x["site"]),
                "not_found_count": len(not_found), "errors": errors, "found_count": len(found)}

    def _check_phone(self, phone: str) -> dict:
        from .phone_osint import analyze_phone
        r = analyze_phone(phone, self.settings.get("default_region", "US"))
        return {"phone": phone, "valid": r.is_valid, "possible": r.is_possible,
                "formatted": r.formatted_international, "e164": r.formatted_e164,
                "country": r.country_name, "region": r.area_description, "type": r.number_type,
                "carrier": r.carrier, "timezones": r.timezone, **({"error": r.error} if r.error else {})}


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
