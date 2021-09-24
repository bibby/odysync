import os
import redis

redis_client = redis.StrictRedis(
        host=os.environ.get('REDIS_HOST', 'localhost'),
        port=6379,
        db=0
    )


class Queue:
    def __init__(self, queue):
        self.queue = queue

    def enqueue(self, *args):
        return redis_client.rpush(self.queue, *args)

    def dequeue(self):
        return redis_client.lpop(self.queue)

    def wipe(self):
        while len(self):
            self.dequeue()

    def __len__(self):
        return redis_client.llen(self.queue)


INFO_QUEUE = "to_info"
DOWN_QUEUE = "to_download"
TRANSCODE_QUEUE = "to_transcode"
UP_QUEUE = "to_upload"
MSG_QUEUE = "to_msg"

CHANNEL = "channel"
VIDEO = "video"

infoQ = Queue(INFO_QUEUE)
downQ = Queue(DOWN_QUEUE)
transQ = Queue(TRANSCODE_QUEUE)
upQ = Queue(UP_QUEUE)
msgQ = Queue(MSG_QUEUE)


TMP_VOLUME = os.environ.get('TMP_VOLUME', '/tmp/odysync')
INFO_TMP = os.path.join(TMP_VOLUME, 'info')
DOWN_TMP = os.path.join(TMP_VOLUME, 'down')
TRANSCODE_TMP = os.path.join(TMP_VOLUME, 'transcode')

QMap = dict(
    info=infoQ,
    download=downQ,
    transcode=transQ,
    upload=upQ,
)