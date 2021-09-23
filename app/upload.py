import os
import time
import json
from db.queue import upQ, TRANSCODE_TMP, INFO_TMP
from db.models import Video, VideoState, Channel
from munch import Munch, munchify


def load_info(vid_id):
    info_file = os.path.join(INFO_TMP, vid_id + '.info.json')

    if not os.path.isfile(info_file):
        raise FileNotFoundError(info_file)

    with open(info_file, 'r') as inf:
        data = inf.read()
        dataj = json.loads(data)
        info = munchify(dataj)

    return info


def load_thumbnail(vid_id, ext=None):
    ext = ext or "png"
    thumb_file = os.path.join(INFO_TMP, vid_id + '.' + ext)
    if not os.path.isfile(thumb_file):
        if ext != "jpg":
            return load_thumbnail(vid_id, ext="jpg")
        raise FileNotFoundError(thumb_file)

    # TODO: upload to somewhere
    return thumb_file


def upload_video(vid_id, cleanup=True):
    info = load_info(vid_id)
    vid_file = os.path.join(TRANSCODE_TMP, vid_id + 'mp4')

    title = info.title
    description = info.description
    name = info.id

    # TODO: some kind of first work settings
    settings = Munch()

    channel = Channel.get(Channel.id == settings.chan_id)
    bid = "0.001"  # from settings
    tags = info.tags[:3]

    langs = settings.langs or []
    license = settings.license or None
    license_url = ""

    account_id = channel.address
    channel = channel.id

    thumbnail_url = ""  # thumbnail result

    data = dict(
        method="stream_create",
        params=dict(
            name=name,
            bid=bid,
            account_id=account_id,
            file_path=vid_file,
            title=title,
            description=description,
            validate_file=False,
            optimaize_file=False,
            languages=langs,
            tags=tags,
            channel_id=channel,
            preview=False,
            blocking=False,
            license=license,
            license_url=license_url,
            thumbnail_url=thumbnail_url,
        )
    )

    print(json.dumps(data, indent=4))
    return


if __name__ == '__main__':
    print("Upload worker started")
    force = True

    while True:
        try:
            vid_id = upQ.dequeue()
            if vid_id:
                vid_id = vid_id.decode()
                print(vid_id)

                vid = Video.set_state(vid_id, VideoState.UPLOADING)
                if isinstance(vid_id, Video) or force:
                    upload_video(vid_id)
                    Video.set_state(vid, VideoState.UPLOADED)
        except FileNotFoundError as e:
            pass  # do something with
        except Exception as e:
            pass  # do something with

        time.sleep(1)
