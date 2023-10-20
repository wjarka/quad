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

class QuakeStats:
	def player_exists(self, name):
		import requests
		r = requests.get(f'https://quake-stats.bethesda.net/api/v2/Player/Search?term={name}')
		if (r.status_code == 200):
			for entity in r.json():
				if (entity.get('entityName') == name):
					return True
		return False

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
	def __init__(self, data = None, model = None):
		if (data is None):
			data = {}
		self.data = {}
		from . import models
		if (model is None):
			self.model = models.Game()
		else: 
			self.model = model
		self.update(data)
		
	@classmethod
	def from_id(cls, id):
		meta = id[20:]
		p_name, p_champ, vs, o_name, o_champ, map = meta.split('-')
		game = Game({
			'time': id[0:19],
			'player_name': p_name,
			'player_champion_id': p_champ.strip("()"), 
			'opponent_name': o_name, 
			'opponent_champion_id': o_champ.strip("()"), 
			'map_id': map
		})
		return game

	def set_paths(self):
		from .extensions import db
		self.model.recording_path = current_app.config["PATH_RECORDING"].format(**self._path_dictionary())
		self.model.screenshot_path = current_app.config["PATH_SCREENSHOT"].format(**self._path_dictionary())
		db.session.commit()

	def game_starts(self):
		from .extensions import db
		db.session.add(self.model)
		db.session.flush()
		self.set_paths()

	def _path_dictionary(self):
		return {
			'year': self.model.timestamp.strftime("%Y"), 
			'month': self.model.timestamp.strftime("%m"),
			'game_id': self.get_game_identifier()
		}

	def get_game_identifier(self):
		return '-'.join([
			self.get('timestamp').strftime("%Y-%m-%d-%H-%M-%S"),
			self.get('player_name'),
			'(' + self.get('player_champion').name + ')',
			'vs',
			self.get('opponent_name'),
			'(' + self.get('opponent_champion').name + ')',
			self.get('map').name
		])

	def get_final_score_frame(self):
		if (self.has('scoreboard') and self.get('scoreboard') is not None):
			return self.get('scoreboard')
		elif (self.has('last_frame_alive') and self.get('last_frame_alive') is not None):
			return self.get('last_frame_alive')
		else:
			return None

	def has(self, key):
		return (hasattr(self.model, key) or key in self.data)

	def get(self, key):
		if hasattr(self.model, key):
			return getattr(self.model, key)
		return self.data[key]

	def set(self, key, value):
		if hasattr(self.model, key):
			setattr(self.model, key, value)
		else:
			self.data[key] = value

	def update(self, dict):
		for key, value in dict.items():
			self.set(key, value)
