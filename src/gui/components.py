"""
Inspector Rabbit - Shared UI Components
Re-usable helpers for consistent page styling across all modules.
"""

from PyQt6.QtWidgets import QFrame


# Per-module accent colours — keep in sync with dashboard feature cards
MODULE_ACCENTS: dict[str, str] = {
    # original 14 modules
    'username':   '#00f5ff',
    'domain':     '#a78bfa',
    'email':      '#34d399',
    'dorks':      '#fb923c',
    'ip':         '#f87171',
    'phone':      '#22d3ee',
    'cert':       '#fbbf24',
    'metadata':   '#fb923c',
    'pastes':     '#f472b6',
    'crawler':    '#60a5fa',
    'graph':      '#f472b6',
    'timeline':   '#818cf8',
    'countersur': '#f85149',
    'settings':   '#8b949e',
    # v1.4.0 — 9 new modules
    'revimage':   '#e879f9',
    'breach':     '#ff6b6b',
    'social':     '#4ade80',
    'geo':        '#06b6d4',
    'darkweb':    '#a855f7',
    'evidence':   '#38bdf8',
    'netdiag':    '#f97316',
    'batch':      '#94a3b8',
    'cases':      '#f59e0b',
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
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #0e1824, stop:0.35 #0a0f1c, stop:1 #060b14);
            border-bottom: 1px solid {accent_color}33;
            border-left: 4px solid {accent_color};
        }}
    """)
