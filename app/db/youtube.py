from munch import Munch
from youtube_dl import YoutubeDL
from youtube_dl.extractor.youtube import YoutubeTabIE

yt = YoutubeDL()
ex = YoutubeTabIE(downloader=yt)


control_id = 'UCQe4TP-50kUqtrs0iRhsg6Q'
custom_name = 'MrBillsTunes'


def yt_urls(id):
    def id_url(id):
        return 'https://www.youtube.com/channel/{}/videos'.format(id)

    def named_url(id):
        return 'https://www.youtube.com/c/{}/videos'.format(id)

    if(len(id) == len(control_id)):
        return [id_url(id), named_url(id)]
    else:
        return [named_url(id), id_url(id)]


def extract_urls(head, tail=None):
    if isinstance(head, list):
        return extract_urls(head.pop(0), head)

    try:
        return ex.extract(head)
    except Exception as e:
        if tail is None:
            raise

        if isinstance(tail, list) and len(tail) == 0:
            raise

        return extract_urls(tail.pop(0), tail)


def fetch_channel(id):
    urls = yt_urls(id)
    res = extract_urls(urls)
    return Munch(
        id=res.get('id', '_failed_id_'),
        title=res.get('title', '_failed_get_'),
        entries=map(Munch, res.get('entries', []))
    )



