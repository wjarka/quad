from __future__ import annotations
from flask import Blueprint, current_app
from .common import Pacer, Game
import shlex
from .ndi import finder
from .ndi import receiver as r
import time
from . import matchers as m
from blinker import signal
from datetime import datetime, timedelta
import os
import cv2
import pexpect

bp = Blueprint('stream', __name__)
signal_game_found = signal('game-found')
signal_game_starts = signal('game-starts')
signal_game_ends = signal('game-ends')
signal_game_cancelled = signal('game-cancelled')


@bp.cli.command('process')
def process_stream():
	pacer = Pacer()
	ndi_connector = NdiConnector(current_app.config["NDI_STREAM"])
	frame_reader = FrameReader(ndi_connector)
	frame_processor = FrameProcessor()
	recorder = Recorder(ndi_connector)
	try:
		while (True):
			pacer.pace()
			frame = frame_reader.read()
			frame_processor.process(frame)
	finally:
		recorder.stop()

@signal_game_ends.connect
def save_last_score(sender, game, **extra):
	path = game.get_screenshot_path()
	dir_to_create = os.path.dirname(path)
	pexpect.run(f"mkdir -p {dir_to_create}")
	frame = game.get_final_score_frame()
	if (frame is not None):
		cv2.imwrite(path, frame)


class Recorder:
	def __init__(self, ndi_connector: NdiConnector, bitrate=None):
		self.ndi_connector = ndi_connector
		self.record_process = None
		self.bitrate = bitrate
		if (self.bitrate is None):
			if ("RECORDER_BITRATE" in current_app.config):
				self.bitrate = current_app.config["RECORDER_BITRATE"]
			else:
				self.bitrate = '6M'

		signal_game_starts.connect(self.on_game_starts)
		signal_game_ends.connect(self.on_game_ends)


	def on_game_starts(self, sender, frame, game, **extra):
		self.start(game.get_recording_path())

	def on_game_ends(self, sender, frame, game, **extra):
		self.stop()

	def start(self, path):
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

	def stop(self):
		if (self.record_process is not None):
			self.record_process.sendintr()
			

class FrameProcessor:

	STATUS_LABELS = ["Waiting for game", "Game Found", "Recording"]
	STATUS_WAITING_FOR_GAME = 0
	STATUS_GAME_FOUND = 1
	STATUS_RECORDING = 2

	def __init__(self):
		self.flow = self.create_flow()
		self.current_scenarios = []
		self.current_status = None
		self.change_status(self.STATUS_WAITING_FOR_GAME)
		self.game = Game()

	def process(self, frame):

		if (frame is None):
			return None
		for scenario in self.flow[self.current_status]:
			self._process_scenario(frame, **scenario)

	def _process_scenario(self, frame, matchers=None, signals=None, status = None, actions=None):
		if (matchers is None):
			matchers = []
		assert(len(matchers) > 0)
		if (signals is None):
			signals = []
		if (actions is None):
			actions = []
		for matcher in matchers:
			found, meta = matcher.match(frame)
			if (found):
				self.game.update(meta)
				for action in actions:
					action(frame, meta)
				for signal in signals:
					signal.send(self, frame=frame, game=self.game)
				if (status is not None):
					self.change_status(status, matcher)		

	def create_flow(self):
		flow = {
			self.STATUS_WAITING_FOR_GAME: [{
				'matchers': [m.MapLoading()], 
				'status': self.STATUS_GAME_FOUND,
				'actions': [self.reset_game],
				'signals': [signal_game_found]
			}],
			self.STATUS_GAME_FOUND: [{
				'matchers': [m.WarmupEnd()], 
				'status': self.STATUS_RECORDING, 
				'actions': [self.set_game_start_time],
				'signals': [signal_game_starts]
			},{
				'matchers': [
					m.MenuLoading(),
					m.MainMenu(),
					m.Desktop5Seconds()
				], 
				'status': self.STATUS_WAITING_FOR_GAME, 
				'signals': [signal_game_cancelled]
			}],
			self.STATUS_RECORDING: [{
				'matchers': [m.DuelEndScoreboard()], 
				'status': self.STATUS_WAITING_FOR_GAME,
				'actions': [self.set_scoreboard],
				'signals': [signal_game_ends]
			},{
				'matchers': [
					m.MenuLoading(),
					m.MainMenu(),
					m.Desktop5Seconds(),
				], 
				'status': self.STATUS_WAITING_FOR_GAME, 
				'signals': [signal_game_ends],
			}, {
				'matchers': [m.IsAlive()],
				'actions': [self.set_last_frame_alive]
			}],
		}
		return flow

	def change_status(self, status, trigger = None):
		if (self.current_status != status):
			self.current_status = status
			if (trigger is not None):
				current_app.logger.info(trigger.__class__.__name__ + " triggered.")
			current_app.logger.info("Current Status: " + self.STATUS_LABELS[self.current_status])

	def set_scoreboard(self, frame, meta):
		self.game.set('scoreboard', frame)

	def set_last_frame_alive(self, frame, meta):
		self.game.set('last_frame_alive', frame)

	def set_game_start_time(self, frame, meta):
		self.game.set_game_start_time()

	def reset_game(self, frame, meta):
		self.game = Game(meta)
		print(self.game.data)


class NdiConnector:

	timeout = 70

	def __init__(self, source_name):
		self.source_name = source_name
		self.connect()
		self.last_frame_received_time = None

	def get_source_name(self):
		return self.source_name

	def connect(self):
		find = finder.create_ndi_finder()
		self.receiver = None
		retry_interval = 5
		while (self.receiver is None):
			sources = find.get_sources()
			for source in sources:
				if (source.name == self.source_name):
					self.receiver = r.create_receiver(source)
					current_app.logger.info("Connected to '" + source.simple_name + "'")
					return 
			current_app.logger.info("No connection estabilished. Retrying in " + str(retry_interval) + " seconds...")
			time.sleep(retry_interval)
			if (retry_interval < 60):
				retry_interval = retry_interval + 5

	def _is_connected(self):
		return self.receiver is not None

	def disconnect(self):
		self.receiver = None

	def _is_timed_out(self):
		if (self.last_frame_received_time is not None and self.last_frame_received_time + timedelta(seconds=self.timeout) < datetime.now()):
			return True
		return False

	def read(self):
		if (not self._is_connected()):
			self.connect()
		frame = self.receiver.read()
		if (frame is None):
			while (frame is None and not self._is_timed_out()):
				frame = self.receiver.read()
			if (frame is None):
				current_app.logger.info("No frame received in " + str(self.timeout) + " seconds. Disconnecting...")
				self.disconnect()
				self.last_frame_received_time = None
		else:
			self.last_frame_received_time = datetime.now()
		return frame

class FrameReader:
	def __init__(self, ndi_connector):
		self.ndi_connector = ndi_connector

	def read(self):
		frame = None
		while (frame is None):
			frame = self.ndi_connector.read()
		return frame
