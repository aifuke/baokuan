"""
报告生成模块 - 将所有分析结果整合为结构化 Markdown 报告
"""

import json
import os
from datetime import datetime
from pathlib import Path


def generate_report(
    analysis_results: dict,
    output_dir: str,
    report_name: str = "viral_video_analysis",
) -> str:
    """
    生成完整的 Markdown 反推报告。

    Args:
        analysis_results: 所有模块的分析结果汇总
        output_dir: 输出目录
        report_name: 报告文件名（不含扩展名）

    Returns:
        str: 报告文件路径
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    meta = analysis_results.get("metadata", {})
    transcript = analysis_results.get("transcript", {})
    script = analysis_results.get("script_analysis", {})
    visual = analysis_results.get("visual_analysis", {})
    trend = analysis_results.get("trend_analysis", {})
    score_card = analysis_results.get("score_card", {})
    llm_enhanced = analysis_results.get("llm_enhanced", {})

    lines = []

    # ===== 标题与基本信息 =====
    title = meta.get("title", "未知视频")
    lines.append(f"# 🔥 爆款视频反推分析报告")
    lines.append("")
    lines.append(f"> **视频标题**: {title}")
    lines.append(f"> **平台**: {meta.get('platform', '未知')}")
    lines.append(f"> **作者**: {meta.get('uploader', '未知')}")
    lines.append(f"> **发布日期**: {meta.get('upload_date_fmt', meta.get('upload_date', '未知'))}")
    lines.append(f"> **时长**: {meta.get('duration_str', '未知')}")
    lines.append(f"> **分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ===== 综合评分卡 =====
    if score_card:
        lines.append("## 📊 综合爆款评分卡")
        lines.append("")
        total = score_card.get("total_score", 0)
        rating = score_card.get("overall_rating", "未评估")
        lines.append(f"**总分: {total}/100 — {rating}**")
        lines.append("")

        dimension_labels = score_card.get("dimension_labels", {})
        scores = score_card.get("scores", {})
        lines.append("| 维度 | 得分 | 满分 |")
        lines.append("|------|------|------|")
        for key, label in dimension_labels.items():
            s = scores.get(key, 0)
            max_s = {"engagement": 30, "hook": 20, "structure": 20, "visual": 15, "publishing": 15}.get(key, 20)
            bar = "█" * int(s / max_s * 10) + "░" * (10 - int(s / max_s * 10))
            lines.append(f"| {label} | {bar} {s} | {max_s} |")
        lines.append("")

    # ===== 互动数据分析 =====
    engagement = trend.get("engagement", {})
    if engagement.get("available"):
        lines.append("## 📈 互动数据分析")
        lines.append("")
        lines.append(f"- **播放量**: {_format_number(engagement.get('views', 0))}")
        lines.append(f"- **点赞数**: {_format_number(engagement.get('likes', 0))} ({engagement.get('like_rate', 0)}%)")
        lines.append(f"- **评论数**: {_format_number(engagement.get('comments', 0))} ({engagement.get('comment_rate', 0)}%)")
        lines.append(f"- **分享数**: {_format_number(engagement.get('shares', 0))} ({engagement.get('share_rate', 0)}%)")
        lines.append(f"- **综合互动率**: {engagement.get('total_engagement_rate', 0)}% — **{engagement.get('engagement_level', '')}**")
        lines.append(f"- **互动类型**: {engagement.get('interaction_type', '')}")
        lines.append("")

    # ===== 文案结构拆解 =====
    lines.append("## 📝 文案结构拆解")
    lines.append("")

    # 钩子分析
    hook = script.get("hook", {})
    lines.append("### 🎣 开头钩子")
    lines.append("")
    hook_types = hook.get("types", ["无"])
    lines.append(f"- **钩子类型**: {', '.join(hook_types)}")
    lines.append(f"- **覆盖时长**: {hook.get('duration_covered', 0)}秒")
    if hook.get("text"):
        lines.append(f"- **原文摘录**: > {hook['text'][:150]}")
    lines.append("")

    # 内容块
    blocks = script.get("content_blocks", [])
    if blocks:
        lines.append("### 📐 内容节奏分段")
        lines.append("")
        lines.append("| 段落 | 时间段 | 字数 | 内容预览 |")
        lines.append("|------|--------|------|----------|")
        for block in blocks:
            start = _format_time(block.get("start_time", 0))
            end = _format_time(block.get("end_time", 0))
            preview = block.get("text_preview", "")[:40]
            lines.append(f"| {block.get('position', '')} | {start}-{end} | {block.get('word_count', 0)} | {preview}... |")
        lines.append("")

    # 情绪曲线
    emotion = script.get("emotion_curve", {})
    lines.append("### 🎭 情绪曲线")
    lines.append("")
    lines.append(f"- **整体基调**: {emotion.get('overall_tone', '未知')}")
    lines.append(f"- **正面情绪触发点**: {emotion.get('positive_hits', 0)}次")
    lines.append(f"- **负面情绪触发点**: {emotion.get('negative_hits', 0)}次")
    lines.append(f"- **惊讶/反转触发点**: {emotion.get('surprise_hits', 0)}次")
    lines.append("")

    # 转折点
    transitions = script.get("transitions", {})
    if transitions.get("count", 0) > 0:
        lines.append("### 🔄 关键转折点")
        lines.append("")
        for item in transitions.get("items", [])[:5]:
            ts = _format_time(item.get("timestamp", 0))
            lines.append(f"- **[{ts}]** {item.get('text', '')[:60]}")
        lines.append("")

    # CTA
    cta = script.get("cta", {})
    lines.append("### 📢 结尾行动号召 (CTA)")
    lines.append("")
    cta_types = cta.get("types", ["无"])
    lines.append(f"- **CTA 类型**: {', '.join(cta_types)}")
    if cta.get("text"):
        lines.append(f"- **原文摘录**: > {cta['text'][:150]}")
    lines.append("")

    # 文本统计
    text_stats = script.get("text_stats", {})
    if text_stats:
        lines.append("### 📊 文案数据统计")
        lines.append("")
        lines.append(f"- **总字数**: {text_stats.get('total_chars', 0)}")
        lines.append(f"- **句子数**: {text_stats.get('sentence_count', 0)}")
        lines.append(f"- **平均句长**: {text_stats.get('avg_sentence_length', 0)}字")
        lines.append(f"- **信息密度**: {text_stats.get('info_density', 0)}")
        lines.append(f"- **语速**: {text_stats.get('chars_per_second', 0)}字/秒")
        lines.append("")

    # ===== 视觉分析 =====
    lines.append("## 🎬 视觉与剪辑分析")
    lines.append("")

    scene = visual.get("scene_analysis", {})
    if scene:
        lines.append("### ✂️ 剪辑节奏")
        lines.append("")
        lines.append(f"- **场景切换次数**: {scene.get('total_scenes', 0)}")
        lines.append(f"- **平均镜头时长**: {scene.get('avg_scene_duration', 0)}秒")
        lines.append(f"- **每分钟切换次数**: {scene.get('cut_frequency', 0)}")
        lines.append(f"- **节奏评价**: {scene.get('pace_label', '未知')}")
        if scene.get("fastest_cut"):
            lines.append(f"- **最快切换间隔**: {scene.get('fastest_cut', 0)}秒")
        lines.append("")

    features = visual.get("visual_features", {})
    if features:
        lines.append("### 🎨 画面风格")
        lines.append("")
        lines.append(f"- **分辨率**: {features.get('resolution', '未知')}")
        lines.append(f"- **亮度风格**: {features.get('brightness_label', '未知')} (均值: {features.get('avg_brightness', 0)})")
        lines.append(f"- **色彩饱和度**: {features.get('saturation_label', '未知')} (均值: {features.get('avg_saturation', 0)})")
        lines.append("")

    # ===== 标签与发布策略 =====
    tags_topics = trend.get("tags_topics", {})
    publishing = trend.get("publishing", {})

    lines.append("## 🏷️ 标签与发布策略")
    lines.append("")

    if publishing:
        lines.append("### 📅 发布信息")
        lines.append("")
        lines.append(f"- **发布日期**: {publishing.get('upload_date', '未知')} {publishing.get('weekday', '')}")
        lines.append(f"- **标题长度**: {publishing.get('title_length', 0)}字 — {publishing.get('title_length_eval', '')}")
        lines.append(f"- **标题风格**: {', '.join(publishing.get('title_styles', []))}")
        lines.append("")

    if tags_topics:
        lines.append("### 🏷️ 标签策略")
        lines.append("")
        lines.append(f"- **标签数量**: {tags_topics.get('tag_count', 0)} — {tags_topics.get('tag_strategy', '')}")
        platform_tags = tags_topics.get("platform_tags", [])
        if platform_tags:
            lines.append(f"- **平台标签**: {', '.join(platform_tags[:10])}")
        hashtags = tags_topics.get("hashtags", [])
        if hashtags:
            lines.append(f"- **话题标签**: {', '.join('#' + t for t in hashtags[:10])}")
        keywords = tags_topics.get("keywords", [])
        if keywords:
            lines.append(f"- **核心关键词**: {', '.join(keywords[:8])}")
        lines.append("")

    # ===== LLM 增强分析 =====
    if llm_enhanced and llm_enhanced.get("llm_enhanced"):
        lines.append("## 🧠 AI 深度洞察")
        lines.append("")
        if llm_enhanced.get("narrative_structure"):
            lines.append(f"### 叙事结构")
            lines.append(f"{llm_enhanced['narrative_structure']}")
            lines.append("")
        if llm_enhanced.get("target_audience"):
            lines.append(f"### 目标受众")
            lines.append(f"{llm_enhanced['target_audience']}")
            lines.append("")
        if llm_enhanced.get("core_value_proposition"):
            lines.append(f"### 核心价值主张")
            lines.append(f"{llm_enhanced['core_value_proposition']}")
            lines.append("")
        if llm_enhanced.get("reusable_template"):
            lines.append(f"### 🔄 可复用内容模板")
            lines.append(f"```")
            lines.append(llm_enhanced["reusable_template"])
            lines.append(f"```")
            lines.append("")
        viral_factors = llm_enhanced.get("viral_factors", [])
        if viral_factors:
            lines.append(f"### 🔥 传播因子")
            for factor in viral_factors:
                lines.append(f"- {factor}")
            lines.append("")
        suggestions = llm_enhanced.get("improvement_suggestions", [])
        if suggestions:
            lines.append(f"### 💡 优化建议")
            for sug in suggestions:
                lines.append(f"- {sug}")
            lines.append("")

    # ===== 完整转录文本 =====
    full_text = transcript.get("full_text", "")
    if full_text:
        lines.append("## 📄 完整转录文本")
        lines.append("")
        lines.append("<details>")
        lines.append("<summary>点击展开完整文案</summary>")
        lines.append("")
        # 按段落分割显示
        segments = transcript.get("segments", [])
        for seg in segments:
            ts = _format_time(seg.get("start", 0))
            lines.append(f"**[{ts}]** {seg.get('text', '')}")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    # ===== 页脚 =====
    lines.append("---")
    lines.append("")
    lines.append("*本报告由 Viral Video Analyzer 自动生成，分析结果仅供参考。*")

    # 写入文件
    report_content = "\n".join(lines)
    report_path = str(output_dir / f"{report_name}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"[report] 报告已生成: {report_path}")
    return report_path


def _format_number(n: int) -> str:
    """格式化大数字"""
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}亿"
    elif n >= 10_000:
        return f"{n / 10_000:.1f}万"
    else:
        return str(n)


def _format_time(seconds: float) -> str:
    """将秒数格式化为 MM:SS"""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
