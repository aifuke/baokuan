#!/usr/bin/env python3
"""
爆款视频反推复刻工具 - Web API
输入URL → 返回可直接照着拍的复刻指南
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
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))

# 确保 ffmpeg
def _ensure_ffmpeg():
    import shutil
    if shutil.which("ffmpeg"):
        return
    try:
        import imageio_ffmpeg
        p = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(p):
            d = os.path.dirname(p)
            link = os.path.join(d, "ffmpeg")
            if not os.path.exists(link):
                os.symlink(p, link)
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
    except ImportError:
        pass

_ensure_ffmpeg()

app = FastAPI(title="爆款视频反推复刻工具", version="2.0.0")
WEB_DIR = Path(__file__).parent / "web"
OUTPUT_BASE = Path(__file__).parent / "output"
OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
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
    return HTMLResponse(content=(WEB_DIR / "index.html").read_text(encoding="utf-8"))


@app.post("/api/analyze")
async def start_analysis(req: AnalyzeRequest):
    task_id = str(uuid.uuid4())[:8]
    task_dir = OUTPUT_BASE / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    tasks[task_id] = {"status": "running", "progress": 0, "current_step": "download", "result": None, "error": None}
    asyncio.create_task(_run(task_id, req, str(task_dir)))
    return {"task_id": task_id, "status": "running"}


@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    return tasks[task_id]


@app.get("/api/download")
async def download_report(path: str = Query(...)):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path, media_type="text/markdown", filename=os.path.basename(path))


async def _run(task_id: str, req: AnalyzeRequest, output_dir: str):
    steps = ["download", "transcribe", "visual", "script", "trend", "replicate", "report"]
    progress_map = {s: i * 14 for i, s in enumerate(steps)}

    def update(step, progress=None):
        tasks[task_id]["current_step"] = step
        if progress is not None:
            tasks[task_id]["progress"] = progress

    try:
        from modules.video_downloader import download_video, extract_audio, extract_video_info_local
        from modules.audio_transcriber import transcribe_audio, estimate_speech_rate
        from modules.visual_analyzer import extract_keyframes, analyze_scene_changes, analyze_frame_visual_features
        from modules.script_analyzer import analyze_script_structure
        from modules.trend_analyzer import compute_engagement_metrics, analyze_tags_and_topics, analyze_publishing_strategy, generate_viral_score_card
        from modules.replication_guide import generate_replication_guide, enhance_replication_with_llm
        from modules.report_generator import generate_report

        cache = os.path.join(output_dir, "cache")
        os.makedirs(cache, exist_ok=True)
        results = {}
        source = req.source
        is_url = source.startswith(("http://", "https://"))

        # 1. Download
        update("download", 5)
        if is_url:
            dl = await asyncio.to_thread(download_video, source, cache, req.max_resolution)
            video_path, metadata = dl["video_path"], dl["metadata"]
        else:
            video_path = source
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"文件不存在: {video_path}")
            metadata = {}
        local_info = await asyncio.to_thread(extract_video_info_local, video_path)
        metadata.update({k: v for k, v in local_info.items() if k not in metadata or not metadata.get(k)})
        results["metadata"] = metadata
        update("download", 14)

        # 2. Transcribe
        update("transcribe", 15)
        audio = await asyncio.to_thread(extract_audio, video_path, cache)
        transcript = await asyncio.to_thread(transcribe_audio, audio, cache, req.whisper_model, req.language)
        sr = estimate_speech_rate(transcript["segments"], transcript.get("language", "zh"))
        transcript["speech_rate"] = sr
        results["transcript"] = transcript
        update("transcribe", 30)

        # 3. Visual
        update("visual", 32)
        kf = await asyncio.to_thread(extract_keyframes, video_path, cache)
        dur = metadata.get("duration", 0) or 0
        sa = analyze_scene_changes(kf, dur)
        vf = analyze_frame_visual_features(kf)
        results["visual_analysis"] = {"keyframe_count": len(kf), "scene_analysis": sa, "visual_features": vf}
        update("visual", 44)

        # 4. Script
        update("script", 46)
        script_a = await asyncio.to_thread(analyze_script_structure, transcript["segments"], transcript["full_text"], dur)
        results["script_analysis"] = script_a
        update("script", 56)

        # 5. Trend
        update("trend", 58)
        eng = compute_engagement_metrics(metadata)
        tags = analyze_tags_and_topics(metadata, transcript["full_text"])
        pub = analyze_publishing_strategy(metadata)
        sc = generate_viral_score_card(eng, script_a, results["visual_analysis"], pub)
        results["trend_analysis"] = {"engagement": eng, "tags_topics": tags, "publishing": pub}
        results["score_card"] = sc
        update("trend", 68)

        # 6. Replication guide
        update("replicate", 70)
        rg = generate_replication_guide(transcript, script_a, results["visual_analysis"], results["trend_analysis"], metadata)
        llm_r = {}
        if req.llm_enhance:
            llm_r = await asyncio.to_thread(enhance_replication_with_llm, rg, transcript, script_a, results["visual_analysis"], metadata, req.openai_api_key, req.openai_base_url, req.openai_model)
            if llm_r.get("llm_enhanced"):
                rg = llm_r
        results["replication_guide"] = rg
        results["llm_enhanced"] = llm_r
        update("replicate", 85)

        # 7. Report
        update("report", 88)
        rp = await asyncio.to_thread(generate_report, results, output_dir)
        with open(rp, "r", encoding="utf-8") as f:
            report_md = f.read()
        results["report_path"] = rp
        results["report_markdown"] = report_md
        update("report", 100)

        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = 100
        tasks[task_id]["result"] = _ser(results)

    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = f"{type(e).__name__}: {e}"
        traceback.print_exc()


def _ser(obj):
    if isinstance(obj, dict): return {k: _ser(v) for k, v in obj.items()}
    if isinstance(obj, list): return [_ser(i) for i in obj]
    if isinstance(obj, (int, float, str, bool, type(None))): return obj
    return str(obj)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8765))
    print(f"🚀 http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
