#!/usr/bin/env python3
"""
Inspector Rabbit - Advanced OSINT Suite
Entry point for the desktop application

Usage:
    python3 inspector_rabbit.py
    or
    inspector-rabbit  (after .deb install)
"""

import sys
import os
import math
import random

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Suppress SSL warnings for OSINT purposes
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import warnings
warnings.filterwarnings("ignore")


def main():
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QColor, QPalette

    app = QApplication(sys.argv)
    app.setApplicationName("Inspector Rabbit")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("InspectorRabbit")
    app.setStyle("Fusion")

    # Set global dark palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#0d1117"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#c9d1d9"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#161b22"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#0d1117"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#1f2937"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#c9d1d9"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#e6edf3"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#21262d"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#c9d1d9"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#00f5ff"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#1f6feb"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Link, QColor("#58a6ff"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#484f58"))
    app.setPalette(palette)

    # Animated splash screen
    splash = AnimatedSplash()
    splash.setWindowFlags(
        Qt.WindowType.SplashScreen |
        Qt.WindowType.FramelessWindowHint |
        Qt.WindowType.WindowStaysOnTopHint
    )
    splash.show()
    app.processEvents()

    # Import and create main window
    from src.gui.main_window import MainWindow
    window = MainWindow()

    def show_main():
        splash.stop()
        splash.finish(window)
        window.show()
        window.raise_()
        window.activateWindow()

    QTimer.singleShot(2800, show_main)
    sys.exit(app.exec())


