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
		'PATH_RECORDING': "/tmp/Games/{year}/{month}/{game_id}.mp4",
		'PATH_SCREENSHOT': "/tmp/Games/{year}/{month}/{game_id}.png",
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
def game(session, frame_scoreboard):
	from quad.common import Game
	import quad.models as models
	game = Game(data = {
		'player_name': "SL4VE", 
		'opponent_name': "b00m MaaV", 
		'player_champion_id': "Slash",
		'opponent_champion_id': "Galena", 
		'map_id': "molten",
		"scoreboard": frame_scoreboard})
	return game

@pytest.fixture
def game_complete(session, game):
	import datetime
	game.game_starts()
	game.set('timestamp', datetime.datetime(1970,1,1))
	game.set_paths()
	return game

@pytest.fixture
def frame_scoreboard():
	import cv2
	return cv2.imread("tests/assets/scoreboard.png")

@pytest.fixture
def frame_alive():
	import cv2
	return cv2.imread('tests/assets/warmupend.png')
		