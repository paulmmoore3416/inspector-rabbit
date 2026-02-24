"""
Inspector Rabbit - Web Crawler Module
Spider websites, extract emails, phones, social links, and metadata
"""

import re
import time
import hashlib
from urllib.parse import urlparse, urljoin, urldefrag
from typing import Set, List, Dict, Optional, Callable
from dataclasses import dataclass, field
from collections import deque

import requests
from bs4 import BeautifulSoup
from PyQt6.QtCore import QObject, pyqtSignal, QThread


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
PHONE_RE = re.compile(
    r'(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}'
    r'|(?:\+\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}'
)
SOCIAL_PATTERNS = {
    'github': r'github\.com/[a-zA-Z0-9\-_]+',
    'twitter': r'twitter\.com/[a-zA-Z0-9_]+',
    'linkedin': r'linkedin\.com/(?:in|company)/[a-zA-Z0-9\-_]+',
    'instagram': r'instagram\.com/[a-zA-Z0-9._]+',
    'facebook': r'facebook\.com/[a-zA-Z0-9.]+',
    'youtube': r'youtube\.com/(?:c|channel|user)/[a-zA-Z0-9_\-]+',
    'tiktok': r'tiktok\.com/@[a-zA-Z0-9._]+',
}


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
        return url.rstrip('/')
    except Exception:
        return None


def extract_page_info(url: str, depth: int = 0, timeout: int = 10) -> PageInfo:
    page = PageInfo(url=url, depth=depth)
    try:
        start = time.time()
        resp = requests.get(url, headers=HEADERS, timeout=timeout,
                            allow_redirects=True, verify=False)
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

        # Emails
        text = resp.text
        emails = set(EMAIL_RE.findall(text))
        # Filter common false positives
        page.emails = {
            e for e in emails
            if not any(e.endswith(x) for x in ['.png', '.jpg', '.gif', '.css', '.js'])
            and len(e) < 100
        }

        # Phone numbers
        page.phones = set(PHONE_RE.findall(text))

        # Social links
        for platform, pattern in SOCIAL_PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                page.social_links[platform] = set(f"https://{m}" for m in matches)

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
                 same_domain_only: bool = True, delay: float = 0.5):
        super().__init__()
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

    def run(self):
        result = CrawlResult(seed_url=self.seed_url)
        try:
            base_domain = urlparse(self.seed_url).netloc
            visited: Set[str] = set()
            queue = deque([(self.seed_url, 0)])

            while queue and len(visited) < self.max_pages and not self._stop:
                url, depth = queue.popleft()

                if url in visited:
                    continue
                visited.add(url)

                if depth > self.max_depth:
                    continue

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
                    if link not in visited:
                        if self.same_domain_only:
                            if parsed.netloc == base_domain or parsed.netloc == f"www.{base_domain}":
                                result.all_links.add(link)
                                queue.append((link, depth + 1))
                            else:
                                result.external_links.add(link)
                        else:
                            result.all_links.add(link)
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
