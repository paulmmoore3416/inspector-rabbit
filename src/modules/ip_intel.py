"""
Inspector Rabbit - IP Intelligence Module
Geolocation, ASN, reverse DNS, RDAP ownership/abuse contacts, DNS blacklist
checks (with resolver-refusal detection), TCP port checks, and Shodan /
Shodan InternetDB exposure data. IPv4 and IPv6.
"""

import ipaddress
import concurrent.futures
from typing import Dict, List, Optional
from dataclasses import dataclass, field

import requests
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from . import net

HEADERS = {'User-Agent': net.TOOL_UA}

# DNSBLs that answer public queries. (SORBS shut down in 2024.)
RBLS = [
    'zen.spamhaus.org',
    'bl.spamcop.net',
    'b.barracudacentral.org',
    'dnsbl-1.uceprotect.net',
    'psbl.surriel.com',
    'all.s5h.net',
    'ix.dnsbl.manitu.net',
    'dnsbl.dronebl.org',
]

COMMON_PORTS = [
    (21, 'FTP'), (22, 'SSH'), (23, 'Telnet'), (25, 'SMTP'),
    (53, 'DNS'), (80, 'HTTP'), (110, 'POP3'), (143, 'IMAP'),
    (443, 'HTTPS'), (445, 'SMB'), (993, 'IMAPS'), (995, 'POP3S'),
    (1433, 'MSSQL'), (3306, 'MySQL'), (3389, 'RDP'), (5432, 'PostgreSQL'),
    (5900, 'VNC'), (6379, 'Redis'), (8080, 'HTTP-Alt'), (8443, 'HTTPS-Alt'),
    (9200, 'Elasticsearch'), (27017, 'MongoDB'),
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
    source: str = ""
    error: str = ""


@dataclass
class IpIntelResult:
    target: str = ""
    resolved_ip: str = ""
    ip_version: int = 4
    ip_scope: str = ""
    reverse_dns: List[str] = field(default_factory=list)
    geo: Optional[IpGeoInfo] = None
    open_ports: List[Dict] = field(default_factory=list)
    blacklists: Dict[str, bool] = field(default_factory=dict)
    blacklist_notes: Dict[str, str] = field(default_factory=dict)
    shodan_data: Dict = field(default_factory=dict)
    rdap: Dict = field(default_factory=dict)
    whois_raw: str = ""
    abuse_contacts: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    error: str = ""


def resolve_to_ip(target: str) -> str:
    return net.resolve_host(target)


def ip_scope(ip: str) -> str:
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return 'invalid'
    if net.is_tailscale(ip):
        return 'tailscale/CGNAT (100.64.0.0/10)'
    for attr, label in [('is_loopback', 'loopback'), ('is_private', 'private (RFC1918)'),
                        ('is_link_local', 'link-local'), ('is_multicast', 'multicast'),
                        ('is_reserved', 'reserved')]:
        if getattr(a, attr):
            return label
    return 'public'


def get_geolocation(ip: str) -> IpGeoInfo:
    """ip-api.com (free, 45 req/min), falling back to ipwho.is."""
    geo = IpGeoInfo(ip=ip)
    try:
        resp = requests.get(
            f"http://ip-api.com/json/{ip}",
            params={'fields': 'status,message,country,countryCode,regionName,city,lat,lon,'
                              'isp,org,as,timezone,mobile,proxy,hosting'},
            headers=HEADERS, timeout=10)
        if resp.status_code == 200:
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
                geo.mobile = bool(data.get('mobile', False))
                geo.proxy = bool(data.get('proxy', False))
                geo.hosting = bool(data.get('hosting', False))
                geo.source = 'ip-api.com'
                return geo
            geo.error = data.get('message', 'lookup failed')
        else:
            geo.error = f"ip-api.com HTTP {resp.status_code}"
    except Exception as e:
        geo.error = f"ip-api.com: {e}"

    try:
        r = requests.get(f"https://ipwho.is/{ip}", headers=HEADERS, timeout=10)
        d = r.json()
        if d.get('success'):
            conn = d.get('connection', {}) or {}
            geo.country = d.get('country', '')
            geo.country_code = d.get('country_code', '')
            geo.region = d.get('region', '')
            geo.city = d.get('city', '')
            geo.lat = d.get('latitude', 0.0)
            geo.lon = d.get('longitude', 0.0)
            geo.isp = conn.get('isp', '')
            geo.org = conn.get('org', '')
            geo.asn = f"AS{conn.get('asn')} {conn.get('org', '')}".strip() if conn.get('asn') else ''
            geo.timezone = (d.get('timezone') or {}).get('id', '')
            geo.source = 'ipwho.is'
            geo.error = ''
    except Exception:
        pass
    return geo


def get_reverse_dns(ip: str) -> List[str]:
    return net.reverse_dns(ip)


def _dnsbl_query_name(ip: str, rbl: str) -> str:
    a = ipaddress.ip_address(ip)
    if a.version == 4:
        return '.'.join(reversed(ip.split('.'))) + '.' + rbl
    nibbles = a.exploded.replace(':', '')
    return '.'.join(reversed(nibbles)) + '.' + rbl


def check_blacklists(ip: str):
    """
    Returns ({rbl: listed_bool}, {rbl: note}).
    Only 127.0.0.2-127.0.0.254 style answers count as listings. Spamhaus and
    others answer 127.255.255.x (or nothing) to queries from public resolvers
    — those are reported as 'refused', never as listed.
    """
    results, notes = {}, {}
    if ipaddress.ip_address(ip).version == 6:
        rbls = ['zen.spamhaus.org', 'dnsbl.dronebl.org']
    else:
        rbls = RBLS

    def check_rbl(rbl):
        q = net.dns_query(_dnsbl_query_name(ip, rbl), 'A', timeout=6)
        if q.status == 'NXDOMAIN':
            return rbl, False, ''
        if q.status in ('NOERROR',) and q.values:
            codes = [v for v in q.values if v.startswith('127.')]
            if any(v.startswith('127.255.255.') for v in codes) or not codes:
                return rbl, None, f"query refused ({', '.join(q.values)}) — list blocks public/open resolvers"
            return rbl, True, f"listed ({', '.join(codes)})"
        return rbl, None, q.error or q.status.lower()

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for rbl, listed, note in ex.map(check_rbl, rbls):
            if listed is not None:
                results[rbl] = listed
            if note:
                notes[rbl] = note
    return results, notes


def scan_ports(ip: str, timeout: float = 1.5) -> List[Dict]:
    """TCP connect check of common ports (through SOCKS when proxied)."""
    open_ports = []

    def check_port(port, service):
        if not net.tcp_port_open(ip, port, timeout):
            return None
        banner = ''
        try:
            s = net.create_connection((ip, port), timeout=3)
            s.settimeout(2.5)
            if port in (80, 8080):
                s.sendall(b"HEAD / HTTP/1.0\r\nHost: " + ip.encode() + b"\r\n\r\n")
            banner = s.recv(512).decode('utf-8', errors='ignore').strip()[:120]
            s.close()
        except Exception:
            pass
        return {'port': port, 'service': service, 'state': 'open', 'banner': banner}

    workers = 6 if net.proxy_active() else 24
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(lambda p: check_port(*p), COMMON_PORTS):
            if r:
                open_ports.append(r)
    return sorted(open_ports, key=lambda x: x['port'])


def get_rdap(ip: str) -> Dict:
    """RDAP via the rdap.org bootstrap (routes to ARIN/RIPE/APNIC/LACNIC/AFRINIC)."""
    try:
        r = requests.get(f"https://rdap.org/ip/{ip}",
                         headers={'Accept': 'application/rdap+json', **HEADERS}, timeout=15)
        if r.status_code != 200:
            return {'error': f'RDAP HTTP {r.status_code}'}
        d = r.json()
        out = {
            'handle': d.get('handle', ''),
            'name': d.get('name', ''),
            'range': f"{d.get('startAddress', '')} - {d.get('endAddress', '')}",
            'country': d.get('country', ''),
            'type': d.get('type', ''),
            'registry': (d.get('port43') or '').replace('whois.', '').upper(),
            'abuse': [], 'org': '',
        }
        for ent in _walk(d.get('entities', [])):
            roles = ent.get('roles', [])
            fn = _vcard(ent, 'fn')
            if ('registrant' in roles or 'administrative' in roles) and fn and not out['org']:
                out['org'] = fn
            if 'abuse' in roles:
                em = _vcard(ent, 'email')
                if em and em not in out['abuse']:
                    out['abuse'].append(em)
        return out
    except Exception as e:
        return {'error': f'RDAP error: {e}'}


def _walk(entities):
    for e in entities or []:
        yield e
        yield from _walk(e.get('entities'))


def _vcard(entity, key):
    try:
        for item in entity.get('vcardArray', [None, []])[1]:
            if item[0] == key:
                return str(item[3])
    except Exception:
        pass
    return ''


def get_abuse_contacts(ip: str) -> List[str]:
    return get_rdap(ip).get('abuse', [])


def get_exposure(ip: str, api_key: str = '') -> Dict:
    if api_key:
        try:
            import shodan as shodan_lib
            api = shodan_lib.Shodan(api_key)
            host = api.host(ip)
            vulns = host.get('vulns', [])
            return {
                'source': 'Shodan API',
                'ports': host.get('ports', []),
                'vulns': sorted(vulns if isinstance(vulns, list) else list(vulns.keys())),
                'os': host.get('os', ''),
                'tags': host.get('tags', []),
                'last_update': host.get('last_update', ''),
                'hostnames': host.get('hostnames', []),
                'services': [
                    {'port': s.get('port'), 'transport': s.get('transport', 'tcp'),
                     'product': s.get('product', ''), 'version': s.get('version', ''),
                     'banner': (s.get('data', '') or '')[:100]}
                    for s in host.get('data', [])[:20]
                ],
            }
        except Exception as e:
            err = str(e)
    else:
        err = ''
    from .domain_intel import get_internetdb
    data = get_internetdb(ip)
    if err and 'error' not in data:
        data['note'] = f"Shodan API failed ({err[:80]}); showing free InternetDB data"
    return data


class IpIntelThread(QThread):
    progress = pyqtSignal(str)
    result_ready = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, target: str, shodan_api_key: str = "",
                 do_port_scan: bool = True, do_blacklists: bool = True,
                 do_exposure: bool = True):
        super().__init__()
        self.target = target.strip()
        self.shodan_api_key = shodan_api_key
        self.do_port_scan = do_port_scan
        self.do_blacklists = do_blacklists
        self.do_exposure = do_exposure

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
            result.ip_version = ipaddress.ip_address(ip).version
            result.ip_scope = ip_scope(ip)
            public = result.ip_scope == 'public'
            if not public:
                result.notes.append(f"{ip} is a {result.ip_scope} address — internet lookups skipped")

            self.progress.emit(f"Reverse DNS for {ip}...")
            result.reverse_dns = get_reverse_dns(ip)

            if public:
                self.progress.emit("Geolocation lookup...")
                result.geo = get_geolocation(ip)

                self.progress.emit("RDAP ownership & abuse contacts...")
                result.rdap = get_rdap(ip)
                result.abuse_contacts = result.rdap.get('abuse', [])
                if result.rdap and not result.rdap.get('error'):
                    result.whois_raw = '\n'.join(f"{k}: {v}" for k, v in result.rdap.items() if v)

                if self.do_blacklists:
                    self.progress.emit("Checking DNS blacklists...")
                    result.blacklists, result.blacklist_notes = check_blacklists(ip)

                if self.do_exposure or self.shodan_api_key:
                    self.progress.emit("Querying Shodan / InternetDB...")
                    result.shodan_data = get_exposure(ip, self.shodan_api_key)

            if self.do_port_scan:
                self.progress.emit(f"Checking {len(COMMON_PORTS)} common TCP ports...")
                result.open_ports = scan_ports(ip)

            self.progress.emit("IP intelligence complete.")
            self.result_ready.emit(result)
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}")
