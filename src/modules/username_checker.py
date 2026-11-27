"""
Inspector Rabbit - Username Checker Module

Checks whether a username exists across hundreds of sites.

Detection rules come from the Sherlock Project's site database (MIT licence,
https://github.com/sherlock-project/sherlock) and every bundled site has been
validated against a known-existing and a random non-existent username, so a
plain "HTTP 200" is never taken as proof that an account exists.
"""

import json
import os
import re
import threading
import time
import concurrent.futures
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from . import net

SITES_JSON = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'sites.json')

HEADERS = {
    'User-Agent': net.BROWSER_UA,
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# Responses that mean "we were blocked", not "the user does not exist"
_BLOCK_MARKERS = (
    'cf-browser-verification', 'challenge-platform', 'Just a moment...',
    'Attention Required! | Cloudflare', 'captcha-delivery.com',
    'px-captcha', 'Access Denied</title>',
)


@dataclass
class UsernameResult:
    site: str
    username: str
    url: str
    found: bool
    status_code: int = 0
    response_time: float = 0.0
    error: str = ""
    category: str = ""
    # 'found' | 'not_found' | 'invalid' (username not allowed on site) | 'error' | 'blocked'
    state: str = "not_found"


_sites_cache: Optional[Dict] = None
_sites_lock = threading.Lock()


def load_sites() -> Dict:
    """Return {site_name: site_rule}. Supports the old flat format too."""
    global _sites_cache
    with _sites_lock:
        if _sites_cache is not None:
            return _sites_cache
        try:
            with open(SITES_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return {}
        sites = data.get('sites', data) if isinstance(data, dict) else {}
        sites = {k: v for k, v in sites.items() if isinstance(v, dict) and not k.startswith('_')}
        _sites_cache = sites
        return sites


def _as_list(v) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _interpolate(obj, username):
    if isinstance(obj, str):
        return obj.replace('{}', username)
    if isinstance(obj, dict):
        return {k: _interpolate(v, username) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_interpolate(v, username) for v in obj]
    return obj


def check_single_site(site_name: str, site_data: dict, username: str,
                      timeout: int = 10, http: Optional[requests.Session] = None,
                      confirm: bool = False) -> UsernameResult:
    """Check one site. With confirm=True a 'found' must be reproduced by a second request."""
    first = _check_once(site_name, site_data, username, timeout, http)
    if confirm and first.found:
        second = _check_once(site_name, site_data, username, timeout, http)
        if not second.found:
            first.found = False
            first.state = 'error'
            first.error = 'Inconsistent responses (not confirmed)'
    return first


def _check_once(site_name: str, site_data: dict, username: str,
                timeout: int = 10, http: Optional[requests.Session] = None) -> UsernameResult:
    url = site_data.get('url', '').replace('{}', username)
    probe_url = (site_data.get('url_probe') or site_data.get('url', '')).replace('{}', username)
    error_type = site_data.get('error_type', 'status_code')
    category = site_data.get('category', 'other')
    res = UsernameResult(site=site_name, username=username, url=url,
                         found=False, category=category)

    regex = site_data.get('regex_check')
    if regex:
        try:
            if not re.search(regex, username):
                res.state = 'invalid'
                res.error = 'Username format not allowed on this site'
                return res
        except re.error:
            pass

    # GET everywhere unless the rule says otherwise: many sites answer HEAD
    # with 405/403, which would read as "not found".
    method = (site_data.get('request_method') or 'GET').upper()
    payload = _interpolate(site_data.get('request_payload'), username)
    headers = {**HEADERS, **(site_data.get('headers') or {})}
    # response_url detection relies on seeing the redirect itself
    allow_redirects = error_type != 'response_url'

    http = http or requests
    try:
        start = time.time()
        resp = http.request(method, probe_url, headers=headers, timeout=timeout,
                            allow_redirects=allow_redirects,
                            json=payload if payload is not None else None)
        res.response_time = round((time.time() - start) * 1000, 1)
        res.status_code = status = resp.status_code
        text = resp.text if method != 'HEAD' else ''

        if error_type == 'message':
            msgs = _as_list(site_data.get('error_msg'))
            found = not any(m in text for m in msgs) and status < 500
        elif error_type == 'status_code':
            codes = _as_list(site_data.get('error_code'))
            if codes:
                found = status not in codes and 200 <= status < 300
            else:
                found = 200 <= status < 300
        elif error_type == 'response_url':
            found = 200 <= status < 300
        else:
            found = 200 <= status < 300

        if not found and status in (403, 429, 503) or (
                text and any(m in text[:20000] for m in _BLOCK_MARKERS) and status >= 400):
            res.state = 'blocked'
            res.error = f'Blocked / rate-limited (HTTP {status})'
            res.found = False
            return res

        res.found = found
        res.state = 'found' if found else 'not_found'
        return res
    except requests.exceptions.Timeout:
        res.state, res.error = 'error', 'Timeout'
    except net.ProxyUnavailable as e:
        res.state, res.error = 'error', str(e)[:120]
    except requests.exceptions.ConnectionError:
        res.state, res.error = 'error', 'Connection Error'
    except Exception as e:
        res.state, res.error = 'error', str(e)[:80]
    return res


class UsernameWorker(QObject):
    """Qt worker for concurrent username checking with signals"""
    result_ready = pyqtSignal(object)   # UsernameResult
    progress = pyqtSignal(int, int)     # current, total
    finished = pyqtSignal(list)         # all results
    error = pyqtSignal(str)

    def __init__(self, username: str, site_filter: Optional[List[str]] = None,
                 max_threads: int = 20, timeout: int = 10, include_nsfw: bool = False):
        super().__init__()
        self.username = username.strip().lstrip('@')
        self.site_filter = site_filter
        self.max_threads = max(1, int(max_threads))
        self.timeout = timeout
        self.include_nsfw = include_nsfw
        self._stop = False
        self._results: List[UsernameResult] = []
        self._lock = threading.Lock()

    def stop(self):
        self._stop = True

    def run(self):
        sites = load_sites()
        if not sites:
            self.error.emit("Failed to load sites database")
            self.finished.emit([])
            return
        if self.site_filter:
            sites = {k: v for k, v in sites.items() if k in self.site_filter}
        if not self.include_nsfw:
            sites = {k: v for k, v in sites.items() if not v.get('nsfw')}

        items = list(sites.items())
        total = len(items)
        done = 0
        http = net.session(retries=1)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as ex:
            futures = {}
            for name, data in items:
                if self._stop:
                    break
                futures[ex.submit(check_single_site, name, data, self.username,
                                  self.timeout, http, True)] = name
            for fut in concurrent.futures.as_completed(futures):
                if self._stop:
                    for f in futures:
                        f.cancel()
                    break
                try:
                    result = fut.result()
                except Exception as e:  # pragma: no cover
                    result = UsernameResult(site=futures[fut], username=self.username,
                                            url='', found=False, error=str(e)[:80], state='error')
                with self._lock:
                    self._results.append(result)
                    done += 1
                self.result_ready.emit(result)
                self.progress.emit(done, total)

        self.finished.emit(self._results)


class UsernameCheckerThread(QThread):
    """QThread wrapper for UsernameWorker"""
    result_ready = pyqtSignal(object)
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, username: str, site_filter=None, max_threads=20, timeout=10,
                 include_nsfw=False):
        super().__init__()
        self.username = username
        self.site_filter = site_filter
        self.max_threads = max_threads
        self.timeout = timeout
        self.include_nsfw = include_nsfw
        self.worker = None

    def run(self):
        self.worker = UsernameWorker(
            self.username, self.site_filter, self.max_threads, self.timeout, self.include_nsfw
        )
        self.worker.result_ready.connect(self.result_ready)
        self.worker.progress.connect(self.progress)
        self.worker.finished.connect(self.finished)
        self.worker.error.connect(self.error)
        self.worker.run()

    def stop(self):
        if self.worker:
            self.worker.stop()
        self.quit()
        self.wait(3000)


def get_categories() -> List[str]:
    sites = load_sites()
    return sorted(set(v.get('category', 'other') for v in sites.values()))


def get_site_count() -> int:
    return len([v for v in load_sites().values() if not v.get('nsfw')])
