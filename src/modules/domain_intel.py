"""
Inspector Rabbit - Domain Intelligence Module
RDAP/WHOIS, DNS (incl. SPF/DMARC), SSL, HTTP headers + security audit,
technology fingerprinting, wildcard-aware subdomain brute force, and
Shodan (API key) or Shodan InternetDB (free) exposure data.
"""

import re
import ssl
import socket
import random
import string
import concurrent.futures
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, field

import requests
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from . import net

HEADERS = {'User-Agent': net.BROWSER_UA, 'Accept-Language': 'en-US,en;q=0.9'}

COMMON_SUBDOMAINS = sorted(set([
    'www', 'mail', 'ftp', 'smtp', 'pop', 'imap', 'vpn', 'remote', 'api',
    'dev', 'staging', 'test', 'beta', 'admin', 'panel', 'portal', 'blog',
    'shop', 'store', 'cdn', 'static', 'media', 'img', 'images', 'video',
    'download', 'upload', 'files', 'docs', 'help', 'support', 'forum',
    'chat', 'wiki', 'app', 'mobile', 'm', 'git', 'gitlab', 'svn', 'jira',
    'jenkins', 'ci', 'grafana', 'kibana', 'elastic', 'monitor', 'dashboard',
    'status', 'ns1', 'ns2', 'ns3', 'mx', 'mx1', 'mx2', 'smtp1', 'smtp2',
    'secure', 'ssl', 'webmail', 'email', 'mail2', 'exchange', 'owa',
    'autodiscover', 'cpanel', 'whm', 'plesk', 'phpmyadmin', 'db', 'database',
    'mysql', 'postgres', 'redis', 'search', 'analytics', 'tracking', 'metrics',
    'backup', 'archive', 'old', 'new', 'v2', 'v3', 'alpha', 'canary', 'sso',
    'auth', 'login', 'id', 'accounts', 'account', 'intranet', 'internal',
    'corp', 'stage', 'uat', 'qa', 'demo', 'sandbox', 'preview', 'assets',
    'web', 'www2', 'origin', 'edge', 'proxy', 'gateway', 'office', 'crm',
    'erp', 'hr', 'careers', 'jobs', 'news', 'events', 'partners', 'cloud',
    'k8s', 'registry', 'vault', 'sentry', 'prometheus', 'lyncdiscover',
    'sip', 'meet', 'zoom', 'calendar', 'drive', 'share', 'sharepoint',
]))

SECURITY_HEADERS = [
    'Strict-Transport-Security', 'Content-Security-Policy', 'X-Frame-Options',
    'X-Content-Type-Options', 'Referrer-Policy', 'Permissions-Policy',
]


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
    source: str = ""
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
    days_remaining: Optional[int] = None
    san: List[str] = field(default_factory=list)
    serial_number: str = ""
    tls_version: str = ""
    verified: bool = False
    verify_error: str = ""
    error: str = ""


@dataclass
class DomainIntelResult:
    domain: str
    whois: Optional[WhoisResult] = None
    dns_records: List[DnsRecord] = field(default_factory=list)
    ssl_info: Optional[SslInfo] = None
    http_headers: Dict = field(default_factory=dict)
    security_headers: Dict = field(default_factory=dict)
    email_security: Dict = field(default_factory=dict)
    subdomains: List[str] = field(default_factory=list)
    wildcard_dns: bool = False
    ip_addresses: List[str] = field(default_factory=list)
    shodan_data: Dict = field(default_factory=dict)
    technologies: List[str] = field(default_factory=list)
    robots_txt: str = ""
    sitemap_found: bool = False
    errors: List[str] = field(default_factory=list)


def normalize_domain(value: str) -> str:
    return net.clean_host(value)


# ── RDAP / WHOIS ──────────────────────────────────────────────────────────────

def _vcard_get(entity: dict, key: str) -> str:
    try:
        for item in entity.get('vcardArray', [None, []])[1]:
            if item[0] == key:
                val = item[3]
                if isinstance(val, list):
                    val = ' '.join(str(v) for v in val if v)
                return str(val)
    except Exception:
        pass
    return ''


def _walk_entities(entities):
    for e in entities or []:
        yield e
        yield from _walk_entities(e.get('entities'))


