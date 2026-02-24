"""
Inspector Rabbit - IP Intelligence Module
Geolocation, ASN, reverse DNS, blacklist checks, open ports, Shodan
"""

import socket
import time
import concurrent.futures
from typing import Dict, List, Optional
from dataclasses import dataclass, field

import requests
import dns.resolver
import dns.reversename
from PyQt6.QtCore import QObject, pyqtSignal, QThread


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0.0.0 Safari/537.36'
}

# Common RBL (Real-time Blackhole Lists) for spam/abuse checking
RBLS = [
    'zen.spamhaus.org',
    'bl.spamcop.net',
    'dnsbl.sorbs.net',
    'b.barracudacentral.org',
    'dnsbl-1.uceprotect.net',
    'psbl.surriel.com',
    'all.s5h.net',
    'ix.dnsbl.manitu.net',
]

# Common ports to scan
COMMON_PORTS = [
    (21, 'FTP'), (22, 'SSH'), (23, 'Telnet'), (25, 'SMTP'),
    (53, 'DNS'), (80, 'HTTP'), (110, 'POP3'), (143, 'IMAP'),
    (443, 'HTTPS'), (445, 'SMB'), (3306, 'MySQL'), (3389, 'RDP'),
    (5432, 'PostgreSQL'), (6379, 'Redis'), (8080, 'HTTP-Alt'),
    (8443, 'HTTPS-Alt'), (27017, 'MongoDB'), (9200, 'Elasticsearch'),
]


@dataclass
class IpGeoInfo:
    ip: str = ""
    country: str = ""
    country_code: str = ""
    region: str = ""
    city: str = ""
    lat: float = 0.0
    lon: float = 0.0
    isp: str = ""
    org: str = ""
    asn: str = ""
    timezone: str = ""
    mobile: bool = False
    proxy: bool = False
    hosting: bool = False
    error: str = ""


@dataclass
class IpIntelResult:
    target: str = ""
    resolved_ip: str = ""
    reverse_dns: List[str] = field(default_factory=list)
    geo: Optional[IpGeoInfo] = None
    open_ports: List[Dict] = field(default_factory=list)
    blacklists: Dict[str, bool] = field(default_factory=dict)
    shodan_data: Dict = field(default_factory=dict)
    whois_raw: str = ""
    abuse_contacts: List[str] = field(default_factory=list)
    error: str = ""


def resolve_to_ip(target: str) -> str:
    """Resolve hostname to IP if needed"""
    import re
    ip_re = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
    target = target.strip().lower()
    target = target.replace('https://', '').replace('http://', '').split('/')[0]
    if ip_re.match(target):
        return target
    try:
        return socket.gethostbyname(target)
    except Exception:
        return ""


def get_geolocation(ip: str) -> IpGeoInfo:
    """Get geolocation via ip-api.com (free, 45 req/min)"""
    geo = IpGeoInfo(ip=ip)
    try:
        resp = requests.get(
            f"http://ip-api.com/json/{ip}",
            params={'fields': 'status,message,country,countryCode,region,regionName,city,lat,lon,isp,org,as,timezone,mobile,proxy,hosting'},
            timeout=8
        )
        data = resp.json()
        if data.get('status') == 'success':
            geo.country = data.get('country', '')
            geo.country_code = data.get('countryCode', '')
            geo.region = data.get('regionName', '')
            geo.city = data.get('city', '')
            geo.lat = data.get('lat', 0.0)
            geo.lon = data.get('lon', 0.0)
            geo.isp = data.get('isp', '')
            geo.org = data.get('org', '')
            geo.asn = data.get('as', '')
            geo.timezone = data.get('timezone', '')
            geo.mobile = data.get('mobile', False)
            geo.proxy = data.get('proxy', False)
            geo.hosting = data.get('hosting', False)
        else:
            geo.error = data.get('message', 'Unknown error')
    except Exception as e:
        geo.error = str(e)
    return geo


def get_reverse_dns(ip: str) -> List[str]:
    results = []
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = 5
        addr = dns.reversename.from_address(ip)
        answers = resolver.resolve(addr, 'PTR')
        for r in answers:
            results.append(str(r))
    except Exception:
        pass
    return results


