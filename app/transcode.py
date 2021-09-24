import time
import os
from db.util import mkdir_p
from db.queue import transQ, DOWN_TMP, TRANSCODE_TMP, upQ
from db.models import Video, VideoState
from db.shell import shell


def transcode_video(input_file, out_file, cleanup=True):
    input_file = os.path.join(DOWN_TMP, input_file)
    out_file = os.path.join(TRANSCODE_TMP, out_file)

    try:
        cmd = [
            'ffmpeg',
            '-i',
            input_file,
            '-c:v',
            'libx264',
            '-crf',
            '21',
            '-preset',
            'faster',
            '-pix_fmt',
            'yuv420p',
            '-maxrate',
            '5000K',
            '-bufsize',
            '5000K',
            '-vf',
            "scale=if(gte(iw\\,ih)\\,min(1920\\,iw)\\,-2):if(lt(iw\\,ih)\\,min(1920\\,ih)\\,-2)",
            '-movflags',
            '+faststart',
            '-c:a',
            'aac',
            '-b:a',
            '160k',
            '-y',
            out_file
        ]

        print(" ".join(cmd))
        print("TRANSCODING")
        res = shell(cmd)
        print("TRANSCODE DONE")

        if cleanup:
            try:
                os.unlink(input_file)
            except Exception as e:
                pass

        return res
    except Exception as e:
        return False


def find_file(vid_id):
    for ext in ['mp4', 'webm', 'mkv', 'avi', 'mpeg']:
        vid_file = os.path.join(DOWN_TMP, vid_id + "." + ext)
        if os.path.isfile(vid_file):
            return vid_file

    raise FileNotFoundError(vid_id)


if __name__ == '__main__':
    print("Transcode worker started")
    force = False
    cleanup = False

    mkdir_p(TRANSCODE_TMP)

    while True:
        vid_id = transQ.dequeue()

        if vid_id:
            print(vid_id)
            vid_id = vid_id.decode()
            vid_file = find_file(vid_id)

            vid = Video.set_state(vid_id, VideoState.TRANSCODING)
            new_vid = vid_id + ".mp4"

            try:
                if isinstance(vid, Video) or force:
                    ret = transcode_video(vid_file, new_vid, cleanup=cleanup)
                    for l in ret.get("error", "").split("\n"):
                        print(l)
                    Video.set_state(vid, VideoState.TRANSCODED)
                    upQ.enqueue(vid_id)
            except Exception as e:
                print(e)
                Video.set_state(vid_id, VideoState.TRANSCODE_ERROR)

        time.sleep(1)
