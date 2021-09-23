import os
import subprocess
import json
import pathlib
import enum
import hashlib
from munch import Munch
from logger import log
from db.queue import infoQ, downQ, transQ, upQ
from db.util import kv, yn, action

DATA_VOLUME = os.environ.get("DATA_VOLUME", "./vol")
WALLET_PATH = os.environ.get(
    "WALLET_PATH",
    os.path.join(
        str(pathlib.Path.home()),
        ".local/share/lbry/lbryum/wallets/default_wallet"
    )
)


class Workers(enum.Enum):
    INFO = 'info'
    DOWNLOAD = 'download'
    TRANSCODE = 'transcode'
    UPLOAD = 'upload'
    LBRYNET = 'lbrynet'


def shell(cmd, json=True):
    try:
        if not isinstance(cmd, (list,)):
            cmd = cmd.split(" ")

        cmd = [c for c in cmd if c]
        log.debug(cmd)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        out, ret = proc.communicate()[0].decode(), proc.returncode
        log.info("ret: %s", ret)

        if json:
            try:
                out = json.loads(out)
            except:
                pass

        if ret == 0 and "ERROR" in out:
            ret = 18

        r = dict(ret=ret)

        # https://github.com/Supervisor/supervisor/issues/1223
        if ret == 3 and "supervisor" in cmd[0]:
            ret = 0

        if ret > 0:
            r['error'] = out.strip()
        else:
            r['message'] = out.strip()
    except Exception as e:
        r = dict(
            ret=-1,
            error=str(e)
        )

    log.info(r)
    return Munch(r)


def args(a):
    ret = []
    for k in a:
        ret.push("--" + k.replace('_', '-'))
        if a[k] is not True:
            ret.push(a[k])
    return ret


def supervisor(*args):
    cmd = ['/usr/bin/supervisorctl']
    cmd += args
    return shell(cmd, json=False)


def get_worker(worker):
    for w in (Workers):
        if isinstance(worker, Workers) and w == worker:
            return w
        if isinstance(worker, str) and w.value == worker:
            return w

    log.warn("no worker for value: %s", worker)
    raise ValueError


def worker_status(worker=None, include_lbry=False):
    if worker:
        worker = get_worker(worker).value

    res = supervisor("status", worker)
    if not res:
        return Munch(error="no response")

    if "error" in res:
        return res

    log.debug("? worker_status: worker? %s", worker)
    log.debug("? worker_status: worker is Workers.LBRYNET? %s", worker is Workers.LBRYNET)

    if worker == Workers.LBRYNET.value:
        include_lbry = True

    log.debug(res)
    lines = res.message.split('\n')
    ret = []
    for line in lines:
        if not line.strip():
            continue
        parts = [t.strip() for t
                 in line.split('  ')
                 if t.strip()]

        log.info("? worker_status: parts[0]? %s", parts[0])
        log.info("? worker_status: Workers.LBRYNET.value? %s", Workers.LBRYNET.value)

        if not include_lbry and parts[0] == Workers.LBRYNET.value:
            continue

        ret.append(Munch(
            worker=parts[0],
            status=parts[1],
            info=parts[2],
            queue=worker_queue_size(parts[0]),
            sort=worker_queue_sort(parts[0]),
            actions=[
                action(
                    "Start",
                    "/worker/{}/start".format(parts[0]),
                    style="success",
                ),
                action(
                    "Stop",
                    "/worker/{}/stop".format(parts[0]),
                    style="error",
                ),
            ]
        ))

    log.debug("? worker_status: include_lbry? %s", include_lbry)
    log.debug("? worker_status: worker? %s", worker)
    log.debug("? worker_status: len(ret)? %s", len(ret))

    if worker and len(ret):
        return Munch(message=ret[0])

    return Munch(
        message=sorted(ret, key=lambda r: r.sort),
        ret=0
    )


def worker_cmd(worker, cmd):
    worker = get_worker(worker)
    return supervisor(cmd, worker.value)


def worker_queue_size(worker):
    worker = get_worker(worker)
    if worker == Workers.DOWNLOAD:
        return len(downQ)
    if worker == Workers.UPLOAD:
        return len(upQ)
    if worker == Workers.TRANSCODE:
        return len(transQ)
    if worker == Workers.INFO:
        return len(infoQ)
    return '-'


def worker_queue_sort(worker):
    worker = get_worker(worker)
    if worker == Workers.DOWNLOAD:
        return 2
    if worker == Workers.UPLOAD:
        return 4
    if worker == Workers.TRANSCODE:
        return 3
    if worker == Workers.INFO:
        return 1
    return 9


def lbry_setup_steps():
    return [
        kv(
            "Valid Wallet",
            lbry_wallet_check(),
            actions=[
                action(
                    "Edit",
                    "/wallet/edit",
                    xhr=False,
                )
            ]
        ),
        kv(
            "lbrynet running",
            lbrynet_running(),
            actions=[
                action(
                    "Start",
                    "/worker/lbrynet/start",
                    style="success",
                ),
                action(
                    "Stop",
                    "/worker/lbrynet/stop",
                    style="error",
                ),
            ]
        ),
        kv(
            "Channel(s) Indexed",
            lbry_channel_check(),
            actions=[
                action(
                    "Index",
                    "/lbry/index",
                    xhr=False
                )
            ]
        ),
    ]


def lbry_wallet_check():
    log.info('wallet_path: %s', WALLET_PATH)

    if not os.path.isfile(WALLET_PATH):
        log.warn("no wallet file")
        return False

    try:
        with open(WALLET_PATH, 'r') as w:
            wallet = json.loads(w.read())
            k = "accounts"
            if k not in wallet:
                log.warn("%s not in wallet file", k)
                return False

            if not isinstance(wallet.get(k), list):
                log.warn("%s in wallet not a list", k)
                return False

            return any([
                "private_key" in a
                for a in wallet.get(k)
            ])
    except Exception as e:
        log.exception(e)
        return False


def lbry_channel_check():
    return True


def lbrynet_running():
    status = worker_status(Workers.LBRYNET)
    if not status:
        log.warn("status unknown for worker: %s", Workers.LBRYNET)
        return False

    if "error" in status:
        log.warning(status.error)
        return False

    log.info("!@ type status: %s", type(status.message))

    return status.message.status == 'RUNNING'


def open_wallet(sanitary=True):
    if not os.path.isfile(WALLET_PATH):
        return ''
    with open(WALLET_PATH, 'r') as w:
        wallet = w.read()
        try:
            wallet = json.loads(wallet)
            if sanitary:
                wallet = sanitize_wallet(wallet)
        except:
            pass

        return wallet


def sanitize_string(v):
    hashed = hashlib.sha256(v.encode())
    return '--Hashed by odysync--(sha256:{})'.format(hashed.hexdigest())


def sanitize_wallet(v, k=None):
    if isinstance(v, dict):
        for k, V in v.items():
            v[k] = sanitize_wallet(V, k=k)
    if isinstance(v, list):
        v = list(map(sanitize_wallet, v))
    if isinstance(v, str):
        if k and k in ['private_key', 'seed']:
            return sanitize_string(v)
        if "PRIVATE KEY" in v:
            return sanitize_string(v)

    return v



