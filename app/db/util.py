import os
import errno


def kv(k, v, **kwargs):
    return dict(
        key=k,
        value=yn(v),
        **kwargs
    )


def yn(v):
    if v:
        return "Yes"
    return "No"


def action(text, uri, style=None, xhr=True):
    return dict(
        text=text,
        uri=uri,
        style=style,
        xhr=xhr,
    )


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise