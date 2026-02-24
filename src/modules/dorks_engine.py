"""
Inspector Rabbit - Google Dorks Engine
Execute dork searches via DuckDuckGo (no rate-limit blocks) and Google
"""

import json
import os
import time
import re
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from urllib.parse import quote_plus, urlencode
from bs4 import BeautifulSoup
from PyQt6.QtCore import QObject, pyqtSignal, QThread


DORKS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'dorks_templates.json')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'DNT': '1',
}


@dataclass
class DorkResult:
    query: str
    engine: str
    results: List[Dict] = field(default_factory=list)
    total_found: int = 0
    error: str = ""
    url: str = ""


def load_dork_templates() -> Dict:
    try:
        with open(DORKS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def build_dork_query(template: str, target: str) -> str:
    return template.replace('{target}', target)


def search_duckduckgo(query: str, max_results: int = 20) -> DorkResult:
    """Search DuckDuckGo with the given query"""
    result = DorkResult(query=query, engine='DuckDuckGo')
    encoded_q = quote_plus(query)
    result.url = f"https://duckduckgo.com/?q={encoded_q}"

    try:
        # DuckDuckGo HTML search
        resp = requests.get(
            'https://html.duckduckgo.com/html/',
            params={'q': query, 'kl': 'us-en'},
            headers=HEADERS,
            timeout=15
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'lxml')

        results = []
        for item in soup.select('.result'):
            title_tag = item.select_one('.result__title a')
            snippet_tag = item.select_one('.result__snippet')
            url_tag = item.select_one('.result__url')

            if title_tag:
                title = title_tag.get_text(strip=True)
                href = title_tag.get('href', '')
                # DuckDuckGo uses redirect URLs
                if 'uddg=' in href:
                    from urllib.parse import unquote, parse_qs, urlparse
                    parsed = urlparse(href)
                    qs = parse_qs(parsed.query)
                    href = unquote(qs.get('uddg', [''])[0])

                results.append({
                    'title': title,
                    'url': href,
                    'snippet': snippet_tag.get_text(strip=True) if snippet_tag else '',
                    'displayed_url': url_tag.get_text(strip=True) if url_tag else href,
                })

            if len(results) >= max_results:
                break

        result.results = results
        result.total_found = len(results)

    except requests.exceptions.Timeout:
        result.error = "Search request timed out"
    except Exception as e:
        result.error = str(e)

    return result


def search_bing(query: str, max_results: int = 20) -> DorkResult:
    """Search Bing as fallback"""
    result = DorkResult(query=query, engine='Bing')
    encoded_q = quote_plus(query)
    result.url = f"https://www.bing.com/search?q={encoded_q}"

    try:
        resp = requests.get(
            'https://www.bing.com/search',
            params={'q': query, 'count': max_results},
            headers={**HEADERS, 'Accept-Language': 'en-US,en;q=0.9'},
            timeout=15
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'lxml')

        results = []
        for item in soup.select('.b_algo'):
            h2 = item.select_one('h2')
            snippet = item.select_one('.b_caption p')
            cite = item.select_one('cite')

            if h2 and h2.find('a'):
                a = h2.find('a')
                results.append({
                    'title': a.get_text(strip=True),
                    'url': a.get('href', ''),
                    'snippet': snippet.get_text(strip=True) if snippet else '',
                    'displayed_url': cite.get_text(strip=True) if cite else '',
                })

            if len(results) >= max_results:
                break

        result.results = results
        result.total_found = len(results)

    except Exception as e:
        result.error = str(e)

    return result


def get_google_url(query: str) -> str:
    return f"https://www.google.com/search?q={quote_plus(query)}"


class DorkWorker(QThread):
    result_ready = pyqtSignal(object)   # DorkResult
    progress = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, queries: List[str], engine: str = 'duckduckgo',
                 max_results: int = 10, delay: float = 2.0):
        super().__init__()
        self.queries = queries
        self.engine = engine.lower()
        self.max_results = max_results
        self.delay = delay
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        for i, query in enumerate(self.queries):
            if self._stop:
                break

            self.progress.emit(f"Searching [{i+1}/{len(self.queries)}]: {query[:60]}...")

            if self.engine == 'bing':
                result = search_bing(query, self.max_results)
            else:
                result = search_duckduckgo(query, self.max_results)

            self.result_ready.emit(result)

            if i < len(self.queries) - 1 and not self._stop:
                time.sleep(self.delay)

        self.finished.emit()


def generate_dork_queries(target: str, template_keys: List[str] = None) -> List[Dict]:
    """Generate dork queries from templates for a target"""
    templates = load_dork_templates()
    queries = []

    for cat_key, cat_data in templates.get('categories', {}).items():
        for tmpl in cat_data.get('templates', []):
            if template_keys and tmpl['name'] not in template_keys:
                continue
            q = build_dork_query(tmpl['template'], target)
            queries.append({
                'query': q,
                'name': tmpl['name'],
                'category': cat_data['name'],
                'description': tmpl.get('description', ''),
                'google_url': get_google_url(q),
            })

    return queries
