"""
爆款元素分析模块 - 综合分析视频的传播因子
包括：互动率计算、标签分析、发布时间策略、竞品对标维度
"""

import json
import re
from typing import Optional


def compute_engagement_metrics(metadata: dict) -> dict:
    """
    根据元数据计算互动指标。

    Returns:
        dict: 各项互动率与评级
    """
    views = metadata.get("view_count", 0) or 0
    likes = metadata.get("like_count", 0) or 0
    comments = metadata.get("comment_count", 0) or 0
    shares = metadata.get("share_count", 0) or 0

    if views <= 0:
        return {
            "available": False,
            "note": "播放量数据不可用，无法计算互动率",
        }

    like_rate = likes / views * 100
    comment_rate = comments / views * 100
    share_rate = shares / views * 100
    total_engagement = (likes + comments + shares) / views * 100

    # 互动率评级（基于行业经验值）
    if total_engagement >= 10:
        engagement_level = "极高（爆款级）"
    elif total_engagement >= 5:
        engagement_level = "高（优质内容）"
    elif total_engagement >= 2:
        engagement_level = "中等"
    elif total_engagement >= 0.5:
        engagement_level = "偏低"
    else:
        engagement_level = "极低"

    # 点赞评论比（反映内容深度 vs 情绪驱动）
    like_comment_ratio = likes / max(comments, 1)
    if like_comment_ratio > 50:
        interaction_type = "情绪驱动型（点赞远多于评论）"
    elif like_comment_ratio > 10:
        interaction_type = "轻度互动型"
    elif like_comment_ratio > 3:
        interaction_type = "均衡互动型"
    else:
        interaction_type = "深度讨论型（评论活跃）"

    return {
        "available": True,
        "views": views,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "like_rate": round(like_rate, 2),
        "comment_rate": round(comment_rate, 2),
        "share_rate": round(share_rate, 2),
        "total_engagement_rate": round(total_engagement, 2),
        "engagement_level": engagement_level,
        "like_comment_ratio": round(like_comment_ratio, 1),
        "interaction_type": interaction_type,
    }


def analyze_tags_and_topics(metadata: dict, full_text: str) -> dict:
    """
    分析标签和话题策略。
    """
    tags = metadata.get("tags", []) or []
    categories = metadata.get("categories", []) or []
    title = metadata.get("title", "")
    description = metadata.get("description", "")

    # 从标题和描述中提取 #话题标签
    hashtag_pattern = r'#([^\s#]+)'
    title_hashtags = re.findall(hashtag_pattern, title)
    desc_hashtags = re.findall(hashtag_pattern, description or "")
    all_hashtags = list(set(title_hashtags + desc_hashtags))

    # 使用 jieba 提取关键词
    keywords = []
    try:
        import jieba.analyse
        combined_text = f"{title} {full_text[:500]}"
        keywords = jieba.analyse.extract_tags(combined_text, topK=10)
    except ImportError:
        # 简单分词回退
        keywords = [w for w in title.split() if len(w) >= 2][:10]

    # 标签策略评估
    tag_count = len(tags) + len(all_hashtags)
    if tag_count == 0:
        tag_strategy = "无标签"
    elif tag_count <= 3:
        tag_strategy = "精简标签（聚焦型）"
    elif tag_count <= 8:
        tag_strategy = "适中标签（平衡型）"
    else:
        tag_strategy = "密集标签（流量覆盖型）"

    return {
        "platform_tags": tags[:15],
        "hashtags": all_hashtags[:15],
        "categories": categories,
        "keywords": keywords,
        "tag_count": tag_count,
        "tag_strategy": tag_strategy,
    }


