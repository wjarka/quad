import cv2
import pathlib
import os
import pytest
import quad.matchers as m

@pytest.mark.parametrize('matcher,image_path,expected_result', [
	('WarmupEnd', 'tests/assets/warmupend.png', True),
	('WarmupEnd', 'tests/assets/warmupend_bot.png', False),
	('Scoreboard', 'tests/assets/scoreboard.png', True),
	('DuelEndScoreboard', 'tests/assets/scoreboard.png', True),
	('Scoreboard', 'tests/assets/warmupend.png', False),
	('Scoreboard', 'tests/assets/warmupend_bot.png', False),
	('Scoreboard', 'tests/assets/scoreboard-mid-duel.png', True),
	('DuelEndScoreboard', 'tests/assets/scoreboard-mid-duel.png', False),
	('IsAlive', 'tests/assets/warmupend.png', True),
	('IsAlive', 'tests/assets/warmupend_bot.png', True),
	('IsAlive', 'tests/assets/scoreboard.png', False),
	('Desktop', 'tests/assets/desktop-qc.png', True),
	('Desktop', 'tests/assets/desktop-no-qc.png', True),
	('Desktop', 'tests/assets/scoreboard.png', False),
	('MainMenu', 'tests/assets/main-menu.png', True),
	('MenuLoading', 'tests/assets/loading-menu.png', True),
	('MapLoading', 'tests/assets/loading-map.png', True)
])
def test_matcher_match(app, requests_get_404, matchers, mocker, matcher, image_path, expected_result):
	# assert os.path.isfile(image_path) == True
	with app.app_context():
		result, data = matchers[matcher].match(cv2.imread(image_path))
	assert result == expected_result

@pytest.mark.parametrize('image_path,expected_result', [
	('tests/assets/Anarki.png', 'Anarki'),
	('tests/assets/Athena.png', 'Athena'),
	('tests/assets/BJ.png', 'BJ'),
	('tests/assets/Clutch.png', 'Clutch'),
	('tests/assets/DK.png', 'DK'),
	('tests/assets/Doom.png', 'Doom'),
	('tests/assets/Eisen.png', 'Eisen'),
	('tests/assets/Galena.png', 'Galena'),
	('tests/assets/Keel.png', 'Keel'),
	('tests/assets/Nyx.png', 'Nyx'),
	('tests/assets/Ranger.png', 'Ranger'),
	('tests/assets/Scalebearer.png', 'Scalebearer'),
	('tests/assets/Slash.png', 'Slash'),
	('tests/assets/Sorlag.png', 'Sorlag'),
	('tests/assets/Strogg.png', 'Strogg'),
	('tests/assets/Visor.png', 'Visor')
])
def test_champion_matcher(app, champion_matcher, image_path, expected_result):
	assert os.path.isfile(image_path) == True
	with app.app_context():
		result = champion_matcher.identify_champion(cv2.imread(image_path))
	assert result == expected_result

@pytest.mark.parametrize('matcher,image_path,expected_data', [
	('MapLoading', 'quad/assets/maps/awoken.png', {"map_id": "awoken"}),
	('MapLoading', 'quad/assets/maps/bc.png', {"map_id": "bc"}),
	('MapLoading', 'quad/assets/maps/ck.png', {"map_id": "ck"}),
	('MapLoading', 'quad/assets/maps/crucible.png', {"map_id": "crucible"}),
	('MapLoading', 'quad/assets/maps/deep.png', {"map_id": "deep"}),
	('MapLoading', 'quad/assets/maps/molten.png', {"map_id": "molten"}),
	('MapLoading', 'quad/assets/maps/ruins.png', {"map_id": "ruins"}),
	('MapLoading', 'quad/assets/maps/vale.png', {"map_id": "vale"}),
	('MapLoading', 'quad/assets/maps/insomnia.png', {"map_id": "insomnia"}),
	('MapLoading', 'quad/assets/maps/exile.png', {"map_id": "exile"}),
])
def test_matcher_data(app, matchers, matcher, image_path, expected_data):
	with app.app_context():
		result, data = matchers[matcher].match(cv2.imread(image_path))
	assert data == expected_data

@pytest.mark.parametrize('image_path,expected_name', [
	('tests/assets/warmupend.png', 'imgoingmid'),
	('tests/assets/ocr_sl4ve_scale_alexr_eisen.png', 'AlexR'),
	('tests/assets/ocr_sl4ve_athena_airwalker_strogg.png', 'AirWalker')
	# ('tests/assets/ocr_.png', ''),
])
def test_warmupend_ocr(app, requests_get_404, mocker, matchers, image_path, expected_name):
	with app.app_context():
		result, data = matchers['WarmupEnd'].match(cv2.imread(image_path))
	assert data['opponent_name'] == expected_name

# def test_player_exists(app, db, matchers):

