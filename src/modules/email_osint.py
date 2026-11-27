"""
Inspector Rabbit - Email OSINT Module
Format/MX validation, disposable & free-provider detection, SMTP mailbox
probing with catch-all detection, Gravatar profile lookup, and breach data
from HaveIBeenPwned (API key) and XposedOrNot (free).
"""

import os
import re
import random
import socket
import string
import smtplib
import hashlib
from typing import List, Dict, Tuple
from dataclasses import dataclass, field

import requests
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from . import net

HEADERS = {'User-Agent': net.TOOL_UA, 'Accept': 'application/json'}

EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$"
)

DISPOSABLE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'disposable_domains.txt')

FREE_PROVIDERS = {
    'gmail.com', 'googlemail.com', 'outlook.com', 'hotmail.com', 'live.com', 'msn.com',
    'yahoo.com', 'ymail.com', 'aol.com', 'icloud.com', 'me.com', 'mac.com',
    'protonmail.com', 'proton.me', 'pm.me', 'gmx.com', 'gmx.net', 'gmx.de', 'web.de',
    'mail.com', 'zoho.com', 'yandex.com', 'yandex.ru', 'mail.ru', 'tutanota.com',
    'tuta.io', 'fastmail.com', 'hey.com', 'qq.com', '163.com', '126.com',
}

_disposable_cache = None


@dataclass
class EmailResult:
    email: str
    valid_format: bool = False
    domain_exists: bool = False
    smtp_valid: bool = False
    smtp_message: str = ""
    catch_all: bool = False
    disposable: bool = False
    free_provider: bool = False
    breaches: List[Dict] = field(default_factory=list)
    breach_error: str = ""
    breach_sources: List[str] = field(default_factory=list)
    social_profiles: List[Dict] = field(default_factory=list)
    gravatar_hash: str = ""
    gravatar_exists: bool = False
    gravatar_profile: Dict = field(default_factory=dict)
    email_patterns: List[str] = field(default_factory=list)
    mx_records: List[str] = field(default_factory=list)
    error: str = ""


def validate_format(email: str) -> bool:
    if len(email) > 254 or '..' in email:
        return False
    local = email.split('@')[0] if '@' in email else ''
    if not local or len(local) > 64 or local.startswith('.') or local.endswith('.'):
        return False
    return bool(EMAIL_PATTERN.match(email))


def get_mx_records(domain: str) -> List[str]:
    """MX hosts sorted by preference. Falls back to the implicit A-record MX (RFC 5321 §5.1)."""
    res = net.dns_query(domain, 'MX')
    mx = []
    for a in res.answers:
        parts = a.value.split()
        if len(parts) == 2:
            try:
                mx.append((int(parts[0]), parts[1].rstrip('.')))
            except ValueError:
                pass
    if any(not h for _, h in mx):
        return []                       # "0 ." null MX (RFC 7505): domain accepts no mail
    mx = [h for _, h in sorted(mx)]
    if mx:
        return mx
    if res.status in ('NODATA', 'NOERROR') and net.resolve(domain, 'A'):
        return [domain]
    return []


def _load_disposable() -> set:
    global _disposable_cache
    if _disposable_cache is None:
        try:
            with open(DISPOSABLE_FILE, 'r', encoding='utf-8') as f:
                _disposable_cache = {l.strip().lower() for l in f if l.strip() and not l.startswith('#')}
        except OSError:
            _disposable_cache = set()
    return _disposable_cache


def check_disposable(domain: str) -> bool:
    domain = domain.lower()
    lst = _load_disposable()
    parts = domain.split('.')
    return any('.'.join(parts[i:]) in lst for i in range(len(parts) - 1))


def _smtp_rcpt(mx: str, addresses: List[str], sender: str) -> Tuple[List[int], str]:
    server = smtplib.SMTP(timeout=12)
    server.connect(mx, 25)
    server.ehlo_or_helo_if_needed()
    try:
        if server.has_extn('starttls'):
            server.starttls()
            server.ehlo()
    except Exception:
        pass
    code, msg = server.mail(sender)
    if code != 250:
        server.quit()
        raise smtplib.SMTPResponseException(code, msg)
    codes, last = [], ''
    for addr in addresses:
        c, m = server.rcpt(addr)
        codes.append(c)
        last = m.decode(errors='replace') if isinstance(m, bytes) else str(m)
    try:
        server.quit()
    except Exception:
        pass
    return codes, last


