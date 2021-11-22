import os
import json
import math
from munch import Munch, munchify
from flask import Flask, jsonify, request, render_template, jsonify, redirect
from db.models import VideoState, Video, Channel, ChannelSite, Config
from db.queue import infoQ, downQ, transQ, upQ, CHANNEL, VIDEO, QMap
from db.shell import worker_status, worker_cmd, lbry_setup_steps, open_wallet, WALLET_PATH
from db.util import langs, licenses, DEFAULT_BID, mkdir_p
from youtube_dl import YoutubeDL
from youtube_dl.extractor.youtube import YoutubeTabIE as Info
from logger import log
from db.youtube import fetch_channel
from pybry.lbryd_api import LbrydApi
from peewee import Asc, Desc

import time

app = Flask(__name__)
lbry = LbrydApi()


def now():
    return time.strftime('%H:%M:%S %Z')


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
    tpl_params = Munch(
        channels=get_channels(),
        now=now(),
        intro=False,
        **get_vids(1),
    )

    conf = Config.load()
    if "intro" not in conf or conf.intro != 'True':
        tpl_params.intro = True
        Config.set("intro", True)

    return render_template('index.j2', **tpl_params)


@app.route('/videos/<int:page>/<sort_field>/<sort_dir>')
def vids(page, sort_field, sort_dir):

    tpl_params = dict(
        now=now(),
        **get_vids(page, sort_field, sort_dir),
    )
    return render_template('videos.j2', **tpl_params)


def get_vids(page, sort_field=None, sort_dir=None):
    vids, count, page, pages = get_videos(page, sort_field, sort_dir)
    return dict(
        videos=vids,
        vid_pages=pages,
        vid_count=count,
        vid_page=page,
    )


@app.route('/wallet/edit', methods=["GET", "POST"])
def wallet_edit():
    error = None
    if request.method == 'POST':
        wallet_json = request.form['wallet']
        try:
            wallet_json = json.loads(wallet_json)
            if "accounts" not in wallet_json:
                error = "JSON has no accounts"

            wallet_base = os.path.dirname(WALLET_PATH)
            if not os.path.isdir(wallet_base):
                mkdir_p(wallet_base)
            with open(WALLET_PATH, 'w') as w:
                w.write(json.dumps(wallet_json, indent=2))
        except json.decoder.JSONDecodeError:
            error = "Not valid json"
        except Exception as e:
            error = e

    wallet = open_wallet()
    has_wallet = False
    if wallet:
        has_wallet = True
        try:
            wallet = json.dumps(wallet, indent=2)
        except:
            pass

    tpl_params = dict(
        exists=has_wallet,
        wallet_path=WALLET_PATH,
        wallet_json=wallet,
        error=error
    )

    return render_template('wallet.j2', **tpl_params)


@app.route('/workers')
def workers():
    status = worker_status()
    log.debug("worker status type = %s", type(status))

    tpl_params = dict(now=now())
    if "error" in status:
        tpl_params['error'] = status.error
    if "message" in status:
        tpl_params['worker_status'] = status.message

    return render_template('workers.j2', **tpl_params)


@app.route('/lbry_setup')
def lbry_steps():
    tpl_params = dict(
        lbry_setup_steps=lbry_setup_steps(Channel.for_site(ChannelSite.LBRY)),
        now=now(),
    )

    return render_template('lbry_setup.j2', **tpl_params)


@app.route('/channel/add', methods=["GET", "POST"])
def channel_add():
    tpl_params = dict()
    err = None
    msg = None
    if request.method == "POST":
        try:
            chan_id = request.form['channel_id'].strip()
            res = fetch_channel(chan_id)
            channel, created = Channel.get_or_create(
                id=chan_id,
                defaults=dict(
                    name=str(res.title).strip('- Videos'),
                    site=ChannelSite.YOUTUBE,
                )
            )
            video_count = 0
            for vid in res.entries:
                _vid, _created = Video.get_or_create(
                    id=vid.id,
                    channel=channel,
                    defaults=dict(
                        title=vid.title,
                        state=VideoState.NEW,
                    )
                )
                video_count += 1

            msg = "Imported {} videos from {}".format(video_count, channel)

        except Exception as e:
            err = str(e)

        tpl_params.update(dict(
            error=err,
            message=msg
        ))

    return render_template('channel_add.j2', **tpl_params)


def get_channels():
    chans = []
    for c in Channel.select():
        chans.append(c.serial(actions=True))

    return chans


def get_videos(page=None, sort_field=None, sort_dir=None):
    vids = []
    page = int(page or 1)
    per_page = 100
    count = Video.select().count()
    pages = math.ceil(count / per_page)
    page = min(page, pages)
    page = max(1, page)
    sort_field, joined = valid_sort_field(sort_field)
    sort_dir = valid_sort_dir(sort_dir, sort_field)

    q = Video.select()
    if joined:
        q = q.join(Channel)

    q = q.order_by(sort_dir)
    q = q.limit(per_page).offset(per_page * (page - 1))

    for v in list(q):
        vids.append(v.serial(actions=True))

    return vids, count, page, pages


