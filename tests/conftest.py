import pytest
from quad import create_app

@pytest.fixture
def app():
	app = create_app({
		'TESTING': True,
	})

	yield app

@pytest.fixture
def client(app):
	return app.test_client()


@pytest.fixture
def runner(app):
	return app.test_cli_runner()

@pytest.fixture
def champion_matcher(app):
	with app.app_context():
		import quad.matchers as m
		return m.ChampionMatcher()

@pytest.fixture
def matchers(app):
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