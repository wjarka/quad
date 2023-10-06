from flask import Blueprint, current_app
import discord
from discord.ext import commands
from blinker import signal
from .common import Game
from .youtube import YouTubeUploader
from .core import signal_game_ends
from threading import Thread
from io import BytesIO
import cv2
import asyncio


bp = Blueprint('discord', __name__)

@signal_game_ends.connect
def send_screenshot(sender, game, **extra):
	webhook = discord.SyncWebhook.from_url(current_app.config["DISCORD_WEBHOOK_GAMES"])
	frame = game.get_final_score_frame()
	if (frame is not None):
		img_string = BytesIO(cv2.imencode('.png', frame)[1].tobytes())
		file = discord.File(img_string, filename="image.png")
		embed = discord.Embed()
		embed.set_image(url="attachment://image.png")
		webhook.send(game.get_game_identifier(), file=file, embed=embed)

def bot():
	intents = discord.Intents.default()
	intents.message_content = True
	bot = commands.Bot(command_presfix='$', intents=intents)

	async def reaction_youtube(sender, payload, **extra):
		if ("DISCORD_YOUTUBE_UPLOAD_ALLOWED_USERS" in current_app.config and payload.user_id not in current_app.config["DISCORD_YOUTUBE_UPLOAD_ALLOWED_USERS"]):
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
	
	signal('discord-reaction-youtube').connect(reaction_youtube)

	@bot.event
	async def on_raw_reaction_add(payload):
		await signal('discord-reaction-' + payload.emoji.name).send_async(current_app._get_current_object(), payload=payload)		
	
	bot.run(current_app.config["DISCORD_BOT_SECRET"])

class DiscordBotThread(Thread):

	daemon = True

	def __init__(self, app):
		super().__init__()
		self.app = app

	def run(self):
		with (self.app.app_context()):
			event_loop = asyncio.new_event_loop()
			asyncio.set_event_loop(event_loop)
			bot()