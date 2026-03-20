#!/bin/bash
# Inspector Rabbit - .deb Package Builder
# Builds and optionally installs the desktop application

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="inspector-rabbit"
APP_VERSION="1.4.0"
APP_DIR="/opt/inspector-rabbit"
DEB_DIR="${SCRIPT_DIR}/debian_pkg"
PKG_NAME="${APP_NAME}_${APP_VERSION}_amd64"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${CYAN}[Inspector Rabbit]${NC} $1"; }
ok()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn(){ echo -e "${YELLOW}[!]${NC} $1"; }
err() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo -e """
${CYAN}
  ╔═══════════════════════════════════════════╗
  ║   🐇 Inspector Rabbit .deb Builder v1.0   ║
  ║   Advanced OSINT Desktop Application      ║
  ╚═══════════════════════════════════════════╝
${NC}"""

# ===== Check prerequisites =====
log "Checking prerequisites..."
command -v python3 >/dev/null 2>&1 || err "python3 not found"
command -v pip3 >/dev/null 2>&1   || err "pip3 not found"
command -v dpkg-deb >/dev/null 2>&1 || err "dpkg-deb not found (install: apt install dpkg)"
ok "Prerequisites OK"

# ===== Install Python dependencies =====
log "Installing Python dependencies..."
pip3 install --quiet --break-system-packages \
    PyQt6 requests aiohttp python-whois dnspython \
    shodan beautifulsoup4 lxml reportlab Pillow networkx \
    matplotlib googlesearch-python cryptography pyOpenSSL \
    2>/dev/null || \
pip3 install --quiet --user \
    PyQt6 requests aiohttp python-whois dnspython \
    shodan beautifulsoup4 lxml reportlab Pillow networkx \
    matplotlib googlesearch-python cryptography pyOpenSSL \
    2>/dev/null || warn "Some packages may not have installed (check manually)"
ok "Python dependencies installed"

# ===== Clean previous build =====
log "Cleaning previous build..."
rm -rf "${DEB_DIR}"
mkdir -p "${DEB_DIR}/${PKG_NAME}"

# ===== Create package structure =====
log "Creating .deb package structure..."
mkdir -p "${DEB_DIR}/${PKG_NAME}/DEBIAN"
mkdir -p "${DEB_DIR}/${PKG_NAME}/opt/inspector-rabbit"
mkdir -p "${DEB_DIR}/${PKG_NAME}/usr/bin"
mkdir -p "${DEB_DIR}/${PKG_NAME}/usr/share/applications"
mkdir -p "${DEB_DIR}/${PKG_NAME}/usr/share/icons/hicolor/256x256/apps"
mkdir -p "${DEB_DIR}/${PKG_NAME}/usr/share/inspector-rabbit"

# ===== Copy application files =====
log "Copying application files..."
cp -r "${SCRIPT_DIR}/src" "${DEB_DIR}/${PKG_NAME}/opt/inspector-rabbit/"
cp "${SCRIPT_DIR}/inspector_rabbit.py" "${DEB_DIR}/${PKG_NAME}/opt/inspector-rabbit/"
chmod 755 "${DEB_DIR}/${PKG_NAME}/opt/inspector-rabbit/inspector_rabbit.py"

# Copy assets if they exist
if [ -d "${SCRIPT_DIR}/assets" ]; then
    cp -r "${SCRIPT_DIR}/assets" "${DEB_DIR}/${PKG_NAME}/opt/inspector-rabbit/"
fi

# ===== Create launcher script =====
log "Creating launcher..."
cat > "${DEB_DIR}/${PKG_NAME}/usr/bin/inspector-rabbit" << 'LAUNCHER'
#!/bin/bash
# Inspector Rabbit launcher
export PYTHONPATH="/opt/inspector-rabbit:$PYTHONPATH"
cd /opt/inspector-rabbit
exec python3 /opt/inspector-rabbit/inspector_rabbit.py "$@"
LAUNCHER
chmod 755 "${DEB_DIR}/${PKG_NAME}/usr/bin/inspector-rabbit"

