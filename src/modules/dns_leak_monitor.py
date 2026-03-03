"""
Inspector Rabbit - DNS Leak Monitor
Counter-Surveillance Feature #4

Monitors DNS resolver configuration for tampering, detects DNS-based
surveillance (resolver hijacking, unusual lookup patterns), and warns
when DNS responses may be intercepted or manipulated.
"""

import hashlib
import ipaddress
import os
import socket
import time
from datetime import datetime
from typing import Dict, List, Optional

from PyQt6.QtCore import QThread, pyqtSignal


RESOLV_CONF = '/etc/resolv.conf'
KNOWN_TRUSTED_DNS = {
    '1.1.1.1', '1.0.0.1',             # Cloudflare
    '8.8.8.8', '8.8.4.4',             # Google
    '9.9.9.9', '149.112.112.112',      # Quad9
    '208.67.222.222', '208.67.220.220',# OpenDNS
    '127.0.0.1', '127.0.0.53',         # Local (systemd-resolved, dnsmasq)
    '192.168.1.1', '192.168.0.1',      # Common home router
}

CANARY_HOSTS = [
    ('example.com',     '93.184.216.34'),
    ('google.com',      None),          # Just check it resolves
    ('cloudflare.com',  None),
]


class DNSLeakMonitor(QThread):
    """
    Counter-Surveillance Feature #4 — DNS Leak & Hijack Monitor

    Polls /etc/resolv.conf for changes (resolver hijacking indicator).
    Verifies that known reference domains resolve to expected IPs.
    Detects signs of DNS interception (NXDOMAIN manipulation, slow
    response indicating DNS proxy in path, unexpected resolver IPs).
    """

    resolver_changed   = pyqtSignal(dict)   # {old, new, timestamp}
    leak_detected      = pyqtSignal(dict)   # {type, detail, severity}
    dns_check_result   = pyqtSignal(dict)   # {host, resolved_ip, expected, ok, latency_ms}
    log_event          = pyqtSignal(str)
    stats_update       = pyqtSignal(dict)

    CHECK_INTERVAL_SECS = 15
    LATENCY_WARN_MS     = 2000   # DNS response > 2s is suspicious

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._last_resolv_hash = ''
        self._last_resolvers: List[str] = []
        self._check_count = 0
        self._anomaly_count = 0
        self._dns_log: List[dict] = []

    def run(self):
        self._running = True
        self.log_event.emit("🔍  DNS Leak Monitor active — watching resolver configuration")
        self._snapshot_resolv()
        while self._running:
            try:
                self._check_resolv()
                self._verify_canaries()
                self._check_count += 1
                self.stats_update.emit({
                    'checks': self._check_count,
                    'anomalies': self._anomaly_count,
                    'resolvers': self._last_resolvers,
                })
            except Exception as exc:
                self.log_event.emit(f"⚠️  DNS monitor error: {exc}")
            self.msleep(self.CHECK_INTERVAL_SECS * 1000)

    def stop_monitor(self):
        self._running = False
        self.quit()
        self.wait(2000)

    # ── Resolver config monitoring ─────────────────────────────────────────

    def _snapshot_resolv(self):
        content = self._read_resolv()
        self._last_resolv_hash = hashlib.md5(content.encode()).hexdigest()
        self._last_resolvers = self._parse_nameservers(content)
        self.log_event.emit(
            f"📋  DNS resolvers: {', '.join(self._last_resolvers) or 'none detected'}"
        )
        self._check_resolvers(self._last_resolvers)

    def _check_resolv(self):
        content = self._read_resolv()
        new_hash = hashlib.md5(content.encode()).hexdigest()

        if new_hash != self._last_resolv_hash:
            old_resolvers = list(self._last_resolvers)
            new_resolvers = self._parse_nameservers(content)
            self._last_resolv_hash = new_hash
            self._last_resolvers = new_resolvers
            self._anomaly_count += 1

            ts = datetime.now().strftime('%H:%M:%S')
            self.resolver_changed.emit({
                'timestamp': ts,
                'old': old_resolvers,
                'new': new_resolvers,
            })
            self.leak_detected.emit({
                'timestamp': ts,
                'type': 'RESOLVER_CHANGED',
                'severity': 'high',
                'detail': (f'DNS resolver config changed! '
                           f'Old: {old_resolvers} → New: {new_resolvers}'),
            })
            self.log_event.emit(
                f"🔴 DNS CONFIG CHANGED — old={old_resolvers} new={new_resolvers}"
            )
            self._check_resolvers(new_resolvers)

    def _check_resolvers(self, resolvers: List[str]):
        for r in resolvers:
            if r not in KNOWN_TRUSTED_DNS:
                # Check if it's a private/local IP first
                try:
                    addr = ipaddress.ip_address(r)
                    if addr.is_private or addr.is_loopback or addr.is_link_local:
                        self.log_event.emit(f"🟡  Unknown private resolver: {r} — monitor closely")
                        continue
                except ValueError:
                    pass
                self._anomaly_count += 1
                self.leak_detected.emit({
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'type': 'UNKNOWN_RESOLVER',
                    'severity': 'medium',
                    'detail': f'Unrecognised DNS resolver: {r} — possible interception point',
                })
                self.log_event.emit(f"🟡  Unrecognised resolver {r} — not in trusted list")

    # ── Canary verification ────────────────────────────────────────────────

    def _verify_canaries(self):
        for host, expected_ip in CANARY_HOSTS:
            t0 = time.time()
            try:
                resolved = socket.gethostbyname(host)
                latency_ms = (time.time() - t0) * 1000
                ok = (expected_ip is None) or (resolved == expected_ip)

                result = {
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'host': host,
                    'resolved_ip': resolved,
                    'expected': expected_ip or 'any',
                    'ok': ok,
                    'latency_ms': round(latency_ms, 1),
                }
                self._dns_log.append(result)
                self.dns_check_result.emit(result)

                if not ok:
                    self._anomaly_count += 1
                    self.leak_detected.emit({
                        'timestamp': result['timestamp'],
                        'type': 'DNS_SPOOFING',
                        'severity': 'high',
                        'detail': (f'{host} resolved to {resolved} '
                                   f'(expected {expected_ip}) — possible DNS spoofing'),
                    })
                    self.log_event.emit(
                        f"🔴 DNS SPOOF: {host} → {resolved} (expected {expected_ip})"
                    )

                if latency_ms > self.LATENCY_WARN_MS:
                    self.leak_detected.emit({
                        'timestamp': result['timestamp'],
                        'type': 'DNS_SLOW_RESPONSE',
                        'severity': 'medium',
                        'detail': (f'DNS for {host} took {latency_ms:.0f}ms — '
                                   f'possible transparent proxy in path'),
                    })
                    self.log_event.emit(
                        f"🟡  Slow DNS: {host} took {latency_ms:.0f}ms (>{self.LATENCY_WARN_MS}ms)"
                    )

            except socket.gaierror as exc:
                self.log_event.emit(f"⚠️  DNS canary failed for {host}: {exc}")

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _read_resolv() -> str:
        try:
            with open(RESOLV_CONF, 'r') as f:
                return f.read()
        except Exception:
            return ''

    @staticmethod
    def _parse_nameservers(content: str) -> List[str]:
        servers = []
        for line in content.splitlines():
            line = line.strip()
            if line.startswith('nameserver'):
                parts = line.split()
                if len(parts) >= 2:
                    servers.append(parts[1])
        return servers

    def get_dns_log(self) -> List[dict]:
        return list(self._dns_log[-200:])

    def get_current_resolvers(self) -> List[str]:
        return list(self._last_resolvers)
