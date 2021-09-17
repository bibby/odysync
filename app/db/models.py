import os
import sys
import inspect
import errno
from peewee import *

DB_DIR = os.environ.get('DATA_VOLUME', '.') + "/db"
DB_FILE = DB_DIR + "/odysync.db"


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


class BaseModel(Model):
    class Meta:
        database = SqliteDatabase(DB_FILE, pragmas={'journal_mode': 'wal'})


class ChannelSite:
    LBRY=1
    YOUTUBE=2

    @staticmethod
    def to_name(n):
        d = dict()
        d[ChannelSite.LBRY] = "LBRY"
        d[ChannelSite.YOUTUBE] = "YOUTUBE"
        return d[n]


class Channel(BaseModel):
    id = CharField(primary_key=True, index=True, unique=True)
    site = IntegerField(default=0)

    @property
    def url(self):
        if self.site == ChannelSite.YOUTUBE:
            return 'https://www.youtube.com/c/{}/videos'.format(self.id)
        return NotImplementedError

    def serial(self):
        return dict(
            id=self.id,
            site=ChannelSite.to_name(self.site)
        )


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

    def serial(self):
        return dict(
            id=self.id,
            title=self.title,
            state=VideoState.to_name(self.state),
        )


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
