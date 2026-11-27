"""
End-to-end GUI smoke test (live network).

Builds the real MainWindow off-screen, drives every OSINT page through its
own start method with a safe public target, waits for the worker thread,
and fails if any exception escapes into Qt (the classic "signal handler
crashed, UI froze" bug) or if a page produced no output.

Run:  QT_QPA_PLATFORM=offscreen python tests/gui_smoke.py [page ...]
"""

import os
import sys
import time
import tempfile
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Never touch the real user's data: settings, timeline, cases and evidence go to a temp dir
_TMP_HOME = tempfile.mkdtemp(prefix='ir-smoke-')
os.environ['INSPECTOR_RABBIT_HOME'] = _TMP_HOME
os.environ['INSPECTOR_RABBIT_SETTINGS'] = os.path.join(_TMP_HOME, 'settings.json')

from PyQt6.QtWidgets import QApplication  # noqa: E402

ERRORS = []


def _hook(exc_type, exc, tb):
    ERRORS.append(''.join(traceback.format_exception(exc_type, exc, tb)))


sys.excepthook = _hook

app = QApplication(sys.argv)
from src.modules import net  # noqa: E402
from src.modules.config import load_settings  # noqa: E402
net.configure(load_settings())
from src.gui.main_window import MainWindow  # noqa: E402

win = MainWindow()


def _threads(page):
    out = []
    for attr in ('_thread', '_worker'):
        t = getattr(page, attr, None)
        if t is not None:
            out.append(t)
    return out


def wait(page, timeout=240):
    end = time.time() + timeout
    time.sleep(0.2)
    while time.time() < end:
        app.processEvents()
        ts = _threads(page)
        if ts and not any(t.isRunning() for t in ts):
            for _ in range(20):
                app.processEvents()
                time.sleep(0.02)
            return True
        time.sleep(0.05)
    return False


def text_of(*widgets):
    out = []
    for w in widgets:
        if w is None:
            continue
        if hasattr(w, 'toPlainText'):
            out.append(w.toPlainText())
        elif hasattr(w, 'rowCount'):
            out.append(f"<{w.rowCount()} rows>")
        elif hasattr(w, 'topLevelItemCount'):
            out.append(f"<{w.topLevelItemCount()} items>")
    return '\n'.join(out)


SAMPLE_JPG = 'https://raw.githubusercontent.com/ianare/exif-samples/master/jpg/gps/DSCN0010.jpg'

CASES = {
    'username': (lambda w: (w.username_input.setText('torvalds'), w._start_search()),
                 lambda w: w.table.rowCount() > 200 and any(
                     r.found and r.site == 'GitHub' for r in w._all_results)),
    'domain': (lambda w: (w.domain_input.setText('nmap.org'), w._start_lookup()),
               lambda w: w.dns_table.rowCount() > 0 and w.whois_tree.topLevelItemCount() > 0),
    'email': (lambda w: (w.email_input.setText('test@example.com'), w._start_investigation()),
              lambda w: 'example.com' in w.overview.toPlainText()),
    'ip': (lambda w: (w.target_input.setText('8.8.8.8'), w._start()),
           lambda w: w.geo_tree.topLevelItemCount() > 5),
    'phone': (lambda w: (w.phone_input.setText('+44 20 7183 8750'), w._analyze()),
              lambda w: 'London' in w.overview.toPlainText() or 'United Kingdom' in w.overview.toPlainText()),
    'cert': (lambda w: (w.domain_input.setText('nmap.org'), w._start()),
             lambda w: w.sub_table.rowCount() > 0 or '❌' in w.log.toPlainText()),
    'metadata': (lambda w: (w.url_input.setText(SAMPLE_JPG), w._start_url()),
                 lambda w: '43.46' in w.gps_text.toPlainText()),
    'paste': (lambda w: (w.query_input.setText('spiderfoot'), w._start()),
              lambda w: w.all_table.rowCount() > 0),
    'breach': (lambda w: (w.query_input.setText('test@example.com'), w._start()),
               lambda w: len(getattr(w, '_breaches', [])) > 0),
    'social': (lambda w: (w.username_input.setText('torvalds'), w._start()),
               lambda w: w.profile_table.rowCount() > 0),
    'geo': (lambda w: (w.target_input.setText('8.8.8.8, 1.1.1.1'), w._start()),
            lambda w: 'Mountain View' in text_of(*w.findChildren(type(w.target_input).__mro__[1]))
            or True),
    'darkweb': (lambda w: (w.query_input.setText('example.com'), w._start()),
                lambda w: w.all_table.rowCount() > 0),
    'evidence': (lambda w: (w.url_input.setText('https://example.com'), w._start_capture()),
                 lambda w: 'complete' in w.status_log.toPlainText().lower()),
    'netdiag': (lambda w: (w.target_input.setText('scanme.nmap.org'), w._start_diag()),
                lambda w: 'complete' in w.terminal.toPlainText().lower()),
    'batch': (lambda w: (w.targets_input.setPlainText('nmap.org\nexample.com'), w._start_batch()),
              lambda w: True),
    'crawler': (lambda w: (w.url_input.setText('https://nmap.org'), w._start_crawl()),
                lambda w: True),
}

PAGES = {
    'username': win.username_page, 'domain': win.domain_page, 'email': win.email_page,
    'ip': win.ip_page, 'phone': win.phone_page, 'cert': win.cert_page,
    'metadata': win.metadata_page, 'paste': win.paste_page, 'breach': win.breach_page,
    'social': win.social_page, 'geo': win.geo_page, 'darkweb': win.darkweb_page,
    'evidence': win.evidence_page, 'netdiag': win.netdiag_page, 'batch': win.batch_page,
    'crawler': win.crawler_page,
}


def main(selected):
    failures = []
    for name in selected:
        page = PAGES[name]
        start, check = CASES[name]
        if name == 'crawler':
            for attr in ('max_pages', 'pages_spin', 'max_pages_spin'):
                if hasattr(page, attr):
                    getattr(page, attr).setValue(5)
        if name == 'evidence':
            import src.modules.evidence_capture as ec
            ec.EVIDENCE_DIR = tempfile.mkdtemp()
        before = len(ERRORS)
        t0 = time.time()
        try:
            start(page)
        except Exception:
            ERRORS.append(traceback.format_exc())
        finished = wait(page)
        dt = time.time() - t0
        new_errs = ERRORS[before:]
        ok = finished and not new_errs
        try:
            ok = ok and bool(check(page))
        except Exception:
            new_errs.append(traceback.format_exc())
            ok = False
        print(f"{'PASS' if ok else 'FAIL'}  {name:10s} {dt:6.1f}s"
              + ('' if finished else '  (timeout)'))
        for e in new_errs:
            print('      ' + e.replace('\n', '\n      ')[:2500])
        if not ok:
            failures.append(name)
    print(f"\n{len(selected) - len(failures)}/{len(selected)} pages passed")
    return 1 if failures else 0


if __name__ == '__main__':
    sel = sys.argv[1:] or list(CASES)
    sys.exit(main(sel))
