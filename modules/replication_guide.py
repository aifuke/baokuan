"""
复刻指南生成模块 - 核心功能
输入分析结果，输出一份可直接照着拍的同款复刻方案：
1. 逐句复刻脚本（带时间轴、语气标注、画面指令）
2. 拍摄清单（设备、场景、道具、灯光）
3. 剪辑模板（转场、字幕样式、BGM风格、节奏点）
4. 发布策略（标题公式、标签组合、发布时间）
支持规则引擎基础版 + LLM 增强版
"""

import json
import os
import re
from typing import Optional


def generate_replication_guide(
    transcript: dict,
    script_analysis: dict,
    visual_analysis: dict,
    trend_analysis: dict,
    metadata: dict,
    llm_enhanced: dict = None,
) -> dict:
    """
    生成完整的复刻指南。

    Returns:
        dict: {
            "replica_script": list[dict],   # 逐句复刻脚本
            "shooting_checklist": dict,     # 拍摄清单
            "editing_template": dict,       # 剪辑模板
            "publishing_strategy": dict,    # 发布策略
            "replication_difficulty": str,  # 复刻难度评估
        }
    """
    guide = {
        "replica_script": _build_replica_script(transcript, script_analysis),
        "shooting_checklist": _build_shooting_checklist(visual_analysis, metadata),
        "editing_template": _build_editing_template(visual_analysis, script_analysis, transcript),
        "publishing_strategy": _build_publishing_strategy(trend_analysis, metadata),
        "replication_difficulty": _assess_difficulty(script_analysis, visual_analysis, transcript),
    }
    return guide


