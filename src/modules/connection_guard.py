"""
Inspector Rabbit - Connection Guard
Monitors all network connections in real-time, detects inbound probes,
tracks suspicious activity, and provides kill-switch functionality.
"""

import socket
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set

import psutil
from PyQt6.QtCore import QThread, pyqtSignal


@dataclass
class ConnRecord:
    key: str
    timestamp: str
    laddr: str
    lport: int
    raddr: str
    rport: int
    status: str
    pid: int
    process: str
    risk: str = 'low'
    inbound: bool = False


class ConnectionGuard(QThread):
    """
    Counter-Surveillance Feature #1 — Connection Guard

    Continuously monitors all active TCP/UDP network connections.
    Detects new connections formed during a scan session, flags inbound
    probes, identifies suspicious destinations, and enables one-click
    kill of any connection.
    """

    new_connection    = pyqtSignal(dict)
    connection_closed = pyqtSignal(str)   # emits key
    threat_detected   = pyqtSignal(dict)
    stats_update      = pyqtSignal(dict)
    log_event         = pyqtSignal(str)

    # Ports that are unusual for an OSINT tool to receive on
    INBOUND_SUSPICIOUS = {22, 23, 25, 80, 135, 139, 443, 445, 1433, 3306, 3389, 5432, 6379}
    # Destination ports considered high-risk when connecting out unexpectedly
    OUTBOUND_SUSPICIOUS = {4444, 5555, 6666, 7777, 8888, 9999, 31337, 1337}
    SCAN_WINDOW_SECS = 8
    SCAN_PORT_THRESHOLD = 3  # distinct ports from same remote = scan

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._known: Set[str] = set()
        self._inbound_map: Dict[str, List[float]] = {}   # ip -> timestamps
        self._inbound_ports: Dict[str, Set[int]] = {}    # ip -> ports seen
        self._detected: Dict[str, dict] = {}
        self._local_ips = self._collect_local_ips()

    # ── Main loop ──────────────────────────────────────────────────────────

    def run(self):
        self._running = True
        self.log_event.emit("🛡️  Connection Guard initialised — watching all sockets")
        while self._running:
            try:
                self._sweep()
            except Exception as exc:
                self.log_event.emit(f"⚠️  Guard sweep error: {exc}")
            self.msleep(1200)

    def stop_guard(self):
        self._running = False
        self.quit()
        self.wait(2000)

    # ── Sweep ──────────────────────────────────────────────────────────────

    def _sweep(self):
        try:
            conns = psutil.net_connections(kind='inet')
        except psutil.AccessDenied:
            conns = []

        current: Set[str] = set()
        inbound_count = 0

        for c in conns:
            if not c.raddr:
                continue
            key = f"{c.laddr.ip}:{c.laddr.port}-{c.raddr.ip}:{c.raddr.port}"
            current.add(key)

            if key not in self._known:
                rec = self._build_record(c, key)
                self.new_connection.emit(rec)

                if rec['inbound']:
                    inbound_count += 1
                    self._track_inbound(c.raddr.ip, c.laddr.port)

                # Suspicious outbound port
                if c.raddr.port in self.OUTBOUND_SUSPICIOUS:
                    self.threat_detected.emit({
                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                        'ip': c.raddr.ip,
                        'port': c.raddr.port,
                        'type': 'SUSPICIOUS_OUTBOUND',
                        'severity': 'high',
                        'detail': f'Outbound to unusual port {c.raddr.port} — possible C2',
                    })

        # Closed connections
        for key in self._known - current:
            self.connection_closed.emit(key)

        self._known = current
        self.stats_update.emit({
            'active': len(current),
            'inbound': inbound_count,
            'threats': len(self._detected),
        })

    # ── Inbound tracking ───────────────────────────────────────────────────

    def _track_inbound(self, remote_ip: str, local_port: int):
        now = time.time()
        self._inbound_map.setdefault(remote_ip, [])
        self._inbound_ports.setdefault(remote_ip, set())
        self._inbound_map[remote_ip].append(now)
        self._inbound_ports[remote_ip].add(local_port)

        # Prune old timestamps
        self._inbound_map[remote_ip] = [
            t for t in self._inbound_map[remote_ip]
            if now - t < self.SCAN_WINDOW_SECS
        ]

        distinct_ports = len(self._inbound_ports[remote_ip])
        recent_hits = len(self._inbound_map[remote_ip])

        if distinct_ports >= self.SCAN_PORT_THRESHOLD and remote_ip not in self._detected:
            self._detected[remote_ip] = {
                'ip': remote_ip,
                'first_seen': datetime.now().strftime('%H:%M:%S'),
                'ports_probed': list(self._inbound_ports[remote_ip]),
                'hits': recent_hits,
            }
            self.threat_detected.emit({
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'ip': remote_ip,
                'type': 'PORT_SCAN_INBOUND',
                'severity': 'high',
                'detail': (f'Port scan detected from {remote_ip} — '
                           f'{distinct_ports} ports probed in {self.SCAN_WINDOW_SECS}s'),
            })
            self.log_event.emit(
                f"🔴 SCAN DETECTED from {remote_ip} — "
                f"{distinct_ports} ports: {sorted(self._inbound_ports[remote_ip])}"
            )
        elif recent_hits >= 2 and remote_ip not in self._detected:
            self.threat_detected.emit({
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'ip': remote_ip,
                'type': 'INBOUND_PROBE',
                'severity': 'medium',
                'detail': f'Repeated inbound probe from {remote_ip} on port {local_port}',
            })

    # ── Kill switch ────────────────────────────────────────────────────────

    def kill_connection(self, raddr: str, rport: int) -> tuple[bool, str]:
        """
        Forcibly terminate a TCP connection.
        Tries `ss -K` first (Linux kernel kill), then process-level SIGTERM.
        Returns (success, message).
        """
        # Method 1: ss -K (Linux iproute2 — no root needed for own connections)
        try:
            result = subprocess.run(
                ['ss', '-K', f'dst {raddr}', f'dport = {rport}'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                self.log_event.emit(f"⚡ Kill: connection to {raddr}:{rport} terminated (ss -K)")
                return True, f"Connection to {raddr}:{rport} killed via ss"
        except FileNotFoundError:
            pass
        except Exception as exc:
            pass

        # Method 2: Find and SIGTERM the owning process
        try:
            for c in psutil.net_connections(kind='inet'):
                if c.raddr and c.raddr.ip == raddr and c.raddr.port == rport:
                    if c.pid:
                        proc = psutil.Process(c.pid)
                        pname = proc.name()
                        # Only kill if it's NOT our own python process
                        if 'python' not in pname.lower() and 'inspector' not in pname.lower():
                            proc.terminate()
                            self.log_event.emit(
                                f"⚡ Kill: process {pname} (PID {c.pid}) terminated"
                            )
                            return True, f"Process {pname} (PID {c.pid}) terminated"
                        else:
                            return False, "Refusing to kill Inspector Rabbit's own process"
        except Exception as exc:
            return False, f"Kill failed: {exc}"

        return False, f"No active connection found to {raddr}:{rport}"

    # ── Helpers ────────────────────────────────────────────────────────────

    def _build_record(self, c, key: str) -> dict:
        try:
            proc_name = psutil.Process(c.pid).name() if c.pid else '—'
        except Exception:
            proc_name = '—'

        is_inbound = (
            c.raddr.ip not in self._local_ips
            and c.laddr.ip in self._local_ips
            and c.status in ('ESTABLISHED', 'SYN_RECV', 'LISTEN')
        )
        risk = 'high' if (
            c.laddr.port in self.INBOUND_SUSPICIOUS or
            c.raddr.port in self.OUTBOUND_SUSPICIOUS
        ) else ('medium' if is_inbound else 'low')

        return {
            'key': key,
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'laddr': c.laddr.ip,
            'lport': c.laddr.port,
            'raddr': c.raddr.ip,
            'rport': c.raddr.port,
            'status': c.status,
            'pid': c.pid or 0,
            'process': proc_name,
            'risk': risk,
            'inbound': is_inbound,
        }

    @staticmethod
    def _collect_local_ips() -> Set[str]:
        ips = {'127.0.0.1', '::1', '0.0.0.0'}
        try:
            for _iface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        ips.add(addr.address)
        except Exception:
            pass
        return ips

    def get_detected_scanners(self) -> dict:
        return dict(self._detected)
