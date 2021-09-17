import os
import subprocess
import json
import enum

DATA_VOLUME = os.environ.get("DATA_VOLUME", "./vol")


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
        print(cmd)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        out = proc.stdout.read().decode()

        if json:
            return json.parse(out)

        return out
    except Exception as e:
        return False


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
        if w.value == worker:
            return w
    raise ValueError


def worker_status(worker=None):
    if worker:
        worker = get_worker()

    res = supervisor("status", worker)
    if not res:
        return

    print(res)
    lines = res.split('\n')
    ret = []
    for line in lines:
        if not line.strip():
            continue
        parts = [t.strip() for t in line.split('  ') if t.strip()]
        ret.append(dict(
            worker=parts[0],
            status=parts[1],
            info=parts[2],
        ))

    return ret


def worker_cmd(worker, cmd):
    worker = get_worker(worker)
    return supervisor(cmd, worker.value)
