"""
Inspector Rabbit - Network Diagnostics Module
Ping, traceroute, port scanning, banner grabbing, and rDNS.
"""

import re
import socket
import subprocess
from datetime import datetime, timezone

from PyQt6.QtCore import QThread, pyqtSignal


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

        # Resolve IP
        try:
            ip = socket.gethostbyname(target)
            self._result["ip"] = ip
            if ip != target:
                self._emit(f"Resolved {target} → {ip}", "info")
        except socket.gaierror as exc:
            self._emit(f"DNS resolution failed: {exc}", "error")
            ip = target

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
        try:
            # If the target looks like an IP, do rDNS; otherwise forward DNS
            socket.inet_aton(ip)
            hostname, _aliases, _addrs = socket.gethostbyaddr(ip)
            self._result["hostname"] = hostname
            self._emit(f"rDNS: {ip} → {hostname}", "success")
        except (socket.herror, socket.gaierror) as exc:
            self._emit(f"rDNS: no PTR record ({exc})", "warn")
        except OSError:
            # Not an IP — resolve forward
            try:
                addrs = socket.getaddrinfo(original_target, None)
                resolved = addrs[0][4][0] if addrs else "?"
                self._result["hostname"] = original_target
                self._emit(f"Forward DNS: {original_target} → {resolved}", "success")
            except Exception as exc2:
                self._emit(f"DNS lookup error: {exc2}", "error")

    def _do_ping(self, target: str):
        self._emit("Pinging target (4 packets)...", "info")
        try:
            proc = subprocess.run(
                ["ping", "-c", "4", "-W", "2", target],
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
                r"rtt\s+min/avg/max/mdev\s*=\s*[\d.]+/([\d.]+)/", output
            )
            if rtt_match:
                avg_ms = float(rtt_match.group(1))
                self._result["ping_ms"] = avg_ms
                self._emit(f"Average RTT: {avg_ms} ms", "success")

            # Parse TTL
            ttl_match = re.search(r"ttl=(\d+)", output, re.IGNORECASE)
            if ttl_match:
                self._result["ttl"] = int(ttl_match.group(1))

            # Parse packet loss
            loss_match = re.search(r"(\d+)%\s+packet loss", output)
            if loss_match:
                self._result["packet_loss"] = int(loss_match.group(1))
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
        try:
            proc = subprocess.run(
                ["traceroute", "-m", "20", "-w", "2", target],
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
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.0)
                result = sock.connect_ex((ip, port))
                sock.close()
                if result == 0:
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
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                sock.connect((ip, port))
                # Send a minimal probe to prompt a banner
                if port == 80:
                    sock.sendall(b"HEAD / HTTP/1.0\r\nHost: " + ip.encode() + b"\r\n\r\n")
                elif port == 443:
                    sock.close()
                    banners[port] = "(SSL — use HTTPS)"
                    self._emit(f"  Port {port}: (SSL)", "data")
                    continue
                else:
                    sock.sendall(b"\r\n")

                banner_bytes = b""
                try:
                    while True:
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
