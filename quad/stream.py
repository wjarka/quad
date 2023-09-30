from __future__ import annotations
import click
from flask import Blueprint, current_app, g
import signal as s
from blinker import signal
import os
import pexpect
import multiprocessing

signal_game_ends = signal('game-ends')

bp = Blueprint('stream', __name__)

@bp.cli.command('twitch')
@click.argument("delay", required=False)
def stream_twitch(delay=None):

	print(f"Not implemented yet. Requested delay is {delay}")


# @bp.cli.command('process')
# def process_stream():
# 	pacer = Pacer()
# 	ndi_connector = NdiConnector(current_app.config["NDI_STREAM"])
# 	frame_reader = FrameReader(ndi_connector)
# 	frame_processor = FrameProcessor()
# 	recorder = Recorder(ndi_connector)
# 	try:
# 		while (True):
# 			pacer.pace()
# 			frame = frame_reader.read()
# 			frame_processor.process(frame)
# 	finally:
# 		recorder.stop()

@signal_game_ends.connect
def save_last_score(sender, game, **extra):
	import cv2
	path = game.get_screenshot_path()
	dir_to_create = os.path.dirname(path)
	pexpect.run(f"mkdir -p {dir_to_create}")
	frame = game.get_final_score_frame()
	if (frame is not None):
		cv2.imwrite(path, frame)


class RecorderProcess(multiprocessing.Process):
	def __init__(self):
		super().__init__()
		self.sigterm_default_handler = s.getsignal(s.SIGTERM)
		self.ndi_connector = g.ndi_connector
		self.record_process = None
		if ("RECORDER_BITRATE" in current_app.config):
			self.bitrate = current_app.config["RECORDER_BITRATE"]
		else:
			self.bitrate = '6M'
		
	def sigterm_handler(self, _signo, _stack_frame):
		self.stop()
		import sys
		sys.exit(0)

	def run(self):
		s.signal(s.SIGTERM, self.sigterm_handler)
		path = g.game.get_recording_path()
		source_name = self.ndi_connector.get_source_name()
		dir_to_create = os.path.dirname(path)
		command = f"ffmpeg -hide_banner -loglevel error -hwaccel qsv -hwaccel_output_format qsv \
		 -use_wallclock_as_timestamps 1 -rtbufsize 1024M -thread_queue_size 8192 -f libndi_newtek -i '{source_name}' \
		 -codec:v h264_qsv -threads 0 -codec:a aac -g 250 -keyint_min 250 -profile:v main \
		 -preset medium -b:v {self.bitrate} -bufsize 1M -maxrate {self.bitrate} '{path}' -y"
		dir_command = f"mkdir -p {dir_to_create}"

		if (current_app.config["FFMPEG_OVER_SSH"]):
			ssh = f'ssh -t {current_app.config["FFMPEG_OVER_SSH_HOST"]}'
			command = f'{ssh} "{command}"'
			dir_command = f'{ssh} "{dir_command}"'

		pexpect.run(dir_command)
		self.record_process = pexpect.spawn(command)
		import time
		while True:
			time.sleep(1)
		

	def stop(self):
		if (self.record_process is not None):
			self.record_process.sendintr()
			self.record_process.wait()
		s.signal(s.SIGTERM, self.sigterm_default_handler)
			
