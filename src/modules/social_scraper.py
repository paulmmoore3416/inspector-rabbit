"""
Inspector Rabbit - Social Profile Scraper Module

Pulls real public profile data from official / public JSON APIs wherever
they exist (GitHub, GitLab, Reddit, Bluesky, Mastodon, Keybase, HackerNews,
DEV, Chess.com, Lichess, Docker Hub) and from page metadata for YouTube and
Twitch.

Instagram, Twitter/X and TikTok cannot be verified without logging in.
Those are reported with status "unverified" and a link to check by hand.
They are NEVER counted as found.
"""

import re
import time
from datetime import datetime, timezone

import requests
from PyQt6.QtCore import QThread, pyqtSignal

from . import net

try:
    from bs4 import BeautifulSoup
    _BS4 = True
except ImportError:
    _BS4 = False

HEADERS = {
    'User-Agent': net.BROWSER_UA,
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}
JSON_HEADERS = {'User-Agent': net.TOOL_UA, 'Accept': 'application/json'}
TIMEOUT = 12

PLATFORMS = [
    ('github', '🐙 GitHub'), ('gitlab', '🦊 GitLab'), ('reddit', '🤖 Reddit'),
    ('bluesky', '🦋 Bluesky'), ('mastodon', '🐘 Mastodon (.social)'), ('keybase', '🔑 Keybase'),
    ('hackernews', '🟧 HackerNews'), ('devto', '👩‍💻 DEV.to'), ('youtube', '▶️  YouTube'),
    ('twitch', '🎮 Twitch'), ('chesscom', '♟️  Chess.com'), ('lichess', '♞ Lichess'),
    ('dockerhub', '🐳 Docker Hub'), ('twitter', '🐦 Twitter / X (manual)'),
    ('instagram', '📸 Instagram (manual)'), ('tiktok', '🎵 TikTok (manual)'),
]


def _fmt_date(ts) -> str:
    try:
        if isinstance(ts, (int, float)) or str(ts).replace('.', '').isdigit():
            v = float(ts)
            if v > 1e12:
                v /= 1000
            return datetime.fromtimestamp(v, tz=timezone.utc).strftime('%Y-%m-%d')
        return str(ts)[:10]
    except Exception:
        return str(ts or '')


def _og(soup, prop: str) -> str:
    tag = soup.find('meta', property=prop) or soup.find('meta', attrs={'name': prop})
    return (tag.get('content') or '').strip() if tag else ''


def _strip(s: str, n: int = 300) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s or '')).strip()[:n]


