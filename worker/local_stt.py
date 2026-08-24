"""Local speech-to-text for browser and phone recordings."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
for _env_name in (".env", ".env.local"):
    _env_file = PROJECT_ROOT / _env_name
    if _env_file.exists():
        load_dotenv(_env_file)


MATERIAL_ROOT = Path(
    os.getenv("KUN_MATERIAL_DIR", r"D:\OneDrive\LLMs\kun-material")
)
_MIGRATED_VENDOR_ROOT = Path(
    r"D:\LocalDevDeps\OneDriveMirror\LLMs\kun-material\tools\python"
)
VENDOR_ROOT = Path(
    os.getenv(
        "KUN_STT_VENDOR_ROOT",
        str(_MIGRATED_VENDOR_ROOT if _MIGRATED_VENDOR_ROOT.exists() else MATERIAL_ROOT / "tools" / "python"),
    )
)
MODEL_CACHE = Path(
    os.getenv("KUN_STT_MODEL_CACHE", str(MATERIAL_ROOT / "tools" / "models"))
)
MAX_AUDIO_BYTES = max(1, int(os.getenv("KUN_STT_MAX_AUDIO_MB", "12"))) * 1024 * 1024
MAX_AUDIO_SECONDS = max(5, int(os.getenv("KUN_STT_MAX_AUDIO_SECONDS", "45")))

_MODEL = None
_MODEL_LOCK = threading.RLock()
_DLL_HANDLES: list[object] = []

_DEFAULT_STT_PROMPT = (
    "普通话语音转写，使用简体中文并保留问句。"
    "可能提到的人名和称呼：邹雨芯、雨芯、邹大猩猩、蔡徐坤、坤坤、峰哥、老残、皓哥、清凉山人、爷爷、奶奶。"
)
_CONTEXT_CORRECTIONS = {
    "zouyuxin": {
        "周玉琴": "邹雨芯",
        "周雨欣": "邹雨芯",
        "周雨芯": "邹雨芯",
        "邹雨欣": "邹雨芯",
        "雨欣": "雨芯",
    },
    "qingliangshanren": {
        "清凉善人": "清凉山人",
        "清凉山仁": "清凉山人",
    },
}


def _valid_snapshot(path: Path) -> bool:
    """Reject interrupted model downloads before faster-whisper sees them."""
    return path.is_dir() and all(
        (path / name).exists()
        for name in ("config.json", "model.bin", "tokenizer.json")
    )


def _ffmpeg_path() -> Path:
    configured = os.getenv("KUN_STT_FFMPEG", "").strip()
    if configured:
        return Path(configured)
    candidates = sorted(
        (VENDOR_ROOT / "imageio_ffmpeg" / "binaries").glob("ffmpeg-*.exe")
    )
    if not candidates:
        raise RuntimeError("本地 FFmpeg 未安装，无法处理手机录音")
    return candidates[0]


def _model_snapshot() -> Path:
    configured = os.getenv("KUN_STT_MODEL_PATH", "").strip()
    if configured:
        path = Path(configured)
        if _valid_snapshot(path):
            return path
        raise RuntimeError("KUN_STT_MODEL_PATH 指向的模型不完整")
    variant = os.getenv("KUN_STT_MODEL_VARIANT", "small").strip().lower() or "small"
    model_dirs = {
        "small": MODEL_CACHE / "models--Systran--faster-whisper-small",
        "large-v3-turbo": (
            MODEL_CACHE / "models--mobiuslabsgmbh--faster-whisper-large-v3-turbo"
        ),
    }
    ordered = [model_dirs.get(variant), model_dirs["large-v3-turbo"]]
    for model_dir in ordered:
        if model_dir is None:
            continue
        snapshots = sorted(
            path
            for path in (model_dir / "snapshots").glob("*")
            if _valid_snapshot(path)
        )
        if snapshots:
            return snapshots[-1]
    raise RuntimeError("本地 Whisper 模型尚未下载")


def available() -> bool:
    try:
        return (
            VENDOR_ROOT.exists()
            and _ffmpeg_path().exists()
            and _model_snapshot().exists()
        )
    except Exception:
        return False


def _prepare_imports():
    vendor = str(VENDOR_ROOT)
    if vendor not in sys.path:
        sys.path.insert(0, vendor)
    for dll_dir in (
        VENDOR_ROOT / "nvidia" / "cublas" / "bin",
        VENDOR_ROOT / "nvidia" / "cudnn" / "bin",
        VENDOR_ROOT / "nvidia" / "cuda_nvrtc" / "bin",
    ):
        if not dll_dir.exists():
            continue
        os.environ["PATH"] = str(dll_dir) + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            _DLL_HANDLES.append(os.add_dll_directory(str(dll_dir)))
    from faster_whisper import WhisperModel

    return WhisperModel


def _model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    with _MODEL_LOCK:
        if _MODEL is not None:
            return _MODEL
        WhisperModel = _prepare_imports()
        device = os.getenv("KUN_STT_DEVICE", "cpu").strip().lower() or "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        kwargs = {"device": device, "compute_type": compute_type, "num_workers": 1}
        if device == "cpu":
            default_threads = max(2, min(os.cpu_count() or 4, 12))
            kwargs["cpu_threads"] = max(
                2, int(os.getenv("KUN_STT_CPU_THREADS", str(default_threads)))
            )
        _MODEL = WhisperModel(str(_model_snapshot()), **kwargs)
        return _MODEL


def warmup() -> None:
    """Load the configured Whisper model before the first microphone request."""
    _model()


def _normalize_text(text: str) -> str:
    text = re.sub(r"\s+([，。！？、；：])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def _context_hint(persona: str) -> str:
    persona = (persona or "").strip().lower()
    names = {
        "kunkun": "蔡徐坤（坤坤）",
        "fengge": "峰哥",
        "laocan": "老残",
        "qiuhao": "皓哥",
        "qingliangshanren": "清凉山人（爷爷）",
        "nainai": "奶奶",
        "zouyuxin": "邹雨芯（邹大猩猩）",
    }
    name = names.get(persona, "")
    return f"当前正在和{name}对话，请准确识别人名。" if name else ""


def _apply_context_corrections(text: str, persona: str) -> str:
    for mistaken, expected in _CONTEXT_CORRECTIONS.get(
        (persona or "").strip().lower(), {}
    ).items():
        text = text.replace(mistaken, expected)
    return text


def transcribe(
    audio: bytes,
    content_type: str = "application/octet-stream",
    persona: str = "",
) -> str:
    if not audio:
        raise ValueError("没有收到录音内容")
    if len(audio) > MAX_AUDIO_BYTES:
        raise ValueError(f"录音过大，请控制在 {MAX_AUDIO_SECONDS} 秒以内")
    if not (
        content_type.startswith("audio/")
        or content_type.startswith("video/")
        or content_type.startswith("application/octet-stream")
    ):
        raise ValueError("不支持的录音格式")

    with tempfile.TemporaryDirectory(prefix="kun-stt-") as temp_dir:
        temp = Path(temp_dir)
        source = temp / "recording.bin"
        wav = temp / "recording.wav"
        source.write_bytes(audio)
        result = subprocess.run(
            [
                str(_ffmpeg_path()),
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source),
                "-t",
                str(MAX_AUDIO_SECONDS),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(wav),
            ],
            capture_output=True,
            text=True,
            timeout=75,
            check=False,
        )
        if result.returncode != 0 or not wav.exists():
            detail = (result.stderr or "").strip()[-240:]
            raise ValueError(f"无法读取这段录音{('：' + detail) if detail else ''}")

        with _MODEL_LOCK:
            beam_size = max(1, int(os.getenv("KUN_STT_BEAM_SIZE", "5")))
            initial_prompt = os.getenv(
                "KUN_STT_INITIAL_PROMPT", _DEFAULT_STT_PROMPT
            ).strip()
            context_hint = _context_hint(persona)
            if context_hint:
                initial_prompt = f"{initial_prompt}{context_hint}"
            hotwords = os.getenv(
                "KUN_STT_HOTWORDS",
                "邹雨芯 雨芯 蔡徐坤 坤坤 峰哥 老残 皓哥 清凉山人 奶奶",
            ).strip()
            segments, _ = _model().transcribe(
                str(wav),
                language="zh",
                beam_size=beam_size,
                best_of=max(1, beam_size),
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 350},
                condition_on_previous_text=False,
                word_timestamps=False,
                initial_prompt=initial_prompt or None,
                hotwords=hotwords or None,
            )
            text = _normalize_text("".join(segment.text for segment in segments))
            text = _apply_context_corrections(text, persona)
    if not text:
        raise ValueError("没有识别到清晰语音，请靠近麦克风再试一次")
    return text
