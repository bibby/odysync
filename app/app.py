import os
from bunch import Bunch
from flask import Flask, jsonify, request, render_template, jsonify
from db.models import VideoState, Video, Channel, ChannelSite
from db.queue import infoQ, downQ, transQ, upQ
from db.shell import worker_status, worker_cmd
from youtube_dl import YoutubeDL
from youtube_dl.extractor.youtube import YoutubeTabIE as Info

app = Flask(__name__)


@app.after_request
def add_cors_headers(response):
    if request.referrer:
        r = request.referrer[:-1]
        response.headers.add('Access-Control-Allow-Origin', r)
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Headers', 'Cache-Control')
        response.headers.add('Access-Control-Allow-Headers', 'X-Requested-With')
        response.headers.add('Access-Control-Allow-Headers', 'Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
    return response


@app.route('/')
def index():
    return render_template('index.j2')

@app.route('/channel/youtube')
def add_youtube():
    channel_id = "RobbieBarnby"
    channel, created = Channel.get_or_create(id=channel_id, site=ChannelSite.YOUTUBE)

    downloader = YoutubeDL()
    info = Info(downloader=downloader)

    ex = info.extract(channel.url)
    #ex = Bunch(entries=[])

    for v in ex.get("entries"):
        v = Bunch(v)
        Video.get_or_create(
            id=v.id,
            channel=channel,
            defaults=dict(
                state=VideoState.NEW,
                title=v.title,
            )
        )

    queue_infos(channel)
    return jsonify(get_videos(channel))


@app.route('/set_channel', methods=['POST'])
def set_channel():
    channel = request.form['']


def get_videos(channel):
    vids = []
    for v in Video.select()\
            .where(Video.channel == channel):
        vids.append(v.serial())

    return dict(
        channel=channel.serial(),
        vids=vids,
    )


def queue_infos(channel):
    for v in Video.select()\
            .where(Video.channel == channel)\
            .where(Video.state == VideoState.NEW):
        infoQ.enqueue(v.id)
        v.state = VideoState.INFOING
        v.save()


@app.route('/workers')
def workers():
    return render_template('workers.j2', worker_status=worker_status())


@app.route('/worker/status', methods=['GET'])
def get_worker_status():
    return jsonify(worker_status())


@app.route('/worker/<worker>/<status>', methods=['GET'])
def set_worker_status(worker, status):
    return worker_cmd(worker, status)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('WEBPORT', 3000))
