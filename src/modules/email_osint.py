"""
Inspector Rabbit - Email OSINT Module
Email validation, SMTP verification, pattern generation, breach checking
"""

import re
import socket
import smtplib
import dns.resolver
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from PyQt6.QtCore import QObject, pyqtSignal, QThread


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0.0.0 Safari/537.36'
}

EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')


@dataclass
class EmailResult:
    email: str
    valid_format: bool = False
    domain_exists: bool = False
    smtp_valid: bool = False
    smtp_message: str = ""
    disposable: bool = False
    breaches: List[Dict] = field(default_factory=list)
    breach_error: str = ""
    social_profiles: List[Dict] = field(default_factory=list)
    gravatar_hash: str = ""
    gravatar_exists: bool = False
    email_patterns: List[str] = field(default_factory=list)
    mx_records: List[str] = field(default_factory=list)
    error: str = ""


DISPOSABLE_DOMAINS = {
    'mailinator.com', 'guerrillamail.com', 'tempmail.com', '10minutemail.com',
    'throwaway.email', 'fakeinbox.com', 'trashmail.com', 'sharklasers.com',
    'yopmail.com', 'dispostable.com', 'maildrop.cc', 'spam4.me',
    'getnada.com', 'tempr.email', 'discard.email', 'spamgourmet.com',
    'mailnull.com', 'jetable.fr.nf', 'mailexpire.com', 'trashmail.at',
    'tempinbox.com', 'sofort-mail.de', 'spam.la', 'emailias.com',
    'nospamfor.us', 'throwam.com', 'maildrop.cc', 'inoutmail.com',
    'binkmail.com', 'bobmail.info', 'deadlymob.org', 'filzmail.com',
}


def validate_format(email: str) -> bool:
    return bool(EMAIL_PATTERN.match(email))


def get_mx_records(domain: str) -> List[str]:
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = 5
        answers = resolver.resolve(domain, 'MX')
        return sorted(
            [str(r.exchange).rstrip('.') for r in answers],
            key=lambda x: x
        )
    except Exception:
        return []


def verify_smtp(email: str, mx_records: List[str],
                sender: str = "osint@inspectorrabbit.local") -> tuple:
    """Try SMTP verify-without-sending (VRFY/RCPT TO). May not work on all servers."""
    if not mx_records:
        return False, "No MX records"

    for mx in mx_records[:2]:
        try:
            server = smtplib.SMTP(mx, 25, timeout=10)
            server.ehlo()
            code, msg = server.mail(sender)
            if code != 250:
                server.quit()
                continue
            code, msg = server.rcpt(email)
            server.quit()
            decoded = msg.decode() if isinstance(msg, bytes) else str(msg)
            if code in (250, 251):
                return True, f"RCPT accepted ({code}): {decoded}"
            elif code == 550:
                return False, f"User not found ({code}): {decoded}"
            else:
                return False, f"Unknown response ({code}): {decoded}"
        except smtplib.SMTPConnectError:
            continue
        except smtplib.SMTPServerDisconnected:
            continue
        except Exception as e:
            continue
    return False, "SMTP verification failed (server may block checks)"


def check_disposable(domain: str) -> bool:
    return domain.lower() in DISPOSABLE_DOMAINS


def check_gravatar(email: str) -> tuple:
    import hashlib
    email_hash = hashlib.md5(email.lower().strip().encode()).hexdigest()
    try:
        url = f"https://www.gravatar.com/avatar/{email_hash}?d=404"
        resp = requests.get(url, timeout=8)
        return email_hash, resp.status_code == 200
    except Exception:
        return email_hash, False


def check_haveibeenpwned(email: str, api_key: str = "") -> tuple:
    """Check breach data from HIBP API (requires paid API key for v3+)"""
    if not api_key:
        return [], "No HIBP API key configured (get one at haveibeenpwned.com/API/Key)"
    try:
        resp = requests.get(
            f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}",
            headers={
                'hibp-api-key': api_key,
                'User-Agent': 'InspectorRabbit-OSINT',
            },
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json(), ""
        elif resp.status_code == 404:
            return [], ""
        elif resp.status_code == 401:
            return [], "Invalid HIBP API key"
        elif resp.status_code == 429:
            return [], "Rate limited by HIBP"
        else:
            return [], f"HIBP error: {resp.status_code}"
    except Exception as e:
        return [], str(e)


def generate_email_patterns(first: str, last: str, domain: str) -> List[str]:
    f = first.lower()
    l = last.lower()
    fi = f[0] if f else ''
    li = l[0] if l else ''

    patterns = [
        f"{f}@{domain}",
        f"{l}@{domain}",
        f"{f}.{l}@{domain}",
        f"{f}{l}@{domain}",
        f"{fi}{l}@{domain}",
        f"{f}{li}@{domain}",
        f"{f}_{l}@{domain}",
        f"{l}.{f}@{domain}",
        f"{l}{f}@{domain}",
        f"{fi}.{l}@{domain}",
        f"{l}_{f}@{domain}",
        f"{f}-{l}@{domain}",
        f"{fi}{li}@{domain}",
        f"{l}.{fi}@{domain}",
    ]
    return [p for p in patterns if p and len(p) > len(f"@{domain}")]


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

            self.progress.emit(f"Checking MX records for {domain}...")
            result.mx_records = get_mx_records(domain)
            result.domain_exists = len(result.mx_records) > 0

            self.progress.emit("Checking if disposable email...")
            result.disposable = check_disposable(domain)

            if self.verify_smtp_flag and result.mx_records:
                self.progress.emit("Attempting SMTP verification...")
                result.smtp_valid, result.smtp_message = verify_smtp(
                    self.email, result.mx_records
                )
            else:
                result.smtp_message = "SMTP verification skipped"

            self.progress.emit("Checking Gravatar...")
            result.gravatar_hash, result.gravatar_exists = check_gravatar(self.email)

            if self.hibp_api_key:
                self.progress.emit("Checking HaveIBeenPwned...")
                result.breaches, result.breach_error = check_haveibeenpwned(
                    self.email, self.hibp_api_key
                )
            else:
                result.breach_error = "No HIBP API key (configure in Settings)"

            self.progress.emit("Email OSINT complete.")
            self.result_ready.emit(result)

        except Exception as e:
            self.error.emit(str(e))


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
