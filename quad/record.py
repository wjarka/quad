from __future__ import annotations
import click
from flask import Blueprint, current_app
from blinker import signal
import os
import pexpect

class Recorder:
	def __init__(self, ndi_connector, bitrate=None):
		self.ndi_connector = ndi_connector
		self.record_process = None
		self.bitrate = bitrate
		if (self.bitrate is None):
			if ("RECORDER_BITRATE" in current_app.config):
				self.bitrate = current_app.config["RECORDER_BITRATE"]
			else:
				self.bitrate = '6M'
		from .core import signal_game_starts, signal_game_ends
		signal_game_starts.connect(self.on_game_starts)
		signal_game_ends.connect(self.on_game_ends)


	def save_last_score(self, game):
		path = game.get_screenshot_path()
		dir_to_create = os.path.dirname(path)
		pexpect.run(f"mkdir -p {dir_to_create}")
		frame = game.get_final_score_frame()
		if (frame is not None):
			import cv2
			cv2.imwrite(path, frame)


	def on_game_starts(self, sender, frame, game, **extra):
		self.start(game.get_recording_path())

	def on_game_ends(self, sender, frame, game, **extra):
		self.save_last_score(game)
		self.stop()

	def start(self, path):
		source_name = self.ndi_connector.get_source_name()
		dir_to_create = os.path.dirname(path)
		from .common import prepare_command
		command = prepare_command(f"ffmpeg -hide_banner -loglevel error -hwaccel qsv -hwaccel_output_format qsv \
		 -use_wallclock_as_timestamps 1 -rtbufsize 1024M -thread_queue_size 8192 -f libndi_newtek -i '{source_name}' \
		 -codec:v h264_qsv -threads 0 -codec:a aac -g 250 -keyint_min 250 -profile:v main \
		 -preset medium -b:v {self.bitrate} -bufsize 1M -maxrate {self.bitrate} '{path}' -y")
		dir_command = prepare_command(f"mkdir -p {dir_to_create}")

		pexpect.run(dir_command)
		self.record_process = pexpect.spawn(command)

	def stop(self):
		if (self.record_process is not None):
			self.record_process.sendintr()
			