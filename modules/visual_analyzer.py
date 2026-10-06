"""
视觉分析模块 - 关键帧提取、场景切换检测、画面特征分析
"""

import json
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional


def get_ffmpeg_path() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return shutil.which("ffmpeg") or "ffmpeg"


def extract_keyframes(
    video_path: str,
    output_dir: str,
    threshold: float = 0.3,
    max_frames: int = 30,
) -> list[dict]:
    """
    基于场景切换检测提取关键帧。

    Args:
        video_path: 视频文件路径
        output_dir: 输出目录
        threshold: 场景切换阈值（0-1），越小越敏感
        max_frames: 最大提取帧数

    Returns:
        list[dict]: 每个元素 {"timestamp": float, "frame_path": str, "scene_index": int}
    """
    output_dir = Path(output_dir)
    frames_dir = output_dir / "keyframes"
    frames_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg = get_ffmpeg_path()

    # 使用 ffmpeg scene detection 滤镜
    cmd = [
        ffmpeg,
        "-i", video_path,
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-vsync", "vfr",
        "-frames:v", str(max_frames),
        "-q:v", "2",
        "-y",
        str(frames_dir / "frame_%04d.jpg"),
    ]

    print(f"[visual] 正在提取关键帧 (threshold={threshold})...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    # 从 stderr 中解析 showinfo 的时间戳
    timestamps = []
    for line in result.stderr.split("\n"):
        if "showinfo" in line and "pts_time:" in line:
            try:
                pts_part = line.split("pts_time:")[1]
                ts = float(pts_part.split()[0])
                timestamps.append(ts)
            except (IndexError, ValueError):
                continue

    # 匹配生成的帧文件
    frame_files = sorted(frames_dir.glob("frame_*.jpg"))
    keyframes = []
    for i, frame_file in enumerate(frame_files):
        ts = timestamps[i] if i < len(timestamps) else 0.0
        keyframes.append({
            "timestamp": round(ts, 2),
            "frame_path": str(frame_file),
            "scene_index": i,
        })

    # 如果 scene detection 没提取到足够帧，按均匀间隔补充
    if len(keyframes) < 5:
        print("[visual] 场景切换帧不足，补充均匀采样帧...")
        supplementary = _extract_uniform_frames(video_path, str(frames_dir), count=10)
        existing_ts = {kf["timestamp"] for kf in keyframes}
        for sf in supplementary:
            if sf["timestamp"] not in existing_ts:
                keyframes.append(sf)
        keyframes.sort(key=lambda x: x["timestamp"])

    print(f"[visual] 关键帧提取完成: {len(keyframes)} 帧")

    # 保存元数据
    meta_path = output_dir / "keyframes_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(keyframes, f, ensure_ascii=False, indent=2)

    return keyframes


def _extract_uniform_frames(
    video_path: str,
    output_dir: str,
    count: int = 10,
) -> list[dict]:
    """均匀间隔提取帧作为补充"""
    ffmpeg = get_ffmpeg_path()

    # 先获取视频时长
    probe_cmd = [
        ffmpeg, "-i", video_path,
        "-hide_banner",
    ]
    probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
    duration = 0
    for line in probe_result.stderr.split("\n"):
        if "Duration:" in line:
            try:
                time_str = line.split("Duration:")[1].split(",")[0].strip()
                parts = time_str.split(":")
                duration = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            except (IndexError, ValueError):
                pass
            break

    if duration <= 0:
        return []

    interval = duration / (count + 1)
    frames = []

    for i in range(1, count + 1):
        ts = interval * i
        out_path = os.path.join(output_dir, f"uniform_{i:04d}.jpg")
        cmd = [
            ffmpeg,
            "-ss", str(ts),
            "-i", video_path,
            "-frames:v", "1",
            "-q:v", "2",
            "-y",
            out_path,
        ]
        subprocess.run(cmd, capture_output=True, timeout=10)
        if os.path.exists(out_path):
            frames.append({
                "timestamp": round(ts, 2),
                "frame_path": out_path,
                "scene_index": -1,  # 标记为补充帧
            })

    return frames


def analyze_scene_changes(keyframes: list, total_duration: float) -> dict:
    """
    分析场景切换节奏。

    Returns:
        dict: {
            "total_scenes": int,
            "avg_scene_duration": float,
            "cut_frequency": float,      # 每分钟切换次数
            "pace_label": str,           # 节奏标签
            "fastest_cut": float,        # 最快切换间隔
            "slowest_cut": float,        # 最慢切换间隔
        }
    """
    if len(keyframes) < 2 or total_duration <= 0:
        return {
            "total_scenes": len(keyframes),
            "avg_scene_duration": total_duration,
            "cut_frequency": 0,
            "pace_label": "未知",
        }

    timestamps = sorted(kf["timestamp"] for kf in keyframes)
    intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
    intervals = [iv for iv in intervals if iv > 0]

    if not intervals:
        return {
            "total_scenes": len(keyframes),
            "avg_scene_duration": total_duration,
            "cut_frequency": 0,
            "pace_label": "静态",
        }

    avg_interval = sum(intervals) / len(intervals)
    cut_freq = len(keyframes) / (total_duration / 60)

    # 剪辑节奏分级
    if cut_freq < 5:
        pace = "慢节奏（长镜头为主）"
    elif cut_freq < 15:
        pace = "中等节奏"
    elif cut_freq < 30:
        pace = "快节奏（频繁切换）"
    else:
        pace = "极快节奏（闪切风格）"

    return {
        "total_scenes": len(keyframes),
        "avg_scene_duration": round(avg_interval, 2),
        "cut_frequency": round(cut_freq, 1),
        "pace_label": pace,
        "fastest_cut": round(min(intervals), 2),
        "slowest_cut": round(max(intervals), 2),
    }


def analyze_frame_visual_features(keyframes: list) -> dict:
    """
    分析关键帧的视觉特征（亮度、色彩饱和度、构图等）。
    使用 OpenCV 进行基础图像分析。
    """
    import cv2
    import numpy as np

    if not keyframes:
        return {}

    brightness_values = []
    saturation_values = []
    resolutions = []

    for kf in keyframes[:15]:  # 最多分析15帧
        frame_path = kf.get("frame_path")
        if not frame_path or not os.path.exists(frame_path):
            continue

        img = cv2.imread(frame_path)
        if img is None:
            continue

        h, w = img.shape[:2]
        resolutions.append((w, h))

        # 转 HSV 分析
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        brightness = np.mean(hsv[:, :, 2])
        saturation = np.mean(hsv[:, :, 1])
        brightness_values.append(brightness)
        saturation_values.append(saturation)

    if not brightness_values:
        return {}

    avg_brightness = sum(brightness_values) / len(brightness_values)
    avg_saturation = sum(saturation_values) / len(saturation_values)

    # 亮度分级
    if avg_brightness < 80:
        brightness_label = "暗调"
    elif avg_brightness < 160:
        brightness_label = "中等亮度"
    else:
        brightness_label = "明亮"

    # 饱和度分级
    if avg_saturation < 60:
        sat_label = "低饱和（冷淡风）"
    elif avg_saturation < 140:
        sat_label = "中等饱和"
    else:
        sat_label = "高饱和（鲜艳风）"

    # 主分辨率
    if resolutions:
        most_common_res = max(set(resolutions), key=resolutions.count)
        res_label = f"{most_common_res[0]}x{most_common_res[1]}"
    else:
        res_label = "未知"

    return {
        "avg_brightness": round(avg_brightness, 1),
        "brightness_label": brightness_label,
        "avg_saturation": round(avg_saturation, 1),
        "saturation_label": sat_label,
        "resolution": res_label,
        "frames_analyzed": len(brightness_values),
    }