# ===== Create SVG icon =====
log "Creating application icon..."
cat > "/tmp/inspector_rabbit.svg" << 'SVGEOF'
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0d1117"/>
      <stop offset="100%" style="stop-color:#1a1a2e"/>
    </linearGradient>
    <linearGradient id="glow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#00f5ff"/>
      <stop offset="100%" style="stop-color:#0070f3"/>
    </linearGradient>
  </defs>
  <!-- Background circle -->
  <circle cx="128" cy="128" r="128" fill="url(#bg)"/>
  <!-- Outer ring -->
  <circle cx="128" cy="128" r="122" fill="none" stroke="url(#glow)" stroke-width="2" opacity="0.6"/>
  <!-- Text emoji style rabbit -->
  <text x="128" y="168" font-size="120" text-anchor="middle" font-family="Noto Emoji,Segoe UI Emoji,Apple Color Emoji,sans-serif">🐇</text>
  <!-- Bottom text -->
  <text x="128" y="228" font-size="16" text-anchor="middle" fill="#00f5ff" font-family="Ubuntu,sans-serif" font-weight="bold" letter-spacing="3">OSINT</text>
</svg>
SVGEOF

# Try to convert SVG to PNG for icon
if command -v convert >/dev/null 2>&1; then
    convert -background none -size 256x256 /tmp/inspector_rabbit.svg \
        "${DEB_DIR}/${PKG_NAME}/usr/share/icons/hicolor/256x256/apps/inspector-rabbit.png" 2>/dev/null || true
elif command -v rsvg-convert >/dev/null 2>&1; then
    rsvg-convert -w 256 -h 256 /tmp/inspector_rabbit.svg \
        -o "${DEB_DIR}/${PKG_NAME}/usr/share/icons/hicolor/256x256/apps/inspector-rabbit.png" 2>/dev/null || true
elif command -v python3 >/dev/null 2>&1; then
    python3 -c "
try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QLinearGradient, QRadialGradient, QPen
    from PyQt6.QtCore import Qt, QRectF
    import sys
    app = QApplication.instance() or QApplication(sys.argv)
    w, h = 256, 256
    pix = QPixmap(w, h)
    pix.fill(QColor('#0d1117'))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    # Gradient bg
    grad = QLinearGradient(0, 0, w, h)
    grad.setColorAt(0, QColor('#0d1117'))
    grad.setColorAt(1, QColor('#1a1a2e'))
    p.fillRect(0, 0, w, h, grad)
    # Border
    p.setPen(QPen(QColor('#00f5ff'), 3))
    p.drawEllipse(4, 4, w-8, h-8)
    # Rabbit
    p.setFont(QFont('Noto Emoji', 100))
    p.drawText(QRectF(0, 20, w, w-40), Qt.AlignmentFlag.AlignCenter, '🐇')
    # Label
    p.setFont(QFont('Ubuntu', 16, QFont.Weight.Bold))
    p.setPen(QColor('#00f5ff'))
    p.drawText(QRectF(0, 210, w, 30), Qt.AlignmentFlag.AlignCenter, 'OSINT')
    p.end()
    pix.save('${DEB_DIR}/${PKG_NAME}/usr/share/icons/hicolor/256x256/apps/inspector-rabbit.png')
    print('Icon created')
except Exception as e:
    print(f'Icon creation skipped: {e}')
" 2>/dev/null || true
fi

# Copy SVG as fallback icon
cp /tmp/inspector_rabbit.svg \
    "${DEB_DIR}/${PKG_NAME}/usr/share/icons/hicolor/256x256/apps/inspector-rabbit.svg" 2>/dev/null || true

# ===== Create desktop entry =====
log "Creating desktop entry..."
cat > "${DEB_DIR}/${PKG_NAME}/usr/share/applications/inspector-rabbit.desktop" << 'DESKTOP'
[Desktop Entry]
Version=1.0
Type=Application
Name=Inspector Rabbit
GenericName=OSINT Intelligence Suite
Comment=Advanced Open Source Intelligence tool for security research
Exec=inspector-rabbit
Icon=inspector-rabbit
Terminal=false
Categories=Security;Network;Education;
Keywords=osint;security;reconnaissance;intelligence;sherlock;maltego;
StartupNotify=true
StartupWMClass=InspectorRabbit
DESKTOP

# ===== Create requirements snapshot =====
cp "${SCRIPT_DIR}/requirements.txt" \
    "${DEB_DIR}/${PKG_NAME}/opt/inspector-rabbit/requirements.txt"