def analyze_publishing_strategy(metadata: dict) -> dict:
    """
    分析发布策略（时间、标题风格等）。
    """
    upload_date = metadata.get("upload_date_fmt", metadata.get("upload_date", ""))
    title = metadata.get("title", "")

    # 标题风格分析
    title_length = len(title)
    has_number = bool(re.search(r'\d', title))
    has_question = bool(re.search(r'[？?]', title))
    has_exclamation = bool(re.search(r'[！!]', title))
    has_emoji = bool(re.search(r'[\U0001F300-\U0001F9FF]', title))
    has_brackets = bool(re.search(r'[\[【\(（]', title))

    title_styles = []
    if has_number:
        title_styles.append("数字型")
    if has_question:
        title_styles.append("疑问型")
    if has_exclamation:
        title_styles.append("感叹型")
    if has_emoji:
        title_styles.append("Emoji装饰")
    if has_brackets:
        title_styles.append("括号强调")
    if not title_styles:
        title_styles.append("陈述型")

    # 标题长度评估
    if title_length < 10:
        length_eval = "过短（可能不利于SEO）"
    elif title_length < 25:
        length_eval = "适中"
    elif title_length < 40:
        length_eval = "较长（信息丰富）"
    else:
        length_eval = "过长（可能被截断）"

    # 星期几发布
    weekday = ""
    if upload_date and len(upload_date) >= 10:
        try:
            from datetime import datetime
            dt = datetime.strptime(upload_date[:10], "%Y-%m-%d")
            weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            weekday = weekdays[dt.weekday()]
        except ValueError:
            pass

    return {
        "upload_date": upload_date,
        "weekday": weekday,
        "title": title,
        "title_length": title_length,
        "title_length_eval": length_eval,
        "title_styles": title_styles,
    }


def generate_viral_score_card(
    engagement: dict,
    script_analysis: dict,
    visual_analysis: dict,
    publishing: dict,
) -> dict:
    """
    生成综合爆款评分卡。
    各维度加权打分，总分100。
    """
    scores = {}

    # 1. 互动数据得分（权重30%）
    if engagement.get("available"):
        eng_rate = engagement.get("total_engagement_rate", 0)
        if eng_rate >= 10:
            scores["engagement"] = 30
        elif eng_rate >= 5:
            scores["engagement"] = 25
        elif eng_rate >= 2:
            scores["engagement"] = 18
        elif eng_rate >= 0.5:
            scores["engagement"] = 10
        else:
            scores["engagement"] = 5
    else:
        scores["engagement"] = 0  # 无数据不计分

    # 2. 钩子质量得分（权重20%）
    hook = script_analysis.get("hook", {})
    hook_score = 5  # 基础分
    if hook.get("found"):
        hook_score += 10
        hook_types = hook.get("types", [])
        if "悬念型" in hook_types or "震惊型" in hook_types:
            hook_score += 5
    scores["hook"] = min(hook_score, 20)

    # 3. 内容结构得分（权重20%）
    structure_score = 8  # 基础分
    transitions = script_analysis.get("transitions", {})
    if transitions.get("count", 0) >= 3:
        structure_score += 5
    emotion = script_analysis.get("emotion_curve", {})
    if emotion.get("overall_tone") != "中性":
        structure_score += 4
    cta = script_analysis.get("cta", {})
    if cta.get("found"):
        structure_score += 3
    scores["structure"] = min(structure_score, 20)

    # 4. 视觉节奏得分（权重15%）
    visual_score = 7  # 基础分
    scene = visual_analysis.get("scene_analysis", {})
    cut_freq = scene.get("cut_frequency", 0)
    if 10 <= cut_freq <= 30:
        visual_score += 5
    elif cut_freq > 30:
        visual_score += 3
    features = visual_analysis.get("visual_features", {})
    if features.get("saturation_label") == "高饱和（鲜艳风）":
        visual_score += 3
    scores["visual"] = min(visual_score, 15)

    # 5. 发布策略得分（权重15%）
    pub_score = 7  # 基础分
    title_styles = publishing.get("title_styles", [])
    if "数字型" in title_styles:
        pub_score += 3
    if "疑问型" in title_styles or "感叹型" in title_styles:
        pub_score += 3
    title_eval = publishing.get("title_length_eval", "")
    if "适中" in title_eval:
        pub_score += 2
    scores["publishing"] = min(pub_score, 15)

    total = sum(scores.values())

    # 总评
    if total >= 80:
        overall = "S级（超级爆款）"
    elif total >= 65:
        overall = "A级（优质爆款）"
    elif total >= 50:
        overall = "B级（良好内容）"
    elif total >= 35:
        overall = "C级（普通内容）"
    else:
        overall = "D级（待优化）"

    return {
        "scores": scores,
        "total_score": total,
        "overall_rating": overall,
        "dimension_labels": {
            "engagement": "互动数据 (30%)",
            "hook": "钩子质量 (20%)",
            "structure": "内容结构 (20%)",
            "visual": "视觉节奏 (15%)",
            "publishing": "发布策略 (15%)",
        },
    }
