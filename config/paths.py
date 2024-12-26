from pathlib import Path

_ROOT = Path(__file__).parent.parent
APP_STATIC_FOLDER = _ROOT / "assets" / "static"
FONTS_DIR = _ROOT / "assets" / "fonts"
LOGS_DIR = _ROOT / "runtime" / "logs"
USER_CONTENT_DIR = _ROOT / "runtime" / "public" / "user_content"
_USER_CONTENT_OUT_DIR = USER_CONTENT_DIR / "out"
_USER_CONTENT_IN_DIR = USER_CONTENT_DIR / "in"


def ensure_user_content_tree() -> None:
    _USER_CONTENT_IN_DIR.mkdir(exist_ok=True, parents=True)
    _USER_CONTENT_OUT_DIR.mkdir(exist_ok=True, parents=True)


def ensure_user_upload_tree(user_id: str, upload_id: str) -> None:
    ensure_user_content_tree()
    (_USER_CONTENT_IN_DIR / user_id / upload_id).mkdir(exist_ok=True, parents=True)
    (_USER_CONTENT_OUT_DIR / user_id / upload_id).mkdir(exist_ok=True, parents=True)


def input_file_dest(user_id: str, upload_id: str, filename: str) -> Path:
    ensure_user_upload_tree(user_id, upload_id)
    return _USER_CONTENT_IN_DIR / user_id / upload_id / filename


def output_file_dest(user_id: str, upload_id: str, filename: str) -> Path:
    ensure_user_upload_tree(user_id, upload_id)
    return _USER_CONTENT_OUT_DIR / user_id / upload_id / filename


class FontPaths:
    DEFAULT = FONTS_DIR / "News Gothic Condensed Regular.ttf"