def lookup_rdap(domain: str) -> WhoisResult:
    result = WhoisResult(domain=domain, source='RDAP')
    try:
        r = requests.get(f"https://rdap.org/domain/{domain}",
                         headers={'Accept': 'application/rdap+json', 'User-Agent': net.TOOL_UA},
                         timeout=15)
        if r.status_code == 404:
            result.error = "Domain not found in RDAP (unregistered, or TLD without RDAP)"
            return result
        if r.status_code != 200:
            result.error = f"RDAP HTTP {r.status_code}"
            return result
        d = r.json()
        for ev in d.get('events', []):
            action, date = ev.get('eventAction', ''), ev.get('eventDate', '')
            if action == 'registration':
                result.creation_date = date
            elif action == 'expiration':
                result.expiration_date = date
            elif action in ('last changed', 'last update of RDAP database') and not result.updated_date:
                if action == 'last changed':
                    result.updated_date = date
        result.status = [str(s) for s in d.get('status', [])]
        result.name_servers = sorted({ns.get('ldhName', '').lower().rstrip('.')
                                      for ns in d.get('nameservers', []) if ns.get('ldhName')})
        for ent in _walk_entities(d.get('entities')):
            roles = ent.get('roles', [])
            if 'registrar' in roles and not result.registrar:
                result.registrar = _vcard_get(ent, 'fn') or ent.get('handle', '')
            if 'registrant' in roles:
                result.registrant_name = result.registrant_name or _vcard_get(ent, 'fn')
                result.registrant_org = result.registrant_org or _vcard_get(ent, 'org')
                result.registrant_email = result.registrant_email or _vcard_get(ent, 'email')
                adr = ''
                try:
                    for item in ent.get('vcardArray', [None, []])[1]:
                        if item[0] == 'adr':
                            lbl = item[1].get('label') if isinstance(item[1], dict) else ''
                            parts = item[3] if isinstance(item[3], list) else []
                            adr = (parts[-1] if parts else '') or lbl or ''
                except Exception:
                    pass
                result.registrant_country = result.registrant_country or str(adr)
            if 'abuse' in roles and not result.raw:
                em = _vcard_get(ent, 'email')
                if em:
                    result.raw = f"Abuse contact: {em}"
    except net.ProxyUnavailable as e:
        result.error = str(e)
    except Exception as e:
        result.error = f"RDAP error: {e}"
    return result


def lookup_whois_legacy(domain: str) -> WhoisResult:
    """Port-43 WHOIS via python-whois. Direct connection only."""
    result = WhoisResult(domain=domain, source='WHOIS')
    try:
        net.require_direct("Port-43 WHOIS")
        import whois
        w = whois.whois(domain)

        def safe_str(val):
            if isinstance(val, list):
                return str(val[0]) if val else ""
            return str(val) if val else ""

        def safe_date(val):
            if isinstance(val, list):
                val = val[0] if val else None
            if hasattr(val, 'strftime'):
                return val.strftime('%Y-%m-%dT%H:%M:%SZ')
            return str(val) if val else ""

        result.registrar = safe_str(w.registrar)
        result.creation_date = safe_date(w.creation_date)
        result.expiration_date = safe_date(w.expiration_date)
        result.updated_date = safe_date(w.updated_date)
        result.name_servers = sorted({str(ns).lower().rstrip('.') for ns in (w.name_servers or [])})
        result.registrant_name = safe_str(getattr(w, 'name', ''))
        result.registrant_org = safe_str(getattr(w, 'org', ''))
        result.registrant_email = safe_str(w.emails)
        result.registrant_country = safe_str(getattr(w, 'country', ''))
        st = w.status
        result.status = [str(s) for s in st] if isinstance(st, list) else ([str(st)] if st else [])
        result.raw = str(getattr(w, 'text', ''))[:8000]
        if not (result.registrar or result.creation_date):
            result.error = "WHOIS returned no data"
    except Exception as e:
        result.error = str(e)[:200]
    return result


def lookup_whois(domain: str) -> WhoisResult:
    """RDAP first (works through proxies, structured); legacy WHOIS fills gaps."""
    rdap = lookup_rdap(domain)
    if not rdap.error and rdap.registrar and rdap.creation_date:
        return rdap
    if not net.direct_allowed():
        return rdap
    legacy = lookup_whois_legacy(domain)
    if rdap.error:
        if legacy.error:
            legacy.error = f"{rdap.error}; {legacy.error}"
        return legacy
    for f in ('registrar', 'creation_date', 'expiration_date', 'updated_date',
              'registrant_name', 'registrant_org', 'registrant_email', 'registrant_country'):
        if not getattr(rdap, f) and getattr(legacy, f):
            setattr(rdap, f, getattr(legacy, f))
    if not rdap.name_servers:
        rdap.name_servers = legacy.name_servers
    rdap.source = 'RDAP + WHOIS'
    return rdap