def verify_smtp(email: str, mx_records: List[str],
                sender: str = "") -> Tuple[bool, str, bool]:
    """
    RCPT TO probe. Returns (mailbox_accepted, message, catch_all).
    A server that also accepts a random address is a catch-all, so a 250
    there proves nothing about the real mailbox.
    """
    if not mx_records:
        return False, "No MX records", False
    try:
        net.require_direct("SMTP verification (port 25)")
    except net.DirectNetworkBlocked as e:
        return False, str(e), False
    domain = email.split('@')[1]
    sender = sender or f"verify@{domain}"
    probe = 'zz' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=16)) + '@' + domain
    last_err = ''
    for mx in mx_records[:3]:
        try:
            codes, msg = _smtp_rcpt(mx, [email, probe], sender)
            real, fake = codes[0], codes[1]
            if real in (250, 251) and fake in (250, 251):
                return False, f"Server is catch-all ({mx}): accepts any address, mailbox unconfirmable", True
            if real in (250, 251):
                return True, f"Mailbox accepted by {mx} ({real})", False
            if real in (550, 551, 553):
                return False, f"Mailbox rejected by {mx} ({real}): {msg[:120]}", False
            if real in (450, 451, 452):
                return False, f"Temporary failure / greylisting ({real}) — inconclusive", False
            return False, f"Inconclusive response ({real}): {msg[:120]}", False
        except (socket.timeout, TimeoutError, ConnectionRefusedError, OSError) as e:
            last_err = f"{mx}: {e}"
        except smtplib.SMTPException as e:
            last_err = f"{mx}: {e}"
    hint = " — outbound port 25 is commonly blocked by home ISPs" if 'timed out' in last_err or 'refused' in last_err else ''
    return False, f"SMTP check failed ({last_err[:120]}){hint}", False


