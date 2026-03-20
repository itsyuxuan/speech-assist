
```bash
#!/usr/bin/env bash
set -euo pipefail

APP_NAME="erindale-speech-assist"
INSTALL_DIR="/opt/${APP_NAME}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_USER="${SUDO_USER:-$USER}"
TARGET_HOME="$(eval echo "~${TARGET_USER}")"

echo "Installing Erindale Speech Assist..."
echo "Target user: ${TARGET_USER}"
echo "Install dir: ${INSTALL_DIR}"

# ===== Check required source files =====
required_files=(
  "${SCRIPT_DIR}/speech_assist.py"
  "${SCRIPT_DIR}/speech-assist-icon.png"
)

for f in "${required_files[@]}"; do
  if [ ! -e "$f" ]; then
    echo "Missing required file: $f"
    exit 1
  fi
done

# ===== Install system packages =====
sudo apt update
sudo apt install -y \
  python3 \
  python3-tk \
  sox \
  alsa-utils \
  network-manager \
  policykit-1 \
  curl \
  tar

# ===== Copy app files =====
sudo rm -rf "${INSTALL_DIR}"
sudo mkdir -p "${INSTALL_DIR}"

sudo cp "${SCRIPT_DIR}/speech_assist.py" "${INSTALL_DIR}/"
sudo cp "${SCRIPT_DIR}/speech-assist-icon.png" "${INSTALL_DIR}/"

# ===== Set up Whisper =====
sudo mkdir -p "${INSTALL_DIR}/whisper"

echo "Downloading whisper.cpp runtime..."
TMP_WHISPER_DIR="$(mktemp -d)"
curl -L -o "${TMP_WHISPER_DIR}/whisper.tar.gz" \
  https://github.com/ggml-org/whisper.cpp/releases/latest/download/whisper.cpp-linux-x86_64.tar.gz

tar -xzf "${TMP_WHISPER_DIR}/whisper.tar.gz" -C "${TMP_WHISPER_DIR}"

WHISPER_CLI_PATH="$(find "${TMP_WHISPER_DIR}" -type f -name whisper-cli | head -n 1)"
if [ -z "${WHISPER_CLI_PATH}" ]; then
  echo "Failed to find whisper-cli in downloaded archive."
  exit 1
fi
sudo cp "${WHISPER_CLI_PATH}" "${INSTALL_DIR}/whisper/whisper-cli"

echo "Downloading Whisper base English model..."
sudo curl -L -o "${INSTALL_DIR}/whisper/ggml-base.en.bin" \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin

# ===== Set up Piper =====
sudo mkdir -p "${INSTALL_DIR}/piper"

echo "Downloading Piper runtime..."
TMP_PIPER_DIR="$(mktemp -d)"
curl -L -o "${TMP_PIPER_DIR}/piper.tar.gz" \
  https://github.com/rhasspy/piper/releases/latest/download/piper_linux_x86_64.tar.gz

tar -xzf "${TMP_PIPER_DIR}/piper.tar.gz" -C "${TMP_PIPER_DIR}"

PIPER_RUNTIME_DIR="$(find "${TMP_PIPER_DIR}" -type d -name piper | head -n 1)"
if [ -z "${PIPER_RUNTIME_DIR}" ]; then
  echo "Failed to find Piper runtime in downloaded archive."
  exit 1
fi

sudo cp -r "${PIPER_RUNTIME_DIR}/"* "${INSTALL_DIR}/piper/"

echo "Downloading Piper voice model..."
sudo curl -L -o "${INSTALL_DIR}/piper/en_US-lessac-medium.onnx" \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx

sudo curl -L -o "${INSTALL_DIR}/piper/en_US-lessac-medium.onnx.json" \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

# ===== Permissions =====
sudo chmod +x "${INSTALL_DIR}/speech_assist.py"
sudo chmod +x "${INSTALL_DIR}/whisper/whisper-cli"
if [ -f "${INSTALL_DIR}/piper/piper" ]; then
  sudo chmod +x "${INSTALL_DIR}/piper/piper"
fi

# ===== Create launcher wrapper =====
sudo tee /usr/local/bin/erindale-speech-assist >/dev/null <<EOF
#!/usr/bin/env bash
python3 "${INSTALL_DIR}/speech_assist.py"
EOF
sudo chmod +x /usr/local/bin/erindale-speech-assist

# ===== Desktop launcher =====
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

echo "${DESKTOP_FILE_CONTENT}" | sudo tee /usr/share/applications/erindale-speech-assist.desktop >/dev/null

mkdir -p "${TARGET_HOME}/Desktop"
echo "${DESKTOP_FILE_CONTENT}" > "${TARGET_HOME}/Desktop/Erindale College Speech Assist.desktop"
chmod +x "${TARGET_HOME}/Desktop/Erindale College Speech Assist.desktop"

mkdir -p "${TARGET_HOME}/.local/share/applications"
echo "${DESKTOP_FILE_CONTENT}" > "${TARGET_HOME}/.local/share/applications/erindale-speech-assist.desktop"

sudo chown "${TARGET_USER}:${TARGET_USER}" "${TARGET_HOME}/Desktop/Erindale College Speech Assist.desktop"
sudo chown "${TARGET_USER}:${TARGET_USER}" "${TARGET_HOME}/.local/share/applications/erindale-speech-assist.desktop"

# ===== Sudoers rule for passwordless network-off commands =====
sudo tee /etc/sudoers.d/erindale-speech-assist >/dev/null <<EOF
${TARGET_USER} ALL=(root) NOPASSWD: /usr/bin/nmcli radio wifi off
${TARGET_USER} ALL=(root) NOPASSWD: /usr/bin/nmcli networking off
EOF
sudo chmod 440 /etc/sudoers.d/erindale-speech-assist

echo
echo "Install completed."
echo "App installed at: ${INSTALL_DIR}"
echo "Desktop shortcut created for: ${TARGET_USER}"
echo
echo "Run with:"
echo "  erindale-speech-assist"
