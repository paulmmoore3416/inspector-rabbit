"""
Inspector Rabbit - Scan Detector
Counter-Surveillance Feature #3

Detects if external hosts are actively port-scanning or probing the
local machine while Inspector Rabbit is running an OSINT operation.
Uses connection-state heuristics and rate analysis — no raw sockets needed.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

import psutil
from PyQt6.QtCore import QThread, pyqtSignal


@dataclass
class ScanEvent:
    ip: str
    first_seen: str
    last_seen: str
    ports_probed: List[int] = field(default_factory=list)
    total_attempts: int = 0
    scan_type: str = 'unknown'   # port_scan, host_probe, syn_flood
    severity: str = 'medium'
    resolved_host: str = ''


class ScanDetector(QThread):
    """
    Counter-Surveillance Feature #3 — Active Scan Detector

    Watches for patterns consistent with an adversary scanning the
    Inspector Rabbit host:
      - Multi-port probing from a single IP in a short window
      - Rapid repeated connection attempts (SYN flood signature)
      - Sequential port walking
      - Connection attempts to unusual/closed local ports

    All detection is passive — analysing psutil connection snapshots.
    """

    scan_detected  = pyqtSignal(ScanEvent)
    stats_update   = pyqtSignal(dict)       # {total_scanners, total_events}
    log_event      = pyqtSignal(str)

    PORT_WINDOW_SECS  = 10
    PORT_THRESHOLD    = 3    # distinct ports within window = scan
    FLOOD_THRESHOLD   = 8    # connections from same IP in window = flood
    POLL_INTERVAL_MS  = 1500

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        # ip -> deque of (timestamp, port) tuples
        self._probe_log: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
        self._known_scanners: Dict[str, ScanEvent] = {}
        self._prev_conns: set = set()
        self._total_events = 0

    def run(self):
        self._running = True
        self.log_event.emit("🔭  Scan Detector active — watching for inbound probes")
        while self._running:
            try:
                self._analyse()
            except Exception as exc:
                self.log_event.emit(f"⚠️  Scan detector error: {exc}")
            self.msleep(self.POLL_INTERVAL_MS)

    def stop_detector(self):
        self._running = False
        self.quit()
        self.wait(2000)

    # ── Analysis pass ─────────────────────────────────────────────────────

    def _analyse(self):
        try:
            conns = psutil.net_connections(kind='tcp')
        except psutil.AccessDenied:
            return

        now = time.time()
        current = set()

        for c in conns:
            if not c.raddr:
                continue
            # We only care about connections INTO us
            key = (c.raddr.ip, c.laddr.port)
            current.add(key)

            if key in self._prev_conns:
                continue  # already processed

            rip = c.raddr.ip
            if rip in ('127.0.0.1', '::1'):
                continue

            # Record probe
            self._probe_log[rip].append((now, c.laddr.port))
            self._total_events += 1

            # Analyse this IP
            self._evaluate_ip(rip, now)

        self._prev_conns = current
        self.stats_update.emit({
            'total_scanners': len(self._known_scanners),
            'total_events': self._total_events,
            'active_ips': len(self._probe_log),
        })

    def _evaluate_ip(self, ip: str, now: float):
        # Filter probes within window
        recent = [
            (ts, port) for ts, port in self._probe_log[ip]
            if now - ts < self.PORT_WINDOW_SECS
        ]
        if not recent:
            return

        ports = {p for _, p in recent}
        count = len(recent)

        # Determine scan type
        scan_type = None
        severity = 'medium'

        if count >= self.FLOOD_THRESHOLD:
            scan_type = 'syn_flood'
            severity = 'high'
        elif len(ports) >= self.PORT_THRESHOLD:
            # Check for sequential walk
            sorted_ports = sorted(ports)
            sequential = all(
                sorted_ports[i+1] - sorted_ports[i] <= 2
                for i in range(len(sorted_ports)-1)
            ) if len(sorted_ports) > 2 else False
            scan_type = 'sequential_scan' if sequential else 'port_scan'
            severity = 'high' if sequential else 'medium'
        elif count >= 2:
            scan_type = 'host_probe'
            severity = 'low'

        if not scan_type:
            return

        if ip not in self._known_scanners:
            ev = ScanEvent(
                ip=ip,
                first_seen=datetime.now().strftime('%H:%M:%S'),
                last_seen=datetime.now().strftime('%H:%M:%S'),
                ports_probed=sorted(ports),
                total_attempts=count,
                scan_type=scan_type,
                severity=severity,
                resolved_host=self._resolve(ip),
            )
            self._known_scanners[ip] = ev
            self.scan_detected.emit(ev)
            self.log_event.emit(
                f"🔴 {'HIGH' if severity=='high' else 'MED'} — "
                f"{scan_type.upper()} from {ip} "
                f"({ev.resolved_host or 'unresolved'}) "
                f"ports={sorted(ports)} hits={count}"
            )
        else:
            # Update existing
            ev = self._known_scanners[ip]
            ev.last_seen = datetime.now().strftime('%H:%M:%S')
            ev.total_attempts = count
            ev.ports_probed = sorted(ports)

    @staticmethod
    def _resolve(ip: str) -> str:
        import socket
        try:
            return socket.gethostbyaddr(ip)[0]
        except Exception:
            return ''

    def get_scanners(self) -> List[ScanEvent]:
        return list(self._known_scanners.values())

    def clear(self):
        self._known_scanners.clear()
        self._probe_log.clear()
        self._total_events = 0
