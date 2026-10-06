"""
音频转录模块 - 使用 OpenAI Whisper 进行语音转文字
支持中文、英文等多语言识别，输出带时间戳的逐句文本
"""

import json
import os
from pathlib import Path
from typing import Optional


def transcribe_audio(
    audio_path: str,
    output_dir: str,
    model_name: str = "base",
    language: Optional[str] = None,
) -> dict:
    """
    使用 Whisper 将音频转为带时间戳的文本。

    Args:
        audio_path: 音频文件路径（推荐 16kHz WAV）
        output_dir: 输出目录
        model_name: Whisper 模型名称 (tiny/base/small/medium/large)
        language: 语言代码，None 则自动检测

    Returns:
        dict: {
            "full_text": str,           # 完整文本
            "segments": list[dict],     # 带时间戳的分段
            "language": str,            # 检测到的语言
            "word_count": int,          # 字数统计
        }
    """
    import whisper

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[transcribe] 加载 Whisper 模型: {model_name}")
    model = whisper.load_model(model_name)

    print(f"[transcribe] 开始转录: {os.path.basename(audio_path)}")
    options = {"verbose": False}
    if language:
        options["language"] = language

    result = model.transcribe(audio_path, **options)

    # 整理分段数据
    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "id": seg["id"],
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip(),
        })

    full_text = result.get("text", "").strip()
    detected_lang = result.get("language", "unknown")

    # 字数统计（中文按字符，英文按单词）
    if detected_lang in ("zh", "ja", "ko"):
        word_count = len(full_text.replace(" ", ""))
    else:
        word_count = len(full_text.split())

    transcript_data = {
        "full_text": full_text,
        "segments": segments,
        "language": detected_lang,
        "word_count": word_count,
        "model": model_name,
        "segment_count": len(segments),
    }

    # 保存结果
    json_path = output_dir / "transcript.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(transcript_data, f, ensure_ascii=False, indent=2)

    # 保存 SRT 字幕文件
    srt_path = output_dir / "transcript.srt"
    _save_srt(segments, str(srt_path))

    # 保存纯文本
    txt_path = output_dir / "transcript.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"[transcribe] 转录完成: {detected_lang}, {len(segments)} 段, {word_count} 字")
    return transcript_data


def _save_srt(segments: list, output_path: str):
    """将分段数据保存为 SRT 字幕格式"""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _format_srt_time(seg["start"])
        end = _format_srt_time(seg["end"])
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(seg["text"])
        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _format_srt_time(seconds: float) -> str:
    """将秒数转换为 SRT 时间格式 HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def estimate_speech_rate(segments: list, language: str = "zh") -> dict:
    """
    根据转录结果估算语速。

    Returns:
        dict: {
            "chars_per_minute": float,   # 每分钟字符数（中文）
            "words_per_minute": float,   # 每分钟词数（英文）
            "avg_segment_duration": float,
            "pace_label": str,           # 慢速/正常/快速/极快
        }
    """
    if not segments:
        return {"chars_per_minute": 0, "words_per_minute": 0, "pace_label": "未知"}

    total_duration = segments[-1]["end"] - segments[0]["start"]
    if total_duration <= 0:
        return {"chars_per_minute": 0, "words_per_minute": 0, "pace_label": "未知"}

    all_text = "".join(seg["text"] for seg in segments)
    total_chars = len(all_text.replace(" ", ""))
    total_words = len(all_text.split())

    chars_per_min = total_chars / (total_duration / 60)
    words_per_min = total_words / (total_duration / 60)

    # 中文语速分级
    if language in ("zh", "ja", "ko"):
        if chars_per_min < 180:
            pace = "慢速"
        elif chars_per_min < 280:
            pace = "正常"
        elif chars_per_min < 380:
            pace = "快速"
        else:
            pace = "极快"
    else:
        if words_per_min < 120:
            pace = "慢速"
        elif words_per_min < 180:
            pace = "正常"
        elif words_per_min < 250:
            pace = "快速"
        else:
            pace = "极快"

    avg_seg_dur = sum(
        seg["end"] - seg["start"] for seg in segments
    ) / len(segments)

    return {
        "chars_per_minute": round(chars_per_min, 1),
        "words_per_minute": round(words_per_min, 1),
        "avg_segment_duration": round(avg_seg_dur, 2),
        "pace_label": pace,
    }
