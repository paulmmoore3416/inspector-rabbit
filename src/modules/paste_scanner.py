"""
Inspector Rabbit - Paste & Leak Scanner
Searches public code, discussion and paste sites for a term.

Sources
  * GitHub code search   — requires a GitHub token (free; Settings → API keys)
  * GitHub repositories  — public search API (no token needed, 10 req/min)
  * GitHub commits       — public search API
  * HackerNews           — Algolia API
  * Pastebin / Reddit    — searched through the dork engine (site: queries),
                           because Pastebin has no search API, psbdmp.ws is
                           offline and Reddit blocks unauthenticated API use.
"""

import html
import re
import time
from typing import List, Dict, Callable

import requests
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from . import net
from .config import load_settings

HEADERS = {'User-Agent': net.TOOL_UA, 'Accept': 'application/json'}

RISK_KEYWORDS = {
    'high': [
        'password', 'passwd', 'pwd=', 'credential', 'api_key', 'apikey', 'api-key',
        'secret', 'token', 'private_key', 'private key', 'access_key', 'aws_access_key_id',
        'db_password', 'connection_string', 'smtp_pass', 'ssh-rsa', 'begin rsa',
        'begin openssh', 'authorization: bearer', 'combolist', 'dump',
    ],
    'medium': [
        'email', 'username', 'login', 'admin', 'config', 'backup', 'export',
        'breach', 'leak', 'exposed', 'database',
    ],
}


def assess_risk(text: str) -> str:
    t = (text or '').lower()
    if any(k in t for k in RISK_KEYWORDS['high']):
        return 'high'
    if any(k in t for k in RISK_KEYWORDS['medium']):
        return 'medium'
    return 'low'


def _clean(text: str, n: int = 240) -> str:
    text = html.unescape(re.sub(r'<[^>]+>', ' ', text or ''))
    return re.sub(r'\s+', ' ', text).strip()[:n]


def _item(source, title, url, date='', author='', snippet='', risk=None, **extra) -> Dict:
    d = {
        'source': source, 'title': _clean(title, 160) or url, 'url': url,
        'date': str(date or ''), 'author': author or '', 'snippet': _clean(snippet),
        'risk': risk or assess_risk(f"{title} {snippet}"),
    }
    d.update(extra)
    return d


def _gh_headers(token: str) -> Dict:
    h = {'User-Agent': net.TOOL_UA, 'Accept': 'application/vnd.github.text-match+json',
         'X-GitHub-Api-Version': '2022-11-28'}
    if token:
        h['Authorization'] = f'Bearer {token}'
    return h


def _gh_error(resp) -> str:
    if resp.status_code == 401:
        return 'GitHub token rejected or missing'
    if resp.status_code in (403, 429):
        reset = resp.headers.get('X-RateLimit-Reset')
        wait = f" (resets in {max(0, int(reset) - int(time.time()))}s)" if reset else ''
        return f'GitHub rate limit reached{wait}'
    if resp.status_code == 422:
        return 'GitHub rejected the query (too short or invalid syntax)'
    return f'GitHub HTTP {resp.status_code}'


def search_github_code(query: str, max_results: int = 20, token: str = '') -> List[Dict]:
    if not token:
        raise RuntimeError("GitHub code search requires a token (Settings → GitHub token)")
    r = requests.get('https://api.github.com/search/code',
                     params={'q': query, 'per_page': min(max_results, 50)},
                     headers=_gh_headers(token), timeout=20)
    if r.status_code != 200:
        raise RuntimeError(_gh_error(r))
    out = []
    for it in r.json().get('items', []):
        repo = it.get('repository', {}) or {}
        frag = ' … '.join(m.get('fragment', '') for m in it.get('text_matches', []) or [])
        ext = it.get('name', '').rsplit('.', 1)[-1] if '.' in it.get('name', '') else ''
        out.append(_item('GitHub Code', f"{repo.get('full_name', '')}/{it.get('path', '')}",
                         it.get('html_url', ''), author=(repo.get('owner') or {}).get('login', ''),
                         snippet=frag, language=ext))
    return out


def search_github_repos(query: str, max_results: int = 20, token: str = '') -> List[Dict]:
    r = requests.get('https://api.github.com/search/repositories',
                     params={'q': query, 'per_page': min(max_results, 50), 'sort': 'updated'},
                     headers=_gh_headers(token), timeout=20)
    if r.status_code != 200:
        raise RuntimeError(_gh_error(r))
    return [
        _item('GitHub Repos', it.get('full_name', ''), it.get('html_url', ''),
              date=it.get('updated_at', ''), author=(it.get('owner') or {}).get('login', ''),
              snippet=it.get('description') or '', language=it.get('language') or '',
              risk=assess_risk(f"{it.get('full_name', '')} {it.get('description') or ''}"))
        for it in r.json().get('items', [])
    ]


