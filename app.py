#!/usr/bin/env python3
"""
爆款视频反推分析工具 - Web API 服务
基于 FastAPI，提供异步分析任务 + 状态轮询接口
"""

import asyncio
import json
import os
import sys
import uuid
import traceback
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pydantic import BaseModel

# 确保模块可导入
sys.path.insert(0, str(Path(__file__).parent))

# 确保 ffmpeg 在 PATH 中
def _ensure_ffmpeg():
    import shutil
    if shutil.which("ffmpeg"):
        return
    try:
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(ffmpeg_path):
            bin_dir = os.path.dirname(ffmpeg_path)
            # 创建名为 ffmpeg 的符号链接（Whisper 需要）
            link = os.path.join(bin_dir, "ffmpeg")
            if not os.path.exists(link):
                os.symlink(ffmpeg_path, link)
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
    except ImportError:
        pass

_ensure_ffmpeg()

app = FastAPI(title="爆款视频反推分析工具", version="1.0.0")

# 静态文件
WEB_DIR = Path(__file__).parent / "web"
OUTPUT_BASE = Path(__file__).parent / "output"
OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

# 任务存储
tasks = {}


class AnalyzeRequest(BaseModel):
    source: str
    whisper_model: str = "base"
    language: Optional[str] = None
    llm_enhance: bool = False
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    max_resolution: int = 720


@app.get("/", response_class=HTMLResponse)
async def index():
    """首页"""
    html_path = WEB_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/api/analyze")
async def start_analysis(req: AnalyzeRequest):
    """启动分析任务"""
    task_id = str(uuid.uuid4())[:8]
    task_dir = OUTPUT_BASE / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    tasks[task_id] = {
        "status": "running",
        "progress": 0,
        "current_step": "download",
        "result": None,
        "error": None,
    }

    # 在后台运行分析
    asyncio.create_task(_run_analysis(task_id, req, str(task_dir)))

    return {"task_id": task_id, "status": "running"}


@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    """查询任务状态"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    return tasks[task_id]


@app.get("/api/download")
async def download_report(path: str = Query(...)):
    """下载报告文件"""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path, media_type="text/markdown", filename=os.path.basename(path))


async def _run_analysis(task_id: str, req: AnalyzeRequest, output_dir: str):
    """后台执行完整分析流程"""
    step_map = {
        "download": ("获取视频与元数据", 5),
        "transcribe": ("音频转录", 20),
        "visual": ("视觉与剪辑分析", 40),
        "script": ("文案结构拆解", 55),
        "trend": ("爆款元素分析与评分", 70),
        "llm": ("AI深度洞察", 80),
        "report": ("生成反推报告", 90),
    }

    def update_step(step_name: str, progress: int = None):
        tasks[task_id]["current_step"] = step_name
        if progress is not None:
            tasks[task_id]["progress"] = progress

    try:
        from modules.video_downloader import download_video, extract_audio, extract_video_info_local
        from modules.audio_transcriber import transcribe_audio, estimate_speech_rate
        from modules.visual_analyzer import extract_keyframes, analyze_scene_changes, analyze_frame_visual_features
        from modules.script_analyzer import analyze_script_structure, enhance_with_llm
        from modules.trend_analyzer import (
            compute_engagement_metrics, analyze_tags_and_topics,
            analyze_publishing_strategy, generate_viral_score_card,
        )
        from modules.report_generator import generate_report

        cache_dir = os.path.join(output_dir, "cache")
        os.makedirs(cache_dir, exist_ok=True)

        results = {}
        source = req.source
        is_url = source.startswith(("http://", "https://"))

        # Step 1: Download / Load video
        update_step("download", 5)
        if is_url:
            dl_result = await asyncio.to_thread(
                download_video, source, cache_dir, req.max_resolution
            )
            video_path = dl_result["video_path"]
            metadata = dl_result["metadata"]
        else:
            video_path = source
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"视频文件不存在: {video_path}")
            metadata = {}

        local_info = await asyncio.to_thread(extract_video_info_local, video_path)
        metadata.update({k: v for k, v in local_info.items() if k not in metadata or not metadata.get(k)})
        results["metadata"] = metadata
        update_step("download", 15)

        # Step 2: Transcribe
        update_step("transcribe", 20)
        audio_path = await asyncio.to_thread(extract_audio, video_path, cache_dir)
        transcript = await asyncio.to_thread(
            transcribe_audio, audio_path, cache_dir, req.whisper_model, req.language
        )
        speech_rate = estimate_speech_rate(transcript["segments"], transcript.get("language", "zh"))
        transcript["speech_rate"] = speech_rate
        results["transcript"] = transcript
        update_step("transcribe", 38)

        # Step 3: Visual analysis
        update_step("visual", 40)
        keyframes = await asyncio.to_thread(extract_keyframes, video_path, cache_dir)
        total_duration = metadata.get("duration", 0) or 0
        scene_analysis = analyze_scene_changes(keyframes, total_duration)
        visual_features = analyze_frame_visual_features(keyframes)
        results["visual_analysis"] = {
            "keyframe_count": len(keyframes),
            "scene_analysis": scene_analysis,
            "visual_features": visual_features,
        }
        update_step("visual", 53)

        # Step 4: Script analysis
        update_step("script", 55)
        script_analysis = await asyncio.to_thread(
            analyze_script_structure, transcript["segments"], transcript["full_text"], total_duration
        )
        results["script_analysis"] = script_analysis
        update_step("script", 68)

        # Step 5: Trend analysis
        update_step("trend", 70)
        engagement = compute_engagement_metrics(metadata)
        tags_topics = analyze_tags_and_topics(metadata, transcript["full_text"])
        publishing = analyze_publishing_strategy(metadata)
        score_card = generate_viral_score_card(engagement, script_analysis, results["visual_analysis"], publishing)
        results["trend_analysis"] = {"engagement": engagement, "tags_topics": tags_topics, "publishing": publishing}
        results["score_card"] = score_card
        update_step("trend", 78)

        # Step 5.5: LLM enhancement (optional)
        if req.llm_enhance:
            update_step("llm", 80)
            llm_result = await asyncio.to_thread(
                enhance_with_llm, script_analysis, transcript["full_text"], metadata,
                req.openai_api_key, req.openai_base_url, req.openai_model,
            )
            results["llm_enhanced"] = llm_result
            update_step("llm", 88)

        # Step 6: Generate report
        update_step("report", 90)
        report_path = await asyncio.to_thread(generate_report, results, output_dir)
        update_step("report", 95)

        # Read report markdown
        with open(report_path, "r", encoding="utf-8") as f:
            report_md = f.read()

        results["report_path"] = report_path
        results["report_markdown"] = report_md

        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = 100
        tasks[task_id]["result"] = _make_serializable(results)

    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = f"{type(e).__name__}: {str(e)}"
        traceback.print_exc()


def _make_serializable(obj):
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_make_serializable(item) for item in obj]
    elif isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    else:
        return str(obj)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8765))
    print(f"🚀 启动服务: http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
