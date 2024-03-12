import pytest
from numpy.ma.testutils import assert_not_equal

from quad.core import FrameProcessor
from blinker import signal

STATUS_WAITING_FOR_GAME = 0
STATUS_GAME_FOUND = 1
STATUS_RECORDING = 2
	
def test_frame_processor_starting_status(app, fp, db):
	assert fp.current_status == fp.STATUS_WAITING_FOR_GAME

def test_status_codes(app, db, fp):
	assert fp.STATUS_WAITING_FOR_GAME == STATUS_WAITING_FOR_GAME
	assert fp.STATUS_GAME_FOUND == STATUS_GAME_FOUND
	assert fp.STATUS_RECORDING == STATUS_RECORDING

@pytest.mark.parametrize('signal_to_mute,start_status,image_path,end_status', [
	(signal('game-found'), STATUS_WAITING_FOR_GAME, 'tests/assets/warmupend.png', STATUS_WAITING_FOR_GAME),
	(signal('game-found'), STATUS_WAITING_FOR_GAME, 'tests/assets/scoreboard.png', STATUS_WAITING_FOR_GAME),
	(signal('game-found'), STATUS_WAITING_FOR_GAME, 'tests/assets/desktop-qc.png', STATUS_WAITING_FOR_GAME),
	(signal('game-found'), STATUS_WAITING_FOR_GAME, 'tests/assets/desktop-no-qc.png', STATUS_WAITING_FOR_GAME),
	(signal('game-found'), STATUS_WAITING_FOR_GAME, 'tests/assets/main-menu.png', STATUS_WAITING_FOR_GAME),
	(signal('game-found'), STATUS_WAITING_FOR_GAME, 'tests/assets/loading-menu.png', STATUS_WAITING_FOR_GAME),
	(signal('game-found'), STATUS_WAITING_FOR_GAME, 'tests/assets/loading-map.png', STATUS_GAME_FOUND),
	(signal('game-starts'), STATUS_GAME_FOUND, 'tests/assets/warmupend.png', STATUS_RECORDING),
	(signal('game-cancelled'), STATUS_GAME_FOUND, 'tests/assets/loading-menu.png', STATUS_WAITING_FOR_GAME),
	(signal('game-cancelled'), STATUS_GAME_FOUND, 'tests/assets/main-menu.png', STATUS_WAITING_FOR_GAME),
	# (signal('game-cancelled'), STATUS_GAME_FOUND, 'tests/assets/desktop-qc.png', STATUS_WAITING_FOR_GAME),
	# (signal('game-ends'), STATUS_RECORDING, 'tests/assets/desktop-no-qc.png', STATUS_WAITING_FOR_GAME),
	(signal('game-ends'), STATUS_RECORDING, 'tests/assets/main-menu.png', STATUS_WAITING_FOR_GAME),
	(signal('game-ends'), STATUS_RECORDING, 'tests/assets/loading-menu.png', STATUS_WAITING_FOR_GAME),
	(signal('game-ends'), STATUS_RECORDING, 'tests/assets/scoreboard.png', STATUS_WAITING_FOR_GAME),
])
def test_frame_processor_status_transitions(app, fp, db, session, requests_get_404, signal_to_mute, start_status, image_path, end_status):
	import cv2
	fp.change_status(start_status)
	frame = cv2.imread(image_path)
	with signal_to_mute.muted():
		fp.process(frame)
	assert fp.current_status == end_status

def test_database_consistency(app, fp, db, session):
	import cv2
	fp.change_status(STATUS_WAITING_FOR_GAME)
	with signal('game-found').muted():
		frame = cv2.imread('tests/assets/loading-map.png')
		fp.process(frame)
	assert_not_equal(fp.game.model, None)
	assert fp.game.get_map_name() == 'Exile'

	with signal('game-starts').muted():
		frame = cv2.imread('tests/assets/warmupend.png')
		fp.process(frame)
	from quad.extensions import db
	from sqlalchemy import inspect
	state = inspect(fp.game.model)
	assert state.persistent == True
	session.refresh(fp.game.model)
	assert_not_equal(fp.game.model.id, None)
	previous_id = fp.game.model.id

	with signal('game-ends').muted():
		frame = cv2.imread('tests/assets/scoreboard.png')
		fp.process(frame)

	with signal('game-found').muted():
		frame = cv2.imread('tests/assets/loading-map-awoken.png')
		fp.process(frame)

	from sqlalchemy	import select
	from quad.models import Game as GameModel
	game_model = db.session.scalar(select(GameModel).where(GameModel.id == previous_id))
	assert_not_equal(game_model, None)
	assert_not_equal(fp.game.model.id, previous_id)
	assert_not_equal(fp.game.model.id, game_model.id)
	assert fp.game.model.map_id == 'awoken'
	assert game_model.map_id == 'exile'