def check_blacklists(ip: str) -> Dict[str, bool]:
    """Check IP against DNS blacklists"""
    # Reverse the IP for DNSBL lookup
    reversed_ip = '.'.join(reversed(ip.split('.')))
    results = {}

    def check_rbl(rbl):
        try:
            query = f"{reversed_ip}.{rbl}"
            resolver = dns.resolver.Resolver()
            resolver.timeout = 3
            resolver.resolve(query, 'A')
            return rbl, True  # Listed
        except dns.resolver.NXDOMAIN:
            return rbl, False  # Not listed
        except Exception:
            return rbl, None  # Error/timeout

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(check_rbl, rbl): rbl for rbl in RBLS}
        for future in concurrent.futures.as_completed(futures):
            rbl, listed = future.result()
            if listed is not None:
                results[rbl] = listed

    return results


def scan_ports(ip: str, timeout: float = 1.0) -> List[Dict]:
    """Quick port scan of common ports"""
    open_ports = []

    def check_port(port, service):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            if result == 0:
                # Try banner grab
                banner = ""
                try:
                    sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock2.settimeout(2.0)
                    sock2.connect((ip, port))
                    banner = sock2.recv(1024).decode('utf-8', errors='ignore').strip()[:100]
                    sock2.close()
                except Exception:
                    pass
                return {'port': port, 'service': service, 'state': 'open', 'banner': banner}
        except Exception:
            pass
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        futures = [ex.submit(check_port, port, service) for port, service in COMMON_PORTS]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                open_ports.append(result)

    return sorted(open_ports, key=lambda x: x['port'])


def get_abuse_contacts(ip: str) -> List[str]:
    """Get abuse contact emails for an IP via RDAP"""
    contacts = []
    try:
        resp = requests.get(
            f"https://rdap.arin.net/registry/ip/{ip}",
            timeout=8, headers={'Accept': 'application/json'}
        )
        if resp.status_code == 200:
            data = resp.json()
            for entity in data.get('entities', []):
                for role in entity.get('roles', []):
                    if role == 'abuse':
                        for vcard in entity.get('vcardArray', [[], []])[1]:
                            if vcard[0] == 'email':
                                contacts.append(vcard[3])
    except Exception:
        pass
    return contacts


class IpIntelThread(QThread):
    progress = pyqtSignal(str)
    result_ready = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, target: str, shodan_api_key: str = "",
                 do_port_scan: bool = True, do_blacklists: bool = True):
        super().__init__()
        self.target = target.strip()
        self.shodan_api_key = shodan_api_key
        self.do_port_scan = do_port_scan
        self.do_blacklists = do_blacklists

    def run(self):
        result = IpIntelResult(target=self.target)
        try:
            self.progress.emit(f"Resolving {self.target}...")
            ip = resolve_to_ip(self.target)
            if not ip:
                result.error = f"Could not resolve {self.target} to an IP"
                self.result_ready.emit(result)
                return
            result.resolved_ip = ip

            self.progress.emit(f"Reverse DNS for {ip}...")
            result.reverse_dns = get_reverse_dns(ip)

            self.progress.emit(f"Geolocation lookup...")
            result.geo = get_geolocation(ip)

            self.progress.emit(f"Fetching abuse contacts...")
            result.abuse_contacts = get_abuse_contacts(ip)

            if self.do_blacklists:
                self.progress.emit(f"Checking {len(RBLS)} blacklists...")
                result.blacklists = check_blacklists(ip)

            if self.do_port_scan:
                self.progress.emit(f"Scanning {len(COMMON_PORTS)} common ports...")
                result.open_ports = scan_ports(ip)

            if self.shodan_api_key:
                self.progress.emit(f"Querying Shodan...")
                try:
                    import shodan as shodan_lib
                    api = shodan_lib.Shodan(self.shodan_api_key)
                    host = api.host(ip)
                    result.shodan_data = {
                        'ports': host.get('ports', []),
                        'vulns': list(host.get('vulns', {}).keys()),
                        'os': host.get('os', ''),
                        'tags': host.get('tags', []),
                        'last_update': host.get('last_update', ''),
                        'hostnames': host.get('hostnames', []),
                        'services': [
                            {
                                'port': s.get('port'),
                                'transport': s.get('transport', 'tcp'),
                                'product': s.get('product', ''),
                                'version': s.get('version', ''),
                                'banner': s.get('data', '')[:100],
                            }
                            for s in host.get('data', [])[:10]
                        ]
                    }
                except Exception as e:
                    result.shodan_data = {'error': str(e)}

            self.progress.emit("IP intelligence complete.")
            self.result_ready.emit(result)

        except Exception as e:
            self.error.emit(str(e))
