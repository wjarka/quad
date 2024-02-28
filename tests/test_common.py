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