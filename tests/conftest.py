import pytest
from quad import create_app
from quad.extensions import db as _db
from flask_migrate import upgrade as flask_migrate_upgrade, downgrade as flask_migrate_downgrade


@pytest.fixture(scope="session")
def app():

	app = create_app({
		'TESTING': True,
		'SQLALCHEMY_DATABASE_URI': 'sqlite:///quad-test.db',
		'DISCORD_WEBHOOK_GAMES': 'discord-webhook-dummy-value',
		'PATH_STORAGE': "/tmp/Games",
		'PATH_RECORDING': "{storage}/{year}/{month}/{game_id}.mp4",
		'PATH_SCREENSHOT': "{storage}/{year}/{month}/{game_id}.png",
	})
	with app.app_context():
		yield app

@pytest.fixture(scope="session")
def db(app, request):
    """Session-wide test database."""

    def teardown():
        flask_migrate_downgrade()
        _db.drop_all()
    _db.app = app

    flask_migrate_upgrade()
    request.addfinalizer(teardown)
    return _db

@pytest.fixture(scope="function")
def session(db, request):
    db.session.begin_nested()
    def commit():
        db.session.flush()    
    # patch commit method
    old_commit = db.session.commit
    db.session.commit = commit
    def teardown():
        db.session.rollback()
        db.session.close()
        db.session.commit = old_commit
    request.addfinalizer(teardown)
    return db.session

@pytest.fixture
def client(app):
	return app.test_client()


@pytest.fixture
def runner(app):
	return app.test_cli_runner()

@pytest.fixture(scope="session")
def champion_matcher(app, db):
	with app.app_context():
		import quad.matchers as m
		return m.ChampionMatcher()

@pytest.fixture(scope="session")
def requests_get_404(session_mocker):
	session_mocker.patch('requests.get').return_value.status_code = 404

@pytest.fixture(scope="session")
def matchers(app, db, session_mocker):
	with app.app_context():
		import quad.matchers as m
		return {
			"WarmupEnd": m.WarmupEnd(),
			'Scoreboard': m.Scoreboard(),
			'DuelEndScoreboard': m.DuelEndScoreboard(),
			'IsAlive': m.IsAlive(),
			'Desktop': m.Desktop(),
			'MainMenu': m.MainMenu(),
			'MenuLoading': m.MenuLoading(),
			'MapLoading': m.MapLoading()
		}

@pytest.fixture(scope="session")
def fp(app, db):
	with app.app_context():
		from quad.core import FrameProcessor
		return FrameProcessor()

@pytest.fixture
def ndi():
	from quad.core import NdiConnector
	return NdiConnector("NDI")	

@pytest.fixture
def new_game():
	from quad.games import Game
	return Game()

@pytest.fixture
def game_ready_to_record():
	from quad.games import Game
	import datetime
	game = Game(data = {
		'player_name': "SL4VE", 
		'opponent_name': "b00m MaaV", 
		'player_champion_id': "Slash",
		'opponent_champion_id': "Galena", 
		'map_id': "molten",
	})
	return game

@pytest.fixture
def game_after_recording_started(session, game_ready_to_record, frame_scoreboard):
	import datetime
	game_ready_to_record.update({
		'timestamp': datetime.datetime(1971,2, 3, 10, 45, 15),
		"recording_path": "/tmp/Games/1971/02/1971-02-03-10-45-15-SL4VE-(Slash)-vs-b00m MaaV-(Galena)-Molten Falls.mp4",
		"scoreboard": frame_scoreboard,
	})
	return game_ready_to_record


@pytest.fixture
def game(session, game_after_recording_started, frame_scoreboard):
	from quad.games import Game
	game_after_recording_started.update(
	{
		"screenshot_path": "/tmp/Games/1971/02/1971-02-03-10-45-15-SL4VE-(Slash)-vs-b00m MaaV-(Galena)-Molten Falls.png"
	})
	return game_after_recording_started

@pytest.fixture
def game_saved(session, game):
	game.save_model()
	return game

@pytest.fixture
def frame_scoreboard():
	import cv2
	return cv2.imread("tests/assets/scoreboard.png")

@pytest.fixture
def frame_alive():
	import cv2
	return cv2.imread('tests/assets/warmupend.png')

@pytest.fixture
def recorder(ndi):
	from quad.record import Recorder
	class RecorderStub(Recorder):
		def set_timestamp(self, game):
			from datetime import datetime
			game.set('timestamp', datetime(1971, 2, 3, 10, 45, 15))
	
	return RecorderStub(ndi)
		