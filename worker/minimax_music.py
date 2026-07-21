"""Small server-side client for MiniMax Music original-song generation.

This module intentionally supports only text-to-music.  It does not accept
reference audio, voice IDs, cover feature IDs, or voice-cloning parameters.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


DEFAULT_STYLE = (
    "Mandarin male a cappella vocal, youthful bright tenor, clean airy tone, "
    "restrained emotion, gentle breathing, modern C-pop phrasing, intimate "
    "close-mic recording, completely original melody, no instrumental "
    "accompaniment, do not imitate or identify any real singer"
)


def available() -> bool:
    enabled = (
        os.getenv("KUN_MUSIC_ENABLED", "").strip().lower()
        in {"1", "true", "yes", "on"}
        or (PROJECT_ROOT / "data" / "music-enabled.flag").exists()
    )
    return enabled and bool(os.getenv("MINIMAX_API_KEY", "").strip())


def generate_original_song(theme: str, lyrics: str) -> dict:
    """Generate an original vocal track and return its temporary audio URL."""

    if not available():
        raise RuntimeError("MiniMax Music 尚未启用或 API Key 未配置")
    theme = " ".join(str(theme).split()).strip()
    lyrics = str(lyrics).strip()
    if not 2 <= len(theme) <= 160:
        raise ValueError("主题长度需要在 2–160 个字符之间")
    if not 10 <= len(lyrics) <= 800:
        raise ValueError("原创歌词长度需要在 10–800 个字符之间")

    api_base = os.getenv("MINIMAX_MUSIC_API_BASE", "https://api.minimax.io").rstrip("/")
    model = os.getenv("MINIMAX_MUSIC_MODEL", "music-3.0-free").strip()
    if model not in {"music-3.0", "music-3.0-free"}:
        raise RuntimeError("KUN Chat 原创清唱仅允许 music-3.0 或 music-3.0-free")
    prompt = f"{DEFAULT_STYLE}. Theme: {theme}"
    payload = {
        "model": model,
        "prompt": prompt,
        "lyrics": lyrics,
        "audio_setting": {
            "sample_rate": 44100,
            "bitrate": 256000,
            "format": "mp3",
        },
        "output_format": "url",
    }
    request = urllib.request.Request(
        f"{api_base}/v1/music_generation",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {os.getenv('MINIMAX_API_KEY', '').strip()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    timeout = max(30, int(os.getenv("MINIMAX_MUSIC_TIMEOUT_SECONDS", "240")))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"MiniMax Music HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"MiniMax Music 网络请求失败：{exc}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("MiniMax Music 返回了无法解析的结果") from exc

    base_resp = result.get("base_resp") or {}
    if base_resp.get("status_code") not in {None, 0}:
        raise RuntimeError(
            f"MiniMax Music 错误 {base_resp.get('status_code')}: "
            f"{base_resp.get('status_msg', 'unknown error')}"
        )
    audio_url = str((result.get("data") or {}).get("audio", "")).strip()
    if not audio_url.startswith(("https://", "http://")):
        raise RuntimeError("MiniMax Music 没有返回可播放的音频 URL")
    info = result.get("extra_info") or {}
    return {
        "audio_url": audio_url,
        "duration_ms": int(info.get("music_duration") or 0),
        "model": model,
        "expires_in_hours": 24,
        "disclosure": "AI 原创演唱，非蔡徐坤本人",
    }
