from flask import current_app, Blueprint


bp = Blueprint('games', __name__)

# @bp.cli.command('import')
# def game_import():
# 	gi = GameImporter()
# 	gi.import_games()
# 	print(gi.find_recordings())

# class GameImporter():
# 	def import_games(self):
# 		pass

# 	def find_recordings(self):
# 		import glob
# 		return glob.glob('/Volumes/Quake/Games/**/*.mp4', recursive=True)
    

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

	def save_model(self):
		from .extensions import db
		from sqlalchemy import inspect
		state = inspect(self.model)
		if (state.transient):
			db.session.add(self.model)
		db.session.commit()

	def get_player_champion_name(self):
		return self.get('player_champion_id')

	def get_opponent_champion_name(self):
		return self.get('opponent_champion_id')

	def get_map_name(self):
		if (self.get('map') is not None):
			return self.get('map').name
		if (self.get('map_id') is not None):
			from .models import Map
			from .extensions import db
			return db.session.get(Map, self.get('map_id')).name
		return None

	def get_game_identifier(self):
		return '-'.join([
			self.get('timestamp').strftime("%Y-%m-%d-%H-%M-%S"),
			self.get('player_name'),
			'(' + self.get_player_champion_name() + ')',
			'vs',
			self.get('opponent_name'),
			'(' + self.get('opponent_champion_id') + ')',
			self.get_map_name()
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
