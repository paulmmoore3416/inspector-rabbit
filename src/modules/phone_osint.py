"""
Inspector Rabbit - Phone OSINT Module
Phone number analysis, validation, carrier, geolocation, format generation
"""

import re
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from PyQt6.QtCore import QObject, pyqtSignal, QThread


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0.0.0 Safari/537.36'
}


@dataclass
class PhoneResult:
    raw_input: str = ""
    is_valid: bool = False
    is_possible: bool = False
    formatted_national: str = ""
    formatted_international: str = ""
    formatted_e164: str = ""
    formatted_rfc3966: str = ""
    country_code: int = 0
    country_name: str = ""
    country_iso2: str = ""
    national_number: str = ""
    number_type: str = ""
    carrier: str = ""
    timezone: List[str] = field(default_factory=list)
    area_description: str = ""
    search_urls: List[Dict] = field(default_factory=list)
    error: str = ""


LINE_TYPES = {
    0: 'FIXED_LINE',
    1: 'MOBILE',
    2: 'FIXED_OR_MOBILE',
    3: 'TOLL_FREE',
    4: 'PREMIUM_RATE',
    5: 'SHARED_COST',
    6: 'VOIP',
    7: 'PERSONAL_NUMBER',
    8: 'PAGER',
    9: 'UAN',
    10: 'VOICEMAIL',
    99: 'UNKNOWN',
}


def analyze_phone(phone_input: str, default_region: str = "US") -> PhoneResult:
    result = PhoneResult(raw_input=phone_input)
    try:
        import phonenumbers
        from phonenumbers import (
            geocoder, carrier, timezone as tz_module,
            PhoneNumberFormat, NumberParseException
        )

        # Try parsing with region
        try:
            num = phonenumbers.parse(phone_input, default_region)
        except NumberParseException:
            try:
                num = phonenumbers.parse(f"+{phone_input.lstrip('+')}", None)
            except NumberParseException as e:
                result.error = str(e)
                return result

        result.is_valid = phonenumbers.is_valid_number(num)
        result.is_possible = phonenumbers.is_possible_number(num)
        result.country_code = num.country_code
        result.national_number = str(num.national_number)

        # Formatted versions
        try:
            result.formatted_national = phonenumbers.format_number(
                num, PhoneNumberFormat.NATIONAL)
        except Exception:
            pass
        try:
            result.formatted_international = phonenumbers.format_number(
                num, PhoneNumberFormat.INTERNATIONAL)
        except Exception:
            pass
        try:
            result.formatted_e164 = phonenumbers.format_number(
                num, PhoneNumberFormat.E164)
        except Exception:
            pass
        try:
            result.formatted_rfc3966 = phonenumbers.format_number(
                num, PhoneNumberFormat.RFC3966)
        except Exception:
            pass

        # Country
        result.country_iso2 = phonenumbers.region_code_for_number(num) or ""
        try:
            result.country_name = geocoder.country_name_for_number(num, "en")
        except Exception:
            pass

        # Area
        try:
            result.area_description = geocoder.description_for_number(num, "en")
        except Exception:
            pass

        # Number type
        num_type = phonenumbers.number_type(num)
        result.number_type = LINE_TYPES.get(num_type, 'UNKNOWN')

        # Carrier
        try:
            result.carrier = carrier.name_for_number(num, "en")
        except Exception:
            pass

        # Timezone
        try:
            result.timezone = list(tz_module.time_zones_for_number(num))
        except Exception:
            pass

        # Generate search URLs
        e164 = result.formatted_e164 or phone_input
        intl = result.formatted_international or phone_input
        national = result.formatted_national or phone_input

        result.search_urls = [
            {
                'name': 'Google Search',
                'url': f"https://www.google.com/search?q={e164.replace('+', '%2B')}",
                'description': 'Search Google for this number'
            },
            {
                'name': 'DuckDuckGo',
                'url': f"https://duckduckgo.com/?q={e164.replace('+', '%2B')}",
                'description': 'Search DuckDuckGo'
            },
            {
                'name': 'Truecaller',
                'url': f"https://www.truecaller.com/search/us/{national.replace(' ', '-').replace('(','').replace(')','').replace('+','')}",
                'description': 'Check Truecaller directory'
            },
            {
                'name': 'NumLookup',
                'url': f"https://www.numlookupapi.com/",
                'description': 'NumLookup API (registration required)'
            },
            {
                'name': 'Whitepages',
                'url': f"https://www.whitepages.com/phone/{national.replace(' ','').replace('(','').replace(')','').replace('-','')}",
                'description': 'Search Whitepages'
            },
            {
                'name': 'Social Media Search',
                'url': f"https://www.google.com/search?q={e164.replace('+', '%2B')}+site:facebook.com+OR+site:instagram.com+OR+site:linkedin.com",
                'description': 'Find social media profiles with this number'
            },
        ]

    except ImportError:
        result.error = "phonenumbers library not installed. Run: pip3 install phonenumbers"
    except Exception as e:
        result.error = str(e)

    return result


def generate_phone_variants(phone: str) -> List[str]:
    """Generate common formatting variants of a phone number"""
    # Clean the input
    clean = re.sub(r'[^\d+]', '', phone)
    digits = re.sub(r'[^\d]', '', phone)

    variants = set()
    variants.add(phone.strip())
    variants.add(clean)
    variants.add(digits)

    if len(digits) == 10:  # US number
        variants.update([
            f"({digits[:3]}) {digits[3:6]}-{digits[6:]}",
            f"{digits[:3]}-{digits[3:6]}-{digits[6:]}",
            f"{digits[:3]}.{digits[3:6]}.{digits[6:]}",
            f"+1{digits}",
            f"+1 {digits[:3]} {digits[3:6]} {digits[6:]}",
            f"+1-{digits[:3]}-{digits[3:6]}-{digits[6:]}",
        ])
    elif len(digits) == 11 and digits[0] == '1':  # US with country code
        d = digits[1:]
        variants.update([
            f"({d[:3]}) {d[3:6]}-{d[6:]}",
            f"+1 ({d[:3]}) {d[3:6]}-{d[6:]}",
            f"+1-{d[:3]}-{d[3:6]}-{d[6:]}",
        ])

    return sorted(variants)


class PhoneOsintThread(QThread):
    progress = pyqtSignal(str)
    result_ready = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, phone: str, region: str = "US"):
        super().__init__()
        self.phone = phone.strip()
        self.region = region

    def run(self):
        self.progress.emit(f"Analyzing phone number: {self.phone}")
        try:
            result = analyze_phone(self.phone, self.region)
            self.progress.emit("Phone analysis complete.")
            self.result_ready.emit(result)
        except Exception as e:
            self.error.emit(str(e))