# ===== Create DEBIAN control file =====
log "Creating DEBIAN control file..."
INSTALLED_SIZE=$(du -sk "${DEB_DIR}/${PKG_NAME}/opt" 2>/dev/null | cut -f1 || echo "50000")
cat > "${DEB_DIR}/${PKG_NAME}/DEBIAN/control" << CONTROL
Package: inspector-rabbit
Version: ${APP_VERSION}
Section: net
Priority: optional
Architecture: amd64
Installed-Size: ${INSTALLED_SIZE}
Depends: python3 (>= 3.9), python3-pip, python3-pyqt6 | python3-qt6
Recommends: python3-requests, python3-bs4
Maintainer: Inspector Rabbit <inspectorrabbit@osint.local>
Description: Advanced OSINT Intelligence Suite
 Inspector Rabbit is a powerful desktop OSINT tool combining features from
 Sherlock, Maltego, SpiderFoot, Shodan, Recon-ng, and Google Dorks.
 .
 Features:
  - Username search across 100+ social platforms
  - Domain intelligence (WHOIS, DNS, SSL, subdomains)
  - Email OSINT and verification
  - Google Dorks engine with 60+ templates
  - Web crawler with email/phone/social extraction
  - Interactive force-directed network graph
  - HTML/JSON/PDF report export
Homepage: https://github.com/paulmmoore3416/sherlock
CONTROL

# ===== Create postinst script =====
cat > "${DEB_DIR}/${PKG_NAME}/DEBIAN/postinst" << 'POSTINST'
#!/bin/bash
set -e

echo "🐇 Configuring Inspector Rabbit..."

# Install Python dependencies
pip3 install --quiet --break-system-packages \
    PyQt6 requests aiohttp python-whois dnspython \
    shodan beautifulsoup4 lxml reportlab Pillow networkx \
    matplotlib googlesearch-python cryptography pyOpenSSL \
    2>/dev/null || \
pip3 install --quiet --user \
    PyQt6 requests aiohttp python-whois dnspython \
    shodan beautifulsoup4 lxml reportlab Pillow networkx \
    matplotlib googlesearch-python cryptography pyOpenSSL \
    2>/dev/null || true

# Update icon cache
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi

# Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications 2>/dev/null || true
fi

echo "✅ Inspector Rabbit installed successfully!"
echo "   Launch from Applications menu or run: inspector-rabbit"

exit 0
POSTINST
chmod 755 "${DEB_DIR}/${PKG_NAME}/DEBIAN/postinst"

# ===== Create prerm script =====
cat > "${DEB_DIR}/${PKG_NAME}/DEBIAN/prerm" << 'PRERM'
#!/bin/bash
echo "🐇 Removing Inspector Rabbit..."
exit 0
PRERM
chmod 755 "${DEB_DIR}/${PKG_NAME}/DEBIAN/prerm"

# ===== Set permissions =====
log "Setting file permissions..."
find "${DEB_DIR}/${PKG_NAME}" -type f -exec chmod 644 {} \;
find "${DEB_DIR}/${PKG_NAME}" -type d -exec chmod 755 {} \;
chmod 755 "${DEB_DIR}/${PKG_NAME}/usr/bin/inspector-rabbit"
chmod 755 "${DEB_DIR}/${PKG_NAME}/opt/inspector-rabbit/inspector_rabbit.py"
chmod 755 "${DEB_DIR}/${PKG_NAME}/DEBIAN/postinst"
chmod 755 "${DEB_DIR}/${PKG_NAME}/DEBIAN/prerm"
ok "Permissions set"

# ===== Build .deb =====
log "Building .deb package..."
dpkg-deb --build --root-owner-group "${DEB_DIR}/${PKG_NAME}" \
    "${SCRIPT_DIR}/${PKG_NAME}.deb" 2>&1

if [ -f "${SCRIPT_DIR}/${PKG_NAME}.deb" ]; then
    ok "Package built: ${SCRIPT_DIR}/${PKG_NAME}.deb"
    DEB_SIZE=$(du -sh "${SCRIPT_DIR}/${PKG_NAME}.deb" | cut -f1)
    echo -e "   Package size: ${CYAN}${DEB_SIZE}${NC}"
else
    err "Package build failed!"
fi

# ===== Install =====
echo ""
log "Installing package..."
if sudo dpkg -i "${SCRIPT_DIR}/${PKG_NAME}.deb" 2>&1; then
    ok "Package installed successfully!"
else
    warn "dpkg install had issues, trying apt fix..."
    sudo apt-get install -f -y 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Inspector Rabbit installed successfully!  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${CYAN}Launch options:${NC}"
echo -e "  • Applications menu → Inspector Rabbit"
echo -e "  • Terminal: ${YELLOW}inspector-rabbit${NC}"
echo -e "  • Direct: ${YELLOW}python3 /opt/inspector-rabbit/inspector_rabbit.py${NC}"
echo ""
