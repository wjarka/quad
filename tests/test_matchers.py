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
def test_matcher_match(app, matchers, matcher, image_path, expected_result):
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
		result = champion_matcher.identifyChampion(cv2.imread(image_path))
	assert result == expected_result

@pytest.mark.parametrize('matcher,image_path,expected_data', [])
def test_matcher_data(app, matchers, matcher, image_path, expected_data):
	with app.app_context():
		result, data = matchers[matcher].match(cv2.imread(image_path))
	assert data == expected_data

@pytest.mark.parametrize('image_path,expected_name', [
	('tests/assets/warmupend.png', 'imgoingmid'),
	('tests/assets/ocr_sl4ve_scale_alexr_eisen.png', 'AlexR'),
	('tests/assets/ocr_sl4ve_ranger_purp1ef1sh2_nyx.png', 'Purp1eF1sh2'),
	('tests/assets/ocr_sl4ve_athena_airwalker_strogg.png', 'AirWalker'),
	('tests/assets/ocr_sl4ve_athena_x1ksAkaBerry_Eisen.png', 'x1ksAkaBerry'),
	('tests/assets/ocr_an1ol.png', 'an1ol'),
	('tests/assets/ocr_PLG_JSkey.png', 'PLG JSkey'),
	# ('tests/assets/ocr_.png', ''),
])
def test_warmupend_ocr(app, matchers, image_path, expected_name):
	with app.app_context():
		result, data = matchers['WarmupEnd'].match(cv2.imread(image_path))
	assert data['o_name'] == expected_name