class SocialScrapeThread(QThread):
    profile_found = pyqtSignal(dict)
    progress = pyqtSignal(str)
    done = pyqtSignal(dict)

    def __init__(self, username: str, platforms: list):
        super().__init__()
        self._username = username.strip().lstrip('@')
        self._platforms = [p.lower() for p in platforms]
        self._found = 0
        self._unverified = 0
        self._errors = 0

    def run(self):
        u = self._username
        self.progress.emit(f"Starting social profile scan for: {u}")
        dispatch = {
            'github': self._check_github, 'gitlab': self._check_gitlab,
            'reddit': self._check_reddit, 'bluesky': self._check_bluesky,
            'mastodon': self._check_mastodon, 'keybase': self._check_keybase,
            'hackernews': self._check_hackernews, 'devto': self._check_devto,
            'youtube': self._check_youtube, 'twitch': self._check_twitch,
            'chesscom': self._check_chesscom, 'lichess': self._check_lichess,
            'dockerhub': self._check_dockerhub,
            'instagram': lambda: self._manual('Instagram', f"https://www.instagram.com/{u}/"),
            'twitter': lambda: self._manual('Twitter/X', f"https://x.com/{u}"),
            'tiktok': lambda: self._manual('TikTok', f"https://www.tiktok.com/@{u}"),
        }
        for platform in self._platforms:
            fn = dispatch.get(platform)
            if not fn:
                continue
            try:
                fn()
            except net.ProxyUnavailable as e:
                self.progress.emit(f"  ↳ {platform}: {e}")
                self._errors += 1
            except Exception as e:
                self.progress.emit(f"  ↳ {platform} error: {e}")
                self._errors += 1
            time.sleep(0.3)

        self.progress.emit(f"Scan complete — {self._found} verified profile(s)"
                           + (f", {self._unverified} need manual check" if self._unverified else ''))
        self.done.emit({
            'username': u,
            'platforms_checked': len(self._platforms),
            'found': self._found,
            'unverified': self._unverified,
            'errors': self._errors,
        })

    # ── helpers ──────────────────────────────────────────────────────────

    def _profile(self, platform, url, **kw):
        self._found += 1
        d = {
            'platform': platform, 'username': self._username, 'display_name': '', 'bio': '',
            'followers': '—', 'following': '—', 'posts': '—', 'verified': '—', 'url': url,
            'avatar_url': '', 'created_at': '', 'location': '', 'status': 'found', 'extra': {},
        }
        d.update({k: ('' if v is None else v) for k, v in kw.items()})
        for k in ('followers', 'following', 'posts'):
            if isinstance(d[k], int):
                d[k] = f"{d[k]:,}"
        self.progress.emit(f"  ✅ {platform}: found {d['username']}")
        self.profile_found.emit(d)

    def _not_found(self, platform):
        self.progress.emit(f"  ↳ {platform}: not found")

    def _http_issue(self, platform, resp):
        msg = {403: 'blocked (403)', 429: 'rate limited (429)'}.get(resp.status_code, f'HTTP {resp.status_code}')
        self.progress.emit(f"  ⚠️  {platform}: {msg} — result unknown")
        self._errors += 1

    def _manual(self, platform, url):
        """Login-walled platform: give the link, never claim the account exists."""
        self._unverified += 1
        self.progress.emit(f"  ❔ {platform}: cannot be verified without login — check manually")
        self.profile_found.emit({
            'platform': platform, 'username': self._username, 'display_name': '',
            'bio': 'UNVERIFIED — this platform requires login; open the link to check by hand.',
            'followers': '—', 'following': '—', 'posts': '—', 'verified': '—', 'url': url,
            'avatar_url': '', 'created_at': '', 'location': '', 'status': 'unverified',
            'extra': {'note': 'Not counted as found'},
        })

    def _get(self, url, json_api=True, **kw):
        return requests.get(url, headers=JSON_HEADERS if json_api else HEADERS, timeout=TIMEOUT, **kw)

    # ── platforms ────────────────────────────────────────────────────────

    def _check_github(self):
        r = self._get(f"https://api.github.com/users/{self._username}")
        if r.status_code == 404:
            return self._not_found('GitHub')
        if r.status_code != 200:
            return self._http_issue('GitHub', r)
        d = r.json()
        self._profile('GitHub', d.get('html_url'), username=d.get('login'),
                      display_name=d.get('name') or '', bio=d.get('bio') or '',
                      followers=d.get('followers', 0), following=d.get('following', 0),
                      posts=d.get('public_repos', 0), avatar_url=d.get('avatar_url', ''),
                      created_at=_fmt_date(d.get('created_at', '')), location=d.get('location') or '',
                      extra={'blog': d.get('blog') or '', 'company': d.get('company') or '',
                             'email': d.get('email') or '', 'twitter': d.get('twitter_username') or '',
                             'public_gists': d.get('public_gists', 0), 'type': d.get('type', ''),
                             'updated_at': d.get('updated_at', '')})

    def _check_gitlab(self):
        r = self._get("https://gitlab.com/api/v4/users", params={'username': self._username})
        if r.status_code != 200:
            return self._http_issue('GitLab', r)
        users = r.json()
        if not users:
            return self._not_found('GitLab')
        d = users[0]
        detail = self._get(f"https://gitlab.com/api/v4/users/{d['id']}")
        if detail.status_code == 200:
            d = {**d, **detail.json()}
        self._profile('GitLab', d.get('web_url'), username=d.get('username'),
                      display_name=d.get('name', ''), bio=d.get('bio') or '',
                      avatar_url=d.get('avatar_url', ''), created_at=_fmt_date(d.get('created_at', '')),
                      location=d.get('location') or '',
                      followers=d.get('followers', '—'), following=d.get('following', '—'),
                      extra={'state': d.get('state', ''), 'website': d.get('website_url') or '',
                             'organization': d.get('organization') or '', 'job_title': d.get('job_title') or ''})

    def _check_reddit(self):
        r = requests.get(f"https://www.reddit.com/user/{self._username}/about.json",
                         headers={'User-Agent': f'python:inspector-rabbit:{net.APP_VERSION} (OSINT research)'},
                         timeout=TIMEOUT)
        if r.status_code == 404:
            return self._not_found('Reddit')
        if r.status_code != 200:
            self._http_issue('Reddit', r)
            return self._manual('Reddit', f"https://www.reddit.com/user/{self._username}")
        data = r.json().get('data', {})
        if data.get('is_suspended'):
            return self._profile('Reddit', f"https://www.reddit.com/user/{self._username}",
                                 bio='Account suspended', extra={'is_suspended': True})
        sub = data.get('subreddit') or {}
        self._profile('Reddit', f"https://www.reddit.com/user/{data.get('name', self._username)}",
                      username=data.get('name', self._username),
                      display_name=sub.get('title') or '', bio=sub.get('public_description') or '',
                      followers=sub.get('subscribers', 0), posts=data.get('link_karma', 0),
                      verified='Yes' if data.get('verified') else 'No',
                      avatar_url=(data.get('icon_img') or '').split('?')[0],
                      created_at=_fmt_date(data.get('created_utc', 0)),
                      extra={'link_karma': data.get('link_karma', 0),
                             'comment_karma': data.get('comment_karma', 0),
                             'is_mod': data.get('is_mod', False),
                             'has_verified_email': data.get('has_verified_email', False)})

    def _check_bluesky(self):
        actor = self._username if '.' in self._username else f"{self._username}.bsky.social"
        r = self._get("https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile", params={'actor': actor})
        if r.status_code == 400:
            return self._not_found('Bluesky')
        if r.status_code != 200:
            return self._http_issue('Bluesky', r)
        d = r.json()
        self._profile('Bluesky', f"https://bsky.app/profile/{d.get('handle')}", username=d.get('handle'),
                      display_name=d.get('displayName', ''), bio=d.get('description', ''),
                      followers=d.get('followersCount', 0), following=d.get('followsCount', 0),
                      posts=d.get('postsCount', 0), avatar_url=d.get('avatar', ''),
                      created_at=_fmt_date(d.get('createdAt', '')), extra={'did': d.get('did', '')})

    def _check_mastodon(self):
        r = self._get("https://mastodon.social/api/v1/accounts/lookup", params={'acct': self._username})
        if r.status_code == 404:
            return self._not_found('Mastodon')
        if r.status_code != 200:
            return self._http_issue('Mastodon', r)
        d = r.json()
        self._profile('Mastodon', d.get('url'), username=d.get('acct'),
                      display_name=d.get('display_name', ''), bio=_strip(d.get('note', '')),
                      followers=d.get('followers_count', 0), following=d.get('following_count', 0),
                      posts=d.get('statuses_count', 0), avatar_url=d.get('avatar', ''),
                      created_at=_fmt_date(d.get('created_at', '')),
                      extra={'bot': d.get('bot', False), 'last_status_at': d.get('last_status_at') or '',
                             'fields': {f.get('name'): _strip(f.get('value', ''), 120) for f in d.get('fields', [])}})

    def _check_keybase(self):
        r = self._get("https://keybase.io/_/api/1.0/user/lookup.json",
                      params={'usernames': self._username,
                              'fields': 'basics,profile,proofs_summary,cryptocurrency_addresses'})
        if r.status_code != 200:
            return self._http_issue('Keybase', r)
        them = (r.json().get('them') or [None])[0]
        if not them:
            return self._not_found('Keybase')
        prof = them.get('profile') or {}
        proofs = (them.get('proofs_summary') or {}).get('all', []) or []
        self._profile('Keybase', f"https://keybase.io/{self._username}",
                      display_name=prof.get('full_name') or '', bio=prof.get('bio') or '',
                      location=prof.get('location') or '',
                      created_at=_fmt_date((them.get('basics') or {}).get('ctime', '')),
                      extra={'proofs': [f"{p.get('proof_type')}: {p.get('nametag')} ({p.get('service_url')})"
                                        for p in proofs]})

    def _check_hackernews(self):
        r = self._get(f"https://hacker-news.firebaseio.com/v0/user/{self._username}.json")
        if r.status_code != 200:
            return self._http_issue('HackerNews', r)
        d = r.json()
        if not d:
            return self._not_found('HackerNews')
        self._profile('HackerNews', f"https://news.ycombinator.com/user?id={d.get('id')}",
                      username=d.get('id'), bio=_strip(d.get('about', '')),
                      posts=len(d.get('submitted', []) or []), created_at=_fmt_date(d.get('created', 0)),
                      extra={'karma': d.get('karma', 0)})

    def _check_devto(self):
        r = self._get("https://dev.to/api/users/by_username", params={'url': self._username})
        if r.status_code == 404:
            return self._not_found('DEV.to')
        if r.status_code != 200:
            return self._http_issue('DEV.to', r)
        d = r.json()
        self._profile('DEV.to', f"https://dev.to/{d.get('username')}", username=d.get('username'),
                      display_name=d.get('name', ''), bio=d.get('summary') or '',
                      location=d.get('location') or '', avatar_url=d.get('profile_image', ''),
                      created_at=d.get('joined_at', ''),
                      extra={'twitter': d.get('twitter_username') or '', 'github': d.get('github_username') or '',
                             'website': d.get('website_url') or ''})

    def _check_chesscom(self):
        r = self._get(f"https://api.chess.com/pub/player/{self._username.lower()}")
        if r.status_code == 404:
            return self._not_found('Chess.com')
        if r.status_code != 200:
            return self._http_issue('Chess.com', r)
        d = r.json()
        self._profile('Chess.com', d.get('url'), username=d.get('username'), display_name=d.get('name', ''),
                      followers=d.get('followers', 0), avatar_url=d.get('avatar', ''),
                      created_at=_fmt_date(d.get('joined', 0)), location=d.get('location', ''),
                      extra={'country': (d.get('country') or '').rsplit('/', 1)[-1], 'status': d.get('status', ''),
                             'last_online': _fmt_date(d.get('last_online', 0)), 'title': d.get('title', '')})

    def _check_lichess(self):
        r = self._get(f"https://lichess.org/api/user/{self._username}")
        if r.status_code == 404:
            return self._not_found('Lichess')
        if r.status_code != 200:
            return self._http_issue('Lichess', r)
        d = r.json()
        if d.get('disabled'):
            return self._profile('Lichess', f"https://lichess.org/@/{d.get('username')}", bio='Account closed')
        prof = d.get('profile') or {}
        self._profile('Lichess', d.get('url'), username=d.get('username'),
                      display_name=prof.get('realName', ''), bio=prof.get('bio', ''),
                      location=prof.get('location', ''), posts=(d.get('count') or {}).get('all', 0),
                      created_at=_fmt_date(d.get('createdAt', 0)),
                      extra={'seen_at': _fmt_date(d.get('seenAt', 0)), 'links': prof.get('links', ''),
                             'flag': prof.get('flag', '')})

    def _check_dockerhub(self):
        r = self._get(f"https://hub.docker.com/v2/users/{self._username}/")
        if r.status_code == 404:
            return self._not_found('Docker Hub')
        if r.status_code != 200:
            return self._http_issue('Docker Hub', r)
        d = r.json()
        self._profile('Docker Hub', f"https://hub.docker.com/u/{d.get('username')}",
                      username=d.get('username'), display_name=d.get('full_name', ''),
                      location=d.get('location', ''), avatar_url=d.get('gravatar_url', ''),
                      created_at=_fmt_date(d.get('date_joined', '')),
                      extra={'company': d.get('company', ''), 'profile_url': d.get('profile_url', '')})

    def _check_youtube(self):
        if not _BS4:
            raise RuntimeError('beautifulsoup4 not installed')
        url = f"https://www.youtube.com/@{self._username}"
        r = self._get(url, json_api=False, cookies={'CONSENT': 'YES+1'})
        if r.status_code == 404:
            return self._not_found('YouTube')
        if r.status_code != 200:
            return self._http_issue('YouTube', r)
        if 'consent.youtube.com' in r.url:
            return self._manual('YouTube', url)
        soup = BeautifulSoup(r.text, 'html.parser')
        title = _og(soup, 'og:title')
        if not title:
            return self._not_found('YouTube')
        text = r.text

        def rx(p):
            m = re.search(p, text)
            return m.group(1) if m else ''
        subs = rx(r'"subscriberCountText":\{"simpleText":"([^"]+)"') or \
            rx(r'"subscriberCountText":\{[^}]*?"content":"([^"]+)"') or rx(r'([\d.,]+[KMB]? subscribers)')
        videos = rx(r'"videosCountText":\{"runs":\[\{"text":"([^"]+)"') or rx(r'([\d.,]+[KMB]? videos)')
        self._profile('YouTube', url, display_name=title, bio=_og(soup, 'og:description')[:250],
                      followers=subs or '—', posts=videos or '—', avatar_url=_og(soup, 'og:image'),
                      extra={'channel_id': rx(r'"(?:externalId|channelId)":"(UC[\w-]{22})"')})

    def _check_twitch(self):
        if not _BS4:
            raise RuntimeError('beautifulsoup4 not installed')
        url = f"https://www.twitch.tv/{self._username}"
        r = self._get(url, json_api=False)
        if r.status_code != 200:
            return self._http_issue('Twitch', r)
        soup = BeautifulSoup(r.text, 'html.parser')
        title = _og(soup, 'og:title')
        # Twitch serves the same SPA shell for every path; real channels get
        # "<name> - Twitch" as og:title, unknown ones just "Twitch".
        if not title or title.strip().lower() == 'twitch' or ' - Twitch' not in title:
            return self._not_found('Twitch')
        # Twitch's SSR occasionally glitches; require the same answer twice
        r2 = self._get(url, json_api=False)
        t2 = _og(BeautifulSoup(r2.text, 'html.parser'), 'og:title') if r2.status_code == 200 else ''
        if ' - Twitch' not in t2:
            self.progress.emit("  ⚠️  Twitch: inconsistent responses — result unknown")
            self._errors += 1
            return
        desc = _og(soup, 'og:description')
        self._profile('Twitch', url, display_name=title.replace(' - Twitch', '').strip(),
                      bio=desc[:250], avatar_url=_og(soup, 'og:image'),
                      extra={'is_live': 'Yes' if '"isLiveBroadcast":true' in r.text else 'No'})
