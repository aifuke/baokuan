"""
文案结构分析模块 - 拆解视频脚本的叙事结构
识别：开头钩子、内容节奏、转折点、情绪曲线、结尾CTA
支持规则引擎 + LLM 增强两种模式
"""

import json
import re
from typing import Optional


# ============================================================
# 规则引擎：基于关键词和位置的结构识别
# ============================================================

# 中文钩子词库
HOOK_PATTERNS = [
    r"你知道吗", r"你绝对想不到", r"千万别", r"一定要看",
    r"震惊", r"真相是", r"揭秘", r"99%的人不知道",
    r"别再.*了", r"为什么.*总是", r"终于.*了",
    r"我.*才发现", r"原来.*", r"居然", r"没想到",
    r"注意看", r"仔细看", r"你敢信", r"离谱",
    r"太.*了吧", r"绝了", r"炸裂", r"封神",
    r"干货", r"建议收藏", r"必看", r"全网最",
]

# CTA（行动号召）词库
CTA_PATTERNS = [
    r"点赞", r"关注", r"收藏", r"转发", r"评论",
    r"三连", r"一键三连", r"别忘了", r"记得",
    r"关注我", r"点个.*赞", r"分享到", r"留言",
    r"告诉我", r"你觉得呢", r"你怎么看",
    r"下期.*见", r"敬请期待", r"持续更新",
]

# 转折词库
TRANSITION_PATTERNS = [
    r"但是", r"然而", r"不过", r"其实", r"实际上",
    r"关键是", r"重点是", r"核心是", r"说白了",
    r"换句话说", r"简单来说", r"总结一下",
    r"首先.*其次.*最后", r"第一.*第二.*第三",
    r"接下来", r"然后", r"紧接着",
]

# 情绪词库（正面/负面/惊讶）
EMOTION_POSITIVE = [
    "喜欢", "爱", "棒", "优秀", "完美", "惊艳", "感动",
    "开心", "幸福", "满足", "震撼", "佩服", "厉害",
]
EMOTION_NEGATIVE = [
    "讨厌", "恶心", "垃圾", "失望", "难过", "愤怒",
    "可怕", "糟糕", "崩溃", "无语", "离谱", "坑",
]
EMOTION_SURPRISE = [
    "震惊", "惊讶", "没想到", "居然", "竟然", "天哪",
    "卧槽", "绝了", "炸裂", "逆天", "离谱",
]


def analyze_script_structure(
    segments: list[dict],
    full_text: str,
    total_duration: float,
) -> dict:
    """
    基于规则引擎分析文案结构。

    Args:
        segments: 带时间戳的转录分段
        full_text: 完整文本
        total_duration: 视频总时长（秒）

    Returns:
        dict: 结构化分析结果
    """
    result = {
        "hook": _analyze_hook(segments, full_text),
        "cta": _analyze_cta(segments, full_text),
        "transitions": _analyze_transitions(segments, full_text),
        "emotion_curve": _analyze_emotion_curve(segments, full_text),
        "content_blocks": _segment_content_blocks(segments, total_duration),
        "text_stats": _compute_text_stats(full_text, total_duration),
    }
    return result


