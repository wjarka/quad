from __future__ import annotations
import click
from flask import Blueprint, current_app
from blinker import signal
import pexpect
import threading

bp = Blueprint('stream', __name__)

@bp.cli.command('stop')
def stop():
	from . import zmq
	r = zmq.Client()
	r.stop_service('stream')

@click.option('-d', '--delay')
@bp.cli.command('start')
def start(delay=None):
	from . import zmq
	r = zmq.Client()
	r.start_service('stream', {'delay': delay})	

class TwitchStream:
	def __init__(self):
		self.capture_process = None
		self.stream_process = None
		self.stream_delay_increments = 4
		self.stream_delay = current_app.config['TWITCH_DELAY'] if 'TWITCH_DELAY' in current_app.config else None
		if ("RECORDER_BITRATE" in current_app.config):
			self.bitrate = current_app.config["RECORDER_BITRATE"]
		else:
			self.bitrate = '6M'
		self.ndi_source_name = current_app.config["NDI_STREAM"]
		self.playlist_path = "/tmp/out.m3u8"
		self.stream_key = current_app.config["TWITCH_STREAM_KEY"]
		if ("TWITCH_STREAM_TEST_MODE" in current_app.config and current_app.config["TWITCH_STREAM_TEST_MODE"]):
			self.stream_params = "?bandwidthtest=true"
		else:
			self.stream_params = ""

	def start_capture(self):
		from .common import prepare_command
		import math
		hls_list_size = math.ceil(self.stream_delay / self.stream_delay_increments)
		capture_command = prepare_command(f"ffmpeg -hwaccel qsv -hwaccel_output_format qsv  -rtbufsize 1024M \
			-thread_queue_size 8192 -f libndi_newtek -i '{self.ndi_source_name}' \
			-thread_queue_size 8192  -i /dev/video0 -c:v h264_qsv -profile:v main -preset medium \
			-b:v {self.bitrate} -bufsize 1M -maxrate {self.bitrate} \
			-filter_complex 'overlay=x=10:y=main_h-overlay_h-10' -hls_time 1 -hls_list_size {hls_list_size} \
			-hls_flags delete_segments {self.playlist_path}")
		self.capture_process = pexpect.spawn(capture_command)

	def start_stream(self, app):
		with (app.app_context()):
			import time
			from .common import prepare_command
			time.sleep(self.stream_delay)
			stream_command = prepare_command(f"ffmpeg -thread_queue_size 8192 -re -live_start_index 0 \
				-i {self.playlist_path} -c copy -f flv \
				rtmp://waw02.contribute.live-video.net/app/{self.stream_key}{self.stream_params}")
			self.stream_process = pexpect.spawn(stream_command)

	def start(self, delay = None):
		if (delay is not None):
			self.stream_delay = delay
		self.start_capture()
		thread = threading.Thread(target=self.start_stream, args=(current_app._get_current_object(),))
		thread.start()

	def stop_stream(self, app):
		with (app.app_context()):
			import time
			if (self.stream_process is not None):
				current_app.logger.info(f"Waiting {str(self.stream_delay)} seconds to stop stream process...")
				time.sleep(self.stream_delay)
				current_app.logger.info("Stopping stream process...")
				self.stream_process.close(force=True)
				self.stream_process = None

	def stop(self):
		if (self.capture_process is not None):
			current_app.logger.info("Stopping capture process...")
			self.capture_process.close(force=True)
			self.capture_process = None
		if (self.stream_process is not None):
			thread = threading.Thread(target=self.stop_stream, args=(current_app._get_current_object(),))
			thread.start()
