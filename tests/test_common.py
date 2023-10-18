import pytest

@pytest.mark.parametrize('nick,status_code,json,expected_result', [
	('SL4VE', 404, [], False),
	('SL4VE', 404, [{"entityName": "SL4VE"}], False),
	('SL4VE', 200, [], False),
	('SL4VE', 200, [{"entityName": "SL4VE beta account"}], False),
	('SL4VE', 200, [{"entityName": "asd"}], False),
	('SL4VE', 200, [{"entityName": "SL4VE"}], True),
])
def test_quake_stats_player_exists(mocker, nick, status_code, json, expected_result):
	from unittest.mock import MagicMock
	mock = MagicMock()
	mock.status_code = status_code
	mock.json.return_value = json
	mocker.patch('requests.get').return_value = mock

	from quad.common import QuakeStats
	stats = QuakeStats()
	assert expected_result == stats.player_exists(nick)

@pytest.mark.parametrize('command,always_local,ssh,result', [
	('test', True, True, 'test'),
	('test', True, False, 'test'),
	('test', False, True, 'ssh -t localhost "test"'),
	('test', False, False, 'test'),
])
def test_prepare_command(app, command, always_local, ssh, result):
	from quad.common import prepare_command
	app.config["FFMPEG_OVER_SSH"] = ssh
	app.config["FFMPEG_OVER_SSH_HOST"] = "localhost"
	assert result == prepare_command(command, always_local)

def test_pacer():
	from quad.common import Pacer
	pacer = Pacer()
	import time
	pacer.pace()
	start = time.monotonic()
	pacer.pace(interval=0.2)
	passed = time.monotonic() - start
	assert passed >= 0.2

def test_game_init_model():
	from quad.common import Game
	import quad.models
	model = quad.models.Game()
	game = Game(model=model)
	assert game.model == model

def test_game_init_data():
	from quad.common import Game
	data = {'test': 'test_value'}
	game = Game(data)
	assert game.data == data

def test_game_has():
	from quad.common import Game
	game = Game()
	assert game.has('player_name') == True
	assert game.has('random_string') == False
	game.set('random_string', 'test')
	assert game.has('random_string') == True

def test_game_set():
	from quad.common import Game
	game = Game()
	game.set('random_string', 'test')
	assert 'random_string' in game.data
	assert game.data['random_string'] == 'test'
	game.set('player_name', 'player1')
	assert 'player_name' not in game.data
	assert game.model.player_name == 'player1'

def test_game_get():
	from quad.common import Game
	import quad.models
	game = Game(data={'test': 'test_value', 'player_name': 'name_in_data'}, model=quad.models.Game(player_name='test_name'))
	assert game.get('player_name') == 'name_in_data'
	assert game.get('test') == 'test_value'

def test_game_game_starts(db, session, game):
	from sqlalchemy import select
	import quad.models as models
	assert db.session.query(models.Game).count() == 0
	assert game.get('id') is None
	import datetime
	game.set('timestamp', datetime.datetime(1970,1,1))
	game.game_starts()
	retrieved_game = db.session.scalars(select(models.Game)).first()
	assert retrieved_game.id is not None
	assert game.model.player_name == retrieved_game.player_name
	assert game.model.player_champion_id == retrieved_game.player_champion_id
	assert game.model.opponent_name == retrieved_game.opponent_name
	assert game.model.opponent_champion_id == retrieved_game.opponent_champion_id
	assert game.model.map_id == retrieved_game.map_id
	assert retrieved_game.recording_path == "/tmp/Games/1970/01/1970-01-01-00-00-00-Player One-(Ranger)-vs-Player Two-(Nyx)-Awoken.mp4"
	assert retrieved_game.screenshot_path == "/tmp/Games/1970/01/1970-01-01-00-00-00-Player One-(Ranger)-vs-Player Two-(Nyx)-Awoken.png"
