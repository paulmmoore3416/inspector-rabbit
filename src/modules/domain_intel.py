"""
Inspector Rabbit - Domain Intelligence Module
WHOIS, DNS, SSL, Shodan, Headers, and Subdomain enumeration
"""

import ssl
import socket
import json
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

import requests
import dns.resolver
import dns.reversename
import whois
from PyQt6.QtCore import QObject, pyqtSignal, QThread


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
}

COMMON_SUBDOMAINS = [
    'www', 'mail', 'ftp', 'smtp', 'pop', 'imap', 'vpn', 'remote', 'api',
    'dev', 'staging', 'test', 'beta', 'admin', 'panel', 'portal', 'blog',
    'shop', 'store', 'cdn', 'static', 'media', 'img', 'images', 'video',
    'download', 'upload', 'files', 'docs', 'help', 'support', 'forum',
    'chat', 'wiki', 'app', 'mobile', 'm', 'git', 'svn', 'jira', 'jenkins',
    'grafana', 'kibana', 'elastic', 'monitor', 'dashboard', 'status',
    'ns1', 'ns2', 'mx1', 'mx2', 'smtp1', 'smtp2', 'secure', 'ssl',
    'webmail', 'email', 'mail2', 'exchange', 'autodiscover', 'cpanel',
    'whm', 'plesk', 'phpmyadmin', 'db', 'database', 'mysql', 'postgres',
    'redis', 'elastic', 'search', 'analytics', 'tracking', 'metrics',
    'backup', 'archive', 'old', 'new', 'v2', 'v3', 'alpha', 'canary',
]


from bs4 import BeautifulSoup

def get_whois_history(domain: str) -> List[Dict]:
    """Scrape WHOIS history from viewdns.info."""
    url = f"https://viewdns.info/iphistory/?domain={domain}"
    history = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'lxml')
            table = soup.find('table', border="1")
            if table:
                rows = table.find_all('tr')[1:] # Skip header
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        history.append({
                            'ip': cols[0].get_text(strip=True),
                            'location': cols[1].get_text(strip=True),
                            'owner': cols[2].get_text(strip=True),
                            'last_checked': cols[3].get_text(strip=True)
                        })
    except Exception as e:
        print(f"Error fetching WHOIS history: {e}")
    return history

@dataclass
class WhoisResult:
    domain: str
    registrar: str = ""
    creation_date: str = ""
    expiration_date: str = ""
    updated_date: str = ""
    name_servers: List[str] = field(default_factory=list)
    registrant_name: str = ""
    registrant_org: str = ""
    registrant_email: str = ""
    registrant_country: str = ""
    status: List[str] = field(default_factory=list)
    raw: str = ""
    error: str = ""


@dataclass
class DnsRecord:
    record_type: str
    value: str
    ttl: int = 0


@dataclass
class SslInfo:
    subject: Dict = field(default_factory=dict)
    issuer: Dict = field(default_factory=dict)
    version: int = 0
    not_before: str = ""
    not_after: str = ""
    san: List[str] = field(default_factory=list)
    serial_number: str = ""
    error: str = ""


@dataclass
class DomainIntelResult:
    domain: str
    whois: Optional[WhoisResult] = None
    dns_records: List[DnsRecord] = field(default_factory=list)
    ssl_info: Optional[SslInfo] = None
    http_headers: Dict = field(default_factory=dict)
    subdomains: List[str] = field(default_factory=list)
    ip_addresses: List[str] = field(default_factory=list)
    shodan_data: Dict = field(default_factory=dict)
    technologies: List[str] = field(default_factory=list)
    robots_txt: str = ""
    sitemap_found: bool = False
    takeover_vulnerabilities: List[Dict] = field(default_factory=list)
    domain_history: List[Dict] = field(default_factory=list)


def check_takeovers(subdomains: List[str]) -> List[Dict]:
    vulnerable = []
    resolver = dns.resolver.Resolver()
    resolver.timeout = 2
    resolver.lifetime = 4

    import concurrent.futures

    def check_sub(sub):
        try:
            answers = resolver.resolve(sub, 'CNAME')
            for rdata in answers:
                cname_target = str(rdata.target).rstrip('.')
                try:
                    resolver.resolve(cname_target, 'A')
                except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                    return {'subdomain': sub, 'cname': cname_target, 'issue': 'CNAME points to NXDOMAIN (Potential Takeover)'}
        except Exception:
            pass
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_sub, sub): sub for sub in subdomains}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                vulnerable.append(res)
    return vulnerable


