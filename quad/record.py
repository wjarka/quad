from __future__ import annotations

from abc import ABCMeta, abstractmethod
from flask import current_app
import os
import pexpect


class RecorderManager:
    def __init__(self):
        from .games import GamePathGenerator
        self.path_generator = GamePathGenerator()
        self.current_recorder = None
        self.available_recorders = []
        for recorder in current_app.config["RECORDERS"].split(','):
            print(f"Adding recorder {recorder}")
            self.available_recorders.append(RecorderFactory.get(recorder))
        print(self.available_recorders)
        for recorder in self.available_recorders:
            print(recorder)
        from .core import signal_game_starts, signal_game_ends
        signal_game_starts.connect(self.on_game_starts)
        signal_game_ends.connect(self.on_game_ends)

    def save_last_score(self, game):
        path = self.path_generator.get_screenshot_path(game)
        dir_to_create = os.path.dirname(path)
        pexpect.run(f"mkdir -p {dir_to_create}")
        frame = game.get_final_score_frame()
        if frame is not None:
            import cv2
            cv2.imwrite(path, frame)
            game.set('screenshot_path', path)
            game.save_model()

    def get_recorder(self):
        if self.current_recorder is not None:
            return self.current_recorder
        for recorder in self.available_recorders:
            print(f"Checking {recorder}")
            if recorder.can_record():
                return recorder

    def on_game_starts(self, sender, frame, game, **extra):
        self.get_recorder().start(game)

    def on_game_ends(self, sender, frame, game, **extra):
        self.save_last_score(game)
        self.get_recorder().stop()
        self.current_recorder = None

    def stop(self): #Legacy
        self.get_recorder().stop()

class RecorderFactory:
    @classmethod
    def get(cls, name):
        if name == 'obs':
            return ObsRecorder()
        if name == 'x264':
            return FfmpegX264Recorder()
        if name == 'h264_qsv':
            return FfmpegH264QsvRecorder()


class Recorder:

    def can_record(self):
        return True

    def start(self, game):
        pass

    def stop(self):
        pass


class FfmpegRecorder(Recorder, metaclass=ABCMeta):
    def __init__(self):
        super().__init__()
        self.record_process = None
        if "RECORDER_BITRATE" in current_app.config:
            self.bitrate = current_app.config["RECORDER_BITRATE"]
        else:
            self.bitrate = '6M'

    def start(self, game):
        from quad.games import GamePathGenerator
        path_generator = GamePathGenerator()
        super().start(game)
        path = path_generator.get_recording_path(game)
        game.set('recording_path', path)
        source_name = current_app.config["NDI_STREAM"]
        dir_to_create = os.path.dirname(path)
        command = self.prepare_ffmpeg_command(path, source_name)
        from .common import prepare_command
        dir_command = prepare_command(f"mkdir -p {dir_to_create}")

        pexpect.run(dir_command)
        self.record_process = pexpect.spawn(command)
        game.save_model()
        return True

    @abstractmethod
    def prepare_ffmpeg_command(self, path, source_name):
        pass

    def stop(self):
        super().stop()
        if self.record_process is not None:
            self.record_process.sendintr()


class FfmpegX264Recorder(FfmpegRecorder):

    def prepare_ffmpeg_command(self, path, source_name):
        from .common import prepare_command
        return prepare_command(f"ffmpeg -hide_banner -loglevel error \
		 -use_wallclock_as_timestamps 1 -rtbufsize 1024M -thread_queue_size 8192 -f libndi_newtek -i '{source_name}' \
		 -codec:v libx264 -threads 0 -codec:a aac -g 250 -keyint_min 250 \
		 -preset medium -b:v {self.bitrate} -bufsize 1M -maxrate {self.bitrate} '{path}' -y")


class FfmpegH264QsvRecorder(FfmpegRecorder):

    def prepare_ffmpeg_command(self, path, source_name):
        from .common import prepare_command
        return prepare_command(f"ffmpeg -hide_banner -loglevel error -hwaccel qsv -hwaccel_output_format qsv \
            -use_wallclock_as_timestamps 1 -rtbufsize 1024M -thread_queue_size 8192 -f libndi_newtek -i '{source_name}' \
            -codec:v h264_qsv -threads 0 -codec:a aac -g 250 -keyint_min 250 -profile:v main \
            -preset medium -b:v {self.bitrate} -bufsize 1M -maxrate {self.bitrate} '{path}' -y")


class ObsRecorder(Recorder):

    def __init__(self):
        super().__init__()
        self.current_game = None
        self.obs = None

    def can_record(self):
        return self.connect()

    def connect(self):
        from websocket import WebSocketConnectionClosedException
        if self.obs is None:
            return self._connect()
        try:
            self.obs.get_version()
        except WebSocketConnectionClosedException:
            return self._connect()
        return True

    def _connect(self):
        import obsws_python as obs
        try:
            self.obs = obs.ReqClient(host=current_app.config["OBS_WEBSOCKET_IP"],
                                     password=current_app.config["OBS_WEBSOCKET_PASSWORD"],
                                     port=current_app.config["OBS_WEBSOCKET_PORT"],
                                     timeout=1)
            return True
        except TimeoutError:
            return False

    def start(self, game):
        super().start(game)
        self.current_game = game
        if self.connect():
            self.obs.start_record()

    def stop(self):
        super().stop()
        if not self.connect():
            return
        result = self.obs.stop_record()
        import os
        source_path = os.path.join(current_app.config["OBS_RECORDING_BASE_DIR"],
                                   os.path.basename(result.output_path))
        from .games import GamePathGenerator
        path_generator = GamePathGenerator()
        destination_path = path_generator.get_recording_path(self.current_game)
        pexpect.run(f"mv \"{source_path}\" \"{destination_path}\"")
        self.current_game = None
        self.obs.disconnect()
