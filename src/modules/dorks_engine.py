"""
Inspector Rabbit - Google Dorks Engine

Execution order in Auto mode:
  1. Brave Search API        (free key: https://brave.com/search/api/)
  2. Google Programmable Search JSON API (free key + engine id)
  3. Bing HTML (best effort)
  4. DuckDuckGo HTML (best effort)

Search engines block or poison scraped queries (bot challenges, or
unrelated filler results). Every result is therefore checked against the
query's site:/filetype:/inurl: operators and anything that does not match
is discarded, so off-target results are reported as an engine problem
instead of being shown as findings.
"""

import base64
import json
import os
import re
import time
from typing import List, Dict
from dataclasses import dataclass, field
from urllib.parse import quote_plus, unquote, parse_qs, urlparse

import requests
from bs4 import BeautifulSoup
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from . import net
from .config import load_settings

DORKS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'dorks_templates.json')

HEADERS = {
    'User-Agent': net.BROWSER_UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}


@dataclass
class DorkResult:
    query: str
    engine: str
    results: List[Dict] = field(default_factory=list)
    total_found: int = 0
    error: str = ""
    url: str = ""
    blocked: bool = False


def load_dork_templates() -> Dict:
    try:
        with open(DORKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def build_dork_query(template: str, target: str) -> str:
    return template.replace('{target}', target.strip())


def _ddg_unwrap(href: str) -> str:
    if 'uddg=' in href:
        qs = parse_qs(urlparse(href).query)
        return unquote(qs.get('uddg', [''])[0])
    if href.startswith('//'):
        return 'https:' + href
    return href


def search_duckduckgo(query: str, max_results: int = 20) -> DorkResult:
    result = DorkResult(query=query, engine='DuckDuckGo')
    result.url = f"https://duckduckgo.com/?q={quote_plus(query)}"
    try:
        resp = requests.post('https://html.duckduckgo.com/html/',
                             data={'q': query, 'kl': 'us-en'}, headers=HEADERS, timeout=15)
        if resp.status_code in (202, 403, 429) or 'anomaly-modal' in resp.text or 'anomaly.js' in resp.text:
            result.blocked = True
            result.error = "DuckDuckGo served a bot challenge (rate limited) — try Bing or wait"
            return result
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'lxml')
        for item in soup.select('.result'):
            if 'result--ad' in (item.get('class') or []):
                continue
            a = item.select_one('.result__title a') or item.select_one('a.result__a')
            if not a:
                continue
            href = _ddg_unwrap(a.get('href', ''))
            if not href.startswith('http') or 'duckduckgo.com/y.js' in href:
                continue
            snip = item.select_one('.result__snippet')
            disp = item.select_one('.result__url')
            result.results.append({
                'title': a.get_text(strip=True),
                'url': href,
                'snippet': snip.get_text(' ', strip=True) if snip else '',
                'displayed_url': disp.get_text(strip=True) if disp else href,
            })
            if len(result.results) >= max_results:
                break
        result.total_found = len(result.results)
    except requests.exceptions.Timeout:
        result.error = "Search request timed out"
    except Exception as e:
        result.error = str(e)[:200]
    return result


def _bing_unwrap(href: str) -> str:
    """Bing wraps results as /ck/a?...&u=a1<base64url(target)>."""
    if 'bing.com/ck/a' not in href:
        return href
    u = parse_qs(urlparse(href).query).get('u', [''])[0]
    if u.startswith('a1'):
        b = u[2:]
        b += '=' * (-len(b) % 4)
        try:
            return base64.urlsafe_b64decode(b).decode('utf-8', 'replace')
        except Exception:
            return href
    return href


def search_bing(query: str, max_results: int = 20) -> DorkResult:
    result = DorkResult(query=query, engine='Bing')
    result.url = f"https://www.bing.com/search?q={quote_plus(query)}"
    try:
        out, first = [], 1
        while len(out) < max_results and first < 60:
            resp = requests.get('https://www.bing.com/search',
                                params={'q': query, 'first': first, 'setlang': 'en-US', 'cc': 'US'},
                                headers=HEADERS, timeout=15)
            if resp.status_code in (403, 429) or '/challenge' in resp.url or 'captcha' in resp.text[:5000].lower():
                result.blocked = True
                result.error = "Bing served a CAPTCHA (rate limited) — wait and retry"
                break
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'lxml')
            items = soup.select('li.b_algo')
            if not items:
                break
            for item in items:
                a = item.select_one('h2 a')
                if not a:
                    continue
                href = _bing_unwrap(a.get('href', ''))
                if not href.startswith('http'):
                    continue
                snip = item.select_one('.b_caption p') or item.select_one('p')
                cite = item.select_one('cite')
                out.append({
                    'title': a.get_text(strip=True),
                    'url': href,
                    'snippet': snip.get_text(' ', strip=True) if snip else '',
                    'displayed_url': cite.get_text(strip=True) if cite else href,
                })
            first += len(items)
            if len(items) < 8:
                break
            time.sleep(1.0)
        seen, dedup = set(), []
        for r in out:
            if r['url'] not in seen:
                seen.add(r['url'])
                dedup.append(r)
        result.results = dedup[:max_results]
        result.total_found = len(result.results)
    except requests.exceptions.Timeout:
        result.error = "Search request timed out"
    except Exception as e:
        result.error = str(e)[:200]
    return result


def _operators(query: str) -> Dict[str, List[str]]:
    ops = {'site': [], 'filetype': [], 'inurl': []}
    for m in re.finditer(r'(?<![-\w])(site|filetype|ext|inurl):("([^"]+)"|\S+)', query, re.I):
        key = m.group(1).lower()
        key = 'filetype' if key == 'ext' else key
        ops[key].append((m.group(3) or m.group(2)).strip('"').lower())
    return ops


def validate_results(query: str, result: DorkResult) -> DorkResult:
    """Drop results that contradict the query operators (poisoned/irrelevant results)."""
    ops = _operators(query)
    if not result.results or not any(ops.values()):
        return result
    kept = []
    for r in result.results:
        u = r.get('url', '')
        p = urlparse(u)
        host = (p.hostname or '').lower()
        path = (p.path or '').lower()
        ok = True
        if ops['site']:
            ok &= any(host == s.lstrip('*.') or host.endswith('.' + s.lstrip('*.'))
                      or (('/' in s) and (host + path).startswith(s)) for s in ops['site'])
        if ops['filetype']:
            ok &= any(path.endswith('.' + ft) for ft in ops['filetype'])
        if ops['inurl']:
            ok &= any(t in u.lower() for t in ops['inurl'])
        if ok:
            kept.append(r)
    dropped = len(result.results) - len(kept)
    if dropped and not kept:
        result.blocked = True
        result.error = (f"{result.engine} returned {dropped} off-target results "
                        "(anti-bot filler) — discarded. Add a Brave/Google API key in Settings.")
    elif dropped:
        result.error = f"{dropped} off-target result(s) discarded"
    result.results = kept
    result.total_found = len(kept)
    return result


def search_brave_api(query: str, max_results: int = 20, api_key: str = '') -> DorkResult:
    result = DorkResult(query=query, engine='Brave API')
    result.url = f"https://search.brave.com/search?q={quote_plus(query)}"
    if not api_key:
        result.error = 'No Brave Search API key'
        return result
    try:
        r = requests.get('https://api.search.brave.com/res/v1/web/search',
                         params={'q': query, 'count': min(max_results, 20)},
                         headers={'X-Subscription-Token': api_key, 'Accept': 'application/json',
                                  'User-Agent': net.TOOL_UA}, timeout=15)
        if r.status_code == 401 or r.status_code == 422:
            result.error = 'Brave API key rejected'
            return result
        if r.status_code == 429:
            result.blocked = True
            result.error = 'Brave API quota/rate limit reached'
            return result
        r.raise_for_status()
        for it in (r.json().get('web') or {}).get('results', []):
            result.results.append({
                'title': it.get('title', ''),
                'url': it.get('url', ''),
                'snippet': re.sub(r'<[^>]+>', '', it.get('description', '')),
                'displayed_url': it.get('url', ''),
            })
        result.total_found = len(result.results)
    except Exception as e:
        result.error = f"Brave API: {e}"[:200]
    return result


