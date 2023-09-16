from flask import Blueprint, current_app
import discord
from discord.ext import commands
from blinker import Namespace
from .common import Game
from .youtube import YouTubeUploader

bp = Blueprint('discord', __name__)

@bp.cli.command('bot')
def bot():
	intents = discord.Intents.default()
	intents.message_content = True
	bot = commands.Bot(command_presfix='$', intents=intents)
	discord_signals = Namespace()

	async def reaction_youtube(sender, payload):
		if (payload.user_id not in current_app.config["DISCORD_YOUTUBE_UPLOAD_ALLOWED_USERS"]):
			return

		channel = await bot.fetch_channel(payload.channel_id)
		message = await channel.fetch_message(payload.message_id)

		game = Game.from_id(message.content)
		yt = YouTubeUploader()
		yt_link = yt.upload(game)
		thread = message.thread
		if (thread is None):
			thread_name = game.get('p_name') + " vs " + game.get('o_name') + " (" + game.get('map') + ")"
			thread = await message.create_thread(name=thread_name)
		await thread.send(content = yt_link)
	
	discord_signals.signal('discord-reaction-youtube').connect(reaction_youtube)

	@bot.event
	async def on_raw_reaction_add(payload):
		await discord_signals.signal('discord-reaction-' + payload.emoji.name).send_async(current_app._get_current_object(), payload=payload)		
	
	bot.run(current_app.config["DISCORD_BOT_SECRET"])