def valid_sort_field(f):
    natural = [
        'id',
        'title',
        'state'
    ]
    join = False

    if f in natural:
        return getattr(Video, f), join

    joined = dict(
        channel=Channel.name,
        site=Channel.site
    )

    if f in joined:
        join = True
        return joined[f], join

    log.warn('invalid sort field: %s', f)
    return Video.id, False


def valid_sort_dir(d, f):
    if d == 'desc':
        return Desc(f)
    return Asc(f)


def queue_infos(channel):
    for v in Video.select()\
            .where(Video.channel == channel)\
            .where(Video.state == VideoState.NEW):
        infoQ.enqueue(v.id)
        v.state = VideoState.INFOING
        v.save()


@app.route('/worker/status', methods=['GET'])
def get_worker_status():
    return jsonify(worker_status())


@app.route('/worker/<worker>/<status>', methods=['GET'])
def set_worker_status(worker, status):
    if status == 'wipe':
        return worker_wipe(worker)
    return worker_cmd(worker, status)


def worker_wipe(worker):
    try:
        QMap.get(worker).wipe()
    except:
        pass

    return Munch(
        message="wiped " + worker,
        ret=0
    )

@app.route('/lbry/index', methods=["GET"])
def lbry_channel_index():
    res = None
    try:
        res, resp = lbry.channel_list()
    except Exception as e:
        log.info(res)
        log.exception(e)
        return redirect('/')

    channels = dict()
    for chan in res.get("items"):
        channel, created = Channel.get_or_create(
            id=chan.get("claim_id"),
            defaults=dict(
                name=chan.get("name"),
                site=ChannelSite.LBRY,
                address=chan.get("address"),
            )
        )

        channels[channel.id] = channel

    video_count = 0
    for vid in lbry_get_videos():
        vid = munchify(vid)
        _vid, _created = Video.get_or_create(
            id=vid.claim_id,
            channel=channels[vid.signing_channel.claim_id],
            defaults=dict(
                title=vid.value.title,
                state=VideoState.UPLOADED,
            )
        )
        video_count += 1

        msg = "Imported {} videos from {}".format(video_count, channel)

    return redirect('/')


def lbry_get_videos(page=1, recursed=None):
    res, resp = lbry.stream_list(page=page, page_size=20)
    if recursed:
        return res.get("items")

    accum = res.get("items")
    page = res.get("page")
    total = res.get("total_pages")
    if page < total:
        for p in range(page, total):
            accum += lbry_get_videos(p + 1, recursed=True)
    return accum


@app.route('/channel/<chan>/delete', methods=["GET"])
def channel_delete(chan):
    try:
        channel = Channel.get(Channel.id == chan)
        channel.delete_instance(recursive=True)
    except Exception as e:
        raise

    return redirect('/')


@app.route('/channel/<chan_id>/match', methods=["GET"])
def channel_match(chan_id):
    try:
        channel = Channel.get(Channel.id == chan_id)
        matches = channel.match_others()
        tpl_params = dict(
            channel=channel.serial(),
            chan_id = chan_id,
            **matches,
        )
        return render_template("match_result.j2", **tpl_params)
    except Exception as e:
        raise

    return redirect('/')


@app.route('/channel/<chan_id>/unmatch/sync', methods=["GET"])
def channel_unmatch_sync(chan_id):
    channel = Channel.get(Channel.id == chan_id)
    matches = channel.match_others()

    for v in list(reversed(matches.solo)):
        infoQ.enqueue(v.id)

    return redirect('/')


@app.route('/sync/config', methods=['GET', 'POST'])
def sync_config():

    error = None
    message = None
    if request.method == 'POST':
        try:
            Config.save_sync_settings(request.form)
            message = "Saved settings"
        except Exception as e:
            error = str(e)

    conf = Config.load()

    def serial_site(site):
        return list(map(
           Channel.serial_map,
           Channel.for_site(site),
       ))

    settings = Munch(
        language=None,
        licence=None,
        tags=None,
        bid=DEFAULT_BID,
    )

    for k in settings.keys():
        if k in conf:
            settings[k] = conf[k]

    tpl_params = dict(
        error=error,
        message=message,
        yt_channels=serial_site(ChannelSite.YOUTUBE),
        lb_channels=serial_site(ChannelSite.LBRY),
        licenses=licenses(),
        languages=langs(),
        now=now(),
        default_bid=DEFAULT_BID,
        **{
            k: v or "" for k, v in settings.items()
        },
    )

    return render_template('sync.j2', **tpl_params)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('WEBPORT', 3000))
