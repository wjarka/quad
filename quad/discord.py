from flask import Blueprint, current_app
import discord
from discord.ext import commands
from blinker import signal
from .games import Game
from .youtube import YouTubeUploader
from .core import signal_game_ends
from threading import Thread
from io import BytesIO
import cv2
import asyncio

bp = Blueprint("discord", __name__)


@signal_game_ends.connect
def send_screenshot_hook(sender, game, **extra):
    send_screenshot(game)


def send_screenshot(game):
    frame = game.get_final_score_frame()
    webhook_url = current_app.config["DISCORD_WEBHOOK_GAMES"]
    text = game.get_game_identifier()
    if frame is not None:
        message = send_message(webhook_url, text, frame)
        from .extensions import db

        game.set("discord_message_id", message.id)
        db.session.commit()


def send_message(webhook_url, text, image=None):
    webhook = discord.SyncWebhook.from_url(webhook_url)
    if image is not None:
        img_string = BytesIO(cv2.imencode(".png", image)[1].tobytes())
        file = discord.File(img_string, filename="image.png")
        embed = discord.Embed()
        embed.set_image(url="attachment://image.png")
        message = webhook.send(text, file=file, embed=embed, wait=True)
    else:
        message = webhook.send(text)
    return message


def bot():
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="/", intents=intents)

    async def reaction_youtube(sender, payload, **extra):
        if (
            "DISCORD_YOUTUBE_UPLOAD_ALLOWED_USERS" in current_app.config
            and payload.user_id
            not in current_app.config["DISCORD_YOUTUBE_UPLOAD_ALLOWED_USERS"]
        ):
            return

        channel = await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        game = Game.from_discord_id(payload.message_id)
        if game is None or game.get("recording_path") is None:
            current_app.logger.error(
                "Cannot start YT upload: Game not found or no recording available"
            )
            return
        yt = YouTubeUploader()
        vid = yt.upload(game)
        game.set("youtube_id", vid)
        yt_link = f"https://youtube.com/watch?v={vid}"
        game.save_model()
        thread = message.thread
        if thread is None:
            thread_name = (
                game.get("player_name")
                + " vs "
                + game.get("opponent_name")
                + " ("
                + game.get_map_name()
                + ")"
            )
            thread = await message.create_thread(name=thread_name)
        await thread.send(content=yt_link)

    signal("discord-reaction-youtube").connect(reaction_youtube)

    @bot.event
    async def on_message(message):
        if (
            message.channel.id == current_app.config["DISCORD_GAMES_CHANNEL_ID"]
            and message.webhook_id is not None
            and message.interaction is None
        ):
            for emoji_id in current_app.config["DISCORD_ACTION_EMOJI_IDS"]:
                await message.add_reaction(bot.get_emoji(emoji_id))

    @bot.event
    async def on_raw_reaction_add(payload):
        await signal("discord-reaction-" + payload.emoji.name).send_async(
            current_app._get_current_object(), payload=payload
        )

    ocr = bot.create_group("ocr", "OCR Commands")

    @ocr.command(name="vocabulary-add")
    async def vocabulary_add(ctx: discord.ApplicationContext, current_name, name):
        from .games import PlayerRenamer

        renamer = PlayerRenamer()
        renamer.rename(current_name, name)
        await ctx.respond(
            "OCR Correction added to vocabulary. Attempted to fix previous games."
        )

    bot.run(current_app.config["DISCORD_BOT_SECRET"])


class DiscordBotThread(Thread):
    daemon = True

    def __init__(self, app):
        super().__init__()
        self.app = app

    def run(self):
        with self.app.app_context():
            event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(event_loop)
            bot()
