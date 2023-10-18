import pytest
from quad.record import Recorder

def test_recorder_start(mocker, ndi):
	r = Recorder(ndi, "8M")
	assert r.bitrate == "8M"
	assert r.record_process is None

	ffmpeg_process = mocker.patch('pexpect.spawn')
	ffmpeg_process.return_value = 1
	mkdir_process = mocker.patch('pexpect.run')

	r.start('/tmp/Games/game.mp4')

	assert r.record_process == 1
	mkdir_process.assert_called_once_with("mkdir -p /tmp/Games")
	ffmpeg_process.assert_called_once_with("ffmpeg -hide_banner -loglevel error -hwaccel qsv -hwaccel_output_format qsv \
		 -use_wallclock_as_timestamps 1 -rtbufsize 1024M -thread_queue_size 8192 -f libndi_newtek -i 'NDI' \
		 -codec:v h264_qsv -threads 0 -codec:a aac -g 250 -keyint_min 250 -profile:v main \
		 -preset medium -b:v 8M -bufsize 1M -maxrate 8M '/tmp/Games/game.mp4' -y")

def test_recorder_default_bitrate(mocker, ndi):
	r = Recorder(ndi)
	assert r.bitrate == "6M"