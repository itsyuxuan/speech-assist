#!/usr/bin/env bash
set -euo pipefail

APP_NAME="erindale-speech-assist"
INSTALL_DIR="/opt/${APP_NAME}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_USER="${SUDO_USER:-$USER}"
TARGET_HOME="$(eval echo "~${TARGET_USER}")"

echo "=========================================="
echo "Installing Erindale College Speech Assist"
echo "Target user : ${TARGET_USER}"
echo "Install dir : ${INSTALL_DIR}"
echo "Source dir  : ${SCRIPT_DIR}"
echo "=========================================="

# ===== Check required files =====
required_files=(
  "${SCRIPT_DIR}/speech_assist.py"
  "${SCRIPT_DIR}/speech-assist-icon.png"
  "${SCRIPT_DIR}/whisper/whisper-cli"
  "${SCRIPT_DIR}/whisper/ggml-base.en.bin"
  "${SCRIPT_DIR}/piper/piper"
  "${SCRIPT_DIR}/piper/en_US-lessac-medium.onnx"
)

for f in "${required_files[@]}"; do
  if [ ! -e "$f" ]; then
    echo "ERROR: Missing required file:"
    echo "  $f"
    exit 1
  fi
done

# ===== Install system packages =====
echo
echo "Installing system packages..."
sudo apt update
sudo apt install -y \
  python3 \
  python3-tk \
  sox \
  alsa-utils \
  network-manager \
  policykit-1

# ===== Copy app bundle =====
echo
echo "Copying application files..."
sudo rm -rf "${INSTALL_DIR}"
sudo mkdir -p "${INSTALL_DIR}"
sudo mkdir -p "${INSTALL_DIR}/whisper"
sudo mkdir -p "${INSTALL_DIR}/piper"

sudo cp -L "${SCRIPT_DIR}/speech_assist.py" "${INSTALL_DIR}/"
sudo cp -L "${SCRIPT_DIR}/speech-assist-icon.png" "${INSTALL_DIR}/"

sudo cp -L "${SCRIPT_DIR}/whisper/whisper-cli" "${INSTALL_DIR}/whisper/"
sudo cp -L "${SCRIPT_DIR}/whisper/ggml-base.en.bin" "${INSTALL_DIR}/whisper/"

sudo chmod +x "${INSTALL_DIR}/whisper/whisper-cli"

sudo mkdir -p "${INSTALL_DIR}/piper"
sudo cp -r "${SCRIPT_DIR}/piper/"* "${INSTALL_DIR}/piper/"

if [ -f "${INSTALL_DIR}/piper/piper" ]; then
  sudo chmod +x "${INSTALL_DIR}/piper/piper"
fi

# ===== Create launcher wrapper =====
echo
echo "Creating launcher command..."
sudo tee /usr/local/bin/erindale-speech-assist >/dev/null <<EOF
#!/usr/bin/env bash
python3 "${INSTALL_DIR}/speech_assist.py"
EOF

sudo chmod +x /usr/local/bin/erindale-speech-assist

# ===== Desktop launcher =====
echo
echo "Creating desktop launcher..."
DESKTOP_FILE_CONTENT="[Desktop Entry]
Version=1.0
Type=Application
Name=Erindale College Speech Assist
Comment=Offline speech assist exam tool
Exec=/usr/local/bin/erindale-speech-assist
Icon=${INSTALL_DIR}/speech-assist-icon.png
Terminal=false
Categories=Education;Utility;
StartupNotify=true
"

# system applications menu
echo "${DESKTOP_FILE_CONTENT}" | sudo tee /usr/share/applications/erindale-speech-assist.desktop >/dev/null

# user's Desktop shortcut
mkdir -p "${TARGET_HOME}/Desktop"
echo "${DESKTOP_FILE_CONTENT}" > "${TARGET_HOME}/Desktop/Erindale College Speech Assist.desktop"
chmod +x "${TARGET_HOME}/Desktop/Erindale College Speech Assist.desktop"

# user's local applications
mkdir -p "${TARGET_HOME}/.local/share/applications"
echo "${DESKTOP_FILE_CONTENT}" > "${TARGET_HOME}/.local/share/applications/erindale-speech-assist.desktop"

# fix ownership for user-visible files
sudo chown "${TARGET_USER}:${TARGET_USER}" "${TARGET_HOME}/Desktop/Erindale College Speech Assist.desktop"
sudo chown "${TARGET_USER}:${TARGET_USER}" "${TARGET_HOME}/.local/share/applications/erindale-speech-assist.desktop"

# ===== Sudoers rule for passwordless network-off commands =====
echo
echo "Configuring sudoers for passwordless network-off commands..."
sudo tee /etc/sudoers.d/erindale-speech-assist >/dev/null <<EOF
${TARGET_USER} ALL=(root) NOPASSWD: /usr/bin/nmcli radio wifi off
${TARGET_USER} ALL=(root) NOPASSWD: /usr/bin/nmcli networking off
EOF

sudo chmod 440 /etc/sudoers.d/erindale-speech-assist

# ===== Final checks =====
echo
echo "Running final checks..."
if [ ! -x /usr/local/bin/erindale-speech-assist ]; then
  echo "ERROR: launcher command was not created correctly."
  exit 1
fi

if [ ! -f /usr/share/applications/erindale-speech-assist.desktop ]; then
  echo "ERROR: desktop file was not created correctly."
  exit 1
fi

echo
echo "=========================================="
echo "Install completed successfully."
echo "=========================================="
echo "Installed to:"
echo "  ${INSTALL_DIR}"
echo
echo "Run from terminal:"
echo "  erindale-speech-assist"
echo
echo "Desktop shortcut:"
echo "  ${TARGET_HOME}/Desktop/Erindale College Speech Assist.desktop"
echo
echo "Passwordless commands enabled for user:"
echo "  sudo nmcli radio wifi off"
echo "  sudo nmcli networking off"
echo
echo "Recommended next steps:"
echo "  1. Double-click the desktop shortcut"
echo "  2. Open Setup and load sample questions"
echo "  3. Test reading, recording, saving"
echo "  4. Check microphone/headset on this machine"
echo
