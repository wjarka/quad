from __future__ import annotations
import click
from flask import Blueprint, current_app, g
import signal as s
from blinker import signal
import pexpect
import multiprocessing


bp = Blueprint('stream', __name__)

@bp.cli.command('stop')
def stop():
	from .core import ProcessManagerZmqClient
	r = ProcessManagerZmqClient()
	r.stop_process('twitch-stream')


@bp.cli.command('start')
def start():
	from .core import ProcessManagerZmqClient
	r = ProcessManagerZmqClient()
	r.start_process('twitch-stream')	



class TwitchStreamProcess(multiprocessing.Process):
	def __init__(self):
		super().__init__()
		self.sigterm_default_handler = s.getsignal(s.SIGTERM)
		self.capture_process = None
		self.stream_process = None
		self.stream_delay_increments = 4
		self.stream_delay = current_app.config['TWITCH_DELAY']
		if ("RECORDER_BITRATE" in current_app.config):
			self.bitrate = current_app.config["RECORDER_BITRATE"]
		else:
			self.bitrate = '6M'
		self.ndi_source_name = current_app.config["NDI_STREAM"]
		self.playlist_path = "/tmp/out.m3u8"
		self.stream_key = current_app.config["TWITCH_STREAM_KEY"]
	

	def run(self):
		import time
		s.signal(s.SIGTERM, self.stop)
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
		stream_command = prepare_command(f"ffmpeg -thread_queue_size 8192 -re -live_start_index 0 \
			-i {self.playlist_path} -c copy -f flv \
			rtmp://waw02.contribute.live-video.net/app/{self.stream_key}")
		time.sleep(self.stream_delay)
		self.stream_process = pexpect.spawn(stream_command)
		while True:
			time.sleep(1)


	def stop(self, _signo, _stack_frame):
		current_app.logger.info("Stopping stream gracefully...")
		if (self.capture_process is not None):
			current_app.logger.info("Stopping capture process...")
			self.capture_process.terminate(force=True)
		if (self.stream_process is not None):
			import time
			time.sleep(self.stream_delay)
			self.stream_process.terminate(force=True)
		s.signal(s.SIGTERM, self.sigterm_default_handler)
		import sys
		sys.exit(0)