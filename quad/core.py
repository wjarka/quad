from flask import Blueprint, current_app, g
import time
from .discord import DiscordBotProcess
from .stream import RecorderProcess
from .common import Pacer, Game
from .ndi import finder
from .ndi import receiver as r
from . import matchers as m
from blinker import signal
from datetime import datetime, timedelta
import zmq

signal_game_found = signal('game-found')
signal_game_starts = signal('game-starts')
signal_game_ends = signal('game-ends')
signal_game_cancelled = signal('game-cancelled')

bp = Blueprint('core', __name__)

@bp.cli.command('run')
def run():
	core = Core()
	core.run()

@bp.cli.command('stop')
def stop():
	r = ProcessManagerZmqClient()
	r.stop_process('core')

class ProcessManagerZmqClient:

	def send_command(self, process, action):
		socket = zmq.Context().socket(zmq.REQ)
		socket.connect('tcp://127.0.0.1:5000')
		socket.send_json({
			'process': process,
			'action': action,
		})
		response = socket.recv_json()
		current_app.logger.info(response)

	def start_process(self, name):
		self.send_command(name, 'start')

	def stop_process(self, name):
		self.send_command(name, 'stop')

class ProcessManagerZmqServer:
	zmq_port = 5000

	def __init__(self, process_manager):
		self.process_manager = process_manager
		self.zmq = zmq.Context().socket(zmq.REP)
		self.zmq.bind('tcp://127.0.0.1:' + str(self.zmq_port))
		self.zmq_pending_response = False

	def get_request_json(self):
		if (self.zmq_pending_response):
			return None
		try:
			json = self.zmq.recv_json(flags=zmq.NOBLOCK)
			self.zmq_pending_response = True
			return json
		except zmq.Again:
			return None
		
	def respond(self, result, data = None):
		if (data is None):
			data = {}
		if (self.zmq_pending_response):
			self.zmq.send_json({'success': result} | data)
			self.zmq_pending_response = False

	def respond_success(self):
		self.respond(True)

	def respond_fail(self, errors = None):
		self.respond(False, {'errors': errors})

	def shutdown(self):
		self.respond_success()

	def validate_request(self, json):
		process = json['process'] if 'process' in json else None
		errors = []
		if (process is None):
			errors.append("No process specified")
		if (not self.process_manager.is_process(process) and process != 'core'):
			errors.append(f"Process {process} does not exist")
		action = json['action'] if 'action' in json else None
		if (action is None):
			errors.append("No action specified")
		if (action not in ["start", "stop"]):
			errors.append(f"Action {action} is invalid")
		if (errors):
			return (False, errors)
		return (True, None)

	def process_messages(self):
		json = self.get_request_json()
		if (json is None):
			return
		result, data = self.validate_request(json)
		if (result == False):
			self.respond_fail(data)
		process = json['process']
		action = json['action']
		if (process == 'core' and action == 'stop'):
			signal('app-shutdown').send(self)
			return
		else:
			if (action == 'start'):
				current_app.logger.info(f"Starting {process}")
				self.process_manager.start_process(process)
			if (action == 'stop'):
				current_app.logger.info(f"Stopping {process}")
				self.process_manager.stop_process(process)
		self.respond_success()

class ProcessManager:
	def __init__(self):
		self.available_processes = {
			'discord-bot': DiscordBotProcess,
			'recorder': RecorderProcess,
		}
		self.autostart_processes = ['discord-bot']
		self.running_processes = {}

	def start_process(self, name):
		p = self.available_processes[name]()
		p.start()
		self.running_processes['name'] = p

	def stop_process(self, name):
		self.running_processes['name'].terminate()
		del self.running_processes['name']

	def is_process(self, name):
		return name in self.available_processes

	def _autostart(self):
		for name in self.autostart_processes:
			self.start_process(name)

	def _stop_running_processes(self):
		for name, process in self.running_processes.items():
			if (not process.daemon):
				process.terminate()

	def _await_process_shutdown(self):
		for name, process in self.running_processes.items():
			if (not process.daemon):
				process.join()


	def boot(self):
		self._autostart()

	def shutdown(self):
		self._stop_running_processes()
		self._await_process_shutdown()


