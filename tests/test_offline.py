"""
Offline unit tests — no network access needed.

Run:  QT_QPA_PLATFORM=offscreen python -m pytest -q tests/test_offline.py
"""

import io
import os
import stat
import sys
import json
import socket
import zipfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile as _tf
os.environ['INSPECTOR_RABBIT_HOME'] = _tf.mkdtemp(prefix='ir-test-')
os.environ['INSPECTOR_RABBIT_SETTINGS'] = os.path.join(os.environ['INSPECTOR_RABBIT_HOME'], 'settings.json')


# ── settings store ────────────────────────────────────────────────────────────

def test_settings_written_owner_only(tmp_path, monkeypatch):
    from src.modules import config
    path = tmp_path / 'settings.json'
    monkeypatch.setattr(config, 'SETTINGS_FILE', str(path))
    config.save_settings({'hibp_api_key': 'k'})
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    os.chmod(path, 0o644)
    s = config.load_settings()                     # re-tightens on load
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert s['hibp_api_key'] == 'k' and s['proxy_mode'] == 'off'


def test_settings_corrupt_file_falls_back(tmp_path, monkeypatch):
    from src.modules import config
    path = tmp_path / 'settings.json'
    path.write_text('{not json')
    monkeypatch.setattr(config, 'SETTINGS_FILE', str(path))
    assert config.load_settings()['request_timeout'] == 10


# ── network policy ────────────────────────────────────────────────────────────

def _free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_kill_switch_blocks_when_proxy_down():
    import requests
    from src.modules import net
    port = _free_port()                      # nothing listening
    net.configure({'proxy_mode': 'custom', 'proxy_url': f'socks5h://127.0.0.1:{port}',
                   'kill_switch': True})
    try:
        with pytest.raises(net.ProxyUnavailable):
            requests.get('https://example.com', timeout=2)
        with pytest.raises(net.ProxyUnavailable):
            net.create_connection(('example.com', 443), timeout=2)
        assert not net.direct_allowed()
        with pytest.raises(net.DirectNetworkBlocked):
            net.require_direct('ping')
    finally:
        net.configure({'proxy_mode': 'off'})
    assert net.direct_allowed() and not net.proxy_active()


def test_socks5_upgraded_to_remote_dns():
    from src.modules import net
    net.configure({'proxy_mode': 'custom', 'proxy_url': 'socks5://127.0.0.1:1080'})
    try:
        assert net.proxy_url() == 'socks5h://127.0.0.1:1080'
    finally:
        net.configure({'proxy_mode': 'off'})


def test_clean_host_variants():
    from src.modules.net import clean_host
    assert clean_host('https://User@Example.COM:8443/path?q') == 'example.com'
    assert clean_host('example.com/abc') == 'example.com'
    assert clean_host('example.com:80') == 'example.com'
    assert clean_host('[2001:db8::1]') == '2001:db8::1'


def test_txt_join():
    from src.modules.net import _txt_join
    assert _txt_join('"v=spf1 a" " ~all"') == 'v=spf1 a ~all'


# ── username detection logic ──────────────────────────────────────────────────

class _Resp:
    def __init__(self, status=200, text=''):
        self.status_code = status
        self.text = text


class _Sess:
    def __init__(self, resp):
        self.resp = resp
        self.calls = []

    def request(self, method, url, **kw):
        self.calls.append((method, url, kw.get('allow_redirects')))
        return self.resp


def test_status_code_rule():
    from src.modules.username_checker import check_single_site
    rule = {'url': 'https://x.test/{}', 'error_type': 'status_code'}
    assert check_single_site('X', rule, 'bob', http=_Sess(_Resp(200))).found
    r = check_single_site('X', rule, 'bob', http=_Sess(_Resp(404)))
    assert not r.found and r.state == 'not_found'
    r = check_single_site('X', rule, 'bob', http=_Sess(_Resp(429)))
    assert r.state == 'blocked' and not r.found


def test_message_rule_and_list():
    from src.modules.username_checker import check_single_site
    rule = {'url': 'https://x.test/{}', 'error_type': 'message', 'error_msg': ['No such user', 'gone']}
    assert not check_single_site('X', rule, 'bob', http=_Sess(_Resp(200, 'Sorry, No such user'))).found
    assert check_single_site('X', rule, 'bob', http=_Sess(_Resp(200, '<h1>bob</h1>'))).found


def test_response_url_rule_disables_redirects():
    from src.modules.username_checker import check_single_site
    rule = {'url': 'https://x.test/{}', 'error_type': 'response_url'}
    s = _Sess(_Resp(302))
    assert not check_single_site('X', rule, 'bob', http=s).found
    assert s.calls[0][2] is False


