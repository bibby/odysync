from db.queue import downQ
from db.shell import youtubedl



def get_info(channel_url):
    return youtubedl(
        skip_download=True,
        write_info_json=True,
        no_overwrites=True,

    )


# youtube-dl -- --write-info-json -no-overwrites -o "%(id)s.%(ext)s" --yes-playlist 'https://www.youtube.com/c/TPainDAILY/videos'
