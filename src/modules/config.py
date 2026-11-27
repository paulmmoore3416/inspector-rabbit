"""
Inspector Rabbit - Settings store

Single source of truth for user settings. The file holds API keys, so it is
written atomically and kept readable by the owner only (0600).
"""

import json
import os
import stat
import tempfile

# INSPECTOR_RABBIT_HOME relocates all app data (settings, timeline, cases,
# evidence) — used by the container and by the test-suite.
DATA_HOME = os.path.expanduser(os.environ.get("INSPECTOR_RABBIT_HOME", "~"))


def data_path(name: str) -> str:
    return os.path.join(DATA_HOME, name)


SETTINGS_FILE = os.environ.get(
    "INSPECTOR_RABBIT_SETTINGS",
    data_path(".inspector_rabbit_settings.json"),
)

DEFAULT_SETTINGS = {
    # API keys (all optional)
    'shodan_api_key': '',
    'hibp_api_key': '',
    'github_token': '',
    'intelx_api_key': '',
    'urlscan_api_key': '',
    'brave_api_key': '',
    'google_cse_key': '',
    'google_cse_cx': '',
    # Network privacy
    'proxy_mode': 'off',          # off | tor | custom
    'proxy_url': '',              # used when proxy_mode == custom (socks5h://host:port or http://host:port)
    'kill_switch': False,         # block all lookups when the proxy is unreachable
    'allow_direct_when_proxied': False,  # allow ping/traceroute/SMTP etc. that cannot be proxied
    # Scan behaviour
    'max_threads': 20,
    'request_timeout': 10,
    'crawl_delay': 0.5,
    'max_crawl_pages': 50,
    'max_crawl_depth': 3,
    'auto_graph': True,
    'show_found_only': False,
    'dork_engine': 'Auto',
    'dork_delay': 2.0,
}


def _harden(path: str) -> None:
    """Make sure only the owner can read the settings file."""
    try:
        if os.name == 'posix' and os.path.exists(path):
            mode = stat.S_IMODE(os.stat(path).st_mode)
            if mode & 0o077:
                os.chmod(path, 0o600)
    except OSError:
        pass


def load_settings() -> dict:
    _harden(SETTINGS_FILE)
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        if not isinstance(saved, dict):
            saved = {}
    except (OSError, ValueError):
        saved = {}
    merged = {**DEFAULT_SETTINGS, **saved}
    # Older versions stored "DuckDuckGo" as the default engine; DDG now blocks
    # scripted queries most of the time, so map it to the auto fallback chain.
    if merged.get('dork_engine') not in ('Auto', 'DuckDuckGo', 'Bing'):
        merged['dork_engine'] = 'Auto'
    return merged


def save_settings(settings: dict) -> None:
    """Atomically write settings with 0600 permissions."""
    data = {**DEFAULT_SETTINGS, **(settings or {})}
    directory = os.path.dirname(SETTINGS_FILE) or '.'
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.ir_settings_', dir=directory)
    try:
        if os.name == 'posix':
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, SETTINGS_FILE)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    _harden(SETTINGS_FILE)
