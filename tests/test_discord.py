import pytest

def test_send_screenshot(app, db, session, mocker, game):
	from unittest.mock import MagicMock
	message = MagicMock()
	message.id = 123
	webhook = MagicMock()
	send = webhook.send
	send.return_value = message
	mocker.patch('discord.SyncWebhook.from_url').return_value = webhook
	# game = game_saved
	game.save_model()
	from quad.discord import send_screenshot
	send_screenshot(game)
	send.assert_called_once()
	assert game.get('discord_message_id') == 123
	
	from sqlalchemy import select
	from quad.models import Game
	retrieved_game = db.session.scalars(select(Game)).first()
	assert retrieved_game.discord_message_id == 123

	webhook.reset_mock()
	
	game.set('scoreboard', None)
	send_screenshot(game)
	webhook.send.assert_not_called()