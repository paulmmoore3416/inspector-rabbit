"""
Inspector Rabbit - Web Crawler Module
Spider websites, extract emails, phones, social links, and metadata
"""

import re
import time
import hashlib
from urllib.parse import urlparse, urljoin, urldefrag, unquote
from typing import Set, List, Dict, Optional, Callable
from dataclasses import dataclass, field
from collections import deque

import requests
from bs4 import BeautifulSoup
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from . import net


HEADERS = {
    'User-Agent': net.BROWSER_UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

EMAIL_RE = re.compile(r'(?<![\w.%+-])[A-Za-z0-9._%+\-]+@(?:[A-Za-z0-9\-]+\.)+[A-Za-z]{2,24}(?![\w-])')
OBFUSCATED_EMAIL_RE = re.compile(
    r'([A-Za-z0-9._%+\-]+)\s*(?:\[at\]|\(at\)|\{at\}| at )\s*([A-Za-z0-9\-]+(?:\s*(?:\[dot\]|\(dot\)|\.| dot )\s*[A-Za-z0-9\-]+)+)',
    re.I)
_ASSET_EXT = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.css', '.js', '.ico', '.woff', '.woff2')
_SKIP_EXT = ('.pdf', '.zip', '.gz', '.tar', '.rar', '.7z', '.exe', '.dmg', '.iso', '.mp4', '.mp3',
             '.avi', '.mov', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.css', '.js',
             '.woff', '.woff2', '.ttf', '.xml', '.json', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx')
SOCIAL_PATTERNS = {
    'github': r'github\.com/(?!features|about|pricing|login|join|sponsors|topics|marketplace|orgs/|site/|collections|enterprise)[A-Za-z0-9\-_]{1,39}(?:/[A-Za-z0-9._\-]+)?',
    'twitter': r'(?:twitter|x)\.com/(?!intent|share|home|i/|search|hashtag|widgets|privacy|tos\b)[A-Za-z0-9_]{1,15}\b',
    'linkedin': r'linkedin\.com/(?:in|company|school)/[A-Za-z0-9\-_%]+',
    'instagram': r'instagram\.com/(?!p/|reel/|explore|accounts)[A-Za-z0-9._]{1,30}',
    'facebook': r'facebook\.com/(?!sharer|share|dialog|plugins|tr\?|login)[A-Za-z0-9.\-]{3,}',
    'youtube': r'youtube\.com/(?:c/|channel/|user/|@)[A-Za-z0-9_\-.]+',
    'tiktok': r'tiktok\.com/@[A-Za-z0-9._]+',
    'mastodon': r'[a-z0-9.\-]+\.[a-z]{2,}/@[A-Za-z0-9_]+(?=["\'\s<])',
    'bluesky': r'bsky\.app/profile/[A-Za-z0-9._:\-]+',
    'telegram': r't\.me/(?!share)[A-Za-z0-9_]{4,}',
    'discord': r'discord(?:\.gg|\.com/invite)/[A-Za-z0-9\-]+',
}


def _strip_www(host: str) -> str:
    host = (host or '').lower()
    return host[4:] if host.startswith('www.') else host


def extract_emails(text: str, soup=None) -> Set[str]:
    found = set()
    for e in EMAIL_RE.findall(text or ''):
        e = e.strip('.').lower()
        if e.endswith(_ASSET_EXT) or len(e) > 100 or re.search(r'@\d+x\.', e):
            continue
        if e.split('@')[1] in ('example.com', 'domain.com', 'email.com', 'sentry.io') or 'sentry' in e:
            continue
        found.add(e)
    for user, dom in OBFUSCATED_EMAIL_RE.findall(text or ''):
        dom = re.sub(r'\s*(?:\[dot\]|\(dot\)| dot )\s*', '.', dom, flags=re.I).replace(' ', '')
        cand = f"{user}@{dom}".lower()
        if EMAIL_RE.fullmatch(cand):
            found.add(cand)
    if soup is not None:
        for a in soup.select('a[href^="mailto:"]'):
            addr = unquote(a['href'][7:].split('?')[0]).strip().lower()
            for part in addr.split(','):
                if EMAIL_RE.fullmatch(part.strip()):
                    found.add(part.strip())
    return found


def extract_phones(visible_text: str, soup=None, region: str = 'US') -> Set[str]:
    """Phone numbers validated by libphonenumber (falls back to tel: links only)."""
    found = set()
    if soup is not None:
        for a in soup.select('a[href^="tel:"]'):
            raw = unquote(a['href'][4:]).strip()
            if raw:
                found.add(_fmt_phone(raw, region) or raw)
    try:
        import phonenumbers
        for m in phonenumbers.PhoneNumberMatcher(visible_text[:200000], region,
                                                 leniency=phonenumbers.Leniency.VALID):
            found.add(phonenumbers.format_number(m.number, phonenumbers.PhoneNumberFormat.INTERNATIONAL))
    except ImportError:
        pass
    return found


def _fmt_phone(raw: str, region: str) -> str:
    try:
        import phonenumbers
        n = phonenumbers.parse(raw, region)
        if phonenumbers.is_valid_number(n):
            return phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    except Exception:
        pass
    return ''


@dataclass
class PageInfo:
    url: str
    title: str = ""
    status_code: int = 0
    links: List[str] = field(default_factory=list)
    emails: Set[str] = field(default_factory=set)
    phones: Set[str] = field(default_factory=set)
    social_links: Dict[str, Set[str]] = field(default_factory=dict)
    forms: List[Dict] = field(default_factory=list)
    meta: Dict[str, str] = field(default_factory=dict)
    error: str = ""
    depth: int = 0
    response_time: float = 0.0


@dataclass
class CrawlResult:
    seed_url: str
    pages_crawled: int = 0
    all_emails: Set[str] = field(default_factory=set)
    all_phones: Set[str] = field(default_factory=set)
    all_social: Dict[str, Set[str]] = field(default_factory=dict)
    all_links: Set[str] = field(default_factory=set)
    external_links: Set[str] = field(default_factory=set)
    pages: List[PageInfo] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def normalize_url(url: str, base: str) -> Optional[str]:
    try:
        url, _ = urldefrag(url)
        if not url:
            return None
        if url.startswith(('mailto:', 'tel:', 'javascript:', '#')):
            return None
        parsed = urlparse(url)
        if not parsed.scheme:
            url = urljoin(base, url)
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return None
        if parsed.path.lower().endswith(_SKIP_EXT):
            return None
        return url.rstrip('/')
    except Exception:
        return None


def extract_page_info(url: str, depth: int = 0, timeout: int = 10) -> PageInfo:
    page = PageInfo(url=url, depth=depth)
    try:
        start = time.time()
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        except requests.exceptions.SSLError:
            resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True, verify=False)
            page.meta['_tls_warning'] = 'certificate failed verification'
        page.response_time = round((time.time() - start) * 1000, 1)
        page.status_code = resp.status_code

        content_type = resp.headers.get('content-type', '')
        if 'text/html' not in content_type and 'text/plain' not in content_type:
            return page

        soup = BeautifulSoup(resp.text, 'lxml')

        # Title
        title_tag = soup.find('title')
        page.title = title_tag.get_text(strip=True)[:200] if title_tag else ""

        # Meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name', meta.get('property', ''))
            content = meta.get('content', '')
            if name and content:
                page.meta[name] = content[:200]

        # All links
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        links = set()
        for a in soup.find_all('a', href=True):
            norm = normalize_url(a['href'], url)
            if norm:
                links.add(norm)
        page.links = list(links)

        text = resp.text
        for tag in soup(['script', 'style', 'noscript', 'template']):
            tag.decompose()
        visible = soup.get_text(' ', strip=True)

        page.emails = extract_emails(text, soup)
        page.phones = extract_phones(visible, soup)

        for platform, pattern in SOCIAL_PATTERNS.items():
            matches = {m.rstrip('/.') for m in re.findall(pattern, text, re.IGNORECASE)}
            if matches:
                page.social_links[platform] = {f"https://{m}" for m in matches}

        # Forms
        for form in soup.find_all('form'):
            inputs = []
            for inp in form.find_all(['input', 'textarea', 'select']):
                inputs.append({
                    'type': inp.get('type', 'text'),
                    'name': inp.get('name', ''),
                    'id': inp.get('id', ''),
                })
            page.forms.append({
                'action': form.get('action', ''),
                'method': form.get('method', 'get').upper(),
                'inputs': inputs,
            })

    except requests.exceptions.Timeout:
        page.error = "Timeout"
    except requests.exceptions.SSLError as e:
        page.error = f"SSL Error: {str(e)[:50]}"
    except Exception as e:
        page.error = str(e)[:100]

    return page


class CrawlerThread(QThread):
    page_crawled = pyqtSignal(object)   # PageInfo
    progress = pyqtSignal(str)
    finished = pyqtSignal(object)       # CrawlResult
    error = pyqtSignal(str)

    def __init__(self, seed_url: str, max_pages: int = 50, max_depth: int = 3,
                 same_domain_only: bool = True, delay: float = 0.5, respect_robots: bool = True):
        super().__init__()
        self.respect_robots = respect_robots
        self.seed_url = seed_url.strip()
        if not self.seed_url.startswith('http'):
            self.seed_url = 'https://' + self.seed_url
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.same_domain_only = same_domain_only
        self.delay = delay
        self._stop = False

    def stop(self):
        self._stop = True

    @staticmethod
    def _load_robots(seed: str):
        from urllib.robotparser import RobotFileParser
        p = urlparse(seed)
        rp = RobotFileParser()
        try:
            r = requests.get(f"{p.scheme}://{p.netloc}/robots.txt", headers=HEADERS, timeout=8)
            if r.status_code == 200 and 'html' not in r.headers.get('content-type', ''):
                rp.parse(r.text.splitlines())
                return rp
        except Exception:
            pass
        return None

    def run(self):
        result = CrawlResult(seed_url=self.seed_url)
        try:
            base_domain = urlparse(self.seed_url).netloc
            visited: Set[str] = set()
            queued: Set[str] = {self.seed_url.rstrip('/')}
            queue = deque([(self.seed_url, 0)])
            robots = self._load_robots(self.seed_url) if self.respect_robots else None

            while queue and len(visited) < self.max_pages and not self._stop:
                url, depth = queue.popleft()

                if url in visited or depth > self.max_depth:
                    continue
                if robots is not None and not robots.can_fetch(HEADERS['User-Agent'], url):
                    result.errors.append(f"robots.txt disallows {url}")
                    continue
                visited.add(url)

                self.progress.emit(f"[{len(visited)}/{self.max_pages}] Crawling: {url[:70]}...")

                page = extract_page_info(url, depth)
                result.pages.append(page)
                result.pages_crawled += 1

                # Accumulate findings
                result.all_emails.update(page.emails)
                result.all_phones.update(page.phones)
                for platform, links in page.social_links.items():
                    if platform not in result.all_social:
                        result.all_social[platform] = set()
                    result.all_social[platform].update(links)

                # Queue new links
                for link in page.links:
                    parsed = urlparse(link)
                    internal = _strip_www(parsed.netloc) == _strip_www(base_domain)
                    if internal:
                        result.all_links.add(link)
                    else:
                        result.external_links.add(link)
                    if (internal or not self.same_domain_only) and link not in queued \
                            and depth + 1 <= self.max_depth:
                        queued.add(link)
                        queue.append((link, depth + 1))

                self.page_crawled.emit(page)

                if self.delay > 0 and not self._stop:
                    time.sleep(self.delay)

            result.all_links = set(result.all_links)
            result.external_links = set(result.external_links)

            self.progress.emit(
                f"Crawl complete. {result.pages_crawled} pages, "
                f"{len(result.all_emails)} emails, {len(result.all_phones)} phones found."
            )
            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))
