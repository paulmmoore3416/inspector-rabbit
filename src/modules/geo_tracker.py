"""
Inspector Rabbit - GeoIP Tracker Module
Resolves IPs/domains and geolocates them using ip-api.com batch API (free, no key).
"""

import socket
import time
import re
from typing import List

import requests
from PyQt6.QtCore import QThread, pyqtSignal


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0.0.0 Safari/537.36'
}

IP_RE = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')

BATCH_URL = "http://ip-api.com/batch"
BATCH_FIELDS = (
    "query,status,country,countryCode,regionName,city,"
    "lat,lon,isp,org,as,timezone,message"
)


def _resolve(target: str) -> str:
    """Return the IPv4 address for target (resolve hostname if needed)."""
    target = target.strip()
    if IP_RE.match(target):
        return target
    try:
        return socket.gethostbyname(target)
    except Exception:
        return target  # return as-is; API will report failure


class GeoTrackThread(QThread):
    result   = pyqtSignal(dict)   # per-IP result dict
    progress = pyqtSignal(str)
    done     = pyqtSignal(list)   # list of all result dicts

    def __init__(self, targets: list[str], parent=None):
        super().__init__(parent)
        self._targets = targets

    def run(self):
        all_results: list[dict] = []

        # Resolve all targets to IPs
        resolved_pairs: list[tuple[str, str]] = []  # (original, ip)
        for target in self._targets:
            target = target.strip()
            if not target:
                continue
            self.progress.emit(f"Resolving {target}...")
            ip = _resolve(target)
            resolved_pairs.append((target, ip))
            self.progress.emit(f"  {target} → {ip}")

        if not resolved_pairs:
            self.done.emit([])
            return

        # ip-api.com allows max 100 per batch; process in chunks
        chunk_size = 100
        for chunk_start in range(0, len(resolved_pairs), chunk_size):
            chunk = resolved_pairs[chunk_start:chunk_start + chunk_size]
            payload = [{"query": ip, "fields": BATCH_FIELDS} for _, ip in chunk]

            self.progress.emit(
                f"Querying ip-api.com for {len(chunk)} address(es)..."
            )
            try:
                t0 = time.monotonic()
                resp = requests.post(
                    BATCH_URL,
                    json=payload,
                    headers=HEADERS,
                    timeout=15
                )
                elapsed_ms = int((time.monotonic() - t0) * 1000)
                data = resp.json()
            except Exception as exc:
                self.progress.emit(f"  ❌ ip-api.com error: {exc}")
                # Emit empty results for each target in the chunk
                for orig, ip in chunk:
                    result = {
                        "ip": ip,
                        "original_target": orig,
                        "country": "",
                        "country_code": "",
                        "region": "",
                        "city": "",
                        "lat": None,
                        "lon": None,
                        "isp": "",
                        "org": "",
                        "as_num": "",
                        "timezone": "",
                        "query_time_ms": 0,
                        "source": "ip-api.com",
                        "status": "error",
                        "error": str(exc),
                    }
                    all_results.append(result)
                    self.result.emit(result)
                continue

            for i, entry in enumerate(data):
                orig, ip = chunk[i] if i < len(chunk) else ("", "")
                status = entry.get("status", "fail")
                result = {
                    "ip": entry.get("query", ip),
                    "original_target": orig,
                    "country": entry.get("country", ""),
                    "country_code": entry.get("countryCode", ""),
                    "region": entry.get("regionName", ""),
                    "city": entry.get("city", ""),
                    "lat": entry.get("lat"),
                    "lon": entry.get("lon"),
                    "isp": entry.get("isp", ""),
                    "org": entry.get("org", ""),
                    "as_num": entry.get("as", ""),
                    "timezone": entry.get("timezone", ""),
                    "query_time_ms": elapsed_ms,
                    "source": "ip-api.com",
                    "status": status,
                    "error": entry.get("message", "") if status != "success" else "",
                }
                all_results.append(result)
                self.result.emit(result)
                city_str = f"{result['city']}, {result['country']}" if result['city'] else result['country']
                self.progress.emit(
                    f"  ✅ {result['ip']} → {city_str or 'Unknown'} ({result['isp']})"
                )

            # ip-api.com free tier: 45 requests/min; be polite between batches
            if chunk_start + chunk_size < len(resolved_pairs):
                time.sleep(0.5)

        self.progress.emit(f"GeoIP complete — {len(all_results)} result(s).")
        self.done.emit(all_results)
