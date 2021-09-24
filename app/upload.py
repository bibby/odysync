import os
import time
import json
from db.util import UPLOAD_COOLDOWN, licenses
from db.queue import upQ, TRANSCODE_TMP, INFO_TMP
from db.models import Video, VideoState, Channel, Config
from munch import Munch, munchify
from youtube_dl import YoutubeDL
from youtube_dl import utils as YTUtil
from pybry.lbryd_api import LbrydApi

lbry = LbrydApi()


def load_info(vid_id):
    info_file = os.path.join(INFO_TMP, vid_id + '.info.json')

    if not os.path.isfile(info_file):
        raise FileNotFoundError(info_file)

    with open(info_file, 'r') as inf:
        data = inf.read()
        dataj = json.loads(data)
        info = munchify(dataj)

    return info


def get_youtube_thumb(vid_id):
    params = dict(
        forcethumbnail=True,

    )

    print(str(params))
    YTUtil.std_headers['User-Agent'] = 'curl/7.54.0'

    with YoutubeDL(params=params) as ytdl:
        url = 'https://www.youtube.com/watch?v=' + vid_id
        res = munchify(ytdl.extract_info(url, download=False))
        thumb = res.thumbnails.pop().url
        return thumb


def upload_video(vid_id, cleanup=True):
    info = load_info(vid_id)
    vid_file = os.path.join(TRANSCODE_TMP, vid_id + '.mp4')

    title = info.title
    description = info.description
    name = info.id

    settings = Config.load()

    channel = Channel.get(Channel.id == settings.dest_channel)
    bid = settings.bid
    tags = [t.lower() for t in
        (info.tags[:3] + [settings.tag1, settings.tag2, settings.tag3])
        if t]

    langs = [l for l in [settings.language] if l]

    license = settings.license or None
    license_url = None

    if license:
        for L in licenses():
            if L.id == license:
                license_url = L.url
                license = L.name
                break

    account_id = channel.address
    channel = channel.id

    thumbnail_url = get_youtube_thumb(vid_id)

    params = dict(
        account_id=account_id,
        file_path=vid_file,
        title=title,
        description=description,
        validate_file=False,
        optimize_file=False,
        languages=langs,
        tags=tags,
        channel_id=channel,
        preview=False,
        blocking=False,
        license=license,
        license_url=license_url,
        thumbnail_url=thumbnail_url,
    )

    data = dict(
        method="stream_create",
        params=params
    )

    print(json.dumps(data, indent=4))

    safety_on = os.environ.get('PUBLISH_SAFETY', None)
    if safety_on:
        return

    try:
        res, resp = lbry.stream_create(name, bid, **params)
        print(res)
    except Exception as e:
        print(e)
        return False


if __name__ == '__main__':
    print("Upload worker started")
    force = False
    cleanup = False

    while True:
        try:
            vid_id = upQ.dequeue()
            if vid_id:
                vid_id = vid_id.decode()
                print(vid_id)

                vid = Video.set_state(vid_id, VideoState.UPLOADING)
                if isinstance(vid, Video) or force:
                    upload_video(vid_id, cleanup=cleanup)
                    Video.set_state(vid, VideoState.UPLOADED)
                    print('cooling down for ' + str(UPLOAD_COOLDOWN))
                    time.sleep(UPLOAD_COOLDOWN)
                    print('cooled down. resuming')
        except Exception as e:
            print(e)
            Video.set_state(vid_id, VideoState.UPLOAD_ERROR)

        # except FileNotFoundError as e:
        #    vid

        time.sleep(1)
