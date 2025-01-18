from flask import current_app
import time


def prepare_command(command, always_local=False):
    if always_local:
        return command
    if current_app.config["FFMPEG_OVER_SSH"]:
        ssh = f'ssh -t {current_app.config["FFMPEG_OVER_SSH_HOST"]}'
        command = f'{ssh} "{command}"'
    return command


class QuakeStats:
    def player_exists(self, name):
        import requests

        r = requests.get(
            f"https://quake-stats.bethesda.net/api/v2/Player/Search?term={name}"
        )
        if r.status_code == 200:
            for entity in r.json():
                if entity.get("entityName") == name:
                    return True
        return False


class Pacer:
    def __init__(self, interval=0.5):
        self.interval = interval
        self.starttime = None

    def pace(self, interval=None):
        if interval is not None:
            self.interval = interval
        if self.starttime is None:
            self.starttime = time.monotonic()
        else:
            sleep_time = self.interval - (
                (time.monotonic() - self.starttime) % self.interval
            )
            time.sleep(sleep_time)
