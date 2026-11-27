"""
Inspector Rabbit - Network layer

Every outbound lookup in the app goes through here so that one setting
controls how the investigator's traffic leaves the machine:

  * proxy routing (Tor or a custom SOCKS5/HTTP proxy) for all HTTP(S)
    traffic made with `requests`, including third-party libraries such as
    `shodan` that use it internally
  * a kill switch that refuses to send anything when the proxy is down,
    so a dead Tor daemon never silently falls back to the real IP
  * DNS-over-HTTPS through the proxy while proxied, so name lookups do not
    leak to the local resolver
  * TCP connections (SSL cert grabs, banner grabs, port checks) tunnelled
    through SOCKS when a SOCKS proxy is active
  * a guard for things that can never be proxied (ICMP ping, traceroute,
    SMTP on port 25, local DNSBL queries)
"""

from __future__ import annotations

import ipaddress
import socket
import threading
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter

try:
    from urllib3.util.retry import Retry
except Exception:  # pragma: no cover
    Retry = None

try:
    import socks  # PySocks
    _HAVE_PYSOCKS = True
except ImportError:
    socks = None
    _HAVE_PYSOCKS = False

try:
    import dns.resolver
    import dns.reversename
    import dns.exception
    _HAVE_DNSPYTHON = True
except ImportError:
    _HAVE_DNSPYTHON = False


APP_VERSION = "1.6.0"

BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
TOOL_UA = f"InspectorRabbit/{APP_VERSION} (+https://github.com/paulmmoore3416/inspector-rabbit)"

TOR_PROXY = "socks5h://127.0.0.1:9050"
TOR_BROWSER_PROXY = "socks5h://127.0.0.1:9150"

DOH_ENDPOINTS = [
    "https://cloudflare-dns.com/dns-query",
    "https://dns.google/resolve",
]

# Tailscale / CGNAT range: devices on the user's own tailnet
TAILSCALE_NET = ipaddress.ip_network("100.64.0.0/10")
TAILSCALE_DNS = "100.100.100.100"


class ProxyUnavailable(requests.exceptions.ConnectionError):
    """Raised when the kill switch blocks a request because the proxy is down."""


class DirectNetworkBlocked(RuntimeError):
    """Raised when an unproxyable operation is attempted while proxied."""


# ── State ─────────────────────────────────────────────────────────────────────

_lock = threading.Lock()
_state = {
    'proxy_url': '',          # effective proxy URL, '' when direct
    'kill_switch': False,
    'allow_direct': True,
}
_health = {'checked_at': 0.0, 'ok': False}
_HEALTH_TTL = 8.0


def configure(settings: dict) -> None:
    """Apply network settings. Safe to call repeatedly."""
    mode = (settings.get('proxy_mode') or 'off').lower()
    if mode == 'tor':
        url = TOR_PROXY
    elif mode == 'tor-browser':
        url = TOR_BROWSER_PROXY
    elif mode == 'custom':
        url = (settings.get('proxy_url') or '').strip()
        if url and '://' not in url:
            url = 'socks5h://' + url
        # socks5:// resolves DNS locally (leaks); always upgrade to socks5h
        if url.startswith('socks5://'):
            url = 'socks5h://' + url[len('socks5://'):]
    else:
        url = ''
    with _lock:
        _state['proxy_url'] = url
        _state['kill_switch'] = bool(settings.get('kill_switch')) and bool(url)
        _state['allow_direct'] = (not url) or bool(settings.get('allow_direct_when_proxied'))
        _health['checked_at'] = 0.0
    _install_patch()


def proxy_url() -> str:
    return _state['proxy_url']


def proxy_active() -> bool:
    return bool(_state['proxy_url'])


def kill_switch_on() -> bool:
    return _state['kill_switch']


def is_socks() -> bool:
    return _state['proxy_url'].startswith('socks')


def describe() -> str:
    if not proxy_active():
        return "Direct connection (no proxy)"
    label = "Tor" if _state['proxy_url'] in (TOR_PROXY, TOR_BROWSER_PROXY) else "Proxy"
    ks = " · kill switch ON" if kill_switch_on() else ""
    return f"{label} via {_redact(_state['proxy_url'])}{ks}"


def _redact(url: str) -> str:
    p = urlparse(url)
    if p.password:
        return url.replace(p.password, '***')
    return url


def _proxy_hostport() -> Tuple[str, int]:
    p = urlparse(_state['proxy_url'])
    default = 1080 if p.scheme.startswith('socks') else 8080
    return p.hostname or '127.0.0.1', p.port or default


def proxy_reachable(force: bool = False) -> bool:
    """Cheap TCP check that the proxy is listening (cached a few seconds)."""
    if not proxy_active():
        return True
    now = time.time()
    if not force and now - _health['checked_at'] < _HEALTH_TTL:
        return _health['ok']
    host, port = _proxy_hostport()
    ok = False
    try:
        with socket.create_connection((host, port), timeout=3):
            ok = True
    except OSError:
        ok = False
    _health.update(checked_at=now, ok=ok)
    return ok


