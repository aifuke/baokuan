#!/usr/bin/env python3
"""
🎬 爆款视频反推复刻工具
========================
输入视频URL → 自动下载+转录+分析 → 输出可直接照着拍的同款复刻指南

用法:
    python main.py <视频URL或本地路径> [选项]

示例:
    python main.py "https://www.bilibili.com/video/BV1xx411c7mD"
    python main.py ./video.mp4 --whisper-model small
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _ensure_ffmpeg():
    """确保 ffmpeg 在 PATH 中"""
    import shutil
    if shutil.which("ffmpeg"):
        return
    try:
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(ffmpeg_path):
            bin_dir = os.path.dirname(ffmpeg_path)
            link = os.path.join(bin_dir, "ffmpeg")
            if not os.path.exists(link):
                os.symlink(ffmpeg_path, link)
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
    except ImportError:
        pass


def analyze_and_replicate(
    source: str,
    output_dir: str = "./output",
    whisper_model: str = "base",
    language: str = None,
    llm_enhance: bool = False,
    openai_api_key: str = None,
    openai_base_url: str = None,
    openai_model: str = "gpt-4o-mini",
    max_resolution: int = 720,
    cookies_file: str = None,
) -> dict:
    """完整流程：下载→转录→分析→生成复刻指南"""
    _ensure_ffmpeg()
    start_time = time.time()
    output_dir = Path(output_dir)
    cache_dir = output_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    from modules.video_downloader import download_video, extract_audio, extract_video_info_local
    from modules.audio_transcriber import transcribe_audio, estimate_speech_rate
    from modules.visual_analyzer import extract_keyframes, analyze_scene_changes, analyze_frame_visual_features
    from modules.script_analyzer import analyze_script_structure
    from modules.trend_analyzer import (
        compute_engagement_metrics, analyze_tags_and_topics,
        analyze_publishing_strategy, generate_viral_score_card,
    )
    from modules.replication_guide import generate_replication_guide, enhance_replication_with_llm
    from modules.report_generator import generate_report

    results = {}
    is_url = source.startswith(("http://", "https://"))

    # Step 1: 获取视频
    print("\n📥 [1/6] 获取视频与元数据...")
    if is_url:
        dl = download_video(source, str(cache_dir), max_resolution, cookies_file)
        video_path = dl["video_path"]
        metadata = dl["metadata"]
    else:
        video_path = source
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"文件不存在: {video_path}")
        metadata = {}

    local_info = extract_video_info_local(video_path)
    metadata.update({k: v for k, v in local_info.items() if k not in metadata or not metadata.get(k)})
    results["metadata"] = metadata
    print(f"  ✅ {metadata.get('duration_str', '?')} | {metadata.get('width', '?')}x{metadata.get('height', '?')}")

    # Step 2: 转录
    print("🎙️ [2/6] 语音转文字...")
    audio_path = extract_audio(video_path, str(cache_dir))
    transcript = transcribe_audio(audio_path, str(cache_dir), whisper_model, language)
    speech_rate = estimate_speech_rate(transcript["segments"], transcript.get("language", "zh"))
    transcript["speech_rate"] = speech_rate
    results["transcript"] = transcript
    print(f"  ✅ {transcript['word_count']}字 | 语速: {speech_rate['pace_label']}")

    # Step 3: 视觉分析
    print("🎬 [3/6] 视觉与剪辑分析...")
    keyframes = extract_keyframes(video_path, str(cache_dir))
    total_duration = metadata.get("duration", 0) or 0
    scene_analysis = analyze_scene_changes(keyframes, total_duration)
    visual_features = analyze_frame_visual_features(keyframes)
    results["visual_analysis"] = {
        "keyframe_count": len(keyframes),
        "scene_analysis": scene_analysis,
        "visual_features": visual_features,
    }
    print(f"  ✅ {len(keyframes)}帧 | 节奏: {scene_analysis.get('pace_label', '?')}")

    # Step 4: 文案拆解
    print("📝 [4/6] 文案结构拆解...")
    script_analysis = analyze_script_structure(
        transcript["segments"], transcript["full_text"], total_duration
    )
    results["script_analysis"] = script_analysis
    print(f"  ✅ 钩子: {', '.join(script_analysis.get('hook', {}).get('types', ['无']))}")

    # Step 5: 爆款评分
    print("🔥 [5/6] 爆款元素分析...")
    engagement = compute_engagement_metrics(metadata)
    tags_topics = analyze_tags_and_topics(metadata, transcript["full_text"])
    publishing = analyze_publishing_strategy(metadata)
    score_card = generate_viral_score_card(engagement, script_analysis, results["visual_analysis"], publishing)
    results["trend_analysis"] = {"engagement": engagement, "tags_topics": tags_topics, "publishing": publishing}
    results["score_card"] = score_card
    print(f"  ✅ 评分: {score_card['total_score']}/100 — {score_card['overall_rating']}")

    # Step 6: 生成复刻指南
    print("🎯 [6/6] 生成复刻指南...")
    replication_guide = generate_replication_guide(
        transcript, script_analysis, results["visual_analysis"],
        results["trend_analysis"], metadata,
    )

    # LLM增强（可选）
    llm_result = {}
    if llm_enhance:
        print("🧠 [6.5] AI增强复刻方案...")
        llm_result = enhance_replication_with_llm(
            replication_guide, transcript, script_analysis,
            results["visual_analysis"], metadata,
            openai_api_key, openai_base_url, openai_model,
        )
        if llm_result.get("llm_enhanced"):
            replication_guide = llm_result  # LLM版覆盖规则引擎版
            print(f"  ✅ AI复刻方案生成完成")

    results["replication_guide"] = replication_guide
    results["llm_enhanced"] = llm_result

    # 生成报告
    report_path = generate_report(results, str(output_dir))
    results["report_path"] = report_path

    # 保存原始数据
    raw_path = str(output_dir / "analysis_raw.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(_serializable(results), f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start_time
    print(f"\n{'='*50}")
    print(f"✅ 完成! 耗时 {elapsed:.1f}s")
    print(f"📄 复刻指南: {report_path}")
    print(f"{'='*50}\n")

    return results


def _serializable(obj):
    if isinstance(obj, dict):
        return {k: _serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_serializable(i) for i in obj]
    elif isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    return str(obj)


def main():
    parser = argparse.ArgumentParser(description="🎬 爆款视频反推复刻工具")
    parser.add_argument("source", help="视频URL或本地路径")
    parser.add_argument("-o", "--output", default="./output", help="输出目录")
    parser.add_argument("--whisper-model", default="base", choices=["tiny", "base", "small", "medium", "large"])
    parser.add_argument("--language", default=None, help="语言(zh/en/ja)")
    parser.add_argument("--max-resolution", type=int, default=720)
    parser.add_argument("--cookies", default=None)
    parser.add_argument("--llm-enhance", action="store_true", help="启用AI增强复刻")
    parser.add_argument("--openai-api-key", default=None)
    parser.add_argument("--openai-base-url", default=None)
    parser.add_argument("--openai-model", default="gpt-4o-mini")
    args = parser.parse_args()

    analyze_and_replicate(
        source=args.source, output_dir=args.output,
        whisper_model=args.whisper_model, language=args.language,
        llm_enhance=args.llm_enhance, openai_api_key=args.openai_api_key,
        openai_base_url=args.openai_base_url, openai_model=args.openai_model,
        max_resolution=args.max_resolution, cookies_file=args.cookies,
    )


if __name__ == "__main__":
    main()
