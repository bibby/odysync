import os
import time
from db.util import mkdir_p
from db.queue import infoQ, INFO_TMP
from db.shell import shell
from db.models import Video, VideoState
from youtube_dl import YoutubeDL


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


def get_info(vid_id):
    params = dict(
        skip_download=True,
        writeinfojson=True,
        writethumbnail=True,
        nooverwrites=True,
        outtmpl=os.path.join(INFO_TMP, "%(id)s.%(ext)s"),
    )

    print(str(params))

    with YoutubeDL(params=params) as ytdl:
        ytdl.download([
            'https://www.youtube.com/watch?v=' + vid_id
        ])


def fix_webp(vid_id):
    for directory, dirnames, filenames in os.walk(INFO_TMP):
        for f in filenames:
            if f.endswith(".webp"):
                print("dwebp " + f)
                shell([
                    "dwebp",
                    os.path.join(directory, f),
                    '-o',
                    os.path.join(INFO_TMP, vid_id + '.png'),
                ])

                shell([
                    "rm",
                    os.path.join(directory, f),
                ])


if __name__ == '__main__':
    print("Info worker started")
    mkdir_p(INFO_TMP)
    while True:
        vid_id = infoQ.dequeue()

        if vid_id:
            vid_id = vid_id.decode()
            print(vid_id)

            vid = set_state(vid_id, VideoState.INFOING)
            if isinstance(vid_id, Video):
                get_info(vid_id)
                fix_webp(vid_id)
                set_state(vid, VideoState.INFO)

        time.sleep(1)

