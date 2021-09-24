import os
import time
from db.util import mkdir_p
from db.queue import downQ, DOWN_TMP, transQ
from db.models import Video, VideoState
from youtube_dl import YoutubeDL


def download_video(vid_id):
    params = dict(
        nooverwrites=True,
        outtmpl=os.path.join(DOWN_TMP, "%(id)s.%(ext)s"),
    )

    print(str(params))

    with YoutubeDL(params=params) as ytdl:
        ytdl.download([
            'https://www.youtube.com/watch?v=' + vid_id
        ])


if __name__ == '__main__':
    print("Download worker started")
    force = False
    mkdir_p(DOWN_TMP)
    while True:
        vid_id = downQ.dequeue()

        if vid_id:
            vid_id = vid_id.decode()
            print(vid_id)

            vid = Video.set_state(vid_id, VideoState.DOWNLOADING)
            try:
                if isinstance(vid, Video) or force:
                    download_video(vid_id)
                    Video.set_state(vid, VideoState.DOWNLOADED)
                    transQ.enqueue(vid_id)
            except Exception as e:
                print(e)
                Video.set_state(vid_id, VideoState.DOWNLOAD_ERROR)

        time.sleep(1)
