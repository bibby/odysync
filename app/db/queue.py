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

    def __len__(self):
        return redis_client.llen(self.queue)


INFO_QUEUE="to_info"
DOWN_QUEUE="to_download"
TRANSCODE_QUEUE="to_trans"
UP_QUEUE="to_upload"

infoQ = Queue(INFO_QUEUE)
downQ = Queue(DOWN_QUEUE)
transQ = Queue(TRANSCODE_QUEUE)
upQ = Queue(UP_QUEUE)
