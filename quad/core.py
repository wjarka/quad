from flask import Blueprint, current_app
from .record import RecorderManager
from .stream import TwitchStream
from .common import Pacer
from .games import Game
from .ndi import finder
from .ndi import receiver as r
from . import matchers as m
from blinker import signal
from datetime import datetime, timedelta
from . import zmq
from . import tools

signal_game_found = signal("game-found")
signal_game_starts = signal("game-starts")
signal_game_ends = signal("game-ends")
signal_game_cancelled = signal("game-cancelled")

bp = Blueprint("core", __name__)


@bp.cli.command("run")
def run():
    core = Core()
    core.run()


@bp.cli.command("stop")
def stop():
    client = zmq.Client()
    client.stop_service("core")


class Core:

    def __init__(self):
        self.ndi_connector = NdiConnector(current_app.config["NDI_STREAM"])
        self.recorder_manager = RecorderManager()
        self.stream = TwitchStream()
        self.zmq = zmq.Server(["core", "stream", "frame-capture"])
        self.pacer = Pacer()
        self.frame_processor = FrameProcessor()
        self.save_frames = False
        self.stop = False

    def start_threads(self):
        from .discord import DiscordBotThread

        discord = DiscordBotThread(current_app._get_current_object())
        discord.start()

    def shutdown(self):
        current_app.logger.info("Starting app shutdown...")
        self.recorder_manager.stop()
        self.stream.stop()
        self.stop = True

    def process_message(self, message=None):
        try:
            if message is not None:
                if message.service == "core" and message.action == "stop":
                    self.shutdown()
                if message.service == "stream":
                    if message.action == "start":
                        self.stream.start()
                    if message.action == "stop":
                        self.stream.stop()
                if message.service == "frame-capture":
                    self.save_frames = message.action == "start"
                self.zmq.respond_success()
        except Exception:
            self.zmq.respond_fail()

    def run(self):
        self.start_threads()
        while not self.stop:
            self.pacer.pace()
            frame = self.ndi_connector.read()
            if self.save_frames:
                tools.save_frame(frame)
            self.frame_processor.process(frame)
            self.process_message(self.zmq.get_message())
        self.zmq.shutdown()


class NdiConnector:
    timeout = 70
    max_retries = 1

    def __init__(self, source_name):
        self.source_name = source_name
        self.find = finder.create_ndi_finder()
        self.receiver = None
        self.retry_interval = 0
        self.last_frame_received_time = None
        self.last_failed_connection_attempt_time = None
        self.connect()

    def get_source_name(self):
        return self.source_name

    def _can_retry(self):
        return (
            self.last_failed_connection_attempt_time is None
            or self.last_failed_connection_attempt_time
            + timedelta(seconds=self.retry_interval)
            < datetime.now()
        )

    def connect(self):
        if not self._can_retry():
            return
        retries = 0

        while retries < self.max_retries:
            sources = self.find.get_sources()
            for source in sources:
                if source.name == self.source_name:
                    self.receiver = r.create_receiver(source)
                    current_app.logger.info("Connected to '" + source.simple_name + "'")
                    self.last_failed_connection_attempt_time = None
                    self.retry_interval = 5
                    return
            retries += 1
        self.last_failed_connection_attempt_time = datetime.now()
        if self.retry_interval < 60:
            self.retry_interval = self.retry_interval + 5
        current_app.logger.info(
            "No connection estabilished. Retrying in "
            + str(self.retry_interval)
            + " seconds..."
        )

    def _is_connected(self):
        return self.receiver is not None

    def disconnect(self):
        self.receiver = None

    def _is_timed_out(self):
        if (
            self.last_frame_received_time is not None
            and self.last_frame_received_time + timedelta(seconds=self.timeout)
            < datetime.now()
        ):
            return True
        return False

    def read(self):
        frame = None
        if not self._is_connected():
            self.connect()
        if self._is_connected():
            frame = self.receiver.read()
        if frame is None:
            if self._is_timed_out():
                current_app.logger.info(
                    "No frame received in "
                    + str(self.timeout)
                    + " seconds. Disconnecting..."
                )
                self.disconnect()
                self.last_frame_received_time = None
        else:
            self.last_frame_received_time = datetime.now()
        return frame


class FrameProcessor:
    STATUS_LABELS = ["Waiting for game", "Game Found", "Recording"]
    STATUS_WAITING_FOR_GAME = 0
    STATUS_GAME_FOUND = 1
    STATUS_RECORDING = 2

    def __init__(self):
        self.flow = self.create_flow()
        self.current_scenarios = []
        self.current_status = None
        self.change_status(self.STATUS_WAITING_FOR_GAME)
        self.game = Game()

    def process(self, frame):
        if frame is None:
            return None
        for scenario in self.flow[self.current_status]:
            self._process_scenario(frame, **scenario)

    def _process_scenario(
        self, frame, matchers=None, signals=None, status=None, actions=None
    ):
        if matchers is None:
            matchers = []
        assert len(matchers) > 0
        if signals is None:
            signals = []
        if actions is None:
            actions = []
        for matcher in matchers:
            found, meta = matcher.match(frame)
            if found:
                for action in actions:
                    action(frame, meta)
                for signal_handler in signals:
                    signal_handler.send(self, frame=frame, game=self.game)
                if status is not None:
                    self.change_status(status, matcher)

    def create_flow(self):
        flow = {
            self.STATUS_WAITING_FOR_GAME: [
                {
                    "matchers": [m.MapLoading()],
                    "status": self.STATUS_GAME_FOUND,
                    "actions": [self.reset_game, self.update_game],
                    "signals": [signal_game_found],
                }
            ],
            self.STATUS_GAME_FOUND: [
                {
                    "matchers": [m.WarmupEnd()],
                    "status": self.STATUS_RECORDING,
                    "actions": [self.update_game, self.game_starts],
                    "signals": [signal_game_starts],
                },
                {
                    "matchers": [m.MenuLoading(), m.MainMenu(), m.Desktop5Seconds()],
                    "status": self.STATUS_WAITING_FOR_GAME,
                    "actions": [self.update_game],
                    "signals": [signal_game_cancelled],
                },
            ],
            self.STATUS_RECORDING: [
                {
                    "matchers": [m.DuelEndScoreboard()],
                    "status": self.STATUS_WAITING_FOR_GAME,
                    "actions": [self.update_game, self.set_scoreboard],
                    "signals": [signal_game_ends],
                },
                {
                    "matchers": [
                        m.MenuLoading(),
                        m.MainMenu(),
                        m.Desktop5Seconds(),
                    ],
                    "status": self.STATUS_WAITING_FOR_GAME,
                    "actions": [self.update_game],
                    "signals": [signal_game_ends],
                },
                {
                    "matchers": [m.IsAlive()],
                    "actions": [self.update_game, self.set_last_frame_alive],
                },
            ],
        }
        return flow

    def change_status(self, status, trigger=None):
        if self.current_status != status:
            self.current_status = status
            if trigger is not None:
                current_app.logger.info(trigger.__class__.__name__ + " triggered.")
            current_app.logger.info(
                "Current Status: " + self.STATUS_LABELS[self.current_status]
            )

    def update_game(self, frame, meta):
        self.game.update(meta)

    def set_scoreboard(self, frame, meta):
        self.game.set("scoreboard", frame)

    def set_last_frame_alive(self, frame, meta):
        self.game.set("last_frame_alive", frame)

    def game_starts(self, frame, meta):
        from datetime import datetime

        self.game.set("timestamp", datetime.now())
        self.game.save_model()

    def reset_game(self, frame, meta):
        self.game = Game(data=meta, model=None)
