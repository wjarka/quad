import pytest
from quad.record import RecorderManager

def test_recorder_start(recorder_ffmpegh264qsv, mocker, ndi, game_ready_to_record):
	r = recorder_ffmpegh264qsv
	assert r.bitrate == "6M"
	r.bitrate = "8M"
	assert r.record_process is None

	ffmpeg_process = mocker.patch('pexpect.spawn')
	ffmpeg_process.return_value = 1
	mkdir_process = mocker.patch('pexpect.run')

	r.start(game_ready_to_record)

	from datetime import datetime
	assert game_ready_to_record.get('timestamp') == datetime(1971, 2, 3, 10, 45, 15)

	assert r.record_process == 1
	mkdir_process.assert_called_once_with("mkdir -p /tmp/Games/1971/02")
	ffmpeg_process.assert_called_once_with("ffmpeg -hide_banner -loglevel error -hwaccel qsv -hwaccel_output_format qsv \
            -use_wallclock_as_timestamps 1 -rtbufsize 1024M -thread_queue_size 8192 -f libndi_newtek -i 'NDI' \
            -codec:v h264_qsv -threads 0 -codec:a aac -g 250 -keyint_min 250 -profile:v main \
            -preset medium -b:v 8M -bufsize 1M -maxrate 8M '/tmp/Games/1971/02/1971-02-03-10-45-15-SL4VE-(Slash)-vs-b00m MaaV-(Galena)-Molten Falls.mp4' -y")

	from sqlalchemy import inspect
	insp = inspect(game_ready_to_record.model)
	assert insp.persistent

def test_save_last_score(mocker, game_after_recording_started, ndi, session, recorder_manager):
	recorder = recorder_manager
	game = game_after_recording_started
	mkdir = mocker.patch('pexpect.run')
	write_image = mocker.patch('cv2.imwrite')
	recorder.save_last_score(game)
	mkdir.assert_called_once_with("mkdir -p /tmp/Games/1971/02")
	write_image.assert_called_once()
	
	assert game.get('screenshot_path') == '/tmp/Games/1971/02/1971-02-03-10-45-15-SL4VE-(Slash)-vs-b00m MaaV-(Galena)-Molten Falls.png'

	from sqlalchemy import inspect
	insp = inspect(game.model)
	assert insp.persistent
	
	game.set('scoreboard', None)
	write_image.reset_mock()
	recorder.save_last_score(game)
	write_image.assert_not_called()
