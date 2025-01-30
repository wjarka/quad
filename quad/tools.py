from flask import current_app, Blueprint
import os
import datetime
import cv2

bp = Blueprint("tools", __name__)
fc = Blueprint("frame-capture", __name__)


def save_frame(frame):
    if frame is None:
        return
    cv2.imwrite(
        os.path.join(
            current_app.config["TOOLS_SCREENSHOT_PATH"],
            datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S_%f"),
        )
        + ".png",
        frame,
    )


@bp.cli.command("screenshot")
def screenshot():
    from .core import NdiConnector

    ndi = NdiConnector(current_app.config["NDI_STREAM"])
    frame = None
    while frame is None:
        frame = ndi.read()

    save_frame(frame)


@fc.cli.command("stop")
def frame_capture_stop():
    from . import zmq

    r = zmq.Client()
    r.stop_service("frame-capture")


@fc.cli.command("start")
def frame_capture_start():
    from . import zmq

    r = zmq.Client()
    r.start_service("frame-capture")