def test_regex_check_marks_invalid():
    from src.modules.username_checker import check_single_site
    rule = {'url': 'https://x.test/{}', 'error_type': 'status_code', 'regex_check': '^[a-z]+$'}
    r = check_single_site('X', rule, 'Bad.Name', http=_Sess(_Resp(200)))
    assert r.state == 'invalid' and not r.found


def test_confirm_rejects_flapping_hit():
    from src.modules.username_checker import check_single_site

    class Flap(_Sess):
        def request(self, *a, **k):
            self.calls.append(1)
            return _Resp(200 if len(self.calls) == 1 else 404)
    r = check_single_site('X', {'url': 'https://x.test/{}', 'error_type': 'status_code'},
                          'bob', http=Flap(None), confirm=True)
    assert not r.found


def test_sites_db_is_validated_and_has_no_known_false_positive_rules():
    from src.modules.username_checker import load_sites
    with open(os.path.join(ROOT, 'src', 'data', 'sites.json')) as f:
        meta = json.load(f)['_meta']
    sites = load_sites()
    assert len(sites) >= 200 and meta['count'] == len(sites)
    # These answer 200 for every username without login — must not be plain status checks
    for name in ('Instagram', 'Twitter', 'Facebook'):
        assert name not in sites or sites[name]['error_type'] != 'status_code'
    for rule in sites.values():
        assert '{}' in rule['url'] or '{}' in rule.get('url_probe', '') \
            or '{}' in json.dumps(rule.get('request_payload', ''))


# ── DNSBL interpretation ──────────────────────────────────────────────────────

def test_blacklist_refusal_is_not_a_listing(monkeypatch):
    from src.modules import ip_intel, net

    def fake(name, rtype='A', timeout=0, **k):
        if 'spamhaus' in name:
            return net.DnsResult('NOERROR', [net.DnsAnswer('A', '127.255.255.254')])
        if 'spamcop' in name:
            return net.DnsResult('NOERROR', [net.DnsAnswer('A', '127.0.0.2')])
        return net.DnsResult('NXDOMAIN')
    monkeypatch.setattr(net, 'dns_query', fake)
    listed, notes = ip_intel.check_blacklists('203.0.113.7')
    assert 'zen.spamhaus.org' not in listed and 'refused' in notes['zen.spamhaus.org']
    assert listed['bl.spamcop.net'] is True
    assert listed['psbl.surriel.com'] is False


def test_ip_scope():
    from src.modules.ip_intel import ip_scope
    assert ip_scope('100.100.1.1').startswith('tailscale')
    assert ip_scope('192.168.1.1').startswith('private')
    assert ip_scope('8.8.8.8') == 'public'


# ── dorks ─────────────────────────────────────────────────────────────────────

def test_dork_validation_discards_off_target():
    from src.modules.dorks_engine import validate_results, DorkResult
    r = DorkResult(query='site:nmap.org filetype:pdf', engine='Bing', results=[
        {'url': 'https://www.drugs.com/x.html'},
        {'url': 'https://nmap.org/book/nmap.pdf'},
        {'url': 'https://svn.nmap.org/a.pdf'},
    ])
    out = validate_results(r.query, r)
    assert [x['url'] for x in out.results] == ['https://nmap.org/book/nmap.pdf', 'https://svn.nmap.org/a.pdf']
    r2 = DorkResult(query='site:nmap.org', engine='Bing', results=[{'url': 'https://drugs.com/'}])
    out2 = validate_results(r2.query, r2)
    assert not out2.results and out2.blocked


def test_bing_unwrap():
    import base64
    from src.modules.dorks_engine import _bing_unwrap
    target = 'https://nmap.org/book/'
    enc = 'a1' + base64.urlsafe_b64encode(target.encode()).decode().rstrip('=')
    assert _bing_unwrap(f'https://www.bing.com/ck/a?!&&p=x&u={enc}&ntb=1') == target


# ── crawler extraction ────────────────────────────────────────────────────────

def test_crawler_extraction_accuracy():
    from bs4 import BeautifulSoup
    from src.modules import web_crawler as w
    html = ('<p>Call +1 (415) 555-2671. Build 2015-11-23, id 1234567890.</p>'
            '<p>jane [at] acme [dot] com, logo@2x.png</p>'
            '<a href="mailto:sales@acme.org?subject=x">m</a><a href="tel:+442071838750">t</a>')
    soup = BeautifulSoup(html, 'lxml')
    assert w.extract_emails(html, soup) == {'jane@acme.com', 'sales@acme.org'}
    assert w.extract_phones(soup.get_text(' '), soup) == {'+1 415-555-2671', '+44 20 7183 8750'}