class SignalHandler:

	def __init__(self, process_manager):
		self.process_manager = process_manager
		signal_game_starts.connect(self.start_recording)
		signal_game_ends.connect(self.stop_recording)

	def start_recording(self, sender, **extra):
		self.process_manager.start_process('recorder')

	def stop_recording(self, sender, **extra):
		self.process_manager.stop_process('recorder')

class Core:

	def __init__(self):
		ndi_connector = NdiConnector(current_app.config["NDI_STREAM"])
		g.ndi_connector = ndi_connector
		self.ndi_connector = ndi_connector
		self.process_manager = ProcessManager()
		self.process_manager_server = ProcessManagerZmqServer(self.process_manager)
		self.signal_handler = SignalHandler(self.process_manager)
		self.pacer = Pacer()
		signal('app-shutdown').connect(self.shutdown)
		self.frame_processor = FrameProcessor()
		self.stop = False
	
	def shutdown(self, sender, **extra):
		current_app.logger.info("Starting app shutdown...")
		self.stop = True

	def run(self):
		self.process_manager.boot()
		while (not self.stop):
			self.pacer.pace()
			frame = self.ndi_connector.read()
			self.frame_processor.process(frame)
			self.process_manager_server.process_messages()
		self.process_manager.shutdown()
		self.process_manager_server.shutdown()

		# Uruchom to co ma być autorun i oczekuj na instrukcje od klientów

class Client:

	def _send_command(self, payload):
		pass

	def start(self, service):
		payload = {'service': service, 'action': 'start'}

	def stop(self, service):
		payload = {'service': service, 'action': 'start'}		


class NdiConnector:

	timeout = 70
	max_retries = 1

	def __init__(self, source_name):
		self.source_name = source_name
		self.find = finder.create_ndi_finder()
		self.receiver = None
		self.retry_interval = 0
		self.last_frame_received_time = None
		self.last_failed_connection_attempt_time = None
		self.connect()
		
	def get_source_name(self):
		return self.source_name

	def _can_retry(self):
		return (self.last_failed_connection_attempt_time is None or self.last_failed_connection_attempt_time + timedelta(seconds=self.retry_interval) < datetime.now())

	def connect(self):
		if (not self._can_retry()):
			return
		retries = 0
		
		while (retries < self.max_retries):
			sources = self.find.get_sources()
			for source in sources:
				if (source.name == self.source_name):
					self.receiver = r.create_receiver(source)
					current_app.logger.info("Connected to '" + source.simple_name + "'")
					self.last_failed_connection_attempt_time = None
					self.retry_interval = 5
					return 
			retries += 1
		self.last_failed_connection_attempt_time = datetime.now()
		if (self.retry_interval < 60):
			self.retry_interval = self.retry_interval + 5
		current_app.logger.info("No connection estabilished. Retrying in " + str(self.retry_interval) + " seconds...")

	def _is_connected(self):
		return self.receiver is not None

	def disconnect(self):
		self.receiver = None

	def _is_timed_out(self):
		if (self.last_frame_received_time is not None and self.last_frame_received_time + timedelta(seconds=self.timeout) < datetime.now()):
			return True
		return False

	def read(self):
		frame = None
		if (not self._is_connected()):
			self.connect()
		if (self._is_connected()):
			frame = self.receiver.read()
		if (frame is None):
			if (self._is_timed_out()):
				current_app.logger.info("No frame received in " + str(self.timeout) + " seconds. Disconnecting...")
				self.disconnect()
				self.last_frame_received_time = None
		else:
			self.last_frame_received_time = datetime.now()
		return frame
		

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
		g.game = Game()

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
				g.game.update(meta)
				for action in actions:
					action(frame, meta)
				for signal in signals:
					signal.send(self, frame=frame, game=g.game)
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
		g.game.set('scoreboard', frame)

	def set_last_frame_alive(self, frame, meta):
		g.game.set('last_frame_alive', frame)

	def set_game_start_time(self, frame, meta):
		g.game.set_game_start_time()

	def reset_game(self, frame, meta):
		g.game = Game(meta)
		print(g.game.data)

