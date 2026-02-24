"""
Inspector Rabbit - Username Checker Module
Checks username availability across 100+ social platforms
"""

import json
import os
import time
import threading
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass, field

import requests
from PyQt6.QtCore import QObject, pyqtSignal, QThread

SITES_JSON = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'sites.json')

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}


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


def load_sites() -> Dict:
    try:
        with open(SITES_JSON, 'r') as f:
            return json.load(f)
    except Exception as e:
        return {}


def check_single_site(site_name: str, site_data: dict, username: str,
                       timeout: int = 10) -> UsernameResult:
    url_template = site_data.get('url', '')
    probe_template = site_data.get('url_probe', url_template)
    error_type = site_data.get('error_type', 'status_code')
    error_code = site_data.get('error_code', 404)
    error_msg = site_data.get('error_msg', '')
    category = site_data.get('category', 'other')

    url = url_template.format(username)
    probe_url = probe_template.format(username) if probe_template else url

    try:
        start = time.time()
        resp = requests.get(
            probe_url,
            headers=HEADERS,
            timeout=timeout,
            allow_redirects=True
        )
        elapsed = time.time() - start
        status = resp.status_code

        if error_type == 'status_code':
            found = status != error_code and status < 400
        elif error_type == 'message':
            found = error_msg not in resp.text
        elif error_type == 'response_url':
            found = error_msg not in resp.url
        else:
            found = status == 200

        return UsernameResult(
            site=site_name,
            username=username,
            url=url,
            found=found,
            status_code=status,
            response_time=round(elapsed * 1000, 1),
            category=category,
        )
    except requests.exceptions.Timeout:
        return UsernameResult(
            site=site_name, username=username, url=url,
            found=False, error="Timeout", category=category
        )
    except requests.exceptions.ConnectionError:
        return UsernameResult(
            site=site_name, username=username, url=url,
            found=False, error="Connection Error", category=category
        )
    except Exception as e:
        return UsernameResult(
            site=site_name, username=username, url=url,
            found=False, error=str(e)[:80], category=category
        )


class UsernameWorker(QObject):
    """Qt worker for async username checking with signals"""
    result_ready = pyqtSignal(object)   # UsernameResult
    progress = pyqtSignal(int, int)     # current, total
    finished = pyqtSignal(list)         # all results
    error = pyqtSignal(str)

    def __init__(self, username: str, site_filter: Optional[List[str]] = None,
                 max_threads: int = 20, timeout: int = 8):
        super().__init__()
        self.username = username.strip()
        self.site_filter = site_filter
        self.max_threads = max_threads
        self.timeout = timeout
        self._stop = False
        self._results: List[UsernameResult] = []
        self._lock = threading.Lock()

    def stop(self):
        self._stop = True

    def run(self):
        sites = load_sites()
        if not sites:
            self.error.emit("Failed to load sites database")
            return

        if self.site_filter:
            sites = {k: v for k, v in sites.items() if k in self.site_filter}

        site_items = list(sites.items())
        total = len(site_items)
        completed = [0]

        def check_and_emit(site_name, site_data):
            if self._stop:
                return
            result = check_single_site(site_name, site_data, self.username, self.timeout)
            with self._lock:
                self._results.append(result)
                completed[0] += 1
                self.result_ready.emit(result)
                self.progress.emit(completed[0], total)

        threads = []
        semaphore = threading.Semaphore(self.max_threads)

        def worker(site_name, site_data):
            with semaphore:
                check_and_emit(site_name, site_data)

        for site_name, site_data in site_items:
            if self._stop:
                break
            t = threading.Thread(target=worker, args=(site_name, site_data), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.finished.emit(self._results)


class UsernameCheckerThread(QThread):
    """QThread wrapper for UsernameWorker"""
    result_ready = pyqtSignal(object)
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, username: str, site_filter=None, max_threads=20, timeout=8):
        super().__init__()
        self.username = username
        self.site_filter = site_filter
        self.max_threads = max_threads
        self.timeout = timeout
        self.worker = None

    def run(self):
        self.worker = UsernameWorker(
            self.username, self.site_filter, self.max_threads, self.timeout
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
    return len(load_sites())
