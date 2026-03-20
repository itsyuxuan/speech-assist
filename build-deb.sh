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

required_files=(
  "${SRC_DIR}/speech_assist.py"
  "${SRC_DIR}/speech-assist-icon.png"
)

for f in "${required_files[@]}"; do
  if [ ! -e "$f" ]; then
    echo "ERROR: Missing required file:"
    echo "  $f"
    exit 1
  fi
done

rm -rf "${PKG_DIR}"
mkdir -p "${PKG_DIR}"

mkdir -p "${PKG_DIR}/DEBIAN"
mkdir -p "${PKG_DIR}/opt/${APP_NAME}"
mkdir -p "${PKG_DIR}/usr/local/bin"
mkdir -p "${PKG_DIR}/usr/share/applications"

cp "${SRC_DIR}/speech_assist.py" "${PKG_DIR}/opt/${APP_NAME}/"
cp "${SRC_DIR}/speech-assist-icon.png" "${PKG_DIR}/opt/${APP_NAME}/"

cat > "${PKG_DIR}/usr/local/bin/erindale-speech-assist" << 'EOF'
#!/usr/bin/env bash
python3 /opt/erindale-speech-assist/speech_assist.py
EOF
chmod 755 "${PKG_DIR}/usr/local/bin/erindale-speech-assist"

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

cat > "${PKG_DIR}/DEBIAN/control" << EOF
Package: ${APP_NAME}
Version: ${VERSION}
Section: education
Priority: optional
Architecture: ${ARCH}
Depends: python3, python3-tk, sox, alsa-utils, network-manager, policykit-1, curl, tar
Maintainer: Jasper Lin <lin.yuxuan@icloud.com>
Description: Offline speech assist exam tool
 Erindale College Speech Assist allows students to listen to
 questions and dictate answers offline using local Whisper
 speech-to-text and Piper text-to-speech.
EOF

cat > "${PKG_DIR}/DEBIAN/postinst" << 'EOF'
#!/usr/bin/env bash
set -e

TARGET_USER="erindale"
APP_DIR="/opt/erindale-speech-assist"

apt-get update || true
apt-get install -y python3 python3-tk sox alsa-utils network-manager policykit-1 curl tar || true

mkdir -p "${APP_DIR}/whisper"
mkdir -p "${APP_DIR}/piper"

TMP_WHISPER_DIR="$(mktemp -d)"
curl -L -o "${TMP_WHISPER_DIR}/whisper.tar.gz" \
  https://github.com/ggml-org/whisper.cpp/releases/latest/download/whisper.cpp-linux-x86_64.tar.gz
tar -xzf "${TMP_WHISPER_DIR}/whisper.tar.gz" -C "${TMP_WHISPER_DIR}"
WHISPER_CLI_PATH="$(find "${TMP_WHISPER_DIR}" -type f -name whisper-cli | head -n 1)"
if [ -n "${WHISPER_CLI_PATH}" ]; then
  cp "${WHISPER_CLI_PATH}" "${APP_DIR}/whisper/whisper-cli"
  chmod 755 "${APP_DIR}/whisper/whisper-cli"
fi

curl -L -o "${APP_DIR}/whisper/ggml-base.en.bin" \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin

TMP_PIPER_DIR="$(mktemp -d)"
curl -L -o "${TMP_PIPER_DIR}/piper.tar.gz" \
  https://github.com/rhasspy/piper/releases/latest/download/piper_linux_x86_64.tar.gz
tar -xzf "${TMP_PIPER_DIR}/piper.tar.gz" -C "${TMP_PIPER_DIR}"
PIPER_RUNTIME_DIR="$(find "${TMP_PIPER_DIR}" -type d -name piper | head -n 1)"
if [ -n "${PIPER_RUNTIME_DIR}" ]; then
  cp -r "${PIPER_RUNTIME_DIR}/"* "${APP_DIR}/piper/"
  if [ -f "${APP_DIR}/piper/piper" ]; then
    chmod 755 "${APP_DIR}/piper/piper"
  fi
fi

curl -L -o "${APP_DIR}/piper/en_US-lessac-medium.onnx" \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
curl -L -o "${APP_DIR}/piper/en_US-lessac-medium.onnx.json" \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

if id "${TARGET_USER}" >/dev/null 2>&1; then
  cat > /etc/sudoers.d/erindale-speech-assist << SUDOEOF
${TARGET_USER} ALL=(root) NOPASSWD: /usr/bin/nmcli radio wifi off
${TARGET_USER} ALL=(root) NOPASSWD: /usr/bin/nmcli networking off
SUDOEOF
  chmod 440 /etc/sudoers.d/erindale-speech-assist
fi

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database /usr/share/applications || true
fi

exit 0
EOF
chmod 755 "${PKG_DIR}/DEBIAN/postinst"

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

find "${PKG_DIR}/DEBIAN" -type f -exec chmod 755 {} \;
chmod 644 "${PKG_DIR}/DEBIAN/control"

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
