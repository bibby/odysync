import os
import time
from db.util import mkdir_p
from db.queue import infoQ, INFO_TMP, downQ
from db.shell import shell
from db.models import Video, VideoState
from youtube_dl import YoutubeDL


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
    force = True
    mkdir_p(INFO_TMP)

    while True:
        vid_id = infoQ.dequeue()

        if vid_id:
            vid_id = vid_id.decode()
            print(vid_id)

            vid = Video.set_state(vid_id, VideoState.INFOING)
            if isinstance(vid_id, Video) or force:
                get_info(vid_id)
                fix_webp(vid_id)
                Video.set_state(vid, VideoState.INFO)
                downQ.enqueue(vid_id)

        time.sleep(1)
