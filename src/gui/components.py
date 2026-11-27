"""
Inspector Rabbit - Shared UI Components
Re-usable helpers for consistent page styling across all modules.
"""

from PyQt6.QtWidgets import QFrame


# Per-module accent colours — keep in sync with dashboard feature cards
MODULE_ACCENTS: dict[str, str] = {
    # Space Gray palette — Apple system colors
    'username':   '#5ac8fa',   # teal
    'domain':     '#bf5af2',   # purple
    'email':      '#30d158',   # green
    'dorks':      '#ff9f0a',   # orange
    'ip':         '#ff453a',   # red
    'phone':      '#5ac8fa',   # teal
    'cert':       '#ffd60a',   # yellow
    'metadata':   '#ff9f0a',   # orange
    'pastes':     '#ff375f',   # pink
    'crawler':    '#0a84ff',   # blue
    'graph':      '#ff375f',   # pink
    'timeline':   '#5e5ce6',   # indigo
    'countersur': '#ff453a',   # red
    'settings':   '#8e8e93',   # gray
    # v1.4.0 — 9 new modules
    'revimage':   '#bf5af2',   # purple
    'breach':     '#ff453a',   # red
    'social':     '#30d158',   # green
    'geo':        '#5ac8fa',   # teal
    'darkweb':    '#bf5af2',   # purple
    'evidence':   '#5ac8fa',   # teal
    'netdiag':    '#ff9f0a',   # orange
    'batch':      '#8e8e93',   # gray
    'cases':      '#ff9f0a',   # orange
}


def apply_page_header_style(frame: QFrame, accent_color: str) -> None:
    """
    Apply the standard page header style with a per-module accent colour.

    Replaces the plain #010409 topbar with a dark gradient that has a
    coloured left-edge stripe and a matching bottom border, giving each
    module its own visual identity at a glance.

    Usage (in each page's _build_topbar):
        bar = QFrame()
        bar.setFixedHeight(64)
        apply_page_header_style(bar, "#00f5ff")
    """
    frame.setStyleSheet(f"""
        QFrame {{
            background: #161618;
            border-bottom: 1px solid #2c2c2e;
            border-left: 3px solid {accent_color};
        }}
    """)
