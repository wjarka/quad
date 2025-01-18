from flask import current_app, Blueprint
import os
import datetime

bp = Blueprint("tools", __name__)


@bp.cli.command("screenshot")
def screenshot():
    import cv2
    from .core import NdiConnector

    ndi = NdiConnector(current_app.config["NDI_STREAM"])
    frame = None
    while frame is None:
        frame = ndi.read()

    cv2.imwrite(
        os.path.join(
            current_app.config["TOOLS_SCREENSHOT_PATH"],
            datetime.datetime.now().strftime("%Y-%m-%d-%H-%m-%S"),
        )
        + ".png",
        frame,
    )
