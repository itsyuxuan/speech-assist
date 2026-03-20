#!/usr/bin/env bash
set -euo pipefail

APP_NAME="erindale-speech-assist"
VERSION="1.0"
ARCH="amd64"

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_ROOT="${HOME}/deb-build"
PKG_DIR="${BUILD_ROOT}/${APP_NAME}_${VERSION}_${ARCH}"
DEB_FILE="${BUILD_ROOT}/${APP_NAME}_${VERSION}_${ARCH}.deb"

echo "=========================================="
echo "Building ${APP_NAME} ${VERSION} (${ARCH})"
echo "Source dir : ${SRC_DIR}"
echo "Build dir  : ${PKG_DIR}"
echo "Output deb : ${DEB_FILE}"
echo "=========================================="

# ===== Check required files =====
required_files=(
  "${SRC_DIR}/speech_assist.py"
  "${SRC_DIR}/speech-assist-icon.png"
  "${SRC_DIR}/whisper/whisper-cli"
  "${SRC_DIR}/whisper/ggml-base.en.bin"
  "${SRC_DIR}/piper/piper"
  "${SRC_DIR}/piper/en_US-lessac-medium.onnx"
)

for f in "${required_files[@]}"; do
  if [ ! -e "$f" ]; then
    echo "ERROR: Missing required file:"
    echo "  $f"
    exit 1
  fi
done

# ===== Clean old build =====
rm -rf "${PKG_DIR}"
mkdir -p "${PKG_DIR}"

# ===== Package structure =====
mkdir -p "${PKG_DIR}/DEBIAN"
mkdir -p "${PKG_DIR}/opt/${APP_NAME}"
mkdir -p "${PKG_DIR}/usr/local/bin"
mkdir -p "${PKG_DIR}/usr/share/applications"

# ===== Copy app bundle =====
cp -r "${SRC_DIR}/"* "${PKG_DIR}/opt/${APP_NAME}/"

# remove things that should not be inside the installed app folder
rm -f "${PKG_DIR}/opt/${APP_NAME}/build-deb.sh"
rm -f "${PKG_DIR}/opt/${APP_NAME}/install.sh"

# ===== Launcher =====
cat > "${PKG_DIR}/usr/local/bin/erindale-speech-assist" << 'EOF'
#!/usr/bin/env bash
python3 /opt/erindale-speech-assist/speech_assist.py
EOF
chmod 755 "${PKG_DIR}/usr/local/bin/erindale-speech-assist"

# ===== Desktop entry =====
cat > "${PKG_DIR}/usr/share/applications/erindale-speech-assist.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Erindale College Speech Assist
Comment=Offline speech assist exam tool
Exec=erindale-speech-assist
Icon=/opt/erindale-speech-assist/speech-assist-icon.png
Terminal=false
Categories=Education;Utility;
StartupNotify=true
EOF
chmod 644 "${PKG_DIR}/usr/share/applications/erindale-speech-assist.desktop"

# ===== Control file =====
cat > "${PKG_DIR}/DEBIAN/control" << EOF
Package: ${APP_NAME}
Version: ${VERSION}
Section: education
Priority: optional
Architecture: ${ARCH}
Depends: python3, python3-tk, sox, alsa-utils, network-manager, policykit-1
Maintainer: Jasper Lin <lin.yuxuan@icloud.com>
Description: Offline speech assist exam tool
 Erindale College Speech Assist allows students to listen to
 questions and dictate answers offline using local Whisper
 speech-to-text and Piper text-to-speech.
EOF

# ===== Post-install script =====
cat > "${PKG_DIR}/DEBIAN/postinst" << 'EOF'
#!/usr/bin/env bash
set -e

TARGET_USER="erindale"

# If the erindale user exists, allow passwordless network-off commands
if id "${TARGET_USER}" >/dev/null 2>&1; then
  cat > /etc/sudoers.d/erindale-speech-assist << SUDOEOF
${TARGET_USER} ALL=(root) NOPASSWD: /usr/bin/nmcli radio wifi off
${TARGET_USER} ALL=(root) NOPASSWD: /usr/bin/nmcli networking off
SUDOEOF
  chmod 440 /etc/sudoers.d/erindale-speech-assist
fi

# Refresh desktop database if available
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database /usr/share/applications || true
fi

exit 0
EOF
chmod 755 "${PKG_DIR}/DEBIAN/postinst"

# ===== Pre-remove script =====
cat > "${PKG_DIR}/DEBIAN/prerm" << 'EOF'
#!/usr/bin/env bash
set -e

rm -f /etc/sudoers.d/erindale-speech-assist || true

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database /usr/share/applications || true
fi

exit 0
EOF
chmod 755 "${PKG_DIR}/DEBIAN/prerm"

# ===== Permissions sanity =====
find "${PKG_DIR}/DEBIAN" -type f -exec chmod 755 {} \;
chmod 644 "${PKG_DIR}/DEBIAN/control"

# app binaries
if [ -f "${PKG_DIR}/opt/${APP_NAME}/whisper/whisper-cli" ]; then
  chmod 755 "${PKG_DIR}/opt/${APP_NAME}/whisper/whisper-cli"
fi

if [ -f "${PKG_DIR}/opt/${APP_NAME}/piper/piper" ]; then
  chmod 755 "${PKG_DIR}/opt/${APP_NAME}/piper/piper"
fi

# ===== Build package =====
mkdir -p "${BUILD_ROOT}"
rm -f "${DEB_FILE}"
dpkg-deb --build "${PKG_DIR}" "${DEB_FILE}"

echo
echo "=========================================="
echo "Build complete"
echo "=========================================="
echo "Created:"
echo "  ${DEB_FILE}"
echo
echo "Install with:"
echo "  sudo apt install ${DEB_FILE}"
echo
