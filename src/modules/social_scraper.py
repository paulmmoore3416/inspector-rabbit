"""
Inspector Rabbit - Social Profile Scraper Module
Real data: GitHub API, Reddit API, YouTube channel scraping,
Twitch page scraping, Instagram og-meta, Twitter/X url-only,
TikTok url-only.
"""

import re
import time
import requests
from datetime import datetime, timezone
from PyQt6.QtCore import QThread, pyqtSignal

try:
    from bs4 import BeautifulSoup
    _BS4 = True
except ImportError:
    _BS4 = False


HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

JSON_HEADERS = {
    'User-Agent': 'InspectorRabbit/1.5.0',
    'Accept': 'application/json',
}

TIMEOUT = 12


def _fmt_date(ts) -> str:
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime('%Y-%m-%d')
    except Exception:
        return str(ts)


def _og(soup, prop: str) -> str:
    """Extract an Open Graph / Twitter Card meta tag value."""
    tag = soup.find('meta', property=prop) or soup.find('meta', attrs={'name': prop})
    if tag:
        return (tag.get('content') or '').strip()
    return ''


class SocialScrapeThread(QThread):
    profile_found = pyqtSignal(dict)
    progress      = pyqtSignal(str)
    done          = pyqtSignal(dict)

    def __init__(self, username: str, platforms: list):
        super().__init__()
        self._username  = username.strip()
        self._platforms = [p.lower() for p in platforms]
        self._found     = 0
        self._errors    = 0

    def run(self):
        self.progress.emit(f"Starting social profile scan for: {self._username}")
        self.progress.emit(f"Platforms: {', '.join(self._platforms)}")

        dispatch = {
            'github':    self._check_github,
            'reddit':    self._check_reddit,
            'youtube':   self._check_youtube,
            'twitch':    self._check_twitch,
            'instagram': self._check_instagram,
            'twitter':   self._check_twitter,
            'tiktok':    self._check_tiktok,
        }

        for platform in self._platforms:
            fn = dispatch.get(platform)
            if fn:
                try:
                    fn()
                    time.sleep(0.4)
                except Exception as e:
                    self.progress.emit(f"  ↳ {platform} error: {e}")
                    self._errors += 1

        self.progress.emit(f"Scan complete — {self._found} profile(s) found")
        self.done.emit({
            'username':          self._username,
            'platforms_checked': len(self._platforms),
            'found':             self._found,
            'errors':            self._errors,
        })

    # ── GitHub ─────────────────────────────────────────────────────────────────

    def _check_github(self):
        self.progress.emit("Checking GitHub API...")
        url = f"https://api.github.com/users/{self._username}"
        try:
            resp = requests.get(url, headers=JSON_HEADERS, timeout=TIMEOUT)
            if resp.status_code == 200:
                d = resp.json()
                self._found += 1
                self.progress.emit(f"  ↳ GitHub: found @{d.get('login', self._username)}")
                self.profile_found.emit({
                    'platform':     'GitHub',
                    'username':     d.get('login', self._username),
                    'display_name': d.get('name', '') or '',
                    'bio':          d.get('bio', '') or '',
                    'followers':    str(d.get('followers', 0)),
                    'following':    str(d.get('following', 0)),
                    'posts':        str(d.get('public_repos', 0)),
                    'verified':     'No',
                    'url':          d.get('html_url', f"https://github.com/{self._username}"),
                    'avatar_url':   d.get('avatar_url', ''),
                    'created_at':   d.get('created_at', ''),
                    'location':     d.get('location', '') or '',
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
                self.progress.emit("  ↳ GitHub: rate limited — try again later")
            else:
                self.progress.emit(f"  ↳ GitHub: HTTP {resp.status_code}")
        except Exception as e:
            self.progress.emit(f"  ↳ GitHub error: {e}")
            self._errors += 1

    # ── Reddit ─────────────────────────────────────────────────────────────────

    def _check_reddit(self):
        self.progress.emit("Checking Reddit API...")
        url = f"https://www.reddit.com/user/{self._username}/about.json"
        try:
            resp = requests.get(url, headers=JSON_HEADERS, timeout=TIMEOUT)
            if resp.status_code == 200:
                data = resp.json().get('data', {})
                self._found += 1
                name    = data.get('name', self._username)
                created = _fmt_date(data.get('created_utc', 0))
                icon    = data.get('icon_img', '')
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
                        'link_karma':         data.get('link_karma', 0),
                        'comment_karma':      data.get('comment_karma', 0),
                        'total_karma':        karma,
                        'is_gold':            data.get('is_gold', False),
                        'is_mod':             data.get('is_mod', False),
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

    # ── YouTube ────────────────────────────────────────────────────────────────

    def _check_youtube(self):
        """
        Scrape YouTube channel page for og tags and extract subscriber count
        from the page's inline JSON (ytInitialData). No API key required.
        """
        self.progress.emit("Checking YouTube (channel page scrape)...")
        if not _BS4:
            self.progress.emit("  ↳ YouTube: beautifulsoup4 not installed")
            self._errors += 1
            return

        url = f"https://www.youtube.com/@{self._username}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)

            if resp.status_code == 404:
                # Try legacy /user/ path
                url = f"https://www.youtube.com/user/{self._username}"
                resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)

            if resp.status_code != 200:
                self.progress.emit(f"  ↳ YouTube: HTTP {resp.status_code}")
                return

            soup = BeautifulSoup(resp.text, 'html.parser')
            title       = _og(soup, 'og:title')
            description = _og(soup, 'og:description')
            thumbnail   = _og(soup, 'og:image')

            if not title:
                self.progress.emit("  ↳ YouTube: channel not found or no og:title")
                return

            # Subscriber count lives inside ytInitialData JSON embedded in the page
            subs = '—'
            sub_match = re.search(
                r'"subscriberCountText":\{"simpleText":"([^"]+)"', resp.text
            )
            if sub_match:
                subs = sub_match.group(1)
            else:
                # Newer format
                sub_match2 = re.search(
                    r'"subscriberCountText":\{[^}]*?"text":"([^"]+)"', resp.text
                )
                if sub_match2:
                    subs = sub_match2.group(1)

            # Video count
            video_count = '—'
            vid_match = re.search(
                r'"videosCountText":\{"runs":\[\{"text":"([^"]+)"', resp.text
            )
            if vid_match:
                video_count = vid_match.group(1)

            # Channel ID
            channel_id = ''
            cid_match = re.search(r'"channelId":"(UC[^"]+)"', resp.text)
            if cid_match:
                channel_id = cid_match.group(1)

            # Joined date
            joined = ''
            joined_match = re.search(
                r'"joinedDateText":\{"runs":\[.*?"text":"([^"]+)"', resp.text
            )
            if joined_match:
                joined = joined_match.group(1)

            self._found += 1
            self.progress.emit(f"  ↳ YouTube: found @{self._username} — {subs} subscribers")
            self.profile_found.emit({
                'platform':     'YouTube',
                'username':     self._username,
                'display_name': title,
                'bio':          description[:250] if description else '',
                'followers':    subs,
                'following':    '—',
                'posts':        video_count,
                'verified':     '—',
                'url':          url,
                'avatar_url':   thumbnail,
                'created_at':   joined,
                'location':     '',
                'extra': {
                    'channel_id':   channel_id,
                    'subscribers':  subs,
                    'video_count':  video_count,
                    'channel_url':  url,
                },
            })

        except Exception as e:
            self.progress.emit(f"  ↳ YouTube error: {e}")
            self._errors += 1

    # ── Twitch ─────────────────────────────────────────────────────────────────

    def _check_twitch(self):
        """
        Scrape Twitch channel page og tags and extract inline JSON data.
        No OAuth required for basic public profile info.
        """
        self.progress.emit("Checking Twitch (channel page scrape)...")
        if not _BS4:
            self.progress.emit("  ↳ Twitch: beautifulsoup4 not installed")
            self._errors += 1
            return

        url = f"https://www.twitch.tv/{self._username}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if resp.status_code == 404:
                self.progress.emit("  ↳ Twitch: channel not found")
                return
            if resp.status_code != 200:
                self.progress.emit(f"  ↳ Twitch: HTTP {resp.status_code}")
                return

            soup = BeautifulSoup(resp.text, 'html.parser')
            title       = _og(soup, 'og:title') or _og(soup, 'twitter:title')
            description = _og(soup, 'og:description') or _og(soup, 'twitter:description')
            thumbnail   = _og(soup, 'og:image') or _og(soup, 'twitter:image')

            if not title:
                self.progress.emit("  ↳ Twitch: channel not found or blocked")
                return

            # Extract follower count from embedded JSON if available
            followers = '—'
            fol_match = re.search(
                r'"followers_count"\s*:\s*(\d+)', resp.text
            )
            if fol_match:
                followers = f"{int(fol_match.group(1)):,}"

            # Extract description from JSON if og:description is empty
            if not description:
                desc_match = re.search(
                    r'"description"\s*:\s*"([^"]{5,200})"', resp.text
                )
                if desc_match:
                    description = desc_match.group(1)

            # Live status
            is_live = 'Yes' if re.search(r'"isLiveBroadcast"\s*:\s*true', resp.text) else 'No'

            self._found += 1
            self.progress.emit(f"  ↳ Twitch: found {self._username} (live: {is_live})")
            self.profile_found.emit({
                'platform':     'Twitch',
                'username':     self._username,
                'display_name': title.replace(' - Twitch', '').strip(),
                'bio':          description[:250] if description else '',
                'followers':    followers,
                'following':    '—',
                'posts':        '—',
                'verified':     '—',
                'url':          url,
                'avatar_url':   thumbnail,
                'created_at':   '',
                'location':     '',
                'extra': {
                    'is_live':    is_live,
                    'channel_url': url,
                },
            })

        except Exception as e:
            self.progress.emit(f"  ↳ Twitch error: {e}")
            self._errors += 1

    # ── Instagram ──────────────────────────────────────────────────────────────

    def _check_instagram(self):
        """
        Scrape Instagram public profile page for og meta tags.
        Private accounts and heavy bot detection may block this.
        """
        self.progress.emit("Checking Instagram (og-meta scrape)...")
        if not _BS4:
            self.progress.emit("  ↳ Instagram: beautifulsoup4 not installed")
            self._errors += 1
            return

        url = f"https://www.instagram.com/{self._username}/"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if resp.status_code == 404:
                self.progress.emit("  ↳ Instagram: profile not found")
                return
            if resp.status_code != 200:
                self.progress.emit(f"  ↳ Instagram: HTTP {resp.status_code} — may require login")
                self._url_fallback('Instagram', url)
                return

            soup = BeautifulSoup(resp.text, 'html.parser')
            title       = _og(soup, 'og:title')
            description = _og(soup, 'og:description')
            thumbnail   = _og(soup, 'og:image')

            if not title or 'login' in resp.url.lower():
                self.progress.emit("  ↳ Instagram: redirected to login — URL only")
                self._url_fallback('Instagram', url)
                return

            # Parse "X Followers, Y Following, Z Posts — Full Name: ..."
            followers = following = posts = bio = ''
            if description:
                fol_m  = re.search(r'([\d,.KkMm]+)\s*Followers', description)
                fing_m = re.search(r'([\d,.KkMm]+)\s*Following', description)
                post_m = re.search(r'([\d,.KkMm]+)\s*Posts', description)
                if fol_m:  followers = fol_m.group(1)
                if fing_m: following = fing_m.group(1)
                if post_m: posts     = post_m.group(1)
                # Bio is after the last dash
                bio_m = re.search(r'-\s*(.+)$', description.strip())
                if bio_m: bio = bio_m.group(1).strip()

            display_name = title.replace('(@' + self._username + ')', '').replace('• Instagram', '').strip()

            self._found += 1
            self.progress.emit(f"  ↳ Instagram: found @{self._username} ({followers} followers)")
            self.profile_found.emit({
                'platform':     'Instagram',
                'username':     self._username,
                'display_name': display_name,
                'bio':          bio or description[:200],
                'followers':    followers or '—',
                'following':    following or '—',
                'posts':        posts or '—',
                'verified':     '—',
                'url':          url,
                'avatar_url':   thumbnail,
                'created_at':   '',
                'location':     '',
                'extra':        {'note': 'Public data from og:meta tags only'},
            })

        except Exception as e:
            self.progress.emit(f"  ↳ Instagram error: {e}")
            self._errors += 1

    # ── Twitter/X ──────────────────────────────────────────────────────────────

    def _check_twitter(self):
        """
        Twitter/X requires authentication for all API access and aggressively
        blocks unauthenticated scraping. Providing URL link only.
        """
        self.progress.emit("Twitter/X: API auth required — providing URL only")
        self._url_fallback(
            'Twitter/X',
            f"https://twitter.com/{self._username}",
            note='Twitter/X v2 API requires OAuth 2.0 bearer token for all endpoints'
        )

    # ── TikTok ─────────────────────────────────────────────────────────────────

    def _check_tiktok(self):
        """
        TikTok uses heavy fingerprinting and bot detection.
        Providing URL link only.
        """
        self.progress.emit("TikTok: bot detection active — providing URL only")
        self._url_fallback(
            'TikTok',
            f"https://www.tiktok.com/@{self._username}",
            note='TikTok uses aggressive bot detection; open URL manually in browser'
        )

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _url_fallback(self, platform: str, url: str, note: str = '') -> None:
        """Emit a URL-only result (profile exists but data cannot be fetched)."""
        self._found += 1
        self.profile_found.emit({
            'platform':     platform,
            'username':     self._username,
            'display_name': '',
            'bio':          'Open URL in browser to view profile',
            'followers':    '—',
            'following':    '—',
            'posts':        '—',
            'verified':     '—',
            'url':          url,
            'avatar_url':   '',
            'created_at':   '',
            'location':     '',
            'extra':        {'note': note or 'Data unavailable without authentication'},
        })