def check_gravatar(email: str) -> Tuple[str, bool, Dict]:
    normalized = email.lower().strip()
    sha = hashlib.sha256(normalized.encode()).hexdigest()
    profile = {}
    exists = False
    try:
        r = requests.get(f"https://www.gravatar.com/avatar/{sha}?d=404&s=80", timeout=10)
        exists = r.status_code == 200
    except Exception:
        pass
    try:
        r = requests.get(f"https://api.gravatar.com/v3/profiles/{sha}", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            d = r.json()
            exists = True
            profile = {
                'display_name': d.get('display_name', ''),
                'profile_url': d.get('profile_url', ''),
                'avatar_url': d.get('avatar_url', ''),
                'location': d.get('location', ''),
                'description': d.get('description', ''),
                'job_title': d.get('job_title', ''),
                'company': d.get('company', ''),
                'pronouns': d.get('pronouns', ''),
                'verified_accounts': [
                    {'service': a.get('service_label', a.get('service_type', '')),
                     'url': a.get('url', '')}
                    for a in d.get('verified_accounts', []) or []
                ],
            }
    except Exception:
        pass
    return sha, exists, profile


def check_haveibeenpwned(email: str, api_key: str = "") -> Tuple[List[Dict], str]:
    """HIBP v3 breached account lookup (requires API key)."""
    if not api_key:
        return [], "No HIBP API key configured (haveibeenpwned.com/API/Key)"
    try:
        resp = requests.get(
            f"https://haveibeenpwned.com/api/v3/breachedaccount/{requests.utils.quote(email)}",
            params={'truncateResponse': 'false'},
            headers={'hibp-api-key': api_key, 'User-Agent': net.TOOL_UA},
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json(), ""
        if resp.status_code == 404:
            return [], ""
        if resp.status_code == 401:
            return [], "Invalid HIBP API key"
        if resp.status_code == 429:
            return [], "Rate limited by HIBP"
        return [], f"HIBP error: HTTP {resp.status_code}"
    except Exception as e:
        return [], f"HIBP error: {e}"


def check_xposedornot(email: str) -> Tuple[List[Dict], str]:
    """XposedOrNot breach analytics (free, no key). Returns HIBP-shaped dicts."""
    try:
        r = requests.get('https://api.xposedornot.com/v1/breach-analytics',
                         params={'email': email}, headers=HEADERS, timeout=20)
        if r.status_code == 404:
            return [], ""
        if r.status_code == 429:
            return [], "XposedOrNot rate limited"
        if r.status_code != 200:
            return [], f"XposedOrNot HTTP {r.status_code}"
        d = r.json()
        details = ((d.get('ExposedBreaches') or {}).get('breaches_details')) or []
        out = []
        for b in details:
            out.append({
                'Name': b.get('breach', ''),
                'Title': b.get('breach', ''),
                'Domain': b.get('domain', ''),
                'BreachDate': str(b.get('xposed_date', '')),
                'PwnCount': b.get('xposed_records', 0),
                'Description': b.get('details', ''),
                'DataClasses': [x for x in (b.get('xposed_data') or '').split(';') if x],
                'IsVerified': str(b.get('verified', '')).lower() == 'yes',
                'PasswordRisk': b.get('password_risk', ''),
                'Source': 'XposedOrNot',
            })
        return out, ""
    except Exception as e:
        return [], f"XposedOrNot error: {e}"


def generate_email_patterns(first: str, last: str, domain: str) -> List[str]:
    f = re.sub(r'[^a-z0-9]', '', first.lower())
    l = re.sub(r'[^a-z0-9]', '', last.lower())
    domain = net.clean_host(domain)
    fi = f[:1]
    li = l[:1]
    patterns = [
        f"{f}", f"{l}", f"{f}.{l}", f"{f}{l}", f"{fi}{l}", f"{f}{li}", f"{f}_{l}",
        f"{l}.{f}", f"{l}{f}", f"{fi}.{l}", f"{l}_{f}", f"{f}-{l}", f"{fi}{li}",
        f"{l}.{fi}", f"{l}{fi}", f"{f}.{li}",
    ]
    seen, out = set(), []
    for p in patterns:
        if p and p not in seen and p not in ('.', '_', '-'):
            seen.add(p)
            out.append(f"{p}@{domain}")
    return out


class EmailOsintThread(QThread):
    progress = pyqtSignal(str)
    result_ready = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, email: str, hibp_api_key: str = "", verify_smtp_flag: bool = True):
        super().__init__()
        self.email = email.strip().lower()
        self.hibp_api_key = hibp_api_key
        self.verify_smtp_flag = verify_smtp_flag

    def run(self):
        result = EmailResult(email=self.email)
        try:
            self.progress.emit("Validating email format...")
            result.valid_format = validate_format(self.email)
            if not result.valid_format:
                result.error = "Invalid email format"
                self.result_ready.emit(result)
                return

            domain = self.email.split('@')[1]

            self.progress.emit(f"Checking mail servers for {domain}...")
            result.mx_records = get_mx_records(domain)
            result.domain_exists = bool(result.mx_records)

            result.disposable = check_disposable(domain)
            result.free_provider = domain in FREE_PROVIDERS

            if self.verify_smtp_flag and result.mx_records:
                self.progress.emit("SMTP mailbox probe (with catch-all detection)...")
                result.smtp_valid, result.smtp_message, result.catch_all = verify_smtp(
                    self.email, result.mx_records)
            else:
                result.smtp_message = "SMTP verification skipped"

            self.progress.emit("Checking Gravatar profile...")
            result.gravatar_hash, result.gravatar_exists, result.gravatar_profile = check_gravatar(self.email)
            for acct in result.gravatar_profile.get('verified_accounts', []):
                result.social_profiles.append(acct)

            errors = []
            seen = set()
            if self.hibp_api_key:
                self.progress.emit("Checking HaveIBeenPwned...")
                b, err = check_haveibeenpwned(self.email, self.hibp_api_key)
                result.breach_sources.append('HaveIBeenPwned')
                if err:
                    errors.append(err)
                for x in b:
                    x.setdefault('Source', 'HaveIBeenPwned')
                    seen.add(x.get('Name', '').lower())
                    result.breaches.append(x)

            self.progress.emit("Checking XposedOrNot breach database...")
            b, err = check_xposedornot(self.email)
            result.breach_sources.append('XposedOrNot')
            if err:
                errors.append(err)
            for x in b:
                if x.get('Name', '').lower() not in seen:
                    result.breaches.append(x)

            if not self.hibp_api_key:
                errors.append("HIBP skipped (no API key) — results from XposedOrNot only")
            result.breach_error = '; '.join(errors)

            self.progress.emit("Email OSINT complete.")
            self.result_ready.emit(result)

        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}")


class EmailPatternThread(QThread):
    result_ready = pyqtSignal(list)
    progress = pyqtSignal(str)

    def __init__(self, first_name: str, last_name: str, domain: str):
        super().__init__()
        self.first_name = first_name
        self.last_name = last_name
        self.domain = domain

    def run(self):
        self.progress.emit("Generating email patterns...")
        patterns = generate_email_patterns(self.first_name, self.last_name, self.domain)
        self.result_ready.emit(patterns)