def enhance_replication_with_llm(
    guide: dict,
    transcript: dict,
    script_analysis: dict,
    visual_analysis: dict,
    metadata: dict,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: str = "gpt-4o-mini",
) -> dict:
    """用 LLM 增强复刻指南，生成更精准的同款脚本和拍摄指导"""
    try:
        from openai import OpenAI
    except ImportError:
        print("[replicate] openai SDK 未安装，跳过 LLM 增强")
        return guide

    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("[replicate] 未提供 API Key，使用规则引擎版本")
        return guide

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)

    full_text = transcript.get("full_text", "")
    segments = transcript.get("segments", [])
    scene_info = visual_analysis.get("scene_analysis", {})
    visual_feat = visual_analysis.get("visual_features", {})

    prompt = f"""你是一个短视频复刻专家。你的任务是帮用户"照着拍同款"。
请根据以下爆款视频的完整分析，输出一份可以直接拿去拍摄的复刻方案。

## 原视频信息
- 标题: {metadata.get('title', '未知')}
- 平台: {metadata.get('platform', '未知')}
- 时长: {metadata.get('duration_str', '未知')}
- 播放量: {metadata.get('view_count', '未知')}
- 点赞: {metadata.get('like_count', '未知')}

## 完整文案（带时间戳）
{json.dumps(segments[:50], ensure_ascii=False, indent=1)}

## 视觉分析
- 剪辑节奏: {scene_info.get('pace_label', '未知')}, 每分钟切换{scene_info.get('cut_frequency', 0)}次
- 画面风格: {visual_feat.get('brightness_label', '')}, {visual_feat.get('saturation_label', '')}
- 分辨率: {visual_feat.get('resolution', '未知')}

## 文案结构
- 钩子类型: {json.dumps(script_analysis.get('hook', {}).get('types', []), ensure_ascii=False)}
- CTA类型: {json.dumps(script_analysis.get('cta', {}).get('types', []), ensure_ascii=False)}
- 情绪基调: {script_analysis.get('emotion_curve', {}).get('overall_tone', '未知')}

请输出以下JSON（不要包含markdown代码块标记）：
{{
    "replica_script": [
        {{
            "time": "00:00-00:03",
            "role": "钩子",
            "original_text": "原文案内容",
            "replica_text": "替换为可复用的同款文案（保留句式结构，替换具体内容）",
            "visual_direction": "画面指令：描述这个镜头应该怎么拍（景别、动作、表情、道具）",
            "tone": "语气标注：如'惊讶''严肃''轻松''加速'"
        }}
    ],
    "shooting_plan": {{
        "scenes_needed": ["需要准备的场景列表"],
        "props": ["需要的道具列表"],
        "wardrobe": "服装/造型建议",
        "lighting": "灯光方案",
        "camera_setup": "机位与运镜建议",
        "total_shots_estimate": "预估总镜头数"
    }},
    "editing_blueprint": {{
        "opening_hook_technique": "开头钩子的剪辑手法",
        "transition_style": "转场风格建议",
        "subtitle_style": "字幕样式（字体、颜色、位置、动效）",
        "bgm_recommendation": "BGM风格与节奏建议",
        "pacing_notes": "剪辑节奏要点（哪里快切、哪里留白）",
        "effects": ["需要用到的特效/滤镜"]
    }},
    "title_formulas": ["3个可直接套用的标题公式"],
    "hashtag_combination": "推荐的标签组合策略",
    "best_post_time": "建议发布时间段",
    "difficulty_notes": "复刻难点与注意事项"
}}"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=4000,
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r'^```(?:json)?\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        llm_result = json.loads(content)
        llm_result["llm_enhanced"] = True
        llm_result["model_used"] = model
        print(f"[replicate] LLM 复刻指南生成完成 (model={model})")
        return llm_result
    except Exception as e:
        print(f"[replicate] LLM 增强失败: {e}")
        return guide


# ============================================================
# 规则引擎：无 LLM 时的基础复刻指南
# ============================================================

def _build_replica_script(transcript: dict, script_analysis: dict) -> list[dict]:
    """基于转录文本构建逐句复刻脚本"""
    segments = transcript.get("segments", [])
    hook_types = script_analysis.get("hook", {}).get("types", [])
    cta_types = script_analysis.get("cta", {}).get("types", [])

    replica = []
    total = len(segments)

    for i, seg in enumerate(segments):
        # 判断段落角色
        if i < max(1, total // 7):
            role = "🎣 钩子"
        elif i >= total - max(1, total // 5):
            role = "📢 CTA"
        else:
            role = "📖 正文"

        # 生成复刻文案（保留句式，标注可替换部分）
        text = seg.get("text", "")
        replica_text = _make_replicable(text, role)

        # 语气推断
        tone = _infer_tone(text, role)

        start = seg.get("start", 0)
        end = seg.get("end", 0)

        replica.append({
            "time": f"{_fmt_time(start)}-{_fmt_time(end)}",
            "role": role,
            "original_text": text,
            "replica_text": replica_text,
            "visual_direction": _infer_visual_direction(role, i, total),
            "tone": tone,
        })

    return replica


def _make_replicable(text: str, role: str) -> str:
    """将原文转为可复刻模板（用【】标注可替换部分）"""
    if not text:
        return "[在此填入你的内容]"

    result = text
    # 替换具体数字为占位符
    result = re.sub(r'\d+\.?\d*', '【数字】', result)
    # 替换专有名词模式（简化处理）
    result = re.sub(r'(?:抖音|快手|B站|小红书|微博|微信)', '【平台】', result)

    if "钩子" in role:
        result = f"[保持悬念/震惊句式] {result}"
    elif "CTA" in role:
        result = f"[引导互动] {result}"

    return result


def _infer_tone(text: str, role: str) -> str:
    """推断语气"""
    if "钩子" in role:
        if any(w in text for w in ["震惊", "居然", "没想到", "离谱"]):
            return "😲 惊讶/震撼"
        if any(w in text for w in ["千万别", "别再", "注意"]):
            return "⚠️ 警告/紧迫"
        if any(w in text for w in ["你知道吗", "为什么"]):
            return "🤔 好奇/提问"
        return "🎯 有力/直接"

    if "CTA" in role:
        return "😊 亲切/邀请"

    # 正文
    if any(w in text for w in ["但是", "然而", "其实"]):
        return "🔄 转折"
    if any(w in text for w in ["首先", "第一", "接下来"]):
        return "📋 条理清晰"
    if any(w in text for w in ["哈哈", "笑死", "绝了"]):
        return "😂 轻松/幽默"
    return "🗣️ 正常叙述"


def _infer_visual_direction(role: str, index: int, total: int) -> str:
    """推断画面指令"""
    if "钩子" in role:
        return "近景/特写，直视镜头，表情夸张或有悬念感，配合文字弹出动效"
    if "CTA" in role:
        return "中景，微笑面对镜头，手指向下方（评论区）或侧面（关注按钮），可加箭头指引贴纸"
    # 正文
    if index < total // 3:
        return "中景为主，配合关键信息文字贴片，适当插入素材/截图/B-roll"
    elif index < total * 2 // 3:
        return "交替使用中景和特写，高潮部分加快剪辑节奏，可用画中画展示案例"
    else:
        return "中景回归，语速放缓，配合总结性文字卡片"


def _build_shooting_checklist(visual_analysis: dict, metadata: dict) -> dict:
    """生成拍摄清单"""
    features = visual_analysis.get("visual_features", {})
    scene = visual_analysis.get("scene_analysis", {})

    brightness = features.get("brightness_label", "中等亮度")
    saturation = features.get("saturation_label", "中等饱和")
    resolution = features.get("resolution", "1080x1920")
    cut_freq = scene.get("cut_frequency", 0)

    # 灯光建议
    if "暗调" in brightness:
        lighting = "侧光/轮廓光为主，营造氛围感；避免正面平光"
    elif "明亮" in brightness:
        lighting = "柔光箱/环形灯正面补光，确保面部均匀明亮"
    else:
        lighting = "自然光+补光灯混合，保持画面通透"

    # 机位建议
    if cut_freq > 20:
        camera = "多机位或频繁变换角度（正面/侧面/俯拍交替），保持视觉新鲜感"
    elif cut_freq > 10:
        camera = "主机位正面+偶尔切入特写/B-roll，节奏适中"
    else:
        camera = "固定机位为主，长镜头叙事，靠内容和表达力吸引观众"

    return {
        "resolution": f"拍摄分辨率建议: {resolution}（竖屏9:16优先）",
        "lighting": lighting,
        "camera_setup": camera,
        "scenes_needed": ["主拍摄场景（干净背景）", "B-roll素材拍摄"],
        "props": ["手机/电脑（如需展示内容）", "文字卡片/手写板（如需强调重点）"],
        "wardrobe": "纯色上衣为主，避免花纹干扰画面；颜色与背景形成对比",
        "total_shots_estimate": f"预估 {max(10, int(cut_freq * 2))} 个镜头",
    }


def _build_editing_template(visual_analysis: dict, script_analysis: dict, transcript: dict) -> dict:
    """生成剪辑模板"""
    scene = visual_analysis.get("scene_analysis", {})
    pace = scene.get("pace_label", "中等节奏")
    cut_freq = scene.get("cut_frequency", 0)

    # 转场风格
    if cut_freq > 25:
        transition = "硬切为主，配合缩放/闪白/故障效果，节奏紧凑"
    elif cut_freq > 12:
        transition = "硬切+偶尔滑入/淡入淡出，自然不突兀"
    else:
        transition = "淡入淡出/交叉溶解为主，节奏舒缓"

    # BGM建议
    emotion = script_analysis.get("emotion_curve", {}).get("overall_tone", "中性")
    if "积极" in emotion:
        bgm = "轻快/正能量BGM，BPM 100-130，卡点剪辑"
    elif "消极" in emotion:
        bgm = "低沉/悬疑BGM，BPM 60-90，留白较多"
    elif "惊讶" in emotion or "反转" in emotion:
        bgm = "前半段平稳→转折点音效突变→后半段高能，制造反差"
    else:
        bgm = "中性背景音乐，不抢戏，BPM 80-110"

    speech_rate = transcript.get("speech_rate", {})
    pace_label = speech_rate.get("pace_label", "正常")

    return {
        "opening_hook_technique": "前3秒必须有视觉冲击或文字悬念，配合钩子文案同步出现",
        "transition_style": transition,
        "subtitle_style": "居中底部字幕，白色描边黑字或黄色高亮关键词，字号大、停留时间短",
        "bgm_recommendation": bgm,
        "pacing_notes": f"整体节奏: {pace}。语速: {pace_label}。"
                       f"{'高潮段加速剪辑，每1-2秒切一个画面' if cut_freq > 20 else '保持呼吸感，重要信息停留2-3秒'}",
        "effects": ["关键词弹出动效", "进度条/章节标记", "表情包/梗图穿插（适度）"],
    }


def _build_publishing_strategy(trend_analysis: dict, metadata: dict) -> dict:
    """生成发布策略"""
    tags = trend_analysis.get("tags_topics", {})
    publishing = trend_analysis.get("publishing", {})

    keywords = tags.get("keywords", [])
    platform_tags = tags.get("platform_tags", [])

    # 标题公式
    title_styles = publishing.get("title_styles", [])
    formulas = []
    if "数字型" in title_styles:
        formulas.append("「N个方法/步骤/真相」+ 核心价值词")
    if "疑问型" in title_styles:
        formulas.append("「为什么XXX总是YYY？」+ 悬念后缀")
    if "感叹型" in title_styles:
        formulas.append("「太XXX了！」+ 具体场景描述")
    formulas.append("「99%的人不知道」+ 领域干货点")
    formulas = formulas[:3]

    # 标签组合
    tag_strategy = f"核心词({'/'.join(keywords[:3])}) + 热门话题标签3-5个 + 长尾精准标签2-3个"

    return {
        "title_formulas": formulas,
        "hashtag_combination": tag_strategy,
        "best_post_time": "工作日: 12:00-13:00 / 18:00-20:00 / 21:00-23:00\n周末: 10:00-12:00 / 20:00-23:00",
        "cover_tip": "封面用大字标题+人物表情/产品特写，3秒内传达视频核心价值",
    }


def _assess_difficulty(script_analysis: dict, visual_analysis: dict, transcript: dict) -> str:
    """评估复刻难度"""
    scene = visual_analysis.get("scene_analysis", {})
    cut_freq = scene.get("cut_frequency", 0)
    word_count = transcript.get("word_count", 0)
    duration = 0
    segments = transcript.get("segments", [])
    if segments:
        duration = segments[-1].get("end", 0) - segments[0].get("start", 0)

    score = 0
    # 剪辑复杂度
    if cut_freq > 25:
        score += 3
    elif cut_freq > 15:
        score += 2
    else:
        score += 1

    # 文案长度
    if word_count > 800:
        score += 3
    elif word_count > 400:
        score += 2
    else:
        score += 1

    # 时长
    if duration > 300:
        score += 3
    elif duration > 120:
        score += 2
    else:
        score += 1

    # 情绪复杂度
    emotion = script_analysis.get("emotion_curve", {}).get("overall_tone", "中性")
    if "混合" in emotion or "反转" in emotion:
        score += 2
    else:
        score += 1

    if score <= 4:
        return "⭐ 简单 — 新手友好，1-2小时可完成拍摄+剪辑"
    elif score <= 7:
        return "⭐⭐ 中等 — 需要一定剪辑基础，半天可完成"
    elif score <= 10:
        return "⭐⭐⭐ 较难 — 需要熟练剪辑+表现力，建议分多次拍摄"
    else:
        return "⭐⭐⭐⭐ 高难度 — 专业级制作，建议拆解为多个短片分别复刻"


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
