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
    def __init__(self, data=None, model=None):
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
    def from_discord_id(cls, discord_id):
        from .extensions import db
        from sqlalchemy import select
        from .models import Game as GameModel
        game_model = db.session.scalar(select(GameModel).where(GameModel.discord_message_id == discord_id))
        print(discord_id)
        print(game_model)
        return Game(model=game_model)

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


class PlayerRenamer:
    def rename(self, current_name, name):
        from .models import OcrVocabulary
        from .models import Game as GameModel
        from .extensions import db
        from sqlalchemy import select
        existing_vocabulary = db.session.scalar(select(OcrVocabulary).where(OcrVocabulary.text_read == current_name))
        if existing_vocabulary is None:
            vocabulary = OcrVocabulary()
            vocabulary.text_read = current_name
            vocabulary.text = name
            db.session.add(vocabulary)
            db.session.commit()
        for game_model in db.session.scalars(select(GameModel).where(GameModel.player_name == current_name)):
            self.rename_game(Game(model=game_model), name, 'player_name')
        for game_model in db.session.scalars(select(GameModel).where(GameModel.opponent_name == current_name)):
            self.rename_game(Game(model=game_model), name, 'opponent_name')


    def rename_game(self, game, name, field):
        import pexpect
        import discord
        path_generator = GamePathGenerator()
        source_rec_path = game.get('recording_path')
        source_scr_path = game.get('screenshot_path')
        game.set(field, name)
        dest_rec_path = path_generator.get_recording_path(game)
        dest_scr_path = path_generator.get_screenshot_path(game)
        if source_rec_path:
            output, status = pexpect.run(f"mv \"{source_rec_path}\" \"{dest_rec_path}\"", withexitstatus=True)
            if status == 0:
                game.set('recording_path', dest_rec_path)
        if source_scr_path:
            output, status = pexpect.run(f"mv \"{source_scr_path}\" \"{dest_scr_path}\"", withexitstatus=True)
            if status == 0:
                game.set('screenshot_path', dest_scr_path)
        if game.get('discord_message_id') is not None:
            message_id = game.get('discord_message_id')
            try:
                webhook = discord.SyncWebhook.from_url(current_app.config["DISCORD_WEBHOOK_GAMES"])
                if message_id:
                    webhook.edit_message(message_id=message_id, content=game.get_game_identifier())
            except discord.NotFound:
                pass
        game.save_model()


class GamePathGenerator:
    def get_recording_path(self, game):
        return current_app.config["PATH_RECORDING"].format(**self._path_dictionary(game))

    def get_screenshot_path(self, game):
        return current_app.config["PATH_SCREENSHOT"].format(**self._path_dictionary(game))

    def _path_dictionary(self, game):
        return {
            'storage': current_app.config["PATH_STORAGE"],
            'year': game.get('timestamp').strftime("%Y"),
            'month': game.get('timestamp').strftime("%m"),
            'game_id': game.get_game_identifier()
        }