# ── DNS ───────────────────────────────────────────────────────────────────────

def lookup_dns(domain: str) -> List[DnsRecord]:
    records: List[DnsRecord] = []
    types = ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME', 'SOA', 'CAA']

    def q(rtype):
        return rtype, net.dns_query(domain, rtype)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for rtype, res in ex.map(q, types):
            for a in res.answers:
                records.append(DnsRecord(rtype, a.value, a.ttl))

    dmarc = net.dns_query(f"_dmarc.{domain}", 'TXT')
    for a in dmarc.answers:
        if 'v=dmarc1' in a.value.lower():
            records.append(DnsRecord('DMARC', a.value, a.ttl))

    for a in [r for r in records if r.record_type == 'A'][:3]:
        for ptr in net.reverse_dns(a.value):
            records.append(DnsRecord('PTR', f"{a.value} → {ptr}"))
    return records


def assess_email_security(records: List[DnsRecord]) -> Dict:
    txt = [r.value.strip('"') for r in records if r.record_type == 'TXT']
    spf = [t for t in txt if t.lower().startswith('v=spf1')]
    dmarc = [r.value for r in records if r.record_type == 'DMARC']
    out = {
        'mx_present': any(r.record_type == 'MX' for r in records),
        'spf': spf[0] if spf else '',
        'dmarc': dmarc[0].strip('"') if dmarc else '',
        'findings': [],
    }
    if not spf:
        out['findings'].append('No SPF record — domain can be spoofed in email')
    elif len(spf) > 1:
        out['findings'].append('Multiple SPF records (invalid per RFC 7208)')
    elif spf[0].rstrip().endswith('+all'):
        out['findings'].append('SPF ends with +all (anyone may send as this domain)')
    if not dmarc:
        out['findings'].append('No DMARC record')
    else:
        m = re.search(r'p=(\w+)', dmarc[0])
        if m and m.group(1).lower() == 'none':
            out['findings'].append('DMARC policy is p=none (monitoring only)')
    return out


# ── SSL ───────────────────────────────────────────────────────────────────────

def _name_dict(name) -> Dict:
    out = {}
    try:
        for attr in name:
            out[attr.oid._name] = attr.value
    except Exception:
        pass
    return out


def get_ssl_info(domain: str, port: int = 443) -> SslInfo:
    info = SslInfo()
    der = None
    try:
        ctx = ssl.create_default_context()
        with net.create_connection((domain, port), timeout=12) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ss:
                der = ss.getpeercert(binary_form=True)
                info.tls_version = ss.version() or ''
                info.verified = True
    except ssl.SSLCertVerificationError as e:
        info.verify_error = e.verify_message or str(e)
    except ssl.SSLError as e:
        info.verify_error = str(e)
    except net.ProxyUnavailable as e:
        info.error = str(e)
        return info
    except (socket.timeout, TimeoutError):
        info.error = "Connection timeout"
        return info
    except ConnectionRefusedError:
        info.error = "Connection refused (port 443 not open)"
        return info
    except Exception as e:
        info.error = str(e)[:200]
        return info

    if der is None:
        # Verification failed: still fetch the certificate so it can be inspected
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with net.create_connection((domain, port), timeout=12) as sock:
                with ctx.wrap_socket(sock, server_hostname=domain) as ss:
                    der = ss.getpeercert(binary_form=True)
                    info.tls_version = ss.version() or ''
        except Exception as e:
            info.error = f"{info.verify_error or 'TLS error'}; {e}"[:200]
            return info

    try:
        from cryptography import x509
        cert = x509.load_der_x509_certificate(der)
        info.subject = _name_dict(cert.subject)
        info.issuer = _name_dict(cert.issuer)
        info.version = cert.version.value + 1
        nb = getattr(cert, 'not_valid_before_utc', None) or cert.not_valid_before.replace(tzinfo=timezone.utc)
        na = getattr(cert, 'not_valid_after_utc', None) or cert.not_valid_after.replace(tzinfo=timezone.utc)
        info.not_before = nb.strftime('%Y-%m-%d %H:%M:%S UTC')
        info.not_after = na.strftime('%Y-%m-%d %H:%M:%S UTC')
        info.days_remaining = (na - datetime.now(timezone.utc)).days
        info.serial_number = format(cert.serial_number, 'X')
        try:
            ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            info.san = [f"DNS: {n}" for n in ext.value.get_values_for_type(x509.DNSName)]
            info.san += [f"IP: {n}" for n in ext.value.get_values_for_type(x509.IPAddress)]
        except x509.ExtensionNotFound:
            pass
        if not info.verified:
            info.subject['_warning'] = f"Certificate NOT trusted: {info.verify_error}"
    except Exception as e:
        info.error = f"Certificate parse error: {e}"
    return info