def lookup_whois(domain: str) -> WhoisResult:
    result = WhoisResult(domain=domain)
    try:
        w = whois.whois(domain)

        def safe_str(val):
            if isinstance(val, list):
                return str(val[0]) if val else ""
            return str(val) if val else ""

        def safe_date(val):
            if isinstance(val, list):
                val = val[0]
            if hasattr(val, 'strftime'):
                return val.strftime('%Y-%m-%d %H:%M:%S UTC')
            return str(val) if val else ""

        result.registrar = safe_str(w.registrar)
        result.creation_date = safe_date(w.creation_date)
        result.expiration_date = safe_date(w.expiration_date)
        result.updated_date = safe_date(w.updated_date)
        result.name_servers = [str(ns).lower() for ns in (w.name_servers or [])]
        result.registrant_name = safe_str(w.name)
        result.registrant_org = safe_str(w.org)
        result.registrant_email = safe_str(w.emails)
        result.registrant_country = safe_str(w.country)
        result.status = [str(s) for s in (w.status or [])] if isinstance(w.status, list) else [str(w.status)] if w.status else []

    except Exception as e:
        result.error = str(e)
    return result


def lookup_dns(domain: str) -> List[DnsRecord]:
    records = []
    record_types = ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME', 'SOA', 'CAA']

    resolver = dns.resolver.Resolver()
    resolver.timeout = 5
    resolver.lifetime = 10

    for rtype in record_types:
        try:
            answers = resolver.resolve(domain, rtype)
            for rdata in answers:
                value = str(rdata)
                # Format MX records nicely
                if rtype == 'MX':
                    value = f"{rdata.preference} {rdata.exchange}"
                records.append(DnsRecord(
                    record_type=rtype,
                    value=value,
                    ttl=answers.rrset.ttl if answers.rrset else 0
                ))
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout):
            pass
        except Exception:
            pass

    # PTR lookup for IP
    try:
        a_records = [r for r in records if r.record_type == 'A']
        for a in a_records[:2]:
            try:
                addr = dns.reversename.from_address(a.value)
                ptr = resolver.resolve(addr, 'PTR')
                for r in ptr:
                    records.append(DnsRecord(record_type='PTR', value=str(r)))
            except Exception:
                pass
    except Exception:
        pass

    return records


def get_ssl_info(domain: str, port: int = 443) -> SslInfo:
    info = SslInfo()
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()

                def parse_tuple(t):
                    return {item[0]: item[1] for item in t} if t else {}

                info.subject = parse_tuple(cert.get('subject', ()))
                info.issuer = parse_tuple(cert.get('issuer', ()))
                info.version = cert.get('version', 0)
                info.not_before = cert.get('notBefore', '')
                info.not_after = cert.get('notAfter', '')
                info.serial_number = str(cert.get('serialNumber', ''))

                san_list = []
                for san_type, san_value in cert.get('subjectAltName', []):
                    san_list.append(f"{san_type}: {san_value}")
                info.san = san_list

    except ssl.SSLError as e:
        info.error = f"SSL Error: {e}"
    except socket.timeout:
        info.error = "Connection timeout"
    except ConnectionRefusedError:
        info.error = "Connection refused (port 443 not open)"
    except Exception as e:
        info.error = str(e)
    return info


def get_http_headers(domain: str) -> Dict:
    try:
        resp = requests.get(
            f"https://{domain}", headers=HEADERS, timeout=10,
            allow_redirects=True, verify=False
        )
        headers = dict(resp.headers)
        headers['_status_code'] = resp.status_code
        headers['_final_url'] = resp.url
        return headers
    except Exception:
        try:
            resp = requests.get(
                f"http://{domain}", headers=HEADERS, timeout=10,
                allow_redirects=True
            )
            headers = dict(resp.headers)
            headers['_status_code'] = resp.status_code
            headers['_final_url'] = resp.url
            return headers
        except Exception as e:
            return {'_error': str(e)}


def detect_technologies(headers: Dict, body: str = "") -> List[str]:
    techs = []
    server = headers.get('Server', headers.get('server', ''))
    if server:
        techs.append(f"Server: {server}")

    x_powered = headers.get('X-Powered-By', headers.get('x-powered-by', ''))
    if x_powered:
        techs.append(f"Powered-By: {x_powered}")

    tech_patterns = {
        'WordPress': ['wp-content', 'wp-includes', 'wp-json'],
        'Drupal': ['Drupal.settings', 'drupal.js', 'sites/default/files'],
        'Joomla': ['Joomla!', '/templates/ja_', 'joomla'],
        'Django': ['csrfmiddlewaretoken', 'django'],
        'Laravel': ['laravel_session', 'XSRF-TOKEN'],
        'React': ['__REACT_DEVTOOLS', 'react-root', '_reactRootContainer'],
        'Angular': ['ng-version', 'ng-app', '_nghost'],
        'Vue.js': ['vue.js', '__vue__', 'data-v-'],
        'jQuery': ['jquery.min.js', 'jQuery.'],
        'Bootstrap': ['bootstrap.min.css', 'bootstrap.min.js'],
        'Cloudflare': ['cf-ray', '__cfduid'],
        'nginx': ['nginx'],
        'Apache': ['Apache'],
        'IIS': ['IIS'],
        'PHP': ['.php', 'PHPSESSID', 'PHP/'],
        'Python': ['Python/', 'Werkzeug/', 'gunicorn'],
        'Ruby': ['ruby', 'rails', 'passenger'],
        'Node.js': ['Express', 'nodejs'],
        'ASP.NET': ['ASP.NET', '__VIEWSTATE', 'aspx'],
    }

    all_text = body[:50000] + str(headers).lower()
    for tech, patterns in tech_patterns.items():
        for pattern in patterns:
            if pattern.lower() in all_text.lower():
                if tech not in techs:
                    techs.append(tech)
                break

    return techs


