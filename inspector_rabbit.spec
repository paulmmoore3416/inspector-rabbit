# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Inspector Rabbit v1.5.0
# Build command:  pyinstaller inspector_rabbit.spec
# Output:         dist/InspectorRabbit/InspectorRabbit.exe

import sys
from pathlib import Path

block_cipher = None

# ── Data files bundled with the exe ───────────────────────────────────────────
datas = [
    # OSINT data
    ("src/data/sites.json",           "src/data"),
    ("src/data/dorks_templates.json", "src/data"),
    # App icon / splash assets
    ("assets/favicon.ico",  "assets"),
    ("assets/favicon.png",  "assets"),
    ("assets/favicon-64.png", "assets"),
    ("assets/rabbit_running.gif", "assets"),
]

# ── Hidden imports that PyInstaller may miss ───────────────────────────────────
hiddenimports = [
    # Qt
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.QtNetwork",
    # networking
    "aiohttp",
    "aiohttp.connector",
    "aiohttp.client",
    "urllib3",
    "requests",
    "requests.adapters",
    # OSINT backends
    "dns",
    "dns.resolver",
    "whois",
    "bs4",
    "lxml",
    "lxml.etree",
    "lxml._elementpath",
    # charting
    "networkx",
    "matplotlib",
    "matplotlib.backends.backend_qtagg",
    # reporting
    "reportlab",
    "reportlab.pdfgen",
    "reportlab.lib",
    "reportlab.platypus",
    # utils
    "psutil",
    "cryptography",
    "OpenSSL",
    "colorama",
    "tqdm",
    "PIL",
    "PIL.Image",
    # app modules
    "src",
    "src.gui",
    "src.modules",
]

a = Analysis(
    ["inspector_rabbit.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "email",
        "html",
        "http.server",
        "xmlrpc",
        "ftplib",
        "poplib",
        "imaplib",
        "smtplib",
        "telnetlib",
        "nntplib",
        "antigravity",
        "this",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="InspectorRabbit",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,              # no black console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/favicon.ico",  # taskbar / window icon
    version_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="InspectorRabbit",
)
