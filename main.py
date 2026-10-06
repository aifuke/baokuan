#!/usr/bin/env python3
"""
🔥 爆款视频反推分析工具 (Viral Video Analyzer)
==============================================

输入一个视频 URL 或本地文件路径，自动完成：
1. 视频下载与元数据提取
2. 音频转录（Whisper 语音识别）
3. 关键帧提取与视觉分析
4. 文案结构拆解（钩子、节奏、CTA、情绪曲线）
5. 爆款元素分析与评分
6. 生成结构化 Markdown 反推报告

用法:
    python main.py <视频URL或本地路径> [选项]

示例:
    python main.py "https://www.bilibili.com/video/BV1xx411c7mD"
    python main.py ./local_video.mp4 --whisper-model small
    python main.py "https://www.douyin.com/video/xxx" --llm-enhance
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# 确保模块可导入
sys.path.insert(0, str(Path(__file__).parent))

from modules.video_downloader import download_video, extract_audio, extract_video_info_local
from modules.audio_transcriber import transcribe_audio, estimate_speech_rate
from modules.visual_analyzer import extract_keyframes, analyze_scene_changes, analyze_frame_visual_features
from modules.script_analyzer import analyze_script_structure, enhance_with_llm
from modules.trend_analyzer import (
    compute_engagement_metrics,
    analyze_tags_and_topics,
    analyze_publishing_strategy,
    generate_viral_score_card,
)
from modules.report_generator import generate_report


def analyze_video(
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
    skip_download: bool = False,
) -> dict:
    """
    完整的视频反推分析流程。

    Args:
        source: 视频 URL 或本地文件路径
        output_dir: 输出目录
        whisper_model: Whisper 模型 (tiny/base/small/medium/large)
        language: 语言代码，None 自动检测
        llm_enhance: 是否启用 LLM 增强分析
        openai_api_key: OpenAI API Key（LLM 增强时需要）
        openai_base_url: OpenAI API Base URL
        openai_model: LLM 模型名称
        max_resolution: 最大下载分辨率
        cookies_file: cookies 文件路径
        skip_download: 跳过下载（source 为本地文件时）

    Returns:
        dict: 完整分析结果 + 报告路径
    """
    start_time = time.time()

    # 确保 ffmpeg 在 PATH 中（Whisper 内部调用需要）
    _ensure_ffmpeg_in_path()

    output_dir = Path(output_dir)
    cache_dir = output_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    is_url = source.startswith(("http://", "https://"))

    # ================================================================
    # Step 1: 获取视频文件与元数据
    # ================================================================
    print("\n" + "=" * 60)
    print("📥 Step 1/6: 获取视频与元数据")
    print("=" * 60)

    if is_url and not skip_download:
        dl_result = download_video(
            url=source,
            output_dir=str(cache_dir),
            max_resolution=max_resolution,
            cookies_file=cookies_file,
        )
        video_path = dl_result["video_path"]
        metadata = dl_result["metadata"]
        results["thumbnail"] = dl_result.get("thumbnail")
    else:
        # 本地文件
        video_path = source
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        metadata = {}

    # 补充本地视频信息
    local_info = extract_video_info_local(video_path)
    metadata.update({k: v for k, v in local_info.items() if k not in metadata or not metadata[k]})
    results["metadata"] = metadata
    results["video_path"] = video_path

    print(f"  ✅ 视频就绪: {os.path.basename(video_path)}")
    print(f"  📊 时长: {metadata.get('duration_str', '未知')}, 分辨率: {metadata.get('width', '?')}x{metadata.get('height', '?')}")

    # ================================================================
    # Step 2: 音频转录
    # ================================================================
    print("\n" + "=" * 60)
    print("🎙️ Step 2/6: 音频转录 (Whisper)")
    print("=" * 60)

    audio_path = extract_audio(video_path, str(cache_dir))
    transcript = transcribe_audio(
        audio_path=audio_path,
        output_dir=str(cache_dir),
        model_name=whisper_model,
        language=language,
    )
    speech_rate = estimate_speech_rate(
        transcript["segments"],
        language=transcript.get("language", "zh"),
    )
    transcript["speech_rate"] = speech_rate
    results["transcript"] = transcript

    print(f"  ✅ 转录完成: {transcript['word_count']}字, 语速: {speech_rate['pace_label']}")

    # ================================================================
    # Step 3: 视觉分析
    # ================================================================
    print("\n" + "=" * 60)
    print("🎬 Step 3/6: 视觉与剪辑分析")
    print("=" * 60)

    keyframes = extract_keyframes(video_path, str(cache_dir))
    total_duration = metadata.get("duration", 0) or 0
    scene_analysis = analyze_scene_changes(keyframes, total_duration)
    visual_features = analyze_frame_visual_features(keyframes)

    results["visual_analysis"] = {
        "keyframe_count": len(keyframes),
        "scene_analysis": scene_analysis,
        "visual_features": visual_features,
    }

    print(f"  ✅ 关键帧: {len(keyframes)}帧, 剪辑节奏: {scene_analysis.get('pace_label', '未知')}")

    # ================================================================
    # Step 4: 文案结构分析
    # ================================================================
    print("\n" + "=" * 60)
    print("📝 Step 4/6: 文案结构拆解")
    print("=" * 60)

    script_analysis = analyze_script_structure(
        segments=transcript["segments"],
        full_text=transcript["full_text"],
        total_duration=total_duration,
    )
    results["script_analysis"] = script_analysis

    hook_types = script_analysis.get("hook", {}).get("types", [])
    cta_types = script_analysis.get("cta", {}).get("types", [])
    print(f"  ✅ 钩子类型: {', '.join(hook_types)}")
    print(f"  ✅ CTA 类型: {', '.join(cta_types)}")
    print(f"  ✅ 情绪基调: {script_analysis.get('emotion_curve', {}).get('overall_tone', '未知')}")

    # ================================================================
    # Step 5: 爆款元素分析
    # ================================================================
    print("\n" + "=" * 60)
    print("🔥 Step 5/6: 爆款元素分析与评分")
    print("=" * 60)

    engagement = compute_engagement_metrics(metadata)
    tags_topics = analyze_tags_and_topics(metadata, transcript["full_text"])
    publishing = analyze_publishing_strategy(metadata)

    score_card = generate_viral_score_card(
        engagement=engagement,
        script_analysis=script_analysis,
        visual_analysis=results["visual_analysis"],
        publishing=publishing,
    )

    results["trend_analysis"] = {
        "engagement": engagement,
        "tags_topics": tags_topics,
        "publishing": publishing,
    }
    results["score_card"] = score_card

    print(f"  ✅ 互动率: {engagement.get('total_engagement_rate', 'N/A')}%")
    print(f"  ✅ 爆款评分: {score_card['total_score']}/100 — {score_card['overall_rating']}")

    # ================================================================
    # Step 5.5: LLM 增强分析（可选）
    # ================================================================
    if llm_enhance:
        print("\n" + "=" * 60)
        print("🧠 Step 5.5: AI 深度洞察 (LLM)")
        print("=" * 60)

        llm_result = enhance_with_llm(
            script_analysis=script_analysis,
            full_text=transcript["full_text"],
            metadata=metadata,
            api_key=openai_api_key,
            base_url=openai_base_url,
            model=openai_model,
        )
        results["llm_enhanced"] = llm_result

        if llm_result.get("llm_enhanced"):
            print(f"  ✅ LLM 分析完成 (model={llm_result.get('model_used', '')})")
        else:
            print(f"  ⚠️ LLM 分析未启用或失败")

    # ================================================================
    # Step 6: 生成报告
    # ================================================================
    print("\n" + "=" * 60)
    print("📄 Step 6/6: 生成反推报告")
    print("=" * 60)

    report_path = generate_report(results, str(output_dir))
    results["report_path"] = report_path

    # 保存原始分析数据
    raw_data_path = str(output_dir / "analysis_raw.json")
    with open(raw_data_path, "w", encoding="utf-8") as f:
        # 移除不可序列化的内容
        serializable = _make_serializable(results)
        json.dump(serializable, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"✅ 分析完成! 耗时 {elapsed:.1f}秒")
    print(f"📄 报告: {report_path}")
    print(f"📊 原始数据: {raw_data_path}")
    print(f"{'=' * 60}\n")

    return results


def _ensure_ffmpeg_in_path():
    """确保 ffmpeg 在系统 PATH 中，Whisper 等库内部通过 subprocess 调用 ffmpeg"""
    import shutil
    if shutil.which("ffmpeg"):
        return
    # 尝试 imageio-ffmpeg
    try:
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(ffmpeg_path):
            bin_dir = os.path.dirname(ffmpeg_path)
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
            print(f"[setup] ffmpeg added to PATH: {bin_dir}")
            return
    except ImportError:
        pass
    # 尝试 ~/bin
    home_bin = os.path.expanduser("~/bin")
    if os.path.exists(os.path.join(home_bin, "ffmpeg")):
        os.environ["PATH"] = home_bin + os.pathsep + os.environ.get("PATH", "")
        print(f"[setup] ffmpeg added to PATH: {home_bin}")


def _make_serializable(obj):
    """递归清理不可 JSON 序列化的对象"""
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_make_serializable(item) for item in obj]
    elif isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    else:
        return str(obj)


def main():
    parser = argparse.ArgumentParser(
        description="🔥 爆款视频反推分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py "https://www.bilibili.com/video/BV1xx411c7mD"
  python main.py ./video.mp4 --whisper-model small --output ./my_report
  python main.py "https://www.douyin.com/video/xxx" --llm-enhance --openai-model gpt-4o
        """,
    )

    parser.add_argument("source", help="视频 URL 或本地文件路径")
    parser.add_argument("-o", "--output", default="./output", help="输出目录 (默认: ./output)")
    parser.add_argument("--whisper-model", default="base", choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper 模型大小 (默认: base)")
    parser.add_argument("--language", default=None, help="语言代码，如 zh/en/ja (默认: 自动检测)")
    parser.add_argument("--max-resolution", type=int, default=720, help="最大下载分辨率 (默认: 720)")
    parser.add_argument("--cookies", default=None, help="cookies 文件路径（用于需要登录的平台）")
    parser.add_argument("--skip-download", action="store_true", help="跳过下载（仅用于本地文件）")

    # LLM 增强选项
    parser.add_argument("--llm-enhance", action="store_true", help="启用 LLM 深度分析")
    parser.add_argument("--openai-api-key", default=None, help="OpenAI API Key (也可通过 OPENAI_API_KEY 环境变量设置)")
    parser.add_argument("--openai-base-url", default=None, help="OpenAI API Base URL")
    parser.add_argument("--openai-model", default="gpt-4o-mini", help="LLM 模型名称 (默认: gpt-4o-mini)")

    args = parser.parse_args()

    results = analyze_video(
        source=args.source,
        output_dir=args.output,
        whisper_model=args.whisper_model,
        language=args.language,
        llm_enhance=args.llm_enhance,
        openai_api_key=args.openai_api_key,
        openai_base_url=args.openai_base_url,
        openai_model=args.openai_model,
        max_resolution=args.max_resolution,
        cookies_file=args.cookies,
        skip_download=args.skip_download,
    )

    return results


if __name__ == "__main__":
    main()
