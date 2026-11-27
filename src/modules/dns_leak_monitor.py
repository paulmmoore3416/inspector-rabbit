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
import random
import re
import shutil
import socket
import string
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Optional

from PyQt6.QtCore import QThread, pyqtSignal

from . import net


RESOLV_CONF = '/etc/resolv.conf'
KNOWN_TRUSTED_DNS = {
    '1.1.1.1', '1.0.0.1', '2606:4700:4700::1111', '2606:4700:4700::1001',   # Cloudflare
    '8.8.8.8', '8.8.4.4', '2001:4860:4860::8888', '2001:4860:4860::8844',   # Google
    '9.9.9.9', '149.112.112.112', '2620:fe::fe', '2620:fe::9',              # Quad9
    '208.67.222.222', '208.67.220.220',                                     # OpenDNS
    '194.242.2.2', '10.64.0.1',                                             # Mullvad
    '127.0.0.1', '127.0.0.53', '127.0.0.54', '::1',                         # Local stub resolvers
    '100.100.100.100', 'fd7a:115c:a1e0::53',                                # Tailscale MagicDNS
}

# Hostnames whose addresses are fixed anycast IPs. If the system resolver
# returns anything else for them, the answer was rewritten in transit.
CANARY_HOSTS = [
    ('one.one.one.one', {'1.1.1.1', '1.0.0.1'}),
    ('dns.google',      {'8.8.8.8', '8.8.4.4'}),
    ('dns.quad9.net',   {'9.9.9.9', '149.112.112.112'}),
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
        if any(r.startswith('127.0.0.5') for r in self._last_resolvers):
            ups = self._resolvectl_upstreams()
            if ups:
                self.log_event.emit(f"📋  systemd-resolved upstreams: {', '.join(ups)}")
                self._last_resolvers = self._last_resolvers + [u for u in ups if u not in self._last_resolvers]
        if net.proxy_active():
            self.log_event.emit("🧅  App lookups use DNS-over-HTTPS through the proxy; "
                                "the system resolver below is only used by other programs.")
        self._check_resolvers(self._last_resolvers)
        self._check_nxdomain_hijack()

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
            if r in ('100.100.100.100', 'fd7a:115c:a1e0::53'):
                self.log_event.emit("🟢  Tailscale MagicDNS resolver (100.100.100.100) — trusted")
                continue
            if r not in KNOWN_TRUSTED_DNS:
                try:
                    addr = ipaddress.ip_address(r.split('%')[0])
                    if net.is_tailscale(str(addr)):
                        self.log_event.emit(f"🟢  Tailnet resolver {r}")
                        continue
                    if addr.is_private or addr.is_loopback or addr.is_link_local:
                        self.log_event.emit(f"🟡  Local-network resolver {r} (router/ISP gateway) — "
                                            f"it sees every domain you look up")
                        continue
                except ValueError:
                    pass
                self._anomaly_count += 1
                self.leak_detected.emit({
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'type': 'UNKNOWN_RESOLVER',
                    'severity': 'low',
                    'detail': (f'Resolver {r} is not a well-known public DNS service (usually your ISP). '
                               f'It can log every domain you look up — use Tor/VPN DNS for investigations.'),
                })
                self.log_event.emit(f"🟡  Resolver {r} is not a known public DNS service (likely ISP)")

    # ── Canary verification ────────────────────────────────────────────────

    def _check_nxdomain_hijack(self):
        """A random non-existent name must fail. If it resolves, the resolver rewrites NXDOMAIN."""
        label = 'ir-nx-' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))
        try:
            ip = socket.gethostbyname(f"{label}.com")
        except socket.gaierror:
            self.log_event.emit("🟢  NXDOMAIN check passed (resolver does not hijack typos)")
            return
        self._anomaly_count += 1
        self.leak_detected.emit({
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'type': 'NXDOMAIN_HIJACK', 'severity': 'medium',
            'detail': f'Non-existent domain resolved to {ip} — resolver (ISP/router) rewrites failed lookups',
        })
        self.log_event.emit(f"🟡  NXDOMAIN hijacking: {label}.com → {ip}")

    def _verify_canaries(self):
        for host, expected in CANARY_HOSTS:
            t0 = time.time()
            try:
                infos = socket.getaddrinfo(host, None, socket.AF_INET)
                resolved = sorted({i[4][0] for i in infos})
                latency_ms = (time.time() - t0) * 1000
                ok = bool(resolved) and set(resolved) <= expected
                result = {
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'host': host,
                    'resolved_ip': ', '.join(resolved),
                    'expected': ', '.join(sorted(expected)),
                    'ok': ok,
                    'latency_ms': round(latency_ms, 1),
                }
                self._dns_log.append(result)
                self.dns_check_result.emit(result)
                if not ok:
                    self._anomaly_count += 1
                    self.leak_detected.emit({
                        'timestamp': result['timestamp'], 'type': 'DNS_SPOOFING', 'severity': 'high',
                        'detail': (f'{host} resolved to {result["resolved_ip"]} but its address is fixed '
                                   f'({result["expected"]}) — DNS answers are being rewritten'),
                    })
                    self.log_event.emit(f"🔴 DNS SPOOF: {host} → {result['resolved_ip']}")
                if latency_ms > self.LATENCY_WARN_MS:
                    self.leak_detected.emit({
                        'timestamp': result['timestamp'], 'type': 'DNS_SLOW_RESPONSE', 'severity': 'low',
                        'detail': f'DNS for {host} took {latency_ms:.0f}ms (slow resolver or network)',
                    })
            except socket.gaierror as exc:
                self.log_event.emit(f"⚠️  DNS canary failed for {host}: {exc}")

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _resolvectl_upstreams() -> List[str]:
        """Real upstream servers when /etc/resolv.conf points at systemd-resolved."""
        if not shutil.which('resolvectl'):
            return []
        try:
            out = subprocess.run(['resolvectl', 'dns'], capture_output=True, text=True, timeout=4).stdout
        except Exception:
            return []
        ips = []
        for line in out.splitlines():
            for tok in line.split(':', 1)[-1].split():
                tok = tok.split('#')[0].strip('[]')
                try:
                    ipaddress.ip_address(tok.split('%')[0])
                    if tok not in ips:
                        ips.append(tok)
                except ValueError:
                    pass
        return ips

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
