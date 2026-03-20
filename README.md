# Erindale College Speech Assist (Exam)

An offline, Linux-based assistive exam system designed to support students with accessibility needs.

## Features

- Text-to-speech for reading exam questions aloud
- Speech-to-text for dictating responses
- Fully offline processing
- Question-by-question workflow
- Automatic saving of responses
- Automatic network disable on startup
- Linux desktop launcher and `.deb` packaging support

## Intended use

This tool is designed for supported exam and assessment environments where staff prepare questions in advance and students respond verbally.

## Repository contents

```text
erindale-speech-assist/
├── README.md
├── USER_GUIDE.md
├── LICENSE
├── .gitignore
├── speech_assist.py
├── install.sh
├── build-deb.sh
├── speech-assist-icon.png
└── assets/

## Requirements

- Linux Mint / Ubuntu / Debian-based Linux
- Python 3
- `python3-tk`
- `sox`
- `alsa-utils`
- `network-manager`

## Runtime assets

The application expects these runtime files after installation:

- `whisper/whisper-cli`
- `whisper/ggml-base.en.bin`
- `piper/piper`
- `piper/en_US-lessac-medium.onnx`

These are downloaded or provisioned during installation and are not intended to be stored in this GitHub repository.

## Installation

### Option 1: install from source folder

```
git clone https://github.com/YOUR_USERNAME/erindale-speech-assist.git
cd erindale-speech-assist
bash install.sh
```

### Option 2: build and install a `.deb`

```
cd erindale-speech-assist
./build-deb.sh
sudo apt install ~/deb-build/erindale-speech-assist_1.0_amd64.deb
```

## Launch

```
erindale-speech-assist
```

Or use the desktop shortcut:

```
Erindale College Speech Assist
```

## Saved output

Answers are saved to:

```
~/Desktop/Exam Answers/
```

Each session folder is named like:

```
Student_Subject_YYYY-MM-DD_01
```

Files inside include:

- `Q01.txt`
- `Q02.txt`
- ...
- `ALL.txt`

## Notes

- The application attempts to detect a suitable microphone automatically.
- A manual input device can be forced with:

```
export SPEECH_ASSIST_MIC=plughw:1,0
erindale-speech-assist
```

- The application attempts to disable Wi-Fi/networking at startup using `nmcli`.

## Maintainer

Jasper Lin
 lin.yuxuan@icloud.com