def search_github_commits(query: str, max_results: int = 20, token: str = '') -> List[Dict]:
    r = requests.get('https://api.github.com/search/commits',
                     params={'q': query, 'per_page': min(max_results, 50), 'sort': 'committer-date'},
                     headers={**_gh_headers(token), 'Accept': 'application/vnd.github+json'}, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(_gh_error(r))
    out = []
    for it in r.json().get('items', []):
        c = it.get('commit', {}) or {}
        repo = (it.get('repository') or {}).get('full_name', '')
        msg = c.get('message', '')
        out.append(_item('GitHub Commits', f"{repo}: {msg.splitlines()[0] if msg else ''}",
                         it.get('html_url', ''), date=(c.get('committer') or {}).get('date', ''),
                         author=(c.get('author') or {}).get('name', ''), snippet=msg))
    return out


def search_hackernews(query: str, max_results: int = 20, **_) -> List[Dict]:
    r = requests.get('https://hn.algolia.com/api/v1/search',
                     params={'query': query, 'hitsPerPage': max_results, 'tags': '(story,comment)'},
                     headers=HEADERS, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(f'HN Algolia HTTP {r.status_code}')
    out = []
    for hit in r.json().get('hits', []):
        oid = hit.get('objectID', '')
        title = hit.get('title') or hit.get('story_title') or 'Comment'
        body = hit.get('story_text') or hit.get('comment_text') or ''
        out.append(_item('HackerNews', title, f"https://news.ycombinator.com/item?id={oid}",
                         date=hit.get('created_at', ''), author=hit.get('author', ''),
                         snippet=body, risk=assess_risk(body) if body else 'low',
                         external_url=hit.get('url') or ''))
    return out


def _dork_source(source: str, site: str):
    def fn(query: str, max_results: int = 20, **_) -> List[Dict]:
        from .dorks_engine import search_auto
        res = search_auto(f'site:{site} "{query}"', max_results)
        if not res.results and res.error:
            raise RuntimeError(f"via {res.engine}: {res.error}")
        out = []
        for r in res.results:
            pid = r['url'].rstrip('/').rsplit('/', 1)[-1] if source == 'Pastebin' else ''
            out.append(_item(source, r.get('title', ''), r.get('url', ''),
                             snippet=r.get('snippet', ''), id=pid, engine=res.engine))
        return out
    return fn


SOURCES: Dict[str, List[tuple]] = {
    'github': [('GitHub Code', search_github_code), ('GitHub Repos', search_github_repos),
               ('GitHub Commits', search_github_commits)],
    'hackernews': [('HackerNews', search_hackernews)],
    'pastebin': [('Pastebin', _dork_source('Pastebin', 'pastebin.com'))],
    'reddit': [('Reddit', _dork_source('Reddit', 'reddit.com'))],
}


class PasteScannerThread(QThread):
    result_ready = pyqtSignal(dict)       # one finding
    progress = pyqtSignal(str)
    finished = pyqtSignal()
    summary = pyqtSignal(dict)            # {total, high, sources_checked, errors}

    def __init__(self, query: str, sources: Dict[str, bool] = None, max_results_per_source: int = 20):
        super().__init__()
        self.query = query.strip()
        if isinstance(sources, dict):
            self.sources = {k for k, v in sources.items() if v}
        else:
            self.sources = set(SOURCES)
        self.max_results = max_results_per_source
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        token = load_settings().get('github_token', '')
        total, high, checked, errors = 0, 0, [], []
        seen = set()
        for key, fns in SOURCES.items():
            if key not in self.sources:
                continue
            for name, fn in fns:
                if self._stop:
                    break
                self.progress.emit(f"Searching {name}...")
                try:
                    items = fn(self.query, self.max_results, token=token)
                    checked.append(name)
                    self.progress.emit(f"{name}: {len(items)} result(s)")
                    for it in items:
                        if it['url'] in seen:
                            continue
                        seen.add(it['url'])
                        total += 1
                        high += it['risk'] == 'high'
                        self.result_ready.emit(it)
                except Exception as e:
                    errors.append(f"{name}: {e}")
                    self.progress.emit(f"⚠️ {name}: {e}")
                time.sleep(0.4)
        self.summary.emit({'total': total, 'high': high, 'sources_checked': checked, 'errors': errors})
        self.finished.emit()