def _analyze_hook(segments: list, full_text: str) -> dict:
    """分析开头钩子（前15%的内容）"""
    if not segments:
        return {"found": False, "text": "", "type": "无"}

    # 取前15%的分段作为开头区域
    hook_end_idx = max(1, len(segments) // 7)
    hook_segments = segments[:hook_end_idx]
    hook_text = "".join(seg["text"] for seg in hook_segments)

    matched_patterns = []
    for pattern in HOOK_PATTERNS:
        if re.search(pattern, hook_text):
            matched_patterns.append(pattern)

    hook_types = []
    if any(p in hook_text for p in ["你知道吗", "你绝对想不到", "99%的人不知道"]):
        hook_types.append("悬念型")
    if any(p in hook_text for p in ["震惊", "居然", "没想到", "离谱"]):
        hook_types.append("震惊型")
    if any(p in hook_text for p in ["千万别", "别再", "一定要看", "必看"]):
        hook_types.append("警告/建议型")
    if any(p in hook_text for p in ["干货", "建议收藏", "全网最"]):
        hook_types.append("价值承诺型")
    if any(p in hook_text for p in ["注意看", "仔细看"]):
        hook_types.append("视觉引导型")

    return {
        "found": len(matched_patterns) > 0,
        "text": hook_text[:200],
        "matched_patterns": matched_patterns[:5],
        "types": hook_types if hook_types else ["平铺直叙"],
        "duration_covered": round(hook_segments[-1]["end"] - hook_segments[0]["start"], 1) if hook_segments else 0,
    }


def _analyze_cta(segments: list, full_text: str) -> dict:
    """分析结尾 CTA（后20%的内容）"""
    if not segments:
        return {"found": False, "text": "", "types": []}

    cta_start_idx = max(0, len(segments) - len(segments) // 5)
    cta_segments = segments[cta_start_idx:]
    cta_text = "".join(seg["text"] for seg in cta_segments)

    matched = []
    for pattern in CTA_PATTERNS:
        if re.search(pattern, cta_text):
            matched.append(pattern)

    cta_types = []
    if any(p in cta_text for p in ["点赞", "三连", "一键三连"]):
        cta_types.append("求赞")
    if any(p in cta_text for p in ["关注", "关注我"]):
        cta_types.append("求关注")
    if any(p in cta_text for p in ["收藏", "建议收藏"]):
        cta_types.append("求收藏")
    if any(p in cta_text for p in ["评论", "留言", "告诉我", "你觉得"]):
        cta_types.append("引导互动")
    if any(p in cta_text for p in ["转发", "分享"]):
        cta_types.append("求转发")

    return {
        "found": len(matched) > 0,
        "text": cta_text[:200],
        "matched_patterns": matched[:5],
        "types": cta_types if cta_types else ["无明显CTA"],
    }


def _analyze_transitions(segments: list, full_text: str) -> dict:
    """分析内容转折点"""
    transitions = []
    for seg in segments:
        text = seg["text"]
        for pattern in TRANSITION_PATTERNS:
            if re.search(pattern, text):
                transitions.append({
                    "timestamp": seg["start"],
                    "text": text[:80],
                    "pattern": pattern,
                })
                break

    return {
        "count": len(transitions),
        "items": transitions[:10],
        "density": round(len(transitions) / max(len(segments), 1), 2),
    }


def _analyze_emotion_curve(segments: list, full_text: str) -> dict:
    """分析情绪曲线"""
    emotion_timeline = []
    pos_count = 0
    neg_count = 0
    sur_count = 0

    for seg in segments:
        text = seg["text"]
        pos = sum(1 for w in EMOTION_POSITIVE if w in text)
        neg = sum(1 for w in EMOTION_NEGATIVE if w in text)
        sur = sum(1 for w in EMOTION_SURPRISE if w in text)

        pos_count += pos
        neg_count += neg
        sur_count += sur

        # 情绪分数：正-负，惊讶加权
        score = pos - neg + sur * 0.5
        emotion_timeline.append({
            "timestamp": seg["start"],
            "score": round(score, 2),
            "pos": pos, "neg": neg, "sur": sur,
        })

    # 整体情绪倾向
    total = pos_count + neg_count + sur_count
    if total == 0:
        overall = "中性"
    elif pos_count > neg_count * 1.5:
        overall = "积极正面"
    elif neg_count > pos_count * 1.5:
        overall = "消极负面"
    elif sur_count > (pos_count + neg_count):
        overall = "惊讶/反转型"
    else:
        overall = "混合情绪"

    return {
        "overall_tone": overall,
        "positive_hits": pos_count,
        "negative_hits": neg_count,
        "surprise_hits": sur_count,
        "timeline": emotion_timeline,
    }


def _segment_content_blocks(segments: list, total_duration: float) -> list[dict]:
    """将视频按时间分为若干内容块"""
    if not segments or total_duration <= 0:
        return []

    # 分为5个等分块
    num_blocks = min(5, max(2, len(segments) // 3))
    block_duration = total_duration / num_blocks
    blocks = []

    for i in range(num_blocks):
        start_time = i * block_duration
        end_time = (i + 1) * block_duration

        block_segs = [
            s for s in segments
            if start_time <= s["start"] < end_time
        ]
        block_text = "".join(s["text"] for s in block_segs)

        # 位置标签
        if i == 0:
            position = "开头"
        elif i == num_blocks - 1:
            position = "结尾"
        elif i == num_blocks // 2:
            position = "中段高潮"
        else:
            position = f"第{i+1}段"

        blocks.append({
            "index": i,
            "position": position,
            "start_time": round(start_time, 1),
            "end_time": round(end_time, 1),
            "text_preview": block_text[:100],
            "word_count": len(block_text.replace(" ", "")),
        })

    return blocks


def _compute_text_stats(full_text: str, total_duration: float) -> dict:
    """计算文本基础统计"""
    char_count = len(full_text.replace(" ", ""))
    sentence_count = len(re.split(r'[。！？!?]', full_text)) - 1
    sentence_count = max(sentence_count, 1)

    avg_sentence_len = char_count / sentence_count if sentence_count else 0

    # 信息密度估算（去停用词后的有效词占比）
    stopwords = set("的了是在有我他她它们这那个就都也还而且但如果因为所以虽然已经正在被把让给向从到为与及等")
    effective_chars = sum(1 for c in full_text if c not in stopwords and c.strip())
    info_density = effective_chars / max(char_count, 1)

    return {
        "total_chars": char_count,
        "sentence_count": sentence_count,
        "avg_sentence_length": round(avg_sentence_len, 1),
        "info_density": round(info_density, 2),
        "chars_per_second": round(char_count / max(total_duration, 1), 1),
    }


def enhance_with_llm(
    script_analysis: dict,
    full_text: str,
    metadata: dict,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: str = "gpt-4o-mini",
) -> dict:
    """
    使用 LLM 增强文案分析（可选）。
    提供更深层的叙事结构、受众画像、可复用模板等洞察。
    """
    try:
        from openai import OpenAI
    except ImportError:
        print("[script] openai SDK 未安装，跳过 LLM 增强")
        return {"llm_enhanced": False}

    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("[script] 未提供 API Key，跳过 LLM 增强")
        return {"llm_enhanced": False}

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)

    prompt = f"""你是一个短视频内容分析专家。请分析以下视频的文案，输出 JSON 格式的深度分析。

## 视频信息
- 标题: {metadata.get('title', '未知')}
- 平台: {metadata.get('platform', '未知')}
- 播放量: {metadata.get('view_count', '未知')}
- 点赞数: {metadata.get('like_count', '未知')}

## 完整文案
{full_text[:3000]}

## 规则引擎初步分析
- 钩子类型: {json.dumps(script_analysis.get('hook', {}).get('types', []), ensure_ascii=False)}
- CTA 类型: {json.dumps(script_analysis.get('cta', {}).get('types', []), ensure_ascii=False)}
- 情绪基调: {script_analysis.get('emotion_curve', {}).get('overall_tone', '未知')}

请输出以下 JSON 结构（不要包含 markdown 代码块标记）：
{{
    "narrative_structure": "叙事结构类型（如：问题-方案型、故事型、清单型、对比型、反转型等）",
    "target_audience": "目标受众画像描述",
    "core_value_proposition": "核心价值主张（这个视频给了观众什么）",
    "reusable_template": "可复用的内容模板（用 [占位符] 表示可变部分）",
    "viral_factors": ["列出3-5个可能导致传播的关键因素"],
    "improvement_suggestions": ["列出2-3个可以优化的方向"],
    "hook_effectiveness_score": 1-10的整数评分,
    "content_depth_score": 1-10的整数评分
}}"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000,
        )
        content = response.choices[0].message.content.strip()
        # 清理可能的 markdown 代码块标记
        content = re.sub(r'^```(?:json)?\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        llm_result = json.loads(content)
        llm_result["llm_enhanced"] = True
        llm_result["model_used"] = model
        print(f"[script] LLM 增强分析完成 (model={model})")
        return llm_result
    except Exception as e:
        print(f"[script] LLM 增强失败: {e}")
        return {"llm_enhanced": False, "error": str(e)}
