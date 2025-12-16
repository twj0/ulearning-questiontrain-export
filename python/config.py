"""
Configuration management - load settings from environment variables
"""

import json
import os
import re
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration"""
    authorization: str
    user_id: int
    qt_id: int
    oc_id: int
    qt_type: int = 1
    base_url: str = "https://lms.dgut.edu.cn/utestapi"
    output_dir: str = "output"

    @classmethod
    def load(
        cls,
        env_file: str = ".env",
        cookie_file: str | None = None,
        practice_url: str | None = None,
    ) -> "Config":
        """Load configuration from multiple sources.

        Precedence (high -> low):
          1) cookie file (cookie.json / cookie.jsonc)
          2) .env
          3) practice URL (only provides QT_ID/OC_ID/QT_TYPE)
        """

        env_path = Path(env_file)
        if env_path.exists():
            load_dotenv(env_path)

        cookie_file = cookie_file or os.getenv("COOKIE_FILE")
        practice_url = practice_url or os.getenv("PRACTICE_URL")

        if not cookie_file:
            # Prefer real cookie.json; allow cookie.jsonc as demo with comments.
            if Path("cookie.json").exists():
                cookie_file = "cookie.json"
            elif Path("cookie.jsonc").exists():
                cookie_file = "cookie.jsonc"

        url_values: dict[str, str] = {}
        if practice_url:
            url_values = _parse_practice_url(practice_url)

        env_values: dict[str, str] = {
            "AUTHORIZATION": os.getenv("AUTHORIZATION") or "",
            "USER_ID": os.getenv("USER_ID") or "",
            "QT_ID": os.getenv("QT_ID") or url_values.get("QT_ID", ""),
            "OC_ID": os.getenv("OC_ID") or url_values.get("OC_ID", ""),
            "QT_TYPE": os.getenv("QT_TYPE") or url_values.get("QT_TYPE", "1"),
            "BASE_URL": os.getenv("BASE_URL") or "https://lms.dgut.edu.cn/utestapi",
            "OUTPUT_DIR": os.getenv("OUTPUT_DIR") or "output",
        }

        cookie_values: dict[str, str] = {}
        if cookie_file:
            cookie_path = Path(cookie_file)
            if cookie_path.exists():
                cookie_values = _extract_from_cookie_file(cookie_path)

        # cookie overrides env
        merged = {**env_values, **{k: v for k, v in cookie_values.items() if v}}

        authorization = merged.get("AUTHORIZATION")
        if not authorization:
            raise ValueError("AUTHORIZATION is required (from cookie or .env)")

        user_id = merged.get("USER_ID")
        if not user_id:
            raise ValueError("USER_ID is required (from cookie or .env)")

        qt_id = merged.get("QT_ID")
        if not qt_id:
            raise ValueError("QT_ID is required (from practice URL, cookie or .env)")

        oc_id = merged.get("OC_ID")
        if not oc_id:
            raise ValueError("OC_ID is required (from practice URL, cookie or .env)")

        return cls(
            authorization=authorization,
            user_id=int(user_id),
            qt_id=int(qt_id),
            oc_id=int(oc_id),
            qt_type=int(merged.get("QT_TYPE", "1")),
            base_url=merged.get("BASE_URL", "https://lms.dgut.edu.cn/utestapi"),
            output_dir=merged.get("OUTPUT_DIR", "output"),
        )


def _strip_jsonc(text: str) -> str:
    # Remove /* ... */ and // ... comments.
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    text = re.sub(r"(^|\s)//.*$", r"\1", text, flags=re.MULTILINE)
    return text


def _read_cookie_file(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(_strip_jsonc(raw))
    if not isinstance(data, list):
        raise ValueError("Cookie file must be a JSON array")
    return data


def _extract_from_cookie_file(path: Path) -> dict[str, str]:
    cookies = _read_cookie_file(path)
    cookie_map: dict[str, str] = {}
    for c in cookies:
        name = str(c.get("name", ""))
        value = str(c.get("value", ""))
        if name:
            cookie_map[name] = value

    authorization = cookie_map.get("AUTHORIZATION") or cookie_map.get("token") or ""

    user_id = ""
    userinfo_raw = cookie_map.get("USERINFO") or cookie_map.get("USER_INFO") or ""
    if userinfo_raw:
        # USERINFO sometimes is URL-encoded JSON
        decoded = urllib.parse.unquote(userinfo_raw)
        try:
            userinfo = json.loads(decoded)
            if isinstance(userinfo, dict) and "userId" in userinfo:
                user_id = str(userinfo["userId"])
        except Exception:
            pass

    # Cookie file cannot provide QT_ID/OC_ID/QT_TYPE reliably, leave empty.
    return {
        "AUTHORIZATION": authorization,
        "USER_ID": user_id,
    }


def _parse_practice_url(url: str) -> dict[str, str]:
    # Example:
    # https://lms.dgut.edu.cn/utest/index.html?v=...#/questionTrain/practice/2674/134202/1
    m = re.search(r"#/questionTrain/practice/(\d+)/(\d+)/(\d+)", url)
    if not m:
        return {}
    return {"QT_ID": m.group(1), "OC_ID": m.group(2), "QT_TYPE": m.group(3)}
