import pytest
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


