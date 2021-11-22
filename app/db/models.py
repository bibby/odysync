import os
import sys
import inspect
from peewee import *
from db.util import action, mkdir_p, is_float
from munch import Munch

DB_DIR = os.environ.get('DATA_VOLUME', '.')
DB_FILE = os.path.join(DB_DIR, "odysync.db")


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

            if self.site == ChannelSite.LBRY:
                d.actions.append(action(
                    'match',
                    '/channel/{}/match'.format(self.id),
                    style="success",
                    xhr=None,
                ))

            if self.site == ChannelSite.YOUTUBE:
                d.actions.append(action(
                    'sync',
                    '/channel/{}/sync'.format(self.id),
                    style="success",
                    xhr=None,
                ))
        return d

    @staticmethod
    def for_site(site):
        return list(
            Channel.select().where(Channel.site == site))

    @staticmethod
    def serial_map(c):
        return c.serial()

    def match_others(self):
        title_index = dict()

        def state_resolve(vid):
            if isinstance(vid, list):
                resolve_result = []
                for v in vid:
                    resolve_result.append(state_resolve(v))
                return any(resolve_result)

            if vid.channel.site == ChannelSite.YOUTUBE:
                return

            if vid.channel.site == ChannelSite.LBRY:
                if vid.state == VideoState.UPLOADED:
                    return

                if vid.state != VideoState.NEW:
                    vid.state = VideoState.UPLOADED
                    vid.save()
                    return True

        for v in Video.select():
            t = v.title
            if t not in title_index:
                title_index[t] = []
            title_index[t].append(v)

        # resolve
        solo = []
        resolved = []
        odd = []
        for t, vids in title_index.items():
            serials = [v.serial() for v in vids]

            if len(vids) == 1:
                solo.append(serials[0])
                continue

            if len(vids) == 2:
                if state_resolve(vids):
                    resolved.append(serials)

            if len(vids) > 2:
                odd.append(serials)

        return Munch(
            odd=odd,
            solo=solo,
            resolved=resolved,
        )


class VideoState:
    ERROR = 6
    SKIPPED = 9
    NEW = 10
    INFOING = 15
    INFO = 16
    INFO_ERROR = 19
    DOWNLOADING = 20
    DOWNLOADED = 30
    DOWNLOAD_ERROR = 39
    TRANSCODING = 40
    TRANSCODED = 50
    TRANSCODE_ERROR = 59
    UPLOADING = 60
    UPLOADED = 70
    UPLOAD_ERROR = 79

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

        d[VideoState.INFO_ERROR] = 'Info Error'
        d[VideoState.DOWNLOAD_ERROR] = 'Download Error'
        d[VideoState.TRANSCODE_ERROR] = 'Transcode Error'
        d[VideoState.UPLOAD_ERROR] = 'Upload Error'
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
                vid = list(Video.select().where(Video.id == vid_id).limit(1))
                if len(vid):
                    vid = vid[0]
                else:
                    return False
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


class Config(BaseModel):
    k = CharField(primary_key=True)
    v = CharField(null=True)

    @staticmethod
    def load():
        r = Munch()
        for c in Config.select():
            r[c.k] = c.v or None
        return r

    @staticmethod
    def save_sync_settings(form):
        keys = [
            'src_channel',
            'dest_channel',
            'bid',
            'tags',
            'language',
            'license',
        ]

        kvs = dict()

        for k in keys:
            if k not in form:
                raise KeyError(k)
            if k == 'bid' and not is_float(form[k]):
                raise ValueError("bid should be a float: got " + str(form[k]))
            kvs[k] = form[v]

        return Config.set_all(kvs)


    @staticmethod
    def set_all(kvs):
        for k in kvs:
            Config.set(k, kvs[k])

    @staticmethod
    def set(k, v):
        c, _created = Config.get_or_create(k=k)
        c.v = v or ""
        c.save()


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
