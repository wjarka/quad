from flask import current_app
from datetime import datetime
import time

def prepare_command(command, always_local = False):
	if (always_local):
		return command
	if (current_app.config["FFMPEG_OVER_SSH"]):
		ssh = f'ssh -t {current_app.config["FFMPEG_OVER_SSH_HOST"]}'
		command = f'{ssh} "{command}"'
	return command

class Pacer:
	def __init__(self, interval = 0.5):
		self.interval = interval
		self.starttime = None

	def pace(self, interval = None):
		if (interval is not None):
			self.interval = interval
		if (self.starttime is None):
			self.starttime = time.monotonic()
		else:
			sleep_time = self.interval - ((time.monotonic() - self.starttime) % self.interval)
			time.sleep(sleep_time)

class Game:
	def __init__(self, data = None):
		if (data is None):
			data = {}
		self.data = data
		
	@classmethod
	def from_id(cls, id):
		meta = id[20:]
		p_name, p_champ, vs, o_name, o_champ, map = meta.split('-')
		game = Game({
			'time': id[0:19],
			'p_name': p_name,
			'p_champion': p_champ.strip("()"), 
			'o_name': o_name, 
			'o_champion': o_champ.strip("()"), 
			'map': map
		})
		return game

	def set_game_start_time(self):
		self.data['start_timestamp'] = datetime.now()
		self.data['time'] = self.data['start_timestamp'].strftime("%Y-%m-%d-%H-%M-%S")

	def _path_dictionary(self):
		return {
			'year': self.data['time'][0:4], 
			'month': self.data['time'][5:7],
			'game_id': self.get_game_identifier()
		}

	def get_recording_path(self):
		return current_app.config["PATH_RECORDING"].format(**self._path_dictionary())

	def get_screenshot_path(self):
		return current_app.config["PATH_SCREENSHOT"].format(**self._path_dictionary())

	def get_game_identifier(self):
		return '-'.join([
			self.data['time'],
			self.data['p_name'],
			'(' + self.data['p_champion'] + ')',
			'vs',
			self.data['o_name'],
			'(' + self.data['o_champion'] + ')',
			self.data['map']
		])

	def get_final_score_frame(self):
		if (self.has('scoreboard')):
			return self.get('scoreboard')
		elif (self.has('last_frame_alive')):
			return self.get('last_frame_alive')
		else:
			return None

	def has(self, name):
		return (name in self.data)

	def get(self, name):
		return self.data[name]

	def set(self, name, value):
		self.data[name] = value

	def update(self, data):
		self.data.update(data)