# ── metadata ──────────────────────────────────────────────────────────────────

def _jpeg_with_gps():
    from PIL import Image
    from PIL.ExifTags import IFD
    img = Image.new('RGB', (8, 8))
    ex = Image.Exif()
    ex[0x010F] = 'Canon'
    g = ex.get_ifd(IFD.GPSInfo)
    g[1], g[2], g[3], g[4] = 'S', (33.0, 52.0, 4.0), 'E', (151.0, 12.0, 26.0)
    b = io.BytesIO()
    img.save(b, 'JPEG', exif=ex)
    return b.getvalue()


def test_jpeg_gps_and_dict_contract():
    from src.modules.metadata_extractor import extract_metadata_from_bytes
    d = extract_metadata_from_bytes(_jpeg_with_gps(), 'a.jpg').to_dict()
    assert d['file_type'] == 'image' and d['make'] == 'Canon' and len(d['sha256']) == 64
    assert round(d['gps']['latitude'], 3) == -33.868 and round(d['gps']['longitude'], 3) == 151.207


def test_docx_core_properties():
    from src.modules.metadata_extractor import extract_metadata_from_bytes
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w') as z:
        z.writestr('word/document.xml', '<x/>')
        z.writestr('docProps/core.xml',
                   '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                   'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:creator>Jane</dc:creator></cp:coreProperties>')
    r = extract_metadata_from_bytes(b.getvalue(), 'a.docx')
    assert r.kind == 'office' and r.document_meta['Author'] == 'Jane'


def test_html_page_is_not_a_file():
    from src.modules.metadata_extractor import extract_metadata_from_bytes
    r = extract_metadata_from_bytes(b'<!DOCTYPE html><html>login</html>', 'x')
    assert 'HTML page' in r.error


# ── email ─────────────────────────────────────────────────────────────────────

def test_email_format_and_disposable():
    from src.modules.email_osint import validate_format, check_disposable, generate_email_patterns
    assert validate_format('a.b+tag@sub.example.co.uk')
    for bad in ('a@@b.com', '.a@b.com', 'a..b@c.com', 'a@b', 'a b@c.com'):
        assert not validate_format(bad)
    assert check_disposable('mailinator.com') and check_disposable('x.mailinator.com')
    assert not check_disposable('gmail.com')
    pats = generate_email_patterns('Jean-Luc', "O'Neil", 'https://Acme.com/')
    assert 'jeanluc.oneil@acme.com' in pats and len(pats) == len(set(pats))


def test_breach_severity_from_data_classes():
    from src.modules.breach_agg import severity_from_classes
    assert severity_from_classes(['Email addresses', 'Passwords']) == 'high'
    assert severity_from_classes(['Email addresses', 'Phone numbers']) == 'medium'
    assert severity_from_classes(['Email addresses']) == 'low'


# ── reports ───────────────────────────────────────────────────────────────────

def test_report_escapes_scraped_content():
    from src.modules.report_generator import generate_username_report
    from src.modules.username_checker import UsernameResult
    h = generate_username_report('<script>x</script>', [
        UsernameResult('Evil<img src=x onerror=alert(1)>', 'u', 'javascript:alert(1)', True)])
    assert '<script>x' not in h and 'onerror=alert(1)>' not in h and 'href="javascript' not in h


# ── counter-surveillance ──────────────────────────────────────────────────────

def test_outbound_connection_is_not_inbound():
    from collections import namedtuple
    from src.modules.connection_guard import is_inbound
    A = namedtuple('A', 'ip port')
    C = namedtuple('C', 'laddr raddr status')
    listen = {22, 631}
    assert not is_inbound(C(A('192.168.1.5', 51514), A('140.82.112.3', 443), 'ESTABLISHED'), listen)
    assert is_inbound(C(A('192.168.1.5', 22), A('203.0.113.9', 40000), 'ESTABLISHED'), listen)
    assert is_inbound(C(A('192.168.1.5', 8080), A('203.0.113.9', 40000), 'SYN_RECV'), listen)


def test_dns_canaries_are_fixed_anycast():
    from src.modules.dns_leak_monitor import CANARY_HOSTS, KNOWN_TRUSTED_DNS
    assert all(isinstance(exp, set) and exp for _, exp in CANARY_HOSTS)
    assert '100.100.100.100' in KNOWN_TRUSTED_DNS
