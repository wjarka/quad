# Introduction
This project is my proof of concept for an automated video game recorder. This project has been recording my Quake Champions matches for the past 2 years or so. 

## Features

Quad is a powerful game streaming and recording suite that integrates NDI streams multiple recorders and Twitch. It also integrates with Discord. Here's what it can do:

### NDI Integration
- Capture and process NDI video streams

### Game Recording
- Intelligent frame processing to detect game states
- Automatic recording based on game states
- Screenshot capture of final game scores
- Flexible recording paths and file management

### Discord Integration
- Automatic posting of game results to Discord channels via webhooks
- YouTube upload capabilities for game recordings
- OCR corrections for player names

### Stream Management
- Stream directly to Twitch with configurable delay and bitrate settings

### Advanced Features
- Support for multiple recorders
    - Open Broadcaster Software (OBS) 
    - Hardware-accelerated recording support (VAAPI)
    - x264 encoding




# Setup Guide

## Recommended Setup
Due to Quake Champions Anti Cheat not tolerating python processes, it's recommended to run Quad on a separate machine. I might test running it on the same machine in a Docker container, but this hasn't been tested yet.

Also, due to the black screen decoder issue, it's not recommended to run Quad on a Ubuntu machine. While it is possible to get it to work, it requires installing outdated packages from .deb files that may cause issues. I have done that in the past and it worked fine, but it would be better to avoid it (contact me if that's your only option). Satisfying those requirements on Arch Linux is easy and just requires one additional package.

The setup guide will assume the usage of Arch Linux or a Docker container (based on Arch Linux).

Note: While Quad supports multiple recorders, OBS will be the only one covered in this guide. 

## Prerequisites

Arch Linux with the following packages installed:
- git
- python
- python-venv
- python-pip
- ffmpeg4.4
- tesseract
- avahi

Or any linux distro with docker installed (if you want to run in a docker container)

## Gaming PC minimal setup
- Windows 10/11
- Download and install NDI Tools from https://ndi.video/tools/
- Start Screen Capture or ScreenCapture HX
- Set frame rate to 60 fps or 60 Hz (depending on HX or non-HX)
- Set resolution to 1920x1080 (if you have a 1440p monitor, NDI will scale it down for you)
- Start NDI Monitor to test a video stream and look up your NDI Stream Name (you will need it later to configure the app)

## Installation

### Arch Linux
```bash
git clone https://github.com/wjarka/quad.git
cd quad
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Docker Container
```bash
git clone https://github.com/wjarka/quad.git
cd quad
docker build -t quad .
```

## Configuration


### App
Create a config.py file in the instance directory. If instance directory doesn't exist, create it.

Example configuration file (not all options included):

```python
# GENERAL SETTINGS
LOG_LEVEL = "INFO"

# FILE PATHS
PATH_STORAGE = "PATH TO STORE GAMES"
PATH_RECORDING = "{storage}/{year}/{month}/{game_id}.mp4"
PATH_SCREENSHOT = "{storage}/{year}/{month}/{game_id}.png"
TOOLS_SCREENSHOT_PATH = "/app/instance/screenshots"

# NDI SETTINGS
NDI_STREAM = "PUT YOUR NDI SOURCE NAME HERE"

# RECORDER SETTINGS
RECORDERS = ["obs"] # List of available recorders

# OBS SETTINGS
OBS_WEBSOCKET_IP = "PUT OBS WEBSOCKET IP HERE"
OBS_WEBSOCKET_PORT = "4455"
OBS_WEBSOCKET_PASSWORD = "PUT OBS WEBSOCKET PASSWORD HERE"
OBS_SKIP_RECORDING_WHEN_STREAMING = True
OBS_SKIP_SWITCHING_SCENES_WHEN_STREAMING = True
OBS_RECORDING_SCENE = "PUT OBS SCENE NAME HERE"
OBS_RECORDING_BASE_DIR = "PUT OBS RECORDING DIRECTORY HERE"

# OTHER RECORDERS
RECORDER_BITRATE = "PUT BITRATE HERE (e.g. 6M)"

# DISCORD SETTINGS (OPTIONAL)
DISCORD_BOT_SECRET = "PUT YOUR DISCORD BOT TOKEN HERE"
DISCORD_WEBHOOK_GAMES = "GAMES CHANNEL WEBHOOK URL HERE"
DISCORD_GAMES_CHANNEL_ID = "GAMES CHANNEL ID HERE"
DISCORD_YOUTUBE_UPLOAD_ALLOWED_USERS = [] # List of user IDs
DISCORD_ACTION_EMOJI_IDS = [] # List of emoji IDs (e.g. for youtube upload)
```

#### Quad OBS settings
While some of the OBS settings may seem obvious, there are a few that may need to be explained:
- OBS_RECORDING_BASE_DIR: The base directory where OBS puts the recordings. Those will be moved to the PATH_RECORDING directory after the recording is done.
- OBS_RECORDING_SCENE: OBS will switch to this scene when it starts recording.
- OBS_SKIP_RECORDING_WHEN_STREAMING: If set to True, the recording will be skipped if OBS is streaming.
- OBS_SKIP_SWITCHING_SCENES_WHEN_STREAMING: If set to True, the OBS will not switch scenes when recording.

OBS can run on both gaming machine or where Quad is running. Either way, make sure it has Websockets plugin enabled and configured. Make sure the app config has the right IP, port, and password set.


## Running the app

### Arch Linux
```bash
source .venv/bin/activate
flask --app quad core run
```

### Docker Container
```bash
docker run \
    --network=host \
    --mount type=bind,src="$(pwd)/quad",target=/app/quad \
    --mount type=bind,src="$(pwd)/instance",target=/app/instance \
    quad
```