import pytest

def test_game_init_model():
	from quad.games import Game
	import quad.models
	model = quad.models.Game()
	game = Game(model=model)
	assert game.model == model

def test_game_init_data():
	from quad.games import Game
	data = {'test': 'test_value'}
	game = Game(data)
	assert game.data == data

def test_game_has():
	from quad.games import Game
	game = Game()
	assert game.has('player_name') == True
	assert game.has('random_string') == False
	game.set('random_string', 'test')
	assert game.has('random_string') == True

def test_game_set():
	from quad.games import Game
	game = Game()
	game.set('random_string', 'test')
	assert 'random_string' in game.data
	assert game.data['random_string'] == 'test'
	game.set('player_name', 'player1')
	assert 'player_name' not in game.data
	assert game.model.player_name == 'player1'

def test_game_get():
	from quad.games import Game
	import quad.models
	game = Game(data={'test': 'test_value', 'player_name': 'name_in_data'}, model=quad.models.Game(player_name='test_name'))
	assert game.get('player_name') == 'name_in_data'
	assert game.get('test') == 'test_value'

def test_game_save_model(db, session, game):
	from sqlalchemy import select
	import quad.models as models
	assert db.session.query(models.Game).count() == 0
	assert game.get('id') is None
	import datetime
	game.save_model()
	retrieved_game = db.session.scalars(select(models.Game)).first()
	assert retrieved_game.id is not None
	assert game.model.player_name == retrieved_game.player_name
	assert game.model.player_champion_id == retrieved_game.player_champion_id
	assert game.model.opponent_name == retrieved_game.opponent_name
	assert game.model.opponent_champion_id == retrieved_game.opponent_champion_id
	assert game.model.map_id == retrieved_game.map_id
	assert retrieved_game.recording_path == "/tmp/Games/1971/02/1971-02-03-10-45-15-SL4VE-(Slash)-vs-b00m MaaV-(Galena)-Molten Falls.mp4"
	assert retrieved_game.screenshot_path == "/tmp/Games/1971/02/1971-02-03-10-45-15-SL4VE-(Slash)-vs-b00m MaaV-(Galena)-Molten Falls.png"

def test_game_get_champion_name(db, game):
	assert game.get_player_champion_name() == "Slash"
	assert game.get_opponent_champion_name() == "Galena"

def test_game_get_map_name(db, game):
	assert game.get_map_name() == "Molten Falls"

def test_game_get_game_identifier(db, session, game):
	import datetime
	game.set('timestamp', datetime.datetime(1971,2,3,12,30,55))
	assert game.get_game_identifier() == "1971-02-03-12-30-55-SL4VE-(Slash)-vs-b00m MaaV-(Galena)-Molten Falls"
	game.save_model()
	assert game.get_game_identifier() == "1971-02-03-12-30-55-SL4VE-(Slash)-vs-b00m MaaV-(Galena)-Molten Falls"
	# Test for both saved and unsaved model


def test_game_get_final_score_frame(frame_scoreboard, frame_alive):
	import cv2, numpy as np
	from quad.games import Game

	game = Game()
	assert game.get_final_score_frame() == None
	game.set('scoreboard', frame_scoreboard)
	assert np.array_equal(game.get_final_score_frame(), frame_scoreboard)
	game.set('scoreboard', None)
	assert game.get_final_score_frame() == None
	game.set('last_frame_alive', frame_alive)
	assert np.array_equal(game.get_final_score_frame(), frame_alive)
	game.set('last_frame_alive', None)
	assert game.get_final_score_frame() == None
	game.set('scoreboard', frame_scoreboard)
	game.set('last_frame_alive', frame_alive)
	assert np.array_equal(game.get_final_score_frame(), frame_scoreboard)


# def test_game_import_command(runner):
# 	result = runner.invoke(args=["games", "import"])
# 	assert "Error: No such command 'games'" not in result.output
# 	assert result.exception is None

# def test_game_importer_class_exists():
# 	from quad.games import GameImporter
# 	g = GameImporter()
# 	assert 1

# def test_game_importer_find_recordings():
# 	from quad.games import GameImporter
# 	g = GameImporter()
# 	result = g.find_recordings()
# 	assert result == []
	