def enumerate_subdomains(domain: str, wordlist: List[str] = None) -> List[str]:
    if wordlist is None:
        wordlist = COMMON_SUBDOMAINS

    found = []
    resolver = dns.resolver.Resolver()
    resolver.timeout = 2
    resolver.lifetime = 4

    import concurrent.futures

    def check_subdomain(sub):
        fqdn = f"{sub}.{domain}"
        try:
            resolver.resolve(fqdn, 'A')
            return fqdn
        except Exception:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(check_subdomain, sub): sub for sub in wordlist}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                found.append(result)

    return sorted(found)


def get_robots_txt(domain: str) -> str:
    for scheme in ['https', 'http']:
        try:
            resp = requests.get(
                f"{scheme}://{domain}/robots.txt",
                headers=HEADERS, timeout=8
            )
            if resp.status_code == 200 and 'text' in resp.headers.get('content-type', 'text'):
                return resp.text[:5000]
        except Exception:
            pass
    return ""


def check_sitemap(domain: str) -> bool:
    for scheme in ['https', 'http']:
        for path in ['/sitemap.xml', '/sitemap_index.xml', '/sitemap.txt']:
            try:
                resp = requests.get(
                    f"{scheme}://{domain}{path}",
                    headers=HEADERS, timeout=5
                )
                if resp.status_code == 200:
                    return True
            except Exception:
                pass
    return False


def resolve_ips(domain: str) -> List[str]:
    ips = []
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = 5
        answers = resolver.resolve(domain, 'A')
        ips.extend([str(r) for r in answers])
    except Exception:
        pass
    try:
        resolver = dns.resolver.Resolver()
        answers = resolver.resolve(domain, 'AAAA')
        ips.extend([str(r) for r in answers])
    except Exception:
        pass
    return ips


def get_shodan_info(ip: str, api_key: str) -> Dict:
    if not api_key:
        return {'error': 'No Shodan API key configured'}
    try:
        import shodan
        api = shodan.Shodan(api_key)
        host = api.host(ip)
        return {
            'ip': host.get('ip_str', ''),
            'hostnames': host.get('hostnames', []),
            'country': host.get('country_name', ''),
            'city': host.get('city', ''),
            'org': host.get('org', ''),
            'isp': host.get('isp', ''),
            'asn': host.get('asn', ''),
            'os': host.get('os', ''),
            'ports': host.get('ports', []),
            'vulns': list(host.get('vulns', {}).keys()),
            'tags': host.get('tags', []),
            'last_update': host.get('last_update', ''),
        }
    except Exception as e:
        return {'error': str(e)}


class DomainIntelThread(QThread):
    progress = pyqtSignal(str)         # status message
    result_ready = pyqtSignal(object)  # DomainIntelResult
    error = pyqtSignal(str)

    def __init__(self, domain: str, shodan_api_key: str = "", do_subdomains: bool = True):
        super().__init__()
        self.domain = domain.strip().lower()
        # Strip protocol if present
        self.domain = re.sub(r'^https?://', '', self.domain).split('/')[0]
        self.shodan_api_key = shodan_api_key
        self.do_subdomains = do_subdomains

    def run(self):
        result = DomainIntelResult(domain=self.domain)
        try:
            self.progress.emit(f"WHOIS lookup for {self.domain}...")
            result.whois = lookup_whois(self.domain)

            self.progress.emit("Resolving IP addresses...")
            result.ip_addresses = resolve_ips(self.domain)

            self.progress.emit("Querying DNS records...")
            result.dns_records = lookup_dns(self.domain)

            self.progress.emit("Fetching SSL certificate...")
            result.ssl_info = get_ssl_info(self.domain)

            self.progress.emit("Fetching HTTP headers...")
            result.http_headers = get_http_headers(self.domain)

            self.progress.emit("Detecting technologies...")
            result.technologies = detect_technologies(result.http_headers)

            self.progress.emit("Checking robots.txt...")
            result.robots_txt = get_robots_txt(self.domain)

            self.progress.emit("Checking sitemap...")
            result.sitemap_found = check_sitemap(self.domain)

            self.progress.emit("Fetching domain history...")
            result.domain_history = get_whois_history(self.domain)

            if self.do_subdomains:
                self.progress.emit("Enumerating subdomains (this may take a moment)...")
                result.subdomains = enumerate_subdomains(self.domain)

            if self.shodan_api_key and result.ip_addresses:
                self.progress.emit(f"Querying Shodan for {result.ip_addresses[0]}...")
                result.shodan_data = get_shodan_info(
                    result.ip_addresses[0], self.shodan_api_key
                )

            self.progress.emit("Domain intelligence complete.")
            self.result_ready.emit(result)

        except Exception as e:
            self.error.emit(str(e))
