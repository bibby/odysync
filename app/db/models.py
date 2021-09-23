import os
import sys
import inspect
from peewee import *
from db.util import action
from db.util import mkdir_p
from munch import Munch

DB_DIR = os.environ.get('DATA_VOLUME', '.')
DB_FILE = DB_DIR + "/odysync.db"


class BaseModel(Model):
    class Meta:
        database = SqliteDatabase(DB_FILE, pragmas={'journal_mode': 'wal'})


class ChannelSite:
    LBRY = 1
    YOUTUBE = 2

    @staticmethod
    def to_name(n):
        d = dict()
        d[ChannelSite.LBRY] = "LBRY"
        d[ChannelSite.YOUTUBE] = "YOUTUBE"
        return d[n]


class Channel(BaseModel):
    id = CharField(primary_key=True, index=True, unique=True)
    name = CharField()
    site = IntegerField(default=0)
    address = CharField(null=True)

    @property
    def url(self):
        if self.site == ChannelSite.YOUTUBE:
            return 'https://www.youtube.com/c/{}/videos'.format(self.id)
        return NotImplementedError

    def serial(self, actions=None):
        d = Munch(
            id=self.id,
            site=ChannelSite.to_name(self.site),
            name=self.name,
        )

        if actions:
            d.update(dict(actions=[
                action(
                    'delete',
                    '/channel/{}/delete'.format(self.id),
                    style='error',
                    xhr=None,
                )
            ]))

            if self.site == ChannelSite.YOUTUBE:
                d.actions.append(action(
                    'sync',
                    '/channel/{}/sync'.format(self.id),
                    style="success",
                    xhr=None,
                ))
        return d


class VideoState:
    ERROR = 6
    SKIPPED = 9
    NEW = 10
    INFOING = 15
    INFO = 16
    DOWNLOADING = 20
    DOWNLOADED = 30
    TRANSCODING = 40
    TRANSCODED = 50
    UPLOADING = 60
    UPLOADED = 70

    @staticmethod
    def to_name(n):
        d = dict()
        d[VideoState.ERROR] = 'Error'
        d[VideoState.SKIPPED] = 'Skipped'
        d[VideoState.NEW] = 'New'
        d[VideoState.INFOING] = 'Queued'
        d[VideoState.INFO] = 'Got Info'
        d[VideoState.DOWNLOADING] = 'Downloading'
        d[VideoState.DOWNLOADED] = 'Downloaded'
        d[VideoState.TRANSCODING] = 'Transcoding'
        d[VideoState.TRANSCODED] = 'Transcoded'
        d[VideoState.UPLOADING] = 'Uploading'
        d[VideoState.UPLOADED] = 'Uploaded'
        return d[n]


class Video(BaseModel):
    id = CharField(primary_key=True, index=True, unique=True)
    channel = ForeignKeyField(Channel, backref='videos')
    title = TextField(null=True)
    state = IntegerField(default=0)

    def serial(self, actions=None):
        d = Munch(
            id=self.id,
            title=self.title,
            state=VideoState.to_name(self.state),
            channel=Munch(
                name=self.channel.name,
                site=ChannelSite.to_name(self.channel.site),
            )
        )

        if actions:
            d.update(dict(actions=[

            ]))

        return d

    @staticmethod
    def set_state(vid_id, state):
        if vid_id is False:
            return False

        err_class = Video.DoesNotExist
        if isinstance(vid_id, Video):
            vid = vid_id
        else:
            try:
                vid = Video.get(Video.id == vid_id)
            except err_class as e:
                print(str(e))
                return False

        vid.state = state
        vid.save()
        return vid


class Sync(BaseModel):
    youtube = ForeignKeyField(Video, backref="yt_link")
    lbry = ForeignKeyField(Video, backref="lbry_link")
    state = IntegerField(default=0)


def create_all_tables():
    mkdir_p(DB_DIR)
    for cls in sys.modules[__name__].__dict__.values():
        if not inspect.isclass(cls):
            continue
        if not hasattr(cls, '__bases__'):
            continue
        if not issubclass(cls, Model):
            continue
        if cls is Model:
            continue
        if cls is not BaseModel:
            cls.create_table()


if not os.path.isfile(DB_FILE):
    create_all_tables()