def search_google_cse(query: str, max_results: int = 20, api_key: str = '', cx: str = '') -> DorkResult:
    result = DorkResult(query=query, engine='Google API')
    result.url = get_google_url(query)
    if not (api_key and cx):
        result.error = 'No Google Programmable Search key / engine id'
        return result
    try:
        start = 1
        while len(result.results) < max_results and start <= 91:
            r = requests.get('https://www.googleapis.com/customsearch/v1',
                             params={'key': api_key, 'cx': cx, 'q': query, 'start': start,
                                     'num': min(10, max_results - len(result.results))},
                             headers={'User-Agent': net.TOOL_UA}, timeout=15)
            if r.status_code == 429:
                result.blocked = True
                result.error = 'Google API daily quota reached'
                break
            if r.status_code != 200:
                result.error = f"Google API HTTP {r.status_code}: {r.text[:120]}"
                break
            items = r.json().get('items', [])
            for it in items:
                result.results.append({'title': it.get('title', ''), 'url': it.get('link', ''),
                                       'snippet': it.get('snippet', ''),
                                       'displayed_url': it.get('displayLink', '')})
            if len(items) < 10:
                break
            start += 10
        result.total_found = len(result.results)
    except Exception as e:
        result.error = f"Google API: {e}"[:200]
    return result


def search_auto(query: str, max_results: int = 20) -> DorkResult:
    s = load_settings()
    chain = []
    if s.get('brave_api_key'):
        chain.append(lambda: search_brave_api(query, max_results, s['brave_api_key']))
    if s.get('google_cse_key') and s.get('google_cse_cx'):
        chain.append(lambda: search_google_cse(query, max_results, s['google_cse_key'], s['google_cse_cx']))
    chain += [lambda: search_bing(query, max_results), lambda: search_duckduckgo(query, max_results)]
    errors, last = [], None
    for fn in chain:
        r = validate_results(query, fn())
        if r.results:
            if errors:
                r.error = (r.error + ' | ' if r.error else '') + 'fallbacks: ' + '; '.join(errors)
            return r
        errors.append(f"{r.engine}: {r.error or 'no results'}")
        last = r
    last.error = ' | '.join(errors)
    return last


def get_google_url(query: str) -> str:
    return f"https://www.google.com/search?q={quote_plus(query)}"


class DorkWorker(QThread):
    result_ready = pyqtSignal(object)   # DorkResult
    progress = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, queries: List[str], engine: str = 'auto',
                 max_results: int = 10, delay: float = 2.0):
        super().__init__()
        self.queries = queries
        self.engine = (engine or 'auto').lower()
        self.max_results = max_results
        self.delay = delay
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        direct = {'bing': search_bing, 'duckduckgo': search_duckduckgo}.get(self.engine)
        fn = (lambda q, n: validate_results(q, direct(q, n))) if direct else search_auto
        blocked_streak = 0
        for i, query in enumerate(self.queries):
            if self._stop:
                break
            self.progress.emit(f"Searching [{i+1}/{len(self.queries)}]: {query[:60]}...")
            result = fn(query, self.max_results)
            self.result_ready.emit(result)
            blocked_streak = blocked_streak + 1 if result.blocked else 0
            if blocked_streak >= 3:
                self.progress.emit("Search engines are blocking requests — stopping. "
                                   "Increase the delay or retry later.")
                break
            if i < len(self.queries) - 1 and not self._stop:
                time.sleep(self.delay * (3 if result.blocked else 1))
        self.finished.emit()


def generate_dork_queries(target: str, template_keys: List[str] = None) -> List[Dict]:
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
