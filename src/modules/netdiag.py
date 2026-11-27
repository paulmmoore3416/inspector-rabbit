"""
Inspector Rabbit - Network Diagnostics Module
Ping, traceroute, port scanning, banner grabbing, and rDNS.
"""

import re
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone

from PyQt6.QtCore import QThread, pyqtSignal

from . import net

_WIN = sys.platform.startswith('win')


SCAN_PORTS = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 3306, 3389, 8080, 8443]

PORT_NAMES = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    143: "IMAP",
    443: "HTTPS",
    445: "SMB",
    3306: "MySQL",
    3389: "RDP",
    8080: "HTTP-Alt",
    8443: "HTTPS-Alt",
}


class NetDiagThread(QThread):
    line_output = pyqtSignal(str, str)   # (text, kind)
    result_ready = pyqtSignal(dict)
    done = pyqtSignal()

    def __init__(self, target: str, tests: list):
        super().__init__()
        self.target = target.strip()
        self.tests = tests
        self._result = {
            "target": self.target,
            "ping_ms": None,
            "ttl": None,
            "packet_loss": None,
            "traceroute_hops": [],
            "open_ports": [],
            "banners": {},
            "hostname": "",
            "ip": "",
        }

    def run(self):
        target = self.target

        target = net.clean_host(target)
        self.target = target
        if net.proxy_active():
            self._emit(f"Network: {net.describe()}", "info")
        ip = net.resolve_host(target)
        if ip:
            self._result["ip"] = ip
            if ip != target:
                self._emit(f"Resolved {target} → {ip}", "info")
        else:
            self._emit(f"DNS resolution failed for {target}", "error")
            self.result_ready.emit(self._result)
            self.done.emit()
            return

        # rDNS
        if "rdns" in self.tests:
            self._do_rdns(ip, target)

        # Ping
        if "ping" in self.tests:
            self._do_ping(target)

        # Traceroute
        if "traceroute" in self.tests:
            self._do_traceroute(target)

        # Port scan
        open_ports = []
        if "portscan" in self.tests:
            open_ports = self._do_portscan(ip)
            self._result["open_ports"] = open_ports

        # Banner grab
        if "banner" in self.tests and open_ports:
            self._do_banner_grab(ip, open_ports)

        self.result_ready.emit(self._result)
        self._emit("Diagnostics complete.", "success")
        self.done.emit()

    # ------------------------------------------------------------------
    # Individual test methods
    # ------------------------------------------------------------------

    def _do_rdns(self, ip: str, original_target: str):
        self._emit("Running reverse DNS lookup...", "info")
        names = net.reverse_dns(ip)
        if names:
            self._result["hostname"] = names[0]
            for n in names:
                self._emit(f"rDNS: {ip} → {n}", "success")
        else:
            self._emit(f"rDNS: no PTR record for {ip}", "warn")

    def _do_ping(self, target: str):
        self._emit("Pinging target (4 packets)...", "info")
        if not net.direct_allowed():
            self._emit("Ping skipped: ICMP cannot go through the proxy and would reveal your IP "
                       "(enable 'Allow direct traffic when proxied' to run it).", "warn")
            return
        cmd = ["ping", "-n", "4", "-w", "2000", target] if _WIN else ["ping", "-c", "4", "-W", "2", target]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
            )
            output = proc.stdout + proc.stderr
            for line in output.splitlines():
                if line.strip():
                    self._emit(line, "data")

            # Parse avg RTT
            rtt_match = re.search(
                r"(?:rtt|round-trip)\s+min/avg/max/(?:mdev|stddev)\s*=\s*[\d.]+/([\d.]+)/", output
            ) or re.search(r"Average = (\d+)ms", output)
            if rtt_match:
                avg_ms = float(rtt_match.group(1))
                self._result["ping_ms"] = avg_ms
                self._emit(f"Average RTT: {avg_ms} ms", "success")

            # Parse TTL
            ttl_match = re.search(r"ttl=(\d+)", output, re.IGNORECASE)
            if ttl_match:
                self._result["ttl"] = int(ttl_match.group(1))

            # Parse packet loss
            loss_match = re.search(r"(\d+(?:\.\d+)?)%\s+(?:packet )?loss", output)
            if loss_match:
                self._result["packet_loss"] = int(float(loss_match.group(1)))
                loss_pct = self._result["packet_loss"]
                kind = "success" if loss_pct == 0 else ("warn" if loss_pct < 50 else "error")
                self._emit(f"Packet loss: {loss_pct}%", kind)

        except subprocess.TimeoutExpired:
            self._emit("Ping timed out.", "error")
        except FileNotFoundError:
            self._emit("ping command not found.", "error")
        except Exception as exc:
            self._emit(f"Ping error: {exc}", "error")

    def _do_traceroute(self, target: str):
        self._emit("Running traceroute (max 20 hops)...", "info")
        hops = []
        if not net.direct_allowed():
            self._emit("Traceroute skipped: it cannot be proxied and would reveal your IP.", "warn")
            return
        if _WIN:
            cmd = ["tracert", "-h", "20", "-w", "2000", target]
        elif shutil.which("traceroute"):
            cmd = ["traceroute", "-m", "20", "-w", "2", target]
        elif shutil.which("tracepath"):
            cmd = ["tracepath", "-m", "20", target]
        else:
            self._emit("traceroute/tracepath not installed (sudo apt install traceroute).", "error")
            return
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            for line in proc.stdout.splitlines():
                stripped = line.strip()
                if stripped:
                    hops.append(stripped)
                    self._emit(stripped, "data")
            self._result["traceroute_hops"] = hops
            self._emit(f"Traceroute complete: {len(hops)} hops", "success")
        except subprocess.TimeoutExpired:
            self._emit("Traceroute timed out.", "error")
        except FileNotFoundError:
            self._emit("traceroute command not found.", "error")
        except Exception as exc:
            self._emit(f"Traceroute error: {exc}", "error")

    def _do_portscan(self, ip: str) -> list:
        self._emit(f"Scanning {len(SCAN_PORTS)} ports on {ip}...", "info")
        open_ports = []
        for port in SCAN_PORTS:
            try:
                if net.tcp_port_open(ip, port, 2.0 if net.proxy_active() else 1.0):
                    proto = PORT_NAMES.get(port, "?")
                    open_ports.append(port)
                    self._emit(f"  OPEN  {port:5d}/tcp  {proto}", "success")
                else:
                    proto = PORT_NAMES.get(port, "?")
                    self._emit(f"  closed {port:5d}/tcp  {proto}", "data")
            except Exception as exc:
                self._emit(f"  Error scanning port {port}: {exc}", "error")

        self._emit(
            f"Port scan complete: {len(open_ports)}/{len(SCAN_PORTS)} open",
            "success" if open_ports else "warn",
        )
        return open_ports

    def _do_banner_grab(self, ip: str, open_ports: list):
        self._emit("Grabbing banners from open ports...", "info")
        banners = {}
        for port in open_ports:
            try:
                sock = net.create_connection((ip, port), timeout=4.0)
                sock.settimeout(2.5)
                # Send a minimal probe to prompt a banner
                if port in (80, 8080):
                    sock.sendall(b"HEAD / HTTP/1.0\r\nHost: " + ip.encode() + b"\r\n\r\n")
                elif port in (443, 8443):
                    import ssl as _ssl
                    ctx = _ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = _ssl.CERT_NONE
                    tls = ctx.wrap_socket(sock, server_hostname=self.target)
                    tls.sendall(b"HEAD / HTTP/1.0\r\nHost: " + self.target.encode() + b"\r\n\r\n")
                    sock = tls
                banner_bytes = b""
                if port not in (80, 443, 8080, 8443):
                    # Most services (SSH, FTP, SMTP, POP, IMAP) speak first
                    try:
                        sock.settimeout(2.5)
                        banner_bytes = sock.recv(1024)
                    except Exception:
                        banner_bytes = b""
                    if not banner_bytes:
                        try:
                            sock.sendall(b"\r\n")
                        except Exception:
                            pass

                try:
                    while not banner_bytes or port in (80, 443, 8080, 8443):
                        chunk = sock.recv(1024)
                        if not chunk:
                            break
                        banner_bytes += chunk
                        if len(banner_bytes) > 4096:
                            break
                except Exception:
                    pass
                sock.close()

                banner_text = banner_bytes.decode("utf-8", errors="replace").strip()
                banner_short = banner_text[:200].replace("\r", "").replace("\n", " | ")
                if banner_short:
                    banners[port] = banner_short
                    self._emit(f"  Port {port} banner: {banner_short[:80]}", "data")
                else:
                    self._emit(f"  Port {port}: no banner", "data")

            except Exception as exc:
                self._emit(f"  Banner grab port {port}: {exc}", "warn")

        self._result["banners"] = banners

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _emit(self, text: str, kind: str = "info"):
        self.line_output.emit(text, kind)
