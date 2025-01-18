from . import db
import os
import datetime
from sqlalchemy import String, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from typing_extensions import Annotated

intpk = Annotated[int, mapped_column(primary_key=True)]
timestamp = Annotated[
    datetime.datetime,
    mapped_column(nullable=False, server_default=func.CURRENT_TIMESTAMP()),
]


class MassUpdateableMixin:
    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


class Champion(db.Model):
    name: Mapped[str] = mapped_column(String(12), primary_key=True)

    @hybrid_property
    def template_path(self):
        return os.path.join("assets", "champions", self.name + ".png")

    def __repr__(self):
        return self.name


class Map(db.Model):
    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(25))

    @hybrid_property
    def template_path(self):
        return os.path.join("assets", "maps", self.code + ".png")

    def __repr__(self):
        return self.name


class Player(db.Model):
    id: Mapped[intpk]
    name: Mapped[str]


class OcrVocabulary(db.Model):
    id: Mapped[intpk]
    text_read: Mapped[str]
    text: Mapped[str]


class Game(MassUpdateableMixin, db.Model):
    id: Mapped[intpk]
    timestamp: Mapped[timestamp]
    player_name: Mapped[str] = mapped_column(String(15))
    player_champion_id: Mapped[str] = mapped_column(ForeignKey("champion.name"))
    player_champion: Mapped["Champion"] = relationship(
        foreign_keys=[player_champion_id]
    )
    opponent_name: Mapped[str] = mapped_column(String(15))
    opponent_champion_id: Mapped[str] = mapped_column(ForeignKey("champion.name"))
    opponent_champion: Mapped["Champion"] = relationship(
        foreign_keys=[opponent_champion_id]
    )
    map_id: Mapped[str] = mapped_column(ForeignKey("map.code"))
    map: Mapped["Map"] = relationship()
    recording_path: Mapped[str] = mapped_column(nullable=True)
    screenshot_path: Mapped[str] = mapped_column(nullable=True)
    discord_message_id: Mapped[int] = mapped_column(nullable=True)
    youtube_id: Mapped[str] = mapped_column(nullable=True)
