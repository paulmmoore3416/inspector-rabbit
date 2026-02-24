"""
Inspector Rabbit - Paste & Leak Scanner
Search public paste sites and GitHub for data leaks
"""

import time
import json
import re
import requests
from typing import List, Dict
from dataclasses import dataclass, field
from PyQt6.QtCore import QObject, pyqtSignal, QThread


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
}


@dataclass
class PasteResult:
    source: str = ""
    title: str = ""
    url: str = ""
    date: str = ""
    author: str = ""
    preview: str = ""
    matched_terms: List[str] = field(default_factory=list)
    risk_level: str = "low"   # low, medium, high


@dataclass
class PasteScanResult:
    query: str = ""
    total_found: int = 0
    results: List[PasteResult] = field(default_factory=list)
    sources_checked: List[str] = field(default_factory=list)
    high_risk_count: int = 0
    error: str = ""


RISK_KEYWORDS = {
    'high': [
        'password', 'passwd', 'credential', 'api_key', 'apikey', 'secret',
        'token', 'private_key', 'access_key', 'database', 'db_password',
        'connection_string', 'smtp_pass', 'ssh_key', 'BEGIN RSA',
    ],
    'medium': [
        'email', 'username', 'user', 'login', 'admin', 'config',
        'backup', 'dump', 'export', 'breach', 'leak', 'exposed',
    ],
    'low': ['found', 'test', 'demo', 'example'],
}


def assess_risk(text: str, matched_terms: List[str]) -> str:
    text_lower = text.lower()
    for term in RISK_KEYWORDS['high']:
        if term.lower() in text_lower:
            return 'high'
    for term in RISK_KEYWORDS['medium']:
        if term.lower() in text_lower:
            return 'medium'
    return 'low'


def search_github_gists(query: str, max_results: int = 20) -> List[PasteResult]:
    """Search GitHub public gists for mentions of query"""
    results = []
    try:
        resp = requests.get(
            'https://api.github.com/search/code',
            params={
                'q': query,
                'per_page': min(max_results, 30),
                'sort': 'indexed',
                'order': 'desc',
            },
            headers={
                **HEADERS,
                'Accept': 'application/vnd.github.v3+json',
            },
            timeout=15
        )

        if resp.status_code == 200:
            data = resp.json()
            for item in data.get('items', []):
                repo = item.get('repository', {})
                preview = ' | '.join([f.get('fragment', '') for f in item.get('text_matches', [])])[:200]
                risk = assess_risk(preview, [query])
                results.append(PasteResult(
                    source='GitHub',
                    title=item.get('name', 'Unknown'),
                    url=item.get('html_url', ''),
                    date=item.get('last_modified', ''),
                    author=repo.get('full_name', ''),
                    preview=preview or item.get('name', ''),
                    matched_terms=[query],
                    risk_level=risk,
                ))
        elif resp.status_code == 403:
            # Rate limited
            pass
    except Exception:
        pass
    return results


def search_github_repos(query: str, max_results: int = 20) -> List[PasteResult]:
    """Search GitHub repositories for query mentions"""
    results = []
    try:
        resp = requests.get(
            'https://api.github.com/search/repositories',
            params={
                'q': query,
                'per_page': min(max_results, 20),
                'sort': 'updated',
            },
            headers={
                **HEADERS,
                'Accept': 'application/vnd.github.v3+json',
            },
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get('items', []):
                results.append(PasteResult(
                    source='GitHub Repo',
                    title=item.get('full_name', ''),
                    url=item.get('html_url', ''),
                    date=item.get('updated_at', ''),
                    author=item.get('owner', {}).get('login', ''),
                    preview=item.get('description', '')[:200],
                    matched_terms=[query],
                    risk_level=assess_risk(item.get('description', ''), [query]),
                ))
    except Exception:
        pass
    return results


def search_hackernews(query: str, max_results: int = 15) -> List[PasteResult]:
    """Search HackerNews via Algolia API"""
    results = []
    try:
        resp = requests.get(
            'https://hn.algolia.com/api/v1/search',
            params={
                'query': query,
                'hitsPerPage': max_results,
                'tags': 'story,comment',
            },
            headers=HEADERS,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            for hit in data.get('hits', []):
                title = hit.get('title', '') or hit.get('story_title', '') or 'Comment'
                results.append(PasteResult(
                    source='HackerNews',
                    title=title,
                    url=hit.get('url', '') or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                    date=hit.get('created_at', ''),
                    author=hit.get('author', ''),
                    preview=hit.get('story_text', '') or hit.get('comment_text', '') or '',
                    matched_terms=[query],
                    risk_level='low',
                ))
    except Exception:
        pass
    return results


def search_reddit_pushshift(query: str, max_results: int = 10) -> List[PasteResult]:
    """Search Reddit via Pushshift API (public posts)"""
    results = []
    try:
        resp = requests.get(
            'https://api.pushshift.io/reddit/search/submission',
            params={'q': query, 'size': max_results, 'sort': 'desc', 'sort_type': 'score'},
            headers=HEADERS,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            for post in data.get('data', []):
                results.append(PasteResult(
                    source='Reddit',
                    title=post.get('title', ''),
                    url=f"https://reddit.com{post.get('permalink', '')}",
                    date=str(post.get('created_utc', '')),
                    author=post.get('author', ''),
                    preview=post.get('selftext', '')[:200],
                    matched_terms=[query],
                    risk_level=assess_risk(post.get('selftext', ''), [query]),
                ))
    except Exception:
        pass
    return results


def search_psbdmp(query: str) -> List[PasteResult]:
    """Search psbdmp.ws - Pastebin search engine"""
    results = []
    try:
        resp = requests.get(
            'https://psbdmp.ws/api/v3/search',
            params={'q': query},
            headers=HEADERS,
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get('data', []):
                paste_id = item.get('id', '')
                preview = item.get('text', '')[:300]
                results.append(PasteResult(
                    source='Pastebin (via psbdmp)',
                    title=item.get('title', '') or f"Paste {paste_id}",
                    url=f"https://pastebin.com/{paste_id}",
                    date=item.get('date', ''),
                    author=item.get('author', ''),
                    preview=preview,
                    matched_terms=[query],
                    risk_level=assess_risk(preview, [query]),
                ))
    except Exception:
        pass
    return results


class PasteScannerThread(QThread):
    result_ready = pyqtSignal(object)       # PasteResult (one at a time)
    progress = pyqtSignal(str)
    finished = pyqtSignal(object)           # PasteScanResult (final)
    error = pyqtSignal(str)

    def __init__(self, query: str, max_results_per_source: int = 20):
        super().__init__()
        self.query = query.strip()
        self.max_results = max_results_per_source
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        scan_result = PasteScanResult(query=self.query)
        all_results = []

        sources = [
            ('GitHub Code', search_github_gists),
            ('GitHub Repos', search_github_repos),
            ('HackerNews', search_hackernews),
            ('Pastebin (psbdmp)', search_psbdmp),
            ('Reddit', search_reddit_pushshift),
        ]

        for source_name, search_fn in sources:
            if self._stop:
                break
            self.progress.emit(f"Searching {source_name}...")
            try:
                results = search_fn(self.query)
                scan_result.sources_checked.append(source_name)
                for r in results:
                    all_results.append(r)
                    scan_result.total_found += 1
                    if r.risk_level == 'high':
                        scan_result.high_risk_count += 1
                    self.result_ready.emit(r)
            except Exception as e:
                self.progress.emit(f"  Error searching {source_name}: {e}")
            time.sleep(0.5)

        scan_result.results = all_results
        self.finished.emit(scan_result)
