import os
import errno
from munch import Munch

DEFAULT_BID = "0.001"
UPLOAD_COOLDOWN = int(os.environ.get('UPLOAD_COOLDOWN', 150))


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


def is_float(num, cast_to=str):
    try:
        s = float(num)
    except:
        return False

    return cast_to(s)


def is_docker():
    return os.environ.get("DOCKER", None) == str(1)


def langs():
    langs = [
        ["en", "English"],
        ["es", "Español"],
        ["fr", "Français"],
        ["de", "Deutsch"],
        ["ja", "日本語"],
        ["zh-Hans", "中文 (简体)"],
        ["af", "Afrikaans"],
        ["id", "Bahasa Indonesia"],
        ["ms", "Bahasa Melayu"],
        ["jv", "Basa Jawa"],
        ["ca", "Català"],
        ["da", "Dansk"],
        ["hr", "Hrvatski"],
        ["it", "Italiano"],
        ["nl", "Nederlands"],
        ["no", "Norsk (bokmål / riksmål)"],
        ["pl", "Polski"],
        ["pt", "Português"],
        ["pt-BR", "Português (Brasil)"],
        ["ro", "Română"],
        ["sk", "Slovenčina"],
        ["fi", "Suomi"],
        ["sv", "Svenska"],
        ["tl", "Tagalog"],
        ["vi", "Tiếng Việt"],
        ["tr", "Türkçe"],
        ["cs", "Česky"],
        ["ru", "Русский"],
        ["sr", "Српски"],
        ["uk", "Українська"],
        ["ur", "اردو"],
        ["ar", "العربية"],
        ["mr", "मराठी"],
        ["hi", "हिन्दी"],
        ["pa", "ਪੰਜਾਬੀ / पंजाबी / پنجابي"],
        ["gu", "ગુજરાતી"],
        ["kn", "ಕನ್ನಡ"],
        ["ml", "മലയാളം"],
        ["th", "ไทย / Phasa Thai"],
        ["zh-Hant", "中文 (繁體)"],
    ]

    return [
        dict(id=v[0], name=v[1]) for v in langs
    ]


def licenses():
    lics = [
        {
            "id": "cc4-by-sa",
            "license_title": "Creative Commons - Attribution-ShareAlike 4.0 International",
            "uri": "http://creativecommons.org/licenses/by-sa/4.0/"
        },
        {
            "id": "cc4-by-nd",
            "license_title": "Creative Commons - Attribution-NoDerivatives 4.0 International",
            "uri": "http://creativecommons.org/licenses/by-nd/4.0/"
        },
        {
            "id": "cc4-by",
            "license_title": "Creative Commons - Attribution 4.0 International",
            "uri": "http://creativecommons.org/licenses/by/4.0/"
        },

        {
            "id": "cc4-by-nc",
            "license_title": "Creative Commons - Attribution-NonCommercial 4.0 International",
            "uri": "http://creativecommons.org/licenses/by-nc/4.0/"
        },
        {
            "id": "cc4-by-nc-nd",
            "license_title": "Creative Commons - Attribution-NonCommercial-NoDerivatives 4.0 International",
            "uri": "http://creativecommons.org/licenses/by-nc-nd/4.0/"
        },
        {
            "id": "cc4-by-nc-sa",
            "license_title": "Creative Commons - Attribution-NonCommercial-ShareAlike 4.0 International",
            "uri": "http://creativecommons.org/licenses/by-nc-sa/4.0/"
        },

    ]

    return [
        Munch(
            id=l.id,
            name=l.license_title,
            url=l.uri,
        ) for l in [Munch(L) for L in lics]
    ]