# ── HTTP ──────────────────────────────────────────────────────────────────────

def fetch_homepage(domain: str):
    """Return (headers dict, body text). Tries HTTPS (verified, then not), then HTTP."""
    attempts = [(f"https://{domain}", True), (f"https://{domain}", False), (f"http://{domain}", True)]
    last_err = ''
    for url, verify in attempts:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True, verify=verify)
            headers = dict(resp.headers)
            headers['_status_code'] = resp.status_code
            headers['_final_url'] = resp.url
            if not verify:
                headers['_tls_warning'] = 'Certificate failed verification'
            if resp.history:
                headers['_redirect_chain'] = ' → '.join([h.url for h in resp.history] + [resp.url])
            body = resp.text[:300000] if 'html' in resp.headers.get('content-type', '') else ''
            return headers, body
        except net.ProxyUnavailable as e:
            return {'_error': str(e)}, ''
        except requests.exceptions.SSLError as e:
            last_err = str(e)
            continue
        except Exception as e:
            last_err = str(e)
            if url.startswith('https') and verify:
                continue
    return {'_error': last_err[:200]}, ''


def get_http_headers(domain: str) -> Dict:
    return fetch_homepage(domain)[0]


def audit_security_headers(headers: Dict) -> Dict:
    lower = {k.lower(): v for k, v in headers.items() if not k.startswith('_')}
    return {h: (lower.get(h.lower()) or 'MISSING') for h in SECURITY_HEADERS}


TECH_SIGNATURES = {
    # name: (header patterns, body patterns)
    'WordPress': ([], ['/wp-content/', '/wp-includes/', 'wp-json']),
    'Drupal': (['x-drupal-cache', 'x-generator: drupal'], ['drupal-settings-json', '/sites/default/files', 'Drupal.settings']),
    'Joomla': ([], ['/media/jui/', 'content="Joomla!']),
    'Shopify': (['x-shopid', 'x-shopify'], ['cdn.shopify.com']),
    'Wix': (['x-wix-request-id'], ['static.wixstatic.com']),
    'Squarespace': ([], ['static1.squarespace.com']),
    'Ghost': ([], ['content="Ghost ']),
    'Next.js': (['x-nextjs', 'x-powered-by: next.js'], ['/_next/static/', '__NEXT_DATA__']),
    'Nuxt.js': ([], ['__NUXT__', '/_nuxt/']),
    'Gatsby': ([], ['___gatsby']),
    'React': ([], ['data-reactroot', 'react-dom.production']),
    'Angular': ([], ['ng-version=']),
    'Vue.js': ([], ['data-v-app', 'vue.runtime', '__VUE__']),
    'Svelte': ([], ['svelte-']),
    'jQuery': ([], ['jquery.min.js', 'jquery-']),
    'Bootstrap': ([], ['bootstrap.min.css', 'bootstrap.min.js', 'bootstrap.bundle']),
    'Tailwind CSS': ([], ['tailwindcss']),
    'Google Analytics': ([], ['googletagmanager.com/gtag/js', 'google-analytics.com/analytics.js']),
    'Google Tag Manager': ([], ['googletagmanager.com/gtm.js']),
    'Cloudflare': (['cf-ray', 'server: cloudflare'], []),
    'Akamai': (['x-akamai', 'akamai-grn'], []),
    'Fastly': (['x-served-by: cache-', 'fastly'], []),
    'Amazon CloudFront': (['x-amz-cf-id', 'via: 1.1 .*cloudfront'], []),
    'Vercel': (['x-vercel-id', 'server: vercel'], []),
    'Netlify': (['x-nf-request-id', 'server: netlify'], []),
    'nginx': (['server: nginx'], []),
    'Apache': (['server: apache'], []),
    'Microsoft IIS': (['server: microsoft-iis'], []),
    'LiteSpeed': (['server: litespeed'], []),
    'PHP': (['x-powered-by: php', 'phpsessid'], []),
    'ASP.NET': (['x-aspnet-version', 'x-powered-by: asp.net'], ['__VIEWSTATE']),
    'Express': (['x-powered-by: express'], []),
    'Django': (['csrftoken'], ['csrfmiddlewaretoken']),
    'Laravel': (['laravel_session'], []),
    'Ruby on Rails': (['x-runtime', '_rails_session'], ['csrf-param" content="authenticity_token']),
    'HubSpot': ([], ['js.hs-scripts.com']),
    'reCAPTCHA': ([], ['google.com/recaptcha']),
}


