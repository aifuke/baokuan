"""
视频下载与元数据提取模块
支持：抖音、快手、B站、YouTube、小红书等主流平台
"""

import json
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional


def get_ffmpeg_path() -> str:
    """获取 ffmpeg 可执行文件路径"""
    # 优先使用 imageio-ffmpeg 自带的二进制
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    # 回退到系统 PATH
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    raise FileNotFoundError("ffmpeg not found. Install via: pip install imageio-ffmpeg")


def download_video(
    url: str,
    output_dir: str,
    max_resolution: int = 720,
    cookies_file: Optional[str] = None,
) -> dict:
    """
    下载视频并提取元数据。

    Args:
        url: 视频 URL
        output_dir: 输出目录
        max_resolution: 最大分辨率（高度），默认 720p
        cookies_file: 可选的 cookies 文件路径

    Returns:
        dict: {
            "video_path": str,       # 下载的视频文件路径
            "metadata": dict,        # 视频元数据
            "thumbnail": str | None, # 缩略图路径
        }
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    video_template = str(output_dir / "video.%(ext)s")
    thumbnail_template = str(output_dir / "thumb.%(ext)s")

    # yt-dlp 命令构建
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f", f"bestvideo[height<={max_resolution}]+bestaudio/best[height<={max_resolution}]/best",
        "--merge-output-format", "mp4",
        "-o", video_template,
        "--write-thumbnail",
        "--convert-thumbnails", "jpg",
        "--write-info-json",
        "--no-warnings",
        "--quiet",
    ]

    if cookies_file and os.path.exists(cookies_file):
        cmd.extend(["--cookies", cookies_file])

    cmd.append(url)

    print(f"[download] 正在下载视频: {url}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        # 尝试不限制分辨率重新下载
        print("[download] 首次下载失败，尝试不限分辨率...")
        cmd_fallback = [
            "yt-dlp",
            "--no-playlist",
            "-f", "best",
            "--merge-output-format", "mp4",
            "-o", video_template,
            "--write-info-json",
            "--no-warnings",
        ]
        if cookies_file and os.path.exists(cookies_file):
            cmd_fallback.extend(["--cookies", cookies_file])
        cmd_fallback.append(url)
        result = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"视频下载失败:\n{result.stderr}")

    # 查找下载的视频文件
    video_files = list(output_dir.glob("video.*"))
    video_file = None
    for f in video_files:
        if f.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov", ".flv"):
            video_file = f
            break

    if not video_file:
        raise FileNotFoundError(f"未找到下载的视频文件，目录内容: {[f.name for f in output_dir.iterdir()]}")

    # 读取元数据
    info_json_files = list(output_dir.glob("*.info.json"))
    metadata = {}
    if info_json_files:
        with open(info_json_files[0], "r", encoding="utf-8") as f:
            metadata = json.load(f)

    # 提取关键元数据字段
    clean_metadata = _extract_key_metadata(metadata)

    # 查找缩略图
    thumb_files = list(output_dir.glob("thumb.*"))
    thumbnail = str(thumb_files[0]) if thumb_files else None

    print(f"[download] 下载完成: {video_file.name} ({clean_metadata.get('duration_str', 'unknown')})")

    return {
        "video_path": str(video_file),
        "metadata": clean_metadata,
        "raw_metadata": metadata,
        "thumbnail": thumbnail,
    }


def extract_audio(video_path: str, output_dir: str, sample_rate: int = 16000) -> str:
    """
    从视频中提取音频为 WAV 格式（适配 Whisper）。

    Args:
        video_path: 视频文件路径
        output_dir: 输出目录
        sample_rate: 采样率，Whisper 推荐 16000

    Returns:
        str: 音频文件路径
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = str(output_dir / "audio.wav")

    ffmpeg = get_ffmpeg_path()
    cmd = [
        ffmpeg,
        "-i", video_path,
        "-vn",                  # 不要视频
        "-acodec", "pcm_s16le", # 16-bit PCM
        "-ar", str(sample_rate),# 16kHz
        "-ac", "1",             # 单声道
        "-y",                   # 覆盖已有文件
        audio_path,
    ]

    print(f"[audio] 正在提取音频: {os.path.basename(video_path)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"音频提取失败:\n{result.stderr}")

    file_size = os.path.getsize(audio_path)
    print(f"[audio] 音频提取完成: {file_size / 1024 / 1024:.1f} MB")
    return audio_path


def extract_video_info_local(video_path: str) -> dict:
    """
    使用 ffprobe 或 ffmpeg 提取本地视频文件的详细信息。
    """
    ffmpeg = get_ffmpeg_path()
    ffprobe = ffmpeg.replace("ffmpeg", "ffprobe")

    # 尝试 ffprobe，如果不存在则用 ffmpeg -i 解析
    use_ffprobe = os.path.exists(ffprobe)

    if use_ffprobe:
        cmd = [
            ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return _parse_ffmpeg_info(video_path, ffmpeg)
        try:
            info = json.loads(result.stdout)
        except json.JSONDecodeError:
            return _parse_ffmpeg_info(video_path, ffmpeg)
    else:
        return _parse_ffmpeg_info(video_path, ffmpeg)

    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "Failed to parse ffprobe output"}

    # 提取关键信息
    summary = {
        "duration": float(info.get("format", {}).get("duration", 0)),
        "size_bytes": int(info.get("format", {}).get("size", 0)),
        "format": info.get("format", {}).get("format_name", "unknown"),
    }

    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video":
            summary["width"] = stream.get("width", 0)
            summary["height"] = stream.get("height", 0)
            try:
                rfr = stream.get("r_frame_rate", "0/1")
                if "/" in str(rfr):
                    num, den = rfr.split("/")
                    summary["fps"] = float(num) / float(den) if float(den) != 0 else 0
                else:
                    summary["fps"] = float(rfr)
            except (ValueError, ZeroDivisionError):
                summary["fps"] = 0
            summary["video_codec"] = stream.get("codec_name", "unknown")
        elif stream.get("codec_type") == "audio":
            summary["audio_codec"] = stream.get("codec_name", "unknown")
            summary["sample_rate"] = stream.get("sample_rate", "unknown")

    # 格式化时长
    dur = summary["duration"]
    minutes, seconds = divmod(int(dur), 60)
    hours, minutes = divmod(minutes, 60)
    summary["duration_str"] = f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"

    return summary


def _parse_ffmpeg_info(video_path: str, ffmpeg: str) -> dict:
    """当 ffprobe 不可用时，用 ffmpeg -i 解析视频信息"""
    import re

    cmd = [ffmpeg, "-i", video_path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    stderr = result.stderr

    summary = {"duration": 0, "width": 0, "height": 0, "fps": 0}

    # 解析 Duration
    dur_match = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.\d+)', stderr)
    if dur_match:
        h, m, s = float(dur_match.group(1)), float(dur_match.group(2)), float(dur_match.group(3))
        summary["duration"] = h * 3600 + m * 60 + s

    # 解析分辨率和帧率
    vid_match = re.search(r'Video:.*?(\d{2,5})x(\d{2,5}).*?(\d+(?:\.\d+)?)\s*fps', stderr)
    if vid_match:
        summary["width"] = int(vid_match.group(1))
        summary["height"] = int(vid_match.group(2))
        summary["fps"] = float(vid_match.group(3))

    # 格式化时长
    dur = summary["duration"]
    minutes, seconds = divmod(int(dur), 60)
    hours, minutes = divmod(minutes, 60)
    summary["duration_str"] = f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"

    return summary


def _extract_key_metadata(raw: dict) -> dict:
    """从 yt-dlp 原始元数据中提取关键字段"""
    keys_map = {
        "title": "title",
        "description": "description",
        "uploader": "uploader",
        "upload_date": "upload_date",
        "duration": "duration",
        "view_count": "view_count",
        "like_count": "like_count",
        "comment_count": "comment_count",
        "share_count": "repost_count",
        "tags": "tags",
        "categories": "categories",
        "platform": "extractor",
        "thumbnail": "thumbnail",
    }

    result = {}
    for target_key, source_key in keys_map.items():
        value = raw.get(source_key)
        if value is not None:
            result[target_key] = value

    # 格式化时长
    duration = result.get("duration")
    if duration:
        minutes, seconds = divmod(int(duration), 60)
        hours, minutes = divmod(minutes, 60)
        result["duration_str"] = f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"

    # 格式化日期
    date_str = result.get("upload_date")
    if date_str and len(date_str) == 8:
        result["upload_date_fmt"] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

    return result