def _check_policy() -> None:
    if not proxy_active():
        return
    if is_socks() and not _HAVE_PYSOCKS:
        raise ProxyUnavailable(
            "SOCKS proxy configured but PySocks is not installed "
            "(pip install PySocks). Request blocked to protect your IP.")
    if _state['kill_switch'] and not proxy_reachable():
        raise ProxyUnavailable(
            f"Kill switch: proxy {_redact(_state['proxy_url'])} is not reachable. "
            "Request blocked so your real IP is not exposed.")


# ── requests patch ────────────────────────────────────────────────────────────

_original_request = requests.Session.request
_patched = False


def _patched_request(self, method, url, **kwargs):
    _check_policy()
    if proxy_active():
        p = _state['proxy_url']
        kwargs['proxies'] = {'http': p, 'https': p}
        # Proxied requests are slower; give them a bit more time.
        t = kwargs.get('timeout')
        if isinstance(t, (int, float)) and t < 20:
            kwargs['timeout'] = t * 2
    return _original_request(self, method, url, **kwargs)


def _install_patch() -> None:
    global _patched
    if not _patched:
        requests.Session.request = _patched_request
        _patched = True


_install_patch()


def session(json_api: bool = False, retries: int = 2) -> requests.Session:
    """A requests session with sane retries and a default User-Agent."""
    s = requests.Session()
    s.headers['User-Agent'] = TOOL_UA if json_api else BROWSER_UA
    s.headers['Accept-Language'] = 'en-US,en;q=0.9'
    if Retry is not None and retries:
        retry = Retry(
            total=retries, connect=retries, read=retries, status=retries,
            backoff_factor=0.8,
            status_forcelist=(502, 503, 504),
            allowed_methods=frozenset(['GET', 'HEAD', 'POST']),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=40)
        s.mount('http://', adapter)
        s.mount('https://', adapter)
    return s


# ── Raw sockets ───────────────────────────────────────────────────────────────

def direct_allowed() -> bool:
    """Whether unproxyable traffic (ICMP, UDP, SMTP, local DNS) may be sent."""
    return _state['allow_direct']


def require_direct(feature: str) -> None:
    if not direct_allowed():
        raise DirectNetworkBlocked(
            f"{feature} cannot be routed through the proxy and would expose your "
            "real IP. Enable 'Allow direct traffic when proxied' in Settings to run it.")


def create_connection(address: Tuple[str, int], timeout: float = 10.0) -> socket.socket:
    """socket.create_connection that tunnels through SOCKS when proxied."""
    _check_policy()
    if proxy_active():
        if not is_socks():
            require_direct("Raw TCP connections over an HTTP proxy")
            return socket.create_connection(address, timeout=timeout)
        host, port = _proxy_hostport()
        p = urlparse(_state['proxy_url'])
        ptype = socks.SOCKS4 if p.scheme.startswith('socks4') else socks.SOCKS5
        return socks.create_connection(
            address, timeout=timeout,
            proxy_type=ptype, proxy_addr=host, proxy_port=port,
            proxy_rdns=True, proxy_username=p.username, proxy_password=p.password,
        )
    return socket.create_connection(address, timeout=timeout)


def tcp_port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        s = create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except (OSError, Exception):
        return False


# ── DNS ───────────────────────────────────────────────────────────────────────

_RTYPE_CODES = {
    'A': 1, 'NS': 2, 'CNAME': 5, 'SOA': 6, 'PTR': 12, 'MX': 15, 'TXT': 16,
    'AAAA': 28, 'SRV': 33, 'CAA': 257,
}


@dataclass
class DnsAnswer:
    rtype: str
    value: str
    ttl: int = 0


class DnsResult:
    def __init__(self, status: str, answers: Optional[List[DnsAnswer]] = None, error: str = ''):
        self.status = status          # NOERROR | NXDOMAIN | NODATA | TIMEOUT | ERROR
        self.answers = answers or []
        self.error = error

    @property
    def values(self) -> List[str]:
        return [a.value for a in self.answers]

    def __bool__(self):
        return bool(self.answers)


def _txt_join(data: str) -> str:
    """'"abc" "def"' -> 'abcdef' (DoH returns TXT in presentation format)."""
    import re as _re
    parts = _re.findall(r'"((?:[^"\\]|\\.)*)"', data)
    return ''.join(parts) if parts else data


def _doh_query(name: str, rtype: str, timeout: float) -> DnsResult:
    last_err = ''
    for ep in DOH_ENDPOINTS:
        try:
            r = requests.get(
                ep, params={'name': name, 'type': rtype},
                headers={'Accept': 'application/dns-json', 'User-Agent': TOOL_UA},
                timeout=timeout,
            )
            if r.status_code != 200:
                last_err = f"DoH HTTP {r.status_code}"
                continue
            data = r.json()
            status = data.get('Status', 2)
            if status == 3:
                return DnsResult('NXDOMAIN')
            if status != 0:
                last_err = f"DoH rcode {status}"
                continue
            code = _RTYPE_CODES.get(rtype)
            answers = [
                DnsAnswer(rtype, _txt_join(str(a.get('data', '')).strip()) if rtype == 'TXT'
                          else str(a.get('data', '')).strip(), int(a.get('TTL', 0)))
                for a in data.get('Answer', []) or []
                if code is None or a.get('type') == code
            ]
            return DnsResult('NOERROR' if answers else 'NODATA', answers)
        except ProxyUnavailable:
            raise
        except Exception as exc:
            last_err = str(exc)
    return DnsResult('ERROR', error=last_err)