def detect_technologies(headers: Dict, body: str = "") -> List[str]:
    techs = []
    server = headers.get('Server') or headers.get('server')
    if server:
        techs.append(f"Server: {server}")
    xp = headers.get('X-Powered-By') or headers.get('x-powered-by')
    if xp:
        techs.append(f"Powered-By: {xp}")
    hdr_text = '\n'.join(f"{k.lower()}: {str(v).lower()}" for k, v in headers.items() if not k.startswith('_'))
    gen = re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)', body or '', re.I)
    if gen:
        techs.append(f"Generator: {gen.group(1)[:60]}")
    for tech, (hpats, bpats) in TECH_SIGNATURES.items():
        if any(re.search(p, hdr_text) for p in hpats) or any(p in (body or '') for p in bpats):
            techs.append(tech)
    return techs


# ── Subdomains ────────────────────────────────────────────────────────────────

def _rand_label() -> str:
    return 'ir-' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=14))


def detect_wildcard(domain: str) -> set:
    """IPs returned for random labels (wildcard DNS). Empty set = no wildcard."""
    ips = set()
    for _ in range(2):
        ips.update(net.resolve(f"{_rand_label()}.{domain}", 'A', timeout=5))
    return ips


def enumerate_subdomains(domain: str, wordlist: List[str] = None, wildcard_ips: set = None) -> List[str]:
    wordlist = wordlist or COMMON_SUBDOMAINS
    wildcard_ips = wildcard_ips if wildcard_ips is not None else detect_wildcard(domain)
    found = []
    workers = 10 if net.proxy_active() else 30

    def check(sub):
        fqdn = f"{sub}.{domain}"
        ips = set(net.resolve(fqdn, 'A', timeout=5))
        if not ips:
            cname = net.resolve(fqdn, 'CNAME', timeout=5)
            return fqdn if cname else None
        if wildcard_ips and ips <= wildcard_ips:
            return None       # same answer as the wildcard -> not a real host
        return fqdn

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(check, wordlist):
            if r:
                found.append(r)
    return sorted(found)


def get_robots_txt(domain: str) -> str:
    for scheme in ['https', 'http']:
        try:
            resp = requests.get(f"{scheme}://{domain}/robots.txt", headers=HEADERS, timeout=8)
            ct = resp.headers.get('content-type', 'text/plain')
            if resp.status_code == 200 and 'text/plain' in ct and '<html' not in resp.text[:500].lower():
                return resp.text[:8000]
        except Exception:
            pass
    return ""


def check_sitemap(domain: str) -> bool:
    for path in ['/sitemap.xml', '/sitemap_index.xml', '/sitemap.txt']:
        for scheme in ['https', 'http']:
            try:
                resp = requests.get(f"{scheme}://{domain}{path}", headers=HEADERS, timeout=6)
                head = resp.text[:600].lower()
                if resp.status_code == 200 and ('<urlset' in head or '<sitemapindex' in head
                                                or (path.endswith('.txt') and head.startswith('http'))):
                    return True
            except Exception:
                pass
    return False


def resolve_ips(domain: str) -> List[str]:
    return net.resolve(domain, 'A') + net.resolve(domain, 'AAAA')


