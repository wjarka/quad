import os

from flask import Flask, g
from .extensions import db, migrate

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        SQLALCHEMY_DATABASE_URI='sqlite:///quad.db',
        FFMPEG_OVER_SSH=False,
        OBS_RECORDING_SCENE="Recording",
        OBS_SKIP_RECORDING_WHEN_STREAMING = False,
        RECORDERS="x264"
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from logging.config import dictConfig
    dictConfig({
        'version': 1,
        'root': {
            'level': 'WARN' if "LOG_LEVEL" not in app.config else app.config["LOG_LEVEL"],
        }
    })
    
    from . import models

    db.init_app(app)
    migrate.init_app(app, db)

    from . import core
    app.register_blueprint(core.bp)

    from . import stream
    app.register_blueprint(stream.bp)

    from . import discord
    app.register_blueprint(discord.bp)

    from . import games
    app.register_blueprint(games.bp)

    return app