"""
报告生成模块 - 聚焦"复刻同款"输出
将分析结果 + 复刻指南整合为一份可直接执行的 Markdown 报告
"""

import json
import os
from datetime import datetime
from pathlib import Path


def generate_report(
    analysis_results: dict,
    output_dir: str,
    report_name: str = "replication_guide",
) -> str:
    """生成完整的复刻指南报告"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    meta = analysis_results.get("metadata", {})
    transcript = analysis_results.get("transcript", {})
    script = analysis_results.get("script_analysis", {})
    visual = analysis_results.get("visual_analysis", {})
    trend = analysis_results.get("trend_analysis", {})
    score_card = analysis_results.get("score_card", {})
    replicate = analysis_results.get("replication_guide", {})
    llm = analysis_results.get("llm_enhanced", {})

    lines = []

    # ===== 标题 =====
    title = meta.get("title", "未知视频")
    lines.append(f"# 🎬 爆款视频复刻指南")
    lines.append("")
    lines.append(f"> **原视频**: {title}")
    lines.append(f"> **平台**: {meta.get('platform', '未知')} | **作者**: {meta.get('uploader', '未知')}")
    lines.append(f"> **时长**: {meta.get('duration_str', '未知')} | **播放**: {_fmt_num(meta.get('view_count', 0))} | **点赞**: {_fmt_num(meta.get('like_count', 0))}")
    lines.append(f"> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ===== 复刻难度 =====
    difficulty = replicate.get("replication_difficulty", "未评估")
    lines.append(f"## 📊 复刻难度: {difficulty}")
    lines.append("")

    # ===== 评分卡 =====
    if score_card:
        total = score_card.get("total_score", 0)
        rating = score_card.get("overall_rating", "")
        lines.append(f"**爆款评分: {total}/100 — {rating}**")
        lines.append("")
        scores = score_card.get("scores", {})
        labels = score_card.get("dimension_labels", {})
        for key, label in labels.items():
            s = scores.get(key, 0)
            mx = {"engagement": 30, "hook": 20, "structure": 20, "visual": 15, "publishing": 15}.get(key, 20)
            bar = "█" * int(s / max(mx, 1) * 10) + "░" * (10 - int(s / max(mx, 1) * 10))
            lines.append(f"- {label}: `{bar}` {s}/{mx}")
        lines.append("")

    # ===== 逐句复刻脚本 =====
    lines.append("---")
    lines.append("")
    lines.append("## 🎭 逐句复刻脚本")
    lines.append("")
    lines.append("| 时间 | 角色 | 原文案 | 复刻文案 | 画面指令 | 语气 |")
    lines.append("|------|------|--------|----------|----------|------|")

    replica_script = replicate.get("replica_script", [])
    # LLM增强版优先
    if llm and llm.get("llm_enhanced") and llm.get("replica_script"):
        replica_script = llm["replica_script"]

    for item in replica_script[:30]:  # 最多展示30行
        t = item.get("time", "")
        role = item.get("role", "")
        orig = item.get("original_text", "")[:40]
        rep = item.get("replica_text", "")[:40]
        vis = item.get("visual_direction", "")[:30]
        tone = item.get("tone", "")
        lines.append(f"| {t} | {role} | {orig} | {rep} | {vis} | {tone} |")
    lines.append("")

    # ===== 拍摄清单 =====
    lines.append("---")
    lines.append("")
    lines.append("## 🎥 拍摄清单")
    lines.append("")

    shooting = replicate.get("shooting_checklist", {})
    if llm and llm.get("llm_enhanced") and llm.get("shooting_plan"):
        sp = llm["shooting_plan"]
        lines.append(f"### 场景")
        for s in sp.get("scenes_needed", []):
            lines.append(f"- {s}")
        lines.append(f"### 道具")
        for p in sp.get("props", []):
            lines.append(f"- {p}")
        lines.append(f"### 服装造型")
        lines.append(f"{sp.get('wardrobe', '')}")
        lines.append(f"### 灯光")
        lines.append(f"{sp.get('lighting', '')}")
        lines.append(f"### 机位运镜")
        lines.append(f"{sp.get('camera_setup', '')}")
        lines.append(f"### 预估镜头数: {sp.get('total_shots_estimate', '')}")
    else:
        for key, val in shooting.items():
            label = {
                "resolution": "📐 分辨率",
                "lighting": "💡 灯光",
                "camera_setup": "📷 机位",
                "wardrobe": "👔 服装",
                "total_shots_estimate": "🎞️ 镜头数",
            }.get(key, key)
            if isinstance(val, list):
                lines.append(f"### {label}")
                for v in val:
                    lines.append(f"- {v}")
            else:
                lines.append(f"- **{label}**: {val}")
    lines.append("")

    # ===== 剪辑模板 =====
    lines.append("---")
    lines.append("")
    lines.append("## ✂️ 剪辑模板")
    lines.append("")

    editing = replicate.get("editing_template", {})
    if llm and llm.get("llm_enhanced") and llm.get("editing_blueprint"):
        eb = llm["editing_blueprint"]
        lines.append(f"- **开头钩子手法**: {eb.get('opening_hook_technique', '')}")
        lines.append(f"- **转场风格**: {eb.get('transition_style', '')}")
        lines.append(f"- **字幕样式**: {eb.get('subtitle_style', '')}")
        lines.append(f"- **BGM建议**: {eb.get('bgm_recommendation', '')}")
        lines.append(f"- **节奏要点**: {eb.get('pacing_notes', '')}")
        effects = eb.get("effects", [])
        if effects:
            lines.append(f"- **特效/滤镜**: {', '.join(effects)}")
    else:
        for key, val in editing.items():
            label = {
                "opening_hook_technique": "🎣 开头钩子手法",
                "transition_style": "🔄 转场风格",
                "subtitle_style": "📝 字幕样式",
                "bgm_recommendation": "🎵 BGM建议",
                "pacing_notes": "⏱️ 节奏要点",
                "effects": "✨ 特效/滤镜",
            }.get(key, key)
            if isinstance(val, list):
                lines.append(f"- **{label}**: {', '.join(val)}")
            else:
                lines.append(f"- **{label}**: {val}")
    lines.append("")

    # ===== 发布策略 =====
    lines.append("---")
    lines.append("")
    lines.append("## 🚀 发布策略")
    lines.append("")

    pub = replicate.get("publishing_strategy", {})
    if llm and llm.get("llm_enhanced"):
        formulas = llm.get("title_formulas", [])
        if formulas:
            lines.append("### 标题公式")
            for f in formulas:
                lines.append(f"1. {f}")
            lines.append("")
        if llm.get("hashtag_combination"):
            lines.append(f"### 标签组合: {llm['hashtag_combination']}")
            lines.append("")
        if llm.get("best_post_time"):
            lines.append(f"### 最佳发布时间: {llm['best_post_time']}")
            lines.append("")
        if llm.get("difficulty_notes"):
            lines.append(f"### ⚠️ 复刻注意事项")
            lines.append(f"{llm['difficulty_notes']}")
            lines.append("")
    else:
        formulas = pub.get("title_formulas", [])
        if formulas:
            lines.append("### 标题公式")
            for i, f in enumerate(formulas, 1):
                lines.append(f"{i}. {f}")
            lines.append("")
        if pub.get("hashtag_combination"):
            lines.append(f"### 标签组合")
            lines.append(f"{pub['hashtag_combination']}")
            lines.append("")
        if pub.get("best_post_time"):
            lines.append(f"### 最佳发布时间")
            lines.append(f"{pub['best_post_time']}")
            lines.append("")
        if pub.get("cover_tip"):
            lines.append(f"### 封面建议")
            lines.append(f"{pub['cover_tip']}")
            lines.append("")

    # ===== 完整原文 =====
    full_text = transcript.get("full_text", "")
    if full_text:
        lines.append("---")
        lines.append("")
        lines.append("## 📄 原视频完整文案")
        lines.append("")
        lines.append("<details>")
        lines.append("<summary>点击展开</summary>")
        lines.append("")
        segments = transcript.get("segments", [])
        for seg in segments:
            ts = _fmt_time(seg.get("start", 0))
            lines.append(f"**[{ts}]** {seg.get('text', '')}")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.append("---")
    lines.append("*由爆款视频反推工具自动生成，照着拍就行。*")

    report_content = "\n".join(lines)
    report_path = str(output_dir / f"{report_name}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"[report] 复刻指南已生成: {report_path}")
    return report_path


def _fmt_num(n) -> str:
    if not n or not isinstance(n, (int, float)):
        return "未知"
    n = int(n)
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}亿"
    elif n >= 10_000:
        return f"{n / 10_000:.1f}万"
    return str(n)


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