def get_internetdb(ip: str) -> Dict:
    """Shodan InternetDB: free, keyless open ports / CPEs / known CVEs."""
    try:
        r = requests.get(f"https://internetdb.shodan.io/{ip}",
                         headers={'User-Agent': net.TOOL_UA}, timeout=12)
        if r.status_code == 404:
            return {'source': 'Shodan InternetDB (free)', 'ip': ip,
                    'note': 'No data — Shodan has not seen open services on this IP'}
        if r.status_code != 200:
            return {'error': f'InternetDB HTTP {r.status_code}'}
        d = r.json()
        return {
            'source': 'Shodan InternetDB (free)',
            'ip': d.get('ip', ip),
            'ports': d.get('ports', []),
            'hostnames': d.get('hostnames', []),
            'cpes': d.get('cpes', []),
            'vulns': d.get('vulns', []),
            'tags': d.get('tags', []),
        }
    except Exception as e:
        return {'error': f'InternetDB error: {e}'}


def get_shodan_info(ip: str, api_key: str) -> Dict:
    if not api_key:
        return get_internetdb(ip)
    try:
        import shodan
        api = shodan.Shodan(api_key)
        host = api.host(ip)
        return {
            'source': 'Shodan API',
            'ip': host.get('ip_str', ''),
            'hostnames': host.get('hostnames', []),
            'country': host.get('country_name', ''),
            'city': host.get('city', ''),
            'org': host.get('org', ''),
            'isp': host.get('isp', ''),
            'asn': host.get('asn', ''),
            'os': host.get('os', ''),
            'ports': host.get('ports', []),
            'vulns': sorted(host.get('vulns', []) if isinstance(host.get('vulns'), list)
                            else list((host.get('vulns') or {}).keys())),
            'tags': host.get('tags', []),
            'last_update': host.get('last_update', ''),
        }
    except Exception as e:
        msg = str(e)
        fallback = get_internetdb(ip)
        if 'error' not in fallback:
            fallback['note'] = f"Shodan API failed ({msg[:80]}); showing free InternetDB data"
            return fallback
        return {'error': msg}


class DomainIntelThread(QThread):
    progress = pyqtSignal(str)
    result_ready = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, domain: str, shodan_api_key: str = "", do_subdomains: bool = True,
                 do_exposure: bool = True):
        super().__init__()
        self.domain = normalize_domain(domain)
        self.shodan_api_key = shodan_api_key
        self.do_subdomains = do_subdomains
        self.do_exposure = do_exposure or bool(shodan_api_key)

    def run(self):
        result = DomainIntelResult(domain=self.domain)
        try:
            if not self.domain or '.' not in self.domain:
                self.error.emit(f"'{self.domain}' is not a valid domain name")
                return

            self.progress.emit(f"Resolving {self.domain}...")
            result.ip_addresses = resolve_ips(self.domain)

            self.progress.emit("Registration data (RDAP / WHOIS)...")
            result.whois = lookup_whois(self.domain)

            self.progress.emit("Querying DNS records...")
            result.dns_records = lookup_dns(self.domain)
            result.email_security = assess_email_security(result.dns_records)

            if not result.ip_addresses and not result.dns_records:
                result.errors.append("Domain does not resolve (no DNS records found)")

            if result.ip_addresses:
                self.progress.emit("Fetching SSL certificate...")
                result.ssl_info = get_ssl_info(self.domain)

                self.progress.emit("Fetching homepage & headers...")
                headers, body = fetch_homepage(self.domain)
                result.http_headers = headers
                result.security_headers = audit_security_headers(headers) if '_error' not in headers else {}

                self.progress.emit("Fingerprinting technologies...")
                result.technologies = detect_technologies(headers, body)

                self.progress.emit("Checking robots.txt / sitemap...")
                result.robots_txt = get_robots_txt(self.domain)
                result.sitemap_found = check_sitemap(self.domain)

            if self.do_subdomains:
                self.progress.emit("Checking for wildcard DNS...")
                wc = detect_wildcard(self.domain)
                result.wildcard_dns = bool(wc)
                if wc:
                    self.progress.emit(f"Wildcard DNS detected ({', '.join(sorted(wc))}) — filtering false positives")
                self.progress.emit(f"Brute-forcing {len(COMMON_SUBDOMAINS)} common subdomains...")
                result.subdomains = enumerate_subdomains(self.domain, wildcard_ips=wc)

            v4 = [ip for ip in result.ip_addresses if ':' not in ip]
            if self.do_exposure and v4:
                src = 'Shodan API' if self.shodan_api_key else 'Shodan InternetDB'
                self.progress.emit(f"Querying {src} for {v4[0]}...")
                result.shodan_data = get_shodan_info(v4[0], self.shodan_api_key)

            self.progress.emit("Domain intelligence complete.")
            self.result_ready.emit(result)
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}")
