"""
Inspector Rabbit - Social Profile Scraper Module
Scrape public profile data from GitHub and Reddit; construct
profile URLs for platforms that block scraping.
"""

import time
import requests
from datetime import datetime, timezone
from PyQt6.QtCore import QThread, pyqtSignal


HEADERS = {
    'User-Agent': 'InspectorRabbit/1.3.0',
    'Accept': 'application/json',
}

TIMEOUT = 10


def _fmt_date(ts) -> str:
    """Convert a UNIX timestamp to an ISO date string."""
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime('%Y-%m-%d')
    except Exception:
        return str(ts)


class SocialScrapeThread(QThread):
    profile_found = pyqtSignal(dict)
    progress = pyqtSignal(str)
    done = pyqtSignal(dict)

    def __init__(self, username: str, platforms: list):
        super().__init__()
        self._username = username.strip()
        self._platforms = [p.lower() for p in platforms]
        self._found = 0
        self._errors = 0

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def run(self):
        self.progress.emit(f"Starting social profile scan for: {self._username}")
        self.progress.emit(f"Platforms: {', '.join(self._platforms)}")

        dispatch = {
            'github':    self._check_github,
            'reddit':    self._check_reddit,
            'twitter':   self._check_twitter,
            'instagram': self._check_instagram,
            'tiktok':    self._check_tiktok,
            'youtube':   self._check_youtube,
            'twitch':    self._check_twitch,
        }

        for platform in self._platforms:
            fn = dispatch.get(platform)
            if fn:
                try:
                    fn()
                except Exception as e:
                    self.progress.emit(f"  ↳ {platform} error: {e}")
                    self._errors += 1

        self.progress.emit(f"Scan complete — {self._found} profile(s) found")
        self.done.emit({
            'username': self._username,
            'platforms_checked': len(self._platforms),
            'found': self._found,
            'errors': self._errors,
        })

    # ------------------------------------------------------------------
    # GitHub
    # ------------------------------------------------------------------

    def _check_github(self):
        self.progress.emit("Checking GitHub...")
        url = f"https://api.github.com/users/{self._username}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if resp.status_code == 200:
                d = resp.json()
                self._found += 1
                self.progress.emit(f"  ↳ GitHub: found @{d.get('login', self._username)}")
                self.profile_found.emit({
                    'platform':      'GitHub',
                    'username':      d.get('login', self._username),
                    'display_name':  d.get('name', ''),
                    'bio':           d.get('bio', '') or '',
                    'followers':     str(d.get('followers', 0)),
                    'following':     str(d.get('following', 0)),
                    'posts':         str(d.get('public_repos', 0)),
                    'verified':      'No',
                    'url':           d.get('html_url', f"https://github.com/{self._username}"),
                    'avatar_url':    d.get('avatar_url', ''),
                    'created_at':    d.get('created_at', ''),
                    'location':      d.get('location', '') or '',
                    'extra': {
                        'blog':         d.get('blog', '') or '',
                        'company':      d.get('company', '') or '',
                        'public_repos': d.get('public_repos', 0),
                        'public_gists': d.get('public_gists', 0),
                        'type':         d.get('type', ''),
                        'hireable':     d.get('hireable', False),
                    },
                })
            elif resp.status_code == 404:
                self.progress.emit("  ↳ GitHub: profile not found")
            elif resp.status_code == 403:
                self.progress.emit("  ↳ GitHub: rate limited")
            else:
                self.progress.emit(f"  ↳ GitHub: HTTP {resp.status_code}")
        except Exception as e:
            self.progress.emit(f"  ↳ GitHub error: {e}")
            self._errors += 1

    # ------------------------------------------------------------------
    # Reddit
    # ------------------------------------------------------------------

    def _check_reddit(self):
        self.progress.emit("Checking Reddit...")
        url = f"https://www.reddit.com/user/{self._username}/about.json"
        headers = dict(HEADERS)
        try:
            resp = requests.get(url, headers=headers, timeout=TIMEOUT)
            if resp.status_code == 200:
                data = resp.json().get('data', {})
                self._found += 1
                name = data.get('name', self._username)
                created = _fmt_date(data.get('created_utc', 0))
                icon = data.get('icon_img', '')
                if '?' in icon:
                    icon = icon.split('?')[0]
                karma = data.get('link_karma', 0) + data.get('comment_karma', 0)
                self.progress.emit(f"  ↳ Reddit: found u/{name}")
                self.profile_found.emit({
                    'platform':     'Reddit',
                    'username':     name,
                    'display_name': data.get('subreddit', {}).get('title', '') or name,
                    'bio':          data.get('subreddit', {}).get('public_description', '') or '',
                    'followers':    str(data.get('subreddit', {}).get('subscribers', 0)),
                    'following':    '—',
                    'posts':        str(data.get('link_karma', 0)),
                    'verified':     'Yes' if data.get('verified', False) else 'No',
                    'url':          f"https://www.reddit.com/user/{name}",
                    'avatar_url':   icon,
                    'created_at':   created,
                    'location':     '',
                    'extra': {
                        'link_karma':    data.get('link_karma', 0),
                        'comment_karma': data.get('comment_karma', 0),
                        'total_karma':   karma,
                        'is_gold':       data.get('is_gold', False),
                        'is_mod':        data.get('is_mod', False),
                        'has_verified_email': data.get('has_verified_email', False),
                    },
                })
            elif resp.status_code == 404:
                self.progress.emit("  ↳ Reddit: user not found")
            elif resp.status_code == 429:
                self.progress.emit("  ↳ Reddit: rate limited")
            else:
                self.progress.emit(f"  ↳ Reddit: HTTP {resp.status_code}")
        except Exception as e:
            self.progress.emit(f"  ↳ Reddit error: {e}")
            self._errors += 1

    # ------------------------------------------------------------------
    # URL-only platforms
    # ------------------------------------------------------------------

    def _check_twitter(self):
        self.progress.emit("Twitter/X: constructing URL only (scraping blocked)")
        self._found += 1
        self.profile_found.emit({
            'platform':     'Twitter/X',
            'username':     self._username,
            'display_name': '',
            'bio':          'URL only — open in browser to view profile',
            'followers':    '—',
            'following':    '—',
            'posts':        '—',
            'verified':     '—',
            'url':          f"https://twitter.com/{self._username}",
            'avatar_url':   '',
            'created_at':   '',
            'location':     '',
            'extra':        {'note': 'Twitter/X does not allow unauthenticated API access'},
        })

    def _check_instagram(self):
        self.progress.emit("Instagram: constructing URL only (scraping blocked)")
        self._found += 1
        self.profile_found.emit({
            'platform':     'Instagram',
            'username':     self._username,
            'display_name': '',
            'bio':          'URL only — open in browser to view profile',
            'followers':    '—',
            'following':    '—',
            'posts':        '—',
            'verified':     '—',
            'url':          f"https://www.instagram.com/{self._username}/",
            'avatar_url':   '',
            'created_at':   '',
            'location':     '',
            'extra':        {'note': 'Instagram requires authentication for API access'},
        })

    def _check_tiktok(self):
        self.progress.emit("TikTok: constructing URL only (scraping blocked)")
        self._found += 1
        self.profile_found.emit({
            'platform':     'TikTok',
            'username':     self._username,
            'display_name': '',
            'bio':          'URL only — open in browser to view profile',
            'followers':    '—',
            'following':    '—',
            'posts':        '—',
            'verified':     '—',
            'url':          f"https://www.tiktok.com/@{self._username}",
            'avatar_url':   '',
            'created_at':   '',
            'location':     '',
            'extra':        {'note': 'TikTok blocks unauthenticated scraping'},
        })

    def _check_youtube(self):
        self.progress.emit("YouTube: constructing URL only (API key required)")
        self._found += 1
        self.profile_found.emit({
            'platform':     'YouTube',
            'username':     self._username,
            'display_name': '',
            'bio':          'URL only — open in browser to view channel',
            'followers':    '—',
            'following':    '—',
            'posts':        '—',
            'verified':     '—',
            'url':          f"https://www.youtube.com/@{self._username}",
            'avatar_url':   '',
            'created_at':   '',
            'location':     '',
            'extra':        {'note': 'YouTube Data API v3 key required for full data'},
        })

    def _check_twitch(self):
        self.progress.emit("Twitch: constructing URL only (API key required)")
        self._found += 1
        self.profile_found.emit({
            'platform':     'Twitch',
            'username':     self._username,
            'display_name': '',
            'bio':          'URL only — open in browser to view channel',
            'followers':    '—',
            'following':    '—',
            'posts':        '—',
            'verified':     '—',
            'url':          f"https://www.twitch.tv/{self._username}",
            'avatar_url':   '',
            'created_at':   '',
            'location':     '',
            'extra':        {'note': 'Twitch API requires OAuth client credentials'},
        })