class AnimatedSplash:
    """Animated splash screen with matrix rain and pulsing glow."""

    W, H = 640, 360

    def __init__(self):
        from PyQt6.QtWidgets import QSplashScreen
        from PyQt6.QtCore import QTimer
        from PyQt6.QtGui import QPixmap

        self._frame = 0
        self._matrix_cols = []
        self._init_matrix()
        self._pixmap = QPixmap(self.W, self.H)
        self._draw_frame()
        self._splash = QSplashScreen(self._pixmap)

        # Expose QSplashScreen interface
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)  # 20fps

    def _init_matrix(self):
        cols = self.W // 14
        self._matrix_cols = [
            {'y': random.randint(-self.H, 0), 'speed': random.randint(4, 12),
             'chars': [chr(random.randint(0x30A0, 0x30FF)) for _ in range(30)]}
            for _ in range(cols)
        ]

    def _tick(self):
        self._frame += 1
        for col in self._matrix_cols:
            col['y'] += col['speed']
            if col['y'] > self.H + 200:
                col['y'] = random.randint(-200, -20)
                col['speed'] = random.randint(4, 12)
            if random.random() < 0.05:
                col['chars'][random.randint(0, len(col['chars']) - 1)] = \
                    chr(random.randint(0x30A0, 0x30FF))
        self._draw_frame()
        self._splash.setPixmap(self._pixmap)

    def _draw_frame(self):
        from PyQt6.QtGui import (QPainter, QColor, QFont, QLinearGradient,
                                  QRadialGradient, QPen, QPixmap)
        from PyQt6.QtCore import QRectF, Qt

        self._pixmap = QPixmap(self.W, self.H)
        self._pixmap.fill(QColor("#010409"))

        p = QPainter(self._pixmap)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # ── Matrix rain ────────────────────────────────────────────────────
        p.setFont(QFont("Ubuntu Mono", 11))
        col_w = self.W // len(self._matrix_cols) if self._matrix_cols else 14
        for ci, col in enumerate(self._matrix_cols):
            x = ci * col_w
            for ri, ch in enumerate(col['chars']):
                y = col['y'] - ri * 14
                if y < -14 or y > self.H + 14:
                    continue
                alpha = max(0, min(255, int(255 * (1 - ri / len(col['chars'])))))
                if ri == 0:
                    p.setPen(QColor(200, 255, 220, alpha))
                else:
                    p.setPen(QColor(0, 120 + random.randint(0, 60), 60, alpha // 2))
                p.drawText(x, int(y), ch)

        # ── Dark overlay gradient ──────────────────────────────────────────
        overlay = QLinearGradient(0, 0, 0, self.H)
        overlay.setColorAt(0.0, QColor(1, 4, 9, 180))
        overlay.setColorAt(0.35, QColor(1, 4, 9, 80))
        overlay.setColorAt(0.65, QColor(1, 4, 9, 80))
        overlay.setColorAt(1.0, QColor(1, 4, 9, 200))
        p.fillRect(0, 0, self.W, self.H, overlay)

        # ── Pulsing cyan glow ──────────────────────────────────────────────
        pulse = 0.6 + 0.4 * math.sin(self._frame * 0.15)
        glow = QRadialGradient(self.W / 2, self.H / 2 - 20, 220)
        glow.setColorAt(0.0, QColor(0, 245, 255, int(30 * pulse)))
        glow.setColorAt(0.5, QColor(0, 100, 140, int(15 * pulse)))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(0, 0, self.W, self.H, glow)

        # ── Border ────────────────────────────────────────────────────────
        border_alpha = int(180 + 60 * pulse)
        pen = QPen(QColor(0, 245, 255, border_alpha), 2)
        p.setPen(pen)
        p.drawRoundedRect(2, 2, self.W - 4, self.H - 4, 16, 16)

        # ── Inner accent line ─────────────────────────────────────────────
        inner_pen = QPen(QColor(0, 245, 255, 30), 1)
        p.setPen(inner_pen)
        p.drawRoundedRect(8, 8, self.W - 16, self.H - 16, 12, 12)

        # ── Rabbit emoji ───────────────────────────────────────────────────
        rabbit_y = 50 + 4 * math.sin(self._frame * 0.12)
        p.setFont(QFont("Noto Emoji", 52))
        p.setPen(QColor("#ffffff"))
        p.drawText(QRectF(0, rabbit_y, self.W, 80), Qt.AlignmentFlag.AlignCenter, "🐇")

        # ── Title with glow ────────────────────────────────────────────────
        title_alpha = int(200 + 55 * pulse)
        p.setFont(QFont("Ubuntu", 34, QFont.Weight.Black))
        # Glow pass
        for offset in [(2, 2), (-2, -2), (2, -2), (-2, 2)]:
            p.setPen(QColor(0, 245, 255, 40))
            p.drawText(
                QRectF(offset[0], 145 + offset[1], self.W, 50),
                Qt.AlignmentFlag.AlignCenter, "Inspector Rabbit"
            )
        p.setPen(QColor(0, 245, 255, title_alpha))
        p.drawText(QRectF(0, 145, self.W, 50), Qt.AlignmentFlag.AlignCenter, "Inspector Rabbit")

        # ── Subtitle ───────────────────────────────────────────────────────
        p.setFont(QFont("Ubuntu", 12))
        p.setPen(QColor(139, 148, 158, 220))
        p.drawText(QRectF(0, 198, self.W, 28), Qt.AlignmentFlag.AlignCenter,
                   "Advanced OSINT Intelligence Suite")

        # ── Feature tags ──────────────────────────────────────────────────
        p.setFont(QFont("Ubuntu", 9))
        p.setPen(QColor(0x30, 0x36, 0x3d, 200))
        tags = "Username · Domain · Email · IP Intel · Phone · Cert CT · Metadata · Pastes · Dorks · Graph"
        p.drawText(QRectF(0, 232, self.W, 20), Qt.AlignmentFlag.AlignCenter, tags)

        # ── Loading bar ────────────────────────────────────────────────────
        bar_w = 320
        bar_h = 4
        bar_x = (self.W - bar_w) // 2
        bar_y = self.H - 60

        # Background
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0x21, 0x26, 0x2d))
        p.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 2, 2)

        # Fill (cycles)
        fill_frac = (self._frame % 60) / 60.0
        fill_w = int(bar_w * fill_frac)
        grad = QLinearGradient(bar_x, 0, bar_x + bar_w, 0)
        grad.setColorAt(0.0, QColor("#00f5ff"))
        grad.setColorAt(1.0, QColor("#7c3aed"))
        p.setBrush(grad)
        p.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 2, 2)

        # ── Loading text ──────────────────────────────────────────────────
        load_msgs = [
            "Initializing OSINT modules...",
            "Loading Certificate Transparency...",
            "Warming up Dorks engine...",
            "Preparing Graph visualization...",
            "Connecting intelligence feeds...",
        ]
        msg_idx = min(self._frame // 12, len(load_msgs) - 1)
        p.setFont(QFont("Ubuntu Mono", 9))
        p.setPen(QColor(0x48, 0x4f, 0x58))
        p.drawText(QRectF(0, bar_y + 12, self.W, 20), Qt.AlignmentFlag.AlignCenter,
                   load_msgs[msg_idx])

        # ── Version ────────────────────────────────────────────────────────
        p.setFont(QFont("Ubuntu", 8))
        p.setPen(QColor(0x21, 0x26, 0x2d))
        p.drawText(QRectF(0, self.H - 20, self.W, 16), Qt.AlignmentFlag.AlignCenter,
                   "v1.0.0  ·  Educational Use Only  ·  github.com/paulmmoore3416/inspector-rabbit")

        p.end()

    def stop(self):
        self._timer.stop()

    # Delegate QSplashScreen methods
    def setWindowFlags(self, flags):
        self._splash.setWindowFlags(flags)

    def show(self):
        self._splash.show()

    def finish(self, w):
        self._splash.finish(w)

    def setPixmap(self, pix):
        self._splash.setPixmap(pix)


if __name__ == "__main__":
    main()