def _local_query(name: str, rtype: str, timeout: float, nameservers=None) -> DnsResult:
    if not _HAVE_DNSPYTHON:
        if rtype in ('A', 'AAAA'):
            fam = socket.AF_INET if rtype == 'A' else socket.AF_INET6
            try:
                infos = socket.getaddrinfo(name, None, fam)
                vals = sorted({i[4][0] for i in infos})
                return DnsResult('NOERROR', [DnsAnswer(rtype, v) for v in vals])
            except socket.gaierror as exc:
                return DnsResult('NXDOMAIN', error=str(exc))
        return DnsResult('ERROR', error='dnspython not installed')
    res = dns.resolver.Resolver()
    if nameservers:
        res.nameservers = list(nameservers)
    res.timeout = min(timeout, 5)
    res.lifetime = timeout
    try:
        ans = res.resolve(name, rtype)
        ttl = ans.rrset.ttl if ans.rrset is not None else 0
        out = []
        for rd in ans:
            if rtype == 'MX':
                out.append(DnsAnswer(rtype, f"{rd.preference} {rd.exchange}", ttl))
            elif rtype == 'TXT':
                out.append(DnsAnswer(rtype, b''.join(rd.strings).decode('utf-8', 'replace'), ttl))
            else:
                out.append(DnsAnswer(rtype, rd.to_text(), ttl))
        return DnsResult('NOERROR', out)
    except dns.resolver.NXDOMAIN:
        return DnsResult('NXDOMAIN')
    except dns.resolver.NoAnswer:
        return DnsResult('NODATA')
    except dns.resolver.NoNameservers as exc:
        return DnsResult('ERROR', error=str(exc)[:120])
    except dns.exception.Timeout:
        return DnsResult('TIMEOUT', error='DNS timeout')
    except Exception as exc:
        return DnsResult('ERROR', error=str(exc)[:120])


def dns_query(name: str, rtype: str = 'A', timeout: float = 8.0,
              force_local: bool = False, nameservers=None) -> DnsResult:
    """Resolve a record. Uses DoH through the proxy when proxied (no leaks)."""
    name = name.strip().rstrip('.')
    rtype = rtype.upper()
    if proxy_active() and not force_local:
        return _doh_query(name, rtype, timeout)
    if force_local and proxy_active():
        require_direct("Local DNS queries")
    return _local_query(name, rtype, timeout, nameservers)


def resolve(name: str, rtype: str = 'A', timeout: float = 8.0) -> List[str]:
    return dns_query(name, rtype, timeout).values


def reverse_dns(ip: str, timeout: float = 6.0) -> List[str]:
    try:
        rev = ipaddress.ip_address(ip).reverse_pointer
    except ValueError:
        return []
    return [v.rstrip('.') for v in resolve(rev, 'PTR', timeout)]


def is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value.strip().strip('[]'))
        return True
    except ValueError:
        return False


def clean_host(target: str) -> str:
    """Strip scheme, path, port and credentials from a URL-ish target."""
    t = (target or '').strip()
    if '://' in t:
        t = urlparse(t).hostname or ''
    else:
        t = t.split('/')[0]
        if t.count(':') == 1:          # host:port (not IPv6)
            t = t.split(':')[0]
        if '@' in t:
            t = t.split('@')[-1]
    return t.strip('[]').strip().lower().rstrip('.')


def resolve_host(target: str) -> str:
    """Return the first IP (IPv4 preferred) for a host, or '' if unresolvable."""
    host = clean_host(target)
    if not host:
        return ''
    if is_ip(host):
        return host
    v4 = resolve(host, 'A')
    if v4:
        return v4[0]
    v6 = resolve(host, 'AAAA')
    return v6[0] if v6 else ''


def is_tailscale(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip) in TAILSCALE_NET
    except ValueError:
        return False


def is_public_ip(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip)
        return a.is_global
    except ValueError:
        return False


# ── Diagnostics ───────────────────────────────────────────────────────────────

def exit_ip_check(timeout: float = 25.0) -> dict:
    """Report the public IP our requests leave from and whether it is Tor."""
    out = {'ip': '', 'is_tor': None, 'via': describe(), 'error': ''}
    try:
        r = requests.get('https://check.torproject.org/api/ip',
                         headers={'User-Agent': TOOL_UA}, timeout=timeout)
        data = r.json()
        out['ip'] = data.get('IP', '')
        out['is_tor'] = bool(data.get('IsTor'))
    except ProxyUnavailable as exc:
        out['error'] = str(exc)
    except Exception as exc:
        out['error'] = f"{type(exc).__name__}: {exc}"[:200]
    return out
