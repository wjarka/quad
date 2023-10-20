import pytest

def test_uploadoptions_from_game(game_complete):
	from quad.youtube import UploadOptions
	game = game_complete
	o = UploadOptions.from_game(game)

	assert o.file == '/tmp/Games/1970/01/1970-01-01-00-00-00-SL4VE-(Slash)-vs-b00m MaaV-(Galena)-Molten Falls.mp4'
	assert o.title == 'SL4VE (Slash) vs b00m MaaV (Galena) Molten Falls (1970-01-01-00-00-00)'
	assert o.description == "Recorded with NDI QC Recorder by SL4VE"
	assert o.keywords == 'Slash,Galena,Molten Falls'

