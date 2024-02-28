import pytest

def test_uploadoptions_from_game(game):
	from quad.youtube import UploadOptions
	o = UploadOptions.from_game(game)

	assert o.file == '/tmp/Games/1971/02/1971-02-03-10-45-15-SL4VE-(Slash)-vs-b00m MaaV-(Galena)-Molten Falls.mp4'
	assert o.title == 'SL4VE (Slash) vs b00m MaaV (Galena) Molten Falls (1971-02-03-10-45-15)'
	assert o.description == "Recorded with NDI QC Recorder by SL4VE"
	assert o.keywords == 'Slash,Galena,Molten Falls'

