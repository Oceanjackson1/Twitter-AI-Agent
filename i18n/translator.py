from i18n.en import STRINGS as EN
from i18n.zh import STRINGS as ZH

_LANGS = {
    "en": EN,
    "zh": ZH,
}


def get_text(key: str, lang: str = "zh", **kwargs) -> str:
    """Look up a translated string by key and language, with fallback to English."""
    strings = _LANGS.get(lang, EN)
    text = strings.get(key) or EN.get(key) or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text
